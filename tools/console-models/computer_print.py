"""The computer cards' printing and screens (<card>_print.png, <card>_media.png), for the console theme's computer cards
(computer.py), each from its `<card>_layout.py` (computer_layout.py says what one holds).

`<card>_print.png`: the blocks' printed faces (their drawing items over their colour), the keys' tops (each key's colour
inset by its taper, its legend), the display's front, the media's label, packed by computer_layout.pack(), and the
swatches along the foot. `<card>_media.png`: the screens, each a cell of the media atlas: the machine at rest (`boot`),
its loading screen, the made-up game's title (tools/made-up-games) and two moments of it, at the machine's resolution
and in its palette, in its border. Make the made-up games' library first (tools/made-up-games/README.md), then run it
with the system Python (Pillow, numpy, scipy):

    python tools/console-models/computer_print.py <card> artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import computer_layout as C  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

SPEC = None
GAME = None


def colour(value):
    if isinstance(value, tuple):
        return value
    return rgb(SPEC.COLOURS.get(value, value))


def draw(reg, items):
    """A face's drawing items (computer_layout.py's docstring lists them)."""
    for item in items:
        kind = item[0]
        if kind == "rect":
            reg.rect_(*item[1:5], colour(item[5]), r=item[6] if len(item) > 6 else 0.0)
        elif kind == "frame":
            reg.rect_(*item[1:5], None, r=item[7] if len(item) > 7 else 0.0, outline=colour(item[5]), width=item[6])
        elif kind == "text":
            _, s, font, size, a, b, c = item[:7]
            reg.text(s, font, size, a, b, colour(c), anchor=item[7] if len(item) > 7 else "mm")
        elif kind == "circle":
            reg.circle(item[1], item[2], item[3], colour(item[4]))
        elif kind in ("slots", "hslots"):
            _, a0, b0, a1, b1, n, c = item
            for k in range(n):
                if kind == "slots":
                    step = (a1 - a0) / n
                    reg.rect_(a0 + step * k + step * 0.25, b0, a0 + step * k + step * 0.75, b1, colour(c), r=step * 0.2)
                else:
                    step = (b1 - b0) / n
                    reg.rect_(a0, b0 + step * k + step * 0.25, a1, b0 + step * k + step * 0.75, colour(c), r=step * 0.2)
        elif kind == "dots":
            _, a0, b0, a1, b1, cols, rows, r, c = item
            for i in range(cols):
                for j in range(rows):
                    reg.circle(a0 + (a1 - a0) * (i + 0.5) / cols, b0 + (b1 - b0) * (j + 0.5) / rows, r, colour(c))
        elif kind == "line":
            reg.line(item[1], colour(item[2]), item[3])
        elif kind in ("cover", "logo"):
            _, a0, b0, a1, b1 = item
            x0, y0, x1, y1 = reg.box(a0, b0, a1, b1)
            w, h = round(x1 - x0), round(y1 - y0)
            if kind == "cover":
                reg.img.paste(ImageOps.fit(GAME.keyart, (w, h), Image.LANCZOS, centering=(0.5, 0.4)),
                              (round(x0), round(y0)))
                k = min(w * 0.86 / GAME.logo.width, h * 0.34 / GAME.logo.height)
                logo = GAME.logo.resize((round(GAME.logo.width * k), round(GAME.logo.height * k)), Image.LANCZOS)
                reg.img.alpha_composite(logo, (round(x0 + (w - logo.width) / 2), round(y0 + h * 0.05)))
            else:
                k = min(w / GAME.logo.width, h / GAME.logo.height)
                logo = GAME.logo.resize((round(GAME.logo.width * k), round(GAME.logo.height * k)), Image.LANCZOS)
                reg.img.alpha_composite(logo, (round(x0 + (w - logo.width) / 2), round(y0 + (h - logo.height) / 2)))


def keys(reg):
    kb = SPEC.KEYBOARD
    ex0, ex1, es0, es1 = C.keys_extent(kb)
    t = kb["taper"]
    ink = colour(kb.get("ink", "#1E1E1E"))
    for legend, x0, x1, s0, s1, c in C.key_rects(kb):
        a0, a1, b0, b1 = x0 - ex0, x1 - ex0, es1 - s1, es1 - s0
        reg.rect_(a0, b0, a1, b1, shade(colour(c), -0.12), r=1.2)
        reg.rect_(a0 + t, b0 + t, a1 - t, b1 - t, colour(c), r=1.0)
        lines = legend.split("\n") if legend else []
        ink_here = colour(kb.get("inks", {}).get(c, ink)) if kb.get("inks") else ink
        size = kb.get("legend", 3.0)
        for k, line in enumerate(lines):
            font = "seguisym.ttf" if not line.isascii() else "arialbd.ttf" if len(line) > 1 else "arial.ttf"
            s = size * (0.8 if len(line) > 3 else 1.0)
            reg.text(line, font, s, (a0 + a1) / 2, (b0 + b1) / 2 + (k - (len(lines) - 1) / 2) * (s + 0.8), ink_here)


def print_atlas(out):
    regions = C.pack(SPEC)
    image = Image.new("RGB", (C.PRINT_ATLAS, C.PRINT_ATLAS), colour("case"))

    def region(name, w, h, background):
        return Region(regions[name], w, h, background)
    for k, block in enumerate(SPEC.BLOCKS):
        b = C.bounds(block["shape"])
        for face in C.FACES:
            items = block.get("faces", {}).get(face)
            if items:
                reg = region(f"b{k}_{face}", *C.face_size(b, face), colour(block.get("colour", "case")))
                draw(reg, items)
                reg.paste(image)
    for k, mover in enumerate(getattr(SPEC, "MOVERS", ())):
        b = C.bounds(mover["shape"])
        for face in C.FACES:
            items = mover.get("faces", {}).get(face)
            if items:
                reg = region(f"m{k}_{face}", *C.face_size(b, face), colour(mover.get("colour", "case")))
                draw(reg, items)
                reg.paste(image)
    kb = getattr(SPEC, "KEYBOARD", None)
    if kb:
        x0, x1, s0, s1 = C.keys_extent(kb)
        reg = region("keys", x1 - x0, s1 - s0, colour(kb.get("ground", "case")))
        keys(reg)
        reg.paste(image)
    d = getattr(SPEC, "DISPLAY", None)
    if d and d.get("faces", {}).get("front"):
        reg = region("display_front", d["size"][0], d["size"][1], colour(d.get("colour", "case")))
        draw(reg, d["faces"]["front"])
        reg.paste(image)
    media = getattr(SPEC, "MEDIA", None)
    if media and media.get("label"):
        reg = region("label", media["size"][0], media["size"][1], colour(media.get("colour", "case")))
        draw(reg, media["label"])
        reg.paste(image)
    dr = ImageDraw.Draw(image)
    for name, (x, y) in C.swatches(SPEC).items():
        dr.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour(name))
    path = os.path.join(out, f"{SPEC.__name__.replace('_layout', '')}_print.png")
    image.save(path, optimize=True)
    print(path)


# ---- The screens -----------------------------------------------------------------------------------------------------

def framed(img):
    """A native screen in the machine's border, the border's share of the glass the spec's fraction."""
    sc = SPEC.SCREEN
    border, frac = sc.get("border", ("#000000", 0.08))
    w, h = img.size
    bw, bh = round(w * (1 + 2 * frac)), round(h * (1 + 2 * frac))
    out = Image.new("RGB", (bw, bh), colour(border))
    out.paste(img, ((bw - w) // 2, (bh - h) // 2))
    return out


def native(img):
    palette = SPEC.SCREEN.get("palette")
    return S.native(img, SPEC.SCREEN["px"], palette)


def screens():
    sc = SPEC.SCREEN
    px = sc["px"]
    ink, paper = colour(sc["ink"]), colour(sc["paper"])
    boot = S.text_screen(px, sc["boot"], ink, paper, col=sc.get("col", 0), row=sc.get("row", 0))
    load = S.text_screen(px, sc["load"], ink, paper, col=sc.get("col", 0), row=sc.get("row", 0))
    title = S.title(GAME, px, palette=sc.get("palette"), prompt=sc.get("prompt", "PRESS SPACE"),
                    ink=colour(sc.get("title_ink", "#FFFFFF")))
    game1, game2 = S.play(GAME, px, palette=sc.get("palette"))
    return dict(boot=boot, load=load, title=title, game1=game1, game2=game2)


def media_atlas(out):
    image = Image.new("RGB", (C.MEDIA_ATLAS, C.MEDIA_ATLAS), (0, 0, 0))
    cells = C.media_regions()
    for name, img in screens().items():
        x, y, w, h = cells[name]
        image.paste(framed(img.convert("RGB")).resize((w, h), Image.LANCZOS), (x, y))
    path = os.path.join(out, f"{SPEC.__name__.replace('_layout', '')}_media.png")
    image.save(path, optimize=True)
    print(path)


def main(card, made_up, out):
    global SPEC, GAME
    os.makedirs(out, exist_ok=True)
    SPEC = C.load(card)
    GAME = S.made_up(*SPEC.SCREEN["game"], made_up)
    print_atlas(out)
    media_atlas(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
