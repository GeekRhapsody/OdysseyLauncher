using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Launcher.Core.Media;
using static Launcher.Core.Platform.Linux.FfmpegNativeMethods;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// Decodes videos with the FFmpeg the AppImage carries (L4, the owner's choice: an LGPL build of FFmpeg 9.0 with only
/// the decoders the media folders need, H.264 with its 4:4:4 profiles, HEVC, VP9, AAC, MP3 and Opus, in MP4). It gives
/// the app what <c>MediaFoundationVideoDecoder</c> does on Windows: each stream opens the file on its own; the picture
/// is converted by swscale to opaque RGBA, top row first, straight into the caller's buffer (FFmpeg crops it to the
/// picture); the sound by swresample to interleaved 32-bit float at its own rate. A reader belongs to the thread that
/// opened it, and the libraries are loaded by the first one opened (<see cref="BundledLibraries"/>).
/// </summary>
[SupportedOSPlatform("linux")]
public sealed unsafe class FfmpegVideoDecoder : IVideoDecoder
{
    // A cap per video: the details screen and a focused card can each be decoding one.
    private static readonly int Threads = Math.Min(Environment.ProcessorCount, 4);

    public IVideoReader? OpenVideo(string path, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);
        return VideoReader.Open(path, out error);
    }

    public IAudioReader? OpenAudio(string path, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);
        return AudioReader.Open(path, out error);
    }

    private static T Read<T>(nint address, int offset)
        where T : unmanaged => *(T*)(address + offset);

    private static string Failure(string what, int error)
    {
        var text = stackalloc byte[256];
        return StrError(error, text, 256) >= 0
            ? $"couldn't {what} ({Marshal.PtrToStringUTF8((nint)text)})"
            : string.Create(CultureInfo.InvariantCulture, $"couldn't {what} (FFmpeg error {error})");
    }

    /// <summary>A file opened for one of its streams, with that stream's decoder, decoding a frame at a time.</summary>
    private sealed class Input : IDisposable
    {
        private nint _format;
        private nint _codec;
        private nint _packet;
        private nint _frame;
        private nint _stream;
        private int _index;
        private bool _draining;

        /// <summary>The last frame <see cref="Next"/> decoded.</summary>
        public nint Frame => _frame;

        public TimeSpan Duration
        {
            get
            {
                var duration = Read<long>(_stream, Abi.StreamDuration);
                if (duration > 0)
                {
                    return Time(duration);
                }

                var whole = Read<long>(_format, Abi.FormatContextDuration);
                return whole > 0 ? TimeSpan.FromTicks(whole * (TimeSpan.TicksPerSecond / Abi.TimeBase)) : TimeSpan.Zero;
            }
        }

        public static Input? Open(string path, int mediaType, out string? error)
        {
            if (!File.Exists(path))
            {
                error = "the file doesn't exist";
                return null;
            }

            error = BundledLibraries.Load(BundledLibraries.Ffmpeg);
            if (error is not null)
            {
                return null;
            }

            LogSetLevel(Abi.LogQuiet);
            var input = new Input();
            error = input.Start(path, mediaType);
            if (error is null)
            {
                return input;
            }

            input.Dispose();
            return null;
        }

        /// <summary>1 with a frame in <see cref="Frame"/>, 0 at the stream's end, or a negative FFmpeg error.</summary>
        public int Next()
        {
            FrameUnref(_frame);
            while (true)
            {
                var result = CodecReceiveFrame(_codec, _frame);
                if (result != Abi.ErrorAgain || _draining)
                {
                    return result >= 0 ? 1 : result is Abi.ErrorEndOfFile or Abi.ErrorAgain ? 0 : result;
                }

                result = ReadFrame(_format, _packet);
                if (result == Abi.ErrorEndOfFile)
                {
                    // The decoder gives what it still holds, then the end.
                    _draining = true;
                    result = CodecSendPacket(_codec, 0);
                }
                else if (result >= 0)
                {
                    result = Read<int>(_packet, Abi.PacketStreamIndex) == _index ? CodecSendPacket(_codec, _packet) : 0;
                    PacketUnref(_packet);

                    // A damaged packet is skipped, as players do: the decoder carries on from the next.
                    result = result == Abi.ErrorInvalidData ? 0 : result;
                }

                if (result < 0 && result != Abi.ErrorEndOfFile)
                {
                    return result;
                }
            }
        }

        /// <summary>The key frame at or before <paramref name="position"/>; false if the file can't seek.</summary>
        public bool Seek(TimeSpan position)
        {
            var timeBase = Read<Rational>(_stream, Abi.StreamTimeBase);
            if (timeBase.Num <= 0 || timeBase.Den <= 0)
            {
                return false;
            }

            var timestamp = (long)((Int128)Math.Max(0, position.Ticks) * timeBase.Den / ((Int128)timeBase.Num * TimeSpan.TicksPerSecond));
            if (SeekFrame(_format, _index, timestamp, Abi.SeekBackward) < 0)
            {
                return false;
            }

            CodecFlushBuffers(_codec);
            _draining = false;
            return true;
        }

        /// <summary>A timestamp in the stream's time base from the file's start; none or before the start is the start.</summary>
        public TimeSpan Time(long timestamp)
        {
            var timeBase = Read<Rational>(_stream, Abi.StreamTimeBase);
            if (timestamp is Abi.NoTimestamp or <= 0 || timeBase.Num <= 0 || timeBase.Den <= 0)
            {
                return TimeSpan.Zero;
            }

            return TimeSpan.FromTicks((long)((Int128)timestamp * timeBase.Num * TimeSpan.TicksPerSecond / timeBase.Den));
        }

        /// <summary>A pixel's width over its height: the stream's, else the codec's, else square.</summary>
        public double PixelAspect()
        {
            var ratio = GuessSampleAspectRatio(_format, _stream, _frame);
            return ratio.Num > 0 && ratio.Den > 0 ? (double)ratio.Num / ratio.Den : 1;
        }

        public void Dispose()
        {
            var (format, codec, packet, frame) = (_format, _codec, _packet, _frame);
            CodecFreeContext(&codec);
            PacketFree(&packet);
            FrameFree(&frame);
            FormatCloseInput(&format);
            (_format, _codec, _packet, _frame) = (0, 0, 0, 0);
        }

        private string? Start(string path, int mediaType)
        {
            nint format = 0;
            var result = FormatOpenInput(&format, path, 0, 0);
            if (result < 0)
            {
                return result == Abi.ErrorInvalidData ? "it isn't a video the launcher can read" : Failure("open the file", result);
            }

            _format = format;
            if ((result = FormatFindStreamInfo(format, 0)) < 0)
            {
                return Failure("read the file's streams", result);
            }

            var sound = mediaType == Abi.MediaTypeAudio;
            nint decoder;
            _index = FindBestStream(format, mediaType, -1, -1, &decoder, 0);
            if (_index < 0)
            {
                return _index switch
                {
                    Abi.ErrorStreamNotFound => sound ? "it has no sound" : "it has no picture",
                    Abi.ErrorDecoderNotFound => sound ? "its sound is in a format the launcher can't decode" : "its picture is in a format the launcher can't decode",
                    _ => Failure("choose the stream", _index),
                };
            }

            _stream = Read<nint>(Read<nint>(format, Abi.FormatContextStreams), _index * sizeof(nint));
            (_codec, _packet, _frame) = (CodecAllocContext(decoder), PacketAlloc(), FrameAlloc());
            if (_codec == 0 || _packet == 0 || _frame == 0)
            {
                return "FFmpeg ran out of memory";
            }

            if ((result = CodecParametersToContext(_codec, Read<nint>(_stream, Abi.StreamCodecParameters))) < 0)
            {
                return Failure("set up the decoder", result);
            }

            if (!sound)
            {
                _ = OptSetInt(_codec, "threads", Threads, 0);
            }

            return (result = CodecOpen(_codec, decoder, 0)) < 0 ? Failure("open the decoder", result) : null;
        }
    }

    private sealed class VideoReader : IVideoReader
    {
        private Input? _input;
        private bool _pending;
        private bool _ended;

        /// <summary>swscale's context and what it was made for: the frame's size, pixel format, colourspace and range.</summary>
        private nint _scale;
        private (int Width, int Height, int Format, int Colourspace, int Range) _scaled;

        private VideoReader(Input input) => _input = input;

        public int Width { get; private set; }

        public int Height { get; private set; }

        public double PixelAspect { get; private set; } = 1;

        public TimeSpan Duration { get; private init; }

        public string? Error { get; private set; }

        public static VideoReader? Open(string path, out string? error)
        {
            var input = Input.Open(path, Abi.MediaTypeVideo, out error);
            if (input is null)
            {
                return null;
            }

            // The first frame is decoded now, as on Windows: a file that can't be decoded fails here, and the size is
            // right before anyone sizes a buffer.
            var video = new VideoReader(input) { Duration = input.Duration };
            var result = input.Next();
            error = result < 0 ? Failure("decode a frame", result) : result == 0 ? "it has no frames" : null;
            if (error is not null)
            {
                video.Dispose();
                return null;
            }

            video._pending = true;
            video.TakeSize();
            return video;
        }

        public VideoFrameResult ReadFrame(Span<byte> rgba, out TimeSpan time)
        {
            time = default;
            if (_input is null)
            {
                Error = "the reader is closed";
                return VideoFrameResult.Failed;
            }

            if (!_pending && !_ended)
            {
                var result = _input.Next();
                if (result < 0)
                {
                    Error = Failure("decode a frame", result);
                    return VideoFrameResult.Failed;
                }

                (_pending, _ended) = (result > 0, result == 0);
            }

            if (!_pending)
            {
                return VideoFrameResult.Ended;
            }

            var frame = _input.Frame;
            if (Read<int>(frame, Abi.FrameWidth) != Width || Read<int>(frame, Abi.FrameHeight) != Height)
            {
                TakeSize();
                return VideoFrameResult.Resized;
            }

            if (rgba.Length != Width * Height * 4)
            {
                return VideoFrameResult.Resized;
            }

            _pending = false;
            time = _input.Time(Read<long>(frame, Abi.FrameBestEffortTimestamp));
            if (Convert(frame, rgba) is { } failed)
            {
                Error = failed;
                return VideoFrameResult.Failed;
            }

            return VideoFrameResult.Frame;
        }

        public bool Seek(TimeSpan position)
        {
            if (_input is null || !_input.Seek(position))
            {
                return false;
            }

            (_pending, _ended) = (false, false);
            return true;
        }

        public void Dispose()
        {
            ScaleFreeContext(_scale);
            _scale = 0;
            _input?.Dispose();
            _input = null;
        }

        private void TakeSize()
        {
            var frame = _input!.Frame;
            (Width, Height) = (Read<int>(frame, Abi.FrameWidth), Read<int>(frame, Abi.FrameHeight));
            PixelAspect = _input.PixelAspect();
        }

        /// <summary>The frame as opaque RGBA in <paramref name="rgba"/>; null, or why it couldn't be.</summary>
        private string? Convert(nint frame, Span<byte> rgba)
        {
            var wanted = (Width, Height, Read<int>(frame, Abi.FrameFormat), Read<int>(frame, Abi.FrameColourspace), Read<int>(frame, Abi.FrameColourRange));
            if (_scale == 0 || wanted != _scaled)
            {
                ScaleFreeContext(_scale);
                _scale = ScaleGetContext(Width, Height, wanted.Item3, Width, Height, Abi.PixelFormatRgba, Abi.SwsBilinear, 0, 0, 0);
                if (_scale == 0)
                {
                    return "couldn't convert the picture's pixel format";
                }

                // swscale assumes BT.601; a file that doesn't say is taken as HD's BT.709 from 720 lines up, as players do.
                var matrix = wanted.Item4 != Abi.ColourspaceUnspecified ? wanted.Item4 : Height >= 720 ? Abi.ColourspaceBt709 : Abi.SwsColourspaceItu601;
                var fullRange = wanted.Item5 == Abi.ColourRangeJpeg ? 1 : 0;
                _ = ScaleSetColourspaceDetails(_scale, ScaleGetCoefficients(matrix), fullRange, ScaleGetCoefficients(Abi.SwsColourspaceItu601), 1, 0, 1 << 16, 1 << 16);
                _scaled = wanted;
            }

            fixed (byte* pixels = rgba)
            {
                var destination = stackalloc nint[4] { (nint)pixels, 0, 0, 0 };
                var stride = stackalloc int[4] { Width * 4, 0, 0, 0 };
                var rows = Scale(_scale, (nint*)(frame + Abi.FrameData), (int*)(frame + Abi.FrameLinesize), 0, Height, destination, stride);
                return rows > 0 ? null : Failure("convert a frame", rows);
            }
        }
    }

    private sealed class AudioReader : IAudioReader
    {
        private Input? _input;
        private nint _resample;
        private float[] _block = [];
        private int _blockCount;
        private int _blockRead;
        private bool _pending;
        private bool _ended;

        private AudioReader(Input input) => _input = input;

        public int Channels { get; private set; }

        public int SampleRate { get; private set; }

        public string? Error { get; private set; }

        public static AudioReader? Open(string path, out string? error)
        {
            var input = Input.Open(path, Abi.MediaTypeAudio, out error);
            if (input is null)
            {
                return null;
            }

            // The first block is decoded now: its format, the decoder's, sets up the conversion.
            var audio = new AudioReader(input);
            var result = input.Next();
            error = result < 0 ? Failure("decode the sound", result) : result == 0 ? "its sound is empty" : audio.Start();
            if (error is not null)
            {
                audio.Dispose();
                return null;
            }

            audio._pending = true;
            return audio;
        }

        public int Read(Span<float> samples)
        {
            if (_input is null)
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
            var resample = _resample;
            ResampleFree(&resample);
            _resample = 0;
            _input?.Dispose();
            _input = null;
        }

        private string? Start()
        {
            var frame = _input!.Frame;
            var layout = frame + Abi.FrameChannelLayout;
            (Channels, SampleRate) = (Read<int>(layout, Abi.ChannelLayoutChannels), Read<int>(frame, Abi.FrameSampleRate));
            if (Channels is <= 0 or > 32 || SampleRate is <= 0 or > 768_000)
            {
                return "couldn't read the sound's format";
            }

            nint resample = 0;
            var result = ResampleAllocSetOptions(&resample, layout, Abi.SampleFormatFloat, SampleRate, layout, Read<int>(frame, Abi.FrameFormat), SampleRate, 0, 0);
            _resample = resample;
            if (result >= 0)
            {
                result = ResampleInit(resample);
            }

            return result < 0 ? Failure("set up the sound's conversion", result) : null;
        }

        /// <summary>The pending frame, else the next one decoded, into <see cref="_block"/>; at the end, what the conversion still holds.</summary>
        private string? NextBlock()
        {
            _blockCount = _blockRead = 0;
            if (!_pending)
            {
                var result = _input!.Next();
                if (result < 0)
                {
                    return Failure("decode the sound", result);
                }

                (_pending, _ended) = (result > 0, result == 0);
            }

            var frame = _input!.Frame;
            var count = _pending ? Read<int>(frame, Abi.FrameNbSamples) : 0;
            var planes = _pending ? Read<nint>(frame, Abi.FrameExtendedData) : 0;
            _pending = false;
            var room = ResampleGetOutSamples(_resample, count);
            if (room <= 0)
            {
                return room == 0 ? null : Failure("convert the sound", room);
            }

            if (_block.Length < room * Channels)
            {
                // Grows to the decoder's largest block, then stays.
                _block = new float[room * Channels];
            }

            int converted;
            fixed (float* block = _block)
            {
                var output = (nint)block;
                converted = ResampleConvert(_resample, &output, room, (nint*)planes, count);
            }

            if (converted < 0)
            {
                return Failure("convert the sound", converted);
            }

            _blockCount = converted * Channels;
            return null;
        }
    }
}
