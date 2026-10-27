"""The All games card's measurements and its art's layout, shared by all_games_print.py (which packs the boxes' art) and
all_games.py (which builds the pile). Plain Python: Blender's Python imports it too.

All games has no hardware, so its card is an untidy pile of game boxes: made-up games from tools/made-up-games's library
(their covers, backs and spines; no real game's art), three Mega Drive cases, three Super Nintendo boxes and two
Nintendo 64 boxes, each the base theme's own template for its system (memory-card's megadrive_clamshell,
snes_box_horizontal and generic_box_top, the N64's), at its real size. Millimetres: x across (left to right), y back
from the pile's middle, z up from the table.

The pile (BOXES): five boxes stacked flat, each turned against the one under it, the two Mega Drive cases on top; an N64
box leaning back against its right side, its cover out to the right; a Mega Drive case and a Super Nintendo box on the
table in front of it and at its left. Each box: its system and game (the library's file name), its lean (pitch, degrees
about x: -90 lies it on its back, cover up; 0 stands it up; a little less than 0 leans it back), its turn about the
vertical (yaw, degrees), and where it goes: the middle of its footprint (x, y) and its underside (z).

The art is two textures (ATLAS_SIZE, JPEG: it's painted art): `art`, every box's cover and spine, and `backs`, every
box's back, each image at SCALE of the library's size, packed in rows (REGIONS, computed by regions()). 1024 pixels
wide, as the launcher draws no texture larger. A region is (x, y, width, height) in pixels.
"""

FPS = 30
LENGTH = 150                 # 5 s

# The templates: the file in memory-card's models/templates/, and its largest side in millimetres (the spec fits it to
# 1 m): the Mega Drive case's height with its hanger tab; the boxes' width.
TEMPLATES = dict(megadrive=("megadrive_clamshell.glb", 205.4), snes=("snes_box_horizontal.glb", 190.0),
                 n64=("generic_box_top.glb", 190.0))

# The library's image sizes, per system: cover, back, spine.
ART = dict(megadrive=dict(cover=(968, 1360), back=(962, 1360), spine=(162, 1360)),
           snes=dict(cover=(1360, 994), back=(1360, 994), spine=(1360, 194)),
           n64=dict(cover=(1360, 994), back=(1360, 994), spine=(1360, 194)))

FLAT = -90.0

BOXES = [
    dict(name="mooncrest", system="snes", game="Mooncrest Chronicle (Europe)", pitch=FLAT, yaw=4.0,
         at=(-10.0, 22.0, 0.0)),
    dict(name="wyrmspire", system="n64", game="Wyrmspire (Europe)", pitch=FLAT, yaw=-16.0, at=(-24.0, 28.0, 28.0)),
    dict(name="puck_rush", system="snes", game="Puck Rush (Europe)", pitch=FLAT, yaw=15.0, at=(-12.0, 18.0, 58.0)),
    dict(name="ghoulish_gus", system="megadrive", game="Ghoulish Gus (Europe)", pitch=FLAT, yaw=-24.0,
         at=(-16.0, 12.0, 86.0)),
    dict(name="halcyon_strike", system="megadrive", game="Halcyon Strike (Europe)", pitch=FLAT, yaw=70.0,
         at=(-16.0, 24.0, 107.9)),
    dict(name="budling", system="n64", game="Budling - Sky Garden (Europe)", pitch=-16.0, yaw=62.0,
         at=(137.0, 4.0, 0.0)),
    dict(name="kickflip_city", system="megadrive", game="Kickflip City (Europe)", pitch=FLAT, yaw=-76.0,
         at=(4.0, -147.0, 0.0)),
    dict(name="apex_circuit", system="snes", game="Apex Circuit (Europe)", pitch=FLAT, yaw=84.0,
         at=(-188.0, -40.0, 0.0)),
]

SCALE = 0.25                 # of the library's image size, in the atlases
ATLAS_SIZE = (1024, 840)


def regions():
    """Each box's images in the two atlases: {name: {"cover": ("art", region), "spine": ..., "back": ("backs",
    region)}}. Rows, in BOXES's order: the Mega Drive's covers and spines in the first row of `art`, the others' covers
    three to a row under it, their spines in a column beside the last row; the backs likewise in `backs`."""
    out = {box["name"]: {} for box in BOXES}
    for atlas, kinds in (("art", ("cover", "spine")), ("backs", ("back",))):
        x, y, row = 0, 0, 0
        tall = [b for b in BOXES if b["system"] == "megadrive"]
        wide = [b for b in BOXES if b["system"] != "megadrive"]
        for box in tall:                                        # the tall covers (or backs) side by side
            w, h = (round(v * SCALE) for v in ART["megadrive"][kinds[0]])
            out[box["name"]][kinds[0]] = (atlas, (x, y, w, h))
            x, row = x + w, max(row, h)
        if "spine" in kinds:
            for box in tall:                                    # then their spines
                w, h = (round(v * SCALE) for v in ART["megadrive"]["spine"])
                out[box["name"]]["spine"] = (atlas, (x, y, w, h))
                x += w
        x, y = 0, y + row
        for k, box in enumerate(wide):                          # the wide ones three to a row
            w, h = (round(v * SCALE) for v in ART[box["system"]][kinds[0]])
            if k and k % 3 == 0:
                x, y = 0, y + h
            out[box["name"]][kinds[0]] = (atlas, (x, y, w, h))
            x += w
        if "spine" in kinds:
            sy = y
            for box in wide:                                    # their spines stacked beside the last row
                w, h = (round(v * SCALE) for v in ART[box["system"]]["spine"])
                out[box["name"]]["spine"] = (atlas, (x, sy, w, h))
                sy += h
    return out


REGIONS = regions()
