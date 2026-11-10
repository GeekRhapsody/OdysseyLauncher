"""The Nintendo Switch 2's measurements, shared by switch2_print.py (which draws its printing, its screen's still and the
screens of its video), switch2_video.py (which draws the video) and switch2.py (which builds it). Plain Python:
Blender's Python imports it too.

The Nintendo Switch 2 (2025) with its Joy-Con 2 attached: 272 x 116 x 13.9 mm (Nintendo's figures; 30.7 mm from the
sticks' tips to the ZL and ZR buttons), built upright in handheld.py's frame: x from the middle (left to right, as the
face is seen), z up from the bottom edge, y back from the face. Its shape is measured from the renders on Nintendo's
tech specs page (nintendo.com/us/gaming-systems/switch-2/tech-specs), each with a transparent background, so their
silhouettes are exact: the Joy-Con 2 straight on from the front (17.10 px a millimetre), from behind (17.26) and from
their inner sides (17.70), each scale from their 116 mm height; the console's top and bottom edges straight on (17.34
px a millimetre, from its 202.2 mm, which with the two Joy-Con 2's 34.9 mm makes Nintendo's 272; its depth comes out
at 13.84 mm, against Nintendo's 13.9); and a three-quarter render of the console alone, whose screen's corners (the
7.9-inch 16:9 panel, 174.9 x 98.4 mm) map the face affinely (its two upright edges are the same length in pixels), for
the glass and the frame round it. Nintendo's back render (the kickstand open) places the kickstand's hinges; a
Nintendo Today screenshot and its photograph (on Nintendo Life, 2025-05-12) show the HOME Menu with mouse controls, its
black arrow, and a right Joy-Con 2 used as a mouse: on its side, its attachment side down, its face towards the thumb.

The console is a slab (TABLET) with a channel in each end (CHANNEL), coloured inside (blue on the left, red on the
right), that a Joy-Con 2's tongue (TONGUE) fits into; the Joy-Con 2 hold on by magnets. A Joy-Con 2 seen from the front
is JOYCON_OUTLINE (the right one's, u out from its inner edge; the left one is its mirror): a straight inner edge, the
bottom curving up to the outer side over 35 mm, the top over 27 mm, the R or L button the outline's top from 5 mm out
(a millimetre higher than the inner edge's top). ZR or ZL is a hooked trigger behind the top outer corner (the band
outside TRIGGER_INNER seen from behind, TRIGGER_LOBE from the inner side); the release button is on the back by the
inner edge.

Two textures and the screen's still. `switch2_print.png` (ATLAS square, PRINT_REGIONS): `front` (the face seen square
on, with both Joy-Con 2: the frame, the glass round the screen, the Joy-Con 2's faces, the buttons' and the sticks'
tops where they stand), `top` (the console's top edge seen from above, the face towards the region's bottom), `bottom`
(the bottom edge seen from below, the face towards the region's top), and SWATCHES. `switch2_rear.png`
(REAR_REGIONS): `rear` (the back seen from behind, its x the face's negated), `side_r` and `side_l` (each Joy-Con 2's
inner side, seen from the console: its tongue's face, SL and SR, the mouse sensor and the connector; z along the
region, y down it), `end_r` and `end_l` (the console's ends, the channels' floors and their connectors, seen from
outside; z along the region, y down it), and REAR_SWATCHES. `switch2_screen.png`: the glass's still, VIDEO_PX, the LCD
switched off. A region is (x, y, width, height) in pixels, and the box of millimetres it covers.

The `focused` clip's timing, in frames at FPS, is here so that the video (switch2_video.py) follows the clip
(switch2.py) frame for frame, and so does the pointer: POINTER is the one path both the cursor on the screen and the
Joy-Con 2 on the table follow (pointer_path.py), GAIN screen pixels a millimetre.
"""

import math

from pointer_path import Path

FPS = 30
LENGTH = 360                      # the clip: 12 s

# ---- The console -----------------------------------------------------------------------------------------------------
HALF = 101.1                      # the console's half-width without the Joy-Con 2
HEIGHT = 116.0
DEPTH = 13.9
CORNER = 2.4                      # the face's outline's corners
FRONT_ROUND, BACK_ROUND = 1.0, 2.6   # its edges rounded over, round the face and round the back
LEAN = 18.0                       # degrees: on its kickstand, it leans back this far
# The glass over the face, and the LCD in it (1920 x 1080), both centred on the face across; z their middles.
GLASS = dict(width=196.2, height=108.5, z=58.0, r=1.2)
SCREEN = dict(width=174.9, height=98.4, z=58.0)
# Each end's channel the Joy-Con 2's tongue goes into: y across (from the face), z up, its ends rounded; DEPTH in.
CHANNEL = dict(y=(2.3, 11.55), z=(8.3, 109.2), depth=6.3)
CONNECTOR = dict(z=(51.0, 66.0), y=(5.4, 8.5))   # the pins in each channel's floor, and on each tongue

