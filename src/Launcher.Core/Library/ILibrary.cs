using Launcher.Core.Config;

namespace Launcher.Core.Library;

/// <summary>A game's identity: stable across rebuilds and case-only renames (ARCHITECTURE.md A4).</summary>
public readonly record struct GameKey(string SystemId, string PathKey);

/// <summary>A row of the systems grid, for boot.</summary>
public sealed record SystemSummary(string SystemId, string Name, int GameCount, DateTimeOffset? ScannedAt);

/// <summary>
/// One cell of a games grid: only what the grid draws, plus the id to ask for more
/// (<see cref="ILibrary.GetGameAsync"/>).
/// </summary>
/// <param name="CoverPath">Relative to DataDir; null when the game has no cover.</param>
/// <param name="CoverAspect">The cover's width over its height, which the grid crops it by; 0 when unknown.</param>
/// <param name="CoverSizeBytes">The cover file's size when it was indexed, for its derivative's key; 0 when unknown.</param>
/// <param name="CoverMtimeMs">The cover file's modification time (unix ms) when it was indexed; 0 when unknown.</param>
public readonly record struct GameRow(
    long GameId,
    string Title,
    string? CoverPath,
    bool IsFavourite,
    float CoverAspect = 0,
    long CoverSizeBytes = 0,
    long CoverMtimeMs = 0);

/// <summary>One indexed media file: what the grid needs to name its derivative and crop it.</summary>
/// <param name="Path">Relative to DataDir (<c>media/&lt;system&gt;/&lt;kind&gt;/...</c>).</param>
/// <param name="Aspect">Width over height; 0 when unknown (models, and images whose header wasn't read).</param>
/// <param name="SizeBytes">The file's size when it was indexed; 0 when unknown.</param>
/// <param name="MtimeMs">The file's modification time (unix ms) when it was indexed; 0 when unknown.</param>
public readonly record struct MediaRef(string Path, float Aspect, long SizeBytes, long MtimeMs);

/// <summary>A game's media of one kind (<see cref="ILibrary.GetGameMediaAsync(string, IReadOnlyList{string}, CancellationToken)"/>).</summary>
public readonly record struct GameMediaRow(long GameId, string Kind, MediaRef Media);

/// <summary>Which games' media changed (<see cref="LibraryService.MediaChanged"/>).</summary>
/// <param name="games">The games whose <c>media</c> rows changed; null when any game's may have (a rebuild), or its derivatives were baked.</param>
public sealed class MediaChangedEventArgs(IReadOnlyList<GameKey>? games) : EventArgs
{
    public IReadOnlyList<GameKey>? Games { get; } = games;
}

/// <summary>A system's games, visible ones only, already in grid order.</summary>
public sealed record GameList(string SystemId, IReadOnlyList<GameRow> Games);

/// <summary>A cell of a virtual system (Favourites, Recently played), which mixes systems.</summary>
public readonly record struct VirtualGameRow(string SystemId, GameRow Game);

/// <summary>Everything about one game, for the focused item and for launching.</summary>
/// <param name="RomPath">Absolute path, with native separators.</param>
public sealed record GameDetails(
    GameKey Key,
    long GameId,
    string RomDir,
    string RelPath,
    string RomPath,
    string Title,
    string? Region,
    string? Languages,
    string? Revision,
    int? Disc,
    string? Tags,
    long SizeBytes,
    bool IsFavourite,
    bool IsHidden,
    string? TitleOverride,
    string? EmulatorOverride = null,
    GameMetadata? Metadata = null,
    ScrapeInfo? Scrape = null);

/// <summary>A game's last scrape (<c>scrape_state</c>, M4). Null on <see cref="GameDetails"/> means never scraped.</summary>
/// <param name="Status">'ok', 'partial' (a provider failed), 'not_found' or 'error'.</param>
/// <param name="Providers">The providers that supplied data, in the order used.</param>
public sealed record ScrapeInfo(string Status, IReadOnlyList<string> Providers, DateTimeOffset ScrapedAt);

/// <summary>Metadata the user typed for one game (userdata.db). Null fields fall back to the scraped value; scraping never writes these.</summary>
public sealed record MetadataOverride(
    string? Description = null,
    string? ReleaseDate = null,
    string? Developer = null,
    string? Publisher = null,
    string? Genre = null,
    string? Players = null,
    double? Rating = null);

/// <summary>A game's metadata (A4): the scraped <c>metadata</c> row, with the user's overrides on top. Every field can be missing.</summary>
/// <param name="ReleaseDate">ISO 8601, possibly partial: '1991', '1991-06' or '1991-06-23'.</param>
/// <param name="Rating">0 to 1.</param>
/// <param name="Source">The providers it came from ('screenscraper,igdb'), or 'user' when only overrides are set.</param>
public sealed record GameMetadata(
    string? Description,
    string? ReleaseDate,
    string? Developer,
    string? Publisher,
    string? Genre,
    string? Players,
    double? Rating,
    string Source);

/// <summary>One of a game's media rows, for the game options panel (M7).</summary>
/// <param name="Width">From the image's header; null for a model, a video or an image whose header wasn't read.</param>
public sealed record GameMediaInfo(string Kind, MediaRef Media, int? Width, int? Height);

/// <summary>
/// A game's title and metadata with the scraped values and the user's own apart, for editing them (M7). The grid and
/// <see cref="GameDetails"/> show the user's value where there is one, else the scraped one.
/// </summary>
/// <param name="Title">The scraped title, else the one cleaned from the file name: what shows without an override.</param>
/// <param name="Scraped">The <c>metadata</c> row; null when the game has never been scraped (or nothing was found).</param>
/// <param name="Overrides">The user's metadata (userdata.db); every field null when there's none.</param>
public sealed record GameMetadataEdit(GameKey Key, string Title, string? TitleOverride, GameMetadata? Scraped, MetadataOverride Overrides);

