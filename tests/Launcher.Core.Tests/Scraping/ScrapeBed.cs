using System.Collections.Concurrent;
using System.Globalization;
using System.Net;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Scraping;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Scraping;

/// <summary>A clock the scraping tests move from several threads at once: each wait advances it instead of sleeping.</summary>
public sealed class SteppingClock(DateTimeOffset start) : TimeProvider
{
    private readonly object _lock = new();
    private DateTimeOffset _now = start;

    public override DateTimeOffset GetUtcNow()
    {
        lock (_lock)
        {
            return _now;
        }
    }

    public void Advance(TimeSpan by)
    {
        lock (_lock)
        {
            _now += by;
        }
    }
}

/// <summary>Collects log lines.</summary>
public sealed class ListLog : ILog
{
    public ConcurrentQueue<string> Lines { get; } = new();

    public void Write(LogLevel level, string message) => Lines.Enqueue($"{level}: {message}");
}

/// <summary>
/// A library with a few Mega Drive ROMs, fake credentials for all three providers, and a fake HTTP handler that
/// answers like each provider from the recorded fixtures. Credential placeholders in the fixtures are filled with
/// the fake credentials, as the real providers echo them, so redaction is tested for real.
/// </summary>
public sealed class ScrapeBed : IAsyncDisposable
{
    public const string DevId = "dev-id-7f3a";
    public const string DevPassword = "dev-pass-Q9x!";
    public const string SsUser = "ss-user-k2";
    public const string SsPassword = "ss-pass-Zz8#";
    public const string SgdbKey = "sgdb-key-5e1c0d";
    public const string IgdbClientId = "igdb-client-44aa";
    public const string IgdbSecret = "igdb-secret-90bb";

    public static readonly string[] AllCredentials = [DevId, DevPassword, SsUser, SsPassword, SgdbKey, IgdbClientId, IgdbSecret];

    private int _tokens;

    private ScrapeBed(TempDir dir) => Dir = dir;

    public TempDir Dir { get; }

    public SteppingClock Clock { get; } = new(new DateTimeOffset(2026, 9, 28, 10, 0, 0, TimeSpan.Zero));

    public FakeHttpHandler Http { get; } = new();

    public ListLog Log { get; } = new();

    public ConcurrentQueue<TimeSpan> Delays { get; } = new();

    public LibraryService Library { get; private set; } = null!;

    public PlatformPaths Paths { get; private set; } = null!;

    public AppConfig Config { get; private set; } = null!;

    /// <summary>The maxthreads ScreenScraper reports.</summary>
    public int MaxThreads { get; set; } = 2;

    /// <summary>requeststoday, as ScreenScraper reports it.</summary>
    public int RequestsToday { get; set; } = 10;

    public static string Fixture(string name) => File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Scraping", "Fixtures", name));

    public static async Task<ScrapeBed> CreateAsync(string? scraping = null)
    {
        var bed = new ScrapeBed(new TempDir());
        bed.Paths = PlatformPaths.InOneFolder(bed.Dir.Combine("user"), bed.Dir.Path);
        bed.Config = bed.LoadConfig(scraping);
        bed.Library = await LibraryService.OpenAsync(bed.Config, bed.Paths.DataDir, bed.Clock, TestContext.Current.CancellationToken);
        bed.Library.ConfigDir = bed.Paths.ConfigDir;
        bed.DefaultRoutes();
        return bed;
    }

