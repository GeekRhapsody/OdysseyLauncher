using System.IO.Enumeration;
using Launcher.Core.Config;

namespace Launcher.Core.Scanning;

/// <summary>A file the scanner kept, before multi-file grouping decides whether it's a game.</summary>
/// <param name="DirIndex">Index into <see cref="SystemScan.RomDirs"/>.</param>
/// <param name="CreatedMs">The file's creation time (unix ms): when it arrived in the folder, for sorting games by "added". 0 when unknown.</param>
public sealed record ScannedFile(int DirIndex, string RelPath, string PathKey, long SizeBytes, long MtimeMs, long CreatedMs = 0);

/// <summary>A parsed <c>.m3u</c>, <c>.cue</c> or <c>.gdi</c>, cached so an unchanged one isn't read again.</summary>
/// <param name="Refs">The <c>path_key</c>s it references, in order.</param>
public sealed record PlaylistEntry(string PathKey, long SizeBytes, long MtimeMs, IReadOnlyList<string> Refs);

/// <summary>What one system's ROM folders hold now.</summary>
/// <param name="RomDirs">The folders that were scanned, in priority order.</param>
/// <param name="Games">Visible games, sorted by folder then <c>rel_path</c>.</param>
/// <param name="Playlists">Every playlist that was found, including hidden ones, for the cache.</param>
public sealed record SystemScan(
    string SystemId,
    IReadOnlyList<string> RomDirs,
    IReadOnlyList<ScannedFile> Games,
    IReadOnlyList<PlaylistEntry> Playlists,
    IReadOnlyList<Diagnostic> Diagnostics,
    int FilesSeen,
    int PlaylistsRead);

/// <summary>
/// Walks a system's ROM folders by file name only: extensions, recursion and excludes from config.
/// Multi-file games are grouped: files referenced by an <c>.m3u</c>, <c>.cue</c> or <c>.gdi</c> are hidden.
/// Does file I/O: never call it on the main thread. It holds no state, so systems can be scanned in parallel.
/// </summary>
public sealed class RomScanner
{
    private const int MaxDepth = 32;

    /// <summary>
    /// Directory-listing buffer. .NET's default (4 KB) holds about 20 entries at ROM-name lengths, and on an
    /// SMB share every refill is a network round trip. 256 KB halved a listing of 56,000 entries on a NAS
    /// (13.3 s to 5.5 s; docs/perf/m2-core.md) and costs nothing locally.
    /// </summary>
    public const int ListingBufferBytes = 256 * 1024;

    /// <param name="playlistCache">Playlists from the previous scan, by <c>path_key</c>. An entry is reused when size and mtime match.</param>
    public SystemScan Scan(
        SystemConfig system,
        IReadOnlyDictionary<string, PlaylistEntry>? playlistCache,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(system);
        var diagnostics = new List<Diagnostic>();
        var dirs = ResolveDirs(system, diagnostics);
        var excludes = system.Exclude.Select(GlobPattern.Create).ToArray();

        var kept = new Dictionary<string, ScannedFile>(StringComparer.Ordinal);
        var ordered = new List<ScannedFile>();
        var filesSeen = 0;
        for (var d = 0; d < dirs.Count; d++)
        {
            var files = Enumerate(dirs[d], d, system, excludes, diagnostics);
            files.Sort(static (a, b) => string.CompareOrdinal(a.RelPath, b.RelPath));
            filesSeen += files.Count;
            foreach (var file in files)
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (kept.TryGetValue(file.PathKey, out var first))
                {
                    diagnostics.Add(new Diagnostic(
                        Severity.Warning,
                        Path.Combine(dirs[d], file.RelPath),
                        0,
                        0,
                        string.Empty,
                        $"has the same path, ignoring case, as '{Path.Combine(dirs[first.DirIndex], first.RelPath)}', which is kept"));
                    continue;
                }

                kept.Add(file.PathKey, file);
                ordered.Add(file);
            }
        }

        var playlists = new List<PlaylistEntry>();
        var hidden = new HashSet<string>(StringComparer.Ordinal);
        var playlistsRead = 0;
        foreach (var file in ordered)
        {
            if (!PlaylistParser.IsPlaylist(Path.GetExtension(file.RelPath)))
            {
                continue;
            }

            cancellationToken.ThrowIfCancellationRequested();
            PlaylistEntry entry;
            if (playlistCache is not null
                && playlistCache.TryGetValue(file.PathKey, out var cached)
                && cached.SizeBytes == file.SizeBytes
                && cached.MtimeMs == file.MtimeMs)
            {
                entry = cached;
            }
            else
            {
                entry = ReadPlaylist(Path.Combine(dirs[file.DirIndex], file.RelPath), file, diagnostics);
                playlistsRead++;
            }

            playlists.Add(entry);
            foreach (var reference in entry.Refs)
            {
                if (reference != file.PathKey)
                {
                    hidden.Add(reference);
                }
            }
        }

