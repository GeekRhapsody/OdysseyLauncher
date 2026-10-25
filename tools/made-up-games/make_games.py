"""Makes the made-up games' media for the README's captures (docs/readme/): for every release of every game in
games.toml, its cover, back, spine, cartridge label, logo and screenshot (an arcade game's logo and screenshot only),
composed from its Codex paintings (codex_art.py) with logos, packaging and HUDs drawn here, the same on every run.
Writes a portable user folder to capture from, and review sheets:

    python tools/made-up-games/make_games.py [--games=<id>,...] [--out=<folder>] [--jobs=<n>]

  <out>/library/                  a portable user folder (--user-dir): settings.toml, ROMs/<system>/ with an empty file per
                                  game and a gamelist.xml of their details, and media/<system>/<kind>/ in the app's layout
  <out>/sheets/<system>-<kind>.jpg  every game's piece of one kind side by side, for review

--out defaults to artifacts/made-up-games; --games makes only those games' pieces again. Games whose paintings are
missing are left out, with a warning. Scan the library and import the details once with odyssey-scrape (the library's
README.txt says how). Needs Pillow, numpy and scipy, and the fonts named in logos.py and boxes.py (Windows' and
Office's).
"""
import argparse
import os
import shutil
import tomllib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw

import boxes as B
import logos as L
import paint as P
import screens as S
from codex_art import look_of

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXTENSIONS = {"cover": ".jpg", "back": ".jpg", "spine": ".jpg", "label": ".jpg", "logo": ".png", "screenshot": ".png"}
FOLDERS = {"cover": "covers", "back": "backcovers", "spine": "spines", "label": "labels", "logo": "logos",
           "screenshot": "screenshots"}
ROM_EXTENSIONS = {"megadrive": ".md", "snes": ".sfc", "n64": ".z64", "arcade": ".zip"}
SYSTEMS = ["megadrive", "snes", "n64", "arcade"]


def releases(games):
    """Every version of every game, as the game with that version's changes."""
    out = []
    for game in games:
        for version in game["versions"]:
            g = {k: v for k, v in game.items() if k not in ("versions", "screens", "keyart")}
            g.update(version)
            g["concept"] = game["id"]
            g["look"] = look_of(game, version)
            if "file" not in g:
                g["file"] = g["title"].replace(": ", " - ") + " (Europe)" + ROM_EXTENSIONS[g["system"]]
            out.append(g)
    return out


def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".jpg":
        image.convert("RGB").save(path, quality=92, subsampling=0, optimize=True)
    else:
        image.save(path, optimize=True)


def make(release, paintings, media):
    """One release's pieces, written into the library's media folder. Returns its kinds."""
    folder = paintings / release["concept"]
    system = release["system"]
    stem = Path(release["file"]).stem
    logo = L.logo(release["logo"])
    pieces = {"logo": P.layer_image(logo),
              "screenshot": S.screenshot(release, Image.open(folder / f"screen-{release['look']}.png"), system, release["look"])}
    if system != "arcade":
        art = Image.open(folder / "keyart.png").convert("RGB")
        pieces["cover"] = P.to_image(B.cover(release, art, logo))
        pieces["back"] = P.to_image(B.back(release, art, logo, pieces["screenshot"]))
        pieces["spine"] = P.to_image(B.spine(release, art, logo))
        pieces["label"] = P.to_image(B.label(release, art, logo))
    for kind, image in pieces.items():
        save(image, media / system / FOLDERS[kind] / (stem + EXTENSIONS[kind]))
    return f"{system}/{stem}: {', '.join(pieces)}"


def gamelist(members):
    """ES-DE's gamelist.xml for one system's games: their details, which import-gamelist reads."""
    lines = ['<?xml version="1.0"?>', "<gameList>"]
    for g in members:
        lines += ["\t<game>", f"\t\t<path>./{escape(g['file'])}</path>", f"\t\t<name>{escape(g['title'])}</name>",
                  f"\t\t<desc>{escape(g['description'])}</desc>", f"\t\t<rating>{g['rating']}</rating>",
                  f"\t\t<releasedate>{g['released'].replace('-', '')}T000000</releasedate>",
                  f"\t\t<developer>{escape(g['developer'])}</developer>",
                  f"\t\t<publisher>{escape(g['publisher'])}</publisher>", f"\t\t<genre>{escape(g['genre'])}</genre>",
                  f"\t\t<players>{escape(g['players'])}</players>", "\t</game>"]
    lines.append("</gameList>")
    return "\n".join(lines) + "\n"


