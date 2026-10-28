"""The PlayStation Vita's measurements, shared by psvita_print.py (which draws its printing, its screen's still and the
screens of its video), psvita_video.py (which draws the video) and psvita.py (which builds it). Plain Python: Blender's
Python imports it too.

The first PS Vita, the PCH-1000 series (2011), in black: 182 mm wide, 83.5 mm high and 18.6 mm deep (Sony's figures),
standing up in handheld.py's frame: x from the middle (left to right, as the face is seen), z up from the bottom edge,
y back from the face (0) to the back's flat (DEPTH). The layout is measured from the layout drawing on Wikimedia Commons
(PlayStation Vita Layout.svg: the face, the back, the top and the bottom edge to one scale, read at 15.9 px a
millimetre), and checked against Evan-Amos's four photographs (Commons: PlayStation-Vita-1101-FL, -FR, -BL and -BR) and
a PCH-1004's straight views (Commons: Sony PlayStation Vita PCH-1004 (EUR) - front, rear and top view). Sony's Quick
Start Guide for the PCH-1001 and PCH-1101 gives the screens (the home screen's bubbles, the LiveArea and its gate, the
peel) and what the buttons do: the PS button wakes it and lights blue once, the power button puts it to sleep.

The body's outline (body_outline()): a straight top and bottom, each end half an ellipse (ENDS: its middle 60 mm out
from the middle, 31 mm across and the body's height tall; the drawing's outline is within 0.6 mm of it). Through its
depth: the face's glossy panel, its edge rounded over (FRONT_ROUND); the gunmetal frame round the edge (BAND), carrying
the top edge's controls; then the matte back shell, rounded over broadly (BACK_INSET in, over its depth) to the back's
flat. At the top corners the frame is the chrome shoulder buttons L and R, whose crescents show on the face
(SHOULDER_CURVE: the panel's edge round them); at the bottom corners it's a loop round a hole through the console
(HOLE), the panel's edge running along the hole's top (BOTTOM_NOTCH).

Two textures and the screen's still. `psvita_print.png` (ATLAS square, PRINT_REGIONS): `front` (the face seen square
on), `top` (the top edge seen from above, the face towards the region's bottom), `bottom` (the bottom edge seen from
below, the face towards the region's top), `lit` (the PS button's top lit blue) and the swatches small parts take their
colour from. `psvita_rear.png` (REAR_REGIONS): `rear` (the back seen from behind, its x the face's negated).
`psvita_screen.png`: the screen's still, VIDEO_PX: the glass with the OLED switched off, the first and last frame of
the card's video (psvita_video.py), which the launcher plays on the glass while the card is focused. A region is
(x, y, width, height) in pixels, and the box of millimetres it covers, (x0, x1, z0, z1).

The `focused` clip's timing, in frames at FPS, is here so that the video (psvita_video.py) follows the clip
(psvita.py) frame for frame: the launcher starts the video with the clip, and again each time the clip loops.
"""

import math

# ---- The body --------------------------------------------------------------------------------------------------------
WIDTH, HEIGHT, DEPTH = 182.0, 83.5, 18.6
MID = HEIGHT / 2
ENDS = dict(x=60.0, a=31.0)       # each end half an ellipse: its middle at x = +-60, 31 mm across, HEIGHT tall
FRONT_ROUND = 0.9                 # the radius rounding the face's edge over
PANEL = 1.4                       # the panel's depth: the frame starts behind it
BAND = (1.4, 9.7)                 # the gunmetal frame, front to back
BACK_INSET = 10.0                 # the back's flat is the outline moved in this far, the shell rounding over to it
FRAME_EDGE = 0.6                  # the frame showing round the panel's edge, seen from the front

COLOURS = dict(case="#111114", rear="#1C1C20", frame="#45484E", chrome="#C5C9CF", buttons="#17171B", dark="#08080A",
               lens="#0E1420", lit="#3D9BFF", glass="#0B0C0F")

