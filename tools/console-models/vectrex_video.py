"""The console theme's Vectrex card's video (godot/themes/console/videos/vectrex.mp4): the tube's face through the
card's focused clip, which the launcher plays on the model's `video` material, the glass, starting it again each time
the clip loops (A6 Card videos).

It follows the clip (vectrex.py) frame for frame, by the timing in vectrex_layout.py: the power-on screen while the
cartridge goes in; the game's overlay sliding down into place over it, the screen's lines taking its colours where it
covers them; the tube flickering on behind it and a made-up game, Odyssey, through its colours: the ship under the
rocks, moving and banking as the joystick rocks, a bolt for each press of button 1 flying up to meet a rock, which
bursts for its points, the shield round the ship for each press of button 4; the picture fading out; the overlay
sliding up and out, over the tube switched off; the tube dark while the cartridge comes out; then the tube flickering
on to the power-on screen, its rays rising to the first frame's, so the loop is seamless. Each frame of the game holds
its last moments, fading (SMEAR), so what moves leaves a short afterglow, as the phosphor does, rather than a copy of
itself a frame back.

Each frame is the tube's face as vectrex_print.py draws it, at VIDEO_PX, encoded by card_video.py. Run it from the repo
root with the system Python (Pillow, numpy; ffmpeg on the PATH):

    python tools/console-models/vectrex_video.py godot/themes/console/videos/vectrex.mp4
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vectrex_layout as L  # noqa: E402
import vectrex_print as P  # noqa: E402
from card_video import encode  # noqa: E402
from retro_pc_layout import ease_in, phase, smooth  # noqa: E402

SMEAR = [1.0, 0.6, 0.4, 0.25]   # a frame of the game: its moments a quarter of a frame apart, newest first, and how
                                # bright each is

# The game, in the tube's millimetres (x across from its left, y down from its top).
SHIP = dict(x=42.0, y=136.0, gain=0.35, bank=0.9)   # where it starts; how far it moves in a frame (mm) and how far it
                                                    # banks (degrees) for each degree of the joystick's roll
SHIP_LINES = [(0.0, -10.0), (-7.0, 7.0), (0.0, 3.0), (7.0, 7.0), (0.0, -10.0)]      # from its middle
BOLT = dict(start=12.0, speed=9.0, length=5.0)       # its tip leaves start above the ship's middle; mm a frame
BURST = 12                   # frames a rock's burst lasts
SHIELD = dict(r=14.0, frames=15)
JAG = [1.0, 0.75, 1.05, 0.85, 1.1, 0.7, 0.95, 0.8]   # a rock's outline: its radius at each of its eight corners
# The rocks: one for each of L.SHOTS, put where its bolt meets it (its flight in frames; the rock's offset from the
# bolt's line); then those the bolts miss, where they are as the game starts. Each with its size and points, its drift
# (mm a frame) and its spin (radians a frame).
TARGETS = [dict(flight=6, dx=-2.0, r=9.0, points=100, drift=(0.06, 0.12), spin=0.03),
           dict(flight=4, dx=-1.5, r=7.0, points=150, drift=(0.08, 0.14), spin=0.04),
           dict(flight=7, dx=2.0, r=11.0, points=50, drift=(-0.05, 0.08), spin=-0.02)]
DRIFTERS = [dict(at=(125.0, 44.0), r=8.0, drift=(-0.04, 0.06), spin=0.03),
            dict(at=(126.0, 106.0), r=9.0, drift=(-0.05, 0.07), spin=-0.025)]


class Game:
    """Odyssey through the clip: the ship's place at each frame, the rocks' paths, the stars."""

    def __init__(self):
        self.ship, x = [], SHIP["x"]
        for f in range(L.LENGTH):
            self.ship.append(x)
            x += SHIP["gain"] * L.stick(f)[0]
        self.rocks = []                     # (where it is at frame f0, f0, the frame it's hit or None, the rock)
        for f0, rock in zip(L.SHOTS, TARGETS):
            hit = f0 + rock["flight"]
            tip = SHIP["y"] - BOLT["start"] - BOLT["speed"] * rock["flight"]
            self.rocks.append(((self.ship[f0] + rock["dx"], tip - 0.8 * rock["r"]), hit, hit, rock))
        for rock in DRIFTERS:
            self.rocks.append((rock["at"], L.PLAY[0], None, rock))
        stars = random.Random(7)
        self.stars = [(stars.uniform(6.0, 143.0), stars.uniform(32.0, 150.0)) for _ in range(18)]
        self.twinkles = [(stars.uniform(20.0, 45.0), stars.uniform(0.0, 2 * math.pi)) for _ in self.stars]

    def smeared(self, f):
        """Frame f as beam()'s groups: the game at each of SMEAR's moments, oldest and dimmest first, so that beam()
        draws the newest over them."""
        groups = []
        for k in reversed(range(len(SMEAR))):
            groups += [(lines, brightness * SMEAR[k]) for lines, brightness in self.lines(f - k / len(SMEAR))]
        return groups

    def lines(self, f):
        """The game's lines at moment f (in frames, between them too), as beam()'s groups: the score, the stars
        twinkling, the rocks, the ship."""
        score = sum(rock["points"] for f0, rock in zip(L.SHOTS, TARGETS) if f >= f0 + rock["flight"])
        groups = [(P.letter_strokes(f"{score:04d}", 50.0, 13.0, 7.0), 1.0)]
        for (x, y), (period, offset) in zip(self.stars, self.twinkles):
            groups.append(([[(x, y)]], 0.7 + 0.3 * math.sin(2 * math.pi * f / period + offset)))
        return groups + self.rock_lines(f) + self.ship_lines(f)

    def rock_lines(self, f):
        """The rocks at frame f, drifting and spinning, and the bursts of those just hit."""
        groups = []
        for k, ((x0, y0), f0, hit, rock) in enumerate(self.rocks):
            x, y = x0 + rock["drift"][0] * (f - f0), y0 + rock["drift"][1] * (f - f0)
            turn = k + rock["spin"] * f
            if hit is None or f < hit:
                corners = [(x + rock["r"] * j * math.cos(2 * math.pi * n / 8 + turn),
                            y + rock["r"] * j * math.sin(2 * math.pi * n / 8 + turn)) for n, j in enumerate(JAG)]
                groups.append(([corners + corners[:1]], 1.0))
            elif f < hit + BURST:
                t = (f - hit) / BURST
                rays = [[(x + r * math.cos(2 * math.pi * n / 10 + turn), y + r * math.sin(2 * math.pi * n / 10 + turn))
                         for r in (2.0 + 7.0 * t, 5.0 + 11.0 * t)] for n in range(10)]
                groups.append((rays, 1 - t))
        return groups

    def ship_lines(self, f):
        """The ship at moment f, banking with the joystick; its bolts in flight; its shield."""
        i = int(f)
        x, y = self.ship[i] + (self.ship[i + 1] - self.ship[i]) * (f - i), SHIP["y"]
        a = math.radians(SHIP["bank"] * L.stick(f)[0])
        lines = [[(x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a))
                  for px, py in SHIP_LINES]]
        for f0, rock in zip(L.SHOTS, TARGETS):
            if f0 <= f < f0 + rock["flight"]:
                tip = y - BOLT["start"] - BOLT["speed"] * (f - f0)
                lines.append([(self.ship[f0], tip), (self.ship[f0], tip + BOLT["length"])])
        groups = [(lines, 1.0)]
        for f0 in L.SHIELDS:
            if f0 <= f < f0 + SHIELD["frames"]:
                n = f - f0
                r = SHIELD["r"] * (1 + 0.06 * math.sin(1.3 * n))
                ring = [(x + r * math.cos(math.pi * j / 6), y - 1.0 + r * math.sin(math.pi * j / 6)) for j in range(13)]
                groups.append(([ring], min(1.0, (n + 1) / 2, (SHIELD["frames"] - n) / 5)))
        return groups


def lit(f, on):
    """How lit the tube is at frame f, having come on at frame on: flickering, then steady."""
    return L.FLICKER[f - on] if f - on < len(L.FLICKER) else 1.0


def frames():
    """The face at each frame of the clip."""
    face, game = P.Face(L.VIDEO_PX), Game()
    logo = P.beam([(P.logo(), 1.0)], L.VIDEO_PX)
    still = face.picture(logo)
    for f in range(L.LENGTH):
        if f < L.OVERLAY_IN[0]:
            yield still
        elif f < L.ON:
            yield face.picture(logo, overlay=smooth(phase(f, *L.OVERLAY_IN)))
        elif f < L.OFF[1]:
            level = lit(f, L.ON) * (1 - smooth(phase(f, *L.OFF)))
            yield face.picture(level * P.beam(game.smeared(f), L.VIDEO_PX), overlay=1.0, lit=level)
        elif f < L.LOGO[0]:
            yield face.picture(overlay=1 - ease_in(phase(f, *L.OVERLAY_OUT)), lit=0.0)
        else:
            rise = smooth(phase(f, L.LOGO[0] + len(L.FLICKER), L.LOGO[1]))
            yield face.picture(lit(f, L.LOGO[0]) * P.beam([(P.logo(rise), 1.0)], L.VIDEO_PX))


def main():
    encode(sys.argv[1], L.VIDEO_PX, L.FPS, frames(), "Vectrex")


if __name__ == "__main__":
    main()