        var games = hidden.Count == 0 ? ordered : ordered.Where(file => !hidden.Contains(file.PathKey)).ToList();
        return new SystemScan(system.Id, dirs, games, playlists, diagnostics, filesSeen, playlistsRead);
    }

    private static List<string> ResolveDirs(SystemConfig system, List<Diagnostic> diagnostics)
    {
        var dirs = new List<string>();
        if (system.RomDirSource == RomDirSource.Default)
        {
            // {rom_root}/<id>, then each alias: the first that exists.
            var first = system.RomDirs.FirstOrDefault(Directory.Exists);
            if (first is not null)
            {
                dirs.Add(Path.TrimEndingDirectorySeparator(first));
            }

            return dirs;
        }

        foreach (var dir in system.RomDirs)
        {
            if (Directory.Exists(dir))
            {
                dirs.Add(Path.TrimEndingDirectorySeparator(dir));
            }
            else
            {
                diagnostics.Add(new Diagnostic(
                    Severity.Warning, dir, 0, 0, $"systems.{system.Id}.rom_dirs", "this ROM folder doesn't exist, so it was skipped"));
            }
        }

        return dirs;
    }

    private static List<ScannedFile> Enumerate(
        string root, int dirIndex, SystemConfig system, GlobPattern[] excludes, List<Diagnostic> diagnostics)
    {
        var extensions = system.Extensions;
        var options = new EnumerationOptions
        {
            RecurseSubdirectories = system.Recursive,
            IgnoreInaccessible = true,
            AttributesToSkip = FileAttributes.System,
            MaxRecursionDepth = MaxDepth,
            ReturnSpecialDirectories = false,
            BufferSize = ListingBufferBytes,
        };

        var enumerable = new FileSystemEnumerable<ScannedFile>(
            root,
            (ref FileSystemEntry entry) =>
            {
                var relPath = PathKeys.ToRelPath(RelativePath(ref entry));
                return new ScannedFile(
                    dirIndex,
                    relPath,
                    PathKeys.ToPathKey(relPath),
                    entry.Length,
                    entry.LastWriteTimeUtc.ToUnixTimeMilliseconds(),
                    CreatedMs(ref entry));
            },
            options)
        {
            ShouldIncludePredicate = (ref FileSystemEntry entry) =>
                !entry.IsDirectory
                && HasExtension(Path.GetExtension(entry.FileName), extensions)
                && (excludes.Length == 0 || !IsExcluded(RelativePath(ref entry), excludes)),
            ShouldRecursePredicate = (ref FileSystemEntry entry) =>
                excludes.Length == 0 || !IsExcluded(RelativePath(ref entry).Replace('\\', '/'), excludes),
        };

        try
        {
            return [.. enumerable];
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            diagnostics.Add(new Diagnostic(Severity.Warning, root, 0, 0, string.Empty, $"couldn't be read: {e.Message}"));
            return [];
        }
    }

    /// <summary>
    /// The entry's creation time, which Windows' folder listing carries (no extra call per file). 0 when the file
    /// system reports none (the epoch, or before it).
    /// </summary>
    private static long CreatedMs(ref FileSystemEntry entry)
    {
        var ms = entry.CreationTimeUtc.ToUnixTimeMilliseconds();
        return ms > 0 ? ms : 0;
    }

    private static string RelativePath(ref FileSystemEntry entry)
    {
        var directory = entry.Directory;
        var root = entry.RootDirectory;
        return directory.Length > root.Length
            ? string.Concat(directory[(root.Length + 1)..], "/", entry.FileName)
            : entry.FileName.ToString();
    }

    private static bool HasExtension(ReadOnlySpan<char> extension, IReadOnlyList<string> extensions)
    {
        for (var i = 0; i < extensions.Count; i++)
        {
            if (extension.Equals(extensions[i], StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }

    private static bool IsExcluded(string relPath, GlobPattern[] excludes)
    {
        var path = relPath.Replace('\\', '/');
        foreach (var exclude in excludes)
        {
            if (exclude.IsMatch(path))
            {
                return true;
            }
        }

        return false;
    }

    private static PlaylistEntry ReadPlaylist(string fullPath, ScannedFile file, List<Diagnostic> diagnostics)
    {
        if (file.SizeBytes > PlaylistParser.MaxBytes)
        {
            diagnostics.Add(new Diagnostic(Severity.Warning, fullPath, 0, 0, string.Empty,
                $"is over {PlaylistParser.MaxBytes / 1024} KB, so it wasn't read as a playlist and the files it lists aren't hidden"));
            return new PlaylistEntry(file.PathKey, file.SizeBytes, file.MtimeMs, []);
        }

        string text;
        try
        {
            text = PlaylistParser.Decode(File.ReadAllBytes(fullPath));
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            diagnostics.Add(new Diagnostic(Severity.Warning, fullPath, 0, 0, string.Empty, $"couldn't be read: {e.Message}"));
            return new PlaylistEntry(file.PathKey, file.SizeBytes, file.MtimeMs, []);
        }

        var refs = new List<string>();
        foreach (var reference in PlaylistParser.Parse(Path.GetExtension(file.RelPath), text))
        {
            if (PathKeys.ResolveReference(file.RelPath, reference) is { } key && !refs.Contains(key))
            {
                refs.Add(key);
            }
        }

        return new PlaylistEntry(file.PathKey, file.SizeBytes, file.MtimeMs, refs);
    }
}
