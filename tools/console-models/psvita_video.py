"""The console theme's PlayStation Vita card's video (godot/themes/console/videos/psvita.mp4): the screen through the
card's focused clip, which the launcher plays on the model's `video` material, the glass, starting it again each time
the clip loops (A6 Card videos).

It follows the clip (psvita.py) frame for frame, by the timing in psvita_layout.py: the screen is off; the PS button,
and the lock screen comes on; a finger peels it away from its top right corner to the bottom left, onto the home
screen's bubbles; it taps the game's bubble, whose LiveArea opens out of it, and Start on its gate, which opens over the
screen; Arcwave's name, then Voltcrown's title, PRESS START BUTTON blinking until START is pressed; the fight (Juno
walks in on the left stick, a punch, a kick and a punch land, VOLT lights on the screen and is touched, the finisher,
K.O.); the PS button, and the LiveArea again, the gate showing the paused fight and Continue; the finger peels the page
away to close the game, back to the bubbles; POWER, and the screen goes dark, back to the switched-off screen, which
is also the first frame, so the loop is seamless.

Each frame is the glass as psvita_print.py draws it, at VIDEO_PX, encoded by card_video.py. Make the made-up games'
library and the paintings first (tools/made-up-games/README.md; paintings.py), then run it from the repo root with the
system Python (Pillow, numpy, scipy; ffmpeg on the PATH):

    python tools/console-models/psvita_video.py artifacts/made-up-games godot/themes/console/videos/psvita.mp4
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psvita_layout as L  # noqa: E402
import psvita_print as P  # noqa: E402
from card_video import encode  # noqa: E402

BLACK = Image.new("RGB", L.LCD_PX, (0, 0, 0))
WHITE = Image.new("RGB", L.LCD_PX, (255, 255, 255))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_in(t):
    t = min(1.0, max(0.0, t))
    return t * t


def drag(f, span, start, end, fling):
    """The finger's point while it peels a page: from start to end (in the OLED's pixels) over the first three
    quarters of span, then let go: the page's corner flies on to fling, past the far corner. (point, finger down)."""
    a, b = span
    release = a + (b - a) * 0.75
    if f < release:
        t = smooth((f - a) / (release - a))
        return (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t), True
    t = ease_in((f - release) / (b - release))
    return (end[0] + (fling[0] - end[0]) * t, end[1] + (fling[1] - end[1]) * t), False


