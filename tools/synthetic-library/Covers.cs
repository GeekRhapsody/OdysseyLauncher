using System.Globalization;

/// <summary>
/// The library's source images: <c>&lt;covers&gt;/jpg/NNNNN.jpg</c>, 10,000 of them. The M1 spike library has them; without it,
/// <see cref="Generate"/> writes stand-ins like its covers: 512×720 baseline JPEGs at quality 90, each a diagonal
/// gradient in hues of its own with stripes, a disc, a title band, noise and its number in large digits, so they
/// decode and compress like art rather than flat colour (about 85 KB each).
/// </summary>
internal static class Covers
{
    public const int Count = 10_000;
    private const int Width = 512;
    private const int Height = 720;

    public static string PathOf(string folder, int n) => Path.Combine(folder, "jpg", n.ToString("D5", CultureInfo.InvariantCulture) + ".jpg");

    /// <summary>The first image the folder lacks, or null if it has all of them.</summary>
    public static string? FirstMissing(string folder)
    {
        for (var n = 0; n < Count; n++)
        {
            var path = PathOf(folder, n);
            if (!File.Exists(path))
            {
                return path;
            }
        }

        return null;
    }

    /// <summary>Writes every image the folder lacks (each through a temporary file, so a stopped run leaves none half-written); returns how many.</summary>
    public static int Generate(string folder)
    {
        Directory.CreateDirectory(Path.Combine(folder, "jpg"));
        var written = 0;
        Parallel.For(0, Count, () => new byte[Width * Height * 3], (n, _, rgb) =>
        {
            var path = PathOf(folder, n);
            if (!File.Exists(path))
            {
                Draw(n, rgb);
                var temporary = path + ".tmp";
                File.WriteAllBytes(temporary, JpegEncoder.Encode(rgb, Width, Height, 90));
                File.Move(temporary, path, overwrite: true);
                Interlocked.Increment(ref written);
            }

            return rgb;
        }, _ => { });
        return written;
    }

    // 3×5 digits, a row of three bits per line, top line in the high bits.
    private static readonly ushort[] Digits =
    [
        0b111_101_101_101_111, 0b010_110_010_010_111, 0b111_001_111_100_111, 0b111_001_111_001_111, 0b101_101_111_001_001,
        0b111_100_111_001_111, 0b111_100_111_101_111, 0b111_001_001_001_001, 0b111_101_111_101_111, 0b111_101_111_001_111,
    ];

