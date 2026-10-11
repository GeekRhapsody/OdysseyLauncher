"""The console theme's Amstrad CPC card's video (godot/themes/console/videos/amstradcpc.mp4): the CTM644's screen through
the card's focused clip, which the launcher plays on the model's `video` material, starting it again each time the clip
loops (A6 Card videos).

It follows the clip (amstrad_cpc.py) frame for frame, by the timing in amstrad_cpc_layout.py: BASIC's boot screen
while the door opens and the cassette goes in; RUN" typed once the door has shut; "Press PLAY then any key:"; once
PLAY and ENTER are down, "Loading ODYSSEY block 1"; then the loader clears the screen to black and the game's picture
loads at a steady rate, a pixel row of every character row at a time, as the CPC's screen memory fills; the title runs
(its grid rolling, its stars twinkling, PRESS FIRE blinking) while the tape is ejected; and when the cassette is out
the computer resets to the boot screen, which is also the first frame, so the loop is seamless.

Each frame is the glass as amstrad_cpc_print.py draws it, at VIDEO_PX, piped to ffmpeg as raw RGB and encoded as
H.264 4:2:0 (High profile: Media Foundation decodes it; it can't decode 4:4:4) with a key frame every second, no
sound. Run from the repo root (ffmpeg on the PATH):

    python tools/console-models/amstrad_cpc_video.py godot/themes/console/videos/amstradcpc.mp4
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amstrad_cpc_layout as L  # noqa: E402
import amstrad_cpc_print as P  # noqa: E402

COMMAND = 'run"'
TYPED = 84                 # the first of RUN"'s characters, once the door has shut (DOOR_SHUT)
PER_CHARACTER = 3          # frames between characters
PRESS_SHOWN = 98           # RUN"'s own ENTER: "Press PLAY then any key:"
FOUND = L.ENTER + 6        # the tape's header found: "Loading ODYSSEY block 1"
CLEARED = FOUND + 14       # the loader sets mode 0 and clears the screen to black
LOADED = (CLEARED + 2, 188)  # the picture's 16 KB, at a steady rate
BLANK = 5                  # frames of a blank screen at the reset


def screen(f, full):
    """The CPC's screen at frame f: (the paper, 320 x 200, and the border's colour)."""
    if f >= L.RESET + BLANK or f < TYPED:
        return P.text_screen(P.BOOT, (0, 8))
    if f >= L.RESET:
        return P.loading(full, 0), P.BLACK
    if f < PRESS_SHOWN:
        typed = COMMAND[:min(len(COMMAND), (f - TYPED) // PER_CHARACTER + 1)]
        return P.text_screen(P.BOOT + [typed], (len(typed), 8))
    if f < FOUND:
        return P.text_screen(P.PRESS, (24, 9))
    if f < CLEARED:
        return P.text_screen(P.LOADING)
    start, end = LOADED
    if f < end:
        loaded = round(P.SCREEN_BYTES * max(0, f - start) / (end - start))
        return P.loading(full, loaded), P.BLACK
    return P.picture((f - end) / L.FPS, prompt=True), P.BLACK


def main():
    out = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    width, height = L.VIDEO_PX
    encoder = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(L.FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "veryslow", "-tune", "animation", "-crf", "18",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-g", str(L.FPS), "-movflags", "+faststart", "-an", out],
        stdin=subprocess.PIPE)
    full = P.picture()
    cache = {}
    for f in range(L.LENGTH):
        paper, border = screen(f, full)
        key = (paper.tobytes(), border)
        if key not in cache:
            cache.clear()                            # frames repeat in runs: keep only the last
            cache[key] = P.glass(paper, border, L.VIDEO_PX).tobytes()
        encoder.stdin.write(cache[key])
    encoder.stdin.close()
    if encoder.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"Amstrad CPC video: {L.LENGTH} frames at {L.FPS} fps, {width} x {height}, {os.path.getsize(out) // 1024} KB")


if __name__ == "__main__":
    main()
