# M1 spike results: grid rendering, cover textures and renderer

Measured on 27 September 2026 on the baseline Steam Deck, using exported ExportRelease builds only. This document answers three questions with numbers:
1. How should grid items be drawn?
2. Which cover texture format should the grid load?
3. Which renderer should the launcher use?

It closes with the performance targets and the risks. The design that follows from it is in [ARCHITECTURE.md](ARCHITECTURE.md) (A3 and the decisions log).

- **Spike code:** branch `spike/grid-perf`, under `godot/spikes/` (commits `e165f58` and `7fe35ea`). It's throwaway code and isn't merged.
- **Raw evidence:** [perf/m1/](perf/m1/) holds one JSON file per configuration (the per-run values and medians) and the six load-test reports.

## Recommendations

| Question | Recommendation | Why, in one line |
|---|---|---|
| 1. Item rendering | **One `MultiMesh` per template plus a `Texture2DArray` with one layer per pool cell**, with the layer, fade and phase passed in `INSTANCE_CUSTOM`. Per-game custom `.glb` models use per-node instances. | Both approaches hold vsync with 64 cells. MultiMesh uses 3 draw calls instead of 42 and about 20% less render CPU, and its texture memory is fixed by the pool size. |
| 2. Cover format | **BC7 in DDS, 512×512 with a full mip chain**, read into a pooled buffer and decoded with `Image.LoadDdsFromBuffer(ReadOnlySpan<byte>)` on 2 workers. The main thread updates textures that were created at boot. | Decode is 0.26 ms per cover against 5.4 ms (PNG) and 4.1 ms (JPEG). It uses 4× less VRAM, and the visible grid is textured 10 ms after the first frame instead of about 100 ms. **Blocker:** export templates can't encode BC7 (see risk R1). |
| 3. Renderer | **Mobile, on D3D12.** | Frame pacing is the same as Forward+, GPU time is 36–42% lower (1.2 ms against 2.0 ms at 1280×800), start-up is the same or faster, and the output matches within 4/255. The design uses no feature that only Forward+ has. |

**Targets.** Start-up for our code (186–449 ms) and the p99 target (17.65–18.34 ms against 18.35 ms) are both met. The "0 hitches" target is met by the chosen configuration (0, 0 and 0 hitches), but it can't be met reliably in windowed mode on this machine. The no-texture control scene has 0–2 hitches per 60 s run there (1–4 per 3 runs), which comes from presentation rather than from the launcher. A revised wording is proposed [below](#performance-targets-verdict-and-proposed-changes).

## Machine and method

