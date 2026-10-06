using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Scanning;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Scraping;

/// <summary>What the library knows about a game before it's scraped.</summary>
/// <param name="FileTitle">The cleaned file-name title (not a scraped one).</param>
/// <param name="StoredMatches">Automatic matches in library.db: provider → (id, method).</param>
/// <param name="ManualMatches">Manual matches in userdata.db, which win: provider → id.</param>
/// <param name="Media">Current media rows: kind → (path, size, mtime).</param>
/// <param name="TitleOverride">The user's title for the game (userdata.db), or null.</param>
public sealed record GameContext(
    GameKey Key,
    long GameId,
    string RelPath,
    string RomPath,
    long SizeBytes,
    string FileTitle,
    int? Disc,
    RomHashes? Hashes,
    IReadOnlyDictionary<string, (string Id, string Method)> StoredMatches,
    IReadOnlyDictionary<string, string> ManualMatches,
    IReadOnlyDictionary<string, (string Path, long? SizeBytes, long? MtimeMs)> Media,
    string? TitleOverride = null)
{
    /// <summary>The providers with a manual match, the most recently chosen first: they're asked first, in this order.</summary>
    public IReadOnlyList<string> ManualOrder { get; init; } = [];
}

/// <summary>A provider's outcome, for <c>scrape_log</c>.</summary>
/// <param name="Status">'ok', 'not_found' or 'error'.</param>
public sealed record ProviderLog(string Provider, string Status, string? Detail);

/// <summary>Everything one scrape writes, in one transaction.</summary>
/// <param name="Metadata">Null leaves the game's metadata as it is (nothing was found).</param>
/// <param name="Matches">Provider → (id, method).</param>
/// <param name="Status">'ok', 'partial', 'not_found' or 'error'.</param>
/// <param name="Gone">
/// Media rows whose files are no longer on disk (deleted by hand since the last scan): removed, unless a download
/// in <paramref name="Media"/> takes their kind's place.
/// </param>
public sealed record ScrapeWrite(
    MergedMetadata? Metadata,
    IReadOnlyDictionary<string, (string Id, string Method)> Matches,
    IReadOnlyList<(string Kind, StoredMedia Media)> Media,
    IReadOnlyList<ProviderLog> Log,
    string Status,
    IReadOnlyList<string> Providers,
    long At,
    IReadOnlyList<(string Kind, string Path)>? Gone = null);

/// <summary>A scrape job taken from the queue.</summary>
public sealed record QueuedJob(long BatchId, long Seq, GameKey Game);

/// <summary>A batch in <c>userdata.db</c>.</summary>
public sealed record ScrapeBatchInfo(long BatchId, string Kind, string? Target, int Total, int Done, int Failed, int Pending, DateTimeOffset CreatedAt, bool Finished, bool Cancelled);

