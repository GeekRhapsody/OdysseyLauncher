# Odyssey Launcher

A fully 3D game launcher frontend (systems grid → games grid → emulator), styled after the PS2 memory card browser. It's built with Godot 4.7 .NET and C#, for Windows first, Linux later if cheap, and never macOS. **Performance is the headline feature.**

- The design is in `docs/ARCHITECTURE.md`. Add to its decisions log whenever a decision changes.
- Milestones and acceptance criteria are in `docs/ROADMAP.md`. Update its **Progress** section at the end of every milestone.
- The guide for theme authors is `docs/THEMING.md`. Keep it in step with the manifest, the slots, the model spec and the budgets.

## Layout

| Path | What |
|---|---|
| `src/Launcher.Core/` | Plain .NET class library: config, DBs, scanning, scraping, launching, platform, diagnostics. **No Godot reference.** |
| `tests/Launcher.Core.Tests/` | xUnit v3 tests for Core. |
| `tests/FakeEmulator/` | A console app the launch tests run as a stand-in emulator. It logs its arguments, sleeps, exits with a chosen code, and can act as a stub launcher (options in its `Program.cs`). |
| `godot/` | The Godot project. `OdysseyLauncher.csproj` references Core. C# scripts live in `godot/src/`, in namespace `Launcher.App`. |
| `src/Launcher.Core/Defaults/` | The built-in `settings.toml`, `systems.toml` and `emulators.toml`, embedded in Core: the original 14 systems, then ES-DE's catalogue (docs/ARCHITECTURE.md A5, "The ES-DE catalogue"), with Windows and Steam ("Windows and Steam games"). Keep them plain TOML (tables, bare keys, strings, numbers, booleans, single-line arrays): `TomlFast` reads them and `TomlFastTests` checks it builds Tomlyn's tree. |
| `src/Launcher.Core/Data/Migrations/` | Numbered SQL migrations for `library.db` and `userdata.db`, embedded in Core. |
| `tools/verify.ps1` | Runs every non-windowed check. |
| `.github/workflows/release.yml` | The Windows release (docs/ARCHITECTURE.md decisions log, 2026-10-01): on a pushed `v<version>` tag it builds, tests (not the benchmarks), exports on the runner's software GPU (WARP), runs the launch smoke test on the export, and attaches `OdysseyLauncher-<version>-windows-x86_64.zip` to the tag's release. Run by hand (Actions > Release), it's a test build kept as the run's artifact. |
| `tools/launch-smoke.ps1` | Runs the app with `--launch` against the fake emulator, in an isolated user folder. |
| `docs/manual-tests.md` | Checks a script can't observe (window focus with a real emulator). |
| `tools/core-bench/` | Times Core's config, scan and query paths on self-contained .NET 8 (the export's runtime). Not in the solution. |
| `tools/synthetic-library/` | Writes a portable user folder with 20 systems and 14,215 games (10,000 on PS2), with covers and BC7 derivatives hardlinked from the M1 spike library (`artifacts/spike-library`). `--games`, `--others`, `--slots=back,spine,...` (art for more slots) and `--models=<n>` (that many PS2 games get a per-game model) make other libraries. Not in the solution. |
| `tools/bench-summary.py` | One line per bench run (scroll, textures, memory) from `artifacts/bench/<folder>`. |
| `tools/scrape-cli/` | `odyssey-scrape`: every scraping operation from the command line (`providers`, `game`, `system`, `missing`, `clear`, `show`, `resume`, `bake`, `scan`, `ss-systems`), for live tests with the owner's credentials, and the model commands (`import-model`, `remove-model`, `inspect-model`, `models-log`; no network). In the solution. |
| `tests/Launcher.Core.Tests/Scraping/Fixtures/` | Recorded provider responses. Credentials appear as `{{DEVPASSWORD}}`-style placeholders, which the tests' fake HTTP handler fills with fake values. |
| `godot/themes/memory-card/` | The built-in theme: `theme.toml` (looks, templates and each built-in system's colour and template, and the look of the first 14) and its models. Every other theme falls back to it. |
| `tests/themes/` | Themes for tests and captures (`slot-showcase`: a game template with three slots). Copy one into a user folder's `themes/` to use it. |
| `samples/themes/retro-tv/` | The sample theme for theme authors (`docs/THEMING.md`): a CRT television game template (screenshot screen, logo plate, focused and launch clips) and a console system model (idle clip). A user theme: copy it into a user folder's `themes/`. |
| `godot/src/Tools/`, `godot/scenes/tools/` | The `[Tool]` generator for the built-in models; its output is `godot/themes/memory-card/models/{templates,systems}/*.glb`, plus the test theme's `tests/themes/slot-showcase/models/` and the sample theme's `samples/themes/retro-tv/models/`. Excluded from exports. |

## Commands (PowerShell, repo root)

| Command | Does |
|---|---|
| `dotnet build` | Builds the whole solution (`OdysseyLauncher.slnx`). |
| `dotnet test` | Runs the tests on Microsoft.Testing.Platform (selected in `global.json`), including the scan benchmarks (about 12 s; they run alone, after the parallel tests). |
| `.\tests\Launcher.Core.Tests\bin\Debug\net8.0\Launcher.Core.Tests.exe -trait "Category=Benchmark" -showLiveOutput` | Runs only the benchmarks and prints their timings. |
| `dotnet publish tools/core-bench -c ExportRelease -o artifacts/core-bench` then `artifacts/core-bench/core-bench.exe $PWD/artifacts/core-bench-work` | Core timings on the export's runtime. **Use this for any Core number you compare with a target** (results in `docs/perf/m2-core.md`). |
| `godot --headless --path godot --build-solutions --quit` | Godot's own C# build. Exits 1 if it fails. |
| `godot --headless --path godot --import` | Imports assets and generates the `.uid` and `.import` files. Commit those files. |
| `godot --headless --path godot --quit-after 10` | Smoke run. Prints the `Launcher.Core ...` line. |
| `.\tools\launch-smoke.ps1` | Headless `--launch` of the fake emulator; checks the exit code, arguments and working folder. `-Windowed` shows the window, `-SleepMs` sets the play time, and `-Executable artifacts/export/windows/OdysseyLauncher.exe` runs the export. Needs `dotnet build` first. |
| `.\tools\verify.ps1` | All of the above, in order. |
| `godot --path godot` | Runs the app windowed. Use `godot --path godot -e` for the editor. |
| `godot --path godot --export-release "Windows Desktop" $PWD/artifacts/export/windows/OdysseyLauncher.exe` | Exports an ExportRelease build (the preset is in `godot/export_presets.cfg`). **Not `--headless`:** the shader baker needs a rendering device, and a headless export silently bakes nothing (a 49 KB PCK instead of about 2.6 MB). |
| `.\tools\bench-export.ps1` | Exports, then runs one warm-up plus 5 benched runs of the export and prints the medians. Options: `-SkipExport`, `-Runs`, `-Frames`, `-Resolution`, `-Fullscreen`, `-EngineArgs '--rendering-driver', 'vulkan'`, `-Label`, `-AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll'`, `-TimeoutSeconds`, `-Executable` (another export, to bench two builds side by side). **Use this for any number you compare with a target**, with nothing else running on the machine. |
| `godot --headless --path godot res://scenes/tools/generate_box_templates.tscn` | Regenerates the built-in theme's models, the test theme's and the sample theme's (deterministic), then `--import`. Commit the `.glb` and `.import` files. `BuiltInModelTests` and `ModelInspectorTests` check them against the model spec and budgets. |
| `dotnet run --project tools/synthetic-library -c ExportRelease -- "--out=$PWD\artifacts\synthetic" "--covers=$PWD\artifacts\spike-library"` | The synthetic library, for `--user-dir`. About 50 s. M6's 3,000-game library with art for four more slots: `"--out=$PWD\artifacts\synthetic-3000" ... --games=2620 --others=20 --slots=back,spine,screenshot,logo`, then copy `tests/themes/slot-showcase` (and `samples/themes/retro-tv`) into its `themes/`. Add `--models=300` for 300 per-game models (M6 part 2 used `artifacts\synthetic-3000-models`). |
| `.\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe [--user-dir=<folder>] <command>` | Scraping by hand (`help` lists the commands). Without `--user-dir` it uses the app's AppData folders. **Don't run a live scrape yourself:** it needs the owner's credentials, and it's the owner's manual test (`docs/manual-tests.md`). `providers`, `scan`, `show`, `bake` and the model commands make no network calls. `import-model --from=<file> <system>/<rel path>` imports a game's model; `inspect-model [--kind=template|system] <file>` checks one. |
| `python tools/bench-summary.py "artifacts/bench/*-<label>"` | Per-run summary of bench folders. |
| `git tag v<version>` then `git push origin v<version>` | Releases that version. `<version>` must be `Version` in `Directory.Build.props` and `config/version` in `godot/project.godot` (bump both first), or the workflow stops; a version with a `-` (`0.2.0-beta.1`) is a pre-release. |

`godot` is `C:\Users\claudio\Coding\Godot\godot.cmd`. It forwards to the 4.7.2 .NET console build, which waits for exit and passes the exit code through.

## Debug facilities (windowed only: headless mode doesn't render)

Use these to check your own work. Look at captures with the Read tool, and compare bench JSON before and after a change.

```powershell
godot --path godot --resolution 1280x800 --fixed-fps 60 -- --capture=$PWD/artifacts/shot.png --capture-frame=60
godot --path godot --resolution 1280x800 -- --bench=$PWD/artifacts/bench.json --bench-frames=600
```

- **`--capture`** saves a PNG of the viewport after n drawn frames (`--capture-frame`, default 60), then quits.
- **`--bench`** samples n frame intervals from `interactive` (`--bench-frames`, default 600), writes JSON, then quits. The JSON (format 2) contains:
  - `app_startup_ms`: **our code's start-up**, from the first autoload's `_EnterTree` to `interactive`. The 1 s target applies to this number only. Engine and .NET start-up before it is excluded.
  - `startup_ms`: ms since the process started, with `engine_start`, `autoload_enter_tree`, `main_ready`, `first_frame_drawn` and `interactive`.
  - `frames`: mean, p50, p95, p99, max, `hitch_count` (over 1.5× the refresh interval) and the worst frames.
  - `render_ms`: render CPU and GPU times.
  - `gc`: GC activity, including `main_thread_allocated_bytes`.
  - `scenario`, `options`, `library`, `memory`, and in the scroll scenario `scroll` (the scroll frames alone, textured fraction, main-thread allocation) and `textures`.
- **`--bench-scenario=scroll`** enters the biggest system (or `--bench-system=<id>`) and scrolls from the first row to the last in `--bench-scroll-seconds` (default 60, the M1 rate). **`--no-textures`** is the control the hitch target is compared with, in the same session.
- **`--render-scale=<0.25–1>`** and **`--upscaler=bilinear|fsr`** override the automatic cap of 1080p for 3D (FSR1 needs Forward+). **`--upload-cap=<n>`** sets the cover-sized uploads per frame (default 4, a 256² slot layer counting a quarter; 0 = no cap).
- **`--start-system=<id>`** (with **`--start-index=<n>`**) enters a system once interactive, and **`--nav-script=down,right,accept,back,...`** plays navigation commands through the controller's path, one every 30 frames, logging each (`Nav script:`). Use them with `--capture` for transitions, focus and screens. The steps `theme` (the next theme, applied without a restart) and `rescan` (every system, from any screen) exercise theme switching and media rebinding. `menu` is Menu (it opens and closes the settings), `power` is View (the power menu: never `accept` a row in it but Quit app, which is last), `x` is X (in the grids, the focused system's or game's options: M7 part 2) and `favourite` is Y; while a settings screen or options panel is open, the steps go to it. Unknown steps (`wait`) do nothing, for giving a save or a load time to finish. `click` (the left button on the focused control), `scroll` (the wheel, three notches) and `type` (the keys "Ok 1") send real mouse and keyboard events.
- **`--open=settings|keyboard|folder-picker|image-picker|program-picker|confirm|progress|power|match`** shows a settings screen or shared component once interactive (M7), with **`--open-path=<folder>`** for where a picker starts. `progress` makes a job with made-up numbers, for its card. `match` shows the manual-match panel ("scrape this game") over made-up results for `--start-system`'s game at `--start-index`; nothing is searched or scraped. Captures that save settings should use a copy of a library's config (`--user-dir`), not a bench library.
- **`--theme=<id>`** uses that theme instead of settings.toml's `[display] theme` (a user theme must be in the user folder's `themes/`). **`--no-overlay`** hides the text overlay, whose scrims darken the screen's top and bottom, so a capture shows a look's corners (exact on Forward+, within 2/255 on Mobile: ARCHITECTURE.md A6).
- **`--launch=<system>/<rel path>`** launches that game once the app is interactive, scanning the system first if the game isn't in the library. It works headless too.
  - **`--user-dir=<folder>`** keeps config, data and cache in that folder (the portable layout), instead of AppData.
  - **`--quit-after-launch`** quits once the game has ended: exit code 0 if it ran, 1 if the launch failed.
  - The log lines start with `Launch`, including the exact command line, how the launcher minimised, and how it got the foreground back.
  - **Don't run a windowed `--launch` of a real emulator yourself:** it minimises the app and takes the foreground back from the owner's desktop (possibly with a synthetic Alt key). That's the owner's manual test.
