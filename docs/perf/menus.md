# Themeable menus: checks and measurements

Measured on 15 October 2026 on the development PC (Intel Core i5-11400F, 64 GB, GeForce RTX 3060), windowed at 1280×800 on a 60 Hz display, with nothing else running.

- Builds are ExportRelease on .NET 8.0.32, Mobile/D3D12, with the shader baker on.
- **Before** is commit `ca697d9`, exported to `artifacts/export-menus-before/` before the change. **After** is the change (`[ui.menu]`, A6 Menus), exported to `artifacts/export-menus-after/`. Both were benched in the same session.
- Scenario A is one warm-up and 5 benched runs. B is the same; C is one warm-up and 3 runs. The tables give the medians, and the JSON is in [menus/](menus/).
- The decision is in [ARCHITECTURE.md](../ARCHITECTURE.md) (decisions log, 2026-10-15).

```powershell
# A: the 60 s scroll of 10,000 PS2 games on Slab, for each build
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-menus-<build>\OdysseyLauncher.exe -Label menus-<build> -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll', '--theme=slab'
# B: two theme switches with the settings open: Console, then a user theme with only a menu font
#    (themes/menu-font in the user folder, a 220 KB TTF), then Slab (its colours, no font)
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-menus-<build>\OdysseyLauncher.exe -Label switch-<build> -Frames 600 -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--theme=console', '--open=settings', '--nav-script=wait,wait,wait,wait,theme,wait,wait,wait,wait,wait,wait,wait,wait,theme'
# C: as B without the font theme: Console, Slab, Console (-Runs 3)
```

## What it can cost

- **Per frame:** nothing by design. A `StyleBoxFlat` or a `Label` costs the same whatever its colour, and no per-frame code changed (A).
- **A theme switch that changes the menus' palette** sets about 20 shared resources to the new colours, then walks the menus shown once and maps each colour they copied to the same role's new one. Godot tells every control using a resource each time one of the resource's properties is set. And a style box held by the shared `Theme` makes the theme tell every control using it, so each control looks its items up again and lays out again. The colours are therefore set with signals blocked, and each resource, then the `Theme`, emits `changed` once. Both steps were measured (C):
  - Setting the colours one at a time (the first version): the menus' part of the switch, in the editor's Debug build, was 24.6 ms going to Slab and 19.1 ms back to Console.
  - Batching each resource, with the theme still notified once per style box: 5.0 ms and 0.6 ms in `Apply`. But on the export the next frames still took **30–37 ms** going to Slab and **30–31 ms** back (`palette-unbatched`).
  - The theme silent until every box has changed (the final version): `Apply` takes 3.2 ms on the export, and the switch's frame is **18–20 ms**. Coming back to the launcher's own palette, no frame is over 18 ms.
- **A switch between themes with the same menus** does nothing.
- **A menu font** is read and parsed on a worker (`FontFile.LoadDynamicFont`: 2–8 ms for the 220 KB TTF), never before `interactive`, and set in about 0.1 ms. The menus then lay out again on the next frame. Its printable ASCII at the menus' three main sizes is drawn ahead, a third of a size a frame. Other characters and sizes are rasterised when first drawn, as with the default font. A theme without a font pays none of this.
- **Memory:** a font stays in memory while its theme is active, at most 4 MB (the budget), plus its glyph atlases (0.7 MB of textures for the 242 KB test font, after the warm-up and a settings page). A replaced font is released at once (`MenuLook.Release`), not at the next full collection, and leaves nothing behind (D).

## Results

**A. The 60 s scroll on Slab** (`artifacts/synthetic`, 10,000 PS2 games).

| | Before | After |
|---|---|---|
| Start-up of our code | 353 ms | 327 ms |
| Scroll p50, p95, p99 | 16.67, 16.86, 16.95 ms | 16.67, 16.87, 16.98 ms |
| Scroll's longest frame | 20.05 ms | 19.80 ms |
| Hitches | 0 | 0 |
| GPU, render CPU | 0.19, 0.22 ms | 0.19, 0.20 ms |
| Main-thread allocation in the scroll | 96 B | 96 B |
| Working set, video memory | 375, 296 MB | 379, 297 MB |

The palette is applied once, in the warm-up after `interactive` (0.6 ms with the launcher's own colours, 3.5–4.6 ms with Slab's in the editor's Debug build, where it builds the menus' theme for the first time), so start-up isn't affected: the difference is run-to-run spread.

**B. Console → the font theme → Slab, with the settings open**, frames over 18 ms after the settings opened (frame 12: 41–48 ms in both builds, every run).

| | Before | After |
|---|---|---|
| Switch to the font theme (frame ~165, the font about 3 frames later) | none | none |
| Switch to Slab (frame ~434: the palette changes and the font goes) | none | one frame, 19.0–20.5 ms |
| Hitches (over 25 ms) | 1 (the settings opening) | 1 (the settings opening) |
| Texture memory at the end | 358 MB | 358 MB |
| Video memory at the end, each run | 436, 436, 436, 428, 436 MB | 444, 444, 436, 436, 444 MB |

