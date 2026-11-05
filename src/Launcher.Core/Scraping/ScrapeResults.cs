using Launcher.Core.Library;
using Launcher.Core.Media;

namespace Launcher.Core.Scraping;

/// <summary>A provider's state, for the settings screen and the console.</summary>
public enum ProviderState
{
    Ready,

    /// <summary>No credentials: skipped, never an error.</summary>
    MissingCredentials,

    /// <summary>Quota used up, closed, or credentials refused: resting until <see cref="ProviderStatus.Until"/> (null: until restart).</summary>
    Resting,
}

/// <param name="InOrder">Whether config's provider and fallback list names it.</param>
public sealed record ProviderStatus(string Id, string DisplayName, ProviderState State, string? Message, DateTimeOffset? Until, bool InOrder);

/// <summary>Something the user should know about a provider during a batch (skipped for want of credentials, or resting).</summary>
public sealed record ProviderNotice(string Provider, ProviderState State, string Message, DateTimeOffset? Until);

/// <summary>One game's scrape.</summary>
/// <param name="Status">'ok', 'partial', 'not_found', 'error', or 'skipped' (no provider could look it up; nothing written).</param>
/// <param name="Providers">The providers that found it, in order.</param>
/// <param name="Media">The media kinds saved.</param>
/// <param name="Log">Each provider tried, with its outcome.</param>
public sealed record ScrapeGameResult(
    GameKey Game,
    string Status,
    IReadOnlyList<string> Providers,
    IReadOnlyList<string> Media,
    IReadOnlyList<ProviderLog> Log)
{
    /// <summary>The provider each saved kind came from: only this result says, as the media folder doesn't (A4).</summary>
    public IReadOnlyDictionary<string, string> MediaSources { get; init; } = new Dictionary<string, string>();
}

/// <summary>A batch's outcome.</summary>
/// <param name="Paused">The service stopped (the app closed) before the batch finished: it resumes on the next start.</param>
public sealed record ScrapeBatchResult(
    long BatchId,
    string Kind,
    int Total,
    int Done,
    int Failed,
    bool Cancelled,
    bool Paused,
    IReadOnlyList<ProviderNotice> Notices);

/// <summary>The settings screen's "test connection" (M7), written for the user; never holds a credential.</summary>
public sealed record ConnectionTestResult(string Provider, bool Succeeded, string Message);

/// <summary>What "scrape all missing" would take on, counted before it starts (M7).</summary>
/// <param name="Systems">Each system with games to scrape, in config order.</param>
public sealed record MissingSummary(int Games, IReadOnlyList<(string SystemId, int Games)> Systems);

/// <summary>What "scrape this system" would take on, counted before it starts (M7), with each filter's games (2026-10-04).</summary>
/// <param name="Games">Every game of the system: each is scraped (matched ones fetched by id).</param>
/// <param name="Missing">Those never successfully scraped, or without a front cover.</param>
/// <param name="NoCover">Those without a front cover (<see cref="SystemScrapeFilter.NoCover"/>).</param>
/// <param name="NoScreenshot">Those without a screenshot (<see cref="SystemScrapeFilter.NoScreenshot"/>).</param>
/// <param name="NotRecent">Those not scraped within <see cref="ScrapeService.RecentScrape"/> (<see cref="SystemScrapeFilter.NotRecent"/>).</param>
public sealed record SystemScrapeCount(int Games, int Missing, int NoCover, int NoScreenshot, int NotRecent)
{
    /// <summary>How many games <paramref name="filter"/> takes on.</summary>
    public int Of(SystemScrapeFilter filter) => filter switch
    {
        SystemScrapeFilter.NoCover => NoCover,
        SystemScrapeFilter.NoScreenshot => NoScreenshot,
        SystemScrapeFilter.NotRecent => NotRecent,
        _ => Games,
    };
}

/// <summary>
/// Which of a system's games "scrape this system" takes on (2026-10-04). Whichever it is, a game's scrape downloads
/// only the media kinds it has no file for, and fetches a matched game by id.
/// </summary>
public enum SystemScrapeFilter
{
    /// <summary>Every game.</summary>
    All,

    /// <summary>Games without a front cover (any: scraped, the user's own or imported).</summary>
    NoCover,

    /// <summary>Games without a screenshot.</summary>
    NoScreenshot,

    /// <summary>Games never scraped, or last scraped (whatever the outcome) longer ago than <see cref="ScrapeService.RecentScrape"/>.</summary>
    NotRecent,
}

