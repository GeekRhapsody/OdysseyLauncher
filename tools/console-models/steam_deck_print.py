"""The Steam Deck card's printing and screens (steam_deck_print.png, steam_deck_screens.jpg), for the console theme's
Steam model (steam_deck.py).

`steam_deck_print.png`, laid out as steam_deck_layout.REGIONS says, each region in millimetres as the model's UVs map
it: the face (the black glass round the display, the seams round the grips, the trackpads' surfaces in their gaps, the
speakers' slots, the sticks' housings and caps, and the buttons' tops where they stand: the D-pad, A, B, X and Y
lettered, View's and Menu's marks, STEAM, the quick access button's dots), the back (the seams round the grips, the
triggers' outlines, the grip buttons' gaps and names, the fan's intake grilles, VALVE on its plate, the screws, the
regulatory print as faint lines), the top edge (the fan's exhaust, USB-C, the status light, POWER's and the volume
buttons' marks, the headphone jack, the seam along it), the bottom edge (the microSD slot) and the swatches.
`steam_deck_screens.jpg`, the display's four states at 960 x 600: waking (a spinner), the library (made-up covers, the
first game chosen) and two moments of a made-up game (tools/made-up-games: no real game's art). Make the made-up
games' library first (tools/made-up-games/README.md), then run it with the system Python (Pillow, numpy, scipy):

    python tools/console-models/steam_deck_print.py artifacts/made-up-games <out folder>
"""

import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steam_deck_layout as L  # noqa: E402
from arcade_print import Game, font  # noqa: E402
from retro_pc_print import mix, rgb, shade  # noqa: E402
from windows_pc_print import Region  # noqa: E402

C = {name: rgb(hex_) for name, hex_ in L.COLOURS.items()}
SANS, BOLD, DIN = "segoeui.ttf", "segoeuib.ttf", "bahnschrift.ttf"
SEAM = 0.35                       # a seam's width, mm


def region(name):
    """A region drawn in millimetres, and where a point (x and z, or x and y on the edges) lands in it."""
    x0, x1, v0, v1 = L.SPANS[name]
    reg = Region(L.REGIONS[name], x1 - x0, v1 - v0, C["case"] + (255,))
    if name == "front":
        return reg, lambda x, z: (x - x0, v1 - z)
    if name == "rear":
        return reg, lambda x, z: (x1 - x, v1 - z)
    if name == "top":
        return reg, lambda x, y: (x - x0, v1 - y)
    return reg, lambda x, y: (x - x0, y - v0)


def box(at, cx, cz, w, h):
    """A box w x h about (cx, cz), as a region's corners (left, top, right, bottom)."""
    (ax, ay), (bx, by) = at(cx - w / 2, cz + h / 2), at(cx + w / 2, cz - h / 2)
    return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)


def pill(reg, at, cx, cz, w, h, fill, outline=None, width=0.0):
    x0, y0, x1, y1 = box(at, cx, cz, w, h)
    reg.rect_(x0, y0, x1, y1, fill, r=min(w, h) / 2, outline=outline, width=width)


# ---- The face --------------------------------------------------------------------------------------------------------

def face(atlas):
    reg, at = region("front")
    for side in (1, -1):                                       # the seams round the grips
        reg.line([at(side * x, z) for x, z in L.SEAM_FRONT], C["seam"], SEAM)
    g, s = L.GLASS, L.SCREEN
    x0, y0, x1, y1 = box(at, g["x"], g["z"], g["width"], g["height"])
    reg.rect_(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5, C["seam"], r=g["r"] + 0.5)
    reg.rect_(x0, y0, x1, y1, C["glass"], r=g["r"])
    reg.rect_(*box(at, s["x"], s["z"], s["width"], s["height"]), shade(C["glass"], -0.25))
    for mx, mz in L.MICS:
        reg.circle(*at(mx, mz), 0.45, C["port"])
    for side in (1, -1):
        speaker(reg, at, side)
        trackpad(reg, at, *L.PADS["left" if side < 0 else "right"])
        stick_top(reg, at, *L.STICKS["left" if side < 0 else "right"])
    dpad(reg, at)
    face_buttons(reg, at)
    pills(reg, at)
    reg.paste(atlas)


def speaker(reg, at, side):
    for z, slots in L.SPEAKER:
        for xa, xb in slots:
            pill(reg, at, side * (xa + xb) / 2, z, abs(xb - xa), L.SPEAKER_SLOT, C["vent"])