# ---- The face (x, z) -------------------------------------------------------------------------------------------------
SCREEN = dict(x=0.0, z=45.7, width=110.5, height=62.6)   # the OLED's lit area: 5 inches, 960 x 544
DPAD = dict(x=-73.65, z=55.82, well=12.1)
DPAD_ARM = [(2.63, 0.0), (6.33, -3.7), (9.93, -3.7), (9.93, 3.7), (6.33, 3.7)]   # an arm, from the pad's middle out
DPAD_RADII = [0.6, 0.9, 1.3, 1.3, 0.9]
DPAD_BUTTONS = [("up", 90.0), ("right", 0.0), ("down", 270.0), ("left", 180.0)]
FACE = dict(x=73.3, z=55.6, reach=7.85, radius=3.6)
FACE_BUTTONS = [("triangle", 90.0), ("circle", 0.0), ("cross", 270.0), ("square", 180.0)]
STICKS = dict(left=(-68.6, 33.15), right=(68.6, 33.15))
STICK = dict(well=8.6, bezel=5.7, cap=4.8, neck=2.4, recess=1.1, top=3.6, pivot=4.0, tilt=16.0)
PS = dict(x=-70.8, z=16.65, half=(6.05, 3.1))            # the PS button, an oval
SMALL = dict(SELECT=(65.4, 16.65), START=(75.2, 16.65), half=(3.9, 1.95))
CAMERA = dict(x=63.9, z=67.95, r=1.7)
SPEAKER_X, SPEAKER_Z, SPEAKER_R = (80.6, 83.35, 86.1), (33.25, 30.15), 0.55
SONY = dict(x=-65.8, z=71.94, width=15.1, cap=2.7)
LOGO = dict(x=0.0, z=9.65, width=19.2, cap=3.2)         # PS VITA under the screen

# The panel's edge round the left shoulder's crescent (mirrored for the right), from the outline to the top edge.
SHOULDER_CURVE = [(-78.4, 75.35), (-75.0, 75.75), (-70.0, 76.15), (-66.5, 76.75), (-63.0, 78.55), (-61.0, 80.75),
                  (-60.0, 82.05), (-59.0, 82.95), (-57.6, 83.5)]
SHOULDER_END = (-84.5, 67.3)      # how far the shoulder button runs down the end, on the frame
# The hole through the bottom left corner (mirrored for the right): its top edge, left to right, then its bottom edge
# back; the panel's edge runs FRAME_EDGE above its top, from the outline to the bottom edge.
HOLE_TOP = [(-74.8, 9.78), (-70.4, 9.45), (-66.3, 8.65), (-64.1, 7.75), (-62.2, 6.25), (-60.9, 4.65), (-60.5, 3.55)]
HOLE_BOTTOM = [(-61.4, 2.35), (-64.1, 3.45), (-67.2, 4.55), (-69.9, 5.45), (-72.3, 6.55), (-74.15, 7.85), (-74.8, 8.75)]
BOTTOM_NOTCH = dict(outline=(-80.4, 10.35), bottom=(-57.6, 0.0))

# ---- The edges -------------------------------------------------------------------------------------------------------
# The top edge, x along it and y back from the face: L and R (chrome pills over the corners), POWER, the PS Vita card
# slot's cover, the accessory port's cover, VOL - and +.
TOP = dict(L=(-84.5, -57.6), R=(57.6, 84.5), pill_y=(4.1, 11.1), housing=(-50.5, 27.8), housing_y=(1.6, 9.5),
           card=(-40.7, -7.0), port=(-5.3, 27.0), cover_y=(2.3, 8.8), vol=(28.5, 51.8), minus=34.5, plus=46.8)
POWER = dict(x=-45.5, y=5.3, r=2.9, height=0.6, travel=0.5)
VOLUME = dict(r=2.6, height=0.45)
# The bottom edge: the multi-use connector, the headset jack, two screws.
BOTTOM = dict(connector=(-7.7, 7.7), connector_y=(3.6, 7.2), jack=19.9, jack_r=1.9, screws=(-12.7, 12.2), y=5.4)

# ---- The back (x as the face is seen) --------------------------------------------------------------------------------
TOUCHPAD = dict(x=(-56.0, 56.0), z=(24.05, 71.85), pitch=2.25)
GRIPS = dict(x=66.8, z=42.7, half=(8.9, 20.35))          # the two ovals, at +-x
POD = dict(half_width=6.0, z=(75.25, 81.45), lens=(0.0, 78.35), lens_r=2.1, y=(14.6, 18.9))   # the rear camera
SCREWS = [(81.5, 65.25), (-81.5, 65.25), (80.5, 20.25), (-80.5, 20.25)]
CARD_SLOT = dict(x=(34.2, 49.9), z=(0.6, 6.25))          # the memory card's slot cover, by the bottom edge
MIC = dict(x=12.4, z=4.25)


def region(px, mm):
    return dict(px=px, mm=mm)


ATLAS = 1024
PRINT_REGIONS = dict(
    front=region((0, 0, 1024, 476), (-92.0, 92.0, -1.0, 84.5)),
    top=region((0, 484, 1024, 112), (-92.0, 92.0, -0.5, 19.6)),       # (x0, x1, y0, y1): the face at the bottom
    bottom=region((0, 604, 1024, 112), (-92.0, 92.0, -0.5, 19.6)),    # the face at the top
    lit=region((8, 724, 160, 82), (-7.2, 7.2, -3.7, 3.7)),            # the PS button's top, lit; about its middle
)
SWATCHES = dict(case=(200, 760), frame=(232, 760), chrome=(264, 760), dark=(296, 760), buttons=(328, 760),
                rear=(360, 760), lens=(392, 760), glass=(424, 760))   # 20 x 20 blocks' middles
