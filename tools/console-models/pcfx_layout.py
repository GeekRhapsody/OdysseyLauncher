"""The PC-FX's measurements, shared by pcfx_print.py (which draws its printing) and pcfx.py (which builds it). Plain
Python: Blender's Python imports it too.

NEC's PC-FX (1994), a tower, 132 mm wide, 267 deep and 244 high (GameTechWiki's figures; the Computer History Museum's
9.5 x 5.25 x 10.5 inches agree), and its pad, a made-up game, Odyssey, on the CD. Millimetres: x from its middle (left
to right), y back from its front, z up from the table. The rest was measured from Evan-Amos's photographs on Wikimedia
Commons (straight on from the front, both sides and the back; from the front left with its CD lid shut and open), scaled
by its depth and height; the pad from his photograph of it from above, its width (about 168 mm) judged against the
console's in the photographs of the pair, as no source gives it.

The console: two pillars running up the front's sides, the recessed strip between them (NEC PC-FX, the badge, the POWER
and BUSY lights, the expansion door, the controller ports); the cap along the top (its front piece with the lid's
latch, the CD lid, the back piece with its louvres), the ribbed band under it; on each side a raised panel of vents,
three grooves near the back; its underside arched between its feet. Under the lid, the drive: the disc's well and the
spindle. The pad: its outline, the d-pad in its dish, NEC, the MODE 1 and MODE 2 switches, SELECT and RUN, buttons I to
VI in two rows.

One texture (ATLAS square, REGIONS): `side` (a side: y across from the front, z down from the top), `top` (the top
from above: x across, y down from the back), `front` (the front: x across, z down from the top), `drive` (the drive's
floor from above), `pad` (the pad from above), `disc` (the CD's label), and swatches. A region is (x, y, width,
height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 132.0, 267.0, 244.0
EDGE = 4.0                       # the body's edges' rounding
PILLARS = dict(inner=26.5, recess=6.0, top=188.0)   # the front's recessed strip: its half width, depth and top
CAP = 188.0                      # the cap's underside: the ribbed band under it
SEAMS = dict(front=35.0, back=170.0)                 # the cap's pieces: the front piece to y = 35, the lid to 170
LID = dict(thickness=12.0, inset=3.0, open=-102.0)   # its thickness, how far in from the sides; open: its pitch
DRIVE = dict(half=(62.0, 64.0), floor=8.0)           # the bay under the lid: half its width and length, its depth
SPINDLE = dict(y=103.0, r=7.5, height=4.0)
PANEL = dict(y=(47.0, 214.0), z=(10.0, 154.0), height=2.4)     # the sides' raised panels
ARCH = dict(y=(38.0, 229.0), rise=6.0)               # the underside's arch between the feet

# The front's printing and parts, (x, z).
LOGO = dict(at=(0.0, 172.0))
BADGE = dict(at=(0.0, 152.0), size=13.0)
LIGHTS = dict(power=(0.0, 138.0), busy=(0.0, 130.0), size=(2.4, 1.8))
DOOR = dict(z=(72.0, 124.0))
PORTS = dict(z=(14.0, 68.0), at=[(-6.0, 52.0), (-6.0, 30.0)], size=(15.0, 8.0))

DISC = dict(diameter=120.0, hole=15.0, thickness=1.2, above=70.0)

# The pad, from above (x across from its middle, y up from its lower edge's lowest points), traced from the photograph.
PAD_TOP = [(-83.6, 31.1), (-79.4, 50.1), (-75.2, 60.1), (-71.0, 65.7), (-66.9, 67.9), (-58.5, 69.7), (-50.1, 71.1),
           (-41.7, 72.5), (-33.3, 74.0), (-24.9, 74.8), (24.9, 74.8), (33.8, 74.4), (42.2, 73.3), (50.6, 72.1),
           (59.0, 70.6), (67.4, 68.6), (71.6, 65.7), (75.8, 59.2), (80.0, 48.8), (83.6, 31.1)]
PAD_BOTTOM = [(83.6, 20.2), (80.0, 11.9), (75.8, 7.5), (71.6, 4.8), (67.4, 3.3), (59.0, 2.1), (50.6, 1.5),
              (42.2, 0.8), (33.8, 0.4), (29.6, 1.0), (25.4, 4.9), (21.3, 7.4), (17.1, 8.4), (8.7, 9.1), (0.0, 9.4),
              (-8.1, 9.2), (-16.5, 8.5), (-20.7, 7.6), (-24.9, 5.4), (-29.1, 1.4), (-33.3, 0.2), (-41.7, 0.6),
              (-50.1, 1.2), (-58.5, 1.7), (-66.9, 2.8), (-71.0, 4.3), (-75.2, 6.8), (-79.4, 11.0), (-83.6, 20.2)]
PAD = dict(height=22.0, at=(-104.0, -96.0), turn=16.0)
DPAD = dict(at=(-52.6, 36.2), dish=16.7, span=29.0, arm=11.0, height=2.4, tilt=9.0)
BUTTONS = dict(I=(68.2, 36.5), II=(53.6, 32.1), III=(39.8, 25.5), IV=(33.9, 40.8), V=(47.9, 46.9), VI=(62.3, 51.5),
               r=6.0, height=2.6, press=1.6)
SWITCHES = dict(mode_1=(-0.6, 46.5), mode_2=(-0.6, 34.9), size=(8.2, 3.6))
SMALL = dict(select=(-7.5, 21.0), run=(6.2, 21.0), size=(10.2, 3.6))

COLOURS = dict(body="#DCDCDA", print="#FFFFFF")

REGIONS = dict(side=(0, 0, 512, 468), top=(520, 0, 240, 486), front=(768, 0, 256, 474), pad=(0, 476, 512, 225),
               drive=(520, 494, 240, 240), disc=(768, 482, 256, 256))
SWATCHES = dict(body=(40, 740), light=(72, 740), grey=(104, 740), dark=(136, 740), green=(168, 740), amber=(200, 740),
                key=(232, 740), black=(264, 740))

FPS = 30
LENGTH = 240                 # 8 s
