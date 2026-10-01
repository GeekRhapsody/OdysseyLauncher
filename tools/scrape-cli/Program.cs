// odyssey-scrape: every M4 scraping operation from the command line, for testing live with your own credentials,
// and (M6) importing, inspecting and removing a game's own 3D model. It uses the app's config, library, queue, media
// and model folders (or a portable folder with --user-dir), so what it scrapes or imports shows in the launcher. Credentials come from ConfigDir/secrets.toml or ODYSSEY_* variables, never from
// the command line, and nothing it prints contains them. Ctrl+C pauses: `resume` carries on.

using System.Globalization;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Models;
using Launcher.Core.Platform;
using Launcher.Core.Scanning;
using Launcher.Core.Scraping;

const string Usage = """
    odyssey-scrape [--user-dir=<folder>] <command> [argument]

    Commands:
      providers                   Each provider's state: credentials, and ScreenScraper's account limits
      game <system>/<rel path>    Scrapes one game (scanning its system first if it isn't in the library)
      system <system>             Scrapes every game of a system
      missing                     Scrapes every game never scraped successfully, or with no front cover
      clear <system>/<rel path>   Clears a game's metadata, media files, matches and overrides
      show <system>/<rel path>    Prints what the library has for a game
      resume                      Carries on with batches a stopped run left unfinished
      bake                        Bakes every missing cover derivative (and removes stale ones)
      scan [<system>]             Rescans ROM folders (every system without an argument)
      ss-systems                  Lists ScreenScraper's systems against each system's screenscraper_id

    Models (M6; no network):
      import-model --from=<file> <system>/<rel path>
                                  Imports a .glb, an OBJ zip (.obj, .mtl, textures) or an .obj as the game's model:
                                  converted, fitted to the per-game budget, put in its model slot and indexed
      remove-model <system>/<rel path>
                                  Removes the game's own model (it shows its system's template again)
      inspect-model [--kind=game|template|system] <file>
                                  Checks a model against the spec and budgets without importing it
      models-log                  Prints the model log (rejected and over-budget models, imports)

    <rel path> is the ROM's path under its system's ROM folder, as on disk: megadrive/Sonic the Hedgehog 3 (Europe).md
    Credentials: ConfigDir/secrets.toml ([screenscraper] dev_id, dev_password, username, password;
    [steamgriddb] api_key; [igdb] client_id, client_secret), or ODYSSEY_* environment variables. The Steam store
    ("steam") needs none; it looks up systems with steam_store = true (Windows and Steam) by title.
    """;

Console.OutputEncoding = System.Text.Encoding.UTF8;
var arguments = args.ToList();
string? userDir = null;
string? from = null;
var kind = ModelKind.PerGame;
foreach (var argument in arguments.ToList())
{
    if (argument.StartsWith("--user-dir=", StringComparison.Ordinal))
    {
        userDir = Path.GetFullPath(argument["--user-dir=".Length..]);
        arguments.Remove(argument);
    }
    else if (argument.StartsWith("--from=", StringComparison.Ordinal))
    {
        from = Path.GetFullPath(argument["--from=".Length..]);
        arguments.Remove(argument);
    }
    else if (argument.StartsWith("--kind=", StringComparison.Ordinal))
    {
        kind = argument["--kind=".Length..] switch
        {
            "template" => ModelKind.GameTemplate,
            "system" => ModelKind.SystemModel,
            _ => ModelKind.PerGame,
        };
        arguments.Remove(argument);
    }
}

if (arguments.Count == 0 || arguments[0] is "help" or "-h" or "--help")
{
    Console.WriteLine(Usage);
    return arguments.Count == 0 ? 2 : 0;
}

var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
var paths = userDir is null ? PlatformPaths.Detect(AppContext.BaseDirectory) : PlatformPaths.InOneFolder(userDir, home);
var loaded = new ConfigLoader().Load(ConfigSources.FromDirectory(paths.ConfigDir, paths.HomeDir) with { FileExists = null });
var accounts = ProviderAccounts.Load(paths.ConfigDir);
foreach (var diagnostic in loaded.Diagnostics.Concat(accounts.Diagnostics).Where(d => d.Severity != Severity.Info))
{
    Console.Error.WriteLine(diagnostic);
}

Console.WriteLine($"Config: {paths.ConfigDir}");
Console.WriteLine($"Data:   {paths.DataDir}");

using var stop = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) =>
{
    e.Cancel = true;
    Console.WriteLine("Stopping after the games in progress; `resume` carries on.");
    stop.Cancel();
};

