"""The console theme's DOS, Windows 3.x and Windows 9x cards' videos (godot/themes/console/videos/<set>.mp4): each
monitor's glass through its card's focused clip, which the launcher plays on the model's `video` material, starting it
again each time the clip loops (A6 Card videos).

Each follows its clip (retro_pc.py) frame for frame, by its set's timing (dos_layout.py, windows3x_layout.py,
windows9x_layout.py); its screens are its own module's (dos_screens.py, windows3x_screens.py, windows9x_screens.py),
which say what each shows. Each frame is the whole glass, GLASS_PX, encoded by card_video.py; the first is the still,
retro_pc_print.py's <set>_screen.png, and the clip comes back to it, so the loop is seamless. Make the made-up games'
library and the paintings first (tools/made-up-games/README.md; paintings.py), then run it from the repo root with the
system Python (Pillow, numpy; ffmpeg on the PATH):

    python tools/console-models/retro_pc_video.py <set> artifacts/made-up-games godot/themes/console/videos/<set>.mp4
"""

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retro_pc_layout as K  # noqa: E402
from card_video import encode  # noqa: E402


def frames(name, made_up):
    spec = importlib.import_module(name + "_layout")
    screens = importlib.import_module(name + "_screens").Screens(made_up)
    for f in range(spec.LENGTH):
        yield screens.frame(f)


def main():
    name, made_up, out = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
    spec = importlib.import_module(name + "_layout")
    encode(out, K.GLASS_PX, spec.FPS, frames(name, made_up), spec.NAME)


if __name__ == "__main__":
    main()
