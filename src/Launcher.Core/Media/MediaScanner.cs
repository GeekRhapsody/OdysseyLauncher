using System.IO.Enumeration;
using Launcher.Core.Config;
using Launcher.Core.Scanning;

namespace Launcher.Core.Media;

/// <summary>
/// One file in the media folder, <c>DataDir/media/&lt;system&gt;/&lt;kind&gt;/&lt;rel path&gt;.&lt;ext&gt;</c>: an image,
/// a video (kind <c>video</c>) or a per-game model (kind <c>model</c>), scraped or the user's own alike.
/// </summary>
/// <param name="Path">Relative to DataDir, '/'-separated, as stored in <c>media.path</c>.</param>
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
    /// <summary>The media folder, under DataDir.</summary>
    public const string FolderName = "media";

    /// <param name="cache">The previous scan's images, by <see cref="MediaFile.Path"/>.</param>
    public static MediaScan Scan(
        string dataDir,
        string systemId,
        IReadOnlyDictionary<string, MediaEntry>? cache,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(dataDir);
        ArgumentNullException.ThrowIfNull(systemId);
        var files = new List<MediaFile>();
        var diagnostics = new List<Diagnostic>();
        var headersRead = 0;
        var systemDir = System.IO.Path.Combine(dataDir, FolderName, systemId);
        if (!Directory.Exists(systemDir))
        {
            return new MediaScan(files, diagnostics, 0);
        }

        foreach (var kind in MediaKinds.All)
        {
            var kindDir = System.IO.Path.Combine(systemDir, kind);
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
                var stored = $"{FolderName}/{systemId}/{kind}/{relPath}";
                var matchKey = PathKeys.ToPathKey(relPath[..^System.IO.Path.GetExtension(relPath).Length]);
                if (keys.TryGetValue(matchKey, out var first))
                {
                    diagnostics.Add(new Diagnostic(Severity.Warning, System.IO.Path.Combine(dataDir, stored), 0, 0, string.Empty,
                        $"is the same {kind} as '{first}', which is used instead"));
                    continue;
                }

                // Only an image's header is read; a model is inspected when the app loads it, and nothing plays a video yet.
                int? width = null, height = null;
                if (image)
                {
                    if (cache is not null && cache.TryGetValue(stored, out var known) && known.SizeBytes == size && known.MtimeMs == mtime)
                    {
                        (width, height) = (known.Width, known.Height);
                    }
                    else
                    {
                        headersRead++;
                        if (!ImageHeaders.TryReadSize(System.IO.Path.Combine(dataDir, stored), out var w, out var h))
                        {
                            diagnostics.Add(new Diagnostic(Severity.Warning, System.IO.Path.Combine(dataDir, stored), 0, 0, string.Empty,
                                "isn't a PNG, JPEG or WebP image the launcher can read, so it's ignored"));
                            continue;
                        }

                        (width, height) = (w, h);
                    }
                }

                keys.Add(matchKey, relPath);
                files.Add(new MediaFile(kind, stored, matchKey, size, mtime, width, height));
            }
        }

        return new MediaScan(files, diagnostics, headersRead);
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
