"""The 64DD's printing and the disk's label (n64dd_print.png), for the console theme's 64DD card (n64dd.py), whose
console and controller are n64.py's (their printing is n64_print.py's).

One image, laid out as n64dd_layout.REGIONS says: the drive's front (the panel sunk into it, the disk's slot, EJECT, the
Nintendo emblem), the disk's top (its label: a made-up game, Odyssey, and 64DD), and swatches. Run it with the system
Python (Pillow):

    python tools/console-models/n64dd_print.py <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n64dd_layout as L  # noqa: E402
from psp_print import ship, space  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

CASE = rgb(L.COLOURS["case"])
WIDTH = 2 * L.BASE["x"]


def front():
    """The drive's front: x across (-126 at the left), z down from its top (46)."""
    reg = Region(L.REGIONS["front"], WIDTH, L.HEIGHT, CASE)

    def at(x, z):
        return x + WIDTH / 2, L.HEIGHT - z

    (x0, x1), (z0, z1) = L.RECESS["x"], L.RECESS["z"]
    reg.rect_(*at(x0, z1), *at(x1, z0), (44, 44, 48), r=3.0)
    (s0, s1), (t0, t1) = L.SLOT["x"], L.SLOT["z"]
    reg.rect_(*at(s0, t1), *at(s1, t0), (8, 8, 10), r=1.5)
    reg.rect_(*at(s0 - 4.0, t1 + 3.0), *at(s1 + 4.0, t1 + 1.5), (58, 58, 62))
    reg.rect_(*at(-40.0, z0 + 6.0), *at(-12.0, z0 + 2.0), None, r=2.0, outline=(78, 78, 84), width=0.4)
    reg.text("Nintendo", "arialbd.ttf", 2.8, *at(-26.0, z0 + 4.0), (78, 78, 84))
    ex, ez = L.EJECT["at"]
    reg.text("EJECT", "arialbd.ttf", 2.4, *at(ex, ez + L.EJECT["r"] + 3.0), (120, 120, 126))
    return reg


def disk():
    """The disk's top: its label on the grey shell, from above (its front, the end that goes in first, at the top)."""
    w, d, _ = L.DISK["size"]
    reg = Region(L.REGIONS["disk"], w, d, rgb(L.COLOURS["disk"]))
    lw, lh = L.DISK["label"]
    x0, y0 = (w - lw) / 2, d - lh - 14.0
    art = space((560, 420)).convert("RGB")
    ship(ImageDraw.Draw(art), 170, 250, 3.4, "#FFFFFF", "#FFB23C")
    a, b, c, e = reg.box(x0, y0, x0 + lw, y0 + lh)
    reg.img.paste(art.resize((round(c - a), round(e - b)), Image.LANCZOS), (round(a), round(b)))
    reg.rect_(x0, y0, x0 + lw, y0 + 9.0, (236, 236, 234))
    reg.text("ODYSSEY", "ariblk.ttf", 6.0, w / 2, y0 + 4.6, (40, 40, 44))
    reg.rect_(w - 24.0, d - 10.0, w - 6.0, d - 4.0, (30, 30, 34), r=1.0)
    reg.text("64DD", "arialbd.ttf", 3.6, w - 15.0, d - 7.0, (236, 236, 234))
    reg.circle(w / 2, 22.0, 9.0, (118, 119, 122))                  # the shutter's mark
    return reg


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), CASE)
    for reg in (front(), disk()):
        reg.paste(image)
    d = ImageDraw.Draw(image)
    colours = dict(case=CASE, dark=(10, 10, 12), disk=rgb(L.COLOURS["disk"]), button=(176, 176, 180))
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colours[name])
    path = os.path.join(out, "n64dd_print.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
