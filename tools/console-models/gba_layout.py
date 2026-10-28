"""The Game Boy Advance card's measurements, shared by gba_print.py (which draws its printing and its screen),
gba_video.py (which draws the screen through the clip) and gba.py (which builds it). Plain Python: Blender's Python
imports it too.

Nintendo's indigo Game Boy Advance, AGB-001 (2001): 144.5 x 82 x 24.5 mm (Nintendo's figures), its 2.9-inch screen
240 x 160 pixels. The rest is measured from photographs of an indigo one in the BnF's Charles Cros collection on
Wikimedia Commons (straight on from the front at 19.9 px a millimetre, the back, each end, the top and bottom edges),
Evan-Amos's photographs of the purple one and of a cartridge, and the side and top elevations on dimensions.com (the
main body 14.5 mm deep, the back's middle 24.5). Millimetres in handheld.py's frame: x from its middle (left to right),
z up from its bottom edge's lowest point, y back from its face.

The face (outline()) is traced from the front photograph: its top edge flat over the middle, falling to the shoulders;
its ends leaning in a little towards the top, each a rounded nose; its bottom edge bowing down to the middle. The main
body is that outline 14.5 mm deep, its front and back edges rounded. Behind it, the back's middle swells out to 24.5 mm
(bulge()): flat across the battery cover and the cartridge's bay, curving away into the grips. The cartridge slides
down into the bay from the slot along the top of that swell, its label to the back, and sits flush with it.

The lens is the dark plastic over the screen, a cushion shape (LENS: its outline), standing a little off the face; the
screen's 240 x 160 pixels (61.2 x 40.8 mm) sit in its window, GAME BOY ADVANCE is printed under them. The whole lens is
the card's `video` material: each frame of the video (VIDEO_PX, the lens's box at VIDEO_SCALE pixels a screen pixel) is
the lens with its printing and the screen as it is at that moment, so the screen switches on, boots and plays inside
the video. The light grey D-pad, A and B, START and SELECT stand out of the face; the grey caps round the ends carry
the L and R buttons at the top corners; the power switch slides along the bottom edge's left end, the POWER light sits
above the face buttons.

Two textures: the print (ATLAS square, REGIONS: `face` from the front, `back` from behind, the cartridge's `label` side
and `plain` side, the tops of A, B and the D-pad, and swatches) and the video's still (the lens with the screen off).
A region is (x, y, width, height) in pixels, drawn with a margin of its own edge's pixels round it (PAD).
"""

import math

# ---- The body ----------------------------------------------------------------------------------------------------------

WIDTH, HEIGHT, DEPTH = 144.5, 82.7, 24.5
BODY_DEPTH = 14.5                 # the main body; the back's middle swells to DEPTH
FRONT_ROUND, BACK_ROUND = 2.5, 3.0

# The face's outline, right half, from the bottom edge's middle anticlockwise to the top edge's middle (traced from the
# straight front photograph; mirrored for the left).
_RIGHT = [(0.0, 0.0), (12.0, 0.3), (21.0, 1.05), (27.0, 1.7), (33.0, 2.55), (39.0, 4.25), (45.0, 6.6), (51.0, 8.3),
          (57.0, 10.2), (63.0, 12.2), (66.6, 13.4), (69.2, 15.3), (71.3, 19.4), (72.25, 26.5), (72.0, 33.5),
          (70.7, 49.0), (69.4, 63.0), (68.1, 69.4), (65.9, 72.4), (63.0, 73.1), (60.0, 73.55), (57.0, 74.2),
          (54.0, 75.0), (51.0, 76.0), (48.0, 77.2), (45.0, 78.6), (42.0, 80.1), (39.0, 81.5), (36.0, 82.35),
          (33.0, 82.65), (24.0, 82.7), (12.0, 82.7)]


def catmull_rom(points, per, closed=True):
    """A smooth curve through points (a Catmull-Rom spline, per points to each span)."""
    n = len(points)
    out = []
    spans = n if closed else n - 1
    for i in range(spans):
        p = [points[(i + k) % n] if closed else points[max(0, min(n - 1, i + k))] for k in (-1, 0, 1, 2)]
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * (2 * p[1][c] + (p[2][c] - p[0][c]) * t
                                    + (2 * p[0][c] - 5 * p[1][c] + 4 * p[2][c] - p[3][c]) * t * t
                                    + (3 * p[1][c] - p[0][c] - 3 * p[2][c] + p[3][c]) * t ** 3) for c in (0, 1)))
    if not closed:
        out.append(tuple(points[-1]))
    return out


def outline(per=3):
    """The face's outline (x, z), anticlockwise from the bottom edge's middle."""
    left = [(-x, z) for x, z in reversed(_RIGHT[1:])]
    return catmull_rom(_RIGHT + [(0.0, 82.7)] + left, per)


