using System;
using System.IO;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Media;

namespace Launcher.App.Textures;

/// <summary>
/// Core's <see cref="IImageDecoder"/> through Godot, where Core has none of its own (Linux, with no WIC): the file read
/// and decoded as the grid's covers are (<see cref="SourceImages"/>; BMP too, as WIC reads it), then squeezed to the
/// size asked for with Lanczos. With it the themes' logos are baked there, and oversized model textures scaled
/// (<see cref="AppServices.CreateImageDecoder"/>). Each image costs one managed array of its pixels
/// (<see cref="Image.GetData"/>), which is fine for the one-time bakes it serves. Worker threads only.
/// </summary>
public sealed class GodotImageDecoder : IImageDecoder
{
    /// <summary>Each thread's read buffer, grown to the largest file it has read.</summary>
    [ThreadStatic]
    private static byte[]? _buffer;

    public bool TryDecodeScaled(string path, int width, int height, Span<byte> rgba, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);
        var length = width * height * 4;
        if (width <= 0 || height <= 0 || rgba.Length < length)
        {
            throw new ArgumentException($"{rgba.Length} bytes can't hold {width} × {height} RGBA pixels.", nameof(rgba));
        }

        if (!GodotWork.TryEnter())
        {
            error = "the launcher is quitting";
            return false;
        }

        try
        {
            var buffer = _buffer ?? new byte[64 * 1024];
            var found = SourceImages.TryReadFile(path, ref buffer, SourceImages.MaxBytes, out var read);
            _buffer = buffer;
            if (!found)
            {
                error = "it's missing, or over 64 MB";
                return false;
            }

            using var image = new Image();
            var data = buffer.AsSpan(0, read);
            var loaded = SourceImages.Load(image, data);
            if (loaded == Error.FileUnrecognized && data is [(byte)'B', (byte)'M', ..])
            {
                loaded = image.LoadBmpFromBuffer(data);
            }

            if (loaded != Error.Ok || image.IsEmpty())
            {
                error = loaded == Error.FileUnrecognized ? "it isn't a PNG, JPEG, WebP or BMP" : $"Godot couldn't decode it ({loaded})";
                return false;
            }

            if (image.GetFormat() != Image.Format.Rgba8)
            {
                image.Convert(Image.Format.Rgba8);
            }

            image.Resize(width, height, Image.Interpolation.Lanczos);
            image.GetData().AsSpan(0, length).CopyTo(rgba);
            error = null;
            return true;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            error = e.Message;
            return false;
        }
        finally
        {
            GodotWork.Exit();
        }
    }
}
