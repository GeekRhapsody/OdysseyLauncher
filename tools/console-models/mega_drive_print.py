"""The Mega Drive's printing and its cartridge label, for the console theme's models (mega_drive.py, mega_drive_cartridge.py).

Writes three images into a folder:
- megadrive_print.png: the console's top, as the model's planar UVs map it (x -140..140 left to right, y -106..106 front
  to back, seen from above): the body colour, the black ring with HIGH DEFINITION GRAPHICS - STEREO SOUND round its
  back, the slot's black lip, the 16-BIT plate and its white POWER strip, the volume, power and reset legends in the
  control panel, and MEGA DRIVE SEGA on the front slope.
- megadrive_label.png: mega_drive_label.png (the cartridge label) as plain RGB, for the inserted cartridge.
- megadrive_band.png: the label's bottom band (the grid and the MEGA DRIVE logo under the grey border), for the
  cartridge template, whose art shows above it. What's above the border's curve is painted the border's grey, so
  filtering never brings the label's art in at the edge.

Run it with the system Python (Pillow):

    python tools/console-models/mega_drive_print.py <out folder>
"""

import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

WIDTH_MM, DEPTH_MM = 280.0, 212.0
SCALE = 16  # pixels per millimetre while drawing; the result is resampled to OUT
OUT = (2048, 1552)
FONTS = "C:/Windows/Fonts/"
HERE = os.path.dirname(os.path.abspath(__file__))

BODY = "#34363B"
BLACK = "#151619"
SLOT = "#0A0A0C"
WHITE = "#ECECEC"
STRIP = "#E6E2D4"
GOLD = "#DDBE68"
LEGEND = "#C9CBCF"
RED = "#C8201E"

# As in mega_drive.py.
RING_CENTRE, RING_INNER, RING_OUTER = (34.0, 17.4), 74.0, 88.0
LIP = (34.0, 38.0, 134.0, 23.0)          # the slot's lip: centre, length, width
PLATE = (1.6, 65.4, -1.6)                # the 16-BIT plate: left, right, back edge
PANEL = (-121.0, -50.0, -98.0, -37.5)    # the control panel's recess: left, right, front, back

# The label's grey border, in the label's pixels (600 x 500): straight at its sides, with a bump under the SEGA badge.
LABEL_SIZE = (600, 500)
BAND_TOP = 356


def border_top(x):
    """The row where the label's grey border starts, at column x (as mega_drive_cartridge.py has it)."""
    return 393.5 - 27.5 * math.exp(-((x - 300) / 62) ** 2)


def is_grey(rgb):
    """The label's grey border (about #8E8785), not the beige art or the black grid."""
    r, g, b = rgb
    return 120 < r < 185 and abs(r - g) < 12 and abs(g - b) < 14


def px(x, y):
    """A point in millimetres (x from the centre, y from the centre towards the back) as canvas pixels."""
    return ((x + WIDTH_MM / 2) * SCALE, (DEPTH_MM / 2 - y) * SCALE)


def circle(draw, x, y, r, fill):
    cx, cy = px(x, y)
    draw.ellipse([cx - r * SCALE, cy - r * SCALE, cx + r * SCALE, cy + r * SCALE], fill=fill)


def rect(draw, x0, y0, x1, y1, fill, r=0.0):
    (a, b), (c, d) = px(x0, y1), px(x1, y0)
    if r:
        draw.rounded_rectangle([a, b, c, d], radius=r * SCALE, fill=fill)
    else:
        draw.rectangle([a, b, c, d], fill=fill)


def face(font, cap_mm, variation=None):
    """A font sized so its capitals are cap_mm high."""
    probe = ImageFont.truetype(FONTS + font, 200)
    if variation:
        probe.set_variation_by_name(variation)
    left, top, right, bottom = probe.getbbox("H")
    f = ImageFont.truetype(FONTS + font, int(200 * cap_mm * SCALE / (bottom - top)))
    if variation:
        f.set_variation_by_name(variation)
    return f


