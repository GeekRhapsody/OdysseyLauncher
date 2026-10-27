# The ES-DE catalogue: what it cost at boot

2026-10-01. The built-in systems went from 14 to 164 and the emulator profiles from 18 to 474 (ARCHITECTURE.md A5, "The ES-DE catalogue"), which is about 140 KB of TOML for config to read on the boot path. This note records how that was kept off the headline numbers.

## Config load

Core's timings on the export's runtime (`tools/core-bench`, .NET 8.0.31, `ExportRelease`; the tool now loads config with `FileExists = null`, as boot does):

| | Before (14 systems, 18 profiles) | Catalogue through Tomlyn only | Catalogue with `TomlFast` |
|---|---|---|---|
| Warm | 2.1 ms | about 50–60 ms (Tomlyn parsed the three files in about 20 + 30 ms) | 9–11 ms |
| First in the process (JIT included) | 46–64 ms | about 114 ms | 93–132 ms |

- **`TomlFast`** (`Config/TomlFast.cs`) reads the built-in defaults and the built-in theme: a strict parser for the plain TOML they use, falling back to Tomlyn for anything else. `TomlFastTests` builds the same tree, positions included, with both parsers for every shipped file. The warm remainder is Core's own work: about 2–3 ms of parsing, 5 ms reading 474 profiles and 1.5 ms reading 164 systems.
- **The install checks left boot.** They did a `File.Exists` for each emulator of each system (about 450 calls, 10–25 ms on this machine, and unbounded on an unplugged share). The app loads config again after `interactive` for the systems that have games, on the thread pool (`AppServices.CheckInstallsAsync`), and only for each system's default emulator.
- The first load is mostly JIT (the export isn't ReadyToRun), as in M2.
- `Loading_the_default_config_meets_its_budget` has a budget of 20 ms now (it was 10): 12 ms measured in the Debug test run.

## Boot in the app

`tools/bench-export.ps1`, the `boot` scenario on the 20-system synthetic library, 1280×800 windowed, mobile/d3d12, 5 warm runs each, before in a worktree of the previous commit and after in the working tree, back to back with nothing else running (the grid shows the same 20 systems in both; the other 150 are empty and hidden):

| | Before | After |
|---|---|---|
| Our start-up (first autoload to `interactive`), per run | 387, 411, 594, 587, 471 ms | 549, 387, 370, 385, 420 ms |
| Median | **471 ms** | **387 ms** |
| Frame p99 (median) / hitches | 22.3 ms / 0, 0, 2, 2, 0 | 20.8 ms / 0 in every run |

The runs vary by more than the difference (370–594 ms), so the result is "no measurable cost", not "faster". After it, the systems grid's pool was sized from the shown systems instead of every system (it would otherwise have grown from 27 to 64 slots); that change was checked by the headless smoke run and a capture, not re-benched.

**2026-10-27: back to every enabled system.** Settings > Look > Show systems without games shows the empty systems without a restart, and the pool can't grow, so it's sized for every enabled system again (64 cells with the catalogue; a library with 52 or more systems with games had 64 already). A pool sized for 3 shown systems (24 cells) drops the grid from 5 columns to 4 at 1280×800 once they all appear. Same method, the export at `ea023f3` before and with the change after, the 20-system synthetic library (32 cells to 64), medians of 5 warm runs:

| | Slab before | Slab after | Console before | Console after |
|---|---|---|---|---|
| Our start-up | 284.2 ms | 279.1 ms | 1,582.2 ms | 1,603.7 ms |
| Frame p99 / hitches | 17.06 ms / 0 | 17.02 ms / 0 | 17.20 ms / 0 | 17.32 ms / 0 |
| Video memory | 296.2 MiB | 315.2 MiB | 1,993.8 MiB | 2,009.5 MiB |
| Texture memory | 255.8 MiB | 274.3 MiB | 1,529.1 MiB | 1,544.8 MiB |
| Working set | 351.1 MiB | 353.2 MiB | 591.4 MiB | 592.0 MiB |

Start-up and frames show no measurable change (Console's runs, 1,570–1,618 ms before and 1,592–1,636 ms after, overlap). The cost is video memory: about 16 MiB in both themes, and on Slab another 3 MiB (its cards' logo layers). The 16 MiB wasn't measured apart, but the only other per-cell texture is the systems grid's title atlas, a render target that grows from 6 × 6 blocks of 192 px to 8 × 8.

## What else grew

- The settings screen's ROM folders page lists all 164 systems (a row each, built when it's opened); the Emulators page lists only the profiles the systems with games use.
- A rescan after boot scans every system never scanned (150 on the first run after this change, in the background, one transaction each).
- `ThemePlan` resolves model candidates for every system at boot (a lookup each, no more models: the catalogue systems use the five built-in boxes and the generic card).
