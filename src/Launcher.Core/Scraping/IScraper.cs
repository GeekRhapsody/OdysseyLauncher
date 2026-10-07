using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Scanning;

namespace Launcher.Core.Scraping;

/// <summary>The provider ids, as config and the DB write them.</summary>
public static class ScraperIds
{
    public const string ScreenScraper = "screenscraper";
    public const string Igdb = "igdb";
    public const string SteamGridDb = "steamgriddb";
    public const string Steam = "steam";
}

/// <summary>The metadata a provider can supply (the <c>metadata</c> columns, A4).</summary>
public enum MetadataField
{
    Title,
    Description,
    ReleaseDate,
    Developer,
    Publisher,
    Genre,
    Players,
    Rating,
}

/// <summary>What a provider can supply: the fallback order only asks a provider for what it has.</summary>
/// <param name="Media">Media kinds (<see cref="Media.MediaKinds"/>).</param>
public sealed record ScraperCapabilities(IReadOnlySet<MetadataField> Fields, IReadOnlySet<string> Media);

/// <summary>How a provider's game was matched: the <c>scraper_matches.method</c> values.</summary>
public static class MatchMethods
{
    public const string Filename = "filename";
    public const string Hash = "hash";
    public const string Search = "search";
    public const string Manual = "manual";

    /// <summary>ScreenScraper's id from an imported ES-DE gamelist (2026-10-04): fetched by id, as any stored match is.</summary>
    public const string Gamelist = "gamelist";
}

/// <summary>Everything a provider may use to find a game.</summary>
/// <param name="FileName">The ROM's file name with its extension, no folders.</param>
/// <param name="Title">The cleaned file-name title, without a disc number: the search term.</param>
/// <param name="Hashes">Null when the file is too big to hash (or is a playlist).</param>
/// <param name="WantedMedia">The media kinds still wanted, so providers only fetch what's useful.</param>
public sealed record ScrapeQuery(
    GameKey Game,
    SystemConfig System,
    string FileName,
    string Title,
    long SizeBytes,
    RomHashes? Hashes,
    IReadOnlySet<string> WantedMedia);

/// <summary>One image a provider offers. <see cref="Url"/> may carry credentials (ScreenScraper): never log it unredacted.</summary>
/// <param name="Region">The provider's region code, when it has one.</param>
public sealed record ScrapedMedia(string Kind, string Url, string? Region = null);

/// <summary>A provider's answer for one game, normalised. Missing fields are null.</summary>
/// <param name="ReleaseDate">ISO 8601, possibly partial: '1994', '1994-01' or '1994-01-23'.</param>
/// <param name="Rating">0 to 1.</param>
public sealed record ScrapedGame(
    string ProviderGameId,
    string? Title = null,
    string? Description = null,
    string? ReleaseDate = null,
    string? Developer = null,
    string? Publisher = null,
    string? Genre = null,
    string? Players = null,
    double? Rating = null,
    IReadOnlyList<ScrapedMedia>? Media = null)
{
    public IReadOnlyList<ScrapedMedia> MediaOrEmpty => Media ?? [];

    public bool Has(MetadataField field) => field switch
    {
        MetadataField.Title => Title is not null,
        MetadataField.Description => Description is not null,
        MetadataField.ReleaseDate => ReleaseDate is not null,
        MetadataField.Developer => Developer is not null,
        MetadataField.Publisher => Publisher is not null,
        MetadataField.Genre => Genre is not null,
        MetadataField.Players => Players is not null,
        MetadataField.Rating => Rating is not null,
        _ => false,
    };
}

/// <summary>A search hit, for choosing a manual match (M7).</summary>
/// <param name="Method">How the file itself matched it (<see cref="MatchMethods.Filename"/> or <see cref="MatchMethods.Hash"/>): a hit from <see cref="IScraper.IdentifyFileAsync"/>; null for a title search's.</param>
/// <param name="Cover">Its front cover, small, when the provider's answer carried one (2026-10-07: shown beside the hit, so games of one name can be told apart). Its URL may hold credentials: never log it.</param>
public sealed record ScrapeCandidate(string ProviderGameId, string Name, string? Year, string? Method = null, ScrapedMedia? Cover = null);

