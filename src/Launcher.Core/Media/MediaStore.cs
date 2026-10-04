namespace Launcher.Core.Media;

/// <summary>A media file as written: where it is, and what the <c>media</c> row records about it.</summary>
/// <param name="RelativePath">'/'-separated, as stored in <c>media.path</c>: <c>media/&lt;system&gt;/...</c> (<see cref="MediaFolder"/>).</param>
public sealed record StoredMedia(string RelativePath, long SizeBytes, long MtimeMs, int Width, int Height);

/// <summary>
/// Scraped downloads on disk (ARCHITECTURE.md A4), in the media folder every game's media is indexed from:
/// <c>&lt;media folder&gt;/&lt;system&gt;/&lt;kind&gt;/&lt;rel path&gt;.&lt;ext&gt;</c>, the ROM's whole name, as the user's own
/// art is named. A download never replaces a file: what's in the folder is the game's, wherever it came from. Writes
/// are atomic (a temporary file, then a move), so a crash never leaves a half-written image where the grid would
/// read it. Does file I/O: never on the main thread.
/// </summary>
/// <param name="mediaDir">The media folder (<see cref="MediaFolder.Of"/>).</param>
public sealed class MediaStore(string mediaDir)
{
    public string MediaDir { get; } = mediaDir ?? throw new ArgumentNullException(nameof(mediaDir));

    /// <summary>A game's own file of a kind: <c>media/&lt;system&gt;/&lt;kind&gt;/&lt;rel path&gt;&lt;extension&gt;</c>.</summary>
    /// <param name="relPath">The ROM's <c>rel_path</c>, its extension included.</param>
    /// <param name="extension">With its dot: ".png", ".jpg", ".webp", ".mp4" or ".glb".</param>
    public static string RelativePathFor(string systemId, string relPath, string kind, string extension)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        ArgumentNullException.ThrowIfNull(relPath);
        ArgumentNullException.ThrowIfNull(kind);
        ArgumentNullException.ThrowIfNull(extension);
        return $"{MediaScanner.FolderName}/{systemId}/{kind}/{relPath}{extension}";
    }

    public string FullPath(string relativePath) => MediaFolder.FullPath(MediaDir, relativePath);

    /// <summary>
    /// Writes a download (an image, or for <see cref="MediaKinds.Video"/> a video) as the game's file of that kind,
    /// unless the game has one already (<see cref="HasFile"/>). A video has no size: its width and height are 0.
    /// </summary>
    /// <returns>The file written, or null when the game already had a file of that kind, which is left as it is.</returns>
    /// <exception cref="InvalidDataException">The content isn't a PNG, JPEG or WebP image, or for a video an MP4.</exception>
    public async Task<StoredMedia?> SaveAsync(string systemId, string relPath, string kind, ReadOnlyMemory<byte> content, CancellationToken cancellationToken)
    {
        int width = 0, height = 0;
        string extension;
        if (kind == MediaKinds.Video)
        {
            extension = VideoFormats.Sniff(content.Span) ?? throw new InvalidDataException("the download isn't an MP4 video");
        }
        else
        {
            extension = ImageFormats.Sniff(content.Span)
                ?? throw new InvalidDataException("the download isn't a PNG, JPEG or WebP image");
            using var probe = new MemoryStream(content.ToArray(), writable: false);
            if (!ImageHeaders.TryReadSize(probe, out width, out height))
            {
                throw new InvalidDataException("the image's header can't be read");
            }
        }

        if (HasFile(systemId, relPath, kind))
        {
            return null;
        }

        var relative = RelativePathFor(systemId, relPath, kind, extension);
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

            // Not overwriting: a file the user put there meanwhile stays.
            File.Move(temp, full, overwrite: false);
        }
        catch (IOException) when (File.Exists(full))
        {
            File.Delete(temp);
            return null;
        }
        catch
        {
            File.Delete(temp);
            throw;
        }

        var info = new FileInfo(full);
        return new StoredMedia(relative, info.Length, new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds(), width, height);
    }

    /// <summary>
    /// Whether the game has a file of the kind on disk, in any of the kind's formats: its own (its whole ROM name), or
    /// the one every game of its name shares (the ROM's name without its extension), as a scan matches them.
    /// </summary>
    public bool HasFile(string systemId, string relPath, string kind)
    {
        var dot = relPath.LastIndexOf('.');
        var stem = dot > relPath.LastIndexOf('/') + 1 ? relPath[..dot] : null;
        foreach (var extension in MediaKinds.ExtensionsOf(kind))
        {
            if (File.Exists(FullPath(RelativePathFor(systemId, relPath, kind, extension)))
                || (stem is not null && File.Exists(FullPath(RelativePathFor(systemId, stem, kind, extension)))))
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>Every file named after the game (its whole ROM name), of every kind and format: what clearing it deletes.</summary>
    public IReadOnlyList<string> FilesOf(string systemId, string relPath)
    {
        var files = new List<string>();
        if (!Directory.Exists(Path.Combine(MediaDir, systemId)))
        {
            return files;
        }

        foreach (var kind in MediaKinds.All)
        {
            foreach (var extension in MediaKinds.ExtensionsOf(kind))
            {
                var path = FullPath(RelativePathFor(systemId, relPath, kind, extension));
                if (File.Exists(path))
                {
                    files.Add(path);
                }
            }
        }

        return files;
    }
}

/// <summary>Recognises the image formats the app decodes by their first bytes.</summary>
public static class ImageFormats
{
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

/// <summary>Recognises the video formats scraping stores by their first bytes.</summary>
public static class VideoFormats
{
    /// <summary>".mp4" (an ISO base media file: an <c>ftyp</c> box first), or null for anything else.</summary>
    public static string? Sniff(ReadOnlySpan<byte> data) =>
        data.Length >= 12 && data[4..8].SequenceEqual("ftyp"u8) ? ".mp4" : null;
}
