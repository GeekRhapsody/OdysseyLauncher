using System.Diagnostics;
using System.Globalization;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Scanning;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Benchmarks;

/// <summary>
/// Scan and query budgets on a synthetic 10,000-file tree. The budgets were set from measurements on the
/// baseline Steam Deck (docs/ROADMAP.md, M2 log) with headroom for a noisy run; they're tighter than the M2
/// acceptance targets (3 s full scan, 0.5 s unchanged rescan, 50 ms GetGamesAsync for 10,000 games).
/// Every time is the median of several runs, on a warm file cache.
/// </summary>
[Trait("Category", "Benchmark")]
[Collection(nameof(BenchmarkCollection))]
public sealed class ScanBenchmarkTests : IDisposable
{
    public const int FileCount = 10_000;

    // Budgets, in ms, for `dotnet test` (Debug build, .NET 10 runtime). Measured on 2026-09-28 (Debug, then
    // ExportRelease on .NET 8.0.31): full scan 314 / 275, unchanged rescan 72 / 71, 1% changed 75 / 56,
    // GetGamesAsync for 10,000 games 21 / 19, warm config load 2.6 / 2.1.
    public const double FullScanBudgetMs = 1000;
    public const double UnchangedRescanBudgetMs = 200;
    public const double ChangedRescanBudgetMs = 250;
    public const double GetGames10kBudgetMs = 45;
    public const double ConfigLoadBudgetMs = 10;

    private readonly TempDir _dir = new();

    public void Dispose()
    {
        SqliteConnection.ClearAllPools();
        _dir.Dispose();
    }

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static void Report(string text) => TestContext.Current.TestOutputHelper?.WriteLine(text);

    private static double Median(List<double> values)
    {
        values.Sort();
        return values[values.Count / 2];
    }

