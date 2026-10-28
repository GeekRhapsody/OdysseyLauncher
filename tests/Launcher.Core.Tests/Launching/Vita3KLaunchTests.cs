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
/// PS Vita games through the real process runner and library, with tests/FakeEmulator standing in for Vita3K, a
/// <c>portable</c> folder beside it holding its storage (ARCHITECTURE.md A5, Vita3K's games).
/// </summary>
public sealed class Vita3KLaunchTests : IAsyncLifetime
{
    private readonly TempDir _dir = new();
    private readonly ManualClock _clock = new(new DateTimeOffset(2026, 10, 28, 10, 0, 0, TimeSpan.Zero));
    private readonly ConcurrentQueue<string> _events = new();
    private LibraryService _library = null!;
    private LaunchService _launcher = null!;
    private string _apps = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private string Log => _dir.Combine("fake-log.json");

    private string Roms => _dir.Combine("ROMs", "psvita");

    public async ValueTask InitializeAsync()
    {
        var exe = FakeEmulator.InstallAt(_dir.Combine("Emulators", "Vita3K"));
        _apps = Path.Combine(Path.GetDirectoryName(exe)!, "portable", "fs", "ux0", "app");
        Directory.CreateDirectory(Path.Combine(_apps, "PCSB00842"));
        Directory.CreateDirectory(Path.Combine(_apps, "PCSE00232"));
        Directory.CreateDirectory(Path.Combine(_apps, "PCSF00243"));

        _dir.File("ROMs/psvita/Infected Wars (Europe) [PCSB00842].vpk", "vpk");
        _dir.File("ROMs/psvita/Gravity Rush (Europe) [PCSF00024].vpk", "vpk");
        _dir.File("ROMs/psvita/A-men.psvita", "PCSE00232\n");
        _dir.File("ROMs/psvita/Freedom Wars.psvita", "PCSF00446\n");
        _dir.File("ROMs/psvita/No Id.psvita", "\n");
        _dir.File("ROMs/psvita/Killzone Mercenary.psvita/Killzone Mercenary.psvita", "PCSF00243");
        _dir.File("ROMs/psvita/Ciel Nosurge.psvita/eboot.bin");
        File.WriteAllBytes(_dir.File("ROMs/psvita/Ciel Nosurge.psvita/sce_sys/param.sfo"), TitleIdTests.Sfo(("TITLE_ID", "PCSG00454")));

        var log = $"'--fake-log={Template.Escape(Log)}'";
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = _dir.Path,
            ConfigDir = _dir.Combine("config"),
            Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = '{_dir.Combine("ROMs")}'\n"),
            Systems = new ConfigFile("systems.toml", """
                [systems.psvita]
                emulator = "fake-vita3k"
                """),
            Emulators = new ConfigFile("emulators.toml", $"""
                [emulators.fake-vita3k]
                name = "Vita3K"
                executable = '{exe}'
                args = [{log}, "-r", "{"{title_id}"}"]
                install_args = [{log}, "{"{rom}"}"]
                installs = "vita3k"
                """),
        });
        Assert.False(result.HasErrors, string.Join('\n', result.Diagnostics));

        _library = await LibraryService.OpenAsync(result.Config, _dir.Combine("data"), _clock, Ct);
        await _library.RescanAsync("psvita", null, Ct);
        _launcher = new LaunchService(result.Config, PlatformServices.CreateProcessRunner(), _library, _clock)
        {
            ApplicationData = _dir.Combine("Roaming"),
        };
        _launcher.Starting += (_, _) => _events.Enqueue("starting");
        _launcher.Failed += (_, _) => _events.Enqueue("failed");
    }

    public ValueTask DisposeAsync()
    {
        _library.Dispose();
        SqliteConnection.ClearAllPools();
        _dir.Dispose();
        return ValueTask.CompletedTask;
    }

    private async Task<LaunchOutcome> Launch(string name)
    {
        var game = await _library.GetGameAsync(new GameKey("psvita", PathKeys.ToPathKey(PathKeys.ToRelPath(name))), Ct);
        Assert.NotNull(game);
        return await _launcher.LaunchAsync(game, null, Ct);
    }

    private string[] LoggedArgs() => FakeEmulator.ReadLog(Log).Args.Skip(1).ToArray();

    [Theory]
    [InlineData("Infected Wars (Europe) [PCSB00842].vpk", "PCSB00842")]
    [InlineData("A-men.psvita", "PCSE00232")]
    [InlineData("Killzone Mercenary.psvita", "PCSF00243")]
    public async Task An_installed_game_is_booted_by_its_title_id(string name, string titleId)
    {
        var outcome = await Launch(name);

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.Equal(["-r", titleId], LoggedArgs());
    }

    [Theory]
    [InlineData("Gravity Rush (Europe) [PCSF00024].vpk")]
    [InlineData("Ciel Nosurge.psvita")]
    public async Task A_package_or_a_folder_that_isnt_installed_is_given_to_Vita3K_to_install(string name)
    {
        var outcome = await Launch(name);

        Assert.Equal(LaunchStatus.Exited, outcome.Status);
        Assert.Equal([Path.Combine(Roms, name)], LoggedArgs());
    }

    [Fact]
    public async Task Once_its_installed_the_same_package_is_booted_instead()
    {
        Directory.CreateDirectory(Path.Combine(_apps, "PCSF00024"));

        await Launch("Gravity Rush (Europe) [PCSF00024].vpk");

        Assert.Equal(["-r", "PCSF00024"], LoggedArgs());
    }

    [Fact]
    public async Task An_ES_DE_file_naming_a_game_that_isnt_installed_fails_before_anything_starts()
    {
        var outcome = await Launch("Freedom Wars.psvita");

        Assert.Equal(["failed"], _events);
        Assert.Equal(LaunchFailure.MissingFile, outcome.Failure);
        Assert.Equal($"The game PCSF00446 isn't installed in Vita3K, and '{Path.Combine(Roms, "Freedom Wars.psvita")}' isn't something " +
            "it can install (a .vpk or .zip package, or a game's folder). Install the game in Vita3K, then launch it again.", outcome.Reason);
    }

    [Fact]
    public async Task A_file_with_no_title_id_says_where_to_put_one()
    {
        var outcome = await Launch("No Id.psvita");

        Assert.Equal(LaunchFailure.MissingFile, outcome.Failure);
        Assert.StartsWith($"No title id was found for '{Path.Combine(Roms, "No Id.psvita")}'", outcome.Reason, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_missing_file_is_reported_as_missing()
    {
        var game = await _library.GetGameAsync(new GameKey("psvita", "freedom wars.psvita"), Ct);
        File.Delete(Path.Combine(Roms, "Freedom Wars.psvita"));

        var outcome = await _launcher.LaunchAsync(game!, null, Ct);

        Assert.Equal(LaunchFailure.MissingFile, outcome.Failure);
        Assert.StartsWith($"The game's file is missing: '{Path.Combine(Roms, "Freedom Wars.psvita")}'.", outcome.Reason, StringComparison.Ordinal);
    }
}
