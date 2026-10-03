using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Diagnostics;
using Launcher.App.Grid;
using Launcher.App.Launching;
using Launcher.App.Models;
using Launcher.App.Navigation;
using Launcher.App.Options;
using Launcher.App.Screens;
using Launcher.App.Settings;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.App.Ui;
using Launcher.Core;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Platform;

namespace Launcher.App.Boot;

/// <summary>
/// The main scene (A1 Boot, A3 boot path). Boots straight into the systems grid:
/// <list type="number">
/// <item>On the thread pool: settings and systems config, the theme (its manifests, and each system's model
/// candidates), then library.db and the systems query.</item>
/// <item>Meanwhile on the main thread: the camera, the cover array and the overlay; then, as soon as the theme is
/// resolved, its models load (Godot's loader threads for built-in ones, a worker for user files).</item>
/// <item>When both are done, the look and the grids are built and the systems grid is bound; the next drawn frame is
/// <c>interactive</c>.</item>
/// <item>After that, a warm-up spread over a few frames: every pipeline drawn once, the first cover upload, the
/// glyphs, the launch controller and the status indicators. Nothing is scanned at boot; systems never scanned are scanned after it.</item>
/// </list>
/// </summary>
public partial class Main : Node3D
{
    public const float FieldOfView = 40.0f;
    public const float CameraDistance = 6.2f;

    /// <summary>A3: 3D renders at no more than 1080p internally, upscaled; the 2D overlay stays native.</summary>
    public const int MaxRenderHeight = 1080;

    private const int CoverSlots = 64;
    private const int MaxSystemSlots = 64;
    private const float SystemRowsVisible = 2.7f;
    private const float GameRowsVisible = 3.2f;

    private readonly MainThreadQueue _queue = new();
    private readonly CancellationTokenSource _shutdown = new();
    private readonly ModelLoader _loader = new();
    private DebugOptions _options = DebugOptions.None;
    private AppServices? _services;
    private ThemePlan? _plan;
    private ThemeRuntime? _theme;
    private LookStage? _look;
    private Exception? _bootFailure;
    private Camera3D _camera = null!;
    private TextureStreamer? _streamer;
    private ItemGrid? _systemsGrid;
    private ItemGrid? _gamesGrid;
    private InfoOverlay? _overlay;
    private Navigator? _navigator;
    private LaunchController? _launch;
    private ScrollBench? _scrollBench;
    private UiLayer? _ui;
    private LibraryJobs? _jobs;
    private SettingsController? _settings;
    private IPowerControl? _power;
    private StatusBar? _statusBar;
    private Launcher.Core.Media.IVideoDecoder? _videoDecoder;
    private DeviceStatusMonitor? _deviceStatus;
    private Stage _stage = Stage.Loading;
    private int _warmUpFrame;
    private SubViewport? _glyphWarmUp;
    private bool _waitingForFirstFrame;
    private bool _headless;

    private enum Stage
    {
        Loading,
        WaitingForFrame,
        WarmingUp,
        Running,
        Failed,
    }

    public override void _Ready()
    {
        DebugHooks.Timeline.Mark(StartupMarks.MainReady);
        _options = DebugHooks.Options;
        _headless = DisplayServer.GetName() == "headless";
        GD.Print(
            $"Launcher.Core {CoreInfo.Version} | Godot {Engine.GetVersionInfo()["string"].AsString()} | " +
            $"{RuntimeInformation.FrameworkDescription} | " +
            $"{RenderingServer.GetCurrentRenderingMethod()}/{RenderingServer.GetCurrentRenderingDriverName()}");

        var executableDir = Path.GetDirectoryName(OS.GetExecutablePath()) ?? ".";

        // The app's own themes are a folder beside its executable, outside the PCK (A6 Locations); run from the editor
        // binary, the project's.
        var themesDir = OS.HasFeature("editor")
            ? ProjectSettings.GlobalizePath("res://" + Launcher.Core.Theming.ThemeLoader.FolderName)
            : Path.Combine(executableDir, Launcher.Core.Theming.ThemeLoader.FolderName);
        var options = _options;
        var token = _shutdown.Token;
        var headless = _headless;
        _ = Task.Run(async () =>
        {
            try
            {
                _services = await AppServices.LoadAsync(options, executableDir, themesDir, headless ? null : plan => Volatile.Write(ref _plan, plan), token).ConfigureAwait(false);
            }
            catch (Exception e) when (e is not OperationCanceledException)
            {
                _bootFailure = e;
            }
        }, token);

        if (_headless)
        {
            // No rendering: only the services, for --launch.
            return;
        }

        NavInput.RegisterActions();
        _camera = new Camera3D { Fov = FieldOfView, Position = new Vector3(0, 0, CameraDistance), Current = true };
        AddChild(_camera);

        // The environment, gradient and lights are made now, while the main thread would only wait; the theme's look
        // is shown on them once it's known.
        _look = new LookStage(this, _camera);
        ApplyRenderScale();
        GetViewport().SizeChanged += OnViewportSizeChanged;

        // Pool textures are created at boot and only updated while browsing (A3). The cover-class array is made now,
        // since nearly every theme's templates have a cover (A7); a theme's other slots get theirs once its models are in.
        if (!_options.NoTextures)
        {
            _streamer = new TextureStreamer(CoverSlots, TextureStreamer.DefaultWorkers);
            _streamer.CreateBootArray();

            // The first layer update can take tens of milliseconds (M1), so it's done now, while the DB opens, rather
            // than in the first frames after interactive.
            _streamer.WarmUpload();
        }

        _overlay = new InfoOverlay { Visible = !_options.NoOverlay };
        AddChild(_overlay);

        // The settings screens' layer (M7): hidden and idle until the settings open. Its contents are built on demand.
        _ui = new UiLayer();
        AddChild(_ui);

        // The games grid needs nothing from the theme or the library until it's given templates, so it's built now,
        // while the main thread would only wait for them: its title atlas and slot-state texture are its dearest parts.
        _gamesGrid = new ItemGrid(_streamer, default, CoverSlots, blockSize: 160, spines: true, systemCards: false)
        {
            RowsVisible = GameRowsVisible,
            Name = "Games",
            Visible = false,
        };
        AddChild(_gamesGrid);
    }

