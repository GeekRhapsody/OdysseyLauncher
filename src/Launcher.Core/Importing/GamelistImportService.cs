using System.Globalization;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Scanning;

namespace Launcher.Core.Importing;

/// <summary>A media file to copy for a game: the kind it fills and the gamelist's file (absolute).</summary>
public sealed record GamelistCopy(string Kind, string Source);

/// <summary>What importing does for one game. Every value fills a gap: the game had none.</summary>
/// <param name="Title">A title to set as the user's, or null.</param>
/// <param name="Fill">Metadata to set as the user's (null fields: nothing to set).</param>
/// <param name="Favourite">It becomes a favourite (it isn't one).</param>
/// <param name="ScreenScraperId">To store as its ScreenScraper match (it has none).</param>
/// <param name="Media">Files of kinds it has no media for.</param>
public sealed record GamelistGame(
    GameKey Key,
    string RelPath,
    string? Title,
    MetadataOverride Fill,
    bool Favourite,
    string? ScreenScraperId,
    IReadOnlyList<GamelistCopy> Media)
{
    public bool HasMetadata => Title is not null || Fill != Empty;

    internal static MetadataOverride Empty { get; } = new();
}

/// <summary>
/// An import worked out before it's run, for the question asked first: what the gamelist has, what matched the
/// library, and what it would add.
/// </summary>
/// <param name="Entries">The gamelist's games.</param>
/// <param name="InLibrary">Those that are games of the system in the library.</param>
/// <param name="NotInLibrary">Those that aren't (not scanned, moved, or named for another folder).</param>
/// <param name="Games">The games it would change.</param>
/// <param name="Hidden">Games the gamelist hides: not imported, as the launcher can't show them again yet.</param>
/// <param name="Error">Why the gamelist couldn't be read (then nothing else is set).</param>
public sealed record GamelistPlan(
    string SystemId,
    string File,
    int Entries,
    int InLibrary,
    int NotInLibrary,
    IReadOnlyList<GamelistGame> Games,
    int Hidden,
    string? Error = null)
{
    public int WithMetadata => Games.Count(g => g.HasMetadata);

    public int Favourites => Games.Count(g => g.Favourite);

    public int Matches => Games.Count(g => g.ScreenScraperId is not null);

    public int Files => Games.Sum(g => g.Media.Count);

    /// <summary>Files to copy, per media kind.</summary>
    public IReadOnlyDictionary<string, int> FilesByKind() =>
        Games.SelectMany(g => g.Media).GroupBy(m => m.Kind, StringComparer.Ordinal).ToDictionary(g => g.Key, g => g.Count(), StringComparer.Ordinal);
}

/// <summary>What an import did.</summary>
/// <param name="MetadataGames">Games given a title or metadata.</param>
/// <param name="Copied">Files copied into the media folder, per kind.</param>
/// <param name="AlreadyThere">Files skipped because the game had a file of that kind by then.</param>
/// <param name="Missing">Files the gamelist names that aren't there.</param>
/// <param name="Unreadable">Files that aren't an image (or for a video, an MP4) the launcher can read, or couldn't be copied.</param>
public sealed record GamelistImportResult(
    int MetadataGames,
    int Favourites,
    int Matches,
    IReadOnlyDictionary<string, int> Copied,
    int AlreadyThere,
    int Missing,
    int Unreadable)
{
    public int CopiedTotal => Copied.Values.Sum();
}

