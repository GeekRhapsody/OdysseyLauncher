using System.Globalization;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Platform;

namespace Launcher.Core.Launching;

public enum LaunchStatus
{
    /// <summary>The game ran and ended (<see cref="LaunchService.Exited"/>).</summary>
    Exited,

    /// <summary>The game didn't run (<see cref="LaunchService.Failed"/>).</summary>
    Failed,
}

public enum LaunchFailure
{
    None,

    /// <summary>No usable emulator profile: unknown system or emulator, or a template problem.</summary>
    Config,

    /// <summary>The ROM, executable, core or working folder doesn't exist.</summary>
    MissingFile,

    /// <summary>The OS refused to start the executable.</summary>
    StartRefused,

    /// <summary>It started, then exited with a non-zero code within <see cref="LaunchService.QuickExitThreshold"/>.</summary>
    QuickExit,
}

/// <summary>The result of one <see cref="LaunchService.LaunchAsync"/>.</summary>
/// <param name="Reason">For a failure: what went wrong, written for the user.</param>
/// <param name="HistoryError">Set if the play session couldn't be recorded. The game still ran.</param>
public sealed record LaunchOutcome(
    GameKey Game,
    LaunchStatus Status,
    LaunchFailure Failure,
    string? Reason,
    LaunchPlan? Plan,
    int? ExitCode,
    TimeSpan Duration,
    bool Terminated,
    string? HistoryError);

public sealed class LaunchStartingEventArgs(GameDetails game, LaunchPlan plan) : EventArgs
{
    public GameDetails Game { get; } = game;

    public LaunchPlan Plan { get; } = plan;
}

public sealed class LaunchRunningEventArgs(GameDetails game, LaunchPlan plan, int processId) : EventArgs
{
    public GameDetails Game { get; } = game;

    public LaunchPlan Plan { get; } = plan;

    /// <summary>The process the runner started, for <see cref="IWindowFocus.BeforeLaunch"/>.</summary>
    public int ProcessId { get; } = processId;
}

public sealed class LaunchExitedEventArgs(GameDetails game, LaunchOutcome outcome) : EventArgs
{
    public GameDetails Game { get; } = game;

    public LaunchOutcome Outcome { get; } = outcome;

    public int ExitCode => Outcome.ExitCode ?? -1;

    public TimeSpan Duration => Outcome.Duration;
}

public sealed class LaunchFailedEventArgs(GameDetails game, LaunchOutcome outcome) : EventArgs
{
    public GameDetails Game { get; } = game;

    public LaunchOutcome Outcome { get; } = outcome;

    /// <summary>Written for the user.</summary>
    public string Reason => Outcome.Reason!;
}

/// <summary>
/// Runs games and records their play sessions (ARCHITECTURE.md A1). One game at a time.
/// <para>
/// Events are raised on worker threads, never on the caller's: hand them to the main thread yourself. Handlers must
/// not throw. Each launch raises, in order:
/// <list type="bullet">
/// <item><see cref="Starting"/>, once the plan is made and its files exist, just before the process starts;</item>
/// <item><see cref="Running"/>, once it has started;</item>
/// <item>then exactly one of <see cref="Exited"/> or <see cref="Failed"/>. Failed can come without the others (nothing
/// started), or after them (the emulator exited with an error straight away).</item>
/// </list>
/// </para>
/// </summary>
public sealed class LaunchService
{
    private readonly IProcessRunner _runner;
    private readonly IPlayHistory _history;
    private readonly TimeProvider _clock;
    private AppConfig _config;
    private int _running;