# The top edge (x along it, y back from the face): POWER and VOLUME at the left; a microphone, a screw, three vents,
# USB-C, the headphone jack, the GAME CARD flap and a second microphone. The bottom edge: the speakers, USB-C between
# two holes and two screws. From the renders of the edges, x from the console's left end there.
def _x(from_left):
    return round(from_left - HALF, 2)


TOP = dict(power=(_x(14.3), _x(21.5)), volume=(_x(25.0), _x(41.2)), minus=_x(28.4), plus=_x(37.6), button_y=6.6,
           button_w=3.3, button_height=0.5, button_travel=0.45, mic=(_x(58.7), 1.9), screw=(_x(77.3), 1.4),
           vents=[(_x(81.3), _x(96.4)), (_x(98.2), _x(113.4)), (_x(115.1), _x(130.2))], vent_y=(4.0, 9.0),
           usb=(_x(135.8), _x(143.8)), usb_h=2.6, jack=(_x(152.4), 1.9), card=(_x(158.5), _x(184.8)),
           card_y=(3.6, 12.6), slit=_x(190.2))
BOTTOM = dict(speakers=(22.0, 61.9), speaker_y=(3.5, 10.4), usb=(-4.1, 4.1), usb_h=2.6, holes=16.65, hole_r=1.6,
              screws=12.35, screw_r=1.1, notch=(-7.0, 7.0))

# ---- The Joy-Con 2 ---------------------------------------------------------------------------------------------------
JOYCON = dict(width=34.9, height=115.0, front=1.6, back=3.0)   # its edges rounded over, but for the inner edge's
# The right Joy-Con 2 from the front, (u, z), u out from its inner edge, from its inner edge's bottom anticlockwise:
# traced from the render of its silhouette (the left one's, mirrored).
JOYCON_OUTLINE = [
    (0.0, 0.0), (4.0, 0.03), (6.0, 0.08), (8.0, 0.24), (10.0, 0.45), (12.0, 0.77), (14.0, 1.21), (16.0, 1.76),
    (18.0, 2.46), (20.0, 3.32), (22.0, 4.45), (24.0, 5.74), (26.0, 7.38), (28.0, 9.50), (30.0, 12.28), (31.0, 14.05),
    (32.0, 16.40), (33.0, 19.35), (34.0, 23.77), (34.58, 28.0), (34.75, 30.0), (34.96, 35.0), (34.99, 40.0),
    (34.99, 88.5), (34.87, 91.0), (34.71, 92.0), (34.34, 94.0), (33.86, 96.0), (33.27, 98.0), (32.52, 100.0),
    (31.61, 102.0), (30.49, 104.0), (29.05, 106.0), (27.28, 108.0), (25.01, 110.0), (23.61, 111.0), (21.97, 112.0),
    (19.98, 113.0), (17.47, 114.0), (13.91, 115.0), (11.04, 115.5), (8.0, 115.83), (6.0, 115.95), (5.2, 115.98),
    (3.6, 115.0), (0.0, 115.0)]
SHOULDER_FROM = (5.2, 88.5)       # the R (or L) button: the outline from here (along the top) round to here (down the
                                  # outer side), a millimetre deep
TONGUE = dict(depth=5.8, y=(2.5, 11.35), z=(8.5, 109.0))      # out of the inner edge into the console's channel
# On the tongue's face, z up it (the right Joy-Con 2's; SR at the top, SL below; the left one's are SL above, SR below).
TONGUE_PARTS = dict(top_pad=(104.5, 2.2), shoulder_pad=(77.0, 94.0), sensor=(69.0, 73.0), pin=(46.5, 1.6),
                    lower_pad=(20.0, 37.5), sync=(10.0, 16.0), pad_y=(4.0, 9.8))
# ZR (or ZL): behind the top outer corner, what its outline from behind (the band round the corner between the outline
# and TRIGGER_INNER) and its profile from the inner side (TRIGGER_LOBE, (y, z)) have in common.
TRIGGER_INNER = [(6.6, 116.5), (6.6, 106.0), (8.5, 104.4), (12.0, 103.4), (16.0, 102.2), (19.5, 100.3), (23.0, 97.2),
                 (26.0, 93.6), (28.5, 90.2), (29.5, 88.8), (36.0, 88.8)]
