using System.Buffers.Binary;

namespace Launcher.Core.Tests.TestSupport;

/// <summary>
/// Image files with valid headers and no pixel data worth decoding: enough for <see cref="Launcher.Core.Media.ImageHeaders"/>.
/// </summary>
public static class TestImages
{
    public static byte[] Png(int width, int height)
    {
        var bytes = new byte[33];
        ReadOnlySpan<byte> signature = [0x89, (byte)'P', (byte)'N', (byte)'G', 0x0D, 0x0A, 0x1A, 0x0A];
        signature.CopyTo(bytes);
        BinaryPrimitives.WriteInt32BigEndian(bytes.AsSpan(8), 13);
        "IHDR"u8.CopyTo(bytes.AsSpan(12));
        BinaryPrimitives.WriteInt32BigEndian(bytes.AsSpan(16), width);
        BinaryPrimitives.WriteInt32BigEndian(bytes.AsSpan(20), height);
        bytes[24] = 8;
        bytes[25] = 2;
        return bytes;
    }

    /// <param name="paddingBytes">Size of an APP1 (EXIF-like) segment before the frame header, to test skipping.</param>
    public static byte[] Jpeg(int width, int height, int paddingBytes = 0)
    {
        using var stream = new MemoryStream();
        stream.Write([0xFF, 0xD8]);
        stream.Write([0xFF, 0xE0, 0x00, 0x10, (byte)'J', (byte)'F', (byte)'I', (byte)'F', 0, 1, 1, 0, 0, 1, 0, 1, 0, 0]);
        if (paddingBytes > 0)
        {
            var length = paddingBytes + 2;
            stream.Write([0xFF, 0xE1, (byte)(length >> 8), (byte)length]);
            stream.Write(new byte[paddingBytes]);
        }

        // A fill byte before the marker, which readers must skip.
        stream.Write([0xFF, 0xFF, 0xC4, 0x00, 0x03, 0x00]);
        stream.Write([0xFF, 0xC2, 0x00, 0x11, 0x08, (byte)(height >> 8), (byte)height, (byte)(width >> 8), (byte)width, 0x03]);
        stream.Write(new byte[9]);
        stream.Write([0xFF, 0xD9]);
        return stream.ToArray();
    }

    public static byte[] WebPLossy(int width, int height)
    {
        var bytes = new byte[40];
        "RIFF"u8.CopyTo(bytes);
        BinaryPrimitives.WriteInt32LittleEndian(bytes.AsSpan(4), bytes.Length - 8);
        "WEBPVP8 "u8.CopyTo(bytes.AsSpan(8));
        BinaryPrimitives.WriteInt32LittleEndian(bytes.AsSpan(16), 20);
        bytes[23] = 0x9D;
        bytes[24] = 0x01;
        bytes[25] = 0x2A;
        BinaryPrimitives.WriteUInt16LittleEndian(bytes.AsSpan(26), (ushort)width);
        BinaryPrimitives.WriteUInt16LittleEndian(bytes.AsSpan(28), (ushort)height);
        return bytes;
    }

    public static byte[] WebPLossless(int width, int height)
    {
        var bytes = new byte[40];
        "RIFF"u8.CopyTo(bytes);
        BinaryPrimitives.WriteInt32LittleEndian(bytes.AsSpan(4), bytes.Length - 8);
        "WEBPVP8L"u8.CopyTo(bytes.AsSpan(8));
        BinaryPrimitives.WriteInt32LittleEndian(bytes.AsSpan(16), 20);
        bytes[20] = 0x2F;
        var bits = (uint)(width - 1) | (uint)(height - 1) << 14;
        BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(21), bits);
        return bytes;
    }

    public static byte[] WebPExtended(int width, int height)
    {
        var bytes = new byte[40];
        "RIFF"u8.CopyTo(bytes);
        BinaryPrimitives.WriteInt32LittleEndian(bytes.AsSpan(4), bytes.Length - 8);
        "WEBPVP8X"u8.CopyTo(bytes.AsSpan(8));
        BinaryPrimitives.WriteInt32LittleEndian(bytes.AsSpan(16), 10);
        var w = width - 1;
        var h = height - 1;
        bytes[24] = (byte)w;
        bytes[25] = (byte)(w >> 8);
        bytes[26] = (byte)(w >> 16);
        bytes[27] = (byte)h;
        bytes[28] = (byte)(h >> 8);
        bytes[29] = (byte)(h >> 16);
        return bytes;
    }
}
