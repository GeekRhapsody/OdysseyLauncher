"""Makes the README's captures (docs/readme/) from the made-up library, so that no real game's art is shown:

    python tools/made-up-games/readme_captures.py [--only=<name>,...] [--setup] [--check] [--keep-frames]

First it builds a capture library (artifacts/made-up-games/readme/library/, again with --setup, or when missing): a copy
of make_games.py's library (its ROMs, gamelists and media) with empty ROMs for 24 more systems, so that the systems
screen shows their cards (named after the made-up games, never real ones; no capture enters those systems), and a few
favourites and some play history, written to userdata.db as L3 and playing would, so that the Favourites and Recently
played cards show without launching anything; then scanned and imported with odyssey-scrape (no network). The folder
is mapped to R: with subst while the script runs, so that the system details show R:\\ROMs\\megadrive and not the
folder's own path.

Then it records each capture (CAPTURES) in Godot's movie mode (--write-movie: a PNG for every frame at --fixed-fps 60,
1280 x 800), driven by --nav-script. --boot-frames holds boot to the same number of frames on every run (it otherwise
lasts as long as its background work takes, and the items' idle bob counts from the engine's start), and frames are
counted from the nav script's first step, whose frame the log names (a movie's frame n is the one the log calls frame
n). A still is one frame, saved as a JPEG; an animation is every fourth frame from a step to a while after the last, at
720 x 450 and 15 fps, saved as an animated WebP. Each capture starts from the library's own settings with its own
changes; the animations hide the clock, which shows the time of the run. --check records the animations twice and
compares their frames: only art streamed in on worker threads can arrive a frame apart. Last, a contact sheet of every
image (artifacts/made-up-games/readme/contact-sheet.jpg, and contact-sheet.html, which plays the animations).

Needs a built solution (dotnet build: the app and odyssey-scrape), Godot (GODOT, or godot.cmd on PATH) and Pillow.
Windowed: leave the machine alone while it runs (about fifteen minutes, and ten more with --check; movie mode runs at
about a fifth of real time).
"""
import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "artifacts" / "made-up-games" / "library"
WORK = REPO / "artifacts" / "made-up-games" / "readme"
LIBRARY = WORK / "library"
FRAMES = WORK / "frames"
OUT = REPO / "docs" / "readme"
SCRAPE = REPO / "tools" / "scrape-cli" / "bin" / "Debug" / "net8.0" / "odyssey-scrape.exe"
DRIVE = "R:"
USER_DIR = DRIVE + "\\"
STEP = 30          # frames between nav script steps (DebugOptions.NavScriptStepFrames)
BOOT = 90          # --boot-frames: boot lasts this many frames on every run (a few dozen in movie mode otherwise)
STILL = (1280, 800)
ANIMATION = (720, 450)
EVERY = 4          # 60 fps to 15

# The systems without made-up games, each with a few empty ROMs: a spread of makers and eras, each with its own
# console in the Console theme. Sorted by name after Favourites, Recently played and All games, five to a row, they
# put the Mega Drive in the middle of the fourth row.
PLACEHOLDERS = {
    "3do": (".chd", 2), "amiga": (".adf", 3), "amstradcpc": (".dsk", 2), "atari2600": (".a26", 2),
    "atarilynx": (".lnx", 2), "c64": (".d64", 3), "dreamcast": (".chd", 4), "gb": (".gb", 3), "gba": (".gba", 4),
    "gbc": (".gbc", 3), "gamegear": (".gg", 2), "gc": (".rvz", 3), "mastersystem": (".sms", 3), "neogeo": (".neo", 2),
    "nds": (".nds", 3), "nes": (".nes", 4), "pcengine": (".pce", 2), "psx": (".chd", 5), "ps2": (".chd", 4),
    "psp": (".cso", 3), "saturn": (".chd", 3), "zxspectrum": (".tzx", 3), "switch": (".xci", 3), "wii": (".rvz", 3),
}