/// <summary>One search hit for a manual match.</summary>
/// <param name="Similarity">How close its name is to the search, 0 to 1 (<see cref="TitleMatcher.Similarity"/>).</param>
/// <param name="MatchedBy">How the game's file matched it, for a hit from the provider's ROM index (<see cref="MatchMethods.Filename"/> or <see cref="MatchMethods.Hash"/>); null for a title search's.</param>
/// <param name="Cover">Its front cover, to fetch with <see cref="ScrapeService.GetMatchCoverAsync"/>; null when the provider has no covers.</param>
public sealed record MatchCandidate(string ProviderGameId, string Name, string? Year, double Similarity, string? MatchedBy = null, MatchCover? Cover = null);

/// <summary>
/// A search hit's front cover (2026-10-07), shown beside it so that games of one name can be told apart, fetched with
/// <see cref="ScrapeService.GetMatchCoverAsync"/>. What to download stays in Core: a provider's URL may hold
/// credentials (ScreenScraper's do).
/// </summary>
public sealed class MatchCover
{
    internal MatchCover(string provider, ScrapeCandidate candidate)
    {
        Provider = provider;
        Candidate = candidate;
    }

    public string Provider { get; }

    public string ProviderGameId => Candidate.ProviderGameId;

    internal ScrapeCandidate Candidate { get; }

    public override string ToString() => $"{Provider} {ProviderGameId} cover";
}

/// <summary>
/// One image the user can choose for a kind once they've chosen a provider's game (2026-10-15: the art chooser of
/// manual matching). Its thumbnail comes from <see cref="ScrapeService.GetArtThumbAsync"/>; choosing it means passing it
/// to <see cref="ScrapeService.ScrapeGameWithMatchAsync(GameKey, string, string, IReadOnlyList{ArtChoice}, CancellationToken)"/>.
/// What to download stays in Core, as for <see cref="MatchCover"/>.
/// </summary>
public sealed class ArtChoice
{
    internal ArtChoice(string provider, string providerGameId, ScrapedArt art)
    {
        Provider = provider;
        ProviderGameId = providerGameId;
        Art = art;
    }

    public string Provider { get; }

    public string ProviderGameId { get; }

    /// <summary>A <see cref="MediaKinds"/> value: cover, logo or hero.</summary>
    public string Kind => Art.Kind;

    /// <summary>The full image's size; 0 when the provider doesn't say.</summary>
    public int Width => Art.Width;

    public int Height => Art.Height;

    /// <summary>The provider's word for its style, when it has one.</summary>
    public string? Style => Art.Style;

    internal ScrapedArt Art { get; }

    public override string ToString() => $"{Provider} {ProviderGameId} {Kind}";
}

/// <summary>The images a provider's game offers for each kind, when it has more than one (the art chooser).</summary>
/// <param name="Kinds">Each wanted kind with two images or more, cover then logo then hero; each list in the order a scrape takes them, at most <see cref="ScrapeService.ArtChoiceLimit"/>.</param>
public sealed record ArtChoices(string Provider, string ProviderGameId, IReadOnlyList<(string Kind, IReadOnlyList<ArtChoice> Choices)> Kinds)
{
    public static ArtChoices None(string provider, string providerGameId) => new(provider, providerGameId, []);
}

/// <summary>One provider's answer to a manual match search.</summary>
/// <param name="InOrder">Whether config's provider and fallback list names it; one that doesn't is still used for the game if the user chooses one of its results.</param>
/// <param name="Candidates">The file's own match first (<see cref="MatchCandidate.MatchedBy"/>), then the closest name; empty when nothing was found or it wasn't searched.</param>
/// <param name="Problem">Why it wasn't searched (no credentials, no id for the system, resting) or why the search failed, written for the user; null when it was searched.</param>
/// <param name="Current">The game's match on this provider now: the user's own, else the one found automatically; null when it has none.</param>
public sealed record ProviderMatches(
    string Provider,
    string DisplayName,
    bool InOrder,
    IReadOnlyList<MatchCandidate> Candidates,
    string? Problem,
    string? Current,
    bool CurrentIsManual);

/// <summary>Every provider's results for a manual match, in config order, then the providers config doesn't name.</summary>
/// <param name="Term">The name searched for.</param>
public sealed record MatchSearch(GameKey Game, string Term, IReadOnlyList<ProviderMatches> Providers);

/// <summary>What clearing a game removed.</summary>
/// <param name="KeptSharedArt">Media files another game also uses (by stem): their rows went, the files stay.</param>
public sealed record ClearResult(bool Found, int FilesDeleted, IReadOnlyList<string> KeptSharedArt);