def text(canvas, s, font, cap_mm, x, y, fill, anchor="centre", shear=0.0, stretch=1.0, degrees=0.0, variation=None):
    """Text whose capitals are cap_mm high, its centre (or left edge) at x and its middle at y."""
    f = face(font, cap_mm, variation)
    left, top, right, bottom = f.getbbox(s)
    pad = int(cap_mm * SCALE)
    layer = Image.new("RGBA", (right - left + 2 * pad, bottom - top + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((pad - left, pad - top), s, font=f, fill=fill)
    if stretch != 1.0:
        layer = layer.resize((int(layer.width * stretch), layer.height), Image.LANCZOS)
    if shear:
        # Leans the tops to the right (italic), about the layer's middle.
        layer = layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * layer.height / 2, 0, 1, 0), resample=Image.BICUBIC)
    if degrees:
        layer = layer.rotate(degrees, resample=Image.BICUBIC, expand=True)
    layer = layer.crop(layer.getbbox())
    cx, cy = px(x, y)
    left_px = cx - layer.width / 2 if anchor == "centre" else cx
    canvas.alpha_composite(layer, (int(left_px), int(cy - layer.height / 2)))


def arc_text(canvas, s, font, cap_mm, centre, radius, fill, spacing=1.0):
    """Text round an arc, reading clockwise with its tops outwards, centred on the arc's back (+y)."""
    f = face(font, cap_mm)
    widths = [f.getlength(c) / SCALE * spacing for c in s]
    total = sum(widths)
    angle = math.pi / 2 + total / 2 / radius  # start left of the back, going clockwise
    for c, w in zip(s, widths):
        a = angle - w / 2 / radius
        if c != " ":
            x, y = centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)
            text(canvas, c, font, cap_mm, x, y, fill, degrees=math.degrees(a - math.pi / 2))
        angle -= w / radius