/// <summary>
/// Imports a system's ES-DE <c>gamelist.xml</c> (2026-10-04): its games' titles and metadata as the user's own edits
/// (userdata.db, so they survive a rebuild and scraping never replaces them), its favourites, its ScreenScraper ids as
/// matches, and its media <b>copied</b> (never moved) into the media folder as each game's own files
/// (<c>media/&lt;system&gt;/&lt;kind&gt;/&lt;rel path&gt;.&lt;ext&gt;</c>, A4): <c>thumbnail</c> the cover, <c>image</c> the
/// screenshot, <c>marquee</c> the logo, <c>video</c> the video. Only gaps are filled: a value the game has, scraped or
/// the user's, and a media kind it has a file for, are kept, so importing again only finishes what was left. Hidden
/// flags aren't imported. File and DB work is on the thread pool and the library's writer: never call it from the
/// main thread and wait.
/// </summary>
public sealed class GamelistImportService(LibraryService library, IPlatformPaths paths, DerivativeService? derivatives, TimeProvider? clock = null)
{
    public const string FileName = "gamelist.xml";

    /// <summary>The media index is refreshed after this many files are copied, so the grid fills in as it goes.</summary>
    private const int RefreshEvery = 100;

    private const int WriteBatch = 200;

    private readonly LibraryService _library = library ?? throw new ArgumentNullException(nameof(library));
    private readonly IPlatformPaths _paths = paths ?? throw new ArgumentNullException(nameof(paths));
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;