REAR_REGIONS = dict(rear=region((0, 0, 1024, 476), (-92.0, 92.0, -1.0, 84.5)))
REAR_SWATCHES = dict(rear=(16, 500), pod=(48, 500))

# ---- The screen and its video ----------------------------------------------------------------------------------------
NATIVE = (960, 544)                                    # the OLED's pixels: the screens are laid out in them
LCD_PX = (720, 408)                                    # the video's picture of the OLED: three quarters of its pixels
PITCH = LCD_PX[0] / SCREEN["width"]                    # pixels a millimetre: 6.52
VIDEO_PX = (740, 428)                                  # the glass, the OLED and 10 pixels of black round it
LCD_AT = (10, 10)                                      # the OLED's top left in the video's frame
GLASS = dict(x=(-VIDEO_PX[0] / PITCH / 2, VIDEO_PX[0] / PITCH / 2),
             z=(SCREEN["z"] - VIDEO_PX[1] / PITCH / 2, SCREEN["z"] + VIDEO_PX[1] / PITCH / 2))

MADE_UP = ("voltcrwn", "arcade")   # the game: Voltcrown, from tools/made-up-games (made up: Arcwave's fighting game)

# ---- The focused clip, in frames at FPS --------------------------------------------------------------------------------
FPS = 30
LENGTH = 330                 # 11 s
WAKE = 10                    # the PS button pressed: the Vita wakes from standby to its lock screen ...
LIT = (12, 46)               # ... and the button lights blue for a second
PEEL_LOCK = (24, 44)         # a finger peels the lock screen from its top right corner to the bottom left: the bubbles
TAP_GAME = 64                # the game's bubble tapped ...
OPEN = (68, 82)              # ... its LiveArea opens out of it, the game's gate in its middle
TAP_START = 102              # Start on the gate tapped ...
GATE = (106, 118)            # ... the gate opens over the screen
SPLASH = (118, 134)          # the publisher's name
TITLE = (134, 166)           # the title, PRESS START
START = 154
FIGHT = (166, 262)           # the fight
WALK = (172, 190)            # the left stick pushed forward: Juno walks in
PUNCHES = dict(square=192, triangle=200, circle=210)   # the combo: punch, kick, punch, each landing two frames later
TOUCH_VOLT = 222             # VOLT on the screen touched: the finisher
VOLT = (224, 246)
KO = 238
PS_PAUSE = 264               # the PS button: back to the LiveArea, the game paused
PAUSED = (266, 300)
PEEL_LIVE = (276, 296)       # the LiveArea peeled away: the game closes, back to the bubbles
POWER_OFF = 304              # the power button: standby
SCREEN_OFF = (306, 312)


def stick(f):
    """The left stick's push at frame f, (x, z), each from -1 to 1: forward (right) as Juno walks in, little nudges
    through the combo, back to the middle for the finisher."""
    a, b = WALK
    x = 0.95 * max(0.0, min(1.0, (f - a) / 3.0, (b - f) / 4.0))
    z = 0.0
    for f0, nx, nz in ((196, 0.45, 0.25), (205, -0.3, -0.35), (214, 0.5, 0.1)):    # (frame, x, z)
        w = max(0.0, 1 - abs(f - f0) / 4.0)
        w = w * w * (3 - 2 * w)
        x += nx * w
        z += nz * w
    return x, z


# ---- Outlines ----------------------------------------------------------------------------------------------------------

def line(a, b, steps):
    """a to b, without b."""
    return [(a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps) for k in range(steps)]


def end_point(t, inset=0.0):
    """The right end's half ellipse at angle t (-90 to 90 degrees round from the bottom), moved in by inset along its
    normal."""
    a, b = ENDS["a"], MID
    c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
    nx, nz = b * c, a * s
    n = math.hypot(nx, nz)
    return ENDS["x"] + a * c - inset * nx / n, MID + b * s - inset * nz / n


def body_outline(inset=0.0, end_steps=40, top_steps=24):
    """The body's outline moved in by inset (out, if negative), anticlockwise from the bottom's middle: the same number
    of points at every inset, so outlines can be joined into rings."""
    x0 = ENDS["x"]
    right = [end_point(-90.0 + 180.0 * k / end_steps, inset) for k in range(end_steps + 1)]
    left = [(-x, z) for x, z in reversed(right)]
    half = top_steps // 2
    return (line((0.0, inset), (x0, inset), half) + right[:-1] + line((x0, HEIGHT - inset), (-x0, HEIGHT - inset), top_steps)
            + left[:-1] + line((-x0, inset), (0.0, inset), half))


