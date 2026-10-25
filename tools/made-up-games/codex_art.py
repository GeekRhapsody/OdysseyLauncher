"""Commissions the made-up games' paintings from Codex (its built-in image tool), from games.toml's prompts, into
artifacts/made-up-games/paintings/<game>/: each game's key art (keyart.png), and its screens (screen-<look>.png),
painted four at a time as a 2 x 2 grid of four games' screens and cut apart (the grids are kept in _grids/). Each
painting's prompt is saved beside it. Only missing paintings are made, so delete one to have it painted again.

    python tools/made-up-games/codex_art.py [--games=<id>,...] [--jobs=4] [--model=gpt-6.1-sol] [--dry-run]
    python tools/made-up-games/codex_art.py --resplit

--resplit cuts the kept grids into their games' screens again (after a change to how grids are split), painting nothing.

Mega Drive games come first, then SNES, N64 and arcade ones, so that if Codex starts refusing (a usage limit), the
games already painted are whole: it then stops starting new runs, lets the running ones finish, and says how many
paintings it made. Needs the Codex CLI, logged in (a ChatGPT account will do); a run takes about two minutes. See
README.md for the whole process.
The paintings aren't reproducible: everything make_games.py makes from them is.
"""
import argparse
import re
import shutil
import subprocess
import sys
import threading
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PAINTINGS = REPO / "artifacts" / "made-up-games" / "paintings"
PRIORITY = {"megadrive": 0, "snes": 1, "n64": 2, "arcade": 3}
LOOKS = {   # how a look's screens are painted: the grid, the panels' shape, and what the panels are
    "16bit": ("2x2", "Landscape, 3:2", "each a screenshot from a different fictional 16-bit console game of the early 1990s, exactly as "
              "the console drew it: about 320 x 224 pixels shown enlarged, every pixel crisp and square, a limited 16-bit palette, no "
              "blur and no smoothing"),
    "n64": ("2x2", "Landscape, 3:2", "each a screenshot from a different fictional 3D game for a late-1990s 64-bit console, exactly "
            "as the console drew it: about 320 x 240, low-polygon models, blurry bilinear-filtered textures, distance fog and the "
            "console's soft, slightly dithered look"),
    "arcade": ("2x2", "Landscape, 3:2", "each a screenshot from a different fictional 1990s arcade game, exactly as the arcade board "
               "drew it: about 320 x 224 pixels shown enlarged, every pixel crisp and square, rich colourful pixel art, no blur"),
    "arcade_v": ("1x2", "Landscape, 3:2", "each a screenshot from a different fictional vertical-screen arcade game of the early "
                 "1990s, exactly as the arcade board drew it: about 224 x 300 pixels shown enlarged (taller than wide), every pixel "
                 "crisp and square, no blur"),
}
REFUSED = re.compile(r"usage limit|rate limit|quota|too many requests|\b429\b|limit reached|try again later", re.I)

PREAMBLE = """Use your built-in image generation tool to create exactly one image, and save it as a PNG file named \
{name} in the current working directory. Do nothing else: don't create or edit any other files.

No text, letters, numbers, logos, signatures, borders or watermarks anywhere in the image. Original designs only: \
don't imitate any existing game, character, film, car or franchise.

The image: """


def look_of(game, version):
    """The screen a version shows: its own choice, else its system's look, else the 16-bit one."""
    if "screen" in version:
        return version["screen"]
    order = {"megadrive": ["16bit"], "snes": ["16bit"], "n64": ["n64", "16bit"], "arcade": ["arcade", "16bit"]}
    return next((k for k in order[version["system"]] if k in game.get("screens", {})), "16bit")


def needs(games, only):
    """The missing paintings, most important first: [(priority, kind, game, look)], kind 'keyart' or 'screen'."""
    out = []
    for game in games:
        if only and game["id"] not in only:
            continue
        folder = PAINTINGS / game["id"]
        prio = min(PRIORITY[v["system"]] for v in game["versions"])
        if any(v["system"] != "arcade" for v in game["versions"]) and not (folder / "keyart.png").exists():
            out.append((prio, "keyart", game, None))
        for look in sorted({look_of(game, v) for v in game["versions"]}):
            if not (folder / f"screen-{look}.png").exists():
                out.append((prio, "screen", game, look))
    return sorted(out, key=lambda n: (n[0], n[1] != "screen"))


