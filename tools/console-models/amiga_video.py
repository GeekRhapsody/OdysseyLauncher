"""The console theme's Amiga card's video (godot/themes/console/videos/amiga.mp4): the 1084S's glass through the card's
focused clip, which the launcher plays on the model's `video` material, starting it again each time the clip loops (A6
Card videos).

It follows the clip (amiga.py) frame for frame, by the timing in amiga_layout.py: Kickstart 1.3's hand while the floppy
goes in; the screen black while the boot block loads; the loader decrunching the game, the background's colour
flickering in stripes; the title screen fading in (copper bars rolling, the floor running towards the viewer, the ship
bobbing, a glint crossing the title) until SPACE; the game fading in: the ship over the scrolling floor among the
stars, the planet drifting by, climbing and diving as the cursor keys are held, a laser for each press of SPACE, each
meeting an enemy flying in on its wave, which bursts for its points; the game playing on from memory while the floppy is
ejected and taken away; then the reset: black, and the hand again, the first frame, so the loop is seamless.

Each frame is the Amiga's 320 x 256 picture, drawn with amiga_print.py's pieces and set in the glass at VIDEO_PX,
encoded by card_video.py. Run it from the repo root with the system Python (Pillow, numpy; ffmpeg on the PATH):

    python tools/console-models/amiga_video.py godot/themes/console/videos/amiga.mp4
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amiga_layout as L  # noqa: E402
import amiga_print as P  # noqa: E402
from card_video import encode  # noqa: E402
from psp_print import ship  # noqa: E402
from retro_pc_layout import phase  # noqa: E402

# The game, in the Amiga's pixels.
GAME_SKY = [(0, (0, 0, 32)), (0.6, (32, 8, 80)), (1.0, (112, 32, 128))]
HUD, GROUND = 14, 200              # the score's band at the top; the horizon, the floor below it
SHIP = dict(x=64, y=120, speed=3.0)   # where it flies; how far it climbs or dives in a frame, a cursor key held
NOSE = SHIP["x"] + 17              # where a laser leaves the ship
LASER = dict(speed=10, length=10)
FLIGHTS = (10, 10, 11, 12, 12)     # each laser's frames to its enemy (L.FIRE's order): the enemies 40 px apart or more
WAVE = dict(speed=2.0, height=10.0, period=36.0)   # an enemy's flight: to the left, up and down
BURST = 14
WHITE = P.WHITE
SPARKS = [WHITE, (255, 240, 96), (255, 160, 32), (208, 64, 32), (96, 16, 16)]   # their colours as a burst ages
DRONES = ((280, 40), (292, 52), (304, 36))   # a formation crossing high up near the end: when each comes, its height
STARS = ((0.5, 24, (96, 96, 160)), (1.0, 18, (160, 160, 224)), (2.0, 12, WHITE))   # each layer's speed, count, colour


class Game:
    """Odyssey's game through the clip: the ship's height at each frame, each enemy's flight to its laser."""

    def __init__(self):
        self.ship, v, y = [], 0.0, float(SHIP["y"])
        for f in range(L.LENGTH):
            v += (SHIP["speed"] * (L.held(f, L.DOWN) - L.held(f, L.UP)) - v) * 0.5
            y += v
            self.ship.append(y)
        # Each enemy is where its laser's head will be as it's hit: (the frame it's hit, its x and y then).
        self.hits = [(f0 + n, NOSE + LASER["speed"] * n + 6, self.ship[f0]) for f0, n in zip(L.FIRE, FLIGHTS)]

    def frame(self, f):
        """The game's picture at frame f."""
        n = f - L.GAME_IN[0]                           # frames since the game began
        img = Image.new("RGB", (P.W, P.H))
        d = ImageDraw.Draw(img)
        P.copper(d, HUD, GROUND, GAME_SKY)
        for speed, count, colour in STARS:             # the stars' layers, the nearer the faster
            rng = random.Random(count)
            for _ in range(count):
                x, y = (rng.uniform(0, P.W) - speed * n) % P.W, rng.uniform(HUD + 2, GROUND - 4)
                d.line([(round(x), round(y)), (round(x) + (speed > 1), round(y))], fill=colour)
        P.planet(d, round(284 - 0.1 * n), 50, 24)      # far off, high in the corner, out of the fight's way
        img = P.floor(img, GROUND, along=2.0 * n)
        d = ImageDraw.Draw(img)
        d.fontmode = "1"
        d.line([(0, GROUND), (P.W, GROUND)], fill=(255, 208, 128))
        self.foes(d, f)
        ship(d, SHIP["x"], round(self.ship[f]), 1.0, WHITE, (255, 176, 48) if f % 4 < 2 else (255, 96, 32))
        score = 100 * sum(1 for hit, _, _ in self.hits if f >= hit)
        d.rectangle([0, 0, P.W, HUD - 1], fill=(0, 0, 0))
        font = P.pixel_font("arialbd.ttf", 10)
        d.text((6, 7), f"SCORE {score:06d}", font=font, fill=(255, 240, 64), anchor="lm")
        d.text((P.W - 6, 7), "HI 050000", font=font, fill=(160, 208, 255), anchor="rm")
        return img

    def foes(self, d, f):
        """The enemies flying in until their lasers meet them, the lasers, the bursts, and the drones."""
        for (hit, hx, hy), f0 in zip(self.hits, L.FIRE):
            if f < hit:
                x = hx + WAVE["speed"] * (hit - f)
                enemy(d, round(x), round(hy + WAVE["height"] * math.sin(2 * math.pi * (f - hit) / WAVE["period"])), f)
            if f0 <= f < hit:
                head = NOSE + LASER["speed"] * (f - f0 + 1)
                d.line([(head - LASER["length"], round(hy)), (head, round(hy))], fill=(255, 255, 160), width=2)
            if hit <= f < hit + BURST:
                burst(d, hx, hy, f - hit, random.Random(hit))
        for f0, y in DRONES:
            if f >= f0:
                x = round(340 - 3.0 * (f - f0))
                d.ellipse([x - 7, y - 2, x + 7, y + 2], fill=(176, 96, 255))
                d.ellipse([x - 3, y - 5, x + 3, y], fill=(224, 192, 255))


