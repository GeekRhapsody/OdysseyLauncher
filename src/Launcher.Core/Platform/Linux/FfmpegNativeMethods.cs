using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// The FFmpeg 9.0 calls <see cref="FfmpegVideoDecoder"/> makes, bound by hand (no package), to the libraries the
/// AppImage carries (<see cref="BundledLibraries"/>): call <see cref="BundledLibraries.Load"/> with
/// <see cref="BundledLibraries.Ffmpeg"/> first. Structs FFmpeg gives no accessors for are read at the offsets in
/// <see cref="Abi"/>.
/// </summary>
[SupportedOSPlatform("linux")]
internal static unsafe partial class FfmpegNativeMethods
{
    private const string AvUtil = BundledLibraries.Prefix + "libavutil.so.61";
    private const string SwResample = BundledLibraries.Prefix + "libswresample.so.7";
    private const string AvCodec = BundledLibraries.Prefix + "libavcodec.so.63";
    private const string AvFormat = BundledLibraries.Prefix + "libavformat.so.63";
    private const string SwScale = BundledLibraries.Prefix + "libswscale.so.10";

    /// <summary>
    /// Field offsets and constants from FFmpeg 9.0's headers. tools/linux/ffmpeg-abi.c prints the same names from the
    /// headers setup.sh builds against, and <c>FfmpegAbiTests</c> compares the two, so a new FFmpeg that moves a field
    /// fails a test.
    /// </summary>
    internal static class Abi
    {
        public const int FormatContextStreams = 48;
        public const int FormatContextDuration = 104;
        public const int StreamCodecParameters = 16;
        public const int StreamTimeBase = 32;
        public const int StreamDuration = 48;
        public const int FrameData = 0;
        public const int FrameLinesize = 64;
        public const int FrameExtendedData = 96;
        public const int FrameWidth = 104;
        public const int FrameHeight = 108;
        public const int FrameNbSamples = 112;
        public const int FrameFormat = 116;
        public const int FrameColourRange = 280;
        public const int FrameColourspace = 292;
        public const int FrameBestEffortTimestamp = 304;
        public const int FrameSampleRate = 180;
        public const int FrameChannelLayout = 384;
        public const int PacketStreamIndex = 36;
        public const int ChannelLayoutChannels = 4;

        public const int MediaTypeVideo = 0;
        public const int MediaTypeAudio = 1;
        public const int PixelFormatRgba = 26;
        public const int SampleFormatFloat = 3;
        public const int ColourRangeJpeg = 2;
        public const int ColourspaceUnspecified = 2;
        public const int ColourspaceBt709 = 1;
        public const int SwsColourspaceItu601 = 5;
        public const int ErrorEndOfFile = -541478725;
        public const int ErrorAgain = -11;
        public const int ErrorStreamNotFound = -1381258232;
        public const int ErrorDecoderNotFound = -1128613112;
        public const int ErrorNoEntry = -2;
        public const int ErrorInvalidData = -1094995529;
        public const int SwsBilinear = 2;
        public const int SeekBackward = 1;
        public const long NoTimestamp = long.MinValue;
        public const int TimeBase = 1_000_000;
        public const int LogQuiet = -8;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct Rational
    {
        public int Num;
        public int Den;
    }

    [LibraryImport(AvFormat, EntryPoint = "avformat_open_input", StringMarshalling = StringMarshalling.Utf8)]
    public static partial int FormatOpenInput(nint* context, string url, nint format, nint options);

    [LibraryImport(AvFormat, EntryPoint = "avformat_find_stream_info")]
    public static partial int FormatFindStreamInfo(nint context, nint options);

    [LibraryImport(AvFormat, EntryPoint = "av_find_best_stream")]
    public static partial int FindBestStream(nint context, int type, int wanted, int related, nint* decoder, int flags);

    [LibraryImport(AvFormat, EntryPoint = "av_read_frame")]
    public static partial int ReadFrame(nint context, nint packet);

    [LibraryImport(AvFormat, EntryPoint = "av_seek_frame")]
    public static partial int SeekFrame(nint context, int stream, long timestamp, int flags);

    [LibraryImport(AvFormat, EntryPoint = "av_guess_sample_aspect_ratio")]
    public static partial Rational GuessSampleAspectRatio(nint context, nint stream, nint frame);