/// <summary>A provider's result for one game.</summary>
/// <param name="Game">Null when not found.</param>
/// <param name="Method">How it was matched (<see cref="MatchMethods"/>); null for a fetch by a known id.</param>
/// <param name="Response">The raw response to save (the service redacts it first). When not found, what the provider said, if it says why (ScreenScraper); else null.</param>
public sealed record ProviderResult(ScrapedGame? Game, string? Method, string? Response)
{
    public static ProviderResult NotFound { get; } = new(null, null, null);

    public bool Found => Game is not null;
}

/// <summary>Why a provider call failed, which decides what the queue does next.</summary>
public enum ProviderFailure
{
    /// <summary>Network trouble, a server error or rate limiting that outlasted the retries: this game only.</summary>
    Transient,

    /// <summary>A request the provider refused as malformed: this game only.</summary>
    Rejected,

    /// <summary>The account's quota is used up: the provider rests until <see cref="ProviderException.Until"/>.</summary>
    QuotaExhausted,

    /// <summary>The provider is closed or overloaded: it rests until <see cref="ProviderException.Until"/>.</summary>
    Closed,

    /// <summary>The credentials were refused: the provider is left out until the app restarts.</summary>
    AuthFailed,
}

/// <summary>A provider call failed. The message is for the user and never contains credentials.</summary>
public sealed class ProviderException(string provider, ProviderFailure failure, string message, DateTimeOffset? until = null, Exception? inner = null)
    : Exception(message, inner)
{
    public string Provider { get; } = provider;

    public ProviderFailure Failure { get; } = failure;

    /// <summary>When the provider can be tried again, for <see cref="ProviderFailure.QuotaExhausted"/> and <see cref="ProviderFailure.Closed"/>.</summary>
    public DateTimeOffset? Until { get; } = until;
}

/// <summary>
/// A metadata and media provider (ARCHITECTURE.md A2). Implementations are thread-safe: the queue runs several
/// games at once, and each implementation bounds its own concurrency and request rate to the provider's limits.
/// </summary>
public interface IScraper
{
    /// <summary>A <see cref="ScraperIds"/> value.</summary>
    string Id { get; }

    string DisplayName { get; }

    ScraperCapabilities Capabilities { get; }

    /// <summary>Null when it can be used; otherwise why not, written for the user (missing credentials, and where to put them).</summary>
    string? Unavailable { get; }

    /// <summary>How many games may be worked on at once for this provider's sake (its thread or open-request limit).</summary>
    int MaxConcurrency { get; }

    /// <summary>Null when the provider can look up this system's games; otherwise why not (no platform id in config).</summary>
    string? Unsupported(SystemConfig system);

    /// <summary>Once per batch: account limits (ScreenScraper), an access token (IGDB).</summary>
    Task PrepareAsync(CancellationToken cancellationToken);

    /// <summary>Finds the game from the file (hashes, name, size) or a title search, and fetches it.</summary>
    Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken cancellationToken);

    /// <summary>Fetches a game by the provider's id: a stored or manual match, so no search.</summary>
    Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken cancellationToken);

    /// <summary>
    /// The settings screen's "test connection" (M7): one cheap request with the current credentials, and a line about
    /// the account for the user. Throws <see cref="ProviderException"/> when the credentials are missing or refused, or
    /// the provider can't be reached.
    /// </summary>
    Task<string> TestConnectionAsync(CancellationToken cancellationToken);

    /// <summary>Title search, for choosing a manual match.</summary>
    Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken cancellationToken);

    /// <summary>
    /// The game the file itself is known as, from the provider's ROM index (name, size, hashes), for choosing a manual
    /// match: a title search can't find an arcade set by its MAME short name, but ScreenScraper's ROM index can. Null
    /// when the file isn't known, or the provider has no such index.
    /// </summary>
    Task<ScrapeCandidate?> IdentifyFileAsync(ScrapeQuery query, CancellationToken cancellationToken);

    /// <summary>
    /// A search hit's front cover, small, to show beside it (manual matching): the one the search's answer carried
    /// (<see cref="ScrapeCandidate.Cover"/>), or, for a provider whose search has no art (SteamGridDB), one more request.
    /// Null when it has none. <see cref="DownloadAsync"/> fetches it.
    /// </summary>
    Task<ScrapedMedia?> SearchCoverAsync(ScrapeCandidate candidate, CancellationToken cancellationToken);

    /// <summary>Downloads one image. The bytes are checked (and rejected if they aren't an image) by the media store.</summary>
    Task<byte[]> DownloadAsync(ScrapedMedia media, CancellationToken cancellationToken);
}
