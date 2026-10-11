# Game videos and the 1990s television: checks and measurements

Measured on 11 October 2026 on the development machine, windowed at 1280×800 (59.94 Hz), with nothing else running.

- Builds are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on.
- **Before** is commit `418adf7`, exported to `artifacts/export-before/windows/`. **After** is the change, exported to `artifacts/export/windows/`.
- One warm-up and 5 benched runs per series (3 for PSX, 2 for the looping video); the tables give the medians, with ranges where the runs spread. The JSON is in [game-videos/](game-videos/), and the captures in [game-videos/captures.jpg](game-videos/captures.jpg): the grid with the focused TV playing its video; that TV inspected (R3); the grid half a second after moving right (the first TV shows its screenshot again, the second hasn't started yet); a TV inspected with a tall screenshot boxed on its dark tube.
- The design is in [ARCHITECTURE.md](../ARCHITECTURE.md) (A6, "Game videos"; A7, "The television"; and the decisions log, 2026-10-11).

The library is `artifacts\synthetic-video`, a copy of `artifacts\synthetic-genbox` (2,620 PS2 games, each with a cover, back, spine, screenshot and logo, and 380 other games), its `systems.toml` given `[systems.ps2] game_model = "crt_tv_90s"`, and the first 200 PS2 games (by title) given a video in `library.db`: one file, `testsrc2` at 640 × 480, 30 frames a second, 30 s, H.264 4:2:0 with a key frame a second, and a 440 Hz tone, AAC stereo at 44.1 kHz, 6 MB, made with ffmpeg; the third game's video is a 2 s, 320 × 240 one with a 48 kHz tone, for the loop. The before build doesn't know `crt_tv_90s`, so its PS2 games use their default template, the DVD case.

```powershell
$u = "--user-dir=$PWD\artifacts\synthetic-video"
# The focused game held for 40 s: index 0 has a video, 300 none.
.\tools\bench-export.ps1 -SkipExport -Executable <build> -Frames 2400 -Label <series> -AppArgs $u, '--start-system=ps2', '--start-index=0'
# A system the TV isn't used on, held and scrolled.
.\tools\bench-export.ps1 -SkipExport -Executable <build> -Runs 3 -Frames 1200 -Label <series> -AppArgs $u, '--start-system=psx', '--start-index=0'
.\tools\bench-export.ps1 -SkipExport -Executable <build> -Runs 3 -Label <series> -AppArgs $u, '--bench-scenario=scroll', '--bench-system=psx'
```

## What changed per frame

- **Every item's fragments on a slot face:** one comparison of the face's slot and cell against a uniform (`video_state`), which matches nothing unless a video plays. No new shader variant.
- **The games grid, once a frame:** `UpdateGameVideo` reads the focused cell, its model and the time it's been focused. Nothing allocates.
- **While a video plays:** its decoding thread decodes a few frames ahead; the main thread pushes the sound to an `AudioStreamGenerator` and uploads each new frame once (`ImageTexture.Update`), and the fragments of the focused game's slot face sample one more texture.
- **Once per video, and once each time it loops:** a `VideoPlayback` (a thread, four frame images, a sound ring) and an `AudioStreamGenerator` are made: a few KB of main-thread allocation.
- **Memory:** nothing until a video plays; then Media Foundation's decoder, the frames and the sound ring. Games' videos are read with the list only when a template the theme uses plays them: one `MediaRef` per game.

## Results

**The same 40 s, the first PS2 game focused,** all three series back to back in one session: before (the DVD case), after with the game focused that has no video (index 300: the TV showing its screenshot), and after with the game that has one (index 0: its video starts about 1.3 s in and plays to the end).

| | Before, DVD case | After, TV, no video | After, TV, video |
|---|---|---|---|
| Frame p99 | 18.33 ms (18.25–18.34) | 18.22 ms (18.13–18.33) | 18.21 ms (18.12–18.22) |
| Hitches (over 25 ms) | 3 (1–3) | 4 (3–4) | 3 (2–5) |
| Render CPU, mean | 0.40 ms (0.37–0.46) | 0.35 ms (0.34–0.36) | 0.52 ms (0.52–0.55) |
| GPU, mean | 1.19 ms | 2.00 ms | 1.84 ms |
| Working set at the end | 590 MB | 590 MB | 643 MB (640–644) |
| Texture memory | 256.27 MB | 256.36 MB | 258.86 MB |
| Video memory | 298.0 MB | 298.5 MB | 301.6 MB |
| Managed heap | 14.1 MB | 14.4 MB | 18.6 MB |
| Main-thread allocation, whole run | 398 KB | 395 KB | 411 KB (411–477) |

- **Frames:** the same in all three: vsync-bound at 16.67 ms mean, the same p99 and hitches. The long frames are the start (frame 0) and entering the system (about frame 20) in every series; none falls where the video starts (about frame 80).
- **The video's cost** (the last column against the middle one): render CPU +0.17 ms a frame, working set +53 MB (the decoder, as the card video's 53 MB), textures +2.5 MB, video memory +3.1 MB, the managed heap +4 MB (the sound ring and the frame buffer), 16 KB more main-thread allocation over the run, once.
- **The TV against the DVD case** (the first two columns): the GPU's 0.8 ms more is the TV's size on screen (its fragments cover more of each cell, and the cells' screens are 4:3), not the shader: on PSX below the GPU time is the same. Texture memory is 0.09 MB more: the TV's palette and dark tube.

**Looping,** a 2 s, 320 × 240 video looping about 19 times in 40 s (after only, 2 runs): p99 18.37 ms, hitches 2–3, textures 258.24 MB and video memory 299.4 MB at the end, no more than one 30 s video's, so an ended playback's frames are freed; main-thread allocation 432 KB, 37 KB more than no video over 19 loops (about 2 KB a loop). A 20 s run (about 9 loops) ended with textures at 259.0–259.7 MB: a playback's last texture is freed a little after the next takes over, so the number moves with when the run ends, not with the loops.

**A system the TV isn't used on** (PSX, 3 runs each, back to back), so only the shader's comparison and the grid's per-frame check differ:

| | Before, held | After, held | Before, scroll | After, scroll |
|---|---|---|---|---|
| Frame p99 | 18.33 ms | 18.37 ms | 18.21 ms (scroll frames) | 18.26 ms (scroll frames) |
| Hitches | 2 | 4 (2–4) | 1 (0–2) | 1 (1–2) |
| Render CPU | 0.38 ms | 0.37 ms | 0.39 ms | 0.38 ms |
| GPU | 1.24 ms | 1.28 ms | 1.25 ms | 1.27 ms |
| Working set | 586 MB | 587 MB | 584 MB | 586 MB |
| Texture memory | 256.27 MB | 256.36 MB | 256.27 MB | 256.36 MB |
| Scroll main-thread allocation | | | 96 bytes | 96 bytes |

The same within the runs' spread.

**The PS2 scroll** (60 s, 2,620 games, in separate sessions, so only the frames compare): before on the DVD case, scroll p99 19.38 ms (18.90–19.62) and 5 hitches; after on the TV, 18.31 ms (18.20–18.35) and 1; both 96 bytes of main-thread allocation, everything textured. The focus moves every 0.11 s, so no video starts while scrolling.

## Checks

- `verify.ps1`: 930 tests passed. The new ones check the keys, their errors and warnings, an extension keeping its base's video, and a video on a slot the model lacks.
- `inspect-model --kind=template` on `crt_tv_90s.glb`: accepted, 782 triangles (budget 2,000), 2 materials, 2 textures (64² and 128²), the `screenshot` slot, no clips; 1 × 0.868 × 0.743.
- Captures (editor build, `--fixed-fps 60`): before the delay the focused TV shows its screenshot; after it, the video fills the 4:3 tube; moving right puts the first TV's screenshot back at once and the second's video starts a second later; moving back starts the first again; opening the settings over a playing video and closing them leaves the screenshot showing until the delay has passed again; the 2 s video's counter reads 0 again after several loops; a tall screenshot is boxed on the dark tube; a game with no art shows the dark tube.
- Not checked: the sound, by ear (it goes through the details screen's player, which plays it).