# Favourites, and play history (plays, hours played, hours ago), by system and title.
FAVOURITES = [("megadrive", "Tidecaller Saga"), ("megadrive", "Redline Riviera"),
              ("snes", "Starhallow: The Sundered Crown"), ("n64", "Wyrmspire"), ("arcade", "Steel Lotus")]
PLAYED = [("megadrive", "Stormfist", 7, 4.2, 20), ("snes", "Mooncrest Chronicle", 3, 6.5, 50),
          ("n64", "Apex Circuit 64", 5, 2.1, 74), ("arcade", "Bubble Barrage", 12, 1.6, 97),
          ("megadrive", "Tidecaller Saga", 4, 9.3, 122), ("n64", "Whirligig Karts", 9, 3.4, 145)]

SETTINGS = {"paths": {"rom_root": f"{DRIVE}\\ROMs"}, "display": {"screen_mode": "windowed"}}
NO_CLOCK = {"ui": {"show_clock": False}}

# The systems screen starts on the first system, the 3DO, the fourth card of the first row (Favourites, Recently played
# and All games come first). These reach Recently played and All games (the grid stays at its top while the focus is
# on the first row), and the Mega Drive, in the middle of the fourth.
TO_RECENTLY_PLAYED = ["left", "left"]
TO_ALL_GAMES = ["left"]
TO_MEGADRIVE = ["down", "down", "down", "left"]


@dataclass
class Capture:
    """One image: a still (`after` frames after the nav script's last step) or an animation (from `lead` frames before
    step `start` to `after` frames after the last). `expect` is in the log's line for the last step."""
    name: str
    theme: str
    nav: list
    after: int
    args: list = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    expect: str = ""
    animation: bool = False
    start: int = 0
    lead: int = 0

    def output(self):
        return OUT / (self.name + (".webp" if self.animation else ".jpg"))


CAPTURES = [
    Capture("navigation", "console", ["wait", "left", "left", "down", "down", "down", "right", "wait", "wait", "wait",
                                      "wait", "accept", "wait", "right", "right", "down", "right"],
            after=45, settings=NO_CLOCK, expect="Kaleidrop", animation=True, lead=15),
    # Three turns (the stick right and a little up) bring the back round; more would tumble the box onto its edge.
    Capture("inspect", "console", ["wait", "zoom", "wait", "turn", "turn", "turn", "wait", "wait", "wait", "zoom"],
            after=45, args=["--start-system=megadrive", "--start-index=12"], settings=NO_CLOCK,
            expect="Redline Riviera", animation=True, start=1, lead=15),
    Capture("themes", "console", [*TO_RECENTLY_PLAYED, "wait", "wait", "theme", "wait", "wait", "wait", "wait", "theme",
                                  "wait", "wait", "wait", "wait", "theme", "wait", "wait"],
            after=0, settings=NO_CLOCK, expect="theme console", animation=True, start=3),
    Capture("systems-console", "console", [*TO_RECENTLY_PLAYED, "wait", "wait"], after=19, expect="Recently played"),
    Capture("systems-slab", "slab", [*TO_ALL_GAMES, "wait"], after=60, expect="All games"),
    Capture("systems-classic-view", "classic-view", ["wait"], after=60),
    Capture("games-megadrive", "console", ["wait", "wait"], after=30,
            args=["--start-system=megadrive", "--start-index=8"]),
    Capture("games-snes", "console", ["wait", "wait"], after=30, args=["--start-system=snes", "--start-index=7"]),
    Capture("games-arcade", "console", ["wait", "wait"], after=30, args=["--start-system=arcade", "--start-index=2"]),
    Capture("games-n64", "console", ["wait", "wait"], after=30, args=["--start-system=n64", "--start-index=7"]),
    Capture("layout-carousel", "console", ["wait", "wait"], after=30,
            args=["--start-system=snes", "--start-index=7", "--layout=grid/carousel"]),
    Capture("layout-list", "console", ["wait", "wait"], after=30,
            args=["--start-system=megadrive", "--start-index=6", "--layout=grid/list"]),
    Capture("game-details", "console", ["wait"], after=30,
            args=["--start-system=megadrive", "--start-index=17", "--open=details"]),
    Capture("game-options", "console", ["wait", "x"], after=30, args=["--start-system=megadrive", "--start-index=17"]),
    Capture("system-details", "console", [*TO_MEGADRIVE, "y"], after=60, expect="Mega Drive"),
]


