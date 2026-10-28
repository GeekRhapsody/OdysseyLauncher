"""The Sega Game Gear card's measurements, shared by game_gear_print.py (which draws its printing, its lens and its
screens), game_gear.py (which builds it) and game_gear_video.py (which draws its video). Plain Python: Blender's Python
imports it too.

The black Game Gear (1990): 210 x 113 x 38 mm (Wikipedia), its cartridge 68 x 66 x 10 mm at its thickest (a
collector's measurements); the rest measured on Evan-Amos's photographs on Wikimedia Commons (the front, turned square
on and scaled to the width: 7.37 pixels a millimetre at 1600 px; the back, the top edge and a cartridge). Millimetres in
handheld.py's frame: x from its middle (left to right), z up from its bottom edge, y back from its face.

Its face (OUTLINE: the bottom corners rounded far more than the top ones): two matt grips, and between them the island
(ISLAND), sunk a little into the face and reaching up over the top edge, glossy, round the lens (PANEL): one sheet of
black acrylic printed with the three coloured ovals, GAME GEAR, the power light and POWER on its left, SEGA and PORTABLE
VIDEO GAME SYSTEM on its right, and the LCD's grey frame (FRAME) round its window. The lens is the card's `video`
material: its video (LENS_PX, the LCD's 160 x 144 at twice their size in LCD_PX) is the whole lens, so the power light
lights inside it. The left grip: the D-pad (a disc, its cross cut by an X) in its well, the speaker's 36 holes below it;
the right grip: START (a blue drop on the island's edge) and the 1 and 2 buttons in their wells, the bracket between
them. On the top edge, left to right: VOLUME, PHONE and EXT, the cartridge's notch at the back (the cartridge slides
down into it label to the back, its top flush with the top edge), DC 9V and the POWER switch. On the back: the two
battery covers, the stickers, the screws. A seam runs round its sides where the two halves meet.

One print texture (ATLAS square, REGIONS: `face` from the front, `back` from behind, `top` from above (its back edge at
the region's top), `cart` the cartridge's label side, and swatches); the lens's video (the still is its first frame). A
region is (x, y, width, height) in pixels.
"""

import math

WIDTH, HEIGHT, DEPTH = 210.0, 113.0, 38.0

# The face's outline: corners anticlockwise from the bottom right, and their radii (game_gear.rounded_polygon).
OUTLINE = ([(105.0, 0.0), (105.0, 113.0), (-105.0, 113.0), (-105.0, 0.0)], [26.0, 12.0, 12.0, 26.0])
FRONT_ROUND, BACK_ROUND = 6.0, 5.0             # the radii of the face's and the back's rounded edges
SEAM = (21.0, 0.6, 0.45)                       # where the halves meet: y, its width, its depth

ISLAND = ([(46.4, 30.4), (80.0, 120.0), (-80.0, 120.0), (-46.4, 30.4)], [19.0, 0.5, 0.5, 19.0])
ISLAND_DEPTH = 1.5                             # how far the island is sunk into the face
PANEL = ([(45.6, 33.76), (69.7, 105.6), (-69.7, 105.6), (-45.6, 33.76)], [16.0, 7.0, 7.0, 16.0])
PANEL_FACE = 1.3                               # the lens's face, a little proud of the island's floor

# The lens's video: its frame spans LENS (x0, x1, z0, z1), LENS_PX pixels; the LCD's 160 x 144 pixels, each 2 x 2,
# fill LCD_PX (x, y, width, height) of it. The Game Gear's pixels are a fifth wider than they're tall: 65.0 x 48.8 mm.
LENS = (-69.875, 69.875, 33.76, 105.6)
LENS_PX = (688, 424)
LCD = (160, 144)
LCD_PX = (184, 59, 320, 288)
FRAME = dict(outer=(-41.0, 41.0, 40.4, 102.1), window=(-34.7, 34.7, 45.2, 97.2), bevel=2.2)
LED = (-50.6, 79.1, 1.25)                      # the power light: x, z, radius

