"""The Commodore 64 card's printing and screens, for the console theme's Commodore 64 model (commodore_64.py); its video
(commodore_64_video.py) draws its frames with the screens here. commodore_64_layout.py has the measurements and where
each part is in the atlases.

Writes three images into a folder:
- c64_print.png: the computer seen from above, in millimetres as the model's planar UVs map it (the wells, each key's
  top in its colour with its legend, the plate's frame line, the badge with commodore, the rainbow and 64, the POWER
  plate, the ribs); each key's front, a cell each (the PETSCII graphics, the colours' names, HOME, DEL, pi, f 2 to f 8);
  the right end and its recess (CONTROL PORT 1 and 2, ON over the switch, the power socket); the strip the case's other
  sides take, the seam's line across it; swatches.
- c64_devices.png: the 1541's front (the brown band with commodore, the rainbow and 1541; the bezel round its slot, the
  pocket under the lever, the green power light) and its top (the vents, Commodore's mark pressed into it); the floppy's
  two sides (a made-up game's label on its top); the 1702's front under its bezel (the commodore badge and its lit POWER
  light, VIDEO MONITOR MODEL 1702, the control door, the jacks) and its top's vents; the drive's sides' strip with its
  seam; swatches.
- c64_screen.png: the glass showing the C64's start-up screen, the `video` material's texture: the video's first frame.

The screens are the C64's: its 16 colours, its 40 x 25 characters of 8 x 8 pixels (a character set drawn here in the
C64's manner, two pixels wide upright and one across), the paper in its border, at twice the size on the 1702's glass.
The loading picture is the game's key art in multicolour's wide pixels, at most four colours to a character cell; the
game itself is drawn here, a submarine in a sea that scrolls. The game, Deep Fathom, is made up (tools/made-up-games).
Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow):

    python tools/console-models/commodore_64_print.py artifacts/made-up-games artifacts/c64
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commodore_64_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region, mix  # noqa: E402

C = {name: rgb(value) for name, value in L.COLOURS.items()}
WHITE = (244, 242, 236)
SILVER = (206, 202, 192)
RAINBOW = [(224, 60, 49), (240, 138, 36), (242, 210, 60), (62, 168, 78), (47, 143, 216)]


def commodore_mark(reg, x, y, s, fill, cut):
    """Commodore's mark, s across, its middle at (x, y): the C, open to the right, and its two flags."""
    layer = reg.layer()
    d = ImageDraw.Draw(layer)
    r0, r1 = 0.5 * s, 0.29 * s
    d.ellipse(reg.box(x - r0, y - r0, x + r0, y + r0), fill=fill + (255,))
    d.ellipse(reg.box(x - r1, y - r1, x + r1, y + r1), fill=cut + (255,))
    d.rectangle(reg.box(x, y - 0.23 * s, x + r0 + 1, y + 0.23 * s), fill=cut + (255,))
    reg.over(layer)
    for top, bottom in ((-0.21 * s, -0.03 * s), (0.03 * s, 0.21 * s)):
        reg.poly([(x + 0.06 * s, y + top), (x + 0.5 * s, y + top), (x + 0.5 * s - (bottom - top), y + bottom),
                  (x + 0.06 * s, y + bottom)], fill)


def rainbow(reg, x0, y0, x1, y1, slant=0.0):
    """The rainbow's five stripes across (x0, y0, x1, y1), each slanting by slant (millimetres over its height)."""
    h = (y1 - y0) / 5
    for k, colour in enumerate(RAINBOW):
        a, b = y0 + k * h, y0 + (k + 0.72) * h
        reg.poly([(x0 + slant, a), (x1 + slant, a), (x1, b), (x0, b)], colour)


def pad_edges(atlas, rect, width=4):
    """Repeats a region's edge pixels outwards by width, so a face sampling its edge never takes its neighbour's."""
    x, y, w, h = rect
    inner = atlas.crop((x, y, x + w, y + h))
    grown = inner.resize((w + 2 * width, h + 2 * width), Image.NEAREST)
    grown.paste(inner, (width, width))
    for k in range(width):                                   # the edges, copied out a pixel at a time
        grown.paste(inner.crop((0, 0, w, 1)), (width, k))
        grown.paste(inner.crop((0, h - 1, w, h)), (width, h + width + k))
        grown.paste(grown.crop((width, 0, width + 1, h + 2 * width)), (k, 0))
        grown.paste(grown.crop((width + w - 1, 0, width + w, h + 2 * width)), (w + width + k, 0))
    return grown, (x - width, y - width)


def place(atlas, reg, pad=4):
    """Pastes a region into the atlas, its edge pixels repeated round it."""
    reg.paste(atlas)
    grown, at = pad_edges(atlas, reg.rect, pad)
    gx, gy = at
    gw, gh = grown.size
    left, top = max(0, -gx), max(0, -gy)
    right, bottom = min(gw, atlas.width - gx), min(gh, atlas.height - gy)
    atlas.paste(grown.crop((left, top, right, bottom)), (gx + left, gy + top))
    reg.paste(atlas)                                          # the region itself on top, unpadded


# ---- The computer from above -----------------------------------------------------------------------------------------

def top_xy(x, s, h=0.0):
    """The top region's millimetres (across from the left end, down from the back) of the point (x, s, h) on the
    deck."""
    y, _ = L.deck_point(s, h)
    return x + L.WIDTH / 2, L.DEPTH - y


def deck_poly(points, h=0.0):
    return [top_xy(x, s, h) for x, s in points]


def graphics(reg, x, y, k, ink, size=2.6):
    """Two PETSCII graphics side by side, centred on (x, y): small squares, each part filled, varying with the key."""
    rng = random.Random(k * 7 + 3)
    for i in range(2):
        x0, half = x - size * 1.15 + i * size * 1.3, size / 2
        reg.rect_(x0, y - half, x0 + size, y + half, None, outline=ink, width=0.2)
        kind = rng.randrange(6)
        if kind == 0:
            reg.rect_(x0, y - half, x0 + size / 2, y + half, ink)
        elif kind == 1:
            reg.rect_(x0, y, x0 + size, y + half, ink)
        elif kind == 2:
            reg.circle(x0 + size / 2, y, size * 0.3, ink)
        elif kind == 3:
            reg.line([(x0, y + half), (x0 + size, y - half)], ink, 0.22)
        elif kind == 4:
            reg.poly([(x0, y + half), (x0 + size, y + half), (x0 + size, y - half)], ink)
        else:
            reg.rect_(x0 + size / 2, y - half, x0 + size, y, ink)