/// <summary>The SQL behind scraping. Every method runs on a connection it's given (the library writer's, or a reader's).</summary>
internal static class ScrapeStore
{
    public static GameContext? LoadContext(SqliteConnection connection, GameKey key)
    {
        long gameId;
        string relPath, romDir;
        long size;
        int? disc;
        RomHashes? hashes;
        using (var command = connection.CreateCommand())
        {
            command.CommandText = """
                SELECT g.game_id, g.rel_path, d.path, g.size_bytes, g.disc, g.crc32, g.md5, g.sha1
                FROM games g JOIN rom_dirs d ON d.dir_id = g.dir_id
                WHERE g.system_id = $system AND g.path_key = $key
                """;
            command.Parameters.AddWithValue("$system", key.SystemId);
            command.Parameters.AddWithValue("$key", key.PathKey);
            using var reader = command.ExecuteReader();
            if (!reader.Read())
            {
                return null;
            }

            gameId = reader.GetInt64(0);
            relPath = reader.GetString(1);
            romDir = reader.GetString(2);
            size = reader.GetInt64(3);
            disc = reader.IsDBNull(4) ? null : reader.GetInt32(4);
            hashes = reader.IsDBNull(5) || reader.IsDBNull(6) || reader.IsDBNull(7)
                ? null
                : new RomHashes(reader.GetString(5), reader.GetString(6), reader.GetString(7));
        }

        var stored = new Dictionary<string, (string, string)>(StringComparer.Ordinal);
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT scraper, scraper_game_id, method FROM scraper_matches WHERE game_id = $id";
            command.Parameters.AddWithValue("$id", gameId);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                stored[reader.GetString(0)] = (reader.GetString(1), reader.GetString(2));
            }
        }

        var manualOrder = ManualMatches(connection, key);
        var manual = manualOrder.ToDictionary(m => m.Provider, m => m.Id, StringComparer.Ordinal);

        var media = new Dictionary<string, (string, long?, long?)>(StringComparer.Ordinal);
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT kind, path, size_bytes, mtime_ms FROM media WHERE game_id = $id";
            command.Parameters.AddWithValue("$id", gameId);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                media[reader.GetString(0)] = (reader.GetString(1),
                    reader.IsDBNull(2) ? null : reader.GetInt64(2), reader.IsDBNull(3) ? null : reader.GetInt64(3));
            }
        }

        string? titleOverride;
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT title FROM user.game_overrides WHERE system_id = $system AND path_key = $key";
            command.Parameters.AddWithValue("$system", key.SystemId);
            command.Parameters.AddWithValue("$key", key.PathKey);
            titleOverride = command.ExecuteScalar() as string;
        }

        var fileTitle = TitleParser.Parse(LibraryStore.FileStemOf(relPath)).Title;
        var romPath = Path.GetFullPath(Path.Combine(romDir, relPath.Replace('/', Path.DirectorySeparatorChar)));
        return new GameContext(key, gameId, relPath, romPath, size, fileTitle, disc, hashes, stored, manual, media, titleOverride)
        {
            ManualOrder = manualOrder.Select(m => m.Provider).ToList(),
        };
    }

    /// <summary>
    /// Every game's providers with a manual match (userdata.db, which is small), the most recently chosen first, for a
    /// restore to merge in the order a live scrape asks them. Needs <c>userdata.db</c> attached as <c>user</c>.
    /// </summary>
    public static Dictionary<GameKey, IReadOnlyList<string>> ManualOrders(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT system_id, path_key, scraper FROM user.manual_matches ORDER BY system_id, path_key, matched_at DESC, scraper";
        using var reader = command.ExecuteReader();
        var orders = new Dictionary<GameKey, IReadOnlyList<string>>();
        while (reader.Read())
        {
            var key = new GameKey(reader.GetString(0), reader.GetString(1));
            if (!orders.TryGetValue(key, out var list))
            {
                orders[key] = list = new List<string>();
            }

            ((List<string>)list).Add(reader.GetString(2));
        }

        return orders;
    }

    /// <summary>A game's manual matches (userdata.db), the most recently chosen first.</summary>
    public static List<(string Provider, string Id)> ManualMatches(SqliteConnection connection, GameKey key)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT scraper, scraper_game_id FROM user.manual_matches WHERE system_id = $system AND path_key = $key
            ORDER BY matched_at DESC, scraper
            """;
        command.Parameters.AddWithValue("$system", key.SystemId);
        command.Parameters.AddWithValue("$key", key.PathKey);
        using var reader = command.ExecuteReader();
        var matches = new List<(string, string)>();
        while (reader.Read())
        {
            matches.Add((reader.GetString(0), reader.GetString(1)));
        }

        return matches;
    }

    /// <summary>
    /// Saves the user's choice of a provider's game (userdata.db, keyed by identity, so it survives a rebuild), as
    /// the most recent: choosing a match again puts it first again.
    /// </summary>
    public static void SaveManualMatch(SqliteConnection connection, GameKey key, string provider, string providerGameId, long now)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO user.manual_matches (system_id, path_key, scraper, scraper_game_id, matched_at) VALUES ($system, $key, $scraper, $id, $now)
            ON CONFLICT (system_id, path_key, scraper) DO UPDATE SET scraper_game_id = excluded.scraper_game_id, matched_at = excluded.matched_at
            """;
        command.Parameters.AddWithValue("$system", key.SystemId);
        command.Parameters.AddWithValue("$key", key.PathKey);
        command.Parameters.AddWithValue("$scraper", provider);
        command.Parameters.AddWithValue("$id", providerGameId);
        command.Parameters.AddWithValue("$now", now);
        command.ExecuteNonQuery();
    }

    public static void SaveHashes(SqliteConnection connection, GameKey key, long sizeBytes, RomHashes hashes)
    {
        using var command = connection.CreateCommand();
        // Only if the file is still the one that was hashed.
        command.CommandText = """
            UPDATE games SET crc32 = $crc, md5 = $md5, sha1 = $sha1
            WHERE system_id = $system AND path_key = $key AND size_bytes = $size
            """;
        command.Parameters.AddWithValue("$crc", hashes.Crc32);
        command.Parameters.AddWithValue("$md5", hashes.Md5);
        command.Parameters.AddWithValue("$sha1", hashes.Sha1);
        command.Parameters.AddWithValue("$system", key.SystemId);
        command.Parameters.AddWithValue("$key", key.PathKey);
        command.Parameters.AddWithValue("$size", sizeBytes);
        command.ExecuteNonQuery();
    }

    /// <summary>
    /// Writes a scrape in one transaction, keyed by <see cref="GameKey"/> (never a cached game id, which a rebuild
    /// can change). Media rows are written as a scan would index the files (A4); every userdata.db override is left alone.
    /// Returns false when the game is no longer in the library.
    /// </summary>
    public static bool Save(SqliteConnection connection, GameKey key, ScrapeWrite write) =>
        Save(connection, null, key, write);

    public static bool Save(SqliteConnection connection, SqliteTransaction? outer, GameKey key, ScrapeWrite write)
    {
        var transaction = outer ?? connection.BeginTransaction();
        try
        {
            SqliteCommand Command(string sql)
            {
                var command = connection.CreateCommand();
                command.Transaction = transaction;
                command.CommandText = sql;
                return command;
            }

            long gameId;
            int? disc;
            string relPath;
            using (var find = Command("SELECT game_id, disc, rel_path FROM games WHERE system_id = $system AND path_key = $key"))
            {
                find.Parameters.AddWithValue("$system", key.SystemId);
                find.Parameters.AddWithValue("$key", key.PathKey);
                using var reader = find.ExecuteReader();
                if (!reader.Read())
                {
                    return false;
                }

                gameId = reader.GetInt64(0);
                disc = reader.IsDBNull(1) ? null : reader.GetInt32(1);
                relPath = reader.GetString(2);
            }

            if (write.Metadata is { IsEmpty: false } m)
            {
                using (var upsert = Command("""
                    INSERT INTO metadata (game_id, title, description, release_date, developer, publisher, genre, players, rating, source)
                    VALUES ($id, $title, $description, $release, $developer, $publisher, $genre, $players, $rating, $source)
                    ON CONFLICT (game_id) DO UPDATE SET title = excluded.title, description = excluded.description,
                        release_date = excluded.release_date, developer = excluded.developer, publisher = excluded.publisher,
                        genre = excluded.genre, players = excluded.players, rating = excluded.rating, source = excluded.source
                    """))
                {
                    upsert.Parameters.AddWithValue("$id", gameId);
                    upsert.Parameters.AddWithValue("$title", (object?)m.Title ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$description", (object?)m.Description ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$release", (object?)m.ReleaseDate ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$developer", (object?)m.Developer ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$publisher", (object?)m.Publisher ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$genre", (object?)m.Genre ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$players", (object?)m.Players ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$rating", (object?)m.Rating ?? DBNull.Value);
                    upsert.Parameters.AddWithValue("$source", string.Join(',', m.Sources));
                    upsert.ExecuteNonQuery();
                }

                // games.title holds the scraped title for the grid query; a lone disc keeps its number (A4).
                var title = m.Title ?? TitleParser.Parse(LibraryStore.FileStemOf(relPath)).Title;
                if (m.Title is not null && disc is { } n)
                {
                    title += $" (Disc {n})";
                }

                using var titles = Command("UPDATE games SET title = $title, sort_title = $sort WHERE game_id = $id");
                titles.Parameters.AddWithValue("$title", title);
                titles.Parameters.AddWithValue("$sort", TitleParser.SortKey(title));
                titles.Parameters.AddWithValue("$id", gameId);
                titles.ExecuteNonQuery();
            }

            foreach (var (provider, (id, method)) in write.Matches)
            {
                using var match = Command("""
                    INSERT INTO scraper_matches (game_id, scraper, scraper_game_id, method, matched_at) VALUES ($id, $scraper, $gid, $method, $at)
                    ON CONFLICT (game_id, scraper) DO UPDATE SET scraper_game_id = excluded.scraper_game_id, method = excluded.method,
                        matched_at = CASE WHEN scraper_game_id = excluded.scraper_game_id THEN matched_at ELSE excluded.matched_at END
                    """);
                match.Parameters.AddWithValue("$id", gameId);
                match.Parameters.AddWithValue("$scraper", provider);
                match.Parameters.AddWithValue("$gid", id);
                match.Parameters.AddWithValue("$method", method);
                match.Parameters.AddWithValue("$at", write.At);
                match.ExecuteNonQuery();
            }

            foreach (var (kind, path) in write.Gone ?? [])
            {
                using var gone = Command("DELETE FROM media WHERE game_id = $id AND kind = $kind AND path = $path");
                gone.Parameters.AddWithValue("$id", gameId);
                gone.Parameters.AddWithValue("$kind", kind);
                gone.Parameters.AddWithValue("$path", path);
                gone.ExecuteNonQuery();
            }

            foreach (var (kind, stored) in write.Media)
            {
                // A download is the game's file, named without the ROM's extension (MediaStore.PathFor), as a scan finds it.
                using var media = Command("""
                    INSERT INTO media (game_id, kind, path, width, height, size_bytes, mtime_ms)
                    VALUES ($id, $kind, $path, $width, $height, $size, $mtime)
                    ON CONFLICT (game_id, kind) DO UPDATE SET path = excluded.path, width = excluded.width, height = excluded.height,
                        size_bytes = excluded.size_bytes, mtime_ms = excluded.mtime_ms
                    """);
                media.Parameters.AddWithValue("$id", gameId);
                media.Parameters.AddWithValue("$kind", kind);
                media.Parameters.AddWithValue("$path", stored.RelativePath);
                media.Parameters.AddWithValue("$width", stored.Width > 0 ? stored.Width : DBNull.Value);    // a video has no size
                media.Parameters.AddWithValue("$height", stored.Height > 0 ? stored.Height : DBNull.Value);
                media.Parameters.AddWithValue("$size", stored.SizeBytes);
                media.Parameters.AddWithValue("$mtime", stored.MtimeMs);
                media.ExecuteNonQuery();
            }

            foreach (var entry in write.Log)
            {
                using var log = Command("""
                    INSERT INTO scrape_log (game_id, scraper, status, attempted_at, detail) VALUES ($id, $scraper, $status, $at, $detail)
                    ON CONFLICT (game_id, scraper) DO UPDATE SET status = excluded.status, attempted_at = excluded.attempted_at, detail = excluded.detail
                    """);
                log.Parameters.AddWithValue("$id", gameId);
                log.Parameters.AddWithValue("$scraper", entry.Provider);
                log.Parameters.AddWithValue("$status", entry.Status);
                log.Parameters.AddWithValue("$at", write.At);
                log.Parameters.AddWithValue("$detail", (object?)entry.Detail ?? DBNull.Value);
                log.ExecuteNonQuery();
            }

            using (var state = Command("""
                INSERT INTO scrape_state (game_id, status, providers, scraped_at) VALUES ($id, $status, $providers, $at)
                ON CONFLICT (game_id) DO UPDATE SET status = excluded.status, providers = excluded.providers, scraped_at = excluded.scraped_at
                """))
            {
                state.Parameters.AddWithValue("$id", gameId);
                state.Parameters.AddWithValue("$status", write.Status);
                state.Parameters.AddWithValue("$providers", write.Providers.Count == 0 ? DBNull.Value : string.Join(',', write.Providers));
                state.Parameters.AddWithValue("$at", write.At);
                state.ExecuteNonQuery();
            }

            if (outer is null)
            {
                transaction.Commit();
            }

            return true;
        }
        finally
        {
            if (outer is null)
            {
                transaction.Dispose();
            }
        }
    }

    /// <summary>
    /// <see cref="Save"/>, then everything the <paramref name="replaced"/> providers had supplied that this scrape
    /// didn't supply again goes, in the same transaction: the providers whose manual match answered, so a match the
    /// user corrected leaves none of the wrong game's metadata behind. Goes: their matches and log rows not just
    /// written, and the metadata row when nothing was found and only they had supplied it (the title goes back to the
    /// file name's). Media files aren't the providers' to take back (A4): what's in the media folder stays.
    /// Returns false when the game isn't in the library.
    /// </summary>
    public static bool SaveReplacing(SqliteConnection connection, GameKey key, ScrapeWrite write, IReadOnlySet<string> replaced)
    {
        using var transaction = connection.BeginTransaction();
        if (!Save(connection, transaction, key, write))
        {
            return false;
        }

        SqliteCommand Command(string sql)
        {
            var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText = sql;
            command.Parameters.AddWithValue("$system", key.SystemId);
            command.Parameters.AddWithValue("$key", key.PathKey);
            return command;
        }

        long gameId;
        string relPath;
        using (var find = Command("SELECT game_id, rel_path FROM games WHERE system_id = $system AND path_key = $key"))
        using (var reader = find.ExecuteReader())
        {
            reader.Read();
            gameId = reader.GetInt64(0);
            relPath = reader.GetString(1);
        }

        var logged = write.Log.Select(l => l.Provider).ToHashSet(StringComparer.Ordinal);
        foreach (var provider in replaced)
        {
            if (!write.Matches.ContainsKey(provider))
            {
                using var match = Command("DELETE FROM scraper_matches WHERE game_id = $id AND scraper = $scraper");
                match.Parameters.AddWithValue("$id", gameId);
                match.Parameters.AddWithValue("$scraper", provider);
                match.ExecuteNonQuery();
            }

            if (!logged.Contains(provider))
            {
                using var log = Command("DELETE FROM scrape_log WHERE game_id = $id AND scraper = $scraper");
                log.Parameters.AddWithValue("$id", gameId);
                log.Parameters.AddWithValue("$scraper", provider);
                log.ExecuteNonQuery();
            }
        }

        if (write.Metadata is null or { IsEmpty: true })
        {
            string? sources;
            using (var source = Command("SELECT source FROM metadata WHERE game_id = $id"))
            {
                source.Parameters.AddWithValue("$id", gameId);
                sources = source.ExecuteScalar() as string;
            }

            if (sources is not null && sources.Split(',', StringSplitOptions.RemoveEmptyEntries).All(replaced.Contains))
            {
                using (var delete = Command("DELETE FROM metadata WHERE game_id = $id"))
                {
                    delete.Parameters.AddWithValue("$id", gameId);
                    delete.ExecuteNonQuery();
                }

                var title = TitleParser.Parse(LibraryStore.FileStemOf(relPath));
                using var titles = Command("UPDATE games SET title = $title, sort_title = $sort WHERE game_id = $id");
                titles.Parameters.AddWithValue("$title", title.Title);
                titles.Parameters.AddWithValue("$sort", title.SortTitle);
                titles.Parameters.AddWithValue("$id", gameId);
                titles.ExecuteNonQuery();
            }
        }

        transaction.Commit();
        return true;
    }

    /// <summary>What <see cref="Clear"/> removed from the DB, so the caller can delete the files.</summary>
    /// <param name="RelPath">The game's <c>rel_path</c>, which its own media files are named after; null if it isn't in the library.</param>
    /// <param name="Media">Every media row the game had: (kind, path, size, mtime), for its file and derivative.</param>
    /// <param name="Shared">Media files another game also uses (matched by stem): their rows went, but the files stay.</param>
    /// <param name="NameShared">
    /// Another of the system's games has the same name without its extension (<c>Game.chd</c> beside <c>Game.cue</c>), so
    /// media named that way (<see cref="MediaStore.NameOf"/>) is that game's too, indexed or not.
    /// </param>
    public sealed record Cleared(bool Found, string? RelPath, IReadOnlyList<(string Kind, string Path, long? SizeBytes, long? MtimeMs)> Media, IReadOnlyList<string> Shared,
        bool NameShared = false);

    /// <summary>
    /// Clears everything scraped and every metadata override: metadata, scrape state and log, every match (manual
    /// ones too), every media row, and the title back to the file name. The emulator override, hidden flag,
    /// favourite and play history stay.
    /// </summary>
    public static Cleared Clear(SqliteConnection connection, GameKey key)
    {
        using var transaction = connection.BeginTransaction();
        SqliteCommand Command(string sql)
        {
            var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText = sql;
            command.Parameters.AddWithValue("$system", key.SystemId);
            command.Parameters.AddWithValue("$key", key.PathKey);
            return command;
        }

        long? gameId = null;
        string? relPath = null;
        using (var find = Command("SELECT game_id, rel_path FROM games WHERE system_id = $system AND path_key = $key"))
        using (var reader = find.ExecuteReader())
        {
            if (reader.Read())
            {
                gameId = reader.GetInt64(0);
                relPath = reader.GetString(1);
            }
        }

        var media = new List<(string, string, long?, long?)>();
        var shared = new List<string>();
        var nameShared = false;
        if (gameId is { } id)
        {
            using (var select = Command("SELECT kind, path, size_bytes, mtime_ms FROM media WHERE game_id = $id"))
            {
                select.Parameters.AddWithValue("$id", id);
                using var reader = select.ExecuteReader();
                while (reader.Read())
                {
                    media.Add((reader.GetString(0), reader.GetString(1), reader.IsDBNull(2) ? null : reader.GetInt64(2), reader.IsDBNull(3) ? null : reader.GetInt64(3)));
                }
            }

            foreach (var (_, path, _, _) in media)
            {
                using var others = Command("SELECT COUNT(*) FROM media WHERE path = $path AND game_id <> $id");
                others.Parameters.AddWithValue("$path", path);
                others.Parameters.AddWithValue("$id", id);
                if ((long)others.ExecuteScalar()! > 0)
                {
                    shared.Add(path);
                }
            }

            // Other games named the same but for the extension: path keys starting with the name and a dot.
            var name = PathKeys.ToPathKey(MediaStore.NameOf(relPath!));
            if (name.Length < key.PathKey.Length)
            {
                using var siblings = Command("SELECT path_key FROM games WHERE system_id = $system AND game_id <> $id AND substr(path_key, 1, $length) = $prefix");
                siblings.Parameters.AddWithValue("$id", id);
                siblings.Parameters.AddWithValue("$length", name.Length + 1);
                siblings.Parameters.AddWithValue("$prefix", name + ".");
                using var reader = siblings.ExecuteReader();
                while (reader.Read())
                {
                    if (string.Equals(MediaStore.NameOf(reader.GetString(0)), name, StringComparison.Ordinal))
                    {
                        nameShared = true;
                        break;
                    }
                }
            }

            foreach (var table in (ReadOnlySpan<string>)["metadata", "scrape_state", "scrape_log", "scraper_matches", "media"])
            {
                using var delete = Command($"DELETE FROM {table} WHERE game_id = $id");
                delete.Parameters.AddWithValue("$id", id);
                delete.ExecuteNonQuery();
            }

            var title = TitleParser.Parse(LibraryStore.FileStemOf(relPath!));
            using var titles = Command("UPDATE games SET title = $title, sort_title = $sort WHERE game_id = $id");
            titles.Parameters.AddWithValue("$title", title.Title);
            titles.Parameters.AddWithValue("$sort", title.SortTitle);
            titles.Parameters.AddWithValue("$id", id);
            titles.ExecuteNonQuery();
        }

        // userdata.db is keyed by identity, so clear it even for a game that's gone from the library.
        using (var overrides = Command("""
            UPDATE user.game_overrides SET title = NULL, sort_title = NULL, description = NULL, release_date = NULL,
                developer = NULL, publisher = NULL, genre = NULL, players = NULL, rating = NULL
            WHERE system_id = $system AND path_key = $key
            """))
        {
            overrides.ExecuteNonQuery();
        }

        using (var manual = Command("DELETE FROM user.manual_matches WHERE system_id = $system AND path_key = $key"))
        {
            manual.ExecuteNonQuery();
        }

        transaction.Commit();
        return new Cleared(gameId is not null, relPath, media, shared, nameShared);
    }

    // ---- Selection --------------------------------------------------------------------------------

    /// <summary>
    /// A system's games that <paramref name="filter"/> picks, in grid order. <paramref name="recentSince"/> (unix ms) is
    /// when a scrape starts to count as recent, for <see cref="SystemScrapeFilter.NotRecent"/>.
    /// </summary>
    public static List<GameKey> SystemGames(SqliteConnection connection, string systemId, SystemScrapeFilter filter = SystemScrapeFilter.All, long recentSince = 0)
    {
        using var command = connection.CreateCommand();
        var condition = filter switch
        {
            SystemScrapeFilter.NoCover => $" AND {NoMedia("cover")}",
            SystemScrapeFilter.NoScreenshot => $" AND {NoMedia("screenshot")}",
            SystemScrapeFilter.NotRecent => " AND " + NotRecent,
            _ => string.Empty,
        };
        command.CommandText = $"SELECT g.path_key FROM games g WHERE g.system_id = $system{condition} ORDER BY g.sort_title, g.game_id";
        command.Parameters.AddWithValue("$system", systemId);
        command.Parameters.AddWithValue("$since", recentSince);
        using var reader = command.ExecuteReader();
        var keys = new List<GameKey>();
        while (reader.Read())
        {
            keys.Add(new GameKey(systemId, reader.GetString(0)));
        }

        return keys;
    }

    /// <summary>
    /// A system's games, its "missing" ones (as <see cref="MissingGames"/>) and each <see cref="SystemScrapeFilter"/>'s,
    /// counted in one pass. <paramref name="recentSince"/> as for <see cref="SystemGames"/>.
    /// </summary>
    public static SystemScrapeCount CountSystem(SqliteConnection connection, string systemId, long recentSince)
    {
        using var command = connection.CreateCommand();
        command.CommandText = $"""
            SELECT COUNT(*),
                   COALESCE(SUM(CASE WHEN s.status IS NULL OR s.status IN ('not_found', 'error') OR {NoMedia("cover")} THEN 1 ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN {NoMedia("cover")} THEN 1 ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN {NoMedia("screenshot")} THEN 1 ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN {NotRecent} THEN 1 ELSE 0 END), 0)
            FROM games g
            LEFT JOIN scrape_state s ON s.game_id = g.game_id
            WHERE g.system_id = $system
            """;
        command.Parameters.AddWithValue("$system", systemId);
        command.Parameters.AddWithValue("$since", recentSince);
        using var reader = command.ExecuteReader();
        reader.Read();
        return new SystemScrapeCount(reader.GetInt32(0), reader.GetInt32(1), reader.GetInt32(2), reader.GetInt32(3), reader.GetInt32(4));
    }

    /// <summary>SQL that's true when game <c>g</c> has no file of <paramref name="kind"/> (a constant, never user text).</summary>
    private static string NoMedia(string kind) => $"NOT EXISTS (SELECT 1 FROM media m WHERE m.game_id = g.game_id AND m.kind = '{kind}')";

    /// <summary>SQL that's true when game <c>g</c> was never scraped, or last scraped before <c>$since</c>.</summary>
    private const string NotRecent = "NOT EXISTS (SELECT 1 FROM scrape_state r WHERE r.game_id = g.game_id AND r.scraped_at >= $since)";

    /// <summary>
    /// "Missing" (M4): never successfully scraped (no state, or not found or failed), plus every game with no front
    /// cover. In config order of systems, then grid order.
    /// </summary>
    public static List<GameKey> MissingGames(SqliteConnection connection, AppConfig config)
    {
        var keys = new List<GameKey>();
        foreach (var system in config.Systems)
        {
            using var command = connection.CreateCommand();
            command.CommandText = """
                SELECT g.path_key FROM games g
                LEFT JOIN scrape_state s ON s.game_id = g.game_id
                LEFT JOIN media m ON m.game_id = g.game_id AND m.kind = 'cover'
                WHERE g.system_id = $system
                  AND (s.status IS NULL OR s.status IN ('not_found', 'error') OR m.game_id IS NULL)
                ORDER BY g.sort_title, g.game_id
                """;
            command.Parameters.AddWithValue("$system", system.Id);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                keys.Add(new GameKey(system.Id, reader.GetString(0)));
            }
        }

        return keys;
    }

    /// <summary>Every indexed file of the given kinds, with its size and time, once each (a file several games share is one entry).</summary>
    public static List<(string Path, long SizeBytes, long MtimeMs)> MediaOfKinds(SqliteConnection connection, IReadOnlyList<string> kinds)
    {
        using var command = connection.CreateCommand();
        var names = new string[kinds.Count];
        for (var i = 0; i < kinds.Count; i++)
        {
            names[i] = "$k" + i.ToString(System.Globalization.CultureInfo.InvariantCulture);
            command.Parameters.AddWithValue(names[i], kinds[i]);
        }

        command.CommandText = $"""
            SELECT DISTINCT path, size_bytes, mtime_ms FROM media
            WHERE kind IN ({string.Join(", ", names)}) AND size_bytes IS NOT NULL AND mtime_ms IS NOT NULL
            """;
        using var reader = command.ExecuteReader();
        var rows = new List<(string, long, long)>();
        while (reader.Read())
        {
            rows.Add((reader.GetString(0), reader.GetInt64(1), reader.GetInt64(2)));
        }

        return rows;
    }

    // ---- The queue (userdata.db) -------------------------------------------------------------------

    public static long CreateBatch(SqliteConnection connection, string kind, string? target, int priority, IReadOnlyList<GameKey> games, long now)
    {
        using var transaction = connection.BeginTransaction();
        long batchId;
        using (var insert = connection.CreateCommand())
        {
            insert.Transaction = transaction;
            insert.CommandText = """
                INSERT INTO user.scrape_batches (kind, target, priority, total, created_at) VALUES ($kind, $target, $priority, $total, $now)
                RETURNING batch_id
                """;
            insert.Parameters.AddWithValue("$kind", kind);
            insert.Parameters.AddWithValue("$target", (object?)target ?? DBNull.Value);
            insert.Parameters.AddWithValue("$priority", priority);
            insert.Parameters.AddWithValue("$total", games.Count);
            insert.Parameters.AddWithValue("$now", now);
            batchId = (long)insert.ExecuteScalar()!;
        }

        using (var job = connection.CreateCommand())
        {
            job.Transaction = transaction;
            job.CommandText = "INSERT INTO user.scrape_jobs (batch_id, seq, system_id, path_key) VALUES ($batch, $seq, $system, $key)";
            var batch = job.Parameters.Add("$batch", SqliteType.Integer);
            var seq = job.Parameters.Add("$seq", SqliteType.Integer);
            var system = job.Parameters.Add("$system", SqliteType.Text);
            var key = job.Parameters.Add("$key", SqliteType.Text);
            batch.Value = batchId;
            for (var i = 0; i < games.Count; i++)
            {
                seq.Value = i;
                system.Value = games[i].SystemId;
                key.Value = games[i].PathKey;
                job.ExecuteNonQuery();
            }
        }

        if (games.Count == 0)
        {
            using var finish = connection.CreateCommand();
            finish.Transaction = transaction;
            finish.CommandText = "UPDATE user.scrape_batches SET finished_at = $now WHERE batch_id = $batch";
            finish.Parameters.AddWithValue("$now", now);
            finish.Parameters.AddWithValue("$batch", batchId);
            finish.ExecuteNonQuery();
        }

        transaction.Commit();
        return batchId;
    }

    /// <summary>The next jobs to run: single games first, then batches in the order they were asked for.</summary>
    /// <param name="exclude">Jobs already running, which stay in the table until they finish.</param>
    public static List<QueuedJob> NextJobs(SqliteConnection connection, int limit, IReadOnlyCollection<(long, long)> exclude)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT j.batch_id, j.seq, j.system_id, j.path_key
            FROM user.scrape_jobs j JOIN user.scrape_batches b ON b.batch_id = j.batch_id
            WHERE b.finished_at IS NULL
            ORDER BY b.priority, b.batch_id, j.seq
            LIMIT $limit
            """;
        command.Parameters.AddWithValue("$limit", limit + exclude.Count);
        using var reader = command.ExecuteReader();
        var jobs = new List<QueuedJob>();
        while (reader.Read() && jobs.Count < limit)
        {
            var id = (reader.GetInt64(0), reader.GetInt64(1));
            if (!exclude.Contains(id))
            {
                jobs.Add(new QueuedJob(id.Item1, id.Item2, new GameKey(reader.GetString(2), reader.GetString(3))));
            }
        }

        return jobs;
    }

    /// <summary>Marks a job done (deleting it) and counts it. Finishes the batch when it was the last. Returns the batch.</summary>
    public static ScrapeBatchInfo? CompleteJob(SqliteConnection connection, QueuedJob job, bool failed, long now)
    {
        using var transaction = connection.BeginTransaction();
        using (var delete = connection.CreateCommand())
        {
            delete.Transaction = transaction;
            delete.CommandText = "DELETE FROM user.scrape_jobs WHERE batch_id = $batch AND seq = $seq";
            delete.Parameters.AddWithValue("$batch", job.BatchId);
            delete.Parameters.AddWithValue("$seq", job.Seq);
            if (delete.ExecuteNonQuery() == 0)
            {
                // Cancelled while it ran.
                transaction.Commit();
                return GetBatch(connection, job.BatchId);
            }
        }

        using (var count = connection.CreateCommand())
        {
            count.Transaction = transaction;
            count.CommandText = failed
                ? "UPDATE user.scrape_batches SET done = done + 1, failed = failed + 1 WHERE batch_id = $batch"
                : "UPDATE user.scrape_batches SET done = done + 1 WHERE batch_id = $batch";
            count.Parameters.AddWithValue("$batch", job.BatchId);
            count.ExecuteNonQuery();
        }

        using (var finish = connection.CreateCommand())
        {
            finish.Transaction = transaction;
            finish.CommandText = """
                UPDATE user.scrape_batches SET finished_at = $now
                WHERE batch_id = $batch AND finished_at IS NULL
                  AND NOT EXISTS (SELECT 1 FROM user.scrape_jobs WHERE batch_id = $batch)
                """;
            finish.Parameters.AddWithValue("$now", now);
            finish.Parameters.AddWithValue("$batch", job.BatchId);
            finish.ExecuteNonQuery();
        }

        transaction.Commit();
        return GetBatch(connection, job.BatchId);
    }

    /// <summary>Drops a batch's remaining jobs and marks it finished and cancelled.</summary>
    public static void CancelBatch(SqliteConnection connection, long batchId, long now)
    {
        using var transaction = connection.BeginTransaction();
        using (var delete = connection.CreateCommand())
        {
            delete.Transaction = transaction;
            delete.CommandText = "DELETE FROM user.scrape_jobs WHERE batch_id = $batch";
            delete.Parameters.AddWithValue("$batch", batchId);
            delete.ExecuteNonQuery();
        }

        using (var update = connection.CreateCommand())
        {
            update.Transaction = transaction;
            update.CommandText = "UPDATE user.scrape_batches SET cancelled = 1, finished_at = COALESCE(finished_at, $now) WHERE batch_id = $batch";
            update.Parameters.AddWithValue("$now", now);
            update.Parameters.AddWithValue("$batch", batchId);
            update.ExecuteNonQuery();
        }

        transaction.Commit();
    }

    public static ScrapeBatchInfo? GetBatch(SqliteConnection connection, long batchId) =>
        Batches(connection, "WHERE b.batch_id = $batch", batchId).FirstOrDefault();

    public static List<ScrapeBatchInfo> UnfinishedBatches(SqliteConnection connection) =>
        Batches(connection, "WHERE b.finished_at IS NULL ORDER BY b.priority, b.batch_id", null);

    /// <summary>Keeps the newest finished batches' history only.</summary>
    public static void PruneFinished(SqliteConnection connection, int keep)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            DELETE FROM user.scrape_batches WHERE finished_at IS NOT NULL AND batch_id NOT IN
                (SELECT batch_id FROM user.scrape_batches WHERE finished_at IS NOT NULL ORDER BY batch_id DESC LIMIT $keep)
            """;
        command.Parameters.AddWithValue("$keep", keep);
        command.ExecuteNonQuery();
    }

    private static List<ScrapeBatchInfo> Batches(SqliteConnection connection, string where, long? batchId)
    {
        using var command = connection.CreateCommand();
        command.CommandText = $"""
            SELECT b.batch_id, b.kind, b.target, b.total, b.done, b.failed,
                   (SELECT COUNT(*) FROM user.scrape_jobs j WHERE j.batch_id = b.batch_id), b.created_at, b.finished_at IS NOT NULL, b.cancelled
            FROM user.scrape_batches b {where}
            """;
        if (batchId is not null)
        {
            command.Parameters.AddWithValue("$batch", batchId.Value);
        }

        using var reader = command.ExecuteReader();
        var batches = new List<ScrapeBatchInfo>();
        while (reader.Read())
        {
            batches.Add(new ScrapeBatchInfo(
                reader.GetInt64(0), reader.GetString(1), reader.IsDBNull(2) ? null : reader.GetString(2),
                reader.GetInt32(3), reader.GetInt32(4), reader.GetInt32(5), reader.GetInt32(6),
                DateTimeOffset.FromUnixTimeMilliseconds(reader.GetInt64(7)), reader.GetBoolean(8), reader.GetInt64(9) != 0));
        }

        return batches;
    }
}
