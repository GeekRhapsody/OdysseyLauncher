using System.Globalization;
using System.Numerics;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Launcher.Core.Models;

/// <summary>
/// The shape animation exported beside a PS2 save icon converted to OBJ (<c>ICON.ICO.obj</c> with
/// <c>ICON.ICO.anim</c>, as ps2iodb's zips have it). The file is JSON: a header (<c>frameLength</c>,
/// <c>animSpeed</c>, <c>playOffset</c>) and <c>frames</c>, each a whole set of vertex positions
/// (<c>vertexData</c>, in the OBJ's <c>v</c> order and the PS2's axes) with weight keys (<c>keys</c>: a
/// <c>time</c> in frames and a <c>value</c>). The icon at a time is its frames blended by their weights, which add
/// up to 1. In glTF that's the OBJ (the first frame) as the mesh, every other distinct frame as a morph target, and
/// a clip of the targets' weights (A7), which the converter names <c>focused</c>: the PS2 browser animates the
/// icon that's selected.
/// </summary>
public sealed class ShapeAnimation
{
    /// <summary>
    /// Key times count frames of the PS2's 60 Hz display, divided by <c>animSpeed</c>. The format's documentation
    /// doesn't say; this is what looks right.
    /// </summary>
    public const float FramesPerSecond = 60;

    private ShapeAnimation(Vector3[][] shapes, float[] times, float[] weights)
    {
        Shapes = shapes;
        Times = times;
        Weights = weights;
    }

    /// <summary>Each morph target's positions in the OBJ's axes, indexed like its <c>v</c> lines.</summary>
    public IReadOnlyList<Vector3[]> Shapes { get; }

    /// <summary>The keys' times in seconds, from 0 to the loop's length.</summary>
    public float[] Times { get; }

    /// <summary>Every target's weight at each time: <see cref="Times"/>.Length × <see cref="Shapes"/>.Count, by time.</summary>
    public float[] Weights { get; }

    /// <summary>
    /// The animation in <paramref name="json"/> for a model whose OBJ positions are <paramref name="positions"/>, or
    /// null if it has nothing to play. Whatever stops it playing is added to <paramref name="warnings"/>, and the
    /// model is still imported, without its animation.
    /// </summary>
    public static ShapeAnimation? Read(byte[] json, IReadOnlyList<Vector3> positions, string fileName, List<string> warnings)
    {
        ArgumentNullException.ThrowIfNull(json);
        ArgumentNullException.ThrowIfNull(positions);
        ArgumentNullException.ThrowIfNull(warnings);
        try
        {
            return Read(JsonNode.Parse(json) as JsonObject, positions, fileName, warnings);
        }
        catch (Exception e) when (e is JsonException or InvalidOperationException or FormatException)
        {
            warnings.Add($"the animation '{fileName}' couldn't be read ({e.Message}), so the model doesn't animate");
            return null;
        }
    }

