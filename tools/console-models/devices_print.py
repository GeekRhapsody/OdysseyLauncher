"""The device cards' screens and printing (devices.py builds the cards): one image a card, `<card>_media.png` (or
`.jpg`, for a card of pictures), its regions as devices_layout.py has them; and OpenBOR's drum (props.py). The games
on the screens are tools/made-up-games's (made up: no real game's art): their screenshots, a second frame rendered from
their paintings (arcade_print.Game), their covers, logos and key art, reduced to each fantasy console's own palette
and resolution (TIC-80's Sweetie 16 at 240 x 136, WASM-4's four greens at 160 x 160, LowRes NX's 160 x 128). The
pinball machine's playfield and backglass, and the drum, are paintings (paintings.py); everything else is drawn here.
Make the made-up games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow,
numpy, scipy):

    python tools/console-models/devices_print.py <card> artifacts/made-up-games <out folder>
"""

import math
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import devices_layout as L  # noqa: E402
from arcade_print import Game, font, lettered, painting  # noqa: E402
from retro_pc_print import mix, rgb, shade  # noqa: E402


def palette_image(colours):
    pal = Image.new("P", (1, 1))
    flat = [c for colour in colours for c in rgb(colour)]
    pal.putpalette(flat + flat[:3] * (256 - len(colours)))
    return pal


def reduced(img, size, colours):
    """A picture at a fantasy console's resolution and in its palette: cropped to its shape, each pixel its nearest
    colour."""
    small = ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS)
    return small.quantize(palette=palette_image(colours), dither=Image.Dither.NONE).convert("RGB")


def put(atlas, card, name, img, pixels=False):
    x, y, w, h = L.REGIONS[card][name]
    atlas.paste(img.convert("RGB").resize((w, h), Image.NEAREST if pixels else Image.LANCZOS), (x, y))


def pixel_text(img, xy, text, size, fill, name="consolab.ttf"):
    ImageDraw.Draw(img).text(xy, text, font=font(name, size), fill=rgb(fill) if isinstance(fill, str) else fill)


# ---- TIC-80 ----------------------------------------------------------------------------------------------------------

def tic80(atlas, made_up):
    c = L.TIC80_COLOURS
    for name, eyes in (("eyes", "open"), ("blink", "shut")):
        face = Image.new("RGB", (18, 10), rgb(c["W"]))
        d = ImageDraw.Draw(face)
        d.rectangle([0, 0, 17, 1], fill=rgb(c["N"]))
        for x0 in (4, 12):
            if eyes == "open":
                d.rectangle([x0, 3, x0 + 1, 7], fill=rgb(c["N"]))
            else:
                d.rectangle([x0 - 1, 6, x0 + 2, 6], fill=rgb(c["N"]))
        put(atlas, "tic80", name, face, pixels=True)
    game = Game("Springheel Sam (Europe)", made_up, "megadrive")
    put(atlas, "tic80", "game1", reduced(game.shot, (240, 136), L.SWEETIE16), pixels=True)
    put(atlas, "tic80", "game2", reduced(game.frame(0.35), (240, 136), L.SWEETIE16), pixels=True)
    # The cartridge's label, as TIC-80's cartridges are drawn: its picture in a window, its title under it.
    label = Image.new("RGB", (120, 100), rgb(c["edge"]))
    d = ImageDraw.Draw(label)
    d.rectangle([4, 4, 115, 66], fill=rgb(c["cart"]))
    label.paste(reduced(game.keyart, (106, 56), L.SWEETIE16), (7, 7))
    d.rectangle([4, 70, 115, 95], fill=rgb(c["cart"]))
    pixel_text(label, (8, 72), game.title.upper(), 10, "#F4F4F4")
    pixel_text(label, (8, 84), "TIC-80 CARTRIDGE", 8, "#94B0C2")
    put(atlas, "tic80", "label", label, pixels=True)


# ---- WASM-4 ----------------------------------------------------------------------------------------------------------

