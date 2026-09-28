using System.Buffers.Binary;
using System.Diagnostics;

namespace Launcher.Core.Media;

/// <summary>
/// Decodes an image file into RGBA pixels. The OS supplies the codecs (Windows: WIC), so Core needs no image
/// package; <see cref="Platform.PlatformServices.CreateImageDecoder"/> picks the implementation.
/// Implementations must be safe to call from several threads at once.
/// </summary>
public interface IImageDecoder
{
    /// <summary>
    /// Decodes <paramref name="path"/> and scales the whole image to <paramref name="width"/> × <paramref name="height"/>
    /// (ignoring its aspect ratio), as 8-bit RGBA with straight alpha, rows top to bottom.
    /// </summary>
    /// <param name="rgba">At least width × height × 4 bytes.</param>
    /// <param name="error">Why it failed, for the log; null on success.</param>
    bool TryDecodeScaled(string path, int width, int height, Span<byte> rgba, out string? error);
}

/// <summary>
/// Writes the grid's cover derivative (A3): the whole image squeezed to 512×512, BC7 (<see cref="Bc7Encoder"/>) with a full mip
/// chain of 10 levels, in a DDS file with a DX10 header, exactly the layout M1 measured and M5's streamer reads.
/// </summary>
public static class Bc7DdsWriter
{
    public const int Size = TextureDerivatives.Size;
    public const int MipLevels = 10;

    /// <summary>148 bytes of header plus 349,552 of blocks: the same file size as M1's derivatives.</summary>
    public const int FileLength = HeaderLength + 349_552;

    private const int HeaderLength = 148;

    /// <summary>
    /// The header of every derivative: "DDS ", a 512×512 surface with 10 mips, pixel format "DX10", then
    /// DXGI_FORMAT_BC7_UNORM (98) as a 2D texture. Byte for byte the header of M1's derivatives, which Godot's
    /// <c>Image.LoadDdsFromBuffer</c> reads in exports.
    /// </summary>
    private static readonly byte[] Header = BuildHeader();

    /// <summary>Encodes 512×512 RGBA pixels into a complete DDS file, written to <paramref name="output"/>.</summary>
    /// <param name="rgba">512 × 512 × 4 bytes; used as scratch for the smaller mips, so its content is lost.</param>
    public static void Encode(Span<byte> rgba, Stream output)
    {
        ArgumentNullException.ThrowIfNull(output);
        if (rgba.Length < Size * Size * 4)
        {
            throw new ArgumentException("needs 512×512 RGBA pixels", nameof(rgba));
        }

        output.Write(Header);
        var at = HeaderLength;
        Span<byte> row = stackalloc byte[Size / 4 * 16];
        var size = Size;
        for (var level = 0; level < MipLevels; level++)
        {
            var blocksX = (size + 3) / 4;
            for (var blockRow = 0; blockRow < (size + 3) / 4; blockRow++)
            {
                var blocks = row[..(blocksX * 16)];
                Bc7Encoder.EncodeBlockRow(rgba, size, size, blockRow, blocks);
                output.Write(blocks);
                at += blocks.Length;
            }

            if (size > 1)
            {
                HalveInPlace(rgba, size);
                size /= 2;
            }
        }

        Debug.Assert(at == FileLength, "a BC7 mip chain of 512² is 349,552 bytes");
    }

    /// <summary>A 2×2 box filter: the top-left quarter of <paramref name="rgba"/> becomes the image at half size.</summary>
    private static void HalveInPlace(Span<byte> rgba, int size)
    {
        var half = size / 2;
        var stride = size * 4;
        for (var y = 0; y < half; y++)
        {
            for (var x = 0; x < half; x++)
            {
                var a = (2 * y * stride) + (2 * x * 4);
                var b = a + stride;
                var o = ((y * half) + x) * 4;
                for (var c = 0; c < 4; c++)
                {
                    rgba[o + c] = (byte)((rgba[a + c] + rgba[a + 4 + c] + rgba[b + c] + rgba[b + 4 + c] + 2) >> 2);
                }
            }
        }
    }

    private static byte[] BuildHeader()
    {
        var h = new byte[HeaderLength];
        var s = h.AsSpan();
        "DDS "u8.CopyTo(s);
        BinaryPrimitives.WriteInt32LittleEndian(s[4..], 124);                  // dwSize
        BinaryPrimitives.WriteInt32LittleEndian(s[8..], 0x000A100F);           // caps, height, width, pitch, pixel format, mip count, linear size
        BinaryPrimitives.WriteInt32LittleEndian(s[12..], Size);                // height
        BinaryPrimitives.WriteInt32LittleEndian(s[16..], Size);                // width
        BinaryPrimitives.WriteInt32LittleEndian(s[20..], Size * Size);         // linear size of the top level (1 byte per pixel in BC7)
        BinaryPrimitives.WriteInt32LittleEndian(s[28..], MipLevels);
        BinaryPrimitives.WriteInt32LittleEndian(s[76..], 32);                  // pixel format size
        BinaryPrimitives.WriteInt32LittleEndian(s[80..], 4);                   // DDPF_FOURCC
        "DX10"u8.CopyTo(s[84..]);
        BinaryPrimitives.WriteInt32LittleEndian(s[108..], 0x00080000);         // caps, as M1's files have them
        BinaryPrimitives.WriteInt32LittleEndian(s[128..], 98);                 // DXGI_FORMAT_BC7_UNORM
        BinaryPrimitives.WriteInt32LittleEndian(s[132..], 3);                  // D3D10_RESOURCE_DIMENSION_TEXTURE2D
        BinaryPrimitives.WriteInt32LittleEndian(s[140..], 1);                  // array size
        return h;
    }
}

/// <summary>
/// Bakes cover derivatives: decode and squeeze to 512² (<see cref="IImageDecoder"/>), encode to BC7, and write the
/// file atomically. CPU-heavy and synchronous: callers run it on their own worker threads. Safe to call from
/// several threads at once; each thread keeps one pixel buffer, so a bake allocates no large pixel arrays.
/// </summary>
public sealed class DerivativeBaker(IImageDecoder decoder)
{
    [ThreadStatic]
    private static byte[]? t_pixels;

    /// <summary>Writes the derivative of <paramref name="sourcePath"/> to <paramref name="destinationPath"/>.</summary>
    /// <param name="error">Why it failed, for the log; null on success.</param>
    public bool TryBake(string sourcePath, string destinationPath, out string? error)
    {
        ArgumentNullException.ThrowIfNull(sourcePath);
        ArgumentNullException.ThrowIfNull(destinationPath);
        var pixels = t_pixels ??= new byte[Bc7DdsWriter.Size * Bc7DdsWriter.Size * 4];
        if (!decoder.TryDecodeScaled(sourcePath, Bc7DdsWriter.Size, Bc7DdsWriter.Size, pixels, out error))
        {
            return false;
        }

        Directory.CreateDirectory(Path.GetDirectoryName(destinationPath)!);
        var temp = destinationPath + ".tmp-" + Environment.CurrentManagedThreadId.ToString(System.Globalization.CultureInfo.InvariantCulture);
        try
        {
            using (var stream = new FileStream(temp, FileMode.Create, FileAccess.Write, FileShare.None, 64 * 1024))
            {
                Bc7DdsWriter.Encode(pixels, stream);
            }

            File.Move(temp, destinationPath, overwrite: true);
        }
        catch (IOException e)
        {
            File.Delete(temp);
            error = e.Message;
            return false;
        }

        error = null;
        return true;
    }
}
