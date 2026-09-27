# Odyssey Launcher

A fully 3D game launcher frontend (systems grid → games grid → emulator), styled after the PS2 memory card browser. It's built with Godot 4.7 .NET and C#, for Windows first, Linux later if cheap, and never macOS. **Performance is the headline feature.**

- The design is in `docs/ARCHITECTURE.md`. Add to its decisions log whenever a decision changes.
- Milestones and acceptance criteria are in `docs/ROADMAP.md`. Update its **Progress** section at the end of every milestone.

## Layout

| Path | What |
|---|---|
| `src/Launcher.Core/` | Plain .NET class library: config, DBs, scanning, scraping, launching, platform, diagnostics. **No Godot reference.** |
| `tests/Launcher.Core.Tests/` | xUnit v3 tests for Core. |
| `godot/` | The Godot project. `OdysseyLauncher.csproj` references Core. C# scripts live in `godot/src/`, in namespace `Launcher.App`. |
| `tools/verify.ps1` | Runs every non-windowed check. |

## Commands (PowerShell, repo root)

| Command | Does |
|---|---|
| `dotnet build` | Builds the whole solution (`OdysseyLauncher.slnx`). |
| `dotnet test` | Runs the tests on Microsoft.Testing.Platform (selected in `global.json`). |
| `godot --headless --path godot --build-solutions --quit` | Godot's own C# build. Exits 1 if it fails. |
| `godot --headless --path godot --import` | Imports assets and generates the `.uid` and `.import` files. Commit those files. |
| `godot --headless --path godot --quit-after 10` | Smoke run. Prints the `Launcher.Core ...` line. |
| `.\tools\verify.ps1` | All of the above, in order. |
| `godot --path godot` | Runs the app windowed. Use `godot --path godot -e` for the editor. |

`godot` is `C:\Users\claudio\Coding\Godot\godot.cmd`. It forwards to the 4.7.2 .NET console build, which waits for exit and passes the exit code through.

## Debug facilities (windowed only: headless mode doesn't render)

Use these to check your own work. Look at captures with the Read tool, and compare bench JSON before and after a change.

```powershell
godot --path godot --resolution 1280x800 --fixed-fps 60 -- --capture=$PWD/artifacts/shot.png --capture-frame=60
godot --path godot --resolution 1280x800 -- --bench=$PWD/artifacts/bench.json --bench-frames=600
```

- **`--capture`** saves a PNG of the viewport after n drawn frames (`--capture-frame`, default 60), then quits.
- **`--bench`** samples n frame intervals after the first drawn frame (`--bench-frames`, default 600), writes JSON, then quits. The JSON contains:
  - `startup_ms`: ms since the process started, with `engine_start`, `autoload_enter_tree`, `main_ready`, `first_frame_drawn` and `interactive`.
  - `frames`: mean, p50, p95, p99, max, `hitch_count` (over 1.5× the refresh interval) and the worst frames.
  - `render_ms`: render CPU and GPU times.
  - `gc`: GC activity, including `main_thread_allocated_bytes`.
- User arguments go after `--`. Use `++` instead if a shell swallows `--`.
- **Paths must be absolute.** With `--path`, Godot changes the working directory into `godot/`, and a PNG saved there would be imported as an asset. `artifacts/` is gitignored.
- Use `--fixed-fps 60` for captures, so animation is deterministic. **Never** use it with `--bench`.
- Don't combine `--capture` with `--bench` for measurements, because the PNG write shows up as one long frame.
- Exit codes: 0 means success; 1 means a failure, including a headless run or a watchdog timeout (30 s plus 100 ms per requested frame); 2 means invalid debug arguments.
- Timings from the editor binary with Debug assemblies aren't comparable with the performance targets. M1 adds exported-build benchmarks.

## Decided stack (don't change without asking)

- Godot 4 .NET edition with C#. Use Godot 4 C# APIs only, and check their signatures against https://docs.godotengine.org/en/stable/. Godot 3 examples are wrong: for example `Spatial` is now `Node3D`, `yield` is now `await ToSignal(...)`, and string-based `Connect` is now C# events or `Callable`.
- Target frameworks follow what Godot generates, which is net8.0 for 4.7.2. Bump every project together.
- TOML via Tomlyn. Config files are the source of truth for user intent.
- SQLite via Microsoft.Data.Sqlite, in WAL mode, with versioned migrations. `library.db` must be rebuildable from config, disk and scrapers. User data that can't be rebuilt goes in `userdata.db`.
- Media lives on disk, and the DB stores relative paths only.
- 3D models are glTF 2.0 `.glb` only.
- Platform-specific code (paths, processes, window focus) lives only in `src/Launcher.Core/Platform`, behind interfaces.

## Rules

- **Ask before adding any NuGet package**, including test and analyser packages.
- **Never commit credentials.** API keys and passwords live only in the user's `secrets.toml` or in `ODYSSEY_*` environment variables. Never put them in the repo, tests, logs or bench output.
- Launcher.Core must never reference Godot. `ArchitectureTests` enforces this.
- The Godot main thread must never do file, network or DB I/O, never decode images, and never call `.Wait()` or `.Result`. Never touch the scene tree from another thread.
- No allocations in per-frame code (`_Process`, grid updates, `frame_post_draw` handlers). That means no LINQ, closures, boxing, string formatting, or implicit `string`→`StringName` conversions. Cache every `StringName` and `NodePath`.
- For a performance-sensitive change, run `--bench` before and after, and quote both results.
- For a visual change, run `--capture` and look at the PNG.

## Conventions

- Godot script classes are `partial`, and each file is named after its class (Godot requires this).
- The Godot project has no ImplicitUsings, because `Godot.Environment` clashes with `System.Environment`.
- In Core, every `await` uses `ConfigureAwait(false)`. CA2007 is an error in `src/`.
- Warnings are errors in Core and in the tests.
- File-scoped namespaces. Core namespaces mirror its folders (`Launcher.Core.Diagnostics`, ...).
- A schema change means a new numbered migration file. Never edit a shipped migration.
- Tests never touch the network. Scraper tests use recorded fixtures.
- Use UK English in docs, comments, UI text, our own identifiers and our config keys (`favourite`, `colour`). External names keep their own spelling (Godot `Color`, glTF `baseColorTexture`).
