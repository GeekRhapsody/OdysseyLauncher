using System.Buffers.Binary;

namespace Launcher.Core.Media;

/// <summary>
/// Reads an image's pixel size from its header only (A1 Media): PNG, JPEG and WebP. Nothing is decoded, and a JPEG
/// is read segment by segment, skipping the data in between.
/// </summary>
public static class ImageHeaders
{
    /// <summary>A JPEG whose frame header isn't within this many bytes is treated as unreadable.</summary>
    private const long MaxJpegScanBytes = 4 * 1024 * 1024;

    /// <summary>Does file I/O. False if the file can't be read or isn't a PNG, JPEG or WebP with a sane size.</summary>
    public static bool TryReadSize(string path, out int width, out int height)
    {
        ArgumentNullException.ThrowIfNull(path);
        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, bufferSize: 512);
            return TryReadSize(stream, out width, out height);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            width = height = 0;
            return false;
        }
    }

    /// <summary>Reads from the stream's current position, which must be the start of the image.</summary>
    public static bool TryReadSize(Stream stream, out int width, out int height)
    {
        ArgumentNullException.ThrowIfNull(stream);
        width = height = 0;
        Span<byte> head = stackalloc byte[30];
        var read = ReadAtMost(stream, head);
        head = head[..read];
        var ok = head switch
        {
            [0x89, (byte)'P', (byte)'N', (byte)'G', ..] => TryPng(head, out width, out height),
            [0xFF, 0xD8, ..] => TryJpeg(stream, out width, out height),
            [(byte)'R', (byte)'I', (byte)'F', (byte)'F', _, _, _, _, (byte)'W', (byte)'E', (byte)'B', (byte)'P', ..] => TryWebP(head, out width, out height),
            _ => false,
        };

        if (!ok || width <= 0 || height <= 0 || width > 65535 || height > 65535)
        {
            width = height = 0;
            return false;
        }

        return true;
    }

    /// <summary>The 8-byte signature, then the IHDR chunk: length, type, width and height, big-endian.</summary>
    private static bool TryPng(ReadOnlySpan<byte> head, out int width, out int height)
    {
        width = height = 0;
        if (head.Length < 24 || !head[12..16].SequenceEqual("IHDR"u8))
        {
            return false;
        }

        width = BinaryPrimitives.ReadInt32BigEndian(head[16..]);
        height = BinaryPrimitives.ReadInt32BigEndian(head[20..]);
        return true;
    }

    /// <summary>
    /// Walks the markers after SOI until a start-of-frame (SOF0 to SOF15, except DHT, JPG and DAC), whose payload is
    /// precision, height and width.
    /// </summary>
    private static bool TryJpeg(Stream stream, out int width, out int height)
    {
        width = height = 0;
        if (!stream.CanSeek)
        {
            return false;
        }

        long position = 2;
        Span<byte> segment = stackalloc byte[9];
        while (position < MaxJpegScanBytes)
        {
            stream.Position = position;
            var got = ReadAtMost(stream, segment);
            if (got < 4 || segment[0] != 0xFF)
            {
                return false;
            }

            // Fill bytes: any number of 0xFF before the marker.
            var marker = segment[1];
            if (marker == 0xFF)
            {
                position++;
                continue;
            }

            // Markers without a length.
            if (marker is 0x01 or (>= 0xD0 and <= 0xD8))
            {
                position += 2;
                continue;
            }

            if (marker is 0xD9 or 0xDA)
            {
                // End of image, or the scan started before any frame header.
                return false;
            }

            var length = BinaryPrimitives.ReadUInt16BigEndian(segment[2..]);
            if (length < 2)
            {
                return false;
            }

            if (marker is >= 0xC0 and <= 0xCF and not 0xC4 and not 0xC8 and not 0xCC)
            {
                if (length < 7 || got < segment.Length)
                {
                    return false;
                }

                height = BinaryPrimitives.ReadUInt16BigEndian(segment[5..]);
                width = BinaryPrimitives.ReadUInt16BigEndian(segment[7..]);
                return true;
            }

            position += 2 + length;
        }

        return false;
    }

    /// <summary>The first chunk after the RIFF header: <c>VP8 </c> (lossy), <c>VP8L</c> (lossless) or <c>VP8X</c> (extended).</summary>
    private static bool TryWebP(ReadOnlySpan<byte> head, out int width, out int height)
    {
        width = height = 0;
        if (head.Length < 30)
        {
            return false;
        }

        var chunk = head[12..16];
        var data = head[20..];
        if (chunk.SequenceEqual("VP8 "u8))
        {
            // A 3-byte frame tag, the start code 9D 01 2A, then 14-bit width and height.
            if (data[3] != 0x9D || data[4] != 0x01 || data[5] != 0x2A)
            {
                return false;
            }

            width = BinaryPrimitives.ReadUInt16LittleEndian(data[6..]) & 0x3FFF;
            height = BinaryPrimitives.ReadUInt16LittleEndian(data[8..]) & 0x3FFF;
            return true;
        }

        if (chunk.SequenceEqual("VP8L"u8))
        {
            // The signature 0x2F, then width - 1 and height - 1 in 14 bits each.
            if (data[0] != 0x2F)
            {
                return false;
            }

            var bits = BinaryPrimitives.ReadUInt32LittleEndian(data[1..]);
            width = (int)(bits & 0x3FFF) + 1;
            height = (int)((bits >> 14) & 0x3FFF) + 1;
            return true;
        }

        if (chunk.SequenceEqual("VP8X"u8))
        {
            // Flags and reserved bytes, then the canvas width - 1 and height - 1 in 24 bits each.
            width = (data[4] | data[5] << 8 | data[6] << 16) + 1;
            height = (data[7] | data[8] << 8 | data[9] << 16) + 1;
            return true;
        }

        return false;
    }

    private static int ReadAtMost(Stream stream, Span<byte> buffer)
    {
        var total = 0;
        while (total < buffer.Length)
        {
            var n = stream.Read(buffer[total..]);
            if (n == 0)
            {
                break;
            }

            total += n;
        }

        return total;
    }
}
