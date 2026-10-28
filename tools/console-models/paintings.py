"""Commissions the console theme's paintings from Codex (its built-in image tool), from the prompts below, into
artifacts/console-paintings/<name>.png, each with its prompt beside it (<name>.prompt.txt). Only missing paintings are
made, so delete one to have it painted again. The cards' print scripts read them (arcade_print.py, ...).

    python tools/console-models/paintings.py [--only=<name>,...] [--jobs=4] [--model=gpt-6.1-sol] [--dry-run]

Every painting is made up: no real game, character, company or artwork. Needs the Codex CLI, logged in (a ChatGPT
account will do); a run takes about a minute. The paintings aren't reproducible, so keep them: everything the print
scripts make from them is. Codex works in artifacts/console-paintings/.codex/, made with a plain mkdir so the files its
sandbox writes inherit the user's rights (a folder made by tempfile.mkdtemp gets an owner-only ACL, and they couldn't
be read back).
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "artifacts" / "console-paintings"
REFUSED = re.compile(r"usage limit|rate limit|quota|too many requests|\b429\b|limit reached|try again later", re.I)

PREAMBLE = """Use your built-in image generation tool to create exactly one image, and save it as a PNG file named \
painting.png in the current working directory. Do nothing else: don't create or edit any other files.

No text, letters, numbers, logos, signatures, borders or watermarks anywhere in the image. Original designs only: \
don't imitate any existing game, character, film, artwork, company or franchise.