TRIGGER_LOBE = [(6.0, 116.4), (8.0, 115.7), (10.8, 113.4), (13.0, 111.0), (14.75, 109.6), (16.4, 108.5), (19.3, 107.2),
                (22.1, 106.2), (23.0, 104.0), (23.4, 100.5), (23.2, 96.2), (22.1, 93.0), (19.3, 89.7), (16.4, 87.0),
                (14.75, 84.8), (13.9, 83.5), (6.0, 83.5)]
TRIGGER_PROUD = 0.35              # the trigger stands this far out of the outline, so it reads as a part of its own
RELEASE = dict(u=7.0, z=96.8, width=9.0, height=7.5, r=1.6, proud=1.1)   # the release button, on the back

# The faces' controls, (u, z) on the right Joy-Con 2 (the left one's u the same distance out from its inner edge).
STICK_R, STICK_L = (16.5, 57.6), (16.5, 86.9)
STICK = dict(ring=(8.45, 9.35), ring_height=1.4, cap=7.3, cap_y=(4.6, 7.0), shaft=3.3, dish=0.5)
ABXY = dict(centre=(16.5, 87.0), reach=8.4, r=4.25, height=1.6)        # X up, A out, B down, Y in
DPAD = dict(centre=(16.5, 58.4), reach=8.4, r=4.25, height=1.6)        # the left one's direction buttons
FACE_BUTTONS = [("x", 90.0), ("a", 0.0), ("b", 270.0), ("y", 180.0)]  # degrees round ABXY, from out (u)
PLUS = dict(at=(6.2, 103.6), length=5.8, width=1.7, height=0.8)
MINUS = dict(at=(6.1, 103.7), length=5.8, width=1.7, height=0.8)
HOME = dict(at=(9.4, 37.5), r=3.8, height=0.8)
C_BUTTON = dict(at=(9.3, 27.0), size=6.1, r=1.1, height=0.4)
CAPTURE = dict(at=(7.45, 37.2), size=6.2, r=1.1, height=0.4)

# ---- The kickstand ---------------------------------------------------------------------------------------------------
# A U: two legs hinged on the back half-way up and a bar between their ends; shut, it lies on the back, the bar along
# its bottom edge. Open, the bar rests on the table behind (switch2.py turns the legs until it touches).
KICKSTAND = dict(hinge_z=56.0, hinge_y=DEPTH + 1.4, legs=(80.1, 87.1), thick=2.6, bar=7.0, block=(52.0, 70.0))

# ---- Colours (sRGB, sampled from the renders) ------------------------------------------------------------------------
COLOURS = dict(case="#3A3C40", glass="#08080A", body="#37393D", edge="#2D2F32", button="#2A2C2F",
               legend="#A3A7AD", cap="#232527", blue="#4FB8E0", coral="#F56A55", ring_blue="#5CC3EA",
               ring_coral="#E8604F", seam="#1A1B1D", port="#0B0B0C", vent="#121214", rear="#35383B", logo="#4C4F54",
               kickstand="#383B3F", pin="#C9A55A")

# ---- The atlases -----------------------------------------------------------------------------------------------------
ATLAS = 1024


def region(px, mm):
    return dict(px=px, mm=mm)


PRINT_REGIONS = dict(
    front=region((0, 0, 1024, 440), (-136.5, 136.5, -0.6, 116.7)),       # (x0, x1, z0, z1)
    top=region((0, 446, 1024, 72), (-101.6, 101.6, -0.3, 14.0)),         # (x0, x1, y0, y1): the face at the bottom
    bottom=region((0, 524, 1024, 72), (-101.6, 101.6, -0.3, 14.0)),      # the face at the top
)
SWATCHES = {name: (12 + 24 * k, 620) for k, name in enumerate(("case", "edge", "button", "cap", "ring_blue", "ring_coral"))}
REAR_REGIONS = dict(
    rear=region((0, 0, 1024, 440), (-136.5, 136.5, -0.6, 116.7)),        # seen from behind: x mirrored
    side_r=region((0, 446, 512, 64), (-0.5, 116.5, -0.3, 14.3)),         # (z0, z1, y0, y1)
    side_l=region((512, 446, 512, 64), (-0.5, 116.5, -0.3, 14.3)),
    end_r=region((0, 514, 512, 64), (-0.5, 116.5, -0.3, 14.3)),
    end_l=region((512, 514, 512, 64), (-0.5, 116.5, -0.3, 14.3)),
)
REAR_SWATCHES = {name: (12 + 24 * k, 610) for k, name in enumerate(("kickstand", "blue", "coral", "button"))}

