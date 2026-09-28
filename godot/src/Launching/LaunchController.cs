using System;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Launching;
using Launcher.Core.Library;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Windows;
using Launcher.Core.Scanning;
using Timer = Godot.Timer;

namespace Launcher.App.Launching;

/// <summary>
/// Hands the machine to the emulator while a game runs, and takes it back afterwards (ARCHITECTURE.md A1):
/// <list type="number">
/// <item>Starting: the render loop stops, the engine idles at 10 iterations a second in low-processor mode, the
/// tree pauses (no animation or processing), the master bus mutes and input is ignored.</item>
/// <item>Running: the emulator may take the foreground. Once it has (or after 10 s), the launcher minimises without
/// activating anything, so no unrelated window comes forward in between.</item>
/// <item>Exited or failed: everything above is undone, the window is restored and brought to the foreground
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
    private const ulong MinimiseTimeoutMs = 10_000;
    private const ulong InputGraceMs = 500;
    private const double MessageSeconds = 10.0;

    private readonly CancellationTokenSource _shutdown = new();
    private IWindowFocus _focus = NullWindowFocus.Instance;
    private nint _window;
    private LibraryService? _library;
    private LaunchService? _service;
    private Timer _foregroundTimer = null!;
    private Timer _messageTimer = null!;
    private Label _message = null!;
    private bool _gameMode;
    private bool _minimised;
    private bool _quitAfterLaunch;
    private ulong _runningSinceMs;
    private ulong _endedAtMs;
    private ulong _inputBlockedUntilMs;
    private SavedState _saved;

    /// <summary>
    /// True while a game runs and just after it. The navigation input router (M5) must drop input while this is set;
    /// until then, <see cref="_Input"/> swallows what it can.
    /// </summary>
    public bool IsInputBlocked => _gameMode || Time.GetTicksMsec() < _inputBlockedUntilMs;

    public override void _Ready()
    {
        // Keeps working while the tree is paused for a game.
        ProcessMode = ProcessModeEnum.Always;

        // Godot turns input processing on at READY because _Input is defined. It stays off until input needs
        // swallowing: every event reaching C# allocates a wrapper, and the Deck's controls send joypad motion
        // all the time (an always-on _Input cost about 1.9 KB per frame on the main thread).
        SetProcessInput(false);

        var headless = DisplayServer.GetName() == "headless";
        _window = headless ? 0 : (nint)DisplayServer.WindowGetNativeHandle(DisplayServer.HandleType.WindowHandle);
        _focus = headless ? NullWindowFocus.Instance : PlatformServices.CreateWindowFocus();

        _foregroundTimer = new Timer { WaitTime = ForegroundPollSeconds, OneShot = false };
        _foregroundTimer.Timeout += OnForegroundPoll;
        AddChild(_foregroundTimer);

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
    }

    public override void _ExitTree()
    {
        _shutdown.Cancel();
        if (_gameMode)
        {
            LeaveGameMode();
        }

        // The token source isn't disposed: the background launch may still be looking at its token.
        _library?.Dispose();
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
    /// <c>--launch=&lt;system&gt;/&lt;rel path&gt;</c>: loads config and the library off the main thread, rescans the
    /// system if the game isn't in the library yet, and launches it.
    /// </summary>
    public void StartDebugLaunch(DebugOptions options)
    {
        _quitAfterLaunch = options.QuitAfterLaunch;
        var executableDir = Path.GetDirectoryName(OS.GetExecutablePath()) ?? ".";
        var token = _shutdown.Token;
        _ = Task.Run(() => DebugLaunchAsync(options, executableDir, token), token);
    }

    private async Task DebugLaunchAsync(DebugOptions options, string executableDir, CancellationToken cancellationToken)
    {
        try
        {
            var home = System.Environment.GetFolderPath(System.Environment.SpecialFolder.UserProfile);
            var paths = options.UserDir is { } userDir ? PlatformPaths.InOneFolder(userDir, home) : PlatformPaths.Detect(executableDir);
            GD.Print($"Launch: config in {paths.ConfigDir}, data in {paths.DataDir}");

            var loaded = new ConfigLoader().Load(ConfigSources.FromDirectory(paths.ConfigDir, paths.HomeDir));
            foreach (var diagnostic in loaded.Diagnostics)
            {
                GD.Print(diagnostic.ToString());
            }

            _library = await LibraryService.OpenAsync(loaded.Config, paths.DataDir, null, cancellationToken).ConfigureAwait(false);
            if (_library.ClosedOrphanSessions > 0)
            {
                GD.Print($"Launch: closed {_library.ClosedOrphanSessions} play session(s) left open by a crash.");
            }

            var key = new GameKey(options.LaunchSystem!, PathKeys.ToPathKey(PathKeys.ToRelPath(options.LaunchRelPath!)));
            var game = await _library.GetGameAsync(key, cancellationToken).ConfigureAwait(false);
            if (game is null && loaded.Config.FindSystem(key.SystemId) is not null)
            {
                GD.Print($"Launch: {options.LaunchSystem}/{options.LaunchRelPath} isn't in the library yet, so {key.SystemId} is being scanned.");
                await _library.RescanAsync(key.SystemId, null, cancellationToken).ConfigureAwait(false);
                game = await _library.GetGameAsync(key, cancellationToken).ConfigureAwait(false);
            }

            if (game is null)
            {
                var reason = loaded.Config.FindSystem(key.SystemId) is null
                    ? $"'{key.SystemId}' isn't an enabled system."
                    : $"There's no '{options.LaunchRelPath}' in {key.SystemId}'s ROM folders.";
                CallDeferred(MethodName.OnLaunchEnded, true, reason);
                return;
            }

            _service = new LaunchService(loaded.Config, PlatformServices.CreateProcessRunner(), _library);
            _service.Starting += (_, e) =>
            {
                GD.Print($"Launch: {e.Game.Title} with {e.Plan.EmulatorName}: {CommandLine(e.Plan)}");
                CallDeferred(MethodName.OnStarting);
            };
            _service.Running += (_, e) => CallDeferred(MethodName.OnRunning, e.ProcessId);
            _service.Exited += (_, e) => CallDeferred(
                MethodName.OnLaunchEnded,
                false,
                string.Create(CultureInfo.InvariantCulture, $"{e.Game.Title} ended after {e.Duration.TotalSeconds:0.0} s (exit code {e.ExitCode})."));
            _service.Failed += (_, e) => CallDeferred(MethodName.OnLaunchEnded, true, e.Reason);

            var outcome = await _service.LaunchAsync(game, null, cancellationToken).ConfigureAwait(false);
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

    private void OnStarting() => EnterGameMode();

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
        if (!lost && waited < MinimiseTimeoutMs)
        {
            return;
        }

        _foregroundTimer.Stop();
        _focus.Minimise(_window);
        _minimised = true;
        GD.Print(lost
            ? $"Launch: the emulator took the foreground after {waited} ms, so the launcher minimised."
            : $"Launch: the emulator didn't take the foreground within {MinimiseTimeoutMs} ms, so the launcher minimised anyway.");
    }

    private void OnLaunchEnded(bool failed, string message)
    {
        _foregroundTimer.Stop();
        if (_gameMode)
        {
            _endedAtMs = Time.GetTicksMsec();
            LeaveGameMode();
            var result = _focus.AfterExit(_window);
            if (_minimised && DisplayServer.WindowGetMode() != _saved.WindowMode)
            {
                DisplayServer.WindowSetMode(_saved.WindowMode);
            }

            GD.Print($"Launch: back in the launcher; foreground: {result}.");
            if (result is ForegroundResult.AlreadyForeground or ForegroundResult.NotSupported)
            {
                // No focus-in is coming; don't report a later, unrelated one.
                _endedAtMs = 0;
            }
        }

        _minimised = false;
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

        if (_quitAfterLaunch)
        {
            GetTree().Quit(failed ? 1 : 0);
        }
    }

    private void ShowMessage(string text)
    {
        _message.Text = text;
        _message.Visible = true;
        _messageTimer.Start();
    }

    private void EnterGameMode()
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
        SetProcessInput(true);

        RenderingServer.RenderLoopEnabled = false;
        OS.LowProcessorUsageMode = true;
        OS.LowProcessorUsageModeSleepUsec = IdleSleepUsec;
        Engine.MaxFps = IdleMaxFps;
        GetTree().Paused = true;
        AudioServer.SetBusMute(0, true);
        GetViewport().GuiDisableInput = true;
    }

    private void LeaveGameMode()
    {
        _gameMode = false;
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
