"""The PAL Dreamcast jewel case's texture, for memory-card's dreamcast_jewel_case template
(tools/console-models/dreamcast_jewel_case.py).

Draws one image, laid out as dreamcast_jewel_case_layout.py places it: the tray's hinge band as the front shows it (its
pocket's floor: the tray's blue, the panel moulded into it with its light rim, and Dreamcast in the panel, read from the
bottom up, set in Segoe UI, which is close to the case's lettering), padded with the band's blue; and the swatches the
case's other faces take their colours from. Run it with the system Python (Pillow):

    python tools/console-models/dreamcast_jewel_case_print.py <out folder>

It writes dreamcast_jewel_case.png there.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dreamcast_jewel_case_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS  # noqa: E402

SS = 4                  # drawn this many times larger, then resampled: the lettering is small
TRADEMARK = 0.5         # the trademark sign's size, as a fraction of the lettering's; it stands at the capitals' top


def lettering(size, ink):
    """Dreamcast and a small trademark sign after it, on one transparent line, at a font size in pixels."""
    font = ImageFont.truetype(FONTS + L.FONT, size)
    small = ImageFont.truetype(FONTS + L.FONT, round(size * TRADEMARK))
    word = font.getbbox("Dreamcast")
    mark = small.getbbox("™")
    cap_top = font.getbbox("D")[1]
    gap = round(size * 0.04)
    line = Image.new("RGBA", (word[2] - word[0] + gap + mark[2] - mark[0], word[3] - cap_top), (0, 0, 0, 0))
    d = ImageDraw.Draw(line)
    d.text((-word[0], -cap_top), "Dreamcast", font=font, fill=ink)
    d.text((word[2] - word[0] + gap - mark[0], -mark[1]), "™", font=small, fill=ink)
    return line


def band():
    """The band's pocket floor, as the front shows it, at its size in the atlas."""
    w_mm, h_mm = L.BAND_RIGHT - L.BAND_LEFT, L.BAND_TOP - L.BAND_BOTTOM
    w, h = L.BAND_PIXELS * SS, L.ATLAS[1] * SS
    sx, sy = w / w_mm, h / h_mm
    blue = rgb(L.COLOURS["band"])
    image = Image.new("RGBA", (w, h), blue + (255,))
    d = ImageDraw.Draw(image)

    # The panel: a little darker than the band, with a light rim where its moulded edge catches the light.
    x0, x1 = (L.PANEL_X - L.PANEL_W / 2) * sx, (L.PANEL_X + L.PANEL_W / 2) * sx
    y0, y1 = (L.PANEL_Y - L.PANEL_L / 2) * sy, (L.PANEL_Y + L.PANEL_L / 2) * sy
    d.rounded_rectangle([x0, y0, x1, y1], radius=L.PANEL_R * sx, fill=rgb(L.COLOURS["panel"]) + (255,),
                        outline=shade(blue, 0.18) + (255,), width=round(0.3 * sx))

    # The lettering, set along the band at its length and turned to read from the bottom up, in the middle of the panel.
    ink = rgb(L.COLOURS["ink"]) + (255,)
    trial = 100
    size = round(trial * L.LETTERING * sy / lettering(trial, ink).width)
    line = lettering(size, ink).rotate(90, expand=True)
    image.alpha_composite(line, (round((x0 + x1 - line.width) / 2), round((y0 + y1 - line.height) / 2)))
    return image.convert("RGB").resize((L.BAND_PIXELS, L.ATLAS[1]), Image.LANCZOS)


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", L.ATLAS, rgb(L.COLOURS["band"]))
    image.paste(band(), (0, 0))
    d = ImageDraw.Draw(image)
    for i, name in enumerate(L.SWATCHES):
        y = i * L.SWATCH_SIZE
        d.rectangle([L.SWATCH_X, y, L.SWATCH_X + L.SWATCH_SIZE - 1, y + L.SWATCH_SIZE - 1], fill=rgb(L.COLOURS[name]))
    path = os.path.join(out, "dreamcast_jewel_case.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
