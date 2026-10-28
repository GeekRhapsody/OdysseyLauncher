"""The PlayStation Vita's printing and screens, for the console theme's PS Vita model (psvita.py) and its video
(psvita_video.py). psvita_layout.py has the measurements and where each part is in the atlases.

Writes three images into a folder:
- psvita_print.png: the face seen square on (the glossy black panel; the gunmetal frame showing round its edge and
  looping round the bottom corners' holes; the chrome shoulder buttons' crescents; SONY; the screen's surround; the
  wells the D-pad and the left stick, and the face buttons and the right stick, sit in; the D-pad's arms and their
  arrows, the face buttons and their symbols, the sticks' chrome bezels and their caps, the PS button, SELECT and START,
  the front camera and the speakers' holes; PS VITA under the screen); the top edge seen from above (the frame's
  strip: L and R, POWER, the PS Vita card slot's cover with PS VITA on it, the accessory port's cover, VOL - and +);
  the bottom edge seen from below (the multi-use connector, the headset jack, two screws); the PS button's top lit
  blue; and the swatches small parts take their colour from.
- psvita_rear.png: the back seen from behind (the rear touch pad and its pattern of the four shapes, the two finger
  grips, the label, the screws, the memory card slot's cover and the microphone, the rear camera).
- psvita_screen.png: the glass with the OLED switched off: the still of the model's `video` material, and the first
  and last frame of the card's video.

The screens the video shows are drawn here too, laid out in the OLED's own 960 x 544 pixels at 1.5 times them (twice
the video's picture), then halved: the lock screen, its corner peeled away by a finger; the home screen's bubbles; the
game's LiveArea, its gate with Start (Continue once the game is paused), peeled away to close the game; the game's
publisher, its title and the fight. A touch is drawn as Sony's guide draws one, a soft white circle where the finger
is. The game is made up (no real game's art): Voltcrown, Arcwave's fighting game, its logo from the made-up games'
library, its key art, its empty arena and its two fighters' poses painted by Codex for this card (paintings.py:
vita_keyart, vita_arena, vita_juno, vita_sable). The fighters are cut out of their green and moved over the arena, as a
2.5D fighting game draws them, under the HUD the library draws Voltcrown's with (screens._versus).

Make the made-up games' library and the paintings first (tools/made-up-games/README.md; paintings.py), then run it with
the system Python (Pillow, numpy, scipy):

    python tools/console-models/psvita_print.py artifacts/made-up-games artifacts/psvita
"""

import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psvita_layout as L  # noqa: E402
from arcade_print import Game, painting  # noqa: E402
from psp_print import Canvas, font, glossy, grown, paste_region, ps_mark, rgb, symbol  # noqa: E402

CASE = L.COLOURS["case"]
FRAME = L.COLOURS["frame"]
CHROME = L.COLOURS["chrome"]
REAR = L.COLOURS["rear"]
TOP = "#1F2025"        # the buttons' tops
LEGEND = "#B4B8BF"     # the grey printing
WHITE = (255, 255, 255)


def ellipse(c, x, z, rx, rz, fill):
    (x0, y0), (x1, y1) = c.p(x - rx, z + rz), c.p(x + rx, z - rz)
    c.draw.ellipse([x0, y0, x1, y1], fill=fill)


def gradient(c, polygon, top, bottom, z0, z1):
    """A polygon filled with a vertical gradient, top at z1 to bottom at z0."""
    _, y1 = c.p(0.0, z0)
    _, y0 = c.p(0.0, z1)
    ramp = Image.linear_gradient("L").resize((1, max(2, round(y1 - y0))))
    strip = Image.composite(Image.new("RGBA", ramp.size, rgb(bottom)), Image.new("RGBA", ramp.size, rgb(top)), ramp)
    layer = c.layer()
    layer.paste(strip.resize((c.img.width, strip.height)), (0, round(y0)))
    mask = Image.new("L", c.img.size, 0)
    ImageDraw.Draw(mask).polygon([c.p(x, z) for x, z in polygon], fill=255)
    c.over(layer, mask)


def mask_of(c, draw):
    """A boolean array of the canvas's pixels draw(ImageDraw) fills."""
    m = Image.new("L", c.img.size, 0)
    draw(ImageDraw.Draw(m))
    return np.asarray(m) > 127


def well(c, circles, close):
    """A shallow well in the panel: the circles ((x, z, r), ...) merged into one smooth outline (closed by close mm),
    a little darker inside; a hairline of light round its edge and a shadow just inside it."""
    m = mask_of(c, lambda d: [d.ellipse([*c.p(x - r, z + r), *c.p(x + r, z - r)], fill=255) for x, z, r in circles])
    r = close * c.s
    grown_ = ndimage.distance_transform_edt(~m) <= r
    m = ndimage.distance_transform_edt(grown_) > r
    inner = ndimage.distance_transform_edt(m)
    outer = ndimage.distance_transform_edt(~m)
    shade = np.zeros(m.shape, np.float32)
    shade[m] = 0.18
    tint = Image.fromarray((shade * 255).astype(np.uint8))
    c.over(Image.new("RGBA", c.img.size, (0, 0, 0, 255)), tint)
    light = np.clip(1.6 - np.abs(outer - 0.8) / 0.9, 0, 1) * (~m)
    c.over(Image.new("RGBA", c.img.size, (70, 72, 80, 255)), Image.fromarray((light * 200).astype(np.uint8)))
    dark = np.clip(1 - np.abs(inner - 2.0) / 2.2, 0, 1) * m
    c.over(Image.new("RGBA", c.img.size, (0, 0, 0, 255)), Image.fromarray((dark * 230).astype(np.uint8)))


def strokes(c, paths, width, fill):
    for path in paths:
        c.line(path, width, fill)


def vita_logo(c, x, z, width, fill):
    """PS VITA in its strokes, width wide, centred on (x, z): the P open at its top left, its stem dropping from its
    middle bar; the S slanting under the P's bowl; V, I, T and A."""
    cap = width / 6.11
    w = 0.16 * cap
    x0, z0 = x - width / 2, z - cap / 2

    def at(u, v):
        return (x0 + u * cap, z0 + v * cap)

    h = w / cap / 2
    paths = [[at(0.0 + h, 1 - h), at(1.02 - h, 1 - h), at(1.02 - h, 0.5), at(0.0 + h + 0.02, 0.5), at(0.0 + h + 0.02, 0.0)],
             [at(2.24, 1 - h), at(1.68, 1 - h), at(1.50, h), at(0.97, h)],
             [at(2.42 + h, 1.0), at(2.97, h), at(3.52 - h, 1.0)],
             [at(3.78, 0.0), at(3.78, 1.0)],
             [at(4.05, 1 - h), at(5.12, 1 - h)], [at(4.585, 1 - h), at(4.585, 0.0)],
             [at(4.92, 0.0), at(5.5, 1.0 - h), at(6.08, 0.0)], [at(5.2, 0.33), at(5.8, 0.33)]]
    strokes(c, paths, w, fill)


def brushed(c, x0, x1, z0, z1, seed):
    """Fine grain along a strip, as the frame's metal has."""
    grain = c.layer()
    d = ImageDraw.Draw(grain)
    rng = random.Random(seed)
    for _ in range(int((z1 - z0) * 26)):
        zz = rng.uniform(z0, z1)
        d.line([c.p(x0, zz), c.p(x1, zz)], fill=(255, 255, 255, rng.randint(4, 16)), width=1)
    c.over(grain)


# ---- The face ---------------------------------------------------------------------------------------------------------