    public override void _ExitTree()
    {
        _shutdown.Cancel();
        if (_waitingForFirstFrame)
        {
            RenderingServer.FramePostDraw -= OnFramePostDraw;
        }

        _scrollBench?.Dispose();
        _deviceStatus?.Dispose();

        // A scrape still running pauses (it stays queued) before the library closes.
        _jobs?.Dispose();
        _loader.FreeScenes();
        _streamer?.Dispose();
        _services?.Dispose();
    }

    public override void _Process(double delta)
    {
        _queue.Drain();
        switch (_stage)
        {
            case Stage.Loading:
                PollBoot();
                return;
            case Stage.Failed:
                return;
        }

        if (_headless)
        {
            return;
        }

        if (_stage == Stage.WarmingUp)
        {
            WarmUpStep();
        }

        _scrollBench?.Update(delta);
        StepNavScript();
        _ui!.Update(delta);
        _jobs?.Jobs.Tick(delta);
        _statusBar?.Tick(delta);
        _navigator?.Update(delta);
        var dt = (float)delta;
        _systemsGrid!.Tick(dt);
        _gamesGrid!.Tick(dt);
        _gamesGrid.PumpTextures(TextureStreamer.DefaultBudgetBytes, _options.UploadCap);
    }

    // ---- Boot -----------------------------------------------------------------------------------

    private void PollBoot()
    {
        if (_bootFailure is { } failure)
        {
            _stage = Stage.Failed;
            GD.PushError($"Boot failed: {failure}");
            if (!_headless)
            {
                _overlay?.SetStatus($"Odyssey Launcher couldn't open its library. {failure.Message}");
            }

            if (_options.IsActive || _options.LaunchRequested)
            {
                GetTree().Quit(1);
            }

            return;
        }

        if (_headless)
        {
            if (_services is not null)
            {
                _stage = Stage.Running;
                if (_options.LaunchRequested)
                {
                    Launch().StartDebugLaunch(_options);
                }
            }

            return;
        }

        // The theme's models start loading as soon as the theme is resolved, while the DB opens.
        if (_theme is null && Volatile.Read(ref _plan) is { } plan)
        {
            // User models are processed into CacheDir/models/ and their problems logged to DataDir/logs/models.log (A7).
            _loader.UseFolders(plan.Paths.CacheDir, plan.Paths.DataDir, PlatformServices.CreateImageDecoder());
            _theme = new ThemeRuntime(plan, _loader);
        }

        try
        {
            if (_theme?.Poll() == true)
            {
                DebugHooks.Timeline.Mark(BootMarks.ModelsLoaded);
            }
        }
        catch (InvalidOperationException e)
        {
            _bootFailure = e;
            return;
        }

        if (_services is not { } services || _theme is not { Ready: true })
        {
            return;
        }

        BuildScene(services);
        _stage = Stage.WaitingForFrame;
        _waitingForFirstFrame = true;
        RenderingServer.FramePostDraw += OnFramePostDraw;
    }

