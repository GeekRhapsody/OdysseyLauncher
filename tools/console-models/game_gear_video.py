"""The console theme's Game Gear card's video (godot/themes/console/videos/gamegear.mp4): its lens through the card's
focused clip, which the launcher plays on the model's `video` material, starting it again each time the clip loops
(A6 Card videos).

It follows the clip (game_gear.py) frame for frame, by the timing in game_gear_layout.py: the lens with the Game Gear
switched off while the cartridge goes in; POWER, and the light comes on and the backlight flickers up; the made-up
publisher's splash; the made-up game's title, PRESS START BUTTON blinking, quickly once START has been pressed, then a
fade to black; the game, faded in: the bamboo forest scrolls a whole pixel at a time as the ninja runs (the D-pad held
right), throws knives (2), each striking a grey ninja ahead in a spark for a hundred points, leaps off the cliff onto
the bridge (1), and leaps and throws again; then POWER, the light goes out, the picture fades and the backlight goes
off, as at the start, so the loop is seamless. The Game Gear's LCD was slow: each frame keeps a little of the one
before, so moving things smear as they did.

Each frame is the lens as game_gear_print.py draws it, at LENS_PX, encoded by card_video.py. Run from the repo root
(ffmpeg on the PATH), after the made-up games' library:

    python tools/console-models/game_gear_video.py artifacts/made-up-games godot/themes/console/videos/gamegear.mp4

With a third argument, a folder, it also saves the frames it's given there (`--frames=0,80,130`) as PNGs, to check.
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_gear_layout as L  # noqa: E402
import game_gear_print as P  # noqa: E402
from card_video import encode  # noqa: E402

GRAVITY = 0.42                # the LCD's rows a frame, each frame
LEAP = (4.6, 3.6)             # the jumps' starting speeds, up
KNIFE = 4.5                   # a knife's speed across the screen, pixels a frame
SCROLL = 1.15                 # the forest's speed, pixels a frame
NINJA_X = 36                  # where the ninja runs on the screen
HITS = 100                    # a knife's points
SCORE = 12600                 # the score the made-up game's screenshot shows


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def backlight(f):
    """The backlight: off, flickering up as its tube strikes, on; and off again."""
    if f < L.LIT or f >= L.DARK + 4:
        return 0.0
    if f < L.LIT + 8:
        u = (f - L.LIT) / 8
        return smooth(u) * (0.55 if f in (L.LIT + 1, L.LIT + 3) else 1.0)
    if f >= L.DARK:
        return 1 - smooth((f - L.DARK) / 4)
    return 1.0


def light(f):
    return 1.0 if L.LIT <= f < L.DARK else 0.0


def fade(img, level):
    """A fade through the palette, in the Game Gear's 16 steps."""
    level = round(max(0.0, min(1.0, level)) * 15) / 15
    return img.point(lambda v: round(v * level / 17) * 17)


