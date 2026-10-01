using System.Globalization;
using Launcher.Core.Platform;

namespace Launcher.Core.Launching;

/// <summary>
/// A game Steam runs, followed through what the Steam client reports (<see cref="ISteamClient"/>), because the
/// process the launcher starts only hands the shortcut to Steam (ARCHITECTURE.md A1, Launching):
/// <list type="bullet">
/// <item>The game is running while Steam's current game is this app, or while the app's own running flag is set,
/// that flag being trusted only once it has been seen clear (Steam can leave it set after a crash), and only while
/// the client runs.</item>
/// <item>It has ended once it's been seen running, then not running at two polls in a row.</item>
/// <item>If it isn't seen running within the start timeout, not counting time Steam spends updating it, it never
/// started: <see cref="ProcessOutcome.NotStarted"/> says why.</item>
/// </list>
/// The game isn't the launcher's to end, so <see cref="Terminate"/> stops following it and leaves it to Steam.
/// </summary>
public sealed class SteamGame : IRunningProcess
{
    /// <summary>Not running at this many polls in a row ends it, so a game that restarts itself isn't cut short.</summary>
    private const int EndPolls = 2;

    private readonly ISteamClient _steam;
    private readonly uint _appId;
    private readonly long _startTimestamp;
    private readonly TimeProvider _clock;
    private readonly TimeSpan _pollInterval;
    private readonly TimeSpan _startTimeout;
    private readonly Func<TimeSpan, Task> _delay;
    private readonly TaskCompletionSource _wake = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private volatile bool _terminated;
    private volatile bool _detached;

    /// <param name="startTimestamp">When the launch started, from <paramref name="clock"/>'s <c>GetTimestamp</c>.</param>
    /// <param name="delay">Waits between polls; by default <paramref name="clock"/>'s timers.</param>
    public SteamGame(
        ISteamClient steam,
        uint appId,
        long startTimestamp,
        TimeProvider clock,
        TimeSpan pollInterval,
        TimeSpan startTimeout,
        Func<TimeSpan, Task>? delay = null)
    {
        _steam = steam ?? throw new ArgumentNullException(nameof(steam));
        _clock = clock ?? throw new ArgumentNullException(nameof(clock));
        _appId = appId;
        _startTimestamp = startTimestamp;
        _pollInterval = pollInterval;
        _startTimeout = startTimeout;
        _delay = delay ?? (duration => Task.Delay(duration, clock));
        Completion = Task.Run(FollowAsync);
    }

    /// <summary>0: Steam started the game, and the launcher doesn't know its process.</summary>
    public int ProcessId => 0;

    public Task<ProcessOutcome> Completion { get; }

    /// <summary>Stops following the game, which keeps running in Steam's hands. <see cref="Completion"/> reports <c>Terminated</c>.</summary>
    public void Terminate()
    {
        _terminated = true;
        _wake.TrySetResult();
    }

    /// <summary>Stops following; if the game hasn't ended, <see cref="Completion"/> is cancelled.</summary>
    public void Dispose()
    {
        _detached = true;
        _wake.TrySetResult();
    }

    private async Task<ProcessOutcome> FollowAsync()
    {
        var trustFlag = false;
        var started = false;
        var notRunning = 0;
        var waited = TimeSpan.Zero;
        var seenClient = false;
        var seenInstalled = false;
        var last = _clock.GetTimestamp();
        while (true)
        {
            if (_terminated)
            {
                return new ProcessOutcome(0, Elapsed, Terminated: true);
            }

            if (_detached)
            {
                throw new OperationCanceledException("The launcher stopped following the Steam game.");
            }

            var state = Read();
            seenClient |= state.ClientRunning;
            seenInstalled |= state.Installed;
            trustFlag |= !state.Running || state.Current;
            var running = state.ClientRunning && (state.Current || (state.Running && trustFlag));

            var now = _clock.GetTimestamp();
            var sinceLast = _clock.GetElapsedTime(last, now);
            last = now;
            if (running)
            {
                started = true;
                notRunning = 0;
            }
            else if (started)
            {
                if (++notRunning >= EndPolls)
                {
                    return new ProcessOutcome(0, Elapsed, Terminated: false);
                }
            }
            else if (!state.Updating)
            {
                waited += sinceLast;
                if (waited >= _startTimeout)
                {
                    return new ProcessOutcome(0, Elapsed, Terminated: false, NotStarted(seenClient, seenInstalled));
                }
            }

            await Task.WhenAny(_delay(_pollInterval), _wake.Task).ConfigureAwait(false);
        }
    }

    private TimeSpan Elapsed => _clock.GetElapsedTime(_startTimestamp);

    /// <summary>A registry or file the client can't read counts as "nothing running", never as a fault.</summary>
    private SteamAppState Read()
    {
        try
        {
            return _steam.GetAppState(_appId);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or System.Security.SecurityException)
        {
            return default;
        }
    }

    private string NotStarted(bool seenClient, bool seenInstalled)
    {
        var within = _startTimeout.TotalSeconds >= 120 && _startTimeout.TotalSeconds % 60 == 0
            ? string.Create(CultureInfo.InvariantCulture, $"{_startTimeout.TotalMinutes:0} minutes")
            : string.Create(CultureInfo.InvariantCulture, $"{_startTimeout.TotalSeconds:0} s");
        if (!seenClient)
        {
            return $"Steam didn't open within {within}. Start Steam and sign in, then launch the game again.";
        }

        return seenInstalled
            ? $"Steam didn't start the game within {within}. Steam may be waiting for you (a launch option, an agreement or " +
              "a sign-in), or the game closed before Steam saw it run."
            : $"Steam didn't start the game within {within}, and says it isn't installed. Install it in Steam, then launch it again.";
    }
}
