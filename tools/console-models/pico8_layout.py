"""PICO-8's card, its logo in voxels: the pixels, palette and shades for pico8.py (which builds it). Plain Python:
Blender's Python imports it too.

PICO-8 is a fantasy console: it has no hardware, so its card is its emblem made solid: the sparkle of its logo (its
icon too), PICO-8's eight bright colours round a white cross, each pixel a cube VOXEL millimetres on a side, one deep.
A cube's front and back are its pixel's colour, its top and bottom one shade darker and its sides two (SHADES), as
voxel art in PICO-8's palette shades them. The owner's reference image, a voxel render of the sparkle seen from the
front, the right and above, has the shades of the tops and the right sides; the rest are the next shades down
PICO-8's palette and its secret one.

Millimetres: x across the face (left to right), y through it (away from the viewer), z up from the table.
"""

VOXEL = 20.0

# The sparkle, a pixel a character, its top row first: palette indices (hex digits), '.' nothing. As in PICO-8's logo,
# over its 8: red at the top, then round to the right peach, pink, lavender, blue, green, yellow and orange.
SPARKLE = ["..8..",
           ".97f.",
           "a777e",
           ".b7d.",
           "..c.."]

# PICO-8's palette (0 to 15) and its secret one (128 to 143), by index.
PALETTE = {0: "#000000", 1: "#1D2B53", 2: "#7E2553", 3: "#008751", 4: "#AB5236", 5: "#5F574F", 6: "#C2C3C7",
           7: "#FFF1E8", 8: "#FF004D", 9: "#FFA300", 10: "#FFEC27", 11: "#00E436", 12: "#29ADFF", 13: "#83769C",
           14: "#FF77A8", 15: "#FFCCAA",
           128: "#291814", 129: "#111D35", 130: "#422136", 131: "#125359", 132: "#742F29", 133: "#49333B",
           134: "#A28879", 135: "#F3EF7D", 136: "#BE1250", 137: "#FF6C24", 138: "#A8E72E", 139: "#00B543",
           140: "#065AB5", 141: "#754665", 142: "#FF6E59", 143: "#FF9D81"}

# Each colour's shades, as palette indices: (its top's and bottom's, its sides'). The white has none: the cross's
# sides are all against the colours round it.
SHADES = {8: (136, 2), 9: (137, 4), 10: (9, 137), 11: (139, 3), 12: (140, 1), 13: (141, 2), 14: (8, 136),
          15: (143, 142)}

# The texture: the palette, a block of BLOCK pixels a colour, COLUMNS blocks a row, in PALETTE's order.
BLOCK = 8
COLUMNS = 8

FPS = 30
LENGTH = 120                 # 4 s: one turn
