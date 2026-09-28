using System.Buffers.Binary;

namespace Launcher.Core.Media;

/// <summary>
/// BC7 mode 1, for opaque blocks where mode 6's single line fits badly: two subsets chosen from BC7's 64
/// partitions, each with RGB endpoints of 6 bits plus a p-bit shared by the subset, and 3-bit indices. Blocks with
/// an edge between two colour regions (text, outlines, logos) are what it's for.
/// <para>
/// Each partition is scored by how far its two subsets' colours lie from their own principal axes; the best few
/// are then encoded in full and the best result kept.
/// </para>
/// </summary>
public static partial class Bc7Encoder
{
    /// <summary>BC7's two-subset partitions: bit i set means texel i (row-major) is in subset 1.</summary>
    internal static ReadOnlySpan<ushort> Partitions2 =>
    [
        0xCCCC, 0x8888, 0xEEEE, 0xECC8, 0xC880, 0xFEEC, 0xFEC8, 0xEC80, 0xC800, 0xFFEC, 0xFE80, 0xE800, 0xFFE8, 0xFF00, 0xFFF0, 0xF000,
        0xF710, 0x008E, 0x7100, 0x08CE, 0x008C, 0x7310, 0x3100, 0x8CCE, 0x088C, 0x3110, 0x6666, 0x366C, 0x17E8, 0x0FF0, 0x718E, 0x399C,
        0xAAAA, 0xF0F0, 0x5A5A, 0x33CC, 0x3C3C, 0x55AA, 0x9696, 0xA55A, 0x73CE, 0x13C8, 0x324C, 0x3BDC, 0x6996, 0xC33C, 0x9966, 0x0660,
        0x0272, 0x04E4, 0x4E40, 0x2720, 0xC936, 0x936C, 0x39C6, 0x639C, 0x9336, 0x9CC6, 0x817E, 0xE718, 0xCCF0, 0x0FCC, 0x7744, 0xEE22,
    ];

    /// <summary>The anchor texel of subset 1 in each two-subset partition (subset 0's is always texel 0).</summary>
    internal static ReadOnlySpan<byte> Anchors2 =>
    [
        15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
        15, 2, 8, 2, 2, 8, 8, 15, 2, 8, 2, 2, 8, 8, 2, 2,
        15, 15, 6, 8, 2, 8, 15, 15, 2, 8, 2, 2, 2, 15, 15, 6,
        6, 2, 6, 8, 15, 15, 2, 2, 15, 15, 15, 15, 15, 2, 2, 15,
    ];

    private static ReadOnlySpan<int> Weights3 => [0, 9, 18, 27, 37, 46, 55, 64];

    /// <summary>Partitions encoded in full, of those scored best.</summary>
    private const int Mode1Candidates = 3;

    /// <summary>Encodes an opaque block as mode 1 and returns its squared error.</summary>
    private static long EncodeMode1(ReadOnlySpan<byte> texels, Span<byte> block)
    {
        // Score every partition by the colour variance off each subset's principal axis.
        Span<int> bestPartitions = stackalloc int[Mode1Candidates];
        Span<float> bestScores = stackalloc float[Mode1Candidates];
        bestScores.Fill(float.MaxValue);
        var partitions = Partitions2;
        for (var partition = 0; partition < 64; partition++)
        {
            var mask = partitions[partition];
            var score = OffAxisVariance(texels, mask, 0) + OffAxisVariance(texels, mask, 1);
            for (var k = 0; k < Mode1Candidates; k++)
            {
                if (score < bestScores[k])
                {
                    for (var m = Mode1Candidates - 1; m > k; m--)
                    {
                        bestScores[m] = bestScores[m - 1];
                        bestPartitions[m] = bestPartitions[m - 1];
                    }

                    bestScores[k] = score;
                    bestPartitions[k] = partition;
                    break;
                }
            }
        }

        var bestError = long.MaxValue;
        Span<int> endpoints = stackalloc int[12];      // subset s, endpoint e, channel c: ((s * 2) + e) * 3 + c (6-bit values)
        Span<int> pbits = stackalloc int[2];
        Span<byte> indices = stackalloc byte[16];
        Span<int> bestEndpoints = stackalloc int[12];
        Span<int> bestPbits = stackalloc int[2];
        Span<byte> bestIndices = stackalloc byte[16];
        var bestPartition = 0;
        foreach (var partition in bestPartitions)
        {
            var mask = partitions[partition];
            long error = 0;
            for (var subset = 0; subset < 2; subset++)
            {
                error += EncodeSubset(texels, mask, subset, endpoints.Slice(subset * 6, 6), out pbits[subset], indices);
            }

            if (error < bestError)
            {
                bestError = error;
                bestPartition = partition;
                endpoints.CopyTo(bestEndpoints);
                pbits.CopyTo(bestPbits);
                indices.CopyTo(bestIndices);
            }
        }

        PackMode1(bestPartition, bestEndpoints, bestPbits, bestIndices, block);
        return bestError;
    }