    /// <summary>
    /// The system's gamelists that exist: one in each of its ROM folders (ES-DE's "legacy" place, and Batocera's,
    /// RetroBat's), then ES-DE's own, <c>~/ES-DE/gamelists/&lt;id or alias&gt;/</c>. Checks files, so the thread pool.
    /// </summary>
    public async Task<IReadOnlyList<string>> FindAsync(string systemId, CancellationToken cancellationToken)
    {
        var system = _library.Config.FindSystem(systemId) ?? throw new ArgumentException($"'{systemId}' isn't an enabled system.", nameof(systemId));
        var scanned = await _library.ReadAsync(c => GamelistStore.RomDirs(c, systemId), cancellationToken).ConfigureAwait(false);
        return await Task.Run<IReadOnlyList<string>>(() =>
        {
            var candidates = new List<string>();
            foreach (var dir in scanned.Concat(system.RomDirs))
            {
                candidates.Add(Path.Combine(dir, FileName));
            }

            foreach (var id in system.Aliases.Prepend(system.Id))
            {
                candidates.Add(Path.Combine(_paths.HomeDir, "ES-DE", "gamelists", id, FileName));
            }

            var found = new List<string>();
            foreach (var candidate in candidates)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var full = Path.GetFullPath(candidate);
                if (!found.Exists(f => GamelistPaths.SameFolder(f, full)) && File.Exists(full))
                {
                    found.Add(full);
                }
            }

            return found;
        }, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Reads the gamelist and works out what importing it would do, against the library as it is (the system's games
    /// must have been scanned). Never throws for a bad file: <see cref="GamelistPlan.Error"/> says why.
    /// </summary>
    public async Task<GamelistPlan> PlanAsync(string systemId, string file, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        ArgumentNullException.ThrowIfNull(file);
        var read = await Task.Run(() =>
        {
            try
            {
                using var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.Read, 65536);
                return GamelistReader.Read(stream, Path.GetFileName(file));
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                return new GamelistReadResult([], $"{file} couldn't be read: {e.Message}");
            }
        }, cancellationToken).ConfigureAwait(false);
        if (read.Error is not null)
        {
            return new GamelistPlan(systemId, file, 0, 0, 0, [], 0, read.Error);
        }

        var (romDirs, games) = await _library.ReadAsync(
            c => (GamelistStore.RomDirs(c, systemId), GamelistStore.Games(c, systemId)), cancellationToken).ConfigureAwait(false);
        return Plan(systemId, file, read.Games, romDirs, games, _paths.HomeDir);
    }

    internal static GamelistPlan Plan(string systemId, string file, IReadOnlyList<GamelistEntry> entries, IReadOnlyList<string> romDirs,
        IReadOnlyDictionary<string, GamelistLibraryGame> games, string homeDir)
    {
        // Paths are relative to the ROM folder the gamelist is in; one kept elsewhere (ES-DE's gamelists folder) is
        // tried against each of the system's ROM folders, in order.
        var gamelistDir = Path.GetDirectoryName(Path.GetFullPath(file))!;
        var inRomDir = romDirs.FirstOrDefault(d => GamelistPaths.SameFolder(d, gamelistDir));
        IReadOnlyList<string> bases = inRomDir is not null ? [inRomDir] : romDirs.Count > 0 ? romDirs : [gamelistDir];

        var planned = new List<GamelistGame>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        int inLibrary = 0, notInLibrary = 0, hidden = 0;
        foreach (var entry in entries)
        {
            if (entry.Hidden)
            {
                hidden++;
            }

            if (Match(entry.Path, bases, romDirs, games, homeDir) is not { } matched)
            {
                notInLibrary++;
                continue;
            }

            var (game, baseDir) = matched;

            if (!seen.Add(game.Key.PathKey))
            {
                continue;
            }

            inLibrary++;
            var values = game.Values;
            var fill = new MetadataOverride(
                values.Description is null ? entry.Description : null,
                values.ReleaseDate is null ? entry.ReleaseDate : null,
                values.Developer is null ? entry.Developer : null,
                values.Publisher is null ? entry.Publisher : null,
                values.Genre is null ? entry.Genre : null,
                values.Players is null ? entry.Players : null,
                values.Rating is null ? entry.Rating : null);

            var media = new List<GamelistCopy>();
            foreach (var named in entry.Media)
            {
                if (!game.MediaKinds.Contains(named.Kind) && !media.Exists(m => m.Kind == named.Kind)
                    && GamelistPaths.Resolve(named.Path, baseDir, homeDir) is { } source)
                {
                    media.Add(new GamelistCopy(named.Kind, source));
                }
            }

            var planGame = new GamelistGame(
                game.Key,
                game.RelPath,
                game.HasTitle ? null : TitleFor(entry.Name, game),
                fill,
                entry.Favourite && !game.IsFavourite,
                game.HasScreenScraperMatch ? null : entry.ScreenScraperId,
                media);
            if (planGame.HasMetadata || planGame.Favourite || planGame.ScreenScraperId is not null || media.Count > 0)
            {
                planned.Add(planGame);
            }
        }

        return new GamelistPlan(systemId, file, entries.Count, inLibrary, notInLibrary, planned, hidden);
    }

    /// <summary>The library's game a gamelist path names, and the folder its media paths are relative to.</summary>
    private static (GamelistLibraryGame Game, string BaseDir)? Match(string path, IReadOnlyList<string> bases, IReadOnlyList<string> romDirs,
        IReadOnlyDictionary<string, GamelistLibraryGame> games, string homeDir)
    {
        foreach (var baseDir in bases)
        {
            if (GamelistPaths.Resolve(path, baseDir, homeDir) is not { } full)
            {
                return null;
            }

            foreach (var romDir in romDirs)
            {
                if (GamelistPaths.RelPathUnder(full, romDir) is { } relPath
                    && games.TryGetValue(PathKeys.ToPathKey(relPath), out var game)
                    && GamelistPaths.SameFolder(game.RomDir, romDir))
                {
                    return (game, baseDir);
                }
            }
        }

        return null;
    }

    /// <summary>
    /// The gamelist's name as the game's title, or null when it adds nothing: an unscraped entry carries the file's
    /// own name, and the file-name title is shown anyway. A lone disc keeps its number, as a scraped title does (A4).
    /// </summary>
    private static string? TitleFor(string? name, GamelistLibraryGame game)
    {
        if (name is null)
        {
            return null;
        }

        var stem = LibraryStore.FileStemOf(game.RelPath);
        var parsed = TitleParser.Parse(stem);
        if (string.Equals(name, stem, StringComparison.OrdinalIgnoreCase) || string.Equals(name, parsed.Title, StringComparison.Ordinal))
        {
            return null;
        }

        return game.Disc is { } disc && !name.Contains("disc", StringComparison.OrdinalIgnoreCase)
            ? string.Create(CultureInfo.InvariantCulture, $"{name} (Disc {disc})")
            : name;
    }

    /// <summary>
    /// Runs a plan: the titles, metadata, favourites and matches first (so the grid's titles change at once;
    /// <paramref name="metadataSaved"/> hears which games, on the writer's thread), then each file, copied one at a
    /// time. Progress counts files. Cancelling stops between files (and during a copy), keeping what's done; importing
    /// again finishes the rest.
    /// </summary>
    public async Task<GamelistImportResult> ImportAsync(GamelistPlan plan, IProgress<JobProgress>? progress,
        Action<IReadOnlyList<GameKey>>? metadataSaved, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(plan);
        if (plan.Error is not null)
        {
            throw new ArgumentException("That gamelist couldn't be read.", nameof(plan));
        }

        var now = _clock.GetUtcNow().ToUnixTimeMilliseconds();
        int metadataGames = 0, favourites = 0, matches = 0;
        var userData = plan.Games.Where(g => g.HasMetadata || g.Favourite || g.ScreenScraperId is not null).ToList();
        for (var start = 0; start < userData.Count; start += WriteBatch)
        {
            var batch = userData.GetRange(start, Math.Min(WriteBatch, userData.Count - start));
            var (m, f, s) = await _library.WriteAsync(c =>
            {
                int metadata = 0, favourite = 0, matched = 0;
                using var transaction = c.BeginTransaction();
                foreach (var game in batch)
                {
                    if (game.HasMetadata)
                    {
                        GamelistStore.FillOverrides(c, transaction, game.Key, game.Title, game.Fill);
                        metadata++;
                    }

                    if (game.Favourite)
                    {
                        GamelistStore.AddFavourite(c, transaction, game.Key, now);
                        favourite++;
                    }

                    if (game.ScreenScraperId is { } id && GamelistStore.AddScreenScraperMatch(c, transaction, game.Key, id, now))
                    {
                        matched++;
                    }
                }

                transaction.Commit();
                return (metadata, favourite, matched);
            }, cancellationToken).ConfigureAwait(false);
            (metadataGames, favourites, matches) = (metadataGames + m, favourites + f, matches + s);
        }

        if (userData.Count > 0)
        {
            metadataSaved?.Invoke(userData.ConvertAll(g => g.Key));
        }

        var copied = new Dictionary<string, int>(StringComparer.Ordinal);
        int alreadyThere = 0, missing = 0, unreadable = 0, done = 0, unindexed = 0;
        var total = plan.Files;
        var store = new MediaStore(_library.MediaDir);

        // Derivatives bake on the derivative service's thread while the next files copy; they're waited for before the
        // copies are indexed, so the grid never finds an image it has no derivative for yet.
        var baking = new List<Task<bool>>();
        progress?.Report(new JobProgress("copy", 0, total));
        try
        {
            foreach (var game in plan.Games)
            {
                foreach (var copy in game.Media)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    var (outcome, bake) = await CopyAsync(store, plan.SystemId, game.RelPath, copy, cancellationToken).ConfigureAwait(false);
                    switch (outcome)
                    {
                        case CopyOutcome.Copied:
                            copied[copy.Kind] = copied.GetValueOrDefault(copy.Kind) + 1;
                            if (bake is not null)
                            {
                                baking.Add(bake);
                            }

                            if (++unindexed >= RefreshEvery)
                            {
                                await Task.WhenAll(baking).ConfigureAwait(false);
                                baking.Clear();
                                await _library.RefreshMediaAsync(plan.SystemId, cancellationToken).ConfigureAwait(false);
                                unindexed = 0;
                            }

                            break;
                        case CopyOutcome.AlreadyThere:
                            alreadyThere++;
                            break;
                        case CopyOutcome.Missing:
                            missing++;
                            break;
                        default:
                            unreadable++;
                            break;
                    }

                    progress?.Report(new JobProgress("copy", ++done, total));
                }
            }
        }
        finally
        {
            // What was copied is indexed, cancelled or not.
            if (unindexed > 0)
            {
                try
                {
                    await Task.WhenAll(baking).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    // Cancelled bakes are done by the next bake of missing derivatives.
                }

                await _library.RefreshMediaAsync(plan.SystemId, CancellationToken.None).ConfigureAwait(false);
            }
        }

        return new GamelistImportResult(metadataGames, favourites, matches, copied, alreadyThere, missing, unreadable);
    }

