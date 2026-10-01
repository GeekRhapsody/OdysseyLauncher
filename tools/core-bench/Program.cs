using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Scanning;
using Launcher.Core.Tests.Benchmarks;

// core-bench <absolute work folder>: times in ms, medians over runs, warm file cache.
// The work folder is deleted and recreated.
if (args.Length != 1 || !Path.IsPathRooted(args[0]))
{
    Console.Error.WriteLine("usage: core-bench <absolute work folder>");
    return 2;
}

var work = args[0];
if (Directory.Exists(work))
{
    Directory.Delete(work, recursive: true);
}

Directory.CreateDirectory(work);
var romRoot = Path.Combine(work, "ROMs");
var optimised = !typeof(ConfigLoader).Assembly.GetCustomAttributes(typeof(DebuggableAttribute), false)
    .OfType<DebuggableAttribute>().Any(a => a.IsJITOptimizerDisabled);
Print($"runtime {RuntimeInformation.FrameworkDescription}, Launcher.Core optimised: {optimised}");

var stopwatch = Stopwatch.StartNew();
var config = LoadConfig(romRoot);
Print($"config load, first in process (Tomlyn and loader JIT included): {stopwatch.Elapsed.TotalMilliseconds:F1}");
Print($"config load, warm: {Median(20, () => LoadConfig(romRoot)):F2}");

stopwatch.Restart();
var games = FakeRomTree.Write(romRoot, 10_000);
Print($"generated 10,000 files ({games} games) in {stopwatch.ElapsedMilliseconds}");

stopwatch.Restart();
using (var first = await LibraryService.OpenAsync(config, Path.Combine(work, "first"), null, default))
{
    Print($"LibraryService.OpenAsync, first in process (SQLite native load, creating both DBs): {stopwatch.Elapsed.TotalMilliseconds:F1}");
    stopwatch.Restart();
    await first.RescanAsync(null, null, default);
    Print($"full scan, first in process (JIT included): {stopwatch.Elapsed.TotalMilliseconds:F1}");
}

var run = 0;
Print($"full scan into an empty library: {await MedianAsync(5, async () =>
{
    using var fresh = await LibraryService.OpenAsync(config, Path.Combine(work, $"full{run++}"), null, default);
    var timer = Stopwatch.StartNew();
    await fresh.RescanAsync(null, null, default);
    return timer.Elapsed.TotalMilliseconds;
}):F1}");

using var library = await LibraryService.OpenAsync(config, Path.Combine(work, "full0"), null, default);
Print($"rescan, nothing changed: {await MedianAsync(7, async () => await Time(() => library.RescanAsync(null, null, default))):F1}");
var scanner = new RomScanner();
Print($"  scanner alone, no playlist cache: {Median(5, () =>
{
    foreach (var system in config.Systems)
    {
        scanner.Scan(system, null, default);
    }
}):F1}");

var roms = Directory.GetFiles(Path.Combine(romRoot, "snes"), "*.sfc", SearchOption.AllDirectories).Order(StringComparer.Ordinal).ToArray();
var change = 0;
Print($"rescan, 1% changed (30 touched, 35 added, 35 deleted): {await MedianAsync(3, async () =>
{
    for (var i = 0; i < 30; i++)
    {
        File.SetLastWriteTimeUtc(roms[(change * 100) + i], new DateTime(2025, 1, 1, 0, 0, change, DateTimeKind.Utc));
    }

    for (var i = 0; i < 35; i++)
    {
        File.Delete(roms[(change * 100) + 50 + i]);
        File.WriteAllText(Path.Combine(romRoot, "snes", string.Create(CultureInfo.InvariantCulture, $"New {change}-{i:D2}.sfc")), string.Empty);
    }

    change++;
    return await Time(() => library.RescanAsync(null, null, default));
}):F1}");
Print($"rebuild: {await Time(() => library.RebuildAsync(null, default)):F1}");

// One 10,000-game system, with 200 favourites to join against.
var bigRoot = Path.Combine(work, "BigROMs");
Directory.CreateDirectory(Path.Combine(bigRoot, "snes"));
for (var i = 0; i < 10_000; i++)
{
    File.WriteAllText(Path.Combine(bigRoot, "snes", string.Create(CultureInfo.InvariantCulture, $"Game {(i * 7919) % 10_000:D5} - Subtitle (USA).sfc")), string.Empty);
}

using var big = await LibraryService.OpenAsync(LoadConfig(bigRoot), Path.Combine(work, "big"), null, default);
await big.RescanAsync("snes", null, default);
for (var i = 0; i < 200; i++)
{
    await big.SetFavouriteAsync(new GameKey("snes", string.Create(CultureInfo.InvariantCulture, $"game {i * 37:D5} - subtitle (usa).sfc")), true, default);
}

Print($"GetGamesAsync, 10,000 games: {await MedianAsync(9, async () => await Time(() => big.GetGamesAsync("snes", default))):F2}");
await big.SetTitleOverrideAsync(new GameKey("snes", "game 00005 - subtitle (usa).sfc"), "Aaa", default);
Print($"GetGamesAsync, 10,000 games, one title override: {await MedianAsync(9, async () => await Time(() => big.GetGamesAsync("snes", default))):F2}");
Print($"GetSystemsAsync (the boot query): {await MedianAsync(9, async () => await Time(() => big.GetSystemsAsync(default))):F2}");
return 0;

static AppConfig LoadConfig(string romRoot) => new ConfigLoader().Load(new ConfigSources
{
    HomeDir = romRoot,
    ConfigDir = romRoot,
    Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = '{romRoot}'\n"),
    FileExists = null, // as at boot: the install checks run after interactive (AppServices.CheckInstallsAsync)
}).Config;

static void Print(string line) => Console.WriteLine(line);

static async Task<double> Time(Func<Task> action)
{
    var timer = Stopwatch.StartNew();
    await action();
    return timer.Elapsed.TotalMilliseconds;
}

static double Median(int runs, Action action)
{
    var times = new List<double>(runs);
    for (var i = 0; i < runs; i++)
    {
        var timer = Stopwatch.StartNew();
        action();
        times.Add(timer.Elapsed.TotalMilliseconds);
    }

    times.Sort();
    return times[runs / 2];
}

static async Task<double> MedianAsync(int runs, Func<Task<double>> measure)
{
    var times = new List<double>(runs);
    for (var i = 0; i < runs; i++)
    {
        times.Add(await measure());
    }

    times.Sort();
    return times[runs / 2];
}