def write_library(root, made):
    roms = root / "ROMs"
    root.mkdir(parents=True, exist_ok=True)
    (root / "settings.toml").write_text(
        f"[paths]\nrom_root = '{roms}'\n\n[display]\nscreen_mode = \"windowed\"\n", encoding="utf-8", newline="\n")
    systems = sorted({g["system"] for g in made}, key=SYSTEMS.index)
    for system in systems:
        members = [g for g in made if g["system"] == system]
        folder = roms / system
        folder.mkdir(parents=True, exist_ok=True)
        for g in members:
            (folder / g["file"]).write_bytes(b"")
        (folder / "gamelist.xml").write_text(gamelist(members), encoding="utf-8", newline="\n")
    (root / "README.txt").write_text(
        "Made by tools/made-up-games/make_games.py: made-up games for the README's captures. Safe to delete.\n\n"
        "Scan the library and bring in the games' details (titles, descriptions, release dates...) once, from the repo root:\n\n"
        f"  .\\tools\\scrape-cli\\bin\\Debug\\net8.0\\odyssey-scrape.exe --user-dir={root} scan\n"
        + "".join(f"  .\\tools\\scrape-cli\\bin\\Debug\\net8.0\\odyssey-scrape.exe --user-dir={root} import-gamelist {s}\n"
                  for s in systems)
        + f"\nThen run the app with --user-dir={root}\n", encoding="utf-8", newline="\n")


# Review sheets -----------------------------------------------------------------------------------------------------

def _checker(w, h, cell=12):
    yy, xx = np.mgrid[0:h, 0:w]
    a = np.where(((xx // cell) + (yy // cell)) % 2, 70, 52).astype(np.uint8)
    return Image.fromarray(np.stack([a, a, a + 8], -1))


def contact_sheet(paths, height, width=2400, captions=True):
    """Images in rows, each scaled to height (a wide strip to a share of the width instead), captioned."""
    pad, cap = 14, 22 if captions else 0
    tiles = []
    for p in paths:
        im = Image.open(p)
        w, h = im.size
        if w / h > 4:                                          # a top spine
            tw = min(width // 2 - 2 * pad, int(w * height / h * 0.35))
            im = im.resize((tw, max(1, int(h * tw / w))), Image.LANCZOS)
        else:
            resample = Image.NEAREST if w <= 320 else Image.LANCZOS
            im = im.resize((max(1, int(w * height / h)), height), resample)
        if im.mode == "RGBA":
            bg = _checker(*im.size)
            bg.paste(im, (0, 0), im)
            im = bg
        tiles.append((p.stem, im.convert("RGB")))
    x = y = pad
    row_h = 0
    places = []
    for name, im in tiles:
        if x + im.width > width - pad and x > pad:
            x = pad
            y += row_h + cap + pad
            row_h = 0
        places.append((name, im, x, y))
        x += max(im.width, 120) + pad
        row_h = max(row_h, im.height)
    sheet = Image.new("RGB", (width, y + row_h + cap + pad), (24, 24, 30))
    draw = ImageDraw.Draw(sheet)
    font = P.font("segoeui.ttf", 15)
    for name, im, x, y in places:
        sheet.paste(im, (x, y))
        if captions:
            draw.text((x, y + im.height + 3), name[:max(8, im.width // 8)], fill=(170, 170, 185), font=font)
    return sheet


def sheets(media, out):
    heights = {"cover": 300, "back": 300, "spine": 300, "label": 160, "logo": 110, "screenshot": 224}
    for system in SYSTEMS:
        for kind, folder in FOLDERS.items():
            paths = sorted((media / system / folder).glob("*")) if (media / system / folder).exists() else []
            if paths:
                save(contact_sheet(paths, heights[kind]), out / f"{system}-{folder}.jpg")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--games", help="only these games' ids, comma-separated")
    parser.add_argument("--out", default=str(REPO / "artifacts" / "made-up-games"))
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    args = parser.parse_args()
    out = Path(args.out)
    paintings = out / "paintings"
    with open(HERE / "games.toml", "rb") as f:
        games = tomllib.load(f)["games"]
    ready, skipped = [], []
    for r in releases(games):
        folder = paintings / r["concept"]
        needed = [folder / f"screen-{r['look']}.png"] + ([folder / "keyart.png"] if r["system"] != "arcade" else [])
        (ready if all(p.exists() for p in needed) else skipped).append(r)
    for r in skipped:
        print(f"Left out {r['system']}/{r['title']}: its paintings aren't there yet (codex_art.py)")
    # Only the chosen games' pieces are made again, but every ready game keeps its ROM and its gamelist entry.
    wanted = set(args.games.split(",")) if args.games else None
    todo = [r for r in ready if not wanted or r["concept"] in wanted]
    media = out / "library" / "media"
    if not wanted:                                             # a full run starts from a clean library and sheets
        for stale in (media, out / "library" / "ROMs", out / "sheets"):
            shutil.rmtree(stale, ignore_errors=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for line in pool.map(make, todo, [paintings] * len(todo), [media] * len(todo)):
            print(line, flush=True)
    write_library(out / "library", ready)
    sheets(media, out / "sheets")
    counts = {s: sum(1 for r in ready if r["system"] == s) for s in SYSTEMS}
    print(f"Wrote {len(ready)} games ({', '.join(f'{n} {s}' for s, n in counts.items())}) into {out / 'library'}, "
          f"and sheets into {out / 'sheets'}; {len(skipped)} left out.")


if __name__ == "__main__":
    main()