def plan(needed):
    """Runs: a key art each, and the screens four (or two) to a grid, grouped by look, in priority order."""
    runs, by_look = [], {}
    for prio, kind, game, look in needed:
        if kind == "keyart":
            runs.append((prio, "keyart", [(game, None)]))
        else:
            by_look.setdefault(look, []).append((prio, game))
    for look, items in by_look.items():
        size = 4 if LOOKS[look][0] == "2x2" else 2
        for k in range(0, len(items), size):
            chunk = items[k:k + size]
            runs.append((min(p for p, _ in chunk), "grid", [(g, look) for _, g in chunk]))
    return sorted(runs, key=lambda r: (r[0], r[1] != "grid"))


def grid_prompt(cells):
    look = cells[0][1]
    layout, shape, what = LOOKS[look]
    places = ["Top left", "Top right", "Bottom left", "Bottom right"] if layout == "2x2" else ["Left", "Right"]
    n = len(cells)
    if layout == "2x2":
        head = (f"{shape}. A grid of two rows and two columns: four separate panels of the same size, divided by thin black "
                f"lines, {what}. Each panel shows only its own game's screen, edge to edge.")
    else:
        head = (f"{shape}. Two separate tall panels side by side, each as tall as the picture and of the same size, divided "
                f"by a thin black line, {what}. Each panel shows only its own game's screen, edge to edge.")
    body = "\n\n".join(f"{places[k]}: {g['screens'][look]}" for k, (g, _) in enumerate(cells))
    if n < len(places):
        body += "\n\n" + "\n\n".join(f"{places[k]}: a plain black panel." for k in range(n, len(places)))
    return f"{head}\n\n{body}"


def _uniform_runs(std, low=6.0, gap=4):
    """The runs of rows (or columns) that hardly vary, as (start, end) pairs, those a few pixels apart merged."""
    out, start = [], None
    for k, v in enumerate(list(std) + [low + 1]):
        if v < low and start is None:
            start = k
        elif v >= low and start is not None:
            if out and start - out[-1][1] <= gap:
                out[-1] = (out[-1][0], k)
            else:
                out.append((start, k))
            start = None
    return out


def split(image, layout):
    """A grid painting cut into its panels. The dividers are thin runs of rows or columns that hardly vary, near where
    the grid's boundaries should be; a thin one at an edge is a border. A wide plain band is a panel's own (a prompt
    asks for one for the HUD), even where it runs across two panels. With no divider found, the boundary is cut where
    it should be."""
    a = np.asarray(image.convert("L"), dtype=np.float32)
    h, w = a.shape
    cols, rows = (2, 2) if layout == "2x2" else (2, 1)

    def spans(std, length, count):
        thin = length * 0.02
        uniform = [r for r in _uniform_runs(std) if r[1] - r[0] <= thin]
        lo = next((e for s, e in uniform if s == 0), 0)
        hi = next((s for s, e in uniform if e == length), length)
        bounds = [lo]
        for k in range(1, count):
            expected = length * k / count
            near = [r for r in uniform if abs((r[0] + r[1]) / 2 - expected) < length * 0.08]
            cut = min(near, key=lambda r: abs((r[0] + r[1]) / 2 - expected)) if near else (int(expected) - 4, int(expected) + 4)
            bounds += list(cut)
        bounds.append(hi)
        return [(bounds[2 * k], bounds[2 * k + 1]) for k in range(count)]

    xs = spans(a.std(axis=0), w, cols)
    ys = spans(a.std(axis=1), h, rows)
    return [image.crop((x0, y0, x1, y1)) for (y0, y1) in ys for (x0, x1) in xs]


def cut(grid, look, ids):
    """A kept grid cut into its games' screens: each saved as screen-<look>.png, with the grid it came from beside it
    (screen-<look>.source.txt), so --resplit knows which grid a screen is from when a game has been painted again."""
    with Image.open(grid) as image:
        panels = split(image.convert("RGB"), LOOKS[look][0])
    for game_id, panel in zip(ids, panels):
        folder = PAINTINGS / game_id
        folder.mkdir(parents=True, exist_ok=True)
        panel.save(folder / f"screen-{look}.png")
        (folder / f"screen-{look}.source.txt").write_text(grid.name + "\n", encoding="utf-8", newline="\n")


def resplit():
    """Cut every game's screens again from the grids they came from (each game's source.txt, else the newest grid
    holding it): after a change to split(), with no painting."""
    grids = PAINTINGS / "_grids"
    newest = {}
    for grid in sorted(grids.glob("*.png"), key=lambda p: p.stat().st_mtime):
        look, tag = grid.stem.split("-", 1)
        for game_id in tag.split("+"):
            newest[(game_id, look)] = grid
    done = 0
    for grid in sorted(grids.glob("*.png")):
        look, tag = grid.stem.split("-", 1)
        ids = tag.split("+")
        keep = []
        for game_id in ids:
            source = PAINTINGS / game_id / f"screen-{look}.source.txt"
            chosen = source.read_text(encoding="utf-8").strip() if source.exists() else newest[(game_id, look)].name
            keep.append(chosen == grid.name)
        if not any(keep):
            continue
        with Image.open(grid) as image:
            panels = split(image.convert("RGB"), LOOKS[look][0])
        for game_id, panel, wanted in zip(ids, panels, keep):
            if wanted:
                panel.save(PAINTINGS / game_id / f"screen-{look}.png")
                (PAINTINGS / game_id / f"screen-{look}.source.txt").write_text(grid.name + "\n", encoding="utf-8",
                                                                                newline="\n")
                print(f"{game_id}/screen-{look}: {panel.size[0]} x {panel.size[1]} from {grid.name}")
                done += 1
    print(f"Cut {done} screens again.")