DPAD = dict(at=(-84.3, 68.0), r=12.3, arm=11.4, half=4.4, well=14.2)
START = dict(at=(69.0, 88.8), along=6.0, across=7.0)  # the drop: its straight side's middle, on the island's edge
BUTTONS = dict(one=(71.6, 59.9), two=(88.6, 72.6), r=6.5, well=7.7)
BRACKET = [(68.7, 68.3), (68.7, 71.6), (82.9, 83.9), (86.3, 84.1), (87.3, 83.0)]
LEGENDS = dict(one=(69.4, 66.6), two=(88.9, 81.6), start=(80.6, 89.6))
# The grips' creases, where their raised plates fall away to the face's lower bulge, each from the island's edge out.
CREASES = [[(-50.0, 33.5), (-58.0, 37.0), (-66.0, 39.5), (-74.0, 41.5), (-84.0, 46.0), (-93.0, 50.5), (-99.0, 52.5)],
           [(56.5, 52.0), (62.0, 46.0), (70.0, 41.5), (78.0, 38.0), (86.0, 36.5), (95.0, 37.5), (101.0, 40.0)]]
SPEAKER = dict(x=-73.8, rows=[(32.3, 6), (28.9, 8), (25.5, 8), (22.0, 8), (18.5, 6)], pitch=3.5, r=0.85)

# The top edge (z = HEIGHT): x along it, y back from the face.
POWER = dict(recess=(80.8, 93.2, 8.6, 14.0), knob=(4.2, 3.6, 2.4), off=83.6, travel=5.6)
JACKS = dict(dc=(66.0, 31.0, 2.2), phone=(-73.0, 31.0, 1.8), ext=(-50.0, 30.5, 12.0, 3.2))
VOLUME = dict(x=-93.5, y=(19.0, 25.0), r=6.0, out=2.2)
NOTCH = dict(x=34.5, y=27.5, z=98.0)           # the cartridge's notch at the back: half its width, its front, its floor
FEET = dict(x=60.0, size=(8.0, 6.0, 3.5))      # the two slots in the bottom edge: x either way; width, y, depth

COVERS = dict(x=70.0, z=58.0, size=(50.0, 52.0), r=3.0, out=0.4)  # the battery covers, either side of the back

# The cartridge, its bottom's middle (and its body's middle, through its thickness) at its origin, its label side +y:
# the body THICK deep, the grip's U standing RIB proud of the label side round the top of the label.
CART = dict(width=68.0, height=66.0, thick=7.5, rib=2.5, seat=(0.0, 31.75, 47.0),
            label=(-27.7, 27.7, 15.6, 54.4), label_r=(6.0, 2.0), grip=(-31.6, 31.6, 54.9, 60.3), leg=4.4,
            legs_to=40.5, sega=(0.0, 8.1, 26.5, 7.0))

