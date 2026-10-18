"""Draws the slot-showcase test theme's wallpapers (docs/ARCHITECTURE.md A6, Background), the same on every run.

  python tools/test-wallpapers/make_test_wallpapers.py [--out=<folder>]

Writes into tests/themes/slot-showcase/wallpapers/ (or --out):
  grid.webp  1920x1080, opaque: a dark perspective grid with fine lines, so a seam where an item fades into the
             wallpaper shows in a capture.
  ps2.png    1920x1080 with transparency: the four face-button shapes scattered over nothing, so the system's gradient
             shows through, and an item fading out must match both.
Needs Pillow.
"""

import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

WIDTH, HEIGHT = 1920, 1080
ROOT = Path(__file__).resolve().parents[2]


def grid() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (10, 8, 18))
    draw = ImageDraw.Draw(image)
    horizon = HEIGHT * 0.42
    # Rows recede towards the horizon; columns fan out from its centre.
    for i in range(1, 40):
        y = horizon + (HEIGHT - horizon) * (i / 40) ** 2
        shade = int(30 + 90 * (i / 40))
        draw.line([(0, y), (WIDTH, y)], fill=(shade, shade // 3, shade), width=2)
    for i in range(-30, 31):
        x = WIDTH / 2 + i * 120
        draw.line([(WIDTH / 2 + i * 6, horizon), (x, HEIGHT)], fill=(40, 90, 120), width=2)
    # A sky of fine stars above it.
    rng = random.Random(7)
    for _ in range(900):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, horizon - 4)
        level = rng.randint(70, 220)
        draw.point((x, y), fill=(level, level, min(255, level + 30)))
    # A soft glow along the horizon.
    glow = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(glow).rectangle([0, horizon - 6, WIDTH, horizon + 6], fill=200)
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    image = Image.composite(Image.new("RGB", (WIDTH, HEIGHT), (190, 60, 150)), image, glow.point(lambda v: v // 2))
    return image


def ps2() -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    rng = random.Random(2)
    colours = [(80, 200, 160, 150), (230, 90, 90, 150), (110, 140, 240, 150), (220, 120, 200, 150)]
    for n in range(70):
        kind = n % 4
        size = rng.uniform(30, 110)
        cx, cy = rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT)
        width = max(3, int(size / 9))
        colour = colours[kind]
        if kind == 0:  # triangle
            points = [(cx + size * math.cos(a), cy + size * math.sin(a)) for a in (-math.pi / 2, math.pi / 6, 5 * math.pi / 6)]
            draw.polygon(points, outline=colour, width=width)
        elif kind == 1:  # circle
            draw.ellipse([cx - size, cy - size, cx + size, cy + size], outline=colour, width=width)
        elif kind == 2:  # cross
            draw.line([(cx - size, cy - size), (cx + size, cy + size)], fill=colour, width=width)
            draw.line([(cx - size, cy + size), (cx + size, cy - size)], fill=colour, width=width)
        else:  # square
            draw.rectangle([cx - size * 0.8, cy - size * 0.8, cx + size * 0.8, cy + size * 0.8], outline=colour, width=width)
    return image


def main() -> None:
    out = ROOT / "tests" / "themes" / "slot-showcase" / "wallpapers"
    for arg in sys.argv[1:]:
        if arg.startswith("--out="):
            out = Path(arg[len("--out="):])
        else:
            sys.exit(f"Unknown argument: {arg}")
    out.mkdir(parents=True, exist_ok=True)
    grid().save(out / "grid.webp", quality=85, method=6)
    ps2().save(out / "ps2.png", optimize=True)
    for name in ("grid.webp", "ps2.png"):
        print(f"{out / name}: {(out / name).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
