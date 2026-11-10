# Making themes for Odyssey Launcher

This guide is for theme authors. The design behind it is in [ARCHITECTURE.md](ARCHITECTURE.md) (A6 is the manifest, A7 the model spec).

These themes come with the repo, and each one is a working example:

| Theme | What it shows |
|---|---|
| [Retro TV](../samples/themes/retro-tv/theme.toml) (the sample) | A CRT television as its game template, a console as its system model, and animation clips. **Start here.** |
| [Memory Card](../godot/themes/memory-card/theme.toml) | The base theme. Users can't choose it: every other theme builds on it (section 2), and any theme can use its game templates. |
| [Slab](../godot/themes/slab/theme.toml) (the default) | One card model for every system, with each system's image on it (section 4, "System cards and logos"), and its own menu colours. |
| [Classic View](../godot/themes/classic-view/theme.toml) | The look of a 2D launcher: a wallpaper, flat covers and no motion. |
| [Console](../godot/themes/console/theme.toml) | A model of its own for every built-in system, many of them with `focused` clips and card videos. |

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

1. Copy `samples/themes/retro-tv/` into your themes folder, and rename the copy to your theme's id (for example `neon-arcade`):
   - Windows: `%APPDATA%\OdysseyLauncher\themes\neon-arcade\`
   - Portable install: `userdata\themes\neon-arcade\`, next to the executable
2. In `theme.toml`, change `name`, and then the colours.
3. Start the launcher and choose your theme in **Settings > Appearance > Theme**. It applies at once. On a keyboard, **T** switches to the next theme until the launcher closes. You can also set the theme in `settings.toml`:

   ```toml
   [display]
   theme = "neon-arcade"
   ```

4. Replace the models with your own `.glb` files, and keep their material names (section 4).

## 2. The theme folder

```
neon-arcade/                      the folder name is the theme's id: lower-case letters, digits, '_' and '-'
  theme.toml                      the manifest (the only required file)
  models/templates/crt_tv.glb     game templates (the models that games are shown on)
  models/systems/console.glb      system models (the cards on the systems screen)
  logos/ps2.png                   each system's image for its card, named by the system's id (section 4)
  videos/ps2.mp4                  a card's video, played on its screen while it's focused (section 4)
```

- Apart from `logos/`, the folder layout is up to you. The manifest names each file by a path relative to the theme folder, separated by `/`. A path can't point outside the folder.
- The launcher finds `logos/` by its name (section 4).
- The launcher's own themes are in the `themes` folder beside the executable. A user theme with the same id as one of them replaces it. The id `memory-card` is reserved: a user theme with that id is ignored, with a warning.
- Models must be glTF 2.0 binaries (`.glb`). Convert any other format first (section 9).

### The base theme

Every theme builds on Memory Card, so a theme can be as small as a single `name` line. Anything your theme leaves out comes from Memory Card:

- **Look:** each of `[look.background]`, `[look.ambient]` and `[look.lights]` that you leave out or get wrong, and `look_transition_ms` (300). A system with no look of its own uses your theme's look.
- **Templates:** `game_template` can name any of Memory Card's templates as well as your own: `dvd_case`, `jewel_case`, `psx_jewel_case`, `dreamcast_jewel_case`, `megacd_case`, `segacd_case`, `cartridge_box`, `gameboy_box`, `generic_box_spine`, `generic_box_top_spine`, `generic_box_logo`, `snes_box_horizontal`, `snes_box_vertical`, `clamshell`, `megadrive_clamshell`, `ps2_clamshell`, `ps2_clamshell_blue`, `psp_clamshell`, `umd_case`, `switch_case`, `arcade_cabinet`, `crt_tv_90s`, `flat_cover` and `flat_screenshot`. A `[templates.<id>]` table that uses one of these ids **extends** that template: each key you leave out (`model`, `shape`, or a slot's chain or `fit`) keeps Memory Card's value. For example, this keeps Memory Card's DVD case and changes only what its back shows:

  ```toml
  [templates.dvd_case.slots]
  back = ["screenshot", "generated"]
  ```

- **Each system's template and card:** if your theme doesn't assign a system a template and has no `[defaults] game_template`, that system gets Memory Card's template for it. If your theme gives a system no card and has no `[defaults] system_model`, the system gets Memory Card's slab.
- **Colours:** a system without a `colour` in your theme takes Memory Card's.
- **Menus and motion:** Memory Card sets no `[ui.menu]` or `[motion]` keys, so any key you leave out uses the launcher's own: deep blue menus in its own font, and its normal sway and bob.

## 3. The manifest (`theme.toml`)

The sample's [`theme.toml`](../samples/themes/retro-tv/theme.toml) is a complete example with comments. Every key:

```toml
format = 1                            # optional; 1 is the only format
name = "Neon Arcade"                  # required: shown in the theme list
author = "Your name"                  # optional
look_transition_ms = 300              # length of a cross-fade between looks: 0 to 5000, default 300

