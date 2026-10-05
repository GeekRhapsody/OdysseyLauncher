# Spike: scraped images straight to the grid, no DDS derivatives

Measured on 5 October 2026 on the baseline Steam Deck (LCD APU, Windows 11, docked; the machine in [m1-spike.md](m1-spike.md#machine)), with nothing else running.

The question is whether the grid can read the scraped images themselves, instead of a baked BC7 DDS copy of each one (A3, "Baked derivatives are mandatory"). Removing the copies saves the cache folder and the bake. The cost is GPU memory: exports can't compress to BC7 at runtime, so the layers become RGBA8.

- **POC** is branch `poc/direct-source-images` (`02afcd3` plus the `--memory-log` tool). The games grid's streamer reads `media/...` itself. Its workers decode PNG, JPEG or WebP with Godot, squeeze the image to the layer's square with Lanczos, build mips, and upload into RGBA8 arrays. The app bakes no library images. Theme logos are still baked.
- **main** is `b758e45` (BC7 derivatives) with the same `--memory-log` tool applied, for the baseline.
- **Control** is the POC build with `--no-textures` (no media arrays, no streaming), as A3 asks for hitch comparisons.
- Both are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on. They're exported to `artifacts/export-poc/` and `artifacts/export-main/`.
- **The library** is a copy of the owner's export user folder (`artifacts/export/windows/userdata`), without its secrets, reading the same media folder in place. It has 169 systems and 8,005 games. Mega Drive has 956 games, with 950 covers (median 484×680 PNG), 950 screenshots and 947 logos, all from ScreenScraper. The theme is Slab, whose game templates have five media slots: cover (512²), plus back, spine, label and screenshot (256²). For main, every image was baked first (3,652 derivatives).
- The raw data is in [spike-direct-images/](spike-direct-images/): the bench JSON per configuration, and `memory.csv` with `gpu.csv` per memory run.

## Summary

| | POC (source images, RGBA8) | main (BC7 DDS) |
|---|---|---|
| Scroll p99, frames over 2×, hitches (5 runs, windowed) | 20.70 ms, 0, 5 | 20.99 ms, 0, 4 (control: 20.85 ms, 0, 7) |
| Grid textured while scrolling | 100% (min 100%) | 100% (min 100%) |
| Decode per image (mean, p95) | 19.2, 21.7 ms | 0.57, 1.22 ms |
| Media arrays, Godot's accounting | 187 MB | 59 MB |
| GPU memory, Windows' view, browsing (windowed / fullscreen) | 507 / 443 MB | 355 / 290 MB |
| GPU memory, Windows' view, while a game runs | 322 / 258 MB | 355 / 290 MB |
| Working set after the scroll | 586 MB | 450 MB |
| Cache on disk for these images | none | 1,219 MiB (the images themselves: 818 MiB) |

- **FPS and frame drops:** no difference. Every configuration holds the 59.94 Hz refresh: mean 16.68 ms in every run, **no frame over 2× the refresh interval in any of the 30 runs**, and hitch counts within the run-to-run spread of the no-texture control.
- **VRAM while browsing:** the POC uses about 128 MB more (Godot's accounting) or 152 MB more (Windows'), exactly the 4× of RGBA8 over BC7 on the five 64-layer arrays. Half of that pool is never written on the Mega Drive, whose template only streams covers (suggestion 1).
- **VRAM while a game runs:** the POC *gives back* 185 MB, ending up 32 MB *below* main. main gives back nothing: Godot frees its arrays, but the process's GPU memory doesn't fall (finding 3).
- On the Deck, GPU memory and RAM are the same memory, and nearly all of the extra working set is the bigger arrays (finding 4).

## Results

Every configuration is one warm-up plus 5 runs of the scroll scenario: all 956 Mega Drive games, first row to last in 60 s. The tables give medians, and hitches as per-run counts.

### A. Windowed, 1280×800 (handheld size)

| | POC | main | Control |
|---|---|---|---|
| Start-up of our code | 387 ms | 378 ms | 394 ms |
| Scroll p50, p95, p99 | 17.96, 20.01, 20.70 ms | 18.06, 20.25, 20.99 ms | 18.19, 20.22, 20.85 ms |
| Longest frame | 25.7 ms | 25.5 ms | 26.3 ms |
| Hitches per run | 1, 0, 0, 2, 2 | 2, 1, 0, 1, 0 | 1, 3, 2, 1, 0 |
| Frames over 2× | 0 | 0 | 0 |
| GPU, render CPU | 1.58, 0.41 ms | 1.69, 0.36 ms | 1.66, 0.36 ms |
| Grid textured (mean, min) | 100%, 100% | 100%, 100% | – |
| Visible grid textured after entering | 19.1 ms | 18.2 ms | – |
| Decode mean, p95 | 19.2, 21.7 ms | 0.57, 1.22 ms | – |
| Upload mean, longest | 0.32, 1.26 ms | 0.21, 2.72 ms | – |
| Frames stopped at the 4 MB budget, at the cap of 4 | 1–3, 0 | 0, 186–187 | – |
| GCs in the scroll (gen0/1/2), total pause | up to 3/1/1, ≤ 8.1 ms | none | at most one gen0 |
| Allocated in the run (all threads); main thread in the scroll | 14.3 MB; 96 B | 2.8 MB; 96 B | 2.5 MB; 96 B |
| Working set (peak) | 586 MB (603) | 450 MB (464) | 374 MB (384) |
| Godot texture, video memory | 251.8, 291.9 MB | 123.8, 163.9 MB | 64.8, 102.4 MB |

### B. Fullscreen, 2560×1440 (docked; 3D at 0.75 scale, the automatic 1080p cap)

| | POC | main | Control |
|---|---|---|---|
| Start-up of our code | 430 ms | 394 ms | 517 ms |
| Scroll p50, p95, p99 | 16.35, 21.77, 22.60 ms | 16.35, 21.75, 22.62 ms | 16.32, 21.52, 22.21 ms |
| Longest frame | 25.0 ms | 24.8 ms | 23.6 ms |
| Hitches per run | 3, 1, 0, 0, 1 | 2, 0, 1, 0, 0 | 3, 0, 1, 0, 0 |
| Frames over 2× | 0 | 0 | 0 |
| GPU, render CPU | 3.07, 0.33 ms | 3.04, 0.34 ms | 3.00, 0.33 ms |
| Grid textured (mean, min) | 100%, 100% | 100%, 100% | – |
| Visible grid textured after entering | 13.9 ms | 13.7 ms | – |
| Decode mean, p95 | 19.6, 22.0 ms | 0.41, 0.67 ms | – |
| Upload mean, longest | 0.41, 0.86 ms | 0.12, 0.36 ms | – |
| Frames stopped at the 4 MB budget, at the cap of 4 | 2–8, 0 | 0, 160–161 | – |
| GCs in the scroll (gen0/1/2), total pause | 2–3/0–1/0–1, 6.9–8.7 ms | 1–2/0/0, 4.2–5.2 ms | none |
| Working set (peak) | 589 MB (606) | 450 MB (467) | 374 MB (386) |
| Godot texture, video memory | 272.6, 312.7 MB | 144.6, 184.2 MB | 85.6, 123.2 MB |

The fullscreen target of 0 hitches (A3) isn't met by any of the three, the control included, so that's the environment and not this change. The display ran at 2560×1440 for these runs; 3840×2160 still needs measuring.

### C. GPU memory: browsing, while a game runs, and back

Each memory run boots into the Mega Drive grid, pages down six times and back up two, waits, then launches the focused game. The game is the fake emulator, which sleeps for 30 s and uses no GPU. The run then waits back in the grid. There are two runs per build and display mode, and they agreed within 1 MB.

- `memory.csv` comes from the app (`--memory-log`): Godot's video and texture memory, and the phase.
- `gpu.csv` comes from Windows' `GPU Process Memory` counters for the process, sampled outside it (`tools/gpu-memory-run.ps1`).

The figures are medians of the samples taken from 3 s after each phase began (`tools/gpu-memory-summary.py`). "Dedicated" is the APU's carve-out; "shared" is system memory the GPU uses.

| | Browsing | Game running | Back in the grid |
|---|---|---|---|
| **POC, windowed:** Windows (dedicated + shared) | **507.1** (94.0 + 413.1) | **322.4** (93.3 + 229.1) | 507.1 |
| main, windowed: Windows | **354.5** (93.4 + 261.1) | **354.5** (93.4 + 261.1) | 354.5 |
| **POC, fullscreen:** Windows | **442.9** (93.8 + 349.1) | **258.1** (93.1 + 165.1) | 442.9 |
| main, fullscreen: Windows | **290.3** (93.2 + 197.1) | **290.3** (93.2 + 197.1) | 290.3 |
| POC: Godot's video, texture memory | 312.7, 272.6 | 130.2, 86.1 | 317.2, 273.1 |
| main: Godot's video, texture memory | 184.7, 144.6 | 130.2, 86.1 | 189.2, 145.1 |
| POC: working set, windowed / fullscreen | 710–721 / 654–655 | 506–517 / 426–451 | 698–700 / 620–645 |
| main: working set, windowed / fullscreen | 536–539 / 469–473 | 520–523 / 453–457 | 527–528 / 459–463 |

## Findings

1. **Frame pacing doesn't change.** Decoding moves from 0.5 ms to about 20 ms an image, but it happens on the two workers. The main thread only uploads, at 0.3–0.4 ms a layer on average, and the RGBA8 layers meet the 4 MB budget after about 2 covers. The scroll stayed 100% textured, with no frame over 2× in 30 runs, and the main thread allocated the same 96 B in every configuration.
2. **The extra GPU memory is exactly the format.** The media arrays (texture memory above the control's) are 187 MB against 59 MB. The difference, 128 MB, is what the layer sizes give: a 512² mip chain is 1.33 MiB in RGBA8 against 0.33 MiB in BC7, and a 256² chain is 0.33 against 0.08. With 64 cells, that's 170.7 MiB against 42.7 MiB for Slab's five slots. The other ~16 MB in both builds doesn't come from this change.
3. **On main, evicting the textures for a game gives nothing back to Windows.** Godot's accounting drops by 59 MB when the game starts, but the process's GPU memory stays at 290 MB (fullscreen) the whole time the game runs. With the POC's RGBA8 arrays it drops by 185 MB, to 258 MB. The likely cause, not confirmed here, is the D3D12 memory allocator Godot uses keeping the memory heaps it carved the BC7 arrays from, while the much larger RGBA8 arrays are released outright. Either way, A1's "free the media textures for the emulator" currently frees nothing an emulator could use on main. That's worth a follow-up whichever way this spike goes.
4. **On the Deck, VRAM is RAM.** The carve-out ("dedicated") stays at 93–94 MB in every phase and build, and everything else is shared system memory. The POC's extra working set (136 MB after the scroll) matches its extra GPU memory (128–152 MB), so the RAM increase the owner noticed is mostly the arrays themselves. Shrinking the arrays shrinks both.
5. **The managed heap does more work.** The POC allocates about 11 MB more per run, on the workers (probably each worker's read buffer, which grows to the largest file it meets and lands on the large object heap; not confirmed), and gets up to one gen2 collection per run, with ≤ 8.7 ms of GC pause in total. None of it caused a frame over 2×. Reading each file at its size, or into a pooled native buffer, would remove it.
6. **Throughput is the real cost.** Two workers decode about 100 images a second, against several thousand from DDS. That was enough for this scroll (the M1 rate) and for entering a system, where the visible grid was textured within 14–19 ms in both builds. A jump to a fresh screen (LB/RB, letters, a long hold) has to decode every image on it. For a screen of 15–20 Mega Drive covers that's roughly 0.15–0.2 s, against a frame or two with DDS, and more for a template with several slots. This is estimated from the decode times, not measured; watch for it by eye.
7. **Disk:** the 3,652 derivatives for this library take 1,219 MiB, half as much again as the 818 MiB of images they copy, and baked in 220 s on 6 threads. The bake the app and `odyssey-scrape bake` use, on one below-normal thread, did about 800 in its first 25 minutes, while the exports were running.

## Keeping VRAM low while reading scraped images directly

These are ordered by cost to quality and effort. The sizes are computed for 64 cells and this theme; none of them was measured in this spike.

1. **Only make arrays for the slots the shown system can fill.** The arrays follow the union of all the theme's templates, not the system on screen. The Mega Drive's template (`clamshell`) has no label or screenshot slot (only the arcade cabinet does), and its back and spine have no scraped media, so they show generated faces. In these runs only the cover was streamed (916 uploads for 956 games), and **the four 256² arrays, 85.3 MiB of RGBA8 and half the pool, were never written.** Building the layout from the shown system's templates, and the slots whose chains reach media it actually has, would avoid that. Arrays are already built on a worker in about 100 ms when the theme changes, so this would be a rebuild on entering a system with a different set. **No cost in quality.**
2. **Size each slot's layers by what it shows on screen.** The cover needs 512², and the spine needs 256² along its length ([anisotropy.md](anisotropy.md)). A label or screenshot panel may be fine at 128², which is a quarter: 5.3 MiB instead of 21.3 MiB a slot.
3. **Use 16-bit RGB565 for slots without transparency.** That halves RGBA8 (the cover array goes from 85.3 to 42.7 MiB), and the conversion is cheap (`Image.Convert`). The risk is banding on gradients. D3D12's support for that format in a mipmapped array still needs checking on the Deck. With item 1, the Mega Drive's pool would be its cover array alone: 42.7 MiB in RGB565, the same as today's whole five-slot BC7 pool, or 85.3 MiB in RGBA8.
4. **Compress on the workers as images stream in.** BC1 is half the size of BC7 (the whole five-slot pool would be 21.3 MiB), but it needs a fast encoder. Core's BC7 encoder takes about 0.44 s a cover (M4), roughly 20 times too slow to stream with. A BC1 range-fit encoder should take milliseconds, adding to the ~20 ms decode. BC1's 1-bit alpha doesn't suit logos with soft edges. Compressing on the GPU with a compute shader (as Godot's importer does) would be fastest, but is the most work: it isn't in export templates (A3).
5. **Fit the pool to the layout.** 64 cells covers the biggest layouts. A layout that shows fewer cells, plus its prefetch rows, needs proportionally less: 40 cells would be 37.5% less in every array.
6. **Keep evicting during games, and make it effective on main too** (finding 3). With RGBA8 arrays the eviction already returns 185 MB. If a compressed format comes back (BC1, or BC7 on main), check that its arrays are actually released.
7. **For RAM and CPU (not VRAM): decode at the layer's size.** Core's `IImageDecoder` (WIC) already decodes and scales in one step for the baker, and JPEG can be scaled while decoding. Using it instead of a full-size Godot decode plus Lanczos would cut the per-image memory and probably much of the 20 ms.

## Reproducing

```powershell
# Builds: the POC branch, and main with the --memory-log tool, each exported (not headless).
godot --path godot --export-release "Windows Desktop" $PWD\artifacts\export-poc\windows\OdysseyLauncher.exe
# Frame times: per build, plus the control (-AppArgs ... '--no-textures'), windowed and with -Fullscreen.
.\tools\bench-export.ps1 -SkipExport -Executable artifacts/export-poc/windows/OdysseyLauncher.exe -Label sdi-poc-win `
    -AppArgs "--user-dir=$PWD\artifacts\poc-bench\user", '--bench-scenario=scroll', '--bench-system=megadrive'
# GPU memory through a launch (the user folder's Mega Drive uses the fake emulator, sleeping 30 s).
.\tools\gpu-memory-run.ps1 -Executable artifacts/export-poc/windows/OdysseyLauncher.exe -Out artifacts/poc-bench/mem-poc-win-1 -Seconds 80 `
    -AppArgs "--user-dir=$PWD\artifacts\poc-bench\user", '--start-system=megadrive', `
    '--nav-script=wait,wait,wait,pagedown,pagedown,pagedown,pagedown,pagedown,pagedown,pageup,pageup,wait,wait,wait,wait,wait,wait,wait,wait,wait,wait,accept'
python tools/gpu-memory-summary.py "artifacts/poc-bench/mem-*"
```
