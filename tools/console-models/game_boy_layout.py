"""The Game Boys' measurements, shared by game_boy_print.py (which draws their printing) and game_boy.py (which builds
them). Plain Python: Blender's Python imports it too.

Three handhelds, one per system: `gb` (the original grey Game Boy, DMG-01), `gbc` (a teal Game Boy Color) and `gba`
(an indigo Game Boy Advance). Millimetres, seen from the front: x from the middle (left to right), z up from the
bottom; the front is at y = -DEPTH / 2.

Each has one ATLAS x ATLAS print texture of named regions, each a face's planar projection: `front` (the body's front:
its colour, the screen's surround, the screen switched off, the legends, the buttons' wells), `cart` and `cart_rear`
(the cartridge's label side and its other side, each as seen looking at it), `screen` (the screen switched on, or the
DMG's Nintendo logo on its switched-off screen) and `led` (the power light lit, on the surround round it). A region is
(x, y, width, height) in pixels, and the box of millimetres it covers, (x0, x1, z0, z1): a little more than its face,
so filtering never reaches the next region.

A bezel is the screen's surround (the GBC's and GBA's lens): its x and z extents, its corners' radii (bottom right,
top right, top left, bottom left) and, for the GBA, how far its bottom bows down in the middle (bulge). A cartridge
sits in the slot centred at depth y, its top `protrudes` above the console's top; `dmg` is the Game Boy cartridge's
shape (its top corner cut, seen from the label side at the top right), `agb` the Game Boy Advance's.
"""

ATLAS = 1024


def region(px, mm):
    return dict(px=px, mm=mm)


MODELS = {
    "gb": dict(
        name="Game Boy",
        width=90.0, height=148.0, depth=30.0,
        corners=[20.0, 2.5, 2.5, 3.5],         # bottom right, top right, top left, bottom left
        front_round=(1.0, 1.0), back_round=(2.5, 3.0),
        colours=dict(case="#C2C0B8", dark="#202024", ab="#9C1B57", rubber="#8C8B93", cart="#8E8D93"),
        bezel=dict(x=(-38.5, 38.5), z=(84.0, 137.5), radii=[15.0, 3.5, 3.5, 3.5], colour="#5F6070"),
        screen=dict(x=(-20.5, 26.5), z=(88.0, 130.0), colour="#9DAA5E"),
        led=(-31.0, 116.0),
        dpad=(-24.0, 56.0, 24.0, 8.0),           # centre, arm length and width
        buttons=[("B", 13.5, 50.5, 5.0), ("A", 31.5, 59.0, 5.0)],
        pills=[("SELECT", -14.5, 30.0), ("START", 1.5, 30.0)],
        pill=(11.0, 3.6, 25.0),                   # length, width, degrees
        slot=dict(x=(-30.0, 30.0), y=(2.0, 11.0)),
        cart=dict(width=57.0, height=65.0, thickness=8.0, kind="dmg", protrudes=6.0, y=6.5),
        regions=dict(
            front=region((0, 0, 600, 980), (-46.0, 46.0, -1.0, 149.0)),
            cart=region((608, 0, 416, 472), (-29.5, 29.5, -1.0, 66.0)),
            cart_rear=region((608, 480, 416, 472), (-29.5, 29.5, -1.0, 66.0)),
            screen=region((608, 960, 300, 60), (-12.5, 12.5, -2.5, 2.5)),
            led=region((916, 960, 60, 60), (-2.5, 2.5, -2.5, 2.5)),
        ),
    ),
    "gbc": dict(
        name="Game Boy Color",
        width=78.0, height=133.0, depth=27.0,
        corners=[13.0, 5.0, 5.0, 13.0],
        front_round=(1.5, 1.5), back_round=(3.0, 3.5),
        colours=dict(case="#14889A", dark="#26262C", rubber="#3F4048", cart="#222226"),
        bezel=dict(x=(-33.0, 33.0), z=(69.0, 128.0), radii=[9.0, 3.5, 3.5, 9.0], colour="#16161A"),
        screen=dict(x=(-19.5, 24.5), z=(84.0, 124.0), colour="#7E857A"),
        led=(-27.0, 112.5),
        dpad=(-21.0, 46.0, 21.0, 7.5),
        buttons=[("B", 12.0, 41.5, 4.4), ("A", 26.0, 46.5, 4.4)],
        pills=[("SELECT", -8.0, 22.5), ("START", 4.5, 22.5)],
        pill=(8.0, 3.2, 0.0),
        slot=dict(x=(-30.0, 30.0), y=(1.0, 10.0)),
        cart=dict(width=57.0, height=65.0, thickness=8.0, kind="dmg", protrudes=12.0, y=5.5),
        regions=dict(
            front=region((0, 0, 600, 1012), (-40.0, 40.0, -1.0, 134.0)),
            cart=region((608, 0, 300, 340), (-29.5, 29.5, -1.0, 66.0)),
            cart_rear=region((608, 348, 300, 340), (-29.5, 29.5, -1.0, 66.0)),
            screen=region((608, 700, 264, 240), (-22.0, 22.0, -20.0, 20.0)),
            led=region((880, 700, 60, 60), (-2.5, 2.5, -2.5, 2.5)),
        ),
    ),
    "gba": dict(
        name="Game Boy Advance",
        width=144.5, height=82.0, depth=24.5,
        corners=[26.0, 16.0, 16.0, 26.0],
        front_round=(2.0, 2.0), back_round=(3.0, 4.0),
        colours=dict(case="#4B44A6", light="#C9CAD6", dark="#1E1E24", cart="#5C5E66"),
        bezel=dict(x=(-43.0, 43.0), z=(19.0, 73.5), radii=[8.0, 4.0, 4.0, 8.0], colour="#1E1E24", bulge=2.0),
        screen=dict(x=(-30.5, 30.5), z=(30.0, 70.8), colour="#5E655E"),
        led=(52.0, 62.5),
        dpad=(-55.0, 51.0, 21.0, 7.0),
        buttons=[("B", 49.0, 40.0, 5.0), ("A", 62.0, 45.0, 5.0)],
        small_buttons=[("START", -47.5, 35.0), ("SELECT", -47.5, 27.5)],
        slot=dict(x=(-30.5, 30.5), y=(0.0, 8.0)),
        cart=dict(width=57.5, height=35.0, thickness=7.0, kind="agb", protrudes=11.0, y=4.0),
        regions=dict(
            front=region((0, 0, 1024, 585), (-73.5, 73.5, -1.0, 83.0)),
            cart=region((0, 593, 330, 204), (-30.0, 30.0, -1.0, 36.0)),
            cart_rear=region((0, 805, 330, 204), (-30.0, 30.0, -1.0, 36.0)),
            screen=region((338, 593, 420, 282), (-30.5, 30.5, -20.4, 20.4)),
            led=region((766, 593, 60, 60), (-2.5, 2.5, -2.5, 2.5)),
        ),
    ),
}