def trackpad(reg, at, px, pz):
    p = L.PADS
    x0, y0, x1, y1 = box(at, px, pz, p["size"], p["size"])
    reg.rect_(x0 - 0.6, y0 - 0.6, x1 + 0.6, y1 + 0.6, C["seam"], r=p["r"] + 0.6)    # the gap round it
    reg.rect_(x0, y0, x1, y1, C["pad"], r=p["r"])
    reg.rect_(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5, shade(C["pad"], -0.06), r=p["r"] - 0.5)


def stick_top(reg, at, sx, sz):
    """The housing round the stick and the cap's top: dished, its rim knurled."""
    s = L.STICK
    cx, cy = at(sx, sz)
    reg.circle(cx, cy, s["base"] + 0.3, C["seam"])
    reg.circle(cx, cy, s["base"], C["button"])
    reg.circle(cx, cy, s["top"] + 0.6, shade(C["button"], 0.08))
    reg.circle(cx, cy, s["cap"], C["cap"])
    for k in range(48):                                        # the knurled rim
        a = 2 * math.pi * k / 48
        reg.line([(cx + 6.6 * math.cos(a), cy + 6.6 * math.sin(a)), (cx + 7.9 * math.cos(a), cy + 7.9 * math.sin(a))],
                 shade(C["cap"], -0.35), 0.25)
    reg.circle(cx, cy, 6.3, shade(C["cap"], 0.05))
    reg.circle(cx, cy, 4.0, shade(C["cap"], 0.09))


def dpad(reg, at):
    d = L.DPAD
    cx, cy = at(d["x"], d["z"])
    half, arm = d["span"] / 2, d["arm"] / 2
    for w, h in ((2 * half + 0.6, 2 * arm + 0.6), (2 * arm + 0.6, 2 * half + 0.6)):
        reg.rect_(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, C["seam"], r=1.6)
    for w, h in ((2 * half, 2 * arm), (2 * arm, 2 * half)):
        reg.rect_(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, C["button"], r=1.3)
    reg.circle(cx, cy, 3.0, shade(C["button"], -0.15))         # the dish in its middle


def face_buttons(reg, at):
    a = L.ABXY
    for name, degrees in L.FACE_BUTTONS:
        bx = a["x"] + a["reach"] * math.cos(math.radians(degrees))
        bz = a["z"] + a["reach"] * math.sin(math.radians(degrees))
        cx, cy = at(bx, bz)
        reg.circle(cx, cy, a["r"] + 0.3, C["seam"])
        reg.circle(cx, cy, a["r"], C["button"])
        reg.text(name.upper(), BOLD, 5.2, cx, cy - 0.2, C["legend"])


def pills(reg, at):
    for name, (px, pz, w, h) in L.PILLS.items():
        pill(reg, at, px, pz, w + 0.6, h + 0.6, C["seam"])
        pill(reg, at, px, pz, w, h, C["button"])
        cx, cy = at(px, pz)
        ink = shade(C["legend"], -0.08)
        if name == "steam":
            reg.text("STEAM", DIN, 3.0, cx, cy, ink)
        elif name == "qam":
            for k in (-1, 0, 1):
                reg.circle(cx + 1.9 * k, cy, 0.55, ink)
        elif name == "menu":
            for k in (-1, 0, 1):
                reg.rect_(cx - 1.6, cy + 0.85 * k - 0.2, cx + 1.6, cy + 0.85 * k + 0.2, ink)
        else:                                                  # View: two windows, one over the other
            reg.rect_(cx - 1.9, cy - 0.3, cx + 0.5, cy + 1.3, None, outline=ink, width=0.35)
            reg.rect_(cx - 0.6, cy - 1.3, cx + 1.9, cy + 0.3, C["button"], outline=ink, width=0.35)


# ---- The back --------------------------------------------------------------------------------------------------------

