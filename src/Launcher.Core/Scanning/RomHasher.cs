using System.Buffers;
using System.Security.Cryptography;

namespace Launcher.Core.Scanning;

/// <summary>A ROM's checksums as ScreenScraper takes them: upper-case hex.</summary>
public sealed record RomHashes(string Crc32, string Md5, string Sha1);

/// <summary>
/// Hashes a ROM file in one pass: CRC32, MD5 and SHA-1. ScreenScraper asks for at least one hash with every lookup,
/// so files up to <c>[scraping] hash_limit_mb</c> are hashed once and the result kept in <c>games</c> (cleared when
/// the file changes). Does file I/O: never on the main thread.
/// </summary>
public static class RomHasher
{
    private static readonly uint[] Table = BuildTable();

    /// <summary>Playlists name other files; their own hash matches nothing.</summary>
    public static bool IsHashable(string relPath)
    {
        ArgumentNullException.ThrowIfNull(relPath);
        var extension = Path.GetExtension(relPath);
        return !extension.Equals(".m3u", StringComparison.OrdinalIgnoreCase)
            && !extension.Equals(".cue", StringComparison.OrdinalIgnoreCase)
            && !extension.Equals(".gdi", StringComparison.OrdinalIgnoreCase);
    }

    public static RomHashes Compute(string path, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(path);
        using var md5 = IncrementalHash.CreateHash(HashAlgorithmName.MD5);
        using var sha1 = IncrementalHash.CreateHash(HashAlgorithmName.SHA1);
        var crc = 0xFFFF_FFFFu;
        var buffer = ArrayPool<byte>.Shared.Rent(1 << 20);
        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1, FileOptions.SequentialScan);
            int read;
            while ((read = stream.Read(buffer, 0, buffer.Length)) > 0)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var span = buffer.AsSpan(0, read);
                md5.AppendData(span);
                sha1.AppendData(span);
                crc = UpdateCrc(crc, span);
            }
        }
        finally
        {
            ArrayPool<byte>.Shared.Return(buffer);
        }

        return new RomHashes(
            (~crc).ToString("X8", System.Globalization.CultureInfo.InvariantCulture),
            Convert.ToHexString(md5.GetHashAndReset()),
            Convert.ToHexString(sha1.GetHashAndReset()));
    }

    /// <summary>The standard (IEEE, reflected) CRC-32 of <paramref name="data"/>.</summary>
    public static uint Crc32(ReadOnlySpan<byte> data) => ~UpdateCrc(0xFFFF_FFFFu, data);

    private static uint UpdateCrc(uint crc, ReadOnlySpan<byte> data)
    {
        foreach (var b in data)
        {
            crc = Table[(crc ^ b) & 0xFF] ^ (crc >> 8);
        }

        return crc;
    }

    private static uint[] BuildTable()
    {
        var table = new uint[256];
        for (var i = 0u; i < 256; i++)
        {
            var c = i;
            for (var k = 0; k < 8; k++)
            {
                c = (c & 1) != 0 ? 0xEDB8_8320u ^ (c >> 1) : c >> 1;
            }

            table[i] = c;
        }

        return table;
    }
}
