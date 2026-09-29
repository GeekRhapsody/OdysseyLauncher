# M6 part 1, themes and media binding: measurements

Measured on 29 September 2026 on the baseline Steam Deck (the machine in [m1-spike.md](m1-spike.md#machine)), docked. Godot reported the display as 2560×1440 at 59.94 Hz, so "fullscreen" below means 2560×1440 (3D at 0.75, the 1080p cap). Everything is ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on, windowed at 1280×800 unless a row says otherwise. Bench JSON for every row is in [m6/](m6/), and the captures are in [m6/captures.jpg](m6/captures.jpg). The brief and the acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m6-theming-and-custom-models).

## Library and themes

| | How it's made |
|---|---|
| Library | `tools/synthetic-library` with `--games=2620 --others=20 --slots=back,spine,screenshot,logo`: 20 systems (22 cards), **3,000 games** (PlayStation 2 has 2,620, every other system 20). 2,667 games have a cover and a back, spine, screenshot and logo (each a different M1 spike image, with its BC7 derivative); every ninth game has no art. |
| Memory Card | The built-in theme ([godot/themes/memory-card/](../../godot/themes/memory-card/theme.toml)): the M5 boxes, whose slots are cover, back and spine, each `[<kind>, "generated"]`. So this library streams **three slots** with it, where M5 streamed the cover only. |
| Slot Showcase | The test theme ([tests/themes/slot-showcase/](../../tests/themes/slot-showcase/theme.toml)), a user theme copied into the library's `themes/`: a tall case with `cover = ["cover", "generated"]`, `spine = ["spine", "logo", "generated"]` and `screenshot = ["screenshot", "hero", "authored"]` (the model's own test card), 8 columns on the PS2 grid. The 6 extra systems' `game_model` (the synthetic library's systems.toml) keeps the built-in boxes for them, so it streams four slots: cover, back, spine, screenshot. |

```powershell
dotnet run --project tools/synthetic-library -c ExportRelease -- "--out=$PWD\artifacts\synthetic-3000" "--covers=$PWD\artifacts\spike-library" --games=2620 --others=20 --slots=back,spine,screenshot,logo
Copy-Item -Recurse tests\themes\slot-showcase artifacts\synthetic-3000\themes\
$lib = "$PWD\artifacts\synthetic-3000"
.\tools\bench-export.ps1 -Runs 5 -Frames 300 -Label boot -AppArgs "--user-dir=$lib"
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Label scroll -AppArgs "--user-dir=$lib", '--bench-scenario=scroll'
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Label control -AppArgs "--user-dir=$lib", '--bench-scenario=scroll', '--no-textures'
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Label showcase -AppArgs "--user-dir=$lib", '--theme=slot-showcase', '--bench-scenario=scroll'
.\tools\bench-export.ps1 -SkipExport -Runs 2 -Fullscreen -Label fs -AppArgs "--user-dir=$lib", '--bench-scenario=scroll'
```

The "before" series is the M4 commit (`bc16c78`) on the same library, earlier the same day.

## Results against the targets

