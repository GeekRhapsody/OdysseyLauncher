namespace Launcher.Core.Media;

/// <summary>A media file as written: where it is, and what the <c>media</c> row records about it.</summary>
/// <param name="RelativePath">'/'-separated, as stored in <c>media.path</c>: <c>media/&lt;system&gt;/...</c> (<see cref="MediaFolder"/>).</param>
public sealed record StoredMedia(string RelativePath, long SizeBytes, long MtimeMs, int Width, int Height);

/// <summary>
/// Scraped downloads on disk (ARCHITECTURE.md A4), in the media folder every game's media is indexed from:
/// <c>&lt;media folder&gt;/&lt;system&gt;/&lt;folder&gt;/&lt;name&gt;.&lt;ext&gt;</c>, the name being the ROM's <c>rel_path</c>
/// without its extension, as ES-DE names media (2026-10-06), and as the user's own art is named. A download never
/// replaces a file: what's in the folder is the game's, wherever it came from. Writes are atomic (a temporary file,
/// then a move), so a crash never leaves a half-written image where the grid would read it. Does file I/O: never on
/// the main thread.
/// </summary>
/// <param name="mediaDir">The media folder (<see cref="MediaFolder.Of"/>).</param>
public sealed class MediaStore(string mediaDir)
{
    public string MediaDir { get; } = mediaDir ?? throw new ArgumentNullException(nameof(mediaDir));

    /// <summary>
    /// A file of a kind, as stored: <c>media/&lt;system&gt;/&lt;folder&gt;/&lt;name&gt;&lt;extension&gt;</c>, the folder being
    /// <see cref="MediaKinds.FolderOf"/>.
    /// </summary>
    /// <param name="name">The path under the kind's folder without the file's extension: <see cref="NameOf"/> for the file a game's media is written as.</param>
    /// <param name="extension">With its dot: ".png", ".jpg", ".webp", ".mp4", ".pdf" or ".glb".</param>
    public static string RelativePathFor(string systemId, string name, string kind, string extension)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        ArgumentNullException.ThrowIfNull(name);
        ArgumentNullException.ThrowIfNull(kind);
        ArgumentNullException.ThrowIfNull(extension);
        return $"{MediaScanner.FolderName}/{systemId}/{MediaKinds.FolderOf(kind)}/{name}{extension}";
    }

    /// <summary>
    /// The file a game's media of a kind is written as: <c>media/&lt;system&gt;/&lt;folder&gt;/&lt;name&gt;&lt;extension&gt;</c>,
    /// named after the ROM without its extension (<see cref="NameOf"/>).
    /// </summary>
    /// <param name="relPath">The ROM's <c>rel_path</c>, its extension included.</param>
    public static string PathFor(string systemId, string relPath, string kind, string extension) =>
        RelativePathFor(systemId, NameOf(relPath), kind, extension);

    /// <summary>
    /// The name a game's media files are written with: its <c>rel_path</c> without the ROM's extension
    /// (<c>sub/Albion (1995).zip</c> is <c>sub/Albion (1995)</c>), so every ROM of that name shares them, as in ES-DE.
    /// A name with no extension is kept whole.
    /// </summary>
    public static string NameOf(string relPath)
    {
        ArgumentNullException.ThrowIfNull(relPath);
        var dot = relPath.LastIndexOf('.');
        return dot > relPath.LastIndexOf('/') + 1 ? relPath[..dot] : relPath;
    }

    public string FullPath(string relativePath) => MediaFolder.FullPath(MediaDir, relativePath);

    /// <summary>
    /// Writes a download (an image, for <see cref="MediaKinds.Video"/> a video, for <see cref="MediaKinds.Manual"/> a
    /// PDF) as the game's file of that kind, unless the game has one already (<see cref="HasFile"/>). A video or a
    /// manual has no size: its width and height are 0.
    /// </summary>
    /// <returns>The file written, or null when the game already had a file of that kind, which is left as it is.</returns>
    /// <exception cref="InvalidDataException">The content isn't a PNG, JPEG or WebP image, for a video an MP4, or for a manual a PDF.</exception>
    public async Task<StoredMedia?> SaveAsync(string systemId, string relPath, string kind, ReadOnlyMemory<byte> content, CancellationToken cancellationToken)
    {
        int width = 0, height = 0;
        string extension;
        if (kind == MediaKinds.Video)
        {
            extension = VideoFormats.Sniff(content.Span) ?? throw new InvalidDataException("the download isn't an MP4 video");
        }
        else if (kind == MediaKinds.Manual)
        {
            extension = DocumentFormats.Sniff(content.Span) ?? throw new InvalidDataException("the download isn't a PDF");
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

        var relative = PathFor(systemId, relPath, kind, extension);
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
    /// Whether the game has a file of the kind on disk, in any of the kind's formats, as a scan matches them: the one
    /// every game of its name shares (<see cref="NameOf"/>, as the app writes them), or one named after its whole ROM
    /// name (that ROM's alone, which the user can add).
    /// </summary>
    public bool HasFile(string systemId, string relPath, string kind) => FilesOf(systemId, relPath, kind).Count > 0;

    /// <summary>
    /// The game's files of a kind on disk, as stored (<see cref="HasFile"/>): what the user's own file replaces, and
    /// what removing the kind deletes.
    /// </summary>
    public IReadOnlyList<string> FilesOf(string systemId, string relPath, string kind)
    {
        ArgumentNullException.ThrowIfNull(relPath);
        var files = new List<string>();
        var name = NameOf(relPath);
        foreach (var extension in MediaKinds.ExtensionsOf(kind))
        {
            foreach (var named in (ReadOnlySpan<string>)[name, relPath])
            {
                var relative = RelativePathFor(systemId, named, kind, extension);
                if (File.Exists(FullPath(relative)) && !files.Contains(relative))
                {
                    files.Add(relative);
                }
            }
        }

        return files;
    }

    /// <summary>
    /// Every file named after the game, of every kind and format (<see cref="FilesOf(string, string, string)"/>), as
    /// full paths: what clearing it deletes, except a file another game also uses.
    /// </summary>
    public IReadOnlyList<string> FilesOf(string systemId, string relPath)
    {
        var files = new List<string>();
        if (!Directory.Exists(Path.Combine(MediaDir, systemId)))
        {
            return files;
        }

        foreach (var kind in MediaKinds.All)
        {
            foreach (var relative in FilesOf(systemId, relPath, kind))
            {
                files.Add(FullPath(relative));
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

/// <summary>Recognises the document formats scraping stores (a game's manual) by their first bytes.</summary>
public static class DocumentFormats
{
    /// <summary>How far into a file a PDF's header may be: PDF readers accept it anywhere in the first 1 KB.</summary>
    public const int HeaderWindow = 1024;

    /// <summary>".pdf" (<c>%PDF-</c> in the first KB), or null for anything else.</summary>
    public static string? Sniff(ReadOnlySpan<byte> data) =>
        data[..Math.Min(data.Length, HeaderWindow)].IndexOf("%PDF-"u8) >= 0 ? ".pdf" : null;
}
