"""The N-Gage card's measurements, shared by ngage_print.py (which draws its printing and screens) and ngage.py (which
builds it). Plain Python: Blender's Python imports it too.

Nokia's N-Gage (2003, the first one): 133.7 x 69.7 x 20.2 mm (Nokia's figures), its parts placed from a photograph of
its face square on (0.0855 mm a pixel); its screen 176 x 208, portrait, 4,096 colours. Millimetres in handheld.py's
frame: x from its middle (left to right), z up from its bottom edge's lowest point, y back from its face.

Its outline (OUTLINE, smoothed): a nearly straight top edge, rounded ends, one deep curve along the bottom. Its face: the
charcoal frame; the silver panel round the screen, printed with its dimples; the black bezel (BEZEL, a U), NOKIA above
the screen and N-GAGE below it; on the left the D-pad's disc in its shield-shaped recess (DPAD), the call key, the music,
radio and menu keys, C and the left soft key; on the right the end key, the keypad's twelve keys fanning round the
screen, 5 and 7 ringed in bronze, the right soft key and the edit key (KEYS); the power key on the top edge's right end.

Two textures: the print (ATLAS square, REGIONS: `face` from the front, `back` from behind, and swatches) and the screens
(MEDIA_REGIONS: NOKIA's start-up, the N-Gage's games menu, a made-up game's title and two moments of it, in 4,096
colours). A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 133.7, 69.7, 20.2
HALF = WIDTH / 2
# The outline's points (x, z), anticlockwise from the bottom's lowest point; smoothed through.
OUTLINE = [(0.0, 0.0), (17.0, 1.0), (34.0, 4.0), (50.0, 11.0), (60.0, 16.5), (65.4, 22.0), (66.9, 30.0), (66.9, 52.0),
           (66.0, 61.0), (61.5, 67.0), (52.0, 68.9), (30.0, 69.5), (0.0, 69.7), (-30.0, 69.5), (-52.0, 68.9),
           (-61.5, 67.0), (-66.0, 61.0), (-66.9, 52.0), (-66.9, 30.0), (-65.4, 22.0), (-60.0, 16.5), (-50.0, 11.0),
           (-34.0, 4.0), (-17.0, 1.0)]
SPAN = (-HALF, HALF, 0.0, HEIGHT)
PANEL = [(-40.0, 69.0), (-40.0, 30.0), (-36.0, 16.0), (-24.0, 8.0), (0.0, 6.0), (24.0, 8.0), (36.0, 16.0), (40.0, 30.0),
         (40.0, 69.0)]
BEZEL = dict(rect=(-24.0, 24.0, 15.5, 69.4), top=3.0, bottom=15.0)
SCREEN = dict(size=(34.0, 41.0), at=(0.3, 43.8), pixels=(176, 208))
DPAD = dict(at=(-43.8, 49.8), r=9.2, shield=[(-62.0, 63.0), (-31.0, 63.0), (-27.0, 49.0), (-33.0, 37.0), (-62.0, 37.0)])
# The keys: (name, x, z, width, height, turned degrees, kind: key, call, end, game, soft).
KEYS = [("call", -35.2, 63.1, 14.0, 6.0, -14.0, "call"), ("end", 34.9, 63.1, 14.0, 6.0, 14.0, "end"),
        ("music", -55.3, 29.3, 10.0, 7.6, 14.0, "key"), ("radio", -45.5, 31.5, 9.0, 7.6, 10.0, "key"),
        ("menu", -34.8, 33.2, 10.0, 7.0, 8.0, "key"), ("C", -39.9, 16.5, 9.0, 6.0, 26.0, "key"),
        ("soft_left", -32.0, 18.6, 9.0, 6.0, 30.0, "soft"),
        ("1", 34.0, 55.0, 9.4, 7.0, 10.0, "key"), ("2", 43.0, 56.7, 9.4, 7.0, 7.0, "key"),
        ("3", 52.8, 57.6, 9.4, 7.0, 4.0, "key"), ("4", 34.9, 46.4, 9.4, 7.4, 2.0, "key"),
        ("5", 45.1, 46.8, 9.4, 7.4, 0.0, "game"), ("6", 55.0, 46.8, 9.4, 7.4, -2.0, "key"),
        ("7", 35.3, 37.4, 9.4, 7.4, -4.0, "game"), ("8", 45.6, 37.0, 9.4, 7.4, -6.0, "key"),
        ("9", 55.9, 35.9, 9.4, 7.4, -8.0, "key"), ("*", 34.5, 28.0, 9.4, 7.0, -10.0, "key"),
        ("0", 44.3, 27.2, 9.4, 7.0, -12.0, "key"), ("#", 53.2, 25.4, 9.4, 7.0, -14.0, "key"),
        ("soft_right", 32.0, 18.6, 9.0, 6.0, -30.0, "soft"), ("edit", 40.4, 16.5, 9.0, 6.0, -26.0, "key")]
LEGENDS = {"1": "1 oo", "2": "2abc", "3": "3def", "4": "4ghi", "5": "5jkl", "6": "6mno", "7": "7pqrs", "8": "8tuv",
           "9": "9wxyz", "*": "* +", "0": "0 _", "#": "# ⇧", "C": "C", "music": "♫", "radio": "▤", "menu": "§",
           "edit": "✎", "soft_left": "—", "soft_right": "—", "call": "✆", "end": "✆"}
def turned_rect(cx, cz, w, h, degrees, r=1.6, n=4):
    """A rounded rectangle's outline, turned, as (x, z) points."""
    pts = []
    for qx, qz, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oz = qx * (w / 2 - r), qz * (h / 2 - r)
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((ox + r * math.cos(a), oz + r * math.sin(a)))
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(cx + x * c - z * s, cz + x * s + z * c) for x, z in pts]


def bezel_outline():
    """The bezel's U: its top corners a little rounded, its bottom ones much more."""
    x0, x1, z0, z1 = BEZEL["rect"]
    t, u = BEZEL["top"], BEZEL["bottom"]
    pts = []
    for cx, cz, r, a0 in ((x1 - t, z1 - t, t, 0), (x0 + t, z1 - t, t, 90), (x0 + u, z0 + u, u, 180),
                          (x1 - u, z0 + u, u, 270)):
        pts += [(cx + r * math.cos(math.radians(a0 + 90 * k / 6)), cz + r * math.sin(math.radians(a0 + 90 * k / 6)))
                for k in range(7)]
    return pts


POWER = dict(at=(58.0, 10.0), r=2.6)                      # on the top edge: x, y
PLAYED = ("5", "7", "2", "8")

PALETTE_BITS = 4                                           # bits per channel
MADE_UP = ("vermsqdn", "arcade")                           # a made-up vertical shooter, for the portrait screen
GAMES = ["VERMILION SQUADRON", "Tidecaller Saga", "Puck Rush", "Springheel Sam"]

COLOURS = dict(frame="#45474B", panel="#AEB1B6", key="#DCDCD6", ink="#12120F", call="#3D7145", end="#955843",
               bronze="#86633A", bezel="#101012", lcd="#575855", back="#6B6D6C", disc="#D3D3D3", shield="#5D5E63",
               nred="#8C402F")

REGIONS = dict(face=(0, 0, 1003, 523), back=(0, 531, 535, 279))
SWATCHES = {name: (560 + 32 * (k % 13), 560 + 32 * (k // 13)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(boot=(0, 0, 176 * 2, 208 * 2), menu=(360, 0, 352, 416), title=(720, 0, 280, 331),
                     game1=(0, 424, 352, 416), game2=(360, 424, 352, 416))

FPS = 30
LENGTH = 240                 # 8 s
