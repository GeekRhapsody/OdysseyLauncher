"""The Xbox 360's measurements, shared by xbox360_print.py (which draws its printing) and xbox360.py (which builds it).
Plain Python: Blender's Python imports it too.

The first Xbox 360 (2005) in white, lying flat with its hard drive on its left end, 309 mm wide, 258 deep and 83 high
(Microsoft's figures), and its wireless controller resting on its top, a made-up game, Odyssey, on the disc.
Millimetres: x from its middle (left to right), y back from the faceplate's front, z up from the table. The rest was
measured from Evan-Amos's photographs on Wikimedia Commons (the console from the front left and right and the back,
lying flat with its controller, standing with it), scaled by its width; the controller's outline traced from the drawing
of it on Commons, scaled by its 153 mm.

The console: its top and underside drawn in towards the middle (its sides' "inhale" when it stands), the vents along the
top's ends, XBOX 360 on the top; the grey grilles of its ends, the hard drive on the left one; the faceplate with the
tray (eject at its left, XBOX 360 at its right), the IR window, MEMORY UNIT A and B, the sync button, the power button
in the Ring of Light, the USB door. The controller: its outline, the left stick high and the d-pad low on the left, the
right stick low and A, B, X and Y on the right, the Guide button with its ring of light, BACK and START.

One texture (ATLAS square, REGIONS): `top` (the console from above), `front` (the faceplate: x across, z down from the
top), `pad` (the controller from above), `disc` (the disc's label), `grille` (an end's dots), and swatches. A region is
(x, y, width, height) in pixels."""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 309.0, 258.0, 83.0
INHALE = 4.0                     # how far the top and the underside are drawn in at the middle
FACEPLATE = 9.0                  # the faceplate's thickness, at the front
ROUND = dict(plan=10.0, ends=16.0, front=6.0)     # the corners: in plan, the ends' long edges, the front's edges
GRILLE = dict(bulge=4.0, inset=3.0)               # the ends' grilles: how far they bulge, how far in from the edges

HDD = dict(x=24.0, y=(22.0, 236.0), z=(10.0, 76.0), r=12.0)   # on the left end: how far out, its span, its corners
TRAY = dict(x=(-128.0, -8.0), z=(57.0, 68.0), travel=130.0, depth=150.0)   # its front on the faceplate; its bay
WELL = dict(y=62.0, r=61.0, depth=1.4)            # the disc's place on the tray, back from its front
EJECT = dict(at=(-140.0, 62.5), size=(12.0, 9.0))
IR = dict(at=(-140.0, 38.0), size=(14.0, 6.5))
MEMORY = dict(a=(-94.0, 31.0), b=(-44.0, 26.0), size=(42.0, 9.0))
SYNC = dict(at=(-10.0, 24.0), r=4.2)
POWER = dict(at=(52.0, 31.0), r=12.5, ring=(13.4, 18.0), recess=22.0, height=2.0)
USB_DOOR = dict(at=(122.0, 34.0), size=(14.0, 44.0))
DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)

# The controller, from above (x across from its middle, y up from its grips' ends), traced from the drawing.
PAD_RIGHT = [(0.0, 15.5), (12.0, 15.0), (24.0, 12.0), (36.5, 9.6), (40.3, 7.7), (43.9, 5.7), (47.5, 3.8), (51.8, 1.9),
             (58.5, 0.0), (65.3, 1.9), (69.7, 5.7), (72.2, 9.6), (74.4, 15.3), (76.1, 23.0), (76.5, 28.7),
             (76.1, 36.4), (75.3, 42.2), (74.0, 49.8), (72.6, 55.6), (70.8, 61.3), (68.3, 69.0), (65.4, 76.6),
             (62.0, 83.0), (57.0, 88.4), (50.0, 92.0), (26.0, 91.0), (0.0, 90.0)]
PAD = dict(at=(46.0, 96.0), turn=-14.0, height=26.0, grey=9.0)    # resting on the console's top; its lower shell
                                                                   # grey below `grey`
STICKS = dict(left=(-47.2, 44.9), right=(22.5, 21.7), housing=14.5, cap=11.0, height=(9.0, 14.0), tilt=16.0)
DPAD = dict(at=(-23.2, 24.1), r=14.6, height=2.4)
FACE = dict(a=(48.2, 41.4), b=(61.0, 53.6), x=(35.4, 52.0), y=(49.0, 64.3), r=5.8, height=3.0, press=1.8)
GUIDE = dict(at=(0.0, 52.0), r=7.0, ring=8.8)
SMALL = dict(back=(-16.7, 51.3), start=(18.2, 51.3), size=(6.0, 4.2))

COLOURS = dict(body="#ECEDEA", plate="#F4F4F1", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 618, 516), front=(0, 524, 618, 166), pad=(626, 0, 398, 240), disc=(626, 248, 256, 256),
               grille=(626, 512, 398, 128))
SWATCHES = dict(body=(904, 270), plate=(936, 270), grey=(968, 270), silver=(1000, 270), dark=(904, 302),
                green=(936, 302), green_dim=(968, 302), hdd=(1000, 302), chrome=(904, 334), shell=(936, 334))

FPS = 30
LENGTH = 240                 # 8 s
