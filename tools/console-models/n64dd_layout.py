"""The 64DD card's measurements, shared by n64dd_print.py (which draws the drive's printing and the disk's label) and
n64dd.py (which builds it). Plain Python: Blender's Python imports it too.

The Nintendo 64 standing on its 64DD (1999), the magnetic disk drive that plugs into the console's underside, with the
N64's controller in front: the console and the controller are n64.py's own. The drive has the console's footprint and
its corner pods, about 46 mm high (no source gives its size: its pods are as tall as the console's in Evan-Amos's
photographs of the pair on Wikimedia Commons, which the rest was measured from), the disk's slot and EJECT in its front;
the disk is a made-up game, Odyssey. Millimetres: x from the middle (left to right), y back from the console's front,
z up from the table.

One texture of its own (ATLAS square, REGIONS): `front` (the drive's front: x across, z down from its top), `disk`
(the disk's top: its label), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 512

HEIGHT = 46.0                    # the drive: the console stands on it
FOOT = 3.0
BASE = dict(front=10.0, back=188.0, x=126.0, r=16.0)          # its plan, like the console's base but a little larger
PODS = dict(front=(104.0, 22.0, 28.0, 24.0), back=(104.0, 166.0, 26.0, 22.0))   # x, y, rx, ry: full height
RECESS = dict(x=(-74.0, 72.0), z=(6.0, 36.0), depth=6.0)       # the panel sunk into its front, between the pods
SLOT = dict(x=(-62.0, 44.0), z=(15.0, 26.0))                   # the disk's slot in the panel
EJECT = dict(at=(58.0, 16.0), r=5.5, press=2.0)

DISK = dict(size=(102.0, 104.0, 9.0), out=118.0, label=(70.0, 52.0))   # w, d, t; how far out it waits

REGIONS = dict(front=(0, 0, 512, 92), disk=(0, 100, 256, 264))
SWATCHES = dict(case=(300, 120), dark=(332, 120), disk=(364, 120), button=(396, 120))
COLOURS = dict(case="#38383B", disk="#8A8B8E")

FPS = 30
LENGTH = 240                 # 8 s
