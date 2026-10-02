using System.IO.Enumeration;
using Launcher.Core.Config;
using Launcher.Core.Scanning;

namespace Launcher.Core.Media;

/// <summary>
/// One file of the user's own art, <c>ConfigDir/media/&lt;system&gt;/&lt;kind&gt;/&lt;rel path&gt;.&lt;ext&gt;</c>, or a
/// per-game model, <c>ConfigDir/models/games/&lt;system&gt;/&lt;rel path&gt;.glb</c> (kind <c>model</c>, M6).
/// </summary>
/// <param name="Path">Relative to ConfigDir, '/'-separated, as stored in <c>media.path</c>.</param>
/// <param name="MatchKey">
/// The path under the kind's folder without the file's extension, as a <c>path_key</c>. It matches a game whose
/// <c>path_key</c> is the same, or is the same without the ROM's extension.
/// </param>
/// <param name="Width">An image's width from its header; null for a model.</param>
public sealed record UserMediaFile(string Kind, string Path, string MatchKey, long SizeBytes, long MtimeMs, int? Width, int? Height);

/// <summary>What the previous scan knew about a file, so an unchanged one isn't opened again.</summary>
public sealed record UserMediaEntry(long SizeBytes, long MtimeMs, int Width, int Height);

/// <summary>A system's user art, as found on disk.</summary>
/// <param name="HeadersRead">Files whose header was read because they're new or changed.</param>
public sealed record UserMediaScan(IReadOnlyList<UserMediaFile> Files, IReadOnlyList<Diagnostic> Diagnostics, int HeadersRead);

/// <summary>
/// Finds the user's own art and per-game models (A4, A7), so the grid never probes for them. Does file I/O: never
/// call it on the main thread. It holds no state, so systems can be scanned in parallel.
/// </summary>
public static class UserMedia
{
    public const string FolderName = "media";

    /// <summary>Per-game models: <c>ConfigDir/models/games/&lt;system&gt;/</c>.</summary>
    public const string ModelsFolderName = "models/games";

    /// <param name="cache">The previous scan's entries, by <see cref="UserMediaFile.Path"/>.</param>
    public static UserMediaScan Scan(
        string configDir,
        string systemId,
        IReadOnlyDictionary<string, UserMediaEntry>? cache,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(configDir);
        ArgumentNullException.ThrowIfNull(systemId);
        var files = new List<UserMediaFile>();
        var diagnostics = new List<Diagnostic>();
        var headersRead = 0;
        ScanModels(configDir, systemId, files, diagnostics, cancellationToken);
        var systemDir = System.IO.Path.Combine(configDir, FolderName, systemId);
        if (!Directory.Exists(systemDir))
        {
            return new UserMediaScan(files, diagnostics, 0);
        }

        foreach (var kind in MediaKinds.Images)
        {
            var kindDir = System.IO.Path.Combine(systemDir, kind);
            if (!Directory.Exists(kindDir))
            {
                continue;
            }

            var found = List(kindDir, IsImage, diagnostics);
            found.Sort(static (a, b) => string.CompareOrdinal(a.RelPath, b.RelPath));
            var keys = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var (relPath, size, mtime) in found)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var stored = $"{FolderName}/{systemId}/{kind}/{relPath}";
                var matchKey = PathKeys.ToPathKey(relPath[..^System.IO.Path.GetExtension(relPath).Length]);
                if (keys.TryGetValue(matchKey, out var first))
                {
                    diagnostics.Add(new Diagnostic(Severity.Warning, System.IO.Path.Combine(configDir, stored), 0, 0, string.Empty,
                        $"is the same {kind} as '{first}', which is used instead"));
                    continue;
                }

                int width, height;
                if (cache is not null && cache.TryGetValue(stored, out var known) && known.SizeBytes == size && known.MtimeMs == mtime)
                {
                    (width, height) = (known.Width, known.Height);
                }
                else
                {
                    headersRead++;
                    if (!ImageHeaders.TryReadSize(System.IO.Path.Combine(configDir, stored), out width, out height))
                    {
                        diagnostics.Add(new Diagnostic(Severity.Warning, System.IO.Path.Combine(configDir, stored), 0, 0, string.Empty,
                            "isn't a PNG, JPEG or WebP image the launcher can read, so it's ignored"));
                        continue;
                    }
                }

                keys.Add(matchKey, relPath);
                files.Add(new UserMediaFile(kind, stored, matchKey, size, mtime, width, height));
            }
        }

        return new UserMediaScan(files, diagnostics, headersRead);
    }

    /// <summary>A model is matched like art; there's no header to read (the app inspects it when it loads it).</summary>
    private static void ScanModels(string configDir, string systemId, List<UserMediaFile> files, List<Diagnostic> diagnostics, CancellationToken cancellationToken)
    {
        var modelsDir = System.IO.Path.Combine(configDir, ModelsFolderName.Replace('/', System.IO.Path.DirectorySeparatorChar), systemId);
        if (!Directory.Exists(modelsDir))
        {
            return;
        }

        var found = List(modelsDir, static extension => extension.Equals(".glb", StringComparison.OrdinalIgnoreCase), diagnostics);
        found.Sort(static (a, b) => string.CompareOrdinal(a.RelPath, b.RelPath));
        foreach (var (relPath, size, mtime) in found)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var matchKey = PathKeys.ToPathKey(relPath[..^".glb".Length]);
            files.Add(new UserMediaFile(MediaKinds.Model, $"{ModelsFolderName}/{systemId}/{relPath}", matchKey, size, mtime, null, null));
        }
    }

    private delegate bool ExtensionFilter(ReadOnlySpan<char> extension);

    private static List<(string RelPath, long Size, long MtimeMs)> List(string root, ExtensionFilter include, List<Diagnostic> diagnostics)
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
            ShouldIncludePredicate = (ref FileSystemEntry entry) => !entry.IsDirectory && include(System.IO.Path.GetExtension(entry.FileName)),
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

    private static bool IsImage(ReadOnlySpan<char> extension)
    {
        foreach (var image in MediaKinds.ImageExtensions)
        {
            if (extension.Equals(image, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }
}