def key_top(reg, name, rect, colour, legend):
    x0, s0, x1, s1 = rect
    i, f = L.KEY_INSET, L.KEY_FRONT
    pts = deck_poly([(x0 + i, s0 + f), (x1 - i, s0 + f), (x1 - i, s1 - i), (x0 + i, s1 - i)], L.KEY_HEIGHT)
    reg.poly(pts, shade(colour, 0.06))
    if not legend:
        return
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    if name == "cbm":
        commodore_mark(reg, cx, cy, 6.2, WHITE, shade(colour, 0.06))
        return
    lines = legend.split("\n")
    if len(lines) == 2 and all(len(line) == 1 for line in lines):     # a symbol over its digit or character
        reg.text(lines[0], "arialbd.ttf", 3.0, cx - 2.2, cy - 2.0, WHITE)
        reg.text(lines[1], "arialbd.ttf", 4.2, cx + 0.8, cy + 1.4, WHITE)
        return
    if len(lines) == 1 and len(legend) <= 2 and not legend.startswith("f"):
        font = "seguisym.ttf" if not legend.isascii() else "arialbd.ttf"
        reg.text(legend, font, 4.8, cx, cy, WHITE)
        return
    size = 2.3 if max(len(line) for line in lines) > 4 else 2.7
    for j, line in enumerate(lines):
        font = "seguisym.ttf" if not line.isascii() else "arialbd.ttf"
        reg.text(line, font, size, cx, cy + (j - (len(lines) - 1) / 2) * (size + 0.7), WHITE)


def badge(reg):
    (x0, x1), (s0, s1) = L.BADGE["x"], L.BADGE["s"]
    (ax, ay), (bx, by) = top_xy(x0, s1), top_xy(x1, s0)
    h = by - ay
    plate = C["badge"]
    reg.rect_(ax - 0.3, ay - 0.3, bx + 0.3, by + 0.3, shade(plate, -0.35), r=h / 2 + 0.3)
    reg.rect_(ax, ay, bx, by, plate, r=h / 2)
    ink = C["ink"]
    commodore_mark(reg, ax + h * 0.75, (ay + by) / 2, h * 0.66, ink, plate)
    reg.text("commodore", "arialbd.ttf", h * 0.78, ax + h * 1.3, (ay + by) / 2 - h * 0.04, ink, anchor="lm")
    rx = ax + (bx - ax) * 0.6
    rainbow(reg, rx, ay + h * 0.12, rx + h * 2.6, by - h * 0.12, slant=h * 0.5)
    reg.text("64", "arialbd.ttf", h * 0.92, bx - h * 1.25, (ay + by) / 2, ink)


def power_plate(reg):
    (x0, x1), (s0, s1) = L.POWER["x"], L.POWER["s"]
    (ax, ay), (bx, by) = top_xy(x0, s1), top_xy(x1, s0)
    h = by - ay
    reg.rect_(ax - 0.3, ay - 0.3, bx + 0.3, by + 0.3, shade(C["badge"], -0.35), r=h / 2 + 0.3)
    reg.rect_(ax, ay, bx, by, C["badge"], r=h / 2)
    reg.text("POWER", "arialbd.ttf", h * 0.46, ax + (bx - ax) * 0.42, (ay + by) / 2, C["ink"])
    lx, ly = top_xy(*L.POWER["light"])
    reg.circle(lx, ly, L.POWER["r"] + 0.9, (40, 22, 18))
    reg.circle(lx, ly, L.POWER["r"], (120, 30, 24))


def top():
    reg = Region(L.REGIONS["top"], L.WIDTH, L.DEPTH, C["case"])
    for k in range(L.RIBS["count"]):                          # the ribs across the back
        y = L.DEPTH - (L.RIBS["y0"] + k * L.RIBS["step"])
        reg.rect_(3.0, y - 1.5, L.WIDTH - 3.0, y + 1.5, shade(C["case"], -0.07))
        reg.line([(3.0, y - 1.5), (L.WIDTH - 3.0, y - 1.5)], shade(C["case"], 0.14), 0.5)
        reg.line([(3.0, y + 1.5), (L.WIDTH - 3.0, y + 1.5)], shade(C["case"], -0.2), 0.45)
    fx, (fs0, fs1) = L.FRAME["x"], L.FRAME["s"]               # the line round the keyboard's plate
    groove = [top_xy(-fx, fs1), top_xy(-fx, fs0), top_xy(fx, fs0), top_xy(fx, fs1)]
    reg.line(groove, shade(C["case"], -0.22), 0.55)
    reg.line([(x + 0.5, y + 0.5) for x, y in groove], shade(C["case"], 0.12), 0.35)
    for outline in L.wells():                                 # the wells, dark between the keys
        reg.poly(deck_poly(outline, -L.WELL), (26, 22, 18))
    badge(reg)
    power_plate(reg)
    for name, xu, row, wu, top_legend, _ in L.KEYS:
        key_top(reg, name, L.key_rect(xu, row, wu), C["key"], top_legend)
    for name, row, top_legend, _ in L.FKEYS:
        key_top(reg, name, L.fkey_rect(row), C["fkey"], top_legend)
    return reg


def fronts(atlas):
    """Each key's front face, its cell spanning its base's width and from the well's floor (the cell's foot) to its
    top: its legend on its upper part."""
    cells = L.front_cells()
    legends = {k[0]: (k[5], k[3]) for k in L.KEYS}
    legends.update({f[0]: (f[3], L.FKEY_W) for f in L.FKEYS})
    for k, (name, rect) in enumerate(cells.items()):
        legend, wu = legends[name]
        w, h = wu * L.U - L.GAP, L.KEY_HEIGHT + L.WELL
        colour = C["fkey"] if name.startswith("f") and name[1:].isdigit() else C["key"]
        reg = Region(rect, w, h, colour)
        reg.rect_(0, 0, w, h * 0.12, shade(colour, 0.06))        # the top's edge, catching the light
        cx, cy = w / 2, h * 0.36
        if legend == L.G:
            graphics(reg, cx, cy, k, WHITE)
        else:
            lines = legend.split("\n")
            size = 2.4 if max(len(line) for line in lines) > 3 else 3.0
            for j, line in enumerate(lines):
                font = "seguisym.ttf" if not line.isascii() else "arialbd.ttf"
                reg.text(line, font, size, cx, cy + (j - (len(lines) - 1) / 2) * (size + 0.4), WHITE)
        place(atlas, reg, 1)


def dsub(reg, y0, y1, z0, z1, label):
    """A 9-pin D socket seen from the right (front to the left), and its name over it."""
    w, h = y1 - y0, z1 - z0
    reg.poly([(y0, z0), (y1, z0), (y1 - w * 0.08, z1), (y0 + w * 0.08, z1)], (58, 58, 56))
    reg.poly([(y0 + 1.2, z0 + 1.2), (y1 - 1.2, z0 + 1.2), (y1 - w * 0.08 - 1.0, z1 - 1.2),
              (y0 + w * 0.08 + 1.0, z1 - 1.2)], (18, 18, 18))
    for k in range(5):
        reg.circle(y0 + w * (0.2 + 0.15 * k), z0 + h * 0.35, 0.55, (180, 176, 160))
    for k in range(4):
        reg.circle(y0 + w * (0.275 + 0.15 * k), z0 + h * 0.68, 0.55, (180, 176, 160))
    for j, line in enumerate(label.split("\n")):
        reg.text(line, "arialbd.ttf", 2.1, (y0 + y1) / 2, z0 - 6.2 + j * 2.6, (196, 192, 180))


