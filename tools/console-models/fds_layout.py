"""The Famicom Disk System's measurements, shared by fds_print.py (which draws its printing) and fds.py (which builds
it). Plain Python: Blender's Python imports it too.

The Family Computer (HVC-001), 150 x 220 x 60 mm, sitting on its Disk System's drive (HVC-022), 150 x 246 x 73 mm (both
Nintendo's figures), the RAM adapter (HVC-023) in its cartridge slot, its two controllers in their docks. Millimetres:
x from the set's middle (left to right), y back from the drive's front, z up from the table. The rest was measured from
Evan-Amos's photographs on Wikimedia Commons (the Famicom on its drive, the drive alone, the Famicom alone and with its
controller out, a disk card), scaled by their widths; the disk card is 76 x 90 mm.

The drive: a red box in two halves, a seam round it, the black panel in its front (the disk's slot in its bay, the
yellow eject button, Nintendo HVC-022 FAMILY COMPUTER DISK SYSTEM, the operating lamp, grooved ends). The Famicom on
it, its front set back: the dark red base; the white shell, its front sloping up to the front deck (POWER, the EJECT
lever, RESET) and stepping up behind it to the back deck, where the black RAM adapter lies in the slot; the
controllers standing in their red docks down its sides, their gold faces outwards; FAMILY COMPUTER on the red band
across the front slope.

One texture (ATLAS square, REGIONS): `top` (the Famicom and the drive seen from above: the decks' printing, the RAM
adapter's top; planar-mapped onto every face facing up), `band` (the front slope, along it), `drive` (the drive's
front), `pad1` and `pad2` (the controllers' faces), `side_a` and `side_b` (the disk card's two sides: a made-up game,
Odyssey), and swatches. A region is (x, y, width, height) in pixels.
"""

import math

ATLAS = 1024

# -- The drive -------------------------------------------------------------------------------------------------------

WIDTH = 150.0
DRIVE = dict(depth=246.0, height=73.0, seam=37.0, r=4.0)
PANEL = dict(x=(-70.0, 70.0), z=(6.0, 65.0), depth=2.0)    # the black panel sunk into its front
BAY = dict(x=(-50.0, 38.0), z=(39.0, 60.0), depth=4.0)     # the slot's bay in it
SLOT = dict(x=(-41.0, 37.0), z=(47.5, 51.5), depth=96.0)   # the disk's slot, deep enough for the whole card
EJECT = dict(x=(11.0, 24.0), z=(30.0, 35.5), out=3.0)      # the yellow eject button
LAMP = (51.0, 23.0, 1.6)                                   # the operating lamp: x, z, radius

# -- The Famicom -----------------------------------------------------------------------------------------------------

FAMICOM = dict(y=20.0, depth=220.0, z=DRIVE["height"])     # its front (back from the drive's front) and its foot


def shell_profile():
    """The white shell's side outline, (y, z) from the Famicom's front and foot: the front slope, the front deck, the
    step, the back deck."""
    return [(0.0, 7.0), (220.0, 7.0), (220.0, 41.0), (217.0, 44.0), (100.0, 44.0), (96.0, 37.0), (28.0, 34.0),
            (4.0, 11.0), (0.0, 8.5)]


BASE = dict(x=74.0, height=7.5)                             # the dark red base under the shell
SLOPE = ((4.0, 11.0), (28.0, 34.0))                         # the front slope: its foot and its top, (y, z)
DECK = ((28.0, 34.0), (96.0, 37.0))                         # the front deck
POWER = dict(at=(-36.0, 52.0), size=(16.0, 10.0, 5.0), travel=6.0)    # its middle (x, y from the front); w, d, h
RESET = dict(at=(37.0, 42.0), size=(18.0, 15.0, 3.0))
LEVER = dict(x=(-10.0, 10.0), y=(56.0, 84.0), top=56.0)    # the EJECT lever: a wedge up to its top
CONTROLLERS = dict(y=(78.0, 206.0), z=(7.5, 57.5), x=(61.0, 76.0))     # in their docks: along, up, across (each side)
ADAPTER = dict(x=(-56.0, 56.0), y=(98.0, 228.0), top=58.0, grooves=6)  # the RAM adapter on the back deck
TAB = dict(x=(-26.0, -6.0), z=(1.0, 13.0), out=3.0)        # the expansion port's cover, at the base's front

# -- The disk card ---------------------------------------------------------------------------------------------------

DISK = dict(size=(76.0, 90.0), thickness=3.0, inside=6.0)  # w, length; how much stays out of the slot once in

COLOURS = dict(red="#B2202A", white="#EDE8DC", dark="#141416", base="#7A1A1E", yellow="#F3B700")

REGIONS = dict(top=(0, 0, 400, 656), band=(408, 0, 400, 104), drive=(408, 112, 400, 196),
               pad1=(408, 316, 400, 156), pad2=(408, 480, 400, 156), side_a=(816, 0, 208, 246),
               side_b=(816, 254, 208, 246))
SWATCHES = dict(red=(16, 680), white=(48, 680), dark=(80, 680), base=(112, 680), yellow=(144, 680), lit=(176, 680),
                lamp_off=(208, 680), gold=(240, 680))

FPS = 30
LENGTH = 240                 # 8 s


def slope_length():
    (y0, z0), (y1, z1) = SLOPE
    return math.hypot(y1 - y0, z1 - z0)
