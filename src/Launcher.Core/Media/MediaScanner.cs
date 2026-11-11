using System.IO.Enumeration;
using Launcher.Core.Config;
using Launcher.Core.Scanning;

namespace Launcher.Core.Media;

/// <summary>
/// One file in the media folder, <c>&lt;media folder&gt;/&lt;system&gt;/&lt;folder&gt;/&lt;name&gt;.&lt;ext&gt;</c> (the folder
/// <see cref="MediaKinds.FolderOf"/>): an image, a video (kind <c>video</c>), a manual (kind <c>manual</c>, a PDF) or
/// a per-game model (kind <c>model</c>), scraped or the user's own alike.
/// </summary>
/// <param name="Path">'/'-separated, as stored in <c>media.path</c>: <c>media/&lt;system&gt;/...</c>, <c>media</c> standing for the media folder (<see cref="MediaFolder"/>).</param>
/// <param name="MatchKey">
/// The path under the kind's folder without the file's extension, as a <c>path_key</c>. It matches a game whose
/// <c>path_key</c> is the same, or is the same without the ROM's extension.
/// </param>
/// <param name="Width">An image's width from its header; null for a video or a model.</param>
public sealed record MediaFile(string Kind, string Path, string MatchKey, long SizeBytes, long MtimeMs, int? Width, int? Height);

/// <summary>What the previous scan knew about an image, so an unchanged one isn't opened again.</summary>
public sealed record MediaEntry(long SizeBytes, long MtimeMs, int Width, int Height);

/// <summary>A system's media, as found on disk.</summary>
/// <param name="HeadersRead">Images whose header was read because they're new or changed.</param>
public sealed record MediaScan(IReadOnlyList<MediaFile> Files, IReadOnlyList<Diagnostic> Diagnostics, int HeadersRead);

/// <summary>
/// Indexes the media folder (A4), so the grid never probes for files: scraping writes there, the user's own art and
/// models go there, and whatever is there is the game's media, wherever it came from. Does file I/O: never call it
/// on the main thread. It holds no state, so systems can be scanned in parallel.
/// </summary>
public static class MediaScanner
{
    /// <summary>The first part of every stored path, standing for the media folder (<see cref="MediaFolder.Name"/>).</summary>
    public const string FolderName = MediaFolder.Name;