def side():
    """The right end seen from the right: the front at the left, millimetres down from its top."""
    reg = Region(L.REGIONS["side"], L.DEPTH, L.HEIGHT, C["case"])
    (y0, y1), (z0, z1) = L.RECESS["y"], L.RECESS["z"]
    down = lambda z: L.HEIGHT - z                              # noqa: E731
    reg.rect_(0, down(L.SEAM) - 0.55, L.DEPTH, down(L.SEAM) + 0.55, shade(C["case"], -0.45))
    reg.rect_(0, down(L.SEAM) + 0.55, L.DEPTH, down(L.SEAM) + 1.1, shade(C["case"], 0.1))
    reg.rect_(y0, down(z1), y1, down(z0), (33, 34, 30), r=2.0)
    p = L.PORTS
    dsub(reg, *p["control1"], down(36.0), down(24.0), "CONTROL\nPORT 1")
    dsub(reg, *p["control2"], down(36.0), down(24.0), "CONTROL\nPORT 2")
    a, b = p["switch"]
    reg.text("ON", "arialbd.ttf", 2.2, (a + b) / 2, down(45.5), (196, 192, 180))
    a, b = p["socket"]
    cy, r = down(33.0), (b - a) / 2
    reg.circle((a + b) / 2, cy, r, (52, 52, 50))
    reg.circle((a + b) / 2, cy, r - 2.0, (14, 14, 14))
    for k in range(7):
        ang = math.radians(200 + 140 * k / 6)
        reg.circle((a + b) / 2 + 5.4 * math.cos(ang), cy - 5.4 * math.sin(ang), 0.6, (170, 166, 150))
    reg.text("POWER", "arialbd.ttf", 2.0, (a + b) / 2, down(47.0), (196, 192, 180))
    return reg


def seam_strip(rect, height, z, colour):
    """A strip up a side's height (millimetres down from its top), its colour with the seam's line at z: what the
    sides take, so the seam is drawn smooth at any distance where a groove a millimetre high would break up."""
    reg = Region(rect, 4.0, height, colour)
    y = height - z
    reg.rect_(0, y - 0.55, 4.0, y + 0.55, shade(colour, -0.45))
    reg.rect_(0, y + 0.55, 4.0, y + 1.1, shade(colour, 0.1))
    return reg


def print_atlas(out):
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), C["case"])
    for reg in (top(), side(), seam_strip(L.REGIONS["seam"], L.HEIGHT, L.SEAM, C["case"])):
        place(atlas, reg)
    fronts(atlas)
    d = ImageDraw.Draw(atlas)
    swatch = dict(case=C["case"], key=C["key"], fkey=C["fkey"], dark=C["dark"], lit=rgb(L.COLOURS["lit"]),
                  badge=C["badge"], recess=(33, 34, 30), black=(10, 10, 10), plug=(40, 40, 40))
    for name, colour in swatch.items():
        x, y = L.SWATCHES[name]
        d.rectangle([x - 16, y - 16, x + 15, y + 15], fill=colour)
    path = os.path.join(out, "c64_print.png")
    atlas.save(path, optimize=True)
    print(path)


# ---- The 1541, the floppy and the 1702 -------------------------------------------------------------------------------

def drive_front():
    """The drive's front: x from its left end, millimetres down from its top."""
    w, h = L.DRIVE["width"], L.DRIVE["height"]
    reg = Region(L.DEVICE_REGIONS["drive_front"], w, h, C["drive"])
    down = lambda z: h - z                                     # noqa: E731
    seam = down(L.DRIVE["seam"])
    reg.rect_(0, seam - 0.55, w, seam + 0.55, shade(C["drive"], -0.45))
    reg.rect_(0, seam + 0.55, w, seam + 1.1, shade(C["drive"], 0.1))
    (b0, b1), (z0, z1) = L.BAND["x"], L.BAND["z"]
    reg.rect_(b0, down(z1), b1, down(z0), C["band"], r=1.0)
    bh = z1 - z0
    mid = down((z0 + z1) / 2)
    commodore_mark(reg, b0 + 8.5, mid, bh * 0.58, SILVER, C["band"])
    reg.text("commodore", "arialbd.ttf", bh * 0.42, b0 + 15.0, mid, SILVER, anchor="lm")
    rainbow(reg, b0 + 82.0, down(z1) + bh * 0.16, b0 + 120.0, down(z0) - bh * 0.16, slant=bh * 0.3)
    reg.text("1541", "arialbd.ttf", bh * 0.44, b1 - 16.0, mid + bh * 0.08, SILVER)
    # The bezel: its face, the slot's lips, the pocket under the lever, the step at its right.
    (x0, x1), (z0, z1) = L.BEZEL["x"], L.BEZEL["z"]
    reg.rect_(x0, down(z1), x1, down(z0), C["bezel"], r=0.8)
    (s0, s1), (sz0, sz1) = L.SLOT["x"], L.SLOT["z"]
    reg.rect_(s0 - 1.5, down(sz1) - 1.6, s1 + 1.5, down(sz0) + 1.6, shade(C["bezel"], -0.25), r=1.0)
    reg.rect_(s0, down(sz1), s1, down(sz0), (14, 10, 8))
    lx, lz = L.LEVER["x"], L.LEVER["z"]
    reg.rect_(lx + 4.0, down(lz + 1.0), 124.0, down(z0 + 3.0), shade(C["bezel"], -0.12), r=0.6)
    reg.poly([(124.0, down(lz + 1.0)), (156.0, down(lz + 1.0)), (148.0, down(z0 + 3.0)), (124.0, down(z0 + 3.0))],
             shade(C["bezel"], -0.06))
    reg.rect_(lx - 6.5, down(sz0 - 1.0), lx + 6.5, down(z0 + 2.0), shade(C["bezel"], 0.05), r=0.6)
    dx, dz = L.DRIVE_LIGHT["x"], L.DRIVE_LIGHT["z"]
    dw, dh = L.DRIVE_LIGHT["size"]
    reg.rect_(dx - dw / 2 - 0.4, down(dz + dh / 2) - 0.4, dx + dw / 2 + 0.4, down(dz - dh / 2) + 0.4, (20, 8, 6))
    reg.rect_(dx - dw / 2, down(dz + dh / 2), dx + dw / 2, down(dz - dh / 2), (96, 26, 20))
    gx, gz, gr = L.GREEN["x"], L.GREEN["z"], L.GREEN["r"]     # the power light, lit
    glow = reg.layer()
    ImageDraw.Draw(glow).ellipse(reg.box(gx - gr * 2.6, down(gz) - gr * 2.6, gx + gr * 2.6, down(gz) + gr * 2.6),
                                 fill=(90, 255, 120, 70))
    reg.over(Image.composite(glow, reg.layer(), glow.getchannel("A").filter(ImageFilter.GaussianBlur(6))))
    reg.circle(gx, down(gz), gr + 0.7, (30, 34, 30))
    reg.circle(gx, down(gz), gr, rgb(L.COLOURS["green"]))
    reg.circle(gx - gr * 0.3, down(gz) - gr * 0.3, gr * 0.35, (220, 255, 226))
    return reg


