using System.Globalization;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Data;

/// <summary>Opens connections with the settings every connection uses (ARCHITECTURE.md A1).</summary>
public static class Sqlite
{
    public const int BusyTimeoutMs = 5000;

    /// <summary>
    /// Opens a connection with WAL, <c>foreign_keys=ON</c>, <c>synchronous=NORMAL</c> and <c>busy_timeout</c>.
    /// Connections aren't pooled by Microsoft.Data.Sqlite: <see cref="ReaderPool"/> pools them itself, so
    /// ATTACHed databases and file swaps are under our control.
    /// </summary>
    /// <param name="queryOnly">
    /// For readers: <c>PRAGMA query_only</c>, which also covers ATTACHed DBs. (A read-only open can fail on a
    /// WAL database whose <c>-shm</c> file doesn't exist yet, so readers open read-write and are made query-only.)
    /// </param>
    /// <param name="attachUserData">If set, this <c>userdata.db</c> is ATTACHed as schema <c>user</c>, for the grid queries' joins.</param>
    public static SqliteConnection Open(string path, bool queryOnly = false, string? attachUserData = null)
    {
        ArgumentNullException.ThrowIfNull(path);
        var builder = new SqliteConnectionStringBuilder
        {
            DataSource = path,
            Mode = queryOnly ? SqliteOpenMode.ReadWrite : SqliteOpenMode.ReadWriteCreate,
            Pooling = false,
            Cache = SqliteCacheMode.Private,
        };

        var connection = new SqliteConnection(builder.ToString());
        try
        {
            connection.Open();
            MigrationRunner.Execute(connection, string.Create(
                CultureInfo.InvariantCulture,
                $"PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON; PRAGMA synchronous = NORMAL; PRAGMA busy_timeout = {BusyTimeoutMs}"));
            if (attachUserData is not null)
            {
                using var attach = connection.CreateCommand();
                attach.CommandText = "ATTACH DATABASE $path AS user";
                attach.Parameters.AddWithValue("$path", attachUserData);
                attach.ExecuteNonQuery();
                MigrationRunner.Execute(connection, "PRAGMA user.synchronous = NORMAL");
            }

            if (queryOnly)
            {
                MigrationRunner.Execute(connection, "PRAGMA query_only = ON");
            }

            return connection;
        }
        catch
        {
            connection.Dispose();
            throw;
        }
    }

    /// <summary>Deletes a DB and its <c>-wal</c> and <c>-shm</c> files.</summary>
    public static void DeleteFiles(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        foreach (var file in (ReadOnlySpan<string>)[path, path + "-wal", path + "-shm", path + "-journal"])
        {
            File.Delete(file);
        }
    }
}

/// <summary>What happened when <c>library.db</c> was opened.</summary>
public enum LibraryOpenOutcome
{
    /// <summary>It was at the current version, or was migrated to it.</summary>
    Ready,

    /// <summary>It didn't exist, so it was created empty.</summary>
    Created,

    /// <summary>It was newer than this build, unreadable, or a migration failed, so it was recreated empty and needs a full scan.</summary>
    Recreated,
}

public static class LibraryDatabase
{
    /// <summary>
    /// Opens (or creates) <c>library.db</c> and migrates it. Because the library is rebuildable, a DB that is
    /// newer than this build, corrupt, or fails to migrate is deleted and recreated empty (A4).
    /// Does file I/O: never call it on the main thread.
    /// </summary>
    public static LibraryOpenOutcome Prepare(string path, out string? recreatedBecause) =>
        Prepare(path, MigrationRunner.Library, out recreatedBecause);

    internal static LibraryOpenOutcome Prepare(string path, IReadOnlyList<Migration> migrations, out string? recreatedBecause)
    {
        ArgumentNullException.ThrowIfNull(path);
        recreatedBecause = null;
        var existed = File.Exists(path);
        try
        {
            using var connection = Sqlite.Open(path);
            MigrationRunner.Migrate(connection, migrations, path);
            return existed ? LibraryOpenOutcome.Ready : LibraryOpenOutcome.Created;
        }
        catch (Exception e) when (e is SqliteException or DatabaseTooNewException or InvalidOperationException)
        {
            recreatedBecause = e.Message;
        }

        SqliteConnection.ClearAllPools();
        Sqlite.DeleteFiles(path);
        using (var fresh = Sqlite.Open(path))
        {
            MigrationRunner.Migrate(fresh, migrations, path);
        }

        return LibraryOpenOutcome.Recreated;
    }
}

public static class UserDatabase
{
    public const int BackupsKept = 3;

    /// <summary>
    /// Opens (or creates) <c>userdata.db</c> and migrates it. Before migrating an existing DB it's copied with
    /// <c>VACUUM INTO</c>, and only the newest <see cref="BackupsKept"/> backups are kept (A4).
    /// Does file I/O: never call it on the main thread.
    /// </summary>
    /// <exception cref="DatabaseTooNewException">The DB is newer than this build. It's left untouched: user data can't be rebuilt.</exception>
    public static void Prepare(string path, TimeProvider clock) => Prepare(path, MigrationRunner.User, clock);

    internal static void Prepare(string path, IReadOnlyList<Migration> migrations, TimeProvider clock)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(clock);
        using var connection = Sqlite.Open(path);
        var version = MigrationRunner.GetVersion(connection);
        var latest = migrations.Count == 0 ? 0 : migrations[^1].Version;
        if (version > latest)
        {
            throw new DatabaseTooNewException(path, version, latest);
        }

        if (version > 0 && version < latest)
        {
            Backup(connection, path, version, clock);
        }

        MigrationRunner.Migrate(connection, migrations, path);
    }

    /// <summary>Backups sit next to the DB: <c>userdata.db.v1-20260928-101500.bak</c>.</summary>
    public static IReadOnlyList<string> ListBackups(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var directory = Path.GetDirectoryName(Path.GetFullPath(path))!;
        if (!Directory.Exists(directory))
        {
            return [];
        }

        var backups = Directory.GetFiles(directory, Path.GetFileName(path) + ".v*.bak");
        Array.Sort(backups, (a, b) => File.GetLastWriteTimeUtc(a).CompareTo(File.GetLastWriteTimeUtc(b)) is var byTime and not 0
            ? byTime
            : string.CompareOrdinal(a, b));
        return backups;
    }

    private static void Backup(SqliteConnection connection, string path, int version, TimeProvider clock)
    {
        var stamp = clock.GetUtcNow().ToString("yyyyMMdd-HHmmssfff", CultureInfo.InvariantCulture);
        var backup = string.Create(CultureInfo.InvariantCulture, $"{path}.v{version}-{stamp}.bak");
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "VACUUM INTO $path";
            command.Parameters.AddWithValue("$path", backup);
            command.ExecuteNonQuery();
        }

        var backups = ListBackups(path);
        for (var i = 0; i < backups.Count - BackupsKept; i++)
        {
            File.Delete(backups[i]);
        }
    }
}