- **Hardware:** Steam Deck LCD. AMD Custom APU 0405 (4 cores and 8 threads, Zen 2), AMD Custom GPU 0405 (RDNA2, 8 CUs, driver 32.0.11002.3007), 16 GB shared memory.
- **Software:** Windows 11 Pro 10.0.26200. Godot 4.7.2.stable.mono, with a self-contained .NET 8.0.31 runtime in the export.
- **Display:** the Deck is docked. The desktop ran at **2560×1440, 59.94 Hz, 100% scaling** during these runs (DPI-aware `GetSystemMetrics`), although WMI reports the monitor as 3840×2160. So "fullscreen" below means 2560×1440, and **4K wasn't measured**. The handheld panel wasn't measured either; see [Not covered](#not-covered-by-this-spike).
- **Library:** 10,000 synthetic games, each with its own 512×512 cover showing a distinct colour and its index in large digits. The covers were written to disk in 7 formats before the tests (18.6 GB, 0 failures, 34 minutes with the editor binary). They have gradients, stripes and noise, so PNG and JPEG sizes resemble real art: PNG averages 245 KB and JPEG (quality 0.9) 65 KB.
- **Grid:**
  - 8 columns, so 1,250 rows.
  - A pool of 8 rows × 8 columns = 64 cells, bound as rows scroll into view. About 4 rows (32–40 covers) are on screen.
  - A DVD-case box mesh (0.711 × 1 × 0.074) with front, back and spine UVs; the face id is in `COLOR.r`.
  - The camera scrolls and the grid never moves.
  - The focused case lifts 0.45 towards the camera, scales to 1.12× and turns slowly.
  - Unfocused cases bob in the vertex shader (`TIME` plus a per-instance phase).
  - One opaque shader fades from the placeholder to the cover.
  - The four-corner gradient is on a canvas layer. Three directional lights are children of the camera, plus an ambient colour.
- **Input:** `ui_*` actions from the keyboard and controller, with hold-to-repeat: first repeat after 300 ms, then every 90 ms, then every 40 ms after 1.2 s.
- **Streaming:**
  - 2 decode workers (`clamp(ProcessorCount / 4, 1, 4)`) at BelowNormal priority. Each pool cell has one request slot; a new bind bumps its generation, which cancels stale work.
  - Workers pick the pending cell closest to the view centre, and rows ahead of the scroll count 0.6× as far.
  - The main thread uploads within 4 MB per frame, by updating textures created at boot: `ImageTexture.Update`, or `Texture2DArray.UpdateLayer`.
- **Bench scenario:**
  - The scripted scroll runs from row 0 to the last row (1,246 rows) in 60 s: 20.8 rows/s, or about 166 covers/s. That's close to the 40 ms maximum repeat rate.
  - The "slow" variant scrolls 300 rows in 60 s (5 rows/s).
  - The scroll starts at frame 90. Scroll statistics cover only the scroll frames, about 3,600 per run. Start-up frames are covered by `app_startup_ms`.
- **Runs:** each configuration ran one warm-up (which also warms the shader and file caches), then **3 measured runs**. Medians are shown; hitches and ">2×" are totals over the 3 runs, out of about 10,800 frames.
- **Thresholds:** the refresh interval is 16.68 ms. A hitch is over 25.02 ms (1.5×), ">2× budget" is over 33.37 ms, and the p99 target (1.1×) is 18.35 ms.
- **Where the numbers come from:**
  - Frame intervals are raw `Time.GetTicksUsec()` at `frame_post_draw`.
  - Render CPU and GPU times come from `RenderingServer.ViewportGetMeasuredRenderTime*`.
  - RAM is the process working set, from `Process`.
  - "Godot texture memory" is `Performance.RenderTextureMemUsed`.
  - GPU dedicated and shared memory are the highest values of the Windows "GPU Process Memory" counters, polled while the app runs.
- **File cache:** the measured runs read files the warm-up had just read, so the numbers are **warm-cache**. The first load-test pass read files that had dropped out of the cache (the library is bigger than RAM), which gives a rough cold figure.

## 1. Rendering: a node per item, or a MultiMesh with a Texture2DArray

Forward+, BC7 covers, windowed 1280×800, whole library in 60 s.

| Configuration | Our code (ms) | Mean (ms) | p99 (ms) | Max (ms) | Hitches | >2× | Render CPU (ms) | GPU (ms) | Draw calls | Working set (MB) |
|---|---|---|---|---|---|---|---|---|---|---|
| Nodes, BC7 | 303.5 | 16.68 | 17.89 | 20.51 | 0 | 0 | 0.32 | 1.98 | 42 | 345 |
| MultiMesh, BC7 | 291.6 | 16.68 | 17.93 | 23.14 | 2 | 1 | 0.26 | 2.02 | 3 | 374 |
| MultiMesh, BC7, no counter polling | 259.5 | 16.68 | 17.77 | 22.87 | 0 | 0 | 0.27 | 2.04 | 3 | 375 |
| Nodes, no textures | 210.0 | 16.68 | 17.88 | 19.30 | 0 | 0 | 0.32 | 2.07 | 42 | 332 |
| MultiMesh, no textures | 188.8 | 16.68 | 18.00 | 25.38 | 4 | 1 | 0.26 | 2.08 | 3 | 346 |
| Nodes, PNG | 236.1 | 16.68 | 18.01 | 25.17 | 2 | 0 | 0.35 | 2.01 | 42 | 392 |
| MultiMesh, PNG | 243.6 | 16.68 | 18.03 | 26.43 | 3 | 0 | 0.29 | 1.98 | 3 | 366 |
| Mobile: nodes, BC7 | 205.1 | 16.70 | 17.97 | 73.91 | 6 | 5 | 0.30 | 1.27 | 42 | 327 |
| Mobile: nodes, BC7 (rerun) | 309.0 | 16.68 | 18.01 | 21.56 | 2 | 0 | 0.29 | 1.21 | 42 | 324 |
| Mobile: MultiMesh, BC7 | 203.8 | 16.68 | 17.88 | 21.75 | 0 | 0 | 0.23 | 1.23 | 3 | 356 |

**Findings**
- Both approaches stay locked to vsync. The mean is 16.68 ms everywhere, and p99 is 17.8–18.0 ms.
- At 64 cells the CPU difference is 0.06 ms per frame: 0.26 ms of render CPU for MultiMesh against 0.32 ms for nodes. GPU time is the same.
- The hitch counts don't separate the two approaches. The MultiMesh control with no textures at all had 4 hitches (see [Hitches](#hitches-what-they-are)).
- Mobile/nodes had one 234.7 ms frame and one 73.9 ms frame, in runs 3 and 2. A rerun didn't reproduce them (max 21.6 ms), so they're treated as system outliers.
- The per-frame work for both approaches is tiny, because the camera scrolls instead of the grid:
  - binding a row: 8 transforms, 8 shader-parameter sets and 8 requests
  - the focused and previous items: 2 transforms
  - fading items: one parameter set each
  - Our whole `_Process` takes about 0.02 ms per frame.

**Recommendation: MultiMesh plus a Texture2DArray** for template boxes, with per-node instances only for per-game custom models.
- **Fixed memory:** the array is allocated once with one layer per pool cell. That's 64 × 341 KB = 21.8 MB for BC7.
- **One material and one draw call** per template, which fits the "no extra variants" rule.
- **The placeholder fade is already per instance**, through `INSTANCE_CUSTOM`.
- **The limits:** every layer must share a size and format, so the canonical derivative is mandatory (it already is in A3). User `.glb` models don't fit in a shared MultiMesh.
- **If the hybrid proves awkward in M5, nodes-only is an acceptable fallback.** The data shows no performance reason to avoid it at this scale.

## 2. Cover textures: format, decode and upload

### 2a. Which GPU formats Godot 4.7 can load at run time from outside the project

These results come from the load test's probes, run in the **exported** build.

| Path | Works in an export? | Notes |
|---|---|---|
| `Image.LoadDdsFromBuffer(ReadOnlySpan<byte>)` | **Yes** | BC7 and BC1 with 10 mip levels load as `BptcRgba` and `Dxt1`. The span overload means a pooled read buffer, with no managed `byte[]` per cover. |
| `Image.LoadFromFile("…dds")` and `Image.LoadFromFile("…ktx")` | **No** | Returns an empty image. Use the buffer loaders. |
| `Image.LoadKtxFromBuffer(ReadOnlySpan<byte>)` | **Yes** | Tested with KTX 1.1 BC7 files that the spike writes itself. Godot can read KTX, but not write it. |
| `ResourceLoader.Load<Image>(absolute path, CacheMode.Ignore)` for a saved `Image` `.res` | **Yes** | The slowest of the BC7 containers, and the binary format is tied to the Godot version. |
| Raw BC7 mip chain, then `Image.CreateFromData(…, ReadOnlySpan<byte>)` | **Yes** | The fastest, but it has no header, so size and format are implicit. |
| `Image.Compress(Bptc)` and `Image.Compress(S3Tc)` | **No: `Unavailable`** | Godot documents this as editor-only, and the probe confirms it. **An exported launcher can't bake BCn derivatives** (risk R1). |
| `Image.SaveDds` | Yes, for uncompressed data | The DDS writer is in the templates. The encoders aren't. |

### 2b. Load time per cover, per format (load test)

A single worker loads 300 covers in sequence. The main thread uploads each one into an `ImageTexture` (`Update`) and into a `Texture2DArray` layer (`UpdateLayer`). "Warm" is the mean over 5 runs (Forward+ runs 2–3 and Mobile runs 1–3). "Cold-ish" is Forward+ run 1, which read files that had dropped out of the OS cache (not true for `dds-bc7`, which the benches had just read). PNG and JPEG decode includes the conversion to RGBA8 and mipmap generation, which a derivative would otherwise have done at bake time.

| Format | File (KB) | GPU (KB) | Decode, warm: mean / p95 (ms) | Decode, cold-ish mean (ms) | `ImageTexture.Update`: mean / p95 / max (ms) | Array layer update: mean / p95 / max (ms) |
|---|---|---|---|---|---|---|
| PNG | 245 | 1,365 | 5.43 / 6.48 | 6.70 | 0.351 / 0.467 / 8.5 | 0.166 / 0.366 / 1.1 |
| JPEG (q 0.9) | 65 | 1,365 | 4.09 / 4.88 | 5.14 | 0.292 / 0.407 / 1.1 | 0.163 / 0.245 / 32.4 |
| **DDS BC7** | 342 | 341 | **0.26 / 0.41** | 0.27 (warm) | 0.097 / 0.164 / 0.7 | **0.028 / 0.045** / 37.0 (first upload) |
| DDS BC1 | 171 | 171 | 0.16 / 0.29 | 1.07 | 0.075 / 0.158 / 0.7 | 0.022 / 0.040 / 0.2 |
| KTX 1.1 BC7 | 341 | 341 | 0.35 / 0.55 | 1.26 | 0.104 / 0.210 / 0.4 | 0.029 / 0.054 / 0.2 |
| Image `.res` BC7 | 342 | 341 | 0.45 / 0.77 | 1.61 | 0.101 / 0.199 / 0.7 | 0.027 / 0.047 / 0.2 |
| Raw BC7 | 341 | 341 | 0.21 / 0.35 | 1.10 | 0.109 / 0.236 / 0.6 | 0.030 / 0.060 / 0.3 |

### 2c. The formats in the scrolling grid

MultiMesh, Forward+, windowed 1280×800.

| Configuration | Textured after first frame (ms) | Textured while scrolling | Mean / p99 / max (ms) | Hitches | Upload mean / max (ms) | Frames at the upload budget | Godot texture memory (MB) | Working set (MB) |
|---|---|---|---|---|---|---|---|---|
| BC7 (DDS) | 10 | 100.0% | 16.68 / 17.93 / 23.14 | 2 | 0.080 / 33.9 | 3 | 45.1 | 374 |
| BC7 (raw) | 12 | 100.0% | 16.68 / 17.86 / 25.30 | 4 | 0.080 / 17.7 | 3 | 45.1 | 374 |
| BC1 (DDS) | 21 | 100.0% | 16.68 / 17.85 / 21.06 | 0 | 0.060 / 17.8 | 1 | 33.1 | 405 |
| PNG | 108 | 100.0% | 16.68 / 18.03 / 26.43 | 3 | 0.329 / 1.2 | 2,338 | 109.1 | 366 |
| PNG, 4 workers | 108 | 100.0% | 16.68 / 18.34 / 27.19 | 3 | 0.293 / 1.0 | 2,344 | 109.1 | 384 |
| JPEG | 100 | 100.0% | 16.68 / 17.87 / 26.39 | 4 | 0.322 / 2.2 | 2,343 | 109.1 | 366 |
| PNG, slow (5 rows/s) | 111 | 100.0% | 16.68 / 17.84 / 24.52 | 1 | 0.337 / 2.0 | 572 | 109.1 | 365 |
| BC7, slow (5 rows/s) | 11 | 100.0% | 16.68 / 17.95 / 25.11 | 6 | 0.085 / 13.5 | 3 | 45.1 | 373 |

- **"Textured while scrolling"** is the share of on-screen cell-frames whose cover had been uploaded. Every format kept up at 166 covers/s.
- **PNG and JPEG saturate the 4 MB upload budget** (3 RGBA8 covers a frame) in about 65% of scroll frames. So they're close to their limit.
- **Four workers don't help PNG.** Decode per cover rises from 5.5 ms to 6.5 ms because the workers contend on 4 cores, and p99 gets slightly worse.
- **Upload maxima of 13–43 ms** are the first uploads after the first frame, in frames 2–5 (see [Hitches](#hitches-what-they-are)). Where a maximum is longer than that configuration's worst scroll frame (33.9–43.4 ms with BC7), the upload can't have happened during the scroll.

### 2d. Upload path

The load test also tried texture creation from a worker thread, in the export.
- `RenderingServer.Texture2DCreate` **from a worker works** in 4.7: no errors, and no stall on the main thread (frame max 18–25 ms, the same as idle).
- But each call **blocks the calling worker for about 11.8 ms**, because it waits for the frame's sync point. That's about one texture per frame per worker.
- The same call on the main thread has a p50 of 0.4–0.5 ms, with **outliers of 17–66 ms**.
- Updating a texture that already exists costs 0.03 ms (BC7 array layer) to 0.35 ms (RGBA8 `ImageTexture`).

**Recommendation for question 2**
- **Format:** BC7 in DDS, 512² with mips. It's the fastest standard container that Godot both writes (in the editor) and reads (in exports), and a DDS header costs 0.05 ms over raw.
  - BC1 halves disk and VRAM and is 40% faster, but it shows visible block artefacts on gradients and text, and it has no alpha. Keep it as an option for a low-memory setting.
  - Don't use KTX (it needs our own writer and is slower) or `.res` (slower, and tied to the Godot version).
- **Loading:** `File.OpenHandle` plus `RandomAccess.Read` into a per-worker pooled buffer, then `Image.LoadDdsFromBuffer(span)`. There's no managed `byte[]` per cover.
- **Uploads:** create every pool texture at boot, and only *update* them while browsing, on the main thread, within a byte budget. Never create textures on the main thread while browsing.
  - Worker-side `Texture2DCreate` is only for one-off textures outside the pool, such as the focused item's full-resolution art.
- **Workers:** 2, as A3 says.
- **Budget:** 4 MB per frame. BC7 only reaches it during the first frames. Also cap uploads at 8 per frame, so that a row bind can't land all at once. This cap is proposed but not yet measured.
- **Fallback until R1 is resolved:** JPEG derivatives. They met every frame target and are 5× smaller on disk than BC7. The costs are 4× the VRAM, ~100 ms to texture the first screen, and PNG/JPEG running close to the upload budget at maximum scroll speed.

## 3. Renderer: Forward+ or Mobile

Both use D3D12. MultiMesh unless stated.

| Configuration | First frame since process start (ms, 3 runs) | Our code (ms) | GPU (ms) | Render CPU (ms) | p99 (ms) | Hitches | Godot texture memory (MB) |
|---|---|---|---|---|---|---|---|
| Forward+, BC7 | 1,686 / 1,725 / 1,596 | 291.6 | 2.02 | 0.26 | 17.93 | 2 | 45.1 |
| **Mobile, BC7** | **1,302 / 1,297 / 1,251** | **203.8** | **1.23** | 0.23 | 17.88 | 0 | 40.3 |
| Forward+, PNG | 1,530 / 1,467 / 1,395 | 243.6 | 1.98 | 0.29 | 18.03 | 3 | 109.1 |
| Mobile, PNG | 1,435 / 1,491 / 1,343 | 280.2 | 1.15 | 0.23 | 18.04 | 5 | 104.3 |
| Forward+, nodes, BC7 | 1,643 / 1,710 / 1,524 | 303.5 | 1.98 | 0.32 | 17.89 | 0 | 45.1 |
| Mobile, nodes, BC7 | 1,259 / 1,256 / 1,296 | 205.1 | 1.27 | 0.30 | 17.97 | 6 | 40.3 |
| Forward+, fullscreen 1440p, 0.5 scale | 2,135 / 1,944 / 1,915 | 400.5 | 2.43 | 0.26 | 17.71 | 1 | 54.2 |
| Mobile, fullscreen 1440p, 0.5 scale | 1,702 / 1,616 / 1,652 | 392.2 | 1.70 | 0.23 | 17.65 | 0 | 49.4 |

- **GPU:** Mobile's GPU time is 30–42% lower in every pairing (36–42% at 1280×800). On a battery-powered handheld, that's headroom and power.
- **Start-up:**
  - Measured in the same session, Mobile reaches its first frame 50–450 ms sooner.
  - Our code is about 90–100 ms faster with BC7 (less pipeline compilation for the first frame). With PNG it's 37 ms slower.
  - Across sessions, start-up varies by about ±100–200 ms: the Mobile/nodes rerun at the end of the day gave 1,462–1,517 ms. So treat the start-up gain as "equal or better", not as a fixed number.
- **Frame pacing:** the same for both.
- **Visual parity:** the captures of the same view differ by a mean of 0.92/255 and a maximum of 4/255 per channel. The gradient corners are exact (#1B1F4A and #0B0B24) in both.
- **Features:** Mobile lacks SDFGI, VoxelGI, SSR, SSAO, SSIL and volumetric fog, and limits the omni and spot lights per mesh. The design uses none of these (A3: no shadows, GI, SSAO, SSR or glow; three directional lights).

**Recommendation: Mobile on D3D12.** Compatibility (OpenGL) wasn't benched on the grid. It had the fastest engine start-up on the scaffold scene, but it has no `RenderingDevice`, and `Texture2DArray` updates and the upload path would need re-measuring. It's not worth pursuing while Mobile meets every target.

## Docked: fullscreen and 3D render scale

Fullscreen on the attached display, at 2560×1440 and 59.94 Hz.

| Configuration | GPU (ms) | Mean / p99 / max (ms) | Hitches | Our code (ms) | Working set (MB) | GPU dedicated / shared (MB) |
|---|---|---|---|---|---|---|
| Forward+, native 2560×1440 | 6.45 | 16.68 / 17.70 / 21.19 | 0 | 449.0 | 460 | 81 / 249 |
| Forward+, 3D at 0.5 (1280×720), bilinear | 2.43 | 16.68 / 17.71 / 23.00 | 1 | 400.5 | 385 | 88 / 181 |
| Mobile, 3D at 0.5, bilinear | 1.70 | 16.68 / 17.65 / 23.34 | 0 | 392.2 | 382 | 79 / 163 |

- Fullscreen gave the cleanest pacing in the whole matrix: 1 hitch in 9 runs.
- Scaling by pixel count, native 3840×2160 on Forward+ would cost about 14.5 ms of GPU time (2.25 × 6.45). That's too close to the 16.68 ms budget.
- Mobile's native cost wasn't measured. Capping 3D at 1080p internal (0.5 scale at 4K), as A3 already plans, is supported by the data.
- **FSR1 against bilinear wasn't compared**, and **3840×2160 needs re-measuring** once the display runs at 4K.

## Hitches: what they are

Hitches were rare: 0–6 per 10,800 frames. For every scroll frame, the spike records the time before our `_Process`, the time inside it, and the time from its end to `frame_post_draw`, plus render CPU and GPU.

- **Periodic present delay:**
  - The worst frames recur every **~301 frames (5.02 s)** in every configuration, **including the no-texture control**: frames 503, 805, 1104, 1405, 1706, 2006 and so on.
  - In those frames, our `_Process` takes 0.02 ms, render CPU 0.2–0.3 ms and GPU about 2 ms. The extra 2–9 ms is all in the present and vsync wait ("after process").
  - It's outside our code. It could be DWM composition in windowed mode, the Steam client, or a driver or OS timer; PresentMon would tell (see R5).
  - **The GPU-counter polling in the bench script made it worse.** Without polling, the no-texture control and Forward+ MultiMesh BC7 had 1 and 0 hitches over 3 runs, against 4 and 2 with polling.
  - Fullscreen runs showed the same cadence, but it stayed under 22 ms.
- **Frames with upload bursts:** a few hitch frames spend 1.1–1.7 ms in `_Process`, because of several uploads in one frame, and then miss the vblank in present. Capping uploads per frame (see 2d) targets these.
- **Start-up:**
  - Frames 2–5 of many runs take 25–42 ms. These are the first texture uploads (single uploads of up to 43 ms) and first-use pipeline work.
  - They fall inside the "first 60 frames" that the acceptance criterion excludes. M5 should still warm this path during the post-`interactive` warm-up (A3).
- **Measurement artefact:** the longest frame in each whole-run bench report (40–65 ms, at frame about 3,685) is the spike writing its own JSON report on the main thread, at the end of the scroll. It isn't in the scroll statistics.
- **Outliers:** a 234.7 ms frame and a 73.9 ms frame in one configuration (Mobile/nodes, runs 3 and 2) didn't reproduce in the rerun. No cause was found.
- **GC:**
  - Worker allocations (Image wrappers, path strings) cause 4–7 gen0 collections per minute. The total GC pause per run is 6–11 ms, with no hitch coinciding.
  - The main thread allocated **0.6 KB in each 60 s scroll**, in every configuration. The 312 KB in the whole-run bench figure is the spike's own report writer.

## Performance targets: verdict and proposed changes

These are measured on the chosen configuration (Mobile, MultiMesh, BC7, windowed 1280×800), with the rest of the matrix in brackets.

| Target | Measured | Verdict | Proposal |
|---|---|---|---|
| Our code's start-up (`app_startup_ms`) under 1 s, warm, 10,000 games | 204 ms (186–449 ms; the highest is fullscreen 1440p Forward+) | **Met**, with more than 500 ms of headroom | Keep 1 s. M2 re-checks it with real config and `library.db` loading (A3 estimates about 15 ms). |
| 0 hitches after the first 60 frames in a 60 s scroll | 0 / 0 / 0 (0–6 per 3 runs across configurations; the no-texture control has 1–4 per 3 runs) | **Met by the chosen configuration, but not reliably reachable windowed**, because of the environment's periodic present delay | Reword it: *"No hitches caused by the launcher: over 3 × 60 s scrolls, hitches ≤ the no-texture control's in the same session, 0 frames over 2× the refresh interval, and 0 hitches in fullscreen."* |
| p99 ≤ 1.1× the refresh interval (18.35 ms) | 17.88 ms (17.65–18.34 ms) | **Met**, with a thin margin | Keep it. |
| Main-thread allocation ceiling during the scroll | 0.6 KB per 60 s scroll | Set by M1 | **Ceiling: 4 KB per 60 s scroll**, and no GC caused by the main thread. |
| *(new)* Visible grid textured after the first frame | 10 ms with BC7; about 100 ms with PNG or JPEG | — | **≤ 100 ms**, with derivatives in cache. |
| *(new)* Covers textured while scrolling at maximum repeat speed | 100.0% for every format | — | **≥ 99% of on-screen cell-frames.** |
| *(new)* Memory while browsing 10,000 games | 324–481 MB working set; the BC7 pool texture memory is 40–45 MB | — | **Working set ≤ 512 MB. Pool texture memory ≤ 64 MB with BC7.** |

## Risks

- **R1. No BC7 encoder in the export templates.** `Image.Compress` returns `Unavailable` in exports (measured). The shipped launcher therefore can't bake the recommended derivative. The options, for the owner to choose in M4:
  1. A managed BCn encoder package. This needs the owner's approval under the NuGet rule, and its BC7 encode time on the Deck must be measured.
  2. Our own encoder in Core. BC1 is simple. A decent BC7 encoder is substantial work.
  3. A GPU compute encoder through `RenderingDevice`, porting Godot's MIT-licensed Betsy shaders.
  4. Stay on JPEG derivatives (measured as viable) and accept 4× the VRAM and ~100 ms to texture the first screen.

  The spike's BC7 files came from the editor binary.
- **R2. Disk footprint.** BC7 derivatives take 3.26 GB per 10,000 covers at 512², against 0.62 GB for JPEG. CacheDir is regenerable, but this matters on a 64 GB Deck, or with CacheDir on microSD, whose read speed is untested. If needed, a 384² or BC1 option reduces it.
- **R3. Cold cache.** Measured runs read warm files. A first pass costs 1.1–1.6 ms per BC7-class cover, which is still well over 166 covers/s with 2 workers. But microSD and spinning disks are untested.
- **R4. Untested modes.** The handheld panel (undocked, 1280×800 fullscreen) and 3840×2160 docked weren't measured. The 1280×800 windowed runs have the same pixel count as handheld, but not the same presentation path.
- **R5. The periodic 5 s present delay isn't explained.** It's the main threat to a strict "0 hitches". PresentMon would identify it, and installing it needs the owner's approval.
- **R6. `Texture2DArray` constraints.**
  - Every layer must match in size and format, so the canonical derivative size is fixed per array.
  - The layer count is fixed at creation, so a larger pool (for example, more columns when docked) means recreating the array.
  - Custom `.glb` models need the node path.
- **R7. Main-thread texture creation stalls for 17–66 ms**, and so does the first `UpdateLayer`. Everything must be created and warmed at boot, or on a worker.
- **R8. Start-up measurements are noisy.** The same configuration moved 100–200 ms between sessions. Compare start-up only within one session, and use 5 runs for sign-off numbers.
- **R9. What the spike simplified:**
  - synthetic art
  - no config or DB loading
  - a fixed 8 columns and one template mesh
  - no custom models
  - no full-resolution focus upgrade
  - no LRU beyond the pool
  - Real covers vary in aspect ratio and need centre-cropping into the square derivative.
- **R10. Worker allocations.** The streamer allocated an `Image` wrapper, a path string and a `FileInfo` per cover on the workers. Production code should cache paths per binding, to keep gen0 collections rare.

## Not covered by this spike

The roadmap's M1 scope also lists the items below. They weren't part of this spike, and the roadmap now tracks them under later milestones:
- Tomlyn and Microsoft.Data.Sqlite, and the config-parse and SQLite native-load measurements (M2)
- the 20-system synthetic library and the `boot` scenario (M2)
- ReadyToRun and the shader baker (M5)
- the net10.0 comparison build (M2)
- `.glb` conversion on a worker thread (M6)
- handheld mode, 3840×2160, FSR1 against bilinear, and PresentMon (M5)

## Reproducing

These commands run from the repo root, on branch `spike/grid-perf`. They need the Godot 4.7.2 editor (for generation) and the export templates.

```powershell
# 1. Generate the library (editor binary: BC7/BC1 encoding only works there). About 34 min, 18.6 GB.
godot --headless --path godot -- "--spike-generate=$PWD/artifacts/spike-library" --spike-count=10000

# 2. Export, then run every configuration (3 runs plus a warm-up each) and the load tests. About 2 h.
godot --headless --path godot --export-release "Windows Desktop" $PWD/artifacts/export/windows/OdysseyLauncher.exe
.\godot\spikes\run-matrix.ps1

# One configuration:
.\godot\spikes\bench-spike.ps1 -Label mobile-mm-bc7 -EngineArgs '--rendering-method', 'mobile' -SpikeArgs '--spike-render=multimesh', '--spike-format=dds-bc7'

# 3. Tables from artifacts/spike-bench/*/summary.json:
.\godot\spikes\summarise.ps1

# Interactive (arrow keys or D-pad, with hold-to-repeat):
godot --path godot -- "--spike-library=$PWD/artifacts/spike-library" --spike-render=multimesh --spike-format=dds-bc7
```

The spike's user arguments are:
- `--spike-render=nodes|multimesh`
- `--spike-format=png|jpg|dds-bc7|dds-bc1|ktx-bc7|res-bc7|raw-bc7`
- `--spike-workers=N` and `--spike-upload-kb=N`
- `--spike-scroll-seconds=S` and `--spike-scroll-rows=N`
- `--spike-autoscroll` and `--spike-start-row=N`
- `--spike-3d-scale=F` and `--spike-fsr`
- `--spike-no-textures`
- `--spike-loadtest=FILE.json` and `--spike-loadtest-items=N`

With `--bench`, the spike writes `<bench>.spike.json` next to the bench report.
