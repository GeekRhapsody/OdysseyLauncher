using Launcher.Core.Library;

namespace Launcher.Core.Media;

/// <summary>A media file as written: where it is, and what the <c>media</c> row records about it.</summary>
/// <param name="RelativePath">Relative to DataDir, '/'-separated, as stored in <c>media.path</c>.</param>
public sealed record StoredMedia(string RelativePath, long SizeBytes, long MtimeMs, int Width, int Height);

/// <summary>
/// Scraped media on disk (ARCHITECTURE.md A4): <c>DataDir/scraped/media/&lt;system&gt;/&lt;kind&gt;/&lt;path_key&gt;.&lt;ext&gt;</c>.
/// Paths are deterministic, and writes are atomic (a temporary file, then a replacing move), so a crash never leaves
/// a half-written image where the grid would read it. Does file I/O: never on the main thread.
/// </summary>
/// <remarks>
/// Scraped media sits under <c>scraped/</c> rather than DataDir's own <c>media/</c>: in the portable layout ConfigDir and
/// DataDir are one folder, and <c>media/</c> there is the user's own art.
/// </remarks>
public sealed class MediaStore(string dataDir)
{
    public const string ScrapedFolder = "scraped";
    public const string MediaFolder = "media";

    public string DataDir { get; } = dataDir ?? throw new ArgumentNullException(nameof(dataDir));

    /// <summary>Deterministic: <c>scraped/media/&lt;system&gt;/&lt;kind&gt;/&lt;path_key&gt;&lt;extension&gt;</c>.</summary>
    /// <param name="extension">With its dot: ".png", ".jpg" or ".webp".</param>
    public static string RelativePathFor(GameKey game, string kind, string extension)
    {
        ArgumentNullException.ThrowIfNull(kind);
        ArgumentNullException.ThrowIfNull(extension);
        return $"{ScrapedFolder}/{MediaFolder}/{game.SystemId}/{kind}/{game.PathKey}{extension}";
    }

    public string FullPath(string relativePath) =>
        Path.Combine(DataDir, relativePath.Replace('/', Path.DirectorySeparatorChar));

    /// <summary>
    /// Writes an image atomically, replacing the game's file of that kind in any other format.
    /// </summary>
    /// <exception cref="InvalidDataException">The content isn't a PNG, JPEG or WebP image.</exception>
    public async Task<StoredMedia> SaveAsync(GameKey game, string kind, ReadOnlyMemory<byte> content, CancellationToken cancellationToken)
    {
        var extension = ImageFormats.Sniff(content.Span)
            ?? throw new InvalidDataException("the download isn't a PNG, JPEG or WebP image");
        int width, height;
        using (var probe = new MemoryStream(content.ToArray(), writable: false))
        {
            if (!ImageHeaders.TryReadSize(probe, out width, out height))
            {
                throw new InvalidDataException("the image's header can't be read");
            }
        }

        var relative = RelativePathFor(game, kind, extension);
        var full = FullPath(relative);
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        var temp = full + ".tmp-" + Guid.NewGuid().ToString("N");
        try
        {
            var stream = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None, 81920, useAsync: true);
            await using (stream.ConfigureAwait(false))
            {
                await stream.WriteAsync(content, cancellationToken).ConfigureAwait(false);
            }

            File.Move(temp, full, overwrite: true);
        }
        catch
        {
            File.Delete(temp);
            throw;
        }

        DeleteOtherFormats(full, extension);
        var info = new FileInfo(full);
        return new StoredMedia(relative, info.Length, new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds(), width, height);
    }

    /// <summary>Every scraped file of the game, of every kind and format.</summary>
    public IReadOnlyList<string> FilesOf(GameKey game)
    {
        var files = new List<string>();
        var systemDir = Path.Combine(DataDir, ScrapedFolder, MediaFolder, game.SystemId);
        if (!Directory.Exists(systemDir))
        {
            return files;
        }

        foreach (var kind in MediaKinds.Images)
        {
            foreach (var extension in ImageFormats.Extensions)
            {
                var path = FullPath(RelativePathFor(game, kind, extension));
                if (File.Exists(path))
                {
                    files.Add(path);
                }
            }
        }

        return files;
    }

    private static void DeleteOtherFormats(string full, string keep)
    {
        var stem = full[..^keep.Length];
        foreach (var extension in ImageFormats.Extensions)
        {
            if (extension != keep)
            {
                File.Delete(stem + extension);
            }
        }
    }
}

/// <summary>Recognises the image formats the app decodes by their first bytes.</summary>
public static class ImageFormats
{
    /// <summary>The extensions scraped images are stored with.</summary>
    public static IReadOnlyList<string> Extensions { get; } = [".png", ".jpg", ".webp"];

    /// <summary>".png", ".jpg" or ".webp", or null for anything else (an HTML error page, "NOMEDIA", ...).</summary>
    public static string? Sniff(ReadOnlySpan<byte> data)
    {
        if (data.Length >= 8 && data[0] == 0x89 && data[1] == (byte)'P' && data[2] == (byte)'N' && data[3] == (byte)'G')
        {
            return ".png";
        }

        if (data.Length >= 3 && data[0] == 0xFF && data[1] == 0xD8 && data[2] == 0xFF)
        {
            return ".jpg";
        }

        if (data.Length >= 12 && data[..4].SequenceEqual("RIFF"u8) && data[8..12].SequenceEqual("WEBP"u8))
        {
            return ".webp";
        }

        return null;
    }
}
