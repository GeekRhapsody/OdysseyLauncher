using System.Collections.Concurrent;
using Launcher.Core.Config;
using Launcher.Core.Launching;
using Launcher.Core.Library;
using Launcher.Core.Platform;
using Launcher.Core.Scanning;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Launching;

/// <summary>
/// Steam games are handed to Steam and followed through what the Steam client reports, with a scripted client:
/// first <see cref="SteamGame"/> alone on a clock the polls move, then the launch service end to end with the
/// built-in <c>steam</c> and <c>windows</c> systems and the library.
/// </summary>
public sealed class SteamGameTests : IAsyncLifetime
{
    private const uint AppId = 1260320;
    private const string Shortcut = "[InternetShortcut]\r\nURL=steam://rungameid/1260320\r\n";

    private static readonly TimeSpan Poll = TimeSpan.FromSeconds(1);
    private static readonly TimeSpan Timeout = TimeSpan.FromMinutes(2);

    private static readonly SteamAppState Idle = new(ClientRunning: true, Installed: true, Running: false, Current: false, Updating: false);
    private static readonly SteamAppState Playing = Idle with { Running = true, Current = true };

    private readonly TempDir _dir = new();
    private readonly ManualClock _wallClock = new(new DateTimeOffset(2026, 10, 1, 10, 0, 0, TimeSpan.Zero));
    private readonly ConcurrentQueue<string> _events = new();
    private readonly FakeRunner _runner = new();
    private readonly FakeSteam _steam = new();
    private LibraryService _library = null!;
    private LaunchService _launcher = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private string DataDir => _dir.Combine("data");

    public async ValueTask InitializeAsync()
    {
        _dir.File("ROMs/steam/Party Animals.url", Shortcut);
        _dir.File("ROMs/steam/Spacewar.lnk", "not read");
        _dir.File("ROMs/windows/Website.url", "[InternetShortcut]\r\nURL=https://example.com/\r\n");
        _dir.File("ROMs/windows/Steam game.url", Shortcut);
        var config = LoadConfig();
        _library = await LibraryService.OpenAsync(config, DataDir, _wallClock, Ct);
        await _library.RescanAsync("steam", null, Ct);
        await _library.RescanAsync("windows", null, Ct);
        _launcher = NewLauncher(config, _steam);
    }

    public ValueTask DisposeAsync()
    {
        _library.Dispose();
        SqliteConnection.ClearAllPools();
        _dir.Dispose();
        return ValueTask.CompletedTask;
    }