def front():
    c = Canvas(L.PRINT_REGIONS["front"]["mm"], rgb(FRAME))
    # The panel: glossy black, a little lighter towards its top; a hairline of light just inside its edge.
    gradient(c, L.body_outline(L.FRAME_EDGE), "#17181C", "#0D0D10", 0.0, L.HEIGHT)
    c.outline(L.body_outline(L.FRAME_EDGE + 0.25), 0.16, rgb("#34363C"))
    for side in (-1, 1):
        # The frame's loop round the bottom corner's hole (which psvita.py cuts through), and the shoulder button's
        # chrome crescent, lighter at its top, the gap round it dark.
        c.polygon(L.notch_region(side), rgb(FRAME))
        top = [(x, z + L.FRAME_EDGE) for x, z in L.smooth_path(L.HOLE_TOP, 5)]
        c.line(top if side < 0 else [(-x, z) for x, z in top], 0.16, rgb("#34363C"))
        c.polygon(L.hole_outline(side), rgb(L.COLOURS["dark"]))
        gradient(c, L.shoulder_region(side), "#E9ECEF", "#868B93", 66.0, L.HEIGHT)
        curve = L.smooth_path(L.SHOULDER_CURVE, 6)
        c.line(curve if side < 0 else [(-x, z) for x, z in curve], 0.3, rgb("#050506"))
    # The screen's surround: the video's glass covers its middle.
    (gx0, gx1), (gz0, gz1) = L.GLASS["x"], L.GLASS["z"]
    c.rounded(gx0 - 0.5, gx1 + 0.5, gz0 - 0.5, gz1 + 0.5, 1.2, rgb("#26272C"))
    c.rounded(gx0 - 0.2, gx1 + 0.2, gz0 - 0.2, gz1 + 0.2, 0.9, rgb(L.COLOURS["glass"]))
    # The wells: the D-pad's and the left stick's; the face buttons' and the right stick's.
    (sx, sz), (rx, rz) = L.STICKS["left"], L.STICKS["right"]
    well(c, [(L.DPAD["x"], L.DPAD["z"], L.DPAD["well"]), (sx, sz, L.STICK["well"])], 3.2)
    well(c, [(x, z, L.FACE["radius"] + 0.8) for _, x, z in L.face_centres()] + [(L.FACE["x"], L.FACE["z"], 7.0),
                                                                              (rx, rz, L.STICK["well"])], 3.2)
    dpad(c)
    face_buttons(c)
    sticks(c)
    small_buttons(c)
    # The front camera, the speakers' holes, SONY and PS VITA.
    x, z, r = L.CAMERA["x"], L.CAMERA["z"], L.CAMERA["r"]
    c.circle(x, z, r, rgb("#3B3E45"))
    c.circle(x, z, r - 0.45, rgb(L.COLOURS["lens"]))
    c.circle(x - 0.35, z + 0.35, 0.28, rgb("#7E8DAA"))
    for side in (-1, 1):
        for x in L.SPEAKER_X:
            for z in L.SPEAKER_Z:
                c.circle(side * x, z, L.SPEAKER_R + 0.12, rgb("#2B2C31"))
                c.circle(side * x, z, L.SPEAKER_R, rgb("#030304"))
    s = L.SONY
    c.text("SONY", "timesbd.ttf", s["cap"], s["x"], s["z"], rgb("#C9CCD2"), stretch=1.18, spacing=0.18)
    vita_logo(c, L.LOGO["x"], L.LOGO["z"], L.LOGO["width"], rgb("#D2D5DA"))
    return c


def dpad(c):
    cx, cz = L.DPAD["x"], L.DPAD["z"]
    for _, a in L.DPAD_BUTTONS:
        corners, radii = L.dpad_arm(a)
        c.polygon(L.rounded_polygon(grown(corners, (cx, cz), 0.55), [r + 0.45 for r in radii]), rgb(CASE, 0.35))
    for _, a in L.DPAD_BUTTONS:
        corners, radii = L.dpad_arm(a)
        c.polygon(L.rounded_polygon(corners, radii), rgb(TOP))
        # Its arrow, a small hollow triangle pointing out.
        co, si = math.cos(math.radians(a)), math.sin(math.radians(a))
        mx, mz = cx + 7.7 * co, cz + 7.7 * si
        c.outline([(mx + 1.1 * co, mz + 1.1 * si), (mx - 0.7 * co - 1.2 * si, mz - 0.7 * si + 1.2 * co),
                   (mx - 0.7 * co + 1.2 * si, mz - 0.7 * si - 1.2 * co)], 0.22, rgb(LEGEND))


def face_buttons(c):
    r = L.FACE["radius"]
    for name, x, z in L.face_centres():
        c.circle(x, z, r + 0.6, rgb(CASE, 0.3))
        glossy(c, x, z, r, TOP)
        symbol(c, name, x, z, r * 0.48, 0.3, rgb("#BDC1C8"))


def sticks(c):
    """Each stick's recess and chrome bezel, and its cap's dished top where it rests (psvita.py's cap takes it)."""
    for x, z in L.STICKS.values():
        b, cap = L.STICK["bezel"], L.STICK["cap"]
        c.circle(x, z, b + 0.35, rgb("#040405"))
        c.ring(x, z, b - 0.1, 0.55, rgb("#A3A8B0"))
        c.circle(x, z, b - 0.4, rgb(L.COLOURS["dark"]))
        c.circle(x, z, cap, rgb("#2C2D32"))
        c.circle(x, z, cap - 0.5, rgb("#1B1B1F"))
        dish = c.layer()
        d = ImageDraw.Draw(dish)
        for k in range(10):
            rr = (cap - 0.6) * (1 - k / 11)
            v = 26 + k * 2
            d.ellipse([*c.p(x - rr + 0.06 * k, z + rr - 0.06 * k), *c.p(x + rr + 0.06 * k, z - rr - 0.06 * k)],
                      fill=(v, v, v + 4, 255))
        c.over(dish)
        c.ring(x, z, cap - 0.3, 0.12, rgb("#4A4C52"))


def small_buttons(c):
    x, z = L.PS["x"], L.PS["z"]
    hx, hz = L.PS["half"]
    ellipse(c, x, z, hx + 0.55, hz + 0.55, rgb(CASE, 0.3))
    ps_top(c, x, z, lit=False)
    hx, hz = L.SMALL["half"]
    for name in ("SELECT", "START"):
        x, z = L.SMALL[name]
        ellipse(c, x, z, hx + 0.45, hz + 0.45, rgb(CASE, 0.3))
        ellipse(c, x, z, hx, hz, rgb(TOP))
        ellipse(c, x, z + 0.25, hx - 0.5, hz - 0.6, rgb("#25262B"))
        c.text(name, "arialbd.ttf", 0.78, x, z, rgb(LEGEND), stretch=0.92)


def ps_top(c, x, z, lit):
    """The PS button's top: dark and glossy with the PlayStation mark, or lit, the mark and its rim glowing blue."""
    hx, hz = L.PS["half"]
    ellipse(c, x, z, hx, hz, rgb(TOP))
    ellipse(c, x, z + 0.35, hx - 0.7, hz - 0.8, rgb("#26272C"))
    if lit:
        glow = c.layer()
        gd = ImageDraw.Draw(glow)
        gd.ellipse([*c.p(x - hx + 0.1, z + hz - 0.1), *c.p(x + hx - 0.1, z - hz + 0.1)], outline=rgb(L.COLOURS["lit"]),
                   width=round(0.5 * c.s))
        c.over(glow.filter(ImageFilter.GaussianBlur(0.5 * c.s)))
        c.over(glow)
        ps_mark(c, x, z, 3.0, rgb("#9CD0FF"), rgb("#26272C"))
        halo = c.layer()
        ImageDraw.Draw(halo).ellipse([*c.p(x - 2.0, z + 2.0), *c.p(x + 2.0, z - 2.0)], fill=(80, 170, 255, 140))
        c.over(halo.filter(ImageFilter.GaussianBlur(0.9 * c.s)))
        ps_mark(c, x, z, 3.0, rgb("#E4F2FF"), rgb("#2C3E58"))
    else:
        ps_mark(c, x, z, 3.0, rgb("#BDC1C8"), rgb("#26272C"))


def lit():
    """The PS button's top lit (its region is about the button's middle)."""
    c = Canvas(L.PRINT_REGIONS["lit"]["mm"], rgb(TOP))
    ps_top(c, 0.0, 0.0, lit=True)
    return c


# ---- The edges --------------------------------------------------------------------------------------------------------

def edge(region, face_at_bottom):
    """A canvas for an edge seen square on, x along it and its depth y up the region (the top edge, its face at the
    bottom) or down it (the bottom edge, its face at the top): .q(x, y) is where (x, y) is drawn."""
    x0, x1, y0, y1 = L.PRINT_REGIONS[region]["mm"]
    if face_at_bottom:
        c = Canvas((x0, x1, y0, y1), rgb(REAR))
        c.q = lambda x, y: (x, y)
    else:
        c = Canvas((x0, x1, -y1, -y0), rgb(REAR))
        c.q = lambda x, y: (x, -y)
    return c


def strip(c, seed):
    """An edge's bands: the panel's edge, the frame (brushed), the back's shell."""
    q = c.q
    (ax, ay), (bx, by) = q(-95.0, -1.0), q(95.0, L.PANEL)
    c.rounded(ax, bx, min(ay, by), max(ay, by), 0.0, rgb(CASE))
    (ax, ay), (bx, by) = q(-95.0, L.BAND[0]), q(95.0, L.BAND[1])
    c.rounded(ax, bx, min(ay, by), max(ay, by), 0.0, rgb(FRAME))
    brushed(c, -95.0, 95.0, min(ay, by), max(ay, by), seed)


