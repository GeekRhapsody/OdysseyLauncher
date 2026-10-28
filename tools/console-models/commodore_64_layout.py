"""The Commodore 64 card's measurements, shared by commodore_64_print.py (which draws its printing and its screens),
commodore_64_video.py (which draws the card's video) and commodore_64.py (which builds it). Plain Python: Blender's
Python imports it too.

The set: the C64 (1982, the breadbin: 404 x 216 x 75 mm, Commodore's figures, its rubber feet included), a Commodore
1541 disk drive beside its right end (200 x 97 x 374 mm, the drive's manual) and a Commodore 1702 colour monitor behind
it (373 x 348 mm across its front, measured from a straight photograph of one on Wikimedia Commons at 3.71 pixels a
millimetre; about 345 mm deep, ValorosoIT's figure). The rest was measured from Evan-Amos's photographs on Wikimedia
Commons (the C64 from its front corners and its back, the 1541 from its front left and its back), scaled by the keys'
19.05 mm pitch and the drive's width. Millimetres: x from the computer's middle (left to right), y back from its front,
z up from the table.

The breadbin: its side outline (profile()) across its width: the front face rounding over into the deck, which slopes up
to the back, then rounds down over the ribs into the back face; the seam round it at SEAM. The keyboard is the
VIC-20's (the C64 has its case): the keys in units of U from the main block's left edge (KEYS_X0), in rows from the
front (row 5, the space bar's) to the back (row 1, the digits'), standing in their wells (wells()), the four function
keys in a well of their own. Everything on the deck is placed in its frame: x across, s up the slope from the deck's front edge, h off it;
deck_point() maps (s, h) to the model's (y, z). Behind the keys: the badge (commodore, the rainbow, 64), the POWER
plate and its light, and the ribs. In its right end, a recess holds CONTROL PORT 1 and 2, the power switch (a rocker)
and the power socket; in its back, the cartridge port and the user port.

The 1541 (DRIVE: its left end at x0, its front at y = 0): its top shell rounded over at the front, the seam round its
base; on its front, the brown band (commodore, the rainbow, 1541) and the drive's brown bezel standing proud of it, the
slot across it, the lever (its knob the pivot, its handle along the slot while it's open, turned down to shut it), the
red drive light under the lever, the green power light at the left; vents across the back of its top.

The 1702 (MONITOR: its front's middle at `at`): a beige box, the dark bezel sunk into its front, the opening's walls
sloping back to the curved glass; under it the strip (the commodore badge and the POWER light, VIDEO MONITOR MODEL
1702, the power button), the control door and the jacks; behind it the dark housing of the tube.

Three textures. `print` (ATLAS square, REGIONS): `top` (the computer seen from above, planar-mapped onto every face
facing up: the key tops and their legends, the deck's frame, the badge, the POWER plate, the ribs), `fronts` (each key's
front face, a cell each, with the legends printed there: the graphics, the colours' names, HOME, DEL, f 2), `side` (the
right end and its recess), `seam` (a strip up the case's height, the seam's line across it, which its other sides take
by their height) and swatches. `devices` (DEVICE_REGIONS): the drive's front, top and sides' strip (`drive_seam`), the
floppy's two sides, the monitor's lower front and top, and swatches. `screen`: the glass showing the C64's start-up
screen, the video's first frame (SCREEN_PX, the video's size).

The focused clip's timing (frames at FPS) is shared with the video, which follows it frame for frame.
"""

import math

# ---- The C64 ---------------------------------------------------------------------------------------------------------
WIDTH, DEPTH, HEIGHT = 404.0, 216.0, 72.0      # its case; the feet (3 mm) are left out
SEAM = 14.0                                     # the seam round it, between the base and the top
FRONT_ROUND = (22.0, 26.0, 22.0)                # the front's rounding into the deck: its centre (y, z) and radius
DECK_BACK = (160.0, 69.0)                       # where the deck meets the back's rounding (y, z)
BACK_FACE = 40.0                                # the back's rounding comes down into the back face here (z)


def _deck_front():
    """The deck's front edge (y, z): where the front's rounding meets it, tangent to it."""
    cy, cz, r = FRONT_ROUND
    slope = math.atan2(DECK_BACK[1] - cz - r, DECK_BACK[0] - cy)      # near enough the deck's own slope
    a = math.pi / 2 + slope
    return cy + r * math.cos(a), cz + r * math.sin(a), a


DECK_FRONT = _deck_front()[:2]
SLOPE = math.atan2(DECK_BACK[1] - DECK_FRONT[1], DECK_BACK[0] - DECK_FRONT[0])
DECK_LENGTH = math.hypot(DECK_BACK[0] - DECK_FRONT[0], DECK_BACK[1] - DECK_FRONT[1])


