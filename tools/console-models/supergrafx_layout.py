"""The SuperGrafx card's measurements, shared by supergrafx_print.py (which draws its printing) and supergrafx.py (which
builds it). Plain Python: Blender's Python imports it too.

NEC's PC Engine SuperGrafx (PI-TG4, 1989), its HuCard and its PI-PD6 pad: the PC Engine's pad (pc_engine.py builds it)
in the SuperGrafx's dark grey and light blue. No maker's figure was found; it is about 295 x 215 x 65 mm, measured from
photographs with a HuCard (54 mm wide) in them, its box (311 x 266 x 128) bounding it. Millimetres: x from the console's
middle (left to right), y back from its front, z up from the table. Measured from photographs (Evan-Amos's of the
console, its back and its pad on Wikimedia Commons; others from above with a card in).

The console is styled on an engine: the spine down its middle, raised over the wings either side, SUPER GRAFX in light
blue on the strip down its front between the ribs, PC Engine under it, four bolts; behind the strip the HuCard's
channel, the card lying in it face up and slid forwards under the strip, half of it showing, a finger notch at the
channel's back; the rear block behind it (AC ADAPTER) carrying the expansion connector at the back; on each wing three
pipes, each ending in a round cap at its outer end; at the back of each wing a block, the left one with POWER's green
slider (switched on, it slides the green tab over the card's corner, locking it), the right one with HE; on the base in
front of the right wing the S EXP door and the pad's socket.

One texture (ATLAS square, REGIONS): `top` (the console from above, planar-mapped onto every face facing up), `front`
(the base's front at the right), and, where pc_engine_layout.py has them (pc_engine.py's pad and HuCard map them so),
`card` (the HuCard's face: a made-up game) and `pad` (the pad's top), and its swatches. A region is (x, y, width,
height) in pixels.
"""

import pc_engine_layout as P

ATLAS = 1024

WIDTH, DEPTH = 295.0, 215.0
WINGS = dict(depth=182.0, height=24.0, corner=6.0)                 # the base under the wings: its back edge, its top
RAILS = dict(x=(64.0, 126.0), y=(36.0, 70.0, 104.0), width=13.0, height=5.0, pad=(132.0, 13.5, 7.0))  # x, r, height
BLOCKS = dict(x=(70.0, 146.0), y=(124.0, 182.0), height=60.0)       # each wing's back block, either side
SPINE = dict(x=64.0, y=(-2.0, 182.0), height=44.0)                  # its half width, front and back, top
RIBS = dict(x=(32.0, 58.0), count=5, width=2.2, depth=2.0, y=(6.0, 176.0))   # down the spine either side of the strip
STRIP = dict(y=(4.0, 110.0))                                        # the logo strip, the slot under its back
SCREWS = dict(at=[(-45.0, 26.0), (45.0, 26.0), (-45.0, 150.0), (45.0, 150.0)], r=6.0)
CHANNEL = dict(x=(-30.0, 30.0), y=(110.0, 170.0), floor=37.0, notch=(170.0, 182.0, 30.0))   # its back: a finger notch
SLOT = dict(x=(-28.5, 28.5), y=(66.0, 112.0), z=(37.0, 40.0))       # under the strip, the card's front half in it
TOWER = dict(x=(-60.0, 60.0), y=(182.0, DEPTH), height=(58.0, 52.0))   # the rear block: its top's front and back
CONNECTOR = dict(x=(-44.0, 44.0), z=(10.0, 22.0))                   # the expansion connector in its back
POWER = dict(x=(-130.0, -116.0), y=(146.0, 162.0), travel=7.0)     # the slider's well in the left block's top
TAB = dict(x=(-37.0, -31.0), y=(146.0, 160.0), travel=7.0)          # the lock tab, beside the channel's left edge
HATCH = dict(x=(70.0, 104.0), z=(5.0, 19.0))                        # on the base's front: the S EXP door, the socket
SOCKET = dict(x=120.0, z=12.0, r=5.0)

CARD = dict(slide=30.0, drop=56.0)                                  # how far it slides home, how far over it appears
SEAT = (0.0, SLOT["y"][0] + P.CARD["size"][1] / 2 - 2.0, CHANNEL["floor"] + P.CARD["thickness"] / 2 + 0.05)
PAD_AT = (58.0, -92.0)                                              # the pad's middle (pc_engine.py's, moved), in front

COLOURS = dict(case="#4E5357", dark="#1E2023", pad="#5A5C5F", blue="#6ABCDF", green="#60AB81", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 512, 373), front=(520, 0, 504, 120), card=P.REGIONS["card"], pad=P.REGIONS["pad"])
SWATCHES = dict(P.SWATCHES, case=(904, 168), rib=(936, 168), screw=(968, 168), blue=(1000, 168))

FPS = 30
LENGTH = 240                 # 8 s
