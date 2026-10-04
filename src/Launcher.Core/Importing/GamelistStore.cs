using Launcher.Core.Library;
using Launcher.Core.Scanning;
using Launcher.Core.Scraping;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Importing;

/// <summary>What the library knows about one of a system's games, for planning an import.</summary>
/// <param name="RomDir">The ROM folder it was scanned in (absolute).</param>
/// <param name="Values">Its effective metadata: the user's value, else the scraped one (null: neither).</param>
/// <param name="HasTitle">The user's title, or a scraped one.</param>
/// <param name="HasScreenScraperMatch">A stored or manual ScreenScraper match.</param>
internal sealed record GamelistLibraryGame(
    GameKey Key,
    string RelPath,
    string RomDir,
    int? Disc,
    bool HasTitle,
    MetadataOverride Values,
    bool IsFavourite,
    bool HasScreenScraperMatch,
    IReadOnlySet<string> MediaKinds);

/// <summary>The SQL behind the gamelist import. Each method runs on a connection it's given (a reader's, or the writer's).</summary>
internal static class GamelistStore
{
    /// <summary>The system's ROM folders as last scanned, in order (absolute).</summary>
    public static List<string> RomDirs(SqliteConnection connection, string systemId)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT path FROM rom_dirs WHERE system_id = $system ORDER BY position";
        command.Parameters.AddWithValue("$system", systemId);
        using var reader = command.ExecuteReader();
        var dirs = new List<string>();
        while (reader.Read())
        {
            dirs.Add(reader.GetString(0));
        }

