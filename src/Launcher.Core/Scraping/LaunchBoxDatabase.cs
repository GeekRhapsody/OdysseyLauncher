using System.Collections.Concurrent;
using System.Globalization;
using System.IO.Compression;
using System.Net;
using System.Net.Http.Headers;
using System.Text.Json.Nodes;
using System.Xml;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Scraping;

/// <summary>What the local copy of LaunchBox's Games DB holds.</summary>
/// <param name="Published">The dump's Last-Modified, when LaunchBox sent one.</param>
/// <param name="Checked">When LaunchBox was last asked for a newer dump.</param>
/// <param name="Games">The games in the index.</param>
public sealed record LaunchBoxInfo(DateTimeOffset? Published, DateTimeOffset Checked, int Games);

/// <summary>What an update of the local copy did.</summary>
public enum LaunchBoxUpdateOutcome
{
    /// <summary>LaunchBox has nothing newer (or the copy was checked recently enough).</summary>
    Unchanged,

    /// <summary>A new dump was downloaded and indexed.</summary>
    Updated,
}

/// <summary>An update's progress: the phase ("Downloading", "Indexing") and megabytes done of the total (0 when unknown).</summary>
public sealed class LaunchBoxProgressEventArgs(JobProgress progress) : EventArgs
{
    public JobProgress Progress { get; } = progress;
}

/// <summary>An update ended: <see cref="Outcome"/> when it worked; otherwise why not, or that it was cancelled.</summary>
public sealed class LaunchBoxUpdateEndedEventArgs(LaunchBoxUpdateOutcome? outcome, string? error, bool cancelled) : EventArgs
{
    public LaunchBoxUpdateOutcome? Outcome { get; } = outcome;

    /// <summary>For the user; null when it worked or was cancelled.</summary>
    public string? Error { get; } = error;

    public bool Cancelled { get; } = cancelled;
}

/// <summary>One name a game can be found by: its own, or one of its alternate names.</summary>
/// <param name="Norm">The name normalised (<see cref="TitleMatcher.Normalise"/>).</param>
/// <param name="Year">The game's release year, when LaunchBox has one.</param>
public sealed record LaunchBoxTitle(long Id, string Name, string Norm, bool Alternate, string? Year);

/// <summary>
/// The local copy of LaunchBox's Games DB (ARCHITECTURE.md A5, "LaunchBox Games DB"). LaunchBox has no API: it publishes
/// its whole database once a day as <c>Metadata.zip</c> (about 110 MB, 500 MB of XML), which this downloads and streams
/// into an SQLite index, <c>CacheDir/launchbox/launchbox.db</c>, so games are looked up offline and only their images
/// are fetched. The index is a cache: it has no migrations, and an index of another <see cref="SchemaVersion"/> is
/// rebuilt from a fresh download. A copy older than <see cref="CheckInterval"/> is checked again with a conditional
/// request, so an unchanged dump costs one small request. One update runs at a time, whoever asks for it, and it
/// isn't cancelled by its callers (only by <see cref="CancelUpdate"/>): readers keep the old index until the new one
/// is swapped in. Every method does file I/O: never call one on the main thread.
/// </summary>
public sealed class LaunchBoxDatabase : IDisposable
{
    public const string DumpUrl = "https://gamesdb.launchbox-app.com/Metadata.zip";

    public const string FileName = "launchbox.db";

    /// <summary>The index's tables' version: an index of another one is rebuilt.</summary>
    public const int SchemaVersion = 1;

    /// <summary>How old the copy gets before LaunchBox is asked for a newer one.</summary>
    public static readonly TimeSpan CheckInterval = TimeSpan.FromDays(7);

    /// <summary>How long the download may go without a byte before the attempt is abandoned.</summary>
    public static readonly TimeSpan StallTimeout = TimeSpan.FromSeconds(60);

    private const int Attempts = 3;
    private const long Megabyte = 1024 * 1024;

    private static readonly XmlReaderSettings XmlSettings = new()
    {
        IgnoreWhitespace = true,
        IgnoreComments = true,
        IgnoreProcessingInstructions = true,
        DtdProcessing = DtdProcessing.Prohibit,
        XmlResolver = null,
        CloseInput = false,
    };

