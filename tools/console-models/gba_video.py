"""The console theme's Game Boy Advance card's video (godot/themes/console/videos/gba.mp4): the lens and its screen
through the card's focused clip, which the launcher plays on the model's `video` material, starting it again each time
the clip loops (A6 Card videos).

It follows the clip (gba.py) frame for frame, by the timing in gba_layout.py: the screen is off while the cartridge
goes in and the switch slides to ON; then it lights white and the start-up runs (GAME BOY appearing behind a sweeping
light, a shine, Nintendo under it); Kaleidrop's title (a made-up game) fades in, its gems hopping and PRESS START
blinking, until START is pressed; then a round of play, its pair of gems moved, turned and dropped as the D-pad, A, B
and R are pressed, and two rows of three shattering; when the switch slides to OFF the picture fades out, and the
screen is off again for the cartridge to come out, as it is in the first frame, so the loop is seamless.

Each frame is the whole lens as gba_print.py draws it (its printing, the LCD's border, the screen at two video pixels
a screen pixel), VIDEO_PX, encoded by card_video.py. Run from the repo root (ffmpeg on the PATH):

    python tools/console-models/gba_video.py artifacts/made-up-games godot/themes/console/videos/gba.mp4
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gba_layout as L  # noqa: E402
import gba_print as P  # noqa: E402
from card_video import encode  # noqa: E402

LIGHT = 5                         # frames the screen takes to light
FADE = 6                          # frames it takes to go off
OFF = L.POWER_OFF[0] + 2          # the picture starts to fade as the switch reaches OFF
WHITE = (255, 255, 255)


def whiten(img, t):
    """img faded towards white by t (0 to 1)."""
    return Image.blend(img, Image.new("RGB", img.size, WHITE), max(0.0, min(1.0, t)))


def screen(made_up, f):
    """The screen at frame f: (its 240 x 160 picture, or None, and how lit it is: 0 off, 1 on)."""
    if f < L.BOOT or f >= OFF + FADE:
        return None, 0.0
    level = min(1.0, (f - L.BOOT + 1) / LIGHT)
    if f >= OFF:
        level = 1.0 - (f - OFF + 1) / FADE
    if f < L.TITLE:
        return P.boot(f - L.BOOT), level
    if f < L.GAME:
        pressed = f - L.START if f >= L.START else None
        img = whiten(P.title(made_up, f - L.TITLE, pressed), 1.0 - (f - L.TITLE) / 6.0)
        if f >= L.START + 4:
            img = whiten(img, (f - L.START - 4) / (L.GAME - L.START - 4))
        return img, level
    return whiten(P.play(made_up, f), 1.0 - (f - L.GAME) / 4.0), level


def frames(made_up):
    base = P.lens()
    for f in range(L.LENGTH):
        content, level = screen(made_up, f)
        yield P.frame(base, content, level)


def main():
    made_up, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    encode(out, L.VIDEO_PX, L.FPS, frames(made_up), "Game Boy Advance")


if __name__ == "__main__":
    main()