    [LibraryImport(AvFormat, EntryPoint = "avformat_close_input")]
    public static partial void FormatCloseInput(nint* context);

    [LibraryImport(AvCodec, EntryPoint = "avcodec_alloc_context3")]
    public static partial nint CodecAllocContext(nint codec);

    [LibraryImport(AvCodec, EntryPoint = "avcodec_parameters_to_context")]
    public static partial int CodecParametersToContext(nint context, nint parameters);

    [LibraryImport(AvCodec, EntryPoint = "avcodec_open2")]
    public static partial int CodecOpen(nint context, nint codec, nint options);

    [LibraryImport(AvCodec, EntryPoint = "avcodec_send_packet")]
    public static partial int CodecSendPacket(nint context, nint packet);

    [LibraryImport(AvCodec, EntryPoint = "avcodec_receive_frame")]
    public static partial int CodecReceiveFrame(nint context, nint frame);

    [LibraryImport(AvCodec, EntryPoint = "avcodec_flush_buffers")]
    public static partial void CodecFlushBuffers(nint context);

    [LibraryImport(AvCodec, EntryPoint = "avcodec_free_context")]
    public static partial void CodecFreeContext(nint* context);

    [LibraryImport(AvCodec, EntryPoint = "av_packet_alloc")]
    public static partial nint PacketAlloc();

    [LibraryImport(AvCodec, EntryPoint = "av_packet_unref")]
    public static partial void PacketUnref(nint packet);

    [LibraryImport(AvCodec, EntryPoint = "av_packet_free")]
    public static partial void PacketFree(nint* packet);

    [LibraryImport(AvUtil, EntryPoint = "av_frame_alloc")]
    public static partial nint FrameAlloc();

    [LibraryImport(AvUtil, EntryPoint = "av_frame_unref")]
    public static partial void FrameUnref(nint frame);

    [LibraryImport(AvUtil, EntryPoint = "av_frame_free")]
    public static partial void FrameFree(nint* frame);

    [LibraryImport(AvUtil, EntryPoint = "av_strerror")]
    public static partial int StrError(int error, byte* buffer, nuint size);

    [LibraryImport(AvUtil, EntryPoint = "av_log_set_level")]
    public static partial void LogSetLevel(int level);

    [LibraryImport(AvUtil, EntryPoint = "av_opt_set_int", StringMarshalling = StringMarshalling.Utf8)]
    public static partial int OptSetInt(nint target, string name, long value, int flags);

    [LibraryImport(SwScale, EntryPoint = "sws_getContext")]
    public static partial nint ScaleGetContext(int sourceWidth, int sourceHeight, int sourceFormat, int width, int height, int format, int flags, nint sourceFilter, nint filter, nint parameters);

    [LibraryImport(SwScale, EntryPoint = "sws_setColorspaceDetails")]
    public static partial int ScaleSetColourspaceDetails(nint context, int* sourceTable, int sourceRange, int* table, int range, int brightness, int contrast, int saturation);

    [LibraryImport(SwScale, EntryPoint = "sws_getCoefficients")]
    public static partial int* ScaleGetCoefficients(int colourspace);

    [LibraryImport(SwScale, EntryPoint = "sws_scale")]
    public static partial int Scale(nint context, nint* source, int* sourceStride, int top, int height, nint* destination, int* destinationStride);

    [LibraryImport(SwScale, EntryPoint = "sws_freeContext")]
    public static partial void ScaleFreeContext(nint context);

    [LibraryImport(SwResample, EntryPoint = "swr_alloc_set_opts2")]
    public static partial int ResampleAllocSetOptions(nint* context, nint outLayout, int outFormat, int outRate, nint inLayout, int inFormat, int inRate, int logOffset, nint logContext);

    [LibraryImport(SwResample, EntryPoint = "swr_init")]
    public static partial int ResampleInit(nint context);

    [LibraryImport(SwResample, EntryPoint = "swr_get_out_samples")]
    public static partial int ResampleGetOutSamples(nint context, int inSamples);

    [LibraryImport(SwResample, EntryPoint = "swr_convert")]
    public static partial int ResampleConvert(nint context, nint* output, int outCount, nint* input, int inCount);

    [LibraryImport(SwResample, EntryPoint = "swr_free")]
    public static partial void ResampleFree(nint* context);
}