    private readonly string _folder;
    private readonly string _path;
    private readonly HttpClient _client;
    private readonly TimeProvider _clock;
    private readonly Delay _delay;
    private readonly ILog _log;
    private readonly ReaderWriterLockSlim _swap = new();
    private readonly object _lock = new();
    private readonly object _infoLock = new();
    private readonly ConcurrentDictionary<string, IReadOnlyList<LaunchBoxTitle>> _titles = new(StringComparer.Ordinal);
    private Task<LaunchBoxUpdateOutcome>? _running;
    private CancellationTokenSource? _runningCancel;
    private LaunchBoxInfo? _info;
    private bool _infoRead;
    private int _generation;
    private bool _disposed;

    /// <param name="folder">Where the index lives (<c>CacheDir/launchbox</c>).</param>
    /// <param name="handler">Null uses the network (tests pass a fake).</param>
    /// <param name="delay">Null waits for real.</param>
    public LaunchBoxDatabase(string folder, HttpMessageHandler? handler, TimeProvider clock, Delay? delay, ILog log)
    {
        ArgumentNullException.ThrowIfNull(folder);
        ArgumentNullException.ThrowIfNull(clock);
        _folder = folder;
        _path = Path.Combine(folder, FileName);
        _client = ScraperHttp.CreateClient(handler);
        _clock = clock;
        _delay = delay ?? ScraperHttp.RealDelay(clock);
        _log = log ?? NullLog.Instance;
    }

    /// <summary>The index file.</summary>
    public string IndexPath => _path;

    /// <summary>An update started (on a worker thread).</summary>
    public event EventHandler? UpdateStarted;

    /// <summary>An update's progress (on a worker thread), a few times a second at most.</summary>
    public event EventHandler<LaunchBoxProgressEventArgs>? UpdateProgress;

    /// <summary>An update ended (on a worker thread).</summary>
    public event EventHandler<LaunchBoxUpdateEndedEventArgs>? UpdateEnded;

    /// <summary>The copy's state; null when there's no index (or one of another schema).</summary>
    public LaunchBoxInfo? Info
    {
        get
        {
            lock (_infoLock)
            {
                if (!_infoRead)
                {
                    _info = ReadInfo();
                    _infoRead = true;
                }

                return _info;
            }
        }
    }

    /// <summary>There's an index to look games up in.</summary>
    public bool IsReady => Info is not null;

    /// <summary>There's no index, or LaunchBox hasn't been asked for a newer dump in <see cref="CheckInterval"/>.</summary>
    public bool NeedsCheck => Info is not { } info || _clock.GetUtcNow() - info.Checked >= CheckInterval;

    /// <summary>An update is running.</summary>
    public bool Updating
    {
        get
        {
            lock (_lock)
            {
                return _running is { IsCompleted: false };
            }
        }
    }