    private AppConfig Config()
    {
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = _dir.Path,
            ConfigDir = _dir.Path,
            Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = '{_dir.Combine("ROMs")}'\n"),
        });
        Assert.False(result.HasErrors);
        return result.Config;
    }

    [Fact]
    public async Task Full_scan_and_incremental_rescans_of_10000_files_across_12_systems_meet_their_budgets()
    {
        var generate = Stopwatch.StartNew();
        var expectedGames = FakeRomTree.Write(_dir.Combine("ROMs"), FileCount);
        Report($"generated {FileCount} files ({expectedGames} games) in {generate.ElapsedMilliseconds} ms");
        var config = Config();

        // Full scans, each into a new, empty library.
        var full = new List<double>();
        for (var run = 0; run < 3; run++)
        {
            var dataDir = _dir.Combine($"data{run}");
            using var fresh = await LibraryService.OpenAsync(config, dataDir, null, Ct);
            var stopwatch = Stopwatch.StartNew();
            var summary = await fresh.RescanAsync(null, null, Ct);
            full.Add(stopwatch.Elapsed.TotalMilliseconds);
            Assert.Equal(expectedGames, summary.Added);
            Assert.Equal(12, summary.Systems.Count(s => s.Added > 0));
        }

        using var library = await LibraryService.OpenAsync(config, _dir.Combine("data0"), null, Ct);

        // Rescans with nothing changed.
        var unchanged = new List<double>();
        for (var run = 0; run < 5; run++)
        {
            var stopwatch = Stopwatch.StartNew();
            var summary = await library.RescanAsync(null, null, Ct);
            unchanged.Add(stopwatch.Elapsed.TotalMilliseconds);
            Assert.Equal((0, 0, 0), (summary.Added, summary.Updated, summary.Removed));
            Assert.Equal(0, summary.Systems.Sum(s => s.PlaylistsRead));
        }

        // Rescans after 1% of the files changed: 30 touched, 35 added, 35 deleted each time.
        var changed = new List<double>();
        var roms = Directory.GetFiles(_dir.Combine("ROMs", "snes"), "*.sfc", SearchOption.AllDirectories)
            .Concat(Directory.GetFiles(_dir.Combine("ROMs", "megadrive"), "*.md", SearchOption.AllDirectories))
            .Order(StringComparer.Ordinal)
            .ToArray();
        for (var run = 0; run < 3; run++)
        {
            for (var i = 0; i < 30; i++)
            {
                File.SetLastWriteTimeUtc(roms[(run * 100) + i], new DateTime(2025, 1, 1, 0, 0, run, DateTimeKind.Utc));
            }

            for (var i = 0; i < 35; i++)
            {
                File.Delete(roms[(run * 100) + 50 + i]);
                File.WriteAllText(_dir.Combine("ROMs", "snes", $"New {run}-{i:D2} (USA).sfc"), string.Empty);
            }

            var stopwatch = Stopwatch.StartNew();
            var summary = await library.RescanAsync(null, null, Ct);
            changed.Add(stopwatch.Elapsed.TotalMilliseconds);
            Assert.Equal((35, 30, 35), (summary.Added, summary.Updated, summary.Removed));
        }

        // Entering the biggest system.
        var systems = await library.GetSystemsAsync(Ct);
        var biggest = systems.MaxBy(s => s.GameCount)!;
        var enter = new List<double>();
        for (var run = 0; run < 5; run++)
        {
            var stopwatch = Stopwatch.StartNew();
            var list = await library.GetGamesAsync(biggest.SystemId, Ct);
            enter.Add(stopwatch.Elapsed.TotalMilliseconds);
            Assert.Equal(biggest.GameCount, list.Games.Count);
        }

        Report(string.Create(CultureInfo.InvariantCulture, $"""
            full scan (median of 3):        {Median(full),8:F1} ms   budget {FullScanBudgetMs} ms   runs {string.Join(", ", full.Select(v => v.ToString("F0", CultureInfo.InvariantCulture)))}
            unchanged rescan (median of 5): {Median(unchanged),8:F1} ms   budget {UnchangedRescanBudgetMs} ms   runs {string.Join(", ", unchanged.Select(v => v.ToString("F0", CultureInfo.InvariantCulture)))}
            1% changed rescan (median of 3):{Median(changed),8:F1} ms   budget {ChangedRescanBudgetMs} ms   runs {string.Join(", ", changed.Select(v => v.ToString("F0", CultureInfo.InvariantCulture)))}
            GetGamesAsync {biggest.SystemId} ({biggest.GameCount} games):  {Median(enter),8:F1} ms
            """));

        Assert.True(Median(full) < FullScanBudgetMs, $"Full scan took {Median(full):F0} ms; the budget is {FullScanBudgetMs} ms.");
        Assert.True(Median(unchanged) < UnchangedRescanBudgetMs, $"Unchanged rescan took {Median(unchanged):F0} ms; the budget is {UnchangedRescanBudgetMs} ms.");
        Assert.True(Median(changed) < ChangedRescanBudgetMs, $"1% changed rescan took {Median(changed):F0} ms; the budget is {ChangedRescanBudgetMs} ms.");
    }

    [Fact]
    public async Task Entering_a_10000_game_system_meets_its_budget()
    {
        using var library = await LibraryService.OpenAsync(Config(), _dir.Combine("data"), null, Ct);

        // Rows straight into the library: this measures the grid query, not the scanner.
        var games = new List<ScannedFile>(FileCount);
        for (var i = 0; i < FileCount; i++)
        {
            var rel = string.Create(CultureInfo.InvariantCulture, $"Game {(i * 7919) % FileCount:D5} - Subtitle (USA).sfc");
            games.Add(new ScannedFile(0, rel, PathKeys.ToPathKey(rel), 1024, 0));
        }

        var scan = new SystemScan("snes", [_dir.Combine("ROMs", "snes")], games, [], [], FileCount, 0);
        var path = Path.Combine(_dir.Combine("data"), LibraryService.LibraryFileName);
        using (var connection = Launcher.Core.Data.Sqlite.Open(path))
        {
            LibraryStore.Apply(connection, [scan], null, 0);
        }

        // Some user data to join against.
        for (var i = 0; i < 200; i++)
        {
            await library.SetFavouriteAsync(new GameKey("snes", games[i * 37].PathKey), true, Ct);
        }

        await library.SetTitleOverrideAsync(new GameKey("snes", games[5].PathKey), "Aaa First", Ct);

        var times = new List<double>();
        GameList list = null!;
        for (var run = 0; run < 7; run++)
        {
            var stopwatch = Stopwatch.StartNew();
            list = await library.GetGamesAsync("snes", Ct);
            times.Add(stopwatch.Elapsed.TotalMilliseconds);
        }

        Report(string.Create(CultureInfo.InvariantCulture,
            $"GetGamesAsync, 10,000 games (median of 7): {Median(times):F1} ms   budget {GetGames10kBudgetMs} ms   runs {string.Join(", ", times.Select(v => v.ToString("F1", CultureInfo.InvariantCulture)))}"));
        Assert.Equal(FileCount, list.Games.Count);
        Assert.Equal("Aaa First", list.Games[0].Title);
        Assert.Equal("Game 00000 - Subtitle", list.Games[1].Title);
        Assert.Equal(200, list.Games.Count(g => g.IsFavourite));
        Assert.True(Median(times) < GetGames10kBudgetMs, $"GetGamesAsync took {Median(times):F1} ms; the budget is {GetGames10kBudgetMs} ms.");
    }

    [Fact]
    public void Loading_the_default_config_meets_its_budget()
    {
        var loader = new ConfigLoader();
        var sources = new ConfigSources { HomeDir = _dir.Path, ConfigDir = _dir.Path };
        var first = Stopwatch.StartNew();
        loader.Load(sources);
        var firstMs = first.Elapsed.TotalMilliseconds;

        var times = new List<double>();
        for (var run = 0; run < 20; run++)
        {
            var stopwatch = Stopwatch.StartNew();
            var result = loader.Load(sources);
            times.Add(stopwatch.Elapsed.TotalMilliseconds);

            // The timing includes the install check, as boot does. The default paths needn't exist on this machine.
            Assert.All(result.Diagnostics, d => Assert.True(
                d.Severity == Severity.Warning && (d.Key.EndsWith(".executable", StringComparison.Ordinal) || d.Key.EndsWith(".core", StringComparison.Ordinal)),
                d.ToString()));
        }

        Report(string.Create(CultureInfo.InvariantCulture,
            $"config load (3 default files): first in this test {firstMs:F1} ms, then median {Median(times):F2} ms   budget {ConfigLoadBudgetMs} ms"));
        Assert.True(Median(times) < ConfigLoadBudgetMs, $"Loading config took {Median(times):F1} ms; the budget is {ConfigLoadBudgetMs} ms.");
    }
}
