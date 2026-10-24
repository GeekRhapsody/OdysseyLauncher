"""The Nintendo DS family's measurements, shared by nintendo_ds_print.py (which draws their printing and screens) and
nintendo_ds.py (which builds them). Plain Python: Blender's Python imports it too.

`nds`: the DS Lite in Polar White, 133 x 73.9 x 21.5 mm closed; `n3ds`: the first 3DS in Aqua Blue, 134 x 74 x 21 mm,
its upper half's face black, the Circle Pad over its D-pad, SELECT, HOME and START under its touch screen, the inner
camera over its wide 3D screen. Millimetres: x from its middle (left to right), y back from the lower half's front edge,
z up from the table, with the console open on the table. The rest was measured from photographs on Wikimedia Commons
(Evan-Amos's three-quarter views, of the DS Lite with its stylus and of the 3DS; views of a white DS Lite from above and
behind), scaled by its width.

The lower half lies flat: the touch screen in its middle, the D-pad on its left, A, B, X and Y on its right, START and
SELECT under them, the hinge along its back edge, slot-1 for the game card in its back face under the hinge, and the
stylus's silo at its back right. The upper half is hinged OPEN degrees up from flat, its screen between two speakers.
Each half is its plan's outline, CORNER at the corners, lofted up through EDGE's rounding over its top and bottom edges.

Two textures. `print` (ATLAS square, PRINT_REGIONS): `lower` (the lower half's face seen from above: the screen's bezel,
the legends, the buttons' wells and tops), `upper` (the upper half's face, seen square on with the hinge at the bottom:
the screen's bezel, the speakers), and swatches. `media` (each kind's `media` regions): the screens at the console's own
pixels, a texel each (the start-up screen or menu on both, then the game's title on the upper and TOUCH TO START on the
lower, and that button pressed), and the game card's label.
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
        colour="#F2F2F0", accent="#C9CBCF", dark="#1C1C1E", face_colour="#F2F2F0", upper_colour="#F2F2F0", legend="#7C7E82",
        name="NINTENDO DS", speaker_dots=[(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)],
        screen_px=((256, 192), (256, 192)),       # the upper screen's pixels, the lower's
        media=dict(boot_upper=(8, 8, 256, 192), boot_lower=(272, 8, 256, 192), game_upper=(536, 8, 256, 192),
                   game_lower=(8, 208, 256, 192), game_pressed=(272, 208, 256, 192), card=(536, 208, 280, 264)),
    ),
    "n3ds": dict(
        width=134.0, depth=74.0, lower=11.0, upper=10.0, corner=7.0, edge=2.0,
        open=60.0,
        hinge=dict(y=69.5, z=12.5, r=5.5, x=58.0),
        screen=dict(x=0.0, y=40.0, size=(61.4, 46.0), bezel=(74.0, 60.0, 2.5)),
        panel=dict(y=36.0, size=(78.0, 70.0, 3.0), height=0.8),   # the raised panel holding it, the buttons' strip under it
        upper_screen=dict(y=36.0, size=(76.8, 46.1), bezel=(80.0, 50.0, 1.0)),
        speakers=[(-52.0, 36.0), (52.0, 36.0)],
        camera=(0.0, 66.0, 1.8),
        circle_pad=dict(x=-49.0, y=52.0, r=7.2, well=9.4),
        dpad=dict(x=-49.0, y=27.0, arm=(17.0, 5.6), height=1.5),
        face=dict(x=48.0, y=35.0, reach=6.8, r=3.4, height=1.3),
        small=[("power", 46.0, 11.0, 2.4)],
        strip=["SELECT", "HOME", "START"],                     # printed under the touch screen
        slot=dict(x=(-19.0, 19.0), z=(2.0, 6.5)),
        stylus=dict(x=-59.0, z=5.5, r=2.0, length=80.0),
        colour="#2C9AC6", accent="#2789B4", dark="#1A1B1D", face_colour="#2C9AC6", upper_colour="#1C1D20", legend="#E6F3FA", pad="#B9B8CC",
        name="NINTENDO 3DS", speaker_dots=[(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
        screen_px=((400, 240), (320, 240)),
        media=dict(boot_upper=(8, 8, 400, 240), boot_lower=(416, 8, 320, 240), game_upper=(8, 256, 400, 240),
                   game_lower=(416, 256, 320, 240), game_pressed=(8, 504, 320, 240), card=(744, 8, 270, 255)),
    ),
}

CARD = dict(width=35.0, length=33.0, thickness=3.8)

PRINT_REGIONS = dict(lower=(0, 0, 1024, 570), upper=(0, 580, 1024, 444))
SWATCHES = dict(dark=(16, 1012), accent=(48, 1012), card=(80, 1012), pad=(112, 1012))  # 24 x 24 blocks' middles

SCREENS = ["boot_upper", "boot_lower", "game_upper", "game_lower", "game_pressed"]

FPS = 30
LENGTH = 240                 # 8 s