    private void BuildScene(AppServices services)
    {
        _streamer?.SetFolders(services.Paths.CacheDir, services.Paths.DataDir);

        var clock = System.Diagnostics.Stopwatch.StartNew();
        var theme = _theme!;
        _look!.Show(theme.LookFor(null), 0);
        var lookMs = clock.Elapsed.TotalMilliseconds;
        _gamesGrid!.SetBackground(_look.Colours);
        _gamesGrid.SetTemplates(theme.GameTemplates);
        var templatesMs = clock.Elapsed.TotalMilliseconds;

        // Every shown system fits in the pool (empty ones aren't shown unless the setting says so), with room for the
        // columns to change; the virtual systems are 2 more.
        var shownSystems = 0;
        foreach (var system in services.Systems)
        {
            if (system.GameCount > 0 || !services.Config.Settings.Display.HideEmptySystems)
            {
                shownSystems++;
            }
        }

        var systemSlots = Math.Clamp(shownSystems + 2 + ItemGrid.MaxColumns, 24, MaxSystemSlots);
        _systemsGrid = new ItemGrid(null, _look.Colours, systemSlots, blockSize: 192, spines: false, systemCards: true)
        {
            RowsVisible = SystemRowsVisible,
            Name = "Systems",
        };
        _systemsGrid.SetTemplates(theme.CardTemplates);
        var gridsMs = clock.Elapsed.TotalMilliseconds;
        AddChild(_systemsGrid);
        _gamesGrid.Visible = true;
        var addMs = clock.Elapsed.TotalMilliseconds;
        UpdateGridViews();
        ApplyDisplaySettings(services.Config);
        InstallBootLayout(theme);
        DebugHooks.Timeline.Mark(BootMarks.SceneBuilt);

        _navigator = new Navigator(services, _queue, _systemsGrid, _gamesGrid, _overlay!, _look, _loader, theme)
        {
            Streamer = _streamer,
            LayoutOverride = _options.Layout,
        };
        AddChild(_navigator);
        _navigator.ShowSystems();

        // Every template's pipeline is drawn in the first frame, faded into the background (A3), so it's compiled
        // before interactive rather than in a hitch just after it.
        _gamesGrid.BeginWarmUp();
        DebugHooks.Timeline.Mark(BootMarks.SystemsGridBound);
        GD.Print(FormattableString.Invariant($"Boot: look {lookMs:0.0} ms, games templates {templatesMs - lookMs:0.0} ms, systems grid {gridsMs - templatesMs:0.0} ms, added in {addMs - gridsMs:0.0} ms, bound in {clock.Elapsed.TotalMilliseconds - addMs:0.0} ms."));
        GD.Print($"Theme: '{theme.Plan.Active.Id}' ({theme.Plan.Active.Name}): {theme.GameTemplates.Count} game template(s), {theme.CardTemplates.Count} system model(s); media slots: {theme.Layout}.");
        DebugHooks.Theme = (theme.Plan.Active.Id, theme.Layout.ToString());

        var games = 0;
        foreach (var system in services.Systems)
        {
            games += system.GameCount;
        }

        DebugHooks.Library = new BenchLibrary(shownSystems + 2, games, null, 0);
        GCSettings.LatencyMode = GCLatencyMode.SustainedLowLatency;
    }

    /// <summary>
    /// The theme's slot layout for the streamer. With only the cover class, the boot array is enough. Other slots'
    /// 256² array is made on a worker (creating textures on the main thread can stall for tens of milliseconds), and
    /// installed when it's ready: the games grid isn't on screen before then, and shows each slot's fallback if it is.
    /// </summary>
    private void InstallBootLayout(ThemeRuntime theme)
    {
        if (_streamer is not { } streamer)
        {
            return;
        }

        var layout = theme.Layout;
        var large = streamer.Large;
        if (layout.SmallCount == 0 && (layout.LargeCount == 0 || large is not null))
        {
            streamer.Install(layout, layout.LargeCount > 0 ? large : null, null);
            _gamesGrid!.EnableTextures();
            return;
        }

        streamer.Install(layout, large, null);
        _ = Task.Run(() =>
        {
            var built = System.Diagnostics.Stopwatch.StartNew();
            var arrays = streamer.BuildArrays(layout, large, null);
            var builtMs = built.Elapsed.TotalMilliseconds;
            _queue.Post(() =>
            {
                if (_navigator?.ThemeId is { } id && id != theme.Plan.Active.Id)
                {
                    return;
                }

                var installed = System.Diagnostics.Stopwatch.StartNew();
                streamer.Install(layout, arrays.Large, arrays.Small);
                _gamesGrid!.EnableTextures();
                GD.Print(FormattableString.Invariant($"Boot: media arrays for {layout} built and warmed in {builtMs:0.0} ms on a worker, installed in {installed.Elapsed.TotalMilliseconds:0.0} ms."));
            });
        });
    }

    private void OnFramePostDraw()
    {
        // Interactive: the systems grid, bound from the DB, is on screen and input is handled from here on.
        RenderingServer.FramePostDraw -= OnFramePostDraw;
        _waitingForFirstFrame = false;
        DebugHooks.MarkInteractive();
        CallDeferred(MethodName.OnInteractive);
    }



