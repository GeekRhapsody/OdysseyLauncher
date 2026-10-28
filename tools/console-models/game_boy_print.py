"""The Game Boy's and Game Boy Color's printing and lenses, for the console theme's cards (game_boy.py), from
game_boy_layout.py's measurements.

Writes into a folder, for each of `gb` and `gbc`:
- <kind>_print.png: the shell's printing, each region seen square on (game_boy_layout's PRINT_REGIONS): the face (its
  legends, the wells round the controls, the speaker; not the lens, which is the screen), the back (the cartridge's
  bay, the DMG's label panel, ribs and battery cover, or the Color's batteries' bulge), the ends, the top and the
  bottom; the D-pad's top (and the Color's B and A with their letters); and the plain colours' swatches.
- <kind>_cart.png: the cartridge's two sides: its label (a made-up game from tools/made-up-games's library: its key
  art and its logo) and its other side.
- <kind>_screen.png: the lens switched off, at its video's size: the texture of the card's `video` material, and the
  first and last frame of its video.

The lens's drawing and the composing of a frame of its video (the LCD's picture at two video pixels a dot, the light,
the lens's sheen) are shared with game_boy_video.py, which draws the cards' videos with them. Run it with the system
Python (Pillow):

    python tools/console-models/game_boy_print.py artifacts/made-up-games artifacts/gameboys

FONTS, SCALE, Face and rgb are psp_print.py's and wonderswan_print.py's too, so they stay as they are.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_boy_layout as L  # noqa: E402

SCALE = 16  # pixels per millimetre while drawing; each region is resampled to its size in the atlas
FONTS = "C:/Windows/Fonts/"


def rgb(hex_colour, scale=1.0):
    """A #RRGGBB colour as an (r, g, b, 255) tuple, each channel times scale (darker below 1)."""
    return tuple(max(0, min(255, round(int(hex_colour[i:i + 2], 16) * scale))) for i in (1, 3, 5)) + (255,)


def rounded_polygon(corners, radii, segments=12):
    """A convex polygon's outline (anticlockwise corners, in mm) with each corner rounded by its radius (as
    game_gear_print.py drew it, for Face.rounded)."""
    points = []
    n = len(corners)
    for i in range(n):
        cx, cv = corners[i]
        ax, av = corners[i - 1]
        bx, bv = corners[(i + 1) % n]
        ux, uv = ax - cx, av - cv
        wx, wv = bx - cx, bv - cv
        lu, lw = math.hypot(ux, uv), math.hypot(wx, wv)
        ux, uv, wx, wv = ux / lu, uv / lu, wx / lw, wv / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uv * wv))) / 2
        r = radii[i]
        t = r / math.tan(half)
        bx_, bv_ = ux + wx, uv + wv
        lb = math.hypot(bx_, bv_)
        ox, ov = cx + bx_ / lb * r / math.sin(half), cv + bv_ / lb * r / math.sin(half)
        p1 = (cx + ux * t - ox, cv + uv * t - ov)
        p2 = (cx + wx * t - ox, cv + wv * t - ov)
        a1, a2 = math.atan2(p1[1], p1[0]), math.atan2(p2[1], p2[0])
        while a2 < a1:
            a2 += 2 * math.pi
        for k in range(segments + 1):
            a = a1 + (a2 - a1) * k / segments
            points.append((ox + r * math.cos(a), ov + r * math.sin(a)))
    return points


class Face:
    """One region's canvas: x to the right and z up, in millimetres, over the region's box."""

    def __init__(self, mm, fill):
        self.x0, self.x1, self.z0, self.z1 = mm
        self.img = Image.new("RGBA", (round((self.x1 - self.x0) * SCALE), round((self.z1 - self.z0) * SCALE)), fill)
        self.draw = ImageDraw.Draw(self.img)

    def p(self, x, z):
        return ((x - self.x0) * SCALE, (self.z1 - z) * SCALE)

    def polygon(self, points, fill):
        self.draw.polygon([self.p(x, z) for x, z in points], fill=fill)

    def rounded(self, x0, x1, z0, z1, radii, fill):
        radii = radii if isinstance(radii, list) else [radii] * 4
        self.polygon(rounded_polygon([(x1, z0), (x1, z1), (x0, z1), (x0, z0)], radii, 16), fill)

    def circle(self, x, z, r, fill):
        cx, cy = self.p(x, z)
        self.draw.ellipse([cx - r * SCALE, cy - r * SCALE, cx + r * SCALE, cy + r * SCALE], fill=fill)

    def ring(self, x, z, r, width, fill):
        cx, cy = self.p(x, z)
        self.draw.ellipse([cx - r * SCALE, cy - r * SCALE, cx + r * SCALE, cy + r * SCALE], outline=fill,
                          width=max(1, round(width * SCALE)))

    def pill(self, x, z, length, width, degrees, fill):
        """A stadium length long and width wide, centred at (x, z), turned anticlockwise by degrees."""
        r = width / 2
        c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
        points = []
        for end, a0 in ((length / 2 - r, -90), (-(length / 2 - r), 90)):
            for k in range(13):
                a = math.radians(a0 + 180 * k / 12)
                u, v = end + r * math.cos(a), r * math.sin(a)
                points.append((x + u * c - v * s, z + u * s + v * c))
        self.polygon(points, fill)

    def line(self, x0, z0, x1, z1, width, fill):
        self.pill((x0 + x1) / 2, (z0 + z1) / 2, math.hypot(x1 - x0, z1 - z0) + width, width,
                  math.degrees(math.atan2(z1 - z0, x1 - x0)), fill)

    def text(self, s, font, cap_mm, x, z, fill, anchor="left", shear=0.0, degrees=0.0, stretch=1.0):
        """Text whose capitals are cap_mm high, its left edge (or centre, or right edge) at x and its middle at z.
        Returns its width in millimetres."""
        probe = ImageFont.truetype(FONTS + font, 200)
        left, top, right, bottom = probe.getbbox("H")
        size = max(1, int(200 * cap_mm * SCALE / (bottom - top)))
        face = ImageFont.truetype(FONTS + font, size)
        left, top, right, bottom = face.getbbox(s)
        pad = size
        layer = Image.new("RGBA", (right - left + 2 * pad, bottom - top + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((pad - left, pad - top), s, font=face, fill=fill)
        if stretch != 1.0:
            layer = layer.resize((int(layer.width * stretch), layer.height), Image.LANCZOS)
        if shear:
            layer = layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * layer.height / 2, 0, 1, 0),
                                    resample=Image.BICUBIC)
        if degrees:
            layer = layer.rotate(degrees, resample=Image.BICUBIC, expand=True)
        layer = layer.crop(layer.getbbox())
        cx, cy = self.p(x, z)
        offset = {"left": 0, "centre": layer.width / 2, "right": layer.width}[anchor]
        self.img.alpha_composite(layer, (int(cx - offset), int(cy - layer.height / 2)))
        return layer.width / SCALE

    def paste(self, image, x0, x1, z0, z1, resample=Image.LANCZOS):
        """An image stretched over the box (x0..x1, z0..z1)."""
        a, b = self.p(x0, z1)
        c, d = self.p(x1, z0)
        layer = image.convert("RGBA").resize((round(c - a), round(d - b)), resample)
        self.img.alpha_composite(layer, (round(a), round(b)))

    def glow(self, x, z, r, colour):
        """A lit light: a bright dot with a soft halo."""
        base = rgb(colour)
        for k in range(10, 0, -1):
            rr = r * (1 + 0.06 * k)  # the halo stays inside the light's 5 mm face
            alpha = int(255 * (1 - k / 11) ** 2 * 0.6)
            self.circle(x, z, rr, base[:3] + (alpha,))
        self.circle(x, z, r, base)
        self.circle(x - r * 0.3, z + r * 0.3, r * 0.35, (255, 255, 255, 200))