def rear(atlas):
    reg, at = region("rear")
    for side in (1, -1):
        reg.line([at(side * x, z) for x, z in L.SEAM_BACK], C["seam"], SEAM)
        reg.line([at(side * x, z) for x, z in L.SOCKET[4:]] + [at(side * L.SOCKET[-1][0], L.HEIGHT)], C["seam"], SEAM)
        reg.line([at(side * x, z) for x, z in L.TRIGGER_BACK + L.TRIGGER_BACK[:1]], C["seam"], SEAM)
    q = L.PADDLES
    for name in ("r4", "r5", "l4", "l5"):
        px, pz = q[name]
        x0, y0, x1, y1 = box(at, px, pz, q["size"], q["size"])
        reg.rect_(x0 - 0.6, y0 - 0.6, x1 + 0.6, y1 + 0.6, C["seam"], r=q["r"] + 0.6)
        reg.rect_(x0, y0, x1, y1, C["case"], r=q["r"])
        inward = -1 if px > 0 else 1                           # its name in its upper corner nearer the middle
        reg.text(name.upper(), SANS, 2.4, *at(px + inward * 6.2, pz + 6.6), shade(C["case"], 0.28))
    v = L.VENTS
    for vx in v["x"]:
        vent(reg, at, vx, v["z"], v["width"], v["height"])
    p = L.VALVE
    x0, y0, x1, y1 = box(at, p["x"], p["z"], p["width"], p["height"])
    reg.rect_(x0, y0, x1, y1, C["plate"], r=0.8)
    cx, cy = at(p["x"], p["z"])
    for k, letter in enumerate("VALVE"):
        reg.text(letter, DIN, 6.0, cx + (k - 2) * 5.6, cy, shade(C["case"], 0.22))
    for sx, sz in L.SCREWS:
        cx, cy = at(sx, sz)
        reg.circle(cx, cy, 1.25, C["seam"])
        reg.circle(cx, cy, 0.95, shade(C["case"], -0.1))
        reg.line([(cx - 0.6, cy), (cx + 0.6, cy)], C["seam"], 0.25)
        reg.line([(cx, cy - 0.6), (cx, cy + 0.6)], C["seam"], 0.25)
    faint = shade(C["case"], 0.045)                            # the regulatory print, too small to read
    for k in range(4):
        reg.line([at(-26.0, 46.0 - 3.0 * k), at(-78.0 + 9 * (k % 2), 46.0 - 3.0 * k)], faint, 0.8)
    reg.paste(atlas)


def vent(reg, at, vx, vz, w, h):
    """An intake grille: a slot with round ends, a mesh of holes in it."""
    x0, y0, x1, y1 = box(at, vx, vz, w, h)
    reg.rect_(x0 - 0.4, y0 - 0.4, x1 + 0.4, y1 + 0.4, C["seam"], r=w / 2 + 0.4)
    reg.rect_(x0, y0, x1, y1, C["vent"], r=w / 2)
    for row in range(int(h / 1.0)):
        for col in range(int(w / 1.1)):
            hx, hy = x0 + 0.9 + col * 1.1 + 0.55 * (row % 2), y0 + 0.9 + row * 1.0
            if math.hypot((hx - (x0 + x1) / 2) / (w / 2 - 0.6), max(0.0, abs(hy - (y0 + y1) / 2) - (h / 2 - w / 2))
                          / (w / 2 - 0.6)) < 1.0:
                reg.circle(hx, hy, 0.32, shade(C["vent"], 0.22))


# ---- The edges -------------------------------------------------------------------------------------------------------

def top(atlas):
    reg, at = region("top")
    t = L.TOP
    reg.line([at(-L.HALF, t["seam"]), at(L.HALF, t["seam"])], C["seam"], SEAM)
    x0, x1, n = t["vent"]
    pitch = (x1 - x0) / n
    y0, y1 = t["vent_y"]
    for k in range(n):
        cx = x0 + pitch * (k + 0.5)
        pill(reg, at, cx, (y0 + y1) / 2, pitch * 0.74, y1 - y0, C["vent"])
        for j in range(5):
            reg.circle(*at(cx, y0 + 1.4 + j * (y1 - y0 - 2.8) / 4), 0.3, shade(C["vent"], 0.2))
    ux, uw, uh = t["usb"]
    pill(reg, at, ux, t["y"], uw + 0.6, uh + 0.6, C["seam"])
    pill(reg, at, ux, t["y"], uw, uh, C["port"])
    pill(reg, at, ux, t["y"], uw - 3.2, 0.7, shade(C["port"], 0.35))
    reg.circle(*at(t["led"], t["y"]), 0.7, shade(C["case"], 0.25))
    r = t["button_r"]
    for x, mark in ((t["power"], "power"), (t["volume"][0], "-"), (t["volume"][1], "+")):
        cx, cy = at(x, t["y"])
        reg.circle(cx, cy, r + 0.35, C["seam"])
        reg.circle(cx, cy, r, C["button"])
        ink = shade(C["legend"], -0.25)
        reg.line([(cx - 1.4, cy), (cx + 1.4, cy)], ink, 0.35)
        if mark == "+":
            reg.line([(cx, cy - 1.4), (cx, cy + 1.4)], ink, 0.35)
        elif mark == "power":
            reg.draw.arc(reg.box(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), -50, 230, fill=ink, width=reg.width(0.35))
            reg.draw.rectangle(reg.box(cx - 0.17, cy - 1.8, cx + 0.17, cy - 0.3), fill=C["button"])
            reg.line([(cx, cy - 1.8), (cx, cy - 0.2)], ink, 0.35)
    cx, cy = at(t["jack"], t["y"])
    reg.circle(cx, cy, r + 0.35, C["seam"])
    reg.circle(cx, cy, r, shade(C["case"], -0.12))
    reg.circle(cx, cy, 1.8, C["port"])
    reg.paste(atlas)