    /// <summary>
    /// Brings the copy up to date: downloads and indexes the dump when there's no index, or when LaunchBox has a newer
    /// one (asked only when <paramref name="force"/> or <see cref="NeedsCheck"/>). Joins an update already running.
    /// <paramref name="cancellationToken"/> stops this caller waiting, not the update.
    /// </summary>
    /// <exception cref="ProviderException">The download or the index failed (the old index, if any, is kept).</exception>
    /// <exception cref="OperationCanceledException">The update was cancelled (<see cref="CancelUpdate"/>), or the caller stopped waiting.</exception>
    public Task<LaunchBoxUpdateOutcome> UpdateAsync(bool force, CancellationToken cancellationToken)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        lock (_lock)
        {
            if (_running is { IsCompleted: false } running)
            {
                return running.WaitAsync(cancellationToken);
            }

            if (!force && !NeedsCheck)
            {
                return Task.FromResult(LaunchBoxUpdateOutcome.Unchanged);
            }

            _runningCancel?.Dispose();
            _runningCancel = new CancellationTokenSource();
            var token = _runningCancel.Token;
            _running = Task.Run(() => RunUpdateAsync(token), CancellationToken.None);
            return _running.WaitAsync(cancellationToken);
        }
    }

    /// <summary>Cancels the running update, if any: the old index, if any, is kept.</summary>
    public void CancelUpdate()
    {
        lock (_lock)
        {
            if (_running is { IsCompleted: false })
            {
                _runningCancel?.Cancel();
            }
        }
    }

    /// <summary>The game LaunchBox's <c>Files.xml</c> names for a file (its name without the extension), on one of <paramref name="platforms"/>.</summary>
    public string? FindFile(IReadOnlyList<string> platforms, string fileStem)
    {
        ArgumentNullException.ThrowIfNull(platforms);
        ArgumentNullException.ThrowIfNull(fileStem);
        return Read(connection =>
        {
            using var command = connection.CreateCommand();
            command.CommandText = $"SELECT game_name FROM files WHERE file = $file AND platform IN ({PlatformParameters(command, platforms)}) LIMIT 1";
            command.Parameters.AddWithValue("$file", fileStem.ToLowerInvariant());
            return command.ExecuteScalar() as string;
        }, null);
    }

    /// <summary>The title <c>Mame.xml</c> gives a MAME set's short name, e.g. "Pac-Man (Midway)" for <c>pacman</c>.</summary>
    public string? FindMame(string shortName)
    {
        ArgumentNullException.ThrowIfNull(shortName);
        return Read(connection =>
        {
            using var command = connection.CreateCommand();
            command.CommandText = "SELECT name FROM mame WHERE short_name = $name";
            command.Parameters.AddWithValue("$name", shortName.ToLowerInvariant());
            return command.ExecuteScalar() as string;
        }, null);
    }

    /// <summary>
    /// Every name the games of <paramref name="platforms"/> can be found by (each game's own name first), by game id.
    /// Kept in memory until the index changes: a lookup scores the ROM's title against all of them.
    /// </summary>
    public IReadOnlyList<LaunchBoxTitle> Titles(IReadOnlyList<string> platforms)
    {
        ArgumentNullException.ThrowIfNull(platforms);
        var key = string.Join('\n', platforms.Order(StringComparer.Ordinal));
        if (_titles.TryGetValue(key, out var cached))
        {
            return cached;
        }

        var generation = Volatile.Read(ref _generation);
        var titles = Read<IReadOnlyList<LaunchBoxTitle>>(connection =>
        {
            using var command = connection.CreateCommand();
            var inList = PlatformParameters(command, platforms);
            command.CommandText = $"""
                SELECT g.id, g.name, g.norm, 0, COALESCE(substr(g.release, 1, 4), g.year) FROM games g WHERE g.platform IN ({inList})
                UNION ALL
                SELECT a.game_id, a.name, a.norm, 1, COALESCE(substr(g.release, 1, 4), g.year)
                FROM alt_names a JOIN games g ON g.id = a.game_id WHERE g.platform IN ({inList})
                ORDER BY 1, 4
                """;
            var list = new List<LaunchBoxTitle>();
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                list.Add(new LaunchBoxTitle(
                    reader.GetInt64(0),
                    reader.GetString(1),
                    reader.GetString(2),
                    reader.GetInt64(3) == 1,
                    reader.IsDBNull(4) ? null : Convert.ToString(reader.GetValue(4), CultureInfo.InvariantCulture)));
            }

            return list;
        }, []);

        // Not kept when the index was swapped meanwhile: it may be the old one's.
        if (IsReady && Volatile.Read(ref _generation) == generation)
        {
            _titles[key] = titles;
        }

        return titles;
    }

    /// <summary>
    /// A game with its alternate names and the images the index keeps, as the JSON <see cref="LaunchBoxScraper.Parse"/>
    /// reads (and a scrape saves); null when the index has no such game.
    /// </summary>
    public string? Load(long id) => Read(connection =>
    {
        JsonObject game;
        using (var command = connection.CreateCommand())
        {
            command.CommandText = """
                SELECT id, platform, name, release, year, overview, developer, publisher, genres, players, rating
                FROM games WHERE id = $id
                """;
            command.Parameters.AddWithValue("$id", id);
            using var reader = command.ExecuteReader();
            if (!reader.Read())
            {
                return null;
            }

            game = new JsonObject
            {
                ["id"] = reader.GetInt64(0).ToString(CultureInfo.InvariantCulture),
                ["platform"] = reader.GetString(1),
                ["name"] = reader.GetString(2),
                ["release"] = Text(reader, 3),
                ["year"] = reader.IsDBNull(4) ? null : reader.GetInt64(4),
                ["overview"] = Text(reader, 5),
                ["developer"] = Text(reader, 6),
                ["publisher"] = Text(reader, 7),
                ["genres"] = Text(reader, 8),
                ["players"] = reader.IsDBNull(9) ? null : reader.GetInt64(9),
                ["rating"] = reader.IsDBNull(10) ? null : reader.GetDouble(10),
            };
        }

        var names = new JsonArray();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT name, region FROM alt_names WHERE game_id = $id ORDER BY rowid";
            command.Parameters.AddWithValue("$id", id);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                names.Add(new JsonObject { ["name"] = reader.GetString(0), ["region"] = Text(reader, 1) });
            }
        }

        var images = new JsonArray();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT type, region, file FROM images WHERE game_id = $id ORDER BY rowid";
            command.Parameters.AddWithValue("$id", id);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                images.Add(new JsonObject { ["type"] = reader.GetString(0), ["region"] = Text(reader, 1), ["file"] = reader.GetString(2) });
            }
        }

        game["alternate_names"] = names;
        game["images"] = images;
        return game.ToJsonString();
    }, null);

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        Task? running;
        lock (_lock)
        {
            running = _running;
            _runningCancel?.Cancel();
        }

        try
        {
            running?.Wait(TimeSpan.FromSeconds(10));
        }
        catch (AggregateException)
        {
            // Cancelled or failed: the old index is kept.
        }

        _runningCancel?.Dispose();
        _client.Dispose();
        _swap.Dispose();
    }

    // ---- Updating ------------------------------------------------------------------------------------

    private async Task<LaunchBoxUpdateOutcome> RunUpdateAsync(CancellationToken token)
    {
        UpdateStarted?.Invoke(this, EventArgs.Empty);
        var zip = Path.Combine(_folder, "Metadata.zip.part");
        try
        {
            var outcome = await DownloadAndIndexAsync(zip, token).ConfigureAwait(false);
            UpdateEnded?.Invoke(this, new LaunchBoxUpdateEndedEventArgs(outcome, null, false));
            return outcome;
        }
        catch (OperationCanceledException)
        {
            _log.Write(LogLevel.Info, $"{ScraperIds.LaunchBox}: the database update was cancelled; the old copy, if any, is kept");
            UpdateEnded?.Invoke(this, new LaunchBoxUpdateEndedEventArgs(null, null, true));
            throw;
        }
        catch (Exception e)
        {
            var failure = e as ProviderException
                ?? new ProviderException(ScraperIds.LaunchBox, ProviderFailure.Transient, "LaunchBox's database couldn't be updated: " + e.Message, inner: e);
            _log.Write(LogLevel.Warning, $"{ScraperIds.LaunchBox}: {failure.Message}");
            UpdateEnded?.Invoke(this, new LaunchBoxUpdateEndedEventArgs(null, failure.Message, false));
            throw failure;
        }
        finally
        {
            TryDelete(zip);
            TryDeleteDatabase(_path + ".tmp");
        }
    }

    private async Task<LaunchBoxUpdateOutcome> DownloadAndIndexAsync(string zip, CancellationToken token)
    {
        Directory.CreateDirectory(_folder);
        var current = Info;
        Download download;
        for (var attempt = 1; ; attempt++)
        {
            try
            {
                download = await DownloadAsync(current, zip, token).ConfigureAwait(false);
                break;
            }
            catch (Exception e) when (attempt < Attempts && !token.IsCancellationRequested
                && e is HttpRequestException or IOException or TimeoutException or ProviderException { Failure: ProviderFailure.Transient })
            {
                var wait = TimeSpan.FromSeconds(10 * attempt);
                _log.Write(LogLevel.Warning, string.Create(CultureInfo.InvariantCulture,
                    $"{ScraperIds.LaunchBox}: database download: {e.Message}; retrying in {wait.TotalSeconds:0} s (attempt {attempt + 1} of {Attempts})"));
                await _delay(wait, token).ConfigureAwait(false);
            }
        }

        if (download.NotModified)
        {
            MarkChecked();
            _log.Write(LogLevel.Info, $"{ScraperIds.LaunchBox}: the database is up to date");
            return LaunchBoxUpdateOutcome.Unchanged;
        }

        var temp = _path + ".tmp";
        var games = await Task.Run(() => BuildIndex(zip, temp, download, token), token).ConfigureAwait(false);
        _swap.EnterWriteLock();
        try
        {
            File.Move(temp, _path, overwrite: true);
            lock (_infoLock)
            {
                _infoRead = false;
            }

            Interlocked.Increment(ref _generation);
            _titles.Clear();
        }
        finally
        {
            _swap.ExitWriteLock();
        }

        _log.Write(LogLevel.Info, string.Create(CultureInfo.InvariantCulture, $"{ScraperIds.LaunchBox}: indexed {games:N0} games"));
        return LaunchBoxUpdateOutcome.Updated;
    }

    private sealed record Download(bool NotModified, string? ETag, DateTimeOffset? LastModified);

    /// <summary>Streams the dump to <paramref name="zip"/>, or finds it unchanged since <paramref name="current"/>.</summary>
    private async Task<Download> DownloadAsync(LaunchBoxInfo? current, string zip, CancellationToken token)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, DumpUrl);
        if (current is not null)
        {
            if (ReadMeta("etag") is { } etag && EntityTagHeaderValue.TryParse(etag, out var tag))
            {
                request.Headers.IfNoneMatch.Add(tag);
            }

            if (current.Published is { } published)
            {
                request.Headers.IfModifiedSince = published;
            }
        }

        using var stall = CancellationTokenSource.CreateLinkedTokenSource(token);
        stall.CancelAfter(StallTimeout);
        try
        {
            using var response = await _client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, stall.Token).ConfigureAwait(false);
            if (response.StatusCode == HttpStatusCode.NotModified)
            {
                return new Download(true, null, null);
            }

            var status = (int)response.StatusCode;
            if (!response.IsSuccessStatusCode)
            {
                throw new ProviderException(ScraperIds.LaunchBox, status is 408 or 429 or >= 500 ? ProviderFailure.Transient : ProviderFailure.Rejected,
                    $"LaunchBox's database download was refused (HTTP {status})");
            }

            var total = response.Content.Headers.ContentLength ?? 0;
            var stream = await response.Content.ReadAsStreamAsync(stall.Token).ConfigureAwait(false);
            await using (stream.ConfigureAwait(false))
            {
                var file = new FileStream(zip, FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16, useAsync: true);
                await using (file.ConfigureAwait(false))
                {
                    var buffer = new byte[1 << 16];
                    long done = 0;
                    var reported = -1L;
                    int read;
                    while ((read = await stream.ReadAsync(buffer, stall.Token).ConfigureAwait(false)) > 0)
                    {
                        stall.CancelAfter(StallTimeout);
                        await file.WriteAsync(buffer.AsMemory(0, read), token).ConfigureAwait(false);
                        done += read;
                        if (done / Megabyte != reported)
                        {
                            reported = done / Megabyte;
                            Report("Downloading", done, total);
                        }
                    }
                }
            }

            return new Download(false, response.Headers.ETag?.ToString(), response.Content.Headers.LastModified);
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        {
            throw new TimeoutException($"LaunchBox's server sent nothing for {StallTimeout.TotalSeconds:0} seconds");
        }
    }

    /// <summary>Builds the index from the dump into <paramref name="temp"/>; returns the games indexed.</summary>
    private int BuildIndex(string zip, string temp, Download download, CancellationToken token)
    {
        TryDeleteDatabase(temp);
        using var archive = ZipFile.OpenRead(zip);
        var metadata = Entry(archive, "Metadata.xml")
            ?? throw new ProviderException(ScraperIds.LaunchBox, ProviderFailure.Transient, "LaunchBox's download had no Metadata.xml");
        ZipArchiveEntry?[] entries = [metadata, Entry(archive, "Files.xml"), Entry(archive, "Mame.xml")];
        var total = entries.Sum(e => e?.Length ?? 0);
        long before = 0;

        using var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = temp, Mode = SqliteOpenMode.ReadWriteCreate, Pooling = false }.ToString());
        connection.Open();
        Execute(connection, "PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF; PRAGMA page_size = 4096;");
        Execute(connection, """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID;
            CREATE TABLE games (
                id INTEGER PRIMARY KEY, platform TEXT NOT NULL, name TEXT NOT NULL, norm TEXT NOT NULL, release TEXT, year INTEGER,
                overview TEXT, developer TEXT, publisher TEXT, genres TEXT, players INTEGER, rating REAL);
            CREATE TABLE alt_names (game_id INTEGER NOT NULL, name TEXT NOT NULL, norm TEXT NOT NULL, region TEXT);
            CREATE TABLE images (game_id INTEGER NOT NULL, type TEXT NOT NULL, region TEXT, file TEXT NOT NULL);
            CREATE TABLE files (platform TEXT NOT NULL, file TEXT NOT NULL, game_name TEXT NOT NULL);
            CREATE TABLE mame (short_name TEXT PRIMARY KEY, name TEXT NOT NULL) WITHOUT ROWID;
            """);

        var games = 0;
        using (var transaction = connection.BeginTransaction())
        {
            using var insertGame = Command(connection, transaction,
                "INSERT OR REPLACE INTO games VALUES ($id, $platform, $name, $norm, $release, $year, $overview, $developer, $publisher, $genres, $players, $rating)");
            using var insertName = Command(connection, transaction, "INSERT INTO alt_names VALUES ($id, $name, $norm, $region)");
            using var insertImage = Command(connection, transaction, "INSERT INTO images VALUES ($id, $type, $region, $file)");
            using var insertFile = Command(connection, transaction, "INSERT INTO files VALUES ($platform, $file, $name)");
            using var insertMame = Command(connection, transaction, "INSERT OR REPLACE INTO mame VALUES ($short, $name)");
            var fields = new Dictionary<string, string>(StringComparer.Ordinal);

            foreach (var entry in entries)
            {
                if (entry is null)
                {
                    continue;
                }

                using var stream = new CountingStream(entry.Open());
                var reported = -1L;
                foreach (var tag in Records(stream, fields))
                {
                    token.ThrowIfCancellationRequested();
                    switch (tag)
                    {
                        case "Game" when Long(fields, "DatabaseID") is { } id && Field(fields, "Name") is { } name && Field(fields, "Platform") is { } platform:
                            Run(insertGame, id, platform, name, TitleMatcher.Normalise(name), ReleaseDate(Field(fields, "ReleaseDate")), Long(fields, "ReleaseYear"),
                                Field(fields, "Overview"), Field(fields, "Developer"), Field(fields, "Publisher"), Field(fields, "Genres"),
                                Long(fields, "MaxPlayers"), Double(fields, "CommunityRating"));
                            games++;
                            break;
                        case "GameAlternateName" when Long(fields, "DatabaseID") is { } id && Field(fields, "AlternateName") is { } name:
                            Run(insertName, id, name, TitleMatcher.Normalise(name), Field(fields, "Region"));
                            break;
                        case "GameImage" when Long(fields, "DatabaseID") is { } id && Field(fields, "Type") is { } type && Field(fields, "FileName") is { } file
                            && LaunchBoxScraper.ImageTypes.Contains(type):
                            Run(insertImage, id, type, Field(fields, "Region"), file);
                            break;
                        case "File" when Field(fields, "Platform") is { } platform && Field(fields, "FileName") is { } file && Field(fields, "GameName") is { } game
                            && !string.Equals(file, game, StringComparison.OrdinalIgnoreCase):
                            // A file named as its game adds nothing to the title lookup.
                            Run(insertFile, platform, file.ToLowerInvariant(), game);
                            break;
                        case "MameFile" when Field(fields, "FileName") is { } file && Field(fields, "Name") is { } name:
                            Run(insertMame, file.ToLowerInvariant(), name);
                            break;
                    }

                    var done = before + stream.Position;
                    if (done / (8 * Megabyte) != reported)
                    {
                        reported = done / (8 * Megabyte);
                        Report("Indexing", done, total);
                    }
                }

                before += entry.Length;
            }

            using (var meta = Command(connection, transaction, "INSERT INTO meta VALUES ($key, $value)"))
            {
                foreach (var (key, value) in (ReadOnlySpan<(string, string?)>)
                [
                    ("schema", SchemaVersion.ToString(CultureInfo.InvariantCulture)),
                    ("etag", download.ETag),
                    ("published", download.LastModified?.ToString("O", CultureInfo.InvariantCulture)),
                    ("checked", _clock.GetUtcNow().ToString("O", CultureInfo.InvariantCulture)),
                    ("games", games.ToString(CultureInfo.InvariantCulture)),
                ])
                {
                    Run(meta, key, value);
                }
            }

            Execute(connection, transaction, """
                CREATE INDEX games_platform ON games (platform);
                CREATE INDEX alt_names_game ON alt_names (game_id);
                CREATE INDEX images_game ON images (game_id);
                CREATE INDEX files_file ON files (file, platform);
                """);
            transaction.Commit();
        }

        Execute(connection, "PRAGMA optimize;");
        return games;
    }

    private static ZipArchiveEntry? Entry(ZipArchive archive, string name) =>
        archive.Entries.FirstOrDefault(e => string.Equals(e.FullName, name, StringComparison.OrdinalIgnoreCase));

    /// <summary>
    /// The dump's records, one element under the root each (a <c>Game</c>, a <c>GameImage</c>, ...), with their child
    /// elements' text in <paramref name="fields"/> (cleared for each): streamed, never the whole document.
    /// </summary>
    private static IEnumerable<string> Records(Stream stream, Dictionary<string, string> fields)
    {
        using var reader = XmlReader.Create(stream, XmlSettings);
        if (reader.MoveToContent() != XmlNodeType.Element || reader.IsEmptyElement)
        {
            yield break;
        }

        var recordDepth = reader.Depth + 1;
        reader.Read();
        while (!reader.EOF)
        {
            if (reader.NodeType != XmlNodeType.Element || reader.Depth != recordDepth)
            {
                reader.Read();
                continue;
            }

            var tag = reader.LocalName;
            fields.Clear();
            if (reader.IsEmptyElement)
            {
                reader.Read();
                yield return tag;
                continue;
            }

            reader.Read();
            while (!reader.EOF && !(reader.NodeType == XmlNodeType.EndElement && reader.Depth == recordDepth))
            {
                if (reader.NodeType == XmlNodeType.Element && reader.Depth == recordDepth + 1)
                {
                    var name = reader.LocalName;
                    fields[name] = reader.ReadElementContentAsString();
                }
                else
                {
                    reader.Read();
                }
            }

            reader.Read();
            yield return tag;
        }
    }

    private void Report(string phase, long done, long total) =>
        UpdateProgress?.Invoke(this, new LaunchBoxProgressEventArgs(new JobProgress(phase, (int)(done / Megabyte), (int)(total / Megabyte))));

    /// <summary>LaunchBox had nothing newer: the copy counts as checked now.</summary>
    private void MarkChecked()
    {
        _swap.EnterReadLock();
        try
        {
            using var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = _path, Mode = SqliteOpenMode.ReadWrite, Pooling = false }.ToString());
            connection.Open();
            using var command = connection.CreateCommand();
            command.CommandText = $"PRAGMA busy_timeout = {Data.Sqlite.BusyTimeoutMs}; INSERT OR REPLACE INTO meta VALUES ('checked', $value)";
            command.Parameters.AddWithValue("$value", _clock.GetUtcNow().ToString("O", CultureInfo.InvariantCulture));
            command.ExecuteNonQuery();
        }
        finally
        {
            _swap.ExitReadLock();
        }

        lock (_infoLock)
        {
            _infoRead = false;
        }
    }

    // ---- Reading -------------------------------------------------------------------------------------

    private LaunchBoxInfo? ReadInfo()
    {
        try
        {
            return Read(connection =>
            {
                var meta = new Dictionary<string, string>(StringComparer.Ordinal);
                using var command = connection.CreateCommand();
                command.CommandText = "SELECT key, value FROM meta";
                using var reader = command.ExecuteReader();
                while (reader.Read())
                {
                    if (!reader.IsDBNull(1))
                    {
                        meta[reader.GetString(0)] = reader.GetString(1);
                    }
                }

                if (!meta.TryGetValue("schema", out var schema) || schema != SchemaVersion.ToString(CultureInfo.InvariantCulture)
                    || !meta.TryGetValue("checked", out var checkedText)
                    || !DateTimeOffset.TryParse(checkedText, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var checkedAt))
                {
                    return null;
                }

                DateTimeOffset? published = meta.TryGetValue("published", out var publishedText)
                    && DateTimeOffset.TryParse(publishedText, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var p) ? p : null;
                var games = meta.TryGetValue("games", out var count) && int.TryParse(count, NumberStyles.None, CultureInfo.InvariantCulture, out var n) ? n : 0;
                return new LaunchBoxInfo(published, checkedAt, games);
            }, null);
        }
        catch (SqliteException e)
        {
            // Unreadable (another version's, or damaged): rebuilt by the next update.
            _log.Write(LogLevel.Warning, $"{ScraperIds.LaunchBox}: the database copy is unreadable ({e.Message}); it will be downloaded again");
            return null;
        }
    }

    private string? ReadMeta(string key) => Read(connection =>
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT value FROM meta WHERE key = $key";
        command.Parameters.AddWithValue("$key", key);
        return command.ExecuteScalar() as string;
    }, null);

    /// <summary>Runs a query on the index, which isn't swapped meanwhile; <paramref name="missing"/> when there's no index.</summary>
    private T Read<T>(Func<SqliteConnection, T> read, T missing)
    {
        _swap.EnterReadLock();
        try
        {
            if (!File.Exists(_path))
            {
                return missing;
            }

            using var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = _path, Mode = SqliteOpenMode.ReadOnly, Pooling = false }.ToString());
            connection.Open();
            return read(connection);
        }
        finally
        {
            _swap.ExitReadLock();
        }
    }

    private static string PlatformParameters(SqliteCommand command, IReadOnlyList<string> platforms)
    {
        if (platforms.Count == 0)
        {
            return "NULL";
        }

        var names = new string[platforms.Count];
        for (var i = 0; i < platforms.Count; i++)
        {
            names[i] = "$p" + i.ToString(CultureInfo.InvariantCulture);
            command.Parameters.AddWithValue(names[i], platforms[i]);
        }

        return string.Join(", ", names);
    }

    // ---- Helpers -------------------------------------------------------------------------------------

    /// <summary>The date part of a release date ("2000-08-11T00:00:00-07:00" is 2000-08-11, as LaunchBox shows it).</summary>
    private static string? ReleaseDate(string? text) =>
        text is { Length: >= 10 } && DateOnly.TryParseExact(text.AsSpan(0, 10), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out _)
            ? text[..10]
            : null;

    private static string? Field(Dictionary<string, string> fields, string name) =>
        fields.TryGetValue(name, out var value) && !string.IsNullOrWhiteSpace(value) ? value.Trim() : null;

    private static long? Long(Dictionary<string, string> fields, string name) =>
        Field(fields, name) is { } text && long.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value) ? value : null;

    private static double? Double(Dictionary<string, string> fields, string name) =>
        Field(fields, name) is { } text && double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) ? value : null;

    private static string? Text(SqliteDataReader reader, int column) => reader.IsDBNull(column) ? null : reader.GetString(column);

    private static SqliteCommand Command(SqliteConnection connection, SqliteTransaction transaction, string sql)
    {
        var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        var start = 0;
        while ((start = sql.IndexOf('$', start)) >= 0)
        {
            var end = start + 1;
            while (end < sql.Length && (char.IsLetterOrDigit(sql[end]) || sql[end] == '_'))
            {
                end++;
            }

            command.Parameters.Add(new SqliteParameter(sql[start..end], null));
            start = end;
        }

        command.Prepare();
        return command;
    }

    /// <summary>Runs a prepared command with its parameters, in order, set to <paramref name="values"/> (null as NULL).</summary>
    private static void Run(SqliteCommand command, params object?[] values)
    {
        for (var i = 0; i < values.Length; i++)
        {
            command.Parameters[i].Value = values[i] ?? DBNull.Value;
        }

        command.ExecuteNonQuery();
    }

    private static void Execute(SqliteConnection connection, string sql) => Execute(connection, null, sql);

    private static void Execute(SqliteConnection connection, SqliteTransaction? transaction, string sql)
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    private static void TryDelete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch (IOException)
        {
            // Left for the next update, which overwrites it.
        }
        catch (UnauthorizedAccessException)
        {
            // As above.
        }
    }

    private static void TryDeleteDatabase(string path)
    {
        foreach (var file in (ReadOnlySpan<string>)[path, path + "-journal"])
        {
            TryDelete(file);
        }
    }

    /// <summary>A read-only stream that counts what's been read through it (a zip entry's stream has no position).</summary>
    private sealed class CountingStream(Stream inner) : Stream
    {
        private long _read;

        public override bool CanRead => true;

        public override bool CanSeek => false;

        public override bool CanWrite => false;

        public override long Length => throw new NotSupportedException();

        public override long Position
        {
            get => _read;
            set => throw new NotSupportedException();
        }

        public override int Read(byte[] buffer, int offset, int count)
        {
            var read = inner.Read(buffer, offset, count);
            _read += read;
            return read;
        }

        public override int Read(Span<byte> buffer)
        {
            var read = inner.Read(buffer);
            _read += read;
            return read;
        }

        public override void Flush()
        {
        }

        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();

        public override void SetLength(long value) => throw new NotSupportedException();

        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                inner.Dispose();
            }

            base.Dispose(disposing);
        }
    }
}