The 8 MB difference in video memory is run-to-run spread, not something the font leaves behind (D). An 18.8 ms frame at about frame 277, with no switch near it, showed up in 2 of the 16 runs of the after builds (B and C, as the change was refined) and in none of the 8 before. It's under the hitch threshold and not explained.

**C. Console → Slab → Console, with the settings open** (no font theme), frames over 18 ms after the settings opened.

| | Before | Theme notified per box | After |
|---|---|---|---|
| Switch to Slab (frame ~165) | none | 35.4–37.7 ms | 18.3–19.4 ms |
| Back to Console (frame ~432) | none | 30.2–31.4 ms | none |
| Hitches | 1 | 3 | 1 |

**D. Does a used font leave memory behind?** No. B's 8 MB is the way Godot counts video memory. Measured the same day on the same builds, with `--memory-log` (one sample a second) beside `--bench`, by a script that runs the export as `bench-export.ps1` does (one warm-up, then the runs). The data is in [menus/](menus/) (`memory-*`: each run's JSON and CSV).

- **What "video memory" counts.** On D3D12 it's the allocator's heaps (`RenderingDeviceDriverD3D12::get_total_memory_used`: D3D12MA's `BlockBytes`), not the bytes in them. Texture and buffer memory are counted per resource. So video memory moves in whole heaps: every end figure in these runs, of every build and theme, is 427.9, 435.9, 443.9 or 451.9 MB (8 MB apart), with a few runs at 434.8, 439.0, 439.9 or 447.0 MB. Which heap a run ends on depends on the order its uploads happened in.
- **B again, 10 runs each.** Console → a theme → Slab with the settings open, as in B. The theme was `menu-font` (only a menu font, a 242 KB TTF) or `menu-palette` (only `background = "#202020"`). Texture memory at the end was 357.7 MB in all 30 runs, and buffer memory 17.0–17.2 MB.

  | Build, middle theme | Video memory at the end, each run | Median |
  |---|---|---|
  | After, the font | 428, 444, 436, 444, 435, 452, 436, 436, 444, 436 MB | 436 MB |
  | After, the palette | 444, 444, 436, 444, 436, 436, 436, 444, 439, 444 MB | 441 MB |
  | Before (ignores `[ui.menu]`), the font theme | 444, 447, 436, 444, 436, 444, 452, 444, 440, 444 MB | 444 MB |

  The font run's median is the lowest of the three, and the before build, which never loads the font, spans the same heaps.
- **Forty switches.** To make a leak per font add up, two user themes with Console's and Slab's ids replaced the built-in ones, so the `theme` step went back and forth between two themes on Memory Card's models alone. They differed only in their menus: a font in one (`alternate-font`), `background = "#202020"` in one (`alternate-palette`), or nothing (`alternate-none`). Each run made 40 switches, one a second with the settings open, so 20 fonts were loaded, used and released (3,000 frames, 3 runs each).

  | Themes | Video memory, before the first switch → the end | Texture memory during the run |
  |---|---|---|
  | No difference | 292.7 → 299.8 MB (+7.1, +7.1, +7.1) | 253.6 MB throughout |
  | A palette | 292.7 → 302.5 MB (+8.2, +10.5, +9.8) | 253.6 MB throughout |
  | A font | 293.1 → 300.7 MB (+7.6 in all 3) | 254.3 MB with the font, 253.6 MB after each release |

  The font's glyph textures (0.7 MB) are freed at every release. The 7–10 MB rise in video memory comes from the switches themselves, with or without a font (it's in the "no difference" runs too). So there was nothing to fix.

```powershell
# D: as B, with --memory-log=<run>.csv and themes/menu-font or themes/menu-palette in the user folder, 10 runs each
'--theme=console', '--open=settings', '--nav-script=wait,wait,wait,wait,theme,wait,wait,wait,wait,wait,wait,wait,wait,theme'
# D, forty switches: themes/console and themes/slab in the user folder (the two alternating themes), 3,000 frames
'--theme=console', '--open=settings', "--nav-script=wait,wait,wait,wait,$((1..40 | ForEach-Object { 'theme,wait' }) -join ',')"
```

## Captures

These were taken with `--fixed-fps 60` at 1280×800, compared ignoring the clock's corner.

- **Console's menus are pixel-identical before and after:** `--open=settings`, `power`, `keyboard`, `confirm`, `folder-picker`, `progress` (the job cards), `details`, and a system's details. Only the animated 3D models behind and beside them differ, by as much as two runs of the same build do.
- **A switch from Console to Slab and back, with the settings open,** gives Console's menus again within 2/255 inside the panel (the grid behind the translucent panel).
- **Switching to Slab with the settings open** matches booting on Slab, apart from the Theme row's own text, which is read when the page opens.
- **A font theme's menus** use its font from boot, and from a switch with the settings open.