    public AppConfig LoadConfig(string? scraping)
    {
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = Dir.Path,
            ConfigDir = Dir.Combine("user"),
            FileExists = null,
            Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = '{Dir.Combine("ROMs")}'\n\n[scraping]\n{scraping ?? string.Empty}\n"),
        });
        Assert.False(result.HasErrors, string.Join('\n', result.Diagnostics));
        return result.Config;
    }

    public void Reconfigure(string scraping)
    {
        Config = LoadConfig(scraping);
        Library.Config = Config;
    }

    public static ProviderAccounts Accounts(bool screenScraper = true, bool igdb = true, bool steamGridDb = true)
    {
        var values = new Dictionary<string, string>();
        if (screenScraper)
        {
            values["screenscraper.dev_id"] = DevId;
            values["screenscraper.dev_password"] = DevPassword;
            values["screenscraper.username"] = SsUser;
            values["screenscraper.password"] = SsPassword;
        }

        if (igdb)
        {
            values["igdb.client_id"] = IgdbClientId;
            values["igdb.client_secret"] = IgdbSecret;
        }

        if (steamGridDb)
        {
            values["steamgriddb.api_key"] = SgdbKey;
        }

        return ProviderAccounts.FromValues(values);
    }

    /// <summary>A service over the bed's library. Waits advance the clock and are recorded, so nothing sleeps.</summary>
    public ScrapeService Service(ProviderAccounts? accounts = null, bool derivatives = false, RetryPolicy? retry = null) =>
        new(new ScrapeServiceOptions
        {
            Library = Library,
            Paths = Paths,
            Accounts = accounts ?? Accounts(),
            HttpHandler = Http,
            Clock = Clock,
            Delay = (duration, token) =>
            {
                token.ThrowIfCancellationRequested();
                Delays.Enqueue(duration);
                Clock.Advance(duration);
                return Task.CompletedTask;
            },
            Retry = retry ?? new RetryPolicy(4, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(30)),
            Log = Log,
            ImageDecoder = derivatives ? PlatformServices.CreateImageDecoder() : null,
        });

    /// <summary>Closes the library and opens it again, as the next run would; optionally deleting library.db first.</summary>
    public async Task ReopenAsync(bool deleteLibrary)
    {
        Library.Dispose();
        SqliteConnection.ClearAllPools();
        if (deleteLibrary)
        {
            Launcher.Core.Data.Sqlite.DeleteFiles(Path.Combine(Paths.DataDir, LibraryService.LibraryFileName));
        }

        Library = await LibraryService.OpenAsync(Config, Paths.DataDir, Clock, TestContext.Current.CancellationToken);
        Library.ConfigDir = Paths.ConfigDir;
    }

    public string Rom(string relPath, string content = "rom data") => Dir.File("ROMs/" + relPath, content);

    public Task ScanAsync() => Library.RescanAsync(null, null, TestContext.Current.CancellationToken);

    /// <summary>A fixture with every placeholder filled in.</summary>
    public string Fill(string fixture, RecordedRequest? request = null) => Fixture(fixture)
        .Replace("{{DEVID}}", Uri.EscapeDataString(DevId), StringComparison.Ordinal)
        .Replace("{{DEVPASSWORD}}", Uri.EscapeDataString(DevPassword), StringComparison.Ordinal)
        .Replace("{{SSID}}", SsUser, StringComparison.Ordinal)
        .Replace("{{SSPASSWORD}}", Uri.EscapeDataString(SsPassword), StringComparison.Ordinal)
        .Replace("{{MAXTHREADS}}", MaxThreads.ToString(CultureInfo.InvariantCulture), StringComparison.Ordinal)
        .Replace("{{TODAY}}", RequestsToday.ToString(CultureInfo.InvariantCulture), StringComparison.Ordinal)
        .Replace("{{CRC}}", request?.Query("crc") ?? "00000000", StringComparison.Ordinal);

    public static bool Is(Uri uri, string host, string pathContains) =>
        (uri.Host == host || uri.Host.EndsWith("." + host, StringComparison.Ordinal)) && uri.AbsolutePath.Contains(pathContains, StringComparison.Ordinal);

    /// <summary>The providers' default answers: Sonic 3 is found everywhere, anything else nowhere.</summary>
    public void DefaultRoutes()
    {
        // ScreenScraper.
        Http.On("GET", u => Is(u, "screenscraper.fr", "ssuserInfos.php"), _ => FakeHttpHandler.Json(Fill("ss_ssuserinfos.json")));
        Http.On("GET", u => Is(u, "screenscraper.fr", "jeuInfos.php"), r =>
            (r.Query("romnom") ?? string.Empty).StartsWith("Sonic the Hedgehog 3", StringComparison.Ordinal) || r.Query("gameid") == "1187"
                ? FakeHttpHandler.Json(Fill("ss_jeuinfos.json", r))
                : FakeHttpHandler.Text("Erreur : Rom/Iso/Dossier non trouvée !  ", HttpStatusCode.NotFound));
        Http.On("GET", u => Is(u, "screenscraper.fr", "jeuRecherche.php"), _ => FakeHttpHandler.Json(Fill("ss_jeurecherche_empty.json")));
        Http.On("GET", u => Is(u, "screenscraper.fr", "mediaJeu.php"), r => FakeHttpHandler.Bytes(Png(r.Query("media") ?? "x")));

        // Twitch and IGDB.
        Http.On("POST", u => u.Host == "id.twitch.tv", _ =>
            FakeHttpHandler.Json($$"""{"access_token":"token-{{Interlocked.Increment(ref _tokens)}}-{{Guid.NewGuid():N}}","expires_in":5184000,"token_type":"bearer"}"""));
        Http.On("POST", u => u.Host == "api.igdb.com", r =>
            (r.Body ?? string.Empty).Contains("search \"Sonic the Hedgehog 3\"", StringComparison.Ordinal) || (r.Body ?? string.Empty).Contains("where id = 1234;", StringComparison.Ordinal)
                ? FakeHttpHandler.Json(Fixture("igdb_games.json"))
                : FakeHttpHandler.Json("[]"));
        Http.On("GET", u => u.Host == "images.igdb.com", r => FakeHttpHandler.Bytes(Png(r.Uri.AbsolutePath)));

        // SteamGridDB.
        Http.On("GET", u => Is(u, "steamgriddb.com", "/api/v2/search/autocomplete/"), r =>
            r.Uri.AbsolutePath.Contains("Sonic%20the%20Hedgehog%203", StringComparison.Ordinal)
                ? FakeHttpHandler.Json(Fixture("sgdb_search.json"))
                : FakeHttpHandler.Json("""{"success":true,"data":[]}"""));
        Http.On("GET", u => Is(u, "steamgriddb.com", "/api/v2/grids/game/"), _ => FakeHttpHandler.Json(Fixture("sgdb_grids.json")));
        Http.On("GET", u => Is(u, "steamgriddb.com", "/api/v2/heroes/game/"), _ => FakeHttpHandler.Json(Fixture("sgdb_heroes.json")));
        Http.On("GET", u => Is(u, "steamgriddb.com", "/api/v2/logos/game/"), _ => FakeHttpHandler.Json(Fixture("sgdb_logos.json")));
        Http.On("GET", u => u.Host == "cdn2.steamgriddb.com", r => FakeHttpHandler.Bytes(Png(r.Uri.AbsolutePath)));
    }

    /// <summary>A small real PNG whose colour depends on <paramref name="seed"/>, so different media differ.</summary>
    public static byte[] Png(string seed)
    {
        var hash = (uint)seed.GetHashCode(StringComparison.Ordinal);
        return TestImages.RealPng(24, 32, (x, y) => ((byte)hash, (byte)(hash >> 8), (byte)(hash >> 16), 255));
    }

    public async Task<GameDetails> Game(string system, string relPath) =>
        (await Library.GetGameAsync(new GameKey(system, relPath.ToLowerInvariant()), TestContext.Current.CancellationToken))!;

    public T Query<T>(string sql, params (string Name, object Value)[] parameters)
    {
        using var connection = new SqliteConnection($"Data Source={Path.Combine(Paths.DataDir, LibraryService.LibraryFileName)};Pooling=False");
        connection.Open();
        using (var attach = connection.CreateCommand())
        {
            attach.CommandText = "ATTACH DATABASE $path AS user";
            attach.Parameters.AddWithValue("$path", Path.Combine(Paths.DataDir, LibraryService.UserDataFileName));
            attach.ExecuteNonQuery();
        }

        using var command = connection.CreateCommand();
        command.CommandText = sql;
        foreach (var (name, value) in parameters)
        {
            command.Parameters.AddWithValue(name, value);
        }

        var result = command.ExecuteScalar();
        return result is null or DBNull ? default! : (T)Convert.ChangeType(result, Nullable.GetUnderlyingType(typeof(T)) ?? typeof(T), CultureInfo.InvariantCulture);
    }

    public void Execute(string sql)
    {
        using var connection = new SqliteConnection($"Data Source={Path.Combine(Paths.DataDir, LibraryService.UserDataFileName)};Pooling=False");
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    public ValueTask DisposeAsync()
    {
        Library.Dispose();
        SqliteConnection.ClearAllPools();
        Dir.Dispose();
        return ValueTask.CompletedTask;
    }
}