[look.background]                     # one sRGB colour per screen corner; all four are required
top_left     = "#1B1F4A"
top_right    = "#1B1F4A"
bottom_left  = "#04040C"
bottom_right = "#0B0B24"
wallpaper    = "wallpapers/main.webp" # optional: a PNG, JPEG or WebP of at most 16 MB, drawn over the corners
fit          = "cover"                # optional: "cover" (fill the screen and crop evenly; the default) or "stretch"

[look.ambient]
colour = "#303038"
energy = 1.0                          # 0 to 16, default 1

[[look.lights]]                       # 1 to 3 directional lights
direction = [-0.5, -0.4, -0.75]       # the direction the light travels in view space: +X right, +Y up, +Z towards you
colour = "#FFFFFF"                    # default white
energy = 1.0                          # 0 to 16, default 1

[defaults]
system_model = "models/systems/console.glb"   # the card for systems without a model of their own
tint_system_model = true                      # its plain materials take each system's colour
game_template = "crt_tv"                      # the template for systems the theme doesn't assign one: yours or Memory Card's

[defaults.system_slots]               # optional: what your cards' slots show (section 4, "System cards and logos")
label = ["logo", "generated"]         # the system's logo, or else its name printed on the label

[templates.crt_tv]                    # a game template (a Memory Card id extends that template)
model = "models/templates/crt_tv.glb"
shape = "model"                       # optional: "model" (the model's own shape; the default) or "media" (section 4)
video = "screenshot"                  # optional: the slot that plays the focused game's video, with sound (section 4, "Game videos")
video_delay_ms = 1000                 # optional: how long a game must be focused before its video starts: 0 to 60000, default 1000

[templates.crt_tv.slots]              # optional: fallback chains (section 4)
screenshot = ["screenshot", "hero", "cover", "authored"]
label = ["logo", "generated"]

[templates.crt_tv.fit]                # optional, per slot: "crop" (fill the face; the default) or "whole" (section 4)
screenshot = "whole"

[systems.ps2]                         # per system, by system id; every key is optional
model = "models/systems/ps2.glb"      # its card (default: [defaults] system_model)
tint = false                          # default false with its own model, otherwise tint_system_model
colour = "#2B4C9A"                    # its card's tint, and the colour of its games' plain boxes
game_template = "crt_tv"              # a template id from this theme or Memory Card (default: [defaults] game_template)
logo = "art/ps2.png"                  # its card's logo: PNG, JPEG or WebP (default: logos/ps2.png, .jpg, .jpeg or .webp)
video = "videos/ps2.mp4"              # an MP4 that its card plays while focused (section 4, "Card videos"); needs model

[systems.ps2.slots]                   # its card's chains, slot by slot, over [defaults.system_slots]
cover = ["logo", "authored"]

[systems.ps2.look.background]         # the look while its games are shown; replaces the theme's whole block
top_left     = "#1E2A4E"
top_right    = "#3A2418"
bottom_left  = "#06080E"
bottom_right = "#100A08"
wallpaper    = "wallpapers/ps2.png"   # optional; without one, its games show the corners only

[ui.menu]                             # optional: the menus' look; every key is optional
background = "#141414"                # the panels; their rows, frames and borders are mixed from this and accent
text = "#ECECEC"                      # the text; dim and faint text are mixed from this towards background
accent = "#C8C8C8"                    # the focused row's border and glow, section headings and values
font = "fonts/menu.ttf"               # a TTF, OTF, WOFF or WOFF2 file of at most 4 MB

