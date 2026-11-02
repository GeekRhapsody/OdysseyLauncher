"""The console theme's Flash card's video (godot/themes/console/videos/flash.mp4): the monitor's screen through the
card's focused clip, which the launcher plays on the model's `video` material, the glass, starting it again each time
the clip loops (A6 Card videos).

It follows the clip (flash.py) frame for frame, by the timing in flash_layout.py, and its pointer goes where the mouse
does: the page has just been loaded from Go, the pointer still on it; the preloader's bar fills in bursts to 100% and
the preloader fades; Odyssey's title comes up (the sky drifting, the name dropping in and bouncing, the ship sliding in,
PLAY popping up and breathing); the pointer glides to PLAY, turns to a hand and lights it, and PLAY is pressed as the
mouse dips; the title fades and the game comes in with the pointer hidden: the ship's nose follows the mouse as it
weaves, a bolt for each click, each hitting a rock, which bursts for its points; a right click, and the Flash Player's
menu fades in over the game, which it freezes, as the Flash Player did; the pointer goes down the items, lighting each,
to About Adobe Flash Player, out by the menu's edge and up to Go; Go clicked, the menu goes, the status bar shows the
page opening by the busy pointer, and the page goes white and comes back with the preloader at 0%, the first frame, so
the loop is seamless.

Each frame is the glass as flash_print.py draws it, at VIDEO_PX, encoded by card_video.py. Run it from the repo root
with the system Python (Pillow; ffmpeg on the PATH):

    python tools/console-models/flash_video.py godot/themes/console/videos/flash.mp4
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flash_layout as L  # noqa: E402
import flash_print as P  # noqa: E402
from card_video import encode  # noqa: E402

TITLE_IN = 8                 # frames the title takes to come up from black
GAME_IN = 6                  # the game's
MENU_IN = 4                  # the menu's fade in (Windows XP's)


def on_play(f):
    """Whether the pointer is on PLAY at frame f, once PLAY is there."""
    x, y = L.pointer(f)
    x0, y0, x1, y1 = L.PLAY
    return L.TITLE + 20 <= f < L.TITLE_OUT[1] and x0 <= x <= x1 and y0 <= y <= y1


def lit(f):
    """How lit PLAY is at frame f: brightening over three frames from when the pointer came onto it."""
    if not on_play(f):
        return 0.0
    since = f
    while on_play(since - 1):
        since -= 1
    return P.smooth((f - since + 1) / 3)


class Screens:
    """The glass at each frame of the clip."""

    def __init__(self):
        self.sky = P.Backdrop()
        self.game = P.Game()
        self.frozen = self.game.frame(L.FREEZE)
        self.menus = {}

    def menu(self, item, alpha):
        key = (item, alpha)
        if key not in self.menus:
            self.menus[key] = P.menu(item, alpha)
        return self.menus[key]

    def frame(self, f):
        x, y = L.pointer(f)
        if f < L.TITLE or f >= L.RELOADED:
            if f >= L.RELOADED:
                return P.still()
            movie = P.faded(P.preloader(L.loaded(f)), 1 - P.smooth(P.phase(f, *L.PRELOADER_OUT)))
            return P.screen(movie, cursor=(x, y, False, False))
        if f < L.GAME:
            n = f - L.TITLE
            movie = P.title(self.sky, n, hover=lit(f), down=L.held(f, L.CLICK_PLAY))
            movie = P.faded(movie, min(P.smooth(n / TITLE_IN), 1 - P.smooth(P.phase(f, *L.TITLE_OUT))))
            return P.screen(movie, cursor=(x, y, on_play(f), False))
        movie = self.game.frame(f) if f < L.FREEZE else self.frozen
        movie = P.faded(movie, P.smooth((f - L.GAME + 1) / GAME_IN))
        if f < L.FREEZE:
            return P.screen(movie)                   # the pointer hidden while the game plays
        menu = None
        if f < L.CLICK_GO:                           # the menu goes as Go is pressed
            menu = self.menu(P.menu_item(x, y), round(P.smooth((f - L.FREEZE + 1) / MENU_IN), 3))
        released = L.CLICK_GO + L.CLICK
        loading = f >= released
        return P.screen(movie, cursor=(x, y, False, loading), menu_layer=menu, status=P.STATUS if loading else "Done",
                        progress=round(P.phase(f, released, L.RELOADED), 3) if loading else None,
                        go_down=L.held(f, L.CLICK_GO), blank=L.BLANK[0] <= f < L.BLANK[1])


def frames():
    screens = Screens()
    for f in range(L.LENGTH):
        yield screens.frame(f)


def main():
    encode(sys.argv[1], L.VIDEO_PX, L.FPS, frames(), "Flash")


if __name__ == "__main__":
    main()
