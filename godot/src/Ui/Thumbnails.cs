using System;
using System.Globalization;
using System.IO;
using Godot;
using Launcher.Core.Media;

namespace Launcher.App.Ui;

/// <summary>
/// Small previews of image files (M7: the image picker, and each media slot of a game's options), decoded and scaled
/// by the OS decoder off the main thread. Never call it on the main thread.
/// </summary>
public static class Thumbnails
{
    private static readonly object DecoderLock = new();

    /// <summary>
    /// Worker thread: the image scaled to fit a square of <paramref name="side"/> pixels (never enlarged), and its size
    /// for a caption; null, with the reason in <paramref name="info"/>, when it can't be read.
    /// </summary>
    public static ImageTexture? Load(string path, int side, IImageDecoder? decoder, out string info)
    {
        try
        {
            if (!ImageHeaders.TryReadSize(path, out var width, out var height) || width <= 0 || height <= 0)
            {
                info = "Not an image the launcher can read.";
                return null;
            }

            var scale = Math.Min(1.0, Math.Min((double)side / width, (double)side / height));
            var w = Math.Max(1, (int)Math.Round(width * scale));
            var h = Math.Max(1, (int)Math.Round(height * scale));
            Image image;
            if (decoder is not null)
            {
                var rgba = new byte[w * h * 4];
                bool decoded;
                string? error;
                lock (DecoderLock)
                {
                    decoded = decoder.TryDecodeScaled(path, w, h, rgba, out error);
                }

                if (!decoded)
                {
                    info = $"It couldn't be read: {error}";
                    return null;
                }

                image = Image.CreateFromData(w, h, false, Image.Format.Rgba8, rgba);
            }
            else
            {
                image = Image.LoadFromFile(path);
                image.Resize(w, h);
            }

            var texture = ImageTexture.CreateFromImage(image);
            image.Dispose();
            info = string.Create(CultureInfo.InvariantCulture, $"{width} × {height}, {UiStyle.Size(new FileInfo(path).Length)}");
            return texture;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            info = $"It couldn't be read: {e.Message}";
            return null;
        }
    }
}