def wasm4(atlas, made_up):
    game = Game("Deep Fathom (Europe)", made_up, "megadrive")
    title = reduced(game.shot, (160, 160), L.WASM4_PALETTE).convert("RGBA")
    dim = Image.new("RGBA", title.size, rgb(L.WASM4_PALETTE[3]) + (170,))
    title.alpha_composite(dim)
    logo = reduced(game.logo.convert("RGB"), (140, 50), L.WASM4_PALETTE).convert("RGBA")
    logo.putalpha(game.logo.resize((140, 50)).getchannel("A").point(lambda a: 255 if a > 100 else 0))
    title.alpha_composite(logo, (10, 40))
    pixel_text(title, (34, 120), "PRESS X", 12, L.WASM4_PALETTE[0])
    put(atlas, "wasm4", "title", title, pixels=True)
    put(atlas, "wasm4", "game1", reduced(game.shot, (160, 160), L.WASM4_PALETTE), pixels=True)
    put(atlas, "wasm4", "game2", reduced(game.frame(0.35), (160, 160), L.WASM4_PALETTE), pixels=True)


# ---- LowRes NX -------------------------------------------------------------------------------------------------------

def lowresnx(atlas, made_up):
    for name, lines in (("ready", ["READY.", "_"]), ("run", ["READY.", "RUN", "_"])):
        screen = Image.new("RGB", (160, 128), rgb("#07C8C8"))
        for k, line in enumerate(lines):
            pixel_text(screen, (6, 6 + 12 * k), line, 11, "#0F0F0F")
        put(atlas, "lowresnx", name, screen, pixels=True)
    game = Game("Kaleidrop (Europe)", made_up, "megadrive")
    put(atlas, "lowresnx", "game1", reduced(game.shot, (160, 128), L.LOWRES_PALETTE), pixels=True)
    put(atlas, "lowresnx", "game2", reduced(game.frame(0.35), (160, 128), L.LOWRES_PALETTE), pixels=True)


# ---- Vircon32 --------------------------------------------------------------------------------------------------------