    private enum CopyOutcome
    {
        Copied,
        AlreadyThere,
        Missing,
        Unreadable,
    }

    /// <summary>
    /// Copies one file to the game's own name in the media folder, through a temporary file, never replacing one
    /// (as a scrape's download: A4). The source is only read. A copied image's derivative is queued to bake, and its
    /// task returned.
    /// </summary>
    private async Task<(CopyOutcome Outcome, Task<bool>? Bake)> CopyAsync(MediaStore store, string systemId, string relPath, GamelistCopy copy, CancellationToken cancellationToken)
    {
        if (store.HasFile(systemId, relPath, copy.Kind))
        {
            return (CopyOutcome.AlreadyThere, null);
        }

        var extension = Path.GetExtension(copy.Source).ToLowerInvariant();
        if (!MediaKinds.ExtensionsOf(copy.Kind).Contains(extension))
        {
            return (CopyOutcome.Unreadable, null);
        }

        var relative = MediaStore.RelativePathFor(systemId, relPath, copy.Kind, extension);
        var target = store.FullPath(relative);
        var temporary = target + ".import-" + Guid.NewGuid().ToString("N");
        try
        {
            if (!File.Exists(copy.Source))
            {
                return (CopyOutcome.Missing, null);
            }

            if (!Readable(copy))
            {
                return (CopyOutcome.Unreadable, null);
            }

            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            var source = new FileStream(copy.Source, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20, useAsync: true);
            await using (source.ConfigureAwait(false))
            {
                var destination = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1 << 20, useAsync: true);
                await using (destination.ConfigureAwait(false))
                {
                    await source.CopyToAsync(destination, 1 << 20, cancellationToken).ConfigureAwait(false);
                }
            }

            // Not overwriting: a file a scrape or the user put there meanwhile stays.
            File.Move(temporary, target, overwrite: false);
        }
        catch (IOException) when (File.Exists(target))
        {
            Delete(temporary);
            return (CopyOutcome.AlreadyThere, null);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            Delete(temporary);
            return (CopyOutcome.Unreadable, null);
        }
        catch
        {
            Delete(temporary);
            throw;
        }

        Task<bool>? bake = null;
        if (copy.Kind != MediaKinds.Video && derivatives is not null)
        {
            var info = new FileInfo(target);
            bake = derivatives.BakeAsync(relative, info.Length, new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds(), cancellationToken);
        }

        return (CopyOutcome.Copied, bake);
    }

    /// <summary>An image whose header the launcher reads, or a video that's an MP4, by its first bytes.</summary>
    private static bool Readable(GamelistCopy copy)
    {
        if (copy.Kind != MediaKinds.Video)
        {
            return ImageHeaders.TryReadSize(copy.Source, out var width, out var height) && width > 0 && height > 0;
        }

        Span<byte> head = stackalloc byte[12];
        using var stream = new FileStream(copy.Source, FileMode.Open, FileAccess.Read, FileShare.Read, 1);
        return stream.ReadAtLeast(head, head.Length, throwOnEndOfStream: false) == head.Length && VideoFormats.Sniff(head) is not null;
    }

    private static void Delete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // A leftover temporary file is never indexed (its extension isn't a media one).
        }
    }
}