def bottom_z(x):
    """The bottom edge's height at x (the face's outline, below its nose)."""
    ax = min(abs(x), _RIGHT[12][0])
    for (x0, z0), (x1, z1) in zip(_RIGHT, _RIGHT[1:13]):
        if x0 <= ax <= x1:
            return z0 + (z1 - z0) * (ax - x0) / (x1 - x0)
    return _RIGHT[12][1]


def top_z(x):
    """The top edge's height at x (|x| up to 63)."""
    ax = abs(x)
    top = list(reversed(_RIGHT[19:])) + [(0.0, 82.7)]
    top = sorted(top)
    for (x0, z0), (x1, z1) in zip(top, top[1:]):
        if x0 <= ax <= x1:
            return z0 + (z1 - z0) * (ax - x0) / (x1 - x0)
    return top[-1][1]


# ---- The back's swell --------------------------------------------------------------------------------------------------

SWELL = dict(flat=33.0, end=64.0, top=74.6, top_flat=31.0, top_end=60.0, bottom=0.3, back_round=5.0, top_round=2.5)


def swell_depth(x):
    """How far back the swell reaches at x: DEPTH across the middle, curving into the body by the grips."""
    ax = abs(x)
    if ax <= SWELL["flat"]:
        return DEPTH
    t = min(1.0, (ax - SWELL["flat"]) / (SWELL["end"] - SWELL["flat"]))
    return BODY_DEPTH - 1.0 + (DEPTH - BODY_DEPTH + 1.0) * 0.5 * (1 + math.cos(math.pi * t))


def swell_top(x):
    """The swell's top at x: level with the slot over the middle, falling under the shoulder buttons."""
    ax = abs(x)
    if ax <= SWELL["top_flat"]:
        return SWELL["top"]
    t = min(1.0, (ax - SWELL["top_flat"]) / (SWELL["end"] - SWELL["top_flat"]))
    return SWELL["top"] - (SWELL["top"] - SWELL["top_end"]) * (0.5 - 0.5 * math.cos(math.pi * t))


SLOT = dict(x=28.8, y=(15.0, 23.0), z=39.0)      # the cartridge's bay, cut down from the swell's top

# ---- The cartridge ------------------------------------------------------------------------------------------------------

CART = dict(width=57.0, height=35.0, thickness=7.6, step=(1.6, 4.0))   # the grip end narrower by step (in, down)
SEAT = (0.0, (SLOT["y"][0] + SLOT["y"][1]) / 2, SWELL["top"] - CART["height"])   # its bottom's middle, seated
HOVER = HEIGHT + 4.0 - SEAT[2]    # how far above its seat it waits: its bottom 4 mm over the top edge
LABEL = dict(rect=(-23.0, 23.0, 3.0, 26.5), r=2.0)    # the label on its back, x and z from its bottom's middle

# ---- The lens and the screen ----------------------------------------------------------------------------------------------

SCREEN_PX = (240, 160)
PITCH = 0.255                     # a screen pixel, mm: 61.2 x 40.8 mm
VIDEO_SCALE = 2                   # video pixels a screen pixel
PX_MM = VIDEO_SCALE / PITCH       # video pixels a millimetre
VIDEO_PX = (616, 520)             # the lens's box, even sides for H.264's 4:2:0
LENS_BOX = (-VIDEO_PX[0] / PX_MM / 2, VIDEO_PX[0] / PX_MM / 2, 7.8, 7.8 + VIDEO_PX[1] / PX_MM)   # x0, x1, z0, z1
SCREEN_CENTRE = (0.0, 45.4)       # the pixels' middle
# The screen's top-left pixel in the video frame, whole pixels.
SCREEN_AT = (round((SCREEN_CENTRE[0] - LENS_BOX[0]) * PX_MM - SCREEN_PX[0] * VIDEO_SCALE / 2),
             round((LENS_BOX[3] - SCREEN_CENTRE[1]) * PX_MM - SCREEN_PX[1] * VIDEO_SCALE / 2))
WINDOW = (65.6, 43.6, 1.6)        # the clear window round the pixels (its LCD's dark border): width, height, corners
LENS_OUT = 0.45                   # how far the lens stands off the face

# The lens's outline, right half, from the bottom's middle anticlockwise to the top's middle (mirrored for the left).
_LENS_RIGHT = [(0.0, 7.9), (12.0, 8.7), (18.0, 9.3), (22.0, 9.9), (26.0, 10.8), (31.0, 11.8), (34.0, 12.6),
               (36.6, 14.4), (38.5, 17.3), (39.1, 20.5), (38.8, 40.0), (38.3, 50.0), (37.55, 60.0), (37.0, 66.0),
               (36.2, 69.3), (34.6, 71.4), (32.0, 72.5), (23.0, 73.3), (12.0, 73.8)]


