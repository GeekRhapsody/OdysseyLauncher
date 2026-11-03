"""Prepares the Classic View theme's logos (godot/themes/classic-view/logos/) from Batocera's Carbon theme's system
logos (https://github.com/fabricecaruso/es-theme-carbon, CC BY-NC-SA), in two untracked folders at the repo root:
system_logos_all/ (Carbon's whole set, by Batocera's names) and system_logos/ (a smaller set by ES-DE's names, for the
few the first lacks).

Carbon draws its logos for a light background; the card is dark grey, so a logo's "-w" variant (ps4-w.svg, drawn for
a dark one) is taken whenever there is one. A few systems are found by Batocera's name for them (NAMES).

The source is mostly SVG, which the launcher can't read, so each SVG is rendered with ImageMagick's librsvg first, its
longer side about 1024 pixels. Then, as tools/slab-logos.py does, each image is cropped to what it shows (its
transparent border cut off, with a small margin), so the launcher fits the logo itself to the card, and scaled down to
at most 512 pixels on its longer side, the size the launcher bakes every image to (TextureDerivatives.Size).

Only the images of built-in systems are kept (systems.toml), plus the virtual cards' (renamed: Favourites from the
UK English variant). Localised variants (auto-favorites-de, ...) are ignored. A regional variant Carbon has no logo for
can have another system's in other colours (DERIVED): Dreamcast (NA/JP)'s is the Dreamcast's with an orange swirl. When a name has both an SVG and a PNG,
the SVG wins. Logos still drawn mostly in dark colours are listed, to check on the card.

Needs Pillow and ImageMagick (magick) with its librsvg delegate. Run from the repo root:

    python tools/classic-view-logos.py [--sources=system_logos_all,system_logos]

It takes a few minutes: WebP's slowest, smallest compression (method 6).
"""

import colorsys
import io
import os
import re
import subprocess
import sys

from PIL import Image

SOURCES = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--sources=')),
               'system_logos_all,system_logos').split(',')
TARGET = 'godot/themes/classic-view/logos'
# The names a card's logo is looked for by, after its own id, in order: the virtual cards' (Favourites in UK English),
# and Batocera's names for systems whose id differs. A name with a folder is in that subfolder of a source: Carbon's
# regional logos (jp/, us/, br/), for a regional variant whose region Carbon draws its own way.
NAMES = {
    'favourites': ['auto-favorites-engb', 'auto-favorites'],
    'recently_played': ['auto-lastplayed'],
    'all_games': ['auto-allgames'],
    'atarixe': ['atari8bit'],
    'cdimono1': ['cdi'],
    'cdtv': ['amigacdtv'],
    'n3ds': ['3ds'],
    'megacdjp': ['jp/megacd'],
    'naomigd': ['naomi'],
    'type-x': ['typex'],
}
# Cards whose logo is another card's with its coloured parts (not its white lettering) turned to another colour, as
# (the other card, the hue in degrees, the saturation and the brightness its commonest coloured pixel takes): Dreamcast
# (NA/JP), a regional variant, has the Dreamcast's logo with the North American and Japanese orange swirl for Carbon's
# PAL blue.
DERIVED = {
    'dreamcastnajp': ('dreamcast', 22, 0.85, 0.92),
}
RENDER_SIDE = 1024     # an SVG's longer side once rendered, before the crop
MAX_SIDE = 512
MARGIN = 0.02          # of the cropped picture's longer side, so soft edges and shadows aren't cut
ALPHA_THRESHOLD = 4    # alpha at or below this counts as empty
DARK_LUMA = 60         # a logo whose opaque pixels average darker than this (0-255) is listed


def svg_size(path):
    """The SVG's width and height in its own units (its width and height attributes, else its viewBox)."""
    head = open(path, encoding='utf-8', errors='replace').read(4096)
    tag = re.search(r'<svg\b[^>]*>', head, re.S)
    text = tag.group(0) if tag else ''

    def number(name):
        m = re.search(r'\b' + name + r'\s*=\s*["\']\s*([0-9.]+)\s*(px)?\s*["\']', text)
        return float(m.group(1)) if m else None

    width, height = number('width'), number('height')
    if not (width and height):
        box = re.search(r'viewBox\s*=\s*["\']\s*[-0-9.]+[\s,]+[-0-9.]+[\s,]+([0-9.]+)[\s,]+([0-9.]+)', text)
        if box:
            width, height = float(box.group(1)), float(box.group(2))
    return (width, height) if width and height else (512.0, 512.0)


def load(path):
    if path.lower().endswith('.svg'):
        density = 96 * RENDER_SIDE / max(svg_size(path))
        png = subprocess.run(['magick', '-background', 'none', '-density', f'{density:.2f}', f'svg:{path}', 'png:-'],
                             check=True, capture_output=True).stdout
        return Image.open(io.BytesIO(png)).convert('RGBA')
    return Image.open(path).convert('RGBA')


