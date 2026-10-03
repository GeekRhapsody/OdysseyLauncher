# Odyssey Launcher: roadmap

Each milestone ends when all of its acceptance criteria are met, including a bench run on the baseline hardware in both modes. The baseline is a Steam Deck on Windows 11, run handheld at 1280×800 and docked at 3840×2160 and 59.94 Hz. Record the results in [Progress](#progress). The design lives in [ARCHITECTURE.md](ARCHITECTURE.md).

Performance targets, as revised by M1 ([SPIKE_RESULTS.md](SPIKE_RESULTS.md); the full list is in ARCHITECTURE.md A3). The reworded hitch target and the new targets are proposals awaiting the owner's sign-off.
- First interactive frame under 1 s **for our code**, on a warm start with a 10,000-game library. It's timed from the first autoload's `_EnterTree` to `interactive` (`app_startup_ms` in the bench). Engine and .NET start-up before our code is reported, but it isn't part of the target.
- No dropped frames while scrolling: p99 frame interval ≤ 1.1× the refresh interval.
- **No hitches caused by the launcher** while textures stream in. Over 3 × 60 s scrolls:
  - hitches are no more than the same session's no-texture control
  - 0 frames exceed 2× the refresh interval
  - there are 0 hitches in fullscreen
- The visible grid is textured ≤ 100 ms after the first frame, and ≥ 99% textured while scrolling at the maximum repeat speed.
- The working set is ≤ 512 MB while browsing. The main thread allocates ≤ 4 KB per 60 s scroll.

A hitch is any frame interval longer than 1.5× the refresh interval.

## M1: Performance spike

Prove, or revise with evidence, the targets on the Deck before building features.

**Scope**
- Prerequisites (done 2026-09-27):
  - Install the Godot 4.7.2 .NET export templates.
  - Add an ExportRelease export preset (`godot/export_presets.cfg`), plus a script to export and bench (`tools/bench-export.ps1`).
- Add Tomlyn and Microsoft.Data.Sqlite. Both are part of the decided stack.
- Build a synthetic-library generator: 10,000 games in one system, plus 20 small systems, with generated JPEG covers.
- Build a prototype virtualised grid, with pooled items and texture streaming, using a placeholder box template.
- Add `--bench` scenarios: `boot`, and `scroll` (a scripted scroll at maximum repeat speed).
- Run the experiments in ARCHITECTURE.md A3:
  - renderer × driver
  - per-node materials versus `Texture2DArray`
  - derivative format and upload path
  - upload budget and worker count
  - ReadyToRun and the shader baker
  - config parse cost
  - 4K render scale
  - SQLite's native load in an editor run and in an export
  - `.glb` conversion on a worker thread
  - a net10.0 comparison build

**Acceptance**
- `docs/perf/m1-spike.md` gives, for every configuration tried: the bench JSON, the exact commands, and the machine details.
- On an exported build of the chosen configuration, in both modes:
  - Over 5 warm starts, the median `app_startup_ms` (our code: first autoload to `interactive`) is under 1000 ms. Engine and .NET start-up is recorded alongside.
  - A 60 s scripted scroll across the 10,000-game system has 0 hitches after the first 60 frames.
  - The p99 frame interval is at most 1.1× the refresh interval.
  - The main-thread allocation ceiling during the scroll is set, and met.
- For any missed target, the doc records the best result, the bottleneck and a proposed revised target. The owner signs this off before M2 starts.
- The decisions log in ARCHITECTURE.md records the choices (renderer, driver, item rendering, texture pipeline, budgets).

**Closed on 2026-09-27 with a reduced scope.** The owner scoped M1 to the grid, texture and renderer spike. The results are in [SPIKE_RESULTS.md](SPIKE_RESULTS.md), and the spike code is on branch `spike/grid-perf`. These items weren't done, and moved:
- to M2: Tomlyn and Microsoft.Data.Sqlite; the config-parse cost; SQLite's native load; the 20-system synthetic library and the `boot` scenario; the net10.0 build
- to M5: ReadyToRun and the shader baker; handheld (undocked) mode; 3840×2160 docked; FSR1 against bilinear; PresentMon for the periodic present delay
- to M6: `.glb` conversion on a worker thread

The hitch target was met by the chosen configuration, but it's reworded (see above). The owner still needs to sign off the revised targets.

## M2: Core data layer

**Scope**
- Config loading, merging and validation for `settings.toml`, `systems.toml` and `emulators.toml`, with embedded defaults, aliases and variables.
- `library.db` and `userdata.db`, with migrations, backups and the attach-for-joins query path.
- The scanner (extensions, recursion, excludes, `.m3u`, `path_key`), user override indexing, `RebuildAsync`, and the `ILibrary` queries.

**Acceptance**
- Config tests cover each class of error (syntax, unknown key, missing key, unknown emulator, bad placeholder) and variable cycles. Diagnostics give file:line:column.
- Migration tests cover:
  - fresh creation
  - upgrade from every previous version
  - refusal of a newer `userdata.db`
  - rebuild of a newer or broken `library.db`
  - the backup being written and pruned to 3
- Scanner tests cover add, remove, rename, case-only rename (user data kept), `.m3u` hiding and case-fold collisions.
- A golden test deletes `library.db`, rebuilds it offline, and compares it with the incrementally built DB (ids and timestamps excluded).
- On the Deck, in ExportRelease:
  - A full scan of 10,000 files takes under 3 s.
  - A rescan with no changes takes under 0.5 s.
  - `GetGamesAsync` for 10,000 games takes under 50 ms.
- The M1 boot target still holds with real config and DB loading.
- Carried over from M1, with results in `docs/perf/`:
  - add Tomlyn and Microsoft.Data.Sqlite
  - measure the config-parse options (A3)
  - measure SQLite's native load in an editor run and in an export
  - add the 20-system synthetic library and a `boot` bench scenario
  - bench a net10.0 comparison build (adopting it needs the owner's approval)

**Closed on 2026-09-28 with a reduced scope.** The owner scoped M2 to Launcher.Core (config, database and ROM scanning), with no Godot code. Every Core criterion above is met; the numbers are in [perf/m2-core.md](perf/m2-core.md) and the [log](#log). These items need the app, or belong with later features, so they moved:
- to M4: indexing the user's art override files; re-checking the ScreenScraper system ids against `systemesListe.php`
- to M5: the M1 boot target with real config and DB loading; SQLite's native load in an editor run and in a Godot export; the 20-system synthetic library and the `boot` bench scenario; the Godot side of the net10.0 comparison
- to M6: indexing the user's model override files

## M3: Launching

**Scope**
- Emulator profiles and templates, with built-in profiles for RetroArch cores and common standalone emulators.
- Rejection of `.bat` and `.cmd` targets.
- A Windows `IProcessRunner`: the child is created inside a job object (`PROC_THREAD_ATTRIBUTE_JOB_LIST`), and the runner waits until the job is empty, so stub launchers are tracked.
- A Windows `IWindowFocus`.
- While a game runs: rendering off, textures evicted, input ignored.
- Play sessions and stats.
- A `--launch=<system>/<rel path>` debug argument.

**Acceptance**
- Template tests cover spaces, Unicode, `&` and `%` in names, `{{`/`}}` escaping, and unknown placeholders or missing variables.
- A real game launches from the app, including through a stub launcher. The launcher stops rendering while the game runs, and gets focus back on exit.
- The play session is recorded with the correct duration. Sessions left open by a crash are closed on the next start.
- A missing executable, a missing ROM, or an immediate non-zero exit each produces a clear message.

**Closed on 2026-09-28.** Every criterion a script can check is met (see the [log](#log)). The one that needs a person at the machine, a real game launching from the app directly and through a stub launcher, with rendering stopped while it runs and the foreground back on exit, is the owner's manual test: [manual-tests.md](manual-tests.md#m3-launching-a-real-emulator-and-focus). The same code path passes headless against the fake emulator, in the editor run and in the export. These items moved or were dropped:
- to M5: evicting textures while a game runs (the texture streamer arrives in M5); making the navigation input router honour `LaunchController.IsInputBlocked`; building the controller in the post-`interactive` warm-up instead of on first use
- still to do, whenever each emulator is installed: a launch with each built-in profile. The RetroArch core file names and `pcsx2-qt.exe` were checked against a RetroBat install.
- dropped: an escaped mode for `.bat` and `.cmd` targets. Stub launchers are handled by the job object, and cmd.exe's re-parsing can't be made safe for every file name.

## M4: Scraping and media pipeline

**Scope**
- ScreenScraper and SteamGridDB clients, with quota and rate handling.
- Match resolution (manual, then stored, then filename).
- Deterministic media, and `scraped/` responses with credentials stripped.
- Derivative baking off the main thread.
- User art overrides.

**Acceptance**
- Tests show a manual match surviving both a re-scrape and a library rebuild.
- A rebuild with the network disabled restores metadata and media links.
- Unit tests use recorded HTTP fixtures only.
- A live scrape of a 50-game set is documented, with its commands and results.
- Secrets appear in no log, saved JSON or bench output (a test scans for them).
- Derivatives regenerate when their source file changes.
- Carried over from M2:
  - ~~the scanner indexes the user's art overrides (`ConfigDir/media/`) into `media` with source `user`~~ (done in M5)
  - the default systems' `screenscraper_id` values are checked against `systemesListe.php`
- Carried over from M5:
  - bake derivatives for the user's art (and scraped art), with the encoder M4 picks; until then a cover with no derivative shows as a plain box
  - ReadyToRun, if the owner approves the crossgen2 runtime pack from NuGet

**Closed on 2026-09-28.** The owner's M4 brief: all three providers (ScreenScraper, SteamGridDB, IGDB) behind the provider interface with capability maps; provider selection by the configured default and fallback order, skipping providers without credentials and saying so; credentials from a user file outside the repo; scrape a game, a system and everything missing, and clear a game, as services with progress events; a resumable, cancellable job queue with per-provider limits and backoff; stored matches with manual ones winning, overrides never overwritten, status, provider and time per game; the cover and box texture plus the architecture doc's metadata, converted off the main thread by the approach SPIKE_RESULTS.md chose (a 512² BC7 thumbnail, and the full-size original kept); fixture-only tests; and a console tool for live testing. All of it is done ([perf/m4-scraping.md](perf/m4-scraping.md) and the [log](#log)). Against the acceptance criteria:
- **A manual match survives a re-scrape and a rebuild:** tested (`A_manual_match_wins_and_survives_a_rescrape_and_a_rebuild`).
- **A rebuild with the network off restores metadata and media links:** tested, with every request failing; a recreated `library.db` gets them back on its first scan too.
- **Recorded fixtures only:** the scraping tests answer from `tests/Launcher.Core.Tests/Scraping/Fixtures/` through a fake handler, which fails the test on any request it has no route for.
- **Secrets appear in no log, saved JSON or bench output:** a test scrapes with all three providers (ScreenScraper echoing its credentials, as it does) and scans every file written under DataDir, both databases included, and the log, for every credential, raw and URL-encoded. Bench output never sees credentials.
- **Derivatives regenerate when their source changes:** tested (the key includes the source's size and time; the stale derivative is removed).
- **Carried over, done:** derivatives for the user's art and scraped art, with our own BC7 encoder (the app bakes missing ones after its background scans).
- **Not done, needing the owner:**
  - a live scrape of a 50-game set: it needs the owner's credentials. `odyssey-scrape` runs it; the steps are in [manual-tests.md](manual-tests.md#m4-a-live-scrape)
  - ~~checking the default `screenscraper_id` values against `systemesListe.php`~~: done 2026-10-03 with `odyssey-scrape ss-systems` (Progress, "ScreenScraper system ids")
  - ReadyToRun: still waits for the owner's approval of the crossgen2 runtime pack

## M5: 3D navigation

**Scope**
- Systems grid → games grid → launch, with back navigation.
- Favourites and Recently played virtual systems.
- Keyboard and gamepad mapping, hold-to-scroll acceleration, and page and letter jumps.
- The virtualised grid, with streaming and the opaque cover fade.
- Pre-rendered font glyphs.

**Acceptance**
- The M1 targets hold in both modes, with a real library of at least 2,000 games and with the 10,000-game synthetic set.
- Captures of both grids, the focus state and the transition have been reviewed.
- Every screen can be driven with a gamepad only.
- Carried over from M1:
  - measure ReadyToRun and the export shader baker
  - bench handheld (undocked, 1280×800 fullscreen) and 3840×2160 docked
  - compare FSR1 with bilinear at 0.5 scale
  - test the proposed 8-uploads-per-frame cap
  - identify the periodic ~5 s present delay, with PresentMon if the owner approves installing it
- Carried over from M2:
  - the M1 boot target holds with real config and DB loading, in an export
  - measure SQLite's native load in an editor run and in an export (M3 showed it loads in both)
  - add the 20-system synthetic library and a `boot` bench scenario
  - the Godot side of the net10.0 comparison (Core alone gained nothing: [perf/m2-core.md](perf/m2-core.md))
- Carried over from M3:
  - evict textures while a game runs, and restore them after
  - the input router drops input while `LaunchController.IsInputBlocked`
  - build the launch controller during the post-`interactive` warm-up (building it at boot cost 10–24 ms: [perf/m3-launching.md](perf/m3-launching.md))

**Closed on 2026-09-28.** The owner's M5 brief: boot straight into the systems grid from the DB within the targets, with timings in `--bench`; systems → games → launch, with back, animated transitions and focus memory; the five box templates generated by a Godot tool script and exported to `.glb`; spines and backs generated from front art, and plain boxes with titles when there's none; controller and keyboard navigation with repeat acceleration; and a PS2-style overlay with the architecture doc's metadata. All of it is done ([perf/m5-navigation.md](perf/m5-navigation.md), [captures](perf/m5/captures.jpg), and the [log](#log)). Against the acceptance criteria:
- **The M1 targets**, with the real library (9,422 games on the NAS) and the 10,000-game synthetic set: start-up of our code, textured ≤ 100 ms and ≥ 99%, hitches no more than the control's, 0 frames over 2× while scrolling, the working set, the pool and the main-thread allocation are all met. **Not met, with evidence that it isn't the launcher:** p99 ≤ 1.1× (about 21 ms windowed and 22 ms fullscreen, the same for the no-texture control and with the grids hidden) and 0 hitches in fullscreen (the fullscreen control has them too). A 430–480 ms frame 3 frames after interactive, in some fullscreen runs, is unexplained. All three need PresentMon.
- **Captures** of both grids, the focus state, the spine and back, and the transition were reviewed.
- **Gamepad only:** every screen has a gamepad path (D-pad or stick, A, B, Y, shoulders, triggers, View), and `--nav-script` drives the same path in checks. Pressing real buttons is the owner's manual test ([manual-tests.md](manual-tests.md#m5-navigation-with-a-controller)).
- **Carried over, done:** the shader baker (on: it halves a cold start); the 20-system library and the `boot` scenario; the boot target with real config and DB in an export; SQLite's native load in both builds (73–87 ms export, 86–125 ms editor, for opening both DBs); the upload cap (no difference, kept); evicting textures during a game; the input router honouring `IsInputBlocked`; the launch controller built in the warm-up.
- **Moved or not done:**
  - to M4: baking derivatives for real art (above); ReadyToRun, which needs a NuGet pack and the owner's approval
  - to M6: the LRU texture cache and the focused item's full-resolution upgrade; theme loading and per-system looks (M5 uses the default look)
  - still to do, needing the owner or the hardware: handheld (undocked) mode; 3840×2160 docked (the desktop ran at 2560×1440); PresentMon; a real game launched from the grid (the owner's manual test; the launch path itself passes the headless smoke test)
  - FSR1: not available on the Mobile renderer, so bilinear stays
  - the Godot side of the net10.0 comparison: needs every project's TFM changed on a branch; Core alone gained nothing

## M6: Theming and custom models

**Scope**
- Theme loading and validation.
- The gradient, lights and per-system looks, with cross-fades.
- ~~The five built-in templates~~ (done in M5: `dvd_case`, `jewel_case`, `cartridge_box`, `clamshell`, `umd_case`).
- Carried over from M5: the LRU texture cache and the focused item's full-resolution art; per-system looks and cross-fades.
- Runtime `.glb` conversion and caching, material remapping, media slots, and idle/focused/launch clips with procedural fallbacks.
- `ModelInspector` budgets.

**Acceptance**
- Tests use fixture `.glb` files that are in budget, over budget and more than 2× over (rejected, with fallback), plus slot and clip name matching.
- Captures of the default theme and one alternative theme. The corner colours match their hex values.
- The M1 targets hold with in-budget custom models on screen.
- Carried over from M1: runtime `.glb` conversion on a worker thread is measured.
- Carried over from M2: the scanner indexes the user's model overrides (`ConfigDir/models/games/`), so nothing is probed per item at runtime.

**Part 1 done on 2026-09-29: the theme system and media binding.** The owner's brief for part 1: theme manifest loading and validation, with errors naming the file and key, from user theme folders plus the built-in theme; per theme, a model and an icon.sys-style background and lights for each system, optional game templates per system and a theme-wide default; media binding, where every material named after a media slot gets the game's media through the template's per-slot fallback chain, ending with the material's authored texture, and a game's media changing rebinds it without reloading its model; the default theme rebuilt on this system, with the M5 boxes as its templates and no special-case code for them; each game's model resolved in the architecture doc's precedence; the batched rendering kept for games sharing a template, only the slots a template uses loaded, and slot media standardised to fixed sizes; switching theme at run time; Core tests for manifests, precedence and fallback resolution; a capture of a test theme with a 3-slot template; and `--bench` against the targets with a 3,000-game library. All of it is done ([perf/m6-themes.md](perf/m6-themes.md), [captures](perf/m6/captures.jpg), and the [log](#log)). Against the M6 criteria so far:
- **Captures of the default theme and an alternative one:** done (Memory Card and Slot Showcase). **Corner colours:** exact on Forward+; within 2/255 on the Mobile renderer, whose 3D buffer the background is composited through (A6).
- **Carried over from M1, runtime `.glb` conversion on a worker, measured:** every model is now parsed and converted on a worker; the built-in boxes take about 27 ms each, in parallel, and a per-game model 7.2 ms.
- **Carried over from M2, the scanner indexes `ConfigDir/models/games/`:** done (media kind `model`).
- **Slot name matching:** tested (case and Blender suffixes). Clip name matching: part 2.
- **The M1 targets with custom models on screen:** met with the test theme's user models (a user theme's `.glb` files) on screen; a scroll with per-game models on screen isn't benched yet.

**Closed on 2026-09-30 with part 2: user-supplied models and theme authoring.**

The owner's brief for part 2:
- importing a user's `.glb` for a game into its model slot, as a Core service for M7's game options panel, with a console command to test it now
- converting a Wavefront OBJ zip to `.glb`
- run-time `GLTFDocument` loading for user and theme models: fitted to the cell, media bound by slot names, optional idle, focused and launch clips, and no `cover` required
- budgets enforced at import (textures scaled down, a warning over the triangle budget, never a crash on a bad file, with a fall back to the next model in line and the error in a log the user can read)
- processed models cached, and processed again when their file changes
- games with their own model drawn individually beside the batched items, with `--bench` showing that a system with a few hundred of them meets the targets
- clearing a game's metadata removes its model
- a sample theme with a custom system model and a game template that isn't a box
- `docs/THEMING.md` for theme authors using Blender

All of it is done ([perf/m6-models.md](perf/m6-models.md), [captures](perf/m6/part2/captures.jpg), [THEMING.md](THEMING.md), and the [log](#log)).

Against the M6 criteria:
- **Fixture `.glb` files in budget, over budget and more than 2× over (rejected, with fallback):** tested. `ModelInspectorTests` writes the fixtures with `GltfBuilder`, since their size is the point. The rejection falls through to the next model in line through `ModelCache`, and it's logged.
- **Slot and clip name matching:** tested (clips: case, Blender's `.NNN` suffix and an `Armature|` prefix).
- **Captures of the default theme and an alternative one:** part 1, plus the sample theme now.
- **The M1 targets with in-budget custom models on screen**, with 300 per-game models in a 3,000-game library, on the export:
  - Met: 0–1 hitches against the control's 0–2, 0 frames over 2×, 100% textured, the visible grid in 14–18 ms, 64 B on the main thread, and 20% less GPU time than part 1's one-MultiMesh-per-model design.
  - Not met, as in every milestone since M5 and the same for the control: p99, and fullscreen hitches.
  - **At the limit:** the working set is 512–515 MB against 512 MB, down from 548–558 MB with part 1's design. Each resident per-game model costs about 0.3 MB, mostly D3D12 buffer placement, so a list with many more models would pass the target. The options are in the perf doc, for the owner.
- **Carried over from M1 and M2:** done in part 1.

Moved or not done:
- to later (not scheduled), needing the owner's choice:
  - streaming per-game models by the visible rows (or packing their meshes), for lists with many hundreds of them
  - the rest of material remapping (metallic, normal, emissive, unlit, alpha, texture transform), which A7 now lists as planned; mipmapped user textures are done
  - carried over from M5: the LRU texture cache and the focused item's full-resolution art
- ReadyToRun, which would take the new converter's first-call JIT (+33 ms of our start-up) off the boot: still waits for the owner's approval of the crossgen2 pack
- the owner's manual test: a Blender model imported for a real game, and the sample theme's clips on the real display ([manual-tests.md](manual-tests.md#m6-part-2-your-own-models-the-sample-theme-and-clips)). Skinned and morph-target clips are untested.

## M7: Settings UI

**Scope**
- Controller-navigable screens for ROM folders per system, the emulator per system and per game, title overrides, the theme, and scraper credentials (masked).
- Rescan and scrape actions with progress.

**Acceptance**
- TOML writes preserve comments and formatting (round-trip tests) and contain only changed values.
- Secrets are written only to `secrets.toml`.
- Input is validated before saving.
- Changes apply without a restart where feasible.

**Part 1 done on 2026-09-30: the shared UI components and the main settings screen.**

The owner's brief for part 1:
- shared components, as reusable scenes:
  - an on-screen keyboard (Godot has none on Windows desktop)
  - folder and file pickers wherever the app asks for a path: drives, mapped network drives and quick-access places behind the platform interface (with a Linux stub); the D-pad, confirm to enter, back to go up, the shoulders to page, jump-to-letter; typing a path (`\\server\share` too); filters per use, and a thumbnail for images; a virtualised list, listed off the main thread; inaccessible folders, disconnected drives and slow shares handled without freezing; the last location per use
  - confirmation dialogs, and a progress display bound to the M4 events, cancellable and not blocking navigation
- the main settings screen: the ROM root and per-system ROM folders, emulator profiles and their programs, the theme; the default provider, fallback order and credentials for ScreenScraper, SteamGridDB and IGDB (masked, stored in the user's config, with a connection test each); rescan, and "scrape all missing" saying how many games it will take on first
- config written back to the TOML files, keeping the user's comments if Tomlyn's syntax tree allows it (or the trade-off explained first)
- everything controller-navigable, with the mouse and keyboard working too; every screen and component checked with `--capture`, the pickers on a folder of thousands of files

All of it is done ([perf/m7-settings.md](perf/m7-settings.md), [captures](perf/m7/captures.jpg), and the [log](#log)). Tomlyn 2.10.1's syntax tree round-trips byte for byte and can be edited in place, so comments are kept with no trade-off to decide. Against the M7 criteria so far:
- **TOML writes preserve comments and formatting, and contain only changed values:** round-trip tests (`TomlEditorTests`, `ConfigWriterTests`), and checked in the app: a commented `settings.toml` kept every comment when the theme was saved, and a system's new folder went into `systems.toml` as one new table.
- **Secrets are written only to `secrets.toml`:** tested, and checked in the app: a key typed on the on-screen keyboard is in `secrets.toml` and in no other file or log.
- **Input is validated before saving:** `ConfigInput` checks folders, programs, credentials and the provider order; then the edited files are loaded as the app would load them, and an edit that brings a new error writes nothing.
- **Changes apply without a restart:** the theme switches at once; changed ROM folders rescan what they affect; emulators apply at the next launch; new credentials and scraping settings give the next scrape a new service.

A real pad, the mouse and a physical keyboard on the Deck, a live connection test and a live "scrape all missing" are the owner's manual test ([manual-tests.md](manual-tests.md#m7-part-1-the-settings-screen)).

**Closed on 2026-10-01 with part 2: the item options panels.**

The owner's brief for part 2, reusing part 1's components (on-screen keyboard, pickers, confirmation dialogs, progress):
- a system's options, on the West (X) button: its ROM folders (folder picker), its emulator, its model and template overrides (file picker for `.glb`), and "scrape this system", saying how many games it will affect
- a game's options, on X: its emulator, its model (file picker for `.glb`), metadata editing, each media slot with its current image and source (scraped, the user's or none) and the user's own image per slot from the image picker, "scrape this game", and "clear metadata" with a confirmation saying it removes scraped data, every image including the user's, and edits
- after any scrape, edit or image change, the affected items in the 3D grid update without a restart
- each panel checked with `--capture`, including a game with the user's images on its box

All of it is done ([perf/m7-items.md](perf/m7-items.md), [captures](perf/m7/part2/captures.jpg), and the [log](#log)). The slots are the design's eight image kinds: the brief's "support texture" (ScreenScraper's disc or cartridge art) is the `label` slot, and there's no video slot, because the design has no video kind (A7; the decisions log). Against the M7 criteria:
- **TOML writes preserve comments and formatting, and contain only changed values:** part 1; part 2's one TOML write, a system's `game_model`, goes through the same `ConfigWriter`. Everything else part 2 saves is the user's data in userdata.db (overrides, the emulator) or files in ConfigDir (images, models).
- **Secrets are written only to `secrets.toml`:** part 2 writes none.
- **Input is validated before saving:** typed metadata by `MetadataInput` (one line and a length; dates and ratings parsed), on the keyboard before Done; images by their headers and models by `ModelInspector` before anything is copied.
- **Changes apply without a restart:** images and a game's model rebind its cell in place (MediaChanged); titles from scrapes, clears and edits are renamed in place; a system's models and template reload the theme in the background; an emulator applies at the next launch. Each was checked in a capture taken in the same run as the change.

Moved or not done:
- manual matching (choosing a provider's game by hand), listed with part 2 when part 1 closed but not in the part 2 brief: done since, on 2026-10-01 (Progress, "manual matching")
- a video slot: not in the design; the owner's choice
- scraping `label` art (ScreenScraper's "support-texture"): no provider is mapped to it yet, so the slot takes the user's own images only
- the app still doesn't resume a scrape batch left unfinished when it closed (part 1)
- the owner's manual test: a real pad on the panels, and a live "scrape this game" and "scrape this system" ([manual-tests.md](manual-tests.md#m7-part-2-item-options))

## Progress

Update this at the end of every milestone: the status, the date, and the evidence (commit, bench JSON and captures).

| Milestone | Status | Finished | Evidence |
|---|---|---|---|
| Scaffold | Done | 2026-09-27 | Initial commit; `tools/verify.ps1` green; capture corners exact; bench baseline below |
| M1 Performance spike | Done (reduced scope; the revised targets need the owner's sign-off) | 2026-09-27 | [SPIKE_RESULTS.md](SPIKE_RESULTS.md); per-configuration JSON in [perf/m1/](perf/m1/); spike code on branch `spike/grid-perf` (`e165f58`, `7fe35ea`); scaffold matrix in [perf/m1-spike.md](perf/m1-spike.md) |
| M2 Core data layer | Done (reduced scope: Core only; app-side items moved to M4–M6) | 2026-09-28 | [perf/m2-core.md](perf/m2-core.md); 134 tests, including the scan benchmarks; see the log below |
| M3 Launching | Done (a real emulator and focus are the owner's manual test: [manual-tests.md](manual-tests.md#m3-launching-a-real-emulator-and-focus)) | 2026-09-28 | [perf/m3-launching.md](perf/m3-launching.md), bench JSON in [perf/m3/](perf/m3/); 217 tests; `verify.ps1` now ends with a headless `--launch` through the fake emulator; see the log below |
| M4 Scraping and media pipeline | Done (the live 50-game scrape needs the owner's credentials; the `systemesListe.php` check was done 2026-10-03: [manual-tests.md](manual-tests.md#m4-a-live-scrape)) | 2026-09-28 | [perf/m4-scraping.md](perf/m4-scraping.md), bench JSON in [perf/m4/](perf/m4/), [real cover capture](perf/m4/real-cover-bc7.png); 321 tests, 62 of them new for scraping and derivatives; see the log below |
| M5 3D navigation | Done (p99 and fullscreen hitches not met, the same without the launcher's work; handheld, 4K and PresentMon still to do) | 2026-09-28 | [perf/m5-navigation.md](perf/m5-navigation.md), bench JSON in [perf/m5/](perf/m5/), [captures](perf/m5/captures.jpg); 259 tests, including the model spec check; see the log below |
| M6 Theming and custom models | Done (the working set is at the target with 300 per-game models; p99 and fullscreen hitches not met, as in M5; a Blender model on the real display is the owner's manual test) | 2026-09-30 | Part 1: [perf/m6-themes.md](perf/m6-themes.md), [perf/m6/](perf/m6/), [captures](perf/m6/captures.jpg). Part 2: [perf/m6-models.md](perf/m6-models.md), [perf/m6/part2/](perf/m6/part2/), [captures](perf/m6/part2/captures.jpg), [THEMING.md](THEMING.md); 427 tests; see the log below |
| M7 Settings UI | Done (a real pad on the panels and live scrapes are the owner's manual test; manual matching moved out) | 2026-10-01 | Part 1: [perf/m7-settings.md](perf/m7-settings.md), bench JSON in [perf/m7/](perf/m7/), [captures](perf/m7/captures.jpg); 477 tests. Part 2: [perf/m7-items.md](perf/m7-items.md), bench JSON in [perf/m7/part2/](perf/m7/part2/), [captures](perf/m7/part2/captures.jpg); 523 tests; see the log below |

### Log

- **2026-09-27: Scaffold.**
  - **What was added:**
    - Docs.
    - The `.slnx` solution: Launcher.Core, its xUnit v3 tests, and the Godot 4.7.2 project.
    - The `--capture` and `--bench` debug facilities.
    - `tools/verify.ps1` and the `godot.cmd` shim.
  - **Verification:**
    - `dotnet build`: 0 warnings.
    - 35 tests pass on the .NET 10 runtime.
    - The headless Godot build, import and smoke run all exit 0.
    - All four capture corners match their hex values exactly.
  - **First numbers.** These came from the editor binary with Debug assemblies, docked (1280×800 window, D3D12 Forward+, 59.94 Hz). They **aren't comparable with the targets**; M1 measures exports.
    - Process start to `interactive`: about 1.44 s warm (about 1.28 s of that before the first script runs).
    - An idle 300-frame bench: mean 16.63 ms, p99 18.07 ms, and 0 or 1 hitches per run.
    - 216 bytes allocated on the main thread, with no GCs.
- **2026-09-27: M1 prerequisites.**
  - **What was added:**
    - The export templates are installed.
    - `godot/export_presets.cfg` (Windows Desktop, ExportRelease).
    - `tools/bench-export.ps1`, which exports, runs one warm-up plus N measured runs, and prints medians.
    - `app_startup_ms` in the bench report, after the owner confirmed that the 1 s target covers our code only.
  - **Results:**
    - Exports are self-contained and bundle .NET 8.0.31.
    - On the scaffold scene at 1280×800, our code's start-up is a median **122–151 ms** in every renderer and driver combination.
    - Engine and .NET start-up before our code takes 962–1373 ms. Compatibility/OpenGL is fastest and Forward+/Vulkan slowest.
    - Frame pacing is about 16.5 ms mean and 18 ms p99 everywhere. The odd 26–30 ms frame shows up early in short runs.
    - Details are in [perf/m1-spike.md](perf/m1-spike.md).
- **2026-09-27: M1 grid spike, and M1 closed.**
  - **What was built** (on branch `spike/grid-perf`, not merged):
    - A 10,000-game synthetic library, with a distinct numbered 512² cover per game in 7 formats.
    - A virtualised 8-column grid over a 64-cell pool, with a front/spine/back box mesh, focus lift and spin, hold-to-repeat navigation and a scripted whole-library scroll.
    - Node and MultiMesh/`Texture2DArray` renderers.
    - Off-thread decoding with a byte-budgeted upload.
    - A per-format load test, and bench scripts.
  - **How it was measured:** 21 configurations × 3 runs (plus a warm-up each) on the ExportRelease build, and 6 load-test runs.
  - **Results:**
    - Every configuration holds vsync: mean 16.68 ms, p99 17.65–18.34 ms.
    - Covers are 100% textured while scrolling the whole library in 60 s.
    - Our code's start-up is 186–449 ms.
    - The main thread allocates 0.6 KB per 60 s scroll.
    - The chosen configuration (Mobile, MultiMesh, BC7) had 0 hitches in all 3 runs.
  - **Decided:** Mobile/D3D12; MultiMesh plus `Texture2DArray`; BC7 DDS derivatives; update-only uploads with 2 workers.
  - **New risk:** there's no BCn encoder in the export templates (M4).
  - **Not done** (moved to M2, M5 and M6; see M1 above):
    - handheld mode and true 4K. The desktop ran at 2560×1440 during the spike, although WMI reports 3840×2160, so the docked fullscreen runs are at 1440p. Check the display mode before any 4K run.
    - the other A3 experiments
- **2026-09-28: M2 core data layer, closed with a reduced scope** (Launcher.Core only, no Godot code).
  - **What was added:**
    - Tomlyn 2.10.1 and Microsoft.Data.Sqlite 10.0.12 in Launcher.Core.
    - `Config`: `ConfigLoader` layers `settings.toml`, `systems.toml` and `emulators.toml` over embedded defaults, with variables (cycles detected), templates with `{{`/`}}` escaping, and diagnostics that give file, line, column and key. The default systems are Game Boy, Game Boy Color, Game Boy Advance, NES, SNES, N64, GameCube, Master System, Mega Drive, Saturn, Dreamcast, PlayStation, PlayStation 2 and PSP, with 16 built-in emulator profiles.
    - ScreenScraper ids: all 14 were confirmed on ScreenScraper's own system pages and match ES-DE's table. ScreenScraper's API documentation has no system list, and `systemesListe.php` needs developer credentials, so that check moved to M4.
    - ROM folders: `{rom_root}/<id>` by default (then each alias), or one or more `rom_dirs` per system.
    - `Data`: both schemas as migration 0001, the migration runner, `userdata.db` backups (3 kept), refusal of a newer `userdata.db`, and recreation of a newer or broken `library.db`.
    - `Scanning`: `RomScanner` (extensions, recursion, excludes, several folders, `.m3u`/`.cue`/`.gdi` grouping with a playlist cache, NFC `rel_path` and `path_key`, collision warnings) and `TitleParser` (display title, sort key, and region, languages, revision, disc and tags as separate fields).
    - `Library`: `LibraryService`, with the boot, games, Favourites and Recently played queries, favourites, title and hidden overrides, alias re-keying, incremental rescans in one transaction, and `RebuildAsync` with an atomic swap.
    - `Platform`: `IPlatformPaths`, with Windows and portable-mode paths.
    - `tools/core-bench`, which times Core on self-contained .NET 8.0.31, ExportRelease.
  - **Verification:**
    - `dotnet build`: 0 warnings. 134 tests pass, covering config errors of every class, variable cycles, title cleaning, multi-file grouping, add/remove/rename/case-only rename, incremental rescans, migrations from an empty DB and every previous version, backups and the golden rebuild.
  - **Results** (Steam Deck; ExportRelease on .NET 8.0.31; 10,000 files, 12 systems, 6,213 games; warm file cache):
    - Full scan: 275–281 ms (target < 3 s).
    - Rescan with no changes: 65–71 ms (target < 0.5 s). With 1% changed: 55–57 ms.
    - `GetGamesAsync` for one 10,000-game system: 17.6–19.2 ms (target < 50 ms).
    - Config load: 2.1–2.6 ms warm, about 50 ms first in a process (JIT). Boot query: 0.03 ms.
    - net10.0 gives Core no gain (full scan 304 ms against 274 ms).
  - **Budgets in `ScanBenchmarkTests`** (Debug on .NET 10, as `dotnet test` runs them; medians over 3–4 invocations):

    | Benchmark | Budget | Measured (Debug) |
    |---|---|---|
    | Full scan, 10,000 files, 12 systems | 1,000 ms | 235–314 ms |
    | Rescan, nothing changed | 200 ms | 63–72 ms |
    | Rescan, 1% changed | 250 ms | 63–75 ms |
    | `GetGamesAsync`, 10,000 games | 45 ms | 20–28 ms |
    | Config load, warm | 10 ms | 0.6–2.8 ms |

  - **Moved** (see M2 above): the boot target with real config and DB, SQLite's native load inside Godot, the 20-system `boot` scenario and the Godot-side net10.0 comparison to M5; override indexing to M4 (art) and M6 (models).
- **2026-09-28: network-share scans** (after M2 closed).
  - **Measured:** a real 9,422-game library on a NAS over SMB. The M2 scanner took 14.4 s for a full scan and 13.6 s for an unchanged rescan (59 s on the first touch of the day), almost all of it listing folders.
  - **Changed:**
    - `RomScanner` lists with a 256 KB buffer.
    - `LibraryService` scans 8 systems at once.
    - New `[scanning] exclude` setting, applied to every system; default `["images", "manuals", "videos", "gamelist.xml"]`.
  - **Results:** on the NAS, an unchanged rescan takes 1.4 s and a full scan 1.9 s. Local scans are unchanged or slightly faster (full scan 222–234 ms). 142 tests pass. There are no network targets yet; details are in [perf/m2-core.md](perf/m2-core.md#network-share-added-2026-09-28).
- **2026-09-28: M3 launching, closed.** The real-emulator and focus check is the owner's manual test ([manual-tests.md](manual-tests.md#m3-launching-a-real-emulator-and-focus)).
  - **What was added:**
    - `Config`: placeholders `{emulator}`, `{rom_stem}` (was `{rom_name}`) and `{core}`; a `core` key on emulator profiles, used by the 13 built-in RetroArch profiles; a load-time check that each used emulator's executable and core exist, as warnings naming the affected systems.
    - `Launching`: `LaunchPlanner` (the emulator from this launch's choice, the game's override or the system; single-pass expansion) and `LaunchService` (file checks, the process, events `Starting`/`Running`/`Exited`/`Failed`, quick-exit detection, one game at a time, cancellation ends the game).
    - `Platform`: `IProcessRunner` and `IWindowFocus`, with Windows implementations (a job object from the first instruction via `PROC_THREAD_ATTRIBUTE_JOB_LIST`; `WindowsCommandLine` quoting by the C runtime's rules; foreground hand-over and an escalating reclaim) and a Linux stub (`PortableProcessRunner`, `NullWindowFocus`).
    - `Library`: per-game emulator overrides, lookup by `GameKey`, and `IPlayHistory` (sessions, play count, play time, last played; sessions a crash left open are closed on open).
    - App: `LaunchController` (render loop off, low-processor mode at 10 Hz, tree paused, audio muted, input swallowed; minimise once the emulator has the foreground; restore and reclaim focus on exit), and the debug arguments `--launch`, `--user-dir` and `--quit-after-launch`.
    - `tests/FakeEmulator` (logs its arguments, working folder and command line; sleeps; exits with a chosen code; starts a copy of itself or another program and exits, as a stub launcher does) and `tools/launch-smoke.ps1`, which `verify.ps1` now runs.
  - **Verification:**
    - `dotnet build`: 0 warnings. 217 tests pass; the launch tests passed on three consecutive runs.
    - The launch tests run the fake emulator through the real runner, installed under `Emulators ü 日本\Fake Emu\Fake Emu ü.exe`, with a ROM named `Sonic & Knuckles {x} (100%) ü 日本 😀.md` in `Sub Folder é`. They check every placeholder, the empty argument, embedded quotes, trailing backslashes, tabs, `{{`/`}}`, `& ^ | < > ! % $`, and the working folder, through both runners. Quoting is also checked against `CommandLineToArgvW`.
    - They also cover the lifecycle events, exit codes and durations; quick non-zero exits; missing executable, ROM and core; a file that isn't a program; stub launchers (a job still running after the stub exits); per-game and per-launch emulator choice; an unknown override; cancellation; play count, time and last played over two sessions; and crash-orphaned sessions.
    - `tools/launch-smoke.ps1` passes headless in the editor run (.NET 10.0.12) and in the export (.NET 8.0.31). So Microsoft.Data.Sqlite's native library loads in both; M2 had left that for M5.
  - **Performance** ([perf/m3-launching.md](perf/m3-launching.md)): the committed build's start-up is 135.5 ms against 129.1 ms for M2 in the same session (overlapping ranges), with the same frames and 216 B of main-thread allocation. Two problems were found and fixed on the way:
    - building the controller at boot cost 10–24 ms, so it's built on first use
    - an always-on `_Input` allocated about 1.9 KB per frame from the Deck's joypad events, so input processing is on only while input is being swallowed
  - **Moved to M5:** evicting textures during a game, the input router honouring `IsInputBlocked`, and building the controller in the warm-up.
- **2026-09-28: M5 3D navigation, closed.**
  - **What was added:**
    - Core: `GameRow` carries the cover's aspect, size and time, and `GameDetails` the `metadata` row. `UserMedia` indexes the user's art in `ConfigDir/media/<system>/<kind>/` (migration 0002: `media.size_bytes`, `mtime_ms`); `ImageHeaders` reads PNG, JPEG and WebP sizes from headers; `TextureDerivatives` names derivatives. The template ids are `dvd_case`, `jewel_case`, `cartridge_box`, `clamshell` and `umd_case` (Saturn now uses the jewel case, PSP the UMD case). Bench report format 2 (scenario, options, library, scroll, textures, memory); debug arguments `--bench-scenario`, `--bench-system`, `--bench-scroll-seconds`, `--no-textures`, `--render-scale`, `--upscaler`, `--upload-cap`, `--start-system`, `--start-index` and `--nav-script`.
    - Models: `BoxTemplateGenerator`, a `[Tool]` Godot script that builds the five templates and a generic system model from real case sizes and exports them with `GLTFDocument` (deterministic; about 220 triangles each). `BuiltInModelTests` checks them against A7.
    - App: off-thread boot (`AppServices`, `MainThreadQueue`); `ItemGrid` (MultiMesh per template, shared cover array, title atlas, focus animation, cover fades); `TextureStreamer`; the item shader (art crop and fade, generated spine and back, titles, opaque fade into the background); `Navigator` (screens, transitions, focus memory, favourites, rescans, launching); `NavInput`; `InfoOverlay`; `ScrollBench`. `project.godot` uses the Mobile renderer; the export bakes shaders; Godot's staging buffer is capped at 16 MB.
    - Tools: `tools/synthetic-library` (20 systems, 14,215 games, covers and derivatives hardlinked from the M1 spike library); `tools/bench-summary.py`; `bench-export.ps1` takes `-AppArgs` and `-TimeoutSeconds`, exports with a rendering device, and its `-Fullscreen` option works again (it had been passing one mangled argument).
  - **Verification:** `dotnet build`: 0 warnings. 259 tests pass (217 at M3). `verify.ps1` passes, and the launch smoke test passes on the export. Captures of both grids, every template, the focus state, spine and back, the transition and the real library were reviewed. `--nav-script` checked focus memory (re-entering a system restores its last game), letter jumps, page, first and last, back, and adding a favourite that then shows in Favourites.
  - **Results** (export, Deck docked; [perf/m5-navigation.md](perf/m5-navigation.md)):
    - Start-up of our code: 340 ms (synthetic, 14,215 games), 338 ms (real, 9,422 games); 359 ms for the committed build; 689–818 ms fullscreen at 2560×1440. Cold, with the shader baker: 1.2–1.4 s (2.3–2.4 s without).
    - 60 s scroll of 10,000 games, committed build: mean 16.68 ms, 100% textured (visible grid in 13–20 ms), 0 hitches and 0 frames over 2× in both runs, main thread 64 B, working set 357 MB windowed (447 MB fullscreen). p99 about 21 ms, the same as the no-texture control.
  - **Found and fixed:** a full Latin-1 glyph warm-up (150–220 ms frame, +130 MB; now ASCII, a third a frame); title atlases at 3× their pixel size in GPU memory (now smaller); the first upload and pipeline compile after interactive (now before it); 2.2 KB allocated per cover on the workers (now one string); `ConcurrentStack` allocating on the main thread; a binding window with one row of lookahead (77% textured); the fullscreen working set (staging buffer).
  - **Moved:** see M5 above.
- **2026-09-28: M4 scraping and the media pipeline, closed.** The live scrape needs the owner's credentials ([manual-tests.md](manual-tests.md#m4-a-live-scrape)).
  - **Research first** (the current docs of ScreenScraper's Web API v2, SteamGridDB's API v2 and IGDB's API v4 with Twitch's client-credentials flow). What contradicted the architecture doc, and what was decided with the owner:
    - The BC7 encoder wasn't chosen yet (SPIKE_RESULTS.md R1). The owner approved BCnEncoder.Net; measured at about 10 s a cover, it was replaced by our own (below).
    - ScreenScraper's rules want a hash with every lookup, not a file name alone. The owner chose name and size always, plus hashes for files up to 64 MB.
    - ScreenScraper echoes its credentials in `header.commandRequested` as well as in media URLs, and has per-minute and "not found" quotas besides threads and the daily quota.
    - Only ScreenScraper has back, spine and box texture. SteamGridDB has community capsule art and no metadata. IGDB has no logos, three different ratings, and tokens that can't be refreshed (25 per application).
    - The portable layout would have mixed scraped media with the user's art (`media/` in one folder), so scraped files moved under `scraped/`.
  - **What was added:**
    - `Scraping`: `IScraper` with capability maps; `ScreenScraperScraper` (lookup by name, size, `romtype` and hashes; title search with a name check; the account's limits from `ssuser`; quota codes 430 and 431 rest it until French midnight), `IgdbScraper` (Apicalypse search limited to the system's `igdb_platforms`; `TwitchAppToken` cached on disk and renewed a day before expiry or on a 401), `SteamGridDbScraper` (autocomplete search; case-shaped grids first; heroes and logos); `ProviderGate` and `ScraperHttp` (concurrency, per-second and per-minute limits, pauses, exponential backoff with Retry-After, gates shut on quota or refused credentials); `ScrapeMerge` (the provider, then fallbacks, for what's missing); `ScrapeService` (operations, a persistent queue in userdata.db, events, pause and resume, cancel, clear); `ScrapedResponses` and `ScrapedRestore` (saved, redacted responses re-parsed offline when a scan adds a game); `ProviderAccounts` (secrets.toml and `ODYSSEY_*`); `TitleMatcher`.
    - `Media`: `MediaStore` (atomic, deterministic scraped media); `Bc7Encoder` (modes 6 and 1) and `Bc7DdsWriter`; `DerivativeBaker` and `DerivativeService` (below-normal thread; bake missing; prune stale). `Platform/Windows/WicImageDecoder`. `Scanning/RomHasher`. `Diagnostics/Redactor` and `ILog`.
    - Schema: library migration 0003 (`metadata.title`, `scrape_state`), userdata migration 0002 (metadata override columns, `scrape_batches`, `scrape_jobs`). `GameDetails` shows the user's overrides over scraped values and carries the scrape status; `SetMetadataOverrideAsync`.
    - Config: `[scraping] provider`, `fallback`, `media` and `hash_limit_mb` (replacing `cover_sources`); `igdb_platforms` for every built-in system.
    - App: missing derivatives are baked after the background scans (not in benches).
    - `tools/scrape-cli` (`odyssey-scrape`): `providers`, `game`, `system`, `missing`, `clear`, `show`, `resume`, `bake`, `scan`, `ss-systems`.
  - **Verification:** `dotnet build`: 0 warnings. 321 tests pass (259 at M5) on three consecutive runs, including 24 service tests over a fake HTTP handler and recorded fixtures (matching by name, size and hash; title search; fallback order and capability maps; missing credentials; IGDB token caching, refusal and expiry; 429 with Retry-After; 5xx backoff; used-up quotas; the account's thread limit; resume after a stop; cancel; the "missing" selection; overrides surviving re-scrapes; stored and manual matches; offline rebuild; clearing; no credential anywhere), and a check that 3,000 BC7 blocks decode (by BCnEncoder.Net) with exactly the error our encoder predicted. A capture shows a real cover baked by the console tool on a box in the grid ([perf/m4/real-cover-bc7.png](perf/m4/real-cover-bc7.png)).
  - **Results** ([perf/m4-scraping.md](perf/m4-scraping.md)): BC7 encoding takes about 0.44 s a real cover with mips (BCnEncoder.Net about 10 s) at 40.0 dB on real Mega Drive box art (BCnEncoder.Net 36.9–40.1 dB on the same covers). An A/B against the M5 build in one session: scroll hitches 1/2/1 against 3/0/0, none over 2× in either, p99 20.2–21.2 against 20.2–21.4 ms, 64 B of main-thread allocation in both, start-up of our code 354 against 375 ms.
  - **Not done:** the live 50-game scrape (the owner's credentials; the `systemesListe.php` check was done 2026-10-03); ReadyToRun (the owner's approval); scrolling while the baker runs isn't benched.
- **2026-09-29: M6 part 1, the theme system and media binding.**
  - **What was added:**
    - Core `Theming`: `ThemeLoader` (manifests from text and a source name, validated like config, with file:line:column:key diagnostics; bad look blocks fall back to the built-in theme's, bad templates are left out, bad chains fall back to the default chain), `ThemeCatalog` (user themes in `ConfigDir/themes/<id>/`, the active one, the built-in `memory-card` as the last resort), `ModelResolver` (each system's model candidates for its games and its card in A7's precedence, with its look and colour), `SlotChain` and `MediaSlots` (the slots, their standard texture sizes, and allocation-free fallback resolution). `Models/GlbInfo` (a `.glb`'s material names from its JSON chunk). `Config/TomlValidator` (typed reads with diagnostics, shared with `ConfigLoader`'s suggestions).
    - Core elsewhere: `game_model` is now the user's choice of a template id (the built-in systems.toml no longer sets it; `ConfigLoader.GameModels` is gone); the scanner indexes per-game models (`ConfigDir/models/games/`, media kind `model`); `ILibrary.GetGameMediaAsync`; `LibraryService.MediaChanged` (rescans, scrapes, clears, rebuilds, bakes); derivatives for every image kind; debug arguments `--theme` and `--no-overlay`, and nav-script steps `theme` and `rescan`; bench report options `theme` and `media_slots`.
    - The built-in theme, `godot/themes/memory-card/`: the M5 boxes and generic card (now exported as the `.glb` files themselves), a colour, template and look (background and three lights) for each of the 14 built-in systems. The test theme, `tests/themes/slot-showcase/`: a tall case with cover, screenshot and spine slots (its screenshot material carries an authored test card), a tile card, two lights and a PS2 look; both generated by `BoxTemplateGenerator`.
    - App: `ModelLoader`, `ModelConverter` and `ItemTemplate` (every `.glb` parsed and converted on a worker, fitted to the spec, rejected without a cover), replacing `TemplateLibrary`; `ThemePlan` and `ThemeRuntime`; `LookStage` (cross-fades between looks); `SlotLayout`; `TextureStreamer` with slot channels (512² for covers, 256² from each derivative's mip 1 for every other slot, arrays built on a worker); `ItemGrid` with materials shared between templates with the same authored textures, a slot-state texture, fallback chains, `RefreshItem` and templates added at run time (per-game models); the item shader's media slots, authored textures and `generated` faces; the navigator's theme switching (T or Menu), per-system looks, media rebinding and per-game models.
    - Tools: `synthetic-library` takes `--others` and `--slots`.
  - **Verification:** `dotnet build`: 0 warnings. 368 tests pass (321 at M4), including 47 new ones for manifests, catalogues, precedence, fallback chains, slot media queries, model indexing and `MediaChanged`. `verify.ps1` passes. Captures of both themes, a run-time switch, art added and removed while running (rebound in place), a per-game model, and both themes' corners were reviewed ([perf/m6/captures.jpg](perf/m6/captures.jpg)).
  - **Results** ([perf/m6-themes.md](perf/m6-themes.md); 3,000 games, export, Deck docked): start-up of our code 347 ms (M4: 332 ms on the same library); scroll with three slots streaming: 0 hitches and 0 frames over 2× in every final run (the no-texture control had up to 3 and 2), 100% textured, visible grid in 14–20 ms, 64 B of main-thread allocation; fullscreen 2560×1440: 1 hitch in 2 runs, 0 over 2×; working set 420–428 MB (peak 450), fullscreen 425 MB; pool 32.8 MB (three slots).
  - **Found and fixed:** bursts of whole-row uploads made single uploads take 14–31 ms (so M4's frames over 2×): the cap is now 4 cover-sized uploads a frame, and the maximum is 1.1–1.7 ms; the theme on the boot's critical path (+105 ms at first): resolved alongside the library, with the look and games grid built in `_Ready` and the models parsed in parallel on workers (Godot's threaded loader took about 25 ms a model, one after another); a headless run crashing when `--quit-after` shut the engine while the boot task read `res://` (headless runs resolve no theme).
  - **Not done:** part 2 (above); the working set is 70 MB above M4's for reasons not yet found (neither the slot arrays nor the materials); corner colours are within 2/255 on Mobile, exact on Forward+.
- **2026-09-30: M6 part 2, user models and theme authoring. M6 closed.**
  - **What was added:**
    - Core `Models`:
      - `GlbFile`: a GLB's JSON (mutable) and binary chunk, read and written.
      - `ModelInspector`: checks every index, range, node and image without Godot; counts triangles, materials, textures, joints and morph targets against `ModelBudget` for its `ModelKind`; finds the slots and the clips (`ModelClips`).
      - `ModelProcessor`: scales textures over the budget's side down (WIC, then `Media/PngEncoder`) and repacks the file.
      - `ModelCache`: `CacheDir/models/`, with its reports, a rejection remembered too.
      - `ModelLog`: `DataDir/logs/models.log`.
      - `ObjConverter`, through `GltfBuilder`: OBJ, MTL and textures from a zip or a folder, to GLB.
      - `ModelImportService`: import, remove, and the current model's report.
    - Core elsewhere: `LibraryService.RefreshUserMediaAsync`; clearing a game removes its model and its cached copy; a game template needs no `cover`.
    - App:
      - `ModelLoader` loads user models through the cache (a rejection is logged, and the next model in line is used), and adopts finished loads within 2 ms a frame.
      - `ModelConverter` decodes base colour images itself with mipmaps, multiplies in vertex colours, and keeps a model's node tree when it has clips (clips renamed to their canonical names, with a generated `_rest` clip). It disposes every Godot wrapper it reads.
      - `ItemGrid` draws per-game models on per-cell `MeshInstance3D`s, and clips on pooled copies of a model's node tree (every cell for an idle clip; the focused cell for focused and launch clips, swapping back to the MultiMesh once it's at rest). The procedural sway and spin only run without a clip, and the launch waits for the launch clip (at most 2 s).
      - The item shader's `node_custom` instance uniform carries the per-cell data for nodes.
      - The scroll bench waits for a list's per-game models.
    - Content:
      - the sample theme `samples/themes/retro-tv/`: a CRT television game template (screenshot screen, logo or printed title on its stand, focused and launch clips) and a console system model (idle and focused clips), generated by `RetroTvBuilder`
      - `docs/THEMING.md`
    - Tools:
      - `odyssey-scrape import-model`, `remove-model`, `inspect-model` and `models-log`
      - `synthetic-library --models=<n>`
  - **Verification:** `dotnet build`: 0 warnings. 427 tests pass (368 at part 1). The 59 new ones cover the model fixtures (in budget, over, more than 2× over), 15 kinds of broken file, clip names, every committed model in budget, texture scaling, OBJ conversion, the cache (processed once, again when the file changes, rejections remembered), the log, import, removal, and clearing. `verify.ps1` passes. The console commands were run end to end in a scratch user folder: a `.glb` and an OBJ zip imported, a bad file rejected and logged, a model removed, a game cleared. Captures of the sample theme (both grids, a clip, the launch clip) and of per-game models beside batched items were reviewed ([perf/m6/part2/captures.jpg](perf/m6/part2/captures.jpg)).
  - **Results** ([perf/m6-models.md](perf/m6-models.md); export, Deck docked, 300 per-game models in 3,000 games):
    - scroll: 0–1 hitches (the control's 0–2), 0 frames over 2×, 100% textured, the visible grid in 14–18 ms, 64 B on the main thread, GPU 1.28–1.36 ms (part 1: 1.67–1.69)
    - working set 512–515 MB (part 1: 548–558)
    - start-up of our code 376 ms (part 1: 339 ms, the difference first-call JIT)
    - the sample theme: 0–1 hitches and 64 B
  - **Found and fixed:**
    - Godot wrappers holding each model's parsed state and meshes until finalised (20–40 MB)
    - the sample theme's node trees first copied mid-scroll (4.8 KB on the main thread)
    - Godot converting a `Color` given to an instance uniform from sRGB to linear, which scrambled cells and colours
    - `GltfState.GetSceneNode` returning freed nodes at run time
    - the runtime importer's textures having no mipmaps
    - the runtime glTF generator handing back meshes already on the GPU, so models with clips were first drawn without their slots
  - **Not done:** see M6 above (streaming per-game models, the rest of material remapping, the LRU cache and full-resolution art, ReadyToRun, the owner's manual test).
- **2026-09-30: M7 part 1, the shared UI components and the main settings screen.**
  - **What was added:**
    - Core `Config`: `TomlEditor` (edits over Tomlyn's syntax tree: values replaced keeping their comments, keys added at the end of their table or in a new one, keys removed, dotted keys, comment-only files, line endings); `ConfigWriter` (only changed values, a default removed unless its line has a comment, validated by loading the edited files, written atomically, a byte order mark kept; credentials to `secrets.toml` only); `ConfigInput`.
    - Core `Files`: `DirectoryListing`, `FileFilter`, `PathInput`, `LetterJump`, `NaturalComparer`, `PickerHistory`.
    - Core `Platform`: `IFileLocations`, with `WindowsFileLocations` (drives, mapped shares, volume labels, known folders) and the `PortableFileLocations` stub.
    - Core `Scraping`: `IScraper.TestConnectionAsync` for the three providers, `ScrapeService.TestConnectionAsync` and `CountMissingAsync`; `ProviderAccounts.SourceOf` (the file or an `ODYSSEY_*` variable) and `EnvironmentVariable`.
    - Debug arguments `--open` and `--open-path`, and nav-script steps `menu`, `x`, `click`, `scroll` and `type` (the last three send real mouse and keyboard events).
    - App `Ui`: `UiLayer`, `UiPanel`, `ListPanel`, `SettingRow`, `ChoicePanel`, `ConfirmDialog`, `OnScreenKeyboard` and `TextField`, `FilePicker` and `VirtualList`, `BackgroundJobs` and `JobsHud`, `UiStyle`, `UiContext`.
    - App `Settings`: `SettingsController`, `LibraryJobs`, and the pages (`SettingsHome`, `RomFoldersPage`, `SystemPage`, `EmulatorsPage`, `ScrapingPage`, `FallbackPage`, `ProviderPage`).
    - App elsewhere: `NavInput` with a keyboard and a gamepad action per command, plus Menu and X (Godot's `ui_*` navigation emptied); the navigator opens the settings, ignores input while they're open, and rescans through `LibraryJobs`; `AppServices.ApplyConfig` and `LaunchController.ApplyConfig`.
  - **Verification:** `dotnet build`: 0 warnings. 477 tests pass (427 at M6 part 2). The 50 new ones cover the editor's round trips (comments, blank lines, line endings, dotted keys, inline tables, arrays of tables, quoting, comment-only files), only changed values, refusals (an unknown emulator, a syntax error), secrets written to `secrets.toml` alone and never quoted, a byte order mark, listing, filtering and sorting, 3,000 files, hidden entries, the reasons a folder can't be listed, typed paths, going up, letter jumps, the history, the drive listing, the connection tests over recorded fixtures (plus one for `ssinfraInfos.php`, written from ScreenScraper's API documentation as it hasn't been recorded), and the missing count. `verify.ps1` passes. Every screen and component was captured and reviewed ([perf/m7/captures.jpg](perf/m7/captures.jpg)), including the pickers on a folder of 5,000 images and 300 folders, the NAS share, and shares that are slow or unreachable; saves made in the app were checked in the files.
  - **Results** ([perf/m7-settings.md](perf/m7-settings.md); export, Deck docked, 3,000 games, the same session as M6 part 2's commit): scroll 0 hitches and 0 frames over 2× in every run, 100% textured, 64 B on the main thread, working set 425–426 MB, all the same as before; start-up of our code 446 ms median (before: 517 ms).
  - **Found and fixed:** a page showing through the page over it; the grid's overlay and the progress cards beside the settings panel; a new `secrets.toml` with its table above its header comment (Tomlyn keeps a comment-only file's text as the document's trailing trivia); a doubled blank line before a new table; an empty picker after B while its first folder was still opening; a progress card running off the screen.
  - **Not done:** part 2 (above); the owner's manual test; the app doesn't resume a scrape batch left unfinished when it closed (`odyssey-scrape resume` does).
- **2026-10-01: M7 part 2, the item options panels. M7 closed.**
  - **What was added:**
    - Core `Library`: `GetGameMediaInfoAsync` (a game's media with their sources), `GetMetadataEditAsync` (scraped values and the user's overrides apart), `MetadataInput` (titles and fields, UK dates, ratings).
    - Core `Media`: `UserArtService` (the user's own image per slot: copied to the game's ROM name, baked, indexed; removed with the scraped image restored).
    - Core `Models`: `ModelImportService` imports, removes and reports a system's own card and game template.
    - Core `Scraping`: `ScrapeService.CountSystemAsync`; `ScrapedRestore.RestoreMedia`.
    - App `Options`: `ItemOptions`, `GameOptionsPanel`, `GameMetadataPanel`, `GameMediaPanel`; `Ui/Thumbnails` (shared with the image picker).
    - App elsewhere: `SystemPage` gains models and "scrape this system" (and opens with X on a system); `LibraryJobs` scrapes a system or a game, clears a game and raises `GamesUpdated`; the navigator opens the options on X (O or the menu key on a keyboard), renames games in place after scrapes and edits, and reloads the theme after a system's model changes; `RefreshItem` sets the cell's title; `ThemeRuntime` says which model a system uses.
  - **Verification:** `dotnet build`: 0 warnings. 523 tests pass (477 at part 1). The 46 new ones cover the user's images (set, replaced in another format, refused files, removal restoring the scraped image or leaving none, a shared file left alone, a rebuild keeping them), typed metadata (dates in every accepted form and rejected ones, ratings, lengths, single lines), the editing view (scraped and user values apart, sources), a system's card and template (imported where the theme resolver looks, held to their budgets, removed), and the system scrape count. `verify.ps1` passes. Every panel and dialog was captured and reviewed, with changes checked in the grid in the same run ([perf/m7-items.md](perf/m7-items.md#captures)).
  - **Results** ([perf/m7-items.md](perf/m7-items.md); export, Deck docked, 3,000 games, the same session as part 1's commit): scroll 0–1 hitches and 0 frames over 2× (before: 0–2 and 0), 100% textured, 64 B on the main thread, GPU 1.35–1.37 ms, working set 425–426 MB: all as before; start-up of our code 411 ms median (before: 375 ms, overlapping ranges).
  - **Found and fixed:** switching away from a theme whose models have clips leaked their node trees (since M6 part 2); "scrape this game" without credentials named one provider only.
  - **Not done:** see M7 above (manual matching, a video slot, scraping labels, resuming batches at start-up, the owner's manual test).
- **2026-10-01: the ES-DE catalogue** (outside the milestones: the owner asked for ES-DE's systems and emulators).
  - **What was added:**
    - 150 systems and about 450 emulator profiles in `Defaults/systems.toml` and `Defaults/emulators.toml`, converted from ES-DE 3.5.0's `es_systems.xml` and `es_find_rules.xml` (ARCHITECTURE.md A5, "The ES-DE catalogue"); regional twins are aliases; the original 14 systems keep their defaults and gain ES-DE's other emulators as alternatives; the built-in theme gives each a colour and a box.
    - `run_file` profiles and `LaunchPlan.RunFile`: shortcuts, scripts and programs as games, with no cmd.exe command line (`WindowsProcessRunner`: programs directly, batch files as `cmd.exe /d /s /c ""path""`, shortcuts through `ShellExecuteEx` into the game's job).
    - `[display] hide_empty_systems` (default on): systems with no games have no card; install warnings cover only the default emulators of systems with games (`ConfigSources.CheckInstallsFor`, run after `interactive`); the Emulators page lists only those systems' profiles.
    - `TomlFast`, which reads the built-in defaults and theme (Tomlyn took about 50 ms for the catalogue).
  - **Verification:** `dotnet build`: 0 warnings. 567 tests pass (550 before the new ones: `TomlFastTests` compares its tree with Tomlyn's for every shipped file; `RunFileTests` runs a batch file named `Sonic & copy NUL pwned.txt & Knuckles (Zone) ^ 100 ! 'n'.bat`, a program and a `.lnk`; the catalogue's rules, the hide setting and the install-check filter). `verify.ps1` passes. Captures of the grid (only systems with games) and the settings were reviewed. Boot: [perf/catalogue.md](perf/catalogue.md) (our start-up 471 → 387 ms median, within the noise; config warm 2.1 → 9–11 ms).
  - **Found and fixed:** a plain `CreateProcess` of `Sonic & Knuckles.bat` runs `Knuckles.bat` as a second command (the tests showed it), so batch files go through an explicit `cmd.exe /d /s /c`; `tools/synthetic-library` generated games for every built-in system, and now only for its 20.
  - **Not done:** `igdb_platforms` for the catalogue systems are from memory, unverified (`screenscraper_id` was checked on 2026-10-03); ES-DE's `%INJECT%` files aren't supported, so psvita (Vita3K), PS3 and PS4 game serials, 3dSen and Linux Loader are left out; a real emulator for each catalogue system, and a real `.lnk` and `.bat` launch with the focus handover, are the owner's manual test ([manual-tests.md](manual-tests.md)).
- **2026-10-01: Windows and Steam games** (outside the milestones: the owner asked for them).
  - **What was added:**
    - The `windows` and `steam` systems (ES-DE's ids and folders): shortcuts, batch files and internet shortcuts, run by `run-file`, with a colour and DVD cases in the built-in theme (ARCHITECTURE.md A5, "Windows and Steam games").
    - Core `Launching`: `SteamShortcut` reads a Steam game's app id from its `.url`; `SteamGame` follows the game through the Steam client's state (running, ended, never started, updating); `LaunchService` hands Steam shortcuts to Steam (`LaunchPlan.Detached`), fails before starting when Steam isn't installed, and reports a game Steam never started as `LaunchFailure.NotStarted`, not a play (`ProcessOutcome.NotStarted`).
    - Core `Platform`: `ISteamClient` and `WindowsSteamClient` (the registry Steam writes); both runners open a `Detached` plan without following it.
  - **Verification:** `dotnet build`: 0 warnings. 610 tests pass (567 before). The 43 new ones cover reading app ids (the shortcut Steam writes, each URL form, non-Steam game ids, other stores, other sections, oversized files), `SteamGame` on a clock its polls move (followed to its end, a one-poll gap, the app's flag alone, a stale flag, a game already running, no client, the timeout and its three messages, updates not counted, terminate, dispose, an unreadable client), the launch service end to end with the library (handed to Steam and counted as a play, a Steam shortcut in `windows`, never started and not a play, Steam not installed, other shortcuts unchanged, no client), the built-in systems and their scan, and the Windows runner opening a detached shortcut without following it. `verify.ps1` passes. A headless `--launch=windows/Hello & World.bat` ran the script through the app; captures of the systems grid (Steam and Windows cards) and Steam's games grid were reviewed. The registry keys were checked on the owner's PC (read only), where an app's `Running` flag was set with nothing running.
  - **Not done:** a real Steam launch with the focus handover is the owner's manual test ([manual-tests.md](manual-tests.md#windows-and-steam-games)); scraping doesn't use the app id (the Steam store provider, added later the same day, finds games by title instead); non-Steam games added to Steam, and other stores' shortcuts (Epic), aren't followed; no Steam client on Linux yet.
- **2026-10-01: scraped media kinds** (outside the milestones: the owner asked for them).
  - **What was added:**
    - ScreenScraper's support texture (`support-texture`) fills the `label` slot, and `video` is a new media kind (`video-normalized` first, then `video`), saved as an MP4 by `MediaStore` (`VideoFormats`) with no size, derivative or slot; the back, spine, screenshot, wheel (logo) and fan art (hero) were already mapped. Box textures aren't scraped any more: an old `box_texture` in `[scraping] media` is a warning and left out.
    - `[scraping] media` defaults to cover, back, spine, screenshot and logo, so fan art, support textures and videos are off.
    - App `Settings`: `ScrapeMediaPage` (Scraping, then Media to scrape) turns each kind on or off, saying which providers have it.
    - `ScraperHttp` times each attempt itself, after the gate: 30 s, 5 minutes for a video.
  - **Verification:** `dotnet build`: 0 warnings. 613 tests pass (610 before; the 3 new ones cover every scrapable kind from ScreenScraper's preferred types with no box texture, the video surviving a rebuild and going with a clear; `box_texture` left out with a warning; `MediaStore` refusing a non-MP4 video and a non-image cover). The ScreenScraper fixture gained the new types. Captures of the Media page and the Scraping page, before and after turning video on, were reviewed.
  - **Found and fixed:** a settings page rebuilt after a save (the Fallbacks page too) scrolled to its top, away from the focused row.
  - **Not done:** ScreenScraper's names for the new types are from its documentation, not a recorded response: the owner's manual test checks them live ([manual-tests.md](manual-tests.md#scraped-media-kinds)); nothing plays a video yet, and there's no video in the game's Images panel.
- **2026-10-01: the Steam store provider** (outside the milestones: the owner asked for Steam's official art, found without a game's app id).
  - **What was added:**
    - Core `Scraping`: `SteamStoreScraper` (`"steam"`), on Steam's keyless Web API. A lookup is one `IStoreQueryService/SearchSuggestions` request (games only, with each hit's assets, basic info, release, reviews and screenshots), matched by `TitleMatcher`; a stored match is fetched by app id with `IStoreBrowseService/GetItems`. It supplies the cover (the 2x library capsule), hero, logo (`logo.png`, checked with a HEAD request first, as the API doesn't list it) and first screenshot, and the title, description, release date, developer, publisher and rating. Two gates: 2 requests in flight and 1 a second for the API, 4 in flight for images. It's in the rebuild (`ScrapedResponses`, `ScrapedRestore`) and the connection test.
    - Config: `"steam"` is a provider id, opt-in (the default order is unchanged); the system key `steam_store`, true on `windows` and `steam` only.
    - App `Settings`: the Steam store on the Scraping page (the "Credentials" section is now "Providers") and the Media page; its own page says no credentials are needed and keeps Test connection.
    - The research behind it is in ARCHITECTURE.md's decisions log: SteamGridDB's API has no official art, and the Steam-client routes need app ids or a key.
  - **Verification:** `dotnet build`: 0 warnings. 624 tests pass (615 before). The 9 new ones run on recorded, keyless responses: parsing hashed and bare file names, the 2x art first, the date, rating and decoded description, and the logo only once found; the closest name chosen over a Steam search's look-alikes; the language; `steam_store` per system and a non-boolean one refused; a Portal 2 shortcut naming another app id still scraped as Portal 2 by title, then rebuilt with the network off; a Mega Drive game never sent to Steam; a game with no Steam logo taking SteamGridDB's; a stored match re-fetched by id, then searched for again once Steam no longer knows it; the connection test. `tools/verify.ps1` passed. `odyssey-scrape providers` lists the Steam store as ready with no credentials. Captures of the Scraping page (the Steam store chosen as the default provider) and the Steam store's page were reviewed.
  - **Not done:** a live scrape is the owner's manual test ([manual-tests.md](manual-tests.md#steam-store-scraping)); a game Steam no longer sells isn't found by the search (a full app list needs a Steam Web API key, and Steam's own client protocol needs SteamKit2); titles that differ from Steam's beyond a subtitle ("Rainbow Six Siege" against "Tom Clancy's Rainbow Six Siege") wait for manual matching (`SearchAsync` is ready); no genre or players from Steam.
- **2026-10-01: manual matching** (moved out of M7; the owner asked for it on "scrape this game").
  - **What was added:**
    - Core `Scraping`: `ScrapeService.SearchMatchesAsync` (every provider searched at once for the game's title, the user's or the file name's, or a typed name; each one's results closest name first, with its current match, or why it couldn't be searched) and `ScrapeGameWithMatchAsync` (the chosen result saved as a manual match, then the game scraped in a batch of kind `manual`); a game's manual matches are asked first, the latest choice first, in every scrape, and merged first by the rebuild's restore (`ScrapeStore.ManualOrders`); `ScrapeStore.SaveReplacing` (what a re-matched provider had brought in and doesn't bring again goes: its old match, log, scraped media and their files, and metadata only it supplied); a game's manual match is asked even when `[scraping]` doesn't name its provider.
    - App `Options`: `GameMatchPanel`, opened by "scrape this game": a section per provider with its results, its current match marked; A on a result scrapes with it; X searches for another name. `LibraryJobs.SearchMatchesAsync`, and `ScrapeGame` with the chosen result.
    - `--open=match`: the panel over made-up results, for captures.
  - **Verification:** `dotnet build`: 0 warnings. 633 tests pass (624 before). The 9 new ones (`ManualMatchTests`, on the recorded fixtures) cover the search (every provider at once, ranked by name, HTML decoded, the Steam store saying why it can't search a Mega Drive game, nothing fetched or written), the default and typed search names and the current match, a provider without credentials and one whose search fails while the others answer, the chosen result fetched by id and surviving a rebuild, the chosen game's data first with the others filling in (and the same after a rebuild, and the latest choice leading), a corrected match leaving none of the wrong game's art, a failing provider keeping what it had, a provider outside the order used when chosen, and bad choices refused. Captures of the panel (`--open=match`, and A on a result sending it to the scrape) were reviewed. Not performance-sensitive: nothing runs per frame, and the panel only exists while it's open.
  - **Not done:** a live search and scrape with your credentials is the owner's manual test ([manual-tests.md](manual-tests.md#manual-matching)); batch scrapes ("scrape this system", "scrape all missing") still match automatically; the search shows names and years only, not cover thumbnails.
- **2026-10-02: status indicators** (outside the milestones: the owner asked for them).
  - **What was added:**
    - Core `Platform`: `IDeviceStatus` (the battery and the network; the bar and battery-icon levels), `WindowsDeviceStatus` (`GetSystemPowerStatus`, `GetIfTable2` with `GetBestInterface`, and the WLAN service's signal quality), `PortableDeviceStatus` (Linux: the network only), and `DeviceStatusMonitor` (polled every 10 s and on a network change, raised only on a change, paused while a game runs).
    - Config: `[ui] show_clock`, `show_battery` and `show_network`, all on by default.
    - App: `Screens/StatusBar`, top right, above the settings screens: the network (Wi-Fi with its bars, a cable, or disconnected), the battery's charge (only on a device with one) and the time (Windows' short-time format), with Lucide icons (`godot/icons/status/`). Whatever is shown sits together against the right edge. The settings screen's new UI section turns each one on or off, live. The overlay's title stops short of them; "Favourite" and the job cards moved under them.
    - `--fake-status`, for captures.
  - **Verification:**
    - `dotnet build`: 0 warnings. 686 tests pass. The new tests cover the `[ui]` defaults, values, a wrong type and an unknown key; writing a `[ui]` key and removing it again; the bar and battery-icon levels; the monitor reporting only changes, nothing while paused, polling at once on start and on resume, and an unreadable state as unknown; `MIB_IF_ROW2`'s size and offsets, checked against .NET's own interface list on this PC; the Windows reads; and `--fake-status`.
    - Captures were reviewed: all three on, the games grid with "Favourite" under the indicators, every combination packed against the right edge (no clock; network only; no battery), weak Wi-Fi bars, the settings screen with the bar above it, a live toggle of the clock through `--nav-script`, 2564×1421 (sharp icons), and the real state on the Deck.
    - **Benches** (export, `artifacts/synthetic`, before and after in one session):
      - **Boot:** `app_startup_ms` 353 ms before, 363 ms after (medians of 5, within the session's noise).
      - **Boot frames:** hitches in 2 of 5 runs before and 1 of 5 after, all at frames 5–6, the glyph warm-up that was already there.
      - **Scroll** (3 runs each): 0 hitches; scroll p99 21.25–21.40 ms before, 21.39–21.50 ms after; main-thread allocation 64 B before, 96 B after (the clock's text, once a minute).
      - **A first version** built the bar in a warm-up step of its own, and that frame took 25–28 ms in every run: the time zone's and the time format's first use, and the monitor's first `System.Net.NetworkInformation` load. Those now run on the thread pool, and the nodes are made after the glyphs.
  - **Not done:**
    - On Linux, only the network is read (no battery, no Wi-Fi signal).
    - Themes can't style or move the indicators.
    - Watching them follow the real device (charger, Wi-Fi, sleep) is the owner's manual test ([manual-tests.md](manual-tests.md#status-indicators)).
- **2026-10-02: a game's details screen, and videos** (outside the milestones: the owner asked for them).
  - **What was added:**
    - Core `Media`: `IVideoDecoder` (`IVideoReader`: RGBA frames with their times, the size, pixel shape and length, and a seek; `IAudioReader`: interleaved float sound). Core `Platform`: `MediaFoundationVideoDecoder` and `MediaFoundation` (raw COM, as WIC is: a source reader per stream, the picture through the video processor to RGB, cropped to its aperture; the sound to float), `PlatformServices.CreateVideoDecoder` (none on Linux yet).
    - App `Screens`: `GameDetailsPanel` (Y on a game: the whole description, then every field; a card for the video, the front cover, the screenshot, then the other images) and `MediaViewer` (A on a card: full screen on black; left and right through the others; A pauses, plays and plays again). The overlay no longer shows a game's metadata, only its title, system and "Favourite"; a system's details stay.
    - App `Ui`: `VideoPlayback` (a decoding thread, frames in `Image`s of their own, the sound through an `AudioStreamGenerator`, timed by the sound played), `Thumbnails.LoadVideo` (a frame that isn't dark), `PanelPlacement.FullScreen`, `UiLayer.TopChanged` (the status indicators hide under a full-screen panel).
    - App `Navigation`: Y (or I) is `Secondary`, the game's details in the grid; the favourite is L3 (or F), in the grid and the details. The settings lists' second action is still Y (so I on the keyboard).
    - `--open=details`, and the nav script's `y` step (`favourite` is L3 now).
  - **Verification:**
    - `dotnet build`: 0 warnings. 703 tests: 699 pass. The 8 new ones: 7 `VideoDecoderTests` on MP4s that Media Foundation's own encoders write for the test (every frame in order, red over blue, the right way up and opaque; seeking to the start; a wrongly sized buffer refused without losing the frame; the sound as interleaved floats of the right length and level; no sound said; a broken and a missing file; the H.264 profile read from `avcC`), and `--open=details` with the `y` step. The 4 that fail are theme tests that still expect `dvd_case` as the built-in default template, which commit `e5b3a84` changed; they failed before this change too.
    - The owner's scraped videos (a copy of the export's user folder without its secrets): 57 of 72 play; 30 s of 360×480 decodes in about 1.5 s on one thread. The other 15 are H.264 4:4:4, which Windows can't decode, and they say so.
    - Captures were reviewed: the games grid's new hints, the details screen (fields, description, cards with a video's thumbnail and play mark), the description scrolled, the favourite added from the details and shown in the grid, an image full screen with its caption, a video playing (caption, then faded), a portrait arcade video at its own shape, and the 4:4:4 message.
    - **Benches** (export, `artifacts/synthetic`, scroll scenario, 3 runs each, before and after in one session): scroll p99 21.22–21.33 ms before, 21.19–21.51 ms after; hitches 0–1 before, 0–2 after (one run of each had a frame of about 50 ms); main-thread allocation 96 B in every run; start-up of our code 393 ms before and 387 ms after (medians). The synthetic library showed no covers in either build (0% textured), as it was before this change.
  - **Not done:**
    - H.264 4:4:4 videos don't play: a decoder of our own choosing (FFmpeg as a GDExtension) would play them, and is the owner's call.
    - On Linux, videos are listed but not played (no decoder yet).
    - The sound's sync with the picture, and a real pad's L3, are the owner's manual test ([manual-tests.md](manual-tests.md#a-games-details-and-videos)).
- **2026-10-02: an arcade cabinet template** (outside the milestones: the owner asked for it, from a 2D mock-up).
  - **What was added:**
    - App `Tools`: `ArcadeCabinetBuilder`, the top half of an upright cabinet (marquee, monitor tilted back in a framed bezel, a control panel with two joysticks and twelve buttons), exported by `BoxTemplateGenerator` to `godot/themes/memory-card/models/templates/arcade_cabinet.glb`: 1,402 triangles, three materials (`screenshot`, `label` and `case`, its colours from a palette texture).
    - The built-in theme: the `arcade_cabinet` template (`label = ["logo", "generated"]`), for Arcade, MAME, FinalBurn Neo, CPS (1, 2 and 3), Neo Geo, NAOMI (1, 2 and GD-ROM), Atomiswave, Model 2 and 3, ST-V, Triforce, Daphne, and the console and PC arcade systems.
    - The item shader and `ItemGrid`: a slot showing a logo draws it whole over its fallback (upright, or along a spine as before), where it used to crop it.
  - **Verification:**
    - `dotnet build`: 0 warnings. 705 tests: 701 pass. `BuiltInModelTests` checks the cabinet against the model spec (a built-in template now needs some slot, not a `cover`); `ThemeLoaderTests` lists it and checks its chain and the arcade systems. The 4 that fail are the theme tests that expect `dvd_case` as the default template, as before this change; the first of them also stops on six of the original systems having no `game_template` in the built-in theme (`gb`, `gbc`, `gba`, `snes`, `n64`, `saturn`), so its new checks don't run yet; what they check was confirmed against the manifest directly.
    - `odyssey-scrape inspect-model --kind=template`: accepted, within every budget, slots `label` and `screenshot`.
    - Captures were reviewed (a copy of the owner's arcade library with scraped art): the grid, focused on 3x3 Puzzle (as in the mock-up); games with no art (a printed title on the marquee, the switched-off screen); the Retro TV sample, whose plate now shows each logo whole; Windows's logo spines, unchanged.
    - **Benches:** [perf/arcade-cabinet.md](perf/arcade-cabinet.md). The box scroll is unchanged within noise; the cabinet costs 0.75 ms more GPU time than the box, and nothing on the CPU.
  - **Not done:**
    - A vertical game's screenshot (Pac-Man, most shooters) is centre-cropped to the 4:3 screen, showing its middle (fixed below: `fit`).
    - The two extra slot channels cost 16 MB of texture memory in every games grid, even with no arcade games: `SlotLayout` could be built from the templates the shown list uses, not the whole theme.
- **2026-10-02: the arcade cabinet's fixes, and fitting art whole** (the owner's requests after trying it).
  - **What was added:**
    - Core `Theming`: `[templates.<id>.fit]`, per slot `"crop"` (the default) or `"whole"` (`GameTemplate.WholeSlots`, `ShowsWhole`), validated like a chain (a bad value or slot is an error and the slot stays cropped; a slot the model lacks, a warning).
    - App: `ItemTemplate.ShowsWhole`; `ItemGrid` sets a "drawn whole" bit for such a slot (and a separate one for a logo); the item shader's logo branch is now `art_whole`, which draws a template's whole art with no margin and a logo as before.
    - The built-in theme: the cabinet's `screenshot = "whole"`, so tall games are pillarboxed on its switched-off screen.
    - The model: a 568 × 426 mm screen (was 480 × 360) in the same cabinet, with a thinner frame; the screen and marquee matte (roughness 0.9: glossy glass whited out the focused cabinet's screen, and middling roughness turned the bars grey); the side panels' lower part inside the control panel, well under its top and behind its front (their grey edges had shared the panel's front plane and stood just above its top, and flickered as the model moved).
  - **Verification:**
    - `dotnet build`: 0 warnings. 708 tests: 704 pass. The 3 new ones are `ThemeLoaderTests`: a fit read per slot, bad values and slots as errors at their keys with the slot left cropped, and a fit for a missing material as a warning; the built-in theme test also checks the cabinet's screen is fitted whole (though it still stops earlier on the known `dvd_case` failure; the same 4 fail as before).
    - `inspect-model --kind=template`: accepted, 1,402 triangles, as before. The other generated models are unchanged.
    - Captures were reviewed: tall games (1941, 1942, 1943, 19XX, 1945k III) pillarboxed on dark bars, wide ones filling the screen, the bigger screen, and the control panel's sides with no grey strips. The flicker itself can't show in a still: its cause, faces in or near the panel's planes, is gone.
    - **Benches:** [perf/arcade-cabinet.md](perf/arcade-cabinet.md#second-round-the-screen-fitted-whole-a-bigger-screen-no-flicker): the box unchanged, the cabinet 0.73 ms more GPU time than the box.
  - **Not done:** screenshots are fitted at their image's proportions, so one at an arcade board's native resolution (224 × 256 for 1942, shown on a 3:4 monitor) looks about 15% too wide; snapping a screen's art to 4:3 or 3:4 would fix that.
- **2026-10-02: layouts** (the owner's request): the systems as a grid, a carousel or one at a time, and the games as a grid, a carousel or a list with the focused game's model beside it; each grid's columns and rows automatic or set, and a system's own games grid size.
  - **What was added:**
    - Core `Config`: `[display] systems_layout`, `systems_columns`, `systems_rows`, `games_layout`, `games_columns` and `games_rows` (`DisplaySettings`, `SystemsLayout`, `GamesLayout`, `GridSize`), and a system's `games_columns` and `games_rows` (`SystemConfig`, `DisplaySettings.GamesGridFor`); a bad layout or size in settings.toml is an error and its default is used, a system's bad size a warning. `--layout` (`DebugOptions`, `LayoutOverride`), and the bench report's `options.layout`.
    - App: `GridLayout` and four shapes in `ItemGrid` (grid with set columns and rows, carousel, single, list), `Move(dx, dy)` and `PageStep`; `TitleList`, the list's titles in the overlay, following the games grid's scroll; the navigator lays each grid out from config (again when it's saved) and pages a list by its titles.
    - Settings: a Layout page (Look), and a system's own View, Columns and Rows on its page (each Default until set; Y goes back to it).
    - Later the same day (the owner's request): a system's own `games_layout` in systems.toml (unset follows `[display]`; a bad one warns), and its View row.
  - **Verification:**
    - `dotnet build`: 0 warnings. `tools/verify.ps1`: all checks pass, 715 tests; the new ones read the layouts, sizes and a system's own (and their errors and warnings), write and remove them through `ConfigWriter`, and parse `--layout`.
    - Captures were reviewed for every layout (systems: 3 × 2 grid, carousel, one at a time; PS2's games: 7 × 4, 5 and 1 column grids, carousel, list; the Layout page and a system's columns and rows after changing them with left and right): [perf/layouts/captures.jpg](perf/layouts/captures.jpg). Navigation was checked with `--nav-script` in each (left and right in a carousel and one at a time, up, down and a page in the list).
    - **Benches:** [perf/layouts.md](perf/layouts.md): the default grid's percentiles, GPU time, allocation (96 B), texturing (100%) and memory are unchanged; the carousel and the list hold the same pacing with a third less GPU time.
  - **Not done:**
    - Frames over 2× in the grid: 10 in 15 runs of the after build against 1 in 10 of the before build, single frames at random places with nothing new per frame and the same allocation and GC; leaving the list out didn't remove them, and the last after series was as clean as before. Unexplained; one more paired session (or PresentMon) should settle it.
    - The carousel and one at a time stop at the ends rather than wrapping round.
    - `artifacts/synthetic` streams nothing until its systems are rescanned (its media rows predate the media folder), so these benches used `synthetic-genbox`.
- **2026-10-03: sorting systems and games** (the owner's request): systems alphabetically, by manufacturer, by release year, or by manufacturer then year; games alphabetically, by last played, time played, date added or release date; each ascending or descending, alphabetical and ascending by default, and a system's own games sort and order. Favourites and Recently played stay first.
  - **What was added:**
    - Core `Config`: `[display] systems_sort`, `systems_sort_order`, `games_sort` and `games_sort_order` (`SystemSort`, `GameSort`, `SortOrder`, `SystemsOrdering`, `GamesOrdering`, `Sorts`), and a system's own `games_sort` and `games_sort_order` (`DisplaySettings.GamesSortFor`); a bad value in settings.toml is an error and its default is used, a system's a warning. The built-in settings.toml documents them.
    - Core `Library`: `SystemOrder` (the systems' comparer: what's missing last, ties by name) and `GetGamesAsync(system, ordering)` (A4 Grid queries).
    - Core `Data` and `Scanning`: migration 0005, `games.added_ms`, each ROM's creation time from the folder listing ("added"), updated when it changes; every system is rescanned once to fill it.
    - Defaults: a `year` for every console, handheld, computer and arcade board in the catalogue, and a manufacturer for 12 more systems, from memory (unverified).
    - App: the navigator sorts the systems after Favourites and Recently played, reads each list in its order, reads the shown list again when its order changes (keeping the focus on its game) and after a game ends when it's sorted by plays. Settings: Sort by and Order rows for the systems and the games on the Layout page, and for a system's games on its page (Default until set; Y goes back to it).
  - **Verification:**
    - `tools/verify.ps1`: all checks pass (759 tests, then the benchmarks). The new tests read the sorts and orders (defaults, errors, warnings, a system's own), check every catalogue console has a year, sort systems every way (`SystemOrderTests`), and sort games every way from real scans: hidden games left out, never played and undated games last, the user's release date over the scraped one, a file copied again moving to the newest.
    - Captures were reviewed against a copy of `artifacts/synthetic`: systems by release year, newest first (Favourites and Recently played first; ties by name); PS2's games Z to A in the list layout; the Layout page's rows; the games sort changed from the open list (settings.toml written, the list read again in the new order, the focus kept on its game); and a system's own sort and order set with left and right (systems.toml written, shown as its own).
    - **Benches:** core-bench before and after ([perf/m2-core.md](perf/m2-core.md#sorted-games-queries-added-2026-10-03)): title order unchanged (21 ms for 10,000 games), the other orders 20–27 ms, scans within noise. No `--bench` frame run: nothing per-frame changed, and the systems are sorted once per bind (at most 168 entries).
  - **Not done:**
    - LT and RT still jump where the first letter changes, which only helps in title order; in another order they could jump by year or month.
    - Favourites keep title order and Recently played newest first, whatever `games_sort` says.
    - The catalogue's years and the added manufacturers are unverified, like its ScreenScraper ids.
- **2026-10-03: turning an item with the right stick** (the owner's request): the right stick turns the focused system or game about its middle, and it goes back square when the focus moves.
  - **What was added:**
    - App `Navigation`: the right stick's four directions as gamepad actions (`nav_turn_*_pad`), read each frame by `NavInput.ReadTurn`; the navigator passes them to the shown grid while nothing else holds the input.
    - App `Grid`: `ItemGrid.Turn`, the player's turn in the focused item's transform (round its vertical without limit; towards or away from the camera, up to 83°; 3 rad/s at full tilt, the tilt squared), about its model's middle; the sway holds still once it's turned; the item left eases back square in its blend-out, and a bind sets everything square.
    - Core `Diagnostics` and app `Boot`: the nav script's `turn` step (the stick held right and a little up until the next step, on a joypad device id of its own).
  - **Verification:**
    - `dotnet build`: 0 warnings. `DebugOptionsTests` pass with the new step.
    - Captures were reviewed on `synthetic-genbox` (PS2's games, and the systems): a game turned in place; the focus moved on (the one left square, the new one square); back to the turned game (square); a system's card turned.
    - **Bench:** an editor scroll bench (`synthetic-genbox`, 20 s): the scroll's main-thread allocation is 96 B, as before. No export bench: nothing else per frame changed, and the turn is a few more terms in a transform already written each frame.
    - A real pad is the owner's manual test ([manual-tests.md](manual-tests.md#turning-an-item-with-the-right-stick)).
  - **Not done:** the controls hints don't mention the right stick (the games' line is already full); no keyboard or mouse equivalent.
- **2026-10-03: deleting a game** (the owner's request): "Delete this game", last in a game's options, deletes its file and, for a playlist, every file it lists, after a question that lists them.
  - **What was added:**
    - Core `Library`: `GameDeleter` (finds a game's files through its playlists, read from disk as the scanner reads them, keeping files another game's playlist lists; deletes the game's own file first, then the rest and the folders left empty), `LibraryService.PlanDeleteAsync` and `DeleteGameAsync` (waits for a running scan; takes the game out of `library.db` in one transaction, no rescan), `LibraryStore.RemoveDeletedGame`; `PathKeys.ResolveRelPath` (a playlist reference as written, case kept, to find the file).
    - App `Options`: the "Delete this game" row and its question (the files, the first six and a count, their size and folder, what's kept, a shortcut's game staying installed, the user data kept), with "Keep it" focused. App `Settings`: `LibraryJobs.PlanDeleteAsync`, `DeleteGameAsync` and the `GameDeleted` event. App `Screens`: `Navigator.OnGameDeleted` (the systems grid built again, the shown list read again with the focus on the next game, or back to the systems when its card dropped out).
  - **Verification:**
    - `dotnet build`: 0 warnings. Seven new `LibraryServiceTests`: a lone file (its user data back when the file is), an `.m3u` of `.cue` discs with their tracks and a missing disc (the folder removed), a shared disc kept, a read-only file, a locked game file (nothing deleted; Windows only), a game gone from the library; after each delete a rescan changes nothing.
    - Captures on a throwaway library (`artifacts/delete-test`, made up files): the row, the question for an `.m3u` of three `.cue`/`.bin` discs, the grid after (focus on the next game, the disc folder gone), and deleting the system's last game (its card gone, back on the systems).
    - No bench: nothing per frame changed.
    - A real NAS folder is the owner's manual test ([manual-tests.md](manual-tests.md#deleting-a-game)).
  - **Not done:** no Recycle Bin; the game's media-folder files and user data stay (clear its metadata first to remove its art); a system with `rom_dirs` in several folders resolves a playlist's files in its own folder only, as an emulator would.
- **2026-10-03: ScreenScraper system ids** (the owner's request): every built-in system ScreenScraper has now has its `screenscraper_id`, checked against `systemesListe.php`.
  - **What changed:**
    - `Defaults/systems.toml`: 69 catalogue systems had no id and now have ScreenScraper's (some share one, where ScreenScraper has one system for them: ARCHITECTURE.md A5, "The ES-DE catalogue"); `pc88` (147, Sega Classics) is 221 and `pc98` (149, Seta) is 208.
    - `odyssey-scrape ss-systems` also lists ScreenScraper's systems that no system uses, so a missing or wrong id can be found.
  - **Verification:** `ss-systems` with the owner's credentials: 250 ScreenScraper systems; every row with an id names the right console. `dotnet test`.
  - **Not done:** twelve systems ScreenScraper has no system for stay without an id (`ags`, `chailove`, `consolearcade`, `flash`, `mess`, `mugen`, `pcarcade`, `ports`, `symbian`, `triforce`, `trs-80`, `zxnext`); no live scrape of the newly covered systems.
- **2026-10-03: system years and descriptions from ES-DE** (the owner's request): every system's year and a description, from ES-DE's theme metadata (`themes/linear-es-de/system/metadata`).
  - **What changed:**
    - `Defaults/systems.toml`: `year` from ES-DE's `systemReleaseYear`, the earliest of the system's and its aliases' (38 changed, 20 of them engines and stores that had none); a `description` on all 167 systems, from ES-DE's English `systemDescription`, in one paragraph with UK dates and spelling (ARCHITECTURE.md A5, "The ES-DE catalogue").
    - Core `Config`: a system's `description` (`SystemConfig.Description`); a user's replaces the built-in one.
    - App: the systems' details show it bottom right (`DetailsFormatter.System`), four lines and then an ellipsis.
    - `desktop` (Desktop Apps), which came with the ScreenScraper ids, is kept as a built-in system beside Windows and Steam: a colour and the `generic_box_logo` in the base theme, and the tests that said it was left out now expect it (ARCHITECTURE.md A5, "Windows and Steam games").
  - **Verification:**
    - `dotnet test`: all pass. The new tests check every system has a one-line description, a user's replaces it, and only the six catch-alls have no year. The 3 tests the `desktop` system broke pass again (the base theme's colour for every system, the Steam store systems, the catalogue's left-out systems), and `desktop` runs its own files as Windows and Steam do.
    - Captures on `synthetic-genbox`: Game Boy Advance's description under the overlay's four lines; a user's description with Japanese text (as in X68000's and FM Towns') draws through the system font fallback.
  - **Not done:** systems with no year: `arcade`, `consolearcade`, `desktop`, `lcdgames`, `pcarcade`, `ports` (ES-DE says "Various"). Some of ES-DE's years date something other than the hardware (`daphne` 2007, the emulator; `ti99` 1981, where its description says 1979). Several descriptions are a family's (`msx1` and `msx2` share MSX's, `windows3x` and `windows9x` Windows', `wonderswancolor` WonderSwan's, `naomigd` NAOMI's; `xbox` describes the brand). No screen shows more of a description than the overlay's four lines.
- **2026-10-03: a system's details screen** (the owner's request): Y on a system opens its details, as Y on a game does, with all its metadata and a large version of its card's model; the overlay no longer shows a system's details.
  - **What was added:**
    - App `Screens`: `SystemDetailsPanel` (Y on a system, Favourites or Recently played: the card's model on the left; the whole description and every field on the right, scrolled with up and down; Y or B goes back) and `DetailsFormatter.SystemFields` (maker, year, games, last scan, emulator and alternatives, ROM folders, subfolders, what's left out, file types, aliases, the games' view, grid size and sort, the card's and games' models, ScreenScraper and IGDB ids, the Steam store, the id) and `VirtualFields`.
    - App `Screens`: `ModelView`, the model large: a `SubViewport` with its own world, the system's look (`LookStage`) and a one-cell `ItemGrid` (one at a time, focused, zoomed to fill about two thirds of the view), so it's drawn as in the grid; the right stick turns it, and left and right a step at a time. One is made on first use and kept, parked when the screen closes.
    - App `Grid`: `ItemGrid.FadeAtEdges` (the item shader's `edge_fade` off) and `ItemScale`.
    - The overlay keeps a system's name and the line under it, and drops its rows and description; the systems' hints add "Y / I  Details". The navigator no longer formats a system's details when the focus rests.
  - **Verification:**
    - `tools/verify.ps1`: all checks pass (775 tests; nothing in Core changed).
    - Captures were reviewed on `synthetic-genbox` with the console theme: the systems grid (no rows bottom left, the new hint); Mega Drive (its console filling the view, its focused clip putting the cartridge in), Game Boy, a memory card with its name on the label (Game Boy Advance, Dreamcast), Favourites (its games counted); the fields scrolled to the end (paths wrapping inside the column, multi-line values under their label); the model turned with the right stick; and a second screen on another system after the first (the kept view showing the new model, square).
    - **Opening it** (an editor bench with the nav script, Debug build, not comparable with the targets): the first open's frame 89–98 ms (a game's details: 50 ms); later opens 33 ms, as they were 43–45 ms before the view was kept (main thread about 21 ms, most of it the panel's labels entering the tree, which a game's details also pay). No `--bench` scroll run: nothing per frame in the grids changed, and the screen renders only while open.
    - A real pad, and the 4K dock, are the owner's manual test ([manual-tests.md](manual-tests.md#a-systems-details)).
  - **Not done:**
    - The first open's frame: making the view (and its render target's first frames) could move into the warm-up after `interactive`.
    - The default ROM folders are listed as candidates (the first that exists is used), not checked on disk, since a disconnected share can take tens of seconds to answer; the library's `rom_dirs` has the folder the last scan used, but no API reads it yet.
    - No per-system play statistics (time played, games played) or favourites count: they'd need a new library query.
    - `--layout`'s override isn't reflected in the games view the screen reports (it shows settings.toml's).