def lens_outline(per=3):
    """The lens's outline (x, z), anticlockwise from its bottom's middle."""
    right = _LENS_RIGHT
    left = [(-x, z) for x, z in reversed(_LENS_RIGHT[1:])]
    return catmull_rom(right + [(0.0, 73.9)] + left, per)


def lens_px(x, z):
    """A point on the face (mm) to the video frame's pixels (from its top left)."""
    return (x - LENS_BOX[0]) * PX_MM, (LENS_BOX[3] - z) * PX_MM


# ---- The controls --------------------------------------------------------------------------------------------------

DPAD = dict(at=(-54.6, 48.3), arm=8.8, half=3.15, height=2.4)
BUTTONS = dict(b=(47.7, 45.5), a=(61.2, 50.2), r=4.7, height=2.6)
SMALL = dict(start=(-44.6, 27.8), select=(-44.5, 19.6), r=2.05, height=1.6)
LED = dict(at=(47.3, 67.7), r=0.95)
SPEAKER = dict(at=[(51.0, 21.0 + 2.9 * k) for k in range(6)], size=(14.6, 1.35), slant=13.0)
PLATES = dict(start=(-54.5, 28.6), select=(-54.5, 20.4), size=(15.0, 4.6), slant=-8.0)   # their embossed name plates
NINTENDO = dict(at=(0.0, 77.4), size=(19.4, 4.4))
POWER_SWITCH = dict(x=(-49.0, -45.0), y=(5.8, 9.4), travel=3.4)       # the slider at OFF, how far it goes to ON
EXT = dict(x=4.6, y=(4.0, 9.0))                                       # the link port in the top edge

# The grey caps round the ends: a band along the outline from the bottom edge (x = CAP_FROM) up the end and over the
# top corner to x = CAP_TO, out of the outline by CAP_OUT; the L and R buttons are its part above SHOULDER_FROM (z on
# the end), reaching back over the body's back edge.
CAP = dict(start=58.0, end=40.0, out=1.4, inside=4.0, y=(3.3, 11.4), shoulder_z=65.5, shoulder_y=(3.3, 16.0),
           gap=0.6, round=1.0)

# ---- Colours ---------------------------------------------------------------------------------------------------------

COLOURS = dict(case="#5B56A4", case_dark="#48438A", grey="#C9CACF", grey_dark="#9C9DA6", dark="#1C1C22",
               lens="#2C2D31", window="#18191B", lcd_off="#3B3E3A", lit="#52FF6A", led_off="#2A2338",
               cart="#6E7074", slot="#0E0E12", label_paper="#F3F1EA", sticker="#4A4C52")

# ---- The atlas -----------------------------------------------------------------------------------------------------

ATLAS = 1024
PAD = 4
FACE_BOX = (-73.5, 73.5, -1.0, 84.56)         # x0, x1, z0, z1 of the face and back regions
REGIONS = dict(face=(0, 0, 1024, 596), back=(0, 606, 512, 298), label=(522, 606, 456, 280),
               plain=(522, 896, 208, 128), btn_a=(740, 896, 64, 64), btn_b=(814, 896, 64, 64),
               dpad=(888, 896, 128, 128))
SWATCH_NAMES = ("case", "case_dark", "grey", "grey_dark", "dark", "lens", "lit", "led_off", "cart", "slot", "black")
SWATCHES = {name: (16 + 32 * k, 928) for k, name in enumerate(SWATCH_NAMES)}

# ---- The made-up game --------------------------------------------------------------------------------------------------

MADE_UP = ("Kaleidrop (Europe)", "snes")

# ---- The focused clip's timing (frames at FPS), which the video follows frame for frame ---------------------------------

FPS = 30
LENGTH = 300                       # 10 s
CART_IN = (8, 16, 36, 48)          # it grows above the slot, turns round, drops, is seated
POWER_ON = (60, 64)                # the switch slides to ON; the light comes on at its end
BOOT = 66                          # the screen lights: the start-up
TITLE = 132                        # the game's title screen
START = 158                        # START pressed
GAME = 166                         # play
POWER_OFF = (262, 266)             # the switch slides to OFF; the light and the screen go
CART_OUT = (276, 290, 298)         # it rises out, waits, shrinks away

# The game's inputs, in step with the screen: (frame, button, frames held).
INPUTS = [(176, "left", 3), (182, "left", 3), (188, "a", 3), (196, "down", 9), (230, "b", 3), (236, "r", 4)]