The image: """

LASERDISC = ("A single frame from a fictional 1983 laserdisc arcade game, exactly like hand-drawn, hand-painted 1980s "
             "feature animation shown on a 4:3 arcade monitor: ")
SIDE_ART = ("Side art for the side panel of a fictional early-1980s American arcade cabinet, exactly like the "
            "silk-screened cabinet art of the time: bold flat colours, thick black outlines, a little halftone "
            "shading, one big illustration standing tall in a portrait panel on a plain ")
PORTRAIT = " Tall portrait, the figures filling the frame, a plain margin of the background all round."
HD_FIGHTER = ("A screenshot from a fictional 2010s high-definition 3D fighting game, exactly as it ran: detailed "
              "modern 3D rendering, dynamic neon lighting, and no interface at all (no health bars, no timer, no "
              "names): ")
HD_POSES = ("Four poses of one original character from a fictional 2010s high-definition 3D fighting game, in a 2x2 "
            "grid of four equal square panels, each pose whole from head to feet with a margin round it, seen from "
            "the side as the game's camera sees the fighters, detailed modern 3D rendering lit by cyan and red neon. "
            "Every panel's background is the same plain flat pure green (#00FF00), with no floor, shadow, scenery or "
            "lines between the panels, so the figures can be cut out. The character: ")
PAINTINGS = {
    # Daphne's card: its screen plays the laserdisc's frames.
    "daphne_frame1": LASERDISC + "a brave, slightly clumsy young knight in bright silver armour with a red plume leaps "
    "across a crumbling stone bridge in a cavernous castle dungeon, glowing orange lava far below, the arch behind him "
    "collapsing; warm torchlight, rich painted backgrounds, clean ink outlines on the character, cel shading. "
    "Landscape 4:3.",
    "daphne_frame2": LASERDISC + "the same kind of young knight in silver armour with a red plume backs away in alarm "
    "as a huge green dragon with amber eyes rears up over a heap of gold coins in a vast treasure cave, smoke curling "
    "from its nostrils; warm golden light on the gold, deep shadows, rich painted background, clean ink outlines on "
    "the characters, cel shading. Landscape 4:3.",
    "daphne_attract": LASERDISC + "the title scene: a towering dark castle on a crag at dusk, lightning behind its "
    "spires, a winding road up to its gate, painted clouds lit purple and orange; dramatic and inviting, nothing "
    "written anywhere. Landscape 4:3.",
    "daphne_side": "Side art for the side panel of a fictional 1983 laserdisc arcade game's cabinet, hand-painted in "
    "the style of the fantasy animation of the time, in glowing yellows, oranges and greens on a plain black "
    "background: a crooked stone tower rising through smoke, a long red dragon coiled round it with its wings "
    "spread, a small knight at its foot holding up a lantern and a sword." + PORTRAIT,
    # The arcade and MAME cards' cabinets carry their made-up game's side art (tools/made-up-games's games).
    "side_musemyhm": SIDE_ART + "deep red background: a cheeky cartoon cat burglar in a striped jumper and a black "
    "eye mask tiptoes along with a bulging sack over his shoulder, a towering dinosaur skeleton and a golden "
    "sarcophagus looming behind him in a museum at night, a guard's torch beam sweeping past." + PORTRAIT,
    "side_hivehstl": SIDE_ART + "black background: a chubby cartoon honeybee with huge eyes and a wide grin zooms "
    "through a maze of golden honeycomb, two grumpy wasps giving chase, drops of honey flying." + PORTRAIT,
    # OpenBOR's card: its oil drum, as beat 'em ups have them, its dragon spray-painted on.
    "openbor_drum": "The unrolled side of a battered steel oil drum, seen flat and front-on with no perspective, to "
    "wrap round a 3D model: slate-blue paint worn through to bare metal and rust along streaks, scratches and dents, two "
    "darker horizontal bands where its rolling hoops are, a third of the way down and a third of the way up; across "
    "its middle a big original blue dragon, side-on, roaring, wings swept back, spray-painted on in a rough graffiti "
    "stencil style with overspray. It must wrap seamlessly: its left and right edges meet. Landscape, three times as "
    "wide as it is tall.",
    # Future Pinball's card: a pinball machine's playfield and backglass.
    "fpinball_playfield": "The playfield of a fictional 1990s pinball machine, seen from directly above, flat and "
    "front-on with no perspective, as printed art with none of its parts fitted (no flippers, bumpers, ramps or "
    "ball): a deep-space theme in purples, blues and glowing greens, painted lanes with round and arrow-shaped lamp "
    "inserts along them, a big ringed planet and a rocket in the upper half, curving orbit lanes, two inlanes and "
    "outlanes at the bottom. Portrait, exactly twice as tall as it is wide.",
    "fpinball_backglass": "The backglass of a fictional 1990s pinball machine: a sleek silver rocket blasting off "
    "past a giant ringed green planet, little round alien saucers with glowing green lights, stars and a nebula "
    "behind, in the airbrushed style of the pinball backglasses of the time, a dark band left clear across the top "
    "for a title. Square.",
    # The PS Vita card: its screen plays Voltcrown (tools/made-up-games), its fighters cut out of the poses (on green)
    # and moved over the empty arena, as a 2.5D fighting game draws them; the key art is its LiveArea and its bubble.
    "vita_arena": HD_FIGHTER + "the empty arena, with no fighters in it: a rain-soaked rooftop in a neon megacity at "
    "night, seen from the side at a fighter's height, the flat roof running the whole width of the picture with a low "
    "railing along its far edge, skyscrapers behind with holographic billboards of abstract shapes (a cyan triangle, "
    "a red crescent) and no lettering, rain falling, puddles on the concrete reflecting the cyan and red lights. Leave "
    "the middle of the roof clear: the fighters will be drawn over it later. Landscape 3:2.",
    "vita_juno": HD_POSES + "a lanky young man with a shaved head, glowing cyan circuit tattoos down his bare forearms, "
    "a cropped black jacket, black cargo trousers and black boots, facing right. Top left: his fighting stance, fists "
    "up, weight on his back foot. Top right: a straight punch, his right arm out at full stretch. Bottom left: a high "
    "kick, his leading leg out straight at head height. Bottom right: his finisher, both fists thrust forward, cyan "
    "lightning crackling along his arms and bursting from his fists.",
    "vita_sable": HD_POSES + "a tall woman in sleek white armour plating over a black bodysuit, a red visor across her "
    "eyes, long black hair, short glowing red energy blades on her forearms, facing left. Top left: her fighting "
    "stance, her blades raised. Top right: a slash with her right blade. Bottom left: reeling backwards from a blow, "
    "her head thrown back. Bottom right: knocked down, lying on her side on the ground, beaten.",
    "vita_keyart": "Key art for a fictional 2014 high-definition 3D fighting game, as glossy as the game box and poster "
    "art of the time: two original fighters face off on a rain-soaked rooftop in a neon megacity at night. On the left "
    "a lanky young man with a shaved head, glowing cyan circuit tattoos down his forearms and a cropped black jacket, "
    "cyan electricity crackling round his fists; on the right a tall woman in sleek white armour with a red visor and "
    "short red energy blades on her forearms. Holographic billboards of abstract shapes behind them, rain and neon "
    "reflections. Keep the fighters in the lower two thirds and the top third dark and open: a title will be printed "
    "there later. Landscape 3:2.",
}


def paint(codex, model, name, stop):
    if stop.is_set():
        return None
    work = OUT / ".codex" / ("run_" + uuid.uuid4().hex[:8])
    work.mkdir(parents=True)                      # a plain mkdir: see the docstring
    text = PREAMBLE + PAINTINGS[name]
    with open(work / "codex.log", "w", encoding="utf-8") as log:
        result = subprocess.run([codex, "exec", "-m", model, "--skip-git-repo-check", "--ephemeral", "-s",
                                 "workspace-write", "-C", str(work), "-"], input=text, text=True, encoding="utf-8",
                                stdout=log, stderr=subprocess.STDOUT)
    made = work / "painting.png"
    if result.returncode != 0 or not made.exists():
        log = (work / "codex.log").read_text(encoding="utf-8", errors="replace")
        refused = bool(REFUSED.search(log))
        if refused:
            stop.set()
        tail = " ".join(log.strip().splitlines()[-3:])[-300:]
        return f"FAILED {name}{' (refused: stopping)' if refused else ''}: {tail}"
    for _ in range(30):                           # the file can stay locked a moment after Codex exits
        try:
            shutil.copyfile(made, OUT / f"{name}.png")
            break
        except PermissionError:
            time.sleep(1)
    else:
        return f"FAILED {name}: couldn't copy {made}"
    (OUT / f"{name}.prompt.txt").write_text(text, encoding="utf-8", newline="\n")
    shutil.rmtree(work, ignore_errors=True)
    return f"{name}: done"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="only these paintings, comma-separated")
    parser.add_argument("--jobs", type=int, default=4, help="Codex runs at once")
    parser.add_argument("--model", default="gpt-6.1-sol", help="the Codex model that calls the image tool")
    parser.add_argument("--dry-run", action="store_true", help="list the paintings missing without painting")
    args = parser.parse_args()
    names = [n for n in PAINTINGS if (not args.only or n in args.only.split(",")) and not (OUT / f"{n}.png").exists()]
    if not names:
        print("Every painting is there already.")
        return
    print(f"{len(names)} to paint: {', '.join(names)}", flush=True)
    if args.dry_run:
        return
    codex = shutil.which("codex")
    if not codex:
        sys.exit("The Codex CLI isn't on PATH.")
    OUT.mkdir(parents=True, exist_ok=True)
    import threading
    stop = threading.Event()
    with ThreadPoolExecutor(args.jobs) as pool:
        for line in pool.map(lambda n: paint(codex, args.model, n, stop), names):
            if line:
                print(line, flush=True)


if __name__ == "__main__":
    main()
