# One PC big box, two templates: checks and measurements

Measured on 2 October 2026 on the development machine, windowed at 1280×800 (59.94 Hz), with nothing else running.

- Builds are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on.
- **Before** is commit `16bafee`, exported from a separate worktree to `artifacts/export-genbox-before/`. **After** is the change, exported to `artifacts/export-genbox-after/`. Both were benched in the same session.
- One warm-up and 5 benched runs per build; the table gives the medians. The JSON is in [generic-box/](generic-box/), and the captures (DOS's Aldo's Adventure on `generic_box_spine`, then on `generic_box_logo`) are in [generic-box/captures.jpg](generic-box/captures.jpg).
- The design is in [ARCHITECTURE.md](../ARCHITECTURE.md) (A7, "A logo on the spine", and the decisions log, 2026-10-02).

```powershell
# A fresh 3,000-game library (the older artifacts\synthetic-3000 predates the media folder, so its derivatives were missing):
dotnet run --project tools/synthetic-library -c ExportRelease -- "--out=$PWD\artifacts\synthetic-genbox" "--covers=$PWD\artifacts\spike-library" --games=2620 --others=20 --slots=back,spine,screenshot,logo
# Its systems.toml given [systems.ps2] game_model = "big_box" (before) or "generic_box_logo" (after):
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-genbox-<build>\OdysseyLauncher.exe -Label genbox2-<build> -AppArgs "--user-dir=$PWD\artifacts\synthetic-genbox", '--bench-scenario=scroll', '--bench-system=ps2'
```

## What changed per frame

- **Every item:** the vertex and fragment shaders read the slot state's fallback with `mod(x, 2)`, and the fragment shader has one more branch, skipped unless a spine shows a logo.
- **A spine showing a logo:** the logo is sampled once per fragment, as the spine's own art was, with a few more ALU operations to turn and fit it. No more texture layers: the logo takes the spine's channel.
- **The box:** the same 220 triangles. The chamfers moved from the `case` surface to the `cover` and `back` surfaces (one merged mesh either way).
- **CPU:** nothing per frame. The logo bit is set in the slot state when a slot resolves, as the fallback already was.

## Results

**The 60 s scroll of 2,620 PS2 games, each with a cover, back, spine and logo:** before, `big_box` showing the spine art; after, `generic_box_logo` showing the logo along the spine.

| | Before | After |
|---|---|---|
| Start-up of our code | 387 ms | 392 ms |
| Scroll p50, p95, p99 | 17.97, 20.16, 21.01 ms | 18.02, 20.18, 21.13 ms |
| Hitches, frames over 2× | 0, 0 | 0, 0 |
| GPU, render CPU | 1.58, 0.33 ms | 1.60, 0.34 ms |
| Main-thread allocation in the scroll | 96 B | 96 B |
| Grid textured | 100% | 100% |
| Uploads | 6,894 | 6,894 |
| Working set | 435 MB | 435 MB |

Within run-to-run noise: the GPU's 0.02 ms is the size of the spread between runs of one build (1.54–1.60 ms before).