def drive_top():
    """The drive's top from above: x from its left end, millimetres down from its back."""
    w, d = L.DRIVE["width"], L.DRIVE["depth"]
    reg = Region(L.DEVICE_REGIONS["drive_top"], w, d, C["drive"])
    for k in range(34):                                        # the vents across its back
        y = 8.0 + k * 5.0
        reg.rect_(10.0, y, w - 10.0, y + 2.2, shade(C["drive"], -0.12), r=1.0)
        reg.line([(10.0, y + 2.2), (w - 10.0, y + 2.2)], shade(C["drive"], 0.1), 0.4)
    cx, cy, s = w / 2, d - 175.0, 26.0                         # Commodore's mark, pressed into the top
    reg.rect_(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, shade(C["drive"], -0.05), r=4.0)
    reg.rect_(cx - s / 2 + 1.0, cy - s / 2 + 1.0, cx + s / 2 - 1.0, cy + s / 2 - 1.0, shade(C["drive"], 0.03), r=3.4)
    commodore_mark(reg, cx, cy, s * 0.62, shade(C["drive"], -0.1), shade(C["drive"], 0.03))
    return reg


def floppy(made_up, under=False):
    """The floppy from above, its leading edge (into the drive) at the top: its black jacket, the hub's ring, the
    head's window and the index hole; on its top, the label along its trailing edge and the write-protect notch."""
    s = L.DISK["size"]
    reg = Region(L.DEVICE_REGIONS["floppy_under" if under else "floppy"], s, s, C["disk"])
    sheen = reg.layer()
    ImageDraw.Draw(sheen).polygon([reg.p(0, s * 0.15), reg.p(s * 0.35, 0), reg.p(s * 0.55, 0), reg.p(0, s * 0.42)],
                                  fill=(255, 255, 255, 12))
    reg.over(sheen)
    cx, cy = s / 2, s / 2
    media = (70, 48, 36)
    reg.circle(cx, cy, 19.0, (214, 210, 200))                  # the hub's ring and its hole
    reg.circle(cx, cy, 14.3, media)
    reg.circle(cx, cy, 13.4, (20, 16, 14))
    hx = cx + (-1 if under else 1) * 19.0
    reg.circle(hx, cy - 12.0, 2.6, media)                      # the index hole
    reg.rect_(cx - 6.5, 6.0, cx + 6.5, cy - 24.0, media, r=6.5)   # the head's window, towards the leading edge
    nx = s - 0.01 if not under else 0.01
    reg.rect_(nx - 3.0, s - 46.0, nx + 3.0, s - 39.0, (44, 40, 36))   # the write-protect notch
    if under:
        return reg
    lw, lh, ly = 104.0, 30.0, s - 35.0                         # the label along the trailing edge
    lx = (s - lw) / 2
    reg.rect_(lx, ly, lx + lw, ly + lh, rgb(L.COLOURS["sleeve"]), r=1.2)
    stem, system, _ = L.MADE_UP
    cover = Image.open(os.path.join(made_up, "library", "media", system, "covers", stem + ".jpg")).convert("RGB")
    art = ImageOps.fit(cover.crop((round(cover.width * 0.16), 0, cover.width, cover.height)), (300, 230),
                          Image.LANCZOS, centering=(0.5, 0.45))   # past the box's banner at its left
    x0, y0, x1, y1 = reg.box(lx + 1.5, ly + 1.5, lx + 34.0, ly + lh - 1.5)
    reg.img.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.rect_(lx + 36.0, ly + 2.0, lx + lw - 2.0, ly + 5.0, (20, 92, 150))
    reg.text("DEEP FATHOM", "ariblk.ttf", 6.4, lx + 36.0, ly + 12.2, (18, 40, 70), anchor="lm")
    reg.text("COMMODORE 64  -  DISK 1", "arialbd.ttf", 2.7, lx + 36.0, ly + 19.6, (60, 60, 64), anchor="lm")
    reg.text("Brightmoor  1992", "ariali.ttf", 2.7, lx + 36.0, ly + 24.6, (60, 60, 64), anchor="lm")
    return reg


def monitor_front():
    """The 1702's front under its bezel: x from its left edge, millimetres down from z = 62."""
    M = L.MONITOR
    w, top = M["width"], 62.0
    reg = Region(L.DEVICE_REGIONS["monitor_front"], w, top, C["monitor"])
    down = lambda z: top - z                                   # noqa: E731
    x = lambda v: v + w / 2                                    # noqa: E731
    reg.line([(0, down(36.2)), (w, down(36.2))], shade(C["monitor"], -0.3), 0.6)     # under the strip
    reg.line([(0, down(35.6)), (w, down(35.6))], shade(C["monitor"], 0.12), 0.4)
    # The badge: commodore and the rainbow on a dark plate, the POWER window and its light at its right.
    bx0, bx1, bz0, bz1 = x(-59.5), x(54.5), 41.5, 56.5
    reg.rect_(bx0, down(bz1), bx1, down(bz0), (84, 74, 62), r=0.6)
    bh = bz1 - bz0
    mid = down((bz0 + bz1) / 2)
    commodore_mark(reg, bx0 + 7.0, mid, bh * 0.55, SILVER, (84, 74, 62))
    reg.text("commodore", "arialbd.ttf", bh * 0.4, bx0 + 12.5, mid, SILVER, anchor="lm")
    rainbow(reg, bx0 + 64.0, down(bz1) + 2.0, bx0 + 88.0, down(bz0) - 2.0)
    reg.rect_(bx1 - 22.0, down(bz1) + 1.0, bx1 - 2.0, down(bz0) - 1.0, (16, 14, 12), r=0.4)
    reg.circle(bx1 - 12.0, mid - 1.6, 1.3, (255, 70, 50))
    reg.text("POWER", "arialbd.ttf", 1.9, bx1 - 12.0, mid + 3.0, (190, 186, 176))
    # VIDEO MONITOR / MODEL 1702, and the power button's legend.
    reg.rect_(x(91.5), down(56.0), x(151.5), down(43.0), shade(C["monitor"], 0.06), r=0.6)
    reg.rect_(x(91.5), down(56.0), x(151.5), down(43.0), None, r=0.6, outline=shade(C["monitor"], -0.2), width=0.3)
    reg.text("VIDEO MONITOR", "arialbd.ttf", 3.0, x(121.5), down(52.5), (40, 36, 34))
    reg.text("MODEL 1702", "arialbd.ttf", 3.0, x(121.5), down(46.6), (40, 36, 34))
    reg.text("POWER", "arial.ttf", 2.0, x(166.0), down(38.6), (60, 56, 52))
    # The control door and the jacks' panel.
    (d0, d1), (dz0, dz1) = M["door"]["x"], M["door"]["z"]
    reg.rect_(x(d0), down(dz1), x(d1), down(dz0), None, r=0.8, outline=shade(C["monitor"], -0.28), width=0.6)
    reg.line([(x(d0) + 1.0, down(dz1) + 1.2), (x(d1) - 1.0, down(dz1) + 1.2)], shade(C["monitor"], 0.1), 0.5)
    (j0, j1), (jz0, jz1) = M["jacks"]["x"], M["jacks"]["z"]
    reg.rect_(x(j0), down(jz1), x(j1), down(jz0), shade(C["monitor"], -0.1), r=0.8)
    for k, (name, ring) in enumerate((("VIDEO", (232, 196, 40)), ("AUDIO", (226, 226, 220)))):
        cx = x(j0) + 16.0 + k * 26.0
        reg.circle(cx, down(23.0), 6.0, (24, 22, 20))
        reg.circle(cx, down(23.0), 4.4, ring)
        reg.circle(cx, down(23.0), 2.2, (30, 28, 26))
        reg.text(name, "arial.ttf", 2.2, cx, down(12.5), (50, 46, 42))
    return reg


