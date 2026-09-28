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
using Launcher.App.Screens;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.Core;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;

namespace Launcher.App.Boot;

/// <summary>
/// The main scene (A1 Boot, A3 boot path). Boots straight into the systems grid:
/// <list type="number">
/// <item>On the thread pool: settings and systems config, then library.db and the systems query.</item>
/// <item>Meanwhile on the main thread: the look, the camera, the cover array, the grids and the overlay, with the
/// built-in models loading on Godot's loader threads.</item>
/// <item>When both are done, the systems grid is bound; the next drawn frame is <c>interactive</c>.</item>
/// <item>After that, a warm-up spread over a few frames: every pipeline drawn once, the first cover upload, the
/// glyphs, and the launch controller. Nothing is scanned at boot; systems never scanned are scanned after it.</item>
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
    private readonly TemplateLibrary _models = new();
    private DebugOptions _options = DebugOptions.None;
    private AppServices? _services;
    private Exception? _bootFailure;
    private Camera3D _camera = null!;
    private TextureStreamer? _streamer;
    private ItemGrid? _systemsGrid;
    private ItemGrid? _gamesGrid;
    private InfoOverlay? _overlay;
    private Navigator? _navigator;
    private LaunchController? _launch;
    private ScrollBench? _scrollBench;
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
        var options = _options;
        var token = _shutdown.Token;
        _ = Task.Run(async () =>
        {
            try
            {
                _services = await AppServices.LoadAsync(options, executableDir, token).ConfigureAwait(false);
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
        _models.Request(ConfigLoader.GameModels);
        _camera = new Camera3D { Fov = FieldOfView, Position = new Vector3(0, 0, CameraDistance), Current = true };
        AddChild(_camera);
        Look.Default.Build(this, _camera);
        ApplyRenderScale();
        GetViewport().SizeChanged += OnViewportSizeChanged;

        // Pool textures are created at boot and only updated while browsing (A3).
        if (!_options.NoTextures)
        {
            _streamer = new TextureStreamer(CoverSlots, TextureStreamer.DefaultWorkers);
            _streamer.CreateArray();

            // The first layer update can take tens of milliseconds (M1), so it's done now, while the DB opens, rather
            // than in the first frames after interactive.
            _streamer.WarmUpload();
        }


        _overlay = new InfoOverlay();
        AddChild(_overlay);
    }

    public override void _ExitTree()
    {
        _shutdown.Cancel();
        if (_waitingForFirstFrame)
        {
            RenderingServer.FramePostDraw -= OnFramePostDraw;
        }

        _scrollBench?.Dispose();
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

        var modelsReady = _models.Poll();
        if (modelsReady)
        {
            DebugHooks.Timeline.Mark(BootMarks.ModelsLoaded);
        }

        if (_services is not { } services || !modelsReady)
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
        _streamer?.SetFolders(services.Paths.CacheDir, services.Paths.ConfigDir, services.Paths.DataDir);

        var clock = System.Diagnostics.Stopwatch.StartNew();
        var templates = new List<ItemMesh>();
        foreach (var id in ConfigLoader.GameModels)
        {
            templates.Add(_models.Get(id));
        }

        _gamesGrid = new ItemGrid(templates, _streamer, Look.Default, CoverSlots, blockSize: 160, spines: true, tintCase: false)
        {
            RowsVisible = GameRowsVisible,
            Name = "Games",
        };
        // Every system fits in the pool, with room for the columns to change; the virtual systems are 2 more.
        var systemSlots = Math.Clamp(services.Systems.Count + 2 + ItemGrid.MaxColumns, 24, MaxSystemSlots);
        _systemsGrid = new ItemGrid([_models.Get(TemplateLibrary.GenericSystemId)], null, Look.Default, systemSlots, blockSize: 192, spines: false, tintCase: true)
        {
            RowsVisible = SystemRowsVisible,
            Name = "Systems",
        };
        var gridsMs = clock.Elapsed.TotalMilliseconds;
        AddChild(_systemsGrid);
        AddChild(_gamesGrid);
        var addMs = clock.Elapsed.TotalMilliseconds;
        UpdateGridViews();
        ApplyDisplaySettings(services.Config);
        DebugHooks.Timeline.Mark(BootMarks.SceneBuilt);

        _navigator = new Navigator(services, _queue, _systemsGrid, _gamesGrid, _overlay!, ConfigLoader.GameModels)
        {
            Streamer = _streamer,
        };
        AddChild(_navigator);
        _navigator.ShowSystems(0);

        // Every template's pipeline is drawn in the first frame, faded into the background (A3), so it's compiled
        // before interactive rather than in a hitch just after it.
        _gamesGrid.BeginWarmUp();
        DebugHooks.Timeline.Mark(BootMarks.SystemsGridBound);
        GD.Print(FormattableString.Invariant($"Boot: grids built in {gridsMs:0.0} ms, added in {addMs - gridsMs:0.0} ms, bound in {clock.Elapsed.TotalMilliseconds - addMs:0.0} ms."));

        var games = 0;
        foreach (var system in services.Systems)
        {
            games += system.GameCount;
        }

        DebugHooks.Library = new BenchLibrary(services.Systems.Count + 2, games, null, 0);
        GCSettings.LatencyMode = GCLatencyMode.SustainedLowLatency;
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
                _stage = Stage.Running;
                DebugHooks.Timeline.Mark(BootMarks.WarmUpDone);
                AfterWarmUp();
                break;
        }
    }

    private int _navScriptStep = -1;
    private int _navScriptWait;

    /// <summary>--nav-script: one step every few frames, through the navigator as the controller would.</summary>
    private void StepNavScript()
    {
        if (_navScriptStep < 0 || _navScriptStep >= _options.NavScript.Count || ++_navScriptWait < DebugOptions.NavScriptStepFrames)
        {
            return;
        }

        _navScriptWait = 0;
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
            _ => NavCommand.None,
        };
        if (command != NavCommand.None)
        {
            _navigator!.Run(command);
        }

        GD.Print($"Nav script: {step} -> {_navigator!.Describe()} (frame {Engine.GetFramesDrawn()})");
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

            if (unscanned.Count > 0)
            {
                _navigator!.Rescan(unscanned.Count == services.Systems.Count ? null : unscanned);
            }
        }
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