def box(c, x0, x1, y0, y1, r, fill, line=None):
    (ax, ay), (bx, by) = c.q(x0, y0), c.q(x1, y1)
    if line:
        c.rounded(ax - 0.2, bx + 0.2, min(ay, by) - 0.2, max(ay, by) + 0.2, r + 0.2, line)
    c.rounded(ax, bx, min(ay, by), max(ay, by), r, fill)


def top():
    """The top edge seen from above, its face towards the bottom: L and R over the corners; the housing with POWER,
    the PS Vita card slot's cover (PS VITA on it) and the accessory port's cover; VOL - and +."""
    c = edge("top", True)
    strip(c, 1101)
    q = c.q
    t = L.TOP
    for (x0, x1), letter, lx in ((t["L"], "L", -60.5), (t["R"], "R", 61.0)):
        box(c, -95.0 if x0 < 0 else x0, x1 if x0 < 0 else 95.0, L.BAND[0], 19.6, 0.0, rgb(CHROME))
        a, b = q(x0, t["pill_y"][0]), q(x1, t["pill_y"][1])
        c.polygon(L.stadium(a[0], b[0], min(a[1], b[1]), max(a[1], b[1])), rgb("#8E939B"))
        c.polygon(L.stadium(a[0] + 0.3, b[0] - 0.3, min(a[1], b[1]) + 0.3, max(a[1], b[1]) - 0.3), rgb("#DCDFE3"))
        c.text(letter, "arialbd.ttf", 1.6, *q(lx, sum(t["pill_y"]) / 2), rgb("#4A4D54"))
    box(c, *t["housing"], *t["housing_y"], 0.8, rgb(FRAME, 0.78), rgb("#2E3035"))
    box(c, *t["card"], *t["cover_y"], 0.6, rgb(FRAME, 0.94), rgb("#2E3035"))
    vita_logo(c, (t["card"][0] + t["card"][1]) / 2, q(0, sum(t["cover_y"]) / 2)[1], 13.0, rgb("#D8DBE0"))
    box(c, *t["port"], *t["cover_y"], 0.6, rgb(FRAME, 0.9), rgb("#2E3035"))
    box(c, *t["vol"], *t["housing_y"], 0.8, rgb(FRAME, 0.78), rgb("#2E3035"))
    # POWER (psvita.py's button takes its top from here), VOL - and +.
    x, y = L.POWER["x"], L.POWER["y"]
    c.circle(*q(x, y), L.POWER["r"] + 0.4, rgb("#141417"))
    c.circle(*q(x, y), L.POWER["r"], rgb(TOP))
    px, pz = q(x, y)
    c.line([(px + 1.2 * math.cos(math.radians(a)), pz + 1.2 * math.sin(math.radians(a))) for a in range(120, 421, 15)],
           0.28, rgb(LEGEND))
    c.line([(px, pz + 0.2), (px, pz + 1.6)], 0.28, rgb(LEGEND))
    for x, plus in ((t["minus"], False), (t["plus"], True)):
        cx, cz = q(x, sum(t["housing_y"]) / 2)
        c.circle(cx, cz, L.VOLUME["r"] + 0.35, rgb("#141417"))
        glossy(c, cx, cz, L.VOLUME["r"], TOP)
        c.line([(cx - 0.9, cz), (cx + 0.9, cz)], 0.26, rgb(LEGEND))
        if plus:
            c.line([(cx, cz - 0.9), (cx, cz + 0.9)], 0.26, rgb(LEGEND))
    c.text("VOL", "arialbd.ttf", 0.8, *q((t["minus"] + t["plus"]) / 2, sum(t["housing_y"]) / 2), rgb(LEGEND))
    return c


def bottom():
    """The bottom edge seen from below, its face towards the top: the multi-use connector, its screws, the headset
    jack."""
    c = edge("bottom", False)
    strip(c, 2011)
    q, b = c.q, L.BOTTOM
    box(c, *b["connector"], *b["connector_y"], 0.5, rgb("#060607"), rgb("#6C7078"))
    box(c, b["connector"][0] + 1.4, b["connector"][1] - 1.4, 5.1, 5.7, 0.2, rgb("#8C9098"))
    x, z = q(b["jack"], b["y"])
    c.circle(x, z, b["jack_r"] + 0.45, rgb("#5A5E66"))
    c.circle(x, z, b["jack_r"], rgb("#050506"))
    for sx in b["screws"]:
        x, z = q(sx, b["y"])
        c.circle(x, z, 0.95, rgb("#6F737B"))
        c.line([(x - 0.55, z), (x + 0.55, z)], 0.2, rgb("#3A3D43"))
        c.line([(x, z - 0.55), (x, z + 0.55)], 0.2, rgb("#3A3D43"))
    return c


def swatches(image, places, colours):
    d = ImageDraw.Draw(image)
    for name, (x, y) in places.items():
        d.rectangle([x - 10, y - 10, x + 9, y + 9], fill=rgb(colours[name]))


def print_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(CASE))
    for name, draw in (("front", front), ("top", top), ("bottom", bottom), ("lit", lit)):
        paste_region(image, L.PRINT_REGIONS[name]["px"], draw())
    swatches(image, L.SWATCHES, dict(L.COLOURS, buttons=TOP))
    return image


# ---- The back ---------------------------------------------------------------------------------------------------------

def rear():
    """The back, seen from behind (x is the face's, negated): the touch pad's rows of the four shapes, the finger
    grips, the label under the pad, the screws, the memory card slot's cover and the microphone by the bottom edge, the
    rear camera at the top."""
    c = Canvas(L.REAR_REGIONS["rear"]["mm"], rgb(REAR))
    (x0, x1), (z0, z1) = L.TOUCHPAD["x"], L.TOUCHPAD["z"]
    c.rounded(x0 - 0.4, x1 + 0.4, z0 - 0.4, z1 + 0.4, 1.0, rgb(REAR, 0.8))
    c.rounded(x0, x1, z0, z1, 0.8, rgb("#202024"))
    pitch = L.TOUCHPAD["pitch"]
    shapes = ("triangle", "circle", "cross", "square")
    rows = int((z1 - z0 - 1.0) / pitch)
    cols = int((x1 - x0 - 1.0) / pitch)
    for j in range(rows):
        for i in range(cols):
            x = x0 + 1.6 + i * pitch
            z = z1 - 1.6 - j * pitch
            symbol(c, shapes[(i + j) % 4], x, z, 0.62, 0.13, rgb("#3A3B41"))
    gx, gz = L.GRIPS["x"], L.GRIPS["z"]
    hx, hz = L.GRIPS["half"]
    for side in (-1, 1):
        ellipse(c, side * gx, gz, hx + 0.35, hz + 0.35, rgb(REAR, 0.7))
        ellipse(c, side * gx, gz, hx, hz, rgb("#18181B"))
    # The label under the pad.
    c.rounded(-50.0, 50.0, 12.6, 23.2, 0.6, rgb(REAR, 1.12))
    ink = rgb("#4C4E54")
    c.text("SONY", "timesbd.ttf", 1.5, 0.0, 21.4, ink, stretch=1.15, spacing=0.12)
    c.text("MODEL PCH-1004   PlayStation®Vita   DC 5V 1.2A", "arial.ttf", 0.95, 0.0, 18.8, ink)
    c.text("Sony Computer Entertainment Inc.", "arial.ttf", 0.95, 0.0, 16.6, ink)
    c.text("MADE IN CHINA      4-412-811-01", "arial.ttf", 0.75, 0.0, 14.4, ink)
    c.text("CE", "arialbd.ttf", 1.6, -44.0, 17.6, ink)
    for x, z in L.SCREWS:
        c.circle(-x, z, 1.25, rgb(REAR, 0.55))
        c.circle(-x, z, 0.8, rgb(REAR, 0.85))
    (sx0, sx1), (sz0, sz1) = L.CARD_SLOT["x"], L.CARD_SLOT["z"]
    c.rounded(-sx1 - 0.3, -sx0 + 0.3, sz0 - 0.3, sz1 + 0.3, 0.6, rgb(REAR, 0.55))
    c.rounded(-sx1, -sx0, sz0, sz1, 0.5, rgb(REAR, 1.15))
    c.rounded(-L.MIC["x"] - 0.4, -L.MIC["x"] + 0.4, L.MIC["z"] - 0.9, L.MIC["z"] + 0.9, 0.3, rgb("#050506"))
    # The rear camera's pod (psvita.py's pod takes its back from here).
    p = L.POD
    c.polygon(L.stadium(-p["half_width"], p["half_width"], *p["z"]), rgb("#141417"))
    lx, lz = p["lens"]
    c.circle(-lx, lz, p["lens_r"] + 0.3, rgb("#4A4D54"))
    c.circle(-lx, lz, p["lens_r"], rgb(L.COLOURS["lens"]))
    c.circle(-lx - 0.5, lz + 0.5, 0.35, rgb("#7E8DAA"))
    return c


