using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Launching;
using Launcher.Core.Launching.Controllers;
using Launcher.Core.Library;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Windows;
using Launcher.Core.Scanning;
using Timer = Godot.Timer;

namespace Launcher.App.Launching;

/// <summary>
/// Hands the machine to the emulator while a game runs, and takes it back afterwards (ARCHITECTURE.md A1):
/// <list type="number">
/// <item>Starting: the tree pauses (no animation or processing), the master bus mutes, input is ignored, and the
/// window turns black with "Running" and the game's title in the middle. Once that has been drawn, the render loop
/// stops and the engine idles at 10 iterations a second in low-processor mode; the window keeps showing it.</item>
/// <item>Running: the emulator may take the foreground. The launcher stays as it is behind it (it isn't minimised).</item>
/// <item>Exited or failed: everything above is undone, the window is brought to the foreground
/// (<see cref="IWindowFocus.AfterExit"/>), and input stays ignored for a moment after focus returns, so the
/// button press that quit the emulator doesn't also act in the launcher.</item>
/// </list>
/// LaunchService events arrive on worker threads and reach this node through <c>CallDeferred</c>.
/// </summary>
public partial class LaunchController : Node
{
    private const int IdleMaxFps = 10;
    private const int IdleSleepUsec = 100_000;
    private const double ForegroundPollSeconds = 0.25;
    private const ulong ForegroundTimeoutMs = 10_000;

    /// <summary>Frames drawn with the running screen before the render loop stops, so it's surely on screen.</summary>
    private const int RunningScreenFrames = 2;

    /// <summary>The longest the running screen waits for those frames: a headless or minimised window draws none.</summary>
    private const ulong RunningScreenTimeoutMs = 500;

    private const ulong InputGraceMs = 500;

    /// <summary>
    /// While the shell keeps the window cloaked after a game: the wait before each check, and how many times
    /// <see cref="IWindowFocus.Uncloak"/> is tried.
    /// </summary>
    private const double UncloakCheckSeconds = 0.3;
    private const int UncloakAttempts = 3;
    private const double MessageSeconds = 10.0;

    private readonly CancellationTokenSource _shutdown = new();
    private readonly AppServices _services;
    private IWindowFocus _focus = NullWindowFocus.Instance;
    private nint _window;
    private LaunchService? _service;
    private Timer _foregroundTimer = null!;
    private Timer _messageTimer = null!;
    private Timer _uncloakTimer = null!;
    private int _uncloakAttempts;
    private ulong _uncloakFromMs;
    private Label _message = null!;
    private CanvasLayer _runningScreen = null!;
    private Label _runningTitle = null!;
    private bool _gameMode;
    private bool _idling;
    private int _idleAfterFrame;
    private ulong _idleByMs;
    private bool _quitAfterLaunch;
    private ulong _runningSinceMs;
    private ulong _endedAtMs;
    private ulong _inputBlockedUntilMs;
    private SavedState _saved;

    public LaunchController(AppServices services)
    {
        _services = services;
        Name = "Launch";
    }

    /// <summary>
    /// True while a game runs and just after it. The navigator drops its input while this is set, and
    /// <see cref="_Input"/> swallows what reaches the GUI.
    /// </summary>
    public bool IsInputBlocked => _gameMode || Time.GetTicksMsec() < _inputBlockedUntilMs;

    /// <summary>True while a game runs (textures are evicted then, once the running screen is up).</summary>
    public bool InGameMode => _gameMode;