    private void OnInteractive()
    {
        var ourCode = DebugHooks.Timeline.Between(StartupMarks.AutoloadEnterTree, StartupMarks.Interactive);
        var marks = new System.Text.StringBuilder();
        foreach (var (name, ms) in DebugHooks.Timeline.ToDictionary())
        {
            marks.Append(FormattableString.Invariant($" {name} {ms:0}"));
        }

        GD.Print(FormattableString.Invariant($"Boot: interactive, {ourCode:0.0} ms after our first code. Marks (ms since the process started):{marks}"));
        _stage = Stage.WarmingUp;
        _warmUpFrame = 0;
    }

    /// <summary>One step per frame, so no single frame carries the whole warm-up.</summary>
    private void WarmUpStep()
    {
        var step = _warmUpFrame++;
        switch (step)
        {
            case 0:
                _gamesGrid!.EndWarmUp();
                break;
            case 1:
                BuildSettings();
                break;
            case 2:
                _navigator!.Launcher = Launch();
                break;
            case >= 3 and < 3 + GlyphSteps:
                // The sizes the title atlases draw at, a third of printable ASCII per frame: a title's first
                // appearance would otherwise rasterise its glyphs mid-scroll.
                var glyph = step - 3;
                _glyphWarmUp?.QueueFree();
                _glyphWarmUp = GlyphWarmUp(
                    (glyph / GlyphChunks) switch
                    {
                        0 => _gamesGrid!.AtlasFontSizes.Block,
                        1 => _gamesGrid!.AtlasFontSizes.Spine,
                        _ => _systemsGrid!.AtlasFontSizes.Block,
                    },
                    glyph % GlyphChunks);
                AddChild(_glyphWarmUp);
                break;
            case 3 + GlyphSteps:
                _glyphWarmUp?.QueueFree();
                _glyphWarmUp = null;
                BuildStatusBar();
                _stage = Stage.Running;
                DebugHooks.Timeline.Mark(BootMarks.WarmUpDone);
                AfterWarmUp();
                break;
        }
    }

    private int _navScriptStep = -1;
    private int _navScriptWait;
    private bool _navScriptTurning;

    /// <summary>--nav-script: one step every few frames, through the navigator as the controller would.</summary>
    private void StepNavScript()
    {
        if (_navScriptStep < 0 || _navScriptStep >= _options.NavScript.Count || ++_navScriptWait < DebugOptions.NavScriptStepFrames)
        {
            return;
        }

        _navScriptWait = 0;
        if (_navScriptTurning)
        {
            SendTurn(0, 0);
        }

        var step = _options.NavScript[_navScriptStep++];
        var command = step switch
        {
            "up" => NavCommand.Up,
            "down" => NavCommand.Down,
            "left" => NavCommand.Left,
            "right" => NavCommand.Right,
            "pageup" => NavCommand.PageUp,
            "pagedown" => NavCommand.PageDown,
            "letterprevious" => NavCommand.LetterPrevious,
            "letternext" => NavCommand.LetterNext,
            "first" => NavCommand.First,
            "last" => NavCommand.Last,
            "accept" => NavCommand.Accept,
            "back" => NavCommand.Back,
            "favourite" => NavCommand.Favourite,
            "menu" => NavCommand.Menu,
            "x" => NavCommand.Alternate,
            "y" => NavCommand.Secondary,
            "power" => NavCommand.Power,
            _ => NavCommand.None,
        };
        if (command != NavCommand.None && _ui!.IsOpen)
        {
            _ui.Run(command);
        }
        else if (command != NavCommand.None)
        {
            _navigator!.Run(command);
        }
        else if (step == "theme")
        {
            _navigator!.SwitchTheme(null);
        }
        else if (step == "rescan")
        {
            _navigator!.Rescan(null);
        }
        else if (step is "click" or "scroll" or "type")
        {
            SendInput(step);
        }
        else if (step == "turn")
        {
            // The right stick held right and a little up until the next step.
            SendTurn(1, -0.6f);
        }

        GD.Print($"Nav script: {step} -> {(_ui!.Top is { } panel ? $"{panel.Name} '{panel.Heading}', focus {GetViewport().GuiGetFocusOwner()?.Name ?? "none"}" : _navigator!.Describe())} (frame {Engine.GetFramesDrawn()})");
    }

