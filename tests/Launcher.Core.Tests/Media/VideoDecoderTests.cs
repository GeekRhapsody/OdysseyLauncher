using System.Runtime.Versioning;
using Launcher.Core.Media;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Windows;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Media;

/// <summary>
/// The platform's video decoder (Media Foundation on Windows), on MP4s Media Foundation writes for the test. Each test
/// starts with <see cref="Decoder"/>, which skips it elsewhere.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class VideoDecoderTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private static IVideoDecoder Decoder()
    {
        var decoder = PlatformServices.CreateVideoDecoder();
        Assert.SkipWhen(decoder is null, "no video decoder on this platform");
        return decoder;
    }

    private string Video(int frames, double soundSeconds, string name = "game.mp4")
    {
        var path = _dir.Combine(name);
        TestVideos.WriteMp4(path, frames, soundSeconds);
        return path;
    }

    [Fact]
    public void Every_frame_is_read_in_order_as_opaque_RGBA_top_row_first()
    {
        var decoder = Decoder();
        var path = Video(frames: 30, soundSeconds: 0);
        using var reader = decoder.OpenVideo(path, out var error);
        Assert.True(reader is not null, error);
        Assert.Equal((TestVideos.Width, TestVideos.Height), (reader.Width, reader.Height));
        Assert.Equal(1, reader.PixelAspect, 3);
        Assert.InRange(reader.Duration.TotalSeconds, 0.9, 1.1);

        var rgba = new byte[reader.Width * reader.Height * 4];
        var times = new List<TimeSpan>();
        while (reader.ReadFrame(rgba, out var time) is var result && result != VideoFrameResult.Ended)
        {
            Assert.Equal(VideoFrameResult.Frame, result);
            times.Add(time);
            if (times.Count == 1)
            {
                // Lossy, so roughly: red at the top, blue at the bottom, opaque.
                AssertColour(rgba, TestVideos.Width / 2, 8, (220, 30, 30));
                AssertColour(rgba, TestVideos.Width / 2, TestVideos.Height - 8, (30, 30, 220));
            }
        }

        Assert.Equal(30, times.Count);
        Assert.Equal(times.Order(), times);
        Assert.InRange(times[^1].TotalSeconds, 0.9, 1.0);
        Assert.Equal(VideoFrameResult.Ended, reader.ReadFrame(rgba, out _));
    }

    [Fact]
    public void Seeking_to_the_start_plays_it_again()
    {
        var decoder = Decoder();
        using var reader = decoder.OpenVideo(Video(frames: 10, soundSeconds: 0), out var error);
        Assert.True(reader is not null, error);
        var rgba = new byte[reader.Width * reader.Height * 4];
        while (reader.ReadFrame(rgba, out _) == VideoFrameResult.Frame)
        {
        }

        Assert.True(reader.Seek(TimeSpan.Zero));
        Assert.Equal(VideoFrameResult.Frame, reader.ReadFrame(rgba, out var time));
        Assert.Equal(TimeSpan.Zero, time);
    }

    [Fact]
    public void A_buffer_of_the_wrong_size_is_refused_without_losing_the_frame()
    {
        var decoder = Decoder();
        using var reader = decoder.OpenVideo(Video(frames: 3, soundSeconds: 0), out var error);
        Assert.True(reader is not null, error);
        Assert.Equal(VideoFrameResult.Resized, reader.ReadFrame(new byte[16], out _));
        Assert.Equal(VideoFrameResult.Frame, reader.ReadFrame(new byte[reader.Width * reader.Height * 4], out var time));
        Assert.Equal(TimeSpan.Zero, time);
    }

    [Fact]
    public void The_sound_is_decoded_to_interleaved_floats()
    {
        var decoder = Decoder();
        using var audio = decoder.OpenAudio(Video(frames: 30, soundSeconds: 1), out var error);
        Assert.True(audio is not null, error);
        Assert.Equal((2, TestVideos.SampleRate), (audio.Channels, audio.SampleRate));

        var block = new float[1001];
        var total = 0;
        var peak = 0f;
        int read;
        while ((read = audio.Read(block)) > 0)
        {
            // Whole frames only, so 1000 of the 1001.
            Assert.True(read % 2 == 0, $"{read} samples isn't a whole number of stereo frames");
            total += read / 2;
            for (var i = 0; i < read; i++)
            {
                peak = Math.Max(peak, Math.Abs(block[i]));
            }
        }

        Assert.Equal(0, read);
        Assert.InRange(total, TestVideos.SampleRate * 0.9, TestVideos.SampleRate * 1.1);
        Assert.InRange(peak, 0.3f, 0.7f);
    }

    [Fact]
    public void A_video_without_sound_says_so()
    {
        var decoder = Decoder();
        Assert.Null(decoder.OpenAudio(Video(frames: 3, soundSeconds: 0), out var error));
        Assert.Equal("it has no sound", error);
    }

    [Fact]
    public void A_file_that_isnt_a_video_is_refused_with_a_reason()
    {
        var decoder = Decoder();
        var path = _dir.File("broken.mp4", "this isn't an MP4");
        Assert.Null(decoder.OpenVideo(path, out var error));
        Assert.False(string.IsNullOrEmpty(error));
        Assert.Null(decoder.OpenVideo(_dir.Combine("missing.mp4"), out error));
        Assert.Equal("the file doesn't exist", error);
    }

    [Fact]
    public void The_H264_profile_is_read_to_say_why_a_video_cant_play()
    {
        _ = Decoder();
        Assert.InRange(MediaFoundationVideoDecoder.H264Profile(Video(frames: 3, soundSeconds: 0)) ?? 0, 66, 100);

        // A 4:4:4 file Windows can't decode (ScreenScraper serves some), its box name straddling two reads.
        var bytes = new byte[64 * 1024 + 16];
        ((ReadOnlySpan<byte>)[(byte)'a', (byte)'v', (byte)'c', (byte)'C', 1, 244]).CopyTo(bytes.AsSpan(64 * 1024 - 2));
        var path = _dir.Combine("444.mp4");
        File.WriteAllBytes(path, bytes);
        Assert.Equal(244, MediaFoundationVideoDecoder.H264Profile(path));
        Assert.Null(MediaFoundationVideoDecoder.H264Profile(_dir.File("none.mp4", "no boxes here")));
    }

    private static void AssertColour(byte[] rgba, int x, int y, (int R, int G, int B) expected)
    {
        var i = (y * TestVideos.Width + x) * 4;
        var actual = (rgba[i], rgba[i + 1], rgba[i + 2]);
        Assert.True(
            Math.Abs(actual.Item1 - expected.R) < 50 && Math.Abs(actual.Item2 - expected.G) < 50 && Math.Abs(actual.Item3 - expected.B) < 50,
            $"pixel ({x}, {y}) is {actual}, expected about {expected}");
        Assert.Equal(255, rgba[i + 3]);
    }
}
