"""The Nintendo GameCube's measurements, shared by gamecube_print.py (which draws its printing) and gamecube.py (which
builds it). Plain Python: Blender's Python imports it too.

The GameCube (2001) in indigo, 150 x 161 x 110 mm (Nintendo's figures), its handle at the back, and its controller.
Millimetres: x from the console's middle (left to right), y back from its front face, z up from the table. The rest
was measured from Evan-Amos's photographs on Wikimedia Commons (the console from each corner, with its lid open, and
with its controller), scaled by the console's width; the controller's outline was traced from its photograph from
above, scaled to 150 mm across.

The console: a cube with rounded edges, a seam round it near its foot; the light grey panel on its front with the
four controller ports and the two memory card slots; a grid of square vents in each side; on its top the lid (its
hinge along the back, its round black window with NINTENDO GAMECUBE), POWER (light grey) at the back left, RESET at the
front left, OPEN at the front right, Nintendo's name at the back right; the black handle round the back. The
controller lies to its left.

Two textures. `print` (ATLAS square, REGIONS): `top` (the console seen from above: the lid's seam, its window and the
logo, the buttons' names), `panel` (the front panel seen from in front: the ports' rims and numbers, the slots and
their names), `pad` (the controller's top: its colours, the sticks' gates, the logo), and swatches. `disc` (DISC_ATLAS):
the mini disc's label side (a made-up game, Odyssey) and its shiny side. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024
DISC_ATLAS = 512

WIDTH, DEPTH, HEIGHT = 150.0, 161.0, 110.0
EDGE = 7.0                                                 # its edges' rounding
SEAM = dict(z=20.0, depth=0.8)                             # the seam round it near its foot
PANEL = dict(x=(-62.0, 62.0), z=(10.0, 86.0), out=2.0)     # the front panel, standing out of the front
PORTS = dict(x=(-45.0, -15.0, 15.0, 45.0), z=60.0, r=8.0, depth=10.0)
SLOTS = dict(x=(-30.0, 30.0), z=27.0, size=(40.0, 5.0))
VENT = dict(columns=8, rows=9, hole=6.4, pitch=8.6, y=88.0, z=58.0, depth=4.0)   # each side's grid: its middle (y, z)
LID = dict(x=(-58.0, 58.0), y=(16.0, 150.0), thickness=6.0, hinge=(152.0, HEIGHT - 3.0), open=-70.0)
WINDOW = dict(at=(0.0, 86.0), r=36.0)                      # the lid's black window, its middle (x, y)
BUTTONS = dict(power=(-61.0, 140.0, 8.5), reset=(-61.0, 20.0, 8.5), open=(61.0, 20.0, 8.5))   # x, y, radius
HANDLE = dict(at=(0.0, 150.0, 96.0), r=79.0, width=13.0, thickness=7.0, tilt=-18.0)  # the half ring's middle,
                                                                                     # radius, band, its lean
DISC = dict(r=40.0, hole=7.5, thickness=1.2)
SPINDLE = (0.0, 86.0, HEIGHT - 26.0)                       # where the disc sits, its middle

# The controller: its outline traced from above, y from its grips' tips, x from its middle; it lies at PAD["at"],
# turned PAD["turn"] degrees.
PAD_OUTLINE = [(0.0, 115.1), (19.5, 113.7), (36.5, 109.3), (41.9, 109.7), (48.6, 108.4), (58.9, 103.0), (65.6, 94.5),
               (69.6, 87.3), (71.9, 77.5), (74.6, 47.0), (75.0, 21.9), (73.7, 10.3), (71.4, 4.9), (66.0, 0.0),
               (61.6, 0.0), (57.1, 2.7), (54.0, 8.5), (48.1, 36.3), (45.0, 33.6), (41.4, 36.7), (36.5, 29.6),
               (29.8, 25.5), (19.5, 25.1), (15.4, 26.4), (10.1, 30.4), (5.6, 38.1), (4.3, 46.6), (-0.2, 47.0),
               (-3.4, 47.0), (-6.0, 40.7), (-8.7, 33.6), (-15.4, 27.3), (-22.2, 25.1), (-27.1, 25.1), (-34.3, 27.8),
               (-39.2, 32.2), (-43.2, 39.0), (-46.3, 39.0), (-47.7, 40.3), (-54.4, 8.5), (-56.6, 4.5), (-61.6, 0.9),
               (-67.8, 1.8), (-70.5, 4.5), (-73.2, 10.3), (-75.0, 21.9), (-75.0, 42.5), (-71.9, 81.9), (-69.6, 89.6),
               (-66.5, 94.5), (-53.1, 106.6), (-49.0, 108.4), (-41.4, 107.9), (-23.1, 113.3), (-2.5, 115.1)]
PAD = dict(at=(-168.0, 40.0), turn=16.0, thickness=24.0, length=115.1,
           stick=(-46.3, 83.1), rim=18.8, gate=11.9, cap=9.9, dpad=(-25.0, 48.4, 19.8, 6.9),
           start=(-0.7, 78.9, 3.5), a=(44.4, 80.6, 8.9), b=(27.5, 72.2, 5.5),
           x=(61.2, 83.6, 7.4, 14.9, -14.0), y=(39.9, 94.5, 14.9, 7.4, 10.0),     # the kidneys: x, y, w, h, turn
           c=(23.1, 48.9), c_gate=9.9, c_cap=6.9, logo=(0.2, 102.9))

COLOURS = dict(case="#5F58A6", grey="#C9CACC", dark="#1C1D1F", disc="#FFFFFF", panel_dark="#8E9093")

REGIONS = dict(top=(0, 0, 512, 550), panel=(520, 0, 504, 309), pad=(520, 317, 504, 387))
SWATCHES = dict(grey=(16, 576), dark=(48, 576), green=(80, 576), red=(112, 576), yellow=(144, 576), white=(176, 576),
                case=(208, 576), lit=(240, 576))
DISC_REGIONS = dict(label=(0, 0, 256, 256), data=(256, 0, 256, 256))

FPS = 30
LENGTH = 240                 # 8 s