    public LaunchService(AppConfig config, IProcessRunner runner, IPlayHistory history, TimeProvider? clock = null)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));
        _runner = runner ?? throw new ArgumentNullException(nameof(runner));
        _history = history ?? throw new ArgumentNullException(nameof(history));
        _clock = clock ?? TimeProvider.System;
    }

    public event EventHandler<LaunchStartingEventArgs>? Starting;

    public event EventHandler<LaunchRunningEventArgs>? Running;

    public event EventHandler<LaunchExitedEventArgs>? Exited;

    public event EventHandler<LaunchFailedEventArgs>? Failed;

    /// <summary>Config for the next launch.</summary>
    public AppConfig Config
    {
        get => Volatile.Read(ref _config);
        set => Volatile.Write(ref _config, value ?? throw new ArgumentNullException(nameof(value)));
    }

    /// <summary>
    /// A non-zero exit sooner than this is reported as a failed launch, and doesn't count as a play. Some emulators
    /// return non-zero after a normal session too, so it's kept short.
    /// </summary>
    public TimeSpan QuickExitThreshold { get; set; } = TimeSpan.FromSeconds(5);

    public bool IsRunning => Volatile.Read(ref _running) != 0;

    /// <summary>
    /// Launches <paramref name="game"/> and completes when it has ended (after <see cref="Exited"/> or
    /// <see cref="Failed"/>). Cancelling after the game has started ends the game: it's reported as Exited, with
    /// <see cref="LaunchOutcome.Terminated"/> set, and the session is recorded.
    /// </summary>
    /// <param name="emulatorOverride">An emulator chosen for this launch only; null uses the game's, then the system's.</param>
    /// <exception cref="InvalidOperationException">A game is already running.</exception>
    public async Task<LaunchOutcome> LaunchAsync(GameDetails game, string? emulatorOverride, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(game);
        cancellationToken.ThrowIfCancellationRequested();
        if (Interlocked.Exchange(ref _running, 1) != 0)
        {
            throw new InvalidOperationException("A game is already running.");
        }

        // File checks and process creation block, so none of it runs on the caller's thread, and neither do the events.
        return await Task.Run(
            async () =>
            {
                LaunchOutcome outcome;
                try
                {
                    outcome = await RunAsync(game, emulatorOverride, cancellationToken).ConfigureAwait(false);
                }
                finally
                {
                    Volatile.Write(ref _running, 0);
                }

                // Raised once the next launch is allowed, so a handler can start one.
                if (outcome.Status == LaunchStatus.Exited)
                {
                    Exited?.Invoke(this, new LaunchExitedEventArgs(game, outcome));
                }
                else
                {
                    Failed?.Invoke(this, new LaunchFailedEventArgs(game, outcome));
                }

                return outcome;
            },
            CancellationToken.None).ConfigureAwait(false);
    }

    private async Task<LaunchOutcome> RunAsync(GameDetails game, string? emulatorOverride, CancellationToken cancellationToken)
    {
        var planned = LaunchPlanner.Plan(Config, game, emulatorOverride);
        if (planned.Plan is not { } plan)
        {
            return Fail(game, null, LaunchFailure.Config, planned.Error!);
        }

        if (MissingFile(game, plan) is { } missing)
        {
            return Fail(game, plan, LaunchFailure.MissingFile, missing);
        }

        Starting?.Invoke(this, new LaunchStartingEventArgs(game, plan));
        var startedAt = _clock.GetUtcNow();
        IRunningProcess process;
        try
        {
            process = _runner.Start(plan);
        }
        catch (ProcessStartException e)
        {
            return Fail(game, plan, LaunchFailure.StartRefused, $"{plan.EmulatorName} couldn't start. {e.Message}");
        }
        catch (Exception e) when (e is ArgumentException or IOException or UnauthorizedAccessException or InvalidOperationException)
        {
            // Starting was raised, so a terminal event must follow whatever went wrong.
            return Fail(game, plan, LaunchFailure.StartRefused, $"{plan.EmulatorName} couldn't start: {e.Message}");
        }

        using (process)
        {
            Running?.Invoke(this, new LaunchRunningEventArgs(game, plan, process.ProcessId));

            string? historyError = null;
            long? sessionId = null;
            try
            {
                sessionId = await _history.BeginSessionAsync(game.Key, plan.EmulatorId, startedAt, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e) when (e is not OperationCanceledException)
            {
                historyError = $"The play session couldn't be recorded: {e.Message}";
            }

            ProcessOutcome result;
            using (cancellationToken.Register(static state => ((IRunningProcess)state!).Terminate(), process))
            {
                result = await process.Completion.ConfigureAwait(false);
            }

            var quickExit = result.ExitCode != 0 && !result.Terminated && result.Elapsed < QuickExitThreshold;
            if (sessionId is { } id)
            {
                try
                {
                    await _history.EndSessionAsync(
                        new PlaySessionEnd(id, game.Key, startedAt, result.Elapsed, result.ExitCode, CountAsPlay: !quickExit),
                        CancellationToken.None).ConfigureAwait(false);
                }
                catch (Exception e) when (e is not OperationCanceledException)
                {
                    historyError = $"The play session couldn't be recorded: {e.Message}";
                }
            }

            if (quickExit)
            {
                var seconds = result.Elapsed.TotalSeconds.ToString("0.0", CultureInfo.InvariantCulture);
                return Fail(game, plan, LaunchFailure.QuickExit,
                    $"{plan.EmulatorName} closed after {seconds} s with exit code {FormatExitCode(result.ExitCode)}, so the game " +
                    $"probably didn't start. {ExitCodeHint(result.ExitCode)}",
                    result.ExitCode, result.Elapsed, historyError);
            }

            return new LaunchOutcome(
                game.Key, LaunchStatus.Exited, LaunchFailure.None, null, plan, result.ExitCode, result.Elapsed, result.Terminated, historyError);
        }
    }

    /// <summary>The first file the launch needs that isn't there, as a message for the user.</summary>
    private static string? MissingFile(GameDetails game, LaunchPlan plan)
    {
        if (!File.Exists(game.RomPath))
        {
            return $"The game's file is missing: '{game.RomPath}'. Reconnect the drive it's on, or rescan the system if it has moved.";
        }

        if (!plan.RunFile && !File.Exists(plan.Executable))
        {
            return $"{plan.EmulatorName} isn't installed at '{plan.Executable}'. Install it there, or fix the path in " +
                "emulators.toml (or the variable it uses in settings.toml).";
        }

        if (plan.Core is { } core && !File.Exists(core))
        {
            return $"The core '{core}' for {plan.EmulatorName} doesn't exist. Install it (in RetroArch: Online Updater, " +
                "Core Downloader), or fix core in emulators.toml.";
        }

        if (!Directory.Exists(plan.WorkingDirectory))
        {
            return $"The working folder '{plan.WorkingDirectory}' for {plan.EmulatorName} doesn't exist. Check working_dir in emulators.toml.";
        }

        return null;
    }

    /// <summary>A failed outcome; <see cref="LaunchAsync"/> raises <see cref="Failed"/> for it.</summary>
    private static LaunchOutcome Fail(
        GameDetails game,
        LaunchPlan? plan,
        LaunchFailure failure,
        string reason,
        int? exitCode = null,
        TimeSpan duration = default,
        string? historyError = null) =>
        new(game.Key, LaunchStatus.Failed, failure, reason, plan, exitCode, duration, false, historyError);

    /// <summary>Windows reports crashes as NTSTATUS codes, which read better in hex.</summary>
    internal static string FormatExitCode(int code) =>
        code is < 0 or > 0xFFFF
            ? string.Create(CultureInfo.InvariantCulture, $"0x{unchecked((uint)code):X8}")
            : code.ToString(CultureInfo.InvariantCulture);

    private static string ExitCodeHint(int code) => unchecked((uint)code) switch
    {
        0xC0000005 => "It crashed (access violation).",
        0xC0000135 => "A DLL it needs is missing: reinstall the emulator, or install the runtime it asks for.",
        0xC000007B => "It, or a DLL it loads, is built for the wrong kind of processor (32-bit and 64-bit mixed).",
        0xC0000409 => "It stopped itself after an internal error.",
        _ => "Check the emulator's own log: the ROM may be unsupported, or a BIOS or core may be missing.",
    };
}