| Target (A3) | Before (M4, cover only) | Memory Card (3 slots) | Slot Showcase (3 slots in its template, 4 streamed) | Verdict |
|---|---|---|---|---|
| Our start-up < 1 s, warm | 332 ms median (317–372) | **347 ms** median (309–465), the committed build | 323 ms (318–333) | Met |
| p99 ≤ 1.1× refresh (18.35 ms) | 20.70–21.11 ms; control 20.97–21.16 | 20.69–21.26 ms; control 20.96–21.29 | 20.76–21.30 ms; control 20.77–20.94 | **Not met, and not ours**, as in M5: the no-texture control is the same |
| Hitches ≤ the control's | 2, 2, 2 against 1, 0, 0 | **0, 0, 0** (and 0, 0 committed) against 3, 0, 2 | **0, 0, 0** (and 0, 3 committed) against 2, 0, 1 | Met in the final series. One of the two committed Showcase runs had 3, more than its control, with every upload under 1.1 ms, so not the streamer |
| 0 frames over 2× refresh | 1, 2, 1 | **0** in every run | 0 in 4 runs of 5; 3 in the other | Met but for that one run, which the control series also had (0, 0, 2) |
| 0 hitches in fullscreen | — | 1, 0 (control 0, 0); 0 over 2× | — | Not met in one run of two (25.8 ms), as in M5 |
| Visible grid textured ≤ 100 ms | 18.7–20.0 ms | 14.5–19.7 ms (fullscreen 19.6–20.0) | 13.2–19.7 ms | Met |
| ≥ 99% of on-screen media textured while scrolling | 100.00% (lowest frame 100%) | 100.00% (lowest frame 100%), every slot counted | 100.00% (lowest frame 100%) | Met |
| Working set ≤ 512 MB | 350–351 MB (peak 367) | 420–421 MB (peak 439); fullscreen 425 MB (peak 445) | 425–428 MB (peak 450) | Met; +70 MB over M4 (below) |
| Pool texture memory ≤ 64 MB | 21.8 MB (the cover array) | 32.8 MB (cover 21.8 + back and spine 5.5 each) | 38.3 MB (+ screenshot) | Met; all eight slots would be 60.1 MB |
| Main thread ≤ 4 KB per 60 s scroll | 64 B | **64 B** | 64 B | Met |

The scroll covers 524 rows of PlayStation 2 in 60 s with Memory Card (5 columns) and 327 rows with Slot Showcase (8 columns). Uploads per scroll: 2,298 before, 6,894 with three slots (2,329 covers and 4,658 256² layers; mean 0.062–0.082 ms), 6,837 with Slot Showcase.

## What changed on the way

Each was found with the bench and fixed (or tried and dropped) before the final series.