def rear_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(REAR))
    paste_region(image, L.REAR_REGIONS["rear"]["px"], rear())
    swatches(image, L.REAR_SWATCHES, dict(rear=REAR, pod="#141417"))
    return image


# ---- The screens --------------------------------------------------------------------------------------------------------
# Laid out in the OLED's own 960 x 544 pixels, drawn at K times them (twice the video's picture) and halved.

K = L.LCD_PX[0] * 2 / L.NATIVE[0]
W2, H2 = L.LCD_PX[0] * 2, L.LCD_PX[1] * 2
BORDER = (5, 5, 6)
OFF = (13, 14, 17)
_CACHE = {}


def n(v):
    return v * K


def ui(px, weight="segoeui.ttf"):
    return font(weight, n(px))


def half(img):
    return img.convert("RGB").resize(L.LCD_PX, Image.LANCZOS)


def made_up(made_up_dir):
    """The game: a made-up game from tools/made-up-games's library (arcade_print.Game)."""
    stem, system = L.MADE_UP
    return Game(stem, made_up_dir, system)


def fit(img, size, centre=(0.5, 0.5)):
    return ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS, centering=centre)


def sheen(size, strength):
    """The glass's reflection: a soft diagonal band of light, the same on every frame."""
    w, h = size
    band = Image.new("L", size, 0)
    ImageDraw.Draw(band).polygon([(w * 0.1, 0), (w * 0.38, 0), (w * 0.2, h), (-w * 0.08, h)], fill=255)
    return band.filter(ImageFilter.GaussianBlur(w * 0.06)).point(lambda v: round(v * strength))


def glass(lcd=None, off=1.0):
    """The glass's frame, VIDEO_PX: black round the OLED, which shows lcd (LCD_PX) or, without it, is switched off.
    off (0 to 1) mixes lcd towards the switched-off OLED."""
    if "sheen" not in _CACHE:
        _CACHE["sheen"] = sheen(L.VIDEO_PX, 0.05)
        _CACHE["panel"] = Image.new("RGB", L.LCD_PX, OFF)
    frame = Image.new("RGB", L.VIDEO_PX, BORDER)
    panel = _CACHE["panel"] if lcd is None else lcd.convert("RGB")
    if lcd is not None and off > 0:
        panel = Image.blend(panel, _CACHE["panel"], min(1.0, off))
    frame.paste(panel, L.LCD_AT)
    return Image.composite(Image.new("RGB", L.VIDEO_PX, WHITE), frame, _CACHE["sheen"])


def still():
    """The switched-off screen: the video's material's own texture, and its first and last frame."""
    return glass()


def touch(img, x, y, press=1.0, ripple=0.0):
    """A fingertip on the glass of the LCD-sized img, at (x, y) in the OLED's pixels, as Sony's guide draws one: a
    soft white disc with a brighter ring (press, 0 to 1, how firmly); ripple (0 to 1) a tap's ring spreading out."""
    s = L.LCD_PX[0] / L.NATIVE[0]
    cx, cy = x * s, y * s
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = 26 * s * (1.08 - 0.08 * press)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, round(70 * press)),
              outline=(255, 255, 255, round(190 * press)), width=max(1, round(2.4 * s)))
    if ripple > 0:
        rr = r * (1 + 1.4 * ripple)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, round(150 * (1 - ripple))),
                  width=max(1, round(2 * s)))
    out = img.convert("RGBA")
    out.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))
    return out.convert("RGB")


# The home screen, as Sony's guide shows it: its wallpaper, deep blue with a sweep of light across it; three rows of
# bubbles under the info bar; the page's dots at the left and an arrow to the LiveArea pages at the right.

BUBBLES = [("settings", "Settings", 260, 150), ("trophies", "Trophies", 485, 150), ("friends", "Friends", 710, 150),
           ("music", "Music", 150, 295), ("photos", "Photos", 375, 295), ("game", "Voltcrown", 595, 295),
           ("browser", "Browser", 815, 295), ("videos", "Videos", 260, 445), ("messages", "Messages", 485, 445),
           ("calendar", "Calendar", 710, 445)]
BUBBLE_D = 124
GAME_BUBBLE = next((x, y) for kind, _, x, y in BUBBLES if kind == "game")


def wallpaper():
    if "wallpaper" not in _CACHE:
        w, h = W2, H2
        t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        top, mid, low = np.array([2, 12, 40], np.float32), np.array([18, 66, 160], np.float32), np.array([6, 34, 96], np.float32)
        col = np.where(t < 0.64, top + (mid - top) * (t / 0.64), mid + (low - mid) * ((t - 0.64) / 0.36))
        img = np.broadcast_to(col, (h, w, 3)).astype(np.float32).copy()
        sweep = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(sweep)
        pts = [(x, h * (0.7 - 0.16 * (x / w) + 0.06 * math.sin(math.pi * x / w))) for x in range(-60, w + 80, 20)]
        d.line(pts, fill=255, width=round(n(36)))
        wide = np.asarray(sweep.filter(ImageFilter.GaussianBlur(n(46)))).astype(np.float32)[..., None] / 255
        core = np.asarray(sweep.filter(ImageFilter.GaussianBlur(n(7)))).astype(np.float32)[..., None] / 255
        img += wide * np.array([70, 150, 255], np.float32) * 0.85 + core * np.array([190, 230, 255], np.float32) * 0.5
        streak = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(streak)
        for k in range(5):
            y0 = h * (0.5 + 0.06 * k)
            d.line([(x, y0 - 0.12 * h * (x / w) + 8 * math.sin(x / 90 + k)) for x in range(0, w + 20, 20)], fill=90,
                   width=2)
        img += np.asarray(streak.filter(ImageFilter.GaussianBlur(2))).astype(np.float32)[..., None] / 255 * 120
        _CACHE["wallpaper"] = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return _CACHE["wallpaper"].copy()


