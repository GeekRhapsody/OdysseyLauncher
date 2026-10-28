using System.Buffers.Binary;
using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;

namespace Launcher.Core.Launching;

/// <summary>
/// A game's title id, which <c>{title_id}</c> expands to (ARCHITECTURE.md A5, Vita3K's games): nine letters and digits,
/// as Sony numbers its games (<c>PCSF00024</c>, a PS Vita game) and as Vita3K names an installed game's folder. Read,
/// in order, from the game's name, as dumps carry it and RetroBat reads it (<c>Gravity Rush (Europe) [PCSF00024].vpk</c>,
/// the last such tag); from a file of at most <see cref="MaxTextFileSize"/> bytes, as text (ES-DE's <c>.psvita</c>
/// file holds the id); from a game's folder's <c>sce_sys/param.sfo</c>; or from the <c>sce_sys/param.sfo</c> in a
/// package (<c>.vpk</c> and <c>.zip</c> are zip files). Does file I/O: never on the main thread.
/// </summary>
public static partial class TitleId
{
    /// <summary>A file this size or smaller is read as text: ES-DE reads at most 4,096 bytes of a file it injects.</summary>
    public const int MaxTextFileSize = 4096;

    /// <summary>A <c>param.sfo</c> larger than this isn't read (a game's is about 1 KB).</summary>
    private const int MaxSfoSize = 64 * 1024;

    private const string SfoName = "sce_sys/param.sfo";

    /// <summary>The title id in <paramref name="path"/>'s file or folder name, or null. No file I/O.</summary>
    public static string? FromName(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var matches = BracketedId().Matches(Path.GetFileName(Path.TrimEndingDirectorySeparator(path)));
        return matches.Count == 0 ? null : matches[^1].Groups[1].Value.ToUpperInvariant();
    }

    /// <summary>
    /// The title id of the game at <paramref name="path"/> (its file, or its folder), or null when none of the places
    /// above has one, or the file can't be read.
    /// </summary>
    public static string? Read(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (FromName(path) is { } named)
        {
            return named;
        }

        try
        {
            if (Directory.Exists(path))
            {
                var sfo = new FileInfo(Path.Combine(path, "sce_sys", "param.sfo"));
                return sfo.Exists && sfo.Length <= MaxSfoSize ? FromParamSfo(File.ReadAllBytes(sfo.FullName)) : null;
            }

            var file = new FileInfo(path);
            if (!file.Exists)
            {
                return null;
            }

            return file.Length <= MaxTextFileSize ? FromText(File.ReadAllText(path)) : FromArchive(path);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or InvalidDataException)
        {
            return null;
        }
    }

    /// <summary>The first word of <paramref name="text"/> that is a title id, or null.</summary>
    public static string? FromText(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        foreach (var word in text.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries))
        {
            if (IsTitleId(word))
            {
                return word.ToUpperInvariant();
            }
        }

        return null;
    }

    /// <summary>
    /// The <c>TITLE_ID</c> of a <c>param.sfo</c> (Sony's "system file object": a header, an index of keys, the keys,
    /// then their values), or null when it has none or isn't one.
    /// </summary>
    public static string? FromParamSfo(ReadOnlySpan<byte> sfo)
    {
        // The header: "\0PSF", the version, where the keys and the values start, and how many entries there are.
        if (sfo.Length < 20 || !sfo[..4].SequenceEqual("\0PSF"u8))
        {
            return null;
        }

        var keys = BinaryPrimitives.ReadUInt32LittleEndian(sfo[8..]);
        var values = BinaryPrimitives.ReadUInt32LittleEndian(sfo[12..]);
        var count = BinaryPrimitives.ReadUInt32LittleEndian(sfo[16..]);
        for (var i = 0L; i < count; i++)
        {
            // Each index entry: the key's offset (16 bits), the value's format (16) and length (32), the space kept
            // for it (32), and its offset (32).
            var at = 20 + (i * 16);
            if (at + 16 > sfo.Length)
            {
                return null;
            }

            var entry = sfo.Slice((int)at, 16);
            var keyAt = keys + (long)BinaryPrimitives.ReadUInt16LittleEndian(entry);
            var length = BinaryPrimitives.ReadUInt32LittleEndian(entry[4..]);
            var valueAt = values + (long)BinaryPrimitives.ReadUInt32LittleEndian(entry[12..]);
            if (keyAt >= sfo.Length || !sfo[(int)keyAt..].StartsWith("TITLE_ID\0"u8))
            {
                continue;
            }

            if (valueAt + length > sfo.Length)
            {
                return null;
            }

            var value = Encoding.UTF8.GetString(sfo.Slice((int)valueAt, (int)length)).TrimEnd('\0').Trim();
            return IsTitleId(value) ? value.ToUpperInvariant() : null;
        }

        return null;
    }

    /// <summary>
    /// The title id in a package's <c>param.sfo</c>: the one nearest its root, the game's own, not an update's or an
    /// add-on's the package may also hold. Only the zip's directory and that one entry are read.
    /// </summary>
    private static string? FromArchive(string path)
    {
        using var zip = ZipFile.OpenRead(path);
        ZipArchiveEntry? sfo = null;
        foreach (var entry in zip.Entries)
        {
            if (entry.FullName.Replace('\\', '/').EndsWith(SfoName, StringComparison.OrdinalIgnoreCase)
                && entry.Length <= MaxSfoSize && (sfo is null || entry.FullName.Length < sfo.FullName.Length))
            {
                sfo = entry;
            }
        }

        if (sfo is null)
        {
            return null;
        }

        using var stream = sfo.Open();
        using var bytes = new MemoryStream((int)sfo.Length);
        stream.CopyTo(bytes);
        return FromParamSfo(bytes.GetBuffer().AsSpan(0, (int)bytes.Length));
    }

    private static bool IsTitleId(string value)
    {
        if (value.Length != 9)
        {
            return false;
        }

        foreach (var c in value)
        {
            if (!char.IsAsciiLetterOrDigit(c))
            {
                return false;
            }
        }

        return true;
    }

    [GeneratedRegex(@"\[([A-Za-z0-9]{9})\]", RegexOptions.CultureInvariant)]
    private static partial Regex BracketedId();
}