[motion]                              # optional: the grids' motion; every key is optional
focus_sway = 1.0                      # how far the focused item sways: 0 to 3 times the launcher's own; 0 faces it to you
idle_bob = 1.0                        # how far the other items bob: 0 to 3 times the launcher's own; 0 holds them still
```

- **Colours** are `#RRGGBB` in sRGB. The four corners blend in sRGB, as on the PS2.
- **Lights** are in view space, so they don't move while the grid scrolls. Any direction except zero is valid. Lights you don't define are off.
- **Per-system looks:** a system's `background`, `ambient` or `lights` block replaces the theme's block of that name whole. Blocks the system leaves out come from the theme. The look cross-fades when the user enters or leaves the system.
- **Wallpapers** are drawn over the four corners and behind everything else. Transparent areas of a PNG or WebP show the corners through. The theme's wallpaper shows on the systems screen, Favourites, Recently played and All games. A system's `[systems.<id>.look.background]` replaces the theme's block whole, including the wallpaper, so repeat `wallpaper` there to keep it. Make wallpapers 1920×1080: the launcher scales them to fit 2560×1080, and the 3D is drawn at up to 1080p, so a bigger image adds no detail. Keep the area behind the middle of the grid plain, or the boxes are hard to read. Until a wallpaper has loaded, which takes a fraction of a second, the corners show alone.
- **Menus** (`[ui.menu]`) are the settings, options and details screens, the power menu, dialogs, the on-screen keyboard, the pickers and the job cards. The text over the grids uses the same colours, except the focused item's name, which stays white. The status indicators and the titles printed on cards keep the launcher's look. If you set any of `background`, `text` and `accent`, the launcher mixes a palette from them, and uses its own values for those you leave out. If you set none, the menus keep the launcher's blue. Use light text on a dark background or dark text on a light one, because dim and faint text are mixed between the two. Green, amber and red (done, a warning and a failure) are the same in every theme.
- **A menu font** has to fit menus laid out for the default font at 1280×800. A much wider font can cut titles short (with "…") or wrap details onto more lines, so check your menus with `--open=settings` at `--ui-size=large` (section 10). Any character missing from your font is drawn in a system font.
- **Motion** (`[motion]`) scales the motion that the grid adds to models (section 8), in both grids and on a system's details screen: 1 is the launcher's own, 0.5 is half and 0 is none. A clip still replaces the motion it stands for.
- **System ids** are the launcher's own, such as `gb`, `snes`, `megadrive`, `psx`, `ps2` and the rest of its built-in catalogue (ES-DE's ids), plus any system the user defines. An entry for a system the user doesn't have is ignored.
  - **Regional variants** are systems of their own: `dreamcastnajp` (Dreamcast (NA/JP)), `segacd` (Sega CD), `megacdjp` (Mega-CD (JP)) and `sfc` (Super Famicom). If your theme gives a system a card or a logo, give its variants one as well. While variants are grouped (the default), their games appear in their system's card, with that system's card, logo and look. A variant's own card shows when the user turns grouping off. A variant's games always use the variant's own template.
  - **Favourites, Recently played and All games** are `favourites`, `recently_played` and `all_games`. Their `model`, `tint`, `logo` and `slots` keys work as a system's do, and their games keep their own systems' templates.
- **Mistakes never stop the launcher.** It reports each problem with its file, line, column and key, for example:

  ```
  user/themes/neon-arcade/theme.toml:12:1: error: templates.box.model: 'box.glb' doesn't exist in the theme's folder
  ```

  | Mistake | What happens |
  |---|---|
  | A TOML syntax error, or an unsupported `format` | The whole theme is rejected, and Slab is used. |
  | A bad look block | Memory Card's block is used. |
  | A template whose model is missing, or isn't a `.glb` inside the folder | The template is left out. Whatever named it falls through to the next model in line (section 5), or to Memory Card's template if it extended one. |
  | A template id that's neither yours nor Memory Card's | An error with a "did you mean" suggestion. The next model in line is used. |
  | A bad slot chain, `fit` or `shape` | The slot's default chain is used, the slot is cropped, or the template keeps its own shape. |
  | A template `video` that isn't a slot name, or a `video_delay_ms` out of range | An error. The template plays no video, or keeps the delay it extends. |
  | A template `video` naming a slot the model lacks, or `video_delay_ms` without `video` | A warning. |
  | A system `video` that isn't an `.mp4` inside the folder | An error. The card shows its `video` material's own texture. |
  | A system `video` in an entry without its own `model` | A warning, and the video is ignored. |
  | A bad `[ui.menu]` colour | That colour is the launcher's own. |
  | A font that isn't a TTF, OTF, WOFF or WOFF2 inside the folder, is over 4 MB, or can't be read | The menus keep the default font. |
  | A `[motion]` value that isn't a number from 0 to 3 | That value is 1. |
  | An unknown key | A warning with a "did you mean" suggestion. |

## 4. Media slots and fallback chains

A material named after a media kind is a **media slot**, and shows that game's art. Any other material is plain, and shows what you authored.

| Slot (material name) | Shows | Can the launcher draw it (`generated`)? |
|---|---|---|
| `cover` | the front cover | yes: a title card in the game's colour |
| `back` | the back cover | yes: a darker panel with the title and a strip of the cover |
| `spine` | the spine | yes: the cover's main colour, with the title |
| `box_texture` | a whole box's unfolded art (the user's own: it isn't scraped) | no |
| `label` | a disc or cartridge label | yes: a paper label with the title |
| `screenshot` | a screenshot | no |
| `logo` | the game's logo | no |
| `hero` | a wide banner | no |

- Name matching ignores case and Blender's `.001`-style suffixes, so `Cover.001` is the cover.
- No slot is required, not even `cover`. A model with no slots just shows no art.
- Any slot can show any kind of image: a `label` can show the logo, and a screen can show the cover.

### Fallback chains

Each slot of a game template has a chain: the sources it tries, in order, for each game.

- **A media kind** (`cover`, `screenshot`, ...): the game's art of that kind, if it has any. The first kind the game has wins.
- **`generated`**: the face the launcher draws (the third column above). Only cover, back, spine and label can use it.
- **`authored`**: the material's own texture, or its base colour if it has none.

`generated` and `authored` always show, so they end a chain, and every chain implicitly ends with `authored`. While art loads, the chain's next `generated` or `authored` entry shows, and the art fades in over it.

