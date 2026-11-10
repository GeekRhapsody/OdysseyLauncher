"""The console theme's Switch 2 card's video (godot/themes/console/videos/switch2.mp4): the screen through the card's
focused clip, which the launcher plays on the model's `video` material, the screen, starting it again each time the
clip loops (A6 Card videos).

It follows the clip (switch2.py) frame for frame, by the timing in switch2_layout.py, and its cursor follows the path
the Joy-Con 2 follows on the table (switch2_layout.POINTER): the screen is off; POWER, and the HOME Menu fades in; the
right Joy-Con 2 comes off and is set down on its side, and the cursor appears (a black arrow); it glides to Dusty
Gulch's tile, which lights up, and clicks it; the HOME Menu fades to black as the game starts; its title fades in,
SHOOT TO START, and the cursor is the game's sights, which shoot it; a flash, and the street: five targets, each shot
as the sights stop on it (a flash at the sights, the outlaw thrown back or the bottle shattering, its points counted),
STAGE CLEAR!; the Joy-Con 2 is lifted and the sights go; POWER, and the screen goes dark, back to the switched-off
screen, which is also the first frame, so the loop is seamless.

Each frame is the glass as switch2_print.py draws it, at VIDEO_PX, encoded by card_video.py. Make the made-up games'
library and the paintings first (tools/made-up-games/README.md; paintings.py), then run it from the repo root with
the system Python (Pillow, numpy, scipy; ffmpeg on the PATH):

    python tools/console-models/switch2_video.py artifacts/made-up-games godot/themes/console/videos/switch2.mp4
"""

import math
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch2_layout as L  # noqa: E402
import switch2_print as P  # noqa: E402
from card_video import encode  # noqa: E402

BLACK = Image.new("RGBA", (P.W2, P.H2), (0, 0, 0, 255))
WHITE = Image.new("RGBA", (P.W2, P.H2), (255, 255, 255, 255))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def on_tile(f):
    """Whether the pointer is over the game's tile at frame f."""
    (x, y), shown = L.pointer(f)
    t = L.TILES
    return shown and t["x"] <= x <= t["x"] + t["size"] and t["y"] <= y <= t["y"] + t["size"]


def since(f, frames):
    """Frames since the latest of frames at or before f, or None."""
    past = [f0 for f0 in frames if f0 <= f]
    return f - max(past) if past else None


class Screens:
    """The LCD at each clip frame, W2 x H2, and what's over it: the cursor or the sights."""

    def __init__(self, made_up_dir):
        self.library = P.Library(made_up_dir)
        self.home = P.Home(self.library)
        self.street = P.Street()

    def lcd(self, f):
        """The LCD's picture at frame f, or None while it's off."""
        if f < L.ON[0] or f >= L.OFF[1]:
            return None
        if f < L.LAUNCH[0]:
            hover = sum(on_tile(g) for g in (f - 2, f - 1, f)) / 3
            press = smooth((f - L.CLICK_TILE) / 2) * (1 - smooth((f - L.CLICK_TILE - 3) / 3)) if f >= L.CLICK_TILE else 0
            img = self.home.frame(hover=hover, pressed=press, glow=0.5 + 0.5 * math.sin(f / 5))
            return Image.blend(BLACK, img, smooth((f - L.ON[0]) / (L.ON[1] - L.ON[0])))
        if f < L.LAUNCH[1]:
            img = self.home.frame(hover=1.0, glow=0.5 + 0.5 * math.sin(f / 5))
            return Image.blend(img, BLACK, smooth((f - L.LAUNCH[0]) / (L.LAUNCH[1] - L.LAUNCH[0] - 2)))
        if f < L.CLICK_START + 2:
            prompt = (f - L.TITLE[0]) % 24 < 16 if f < L.CLICK_START else True
            return P.title(self.library, prompt=prompt, fade=smooth((f - L.TITLE[0]) / 6))
        street = self.street.frame(f)
        if f < L.CLICK_START + 8:                          # the shot's white flash, the street coming through it
            return Image.blend(WHITE, street, smooth((f - L.CLICK_START - 1) / 7))
        if f >= L.OFF[0]:
            return Image.blend(street, BLACK, smooth((f - L.OFF[0]) / (L.OFF[1] - L.OFF[0] - 1)))
        return street

    def over(self, img, f):
        """The cursor on the HOME Menu, or the game's sights and a shot's flash, at the pointer."""
        (x, y), shown = L.pointer(f)
        x, y = P.n(x), P.n(y)
        if not shown or L.LAUNCH[0] <= f < L.TITLE[0] + 4:
            return img
        if f < L.LAUNCH[0]:
            P.arrow(img, x, y, smooth((f - L.CURSOR + 1) / 4))
            return img
        age = since(f, L.CLICKS)
        kick = max(0.0, 1 - age / 5) if age is not None else 0.0
        alpha = smooth((f - L.TITLE[0] - 4) / 4) * (1 - smooth((f - L.LIFT[0] + 1) / 3))
        if age is not None:
            P.muzzle(img, x, y, age)
        P.sights(img, x, y, alpha, kick)
        return img


def frames(made_up_dir):
    screens = Screens(made_up_dir)
    off = P.still()
    for f in range(L.LENGTH):
        lcd = screens.lcd(f)
        if lcd is None:
            yield off
            continue
        yield P.glass(P.half(screens.over(lcd.copy(), f)))


def main():
    made_up_dir, out = sys.argv[1], sys.argv[2]
    encode(out, L.VIDEO_PX, L.FPS, frames(made_up_dir), "Switch 2")


if __name__ == "__main__":
    main()
