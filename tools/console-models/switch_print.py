"""The Nintendo Switch's printing, for the console theme's model (tools/console-models/switch.py).

Writes switch_print.png into a folder: the front and the back as the model's planar UVs map them (switch_layout.py has
the layout and the positions).
- The front: the tablet's dark grey rim round the black glass, the screen showing the start-up logo over a dark,
  blurred, colourful background, and the Joy-Con faces (neon blue on the left, neon red on the right) with the wells
  round their sticks and buttons, the direction buttons' arrows, X, Y, A and B, the capture button's dimple and the
  HOME button's ring and house.
- The back, drawn as seen from the front and then mirrored: the vent along the top, the kickstand's outline, the
  screws, and each Joy-Con's release button; then the logo in grey, in the middle, reading the right way round.

Run it with the system Python (Pillow):

    python tools/console-models/switch_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_layout as L  # noqa: E402

SCALE = 20  # pixels per millimetre while drawing; each half is resampled to half of L.PRINT_SIZE
FONTS = "C:/Windows/Fonts/"

BODY = "#2D2E32"
GLASS = "#0A0A0C"
BLUE = "#00B9E4"
RED = "#FF4B55"
BUTTON = "#232327"
WELL = "#141416"
LEGEND = "#D2D3D6"
ARROW = "#66676C"
RING = "#9A9BA0"
BACK_PRINT = "#808186"
SEAM = "#1C1D20"


def px(x, z):
    """A point in millimetres as canvas pixels."""
    return ((x - L.PRINT_X[0]) * SCALE, (L.PRINT_Z[1] - z) * SCALE)


def circle(draw, x, z, r, fill):
    cx, cy = px(x, z)
    draw.ellipse([cx - r * SCALE, cy - r * SCALE, cx + r * SCALE, cy + r * SCALE], fill=fill)


def rect(draw, x0, z0, x1, z1, fill, r=0.0, outline=None, width=0.0):
    (a, b), (c, d) = px(x0, z1), px(x1, z0)
    draw.rounded_rectangle([a, b, c, d], radius=r * SCALE, fill=fill, outline=outline, width=int(width * SCALE))


def font(name, cap_mm, scale=SCALE):
    """A font sized so its capitals are cap_mm high."""
    probe = ImageFont.truetype(FONTS + name, 200)
    left, top, right, bottom = probe.getbbox("H")
    return ImageFont.truetype(FONTS + name, int(200 * cap_mm * scale / (bottom - top)))


def text(canvas, s, name, cap_mm, x, z, fill, spacing=0.0):
    """Text whose capitals are cap_mm high, centred on (x, z), with spacing mm between letters."""
    face = font(name, cap_mm)
    widths = [face.getbbox(ch)[2] - face.getbbox(ch)[0] for ch in s]
    total = sum(widths) + spacing * SCALE * (len(s) - 1)
    top = face.getbbox("H")[1]
    height = face.getbbox("H")[3] - top
    cx, cy = px(x, z)
    left = cx - total / 2
    draw = ImageDraw.Draw(canvas)
    for ch, w in zip(s, widths):
        draw.text((left - face.getbbox(ch)[0], cy - height / 2 - top), ch, font=face, fill=fill)
        left += w + spacing * SCALE


def width_of(s, name, cap_mm, spacing=0.0):
    face = font(name, cap_mm)
    return sum(face.getbbox(ch)[2] - face.getbbox(ch)[0] for ch in s) / SCALE + spacing * (len(s) - 1)


def logo_mask(size_mm, scale):
    """
    The Switch's logo, size_mm high, as an L mask at scale pixels per millimetre: two Joy-Con-like halves, the left an
    outline with a dot near its top, the right solid with a hole near its middle.
    """
    w, gap = 0.44 * size_mm, 0.06 * size_mm
    width = 2 * w + gap
    mask = Image.new("L", (int(width * scale) + 2, int(size_mm * scale) + 2), 0)
    draw = ImageDraw.Draw(mask)
    s = lambda v: v * scale
    outer, inner, stroke = 0.62 * w, 0.06 * w, 0.2 * w

    def half(x0, rounded_left, fill, inset=0.0):
        box = [s(x0 + inset), s(inset), s(x0 + w - inset), s(size_mm - inset)]
        r = max(outer - inset, 0.1)
        # The outer corners are rounded; the inner ones nearly square: a big rounded rectangle, with its inner side
        # squared off by a rectangle over it.
        draw.rounded_rectangle(box, radius=s(r), fill=fill)
        if rounded_left:
            draw.rounded_rectangle([s(x0 + w / 2), box[1], box[2], box[3]], radius=s(inner), fill=fill)
        else:
            draw.rounded_rectangle([box[0], box[1], s(x0 + w / 2), box[3]], radius=s(inner), fill=fill)

    half(0, True, 255)
    half(0, True, 0, stroke)
    cx, cz, r = w / 2, 0.3 * size_mm, 0.23 * w
    draw.ellipse([s(cx - r), s(cz - r), s(cx + r), s(cz + r)], fill=255)
    half(w + gap, False, 255)
    cx, cz, r = w + gap + w / 2, 0.57 * size_mm, 0.25 * w
    draw.ellipse([s(cx - r), s(cz - r), s(cx + r), s(cz + r)], fill=0)
    return mask


def paste_logo(canvas, size_mm, x, z, colour):
    mask = logo_mask(size_mm, SCALE)
    cx, cy = px(x, z)
    canvas.paste(Image.new("RGBA", mask.size, colour), (int(cx - mask.width / 2), int(cy - mask.height / 2)), mask)


def wordmark(canvas, x, z_logo, size_mm, colour):
    """The logo, then NINTENDO (spaced to SWITCH's width) and SWITCH under it."""
    paste_logo(canvas, size_mm, x, z_logo, colour)
    cap_n, cap_s = 0.135 * size_mm, 0.27 * size_mm
    switch_width = width_of("SWITCH", "seguibl.ttf", cap_s, 0.05 * cap_s)
    plain = width_of("NINTENDO", "seguisb.ttf", cap_n)
    spacing = (switch_width - plain) / 7
    z_n = z_logo - size_mm / 2 - 0.36 * size_mm
    text(canvas, "NINTENDO", "seguisb.ttf", cap_n, x, z_n, colour, spacing)
    text(canvas, "SWITCH", "seguibl.ttf", cap_s, x, z_n - 0.32 * size_mm, colour, 0.05 * cap_s)


def screen():
    """The start-up screen: the logo over soft blots of colour on a dark ground."""
    half_w, z0, z1 = L.SCREEN
    w_mm, h_mm = 2 * half_w, z1 - z0
    small = 4  # pixels per millimetre for the blurred ground
    ground = Image.new("RGB", (int(w_mm * small), int(h_mm * small)), "#121419")
    draw = ImageDraw.Draw(ground)
    for x, z, rx, rz, colour in ((-46, 50, 26, 30, "#1F7F73"), (-60, 18, 22, 18, "#1E4E7A"), (-20, 70, 22, 12, "#23364F"),
                                 (30, 52, 22, 26, "#5A3790"), (54, 30, 18, 22, "#9C3F79"), (58, 70, 14, 10, "#A2582E"),
                                 (12, 20, 16, 10, "#2B2B55")):
        cx, cy = (x + half_w) * small, (h_mm - z) * small
        draw.ellipse([cx - rx * small, cy - rz * small, cx + rx * small, cy + rz * small], fill=colour)
    ground = ground.filter(ImageFilter.GaussianBlur(14 * small))
    image = ground.resize((int(w_mm * SCALE), int(h_mm * SCALE)), Image.BICUBIC).convert("RGBA")
    return image


def joycon_front(canvas, draw):
    # The wells round the sticks.
    for x, z in (L.LEFT_STICK, L.RIGHT_STICK):
        circle(draw, x, z, L.STICK_WELL, WELL)

    # The direction buttons, with their arrows (up, left, right, down), and X, Y, A, B.
    shade = {"left": "#0096BA", "right": "#D93C45"}
    for (x, z), (dx, dz) in zip(L.four(L.DPAD), ((0, 1), (-1, 0), (1, 0), (0, -1))):
        circle(draw, x, z, L.BUTTON_R + 0.6, shade["left"])
        circle(draw, x, z, L.BUTTON_R + 0.15, BUTTON)
        tip, base, half = 1.15, -0.55, 0.95
        points = [(x + dx * tip, z + dz * tip), (x + dx * base - dz * half, z + dz * base + dx * half),
                  (x + dx * base + dz * half, z + dz * base - dx * half)]
        draw.polygon([px(*p) for p in points], fill=ARROW)
    for (x, z), letter in zip(L.four(L.ABXY), "XYAB"):
        circle(draw, x, z, L.BUTTON_R + 0.6, shade["right"])
        circle(draw, x, z, L.BUTTON_R + 0.15, BUTTON)
        text(canvas, letter, "arialbd.ttf", 2.5, x, z, LEGEND)

    # Capture: a rounded square with a round dimple.
    x, z = L.CAPTURE
    rect(draw, x - 3.6, z - 3.6, x + 3.6, z + 3.6, shade["left"], 1.6)
    rect(draw, x - 3.15, z - 3.15, x + 3.15, z + 3.15, BUTTON, 1.2)
    circle(draw, x, z, 1.9, "#303035")
    circle(draw, x, z, 1.5, "#1D1D21")

    # HOME: a silver ring round a dark button with a house on it.
    x, z = L.HOME
    circle(draw, x, z, L.HOME_RING + 0.3, shade["right"])
    circle(draw, x, z, L.HOME_RING, RING)
    circle(draw, x, z, L.HOME_R + 0.15, "#2B2B30")
    house = [(x - 1.25, z - 1.1), (x + 1.25, z - 1.1), (x + 1.25, z + 0.25), (x + 1.75, z + 0.25), (x, z + 1.6),
             (x - 1.75, z + 0.25), (x - 1.25, z + 0.25)]
    draw.polygon([px(*p) for p in house], fill=LEGEND)
    rect(draw, x - 0.35, z - 1.1, x + 0.35, z - 0.2, "#2B2B30")

    # Under the minus and plus (moulded: switch.py builds them).
    x, z = L.MINUS
    rect(draw, x - 3.0, z - 1.1, x + 3.0, z + 1.1, shade["left"], 0.8)
    x, z = L.PLUS
    rect(draw, x - 3.1, z - 1.2, x + 3.1, z + 1.2, shade["right"], 0.8)
    rect(draw, x - 1.2, z - 3.1, x + 1.2, z + 3.1, shade["right"], 0.8)


def base(width, height):
    canvas = Image.new("RGBA", (width, height), BODY)
    draw = ImageDraw.Draw(canvas)
    rect(draw, L.PRINT_X[0] - 1, L.PRINT_Z[0] - 1, -L.TABLET, L.PRINT_Z[1] + 1, BLUE)
    rect(draw, L.TABLET, L.PRINT_Z[0] - 1, L.PRINT_X[1] + 1, L.PRINT_Z[1] + 1, RED)
    return canvas, draw


def front(size):
    canvas, draw = base(*size)
    half_w, z0, z1, r = L.GLASS
    rect(draw, -half_w - 0.3, z0 - 0.3, half_w + 0.3, z1 + 0.3, GLASS, r + 0.3)
    sx, sy = px(-L.SCREEN[0], L.SCREEN[2])
    canvas.alpha_composite(screen(), (int(sx), int(sy)))
    wordmark(canvas, 0.0, 59.0, 19.0, "#F4F4F4")
    joycon_front(canvas, draw)
    return canvas


def back(size):
    canvas, draw = base(*size)

    # The vent along the top, the kickstand's outline (behind the right-hand end), the screws.
    x = -32.0
    while x < 78.0:
        rect(draw, x, 95.6, x + 1.1, 98.4, "#18191B", 0.5)
        x += 2.3
    rect(draw, 62.0, 7.0, 84.0, 56.0, None, 1.6, SEAM, 0.35)
    for sx in (-83.5, 83.5):
        for sz in (4.5, 97.5):
            circle(draw, sx, sz, 0.9, "#1A1A1C")
            circle(draw, sx, sz, 0.45, "#3C3D41")

    # Each Joy-Con's release button, near its top, by the rail; its screws.
    for side in (-1, 1):
        circle(draw, side * 90.6, 93.0, 1.8, BUTTON)
        for sz in (9.0, 93.0):
            circle(draw, side * 113.5, sz, 0.7, "#0080A0" if side < 0 else "#C23540")
    canvas = ImageOps.mirror(canvas)  # seen from behind
    wordmark(canvas, 0.0, 58.0, 17.0, BACK_PRINT)  # on the middle line, so drawn after the mirror, reading right
    return canvas


def main(folder):
    os.makedirs(folder, exist_ok=True)
    size = (int((L.PRINT_X[1] - L.PRINT_X[0]) * SCALE), int((L.PRINT_Z[1] - L.PRINT_Z[0]) * SCALE))
    half = (L.PRINT_SIZE[0], L.PRINT_SIZE[1] // 2)
    out = Image.new("RGB", L.PRINT_SIZE)
    out.paste(front(size).convert("RGB").resize(half, Image.LANCZOS), (0, 0))
    out.paste(back(size).convert("RGB").resize(half, Image.LANCZOS), (0, half[1]))
    out.save(os.path.join(folder, "switch_print.png"), optimize=True)


if __name__ == "__main__":
    main(sys.argv[1])
