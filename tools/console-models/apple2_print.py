"""The Apple IIe's, its Disk II drives' and its Monitor II's printing, for the console theme's Apple II model
(tools/console-models/apple2.py).

Draws its two atlases, their regions as apple2_layout.py places them. apple2_print.png: the computer's top in front of
the drives, seen from above, in millimetres as the model's planar UVs map it (each key's top with its legend, the
power light lit in the bottom row, the lid's seams and the apple //e badge), the two drives' front panels (DRIVE 1 and
DRIVE 2, the IN USE lights off, disk II and the rainbow apple), the monitor's control strip (its power light lit, the
switch, the badge), and the swatches small parts take their colour from. apple2_media.png: the screens, each the
glass's whole width and height, the Apple's 280 x 192 pixels in green phosphor round a dark border (the banner the
IIe shows looking for a disk; the title screen of a made-up game, Odyssey, two passes into loading, the hi-res lines
arriving every eighth line at a time, and whole), and the floppy's label side. Run it with the system Python (Pillow):

    python tools/console-models/apple2_print.py <out folder>

It writes apple2_print.png and apple2_media.png there.
"""

import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apple2_layout as L  # noqa: E402
from psp_print import ship  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
LEGEND = (58, 56, 52)
RAINBOW = [(97, 187, 70), (253, 184, 39), (245, 130, 31), (224, 58, 62), (150, 61, 151), (0, 157, 220)]
TOP_DEPTH = 250.0            # the top region's depth: the top in front of the drives
PHOSPHOR, DARK_GLASS = (88, 255, 120), (8, 20, 12)


def top_point(x, y):
    """A point of the computer's top (x from its middle, y back from its front) in the top region's millimetres."""
    return x + L.WIDTH / 2, TOP_DEPTH - y


def slope_top(points, h):
    """An (x, s) outline on the slope, raised h off it, in the top region's millimetres."""
    return [top_point(x, L.slope_point(s, h)[0]) for x, s in points]


# ---- The apple ---------------------------------------------------------------------------------------------------------

def apple(reg, cx, cy, h, fill=None, outline=None, width=0.3, rainbow=False):
    """Apple's apple, h tall, its middle at (cx, cy): the body with its bite and the leaf; striped like the rainbow
    logo, filled, or outlined."""
    mask = Image.new("L", reg.img.size, 0)
    d = ImageDraw.Draw(mask)
    w = h * 0.94
    d.ellipse(reg.box(cx - w / 2, cy - h * 0.3, cx + w * 0.04, cy + h / 2), fill=255)
    d.ellipse(reg.box(cx - w * 0.04, cy - h * 0.3, cx + w / 2, cy + h / 2), fill=255)
    d.ellipse(reg.box(cx - w * 0.13, cy + h * 0.41, cx + w * 0.13, cy + h * 0.56), fill=0)    # the dip at its foot
    d.ellipse(reg.box(cx + w * 0.3, cy - h * 0.1, cx + w * 0.68, cy + h * 0.28), fill=0)      # the bite
    d.ellipse(reg.box(cx - w * 0.2, cy - h * 0.38, cx + w * 0.12, cy - h * 0.2), fill=0)      # the dip at its top
    d.polygon([reg.p(cx + w * 0.02, cy - h * 0.34), reg.p(cx + w * 0.28, cy - h * 0.62),
               reg.p(cx + w * 0.06, cy - h * 0.5)], fill=255)                                  # the leaf
    if rainbow:
        bands = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
        db = ImageDraw.Draw(bands)
        top, bottom = cy - h * 0.62, cy + h / 2
        for k, colour in enumerate(RAINBOW):
            y0 = top + (bottom - top) * (0.0 if k == 0 else 0.33 + (k - 1) * 0.134)
            y1 = top + (bottom - top) * (0.33 + k * 0.134)
            db.rectangle(reg.box(cx - w, y0, cx + w, y1), fill=colour + (255,))
        reg.img.paste(bands, (0, 0), mask)
    elif fill is not None:
        reg.img.paste(fill, (0, 0), mask)
    if outline is not None:
        edge = mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 60 else 0)
        edge = edge.filter(ImageFilter.MaxFilter(max(1, round(width * reg.sx)) | 1))
        reg.img.paste(outline, (0, 0), edge)