    /// <param name="mediaDir">The media folder (<see cref="MediaFolder.Of"/>).</param>
    /// <param name="cache">The previous scan's images, by <see cref="MediaFile.Path"/>.</param>
    /// <param name="gameKeys">
    /// The system's games' <c>path_key</c>s: only files one of them would match are indexed, and an image's header is
    /// read only then, so a media folder shared with ES-DE (media for games the library doesn't have, on a share) costs
    /// a listing, not a read per file. Empty: nothing is listed. Null: every file is indexed.
    /// </param>
    public static MediaScan Scan(
        string mediaDir,
        string systemId,
        IReadOnlyDictionary<string, MediaEntry>? cache,
        IReadOnlyCollection<string>? gameKeys,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(mediaDir);
        ArgumentNullException.ThrowIfNull(systemId);
        var files = new List<MediaFile>();
        var diagnostics = new List<Diagnostic>();
        var headersRead = 0;
        if (gameKeys is { Count: 0 })
        {
            return new MediaScan(files, diagnostics, 0);
        }

        var systemDir = System.IO.Path.Combine(mediaDir, systemId);
        if (!Directory.Exists(systemDir))
        {
            return new MediaScan(files, diagnostics, 0);
        }

        var wanted = gameKeys is null ? null : MatchKeys(gameKeys);

        foreach (var kind in MediaKinds.All)
        {
            var folder = MediaKinds.FolderOf(kind);
            var kindDir = System.IO.Path.Combine(systemDir, folder);
            if (!Directory.Exists(kindDir))
            {
                continue;
            }

            var image = MediaKinds.Images.Contains(kind);
            var extensions = MediaKinds.ExtensionsOf(kind);
            var found = List(kindDir, extensions, diagnostics);
            found.Sort(static (a, b) => string.CompareOrdinal(a.RelPath, b.RelPath));
            var keys = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var (relPath, size, mtime) in found)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var matchKey = PathKeys.ToPathKey(relPath[..^System.IO.Path.GetExtension(relPath).Length]);
                if (wanted is not null && !wanted.Contains(matchKey))
                {
                    continue;
                }

                var stored = $"{FolderName}/{systemId}/{folder}/{relPath}";
                if (keys.TryGetValue(matchKey, out var first))
                {
                    diagnostics.Add(new Diagnostic(Severity.Warning, MediaFolder.FullPath(mediaDir, stored), 0, 0, string.Empty,
                        $"is the same {kind} as '{first}', which is used instead"));
                    continue;
                }

                // Only an image's header is read; a model is inspected when the app loads it, and a video or a manual when it's opened.
                int? width = null, height = null;
                if (image)
                {
                    if (!TryReadSize(mediaDir, stored, size, mtime, cache, out var w, out var h, ref headersRead))
                    {
                        diagnostics.Add(new Diagnostic(Severity.Warning, MediaFolder.FullPath(mediaDir, stored), 0, 0, string.Empty,
                            "isn't a PNG, JPEG or WebP image the launcher can read, so it's ignored"));
                        continue;
                    }

                    (width, height) = (w, h);
                }

                keys.Add(matchKey, relPath);
                files.Add(new MediaFile(kind, stored, matchKey, size, mtime, width, height));
            }
        }

        return new MediaScan(files, diagnostics, headersRead);
    }

    /// <summary>
    /// The files of one <paramref name="kind"/> that could be these games' (named after a game's <c>rel_path</c>, with or
    /// without the ROM's extension, in any of the kind's formats), as <see cref="Scan"/> would index them, found by
    /// asking for each name instead of listing the kind's folder: on a share, a big system's listing can take seconds
    /// and a few lookups take milliseconds (docs/ARCHITECTURE.md decisions log, 2026-11-11). A name is looked up as
    /// the game's <c>rel_path</c> writes it, so where file names are case-sensitive (Linux) a file whose case differs
    /// isn't found, as <see cref="MediaStore.FilesOf(string, string, string)"/> doesn't find it.
    /// </summary>
    /// <param name="relPaths">The games' <c>rel_path</c>s.</param>
    /// <param name="cache">The games' indexed images of the kind, by <see cref="MediaFile.Path"/>.</param>
    public static IReadOnlyList<MediaFile> Probe(
        string mediaDir, string systemId, string kind, IEnumerable<string> relPaths, IReadOnlyDictionary<string, MediaEntry>? cache)
    {
        ArgumentNullException.ThrowIfNull(relPaths);
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var relPath in relPaths)
        {
            names.Add(relPath);
            names.Add(MediaStore.NameOf(relPath));
        }

        var candidates = new List<string>();
        foreach (var extension in MediaKinds.ExtensionsOf(kind))
        {
            foreach (var name in names)
            {
                candidates.Add(name + extension);
            }
        }

        // In the order a scan lists them, so the same file wins where two share a match key.
        candidates.Sort(string.CompareOrdinal);
        var folder = MediaKinds.FolderOf(kind);
        var image = MediaKinds.Images.Contains(kind);
        var found = new HashSet<string>(StringComparer.Ordinal);
        var files = new List<MediaFile>();
        var headersRead = 0;
        foreach (var relPath in candidates)
        {
            var matchKey = PathKeys.ToPathKey(relPath[..^System.IO.Path.GetExtension(relPath).Length]);
            var stored = $"{FolderName}/{systemId}/{folder}/{relPath}";
            var info = new FileInfo(MediaFolder.FullPath(mediaDir, stored));
            if (found.Contains(matchKey) || !info.Exists || (info.Attributes & (FileAttributes.System | FileAttributes.Hidden)) != 0)
            {
                continue;
            }

            var mtime = new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds();
            int? width = null, height = null;
            if (image)
            {
                if (!TryReadSize(mediaDir, stored, info.Length, mtime, cache, out var w, out var h, ref headersRead))
                {
                    continue;
                }

                (width, height) = (w, h);
            }

            found.Add(matchKey);
            files.Add(new MediaFile(kind, stored, matchKey, info.Length, mtime, width, height));
        }

        return files;
    }

    /// <summary>
    /// An image's size: the cache's when its size and time are the ones indexed, else from its header (counted in
    /// <paramref name="headersRead"/>). False if the header can't be read.
    /// </summary>
    private static bool TryReadSize(
        string mediaDir, string stored, long size, long mtime, IReadOnlyDictionary<string, MediaEntry>? cache,
        out int width, out int height, ref int headersRead)
    {
        if (cache is not null && cache.TryGetValue(stored, out var known) && known.SizeBytes == size && known.MtimeMs == mtime)
        {
            (width, height) = (known.Width, known.Height);
            return true;
        }

        headersRead++;
        return ImageHeaders.TryReadSize(MediaFolder.FullPath(mediaDir, stored), out width, out height);
    }

    /// <summary>
    /// The match keys a file may have to belong to one of the games: each <c>path_key</c>, and each one without the ROM's
    /// extension (as <c>LibraryStore</c> matches them, and <see cref="MediaStore.NameOf"/> names them).
    /// </summary>
    private static HashSet<string> MatchKeys(IReadOnlyCollection<string> gameKeys)
    {
        var keys = new HashSet<string>(gameKeys.Count * 2, StringComparer.Ordinal);
        foreach (var key in gameKeys)
        {
            keys.Add(key);
            keys.Add(MediaStore.NameOf(key));
        }

        return keys;
    }

    private static List<(string RelPath, long Size, long MtimeMs)> List(string root, IReadOnlyList<string> extensions, List<Diagnostic> diagnostics)
    {
        var options = new EnumerationOptions
        {
            RecurseSubdirectories = true,
            IgnoreInaccessible = true,
            AttributesToSkip = FileAttributes.System | FileAttributes.Hidden,
            MaxRecursionDepth = 32,
            ReturnSpecialDirectories = false,
            BufferSize = RomScanner.ListingBufferBytes,
        };

        var enumerable = new FileSystemEnumerable<(string, long, long)>(
            root,
            (ref FileSystemEntry entry) =>
            {
                var directory = entry.Directory;
                var relPath = directory.Length > entry.RootDirectory.Length
                    ? string.Concat(directory[(entry.RootDirectory.Length + 1)..], "/", entry.FileName)
                    : entry.FileName.ToString();
                return (PathKeys.ToRelPath(relPath), entry.Length, entry.LastWriteTimeUtc.ToUnixTimeMilliseconds());
            },
            options)
        {
            ShouldIncludePredicate = (ref FileSystemEntry entry) => !entry.IsDirectory && Matches(System.IO.Path.GetExtension(entry.FileName), extensions),
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

    private static bool Matches(ReadOnlySpan<char> extension, IReadOnlyList<string> extensions)
    {
        foreach (var wanted in extensions)
        {
            if (extension.Equals(wanted, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }
}
