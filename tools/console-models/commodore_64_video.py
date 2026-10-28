"""The console theme's Commodore 64 card's video (godot/themes/console/videos/c64.mp4): the 1702's glass through the
card's focused clip, which the launcher plays on the model's `video` material, starting it again each time the clip
loops (A6 Card videos).

It follows the clip (commodore_64.py) frame for frame, by the timing in commodore_64_layout.py: the start-up screen, its
cursor blinking, while the floppy goes in; LOAD"*",8,1, each character as its key goes down; RETURN, SEARCHING FOR *
and LOADING; the loader clearing the screen and the game's loading picture coming in a character cell at a time while
the border flickers; PRESS F1 TO START; f1, and the game: the submarine gliding in over the scrolling sea floor, a
torpedo as each press of the space bar goes down, each hitting a fish; then the switch goes off: the screen goes dark,
and comes back with the switch to the start-up screen, which is also the first frame, so the loop is seamless.

Each frame is the glass as commodore_64_print.py draws it, at SCREEN_PX, encoded by card_video.py. Make the made-up
games' library first (tools/made-up-games/README.md), then run from the repo root (ffmpeg on the PATH):

    python tools/console-models/commodore_64_video.py artifacts/made-up-games godot/themes/console/videos/c64.mp4
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commodore_64_layout as L  # noqa: E402
import commodore_64_print as P  # noqa: E402
from card_video import encode  # noqa: E402

BLINK = 12                                   # the cursor's frames on, then off


def boot(f, since):
    shown = ((f - since) // BLINK) % 2 == 0
    return P.frame(*P.text_screen(P.BOOT, (0, 6) if shown else None))


def typed(f):
    """How many of the command's characters are on the screen: each once its key is down."""
    return sum(1 for k in range(len(L.COMMAND)) if f >= L.TYPED + k * L.PER_KEY + 2)


def screen(f, full):
    """The C64's picture at frame f (FRAME_PX), and how bright the tube shows it; None while there's no picture."""
    if f < L.TYPED:
        return boot(f, 0), 1.0
    if f < L.RETURN:
        n = typed(f)
        return P.frame(*P.text_screen(P.BOOT + [L.COMMAND[:n]], (n, 6))), 1.0
    lines = P.BOOT + [L.COMMAND]
    if f < L.SEARCHING:
        return P.frame(*P.text_screen(lines)), 1.0
    if f < L.LOADING:
        return P.frame(*P.text_screen(lines + ["", "SEARCHING FOR *"])), 1.0
    if f < L.LOADER:
        return P.frame(*P.text_screen(lines + ["", "SEARCHING FOR *", "LOADING"])), 1.0
    start, end = L.PICTURE
    if f < end:
        cells = round(1000 * max(0, f - start) / (end - start))
        return P.frame(P.loading(full, cells), P.stripes(f)), 1.0
    if f < L.F1 + 2:
        return P.frame(P.title(full, f - end), P.BLACK), 1.0
    if f < L.GAME:
        return P.frame(P.paper(P.BLACK), P.BLACK), 1.0
    if f < L.POWER_OFF:
        return P.frame(P.game(f - L.GAME), P.BLACK), 1.0
    if f < L.POWER_OFF + 2:                  # the picture going as the computer goes off
        return P.frame(P.game(L.POWER_OFF - L.GAME), P.BLACK), 0.45 if f == L.POWER_OFF else 0.15
    if f < L.POWER_ON:
        return None, 1.0
    if f < L.BANNER:                         # on again: the colours first, then the start-up screen
        return P.frame(P.paper(P.BLUE), P.LIGHT_BLUE), 1.0
    return boot(f, L.BANNER), 1.0


def frames(made_up):
    full = P.picture(made_up)
    last, image = None, None
    for f in range(L.LENGTH):
        picture, brightness = screen(f, full)
        key = (picture.tobytes() if picture is not None else None, brightness)
        if key != last:                      # frames repeat in runs: draw each once
            image = P.glass(picture, brightness)
            last = key
        yield image


def main():
    made_up, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    encode(out, L.SCREEN_PX, L.FPS, frames(made_up), "Commodore 64")


if __name__ == "__main__":
    main()
