using System.Buffers.Binary;
using System.Runtime.CompilerServices;

namespace Launcher.Core.Media;

/// <summary>
/// A fast BC7 encoder using two modes. Mode 6 (one subset, RGBA endpoints of 7 bits plus a p-bit each, 4-bit indices)
/// is BC7's general-purpose mode and suits most of a photographic cover. Where it fits an opaque block badly (an
/// edge between two colour regions: text, outlines), mode 1 (two subsets from 64 partitions,
/// <see cref="Bc7Encoder.EncodeMode1"/>) is tried and kept if it's better. The four other modes aren't used.
/// <para>
/// Per block: endpoints from the principal axis of the colours, then least-squares refinement over the chosen
/// indices, trying each p-bit combination. No allocations. About 0.44 s for a real 512² cover with its mips on the
/// Deck; BCnEncoder.Net took about 10 s (docs/perf/m4-scraping.md), too slow for thousands.
/// </para>
/// </summary>
public static partial class Bc7Encoder
{
    private static ReadOnlySpan<int> Weights => [0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64];

    /// <summary>Encodes an RGBA image (rows top to bottom) into BC7 blocks, in row order of blocks, 16 bytes each.</summary>
    /// <remarks>Sizes that aren't a multiple of 4 (the 2×2 and 1×1 mips) repeat their edge pixels to fill the block.</remarks>
    public static void EncodeImage(ReadOnlySpan<byte> rgba, int width, int height, Span<byte> blocks)
    {
        var blocksX = (width + 3) / 4;
        var blocksY = (height + 3) / 4;
        if (blocks.Length < blocksX * blocksY * 16)
        {
            throw new ArgumentException("the output is too small", nameof(blocks));
        }

        for (var by = 0; by < blocksY; by++)
        {
            EncodeBlockRow(rgba, width, height, by, blocks.Slice(by * blocksX * 16, blocksX * 16));
        }
    }

    /// <summary>Encodes one row of blocks (4 rows of pixels, <paramref name="blockRow"/> counting from the top).</summary>
    /// <param name="blocks">(width + 3) / 4 × 16 bytes.</param>
    public static void EncodeBlockRow(ReadOnlySpan<byte> rgba, int width, int height, int blockRow, Span<byte> blocks)
    {
        var blocksX = (width + 3) / 4;
        Span<byte> texels = stackalloc byte[64];
        for (var bx = 0; bx < blocksX; bx++)
        {
            for (var y = 0; y < 4; y++)
            {
                var sy = Math.Min((blockRow * 4) + y, height - 1);
                for (var x = 0; x < 4; x++)
                {
                    var sx = Math.Min((bx * 4) + x, width - 1);
                    rgba.Slice(((sy * width) + sx) * 4, 4).CopyTo(texels[(((y * 4) + x) * 4)..]);
                }
            }

            EncodeBlock(texels, blocks.Slice(bx * 16, 16));
        }
    }

    /// <summary>Encodes 16 RGBA texels (row-major) into one 16-byte mode 6 block.</summary>
    public static void EncodeBlock(ReadOnlySpan<byte> texels, Span<byte> block) => EncodeBlock(texels, block, out _);

    /// <summary>As <see cref="EncodeBlock(ReadOnlySpan{byte}, Span{byte})"/>, also giving the squared error the block decodes with.</summary>
    internal static void EncodeBlock(ReadOnlySpan<byte> texels, Span<byte> block, out long error)
    {
        error = EncodeMode6(texels, block);
        if (error <= Mode1Threshold || !IsOpaque(texels))
        {
            return;
        }

        Span<byte> candidate = stackalloc byte[16];
        var mode1 = EncodeMode1(texels, candidate);
        if (mode1 < error)
        {
            candidate.CopyTo(block);
            error = mode1;
        }
    }

    /// <summary>
    /// Mode 6 error (summed over the block's 16 texels and 4 channels) above which mode 1 is tried: an average
    /// difference of about 3 per channel. Below it the block is smooth enough that partitions can't win much.
    /// </summary>
    private const long Mode1Threshold = 16 * 4 * 9;

    private static bool IsOpaque(ReadOnlySpan<byte> texels)
    {
        for (var i = 3; i < 64; i += 4)
        {
            if (texels[i] != 255)
            {
                return false;
            }
        }

        return true;
    }

