# Boxes shaped by the art: checks and measurements

Measured on 1 October 2026 on the baseline Steam Deck (the machine in [m1-spike.md](m1-spike.md#machine)), docked, windowed at 1280×800.

- Builds are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on.
- **Before** is commit `4dfdf89`, exported to `artifacts/export-before/` before any of the change was written. **After** is the change, exported to `artifacts/export-after/`. Both were benched in the same session, with nothing else running.
- Every scenario is one warm-up and 5 benched runs, and the tables give the medians. The JSON is in [box-shapes/](box-shapes/), and the captures are in [box-shapes/captures.jpg](box-shapes/captures.jpg).
- The design is in [ARCHITECTURE.md](../ARCHITECTURE.md) (A7, "Boxes shaped by the art").

```powershell
$syn = "$PWD\artifacts\synthetic"; $mod = "$PWD\artifacts\synthetic-3000-models"
# For each build (-Executable artifacts\export-before\... or ...\export-after\..., -SkipExport, -Runs 5):
.\tools\bench-export.ps1 -Frames 300 -Label <build>-boot -AppArgs "--user-dir=$syn"
.\tools\bench-export.ps1 -Label <build>-scroll -AppArgs "--user-dir=$syn", '--bench-scenario=scroll'
.\tools\bench-export.ps1 -Label <build>-control -AppArgs "--user-dir=$syn", '--bench-scenario=scroll', '--no-textures'
.\tools\bench-export.ps1 -Label <build>-models -AppArgs "--user-dir=$mod", '--bench-scenario=scroll'
# C: the synthetic library's systems.toml given [systems.ps2] game_model = "cartridge_box" (before) or "big_box" (after)
.\tools\bench-export.ps1 -Label <build>-shape -AppArgs "--user-dir=$syn", '--bench-scenario=scroll'
```

## What changed per frame

- **Every item:** one more `texelFetch` per vertex in the item shader (the cell's shape texel), and a branch that's skipped when the texel is zero. Every model but a shaped box has a zero texel.
- **A shaped box:** its vertices move by the cell's growth, and its cover, back and spine faces take new aspects. That's three adds and two more fetches per vertex.
- **CPU:** nothing per frame. Two texels per cell are written when a cell binds or its media changes, in the same `Image` the slot states already use, so nothing is allocated.

## Results

**A. The 60 s scroll of 10,000 PS2 games (fixed DVD cases):** what the extra fetch costs every existing box.

| | Before | After |
|---|---|---|
| Start-up of our code | 587 ms | 488 ms |
| Scroll p50, p95, p99 | 16.82, 17.15, 18.41 ms | 16.83, 17.47, 18.12 ms |
| Hitches, frames over 2× | 2, 1 | 2, 1 |
| GPU, render CPU | 1.36, 0.30 ms | 1.26, 0.27 ms |
| Main-thread allocation in the scroll | 64 B | 64 B |
| Grid textured | 99.45% | 99.44% |
| Working set | 439 MB | 437 MB |

**A, control: the same scroll with `--no-textures`.**

| | Before | After |
|---|---|---|
| Scroll p50, p95, p99 | 16.81, 17.55, 18.05 ms | 16.83, 17.47, 18.11 ms |
| Hitches, frames over 2× | 0, 0 | 0, 0 |
| GPU, render CPU | 1.29, 0.29 ms | 1.30, 0.30 ms |

**B. The 60 s scroll of 3,000 games with 300 per-game models** (`synthetic-3000-models`): per-game models are drawn on nodes with the same shader, with a zero shape texel.

| | Before | After |
|---|---|---|
| Scroll p50, p95, p99 | 16.81, 17.53, 18.25 ms | 16.82, 17.47, 18.07 ms |
| Hitches, frames over 2× | 4, 1 | 2, 0 |
| GPU, render CPU | 1.39, 0.31 ms | 1.42, 0.31 ms |
| Main-thread allocation in the scroll | 64 B | 64 B |
| Working set | 516 MB | 517 MB |

**C. 10,000 PS2 games on a cardboard box:** before, the fixed `cartridge_box`; after, `big_box` shaped by each game's art. Both boxes have 220 triangles. The synthetic covers are square, so every box after is reshaped, to a square front with the rest proportions' depth (there are no spines).

| | Before (`cartridge_box`) | After (`big_box`, shaped) |
|---|---|---|
| Scroll p50, p95, p99 | 16.83, 17.57, 18.12 ms | 16.84, 17.43, 18.10 ms |
| Hitches, frames over 2× | 1, 0 | 2, 0 |
| GPU, render CPU | 1.24, 0.27 ms | 1.23, 0.27 ms |
| Main-thread allocation in the scroll | 64 B | 64 B |
| Grid textured | 99.42% | 99.45% |

**D. Boot** (the systems grid, 300 frames):

| | Before | After |
|---|---|---|
| Start-up of our code | 407 ms | 389 ms |
| p50, p95, p99 | 16.84, 17.47, 18.38 ms | 16.84, 17.44, 18.60 ms |
| Hitches, frames over 2× | 1, 0 | 0, 0 |
| GPU | 1.36 ms | 1.38 ms |
| Working set | 445 MB | 441 MB |

**Every difference is within run-to-run noise.** Frame-time percentiles move by at most 0.3 ms in either direction. GPU time moves by less than 0.1 ms. Hitches are at the environment's usual 0–4 a run (A3), with the same counts in the no-texture control. Main-thread allocation and memory are unchanged. Start-up differs by tens of milliseconds between sessions anyway (A3), and the after runs happened to be faster.

**Binding a list.** A list that uses a shaped template is walked once when it's bound, for its widest and tallest box: 2.6–2.8 ms for 10,000 games on the main thread. That was measured in the editor build with Debug assemblies, so the export's cost is no more. Lists without a shaped template skip the walk.

## What stays the same

**Captures before and after.** These were taken with the editor build at frame 400, with `--fixed-fps 60 --no-overlay`, and compared pixel for pixel:
- the systems grid
- Game Boy, PS2 and PlayStation lists with the built-in theme
- Game Boy with the owner's `console` theme
- PS2 with 300 per-game models

**The only pixels that differ are on the focused item**, whose sway phase depends on when loading finished, so they differ between two runs of the same build too. Every other item is identical, in every capture. Crops of the focused Game Boy box show the same box at a slightly different angle.

## The shapes

These were checked on a test library of eight DOS games, with generated art of known proportions. Each image has a frame and a yellow quarter-circle in each corner, so a crop shows:

| Game | Cover | Spine |
|---|---|---|
| Alpha Portrait | 700×900 | 0.16 |
| Bravo Tall Deep | 600×900 | 0.30 |
| Charlie Square | 800×800 | 0.10 |
| Delta Landscape | 960×720 | 0.20 |
| Echo No Spine | 700×880 | none |
| Foxtrot No Art | none | none |
| Golf Wide | 1000×600 | 0.15 |
| Hotel Thin | 700×950 | 0.05 |

- **Fronts:** every front shows its whole image, with all four corners. Each box has its own proportions.
- **Standing:** landscape boxes stand on the row's floor.
- **Cells:** the columns fit the widest box (Golf, 1.67:1) without overlapping.
- **No art:** Foxtrot keeps the rest shape, with its generated title card.
- **Depths:** these were checked with the focused box turned about 57° (a temporary shader change for the capture, since removed). Each depth follows its spine, and each spine shows whole. Echo, with no spine, keeps the rest depth and a generated spine.