class Screens:
    """The OLED at each clip frame, LCD_PX, and where the finger is on it."""

    def __init__(self, game):
        self.game = game
        self.fight = P.Fight(game)
        self.gate_start = P.gate_picture(game)
        self.paused = None

    def corner(self):
        x, y = P.page_corner()
        return x / P.K, y / P.K

    def page_live(self, paused=False, pressed=0.0):
        picture = self.paused if paused else self.gate_start
        return P.live_page(self.game, picture, paused=paused, pressed=pressed)

    def home(self, f, pressed=0.0, apps=(), dim=1.0):
        return P.home(f / L.FPS, pressed=pressed, apps=apps, game=self.game, arrow=bool(apps), dim=dim)

    def frame(self, f):
        """(the OLED, LCD_PX, or None while it's off; a finger on it: (x, y, press, ripple) or None)."""
        if f < L.WAKE + 3 or f >= L.SCREEN_OFF[1]:
            return None, None
        if f < L.PEEL_LOCK[0]:
            fade = smooth((f - L.WAKE - 3) / 4)
            lcd = P.half(self.lock())
            return Image.blend(BLACK, lcd, fade), None
        if f < L.PEEL_LOCK[1]:
            (x, y), down = drag(f, L.PEEL_LOCK, (960 - P.CURL, P.CURL), (330, 400), (-1500, 1700))
            under = self.home(f)
            cx, cy = 960 * P.K, 0.0
            img = P.peel(under, P.lock_page(), (cx, cy), (x * P.K, y * P.K))
            finger = (x - 10, y + 10, 1.0, 0.0) if down and f >= L.PEEL_LOCK[0] + 1 else None
            return P.half(img), finger
        if f < L.OPEN[0]:
            press = smooth((f - L.TAP_GAME) / 2) * (1 - smooth((f - L.TAP_GAME - 4) / 3)) if f >= L.TAP_GAME else 0.0
            finger = None
            if L.TAP_GAME - 5 <= f < L.TAP_GAME + 5:
                gx, gy = P.GAME_BUBBLE
                finger = (gx + 6, gy + 10, min(1.0, (f - L.TAP_GAME + 5) / 4), smooth((f - L.TAP_GAME) / 5) if f >= L.TAP_GAME else 0.0)
            return P.half(self.home(f, pressed=press)), finger
        if f < L.OPEN[1]:
            return P.half(self.opening(f)), None
        if f < L.GATE[0]:
            pressed = 0.0
            finger = None
            if f >= L.TAP_START - 5:
                pressed = smooth((f - L.TAP_START) / 2) if f >= L.TAP_START else 0.0
                finger = (P.GATE["x"] + 8, P.GATE["y"] + P.GATE["h"] / 2 + 4, min(1.0, (f - L.TAP_START + 5) / 4),
                          smooth((f - L.TAP_START) / 5) if f >= L.TAP_START else 0.0)
            img = P.live_screen(self.game, self.page_live(pressed=pressed))
            return P.half(img), finger
        if f < L.GATE[1]:
            return self.gate_opening(f), None
        if f < L.SPLASH[1]:
            return P.half(P.splash((f - L.SPLASH[0]) / (L.SPLASH[1] - L.SPLASH[0]))), None
        if f < L.TITLE[1]:
            t = (f - L.TITLE[0]) / L.FPS
            prompt = (f - L.TITLE[0]) % 24 < 16 if f < L.START else (f - L.START) % 4 < 2
            flash = smooth((f - (L.TITLE[1] - 4)) / 4)
            return P.half(P.title(self.game, t, prompt=prompt, flash=flash, fade=smooth((f - L.TITLE[0]) / 6))), None
        if f < L.FIGHT[1]:
            lcd = self.fight.frame(f).resize(L.LCD_PX, Image.LANCZOS)
            if f < L.FIGHT[0] + 4:
                lcd = Image.blend(WHITE, lcd, smooth((f - L.FIGHT[0]) / 4))
            finger = None
            if L.TOUCH_VOLT - 4 <= f < L.TOUCH_VOLT + 5:
                vx, vy = P.VOLT_AT
                finger = (vx + 6, vy + 8, min(1.0, (f - L.TOUCH_VOLT + 4) / 3),
                          smooth((f - L.TOUCH_VOLT) / 5) if f >= L.TOUCH_VOLT else 0.0)
            return lcd, finger
        if f < L.PAUSED[0]:
            return self.fight.frame(L.FIGHT[1] - 1).resize(L.LCD_PX, Image.LANCZOS), None
        if self.paused is None:
            self.paused = self.fight.frame(L.FIGHT[1] - 1).resize((600, 340), Image.LANCZOS).convert("RGBA")
        if f < L.PEEL_LIVE[0]:
            img = P.live_screen(self.game, self.page_live(paused=True))
            return P.half(img), None
        if f < L.PEEL_LIVE[1]:
            cx, cy = self.corner()
            (x, y), down = drag(f, L.PEEL_LIVE, (cx - P.CURL, cy + P.CURL), (300, 470), (-1500, 1700))
            under = self.home(f, dim=0.62 + 0.38 * smooth((f - L.PEEL_LIVE[0]) / (L.PEEL_LIVE[1] - L.PEEL_LIVE[0])))
            img = P.peel(under, self.page_live(paused=True), (cx * P.K, cy * P.K), (x * P.K, y * P.K))
            finger = (x - 10, y + 10, 1.0, 0.0) if down and f >= L.PEEL_LIVE[0] + 1 else None
            return P.half(img), finger
        img = P.half(self.home(f))
        if f >= L.SCREEN_OFF[0]:
            img = Image.blend(img, BLACK, smooth((f - L.SCREEN_OFF[0]) / (L.SCREEN_OFF[1] - L.SCREEN_OFF[0] - 1)))
        return img, None

    def lock(self):
        """The lock screen over the home screen, its top right corner turned over."""
        cx = 960 * P.K
        return P.peel(P.home(0.0, game=self.game), P.lock_page(), (cx, 0.0), (cx - P.n(P.CURL), P.n(P.CURL)))

    def opening(self, f):
        """The game's LiveArea opening out of its bubble: the page growing from the bubble over the dimming home
        screen."""
        t = smooth((f - L.OPEN[0]) / (L.OPEN[1] - L.OPEN[0]))
        under = self.home(f, dim=1 - 0.38 * t)
        screen = P.live_screen(self.game, self.page_live(), bar=False)
        gx, gy = P.GAME_BUBBLE
        s = 0.12 + 0.88 * t
        w, h = round(P.W2 * s), round(P.H2 * s)
        small = screen.resize((w, h), Image.LANCZOS)
        cx = P.n(gx) + (P.W2 / 2 - P.n(gx)) * t
        cy = P.n(gy) + (P.H2 / 2 - P.n(gy)) * t
        small.putalpha(round(255 * min(1.0, t * 2.5)))
        under.alpha_composite(small, (round(cx - w / 2), round(cy - h / 2)))
        P.info_bar(under, ("game",), self.game)
        return under

    def gate_opening(self, f):
        """The gate growing out over the screen as the game starts, then fading to black."""
        t = smooth((f - L.GATE[0]) / (L.GATE[1] - L.GATE[0]))
        base = P.half(P.live_screen(self.game, self.page_live(pressed=1.0)))
        pic = self.gate_start.convert("RGB")
        g = P.GATE
        s = L.LCD_PX[0] / L.NATIVE[0]
        w0, h0 = g["w"] * s, g["h"] * s
        w = w0 + (L.LCD_PX[0] - w0) * t
        h = h0 + (L.LCD_PX[1] - h0) * t
        cx = g["x"] * s + (L.LCD_PX[0] / 2 - g["x"] * s) * t
        cy = g["y"] * s + (L.LCD_PX[1] / 2 - g["y"] * s) * t
        grown = pic.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)
        base.paste(grown, (round(cx - w / 2), round(cy - h / 2)))
        return Image.blend(base, BLACK, smooth((t - 0.55) / 0.45))


def frames(game):
    screens = Screens(game)
    off = P.glass()
    for f in range(L.LENGTH):
        lcd, finger = screens.frame(f)
        if lcd is None:
            yield off
            continue
        if finger:
            lcd = P.touch(lcd, finger[0], finger[1], finger[2], finger[3])
        yield P.glass(lcd, off=0.0)


def main():
    made_up_dir, out = sys.argv[1], sys.argv[2]
    game = P.made_up(made_up_dir)
    encode(out, L.VIDEO_PX, L.FPS, frames(game), "PS Vita")


if __name__ == "__main__":
    main()