def run(args, **kwargs):
    print(">", " ".join(str(a) for a in args), flush=True)
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def godot():
    found = os.environ.get("GODOT") or shutil.which("godot.cmd") or shutil.which("godot")
    if not found:
        raise SystemExit("No Godot: set GODOT, or put godot.cmd on PATH (CLAUDE.md).")
    return found


def map_drive():
    """Maps DRIVE to the capture library (subst: this logon session only, until unmap_drive)."""
    if Path(USER_DIR).exists():
        mapped = subprocess.run(["subst"], capture_output=True, text=True).stdout
        if f"{DRIVE}\\: => {LIBRARY}".lower() not in mapped.lower():
            raise SystemExit(f"{DRIVE} is in use by something else; change DRIVE in {Path(__file__).name}.")
        return
    run(["subst", DRIVE, LIBRARY])


def unmap_drive():
    subprocess.run(["subst", DRIVE, "/d"], capture_output=True)


def write_settings(extra):
    """The library's settings.toml: SETTINGS with a capture's changes (tables of plain values only)."""
    tables = {name: dict(values) for name, values in SETTINGS.items()}
    for name, values in extra.items():
        tables.setdefault(name, {}).update(values)

    def value(v):
        return ("true" if v else "false") if isinstance(v, bool) else f"'{v}'" if isinstance(v, str) else str(v)

    text = "\n".join(f"[{name}]\n" + "".join(f"{k} = {value(v)}\n" for k, v in values.items())
                     for name, values in tables.items())
    (LIBRARY / "settings.toml").write_text(text, encoding="utf-8", newline="\n")


def setup():
    """Builds the capture library from make_games.py's: copies, placeholder ROMs, scan, import, favourites and plays."""
    if not (SOURCE / "ROMs").is_dir():
        raise SystemExit(f"No made-up library in {SOURCE}: run make_games.py and import it first (its README).")
    unmap_drive()
    if LIBRARY.exists():
        shutil.rmtree(LIBRARY)
    LIBRARY.mkdir(parents=True)
    shutil.copytree(SOURCE / "ROMs", LIBRARY / "ROMs")
    shutil.copytree(SOURCE / "media", LIBRARY / "media")
    write_settings({})

    titles = [g["title"] for g in tomllib.load(open(HERE / "games.toml", "rb"))["games"]]
    n = 0
    for system, (extension, count) in PLACEHOLDERS.items():
        folder = LIBRARY / "ROMs" / system
        folder.mkdir()
        for _ in range(count):
            (folder / (titles[n % len(titles)].replace(": ", " - ") + " (Europe)" + extension)).touch()
            n += 7  # a stride prime to the titles' count, so a system's games are different ones

    map_drive()
    run([SCRAPE, f"--user-dir={USER_DIR}", "scan"])
    for system in ["megadrive", "snes", "n64", "arcade"]:
        run([SCRAPE, f"--user-dir={USER_DIR}", "import-gamelist", system])

    library = sqlite3.connect(LIBRARY / "library.db")
    library.execute("ATTACH ? AS user", (str(LIBRARY / "userdata.db"),))

    def key(system, title):
        row = library.execute(
            "SELECT g.path_key FROM games g LEFT JOIN user.game_overrides o"
            " ON o.system_id = g.system_id AND o.path_key = g.path_key"
            " WHERE g.system_id = ? AND COALESCE(o.title, g.title) = ?", (system, title)).fetchone()
        if row is None:
            raise SystemExit(f"No {title} on {system} in the library.")
        return row[0]

    now = int(time.time() * 1000)
    hour = 3_600_000
    with library:
        for i, (system, title) in enumerate(FAVOURITES):
            library.execute("INSERT OR REPLACE INTO user.favourites VALUES (?, ?, ?)",
                            (system, key(system, title), now - (200 + i) * hour))
        for system, title, plays, hours, ago in PLAYED:
            library.execute("INSERT OR REPLACE INTO user.play_stats VALUES (?, ?, ?, ?, ?)",
                            (system, key(system, title), plays, round(hours * 3600), now - ago * hour))
    library.close()


