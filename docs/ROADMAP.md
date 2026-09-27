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

## M6: Theming and custom models

**Scope**
- Theme loading and validation.
- The gradient, lights and per-system looks, with cross-fades.
- The five built-in templates: `dvd_case`, `jewel_case`, `tall_jewel_case`, `cartridge_box`, `clamshell`.
- Runtime `.glb` conversion and caching, material remapping, media slots, and idle/focused/launch clips with procedural fallbacks.
- `ModelInspector` budgets.

**Acceptance**
- Tests use fixture `.glb` files that are in budget, over budget and more than 2× over (rejected, with fallback), plus slot and clip name matching.
- Captures of the default theme and one alternative theme. The corner colours match their hex values.
- The M1 targets hold with in-budget custom models on screen.
- Carried over from M1: runtime `.glb` conversion on a worker thread is measured.

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
| M2 Core data layer | Not started | | |
| M3 Launching | Not started | | |
| M4 Scraping and media pipeline | Not started | | |
| M5 3D navigation | Not started | | |
| M6 Theming and custom models | Not started | | |
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
