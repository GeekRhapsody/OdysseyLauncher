using Launcher.Core.Config;

namespace Launcher.Core.Library;

/// <summary>A game's identity: stable across rebuilds and case-only renames (ARCHITECTURE.md A4).</summary>
public readonly record struct GameKey(string SystemId, string PathKey);

/// <summary>A row of the systems grid, for boot.</summary>
public sealed record SystemSummary(string SystemId, string Name, int GameCount, DateTimeOffset? ScannedAt);

/// <summary>Which root a media path is relative to.</summary>
public enum MediaRoot
{
    None,

    /// <summary>DataDir: scraped media.</summary>
    Data,

    /// <summary>ConfigDir: the user's own art.</summary>
    Config,
}

/// <summary>
/// One cell of a games grid: only what the grid draws, plus the id to ask for more
/// (<see cref="ILibrary.GetGameAsync"/>).
/// </summary>
public readonly record struct GameRow(long GameId, string Title, string? CoverPath, MediaRoot CoverRoot, bool IsFavourite);

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
    string? TitleOverride);

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

    Task<IReadOnlyList<VirtualGameRow>> GetFavouritesAsync(CancellationToken cancellationToken);

    Task<IReadOnlyList<VirtualGameRow>> GetRecentlyPlayedAsync(int limit, CancellationToken cancellationToken);

    Task<GameDetails?> GetGameAsync(long gameId, CancellationToken cancellationToken);

    Task SetFavouriteAsync(GameKey game, bool favourite, CancellationToken cancellationToken);

    /// <summary>Null restores the scraped or file-name title.</summary>
    Task SetTitleOverrideAsync(GameKey game, string? title, CancellationToken cancellationToken);

    Task SetHiddenAsync(GameKey game, bool hidden, CancellationToken cancellationToken);

    /// <summary>Rescans one system, or every enabled one when <paramref name="systemId"/> is null (which also drops disabled systems).</summary>
    Task<ScanSummary> RescanAsync(string? systemId, IProgress<JobProgress>? progress, CancellationToken cancellationToken);

    /// <summary>Builds a new library.db from disk, with no network, and swaps it in atomically.</summary>
    Task<ScanSummary> RebuildAsync(IProgress<JobProgress>? progress, CancellationToken cancellationToken);
}
