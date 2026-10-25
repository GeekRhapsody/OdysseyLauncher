# Made-up games

Art for the README's captures (`docs/readme/`), so that no real game's art is shown: invented games with their covers,
backs, spines, cartridge labels, logos and screenshots, in a portable user folder the app runs with. Every name,
company, character and picture is made up (docs/ARCHITECTURE.md, decisions log, 2026-10-25).

The paintings (each game's key art and its screens) come from Codex's image tool. Everything else is drawn by these
scripts from the paintings, the same on every run: the logos, each system's packaging, the HUDs and every word.

## What there is

39 game concepts and 59 releases: 20 Mega Drive, 15 SNES, 12 N64 and 12 arcade. A concept can come out on several
systems (Stormfist is on all four), each release with its own box. To list them:

```powershell
python -c "import tomllib; [print(g['id'], g['genre'], [v['system'] for v in g['versions']]) for g in tomllib.load(open('tools/made-up-games/games.toml','rb'))['games']]"
```

| System | Cover | Back | Spine | Label | Screenshot | The app's template |
|---|---|---|---|---|---|---|
| Mega Drive | 968 × 1360 | 962 × 1360 | 162 × 1360 | 1036 × 700 | 320 × 224 | `megadrive_clamshell` |
| SNES | 1360 × 994 | 1360 × 994 | 1360 × 194 (top) | 1120 × 700 | 256 × 224 | `snes_box_horizontal` |
| N64 | 1360 × 994 | 1360 × 994 | 1360 × 194 (top) | 1085 × 700 | 320 × 240 | `generic_box_top_spine` |
| Arcade | | | | | 320 × 224, or 224 × 288 for a vertical game | `arcade_cabinet` (the logo on the marquee) |

Every release also has a logo (a transparent PNG). The box sizes are twice ScreenScraper's scans, so the art fits the
templates' faces without cropping. Covers, backs, spines and labels are JPEGs; logos and screenshots PNGs. Not made:
heroes (a 1920 × 620 cut of the key art; dropped as not needed), videos and manuals.

## The process

1. **Describe the game** in [games.toml](games.toml): its details, its box copy, its logo, its releases and two kinds
   of prompt (below).
2. **Paint** what's missing: `python tools/made-up-games/codex_art.py` (`--dry-run` lists the runs first). The
   paintings go to `artifacts/made-up-games/paintings/<game>/`, each with its prompt beside it.
3. **Look at every painting** (below, "Rules"). Repaint any that fails.
4. **Make** every piece: `python tools/made-up-games/make_games.py` (about 90 s for all 59). It writes the library and
   the review sheets.
5. **Review** `artifacts/made-up-games/sheets/<system>-<kind>.jpg` (every game's piece of one kind side by side).
6. **Bring them into the app**, once, from the repo root (the library's `README.txt` has the exact lines):
   ```powershell
   .\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe --user-dir=$PWD\artifacts\made-up-games\library scan
   .\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe --user-dir=$PWD\artifacts\made-up-games\library import-gamelist megadrive
   ```
   and `import-gamelist` for `snes`, `n64` and `arcade` too. Run `scan` again after making new pieces.
7. **Capture** (CLAUDE.md, "Debug facilities"), for example:
   ```powershell
   $lib = "$PWD\artifacts\made-up-games\library"
   godot --path godot --resolution 1280x800 --fixed-fps 60 -- "--user-dir=$lib" --start-system=megadrive "--capture=$PWD\artifacts\made-up-games\captures\megadrive.png" --capture-frame=240
   godot --path godot --resolution 1280x800 --fixed-fps 60 -- "--user-dir=$lib" --start-system=megadrive --start-index=3 --nav-script=zoom,wait,turn,turn,turn,turn,wait "--capture=$PWD\artifacts\made-up-games\captures\inspect.png" --capture-frame=215
   godot --path godot --resolution 1280x800 --fixed-fps 60 -- "--user-dir=$lib" --start-system=n64 --start-index=11 --open=details "--capture=$PWD\artifacts\made-up-games\captures\details.png" --capture-frame=150
   ```

`import-gamelist` never overwrites what's there, so after changing a game's details, delete
`artifacts/made-up-games/library/` and make, scan and import again. `make_games.py --games=<id>,...` makes only those
games' pieces again; a full run starts from a clean `media/` and `ROMs/`.

## Asking for more

**More games for a system.** Add `[[games]]` entries: look at the current mix first (the list above) and fill gaps in
genre, colour and publisher, so a grid of covers looks like a varied shelf. Check each title with a web search. Then
paint, look, make, scan, import, capture.

**An existing game on another system.** Add a release to its `versions`. If that system's screens look different
(an N64 version of a 16-bit game), add the look's prompt to its `[games.screens]`. A "64" version usually changes its
`title` ("Apex Circuit 64") and its `logo` (the same with `badge = "64"`).

**A new system.**
1. Find its id (ES-DE's folder name, `src/Launcher.Core/Defaults/systems.toml`) and its game template
   (`[systems.<id>] game_template` in `godot/themes/memory-card/theme.toml`), and the template's faces' proportions
   (`godot/src/Tools/BoxTemplateGenerator.cs`, or the model's script in `tools/console-models/`, sized from
   ScreenScraper's scans).
2. Study its real PAL boxes: contact sheets of `S:\[media]\<id>\covers`, `backcovers` and `spines` (the names with
   "Europe"). Note where the bands, the platform's logo, the seal and the publisher go. Copy the layout, never a mark.
3. `boxes.py`: its sizes in `FORMATS`, and a branch for it in `cover()`, `back()`, `spine()` and `label()`.
4. `screens.py`: its resolution in `NATIVE`, and its palette in `native()` (bits a channel, colours on screen).
5. `codex_art.py`: its place in `PRIORITY`, and, if its screens look like no other system's, a look in `LOOKS` (how the
   grid's panels are described) and in `look_of()`.
6. `make_games.py`: its ROM extension in `ROM_EXTENSIONS`, its place in `SYSTEMS`, and which pieces it gets (`make()`:
   an arcade game gets a logo and a screenshot only).
7. Add games, then the CLAUDE.md row and this file.

**A kind of art** (heroes again, say): `make()` makes it, `FOLDERS` and `EXTENSIONS` name its folder (the app's names:
`MediaKinds.FolderOf` in `src/Launcher.Core/Media/MediaKinds.cs`) and its format. A hero was `boxes.crop(art, 1920, 620,
focus)`.

## games.toml

A concept's keys:

| Key | What |
|---|---|
| `id` | The paintings' folder name. |
| `title`, `genre`, `developer`, `publisher`, `players`, `rating` (0 to 1), `age` | The details. The ROM's name is the title with `: ` as ` - ` and ` (Europe)`. |
| `description`, `features` | The back's copy and the details' description: about three sentences in UK English, and three short features. |
| `logo` | `{ style, title, subtitle, badge, ...the style's options }` (below). |
| `dialogue` | The dialogue window's text, for `hud = "dialogue"`. |
| `versions` | The releases (below). |
| `keyart` | The key art's prompt: every release's cover and label are cut from it. It says its shape: "Landscape, 3:2", with the subject in the middle third, so a Mega Drive cover can be cut from it too; or "Portrait, 2:3" for a game only on portrait boxes. Arcade-only games have none. |
| `[games.screens]` | A screen prompt per look: `16bit` (Mega Drive, SNES, an arcade game ported from them), `n64`, `arcade` (an arcade-only game), `arcade_v` (a vertical one). |

A release's keys: `system` (`megadrive`, `snes`, `n64`, `arcade`), `released` (YYYY-MM-DD), `hud` and `hud_items`, and
what it changes: `title`, `logo`, `players`, `file` (an arcade game's ROM: a MAME-style name, `redlnriv.zip`), `screen`
(its look), `screen_fit = "pad"` (a screen painting widened by mirroring its edges, not cut: Kaleidrop's square one),
`crop` (a focus for cutting the key art or the screen: `{ cover = [x, y], label = [...], screen = [...] }`, fractions
of the spare width and height), `dress` (the Mega Drive's `classic` or `sidebar`) and `logo_place` (`top` or `bottom`).

**HUDs** (drawn at native resolution in a bitmap font; painted text comes out garbled): `text` draws `hud_items`, each
`[text, place]`, `[text, place, colour]` or `[text, place, colour, scale]`, the place `tl tc tr bl bc br` (`tl2 tr2 bl2
br2` a row further in), `"BAR 0.7"` a health bar 70% full. The rest are drawn by `screens.py` for the screens they fit:
`dialogue` (a role-playing game's window), `racer`, `shooter`, `puzzle` (Kaleidrop's), `flower` (Budling's), `hearts`
(Wyrmspire's); `none` draws nothing. A screen prompt leaves a plain band where its HUD will go.

**Logos** (`logos.py`; every style takes `subtitle` and `badge`, a "64" or "'94" in red italics):

| Style | For | Options |
|---|---|---|
| `chrome_neon` | Racers, pinball | `font`, `script`, `outline`, `neon` (colours) |
| `gold_serif` | Fantasy, strategy, golf, westerns | `font`, `metal` (`gold`, `silver`, `bronze`, `jade`), `emblem` (`crown`, `wave`, `moon`, `sword`, `star`, `cog`, `none`) |
| `steel_flare` | Science fiction | `font`, `steel` (`blue`, `teal`, `red`, `gold`) |
| `candy_gems` | Puzzles | `font`, `gem` (an O as a cut gem) |
| `cartoon_arch` | Mascots, karts | `font`, `face` (`green`, `orange`, `red`, `purple`, `blue`, `ice`), `ribbon` (`red`, `blue`, `purple`), `arch` |
| `sports_block` | Sports | `font`, `colours` (two) |
| `horror_drip` | Horror | `font` |
| `stencil_plate` | Military, rally | `plate` (`olive`, `sand`, `mud`, `steel`) |
| `fire_brush` | Action, fighting | `font`, `colours` (`fire`, `storm`, `graffiti`) |
| `arcade_pixel` | Early arcade games | `colours` (three) |

Fonts are file names in `C:\Windows\Fonts` (Windows' and Office's). Publishers with a mark (`boxes.publisher_mark`):
Moonquill (role-playing and adventure), Arcwave (racing and arcade), Velvet Comet (puzzles), Quayside (sports),
Brightmoor (family), Zephyrix (action); a new one needs a branch there. Developers are names only.

## The boxes

After the owner's PAL scans, with made-up marks: a "16-BIT" plate where the console's logo goes, a gold seal with no
words, an invented publisher, a made-up age badge, and a barcode whose digits don't check out.

- **Mega Drive:** `classic`, black bands across the top (a chrome plate) and the foot ("16-BIT CARTRIDGE", the
  publisher); or `sidebar`, a blue band down the left with "SIXTEEN BIT" up it. The back is black, a blue band down its
  right and a strip across its top (the players, the publisher). The spine is black (or blue), the logo down it.
- **SNES:** an L of black down the left (a red tag, a pad, the age) and along the foot (a red "16-BIT" over
  "PAL VERSION", the publisher, the seal). The back and the top spine are black.
- **N64:** a black band down the right (a cube badge, the accessories' icons, the seal, "PAL VERSION"). The back is
  the key art darkened, with a white warnings box; the top spine is black with a red edge.
- **Labels:** the key art under each system's band, with the logo.
- **Backs:** the logo, one screenshot, the copy, and the foot: the age badge, the publisher, the barcode and small print
  saying the game is made up.

## Rules

- **Nothing real:** no real game's art, characters, cars or names, and no console maker's, rating board's or
  publisher's marks. Every word on a piece is drawn by the scripts; the prompts forbid painted text.
- **Look at every painting.** Codex drifts towards famous designs, and a painting that resembles one is painted again
  with a prompt that describes something specific and different. So far: Redline Riviera's first car (a Testarossa),
  Stormfist's first fighters (Chun-Li and Zangief), Wyrmspire's first hero (Link) and Bubble Barrage's first dragons
  (Puzzle Bobble's). To repaint, move the painting to `paintings/rejected/` (named for why), delete a key art's
  `keyart.prompt.txt` or a screen's `screen-<look>.source.txt`, change the prompt in games.toml, and paint again: only
  what's missing is painted.
- **Check every title** with a web search ("<title>" video game). None of the 39 is a game; two are near: Hoop Heroes
  (a 2014 mobile game, HoopHero) and Stormfist (an armour set in The Elder Scrolls Online).
- **Copy:** UK English, a made-up year in the console's era, and nothing that claims to be real.

## Codex

- `codex_art.py` runs `codex exec -m gpt-6.1-sol --skip-git-repo-check --ephemeral -s workspace-write` in a work folder,
  the prompt on stdin, and moves the image the built-in tool saves into place. The owner's Codex config defaults to
  `gpt-5.5`, which a ChatGPT login refuses; `codex debug models` lists the models it offers. A prompt is the preamble
  (save one PNG, no text, original designs only) and the game's prompt.
- **Grids:** screens are painted four to a 1536 × 1024 painting (two for vertical arcade screens) and cut apart,
  which is why 59 releases took 45 runs. `split()` cuts at the thin plain lines near the middle and keeps wide plain
  bands (the HUDs' space) with their panels. The grids stay in `paintings/_grids/`; each screen names its grid in
  `screen-<look>.source.txt`, and `codex_art.py --resplit` cuts them all again after a change to `split()`.
- **Time and limits:** a run takes about two minutes, four at once: 34 runs took about 13 minutes. On 2026-10-25,
  56 runs on the owner's ChatGPT Pro account were all accepted. If Codex refuses (a usage limit), the script stops
  starting runs, lets the running ones finish and reports; run it again later. Mega Drive games are painted first.
- **Keep the paintings.** They can't be made again the same, and `artifacts/` is gitignored, so they exist only in
  `artifacts/made-up-games/paintings/` (about 160 MB). Back that folder up before cleaning `artifacts/`.

## Files

| File | What |
|---|---|
| `games.toml` | The catalogue. |
| `codex_art.py` | Paints what's missing (`--games`, `--jobs`, `--model`, `--dry-run`, `--resplit`). |
| `make_games.py` | Makes every release's pieces, the library and the sheets (`--games`, `--out`, `--jobs`). |
| `boxes.py` | Each system's cover, back, spine and label. |
| `logos.py` | The logo styles. |
| `screens.py` | Native resolution, palettes and HUDs. |
| `paint.py` | Drawing helpers: gradients, shapes from SVG-style paths, masks, layers, text. |

Output, in `artifacts/made-up-games/`: `paintings/` (keep), `library/` (a portable user folder: `ROMs/` with empty files
and a `gamelist.xml` per system, `media/` in the app's layout), `sheets/` and `captures/`.

Needs Python 3.11 or later with Pillow, numpy and scipy, Windows' and Office's fonts, the Codex CLI logged in, and a
built `odyssey-scrape` (`dotnet build`).