    private static void Draw(int n, byte[] rgb)
    {
        var random = new Random(n * 7919 + 17);
        var hue = random.NextSingle();
        var (r1, g1, b1) = Hsv(hue, 0.5f + random.NextSingle() * 0.4f, 0.35f + random.NextSingle() * 0.4f);
        var (r2, g2, b2) = Hsv((hue + 0.08f + random.NextSingle() * 0.25f) % 1, 0.6f + random.NextSingle() * 0.4f, 0.6f + random.NextSingle() * 0.4f);
        var (r3, g3, b3) = Hsv((hue + 0.5f) % 1, 0.7f, 0.9f);
        var angle = random.NextSingle() * MathF.Tau;
        var (dy, dx) = MathF.SinCos(angle);
        var period = 18 + random.Next(40);
        var stripeAngle = random.NextSingle() * MathF.PI;
        var (sy, sx) = MathF.SinCos(stripeAngle);
        var discX = 80 + random.Next(Width - 160);
        var discY = 200 + random.Next(Height - 300);
        var discRadius = 60 + random.Next(120);
        var band = 60 + random.Next(60);
        var noise = (uint)(n * 2654435761u) | 1;

        for (var y = 0; y < Height; y++)
        {
            for (var x = 0; x < Width; x++)
            {
                var t = Math.Clamp(0.5f + ((x - Width / 2f) * dx + (y - Height / 2f) * dy) / 700f, 0, 1);
                var r = r1 + (r2 - r1) * t;
                var g = g1 + (g2 - g1) * t;
                var b = b1 + (b2 - b1) * t;
                if ((int)MathF.Abs(x * sx + y * sy) / period % 2 == 0)
                {
                    (r, g, b) = (r * 0.85f, g * 0.85f, b * 0.85f);
                }

                var ddx = x - discX;
                var ddy = y - discY;
                if (ddx * ddx + ddy * ddy < discRadius * discRadius)
                {
                    (r, g, b) = (r * 0.4f + r3 * 0.6f, g * 0.4f + g3 * 0.6f, b * 0.4f + b3 * 0.6f);
                }

                if (y < band)
                {
                    (r, g, b) = (r * 0.25f + 0.05f, g * 0.25f + 0.05f, b * 0.25f + 0.05f);
                }

                noise ^= noise << 13;
                noise ^= noise >> 17;
                noise ^= noise << 5;
                var grain = (int)(noise % 11) - 5;
                var i = (y * Width + x) * 3;
                rgb[i] = Byte(r * 255 + grain);
                rgb[i + 1] = Byte(g * 255 + grain);
                rgb[i + 2] = Byte(b * 255 + grain);
            }
        }

        // The number: five digits in cells of 20 px, white with a shadow, near the bottom.
        const int Cell = 20;
        var left = (Width - (5 * 4 - 1) * Cell) / 2;
        var top = Height - 5 * Cell - 80;
        var text = n.ToString("D5", CultureInfo.InvariantCulture);
        for (var d = 0; d < text.Length; d++)
        {
            var glyph = Digits[text[d] - '0'];
            for (var row = 0; row < 5; row++)
            {
                for (var column = 0; column < 3; column++)
                {
                    if ((glyph >> (14 - (row * 3 + column)) & 1) != 0)
                    {
                        var x0 = left + (d * 4 + column) * Cell;
                        var y0 = top + row * Cell;
                        Fill(rgb, x0 + 4, y0 + 4, Cell, 0);
                        Fill(rgb, x0, y0, Cell, 240);
                    }
                }
            }
        }
    }

    private static void Fill(byte[] rgb, int x0, int y0, int size, byte value)
    {
        for (var y = y0; y < Math.Min(y0 + size, Height); y++)
        {
            Array.Fill(rgb, value, (y * Width + x0) * 3, Math.Min(size, Width - x0) * 3);
        }
    }

    private static byte Byte(float value) => (byte)Math.Clamp((int)value, 0, 255);

    private static (float R, float G, float B) Hsv(float h, float s, float v)
    {
        var sector = (int)(h * 6) % 6;
        var f = h * 6 - MathF.Floor(h * 6);
        var (p, q, t) = (v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s));
        return sector switch
        {
            0 => (v, t, p),
            1 => (q, v, p),
            2 => (p, v, t),
            3 => (p, q, v),
            4 => (t, p, v),
            _ => (v, p, q),
        };
    }
}

/// <summary>
/// A baseline JPEG encoder (ITU T.81): 4:4:4 YCbCr, the standard quantisation tables scaled by quality, and the
/// standard luminance Huffman tables for all three components. Enough for test images; no package needed.
/// </summary>
internal static class JpegEncoder
{
    private static readonly byte[] LuminanceQuantisation =
    [
        16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99,
    ];

    private static readonly byte[] ChrominanceQuantisation =
    [
        17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99, 24, 26, 56, 99, 99, 99, 99, 99,
        47, 66, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
    ];

    private static readonly byte[] DcBits = [0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0];
    private static readonly byte[] DcValues = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    private static readonly byte[] AcBits = [0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d];

    private static readonly byte[] AcValues =
    [
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
        0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08, 0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
        0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
        0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
        0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
        0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
        0xf9, 0xfa,
    ];

    /// <summary>ZigZag[k] is the k-th coefficient's index in row order.</summary>
    private static readonly byte[] ZigZag = MakeZigZag();

    private static readonly (ushort Code, byte Length)[] DcCodes = MakeCodes(DcBits, DcValues);
    private static readonly (ushort Code, byte Length)[] AcCodes = MakeCodes(AcBits, AcValues);

    /// <summary>The DCT's basis: Basis[u * 8 + x] = C(u) / 2 · cos((2x + 1)uπ / 16).</summary>
    private static readonly float[] Basis = MakeBasis();