using var library = await LibraryService.OpenAsync(loaded.Config, paths.DataDir, null, CancellationToken.None);
library.ConfigDir = paths.ConfigDir;
var log = new ConsoleLog();
var service = new ScrapeService(new ScrapeServiceOptions
{
    Library = library,
    Paths = paths,
    Accounts = accounts.Accounts,
    Log = log,
    ImageDecoder = PlatformServices.CreateImageDecoder(),
});
service.ProviderNotice += (_, e) => Console.WriteLine($"  ! {e.Notice.Message}");
service.GameScraped += (_, e) =>
{
    var r = e.Result;
    var providers = r.Providers.Count == 0 ? "-" : string.Join(',', r.Providers);
    var media = r.Media.Count == 0 ? "no media" : string.Join(", ", r.Media);
    Console.WriteLine($"  {r.Game.SystemId}/{r.Game.PathKey}: {r.Status} ({providers}; {media})");
    foreach (var entry in r.Log.Where(l => l.Detail is not null))
    {
        Console.WriteLine($"      {entry.Provider}: {entry.Status}: {entry.Detail}");
    }
};
service.Progress += (_, e) =>
{
    if (e.Current is null && e.Done > 0 && (e.Done % 10 == 0 || e.Done == e.Total))
    {
        Console.WriteLine($"  [{e.Done}/{e.Total}] {e.Failed} failed");
    }
};

try
{
    var argument = arguments.Count > 1 ? string.Join(' ', arguments.Skip(1)) : null;
    switch (arguments[0])
    {
        case "providers":
            await Providers();
            return 0;
        case "game":
            {
                var key = await EnsureGame(Require(argument));
                return Report(await service.ScrapeGameAsync(key, stop.Token));
            }

        case "system":
            await EnsureScanned(Require(argument));
            return Report(await service.ScrapeSystemAsync(Require(argument), stop.Token));
        case "missing":
            return Report(await service.ScrapeAllMissingAsync(stop.Token));
        case "resume":
            {
                var results = await service.ResumeAsync(stop.Token);
                Console.WriteLine(results.Count == 0 ? "Nothing to resume." : $"Resumed {results.Count} batch(es).");
                return results.Select(Report).DefaultIfEmpty(0).Max();
            }

        case "clear":
            {
                var key = Key(Require(argument));
                var result = await service.ClearGameAsync(key, stop.Token);
                Console.WriteLine(result.Found ? $"Cleared: {result.FilesDeleted} file(s) deleted." : "Not in the library; its user data was cleared anyway.");
                foreach (var kept in result.KeptSharedArt)
                {
                    Console.WriteLine($"  Kept {kept}: another game uses it too.");
                }

                return 0;
            }

        case "show":
            return await Show(Key(Require(argument)));
        case "bake":
            {
                var summary = await service.Derivatives.BakeMissingAsync(null, stop.Token);
                Console.WriteLine($"Images: {summary.Images}; baked {summary.Baked}, already baked {summary.AlreadyBaked}, failed {summary.Failed}, stale removed {summary.Pruned} ({summary.Elapsed.TotalSeconds:0.0} s)");
                return summary.Failed > 0 ? 1 : 0;
            }

        case "scan":
            {
                var summary = await library.RescanAsync(argument, null, stop.Token);
                Console.WriteLine($"Scanned: {summary.Added} added, {summary.Updated} updated, {summary.Removed} removed, {summary.Unchanged} unchanged ({summary.Elapsed.TotalSeconds:0.0} s)");
                return 0;
            }

        case "ss-systems":
            return await ScreenScraperSystems();
        case "import-model":
            return await ImportModel(await EnsureGame(Require(argument)), from ?? throw new ArgumentException("Give the model file with --from=<file>."));
        case "remove-model":
            {
                var result = await Models().RemoveGameModelAsync(Key(Require(argument)), stop.Token);
                Console.WriteLine(result.Status switch
                {
                    ModelRemoveStatus.Removed => "Removed: the game shows its system's template again.",
                    ModelRemoveStatus.Shared => $"Not removed: {result.SharedPath} is the model of every game with that name. Delete the file to remove it for all of them.",
                    _ => "The game has no model of its own.",
                });
                return result.Status == ModelRemoveStatus.Removed ? 0 : 1;
            }

        case "inspect-model":
            {
                var file = Path.GetFullPath(Require(argument));
                var prepared = ModelImportService.Prepare(file, kind, PlatformServices.CreateImageDecoder(), Path.Combine(paths.CacheDir, ModelCache.FolderName, "scratch"));
                PrintModel(prepared.Processed?.Report, prepared.Converted, prepared.Messages);
                return prepared.Processed?.Report.Accepted == true ? 0 : 1;
            }

        case "models-log":
            {
                var lines = ModelLog.ReadRecent(paths.DataDir, 400);
                Console.WriteLine(lines.Count == 0 ? $"The model log is empty ({ModelLog.PathIn(paths.DataDir)})." : $"{ModelLog.PathIn(paths.DataDir)}:");
                foreach (var line in lines)
                {
                    Console.WriteLine("  " + line);
                }

                return 0;
            }
        default:
            Console.Error.WriteLine($"Unknown command '{arguments[0]}'.");
            Console.WriteLine(Usage);
            return 2;
    }
}
catch (OperationCanceledException)
{
    Console.WriteLine("Stopped.");
    return 1;
}
catch (ArgumentException e)
{
    Console.Error.WriteLine(e.Message);
    return 2;
}
finally
{
    service.Dispose();
}

