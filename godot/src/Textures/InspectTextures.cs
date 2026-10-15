using System;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Theming;

namespace Launcher.App.Textures;

/// <summary>The inspected game's art at <see cref="InspectTextures.Size"/>: an array, and each slot's layer in it (−1: none).</summary>
public sealed class InspectArt(int cell, Texture2DArray texture, Vector4 layersLow, Vector4 layersHigh)
{
    public int Cell { get; } = cell;

    public Texture2DArray Texture { get; } = texture;

    /// <summary>Slots 0–3's layers (item.gdshader <c>inspect_layers_low</c>).</summary>
    public Vector4 LayersLow { get; } = layersLow;

    /// <summary>Slots 4–7's layers.</summary>
    public Vector4 LayersHigh { get; } = layersHigh;
}

/// <summary>
/// The inspected game's slot art read again from its sources at 1024² (A3, 2026-10-15). The grid's layers are 512² for
/// the cover and 256² for every other slot, which is plenty in the grid; inspected (R3), a game's front is about 90% of
/// the view's height, so its back would be magnified about 4×. One game at a time: a request supersedes the last, and
/// its array is made on a thread-pool thread (decoding, squeezing and the array's creation), so the main thread only
/// takes it (<see cref="TryTake"/>) and points the material at it.
/// </summary>
public sealed class InspectTextures
{
    /// <summary>Each slot's side: about the inspected front's height in pixels at the 1080p cap on 3D (A3).</summary>
    public const int Size = 1024;

    private readonly object _gate = new();
    private int _generation;
    private InspectArt? _result;

    /// <summary>
    /// Main thread: loads the cell's art for these slots from these files (absolute paths), dropping any earlier request
    /// or result. Runs once per inspection, so it may allocate.
    /// </summary>
    public void Request(int cell, ReadOnlySpan<int> slots, ReadOnlySpan<string> paths)
    {
        int generation;
        lock (_gate)
        {
            DropResult();
            generation = ++_generation;
        }

        var slotList = slots.ToArray();
        var pathList = paths.ToArray();
        _ = Task.Run(() => Load(generation, cell, slotList, pathList));
    }

    /// <summary>Main thread: drops the request in flight and any result not taken.</summary>
    public void Cancel()
    {
        lock (_gate)
        {
            DropResult();
            _generation++;
        }
    }

    /// <summary>Main thread: the latest request's art, once it's made (the caller owns it then).</summary>
    public bool TryTake(out InspectArt? art)
    {
        lock (_gate)
        {
            art = _result;
            _result = null;
            return art is not null;
        }
    }

    /// <summary>Under the gate.</summary>
    private void DropResult()
    {
        _result?.Texture.Dispose();
        _result = null;
    }

    private bool IsCurrent(int generation) => Volatile.Read(ref _generation) == generation;

    private void Load(int generation, int cell, int[] slots, string[] paths)
    {
        // Decoding and the array call into Godot: once the app is quitting, it doesn't start (GodotWork).
        if (!GodotWork.TryEnter())
        {
            return;
        }

        var images = new Godot.Collections.Array<Image>();
        try
        {
            Span<float> layers = stackalloc float[MediaSlots.Count];
            layers.Fill(-1);
            var buffer = new byte[1024 * 1024];
            for (var i = 0; i < slots.Length; i++)
            {
                if (!IsCurrent(generation) || GodotWork.Quitting)
                {
                    return;
                }

                var image = new Image();
                if (SourceImages.TryLoadSquare(paths[i], ref buffer, image, Size, TextureStreamer.DirectFormat))
                {
                    layers[slots[i]] = images.Count;
                    images.Add(image);
                }
                else
                {
                    // That slot keeps the grid's layer.
                    image.Dispose();
                }
            }

            if (images.Count == 0 || !IsCurrent(generation) || GodotWork.Quitting)
            {
                return;
            }

            var texture = new Texture2DArray();
            if (texture.CreateFromImages(images) != Error.Ok)
            {
                GD.PushWarning($"Inspect: couldn't make a {Size}² array of {images.Count} layers for cell {cell}");
                texture.Dispose();
                return;
            }

            var art = new InspectArt(cell, texture, new Vector4(layers[0], layers[1], layers[2], layers[3]),
                new Vector4(layers[4], layers[5], layers[6], layers[7]));
            lock (_gate)
            {
                if (_generation == generation)
                {
                    DropResult();
                    _result = art;
                    return;
                }
            }

            texture.Dispose();
        }
        finally
        {
            // Each image's memory goes now, not when the GC finalises the array (which holds a reference to each).
            foreach (var image in images)
            {
                image.Dispose();
            }

            images.Clear();
            GodotWork.Exit();
        }
    }
}
