# Theme motion: checks and measurements

Measured on 15 October 2026 on the development PC (Intel Core i5-11400F, 64 GB, GeForce RTX 3060), windowed at 1280×800 on a 60 Hz display, with nothing else running.

- Builds are ExportRelease on .NET 8.0.32, Mobile/D3D12, with the shader baker on (both PCKs 2.1 MB).
- **Before** is commit `c3e2bc2`, exported to `artifacts/export-motion-before/` before the change. **After** is the change (`[motion]`: `focus_sway`, `idle_bob`; A6 Motion), exported to `artifacts/export-motion-after/`. Both were benched in the same session, one after the other.
- Each scenario is one warm-up and 5 benched runs (B: 10). The tables give the medians, and the JSON is in [theme-motion/](theme-motion/).
- The decision is in [ARCHITECTURE.md](../ARCHITECTURE.md) (decisions log, 2026-10-15).

```powershell
# A: the 60 s scroll of 10,000 PS2 games on Slab (start-up, then navigation), for each build
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-motion-<build>\OdysseyLauncher.exe -Label motion-scroll-<build> -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll', '--theme=slab'
# B: start-up, then 600 frames of the systems grid at rest (every card bobbing, the focused one swaying), 10 runs
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-motion-<build>\OdysseyLauncher.exe -Label motion-idle-<build> -Runs 10 -Frames 600 -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--theme=slab'
# C: the scroll on the base theme alone, and on a user theme that is only [motion] focus_sway = 2, idle_bob = 3
#    (themes/motion-lively in the user folder, removed afterwards), so the same look with every material's idle_bob set
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-motion-<build>\OdysseyLauncher.exe -Label motion-theme-<theme> -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll', '--theme=<memory-card|motion-lively>'
```

## What it can cost

- **Per frame:** the sway is one more multiply in `ItemGrid.FocusTransform`, which already ran each frame for the focused item. The bob reads a uniform (`idle_bob`) instead of a constant in the item shader's vertex stage: no shader variant, no branch, no new per-frame code.
- **Start-up:** two more keys to look for in `theme.toml` (nothing when the theme has no `[motion]`). A grid sets `idle_bob` on its materials only when the theme's isn't 1, so the shipped themes set nothing.
- **A theme switch:** `SetMotion` sets one parameter on each of a grid's few materials, and only when the bob changes.

## Results

**A. The 60 s scroll on Slab** (`artifacts/synthetic`, 10,000 PS2 games).

| | Before | After |
|---|---|---|
| Start-up of our code | 349 ms (317–351) | 342 ms (300–349) |
| Scroll p50, p95, p99 | 16.67, 16.87, 16.97 ms | 16.67, 16.87, 16.97 ms |
| Scroll's longest frame, per run | 19.3–22.2 ms | 17.2–19.8 ms |
| Hitches | 0 | 0 |
| GPU, render CPU | 0.19, 0.20 ms | 0.19, 0.19 ms |
| Main-thread allocation in the scroll | 96 B | 96 B |
| Working set, video memory | 383, 297 MB | 385, 297 MB |

**B. Start-up and the systems grid at rest on Slab** (10 runs).

| | Before | After |
|---|---|---|
| Start-up of our code | 315 ms (304–324) | 314 ms (305–337) |
| Frames p50, p95, p99 | 16.66, 16.97, 17.07 ms | 16.67, 16.95, 17.06 ms |
| Longest frame, per run | 17.1–17.7 ms | 17.2–17.9 ms |
| Hitches | 0 | 0 |
| GPU, render CPU | 0.19, 0.22 ms | 0.19, 0.22 ms |
| Working set, video memory | 348, 298 MB | 347, 298 MB |

**C. The 60 s scroll on the base theme, with and without `[motion]`** (two rounds of 5 runs; the second added the before build).

| | Before, base theme | After, base theme | After, `[motion]` 2 and 3 |
|---|---|---|---|
| Start-up of our code (round 1; round 2) | –; 341 ms | 337; 301 ms | 343; 330 ms |
| Scroll p99 (round 1; round 2) | –; 16.97 ms | 16.97; 16.98 ms | 16.98; 16.98 ms |
| GPU | 0.19 ms | 0.19 ms | 0.19 ms |
| Runs with a hitch (one frame, 25–31 ms) | 1 of 5 | 3 of 10 | 5 of 10 |
| Main-thread allocation in the scroll | 96 B | 96 B | 64–96 B |
| Video memory | 293 MB | 293 MB | 293 MB |

Every hitch in C is a single frame between frames 1,420 and 1,670 of the scroll, in all three columns, including the build before the change. Every base-theme run (all three columns) has a full (gen 2) collection during the scroll, and no Slab run has one: that pause is the base theme's, not the motion's, and is outside this change. 3 of 10 against 5 of 10 isn't a difference at this sample size (Fisher's exact test, p ≈ 0.65), and the frame times, GPU time and allocation are the same.

## Checks

- Captures of the systems grid at frames 60 and 100 (`--fixed-fps 60`): with `focus_sway = 0` and `idle_bob = 0`, no pixel changes between the two frames, and the focused card faces the camera; with 2 and 3, about twice as many pixels change as with the launcher's own motion (57,487 against 28,503).
- Core's tests (960) pass, including four new ones for `[motion]` (defaults, values, the base's values, mistakes).