    /// <summary>Encodes packed RGB (3 bytes a pixel, top row first).</summary>
    public static byte[] Encode(byte[] rgb, int width, int height, int quality)
    {
        var luminance = Scale(LuminanceQuantisation, quality);
        var chrominance = Scale(ChrominanceQuantisation, quality);
        var output = new MemoryStream(64 * 1024);
        output.Write([0xFF, 0xD8, 0xFF, 0xE0, 0, 16, (byte)'J', (byte)'F', (byte)'I', (byte)'F', 0, 1, 1, 0, 0, 1, 0, 1, 0, 0]);
        output.Write([0xFF, 0xDB, 0, 132, 0]);
        WriteZigZag(output, luminance);
        output.WriteByte(1);
        WriteZigZag(output, chrominance);
        output.Write([0xFF, 0xC0, 0, 17, 8, (byte)(height >> 8), (byte)height, (byte)(width >> 8), (byte)width, 3, 1, 0x11, 0, 2, 0x11, 1, 3, 0x11, 1]);
        output.Write([0xFF, 0xC4, 0, 210, 0x00]);
        output.Write(DcBits);
        output.Write(DcValues);
        output.WriteByte(0x10);
        output.Write(AcBits);
        output.Write(AcValues);
        output.Write([0xFF, 0xDA, 0, 12, 3, 1, 0x00, 2, 0x00, 3, 0x00, 0, 63, 0]);

        var bits = new BitWriter(output);
        Span<float> y = stackalloc float[64];
        Span<float> cb = stackalloc float[64];
        Span<float> cr = stackalloc float[64];
        Span<float> scratch = stackalloc float[64];
        int previousY = 0, previousCb = 0, previousCr = 0;
        for (var by = 0; by < height; by += 8)
        {
            for (var bx = 0; bx < width; bx += 8)
            {
                for (var row = 0; row < 8; row++)
                {
                    var sourceY = Math.Min(by + row, height - 1);
                    for (var column = 0; column < 8; column++)
                    {
                        var i = (sourceY * width + Math.Min(bx + column, width - 1)) * 3;
                        float r = rgb[i], g = rgb[i + 1], b = rgb[i + 2];
                        var k = row * 8 + column;
                        y[k] = 0.299f * r + 0.587f * g + 0.114f * b - 128;
                        cb[k] = -0.168736f * r - 0.331264f * g + 0.5f * b;
                        cr[k] = 0.5f * r - 0.418688f * g - 0.081312f * b;
                    }
                }

                previousY = EncodeBlock(bits, y, scratch, luminance, previousY);
                previousCb = EncodeBlock(bits, cb, scratch, chrominance, previousCb);
                previousCr = EncodeBlock(bits, cr, scratch, chrominance, previousCr);
            }
        }

        bits.Flush();
        output.Write([0xFF, 0xD9]);
        return output.ToArray();
    }

    private static int EncodeBlock(BitWriter bits, Span<float> block, Span<float> scratch, byte[] quantisation, int previousDc)
    {
        // Rows, then columns: scratch[y * 8 + u] = Σx Basis[u, x] · block[y, x]; block[v * 8 + u] = Σy Basis[v, y] · scratch[y, u].
        for (var row = 0; row < 8; row++)
        {
            for (var u = 0; u < 8; u++)
            {
                var sum = 0f;
                for (var x = 0; x < 8; x++)
                {
                    sum += Basis[u * 8 + x] * block[row * 8 + x];
                }

                scratch[row * 8 + u] = sum;
            }
        }

        for (var v = 0; v < 8; v++)
        {
            for (var u = 0; u < 8; u++)
            {
                var sum = 0f;
                for (var row = 0; row < 8; row++)
                {
                    sum += Basis[v * 8 + row] * scratch[row * 8 + u];
                }

                block[v * 8 + u] = sum;
            }
        }

        var dc = (int)MathF.Round(block[0] / quantisation[0]);
        WriteCoded(bits, DcCodes, 0, dc - previousDc);
        var run = 0;
        for (var k = 1; k < 64; k++)
        {
            var index = ZigZag[k];
            var coefficient = Math.Clamp((int)MathF.Round(block[index] / quantisation[index]), -1023, 1023);
            if (coefficient == 0)
            {
                run++;
                continue;
            }

            for (; run > 15; run -= 16)
            {
                bits.Write(AcCodes[0xF0].Code, AcCodes[0xF0].Length);
            }

            WriteCoded(bits, AcCodes, run << 4, coefficient);
            run = 0;
        }

        if (run > 0)
        {
            bits.Write(AcCodes[0x00].Code, AcCodes[0x00].Length);
        }

        return dc;
    }

