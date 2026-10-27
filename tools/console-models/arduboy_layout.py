"""The Arduboy card's measurements, shared by arduboy_print.py (which draws its printing and screens) and arduboy.py
(which builds it). Plain Python: Blender's Python imports it too.

The Arduboy (2016), credit-card sized: 54 x 85 x 5.5 mm, its parts placed from a photograph of its face square on
(0.0416 mm a pixel); its OLED 128 x 64, white on black. Millimetres in handheld.py's frame: x from its middle (left to
right), z up from its bottom edge, y back from its face.

A stack (LAYERS): the clear front plate, the white board under it, the brushed aluminium back. The theme's materials have
no transparency, so the plate is drawn as it looks from the front: the board and its parts printed on its face (the
gold ARDUBOY, the chips, the traces), its grey-green only in its edge. On the board: the OLED's black glass and the screen
in it (OLED), the four black D-pad keys (DPAD), A and B in red (BUTTONS), the power slide on the top edge, four brass
screws at the corners.

Two textures: the print (ATLAS square, REGIONS: `face` from the front, `back` from behind, and swatches) and the screens
(MEDIA_REGIONS: the start-up logo, a made-up game's title and two moments of it, white on black). A region
is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 54.0, 85.0, 5.5
CORNER = 3.0
LAYERS = dict(plate=2.2, board=4.6)                        # where the plate and the board end, back from the face
SPAN = (-WIDTH / 2, WIDTH / 2, 0.0, HEIGHT)
OLED = dict(glass=(35.0, 22.0), at=(0.0, 67.5), screen=(29.4, 14.7), pixels=(128, 64))
DPAD = dict(at=(-13.0, 33.0), key=9.0, pitch=7.6)
BUTTONS = dict(a=(8.5, 30.0), b=(18.0, 37.0), r=4.5)
SCREWS = [(-22.0, 5.0), (22.0, 5.0), (-22.0, 80.0), (22.0, 80.0)]
SWITCH = dict(at=(-13.5, 2.6), size=(5.0, 2.2, 2.0), travel=2.6)   # x, y on the top edge; its knob

PALETTE = ["#101110", "#E8F0FF"]
MADE_UP = ("Deep Fathom (Europe)", "megadrive")

COLOURS = dict(board="#E4ECEA", plate="#A4AA98", black="#0D0D0D", red="#F2382D", gold="#C9A76B", brass="#AA7A26",
               chip="#1A1A1A", aluminium="#CDCECA", glass="#1F252B")

REGIONS = dict(face=(0, 0, 432, 680), back=(440, 0, 162, 255))
SWATCHES = {name: (456 + 32 * (k % 9), 280 + 32 * (k // 9)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(boot=(0, 0, 384, 192), title=(392, 0, 384, 192), game1=(0, 200, 384, 192),
                     game2=(392, 200, 384, 192))

FPS = 30
LENGTH = 240                 # 8 s