    private void AfterWarmUp()
    {
        if (_options.NavScript.Count > 0)
        {
            _navScriptStep = 0;
        }

        var services = _services!;
        if (_options.LaunchRequested)
        {
            Launch().StartDebugLaunch(_options);
            return;
        }

        if (_options.BenchRequested && _options.BenchScenario == BenchScenario.Scroll)
        {
            _scrollBench = new ScrollBench(_navigator!, _streamer, _options, services);
            return;
        }

        if (_options.StartSystem is { } start && !_navigator!.EnterSystem(start, _options.StartIndex))
        {
            GD.PushWarning($"--start-system: '{start}' isn't in the systems grid.");
        }

        if (_options.Open is { } open)
        {
            OpenForDebug(open);
        }

        // A3: nothing is scanned at boot. Systems that have never been scanned are scanned now, in the background
        // (but not during a bench, which measures a library as it is).
        if (!_options.BenchRequested)
        {
            var unscanned = new List<string>();
            foreach (var system in services.Systems)
            {
                if (system.ScannedAt is null)
                {
                    unscanned.Add(system.SystemId);
                }
            }

            // Covers with no derivative (the user's own art, or art from an earlier version) are baked after the
            // scans, or now if there are none (M4).
            _navigator!.BakeAfterScans = true;
            _ = services.CheckInstallsAsync();
            if (unscanned.Count > 0)
            {
                _navigator.Rescan(unscanned.Count == services.Systems.Count ? null : unscanned);
            }
            else
            {
                _navigator.BakeDerivatives();
            }
        }
    }

    /// <summary>
    /// The settings screen and what it drives (M7), built in the warm-up after interactive: the job runner (rescans
    /// and scrapes with progress, which the navigator's rescans use too), the progress cards, and the controller.
    /// </summary>
    private void BuildSettings()
    {
        var services = _services!;
        var navigator = _navigator!;
        _jobs = new LibraryJobs(services, _queue);
        navigator.Jobs = _jobs;
        navigator.InputSuspended = () => _ui!.IsOpen;
        var hud = new JobsHud(_jobs.Jobs);
        AddChild(hud);
        var context = new UiContext(_ui!, _queue, PlatformServices.CreateFileLocations(services.Paths.HomeDir), services.Paths.HomeDir,
            services.Paths.DataDir, () => services.Config.Settings.RomRoot, PlatformServices.CreateImageDecoder());
        _settings = new SettingsController(services, context, _jobs) { Rescan = navigator.Rescan };
        _settings.ConfigApplied += config =>
        {
            _launch?.ApplyConfig(config);
            navigator.OnConfigChanged();
            _statusBar?.Apply(config.Settings.Ui);
        };
        _settings.ThemeChosen += id =>
        {
            if (id != navigator.ThemeId)
            {
                navigator.SwitchTheme(id);
            }
        };
        navigator.SettingsRequested += () =>
        {
            if (!_ui!.IsOpen)
            {
                _settings.Open();
            }
        };

        // X on a system or a game: its options (M7 part 2). Scrapes and edits rename games in the grid in place.
        var options = new ItemOptions(_settings, navigator);
        _settings.Options = options;
        navigator.SystemOptionsRequested += id =>
        {
            if (!_ui!.IsOpen)
            {
                options.OpenSystem(id);
            }
        };
        navigator.GameOptionsRequested += id =>
        {
            if (!_ui!.IsOpen)
            {
                options.OpenGame(id);
            }
        };
        _jobs.GamesUpdated += navigator.OnGamesUpdated;
        _jobs.GameDeleted += navigator.OnGameDeleted;

        // Y on a game: its details, with its images and video full size.
        _videoDecoder = PlatformServices.CreateVideoDecoder();
        navigator.GameDetailsRequested += id =>
        {
            if (!_ui!.IsOpen)
            {
                GameDetailsPanel.Open(context, services, _videoDecoder, id, navigator.RefreshDetails);
            }
        };

        // Y on a system: its details, with its card's model large.
        navigator.SystemDetailsRequested += entry =>
        {
            if (!_ui!.IsOpen)
            {
                SystemDetailsPanel.Open(context, services, () => navigator.Theme, entry);
            }
        };

        // View (Select) or P in the grids: restart, shut down or sleep the system, or quit.
        navigator.PowerRequested += () =>
        {
            if (!_ui!.IsOpen)
            {
                OpenPowerMenu();
            }
        };
        _ui!.Blocked = () => _launch?.IsInputBlocked ?? false;

        // The overlay's text is about the grid (its controls, the focused game), so it steps aside for the settings.
        // The progress cards too: the settings screen lists the jobs itself, where a pad can cancel them.
        _ui.Opened += () =>
        {
            _overlay!.Visible = false;
            hud.Visible = false;
        };
        _ui.AllClosed += () =>
        {
            _overlay!.Visible = !_options.NoOverlay;
            hud.Visible = true;
        };

        // A full-screen image or video has the whole window: the status indicators step aside for it.
        _ui.TopChanged += ShowStatusBar;
    }

