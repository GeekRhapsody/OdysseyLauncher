using System;
using System.IO;
using Godot;
using Microsoft.Win32.SafeHandles;

namespace Launcher.App.Textures;

/// <summary>
/// The media folder's images read as they are (A3, 2026-10-05): a file into a reusable buffer, then decoded with Godot
/// as a PNG, JPEG or WebP, told apart by its first bytes. Shared by the grid's streamer and the inspected game's art
/// (<see cref="InspectTextures"/>), so both read the same files the same way. Worker threads.
/// </summary>
public static class SourceImages
{
    /// <summary>The largest source image read.</summary>
    public const long MaxBytes = 64L * 1024 * 1024;

    /// <summary>Reads a whole file into the buffer (growing it if need be). False if it's missing or too big.</summary>
    public static bool TryReadFile(string path, ref byte[] buffer, long maxBytes, out int read)
    {
        read = 0;
        SafeFileHandle handle;
        try
        {
            handle = File.OpenHandle(path, FileMode.Open, System.IO.FileAccess.Read, FileShare.Read, FileOptions.SequentialScan);
        }
        catch (FileNotFoundException)
        {
            return false;
        }
        catch (DirectoryNotFoundException)
        {
            return false;
        }

        using var file = handle;
        var length = RandomAccess.GetLength(file);
        if (length > maxBytes)
        {
            return false;
        }

        if (length > buffer.Length)
        {
            buffer = new byte[length];
        }

        while (read < length)
        {
            var n = RandomAccess.Read(file, buffer.AsSpan(read, (int)length - read), read);
            if (n == 0)
            {
                break;
            }

            read += n;
        }

        return true;
    }

    /// <summary>Decodes a PNG, JPEG or WebP into <paramref name="image"/>; <see cref="Error.FileUnrecognized"/> for anything else.</summary>
    public static Error Load(Image image, ReadOnlySpan<byte> data) => data switch
    {
        [0x89, (byte)'P', (byte)'N', (byte)'G', ..] => image.LoadPngFromBuffer(data),
        [0xFF, 0xD8, 0xFF, ..] => image.LoadJpgFromBuffer(data),
        [(byte)'R', (byte)'I', (byte)'F', (byte)'F', _, _, _, _, (byte)'W', (byte)'E', (byte)'B', (byte)'P', ..] => image.LoadWebpFromBuffer(data),
        _ => Error.FileUnrecognized,
    };

    /// <summary>
    /// Reads and decodes a source image, then squeezes the whole of it into an RGBA8 square of <paramref name="size"/>
    /// with mips, as the grid's layers hold it (the shader crops it by the media's aspect). False if there's no such
    /// file or it doesn't decode.
    /// </summary>
    public static bool TryLoadSquare(string path, ref byte[] buffer, Image image, int size, Image.Format format)
    {
        if (!TryReadFile(path, ref buffer, MaxBytes, out var read))
        {
            return false;
        }

        if (Load(image, buffer.AsSpan(0, read)) != Error.Ok || image.IsEmpty())
        {
            return false;
        }

        if (image.GetFormat() != format)
        {
            image.Convert(format);
        }

        image.Resize(size, size, Image.Interpolation.Lanczos);
        image.GenerateMipmaps();
        return true;
    }
}