    private static ShapeAnimation? Read(JsonObject? root, IReadOnlyList<Vector3> positions, string fileName, List<string> warnings)
    {
        void Warn(string why) => warnings.Add($"the animation '{fileName}' {why}, so the model doesn't animate");

        var length = Number(root?["frameLength"]);
        var speed = root?["animSpeed"] is null ? 1 : Number(root["animSpeed"]);
        if (root?["frames"] is not JsonArray frameArray || length is not > 0 || speed is not > 0)
        {
            Warn("has no frames, frame length or speed");
            return null;
        }

        var frames = new List<(float[] Vertices, (float Time, float Value)[] Keys)>();
        foreach (var frame in frameArray)
        {
            if (frame?["vertexData"] is not JsonArray data || frame["keys"] is not JsonArray keys)
            {
                Warn("has a frame without vertices or keys");
                return null;
            }

            if (data.Count != positions.Count * 3)
            {
                Warn(string.Create(CultureInfo.InvariantCulture, $"has {data.Count / 3} vertices a frame, but the model has {positions.Count}"));
                return null;
            }

            var vertices = new float[data.Count];
            for (var i = 0; i < vertices.Length; i++)
            {
                vertices[i] = Number(data[i]) ?? throw new FormatException($"vertex {i / 3} isn't a number");
            }

            var parsed = new (float Time, float Value)[keys.Count];
            for (var i = 0; i < parsed.Length; i++)
            {
                parsed[i] = (Number(keys[i]?["time"]) ?? throw new FormatException("a key has no time"),
                    Number(keys[i]?["value"]) ?? throw new FormatException("a key has no value"));
            }

            Array.Sort(parsed, (a, b) => a.Time.CompareTo(b.Time));
            frames.Add((vertices, parsed));
        }

        if (frames.Count < 2)
        {
            return null;    // One frame: a still icon.
        }

        if (AxesOf(frames[0].Vertices, positions) is not { } axes)
        {
            Warn("doesn't start from the model's shape");
            return null;
        }

        // Frames with the same vertices are one shape (their weights add up); the first frame's is the mesh itself.
        var shapeOf = new int[frames.Count];
        var shapes = new List<float[]> { frames[0].Vertices };
        for (var f = 1; f < frames.Count; f++)
        {
            shapeOf[f] = shapes.FindIndex(s => s.AsSpan().SequenceEqual(frames[f].Vertices));
            if (shapeOf[f] < 0)
            {
                shapeOf[f] = shapes.Count;
                shapes.Add(frames[f].Vertices);
            }
        }

        var targets = shapes.Count - 1;
        if (targets == 0)
        {
            return null;    // Nothing moves.
        }

        if (targets > ModelBudget.MorphTargets)
        {
            Warn(string.Create(CultureInfo.InvariantCulture, $"has {shapes.Count} shapes, but a model can blend only {ModelBudget.MorphTargets + 1}"));
            return null;
        }

        // Every key time in the loop, so linear interpolation between them is exact. playOffset (where the loop
        // starts) isn't used: the clip starts when the item is focused.
        var frameTimes = new SortedSet<float> { 0, length.Value };
        foreach (var (_, keys) in frames)
        {
            foreach (var (time, _) in keys)
            {
                if (time >= 0 && time <= length.Value)
                {
                    frameTimes.Add(time);
                }
            }
        }

        var times = new float[frameTimes.Count];
        var weights = new float[frameTimes.Count * targets];
        var k = 0;
        foreach (var time in frameTimes)
        {
            times[k] = time / (FramesPerSecond * speed.Value);
            for (var f = 0; f < frames.Count; f++)
            {
                if (shapeOf[f] > 0)
                {
                    weights[k * targets + shapeOf[f] - 1] += Sample(frames[f].Keys, time);
                }
            }

            k++;
        }

        var result = new Vector3[targets][];
        for (var t = 0; t < targets; t++)
        {
            var source = shapes[t + 1];
            result[t] = new Vector3[positions.Count];
            for (var v = 0; v < positions.Count; v++)
            {
                result[t][v] = new Vector3(source[v * 3], source[v * 3 + 1], source[v * 3 + 2]) * axes;
            }
        }

        return new ShapeAnimation(result, times, weights);
    }

    /// <summary>
    /// The axis flips (a rotation by a half turn, or none) that take the first frame onto the OBJ, or null if none
    /// does. ps2iodb's OBJs are the PS2's frame turned about Z (x and y negated), since the PS2's y points down.
    /// </summary>
    private static Vector3? AxesOf(float[] first, IReadOnlyList<Vector3> positions)
    {
        var extent = 0f;
        foreach (var p in positions)
        {
            extent = MathF.Max(extent, MathF.Max(MathF.Abs(p.X), MathF.Max(MathF.Abs(p.Y), MathF.Abs(p.Z))));
        }

        // OBJ numbers are usually written to 6 decimals.
        var tolerance = 1e-3f * MathF.Max(1, extent);
        ReadOnlySpan<Vector3> candidates = [new(1, 1, 1), new(-1, -1, 1), new(1, -1, -1), new(-1, 1, -1)];
        foreach (var axes in candidates)
        {
            var matches = true;
            for (var v = 0; v < positions.Count && matches; v++)
            {
                var d = new Vector3(first[v * 3], first[v * 3 + 1], first[v * 3 + 2]) * axes - positions[v];
                matches = MathF.Abs(d.X) <= tolerance && MathF.Abs(d.Y) <= tolerance && MathF.Abs(d.Z) <= tolerance;
            }

            if (matches)
            {
                return axes;
            }
        }

        return null;
    }

    /// <summary>A frame's weight at a time: linear between its keys, held before the first and after the last.</summary>
    private static float Sample((float Time, float Value)[] keys, float time)
    {
        if (keys.Length == 0)
        {
            return 0;
        }

        if (time <= keys[0].Time)
        {
            return keys[0].Value;
        }

        for (var i = 1; i < keys.Length; i++)
        {
            if (time <= keys[i].Time)
            {
                var (t0, v0) = keys[i - 1];
                var (t1, v1) = keys[i];
                return t1 > t0 ? v0 + (v1 - v0) * (time - t0) / (t1 - t0) : v1;
            }
        }

        return keys[^1].Value;
    }

    private static float? Number(JsonNode? node) =>
        node is JsonValue value && value.TryGetValue<double>(out var d) && double.IsFinite(d) ? (float)d : null;
}
