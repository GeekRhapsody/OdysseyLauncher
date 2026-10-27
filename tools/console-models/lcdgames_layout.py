"""The LCD games card's measurements, shared by lcdgames_print.py (which draws its printing and screens) and lcdgames.py
(which builds it). Plain Python: Blender's Python imports it too.

A dedicated LCD handheld in the classic shell of the late 1980s and 1990s (Tiger's, unbranded here): about 127 x 102 x
19 mm (a reissue's listing and a photograph against its blister card), its parts placed from a photograph of its face
square on. Millimetres in handheld.py's frame: x from its middle (left to right), z up from its bottom edge, y back from
its face.

Its face: the white rim round the printed art panel (PANEL: under clear plastic, its lower corners cut away towards the
D-pad and the buttons; a made-up game's painting and logo), the LCD in it (LCD: black segment figures over a printed
backdrop); the strip of small buttons under it (OFF, SOUND, PAUSE, ON/START, the ACL pinhole); the D-pad's cross on its
blue boss at the lower left, the two action bars on theirs at the lower right; the speaker's grille between them.

Two textures: the print (ATLAS square, REGIONS: `face` from the front, and swatches) and the screens (MEDIA_REGIONS:
the LCD's segment figures switched on in turn over its backdrop). A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 127.0, 102.0, 19.0
CORNER = 8.0
SPAN = (-WIDTH / 2, WIDTH / 2, 0.0, HEIGHT)
PANEL = [(-54.5, 97.0), (-54.5, 50.0), (-43.0, 39.0), (43.0, 39.0), (54.5, 50.0), (54.5, 97.0)]
LCD = dict(size=(53.0, 36.0), at=(0.0, 58.0))
STRIP = dict(z=28.0, x=(-24.0, 24.0), height=9.0)
SMALL = dict(names=[("OFF", -17.5), ("SOUND", -8.5), ("PAUSE", 1.5), ("ON/START", 10.5)], acl=18.5, size=(8.0, 4.0))
BOSSES = dict(left=(-43.5, 21.0), right=(43.5, 21.0), r=15.0, height=2.0)
CROSS = dict(arm=11.0, half=4.0)
BARS = dict(size=(17.0, 5.0), gap=9.0, slant=-12.0)
GRILLE = dict(at=(0.0, 9.0), size=(40.0, 12.0), slots=5)

MADE_UP = ("Redline Riviera (Europe)", "megadrive")
LANES = 3

COLOURS = dict(shell="#E0E0E0", boss="#396DAF", red="#B3382F", grey="#979295", strip="#246042", lcd="#A9AE9A",
               segment="#16181A", ink="#1E1E22", white="#F4F4F2")

REGIONS = dict(face=(0, 0, 1016, 816))
SWATCHES = {name: (40 + 32 * k, 860) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(seg1=(0, 0, 424, 288), seg2=(432, 0, 424, 288), seg3=(0, 296, 424, 288),
                     seg4=(432, 296, 424, 288))

FPS = 30
LENGTH = 240                 # 8 s