# ---- The computer's top ------------------------------------------------------------------------------------------------

def key_top(reg, name, xu, row, wu, legend):
    x0, s0, x1, s1 = L.key_rect(xu, row, wu)
    outline = [(x0, s0), (x1, s0), (x1, s1), (x0, s1)]
    top = slope_top([(x0 + L.KEY_INSET, s0 + L.KEY_INSET), (x1 - L.KEY_INSET, s1 - L.KEY_INSET)], L.KEY_HEIGHT)
    (ax, ay), (bx, by) = top
    fill = rgb(L.COLOURS["top_keys"])
    if name == "light":                                    # a pale window, the green light glowing in it
        top = slope_top([(x0 + 1.0, s0 + 1.0), (x1 - 1.0, s1 - 1.0)], L.KEY_HEIGHT - 3.0)
        (ax, ay), (bx, by) = top
        reg.rect_(ax - 0.6, by - 0.6, bx + 0.6, ay + 0.6, (226, 224, 212))
        glow = reg.layer()
        cx, cy = (ax + bx) / 2, (ay + by) / 2
        ImageDraw.Draw(glow).rounded_rectangle(reg.box(cx - 5.5, cy - 3.5, cx + 5.5, cy + 3.5), radius=2 * reg.sx,
                                               fill=(110, 255, 90, 170))
        reg.over(glow.filter(ImageFilter.GaussianBlur(1.6 * reg.sx)))
        reg.rect_(cx - 3.2, cy - 1.4, cx + 3.2, cy + 1.4, (150, 255, 120), r=0.8)
        return
    reg.rect_(ax - 0.7, by - 0.7, bx + 0.7, ay + 0.7, fill)
    reg.rect_(ax + 1.0, by + 1.0, bx - 1.0, ay - 1.0, shade(fill, 0.05), r=1.4)
    if not legend:
        return
    if legend in ("open", "solid"):
        apple(reg, ax + 3.6, by + 3.6, 3.8, fill=LEGEND if legend == "solid" else None,
              outline=LEGEND if legend == "open" else None, width=0.35)
        return
    lines = legend.split("\n")
    if len(lines) == 1 and len(legend) == 1 and not legend.isalnum():
        reg.text(legend, "seguisym.ttf", 4.0, (ax + bx) / 2, (ay + by) / 2, LEGEND)
        return
    if len(lines) == 1 and len(legend) == 1:
        reg.text(legend, "arial.ttf", 3.4, ax + 2.6, by + 3.2, LEGEND)
        return
    size = 2.3 if max(len(line) for line in lines) > 2 else 3.0
    for k, line in enumerate(lines):
        reg.text(line, "arial.ttf", size, ax + 1.8, by + 2.6 + k * (size + 1.0), LEGEND, anchor="lm")


def badge(reg):
    (x0, y0), (x1, y1) = top_point(L.BADGE["x"][0], L.BADGE["y"][1]), top_point(L.BADGE["x"][1], L.BADGE["y"][0])
    split = top_point(L.BADGE["split"], 0.0)[0]
    plate = (78, 74, 70)
    reg.rect_(x0, y0, split - 1.2, y1, plate, r=1.4)
    reg.rect_(split + 1.2, y0, x1, y1, plate, r=1.4)
    h = y1 - y0
    apple(reg, x0 + 0.36 * h, (y0 + y1) / 2 + 0.4, h * 0.66, rainbow=True)
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(h * 0.62 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(x0 + 0.72 * h, (y0 + y1) / 2 + 0.6), "apple", font=f, fill=(226, 224, 218, 255),
                               anchor="lm")
    ImageDraw.Draw(layer).text(reg.p((split + x1) / 2 + 0.3, (y0 + y1) / 2 + 0.6), "//e", font=f,
                               fill=(226, 224, 218, 255), anchor="mm")
    reg.over(layer.transform(layer.size, Image.AFFINE, (1, 0.22, -0.22 * reg.p(0, (y0 + y1) / 2)[1], 0, 1, 0)))