    /// <summary>Encodes as mode 6 and returns the squared error.</summary>
    private static long EncodeMode6(ReadOnlySpan<byte> texels, Span<byte> block)
    {
        Span<float> p = stackalloc float[64];
        for (var i = 0; i < 64; i++)
        {
            p[i] = texels[i];
        }

        // Principal axis of the colours, by power iteration on their covariance.
        Span<float> mean = stackalloc float[4];
        for (var i = 0; i < 16; i++)
        {
            for (var c = 0; c < 4; c++)
            {
                mean[c] += p[(i * 4) + c];
            }
        }

        for (var c = 0; c < 4; c++)
        {
            mean[c] /= 16f;
        }

        Span<float> cov = stackalloc float[16];
        for (var i = 0; i < 16; i++)
        {
            for (var a = 0; a < 4; a++)
            {
                var da = p[(i * 4) + a] - mean[a];
                for (var b = a; b < 4; b++)
                {
                    cov[(a * 4) + b] += da * (p[(i * 4) + b] - mean[b]);
                }
            }
        }

        for (var a = 0; a < 4; a++)
        {
            for (var b = 0; b < a; b++)
            {
                cov[(a * 4) + b] = cov[(b * 4) + a];
            }
        }

        Span<float> axis = stackalloc float[4] { 0.5f, 0.6f, 0.5f, 0.3f };
        Span<float> next = stackalloc float[4];
        for (var iteration = 0; iteration < 6; iteration++)
        {
            float length = 0;
            for (var a = 0; a < 4; a++)
            {
                float sum = 0;
                for (var b = 0; b < 4; b++)
                {
                    sum += cov[(a * 4) + b] * axis[b];
                }

                next[a] = sum;
                length += sum * sum;
            }

            if (length < 1e-12f)
            {
                break;
            }

            length = MathF.Sqrt(length);
            for (var a = 0; a < 4; a++)
            {
                axis[a] = next[a] / length;
            }
        }

        float lo = float.MaxValue, hi = float.MinValue;
        for (var i = 0; i < 16; i++)
        {
            float t = 0;
            for (var c = 0; c < 4; c++)
            {
                t += (p[(i * 4) + c] - mean[c]) * axis[c];
            }

            lo = Math.Min(lo, t);
            hi = Math.Max(hi, t);
        }

        Span<float> e0 = stackalloc float[4];
        Span<float> e1 = stackalloc float[4];
        for (var c = 0; c < 4; c++)
        {
            e0[c] = mean[c] + (axis[c] * lo);
            e1[c] = mean[c] + (axis[c] * hi);
        }

        Span<int> bestQ0 = stackalloc int[4];
        Span<int> bestQ1 = stackalloc int[4];
        Span<byte> bestIndices = stackalloc byte[16];
        int bestP0 = 0, bestP1 = 0;
        var bestError = long.MaxValue;
        Span<int> q0 = stackalloc int[4];
        Span<int> q1 = stackalloc int[4];
        Span<byte> indices = stackalloc byte[16];

        for (var round = 0; round < 3; round++)
        {
            var improved = false;
            for (var pbits = 0; pbits < 4; pbits++)
            {
                var p0 = pbits & 1;
                var p1 = pbits >> 1;
                for (var c = 0; c < 4; c++)
                {
                    q0[c] = Quantise(e0[c], p0);
                    q1[c] = Quantise(e1[c], p1);
                }

                var error = Assign(texels, q0, p0, q1, p1, indices);
                if (error < bestError)
                {
                    bestError = error;
                    q0.CopyTo(bestQ0);
                    q1.CopyTo(bestQ1);
                    indices.CopyTo(bestIndices);
                    (bestP0, bestP1) = (p0, p1);
                    improved = true;
                }
            }

            if (bestError == 0 || (round > 0 && !improved) || !Refine(p, bestIndices, e0, e1))
            {
                break;
            }
        }

        Pack(bestQ0, bestP0, bestQ1, bestP1, bestIndices, block);
        return bestError;
    }

    /// <summary>The 7-bit value that, with p-bit <paramref name="p"/>, comes closest to <paramref name="value"/>.</summary>
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static int Quantise(float value, int p) => Math.Clamp((int)MathF.Round((value - p) / 2f), 0, 127);

