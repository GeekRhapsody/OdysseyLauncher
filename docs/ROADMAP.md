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
  - checking the default `screenscraper_id` values against `systemesListe.php`, which needs developer credentials: `odyssey-scrape ss-systems` prints the comparison
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

Still to do in **part 2**: `ModelInspector` and the budget fixtures (in budget, over, and more than 2× over with fallback); caching converted user models in `CacheDir/models/`; the rest of material remapping (normal, emissive, metallic, unlit, alpha, texture transform) and mipmapping user textures; idle, focused and launch clips; and, carried over from M5, the LRU texture cache and the focused item's full-resolution art.

## M7: Settings UI

**Scope**
- Controller-navigable screens for ROM folders per system, the emulator per system and per game, title overrides, the theme, and scraper credentials (masked).
- Rescan and scrape actions with progress.

**Acceptance**
- TOML writes preserve comments and formatting (round-trip tests) and contain only changed values.
- Secrets are written only to `secrets.toml`.
- Input is validated before saving.
- Changes apply without a restart where feasible.

## Progress

Update this at the end of every milestone: the status, the date, and the evidence (commit, bench JSON and captures).

| Milestone | Status | Finished | Evidence |
|---|---|---|---|
| Scaffold | Done | 2026-09-27 | Initial commit; `tools/verify.ps1` green; capture corners exact; bench baseline below |
| M1 Performance spike | Done (reduced scope; the revised targets need the owner's sign-off) | 2026-09-27 | [SPIKE_RESULTS.md](SPIKE_RESULTS.md); per-configuration JSON in [perf/m1/](perf/m1/); spike code on branch `spike/grid-perf` (`e165f58`, `7fe35ea`); scaffold matrix in [perf/m1-spike.md](perf/m1-spike.md) |
| M2 Core data layer | Done (reduced scope: Core only; app-side items moved to M4–M6) | 2026-09-28 | [perf/m2-core.md](perf/m2-core.md); 134 tests, including the scan benchmarks; see the log below |
| M3 Launching | Done (a real emulator and focus are the owner's manual test: [manual-tests.md](manual-tests.md#m3-launching-a-real-emulator-and-focus)) | 2026-09-28 | [perf/m3-launching.md](perf/m3-launching.md), bench JSON in [perf/m3/](perf/m3/); 217 tests; `verify.ps1` now ends with a headless `--launch` through the fake emulator; see the log below |
| M4 Scraping and media pipeline | Done (the live 50-game scrape and the `systemesListe.php` check need the owner's credentials: [manual-tests.md](manual-tests.md#m4-a-live-scrape)) | 2026-09-28 | [perf/m4-scraping.md](perf/m4-scraping.md), bench JSON in [perf/m4/](perf/m4/), [real cover capture](perf/m4/real-cover-bc7.png); 321 tests, 62 of them new for scraping and derivatives; see the log below |
| M5 3D navigation | Done (p99 and fullscreen hitches not met, the same without the launcher's work; handheld, 4K and PresentMon still to do) | 2026-09-28 | [perf/m5-navigation.md](perf/m5-navigation.md), bench JSON in [perf/m5/](perf/m5/), [captures](perf/m5/captures.jpg); 259 tests, including the model spec check; see the log below |
| M6 Theming and custom models | In progress: part 1 of 2 done (themes and media binding) | 2026-09-29 (part 1) | [perf/m6-themes.md](perf/m6-themes.md), bench JSON in [perf/m6/](perf/m6/), [captures](perf/m6/captures.jpg); 368 tests; see the log below |
| M7 Settings UI | Not started | | |

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
  - **Not done:** the live 50-game scrape and the `systemesListe.php` check (the owner's credentials); ReadyToRun (the owner's approval); scrolling while the baker runs isn't benched.
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