def smooth_path(points, n=6, closed=False):
    """A Catmull-Rom spline through points, n steps a span."""
    p = list(points)
    if closed:
        p = p[-1:] + p + p[:2]
    else:
        p = p[:1] + p + p[-1:]
    out = []
    for i in range(1, len(p) - 2):
        (ax, az), (bx, bz), (cx, cz), (dx, dz) = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n):
            t = k / n
            out.append((0.5 * (2 * bx + (cx - ax) * t + (2 * ax - 5 * bx + 4 * cx - dx) * t * t + (3 * bx - ax - 3 * cx + dx) * t ** 3),
                        0.5 * (2 * bz + (cz - az) * t + (2 * az - 5 * bz + 4 * cz - dz) * t * t + (3 * bz - az - 3 * cz + dz) * t ** 3)))
    if not closed:
        out.append(p[-2])
    return out


def hole_outline(side=-1):
    """The hole through a bottom corner (side -1 the left, 1 the right), a closed outline."""
    pts = smooth_path(HOLE_TOP + HOLE_BOTTOM, 5, closed=True)
    return pts if side < 0 else [(-x, z) for x, z in pts]


def shoulder_region(side=-1):
    """The shoulder button's corner, as a polygon in (x, z) that runs well outside the body: what lies in it, at any
    depth, is chrome."""
    curve = smooth_path(SHOULDER_CURVE, 6)
    ex, ez = SHOULDER_END
    pts = [(-57.6, HEIGHT + 20.0), (-57.6, HEIGHT + 0.01)] + list(reversed(curve)) + [(ex, ez), (-120.0, ez), (-120.0, HEIGHT + 20.0)]
    return pts if side < 0 else [(-x, z) for x, z in reversed(pts)]


def notch_region(side=-1):
    """The frame's loop round a bottom corner's hole, as a polygon in (x, z) running well outside the body: the panel's
    edge FRAME_EDGE above the hole's top."""
    top = [(x, z + FRAME_EDGE) for x, z in smooth_path(HOLE_TOP, 5)]
    ox, oz = BOTTOM_NOTCH["outline"]
    bx, bz = BOTTOM_NOTCH["bottom"]
    pts = [(-120.0, oz), (ox, oz)] + top + [(bx + 0.5, bz + FRAME_EDGE), (bx + 0.5, -20.0), (-120.0, -20.0)]
    return pts if side < 0 else [(-x, z) for x, z in reversed(pts)]


def rounded_polygon(corners, radii, segments=10):
    """A convex polygon's outline (anticlockwise corners) with each corner rounded by its radius."""
    n = len(corners)
    points = []
    for i in range(n):
        (px, pz), (cx, cz), (nx, nz) = corners[i - 1], corners[i], corners[(i + 1) % n]
        ux, uz = px - cx, pz - cz
        wx, wz = nx - cx, nz - cz
        lu, lw = math.hypot(ux, uz), math.hypot(wx, wz)
        ux, uz, wx, wz = ux / lu, uz / lu, wx / lw, wz / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uz * wz))) / 2
        r = radii[i]
        t = r / math.tan(half)
        bx, bz = ux + wx, uz + wz
        lb = math.hypot(bx, bz)
        ox, oz = cx + bx / lb * r / math.sin(half), cz + bz / lb * r / math.sin(half)
        a1 = math.atan2(cz + uz * t - oz, cx + ux * t - ox)
        a2 = math.atan2(cz + wz * t - oz, cx + wx * t - ox)
        while a2 < a1:
            a2 += 2 * math.pi
        points += [(ox + r * math.cos(a1 + (a2 - a1) * k / segments), oz + r * math.sin(a1 + (a2 - a1) * k / segments))
                   for k in range(segments + 1)]
    return points


def dpad_arm(degrees):
    """A D-pad arm: its corners (anticlockwise) and their radii, pointing out from the pad's middle at degrees."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    x, z = DPAD["x"], DPAD["z"]
    return [(x + u * c - v * s, z + u * s + v * c) for u, v in DPAD_ARM], DPAD_RADII


def face_centres():
    """Each face button: (name, x, z)."""
    return [(n, FACE["x"] + FACE["reach"] * math.cos(math.radians(a)), FACE["z"] + FACE["reach"] * math.sin(math.radians(a)))
            for n, a in FACE_BUTTONS]


def stadium(x0, x1, z0, z1, n=8):
    """A pill lying along x, from x0 to x1 and z0 to z1, anticlockwise."""
    r = (z1 - z0) / 2
    zm = (z0 + z1) / 2
    right = [(x1 - r + r * math.cos(math.radians(-90 + 180 * k / n)), zm + r * math.sin(math.radians(-90 + 180 * k / n)))
             for k in range(n + 1)]
    left = [(x0 + r + r * math.cos(math.radians(90 + 180 * k / n)), zm + r * math.sin(math.radians(90 + 180 * k / n)))
            for k in range(n + 1)]
    return right + left
