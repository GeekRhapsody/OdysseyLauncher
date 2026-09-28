using System.Text.Json;
using System.Text.Json.Nodes;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;

namespace Launcher.Core.Scraping;

/// <summary>A media file one provider supplied, as saved with its response.</summary>
/// <param name="Path">Relative to DataDir (<see cref="MediaStore.RelativePathFor"/>).</param>
public sealed record SavedMedia(string Kind, string Path, int Width, int Height);

/// <summary>
/// One provider's last answer for one game: <c>scraped/responses/&lt;provider&gt;/&lt;system&gt;/&lt;path_key&gt;.json</c>
/// (ARCHITECTURE.md A4). It carries the matched id and how it was matched, so a rebuild recovers matches offline,
/// and the raw response (credentials redacted), which the provider's parser reads back.
/// </summary>
/// <param name="Status">'ok' or 'not_found'.</param>
/// <param name="Response">The raw response, redacted; null when not found.</param>
public sealed record SavedScrape(
    string Provider,
    GameKey Game,
    string Status,
    string? GameId,
    string? Method,
    long ScrapedAt,
    IReadOnlyList<SavedMedia> Media,
    string? Response);

/// <summary>Reads and writes <see cref="SavedScrape"/> files. Does file I/O: never on the main thread.</summary>
public static class ScrapedResponses
{
    public const string Folder = "responses";
    public const int Format = 1;

    public static string RelativePath(string provider, GameKey game) =>
        $"{MediaStore.ScrapedFolder}/{Folder}/{provider}/{game.SystemId}/{game.PathKey}.json";

    public static string FullPath(string dataDir, string provider, GameKey game) =>
        Path.Combine(dataDir, RelativePath(provider, game).Replace('/', Path.DirectorySeparatorChar));

    /// <summary>Writes atomically. The response is embedded as JSON when it parses (it's always redacted by then), else as a string.</summary>
    public static void Save(string dataDir, SavedScrape scrape)
    {
        ArgumentNullException.ThrowIfNull(dataDir);
        ArgumentNullException.ThrowIfNull(scrape);
        var media = new JsonArray();
        foreach (var m in scrape.Media)
        {
            media.Add(new JsonObject { ["kind"] = m.Kind, ["path"] = m.Path, ["width"] = m.Width, ["height"] = m.Height });
        }

        JsonNode? response = null;
        if (scrape.Response is not null)
        {
            using var document = LenientJson.Parse(scrape.Response);
            response = document is null ? JsonValue.Create(scrape.Response) : LenientJson.ToNode(document.RootElement);
        }

        var json = new JsonObject
        {
            ["format"] = Format,
            ["provider"] = scrape.Provider,
            ["system"] = scrape.Game.SystemId,
            ["path_key"] = scrape.Game.PathKey,
            ["status"] = scrape.Status,
            ["game_id"] = scrape.GameId,
            ["method"] = scrape.Method,
            ["scraped_at"] = scrape.ScrapedAt,
            ["media"] = media,
            ["response"] = response,
        };

        var path = FullPath(dataDir, scrape.Provider, scrape.Game);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var temp = path + ".tmp-" + Guid.NewGuid().ToString("N");
        File.WriteAllText(temp, json.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        File.Move(temp, path, overwrite: true);
    }

    /// <summary>Null when there's no file, or it can't be read.</summary>
    public static SavedScrape? Load(string dataDir, string provider, GameKey game)
    {
        var path = FullPath(dataDir, provider, game);
        if (!File.Exists(path))
        {
            return null;
        }

        string text;
        try
        {
            text = File.ReadAllText(path);
        }
        catch (IOException)
        {
            return null;
        }

        using var document = LenientJson.Parse(text);
        if (document is null || document.RootElement.Str("status") is not { } status)
        {
            return null;
        }

        var root = document.RootElement;
        var media = new List<SavedMedia>();
        foreach (var m in root.Arr("media"))
        {
            if (m.Str("kind") is { } kind && m.Str("path") is { } mediaPath)
            {
                media.Add(new SavedMedia(kind, mediaPath, (int)(m.Num("width") ?? 0), (int)(m.Num("height") ?? 0)));
            }
        }

        string? response = null;
        if (root.TryGetProperty("response", out var raw) && raw.ValueKind != JsonValueKind.Null)
        {
            response = raw.ValueKind == JsonValueKind.String ? raw.GetString() : raw.GetRawText();
        }

        return new SavedScrape(provider, game, status, root.Str("game_id"), root.Str("method"), (long)(root.Num("scraped_at") ?? 0), media, response);
    }

    /// <summary>Deletes the game's saved responses from every provider. Returns how many files went.</summary>
    public static int Delete(string dataDir, GameKey game)
    {
        var deleted = 0;
        foreach (var provider in ConfigLoader.Scrapers)
        {
            var path = FullPath(dataDir, provider, game);
            if (File.Exists(path))
            {
                File.Delete(path);
                deleted++;
            }
        }

        return deleted;
    }

    /// <summary>
    /// Reads a saved response back into a game with the provider's own parser, offline. Null when it isn't a
    /// response the parser understands.
    /// </summary>
    public static ScrapedGame? Parse(SavedScrape scrape, ScrapingSettings settings, SystemConfig system)
    {
        ArgumentNullException.ThrowIfNull(scrape);
        if (scrape.Response is null)
        {
            return null;
        }

        return scrape.Provider switch
        {
            ScraperIds.ScreenScraper => ScreenScraperScraper.Parse(scrape.Response, settings),
            ScraperIds.SteamGridDb => SteamGridDbScraper.Parse(scrape.Response),
            ScraperIds.Igdb => IgdbScraper.Parse(scrape.Response, settings, system),
            _ => null,
        };
    }
}