def top():
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, TOP_DEPTH, CASE)
    seam = shade(CASE, -0.32)
    lx = L.SEAMS["lid_x"]
    (sx0, sy), (sx1, _) = top_point(-lx, L.SEAMS["lid_front"]), top_point(lx, L.SEAMS["lid_front"])
    reg.line([(sx0, sy), (sx1, sy)], seam, 0.5)
    for x in (-lx, lx):
        a, b = top_point(x, L.SEAMS["lid_front"]), top_point(x, TOP_DEPTH)
        reg.line([a, b], seam, 0.5)
    fold = top_point(0.0, L.SEAMS["lid_fold"])[1]
    reg.line([(sx0, fold), (sx1, fold)], shade(CASE, -0.08), 0.6)
    badge(reg)
    for name, xu, row, wu, legend in L.KEYS:
        key_top(reg, name, xu, row, wu, legend)
    x0, x1 = L.RESET["x"]
    s0, s1 = L.RESET["s"]
    (ax, ay), (bx, by) = slope_top([(x0 + 1.6, s0 + 1.6), (x1 - 1.6, s1 - 1.6)], 6.0)
    fill = rgb(L.COLOURS["top_keys"])
    reg.rect_(ax - 0.7, by - 0.7, bx + 0.7, ay + 0.7, fill)
    reg.rect_(ax + 0.8, by + 0.8, bx - 0.8, ay - 0.8, shade(fill, 0.05), r=1.0)
    reg.text("Reset", "arial.ttf", 2.2, (ax + bx) / 2, (ay + by) / 2, LEGEND)
    return reg


# ---- The drives and the monitor's strip --------------------------------------------------------------------------------

def drive_panel(n):
    w, h, _ = L.DRIVE["panel"]
    base = rgb(L.COLOURS["drive"])
    reg = Region(L.PRINT_REGIONS[f"drive{n}"], w, h, base)
    grain = reg.layer()
    d = ImageDraw.Draw(grain)
    for k in range(2600):                                   # the panel's fine texture
        x, y = (k * 7919) % (reg.img.size[0]), (k * 104729 // 3) % (reg.img.size[1])
        d.point((x, y), fill=(255, 255, 255, 10 + k % 14))
    reg.over(grain)

    def at(x, z):
        return x + w / 2, h - z
    reg.text("DRIVE", "arial.ttf", 3.0, *at(46.0, 52.5), (214, 214, 212), anchor="rm")
    reg.text(str(n), "arial.ttf", 6.0, *at(52.5, 53.2), (214, 214, 212))
    lx, lz, r = L.DRIVE["light"]
    reg.text("IN USE", "arial.ttf", 2.6, *at(lx - 4.6, lz), (214, 214, 212), anchor="rm")
    ax, ay = at(lx - 3.6, lz)
    reg.poly([(ax, ay - 1.2), (ax + 2.0, ay), (ax, ay + 1.2)], (214, 214, 212))
    reg.circle(*at(lx, lz), r + 0.5, (16, 16, 18))
    reg.circle(*at(lx, lz), r, (92, 22, 20))
    layer = reg.layer()
    f = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(8.6 * reg.sx)))
    ImageDraw.Draw(layer).text(reg.p(*at(-66.0, 5.6)), "disk", font=f, fill=(230, 230, 228, 255), anchor="ls")
    reg.over(layer)
    reg.rect_(*at(-43.5, 12.2), *at(-42.3, 5.6), (230, 230, 228))
    reg.rect_(*at(-41.2, 12.2), *at(-40.0, 5.6), (230, 230, 228))
    ax, ay = at(47.0, 14.0)
    apple(reg, ax, ay, 15.0, rainbow=True)
    return reg


