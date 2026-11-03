"""The Mega-CD's and Sega CD's game cases' texture, for memory-card's megacd_case and segacd_case templates
(tools/console-models/sega_cd_case.py).

Draws one small image, laid out as sega_cd_case_layout.py places it: a column of swatches the cases' faces take their
colours from (the clear plastic over the black tray, its edges and rims, the seam, the tray). Both cases share it. Run
it with the system Python (Pillow):

    python tools/console-models/sega_cd_case_print.py <out folder>

It writes sega_cd_case.png there.
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sega_cd_case_layout as L  # noqa: E402
from retro_pc_print import rgb  # noqa: E402


def main(out):
    os.makedirs(out, exist_ok=True)
    image = Image.new("RGB", L.ATLAS)
    d = ImageDraw.Draw(image)
    for i, name in enumerate(L.SWATCHES):
        y = i * L.SWATCH_SIZE
        d.rectangle([0, y, L.SWATCH_SIZE - 1, y + L.SWATCH_SIZE - 1], fill=rgb(L.COLOURS[name]))
    path = os.path.join(out, "sega_cd_case.png")
    image.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
