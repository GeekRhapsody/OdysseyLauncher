using System;
using System.Globalization;
using System.IO;
using Godot;
using Launcher.Core.Media;

namespace Launcher.App.Ui;

/// <summary>
/// Small previews of image files (M7: the image picker, and each media slot of a game's options) and of videos (the
/// game details screen), decoded and scaled by the OS decoder off the main thread; the details screen's viewer loads
/// images full size through it too. Never call it on the main thread.
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

    /// <summary>
    /// Worker thread: a frame from a little way into a video (the first is often black), scaled to fit a square of
    /// <paramref name="side"/> pixels, and its length and file size for a caption; null, with the reason in
    /// <paramref name="info"/>, when it can't be decoded.
    /// </summary>
    public static ImageTexture? LoadVideo(string path, int side, IVideoDecoder? decoder, out string info)
    {
        if (decoder is null)
        {
            info = "Videos can't be played on this system yet.";
            return null;
        }

        try
        {
            using var reader = decoder.OpenVideo(path, out var error);
            if (reader is null)
            {
                info = $"It can't be played: {error}.";
                return null;
            }

            // Many clips open on black, so a frame a little way in, and further on while it's still dark.
            var length = reader.Duration;
            var rgba = new byte[reader.Width * reader.Height * 4];
            var target = TimeSpan.FromTicks(Math.Min(TimeSpan.FromSeconds(3).Ticks, length.Ticks / 5));
            var found = false;
            for (var attempt = 0; attempt < 4 && (attempt == 0 || target < length); attempt++)
            {
                if (target > TimeSpan.Zero)
                {
                    reader.Seek(target);
                }

                // A seek lands on the key frame before the time, so decode on to it.
                var frames = 0;
                VideoFrameResult result;
                TimeSpan at;
                while ((result = reader.ReadFrame(rgba, out at)) == VideoFrameResult.Frame && at < target && ++frames < 600)
                {
                }

                found |= result == VideoFrameResult.Frame;
                if (result != VideoFrameResult.Frame || !Dark(rgba))
                {
                    break;
                }

                target += TimeSpan.FromTicks(Math.Max(TimeSpan.FromSeconds(2).Ticks, length.Ticks / 8));
            }

            if (!found)
            {
                info = $"It can't be played: {reader.Error ?? "it has no frames"}.";
                return null;
            }

            var image = Image.CreateFromData(reader.Width, reader.Height, false, Image.Format.Rgba8, rgba);
            var shown = reader.Width * reader.PixelAspect;
            var scale = Math.Min(1.0, Math.Min(side / shown, (double)side / reader.Height));
            image.Resize(Math.Max(1, (int)Math.Round(shown * scale)), Math.Max(1, (int)Math.Round(reader.Height * scale)), Image.Interpolation.Bilinear);
            var texture = ImageTexture.CreateFromImage(image);
            image.Dispose();
            var time = length > TimeSpan.Zero ? length.ToString(length.TotalHours >= 1 ? @"h\:mm\:ss" : @"m\:ss", CultureInfo.InvariantCulture) + ", " : string.Empty;
            info = time + UiStyle.Size(new FileInfo(path).Length);
            return texture;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            info = $"It couldn't be read: {e.Message}";
            return null;
        }
    }

    /// <summary>True when nearly every sampled pixel of an RGBA frame is close to black.</summary>
    private static bool Dark(byte[] rgba)
    {
        var bright = 0;
        var samples = 0;
        for (var i = 0; i + 2 < rgba.Length; i += 4 * 61)
        {
            samples++;
            if (Math.Max(rgba[i], Math.Max(rgba[i + 1], rgba[i + 2])) > 40)
            {
                bright++;
            }
        }

        return bright < samples / 20;
    }
}
