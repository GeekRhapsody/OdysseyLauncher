"""The console theme's PlayStation Portable card's video (godot/themes/console/videos/psp.mp4): the screen through the
card's focused clip, which the launcher plays on the model's `video` material, the glass, starting it again each time
the clip loops (A6 Card videos).

It follows the clip (psp.py) frame for frame, by the timing in psp_layout.py: the screen is off while the console turns
round, takes the UMD and turns back; POWER, and the backlight comes on; the PSP's start-up (a line of light swelling
into a glow, SONY COMPUTER ENTERTAINMENT); the XMB fades in, its wave drifting, the UMD's game at the top of the Game
column, its icon breathing, then its own picture fading in behind the menu; CROSS (the clip presses it) flashes the
icon and the XMB fades out; the game loads, its title comes up with PRESS START blinking, START (pressed) blinks it
quickly and the screen flashes to the game: Skylance (made up), flown on the nub (the ship slides and banks as the clip
pushes it), CROSS firing the wingtips' bolts, two fighters blown up, the score going up; then POWER held up, the picture
fades and the backlight dies, back to the switched-off screen, which is also the first frame, so the loop is seamless.

Each frame is the glass as psp_print.py draws it, at VIDEO_PX, encoded by card_video.py. Make the made-up games'
library first (tools/made-up-games/README.md), then run it from the repo root with the system Python (Pillow, numpy,
scipy; ffmpeg on the PATH):

    python tools/console-models/psp_video.py artifacts/made-up-games godot/themes/console/videos/psp.mp4
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psp_layout as L  # noqa: E402
import psp_print as P  # noqa: E402
from card_video import encode  # noqa: E402

BLACK = Image.new("RGB", L.LCD_PX, (0, 0, 0))
WHITE = Image.new("RGB", L.LCD_PX, (255, 255, 255))
LIT = 2                      # frames from POWER to the backlight coming on
FLASH = 3                    # frames the chosen icon flashes for
LAST_GAME = L.SCREEN_OFF[0] + 4   # the game's last frame, which fades out


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def screen(f, game, sky):
    """The LCD at clip frame f, or None while it's switched off; and how far its backlight has died (0 to 1)."""
    if f < L.POWER_ON + LIT or f >= L.SCREEN_OFF[1]:
        return None, 0.0
    if f < L.BOOT[0]:
        return BLACK, 0.0
    if f < L.BOOT[1]:
        return P.boot((f - L.BOOT[0]) / (L.BOOT[1] - L.BOOT[0])), 0.0
    if f < L.XMB[1]:
        t = (f - L.XMB[0]) / L.FPS
        fade = min(smooth((f - L.XMB[0]) / 6), 1 - smooth((f - L.CROSS - FLASH) / (L.XMB[1] - L.CROSS - FLASH - 1)))
        chosen = smooth((f - L.CROSS) / 2) if f >= L.CROSS else 0.0
        return P.xmb(game, t, background=smooth((f - L.XMB[0] - 10) / 8), chosen=chosen, fade=fade), 0.0
    if f < L.TITLE[0]:
        return BLACK, 0.0
    if f < L.TITLE[1]:
        t = (f - L.TITLE[0]) / L.FPS
        if f < L.START:
            prompt = (f - L.TITLE[0]) % 20 < 13
        else:
            prompt = (f - L.START) % 4 < 2
        flash = smooth((f - (L.TITLE[1] - 4)) / 4)
        return P.title(game, t, prompt=prompt, fade=smooth((f - L.TITLE[0]) / 6), flash=flash), 0.0
    lcd = sky.frame(min(f, LAST_GAME))
    if f < L.PLAY[0] + 4:
        lcd = Image.blend(WHITE, lcd, smooth((f - L.PLAY[0]) / 4))
    if f >= L.SCREEN_OFF[0]:
        lcd = Image.blend(lcd, BLACK, smooth((f - L.SCREEN_OFF[0]) / 4))
    return lcd, smooth((f - L.SCREEN_OFF[0] - 4) / 4)


def frames(game):
    sky = P.Sky(game)
    off = P.glass()
    for f in range(L.LENGTH):
        lcd, dying = screen(f, game, sky)
        yield off if lcd is None else P.glass(lcd, off=dying)


def main():
    made_up_dir, out = sys.argv[1], sys.argv[2]
    game = P.made_up(made_up_dir)
    encode(out, L.VIDEO_PX, L.FPS, frames(game), "PSP")


if __name__ == "__main__":
    main()