def icon(kind, game):
    """A bubble's picture, 256 square: the game's key art, or a pictogram on a colour."""
    size = 256
    if kind == "game":
        art = fit(painting("vita_keyart"), (size, size), (0.36, 0.62))
        return ImageEnhance.Brightness(ImageEnhance.Contrast(art).enhance(1.15)).enhance(1.45).convert("RGBA")
    grounds = dict(settings=("#9AA6B8", "#3C4656"), trophies=("#2A3E8A", "#0C1640"), friends=("#59B7F0", "#1A5FB0"),
                   music=("#D25BD4", "#5E1F8E"), photos=("#F6B042", "#C2561A"), browser=("#4FD3F2", "#0A6CB2"),
                   videos=("#E2453F", "#7A0F18"), messages=("#7FD6FF", "#2A7FD8"), calendar=("#F4F4F6", "#B9BEC8"))
    a, b = grounds[kind]
    img = Image.composite(Image.new("RGB", (size, size), rgb(b)[:3]), Image.new("RGB", (size, size), rgb(a)[:3]),
                          Image.linear_gradient("L").resize((size, size))).convert("RGBA")
    d = ImageDraw.Draw(img)
    w = (255, 255, 255, 255)
    if kind == "settings":
        for k in range(8):
            t = math.radians(k * 45)
            d.line([(128 + 50 * math.cos(t), 128 + 50 * math.sin(t)), (128 + 86 * math.cos(t), 128 + 86 * math.sin(t))],
                   fill=w, width=34)
        d.ellipse([58, 58, 198, 198], fill=w)
        d.ellipse([100, 100, 156, 156], fill=rgb("#5C6779"))
    elif kind == "trophies":
        gold = rgb("#F4C640")
        d.chord([70, 40, 186, 170], 0, 180, fill=gold)
        d.rectangle([70, 40, 186, 104], fill=gold)
        d.arc([40, 56, 96, 120], 90, 270, fill=gold, width=12)
        d.arc([160, 56, 216, 120], 270, 90, fill=gold, width=12)
        d.rectangle([118, 160, 138, 196], fill=gold)
        d.rounded_rectangle([86, 192, 170, 214], 6, fill=gold)
    elif kind == "friends":
        for (x, y, colour) in ((92, 140, "#3A8BEA"), (160, 104, "#EF4C4C")):
            d.rounded_rectangle([x - 54, y - 54, x + 54, y + 54], 26, fill=rgb(colour))
            d.ellipse([x - 26, y - 14, x - 12, y + 4], fill=w)
            d.ellipse([x + 12, y - 14, x + 26, y + 4], fill=w)
            d.arc([x - 24, y - 4, x + 24, y + 30], 20, 160, fill=w, width=7)
    elif kind == "music":
        d.ellipse([60, 160, 128, 212], fill=w)
        d.rectangle([112, 58, 128, 186], fill=w)
        d.polygon([(112, 58), (196, 42), (196, 74), (128, 88)], fill=w)
        d.ellipse([140, 140, 200, 186], fill=w)
        d.rectangle([184, 50, 198, 166], fill=w)
    elif kind == "photos":
        d.rounded_rectangle([46, 84, 210, 194], 18, fill=(30, 30, 34, 255))
        d.rounded_rectangle([92, 64, 164, 96], 10, fill=(30, 30, 34, 255))
        d.ellipse([92, 104, 164, 176], fill=(200, 205, 215, 255))
        d.ellipse([106, 118, 150, 162], fill=(24, 28, 40, 255))
    elif kind == "browser":
        d.ellipse([44, 44, 212, 212], outline=w, width=14)
        d.ellipse([90, 44, 166, 212], outline=w, width=10)
        d.line([(44, 128), (212, 128)], fill=w, width=10)
        d.line([(60, 84), (196, 84)], fill=w, width=8)
        d.line([(60, 172), (196, 172)], fill=w, width=8)
    elif kind == "videos":
        d.rounded_rectangle([46, 66, 210, 190], 14, fill=(26, 10, 12, 255))
        d.polygon([(104, 92), (104, 164), (168, 128)], fill=w)
    elif kind == "messages":
        d.rounded_rectangle([44, 56, 212, 172], 40, fill=w)
        d.polygon([(84, 160), (72, 212), (128, 166)], fill=w)
        for x in (90, 128, 166):
            d.ellipse([x - 11, 103, x + 11, 125], fill=rgb("#2A7FD8"))
    elif kind == "calendar":
        d.rounded_rectangle([50, 52, 206, 206], 14, fill=w)
        d.rounded_rectangle([50, 52, 206, 96], 14, fill=rgb("#E2453F"))
        d.rectangle([50, 80, 206, 96], fill=rgb("#E2453F"))
        for j in range(3):
            for i in range(4):
                d.rectangle([66 + i * 36, 108 + j * 30, 88 + i * 36, 126 + j * 30], fill=(150, 156, 168, 255))
    return img


def bubble(kind, game):
    """A bubble, BUBBLE_D across (at K), as an RGBA image a little larger than it with its shadow: the picture in a
    glassy sphere, its rim catching the light and a highlight across its top."""
    if ("bubble", kind) in _CACHE:
        return _CACHE[("bubble", kind)]
    d = round(n(BUBBLE_D))
    size = round(d * 1.3)
    o = (size - d) // 2
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(shadow).ellipse([o + d * 0.06, o + d * 0.12, o + d * 0.94, o + d * 1.04], fill=150)
    out.putalpha(shadow.filter(ImageFilter.GaussianBlur(d * 0.05)))
    art = icon(kind, game).resize((d, d), Image.LANCZOS)
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    r = np.hypot(xx - d / 2, yy - d / 2) / (d / 2)
    shade = np.clip(1.05 - 0.45 * np.clip((r - 0.55) / 0.45, 0, 1) ** 1.6 - 0.18 * (yy / d), 0, 1.1)
    a = np.asarray(art.convert("RGB")).astype(np.float32) * shade[..., None]
    sphere = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d - 1, d - 1], fill=255)
    sphere.putalpha(mask)
    out.alpha_composite(sphere, (o, o))
    gloss = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.ellipse([d * 0.16, d * 0.05, d * 0.84, d * 0.5], fill=(255, 255, 255, 120))
    gloss = gloss.filter(ImageFilter.GaussianBlur(d * 0.04))
    rim = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse([1, 1, d - 2, d - 2], outline=(255, 255, 255, 150), width=max(2, d // 60))
    out.alpha_composite(gloss, (o, o))
    out.alpha_composite(rim, (o, o))
    _CACHE[("bubble", kind)] = out
    return out


def label(img, text, x, y, size=16):
    d = ImageDraw.Draw(img)
    f = ui(size)
    d.text((n(x) + 2, n(y) + 2), text, font=f, fill=(0, 0, 0, 170), anchor="mm")
    d.text((n(x), n(y)), text, font=f, fill=(255, 255, 255, 255), anchor="mm")


def info_bar(img, apps=(), game=None):
    """The info bar along the top: the Wi-Fi's signal at the left, the home screen's mark and the running
    applications' small bubbles in the middle, the time and the battery at the right, and the notification tab in
    the corner."""
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W2, n(30)], fill=(0, 0, 0, 235))
    w = (255, 255, 255, 255)
    for k in range(3):
        r = n(5 + k * 5)
        d.arc([n(22) - r, n(23) - r, n(22) + r, n(23) + r], 225, 315, fill=w, width=round(n(2.2)))
    d.ellipse([n(20.5), n(21.5), n(23.5), n(24.5)], fill=w)
    hx = n(410)
    d.polygon([(hx - n(9), n(15)), (hx, n(6)), (hx + n(9), n(15))], fill=w)
    d.rectangle([hx - n(6), n(15), hx + n(6), n(24)], fill=w)
    for k, kind in enumerate(apps):
        mini = bubble(kind, game).resize((round(n(30)), round(n(30))), Image.LANCZOS)
        img.alpha_composite(mini, (round(n(430 + 28 * k)), round(n(0))))
    d.text((n(838), n(15)), "21:43", font=ui(19), fill=w, anchor="rm")
    d.rounded_rectangle([n(846), n(8), n(878), n(22)], round(n(2)), outline=w, width=round(n(1.5)))
    d.rectangle([n(849), n(11), n(870), n(19)], fill=(120, 220, 120, 255))
    d.rectangle([n(879), n(12), n(882), n(18)], fill=w)
    d.pieslice([n(898), -n(62), n(1022), n(62)], 90, 180, fill=(32, 110, 230, 255))
    d.text((n(936), n(20)), "1", font=ui(22, "segoeuib.ttf"), fill=w, anchor="mm")


def home(t=0.0, pressed=0.0, apps=(), game=None, arrow=False, dim=1.0):
    """The home screen at t seconds: the bubbles bob a little; pressed (0 to 1) presses the game's bubble; dim (0 to 1)
    its brightness under the info bar."""
    img = wallpaper().convert("RGBA")
    d = ImageDraw.Draw(img)
    for k, y in enumerate((262, 282)):
        d.ellipse([n(20), n(y) - n(4), n(28), n(y) + n(4)], fill=(255, 255, 255, 230 if k == 0 else 110))
    if arrow:
        d.polygon([(n(930), n(280)), (n(946), n(295)), (n(930), n(310))], fill=(255, 255, 255, 220))
    for k, (kind, text, x, y) in enumerate(BUBBLES):
        bob = 2.2 * math.sin(t * 1.7 + k * 1.3)
        b = bubble(kind, game)
        if kind == "game" and pressed:
            s = 1 - 0.08 * pressed
            b = b.resize((round(b.width * s), round(b.height * s)), Image.LANCZOS)
        img.alpha_composite(b, (round(n(x) - b.width / 2), round(n(y + bob) - b.height / 2)))
        if kind == "game" and pressed:
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            r = n(BUBBLE_D / 2) * (1 - 0.08 * pressed)
            ImageDraw.Draw(glow).ellipse([n(x) - r, n(y + bob) - r, n(x) + r, n(y + bob) + r],
                                         fill=(255, 255, 255, round(70 * pressed)))
            img.alpha_composite(glow)
        label(img, text, x, y + bob + BUBBLE_D / 2 + 13)
    if dim < 1:
        img = ImageEnhance.Brightness(img).enhance(dim)
    info_bar(img, apps, game)
    return img


def lock_page():
    """The lock screen: the wallpaper dimmed, the time large at the lower left and the date under it."""
    img = ImageEnhance.Brightness(wallpaper()).enhance(0.5).convert("RGBA")
    d = ImageDraw.Draw(img)
    d.text((n(52), n(330)), "21:43", font=ui(118, "segoeuil.ttf"), fill=(255, 255, 255, 255), anchor="ls")
    d.text((n(58), n(380)), "Wednesday 28 October", font=ui(28), fill=(225, 232, 245, 255), anchor="ls")
    info_bar(img)
    return img