        return dirs;
    }

    /// <summary>Every game of the system, by <c>path_key</c>. Needs <c>userdata.db</c> attached as <c>user</c>.</summary>
    public static Dictionary<string, GamelistLibraryGame> Games(SqliteConnection connection, string systemId)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT g.path_key, g.rel_path, d.path, g.disc, COALESCE(o.title, mt.title) IS NOT NULL,
                   COALESCE(o.description, mt.description), COALESCE(o.release_date, mt.release_date),
                   COALESCE(o.developer, mt.developer), COALESCE(o.publisher, mt.publisher), COALESCE(o.genre, mt.genre),
                   COALESCE(o.players, mt.players), COALESCE(o.rating, mt.rating),
                   f.path_key IS NOT NULL,
                   EXISTS (SELECT 1 FROM scraper_matches sm WHERE sm.game_id = g.game_id AND sm.scraper = $ss)
                       OR EXISTS (SELECT 1 FROM user.manual_matches mm WHERE mm.system_id = g.system_id AND mm.path_key = g.path_key AND mm.scraper = $ss),
                   (SELECT group_concat(m.kind) FROM media m WHERE m.game_id = g.game_id)
            FROM games g
            JOIN rom_dirs d ON d.dir_id = g.dir_id
            LEFT JOIN metadata mt ON mt.game_id = g.game_id
            LEFT JOIN user.game_overrides o ON o.system_id = g.system_id AND o.path_key = g.path_key
            LEFT JOIN user.favourites f ON f.system_id = g.system_id AND f.path_key = g.path_key
            WHERE g.system_id = $system
            """;
        command.Parameters.AddWithValue("$system", systemId);
        command.Parameters.AddWithValue("$ss", ScraperIds.ScreenScraper);
        using var reader = command.ExecuteReader();
        var games = new Dictionary<string, GamelistLibraryGame>(StringComparer.Ordinal);
        while (reader.Read())
        {
            string? Text(int i) => reader.IsDBNull(i) ? null : reader.GetString(i);
            var key = reader.GetString(0);
            var kinds = Text(14) is { } list
                ? new HashSet<string>(list.Split(','), StringComparer.Ordinal)
                : new HashSet<string>(StringComparer.Ordinal);
            games[key] = new GamelistLibraryGame(
                new GameKey(systemId, key),
                reader.GetString(1),
                reader.GetString(2),
                reader.IsDBNull(3) ? null : reader.GetInt32(3),
                reader.GetBoolean(4),
                new MetadataOverride(Text(5), Text(6), Text(7), Text(8), Text(9), Text(10), reader.IsDBNull(11) ? null : reader.GetDouble(11)),
                reader.GetBoolean(12),
                reader.GetBoolean(13),
                kinds);
        }

        return games;
    }

    /// <summary>
    /// Writes a game's imported title and metadata as the user's own (userdata.db), filling only what the user hasn't
    /// set: a value the user set meanwhile wins.
    /// </summary>
    public static void FillOverrides(SqliteConnection connection, SqliteTransaction transaction, GameKey game, string? title, MetadataOverride values)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            INSERT INTO user.game_overrides (system_id, path_key, title, sort_title, description, release_date, developer, publisher, genre, players, rating)
            VALUES ($system, $key, $title, $sort, $description, $release, $developer, $publisher, $genre, $players, $rating)
            ON CONFLICT (system_id, path_key) DO UPDATE SET
                title = COALESCE(title, excluded.title),
                sort_title = CASE WHEN title IS NULL THEN excluded.sort_title ELSE sort_title END,
                description = COALESCE(description, excluded.description),
                release_date = COALESCE(release_date, excluded.release_date),
                developer = COALESCE(developer, excluded.developer),
                publisher = COALESCE(publisher, excluded.publisher),
                genre = COALESCE(genre, excluded.genre),
                players = COALESCE(players, excluded.players),
                rating = COALESCE(rating, excluded.rating)
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$title", (object?)title ?? DBNull.Value);
        command.Parameters.AddWithValue("$sort", title is null ? DBNull.Value : TitleParser.SortKey(title));
        command.Parameters.AddWithValue("$description", (object?)values.Description ?? DBNull.Value);
        command.Parameters.AddWithValue("$release", (object?)values.ReleaseDate ?? DBNull.Value);
        command.Parameters.AddWithValue("$developer", (object?)values.Developer ?? DBNull.Value);
        command.Parameters.AddWithValue("$publisher", (object?)values.Publisher ?? DBNull.Value);
        command.Parameters.AddWithValue("$genre", (object?)values.Genre ?? DBNull.Value);
        command.Parameters.AddWithValue("$players", (object?)values.Players ?? DBNull.Value);
        command.Parameters.AddWithValue("$rating", (object?)values.Rating ?? DBNull.Value);
        command.ExecuteNonQuery();
    }

    public static void AddFavourite(SqliteConnection connection, SqliteTransaction transaction, GameKey game, long now)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = "INSERT INTO user.favourites (system_id, path_key, added_at) VALUES ($system, $key, $now) ON CONFLICT DO NOTHING";
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$now", now);
        command.ExecuteNonQuery();
    }

    /// <summary>
    /// Stores the gamelist's ScreenScraper id as the game's match (library.db, method <see cref="MatchMethods.Gamelist"/>),
    /// unless it has one already, stored or manual. Returns whether it was stored.
    /// </summary>
    public static bool AddScreenScraperMatch(SqliteConnection connection, SqliteTransaction transaction, GameKey game, string id, long now)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            INSERT INTO scraper_matches (game_id, scraper, scraper_game_id, method, matched_at)
            SELECT g.game_id, $ss, $id, $method, $now FROM games g
            WHERE g.system_id = $system AND g.path_key = $key
              AND NOT EXISTS (SELECT 1 FROM user.manual_matches mm WHERE mm.system_id = g.system_id AND mm.path_key = g.path_key AND mm.scraper = $ss)
            ON CONFLICT (game_id, scraper) DO NOTHING
            """;
        command.Parameters.AddWithValue("$ss", ScraperIds.ScreenScraper);
        command.Parameters.AddWithValue("$id", id);
        command.Parameters.AddWithValue("$method", MatchMethods.Gamelist);
        command.Parameters.AddWithValue("$now", now);
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        return command.ExecuteNonQuery() > 0;
    }
}