    private AppConfig LoadConfig()
    {
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = _dir.Path,
            ConfigDir = _dir.Combine("config"),
            Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = '{_dir.Combine("ROMs")}'\n"),
            FileExists = null,
        });
        Assert.False(result.HasErrors, string.Join('\n', result.Diagnostics));
        return result.Config;
    }

    private LaunchService NewLauncher(AppConfig config, ISteamClient? steam)
    {
        var launcher = new LaunchService(config, _runner, _library, _wallClock, steam)
        {
            SteamPollInterval = TimeSpan.FromMilliseconds(10),
            SteamStartTimeout = TimeSpan.FromMilliseconds(300),
        };
        launcher.Starting += (_, _) => _events.Enqueue("starting");
        launcher.Running += (_, _) => _events.Enqueue("running");
        launcher.Exited += (_, _) => _events.Enqueue("exited");
        launcher.Failed += (_, _) => _events.Enqueue("failed");
        return launcher;
    }

    private static GameKey Key(string system, string relPath) => new(system, PathKeys.ToPathKey(relPath));

    private async Task<LaunchOutcome> Launch(string system, string relPath, LaunchService? launcher = null) =>
        await (launcher ?? _launcher).LaunchAsync((await _library.GetGameAsync(Key(system, relPath), Ct))!, null, Ct);

    private int SessionCount()
    {
        using var connection = new SqliteConnection($"Data Source={Path.Combine(DataDir, LibraryService.UserDataFileName)};Mode=ReadOnly;Pooling=False");
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT COUNT(*) FROM play_sessions WHERE ended_at IS NOT NULL AND emulator = 'run-file'";
        return Convert.ToInt32(command.ExecuteScalar(), System.Globalization.CultureInfo.InvariantCulture);
    }

    // ---- SteamGame on its own ---------------------------------------------------------------------

    /// <summary>Follows <paramref name="steam"/>'s script, one state a poll, on a clock each poll moves by <see cref="Poll"/>.</summary>
    private static SteamGame Follow(FakeSteam steam, StepClock clock) =>
        new(steam, AppId, clock.GetTimestamp(), clock, Poll, Timeout, async duration =>
        {
            await Task.Yield();
            clock.Advance(duration);
        });

    [Fact]
    public async Task A_game_is_followed_from_when_steam_runs_it_until_steam_says_it_has_ended()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Idle, 5), Repeat(Playing, 30), Repeat(Idle, 1));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Equal(new ProcessOutcome(0, TimeSpan.FromSeconds(36), Terminated: false), outcome);
        Assert.Equal(0, game.ProcessId);
    }

    [Fact]
    public async Task One_poll_without_the_game_doesnt_end_it()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Playing, 10), Repeat(Idle, 1), Repeat(Playing, 10), Repeat(Idle, 1));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Equal(TimeSpan.FromSeconds(22), outcome.Elapsed);
    }

    [Fact]
    public async Task The_apps_own_running_flag_counts_without_it_being_steams_current_game()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Idle, 2), Repeat(Idle with { Running = true }, 10), Repeat(Idle, 1));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Null(outcome.NotStarted);
        Assert.Equal(TimeSpan.FromSeconds(13), outcome.Elapsed);
    }

    [Fact]
    public async Task A_running_flag_left_set_from_before_counts_only_once_it_has_cleared()
    {
        // Steam can leave an app's Running flag set after a crash: it isn't the game running.
        var stale = Idle with { Running = true };
        var steam = new FakeSteam();
        steam.Script(Repeat(stale, 20), Repeat(Idle, 3), Repeat(stale, 10), Repeat(Idle, 1));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Null(outcome.NotStarted);
        Assert.Equal(TimeSpan.FromSeconds(34), outcome.Elapsed);
    }

    [Fact]
    public async Task A_game_already_running_is_followed_to_its_end()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Playing, 8), Repeat(Playing with { Current = false }, 4), Repeat(Idle, 1));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Equal(TimeSpan.FromSeconds(13), outcome.Elapsed);
    }

    [Fact]
    public async Task Nothing_counts_as_running_while_the_steam_client_isnt()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Playing with { ClientRunning = false }, 200));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Equal(TimeSpan.FromSeconds(120), outcome.Elapsed);
        Assert.StartsWith("Steam didn't open within 2 minutes. Start Steam and sign in", outcome.NotStarted, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_game_steam_never_runs_hasnt_started_after_the_timeout()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Idle, 500));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Equal(TimeSpan.FromSeconds(120), outcome.Elapsed);
        Assert.StartsWith("Steam didn't start the game within 2 minutes. Steam may be waiting for you", outcome.NotStarted, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_game_steam_says_isnt_installed_is_named_as_such()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Idle with { Installed = false }, 500));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.EndsWith("and says it isn't installed. Install it in Steam, then launch it again.", outcome.NotStarted, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Time_steam_spends_updating_the_game_doesnt_count_towards_the_timeout()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Idle, 60), Repeat(Idle with { Updating = true }, 600), Repeat(Idle, 30), Repeat(Playing, 5), Repeat(Idle, 1));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.Null(outcome.NotStarted);
        Assert.Equal(TimeSpan.FromSeconds(696), outcome.Elapsed);
    }

    [Fact]
    public async Task Terminating_stops_following_and_leaves_the_game_to_steam()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Playing, 10_000));
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        await steam.Polled(5).WaitAsync(Ct);
        game.Terminate();
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.True(outcome.Terminated);
        Assert.Null(outcome.NotStarted);
    }

    [Fact]
    public async Task Disposing_while_the_game_runs_cancels_its_completion()
    {
        var steam = new FakeSteam();
        steam.Script(Repeat(Playing, 10_000));
        var clock = new StepClock();

        var game = Follow(steam, clock);
        await steam.Polled(5).WaitAsync(Ct);
        game.Dispose();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => game.Completion.WaitAsync(Ct));
    }

    [Fact]
    public async Task A_client_that_cant_be_read_counts_as_nothing_running_rather_than_a_fault()
    {
        var steam = new FakeSteam { Throws = true };
        var clock = new StepClock();

        using var game = Follow(steam, clock);
        var outcome = await game.Completion.WaitAsync(Ct);

        Assert.NotNull(outcome.NotStarted);
    }

    // ---- The launch service -------------------------------------------------------------------------

    [Fact]
    public void Windows_and_steam_are_built_in_systems_whose_games_run_their_own_files()
    {
        var config = LoadConfig();
        foreach (var id in new[] { "windows", "steam" })
        {
            var system = config.FindSystem(id)!;
            Assert.Equal("run-file", system.Emulator);
            Assert.Contains(".url", system.Extensions);
            Assert.Contains(".lnk", system.Extensions);
            Assert.Contains(".bat", system.Extensions);
            Assert.DoesNotContain(".exe", system.Extensions);
        }
    }

    [Fact]
    public async Task Shortcuts_are_scanned_as_games_titled_by_their_names()
    {
        var games = (await _library.GetGamesAsync("steam", Ct)).Games;

        Assert.Equal(["Party Animals", "Spacewar"], games.Select(g => g.Title));
    }

    [Fact]
    public async Task A_steam_shortcut_is_handed_to_steam_and_its_game_followed_until_steam_says_it_ended()
    {
        _steam.Script(Repeat(Idle, 3), Repeat(Playing, 10), Repeat(Idle, 1));

        var outcome = await Launch("steam", "Party Animals.url");

        Assert.Equal(["starting", "running", "exited"], _events.ToArray());
        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        var plan = Assert.Single(_runner.Plans);
        Assert.True(plan.RunFile);
        Assert.True(plan.Detached);
        Assert.Equal("Steam", plan.EmulatorName);
        Assert.Equal("run-file", plan.EmulatorId);
        Assert.Equal(_dir.Combine("ROMs", "steam", "Party Animals.url"), plan.Executable);
        Assert.True(_steam.PollCount >= 15, $"polled {_steam.PollCount} times");
        Assert.Equal(1, (await _library.GetPlayStatsAsync(Key("steam", "Party Animals.url"), Ct))!.PlayCount);
        Assert.Equal(1, SessionCount());
    }

    [Fact]
    public async Task A_steam_shortcut_in_the_windows_system_is_followed_too()
    {
        _steam.Script(Repeat(Playing, 3), Repeat(Idle, 1));

        var outcome = await Launch("windows", "Steam game.url");

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.True(Assert.Single(_runner.Plans).Detached);
    }

    [Fact]
    public async Task A_game_steam_never_starts_is_a_failure_and_not_a_play()
    {
        _steam.Script(Repeat(Idle, 10_000));
        string? reason = null;
        _launcher.Failed += (_, e) => reason = e.Reason;

        var outcome = await Launch("steam", "Party Animals.url");

        Assert.Equal(["starting", "running", "failed"], _events.ToArray());
        Assert.Equal(LaunchFailure.NotStarted, outcome.Failure);
        Assert.StartsWith("Steam didn't start the game within", reason, StringComparison.Ordinal);
        Assert.Null(await _library.GetPlayStatsAsync(Key("steam", "Party Animals.url"), Ct));
        Assert.Equal(1, SessionCount());
    }

    [Fact]
    public async Task A_steam_shortcut_without_steam_installed_fails_before_anything_starts()
    {
        _steam.ClientPath = null;

        var outcome = await Launch("steam", "Party Animals.url");

        Assert.Equal(["failed"], _events.ToArray());
        Assert.Equal(LaunchFailure.MissingFile, outcome.Failure);
        Assert.Contains("is a Steam game's shortcut, and Steam isn't installed", outcome.Reason, StringComparison.Ordinal);
        Assert.Empty(_runner.Plans);
    }

    [Fact]
    public async Task Other_internet_shortcuts_and_shortcuts_run_as_themselves()
    {
        await Launch("windows", "Website.url");
        await Launch("steam", "Spacewar.lnk");

        Assert.All(_runner.Plans, plan => Assert.False(plan.Detached));
        Assert.All(_runner.Plans, plan => Assert.Equal("Run the game's own file (shortcut, script or program)", plan.EmulatorName));
        Assert.Equal(0, _steam.PollCount);
    }

    [Fact]
    public async Task Without_a_steam_client_a_steam_shortcut_runs_like_any_other()
    {
        var launcher = NewLauncher(_launcher.Config, steam: null);

        var outcome = await Launch("steam", "Party Animals.url", launcher);

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.False(Assert.Single(_runner.Plans).Detached);
    }

    // ---- Fakes ------------------------------------------------------------------------------------

    private static IEnumerable<SteamAppState> Repeat(SteamAppState state, int polls) => Enumerable.Repeat(state, polls);

    /// <summary>One scripted state a poll; the last one repeats.</summary>
    private sealed class FakeSteam : ISteamClient
    {
        private readonly object _gate = new();
        private readonly List<(int Polls, TaskCompletionSource Reached)> _waiters = [];
        private SteamAppState[] _script = [Idle];
        private int _polls;

        public string? ClientPath { get; set; } = @"C:\Program Files (x86)\Steam\steam.exe";

        public bool Throws { get; init; }

        public int PollCount => Volatile.Read(ref _polls);

        public void Script(params IEnumerable<SteamAppState>[] parts) => _script = parts.SelectMany(p => p).ToArray();

        public Task Polled(int polls)
        {
            lock (_gate)
            {
                var reached = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                if (_polls >= polls)
                {
                    reached.SetResult();
                }
                else
                {
                    _waiters.Add((polls, reached));
                }

                return reached.Task;
            }
        }

        public SteamAppState GetAppState(uint appId)
        {
            Assert.Equal(AppId, appId);
            lock (_gate)
            {
                var poll = _polls++;
                foreach (var waiter in _waiters.Where(w => w.Polls <= _polls))
                {
                    waiter.Reached.TrySetResult();
                }

                if (Throws)
                {
                    throw new UnauthorizedAccessException("no");
                }

                return _script[Math.Min(poll, _script.Length - 1)];
            }
        }
    }

    /// <summary>Opens the file as the shell would, and starts nothing it follows.</summary>
    private sealed class FakeRunner : IProcessRunner
    {
        private readonly ConcurrentQueue<LaunchPlan> _plans = new();

        public IReadOnlyList<LaunchPlan> Plans => _plans.ToArray();

        public IRunningProcess Start(LaunchPlan plan)
        {
            _plans.Enqueue(plan);
            return new Ended();
        }

        private sealed class Ended : IRunningProcess
        {
            public int ProcessId => 0;

            public Task<ProcessOutcome> Completion { get; } = Task.FromResult(new ProcessOutcome(0, TimeSpan.Zero, false));

            public void Terminate()
            {
            }

            public void Dispose()
            {
            }
        }
    }

    /// <summary>A monotonic clock only the polls move.</summary>
    private sealed class StepClock : TimeProvider
    {
        private long _ticks;

        public override long TimestampFrequency => TimeSpan.TicksPerSecond;

        public override long GetTimestamp() => Interlocked.Read(ref _ticks);

        public void Advance(TimeSpan by) => Interlocked.Add(ref _ticks, by.Ticks);
    }
}
