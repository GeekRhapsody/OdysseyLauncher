# Making themes for Odyssey Launcher

This guide is for theme authors. It covers the folder and manifest, the media slots your models show, which model wins when several could, the model spec and budgets, how to make and export models in Blender, and how to test a theme. The design behind it is in [ARCHITECTURE.md](ARCHITECTURE.md) (A6 is the manifest, A7 the model spec).

Two themes come with the repo:
- **Memory Card**, the built-in theme ([`godot/themes/memory-card/`](../godot/themes/memory-card/theme.toml)). Every other theme falls back to it for anything it leaves out.
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
```

- Only `theme.toml` is required. Put models wherever you like inside the folder: the manifest names each one by its path, relative to the folder and `/`-separated. A path can't leave the folder.
- A user theme with the same id as a built-in one replaces it. The built-in Memory Card theme stays the last resort for any system or model your theme doesn't provide, so a partial theme always works.
- Models are glTF 2.0 binaries (`.glb`) only. To use OBJ or another format, convert it first (section 9).

## 3. The manifest (`theme.toml`)

A complete, commented example is the sample's [`theme.toml`](../samples/themes/retro-tv/theme.toml). Every key:

```toml
format = 1                            # optional; 1 is the only format
name = "Neon Arcade"                  # required: shown when the theme is picked
author = "Your name"                  # optional
look_transition_ms = 300              # how long a cross-fade between looks takes: 0 to 5000, default 300

[look.background]                     # icon.sys-style: one sRGB colour per screen corner, all four required
top_left     = "#1B1F4A"
top_right    = "#1B1F4A"
bottom_left  = "#04040C"
bottom_right = "#0B0B24"

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
game_template = "crt_tv"                      # the template for systems the theme doesn't assign one

[templates.crt_tv]                    # a game template: an id, a model, and optional slot chains
model = "models/templates/crt_tv.glb"
shape = "model"                       # optional: "model" (its own shape, the default) or "media" (section 4)

[templates.crt_tv.slots]              # optional; see section 4
screenshot = ["screenshot", "hero", "cover", "authored"]
label = ["logo", "generated"]

[systems.ps2]                         # per system, by the launcher's system id (see below); every key is optional
model = "models/systems/ps2.glb"      # its card (default: [defaults] system_model)
tint = false                          # default false for its own model, else tint_system_model
colour = "#2B4C9A"                    # its card's tint and the colour of its games' plain boxes
game_template = "crt_tv"              # a template id in this theme (default: [defaults] game_template)

[systems.ps2.look.background]         # the look while its games are shown; replaces the theme's block whole
top_left     = "#1E2A4E"
top_right    = "#3A2418"
bottom_left  = "#06080E"
bottom_right = "#100A08"
```

- **Colours** are `#RRGGBB` in sRGB. The four corners blend in sRGB, as on the PS2.
- **Lights** are in view space, so they stay put while the grid scrolls. Any direction but zero is valid. Lights you don't define are off.
- **Per-system looks:** a system's `background`, `ambient` or `lights` block replaces the theme's block of that name whole. Blocks it leaves out come from the theme's look. Entering a system cross-fades to its look, and leaving cross-fades back.
- **System ids** are the launcher's: `gb`, `gbc`, `gba`, `nes`, `snes`, `n64`, `gc`, `mastersystem`, `megadrive`, `saturn`, `dreamcast`, `psx`, `ps2` and `psp`, plus any system the user defines. An entry for a system the user doesn't have is ignored.
- **Mistakes never stop the launcher.** Each problem is reported with its file, line, column and key, for example:

  ```
  user/themes/neon-arcade/theme.toml:12:1: error: templates.box.model: 'box.glb' doesn't exist in the theme's folder
  ```

  - A TOML syntax error, or an unsupported `format`, rejects the whole theme, and the built-in one is used.
  - A bad look block falls back to the built-in theme's.
  - A template whose model is missing, or isn't a `.glb` inside the folder, is left out. Whatever named it falls through to the next model in line (section 5).
  - A bad slot chain falls back to that slot's default chain.
  - A bad `shape` is an error, and the template keeps its own shape.
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

