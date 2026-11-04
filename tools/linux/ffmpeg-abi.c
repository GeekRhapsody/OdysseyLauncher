// Prints the FFmpeg struct offsets and constants Launcher.Core's hand-written bindings use (FfmpegNativeMethods.Abi),
// one "Name value" a line, from the headers of the FFmpeg tools/linux/setup.sh builds. FfmpegAbiTests compares them
// with the C# constants, so a new FFmpeg that moves a field fails a test rather than a video.
#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/pixfmt.h>
#include <libavutil/samplefmt.h>
#include <libswscale/swscale.h>

#define FIELD(name, type, member) printf("%s %zu\n", name, offsetof(type, member))
#define VALUE(name, value) printf("%s %lld\n", name, (long long)(value))

int main(void)
{
    FIELD("FormatContextStreams", AVFormatContext, streams);
    FIELD("FormatContextDuration", AVFormatContext, duration);
    FIELD("StreamCodecParameters", AVStream, codecpar);
    FIELD("StreamTimeBase", AVStream, time_base);
    FIELD("StreamDuration", AVStream, duration);
    FIELD("FrameData", AVFrame, data);
    FIELD("FrameLinesize", AVFrame, linesize);
    FIELD("FrameExtendedData", AVFrame, extended_data);
    FIELD("FrameWidth", AVFrame, width);
    FIELD("FrameHeight", AVFrame, height);
    FIELD("FrameNbSamples", AVFrame, nb_samples);
    FIELD("FrameFormat", AVFrame, format);
    FIELD("FrameColourRange", AVFrame, color_range);
    FIELD("FrameColourspace", AVFrame, colorspace);
    FIELD("FrameBestEffortTimestamp", AVFrame, best_effort_timestamp);
    FIELD("FrameSampleRate", AVFrame, sample_rate);
    FIELD("FrameChannelLayout", AVFrame, ch_layout);
    FIELD("PacketStreamIndex", AVPacket, stream_index);
    FIELD("ChannelLayoutChannels", AVChannelLayout, nb_channels);

    VALUE("MediaTypeVideo", AVMEDIA_TYPE_VIDEO);
    VALUE("MediaTypeAudio", AVMEDIA_TYPE_AUDIO);
    VALUE("PixelFormatRgba", AV_PIX_FMT_RGBA);
    VALUE("SampleFormatFloat", AV_SAMPLE_FMT_FLT);
    VALUE("ColourRangeJpeg", AVCOL_RANGE_JPEG);
    VALUE("ColourspaceUnspecified", AVCOL_SPC_UNSPECIFIED);
    VALUE("ColourspaceBt709", AVCOL_SPC_BT709);
    VALUE("SwsColourspaceItu601", SWS_CS_ITU601);
    VALUE("ErrorEndOfFile", AVERROR_EOF);
    VALUE("ErrorAgain", AVERROR(EAGAIN));
    VALUE("ErrorStreamNotFound", AVERROR_STREAM_NOT_FOUND);
    VALUE("ErrorDecoderNotFound", AVERROR_DECODER_NOT_FOUND);
    VALUE("ErrorNoEntry", AVERROR(ENOENT));
    VALUE("ErrorInvalidData", AVERROR_INVALIDDATA);
    VALUE("SwsBilinear", SWS_BILINEAR);
    VALUE("SeekBackward", AVSEEK_FLAG_BACKWARD);
    VALUE("NoTimestamp", AV_NOPTS_VALUE);
    VALUE("TimeBase", AV_TIME_BASE);
    VALUE("LogQuiet", AV_LOG_QUIET);
    return 0;
}