    /// <summary>Picks each texel's nearest palette entry. Returns the total squared error.</summary>
    private static long Assign(ReadOnlySpan<byte> texels, ReadOnlySpan<int> q0, int p0, ReadOnlySpan<int> q1, int p1, Span<byte> indices)
    {
        Span<int> palette = stackalloc int[64];
        var weights = Weights;
        for (var c = 0; c < 4; c++)
        {
            var a = (q0[c] << 1) | p0;
            var b = (q1[c] << 1) | p1;
            for (var w = 0; w < 16; w++)
            {
                palette[(w * 4) + c] = (((64 - weights[w]) * a) + (weights[w] * b) + 32) >> 6;
            }
        }

        long total = 0;
        for (var i = 0; i < 16; i++)
        {
            int r = texels[i * 4], g = texels[(i * 4) + 1], b = texels[(i * 4) + 2], al = texels[(i * 4) + 3];
            var best = int.MaxValue;
            var bestIndex = 0;
            for (var w = 0; w < 16; w++)
            {
                int dr = palette[w * 4] - r, dg = palette[(w * 4) + 1] - g, db = palette[(w * 4) + 2] - b, da = palette[(w * 4) + 3] - al;
                var d = (dr * dr) + (dg * dg) + (db * db) + (da * da);
                if (d < best)
                {
                    best = d;
                    bestIndex = w;
                }
            }

            indices[i] = (byte)bestIndex;
            total += best;
        }

        return total;
    }

    /// <summary>Least-squares endpoints for fixed indices. False when the indices can't determine them (all equal).</summary>
    private static bool Refine(ReadOnlySpan<float> p, ReadOnlySpan<byte> indices, Span<float> e0, Span<float> e1)
    {
        var weights = Weights;
        float aa = 0, ab = 0, bb = 0;
        Span<float> x0 = stackalloc float[4];
        Span<float> x1 = stackalloc float[4];
        for (var i = 0; i < 16; i++)
        {
            var t = weights[indices[i]] / 64f;
            var s = 1f - t;
            aa += s * s;
            ab += s * t;
            bb += t * t;
            for (var c = 0; c < 4; c++)
            {
                x0[c] += s * p[(i * 4) + c];
                x1[c] += t * p[(i * 4) + c];
            }
        }

        var det = (aa * bb) - (ab * ab);
        if (MathF.Abs(det) < 1e-6f)
        {
            return false;
        }

        for (var c = 0; c < 4; c++)
        {
            e0[c] = Math.Clamp(((bb * x0[c]) - (ab * x1[c])) / det, 0f, 255f);
            e1[c] = Math.Clamp(((aa * x1[c]) - (ab * x0[c])) / det, 0f, 255f);
        }

        return true;
    }

    /// <summary>
    /// Writes a mode 6 block, least significant bit first: mode (0000001), R0 R1 G0 G1 B0 B1 A0 A1 (7 bits each),
    /// P0, P1, then the indices, the first (the anchor) with 3 bits. An anchor index of 8 or more is made to fit by
    /// swapping the endpoints and inverting every index.
    /// </summary>
    private static void Pack(Span<int> q0, int p0, Span<int> q1, int p1, Span<byte> indices, Span<byte> block)
    {
        if (indices[0] >= 8)
        {
            for (var c = 0; c < 4; c++)
            {
                (q0[c], q1[c]) = (q1[c], q0[c]);
            }

            (p0, p1) = (p1, p0);
            for (var i = 0; i < 16; i++)
            {
                indices[i] = (byte)(15 - indices[i]);
            }
        }

        UInt128 bits = 1u << 6;
        var at = 7;
        for (var c = 0; c < 4; c++)
        {
            bits |= (UInt128)(uint)q0[c] << at;
            at += 7;
            bits |= (UInt128)(uint)q1[c] << at;
            at += 7;
        }

        bits |= (UInt128)(uint)p0 << at++;
        bits |= (UInt128)(uint)p1 << at++;
        bits |= (UInt128)indices[0] << at;
        at += 3;
        for (var i = 1; i < 16; i++)
        {
            bits |= (UInt128)indices[i] << at;
            at += 4;
        }

        BinaryPrimitives.WriteUInt64LittleEndian(block, (ulong)bits);
        BinaryPrimitives.WriteUInt64LittleEndian(block[8..], (ulong)(bits >> 64));
    }
}