def monitor_top():
    """The 1702's top from above: x from its left edge, millimetres down from its back."""
    M = L.MONITOR
    w, d = M["width"], M["depth"]
    reg = Region(L.DEVICE_REGIONS["monitor_top"], w, d, C["monitor"])
    reg.rect_(60.0, 20.0, w - 60.0, 180.0, shade(C["monitor"], -0.04), r=3.0)
    for k in range(22):                                        # the vents over the tube
        y = 26.0 + k * 7.0
        reg.rect_(66.0, y, w - 66.0, y + 3.0, shade(C["monitor"], -0.32), r=1.4)
    return reg


def devices_atlas(made_up, out):
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), C["drive"])
    strip = seam_strip(L.DEVICE_REGIONS["drive_seam"], L.DRIVE["height"], L.DRIVE["seam"], C["drive"])
    for reg in (drive_front(), drive_top(), floppy(made_up), floppy(made_up, under=True), monitor_front(),
                monitor_top(), strip):
        place(atlas, reg)
    d = ImageDraw.Draw(atlas)
    swatch = dict(drive=C["drive"], band=C["band"], bezel=C["bezel"], handle=C["handle"], monitor=C["monitor"],
                  frame=C["frame"], rear=C["rear"], disk=C["disk"], lit=rgb(L.COLOURS["lit"]), dark=C["dark"],
                  hub=(214, 210, 200), knob=shade(C["handle"], 0.18))
    for name, colour in swatch.items():
        x, y = L.DEVICE_SWATCHES[name]
        d.rectangle([x - 18, y - 18, x + 17, y + 17], fill=colour)
    path = os.path.join(out, "c64_devices.png")
    atlas.save(path, optimize=True)
    print(path)


# ---- The screens -----------------------------------------------------------------------------------------------------
# The C64's 16 colours (VICE's, after Pepto's measurements of the VIC-II).

PALETTE = ["#000000", "#FFFFFF", "#68372B", "#70A4B2", "#6F3D86", "#588D43", "#352879", "#B8C76F",
           "#6F4F25", "#433900", "#9A6759", "#444444", "#6C6C6C", "#9AD284", "#6C5EB5", "#959595"]
(BLACK, WHITE_, RED, CYAN, PURPLE, GREEN, BLUE, YELLOW, ORANGE, BROWN, PINK, DARK_GREY, GREY, LIGHT_GREEN,
 LIGHT_BLUE, LIGHT_GREY) = range(16)
FLAT = [c for h in PALETTE for c in rgb(h)] + [0] * (768 - 48)

# A character set in the C64's manner, 8 x 8: upright strokes two pixels wide, the rest one.
GLYPHS = {
    "A": ["...##...", "..####..", ".##..##.", ".######.", ".##..##.", ".##..##.", ".##..##."],
    "B": [".#####..", ".##..##.", ".##..##.", ".#####..", ".##..##.", ".##..##.", ".#####.."],
    "C": ["..####..", ".##..##.", ".##.....", ".##.....", ".##.....", ".##..##.", "..####.."],
    "D": [".####...", ".##.##..", ".##..##.", ".##..##.", ".##..##.", ".##.##..", ".####..."],
    "E": [".######.", ".##.....", ".##.....", ".####...", ".##.....", ".##.....", ".######."],
    "F": [".######.", ".##.....", ".##.....", ".####...", ".##.....", ".##.....", ".##....."],
    "G": ["..####..", ".##..##.", ".##.....", ".##.###.", ".##..##.", ".##..##.", "..####.."],
    "H": [".##..##.", ".##..##.", ".##..##.", ".######.", ".##..##.", ".##..##.", ".##..##."],
    "I": ["..####..", "...##...", "...##...", "...##...", "...##...", "...##...", "..####.."],
    "J": ["...####.", "....##..", "....##..", "....##..", "....##..", ".##.##..", "..###..."],
    "K": [".##..##.", ".##.##..", ".####...", ".###....", ".####...", ".##.##..", ".##..##."],
    "L": [".##.....", ".##.....", ".##.....", ".##.....", ".##.....", ".##.....", ".######."],
    "M": [".##...##", ".###.###", ".#######", ".##.#.##", ".##...##", ".##...##", ".##...##"],
    "N": [".##..##.", ".###.##.", ".######.", ".######.", ".##.###.", ".##..##.", ".##..##."],
    "O": ["..####..", ".##..##.", ".##..##.", ".##..##.", ".##..##.", ".##..##.", "..####.."],
    "P": [".#####..", ".##..##.", ".##..##.", ".#####..", ".##.....", ".##.....", ".##....."],
    "Q": ["..####..", ".##..##.", ".##..##.", ".##..##.", ".##..##.", "..####..", "....###."],
    "R": [".#####..", ".##..##.", ".##..##.", ".#####..", ".####...", ".##.##..", ".##..##."],
    "S": ["..####..", ".##..##.", ".##.....", "..####..", ".....##.", ".##..##.", "..####.."],
    "T": [".######.", "...##...", "...##...", "...##...", "...##...", "...##...", "...##..."],
    "U": [".##..##.", ".##..##.", ".##..##.", ".##..##.", ".##..##.", ".##..##.", "..####.."],
    "V": [".##..##.", ".##..##.", ".##..##.", ".##..##.", ".##..##.", "..####..", "...##..."],
    "W": [".##...##", ".##...##", ".##...##", ".##.#.##", ".#######", ".###.###", ".##...##"],
    "X": [".##..##.", ".##..##.", "..####..", "...##...", "..####..", ".##..##.", ".##..##."],
    "Y": [".##..##.", ".##..##.", ".##..##.", "..####..", "...##...", "...##...", "...##..."],
    "Z": [".######.", ".....##.", "....##..", "...##...", "..##....", ".##.....", ".######."],
    "0": ["..####..", ".##..##.", ".##.###.", ".###.##.", ".##..##.", ".##..##.", "..####.."],
    "1": ["...##...", "...##...", "..###...", "...##...", "...##...", "...##...", ".######."],
    "2": ["..####..", ".##..##.", ".....##.", "....##..", "..##....", ".##.....", ".######."],
    "3": ["..####..", ".##..##.", ".....##.", "...###..", ".....##.", ".##..##.", "..####.."],
    "4": [".....##.", "....###.", "...####.", ".##..##.", ".#######", ".....##.", ".....##."],
    "5": [".######.", ".##.....", ".#####..", ".....##.", ".....##.", ".##..##.", "..####.."],
    "6": ["..####..", ".##..##.", ".##.....", ".#####..", ".##..##.", ".##..##.", "..####.."],
    "7": [".######.", ".##..##.", "....##..", "...##...", "...##...", "...##...", "...##..."],
    "8": ["..####..", ".##..##.", ".##..##.", "..####..", ".##..##.", ".##..##.", "..####.."],
    "9": ["..####..", ".##..##.", ".##..##.", "..#####.", ".....##.", ".##..##.", "..####.."],
    "*": ["........", ".##..##.", "..####..", "########", "..####..", ".##..##.", "........"],
    '"': [".##..##.", ".##..##.", ".##..##.", "........", "........", "........", "........"],
    ".": ["........", "........", "........", "........", "........", "...##...", "...##..."],
    ",": ["........", "........", "........", "........", "........", "...##...", "...##...", "..##...."],
    ":": ["........", "........", "...##...", "........", "........", "...##...", "........"],
    "-": ["........", "........", "........", ".######.", "........", "........", "........"],
    "!": ["...##...", "...##...", "...##...", "...##...", "........", "........", "...##..."],
    "(": ["....##..", "...##...", "..##....", "..##....", "..##....", "...##...", "....##.."],
    ")": ["..##....", "...##...", "....##..", "....##..", "....##..", "...##...", "..##...."],
}
_MASKS = {}


