# Layouts (grid, carousel, one at a time, list): checks and measurements

Measured on 2 October 2026 on the development machine, windowed at 1280×800 (59.94 Hz), with nothing else running.

- Builds are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on.
- **Before** is commit `0776701`, exported to `artifacts/export-layout-before/`. **After** is the change, exported to `artifacts/export-layout-after/`. Every series ran in one session.
- One warm-up and 5 benched runs per before and after series, 3 for each new layout; the tables give the medians. The JSON is in [layouts/](layouts/), and the captures (the systems as a 3 × 2 grid, a carousel and one at a time; PS2's games as a 7 × 4 grid, a carousel and a list; the Layout page, and a system's own columns and rows) are in [layouts/captures.jpg](layouts/captures.jpg).
- The design is in [ARCHITECTURE.md](../ARCHITECTURE.md) (A1 Grid and Screens, A5 `[display]`, and the decisions log, 2026-10-02).

```powershell
# artifacts\synthetic-genbox: 2,620 PS2 games, each with a cover, back, spine, screenshot and logo, on dvd_case.
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-layout-<build>\OdysseyLauncher.exe -Label layout2-<series> -AppArgs "--user-dir=$PWD\artifacts\synthetic-genbox", '--bench-scenario=scroll', '--bench-system=ps2' [, '--layout=grid/carousel' | '--layout=grid/list']
```

`artifacts\synthetic` (the 10,000-game library the scroll bench usually takes) was benched first, and streamed nothing in either build: its media rows predate the media folder (migration 0004 marks every system for a rescan, which benches don't do). Its frame times were the same before and after (scroll p99 20.73–20.96 ms before, 20.71–21.18 ms after; 96 B allocated), but with no uploads it says nothing about streaming, so the numbers below are from `synthetic-genbox`.

## What changed per frame

- **The grid (the default):** nothing new runs. `UpdateCurve` returns at once unless the layout is a carousel; the focused item's transform is composed with its resting one (a basis product instead of a scale), and its pull towards the middle works from the root's position across (0 for a grid). Binding computes a cell's place in one function for every layout.
- **A carousel:** while it scrolls, every bound cell (about a dozen) takes its place on the curve again: a transform each, nothing allocated. At rest, nothing.
- **One at a time and the list:** one item on screen (two while one slides in), so fewer than the grid's; the list's titles are 2D labels in the overlay, re-bound only as a title scrolls into view, their positions set each frame the scroll moves (about 20 labels).
- **Memory:** the same pool of 64 cells and the same texture arrays in every layout.

## Results

**The 60 s scroll of 2,620 PS2 games** (523 rows in the grid; 2,619 places in a carousel or the list, so those move about 44 games a second, five times the grid's games per second).

| | Before, grid | After, grid | After, carousel | After, list |
|---|---|---|---|---|
| Start-up of our code | 560 ms (532–581) | 591 ms (516–638) | 579 ms | 556 ms |
| Scroll p50, p95, p99 | 17.89, 19.41, 20.43 ms | 17.90, 19.21, 19.62 ms | 17.93, 19.72, 20.56 ms | 17.91, 19.50, 20.46 ms |
| Scroll p99, each run | 19.62–20.55 ms | 19.58–20.45 ms | 20.07–20.82 ms | 20.23–20.77 ms |
| Hitches, each run | 1, 2, 1, 5, 4 | 2, 1, 1, 3, 2 | 0, 3, 0 | 0, 1, 1 |
| Frames over 2×, each run | 0, 0, 0, 1, 0 | 1, 0, 1, 1, 2 | 0, 2, 0 | 0, 1, 0 |
| GPU, render CPU | 1.33, 0.31 ms | 1.32, 0.31 ms | 0.89, 0.24 ms | 0.86, 0.30 ms |
| Main-thread allocation in the scroll | 96 B | 96 B | 96 B | 96 B |
| Grid textured (mean, worst frame) | 100%, 100% | 100%, 100% | 100%, 94.4% | 99.84%, 0% |
| Texture memory | 124.6 MB | 124.6 MB | 124.6 MB | 125.0 MB |
| Working set | 441 MB | 444 MB | 441 MB | 441 MB |

- **The grid, before and after:** the same. Scroll percentiles, GPU and render CPU time, allocation (96 B, the bench's own), texturing and memory match; each run's p99 falls in the same range, and the start-up medians are inside each other's spread.
- **Frames over 2×:** the after series had five single frames of 34–44 ms (one or two in four runs), the before series one; they fall on unrelated frames in every run, with the same garbage collections and allocation, and the before series had more hitches. More series follow below.
- **The carousel and the list** hold the same frame pacing and spend a third less GPU time than the grid (fewer items on screen). The list's worst frame shows its one item untextured: at 44 games a second, a game whose cover hasn't uploaded yet is sometimes the only one on screen, for a frame or two; 99.84% of its frames show their art.

## The frames over 2×

Three more grid series ran after those, in this order: after, before (the opposite order to the first pair), then a variant of the after build without the list of titles in the scene (`_root.AddChild(List)` left out), and after again. JSON in `layouts/after-2`, `before-2`, `after-without-list` and `after-3`.

| | Before (2) | After (2) | After without the list | After (3) |
|---|---|---|---|---|
| Scroll p50, p95, p99 | 17.89, 19.58, 20.46 ms | 17.91, 19.54, 20.43 ms | 17.92, 19.55, 20.40 ms | 17.93, 19.55, 20.40 ms |
| Hitches, each run | 2, 1, 0, 0, 0 | 2, 2, 3, 0, 1 | 5, 1, 1, 2, 2 | 1, 1, 3, 0, 1 |
| Frames over 2×, each run | 0, 0, 0, 0, 0 | 1, 1, 2, 0, 0 | 1, 0, 0, 0, 1 | 0, 0, 1, 0, 0 |
| Longest frame, each run | 29.8, 25.2, 22.6, 24.8, 25.0 ms | 37.2, 38.3, 40.7, 23.1, 31.2 ms | 36.7, 28.0, 27.1, 30.8, 38.6 ms | 33.3, 33.0, 37.9, 23.4, 26.2 ms |
| GPU | 1.35 ms | 1.35 ms | 1.37 ms | 1.36 ms |
| Main-thread allocation | 96 B | 96 B | 96 B | 96 B |

- The percentiles, GPU time and allocation are the same in every series. Each frame over 2× is one frame on its own, at a different place in every run, never in the same run twice at one place.
- **Not explained.** Over all the grid series, the after build had 10 frames over 2× in 15 runs and the before build 1 in 10. Leaving the list of titles out didn't remove them, and the last after series (1 in 5) was as clean as the first before series. Nothing the grid does per frame is new (above), so this reads as the session's noise, the periodic present delay A3 describes, but the counts lean the after build's way, and it's worth one more paired session (or PresentMon, still awaiting approval) before it's ruled out.