def strip():
    w, h = L.MONITOR["strip"], L.MONITOR["profile"][-1][1]
    reg = Region(L.PRINT_REGIONS["strip"], w, h, CASE)

    def at(x, z):
        return x, h - z
    reg.rect_(*at(1.0, h - 2.0), *at(w - 1.0, 2.0), shade(CASE, 0.03), r=2.0)
    glow = reg.layer()
    gx, gy = at(w / 2 + 6.0, h - 9.0)
    ImageDraw.Draw(glow).ellipse(reg.box(gx - 5.0, gy - 3.0, gx + 5.0, gy + 3.0), fill=(90, 255, 110, 150))
    reg.over(glow.filter(ImageFilter.GaussianBlur(1.4 * reg.sx)))
    reg.rect_(gx - 2.6, gy - 1.2, gx + 2.6, gy + 1.2, (160, 255, 150), r=0.6)
    cx, cy = at(w / 2, h - 26.0)
    reg.circle(cx, cy, 6.5, shade(CASE, -0.12))
    reg.circle(cx, cy, 5.5, shade(CASE, 0.04))
    reg.circle(cx, cy, 2.6, outline=shade(CASE, -0.5), width=0.4)
    cx, cy = at(w / 2, 150.0)
    reg.circle(cx, cy, 6.5, shade(CASE, -0.12))
    reg.circle(cx, cy, 5.5, shade(CASE, 0.04))
    reg.rect_(cx - 2.6, cy - 0.3, cx + 2.6, cy + 0.3, shade(CASE, -0.5))
    bx, by = at(w / 2, 26.0)
    reg.rect_(bx - 8.0, by - 9.5, bx + 8.0, by + 9.5, (246, 244, 236), r=1.2, outline=shade(CASE, -0.2), width=0.3)
    apple(reg, bx, by + 0.6, 12.5, rainbow=True)
    return reg


def print_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), drive_panel(1), drive_panel(2), strip()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("bezel", rgb(L.COLOURS["bezel"])), ("dark", rgb(L.COLOURS["dark"])), ("lit", (255, 60, 44)),
                         ("plate", rgb(L.COLOURS["plate"])), ("green", (120, 255, 110)),
                         ("drive", rgb(L.COLOURS["drive"]))):
        x, y = L.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "apple2_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -------------------------------------------------------------------------------------------------------

FONT = ImageFont.truetype(FONTS + "consolab.ttf", 9)


def text_screen(lines):
    """The 40-column text screen: (row, column, text) in 7 x 8 cells, lit where the characters are."""
    img = Image.new("1", (280, 192), 0)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    for row, col, text in lines:
        for k, ch in enumerate(text):
            d.text((col * 7 + k * 7 + 3.5, row * 8 + 4), ch, font=FONT, fill=1, anchor="mm")
    return img


