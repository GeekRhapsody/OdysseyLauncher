"""Draws the launcher's icon: an isometric cube with a tilted ring round it (the owner's choice, 2026-10-20), on a dark
rounded square in the boot splash's navy. It writes:

    godot/icon.svg    the master, 256 units square: the editor's and Godot's window icon (config/icon)
    godot/icon.ico    every Windows size, for the window and taskbar (config/windows_native_icon), the exported
                      OdysseyLauncher.exe (the export preset's application/icon) and OdysseyUpdater.exe (ApplicationIcon)

Every size is drawn from the same shapes, not scaled down from the master: below 48 pixels the ring and its cut are
thicker, the tile fills more of the square and loses its gradient, so the cube and the ring stay apart at 16 pixels.
The ring's back half is drawn before the cube and its front half after it, over a cut in the background's colour, so
it passes behind the cube and in front of it.

Needs Pillow and ImageMagick (magick) with its librsvg delegate. Deterministic. Run from the repo root:

    python tools/app-icon/make_icon.py [--preview=<folder>]

--preview writes preview.png to that folder: every size at 1x and 4x (nearest neighbour), on the dark and light
backgrounds of Windows' taskbar, for checking it's readable. The renders go to artifacts/app-icon/.
"""

import io
import os
import struct
import subprocess
import sys

from PIL import Image

SVG_OUT = 'godot/icon.svg'
ICO_OUT = 'godot/icon.ico'
WORK = 'artifacts/app-icon'
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

TILE_TOP = '#15152B'
TILE_BOTTOM = '#04040C'    # the boot splash's colour (project.godot)
TILE_FLAT = '#0C0C1C'      # small sizes: no gradient
FACE_TOP = '#E8E8F0'       # lit as icon.sys lights a card: the top brightest, the right darkest
RING_BACK = '#2A86A8'      # the half behind the cube, darker
RING_FRONT = '#4CC9F0'

CENTRE = (128, 134)        # the cube's
RING_RX, RING_RY, RING_TILT = 104, 30, -16


def params(size):
    """How the shapes change with the size they're drawn at, in units of the 256 square."""
    if size >= 48:
        return dict(inset=8, radius=48, edge=58, lift=16, ring=14, cut=24, gradient=True,
                    left='#9A9AB0', right='#5C5C78')
    # Small: the tile almost to the edge, a bigger cube lower in the ring, the ring at least 1.5 pixels wide with half a
    # pixel of cut either side, and lighter sides, so the cube still shows at 16 pixels.
    px = 256 / size        # units per pixel
    ring = max(14, 1.5 * px)
    return dict(inset=px * 0.5, radius=40, edge=68, lift=26, ring=ring, cut=ring + px, gradient=False,
                left='#B4B4C8', right='#7E7E9C')


def svg(size):
    p = params(size)
    inset, radius, edge, ring, gradient = p['inset'], p['radius'], p['edge'], p['ring'], p['gradient']
    cx, cy = CENTRE
    w = edge * 3 ** 0.5 / 2
    top, ur, lr = (cx, cy - edge), (cx + w, cy - edge / 2), (cx + w, cy + edge / 2)
    bottom, ll, ul = (cx, cy + edge), (cx - w, cy + edge / 2), (cx - w, cy - edge / 2)
    centre = (cx, cy)

    def poly(points, fill):
        return f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in points)}" fill="{fill}"/>'

    # In the ring's own frame (y down), left to right through the top is clockwise: sweep 1.
    back = f'M {-RING_RX} 0 A {RING_RX} {RING_RY} 0 0 1 {RING_RX} 0'
    front = f'M {RING_RX} 0 A {RING_RX} {RING_RY} 0 0 1 {-RING_RX} 0'
    ring_frame = f'translate({cx} {cy - p['lift']}) rotate({RING_TILT})'
    side = 256 - 2 * inset
    cut = p['cut']
    fill = 'url(#tile)' if gradient else TILE_FLAT
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 256 256">',
        '<defs><linearGradient id="tile" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{TILE_TOP}"/><stop offset="1" stop-color="{TILE_BOTTOM}"/>'
        '</linearGradient></defs>' if gradient else '',
        f'<rect x="{inset:.2f}" y="{inset:.2f}" width="{side:.2f}" height="{side:.2f}" rx="{radius}" fill="{fill}"/>',
        f'<g transform="{ring_frame}" fill="none" stroke-linecap="round">'
        f'<path d="{back}" stroke="{RING_BACK}" stroke-width="{ring:.2f}"/></g>',
        poly([top, ur, centre, ul], FACE_TOP),
        poly([ul, centre, bottom, ll], p['left']),
        poly([centre, ur, lr, bottom], p['right']),
        f'<g transform="{ring_frame}" fill="none" stroke-linecap="butt">'
        f'<path d="{front}" stroke="{TILE_BOTTOM}" stroke-width="{cut:.2f}"/>'
        f'<path d="{front}" stroke="{RING_FRONT}" stroke-width="{ring:.2f}" stroke-linecap="round"/></g>',
        '</svg>',
    ]
    return ''.join(p for p in parts if p) + '\n'


