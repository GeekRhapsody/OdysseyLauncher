# Making themes for Odyssey Launcher

This guide is for theme authors. It covers the folder and manifest, the media slots your models show, which model wins when several could, the model spec and budgets, how to make and export models in Blender, and how to test a theme. The design behind it is in [ARCHITECTURE.md](ARCHITECTURE.md) (A6 is the manifest, A7 the model spec).

Five themes come with the repo:
- **Memory Card**, the base theme ([`godot/themes/memory-card/`](../godot/themes/memory-card/theme.toml)). It isn't a theme to choose: every theme builds on it, and anything a theme leaves out (a look, a template, a model, a system's colour) is Memory Card's (section 2). Its templates (the DVD case, jewel case, cartridge box and the rest) are there for every theme to use.
- **Console** ([`godot/themes/console/`](../godot/themes/console/theme.toml)): each system's console as its card (for Windows, a gaming PC and its monitor; the Switch's focused clip slides a Joy-Con off and back, and the Game Boys' bring a cartridge in and switch the screen on, the console a node tree whose parts ride along as it bounces; ScummVM, which has no hardware, is the green S of its icon jumping about; each arcade board is a cabinet typical of it, which takes a coin and plays a made-up game when focused; the other systems with no hardware are a device (TIC-80's mascot, a pinball machine, a terminal for the Z-machine, a Steam Deck), an object (Adventure Game Studio's mug, a cargo ship for Ports) or their emblem made solid (Doom's letters, Quake's rune); Favourites is a Power Star that opens its eyes when focused, Recently played the Dreamcast menu's bouncing alarm clock, All games an untidy pile of game boxes), and a Mega Drive cartridge for that system's games (its art on the cartridge's label). It's small, because everything else comes from Memory Card.
- **Slab**, the default theme ([`godot/themes/slab/`](../godot/themes/slab/theme.toml)): one dark grey card, Memory Card's slab shape, for every system, with the system's image on its front (section 4, "System cards and logos"), over a black and dark grey background, with dark grey menus (section 3, "Menus"). It's a manifest, one model and an image per system: the way to show every system's logo without a model for each.
- **Classic View** ([`godot/themes/classic-view/`](../godot/themes/classic-view/theme.toml)): the look of a 2D launcher. Every system's card is the same flat 16:9 dark grey panel with its logo, every game is just its cover (Memory Card's `flat_cover`, as `[defaults] game_template`), nothing sways or bobs (`[motion]` at 0), one light falls straight on, and a wallpaper is behind everything (section 3, "Wallpapers"). A manifest, a wallpaper, one flat model and an image per system.
- **Retro TV**, the sample theme ([`samples/themes/retro-tv/`](../samples/themes/retro-tv/theme.toml)). It has a CRT television as its game template, a console as its system model, and animation clips. It's the best place to start.

## Contents