    /// <summary>The squared distance of a subset's colours from their principal axis (total variance less its largest eigenvalue).</summary>
    private static float OffAxisVariance(ReadOnlySpan<byte> texels, ushort mask, int subset)
    {
        float n = 0, sr = 0, sg = 0, sb = 0;
        float rr = 0, gg = 0, bb = 0, rg = 0, rb = 0, gb = 0;
        for (var i = 0; i < 16; i++)
        {
            if (((mask >> i) & 1) != subset)
            {
                continue;
            }

            float r = texels[i * 4], g = texels[(i * 4) + 1], b = texels[(i * 4) + 2];
            n++;
            sr += r;
            sg += g;
            sb += b;
            rr += r * r;
            gg += g * g;
            bb += b * b;
            rg += r * g;
            rb += r * b;
            gb += g * b;
        }

        if (n < 2)
        {
            return 0;
        }

        // Covariance (as sums of squares about the mean).
        var cRR = rr - (sr * sr / n);
        var cGG = gg - (sg * sg / n);
        var cBB = bb - (sb * sb / n);
        var cRG = rg - (sr * sg / n);
        var cRB = rb - (sr * sb / n);
        var cGB = gb - (sg * sb / n);
        var trace = cRR + cGG + cBB;
        if (trace < 1e-3f)
        {
            return 0;
        }

        float x = 1, y = 1, z = 1, lambda = 0;
        for (var iteration = 0; iteration < 5; iteration++)
        {
            var nx = (cRR * x) + (cRG * y) + (cRB * z);
            var ny = (cRG * x) + (cGG * y) + (cGB * z);
            var nz = (cRB * x) + (cGB * y) + (cBB * z);
            var length = MathF.Sqrt((nx * nx) + (ny * ny) + (nz * nz));
            if (length < 1e-6f)
            {
                break;
            }

            lambda = length / MathF.Sqrt((x * x) + (y * y) + (z * z));
            (x, y, z) = (nx / length, ny / length, nz / length);
        }

        return Math.Max(0, trace - lambda);
    }