# ---- The screen and its video ----------------------------------------------------------------------------------------
NATIVE = (1920, 1080)             # the LCD's pixels: the screens are laid out in them
LCD_PX = (800, 450)               # the video's picture of the LCD: five twelfths of its pixels
PITCH = LCD_PX[0] / SCREEN["width"]   # pixels a millimetre: 4.57
VIDEO_PX = (816, 466)             # the LCD and 8 pixels of the glass's black round it
LCD_AT = (8, 8)                   # the LCD's top left in the video's frame
VIDEO = dict(width=VIDEO_PX[0] / PITCH, height=VIDEO_PX[1] / PITCH, z=SCREEN["z"])   # the video's quad, mm

MADE_UP = ("dustygul", "arcade")  # the game: Dusty Gulch, from tools/made-up-games (made up: Ninebolt's light-gun game)
# The HOME Menu's other software, made up too: (logo's system, logo's file stem, painting folder).
SOFTWARE = [("n64", "Budling - Sky Garden (Europe)", "budling"), ("snes", "Kaleidrop (Europe)", "kaleidrop"),
            ("ps2", "Bolt & Bramble (Europe)", "bolt-and-bramble"), ("n64", "Whirligig Karts (Europe)",
                                                                     "whirligig-karts"),
            ("ps2", "Groove Courier (Europe)", "groove-courier")]
# The HOME Menu's layout, in NATIVE pixels (from the Nintendo Today screenshot, scaled): the software's tiles, the
# round icons' bar, the top bar and the bottom bar.
TILES = dict(x=149, y=295, size=389, gap=23, r=22)
ICON_BAR = dict(x0=325, x1=1593, y0=773, y1=912, icons=10)
TILE_AT = (TILES["x"] + TILES["size"] / 2, TILES["y"] + TILES["size"] / 2)      # the game's tile, the first

# ---- The focused clip, in frames at FPS ------------------------------------------------------------------------------
WAKE = 8                          # POWER pressed: the screen wakes ...
ON = (11, 20)                     # ... the HOME Menu fading in
RELEASE_PRESS = 28                # the right Joy-Con 2's release button: its pin pushes the Joy-Con 2 out a little ...
PULL = (32, 46)                   # ... and it's drawn out of the channel, straight out to the right ...
CARRY = (46, 76)                  # ... turned onto its side and set down to the console's right, attachment side down
CURSOR = 80                       # the cursor appears (a Joy-Con 2 on a surface, attachment side down, is a mouse)
CLICK_TILE = 114                  # R: the game's tile clicked ...
LAUNCH = (118, 130)               # ... the HOME Menu fading to black as it starts
TITLE = (130, 168)                # the title, SHOOT TO START: the cursor is the game's sights now
CLICK_START = 158                 # shot
PLAY = (166, 290)                 # the street: outlaws pop up, are shot; bottles are shot
SHOTS = [188, 204, 220, 236, 252]
LIFT = (270, 284)                 # the Joy-Con 2 lifted off the table (the sights go) ...
BACK = (284, 306)                 # ... turned back upright and brought to the console's side ...
SNAP = (306, 311)                 # ... and the magnets take it home: the console jolts
SLEEP = 322                       # POWER: sleep
OFF = (324, 334)                  # the screen going dark
CLICK = 3                         # frames a mouse button is held down
CLICKS = (CLICK_TILE, CLICK_START) + tuple(SHOTS)

# ---- The pointer and the Joy-Con 2 on the table ----------------------------------------------------------------------
GAIN = 80.0                       # NATIVE pixels the pointer moves for each millimetre the Joy-Con 2 moves
REST = (1000.0, 560.0)            # where the cursor appears: the middle of where the targets take it
START_AT = (960.0, 780.0)         # SHOOT TO START
# The street (paintings.py's sw2_gulch_street, 1536 x 1024): the 16:9 part shown (its plain sky at the top for the
# score), and its targets in its own pixels, left to right: the burly outlaw behind the near barrel, the skinny one in
# the saloon's upstairs window (kept inside it, above the balcony's railing), the burly one behind the porch's crates,
# the two bottles on the fence rail. Each: who (a pose sheet's figure), at (the middle of the
# figure's foot, its foot's y, its height), aim (where the sights stop), rise (how far it comes up into view), early
# (frames it's there before its shot), its points, and front (what's in front of it, cut back out of the painting:
# ellipses by two corners, polygons). Painted again, the street needs them placed again.
STREET = dict(crop=(0, 80, 1536, 944), targets=dict(
    barrel=dict(who="burly", at=(185.0, 790.0, 360.0), aim=(185.0, 592.0), rise=150.0, early=16, points=100,
                front=[("ellipse", ((-4.0, 712.0), (242.0, 772.0))),
                       ("poly", [(0.0, 742.0), (240.0, 742.0), (240.0, 1024.0), (0.0, 1024.0)])]),
    window=dict(who="skinny", at=(331.0, 405.0, 175.0), aim=(331.0, 305.0), rise=60.0, early=12, points=100,
                clip=(281.0, 236.0, 382.0, 337.0), front=[]),
    crates=dict(who="burly", at=(1162.0, 660.0, 190.0), aim=(1162.0, 548.0), rise=90.0, early=12, points=100,
                front=[("poly", [(1127.0, 577.0), (1199.0, 577.0), (1199.0, 675.0), (1127.0, 675.0)])]),
    bottle_brown=dict(who="brown", at=(1365.0, 773.0, 100.0), aim=(1365.0, 723.0), points=50),
    bottle_blue=dict(who="blue", at=(1418.0, 784.0, 100.0), aim=(1418.0, 734.0), points=50),
))