| Problem | Evidence | Change |
|---|---|---|
| **Upload bursts.** A whole row of covers uploaded in one frame (5 on Memory Card, 8 on Slot Showcase's 8 columns) made single `UpdateLayer` calls take 14–31 ms. This was there before M6 too (M4's maxima: 14.0–18.1 ms), and caused its scroll frames over 2×. | [Upload cap](#upload-cap) | The cap is now 4 cover-sized uploads a frame (a 256² layer counts a quarter), down from M1's 8. |
| **Start-up +105 ms** in the first build (437 ms median): the theme was resolved before the library opened, and the look, the games grid and every template's material were built on the critical path. | [m6/first-boot/](m6/first-boot/) | The theme resolves while the library opens; the built-in theme's manifest is read while config loads; the look stage and the games grid (its title atlas and slot-state texture) are built in `_Ready`, while the main thread would only wait. 437 → 371 ms. |
| **Models loaded one after another.** Godot's threaded loader took about 25 ms a model, serially: the built-in theme's six took about 150 ms, now starting only once the theme is known, which put them on the critical path. | `models_loaded` in [m6/exp-early-theme-boot/](m6/exp-early-theme-boot/) | Every model, built-in ones too, is now the `.glb` itself (Godot's "keep file" import) parsed by `GltfDocument` on its own worker: six in parallel, about 27 ms each. 357 → 347 ms, and one loader for every theme. |
| Starting the built-in models' threaded loads from the thread pool, during config | models finished later (296–462 ms after our first code, against 268–365) | Dropped ([m6/exp-prefetch-boot/](m6/exp-prefetch-boot/)). |
| A 36 ms frame 0.5 s after interactive in one boot run | the 256² array was installed and warmed on the main thread | It's created and warmed on the worker that builds it. |

### Start-up

Where our 347 ms goes now, against M4 (typical runs, ms after our first code):

| Mark | M4 | M6 | What |
|---|---|---|---|
| `config_loaded` | 115 | 115 | Settings, systems and emulators (the built-in theme's manifest is read alongside) |
| `theme_resolved` | — | 126 | The active theme and each system's model candidates |
| `library_opened` | 186 | 185 | Both DBs, in parallel with the theme |
| `models_loaded` | 196 | 255 | M4 started its models at `main_ready` (47 ms); M6 can only once the theme is resolved, then loads them in parallel |
| `scene_built` | 275 | 285 | The look and the games grid were built in `_Ready`; this is the templates (15–18 ms) and the systems grid |
| `interactive` | 317 | 333 | |

## Upload cap

Slot Showcase's scroll, one run each ([m6/exp-showcase-cap8/](m6/exp-showcase-cap8/), [m6/exp-showcase-cap4/](m6/exp-showcase-cap4/)):

| Cap (cover-sized uploads a frame) | 512² uploads: mean / max | 256² uploads: mean / max | Frames at the cap | Textured | Visible textured |
|---|---|---|---|---|---|
| 8 (M1 to M5) | 0.974 ms / 21.1 ms | 0.029 ms / 0.8 ms | 317 | 100% | 18.8 ms |
| 4 (M6) | 0.109 ms / 0.9 ms | 0.032 ms / 0.3 ms | 770 | 100% | 18.5 ms |

Across every series, the upload maximum was 14–31 ms at 8 and 1.1–1.7 ms at 4 (4.7 ms fullscreen), with the grid 100% textured throughout.

## Memory

- **Texture arrays:** 64 cells × 341 KB = 21.8 MB for the cover, and 64 × 85 KB = 5.5 MB for each other slot (ARCHITECTURE.md A3).
- **Working set:** 420 MB with textures against 351 MB before, in the boot scenario as well as while scrolling, windowed and fullscreen alike. It's not the slot arrays (a theme streaming the cover only measured the same 419–421 MB: [m6/exp-cover-only-boot/](m6/exp-cover-only-boot/)), nor a material per template (sharing one between the built-in boxes changed nothing: [m6/exp-shared-materials-boot/](m6/exp-shared-materials-boot/)). The no-texture control measured 363–395 MB in different series of the same build, so the working set moves by about 30 MB between sessions anyway. The target (512 MB) is met with 60–90 MB to spare; finding the rest of the difference needs a memory profiler.

## Corner colours

The look's corners at rest, captured with `--no-overlay` (the overlay's scrims darken the top and bottom):

| Theme | Expected | Mobile (our renderer) | Forward+ |
|---|---|---|---|
| Memory Card | #1B1F4A #1B1F4A #04040C #0B0B24 | #1C1F4A #1C1F4A #06060D #0D0D24 | exact |
| Slot Showcase | #3A1030 #10303A #080410 #041018 | #3A1230 #12303A #060612 #061219 | exact |

The Mobile renderer composites the canvas background through its 3D buffer, whose precision moves dark values by up to 2/255. Forward+ renders every corner exactly, so the theme code is right; M1 chose Mobile for 36–42% less GPU time, and the shift isn't visible.

## Themes at run time

- **Switching** (`--nav-script` `theme`, in the editor run): the next theme was loaded 67 ms after it was asked for, and applied in 2.2 ms on the main thread (templates, layout, look, and the shown list loaded again). Its texture arrays were built and warmed on a worker in 26–31 ms.
- **Media changes:** with art added for a visible game while the app ran, the nav script's `rescan` reported `Media: 1 game(s) in ps2 changed and were rebound in place`; the cell showed its fallback while the derivatives were missing, then the new cover and screenshot once the bake finished (`Derivatives: 2 baked`). Removing the art rebound it back to its fallbacks. Both are in the captures.
- **Per-game models:** a `.glb` in `ConfigDir/models/games/ps2/` was indexed by the rescan and loaded on a worker in 7.2 ms (parsed and converted; 0.3 ms to upload on the main thread): the M1 carry-over's measurement of run-time `.glb` conversion on a worker.

## Not measured

- Handheld (undocked) mode, 3840×2160 docked, and PresentMon: as in M5, they need the owner or the hardware.
- A theme switch and a look cross-fade in the export: only in editor runs and captures. The manual test covers them on the real display ([manual-tests.md](../manual-tests.md#m6-themes-with-a-controller)).
- The working set's remaining 70 MB (above).
