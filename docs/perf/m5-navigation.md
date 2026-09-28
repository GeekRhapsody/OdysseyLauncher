# M5 3D navigation: measurements

Measured on 28 September 2026 on the baseline Steam Deck (AMD Custom APU 0405, Windows 11 build 26200; the machine in [m1-spike.md](m1-spike.md#machine)), docked. Godot reported the display as **2560×1440 at 59.94 Hz** (WMI says 3840×2160, as in M1), so "fullscreen" below means 2560×1440 and 4K wasn't measured. The acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m5-3d-navigation). Bench JSON for every row is in [m5/](m5/), and the captures are in [m5/captures.jpg](m5/captures.jpg) and [m5/spine-and-back.jpg](m5/spine-and-back.jpg).

Everything is ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on, unless a row says otherwise. Medians over the runs shown; rows in a table were benched in one session.

## Libraries

| Library | How it's made | Systems | Games | Art |
|---|---|---|---|---|
| Synthetic | `tools/synthetic-library` (below): the 14 built-in systems plus 6 more; PlayStation 2 has 10,000 games, the others 30–400 | 20 (22 cards with Favourites and Recently played) | 14,215 | 12,636 covers in `ConfigDir/media`, with baked BC7 derivatives; every ninth game has none |
| Real | The owner's NAS over SMB (`S:\`), the 14 built-in systems pointed at their folders with `rom_dirs`. Read only. | 14 (16 cards) | 9,422 | none: art is indexed from `ConfigDir/media` only, and scraping is M4 |

```powershell
# The synthetic library, from the M1 spike's covers (hardlinked, so it costs almost no disk). About 50 s.
dotnet run --project tools/synthetic-library -c ExportRelease -- "--out=$PWD\artifacts\synthetic" "--covers=$PWD\artifacts\spike-library"

# The real library: a user folder whose systems.toml points each system at the NAS, e.g.
#   [systems.ps2]
#   rom_dirs = ['S:\Sony PlayStation 2']
# The first boot scans it in the background (9,422 games in under 2.5 s, warm NAS).
```

## Commands

```powershell
.\tools\bench-export.ps1 -Runs 5 -Frames 300 -Label boot -AppArgs "--user-dir=$PWD\artifacts\synthetic"
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Label scroll -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll'
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Label control -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll', '--no-textures'
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Fullscreen -Label scroll-fs -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll'
python tools/bench-summary.py "artifacts/bench/*-scroll*"
```

- **Boot scenario:** boots into the systems grid and samples 300 frame intervals from `interactive`.
- **Scroll scenario:** boots, enters the biggest system (PlayStation 2, 10,000 games, 6 columns, 1,666 rows), waits for its first screen of covers (or 3 s), then scrolls from the first row to the last in 60 s: 27.8 rows or 167 covers a second, the M1 rate. It measures the scroll frames only.
- **No-texture control:** the same scroll with `--no-textures` (no cover streaming), in the same session, as the reworded hitch target needs.
- **Frame window:** the bench window now starts at `interactive`, not at the first drawn frame. The engine sometimes draws an empty frame before the scene is built, and in 1 run in 7 or so the first interval then spanned the scene build (about 110 ms), which is start-up rather than a hitch.

## The committed build

The final code, benched with nothing else running ([m5/commit-boot/](m5/commit-boot/), [m5/commit-scroll/](m5/commit-scroll/)):

| Scenario | Our start-up | Frames | Hitches | Over 2× | Textured | Main thread | Working set |
|---|---|---|---|---|---|---|---|
| Boot, synthetic, 5 × 300 frames from interactive | 359 ms (334–420) | mean 16.61–16.64 ms, p99 20.81–21.32 ms, max 27.4 ms | 0, 1, 0, 0, 0 | 0 | — | — | 352–353 MB |
| Scroll, 10,000 games, 2 × 60 s | 469–470 ms | mean 16.68 ms, p99 21.09–21.20 ms, max 24.9 ms | 0, 0 | 0, 0 | 100.00% (lowest frame 100%), visible in 13–20 ms | 64 B; 3 gen0 and gen1, no gen2 | 355–357 MB (peak 365) |

The one boot hitch is the first glyph warm-up step (frame 3). An earlier series of the same build, run while other work was going on on the machine, had 1–4 hitches a boot run and one scroll run with 6: **benches need the machine otherwise idle.**

## Results against the targets

The series below were run before the last three changes (the staging-buffer cap, glyphs in thirds, and the pull-in of lifted edge items), except where a row says otherwise; the committed build above matches or beats them.

| Target (A3) | Windowed 1280×800 | Fullscreen 2560×1440 (3D at 0.75) | Verdict |
|---|---|---|---|
| Our start-up < 1 s, warm | **340 ms** synthetic (321–355), **338 ms** real (325–349); 5 runs each | 689–818 ms median, one run 1,259 ms | Met |
| p99 ≤ 1.1× refresh (18.35 ms) | 20.80–21.31 ms scrolling; control 20.98–21.43 ms | 21.89–22.07 ms; control 22.59–22.76 ms | **Not met, and not ours:** the no-texture control and a run with both grids hidden (20.25 ms) are the same. See [Frame pacing](#frame-pacing). |
| Hitches ≤ the control's | 1 in 3 runs (25.1 ms); control 1 in 3 | 1 in 3 (26.2 ms); control 1 in 3 | Met |
| 0 frames over 2× refresh | 0 in every scroll run | 0 in every scroll run | Met in the scroll frames. Fullscreen has one frame of 430–480 ms, 3 frames after interactive, in some runs (below). |
| 0 hitches in fullscreen | — | 0, 0, 1 (and 1, 1 in the staging-buffer runs) | **Not met, and not ours:** the fullscreen control also has 1 in 3 |
| Visible grid textured ≤ 100 ms | 13–19 ms | 13–22 ms | Met |
| ≥ 99% of on-screen covers textured while scrolling | 100.00% (lowest frame 100%); after the staging cap, 99.99% (lowest single frame 74%) | 100.00% / 99.99% | Met |
| Working set ≤ 512 MB | 356–358 MB (peak 369) | 441–447 MB (peak 471) | Met, with the staging-buffer cap (below); 521–554 MB without it |
| Pool texture memory ≤ 64 MB | the cover array is 21.8 MB (64 layers × 341 KB); all textures 92 MB | all textures 113 MB | Met for the pool |
| Main thread ≤ 4 KB per 60 s scroll, no GC from it | **64 B**, in every run | 64 B | Met. The workers cause 2–4 gen0 and gen1 collections a minute and no gen2. |

The real library (NES, its biggest system at 1,198 games, all plain boxes) scrolls the same: mean 16.68 ms, p99 20.90–21.32 ms, 1 hitch per run like the controls, 0 over 2×, working set 353 MB ([m5/nas-scroll/](m5/nas-scroll/)).

## What changed on the way

Each of these was found with the bench and fixed before the final runs.

| Problem | Evidence | Fix |
|---|---|---|
| **Glyph warm-up.** Pre-rendering all of Latin-1 at every UI font size after interactive | a 150–220 ms frame and about +130 MB of working set | Printable ASCII only, at the three atlas sizes, one size per frame. Anything else is rasterised when first shown. |
| **Title atlases.** Two SubViewports sized for 64 and 48 cells | about 97 MB of texture memory and 120 MB of working set: a viewport costs about 3× its pixels | Smaller blocks (160 and 192 px) and spine strips (384×24), and the systems atlas sized to the number of systems |
| **First upload** | about 40 ms, in the first frames after interactive (as M1 found) | Done at boot, while the DB opens |
| **Pipeline warm-up** | 30–40 ms in the frame after interactive | Every template is drawn, faded into the background, in the first frame itself |
| **Texture workers.** Working out each derivative's path by reading the source file and hashing it; a new `Image` per cover | 2.2 KB allocated per cover: 8 gen0, 4 gen1 and 2 gen2 collections a minute | The grid row carries the cover's indexed size and time (`media.size_bytes`, `mtime_ms`), so the key is hashed on the stack with one string allocation and no file access; `Image`s are pooled (8). Now 2–3 gen0 and gen1 a minute, no gen2. |
| **`ConcurrentStack` in the image pool** | 283 KB allocated on the main thread per scroll (a node per push) | A plain array under a lock: back to 64 B |
| **Binding window** | 77% textured: one row of lookahead, and the half-visible row bound that frame counted as on screen | The pool's spare rows go ahead of the scroll; only rows whose centre is on screen count |
| **Glyph warm-up, one size a frame** | the first step (95 glyphs at one size) up to 39 ms | A third of ASCII a frame (9 steps) |
| **Fullscreen working set** | 521–554 MB at 2560×1440, against 453 MB for the fullscreen control | `rendering_device/staging_buffer/max_size_mb = 16` (Godot's default is 128): 441–447 MB. Uploads are at most 8 × 341 KB a frame. |

## Start-up

Where our 340 ms goes (synthetic library, a typical warm run; ms after our first code):

| Mark | ms | What |
|---|---|---|
| `main_ready` | 48 | Main scene loaded; the boot task and the model loads start |
| `config_loaded` | 125 | Settings, systems and emulators config, on the thread pool (JIT included) |
| `library_opened` | 198 | Both DBs opened and checked, e_sqlite3 loaded; 73–87 ms in the export and 86–125 ms in the editor run (the M2 carry-over) |
| `systems_loaded` | 208 | The boot query |
| `models_loaded` | 213 | The six built-in models, through Godot's threaded loader |
| `scene_built` | 276 | Grids, title atlases and MultiMeshes (the cover array was made while the DB opened) |
| `systems_grid_bound` | 289 | The systems grid bound from the DB |
| `interactive` | 342 | Its first frame drawn, pipelines included |
| `warm_up_done` | 434 | Launch controller, glyphs: spread over 13 frames (7 then) |

**The shader baker** (Godot's export option, now on) halves a cold start. With the shader and pipeline caches moved away before each run:

| Export | Our start-up, cold (3 runs) | Process start to first frame, cold |
|---|---|---|
| Baked | 1,168–1,361 ms | 2,176–2,502 ms |
| Not baked | 2,339–2,378 ms | 5,018–5,289 ms |

Warm, the two are within noise (336 ms baked against 342 and 356 ms unbaked). The baker needs a rendering device, so **exports are no longer headless**: `tools/bench-export.ps1` now exports with a window, and a headless export silently bakes nothing (a 49 KB PCK, against 2.6 MB).

**ReadyToRun** wasn't measured: it needs the `microsoft.netcore.app.crossgen2` runtime pack, which isn't in the local NuGet cache, and adding a package needs the owner's approval.

## Frame pacing

The mean frame interval is 16.68 ms (the refresh interval) in every run, but frames alternate around it, so p99 sits at about 21 ms windowed and 22 ms fullscreen. It isn't the launcher:
- the no-texture control has the same p99 (20.98–21.43 ms windowed; 22.59–22.76 ms fullscreen)
- a run with both grids hidden had p99 20.25 ms
- M3's scaffold scene measured 20.46–21.29 ms in its session

M1 measured 17.65–18.34 ms with a grid, on 27 September. Something about presentation on this machine has changed since then (the Steam client and other apps were running), and PresentMon would show what. Installing it needs the owner's approval, as M1 noted (R5).

**The fullscreen spike.** In fullscreen only, some runs have one frame of 430–480 ms, 3 frames after interactive (4 of 4 runs in one series, 1 of 3 in the next, and 0 of 4 in a series started by hand). Removing the glyph warm-up didn't change it. It's outside the scroll frames, at the time the window would switch presentation mode, and needs PresentMon to confirm.

## Render scale and upscaling

At 2560×1440 fullscreen the automatic cap renders 3D at 0.75 (1080p): 3.06 ms of GPU time. At 0.5, 1.96 ms. **FSR1 isn't available on the Mobile renderer**: Godot warns and keeps bilinear, and the two 0.5 runs measure the same (1.96 ms). So it's bilinear; FSR1 would need Forward+ ([m5/upscale-bilinear/](m5/upscale-bilinear/), [m5/upscale-fsr/](m5/upscale-fsr/)).

## Upload cap

The proposed cap of 8 uploads a frame (M1) makes no measurable difference: with the cap it bound in 3–4 frames of 3,600, and without it the 4 MB budget bound in 2. Hitches 2 and 0 with it, 0 and 1 without ([m5/cap8/](m5/cap8/), [m5/cap0/](m5/cap0/)). It stays, as insurance for faster scrolling.

## Not measured

- **Handheld mode** (undocked, 1280×800 fullscreen): the Deck was docked. Windowed 1280×800 has the same pixel count.
- **3840×2160 docked:** the display ran at 2560×1440. Changing it is a system setting. The 1080p cap gives 0.5 at 4K, which the 0.5 runs above cover for GPU time.
- **ReadyToRun:** needs a NuGet pack (above).
- **PresentMon:** needs installing (above).
- **The Godot side of net10.0:** a comparison build means changing every project's TFM on a branch. Core alone gained nothing (M2).
