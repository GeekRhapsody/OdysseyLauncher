using Launcher.Core.Scanning;

namespace Launcher.Core.Library;

/// <summary>One of the files deleting a game deletes.</summary>
/// <param name="RelPath">Relative to the game's ROM folder, '/'-separated.</param>
public sealed record GameFile(string RelPath, string FullPath, long SizeBytes);

/// <summary>
/// What deleting a game would delete (2026-10-03), for the question asked first: its file and, for a playlist
/// (<c>.m3u</c>, <c>.cue</c>, <c>.gdi</c>), every file it lists, following playlists inside it (an <c>.m3u</c> of
/// <c>.cue</c> discs takes their tracks too). <see cref="LibraryService.DeleteGameAsync"/> deletes exactly these.
/// </summary>
/// <param name="Files">The game's own file first, then the files its playlists list, in their order.</param>
/// <param name="Shared">Files it lists that another game's playlist lists too, which are kept.</param>
/// <param name="Missing">Files it lists that aren't on disk.</param>
public sealed record GameDeletePlan(
    GameKey Game,
    string Title,
    string RomDir,
    IReadOnlyList<GameFile> Files,
    IReadOnlyList<string> Shared,
    IReadOnlyList<string> Missing)
{
    public long TotalBytes => Files.Sum(f => f.SizeBytes);

    /// <summary>The game's file is a playlist (whether or not the files it lists are still there).</summary>
    public bool IsPlaylist => PlaylistParser.IsPlaylist(Path.GetExtension(Files[0].RelPath));
}

/// <summary>A file that couldn't be deleted, and why.</summary>
public sealed record GameFileFailure(string RelPath, string Message);

/// <summary>What a deletion did.</summary>
/// <param name="Deleted">The game's own file is gone, and the game left the library. False: nothing was deleted.</param>
/// <param name="FilesDeleted">Files deleted (one already gone counts).</param>
/// <param name="Failed">Files that couldn't be deleted: the game's own file (nothing else is then tried), or files its playlists list.</param>
public sealed record GameDeleteResult(bool Deleted, int FilesDeleted, long BytesFreed, IReadOnlyList<GameFileFailure> Failed);

/// <summary>
/// Finds and deletes a game's files (2026-10-03). File I/O: never on the main thread. The library's rows are
/// <see cref="LibraryService"/>'s.
/// </summary>
internal static class GameDeleter
{
    /// <param name="playlists">The system's playlists from the last scan, by <c>path_key</c>: a file another game's playlist lists is kept.</param>
    public static GameDeletePlan Plan(GameDetails game, IReadOnlyDictionary<string, PlaylistEntry> playlists)
    {
        var romDir = game.RomDir;
        var files = new List<GameFile>();
        var missing = new List<string>();

        // Every file the game is made of, through its playlists (read from disk now, as the scanner reads them).
        var found = new Dictionary<string, GameFile>(StringComparer.Ordinal);
        var children = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        var queue = new Queue<string>();
        var root = Inside(romDir, game.RelPath) is { } rootPath && new FileInfo(rootPath) is { Exists: true } rootInfo
            ? new GameFile(game.RelPath, rootPath, rootInfo.Length)
            : new GameFile(game.RelPath, game.RomPath, 0);
        found.Add(game.Key.PathKey, root);
        files.Add(root);
        queue.Enqueue(game.RelPath);
        while (queue.Count > 0)
        {
            var relPath = queue.Dequeue();
            var key = PathKeys.ToPathKey(relPath);
            var file = found[key];
            if (!PlaylistParser.IsPlaylist(Path.GetExtension(relPath)) || file.SizeBytes is 0 or > PlaylistParser.MaxBytes)
            {
                continue;
            }

            string text;
            try
            {
                text = PlaylistParser.Decode(File.ReadAllBytes(file.FullPath));
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                continue;
            }

            var listed = children[key] = [];
            foreach (var reference in PlaylistParser.Parse(Path.GetExtension(relPath), text))
            {
                if (PathKeys.ResolveRelPath(relPath, reference) is not { } target)
                {
                    continue;
                }

                var targetKey = PathKeys.ToPathKey(target);
                if (found.ContainsKey(targetKey) || missing.Contains(target, StringComparer.OrdinalIgnoreCase))
                {
                    continue;
                }

                var info = Inside(romDir, target) is { } path ? new FileInfo(path) : null;
                if (info is not { Exists: true })
                {
                    missing.Add(target);
                    continue;
                }

                var listedFile = new GameFile(target, info.FullName, info.Length);
                found.Add(targetKey, listedFile);
                files.Add(listedFile);
                listed.Add(targetKey);
                queue.Enqueue(target);
            }
        }

        // A file another game's playlist lists stays, with whatever it lists in turn.
        var kept = new HashSet<string>(StringComparer.Ordinal);
        foreach (var (playlistKey, playlist) in playlists)
        {
            if (found.ContainsKey(playlistKey))
            {
                continue;
            }

            foreach (var reference in playlist.Refs)
            {
                if (reference != game.Key.PathKey && found.ContainsKey(reference))
                {
                    kept.Add(reference);
                }
            }
        }

        var keep = new Queue<string>(kept);
        while (keep.Count > 0 && children.TryGetValue(keep.Dequeue(), out var listed))
        {
            foreach (var child in listed)
            {
                if (kept.Add(child))
                {
                    keep.Enqueue(child);
                }
            }
        }

        var shared = files.Where(f => kept.Contains(PathKeys.ToPathKey(f.RelPath))).Select(f => f.RelPath).ToList();
        files.RemoveAll(f => kept.Contains(PathKeys.ToPathKey(f.RelPath)));
        return new GameDeletePlan(game.Key, game.Title, romDir, files, shared, missing);
    }

