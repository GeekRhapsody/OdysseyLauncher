"""The Windows 9x card's screens (retro_pc_print.py draws its still with them, retro_pc_video.py its video), following
its clip frame for frame by the timing in windows9x_layout.py. Run with the system Python (Pillow, numpy).

The desktop of Windows 9x at 640 x 480, drawn pixel for pixel as it drew itself: the teal desktop and its icons, their
titles in MS Sans Serif (raster_fonts.py reads Windows' own bitmap fonts), the taskbar with the Start button (its
four-colour flag, a made-up one, not Microsoft's) and the clock; windows with Windows 98's gradient title bars and their
3D buttons. Apex Circuit (made up, tools/made-up-games) comes up as its CD's AutoPlay window: its key art, its logo and
the buttons to play, install, explore the CD or leave.

The race, in the 3D of 1998: the road drawn in perspective a segment at a time (its curves and its gentle hills, the
grass's and the kerbs' bands, the lines), the coast behind it (a Codex painting, paintings.py's w9x_apex_horizon)
turning with the road, palms, cypresses, tyre walls and a grandstand along it and rivals ahead (w9x_apex_props and
w9x_apex_cars, cut out of their green), each scaled by its distance; the player's car from behind, turning with the
arrows (windows9x_layout.STEER); the position, the lap, the time and the speed over it.

The pointer: Windows' arrow, with the hourglass beside it while the CD's read, hidden while the game's played.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import raster_fonts as R  # noqa: E402
import retro_pc_layout as K  # noqa: E402
import retro_pc_screens as S  # noqa: E402
import windows9x_layout as L  # noqa: E402
from windows3x_screens import ARROW, bitmap  # noqa: E402
from windows_pc_print import FONTS  # noqa: E402

TEAL, NAVY, WHITE, BLACK = (0, 128, 128), (0, 0, 128), (255, 255, 255), (0, 0, 0)
FACE, LIGHT, SHADOW = (192, 192, 192), (223, 223, 223), (128, 128, 128)
SMALL_HOURGLASS = ["XXXXXXX", "X.....X", " X...X", "  X.X", "  X.X", " X...X", "X.....X", "XXXXXXX"]


def raised(d, x0, y0, x1, y1, pressed=False):
    """A Windows 95 3D face: white and light grey on its top and left, dark grey and black under and right (swapped
    while it's pressed)."""
    d.rectangle([x0, y0, x1, y1], fill=FACE)
    outer = (BLACK, WHITE) if pressed else (WHITE, BLACK)
    inner = (SHADOW, LIGHT) if pressed else (LIGHT, SHADOW)
    for (tl, br), k in ((outer, 0), (inner, 1)):
        d.line([(x0 + k, y1 - k), (x0 + k, y0 + k), (x1 - k, y0 + k)], fill=tl)
        d.line([(x1 - k, y0 + k), (x1 - k, y1 - k), (x0 + k, y1 - k)], fill=br)


def sunken(d, x0, y0, x1, y1):
    d.line([(x0, y1), (x0, y0), (x1, y0)], fill=SHADOW)
    d.line([(x1, y0), (x1, y1), (x0, y1)], fill=WHITE)


def flag(img, x, y, s=1.0):
    """The Start button's flag: four coloured panes waving (a made-up one)."""
    d = ImageDraw.Draw(img)
    for k, c in enumerate(((228, 46, 36), (52, 168, 60), (36, 88, 210), (246, 200, 30))):
        cx, cy = x + (k % 2) * 7 * s, y + (k // 2) * 6 * s
        d.polygon([(cx, cy + 1 * s), (cx + 6 * s, cy), (cx + 6 * s, cy + 5 * s), (cx, cy + 6 * s)], fill=c)


def icon(img, kind, x, y):
    """A 32 x 32 desktop icon, its top left at (x, y)."""
    d = ImageDraw.Draw(img)
    if kind == "computer":
        d.rectangle([x + 4, y + 3, x + 27, y + 20], fill=(206, 200, 184), outline=BLACK)
        d.rectangle([x + 7, y + 6, x + 24, y + 17], fill=TEAL)
        d.rectangle([x + 2, y + 23, x + 29, y + 29], fill=(206, 200, 184), outline=BLACK)
        d.line([(x + 18, y + 26), (x + 26, y + 26)], fill=BLACK)
    elif kind == "bin":
        d.polygon([(x + 7, y + 8), (x + 25, y + 8), (x + 23, y + 30), (x + 9, y + 30)], fill=(220, 220, 220),
                  outline=BLACK)
        d.rectangle([x + 5, y + 5, x + 27, y + 8], fill=(200, 200, 200), outline=BLACK)
        for k in range(3):
            d.line([(x + 11 + k * 5, y + 11), (x + 12 + k * 4, y + 27)], fill=SHADOW)
    elif kind == "inbox":
        d.polygon([(x + 3, y + 14), (x + 29, y + 14), (x + 27, y + 28), (x + 5, y + 28)], fill=(240, 200, 80),
                  outline=BLACK)
        d.rectangle([x + 9, y + 6, x + 24, y + 16], fill=WHITE, outline=BLACK)
        d.line([(x + 9, y + 6), (x + 16, y + 12), (x + 24, y + 6)], fill=BLACK)
    elif kind == "globe":
        d.ellipse([x + 4, y + 4, x + 28, y + 28], fill=(60, 120, 220), outline=BLACK)
        d.polygon([(x + 10, y + 8), (x + 17, y + 10), (x + 15, y + 18), (x + 9, y + 15)], fill=(70, 170, 70))
        d.polygon([(x + 19, y + 16), (x + 25, y + 18), (x + 22, y + 25)], fill=(70, 170, 70))
    elif kind == "speaker":
        d.polygon([(x, y + 3), (x + 3, y + 3), (x + 7, y), (x + 7, y + 10), (x + 3, y + 7), (x, y + 7)], fill=BLACK)


def caption(img, rect, title):
    """A Windows 98 window's frame and its title bar (navy fading to blue), the close button; returns its client
    area."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = rect
    raised(d, x0, y0, x1, y1)
    for x in range(x0 + 3, x1 - 2):
        t = (x - x0) / (x1 - x0)
        d.line([(x, y0 + 3), (x, y0 + 20)], fill=(round(16 * t), round(132 * t), round(128 + 80 * t)))
    R.sans(13).draw(img, x0 + 8, y0 + 5, title, WHITE, bold=True)
    raised(d, x1 - 21, y0 + 5, x1 - 5, y0 + 18)
    d.line([(x1 - 16, y0 + 8), (x1 - 10, y0 + 14)], fill=BLACK, width=2)
    d.line([(x1 - 16, y0 + 14), (x1 - 10, y0 + 8)], fill=BLACK, width=2)
    return (x0 + 3, y0 + 22, x1 - 3, y1 - 3)


class Race:
    """The race at 640 x 480, frame by frame from L.RACE[0]."""

    W, H = 640, 480
    HORIZON = 206
    SEG, ROAD, CAMERA, DEPTH, DRAW = 200.0, 1800.0, 1100.0, 0.84, 110

    def __init__(self, made_up):
        sky = S.painting("w9x_apex_horizon")
        k = (self.HORIZON + 30) / sky.height
        self.sky = sky.resize((round(sky.width * k), self.HORIZON + 30), Image.LANCZOS)
        cars = S.sprites("w9x_apex_cars")
        self.player, self.turning, rival_a, rival_b = cars
        self.rivals = [rival_a, rival_b]
        palm, cypress, tyres, stand = S.sprites("w9x_apex_props")
        self.props = dict(palm=palm, cypress=cypress, tyres=tyres, stand=stand)
        total = int(L.SPEED * (L.RACE[1] - L.RACE[0])) + self.DRAW + 20
        self.curve = [0.0] * total
        for a, b, c in L.CURVES:
            for i in range(a, b):
                ramp = min(1.0, (i - a) / 8, (b - i) / 8)
                self.curve[i] = c * ramp
        self.hill = [900.0 * math.sin(i / 34.0) * min(1.0, i / 60.0) for i in range(total)]
        rng = random.Random(9)
        self.scenery = []
        for i in range(6, total, 9):                             # trees well back from the road, the coast between
            side = -1 if (i // 9) % 2 else 1
            kind = "palm" if (i // 9) % 3 else "cypress"
            self.scenery.append((i, side * (2.2 + rng.uniform(0.0, 0.5)), kind))
            if (i // 9) % 4 == 0:
                self.scenery.append((i + 4, -side * (2.3 + rng.uniform(0.0, 0.4)), "palm"))
        for a, b, c in L.CURVES:                                 # tyre walls on the outside of each curve
            for i in range(a, b, 4):
                self.scenery.append((i, 1.3 if c > 0 else -1.3, "tyres"))
        self.scenery += [(96, -2.9, "stand"), (101, -2.9, "stand"), (170, 2.9, "stand")]
        self.racers = [(26.0, 1.62, -0.38, 0), (70.0, 1.74, 0.34, 1), (150.0, 1.66, -0.2, 0)]
        self.hud = ImageFont.truetype(FONTS + "FRAHVIT.TTF", 30)
        self.hud_small = ImageFont.truetype(FONTS + "FRAHVIT.TTF", 20)

    def steering(self, f):
        for a, b, side in L.STEER:
            if a <= f < b:
                return side
        return None

    def frame(self, f):
        t = f - L.RACE[0]
        pos = t * L.SPEED
        base = int(pos)
        frac = pos - base
        img = Image.new("RGB", (self.W, self.H))
        turned = sum(self.curve[:base]) + self.curve[base] * frac
        sx = round(turned * 6.0) % self.sky.width                 # the coast turns as the road does
        sky = self.sky.crop((sx, 0, sx + self.W, self.sky.height)) if sx + self.W <= self.sky.width else None
        if sky is None:
            sky = Image.new("RGB", (self.W, self.sky.height))
            sky.paste(self.sky.crop((sx, 0, self.sky.width, self.sky.height)), (0, 0))
            sky.paste(self.sky.crop((0, 0, self.W - (self.sky.width - sx), self.sky.height)), (self.sky.width - sx, 0))
        img.paste(sky, (0, self.HORIZON + 30 - sky.height))
        d = ImageDraw.Draw(img)
        d.rectangle([0, self.HORIZON + 30, self.W, self.H], fill=(84, 150, 60))
        cam_y = self.CAMERA + self.hill[base] + (self.hill[base + 1] - self.hill[base]) * frac
        x, dx = 0.0, -self.curve[base] * frac
        clip = self.H
        projected = []
        for n in range(self.DRAW):
            i = base + n
            z0, z1 = (n - frac) * self.SEG, (n + 1 - frac) * self.SEG
            if z0 <= 1.0:
                z0 = 1.0
            a = self._project(x, self.hill[i] - cam_y, z0)
            b = self._project(x + dx, self.hill[i + 1] - cam_y, z1)
            x += dx
            dx += self.curve[i]
            projected.append((i, a, b))
            if b[1] >= clip or b[1] >= a[1]:
                continue
            light = (i // 3) % 2 == 0
            grass = (100, 168, 70) if light else (84, 150, 60)
            d.polygon([(0, b[1]), (self.W, b[1]), (self.W, min(a[1], clip)), (0, min(a[1], clip))], fill=grass)
            for k, colour in ((1.18, (220, 30, 30) if light else (245, 245, 245)), (1.0, (108, 108, 112) if light
                                                                                       else (100, 100, 104))):
                d.polygon([(a[0] - a[2] * k, a[1]), (a[0] + a[2] * k, a[1]), (b[0] + b[2] * k, b[1]),
                           (b[0] - b[2] * k, b[1])], fill=colour)
            if light:
                for lane in (-0.33, 0.33):
                    d.polygon([(a[0] + a[2] * (lane - 0.015), a[1]), (a[0] + a[2] * (lane + 0.015), a[1]),
                               (b[0] + b[2] * (lane + 0.015), b[1]), (b[0] + b[2] * (lane - 0.015), b[1])],
                              fill=(236, 236, 236))
            clip = min(clip, b[1])
        sprites = []
        for i, offset, kind in self.scenery:
            if base < i < base + self.DRAW - 1:
                sprites.append((i, offset, self.props[kind], {"palm": 1.5, "cypress": 1.0, "tyres": 0.45,
                                                              "stand": 2.6}[kind]))
        for start, speed, lane, which in self.racers:
            at = start + speed * t
            if base < at < base + self.DRAW - 1:
                sprites.append((at, lane, self.rivals[which], 0.62))
        for at, offset, sprite, size in sorted(sprites, key=lambda s: -s[0]):
            n = int(at) - base
            _i, a, b = projected[n]
            u = at - int(at)
            px, py, pw = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u
            w = max(2, round(pw * size))
            h = max(2, round(sprite.height * w / sprite.width))
            if w > 900:
                continue
            scaled = sprite.resize((w, h), Image.LANCZOS)
            img.paste(scaled, (round(px + pw * offset - w / 2), round(py - h)), scaled)
        side = self.steering(f)
        car = self.player if side is None else self.turning if side == "left" else \
            self.turning.transpose(Image.FLIP_LEFT_RIGHT)
        car = S.scaled(car, 236)
        bounce = round(1.5 * math.sin(f * 1.3))
        img.paste(car, (self.W // 2 - car.width // 2, self.H - car.height - 14 + bounce), car)
        self._hud(img, t)
        return img

    def _project(self, x, y, z):
        scale = self.DEPTH / z
        return (self.W / 2 + scale * x * self.W / 2, self.HORIZON + 30 - scale * y * self.H / 2,
                scale * self.ROAD * self.W / 2)

    def _hud(self, img, t):
        d = ImageDraw.Draw(img)
        place = 3 if t < 34 else 2
        for x, y, text, font, anchor in ((18, 14, f"POS {place}/22", self.hud, "la"), (622, 14, "LAP 1/16", self.hud,
                                                                                         "ra")):
            d.text((x + 2, y + 2), text, font=font, fill=BLACK, anchor=anchor)
            d.text((x, y), text, font=font, fill=WHITE, anchor=anchor)
        seconds = 12.3 + t / L.FPS
        lap = f"0'{int(seconds):02d}\"{int(seconds * 100) % 100:02d}"
        d.text((322, 18), lap, font=self.hud_small, fill=BLACK, anchor="ma")
        d.text((320, 16), lap, font=self.hud_small, fill=(255, 214, 64), anchor="ma")
        speed = min(296, 212 + t)
        d.text((624, 444), f"{speed} KM/H", font=self.hud, fill=BLACK, anchor="rb")
        d.text((622, 442), f"{speed} KM/H", font=self.hud, fill=WHITE, anchor="rb")
        d.rectangle([462, 452, 622, 462], outline=WHITE)
        d.rectangle([464, 454, 464 + round(156 * speed / 320), 460], fill=(232, 32, 42))


class Screens:
    """The glass at each frame of the clip."""

    def __init__(self, made_up):
        self.race = Race(made_up)
        art = Image.open(os.path.join(made_up, "paintings", "apex-circuit", "keyart.png")).convert("RGB")
        self.logo = Image.open(os.path.join(made_up, "library", "media", L.CD_LABEL["system"], "logos",
                                            L.CD_LABEL["stem"] + ".png")).convert("RGBA")
        self.art = art
        self.desktop = self._desktop()
        self.glass = S.Glass()

    def frame(self, f):
        return self.glass(self.raster(f))

    def _desktop(self):
        img = Image.new("RGB", K.RASTER_PX, TEAL)
        font = R.sans(13)
        for name, kind, (x, y) in L.ICONS:
            icon(img, kind, x - 16, y)
            w = font.width(name)
            font.draw(img, x - w // 2, y + 36, name, WHITE)
        return img

    def taskbar(self, img, window):
        d = ImageDraw.Draw(img)
        top = L.TASKBAR
        d.rectangle([0, top, 639, 479], fill=FACE)
        d.line([(0, top), (639, top)], fill=LIGHT)
        d.line([(0, top + 1), (639, top + 1)], fill=WHITE)
        raised(d, 2, top + 4, 56, top + 25)
        flag(img, 7, top + 9)
        R.sans(13).draw(img, 24, top + 8, "Start", BLACK, bold=True)
        if window:
            raised(d, 60, top + 4, 210, top + 25, pressed=True)
            d.rectangle([62, top + 6, 208, top + 23], fill=(222, 222, 222))
            R.sans(13).draw(img, 70, top + 8, "Apex Circuit", BLACK, bold=True)
        sunken(d, 566, top + 4, 637, top + 25)
        icon(img, "speaker", 572, top + 10)
        R.sans(13).draw(img, 588, top + 8, "3:42 PM", BLACK)

    def launcher(self, img, f):
        client = caption(img, L.LAUNCHER, "Apex Circuit")
        x0, y0, x1, y1 = client
        d = ImageDraw.Draw(img)
        d.rectangle(client, fill=(14, 18, 30))
        art_w = 300
        art = self.art.resize((round(self.art.width * (y1 - y0) / self.art.height), y1 - y0), Image.LANCZOS)
        art = art.crop(((art.width - art_w) // 2, 0, (art.width - art_w) // 2 + art_w, y1 - y0))
        img.paste(art, (x0, y0))
        logo = S.scaled(self.logo, art_w - 30)
        img.paste(logo, (x0 + 15, y0 + 10), logo)
        bw, bh = L.BUTTON_SIZE
        px, py = L.POINTER.at(f)
        for name, (cx, cy) in L.BUTTONS:
            down = (name == "Play" and L.CLICK_PLAY <= f < L.CLICK_PLAY + L.CLICK
                    or name == "Exit" and L.CLICK_EXIT <= f < L.CLICK_EXIT + L.CLICK)
            raised(d, cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2, pressed=down)
            over = cx - bw // 2 <= px <= cx + bw // 2 and cy - bh // 2 <= py <= cy + bh // 2
            font = R.sans(13)
            w = font.width(name)
            font.draw(img, cx - w // 2 + (1 if down else 0), cy - 6 + (1 if down else 0), name,
                      (0, 0, 160) if over else BLACK, bold=True)
        R.sans(13).draw(img, x0 + art_w + 14, y1 - 22, "© 1998 Arcwave", (200, 200, 210))

    def raster(self, f):
        if L.LOADING[0] <= f < L.QUIT + 4:
            return self.game(f)
        img = self.desktop.copy()
        window = L.READ[1] <= f < L.LOADING[0] or L.QUIT + 4 <= f < L.CLICK_EXIT + L.CLICK
        if window:
            self.launcher(img, f)
        self.taskbar(img, window)
        x, y = (round(v) for v in L.POINTER.at(f))
        bitmap(img, ARROW, x, y)
        if L.READ[0] <= f < L.READ[1]:
            bitmap(img, SMALL_HOURGLASS, x + 12, y + 12)
        return img

    def game(self, f):
        if f < L.LOADING[0] + 4:
            return Image.new("RGB", K.RASTER_PX)
        if f < L.RACE[0]:
            img = Image.new("RGB", K.RASTER_PX, (8, 10, 18))
            logo = S.scaled(self.logo, 420)
            img.paste(logo, (320 - logo.width // 2, 150 - logo.height // 2), logo)
            d = ImageDraw.Draw(img)
            font = ImageFont.truetype(FONTS + "FRAHVIT.TTF", 22)
            d.text((320, 300), "CIRCUIT 1  ·  RIVIERA", font=font, fill=WHITE, anchor="mm")
            done = K.smooth((f - L.LOADING[0] - 4) / (L.RACE[0] - L.LOADING[0] - 8))
            d.rectangle([180, 340, 460, 352], outline=(160, 160, 170))
            d.rectangle([182, 342, 182 + round(276 * done), 350], fill=(232, 32, 42))
            return S.faded(img, K.smooth((f - L.LOADING[0] - 4) / 4))
        fade = min(K.smooth((f - L.RACE[0] + 1) / 4), 1 - K.smooth((f - L.QUIT) / 4))
        return S.faded(self.race.frame(min(f, L.QUIT)), fade)


def still(made_up):
    """The desktop, the pointer at rest: the video's first frame."""
    return Screens(made_up).frame(0)
