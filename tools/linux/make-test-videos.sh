#!/usr/bin/env bash
# Writes the test videos VideoDecoderTests uses where Media Foundation can't write them (Linux), and the ones that check
# each codec the bundled FFmpeg decodes (L4), into tests/Launcher.Core.Tests/Media/Videos/. Each is 128 x 96, 30
# frames at 30 a second, its top half red (220, 30, 30) and its bottom half blue (30, 30, 220), as TestVideos draws
# them, with a second of a 440 Hz tone at half scale in stereo at 48 kHz. Made with Ubuntu's own ffmpeg package (its
# GPL encoders only make test data: nothing of theirs ships), installed by apt the first time; bit-exact flags and
# one thread, so the same package writes the same files. The files are committed: run this only to change them.
#
#   bash tools/linux/make-test-videos.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="$(cd "$here/../.." && pwd)/tests/Launcher.Core.Tests/Media/Videos"
if ! command -v ffmpeg > /dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg > /dev/null
fi

picture='color=c=0xDC1E1E:s=128x48:r=30:d=1[top];color=c=0x1E1EDC:s=128x48:r=30:d=1[bottom];[top][bottom]vstack[out0]'
tone='aevalsrc=0.5*sin(2*PI*440*t)|0.5*sin(2*PI*440*t):s=48000:d=1'
h264=(-c:v libx264 -preset medium -pix_fmt yuv420p -profile:v high -g 30)
aac=(-c:a aac -b:a 128k)

# <name> <ffmpeg's encoding options...>: with the tone unless the options include -an.
write() {
    local name=$1
    shift
    ffmpeg -nostdin -loglevel error -y -f lavfi -i "$picture" -f lavfi -i "$tone" -frames:v 30 -t 1 -threads 1 \
        -fflags +bitexact -flags:v +bitexact -flags:a +bitexact -map_metadata -1 "$@" "$out/$name"
    echo "$name: $(ffprobe -v error -show_entries stream=codec_name,profile,pix_fmt,sample_rate,channels -of csv=p=0 "$out/$name" | tr '\n' ' ')"
}

mkdir -p "$out"
write red-blue.mp4 "${h264[@]}" "${aac[@]}"
write red-blue-silent.mp4 "${h264[@]}" -an
write red-blue-h264-444.mp4 -c:v libx264 -preset medium -pix_fmt yuv444p -profile:v high444 -g 30 "${aac[@]}"
write red-blue-hevc.mp4 -c:v libx265 -pix_fmt yuv420p -tag:v hvc1 -x265-params log-level=error:pools=1:frame-threads=1 "${aac[@]}"
write red-blue-vp9-opus.mp4 -c:v libvpx-vp9 -pix_fmt yuv420p -b:v 200k -deadline good -c:a libopus -b:a 64k
write red-blue-mp3.mp4 "${h264[@]}" -c:a libmp3lame -b:a 128k
