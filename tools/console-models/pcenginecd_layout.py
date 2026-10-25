"""The PC Engine Duo's measurements, shared by pcenginecd_print.py (which draws its printing) and pcenginecd.py (which
builds it). Plain Python: Blender's Python imports it too.

The PC Engine Duo (1991), the PC Engine with the Super CD-ROM² built in, and its pad. No maker's dimensions were found,
so the size is the photographs': the HuCard's door (about 60 mm across, for the 54 mm card) and the CD lid (about 130
mm, for the 120 mm disc) both give 290 mm for its width; the rest was measured from Evan-Amos's photographs on Wikimedia
Commons (the Duo from in front, from the front left, with its pad, with its flaps up; the TurboDuo, the same case),
scaled by that width: a flat box, its front about 30 mm high, the panels 11 mm more. Millimetres: x from its middle
(left to right), y back from its front face, z up from the table.

The body: a flat box, its sides finely ribbed, three grooves along its top at the left. On it, the left panel (the PC
Engine's side: PC Engine DUO) and the CD lid (hinged at its back: the Compact Disc logo, PUSH CLOSE, the groove across
it, NEC), the CD's well and spindle under the lid. Along the front strip: POWER (its teal slider in the front face), the
HuCard's door with its zigzag edge, the pad's socket, BUSY, the LOCK slider and the round OPEN button. The pad: a
rounded slab, the cable's dome along its back, its black face plate with the blue arc round the D-pad, II and I, their
turbo switches, SELECT and RUN.

One texture (ATLAS square, REGIONS): `top` (the Duo from above: the panels' printing, the strip's names, the lights),
`front` (its front face: POWER's names, PAD, the HuCard door's tab), `pad` (the pad's top), `disc` (the CD's label: a
made-up game, Odyssey), and swatches. A region is (x, y, width, height) in pixels.
"""

WIDTH, DEPTH = 290.0, 215.0
BASE_TOP = 30.0                                   # the body's top; the panels stand on it
PANEL_TOP = 41.0
EDGE = 3.0
STRIP = 48.0                                      # the front strip's depth: the panels start behind it
LEFT_PANEL = dict(x=(-128.0, -16.5), y=(STRIP, 212.0))
LID = dict(x=(-15.0, 115.5), y=(STRIP, 208.0), groove=(118.0, (6.0, 110.0)))   # the groove's y and its x span
WELL = dict(at=(50.0, 128.0), r=62.0, depth=7.0, spindle=7.0)
FINS = dict(x=[-141.0, -136.5, -132.0], y=(52.0, 206.0), width=2.0, depth=3.0)
RIBS = dict(y=(12.0, 206.0), pitch=5.4, width=2.4, depth=2.0, z=(5.0, 26.0))

POWER = dict(x=(-127.0, -104.0), z=(8.0, 17.0), knob=8.0, travel=9.0, out=2.0)   # its slot in the front; the knob
DOOR = dict(x=(-100.0, -40.0), y=(4.0, STRIP), tab=(-88.0, -55.0, 9.0, 21.0), height=1.6)   # on the strip; its tab
PAD_PORT = dict(x=-31.6, z=16.0, r=5.2)
BUSY = dict(x=(0.0, 9.5), y=26.0)
LOCK = dict(x=(57.0, 66.0), y=24.0, height=2.0)
OPEN = dict(at=(101.0, 26.0), r=7.0, height=2.5)

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)

# The pad, in its own plan (x across, y away from the player, its middle at the origin): as the PC Engine model's.
PAD = dict(at=(-196.0, -58.0), turn=12.0, size=(132.0, 64.0, 21.0), r=10.0,
           dome=dict(r=24.0, y=32.0, height=3.5),
           plate=(-60.0, 60.0, -27.0, 22.0),
           dpad=(-41.0, -10.0, 24.0, 8.4), select=(-12.0, -15.0), run=(8.0, -15.0), pill=(11.0, 4.6),
           ii=(32.0, -3.0), i=(49.0, -3.0), button_r=7.6)

COLOURS = dict(case="#47484C", key="#202023", print="#FFFFFF")

ATLAS = 1024
REGIONS = dict(top=(0, 0, 640, 474), front=(0, 482, 640, 112), pad=(0, 602, 512, 252), disc=(648, 0, 256, 256))
SWATCHES = dict(teal=(680, 280), lavender=(712, 280), grey=(744, 280), dark=(776, 280), lit=(808, 280),
                silver=(840, 280), white=(872, 280))

FPS = 30
LENGTH = 240                 # 8 s
