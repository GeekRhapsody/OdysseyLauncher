# The grid with labels: checks and measurements

Measured on 2 November 2026 on the development machine, windowed at 1280×800 (60 Hz), with nothing else running.

- Builds are ExportRelease on .NET 8.0.32, Mobile/D3D12, with the shader baker on.
- **Before** is commit `7c3ff41`, exported from a worktree to `artifacts/export-labels-before/`. **After** is the change, exported to `artifacts/export-labels-after/`. Every series ran in one session.
- One warm-up and 5 benched runs for the grid before and after, 3 for the grid with labels; the tables give each run's range or the medians. The JSON is in [grid-labels/](grid-labels/), and the captures (the systems in Slab, Classic View and Console; Mega Drive's and SNES's games; the transition into a system; a game inspected in front of the labels; the Layout page's Systems view) are in [grid-labels/captures.jpg](grid-labels/captures.jpg).
- The design is in [ARCHITECTURE.md](../ARCHITECTURE.md) (A1 Grid and Screens, A5 `[display]`, and the decisions log, 2026-11-02).

```powershell
# artifacts\synthetic-gen: 10,000 PS2 games with covers, from tools/synthetic-library.
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-labels-<build>\OdysseyLauncher.exe -Label labels-<series> -AppArgs "--user-dir=$PWD\artifacts\synthetic-gen", '--bench-scenario=scroll', '--bench-system=ps2', '--layout=grid/grid' # or '--layout=grid_with_labels/grid_with_labels'
```

## What changed per frame

- **The grid (the default):** `ItemGrid.UpdateLabels` returns at once, and each `GridLabels.Update` reads two fields and returns. A few counters are incremented where rows bind and the focus moves.
- **The grid with labels:** in `Tick`, every bound cell's label point is worked out (a projection by division, no call into Godot) and compared with the last; in a frame where one moved (scrolling, the focus easing, a transition), the overlay sets those labels' positions and scales, and a label's text only when its cell is bound to another item. At rest, nothing is set.
- **Memory:** a `Label` per pool cell (64 for the games, the systems' pool for the systems), made the first time a grid shows labels; no texture of their own (the font's glyph cache).

## Results

**The 60 s scroll of 10,000 PS2 games** (1,999 rows of 5 in the grid; 1,666 rows of 6 with labels, since a row's labels take room from its items, so a sixth column fits).

| | Before, grid | After, grid | After, grid with labels |
|---|---|---|---|
| Start-up of our code | 304 ms | 300 ms | 303 ms |
| Scroll p50, p95, p99 (medians) | 16.66, 16.89, 17.17 ms | 16.67, 16.90, 17.15 ms | 16.66, 16.92, 17.09 ms |
| Scroll p99, each run | 17.06–17.21 ms | 17.13–17.19 ms | 17.07–17.11 ms |
| Scroll hitches, frames over 2× | 0, 0 in every run | 0, 0 in every run | 0, 0, 1; none over 2× |
| GPU, render CPU | 0.19, 0.167 ms | 0.19, 0.167 ms | 0.19, 0.224 ms |
| Main-thread allocation in the scroll | 96 B | 96 B | 96 B |
| Grid textured (mean) | 96.2–97.1% | 96.6–97.4% | 98.9–99.2% |
| Texture memory | 275.7 MB | 275.7 MB | 276.2 MB |
| Working set | 371–375 MB | 371–372 MB | 376–377 MB |

- **The grid, before and after:** the same. Percentiles, GPU and render CPU time, allocation (96 B, the bench's own), texturing and memory match, and neither series had a hitch in the scroll.
- **The grid with labels** holds the same pacing. Its render CPU time is 0.06 ms more (the labels' canvas items), its texture memory 0.5 MB more (the glyphs) and its working set about 5 MB more. Its one scroll hitch, a 25 ms frame 1.2 s before the end of the third run, falls where the grid's runs have their longest frames too (23 ms in the first after run).
- **The first frame:** each run with labels has a hitch outside the scroll, its first frame after interactive (28.0–29.0 ms; 17.5 ms in the grid), when the labels are first made, laid out and their glyphs drawn (17 KB more allocated, once). It happens once a session, the first time a grid with labels is shown.
