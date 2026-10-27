"""The LCD games card's printing and screens (lcdgames_print.png, lcdgames_media.png), for the console theme's LCD games
model (lcdgames.py).

`lcdgames_print.png`, laid out as lcdgames_layout.REGIONS says, each region in millimetres as the model's UVs map it:
the face (the white rim; the art panel under its clear plastic, a made-up game's painting and logo from
tools/made-up-games; the LCD's printed backdrop, a road in three lanes, as it looks switched off; the green strip with
OFF, SOUND, PAUSE, ON/START and ACL) and swatches. `lcdgames_media.png`: the LCD switched on, four moments of the game:
its black segment figures (the player's car in one of the three lanes, the rivals coming down the road, the score in
seven-segment digits) over the backdrop. Make the made-up games' library first (tools/made-up-games/README.md), then run
it with the system Python (Pillow):

    python tools/console-models/lcdgames_print.py artifacts/made-up-games <out folder>
"""

import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lcdgames_layout as L  # noqa: E402
import screens_print as S  # noqa: E402
from retro_pc_print import rgb  # noqa: E402
from windows_pc_print import Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
PX = 8                        # the LCD's pixels a millimetre


def backdrop():
    """The LCD's printed backdrop: a sky, the verges, the road narrowing into the distance in three lanes."""
    w, h = (round(v * PX) for v in L.LCD["size"])
    img = Image.new("RGB", (w, h), C["lcd"])
    d = ImageDraw.Draw(img)
    horizon = h * 0.28
    d.rectangle([0, 0, w, horizon], fill=(214, 196, 150))
    d.polygon([(0, horizon), (w, horizon), (w, h), (0, h)], fill=(160, 178, 140))
    d.polygon([(w * 0.42, horizon), (w * 0.58, horizon), (w * 0.98, h), (w * 0.02, h)], fill=(176, 180, 170))
    for k in (1, 2):
        top = w * 0.42 + w * 0.16 * k / 3
        bottom = w * 0.02 + w * 0.96 * k / 3
        for j in range(8):
            t0, t1 = j / 8 + 0.02, j / 8 + 0.08
            d.line([(top + (bottom - top) * t0, horizon + (h - horizon) * t0),
                    (top + (bottom - top) * t1, horizon + (h - horizon) * t1)], fill=(220, 222, 214), width=3)
    return img


def car(d, cx, cy, s, ink):
    """A car's segment figure from behind, s its width."""
    d.rounded_rectangle([cx - s / 2, cy - s * 0.35, cx + s / 2, cy + s * 0.25], radius=s * 0.08, fill=ink)
    d.rectangle([cx - s * 0.32, cy - s * 0.62, cx + s * 0.32, cy - s * 0.3], fill=ink)
    for side in (-1, 1):
        d.rectangle([cx + side * s * 0.5 - s * 0.08, cy + s * 0.1, cx + side * s * 0.5 + s * 0.08, cy + s * 0.42],
                    fill=ink)


SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
        "8": "abcdefg", "9": "abcdfg"}


def digit(d, x, y, s, ch, ink):
    """A seven-segment digit, s its height."""
    w, t = s * 0.55, s * 0.12
    bars = dict(a=(x, y, x + w, y + t), b=(x + w - t, y, x + w, y + s / 2), c=(x + w - t, y + s / 2, x + w, y + s),
                d=(x, y + s - t, x + w, y + s), e=(x, y + s / 2, x + t, y + s), f=(x, y, x + t, y + s / 2),
                g=(x, y + s / 2 - t / 2, x + w, y + s / 2 + t / 2))
    for seg in SEGS[ch]:
        d.rectangle(bars[seg], fill=ink)