    public override void _Ready()
    {
        // Keeps working while the tree is paused for a game.
        ProcessMode = ProcessModeEnum.Always;

        // Godot turns input processing on at READY because _Input is defined. It stays off until input needs
        // swallowing: every event reaching C# allocates a wrapper, and the Deck's controls send joypad motion
        // all the time (an always-on _Input cost about 1.9 KB per frame on the main thread).
        SetProcessInput(false);

        // _Process runs only while the running screen is being drawn, before the render loop stops.
        SetProcess(false);

        var headless = DisplayServer.GetName() == "headless";
        _window = headless ? 0 : (nint)DisplayServer.WindowGetNativeHandle(DisplayServer.HandleType.WindowHandle);
        _focus = headless ? NullWindowFocus.Instance : PlatformServices.CreateWindowFocus();

        _foregroundTimer = new Timer { WaitTime = ForegroundPollSeconds, OneShot = false };
        _foregroundTimer.Timeout += OnForegroundPoll;
        AddChild(_foregroundTimer);

        _uncloakTimer = new Timer { WaitTime = UncloakCheckSeconds, OneShot = true };
        _uncloakTimer.Timeout += OnUncloakTimer;
        AddChild(_uncloakTimer);

        _messageTimer = new Timer { WaitTime = MessageSeconds, OneShot = true };
        _messageTimer.Timeout += () => _message.Visible = false;
        AddChild(_messageTimer);

        _message = new Label
        {
            Visible = false,
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            HorizontalAlignment = HorizontalAlignment.Center,
        };
        var layer = new CanvasLayer { Layer = 2 };
        layer.AddChild(_message);
        AddChild(layer);
        _message.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.TopWide, Control.LayoutPresetMode.KeepSize, 24);

