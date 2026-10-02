namespace Launcher.Core.Media;

/// <summary>
/// Decodes a game's video (the <c>video</c> kind: a scraped MP4) for the game's details screen, through the OS's codecs
/// (Windows: Media Foundation). A reader is used on one thread, the one that opened it, and never on Godot's main
/// thread: opening and decoding block.
/// </summary>
public interface IVideoDecoder
{
    /// <summary>The file's first video stream, as RGBA frames; null, with the reason in <paramref name="error"/>, when it can't be read.</summary>
    IVideoReader? OpenVideo(string path, out string? error);

    /// <summary>The file's first audio stream, as interleaved 32-bit float samples; null when it has none or it can't be read.</summary>
    IAudioReader? OpenAudio(string path, out string? error);
}

/// <summary>What <see cref="IVideoReader.ReadFrame"/> did.</summary>
public enum VideoFrameResult
{
    /// <summary>A frame was written.</summary>
    Frame,

    /// <summary>
    /// The stream's frame size changed: nothing was written or consumed. Read <see cref="IVideoReader.Width"/> and
    /// <see cref="IVideoReader.Height"/> again, and call again with a buffer that size.
    /// </summary>
    Resized,

    /// <summary>The stream has no more frames.</summary>
    Ended,

    /// <summary>Decoding failed; <see cref="IVideoReader.Error"/> says why.</summary>
    Failed,
}

/// <summary>A video stream, decoded frame by frame.</summary>
public interface IVideoReader : IDisposable
{
    /// <summary>The frame's width in pixels, without the codec's padding.</summary>
    int Width { get; }

    int Height { get; }

    /// <summary>A pixel's width over its height (1 for square pixels), for the picture's shape.</summary>
    double PixelAspect { get; }

    /// <summary>The stream's length; zero when the file doesn't say.</summary>
    TimeSpan Duration { get; }

    /// <summary>Why the last call failed, for the user.</summary>
    string? Error { get; }

    /// <summary>
    /// The next frame as RGBA8 (<see cref="Width"/> × <see cref="Height"/> × 4 bytes, top row first, opaque), with
    /// its presentation time from the start of the file.
    /// </summary>
    VideoFrameResult ReadFrame(Span<byte> rgba, out TimeSpan time);

    /// <summary>
    /// Moves to the key frame at or before <paramref name="position"/>: the next frame read is that one or a little
    /// earlier. False if the file can't seek.
    /// </summary>
    bool Seek(TimeSpan position);
}

/// <summary>An audio stream, decoded to 32-bit float samples.</summary>
public interface IAudioReader : IDisposable
{
    int Channels { get; }

    /// <summary>Frames (one sample per channel) a second.</summary>
    int SampleRate { get; }

    /// <summary>Why the last read failed, for the user.</summary>
    string? Error { get; }

    /// <summary>
    /// Copies up to <paramref name="samples"/>' length of interleaved samples (a whole number of frames), decoding more
    /// as needed. Returns how many were written: 0 at the end of the stream, −1 if decoding failed.
    /// </summary>
    int Read(Span<float> samples);
}
