"""The arcade cards' printing, side art and screens, for the console theme's arcade cards (arcade.py).

Draws a card's three images, laid out as arcade_layout.py says, into a folder: `<card>_print.png` (the marquee, lit,
its board's name over its glow; the speaker panel's grilles, or the speaker boxes' fronts, or a roof's sign; the
control panel's overlay; the lower front and its doors; the bezel's art round the screen; a POP sign of the game's key
art; the control panel's front strip; and the swatches the small parts take their colour from), `<card>_side.png` (the
side art, from the card's shapes: fills, bands, swooshes, flames, lettering, the game's key art) and
`<card>_media.png` (the screens: the board starting up, the game's title with PRESS START and CREDIT 1, and two frames
of play; the side art and the screens JPEG, as pictures, the print PNG, for its lettering and swatches). The game is
one of tools/made-up-games's arcade games (made up: no real game's art): its logo, key art and
screenshot from the made-up library and paintings, and a second frame of play rendered from its painting with its
playfield panned (its HUD the same) by the made-up games' own screen code; a fixed-screen game's second frame flashes
its 1UP instead. Make the library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/arcade_print.py <card> artifacts/made-up-games <out folder>
"""

import math
import os
import random
import sys
import tomllib
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
PAINTINGS = HERE.parents[1] / "artifacts" / "console-paintings"   # paintings.py's
sys.path.insert(0, str(HERE))
import arcade_layout as L  # noqa: E402
from retro_pc_print import mix, rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

YELLOW = "#F6D23A"


def font(name, size):
    return ImageFont.truetype(FONTS + name, max(1, round(size)))


# ---- The made-up game ------------------------------------------------------------------------------------------------

def painting(name):
    return Image.open(PAINTINGS / f"{name}.png")


class Game:
    """A made-up game: its release (from games.toml), logo, key art, screenshot, and its painting for a second frame.
    An arcade game, or a console's for a console arcade system."""

    def __init__(self, stem, made_up, system="arcade"):
        sys.path.insert(0, str(HERE.parent / "made-up-games"))
        import make_games
        import screens
        self.screens = screens
        with open(HERE.parent / "made-up-games" / "games.toml", "rb") as f:
            releases = make_games.releases(tomllib.load(f)["games"])
        self.release = next(r for r in releases if r["system"] == system and Path(r["file"]).stem == stem)
        self.system = system
        media = Path(made_up) / "library" / "media" / system
        self.logo = Image.open(media / "logos" / f"{stem}.png").convert("RGBA")
        self.shot = Image.open(media / "screenshots" / f"{stem}.png").convert("RGB")
        paintings = Path(made_up) / "paintings" / self.release["concept"]
        self.painting = paintings / f"screen-{self.release['look']}.png"
        keyart = paintings / "keyart.png"           # an arcade game has no box, so its painting stands in
        self.keyart = Image.open(keyart if keyart.exists() else self.painting).convert("RGB")
        self.title = self.release["title"]
        self.year = self.release["released"][:4]
        self.publisher = self.release["publisher"]
        self.look = self.release["look"]

    def frame(self, pan):
        """A frame of play: the playfield panned by pan (a fraction of the painting's slack), the HUD the same; a
        fixed-screen 8-bit game's 1UP flashes instead."""
        if self.look.startswith("arcade8"):
            img = self.shot.copy()
            w, h = img.size
            ImageDraw.Draw(img).rectangle([0, 0, w * 0.2, h * 0.035], fill=(0, 0, 0))   # 1UP, off
            return img
        fx, fy = self.release.get("crop", {}).get("screen", (0.5, 0.5))
        vertical = self.look.endswith("_v") or self.look == "arcade_hd"
        crop = [fx, min(1.0, max(0.0, fy + pan))] if vertical else [min(1.0, max(0.0, fx + pan)), fy]
        return self.screens.screenshot(dict(self.release, crop={"screen": crop}), Image.open(self.painting),
                                       self.system, self.look)


class LaserdiscGame:
    """A made-up laserdisc game (Daphne's card): its title lettered over the attract scene, two frames of its
    animation, all paintings (paintings.py)."""

    def __init__(self, spec):
        self.title, self.year, self.publisher = spec["title"], spec["year"], spec["publisher"]
        self.attract = painting(spec["attract"]).convert("RGB")
        self.frames = [painting(name).convert("RGB") for name in spec["frames"]]
        self.keyart = self.attract
        self.shot = self.frames[0]
        self.logo = lettered(self.title, "ALGER.TTF", 120, "#F6C840", "#5A1206")

    def frame(self, pan):
        return self.frames[1]


