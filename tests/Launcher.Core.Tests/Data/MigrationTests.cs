using Launcher.Core.Data;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Data;

public sealed class MigrationTests : IDisposable
{
    private readonly TempDir _dir = new();
    private readonly ManualClock _clock = new(new DateTimeOffset(2026, 9, 28, 10, 0, 0, TimeSpan.Zero));

    public void Dispose()
    {
        SqliteConnection.ClearAllPools();
        _dir.Dispose();
    }

    private static List<string> Tables(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT name FROM sqlite_schema WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' ORDER BY name";
        using var reader = command.ExecuteReader();
        var names = new List<string>();
        while (reader.Read())
        {
            names.Add(reader.GetString(0));
        }

        return names;
    }

    private static string Scalar(SqliteConnection connection, string sql)
    {
        using var command = connection.CreateCommand();
        command.CommandText = sql;
        return Convert.ToString(command.ExecuteScalar(), System.Globalization.CultureInfo.InvariantCulture)!;
    }

    [Fact]
    public void Migrations_are_numbered_from_one_without_gaps()
    {
        Assert.Equal(Enumerable.Range(1, MigrationRunner.Library.Count), MigrationRunner.Library.Select(m => m.Version));
        Assert.Equal(Enumerable.Range(1, MigrationRunner.User.Count), MigrationRunner.User.Select(m => m.Version));
        Assert.Equal("initial", MigrationRunner.Library[0].Name);
    }

    [Fact]
    public void A_fresh_library_db_gets_the_whole_schema_in_WAL_mode()
    {
        var path = _dir.Combine("library.db");

        var outcome = LibraryDatabase.Prepare(path, out var reason);

        Assert.Equal(LibraryOpenOutcome.Created, outcome);
        Assert.Null(reason);
        using var connection = Sqlite.Open(path);
        Assert.Equal(MigrationRunner.Library[^1].Version, MigrationRunner.GetVersion(connection));
        Assert.Equal("wal", Scalar(connection, "PRAGMA journal_mode"));
        Assert.Equal(
            ["games", "games_by_dir", "games_by_system", "media", "metadata", "playlists", "rom_dirs", "scrape_log", "scrape_state", "scraper_matches", "systems"],
            Tables(connection));
    }

    [Fact]
    public void A_fresh_userdata_db_gets_the_whole_schema()
    {
        var path = _dir.Combine("userdata.db");

        UserDatabase.Prepare(path, _clock);

        using var connection = Sqlite.Open(path);
        Assert.Equal(MigrationRunner.User[^1].Version, MigrationRunner.GetVersion(connection));
        Assert.Equal(
            ["favourites", "game_overrides", "manual_matches", "play_sessions", "play_sessions_open", "play_stats", "play_stats_recent", "scrape_batches", "scrape_jobs"],
            Tables(connection));
        Assert.Empty(UserDatabase.ListBackups(path));
    }

    [Fact]
    public void Every_previous_version_upgrades_to_the_latest()
    {
        foreach (var (name, migrations) in (ReadOnlySpan<(string, IReadOnlyList<Migration>)>)[("library", MigrationRunner.Library), ("user", MigrationRunner.User)])
        {
            for (var start = 0; start < migrations.Count; start++)
            {
                var path = _dir.Combine($"{name}-from-{start}.db");
                using (var connection = Sqlite.Open(path))
                {
                    MigrationRunner.Migrate(connection, migrations.Take(start).ToList(), path);
                    Assert.Equal(start, MigrationRunner.GetVersion(connection));
                }

                using (var connection = Sqlite.Open(path))
                {
                    Assert.Equal(start, MigrationRunner.Migrate(connection, migrations, path));
                    Assert.Equal(migrations[^1].Version, MigrationRunner.GetVersion(connection));
                    Assert.Equal("0", Scalar(connection, "SELECT COUNT(*) FROM pragma_foreign_key_check"));
                }
            }
        }
    }

    [Fact]
    public void The_media_folder_migration_drops_the_source_and_queues_every_system_for_a_rescan()
    {
        var path = _dir.Combine("library-3.db");
        using (var connection = Sqlite.Open(path))
        {
            MigrationRunner.Migrate(connection, MigrationRunner.Library.Take(3).ToList(), path);
            using var seed = connection.CreateCommand();
            seed.CommandText = """
                INSERT INTO systems (system_id, scanned_at, game_count) VALUES ('snes', 1000, 1);
                INSERT INTO rom_dirs (dir_id, system_id, position, path) VALUES (1, 'snes', 0, 'C:/ROMs/snes');
                INSERT INTO games (game_id, system_id, dir_id, rel_path, path_key, size_bytes, mtime_ms, title, sort_title)
                VALUES (1, 'snes', 1, 'Game.sfc', 'game.sfc', 1, 1, 'Game', 'game');
                INSERT INTO media (game_id, kind, path, source) VALUES (1, 'cover', 'scraped/media/snes/cover/game.sfc.png', 'screenscraper');
                """;
            seed.ExecuteNonQuery();
        }

        using (var connection = Sqlite.Open(path))
        {
            MigrationRunner.Migrate(connection, MigrationRunner.Library, path);

            Assert.Equal("0", Scalar(connection, "SELECT COUNT(*) FROM pragma_table_info('media') WHERE name = 'source'"));
            Assert.Equal("scraped/media/snes/cover/game.sfc.png", Scalar(connection, "SELECT path FROM media"));   // until the rescan drops it
            Assert.Equal(string.Empty, Scalar(connection, "SELECT scanned_at FROM systems"));
            Assert.Equal("1", Scalar(connection, "SELECT game_count FROM systems"));
        }
    }