    /// <summary>
    /// Fits one subset: endpoints along its principal axis, then least-squares refinement, trying both values of the
    /// subset's shared p-bit. Writes its texels' indices and returns its squared error.
    /// </summary>
    private static long EncodeSubset(ReadOnlySpan<byte> texels, ushort mask, int subset, Span<int> endpoints, out int pbit, Span<byte> indices)
    {
        Span<float> mean = stackalloc float[3];
        var count = 0;
        for (var i = 0; i < 16; i++)
        {
            if (((mask >> i) & 1) == subset)
            {
                count++;
                for (var c = 0; c < 3; c++)
                {
                    mean[c] += texels[(i * 4) + c];
                }
            }
        }

        for (var c = 0; c < 3; c++)
        {
            mean[c] /= count;
        }

        Span<float> cov = stackalloc float[9];
        for (var i = 0; i < 16; i++)
        {
            if (((mask >> i) & 1) != subset)
            {
                continue;
            }

            for (var a = 0; a < 3; a++)
            {
                for (var b = 0; b < 3; b++)
                {
                    cov[(a * 3) + b] += (texels[(i * 4) + a] - mean[a]) * (texels[(i * 4) + b] - mean[b]);
                }
            }
        }

        Span<float> axis = stackalloc float[3] { 0.58f, 0.58f, 0.58f };
        Span<float> next = stackalloc float[3];
        for (var iteration = 0; iteration < 5; iteration++)
        {
            float length = 0;
            for (var a = 0; a < 3; a++)
            {
                next[a] = (cov[a * 3] * axis[0]) + (cov[(a * 3) + 1] * axis[1]) + (cov[(a * 3) + 2] * axis[2]);
                length += next[a] * next[a];
            }

            if (length < 1e-12f)
            {
                break;
            }

            length = MathF.Sqrt(length);
            for (var a = 0; a < 3; a++)
            {
                axis[a] = next[a] / length;
            }
        }

        float lo = float.MaxValue, hi = float.MinValue;
        for (var i = 0; i < 16; i++)
        {
            if (((mask >> i) & 1) == subset)
            {
                var t = ((texels[i * 4] - mean[0]) * axis[0]) + ((texels[(i * 4) + 1] - mean[1]) * axis[1]) + ((texels[(i * 4) + 2] - mean[2]) * axis[2]);
                lo = Math.Min(lo, t);
                hi = Math.Max(hi, t);
            }
        }

        Span<float> e0 = stackalloc float[3];
        Span<float> e1 = stackalloc float[3];
        for (var c = 0; c < 3; c++)
        {
            e0[c] = mean[c] + (axis[c] * lo);
            e1[c] = mean[c] + (axis[c] * hi);
        }

        var bestError = long.MaxValue;
        pbit = 0;
        Span<int> q = stackalloc int[6];
        Span<byte> trial = stackalloc byte[16];
        Span<byte> chosen = stackalloc byte[16];
        for (var round = 0; round < 3; round++)
        {
            var improved = false;
            for (var p = 0; p < 2; p++)
            {
                for (var c = 0; c < 3; c++)
                {
                    q[c] = Quantise6(e0[c], p);
                    q[3 + c] = Quantise6(e1[c], p);
                }

                var error = AssignSubset(texels, mask, subset, q, p, trial);
                if (error < bestError)
                {
                    bestError = error;
                    pbit = p;
                    q.CopyTo(endpoints);
                    trial.CopyTo(chosen);
                    improved = true;
                }
            }

            if (bestError == 0 || (round > 0 && !improved) || !RefineSubset(texels, mask, subset, chosen, e0, e1))
            {
                break;
            }
        }

        for (var i = 0; i < 16; i++)
        {
            if (((mask >> i) & 1) == subset)
            {
                indices[i] = chosen[i];
            }
        }

        return bestError;
    }

    /// <summary>A 6-bit endpoint plus p-bit expands to 8 bits as a 7-bit value with its top bit repeated.</summary>
    private static int Expand7(int value7) => (value7 << 1) | (value7 >> 6);

    /// <summary>The 6-bit value that, with p-bit <paramref name="p"/>, expands closest to <paramref name="value"/>.</summary>
    private static int Quantise6(float value, int p)
    {
        var guess = (int)MathF.Round(((value * 127f / 255f) - p) / 2f);
        var best = 0;
        var bestDistance = float.MaxValue;
        for (var q = Math.Max(0, guess - 1); q <= Math.Min(63, guess + 1); q++)
        {
            var distance = MathF.Abs(Expand7((q << 1) | p) - value);
            if (distance < bestDistance)
            {
                (best, bestDistance) = (q, distance);
            }
        }

        return best;
    }

    private static long AssignSubset(ReadOnlySpan<byte> texels, ushort mask, int subset, ReadOnlySpan<int> q, int p, Span<byte> indices)
    {
        Span<int> palette = stackalloc int[24];
        var weights = Weights3;
        for (var c = 0; c < 3; c++)
        {
            var a = Expand7((q[c] << 1) | p);
            var b = Expand7((q[3 + c] << 1) | p);
            for (var w = 0; w < 8; w++)
            {
                palette[(w * 3) + c] = (((64 - weights[w]) * a) + (weights[w] * b) + 32) >> 6;
            }
        }

        long total = 0;
        for (var i = 0; i < 16; i++)
        {
            if (((mask >> i) & 1) != subset)
            {
                continue;
            }

            int r = texels[i * 4], g = texels[(i * 4) + 1], bl = texels[(i * 4) + 2];
            var best = int.MaxValue;
            var bestIndex = 0;
            for (var w = 0; w < 8; w++)
            {
                int dr = palette[w * 3] - r, dg = palette[(w * 3) + 1] - g, db = palette[(w * 3) + 2] - bl;
                var d = (dr * dr) + (dg * dg) + (db * db);
                if (d < best)
                {
                    (best, bestIndex) = (d, w);
                }
            }

            indices[i] = (byte)bestIndex;
            total += best;
        }

        return total;
    }