def glyph(ch):
    """A character's 8 x 8 mask."""
    if ch not in _MASKS:
        mask = Image.new("L", (8, 8), 0)
        for y, row in enumerate(GLYPHS.get(ch, [])):
            for x, bit in enumerate(row):
                if bit == "#":
                    mask.putpixel((x, y), 255)
        _MASKS[ch] = mask
    return _MASKS[ch]


def paper(colour, size=(320, 200)):
    img = Image.new("P", size, colour)
    img.putpalette(FLAT)
    return img


def chars(img, col, row, text, ink, background=None):
    """Text in character cells, from (col, row): ink, on background if given."""
    for k, ch in enumerate(text):
        x, y = (col + k) * 8, row * 8
        if background is not None:
            img.paste(background, (x, y, x + 8, y + 8))
        img.paste(ink, (x, y, x + 8, y + 8), glyph(ch))


BOOT = ["", "    **** COMMODORE 64 BASIC V2 ****", "", " 64K RAM SYSTEM  38911 BASIC BYTES FREE", "", "READY."]


def text_screen(lines, cursor=None):
    """The C64's text screen: lines from the top in light blue on blue, the cursor (a solid block) at (col, row) if
    given; with its light blue border."""
    img = paper(BLUE)
    for row, line in enumerate(lines):
        chars(img, 0, row, line, LIGHT_BLUE)
    if cursor is not None:
        col, row = cursor
        img.paste(LIGHT_BLUE, (col * 8, row * 8, col * 8 + 8, row * 8 + 8))
    return img, LIGHT_BLUE


def frame(picture, border):
    """The C64's whole picture: the paper in its border, a colour or one for each of its 272 lines."""
    img = paper(BLACK, L.FRAME_PX)
    if isinstance(border, int):
        img.paste(border, (0, 0) + L.FRAME_PX)
    else:
        d = ImageDraw.Draw(img)
        for y, colour in enumerate(border):
            d.line([(0, y), (L.FRAME_PX[0] - 1, y)], fill=colour)
    if picture is not None:
        img.paste(picture, L.PAPER_AT)
    return img


# ---- The loading picture and the title -------------------------------------------------------------------------------

def nearest(colour, indices):
    r, g, b = colour
    return min(indices, key=lambda i: (rgb(PALETTE[i])[0] - r) ** 2 * 3 + (rgb(PALETTE[i])[1] - g) ** 2 * 4
               + (rgb(PALETTE[i])[2] - b) ** 2 * 2)


def multicolour(img, background=BLACK):
    """A picture in multicolour bitmap mode: 160 x 200 wide pixels from img (cropped to the screen's shape), each
    character cell of 4 x 8 in the background colour and at most three others; doubled to 320 x 200."""
    small = ImageOps.fit(img.convert("RGB"), (320, 200), Image.LANCZOS).resize((160, 200), Image.LANCZOS)
    small = ImageEnhance.Color(ImageEnhance.Contrast(small).enhance(1.15)).enhance(1.25)   # as an artist's would
    pal = Image.new("P", (1, 1))
    flat = FLAT[:48]
    pal.putpalette(flat + flat[:3] * 240)                  # the rest black, which the quantiser may pick: index 0
    dithered = small.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG)
    src = small.load()
    out = paper(background, (160, 200))
    px, dx = out.load(), dithered.load()
    for y in range(200):
        for x in range(160):
            if dx[x, y] > 15:
                dx[x, y] = BLACK
    for cy in range(25):
        for cx in range(40):
            cells = [(x, y) for y in range(cy * 8, cy * 8 + 8) for x in range(cx * 4, cx * 4 + 4)]
            counts = {}
            for x, y in cells:
                i = dx[x, y]
                if i != background:
                    counts[i] = counts.get(i, 0) + 1
            allowed = [background] + sorted(counts, key=counts.get, reverse=True)[:3]
            for x, y in cells:
                i = dx[x, y]
                px[x, y] = i if i in allowed else nearest(src[x, y], allowed)
    return out.resize((320, 200), Image.NEAREST)