# The LiveArea: the game's page over the dimmed wallpaper, its title at the top left, two buttons over its middle, the
# gate (its picture in a silver frame, Start, or Continue once the game runs) with a live item each side.

PAGE = dict(x0=50, x1=910, y0=44)            # the page, in the OLED's pixels: it runs off the bottom
GATE = dict(x=480, y=290, w=300, h=170)
CURL = 30                                    # how far the page's top right corner is turned over at rest


def page_corner():
    return n(PAGE["x1"]), n(PAGE["y0"])


def live_page(game, gate_picture, paused=False, pressed=0.0):
    """The game's LiveArea page, RGBA, transparent round it."""
    page = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    x0, x1, y0 = n(PAGE["x0"]), n(PAGE["x1"]), n(PAGE["y0"])
    art = fit(painting("vita_keyart"), (round(x1 - x0), round(H2 + n(20) - y0)), (0.5, 0.35)).convert("RGBA")
    art = ImageEnhance.Brightness(art).enhance(0.72)
    shade = Image.new("RGBA", art.size, (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle([0, 0, art.width, n(70)], fill=(4, 6, 16, 170))
    art.alpha_composite(shade.filter(ImageFilter.GaussianBlur(n(18))))
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, art.width - 1, art.height + n(40)], round(n(10)), fill=255)
    art.putalpha(mask)
    page.alpha_composite(art, (round(x0), round(y0)))
    d = ImageDraw.Draw(page)
    d.text((x0 + n(20), y0 + n(20)), game.title, font=ui(26), fill=(255, 255, 255, 255), anchor="la")
    for k, glyph in enumerate(("?", "↻")):
        bx = n(452 + 58 * k)
        d.rounded_rectangle([bx - n(22), y0 + n(10), bx + n(22), y0 + n(54)], round(n(7)), fill=(240, 242, 246, 235),
                            outline=(170, 176, 188, 255), width=round(n(1.5)))
        d.text((bx, y0 + n(32)), glyph, font=ui(24, "segoeuib.ttf" if k == 0 else "seguisym.ttf"),
               fill=(206, 40, 52, 255) if k == 0 else (40, 110, 220, 255), anchor="mm")
    live_items(page, game)
    gate(page, gate_picture, paused, pressed)
    return page


def live_items(page, game):
    """A live item each side of the gate: a picture in a white frame and its caption."""
    items = [(185, "New fighter: Sable", fit(painting("vita_keyart"), (300, 200), (0.82, 0.6))),
             (775, "Volt League season 3", fit(painting("vita_arena"), (300, 200), (0.25, 0.35)))]
    d = ImageDraw.Draw(page)
    for x, caption, picture in items:
        w, h = n(150), n(100)
        cx, cy = n(x), n(GATE["y"] - 10)
        d.rounded_rectangle([cx - w / 2 - n(4), cy - h / 2 - n(4), cx + w / 2 + n(4), cy + h / 2 + n(4)], round(n(6)),
                            fill=(245, 246, 250, 255))
        page.alpha_composite(picture.resize((round(w), round(h)), Image.LANCZOS).convert("RGBA"),
                             (round(cx - w / 2), round(cy - h / 2)))
        f = ui(15)
        d.text((cx + 2, cy + h / 2 + n(20) + 2), caption, font=f, fill=(0, 0, 0, 200), anchor="mm")
        d.text((cx, cy + h / 2 + n(20)), caption, font=f, fill=(255, 255, 255, 255), anchor="mm")


def gate(page, picture, paused, pressed):
    """The gate: its picture in a silver frame, Start (Continue once the game runs) along its foot, lit as it's
    pressed."""
    g = GATE
    cx, cy, w, h = n(g["x"]), n(g["y"]), n(g["w"]), n(g["h"])
    d = ImageDraw.Draw(page)
    frame = Image.new("RGBA", (round(w + n(12)), round(h + n(12))), (0, 0, 0, 0))
    grad = Image.linear_gradient("L").resize(frame.size)
    metal = Image.composite(Image.new("RGBA", frame.size, (150, 156, 166, 255)), Image.new("RGBA", frame.size, (238, 240, 244, 255)),
                            grad)
    m = Image.new("L", frame.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, frame.width - 1, frame.height - 1], round(n(14)), fill=255)
    metal.putalpha(m)
    page.alpha_composite(metal, (round(cx - frame.width / 2), round(cy - frame.height / 2)))
    pic = picture.resize((round(w), round(h)), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", pic.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, pic.width - 1, pic.height - 1], round(n(10)), fill=255)
    pic.putalpha(m)
    page.alpha_composite(pic, (round(cx - w / 2), round(cy - h / 2)))
    bw, bh = n(150), n(36)
    by = cy + h / 2 - n(6)
    pill = Image.new("RGBA", (round(bw), round(bh)), (0, 0, 0, 0))
    top, bottom = (78, 168, 255), (16, 86, 206)
    if pressed:
        top = tuple(round(a + (255 - a) * 0.5 * pressed) for a in top)
        bottom = tuple(round(a + (255 - a) * 0.4 * pressed) for a in bottom)
    grad = Image.linear_gradient("L").resize(pill.size)
    fill = Image.composite(Image.new("RGBA", pill.size, bottom + (255,)), Image.new("RGBA", pill.size, top + (255,)), grad)
    m = Image.new("L", pill.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], round(bh / 2), fill=255)
    fill.putalpha(m)
    page.alpha_composite(fill, (round(cx - bw / 2), round(by - bh / 2)))
    d.rounded_rectangle([cx - bw / 2, by - bh / 2, cx + bw / 2, by + bh / 2], round(bh / 2), outline=(255, 255, 255, 220),
                        width=round(n(1.5)))
    d.text((cx, by), "Continue" if paused else "Start", font=ui(22), fill=(255, 255, 255, 255), anchor="mm")


