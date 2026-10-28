"""Encodes a console theme card's video (godot/themes/console/videos/<id>.mp4), which the launcher plays on the card's
`video` material while it's focused, starting it again from its first frame each time the card's focused clip loops
(A6 Card videos). The cards' video scripts (game_boy_video.py, psp_video.py, ...) draw its frames, following their
clips frame for frame; this pipes them to ffmpeg as raw RGB.

The settings are amstrad_cpc_video.py's: H.264 4:2:0 (High profile: Media Foundation decodes it; it can't decode 4:4:4),
tuned for animation, a key frame every second (so a restart is quick), no sound. Run with the system Python (Pillow;
ffmpeg on the PATH).
"""

import os
import subprocess
import sys


def encode(out, size, fps, frames, label):
    """Writes frames (Pillow images of size, in order) to out as a card's video, and prints a line about it."""
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    width, height = size
    if width % 2 or height % 2:
        sys.exit(f"{label}: {width} x {height}: H.264's 4:2:0 needs even sides")
    encoder = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-preset", "veryslow", "-tune", "animation", "-crf", "18",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-g", str(fps), "-movflags", "+faststart", "-an", out],
        stdin=subprocess.PIPE)
    count = 0
    for frame in frames:
        if frame.size != (width, height):
            encoder.kill()
            sys.exit(f"{label}: frame {count} is {frame.size[0]} x {frame.size[1]}, not {width} x {height}")
        encoder.stdin.write(frame.convert("RGB").tobytes())
        count += 1
    encoder.stdin.close()
    if encoder.wait() != 0:
        sys.exit(f"{label}: ffmpeg failed")
    print(f"{label} video: {count} frames at {fps} fps, {width} x {height}, {os.path.getsize(out) // 1024} KB")
    return count