def lettered(text, name, size, fill, edge):
    """A title lettered in a font, filled and outlined, on a clear ground, cropped to it."""
    f = font(name, size)
    stroke = max(2, round(size * 0.07))
    box = f.getbbox(text, stroke_width=stroke)
    img = Image.new("RGBA", (box[2] - box[0] + 8, box[3] - box[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((4 - box[0], 4 - box[1]), text, font=f, fill=rgb(fill), stroke_width=stroke,
                             stroke_fill=rgb(edge))
    return img


# ---- The screens -----------------------------------------------------------------------------------------------------

def on_screen(img, size):
    """A frame on the monitor: its pixels enlarged as they are (a painting's scaled down), softened a touch as a CRT
    shows them."""
    if img.width > size[0]:
        return ImageOps.fit(img, size, Image.LANCZOS)
    return img.resize(size, Image.NEAREST).filter(ImageFilter.GaussianBlur(0.7))


def title_screen(game, size):
    w, h = size
    if isinstance(game, LaserdiscGame):                    # the attract scene, dimmed, behind the title
        img = ImageEnhance.Brightness(on_screen(game.attract, size)).enhance(0.55)
    else:
        img = ImageEnhance.Brightness(on_screen(game.shot, size).filter(ImageFilter.GaussianBlur(6))).enhance(0.35)
    img = img.convert("RGBA")
    k = min(w * 0.86 / game.logo.width, h * 0.36 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    img.alpha_composite(logo, ((w - logo.width) // 2, round(h * 0.3 - logo.height / 2)))
    d = ImageDraw.Draw(img)
    u = min(w, h) / 480
    d.text((w / 2, h * 0.64), "PRESS START", font=font("arialbd.ttf", 30 * u), fill=(255, 255, 255), anchor="mm")
    d.text((w / 2, h * 0.84), f"©{game.year} {game.publisher.upper()}", font=font("arialbd.ttf", 18 * u),
           fill=(230, 230, 230), anchor="mm")
    d.text((w - 14 * u, h - 14 * u), "CREDIT 1", font=font("arialbd.ttf", 18 * u), fill=(255, 255, 255), anchor="rb")
    return img.convert("RGB")


def boot_screen(card, game, size):
    """The board at rest, before a coin: its maker's name over the board's as it starts up; a PC's start-up text; a
    laserdisc game's attract scene."""
    w, h = size
    u = min(w, h) / 480
    boot = card.get("boot", {})
    kind = boot.get("kind", "laserdisc" if isinstance(game, LaserdiscGame) else "logo")
    if kind == "laserdisc":
        img = on_screen(game.attract, size).convert("RGBA")
        k = min(w * 0.8 / game.logo.width, h * 0.26 / game.logo.height)
        logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
        img.alpha_composite(logo, ((w - logo.width) // 2, round(h * 0.22 - logo.height / 2)))
        ImageDraw.Draw(img).text((w / 2, h * 0.88), "INSERT COIN", font=font("arialbd.ttf", 26 * u),
                                 fill=(255, 255, 255), anchor="mm", stroke_width=round(2 * u), stroke_fill=(0, 0, 0))
        return img.convert("RGB")
    img = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(img)
    if kind == "bios":                                     # a PC's start-up, in grey on black
        for k, line in enumerate(boot["lines"]):
            d.text((w * 0.06, h * 0.08 + k * h * 0.075), line, font=font("consola.ttf", 20 * u), fill=(200, 200, 200))
        d.rectangle([w * 0.06, h * 0.08 + len(boot["lines"]) * h * 0.075, w * 0.06 + 10 * u,
                     h * 0.08 + len(boot["lines"]) * h * 0.075 + 18 * u], fill=(200, 200, 200))
        return img
    big, small = boot.get("big", card["maker"]), boot.get("small", card["marquee"])
    edge = card.get("boot_edge", card["colours"].get("marquee_edge", "#1E3C9A"))
    size_big = min(64 * u, w * 0.9 / (0.78 * max(1, len(big))))
    d.text((w / 2, h * 0.42), big, font=font("ariblk.ttf", size_big), fill=rgb(card.get("boot_colour", YELLOW)),
           anchor="mm", stroke_width=round(3 * u), stroke_fill=rgb(edge))
    size_small = min(26 * u, w * 0.9 / (0.62 * max(1, len(small))))
    d.text((w / 2, h * 0.58), small, font=font("arialbd.ttf", size_small), fill=(240, 240, 240), anchor="mm")
    d.text((w / 2, h * 0.86), "INSERT COIN", font=font("arialbd.ttf", 22 * u), fill=(255, 255, 255), anchor="mm")
    return img


def menus(card, game):
    """A twin-monitor cabinet's top screen: the game menu, the first chosen; then the game chosen, the time left."""
    w, h = L.SCREEN_SIZES["4:3"]
    u = h / 480
    titles = card["console"]["menu"]
    out = {}
    for name in L.MENUS:
        img = Image.new("RGB", (w, h), (8, 10, 40))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, w, h * 0.16], fill=(200, 30, 30))
        d.text((w / 2, h * 0.08), card["marquee"], font=font("ariblk.ttf", 34 * u), fill=(255, 255, 255), anchor="mm")
        if name == "menu":
            d.text((w / 2, h * 0.23), "SELECT A GAME", font=font("arialbd.ttf", 24 * u), fill=(255, 220, 60),
                   anchor="mm")
            for k, title in enumerate(titles):
                y = h * 0.31 + k * h * 0.08
                if k == 0:
                    d.rectangle([w * 0.1, y - h * 0.035, w * 0.9, y + h * 0.035], fill=(40, 90, 200))
                d.text((w * 0.14, y), f"{k + 1}", font=font("arialbd.ttf", 24 * u), fill=(255, 255, 255), anchor="lm")
                d.text((w * 0.22, y), title.upper(), font=font("arialbd.ttf", 24 * u), fill=(255, 255, 255),
                       anchor="lm")
        else:
            d.text((w / 2, h * 0.3), "NOW PLAYING", font=font("arialbd.ttf", 26 * u), fill=(255, 220, 60), anchor="mm")
            k = min(w * 0.8 / game.logo.width, h * 0.26 / game.logo.height)
            logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
            img.paste(logo, ((w - logo.width) // 2, round(h * 0.5 - logo.height / 2)), logo)
            d.text((w / 2, h * 0.78), "TIME  3:00", font=font("ariblk.ttf", 40 * u), fill=(255, 255, 255), anchor="mm")
            d.text((w / 2, h * 0.9), "GOOD LUCK!", font=font("arialbd.ttf", 22 * u), fill=(120, 220, 255), anchor="mm")
        out[name] = img
    return out


def media(card, game, out):
    size = L.SCREEN_SIZES[card["screen"]]
    shots = dict(boot=boot_screen(card, game, size), title=title_screen(game, size),
                 game1=on_screen(game.shot, size), game2=on_screen(game.frame(0.4), size))
    if card.get("twin"):
        shots.update(menus(card, game))
    image = Image.new("RGB", L.media_size(card), (0, 0, 0))
    for name, (x, y, w, h) in L.media_regions(card).items():
        image.paste(shots[name].resize((w, h), Image.LANCZOS), (x, y))
    save(image, out, f"{card['id']}_media.jpg")


def save(image, out, name):
    """An image saved: a picture (.jpg) as JPEG at quality 90, as the all-games card's art is; the rest PNG."""
    path = os.path.join(out, name)
    if name.endswith(".jpg"):
        image.convert("RGB").save(path, quality=90, optimize=True)
    else:
        image.save(path, optimize=True)
    print(path)


# ---- The printing ----------------------------------------------------------------------------------------------------

def region(cab, name, ground):
    w, h = L.region_size(cab, name)
    return Region(L.PRINT_REGIONS[name], w, h, rgb(ground)), w, h


def paste_image(reg, img, x, y, w, h, fit="cover"):
    """An image into the region's box (x, y, w, h, millimetres): cropped to fill it, or fitted inside it."""
    bw, bh = max(1, round(w * reg.sx)), max(1, round(h * reg.sy))
    if fit == "cover":
        img = ImageOps.fit(img, (bw, bh), Image.LANCZOS)
    else:
        k = min(bw / img.width, bh / img.height)
        img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    layer = img.convert("RGBA")
    reg.img.alpha_composite(layer, (round(x * reg.sx + (bw - layer.width) / 2),
                                    round(y * reg.sy + (bh - layer.height) / 2)))


def marquee(card, cab, made_up):
    """The marquee, lit from behind: a glow of the card's colours, the board's name over it with an outline, the maker
    under it; or a painting under the name; or the four games of a multi-game cabinet under it."""
    c = card["colours"]
    reg, w, h = region(cab, "marquee", c["marquee"])
    art = card.get("marquee_art", {})
    if art.get("kind") == "slots":
        return slots(card, reg, w, h, art, made_up)
    if art.get("kind") == "painting":
        paste_image(reg, painting(art["painting"]).convert("RGB"), 0.0, 0.0, w, h)
        title = lettered(card["marquee"], art["font"], 160, c["marquee_text"], c["marquee_edge"])
        paste_image(reg, title, w * 0.08, h * 0.12, w * 0.84, h * 0.76, fit="contain")
        return reg
    glow = reg.layer()
    gd = ImageDraw.Draw(glow)
    for k in range(16):                                     # the tube's light behind the plexi
        gd.ellipse(reg.box(w * (0.15 - 0.03 * k), h * (0.25 - 0.05 * k), w * (0.85 + 0.03 * k), h * (0.75 + 0.05 * k)),
                   fill=rgb(c["marquee_glow"]) + (14,))
    reg.over(glow)
    size = min(h * 0.5, w * 1.25 / max(1, len(card["marquee"])))
    reg.draw.text(reg.p(w / 2, h * 0.46), card["marquee"], font=font("ariblk.ttf", size * reg.sy),
                  fill=rgb(c["marquee_text"]), anchor="mm", stroke_width=round(size * 0.08 * reg.sy),
                  stroke_fill=rgb(c["marquee_edge"]))
    if card["maker"]:
        reg.text(card["maker"], "arialbd.ttf", min(h * 0.13, size * 0.4), w / 2, h * 0.85, rgb(c["marquee_text"]))
    return reg


def slots(card, reg, w, h, art, made_up):
    """A multi-game cabinet's marquee: its four games' own marquees, two over two, the board's name between them."""
    c = card["colours"]
    band = h * 0.2
    cell_w, cell_h = (w - 30.0) / 2, (h - band - 30.0) / 2
    logos = Path(made_up) / "library" / "media" / "arcade" / "logos"
    hues = ((40, 20, 90), (90, 16, 16), (10, 50, 90), (70, 50, 10))
    for k, stem in enumerate(art["games"]):
        x = 10.0 + (k % 2) * (cell_w + 10.0)
        y = 10.0 + (k // 2) * (cell_h + band + 10.0)
        for i in range(24):                                # each a glow of its own colour
            reg.rect_(x + i * cell_w / 48, y + i * cell_h / 48, x + cell_w - i * cell_w / 48,
                      y + cell_h - i * cell_h / 48, shade(hues[k], i / 40), r=4.0)
        paste_image(reg, Image.open(logos / f"{stem}.png").convert("RGBA"), x + cell_w * 0.06, y + cell_h * 0.1,
                    cell_w * 0.88, cell_h * 0.8, fit="contain")
    y = 10.0 + cell_h + 5.0
    reg.rect_(0.0, y, w, y + band, rgb(c["marquee"]))
    size = min(band * 0.7, w * 1.5 / len(card["marquee"]))
    reg.draw.text(reg.p(w / 2, y + band / 2), card["marquee"], font=font("ariblk.ttf", size * reg.sy),
                  fill=rgb(c["marquee_text"]), anchor="mm", stroke_width=round(size * 0.08 * reg.sy),
                  stroke_fill=rgb(c["marquee_edge"]))
    return reg


def seven(reg, x, y, height, digit, on, off):
    """A seven-segment digit, its top left at (x, y)."""
    segments = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
                "7": "abc", "8": "abcdefg", "9": "abcdfg", " ": ""}[digit]
    w, t = height * 0.55, height * 0.12
    bars = dict(a=(x + t, y, x + w - t, y + t), g=(x + t, y + height / 2 - t / 2, x + w - t, y + height / 2 + t / 2),
                d=(x + t, y + height - t, x + w - t, y + height), f=(x, y + t, x + t, y + height / 2 - t / 2),
                b=(x + w - t, y + t, x + w, y + height / 2 - t / 2),
                e=(x, y + height / 2 + t / 2, x + t, y + height - t),
                c=(x + w - t, y + height / 2 + t / 2, x + w, y + height - t))
    for name, box in bars.items():
        reg.rect_(*box, on if name in segments else off)


def scores(card, cab):
    """A laserdisc cabinet's score panel: each player's score, the lives and the credits in red LEDs."""
    reg, w, h = region(cab, "speakers", card["colours"]["speakers"])
    on, off = (255, 40, 30), (40, 8, 8)
    dh = h * 0.42
    for label, x, digits in (("PLAYER 1", w * 0.06, "  2350"), ("CREDITS", w * 0.43, " 1"),
                             ("PLAYER 2", w * 0.62, "     0")):
        reg.text(label, "arialbd.ttf", h * 0.13, x + len(digits) * dh * 0.36, h * 0.16, (200, 200, 200))
        for k, digit in enumerate(digits):
            seven(reg, x + k * dh * 0.72, h * 0.32, dh, digit, on, off)
    return reg


def speakers(card, cab):
    """The speaker panel's two grilles; or the speaker boxes' fronts, each its grille; or a roof's sign."""
    c = card["colours"]
    reg, w, h = region(cab, "speakers", c["speakers"])
    if "roof_art" in card:
        r = card["roof_art"]
        reg.text(r["text"], "ariblk.ttf", h * 0.32, w / 2, h * 0.62, rgb(r["fill"]))
        return reg
    if L.top_with(cab, "speakers"):
        grille = card.get("grilles", {}).get("kind", "round")
        for t in cab["tops"]:
            if t.get("face") != "speakers":
                continue
            x0, x1 = t["x"][0] + w / 2, t["x"][1] + w / 2
            cx, cy = (x0 + x1) / 2, h / 2
            if grille == "round":                          # a round grille, its cone behind it
                r = min(x1 - x0, h) * 0.38
                reg.circle(cx, cy, r + 6.0, (40, 40, 44))
                reg.circle(cx, cy, r, (22, 22, 24))
                for i in range(-8, 9):
                    for j in range(-8, 9):
                        if (i * i + j * j) * (r / 8.5) ** 2 < r * r:
                            reg.circle(cx + i * r / 8.5, cy + j * r / 8.5, 1.4, (60, 60, 66))
            else:                                          # a slotted grille
                for k in range(9):
                    y = h * 0.18 + k * h * 0.08
                    reg.rect_(x0 + 24.0, y, x1 - 24.0, y + h * 0.04, (52, 52, 58), r=3.0)
        return reg
    for cx in (w * 0.22, w * 0.78):
        reg.rect_(cx - 70.0, h * 0.14, cx + 70.0, h * 0.86, (12, 12, 14), r=10.0)
        for i in range(11):
            for j in range(6):
                reg.circle(cx - 56.0 + i * 11.2, h * 0.22 + j * h * 0.112, 2.6, (46, 46, 52))
    return reg


def bezel(card, cab, game):
    """The bezel's art round the screen: its ground, lines of the card's colours framing the screen, the game's logo in
    the margin over it."""
    art = card["bezel_art"]
    reg, w, h = region(cab, "bezel", art.get("surround", card["colours"]["bezel"]))
    (x0, x1), (s0, s1) = L.recess(cab, card)
    if art.get("speakers"):                                # two round speakers over the screen's corners
        r = min(42.0, (h - s1) / 2 - 6.0)
        for cx in (w * 0.12, w * 0.88):
            reg.circle(cx, (h - s1) / 2, r + 4.0, (40, 40, 44))
            reg.circle(cx, (h - s1) / 2, r, (18, 18, 20))
            reg.circle(cx, (h - s1) / 2, r * 0.4, (52, 52, 56))
    if art.get("rings"):                                   # speaker rings down each side of the screen
        for side in (-1, 1):
            cx = w / 2 + side * (x1 + (w / 2 - x1) / 2)
            r = min(38.0, (w / 2 - x1) / 2 - 6.0)
            for k in range(3):
                cy = h - s0 - (s1 - s0) * (k + 0.5) / 3
                reg.circle(cx, cy, r, rgb(art["rings"]))
                reg.circle(cx, cy, r * 0.62, (20, 20, 24))
    for k, colour in enumerate(art.get("lines", ())):
        e = 6.0 + k * 8.0
        reg.rect_(w / 2 + x0 - e, h - s1 - e, w / 2 + x1 + e, h - s0 + e, None, r=18.0, outline=rgb(colour),
                  width=3.5)
    margin = h - s1 - 30.0                                  # the strip over the screen's frame
    if art.get("logo") and margin > 30.0:
        paste_image(reg, game.logo, w * 0.2, 6.0, w * 0.6, margin - 6.0, fit="contain")
    return reg


def panel(card, cab):
    """The control panel's top: its overlay (speckled laminate, diamond plate, a band, a sunset, stripes, a wave), the
    instruction cards, pads under the buttons, the sticks' and buttons' rings, 1P and 2P, START's legends."""
    art = card["panel_art"]
    p = cab["panel"]
    w, d = p["width"], p["back"]
    ground = rgb(art.get("ground", "#808080"))
    reg = Region(L.PRINT_REGIONS["panel"], w, d, ground)

    def at(x, v):
        return x + w / 2, d - v
    rng = random.Random(7)
    if "painting" in art:                                  # a painted overlay
        paste_image(reg, ImageEnhance.Brightness(painting(art["painting"]).convert("RGB")).enhance(0.8), 0.0, 0.0, w, d)
    if "lines" in art:                                     # stripes across the front, a strip of colours behind
        for k in range(int(d * 0.7 / 8)):
            reg.rect_(0.0, d - k * 8.0 - 3.0, w, d - k * 8.0, rgb(art["lines"]))
        for k, colour in enumerate(art.get("strip", ())):
            n = len(art["strip"])
            reg.rect_(w * k / n, 0.0, w * (k + 1) / n, d * 0.3, rgb(colour))
    if "border" in art:                                    # a dark border round a lit strip at the back
        reg.rect_(0.0, 0.0, w, d, None, outline=rgb(art["border"]), width=22.0)
        reg.rect_(30.0, 18.0, w - 30.0, d * 0.22, rgb(art.get("lit_strip", "#F0F0F0")), r=4.0)
        for k in range(8):
            reg.rect_(50.0 + k * (w - 100.0) / 8, 28.0, 50.0 + (k + 0.7) * (w - 100.0) / 8, d * 0.2,
                      (200, 196, 190), r=2.0)
    if art.get("speckle"):
        for _ in range(int(w * d / 40)):
            reg.circle(rng.uniform(0, w), rng.uniform(0, d), rng.uniform(0.6, 1.6),
                       shade(ground, rng.uniform(-0.35, 0.3)))
    if art.get("diamond"):                                 # diamond plate: rows of raised diamonds
        for j in range(int(d / 14) + 2):
            for i in range(int(w / 14) + 2):
                x, y = i * 14.0 + (7.0 if j % 2 else 0.0), j * 14.0
                reg.poly([(x - 5, y), (x, y - 2), (x + 5, y), (x, y + 2)], shade(ground, 0.22))
    if "sunset" in art:                                    # a sunset graded across the panel, back to front
        for k in range(int(d) + 1):
            reg.rect_(0.0, k, w, k + 1.0, graded(art["sunset"], k / d))
        for k in range(14):                                # its sun, low over the horizon
            reg.circle(w * 0.5, d * 0.52, 70.0 - k * 4.0, mix(rgb(art["sunset"][2]), (255, 240, 200), k / 14))
    if "stripes" in art:
        for k, colour in enumerate(art["stripes"]):
            reg.poly([(0.0, d * (0.62 + 0.1 * k)), (w, d * (0.38 + 0.1 * k)), (w, d * (0.44 + 0.1 * k)),
                      (0.0, d * (0.68 + 0.1 * k))], rgb(colour))
    if "wave" in art:                                      # a wave graded across the front
        for k in range(int(w) + 1):
            top = d * (0.35 + 0.12 * math.sin(k / w * math.pi * 2))
            reg.rect_(k, top, k + 1.0, d, graded(art["wave"], k / w))
    if "band" in art:                                      # a band across the panel, under the controls
        reg.rect_(0.0, d * 0.18, w, d * 0.86, rgb(art["band"]))
        if "band_edge" in art:
            for y in (d * 0.18, d * 0.86):
                reg.rect_(0.0, y - 5.0, w, y + 5.0, rgb(art["band_edge"]))
    if "pads" in art:
        for player, spots in L.buttons(cab, card).items():
            sx, sv = cab["sticks"][player]
            xs = [x for x, _ in spots] + [sx]
            reg.rect_(*at(min(xs) - 50.0, sv + 70.0), *at(max(xs) + 30.0, sv - 70.0), rgb(art["pads"]), r=16.0)
    if art.get("cards"):                                   # the instruction cards
        for side in (-1, 1):
            cx = side * (w / 2 - 150.0)
            reg.rect_(*at(cx - 70.0, d - 40.0), *at(cx + 70.0, d - 110.0), (246, 214, 60), r=3.0)
            for k in range(4):
                reg.rect_(*at(cx - 58.0, d - 52.0 - k * 13.0), *at(cx + 40.0 - 12.0 * (k % 2), d - 56.0 - k * 13.0),
                          (60, 50, 20))
    if "frame" in art:                                     # a frame round the stick, as the early panels had
        sx, sv = cab["sticks"]["p1"]
        reg.rect_(*at(sx - 62.0, sv + 62.0), *at(sx + 62.0, sv - 62.0), None, r=8.0, outline=rgb(art["frame"]),
                  width=5.0)
    if "legends" in art:                                   # a driving cabinet's dash: its buttons' legends
        ink = (236, 236, 236)
        xs = [x for x, _ in cab.get("views", ())]
        if xs:
            reg.text(art["legends"][0], "arialbd.ttf", 13.0, *at(sum(xs) / len(xs), cab["views"][0][1] + 30.0), ink)
        x, v = cab["start"][0]
        reg.text(art["legends"][1], "arialbd.ttf", 13.0, *at(x, v + 30.0), ink)
    if art.get("rings"):
        ink = (24, 24, 28) if sum(ground) > 300 else (236, 236, 236)
        players = [player for player in ("p1", "p2") if player in cab["sticks"]]
        for player in players:
            sx, sv = cab["sticks"][player]
            reg.circle(*at(sx, sv), 34.0, shade(ground, -0.3))
            if len(players) > 1:
                reg.text(player[1] + "P", "arialbd.ttf", 16.0, *at(sx, sv - 54.0), ink)
        for spots in L.buttons(cab, card).values():
            for x, v in spots:
                reg.circle(*at(x, v), cab["button"]["r"] + 3.5, shade(ground, -0.4))
        legends = ("1 PLAYER", "2 PLAYERS") if len(cab["start"]) > 1 else ("START",)
        for (x, v), legend in zip(cab["start"], legends):
            reg.text(legend, "arialbd.ttf", 8.0, *at(x, v + 24.0), ink)
    return reg


def front(card, cab):
    """The lower front: its colour, and a candy cabinet's service doors with their locks."""
    c = card["colours"]
    reg, w, h = region(cab, "front", c["lower"])
    art = card.get("front_art", {})
    if "doors" in art:
        line = rgb(art["doors"])
        for x0, x1 in ((40.0, w / 2 - 12.0), (w / 2 + 12.0, w - 40.0)):
            reg.rect_(x0, h * 0.12, x1, h * 0.9, None, r=6.0, outline=line, width=3.0)
            reg.circle(x1 - 30.0, h * 0.5, 9.0, shade(rgb(c["lower"]), -0.25))
            reg.circle(x1 - 30.0, h * 0.5, 4.0, (60, 60, 64))
    return reg


def pop(card, cab, game):
    """A POP sign: the game's key art in a white frame, its logo over it. A driving cabinet's seat back, its decal:
    a race number, the game's logo."""
    if "seat_art" in card:
        art = card["seat_art"]
        reg, w, h = region(cab, "pop", art["ground"])
        if art.get("number"):
            reg.draw.text(reg.p(w / 2, h * 0.38), art["number"], font=font("ariblk.ttf", h * 0.42 * reg.sy),
                          fill=(255, 255, 255), anchor="mm", stroke_width=round(h * 0.03 * reg.sy),
                          stroke_fill=(20, 20, 24))
        if art.get("logo"):
            paste_image(reg, game.logo, w * 0.08, h * (0.62 if art.get("number") else 0.3), w * 0.84, h * 0.3,
                        fit="contain")
        return reg
    reg, w, h = region(cab, "pop", "#FFFFFF")
    paste_image(reg, game.keyart, 8.0, 8.0, w - 16.0, h - 16.0)
    paste_image(reg, game.logo, w * 0.1, h * 0.06, w * 0.8, h * 0.4, fit="contain")
    return reg


def strip(card, cab):
    """The control panel's front: the board's name, or the maker's badge."""
    art = card["strip_art"]
    reg, w, h = region(cab, "strip", art["ground"])
    if "badge" in art:
        size = h * 0.62
        reg.draw.text(reg.p(w / 2, h / 2), art["badge"], font=font("ariblk.ttf", size * reg.sy), fill=rgb(art["fill"]),
                      anchor="mm", stroke_width=round(size * 0.1 * reg.sy), stroke_fill=rgb(art["edge"]))
    elif art["text"]:
        reg.text(art["text"], "ariblk.ttf", h * 0.5, w / 2, h / 2, rgb(art["fill"]))
    return reg


def print_atlas(card, cab, game, made_up, out):
    c = card["colours"]
    image = Image.new("RGB", (L.PRINT_ATLAS, L.PRINT_ATLAS), rgb(c["case"]))
    regions = [bezel(card, cab, game), panel(card, cab), front(card, cab)]
    if "marquee" in cab or L.top_with(cab, "marquee"):
        regions.append(marquee(card, cab, made_up))
    if "speakers" in cab or L.top_with(cab, "speakers"):
        regions.append(scores(card, cab) if card.get("score_art") else speakers(card, cab))
    if L.top_with(cab, "pop") or "seat" in cab:
        regions.append(pop(card, cab, game))
    if cab["panel"].get("strip"):
        regions.append(strip(card, cab))
    for reg in regions:
        reg.paste(image)
    d = ImageDraw.Draw(image)
    b1, b2, b3, b4 = (tuple(card["buttons"]) * 2)[:4]       # three colours, or a fourth for Neo Geo's arc
    ball1, ball2 = card["balls"]
    colours = dict(case=c["case"], side=c["side"], moulding=c.get("moulding", c["case"]), black="#141416",
                   metal=c["metal"], dark="#0A0A0C", coin="#D2C8A0", white="#F4F4F2", red="#C8201E", red_lit="#FF5A40",
                   b1=b1, b2=b2, b3=b3, b4=b4, start=card.get("start", "#E8E8E4"),
                   start_lit=card.get("start_lit", "#FFFFF0"), ball1=ball1, ball2=ball2, panel_edge=c["panel_edge"],
                   kick=c["kick"], lower=c["lower"], top=c.get("top", c["case"]), trim=c.get("trim", c["case"]),
                   grille="#1A1A1E", stick="#18181A", seat=c.get("seat", "#202024"), seat2=c.get("seat2", "#202024"),
                   base=c.get("base", "#18181C"), rubber="#141416", chrome="#C8CACE", dash=c.get("dash", "#1E1E22"),
                   pedal="#7A7C80", lit=c.get("marquee_glow", "#FFFFFF"), lit2="#FFFFFF")
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 11, y - 11, x + 11, y + 11], fill=rgb(colours[name]))
    save(image, out, f"{card['id']}_print.png")


# ---- The side art ----------------------------------------------------------------------------------------------------

def side_art(card, cab, game, out):
    """The side art, drawn at a millimetre a pixel over the side outline's bounds (y across from the front, z up),
    then fitted to SIDE_PX: fills, polygons, lines, bands graded along their length, tapering swooshes, flames,
    lettering and the game's key art."""
    lo, hi, top = L.side_bounds(cab)
    img = Image.new("RGBA", (round(hi - lo), round(top)), (0, 0, 0, 0))

    def p(y, z):
        return (y - lo, top - z)
    for shape in card["side"]:
        kind = shape[0]
        d = ImageDraw.Draw(img)
        if kind == "fill":
            d.rectangle([0, 0, img.width, img.height], fill=ground(shape[1]))
        elif kind == "poly":
            d.polygon([p(*q) for q in shape[1]], fill=rgb(shape[2]))
        elif kind == "line":
            d.line([p(*q) for q in shape[1]], fill=rgb(shape[2]), width=round(shape[3]))
        elif kind == "band":
            band(img, [p(*q) for q in shape[1]], shape[2], shape[3])
        elif kind == "swoosh":
            swoosh(img, [p(*q) for q in shape[1]], shape[2], shape[3])
        elif kind == "flame":
            flame(img, p(*shape[1]), p(*shape[2]), shape[3], shape[4])
        elif kind == "flames":
            (y0, z0), (y1, z1) = shape[1], shape[2]
            flames(img, p(y0, z1), p(y1, z0))
        elif kind == "text":
            _, s, name, size, (y, z), angle, fill, edge = shape
            lettering(img, s, name, size, p(y, z), angle, fill, edge)
        elif kind == "art":
            _, source, (y0, z0, y1, z1), fade, fit = shape
            art(img, game.keyart if source == "keyart" else painting(source).convert("RGB"), p(y0, z1), p(y1, z0),
                fade, fit)
        elif kind == "rrect":
            _, (y0, z0, y1, z1), r, colour = shape
            d.rounded_rectangle([*p(y0, z1), *p(y1, z0)], radius=r, fill=rgb(colour))
        elif kind == "stripes":
            _, (y0, z0, y1, z1), n, colour, seed = shape
            stripes(img, p(y0, z1), p(y1, z0), n, colour, seed)
        elif kind == "checks":
            _, (y0, z0, y1, z1), size, c1, c2 = shape
            (x0, t0), (x1, t1) = p(y0, z1), p(y1, z0)
            for i in range(int((x1 - x0) / size) + 1):
                for j in range(int((t1 - t0) / size) + 1):
                    d.rectangle([x0 + i * size, t0 + j * size, x0 + (i + 1) * size, t0 + (j + 1) * size],
                                fill=rgb(c1 if (i + j) % 2 else c2))
    save(img.convert("RGB").resize(L.SIDE_PX, Image.LANCZOS), out, f"{card['id']}_side.jpg")


def graded(stops, t):
    """A colour graded through the stops (hex colours, evenly spaced), t from 0 to 1."""
    stops = [rgb(c) for c in stops]
    t = min(1.0, max(0.0, t)) * (len(stops) - 1)
    i = min(len(stops) - 2, int(t))
    return mix(stops[i], stops[i + 1], t - i)


def band(img, points, width, stops):
    """A band of even width along a polyline, graded through its stops from its first point to its last."""
    d = ImageDraw.Draw(img)
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total, done = sum(lengths), 0.0
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        n = max(1, round(length / 2))
        for i in range(n + 1):
            t = i / n
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2],
                      fill=graded(stops, (done + length * t) / total))
        done += length


def curve(points, n=80):
    """A smooth curve through the points (Catmull-Rom)."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for j in range(n):
            t = j / n
            out.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t
                                    + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
    out.append(tuple(points[-1]))
    return out


def swoosh(img, points, width, stops):
    """A swoosh: a stroke along a smooth curve, widest in its middle and tapering to points, graded along it."""
    d = ImageDraw.Draw(img)
    path = curve(points)
    for i, (x, y) in enumerate(path):
        t = i / (len(path) - 1)
        r = width / 2 * math.sin(math.pi * t) ** 0.8
        d.ellipse([x - r, y - r, x + r, y + r], fill=graded(stops, t))


def flame(img, base, tip, width, stops):
    """A flame: tongues licking from a broad base to a tip, graded from the base's colour to the tip's."""
    d = ImageDraw.Draw(img)
    rng = random.Random(3)
    (bx, by), (tx, ty) = base, tip
    length = math.dist(base, tip)
    ux, uy = (tx - bx) / length, (ty - by) / length
    for tongue in range(5):
        spread = (tongue - 2) * width * 0.16
        reach = length * (1.0 - abs(tongue - 2) * 0.14) * rng.uniform(0.9, 1.0)
        for i in range(220):
            t = i / 220
            wob = math.sin(t * 9.0 + tongue) * width * 0.06 * t
            cx = bx + ux * reach * t - uy * (spread * (1 - t) + wob)
            cy = by + uy * reach * t + ux * (spread * (1 - t) + wob)
            r = width * 0.22 * (1 - t) ** 0.9 + 1.0
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=graded(stops, t))


def flames(img, a, b):
    """Flames filling a box (its top left and bottom right), red and yellow licking up over black."""
    (x0, y0), (x1, y1) = a, b
    rng = random.Random(5)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([x0, y0, x1, y1], fill=(16, 16, 16))
    for _ in range(60):
        x = rng.uniform(x0, x1)
        h = rng.uniform(0.3, 1.0) * (y1 - y0)
        w = rng.uniform(10, 30)
        for i in range(30):
            t = i / 30
            r = w * (1 - t) * 0.5 + 1
            cy = y1 - h * t
            d.ellipse([x - r, cy - r, x + r, cy + r], fill=graded(("#F8E040", "#F89020", "#C02810"), t) + (200,))
    layer = layer.crop((round(x0), round(y0), round(x1), round(y1)))
    img.alpha_composite(layer, (round(x0), round(y0)))


def lettering(img, s, name, size, at, angle, fill, edge):
    """Text at a point, turned by angle (degrees, anticlockwise), with an outline (its colour and width)."""
    f = font(name, size)
    stroke = round(edge[1]) if edge else 0
    box = f.getbbox(s, stroke_width=stroke)
    layer = Image.new("RGBA", (box[2] - box[0] + 8, box[3] - box[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((4 - box[0], 4 - box[1]), s, font=f, fill=rgb(fill), stroke_width=stroke,
                               stroke_fill=rgb(edge[0]) if edge else None)
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(layer, (round(at[0] - layer.width / 2), round(at[1] - layer.height / 2)))


def art(img, picture, a, b, fade, fit="cover"):
    """A picture over a box (its top left and bottom right): cropped to fill it, or fitted inside it (on a picture's
    own plain ground); faded out at its edges."""
    (x0, y0), (x1, y1) = a, b
    w, h = round(x1 - x0), round(y1 - y0)
    if fit == "contain":
        k = min(w / picture.width, h / picture.height)
        piece = picture.resize((round(picture.width * k), round(picture.height * k)), Image.LANCZOS).convert("RGBA")
        x0, y0 = x0 + (w - piece.width) / 2, y0 + (h - piece.height) / 2
        w, h = piece.size
    else:
        piece = ImageOps.fit(picture, (w, h), Image.LANCZOS).convert("RGBA")
    if fade:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([fade, fade, w - fade, h - fade], radius=fade, fill=255)
        piece.putalpha(mask.filter(ImageFilter.GaussianBlur(fade / 2)))
    img.alpha_composite(piece, (round(x0), round(y0)))


def ground(colour):
    """A fill: a colour, or a painting's plain ground (its corners' colour)."""
    if colour.startswith("painting:"):
        picture = painting(colour.split(":", 1)[1]).convert("RGB")
        corners = [picture.getpixel((x, y)) for x in (4, picture.width - 5) for y in (4, picture.height - 5)]
        return tuple(round(sum(c[i] for c in corners) / 4) for i in range(3))
    return rgb(colour)


def stripes(img, a, b, n, colour, seed):
    """Brush strokes across a box (its top left and bottom right): n of them, each of its own length, ragged at its
    ends."""
    (x0, y0), (x1, y1) = a, b
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    for k in range(n):
        y = y0 + (y1 - y0) * (k + 0.5) / n
        t = (y1 - y0) / n * rng.uniform(0.35, 0.55)
        start, end = x0 + rng.uniform(0.0, 0.25) * (x1 - x0), x1 - rng.uniform(0.0, 0.3) * (x1 - x0)
        for i in range(int(end - start)):
            jag = t * (0.5 + 0.5 * rng.random()) if i > (end - start) * 0.85 else t
            d.line([(start + i, y - jag / 2), (start + i, y + jag / 2)], fill=rgb(colour))


def main(card_id, made_up, out):
    os.makedirs(out, exist_ok=True)
    card = dict(L.CARDS[card_id], id=card_id)
    cab = L.CABINETS[card["cabinet"]]
    if "laserdisc" in card:
        game = LaserdiscGame(card["laserdisc"])
    elif "console" in card:
        game = Game(card["console"]["stem"], made_up, card["console"]["system"])
    else:
        game = Game(card["game"], made_up)
    print_atlas(card, cab, game, made_up, out)
    side_art(card, cab, game, out)
    media(card, game, out)


if __name__ == "__main__":
    main(sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]))