    private static bool RefineSubset(ReadOnlySpan<byte> texels, ushort mask, int subset, ReadOnlySpan<byte> indices, Span<float> e0, Span<float> e1)
    {
        var weights = Weights3;
        float aa = 0, ab = 0, bb = 0;
        Span<float> x0 = stackalloc float[3];
        Span<float> x1 = stackalloc float[3];
        for (var i = 0; i < 16; i++)
        {
            if (((mask >> i) & 1) != subset)
            {
                continue;
            }

            var t = weights[indices[i]] / 64f;
            var s = 1f - t;
            aa += s * s;
            ab += s * t;
            bb += t * t;
            for (var c = 0; c < 3; c++)
            {
                x0[c] += s * texels[(i * 4) + c];
                x1[c] += t * texels[(i * 4) + c];
            }
        }

        var det = (aa * bb) - (ab * ab);
        if (MathF.Abs(det) < 1e-6f)
        {
            return false;
        }

        for (var c = 0; c < 3; c++)
        {
            e0[c] = Math.Clamp(((bb * x0[c]) - (ab * x1[c])) / det, 0f, 255f);
            e1[c] = Math.Clamp(((aa * x1[c]) - (ab * x0[c])) / det, 0f, 255f);
        }

        return true;
    }

    /// <summary>
    /// Writes a mode 1 block, least significant bit first: mode (01), partition (6 bits), R0 R1 R2 R3, G0-G3, B0-B3
    /// (6 bits each; subset 0's two endpoints, then subset 1's), P0 P1, then 3-bit indices with the two anchors (texel 0
    /// and subset 1's anchor) at 2 bits. An anchor index of 4 or more is made to fit by swapping its subset's
    /// endpoints and inverting that subset's indices.
    /// </summary>
    private static void PackMode1(int partition, Span<int> endpoints, ReadOnlySpan<int> pbits, Span<byte> indices, Span<byte> block)
    {
        var mask = Partitions2[partition];
        var anchor1 = Anchors2[partition];
        for (var subset = 0; subset < 2; subset++)
        {
            var anchor = subset == 0 ? 0 : anchor1;
            if (indices[anchor] < 4)
            {
                continue;
            }

            for (var c = 0; c < 3; c++)
            {
                (endpoints[(subset * 6) + c], endpoints[(subset * 6) + 3 + c]) = (endpoints[(subset * 6) + 3 + c], endpoints[(subset * 6) + c]);
            }

            for (var i = 0; i < 16; i++)
            {
                if (((mask >> i) & 1) == subset)
                {
                    indices[i] = (byte)(7 - indices[i]);
                }
            }
        }

        UInt128 bits = 0b10;
        var at = 2;
        bits |= (UInt128)(uint)partition << at;
        at += 6;
        for (var c = 0; c < 3; c++)
        {
            for (var subset = 0; subset < 2; subset++)
            {
                for (var e = 0; e < 2; e++)
                {
                    bits |= (UInt128)(uint)endpoints[(subset * 6) + (e * 3) + c] << at;
                    at += 6;
                }
            }
        }

        bits |= (UInt128)(uint)pbits[0] << at++;
        bits |= (UInt128)(uint)pbits[1] << at++;
        for (var i = 0; i < 16; i++)
        {
            bits |= (UInt128)indices[i] << at;
            at += i == 0 || i == anchor1 ? 2 : 3;
        }

        BinaryPrimitives.WriteUInt64LittleEndian(block, (ulong)bits);
        BinaryPrimitives.WriteUInt64LittleEndian(block[8..], (ulong)(bits >> 64));
    }
}