    private void ShowStatusBar()
    {
        if (_statusBar is { } bar)
        {
            bar.Visible = !_options.NoOverlay && _ui?.Top is not { FullScreen: true };
        }
    }

    /// <summary>
    /// The status indicators, top right (time, battery, network), and the monitor that reads the device's state on the
    /// thread pool, delivering it only when it changes; paused while a game runs. Built in the warm-up, after the
    /// launch controller and after the glyphs, whose frames are the warm-up's dearest.
    /// </summary>
    private void BuildStatusBar()
    {
        // First uses cost milliseconds, so they happen on the thread pool: the local time zone (DateTime.Now reads it
        // from the registry), the culture's time format, the icons, and the monitor (System.Net.NetworkInformation's
        // first load). Only the nodes are made on the main thread, once that's done.
        var fake = _options.FakeStatus;
        _ = Task.Run(() =>
        {
            _ = DateTime.Now.ToString("t", System.Globalization.CultureInfo.CurrentCulture);
            var icons = StatusBar.LoadIcons();
            var monitor = new DeviceStatusMonitor(fake is { } status ? new FixedDeviceStatus(status) : PlatformServices.CreateDeviceStatus());
            _queue.Post(() =>
            {
                if (_shutdown.IsCancellationRequested)
                {
                    monitor.Dispose();
                    return;
                }

                var bar = new StatusBar(icons);
                AddChild(bar);
                bar.Apply(_services!.Config.Settings.Ui);
                _statusBar = bar;
                ShowStatusBar();
                monitor.Changed += status => _queue.Post(() => bar.Show(status));
                _deviceStatus = monitor;
                _settings!.DeviceStatus = monitor;
                if (_launch is { } launch)
                {
                    launch.GameModeEntered += monitor.Pause;
                    launch.GameModeLeft += monitor.Resume;
                }

                _ = Task.Run(monitor.Start);
            });
        });
    }

    private void OpenPowerMenu() =>
        _ui!.Push(new PowerMenu(_power ??= PlatformServices.CreatePowerControl(), _queue, () => GetTree().Quit()));

    /// <summary>
    /// The nav script's input steps: real events through <see cref="Input.ParseInputEvent"/>, as the mouse and
    /// keyboard send them, so a capture checks the mouse and typing paths too.
    /// </summary>
    private void SendInput(string step)
    {
        switch (step)
        {
            case "click" when GetViewport().GuiGetFocusOwner() is { } control:
                var at = control.GetGlobalRect().GetCenter();
                Input.ParseInputEvent(new InputEventMouseMotion { Position = at, GlobalPosition = at });
                foreach (var pressed in (ReadOnlySpan<bool>)[true, false])
                {
                    Input.ParseInputEvent(new InputEventMouseButton { ButtonIndex = MouseButton.Left, Pressed = pressed, Position = at, GlobalPosition = at });
                }

                break;
            case "scroll":
                var middle = GetViewport().GetVisibleRect().GetCenter();
                Input.ParseInputEvent(new InputEventMouseMotion { Position = middle, GlobalPosition = middle });
                for (var notch = 0; notch < 3; notch++)
                {
                    Input.ParseInputEvent(new InputEventMouseButton { ButtonIndex = MouseButton.WheelDown, Pressed = true, Position = middle, GlobalPosition = middle, Factor = 1 });
                    Input.ParseInputEvent(new InputEventMouseButton { ButtonIndex = MouseButton.WheelDown, Pressed = false, Position = middle, GlobalPosition = middle, Factor = 1 });
                }

                break;
            case "type":
                foreach (var c in "Ok 1")
                {
                    var key = c == ' ' ? Key.Space : c is >= '0' and <= '9' ? Key.Key0 + (c - '0') : Key.A + (char.ToUpperInvariant(c) - 'A');
                    foreach (var pressed in (ReadOnlySpan<bool>)[true, false])
                    {
                        Input.ParseInputEvent(new InputEventKey { Keycode = key, PhysicalKeycode = key, Unicode = c, Pressed = pressed, ShiftPressed = char.IsUpper(c) });
                    }
                }

                break;
        }
    }

    /// <summary>
    /// The nav script's <c>turn</c>: the right stick's position, as a joypad's motion events. From a device of its own:
    /// a real pad (the Deck's controls) sends its sticks' motion all the time, and on the same device would undo it.
    /// </summary>
    private void SendTurn(float x, float y)
    {
        const int device = 15;
        Input.ParseInputEvent(new InputEventJoypadMotion { Device = device, Axis = JoyAxis.RightX, AxisValue = x });
        Input.ParseInputEvent(new InputEventJoypadMotion { Device = device, Axis = JoyAxis.RightY, AxisValue = y });
        _navScriptTurning = x != 0 || y != 0;
    }

