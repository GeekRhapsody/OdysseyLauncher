# M3 launching: measurements

Measured on 28 September 2026 on the baseline Steam Deck (AMD Custom APU 0405, Windows 11 build 26200; the machine in [m1-spike.md](m1-spike.md#machine)). The acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m3-launching).

## Start-up and frames: before and after M3

M3 adds a `LaunchController` node to the main scene. The question was whether it costs anything at boot or per frame.

```powershell
# "Before": a worktree at the M2 commit (0e28505), exported and benched from there
git worktree add --detach artifacts/worktree-before HEAD
godot --headless --path artifacts/worktree-before/godot --import
.\artifacts\worktree-before\tools\bench-export.ps1 -Runs 5 -Frames 300 -Label m3-before

# "After", from the M3 working tree
.\tools\bench-export.ps1 -Runs 5 -Frames 300 -Label m3-after
```

ExportRelease on .NET 8.0.31, Forward+/D3D12, 1280×800 windowed, 59.94 Hz, the scaffold scene, 300 frames a run. Medians of 5 warm runs; the rows in each group were benched back to back in one session.

**Final pair** (JSON in [m3/](m3/)):

| Build | Our code's start-up (ms) | Frame mean (ms) | Frame p99 (ms) | Hitches per run | Main-thread allocation per run |
|---|---|---|---|---|---|
| Before (M2, `0e28505`) | 129.1 (122.9–138.0) | 16.61 | 20.66 | 0–1 | 216 B, no GCs |
| After (M3 as committed) | 135.5 (127.5–138.4, and one 251.2) | 16.62 | 20.70 | 0–1 | 216 B, no GCs |

The ranges overlap. At boot the committed build runs the same code as M2 apart from one static assignment, because the controller isn't built until the first launch (below). An earlier pair in the same session gave 118.2 ms before and 123.2 ms after.

**How the controller got there** (earlier runs, same session):

| Build | Our code's start-up (ms) | Main-thread allocation per run |
|---|---|---|
| Controller built in `Main._Ready`, `_Input` always on | 141.9 (138.6–148.8) | **576–596 KB** |
| Controller built in `Main._Ready`, input processing only while blocked | 134.2 (130.2–146.8) | 216 B |
| Controller built on first launch (committed) | 123.2 (120.4–140.6) | 216 B |

- **Input processing.** Godot turns on input processing for any script that defines `_input`, and every event that reaches C# allocates a managed wrapper. The Deck's built-in controls send joypad motion constantly, so an always-on `_Input` cost about 1.9 KB per frame on the main thread: over the 4 KB per 60 s ceiling (A3) within the first few frames. The controller now enables input processing only while it's swallowing input, and turns it off at the first event after that.
- **Building it at boot** cost 10–24 ms of our start-up (the node, its timers and label, and JIT for it and the platform code). Nothing needs it before the first launch, so it's built then. M5 should build it during the post-`interactive` warm-up.
- **Frames** are unchanged throughout: the controller has no `_Process`, and does nothing per frame.

## The launch path

`tools/launch-smoke.ps1` runs the app with `--launch` against `tests/FakeEmulator`, headless, in an isolated `--user-dir`: config load, library open and scan, the job-object runner, the fake's arguments and working folder (under a path with spaces, `üé` and `日本`), and the play session. It passes in the editor run (.NET 10.0.12) and in the export (.NET 8.0.31):

```powershell
.\tools\launch-smoke.ps1
.\tools\launch-smoke.ps1 -Executable artifacts/export/windows/OdysseyLauncher.exe
```

That also shows **Microsoft.Data.Sqlite's native library loads in both the editor run and the export**, which M2 left for M5. Its load time inside Godot still isn't measured (M5).

In the Core tests, a launch of the fake emulator takes about 100–200 ms from `LaunchAsync` to `Running`, most of it the fake's own .NET start-up.

## Not measured

- **The launcher's CPU and GPU use while a game runs.** In game mode the render loop is off, the main loop idles at 10 iterations a second in low-processor mode, and the tree is paused, so it should be near zero. Measuring it needs a windowed launch that minimises the launcher and then takes the foreground back from whatever is in front, including a synthetic Alt key press if Windows refuses the gentler requests. That would interfere with the owner's desktop, so it's part of the owner's manual test (ROADMAP.md, M3 log), with a command to sample the CPU time.
- **Focus.** It can't be observed from a script; the same manual test covers it.