1. [Quick start](#1-quick-start)
2. [The theme folder](#2-the-theme-folder)
3. [The manifest (`theme.toml`)](#3-the-manifest-themetoml)
4. [Media slots and fallback chains](#4-media-slots-and-fallback-chains)
5. [Which model is used (precedence)](#5-which-model-is-used-precedence)
6. [The model spec](#6-the-model-spec)
7. [Budgets](#7-budgets)
8. [Animation clips](#8-animation-clips)
9. [Making models in Blender](#9-making-models-in-blender)
10. [Testing a theme](#10-testing-a-theme)
11. [Troubleshooting](#11-troubleshooting)
12. [Publishing a theme](#12-publishing-a-theme)

## 1. Quick start

1. Copy `samples/themes/retro-tv/` to your themes folder, and rename the copy to your theme's id (for example `neon-arcade`):
   - Windows: `%APPDATA%\OdysseyLauncher\themes\neon-arcade\`
   - portable install: `userdata\themes\neon-arcade\`, next to the executable
2. In `theme.toml`, change `name`, and then the colours.
3. Start the launcher, press **Menu** (gamepad) or **Escape** (keyboard) on the systems screen, and choose your theme under **Theme**: it's applied at once, and saved. (**T** on the keyboard switches to the next theme until the launcher closes, for a quick look.) Or set it in `settings.toml` yourself:

   ```toml
   [display]
   theme = "neon-arcade"
   ```

4. Replace the models with your own `.glb` files, keeping their material names (section 4).

## 2. The theme folder

```
neon-arcade/                      the folder name is the theme's id: lower-case letters, digits, '_' and '-'
  theme.toml                      the manifest
  models/
    templates/crt_tv.glb          game templates (the models games are shown on)
    systems/console.glb           system models (the cards on the systems screen)
  logos/
    ps2.png                       each system's image for its card, named by its id (section 4)
  videos/
    ps2.mp4                       a card's video, played on its screen while it's focused (section 4)
```

- Only `theme.toml` is required. Put models and videos wherever you like inside the folder: the manifest names each one by its path, relative to the folder and `/`-separated. A path can't leave the folder.
- `logos/` is the one folder found by its name: an image there named after a system's id (`ps2.webp`) is that system's logo, for its card (section 4).
- The app's own themes are in the `themes` folder beside its executable (`OdysseyLauncher.exe`), not packed inside it. A user theme with the same id as one of them (`console`, say) replaces it. `memory-card` is reserved: a user theme with that id is ignored, with a warning.
- Models are glTF 2.0 binaries (`.glb`) only. To use OBJ or another format, convert it first (section 9).

### The base theme

Every theme builds on Memory Card, so a partial theme always works, and a theme can be a single `name` line. What your theme leaves out is Memory Card's:
- **The look:** each of `[look.background]`, `[look.ambient]` and `[look.lights]` your theme doesn't write (or gets wrong) is Memory Card's. A system your theme gives no look of its own shows your theme's look, not Memory Card's look for that system.
- **`look_transition_ms`:** Memory Card's (300) unless you set it.
- **Templates:** `game_template` can name any of Memory Card's templates (`dvd_case`, `jewel_case`, `psx_jewel_case`, `cartridge_box`, `gameboy_box`, `generic_box_spine`, `generic_box_top_spine`, `generic_box_logo`, `snes_box_horizontal`, `snes_box_vertical`, `clamshell`, `megadrive_clamshell`, `ps2_clamshell`, `ps2_clamshell_blue`, `psp_clamshell`, `umd_case`, `switch_case`, `arcade_cabinet`, `crt_tv_90s`, `flat_cover`, `flat_screenshot`) as well as your own. A `[templates.<id>]` table with one of their ids **extends** that template: each key it leaves out (`model`, `shape`, a slot's chain, a slot's `fit`) is Memory Card's. So this keeps Memory Card's DVD case and changes only what its back shows:

  ```toml
  [templates.dvd_case.slots]
  back = ["screenshot", "generated"]
  ```

- **Which template and card a system gets:** a system your theme doesn't assign a template (and your theme has no `[defaults] game_template`) gets Memory Card's template for it; a system with no card in your theme (and no `[defaults] system_model`) gets Memory Card's slab (section 5).
- **Colours:** a system your theme gives no `colour` takes Memory Card's.
- **Menus:** each `[ui.menu]` key your theme doesn't write is Memory Card's, which writes none: the launcher's own deep blue menus (and text over the grids) and its font.
- **Motion:** each `[motion]` key your theme doesn't write is Memory Card's, which writes none: the launcher's own sway and bob (1).

## 3. The manifest (`theme.toml`)

A complete, commented example is the sample's [`theme.toml`](../samples/themes/retro-tv/theme.toml). Every key:

```toml
format = 1                            # optional; 1 is the only format
name = "Neon Arcade"                  # required: shown when the theme is picked
author = "Your name"                  # optional
look_transition_ms = 300              # how long a cross-fade between looks takes: 0 to 5000, default the base theme's (300)

[look.background]                     # icon.sys-style: one sRGB colour per screen corner, all four required
top_left     = "#1B1F4A"
top_right    = "#1B1F4A"
bottom_left  = "#04040C"
bottom_right = "#0B0B24"
wallpaper    = "wallpapers/main.webp" # optional: a PNG, JPEG or WebP over the corners, at most 16 MB (see "Wallpapers" below)
fit          = "cover"                # optional: "cover" (fill the screen, cropped evenly; the default) or "stretch"

[look.ambient]
colour = "#303038"
energy = 1.0                          # 0 to 16, default 1

[[look.lights]]                       # 1 to 3 directional lights
direction = [-0.5, -0.4, -0.75]       # the way the light travels, in view space: +X right, +Y up, +Z towards you
colour = "#FFFFFF"                    # default white
energy = 1.0                          # 0 to 16, default 1

[defaults]
system_model = "models/systems/console.glb"   # the card for systems without their own model
tint_system_model = true                      # its plain materials take each system's colour
game_template = "crt_tv"                      # the template for systems the theme doesn't assign one: yours, or Memory Card's

[defaults.system_slots]               # optional: what your cards' slots show (section 4, "System cards and logos")
label = ["logo", "generated"]         # the system's logo, else its name printed on the label

[templates.crt_tv]                    # a game template: an id, a model, and optional slot chains (Memory Card's id: extends it)
model = "models/templates/crt_tv.glb"
shape = "model"                       # optional: "model" (its own shape, the default) or "media" (section 4)
video = "screenshot"                  # optional: the slot whose face plays the focused game's video, with its sound (section 4, "Game videos")
video_delay_ms = 1000                 # optional: how long the game is focused before its video starts: 0 to 60000, default 1000

[templates.crt_tv.slots]              # optional; see section 4
screenshot = ["screenshot", "hero", "cover", "authored"]
label = ["logo", "generated"]

[templates.crt_tv.fit]                # optional, per slot: "crop" (fill the face, the default) or "whole" (section 4)
screenshot = "whole"

[systems.ps2]                         # per system, by the launcher's system id (see below); every key is optional
model = "models/systems/ps2.glb"      # its card (default: [defaults] system_model)
tint = false                          # default false for its own model, else tint_system_model
colour = "#2B4C9A"                    # its card's tint and the colour of its games' plain boxes
game_template = "crt_tv"              # a template id in this theme or Memory Card (default: [defaults] game_template)
logo = "art/ps2.png"                  # its card's logo: PNG, JPEG or WebP (default: logos/ps2.png, .jpg, .jpeg or .webp)
video = "videos/ps2.mp4"              # an MP4 its card plays on its video material while focused (section 4, "Card videos"); needs model

[systems.ps2.slots]                   # its card's chains, slot by slot over [defaults.system_slots]
cover = ["logo", "authored"]

[systems.ps2.look.background]         # the look while its games are shown; replaces the theme's block whole
top_left     = "#1E2A4E"
top_right    = "#3A2418"
bottom_left  = "#06080E"
bottom_right = "#100A08"
wallpaper    = "wallpapers/ps2.png"   # optional: its own wallpaper; without one, its games show the corners alone

[ui.menu]                             # optional: the menus' look (see "Menus" below); every key is optional
background = "#141414"                # the panels; their rows, frames and borders are mixed from it and accent
text = "#ECECEC"                      # the text; the dim and faint text are mixed from it towards background
accent = "#C8C8C8"                    # the focused row's border and glow, section headings and values
font = "fonts/menu.ttf"               # a TTF, OTF, WOFF or WOFF2 inside the folder, at most 4 MB

[motion]                              # optional: the grids' own motion (see "Motion" below); every key is optional
focus_sway = 1.0                      # how far the focused item sways: 0 to 3 times the launcher's own (1); 0 faces you
idle_bob = 1.0                        # how far the other items bob: 0 to 3 times the launcher's own (1); 0 holds them still
```

- **Colours** are `#RRGGBB` in sRGB. The four corners blend in sRGB, as on the PS2.
- **Lights** are in view space, so they stay put while the grid scrolls. Any direction but zero is valid. Lights you don't define are off.
- **Per-system looks:** a system's `background`, `ambient` or `lights` block replaces the theme's block of that name whole. Blocks it leaves out come from the theme's look. Entering a system cross-fades to its look, and leaving cross-fades back.
- **Wallpapers:** a background's `wallpaper` is drawn over its four corners, behind everything else. Transparent parts of a PNG or WebP show the corners, so a wallpaper can be a pattern over the gradient. The theme's wallpaper shows on the systems screen, Favourites, Recently played and All games; a system's own `[systems.<id>.look.background]` shows its games over its own wallpaper, or over its corners alone if it has none (the block replaces the theme's whole, so repeat the theme's `wallpaper` there to keep it). Wallpapers cross-fade with the look. The launcher loads each one off the main thread, scaled to fit 2560×1080 (the 3D is drawn at up to 1080p, and the background goes through it, so a bigger image adds no detail), and shows the corners until it has loaded, a fraction of a second at most. A system's wallpaper starts loading while its card is focused, so it's usually there when the system opens. 1920×1080 is the size to make: about 8 MB of video memory once loaded, and the launcher keeps at most three. Keep the area behind the grid's middle calm, or the boxes are hard to read. On the development PC a full-screen wallpaper added 0.03 ms of GPU time a frame at 1280×800 and changed nothing else in the frame times; its cost is the memory ([perf/wallpapers.md](perf/wallpapers.md)).
- **Menus** (`[ui.menu]`) are the settings, the options and details screens, the power menu, dialogs, the on-screen keyboard, the pickers and the job cards. The text over the grids takes the same colours: the glow round the focused system's or game's name (top left) and the line under it, the hints (bottom right), the centre message's glow, and the list layout's titles and their highlight; the name itself stays white. The status indicators keep the launcher's look, and so do the titles printed on cards. Setting any of `background`, `text` and `accent` gives the menus and the text over the grids a palette mixed from the three (the launcher's own for those you leave out); setting none keeps the launcher's own blue exactly. Keep the text light on a dark background, or dark on a light one: dim and faint text are mixed between the two. Green, amber and red (done, a warning, a failure) are the same in every theme. The theme's menus apply at once when the theme is switched, even with the settings open.
- **Motion** (`[motion]`) scales the motion the grid adds to models (section 8): `focus_sway` the focused item's sway from side to side, which shows its spine, and `idle_bob` the gentle up and down of every other item. Both are multiples of the launcher's own, so 1 changes nothing, 0.5 is half, 2 is twice, and 0 stops it (a focused item then faces you). They apply to both grids and to a system's details, and cost nothing: a calmer or livelier theme is as fast as any other. A clip still replaces the motion it stands for, whatever the values.
- **A menu font** is read off the main thread once the theme is chosen; the menus keep the font they have until it has loaded, a fraction of a second. Only its printable ASCII is drawn ahead at the menus' main sizes, so other characters are drawn the first time they show, as with the default font. The menus are laid out at 1280×800 for the default font: a font that's much wider at the same size can cut titles short (with "…") or wrap details onto more lines, so check your theme's menus with `--open=settings` (section 10). Characters your font lacks are drawn in a system font.
- **System ids** are the launcher's: `gb`, `gbc`, `gba`, `nes`, `snes`, `n64`, `gc`, `mastersystem`, `megadrive`, `saturn`, `dreamcast`, `psx`, `ps2` and `psp`, plus any system the user defines. An entry for a system the user doesn't have is ignored. Favourites, Recently played and All games are `favourites`, `recently_played` and `all_games`: their `model`, `tint`, `logo` and `slots` work as a system's (the Console theme's star, clock and pile of boxes are `[systems.favourites]`, `[systems.recently_played]` and `[systems.all_games]`), and their games keep their own systems' templates.
- **Mistakes never stop the launcher.** Each problem is reported with its file, line, column and key, for example:

  ```
  user/themes/neon-arcade/theme.toml:12:1: error: templates.box.model: 'box.glb' doesn't exist in the theme's folder
  ```

  - A TOML syntax error, or an unsupported `format`, rejects the whole theme, and the default theme (Slab) is used.
  - A bad look block falls back to Memory Card's.
  - A template whose model is missing, or isn't a `.glb` inside the folder, is left out. Whatever named it falls through to the next model in line (section 5); if it extended one of Memory Card's, Memory Card's is used.
  - A template id that's neither yours nor Memory Card's is an error, with a "did you mean" suggestion, and the next model in line is used.
  - A bad slot chain falls back to that slot's default chain, and a bad `fit` leaves its slot cropped.
  - A bad `shape` is an error, and the template keeps its own shape.
  - A `video` that isn't a slot's name, or a `video_delay_ms` out of range, is an error, and the template plays no video (or keeps the delay it extends). A `video` on a slot the model has no material for, or a `video_delay_ms` without a `video`, is a warning.
  - A `video` that isn't an `.mp4` inside the folder is an error, and the card shows its video material's own texture. A `video` in an entry without its own `model` is a warning, and is ignored.
  - A bad `[ui.menu]` colour is an error, and that colour is Memory Card's (the launcher's own). A `font` that isn't a TTF, OTF, WOFF or WOFF2 inside the folder, or is over 4 MB, is an error, and the menus keep the default font; so do they if the file can't be read as a font (a warning when the theme is applied).
  - A `[motion]` value that isn't a number from 0 to 3 is an error, and that value is Memory Card's (1).
  - Unknown keys are warnings, with a "did you mean" suggestion.

## 4. Media slots and fallback chains

A material whose name is a media kind is a **media slot**. It shows that game's art. Every other material is plain, and shows what you authored.

| Slot (material name) | Shows | Can the launcher draw it (`generated`)? |
|---|---|---|
| `cover` | the front cover | yes: a title card in the game's colour |
| `back` | the back cover | yes: a darker panel with the title and a strip of the cover |
| `spine` | the spine | yes: the cover's main colour, with the title |
| `box_texture` | a whole box's unfolded art (the user's own: it isn't scraped) | no |
| `label` | a disc or cartridge label (ScreenScraper's support texture, when scraping is set to fetch it) | yes: a paper label with the title |
| `screenshot` | a screenshot | no |
| `logo` | the game's logo | no |
| `hero` | a wide banner | no |

- **Name matching** ignores case and Blender's `.001`-style suffix, so `Cover.001` is the cover.
- **No slot is required**, not even `cover`. A model with no slots at all is fine: it just shows no art.
- **Any image can fill any slot.** A `label` can show the logo, and a screen can show the cover.

### Fallback chains

Each slot of a game template has a chain: the sources it tries, in order, for each game.

- A **media kind** (`cover`, `screenshot`, ...): the game's art of that kind, if it has any.
- **`generated`**: the face the launcher draws (the third column above). It's only allowed for cover, back, spine and label.
- **`authored`**: the material's own texture, or its base colour if it has none.

The first media kind the game has wins. `generated` and `authored` always show, so they end the chain, and every chain ends with `authored` anyway. While the art loads, the chain's next `generated` or `authored` entry shows, and the art fades in over it.

A slot you don't list gets the default chain: its own kind, then `generated` where the launcher can draw it:
- `cover = ["cover", "generated"]`
- `screenshot = ["screenshot"]`, which ends with `authored`

A system card's slots work the same way, with one difference: a system's only art is its logo (below).

The sample's television, for example:

```toml
[templates.crt_tv.slots]
screenshot = ["screenshot", "hero", "cover", "authored"]   # the screen; "authored" is the model's own test card
label = ["logo", "generated"]                               # the stand's plate: the logo, else a printed title
```

### System cards and logos

A theme can give each system an image, its **logo**, and show it on its cards, so one card model can serve every system:

- **The image:** `[systems.<id>] logo = "<path>"`, or else an image in the theme's `logos/` folder named after the system's id: `logos/ps2.png`, `.jpg`, `.jpeg` or `.webp` (PNG first when there are several; the name's case doesn't matter). Favourites, Recently played and All games are `logos/favourites.*`, `logos/recently_played.*` and `logos/all_games.*`. Logos with transparency look best: the card shows through. **Crop each image to what it shows:** the launcher fits the whole image to the face, transparent border included, so a picture in the middle of a mostly empty square comes out small. Larger than 512 pixels gains nothing (each is baked to 512² once, below). Slab's images are prepared that way by `tools/slab-logos.py`, and Classic View's by `tools/classic-view-logos.py` (which renders SVGs first).
- **The chains:** `[defaults.system_slots]` gives your cards' slots their chains, and a system's `[systems.<id>.slots]` overrides them slot by slot. A card's chain can name `logo` (the only media a system has), `generated` (cover, back, spine and label, as for games: a card's label prints the system's name) and `authored`. A slot no chain lists shows `generated` where it can, else `authored`, as cards always have.
- **How it's drawn:** a logo is never cropped. It's drawn whole within a margin (at most 88% of the face's width and 84% of its height), over the slot's fallback, as on a game's slot (section 4, "How art fits a face"). Over `authored`, it isn't multiplied by the material's colour, so a slot material in your card's own colour shows the logo on it: Slab's `label` is the slab's dark grey, with `label = ["logo", "authored"]`. Over `generated`, a label's fallback is a darkened plain colour.
- **Whose chains:** a card uses the chains of the theme its model comes from, and a user's own card (`models/systems/<id>.glb`) takes your theme's, so it shows your logos too. Memory Card names none, so its slab shows the system's name.
- **The first time a theme is used,** its logos are baked to textures in the background (as a game's art is when it's scraped), on up to four threads, the cards on screen first: Slab's 169 take about 7 s, the cards on screen a fraction of that; a card shows its fallback until its logo is ready. From then on a logo loads as fast as a game's art. Only the last theme with logos keeps them baked (`CacheDir/theme-logos/`), so switching to a theme without logos and back costs nothing, and an edited image is baked again.
- **Cost:** a theme whose cards show no logo costs nothing. One that does uses a 256² texture layer per card in the systems grid's pool (about 6 MB), and the systems grid uploads its cards' logos as the games grid does its art.

### Card videos

A system card can play a video while it's focused: a monitor showing a game loading, say, as the Console theme's Amstrad CPC does.

- **The video:** `[systems.<id>] video = "<path>"`, an MP4 inside the theme's folder, in the same entry as the card's `model` (a `video` without a `model` is ignored, with a warning: the video is made for that model). It plays only on that model, never on the theme's default card or another theme's.
- **The screen:** a material named **`video`** (matched as slot names are, so `Video.001` works) with a base colour texture **of its own**, which the video replaces while it plays: give it white as its base colour, and UVs spanning 0 to 1 across the screen, upright (the whole frame is shown, never cropped). Its texture is what the card shows when the video isn't playing: unfocused, before the first frame is decoded, and where there's no decoder. So make it the video's first frame. A model can have one `video` material, and it isn't a media slot.
- **Timing:** the video starts with the card's `focused` clip, without sound, and starts again from its first frame each time the clip loops, so it keeps step with the model. Make it as long as the clip: a shorter one holds its last frame until the clip loops, a longer one is cut there. A card without a `focused` clip loops the video on its own.
- **The file:** H.264 in 4:2:0 (`yuv420p`; Windows can't decode 4:4:4), no larger than the screen needs (every texture is drawn at most 1024 pixels on its longer side), with no sound track. With ffmpeg: `ffmpeg -i in.mp4 -c:v libx264 -pix_fmt yuv420p -g 30 -an out.mp4`. A key frame every second or so makes the restarts quick.
- **Platforms:** videos are decoded by Windows (Media Foundation). Elsewhere the card shows its `video` material's texture.
- **Cost:** only the focused card plays, and only while the systems grid shows. Its frames are decoded on a thread of their own and uploaded once each (about 0.05 ms a frame at 640 × 488 and 30 frames a second). The decoder adds about 50 MB to the app's memory while a video plays.

### Game videos

A game template can play the focused game's own video (the `video` kind its scraper fetched, an MP4) on one of its faces, with the video's sound, as a television's screen: Memory Card's `crt_tv_90s` does.

- **Which face:** `[templates.<id>] video = "<slot>"` names a slot of the model (`screenshot` for a screen). That face shows its art as usual, and once the game has been focused for `video_delay_ms` (default 1000, a second) the video fades in over it, plays with its sound, and starts again when it ends. Moving to another game, launching it, or opening the settings, a game's details or options stops it, and the art shows again; coming back starts the delay again.
- **How it fits:** as the slot's art does: cropped to fill the face, or with `fit = "whole"` fitted inside it at its own proportions (its pixels' shape included) over the material's own texture, as a television shows a game of another shape with bars. Give the face's material an `aspect` (section 9) if it's curved.
- **Games without a video** keep showing their art. Nothing is fetched for a template without `video`: the launcher only reads games' videos when a template the theme uses plays them.
- **One at a time:** only the focused game plays, so the video costs nothing while scrolling, and a template that plays videos is batched like any other.
- **The files:** whatever the scraper saved. They're decoded by Windows (Media Foundation), as the details screen's are (H.264 in 4:2:0 plays everywhere); elsewhere the face shows its art.
- **Cost:** nothing until a video plays, and frame times are the same while one does. The video is decoded on a thread of its own and each new frame uploaded once: at 640 × 480 and 30 frames a second, 0.17 ms more of the renderer's time a frame, and the decoder adds about 53 MB to the app's memory and 3 MB of video memory while it plays ([perf/game-videos.md](perf/game-videos.md)).

### How art fits a face

- **UVs:** a slot's first UV map (TEXCOORD_0) must span 0 to 1 across the face, upright as seen from outside. Sampling is clamped.
- **A logo is never cropped:** when a slot shows the game's `logo` (`label = ["logo", "generated"]`, say), it's drawn whole with a margin, over the slot's fallback, using the logo's transparency. On a `spine` it's turned to read top to bottom like a spine's title (unless the spine face is wider than it is high, a box's top: there it's upright); on any other slot it's upright, filling at most 88% of the face's width and 84% of its height. A `generated` fallback is the cover's main colour (or the game's plain colour, if the template has no `cover` slot) darkened to a deep shade, without the title; an `authored` one is the material's own texture. Logos are mostly about 2:1, so on a much wider face (a marquee, a plate) they fill its height and leave space at the sides. Memory Card's `generic_box_logo` (on the spine) and `arcade_cabinet` (on its marquee) do this, and so does the sample TV's plate.
- **Cropping:** every other slot's art is centre-cropped to fill the face, unless the template's `fit` says otherwise (below). The face's aspect ratio (width over height) comes from the material's custom property `aspect`. If a material has none, it's measured from the slot mesh's bounds, which works for flat, upright faces. For a curved or tilted face, set `aspect` (section 9).
- **Fitting it whole (`fit`):** a template's `[templates.<id>.fit]` table can set a slot to `"whole"`. That slot's art is then never cropped: it's fitted inside the face at its own proportions, over the slot's fallback (the material's own texture, or its `generated` face), as a television shows a tall game with bars at the sides. Memory Card's `arcade_cabinet` fits its screen whole, so a vertical shooter is pillarboxed on the switched-off screen. Art is fitted at its image's proportions, so a screenshot saved at an arcade board's native resolution (224 × 256, say, shown on a 3:4 monitor) looks a little wider than it did on the cabinet. `"crop"` is the default. A logo is always drawn whole, whatever `fit` says.
- **Colour:** make each slot material's base colour **white**, because it multiplies the art. Its base colour texture, if it has one, is what `authored` shows.
- **Resolution:** art is streamed at 512² for the cover and 256² for every other slot, whatever the source's size. An inspected game (R3, or Z: large in the middle of the screen) has every slot's art read again at 1024², so a back or a label is as sharp there as its image allows, up to that size. Only the slots whose chains name a media kind stream anything, so an unused slot costs nothing.

### Boxes shaped by the art (`shape = "media"`)

Box art doesn't come in one size: DOS big boxes alone range from tall to square to landscape, thin to deep. With `shape = "media"` on a template, each game's box takes the shape of its own art, so nothing is cropped:
- **The front** is as wide over high as the game's `cover` image (that image itself, even if a chain shows something else on the front), or, for a model with no `cover` material, its `screenshot` image. The larger of the two fills the grid cell.
- **The depth** comes from the game's `spine` image. One taller than it is wide is the box's side: the depth is its width over its height, times the box's height. One wider than it is tall is the box's top (US and European SNES and N64 boxes): the depth is its height over its width, times the box's width. Scraped images are scaled to a set height (ScreenScraper's are 700 pixels high), so only these proportions are used, never sizes.
- **Without a cover or a spine**, the model's own proportions stand in.
- **Out-of-range art** is clamped: covers to between 1:4 and 4:1, and the depth to between 2% and 50% of the side the spine runs along (the height, or for a top, the width).
- **The grid's cells** fit the widest and tallest box in the list being shown, so a list of tall boxes keeps tight columns.
- **The `cover`, `back` and `spine` faces** take the new proportions. The back's art is cropped to the cover's shape.

Memory Card's `generic_box_spine` (DOS), `generic_box_logo` (Windows and Steam: the same box with the logo on its spine), `generic_box_top_spine` (N64: a landscape box with its spine on the top and bottom) `flat_cover` (just the cover) and `flat_screenshot` (just the screenshot, shaped by it) do this; the flat cards have no thickness, so a spine image changes nothing. SNES's boxes don't: `snes_box_horizontal` (US and European, SNES's default) and `snes_box_vertical` (Super Famicom, which users choose per game) are fixed shapes, sized to the scraped art. Their front and back bevels are part of the `cover` and `back` faces, showing the art's edge, so no plain band frames the art. The depth still comes from the `spine` image when the spine shows a logo. To make a model for it:
- **It must have a `cover` material**, or else a `screenshot` one (whose image then sets the front's proportions), or the key is ignored, with a warning.
- **The spine can be on the sides or on the top and bottom.** The launcher tells which from the `spine` face's aspect: wider than it is high means a top and bottom. Map a top's UVs left to right with the front at the image's bottom edge, and a bottom's with the front at its top edge, so both read from the front. On such a face the generated title and a logo read left to right instead of top to bottom.
- **The launcher moves each half of the model**, left and right, top and bottom (split at half the height), front and back, by however much the box grows or shrinks. Nothing is stretched, so corners and bevels keep their size. So keep vertices off the centre planes (x = 0, z = 0, and half the height), keep corner and bevel detail near the edges, and make `cover`, `back` and `spine` whole faces of the box.
- **A model with animation clips keeps its own shape**, with a warning: the launcher reshapes a template's one merged mesh, not a node tree.
- **It costs nothing per frame:** the box is reshaped in the item shader from numbers worked out when a game's cell is bound.

## 5. Which model is used (precedence)

For each game and each system card, the launcher tries these candidates in order and uses the first that loads. A candidate that's missing, broken or rejected (section 7) falls through to the next one.

**A game's model:**
1. The user's own model for that game, in the media folder with its art: `DataDir/media/<system>/models/<name>.glb`, where `<name>` is the ROM's path under its ROM folder without its extension (`Albion (1995).glb` for `Albion (1995).zip`, shared by every ROM of that name), or with it for that ROM alone (`Albion (1995).zip.glb`, which wins).
   - With the extension kept (`Game (Europe).iso.glb`), it's for that ROM only.
   - Without it (`Game (Europe).glb`), it's for every ROM of that name.
   - Users choose one in the game's options (X on the game, then Model, then Your own model), or import one with `odyssey-scrape import-model` (section 10).
2. The template the user chose for that game: a template id in the active theme, else in Memory Card. The game's options (X on the game, then Model) list your theme's templates, then Memory Card's, for this, so a template no system uses (Memory Card's `snes_box_vertical`, the Super Famicom's box) still has a use.
3. The user's template for the system: `ConfigDir/models/templates/<system>.glb`. Users choose one in the system's options (X on the system, then Game template).
4. The user's `game_model` for the system in `systems.toml`: a template id in the active theme, else in Memory Card. The system's options list your theme's templates, then Memory Card's, for this.
5. Your theme's `[systems.<system>] game_template`.
6. Your theme's `[defaults] game_template`.
7. Memory Card's template for the system.
8. Memory Card's default template.

**A system's card** (and its slot chains: section 4, "System cards and logos"), and Favourites', Recently played's and All games' (`<system>` is `favourites`, `recently_played` or `all_games`):
1. The user's `ConfigDir/models/systems/<system>.glb`, chosen in the system's options (X on the system, then System model).
2. Your theme's `[systems.<system>] model`.
3. Your theme's `[defaults] system_model`.
4. Memory Card's generic card (a memory-card slab with the system's name, in its colour).

User models (levels 1 and 3) use the default slot chains; a chosen template (levels 2 and 4) uses its theme's. Nothing is looked for per game while the grid scrolls: per-game models are indexed when the library is scanned.

The card is also shown large on the system's details screen (Y on the system): about two thirds of the height or width of a view on the left of the screen, in the system's look, focused (its `focused` clip plays) and turned by the player with the right stick, so its back and underside show too. That's what the system model's bigger budget is for (more triangles and textures). Every model's textures are drawn at most 1024 pixels on their longer side, though (section 7), which holds up at that size: a bigger image only makes a larger file.

In a grid, each row is as tall as the tallest model in it, and a shorter model is drawn centred in the row's height. So a landscape console stands level with the middle of the cards beside it, not their bottoms. Game boxes that take their shape from their art (`shape = "media"`) are the exception: they stand on the row's floor.

## 6. The model spec

| Rule | Value |
|---|---|
| Format | glTF 2.0 binary (`.glb`) with one scene and everything embedded. Images are PNG or JPEG. A file that keeps data outside itself, or that needs an extension the launcher can't read (Draco compression, for example), is rejected. |
| Units and axes | glTF's: metres, +Y up, the front facing +Z (towards the viewer). |
| Origin | The bottom centre: the model stands on y = 0. |
| Size | About 1 m on its largest side. You don't have to be exact: the launcher fits every model to the spec, and fits per-game models into the grid cell. More than 10× off gets a "wrong units?" warning. |
| Materials honoured today | Base colour (factor and texture), roughness, vertex colours, the slot names, and a system card's `video` (section 4, "Card videos"). |
| Materials ignored for now | Metallic, normal maps, emissive, unlit, alpha, texture transforms and double-sided. They're planned. Until then, don't rely on them: a model looks the same without them, just flatter. |
| Textures | Base colour textures, at most 4 per model. They're mipmapped when loaded. Normal, metallic-roughness, occlusion and emissive maps are allowed but not drawn yet, so they don't count towards the budget. |
| Animation | Clips named `idle`, `focused` and `launch` (section 8), with node transforms, skinning and morph targets. |
| Ignored | Cameras, lights (the theme's lights are the only lights), extra scenes, and other clips. |

Every model, whether it's an app theme's, yours or the user's, is drawn with the launcher's one item shader. So a model never adds a shader variant, and nothing a theme ships can slow the renderer beyond its triangles and textures.

## 7. Budgets

| Model | Triangles | Base colour textures (not counting slot art) | Materials |
|---|---|---|---|
| Game template | ≤ 2,000 | ≤ 2, each ≤ 1024² | ≤ 4 |
| A user's per-game model | ≤ 5,000 | ≤ 2, each ≤ 1024² | ≤ 4 |
| System model | ≤ 30,000 | ≤ 4, each ≤ 2048² | ≤ 8 |

Skins have at most 64 joints, and meshes at most 8 morph targets.

A menu font (`[ui.menu] font`) can be at most **4 MB**. A font for Latin text is well under it; one with every CJK character is many times over, and is refused. While its theme is active it stays in memory, with its glyphs drawn into textures at each size the menus use; when another theme replaces it, it's let go at once.

- **Over a budget,** the model is used, with a warning.
- **More than twice over** a count (triangles, textures, materials, joints or morph targets), the model is **rejected**, and the next model in line is used (section 5).
- **A texture larger than the budget's side** is scaled down when the model is first processed. Its size alone never rejects a model.
- **Every texture is drawn at most 1024 pixels on its longer side.** A larger one (a system model's 2048², an app theme's) is scaled down when it's loaded, keeping its proportions, because textures are held uncompressed on the graphics card: a 2048² texture takes 21 MB there and a 1024² one 5 MB. A model is never drawn taller than 1080p, so the difference doesn't show. Lay out several parts in one texture by all means, but give each part room at 1024.
- **A broken file** (bad JSON, data out of range, an index past the end, a loop in its nodes, a missing image) is rejected with the reason. It never crashes the launcher: models are checked before Godot parses them.

Every rejection and warning goes to the **model log**, `DataDir/logs/models.log`:
- Windows: `%LOCALAPPDATA%\OdysseyLauncher\logs\models.log`
- portable install: `userdata\logs\models.log`

Each entry says what was wrong and what was used instead. `odyssey-scrape models-log` prints it.

**Processed models are cached** in `CacheDir/models/` with their reports, so a model is only checked and fitted once. An edited file (a new size or modification time) is processed again. The cache is safe to delete at any time.

**Performance tips:**
- Game templates are drawn in batches: one draw call per template for every game that uses it. Keep them light.
- A template with an **idle** clip can't be batched, because every game plays its clip, so each is drawn on its own (up to 64 on screen). Give game templates focused and launch clips if you like, and keep idle clips for system models.

## 8. Animation clips

A model can have up to three clips, named like slots: case and a `.NNN` suffix are ignored, and so is an object name before a `|` (so `Armature|idle` works).

| Clip | Plays | Loops |
|---|---|---|
| `idle` | while the item isn't focused | yes |
| `focused` | while the item is focused (blending in and out over 0.25 s) | yes |
| `launch` | once, when the game starts. The emulator starts when the clip ends, or after 2 s, whichever is first. | no |

Clips can move, rotate and scale nodes: split the model into objects to animate parts, like the sample's aerials. Armatures (at most 64 joints) and shape keys (at most 8) are carried through too, but haven't been tested on a real model yet. If you try one, check it in the launcher, and report what you see. Other clips are listed in the log as ignored.

The grid adds its own motion:
- It **always** lifts the focused item towards you and grows it a little.
- **Only for a state without a clip**, it adds the procedural motion: a gentle bob while idle, a sway while focused, and a spin towards the camera on launch.

So a `focused` clip replaces the sway, and a `launch` clip replaces the spin. Your theme's `[motion]` (section 3) sets how far the sway and the bob go, for models without those clips.

The player can also look at a game close up: R3 (or Z) brings the focused game to the middle of the screen, facing the camera, its front about 75% of the window's height (less if that would make it wider than 75% of the window). Its `focused` clip keeps playing there, and the player can turn it with the right stick. A game template is seen far larger there than in the grid, so its authored textures and its front's art should hold up at that size.

A model with only `focused` and `launch` clips is batched like any other. The grid swaps the focused item onto its own copy of the model while its clips play, then blends it back to the rest pose before swapping it back. Clips should therefore start and end near the rest pose.

## 9. Making models in Blender

Blender 4.x's glTF exporter produces everything the launcher needs.

**Modelling**
- Work in metres. The launcher refits sizes, but a model about 1 m tall avoids the units warning.
- Face the front of the model towards Blender's **front view** (numpad 1, looking along +Y). With the exporter's **+Y Up** option, Blender's −Y becomes glTF's +Z, which is the front.
- Put the origin at the bottom centre, and apply the rotation and scale (Ctrl+A, **All Transforms**) before exporting.
- Check the triangle count with the viewport's **Statistics** overlay.

**Slot materials**
- Name each material after its slot: `cover`, `screenshot`, `label`, and so on. Blender's `.001` suffixes are fine.
- Set the slot's Base Color to white. To give the slot a fallback image (`authored`), plug an **Image Texture** into Base Color.
- Unwrap each slot face so its UVs fill 0 to 1, upright. In the UV editor, scale the island to the whole square and keep the top of the art at the top.
- For a face that isn't flat and upright, add the face's aspect ratio as a material custom property:
  1. Open the material's properties, then **Custom Properties**, and click **New**.
  2. Name it `aspect` and give it a Float value, for example `1.333` for a 4:3 screen.
  3. When exporting, tick **Custom Properties** (below) so it's written as `extras.aspect`.

**Plain materials** keep their Base Color (and texture, if any) and Roughness. For system models, `tint_system_model` or `tint` mixes a plain material towards each system's colour, so make the parts you want tinted light and neutral.

**Clips**
- Make one action per clip, named `idle`, `focused` or `launch`, and push each onto the object's or armature's NLA stack so the exporter finds it.
- Animate objects (location, rotation, scale), bones or shape keys. In the sample, the TV's aerials are separate objects parented to the set.

**Export** (File > Export > glTF 2.0)

| Setting | Value |
|---|---|
| Format | glTF Binary (`.glb`) |
| Include | Limit to Selected Objects if the file has anything else; tick **Custom Properties** |
| Transform | **+Y Up** (the default) |
| Data > Mesh | Apply Modifiers, UVs, Normals; vertex colours if you use them |
| Data > Material | Export; Images: Automatic (PNG or JPEG) |
| Animation | tick **Animation**; mode **Actions** (each action becomes a clip named after it) |
| Compression | **off** (Draco isn't supported) |

**Other formats:** users can import a Wavefront OBJ model (a zip of the `.obj`, its `.mtl` and its textures) as a game's own model. The launcher converts it to glTF, keeping the material names, so an OBJ material named `cover` is still a slot. OBJ has no clips, with one exception: a PS2 save icon converted to OBJ with its shape animation beside it (`ICON.ICO.obj` and `ICON.ICO.anim`, as the PS2 icon database's zips have them) gets a `focused` clip, so it animates when it's selected. Those icons face away from the viewer as exported, so the launcher turns them round; any other OBJ must face +Z, as Blender exports it. For a theme, export `.glb` from Blender.

## 10. Testing a theme

**Check a model before using it.** Run this from the repo, after `dotnet build`:

```
.\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe inspect-model --kind=template path\to\crt_tv.glb
```

It prints the triangle, material and texture counts against the budget, the slots and clips found, the size, and every warning and error, without changing anything. Use `--kind=system` for a system model. Without `--kind`, the model is checked as a per-game model.

**Run the launcher on your theme**, in a separate user folder so your own library isn't touched. From the repo, with a test library such as the synthetic one (CLAUDE.md, Commands):

```
godot --path godot -- --user-dir=<absolute folder> --theme=neon-arcade
```

- Copy the theme into `<folder>\themes\` first.
- `--start-system=ps2` opens a system straight away.
- `--nav-script=right,right,accept` presses buttons for you. `accept` launches the focused game; with no emulator installed, the launch clip plays and the launch then fails harmlessly.
- `--capture=<absolute path>.png --capture-frame=150 --fixed-fps 60` saves a screenshot at that frame and quits.
- `--no-overlay` hides the text, so you can check the background corners.
- `--open=settings` (or `power`, `keyboard`, `confirm`, `folder-picker`) opens a menu straight away, to check `[ui.menu]`; the `theme` step in `--nav-script` switches theme with it open.
- `--layout=single/list` shows a system's card, and a game's model, about half the screen's height (the user can choose these layouts in the settings: Look, Layout), so it's the closest look at your models' detail; `--layout=carousel/carousel` turns the items beside the focused one towards it.

The console shows the theme's diagnostics as it loads (section 3), and `logs/models.log` in the user folder shows each model's report.

**Check performance** with the bench:

```
.\tools\bench-export.ps1 -AppArgs "--user-dir=<folder>", '--theme=neon-arcade', '--bench-scenario=scroll'
```

It scrolls the biggest system from the first row to the last and reports frame times, hitches and memory. In the report, `scroll.frames` should match the same run with `--theme=memory-card`.

**Before you publish,** check that:
- `theme.toml` loads with no errors or warnings
- every model passes `inspect-model` with no warnings
- the theme looks right with games that have art and games that have none (a synthetic library has both)
- the focused and launch clips return to the rest pose

Then, to offer it in the launcher's theme downloader, see section 12.

## 11. Troubleshooting

| You see | Why | Fix |
|---|---|---|
| Your theme isn't offered | The folder isn't in `ConfigDir/themes/`, or `theme.toml` has a syntax error (the console names the line) | Check the path and the first error |
| A system uses Memory Card's box | Your theme doesn't assign it a template, or its template was left out (missing file, or a path outside the folder), or its model was rejected | Read the console and `models.log` |
| Art is stretched or cut off badly | The face's aspect ratio is wrong | Set the material's `aspect` custom property, and export Custom Properties |
| Art is upside down or mirrored | The slot's UVs aren't upright from outside | Flip the UV island vertically or horizontally |
| A slot shows the plain colour, never art | The material isn't named after a slot, or the chain names kinds the library has no art for | Check the name (a `.001` suffix is fine), then the chain |
| A system's games show no wallpaper, or the gradient alone for a moment | Its `[systems.<id>.look.background]` replaces the theme's whole, wallpaper and all; or the image was still loading (it fades in) | Repeat `wallpaper` in the system's block; check the console for `Wallpaper:` warnings |
| A card shows no logo | The chain doesn't name `logo` (`[defaults.system_slots]`), the image isn't named after the system's id (`logos/<id>.png`: the id, not its name, e.g. `megadrive`), the card's model comes from another theme (its chains are that theme's), or it's still being baked (the first time, the console says when they're done) | Check the chain, the id (systems.toml) and the console |
| The model is tiny, or huge and warned about units | It's modelled in centimetres or millimetres | Scale it to about 1 m, and apply the scale |
| A clip doesn't play | It isn't named idle, focused or launch, or it wasn't exported | Rename the action, and push it onto the NLA stack |
| A game's video doesn't play | The template has no `video`, the slot it names isn't one of the model's materials, the game has no video (the game's details list its media), or a settings screen or panel is open | Check the console's warnings and the game's media |
| "more than twice the ... may have" in the log | The model is too heavy, so it was rejected | Decimate it, or merge materials |

## 12. Publishing a theme

The launcher's settings have **Download themes** (under Look): a list of themes anyone can get, update and remove from the couch, like ES-DE's theme downloader. The list is [`GeekRhapsody/odyssey-themes`](https://github.com/GeekRhapsody/odyssey-themes), and the launcher's owner tests every theme before it's added. Each theme is a git repository of its own, which the launcher clones into the user's `themes/` folder.

**Your repository:**
- Put `theme.toml` at the top of the repository: the repository *is* the theme folder. A theme in a subfolder isn't found.
- The folder it's installed in is the list's `id`, not your repository's name: pick one in lower-case letters, digits, `_` and `-` (`neon-arcade`), and not `memory-card`, `classic-view`, `console` or `slab`.
- Keep the history small. A user downloads every commit, so a 20 MB model committed ten times costs them 200 MB. Commit models when they're finished, and squash early work before you submit.
- Mark binary files as binary in a `.gitattributes` (`*.glb binary`, `*.png binary`, `*.webp binary`, `*.mp4 binary`), so no git setting ever changes their bytes. The launcher checks out files exactly as committed whatever its user's git settings, but your collaborators' clones won't.
- A file a user adds to your theme's folder (their own logo, say) survives updates, because git doesn't track it. A file of yours they edit is overwritten by an update, and the launcher asks them first.

**Check it** with the command the list's owner runs, from this repository after `dotnet build`:

```
.\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe inspect-theme --json <your theme's folder>
```

It loads the theme as the launcher does (every error and warning, with its line), checks each model against its kind's budget, and prints the theme's size and a `covers` block: what your theme brings (system cards and logos, templates, its own menus, videos), which the list can show in its details. `covers` is optional. Fix every error, and name the folder after the id you want.

**Submit it:** open an issue or a pull request on `odyssey-themes` with:
- the repository's https URL: users get its default branch
- the id, name, your name as the author, and a sentence or two of description
- the oldest launcher version it needs, if it uses something new (`min_app_version`; the launcher shows the theme to older versions, but won't install it)
- two to four screenshots, 16:9 (the list shows the first at 192 × 108, and the details show them all full screen): the systems and a system's games at least, taken with `--capture` (section 10) at 1280 × 720 or larger. The list keeps them in `screenshots/<id>/`.

**Updates:** the list's owner tests your theme once, before it's listed. After that, whatever you push to its default branch reaches users as an update, the next time they press A on it in Download themes, as with ES-DE's themes. Nobody reviews updates, so keeping the theme working is up to you: try changes before pushing them (on a branch of their own while you work), and don't rewrite the default branch's history. If you push a version the user's launcher can't load, it's refused there and they keep the version they had. Ask for new screenshots to be listed if it looks different.

**Try it before you submit:** a list can be read from a folder with `--themes-list=<folder>` (the launcher's and `odyssey-scrape themes`), and a local list may name a repository by a `file:///` URL, so you can install your theme the way users will:

```
godot --path godot -- --user-dir=<absolute folder> --open=themes --themes-list=<absolute folder with themes.json>
```

`tests/themes-list/themes.json` in this repository is an example list (its themes are made up, so they can't be installed).