    [Fact]
    public void Migrating_twice_is_a_no_op()
    {
        var path = _dir.Combine("library.db");
        LibraryDatabase.Prepare(path, out _);

        Assert.Equal(LibraryOpenOutcome.Ready, LibraryDatabase.Prepare(path, out _));
    }

    [Fact]
    public void A_newer_userdata_db_is_refused_and_left_untouched()
    {
        var path = _dir.Combine("userdata.db");
        UserDatabase.Prepare(path, _clock);
        using (var connection = Sqlite.Open(path))
        {
            MigrationRunner.Execute(connection, "INSERT INTO favourites VALUES ('snes', 'a.sfc', 1); PRAGMA user_version = 99");
        }

        var error = Assert.Throws<DatabaseTooNewException>(() => UserDatabase.Prepare(path, _clock));

        Assert.Equal(99, error.Version);
        Assert.Contains("userdata.db", error.Message, StringComparison.Ordinal);
        using var check = Sqlite.Open(path);
        Assert.Equal("99", Scalar(check, "PRAGMA user_version"));
        Assert.Equal("1", Scalar(check, "SELECT COUNT(*) FROM favourites"));
    }

    [Fact]
    public void A_newer_library_db_is_recreated_empty()
    {
        var path = _dir.Combine("library.db");
        LibraryDatabase.Prepare(path, out _);
        using (var connection = Sqlite.Open(path))
        {
            MigrationRunner.Execute(connection, "INSERT INTO systems (system_id) VALUES ('snes'); PRAGMA user_version = 99");
        }

        var outcome = LibraryDatabase.Prepare(path, out var reason);

        Assert.Equal(LibraryOpenOutcome.Recreated, outcome);
        Assert.Contains("schema version 99", reason, StringComparison.Ordinal);
        using var check = Sqlite.Open(path);
        Assert.Equal("0", Scalar(check, "SELECT COUNT(*) FROM systems"));
        Assert.Equal(MigrationRunner.Library[^1].Version.ToString(System.Globalization.CultureInfo.InvariantCulture), Scalar(check, "PRAGMA user_version"));
    }

    [Fact]
    public void A_corrupt_library_db_is_recreated_empty()
    {
        var path = _dir.Combine("library.db");
        File.WriteAllText(path, "this is not a database, just some text that is long enough to be read as a header");

        var outcome = LibraryDatabase.Prepare(path, out var reason);

        Assert.Equal(LibraryOpenOutcome.Recreated, outcome);
        Assert.NotNull(reason);
        using var check = Sqlite.Open(path);
        Assert.Equal("0", Scalar(check, "SELECT COUNT(*) FROM games"));
    }

    [Fact]
    public void A_library_migration_that_fails_on_the_existing_data_recreates_the_db()
    {
        var path = _dir.Combine("library.db");
        LibraryDatabase.Prepare(path, out _);
        using (var connection = Sqlite.Open(path))
        {
            MigrationRunner.Execute(connection, "INSERT INTO systems (system_id) VALUES ('snes')");
        }

        // Works on an empty DB, but not on this one.
        List<Migration> next = [.. MigrationRunner.Library, new Migration(MigrationRunner.Library.Count + 1, "seed", "INSERT INTO systems (system_id) VALUES ('snes');")];

        var outcome = LibraryDatabase.Prepare(path, next, out var reason);

        Assert.Equal(LibraryOpenOutcome.Recreated, outcome);
        Assert.Contains("UNIQUE", reason, StringComparison.Ordinal);
        using var check = Sqlite.Open(path);
        Assert.Equal(next.Count.ToString(System.Globalization.CultureInfo.InvariantCulture), Scalar(check, "PRAGMA user_version"));
    }

    [Fact]
    public void Upgrading_userdata_writes_a_backup_first_and_keeps_the_newest_three()
    {
        var path = _dir.Combine("userdata.db");
        UserDatabase.Prepare(path, _clock);
        using (var connection = Sqlite.Open(path))
        {
            MigrationRunner.Execute(connection, "INSERT INTO favourites VALUES ('snes', 'a.sfc', 1)");
        }

        var migrations = MigrationRunner.User.ToList();
        for (var step = 1; step <= 4; step++)
        {
            _clock.Advance(TimeSpan.FromMinutes(1));
            migrations.Add(new Migration(migrations.Count + 1, $"step{step}", $"CREATE TABLE extra{step} (x INTEGER) STRICT;"));
            UserDatabase.Prepare(path, migrations, _clock);
        }

        var backups = UserDatabase.ListBackups(path);
        Assert.Equal(UserDatabase.BackupsKept, backups.Count);

        // The oldest (taken at version 1) was pruned; the newest was taken just before the last upgrade.
        Assert.DoesNotContain(backups, b => Path.GetFileName(b).StartsWith("userdata.db.v1-", StringComparison.Ordinal));
        var newest = backups[^1];
        Assert.StartsWith($"userdata.db.v{migrations.Count - 1}-", Path.GetFileName(newest), StringComparison.Ordinal);
        using var backup = Sqlite.Open(newest);
        Assert.Equal("1", Scalar(backup, "SELECT COUNT(*) FROM favourites"));
        Assert.Equal((migrations.Count - 1).ToString(System.Globalization.CultureInfo.InvariantCulture), Scalar(backup, "PRAGMA user_version"));
    }
}