def lit(lane, rivals, score):
    """The LCD switched on: the player's car in its lane, the rivals (lane, how far down), the score."""
    img = backdrop()
    d = ImageDraw.Draw(img)
    w, h = img.size
    horizon = h * 0.28
    ink = C["segment"]

    def lane_x(k, t):
        top = w * 0.42 + w * 0.16 * (k + 0.5) / 3
        bottom = w * 0.02 + w * 0.96 * (k + 0.5) / 3
        return top + (bottom - top) * t
    car(d, lane_x(lane, 0.86), horizon + (h - horizon) * 0.86, w * 0.2, ink)
    for k, t in rivals:
        car(d, lane_x(k, t), horizon + (h - horizon) * t, w * 0.2 * (0.35 + 0.65 * t), ink)
    for i, ch in enumerate(score):
        digit(d, w - 4 * 26 - 10 + 26 * i, 10, 34, ch, ink)
    return img


def face(game):
    x0, x1, z0, z1 = L.SPAN
    reg = Region(L.REGIONS["face"], x1 - x0, z1 - z0, C["shell"])

    def at(x, z):
        return x - x0, z1 - z

    panel = [at(x, z) for x, z in L.PANEL]
    xs, ys = [p[0] for p in panel], [p[1] for p in panel]
    a, b, c, d = reg.box(min(xs), min(ys), max(xs), max(ys))
    art = ImageOps.fit(game.keyart, (round(c - a), round(d - b)), Image.LANCZOS, centering=(0.5, 0.45))
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).polygon([(reg.p(*p)[0] - a, reg.p(*p)[1] - b) for p in panel], fill=255)
    reg.img.paste(art, (round(a), round(b)), mask)
    k = min((c - a) * 0.36 / game.logo.width, (d - b) * 0.3 / game.logo.height)
    logo = game.logo.resize((round(game.logo.width * k), round(game.logo.height * k)), Image.LANCZOS)
    reg.img.alpha_composite(logo, (round(a + 2.0 * reg.sx), round(b + 1.5 * reg.sy)))
    (lw, lh), (lx, lz) = L.LCD["size"], L.LCD["at"]
    reg.rect_(*at(lx - lw / 2 - 1.2, lz + lh / 2 + 1.2), *at(lx + lw / 2 + 1.2, lz - lh / 2 - 1.2), (30, 30, 34), r=1.0)
    bx, by, _, _ = reg.box(*at(lx - lw / 2, lz + lh / 2), *at(lx + lw / 2, lz - lh / 2))
    reg.img.paste(backdrop().resize((round(lw * reg.sx), round(lh * reg.sy)), Image.LANCZOS), (round(bx), round(by)))
    sx0, sx1 = L.STRIP["x"]
    z = L.STRIP["z"]
    reg.rect_(*at(sx0, z + L.STRIP["height"] / 2), *at(sx1, z - L.STRIP["height"] / 2), C["strip"], r=2.0)
    for name, x in L.SMALL["names"]:
        reg.text(name, "arialbd.ttf", 1.7, *at(x, z + 3.2), C["white"])
    reg.text("ACL", "arialbd.ttf", 1.7, *at(L.SMALL["acl"], z + 3.2), C["white"])
    reg.circle(*at(L.SMALL["acl"], z - 0.4), 0.8, (10, 10, 10))
    return reg


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    game = S.made_up(*L.MADE_UP, made_up)
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), C["shell"])
    face(game).paste(image)
    d = ImageDraw.Draw(image)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=C[name])
    image.save(os.path.join(out, "lcdgames_print.png"), optimize=True)
    frames = dict(seg1=lit(1, [(0, 0.2), (2, 0.55)], "0120"), seg2=lit(0, [(0, 0.45), (2, 0.85)], "0130"),
                  seg3=lit(0, [(1, 0.2), (0, 0.7)], "0140"), seg4=lit(1, [(1, 0.5), (2, 0.15)], "0150"))
    media = Image.new("RGB", (L.ATLAS, L.ATLAS), C["lcd"])
    for name, img in frames.items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        media.paste(img.resize((w, h), Image.LANCZOS), (x, y))
    media.save(os.path.join(out, "lcdgames_media.png"), optimize=True)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
