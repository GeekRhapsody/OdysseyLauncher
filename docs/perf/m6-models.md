# M6 part 2, user models, clips and the sample theme: measurements

Measured on 30 September 2026 on the baseline Steam Deck (the machine in [m1-spike.md](m1-spike.md#machine)), docked. Godot reported the display as 2560×1440 at 59.94 Hz, so "fullscreen" means 2560×1440 (3D at 0.75, the 1080p cap).

- Every build is ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on, and windowed at 1280×800 unless a row says otherwise.
- "Before" is part 1's commit (`32989ab`), exported from a worktree and benched in the same session.
- The bench JSON is in [m6/part2/](m6/part2/), and the captures are in [m6/part2/captures.jpg](m6/part2/captures.jpg).
- The brief and the acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m6-theming-and-custom-models).

## Libraries

| | How it's made |
|---|---|
| Plain | Part 1's 3,000-game library (`tools/synthetic-library --games=2620 --others=20 --slots=back,spine,screenshot,logo`): the PS2 grid is 524 rows of 5, with cover, back and spine streaming. |
| **300 per-game models** | The same, plus `--models=300`: every ninth PS2 game has a model of its own in `ConfigDir/models/games/ps2/`. Each is a figure turned on a lathe, 984 triangles, on a plinth whose front is a `cover` slot; every third has a 128² texture of its own. They're spread through the list, so a scroll passes all 300. |
| Retro TV | The sample theme (`samples/themes/retro-tv/`), a user theme copied into the models library's `themes/`. Its game template is a CRT (screenshot and label slots, streamed at 256²; `focused` and `launch` clips), and its system model has an `idle` clip. |

```powershell
dotnet run --project tools/synthetic-library -c ExportRelease -- "--out=$PWD\artifacts\synthetic-3000-models" "--covers=$PWD\artifacts\spike-library" --games=2620 --others=20 --slots=back,spine,screenshot,logo --models=300
Copy-Item -Recurse samples\themes\retro-tv artifacts\synthetic-3000-models\themes\
$m = "$PWD\artifacts\synthetic-3000-models"
.\tools\bench-export.ps1 -Runs 3 -Label commit-models-scroll -AppArgs "--user-dir=$m", '--bench-scenario=scroll'
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Label commit-models-control -AppArgs "--user-dir=$m", '--bench-scenario=scroll', '--no-textures'
.\tools\bench-export.ps1 -SkipExport -Runs 2 -Label commit-retro-scroll -AppArgs "--user-dir=$m", '--theme=retro-tv', '--bench-scenario=scroll'
.\tools\bench-export.ps1 -SkipExport -Runs 2 -Fullscreen -Label commit-models-fs -AppArgs "--user-dir=$m", '--bench-scenario=scroll'
```

The scroll bench now also waits, for up to 30 s, until the list's per-game models have loaded before it starts scrolling. The scroll measures the grid, not the loading.

## Results against the targets

The committed build, with 300 per-game models on the PS2 grid:

| Target (A3) | Before (part 1: a MultiMesh per model) | Committed (each model on its cell's node) | Verdict |
|---|---|---|---|
| Our start-up < 1 s, warm | 339 ms median (328–352), plain library | **376 ms** median (355–469) | Met. +37 ms, which is JIT (see [Start-up](#start-up)) |
| p99 ≤ 1.1× refresh (18.35 ms) | 21.20–21.64 ms | 19.46–20.97 ms; control 20.72–20.80 | **Not met, and not ours**, as in M5 and part 1: the no-texture control is the same |
| Hitches ≤ the control's | 1, 1 | **0, 0, 1**, against the control's 0, 0, 2 | Met |
| 0 frames over 2× refresh | 0, 0 | **0** in every run | Met |
| 0 hitches in fullscreen | — | 1, 1 (0 over 2×) | Not met, as in M5 and part 1 (their controls have them too) |
| Visible grid textured ≤ 100 ms | 13.7–18.1 ms | 14.5–18.5 ms | Met |
| ≥ 99% of on-screen media textured while scrolling | 100% (lowest frame 100%) | 100% (lowest frame 100%) | Met |
| Working set ≤ 512 MB | **548–558 MB** (peak 568–578) | **512–515 MB** (peak 526–529); fullscreen 522–523 MB | **At the limit: 0–3 MB over in 3 runs of 3**, from 36–46 MB over before. See [Memory](#memory) |
| Pool texture memory ≤ 64 MB | 32.8 MB | 32.8 MB (the models' own textures aren't the pool) | Met |
| Main thread ≤ 4 KB per 60 s scroll | 64 B | **64 B** | Met |
| GPU time | 1.67–1.69 ms | **1.28–1.36 ms** | 20% less: 300 MultiMeshes of 64 instances each are gone |

Without per-game models, the committed build is unchanged from part 1:

| | Before | Committed |
|---|---|---|
| Plain scroll | 1, 3, 4 hitches; 0 over 2×; p99 20.84–21.21 ms; 420 MB; 64 B | 1, 0 hitches; 0 over 2×; p99 20.76–20.81 ms; 422 MB; 64 B |
| Boot window (300 frames) | 1 or 2 hitches a run | 0 to 2 hitches a run |

With the sample theme, on the 300-model library: 0 and 1 hitches, 0 over 2×, p99 20.79–20.85 ms, 100% textured (the screen and the label stream at 256²), 64 B, 516–523 MB. The 22 system cards all play an idle clip, so they're drawn as nodes. The focused TV swaps to its node tree for its clips, and swaps back to the MultiMesh.

## What changed on the way

Each problem was found with the bench, and fixed or tried and dropped, before the committed series.

| Problem | Evidence | Change |
|---|---|---|
| **Native memory held by wrappers.** Each model's `GltfState`, its CPU-side `ImporterMesh`es and every surface array read from them stay alive until their C# wrappers are finalised. With few GCs, that was 20–40 MB for 300 models. | 530–549 MB ([m6/part2/first-models-scroll/](m6/part2/first-models-scroll/)) | The converter tracks every wrapper it reads and disposes them when it's done. It also disposes the arrays it builds meshes from, and the decoded images. 508–515 MB ([exp-disposed-models-scroll/](m6/part2/exp-disposed-models-scroll/)). |
| **4,808 B on the main thread** with the sample theme: the TV's node tree was first copied when the focus reached a TV mid-scroll. | [exp-lazy-scenes-retro-scroll/](m6/part2/exp-lazy-scenes-retro-scroll/) | A batched template with focused or launch clips gets its two copies (the focused cell and the one it left) when it's added. 64 B. |
| Meshes made on the main thread, within the 2 ms budget, rather than on the workers | The grid took 346–367 ms to show all its art, against 14–19 ms: 300 models finishing over many frames kept rebinding cells. And +20 MB ([exp-main-upload-models-scroll/](m6/part2/exp-main-upload-models-scroll/)) | Dropped: meshes are made on the workers, as part 1 did. |
| A forced background gen2 GC once a list's models had loaded | No change to the working set (the managed heap was 8 MB) | Dropped. |
| `Stopwatch.StartNew` in the loader's per-frame poll | An allocation per frame while models load | Timestamps instead. |

## Memory

The 300 models add about 90 MB to the working set: 512–515 MB against 420–422 MB for the plain library, with the models' own textures only 12.5 MB of it. Without textures (the control) it's 458–460 MB. By the bench's own counters, video memory goes from 146 MB to 222 MB. Take away the textures and that leaves about 63 MB of buffers, **about 210 KB per model**, for meshes whose vertex and index data are about 35 KB each.

That fits D3D12, where every buffer is placed on a 64 KB boundary, and Godot gives each mesh surface three buffers (vertices, attributes, indices). So on this renderer a per-game model costs about 0.2 MB of video memory, however small it is. The same scroll on Vulkan cost 44 MB for the 300 models, against about 90 MB on D3D12. But Vulkan's baseline is 215 MB higher (637 MB), so switching isn't the answer ([exp-vulkan-*/](m6/part2/)).

**What this means:**
- A list with a few hundred per-game models is at the working-set target. Many more would pass it: every model of the shown list, and of the three cached lists, stays resident.
- The fixes are for the owner to choose, since each has a cost:
  - **Streaming:** keep only the models near the visible rows resident, with the load path made allocation-free on the main thread, since models would then load while scrolling.
  - **Packing:** put the small meshes of a list into shared buffers.
  - **Finding part 1's unexplained 70 MB** in the base working set, which would give the margin back on its own.

## Start-up

`models_loaded` comes 33 ms later than in part 1, 298 ms after our first code against 265 ms, and interactive moves with it. Inside the built-in boxes' load on the workers:
- reading each file takes 2 ms
- Godot's parse takes 3 ms
- the conversion takes 30 ms, with all six finishing within a millisecond of each other

A per-game model converted later in the same process, with the code warm, takes **2 ms** (part 1 measured 7.2 ms). So the 30 ms is first-call JIT of the new converter code, paid once per process by every worker at once. ReadyToRun would remove it, and still waits for the owner's approval of the crossgen2 runtime pack (M4). Creating the meshes on the main thread instead didn't change it (above).

## Model processing and loading

- **First use of a user model** (`ModelCache`): the check, texture scaling (only for a texture over the budget's side) and the cached copy happen on the model's worker. After that, each boot reads the cached report and file. The report cache's first read in a process costs about 70 ms (JSON source generation's first use), on a worker, in parallel with the loads.
- **Per-game models of a list** load on workers when the list does, and the main thread adopts them within 2 ms a frame. The 300 of the PS2 list were all in within the bench's settle time.
- **Drawing:** a per-game model is drawn on its cell's `MeshInstance3D`. The most drawn as nodes in a frame was the visible cells with models, a handful in each screen. Batched templates still take one draw call each.

## Captures

[m6/part2/captures.jpg](m6/part2/captures.jpg):
- the sample theme's systems grid (console cards playing their idle clip; the focused one plays its focused clip)
- its games grid (CRTs showing screenshots, with logos or printed titles on the stands, and the test card where there's no art)
- the launch clip mid-spin
- the sample theme and Memory Card, each with per-game models beside the batched items
- Memory Card's systems grid, unchanged

Each was taken with `--capture` and `--fixed-fps 60` in the editor run, on the synthetic libraries. The launch capture used `--nav-script=right,right,accept`: the synthetic PS2 emulator isn't installed, so the launch clip plays and the launch then fails, as it should.

## Not measured

- A theme author's Blender model on the real display, and importing the owner's own models: the owner's manual test ([manual-tests.md](../manual-tests.md#m6-part-2-your-own-models-the-sample-theme-and-clips)).
- Handheld (undocked) mode, 3840×2160 docked, and PresentMon: as in M5, they need the owner or the hardware.
- **Skinned and morph-target clips are untested.** The converter carries bones, weights and blend shapes into the item shader's mesh format, but no committed model or test uses them, and Godot doesn't run in Core's tests. A rigged Blender model is the first check for them (in the manual test).
