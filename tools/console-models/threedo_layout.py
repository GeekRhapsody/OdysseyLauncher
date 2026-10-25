"""The Panasonic FZ-1's measurements, shared by threedo_print.py (which draws its printing) and threedo.py (which builds
it). Plain Python: Blender's Python imports it too.

The FZ-1 R.E.A.L. 3DO Interactive Multiplayer (1993), 279 x 267 x 78 mm (the Computer History Museum's record, with a
listing's 77 mm height), and its FZ-JP1X controller. Millimetres: x from the console's middle (left to right), y back
from its front (the front pods' front), z up from the table. The rest was measured from Evan-Amos's photographs on
Wikimedia Commons (the console from each corner and with its controller) and a collector's views of it from above,
underneath and opened (the-liberator.net), scaled by its width.

The console: a body standing on a fluted pod at each corner, the pods standing proud of its front and sides; on its
top a raised plate, its corners cut round the pods, Panasonic embossed on it over R.E.A.L. 3DO INTERACTIVE MULTIPLAYER;
in its front, between the front pods, the disc tray's door (Panasonic in gold) over the strip with READY and the 3DO
mark, R.E.A.L. FZ-1, ACCESS, the compact disc mark and the CONTROLLER port; POWER on the front left pod and OPEN/CLOSE
on the front right, bronze tabs round them; vents down its right side. The controller lies in front of its left end.

Two textures. `print` (ATLAS square, REGIONS): `top` (the console seen from above: the plate's embossing; planar-mapped
onto every face facing up), `front` (the face between the front pods, seen from in front: the door, the strip), `pad`
(the controller's top), and swatches. `disc` (DISC_ATLAS): the CD's label side (a made-up game, Odyssey) and its
shiny side. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024
DISC_ATLAS = 512

WIDTH, DEPTH, HEIGHT = 279.0, 267.0, 78.0
POD = dict(r=33.0, top=70.0, flutes=36, flute=1.1)          # the pods' radius and top; their flutes' count and depth
PODS = [(sx * (WIDTH / 2 - 33.0), y) for y in (33.0, DEPTH - 33.0) for sx in (-1, 1)]
BODY = dict(x=130.0, y=(14.0, DEPTH - 8.0), z=(7.0, 70.0), r=6.0)   # between the pods: its half width, y, z, rounding
PLATE = dict(x=(-118.0, 118.0), y=(22.0, 252.0), top=HEIGHT, r=16.0, gap=4.0)  # the raised plate; its gap round a pod
FRONT_Y = BODY["y"][0]                                       # the face between the front pods
FRONT = dict(x=(-73.5, 73.5), z=(BODY["z"][0], BODY["z"][1]))
DOOR = dict(x=(-62.0, 62.0), z=(40.0, 62.0), out=1.6, pocket=24.0)
# The tray behind the door: its plate's x, depth and z; the disc's well (its middle, back from the door, and its
# radius); how far it slides out.
TRAY = dict(x=(-61.0, 61.0), depth=140.0, z=(43.0, 48.0), well=(66.0, 60.5), travel=132.0)
# POWER and OPEN/CLOSE: each a tab round a front pod (0 the left, 1 the right) at z; their height, the arc they cover
# (degrees round the pod, 270 facing the front) and how far they stand out.
TABS = dict(power=(0, 50.0), open=(1, 50.0), height=6.5, arc=(240.0, 300.0), out=2.2)
LIGHTS = dict(ready=(-62.0, 33.0), access=(62.0, 33.0), size=(5.0, 1.6))   # x, z on the front face
VENTS = dict(y=[60.0 + 7.0 * k for k in range(22)], z=(22.0, 58.0), width=2.4, depth=3.0)   # down the right side

DISC = dict(r=60.0, hole=7.5, thickness=1.2)

# The controller: a dog-bone, two round lobes joined by its body; it lies at PAD["at"], turned PAD["turn"] degrees.
PAD = dict(at=(-212.0, -20.0), turn=12.0, thickness=26.0, lobes=((-47.0, 0.0, 35.0), (47.0, 2.0, 36.0)),
           waist=(-17.0, 24.0), size=(166.0, 76.0),
           dpad=(-47.0, 0.0, 26.0, 8.6), dish=17.5, abc=[(33.0, -12.0), (48.0, 2.0), (63.0, 16.0)], abc_r=6.0,
           stop=(-9.0, 4.0), play=(9.0, 4.0), small=(8.0, 3.6), logo=(0.0, 21.0))

COLOURS = dict(case="#28282C", dark="#0E0E10", controller="#2D2D31", disc="#FFFFFF")

REGIONS = dict(top=(0, 0, 560, 536), front=(568, 0, 456, 216), pad=(568, 224, 456, 210))
SWATCHES = dict(bronze=(16, 560), beige=(48, 560), green=(80, 560), amber=(112, 560), dark=(144, 560),
                plate=(176, 560), green_off=(208, 560), amber_off=(240, 560))
DISC_REGIONS = dict(label=(0, 0, 256, 256), data=(256, 0, 256, 256))

FPS = 30
LENGTH = 240                 # 8 s