def _bezier(p0, p1, p2, p3, n):
    out = []
    for k in range(n + 1):
        t = k / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def profile():
    """The side outline, (y, z), anticlockwise seen from its right end: the bottom, the back face, the back's rounding
    over the ribs, the deck, the front's rounding and the front face."""
    cy, cz, r = FRONT_ROUND
    a0 = _deck_front()[2]
    front = [(cy + r * math.cos(a0 + (math.pi - a0) * k / 8), cz + r * math.sin(a0 + (math.pi - a0) * k / 8))
             for k in range(9)]
    by, bz = DECK_BACK
    c, s = math.cos(SLOPE), math.sin(SLOPE)
    back = _bezier((DEPTH, BACK_FACE), (DEPTH, BACK_FACE + 20.0), (by + 24.0 * c, bz + 24.0 * s), (by, bz), 10)
    return [(3.0, 0.0), (DEPTH - 3.0, 0.0), (DEPTH, 3.0)] + back + front + [(0.0, 3.0)]


def deck_point(s, h):
    """The model's (y, z) of the point s up the deck from its front edge and h off it."""
    fy, fz = DECK_FRONT
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return fy + s * c - h * k, fz + s * k + h * c


# The keyboard: KEYS_X0 is the main block's left edge, U a key's pitch, GAP between two keys. A key stands from the
# well's floor (WELL below the deck) to its top, KEY_HEIGHT above it, its top inside its base by KEY_INSET at its sides
# and back and by KEY_FRONT at its front, so its front face slopes, as a Commodore keycap's does.
U, GAP = 19.05, 1.0
KEYS_X0 = -186.0
ROW_S = {5: 6.0, 4: 25.05, 3: 44.1, 2: 63.15, 1: 82.2}      # each row's front edge, up the deck
WELL, KEY_HEIGHT, KEY_INSET, KEY_FRONT = 4.0, 10.0, 2.0, 4.2
FKEYS_X = 140.0                                             # the function keys' left edge
FKEY_W = 1.5                                                # their width, in units
PRESS = 3.5                                                 # how far a key goes down


def kx(u):
    return KEYS_X0 + u * U


def key_rect(xu, row, wu):
    """A key's base, (x0, s0, x1, s1) in the deck's frame."""
    s0 = ROW_S[row]
    return kx(xu) + GAP / 2, s0 + GAP / 2, kx(xu + wu) - GAP / 2, s0 + U - GAP / 2


def fkey_rect(row):
    s0 = ROW_S[row]
    return FKEYS_X + GAP / 2, s0 + GAP / 2, FKEYS_X + FKEY_W * U - GAP / 2, s0 + U - GAP / 2


def _row(names, x0, row, tops, fronts):
    return [(n, x0 + i, row, 1.0, t, f) for i, (n, t, f) in enumerate(zip(names, tops, fronts))]


G = "#"     # a front legend of two PETSCII graphics (commodore_64_print.py draws them)
LETTERS = "QWERTYUIOPASDFGHJKLZXCVBNM"

# (name, x in units, row, width in units, the legend on its top, the legend on its front): a legend's line breaks split
# its lines, top first.
KEYS = (
    _row(["arrow"] + [f"d{k}" for k in "1234567890"] + ["plus", "minus", "pound", "home", "del"], 0.0, 1,
         ["←", "!\n1", '"\n2', "#\n3", "$\n4", "%\n5", "&\n6", "'\n7", "(\n8", ")\n9", "0", "+", "−", "£", "CLR",
          "INST"],
         ["", "BLK", "WHT", "RED", "CYN", "PUR", "GRN", "BLU", "YEL", "RVS\nON", "RVS\nOFF", G, G, G, "HOME", "DEL"])
    + [("ctrl", 0.0, 2, 1.5, "CTRL", "")]
    + _row(list("qwertyuiop") + ["at", "star", "up"], 1.5, 2, list("QWERTYUIOP") + ["@", "*", "↑"],
           [G] * 12 + ["π"])
    + [("restore", 14.5, 2, 1.5, "RESTORE", "")]
    + [("stop", 0.0, 3, 1.0, "RUN\nSTOP", ""), ("lock", 1.0, 3, 1.0, "SHIFT\nLOCK", "")]
    + _row(list("asdfghjkl") + ["colon", "semicolon", "equals"], 2.0, 3, list("ASDFGHJKL") + ["[\n:", "]\n;", "="],
           [G] * 9 + ["", "", ""])
    + [("return", 14.0, 3, 2.0, "RETURN", "")]
    + [("cbm", 0.0, 4, 1.0, "C=", ""), ("lshift", 1.0, 4, 1.5, "SHIFT", "")]
    + _row(list("zxcvbnm") + ["comma", "period", "slash"], 2.5, 4, list("ZXCVBNM") + ["<\n,", ">\n.", "?\n/"],
           [G] * 7 + ["", "", ""])
    + [("rshift", 12.5, 4, 1.5, "SHIFT", ""), ("crsr_v", 14.0, 4, 1.0, "CRSR\n⇕", ""),
       ("crsr_h", 15.0, 4, 1.0, "CRSR\n⇔", "")]
    + [("space", 3.0, 5, 9.0, "", "")]
)
FKEYS = [(f"f{2 * k + 1}", row, f"f {2 * k + 1}", f"f {2 * k + 2}") for k, row in enumerate((1, 2, 3, 4))]