# ---- Drawing helpers -------------------------------------------------------------------------------------------------

def mixed(a, b, t):
    """Two #RRGGBB colours mixed, t of the way from a to b, as an RGBA tuple."""
    ca, cb = rgb(a), rgb(b)
    return tuple(round(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)) + (255,)


def text_width(s, font, cap_mm, stretch=1.0, shear=0.0):
    probe = Face((0.0, 1.0, 0.0, 1.0), (0, 0, 0, 0))
    return probe.text(s, font, cap_mm, 0.0, 0.5, (0, 0, 0, 255), stretch=stretch, shear=shear)


def fitted(face, s, font, cap_mm, x0, x1, z, fill, shear=0.0):
    """Text stretched across x0..x1, its middle at z."""
    stretch = (x1 - x0) / text_width(s, font, cap_mm, shear=shear)
    face.text(s, font, cap_mm, (x0 + x1) / 2, z, fill, anchor="centre", shear=shear, stretch=stretch)


def spaced(face, s, font, cap_mm, x0, x1, z, fill):
    """Text whose letters are spread out evenly across x0..x1 (wide tracking), its middle at z."""
    widths = [text_width(ch, font, cap_mm) if ch != " " else cap_mm * 0.45 for ch in s]
    gap = (x1 - x0 - sum(widths)) / max(1, len(s) - 1)
    x = x0
    for ch, w in zip(s, widths):
        if ch != " ":
            face.text(ch, font, cap_mm, x, z, fill)
        x += w + gap


def embossed(face, draw, colour, depth=0.12, light=1.1, dark=0.8, body=0.96):
    """A moulded shape: draw(dx, dz, fill) three times, its lit edge, its shadowed edge, then the shape."""
    draw(-depth, depth, rgb(colour, light))
    draw(depth, -depth, rgb(colour, dark))
    draw(0.0, 0.0, rgb(colour, body))


def embossed_text(face, s, font, cap_mm, x, z, colour, anchor="centre", **kw):
    embossed(face, lambda dx, dz, fill: face.text(s, font, cap_mm, x + dx, z + dz, fill, anchor=anchor, **kw), colour)


def stadium_points(x, z, length, width, degrees=0.0, n=12):
    r = width / 2
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    pts = []
    for end, a0 in ((length / 2 - r, -90), (-(length / 2 - r), 90)):
        for k in range(n + 1):
            a = math.radians(a0 + 180 * k / n)
            u, v = end + r * math.cos(a), r * math.sin(a)
            pts.append((x + u * c - v * s, z + u * s + v * c))
    return pts


def outline(face, points, width, fill):
    for a, b in zip(points, points[1:] + points[:1]):
        face.line(a[0], a[1], b[0], b[1], width, fill)


def cross_points(x, z, arm, half, r=0.0):
    pts = [(arm, -half), (arm, half), (half, half), (half, arm), (-half, arm), (-half, half), (-arm, half),
           (-arm, -half), (-half, -half), (-half, -arm), (half, -arm), (half, -half)]
    return [(x + px, z + pz) for px, pz in pts]


def grown(points, centre, amount):
    """Points pushed out from centre by amount (for a well round a convex-ish part)."""
    cx, cz = centre
    out = []
    for x, z in points:
        dx, dz = x - cx, z - cz
        d = math.hypot(dx, dz) or 1.0
        out.append((x + dx / d * amount, z + dz / d * amount))
    return out