static string Require(string? argument) =>
    argument ?? throw new ArgumentException("This command needs an argument; see `odyssey-scrape help`.");

GameKey Key(string systemAndPath)
{
    var slash = systemAndPath.IndexOfAny(['/', '\\']);
    if (slash <= 0)
    {
        throw new ArgumentException("Give the game as <system>/<rel path>, e.g. megadrive/Sonic the Hedgehog 3 (Europe).md");
    }

    return new GameKey(systemAndPath[..slash], PathKeys.ToPathKey(PathKeys.ToRelPath(systemAndPath[(slash + 1)..])));
}

async Task EnsureScanned(string systemId)
{
    if (loaded.Config.FindSystem(systemId) is null)
    {
        throw new ArgumentException($"'{systemId}' isn't an enabled system.");
    }

    var systems = await library.GetSystemsAsync(stop.Token);
    if (systems.First(s => s.SystemId == systemId).ScannedAt is null)
    {
        Console.WriteLine($"Scanning {systemId} first...");
        await library.RescanAsync(systemId, null, stop.Token);
    }
}

async Task<GameKey> EnsureGame(string systemAndPath)
{
    var key = Key(systemAndPath);
    if (await library.GetGameAsync(key, stop.Token) is null)
    {
        await EnsureScanned(key.SystemId);
        if (await library.GetGameAsync(key, stop.Token) is null)
        {
            Console.WriteLine($"Scanning {key.SystemId}...");
            await library.RescanAsync(key.SystemId, null, stop.Token);
        }
    }

    return await library.GetGameAsync(key, stop.Token) is null
        ? throw new ArgumentException($"'{systemAndPath}' isn't in {key.SystemId}'s ROM folders.")
        : key;
}

ModelImportService Models() => new(library, paths, PlatformServices.CreateImageDecoder());

async Task<int> ImportModel(GameKey key, string file)
{
    var result = await Models().ImportGameModelAsync(key, file, stop.Token);
    Console.WriteLine(result.Status switch
    {
        ModelImportStatus.Imported => $"Imported{(result.Converted ? " (converted from OBJ)" : string.Empty)}: {Path.Combine(paths.ConfigDir, result.ModelPath!.Replace('/', Path.DirectorySeparatorChar))}",
        ModelImportStatus.Rejected => "Rejected: nothing was changed.",
        ModelImportStatus.Unsupported => "Not imported:",
        _ => "Not imported: the game isn't in the library.",
    });
    PrintModel(result.Report, result.Converted, result.Messages);
    return result.Status == ModelImportStatus.Imported ? 0 : 1;
}

static void PrintModel(ModelReport? report, bool converted, IReadOnlyList<string> messages)
{
    foreach (var message in messages)
    {
        Console.WriteLine($"  {(converted ? "OBJ: " : string.Empty)}{message}");
    }

    if (report is null)
    {
        return;
    }

    Console.WriteLine("  " + report.Summary());
    Console.WriteLine(string.Create(CultureInfo.InvariantCulture, $"  Size {report.Size[0]:0.###} × {report.Size[1]:0.###} × {report.Size[2]:0.###}; largest texture {report.LargestTextureSide}²; joints {report.Joints}; morph targets {report.MorphTargets}"));
    foreach (var error in report.Errors)
    {
        Console.WriteLine($"  error: {error}");
    }

    foreach (var warning in report.Warnings)
    {
        Console.WriteLine($"  warning: {warning}");
    }

    foreach (var note in report.Notes)
    {
        Console.WriteLine($"  note: {note}");
    }
}

