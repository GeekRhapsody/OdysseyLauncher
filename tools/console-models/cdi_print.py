"""The Philips CD-i 220's printing and display, for the console theme's CD-i model (tools/console-models/cdi.py).

Draws its atlas, its regions as cdi_layout.py places them, each in millimetres as the model's planar UVs map it: the
front seen from in front (the door's dots and the Compact Disc Interactive logo, PHILIPS on the strip under it, the
buttons' names, the lines between the panels); the display's window three ways (smoked red, its segments unlit, CDI
220 CD-INTERACTIVE PLAYER and PULL TO OPEN; lit, the disc read: CD-i in its digits; lit, playing: PLAY, the track and
its time); the disc's label (a made-up game, Odyssey); the gamepad's top (CD-i, the thumbpad's marks, the buttons'
dots, SPEED); and the swatches small parts take their colour from. Run it with the system Python (Pillow):

    python tools/console-models/cdi_print.py <out folder>

It writes cdi_print.png there.
"""

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdi_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
LABEL = (196, 198, 200)
SMOKE = (44, 16, 18)
VFD = (150, 244, 228)
UNLIT = (60, 26, 28)


# ---- The front ---------------------------------------------------------------------------------------------------------

def disc_logo(reg, x, y, h, ink):
    """The Compact Disc Interactive logo, h tall, its top left at (x, y): COMPACT over disc, Interactive in a box."""
    reg.text("COMPACT", "arial.ttf", h * 0.16, x + h * 0.62, y + h * 0.1, ink)
    reg.text("disc", "arialbd.ttf", h * 0.62, x + h * 0.62, y + h * 0.48, ink)
    reg.rect_(x + h * 0.05, y + h * 0.78, x + h * 1.2, y + h * 1.02, None, outline=ink, width=0.25)
    reg.text("Interactive", "arial.ttf", h * 0.17, x + h * 0.62, y + h * 0.9, ink)


def front():
    w, h = L.WIDTH, L.HEIGHT - L.FOOT
    reg = Region(L.REGIONS["front"], w, h, CASE)

    def at(x, z):
        return x + w / 2, L.HEIGHT - z
    line = shade(CASE, -0.3)
    (ax, ay), (bx, _) = at(-w / 2, L.TOP_STRIP), at(w / 2, L.TOP_STRIP)
    reg.line([(ax, ay), (bx, ay)], line, 0.5)
    reg.line([(ax, ay + 0.5), (bx, ay + 0.5)], shade(CASE, 0.1), 0.3)
    for x in (L.MIDDLE["x"][1] + 0.75, L.RIGHT_PANEL["x"][0] - 1.0):            # the lines between the panels
        reg.line([at(x, L.FOOT), at(x, L.TOP_STRIP)], line, 0.5)
    (dx0, dx1), (dz0, dz1) = L.DOOR["x"], L.DOOR["z"]
    reg.rect_(*at(dx0 - 0.8, dz1 + 0.8), *at(dx1 + 0.8, dz0 - 0.8), shade(CASE, -0.4))   # the door's gap
    reg.rect_(*at(dx0, dz1), *at(dx1, dz0), shade(CASE, -0.03))
    for k in range(7):                                      # the door's dots
        reg.circle(*at(dx0 + 8.0 + 2.6 * k, dz1 - 9.0), 0.35, shade(CASE, 0.22))
    disc_logo(reg, *at(dx0 + 7.0, dz0 + 14.0), 10.0, shade(CASE, 0.22))
    reg.text("PHILIPS", "arialbd.ttf", 5.4, *at(dx0 + 22.0, (L.FOOT + dz0) / 2), (214, 214, 216))
    for name, x0, x1, z0, z1 in L.BUTTONS:                  # the buttons' names over them
        reg.rect_(*at(x0 - 0.7, z1 + 0.7), *at(x1 + 0.7, z0 - 0.7), shade(CASE, -0.35), r=1.2)
        label = {"previous": "PREVIOUS", "play": "PLAY", "next": "NEXT", "open": "OPEN", "onoff": "ON / OFF",
                 "pause": "PAUSE", "stop": "STOP"}[name]
        reg.text(label, "arial.ttf", 1.9, *at((x0 + x1) / 2, z1 + 2.4), LABEL)
    (wx0, wx1), (wz0, wz1) = L.WINDOW["x"], L.WINDOW["z"]
    reg.rect_(*at(wx0 - 0.6, wz1 + 0.6), *at(wx1 + 0.6, wz0 - 0.6), shade(CASE, -0.4))
    return reg


