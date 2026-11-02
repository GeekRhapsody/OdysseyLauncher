"""The console theme's Windows card's video (godot/themes/console/videos/windows.mp4): the monitor's screen through the
card's focused clip, which the launcher plays on the model's `video` material, the glass, starting it again each time
the clip loops (A6 Card videos).

It follows the clip (windows_pc.py) frame for frame, by the timing in windows_pc_layout.py, its pointer going where the
mouse does: the desktop; the pointer glides to Wyrmspire's icon and double-clicks it (the icon selected, the game
lighting up on the taskbar, the busy pointer); the screen goes black and the developer's splash fades in and out; the
title's art comes up and its menu slides in, the game's own pointer goes to Continue, lights it and clicks; the loading
screen; the play (windows_pc_print.Play), the camera behind the hero as W runs her, Shift sprints, A and D step her
aside and the mouse looks round, the beast falling to her two thrusts and its spoils taken on E; Esc, and the pause
menu over the blurred game, the pointer to Quit to Desktop, clicked; the game fades out, the desktop fades in and the
pointer goes back to its rest, the first frame, so the loop is seamless.

Each frame is the glass as windows_pc_print.py draws it, at VIDEO_PX, encoded by card_video.py. Make the made-up games'
library and the paintings first (tools/made-up-games/README.md; paintings.py), then run it from the repo root with the
system Python (Pillow, numpy, scipy; ffmpeg on the PATH):

    python tools/console-models/windows_pc_video.py artifacts/made-up-games godot/themes/console/videos/windows.mp4
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windows_pc_layout as L  # noqa: E402
import windows_pc_print as P  # noqa: E402
from card_video import encode  # noqa: E402
from pointer_path import held  # noqa: E402

BLACK = (0, 0, 0)


def lit(f, box, first, last):
    """How lit a menu item is at frame f: brightening over three frames from when the pointer came onto box, between
    first and last."""
    def on(g):
        return first <= g < last and P.on_item(L.POINTER.at(g), box)
    if not on(f):
        return 0.0
    since = f
    while on(since - 1):
        since -= 1
    return P.smooth((f - since + 1) / 3)


class Screens:
    """The glass at each frame of the clip."""

    def __init__(self, made_up):
        self.game = P.Wyrmspire(made_up)
        self.play = P.Play(self.game)
        self.frozen = None

    def desktop(self, f):
        img = P.desktop(selected=L.DOUBLE[0] <= f < L.LAUNCH[1] + 2,
                        launching=P.smooth(P.phase(f, L.LAUNCH[0], L.LAUNCH[1])) if f < L.QUIT[0] else 0.0)
        busy = L.LAUNCH[0] <= f < L.LAUNCH[1] + 2
        P.pointer(img, *L.POINTER.at(f), "busy" if busy else "arrow", f / L.FPS)
        return img

    def frame(self, f):
        if f < L.LAUNCH[1] or f >= L.QUIT[1]:
            if f == 0 or (f >= L.QUIT[1] + 4 and L.POINTER.at(f) == L.REST):
                return P.still()
            return P.finished(self.desktop(f))
        if f < L.SPLASH[0]:
            return Image.new("RGB", L.VIDEO_PX, BLACK)
        if f < L.SPLASH[1]:
            return P.finished(P.splash(P.phase(f, *L.SPLASH)))
        if f < L.TITLE[1]:
            n = f - L.TITLE[0]
            box = P.continue_box()
            img = P.title_screen(self.game, n, hover=lit(f, box, L.TITLE[0] + 12, L.TITLE[1]),
                                 pressed=held(f, L.CLICK_CONTINUE, L.CLICK))
            if L.TITLE[0] + 8 <= f < L.CLICK_CONTINUE + 6:
                P.pointer(img, *L.POINTER.at(f), "game")
            fade = min(P.smooth(n / 8), 1 - P.smooth(P.phase(f, L.CLICK_CONTINUE + 6, L.TITLE[1])))
            return P.finished(P.faded(img, fade))
        if f < L.LOADING[1]:
            return P.finished(P.faded(P.loading(f - L.LOADING[0]), P.smooth((f - L.LOADING[0] + 1) / 3)))
        if f < L.ESC:
            return P.finished(self.play.frame(f))
        if self.frozen is None:
            self.frozen = self.play.frame(L.ESC - 1)
        if f < L.QUIT[0]:
            hover = lit(f, P.quit_box(), L.ESC + 6, L.QUIT[0])
            img = P.paused(self.frozen, hover=hover, pressed=held(f, L.CLICK_QUIT, L.CLICK))
            if f >= L.ESC + 6:
                P.pointer(img, *L.POINTER.at(f), "game")
            return P.finished(Image.blend(self.frozen, img, P.smooth((f - L.ESC + 1) / 5)))
        half = (L.QUIT[0] + L.QUIT[1]) // 2
        if f < half:
            last = P.paused(self.frozen, hover=1.0)
            return P.finished(P.faded(last, 1 - P.smooth(P.phase(f, L.QUIT[0], half))))
        return P.finished(P.faded(self.desktop(f), P.smooth(P.phase(f, half, L.QUIT[1]))))


def frames(made_up):
    screens = Screens(made_up)
    for f in range(L.LENGTH):
        yield screens.frame(f)


def main():
    made_up, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    encode(out, L.VIDEO_PX, L.FPS, frames(made_up), "Windows")


if __name__ == "__main__":
    main()