def top_print(out):
    canvas = Image.new("RGBA", (int(WIDTH_MM * SCALE), int(DEPTH_MM * SCALE)), BODY)
    draw = ImageDraw.Draw(canvas)

    # The ring (black, gloss on the model) and its legend; the disc inside it keeps the body colour.
    circle(draw, *RING_CENTRE, RING_OUTER + 0.6, BLACK)
    circle(draw, *RING_CENTRE, RING_INNER - 0.3, BODY)
    arc_text(canvas, "HIGH DEFINITION GRAPHICS \u00b7 STEREO SOUND", "arial.ttf", 1.9, RING_CENTRE, 79.6, WHITE, 1.04)

    # The slot's lip, black like the ring.
    x, y, length, width = LIP
    rect(draw, x - length / 2 - 0.5, y - width / 2 - 0.5, x + length / 2 + 0.5, y + width / 2 + 0.5, BLACK, width / 2)

    # The 16-BIT plate: black over the disc, the white POWER strip over the ring.
    left, right, back = PLATE
    strip = Image.new("L", canvas.size, 0)
    sd = ImageDraw.Draw(strip)
    cx, cy = px(*RING_CENTRE)
    r = (RING_OUTER + 0.6) * SCALE
    sd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    r = RING_INNER * SCALE
    sd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    plate_mask = Image.new("L", canvas.size, 0)
    rect(ImageDraw.Draw(plate_mask), left - 0.4, -80, right + 0.4, back + 0.4, 255, 3.0)
    black = Image.new("L", canvas.size, 0)
    r = RING_INNER * SCALE
    ImageDraw.Draw(black).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    canvas.paste(BLACK, mask=ImageChops.multiply(plate_mask, black))
    canvas.paste(STRIP, mask=ImageChops.multiply(plate_mask, strip))
    text(canvas, "16-BIT", "arialbd.ttf", 6.6, 33.6, -34.6, GOLD, stretch=1.08)
    text(canvas, "POWER", "arial.ttf", 1.7, 24.4, -64.2, "#3A3A3A", degrees=-6)
    circle(draw, 33.4, -65.2, 1.35, "#2A2A2A")
    circle(draw, 33.4, -65.2, 0.75, RED)
    draw.line([px(37.0, -65.0), px(44.0, -64.4)], fill="#3A3A3A", width=int(0.3 * SCALE))
    text(canvas, "ON", "arial.ttf", 1.7, 47.6, -64.0, "#3A3A3A", degrees=6)

    # The control panel: the volume slider's and power switch's slots, their knobs' red stripes, and the legends.
    rect(draw, -110.0, -92.5, -96.0, -45.5, SLOT, 0.8)
    rect(draw, -108.6, -73.6, -97.4, -72.6, RED)
    for k, label in enumerate(("10", "5", "0")):
        y = -50.6 - k * 10.3
        text(canvas, label, "arial.ttf", 1.8, -115.2, y, LEGEND)
    for k in range(11):
        y = -50.6 - k * 2.06
        draw.line([px(-113.2, y), px(-111.6 if k % 5 else -110.8, y)], fill=LEGEND, width=int(0.25 * SCALE))
    text(canvas, "VOLUME", "arial.ttf", 1.7, -98.4, -94.6, LEGEND)
    hx, hy = -108.4, -94.4  # a headphone mark
    draw.arc([*px(hx - 1.4, hy + 1.6), *px(hx + 1.4, hy - 1.2)], 180, 360, fill=LEGEND, width=int(0.35 * SCALE))
    rect(draw, hx - 1.6, hy - 1.4, hx - 0.9, hy + 0.2, LEGEND)
    rect(draw, hx + 0.9, hy - 1.4, hx + 1.6, hy + 0.2, LEGEND)

    rect(draw, -86.0, -57.7, -58.0, -45.6, SLOT, 0.8)
    rect(draw, -67.4, -56.4, -66.4, -47.0, RED)
    text(canvas, "ON", "arial.ttf", 1.7, -82.6, -61.4, LEGEND)
    for x in (-74.4, -72.2):
        draw.line([px(x, -60.4), px(x, -62.4)], fill=LEGEND, width=int(0.3 * SCALE))
    text(canvas, "OFF", "arial.ttf", 1.7, -61.6, -61.4, LEGEND)
    for label, y, (x0, x1) in (("POWER", -67.2, (-85.0, -59.0)), ("RESET", -94.2, (-85.0, -59.0))):
        text(canvas, label, "arial.ttf", 1.7, -72.0, y, LEGEND)
        draw.line([px(x0, y), px(-78.6, y)], fill=LEGEND, width=int(0.25 * SCALE))
        draw.line([px(-65.4, y), px(x1, y)], fill=LEGEND, width=int(0.25 * SCALE))

    # MEGA DRIVE and SEGA on the front slope, right.
    text(canvas, "MEGA DRIVE", "bahnschrift.ttf", 4.0, 56.4, -97.0, WHITE, anchor="left", shear=0.32, stretch=1.35,
         variation="Bold")
    text(canvas, "SEGA", "ariblk.ttf", 4.8, 104.4, -96.8, WHITE, anchor="left", shear=0.2, stretch=1.05)

    canvas.convert("RGB").resize(OUT, Image.LANCZOS).save(out, optimize=True)


def label_images(label_out, band_out):
    label = Image.open(os.path.join(HERE, "mega_drive_label.png")).convert("RGBA").convert("RGB")
    assert label.size == LABEL_SIZE, f"the label should be {LABEL_SIZE}, not {label.size}"
    label.save(label_out, optimize=True)

    grey = label.getpixel((50, 398))
    band = label.crop((0, BAND_TOP, LABEL_SIZE[0], LABEL_SIZE[1]))
    draw = ImageDraw.Draw(band)
    for x in range(band.width):
        # Down to the border as drawn (the first grey pixel), or the curve the model cuts along, whichever is lower.
        drawn = next((y for y in range(BAND_TOP, 420) if is_grey(label.getpixel((x, y)))), 0)
        bottom = max(drawn, border_top(x + 0.5) + 1.5)
        draw.line([(x, 0), (x, bottom - BAND_TOP)], fill=grey)
    band.save(band_out, optimize=True)


if __name__ == "__main__":
    folder = os.path.abspath(sys.argv[1])
    os.makedirs(folder, exist_ok=True)
    top_print(os.path.join(folder, "megadrive_print.png"))
    label_images(os.path.join(folder, "megadrive_label.png"), os.path.join(folder, "megadrive_band.png"))
