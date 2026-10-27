"""The Super A'Can card's measurements, shared by supracan_print.py (which draws its printing) and supracan.py (which
builds it). Plain Python: Blender's Python imports it too.

Funtech's Super A'Can (1995), charcoal grey, and its controller. Funtech's manual gives the console as 235 deep x 215
wide x 60 mm; its parts are placed from a 1200 dpi scan of its top (186 mm across its body, 213 across its side blocks),
the rest from photographs. The cartridge's face is 118.6 x 89.7 mm (measured on a 600 dpi scan); the controller about
140 x 66 x 24 mm, traced from a photograph of it square on and scaled against the console. Millimetres: x from the
middle (left to right), y back from the body's front face, z up from the table.

The console: the body (BODY: its corners rounded in plan) with, on its top, the slot's housing (HOUSING: raised, the
cartridge's flap in its recess between two curved ridges, the vents along the back edge behind it) and the button panel
(PANEL: POWER's slide, EJECT, RESET; the power light at its left); the A'can logo moulded at the front right; the
tunnel housing standing out of the front's foot, the two controller ports in its tunnel; a block on each side, the
right one's opening showing the CD-ROM expansion's edge connector.

The controller (PAD): a dog-bone outline (POINTS, its top towards the cable) with a rounded profile; the lavender D-pad
in its well, Y, X, B and A in red, green, yellow and blue, SELECT and START, the raised A'can panel, the lavender
shoulder buttons; its cable from its top to port 1, a 9-pin plug in it.

One texture (ATLAS square, REGIONS): `top` (the console from above, planar-mapped onto every face facing up), `face`
(the cartridge's face: a made-up game's label on it), `pad` (the controller from above, in its own frame), and swatches.
A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 186.0, 235.0, 56.0
HALF = WIDTH / 2
CORNER = 6.0

# The top's map: x across (the side blocks' outer faces at its edges), y from the tunnel housing's front to the back.
TOP_X = (-106.5, 106.5)
TOP_Y = (-7.0, DEPTH)

HOUSING = dict(rect=(-82.0, 82.0, 117.0, 218.0), top=60.0)
FLAP = dict(rect=(-60.3, 60.3, 150.0, 171.0), depth=2.5, thickness=1.2, open=90.0)
RIDGES = dict(x=70.0, y=(146.6, 174.4), width=3.0, height=1.8, sag=1.4)   # the ridges' middles bow towards the back
VENTS = dict(x=(-64.0, 64.0), y=(228.6, 233.6), count=26, width=2.0, depth=3.0)
PANEL = dict(rect=(-69.0, 69.0, 64.6, 117.0), top=58.0)
POWER = dict(well=(-57.2, -30.9, 73.0, 103.0), knob=12.0, travel=14.0)
EJECT = dict(rect=(-21.5, 24.3, 72.7, 101.0))
RESET = dict(rect=(33.7, 59.7, 73.4, 101.0))
BUTTON_HEIGHT = 2.2
LIGHT = dict(x=-74.0, y=86.2, size=(2.6, 4.2))
LOGO = dict(x=49.2, y=30.3, r=15.9)

TUNNEL = dict(block=(-64.6, 64.6, -6.7, 2.0, 30.0), recess=(-56.0, 56.0, 14.0, 9.0, 27.0))   # x0, x1, y0, y1/back, z
PORTS = dict(x=(-32.0, 32.0), z=18.0, size=(18.0, 8.0))
SIDES = dict(out=13.5, y=(117.0, 218.0), z=(12.0, 46.0), opening=(126.0, 209.0, 19.0, 39.0, 7.0))

# The cartridge: width, thickness, height; it stands in the slot, its face to the front, OUT above the housing.
CART = dict(size=(118.6, 20.0, 89.7), out=40.0)

# The controller, in its own frame (x across, y towards its top, where the cable leaves); placed at AT, turned TURN.
PAD = dict(points=[(0.0, 33.0), (27.0, 26.8), (41.0, 29.6), (54.8, 28.2), (65.0, 19.9), (70.0, 2.3), (66.8, -16.2),
                   (56.7, -29.1), (41.0, -33.3), (25.2, -30.0), (10.4, -26.3), (0.0, -25.4), (-10.4, -26.3),
                   (-25.2, -30.0), (-41.0, -33.3), (-56.7, -29.1), (-66.8, -16.2), (-70.0, 2.3), (-65.0, 19.9),
                   (-54.8, 28.2), (-41.0, 29.6), (-27.0, 26.8)],
           height=22.0, at=(-142.0, -88.0), turn=12.0,
           dpad=(-45.0, -5.1, 10.5, 3.6), well=12.0,
           buttons=dict(y=(44.0, 4.6), x=(32.2, -4.8), b=(55.7, -4.8), a=(44.0, -14.1)), button_r=5.0,
           select=(-6.8, -13.2), start=(6.7, -13.2), pill=(8.3, 3.5),
           panel=((-17.3, 7.9), (16.9, 20.8)), shoulders=(52.0, 24.0))
PAD_SPAN = (-72.0, 72.0, -36.0, 36.0)                      # the pad region's x and y

COLOURS = dict(case="#555657", flap="#4F5051", pad="#47494A", panel="#626463", lavender="#8585BF", red="#B8393B",
               yellow="#FEE04B", green="#48BD72", blue="#375EAE", black="#2C2C2C", cart="#2D5056", dark="#141416",
               metal="#B89A54", lit="#FF3A2C", cable="#1C1C1E")

REGIONS = dict(top=(0, 0, 682, 775), face=(690, 0, 332, 251), pad=(690, 259, 334, 167))
SWATCHES = {name: (706 + 32 * (k % 10), 446 + 32 * (k // 10)) for k, name in
            enumerate(("case", "flap", "pad", "panel", "lavender", "red", "yellow", "green", "blue", "black", "cart",
                       "metal", "lit"))}

FPS = 30
LENGTH = 240                 # 8 s
