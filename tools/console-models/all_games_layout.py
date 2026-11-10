"""The All games card's measurements and its art's layout, shared by all_games_print.py (which packs the boxes' art) and
all_games.py (which builds the pile). Plain Python: Blender's Python imports it too.

All games has no hardware, so its card is an untidy pile of game boxes: made-up games from tools/made-up-games's library
(their covers, backs and spines; no real game's art), three Mega Drive cases, three Super Nintendo boxes, two Nintendo
64 boxes, a PS2 case, a PSP case, and a PlayStation and a Dreamcast jewel case, each the base theme's own template for
its system (memory-card's megadrive_clamshell, snes_box_horizontal, generic_box_top (the N64's), ps2_clamshell,
psp_clamshell, psx_jewel_case and dreamcast_jewel_case), at its real size. Millimetres: x across (left to right), y back
from the pile's middle, z up from the table.

The pile (BOXES): five boxes stacked flat, each turned against the one under it, the two Mega Drive cases on top; an N64
box leaning back against its right side, its cover out to the right; a Mega Drive case and a Super Nintendo box on the
table in front of it and at its left; and two more in front, each a smaller case on the front half of a bigger one: the
Dreamcast case on the PSP case at the front left, the PlayStation case on the PS2 case at the front right. Each box: its
system and game (the library's file name), its lean (pitch, degrees about x: -90 lies it on its back, cover up; 0 stands
it up; a little less than 0 leans it back), its turn about the vertical (yaw, degrees), and where it goes: the middle of
its footprint (x, y) and its underside (z).

The art is two textures (ATLAS_SIZE, JPEG: it's painted art): `art`, every box's cover and spine, and `backs`, every
box's back, each image at SCALE of the library's size, packed in shelves (REGIONS, computed by regions()). At most 1024
pixels on a side, as the launcher draws no texture larger. A region is (x, y, width, height) in pixels.
"""

FPS = 30
LENGTH = 150                 # 5 s

# The templates: the file in memory-card's models/templates/, and its largest side in millimetres (the spec fits it to
# 1 m): the Mega Drive case's height with its hanger tab; the boxes' width.
TEMPLATES = dict(megadrive=("megadrive_clamshell.glb", 205.4), snes=("snes_box_horizontal.glb", 190.0),
                 n64=("generic_box_top.glb", 190.0), ps2=("ps2_clamshell.glb", 190.0), psp=("psp_clamshell.glb", 180.0),
                 psx=("psx_jewel_case.glb", 140.43), dreamcast=("dreamcast_jewel_case.glb", 142.0))

# The library's image sizes, per system: cover, back, spine.
ART = dict(megadrive=dict(cover=(968, 1360), back=(962, 1360), spine=(192, 1360)),
           snes=dict(cover=(1360, 994), back=(1360, 994), spine=(1360, 194)),
           n64=dict(cover=(1360, 994), back=(1360, 994), spine=(1360, 194)),
           ps2=dict(cover=(972, 1360), back=(966, 1360), spine=(110, 1360)),
           psp=dict(cover=(796, 1360), back=(796, 1360), spine=(118, 1360)),
           psx=dict(cover=(1360, 1360), back=(1530, 1360), spine=(130, 1360)),
           dreamcast=dict(cover=(1360, 1360), back=(1568, 1360), spine=(174, 1360)))

FLAT = -90.0

BOXES = [
    dict(name="mooncrest", system="snes", game="Mooncrest Chronicle (Europe)", pitch=FLAT, yaw=4.0,
         at=(-10.0, 22.0, 0.0)),
    dict(name="wyrmspire", system="n64", game="Wyrmspire (Europe)", pitch=FLAT, yaw=-16.0, at=(-24.0, 28.0, 28.0)),
    dict(name="puck_rush", system="snes", game="Puck Rush (Europe)", pitch=FLAT, yaw=15.0, at=(-12.0, 18.0, 58.0)),
    dict(name="ghoulish_gus", system="megadrive", game="Ghoulish Gus (Europe)", pitch=FLAT, yaw=-24.0,
         at=(-16.0, 12.0, 86.0)),
    dict(name="halcyon_strike", system="megadrive", game="Halcyon Strike (Europe)", pitch=FLAT, yaw=70.0,
         at=(-16.0, 24.0, 112.0)),
    dict(name="budling", system="n64", game="Budling - Sky Garden (Europe)", pitch=-16.0, yaw=62.0,
         at=(137.0, 4.0, 0.0)),
    dict(name="kickflip_city", system="megadrive", game="Kickflip City (Europe)", pitch=FLAT, yaw=-76.0,
         at=(4.0, -147.0, 0.0)),
    dict(name="apex_circuit", system="snes", game="Apex Circuit (Europe)", pitch=FLAT, yaw=84.0,
         at=(-188.0, -40.0, 0.0)),
    dict(name="emberwild", system="psp", game="Emberwild (Europe)", pitch=FLAT, yaw=14.0, at=(-172.0, -212.0, 0.0)),
    dict(name="marlin_rush", system="dreamcast", game="Marlin Rush (Europe)", pitch=FLAT, yaw=-12.0,
         at=(-186.0, -262.0, 14.9)),
    dict(name="cold_meridian", system="ps2", game="Cold Meridian (Europe)", pitch=FLAT, yaw=-16.0,
         at=(176.0, -176.0, 0.0)),
    dict(name="stringwood", system="psx", game="Stringwood (Europe)", pitch=FLAT, yaw=10.0,
         at=(190.0, -226.0, 14.8)),
]

SCALE = 0.2                  # of the library's image size, in the atlases
ATLAS_WIDTH = 1024


def regions():
    """Each box's images in the two atlases, {name: {"cover": ("art", region), "spine": ..., "back": ("backs",
    region)}}, and the atlases' size: each atlas's images packed in shelves, the tallest first, left to right, a new
    shelf when one is full."""
    out = {box["name"]: {} for box in BOXES}
    height = 0
    for atlas, kinds in (("art", ("cover", "spine")), ("backs", ("back",))):
        items = [(box["name"], kind, *(round(v * SCALE) for v in ART[box["system"]][kind]))
                 for box in BOXES for kind in kinds]
        items.sort(key=lambda item: (-item[3], -item[2]))
        x = y = row = 0
        for name, kind, w, h in items:
            if x + w > ATLAS_WIDTH:
                x, y, row = 0, y + row, 0
            out[name][kind] = (atlas, (x, y, w, h))
            x, row = x + w, max(row, h)
        height = max(height, y + row)
    assert height <= ATLAS_WIDTH, f"The atlases are {height} pixels tall: lower SCALE"
    return out, (ATLAS_WIDTH, -(-height // 8) * 8)


REGIONS, ATLAS_SIZE = regions()
