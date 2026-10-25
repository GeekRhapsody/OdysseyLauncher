"""The PlayStation 3 set's measurements, shared by ps3_print.py (which draws its printing) and ps3.py (which builds it).
Plain Python: Blender's Python imports it too.

The original PlayStation 3 (the CECHA01, 2006), lying flat: 325 x 274 x 98 mm (Wikipedia's figures), and its DualShock
3, 157 mm across. Millimetres: x from its middle (left to right), y back from its front face, z up from the table. The
rest was measured from Evan-Amos's photographs on Wikimedia Commons (the console from the front left and right and the
back right, with its controller; the DualShock 3 at an angle) and the Sixaxis seen from above (its outline traced, its
buttons placed), scaled by the widths.

The console: the glossy shell, its section (SHELL) an arch across its width, its ends curving down, extruded from its
front face to its back; under it the matte plinth, set in, the grille along its front. On the shell's top the silver
line along the front edge and PLAYSTATION 3 reading from the back; in its front, the silver panel with the Blu-ray
slot, the PlayStation mark and the eject mark, the black flap at the left (the card slots behind it, its three lights),
the power mark and SONY at the right end of the lip. The DualShock 3: its outline, its two raised discs (the d-pad's,
the face buttons'), the sticks in their housings, SELECT, START and the PS button, the lights along its front edge.

One texture (ATLAS square, REGIONS): `top` (the shell from above: the silver line, PLAYSTATION 3), `front` (the shell's
front: the silver panel, the slot, the marks, the flap, the lights, SONY), `plinth` (the plinth's front: the grille),
`pad` (the DualShock 3 from above: its discs' outlines, the d-pad's and the face buttons' wells, the symbols, SONY,
SELECT, START, the PS mark), `disc` (the Blu-ray's label: a made-up game, Odyssey), and swatches. A region is (x, y,
width, height) in pixels.
"""

import math

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 325.0, 274.0, 98.0
SHELL_FOOT = 22.0                                 # the shell's underside; the plinth under it
PLINTH = dict(x=(-150.0, 150.0), y=(8.0, 266.0), height=SHELL_FOOT + 1.0)


def arch(x):
    """The shell's top at x: a superellipse, flat across its middle, curving down at its ends."""
    t = min(1.0, abs(x) / (WIDTH / 2))
    return SHELL_FOOT + (HEIGHT - SHELL_FOOT) * (1.0 - t ** 3) ** (1.0 / 3.0)


def shell_section(steps=48):
    """The shell's section, anticlockwise (x, z) seen from in front: its foot, then the arch from its right end."""
    points = [(-WIDTH / 2, SHELL_FOOT), (WIDTH / 2, SHELL_FOOT)]
    for k in range(1, steps):
        x = WIDTH / 2 - WIDTH * k / steps
        points.append((x, arch(x)))
    return points


# The front: the silver panel and its slot, the marks, the flap; (x, z) on the front face.
PANEL = dict(x=(-38.0, 150.0), z=(29.0, 58.0), slant=8.0)       # its left edge slanting in by slant at its foot
SLOT = dict(x=(-24.0, 138.0), z=(47.0, 50.0), depth=70.0)
PS_MARK = dict(at=(56.0, 39.0), height=7.5)
EJECT = dict(at=(56.0, 32.5))
POWER = dict(at=(136.0, 25.5))
LIGHT = dict(at=(124.0, 25.5), size=(2.4, 1.0))
SONY = (151.0, 25.5)
FLAP = dict(x=(-158.0, -40.0), z=(31.0, 56.0), dots=(-120.0, 33.5))
SILVER_LINE = dict(y=(3.5, 8.0))                  # the silver line along the top's front, back from the front face
LOGO = dict(x=26.0, y=(64.0, 252.0), height=13.0)  # PLAYSTATION 3 on the top, reading from the back

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)
SEAT = (56.0, 40.0 + 60.0, (SLOT["z"][0] + SLOT["z"][1]) / 2)   # the disc's middle once it's in

# The DualShock 3, in its own plan (x across, y forward from its grips' ends, its origin there): its outline (traced
# from the Sixaxis seen from above, its shoulder buttons left off), its thickness; its parts.
PAD_RIGHT = [(0.0, 30.0), (12.0, 28.0), (20.0, 23.0), (29.0, 23.0), (36.0, 27.0), (43.0, 14.5), (51.5, 3.4),
             (56.3, 0.9), (63.5, 0.0), (72.9, 3.9), (75.9, 7.3), (78.5, 14.5), (77.5, 40.0), (75.5, 60.0),
             (73.4, 71.0), (68.2, 80.9), (60.0, 86.5), (50.0, 88.5), (38.0, 87.5), (30.0, 85.0), (0.0, 84.3)]
PAD = dict(at=(-212.0, -116.0), turn=16.0, height=22.0, edge=6.0)
DISCS = dict(left=(-51.3, 68.8), right=(47.6, 68.8), r=22.0, height=1.2)
DPAD = dict(at=(-51.3, 68.8), span=27.0, arm=8.2, height=2.2)
FACE = dict(triangle=(48.1, 81.9), circle=(61.7, 68.8), cross=(49.9, 56.5), square=(33.6, 68.8), r=5.4, height=2.6)
STICKS = dict(left=(-26.1, 51.1), right=(28.0, 51.1), housing=13.5, cap=11.0, height=(9.0, 15.0))
SMALL = dict(select=(-15.9, 67.4), start=(13.6, 67.4), ps=(-1.1, 58.8), ps_r=4.6, size=(7.0, 3.6))
LIGHTS = dict(x=(-6.0, -2.0, 2.0, 6.0), y=86.0)   # the four player lights along the top edge

COLOURS = dict(case="#0C0C0E", plinth="#1E1E21", key="#2A2A2E", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 640, 540), front=(0, 548, 1024, 309), plinth=(0, 865, 1024, 74), pad=(648, 0, 376, 212),
               disc=(648, 220, 256, 256))
SWATCHES = dict(silver=(920, 236), green=(952, 236), red=(984, 236), dark=(920, 268), key=(952, 268), lit=(984, 268))

FPS = 30
LENGTH = 240                 # 8 s
