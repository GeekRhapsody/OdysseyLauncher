using System.Buffers.Binary;
using System.Diagnostics;
using BCnEncoder.Decoder;
using BCnEncoder.Shared;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Media;

public sealed class DerivativeTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    /// <summary>The platform's decoder (WIC on Windows); the test is skipped where there's none.</summary>
    private static IImageDecoder Decoder()
    {
        var decoder = PlatformServices.CreateImageDecoder();
        Assert.SkipWhen(decoder is null, "no image decoder on this platform");
        return decoder;
    }

    /// <summary>Left half red, right half blue, with a green stripe along the top: easy to check after scaling.</summary>
    private static (byte, byte, byte, byte) Pattern(int x, int y, int width) =>
        y < 20 ? ((byte)0, (byte)200, (byte)0, (byte)255) : x < width / 2 ? ((byte)220, (byte)30, (byte)30, (byte)255) : ((byte)30, (byte)30, (byte)220, (byte)255);

    private string WritePng(string name, int width, int height)
    {
        var path = _dir.Combine(name);
        File.WriteAllBytes(path, TestImages.RealPng(width, height, (x, y) => Pattern(x, y, width)));
        return path;
    }

    [Fact]
    public void The_Windows_decoder_squeezes_the_whole_image_to_the_requested_size()
    {
        var path = WritePng("cover.png", 300, 420);
        var pixels = new byte[512 * 512 * 4];

        Assert.True(Decoder().TryDecodeScaled(path, 512, 512, pixels, out var error), error);

        static (int R, int G, int B) At(byte[] p, int x, int y) => (p[((y * 512) + x) * 4], p[((y * 512) + x) * 4 + 1], p[((y * 512) + x) * 4 + 2]);
        Assert.Equal((220, 30, 30), At(pixels, 100, 300));
        Assert.Equal((30, 30, 220), At(pixels, 400, 300));
        Assert.Equal((0, 200, 0), At(pixels, 256, 5));
        Assert.Equal(255, pixels[3]);
    }

    [Fact]
    public void The_Windows_decoder_reports_a_file_that_isnt_an_image()
    {
        var path = _dir.File("not-an-image.png", "<html>error</html>");

        Assert.False(Decoder().TryDecodeScaled(path, 512, 512, new byte[512 * 512 * 4], out var error));
        Assert.NotNull(error);
    }

    [Fact]
    public void A_derivative_is_a_512_BC7_DDS_with_ten_mips_in_M1s_layout()
    {
        var pixels = new byte[512 * 512 * 4];
        for (var y = 0; y < 512; y++)
        {
            for (var x = 0; x < 512; x++)
            {
                var (r, g, b, a) = Pattern(x, y, 512);
                var i = ((y * 512) + x) * 4;
                (pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]) = (r, g, b, a);
            }
        }

        var original = pixels.ToArray();
        using var output = new MemoryStream();
        var stopwatch = Stopwatch.StartNew();
        Bc7DdsWriter.Encode(pixels, output);
        TestContext.Current.SendDiagnosticMessage($"BC7 encode of 512² with mips: {stopwatch.Elapsed.TotalMilliseconds:0} ms");
        var dds = output.ToArray();

        Assert.Equal(Bc7DdsWriter.FileLength, dds.Length);
        Assert.Equal(349_700, dds.Length);
        Assert.True(dds.AsSpan(0, 4).SequenceEqual("DDS "u8));
        Assert.Equal(512, BinaryPrimitives.ReadInt32LittleEndian(dds.AsSpan(12)));
        Assert.Equal(512, BinaryPrimitives.ReadInt32LittleEndian(dds.AsSpan(16)));
        Assert.Equal(10, BinaryPrimitives.ReadInt32LittleEndian(dds.AsSpan(28)));
        Assert.True(dds.AsSpan(84, 4).SequenceEqual("DX10"u8));
        Assert.Equal(98, BinaryPrimitives.ReadInt32LittleEndian(dds.AsSpan(128)));

        // The top level decodes back to the picture.
        var decoded = new BcDecoder().DecodeRaw(dds.AsSpan(148, 512 * 512).ToArray(), 512, 512, CompressionFormat.Bc7);
        long squaredError = 0;
        for (var i = 0; i < decoded.Length; i++)
        {
            var o = i * 4;
            squaredError += Square(decoded[i].r - original[o]) + Square(decoded[i].g - original[o + 1]) + Square(decoded[i].b - original[o + 2]);
        }

        var mse = squaredError / (decoded.Length * 3.0);
        Assert.True(mse < 4, $"mean squared error {mse:0.00}");
    }

    /// <summary>
    /// BCnEncoder.Net's decoder is the independent check that our blocks are valid BC7. A gradient in two directions
    /// can't lie on mode 6's one line per block, which bounds its error; pure noise isn't tested, since no single-line
    /// mode can represent it.
    /// </summary>
    [Theory]
    [InlineData("gradient", 8.0)]
    [InlineData("grainy", 40.0)]
    [InlineData("flat", 0.5)]
    [InlineData("alpha edges", 60.0)]
    public void Mode_6_blocks_decode_close_to_the_source(string kind, double maxMeanSquaredError)
    {
        var random = new Random(7);
        var pixels = new byte[64 * 64 * 4];
        for (var y = 0; y < 64; y++)
        {
            for (var x = 0; x < 64; x++)
            {
                var i = ((y * 64) + x) * 4;
                (byte, byte, byte, byte) c = kind switch
                {
                    "gradient" => ((byte)(x * 4), (byte)(y * 4), (byte)(255 - (x * 2)), 255),
                    "grainy" => ((byte)(100 + random.Next(-12, 13)), (byte)(80 + (y * 2) + random.Next(-12, 13)), (byte)(60 + random.Next(-12, 13)), 255),
                    "flat" => (90, 140, 200, 255),
                    _ => ((byte)(x * 4), 60, 200, (byte)(((x / 3) + (y / 5)) % 2 == 0 ? 255 : 0)),
                };
                (pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]) = c;
            }
        }

        var blocks = new byte[16 * 16 * 16];
        Bc7Encoder.EncodeImage(pixels, 64, 64, blocks);
        var decoded = new BcDecoder().DecodeRaw(blocks, 64, 64, CompressionFormat.Bc7);

        double squared = 0;
        for (var i = 0; i < decoded.Length; i++)
        {
            var o = i * 4;
            squared += Square(decoded[i].r - pixels[o]) + Square(decoded[i].g - pixels[o + 1])
                + Square(decoded[i].b - pixels[o + 2]) + Square(decoded[i].a - pixels[o + 3]);
        }

        var mse = squared / (decoded.Length * 4.0);
        TestContext.Current.SendDiagnosticMessage($"{kind}: mean squared error {mse:0.00}");
        Assert.True(mse <= maxMeanSquaredError, $"{kind}: mean squared error {mse:0.00}");
    }

    /// <summary>
    /// The decoder is the oracle for the whole block format: for every block, the error BCnEncoder.Net's decoder
    /// measures must equal, exactly, the error the encoder believes it made. That checks both modes' bit layout,
    /// the partition and anchor tables, the weights and the endpoint expansion.
    /// </summary>
    [Fact]
    public void Every_block_decodes_exactly_as_the_encoder_predicted_in_both_modes()
    {
        var random = new Random(11);
        var modes = new int[8];
        for (var trial = 0; trial < 3000; trial++)
        {
            var texels = new byte[64];
            var kind = trial % 4;
            var colours = new (byte R, byte G, byte B)[3];
            for (var c = 0; c < 3; c++)
            {
                colours[c] = ((byte)random.Next(256), (byte)random.Next(256), (byte)random.Next(256));
            }

            var partition = Bc7Encoder.Partitions2[random.Next(64)];
            for (var i = 0; i < 16; i++)
            {
                var (r, g, b) = kind switch
                {
                    0 => colours[(partition >> i) & 1],                                     // two flat regions: mode 1 territory
                    1 => ((byte)random.Next(256), (byte)random.Next(256), (byte)random.Next(256)),
                    2 => ((byte)((i % 4) * 60), (byte)((i / 4) * 60), colours[0].B),        // a gradient: mode 6
                    _ => colours[i < 8 ? 0 : 1],
                };
                (texels[i * 4], texels[(i * 4) + 1], texels[(i * 4) + 2]) = (r, g, b);
                texels[(i * 4) + 3] = kind == 3 && i % 5 == 0 ? (byte)random.Next(256) : (byte)255;
            }

            var block = new byte[16];
            Bc7Encoder.EncodeBlock(texels, block, out var predicted);
            modes[System.Numerics.BitOperations.TrailingZeroCount(block[0] | 0x100)]++;

            var decoded = new BcDecoder().DecodeRaw(block, 4, 4, CompressionFormat.Bc7);
            long measured = 0;
            for (var i = 0; i < 16; i++)
            {
                measured += Square(decoded[i].r - texels[i * 4]) + Square(decoded[i].g - texels[(i * 4) + 1])
                    + Square(decoded[i].b - texels[(i * 4) + 2]) + Square(decoded[i].a - texels[(i * 4) + 3]);
            }

            Assert.True(predicted == measured, $"trial {trial} (kind {kind}, mode {System.Numerics.BitOperations.TrailingZeroCount(block[0] | 0x100)}): predicted {predicted}, decoded {measured}");
        }

        Assert.True(modes[1] > 500, $"mode 1 blocks: {modes[1]}");
        Assert.True(modes[6] > 500, $"mode 6 blocks: {modes[6]}");
        Assert.Equal(3000, modes[1] + modes[6]);
    }

    [Fact]
    public void Each_two_subset_anchor_lies_in_its_subset_and_texel_0_in_the_first()
    {
        for (var partition = 0; partition < 64; partition++)
        {
            var mask = Bc7Encoder.Partitions2[partition];
            Assert.Equal(0, mask & 1);
            Assert.Equal(1, (mask >> Bc7Encoder.Anchors2[partition]) & 1);
        }
    }

    [Fact]
    public void The_smallest_mips_repeat_their_edge_pixels()
    {
        byte[] pixels = [10, 20, 30, 255, 200, 100, 50, 255, 10, 20, 30, 255, 200, 100, 50, 255];
        var block = new byte[16];

        Bc7Encoder.EncodeImage(pixels, 2, 2, block);

        var decoded = new BcDecoder().DecodeRaw(block, 4, 4, CompressionFormat.Bc7);
        Assert.InRange(decoded[0].r, 8, 12);
        Assert.InRange(decoded[1].r, 198, 202);
        Assert.InRange(decoded[3].r, 198, 202);
        Assert.InRange(decoded[15].r, 198, 202);
    }

    [Fact]
    public void The_baker_writes_the_derivative_of_a_file()
    {
        var source = WritePng("cover.png", 640, 900);
        var destination = _dir.Combine("cache", "textures", "x.dds");

        Assert.True(new DerivativeBaker(Decoder()).TryBake(source, destination, out var error), error);

        Assert.Equal(Bc7DdsWriter.FileLength, new FileInfo(destination).Length);
        Assert.Empty(Directory.GetFiles(Path.GetDirectoryName(destination)!, "*.tmp-*"));
    }

    private static long Square(int value) => (long)value * value;
}
