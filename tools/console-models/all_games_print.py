"""The All games card's art (all_games_art.jpg, all_games_backs.jpg), for the console theme's model (all_games.py).

Packs the pile's boxes' covers, spines and backs, from tools/made-up-games's library (made-up games: no real game's
art), into two images as all_games_layout.REGIONS says, each image at all_games_layout.SCALE of its size; the rest dark,
the boxes' case colour. Make the library first (tools/made-up-games/README.md), then run it with the system Python
(Pillow):

    python tools/console-models/all_games_print.py artifacts/made-up-games/library <out folder>
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import all_games_layout as L  # noqa: E402

FOLDERS = dict(cover="covers", back="backcovers", spine="spines")    # the media folder's kinds (ES-DE's names)
BACKGROUND = (24, 24, 27)


def main(library, out):
    os.makedirs(out, exist_ok=True)
    atlases = {name: Image.new("RGB", L.ATLAS_SIZE, BACKGROUND) for name in ("art", "backs")}
    for box in L.BOXES:
        for kind, (atlas, (x, y, w, h)) in L.REGIONS[box["name"]].items():
            path = os.path.join(library, "media", box["system"], FOLDERS[kind], box["game"] + ".jpg")
            image = Image.open(path).convert("RGB")
            assert image.size == L.ART[box["system"]][kind], f"{path} is {image.size}, not {L.ART[box['system']][kind]}"
            atlases[atlas].paste(image.resize((w, h), Image.LANCZOS), (x, y))
    for name, image in atlases.items():
        path = os.path.join(out, f"all_games_{name}.jpg")
        image.save(path, quality=92, optimize=True)
        print(path)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
