# The arcade cabinet, and logos drawn whole: checks and measurements

Measured on 2 October 2026 on the development machine, windowed at 1280×800 (59.94 Hz), with nothing else running.

- Builds are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on.
- **Before** is commit `2953e8a`, exported to `artifacts/export-arcade-before/`. **After** is the change, exported to `artifacts/export-arcade-after/`. All three series ran in one session.
- One warm-up and 5 benched runs per series; the table gives the medians, and ranges where the runs spread. The JSON is in [arcade-cabinet/](arcade-cabinet/), and the captures (the arcade grid on the owner's scraped art, focused on 3x3 Puzzle; then games with no art: a printed title on the marquee and the switched-off screen) are in [arcade-cabinet/captures.jpg](arcade-cabinet/captures.jpg).
- The design is in [ARCHITECTURE.md](../ARCHITECTURE.md) (A7, "The arcade cabinet" and "A logo drawn whole", and the decisions log, 2026-10-02).

```powershell
# artifacts\synthetic-genbox (2,620 PS2 games, each with a cover, back, spine, screenshot and logo), its systems.toml given
# [systems.ps2] game_model = "generic_box_logo" (before and after), then "arcade_cabinet" (after):
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-arcade-<build>\OdysseyLauncher.exe -Label arcade-<series> -AppArgs "--user-dir=$PWD\artifacts\synthetic-genbox", '--bench-scenario=scroll', '--bench-system=ps2'
```

## What changed per frame

- **Every item:** the vertex shader's test for working out the dominant colour has one more comparison. The fragment shader's logo branch is still skipped unless a slot shows a logo; inside it, an upright logo costs the same as a spine's.
- **A slot showing a logo:** drawn whole, as a spine's already was: one sample, no more layers.
- **An arcade game:** 1,402 triangles instead of a box's 220, two slots (the screen and the marquee) and the case's palette texture.
- **CPU:** nothing per frame. The logo bit is set when a slot resolves, as before.
- **Memory:** the games grid's texture arrays have a layer per pool cell for every slot some template in the theme uses (`SlotLayout`), so the cabinet's `label` and `screenshot` add two 256² channels to every games grid, arcade or not: 16 MB of texture memory in these runs. The sample Retro TV theme already did the same.

## Results

**The 60 s scroll of 2,620 PS2 games:** before and after on `generic_box_logo` (the logo along the spine), then after on `arcade_cabinet` (the screenshot on the screen, the logo on the marquee).

| | Before, box | After, box | After, cabinet |
|---|---|---|---|
| Start-up of our code | 563 ms | 613 ms | 526 ms |
| Scroll p50, p95, p99 | 17.97, 19.38, 20.15 ms | 18.00, 19.89, 20.83 ms | 18.25, 20.48, 21.32 ms |
| Scroll p99, each run | 19.72–20.96 ms | 19.82–20.92 ms | 21.15–21.54 ms |
| Hitches, each run | 4, 3, 1, 1, 2 | 2, 2, 2, 0, 1 | 0, 1, 0, 2, 4 |
| GPU, render CPU | 1.60, 0.31 ms | 1.63, 0.31 ms | 2.38, 0.31 ms |
| Main-thread allocation in the scroll | 96 B | 96 B | 96 B |
| Grid textured | 100% | 100% | 100% |
| Texture memory | 108.6 MB | 124.6 MB | 124.6 MB |
| Working set | 439 MB | 457 MB | 456 MB |

- **The box, before and after:** the same within the session's noise. Each run's scroll p99 falls in the same range, and the start-up medians are inside each other's spread (459–996 ms before, 538–686 ms after). This session had more hitches than the generic box's (0 there), in both builds alike.
- **The cabinet:** 0.75 ms more GPU time for 6× the triangles, with the frame still inside the refresh interval; nothing more on the CPU.
- **Texture memory** is the two extra channels (above), in both after series.