    /// <summary><c>--open</c>: shows a settings screen or component for a capture.</summary>
    private void OpenForDebug(string target)
    {
        var settings = _settings!;
        var context = settings.Ui;
        var start = _options.OpenPath;
        switch (target)
        {
            case "settings":
                settings.Open();
                break;
            case "keyboard":
                OnScreenKeyboard.Open(_ui!, new KeyboardRequest("Type a path", OperatingSystem.IsWindows() ? @"\\nas\roms\Mega Drive" : "/home/me/ROMs", text => GD.Print($"Keyboard: done, '{text}'."),
                    Subtitle: @"A folder, or a network share (\\server\share)", Placeholder: @"D:\ROMs"));
                break;
            case "folder-picker":
                FilePicker.Open(context, new PickerRequest("Choose a folder", PickerMode.Folder, "debug-folder", path => GD.Print($"Picker: chose {path}."), Start: start));
                break;
            case "image-picker":
                FilePicker.Open(context, new PickerRequest("Choose an image", PickerMode.File, "debug-image", path => GD.Print($"Picker: chose {path}."),
                    Filter: Launcher.Core.Files.FileFilter.Images, Start: start, Thumbnails: true));
                break;
            case "program-picker":
                FilePicker.Open(context, new PickerRequest("Choose the emulator's program", PickerMode.File, "debug-program", path => GD.Print($"Picker: chose {path}."),
                    Filter: Launcher.Core.Files.FileFilter.Executables, Start: start));
                break;
            case "confirm":
                settings.Open();
                ConfirmDialog.Ask(_ui!, "Remove this folder?", @"D:\ROMs\Mega Drive" + "\n\nMega Drive won't be scanned there any more, and its games from there leave the library (their favourites and play history are kept, for if you add it back).",
                    "Remove it", "Keep it", yes => GD.Print($"Confirm: {(yes ? "yes" : "no")}."), destructive: true);
                break;
            case "power":
                OpenPowerMenu();
                break;
            case "progress":
                // A job with made-up numbers, so the card and its row can be captured mid-run.
                var job = _jobs!.Jobs.Start("demo", "Scraping missing metadata (--open=progress)", "games", () => GD.Print("Progress: cancel pressed."));
                job.Report(412, 3000, 3);
                job.SetNote("IGDB has no Twitch application credentials, so it's skipped.");
                _jobs.Jobs.End(_jobs.Jobs.Start("demo", "Scanning your ROM folders", "systems", null), JobState.Finished, "Done: 12 new games, 0 removed.");
                break;
            case "match":
                OpenMatchForDebug();
                break;
            case "details":
                OpenDetailsForDebug();
                break;
            case "running":
                Launch().ShowRunningScreenForDebug("Example Game");
                break;
        }
    }

    /// <summary>
    /// <c>--open=details</c>: the details screen of the game at <c>--start-index</c> of <c>--start-system</c>, as Y opens
    /// it (its id read off the main thread).
    /// </summary>
    private void OpenDetailsForDebug()
    {
        var services = _services!;
        var context = _settings!.Ui;
        var system = _options.StartSystem;
        var index = _options.StartIndex ?? 0;
        _ = Task.Run(async () =>
        {
            long? id = null;
            if (system is not null)
            {
                var list = await services.Library.GetGamesAsync(system, CancellationToken.None).ConfigureAwait(false);
                if (list.Games.Count > 0)
                {
                    id = list.Games[Math.Clamp(index, 0, list.Games.Count - 1)].GameId;
                }
            }

            context.Queue.Post(() =>
            {
                if (id is null)
                {
                    GD.PushWarning("--open=details needs --start-system with games in it.");
                    return;
                }

                GameDetailsPanel.Open(context, services, _videoDecoder, id.Value, () => _navigator?.RefreshDetails());
            });
        });
    }

    /// <summary>
    /// <c>--open=match</c>: the game options and the match panel over made-up results, for the game at
    /// <c>--start-index</c> of <c>--start-system</c> (read off the main thread). Nothing is searched or scraped.
    /// </summary>
    private void OpenMatchForDebug()
    {
        var library = _services!.Library;
        var options = _settings!.Options!;
        var queue = _settings.Ui.Queue;
        var system = _options.StartSystem;
        var index = _options.StartIndex ?? 0;
        _ = Task.Run(async () =>
        {
            Launcher.Core.Library.GameDetails? game = null;
            if (system is not null)
            {
                var list = await library.GetGamesAsync(system, CancellationToken.None).ConfigureAwait(false);
                if (list.Games.Count > 0)
                {
                    game = await library.GetGameAsync(list.Games[Math.Clamp(index, 0, list.Games.Count - 1)].GameId, CancellationToken.None).ConfigureAwait(false);
                }
            }

            queue.Post(() =>
            {
                if (game is null)
                {
                    GD.PushWarning("--open=match needs --start-system with games in it.");
                    return;
                }

                // The match panel a frame later, as when the options' row opens it.
                _ui!.Push(new GameOptionsPanel(options, game));
                GetTree().CreateTimer(0).Timeout += () => _ui.Push(new GameMatchPanel(options, game,
                    (provider, id) => GD.Print($"Match: would scrape with {provider} {id}."),
                    GameMatchPanel.MadeUpResults(game, options.SystemName(game.Key.SystemId))));
            });
        });
    }