def street_px(x, y):
    """The street painting's pixel (x, y) on the LCD, NATIVE pixels."""
    x0, y0, x1, y1 = STREET["crop"]
    return (x - x0) * NATIVE[0] / (x1 - x0), (y - y0) * NATIVE[1] / (y1 - y0)


# The targets in the order they're shot: (frame, where the sights aim on the LCD, which). The sights stop on each two
# frames before its shot and leave three frames after it.
TARGETS = [(shot, street_px(*STREET["targets"][name]["aim"]), name)
           for shot, name in zip(SHOTS, ("barrel", "window", "crates", "bottle_brown", "bottle_blue"))]
_WAYPOINTS = [(CURSOR, REST, True), (CURSOR + 6, REST, True), (CLICK_TILE - 4, (TILE_AT[0] + 14, TILE_AT[1] + 8), True),
              (CLICK_TILE + 6, (TILE_AT[0] + 14, TILE_AT[1] + 8), True), (TITLE[0] + 4, (960.0, 600.0), True),
              (CLICK_START - 3, START_AT, True), (CLICK_START + 5, START_AT, True)]
for _f, _at, _what in TARGETS:
    _WAYPOINTS += [(_f - 2, _at, True), (_f + 3, _at, True)]
_WAYPOINTS += [(LIFT[0], (1010.0, 590.0), True)]
POINTER = Path(_WAYPOINTS)
# Where the Joy-Con 2 rests on the table as a mouse, in the set's frame (the console leant back on the table): its
# face's plane at x, its bottom end at y, its tongue on the table, its top end straight away from the viewer. To the
# console's right, clear of the console and of the screen's corner however far the pointer takes it (switch2.py prints
# by how much).
MOUSE = dict(face_x=119.0, front_y=-34.0)


def pointer(f):
    """The pointer's tip at frame f, NATIVE pixels, and whether it's shown: from CURSOR until the Joy-Con 2 is lifted."""
    return POINTER.at(f), CURSOR <= f < LIFT[0] + 2


# ---- Outlines --------------------------------------------------------------------------------------------------------

def joycon_outline(step=1.2):
    """JOYCON_OUTLINE resampled every step millimetres or so along it (each traced span cut into equal parts), its
    corners kept: the inner edge's ends and where the traced spans meet."""
    pts = JOYCON_OUTLINE
    out = []
    for (u0, z0), (u1, z1) in zip(pts, pts[1:]):
        n = max(1, math.ceil(math.hypot(u1 - u0, z1 - z0) / step))
        out += [(u0 + (u1 - u0) * k / n, z0 + (z1 - z0) * k / n) for k in range(n)]
    out.append(pts[-1])
    return out


def rounded_rect(x0, x1, z0, z1, r, steps=6):
    """A rectangle's outline with its corners rounded, anticlockwise from its bottom right."""
    out = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        out += [(cx + r * math.cos(math.radians(a0 + 90 * k / steps)), cz + r * math.sin(math.radians(a0 + 90 * k / steps)))
                for k in range(steps + 1)]
    return out


def stadium(a0, a1, b0, b1, n=10):
    """A pill along b (its ends rounded, a across it): its outline in (a, b), anticlockwise."""
    r = (a1 - a0) / 2
    am = (a0 + a1) / 2
    top = [(am + r * math.cos(math.radians(180 * k / n)), b1 - r + r * math.sin(math.radians(180 * k / n)))
           for k in range(n + 1)]
    bottom = [(am + r * math.cos(math.radians(180 + 180 * k / n)), b0 + r + r * math.sin(math.radians(180 + 180 * k / n)))
              for k in range(n + 1)]
    return top + bottom