def title_screen():
    """Odyssey's title screen in hi-res, one bit a pixel: ODYSSEY large over a ringed planet, the ship, stars, and
    PRESS SPACE under them."""
    img = Image.new("1", (280, 192), 0)
    d = ImageDraw.Draw(img)
    for k in range(70):
        x, y = (k * 7919) % 280, (k * 104729 // 7) % 192
        d.point((x, y), fill=1)
        if k % 9 == 0:
            d.point([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], fill=1)
    big = ImageFont.truetype(FONTS + "ariblk.ttf", 34)
    d.fontmode = "1"
    d.text((140, 30), "ODYSSEY", font=big, fill=1, anchor="mm")
    d.rectangle([30, 52, 250, 53], fill=1)
    d.ellipse([168, 82, 236, 150], outline=1, width=2)
    for k in range(5):                                       # the planet's bands
        y = 96 + k * 11
        d.arc([170, y - 30, 234, y + 6], 20, 160, fill=1)
    d.arc([148, 104, 256, 128], 160, 380, fill=1, width=2)   # its ring
    ship(d, 92, 118, 2.2, 1, 1)
    d.line([(40, 118), (62, 118)], fill=1)
    d.line([(46, 112), (64, 112)], fill=1)
    d.line([(46, 124), (64, 124)], fill=1)
    small = ImageFont.truetype(FONTS + "consolab.ttf", 9)
    d.text((140, 172), "PRESS SPACE TO LAUNCH", font=small, fill=1, anchor="mm")
    return img


def passes(img, n):
    """The hi-res picture n eighths loaded: memory in order fills every eighth line first, then the next, and so on."""
    out = Image.new("1", img.size, 0)
    for y in range(img.size[1]):
        if y % 8 < n:
            out.paste(img.crop((0, y, img.size[0], y + 1)), (0, y))
    return out


def phosphor(bits):
    """A screen region: the one-bit picture in green phosphor in the raster, glowing, with scanlines, round a dark
    border."""
    w, h = L.SCREEN_PX
    rw, rh = L.RASTER
    lit = bits.convert("L").resize((rw, rh), Image.NEAREST)
    raster = Image.new("RGB", (rw, rh), DARK_GLASS)
    raster.paste(PHOSPHOR, (0, 0), lit)
    glow = Image.new("RGB", (rw, rh), (0, 0, 0))
    glow.paste((30, 120, 55), (0, 0), lit.filter(ImageFilter.GaussianBlur(3)))
    raster = ImageChops.add(raster, glow)
    scan = Image.new("L", (rw, rh), 255)
    ds = ImageDraw.Draw(scan)
    for y in range(1, rh, 2):
        ds.line([(0, y), (rw, y)], fill=200)
    raster = Image.composite(raster, Image.new("RGB", (rw, rh), (0, 0, 0)), scan)
    screen = Image.new("RGB", (w, h), (6, 12, 8))
    screen.paste(raster, ((w - rw) // 2, (h - rh) // 2))
    return screen


def disk():
    """The floppy's label side, looking down on it, the edge that goes in first at the top: the black jacket, the
    hub's ring, the index hole, the head's slot, the write-protect notch, and Odyssey's label along the near edge."""
    x, y, w, h = L.MEDIA_REGIONS["disk"]
    reg = Region((x, y, w, h), L.DISK["size"], L.DISK["size"], (24, 24, 26))
    s = L.DISK["size"]
    c = s / 2
    reg.circle(c, c, 19.0, (60, 60, 64))
    reg.circle(c, c, 14.5, (150, 120, 70))
    reg.circle(c, c, 14.0, (14, 14, 16))
    reg.circle(c + 25.0, c - 8.0, 2.4, (14, 14, 16))
    reg.rect_(c - 6.0, 8.0, c + 6.0, c - 22.0, (100, 70, 40), r=6.0)
    reg.rect_(c - 5.0, 9.0, c + 5.0, c - 23.0, (60, 40, 22), r=5.0)
    reg.rect_(s - 6.0, s - 46.0, s, s - 40.0, (10, 10, 12))
    reg.rect_(10.0, s - 34.0, s - 30.0, s - 8.0, (244, 242, 234), r=1.0)
    reg.rect_(10.0, s - 34.0, s - 30.0, s - 28.0, (206, 34, 40), r=1.0)
    reg.text("ODYSSEY", "arialbd.ttf", 7.0, (s - 20.0) / 2, s - 17.5, (34, 34, 38))
    reg.text("DOS 3.3  DISK 1", "arial.ttf", 3.2, (s - 20.0) / 2, s - 11.5, (80, 80, 84))
    return reg


def media_atlas(out):
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (0, 0, 0))
    title = title_screen()
    screens = {"banner": text_screen([(0, 15, "Apple //e")]), "pass2": passes(title, 2), "pass5": passes(title, 5),
               "title": title}
    for name, bits in screens.items():
        x, y, _, _ = L.MEDIA_REGIONS[name]
        image.paste(phosphor(bits), (x, y))
    disk().paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", (6, 12, 8)), ("jacket", (24, 24, 26))):
        x, y = L.MEDIA_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "apple2_media.png")
    image.save(path, optimize=True)
    print(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1])
