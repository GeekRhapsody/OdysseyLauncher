"""Screens from tools/made-up-games's games (made up: no real game's art) for the console theme's later cards'
televisions, monitors and handhelds: a game's title and two frames of play at a machine's own resolution and, where it
has one, in its own palette. Shared by the cards' print scripts; the game is arcade_print.Game (its logo, its
screenshot, a second frame rendered from its painting), the palette devices_print.reduced()'s. Run with the system
Python (Pillow, numpy, scipy).
"""

import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcade_print import Game  # noqa: E402
from devices_print import reduced  # noqa: E402
from vic20_print import chars  # noqa: E402


def made_up(stem, system, made_up_dir):
    """A made-up game: its release's file stem (`Kaleidrop (Europe)`, `dustygul`) on a system of the library."""
    return Game(stem, made_up_dir, system)


def cover(stem, system, made_up_dir):
    """A made-up game's box art from the library (a console game's; an arcade game has none)."""
    return Image.open(os.path.join(made_up_dir, "library", "media", system, "covers", stem + ".jpg")).convert("RGB")


def native(img, size, palette=None):
    """A picture at a machine's resolution, cropped to its shape, each pixel its palette's nearest colour if it has
    one."""
    return reduced(img, size, palette) if palette else ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS)


def title(game, size, palette=None, prompt="PRESS START", ink=(255, 255, 255), dim=0.4, logo_at=0.36):
    """The game's title screen at size: its screenshot blurred and dimmed, its logo over it, the prompt under it in
    8 x 8 character cells; in the palette, if given."""
    w, h = size
    back = ImageOps.fit(game.shot.convert("RGB"), size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(max(1, w / 90)))
    img = ImageEnhance.Brightness(back).enhance(dim).convert("RGBA")
    k = min(w * 0.88 / game.logo.width, h * 0.42 / game.logo.height)
    logo = game.logo.resize((max(1, round(game.logo.width * k)), max(1, round(game.logo.height * k))), Image.LANCZOS)
    img.alpha_composite(logo, ((w - logo.width) // 2, round(h * logo_at - logo.height / 2)))
    img = img.convert("RGB")
    if prompt:
        chars(img, (w / 8 - len(prompt)) / 2, h * 0.74 / 8, prompt, ink)
    return reduced(img, size, palette) if palette else img


def play(game, size, palette=None, pan=0.35):
    """Two frames of play: the game's screenshot, and its playfield panned by pan (arcade_print.Game.frame)."""
    return native(game.shot, size, palette), native(game.frame(pan), size, palette)


def text_screen(size, lines, ink, paper, cursor=True, col=0, row=0):
    """A machine's text screen: lines in 8 x 8 character cells from (col, row), ink on paper, the cursor after them."""
    img = Image.new("RGB", size, paper)
    for k, line in enumerate(lines):
        chars(img, col, row + k, line, ink)
    if cursor:
        y = (row + len(lines)) * 8
        ImageDraw.Draw(img).rectangle([col * 8, y, col * 8 + 7, y + 7], fill=ink)
    return img