def picture(made_up):
    """The game's loading picture: its key art round the submarine and the anglerfish, its logo over the top."""
    from arcade_print import Game
    stem, system, _ = L.MADE_UP
    game = Game(stem, made_up, system)
    art = game.keyart.convert("RGB")
    w = art.width
    crop = art.crop((0, 470, w, 470 + round(w / 1.6))).convert("RGBA")
    k = crop.width * 0.78 / game.logo.width
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    crop.alpha_composite(logo, ((crop.width - logo.width) // 2, round(crop.height * 0.04)))
    return multicolour(crop.convert("RGB"))


def loading(full, cells):
    """The picture as the loader puts it in: cells (of 1000) character cells of its bitmap, left to right and top to
    bottom, each whole (the bitmap keeps a cell's eight bytes together); black where it hasn't reached."""
    img = paper(BLACK)
    for i in range(min(1000, cells)):
        x, y = (i % 40) * 8, (i // 40) * 8
        img.paste(full.crop((x, y, x + 8, y + 8)), (x, y))
    return img


def stripes(f):
    """The border while the loader reads: bands of colour that change every frame, as the turbo loaders' did."""
    rng = random.Random(f * 31 + 7)
    out, y = [], 0
    while y < L.FRAME_PX[1]:
        h = rng.choice((2, 3, 4, 6, 8, 12))
        out += [rng.choice((LIGHT_BLUE, BLUE, CYAN, WHITE_, PURPLE, DARK_GREY))] * h
        y += h
    return out[:L.FRAME_PX[1]]


def title(full, f):
    """The picture loaded, with PRESS F1 TO START blinking in a black band at its foot."""
    img = full.copy()
    img.paste(BLACK, (0, 184, 320, 200))
    if (f // 8) % 3 != 2:
        chars(img, 11, 23, "PRESS F1 TO START", WHITE_)
    return img


# ---- The game --------------------------------------------------------------------------------------------------------
# Drawn in hires pixels (320 x 200) with multicolour's wide pixels (2 x 1), its sprites double size as the C64 can draw
# them. t is the frame since the game started.

SUB = ["......kk..........",
       ".....kyyk.........",
       "...kkkyykkkkk.....",
       "..kyyyyyyyyyyykk..",
       ".kyyywwyyyyyyyyyk.",
       "kyyyywcyyyyyyyyyyk",
       "kyyyyccyyyyyyyyyyk",
       ".kyyyyyyyyyyyyyyk.",
       "..kooookkkkkooook.",
       "...k..........k..."]
FISH = ["...rrrr..r",
        ".rrrrrrrrr",
        "rwrrrrrrr.",
        ".rrrrrrrrr",
        "...rrrr..r"]
FISH_FLAP = ["...rrrr...",
             ".rrrrrrr.r",
             "rwrrrrrrrr",
             ".rrrrrrr.r",
             "...rrrr..."]
SPRITE_COLOURS = {"k": BLACK, "y": YELLOW, "w": WHITE_, "c": CYAN, "o": ORANGE, "r": PINK}
SCALE = 2                                    # the sprites' expansion: each pixel 2 x 2 of its own
SUB_X, SUB_NOSE = 30, 18 * 2 * SCALE         # the sub's left edge, and its nose from there (hires pixels)
TORPEDO_SPEED, FISH_SPEED, FLIGHT = 8, 3, 9  # pixels a frame; frames a torpedo flies to its hit


def sprite(img, rows, x, y, colours=SPRITE_COLOURS, scale=SCALE):
    """A sprite of wide pixels, its top left at (x, y), each pixel scale times larger each way."""
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c != ".":
                xx, yy = x + i * 2 * scale, y + j * scale
                if -2 * scale < xx < 320 and 0 <= yy < 200:
                    img.paste(colours[c], (max(0, xx), yy, min(320, xx + 2 * scale), min(200, yy + scale)))


def sub_y(t):
    return 92 + round(6 * math.sin(t / 9.0))


def sub_x(t):
    """The sub glides in from the left as the game starts."""
    return round(-80 + (SUB_X + 80) * (1 - (1 - min(1.0, t / 16.0)) ** 2))


def shots():
    """Each torpedo: (fired, its height); its hit is FLIGHT frames after it leaves the tube, two after the press."""
    return [(fire - L.GAME, sub_y(fire - L.GAME) + 10) for fire in L.FIRE]


def fish_at(t):
    """The fish swimming in from the right: (x, y, its hit's frame or None)."""
    out = []
    hit_x = SUB_X + SUB_NOSE + TORPEDO_SPEED * FLIGHT
    for fired, y in shots():
        hit = fired + 2 + FLIGHT
        out.append((hit_x + FISH_SPEED * (hit - t), y - 5, hit))
    for x0, y, phase in ((360, 58, 0.0), (470, 146, 1.7), (560, 70, 3.1)):   # others, out of the line of fire
        out.append((x0 - FISH_SPEED * t, y + round(4 * math.sin(t / 6.0 + phase)), None))
    return out


def seabed(img, scroll):
    """The sea floor: rocks, with seaweed and coral, scrolling past two pixels a frame."""
    d = ImageDraw.Draw(img)
    for x in range(0, 320, 2):
        u = x + scroll
        h = int(178 + 7 * math.sin(u / 29.0) + 4 * math.sin(u / 11.0 + 1.3) + 2 * math.sin(u / 5.0))
        d.rectangle([x, h, x + 1, 199], fill=BROWN)
        d.rectangle([x, h, x + 1, h + 1], fill=ORANGE)
        if (u // 2) % 7 == 0:
            d.rectangle([x, h + 6, x + 1, h + 7], fill=DARK_GREY)
    for k in range(-1, 9):                                     # seaweed every 46 pixels, swaying
        base = k * 46 - scroll % 46
        top = 146 + (k * 13 + scroll // 46 * 13) % 20
        for y in range(top, 188, 2):
            sway = round(3 * math.sin(y / 7.0 + scroll / 9.0)) // 2 * 2
            d.rectangle([base + sway, y, base + sway + 3, y + 1], fill=GREEN if y % 6 else LIGHT_GREEN)
    for k in range(-1, 5):                                     # coral
        cx = k * 83 + 30 - scroll % 83
        for dx, dy in ((0, 0), (2, -2), (-2, -2), (4, -4), (-4, -3), (2, -6), (-2, -7), (6, -7), (-6, -6)):
            d.rectangle([cx + dx, 179 + dy, cx + dx + 1, 180 + dy], fill=PINK if dy % 4 else RED)


def ruins(img, scroll):
    """Ruins far off, columns with their capitals and a broken arch between, a pixel a frame."""
    d = ImageDraw.Draw(img)
    for k in range(-1, 6):
        x = k * 72 - scroll % 72
        n = k + scroll // 72
        h = 44 + n % 3 * 16
        base = 176
        if n % 4 != 3:
            d.rectangle([x, base - h, x + 9, base], fill=DARK_GREY)              # the shaft, lit at its left
            d.rectangle([x, base - h, x + 1, base], fill=GREY)
            d.rectangle([x - 3, base - h - 5, x + 12, base - h], fill=DARK_GREY)   # its capital
            d.rectangle([x - 3, base - h - 5, x + 12, base - h - 4], fill=GREY)
        else:                                                   # a broken one
            d.rectangle([x, base - 18, x + 9, base], fill=DARK_GREY)
            d.polygon([(x, base - 18), (x + 9, base - 24), (x + 9, base - 18)], fill=DARK_GREY)
        if n % 3 == 0:                                          # an arch to the next
            top = base - h - 5
            d.rectangle([x + 12, top, x + 60, top + 8], fill=DARK_GREY)
            d.ellipse([x + 16, top + 4, x + 56, top + 30], fill=BLUE)
            d.rectangle([x + 16, top + 17, x + 56, top + 30], fill=BLUE)


def explosion(img, x, y, k):
    """A torpedo's hit, k frames on (0 to 11)."""
    d = ImageDraw.Draw(img)
    colours = (WHITE_, YELLOW, YELLOW, ORANGE, ORANGE, RED, RED, DARK_GREY, DARK_GREY, DARK_GREY, BLUE, BLUE)
    r = 4 + k * 3
    rng = random.Random(x * 7 + y)
    for a in range(14):
        ang = a * math.pi / 7 + rng.random() * 0.4
        px, py = round(x + r * math.cos(ang)) // 2 * 2, round(y + r * 0.7 * math.sin(ang))
        d.rectangle([px, py, px + 3, py + 1], fill=colours[k])
    if k < 6:
        d.ellipse([x - 10 + k, y - 7 + k // 2, x + 10 - k, y + 7 - k // 2], fill=colours[k])


def game(t):
    """The game t frames after it started."""
    img = paper(BLUE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 319, 15], fill=BLACK)
    for y in range(16, 46):                                    # the light near the surface, dithered into the deep
        for x in range(0, 320, 2):
            if y < 30 or (x // 2 + y) % 2 == 0 and y < 38 or (x // 2 + y) % 4 == 0:
                d.rectangle([x, y, x + 1, y], fill=LIGHT_BLUE)
    for x in range(0, 320, 2):                                 # the waves
        y = 17 + round(1.5 * math.sin((x + t * 3) / 14.0))
        d.rectangle([x, 16, x + 1, y], fill=CYAN)
        d.rectangle([x, y, x + 1, y], fill=WHITE_)
    for k in range(3):                                         # shafts of light
        x0 = (k * 120 + t) % 400 - 60
        for y in range(46, 132, 2):
            x = x0 + (y - 46) // 2
            if (y // 2) % 2 == 0:
                d.rectangle([x // 2 * 2, y, x // 2 * 2 + 5, y], fill=LIGHT_BLUE)
    ruins(img, t)
    for k in range(9):                                         # a shoal far off
        x = (120 + k * 9 + (k % 3) * 5 - t) % 360 - 20
        y = 60 + (k % 4) * 5 + round(2 * math.sin(t / 5.0 + k))
        d.rectangle([x // 2 * 2, y, x // 2 * 2 + 3, y], fill=CYAN)
    seabed(img, t * 2)
    rng = random.Random(64)
    for k in range(14):                                        # bubbles rising
        bx = rng.randrange(0, 320)
        by = 190 - (t * (1 + k % 3) + rng.randrange(0, 160)) % 170
        bx = (bx - t * 2) % 320 // 2 * 2
        d.rectangle([bx, by, bx + 1, by], fill=CYAN if k % 2 else WHITE_)
    score = 0
    for fired, y in shots():                                   # the torpedoes and their hits
        hit = fired + 2 + FLIGHT
        if fired + 2 <= t < hit:
            x = SUB_X + SUB_NOSE + TORPEDO_SPEED * (t - fired - 2)
            d.rectangle([x, y, x + 13, y + 2], fill=LIGHT_GREY)
            d.rectangle([x + 14, y, x + 15, y + 2], fill=YELLOW)
            d.rectangle([x - 8, y, x - 2, y + 2], fill=WHITE_ if (t // 2) % 2 else CYAN)
        if t >= hit:
            score += 100
    for x, y, hit in fish_at(t):
        if hit is not None and t >= hit:
            if t < hit + 12:
                explosion(img, x + 10, y + 5, t - hit)
            continue
        if -40 < x < 320:
            sprite(img, FISH if (t // 4) % 2 else FISH_FLAP, x // 2 * 2, y)
    sx, sy = sub_x(t), sub_y(t)
    sprite(img, SUB, sx, sy)
    prop = WHITE_ if (t // 2) % 2 else CYAN                    # the propeller turning, bubbles behind it
    d.rectangle([sx - 6, sy + 8, sx - 3, sy + 13], fill=prop)
    if t % 4 < 2:
        d.rectangle([sx - 12, sy + 6, sx - 11, sy + 7], fill=WHITE_)
    chars(img, 1, 0, f"SCORE {score:06d}", WHITE_)
    chars(img, 26, 0, "HI 050000", YELLOW)
    for k in range(3):                                         # lives
        x = 4 + k * 28
        d.rectangle([x, 10, x + 9, 13], fill=YELLOW)
        d.rectangle([x + 3, 8, x + 5, 9], fill=YELLOW)
    return img


# ---- The glass -------------------------------------------------------------------------------------------------------

_GLASS = {}


def _glass_masks():
    """The raster's rounded corners, the vignette and the sheen: the same in every frame, so made once."""
    if not _GLASS:
        cw, ch = L.SCREEN_PX
        x0, y0 = L.RASTER_AT
        rw, rh = cw - 2 * x0, ch - 2 * y0
        mask = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x0 + rw - 1, y0 + rh - 1], radius=rw * 0.035, fill=255)
        _GLASS["raster"] = mask.filter(ImageFilter.GaussianBlur(1.5))
        vignette = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(vignette).rounded_rectangle([x0 + rw * 0.05, y0 + rh * 0.06, x0 + rw * 0.95, y0 + rh * 0.94],
                                                   radius=rw * 0.14, fill=255)
        _GLASS["vignette"] = vignette.filter(ImageFilter.GaussianBlur(rw * 0.07))
        sheen = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(sheen).ellipse([-cw * 0.3, -ch * 0.6, cw * 0.75, ch * 0.42], fill=26)
        _GLASS["sheen"] = sheen.filter(ImageFilter.GaussianBlur(cw * 0.08))
        _GLASS["tube"] = Image.new("RGB", (cw, ch), (18, 20, 22))
        _GLASS["black"] = Image.new("RGB", (cw, ch), (0, 0, 0))
        _GLASS["white"] = Image.new("RGB", (cw, ch), (255, 255, 255))
    return _GLASS


def glass(picture, brightness=1.0):
    """The 1702's glass (SCREEN_PX): the C64's picture (FRAME_PX, or None for no signal) doubled into its raster, a
    CRT's soft dots, the vignette and the sheen."""
    g = _glass_masks()
    image = g["tube"].copy()
    if picture is not None:
        raster = picture.convert("RGB").resize((L.FRAME_PX[0] * 2, L.FRAME_PX[1] * 2), Image.NEAREST)
        raster = raster.filter(ImageFilter.GaussianBlur(0.7))
        if brightness < 1.0:
            raster = Image.blend(Image.new("RGB", raster.size, (18, 20, 22)), raster, brightness)
        layer = g["tube"].copy()
        layer.paste(raster, L.RASTER_AT)
        image = Image.composite(layer, image, g["raster"])
    image = Image.composite(image, Image.blend(image, g["black"], 0.35), g["vignette"])
    return Image.composite(g["white"], image, g["sheen"])


def boot_glass():
    """The start-up screen on the glass: the video's first and last frames, and the still shown when none plays."""
    picture, border = text_screen(BOOT, (0, 6))
    return glass(frame(picture, border))


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    devices_atlas(made_up, out)
    path = os.path.join(out, "c64_screen.png")
    boot_glass().save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
