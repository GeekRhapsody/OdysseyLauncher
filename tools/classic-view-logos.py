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
UK English variant). Localised variants (auto-favorites-de, ...) are ignored. When a name has both an SVG and a PNG,
the SVG wins. Logos still drawn mostly in dark colours are listed, to check on the card.

Needs Pillow and ImageMagick (magick) with its librsvg delegate. Run from the repo root:

    python tools/classic-view-logos.py [--sources=system_logos_all,system_logos]

It takes a few minutes: WebP's slowest, smallest compression (method 6).
"""

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
# and Batocera's names for systems whose id differs.
NAMES = {
    'favourites': ['auto-favorites-engb', 'auto-favorites'],
    'recently_played': ['auto-lastplayed'],
    'all_games': ['auto-allgames'],
    'atarixe': ['atari8bit'],
    'cdimono1': ['cdi'],
    'cdtv': ['amigacdtv'],
    'n3ds': ['3ds'],
    'naomigd': ['naomi'],
    'type-x': ['typex'],
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
    for name in os.listdir(source):
        stem, ext = os.path.splitext(name)
        if ext.lower() in ('.svg', '.png') and (stem not in files or ext.lower() == '.svg'):
            files[stem] = os.path.join(source, name)
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

print(f'{len(jobs)} logos written to {TARGET} ({after / 1e6:.1f} MB)')
missing = sorted(ids - set(jobs))
if missing:
    print('built-in systems without a logo:', ', '.join(missing))
if dark:
    print(f'mostly dark logos (mean luma under {DARK_LUMA}):', ', '.join(dark))
