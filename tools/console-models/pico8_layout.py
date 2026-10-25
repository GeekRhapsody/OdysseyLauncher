"""PICO-8's cartridge, made solid: the measurements shared by pico8_print.py (which draws its printing and screens) and
pico8.py (which builds it). Plain Python: Blender's Python imports it too.

PICO-8 is a fantasy console: it has no hardware, and the face it shows the world is its cartridge, the 160 x 205
pixel .p8.png image every game is saved as (the grey cartridge, PICO-8 and WWW.PICO-8.COM along its top, the 128 x 128
label, the title and author in the dark box under it, PICO-8 CARTRIDGE). The card is that cartridge made solid, a
cartridge pixel PX millimetres, standing on its bottom edge, its corners cut in pixel steps as the image's are (the
bottom right cut away diagonally), its label a screen. The layout follows Lexaloffle's cartridge images (Celeste's,
from the PICO-8 BBS); the palette and the PICO-8 logo follow the PICO-8 manual and the logo on Wikimedia Commons.

Millimetres: x across the cartridge's face (left to right), y through it (its front at y = 0, facing -y), z up from
the table. Cartridge pixels: (u, v), u to the right and v down from its top-left corner.

Two textures. `print` (ATLAS square, PRINT_REGIONS): `front` (the face, FRONT_PX pixels a cartridge pixel), `back`,
and swatches. `media` (MEDIA_REGIONS): the label's screens, each 128 x 128 PICO-8 pixels drawn SCREEN_PX a pixel
(`label`, the cartridge's label at rest; `noise`, booting; `boot`, the PICO-8 logo; `game1` and `game2`, a made-up
game, Odyssey, playing). A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

CART_PX = (160, 205)         # the cartridge image's size, in its pixels
PX = 0.4                     # millimetres a cartridge pixel
WIDTH, HEIGHT = CART_PX[0] * PX, CART_PX[1] * PX
THICKNESS = 12.0
STEP = 4                     # the corners' steps, in cartridge pixels
CORNERS = dict(top_left=3, top_right=3, bottom_left=3, chamfer=5)   # steps cut at each corner; the bottom right's diagonal

LABEL = (16, 24, 128, 128)   # the label's window: u, v, width, height
TEXT_BOX = (15, 163, 130, 32)
SEAM = 0.6                   # the groove round the edges, between the two halves

PALETTE = ["#000000", "#1D2B53", "#7E2553", "#008751", "#AB5236", "#5F574F", "#C2C3C7", "#FFF1E8",
           "#FF004D", "#FFA300", "#FFEC27", "#00E436", "#29ADFF", "#83769C", "#FF77A8", "#FFCCAA"]
COLOURS = dict(body="#646464", box="#343434", edge="#555555", seam="#2A2A2A")

# PICO-8's logo, a cell a pixel: palette indices (hex digits), '.' see-through. The sparkle over the 8, the letters
# and their dark blue shadow.
LOGO = ["..................................8.....",
        ".................................97f....",
        "................................a777e...",
        ".................................b7d....",
        "...7777.7777..777..7777.....7777..c.....",
        "..771771.771177111771771....71171.......",
        "..777771.771.771..77177177.777771.......",
        "..771111.771.771..771771.11771171.......",
        "..771...7777.7777.777711...777771.......",
        "...11....1111.1111.1111.....11111......."]

FRONT_PX = 4
PRINT_REGIONS = dict(front=(0, 0) + (CART_PX[0] * FRONT_PX, CART_PX[1] * FRONT_PX),
                     back=(648, 0, CART_PX[0] * 2, CART_PX[1] * 2))
PRINT_SWATCHES = dict(edge=(680, 440), seam=(712, 440))

SCREEN_PX = 2
MEDIA_REGIONS = {name: ((k % 4) * 256, (k // 4) * 256, 256, 256)
                 for k, name in enumerate(("label", "noise", "boot", "game1", "game2"))}

FPS = 30
LENGTH = 240                 # 8 s