def record(capture, folder):
    """Runs the capture in movie mode into folder; returns the frames of its nav script's steps, from the log."""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    write_settings(capture.settings)
    last = (len(capture.nav) - 1) * STEP + capture.after
    # The warm-up and the nav script's first step take a few dozen frames after boot; the capture only ends the run.
    frames = BOOT + 100 + last
    result = subprocess.run(
        [godot(), "--path", REPO / "godot", "--resolution", f"{STILL[0]}x{STILL[1]}", "--fixed-fps", "60",
         "--write-movie", folder / "f.png", "--",
         f"--user-dir={USER_DIR}", f"--theme={capture.theme}", "--fake-status=96+/wifi3", f"--boot-frames={BOOT}",
         "--nav-script=" + ",".join(capture.nav), *capture.args,
         f"--capture={folder / 'end.png'}", f"--capture-frame={frames}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = result.stdout + result.stderr
    (folder / "log.txt").write_text(log, encoding="utf-8")
    steps = [(int(m.group(2)), m.group(1)) for m in re.finditer(r"^Nav script: (.*) \(frame (\d+)\)$", log, re.M)]
    if result.returncode != 0 or len(steps) != len(capture.nav):
        raise SystemExit(f"{capture.name}: the run failed (exit {result.returncode}, {len(steps)} of "
                         f"{len(capture.nav)} steps); see {folder / 'log.txt'}.")
    if capture.expect not in steps[-1][1]:
        raise SystemExit(f"{capture.name}: the last step ended on '{steps[-1][1]}', not '{capture.expect}'.")
    for (a, _), (b, _) in zip(steps, steps[1:]):
        if b - a != STEP:
            raise SystemExit(f"{capture.name}: steps {STEP} frames apart expected, got {b - a}.")
    return [frame for frame, _ in steps]


def frames_of(capture, steps):
    """The movie frames the image is made of."""
    if not capture.animation:
        return [steps[-1] + capture.after]
    return list(range(steps[capture.start] - capture.lead, steps[-1] + capture.after + 1, EVERY))


def load(folder, n):
    return Image.open(folder / f"f{n:08d}.png").convert("RGB")


def save(capture, folder, steps):
    frames = frames_of(capture, steps)
    path = capture.output()
    if not capture.animation:
        load(folder, frames[0]).save(path, quality=90, optimize=True, progressive=True)
    else:
        images = [load(folder, n).resize(ANIMATION, Image.LANCZOS) for n in frames]
        images[0].save(path, save_all=True, append_images=images[1:], duration=round(1000 * EVERY / 60), loop=0,
                       quality=80, method=6)
    print(f"{path.relative_to(REPO)}: {len(frames)} frame(s), {path.stat().st_size / 1024:,.0f} KB", flush=True)


def compare(capture, first, second, steps_a, steps_b):
    """The animation's frames from two runs, as their largest difference (0 to 255) and how many frames differ."""
    worst, differing = 0, 0
    for a, b in zip(frames_of(capture, steps_a), frames_of(capture, steps_b)):
        diff = np.abs(np.asarray(load(first, a), np.int16) - np.asarray(load(second, b), np.int16))
        worst = max(worst, int(diff.max()))
        differing += int(diff.any())
    return worst, differing, len(frames_of(capture, steps_a))


def contact_sheet(captures):
    """Every image, small: an animation as eight of its frames in a row, then the stills, four to a row."""
    font = ImageFont.load_default(size=15)
    rows, stills = [], []
    for capture in captures:
        image = Image.open(capture.output())
        if not capture.animation:
            stills.append((capture.output().name, image.convert("RGB").resize((390, 244))))
            continue
        # The encoder merges a run of identical frames into one, so the length is the frames' durations added up.
        n = image.n_frames
        seconds = 0
        for i in range(n):
            image.seek(i)
            image.load()
            seconds += image.info.get("duration", 0) / 1000
        strip = Image.new("RGB", (8 * 198 - 4, 121), "#202020")
        for j in range(8):
            image.seek(round(j * (n - 1) / 7))
            strip.paste(image.convert("RGB").resize((194, 121)), (j * 198, 0))
        rows.append([(f"{capture.output().name}: {seconds:.1f} s", strip)])
    rows += [stills[i:i + 4] for i in range(0, len(stills), 4)]
    sheet = Image.new("RGB", (8 + 4 * 398, 8 + sum(24 + row[0][1].height + 8 for row in rows)), "#202020")
    draw = ImageDraw.Draw(sheet)
    y = 8
    for row in rows:
        for i, (label, image) in enumerate(row):
            draw.text((8 + i * 398, y + 4), label, fill="#E0E0E0", font=font)
            sheet.paste(image, (8 + i * 398, y + 24))
        y += 24 + row[0][1].height + 8
    sheet.save(WORK / "contact-sheet.jpg", quality=88)
    figures = "".join(f'<figure><img src="../../../docs/readme/{c.output().name}"><figcaption>{c.output().name}'
                      f"</figcaption></figure>\n" for c in captures)
    (WORK / "contact-sheet.html").write_text(
        "<!doctype html><meta charset=utf-8><title>README captures</title><style>body{background:#202020;color:#ddd;"
        "font:14px sans-serif;display:flex;flex-wrap:wrap;gap:12px}img{width:640px}</style>\n" + figures,
        encoding="utf-8")
    print(f"{(WORK / 'contact-sheet.jpg').relative_to(REPO)} and contact-sheet.html beside it", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--only", help="these captures only (names, comma-separated)")
    parser.add_argument("--setup", action="store_true", help="build the capture library again")
    parser.add_argument("--check", action="store_true", help="record each animation twice and compare the frames")
    parser.add_argument("--keep-frames", action="store_true", help=f"keep each run's movie frames in {FRAMES}")
    args = parser.parse_args()
    captures = CAPTURES if not args.only else [c for c in CAPTURES if c.name in args.only.split(",")]
    try:
        if args.setup or not (LIBRARY / "library.db").exists():
            setup()
        map_drive()
        OUT.mkdir(parents=True, exist_ok=True)
        for capture in captures:
            folder = FRAMES / capture.name
            steps = record(capture, folder)
            save(capture, folder, steps)
            if args.check and capture.animation:
                again = FRAMES / (capture.name + "-again")
                steps_again = record(capture, again)
                worst, differing, total = compare(capture, folder, again, steps, steps_again)
                print(f"{capture.name}: {differing} of {total} frames differ between two runs (largest difference "
                      f"{worst} of 255; the nav script started on frames {steps[0]} and {steps_again[0]})", flush=True)
                if not args.keep_frames:
                    shutil.rmtree(again)
            if not args.keep_frames:
                shutil.rmtree(folder)
        write_settings({})
        contact_sheet([c for c in CAPTURES if c.output().exists()])
    finally:
        unmap_drive()


if __name__ == "__main__":
    main()