/// <summary>A game's play statistics from userdata.db.</summary>
public sealed record PlayStats(int PlayCount, TimeSpan TotalPlayTime, DateTimeOffset? LastPlayedAt);

/// <summary>How a play session ended.</summary>
/// <param name="Duration">Measured on a monotonic clock; the session's <c>ended_at</c> is its start plus this.</param>
/// <param name="ExitCode">Null when the launcher didn't see the end (it crashed, or stopped watching).</param>
/// <param name="CountAsPlay">
/// False for a launch that failed straight away: the session is kept, with its exit code, but play count, play
/// time and last played don't change.
/// </param>
public sealed record PlaySessionEnd(long SessionId, GameKey Game, DateTimeOffset StartedAt, TimeSpan Duration, int? ExitCode, bool CountAsPlay);

/// <summary>Play sessions and statistics in userdata.db (ARCHITECTURE.md A4). Writes go through the writer thread.</summary>
public interface IPlayHistory
{
    /// <summary>Records a session as started (<c>ended_at</c> NULL until it ends). Returns its id.</summary>
    Task<long> BeginSessionAsync(GameKey game, string emulatorId, DateTimeOffset startedAt, CancellationToken cancellationToken);

    /// <summary>Closes the session and, unless it's a failed launch, adds it to the game's statistics, in one transaction.</summary>
    Task EndSessionAsync(PlaySessionEnd end, CancellationToken cancellationToken);

    /// <summary>Null if the game has never been played.</summary>
    Task<PlayStats?> GetPlayStatsAsync(GameKey game, CancellationToken cancellationToken);
}

public sealed record JobProgress(string Phase, int Done, int Total);

public sealed record SystemScanSummary(
    string SystemId,
    int Added,
    int Updated,
    int Removed,
    int Unchanged,
    int FilesSeen,
    int PlaylistsRead);

public sealed record ScanSummary(
    IReadOnlyList<SystemScanSummary> Systems,
    IReadOnlyList<Diagnostic> Diagnostics,
    TimeSpan Elapsed)
{
    public int Added => Systems.Sum(s => s.Added);

    public int Updated => Systems.Sum(s => s.Updated);

    public int Removed => Systems.Sum(s => s.Removed);

    public int Unchanged => Systems.Sum(s => s.Unchanged);
}

/// <summary>
/// The façade the app uses (ARCHITECTURE.md A1, A2). Reads run on the thread pool; writes go through one
/// writer thread. Every method is safe to call from the Godot main thread, but results must reach nodes
/// through the budgeted main-thread queue, not plain <c>await</c> continuations (A3).
/// </summary>
public interface ILibrary
{
    /// <summary>Boot: one small indexed query. Enabled systems in config order, with their game counts.</summary>
    Task<IReadOnlyList<SystemSummary>> GetSystemsAsync(CancellationToken cancellationToken);

    /// <summary>Entering a system: one indexed query of compact, pre-sorted rows.</summary>
    Task<GameList> GetGamesAsync(string systemId, CancellationToken cancellationToken);

    /// <summary>
    /// A system's media of the given kinds, for the slots a theme's templates use (M6): one row per game and kind that
    /// has a file. One indexed query, like <see cref="GetGamesAsync"/>.
    /// </summary>
    Task<IReadOnlyList<GameMediaRow>> GetGameMediaAsync(string systemId, IReadOnlyList<string> kinds, CancellationToken cancellationToken);

    /// <summary>The same for chosen games: a virtual system's, or games whose media just changed.</summary>
    Task<IReadOnlyList<GameMediaRow>> GetGameMediaAsync(IReadOnlyList<long> gameIds, IReadOnlyList<string> kinds, CancellationToken cancellationToken);

    Task<IReadOnlyList<VirtualGameRow>> GetFavouritesAsync(CancellationToken cancellationToken);

    Task<IReadOnlyList<VirtualGameRow>> GetRecentlyPlayedAsync(int limit, CancellationToken cancellationToken);

    Task<GameDetails?> GetGameAsync(long gameId, CancellationToken cancellationToken);

    /// <summary>By identity, for <c>--launch</c> and the virtual systems. Null if it isn't in the library.</summary>
    Task<GameDetails?> GetGameAsync(GameKey game, CancellationToken cancellationToken);

    Task SetFavouriteAsync(GameKey game, bool favourite, CancellationToken cancellationToken);

    /// <summary>The emulator profile this game launches with. Null goes back to the system's emulator.</summary>
    Task SetEmulatorOverrideAsync(GameKey game, string? emulatorId, CancellationToken cancellationToken);

    /// <summary>Null restores the scraped or file-name title.</summary>
    Task SetTitleOverrideAsync(GameKey game, string? title, CancellationToken cancellationToken);

    Task SetHiddenAsync(GameKey game, bool hidden, CancellationToken cancellationToken);

    /// <summary>Replaces the game's metadata overrides; <c>new MetadataOverride()</c> clears them.</summary>
    Task SetMetadataOverrideAsync(GameKey game, MetadataOverride values, CancellationToken cancellationToken);

    /// <summary>Rescans one system, or every enabled one when <paramref name="systemId"/> is null (which also drops disabled systems).</summary>
    Task<ScanSummary> RescanAsync(string? systemId, IProgress<JobProgress>? progress, CancellationToken cancellationToken);

    /// <summary>Builds a new library.db from disk, with no network, and swaps it in atomically.</summary>
    Task<ScanSummary> RebuildAsync(IProgress<JobProgress>? progress, CancellationToken cancellationToken);
}
