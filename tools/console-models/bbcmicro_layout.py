"""The BBC Micro card's measurements, shared by bbcmicro_print.py (which draws its printing and screens) and
bbcmicro.py (which builds it). Plain Python: Blender's Python imports it too.

The BBC Micro Model B (1981), 409 mm wide, 358 deep and 78 high (the Home Computer Hall of Fame's figures), a twin
5.25-inch disk drive on its back half and a Microvitec Cub colour monitor on the drive, 352 wide, 300 high and 415 deep
(the Science Museum Group's record of one from the BBC's own collection), stacked as schools had them; a made-up game,
Odyssey, on the floppy. Millimetres: x from the middle (left to right), y back from the computer's front, z up from the
table. The computer was measured from photographs of Model Bs on Wikimedia Commons (from above and in front, at an
angle), its keys on the 19.05 mm pitch; the monitor from the Science Museum Group's photograph of it.

The computer: the beige case, the black keyboard panel sunk into its front half; along the panel's back the clear strip
(the speaker's grille at its left, BRITISH BROADCASTING CORPORATION MICROCOMPUTER SYSTEM and the owl at its right); the
red function keys f0 to f9 and BREAK, the keys in five rows (the cursor keys and COPY brown), the space bar; the blank
plate at the panel's left, the three lights (cassette motor, caps lock, shift lock). The drive: a beige box, its two
drives' fronts, each with its slot, its latch and its light. The monitor: its khaki steel case, the dark brown bezel
round the tube, CUB, the red power switch.

One texture (ATLAS square, REGIONS): `panel` (the keyboard panel from above, its keys' legends where their tops are),
the screens (`boot`, `title`, `game_1`, `game_2`: Mode 7's boot and title, Mode 2's game), `bezel` (the monitor's
front), `drive` (the drive's front), `floppy` (the floppy's top), and swatches. A region is (x, y, width, height) in
pixels. """

ATLAS = 1024
U = 19.05                         # the keys' pitch

WIDTH, DEPTH, HEIGHT = 409.0, 358.0, 74.0
FEET = 4.0                        # the case stands on them: 78 in all
PANEL = dict(x=(-180.0, 180.0), y=(22.0, 182.0), depth=10.0)   # the keyboard panel, sunk into the lid
STRIP = dict(y=(160.0, 182.0))    # the clear strip along the panel's back
KEYS = dict(x=-142.0, y=148.0, height=12.0)   # the first row's left edge and middle (y); the keys' height off the floor
# Each row: its offset from the left edge in keys, then (legend, width in keys, colour) for each key.
ROWS = [
    (2.25, [(f"f{k}", 1.0, "red") for k in range(10)] + [("BREAK", 1.0, "black")]),
    (0.0, [("ESCAPE", 1.0, "black")] + [(c, 1.0, "black") for c in "1234567890=^\\"]
     + [("←", 1.0, "brown"), ("→", 1.0, "brown")]),
    (0.0, [("TAB", 1.5, "black")] + [(c, 1.0, "black") for c in "QWERTYUIOP@[£"]
     + [("↑", 1.0, "brown"), ("↓", 1.0, "brown")]),
    (0.0, [("CAPS LOCK", 1.0, "black"), ("CTRL", 1.25, "black")] + [(c, 1.0, "black") for c in "ASDFGHJKL;:]"]
     + [("RETURN", 2.0, "black")]),
    (0.0, [("SHIFT LOCK", 1.0, "black"), ("SHIFT", 1.75, "black")] + [(c, 1.0, "black") for c in "ZXCVBNM,./"]
     + [("SHIFT", 1.75, "black"), ("DELETE", 1.0, "black"), ("COPY", 1.0, "brown")]),
    (3.25, [(" ", 8.5, "black")]),
]
PLATE = dict(x=(-176.0, -148.0), y=(56.0, 98.0))     # the blank plate at the panel's left
LIGHTS = dict(y=34.0, x=[-150.0, -122.0, -94.0])     # cassette motor, caps lock, shift lock

DRIVE = dict(width=360.0, depth=250.0, height=80.0, y=186.0)   # the twin drive on the computer, just behind the
                                                                # strip
BAYS = dict(x=[-88.0, 88.0], size=(150.0, 42.0), z=40.0, slot=(112.0, 5.0), latch=(30.0, 7.0))   # z: above the
                                                                # drive's foot
MONITOR = dict(width=352.0, height=300.0, depth=415.0)        # on the drive, its front with the drive's
SCREEN = dict(size=(272.0, 204.0), z=160.0, bulge=6.0)        # the tube's face, its middle's height above the monitor's
                                                              # foot
FLOPPY = dict(size=133.0, thickness=1.6, out=150.0, label=(110.0, 34.0))   # out: how far in front of its seat it
                                                                # waits

COLOURS = dict(case="#D6CDB6", monitor="#9E8E6C", bezel="#3A3029", print="#FFFFFF")

SCREEN_PX = (240, 180)
REGIONS = dict(panel=(0, 0, 1008, 448), boot=(0, 456) + SCREEN_PX, title=(248, 456) + SCREEN_PX,
               game_1=(496, 456) + SCREEN_PX, game_2=(744, 456) + SCREEN_PX, bezel=(0, 644, 352, 300),
               drive=(360, 644, 432, 108), floppy=(360, 760, 186, 186))
SWATCHES = dict(case=(820, 680), monitor=(852, 680), bezel=(884, 680), black=(916, 680), red=(948, 680),
                brown=(980, 680), dark=(820, 712), lit=(852, 712), floppy=(884, 712), grey=(916, 712))

FPS = 30
LENGTH = 240                 # 8 s


def keys():
    """Every key: (legend, colour, x0, x1, y), y its row's middle; the rows from the back (the function keys) to the
    front."""
    out = []
    for r, (offset, row) in enumerate(ROWS):
        x = KEYS["x"] + offset * U
        y = KEYS["y"] - r * U
        for legend, width, colour in row:
            out.append((legend, colour, x, x + width * U, y))
            x += width * U
    return out