def wells():
    """The wells the keys stand in, each an (x, s) outline: the main block (its front row only the space bar) and the
    function keys'."""
    m = 1.2
    s5, s4, s1 = ROW_S[5] - m, ROW_S[4] - m, ROW_S[1] + U + m

    def rect(x0, x1, a, b):
        return [(x0, a), (x1, a), (x1, b), (x0, b)]
    return [
        [(kx(3.0) - m, s5), (kx(12.0) + m, s5), (kx(12.0) + m, s4), (kx(16.0) + m, s4), (kx(16.0) + m, s1),
         (kx(0.0) - m, s1), (kx(0.0) - m, s4), (kx(3.0) - m, s4)],
        rect(FKEYS_X - m, FKEYS_X + FKEY_W * U + m, ROW_S[4] - m, s1),
    ]


def front_cells():
    """The keys whose fronts carry a legend, each with its cell in REGIONS["fronts"], (x, y, w, h) pixels: the cells
    as wide over high as the faces (FRONT_CELL for a key a unit wide, half as wide again for a function key), in
    rows."""
    fx, fy, fw, _ = REGIONS["fronts"]
    cw, ch = FRONT_CELL
    cells, x, y = {}, fx, fy
    for name in [k[0] for k in KEYS if k[5]] + [f[0] for f in FKEYS]:
        w = round(cw * FKEY_W) if name in {f[0] for f in FKEYS} else cw
        if x + w > fx + fw:
            x, y = fx, y + ch
        cells[name] = (x, y, w, ch)
        x += w
    return cells


FRAME = dict(x=WIDTH / 2 - 9.0, s=(-3.0, 103.0))           # the line round the keyboard's plate: its sides, its front
BADGE = dict(x=(-176.0, -52.0), s=(106.0, 114.5))          # the badge: commodore, the rainbow and 64
POWER = dict(x=(150.0, 186.0), s=(110.0, 116.5), light=(181.0, 113.25), r=1.9)   # the POWER plate and its light
RIBS = dict(y0=140.0, step=8.6, count=6)                   # the ribs across the back of the deck and its rounding (y)

# The right end's recess and what's in it, (y0, y1, z0, z1); the rocker's travel.
RECESS = dict(y=(44.0, 202.0), z=(16.0, 50.0), depth=3.0)
PORTS = dict(control1=(56.0, 84.0), control2=(96.0, 124.0), switch=(138.0, 151.0), socket=(166.0, 190.0))
SWITCH = dict(z=(25.0, 41.0), out=2.2, rock=11.0)
CART_PORT = dict(x=(130.0, 196.0), z=(9.0, 27.0), depth=22.0)   # in its back
USER_PORT = dict(x=(-196.0, -130.0), z=(9.0, 22.0), depth=16.0)

# ---- The 1541 --------------------------------------------------------------------------------------------------------
DRIVE = dict(x0=236.0, width=200.0, height=97.0, depth=374.0, seam=23.0, round=(16.0, 22.0))   # round: the top's
#                                                                                   front rounding (back, down)
# On its front, x from its left end:
BEZEL = dict(x=(28.0, 184.0), z=(8.0, 57.0), out=2.5)        # the drive's bezel
SLOT = dict(x=(37.0, 177.0), z=(44.0, 47.4), depth=40.0)     # the disk's slot through it
LEVER = dict(x=67.0, z=39.0, knob=5.2, out=10.0, handle=(33.0, 6.4, 3.4))   # the pivot; the handle's length, width,
#                                                                             thickness
DRIVE_LIGHT = dict(x=67.0, z=24.0, size=(4.2, 1.8))         # the red drive light, under the lever
GREEN = dict(x=14.0, z=31.0, r=2.4)                         # the green power light, on the case
BAND = dict(x=(8.0, 192.0), z=(61.0, 80.0))                 # the brown band over the bezel
DISK = dict(size=133.35, thickness=1.8, behind=3.0)         # a 5.25-inch floppy; how far its end goes in past the front