def vircon32(atlas, made_up):
    c = L.VIRCON_COLOURS
    game = Game("Ghoulish Gus (Europe)", made_up, "megadrive")
    label = Image.new("RGB", (750, 300), (0, 0, 0))
    d = ImageDraw.Draw(label)
    d.rectangle([0, 0, 70, 300], fill=rgb("#E8A6B4"))
    strip = Image.new("RGBA", (300, 70), (0, 0, 0, 0))
    ImageDraw.Draw(strip).text((150, 35), "GAME CARTRIDGE", font=font("arialbd.ttf", 26), fill=(30, 30, 30),
                               anchor="mm")
    label.paste(strip.rotate(90, expand=True), (0, 0), strip.rotate(90, expand=True))
    d.text((115, 150), "V32", font=font("ariblki.ttf" if os.path.exists("C:/Windows/Fonts/ariblki.ttf") else
                                         "ariblk.ttf", 40), fill=rgb("#80B3FF"), anchor="mm")
    d.rectangle([84, 180, 146, 188], fill=rgb("#66FF00"))
    art = ImageOps.fit(game.keyart, (590, 300), Image.LANCZOS)
    label.paste(art, (160, 0))
    logo = game.logo.copy()
    logo.thumbnail((520, 130), Image.LANCZOS)
    label.paste(logo, (160 + (590 - logo.width) // 2, 14), logo)
    put(atlas, "vircon32", "label", label)
    card = Image.new("RGB", (200, 240), rgb("#5A5E78"))
    d = ImageDraw.Draw(card)
    d.text((100, 30), "MEMORY CARD", font=font("arialbd.ttf", 22), fill=(255, 255, 255), anchor="mm")
    d.polygon([(0, 60), (200, 60), (200, 170), (0, 170)], fill=(255, 255, 255))
    d.polygon([(0, 150), (130, 60), (200, 60), (60, 170), (0, 170)], fill=rgb("#E07A98"))
    d.rectangle([50, 92, 150, 140], fill=(255, 255, 255), outline=(0, 0, 0), width=4)
    d.text((100, 116), "1 MB", font=font("ariblk.ttf", 30), fill=(0, 0, 0), anchor="mm")
    d.rectangle([0, 170, 200, 240], fill=(0, 0, 0))
    d.text((100, 205), "Vircon32", font=font("arialbi.ttf", 32), fill=rgb("#5FD38D"), anchor="mm")
    put(atlas, "vircon32", "card", card)
    top = Image.new("RGB", (600, 200), rgb(c["body"]))
    d = ImageDraw.Draw(top)
    d.text((300, 86), "Vircon32", font=font("arialbi.ttf", 96), fill=rgb("#2E8A5A"), anchor="mm")
    d.rectangle([150, 146, 450, 156], fill=rgb("#46C016"))
    put(atlas, "vircon32", "top", top)
    front = Image.new("RGB", (1000, 120), rgb(c["inset"]))
    d = ImageDraw.Draw(front)
    for k in range(4):
        x = 90 + k * 130
        d.text((x, 30), f"P{k + 1}", font=font("arialbd.ttf", 28), fill=rgb(c["dark"]), anchor="mm")
        d.rounded_rectangle([x - 40, 62, x + 40, 92], radius=6, fill=rgb(c["dark"]))
        d.rectangle([x - 28, 72, x + 28, 82], fill=(20, 20, 20))
    d.text((820, 30), "MEMORY CARD", font=font("arialbd.ttf", 28), fill=rgb(c["dark"]), anchor="mm")
    d.rounded_rectangle([700, 62, 940, 92], radius=6, fill=rgb(c["dark"]))
    d.rectangle([720, 72, 920, 82], fill=(20, 20, 20))
    put(atlas, "vircon32", "front", front)


# ---- Pinball ---------------------------------------------------------------------------------------------------------

def fpinball(atlas, made_up):
    put(atlas, "fpinball", "playfield", ImageOps.fit(painting("fpinball_playfield").convert("RGB"), (400, 800),
                                                      Image.LANCZOS))
    glass = ImageOps.fit(painting("fpinball_backglass").convert("RGB"), (600, 600), Image.LANCZOS).convert("RGBA")
    title = lettered("Future Pinball", "SCRIPTBL.TTF", 140, "#D89A50", "#3A2210")
    k = min(560 / title.width, 130 / title.height)
    title = title.resize((round(title.width * k), round(title.height * k)), Image.LANCZOS)
    glass.alpha_composite(title, ((600 - title.width) // 2, 18))
    put(atlas, "fpinball", "backglass", glass)
    apron = Image.new("RGB", (600, 120), rgb("#1E1E26"))
    d = ImageDraw.Draw(apron)
    for x0 in (20, 420):
        d.rectangle([x0, 20, x0 + 160, 100], fill=rgb("#F2E6C0"))
        for k in range(5):
            d.rectangle([x0 + 12, 30 + k * 14, x0 + 140 - 20 * (k % 2), 36 + k * 14], fill=rgb("#5A4A2A"))
    d.text((300, 60), "FUTURE PINBALL", font=font("arialbd.ttf", 26), fill=rgb("#D89A50"), anchor="mm")
    put(atlas, "fpinball", "apron", apron)


def vpinball(atlas, made_up):
    w, h = 1024, 512                                       # the ball's chrome, round it as its UVs go: a room's
    ball = Image.new("RGB", (w, h))                        # light above, the playfield below, the X at its front
    for y in range(h):
        t = y / h
        colour = (mix((236, 240, 246), (150, 156, 170), t / 0.48) if t < 0.48 else
                  mix((40, 34, 30), (90, 70, 50), (t - 0.48) / 0.52))
        ImageDraw.Draw(ball).line([(0, y), (w, y)], fill=colour)
    d = ImageDraw.Draw(ball)
    rng = random.Random(4)
    for _ in range(14):                                    # reflections: lights and windows above
        x, y = rng.uniform(0, w), rng.uniform(h * 0.08, h * 0.4)
        d.ellipse([x - 26, y - 10, x + 26, y + 10], fill=(255, 255, 255))
    d.rectangle([0, h * 0.47, w, h * 0.5], fill=(60, 60, 70))
    cx, cy = w * 0.75, h * 0.5                            # the X, at the ball's front
    for sign in (-1, 1):
        stroke = [(cx - 120, cy - sign * 150), (cx + 120, cy + sign * 150)]
        d.line(stroke, fill=(232, 224, 160), width=62)
        d.line(stroke, fill=(18, 18, 18), width=46)
    put(atlas, "vpinball", "ball", ball.filter(ImageFilter.GaussianBlur(2)))
    field = Image.new("RGB", (512, 430), rgb("#141A4A"))
    d = ImageDraw.Draw(field)
    rng = random.Random(9)
    for _ in range(160):
        x, y, r = rng.uniform(0, 512), rng.uniform(0, 430), rng.uniform(0.6, 2.2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 220, 255))
    d.ellipse([256 - 92, 60 - 92 + 30, 256 + 92, 60 + 92 + 30], outline=rgb("#F6C820"), width=10)
    for k in range(3):                                     # arrow inserts up the middle
        y = 330 - k * 46
        d.polygon([(236, y), (256, y - 30), (276, y), (256, y - 12)], fill=rgb(("#E8302A", "#F6C820", "#3ADA6A")[k]))
    for sign in (-1, 1):                                   # the inlanes' guides
        d.line([(256 + sign * 230, 160), (256 + sign * 200, 300), (256 + sign * 110, 400)], fill=rgb("#C8CCD2"),
               width=8)
    put(atlas, "vpinball", "playfield", field)
    apron = Image.new("RGBA", (512, 90), rgb("#B81E1A") + (255,))
    name = lettered("VISUAL PINBALL", "ariblk.ttf", 80, "#F6D23A", "#141414")
    name.thumbnail((470, 70), Image.LANCZOS)
    apron.alpha_composite(name, ((512 - name.width) // 2, (90 - name.height) // 2))
    put(atlas, "vpinball", "apron", apron)


# ---- The terminal ----------------------------------------------------------------------------------------------------

ADVENTURE = {
    "dark": ["", "It is too dark to see. Somewhere,", "water drips.", "", ">_"],
    "typed": ["", "It is too dark to see. Somewhere,", "water drips.", "", ">LIGHT LAMP_"],
    "lit": [">LIGHT LAMP", "The brass lantern is now on.", "", "Cellar", "Damp stone walls glisten in the",
            "lamplight. Barrels are stacked", "against the north wall, and a", "narrow stair climbs into the dark.",
            "A rusty key lies on the floor.", "", ">_"],
    "room": [">TAKE KEY", "Taken.", "", ">CLIMB STAIR", "", "Kitchen", "A cold hearth, a long table and a",
             "door to the garden. A hook for a", "lantern hangs by the door.", "", ">_"],
}
STATUS = {"dark": ("Cellar", "Moves: 0"), "typed": ("Cellar", "Moves: 0"), "lit": ("Cellar", "Moves: 1"),
          "room": ("Kitchen", "Moves: 3")}


def zmachine(atlas, made_up):
    green = (60, 255, 120)
    for name, lines in ADVENTURE.items():
        screen = Image.new("RGB", (480, 360), (4, 14, 8))
        glow = Image.new("RGB", screen.size, (0, 0, 0))
        for target, colour in ((glow, green), (screen, green)):
            d = ImageDraw.Draw(target)
            d.rectangle([12, 10, 468, 34], fill=colour)
            place, moves = STATUS[name]
            d.text((20, 22), place, font=font("consolab.ttf", 20), fill=(4, 14, 8), anchor="lm")
            d.text((460, 22), moves, font=font("consolab.ttf", 20), fill=(4, 14, 8), anchor="rm")
            for k, line in enumerate(lines):
                d.text((20, 46 + 27 * k), line, font=font("consola.ttf", 21), fill=colour)
        screen = Image.blend(screen, Image.composite(glow.filter(ImageFilter.GaussianBlur(5)), screen,
                                                     Image.new("L", screen.size, 110)), 0.6)
        put(atlas, "zmachine", name, screen)


# ---- Steam Deck ------------------------------------------------------------------------------------------------------

def steam(atlas, made_up):
    games = ["Springheel Sam", "Stormfist", "Kaleidrop", "Deep Fathom", "Ghoulish Gus", "Redline Riviera"]
    covers = [Image.open(Path(made_up) / "library" / "media" / "megadrive" / "covers" / f"{g} (Europe).jpg")
              .convert("RGB") for g in games]
    w, h = 960, 600
    library = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(library)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=mix((30, 36, 52), (12, 14, 20), y / h))
    d.text((40, 40), "Library", font=font("segoeuib.ttf" if os.path.exists("C:/Windows/Fonts/segoeuib.ttf")
                                          else "arialbd.ttf", 40), fill=(240, 240, 240), anchor="lm")
    d.text((920, 40), "10:41", font=font("arialbd.ttf", 30), fill=(220, 220, 220), anchor="rm")
    for k, cover in enumerate(covers[:5]):
        cw, ch = (230, 320) if k == 0 else (160, 224)
        x = 40 if k == 0 else 300 + (k - 1) * 170
        y = 110 if k == 0 else 150
        library.paste(ImageOps.fit(cover, (cw, ch), Image.LANCZOS), (x, y))
        if k == 0:
            d.rectangle([x - 5, y - 5, x + cw + 4, y + ch + 4], outline=(255, 255, 255), width=5)
    d.text((40, 470), games[0], font=font("arialbd.ttf", 34), fill=(250, 250, 250), anchor="lm")
    d.rounded_rectangle([40, 510, 250, 566], radius=8, fill=rgb("#4C8CF0"))
    d.text((145, 538), "PLAY", font=font("arialbd.ttf", 28), fill=(255, 255, 255), anchor="mm")
    put(atlas, "steam", "library", library)
    game = Game("voltcrwn", made_up)
    for name, frame in (("game1", game.shot), ("game2", game.frame(0.4))):
        put(atlas, "steam", name, ImageOps.fit(frame.convert("RGB"), (960, 600), Image.LANCZOS))
    boot = Image.new("RGB", (w, h), (8, 8, 10))
    d = ImageDraw.Draw(boot)
    for k in range(12):                                    # a spinner while it wakes
        a = 2 * math.pi * k / 12
        d.ellipse([w / 2 + 50 * math.cos(a) - 7, h / 2 + 50 * math.sin(a) - 7, w / 2 + 50 * math.cos(a) + 7,
                   h / 2 + 50 * math.sin(a) + 7], fill=shade((230, 230, 240), -k / 14))
    put(atlas, "steam", "boot", boot)


def openbor(atlas, made_up):
    """OpenBOR's drum (props.py): its painting, wrapped round it, at 1024 wide."""
    drum = painting("openbor_drum").convert("RGB")
    return drum.resize((L.MEDIA_SIZE, round(L.MEDIA_SIZE * drum.height / drum.width)), Image.LANCZOS)


CARDS = dict(tic80=tic80, wasm4=wasm4, lowresnx=lowresnx, vircon32=vircon32, fpinball=fpinball, vpinball=vpinball,
             zmachine=zmachine, steam=steam, openbor=openbor)


def main(card, made_up, out):
    os.makedirs(out, exist_ok=True)
    atlas = Image.new("RGB", (L.MEDIA_SIZE, L.MEDIA_SIZE), (0, 0, 0))
    atlas = CARDS[card](atlas, made_up) or atlas
    path = os.path.join(out, L.media_file(card))
    if path.endswith(".jpg"):
        atlas.save(path, quality=90, optimize=True)
    else:
        atlas.save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]))