def triangle(face, x, z, size, degrees, fill):
    """A small arrowhead pointing degrees anticlockwise from the right."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    pts = [(size * 0.6, 0.0), (-size * 0.4, size * 0.5), (-size * 0.4, -size * 0.5)]
    face.polygon([(x + px * c - pz * s, z + px * s + pz * c) for px, pz in pts], fill)


def ribs(face, x0, x1, z0, z1, step, colour, light=1.08, dark=0.84, width=0.45):
    """Horizontal ribs: each a lit line over a shadowed one."""
    z = z1 - step / 2
    while z > z0:
        face.line(x0, z + width * 0.5, x1, z + width * 0.5, width, rgb(colour, light))
        face.line(x0, z - width * 0.5, x1, z - width * 0.5, width, rgb(colour, dark))
        z -= step


def screw(face, x, z, colour):
    face.circle(x, z, 1.9, rgb(colour, 0.55))
    face.circle(x, z, 1.35, rgb("#8F8B86"))
    face.line(x - 0.8, z, x + 0.8, z, 0.3, rgb("#5A5652"))
    face.line(x, z - 0.8, x, z + 0.8, 0.3, rgb("#5A5652"))


def region_image(face, size):
    return face.img.resize(size, Image.LANCZOS)


def paste_padded(atlas, image, box):
    """A region pasted with its edge pixels repeated 4 pixels round it, so filtering at its edge sees its own colours."""
    x, y, w, h = box
    region = image.resize((w, h), Image.LANCZOS) if image.size != (w, h) else image
    atlas.paste(region.resize((w + 8, h + 8), Image.NEAREST), (x - 4, y - 4))
    atlas.paste(region, (x, y))


# ---- The Game Boy (DMG-01) -------------------------------------------------------------------------------------------

def face_gb(m):
    c = m["colours"]
    case = c["case"]
    w, h = m["width"], m["height"]
    face = Face((-w / 2, w / 2, 0.0, h), rgb(case))

    # The strip along the top: its groove, its seam at the right, OFF-ON in its moulded racetrack.
    face.line(-w / 2, 140.1, 38.0, 140.1, 0.3, rgb(case, 0.72))
    face.line(-w / 2, 139.75, 38.0, 139.75, 0.25, rgb(case, 1.08))
    face.line(38.0, 140.1, 38.0, h, 0.3, rgb(case, 0.72))
    embossed(face, lambda dx, dz, fill: outline(face, stadium_points(-25.3 + dx, 144.4 + dz, 17.2, 3.3), 0.22, fill),
             case)
    embossed_text(face, "OFF\u2022ON", "GOTHIC.TTF", 1.6, -25.3, 144.4, case)
    for x, deg in ((-32.6, 180), (-18.0, 0)):
        embossed(face, lambda dx, dz, fill, x=x, deg=deg: triangle(face, x + dx, 144.4 + dz, 1.4, deg, fill), case)

    # Under the lens: the gap round it, dark.
    face.polygon(L.lens_outline("gb", grow=m["lens"]["gap"] + 0.4), rgb(c["gap"]))

    # Nintendo GAME BOY(TM), in navy.
    navy = rgb(c["navy"])
    face.text("Nintendo", "arialbd.ttf", 3.0, -37.9, 72.5, navy)
    fitted(face, "GAME BOY", "GOTHICBI.TTF", 4.8, -16.5, 11.3, 73.4, navy)
    face.text("TM", "arialbd.ttf", 1.0, 11.9, 71.6, navy)

    # The D-pad's hole and the moulded arrows round it.
    d = m["dpad"]
    x, z = d["at"]
    face.polygon(cross_points(x, z, d["arm"] / 2 + 0.5, d["width"] / 2 + 0.5), rgb(c["dpad"], 1.2))
    for deg, (ax, az) in ((90, (0, 12.7)), (270, (0, -12.7)), (180, (-13.0, 0)), (0, (13.0, 0))):
        embossed(face, lambda dx, dz, fill, deg=deg, ax=ax, az=az: triangle(face, x + ax + dx, z + az + dz, 1.5, deg,
                                                                           fill), case, depth=0.1)

    # B and A: their holes, and their letters, slanting as the buttons do.
    b = m["buttons"]
    for name in ("b", "a"):
        bx, bz = b[name]
        face.circle(bx, bz, b["r"] + 0.75, rgb(case, 0.82))
        face.circle(bx, bz, b["r"] + 0.35, rgb(c["ab"], 0.45))
    face.text("B", "ariblk.ttf", 2.2, 23.3, 35.4, navy, anchor="centre", shear=0.2, degrees=24.0, stretch=1.25)
    face.text("A", "ariblk.ttf", 2.2, 38.0, 42.4, navy, anchor="centre", shear=0.2, degrees=24.0, stretch=1.25)

    # SELECT and START: their wells and their names.
    p = m["pills"]
    length, width = p["size"]
    for name, (tx, tz) in (("select", (-10.1, 20.5)), ("start", (5.3, 20.8))):
        px, pz = p[name]
        face.pill(px, pz, length + 1.6, width + 1.6, p["slant"], rgb(case, 0.8))
        face.pill(px, pz, length + 0.5, width + 0.5, p["slant"], rgb(case, 0.55))
        face.text(name.upper(), "ariblk.ttf", 1.5, tx, tz, navy, anchor="centre", shear=0.2, degrees=p["slant"],
                  stretch=1.3)

    # The speaker's slots (cut into the face: their walls and floors are this dark).
    s = m["speaker"]
    for k in range(s["count"]):
        sx, sz = s["first"][0] + s["step"][0] * k, s["first"][1] + s["step"][1] * k
        face.pill(sx, sz, s["length"] + 0.7, s["width"] + 0.7, s["slant"], rgb(case, 0.7))
        face.pill(sx, sz, s["length"], s["width"], s["slant"], rgb(c["slot"]))

    # PHONES, moulded, and the notches under it.
    embossed(face, lambda dx, dz, fill: outline(face, stadium_points(-4.3 + dx, 4.0 + dz, 14.0, 3.2), 0.2, fill), case)
    embossed_text(face, "\u2229PHONES", "GOTHICB.TTF", 1.5, -4.3, 4.0, case)
    for x in (-5.6, -4.3, -3.0):
        face.line(x, 0.6, x, 2.0, 0.35, rgb(case, 0.7))
    return face


def back_gb(m):
    """The back, seen from behind: drawn at bx = -x."""
    c = m["colours"]
    case = c["case"]
    w, h, d = m["width"], m["height"], m["depth"]
    face = Face((-w / 2, w / 2, 0.0, h), rgb(case))

    # The cartridge's bay: its floor, two rails, the lock's window by the switch.
    (x0, x1), z0 = m["bay"]["x"], m["bay"]["z0"]
    face.rounded(-x1, -x0, z0, h + 1.0, 0.6, rgb(case, 0.86))
    for x in (-16.0, 16.0):
        face.rounded(x - 1.0, x + 1.0, z0 + 1.0, h - 1.0, 0.4, rgb(case, 0.93))
    face.rounded(26.0, 29.0, 142.5, 145.5, 0.2, rgb(c["port"]))

    # The label panel: its edge, the serial number's sticker, the moulded plate of particulars; its screws.
    px0, px1, pz0, pz1 = m["panel"]["rect"]
    face.rounded(-px1, -px0, pz0, pz1, 1.5, rgb(case, 0.88))
    face.rounded(-px1 + 0.35, -px0 - 0.35, pz0 + 0.35, pz1 - 0.35, 1.2, rgb(case, 1.0))
    face.rounded(-13.0, 13.0, 103.4, 107.4, 0.3, rgb(c["sticker"]))
    face.text("G05014781", "consola.ttf", 2.1, 0.0, 105.4, rgb("#2B2A80"), anchor="centre", stretch=1.1)
    face.rounded(-22.0, 22.0, 82.0, 98.5, 0.5, rgb(case, 0.94))
    lines = ["MODEL NO.  DMG-01", "\u00A91989 Nintendo", "RATING : DC6V  0.7W", "BATTERY : SUM-3(AA,R6)\u00D74",
             "PAT. PEND.   MADE IN JAPAN"]
    for k, line in enumerate(lines):
        embossed_text(face, line, "GOTHICB.TTF", 1.15, -20.6, 96.4 - k * 3.15, case, anchor="left")
    for x in (-37.5, 37.5):
        for z in (131.0, 80.0):
            screw(face, x, z, case)

    # The ribbed band across the back and the battery cover in it, with its latch.
    ribs(face, -w / 2 + 2.0, w / 2 - 2.0, 23.0, 75.5, 3.3, case)
    cx0, cx1, cz0, cz1 = m["cover"]["rect"]
    tx0, tx1, tz0, tz1 = m["cover"]["tab"]
    face.rounded(-cx1 - 0.4, -cx0 + 0.4, cz0 - 0.4, cz1 + 0.4, 1.4, rgb(case, 0.62))
    face.rounded(-tx1 - 0.4, -tx0 + 0.4, tz0, tz1 + 0.4, 1.0, rgb(case, 0.62))
    face.rounded(-cx1, -cx0, cz0, cz1, 1.2, rgb(case, 1.0))
    face.rounded(-tx1, -tx0, tz0, tz1, 0.8, rgb(case, 1.0))
    ribs(face, -cx1 + 1.5, -cx0 - 1.5, 30.0, cz1 - 1.0, 3.4, case)
    face.rounded(-tx1 + 3.0, -tx0 - 3.0, tz1 - 4.5, tz1 - 2.5, 0.4, rgb(case, 0.8))
    face.rounded(-5.0, 5.0, 64.6, 66.2, 0.3, rgb(c["port"]))
    return face


def side_gb(m, side):
    """An end, seen from that side: drawn at (y, z) on the right (the face at the left), (d - y, z) on the left."""
    c = m["colours"]
    case = c["case"]
    h, d = m["height"], m["depth"]
    face = Face((0.0, d, 0.0, h), rgb(case))
    at = (lambda y: y) if side > 0 else (lambda y: d - y)
    seam = at(18.5)
    face.line(seam, 0.0, seam, h, 0.35, rgb(case, 0.7))
    lo, hi = sorted((at(19.5), at(d - 1.5)))
    for k in range(16):                                    # the grip's ribs on the back half
        z = 12.0 + k * 3.9
        face.line(lo, z, hi, z, 0.5, rgb(case, 0.84))
        face.line(lo, z + 0.5, hi, z + 0.5, 0.4, rgb(case, 1.08))
    wheel = next(wh for wh in m["wheels"] if wh["side"] == side)
    chord = 2 * math.sqrt(wheel["r"] ** 2 - (wheel["r"] - wheel["out"]) ** 2)
    y0, y1 = sorted((at(wheel["y"][0] - 0.6), at(wheel["y"][1] + 0.6)))
    face.rounded(y0, y1, wheel["z"] - chord / 2 - 0.6, wheel["z"] + chord / 2 + 0.6, 0.5, rgb(c["port"]))
    if side > 0:
        face.text("VOL", "GOTHICB.TTF", 1.3, at(5.5), wheel["z"] + 8.5, rgb(case, 0.62), anchor="centre", degrees=90)
        triangle(face, at(5.5), wheel["z"] + 13.0, 1.5, 90, rgb(case, 0.62))
        y0, y1 = sorted((at(9.0), at(13.0)))
        face.rounded(y0, y1, 112.0, 125.0, 0.6, rgb(c["port"]))
        face.rounded(y0 + 0.8, y1 - 0.8, 113.5, 123.5, 0.3, rgb("#B8B6B0"))
        face.text("EXT. CONNECTOR", "GOTHICB.TTF", 1.1, at(5.2), 118.5, rgb(case, 0.62), anchor="centre", degrees=90)
    else:
        face.text("CONTRAST", "GOTHICB.TTF", 1.25, at(5.5), wheel["z"] - 10.5, rgb(case, 0.62), anchor="centre",
                  degrees=-90)
        face.circle(at(11.0), 122.0, 2.6, rgb(case, 0.75))
        face.circle(at(11.0), 122.0, 1.8, rgb(c["port"]))
        face.circle(at(11.0), 122.0, 0.6, rgb("#9A968E"))
        face.text("DC6V", "GOTHICB.TTF", 1.1, at(5.0), 122.0, rgb(case, 0.62), anchor="centre", degrees=-90)
    return face


def top_gb(m):
    """The top, seen from above: x across, y up the image (the face at the bottom)."""
    c = m["colours"]
    case = c["case"]
    w, d = m["width"], m["depth"]
    face = Face((-w / 2, w / 2, 0.0, d), rgb(case))
    sw = m["switch"]
    face.rounded(sw["x"] - sw["size"][0] / 2 - 0.4, sw["x"] + sw["travel"] + sw["size"][0] / 2 + 0.4, sw["y"][0] + 1.0,
                 sw["y"][1] - 1.0, 0.8, rgb(c["port"]))
    face.line(-w / 2, 8.0, w / 2, 8.0, 0.3, rgb(case, 0.8))   # the strip's back edge
    return face


def bottom_gb(m):
    """The bottom, seen from below: x across, the face at the top of the image."""
    c = m["colours"]
    case = c["case"]
    w, d = m["width"], m["depth"]
    face = Face((-w / 2, w / 2, 0.0, d), rgb(case))
    face.line(-w / 2, d - 18.5, w / 2, d - 18.5, 0.35, rgb(case, 0.7))
    face.circle(-4.3, d - 9.0, 2.4, rgb(case, 0.72))
    face.circle(-4.3, d - 9.0, 1.7, rgb(c["port"]))
    return face


def dpad_top(m, colour):
    """The D-pad's top, seen from the front: its arms' grooves and arrows, the dimple in its middle."""
    d = m["dpad"]
    a = d["arm"] / 2
    face = Face((-a, a, -a, a), rgb(colour))
    for deg in (0, 90, 180, 270):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        for k in range(3):
            r = a * 0.42 + k * 1.1
            x0, z0 = r * c - d["width"] * 0.28 * s, r * s + d["width"] * 0.28 * c
            x1, z1 = r * c + d["width"] * 0.28 * s, r * s - d["width"] * 0.28 * c
            face.line(x0, z0, x1, z1, 0.25, rgb(colour, 2.0))
        triangle(face, a * 0.78 * c, a * 0.78 * s, 1.3, deg, rgb(colour, 2.4))
    face.circle(0.0, 0.0, d["width"] * 0.3, rgb(colour, 0.6))
    face.circle(-0.3, 0.3, d["width"] * 0.24, rgb(colour, 1.5))
    return face


# ---- The Game Boy Color ----------------------------------------------------------------------------------------------

def face_gbc(m):
    c = m["colours"]
    case = c["case"]
    w, h = m["width"], m["height"]
    face = Face((-w / 2, w / 2, 0.0, h), rgb(case))

    face.polygon(L.lens_outline("gbc", grow=m["lens"]["gap"] + 0.4), rgb(c["gap"]))
    embossed_text(face, "\u25B2 COMM.", "GOTHIC.TTF", 1.6, -16.6, 130.0, case)

    # Nintendo in its racetrack.
    embossed(face, lambda dx, dz, fill: outline(face, stadium_points(-0.1 + dx, 61.1 + dz, 21.7, 3.9), 0.25, fill),
             case)
    embossed_text(face, "Nintendo", "arialbd.ttf", 2.1, -0.1, 61.1, case)

    # The holes round the D-pad, B and A, SELECT and START, and their names.
    d = m["dpad"]
    x, z = d["at"]
    face.polygon(cross_points(x, z, d["arm"] / 2 + 0.5, d["width"] / 2 + 0.5), rgb(case, 0.5))
    b = m["buttons"]
    for name in ("b", "a"):
        bx, bz = b[name]
        face.circle(bx, bz, b["r"] + 0.6, rgb(case, 0.75))
        face.circle(bx, bz, b["r"] + 0.3, rgb(case, 0.45))
    p = m["pills"]
    length, width = p["size"]
    for name in ("select", "start"):
        px, pz = p[name]
        face.pill(px, pz, length + 1.4, width + 1.4, 0.0, rgb(case, 0.8))
        face.pill(px, pz, length + 0.5, width + 0.5, 0.0, rgb(case, 0.5))
    for name, x0, x1 in (("SELECT", -11.2, -1.0), ("START", 1.0, 9.5)):
        embossed(face, lambda dx, dz, fill, name=name, x0=x0, x1=x1: fitted(face, name, "ARIALN.TTF", 2.4, x0 + dx,
                                                                              x1 + dx, 19.2 + dz, fill), case)

    # The speaker: open holes and closed dimples in turn, in a circle.
    s = m["speaker"]
    sx, sz = s["at"]
    for row in range(-5, 6):
        for col in range(-5, 6):
            hx = sx + (col + (0.5 if row % 2 else 0.0)) * s["pitch"]
            hz = sz + row * s["pitch"] * 0.87
            if (hx - sx) ** 2 + (hz - sz) ** 2 > s["r"] ** 2:
                continue
            if (row + col) % 2 == 0:
                face.circle(hx, hz, s["hole"] + 0.15, rgb(case, 0.8))
                face.circle(hx, hz, s["hole"], rgb(c["slot"]))
            else:
                face.circle(hx + 0.08, hz - 0.08, s["hole"], rgb(case, 1.06))
                face.circle(hx, hz, s["hole"] * 0.9, rgb(case, 0.9))
    return face


def back_gbc(m):
    c = m["colours"]
    case = c["case"]
    w, h = m["width"], m["height"]
    face = Face((-w / 2, w / 2, 0.0, h), rgb(case))
    (x0, x1), z0 = m["bay"]["x"], m["bay"]["z0"]
    face.rounded(-x1, -x0, z0, h + 1.0, 0.6, rgb(case, 0.82))
    for x in (-15.0, 15.0):
        face.rounded(x - 1.0, x + 1.0, z0 + 1.0, h - 1.0, 0.4, rgb(case, 0.9))
    for x in (-33.3, 33.3):
        for z in (121.3, 80.4):
            screw(face, x, z, case)

    # The batteries' bulge: its cover, GAME BOY moulded on it, its latch at the bottom.
    bx0, bx1, bz0, bz1 = m["bulge"]["rect"]
    face.rounded(-bx1 + 2.0, -bx0 - 2.0, bz0 + 3.0, bz1 - 2.0, 3.0, rgb(case, 0.66))
    face.rounded(-bx1 + 2.4, -bx0 - 2.4, bz0 + 3.4, bz1 - 2.4, 2.6, rgb(case, 1.0))
    embossed(face, lambda dx, dz, fill: face.rounded(-17.0 + dx, 17.0 + dx, 33.0 + dz, 41.0 + dz, 1.0, fill), case)
    embossed_text(face, "GAME BOY", "GOTHICBI.TTF", 3.4, 0.0, 37.0, case)
    face.rounded(-6.0, 6.0, bz0 + 1.0, bz0 + 7.0, 1.0, rgb(case, 0.7))
    face.rounded(-5.4, 5.4, bz0 + 1.6, bz0 + 6.4, 0.8, rgb(case, 0.96))
    return face


def side_gbc(m, side):
    c = m["colours"]
    case = c["case"]
    h, d = m["height"], m["depth"]
    face = Face((0.0, d, 0.0, h), rgb(case))
    at = (lambda y: y) if side > 0 else (lambda y: d - y)
    face.line(at(13.0), 0.0, at(13.0), h, 0.35, rgb(case, 0.72))
    if side < 0:
        wheel = m["wheels"][0]
        chord = 2 * math.sqrt(wheel["r"] ** 2 - (wheel["r"] - wheel["out"]) ** 2)
        y0, y1 = sorted((at(wheel["y"][0] - 0.6), at(wheel["y"][1] + 0.6)))
        face.rounded(y0, y1, wheel["z"] - chord / 2 - 0.6, wheel["z"] + chord / 2 + 0.6, 0.5, rgb(c["port"]))
        face.text("VOL", "GOTHICB.TTF", 1.2, at(5.0), wheel["z"], rgb(case, 0.62), anchor="centre", degrees=-90)
        y0, y1 = sorted((at(9.2), at(12.6)))
        face.rounded(y0, y1, 88.0, 97.5, 0.5, rgb(c["port"]))
        face.rounded(y0 + 0.7, y1 - 0.7, 89.2, 96.3, 0.3, rgb("#B0AEA8"))
        face.text("EXT.", "GOTHICB.TTF", 1.1, at(5.0), 92.7, rgb(case, 0.62), anchor="centre", degrees=-90)
    return face


def top_gbc(m):
    c = m["colours"]
    case = c["case"]
    w, d = m["width"], m["depth"]
    face = Face((-w / 2, w / 2, 0.0, d), rgb(case))
    sw = m["switch"]
    face.rounded(sw["x"] - sw["size"][0] / 2 - 0.4, sw["x"] + sw["travel"] + sw["size"][0] / 2 + 0.4, sw["y"][0] + 1.0,
                 sw["y"][1] - 1.0, 0.8, rgb(c["port"]))
    face.rounded(-17.0, -9.0, 1.6, 6.0, 0.8, rgb("#2A0E10"))      # the infrared port's window
    face.rounded(-16.4, -9.6, 2.2, 5.4, 0.5, rgb("#4A1418"))
    return face


def bottom_gbc(m):
    c = m["colours"]
    case = c["case"]
    w, d = m["width"], m["depth"]
    face = Face((-w / 2, w / 2, 0.0, d), rgb(case))
    face.line(-w / 2, d - 13.0, w / 2, d - 13.0, 0.35, rgb(case, 0.72))
    face.circle(-6.0, d - 12.0, 2.4, rgb(case, 0.72))
    face.circle(-6.0, d - 12.0, 1.7, rgb(c["port"]))
    face.circle(14.0, d - 12.0, 2.6, rgb(case, 0.72))
    face.circle(14.0, d - 12.0, 1.9, rgb(c["port"]))
    face.circle(14.0, d - 12.0, 0.6, rgb("#9A968E"))
    return face


def letter_top(m, letter, colour):
    """A button's top with its letter moulded in, seen from the front."""
    r = m["buttons"]["r"]
    face = Face((-r, r, -r, r), rgb(colour))
    face.text(letter, "GOTHICB.TTF", r * 0.95, 0.12, -0.12, rgb(colour, 0.5), anchor="centre")
    face.text(letter, "GOTHICB.TTF", r * 0.95, 0.0, 0.0, rgb(colour, 1.6), anchor="centre")
    return face


