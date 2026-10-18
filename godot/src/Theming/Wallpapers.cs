using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Media;

namespace Launcher.App.Theming;

/// <summary>
/// Themes' wallpapers (A6 Background) as textures: each decoded on the thread pool, scaled to fit 2560 × 1080 (the 3D,
/// which the background canvas is drawn through, is at most 1080 high: A3), and made a texture there, so the main thread
/// never decodes or uploads one. Godot decodes them, not the OS decoder: its image is native memory, freed when it's
/// disposed, where a managed buffer of 8 MB or more would sit on the large-object heap until a full collection, which
/// browsing never makes (measured: 20 MB more managed heap for two: docs/perf/wallpapers.md). At most <see cref="MaxResident"/> stay loaded (the theme's, the shown system's and one
/// fetched ahead), the least recently used going first; the ones on screen are never let go.
/// </summary>
public sealed class Wallpapers(MainThreadQueue queue)
{
    /// <summary>The most kept at once: about 8 MB each at 1920 × 1080.</summary>
    public const int MaxResident = 3;

    public const int MaxWidth = 2560;
    public const int MaxHeight = 1080;

    private readonly Dictionary<string, Entry> _entries = new(StringComparer.Ordinal);
    private long _uses;

    /// <summary>Main thread: a wallpaper finished loading (its texture is null when it couldn't be read).</summary>
    public event Action<string, Texture2D?>? Loaded;

    /// <summary>Main thread: the wallpaper's texture, or null while it loads (starting it) or when it can't be read.</summary>
    public Texture2D? Get(string path, out float aspect)
    {
        aspect = 1;
        if (!_entries.TryGetValue(path, out var entry))
        {
            Request(path);
            return null;
        }

        entry.LastUse = ++_uses;
        aspect = entry.Aspect;
        return entry.Texture;
    }

    /// <summary>Main thread: starts loading the wallpaper unless it's loaded or loading (a prefetch).</summary>
    public void Request(string path)
    {
        if (_entries.TryGetValue(path, out var known))
        {
            known.LastUse = ++_uses;
            return;
        }

        var entry = new Entry { LastUse = ++_uses, Loading = true };
        _entries[path] = entry;
        _ = Task.Run(() =>
        {
            var texture = Load(path, out var aspect, out var info);
            queue.Post(() => OnLoaded(path, entry, texture, aspect, info));
        });
    }

    /// <summary>
    /// Main thread: lets go of every wallpaper but the ones on screen (<paramref name="keepA"/>, <paramref name="keepB"/>),
    /// so a theme updated in place (A6 Downloading themes) is read again rather than shown from memory.
    /// </summary>
    public void Forget(Texture2D? keepA, Texture2D? keepB)
    {
        var drop = new List<string>();
        foreach (var (path, entry) in _entries)
        {
            if (!entry.Loading && entry.Texture != keepA && entry.Texture != keepB)
            {
                drop.Add(path);
            }
        }

        foreach (var path in drop)
        {
            _entries.Remove(path, out var entry);
            entry!.Texture?.Dispose();
        }
    }

    /// <summary>Main thread: drops the least recently used wallpapers past <see cref="MaxResident"/>, never one on screen.</summary>
    public void Trim(Texture2D? keepA, Texture2D? keepB)
    {
        while (_entries.Count > MaxResident)
        {
            string? oldest = null;
            var oldestUse = long.MaxValue;
            foreach (var (path, entry) in _entries)
            {
                if (!entry.Loading && entry.Texture != keepA && entry.Texture != keepB && entry.LastUse < oldestUse)
                {
                    oldest = path;
                    oldestUse = entry.LastUse;
                }
            }

            if (oldest is null)
            {
                return;
            }

            _entries.Remove(oldest, out var dropped);

            // A material still pointing at it keeps the texture until it's pointed elsewhere; this lets go of ours.
            dropped!.Texture?.Dispose();
        }
    }

    private void OnLoaded(string path, Entry entry, Texture2D? texture, float aspect, string? info)
    {
        if (!_entries.TryGetValue(path, out var current) || current != entry)
        {
            // Forgotten while it loaded (a theme switch); a newer request has its own entry.
            texture?.Dispose();
            return;
        }

        entry.Loading = false;
        entry.Texture = texture;
        entry.Aspect = aspect;
        if (texture is null)
        {
            GD.PushWarning($"Wallpaper: {path}: {info}");
        }

        Loaded?.Invoke(path, texture);
    }

    /// <summary>Worker thread: the image scaled to fit <see cref="MaxWidth"/> × <see cref="MaxHeight"/> (never enlarged).</summary>
    private Texture2D? Load(string path, out float aspect, out string? info)
    {
        aspect = 1;
        info = null;

        // Decoding and the texture call into Godot: once the app is quitting, it doesn't start (GodotWork).
        if (!GodotWork.TryEnter())
        {
            info = "the launcher is quitting";
            return null;
        }

        try
        {
            var clock = System.Diagnostics.Stopwatch.StartNew();
            if (!ImageHeaders.TryReadSize(path, out var width, out var height) || width <= 0 || height <= 0)
            {
                info = "not an image the launcher can read";
                return null;
            }

            var scale = Math.Min(1.0, Math.Min((double)MaxWidth / width, (double)MaxHeight / height));
            var w = Math.Max(1, (int)Math.Round(width * scale));
            var h = Math.Max(1, (int)Math.Round(height * scale));
            var image = Image.LoadFromFile(path);
            if (image is null || image.IsEmpty())
            {
                image?.Dispose();
                info = "it couldn't be decoded";
                return null;
            }

            if (image.GetWidth() != w || image.GetHeight() != h)
            {
                image.Resize(w, h, Image.Interpolation.Cubic);
            }

            var texture = ImageTexture.CreateFromImage(image);
            image.Dispose();
            aspect = (float)width / height;
            GD.Print(FormattableString.Invariant($"Wallpaper: {path} ({width} × {height}) as {w} × {h} in {clock.Elapsed.TotalMilliseconds:0} ms."));
            return texture;
        }
        catch (Exception e) when (e is System.IO.IOException or UnauthorizedAccessException)
        {
            info = e.Message;
            return null;
        }
        finally
        {
            GodotWork.Exit();
        }
    }

    private sealed class Entry
    {
        public Texture2D? Texture;
        public float Aspect = 1;
        public long LastUse;
        public bool Loading;
    }
}
