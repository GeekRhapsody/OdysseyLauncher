"""The Nintendo DS family's measurements, shared by nintendo_ds_print.py (which draws their printing and screens) and
nintendo_ds.py (which builds them). Plain Python: Blender's Python imports it too.

`nds`: the DS Lite in Polar White, 133 x 73.9 x 21.5 mm closed. Millimetres: x from its middle (left to right), y back
from the lower half's front edge, z up from the table, with the console open on the table. The rest was measured from
photographs on Wikimedia Commons (Evan-Amos's three-quarter view with the stylus, views of a white one from above and
behind), scaled by its width.

The lower half lies flat: the touch screen in its middle, the D-pad on its left, A, B, X and Y on its right, START and
SELECT under them, the hinge along its back edge, slot-1 for the game card in its back face under the hinge, and the
stylus's silo at its back right. The upper half is hinged OPEN degrees up from flat, its screen between two speakers.
Each half is its plan's outline, CORNER at the corners, lofted up through EDGE's rounding over its top and bottom edges.

Two textures. `print` (ATLAS square, PRINT_REGIONS): `lower` (the lower half's face seen from above: the screen's bezel,
the legends, the buttons' wells and tops), `upper` (the upper half's face, seen square on with the hinge at the bottom:
the screen's bezel, the speakers), and swatches. `media` (MEDIA_REGIONS): the screens at the DS's 256 x 192 pixels, a
texel each (the start-up screen on both, then the game's title on the upper and TOUCH TO START on the lower, and that
button pressed), and the game card's label.
"""

ATLAS = 1024

KINDS = {
    "nds": dict(
        width=133.0, depth=73.9, lower=10.5, upper=9.0, corner=8.0, edge=1.8,
        open=58.0,                                     # degrees the upper half is tipped up from flat
        hinge=dict(y=70.0, z=12.0, r=5.0, x=55.0),     # its axis (y, z) and radius; it runs x either side of the middle
        screen=dict(x=0.0, y=35.0, size=(62.0, 46.5), bezel=(70.0, 53.0, 2.0)),   # the touch screen: middle, sizes
        upper_screen=dict(y=37.0, size=(62.0, 46.5), bezel=(70.0, 53.0, 2.0)),    # its middle from the hinge's edge
        speakers=[(-50.0, 37.0), (50.0, 37.0)],
        dpad=dict(x=-48.5, y=40.0, arm=(18.5, 6.4), height=1.6),
        face=dict(x=48.5, y=40.0, reach=6.6, r=3.3, height=1.4),
        small=[("start", 46.0, 23.0, 1.9), ("select", 41.0, 16.5, 1.9)],
        slot=dict(x=(-19.0, 19.0), z=(2.0, 6.5)),       # slot-1 in the back face
        stylus=dict(x=58.0, z=5.0, r=2.2, length=87.5),  # its silo's middle in the back face, its size
        colour="#F2F2F0", accent="#C9CBCF", dark="#1C1C1E",
        name="Nintendo DS lite",
    ),
}

CARD = dict(width=35.0, length=33.0, thickness=3.8)

PRINT_REGIONS = dict(lower=(0, 0, 1024, 570), upper=(0, 580, 1024, 444))
SWATCHES = dict(dark=(16, 1012), accent=(48, 1012), card=(80, 1012))   # each a 24 x 24 block's middle

SCREEN_PX = (256, 192)
SCREENS = ["boot_upper", "boot_lower", "game_upper", "game_lower", "game_pressed"]
MEDIA_REGIONS = dict(boot_upper=(8, 8, 256, 192), boot_lower=(272, 8, 256, 192), game_upper=(536, 8, 256, 192),
                     game_lower=(8, 208, 256, 192), game_pressed=(272, 208, 256, 192), card=(536, 208, 280, 264))

FPS = 30
LENGTH = 240                 # 8 s
