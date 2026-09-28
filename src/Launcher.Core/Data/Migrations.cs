using System.Globalization;
using System.Reflection;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Data;

/// <summary>One numbered schema step. Version n takes a DB from <c>user_version</c> n-1 to n.</summary>
public sealed record Migration(int Version, string Name, string Sql);

/// <summary>The database is newer than this build understands.</summary>
public sealed class DatabaseTooNewException(string path, int version, int supported)
    : Exception($"'{path}' has schema version {version}, but this version of Odyssey Launcher only understands up to {supported}.")
{
    public int Version { get; } = version;

    public int Supported { get; } = supported;
}

/// <summary>
/// Applies embedded, numbered SQL migrations (<c>Data/Migrations/{Library,User}/NNNN_name.sql</c>), following
/// SQLite's documented procedure: foreign keys off before BEGIN, apply every migration newer than
/// <c>user_version</c>, <c>foreign_key_check</c>, bump <c>user_version</c>, commit (ARCHITECTURE.md A4).
/// </summary>
public static class MigrationRunner
{
    public static IReadOnlyList<Migration> Library { get; } = LoadEmbedded("migrations/library/");

    public static IReadOnlyList<Migration> User { get; } = LoadEmbedded("migrations/user/");

    public static int GetVersion(SqliteConnection connection)
    {
        ArgumentNullException.ThrowIfNull(connection);
        using var command = connection.CreateCommand();
        command.CommandText = "PRAGMA user_version";
        return Convert.ToInt32(command.ExecuteScalar(), CultureInfo.InvariantCulture);
    }

    /// <summary>Brings the DB up to the last migration. Returns the version it started at.</summary>
    /// <exception cref="DatabaseTooNewException">The DB is newer than the last migration.</exception>
    public static int Migrate(SqliteConnection connection, IReadOnlyList<Migration> migrations, string path)
    {
        ArgumentNullException.ThrowIfNull(connection);
        ArgumentNullException.ThrowIfNull(migrations);
        var from = GetVersion(connection);
        var latest = migrations.Count == 0 ? 0 : migrations[^1].Version;
        if (from > latest)
        {
            throw new DatabaseTooNewException(path, from, latest);
        }

        if (from == latest)
        {
            return from;
        }

        Execute(connection, "PRAGMA foreign_keys = OFF");
        try
        {
            using var transaction = connection.BeginTransaction();
            foreach (var migration in migrations)
            {
                if (migration.Version > from)
                {
                    Execute(connection, migration.Sql, transaction);
                }
            }

            using (var check = connection.CreateCommand())
            {
                check.Transaction = transaction;
                check.CommandText = "PRAGMA foreign_key_check";
                using var reader = check.ExecuteReader();
                if (reader.Read())
                {
                    throw new InvalidOperationException(
                        $"Migrating '{path}' to version {latest} broke a foreign key in table '{reader.GetString(0)}'.");
                }
            }

            Execute(connection, string.Create(CultureInfo.InvariantCulture, $"PRAGMA user_version = {latest}"), transaction);
            transaction.Commit();
        }
        finally
        {
            Execute(connection, "PRAGMA foreign_keys = ON");
        }

        return from;
    }

    internal static void Execute(SqliteConnection connection, string sql, SqliteTransaction? transaction = null)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    private static List<Migration> LoadEmbedded(string prefix)
    {
        var assembly = Assembly.GetExecutingAssembly();
        var migrations = new List<Migration>();
        foreach (var resource in assembly.GetManifestResourceNames())
        {
            if (!resource.StartsWith(prefix, StringComparison.Ordinal))
            {
                continue;
            }

            var fileName = resource[prefix.Length..];
            var underscore = fileName.IndexOf('_', StringComparison.Ordinal);
            if (underscore <= 0 || !int.TryParse(fileName.AsSpan(0, underscore), NumberStyles.None, CultureInfo.InvariantCulture, out var version))
            {
                throw new InvalidOperationException($"Migration '{resource}' must be named NNNN_name.sql.");
            }

            using var stream = assembly.GetManifestResourceStream(resource)!;
            using var reader = new StreamReader(stream);
            migrations.Add(new Migration(version, Path.GetFileNameWithoutExtension(fileName)[(underscore + 1)..], reader.ReadToEnd()));
        }

        migrations.Sort((a, b) => a.Version.CompareTo(b.Version));
        for (var i = 0; i < migrations.Count; i++)
        {
            if (migrations[i].Version != i + 1)
            {
                throw new InvalidOperationException($"Migrations under '{prefix}' must be numbered 1, 2, 3... without gaps.");
            }
        }

        return migrations;
    }
}
