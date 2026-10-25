"""The PlayStation 5's measurements, shared by ps5_print.py (which draws its printing) and ps5.py (which builds it).
Plain Python: Blender's Python imports it too.

The first PlayStation 5 with its disc drive (2020), standing on its stand, 390 mm high, 260 deep and 104 wide (Sony's
figures), and its DualSense lying in front of it, a made-up game, Odyssey, on the disc. Millimetres: x from its middle
(left to right), y back from its front, z up from the table. Its front's hourglass (the white panels flaring out to the
top and the bottom, nearest the black core a little above the middle) was traced from a cut-out photograph of one on
Wikimedia Commons, scaled by its height; the panels' side outline is drawn from photographs of its sides, whose angles
allow no more; the DualSense's outline and its controls were traced from a photograph of one from above (Commons),
scaled by its 160 mm.

The console: the glossy black core, the USB ports and the touch buttons on its front, the disc slot in its right side,
the light strips along its front edges; the white panels either side, their outer faces curving in to the waist and
out again, standing past the core at the top and bottom, the PlayStation mark near the top of each; the round stand.
The DualSense: white wings round the black middle, the white touchpad with the light bar along its sides, the d-pad,
the face buttons, the sticks, the PS button, the mute button.

One texture (ATLAS square, REGIONS): `front` (the core's front: x across, z down from its top), `panel` (a panel's
outer face: y across from the front, z down from the top), `pad` (the DualSense from above), `disc` (the disc's
label), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

HEIGHT, DEPTH, WIDTH = 390.0, 260.0, 104.0
STAND = dict(r=52.0, height=12.0, y=150.0)           # the round stand: the console stands on it
CORE = dict(half=36.0, y=(16.0, 244.0), z=(22.0, 370.0))   # the black core (z from the table): the panels rise
                                                            # past its top
# The panels' outer faces across the height (z above the console's foot, |x|), traced from the front; their thickness.
HOURGLASS = [(0.0, 51.0), (60.0, 48.5), (120.0, 45.6), (180.0, 43.8), (234.0, 43.0), (290.0, 44.6), (340.0, 48.4),
             (370.0, 51.6), (390.0, 55.0)]
PANEL = dict(thickness=6.0)
# A panel's side outline, (y, z above the console's foot), round from its top front.
OUTLINE = [(8.0, 390.0), (4.0, 350.0), (2.0, 290.0), (2.0, 190.0), (4.0, 110.0), (9.0, 40.0), (16.0, 8.0), (30.0, 0.0),
           (230.0, 2.0), (250.0, 10.0), (258.0, 40.0), (259.0, 330.0), (255.0, 360.0), (240.0, 374.0),
           (130.0, 382.0), (40.0, 388.0)]
LOGO = dict(y=48.0, z=352.0, size=26.0)              # the PlayStation mark on each panel, from the top front

SLOT = dict(x=28.0, z=(54.0, 182.0), width=3.0)      # the disc slot in the core's front, on its right
USB = dict(a=(0.0, 150.0), c=(0.0, 128.0), size=(13.0, 5.0))
BUTTONS = dict(power=(-14.0, 40.0), eject=(14.0, 40.0), size=(12.0, 2.4))
LIGHTS = dict(x=34.6, z=(30.0, 362.0), width=1.6)    # the light strips along the core's front edges

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2, out=88.0)    # out: how far in front of the console it waits

# The DualSense, from above (x across from its middle, y up from its grips' ends), traced from the photograph.
PAD_RIGHT = [(0.0, 105.8), (15.0, 105.4), (30.0, 104.3), (40.7, 104.8), (49.3, 104.2), (55.7, 102.4), (60.0, 99.4),
             (64.3, 94.3), (68.6, 86.8), (72.9, 75.8), (77.1, 58.8), (79.3, 44.0), (80.0, 30.0), (79.3, 17.5),
             (77.1, 9.0), (72.9, 5.3), (66.4, 2.9), (60.0, 0.4), (55.7, 3.8), (51.4, 12.9), (47.1, 24.3),
             (42.8, 36.7), (38.5, 41.9), (30.0, 42.1), (15.0, 41.4), (0.0, 41.4)]
PAD = dict(at=(-128.0, -112.0), turn=22.0, height=26.0)
DPAD = dict(at=(-47.8, 83.1), span=26.8, arm=8.6, height=2.4)
FACE = dict(triangle=(50.3, 93.4), circle=(62.3, 83.1), cross=(51.6, 72.9), square=(40.0, 83.1), r=5.0, height=2.6,
            press=1.6)
STICKS = dict(left=(-22.1, 66.3), right=(28.8, 66.3), housing=13.0, cap=9.8, height=(8.0, 13.0), tilt=16.0)
TOUCHPAD = dict(x=(-30.5, 32.4), y=(78.1, 104.6), r=6.0, height=1.0)
SMALL = dict(create=(-35.9, 98.3), options=(37.8, 98.3), size=(3.4, 6.4), ps=(2.5, 64.2), ps_r=4.6, mute=(2.5, 54.5),
             speaker=(2.0, 72.6))

COLOURS = dict(white="#F2F2F0", print="#FFFFFF")

REGIONS = dict(front=(0, 0, 160, 822), panel=(168, 0, 460, 690), pad=(636, 0, 388, 257), disc=(636, 265, 256, 256))
SWATCHES = dict(white=(660, 560), black=(692, 560), gloss=(724, 560), blue=(756, 560), light=(788, 560),
                grey=(820, 560), clear=(852, 560), stand=(884, 560), dark=(916, 560))

FPS = 30
LENGTH = 240                 # 8 s