def bottom(atlas):
    reg, at = region("bottom")
    reg.line([at(-L.HALF, L.TOP["seam"]), at(L.HALF, L.TOP["seam"])], C["seam"], SEAM)
    x, y, w, h = L.MICRO_SD
    pill(reg, at, x, y, w + 0.6, h + 0.6, C["seam"])
    pill(reg, at, x, y, w, h, C["port"])
    reg.paste(atlas)


def swatches(atlas):
    d = ImageDraw.Draw(atlas)
    for name, (x, y) in L.SWATCHES.items():
        d.rectangle([x - 14, y - 14, x + 14, y + 14], fill=C[name])


# ---- The screens -----------------------------------------------------------------------------------------------------

def screens(made_up):
    """The display's four states, each drawn at 960 x 600 and put in its place."""
    atlas = Image.new("RGB", (L.SCREEN_SIZE, L.SCREEN_SIZE), (0, 0, 0))
    w, h = 960, 600
    covers = [Image.open(Path(made_up) / "library" / "media" / "megadrive" / "covers" / f"{g} (Europe).jpg")
              .convert("RGB") for g in L.MADE_UP]
    library = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(library)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=mix((30, 36, 52), (12, 14, 20), y / h))
    d.text((40, 40), "Library", font=font(BOLD, 40), fill=(240, 240, 240), anchor="lm")
    d.text((920, 40), "10:41", font=font("arialbd.ttf", 30), fill=(220, 220, 220), anchor="rm")
    for k, cover in enumerate(covers[:5]):
        cw, ch = (230, 320) if k == 0 else (160, 224)
        x = 40 if k == 0 else 300 + (k - 1) * 170
        y = 110 if k == 0 else 150
        library.paste(ImageOps.fit(cover, (cw, ch), Image.LANCZOS), (x, y))
        if k == 0:
            d.rectangle([x - 5, y - 5, x + cw + 4, y + ch + 4], outline=(255, 255, 255), width=5)
    d.text((40, 470), L.MADE_UP[0], font=font("arialbd.ttf", 34), fill=(250, 250, 250), anchor="lm")
    d.rounded_rectangle([40, 510, 250, 566], radius=8, fill=rgb("#4C8CF0"))
    d.text((145, 538), "PLAY", font=font("arialbd.ttf", 28), fill=(255, 255, 255), anchor="mm")
    boot = Image.new("RGB", (w, h), (8, 8, 10))
    d = ImageDraw.Draw(boot)
    for k in range(12):                                        # a spinner while it wakes
        a = 2 * math.pi * k / 12
        d.ellipse([w / 2 + 50 * math.cos(a) - 7, h / 2 + 50 * math.sin(a) - 7, w / 2 + 50 * math.cos(a) + 7,
                   h / 2 + 50 * math.sin(a) + 7], fill=shade((230, 230, 240), -k / 14))
    game = Game("voltcrwn", made_up)
    frames = dict(boot=boot, library=library, game1=game.shot, game2=game.frame(0.4))
    for name, (x, y, rw, rh) in L.SCREENS.items():
        atlas.paste(ImageOps.fit(frames[name].convert("RGB"), (rw, rh), Image.LANCZOS), (x, y))
    return atlas


def main(made_up, out):
    os.makedirs(out, exist_ok=True)
    atlas = Image.new("RGB", (L.ATLAS, L.ATLAS), C["case"])
    for draw in (face, rear, top, bottom, swatches):
        draw(atlas)
    atlas.save(os.path.join(out, "steam_deck_print.png"), optimize=True)
    screens(made_up).save(os.path.join(out, "steam_deck_screens.jpg"), quality=90, optimize=True)
    print(os.path.join(out, "steam_deck_print.png"))


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