def render(text, size):
    """The SVG as a size × size RGBA image, through librsvg."""
    png = subprocess.run(['magick', '-background', 'none', 'svg:-', 'png32:-'], input=text.encode('utf-8'),
                         capture_output=True, check=True).stdout
    image = Image.open(io.BytesIO(png)).convert('RGBA')
    if image.size != (size, size):
        raise SystemExit(f'{size}: librsvg drew {image.size}')
    return image


def write_ico(images, path):
    """An ICO with each image: 256 pixels as PNG, the smaller ones as 32-bit bitmaps (BGRA, bottom-up, with an empty
    AND mask), which every Windows reader takes."""
    entries = []
    for image in images:
        w, h = image.size
        if w >= 256:
            out = io.BytesIO()
            image.save(out, 'PNG', optimize=True)
            data = out.getvalue()
        else:
            header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
            r, g, b, a = image.split()
            pixels = Image.merge('RGBA', (b, g, r, a)).transpose(Image.FLIP_TOP_BOTTOM).tobytes()
            mask = bytes(((w + 31) // 32 * 4) * h)
            data = header + pixels + mask
        entries.append((w, h, data))
    offset = 6 + 16 * len(entries)
    with open(path, 'wb') as f:
        f.write(struct.pack('<HHH', 0, 1, len(entries)))
        for w, h, data in entries:
            f.write(struct.pack('<BBBBHHII', w % 256, h % 256, 0, 0, 1, 32, len(data), offset))
            offset += len(data)
        for _, _, data in entries:
            f.write(data)


def preview(images, folder):
    """Every size at 1x, then the small ones at 4x, on Windows' dark and light taskbar colours."""
    scale, pad, small = 4, 12, SIZES[:4]
    width = pad + sum(s + pad for s in SIZES) + sum(s * scale + pad for s in small)
    row = SIZES[-1] + 2 * pad
    sheet = Image.new('RGB', (width, 2 * row))
    for r, colour in enumerate(['#202020', '#F3F3F3']):
        sheet.paste(Image.new('RGB', (width, row), colour), (0, r * row))
        x, y = pad, r * row + pad
        for image in [images[s] for s in SIZES] + [images[s].resize((s * scale,) * 2, Image.NEAREST) for s in small]:
            sheet.paste(image, (x, y), image)
            x += image.width + pad
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, 'preview.png')
    sheet.save(path)
    print(f'Preview: {path}')


def main():
    preview_dir = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--preview=')), None)
    os.makedirs(WORK, exist_ok=True)
    with open(SVG_OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(svg(256))
    images = {}
    for size in SIZES:
        images[size] = render(svg(size), size)
        path = os.path.join(WORK, f'icon-{size}.png')
        images[size].save(path)
    write_ico([images[s] for s in SIZES], ICO_OUT)
    print(f'{SVG_OUT}, {ICO_OUT} ({os.path.getsize(ICO_OUT) // 1024} KB, {len(SIZES)} sizes)')
    if preview_dir:
        preview(images, preview_dir)


if __name__ == '__main__':
    main()
