using System.Collections.Concurrent;
using Launcher.Core.Config;
using Launcher.Core.Launching;
using Launcher.Core.Launching.Controllers;
using Launcher.Core.Library;
using Launcher.Core.Platform;
using Launcher.Core.Scanning;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Launching;

/// <summary>
/// End to end through the real process runner, the library and userdata.db, with tests/FakeEmulator standing in for
/// the emulator. The fake is installed at a path with spaces and non-ASCII characters, and the ROM's name has
/// spaces, non-ASCII characters, an emoji, '&amp;', '%' and braces.
/// </summary>
public sealed class LaunchServiceTests : IAsyncLifetime
{
    private const string RomDir = "Sub Folder é";
    private const string RomFile = "Sonic & Knuckles {x} (100%) ü 日本 😀.md";

    private readonly TempDir _dir = new();
    private readonly ManualClock _clock = new(new DateTimeOffset(2026, 9, 28, 10, 0, 0, TimeSpan.Zero));
    private readonly ConcurrentQueue<string> _events = new();
    private LibraryService _library = null!;
    private LaunchService _launcher = null!;
    private string _exe = null!;
    private string _core = null!;
    private string _rom = null!;
    private GameKey _key;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private string Log => _dir.Combine("fake-log.json");

    private string DataDir => _dir.Combine("data");

    public async ValueTask InitializeAsync()
    {
        _exe = FakeEmulator.InstallAt(_dir.Combine("Emulators ü 日本", "Fake Emu"), OperatingSystem.IsWindows() ? "Fake Emu ü.exe" : null);
        _core = _dir.File("Emulators ü 日本/Fake Emu/cores/fake core_libretro.dll");
        _rom = _dir.File($"ROMs/megadrive/{RomDir}/{RomFile}", "rom");
        _key = new GameKey("megadrive", PathKeys.ToPathKey(PathKeys.ToRelPath($"{RomDir}/{RomFile}")));

        var config = LoadConfig(LogArg);
        _library = await LibraryService.OpenAsync(config, DataDir, _clock, Ct);
        await _library.RescanAsync("megadrive", null, Ct);
        _launcher = new LaunchService(config, PlatformServices.CreateProcessRunner(), _library, _clock);
        _launcher.Starting += (_, _) => _events.Enqueue("starting");
        _launcher.Running += (_, _) => _events.Enqueue("running");
        _launcher.Exited += (_, _) => _events.Enqueue("exited");
        _launcher.Failed += (_, _) => _events.Enqueue("failed");
    }

    public ValueTask DisposeAsync()
    {
        _library.Dispose();
        SqliteConnection.ClearAllPools();
        _dir.Dispose();
        return ValueTask.CompletedTask;
    }

    /// <summary>A TOML literal string: no escapes, so Windows paths go in as they are.</summary>
    private static string Literal(string text) => $"'{text}'";

    private string LogArg => Literal($"--fake-log={Template.Escape(Log)}");

