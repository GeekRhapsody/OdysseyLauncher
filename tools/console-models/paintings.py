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
VGA_GAME = ("From a fictional 1992 DOS side-scrolling helicopter action game for VGA PCs, painted in the style of the "
            "256-colour VGA game art of the time (rich painted pixels, a slightly limited palette, crisp edges): ")
ON_GREEN = (" Every panel's background is the same plain flat pure green (#00FF00), with no floor, shadow, scenery or "
            "lines between the panels, so they can be cut out.")
RACER_98 = "From a fictional 1998 3D open-wheel racing game for Windows PCs, in the pre-rendered 3D style of the time: "
GULCH_GAME = ("a fictional 2020s high-definition remake of an arcade light-gun western shooting game, as bright and "
              "glossy as modern cartoon-styled 3D games (stylised characters, warm sunset light, clean detailed "
              "rendering)")
HD_GULCH = "From " + GULCH_GAME + ": "
HD_GULCH_GRID = (" in a 2x2 grid of four equal square panels, each whole with a margin round it, facing the viewer, "
                 "stylised modern 3D rendering in warm sunset light." + ON_GREEN)
PAINTINGS = {
    # The DOS card's game, Rotorstorm: its layers and sprites (dos_screens.py).
    "dos_rotor_sky": VGA_GAME + "the far background layer: a stormy dusk sky over a jungle river valley, dark purple "
    "and teal clouds lit orange along the horizon, one distant fork of lightning, jungle-covered mountains far away "
    "and a small island fortress with searchlights on a crag in the far distance; the lowest fifth is the river's far "
    "bank and a band of distant jungle. Seen side-on, nothing near. Landscape, three times as wide as it is tall.",
    "dos_rotor_ground": VGA_GAME + "the near layer, seen side-on: a strip of dense jungle along a muddy riverbank "
    "across the bottom third only, palm trees and broad-leaved bushes, a wooden hut on stilts, a sandbagged gun "
    "emplacement and a red oil drum standing along it; everything above the jungle is plain flat pure green "
    "(#00FF00), no other colour, so it can be cut out. Landscape, four times as wide as it is tall.",
    "dos_rotor_sprites": "Four sprites " + VGA_GAME.lower() + "in a 2x2 grid of four equal square panels, each whole "
    "with a margin round it, seen exactly side-on. Top left: the player's grey attack helicopter of an original "
    "design flying to the right, rocket pods under its stub wings, its main rotor a thin blurred disc seen edge-on. "
    "Top right: an enemy olive-green helicopter flying to the left. Bottom left: a small olive military jeep with a "
    "mounted gun, facing left. Bottom right: a fiery orange explosion with black smoke." + ON_GREEN,
    # The Windows 3.x card's game, Spellbrick (windows3x_screens.py).
    "w3x_spell_title": "The title painting of a fictional 1993 brick-breaking game for Windows 3.1, in the style of "
    "the dithered 256-colour VGA art of the time: a little wizard in a starry purple robe and a pointed hat stands on "
    "a floating grey stone slab, a glowing white orb bouncing above him towards a wall of glowing coloured enchanted "
    "bricks built into the shape of a castle with two towers, a purple night sky with sparkles. Keep the top third "
    "plain night sky: a title will be written there later. Landscape 4:3.",
    "w3x_spell_sprites": "Four sprites from a fictional 1993 brick-breaking game for Windows 3.1, in the style of the "
    "256-colour VGA art of the time, in a 2x2 grid of four equal square panels, each whole with a margin round it, "
    "seen side-on. Top left: a little wizard in a starry purple robe and a pointed hat standing on a long, flat, "
    "floating grey stone slab, as wide as four of him, his arms raised. Top right: a glowing white orb with a pale "
    "blue halo. Bottom left: a small round potion bottle of glowing green liquid with a cork. Bottom right: a small "
    "round potion bottle of glowing red liquid with a cork." + ON_GREEN,
    # The Windows 9x card's game, Apex Circuit (windows9x_screens.py).
    "w9x_apex_horizon": RACER_98 + "the distant backdrop the track is drawn against: a sunny Mediterranean coast, a "
    "blue sea with a few white sailing boats at the left, a hillside town of pastel houses with terracotta roofs and "
    "a church tower in the middle, green hills and grey mountains behind, a bright blue sky with a few white clouds; "
    "the lowest tenth a band of distant green trees. Flat and side-on, no road, no cars, no people. Landscape, four "
    "times as wide as it is tall, its left and right edges matching so that it wraps round.",
    "w9x_apex_cars": "Four sprites " + RACER_98.lower() + "in a 2x2 grid of four equal square panels, each car whole "
    "with a margin round it, no sponsors' names, badges or numbers. Top left: a red-and-white open-wheel racing car "
    "of an original design seen exactly from behind, a little from above, as the player's car is seen in the game: "
    "its rear wing, its fat rear tyres. Top right: the same car from behind and above, steering left. Bottom left: a "
    "blue-and-white rival car from behind and above. Bottom right: a yellow-and-black rival car from behind and "
    "above." + ON_GREEN,
    "w9x_apex_props": "Four roadside objects " + RACER_98.lower() + "in a 2x2 grid of four equal square panels, each "
    "whole with a margin round it, seen from the front at eye level, no lettering. Top left: a tall palm tree. Top "
    "right: a dark green cypress tree. Bottom left: a stack of black tyres, a crash barrier. Bottom right: a small "
    "white-and-blue spectators' grandstand with a canopy." + ON_GREEN,
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
    # The Windows card's game, Wyrmspire, remastered (windows_pc_print.py).
    "win_title": "Key art for the title screen of a fictional 2020s high-definition remaster of a 3D fantasy action "
    "adventure, as glossy and detailed as modern game key art: an impossibly tall stone spire rising out of a misty "
    "forested valley at dawn, a huge emerald dragon asleep coiled round it, waterfalls, a griffin far off, golden "
    "light breaking through the clouds. No people. Keep the spire and the dragon in the right half and the left third "
    "darker and calm: a title and a menu will be printed there later. Landscape 3:2.",
    "win_vale": "A screenshot from a fictional 2020s high-definition remaster of a 3D fantasy action adventure, "
    "exactly as it runs on a modern PC: detailed modern 3D rendering, soft volumetric morning light, and no interface "
    "and no people at all: the camera low behind a winding grassy path that runs from the bottom middle of the "
    "picture into a vast green valley of forests, waterfalls and ruined stone temples, an impossibly tall stone spire "
    "far off in the middle with a huge emerald dragon asleep coiled round it, blue mountains and soft clouds behind. "
    "Keep the bottom middle clear: the hero will be drawn there later. Landscape 3:2.",
    "win_hero": "Four poses of one original character from a fictional 2020s high-definition 3D fantasy action "
    "adventure, in a 2x2 grid of four equal square panels, each pose whole from head to feet with a margin round it, "
    "seen from behind and a little above as the game's camera follows her, detailed modern 3D rendering in warm "
    "morning light. Every panel's background is the same plain flat pure green (#00FF00), with no floor, shadow, "
    "scenery or lines between the panels, so the figures can be cut out. The character: a young woman with a long "
    "brown braid in a dark blue travelling cloak, a leather satchel and boots, carrying a long spear. Top left: "
    "running away from the camera, her left foot forward. Top right: running away from the camera, her right foot "
    "forward. Bottom left: standing ready, her back to the camera, her spear held across her body. Bottom right: "
    "lunging away from the camera into a spear thrust, the spear driving forward past her right shoulder.",
    "win_beast": "Four poses of one original creature from a fictional 2020s high-definition 3D fantasy action "
    "adventure, in a 2x2 grid of four equal square panels, each pose whole with a margin round it, facing the camera, "
    "detailed modern 3D rendering in warm morning light. Every panel's background is the same plain flat pure green "
    "(#00FF00), with no floor, shadow, scenery or lines between the panels, so the figures can be cut out. The "
    "creature: a hulking wolf-like beast as big as a horse, its back covered in moss and plates of grey stone, "
    "glowing amber eyes. Top left: prowling towards the camera, its head low. Top right: rearing up with a roar, its "
    "front paws raised. Bottom left: reeling back from a blow, its head thrown aside, a burst of light where it was "
    "struck. Bottom right: collapsed on its side on the ground, beaten.",
    # The Switch 2 card's game, Dusty Gulch (tools/made-up-games) remade in HD and aimed with a Joy-Con 2 used as a
    # mouse (switch2_print.py): the empty street, its outlaws and props cut out of their green, and its key art.
    "sw2_gulch_street": HD_GULCH + "the first-person view straight down the middle of the dusty main street of a small "
    "Wild West town at sunset, at eye level, with no people at all: a two-storey wooden saloon with a balcony and an "
    "open upstairs window on the left, a general store with a porch on the right, barrels and crates along both sides, "
    "a wooden water tower further down, red rock mesas and a big low orange sun far away at the end of the street, an "
    "empty wooden fence rail in the right foreground and a barrel in the left foreground. Leave the top tenth as plain "
    "warm sky: the score will be drawn over it later. Landscape 3:2.",
    "sw2_gulch_outlaws": "Four poses of two original cartoonish outlaws from " + GULCH_GAME + ", each from the waist "
    "up," + HD_GULCH_GRID + " Top left: a burly outlaw with a bushy black beard, a black hat, a red bandana round his "
    "neck and a brown leather waistcoat, aiming a revolver straight at the viewer. Top right: the same burly outlaw "
    "hit, thrown backwards with his eyes squeezed shut and his hat flying off. Bottom left: a skinny outlaw with a long "
    "ginger moustache, a battered brown hat and a blue shirt, aiming a revolver at the viewer. Bottom right: the same "
    "skinny outlaw hit, reeling backwards with his eyes squeezed shut and his hat flying off.",
    "sw2_gulch_props": "Four objects from " + GULCH_GAME + "," + HD_GULCH_GRID + " Nothing green "
    "anywhere. Top left: a dark brown glass bottle standing upright. Top right: a pale blue glass bottle standing "
    "upright. Bottom left: a brown glass bottle bursting apart into flying shards. Bottom right: a battered brown "
    "cowboy hat tumbling through the air.",
    "sw2_gulch_keyart": "Key art for the title screen of a fictional 2020s high-definition remake of an arcade "
    "light-gun western shooting game, as glossy and detailed as modern cartoon-styled game key art: a brave young "
    "sheriff of an original design, in a wide tan hat and a waistcoat with a star on it, her revolver raised, standing "
    "in the dusty main street of a Wild West town at sunset, two cartoonish outlaws peeking out from behind a barrel "
    "and a saloon window, a big low orange sun and red rock mesas behind. Keep the top third calm warm sky: a title "
    "will be printed there later. Landscape 3:2.",
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