int Report(ScrapeBatchResult result)
{
    if (result.BatchId == 0 && result.Total == 0)
    {
        Console.WriteLine("Nothing was scraped: no provider has credentials.");
        return 1;
    }

    var state = result.Paused ? "paused" : result.Cancelled ? "cancelled" : "done";
    Console.WriteLine($"Batch {result.BatchId} ({result.Kind}): {state}. {result.Done} of {result.Total} games, {result.Failed} failed.");
    return result.Failed > 0 || result.Paused || result.Cancelled ? 1 : 0;
}

async Task Providers()
{
    foreach (var provider in service.GetProviders())
    {
        var note = provider.InOrder ? string.Empty : " (not in [scraping] provider or fallback)";
        Console.WriteLine($"{provider.DisplayName}: {provider.State}{note}");
        if (provider.Message is not null)
        {
            Console.WriteLine($"  {provider.Message}");
        }
    }

    if (service.Scrapers[ScraperIds.ScreenScraper] is ScreenScraperScraper screenScraper && screenScraper.Unavailable is null)
    {
        await screenScraper.PrepareAsync(stop.Token);
        if (screenScraper.Limits is { } limits)
        {
            Console.WriteLine(string.Create(CultureInfo.InvariantCulture,
                $"ScreenScraper account: {limits.MaxThreads} thread(s), {limits.PerMinute} a minute; today {limits.Today} of {limits.PerDay} requests, {limits.KoToday} of {limits.KoPerDay} not found"));
        }
    }

    var order = loaded.Config.Settings.Scraping.ProviderOrder;
    Console.WriteLine($"Order: {string.Join(" > ", order)}; media: {string.Join(", ", loaded.Config.Settings.Scraping.Media)}");
}

async Task<int> Show(GameKey key)
{
    var game = await library.GetGameAsync(key, stop.Token);
    if (game is null)
    {
        Console.WriteLine("Not in the library.");
        return 1;
    }

    Console.WriteLine($"{game.Title}  ({game.Key.SystemId}/{game.RelPath})");
    Console.WriteLine(game.Scrape is { } s ? $"  Scraped: {s.Status} by {string.Join(',', s.Providers)} at {s.ScrapedAt.ToLocalTime():yyyy-MM-dd HH:mm}" : "  Never scraped");
    if (game.Metadata is { } m)
    {
        Console.WriteLine($"  Released {m.ReleaseDate}; developer {m.Developer}; publisher {m.Publisher}; genre {m.Genre}; players {m.Players}; rating {m.Rating:0.00} (from {m.Source})");
        Console.WriteLine($"  {m.Description}");
    }

    var row = (await library.GetGamesAsync(key.SystemId, stop.Token)).Games.FirstOrDefault(g => g.GameId == game.GameId);
    if (row.CoverPath is not null)
    {
        var root = row.CoverRoot == MediaRoot.Config ? paths.ConfigDir : paths.DataDir;
        var derivative = TextureDerivatives.PathFor(paths.CacheDir, row.CoverRoot, row.CoverPath, row.CoverSizeBytes, row.CoverMtimeMs);
        Console.WriteLine($"  Cover: {Path.Combine(root, row.CoverPath)} (derivative {(File.Exists(derivative) ? "baked" : "missing")})");
    }

    return 0;
}

async Task<int> ScreenScraperSystems()
{
    if (service.Scrapers[ScraperIds.ScreenScraper] is not ScreenScraperScraper screenScraper || screenScraper.Unavailable is not null)
    {
        Console.WriteLine("ScreenScraper has no developer credentials.");
        return 1;
    }

    var systems = await screenScraper.ListSystemsAsync(stop.Token);
    Console.WriteLine($"ScreenScraper lists {systems.Count} systems.");
    var problems = 0;
    foreach (var system in loaded.Config.Systems)
    {
        var names = system.ScreenScraperId is { } id && systems.TryGetValue(id, out var found) ? string.Join(" / ", found) : "(not listed)";
        Console.WriteLine($"  {system.Id,-14} {system.ScreenScraperId,4}  {system.Name,-32} ScreenScraper: {names}");
        if (names == "(not listed)")
        {
            problems++;
        }
    }

    return problems == 0 ? 0 : 1;
}

/// <summary>Warnings and errors to stderr, already redacted by the service.</summary>
internal sealed class ConsoleLog : ILog
{
    public void Write(LogLevel level, string message)
    {
        if (level != LogLevel.Info)
        {
            Console.Error.WriteLine($"  {level}: {message}");
        }
        else
        {
            Console.WriteLine($"  {message}");
        }
    }
}