    /// <param name="args">TOML array items for the <c>fake</c> profile.</param>
    /// <param name="controllers">The system sets controllers up, and fake-alt (only) says how: Eden's way.</param>
    private AppConfig LoadConfig(string args, string? executable = null, bool controllers = false)
    {
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = _dir.Path,
            ConfigDir = _dir.Combine("config"),
            Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = {Literal(_dir.Combine("ROMs"))}\n"),
            Systems = new ConfigFile("systems.toml", $"""
                [systems.megadrive]
                emulator = "fake"
                alt_emulators = ["fake-alt"]
                auto_configure_controllers = {(controllers ? "true" : "false")}
                """),
            Emulators = new ConfigFile("emulators.toml", $"""
                [emulators.fake]
                name = "Fake Emu"
                executable = {Literal(executable ?? _exe)}
                core = {Literal(_core)}
                args = [{args}, "-L", "{"{core}"}"]

                [emulators.fake-alt]
                name = "Fake Alt"
                executable = {Literal(_exe)}
                args = [{LogArg}, "--alt", "{"{rom}"}"]
                {(controllers ? "controllers = \"eden\"" : string.Empty)}
                """),
        });
        Assert.False(result.HasErrors, string.Join('\n', result.Diagnostics));
        return result.Config;
    }

    private void UseArgs(string args, string? executable = null)
    {
        var config = LoadConfig(args, executable);
        _launcher.Config = config;
        _library.Config = config;
    }

    private async Task<GameDetails> Game() => (await _library.GetGameAsync(_key, Ct))!;

    [Fact]
    public async Task Controllers_are_set_up_before_the_start_only_where_the_system_and_the_emulator_say_so()
    {
        var config = LoadConfig(LogArg, controllers: true);
        _launcher.Config = config;
        _launcher.ApplicationData = _dir.Combine("Roaming");
        Directory.CreateDirectory(Path.Combine(Path.GetDirectoryName(_exe)!, "user"));
        var portable = Path.Combine(Path.GetDirectoryName(_exe)!, "user", "config", "qt-config.ini");
        LaunchStartingEventArgs? starting = null;
        _launcher.Starting += (_, e) => starting = e;
        Gamepad[] pads = [new(0, "Steam Deck", "0300f617de2800000512000000026800")];

        // The system's emulator has no controller setup, and no pads were given: nothing is written.
        Assert.Equal(LaunchStatus.Exited, (await _launcher.LaunchAsync(await Game(), null, pads, Ct)).Status);
        Assert.Null(starting!.Controllers);
        Assert.Equal(LaunchStatus.Exited, (await _launcher.LaunchAsync(await Game(), "fake-alt", null, Ct)).Status);
        Assert.False(File.Exists(portable));

        // Eden's way, with Eden's portable folder beside the program: the file is written there before the start.
        Assert.Equal(LaunchStatus.Exited, (await _launcher.LaunchAsync(await Game(), "fake-alt", pads, Ct)).Status);
        Assert.Equal(portable, starting!.Controllers!.ConfigFile);
        Assert.Null(starting.ControllerError);
        Assert.Contains("player_0_connected=true", File.ReadAllText(portable), StringComparison.Ordinal);

        // The system turned it off.
        File.Delete(portable);
        _launcher.Config = LoadConfig(LogArg);
        Assert.Equal(LaunchStatus.Exited, (await _launcher.LaunchAsync(await Game(), "fake-alt", pads, Ct)).Status);
        Assert.False(File.Exists(portable));
    }

    private async Task<LaunchOutcome> Launch(string? emulatorOverride = null, CancellationToken? cancellationToken = null) =>
        await _launcher.LaunchAsync(await Game(), emulatorOverride, cancellationToken ?? Ct);

    private string[] Events => _events.ToArray();

    private List<(string Emulator, long StartedAt, long? EndedAt, long? ExitCode)> Sessions()
    {
        using var connection = new SqliteConnection($"Data Source={Path.Combine(DataDir, LibraryService.UserDataFileName)};Mode=ReadOnly;Pooling=False");
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT emulator, started_at, ended_at, exit_code FROM play_sessions ORDER BY session_id";
        using var reader = command.ExecuteReader();
        var rows = new List<(string, long, long?, long?)>();
        while (reader.Read())
        {
            rows.Add((reader.GetString(0), reader.GetInt64(1), reader.IsDBNull(2) ? null : reader.GetInt64(2), reader.IsDBNull(3) ? null : reader.GetInt64(3)));
        }

        return rows;
    }

    // ---- Quoting and placeholders -----------------------------------------------------------------

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Every_argument_reaches_the_emulator_exactly_as_expanded(bool portableRunner)
    {
        UseArgs($$$"""
            {{{LogArg}}},
            "{rom}", "--dir={rom_dir}", "{rom_file}", "{rom_stem}", "{system}", "{emulator}", "{emulator_dir}",
            "",
            'say "hello" to C:\dir\',
            "tab\there",
            'trailing\',
            'a\\"b',
            "{{literal}} {{rom}}",
            '100% & ^ | < > ! ` $ %PATH%'
            """);
        if (portableRunner)
        {
            _launcher = new LaunchService(_launcher.Config, new PortableProcessRunner(), _library, _clock);
        }

        var outcome = await Launch();

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        var log = FakeEmulator.ReadLog(Log);
        var romDir = Path.GetDirectoryName(_rom)!;
        var exeDir = Path.GetDirectoryName(_exe)!;
        string[] expected =
        [
            $"--fake-log={Log}",
            _rom, $"--dir={romDir}", RomFile, Path.GetFileNameWithoutExtension(RomFile), "megadrive", _exe, exeDir,
            "",
            "say \"hello\" to C:\\dir\\",
            "tab\there",
            "trailing\\",
            "a\\\\\"b",
            "{literal} {rom}",
            "100% & ^ | < > ! ` $ %PATH%",
            "-L", _core,
        ];
        Assert.Equal(expected, log.Args);
        Assert.Equal(exeDir, log.WorkingDirectory);
        Assert.Equal(expected, outcome.Plan!.Arguments);
    }

    [Fact]
    public async Task A_rom_named_like_a_placeholder_stays_literal()
    {
        UseArgs($"{LogArg}, \"{{rom_file}}\"");

        var outcome = await Launch();

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.Equal("Sonic & Knuckles {x} (100%) ü 日本 😀.md", FakeEmulator.ReadLog(Log).Args[1]);
    }

    [Fact]
    public async Task A_folder_game_is_launched_with_its_file_of_the_same_name_or_else_the_folder()
    {
        _dir.File("ROMs/megadrive/Dump ü.md/PS3_GAME/USRDIR/EBOOT.BIN");
        _dir.File("ROMs/megadrive/Multi Disc.md/Multi Disc.md");
        _dir.File("ROMs/megadrive/Multi Disc.md/Disc 1.md");
        await _library.RescanAsync("megadrive", null, Ct);
        UseArgs($"{LogArg}, \"{{rom}}\"");

        var folder = (await _library.GetGameAsync(new GameKey("megadrive", "dump ü.md"), Ct))!;
        var outcome = await _launcher.LaunchAsync(folder, null, Ct);

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.Equal(_dir.Combine("ROMs", "megadrive", "Dump ü.md"), FakeEmulator.ReadLog(Log).Args[1]);

        var withFile = (await _library.GetGameAsync(new GameKey("megadrive", "multi disc.md"), Ct))!;
        outcome = await _launcher.LaunchAsync(withFile, null, Ct);

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.Equal(_dir.Combine("ROMs", "megadrive", "Multi Disc.md", "Multi Disc.md"), FakeEmulator.ReadLog(Log).Args[1]);
        Assert.Null(await _library.GetGameAsync(new GameKey("megadrive", "multi disc.md/disc 1.md"), Ct));
    }

    // ---- Lifecycle events --------------------------------------------------------------------------

    [Fact]
    public async Task A_launch_raises_starting_running_then_exited_with_the_exit_code_and_duration()
    {
        UseArgs($"{LogArg}, '--fake-sleep=300', '--fake-exit=7'");
        _launcher.QuickExitThreshold = TimeSpan.Zero;
        var running = new TaskCompletionSource<int>();
        LaunchExitedEventArgs? exited = null;
        _launcher.Running += (_, e) => running.TrySetResult(e.ProcessId);
        _launcher.Exited += (_, e) => exited = e;

        var outcome = await Launch();

        Assert.Equal(["starting", "running", "exited"], Events);
        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.Equal(7, outcome.ExitCode);
        Assert.Equal(7, exited!.ExitCode);
        Assert.InRange(exited.Duration, TimeSpan.FromMilliseconds(300), TimeSpan.FromSeconds(20));
        Assert.Equal(FakeEmulator.ReadLog(Log).ProcessId, await running.Task);
        Assert.False(_launcher.IsRunning);
    }

    [Fact]
    public async Task A_quick_non_zero_exit_is_a_failure_with_a_readable_reason_and_isnt_counted_as_a_play()
    {
        UseArgs($"{LogArg}, '--fake-exit=3'");
        string? reason = null;
        _launcher.Failed += (_, e) => reason = e.Reason;

        var outcome = await Launch();

        Assert.Equal(["starting", "running", "failed"], Events);
        Assert.Equal(LaunchFailure.QuickExit, outcome.Failure);
        Assert.Equal(3, outcome.ExitCode);
        Assert.StartsWith("Fake Emu closed after ", reason, StringComparison.Ordinal);
        Assert.Contains("with exit code 3, so the game probably didn't start", reason, StringComparison.Ordinal);
        Assert.Null(await _library.GetPlayStatsAsync(_key, Ct));
        var session = Assert.Single(Sessions());
        Assert.Equal(3, session.ExitCode);
        Assert.NotNull(session.EndedAt);
    }

    [Fact]
    public async Task A_missing_executable_fails_before_anything_starts()
    {
        var missing = _dir.Combine("Nowhere", "emu.exe");
        UseArgs(LogArg, missing);

        var outcome = await Launch();

        Assert.Equal(["failed"], Events);
        Assert.Equal(LaunchFailure.MissingFile, outcome.Failure);
        Assert.Equal($"Fake Emu isn't installed at '{missing}'. Install it there, or fix the path in emulators.toml (or the variable it uses in settings.toml).", outcome.Reason);
        Assert.Empty(Sessions());
    }

    [Fact]
    public async Task A_missing_rom_fails_with_its_path()
    {
        var game = await Game();
        File.Delete(_rom);

        var outcome = await _launcher.LaunchAsync(game, null, Ct);

        Assert.Equal(["failed"], Events);
        Assert.Equal(LaunchFailure.MissingFile, outcome.Failure);
        Assert.StartsWith($"The game's file is missing: '{_rom}'.", outcome.Reason, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_missing_core_fails_with_its_path()
    {
        File.Delete(_core);

        var outcome = await Launch();

        Assert.Equal(LaunchFailure.MissingFile, outcome.Failure);
        Assert.StartsWith($"The core '{_core}' for Fake Emu doesn't exist.", outcome.Reason, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_file_that_isnt_a_program_is_refused_by_Windows_with_a_readable_reason()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Windows error mapping.");
        var notAProgram = _dir.File("Emulators ü 日本/Not A Program.exe", "just text");
        UseArgs(LogArg, notAProgram);

        var outcome = await Launch();

        Assert.Equal(["starting", "failed"], Events);
        Assert.Equal(LaunchFailure.StartRefused, outcome.Failure);
        Assert.Equal($"Fake Emu couldn't start. '{notAProgram}' isn't a program this PC can run. It may be the wrong file, or built for another kind of processor.", outcome.Reason);
    }

    [Fact]
    public async Task A_second_launch_while_a_game_runs_is_refused()
    {
        UseArgs($"{LogArg}, '--fake-sleep=1000'");
        var first = Launch();
        while (!_launcher.IsRunning)
        {
            await Task.Delay(10, Ct);
        }

        await Assert.ThrowsAsync<InvalidOperationException>(() => Launch());
        await first;
    }

    [Fact]
    public async Task By_the_time_exited_or_failed_is_raised_the_next_launch_is_allowed()
    {
        var runningDuringEvents = new List<bool>();
        _launcher.Exited += (_, _) => runningDuringEvents.Add(_launcher.IsRunning);
        _launcher.Failed += (_, _) => runningDuringEvents.Add(_launcher.IsRunning);

        await Launch();
        await Launch("nope");

        Assert.Equal([false, false], runningDuringEvents);
    }

    [Fact]
    public async Task Cancelling_a_running_game_ends_it_and_still_records_the_session()
    {
        UseArgs($"{LogArg}, '--fake-sleep=30000'");
        using var cancel = new CancellationTokenSource();
        _launcher.Running += (_, _) => cancel.CancelAfter(300);

        var outcome = await Launch(cancellationToken: cancel.Token);

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.True(outcome.Terminated);
        Assert.InRange(outcome.Duration, TimeSpan.FromMilliseconds(300), TimeSpan.FromSeconds(20));
        Assert.Equal(1, (await _library.GetPlayStatsAsync(_key, Ct))!.PlayCount);
    }

    // ---- Stub launchers -----------------------------------------------------------------------------

    [Fact]
    public async Task A_stub_launcher_is_followed_until_the_process_it_started_exits()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Job objects are Windows-only; the portable runner follows the stub only.");
        UseArgs($"{LogArg}, '--fake-spawn=1500'");

        var outcome = await Launch();

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.Equal(0, outcome.ExitCode);
        Assert.InRange(outcome.Duration, TimeSpan.FromMilliseconds(1500), TimeSpan.FromSeconds(20));
        var stub = FakeEmulator.ReadLog(Log);
        var child = FakeEmulator.ReadLog(Log + ".child");
        Assert.NotEqual(stub.ProcessId, child.ProcessId);
        Assert.Equal(["--fake-sleep=1500", $"--fake-log={Log}.child"], child.Args);
    }

    [Fact]
    public async Task A_stub_that_starts_another_program_with_its_own_arguments_is_followed_too()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Job objects are Windows-only.");
        var child = Log + ".started";
        UseArgs($"{LogArg}, {Literal("--fake-start=" + Template.Escape(_exe))}, '--', '--fake-sleep=1200', {Literal("--fake-log=" + Template.Escape(child))}, \"{{rom}}\"");

        var outcome = await Launch();

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.InRange(outcome.Duration, TimeSpan.FromMilliseconds(1200), TimeSpan.FromSeconds(20));
        Assert.Equal(["--fake-sleep=1200", $"--fake-log={child}", _rom, "-L", _core], FakeEmulator.ReadLog(child).Args);
    }

    // ---- Emulator choice ----------------------------------------------------------------------------

    [Fact]
    public async Task A_per_game_override_picks_the_profile_and_a_per_launch_choice_beats_it()
    {
        await _library.SetEmulatorOverrideAsync(_key, "fake-alt", Ct);
        Assert.Equal("fake-alt", (await Game()).EmulatorOverride);

        var viaOverride = await Launch();
        Assert.Equal("fake-alt", viaOverride.Plan!.EmulatorId);
        Assert.Equal([$"--fake-log={Log}", "--alt", _rom], FakeEmulator.ReadLog(Log).Args);

        var chosen = await Launch("fake");
        Assert.Equal("fake", chosen.Plan!.EmulatorId);

        await _library.SetEmulatorOverrideAsync(_key, null, Ct);
        Assert.Null((await Game()).EmulatorOverride);
        Assert.Equal("fake", (await Launch()).Plan!.EmulatorId);
        Assert.Equal(["fake-alt", "fake", "fake"], Sessions().Select(s => s.Emulator));
    }

    [Fact]
    public async Task A_per_game_override_naming_an_unknown_emulator_fails_rather_than_falling_back()
    {
        await _library.SetEmulatorOverrideAsync(_key, "gone", Ct);

        var outcome = await Launch();

        Assert.Equal(LaunchFailure.Config, outcome.Failure);
        Assert.StartsWith("The emulator 'gone' is set for this game, but it isn't configured", outcome.Reason, StringComparison.Ordinal);
    }

    // ---- Play-time recording ------------------------------------------------------------------------

    [Fact]
    public async Task Play_count_time_and_last_played_add_up_over_sessions()
    {
        UseArgs($"{LogArg}, '--fake-sleep=1500'");
        var first = await Launch();
        _clock.Advance(TimeSpan.FromHours(1));
        UseArgs($"{LogArg}, '--fake-sleep=1100'");
        var second = await Launch();

        var stats = (await _library.GetPlayStatsAsync(_key, Ct))!;
        Assert.InRange(first.Duration, TimeSpan.FromMilliseconds(1500), TimeSpan.FromSeconds(20));
        Assert.InRange(second.Duration, TimeSpan.FromMilliseconds(1100), TimeSpan.FromSeconds(20));
        Assert.Equal(2, stats.PlayCount);
        Assert.Equal(TimeSpan.FromSeconds(Seconds(first.Duration) + Seconds(second.Duration)), stats.TotalPlayTime);
        var secondStart = _clock.Now.ToUnixTimeMilliseconds();
        Assert.Equal(DateTimeOffset.FromUnixTimeMilliseconds(secondStart + (long)second.Duration.TotalMilliseconds), stats.LastPlayedAt);

        var sessions = Sessions();
        Assert.Equal(2, sessions.Count);
        Assert.All(sessions, s => Assert.Equal(("fake", 0L), (s.Emulator, s.ExitCode!.Value)));
        Assert.Equal(secondStart, sessions[1].StartedAt);
        Assert.Equal((long)second.Duration.TotalMilliseconds, sessions[1].EndedAt - sessions[1].StartedAt);
        Assert.Equal((long)first.Duration.TotalMilliseconds, sessions[0].EndedAt - sessions[0].StartedAt);

        static long Seconds(TimeSpan duration) => (long)Math.Round(duration.TotalSeconds, MidpointRounding.AwayFromZero);
    }

    [Fact]
    public async Task A_session_left_open_by_a_crash_is_closed_on_the_next_start_as_a_play_with_no_time()
    {
        var started = _clock.Now;
        await _library.BeginSessionAsync(_key, "fake", started, Ct);
        _library.Dispose();
        _clock.Advance(TimeSpan.FromHours(2));

        _library = await LibraryService.OpenAsync(_launcher.Config, DataDir, _clock, Ct);

        Assert.Equal(1, _library.ClosedOrphanSessions);
        var session = Assert.Single(Sessions());
        Assert.Equal(session.StartedAt, session.EndedAt);
        Assert.Null(session.ExitCode);
        Assert.Equal(new PlayStats(1, TimeSpan.Zero, started), await _library.GetPlayStatsAsync(_key, Ct));

        _library.Dispose();
        _library = await LibraryService.OpenAsync(_launcher.Config, DataDir, _clock, Ct);
        Assert.Equal(0, _library.ClosedOrphanSessions);
    }
}