ATLAS = 1024
REGIONS = dict(face=(0, 0, 882, 475), back=(0, 483, 630, 339), top=(0, 830, 630, 114), cart=(640, 483, 354, 343))
SWATCHES = {name: (906 + 32 * (k % 4), 16 + 32 * (k // 4)) for k, name in
            enumerate(("shell", "band", "black", "blue", "red", "dark", "cart", "wheel", "gold", "lit"))}

COLOURS = dict(shell="#232427", band="#2A2B2F", black="#0B0B0D", blue="#2F5CCF", red="#E43A28", dark="#060607",
               cart="#1C1C1F", wheel="#2A2B2E", gold="#B89A52", lit="#FF3A26", legend="#D0D0CC", teal="#2BB08A",
               frame="#6F7175", lcd_off="#3A3D3C")

MADE_UP = ("Crimson Kunai (Europe)", "megadrive")  # tools/made-up-games's ninja game: its label, its title, its play

# The focused clip's timing, in frames at FPS, which the video (game_gear_video.py) follows frame for frame.
FPS = 30
LENGTH = 285                  # 9.5 s
CART_IN = (6, 15, 34, 46)     # the cartridge grows in over the notch, turns round, drops in and is seated
ON, OFF = 58, 246             # the POWER switch slides on, and off (4 frames each)
LIT = ON + 4                  # the light comes on, the backlight warms up
SPLASH = (76, 112)            # the made-up publisher's splash
TITLE = (112, 156)            # the title, PRESS START BUTTON blinking
START_PRESS = 144             # START goes down
PLAY = (164, 247)             # the game, faded in from black
RUN = 170                     # the D-pad goes right: the ninja runs
JUMPS = (192, 232)            # 1: the ninja leaps
THROWS = (182, 222, 240)      # 2: a knife
DARK = OFF + 3                # the light goes out, the picture fades and the backlight goes off
CART_OUT = (258, 272, 280)    # the cartridge rises out of the notch, and goes


def rounded(corners, radii, inset=0.0, segments=8):
    """A convex outline (corners anticlockwise as seen from the front, (x, z) in millimetres) with each corner rounded
    by its radius, moved in by inset (the radii shrink with it): the same count of points for every inset, so outlines
    can be joined into rings. game_gear.rounded_polygon's way, for Blender's Python and the system's alike."""
    n = len(corners)
    lines = []
    for i in range(n):
        (ax, az), (bx, bz) = corners[i], corners[(i + 1) % n]
        dx, dz = bx - ax, bz - az
        length = math.hypot(dx, dz)
        lines.append(((ax - dz / length * inset, az + dx / length * inset), (dx / length, dz / length)))

    def meet(l1, l2):
        (p, d), (q, e) = l1, l2
        det = d[0] * -e[1] - d[1] * -e[0]
        t = ((q[0] - p[0]) * -e[1] - (q[1] - p[1]) * -e[0]) / det
        return p[0] + d[0] * t, p[1] + d[1] * t

    moved = [meet(lines[i - 1], lines[i]) for i in range(n)]
    points = []
    for i in range(n):
        cx, cz = moved[i]
        ux, uz = moved[i - 1][0] - cx, moved[i - 1][1] - cz
        wx, wz = moved[(i + 1) % n][0] - cx, moved[(i + 1) % n][1] - cz
        lu, lw = math.hypot(ux, uz), math.hypot(wx, wz)
        ux, uz, wx, wz = ux / lu, uz / lu, wx / lw, wz / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uz * wz))) / 2
        r = max(radii[i] - inset, 0.05)
        t = r / math.tan(half)
        sx, sz = ux + wx, uz + wz
        ls = math.hypot(sx, sz)
        ox, oz = cx + sx / ls * r / math.sin(half), cz + sz / ls * r / math.sin(half)
        a1 = math.atan2(cz + uz * t - oz, cx + ux * t - ox)
        a2 = math.atan2(cz + wz * t - oz, cx + wx * t - ox)
        while a2 < a1:
            a2 += 2 * math.pi
        for k in range(segments + 1):
            a = a1 + (a2 - a1) * k / segments
            points.append((ox + r * math.cos(a), oz + r * math.sin(a)))
    return points


def drop():
    """START's outline: half an ellipse whose straight side lies along the island's right edge, bulging to the right."""
    cx, cz = START["at"]
    (x0, z0), (x1, z1) = ISLAND[0][0], ISLAND[0][1]
    length = math.hypot(x1 - x0, z1 - z0)
    ux, uz = (x1 - x0) / length, (z1 - z0) / length       # up along the edge
    nx, nz = uz, -ux                                       # across it, to the right
    a, b = START["along"], START["across"]
    pts = [(cx + ux * a * math.cos(math.pi * k / 16) + nx * b * math.sin(math.pi * k / 16),
            cz + uz * a * math.cos(math.pi * k / 16) + nz * b * math.sin(math.pi * k / 16)) for k in range(17)]
    return list(reversed(pts))                             # anticlockwise as seen from the front