- User arguments go after `--`. Use `++` instead if a shell swallows `--`.
- **Paths must be absolute.** With `--path`, Godot changes the working directory into `godot/`, and a PNG saved there would be imported as an asset. `artifacts/` is gitignored.
- Use `--fixed-fps 60` for captures, so animation is deterministic. **Never** use it with `--bench`.
- Don't combine `--capture` with `--bench` for measurements, because the PNG write shows up as one long frame.
- Exit codes: 0 means success; 1 means a failure, including a headless run or a watchdog timeout (30 s plus 100 ms per requested frame); 2 means invalid debug arguments.
- Timings from the editor binary with Debug assemblies aren't comparable with the performance targets. Use `tools/bench-export.ps1` for those.
- Libraries for runs: `--user-dir=$PWD/artifacts/synthetic` (see above), or a user folder whose `systems.toml` points `rom_dirs` at the owner's NAS (`S:\`, read only; see docs/perf/m5-navigation.md). The app scans systems never scanned in the background, except in benches.
- `DebugHooks` must stay the **first autoload**, because `app_startup_ms` is timed from its `_EnterTree`. It warns if it isn't first.

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
- Tests never touch the network. Scraper tests use recorded fixtures through `FakeHttpHandler`, which fails a test on any request it has no route for. Waits go through the injected `Delay`, which advances a test clock instead of sleeping.
- `Redactor` masks credentials before anything is logged or saved. Provider code must never put a URL or header into a message unredacted.
- Use UK English in docs, comments, UI text, our own identifiers and our config keys (`favourite`, `colour`). External names keep their own spelling (Godot `Color`, glTF `baseColorTexture`).
- Don't rewrite source files with Windows PowerShell's `Get-Content`/`Set-Content`: it reads UTF-8 without a BOM as ANSI and mangles non-ASCII characters. Use the editor tools, or Python with `encoding='utf-8'` and LF line endings.
