"""The computer cards' shared measurements and layout logic, read by computer_print.py (which draws a card's printing and
screens) and computer.py (which builds it). Plain Python: Blender's Python imports it too.

A computer card (pc, pc88, x1, x68000, fm7, fmtowns, moto, to8, samcoupe, spectravideo, adam, coco, trs80) is described
by its own module, `<card>_layout.py`, in millimetres (x from the set's middle, left to right; y back from its front;
z up from the table):

- NAME, YAW, PITCH (the three-quarter view), COLOURS (swatches by name, hex).
- BLOCKS: the set's solids. Each a dict: `shape`, one of ("box", x0, x1, y0, y1, z0, z1), ("profile", x0, x1,
  [(y, z), ...]) (a side outline across x0..x1), ("plan", [(x, y), ...], z0, z1) (an outline in plan, upright) or
  ("lathe", x, y, z, [(r, dz), ...]) (a profile turned about the vertical through (x, y, z)); `round` (its edges' bevel), `corner` (a box's corners rounded in plan), `colour` (a swatch), `cuts` (boxes cut out
  of it, (x0, x1, y0, y1, z0, z1), their walls dark), `faces` (art printed on its faces: `front`, `back`, `top`,
  `left`, `right`, each a list of drawing items in that face's millimetres, a across from its left as seen, b down
  from its top; a profile's `top` is seen from above over its plan, its slopes too).
- KEYBOARD (or None): `origin` (x, y, z) and `slope` (degrees: the keys' frame, s up the slope from y), `height`,
  `taper`, `gap`, `U`, and `rows`, each dict(s=front edge, x=left edge, depth, keys=[(legend, width in U, colour)
  or (legend, width, colour, rows tall towards the front) or (None, width) for a gap]); `ink` (the legends' colour).
- DISPLAY (or None): a CRT monitor or a television: `at` (its front's bottom middle, x, y, z), `size` (the bezel's
  w, h, d), `back` (the tube's housing: w, h, d), `radius`, `colour`, `glass` (w, h), `glass_at` (dx, dz of its
  middle from the front's bottom middle), `recess`, `bulge`, `faces` (dict(front=[...])).
- MEDIA (or None): dict(kind="box"|"disc", size=(w, d, t), seat=(x, y, z), turn=(rx, ry, rz), colour, label=[items]
  drawn on its top (+z) face before it is turned, keys=[(frame, dict(x, y, z, scale, spin...))] from its seat).
- MOVERS: other moving parts: dict(name, shape (as a block's), colour, origin, keys) (a tray, a lid, a latch).
- LIGHTS: dict(name, at, face ("front", "top", "right", "left"), size (w, h), colour, on=[(f0, f1, "on"|"flicker")]).
- CABLES: dict(points, r, colour). PRESS: {legend: [frames]}, the keys the clip presses.
- SCREEN: dict(px=(w, h) native, palette (hex list) or None, ink, paper, border (colour, fraction), boot=[lines],
  load=[lines], prompt, game=(stem, system)); SHOW: [(f0, f1, "load"|"title"|"game")]; at rest the glass shows `boot`.

Drawing items: ("rect", a0, b0, a1, b1, colour[, r]), ("text", s, font, size, a, b, colour[, anchor]),
("circle", a, b, r, colour), ("slots", a0, b0, a1, b1, n, colour) (vertical vents), ("hslots", ...) (horizontal),
("dots", a0, b0, a1, b1, cols, rows, r, colour), ("line", [(a, b), ...], colour, width), ("cover", a0, b0, a1, b1) (the
made-up game's painting with its logo), ("logo", a0, b0, a1, b1). A colour is a swatch's name or a hex string.

Two textures a card: `<card>_print.png` (PRINT_ATLAS square: the faces' regions packed by pack(), the keys' tops, the
display's front, the media's label, the swatches) and `<card>_media.png` (MEDIA_ATLAS square: the screens, one cell each).
"""

import importlib
import math

PRINT_ATLAS = 1024          # every texture is drawn at most 1024 pixels (docs/THEMING.md section 7)
MEDIA_ATLAS = 1024
SWATCH_STRIP = 72            # the print atlas's bottom strip, for the swatches
SCREENS = ("boot", "load", "title", "game1", "game2")
FACES = ("front", "back", "top", "left", "right")


def load(card):
    return importlib.import_module(card + "_layout")


def bounds(shape):
    """A block's bounds (x0, x1, y0, y1, z0, z1)."""
    kind = shape[0]
    if kind == "box":
        return shape[1:7]
    if kind == "profile":
        ys, zs = [p[0] for p in shape[3]], [p[1] for p in shape[3]]
        return shape[1], shape[2], min(ys), max(ys), min(zs), max(zs)
    if kind == "lathe":
        _, x, y, z, profile = shape
        r = max(p[0] for p in profile)
        return x - r, x + r, y - r, y + r, z + min(p[1] for p in profile), z + max(p[1] for p in profile)
    xs, ys = [p[0] for p in shape[1]], [p[1] for p in shape[1]]
    return min(xs), max(xs), min(ys), max(ys), shape[2], shape[3]


def face_size(b, face):
    """A face's size (w, h) in millimetres, as its region is drawn."""
    x0, x1, y0, y1, z0, z1 = b
    return {"front": (x1 - x0, z1 - z0), "back": (x1 - x0, z1 - z0), "top": (x1 - x0, y1 - y0),
            "left": (y1 - y0, z1 - z0), "right": (y1 - y0, z1 - z0)}[face]