# ---- The 1702 --------------------------------------------------------------------------------------------------------
MONITOR = dict(
    at=(0.0, 258.0),                 # its front's middle (x) and its front (y)
    width=373.0, height=348.0, depth=300.0, feet=4.0,
    rear=dict(depth=96.0, size=(318.0, 290.0), end=(214.0, 184.0)),   # the tube's housing: its front and back sizes
    bezel=dict(x=178.5, z=(73.0, 341.0), recess=3.0),                 # the dark frame sunk into the front
    opening=dict(x=165.5, z=(85.0, 328.0), r=14.0),                   # the opening in it, at its face
    glass=dict(size=(280.0, 210.0), z=198.0, back=26.0, bulge=8.0),   # the glass: its edge this far behind the frame
    strip=dict(z=(37.0, 62.0)),
    button=dict(x=(158.0, 174.0), z=(42.0, 57.0), out=3.0),
    door=dict(x=(-180.0, 121.0), z=(11.0, 35.0)),
    jacks=dict(x=(123.0, 183.0), z=(7.0, 34.0)),
)

COLOURS = dict(case="#CEC5AE", key="#3A3127", fkey="#968F7A", badge="#BDBAAD", ink="#4A4846", dark="#141416",
               drive="#D0C8B4", band="#6C6158", bezel="#4B3C33", handle="#5C4A3E", monitor="#B8AFA4",
               frame="#1C1B1A", rear="#3A3938", disk="#1A1A1C", sleeve="#F2EFE6", lit="#FF3A2C", green="#46F06A")

ATLAS = 1024
REGIONS = dict(top=(0, 0, 1024, 548), fronts=(0, 556, 1024, 224), side=(0, 788, 560, 186),
               seam=(580, 840, 16, 150))      # seam: the sides' colour up their height, the seam's line in it
FRONT_CELL = (72, 56)                     # a key front's cell in `fronts`, pixels: 18.05 x 14 mm
SWATCHES = {name: (612 + 40 * (k % 9), 808 + 40 * (k // 9)) for k, name in
            enumerate(("case", "key", "fkey", "dark", "lit", "badge", "recess", "black", "plug"))}

DEVICE_REGIONS = dict(drive_front=(0, 0, 600, 292), drive_top=(612, 0, 240, 449), floppy=(0, 300, 400, 400),
                      floppy_under=(410, 460, 190, 190), monitor_front=(0, 708, 1000, 164),
                      monitor_top=(612, 460, 300, 240), drive_seam=(930, 0, 16, 200))
DEVICE_SWATCHES = {name: (40 + 44 * k, 900) for k, name in
                   enumerate(("drive", "band", "bezel", "handle", "monitor", "frame", "rear", "disk", "lit", "dark",
                              "hub", "knob"))}

# ---- The screens -----------------------------------------------------------------------------------------------------
FRAME_PX = (384, 272)          # the C64's picture with its border (PAL), the paper's 320 x 200 in it at PAPER_AT
PAPER_AT = (32, 36)
SCREEN_PX = (800, 600)         # the video's frames and the glass's still: the glass's 4:3, the picture twice its size
RASTER_AT = (16, 28)           # where the doubled picture sits in a frame

MADE_UP = ("Deep Fathom (Europe)", "megadrive", "deep-fathom")   # the made-up game: its release, system and concept

# ---- The clip: frames at FPS (the video follows them) ----------------------------------------------------------------
FPS = 30
LENGTH = 300                   # 10 s
DISK_IN = (6, 14, 22, 30, 40)  # appears; shows its label; levels at the slot's mouth; slides in until
LEVER_SHUT = (44, 50)
TYPED = 54                     # LOAD"*",8,1: a key every PER_KEY frames from here
PER_KEY = 4
COMMAND = 'LOAD"*",8,1'
RETURN = 100
SEARCHING = 104                # SEARCHING FOR *
DRIVE_ON = (108, 190)          # the drive's light
LOADING = 124
LOADER = 146                   # the loader clears the screen
PICTURE = (150, 186)           # the loading picture comes in, a character cell at a time
F1 = 206                       # f1 starts the game
GAME = 210
FIRE = (222, 240, 256)         # the space bar fires a torpedo
LEVER_OPEN = (262, 268)
DISK_OUT = (266, 274, 284, 292)  # pops out; drawn out; lifted; gone
POWER_OFF = 282                # the switch: off, then on again
POWER_ON = 290
BANNER = 293                   # the start-up screen is back