# ---- The display -------------------------------------------------------------------------------------------------------

SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
            "8": "abcdefg", "9": "abcdfg", "-": "g", "C": "afed", "d": "bcdeg", "i": "e", " ": ""}


def digit(reg, ch, x, y, w, h, colour):
    """A seven-segment digit, w x h, its top left at (x, y)."""
    t = w * 0.16
    segs = {"a": (x + t, y, x + w - t, y + t), "g": (x + t, y + h / 2 - t / 2, x + w - t, y + h / 2 + t / 2),
            "d": (x + t, y + h - t, x + w - t, y + h), "f": (x, y + t, x + t, y + h / 2 - t / 2),
            "b": (x + w - t, y + t, x + w, y + h / 2 - t / 2), "e": (x, y + h / 2 + t / 2, x + t, y + h - t),
            "c": (x + w - t, y + h / 2 + t / 2, x + w, y + h - t)}
    for s in SEGMENTS[ch]:
        x0, y0, x1, y1 = segs[s]
        reg.rect_(x0, y0, x1, y1, colour, r=t * 0.3)
    if ch == "i":
        reg.rect_(x, y + h / 2 - t * 1.6, x + t, y + h / 2 - t * 0.6, colour)


def display(name):
    """The window: smoked red, the segments faint behind it; lit as the disc is read, or playing."""
    w, h = L.WINDOW["x"][1] - L.WINDOW["x"][0], L.WINDOW["z"][1] - L.WINDOW["z"][0]
    reg = Region(L.REGIONS[name], w, h, SMOKE)
    lit = name != "display"

    def ink(on):
        return VFD if lit and on else UNLIT
    text = {"display": "88888888", "display_disc": "  Cd-i  ", "display_play": "01  0012"}[name]
    for k, ch in enumerate(text):
        if not lit:
            ch = "8"
        digit(reg, ch, 30.0 + 10.0 * k, 17.0, 7.0, 12.0, ink(ch != "8" or lit))
    if name == "display_play":
        reg.circle(30.0 + 10.0 * 5 + 8.6, 20.5, 0.6, VFD)
        reg.circle(30.0 + 10.0 * 5 + 8.6, 25.5, 0.6, VFD)
    playing = name == "display_play"
    labels = [("MUTE", 14.0, 8.0, False), ("PAUSE", 14.0, 14.0, False), ("PLAY", 14.0, 20.0, playing),
              ("SHUFFLE", 44.0, 9.0, False), ("REPEAT", 78.0, 11.0, False), ("SCAN", 104.0, 12.0, False),
              ("TRACK", 38.0, 33.5, playing), ("TOTAL", 62.0, 33.5, False), ("TIME", 100.0, 33.5, playing)]
    for word, x, y, on in labels:
        reg.text(word, "arial.ttf", 2.4, x, y, ink(on))
    reg.poly([(9.0, 23.0), (14.0, 26.0), (9.0, 29.0)], ink(playing))
    for k, (word, on) in enumerate((("COMPACT DISC", lit), ("INTERACTIVE", lit), ("GRAPHICS", False))):
        y = 15.0 + 5.2 * k
        if k:
            reg.rect_(116.0, y - 2.0, 136.0, y + 2.0, None, outline=ink(on), width=0.3)
        reg.text(word, "arial.ttf", 2.2, 126.0, y, ink(on))
    reg.text("CDI 220  CD-INTERACTIVE PLAYER", "arial.ttf", 2.0, 4.0, h - 3.2, (150, 120, 120), anchor="lm")
    reg.text("PULL TO OPEN", "arial.ttf", 2.0, w - 4.0, h - 3.2, (150, 120, 120), anchor="rm")
    sheen = reg.layer()
    ImageDraw.Draw(sheen).rectangle(reg.box(0.0, 0.0, w, h * 0.18), fill=(255, 255, 255, 26))
    reg.over(sheen)
    return reg


