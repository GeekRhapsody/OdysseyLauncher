"""Prepares the Slab theme's logos (godot/themes/slab/logos/) from the owner's ES-DE images (slab_images/, untracked).

Each image is cropped to what it shows (its transparent border cut off, with a small margin), so the launcher fits the
picture itself to the card rather than a mostly empty square, and scaled down to at most 512 pixels on its longer side,
the size the launcher bakes every image to (TextureDerivatives.Size): anything larger is decoded only to be shrunk.

Only the images of built-in systems are kept (systems.toml), plus the virtual cards' (renamed), and astrocade, which the
theme assigns to astrocde. Needs Pillow. Run from the repo root:

    python tools/slab-logos.py [--source=slab_images]

It takes about ten minutes: WebP's slowest, smallest compression (method 6).
"""

import os
import re
import sys

from PIL import Image

SOURCE = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--source=')), 'slab_images')
TARGET = 'godot/themes/slab/logos'
RENAMES = {'auto-favorites': 'favourites', 'auto-lastplayed': 'recently_played'}
EXTRA = {'astrocade'}  # [systems.astrocde] logo = "logos/astrocade.webp"
MAX_SIDE = 512
MARGIN = 0.02          # of the cropped picture's longer side, so soft edges and shadows aren't cut
ALPHA_THRESHOLD = 4    # alpha at or below this counts as empty

toml = open('src/Launcher.Core/Defaults/systems.toml', encoding='utf-8').read()
ids = set(re.findall(r'^\[systems\.([A-Za-z0-9_-]+)\]', toml, re.M))

os.makedirs(TARGET, exist_ok=True)
for name in os.listdir(TARGET):
    os.remove(os.path.join(TARGET, name))

kept, skipped, before, after = 0, [], 0, 0
for name in sorted(os.listdir(SOURCE)):
    stem, _ = os.path.splitext(name)
    if stem not in ids and stem not in RENAMES and stem not in EXTRA:
        skipped.append(stem)
        continue

    image = Image.open(os.path.join(SOURCE, name)).convert('RGBA')
    box = image.getchannel('A').point(lambda a: 255 if a > ALPHA_THRESHOLD else 0).getbbox() or (0, 0, *image.size)
    pad = round(max(box[2] - box[0], box[3] - box[1]) * MARGIN)
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(image.width, box[2] + pad), min(image.height, box[3] + pad))
    cropped = image.crop(box)
    scale = min(1.0, MAX_SIDE / max(cropped.size))
    if scale < 1:
        cropped = cropped.resize((round(cropped.width * scale), round(cropped.height * scale)), Image.LANCZOS)

    out = os.path.join(TARGET, RENAMES.get(stem, stem) + '.webp')
    cropped.save(out, 'WEBP', quality=92, alpha_quality=100, method=6)
    before += os.path.getsize(os.path.join(SOURCE, name))
    after += os.path.getsize(out)
    kept += 1

print(f'{kept} logos written to {TARGET} ({before / 1e6:.1f} MB of source, {after / 1e6:.1f} MB written); '
      f'{len(skipped)} skipped (no built-in system): {", ".join(skipped)}')
missing = sorted(ids - {os.path.splitext(n)[0] for n in os.listdir(TARGET)} - {'astrocde'})
if missing:
    print('built-in systems without a logo:', ', '.join(missing))
