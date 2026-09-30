using System.Buffers.Binary;
using System.IO.Compression;
using Launcher.Core.Scanning;

namespace Launcher.Core.Media;

/// <summary>
/// Writes 8-bit RGBA pixels as a PNG (RGB when every pixel is opaque), with the Paeth filter on every row: enough for
/// the textures model processing scales down (A7), with no image package.
/// </summary>
public static class PngEncoder
{
    private static ReadOnlySpan<byte> Signature => [0x89, (byte)'P', (byte)'N', (byte)'G', 0x0D, 0x0A, 0x1A, 0x0A];

    public static byte[] Encode(ReadOnlySpan<byte> rgba, int width, int height)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(width);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(height);
        if (rgba.Length < width * height * 4)
        {
            throw new ArgumentException("the pixels are fewer than width × height", nameof(rgba));
        }

        var opaque = true;
        for (var i = 3; i < width * height * 4 && opaque; i += 4)
        {
            opaque = rgba[i] == 255;
        }

        var channels = opaque ? 3 : 4;
        var stride = width * channels;
        var previous = new byte[stride];
        var row = new byte[stride];
        var filtered = new byte[stride + 1];
        using var compressed = new MemoryStream();
        using (var zlib = new ZLibStream(compressed, CompressionLevel.Optimal, leaveOpen: true))
        {
            for (var y = 0; y < height; y++)
            {
                var source = rgba.Slice(y * width * 4, width * 4);
                for (var x = 0; x < width; x++)
                {
                    for (var c = 0; c < channels; c++)
                    {
                        row[x * channels + c] = source[x * 4 + c];
                    }
                }

                // Paeth: each byte minus the predictor of its left, upper and upper-left neighbours.
                filtered[0] = 4;
                for (var i = 0; i < stride; i++)
                {
                    var a = i >= channels ? row[i - channels] : 0;
                    var b = previous[i];
                    var c = i >= channels ? previous[i - channels] : 0;
                    filtered[i + 1] = (byte)(row[i] - Paeth(a, b, c));
                }

                zlib.Write(filtered);
                (previous, row) = (row, previous);
            }
        }

        var header = new byte[13];
        BinaryPrimitives.WriteInt32BigEndian(header, width);
        BinaryPrimitives.WriteInt32BigEndian(header.AsSpan(4), height);
        header[8] = 8;
        header[9] = (byte)(opaque ? 2 : 6);

        using var png = new MemoryStream();
        png.Write(Signature);
        Chunk(png, "IHDR"u8, header);
        Chunk(png, "IDAT"u8, compressed.ToArray());
        Chunk(png, "IEND"u8, []);
        return png.ToArray();
    }

    private static int Paeth(int a, int b, int c)
    {
        var p = a + b - c;
        var pa = Math.Abs(p - a);
        var pb = Math.Abs(p - b);
        var pc = Math.Abs(p - c);
        return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
    }

    private static void Chunk(Stream stream, ReadOnlySpan<byte> type, ReadOnlySpan<byte> data)
    {
        Span<byte> number = stackalloc byte[4];
        BinaryPrimitives.WriteInt32BigEndian(number, data.Length);
        stream.Write(number);
        var typed = new byte[type.Length + data.Length];
        type.CopyTo(typed);
        data.CopyTo(typed.AsSpan(type.Length));
        stream.Write(typed);
        BinaryPrimitives.WriteUInt32BigEndian(number, RomHasher.Crc32(typed));
        stream.Write(number);
    }
}
