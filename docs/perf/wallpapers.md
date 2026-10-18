# Theme wallpapers: checks and measurements

Measured on 18 October 2026 on the development PC (Intel Core i5-11400F, 64 GB, GeForce RTX 3060), windowed at 1280×800 on a 60 Hz display, with nothing else running.

- Builds are ExportRelease on .NET 8.0.32, Mobile/D3D12, with the shader baker on (both PCKs 2.1 MB).
- **Before** is commit `3490cf9`'s app (its shaders and `godot/src`, with this change's Core, which only reads the new keys), exported to `artifacts/export-wall-before/`. **After** is the change (A6 Background, "Wallpapers"), exported to `artifacts/export-wall-after/`. All were benched in the same session, one after the other.
- Each is one warm-up and 5 benched runs. The tables give the medians of the 5, and the JSON is in [wallpapers/](wallpapers/) (`run-0` is the warm-up).
- The decision is in [ARCHITECTURE.md](../ARCHITECTURE.md) (decisions log, 2026-10-18).

The theme is `tests/themes/slot-showcase` copied into the synthetic library's `themes/`. It has a 1920×1080 opaque WebP as its wallpaper and a 1920×1080 PNG with transparency for PS2. The scroll is PS2's 10,000 games, so both wallpapers are loaded and PS2's is on screen for the whole scroll. The before build reads neither key (`wallpaper` is an unknown key to it), so it shows the same theme's gradients.

```powershell
.\tools\bench-export.ps1 -SkipExport -Executable artifacts\export-wall-<build>\OdysseyLauncher.exe -Label wall-scroll-<build> -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll', '--theme=slot-showcase'
```

## What it can cost

- **Per frame, at rest:** the background layer already covers every pixel; a wallpaper adds one texture read per pixel to it, with no extra layer or overdraw. The item shader reads the wallpapers only while a grid fades (`grid_fade > 0`, a uniform branch).
- **Memory:** each loaded wallpaper is an RGBA8 texture with no mipmaps, scaled to fit 2560×1080: 7.9 MB at 1920×1080. At most three are kept.
- **The main thread:** nothing. Decoding, scaling and making the texture run on the thread pool. A cross-fade sets one more `Vector4` per material a frame, and the textures only when a slot's changes.
- **Start-up:** the theme's wallpaper is asked for as soon as the theme is resolved and is never waited for.

## Results

**The 60 s scroll of PS2's games, with its wallpaper on screen.**

| | Before | After |
|---|---|---|
| Start-up of our code | 262 ms (258–302) | 270 ms (262–332) |
| Scroll p50, p95, p99 | 16.67, 16.87, 16.98 ms | 16.67, 16.82, 16.91 ms |
| Scroll's longest frame, per run | 17.1–29.2 ms | 17.3–23.0 ms |
| Scroll hitches, per run | 1, 0, 1, 1, 0 | 0, 0, 0, 0, 0 |
| GPU, render CPU | 0.18, 0.19 ms | 0.21, 0.21 ms |
| Main-thread allocation in the scroll | 96 B | 96 B |
| Texture memory | 231.8 MB | 247.8 MB |
| Video memory | 269.4 MB | 291.6 MB |
| Managed heap | 19.4 MB | 18.5 MB |
| Working set (peak) | 379 MB (410) | 415 MB (438) |

- **GPU: +0.03 ms a frame** for a full-screen wallpaper at 1280×800, the one sample per pixel. At 1080p (the cap for the 3D, which the background goes through) it would be about 2× that, still well under a tenth of a millisecond on this GPU. Frame times, hitches and main-thread allocation are unchanged.
- **Memory: +16.0 MB of textures for two wallpapers**, exactly two 1920×1080 RGBA8 images. Godot's video memory is 6 MB higher than that, and the working set 36 MB higher (peak +28 MB). The rest is native: the decoder's and uploads' memory, which the allocator keeps once used. Three wallpapers would add about 8 MB of textures more.
- **Start-up: no change measurable.** The medians differ by 7 ms, within the runs' spread. The decode is on the thread pool: 117 ms for the opaque 1080p WebP at boot (alongside the DB opening), and 20 ms for the PNG.

**The first version decoded with the OS decoder (WIC), as `Thumbnails` does** ([wallpapers/scroll-after-os-decoder/](wallpapers/scroll-after-os-decoder/)). Its 8 MB managed buffer per wallpaper stayed on the large-object heap, because browsing never makes a full collection. The managed heap was 39.8 MB against 19.4, and the working set 436 MB (peak 456). Godot's own decoder (`Image.LoadFromFile`, then `Resize`) keeps the image in native memory, freed when it's disposed. That brought the managed heap back to 18.5 MB and the working set to 415 MB, with the same pictures (the captures match).

## Checks

- **Captures** (`--theme=slot-showcase --no-overlay`, 1280×720, `--fixed-fps 60`): the systems grid over the theme's opaque wallpaper; PS2's games over its transparent one, with PS2's gradient through it; and 13 frames into leaving PS2, where the cards fading in and the boxes fading out show both wallpapers mid cross-fade through them, with no seam (each item's fade reads the same image at the same screen point as the layer behind it).
- **A wallpaper that loads late** (PS2's, entered at once with `--start-system`, so never fetched ahead) shows the gradient, then fades in over 0.3 s.
- **Core's tests:** the keys, the paths (inside the folder, an image, existing, at most 16 MB), `fit`, a system's block replacing the theme's wallpaper, the base theme's inherited in its own folder, and that the shipped themes have none (`ThemeLoaderTests`, "Wallpapers").
