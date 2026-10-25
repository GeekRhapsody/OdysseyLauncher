"""The PC Engine Duo's printing, for the console theme's PC Engine CD model (tools/console-models/pcenginecd.py).

Draws its atlas, its regions as pcenginecd_layout.py places them, each in millimetres as the model's planar UVs map it:
the Duo from above (PC Engine DUO on the left panel, NEC, the Compact Disc logo, PUSH CLOSE and the groove on the lid,
the fins' grooves, POWER, the HuCard door with its zigzag edge, BUSY and its window, LOCK and its track, OPEN); its
front face (OFF and ON over POWER's slot, PAD, the door's tab); the pad's top (its black face plate, the blue arc round
the D-pad, NEC, II and I, the turbo switches, SELECT and RUN); the CD's label (a made-up game, Odyssey); and the
swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/pcenginecd_print.py <out folder>

It writes pcenginecd_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcenginecd_layout as L  # noqa: E402
from cdi_print import disc_logo  # noqa: E402
from neogeocd_print import stretched  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
INK = (150, 150, 156)
LAVENDER = (150, 140, 230)
TEAL = (40, 170, 160)
BLUE = (70, 110, 220)


# ---- The top -----------------------------------------------------------------------------------------------------------

def top():
    w, d = L.WIDTH, L.DEPTH
    reg = Region(L.REGIONS["top"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y

    def rect(x0, y0, x1, y1, fill, **kw):
        (a, b), (c, e) = at(x0, y1), at(x1, y0)
        reg.rect_(a, b, c, e, fill, **kw)
    for x in L.FINS["x"]:
        rect(x - L.FINS["width"] / 2, L.FINS["y"][0], x + L.FINS["width"] / 2, L.FINS["y"][1], shade(CASE, -0.5))
    (lx0, lx1), (ly0, ly1) = L.LEFT_PANEL["x"], L.LEFT_PANEL["y"]
    rect(lx0, ly0, lx1, ly1, shade(CASE, 0.03))
    reg.text("PC Engine", "arialbi.ttf", 3.2, *at(lx0 + 14.0, ly1 - 8.0), LAVENDER)
    stretched(reg, "DUO", "arial.ttf", *at(lx0 + 24.0, ly1 - 3.0), *at(lx0 + 60.0, ly1 - 14.0), LAVENDER, outline=True)
    reg.text("PC Engine with SUPER CD-ROM²", "arialbd.ttf", 2.6, *at(lx0 + 63.0, ly1 - 11.0), LAVENDER, anchor="lm")
    (cx0, cx1), (cy0, cy1) = L.LID["x"], L.LID["y"]
    rect(cx0, cy0, cx1, cy1, shade(CASE, 0.03))
    gy, (gx0, gx1) = L.LID["groove"]
    rect(gx0, gy - 0.8, gx1, gy + 0.8, shade(CASE, -0.35), r=0.8)
    disc_logo(reg, *at(cx1 - 20.0, gy + 20.0), 9.0, INK)
    reg.text("PUSH CLOSE", "arial.ttf", 2.6, *at(cx1 - 14.0, cy0 + 8.0), INK)
    reg.text("NEC", "timesbd.ttf", 5.0, *at(cx1 - 10.0, cy1 - 6.0), INK)

    (dx0, dx1), (dy0, dy1) = L.DOOR["x"], L.DOOR["y"]       # the HuCard's door on the strip, its zigzag edge
    rect(dx0, dy0, dx1, dy1, shade(CASE, -0.04))
    zig = [(dx0 + 2.0, dy0 + 24.0)]
    for k in range(7):
        zig.append((dx0 + 8.0 + 7.4 * k, dy0 + (28.0 if k % 2 == 0 else 22.0)))
    zig.append((dx1 - 2.0, dy0 + 24.0))
    reg.line([at(x, y) for x, y in zig], shade(CASE, -0.45), 0.6)
    reg.text("POWER", "arial.ttf", 2.6, *at(-114.0, 40.0), INK)
    reg.line([at(-130.0, 44.0), at(-130.0, 30.0), at(-102.0, 30.0)], shade(CASE, -0.4), 0.4)
    bx0, bx1 = L.BUSY["x"]
    reg.text("BUSY", "arial.ttf", 2.6, *at(bx0 - 6.0, L.BUSY["y"]), INK)
    rect(bx0, L.BUSY["y"] - 1.0, bx1, L.BUSY["y"] + 1.0, (70, 34, 30), r=0.8)
    (kx0, kx1), ky = L.LOCK["x"], L.LOCK["y"]
    rect(-36.0, ky - 0.5, kx1 + 22.0, ky + 0.5, shade(CASE, -0.4))   # the slider's track along the strip
    reg.text("LOCK ▷", "seguisym.ttf", 2.6, *at(kx0 - 8.0, ky), INK)
    (ox, oy), r = L.OPEN["at"], L.OPEN["r"]
    reg.text("OPEN", "arial.ttf", 2.6, *at(ox - r - 7.0, oy), INK)
    reg.circle(*at(ox, oy), r + 1.0, shade(CASE, -0.35))
    reg.text("HE", "arialbd.ttf", 4.0, *at(132.0, 8.0), INK)
    return reg


def front():
    w, h = L.WIDTH, L.BASE_TOP
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, h - z
    (px0, px1), (pz0, pz1) = L.POWER["x"], L.POWER["z"]
    reg.rect_(*at(px0, pz1), *at(px1, pz0), (14, 14, 15), r=1.0)
    reg.text("OFF", "arial.ttf", 2.4, *at(px0 + 4.0, pz1 + 4.0), INK)
    reg.text("ON", "arial.ttf", 2.4, *at(px1 - 5.0, pz1 + 4.0), INK)
    (tx0, tx1, tz0, tz1) = L.DOOR["tab"]
    reg.rect_(*at(tx0, tz1), *at(tx1, tz0), shade(CASE, -0.05), outline=shade(CASE, -0.4), width=0.4)
    reg.circle(*at(L.PAD_PORT["x"], L.PAD_PORT["z"]), L.PAD_PORT["r"] + 1.2, shade(CASE, -0.3))
    reg.text("PAD", "arial.ttf", 2.6, *at(L.PAD_PORT["x"] + 12.0, L.PAD_PORT["z"] - 2.0), INK)
    return reg


# ---- The pad -----------------------------------------------------------------------------------------------------------

def pad():
    p = L.PAD
    pw, pd, _ = p["size"]
    reg = Region(L.REGIONS["pad"], pw, pd, CASE)

    def at(x, y):
        return x + pw / 2, pd / 2 - y
    x0, x1, y0, y1 = p["plate"]
    reg.rect_(*at(x0, y1), *at(x1, y0), (18, 18, 20), r=5.0)
    dx, dy, span, arm = p["dpad"]
    for k in range(6):                                       # the blue arc beside the D-pad
        a = math.radians(-48 + 19 * k)
        r0, r1 = span / 2 + 3.5, span / 2 + 7.0 + k * 0.5
        ca, sa = math.cos(a), math.sin(a)
        cb, sb = math.cos(a + math.radians(13)), math.sin(a + math.radians(13))
        reg.poly([at(dx + ca * r0, dy + sa * r0), at(dx + ca * r1, dy + sa * r1), at(dx + cb * r1, dy + sb * r1),
                  at(dx + cb * r0, dy + sb * r0)], BLUE)
    reg.circle(*at(dx, dy), span / 2 + 2.5, (30, 30, 33))
    reg.text("NEC", "timesbd.ttf", 5.0, *at(-48.0, 16.0), (220, 220, 224))
    for name, label in (("ii", "II"), ("i", "I")):
        x, y = p[name]
        reg.rect_(*at(x - 6.0, y + 17.0), *at(x + 6.0, y + 10.0), BLUE, r=1.0)
        reg.text(label, "timesbd.ttf", 4.6, *at(x, y + 13.5), (240, 240, 246))
        reg.rect_(*at(x - 2.0, y + 26.0), *at(x + 2.0, y + 19.0), (8, 8, 9), r=1.5)    # the turbo switch's slot
    for name, label in (("select", "SELECT"), ("run", "RUN")):
        x, y = p[name]
        reg.text(label, "arial.ttf", 2.8, *at(x, y - 5.6), (220, 220, 224))
    return reg


def disc():
    dm = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc"], dm, dm, (210, 212, 218))
    c = dm / 2
    art = space((600, 600)).convert("RGB")
    ship(ImageDraw.Draw(art), 180, 330, 4.0, "#FFFFFF", "#FFB23C")
    mask = Image.new("L", reg.img.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    md.ellipse(reg.box(c - 21.0, c - 21.0, c + 21.0, c + 21.0), fill=0)
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    reg.circle(c, c, 21.0, (176, 180, 186), outline=(150, 150, 156), width=0.4)
    reg.text("ODYSSEY", "ariblk.ttf", 11.0, c, c - 36.0, (255, 214, 70))
    reg.circle(c, c, 7.5, (40, 40, 44))
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (top(), front(), pad(), disc()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("teal", TEAL), ("lavender", LAVENDER), ("grey", (120, 120, 126)), ("dark", (14, 14, 15)),
                         ("lit", (255, 120, 50)), ("silver", (200, 204, 210)), ("white", (220, 220, 224))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "pcenginecd_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