def run_codex(codex, model, work, text):
    work.mkdir(parents=True, exist_ok=True)
    log = work / "codex.log"
    with open(log, "w", encoding="utf-8") as out:
        result = subprocess.run([codex, "exec", "-m", model, "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write",
                                 "-C", str(work), "-"], input=text, text=True, encoding="utf-8", stdout=out,
                                stderr=subprocess.STDOUT)
    return result.returncode, log.read_text(encoding="utf-8", errors="replace")


def paint(codex, model, run, stop):
    _, kind, cells = run
    if stop.is_set():
        return None
    if kind == "keyart":
        game = cells[0][0]
        name = "keyart.png"
        text = PREAMBLE.format(name=name) + game["keyart"]
        work = PAINTINGS / game["id"] / ".codex"
        label = f"{game['id']}/keyart"
    else:
        look = cells[0][1]
        name = "grid.png"
        tag = "+".join(g["id"] for g, _ in cells)
        text = PREAMBLE.format(name=name) + grid_prompt(cells)
        work = PAINTINGS / "_grids" / ".codex" / f"{look}-{tag}"
        label = f"{look} grid: {', '.join(g['id'] for g, _ in cells)}"
    code, log = run_codex(codex, model, work, text)
    made = work / name
    if code != 0 or not made.exists():
        refused = bool(REFUSED.search(log))
        if refused:
            stop.set()
        tail = " ".join(log.strip().splitlines()[-3:])[-300:]
        return f"FAILED {label}{' (refused: stopping)' if refused else ''}: {tail}"
    if kind == "keyart":
        folder = PAINTINGS / cells[0][0]["id"]
        shutil.move(str(made), folder / "keyart.png")
        (folder / "keyart.prompt.txt").write_text(text, encoding="utf-8", newline="\n")
    else:
        grids = PAINTINGS / "_grids"
        stem = f"{look}-{tag}"
        shutil.move(str(made), grids / f"{stem}.png")
        (grids / f"{stem}.prompt.txt").write_text(text, encoding="utf-8", newline="\n")
        cut(grids / f"{stem}.png", look, [g["id"] for g, _ in cells])
    shutil.rmtree(work, ignore_errors=True)
    try:
        work.parent.rmdir()                                  # _grids/.codex, once the last grid has gone
    except OSError:
        pass
    return f"{label}: done"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--games", help="only these games' ids, comma-separated")
    parser.add_argument("--jobs", type=int, default=4, help="Codex runs at once")
    parser.add_argument("--model", default="gpt-6.1-sol", help="the Codex model that calls the image tool")
    parser.add_argument("--dry-run", action="store_true", help="list the runs without painting")
    parser.add_argument("--resplit", action="store_true", help="cut the kept grids into screens again, painting nothing")
    args = parser.parse_args()
    if args.resplit:
        resplit()
        return
    codex = shutil.which("codex")
    if not codex and not args.dry_run:
        sys.exit("The Codex CLI isn't on PATH.")
    with open(HERE / "games.toml", "rb") as f:
        games = tomllib.load(f)["games"]
    runs = plan(needs(games, set(args.games.split(",")) if args.games else None))
    if not runs:
        print("Every painting is there already.")
        return
    print(f"{len(runs)} Codex runs:", flush=True)
    for _, kind, cells in runs:
        print(f"  {kind}: {', '.join(g['id'] + (f' ({look})' if look else '') for g, look in cells)}", flush=True)
    if args.dry_run:
        return
    (PAINTINGS / "_grids").mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    done = failed = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for line in pool.map(lambda r: paint(codex, args.model, r, stop), runs):
            if line is None:
                continue
            print(line, flush=True)
            done += line.endswith(": done")
            failed += line.startswith("FAILED")
    skipped = len(runs) - done - failed
    print(f"{done} runs painted, {failed} failed, {skipped} not started" + (" (Codex refused: stopped)" if stop.is_set() else ""))


if __name__ == "__main__":
    main()
