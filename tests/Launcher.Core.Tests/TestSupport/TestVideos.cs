using System.Runtime.Versioning;
using Launcher.Core.Platform.Windows;
using static Launcher.Core.Platform.Windows.MediaFoundation;

namespace Launcher.Core.Tests.TestSupport;

/// <summary>
/// Writes small MP4s with Media Foundation's own encoders (H.264 and AAC ship with Windows), so the video tests need no
/// fixture file: the picture's top half is red and its bottom half blue, and the sound a 440 Hz tone.
/// </summary>
[SupportedOSPlatform("windows")]
internal static unsafe class TestVideos
{
    public const int Width = 128;
    public const int Height = 96;
    public const int FramesPerSecond = 30;
    public const int SampleRate = 48_000;

    public static void WriteMp4(string path, int frames, double soundSeconds)
    {
        if (Startup() is { } problem)
        {
            throw new InvalidOperationException(problem);
        }

        nint writer = 0;
        try
        {
            Check(MFCreateSinkWriterFromURLChecked(path, &writer), "create the writer");
            var video = AddStream(writer, VideoType(VideoH264, output: true), VideoType(VideoRgb32, output: false));
            var audio = soundSeconds > 0 ? AddStream(writer, AudioType(AudioAac, output: true), AudioType(AudioPcm, output: false)) : uint.MaxValue;
            Check(((delegate* unmanaged<nint, int>)Slot(writer, SlotWriterBeginWriting))(writer), "begin writing");

            var frameTicks = 10_000_000L / FramesPerSecond;
            for (var i = 0; i < frames; i++)
            {
                WriteSample(writer, video, i * frameTicks, frameTicks, Width * Height * 4, data =>
                {
                    var pixels = (uint*)data;
                    for (var y = 0; y < Height; y++)
                    {
                        for (var x = 0; x < Width; x++)
                        {
                            // BGRX in memory: red is the third byte.
                            pixels[y * Width + x] = y < Height / 2 ? 0x00DC_1E1Eu : 0x001E_1EDCu;
                        }
                    }
                });
            }

            if (audio != uint.MaxValue)
            {
                const int chunk = SampleRate / 10;
                var total = (int)(soundSeconds * SampleRate);
                for (var start = 0; start < total; start += chunk)
                {
                    var count = Math.Min(chunk, total - start);
                    var first = start;
                    WriteSample(writer, audio, first * 10_000_000L / SampleRate, count * 10_000_000L / SampleRate, count * 4, data =>
                    {
                        var pcm = (short*)data;
                        for (var i = 0; i < count; i++)
                        {
                            var value = (short)(Math.Sin(2 * Math.PI * 440 * (first + i) / SampleRate) * 16_000);
                            pcm[2 * i] = value;
                            pcm[2 * i + 1] = value;
                        }
                    });
                }
            }

            Check(((delegate* unmanaged<nint, int>)Slot(writer, SlotWriterFinalize))(writer), "finish the file");
        }
        finally
        {
            Release(writer);
            Shutdown();
        }
    }

    private static int MFCreateSinkWriterFromURLChecked(string path, nint* writer)
    {
        fixed (char* url = path)
        {
            return MFCreateSinkWriterFromURL(url, 0, 0, writer);
        }
    }

    private static uint AddStream(nint writer, nint output, nint input)
    {
        try
        {
            uint index;
            Check(((delegate* unmanaged<nint, nint, uint*, int>)Slot(writer, SlotWriterAddStream))(writer, output, &index), "add a stream");
            Check(((delegate* unmanaged<nint, uint, nint, nint, int>)Slot(writer, SlotWriterSetInputMediaType))(writer, index, input, 0), "set a stream's input");
            return index;
        }
        finally
        {
            Release(output);
            Release(input);
        }
    }

    private static nint VideoType(Guid subtype, bool output)
    {
        var type = NewType(MediaFoundation.Video, subtype);
        Check(SetUInt32(type, InterlaceMode, 2), "set progressive");
        Check(SetUInt64(type, FrameSize, ((ulong)Width << 32) | Height), "set the size");
        Check(SetUInt64(type, FrameRate, ((ulong)FramesPerSecond << 32) | 1), "set the frame rate");
        Check(SetUInt64(type, PixelAspectRatio, (1UL << 32) | 1), "set the pixel shape");
        Check(output ? SetUInt32(type, AverageBitrate, 500_000) : SetUInt32(type, DefaultStride, Width * 4), output ? "set the bitrate" : "set the stride");
        return type;
    }

    private static nint AudioType(Guid subtype, bool output)
    {
        var type = NewType(MediaFoundation.Audio, subtype);
        Check(SetUInt32(type, AudioBitsPerSample, 16), "set the sample size");
        Check(SetUInt32(type, AudioSampleRate, SampleRate), "set the rate");
        Check(SetUInt32(type, AudioChannels, 2), "set the channels");
        Check(output ? SetUInt32(type, AudioAverageBytesPerSecond, 16_000) : SetUInt32(type, AudioBlockAlignment, 4), "set the format");
        if (!output)
        {
            Check(SetUInt32(type, AudioAverageBytesPerSecond, SampleRate * 4), "set the byte rate");
        }

        return type;
    }

    private static nint NewType(Guid major, Guid subtype)
    {
        nint type;
        Check(MFCreateMediaType(&type), "create a media type");
        Check(SetGuid(type, MajorType, major), "set the major type");
        Check(SetGuid(type, Subtype, subtype), "set the subtype");
        return type;
    }

    private static void WriteSample(nint writer, uint stream, long time, long duration, int bytes, Action<nint> fill)
    {
        nint buffer = 0, sample = 0;
        try
        {
            Check(MFCreateMemoryBuffer((uint)bytes, &buffer), "create a buffer");
            byte* data;
            uint max, current;
            Check(((delegate* unmanaged<nint, byte**, uint*, uint*, int>)Slot(buffer, SlotBufferLock))(buffer, &data, &max, &current), "lock a buffer");
            fill((nint)data);
            _ = ((delegate* unmanaged<nint, int>)Slot(buffer, SlotBufferUnlock))(buffer);
            Check(((delegate* unmanaged<nint, uint, int>)Slot(buffer, SlotBufferSetCurrentLength))(buffer, (uint)bytes), "fill a buffer");
            Check(MFCreateSample(&sample), "create a sample");
            Check(((delegate* unmanaged<nint, nint, int>)Slot(sample, SlotSampleAddBuffer))(sample, buffer), "add a buffer");
            Check(((delegate* unmanaged<nint, long, int>)Slot(sample, SlotSampleSetTime))(sample, time), "time a sample");
            Check(((delegate* unmanaged<nint, long, int>)Slot(sample, SlotSampleSetDuration))(sample, duration), "time a sample");
            Check(((delegate* unmanaged<nint, uint, nint, int>)Slot(writer, SlotWriterWriteSample))(writer, stream, sample), "write a sample");
        }
        finally
        {
            Release(sample);
            Release(buffer);
        }
    }

    private static void Check(int hr, string what)
    {
        if (hr < 0)
        {
            throw new InvalidOperationException(Failure(what, hr));
        }
    }
}