def gate_picture(game):
    """The gate's picture before the game runs: its key art, its logo across it."""
    pic = fit(painting("vita_keyart"), (round(n(GATE["w"])) * 2, round(n(GATE["h"])) * 2), (0.5, 0.62)).convert("RGBA")
    logo = game.logo
    k = pic.width * 0.86 / logo.width
    logo = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
    pic.alpha_composite(logo, ((pic.width - logo.width) // 2, round(pic.height * 0.08)))
    return pic


def live_screen(game, page, behind=None, arrows=True, bar=True):
    """The LiveArea screen: the page over the dimmed wallpaper (or behind), the arrows to the pages each side, its top
    right corner turned over, the info bar (unless bar is false)."""
    under = behind.copy() if behind is not None else ImageEnhance.Brightness(wallpaper()).enhance(0.62).convert("RGBA")
    if arrows:
        d = ImageDraw.Draw(under)
        d.polygon([(n(32), n(280)), (n(16), n(295)), (n(32), n(310))], fill=(255, 255, 255, 220))
    cx, cy = page_corner()
    img = peel(under, page, (cx, cy), (cx - n(CURL), cy + n(CURL)))
    if bar:
        info_bar(img, ("game",), game)
    return img


_GRID = {}


def peel(under, page, corner, touch_at, back=(226, 229, 235)):
    """page (RGBA) turned over from corner towards touch_at, over under (RGBA): the part of the page beyond the fold
    (the line halfway between them, square to the way the corner is pulled) folded back over the rest, its back
    showing, darker into the fold, casting a soft shadow; under shows where the page lifted away."""
    w, h = under.size
    cx, cy = corner
    tx, ty = touch_at
    length = math.hypot(tx - cx, ty - cy)
    base = under.convert("RGBA")
    if length < 1:
        base.alpha_composite(page)
        return base
    if (w, h) not in _GRID:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _GRID[(w, h)] = (xx, yy)
    xx, yy = _GRID[(w, h)]
    ux, uy = (tx - cx) / length, (ty - cy) / length
    mx, my = (cx + tx) / 2, (cy + ty) / 2
    s = (xx - mx) * ux + (yy - my) * uy                                     # > 0: the side the corner is pulled to
    pa = np.asarray(page.getchannel("A")).astype(np.float32) / 255
    flat = pa * np.clip(s + 0.5, 0, 1)
    rx = np.clip(np.rint(xx - 2 * s * ux), 0, w - 1).astype(np.int32)
    ry = np.clip(np.rint(yy - 2 * s * uy), 0, h - 1).astype(np.int32)
    inside = (xx - 2 * s * ux >= 0) & (xx - 2 * s * ux < w) & (yy - 2 * s * uy >= 0) & (yy - 2 * s * uy < h)
    flap = np.where((s > 0) & inside, pa[ry, rx], 0.0)
    flap = np.minimum(flap, np.clip(s, 0, 1))
    out = np.asarray(base).astype(np.float32)[..., :3]
    pg = np.asarray(page).astype(np.float32)[..., :3]
    out = out * (1 - flat[..., None]) + pg * flat[..., None]
    shadow = ndimage.gaussian_filter(np.roll(np.roll(flap, round(n(5)), axis=0), -round(n(3)), axis=1), n(6))
    out *= 1 - 0.45 * np.clip(shadow, 0, 1)[..., None] * (1 - flap[..., None])
    depth = np.clip(s / max(1.0, length * 0.35), 0, 1)
    tone = (0.62 + 0.38 * depth ** 0.6)[..., None] * np.array(back, np.float32)
    shine = np.clip(1 - np.abs(s - length * 0.12) / max(1.0, length * 0.08), 0, 1)[..., None] * 30
    out = out * (1 - flap[..., None]) + np.clip(tone + shine, 0, 255) * flap[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")


# The game: Arcwave's name, Voltcrown's title, and the fight.

def splash(t):
    """Arcwave's name, t from 0 to 1: it fades in and out on black."""
    img = Image.new("RGB", (W2, H2), (0, 0, 0))
    a = min(1.0, t / 0.25, (1 - t) / 0.25)
    if a <= 0:
        return img
    layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = W2 / 2, H2 / 2
    d.arc([cx - n(60), cy - n(118), cx + n(60), cy + 2], 200, 340, fill=(80, 200, 255, 255), width=round(n(9)))
    d.line([(cx - n(46) + k * n(4), cy - n(48) + n(8) * math.sin(k / 3.0)) for k in range(24)], fill=(80, 200, 255, 255),
           width=round(n(6)))
    d.text((cx, cy + n(34)), "ARCWAVE", font=ui(46, "segoeuib.ttf"), fill=(255, 255, 255, 255), anchor="mm")
    layer.putalpha(layer.getchannel("A").point(lambda v: round(v * a)))
    out = img.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def title(game, t, prompt=True, flash=0.0, fade=1.0):
    """Voltcrown's title at t seconds: its key art drifting closer, its logo, PRESS START BUTTON blinking (prompt), (c)
    its publisher; flash (0 to 1) to white, fade (0 to 1) from black."""
    zoom = 1.0 + 0.02 * t
    art = fit(painting("vita_keyart"), (round(W2 * zoom), round(H2 * zoom)), (0.5, 0.55))
    art = art.crop(((art.width - W2) // 2, (art.height - H2) // 2, (art.width - W2) // 2 + W2, (art.height - H2) // 2 + H2))
    img = ImageEnhance.Brightness(art).enhance(0.8).convert("RGBA")
    logo = game.logo
    k = W2 * 0.7 / logo.width
    logo = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
    img.alpha_composite(logo, ((W2 - logo.width) // 2, round(n(64))))
    d = ImageDraw.Draw(img)
    if prompt:
        d.text((W2 / 2, n(430)), "PRESS START BUTTON", font=font("FRAHVIT.TTF", n(30)), fill=(255, 255, 255, 255),
               anchor="mm", stroke_width=round(n(3)), stroke_fill=(120, 10, 40, 255))
    d.text((W2 / 2, n(512)), f"© {game.year} {game.publisher.upper()}", font=ui(16), fill=(225, 228, 238, 255),
           anchor="mm", stroke_width=round(n(1.5)), stroke_fill=(0, 0, 0, 255))
    out = img.convert("RGB")
    if flash:
        out = Image.blend(out, Image.new("RGB", out.size, WHITE), flash)
    if fade < 1:
        out = Image.blend(Image.new("RGB", out.size, (0, 0, 0)), out, max(0.0, fade))
    return out


FW, FH = 1200, 680      # the fight's drawing size: the library's HD HUD wants at least 600 lines


def poses(sheet):
    """A sheet's four poses (Codex's 2 x 2 grid on green), each cut out of its green: [{img, foot, hip}], in reading
    order. A pose is the sheet's largest regions, each with the small ones near it (a blade, a spark); its foot is its
    lowest row, its hip the middle of its figure across the rows from 42% to 56% of its height."""
    a = np.asarray(sheet.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    alpha = np.clip(1 - (g - np.maximum(r, b) - 40) / 90, 0, 1)
    a[..., 1] = np.where(alpha < 0.999, np.minimum(g, np.maximum(r, b) * 1.02 + 4), g)     # the green's spill
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
    labels, count = ndimage.label(alpha > 0.1, structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones_like(alpha), labels, range(1, count + 1))
    big = [k + 1 for k in np.argsort(sizes)[::-1][:4]]
    centres = ndimage.center_of_mass(np.ones_like(alpha), labels, big)
    order = sorted(range(4), key=lambda k: (int(centres[k][0] // (a.shape[0] / 2)), centres[k][1]))
    big = [big[k] for k in order]
    centres = [centres[k] for k in order]
    owner = np.zeros(count + 1, np.int32)
    for k, lab in enumerate(big):
        owner[lab] = k + 1
    small = ndimage.center_of_mass(np.ones_like(alpha), labels, range(1, count + 1))
    for lab in range(1, count + 1):
        if owner[lab] == 0 and sizes[lab - 1] >= 12:
            cy, cx = small[lab - 1]
            owner[lab] = 1 + min(range(4), key=lambda k: math.hypot(cx - centres[k][1], cy - centres[k][0]))
    out = []
    for k in range(4):
        keep = owner[labels] == k + 1
        img = rgba.copy()
        img[..., 3] = np.where(keep, img[..., 3], 0)
        ys, xs = np.nonzero(keep)
        crop = Image.fromarray(img, "RGBA").crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        m = np.asarray(crop.getchannel("A")) > 60
        hh = m.shape[0]
        band = m[int(hh * 0.42):int(hh * 0.56)]
        cols = np.nonzero(band.any(axis=0))[0]
        out.append(dict(img=crop, foot=hh, hip=float(cols.mean()) if len(cols) else crop.width / 2))
    return out


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


class Fight:
    """Voltcrown's fight, drawn at FW x FH: the camera drifting across the empty arena, Juno (left,
    facing right) and Sable (right, facing left) cut out of their poses; Juno walks in on the left stick, a punch, a kick
    and a punch land (hit sparks, the combo counted, Sable's health falling), his volt meter fills and VOLT lights on
    the screen; touched, his finisher's lightning crosses to Sable, K.O."""

    SCALE = 0.72            # the poses' pixels to the fight's
    FLOOR = 0.86            # where their feet stand, down the screen

    def __init__(self, game):
        self.game = game
        self.arena = painting("vita_arena").convert("RGB")
        self.juno = poses(painting("vita_juno"))       # stance, punch, kick, finisher
        self.sable = poses(painting("vita_sable"))     # stance, slash, reel, down

    # Where everyone is at frame f.
    def juno_at(self, f):
        a, b = L.WALK
        walked = smoothstep((f - a) / (b - a)) if f < b else 1.0
        x = FW * (0.27 + 0.13 * walked)
        pose = 0
        for name, f0 in L.PUNCHES.items():
            if f0 <= f < f0 + 6:
                pose = 2 if name == "triangle" else 1
        if L.VOLT[0] <= f < L.KO + 18:
            pose = 3
        lunge = 10 if pose else 0
        return x + lunge, pose

    def sable_at(self, f):
        hits = [f0 + 2 for f0 in L.PUNCHES.values()]
        push = sum(16 * smoothstep((f - h) / 4) for h in hits)
        x = FW * 0.70 + push
        pose = 1 if 176 <= f < 183 else 0
        if any(h <= f < h + 6 for h in hits) or L.VOLT[0] + 4 <= f < L.KO:
            pose = 2
        if f >= L.KO:
            pose = 3
            x += 150 * smoothstep((f - L.KO) / 10)
        return x, pose

    def hits(self, f):
        return sum(1 for f0 in L.PUNCHES.values() if f >= f0 + 2) + (1 if f >= L.VOLT[0] + 4 else 0)

    def camera(self, f):
        """The arena's window: its middle follows the fighters; a shake after each hit."""
        jx, _ = self.juno_at(f)
        sx, _ = self.sable_at(f)
        mid = (jx + sx) / 2 / FW
        shake = 0.0
        for h in [f0 + 2 for f0 in L.PUNCHES.values()] + [L.VOLT[0] + 4, L.KO]:
            if h <= f < h + 8:
                shake += (8 if h >= L.VOLT[0] else 5) * math.exp(-(f - h) / 3.0) * math.sin((f - h) * 2.4)
        return mid, shake

    def frame(self, f):
        aw, ah = self.arena.size
        mid, shake = self.camera(f)
        zoom = 1.18 + (0.06 * smoothstep((f - L.KO) / 20) if f >= L.KO else 0.0)
        w = aw / zoom
        h = w * FH / FW
        cx = aw / 2 + (mid - 0.5) * aw * 0.25 + shake * 2
        cy = ah * 0.54 + shake
        img = self.arena.transform((FW, FH), Image.EXTENT, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2),
                                   Image.BICUBIC).convert("RGBA")
        sx, spose = self.sable_at(f)
        jx, jpose = self.juno_at(f)
        self.place(img, self.sable[spose], sx, f, flash=f in (L.KO, L.KO + 1))
        if L.VOLT[0] <= f < L.KO + 4:
            self.lightning(img, f, jx, sx)
        self.place(img, self.juno[jpose], jx, f)
        for f0 in L.PUNCHES.values():
            if f0 + 2 <= f < f0 + 8:
                self.spark(img, f - f0 - 2, sx - 70, FH * (0.42 if f0 != L.PUNCHES["triangle"] else 0.3))
        out = self.hud(img.convert("RGB"), f)
        return out

    def place(self, img, pose, x, f, flash=False):
        s = self.SCALE * (1 + 0.006 * math.sin(f * 0.35))
        sprite = pose["img"]
        sprite = sprite.resize((round(sprite.width * s), round(sprite.height * s)), Image.LANCZOS)
        if flash:
            white = Image.new("RGBA", sprite.size, (255, 255, 255, 0))
            white.putalpha(sprite.getchannel("A"))
            sprite = Image.blend(sprite, white, 0.6)
        top = FH * self.FLOOR - pose["foot"] * s
        left = x - pose["hip"] * s
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse([x - 120, FH * self.FLOOR - 14, x + 120, FH * self.FLOOR + 12], fill=(0, 0, 0, 110))
        img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
        img.alpha_composite(sprite, (round(left), round(top)))

    def spark(self, img, age, x, y):
        """A hit's spark, age frames old: a white-hot star, an orange glow and rays flying out, all fading."""
        t = age / 6
        fade = 1 - t
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        rng = random.Random(int(x) * 7 + int(y))
        r = 40 + 110 * t
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 150, 40, round(170 * fade)))
        for _ in range(16):
            a = rng.uniform(0, 2 * math.pi)
            r0, r1 = r * 0.25, r * rng.uniform(0.9, 1.6)
            d.line([(x + r0 * math.cos(a), y + r0 * math.sin(a)), (x + r1 * math.cos(a), y + r1 * math.sin(a))],
                   fill=(255, 224, 120, round(255 * fade)), width=7)
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(9)))
        star = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(star)
        k = 70 * (1 - 0.5 * t)
        for a in (0, 45, 90, 135):
            c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
            long_ = k if a % 90 == 0 else k * 0.55
            sd.polygon([(x + long_ * c, y + long_ * s_), (x - 9 * s_, y + 9 * c), (x - long_ * c, y - long_ * s_),
                        (x + 9 * s_, y - 9 * c)], fill=(255, 250, 225, round(255 * fade)))
        sd.ellipse([x - 22 * fade, y - 22 * fade, x + 22 * fade, y + 22 * fade], fill=(255, 255, 255, 255))
        img.alpha_composite(star.filter(ImageFilter.GaussianBlur(1.5)))

    def lightning(self, img, f, jx, sx):
        """Juno's finisher: forks of cyan lightning from his fists to Sable, new every two frames, the screen washed
        cyan as it starts."""
        rng = random.Random(f // 2)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        x0, y0 = jx + 300, FH * 0.37
        x1, y1 = sx - 30, FH * 0.42
        for k in range(4):
            pts = [(x0, y0 + rng.uniform(-14, 14))]
            for j in range(1, 10):
                t = j / 10
                pts.append((x0 + (x1 - x0) * t + rng.uniform(-12, 12), y0 + (y1 - y0) * t + rng.uniform(-36, 36)))
            pts.append((x1 + rng.uniform(-20, 20), y1 + rng.uniform(-50, 50)))
            d.line(pts, fill=(120, 230, 255, 255), width=9 if k == 0 else 5)
        glow = layer.filter(ImageFilter.GaussianBlur(10))
        img.alpha_composite(glow)
        img.alpha_composite(glow)
        core = Image.new("RGBA", img.size, (0, 0, 0, 0))
        core.putalpha(layer.getchannel("A").point(lambda v: 255 if v > 200 else 0).filter(ImageFilter.MinFilter(3)))
        white = Image.new("RGBA", img.size, (235, 252, 255, 255))
        white.putalpha(core.getchannel("A"))
        img.alpha_composite(layer)
        img.alpha_composite(white)
        wash = max(0.0, 1 - (f - L.VOLT[0]) / 6)
        if wash > 0:
            img.alpha_composite(Image.new("RGBA", img.size, (90, 220, 255, round(150 * wash))))

    def hud(self, img, f):
        """The library's HD fighting HUD (screens._versus): health, timer, rounds, the combo, the volt meters; then
        FIGHT!, VOLT on the screen while it can be touched, VOLT FINISH and K.O."""
        hits = self.hits(f)
        sable = [0.92, 0.80, 0.66, 0.54][min(3, hits)]
        if f >= L.VOLT[0] + 4:
            sable = 0.54 * max(0.0, 1 - (f - L.VOLT[0] - 4) / (L.KO - L.VOLT[0] - 4))
        meter = 3 if L.PUNCHES["circle"] + 2 <= f < L.VOLT[0] else (0 if f >= L.VOLT[0] else 2)
        spec = dict(names=["Juno", "Sable"], health=[0.86, sable], timer=str(59 - (f - L.FIGHT[0]) // 30),
                    rounds=[1, 1], combo=f"{hits} HITS" if hits >= 2 else None, meters=[meter, 1])
        a = np.asarray(img).copy()
        self.game.screens._versus(a, spec)
        out = Image.fromarray(a).convert("RGBA")
        d = ImageDraw.Draw(out)
        big = lambda size: font("FRAHVIT.TTF", size)
        if f < L.FIGHT[0] + 14:
            t = (f - L.FIGHT[0]) / 14
            d.text((FW / 2, FH * 0.45), "FIGHT!", font=big(round(150 - 30 * smoothstep(t * 3))), anchor="mm",
                   fill=(255, 214, 60, round(255 * min(1.0, (1 - t) * 3))), stroke_width=6, stroke_fill=(120, 10, 10, 255))
        if L.PUNCHES["circle"] + 4 <= f < L.VOLT[0]:
            self.volt_button(out, f)
        if L.VOLT[0] + 2 <= f < L.KO:
            d.text((FW / 2, FH * 0.26), "VOLT FINISH", font=big(86), anchor="mm", fill=(170, 245, 255, 255),
                   stroke_width=6, stroke_fill=(0, 60, 120, 255))
        if f >= L.KO:
            k = smoothstep((f - L.KO) / 5)
            d.text((FW / 2, FH * 0.45), "K.O.", font=big(round(260 - 60 * k)), anchor="mm",
                   fill=(255, 64, 64, round(255 * k)), stroke_width=8, stroke_fill=(255, 255, 255, round(255 * k)))
        return out.convert("RGB")

    def volt_button(self, img, f):
        """VOLT on the screen, at VOLT_AT: a round button pulsing cyan, to be touched."""
        x, y = (v * FW / L.NATIVE[0] for v in VOLT_AT)
        pulse = 0.5 + 0.5 * math.sin((f - L.PUNCHES["circle"]) * 0.7)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        r = 54 + 6 * pulse
        d.ellipse([x - r - 14, y - r - 14, x + r + 14, y + r + 14], fill=(60, 210, 255, round(90 + 80 * pulse)))
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(img)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(8, 40, 70, 230), outline=(140, 240, 255, 255), width=5)
        d.polygon([(x + 8, y - 40), (x - 18, y + 4), (x - 2, y + 4), (x - 10, y + 40), (x + 20, y - 8), (x + 4, y - 8)],
                  fill=(170, 245, 255, 255))
        d.text((x, y + r + 24), "TOUCH!", font=font("FRAHVIT.TTF", 34), anchor="mm", fill=(255, 255, 255, 255),
               stroke_width=4, stroke_fill=(0, 60, 120, 255))


VOLT_AT = (480, 400)      # VOLT on the fight's screen, in the OLED's pixels


def main(made_up_dir, out):
    os.makedirs(out, exist_ok=True)
    for name, image in (("psvita_print.png", print_atlas()), ("psvita_rear.png", rear_atlas()),
                        ("psvita_screen.png", still())):
        path = os.path.join(out, name)
        image.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
