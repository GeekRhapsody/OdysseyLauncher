# M1 performance spike: results

The spike's acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m1-performance-spike), and the design questions are in [ARCHITECTURE.md](../ARCHITECTURE.md#a3-performance-design) (A3).

## Machine

- **Hardware:** Steam Deck, LCD model.
  - CPU: AMD Custom APU 0405, with 4 cores and 8 threads (Zen 2).
  - GPU: AMD Custom GPU 0405 (RDNA2, 8 CUs), driver 32.0.11002.3007.
  - Memory: 16 GB shared.
- **OS:** Windows 11 Pro 10.0.26200.
- **Display:** docked to a 3840×2160 display at 59.94 Hz.
- **Software:** Godot 4.7.2.stable.mono. Exports are self-contained and bundle .NET 8.0.31.

## How to reproduce

Every configuration runs one warm-up, then 5 measured runs of 120 frames each, windowed at 1280×800. The warm-up absorbs the cold shader cache after an export. Reports go to `artifacts/bench/` (local and gitignored).

```powershell
.\tools\bench-export.ps1 -Label fplus-d3d12
.\tools\bench-export.ps1 -SkipExport -Label fplus-vulkan -EngineArgs '--rendering-driver', 'vulkan'
.\tools\bench-export.ps1 -SkipExport -Label mobile-d3d12 -EngineArgs '--rendering-method', 'mobile'
.\tools\bench-export.ps1 -SkipExport -Label mobile-vulkan -EngineArgs '--rendering-method', 'mobile', '--rendering-driver', 'vulkan'
.\tools\bench-export.ps1 -SkipExport -Label compat-gl -EngineArgs '--rendering-method', 'gl_compatibility'
```

## Preliminary: scaffold scene (2026-09-27)

This is the placeholder scene: the gradient, three lights and one box. It measures fixed costs only, not the grid. The start-up target covers **our code**, which starts at the first autoload's `_EnterTree` (`app_startup_ms`).

| Renderer / driver | Our code (ms) | Before our code (ms) | Process → interactive (ms) | Mean frame (ms) | p99 (ms) | Hitches (5 × 120 frames) | GPU (ms) |
|---|---|---|---|---|---|---|---|
| Forward+ / D3D12 | 126.5 | 1186.7 | 1313.2 | 16.51 | 18.01 | 2 | 1.07 |
| Forward+ / Vulkan | 142.7 | 1373.1 | 1511.2 | 16.47 | 18.54 | 0 | 0.74 |
| Mobile / D3D12 | 122.4 | 1044.4 | 1166.8 | 16.56 | 18.09 | 4 | 0.73 |
| Mobile / Vulkan | 151.4 | 1213.3 | 1377.6 | 16.55 | 18.54 | 4 | 0.57 |
| Compatibility / OpenGL 3 | 126.5 | 962.2 | 1083.4 | 16.67 | 18.49 | 0 | 0.58 |

All figures are medians over the 5 runs, except hitches, which are totals. A second Forward+/D3D12 set, on a rebuilt export, gave 136.6 ms for our code, 1310.3 ms before our code and 2 hitches. So the engine phase varies by roughly ±100 ms from one set to the next.

**Observations**
- **Our code** takes 122–151 ms in every configuration, which leaves a lot of headroom under the 1 s target. The real test is the 10,000-game grid.
- **Engine and .NET start-up** is outside the target. Compatibility is fastest (about 0.96 s) and Vulkan is slowest. D3D12 beats Vulkan for both RenderingDevice renderers.
- **Frame pacing** is locked to 59.94 Hz everywhere, with a mean of 16.5–16.7 ms. The occasional hitch (26–30 ms) lands in the first second or so of these short runs. The `scroll` scenario will show whether hitches persist.
- **GPU time** is 0.6–1.1 ms per frame at 1280×800 for this trivial scene.
- **Godot's `--benchmark-file`** writes nothing from release templates. An attempt with the editor binary didn't exit and was stopped. It isn't needed now that engine start-up is outside the target.

**Not measured yet:**
- handheld mode, which needs the Deck undocked
- 4K output
- ReadyToRun and the shader baker
- the grid prototype and its scenarios