        // Above everything else, the status indicators included.
        _runningScreen = new CanvasLayer { Layer = 100, Visible = false, Name = "RunningScreen" };
        var black = new ColorRect { Color = Colors.Black, MouseFilter = Control.MouseFilterEnum.Ignore };
        black.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _runningScreen.AddChild(black);
        _runningTitle = new Label
        {
            LabelSettings = new LabelSettings { FontSize = 30, FontColor = Colors.White },
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            MouseFilter = Control.MouseFilterEnum.Ignore,
        };
        _runningTitle.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.FullRect, Control.LayoutPresetMode.Minsize, 44);
        _runningScreen.AddChild(_runningTitle);
        AddChild(_runningScreen);
    }

    /// <summary>Only while the running screen is being drawn: once it has been (or after a time limit), the launcher idles.</summary>
    public override void _Process(double delta)
    {
        if (_gameMode && !_idling && (Engine.GetFramesDrawn() >= _idleAfterFrame || Time.GetTicksMsec() >= _idleByMs))
        {
            Idle();
        }
    }

    public override void _ExitTree()
    {
        _shutdown.Cancel();
        if (_gameMode)
        {
            LeaveGameMode();
        }

        // The token source isn't disposed: the background launch may still be looking at its token.
        // The library belongs to AppServices.
    }

    /// <summary>Only while <see cref="IsInputBlocked"/>; it turns itself off at the first event after that.</summary>
    public override void _Input(InputEvent @event)
    {
        if (IsInputBlocked)
        {
            GetViewport().SetInputAsHandled();
        }
        else
        {
            SetProcessInput(false);
        }
    }

    public override void _Notification(int what)
    {
        if (what != NotificationApplicationFocusIn || _gameMode)
        {
            return;
        }

        // The grace period runs from when focus actually comes back, which may be later than the restore.
        var now = Time.GetTicksMsec();
        if (_inputBlockedUntilMs != 0)
        {
            _inputBlockedUntilMs = now + InputGraceMs;
        }

        if (_endedAtMs != 0)
        {
            GD.Print($"Launch: the launcher has keyboard focus again, {now - _endedAtMs} ms after the game ended.");
            _endedAtMs = 0;
        }
    }

    /// <summary>
    /// Raised on the main thread once a game has started and the running screen is up: the navigator frees its
    /// textures. <see cref="GameModeLeft"/> follows only if this was raised.
    /// </summary>
    public event Action? GameModeEntered;

    /// <summary>Raised on the main thread when the launcher is back: the navigator restores its textures.</summary>
    public event Action? GameModeLeft;

    /// <summary>Raised on the main thread when a launch is over; the message is the failure, or null if the game ran.</summary>
    public event Action<string?>? LaunchEnded;

    /// <summary>
    /// <c>--launch=&lt;system&gt;/&lt;rel path&gt;</c>: rescans the system if the game isn't in the library yet,
    /// then launches it.
    /// </summary>
    public void StartDebugLaunch(DebugOptions options)
    {
        _quitAfterLaunch = options.QuitAfterLaunch;
        var token = _shutdown.Token;
        var pads = Gamepads.Snapshot(-1);
        _ = Task.Run(() => DebugLaunchAsync(options, pads, token), token);
    }

    /// <summary>Main thread: config changed (M7's settings screen); the next launch uses it.</summary>
    public void ApplyConfig(AppConfig config)
    {
        lock (_shutdown)
        {
            if (_service is not null)
            {
                _service.Config = config;
            }
        }
    }

    /// <summary>Main thread: launches a game the player picked.</summary>
    /// <param name="pad">The pad the game was chosen with (<see cref="Gamepads.Pressing"/>), or -1: player 1 if its controllers are set up.</param>
    public void Launch(GameDetails game, int pad)
    {
        var token = _shutdown.Token;
        var pads = Gamepads.Snapshot(pad);
        _ = Task.Run(() => LaunchAsync(game, pads, token), token);
    }

    private async Task DebugLaunchAsync(DebugOptions options, List<Gamepad> pads, CancellationToken cancellationToken)
    {
        try
        {
            var library = _services.Library;
            var config = _services.Config;
            var key = new GameKey(options.LaunchSystem!, PathKeys.ToPathKey(PathKeys.ToRelPath(options.LaunchRelPath!)));
            var game = await library.GetGameAsync(key, cancellationToken).ConfigureAwait(false);
            if (game is null && config.FindSystem(key.SystemId) is not null)
            {
                GD.Print($"Launch: {options.LaunchSystem}/{options.LaunchRelPath} isn't in the library yet, so {key.SystemId} is being scanned.");
                await library.RescanAsync(key.SystemId, null, cancellationToken).ConfigureAwait(false);
                game = await library.GetGameAsync(key, cancellationToken).ConfigureAwait(false);
            }

            if (game is null)
            {
                var reason = config.FindSystem(key.SystemId) is null
                    ? $"'{key.SystemId}' isn't an enabled system."
                    : $"There's no '{options.LaunchRelPath}' in {key.SystemId}'s ROM folders.";
                CallDeferred(MethodName.OnLaunchEnded, true, reason);
                return;
            }

            await LaunchAsync(game, pads, cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // The launcher is closing.
        }
        catch (Exception e)
        {
            CallDeferred(MethodName.OnLaunchEnded, true, $"The launch failed unexpectedly: {e.Message}");
        }
    }

    private async Task LaunchAsync(GameDetails game, List<Gamepad> pads, CancellationToken cancellationToken)
    {
        try
        {
            var outcome = await Service().LaunchAsync(game, null, pads, cancellationToken).ConfigureAwait(false);
            if (outcome.HistoryError is { } historyError)
            {
                GD.PrintErr($"Launch: {historyError}");
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // The launcher is closing.
        }
        catch (Exception e)
        {
            CallDeferred(MethodName.OnLaunchEnded, true, $"The launch failed unexpectedly: {e.Message}");
        }
    }

    /// <summary>Built on first use, with its event handlers; thread-safe.</summary>
    private LaunchService Service()
    {
        lock (_shutdown)
        {
            if (_service is not null)
            {
                return _service;
            }

            var service = new LaunchService(
                _services.Config, PlatformServices.CreateProcessRunner(), _services.Library, steam: PlatformServices.CreateSteamClient());
            service.Starting += (_, e) =>
            {
                if (e.Controllers is { } controllers)
                {
                    GD.Print($"Launch controllers for {e.Plan.EmulatorName}: {controllers.Describe()}");
                }

                if (e.ControllerError is { } controllerError)
                {
                    GD.PrintErr($"Launch: {controllerError}");
                }

                GD.Print($"Launch: {e.Game.Title} with {e.Plan.EmulatorName}: {CommandLine(e.Plan)}");
                CallDeferred(MethodName.OnStarting, e.Game.Title);
            };
            service.Running += (_, e) => CallDeferred(MethodName.OnRunning, e.ProcessId);
            service.Exited += (_, e) => CallDeferred(
                MethodName.OnLaunchEnded,
                false,
                string.Create(CultureInfo.InvariantCulture, $"{e.Game.Title} ended after {e.Duration.TotalSeconds:0.0} s (exit code {e.ExitCode})."));
            service.Failed += (_, e) => CallDeferred(MethodName.OnLaunchEnded, true, e.Reason);
            _service = service;
            return service;
        }
    }

    /// <summary>The plan as one line, quoted the way the emulator receives it, for the log.</summary>
    private static string CommandLine(LaunchPlan plan)
    {
        if (OperatingSystem.IsWindows())
        {
            return WindowsCommandLine.Build(plan.Executable, plan.Arguments);
        }

        var line = new StringBuilder(plan.Executable);
        foreach (var argument in plan.Arguments)
        {
            line.Append(" '").Append(argument.Replace("'", "'\\''", StringComparison.Ordinal)).Append('\'');
        }

        return line.ToString();
    }

    // ---- Main thread, through CallDeferred ------------------------------------------------------

    private void OnStarting(string title)
    {
        EnterGameMode(title);
    }

    private void OnRunning(int processId)
    {
        _focus.BeforeLaunch(_window, processId);
        _runningSinceMs = Time.GetTicksMsec();
        _foregroundTimer.Start();
    }

    private void OnForegroundPoll()
    {
        var waited = Time.GetTicksMsec() - _runningSinceMs;
        var lost = _focus.HasLostForeground(_window);
        if (!lost && waited < ForegroundTimeoutMs)
        {
            return;
        }

        _foregroundTimer.Stop();
        GD.Print(lost
            ? $"Launch: the emulator took the foreground after {waited} ms."
            : $"Launch: the emulator didn't take the foreground within {ForegroundTimeoutMs} ms.");
    }

    private void OnLaunchEnded(bool failed, string message)
    {
        _foregroundTimer.Stop();
        if (_gameMode)
        {
            _endedAtMs = Time.GetTicksMsec();
            var entered = _idling;
            LeaveGameMode();
            var result = _focus.AfterExit(_window);
            if (DisplayServer.WindowGetMode() != _saved.WindowMode)
            {
                // The player minimised it while the game ran, and AfterExit restored it.
                GD.Print($"Launch: the window mode is {DisplayServer.WindowGetMode()}, so it's set back to {_saved.WindowMode}.");
                DisplayServer.WindowSetMode(_saved.WindowMode);
            }

            if (_focus.IsCloaked(_window))
            {
                LogWindowState("cloaked after the game");
                _uncloakAttempts = 1;
                _uncloakFromMs = _endedAtMs;
                _focus.Uncloak(_window);
                _uncloakTimer.Start();
            }
            else if (result == ForegroundResult.Failed)
            {
                LogWindowState("foreground refused");
            }

            if (entered)
            {
                GameModeLeft?.Invoke();
            }

            GD.Print($"Launch: back in the launcher; foreground: {result}.");
            if (result is ForegroundResult.AlreadyForeground or ForegroundResult.NotSupported)
            {
                // No focus-in is coming; don't report a later, unrelated one.
                _endedAtMs = 0;
            }
        }

        _inputBlockedUntilMs = Time.GetTicksMsec() + InputGraceMs;
        if (failed)
        {
            GD.PrintErr($"Launch failed: {message}");
            ShowMessage($"Couldn't launch the game. {message}");
        }
        else
        {
            GD.Print($"Launch: {message}");
        }

        LaunchEnded?.Invoke(failed ? message : null);
        if (_quitAfterLaunch)
        {
            GetTree().Quit(failed ? 1 : 0);
        }
    }

    /// <summary>
    /// After a game in Windows' full screen experience, booted into: the shell leaves the launcher cloaked (a black
    /// screen) although it has the foreground, until it's minimised and restored (<see cref="IWindowFocus.Uncloak"/>).
    /// Each tick checks, and tries again while it's still cloaked.
    /// </summary>
    private void OnUncloakTimer()
    {
        if (_gameMode)
        {
            return;
        }

        if (!_focus.IsCloaked(_window))
        {
            GD.Print($"Launch: the launcher window is shown again, {Time.GetTicksMsec() - _uncloakFromMs} ms after the game ended ({_uncloakAttempts} minimise and restore).");
            if (DisplayServer.WindowGetMode() != _saved.WindowMode)
            {
                DisplayServer.WindowSetMode(_saved.WindowMode);
            }

            return;
        }

        if (_uncloakAttempts >= UncloakAttempts)
        {
            GD.PrintErr($"Launch: the shell kept the launcher window hidden after {UncloakAttempts} minimise and restore; switching apps shows it.");
            LogWindowState("still cloaked");
            return;
        }

        _uncloakAttempts++;
        _focus.Uncloak(_window);
        _uncloakTimer.Start();
    }

    /// <summary>
    /// Logs the window's state as Godot and Windows see it, when the launcher doesn't come back cleanly after a game.
    /// Never per frame.
    /// </summary>
    private void LogWindowState(string when)
    {
        GD.Print(string.Create(
            CultureInfo.InvariantCulture,
            $"Launch window ({when}): godot mode={DisplayServer.WindowGetMode()} focused={DisplayServer.WindowIsFocused()} " +
            $"can_draw={DisplayServer.WindowCanDraw()} drawn={Engine.GetFramesDrawn()} size={DisplayServer.WindowGetSize()}; {_focus.Describe(_window)}"));
    }

    private void ShowMessage(string text)
    {
        _message.Text = text;
        _message.Visible = true;
        _messageTimer.Start();
    }

    /// <summary>
    /// <c>--open=running</c>: the running screen alone, for a capture. Nothing is launched and the launcher keeps
    /// drawing; the screen stays up until the app quits.
    /// </summary>
    public void ShowRunningScreenForDebug(string title) => ShowRunningScreen(title);

    private void ShowRunningScreen(string title)
    {
        _runningTitle.Text = $"Running {title}";
        _runningScreen.Visible = true;
    }

    /// <summary>
    /// The first half of game mode: everything stops but drawing, and the running screen goes up. <see cref="Idle"/>
    /// does the rest once it has been drawn.
    /// </summary>
    private void EnterGameMode(string title)
    {
        _saved = new SavedState(
            OS.LowProcessorUsageMode,
            OS.LowProcessorUsageModeSleepUsec,
            Engine.MaxFps,
            GetTree().Paused,
            AudioServer.IsBusMute(0),
            GetViewport().GuiDisableInput,
            DisplayServer.WindowGetMode());
        _gameMode = true;
        _idling = false;
        SetProcessInput(true);

        GetTree().Paused = true;
        AudioServer.SetBusMute(0, true);
        GetViewport().GuiDisableInput = true;
        ShowRunningScreen(title);

        // The frame being built now may not have the screen yet; the ones after it do.
        _idleAfterFrame = Engine.GetFramesDrawn() + 1 + RunningScreenFrames;
        _idleByMs = Time.GetTicksMsec() + RunningScreenTimeoutMs;
        SetProcess(true);
    }

    /// <summary>
    /// The running screen has been drawn: the render loop stops (the window keeps showing its last frame), the engine
    /// idles, and the navigator frees its textures.
    /// </summary>
    private void Idle()
    {
        SetProcess(false);
        _idling = true;
        RenderingServer.RenderLoopEnabled = false;
        OS.LowProcessorUsageMode = true;
        OS.LowProcessorUsageModeSleepUsec = IdleSleepUsec;
        Engine.MaxFps = IdleMaxFps;
        GameModeEntered?.Invoke();
    }

    private void LeaveGameMode()
    {
        SetProcess(false);
        _gameMode = false;
        _idling = false;
        _runningScreen.Visible = false;
        OS.LowProcessorUsageMode = _saved.LowProcessor;
        OS.LowProcessorUsageModeSleepUsec = _saved.SleepUsec;
        Engine.MaxFps = _saved.MaxFps;
        GetTree().Paused = _saved.Paused;
        AudioServer.SetBusMute(0, _saved.Muted);
        GetViewport().GuiDisableInput = _saved.GuiDisabled;
        RenderingServer.RenderLoopEnabled = true;
    }

    /// <summary>What game mode changes, so it can be put back exactly.</summary>
    private readonly record struct SavedState(
        bool LowProcessor,
        int SleepUsec,
        int MaxFps,
        bool Paused,
        bool Muted,
        bool GuiDisabled,
        DisplayServer.WindowMode WindowMode);
}