def recolour(image, hue, saturation, value):
    """
    The image with its coloured pixels (saturation over a third) turned to the hue, at the saturation, and brightened or
    darkened by what takes their commonest brightness to value, so the colour's shading stays.
    """
    data = image.tobytes()
    pixels = [tuple(data[i:i + 4]) for i in range(0, len(data), 4)]
    hsv = [colorsys.rgb_to_hsv(r / 255, g / 255, b / 255) for r, g, b, _ in pixels]
    coloured = sorted(round(v, 2) for (_, s, v), (*_, a) in zip(hsv, pixels) if s > 1 / 3 and a > ALPHA_THRESHOLD)
    scale = value / coloured[len(coloured) // 2] if coloured else 1.0
    out = bytearray()
    for (h, s, v), (r, g, b, a) in zip(hsv, pixels):
        if s > 1 / 3:
            r, g, b = (round(c * 255) for c in colorsys.hsv_to_rgb(hue / 360, saturation, min(1.0, v * scale)))
        out += bytes((r, g, b, a))
    return Image.frombytes('RGBA', image.size, bytes(out))


def mean_luma(image):
    """The average luma of the opaque pixels, weighted by their alpha."""
    small = image.copy()
    small.thumbnail((128, 128))
    total = weight = 0.0
    data = small.tobytes()
    for i in range(0, len(data), 4):
        r, g, b, a = data[i:i + 4]
        if a > ALPHA_THRESHOLD:
            total += (0.2126 * r + 0.7152 * g + 0.0722 * b) * a
            weight += a
    return total / weight if weight else 255


toml = open('src/Launcher.Core/Defaults/systems.toml', encoding='utf-8').read()
ids = set(re.findall(r'^\[systems\.([A-Za-z0-9_-]+)\]', toml, re.M))

# Each source folder's images by name (an SVG over a PNG of the same name).
folders = []
for source in SOURCES:
    files = {}
    for sub in ('', 'jp', 'us', 'br'):
        folder = os.path.join(source, sub)
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            stem, ext = os.path.splitext(name)
            stem = f'{sub}/{stem}' if sub else stem
            if ext.lower() in ('.svg', '.png') and (stem not in files or ext.lower() == '.svg'):
                files[stem] = os.path.join(folder, name)
    folders.append(files)


def find(card):
    """The card's image: the first source folder with one, its "-w" variant first."""
    names = [card] + NAMES.get(card, [])
    for files in folders:
        for name in names:
            for stem in (name + '-w', name):
                if stem in files:
                    return files[stem]
    return None


jobs = {card: path for card in sorted(ids | {'favourites', 'recently_played', 'all_games'}) if (path := find(card))}

os.makedirs(TARGET, exist_ok=True)
for name in os.listdir(TARGET):
    os.remove(os.path.join(TARGET, name))

dark, after = [], 0
for target, name in sorted(jobs.items()):
    image = load(name)
    box = image.getchannel('A').point(lambda a: 255 if a > ALPHA_THRESHOLD else 0).getbbox() or (0, 0, *image.size)
    pad = round(max(box[2] - box[0], box[3] - box[1]) * MARGIN)
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(image.width, box[2] + pad), min(image.height, box[3] + pad))
    cropped = image.crop(box)
    scale = min(1.0, MAX_SIDE / max(cropped.size))
    if scale < 1:
        cropped = cropped.resize((round(cropped.width * scale), round(cropped.height * scale)), Image.LANCZOS)

    out = os.path.join(TARGET, target + '.webp')
    cropped.save(out, 'WEBP', quality=92, alpha_quality=100, method=6)
    after += os.path.getsize(out)
    luma = mean_luma(cropped)
    if luma < DARK_LUMA:
        dark.append(f'{target} ({luma:.0f})')

derived = []
for target, (card, hue, saturation, value) in DERIVED.items():
    if target in ids and card in jobs:
        out = os.path.join(TARGET, target + '.webp')
        recolour(Image.open(os.path.join(TARGET, card + '.webp')).convert('RGBA'), hue, saturation, value) \
            .save(out, 'WEBP', quality=92, alpha_quality=100, method=6)
        after += os.path.getsize(out)
        derived.append(target)

print(f'{len(jobs) + len(derived)} logos written to {TARGET} ({after / 1e6:.1f} MB), {len(derived)} derived from another')
missing = sorted(ids - set(jobs) - set(derived))
if missing:
    print('built-in systems without a logo:', ', '.join(missing))
if dark:
    print(f'mostly dark logos (mean luma under {DARK_LUMA}):', ', '.join(dark))
