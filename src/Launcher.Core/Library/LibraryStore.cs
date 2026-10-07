using Launcher.Core.Config;
using Launcher.Core.Media;
using Launcher.Core.Scanning;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Library;

/// <summary>The SQL behind <see cref="LibraryService"/>. Every method runs on a connection it's given.</summary>
internal static class LibraryStore
{
    // ---- Reads -----------------------------------------------------------------------------------

    public static Dictionary<string, PlaylistEntry> LoadPlaylists(SqliteConnection connection, string systemId)
    {
        var playlists = new Dictionary<string, PlaylistEntry>(StringComparer.Ordinal);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT path_key, size_bytes, mtime_ms, refs FROM playlists WHERE system_id = $system";
        command.Parameters.AddWithValue("$system", systemId);
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var refs = reader.GetString(3);
            var key = reader.GetString(0);
            playlists[key] = new PlaylistEntry(
                key, reader.GetInt64(1), reader.GetInt64(2), refs.Length == 0 ? [] : refs.Split('\n'));
        }

        return playlists;
    }

    /// <summary>The system's indexed images, by stored path, for <see cref="MediaScanner.Scan"/>'s cache.</summary>
    public static Dictionary<string, MediaEntry> LoadMedia(SqliteConnection connection, string systemId)
    {
        var entries = new Dictionary<string, MediaEntry>(StringComparer.Ordinal);
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT m.path, m.size_bytes, m.mtime_ms, m.width, m.height FROM media m JOIN games g ON g.game_id = m.game_id
            WHERE g.system_id = $system AND m.size_bytes IS NOT NULL AND m.mtime_ms IS NOT NULL
              AND m.width IS NOT NULL AND m.height IS NOT NULL
            """;
        command.Parameters.AddWithValue("$system", systemId);
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            // A file matched by several games (by stem) has one row each; they're all the same entry.
            entries.TryAdd(reader.GetString(0), new MediaEntry(reader.GetInt64(1), reader.GetInt64(2), reader.GetInt32(3), reader.GetInt32(4)));
        }

        return entries;
    }

    /// <summary>The system's games' <c>path_key</c>s, for <see cref="MediaScanner.Scan"/> to index only their media.</summary>
    public static List<string> LoadGameKeys(SqliteConnection connection, string systemId)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT path_key FROM games WHERE system_id = $system";
        command.Parameters.AddWithValue("$system", systemId);
        using var reader = command.ExecuteReader();
        var keys = new List<string>();
        while (reader.Read())
        {
            keys.Add(reader.GetString(0));
        }

        return keys;
    }

    public static List<SystemSummary> GetSystems(SqliteConnection connection, AppConfig config)
    {
        var rows = new Dictionary<string, (int Count, long? ScannedAt)>(StringComparer.Ordinal);
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT system_id, game_count, scanned_at FROM systems";
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                rows[reader.GetString(0)] = (reader.GetInt32(1), reader.IsDBNull(2) ? null : reader.GetInt64(2));
            }
        }

        var systems = new List<SystemSummary>(config.Systems.Count);
        foreach (var system in config.Systems)
        {
            var found = rows.TryGetValue(system.Id, out var row);
            systems.Add(new SystemSummary(
                system.Id,
                system.Name,
                found ? row.Count : 0,
                found && row.ScannedAt is { } ms ? DateTimeOffset.FromUnixTimeMilliseconds(ms) : null));
        }

        return systems;
    }

    // The grid queries select only what a cell draws. Title order uses games_by_system when no title is
    // overridden; the COALESCE keeps overridden titles in their own place. Another order (A4 Grid queries) joins what
    // it sorts by, and sorts in a temporary B-tree.
    private const string GamesSelect = """
        SELECT g.game_id, COALESCE(o.title, g.title), m.path, f.added_at IS NOT NULL, m.width, m.height, m.size_bytes, m.mtime_ms, o.template
        FROM games g
        LEFT JOIN user.game_overrides o ON o.system_id = g.system_id AND o.path_key = g.path_key
        LEFT JOIN user.favourites f ON f.system_id = g.system_id AND f.path_key = g.path_key
        LEFT JOIN media m ON m.game_id = g.game_id AND m.kind = 'cover'
        """;

    private const string GamesWhere = "WHERE g.system_id = $system AND COALESCE(o.hidden, 0) = 0";
    private const string TitleKey = "COALESCE(o.sort_title, g.sort_title)";
    private const string PlayStatsJoin = "LEFT JOIN user.play_stats p ON p.system_id = g.system_id AND p.path_key = g.path_key";
    private const string ReleaseDate = "NULLIF(COALESCE(o.release_date, mt.release_date), '')";

    /// <summary>
    /// A system's games query in <paramref name="ordering"/>'s order. Descending reverses what the sort names; ties go
    /// by title, A to Z (then by id, so the order is stable); a game without a date the sort needs (never played, no
    /// release date, a creation time never read) comes last either way. A game never played has no play time.
    /// </summary>
    internal static string GamesSql(GamesOrdering ordering)
    {
        var direction = ordering.Order == SortOrder.Descending ? " DESC" : string.Empty;
        return ordering.Sort switch
        {
            GameSort.LastPlayed => $"""
                {GamesSelect}
                {PlayStatsJoin}
                {GamesWhere}
                ORDER BY p.last_played_at IS NULL, p.last_played_at{direction}, {TitleKey}, g.game_id
                """,
            GameSort.PlayTime => $"""
                {GamesSelect}
                {PlayStatsJoin}
                {GamesWhere}
                ORDER BY COALESCE(p.total_seconds, 0){direction}, {TitleKey}, g.game_id
                """,
            GameSort.Added => $"""
                {GamesSelect}
                {GamesWhere}
                ORDER BY g.added_ms IS NULL, g.added_ms{direction}, {TitleKey}, g.game_id
                """,
            GameSort.ReleaseDate => $"""
                {GamesSelect}
                LEFT JOIN metadata mt ON mt.game_id = g.game_id
                {GamesWhere}
                ORDER BY {ReleaseDate} IS NULL, {ReleaseDate}{direction}, {TitleKey}, g.game_id
                """,
            _ => $"""
                {GamesSelect}
                {GamesWhere}
                ORDER BY {TitleKey}{direction}, g.game_id{direction}
                """,
        };
    }

    private const string FavouritesSql = """
        SELECT g.system_id, g.game_id, COALESCE(o.title, g.title), m.path, 1, m.width, m.height, m.size_bytes, m.mtime_ms, o.template
        FROM user.favourites f
        JOIN games g ON g.system_id = f.system_id AND g.path_key = f.path_key
        LEFT JOIN user.game_overrides o ON o.system_id = g.system_id AND o.path_key = g.path_key
        LEFT JOIN media m ON m.game_id = g.game_id AND m.kind = 'cover'
        WHERE COALESCE(o.hidden, 0) = 0
        ORDER BY COALESCE(o.sort_title, g.sort_title), g.system_id, g.game_id
        """;

    // Uses the partial index play_stats_recent.
    private const string RecentSql = """
        SELECT g.system_id, g.game_id, COALESCE(o.title, g.title), m.path, f.added_at IS NOT NULL, m.width, m.height, m.size_bytes, m.mtime_ms, o.template
        FROM user.play_stats p
        JOIN games g ON g.system_id = p.system_id AND g.path_key = p.path_key
        LEFT JOIN user.game_overrides o ON o.system_id = g.system_id AND o.path_key = g.path_key
        LEFT JOIN user.favourites f ON f.system_id = g.system_id AND f.path_key = g.path_key
        LEFT JOIN media m ON m.game_id = g.game_id AND m.kind = 'cover'
        WHERE p.last_played_at IS NOT NULL AND COALESCE(o.hidden, 0) = 0
        ORDER BY p.last_played_at DESC
        LIMIT $limit
        """;

    public static List<GameRow> GetGames(SqliteConnection connection, string systemId, GamesOrdering ordering, int capacityHint)
    {
        using var command = connection.CreateCommand();
        command.CommandText = GamesSql(ordering);
        command.Parameters.AddWithValue("$system", systemId);
        using var reader = command.ExecuteReader();
        var games = new List<GameRow>(capacityHint);
        while (reader.Read())
        {
            games.Add(new GameRow(
                reader.GetInt64(0),
                reader.GetString(1),
                reader.IsDBNull(2) ? null : reader.GetString(2),
                reader.GetBoolean(3),
                Aspect(reader, 4),
                reader.IsDBNull(6) ? 0 : reader.GetInt64(6),
                reader.IsDBNull(7) ? 0 : reader.GetInt64(7),
                NullableString(reader, 8)));
        }

        return games;
    }

    private const string GameMediaColumns = "m.game_id, m.kind, m.path, m.width, m.height, m.size_bytes, m.mtime_ms";

    /// <summary>Through <c>games_by_system</c>, then each game's <c>media</c> rows by primary key.</summary>
    public static List<GameMediaRow> GetGameMedia(SqliteConnection connection, string systemId, IReadOnlyList<string> kinds)
    {
        using var command = connection.CreateCommand();
        command.CommandText = $"""
            SELECT {GameMediaColumns} FROM games g JOIN media m ON m.game_id = g.game_id
            WHERE g.system_id = $system AND m.kind IN ({KindParameters(command, kinds)})
            """;
        command.Parameters.AddWithValue("$system", systemId);
        var rows = new List<GameMediaRow>();
        ReadGameMedia(command, rows);
        return rows;
    }

    public static List<GameMediaRow> GetGameMedia(SqliteConnection connection, IReadOnlyList<long> gameIds, IReadOnlyList<string> kinds)
    {
        const int Chunk = 500;
        var rows = new List<GameMediaRow>();
        for (var start = 0; start < gameIds.Count; start += Chunk)
        {
            using var command = connection.CreateCommand();
            var ids = new string[Math.Min(Chunk, gameIds.Count - start)];
            for (var i = 0; i < ids.Length; i++)
            {
                ids[i] = "$g" + i.ToString(System.Globalization.CultureInfo.InvariantCulture);
                command.Parameters.AddWithValue(ids[i], gameIds[start + i]);
            }

            command.CommandText = $"""
                SELECT {GameMediaColumns} FROM media m
                WHERE m.game_id IN ({string.Join(", ", ids)}) AND m.kind IN ({KindParameters(command, kinds)})
                """;
            ReadGameMedia(command, rows);
        }

        return rows;
    }

    /// <summary>Every media row of one game (the game options panel).</summary>
    public static List<GameMediaInfo> GetGameMediaInfo(SqliteConnection connection, long gameId)
    {
        using var command = connection.CreateCommand();
        command.CommandText = $"SELECT {GameMediaColumns} FROM media m WHERE m.game_id = $id ORDER BY m.kind";
        command.Parameters.AddWithValue("$id", gameId);
        var rows = new List<GameMediaInfo>();
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            rows.Add(new GameMediaInfo(
                reader.GetString(1),
                new MediaRef(reader.GetString(2), Aspect(reader, 3),
                    reader.IsDBNull(5) ? 0 : reader.GetInt64(5), reader.IsDBNull(6) ? 0 : reader.GetInt64(6)),
                reader.IsDBNull(3) ? null : reader.GetInt32(3),
                reader.IsDBNull(4) ? null : reader.GetInt32(4)));
        }

        return rows;
    }

    /// <summary>A game's title and metadata, the scraped values and the user's apart.</summary>
    public static GameMetadataEdit? GetMetadataEdit(SqliteConnection connection, GameKey key)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT g.title, o.title, mt.source, mt.description, mt.release_date, mt.developer, mt.publisher, mt.genre,
                   mt.players, mt.rating, o.description, o.release_date, o.developer, o.publisher, o.genre, o.players, o.rating
            FROM games g
            LEFT JOIN user.game_overrides o ON o.system_id = g.system_id AND o.path_key = g.path_key
            LEFT JOIN metadata mt ON mt.game_id = g.game_id
            WHERE g.system_id = $system AND g.path_key = $key
            """;
        command.Parameters.AddWithValue("$system", key.SystemId);
        command.Parameters.AddWithValue("$key", key.PathKey);
        using var reader = command.ExecuteReader();
        if (!reader.Read())
        {
            return null;
        }

        var scraped = reader.IsDBNull(2) ? null : new GameMetadata(
            NullableString(reader, 3), NullableString(reader, 4), NullableString(reader, 5), NullableString(reader, 6),
            NullableString(reader, 7), NullableString(reader, 8), reader.IsDBNull(9) ? null : reader.GetDouble(9), reader.GetString(2));
        var overrides = new MetadataOverride(
            NullableString(reader, 10), NullableString(reader, 11), NullableString(reader, 12), NullableString(reader, 13),
            NullableString(reader, 14), NullableString(reader, 15), reader.IsDBNull(16) ? null : reader.GetDouble(16));
        return new GameMetadataEdit(key, reader.GetString(0), NullableString(reader, 1), scraped, overrides);
    }

    private static string KindParameters(SqliteCommand command, IReadOnlyList<string> kinds)
    {
        var names = new string[kinds.Count];
        for (var i = 0; i < kinds.Count; i++)
        {
            names[i] = "$k" + i.ToString(System.Globalization.CultureInfo.InvariantCulture);
            command.Parameters.AddWithValue(names[i], kinds[i]);
        }

        return string.Join(", ", names);
    }

    private static void ReadGameMedia(SqliteCommand command, List<GameMediaRow> rows)
    {
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            rows.Add(new GameMediaRow(reader.GetInt64(0), reader.GetString(1), new MediaRef(
                reader.GetString(2),
                Aspect(reader, 3),
                reader.IsDBNull(5) ? 0 : reader.GetInt64(5),
                reader.IsDBNull(6) ? 0 : reader.GetInt64(6))));
        }
    }

    public static List<VirtualGameRow> GetFavourites(SqliteConnection connection, AppConfig config) =>
        ReadVirtual(connection, FavouritesSql, null, config);

    public static List<VirtualGameRow> GetRecentlyPlayed(SqliteConnection connection, int limit, AppConfig config) =>
        ReadVirtual(connection, RecentSql, limit, config);

    private static List<VirtualGameRow> ReadVirtual(SqliteConnection connection, string sql, int? limit, AppConfig config)
    {
        using var command = connection.CreateCommand();
        command.CommandText = sql;
        if (limit is not null)
        {
            command.Parameters.AddWithValue("$limit", limit.Value);
        }

        using var reader = command.ExecuteReader();
        var rows = new List<VirtualGameRow>();
        while (reader.Read())
        {
            // Rows of systems that are now disabled stay until the next full rescan drops them.
            var system = config.FindSystem(reader.GetString(0));
            if (system is null)
            {
                continue;
            }

            rows.Add(new VirtualGameRow(system.Id, new GameRow(
                reader.GetInt64(1),
                reader.GetString(2),
                reader.IsDBNull(3) ? null : reader.GetString(3),
                reader.GetBoolean(4),
                Aspect(reader, 5),
                reader.IsDBNull(7) ? 0 : reader.GetInt64(7),
                reader.IsDBNull(8) ? 0 : reader.GetInt64(8),
                NullableString(reader, 9))));
        }

        return rows;
    }

    /// <summary>Width over height from the two columns at <paramref name="widthOrdinal"/>; 0 when either is unknown.</summary>
    private static float Aspect(SqliteDataReader reader, int widthOrdinal)
    {
        if (reader.IsDBNull(widthOrdinal) || reader.IsDBNull(widthOrdinal + 1))
        {
            return 0;
        }

        var height = reader.GetInt32(widthOrdinal + 1);
        return height > 0 ? (float)reader.GetInt32(widthOrdinal) / height : 0;
    }

    // The user's metadata overrides win over scraped values, field by field (M4).
    private const string GameDetailsSql = """
        SELECT g.system_id, g.path_key, d.path, g.rel_path, COALESCE(o.title, g.title), g.region, g.languages,
               g.revision, g.disc, g.tags, g.size_bytes, f.added_at IS NOT NULL, COALESCE(o.hidden, 0), o.title,
               o.emulator, g.game_id,
               COALESCE(mt.source, CASE WHEN COALESCE(o.description, o.release_date, o.developer, o.publisher, o.genre, o.players, o.rating) IS NOT NULL THEN 'user' END),
               COALESCE(o.description, mt.description), COALESCE(o.release_date, mt.release_date),
               COALESCE(o.developer, mt.developer), COALESCE(o.publisher, mt.publisher), COALESCE(o.genre, mt.genre),
               COALESCE(o.players, mt.players), COALESCE(o.rating, mt.rating),
               ss.status, ss.providers, ss.scraped_at, o.template
        FROM games g
        JOIN rom_dirs d ON d.dir_id = g.dir_id
        LEFT JOIN user.game_overrides o ON o.system_id = g.system_id AND o.path_key = g.path_key
        LEFT JOIN user.favourites f ON f.system_id = g.system_id AND f.path_key = g.path_key
        LEFT JOIN metadata mt ON mt.game_id = g.game_id
        LEFT JOIN scrape_state ss ON ss.game_id = g.game_id
        """;

    public static GameDetails? GetGame(SqliteConnection connection, long gameId)
    {
        using var command = connection.CreateCommand();
        command.CommandText = GameDetailsSql + " WHERE g.game_id = $id";
        command.Parameters.AddWithValue("$id", gameId);
        return ReadGame(command);
    }

    /// <summary>Uses the <c>UNIQUE (system_id, path_key)</c> index.</summary>
    public static GameDetails? GetGame(SqliteConnection connection, GameKey key)
    {
        using var command = connection.CreateCommand();
        command.CommandText = GameDetailsSql + " WHERE g.system_id = $system AND g.path_key = $key";
        command.Parameters.AddWithValue("$system", key.SystemId);
        command.Parameters.AddWithValue("$key", key.PathKey);
        return ReadGame(command);
    }

    private static GameDetails? ReadGame(SqliteCommand command)
    {
        using var reader = command.ExecuteReader();
        if (!reader.Read())
        {
            return null;
        }

        var romDir = reader.GetString(2);
        var relPath = reader.GetString(3);
        return new GameDetails(
            new GameKey(reader.GetString(0), reader.GetString(1)),
            reader.GetInt64(15),
            romDir,
            relPath,
            Path.GetFullPath(Path.Combine(romDir, relPath.Replace('/', Path.DirectorySeparatorChar))),
            reader.GetString(4),
            NullableString(reader, 5),
            NullableString(reader, 6),
            NullableString(reader, 7),
            reader.IsDBNull(8) ? null : reader.GetInt32(8),
            NullableString(reader, 9),
            reader.GetInt64(10),
            reader.GetBoolean(11),
            reader.GetInt64(12) != 0,
            NullableString(reader, 13),
            NullableString(reader, 14),
            reader.IsDBNull(16) ? null : new GameMetadata(
                NullableString(reader, 17),
                NullableString(reader, 18),
                NullableString(reader, 19),
                NullableString(reader, 20),
                NullableString(reader, 21),
                NullableString(reader, 22),
                reader.IsDBNull(23) ? null : reader.GetDouble(23),
                reader.GetString(16)),
            reader.IsDBNull(24) ? null : new ScrapeInfo(
                reader.GetString(24),
                NullableString(reader, 25) is { } providers ? providers.Split(',') : [],
                DateTimeOffset.FromUnixTimeMilliseconds(reader.GetInt64(26))),
            NullableString(reader, 27));
    }

    public static PlayStats? GetPlayStats(SqliteConnection connection, GameKey game)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT play_count, total_seconds, last_played_at FROM user.play_stats
            WHERE system_id = $system AND path_key = $key
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        using var reader = command.ExecuteReader();
        return reader.Read()
            ? new PlayStats(
                reader.GetInt32(0),
                TimeSpan.FromSeconds(reader.GetInt64(1)),
                reader.IsDBNull(2) ? null : DateTimeOffset.FromUnixTimeMilliseconds(reader.GetInt64(2)))
            : null;
    }

    private static string? NullableString(SqliteDataReader reader, int ordinal) =>
        reader.IsDBNull(ordinal) ? null : reader.GetString(ordinal);

    // ---- User data writes --------------------------------------------------------------------------

    public static void SetFavourite(SqliteConnection connection, GameKey game, bool favourite, long now)
    {
        using var command = connection.CreateCommand();
        command.CommandText = favourite
            ? "INSERT INTO user.favourites (system_id, path_key, added_at) VALUES ($system, $key, $now) ON CONFLICT DO NOTHING"
            : "DELETE FROM user.favourites WHERE system_id = $system AND path_key = $key";
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$now", now);
        command.ExecuteNonQuery();
    }

    public static void SetTitleOverride(SqliteConnection connection, GameKey game, string? title)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO user.game_overrides (system_id, path_key, title, sort_title) VALUES ($system, $key, $title, $sort)
            ON CONFLICT (system_id, path_key) DO UPDATE SET title = excluded.title, sort_title = excluded.sort_title
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$title", (object?)title ?? DBNull.Value);
        command.Parameters.AddWithValue("$sort", title is null ? DBNull.Value : TitleParser.SortKey(title));
        command.ExecuteNonQuery();
    }

    public static void SetMetadataOverride(SqliteConnection connection, GameKey game, MetadataOverride values)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO user.game_overrides (system_id, path_key, description, release_date, developer, publisher, genre, players, rating)
            VALUES ($system, $key, $description, $release, $developer, $publisher, $genre, $players, $rating)
            ON CONFLICT (system_id, path_key) DO UPDATE SET description = excluded.description,
                release_date = excluded.release_date, developer = excluded.developer, publisher = excluded.publisher,
                genre = excluded.genre, players = excluded.players, rating = excluded.rating
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$description", (object?)values.Description ?? DBNull.Value);
        command.Parameters.AddWithValue("$release", (object?)values.ReleaseDate ?? DBNull.Value);
        command.Parameters.AddWithValue("$developer", (object?)values.Developer ?? DBNull.Value);
        command.Parameters.AddWithValue("$publisher", (object?)values.Publisher ?? DBNull.Value);
        command.Parameters.AddWithValue("$genre", (object?)values.Genre ?? DBNull.Value);
        command.Parameters.AddWithValue("$players", (object?)values.Players ?? DBNull.Value);
        command.Parameters.AddWithValue("$rating", (object?)values.Rating ?? DBNull.Value);
        command.ExecuteNonQuery();
    }

    public static void SetHidden(SqliteConnection connection, GameKey game, bool hidden)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO user.game_overrides (system_id, path_key, hidden) VALUES ($system, $key, $hidden)
            ON CONFLICT (system_id, path_key) DO UPDATE SET hidden = excluded.hidden
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$hidden", hidden ? 1 : 0);
        command.ExecuteNonQuery();
    }

    public static void SetEmulatorOverride(SqliteConnection connection, GameKey game, string? emulator)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO user.game_overrides (system_id, path_key, emulator) VALUES ($system, $key, $emulator)
            ON CONFLICT (system_id, path_key) DO UPDATE SET emulator = excluded.emulator
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$emulator", (object?)emulator ?? DBNull.Value);
        command.ExecuteNonQuery();
    }

    /// <summary>The template the user chose for one game (2026-10-07); null goes back to its system's.</summary>
    public static void SetGameTemplate(SqliteConnection connection, GameKey game, string? template)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO user.game_overrides (system_id, path_key, template) VALUES ($system, $key, $template)
            ON CONFLICT (system_id, path_key) DO UPDATE SET template = excluded.template
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$template", (object?)template ?? DBNull.Value);
        command.ExecuteNonQuery();
    }

    /// <summary>Every template id some game has chosen, each once, for the theme to load with its own.</summary>
    public static List<string> GetChosenTemplates(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT DISTINCT template FROM user.game_overrides WHERE template IS NOT NULL ORDER BY template";
        using var reader = command.ExecuteReader();
        var ids = new List<string>();
        while (reader.Read())
        {
            ids.Add(reader.GetString(0));
        }

        return ids;
    }

    /// <summary>
    /// A deleted game's rows (2026-10-03), in one transaction: the game (its metadata, media rows, matches and scrape
    /// state go with it), the cached playlists among its files, and the system's count. userdata.db keeps its rows,
    /// as for any file that disappears (A4 Orphans).
    /// </summary>
    public static void RemoveDeletedGame(SqliteConnection connection, GameKey game, IReadOnlyList<string> deletedKeys)
    {
        using var transaction = connection.BeginTransaction();
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.Parameters.AddWithValue("$system", game.SystemId);
        var key = command.Parameters.AddWithValue("$key", game.PathKey);
        command.CommandText = "DELETE FROM games WHERE system_id = $system AND path_key = $key";
        command.ExecuteNonQuery();

        command.CommandText = "DELETE FROM playlists WHERE system_id = $system AND path_key = $key";
        foreach (var deleted in deletedKeys)
        {
            key.Value = deleted;
            command.ExecuteNonQuery();
        }

        command.CommandText = "UPDATE systems SET game_count = (SELECT COUNT(*) FROM games WHERE system_id = $system) WHERE system_id = $system";
        command.ExecuteNonQuery();
        transaction.Commit();
    }

    // ---- Play history ----------------------------------------------------------------------------

    public static long BeginSession(SqliteConnection connection, GameKey game, string emulator, long startedAtMs)
    {
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO user.play_sessions (system_id, path_key, emulator, started_at) VALUES ($system, $key, $emulator, $started)
            RETURNING session_id
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$emulator", emulator);
        command.Parameters.AddWithValue("$started", startedAtMs);
        return (long)command.ExecuteScalar()!;
    }

    public static void EndSession(SqliteConnection connection, PlaySessionEnd end)
    {
        var endedAt = end.StartedAt.ToUnixTimeMilliseconds() + (long)end.Duration.TotalMilliseconds;
        using var transaction = connection.BeginTransaction();
        using (var close = connection.CreateCommand())
        {
            close.Transaction = transaction;
            close.CommandText = "UPDATE user.play_sessions SET ended_at = $ended, exit_code = $code WHERE session_id = $id";
            close.Parameters.AddWithValue("$id", end.SessionId);
            close.Parameters.AddWithValue("$ended", endedAt);
            close.Parameters.AddWithValue("$code", (object?)end.ExitCode ?? DBNull.Value);
            close.ExecuteNonQuery();
        }

        if (end.CountAsPlay)
        {
            AddPlay(connection, transaction, end.Game, (long)Math.Round(end.Duration.TotalSeconds, MidpointRounding.AwayFromZero), endedAt);
        }

        transaction.Commit();
    }

    /// <summary>
    /// Sessions still open were left by a launcher that died while a game ran (A4). How long the game ran isn't
    /// known, so each is closed at its start time: it counts as a play, with no play time.
    /// </summary>
    public static int CloseOrphanedSessions(SqliteConnection connection)
    {
        using var transaction = connection.BeginTransaction();
        var open = new List<(long Id, GameKey Game, long StartedAt)>();
        using (var select = connection.CreateCommand())
        {
            select.Transaction = transaction;
            select.CommandText = "SELECT session_id, system_id, path_key, started_at FROM user.play_sessions WHERE ended_at IS NULL";
            using var reader = select.ExecuteReader();
            while (reader.Read())
            {
                open.Add((reader.GetInt64(0), new GameKey(reader.GetString(1), reader.GetString(2)), reader.GetInt64(3)));
            }
        }

        foreach (var (id, game, startedAt) in open)
        {
            using var close = connection.CreateCommand();
            close.Transaction = transaction;
            close.CommandText = "UPDATE user.play_sessions SET ended_at = started_at WHERE session_id = $id";
            close.Parameters.AddWithValue("$id", id);
            close.ExecuteNonQuery();
            AddPlay(connection, transaction, game, 0, startedAt);
        }

        transaction.Commit();
        return open.Count;
    }

    private static void AddPlay(SqliteConnection connection, SqliteTransaction transaction, GameKey game, long seconds, long playedAtMs)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            INSERT INTO user.play_stats (system_id, path_key, play_count, total_seconds, last_played_at)
            VALUES ($system, $key, 1, $seconds, $played)
            ON CONFLICT (system_id, path_key) DO UPDATE SET
                play_count = play_count + 1,
                total_seconds = total_seconds + excluded.total_seconds,
                last_played_at = MAX(COALESCE(last_played_at, 0), excluded.last_played_at)
            """;
        command.Parameters.AddWithValue("$system", game.SystemId);
        command.Parameters.AddWithValue("$key", game.PathKey);
        command.Parameters.AddWithValue("$seconds", seconds);
        command.Parameters.AddWithValue("$played", playedAtMs);
        command.ExecuteNonQuery();
    }

    /// <summary>User data stored under an alias (e.g. imported as 'genesis') moves to the canonical id (A4).</summary>
    public static void RekeyAliases(SqliteConnection connection, AppConfig config)
    {
        using var transaction = connection.BeginTransaction();
        foreach (var system in config.Systems)
        {
            foreach (var alias in system.Aliases)
            {
                foreach (var table in (ReadOnlySpan<string>)["favourites", "play_stats", "manual_matches", "game_overrides"])
                {
                    // OR IGNORE: a row that already exists under the canonical id wins; the alias row stays as an orphan.
                    Execute(connection, transaction, $"UPDATE OR IGNORE user.{table} SET system_id = $id WHERE system_id = $alias", system.Id, alias);
                }

                Execute(connection, transaction, "UPDATE user.play_sessions SET system_id = $id WHERE system_id = $alias", system.Id, alias);
            }
        }

        transaction.Commit();
    }

    private static void Execute(SqliteConnection connection, SqliteTransaction transaction, string sql, string id, string alias)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        command.Parameters.AddWithValue("$id", id);
        command.Parameters.AddWithValue("$alias", alias);
        command.ExecuteNonQuery();
    }

    // ---- Scan results ----------------------------------------------------------------------------

    private sealed record Existing(long GameId, long DirId, string RelPath, long SizeBytes, long MtimeMs, long? AddedMs);

    /// <summary>
    /// Writes scan results in one transaction: rows are inserted, updated or deleted by <c>path_key</c>, so a
    /// case-only rename keeps its game id and its user data, and unchanged rows aren't written at all.
    /// </summary>
    /// <param name="media">The media found for each scan, at the same index; null entries (or a null list) leave media alone.</param>
    /// <param name="keepOnly">When set, systems not in this set are deleted (a full rescan).</param>
    /// <param name="added">When set, collects the games this scan added (their scraped data is restored after, M4).</param>
    /// <param name="mediaChanged">When set, collects the games whose media rows changed (M6).</param>
    public static List<SystemScanSummary> Apply(
        SqliteConnection connection,
        IReadOnlyList<SystemScan> scans,
        IReadOnlyList<MediaScan?>? media,
        IReadOnlySet<string>? keepOnly,
        long now,
        List<GameKey>? added = null,
        List<GameKey>? mediaChanged = null)
    {
        var summaries = new List<SystemScanSummary>(scans.Count);
        using var transaction = connection.BeginTransaction();
        using var statements = new Statements(connection, transaction);
        for (var i = 0; i < scans.Count; i++)
        {
            summaries.Add(ApplyOne(connection, transaction, statements, scans[i], media?[i], now, added, mediaChanged));
        }

        if (keepOnly is not null)
        {
            using var list = connection.CreateCommand();
            list.Transaction = transaction;
            list.CommandText = "SELECT system_id FROM systems";
            var stale = new List<string>();
            using (var reader = list.ExecuteReader())
            {
                while (reader.Read())
                {
                    if (!keepOnly.Contains(reader.GetString(0)))
                    {
                        stale.Add(reader.GetString(0));
                    }
                }
            }

            foreach (var systemId in stale)
            {
                using var delete = connection.CreateCommand();
                delete.Transaction = transaction;
                delete.CommandText = "DELETE FROM systems WHERE system_id = $system";
                delete.Parameters.AddWithValue("$system", systemId);
                delete.ExecuteNonQuery();
            }
        }

        transaction.Commit();
        return summaries;
    }

    private static SystemScanSummary ApplyOne(
        SqliteConnection connection, SqliteTransaction transaction, Statements s, SystemScan scan, MediaScan? media, long now,
        List<GameKey>? addedKeys, List<GameKey>? mediaChanged)
    {
        var system = scan.SystemId;
        s.Bind(s.InsertSystem, ("$system", system));
        s.InsertSystem.ExecuteNonQuery();

        // Folders: keep ids for folders that are still listed, so their games aren't touched.
        var oldDirs = new Dictionary<string, (long Id, long Position)>(StringComparer.Ordinal);
        s.Bind(s.SelectDirs, ("$system", system));
        using (var reader = s.SelectDirs.ExecuteReader())
        {
            while (reader.Read())
            {
                oldDirs[reader.GetString(1)] = (reader.GetInt64(0), reader.GetInt64(2));
            }
        }

        var dirIds = new long[scan.RomDirs.Count];
        for (var i = 0; i < scan.RomDirs.Count; i++)
        {
            if (oldDirs.Remove(scan.RomDirs[i], out var old))
            {
                dirIds[i] = old.Id;
                if (old.Position != i)
                {
                    s.Bind(s.UpdateDirPosition, ("$id", old.Id), ("$position", i));
                    s.UpdateDirPosition.ExecuteNonQuery();
                }
            }
            else
            {
                s.Bind(s.InsertDir, ("$system", system), ("$position", i), ("$path", scan.RomDirs[i]));
                dirIds[i] = (long)s.InsertDir.ExecuteScalar()!;
            }
        }

        var existing = new Dictionary<string, Existing>(StringComparer.Ordinal);
        s.Bind(s.SelectGames, ("$system", system));
        using (var reader = s.SelectGames.ExecuteReader())
        {
            while (reader.Read())
            {
                existing[reader.GetString(1)] = new Existing(
                    reader.GetInt64(0), reader.GetInt64(2), reader.GetString(3), reader.GetInt64(4), reader.GetInt64(5),
                    reader.IsDBNull(6) ? null : reader.GetInt64(6));
            }
        }

        int added = 0, updated = 0, unchanged = 0;
        foreach (var game in scan.Games)
        {
            var dirId = dirIds[game.DirIndex];
            long? addedMs = game.CreatedMs > 0 ? game.CreatedMs : null;
            if (!existing.Remove(game.PathKey, out var old))
            {
                var title = TitleParser.Parse(FileStem(game.RelPath));
                s.Bind(s.InsertGame,
                    ("$system", system), ("$dir", dirId), ("$rel", game.RelPath), ("$key", game.PathKey),
                    ("$size", game.SizeBytes), ("$mtime", game.MtimeMs), ("$added", addedMs));
                BindTitle(s, s.InsertGame, title);
                s.InsertGame.ExecuteNonQuery();
                added++;
                addedKeys?.Add(new GameKey(system, game.PathKey));
                continue;
            }

            var renamed = !string.Equals(old.RelPath, game.RelPath, StringComparison.Ordinal);
            var contentChanged = old.SizeBytes != game.SizeBytes || old.MtimeMs != game.MtimeMs;
            if (!renamed && !contentChanged && old.DirId == dirId && old.AddedMs == addedMs)
            {
                unchanged++;
                continue;
            }

            s.Bind(s.UpdateGame,
                ("$id", old.GameId), ("$dir", dirId), ("$rel", game.RelPath), ("$size", game.SizeBytes),
                ("$mtime", game.MtimeMs), ("$added", addedMs), ("$changed", contentChanged ? 1 : 0));
            s.UpdateGame.ExecuteNonQuery();
            if (renamed)
            {
                // A case-only rename changes the file-name title too, unless the game has a scraped title.
                var title = TitleParser.Parse(FileStem(game.RelPath));
                if (ScrapedTitle(connection, transaction, old.GameId) is { } scraped)
                {
                    title = title with { Title = scraped, SortTitle = TitleParser.SortKey(scraped) };
                }

                s.Bind(s.UpdateTitle, ("$id", old.GameId));
                BindTitle(s, s.UpdateTitle, title);
                s.UpdateTitle.ExecuteNonQuery();
            }

            updated++;
        }

        foreach (var gone in existing.Values)
        {
            s.Bind(s.DeleteGame, ("$id", gone.GameId));
            s.DeleteGame.ExecuteNonQuery();
        }

        foreach (var (_, oldDir) in oldDirs)
        {
            s.Bind(s.DeleteDir, ("$id", oldDir.Id));
            s.DeleteDir.ExecuteNonQuery();
        }

        ApplyPlaylists(connection, transaction, s, system, scan.Playlists);
        if (media is not null)
        {
            ApplyMedia(connection, transaction, system, media, mediaChanged);
        }

        s.Bind(s.UpdateSystem, ("$system", system), ("$now", now));
        s.UpdateSystem.ExecuteNonQuery();
        return new SystemScanSummary(system, added, updated, existing.Count, unchanged, scan.FilesSeen, scan.PlaylistsRead);
    }

    /// <summary>One system's media alone, in a transaction of their own (no ROM scan).</summary>
    public static void ApplyMediaOnly(SqliteConnection connection, string systemId, MediaScan media, List<GameKey> changed)
    {
        using var transaction = connection.BeginTransaction();
        ApplyMedia(connection, transaction, systemId, media, changed);
        transaction.Commit();
    }

    private static void ApplyPlaylists(
        SqliteConnection connection, SqliteTransaction transaction, Statements s, string system, IReadOnlyList<PlaylistEntry> playlists)
    {
        var old = new Dictionary<string, (long Size, long Mtime, string Refs)>(StringComparer.Ordinal);
        using (var select = connection.CreateCommand())
        {
            select.Transaction = transaction;
            select.CommandText = "SELECT path_key, size_bytes, mtime_ms, refs FROM playlists WHERE system_id = $system";
            select.Parameters.AddWithValue("$system", system);
            using var reader = select.ExecuteReader();
            while (reader.Read())
            {
                old[reader.GetString(0)] = (reader.GetInt64(1), reader.GetInt64(2), reader.GetString(3));
            }
        }

        foreach (var playlist in playlists)
        {
            var refs = string.Join('\n', playlist.Refs);
            if (old.Remove(playlist.PathKey, out var previous)
                && previous.Size == playlist.SizeBytes && previous.Mtime == playlist.MtimeMs && previous.Refs == refs)
            {
                continue;
            }

            s.Bind(s.UpsertPlaylist,
                ("$system", system), ("$key", playlist.PathKey), ("$size", playlist.SizeBytes),
                ("$mtime", playlist.MtimeMs), ("$refs", refs));
            s.UpsertPlaylist.ExecuteNonQuery();
        }

        foreach (var gone in old.Keys)
        {
            s.Bind(s.DeletePlaylist, ("$system", system), ("$key", gone));
            s.DeletePlaylist.ExecuteNonQuery();
        }
    }

    private readonly record struct MediaRow(string Path, long? SizeBytes, long? MtimeMs, int? Width, int? Height);

    /// <summary>
    /// Makes the system's media rows match the media folder. A file matches the game whose <c>path_key</c> is its match
    /// key; otherwise every game whose <c>path_key</c> is its match key plus an extension. Every kind (images, videos,
    /// per-game models) is matched the same way, whether a scrape or the user put the file there.
    /// </summary>
    private static void ApplyMedia(
        SqliteConnection connection, SqliteTransaction transaction, string system, MediaScan media, List<GameKey>? changed)
    {
        var existing = new Dictionary<(long GameId, string Kind), MediaRow>();
        using (var select = connection.CreateCommand())
        {
            select.Transaction = transaction;
            select.CommandText = """
                SELECT m.game_id, m.kind, m.path, m.size_bytes, m.mtime_ms, m.width, m.height
                FROM media m JOIN games g ON g.game_id = m.game_id
                WHERE g.system_id = $system
                """;
            select.Parameters.AddWithValue("$system", system);
            using var reader = select.ExecuteReader();
            while (reader.Read())
            {
                existing[(reader.GetInt64(0), reader.GetString(1))] = new MediaRow(
                    reader.GetString(2),
                    reader.IsDBNull(3) ? null : reader.GetInt64(3),
                    reader.IsDBNull(4) ? null : reader.GetInt64(4),
                    reader.IsDBNull(5) ? null : reader.GetInt32(5),
                    reader.IsDBNull(6) ? null : reader.GetInt32(6));
            }
        }

        if (media.Files.Count == 0 && existing.Count == 0)
        {
            return;
        }

        var byKey = new Dictionary<string, long>(StringComparer.Ordinal);
        var keyOf = new Dictionary<long, string>();
        var byStem = new Dictionary<string, List<long>>(StringComparer.Ordinal);
        using (var games = connection.CreateCommand())
        {
            games.Transaction = transaction;
            games.CommandText = "SELECT game_id, path_key FROM games WHERE system_id = $system";
            games.Parameters.AddWithValue("$system", system);
            using var reader = games.ExecuteReader();
            while (reader.Read())
            {
                var key = reader.GetString(1);
                byKey[key] = reader.GetInt64(0);
                keyOf[reader.GetInt64(0)] = key;
                var dot = key.LastIndexOf('.');
                if (dot > key.LastIndexOf('/') + 1)
                {
                    var stem = key[..dot];
                    if (!byStem.TryGetValue(stem, out var ids))
                    {
                        byStem[stem] = ids = [];
                    }

                    ids.Add(reader.GetInt64(0));
                }
            }
        }

        // Exact matches first, so they win over a stem match of the same kind.
        var wanted = new Dictionary<(long GameId, string Kind), MediaFile>();
        foreach (var file in media.Files)
        {
            if (byKey.TryGetValue(file.MatchKey, out var id))
            {
                wanted.TryAdd((id, file.Kind), file);
            }
        }

        foreach (var file in media.Files)
        {
            if (byStem.TryGetValue(file.MatchKey, out var ids))
            {
                foreach (var id in ids)
                {
                    wanted.TryAdd((id, file.Kind), file);
                }
            }
        }

        using var upsert = connection.CreateCommand();
        upsert.Transaction = transaction;
        upsert.CommandText = """
            INSERT INTO media (game_id, kind, path, width, height, size_bytes, mtime_ms)
            VALUES ($id, $kind, $path, $width, $height, $size, $mtime)
            ON CONFLICT (game_id, kind) DO UPDATE SET path = excluded.path, width = excluded.width, height = excluded.height,
                size_bytes = excluded.size_bytes, mtime_ms = excluded.mtime_ms
            """;
        foreach (var ((id, kind), file) in wanted)
        {
            if (existing.Remove((id, kind), out var old)
                && old == new MediaRow(file.Path, file.SizeBytes, file.MtimeMs, file.Width, file.Height))
            {
                continue;
            }

            upsert.Parameters.Clear();
            upsert.Parameters.AddWithValue("$id", id);
            upsert.Parameters.AddWithValue("$kind", kind);
            upsert.Parameters.AddWithValue("$path", file.Path);
            upsert.Parameters.AddWithValue("$width", file.Width is { } width ? width : DBNull.Value);
            upsert.Parameters.AddWithValue("$height", file.Height is { } height ? height : DBNull.Value);
            upsert.Parameters.AddWithValue("$size", file.SizeBytes);
            upsert.Parameters.AddWithValue("$mtime", file.MtimeMs);
            upsert.ExecuteNonQuery();
            Changed(id);
        }

        using var delete = connection.CreateCommand();
        delete.Transaction = transaction;
        delete.CommandText = "DELETE FROM media WHERE game_id = $id AND kind = $kind";
        foreach (var (id, kind) in existing.Keys)
        {
            delete.Parameters.Clear();
            delete.Parameters.AddWithValue("$id", id);
            delete.Parameters.AddWithValue("$kind", kind);
            delete.ExecuteNonQuery();
            Changed(id);
        }

        void Changed(long id)
        {
            if (changed is not null && keyOf.TryGetValue(id, out var key) && !changed.Contains(new GameKey(system, key)))
            {
                changed.Add(new GameKey(system, key));
            }
        }
    }

    private static string? ScrapedTitle(SqliteConnection connection, SqliteTransaction transaction, long gameId)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = "SELECT title FROM metadata WHERE game_id = $id";
        command.Parameters.AddWithValue("$id", gameId);
        return command.ExecuteScalar() as string;
    }

    internal static string FileStemOf(string relPath) => FileStem(relPath);

    private static void BindTitle(Statements s, SqliteCommand command, TitleInfo title) =>
        s.Bind(command, false,
            ("$title", title.Title), ("$sort", title.SortTitle), ("$region", title.Region),
            ("$languages", title.Languages), ("$revision", title.Revision), ("$disc", title.Disc), ("$tags", title.Tags));

    private static string FileStem(string relPath)
    {
        var slash = relPath.LastIndexOf('/');
        var name = slash < 0 ? relPath : relPath[(slash + 1)..];
        var dot = name.LastIndexOf('.');
        return dot > 0 ? name[..dot] : name;
    }

    /// <summary>Prepared statements, reused for every row of a scan.</summary>
    private sealed class Statements : IDisposable
    {
        private readonly List<SqliteCommand> _all = [];

        public Statements(SqliteConnection connection, SqliteTransaction transaction)
        {
            SqliteCommand Make(string sql)
            {
                var command = connection.CreateCommand();
                command.Transaction = transaction;
                command.CommandText = sql;
                _all.Add(command);
                return command;
            }

            InsertSystem = Make("INSERT INTO systems (system_id) VALUES ($system) ON CONFLICT DO NOTHING");
            UpdateSystem = Make("""
                UPDATE systems SET scanned_at = $now,
                    game_count = (SELECT COUNT(*) FROM games WHERE system_id = $system)
                WHERE system_id = $system
                """);
            SelectDirs = Make("SELECT dir_id, path, position FROM rom_dirs WHERE system_id = $system");
            InsertDir = Make("INSERT INTO rom_dirs (system_id, position, path) VALUES ($system, $position, $path) RETURNING dir_id");
            UpdateDirPosition = Make("UPDATE rom_dirs SET position = $position WHERE dir_id = $id");
            DeleteDir = Make("DELETE FROM rom_dirs WHERE dir_id = $id");
            SelectGames = Make("SELECT game_id, path_key, dir_id, rel_path, size_bytes, mtime_ms, added_ms FROM games WHERE system_id = $system");
            InsertGame = Make("""
                INSERT INTO games (system_id, dir_id, rel_path, path_key, size_bytes, mtime_ms, added_ms,
                                   title, sort_title, region, languages, revision, disc, tags)
                VALUES ($system, $dir, $rel, $key, $size, $mtime, $added, $title, $sort, $region, $languages, $revision, $disc, $tags)
                """);
            // New content invalidates the hashes.
            UpdateGame = Make("""
                UPDATE games SET dir_id = $dir, rel_path = $rel, size_bytes = $size, mtime_ms = $mtime, added_ms = $added,
                    crc32 = CASE WHEN $changed THEN NULL ELSE crc32 END,
                    md5 = CASE WHEN $changed THEN NULL ELSE md5 END,
                    sha1 = CASE WHEN $changed THEN NULL ELSE sha1 END
                WHERE game_id = $id
                """);
            UpdateTitle = Make("""
                UPDATE games SET title = $title, sort_title = $sort, region = $region, languages = $languages,
                    revision = $revision, disc = $disc, tags = $tags
                WHERE game_id = $id
                """);
            DeleteGame = Make("DELETE FROM games WHERE game_id = $id");
            UpsertPlaylist = Make("""
                INSERT INTO playlists (system_id, path_key, size_bytes, mtime_ms, refs) VALUES ($system, $key, $size, $mtime, $refs)
                ON CONFLICT (system_id, path_key) DO UPDATE SET size_bytes = excluded.size_bytes,
                    mtime_ms = excluded.mtime_ms, refs = excluded.refs
                """);
            DeletePlaylist = Make("DELETE FROM playlists WHERE system_id = $system AND path_key = $key");
        }

        public SqliteCommand InsertSystem { get; }

        public SqliteCommand UpdateSystem { get; }

        public SqliteCommand SelectDirs { get; }

        public SqliteCommand InsertDir { get; }

        public SqliteCommand UpdateDirPosition { get; }

        public SqliteCommand DeleteDir { get; }

        public SqliteCommand SelectGames { get; }

        public SqliteCommand InsertGame { get; }

        public SqliteCommand UpdateGame { get; }

        public SqliteCommand UpdateTitle { get; }

        public SqliteCommand DeleteGame { get; }

        public SqliteCommand UpsertPlaylist { get; }

        public SqliteCommand DeletePlaylist { get; }

        /// <summary>Sets parameters by name, creating them on first use. Clears the others first unless told not to.</summary>
        public void Bind(SqliteCommand command, params (string Name, object? Value)[] values) => Bind(command, true, values);

        public void Bind(SqliteCommand command, bool clear, params (string Name, object? Value)[] values)
        {
            if (clear)
            {
                command.Parameters.Clear();
            }

            foreach (var (name, value) in values)
            {
                if (command.Parameters.Contains(name))
                {
                    command.Parameters[name].Value = value ?? DBNull.Value;
                }
                else
                {
                    command.Parameters.AddWithValue(name, value ?? DBNull.Value);
                }
            }
        }

        public void Dispose()
        {
            foreach (var command in _all)
            {
                command.Dispose();
            }
        }
    }
}