System cards have no art. Their slots show `generated` where they can (a card's `label` shows the system's name), and `authored` otherwise.

The sample's television, for example:

```toml
[templates.crt_tv.slots]
screenshot = ["screenshot", "hero", "cover", "authored"]   # the screen; "authored" is the model's own test card
label = ["logo", "generated"]                               # the stand's plate: the logo, else a printed title
```

### How art fits a face

- **UVs:** a slot's first UV map (TEXCOORD_0) must span 0 to 1 across the face, upright as seen from outside. Sampling is clamped.
- **Cropping:** art is centre-cropped to fill the face. The face's aspect ratio (width over height) comes from the material's custom property `aspect`. If a material has none, it's measured from the slot mesh's bounds, which works for flat, upright faces. For a curved or tilted face, set `aspect` (section 9).
- **Colour:** make each slot material's base colour **white**, because it multiplies the art. Its base colour texture, if it has one, is what `authored` shows.
- **Resolution:** art is streamed at 512² for the cover and 256² for every other slot, whatever the source's size. Only the slots whose chains name a media kind stream anything, so an unused slot costs nothing.

### Boxes shaped by the art (`shape = "media"`)

Box art doesn't come in one size: DOS big boxes alone range from tall to square to landscape, thin to deep. With `shape = "media"` on a template, each game's box takes the shape of its own art, so nothing is cropped:
- **The front** is as wide over high as the game's `cover` image (that image itself, even if a chain shows something else on the front). The larger of the two fills the grid cell.
- **The depth** is the game's `spine` width over its height, times the box's height. Scraped images are scaled to a set height (ScreenScraper's are 700 pixels high), so only these proportions are used, never sizes.
- **Without a cover or a spine**, the model's own proportions stand in.
- **Out-of-range art** is clamped: covers to between 1:4 and 4:1, and spines to between 2% and 50% of the height.
- **The grid's cells** fit the widest and tallest box in the list being shown, so a list of tall boxes keeps tight columns.
- **The `cover`, `back` and `spine` faces** take the new proportions. The back's art is cropped to the cover's shape.

The built-in theme's `big_box` (DOS) does this. To make a model for it:
- **It must have a `cover` material**, or the key is ignored, with a warning.
- **The launcher moves each half of the model**, left and right, top and bottom (split at half the height), front and back, by however much the box grows or shrinks. Nothing is stretched, so corners and bevels keep their size. So keep vertices off the centre planes (x = 0, z = 0, and half the height), keep corner and bevel detail near the edges, and make `cover`, `back` and `spine` whole faces of the box.
- **A model with animation clips keeps its own shape**, with a warning: the launcher reshapes a template's one merged mesh, not a node tree.
- **It costs nothing per frame:** the box is reshaped in the item shader from numbers worked out when a game's cell is bound.

## 5. Which model is used (precedence)

For each game and each system card, the launcher tries these candidates in order and uses the first that loads. A candidate that's missing, broken or rejected (section 7) falls through to the next one.

**A game's model:**
1. The user's own model for that game, in the media folder with its art: `DataDir/media/<system>/model/<rel path>.glb`, where `<rel path>` is the ROM's path under its ROM folder.
   - With the extension kept (`Game (Europe).iso.glb`), it's for that ROM only.
   - Without it (`Game (Europe).glb`), it's for every ROM of that name.
   - Users choose one in the game's options (X on the game, then Model), or import one with `odyssey-scrape import-model` (section 10).
2. The user's template for the system: `ConfigDir/models/templates/<system>.glb`. Users choose one in the system's options (X on the system, then Game template).
3. The user's `game_model` for the system in `systems.toml`: a template id in the active theme, else in the built-in one. The system's options list your theme's templates for this.
4. Your theme's `[systems.<system>] game_template`.
5. Your theme's `[defaults] game_template`.
6. The built-in theme's template for the system.
7. The built-in theme's default template (`dvd_case`).

**A system's card:**
1. The user's `ConfigDir/models/systems/<system>.glb`, chosen in the system's options (X on the system, then System model).
2. Your theme's `[systems.<system>] model`.
3. Your theme's `[defaults] system_model`.
4. The built-in theme's generic card.

User models (levels 1 and 2) use the default slot chains. Nothing is looked for per game while the grid scrolls: per-game models are indexed when the library is scanned.

## 6. The model spec

| Rule | Value |
|---|---|
| Format | glTF 2.0 binary (`.glb`) with one scene and everything embedded. Images are PNG or JPEG. A file that keeps data outside itself, or that needs an extension the launcher can't read (Draco compression, for example), is rejected. |
| Units and axes | glTF's: metres, +Y up, the front facing +Z (towards the viewer). |
| Origin | The bottom centre: the model stands on y = 0. |
| Size | About 1 m on its largest side. You don't have to be exact: the launcher fits every model to the spec, and fits per-game models into the grid cell. More than 10× off gets a "wrong units?" warning. |
| Materials honoured today | Base colour (factor and texture), roughness, vertex colours, and the slot names. |
| Materials ignored for now | Metallic, normal maps, emissive, unlit, alpha, texture transforms and double-sided. They're planned. Until then, don't rely on them: a model looks the same without them, just flatter. |
| Textures | Base colour textures, at most 4 per model. They're mipmapped when loaded. Normal, metallic-roughness, occlusion and emissive maps are allowed but not drawn yet, so they don't count towards the budget. |
| Animation | Clips named `idle`, `focused` and `launch` (section 8), with node transforms, skinning and morph targets. |
| Ignored | Cameras, lights (the theme's lights are the only lights), extra scenes, and other clips. |

Every model, whether it's the built-in theme's, yours or the user's, is drawn with the launcher's one item shader. So a model never adds a shader variant, and nothing a theme ships can slow the renderer beyond its triangles and textures.

## 7. Budgets

| Model | Triangles | Base colour textures (not counting slot art) | Materials |
|---|---|---|---|
| Game template | ≤ 2,000 | ≤ 2, each ≤ 1024² | ≤ 4 |
| A user's per-game model | ≤ 5,000 | ≤ 2, each ≤ 1024² | ≤ 4 |
| System model | ≤ 30,000 | ≤ 4, each ≤ 2048² | ≤ 8 |

Skins have at most 64 joints, and meshes at most 8 morph targets.

- **Over a budget,** the model is used, with a warning.
- **More than twice over** a count (triangles, textures, materials, joints or morph targets), the model is **rejected**, and the next model in line is used (section 5).
- **A texture larger than the budget's side** is scaled down when the model is first processed. Its size alone never rejects a model.
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

So a `focused` clip replaces the sway, and a `launch` clip replaces the spin.

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

**Other formats:** users can import a Wavefront OBJ model (a zip of the `.obj`, its `.mtl` and its textures) as a game's own model. The launcher converts it to glTF, keeping the material names, so an OBJ material named `cover` is still a slot. OBJ has no clips, with one exception: a PS2 save icon converted to OBJ with its shape animation beside it (`ICON.ICO.obj` and `ICON.ICO.anim`, as the PS2 icon database's zips have them) gets a `focused` clip, so it animates when it's selected. For a theme, export `.glb` from Blender.

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

## 11. Troubleshooting

| You see | Why | Fix |
|---|---|---|
| Your theme isn't offered | The folder isn't in `ConfigDir/themes/`, or `theme.toml` has a syntax error (the console names the line) | Check the path and the first error |
| A system uses the built-in box | Its template was left out (missing file, or a path outside the folder), or its model was rejected | Read the console and `models.log` |
| Art is stretched or cut off badly | The face's aspect ratio is wrong | Set the material's `aspect` custom property, and export Custom Properties |
| Art is upside down or mirrored | The slot's UVs aren't upright from outside | Flip the UV island vertically or horizontally |
| A slot shows the plain colour, never art | The material isn't named after a slot, or the chain names kinds the library has no art for | Check the name (a `.001` suffix is fine), then the chain |
| The model is tiny, or huge and warned about units | It's modelled in centimetres or millimetres | Scale it to about 1 m, and apply the scale |
| A clip doesn't play | It isn't named idle, focused or launch, or it wasn't exported | Rename the action, and push it onto the NLA stack |
| "more than twice the ... may have" in the log | The model is too heavy, so it was rejected | Decimate it, or merge materials |