    /// <summary>
    /// Deletes the game's own file first, and stops if it can't (so a game is never left half deleted with its
    /// file still listed); then the files it lists, and the folders that leaves empty (never the ROM folder).
    /// A read-only file is deleted too: the user asked for it.
    /// </summary>
    /// <returns>The outcome, and the <c>path_key</c>s of the files now gone.</returns>
    public static (GameDeleteResult Result, List<string> DeletedKeys) Delete(GameDeletePlan plan)
    {
        var deletedKeys = new List<string>();
        var failed = new List<GameFileFailure>();
        var deleted = 0;
        long freed = 0;
        foreach (var file in plan.Files)
        {
            try
            {
                if (Inside(plan.RomDir, file.RelPath) is null)
                {
                    throw new IOException("it isn't inside the ROM folder");
                }

                var info = new FileInfo(file.FullPath);
                if (info.Exists)
                {
                    if (info.IsReadOnly)
                    {
                        info.IsReadOnly = false;
                    }

                    info.Delete();
                    freed += file.SizeBytes;
                }

                deleted++;
                deletedKeys.Add(PathKeys.ToPathKey(file.RelPath));
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                failed.Add(new GameFileFailure(file.RelPath, e.Message));
                if (deleted == 0)
                {
                    return (new GameDeleteResult(false, 0, 0, failed), deletedKeys);
                }
            }
        }

        RemoveEmptyFolders(plan);
        return (new GameDeleteResult(true, deleted, freed, failed), deletedKeys);
    }

    /// <summary>Folders that held the deleted files and are now empty, up to the ROM folder (kept).</summary>
    private static void RemoveEmptyFolders(GameDeletePlan plan)
    {
        var romDir = Path.TrimEndingDirectorySeparator(Path.GetFullPath(plan.RomDir)) + Path.DirectorySeparatorChar;
        var folders = plan.Files.Select(f => Path.GetDirectoryName(f.FullPath)).OfType<string>().Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderByDescending(f => f.Length).ToList();
        foreach (var start in folders)
        {
            for (var folder = start; folder.StartsWith(romDir, StringComparison.OrdinalIgnoreCase); folder = Path.GetDirectoryName(folder) ?? romDir)
            {
                try
                {
                    if (!Directory.Exists(folder) || Directory.EnumerateFileSystemEntries(folder).Any())
                    {
                        break;
                    }

                    Directory.Delete(folder);
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException)
                {
                    break;
                }
            }
        }
    }

    /// <summary>The full path of <paramref name="relPath"/> under <paramref name="romDir"/>; null if it would lie outside it.</summary>
    private static string? Inside(string romDir, string relPath)
    {
        var root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(romDir)) + Path.DirectorySeparatorChar;
        var full = Path.GetFullPath(Path.Combine(root, relPath.Replace('/', Path.DirectorySeparatorChar)));
        return full.StartsWith(root, StringComparison.OrdinalIgnoreCase) && full.Length > root.Length ? full : null;
    }
}