# ---- The print atlases -----------------------------------------------------------------------------------------------

SWATCH_COLOURS = {
    "gb": dict(case="case", lens="lens", frame="frame", gap="gap", dark="dpad", ab="ab", rubber="rubber", slot="slot",
               wheel="wheel", port="port", cart="cart"),
    "gbc": dict(case="case", lens="lens", frame="frame", gap="gap", dark="dark", ab="dark", rubber="dark", slot="slot",
                wheel="wheel", port="port", cart="cart"),
}


def print_atlas(kind):
    m = L.MODELS[kind]
    c = m["colours"]
    atlas = Image.new("RGB", (L.PRINT_ATLAS, L.PRINT_ATLAS), rgb(c["case"])[:3])
    regions = m["print_regions"]
    gb = kind == "gb"
    faces = {
        "face": face_gb(m) if gb else face_gbc(m),
        "back": back_gb(m) if gb else back_gbc(m),
        "right": (side_gb if gb else side_gbc)(m, 1),
        "left": (side_gb if gb else side_gbc)(m, -1),
        "top": top_gb(m) if gb else top_gbc(m),
        "bottom": bottom_gb(m) if gb else bottom_gbc(m),
        "dpad": dpad_top(m, c["dpad"] if gb else c["dark"]),
    }
    if not gb:
        faces["btn_a"] = letter_top(m, "A", c["dark"])
        faces["btn_b"] = letter_top(m, "B", c["dark"])
    for name, face in faces.items():
        paste_padded(atlas, face.img.convert("RGB"), regions[name])
    draw = ImageDraw.Draw(atlas)
    names = dict(SWATCH_COLOURS[kind], cart_edge="cart", metal="port")
    for name, (x, y) in L.SWATCHES.items():
        colour = rgb(c[names[name]])[:3]
        if name == "cart_edge":
            colour = rgb(c["cart"], 0.85)[:3]
        if name == "metal":
            colour = (176, 174, 168)
        draw.rectangle([x - L.SWATCH // 2, y - L.SWATCH // 2, x + L.SWATCH // 2 - 1, y + L.SWATCH // 2 - 1], fill=colour)
    return atlas


# ---- The cartridge ---------------------------------------------------------------------------------------------------

def made_up(made_up_dir, kind):
    from arcade_print import Game
    stem, system = L.MODELS[kind]["made_up"]
    return Game(stem, made_up_dir, system)


def label_art(game, size):
    """The label's picture: the game's key art cut to the label's shape, its logo across the calm top."""
    w, h = size
    art = ImageOps.fit(game.keyart.convert("RGB"), size, Image.LANCZOS, centering=(0.5, 0.55)).convert("RGBA")
    logo = game.logo
    k = min(w * 0.9 / logo.width, h * 0.3 / logo.height)
    logo = logo.resize((max(1, round(logo.width * k)), max(1, round(logo.height * k))), Image.LANCZOS)
    shadow = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    shadow.putalpha(logo.getchannel("A").point(lambda a: a * 0.6))
    art.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(max(1, w // 120))), ((w - logo.width) // 2 + 2,
                                                                                      round(h * 0.05) + 3))
    art.alpha_composite(logo, ((w - logo.width) // 2, round(h * 0.05)))
    return art


def cart_label_side(m, game, kind):
    """The label side, seen looking at it (the console's back): its corner cut at the top right."""
    c = m["colours"]
    col = c["cart"]
    w, h, _ = m["cart"]["size"]
    face = Face((-w / 2, w / 2, 0.0, h), rgb(col))
    light = 1.35 if kind == "gb" else 2.4
    # The grip: ridges either side of the moulded racetrack, Nintendo GAME BOY in it.
    for k in range(5):
        z = 49.5 + k * 2.4
        for x0, x1 in ((-w / 2 + 0.8, -21.5), (21.5, w / 2 - 0.8 - (4.5 if z > h - 6.0 else 0.0))):
            face.line(x0, z, x1, z, 0.55, rgb(col, 0.72))
            face.line(x0, z + 0.55, x1, z + 0.55, 0.4, rgb(col, light * 0.85))
    embossed(face, lambda dx, dz, fill: face.rounded(-20.0 + dx, 20.0 + dx, 51.0 + dz, 61.0 + dz, 4.8, fill), col,
             light=light * 0.8, dark=0.7, body=1.0)
    face.text("Nintendo", "arialbi.ttf", 1.9, -9.0, 56.0, rgb(col, light * 0.78), anchor="centre")
    fitted(face, "GAME BOY", "GOTHICI.TTF", 2.4, -2.4, 15.8, 56.1, rgb(col, light * 0.78))
    face.text("TM", "arialbd.ttf", 0.7, 16.8, 55.2, rgb(col, light * 0.78))

    # The label in its recess: a white strip with the game's code, the picture, a thin frame.
    face.rounded(-21.8, 21.8, 6.2, 46.8, 1.2, rgb(col, 0.66))
    face.rounded(-21.2, 21.2, 6.8, 46.2, 0.9, (246, 244, 238, 255))
    face.text(m["code"], "arialbd.ttf", 1.15, -18.9, 26.5, (40, 40, 44, 255), anchor="centre", degrees=90)
    art = label_art(game, (int(37.0 * SCALE), int(37.6 * SCALE)))
    face.paste(art, -16.6, 20.4, 7.6, 45.2)
    outline(face, [(-16.6, 7.6), (20.4, 7.6), (20.4, 45.2), (-16.6, 45.2)], 0.15, (30, 30, 34, 255))
    embossed(face, lambda dx, dz, fill: triangle(face, 0.0 + dx, 3.2 + dz, 3.0, 270, fill), col, light=light,
             dark=0.7)
    return face


def cart_front_side(m, kind):
    """The side towards the console's face, seen looking at it: its corner cut at the top left."""
    c = m["colours"]
    col = c["cart"]
    w, h, _ = m["cart"]["size"]
    face = Face((-w / 2, w / 2, 0.0, h), rgb(col))
    light = 1.35 if kind == "gb" else 2.4
    for x in (-15.5, 15.5):
        face.rounded(x - 1.8, x + 1.8, 9.0, h - 4.0, 0.3, rgb(col, 0.82))
    embossed(face, lambda dx, dz, fill: face.rounded(-11.0 + dx, 11.0 + dx, 56.0 + dz, 59.5 + dz, 0.3, fill), col,
             light=light * 0.8, dark=0.7, body=1.0)
    face.text("MADE IN JAPAN", "GOTHIC.TTF", 1.3, 0.0, 57.75, rgb(col, light * 0.75), anchor="centre")
    face.text("PAT. PEND.", "GOTHIC.TTF", 1.1, 0.0, 53.5, rgb(col, light * 0.75), anchor="centre")
    face.circle(0.0, 33.0, 1.6, rgb(col, 0.7))
    face.circle(-0.2, 33.2, 1.2, rgb(col, 1.15))
    face.circle(0.0, 15.0, 2.0, rgb(col, 0.45))
    face.circle(0.0, 15.0, 1.4, (178, 150, 82, 255))
    face.line(-0.8, 15.0, 0.8, 15.0, 0.25, (110, 90, 46, 255))
    face.line(-w / 2, 9.0, w / 2, 9.0, 0.35, rgb(col, light * 0.7))
    face.line(-w / 2, 8.6, w / 2, 8.6, 0.3, rgb(col, 0.7))
    return face


def cart_atlas(kind, game):
    m = L.MODELS[kind]
    col = m["colours"]["cart"]
    atlas = Image.new("RGB", L.CART_ATLAS, rgb(col)[:3])
    paste_padded(atlas, cart_label_side(m, game, kind).img.convert("RGB"), L.CART_REGIONS["label"])
    paste_padded(atlas, cart_front_side(m, kind).img.convert("RGB"), L.CART_REGIONS["front"])
    draw = ImageDraw.Draw(atlas)
    for name, (x, y) in L.CART_SWATCHES.items():
        colour = {"cart": rgb(col)[:3], "edge": rgb(col, 0.82)[:3], "pins": (186, 160, 92)}[name]
        draw.rectangle([x - 16, y - 16, x + 15, y + 15], fill=colour)
    return atlas


# ---- The lens: the screen's own drawing, shared with game_boy_video.py ------------------------------------------------

# The DMG's LCD: its four shades, lightest first, and how it looks switched off.
DMG_SHADES = ["#B2BC76", "#86934F", "#56653A", "#2F3B24"]
DMG_OFF = "#949C62"


def lcd_box(kind):
    """The LCD's 2x block in the video's pixels, and in millimetres on the lens."""
    m = L.MODELS[kind]
    x0, x1, z0, z1 = m["lens"]["rect"]
    vw, vh = m["video"]
    px, py, pw, ph = m["lcd_px"]
    sx, sz = vw / (x1 - x0), vh / (z1 - z0)
    return (px, py, pw, ph), (x0 + px / sx, x0 + (px + pw) / sx, z1 - (py + ph) / sz, z1 - py / sz)


def lens_face(kind):
    """The lens switched off, in millimetres (a Face over its box): its colour, the window onto the LCD, the printing
    round it and the light off."""
    m = L.MODELS[kind]
    c = m["colours"]
    x0, x1, z0, z1 = m["lens"]["rect"]
    face = Face((x0, x1, z0, z1), rgb(c["lens"]))
    _, (lx0, lx1, lz0, lz1) = lcd_box(kind)
    wx0, wx1, wz0, wz1 = m["window"]
    lx, lz = m["led"]["at"]
    if kind == "gb":
        face.rounded(wx0, wx1, wz0, wz1, 0.6, rgb(c["frame"]))
        face.rounded(-8.0, 8.0, wz0 - 0.8, wz0 + 1.0, 0.3, rgb(c["frame"]))
        face.rounded(lx0, lx1, lz0, lz1, 0.15, rgb(DMG_OFF))
        # DOT MATRIX WITH STEREO SOUND between the stripes, magenta over navy.
        for z, colour in ((133.4, c["magenta"]), (131.6, c["stripe_navy"])):
            for a, b in ((-34.6, -15.0), (26.8, 35.0)):
                face.line(a, z, b, z, 0.5, rgb(colour))
        spaced(face, "DOT MATRIX WITH STEREO SOUND", "GOTHIC.TTF", 1.75, -12.8, 25.0, 132.5, rgb("#D6D6DE"))
        face.circle(lx, lz, m["led"]["r"] + 0.55, rgb(c["lens"], 0.62))
        face.circle(lx, lz, m["led"]["r"], rgb(c["led_off"]))
        face.circle(lx - 0.35, lz + 0.35, 0.35, (255, 255, 255, 70))
        face.text("BATTERY", "GOTHIC.TTF", 1.05, lx, lz - 4.3, rgb("#A4A4AE"), anchor="centre")
    else:
        face.rounded(wx0 - 0.5, wx1 + 0.5, wz0 - 0.5, wz1 + 0.5, 0.5, rgb(c["frame"]))
        face.rounded(lx0, lx1, lz0, lz1, 0.1, rgb(c["lcd_off"]))
        face.circle(lx, lz, m["led"]["r"], rgb(c["led_off"]))
        for k in range(3):
            cx, cy = face.p(lx + 1.0 + k * 1.15, lz)
            r = (1.2 + 0.35 * k) * SCALE
            face.draw.arc([cx - r, cy - r, cx + r, cy + r], -42, 42, fill=rgb("#8A8C96"), width=max(1, int(0.3 * SCALE)))
        face.text("POWER", "GOTHIC.TTF", 1.2, lx + 2.8, lz - 2.6, rgb("#8A8C96"), anchor="centre")
        # GAME BOY COLOR: GAME BOY in grey across -19.3..4.3, then COLOR's letters in their colours across 5.4..19.0.
        fitted(face, "GAME BOY", "GOTHICBI.TTF", 3.6, -19.3, 4.3, 75.3, rgb(c["logo"]))
        stretch = 13.6 / (text_width("COLOR", "comicbd.ttf", 3.9) - 0.4)
        x = 5.4
        for letter, colour in zip("COLOR", ("#E8213A", "#7A3FD8", "#2DB84A", "#F4C21C", "#2F6CE0")):
            x += face.text(letter, "comicbd.ttf", 3.9, x, 75.6, rgb(colour), stretch=stretch) - 0.1
    return face


def lens_base(kind):
    """The lens switched off at its video's size (RGB)."""
    m = L.MODELS[kind]
    return lens_face(kind).img.convert("RGB").resize(m["video"], Image.LANCZOS)


def led_glow(kind):
    """The power light lit, as an RGBA layer at the video's size: a bright dot and its halo on the lens."""
    m = L.MODELS[kind]
    c = m["colours"]
    x0, x1, z0, z1 = m["lens"]["rect"]
    face = Face((x0, x1, z0, z1), (0, 0, 0, 0))
    lx, lz = m["led"]["at"]
    r = m["led"]["r"]
    lit = rgb(c["led_lit"])
    for k in range(14, 0, -1):
        face.circle(lx, lz, r * (1 + 0.16 * k), lit[:3] + (int(150 * (1 - k / 15) ** 2.2),))
    face.circle(lx, lz, r, lit)
    face.circle(lx - r * 0.3, lz + r * 0.3, r * 0.4, (255, 236, 220, 230))
    return face.img.resize(m["video"], Image.LANCZOS)


def sheen(kind):
    """The lens's sheen: a soft diagonal band of light across its plastic (an L layer at the video's size)."""
    w, h = L.MODELS[kind]["video"]
    layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(layer).polygon([(-w * 0.1, h * 0.05), (w * 0.45, -h * 0.1), (w * 0.62, -h * 0.1), (w * 0.05, h * 0.6)],
                                  fill=26)
    return layer.filter(ImageFilter.GaussianBlur(w * 0.05))


class Lens:
    """A card's lens, ready to compose frames of its video: the lens off, the light's layer, the sheen."""

    def __init__(self, kind):
        self.kind = kind
        self.base = lens_base(kind)
        self.glow = led_glow(kind)
        self.sheen = sheen(kind)
        self.white = Image.new("RGB", self.base.size, (255, 255, 255))
        (self.px, self.py, self.pw, self.ph), _ = lcd_box(kind)

    def frame(self, lcd=None, led=0.0):
        """A frame: the LCD's picture (160 x 144 RGB, or None for the LCD off) and the light (0 to 1)."""
        out = self.base.copy()
        if lcd is not None:
            big = lcd.resize((self.pw, self.ph), Image.NEAREST).filter(ImageFilter.GaussianBlur(0.45))
            out.paste(big, (self.px, self.py))
        if led > 0:
            glow = self.glow.copy()
            glow.putalpha(glow.getchannel("A").point(lambda a: round(a * min(1.0, led))))
            out = out.convert("RGBA")
            out.alpha_composite(glow)
            out = out.convert("RGB")
        return Image.composite(self.white, out, self.sheen)


def still(kind):
    return Lens(kind).frame()


def main(made_up_dir, out):
    os.makedirs(out, exist_ok=True)
    for kind in L.MODELS:
        game = made_up(made_up_dir, kind)
        print_atlas(kind).save(os.path.join(out, f"{kind}_print.png"), optimize=True)
        cart_atlas(kind, game).save(os.path.join(out, f"{kind}_cart.png"), optimize=True)
        still(kind).save(os.path.join(out, f"{kind}_screen.png"), optimize=True)
        print(f"{L.MODELS[kind]['name']}: print, cartridge and screen")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