    /// <summary>A value as its size category's code (plus the run, for AC) then the value's bits (one's complement if negative).</summary>
    private static void WriteCoded(BitWriter bits, (ushort Code, byte Length)[] codes, int runBits, int value)
    {
        var magnitude = Math.Abs(value);
        var size = magnitude == 0 ? 0 : 32 - int.LeadingZeroCount(magnitude);
        var (code, length) = codes[runBits | size];
        bits.Write(code, length);
        if (size > 0)
        {
            bits.Write((value < 0 ? value - 1 : value) & ((1 << size) - 1), size);
        }
    }

    private static byte[] Scale(byte[] table, int quality)
    {
        var scale = quality < 50 ? 5000 / quality : 200 - quality * 2;
        var scaled = new byte[64];
        for (var i = 0; i < 64; i++)
        {
            scaled[i] = (byte)Math.Clamp((table[i] * scale + 50) / 100, 1, 255);
        }

        return scaled;
    }

    private static void WriteZigZag(Stream output, byte[] table)
    {
        for (var k = 0; k < 64; k++)
        {
            output.WriteByte(table[ZigZag[k]]);
        }
    }

    private static byte[] MakeZigZag()
    {
        var order = new byte[64];
        var k = 0;
        for (var sum = 0; sum < 15; sum++)
        {
            var low = Math.Max(0, sum - 7);
            var high = Math.Min(sum, 7);
            for (var j = 0; j <= high - low; j++)
            {
                var row = sum % 2 == 1 ? low + j : high - j;
                order[k++] = (byte)(row * 8 + sum - row);
            }
        }

        return order;
    }

    /// <summary>Canonical codes (T.81 Annex C), indexed by symbol. Checks the table covers every symbol it can be asked for.</summary>
    private static (ushort Code, byte Length)[] MakeCodes(byte[] counts, byte[] values)
    {
        var codes = new (ushort, byte)[256];
        var code = 0;
        var k = 0;
        for (var length = 1; length <= 16; length++)
        {
            for (var i = 0; i < counts[length - 1]; i++)
            {
                codes[values[k++]] = ((ushort)code++, (byte)length);
            }

            code <<= 1;
        }

        if (k != values.Length || values.Distinct().Count() != values.Length)
        {
            throw new InvalidOperationException("A Huffman table's counts don't match its symbols.");
        }

        return codes;
    }

    private static float[] MakeBasis()
    {
        var basis = new float[64];
        for (var u = 0; u < 8; u++)
        {
            for (var x = 0; x < 8; x++)
            {
                basis[u * 8 + x] = (u == 0 ? MathF.Sqrt(0.5f) : 1) / 2 * MathF.Cos((2 * x + 1) * u * MathF.PI / 16);
            }
        }

        return basis;
    }

    /// <summary>The entropy-coded segment's bits, most significant first, with a 0 stuffed after every 0xFF byte.</summary>
    private sealed class BitWriter(Stream output)
    {
        private uint _buffer;
        private int _count;

        public void Write(int bits, int length)
        {
            _buffer = (_buffer << length) | (uint)(bits & ((1 << length) - 1));
            _count += length;
            while (_count >= 8)
            {
                var b = (byte)(_buffer >> (_count - 8));
                output.WriteByte(b);
                if (b == 0xFF)
                {
                    output.WriteByte(0);
                }

                _count -= 8;
            }
        }

        /// <summary>Pads the last byte with ones.</summary>
        public void Flush()
        {
            if (_count > 0)
            {
                Write(0x7F, 8 - _count);
            }
        }
    }
}
