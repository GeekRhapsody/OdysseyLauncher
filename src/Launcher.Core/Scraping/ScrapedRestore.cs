using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Scraping;

/// <summary>
/// Rebuilds a game's scraped data from <c>scraped/responses/</c> when a scan adds it: after a rebuild, a recreated
/// library.db, or a ROM moved back. Offline: each provider's parser reads its saved response, the results merge in
/// config order as a live scrape does, matches come back with their method, and media rows point at the files that
/// still exist (the user's own art keeps its rows). Runs on the library writer, after the scan's own transaction.
/// </summary>
internal static class ScrapedRestore
{
    /// <summary>Returns how many games got scraped data back.</summary>
    public static int Apply(SqliteConnection connection, string dataDir, AppConfig config, IReadOnlyList<GameKey> added)
    {
        var root = Path.Combine(dataDir, MediaStore.ScrapedFolder, ScrapedResponses.Folder);
        if (added.Count == 0 || !Directory.Exists(root))
        {
            return 0;
        }

        // Providers in config order, then any others that left responses behind.
        var providers = config.Settings.Scraping.ProviderOrder.Concat(ConfigLoader.Scrapers).Distinct(StringComparer.Ordinal).ToList();
        var folders = new HashSet<(string Provider, string System)>();
        foreach (var provider in providers)
        {
            foreach (var system in config.Systems)
            {
                if (Directory.Exists(Path.Combine(root, provider, system.Id)))
                {
                    folders.Add((provider, system.Id));
                }
            }
        }

        if (folders.Count == 0)
        {
            return 0;
        }

        var restored = 0;
        using var transaction = connection.BeginTransaction();
        foreach (var key in added)
        {
            if (config.FindSystem(key.SystemId) is not { } system)
            {
                continue;
            }

            var merge = new ScrapeMerge(new HashSet<string>(MediaKinds.Scrapable, StringComparer.Ordinal));
            var matches = new Dictionary<string, (string, string)>(StringComparer.Ordinal);
            var media = new List<(string, string, StoredMedia)>();
            var log = new List<ProviderLog>();
            var found = new List<string>();
            long at = 0;
            foreach (var provider in providers)
            {
                if (!folders.Contains((provider, key.SystemId)) || ScrapedResponses.Load(dataDir, provider, key) is not { } saved)
                {
                    continue;
                }

                log.Add(new ProviderLog(provider, saved.Status, null));
                at = Math.Max(at, saved.ScrapedAt);
                if (saved.Status != "ok" || saved.GameId is null)
                {
                    continue;
                }

                matches[provider] = (saved.GameId, saved.Method ?? MatchMethods.Filename);
                found.Add(provider);
                if (ScrapedResponses.Parse(saved, config.Settings.Scraping, system) is { } game)
                {
                    merge.Add(provider, game, CapabilitiesOf(provider));
                }

                foreach (var m in saved.Media)
                {
                    if (media.Any(x => x.Item1 == m.Kind))
                    {
                        continue;
                    }

                    var file = new FileInfo(Path.Combine(dataDir, m.Path.Replace('/', Path.DirectorySeparatorChar)));
                    if (file.Exists)
                    {
                        media.Add((m.Kind, provider, new StoredMedia(m.Path, file.Length,
                            new DateTimeOffset(file.LastWriteTimeUtc).ToUnixTimeMilliseconds(), m.Width, m.Height)));
                    }
                }
            }

            if (log.Count == 0)
            {
                continue;
            }

            var write = new ScrapeWrite(merge.Metadata(), matches, media, log, found.Count > 0 ? "ok" : "not_found", found, at);
            if (ScrapeStore.Save(connection, transaction, key, write))
            {
                restored++;
            }
        }

        transaction.Commit();
        return restored;
    }

    public static ScraperCapabilities CapabilitiesOf(string provider) => provider switch
    {
        ScraperIds.ScreenScraper => ScreenScraperScraper.Supplies,
        ScraperIds.Igdb => IgdbScraper.Supplies,
        ScraperIds.SteamGridDb => SteamGridDbScraper.Supplies,
        _ => new ScraperCapabilities(new HashSet<MetadataField>(), new HashSet<string>()),
    };
}