    /// <summary>
    /// The launch controller, built in the warm-up (building it at boot cost 10–24 ms of start-up:
    /// docs/perf/m3-launching.md), or on first use by --launch.
    /// </summary>
    private LaunchController Launch()
    {
        if (_launch is not null)
        {
            return _launch;
        }

        _launch = new LaunchController(_services!);
        AddChild(_launch);
        if (_navigator is { } navigator)
        {
            _launch.GameModeEntered += navigator.OnGameModeEntered;
            _launch.GameModeLeft += navigator.OnGameModeLeft;
            _launch.LaunchEnded += navigator.FinishLaunch;
        }

        return _launch;
    }

    /// <summary>The glyph warm-up: 3 font sizes, printable ASCII in 3 parts of 32 characters, one part a frame.</summary>
    private const int GlyphChunks = 3;
    private const int GlyphSteps = 3 * GlyphChunks;

    /// <summary>
    /// Draws a part of printable ASCII once at a font size, so its glyphs are rasterised now rather than the first
    /// time a title needs them. The glyph cache is shared, so a small hidden viewport is enough. Anything beyond ASCII
    /// is rasterised when first shown: all of Latin-1 at every UI size cost about 130 MB and a 150–220 ms frame, and
    /// all of ASCII at one size up to 39 ms (docs/perf/m5-navigation.md).
    /// </summary>
    private static SubViewport GlyphWarmUp(int fontSize, int chunk)
    {
        var text = new System.Text.StringBuilder(32);
        for (var c = 0x20 + chunk * 32; c < Math.Min(0x7F, 0x20 + (chunk + 1) * 32); c++)
        {
            text.Append((char)c);
        }

        var viewport = new SubViewport { Size = new Vector2I(16, 16), RenderTargetUpdateMode = SubViewport.UpdateMode.Once, TransparentBg = true, Disable3D = true };
        viewport.AddChild(new Label { Text = text.ToString(), LabelSettings = new LabelSettings { FontSize = fontSize } });
        return viewport;
    }

    // ---- Display ----------------------------------------------------------------------------------

    private void OnViewportSizeChanged()
    {
        GD.Print($"Display: the window is now {DisplayServer.WindowGetSize().X}x{DisplayServer.WindowGetSize().Y} ({DisplayServer.WindowGetMode()}), frame {Engine.GetFramesDrawn()}.");
        ApplyRenderScale();
        UpdateGridViews();
    }

    private void UpdateGridViews()
    {
        var size = GetViewport().GetVisibleRect().Size;
        var aspect = size.Y > 0 ? size.X / size.Y : 1.6f;
        var height = 2 * CameraDistance * Mathf.Tan(Mathf.DegToRad(FieldOfView / 2));
        _systemsGrid?.SetView(height, aspect, CameraDistance);
        _gamesGrid?.SetView(height, aspect, CameraDistance);
    }

    /// <summary>A3: at most 1080p for 3D (half resolution at 4K), bilinear unless --upscaler says otherwise.</summary>
    private void ApplyRenderScale()
    {
        var viewport = GetViewport();
        var windowHeight = DisplayServer.WindowGetSize().Y;
        var scale = _options.RenderScale ?? (windowHeight > MaxRenderHeight ? (double)MaxRenderHeight / windowHeight : 1.0);
        viewport.Scaling3DScale = (float)scale;
        viewport.Scaling3DMode = _options.Upscaler == Upscaler.Fsr ? Viewport.Scaling3DModeEnum.Fsr : Viewport.Scaling3DModeEnum.Bilinear;
        DebugHooks.RenderScale = scale;
    }

    /// <summary>
    /// settings.toml's <c>[display] fullscreen</c>, unless the command line chose a window (or a debug facility is
    /// measuring one).
    /// </summary>
    private void ApplyDisplaySettings(AppConfig config)
    {
        if (_options.IsActive || !config.Settings.Display.Fullscreen)
        {
            return;
        }

        foreach (var arg in OS.GetCmdlineArgs())
        {
            if (arg is "--resolution" or "--fullscreen" or "-f" or "--windowed" or "-w" or "--maximized" or "-m" or "--position" or "--screen" or "-e" or "--editor")
            {
                return;
            }
        }

        DisplayServer.WindowSetMode(DisplayServer.WindowMode.Fullscreen);
    }
}
