using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Launcher.Core.Media;
using static Launcher.Core.Platform.Windows.MediaFoundation;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Decodes videos with Media Foundation, which ships with Windows (H.264 and AAC, the MP4s scrapers serve; HEVC only
/// with its extension). Each stream has its own source reader: the picture through Media Foundation's video processor,
/// which converts the decoder's YUV to 32-bit RGB, and the sound decoded to 32-bit float. A reader belongs to the thread
/// that opened it.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class MediaFoundationVideoDecoder : IVideoDecoder
{
    public IVideoReader? OpenVideo(string path, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);
        return MfVideoReader.Open(path, out error);
    }

    public IAudioReader? OpenAudio(string path, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);
        return MfAudioReader.Open(path, out error);
    }

    /// <summary>
    /// The H.264 profile in an MP4's <c>avcC</c> box (100 High, 244 High 4:4:4), found by its name, for saying why a
    /// video can't be decoded; null if there's none. Reads the file, so only after a failure.
    /// </summary>
    internal static int? H264Profile(string path)
    {
        try
        {
            using var file = File.OpenRead(path);
            var buffer = new byte[64 * 1024];
            var kept = 0;
            int read;
            while ((read = file.Read(buffer, kept, buffer.Length - kept)) > 0)
            {
                var span = buffer.AsSpan(0, kept + read);
                var at = span.IndexOf("avcC"u8);

                // The box's name, then its version (1) and the profile.
                if (at >= 0 && at + 5 < span.Length && span[at + 4] == 1)
                {
                    return span[at + 5];
                }

                // The name or what follows it may straddle two reads.
                kept = Math.Min(8, span.Length);
                span[^kept..].CopyTo(buffer);
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
        }

        return null;
    }

    private sealed unsafe class MfVideoReader : IVideoReader
    {
        private nint _reader;
        private nint _pending;
        private long _pendingTime;
        private bool _ended;

        /// <summary>The decoded picture: its size with padding, its stride, and the visible part (the aperture).</summary>
        private int _frameWidth;
        private int _frameHeight;
        private int _stride;
        private int _left;
        private int _top;

        private MfVideoReader(nint reader) => _reader = reader;

        public int Width { get; private set; }

        public int Height { get; private set; }

        public double PixelAspect { get; private set; } = 1;

        public TimeSpan Duration { get; private set; }

        public string? Error { get; private set; }

        public static MfVideoReader? Open(string path, out string? error)
        {
            if (Startup() is { } problem)
            {
                error = problem;
                return null;
            }

            var reader = OpenReader(path, FirstVideoStream, videoProcessing: true, out error);
            if (reader == 0)
            {
                Shutdown();
                return null;
            }

            var video = new MfVideoReader(reader) { Duration = TimeSpan.FromTicks(MediaFoundation.Duration(reader)) };
            error = SetOutputType(reader, FirstVideoStream, MediaFoundation.Video, VideoRgb32) ?? video.ReadFormat();

            // The decoder often settles the picture's format only with its first frame, so it's read now: the size is
            // then right before anyone sizes a buffer, and a file that can't be decoded fails here.
            if (error is null && video.Next() is { } failed)
            {
                // Windows' H.264 decoder takes 4:2:0 profiles only; a fifth of ScreenScraper's arcade videos are 4:4:4.
                error = H264Profile(path) is 244 ? "its H.264 is the 4:4:4 profile, which Windows' decoder doesn't support" : failed;
            }

            if (error is null && video._pending == 0)
            {
                error = "it has no frames";
            }

            if (error is not null)
            {
                video.Dispose();
                return null;
            }

            return video;
        }

        public VideoFrameResult ReadFrame(Span<byte> rgba, out TimeSpan time)
        {
            time = default;
            if (_reader == 0)
            {
                Error = "the reader is closed";
                return VideoFrameResult.Failed;
            }

            if (_pending == 0 && !_ended && Next() is { } problem)
            {
                Error = problem;
                return VideoFrameResult.Failed;
            }

            if (_pending == 0)
            {
                return VideoFrameResult.Ended;
            }

            if (rgba.Length != Width * Height * 4)
            {
                return VideoFrameResult.Resized;
            }

            time = TimeSpan.FromTicks(_pendingTime);
            var sample = _pending;
            _pending = 0;
            try
            {
                if (Copy(sample, rgba) is { } failed)
                {
                    Error = failed;
                    return VideoFrameResult.Failed;
                }
            }
            finally
            {
                Release(sample);
            }

            return VideoFrameResult.Frame;
        }

        public bool Seek(TimeSpan position)
        {
            if (_reader == 0 || SetPosition(_reader, Math.Max(0, position.Ticks)) < 0)
            {
                return false;
            }

            Release(_pending);
            _pending = 0;
            _ended = false;
            return true;
        }

        public void Dispose()
        {
            if (_reader == 0)
            {
                return;
            }

            Release(_pending);
            _pending = 0;
            Release(_reader);
            _reader = 0;
            Shutdown();
        }

        /// <summary>Reads the next frame into <see cref="_pending"/> (none at the end); null, or why it failed.</summary>
        private string? Next()
        {
            while (true)
            {
                var hr = ReadSample(_reader, FirstVideoStream, out var flags, out var time, out var sample);
                if (hr < 0 || (flags & ReaderFlagError) != 0)
                {
                    Release(sample);
                    return Failure("decode a frame", hr < 0 ? hr : -1);
                }

                if ((flags & ReaderFlagCurrentTypeChanged) != 0 && ReadFormat() is { } problem)
                {
                    Release(sample);
                    return problem;
                }

                if (sample != 0)
                {
                    _pending = sample;
                    _pendingTime = time;
                    return null;
                }

                if ((flags & ReaderFlagEndOfStream) != 0)
                {
                    _ended = true;
                    return null;
                }

                // A gap in the stream (a stream tick): read on.
            }
        }

        /// <summary>The output type's size, stride, visible part and pixel shape; null, or why it can't be used.</summary>
        private string? ReadFormat()
        {
            var type = CurrentType(_reader, FirstVideoStream);
            if (type == 0)
            {
                return "couldn't read the picture's format";
            }

            try
            {
                if (GetUInt64(type, FrameSize, out var size) < 0 || (uint)(size >> 32) == 0 || (uint)size == 0)
                {
                    return "couldn't read the picture's size";
                }

                _frameWidth = (int)(size >> 32);
                _frameHeight = (int)(uint)size;
                _stride = GetUInt32(type, DefaultStride, out var stride) >= 0 ? (int)stride : _frameWidth * 4;
                (_left, _top, Width, Height) = (0, 0, _frameWidth, _frameHeight);

                // MFVideoArea: OffsetX and OffsetY (each a fraction then a whole part), then the area's width and height.
                Span<byte> area = stackalloc byte[16];
                if (GetBlob(type, MinimumDisplayAperture, area, out var length) >= 0 && length >= 16)
                {
                    var left = (int)MemoryMarshal.Read<short>(area[2..]);
                    var top = (int)MemoryMarshal.Read<short>(area[6..]);
                    var width = MemoryMarshal.Read<int>(area[8..]);
                    var height = MemoryMarshal.Read<int>(area[12..]);
                    if (left >= 0 && top >= 0 && width > 0 && height > 0 && left + width <= _frameWidth && top + height <= _frameHeight)
                    {
                        (_left, _top, Width, Height) = (left, top, width, height);
                    }
                }

                PixelAspect = GetUInt64(type, PixelAspectRatio, out var ratio) >= 0 && (uint)ratio != 0 && (uint)(ratio >> 32) != 0
                    ? (double)(uint)(ratio >> 32) / (uint)ratio
                    : 1;
                return null;
            }
            finally
            {
                Release(type);
            }
        }

        /// <summary>The sample's visible part, from 32-bit BGRX to opaque RGBA, top row first.</summary>
        private string? Copy(nint sample, Span<byte> rgba)
        {
            nint buffer;
            var hr = ((delegate* unmanaged<nint, nint*, int>)Slot(sample, SlotSampleToContiguousBuffer))(sample, &buffer);
            if (hr < 0)
            {
                return Failure("read a frame", hr);
            }

            var buffer2D = Query(buffer, Buffer2D);
            try
            {
                byte* scan0;
                int pitch;
                if (buffer2D != 0)
                {
                    hr = ((delegate* unmanaged<nint, byte**, int*, int>)Slot(buffer2D, SlotLock2D))(buffer2D, &scan0, &pitch);
                }
                else
                {
                    uint max, current;
                    hr = ((delegate* unmanaged<nint, byte**, uint*, uint*, int>)Slot(buffer, SlotBufferLock))(buffer, &scan0, &max, &current);
                    pitch = _stride;
                    if (hr >= 0 && (long)Math.Abs(pitch) * _frameHeight > current)
                    {
                        _ = ((delegate* unmanaged<nint, int>)Slot(buffer, SlotBufferUnlock))(buffer);
                        return "a frame was smaller than its picture";
                    }

                    if (pitch < 0)
                    {
                        // A bottom-up picture starts with its last row.
                        scan0 += (long)-pitch * (_frameHeight - 1);
                    }
                }

                if (hr < 0)
                {
                    return Failure("read a frame", hr);
                }

                fixed (byte* destination = rgba)
                {
                    var target = (uint*)destination;
                    for (var y = 0; y < Height; y++)
                    {
                        var row = (uint*)(scan0 + (long)(y + _top) * pitch) + _left;
                        var outRow = target + (long)y * Width;
                        for (var x = 0; x < Width; x++)
                        {
                            // Little-endian BGRX to RGBA: swap red and blue, and make it opaque.
                            var bgrx = row[x];
                            outRow[x] = ((bgrx >> 16) & 0xFF) | (bgrx & 0xFF00) | ((bgrx & 0xFF) << 16) | 0xFF00_0000;
                        }
                    }
                }

                _ = buffer2D != 0
                    ? ((delegate* unmanaged<nint, int>)Slot(buffer2D, SlotUnlock2D))(buffer2D)
                    : ((delegate* unmanaged<nint, int>)Slot(buffer, SlotBufferUnlock))(buffer);
                return null;
            }
            finally
            {
                Release(buffer2D);
                Release(buffer);
            }
        }
    }

    private sealed unsafe class MfAudioReader : IAudioReader
    {
        private nint _reader;
        private float[] _block = [];
        private int _blockCount;
        private int _blockRead;
        private bool _ended;

        private MfAudioReader(nint reader) => _reader = reader;

        public int Channels { get; private set; }

        public int SampleRate { get; private set; }

        public string? Error { get; private set; }

        public static MfAudioReader? Open(string path, out string? error)
        {
            if (Startup() is { } problem)
            {
                error = problem;
                return null;
            }

            var reader = OpenReader(path, FirstAudioStream, videoProcessing: false, out error);
            if (reader == 0)
            {
                Shutdown();
                return null;
            }

            var audio = new MfAudioReader(reader);
            error = SetOutputType(reader, FirstAudioStream, MediaFoundation.Audio, AudioFloat);
            if (error is null)
            {
                var type = CurrentType(reader, FirstAudioStream);
                if (type != 0 && GetUInt32(type, AudioChannels, out var channels) >= 0 && GetUInt32(type, AudioSampleRate, out var rate) >= 0
                    && channels is > 0 and <= 32 && rate is > 0 and <= 768_000)
                {
                    (audio.Channels, audio.SampleRate) = ((int)channels, (int)rate);
                }
                else
                {
                    error = "couldn't read the sound's format";
                }

                Release(type);
            }

            if (error is not null)
            {
                audio.Dispose();
                return null;
            }

            return audio;
        }

        public int Read(Span<float> samples)
        {
            if (_reader == 0)
            {
                Error = "the reader is closed";
                return -1;
            }

            var wanted = samples.Length - samples.Length % Channels;
            var written = 0;
            while (written < wanted)
            {
                if (_blockRead < _blockCount)
                {
                    var count = Math.Min(wanted - written, _blockCount - _blockRead);
                    _block.AsSpan(_blockRead, count).CopyTo(samples[written..]);
                    _blockRead += count;
                    written += count;
                    continue;
                }

                if (_ended)
                {
                    break;
                }

                if (NextBlock() is { } problem)
                {
                    Error = problem;
                    return written > 0 ? written : -1;
                }
            }

            return written;
        }

        public void Dispose()
        {
            if (_reader == 0)
            {
                return;
            }

            Release(_reader);
            _reader = 0;
            Shutdown();
        }

        /// <summary>Decodes the next sample into <see cref="_block"/>; null, or why it failed.</summary>
        private string? NextBlock()
        {
            _blockCount = _blockRead = 0;
            var hr = ReadSample(_reader, FirstAudioStream, out var flags, out _, out var sample);
            if (hr < 0 || (flags & ReaderFlagError) != 0)
            {
                Release(sample);
                return Failure("decode the sound", hr < 0 ? hr : -1);
            }

            if (sample == 0)
            {
                _ended = (flags & ReaderFlagEndOfStream) != 0;
                return null;
            }

            nint buffer = 0;
            try
            {
                hr = ((delegate* unmanaged<nint, nint*, int>)Slot(sample, SlotSampleToContiguousBuffer))(sample, &buffer);
                byte* data = null;
                uint max, length = 0;
                if (hr >= 0)
                {
                    hr = ((delegate* unmanaged<nint, byte**, uint*, uint*, int>)Slot(buffer, SlotBufferLock))(buffer, &data, &max, &length);
                }

                if (hr < 0)
                {
                    return Failure("read the sound", hr);
                }

                var floats = (int)(length / sizeof(float));
                floats -= floats % Channels;
                if (_block.Length < floats)
                {
                    // Grows to the decoder's largest block, then stays.
                    _block = new float[floats];
                }

                new ReadOnlySpan<float>(data, floats).CopyTo(_block);
                _blockCount = floats;
                _ = ((delegate* unmanaged<nint, int>)Slot(buffer, SlotBufferUnlock))(buffer);
                return null;
            }
            finally
            {
                Release(buffer);
                Release(sample);
            }
        }
    }
}