def enemy(d, x, y, f):
    """An enemy, facing left: a teal orb with a highlight and a red eye, its fins flapping."""
    flap = 3 if (f // 4) % 2 else 1
    for side in (-1, 1):
        d.polygon([(x + 2, y + 4 * side), (x + 8, y + (5 + flap) * side), (x + 5, y + 3 * side)], fill=(0, 128, 128))
    d.ellipse([x - 6, y - 5, x + 6, y + 5], fill=(32, 192, 176))
    d.ellipse([x - 3, y - 3, x, y - 1], fill=(208, 255, 240))
    d.rectangle([x - 5, y, x - 3, y + 1], fill=(255, 64, 64))


def burst(d, x, y, age, rng):
    """A burst age frames old: a flash, a ring going out, sparks flying and cooling."""
    if age == 0:
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=WHITE)
    elif age < 5:
        r = 3 + 3 * age
        d.ellipse([x - r, y - r, x + r, y + r], outline=WHITE)
    colour = SPARKS[min(len(SPARKS) - 1, age * len(SPARKS) // BURST)]
    for k in range(12):
        a, speed = 2 * math.pi * k / 12 + rng.uniform(-0.2, 0.2), rng.uniform(1.5, 3.2)
        sx, sy = round(x + speed * age * math.cos(a)), round(y + speed * age * math.sin(a))
        d.rectangle([sx - 1, sy - 1, sx, sy], fill=colour)


def screen(f, game, still, black):
    """The glass at frame f."""
    if f < L.BOOT or f >= L.HAND:
        return still
    if f < L.DECRUNCH[0] or f >= L.BLACK:
        return black
    if f < L.DECRUNCH[1]:
        return P.glass_image(P.decrunch(f))
    if f < L.TITLE_OUT[1]:
        level = phase(f, *L.TITLE_IN) * (1 - phase(f, *L.TITLE_OUT))
        return P.glass_image(P.faded(P.title(f - L.TITLE_IN[0]), level))
    if f < L.GAME_IN[0]:
        return black
    return P.glass_image(P.faded(game.frame(f), phase(f, *L.GAME_IN)))


def frames():
    still, black = P.glass_image(P.kickstart()), P.glass_image(Image.new("RGB", (P.W, P.H)))
    game = Game()
    for f in range(L.LENGTH):
        yield screen(f, game, still, black)


def main():
    encode(sys.argv[1], L.VIDEO_PX, L.FPS, frames(), "Amiga")


if __name__ == "__main__":
    main()