# ---- The disc, the gamepad ---------------------------------------------------------------------------------------------

def disc_top():
    d = L.DISC["diameter"]
    reg = Region(L.REGIONS["disc_top"], d, d, (196, 200, 206))
    c = d / 2
    art = space((600, 600)).convert("RGB")
    da = ImageDraw.Draw(art)
    ship(da, 180, 330, 4.0, "#FFFFFF", "#FFB23C")
    x0, y0, x1, y1 = reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0)
    mask = Image.new("L", reg.img.size, 0)
    dm = ImageDraw.Draw(mask)
    dm.ellipse(reg.box(c - 58.0, c - 58.0, c + 58.0, c + 58.0), fill=255)
    dm.ellipse(reg.box(c - 22.0, c - 22.0, c + 22.0, c + 22.0), fill=0)
    layer = Image.new("RGBA", reg.img.size, (0, 0, 0, 0))
    layer.paste(art.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    reg.img.paste(layer, (0, 0), mask)
    reg.circle(c, c, 22.0, outline=(150, 154, 160), width=0.4)
    reg.text("ODYSSEY", "ariblk.ttf", 11.0, c, c - 36.0, (255, 214, 70))
    disc_logo(reg, c + 26.0, c + 26.0, 12.0, (236, 236, 240))
    reg.circle(c, c, 7.5, (60, 62, 66))
    return reg


def pad():
    xs = [x for x, _ in L.PAD_OUTLINE]
    w, d = max(xs) - min(xs), 101.0
    reg = Region(L.REGIONS["pad"], w, d, CASE)

    def at(x, y):
        return x + w / 2, d - y
    ink = shade(CASE, -0.25)
    p = L.PAD["dpad"]
    cx, cy = at(*p["at"])
    r = p["ring"] - 3.0
    for k in range(4):                                       # the ring's triangles and dots
        a = math.radians(90 * k)
        tx, ty = cx + r * math.cos(a), cy - r * math.sin(a)
        reg.poly([(tx + 1.4 * math.cos(a), ty - 1.4 * math.sin(a)),
                  (tx - 1.2 * math.cos(a) + 1.3 * math.sin(a), ty + 1.2 * math.sin(a) + 1.3 * math.cos(a)),
                  (tx - 1.2 * math.cos(a) - 1.3 * math.sin(a), ty + 1.2 * math.sin(a) - 1.3 * math.cos(a))], ink)
        b = a + math.pi / 4
        reg.circle(cx + r * math.cos(b), cy - r * math.sin(b), 0.6, ink)
    reg.text("CD-i", "arialbi.ttf", 9.0, *at(2.0, 80.0), shade(CASE, -0.12))
    for k, (bx, by) in enumerate(L.PAD["buttons"]["at"]):   # the buttons' dots
        tx, ty = at(bx, by + L.PAD["buttons"]["r"] + 3.6)
        text = ("•", "••", "•+••")[k]
        reg.text(text, "seguisym.ttf", 2.6, tx, ty, ink)
    reg.text("SPEED", "arialbd.ttf", 2.4, *at(52.0, 22.0), ink)
    reg.text("I  II  III", "arial.ttf", 2.0, *at(64.0, 14.0), ink)
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (front(), display("display"), display("display_disc"), display("display_play"), disc_top(), pad()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("case", CASE), ("button", rgb(L.COLOURS["button"])), ("black", rgb(L.COLOURS["black"])),
                         ("silver", (200, 204, 210)), ("dark", shade(CASE, -0.4))):
        x, y = L.SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    path = os.path.join(out, "cdi_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
