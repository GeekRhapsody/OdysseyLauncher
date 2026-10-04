using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace Launcher.Core.Media;

/// <summary>
/// Where the grid's baked cover derivatives live (A3): <c>CacheDir/textures/&lt;key&gt;.dds</c>, one canonical size
/// (BC7, 512², full mips) keyed by the source's stored path (<c>media/...</c>, wherever the media folder is), size and modification time, so a changed
/// source gets a new derivative and a stale one is never shown.
/// <para>
/// The whole source image is scaled to the square, whatever its aspect ratio. The cover shader crops it to the
/// face at draw time, using the source's aspect from <c>media.width</c> and <c>media.height</c>, so one derivative
/// serves every box template.
/// </para>
/// </summary>
public static class TextureDerivatives
{
    public const string FolderName = "textures";
    public const string Extension = ".dds";

    /// <summary>The canonical size, in pixels, of every derivative.</summary>
    public const int Size = 512;

    /// <summary>
    /// The derivative's file name. Pure; the key is the first 128 bits of a SHA-256, as hex, over a versioned string
    /// of the three inputs.
    /// </summary>
    public static string FileName(string relPath, long sizeBytes, long mtimeMs)
    {
        ArgumentNullException.ThrowIfNull(relPath);
        Span<char> name = stackalloc char[KeyLength + Extension.Length];
        WriteFileName(relPath, sizeBytes, mtimeMs, name);
        return new string(name);
    }

    /// <summary>
    /// The derivative's absolute path for a source whose size and time are known (as indexed in <c>media</c>):
    /// pure, and one string allocation, so the texture workers can call it for every cover.
    /// </summary>
    public static string PathFor(string cacheDir, string relPath, long sizeBytes, long mtimeMs)
    {
        ArgumentNullException.ThrowIfNull(cacheDir);
        ArgumentNullException.ThrowIfNull(relPath);
        var folder = Path.TrimEndingDirectorySeparator(cacheDir.AsSpan());
        var length = folder.Length + 1 + FolderName.Length + 1 + KeyLength + Extension.Length;
        Span<char> path = length <= 1024 ? stackalloc char[length] : new char[length];
        folder.CopyTo(path);
        var at = folder.Length;
        path[at++] = Path.DirectorySeparatorChar;
        FolderName.CopyTo(path[at..]);
        at += FolderName.Length;
        path[at++] = Path.DirectorySeparatorChar;
        WriteFileName(relPath, sizeBytes, mtimeMs, path[at..]);
        return new string(path);
    }

    /// <summary>The derivative's absolute path. Does file I/O (reads the source's size and time): never on the main thread.</summary>
    /// <returns>Null when the source doesn't exist.</returns>
    /// <param name="mediaDir">The media folder, which a stored path's <c>media/</c> stands for (<see cref="MediaFolder"/>).</param>
    public static string? PathFor(string cacheDir, string mediaDir, string relPath)
    {
        ArgumentNullException.ThrowIfNull(cacheDir);
        ArgumentNullException.ThrowIfNull(mediaDir);
        var source = new FileInfo(MediaFolder.FullPath(mediaDir, relPath));
        if (!source.Exists)
        {
            return null;
        }

        return PathFor(cacheDir, relPath, source.Length, new DateTimeOffset(source.LastWriteTimeUtc).ToUnixTimeMilliseconds());
    }

    private const int KeyLength = 32;

    /// <summary>Writes the 32 hex digits and the extension into <paramref name="destination"/>, without allocating.</summary>
    private static void WriteFileName(string relPath, long sizeBytes, long mtimeMs, Span<char> destination)
    {
        // v2 (2026-10-02): every source is in the media folder, so the key no longer names a root (and moving the folder
        // keeps every key).
        var textLength = 3 + relPath.Length + 1 + 20 + 1 + 20;
        Span<char> text = textLength <= 1024 ? stackalloc char[textLength] : new char[textLength];
        var n = 0;
        "v2\n".CopyTo(text);
        n += 3;
        for (var i = 0; i < relPath.Length; i++)
        {
            text[n++] = relPath[i] == '\\' ? '/' : relPath[i];
        }

        text[n++] = '\n';
        sizeBytes.TryFormat(text[n..], out var written, provider: CultureInfo.InvariantCulture);
        n += written;
        text[n++] = '\n';
        mtimeMs.TryFormat(text[n..], out written, provider: CultureInfo.InvariantCulture);
        n += written;

        var byteCount = Encoding.UTF8.GetByteCount(text[..n]);
        Span<byte> utf8 = byteCount <= 4096 ? stackalloc byte[byteCount] : new byte[byteCount];
        Encoding.UTF8.GetBytes(text[..n], utf8);
        Span<byte> hash = stackalloc byte[32];
        SHA256.HashData(utf8, hash);
        const string Hex = "0123456789abcdef";
        for (var i = 0; i < KeyLength / 2; i++)
        {
            destination[2 * i] = Hex[hash[i] >> 4];
            destination[2 * i + 1] = Hex[hash[i] & 0xF];
        }

        Extension.CopyTo(destination[KeyLength..]);
    }
}