A slot you don't list gets the default chain: its own kind, then `generated` if the launcher can draw that slot. So the default for `cover` is `["cover", "generated"]`, and for `screenshot` it's `["screenshot"]`, which ends with `authored`. The sample's television, for example:

```toml
[templates.crt_tv.slots]
screenshot = ["screenshot", "hero", "cover", "authored"]   # the screen; "authored" is the model's own test card
label = ["logo", "generated"]                               # the stand's plate: the logo, or else a printed title
```

### System cards and logos

A theme can give each system an image, its **logo**, and show it on the system's card, so one card model can serve every system.

- **The image** is `[systems.<id>] logo = "<path>"`, or else `logos/<id>.png`, `.jpg`, `.jpeg` or `.webp` (the name's case doesn't matter, and PNG wins when there are several). Favourites, Recently played and All games use `logos/favourites.*`, `logos/recently_played.*` and `logos/all_games.*`. **Crop each image to its content:** the launcher fits the whole image to the face, transparent border included, so a small picture in a mostly empty square comes out small. Transparent images look best, because the card shows through. Images larger than 512 pixels gain nothing. Slab's images are prepared by `tools/slab-logos.py`, and Classic View's by `tools/classic-view-logos.py`.
- **The chains:** `[defaults.system_slots]` sets the chains for all your cards, and a system's `[systems.<id>.slots]` overrides them slot by slot. A card's chain can name `logo` (a system's only media), `generated` (cover, back, spine and label; a card's generated label prints the system's name) and `authored`. A slot that no chain lists shows `generated` if it can, and `authored` otherwise.
- **How it's drawn:** a logo is never cropped. It's drawn whole, at most 88% of the face's width and 84% of its height, over the slot's fallback. Over `authored`, the logo isn't multiplied by the material's colour, so a slot material in your card's colour shows the logo on that colour: Slab's `label` is the slab's dark grey, with `label = ["logo", "authored"]`. Over `generated`, a label's fallback is a darkened plain colour.
- **Whose chains:** a card uses the chains of the theme that its model comes from. A user's own card (`models/systems/<id>.glb`) uses your theme's chains, so it shows your logos too. Memory Card names no chains, so its slab shows the system's name.
- **The first time a theme is used**, its logos are processed in the background, and each card shows its fallback until its logo is ready. An edited image is processed again.

### Card videos

A system card can play a video while it's focused: a monitor loading a game, or a handheld's screen, for example. The Console theme's Amstrad CPC, Game Boy and Vectrex cards do this.

- **The video:** `[systems.<id>] video = "<path>"`, an MP4 inside the theme folder, in the same entry as that card's `model`. It only plays on that model.
- **The screen** is a material named **`video`** (matched the same way as slot names), with a white base colour, its own base colour texture, and UVs that span 0 to 1 across the screen, upright. The whole frame is shown, never cropped. The material's texture shows whenever the video isn't playing (when the card isn't focused, before the first frame is decoded, and where there's no decoder), so make it the video's first frame. A model can have one `video` material, and it isn't a media slot.
- **Timing:** the video starts with the card's `focused` clip, without sound, and restarts from its first frame each time the clip loops. Make it as long as the clip: a shorter video holds its last frame until the clip loops, and a longer one is cut off. On a card with no `focused` clip, the video loops on its own.
- **Encoding:** H.264 in 4:2:0 (`yuv420p`; Windows can't decode 4:4:4), no larger than the screen needs (textures are drawn at most 1024 pixels on their longer side), with no sound track and no B-frames (with B-frames, Windows shows every frame a frame or two late). A key frame about every second makes restarts quick:

  ```
  ffmpeg -i in.mp4 -c:v libx264 -bf 0 -pix_fmt yuv420p -g 30 -an out.mp4
  ```

- **Where it plays:** on the focused card in the systems grid while no menu covers it, and on the system's details screen (Y on the system). Videos are decoded by Windows (Media Foundation) and by the FFmpeg in the Linux AppImage. Anywhere else, the card shows its `video` material's texture.

### Game videos

A game template can play the focused game's scraped video, with its sound, on one of its faces, such as a television's screen. Memory Card's `crt_tv_90s` does this.

- **The face:** `[templates.<id>] video = "<slot>"` names one of the model's slots (`screenshot` for a screen). The face shows its art as usual. Once the game has been focused for `video_delay_ms` (1000 by default), the video fades in over the art, plays with sound and loops. Moving to another game, launching, or opening a menu stops it.
- **Fit:** the video fits the face as the slot's art does: cropped, or with `fit = "whole"` fitted inside it with bars. Give a curved face an `aspect` (section 9).
- Games without a video keep showing their art. Only the focused game plays, so templates with videos are batched like any other.
- Decoding works as for card videos. On Linux, 4:4:4, HEVC and VP9 play as well.

### How art fits a face

- **UVs:** a slot's first UV map (TEXCOORD_0) must span 0 to 1 across the face, upright as seen from outside. Sampling is clamped.
- **Colour:** make each slot material's base colour **white**, because it multiplies the art. The material's base colour texture, if it has one, is what `authored` shows.
- **Cropping:** art is centre-cropped to fill the face. The face's aspect ratio (width over height) comes from the material's custom property `aspect`. Without one, it's measured from the slot mesh's bounds, which works for flat, upright faces. Set `aspect` for a curved or tilted face (section 9).
- **Fitting it whole:** a template's `[templates.<id>.fit]` can set a slot to `"whole"`. That slot's art is then fitted inside the face at its own proportions, over the slot's fallback, as a television shows a tall game with bars at the sides. Memory Card's `arcade_cabinet` does this for its screen.
- **Logos are never cropped,** whatever `fit` says. A logo is drawn whole with a margin (at most 88% of the face's width and 84% of its height), over the slot's fallback. On a `spine` it reads from top to bottom, unless the face is wider than it is high (a box's top), where it's upright. A `generated` fallback behind a logo is the cover's main colour, darkened, without the title. Logos are mostly about 2:1, so on a much wider face, such as a marquee or a plate, they fill its height. Memory Card's `generic_box_logo` (spine) and `arcade_cabinet` (marquee) and the sample TV's plate show logos this way.
- **Resolution:** while browsing, the cover's art is loaded at 512² and every other slot's at 256², whatever the source's size. When the user inspects a game (R3, or Z on a keyboard), every slot's art is loaded again at 1024². Slots whose chains name no media kind load nothing.

### Boxes shaped by the art (`shape = "media"`)

Box art doesn't come in one size: DOS big boxes alone range from tall to square to landscape. With `shape = "media"` on a template, each game's box takes the shape of its own art, so nothing is cropped.

- **The front** has the proportions of the game's `cover` image, or of its `screenshot` image for a model with no `cover` material.
- **The depth** comes from the game's `spine` image. A spine image taller than it is wide is the box's side, and one wider than it is tall is the box's top (as on US and European SNES and N64 boxes). Only its proportions are used.
- Without a cover or a spine image, the model's own proportions are used. Covers are clamped to between 1:4 and 4:1, and the depth to between 2% and 50% of the side that the spine runs along.
- The grid's cells fit the widest and tallest box in the list, and the back's art is cropped to the cover's shape.

Memory Card's `generic_box_spine` (DOS), `generic_box_logo` (Windows and Steam), `generic_box_top_spine` (N64), `flat_cover` and `flat_screenshot` use this. To make a model for it:

- **It must have a `cover` material**, or else a `screenshot` one. Otherwise the key is ignored, with a warning.
- **The spine can be on the sides, or on the top and bottom.** If the `spine` face is wider than it is high, it's a top and bottom: map a top's UVs left to right with the front at the image's bottom edge, and a bottom's with the front at its top edge, so both read from the front. On such a face, the generated title and logos read left to right.
- **The launcher moves each half of the model** (left and right, top and bottom split at half the height, front and back) instead of stretching it, so corners and bevels keep their size. Keep vertices off the centre planes (x = 0, z = 0 and half the height), keep corner and bevel detail near the edges, and make `cover`, `back` and `spine` whole faces of the box.
- **A model with animation clips keeps its own shape**, with a warning.

## 5. Which model is used (precedence)

For each game and each system card, the launcher tries these candidates in order and uses the first one that loads. A candidate that's missing, broken or rejected (section 7) falls through to the next.

**A game's model:**

1. The user's own model for the game, in its media folder: `DataDir/media/<system>/models/<name>.glb`. `<name>` is the ROM's path under its ROM folder. With the extension kept (`Albion (1995).zip.glb`), the model is for that ROM alone and wins; without it (`Albion (1995).glb`), it's for every ROM of that name.
2. The template the user chose for the game (X on the game, then Model): an id from your theme, or else from Memory Card. That list shows your templates, then Memory Card's, so a template that no system uses still has a use.
3. The user's template for the system: `ConfigDir/models/templates/<system>.glb`.
4. The user's `game_model` for the system in `systems.toml`: an id from your theme, or else from Memory Card.
5. Your theme's `[systems.<system>] game_template`.
6. Your theme's `[defaults] game_template`.
7. Memory Card's template for the system.
8. Memory Card's default template.

The user's own models (1 and 3) use the default slot chains, and a chosen template (2 and 4) uses its theme's chains.

**A system's card** (including Favourites, Recently played and All games):

1. The user's `ConfigDir/models/systems/<system>.glb`.
2. Your theme's `[systems.<system>] model`.
3. Your theme's `[defaults] system_model`.
4. Memory Card's generic card: a memory card slab with the system's name, in its colour.

The system's details screen (Y on the system) shows its card large, plays its `focused` clip, and lets the user turn it with the right stick, so its back and underside show. That's why system models have a bigger budget than game templates.

In a grid, each row is as tall as its tallest model, and shorter models are centred in that height. The exception is boxes with `shape = "media"`, which stand on the row's floor.

## 6. The model spec

| Rule | Value |
|---|---|
| Format | glTF 2.0 binary (`.glb`) with one scene and everything embedded. Images are PNG or JPEG. A file that keeps data outside itself, or needs an extension the launcher can't read (such as Draco compression), is rejected. |
| Units and axes | glTF's: metres, +Y up, the front facing +Z (towards the viewer). |
| Origin | The bottom centre: the model stands on y = 0. |
| Size | About 1 m on its largest side. The launcher fits every model to the grid, so this needn't be exact, but a model more than 10× off gets a "wrong units?" warning. |
| Materials used | Base colour (factor and texture), roughness, vertex colours, slot names, and a system card's `video` material (section 4, "Card videos"). |
| Materials ignored for now | Metallic, normal maps, emissive, unlit, alpha, texture transforms and double-sided. Support for them is planned. Until then, a model looks the same without them, only flatter. |
| Textures | At most 4 base colour textures per model, mipmapped when loaded. Normal, metallic-roughness, occlusion and emissive maps are allowed, but aren't drawn yet and don't count towards the budget. |
| Animation | Clips named `idle`, `focused` and `launch` (section 8), with node transforms, skinning and morph targets. |
| Ignored | Cameras, lights (the theme's lights are the only lights), extra scenes and other clips. |

Every model is drawn with the launcher's one shader, so a theme can't slow the renderer except through its triangles and textures.

## 7. Budgets

| Model | Triangles | Base colour textures (not counting slot art) | Materials |
|---|---|---|---|
| Game template | ≤ 2,000 | ≤ 2, each ≤ 1024² | ≤ 4 |
| A user's per-game model | ≤ 5,000 | ≤ 2, each ≤ 1024² | ≤ 4 |
| System model | ≤ 30,000 | ≤ 4, each ≤ 2048² | ≤ 8 |

Skins can have at most 64 joints, and meshes at most 8 morph targets. A menu font can be at most **4 MB**: a font for Latin text is well under that, but one with every CJK character is many times over, and is refused.

- **A model over a budget** is used, with a warning.
- **A model more than twice over** a count (triangles, textures, materials, joints or morph targets) is **rejected**, and the next model in line is used (section 5).
- **A texture larger than the budget allows** is scaled down. Its size alone never rejects a model.
- **Every texture is drawn at most 1024 pixels on its longer side.** Larger ones are scaled down when they're loaded, keeping their proportions, because textures are held uncompressed on the graphics card (a 2048² texture takes 21 MB, and a 1024² one 5 MB). Models are never drawn taller than 1080p, so the difference doesn't show. If you lay out several parts in one texture, give each part enough room at 1024.
- **A broken file** (bad JSON, data out of range, a missing image and so on) is rejected with the reason. It never crashes the launcher.

Every rejection and warning goes to the **model log**, `DataDir/logs/models.log`, which says what was wrong and what was used instead. `odyssey-scrape models-log` prints it.

- Windows: `%LOCALAPPDATA%\OdysseyLauncher\logs\models.log`
- Portable install: `userdata\logs\models.log`

Processed models are cached in `CacheDir/models/`, so each model is checked only once. An edited file is processed again, and the cache is safe to delete at any time.

**Performance:** game templates are drawn in batches, one draw call per template for every game that uses it. A template with an **idle** clip can't be batched, because every game plays the clip, so each game is drawn on its own. Give game templates `focused` and `launch` clips if you like, but keep `idle` clips for system models.

## 8. Animation clips

A model can have up to three clips. Clip names are matched like slot names (case and `.NNN` suffixes are ignored), and an object name before a `|` is ignored too, so `Armature|idle` works.

| Clip | Plays | Loops |
|---|---|---|
| `idle` | while the item isn't focused | yes |
| `focused` | while the item is focused (blending in and out over 0.25 s) | yes |
| `launch` | once, when the game starts. The emulator starts when the clip ends, or after 2 s, whichever comes first. | no |

- Clips can move, rotate and scale nodes, so split the model into objects to animate its parts (like the sample's aerials). Armatures and shape keys work too, but haven't been tested on a real model yet: if you try one, check it in the launcher. Other clips are logged as ignored.
- The grid always lifts the focused item towards the viewer and grows it a little. For any state without a clip, it also adds its own motion: a gentle bob while idle, a sway while focused, and a spin on launch. So a `focused` clip replaces the sway, and a `launch` clip replaces the spin. Your theme's `[motion]` (section 3) sets how far the sway and bob go.
- While a clip plays, the focused item is drawn on its own copy of the model, and then blended back to its rest pose. Clips should start and end near the rest pose.
- When the user inspects a game (R3, or Z on a keyboard), it fills about 75% of the window's height, plays its `focused` clip and can be turned with the right stick. Make sure your templates' textures hold up at that size.

## 9. Making models in Blender

Blender 4.x's glTF exporter produces everything the launcher needs.

**Modelling**

- Work in metres. A model about 1 m tall avoids the units warning.
- Point the model's front towards Blender's **front view** (numpad 1, looking along +Y). With the exporter's **+Y Up** option, Blender's −Y becomes glTF's +Z, which is the front.
- Put the origin at the bottom centre, and apply rotation and scale (Ctrl+A, **All Transforms**) before exporting.
- Check the triangle count with the viewport's **Statistics** overlay.

**Slot materials**

- Name each material after its slot: `cover`, `screenshot`, `label` and so on. Blender's `.001` suffixes are fine.
- Set the slot's Base Color to white. To give the slot a fallback image (`authored`), plug an **Image Texture** into Base Color.
- Unwrap each slot face so that its UVs fill 0 to 1, upright: in the UV editor, scale the island to fill the square, with the top of the art at the top.
- For a face that isn't flat and upright, add its aspect ratio as a custom property: in the material's properties, under **Custom Properties**, click **New**, name it `aspect`, and give it a Float value (for example `1.333` for a 4:3 screen). Tick **Custom Properties** when exporting, so it's written as `extras.aspect`.

**Plain materials** keep their Base Color (and texture, if any) and Roughness. On system models, `tint_system_model` or `tint` mixes plain materials towards each system's colour, so make the parts you want tinted light and neutral.

**Clips:** make one action per clip, named `idle`, `focused` or `launch`, and push each one onto the object's or armature's NLA stack so the exporter finds it. You can animate objects (location, rotation, scale), bones or shape keys.

**Export** (File > Export > glTF 2.0)

| Setting | Value |
|---|---|
| Format | glTF Binary (`.glb`) |
| Include | **Limit to Selected Objects** if the file contains anything else; tick **Custom Properties** |
| Transform | **+Y Up** (the default) |
| Data > Mesh | Apply Modifiers, UVs, Normals; vertex colours if you use them |
| Data > Material | Export; Images: Automatic (PNG or JPEG) |
| Animation | Tick **Animation**; mode **Actions** (each action becomes a clip named after it) |
| Compression | **Off** (Draco isn't supported) |

**Other formats:** users can import a Wavefront OBJ model (a zip of the `.obj`, its `.mtl` and its textures) as a game's own model. The launcher converts it to glTF and keeps its material names, so an OBJ material named `cover` is still a slot. OBJ models have no clips and must face +Z, as Blender exports them. The exception is a PS2 save icon converted to OBJ with its animation beside it (`ICON.ICO.obj` and `ICON.ICO.anim`): the launcher turns it to face the viewer and gives it a `focused` clip. For a theme, always export `.glb` from Blender.

## 10. Testing a theme

**Check a model** from the repo, after `dotnet build`:

```
.\tools\scrape-cli\bin\Debug\net10.0\odyssey-scrape.exe inspect-model --kind=template path\to\crt_tv.glb
```

It prints the triangle, material and texture counts against the budget, the slots and clips it found, the size, and every warning and error, without changing anything. Use `--kind=system` for a system model. Without `--kind`, the model is checked as a per-game model.

**Run the launcher on your theme** with a separate user folder, so your own library isn't touched. Copy the theme into `<folder>\themes\` first, and use a test library such as the synthetic one (CLAUDE.md, Commands):

```
godot --path godot -- --user-dir=<absolute folder> --theme=neon-arcade
```

| Option | Does |
|---|---|
| `--start-system=ps2` | Opens a system straight away. |
| `--nav-script=right,right,accept` | Presses buttons for you. With no emulator installed, `accept` plays the launch clip and then the launch fails harmlessly. |
| `--capture=<absolute path>.png --capture-frame=150 --fixed-fps 60` | Saves a screenshot at that frame, then quits. |
| `--no-overlay` | Hides the text, so you can check the background's corners. |
| `--open=settings` (or `power`, `keyboard`, `confirm`, `folder-picker`) | Opens a menu straight away, to check `[ui.menu]`. The `theme` step in `--nav-script` switches theme with the menu open. |
| `--ui-size=large` | Uses the large UI size, which leaves the menus less room. |
| `--layout=single/list` | Shows one system card, or one game's model, at about half the screen's height: the closest look at your models' detail. |
| `--layout=carousel/carousel`, `grid/showcase`, `coverflow/coverflow`, `grid_with_labels/grid_with_labels` | The other layouts users can choose. Coverflow shows games side on, so it shows their spines. |

The console shows the theme's diagnostics as it loads (section 3), and `logs/models.log` in the user folder has each model's report.

**Check performance** with the bench:

```
.\tools\bench-export.ps1 -AppArgs "--user-dir=<folder>", '--theme=neon-arcade', '--bench-scenario=scroll'
```

It scrolls the biggest system from the first row to the last, and reports frame times, hitches and memory. In the report, `scroll.frames` should match the same run with `--theme=memory-card`.

**Before you publish,** check that:

- `theme.toml` loads with no errors or warnings
- every model passes `inspect-model` with no warnings
- the theme looks right both with games that have art and with games that have none (a synthetic library has both)
- the `focused` and `launch` clips return to the rest pose

## 11. Troubleshooting

| You see | Why | Fix |
|---|---|---|
| Your theme isn't in the list | The folder isn't in `ConfigDir/themes/`, or `theme.toml` has a syntax error (the console names the line) | Check the path and the first error |
| A system uses Memory Card's box | Your theme doesn't assign it a template, the template was left out (a missing file or a path outside the folder), or its model was rejected | Read the console and `models.log` |
| Art is stretched or badly cropped | The face's aspect ratio is wrong | Set the material's `aspect` custom property, and export Custom Properties |
| Art is upside down or mirrored | The slot's UVs aren't upright from outside | Flip the UV island vertically or horizontally |
| A slot shows its plain colour, never art | The material isn't named after a slot, or the chain names kinds the library has no art for | Check the name (a `.001` suffix is fine), then the chain |
| A system's games show no wallpaper | Its `[systems.<id>.look.background]` replaces the theme's whole block, wallpaper included | Repeat `wallpaper` in the system's block, and check the console for `Wallpaper:` warnings |
| A card shows no logo | The chain doesn't name `logo`, the image isn't named after the system's id (`logos/megadrive.png`, not its display name), the card's model comes from another theme (so its chains are that theme's), or it's still being processed the first time | Check the chain, the id (in `systems.toml`) and the console |
| A model is tiny, or huge and warned about units | It was modelled in centimetres or millimetres | Scale it to about 1 m, and apply the scale |
| A clip doesn't play | It isn't named `idle`, `focused` or `launch`, or it wasn't exported | Rename the action, and push it onto the NLA stack |
| A game's video doesn't play | The template has no `video`, the slot it names isn't one of the model's materials, the game has no video (its details list its media), or a menu is open | Check the console's warnings and the game's media |
| "more than twice the ... may have" in the log | The model is too heavy, so it was rejected | Decimate it, or merge materials |

## 12. Publishing a theme

**Settings > Appearance > Download themes** lists themes that users can install, update and remove from the launcher. The list lives in [`GeekRhapsody/odyssey-themes`](https://github.com/GeekRhapsody/odyssey-themes), and the launcher's owner tests every theme before adding it. Each theme is a git repository of its own, which the launcher clones into the user's `themes/` folder.

**Your repository:**

- Put `theme.toml` at the top of the repository: the repository *is* the theme folder. A theme in a subfolder isn't found.
- The theme is installed into a folder named after its `id` in the list, not after your repository. Choose an id of lower-case letters, digits, `_` and `-` (`neon-arcade`), and not `memory-card`, `classic-view`, `console` or `slab`.
- Keep the history small, because users download every commit: a 20 MB model committed ten times costs them 200 MB. Commit models when they're finished, and squash early work before you submit.
- Mark binary files as binary in `.gitattributes` (`*.glb binary`, `*.png binary`, `*.webp binary`, `*.mp4 binary`), so no git setting changes their bytes in your collaborators' clones.
- Files a user adds to your theme's folder (such as their own logo) survive updates, because git doesn't track them. If a user edits one of your files, an update overwrites it, and the launcher asks them first.

**Check it** with the command the list's owner runs, from this repository after `dotnet build`:

```
.\tools\scrape-cli\bin\Debug\net10.0\odyssey-scrape.exe inspect-theme --json <your theme's folder>
```

It loads the theme as the launcher does (with every error and warning, and its line), checks each model against its budget, and prints the theme's size and an optional `covers` block listing what your theme brings (system cards and logos, templates, its own menus, videos), which the list can show. Fix every error, and name the folder after the id you want.

**Try it before you submit:** the launcher (and `odyssey-scrape themes`) can read a list from a folder with `--themes-list=<folder>`, and a local list can name a repository by a `file:///` URL, so you can install your theme the way users will:

```
godot --path godot -- --user-dir=<absolute folder> --open=themes --themes-list=<absolute folder with themes.json>
```

`tests/themes-list/themes.json` in this repository is an example list (its themes are made up, so they can't be installed).

**Submit it:** open an issue or a pull request on `odyssey-themes` with:

- the repository's https URL (users get its default branch)
- the id, the name, you as the author, and a sentence or two of description
- the oldest launcher version it needs (`min_app_version`), if it uses something new: older launchers list the theme but won't install it
- two to four 16:9 screenshots, at least the systems and one system's games, taken with `--capture` (section 10) at 1280×720 or larger. The list keeps them in `screenshots/<id>/`.

**Updates:** your theme is tested once, before it's listed. After that, whatever you push to its default branch reaches users as an update the next time they press A on it in Download themes. Nobody reviews updates, so test changes on a branch before you push them, and don't rewrite the default branch's history. If you push a version that a user's launcher can't load, it's refused there and they keep the version they had. If your theme's look changes, ask for new screenshots to be listed.