class Play:
    """The game played through the clip, worked out once: the scroll, the ninja's place and pose, the knives, the hits
    and the score, frame by frame."""

    def __init__(self, screens):
        self.s = screens
        self.ground_rows = lambda world: (screens.ground(world) - screens.VIEW[0]) * screens.scale
        self.states = {}
        scroll, speed, y, vy, air = 0.0, 0.0, None, 0.0, None
        knives, sparks, score = [], [], SCORE
        enemies = [(470.0, 560.0), (650.0, 740.0)]        # the grey ninjas, along the painting
        per_pixel = P.ASPECT / screens.scale               # painting pixels a screen pixel, across
        for f in range(L.PLAY[0], L.PLAY[1]):
            if f >= L.RUN:
                speed = SCROLL * smooth((f - L.RUN) / 6)
            scroll = min(scroll + speed, screens.strip.width - P.W)
            world = (scroll + NINJA_X) * per_pixel
            ground = self.ground_rows(world)
            if y is None:
                y = ground
            if f - 2 in L.JUMPS:
                vy, air = -LEAP[L.JUMPS.index(f - 2)], f
            if air is not None:
                y += vy
                vy += GRAVITY
                if vy > 0 and y >= ground:
                    y, vy, air = ground, 0.0, None
            else:
                y = ground
            if any(0 <= f - (t + 2) < 5 for t in L.THROWS):
                pose, phase = "throw", 0.0
            elif air is not None:
                pose, phase = "jump", (f - air) / 22
            elif f >= L.RUN:
                pose, phase = "run", ((f - L.RUN) / 11) % 1.0
            else:
                pose, phase = "stand", 0.0
            sprite, hand = screens.ninja(pose, phase)
            left, top = NINJA_X - sprite.width // 2, round(y) - sprite.height
            if f - 2 in L.THROWS:
                knives.append([left + hand[0], top + hand[1] - 1])
            for knife in list(knives):
                knife[0] += KNIFE
                for x0, x1 in enemies:
                    sx = x0 / per_pixel - scroll
                    rows = ((245 - screens.VIEW[0]) * screens.scale, (370 - screens.VIEW[0]) * screens.scale)
                    if sx + 6 <= knife[0] <= x1 / per_pixel - scroll and rows[0] <= knife[1] <= rows[1]:
                        knives.remove(knife)
                        sparks.append([knife[0] + scroll, knife[1], f])
                        score += HITS
                        break
                else:
                    if knife[0] > P.W + 10:
                        knives.remove(knife)
            self.states[f] = dict(scroll=int(scroll), sprite=sprite, at=(left, top), score=score,
                                  knives=[tuple(k) for k in knives],
                                  sparks=[(x - int(scroll), y_, f - f0) for x, y_, f0 in sparks if f - f0 < 6])

    def frame(self, f):
        st = self.states[f]
        img = self.s.strip.crop((st["scroll"], 0, st["scroll"] + P.W, P.H)).convert("RGBA")
        knife = P.kunai()
        for x, y in st["knives"]:
            img.alpha_composite(knife, (round(x) - knife.width, round(y) - 1))
        img.alpha_composite(st["sprite"], st["at"])
        for x, y, t in st["sparks"]:
            spark = P.spark(t)
            img.alpha_composite(spark, (round(x) - 6, round(y) - 5))
        img = img.convert("RGB")
        img = self.s.text(img, 2, 2, f"SCORE {st['score']:06d}", "#FFFFFF")
        return self.s.text(img, P.W - 3 * 7 - 2, 2, "X04", "#FFFFFF")


class Video:
    """The lens frame by frame."""

    def __init__(self, made_up):
        self.lens = P.Lens()
        self.screens = P.Screens(made_up)
        self.play = Play(self.screens)
        self.black = Image.new("RGB", (P.W, P.H), (0, 0, 0))

    def screen(self, f):
        """What the Game Gear puts out at frame f, or None before it's on."""
        s = self.screens
        if f < L.LIT or f >= L.DARK + 4:
            return None
        if f < L.SPLASH[0]:
            return self.black
        if f < L.SPLASH[1]:
            t = f - L.SPLASH[0]
            return fade(s.splash(t), 1 - (t - 30) / 6 if t >= 30 else 1.0)
        if f < L.TITLE[1] + 8:
            t = f - L.TITLE[0]
            pressed = f - (L.START_PRESS + 3) if f >= L.START_PRESS + 3 else None
            level = min(t / 6, 1.0) if t < 6 else 1 - (f - L.TITLE[1]) / 6 if f >= L.TITLE[1] else 1.0
            return fade(s.title(t, pressed), level) if level > 0 else self.black
        if f < L.PLAY[0]:
            return self.black
        if f < L.PLAY[1]:
            return fade(self.play.frame(f), (f - L.PLAY[0]) / 6)
        return self.play.frame(L.PLAY[1] - 1)

    def frames(self):
        shown = None
        for f in range(L.LENGTH):
            out = self.screen(f)
            if out is not None:
                out = out.point(lambda v: round(10 + v * 0.93))          # the LCD's grey blacks
                shown = out if shown is None else Image.blend(shown, out, 0.72)
            else:
                shown = None
            yield f, self.lens.frame(shown, backlight(f), light(f))


def main():
    made_up, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    keep, folder = set(), None
    for arg in sys.argv[3:]:
        if arg.startswith("--frames="):
            keep = {int(v) for v in arg.split("=", 1)[1].split(",")}
        else:
            folder = os.path.abspath(arg)
    video = Video(made_up)

    def frames():
        for f, img in video.frames():
            if folder and f in keep:
                os.makedirs(folder, exist_ok=True)
                img.save(os.path.join(folder, f"f{f:03d}.png"))
            yield img
    encode(out, L.LENS_PX, L.FPS, frames(), "Game Gear")


if __name__ == "__main__":
    main()