def face_ab(b, face, x, y, z):
    """A point's (a, b) on a face's region."""
    x0, x1, y0, y1, z0, z1 = b
    return {"front": (x - x0, z1 - z), "back": (x1 - x, z1 - z), "top": (x - x0, y1 - y),
            "left": (y1 - y, z1 - z), "right": (y - y0, z1 - z)}[face]


def keys_extent(kb):
    """The keys' region in the slope's frame: (x0, x1, s0, s1)."""
    rects = key_rects(kb)
    return (min(r[1] for r in rects) - 2.0, max(r[2] for r in rects) + 2.0, min(r[3] for r in rects) - 2.0,
            max(r[4] for r in rects) + 2.0)


def key_rects(kb):
    """Every key: (legend, x0, x1, s0, s1, colour), its base in the slope's frame (a key's gap taken off)."""
    u, g = kb["U"], kb["gap"] / 2
    rows = kb["rows"]
    out = []
    for i, row in enumerate(rows):
        x = row["x"]
        depth = row.get("depth", u)
        for key in row["keys"]:
            legend, w = key[0], key[1]
            if legend is not None:
                tall = key[3] if len(key) > 3 else 1
                s0 = rows[i + tall - 1]["s"] if tall > 1 else row["s"]
                out.append((legend, x + g, x + w * u - g, s0 + g, row["s"] + depth - g, key[2]))
            x += w * u
    return out


def regions_wanted(spec):
    """Every print region a card needs: (name, w, h) in millimetres."""
    out = []
    for k, block in enumerate(spec.BLOCKS):
        b = bounds(block["shape"])
        for face in FACES:
            if block.get("faces", {}).get(face):
                out.append((f"b{k}_{face}", *face_size(b, face)))
    kb = getattr(spec, "KEYBOARD", None)
    if kb:
        x0, x1, s0, s1 = keys_extent(kb)
        out.append(("keys", x1 - x0, s1 - s0))
    d = getattr(spec, "DISPLAY", None)
    if d and d.get("faces", {}).get("front"):
        out.append(("display_front", d["size"][0], d["size"][1]))
    media = getattr(spec, "MEDIA", None)
    if media and media.get("label"):
        out.append(("label", media["size"][0], media["size"][1]))
    for k, mover in enumerate(getattr(spec, "MOVERS", ())):
        for face in FACES:
            if mover.get("faces", {}).get(face):
                out.append((f"m{k}_{face}", *face_size(bounds(mover["shape"]), face)))
    return out


def pack(spec):
    """The print regions packed into the atlas: {name: (x, y, w, h)} pixels, at the largest scale (pixels a
    millimetre, at most 2) that fits them in shelves over the swatches' strip."""
    wanted = sorted(regions_wanted(spec), key=lambda r: (-r[2], -r[1], r[0]))
    size = PRINT_ATLAS
    for scale in (2.0, 1.8, 1.6, 1.45, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4):
        out, x, y, shelf = {}, 0, 0, 0
        fits = True
        for name, w, h in wanted:
            pw, ph = max(8, round(w * scale)), max(8, round(h * scale))
            if pw > size:
                fits = False
                break
            if x + pw > size:
                x, y, shelf = 0, y + shelf + 6, 0
            if y + ph > size - SWATCH_STRIP:
                fits = False
                break
            out[name] = (x, y, pw, ph)
            x += pw + 6
            shelf = max(shelf, ph)
        if fits:
            return out
    raise ValueError("the print regions don't fit")


def swatches(spec):
    """Each colour's swatch: its block's middle, (x, y) pixels, in the strip at the atlas's foot."""
    names = sorted(spec.COLOURS)
    return {name: (20 + 32 * (k % 31), PRINT_ATLAS - SWATCH_STRIP + 18 + 32 * (k // 31)) for k, name in enumerate(names)}


def media_regions():
    """The screens' cells in the media atlas: two columns of three."""
    w, h = MEDIA_ATLAS // 2, MEDIA_ATLAS // 3
    return {name: ((k % 2) * w, (k // 2) * h, w, h) for k, name in enumerate(SCREENS)}


def keyed(keys, f):
    """A part's pose at frame f from its keyframes [(frame, dict)], smoothed between them; missing values 0 (scale 1)."""
    if not keys:
        return {}
    if f <= keys[0][0]:
        return dict(keys[0][1])
    for (f0, a), (f1, b) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            t = (f - f0) / (f1 - f0) if f1 > f0 else 1.0
            t = t * t * (3 - 2 * t)
            out = {}
            for name in set(a) | set(b):
                rest = 1.0 if name == "scale" else 0.0
                out[name] = a.get(name, rest) + (b.get(name, rest) - a.get(name, rest)) * t
            return out
    return dict(keys[-1][1])


def showing(spec, f):
    for f0, f1, name in spec.SHOW:
        if f0 <= f < f1:
            if name == "game":
                return "game1" if ((f - f0) // 8) % 2 == 0 else "game2"
            return name
    return None


def lit(light, f):
    for f0, f1, mode in light["on"]:
        if f0 <= f < f1:
            return mode == "on" or (f // 3) % 4 != 3
    return False


def angle_of(p, q):
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
