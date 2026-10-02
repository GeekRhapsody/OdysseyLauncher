# Odyssey Launcher: architecture

A fully 3D game launcher frontend, in the same space as Playnite, ES-DE and RetroBat, styled after the PS2 memory card browser:

- The main screen is a 3D grid of systems. Selecting one opens a 3D grid of that system's games, and selecting a game launches it in the configured emulator.
- Every item is a floating 3D model, and the focused item animates.
- Each system and theme defines an icon.sys-style background (a four-corner gradient) and lighting (three directional lights plus ambient).
- Default game models are per-system box templates textured with scraped art. Users can replace any model with their own `.glb`.

Windows comes first, Linux later if it's cheap, and macOS never. **Performance is the headline feature** (see A3).

Milestones and acceptance criteria are in [ROADMAP.md](ROADMAP.md). Decisions are recorded at the end of this file.

## A1. Layout and modules

```
OdysseyLauncher/
  OdysseyLauncher.slnx       Debug / ExportDebug / ExportRelease (Godot's configurations); Godot 4.6+ finds .slnx files
  global.json                .NET SDK 10.0.x; dotnet test uses Microsoft.Testing.Platform
  Directory.Build.props      Version, Nullable=enable, ExportRelease => Optimize=true (Godot's SDK only does this for its own project)
  src/Launcher.Core/         net8.0 class library, no Godot reference (a test enforces this)
  tests/Launcher.Core.Tests/ xUnit v3
  godot/                     project.godot, OdysseyLauncher.csproj (-> Launcher.Core), src/, scenes/, shaders/, themes/ (the built-in theme)
  tests/themes/              user themes for tests and captures (M6: slot-showcase)
  samples/themes/            user themes for theme authors to copy (M6: retro-tv; docs/THEMING.md)
  tools/verify.ps1           build, test, Godot headless build/import/smoke run
  .github/workflows/release.yml  the Windows release, on a pushed v<version> tag
  docs/  CLAUDE.md
```

### Launcher.Core (namespace `Launcher.Core.*`)

| Namespace | Responsibility |
|---|---|
| `Config` | `ConfigLoader` loads TOML (Tomlyn), layering user files over built-in defaults (embedded resources). <br>Maps Tomlyn's syntax tree by hand into a tree that keeps every key's position, so diagnostics still point at the right file after merging (M2). <br>Merges recursively; scalars and arrays are replaced. <br>Validates, with file:line:column:key diagnostics; unknown keys get a "did you mean" warning. <br>Parsers take text plus a source name, so the app can feed `res://` files from the PCK. <br>The files the app ships (the built-in defaults, and the built-in theme) are read by `TomlFast`, a strict parser for the plain TOML they use (tables, arrays of tables, bare keys, strings, numbers, booleans and single-line arrays): Tomlyn took about 50 ms for the built-in catalogue (A5), and `TomlFast` about 1 ms. It builds the same tree with the same positions (`TomlFastTests` compares them), and anything it doesn't handle, or TOML forbids, returns null so Tomlyn parses the text and reports the problem. The user's files always go through Tomlyn. <br>The install checks (an emulator's program or core missing) aren't part of boot: `ConfigSources.FileExists` is null there, and the app loads config again after `interactive` with `CheckInstallsFor`, the systems that have games (`AppServices.CheckInstallsAsync`, and again after each rescan), replacing the settings screen's list of problems. <br>From M7, `ConfigWriter` writes the settings screen's changes through `TomlEditor`, an editor over Tomlyn's syntax tree, so comments, blank lines, key order and quoting survive; only values that differ from the built-in defaults are written, and the edited files must load with no new error before anything is written (A5 Writing config). `ConfigInput` checks what the user entered first (the folder exists, the program is an .exe, a credential is one line). |
| `Data` | `LibraryDatabase` and `UserDatabase` (create, migrate, back up), `MigrationRunner`, and the connection helpers. <br>**Microsoft.Data.Sqlite's async API is synchronous**, so reads run on the thread pool, and writes go through one dedicated writer thread (`DbWriter`). <br>Readers come from our own pool (`ReaderPool`), not Microsoft.Data.Sqlite's: each has `userdata.db` ATTACHed once and is `query_only`, and the pool can be closed and held back while a rebuilt library file is swapped in. <br>Every connection sets WAL, `foreign_keys=ON`, `synchronous=NORMAL` and `busy_timeout`. |
| `Scanning` | `RomScanner` walks a system's ROM folders by file name (extensions, recursion, excludes). Several folders per system are allowed; the first folder wins a `path_key` collision. <br>Folders are listed with a 256 KB buffer, and `LibraryService` scans 8 systems at once on dedicated threads, because a network share costs a round trip per listing refill. Excluded folders (by default ES-DE's `images`, `manuals` and `videos`) aren't listed at all. <br>Multi-file games: files referenced by an `.m3u`, `.cue` or `.gdi` are hidden. Parsed playlists are cached in `library.db` by size and mtime, so a rescan doesn't re-read them. <br>`TitleParser` turns No-Intro and Redump names into a display title and a sort key, keeping region, languages, revision, disc and other tags as separate fields. <br>Normalises paths to `rel_path` and `path_key`. <br>`MediaScanner` (M5's `UserMedia`; from 2026-10-02 the whole media folder) indexes `DataDir/media/<system>/<kind>/<rel path>.<ext>` into `media`: images (PNG, JPEG or WebP), videos (`video`, MP4) and per-game models (`model`, `.glb`), scraped or the user's own alike. A file matches the game with the same `path_key`, or every game whose `path_key` is its name plus an extension. Each file's size and time are stored (migration 0002), so a rescan reads only new or changed image headers; a video's or a model's header isn't read. |
| `Scraping` | (M4) `IScraper` for ScreenScraper, IGDB and SteamGridDB, and the Steam store (2026-10-01, no credentials), each with a capability map (the fields and media kinds it can supply). <br>`ScrapeService`: scrape a game, a system, or everything missing, and clear a game, as operations with progress events (raised on worker threads). They go through a persistent queue in `userdata.db` (resumed after the app closes; single games jump ahead; cancellable), and games run concurrently within each provider's limits. <br>`ProviderGate` bounds each provider's requests in flight, per second and per minute, and holds them during a rate-limit pause or after a used-up quota; `ScraperHttp` retries rate limits and transient failures with exponential backoff, honouring Retry-After. <br>Provider selection: `[scraping] provider` first, then each `fallback` in order, asked only for what's still missing and what its capability map has; a provider with no credentials is skipped and reported. <br>`ProviderAccounts` reads credentials from `secrets.toml` and `ODYSSEY_*` variables. <br>Match resolution (A2). With `--save-responses` (2026-10-02; off by default), each provider's response is saved in `scraped/responses/` (credentials redacted), to debug a scrape, and `ScrapedRestore` rebuilds a game's scraped metadata and matches from them offline when a scan adds it. <br>From M7: `TestConnectionAsync`, one cheap request per provider with the current credentials (ScreenScraper `ssuserInfos.php`, or `ssinfraInfos.php` without an account; IGDB its cached token and the smallest query; SteamGridDB and the Steam store a search), which never throws for a refusal; and `CountMissingAsync`, what "scrape all missing" would take on, per system. From M7 part 2, `CountSystemAsync` (what "scrape this system" would take on: its games, and how many are missing). <br>**Manual matching** (2026-10-01): `SearchMatchesAsync` searches every provider at once (`IScraper.SearchAsync`) for the game's title (the user's, else the file name's) or a typed name, and returns each provider's results, closest name first (`TitleMatcher.Similarity`), with its current match, or why it couldn't be searched; `ScrapeGameWithMatchAsync` saves the result the user chose as a manual match and scrapes the game with it first (batch kind `manual`; see A2's match resolution). |
| `Media` | (M4) `MediaStore`: scraped downloads, written to the media folder as the game's own file (`media/<system>/<kind>/<rel path>.<ext>`, from 2026-10-02) atomically (a temporary file, then a move), never replacing a file the game has of that kind (A4), with the image checked by its first bytes (a video, from 2026-10-01: an MP4, by its `ftyp` box; it gets no derivative). <br>`Bc7Encoder` (modes 6 and 1) and `Bc7DdsWriter` make the derivative; `DerivativeBaker` decodes (`IImageDecoder`), squeezes to 512² and encodes; `DerivativeService` bakes on its own below-normal thread, and `BakeMissingAsync` bakes every image without a derivative (every kind from M6, since any can fill a theme's slot) and deletes stale ones. <br>From M5: `ImageHeaders` reads a PNG, JPEG or WebP's size from its header only; `TextureDerivatives` names each baked derivative (`CacheDir/textures/<key>.dds`, the key a SHA-256 of the source's path, size and time; from 2026-10-02 every source is in DataDir, so no root), allocation-light so texture workers can call it per cover; `MediaKinds` lists the kinds. <br>From 2026-10-02, `IVideoDecoder`: a game's video decoded for its details screen, as RGBA frames (`IVideoReader`, with its size, pixel shape and length, and a seek) and 32-bit float sound (`IAudioReader`), each reader used on the one thread that opened it (Windows: `MediaFoundationVideoDecoder`, in `Platform`). <br>From M7 part 2, `UserArtService`: the user's own image for one of a game's slots, chosen in its options. It's copied to the game's whole ROM name in the media folder, `DataDir/media/<system>/<kind>/<rel path>.<ext>` (so it's that ROM's only; one file per kind, so the game's file in another format goes, a scraped one too), its derivative is baked, and the system's media folder is indexed again without a ROM scan (`RefreshMediaAsync`, which raises `MediaChanged`). Removing deletes the game's own file of that kind, whoever put it there, and the slot stays empty until a scrape fills it; a file every game of that name shares isn't removed for one game. |
| `Theming` | (M6) `ThemeLoader` parses and validates a theme manifest (A6) from text plus a source name, over `IThemeFiles` (a folder on disk, or the app's PCK), with file:line:column:key diagnostics like config's; a bad block falls back to the built-in theme's, a bad template is left out. `ThemeCatalog` finds user themes (`ConfigDir/themes/<id>/`) and picks the active one, the built-in `memory-card` staying the last resort. `ModelResolver` lists each system's model candidates for its games and its card in precedence order (A7), with its look and colour. `SlotChain` and `MediaSlots`: the media slots, their standard texture sizes, and fallback-chain resolution (allocation-free, for the grid). |
| `Models` | No Godot dependency. `GlbInfo` reads a `.glb`'s material names from its JSON chunk only (theme validation checks a template's slots before the app loads it). From M6 part 2: <br>`GlbFile` splits a GLB into its JSON (a mutable tree) and binary chunk, and writes one back. <br>`ModelInspector` validates a model against A7 without Godot: every index, accessor, buffer view and index value, the node tree (no cycles or shared children), embedded PNG or JPEG images sized from their headers, and required extensions; it counts triangles over the scene's nodes, materials, textures, joints and morph targets against `ModelBudget` for its `ModelKind` (game template, per-game, system model), and finds the slots and the clips (`ModelClips`). A file Godot could misread or crash on is rejected here. <br>`ModelProcessor` scales textures over the budget's side down (decoded and scaled by `IImageDecoder`, written back by `Media/PngEncoder`) and repacks the binary chunk. <br>`ModelCache` keeps processed user models and their reports in `CacheDir/models/`, keyed by path, size, time, kind and processing version, so a model (or a rejection) is processed once. <br>`ModelLog` is the log the user reads, `DataDir/logs/models.log`. <br>`ObjConverter` turns a Wavefront OBJ model (a zip, or an `.obj` with its `.mtl` and textures beside it) into a GLB through `GltfBuilder`, which also writes the synthetic library's and the tests' models. A PS2 save icon's shape animation beside the OBJ (`ICON.ICO.anim`, ps2iodb's JSON: whole-mesh frames blended by weight keys) is read by `ShapeAnimation` and written as morph targets and a `focused` clip of their weights. <br>`ModelImportService`, for M7's game options panel and `odyssey-scrape import-model`: import (convert, fit to the per-game budget, write to the game's model slot, prime the cache, index, log), remove, and the current model's report. From M7 part 2 it does the same for a system's own models (A7 level 2: its card, `models/systems/<system>.glb`, to the system model budget, and its game template, `models/templates/<system>.glb`, to the template budget), which aren't indexed: they're found when a theme is resolved. |
| `Launching` | `LaunchPlanner` is pure and static: it picks the emulator (this launch's choice, then the game's override, then the system's) and expands its templates into a final argument list (A5). A named emulator that isn't configured is an error, never a silent fallback. <br>A profile with `run_file = true` (A5) runs the game's own file: the plan's `Executable` is the ROM, with no arguments, and `LaunchPlan.RunFile` is set, so `LaunchService` doesn't look for a program. <br>**Steam games** (2026-10-01): a `run_file` game whose file is a `.url` naming a Steam app (`SteamShortcut`: `steam://rungameid/<id>`, `run` or `launch`) is handed to Steam (the plan is `Detached`: the shell opens it and nothing it starts is followed, so a Steam client the shortcut starts isn't mistaken for the game) and followed by `SteamGame` through `ISteamClient`: running while Steam's current game is that app, or while the app's own running flag is set (trusted only once seen clear, as Steam can leave it set), and the client runs; ended after two polls without it (1 s apart); never started if it isn't seen running within 2 minutes, not counting time Steam spends updating it (`ProcessOutcome.NotStarted`, a failure that isn't a play). Cancelling stops following and leaves the game to Steam. Without Steam installed, the launch fails before anything starts. <br>`LaunchService` checks the ROM, executable, core and working folder exist, runs the plan through `IProcessRunner`, and records the play session through `IPlayHistory`. One game at a time. <br>Events, raised on worker threads: `Starting`, `Running` (process id), then exactly one of `Exited` (exit code, duration) or `Failed` (a reason written for the user). A non-zero exit within 5 s is `Failed`, and isn't counted as a play. Cancelling ends the game's whole process tree. (M3) |
| `Library` | `LibraryService`, the façade the app uses: systems summary (boot), games list (on entry), the Favourites and Recently played lists, favourites and overrides, and rescan and rebuild jobs with progress, and metadata overrides (M4; scrape jobs are `ScrapeService`'s). Scans and rebuilds run one at a time; each writes in one transaction. <br>From M6: `GetGameMediaAsync` (a system's or chosen games' media of the kinds a theme's chains name, one indexed query), `RefreshMediaAsync` (one system's media folder indexed again without a ROM scan, for the import and art services; M6's `RefreshUserMediaAsync`), and the `MediaChanged` event, raised after a rescan or refresh that changed media files, a scrape that saved media, a clear, a rebuild, or a bake. <br>From M7 part 2: `GetGameMediaInfoAsync` (a game's media rows: kind, file and size) and `GetMetadataEditAsync` (its title and metadata with the scraped values and the user's overrides apart), for the game options panel; `MetadataInput` checks and normalises what the user types (one line and a length; release dates as a year, month and year, or day, day first, stored as ISO 8601; ratings out of 5, out of another number, or a percentage, stored 0 to 1). |
| `Files` | (M7) What the pickers list, without Godot. `DirectoryListing` lists one folder on the caller's thread (the pickers use a dedicated one): folders first, then files, each in natural order ignoring case (`NaturalComparer`), filtered by a `FileFilter` (images, `.glb` models, programs), hidden and system entries skipped, with a 256 KB buffer, and a count others can read while it runs. It never throws for a folder it can't read: a missing folder, a refused one, a drive with no disc and an unreachable share come back as a reason written for the user. `PathInput` reads a typed path (quotes dropped, `/` as `\`, `C:`, `~`, relative to the folder shown, `\\server\share`) and finds the folder above, stopping at a drive's or share's root. `LetterJump` groups a list by first letter. `PickerHistory` keeps each picker use's last folder in `DataDir/picker-locations.json`. |
| `Platform` | The only OS-specific code. <br>Interfaces: `IPlatformPaths`, `IProcessRunner`, `IWindowFocus`, `IFileLocations` (M7), `IPowerControl` (the power menu), `ISteamClient` (Steam games), `IDeviceStatus` (the status indicators: the battery and the network); `PlatformServices` picks the implementations. <br>`DeviceStatusMonitor` (2026-10-02) polls `IDeviceStatus` on the thread pool every 10 s, and at once when .NET's `NetworkChange` says an address changed, and raises `Changed` only when the snapshot differs (the Wi-Fi signal compared as bars, 0 to 3, not its raw quality); it's paused while a game runs. <br>**Windows** (`Platform/Windows`, `LibraryImport` to kernel32, user32, advapi32 and powrprof): <br>- `WindowsProcessRunner` creates the emulator inside a new job object (`PROC_THREAD_ATTRIBUTE_JOB_LIST`) with `CreateProcessW`, and the game has ended when the job has no processes, so stub launchers are followed. A dedicated thread waits on the job's completion port, and also asks the job every second, because Windows doesn't guarantee job messages. The job doesn't kill the game if the launcher dies, allows explicit breakaway, and no handles are inherited. <br>- A `RunFile` plan (a game that is its own program, script or shortcut) never goes through a command line cmd.exe could split: `.exe` and `.com` files run directly; `.bat` and `.cmd` files as `cmd.exe /d /s /c ""path""` (Windows starts cmd.exe itself for a batch file given to `CreateProcess`, and a name like `Sonic & Knuckles.bat` then runs `Knuckles.bat` as a second command, which a test showed), refusing a path with a `%`, which cmd would expand; anything else (a `.lnk` shortcut, a `.url`) by `ShellExecuteEx` on a COM-initialised thread, whose process is put in the game's job once it exists (a little it starts first isn't followed; a process that can't be put in a job is followed by its handle; no process at all, such as a document handed to a program already running, counts as ended at once). <br>- `WindowsCommandLine` quotes each argument by the C runtime's rules, since Windows passes one UTF-16 string. <br>- `WindowsWindowFocus`: see Platform glue below. <br>- `WicImageDecoder` (M4) decodes PNG, JPEG and WebP and scales them with the Windows Imaging Component, through raw COM vtable calls (no interop package). <br>- `MediaFoundationVideoDecoder` (2026-10-02) decodes MP4 videos with Media Foundation, the same way (`MediaFoundation` holds the vtable slots, GUIDs and calls): a source reader per stream, the picture through Media Foundation's advanced video processor to 32-bit RGB (then RGBA, cropped to the picture's aperture, top row first whatever the stride), the sound to 32-bit float. The first frame is read when the file opens, since the decoder settles the format with it. Windows' H.264 decoder takes 4:2:0 only: a 4:4:4 file (a fifth of the owner's ScreenScraper arcade videos) fails, and the reader says so, from the `avcC` box's profile. Windows N editions lack Media Foundation, which is reported as such. <br>- `WindowsFileLocations` (M7): drive letters and types (`GetLogicalDrives`, `GetDriveTypeW`) and a mapped drive's share and whether it's connected (`WNetGetConnectionW`), none of which touches the drive; volume labels separately (`GetVolumeInformationW` can block for tens of seconds on a disconnected share, so the pickers call it on a worker and don't wait); Downloads from its known folder. <br>- `WindowsPowerControl`: restart and shutdown with `ExitWindowsEx` (planned, closing hung apps; a full shutdown, not Fast Startup's hybrid), sleep with `SetSuspendState`, each after enabling the shutdown privilege in the process's token (`AdjustTokenPrivileges`). Sleep is offered only where `GetPwrCapabilities` reports S1–S3: a Modern Standby PC can't be put to sleep by an app. <br>- `WindowsDeviceStatus` (2026-10-02): the battery from `GetSystemPowerStatus` (none when `BatteryFlag` says so; plugged in from `ACLineStatus`); the network from the interface table (`GetIfTable2`): the default route's interface (`GetBestInterface` for a public address, which only reads the routing table) if it's a connected hardware adapter (Ethernet or 802.11, up, its medium connected), else the first connected Wi-Fi adapter, else the first connected Ethernet one, so a VPN or a Hyper-V switch over the real adapter still shows the real link; a Wi-Fi connection's signal quality from the WLAN service (`WlanQueryInterface`, current connection), unknown without it. Native memory only, nothing managed allocated per read. <br>- `WindowsSteamClient`: the Steam client's state from what it writes to `HKCU\Software\Valve\Steam` (`SteamExe`; `ActiveProcess\pid`, checked alive; `RunningAppID`; `Apps\<id>`'s `Installed`, `Running` and `Updating`), read with `Microsoft.Win32.Registry`; no network, no Steam API. A `Detached` plan is opened by `ShellExecuteEx` and its process handle closed at once. <br>**Linux stub:** `PortableProcessRunner` (`Process` with `ArgumentList`; follows the started process only), `NullWindowFocus` and `NullPowerControl` (the power menu offers only Quit app); no Steam client yet (Steam's `registry.vdf` has the same keys), so a Steam shortcut runs unfollowed; no image decoder yet, so no derivatives, and no video decoder (videos are listed but not played); `PortableFileLocations` (`/`, and the home folder's Desktop and Downloads); `PortableDeviceStatus` (no battery; the network from .NET's interface list, Wi-Fi without its signal). |
| `Diagnostics` | Debug-argument parser, `StartupTimeline`, `FrameTimeStats`, `BenchReport` (System.Text.Json source generation), a minimal `ILog`, and `Redactor` (M4), which masks every known credential (as written, URL-encoded and JSON-escaped) and the value of any credential-bearing URL parameter or bearer header. |

Every `await` in Core uses `ConfigureAwait(false)`. Analyser rule CA2007 is an error in `src/`.

### Godot app (`godot/src`, namespace `Launcher.App.*`)

| Area | Responsibility |
|---|---|
| `Boot` | Main scene (M5). `AppServices` loads config, resolves the theme (M6: manifests and each system's model candidates) and opens the library on the thread pool. The main thread makes the cover array while that runs, and starts loading the theme's models as soon as the theme is resolved, while the DB opens. When both are done it builds the look and the grids and binds the systems grid; its first drawn frame is `interactive`. A headless run (`--launch` only) resolves no theme. A warm-up follows, one step a frame: the settings screen, the launch controller, glyphs, then the status indicators (2026-10-02: their first uses, the time zone, the time format, the icons and the device monitor, on the thread pool; only their nodes on the main thread). Systems never scanned are scanned in the background after it, and then covers without a derivative are baked (M4; also after F5). `MainThreadQueue` carries every background result to the main thread within 3 ms a frame. |
| `Screens` | `Navigator` (M5): Systems → Games → Launching → back. Transitions move the two grids in depth, scale them and fade them into the background, staggered so the opaque grids barely overlap. From M6: entering a system cross-fades to its look; the next theme (T, or the one chosen in the settings from M7) loads in the background and is applied without a restart (templates, slot layout, look, and the shown list loaded again with the new theme's media kinds); per-game models load when their list does and replace their game's template in place; `MediaChanged` re-reads the shown list's media and rebinds only the games whose media changed. The last focused game is remembered per system, and the last 3 game lists are cached. Favourites and Recently played are cards in the systems grid, mixing templates. A system with no games has no card (`[display] hide_empty_systems`, on by default, A5), so the built-in catalogue shows only what the user has; the grid is built again after each rescan, and a system never scanned is scanned in the background after boot. Details are queried and formatted on the thread pool 0.12 s after the focus rests, so held moves don't query. `InfoOverlay` is the PS2-style text: the title with a soft glow top left, what it belongs to under it, a system's details bottom left (its maker, games, emulator) and controls bottom right; for a game, only "Favourite" top right (2026-10-02: a game's metadata moved to its details screen, below). <br>From M7: Menu, or B or Escape on the systems screen, opens the settings, and the navigator ignores input until they close and every button is let go; rescans (F5, and the settings) run through `LibraryJobs` with a progress card; config the settings save rebuilds the systems grid. <br>From M7 part 2: X opens the focused system's or game's options (Favourites and Recently played have none). Games whose title or metadata changed (a scrape, a clear, an edit: `LibraryJobs.GamesUpdated`) have the shown list read again 0.4 s later, several changes being read once: titles are updated in place (`GamesSource.UpdateTitles`, `RefreshItem`) when the games are still in the same order, else the list is bound again with the focus on the same game; the focused game's details are read again at once. A system's own models or template choice changing reloads the theme (`ReloadTheme`, a switch to the same theme). <br>View (Select) or P in either grid opens `PowerMenu`: Restart system, Shut down system and Sleep system through `IPowerControl`, on a worker (sleep returns only on waking), and Quit app. A row acts at once; B or View again closes it. A restart or shutdown Windows accepted quits the app, so the databases close before Windows ends it; a refusal is shown in a dialog. <br>From 2026-10-02, `StatusBar`: the status indicators top right (the network, the battery and the time, each on or off by `[ui]`, A5), on a canvas layer of their own above the settings screens, so a change made there shows at once (only `--no-overlay` hides them). The row is an `HBoxContainer` anchored top right and growing leftwards, which leaves hidden indicators out of its layout, so whatever is shown sits together against the right edge. The icons are [Lucide](https://lucide.dev)'s (`godot/icons/status/`, ISC), imported at 4× with mipmaps and loaded on the thread pool; a Wi-Fi signal below full draws every arc faintly with its bars over them; a battery at 10% or less is red, one charging green. The device's state comes from `DeviceStatusMonitor` through the main-thread queue, only on a change; the clock is checked once a second in `Tick` (no allocation) and its text, in the user's regional short-time format, made only when the minute changes. The overlay's title stops short of them, and "Favourite" and the job cards sit under them. <br>From 2026-10-02, **Y on a game opens `GameDetailsPanel`**, on the settings layer: every field the library has for it (`DetailsFormatter.GameFields`: release, genre, developer, publisher, players, rating; region, languages, version, disc and other tags; play count, last played and play time; favourite, emulator, whose title and metadata, when it was scraped, size and file) in two columns under its whole description, in one block that up and down scroll; and a card for its video, its front cover and its screenshot, then each other image in slot order, thumbnails decoded on a worker one after another (a video's from a frame a little way in that isn't dark). A on a card opens `MediaViewer`, a full-screen panel on black (no header; the status indicators step aside for it): an image decoded on a worker to fit the window's larger side, or the video through `Ui/VideoPlayback`; left and right go to the previous and next, A pauses and plays (and plays again once ended), and the caption (what it is, which of how many, the controls, a video's progress) fades after 3 s. L3 (or F) toggles the favourite there as in the grid, and the overlay reads it again. `--open=details` opens it for `--start-system`'s game at `--start-index`. <br>From 2026-10-02 the grids take their layouts from `[display]` (and a system's own games layout and grid size), applied on each bind and again when config is saved (the games shown are bound again only if their layout changed); `--layout` overrides them for a run. The list layout's titles are `TitleList`, part of the overlay (so it hides and dims with it), under the heading on the left: a pool of labels re-bound as titles scroll into view, following the games grid's own scroll (a line per title), so the list and the model beside it move together with nothing to keep in step; the focused title stays a third of the way down, under a highlight, and Favourites and Recently played add each game's system. LB and RB page by the titles shown. |
| `Navigation` | `NavInput` (M5) polls `nav_*` actions each frame rather than using `_Input`, which allocates per event: arrows, Enter/Space, Escape/Backspace, Page Up/Down, Home/End, `[` `]`, F and F5; the D-pad, left stick, A/B/Y, shoulders (page), triggers (letter) and View (rescan; from 2026-10-01 the power menu, with P on the keyboard, and F5 alone rescans). A held move repeats after 0.32 s, then speeds up from every 120 ms to every 35 ms over 1.4 s. Input is dropped while `LaunchController.IsInputBlocked`, and a button still held when that ends doesn't count. <br>From M7 each command is two actions, `nav_*` (keyboard) and `nav_*_pad` (gamepad), so a screen that takes typing (the on-screen keyboard) polls the pad alone; X (`Alternate`: from part 2, also O or the menu key, and an item's options in the grids) and Menu or F1 (`Menu`: the settings) are added (from 2026-10-02, Y or I is `Secondary`: a game's details in the grid, a list's second action in the settings; L3 or F is `Favourite`, in the grid and the details screen), T alone switches theme, and Godot's own `ui_*` navigation actions are emptied at boot, so the settings screens' focus moves only from these commands, with the same repeat. |
| `Ui` | (M7) The settings screens' toolkit: Godot controls driven by `NavInput`. `UiLayer` (a canvas layer over the dimmed grid) stacks `UiPanel`s and polls the commands each frame while one is open (and does nothing while none is): the top panel takes a command first, then the layer moves the focus with `Control.FindValidFocusNeighbor`, presses the focused button, or goes back. Panels under the top one can't take focus or clicks, and a page hides the page below it (a dialog dims it). The mouse works through Godot's GUI events: buttons, the wheel, and a Back or Cancel button in each header. `UiStyle` builds the theme in code. Components: `SettingRow` and `ListPanel` (rows, some adjusted with left and right); `ChoicePanel`; `ConfirmDialog` (also one-button messages; the safe answer focused for an action that can't be undone); `OnScreenKeyboard` over `TextField` (letters, then symbols and accented letters; the pad as on the Xbox keyboard; a physical keyboard types straight in through `_Input` while it's on top; hidden entry with Show for credentials; validation before Done); `FilePicker` over `VirtualList` (folder or file mode, a filter, the places and drives at the top level with labels read on workers, a typed path, a thumbnail decoded and scaled on a worker by the OS decoder, each use's last folder, and a folder that's slow to open left behind with B); `BackgroundJobs` (a job's progress written from any thread, one refresh a frame at most) and `JobsHud` (a card per job, top right, with a mouse Cancel; hidden while the settings are open). <br>From 2026-10-02: a panel can be `PanelPlacement.FullScreen` (the whole window on black, no header or hints; `UiLayer.TopChanged` lets the status indicators hide under it); `VideoPlayback` plays an MP4 (Godot plays only Ogg Theora) into an `ImageTexture` with its sound through an `AudioStreamGenerator`: a thread of its own decodes 4 frames ahead, each into an `Image` of its own (`SetData` off the main thread; the texture made there too), and about a second of sound into a ring; once a frame the main thread feeds the generator, takes the time from the sound actually played (frames pushed, less what the generator still holds, less the output latency; the frame time when there's no sound, or once it has played out), and uploads the latest frame due. Nothing it does a frame allocates, and it never waits for its thread, which lets its readers go itself. |
| `Settings` | (M7) The main settings screen. `SettingsController` opens it and saves: `ConfigWriter.Save` on the thread pool, after a check that may need I/O (the folder exists), then on the main thread the new config goes to `AppServices` (the library, launcher and navigator read it), a chosen theme is switched to, and new credentials or scraping settings retire the scrape service once no scrape uses it. Pages: `SettingsHome` (and the Library actions, their jobs, and config problems), `LayoutPage` (2026-10-02: the systems' and games' layouts and grid sizes, each a list on A and stepped with left and right), `RomFoldersPage` and `SystemPage` (the ROM root, each system's folders and emulator; a change rescans what it affects), `EmulatorsPage` (each profile's program (only the profiles systems with games use, with empty systems hidden; a `run_file` profile has no program to pick), checked off the main thread; profiles sharing one install move together, through the variable they share when there is one), `ScrapingPage`, `FallbackPage`, `ScrapeMediaPage` (from 2026-10-01: each media kind scraping downloads, on or off, with the providers that have it) and `ProviderPage` (credentials masked, where each is set, cleared, and tested). `LibraryJobs` runs rescans and "scrape all missing" as jobs bound to the library's progress and the scrape service's events, cancellable, and owns the scrape service. All of it is built in the warm-up after `interactive`. <br>From M7 part 2, `SystemPage` is also a system's options (X on it in the grid): (2026-10-02) its games' own view and grid columns and rows (each Default, the Layout page's, until set; Y goes back to it), its models (its card, and its games' template: one of the themes' templates as `game_model`, or the user's own `.glb`) and "scrape this system", counted and asked first. `LibraryJobs` also scrapes a system (a batch, like "all missing") and a game (a job of its own, which can run beside a batch: the service puts single games first), clears a game, and raises `GamesUpdated` on the main thread as each game is done. |
| `Options` | (M7 part 2) The item options. `ItemOptions` opens them (X in the grids, through the navigator's events) on the settings layer, owns the services they use (`ModelImportService`, `UserArtService`), and passes changes on: a game's edits to `LibraryJobs.GamesUpdated`, a system's models to a theme reload. `GameOptionsPanel`: the emulator (an override, or the system's), its own model (a `.glb` or OBJ zip, Y removes it), images, title and metadata, "scrape this game" (matching is manual: `GameMatchPanel`, below; the outcome in the panel's status) and "clear metadata" (a confirmation saying what goes, including the user's own images). `GameMetadataPanel`: each field with the user's value or the scraped one and where it came from; A types one on the on-screen keyboard, checked by `MetadataInput` before it's saved; Y goes back to the scraped value; a value equal to the scraped one isn't kept as the user's. `GameMediaPanel`: a card per media slot with its image (decoded off the main thread by `Ui/Thumbnails`, shared with the image picker), its file (from 2026-10-02 the media folder doesn't say whether it was scraped), its size and whether the system's template shows it; A chooses the user's own with the image picker, replacing the slot's file; Y removes the slot's file, scraped or not. `GameMatchPanel` (2026-10-01): every provider's search results in a section of its own (the name, year, id and how close the name is), each provider's current match marked "In use" (one the search doesn't list gets a row of its own); a provider that couldn't be searched says why; X searches for a name typed on the on-screen keyboard; A on a result scrapes the game with it, through `LibraryJobs.ScrapeGame`. `--open=match` shows it over made-up results, for captures. Every panel reads and writes off the main thread and reads again when the library says the game changed. |
| `Grid` | `ItemGrid` (M5), a virtualised 3D grid. <br>A cell pool (at most 64 for games) covers the visible rows plus spare rows, most of them ahead of the scroll, and cells are re-bound rather than recreated. <br>Template items are drawn as **one `MultiMesh` per template**, with materials of the one item shader (M6: templates share one unless their authored textures or tint differ, so there's never a variant). Each pool cell has a fixed instance in every template's MultiMesh (hidden where unused), a fixed layer per slot channel in the streamer's arrays (`SlotLayout`), a row of the slot-state texture and a fixed place in the title atlas. `INSTANCE_CUSTOM` = (the cell, the plain colour packed as a 24-bit integer, idle phase or −1 when focused, unused): Godot 4 multiplies a MultiMesh's instance colour into `COLOR`, which carries material data here. The slot-state texture (RGBA32F, 8 slots × 64 cells, created once and only updated) holds, per cell and slot, the fallback shown without media, the media's aspect, its fade and its layer; from 2026-10-01 two more columns per cell reshape a box to its game's art (A7 Boxes shaped by the art), zero for every other model. <br>Each slot walks its template's fallback chain against the game's media when a cell binds; `RefreshItem` redoes that after the game's media changed, keeping its model and unchanged slots. <br>**Items drawn as nodes (M6 part 2).** A per-game model can't share a template's MultiMesh, so it's drawn on the cell's own `MeshInstance3D`, one per pool cell made with the grid (binding one sets its mesh and material, and allocates nothing), fitted to the cell. A model with clips is drawn on a copy of its node tree (pooled per model, made the first time a cell needs one): a template with an `idle` clip in every cell, one with only `focused` or `launch` clips only in the focused cell, which swaps back to the MultiMesh once its clip has blended to the rest pose. A node's per-cell data is the shader's `node_custom` instance uniform (a `Vector4`: Godot converts a `Color` given to one from sRGB to linear), so it's the same material and no new variant. Per-game models' materials are made when they load (`PrepareModel`), not while scrolling. <br>**The items never move to scroll: the grid's root does** (one transform), as the camera would, so a frame only touches newly bound rows, the focused items and fading covers. Two grids (systems and games) each have their own root. <br>Items are sized so 3.2 rows of games fit (2.7 of systems), unless that leaves fewer than 5 columns. A single part-filled row is centred. <br>`TitleAtlas`, a SubViewport of labels, draws each cell's title as a square block and a spine strip; it redraws only in a frame where a title changed. <br>**One update drives every item**, called by the main scene each frame. <br>A cell's texture request is superseded when it's re-bound, so late results are dropped. <br>Critically damped scrolling, the focused row always on the focus line, a little above the middle. <br>**Layouts (2026-10-02).** `GridLayout` (from `[display]`, A5) shapes a grid: `Grid` (rows and columns; set columns fill the width, set rows fit between the overlay's heading and its details with the focused row in the middle one, and either set leaves the other to fit; automatic is the sizing above), `Carousel` (one row scrolling sideways, a little under 5½ items across, each item a place or more from the middle smaller, turned towards it and stepped back, recomputed for the bound cells only while it scrolls), `Single` (one item, about half the view's height, the next a screen to the right, so a move slides it in) and `List` (one item a screen apart, scrolling down on the right of the view). Each is the same machinery with the line (row) along another axis: one item a line, the same pool, bound lines, streamer rows (a line) and focus effects (a big item's lift capped in world units). A pool too small for set columns gives up spare rows first (down to one ahead of the scroll), then columns. `Move(dx, dy)` steps the focus as the shape lays items out. |
| `Models` | (M6, replacing M5's `TemplateLibrary`) `ModelLoader` loads model candidates. A user's model (per-game, in the media folder; per-system, `ConfigDir/models/`; a user theme's) comes from Core's `ModelCache` (inspected, fitted to its budget, rejected and logged if it must be); a built-in theme's is read from the PCK. Each is parsed by `GltfDocument` (told to discard its textures) and converted on its own worker, so they load in parallel, and the main thread adopts finished loads within 2 ms a frame. Models stay for the session; per-game models no shown or cached list uses are released when a list is bound, and a user theme's models are released when another theme is applied (M7 part 2: their node trees are freed then, which they weren't). `ModelConverter` decodes each base colour image itself with mipmaps (the runtime importer makes none), merges every surface into one rest-pose mesh for the item shader and fits it to the spec (standing on y = 0, centred, largest side 1 m): per vertex, `COLOR` is the material's base colour (linear, times any vertex colour) and roughness, and `UV2` the face code ((media slot + 1) × 8 + (authored texture + 1)) and the face's aspect (`extras.aspect`, or the slot mesh's bounds). A model with `idle`, `focused` or `launch` clips also keeps its node tree (`GenerateScene`, each mesh node given a mesh of the same format converted from the glTF mesh's CPU-side `ImporterMesh`), with its clips renamed to the canonical names, looping set, and a `_rest` clip made from their tracks. No slot is required. `ItemTemplate` is the result. The procedural fallbacks are in the grid: lift and scale when focused (always); sway when focused and bob when not, unless a clip plays; spin up and fly forward to launch, unless a launch clip plays. |
| `Textures` | `TextureStreamer` (M5; slots from M6): prioritised, cancellable requests, one per pool cell and slot channel; 2 dedicated decode workers; mandatory baked derivatives (BC7 DDS, 512² with mips); two arrays, 512² layers for the cover and 256² for every other slot (mip 1 of the same derivative), created up front (the cover's at boot, the others on a worker once the theme's layout is known) and only updated while browsing; a per-frame budget of 4 MB and a cap of 4 cover-sized uploads (a 256² layer counts a quarter); pooled `Image`s; and an opaque fallback-to-media fade in the shader. A missing derivative moves the slot on down its chain. The LRU cache and the focused item's full-resolution upgrade are later (moved out of M6: see ROADMAP.md). |
| `Theming` | `LookStage` (M6, was M5's `Look`): the four-corner gradient on a background canvas layer (`Environment` background mode Canvas), three `DirectionalLight3D` children of the camera, and an ambient colour, cross-fading to another look over the theme's `look_transition_ms`. The item materials get the corners too, to fade items into the background. `ThemePlan` (thread pool) resolves a theme for the enabled systems; `ThemeRuntime` (main thread) loads each system's first candidate that loads and gives the grids their templates, the slot layout, and each system's look and colour. |
| `Diagnostics` | `DebugHooks` autoload (`--capture`, `--bench`), timeline marks, and a log sink that writes to Godot's output and a file. `ScrollBench` (M5) drives `--bench-scenario=scroll`. |
| `Tools` | `BoxTemplateGenerator` (M5), a `[Tool]` node that builds the built-in theme's models (A7) procedurally and exports them with `GLTFDocument` (from 2026-10-02 with `ArcadeCabinetBuilder`'s arcade cabinet); from M6 also the test theme's (`tests/themes/slot-showcase/models/`) and, through `RetroTvBuilder`, the sample theme's (`samples/themes/retro-tv/models/`: a CRT television template and a console system model, with clips). |
| Platform glue | A main-thread queue with a per-frame time budget. <br>`Launching/LaunchController` (M3), built on first use, not at boot. `LaunchService` events reach it through `CallDeferred`. <br>- **Starting:** `RenderLoopEnabled = false`, low-processor mode with `Engine.MaxFps = 10`, the tree paused (no animation or processing), the master bus muted, and input swallowed. From M5, textures are evicted too. <br>- **Running:** `IWindowFocus.BeforeLaunch` lets any process take the foreground (`AllowSetForegroundWindow(ASFW_ANY)`, withdrawn by Windows at the next keyboard or mouse input), because a stub launcher's real emulator is a grandchild. A 4 Hz timer waits until another process's window is in front (or 10 s), then minimises the launcher with `SW_SHOWMINNOACTIVE`, so nothing unrelated is activated in between. <br>- **Exited or Failed:** game mode is undone, then `AfterExit` restores the window and takes the foreground: restore and `SetForegroundWindow`; then the same with the foreground window's input queue attached; then with a synthetic Alt key held (Windows lifts its lock after keyboard input); otherwise the taskbar button flashes. System settings (the foreground lock timeout) are never changed. Input stays swallowed until 500 ms after focus returns, so the button that quit the emulator doesn't act in the launcher. <br>- Input processing is on only while input is swallowed: an always-on `_Input` allocated about 1.9 KB per frame, because the Deck sends joypad motion all the time ([perf/m3-launching.md](perf/m3-launching.md)). The navigator also drops its input while `IsInputBlocked`. <br>- From M5 the controller is built in the warm-up after `interactive`, takes the shared `AppServices`, and raises `GameModeEntered` and `GameModeLeft`: the cover array is freed while a game runs and recreated afterwards, and the bound covers re-requested. |

## A2. Key interfaces (sketch)

```csharp
// Launcher.Core.Platform
public interface IPlatformPaths {
    string ConfigDir { get; }   // settings/systems/emulators/secrets .toml, themes/, models/ (the user's per-system models)
    string DataDir { get; }     // library.db, userdata.db, media/ (every game's art, videos and models), scraped/, logs/
    string CacheDir { get; }    // regenerable without network: textures/, models/
    string HomeDir { get; }
}
public interface IProcessRunner {   // Windows: child created inside a job object
    IRunningProcess Start(LaunchPlan plan);                        // blocking; throws ProcessStartException (message for the user)
}
public interface IRunningProcess : IDisposable {
    int ProcessId { get; }
    Task<ProcessOutcome> Completion { get; }                       // Windows: when the job has no processes left
    void Terminate();                                              // the whole tree
}
public readonly record struct ProcessOutcome(int ExitCode, TimeSpan Elapsed, bool Terminated, string? NotStarted = null);  // NotStarted: Steam never ran it
public interface ISteamClient {                                    // Windows: HKCU\Software\Valve\Steam; any thread but the main one
    string? ClientPath { get; }                                    // null: Steam isn't installed
    SteamAppState GetAppState(uint appId);                         // (ClientRunning, Installed, Running, Current, Updating)
}
public interface IWindowFocus {                                    // on the window's thread; no I/O
    void BeforeLaunch(nint launcherWindow, int childProcessId);   // let the emulator (and its children) take the foreground
    bool HasLostForeground(nint launcherWindow);                   // another process's window is in front
    void Minimise(nint launcherWindow);                            // without activating anything
    ForegroundResult AfterExit(nint launcherWindow);               // restore and take the foreground back
}

// Launcher.Core.Config
public sealed record Diagnostic(Severity Severity, string Source, int Line, int Column, string Key, string Message);
    // ToString(): "systems.toml:12:3: error: systems.megadrive.emulator: unknown emulator 'blastemm'"
public sealed record ConfigLoadResult(AppConfig Config, IReadOnlyList<Diagnostic> Diagnostics);
public interface IConfigLoader { ConfigLoadResult Load(ConfigSources sources); }   // never throws for user mistakes

// Launcher.Core.Library
public readonly record struct GameKey(string SystemId, string PathKey);   // stable across rebuilds and case-only renames
public readonly record struct GameRow(long GameId, string Title, string? CoverPath, bool IsFavourite);  // only what a cell draws; paths relative to DataDir
public interface ILibrary {
    Task<IReadOnlyList<SystemSummary>> GetSystemsAsync(CancellationToken ct);   // boot: one small indexed query
    Task<GameList> GetGamesAsync(string systemId, CancellationToken ct);        // entry: compact, pre-sorted rows
    Task<IReadOnlyList<GameMediaRow>> GetGameMediaAsync(string systemId, IReadOnlyList<string> kinds, CancellationToken ct);  // M6: the theme's slot kinds
    Task<IReadOnlyList<GameMediaRow>> GetGameMediaAsync(IReadOnlyList<long> gameIds, IReadOnlyList<string> kinds, CancellationToken ct);
    Task<IReadOnlyList<VirtualGameRow>> GetFavouritesAsync(CancellationToken ct);
    Task<IReadOnlyList<VirtualGameRow>> GetRecentlyPlayedAsync(int limit, CancellationToken ct);
    Task<GameDetails?> GetGameAsync(long gameId, CancellationToken ct);         // the focused item and launching
    Task<GameDetails?> GetGameAsync(GameKey game, CancellationToken ct);        // --launch, virtual systems
    Task SetFavouriteAsync(GameKey game, bool favourite, CancellationToken ct);
    Task SetEmulatorOverrideAsync(GameKey game, string? emulatorId, CancellationToken ct);   // null = the system's
    Task SetTitleOverrideAsync(GameKey game, string? title, CancellationToken ct);
    Task SetHiddenAsync(GameKey game, bool hidden, CancellationToken ct);
    Task<ScanSummary> RescanAsync(string? systemId, IProgress<JobProgress>? progress, CancellationToken ct);
    Task<ScanSummary> RebuildAsync(IProgress<JobProgress>? progress, CancellationToken ct);   // new library.db from disk, no network, swapped in atomically
}
public interface IPlayHistory {                                                  // LibraryService implements it
    Task<long> BeginSessionAsync(GameKey game, string emulatorId, DateTimeOffset startedAt, CancellationToken ct);
    Task EndSessionAsync(PlaySessionEnd end, CancellationToken ct);             // closes the session and updates play_stats, in one transaction
    Task<PlayStats?> GetPlayStatsAsync(GameKey game, CancellationToken ct);
}

// LibraryService (M6): raised on a worker thread after a rescan changed media files, a scrape saved media,
// a clear, a rebuild (Games null) or a bake (Games null).
event EventHandler<MediaChangedEventArgs> MediaChanged;
public readonly record struct MediaRef(string Path, float Aspect, long SizeBytes, long MtimeMs);   // Path: media/<system>/<kind>/..., relative to DataDir

// Launcher.Core.Theming (M6)
public static class ThemeLoader {                                               // never throws for user mistakes
    public static ThemeLoadResult Load(ThemeSource source, Look? fallback);    // fallback: the built-in theme's look
}
public static class ThemeCatalog {
    public const string BuiltInId = "memory-card";
    public static ThemeSet Load(IReadOnlyList<ThemeSource> builtIns, IReadOnlyList<ThemeSource> users, string wantedId, List<Diagnostic> diagnostics);
}
public sealed class ModelResolver {                                             // pure; precedence in A7
    IReadOnlyList<ModelCandidate> GameTemplates(string systemId);             // best first; the app uses the first that loads
    ModelCandidate PerGame(string relativePath);                               // the indexed DataDir/media/<system>/model/... file
    IReadOnlyList<ModelCandidate> SystemModels(string? systemId);              // null: Favourites and Recently played
    Rgb? ColourOf(string systemId);  Look LookFor(string? systemId);
}
public sealed record SlotChain(int Slot, IReadOnlyList<SlotSource> Sources) {  // media kinds, then "generated" or "authored"
    SlotResolution Resolve<TMedia>(int from, ref TMedia media) where TMedia : struct, IMediaAvailability;  // no allocation
}

// Launcher.Core.Models (M6 part 2): no Godot
public static class ModelInspector {                                           // never throws for a bad file
    static ModelInspection Inspect(ReadOnlySpan<byte> glb, ModelKind kind);     // Report (counts, slots, clips, errors, warnings) + images
}
public static class ModelProcessor {                                           // inspect, scale oversized textures down, repack
    static ProcessedModel Process(ReadOnlySpan<byte> glb, ModelKind kind, IImageDecoder? decoder, string scratchDir);
}
public sealed class ModelCache {                                               // CacheDir/models/<source>-<version>.glb + .json
    CachedModel Get(string sourcePath, ModelKind kind, string? description);  // processes once; a rejection is remembered and logged
    void Put(string sourcePath, ModelKind kind, ProcessedModel processed);  void Forget(string sourcePath);
}
public static class ObjConverter {                                             // OBJ + MTL + textures -> GLB
    static ConvertedModelFile FromZip(Stream zip, IImageDecoder? decoder, string scratchDir);
    static ConvertedModelFile FromFile(string objPath, IImageDecoder? decoder, string scratchDir);
}
public sealed class ModelImportService {                                       // M7's game options panel; odyssey-scrape import-model
    Task<ModelImportResult> ImportGameModelAsync(GameKey game, string sourceFile, CancellationToken ct);  // .glb, OBJ zip or .obj
    Task<ModelRemoveResult> RemoveGameModelAsync(GameKey game, CancellationToken ct);
    Task<(string Path, ModelReport Report)?> GetGameModelAsync(GameKey game, CancellationToken ct);
    Task<ModelImportResult> ImportSystemModelAsync(string systemId, SystemModelSlot slot, string sourceFile, CancellationToken ct);  // M7 part 2: Card | GameTemplate
    Task<bool> RemoveSystemModelAsync(string systemId, SystemModelSlot slot, CancellationToken ct);
    Task<ModelReport?> GetSystemModelAsync(string systemId, SystemModelSlot slot, CancellationToken ct);
}

// Launcher.Core.Media and Library (M7 part 2): the game options panel
public sealed class UserArtService {                                           // DataDir/media/<system>/<kind>/<rel path>.<ext>
    Task<UserArtResult> SetAsync(GameKey game, string kind, string sourceFile, CancellationToken ct);  // copied (replacing the kind's file), baked, indexed
    Task<UserArtResult> RemoveAsync(GameKey game, string kind, CancellationToken ct);                  // the slot is empty until a scrape fills it
}
// LibraryService
Task<IReadOnlyList<GameMediaInfo>> GetGameMediaInfoAsync(long gameId, CancellationToken ct);  // kind, file, size
Task<GameMetadataEdit?> GetMetadataEditAsync(GameKey game, CancellationToken ct);           // scraped title and metadata, and the user's overrides
// ScrapeService
Task<SystemScrapeCount> CountSystemAsync(string systemId, CancellationToken ct);            // its games, and how many are missing

// Launcher.Core.Scraping (M4)
public interface IScraper {                                                     // thread-safe; bounds its own requests
    string Id { get; }                                                          // "screenscraper" | "igdb" | "steamgriddb" | "steam"
    ScraperCapabilities Capabilities { get; }                                   // the fields and media kinds it can supply
    string? Unavailable { get; }                                                // null, or why not (missing credentials, and where to put them)
    string? Unsupported(SystemConfig system);                                   // e.g. no screenscraper_id / igdb_platforms
    int MaxConcurrency { get; }
    Task PrepareAsync(CancellationToken ct);                                    // once per run: account limits (ScreenScraper)
    Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken ct);  // by file (name, size, hashes) or a title search
    Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken ct);  // a stored or manual match
    Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken ct);  // for manual matching (M7)
    Task<ScrapeCandidate?> IdentifyFileAsync(ScrapeQuery query, CancellationToken ct);  // manual matching: the file's own match (ScreenScraper's ROM index)
    Task<string> TestConnectionAsync(CancellationToken ct);                     // M7: one cheap request; throws ProviderException
    Task<byte[]> DownloadAsync(ScrapedMedia media, CancellationToken ct);
}
public sealed class ScrapeService : IDisposable {                               // events on worker threads
    event EventHandler<ScrapeBatchEventArgs> BatchStarted, BatchFinished;
    event EventHandler<ScrapeProgressEventArgs> Progress;                       // batch, total, done, failed, current game
    event EventHandler<ScrapeGameEventArgs> GameScraped;                        // status, providers, media, per-provider log
    event EventHandler<ProviderNoticeEventArgs> ProviderNotice;                 // skipped (no credentials) or resting (quota)
    IReadOnlyList<ProviderStatus> GetProviders();
    Task<ScrapeBatchResult> ScrapeGameAsync(GameKey game, CancellationToken ct);
    Task<ScrapeBatchResult> ScrapeSystemAsync(string systemId, CancellationToken ct);
    Task<ScrapeBatchResult> ScrapeAllMissingAsync(CancellationToken ct);        // never successfully scraped, plus no front cover
    Task<MatchSearch?> SearchMatchesAsync(GameKey game, string? term, CancellationToken ct);  // manual matching: every provider's results
    Task<ScrapeBatchResult> ScrapeGameWithMatchAsync(GameKey game, string provider, string providerGameId, CancellationToken ct);  // the chosen result first
    Task<IReadOnlyList<ScrapeBatchResult>> ResumeAsync(CancellationToken ct);   // batches a stopped run left unfinished
    Task CancelBatchAsync(long batchId);                                        // cancelling a call's token does this too
    Task<ClearResult> ClearGameAsync(GameKey game, CancellationToken ct);
    Task<ConnectionTestResult> TestConnectionAsync(string providerId, CancellationToken ct);  // M7; never throws for a refusal
    Task<MissingSummary> CountMissingAsync(CancellationToken ct);              // M7: what "scrape all missing" would take on
    DerivativeService Derivatives { get; }
}

// Launcher.Core.Config (M7): writing
public sealed class TomlEditor {                                                // over Tomlyn's syntax tree: what isn't edited stays as written
    static TomlEditor? Parse(string text, string source, out Diagnostic? error);  // null: a syntax error, so it isn't edited
    object? Get(IReadOnlyList<string> path);  void Set(IReadOnlyList<string> path, object value);  bool Remove(IReadOnlyList<string> path);
}
public sealed record ConfigEdit(ConfigFileKind File, IReadOnlyList<string> Path, object? Value);  // null: the default again
public sealed class ConfigWriter {                                              // thread pool; validated, then atomic
    ConfigSaveResult Save(IReadOnlyList<ConfigEdit> edits);                     // a Problem (nothing written), or the files written and config reloaded
}

// Launcher.Core.Platform and Files (M7): the pickers
public interface IFileLocations {
    IReadOnlyList<FileLocation> Drives();                                       // fast: letters, types, a mapped drive's share
    string? VolumeLabel(string root);                                           // may block on a disconnected share: a worker, never waited on
    IReadOnlyList<FileLocation> QuickAccess();                                  // the user's folder, Desktop, Downloads
}
public static class DirectoryListing {                                          // never throws for a folder it can't read
    static DirectoryListingResult List(string folder, FileFilter? filter, CancellationToken ct, ListingProgress? progress = null);
}

// Launcher.Core.Media (M4)
public sealed class MediaStore {
    static string RelativePathFor(string systemId, string relPath, string kind, string extension); // media/<system>/<kind>/<rel path><ext>
    Task<StoredMedia?> SaveAsync(string systemId, string relPath, string kind, ReadOnlyMemory<byte> content, CancellationToken ct);  // atomic; sniffs the format; null: the game has a file of that kind
}
public interface IImageDecoder {                                                // the OS's codecs; Windows: WIC
    bool TryDecodeScaled(string path, int width, int height, Span<byte> rgba, out string? error);
}
public interface IVideoDecoder {                                                // 2026-10-02: Windows: Media Foundation; a reader stays on its thread
    IVideoReader? OpenVideo(string path, out string? error);                    // Width, Height, PixelAspect, Duration; ReadFrame(rgba, out time), Seek
    IAudioReader? OpenAudio(string path, out string? error);                    // Channels, SampleRate; Read(interleaved floats); null: no sound
}

// Launcher.Core.Launching
public sealed record LaunchPlan(string EmulatorId, string EmulatorName, string Executable,
    IReadOnlyList<string> Arguments, string WorkingDirectory, string? Core,     // arguments final and unquoted
    bool RunFile = false, bool Detached = false);                               // Detached: opened, not followed (a Steam shortcut)
public static class LaunchPlanner {                                             // pure, unit-tested
    public static LaunchPlanResult Plan(AppConfig config, GameDetails game, string? emulatorOverride = null);
}
public sealed class LaunchService {                                             // one game at a time
    event EventHandler<LaunchStartingEventArgs> Starting;                       // plan made, files exist
    event EventHandler<LaunchRunningEventArgs> Running;                         // process id
    event EventHandler<LaunchExitedEventArgs> Exited;                           // exit code, duration
    event EventHandler<LaunchFailedEventArgs> Failed;                           // reason for the user
    Task<LaunchOutcome> LaunchAsync(GameDetails game, string? emulatorOverride, CancellationToken ct);
}

// Launcher.App.Textures (Godot side), as built in M5 and given slot channels in M6: a class, not an interface
public sealed class TextureStreamer {
    void CreateBootArray();                                                        // at boot: the cover-class (512²) array
    (Texture2DArray? Large, Texture2DArray? Small) BuildArrays(SlotLayout layout, ...);  // any thread: 512² and 256² arrays
    void Install(SlotLayout layout, Texture2DArray? large, Texture2DArray? small);  // main thread: a theme's layout
    void Request(int cell, int channel, int row, in MediaRef media);              // supersedes the cell's channel's last request
    void Cancel(int cell, int channel);  void CancelCell(int cell);
    void SetView(float centreRow, float direction);                                // priorities: nearest first, ahead of the scroll, covers first
    void PumpUploads(ITextureSink sink, long budgetBytes, int cap);               // main thread, once per frame
    void Evict();  void Restore();                                                 // while a game runs, and after
}
public interface ITextureSink { void OnLayerReady(int cell, int channel); void OnLayerMissing(int cell, int channel); }
```

**Match resolution for scraping (per game, per scraper):**
1. A manual match in `userdata.db`.
2. Otherwise, the match stored in `library.db` (if the provider no longer has that game, it's looked up again).
3. Otherwise, a lookup: ScreenScraper by file name, size and system id, plus CRC32, MD5 and SHA-1 for files up to `hash_limit_mb` (ScreenScraper asks for a hash); if that finds nothing, a title search. IGDB, SteamGridDB and the Steam store can only search by title (the Steam store never uses a shortcut's app id). A search hit counts only if its name matches the ROM's cleaned title (`TitleMatcher`, similarity ≥ 0.85, case-, accent-, punctuation- and article-blind).

Once matched, re-scrapes use `FetchAsync(id)` and never search again; the stored method (`filename`, `hash`, `search`, `manual`) is kept. Saved responses carry the matched id and method, so a rebuild recovers automatic matches offline, and manual corrections always win.

**Manual matching (2026-10-01).** The game options' "scrape this game" doesn't match the game by itself: every provider is searched, the user chooses the right result, and `ScrapeGameWithMatchAsync` saves it in `manual_matches` before it scrapes:
- A game's manual matches are asked first, the latest choice first (`matched_at`; choosing a match again makes it the latest), each fetched by its id; then the configured providers, as in any scrape, fill in only what's still missing. So the chosen game's data is what shows, in every later scrape and in a rebuild (`ScrapedRestore` merges in the same order). A provider with a manual match is asked even if `[scraping]` doesn't name it.
- What a provider whose manual match answered had brought in before, and the scrape didn't bring again, goes (`ScrapeStore.SaveReplacing`): its old match and log, its scraped media rows of kinds the chosen game doesn't have (files and derivatives too), and the metadata row if nothing was found and only such providers had supplied it (the title goes back to the file name's). So a corrected match leaves nothing of the wrong game behind. A provider that fails keeps what it had, and so does a kind whose download failed.
- Clearing the game forgets its manual matches.
- The first search (the game's own title) also asks each provider's ROM index for the file itself (`IdentifyFileAsync`: ScreenScraper's `jeuInfos.php` by name, size and hashes, as a scrape asks; the others have none), and its hit is listed first, as the file's match. A title search can't find an arcade set by its MAME short name (`1on1gov`), but the ROM index can (2026-10-02). A typed name is a title search only.

**Provider selection (M4).** Each game is scraped by `[scraping] provider` first. Each `fallback` provider, in order, is then asked only if its capability map has a field or media kind still missing, and it fills only those: every field comes from the first provider that has it. Media: each wanted kind the game has no file for (A4: a download never replaces one) is downloaded from the first provider that offers it, falling through to the next if a download fails. Capabilities: ScreenScraper has every field and every scrapable kind (`box-2D` the cover, `box-2D-back` the back, `box-2D-side` the spine, `ss` the screenshot, its wheel (`wheel-hd` first) the logo, `fanart` the hero, `support-texture` the label, and its video (`video-normalized` first)); IGDB every field, the cover, a screenshot and artwork (as the hero); SteamGridDB the cover (community capsule art), hero and logo, and no metadata; the Steam store (only for systems with `steam_store = true`) Steam's own library capsule as the cover, its library hero, logo and first screenshot, and the title, description, release date, developer, publisher and rating (its share of positive reviews), but no genre or players. Only ScreenScraper has back, spine, label and video. Box textures aren't scraped (2026-10-01): the `box_texture` slot takes the user's own art. `[scraping] media` says which kinds are downloaded (the settings' Media page); a video's download may take 5 minutes an attempt, every other request 30 s, timed from leaving the provider's gate.

**Scrape status.** A game is `ok` (found, nothing failed), `partial` (found, but a provider failed or was resting), `not_found` or `error` (nothing found; something failed); no `scrape_state` row means never scraped. "Scrape all missing" takes games never scraped, `not_found` or `error`, plus every game without a cover row.

**Limits and failures.** Each provider's `ProviderGate` holds its requests in flight (ScreenScraper: the account's `maxthreads`; IGDB 4 of its 8; SteamGridDB 2; the Steam store 2), its rate (IGDB 4 a second; SteamGridDB 4 a second; the Steam store 1 a second, its limits being undocumented; ScreenScraper the account's `maxrequestspermin`) and pauses. A 429 or 5xx is retried up to 5 times with exponential backoff (2 s doubling, jitter, capped at 2 minutes; Retry-After honoured), pausing the whole gate on a 429. A used-up quota (ScreenScraper 430, 431, or its reported counters) rests the provider until ScreenScraper's midnight (French time), and refused credentials until the app restarts; the gate refuses queued requests at once, games carry on with the other providers and are marked `partial`, and a `ProviderNotice` says why.

## A3. Performance design

**Targets.** M1 measured these on the baseline hardware ([SPIKE_RESULTS.md](SPIKE_RESULTS.md)). The hitch wording and the new targets marked *(M1)* are proposals awaiting the owner's sign-off.
- First interactive frame under 1 s **for our code**, on a warm start with a 10,000-game library.
  - The clock starts at our first code, the first autoload's `_EnterTree` (mark `autoload_enter_tree`), and stops at `interactive`. The bench reports this as `app_startup_ms`.
  - M1 measured 186–449 ms on the synthetic grid (204 ms for the chosen configuration). M2 re-checks it with real config and DB loading.
  - Engine and .NET start-up before our code is outside the target, but it's still reported in `startup_ms`. It takes about 1.0–1.7 s, depending on the renderer, driver and session (see [perf/m1-spike.md](perf/m1-spike.md) and [SPIKE_RESULTS.md](SPIKE_RESULTS.md)).
- Locked to the display refresh rate while scrolling: p99 frame interval ≤ 1.1× the refresh interval.
- **No hitches caused by the launcher** *(reworded by M1)*. Over 3 × 60 s scripted scrolls:
  - hitches are no more than the no-texture control's in the same session
  - 0 frames exceed 2× the refresh interval
  - there are 0 hitches in fullscreen

  Windowed on the Deck, the environment alone gives 0–2 hitches per 60 s run, through a periodic present delay about every 5 s that isn't caused by the launcher.
- *(M1)* The visible grid is textured ≤ 100 ms after the first frame, with derivatives in cache. M1 measured 10 ms with BC7.
- *(M1)* While scrolling at the maximum repeat speed, ≥ 99% of on-screen cell-frames show their cover. M1 measured 100%.
- *(M1)* The working set is ≤ 512 MB while browsing 10,000 games (M1: 324–481 MB). The cover pool's texture memory is ≤ 64 MB with BC7 (M1: 40–45 MB).

**Baseline hardware:** a Steam Deck (LCD APU: 4c/8t Zen 2, 8 CU RDNA2, 16 GB shared memory) running Windows 11. The targets must hold in two modes:
- handheld at 1280×800
- docked to a 3840×2160 display at 59.94 Hz, with 3D rendered at a capped internal resolution

**Measurement:**
- `--bench`, on an exported ExportRelease build only (`tools/bench-export.ps1`). Editor runs use Debug assemblies and the editor binary.
- `app_startup_ms` = `interactive` − `autoload_enter_tree`. `DebugHooks` must stay the first autoload, and it warns if it isn't.
- The bench's frame window starts at `interactive` (M5). The engine can draw an empty frame before the scene is built, and an interval spanning the build is start-up, not a hitch.
- Scenarios (M5): `boot` samples frames on the systems grid; `scroll` enters the biggest system and scrolls it from the first row to the last in 60 s (the M1 rate), measuring the scroll frames alone; `--no-textures` is the control.
- Frame times come from raw `Time.GetTicksUsec()` at `frame_post_draw`. Godot smooths `_Process` delta, which hides hitches.
- A **hitch** is any frame interval longer than 1.5× the refresh interval.
- Scroll statistics cover only the scripted scroll frames. Each hitch-target run is paired with a no-texture control in the same session.
- Don't poll Windows performance counters during a frame-time run: in M1 it added hitches.
- Compare start-up only within one session. It moves by 100–200 ms from one session to the next.

**Boot path:**
1. Engine and .NET start-up. This is outside the target, but M1 still measures ReadyToRun and the shader baker, because they also cut the JIT and shader work inside it.
2. Settings, theme and systems config, in about 10 ms. M1 measures Tomlyn's first-use cost. The theme (M6): the built-in and user manifests, and each system's model candidates, on the thread pool; its models start loading as soon as it's resolved, while the DB opens.
3. Open `library.db` read-only and run `SELECT system_id, game_count FROM systems`, in about 5 ms.
4. Models (M6): the theme's models are parsed and converted on workers in parallel while the DB opens (built-ins from the PCK; user models from `CacheDir/models/`, processed on first use). Per-game models load when their list does.
5. First frame, then the `interactive` mark.

Everything else waits until after `interactive`, and nothing is scanned at boot. The boot splash is off, with the theme's colour behind it.

**Entering a system:**
- One indexed query on the thread pool: games joined to their effective `cover`, with `userdata.db` ATTACHed for favourites and overrides.
- Results reach nodes through the budgeted main-thread queue, **not** through plain `await` continuations. Godot's `SynchronizationContext` runs every pending continuation each frame, with no budget.
- Only the visible cells are bound.

**Texture streaming:**
- **Media slots (M6).** A template's materials named after a media kind are slots; each slot walks its fallback chain (A7) for each game. Only slots whose chains name a media kind get texture layers, and only the kinds the chains name are queried ("load only the slots a template uses"). **Media is standardised per slot:** every derivative is the whole image squeezed into a 512² BC7 DDS with a full mip chain (below); the cover's layers are 512² and use it whole; every other slot's layers are 256² and use its mip chain from mip 1 (the worker skips the DDS header and mip 0, and `Image.SetData` takes the rest: no second bake). So any image can fill any slot, and a slot's size never depends on the media. The shader crops by the media's own aspect (`media.width`/`height`).
  - **Memory:** the cover array is 64 × 341 KB = 21.8 MB; each other slot adds 64 × 85 KB = 5.5 MB. All eight slots would be 60.1 MB, under the 64 MB pool target; the built-in theme's three (cover, back, spine) are 32.8 MB.
  - **Why not per-slot arrays at 512²:** three would already be 65.5 MB, over the pool target, and a slot other than the cover is smaller on screen (a spine, a back, a screenshot panel).
  - **Filtering: 16× anisotropic** (`rendering/textures/default_filters/anisotropic_filtering_level=4`; the samplers ask for `filter_linear_mipmap_anisotropic`). Squeezing makes the texel density differ by axis: a 60×680 spine is 256 texels across 60 pixels and 256 down 680, about 8 texels a screen pixel across a focused spine and under 1 along it. At Godot's default 4× the GPU took a mip too small for the spine's length, and its title blurred away ([perf/anisotropy.md](perf/anisotropy.md)).
- **Baked derivatives are mandatory.** The grid only reads cached derivatives from `CacheDir/textures/`: one canonical size, with mipmaps, keyed by source path, size and mtime.
  - They're baked at scrape time and by a background job.
  - A missing derivative shows the placeholder and queues a low-priority bake.
  - **The whole source image is squeezed into the square** (M5), whatever its aspect ratio, and the shader crops it to the face using the source's aspect from `media.width` and `height`. So one derivative serves every template, and changing a system's template doesn't invalidate it.
  - **Format (M1): BC7 in DDS, 512×512, full mip chain (341 KB).**
    - Decode is 0.26 ms per cover, against 5.4 ms for PNG and 4.1 ms for JPEG.
    - GPU memory is 4× smaller than RGBA8.
    - The visible grid is textured 10 ms after the first frame, against about 100 ms.
    - BC1 (171 KB) is an option for a low-memory setting. KTX, Godot `.res` and raw blobs were measured and rejected.
    - Real art is centre-cropped to the face in the shader (above).
  - **The encoder (M4): our own, in Core (`Bc7Encoder`).** BC7 mode 6 for every block, and mode 1 (two subsets from 64 partitions) for opaque blocks where mode 6 fits badly, which are the edges: text, outlines, logos. About 0.44 s a real cover with mips on the Deck, and 40 dB PSNR on real Mega Drive box art, slightly better than BCnEncoder.Net, which took about 10 s a cover ([perf/m4-scraping.md](perf/m4-scraping.md)). Images are decoded and scaled by the OS (`IImageDecoder`: WIC on Windows). `Image.Compress` returns `Unavailable` in export templates, so the app couldn't use Godot's.
  - **Baking:** a scraped cover is baked as it's saved; `DerivativeService.BakeMissingAsync` bakes every cover without one (the user's art too), after the app's background scans and by `odyssey-scrape bake`, and deletes derivatives no cover names. Both on one below-normal thread.
- **Loading:**
  - Workers read each file into a **per-worker pooled buffer** (`File.OpenHandle` plus `RandomAccess.Read`) and decode it with `Image.LoadDdsFromBuffer(ReadOnlySpan<byte>)`.
  - `Image.LoadFromFile` can't read DDS or KTX in 4.7.
  - **Workers never create per-texture managed `byte[]`s**, because those churn the large object heap and cause gen2 GC pauses. Cache path strings per binding too: M1's worker allocations caused 4–7 gen0 collections a minute.
  - There are `clamp(ProcessorCount / 4, 1, 4)` workers, which is 2 on the Deck. M1 confirmed 2: 4 workers didn't help PNG, and raised each decode by about 1 ms through contention.
- **Priority:** distance from the view centre, with rows ahead of the scroll counting 0.6× as far. Requests for rows already scrolled past are cancelled by re-binding (the generation changes).
- **Upload:**
  - **Every pool texture is created at boot, and only *updated* while browsing**, on the main thread: `Texture2DArray.UpdateLayer` takes 0.03 ms for BC7 and 0.17 ms for RGBA8.
  - Creating a texture on the main thread has 17–66 ms outliers, so it never happens while browsing.
  - `RenderingServer.Texture2DCreate` from a worker works in 4.7 without stalling the main thread, but it blocks the worker for about 12 ms per call. It's only for one-off textures outside the pool, such as the focused item's full-resolution art.
  - The budget is **4 MB per frame**; BC7 only reaches it in the first frames. The cap is **4 cover-sized uploads per frame** (M6; M1 proposed 8 because a few hitch frames followed a burst of uploads, and M5 kept 8). A 256² layer counts a quarter of a cover's, their size ratio. M6 found bursts of 5 to 8 covers in one frame (a whole row being bound) make single uploads take 14–21 ms; capped at 4 the longest was 1 ms, and the grid stayed 100% textured ([perf/m6-themes.md](perf/m6-themes.md#upload-cap)).
  - Workers take covers first: another slot's request counts as 0.35 rows further away.
  - Warm the first upload at boot, while the DB opens (M5), because the first one takes up to 43 ms.
  - Godot's upload staging buffer is capped at 16 MB (`rendering_device/staging_buffer/max_size_mb`; the default is 128). At 2560×1440 the default grew the working set past 512 MB ([perf/m5-navigation.md](perf/m5-navigation.md)).
- **Per-game models (M6 part 2)** stay resident for the shown list and the three cached ones, at about 0.3 MB each on D3D12 whatever their size (each mesh surface's three buffers are placed on 64 KB boundaries). 300 of them on the 3,000-game library put the working set at 512–515 MB, at the target ([perf/m6-models.md](perf/m6-models.md#memory)); streaming them by the visible rows is the next step for bigger lists.
- **Memory:** an LRU cache with a starting budget of 256 MB.
  - Evicted textures and uploaded `Image`s are `Dispose()`d at once.
  - The focused item upgrades to the full-resolution art.

**Rendering:**
- **The Mobile renderer, on D3D12** (M1). Its GPU time is 36–42% lower than Forward+ with the same frame pacing, and its output matches within 4/255.
- No shadows, GI, SSAO, SSR or glow; the tonemapper is Linear.
- 3D renders at ≤1080p internally when docked at 4K, upscaled with bilinear. The 2D UI renders at native resolution.
  - At 2560×1440 fullscreen, Forward+ took 6.45 ms of GPU time native and 2.43 ms at 0.5 scale; Mobile took 1.70 ms at 0.5 scale.
  - Native 4K on Forward+ would be about 14.5 ms.
  - M5 applies the cap automatically: `Scaling3DScale = min(1, 1080 / window height)`, bilinear; `--render-scale` and `--upscaler` override it. **FSR1 isn't available on the Mobile renderer** (Godot warns and keeps bilinear). 3840×2160 still needs measuring on a 4K desktop.
- Unfocused idle motion runs in the vertex shader (`TIME` plus a per-instance phase), so it costs nothing in C#.
- A box shaped by its art (A7, 2026-10-01) is reshaped in the vertex shader from two texels per cell written at bind time, so it stays in its MultiMesh; every other item pays one texel fetch per vertex ([perf/box-shapes.md](perf/box-shapes.md)).
- The placeholder-to-cover fade happens **inside one opaque cover shader**, through a per-instance `fade` parameter. There's no alpha blending and no extra variant.
- User `.glb` materials are remapped onto the fixed shader set. Items drawn as nodes (per-game models, clips) use the same materials, with their per-cell data in an instance uniform (M6).
- Every template is drawn once in the first frame, faded exactly into the background (M5), so its pipeline is compiled before `interactive`. Ubershaders and the on-disk pipeline cache cover warm starts, and **the export's shader baker** covers cold ones (M5: cold start-up of our code 1.2–1.4 s baked, 2.3–2.4 s not). The baker needs a rendering device, so exports aren't headless.
- **Transitions fade opaque items into the background** in the shader: albedo and specular go to zero while emission becomes the gradient's colour at that pixel. No blending, no extra variant. Items near the top and bottom of the screen fade the same way, under the overlay's text.
- Glyphs: printable ASCII is pre-rendered at the title atlas's sizes in the warm-up, one size a frame. Anything else is rasterised when first shown: pre-rendering all of Latin-1 at every size cost about 130 MB and a 150–220 ms frame (M5). No font is bundled yet (a theme's `[ui]` section, later).

**C# rules:**
- No allocations in per-frame code: no LINQ, closures, boxing, string formatting or implicit `string`→`StringName` conversions. Cache every `StringName` and `NodePath`.
- `GCSettings.LatencyMode = SustainedLowLatency` while browsing.
- Update transforms only for items that move.
- Never `.Wait()` or `.Result` on the main thread.
- The bench reports `GC.GetAllocatedBytesForCurrentThread()` for the main thread. **The ceiling is 4 KB per 60 s scripted scroll** (M1 measured 0.6 KB), with no GC caused by the main thread.

**M1 experiments.** Results are in [SPIKE_RESULTS.md](SPIKE_RESULTS.md). Items marked "later" moved to the milestone named when M1 closed.
- Done: renderer (Forward+ against Mobile, on the grid) → Mobile/D3D12. The driver matrix was run on the scaffold only; Compatibility wasn't benched on the grid.
- Done: per-node materials against a `Texture2DArray` indexed per instance, and MultiMesh against nodes → MultiMesh plus `Texture2DArray` for templates.
- Done: derivative format and upload path → BC7 DDS; update pre-created textures on the main thread. The encoder: our own, in Core (M4).
- Done: upload budget and decode worker count → 4 MB per frame (measured) and 2 workers. The cap of 8 uploads per frame: no measurable difference at the M1 scroll rate (M5), kept.
- Partly done: the 4K render scale. Measured at 2560×1440 only (M1, M5); FSR1 needs Forward+ (M5). 3840×2160 needs the desktop at 4K.
- Done (M5): the export shader baker, now on (halves a cold start). ReadyToRun needs the crossgen2 runtime pack from NuGet, so it waits for the owner's approval.
- Done (M2): config parse → hand mapping from Tomlyn's syntax tree, the only API that keeps key positions. A warm load of the three default files takes 2 ms; the first load in a process takes about 50 ms, nearly all JIT. No snapshot cache ([perf/m2-core.md](perf/m2-core.md)).
- Partly done (M2): Microsoft.Data.Sqlite's native load. In a self-contained .NET 8 console, the first `LibraryService.OpenAsync` takes about 120 ms, including creating both DBs. Inside Godot, M3's `--launch` smoke test shows it loads in both the editor run and the export; timing it there is later (M5).
- Done (M6): runtime `.glb` conversion on a worker thread: about 27 ms a built-in box, 7 ms a per-game model ([perf/m6-themes.md](perf/m6-themes.md), [perf/m6-models.md](perf/m6-models.md)).
- Partly done (M2): a net10.0 comparison build. For Core it's no faster (full scan 304 ms against 274 ms). The Godot-side comparison is later (M5). Adopting it needs the owner's approval.
- Later: PresentMon, to explain the periodic present delay and M5's frame-pacing jitter (p99 about 21 ms with or without the grid), if the owner is happy to install it.

## A4. Storage

| Location | Windows default | Contents |
|---|---|---|
| ConfigDir | `%APPDATA%\OdysseyLauncher` | `settings.toml`, `systems.toml`, `emulators.toml`, `secrets.toml`, `themes/<id>/`, `models/{systems,templates}/` (the user's per-system models) |
| DataDir | `%LOCALAPPDATA%\OdysseyLauncher` | `library.db`, `userdata.db` (plus the last 3 backups), `media/<system>/<kind>/<rel path>.<ext>` (the media folder: every game's images, full size, videos and per-game models, `kind` being `model`; scraped or the user's own alike), `scraped/responses/<provider>/<system>/<path_key>.json` (only with `--save-responses`), `tokens/igdb.json` (IGDB's cached access token), `logs/` (M6: `models.log`, the model problems the user can read), `picker-locations.json` (M7: each picker use's last folder) |
| CacheDir | `%LOCALAPPDATA%\OdysseyLauncher\cache` | `textures/` (derivatives), `models/` (processed user models, `<source>-<version>.glb`, each with its report as `.json`: M6) |

- **Where things go:**
  - ConfigDir holds user intent and user content.
  - DataDir holds what would need the network or the user to recreate.
  - CacheDir holds only what can be regenerated locally; it's safe to delete at any time.
- **Portable mode:** a `portable.txt` next to the executable puts all three under `<exe dir>\userdata\`.
- **Linux (later):** the XDG directories.
- **ROMs:**
  - Each system's folder defaults to `{rom_root}/<system id>`, and `rom_root` defaults to `{home}/ROMs`.
  - System ids follow ES-DE and RetroBat naming (`megadrive`, `mastersystem`, `gb`, `saturn`, `dreamcast`, `psx`, `ps2`), so existing collections work without moving files.
  - A system can list `aliases` (such as `genesis`). With no `rom_dirs`, the first of `{rom_root}/<id>`, `{rom_root}/<alias>`... that exists is used. `userdata.db` rows stored under an alias are re-keyed to the canonical id when the library opens.
  - `rom_dirs` replaces the default with one or more folders, scanned in order (M2).
- **Identity:**
  - `rel_path` is the path as on disk: relative to its ROM folder, `/`-separated, Unicode NFC.
  - `path_key` is `rel_path` lower-cased (invariant) on every OS. It's the stable identity, and it keeps keys portable.
  - Within a system, `path_key` is unique across all its folders. If two files collide (after case-folding on Linux, or the same relative path in two folders), the scanner keeps the one in the earlier folder, or the first in ordinal order, and warns.
  - Because the folder isn't part of the identity, moving a system's ROMs to another folder or drive keeps their user data.
- **Why `path_key`:** keying on the full path, extension included, keeps `Game.cue` and `Game.chd` apart, and a case-only rename keeps its user data.
- **Stored paths:** app-written files are named by `path_key`, except media, named by `rel_path` (A4 The media folder). The DB stores paths relative to their root (media: DataDir), never absolute paths.
- **Rebuildable:** `library.db` is a pure function of config, the ROM folders, `media/`, and `scraped/` (when responses were saved).
  - A rebuild writes a new file offline (`library.db.rebuild`, in rollback-journal mode so it's one self-contained file), then closes every connection and swaps it in with a replacing move.
  - A golden test checks that a rebuild equals the incrementally built DB, ids and timestamps excluded.
- **Missing folders:** a scan of a folder that no longer exists (an unplugged drive) removes its games from `library.db`; their user data stays (see Orphans).
- **Multi-file games:** an `.m3u` hides the discs it lists, a `.cue` its `FILE` tracks, and a `.gdi` its track files, so the playlist is the one game. References resolve against the playlist's folder, match by `path_key`, and can't point outside the ROM folder. A playlist over 256 KB isn't read. Disc systems' default extensions leave out `.bin`, so stray tracks never show.
- **Titles:** `TitleParser` peels trailing `(...)` and `[...]` groups off the file name. The first all-region group is the region, the first language list (`En,Fr,De`) is the languages, and the first `Rev`/`v` and `Disc` tags are the revision and disc. Everything else is kept, as written, in `tags`. A trailing article moves to the front (`Legend of Zelda, The` → `The Legend of Zelda`), and a lone disc keeps " (Disc n)" in its title. The sort key is lower-case and accent-free, drops a leading The/A/An, sorts numbers naturally, and puts a game's discs right after it.
- **Back up:** ConfigDir, `userdata.db` and `media/`, which holds the user's own images and models as well as scraped ones.
- **The media folder (2026-10-02):** `DataDir/media/<system>/<kind>/<rel path>.<ext>` holds every game's media, whoever put it there: scraped images and videos, the user's own images, and per-game models (kind `model`, `.glb`). A file named after the ROM's whole `rel_path` (`Game (Europe).iso.png`) is that ROM's; one named without the ROM's extension (`Game (Europe).png`) is every ROM of that name's. The scanner indexes it all (`MediaScanner`), and a row doesn't record where its file came from. There's one file per game and kind: a scrape downloads only kinds the game has no file for and never replaces one (so to get a kind scraped again, remove its file: Y in the game's images, or clear the game), and the user's own image replaces the game's file of that kind. Scraped files are named the way the user's are, by the ROM's `rel_path`, so a scan matches them alike.
- **Saved responses (2026-10-02)** are for debugging a scrape: off unless the app or `odyssey-scrape` is started with `--save-responses`. A ScreenScraper lookup that finds nothing saves what it was told too (status `not_found`): the file lookup's reply, and the title search's term, hit count and closest name. Without them a rebuild (or a re-added game) keeps its media, which is on disk, and its manual matches (`userdata.db`), but its scraped metadata and automatic matches come back only with the next scrape.
- **Orphans:** when a file disappears, its `userdata.db` rows are kept, so moving a ROM out and back loses nothing.

### `library.db` (schema version 4, `PRAGMA user_version = 4`)

The shipped files are `src/Launcher.Core/Data/Migrations/Library/0001_initial.sql`, `0002_media_file_stamps.sql` (M5: `media.size_bytes` and `mtime_ms`, the indexed file's size and time, so an unchanged file's header isn't read again, and so the grid can name its derivative without touching it; scraped media rows have them too), `0003_scraping.sql` (M4: `metadata.title`, the scraped title, and `scrape_state`, below) and `0004_media_folder.sql` (2026-10-02: `media.source` dropped, and every system marked never scanned, so the app rescans them all once into the media folder's rows). This copy is version 1, for reading.

```sql
-- 0003 (M4)
ALTER TABLE metadata ADD COLUMN title TEXT;   -- games.title also holds it, for the grid query; a lone disc keeps " (Disc n)"
CREATE TABLE scrape_state (                   -- no row = never scraped
  game_id     INTEGER PRIMARY KEY REFERENCES games(game_id) ON DELETE CASCADE,
  status      TEXT NOT NULL,                  -- 'ok' | 'partial' | 'not_found' | 'error'
  providers   TEXT,                           -- the providers that found it, in order: 'screenscraper,igdb'
  scraped_at  INTEGER NOT NULL
) STRICT;
```

`metadata.source` holds the providers that supplied fields (`'screenscraper,igdb'`), and `scraper_matches` and `scrape_log` take `igdb` too.

**Restoring scraped data (M4).** When a scan adds a game (after a rebuild, a recreated library, or a ROM moved back), its saved responses, if any were saved (`--save-responses`), are read back offline: each provider's parser turns its response into a game, the results merge in config order as a live scrape does, and matches return with their method. Media needs no restoring: the scan indexes the media folder.

```sql
CREATE TABLE systems (
  system_id   TEXT PRIMARY KEY,               -- config id, e.g. 'megadrive'
  scanned_at  INTEGER,                        -- unix ms; NULL = never scanned
  game_count  INTEGER NOT NULL DEFAULT 0      -- denormalised for the boot query
) STRICT;

CREATE TABLE rom_dirs (
  dir_id      INTEGER PRIMARY KEY,
  system_id   TEXT NOT NULL REFERENCES systems(system_id) ON DELETE CASCADE,
  position    INTEGER NOT NULL,               -- order in the system's folder list; earlier folders win path_key collisions
  path        TEXT NOT NULL,                  -- resolved absolute folder at last scan
  UNIQUE (system_id, path)
) STRICT;

CREATE TABLE games (
  game_id     INTEGER PRIMARY KEY,
  system_id   TEXT NOT NULL REFERENCES systems(system_id) ON DELETE CASCADE,
  dir_id      INTEGER NOT NULL REFERENCES rom_dirs(dir_id) ON DELETE CASCADE,
  rel_path    TEXT NOT NULL,                  -- as on disk: relative to its ROM folder, '/' separators, NFC
  path_key    TEXT NOT NULL,                  -- lower-invariant rel_path: the stable identity
  size_bytes  INTEGER NOT NULL,
  mtime_ms    INTEGER NOT NULL,
  crc32 TEXT, md5 TEXT, sha1 TEXT,            -- NULL until hash matching lands; cleared when size or mtime change
  title       TEXT NOT NULL,                  -- scraped title, else cleaned file name (user overrides live in userdata)
  sort_title  TEXT NOT NULL,                  -- internal sort key (TitleParser.SortKey)
  region      TEXT,                           -- file name tags, as written: 'USA, Europe'
  languages   TEXT,                           -- 'En,Fr,De'
  revision    TEXT,                           -- 'Rev 1', 'v1.1'
  disc        INTEGER,                        -- '(Disc 2)' on a disc that no .m3u groups
  tags        TEXT,                           -- every other tag, as written: '(Beta) [b1]'
  UNIQUE (system_id, path_key)
) STRICT;
CREATE INDEX games_by_system ON games(system_id, sort_title);   -- the games grid
CREATE INDEX games_by_dir ON games(dir_id);                      -- ON DELETE CASCADE from rom_dirs

-- Parsed .m3u/.cue/.gdi files, hidden ones included, so an unchanged playlist isn't re-read.
CREATE TABLE playlists (
  system_id   TEXT NOT NULL REFERENCES systems(system_id) ON DELETE CASCADE,
  path_key    TEXT NOT NULL,
  size_bytes  INTEGER NOT NULL,
  mtime_ms    INTEGER NOT NULL,
  refs        TEXT NOT NULL,                  -- referenced path_keys, '\n'-separated
  PRIMARY KEY (system_id, path_key)
) STRICT, WITHOUT ROWID;

CREATE TABLE metadata (
  game_id      INTEGER PRIMARY KEY REFERENCES games(game_id) ON DELETE CASCADE,
  description  TEXT, release_date TEXT,       -- ISO 8601, partial allowed ('1991', '1991-06')
  developer TEXT, publisher TEXT, genre TEXT, players TEXT,
  rating       REAL,                          -- 0..1
  source       TEXT NOT NULL                  -- scraper id
) STRICT;

CREATE TABLE scraper_matches (
  game_id          INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  scraper          TEXT NOT NULL,             -- 'screenscraper' | 'igdb' | 'steamgriddb' | 'steam'
  scraper_game_id  TEXT NOT NULL,
  method           TEXT NOT NULL,             -- 'filename' | 'hash' | 'manual'
  matched_at       INTEGER NOT NULL,
  PRIMARY KEY (game_id, scraper)
) STRICT;

CREATE TABLE media (                          -- one row per kind: the game's file in the media folder
  game_id  INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  kind     TEXT NOT NULL,                     -- cover | back | spine | box_texture | label | screenshot | logo | hero | video | model
  path     TEXT NOT NULL,                     -- relative to DataDir: media/<system>/<kind>/...
  width INTEGER, height INTEGER,
  source   TEXT NOT NULL,                     -- dropped by 0004: the media folder doesn't say where a file came from
  PRIMARY KEY (game_id, kind)
) STRICT;

CREATE TABLE scrape_log (
  game_id       INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  scraper       TEXT NOT NULL,
  status        TEXT NOT NULL,                -- 'ok' | 'not_found' | 'error'
  attempted_at  INTEGER NOT NULL,
  detail        TEXT,
  PRIMARY KEY (game_id, scraper)
) STRICT;
```

From 2026-10-01 `media.kind` can also be `video`: a scraped MP4, with no width or height (NULL), no derivative, and no slot; from 2026-10-02 the game's details screen plays it. No schema change.

### `userdata.db` (schema version 2)

This DB can't be rebuilt. It's keyed by `(system_id, path_key)`, never by `library.db` ids. The shipped files are `Data/Migrations/User/0001_initial.sql` and `0002_scraping.sql` (M4):

```sql
-- 0002 (M4): the user's metadata overrides, which scraping never writes (NULL = the scraped value)
ALTER TABLE game_overrides ADD COLUMN description TEXT;  -- and release_date, developer, publisher, genre, players (TEXT), rating (REAL)
-- The scrape queue: a batch survives the app closing. Jobs are deleted as they finish; a batch keeps its counts.
CREATE TABLE scrape_batches (batch_id INTEGER PRIMARY KEY, kind TEXT NOT NULL,   -- 'game' | 'system' | 'missing' | 'manual' (2026-10-01)
                             target TEXT, priority INTEGER NOT NULL,             -- single games (0) before batches (1)
                             total INTEGER NOT NULL, done INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
                             created_at INTEGER NOT NULL, finished_at INTEGER,   -- NULL = resume it
                             cancelled INTEGER NOT NULL DEFAULT 0) STRICT;
CREATE TABLE scrape_jobs    (batch_id INTEGER NOT NULL REFERENCES scrape_batches(batch_id) ON DELETE CASCADE,
                             seq INTEGER NOT NULL, system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             PRIMARY KEY (batch_id, seq)) STRICT, WITHOUT ROWID;
```

**Clearing a game (M4)** deletes its scraped metadata, scrape state and log, every match (manual ones too), every media row, the title and metadata overrides, its media files (scraped or the user's own, and from M6 its model, with the model's processed copy in `CacheDir/models/`) and their derivatives, and its saved responses, except a file another game also uses (matched by stem). The title goes back to the file name. Favourite, play history, emulator override and hidden stay.

```sql
CREATE TABLE favourites     (system_id TEXT NOT NULL, path_key TEXT NOT NULL, added_at INTEGER NOT NULL,
                             PRIMARY KEY (system_id, path_key)) STRICT, WITHOUT ROWID;
CREATE TABLE play_stats     (system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             play_count INTEGER NOT NULL DEFAULT 0, total_seconds INTEGER NOT NULL DEFAULT 0,
                             last_played_at INTEGER, PRIMARY KEY (system_id, path_key)) STRICT, WITHOUT ROWID;
CREATE INDEX play_stats_recent ON play_stats(last_played_at DESC) WHERE last_played_at IS NOT NULL;   -- Recently played
CREATE TABLE play_sessions  (session_id INTEGER PRIMARY KEY, system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             emulator TEXT NOT NULL, started_at INTEGER NOT NULL,
                             ended_at INTEGER, exit_code INTEGER) STRICT;      -- ended_at NULL = launcher died; closed on next start
CREATE INDEX play_sessions_open ON play_sessions(session_id) WHERE ended_at IS NULL;
CREATE TABLE manual_matches (system_id TEXT NOT NULL, path_key TEXT NOT NULL, scraper TEXT NOT NULL,
                             scraper_game_id TEXT NOT NULL, matched_at INTEGER NOT NULL,   -- the latest is asked first (2026-10-01)
                             PRIMARY KEY (system_id, path_key, scraper)) STRICT, WITHOUT ROWID;
CREATE TABLE game_overrides (system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             title TEXT, sort_title TEXT,                     -- NULL = use the scraped or file-name title
                             emulator TEXT,                                   -- NULL = the system default
                             hidden INTEGER NOT NULL DEFAULT 0,
                             PRIMARY KEY (system_id, path_key)) STRICT, WITHOUT ROWID;
```

**Play history (M3).**
- A session row is written when the emulator has started, with `ended_at` NULL.
- When the game ends, one transaction closes it (`ended_at` = start + the duration measured on a monotonic clock, `exit_code`) and adds to `play_stats`: `play_count` + 1, `total_seconds` + the duration rounded to the nearest second, and `last_played_at` = the session's end.
- A failed launch (a non-zero exit within 5 s) keeps its session row with its exit code, but doesn't change `play_stats`.
- Opening the library closes sessions a crashed launcher left open, at their start time. Each counts as a play with no play time, because how long the game ran isn't known.

### Grid queries

Each selects only what a cell draws: game id, effective title, cover path and root, and the favourite flag.
- **A system:** `games` through `games_by_system`, LEFT JOINed on primary keys to `user.game_overrides`, `user.favourites` and `media` (kind `cover`), hidden games left out, ordered by `COALESCE(o.sort_title, g.sort_title)`. An overridden title sorts in its own place, at the cost of a temporary B-tree sort (2.4 ms for 10,000 rows).
- **Favourites:** `user.favourites` joined to `games` through `UNIQUE (system_id, path_key)`, in title order.
- **Recently played:** `user.play_stats` through `play_stats_recent`, newest first, with a limit.

### Migrations (versioned)

- Each DB has its own ordered SQL files, embedded in Core (`Data/Migrations/{Library,User}/NNNN_name.sql`). A shipped file is never edited.
- The runner follows SQLite's documented procedure:
  1. `foreign_keys=OFF` before `BEGIN`.
  2. Apply every migration newer than `user_version`.
  3. `foreign_key_check`.
  4. Bump `user_version` and commit.
- `userdata.db` is copied with `VACUUM INTO` first (`userdata.db.v<from>-<utc time>.bak`, next to it), and the last 3 backups are kept.
- If a DB is newer than the app, or a migration fails:
  - `library.db` is rebuilt.
  - `userdata.db` is refused with a clear error.

## A5. Config files (TOML)

Our own keys use UK spelling (`colour`, `favourite`).

### `settings.toml`

```toml
format = 1

[paths]
rom_root = "D:/ROMs"                 # default "{home}/ROMs"

[scanning]
# Applied to every system, before its own `exclude`. Default: ES-DE's media folders and gamelists.
# Setting a list replaces the default; [] turns it off.
exclude = ["images", "manuals", "videos", "gamelist.xml"]

[variables]                          # expanded at config load; may use {home} and each other (cycles are errors)
retroarch = "C:/Emulators/RetroArch" # built-in defaults: retroarch = "C:/RetroArch-Win64", emulators = "C:/Emulators"

[display]
theme = "memory-card"
fullscreen = true
hide_empty_systems = true            # the systems grid leaves out systems with no games (default); false shows every enabled system
systems_layout = "grid"              # 2026-10-02: "grid" (default), "carousel" (one row, the focused one in the middle) or "single" (one at a time)
systems_columns = 0                  # the grid's columns, 1-9; 0 (default) automatic: as many as fit
systems_rows = 0                     # the grid's rows that fit between the heading and the details, 1-6; 0 (default) automatic
games_layout = "grid"                # "grid" (default), "carousel" or "list" (the titles, the focused game's model beside them)
games_columns = 0                    # as above; a system's own games_layout, games_columns and games_rows (systems.toml) win
games_rows = 0

[ui]                                 # the status indicators, top right (2026-10-02); each defaults to true
show_clock = true                    # the time, in the user's regional short-time format
show_battery = true                  # the battery's charge; nothing shows on a device without one
show_network = true                  # Wi-Fi with its signal, a cable, or disconnected

[scraping]
provider = "screenscraper"           # asked first for every game
fallback = ["igdb", "steamgriddb"]   # then these, in order, for what's still missing; "steam" (the Steam store) is opt-in
regions = ["eu", "wor", "us", "jp"]  # ScreenScraper region codes; first available wins (IGDB's release regions map from them)
languages = ["en"]
media = ["cover", "back", "spine", "screenshot", "logo"]   # the default; also hero (fan art), label (support texture), video
hash_limit_mb = 64                   # ROMs up to this size are hashed for ScreenScraper; 0 = none
```

### System definition

Built-in definitions ship in `Launcher.Core/Defaults/systems.toml`: first the original fourteen (Game Boy, Game Boy Color, Game Boy Advance, NES, SNES, N64, GameCube, Master System, Mega Drive, Saturn, Dreamcast, PlayStation, PlayStation 2 and PSP), then 150 more converted from ES-DE (see [The ES-DE catalogue](#the-es-de-catalogue)), and Windows and Steam (see [Windows and Steam games](#windows-and-steam-games)). The user's `ConfigDir/systems.toml` holds only what changes.

```toml
# built-in
[systems.megadrive]
name = "Mega Drive"
manufacturer = "Sega"
year = 1988
aliases = ["genesis", "md"]
extensions = [".md", ".gen", ".smd", ".bin", ".zip", ".7z"]   # matched ignoring case
emulator = "retroarch-genesis-plus-gx"
alt_emulators = []
game_model = "clamshell"             # M6: user only; a game template id in the theme (else the built-in theme). Unset by default: the theme decides
# games_layout = "list"              # 2026-10-02: user only; how its games are shown. Unset: [display] games_layout
# games_columns = 4                  # 2026-10-02: user only; its games grid's columns and rows (0 automatic). Unset: [display]'s
# games_rows = 3
screenscraper_id = 1
igdb_platforms = [29]                # IGDB platform ids; NES and SNES add their Japanese twins (99, 58)
# steam_store = true                 # only on windows and steam: looked up on the Steam store

# user override
[systems.megadrive]
rom_dirs = ["E:/Sega/Mega Drive", "{rom_root}/genesis"]   # default: the first of {rom_root}/megadrive, /genesis, /md that exists
recursive = true                     # default
exclude = ["bios", "**/Unused/*"]    # added to [scanning] exclude; globs against paths relative to a ROM folder; no '/' = any file or folder name
emulator = "retroarch-mesen"

[systems.mastersystem]
enabled = false
```

- `screenscraper_id` values were checked on 2026-09-28 against ScreenScraper's own system pages (`systemeinfos.php?plateforme=<id>`) and ES-DE's table. ScreenScraper's API documentation has no system table, and `systemesListe.php` needs developer credentials, which the repo doesn't have: `odyssey-scrape ss-systems` (M4) lists it against each system's id, for the owner to run.
- `igdb_platforms` (M4) were cross-checked between RomM's IGDB platform table and an IGDB platform list. A system without them isn't looked up on IGDB.
- `games_layout`, `games_columns` and `games_rows` (2026-10-02; unset by default) give a system's games their own layout (`"grid"`, `"carousel"` or `"list"`) and grid size (used when its layout is a grid). A bad value (an unknown layout, not an integer, or outside 0–9 and 0–6) is a warning and `[display]`'s is used: a matter of taste mustn't disable the system, as an error would.
- `steam_store` (default false; true on `windows` and `steam`) lets the Steam store provider look the system's games up by title. It's off elsewhere so a console game can't match its PC re-release.
- Every config file may start with `format = 1`.

### Emulator profiles

Built-in profiles ship in `Defaults/emulators.toml`, using variables like `{retroarch}`. The user's `ConfigDir/emulators.toml` layers over them.

```toml
[emulators.retroarch-genesis-plus-gx]
name = "RetroArch: Genesis Plus GX"
executable = "{retroarch}/retroarch.exe"
core = "{retroarch}/cores/genesis_plus_gx_libretro.dll"   # a path, like executable; {core} expands to it
args = ["-L", "{core}", "--fullscreen", "{rom}"]

[emulators.blastem]
name = "BlastEm"
executable = "C:/Emulators/BlastEm/blastem.exe"
args = ["-f", "--rom={rom}"]         # placeholders can sit anywhere inside an entry
working_dir = "{emulator_dir}"       # default

[emulators.run-file]                 # a game that is its own program, script or shortcut
name = "Run the game's own file (shortcut, script or program)"
run_file = true                      # no executable, core or args; working_dir defaults to "{rom_dir}"
```

- A game launches with, in order: an emulator chosen for that launch, the game's own override (`game_overrides.emulator` in `userdata.db`), or the system's `emulator`. Any configured profile can be chosen, not only the system's `alt_emulators`. An override naming a profile that's gone is a launch error that says where it was named.
- The built-in RetroArch core file names and `pcsx2-qt.exe` were checked against a RetroBat install (2026-09-28). The flags follow each emulator's documentation; a launch with each real emulator is still to do (M3 log).

### The ES-DE catalogue

`Defaults/systems.toml` and `Defaults/emulators.toml` carry every system of ES-DE 3.5.0's Windows `es_systems.xml` (ids, names, extensions, commands) and every emulator of its `es_find_rules.xml`, converted by a script (kept out of the repo; the files are the source of truth from here on). Rules of the conversion:

- **Ids are ES-DE's**, so existing ES-DE folders work. Regional twins and duplicates are aliases of one system, whose folder names are default ROM folders too: `genesis`, `megadrivejp` (Mega Drive), `sfc`, `snesna` (SNES), `famicom` (NES), `mark3` (Master System), `megacd`, `megacdjp` (`segacd`), `sega32xjp`, `sega32xna` (`sega32x`), `saturnjp`, `neogeocdjp`, `tg16` (`pcengine`), `tg-cd` (`pcenginecd`), `videopac` (`odyssey2`), `fba` (`fbneo`), `mame-advmame` (`mame`), `amiga600`, `amiga1200` (`amiga`), `laserdisc` (`daphne`). Their commands are merged in. Left out: `desktop`, `emulators`, `kodi`, `epic` (not systems), `windows` and `steam` (added by hand since: below), the placeholder-only `androidapps`, `androidgames`, `lutris`, `xboxone`, and `psvita` (Vita3K needs a title id ES-DE reads from a file).
- **The first ES-DE command is the default emulator and the others are alternatives**, except that a system whose first command is a shortcut or script (`run-file`) and which has other kinds of files gets its first real emulator as the default (`ports` keeps `run-file`). The original fourteen keep their defaults and gain the others as alternatives.
- **Emulators sit under `{emulators}` with ES-DE's folder names** (`{emulators}/Mesen/Mesen.exe`, from the first static path of its find rule); RetroArch cores under `{retroarch}/cores`. Profile ids: `retroarch-<core>` (`mednafen_*` is `beetle-*`), `<emulator>` when it has one set of arguments or a general one for six or more systems, else `<emulator>-<system>` or `<emulator>-<what its label adds>`. The existing `dolphin`, `pcsx2` and `ppsspp` are reused for those emulators (their flags are the project's), and RetroArch profiles pass `--fullscreen` like the others.
- **Tokens:** `%ROM%`, `%ROMRAW%` `{rom}`; `%GAMEDIR%` `{rom_dir}`; `%BASENAME%` `{rom_stem}`; `%FILENAME%` `{rom_file}`; `%ROMPATH%` `{rom_root}`; `%EMUDIR%` `{emulator_dir}`; `%STARTDIR%=` `working_dir`; `%HIDEWINDOW%`, `%ESCAPESPECIALS%` and `%RUNINBACKGROUND%` dropped; `%EMULATOR_OS-SHELL% /C` becomes the `run-file` profile. `%INJECT%` (extra arguments ES-DE reads from a file beside the ROM) isn't supported: it's dropped where the command works without it, and the command is left out where it supplies required arguments (PS3 and PS4 game serials, Vita3K, 3dSen, Linux Loader, an EKA2L1 custom device). `pcsx2x6` assumes `pcsx2-qt.exe` (ES-DE matches `pcsx2x6*.exe`).
- **`screenscraper_id` and `igdb_platforms` of the catalogue systems were written from memory and are not verified**; systems without one aren't looked up on that provider. `odyssey-scrape ss-systems` checks the ScreenScraper ones.
- The built-in theme gives each a colour (by manufacturer) and the nearest of its boxes (A6; DOS has the big box, shaped by each game's art). A system with no ROMs has no card (`hide_empty_systems`), the Emulators page lists only the profiles that systems with games use, and install warnings cover only those systems.

### Windows and Steam games

Two built-in systems hold games that are their own programs, with ES-DE's ids so its folders work (2026-10-01):

```toml
[systems.windows]                    # {rom_root}/windows
name = "Windows"
manufacturer = "Microsoft"
extensions = [".bat", ".cmd", ".lnk", ".url"]   # no .exe: a game's own folder would show its uninstaller and tools
emulator = "run-file"
screenscraper_id = 138               # PC Windows (from memory, unverified like the catalogue's)
igdb_platforms = [6]                 # PC (Microsoft Windows)
steam_store = true                   # looked up on the Steam store, by title

[systems.steam]                      # {rom_root}/steam: the .url files Steam makes (Manage, Add desktop shortcut)
name = "Steam"
manufacturer = "Valve"
extensions = [".bat", ".cmd", ".lnk", ".url"]
emulator = "run-file"
screenscraper_id = 138
igdb_platforms = [6]
steam_store = true
```

- Shortcuts, batch files and internet shortcuts launch as any `run_file` game (A1 Platform). A shortcut's program is followed in the game's job, so the game has ended when it and everything it started have.
- **A Steam game's shortcut** (in either system: it's the file that counts, not the system) is handed to Steam and followed through the Steam client's state until Steam says the game has ended (A1 Launching). The game's processes aren't the launcher's: Steam starts them, after updating the game or syncing its saves if it must.
- A non-Steam game added to Steam has a 64-bit game id in its shortcut, which Steam doesn't report on, so it isn't followed (it counts as ended at once, like any shortcut handed to a program already running). Other stores' URLs (Epic's `com.epicgames.launcher://`) aren't followed either.
- Titles come from the file names (`Half-Life 2.url` is "Half-Life 2"), and scraping searches by title. The app id isn't used for scraping: the Steam store provider (`"steam"`, opt-in) also finds the game by its title, so a shortcut to anything (a `.lnk`, a game bought elsewhere) can get Steam's official art. `provider = "steam"` with `fallback = ["screenscraper", "igdb", "steamgriddb"]` asks it first for Windows and Steam games; every other system then starts with ScreenScraper.

### Launch placeholders (expanded at launch time)

| Placeholder | Expands to |
|---|---|
| `{rom}` | Absolute ROM path, with native separators. |
| `{rom_dir}` | The folder containing the ROM. |
| `{rom_file}` | The ROM's file name. |
| `{rom_stem}` | The ROM's file name without its extension. |
| `{system}` | The system id. |
| `{emulator}` | The expanded `executable`. |
| `{emulator_dir}` | The folder of the expanded `executable`. |
| `{core}` | The profile's expanded `core`. Using it in a profile without one is a validation error. |
| `{home}`, `{rom_root}`, `{<variable>}` | Resolved already at config load. |

Write `{{` or `}}` for a literal brace.

### Expansion rules

- Each `args` entry becomes exactly one argument. There's no shell, and users never quote anything.
- **Quoting is the runner's job.** Windows passes a process one UTF-16 command line, so `WindowsCommandLine` quotes each argument by the Microsoft C runtime's rules (the ones `CommandLineToArgvW` and emulators' `main` use): an argument with a space, tab, newline or `"`, or an empty one, is wrapped in quotes; backslashes before a `"` are doubled and the quote escaped. Spaces, `&`, `%`, `^`, braces and any non-ASCII text arrive intact, because there's no cmd.exe and the command line is UTF-16 end to end (`CreateProcessW`). The Linux stub uses `ProcessStartInfo.ArgumentList`.
- Expansion is single-pass, so a ROM named `{x}.zip` stays literal.
- An unknown placeholder is a validation error, and an argument with a NUL character is a launch error.
- **`.bat` and `.cmd` executables are rejected.** cmd.exe re-parses their arguments, so a name like "Sonic & Knuckles" would break or inject commands.

### Paths in config

- Use forward slashes or TOML literal strings (`'C:\Emulators'`).
- Relative paths resolve against ConfigDir, or against the theme folder in `theme.toml`.
- Extension matching ignores case.

### Merge and validation

- Tables merge recursively; scalars and arrays are replaced whole.
- `enabled = false` switches off a built-in entry.
- A new id must be complete, and any missing required keys are listed. Required: `name`, `extensions` and `emulator` for a system; `name` and `executable` for an emulator.
- Ids use lower-case letters, digits, `_` and `-`.
- A TOML syntax error means the whole file is ignored, and its first diagnostic is shown.
- A semantic error disables only the offending entry: a system or emulator is left out, with an info diagnostic saying so, and a bad setting falls back to its default. A system whose `emulator` is unknown, disabled or has errors is disabled; an unknown `alt_emulators` entry is only a warning.
- Unknown keys are warnings, with "did you mean" for a key within two edits.
- **Installs are checked (M3, changed 2026-10-01).** For every emulator an enabled system uses as its `emulator`, a missing `executable`, or else a missing `core`, is a **warning** that names the systems affected: `emulators.retroarch-genesis-plus-gx.executable: the executable 'C:\RetroArch-Win64\retroarch.exe' doesn't exist, so Master System (mastersystem) and Mega Drive (megadrive) can't launch games (it's their emulator)...`. The systems stay enabled, so an unplugged drive doesn't empty the library, and launching reports the same problem. Alternatives (`alt_emulators`) aren't reported (the catalogue lists many the user doesn't have; the Emulators page shows each program's state, and launching names a missing one), nor are `run_file` profiles. Each path is checked once. `ConfigSources.FileExists = null` turns the check off (boot), and `CheckInstallsFor` limits it to some systems (the app passes the ones that have games, so a fresh install stays quiet).
- A `core` that no `args` entry uses as `{core}` is a warning.
- Every diagnostic has the file, line, column and dotted key: `user/systems.toml:3:1: error: systems.megadrive.emulator: unknown emulator 'blastemm' (did you mean 'blastem'?)`. Values from the defaults point at `built-in/<file>`.

### Writing config (M7)

The settings screen saves each change as it's made, through `ConfigWriter` and `TomlEditor`:
- **Only what changed, in the user's own files.** An edit that matches what the file says writes nothing. A key the file doesn't have is added only if its value differs from the built-in default. A key set back to its default is removed, unless its line has a comment (then it's updated, and the comment kept). "Use the default" removes the key.
- **The user's text stays as written.** Comments, blank lines, key order, quoting, line endings and a byte order mark are kept. A changed value keeps the comment after it on its line, but a multi-line array is written again on one line, so comments inside it go. A new key goes at the end of its table, before the blank lines and the comments above the next table; a new table goes at the end of the file; keys written as dotted keys stay dotted. An inline table can be changed but not added to or removed from. A file with a syntax error isn't touched: the settings screen says so, with the line.
- **Validated before writing.** The edited files are loaded as the app would load them, and an edit that brings an error the files didn't have (an unknown emulator, a bad placeholder, a wrong type) is refused with the loader's message; nothing is written. `ConfigInput` checks what the loader can't: the folder exists, the program is an `.exe` (not `.bat` or `.cmd`), a credential is one line.
- **Paths** are written with `/` (`//server/share` for a share) and with braces doubled, so a folder named `{x}` isn't read as a placeholder.
- **Atomic:** each file is written to `<file>.saving`, then moved over the original.

### Secrets

ScreenScraper account and developer credentials, the SteamGridDB API key and the IGDB (Twitch application) client id and secret live only in `ConfigDir/secrets.toml` or in `ODYSSEY_*` environment variables, which override the file value by value (M4, `ProviderAccounts`). A release carries ScreenScraper's developer credentials itself (below), and uses only those, so users only enter their own account:

```toml
[screenscraper]      # ODYSSEY_SCREENSCRAPER_DEV_ID, _DEV_PASSWORD, _USERNAME, _PASSWORD
dev_id = "..."       # developer credentials, issued by ScreenScraper (on its forum) for this software; built into a release
dev_password = "..."
username = "..."     # the user's account; optional (anonymous limits otherwise)
password = "..."

[steamgriddb]        # ODYSSEY_STEAMGRIDDB_API_KEY
api_key = "..."

[igdb]               # ODYSSEY_IGDB_CLIENT_ID, ODYSSEY_IGDB_CLIENT_SECRET
client_id = "..."
client_secret = "..."
```

- **Built in (2026-10-02).** The release workflow writes `src/Launcher.Core/Scraping/BuiltInAccounts.Release.g.cs` from the repository's `SCREENSCRAPER_DEV_ID` and `SCREENSCRAPER_DEV_PASSWORD` secrets (`tools/write-built-in-accounts.ps1`; a tag fails without them) before it builds. The file is gitignored, and implements a partial method of `BuiltInAccounts`, so a build from source has no built-in credentials and asks for them as before. Each value is XORed with a random key made for each build, so it isn't plain text in the DLL: that hides it from a casual search, not from someone determined (every request carries it), and ScreenScraper can revoke it.
- `ProviderAccounts.BuiltIn` is used only when the caller passes it (the app and `odyssey-scrape` do; tests never see a release's), and then it wins: a `dev_id` or `dev_password` in `secrets.toml` or the environment is ignored, with an Info diagnostic (not a problem in the settings screen). Its values are in `ProviderAccounts.Values`, so `Redactor` masks them too. The settings screen doesn't list developer credentials in a release, only the user's account; a build from source lists them, after the account. `BuiltInAccountsTests` checks, in the release workflow, that the generated file was compiled in.
- A provider without its credentials is skipped, and the message says which keys or variables to set and where. Diagnostics about the file never quote a value, and a syntax error shows only its position.
- ScreenScraper embeds the credentials in every URL, and echoes them back in each response (`header.commandRequested`, every media URL). `Redactor` masks them in saved responses and logs; a test scans every file the scrape writes, and the log, for every credential.
- IGDB's app access token (about 60 days, and a Twitch application may only have 25) is cached in `DataDir/tokens/igdb.json`, keyed by a hash of the client id, and replaced a day before expiry or when IGDB refuses it. The client secret travels in a form body, never a URL.
- The settings screen (M7) writes credentials to `secrets.toml` and nowhere else, and never shows one: each is masked, with where it's set (the file, or an `ODYSSEY_*` variable, which wins); the on-screen keyboard starts empty and types hidden. "Test connection" builds a scrape service of its own from `secrets.toml` as saved, so a refusal doesn't rest the provider for real scrapes.

## A6. Theme manifest (`themes/<id>/theme.toml`)

A theme is a folder with a `theme.toml` and the models it names. The guide for theme authors (Blender, testing) is [THEMING.md](THEMING.md); the sample theme is [`samples/themes/retro-tv/`](../samples/themes/retro-tv/theme.toml). Paths are relative to the folder, `/`-separated, and can't leave it. The built-in theme is [`godot/themes/memory-card/theme.toml`](../godot/themes/memory-card/theme.toml); the M6 test theme is [`tests/themes/slot-showcase/theme.toml`](../tests/themes/slot-showcase/theme.toml).

```toml
format = 1
name = "Memory Card"
author = "Odyssey Launcher"
look_transition_ms = 300             # how long a cross-fade between looks takes; default 300, 0 to 5000

[look.background]                    # icon.sys-style: one sRGB colour per screen corner
top_left     = "#1B1F4A"
top_right    = "#1B1F4A"
bottom_left  = "#04040C"
bottom_right = "#0B0B24"

[look.ambient]
colour = "#303038"
energy = 1.0                         # default 1

[[look.lights]]                      # 1-3 directional lights, as in icon.sys
direction = [-0.5, -0.4, -0.75]      # direction the light travels, in view space: +X right, +Y up, +Z towards the viewer
colour = "#FFFFFF"                   # default white
energy = 1.0                         # default 1

[defaults]
system_model = "models/systems/generic.glb"   # the card for systems without their own model
tint_system_model = true                      # its plain materials take each system's colour
game_template = "dvd_case"                    # for systems the theme doesn't assign one

[templates.dvd_case]                 # a game template: a model, and optional slot chains
model = "models/templates/dvd_case.glb"
shape = "model"                      # optional: "model" (its own, the default) or "media" (each game's art: A7)

[templates.dvd_case.slots]           # optional: a slot the table doesn't list is [<its kind>, "generated"]
back = ["back", "screenshot", "generated"]

[templates.dvd_case.fit]             # optional, per slot: "crop" (fill the face, the default) or "whole" (fitted inside it)
back = "crop"

[systems.saturn]
model = "models/systems/saturn.glb"  # optional: the system's card (default: [defaults] system_model)
tint = false                         # optional: default false for its own model, else tint_system_model
colour = "#4A4F5C"                   # optional: its card's tint and its plain boxes' colour
game_template = "jewel_case"         # optional: a template id in this theme (default: [defaults] game_template)

[systems.saturn.look.background]     # optional: the look while its games are shown
top_left = "#2A1A3A"
top_right = "#2A1A3A"
bottom_left = "#050008"
bottom_right = "#100818"
```

- **Colours:** `#RRGGBB` sRGB. `energy` is a linear multiplier, 0 to 16.
- **Background:**
  - The four corners interpolate in sRGB, as on the PS2.
  - The gradient is drawn on a background canvas layer rather than a sky, which avoids radiance-map and cubemap-pass problems and makes cross-fades free.
  - With the Linear tonemapper, glow off and ambient source Colour, each corner pixel renders as its exact hex value **on Forward+**. On the Mobile renderer (the one we use, M1) the canvas background is composited through the 3D buffer, whose precision moves dark corners by up to 2/255 (M6 measured `#04040C` as `#06060D`); Forward+ gives the hex values exactly ([perf/m6-themes.md](perf/m6-themes.md#corner-colours)).
  - Reflections are disabled.
- **Lights:**
  - Directions are in **view space**, as in icon.sys, so the three `DirectionalLight3D`s are children of the camera.
  - Any non-zero direction is valid, including straight up and down.
  - Lights the theme doesn't define are switched off.
- **Per-system looks:**
  - Entering a system cross-fades to its look over `look_transition_ms`, and leaving cross-fades back; the systems grid, Favourites and Recently played use the theme's own look. Mid-fade, the lights' directions, colours and energies blend, and a light only one side has fades from or to energy 0.
  - A per-system `background`, `ambient` or `lights` block **replaces** the theme's block whole. A background needs all four corners.
  - Anything left unspecified falls back to the theme's look; a theme's own blocks fall back to the built-in theme's.
  - The built-in theme gives each of the original 14 built-in systems a colour, a template and its own background and lights (generated from its colour), and each of the 150 ES-DE catalogue systems, and Windows and Steam, a colour (by manufacturer) and the nearest of the boxes (DOS the `generic_box_spine`, and Windows and Steam the `generic_box_logo`, from 2026-10-02) or, for the arcade systems, the `arcade_cabinet` (from 2026-10-02), with the theme's look.
- **Templates** (`[templates.<id>]`): a game template is a `.glb` (any slots, or none: M6 part 2 dropped the `cover` requirement, so a template can be a television showing the screenshot) and optional slot chains (A7 Media slots). From 2026-10-01 `shape = "media"` makes each game's box take its proportions from its cover and its depth from its spine (A7 Boxes shaped by the art); a bad value is an error and the template keeps its own shape, and a model with no `cover` material keeps its own with a warning. From 2026-10-02 `[templates.<id>.fit]` sets a slot to `"whole"`: its art is fitted inside the face at its own proportions over the slot's fallback, never cropped (A7 Art drawn whole); a bad value or slot is an error and the slot stays cropped, and a slot the model lacks a warning. Themes name their templates and assign them to systems; the resolution order is in A7.
- **Validation:** like config (A5), a syntax error or an unsupported `format` rejects the theme (the built-in one is used), and every other problem is a diagnostic naming the file, line, column and key: `user/themes/neon/theme.toml:12:1: error: templates.box.model: 'box.glb' doesn't exist in the theme's folder`. A bad look block falls back to the built-in theme's; a template whose model is missing or isn't a `.glb` inside the folder is left out, and whatever named it falls through to the next model in line; a bad slot chain falls back to the slot's default chain; unknown keys are warnings with "did you mean". A user theme's models are inspected (their material names, from the GLB's JSON chunk) when the manifest loads; a built-in theme's are checked by Core's tests against the repo's files instead, and at load time.
- **Locations:** built-in themes live in `res://themes/` (the export includes each `theme.toml`, and each `.glb` as the file itself: Godot's "keep file" import. Godot's default for a new `.glb` is a scene, which the export packs instead of the file, so the theme loses that template; `BoxTemplateGenerator` writes the keep import for the models it makes, and `BuiltInModelTests` fails on any `.glb` in the project without one), and user themes in `ConfigDir/themes/<id>/`. A user theme with the same id replaces the built-in one, but the built-in `memory-card` stays the last resort for anything the active theme doesn't provide. `[display] theme` in settings.toml picks the theme; `--theme=<id>` overrides it for a run.
- **Switching:** the settings screen (M7: Menu, then Theme) lists the themes by name, applies the one chosen without a restart, and writes `[display] theme`. T on the keyboard (systems screen) loads the next theme in id order for the session only (M6), as the nav script's `theme` step does.
- **Later:** a `[ui]` section is reserved for fonts, sounds and UI colours.

## A7. glTF model spec

| Rule | Value |
|---|---|
| Format | glTF 2.0 binary `.glb`, one scene, everything embedded. Images are PNG or JPEG. |
| Units and axes | glTF defaults, with no conversion: metres, right-handed, +Y up, the front facing +Z (towards the viewer). |
| Origin | The bottom-centre of the rest-pose bounding box. The model stands on y=0, and spin is about +Y through the origin. |
| Size | The bounding box fits x∈[-0.5,0.5], y∈[0,1], z∈[-0.5,0.5], with the largest side about 1 m. <br>The loader fits the rest-pose bounding box to the grid cell by scaling a **wrapper node**, so animation clips are never touched. <br>Anything off by more than 10× gets a "wrong units?" warning. |
| Media slots | A material whose name is a media kind (`cover`, `back`, `spine`, `box_texture`, `label`, `screenshot`, `logo`, `hero`) is a slot, and shows that game's media through its fallback chain (below). <br>Every slot is optional, `cover` included (M6 part 2). <br>Matching ignores case and a trailing Blender `.NNN` suffix. <br>TEXCOORD_0 spans 0..1 across the face, upright, and sampling is clamped. <br>Art is centre-cropped to fill. The face's aspect ratio comes from the material's `extras.aspect`, or else from the slot mesh's bounds. <br>The material's own base colour texture is the chain's last fallback. <br>Set the base colour factor to white. |
| Materials | Remapped onto the launcher's one item shader, so a model never adds a shader variant. <br>Honoured (M6): base colour factor and texture (at most 4 textures a model, mipmapped when loaded), roughness, and vertex colours (multiplied into the base colour). <br>Planned, ignored until then: metallic, normal, emissive, `KHR_materials_unlit`, `KHR_texture_transform`, alpha and double-sided. <br>A model that requires an extension outside `KHR_materials_unlit`, `KHR_texture_transform`, `KHR_materials_emissive_strength`, `KHR_mesh_quantization` and `KHR_lights_punctual` (Draco, for one) is rejected. |
| Animations (optional; names match like slots) | `idle` loops while not focused. <br>`focused` loops while focused. <br>`launch` plays once; the emulator starts when it ends or after 2 s, whichever comes first. <br>Node TRS, skinning (≤64 joints, 4 or 8 influences per vertex) and morph targets (≤8) are supported. Other clips are ignored. <br>Matching also ignores an object name before a `|` (Blender's `Armature|idle`); the loader renames each to its canonical name. <br>Drawing (M6 part 2): a model with an `idle` clip is drawn as a node in every cell (so keep idle clips for system models); one with only `focused` or `launch` clips stays batched, and the focused cell swaps to a node while it plays them, blending (0.25 s) to a `_rest` clip made from their tracks before it swaps back. |
| Procedural fallbacks | The grid's focus lift and scale always apply. <br>Spin or bob runs only for a state without a clip. <br>The launch fallback spins up and moves towards the camera. |
| Ignored | Cameras, `KHR_lights_punctual` and extra scenes. Theme lights are the only lights. |
| Runtime handling | A user's `.glb` (per-game, `ConfigDir/models/`, a user theme's) is first processed by Core (`ModelInspector`, `ModelProcessor`: checked, textures over the budget's side scaled down, rejected if broken or more than 2× over) and cached in `CacheDir/models/`, keyed by path, size, time, kind and processing version; a rejection is cached and logged too (`DataDir/logs/models.log`). Then every `.glb`, the built-in theme's included, is parsed by `GltfDocument` on a worker and converted there, textures and meshes created there too; the main thread adopts the result within 2 ms a frame. Every model is fitted to the spec (standing on y = 0, centred, largest side 1 m). A per-game model shows its system's template until it has loaded, is fitted into the cell, and is drawn on the cell's own node. Users import per-game models with `ModelImportService` (a `.glb`, or an OBJ model converted by `ObjConverter`). |

### Budgets

M6 part 2 enforces them (`ModelBudget`); the per-game one was measured with 300 per-game models in a 3,000-game library ([perf/m6-models.md](perf/m6-models.md)).

| Model | Triangles | Textures (excluding media slots) | Materials |
|---|---|---|---|
| Game template (built-in or per system) | ≤ 2,000 | ≤ 2 × 1024² | ≤ 4 |
| Per-game custom model | ≤ 5,000 | ≤ 2 × 1024² | ≤ 4 |
| System model | ≤ 30,000 | ≤ 4 × 2048² | ≤ 8 |

Textures are the base colour images the materials use. Normal, metallic-roughness, occlusion and emissive maps aren't drawn yet, so they don't count (their references are still checked); they will once they're honoured.

`ModelInspector` checks each model first:
- Over budget: the model loads, with a warning.
- More than 2× any count (triangles, textures, materials; 64 joints a skin and 8 morph targets a mesh are budgets too): the model is rejected, and the next model in the resolution order is used.
- A texture over the budget's side is scaled down when the model is processed, so its size never rejects a model.
- A broken file (a bad range or index, a node loop, a non-PNG/JPEG image, data outside the file) is rejected with its reason, before Godot parses it.
- Every warning and rejection goes to `DataDir/logs/models.log`, with what's used instead; `odyssey-scrape models-log` prints it, and `inspect-model` checks a file.

### Media slots and fallback chains (M6)

Each slot of a game template has a **fallback chain**, walked for every game when its cell binds:
- A media kind: the game's media of that kind, if it has one. Any image kind can fill any slot (a back slot can show a screenshot).
- `generated`: a face the launcher draws (below), for `cover`, `back`, `spine` and `label` only.
- `authored`: the material's own texture, as the model was made (or its base colour).

The first media kind the game has wins; `generated` or `authored` ends the walk; and every chain ends, implicitly, with `authored`. While the media loads, the chain's next `generated` or `authored` entry shows, and the media fades in over it. If the media has no usable derivative, the walk carries on from the next entry. A slot the theme doesn't list is `[<its kind>, "generated"]` where the launcher can draw it, else `[<its kind>]`. System cards have no media: their slots are `generated` where possible, else `authored`.

```toml
[templates.showcase_case.slots]      # the test theme's template
cover = ["cover", "generated"]
spine = ["spine", "logo", "generated"]
screenshot = ["screenshot", "hero", "authored"]   # "authored": the model's own test card
```

When a game's media changes (a rescan finds new or removed art or models, a scrape saves media, a game is cleared, or derivatives are baked), the library raises `MediaChanged`, and the shown list's media is read again: each changed game's cell walks its chains again, keeping its model and every slot whose media is unchanged.

### Resolution order (first hit wins)

User files are matched by `path_key`, with or without the ROM's extension, and found by folder convention: per-game models are indexed by the scanner (media kind `model`), and the two per-system folders are listed when the theme loads, so nothing is probed per item. A candidate that fails to load or is rejected by its budget is skipped for the next one.

- **Game** (M6):
  1. `DataDir/media/<system>/model/<rel path>.glb` (the media folder, A4)
  2. `ConfigDir/models/templates/<system>.glb`
  3. the user's `game_model` in systems.toml: that template id in the active theme, else in the built-in theme (a warning if neither has it)
  4. the active theme's `[systems.<system>] game_template`
  5. the active theme's `[defaults] game_template`
  6. the built-in theme's `[systems.<system>] game_template`
  7. the built-in theme's `[defaults] game_template` (`dvd_case`)
- **System card:**
  1. `ConfigDir/models/systems/<system>.glb`
  2. the active theme's `[systems.<system>] model`
  3. the active theme's `[defaults] system_model`
  4. the built-in theme's (`models/systems/generic.glb`)

From M7 part 2 the user sets levels 1 to 3 in the app: a game's own model in its options, and a system's own card, own template or `game_model` in the system's options. The game's model swaps in place (its media changed); a system's changes reload the theme in the background.

User models (levels 1 and 2) use the default slot chains. The built-in theme's templates (M5) are `dvd_case` (PlayStation 2, GameCube), `jewel_case` (PlayStation, Saturn, Dreamcast), `cartridge_box` (NES, SNES, N64, Game Boy Advance), `gameboy_box` (Game Boy, Game Boy Color, Super Game Boy: from 2026-10-01), `generic_box_spine` (DOS) and `generic_box_logo` (Windows, Steam: the game's logo along the spine), two templates of one PC big box, `generic_box.glb` (shaped by each game's art: below; 190 × 240 × 50 mm without art; from 2026-10-02, renamed from `big_box`), `clamshell` (Mega Drive, Master System), `umd_case` (PSP) and `arcade_cabinet` (from 2026-10-02: Arcade, MAME, FinalBurn Neo, the CPS boards, Neo Geo, NAOMI, Atomiswave, Model 2 and 3, ST-V, Triforce, Daphne, and the console and PC arcade systems; below), plus the generic system model, a memory-card-shaped slab with a `label` slot, in [`godot/themes/memory-card/models/`](../godot/themes/memory-card/models/). `BoxTemplateGenerator` builds them from real case sizes in millimetres: a rounded-rectangle front outline extruded to the depth, with bevelled edges, one surface per material (the front slot, `back`, `spine`, `case`; the generic box's front and back chamfers are part of the `cover` and `back` slots, showing the art's edge, and its case is dark, so no light band frames its art), and `extras.aspect` on each slot (the spine's is its straight wall: the depth less the chamfers, over the height less the corners). It exports them with Godot's glTF exporter; the output is deterministic, and `BuiltInModelTests` checks each file against this spec. About 220 triangles each.

**The arcade cabinet (2026-10-02).** `ArcadeCabinetBuilder` builds the top half of an upright cabinet, cut off below the control panel, from a real one's proportions in millimetres: side panels (blue outside, with a grey T-moulding along their front edges so the black cabinet's outline reads on a dark background), a marquee box whose front panel is the `label` slot (2.7:1, taller than most real marquees, since logos are drawn whole and most are nearer 2:1), the monitor tilted back 12° in a framed bezel as the `screenshot` slot (568 × 426 mm, 4:3, nearly filling the bezel, with `extras.aspect` set, as the face is tilted; matte, roughness 0.9, as glossy glass mirrored the lights over the focused cabinet's screen), and a control panel with two players' joysticks and six buttons each. The side panels' lower part is inside the control panel, 10 mm or more under its top and behind its front: where they shared its front plane and stood a few millimetres proud of its top, their grey edges flickered as the model moved. The theme gives it `label = ["logo", "generated"]`: the logo drawn whole over a deep shade (below), else a printed title; and `fit` `screenshot = "whole"`, so a vertical game is pillarboxed on the screen's own switched-off texture, which also shows for a game with no screenshot (the default chain). It's 1,402 triangles and three materials: the two slots, and `case`, whose many colours come from a 64² palette texture with each part's UVs in the middle of its colour's 16-pixel swatch (one colour at any distance, as the UVs don't vary across a triangle; vertex colours would do it too, but their colour space through Godot's glTF round trip is one more thing to get wrong). No clips, so it stays batched.

**Generated faces (M5; `generated` in a chain from M6).** With front art only, the item shader makes the rest. The spine is the cover's dominant colour, with the title reading top to bottom and a darker band where a logo would be.

**Art drawn whole (2026-10-02).** When a slot's chain resolves to the `logo` kind, or its template's `fit` sets it to `"whole"`, the grid sets a bit in the slot's state (and another for a logo), and the shader draws the art whole over the slot's fallback using its alpha. Art the template fits whole fills the face's width or height at its own proportions (a tall screenshot pillarboxed), with no margin. A logo is drawn within a margin, over that fallback: the cover's dominant colour (the game's plain colour when the template shows no cover) darkened to a deep shade (a `generated` fallback), or the authored texture. On a `spine` it's turned to read top to bottom like the generated title (at most 90% of the length and 76% of the depth); on any other slot it's upright (88% of the width, 84% of the height), as on the arcade cabinet's marquee and the sample TV's plate. Before the arcade cabinet only a spine did this, and other slots cropped a logo like any art, which cut it off and showed its transparent parts as whatever colour they hid. Every other kind crops to fill, as before. The back is a darker gradient of that colour, with the title and a strip of the cover. The dominant colour is chosen per vertex from the cover's 4×4 mip, as the texel most like the others, preferring saturated ones. With no art, the front is the plain colour (the system's colour, varied per game) with the title and a thin frame. Titles come from the title atlas.

### Boxes shaped by the art (2026-10-01)

A template with `shape = "media"` (A6) takes each game's shape from its art, so a game's cover, back and spine show whole whatever their proportions (DOS big boxes vary from game to game). The built-in `generic_box_spine` (DOS) and `generic_box_logo` (Windows, Steam) do it. The depth still comes from the game's `spine` image when the spine shows its logo.
- **The rule** (`Theming/BoxShape`, pure): the front is as wide over high as the game's `cover` media (that kind itself, not whatever a chain resolved to), clamped to 1:4–4:1, with the larger side filling the list's envelope. The depth is the `spine` media's width over height (clamped to 0.02–0.5) times the box's height. Scraped images are normalised (ScreenScraper's are 700 pixels high), so only ratios are read. Without a cover or a spine, the rest shape's proportions stand in.
- **The envelope:** when a list is bound, the grid walks it once on the main thread (only if a template it uses has the shape: 2.7 ms for 10,000 games in a Debug build, [perf/box-shapes.md](perf/box-shapes.md)) for the widest and tallest box, each with its larger side 1, and sizes the cells to that instead of the template's rest size. A list of tall boxes keeps tight columns. A box whose cover arrives later is scaled down into the envelope until the list is bound again.
- **Reshaping, in the item shader:** each cell's growth goes in two slot-state columns when it binds or its media changes (half the width's growth, the height's, half the depth's, the height of the top half's start; then the front and spine faces' aspects). The vertex shader moves every vertex of each half of the rest mesh out (or in) by the growth, so bevels and corners keep their size and flat faces their normals, and the `cover`, `back` and `spine` faces take the new aspects. Every other cell's columns are zero, and the shader leaves those vertices alone. The box stays in its template's MultiMesh: no mesh per game, no node, nothing allocated. The template mesh's custom bounds cover the largest box (sides of 1, half as deep), for culling.
- **Limits:** the model must keep vertices off the centre planes (x = 0, z = 0, half the height), which the generated boxes do; sides never shrink below 0.1 (depth 0.01) of the cell. A model with clips (a node tree) or a per-game model keeps its own shape.


## Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-09-27 | Stack: Godot 4 .NET (C#), Tomlyn, Microsoft.Data.Sqlite (WAL, versioned migrations), glTF `.glb` only, platform code behind interfaces. | The owner decided it. Don't revisit without asking. |
| 2026-09-27 | TFMs follow Godot's generated csproj: net8.0 for 4.7.2. Tests use `RollForward=Major`. | The owner's rule. This machine has no .NET 8 runtime, and the editor already rolls forward to .NET 10. |
| 2026-09-27 | **Open risk:** .NET 8 support ends on 10 November 2026, and exports bundle the runtime they target (confirmed: .NET 8.0.31, self-contained). M1 benches a net10.0 build; switching needs the owner's approval. | Godot keeps a higher TFM if one is set; it only raises TFMs below net8.0. |
| 2026-09-27 | The 1 s start-up target covers **our code only**: `app_startup_ms`, from the first autoload's `_EnterTree` to `interactive`. Engine and .NET start-up is reported separately. `DebugHooks` stays the first autoload. | The owner clarified this. Engine and runtime start-up isn't ours to optimise beyond renderer and publish settings. |
| 2026-09-27 | Windows export preset: ExportRelease, separate PCK, S3TC/BPTC textures, `modify_resources` off, console wrapper for debug exports only. `tools/bench-export.ps1` starts the exe directly and reads its JSON. | This is enough for benchmarking. An embedded icon and version info can come later. |
| 2026-09-27 | `.slnx` solution, with Godot's three configurations. | .NET 10 default. Godot 4.6+ finds `.slnx` files; its builds use the csproj directly. |
| 2026-09-27 | xUnit v3 on Microsoft.Testing.Platform (`global.json` test runner). The VSTest packages are kept for IDE test explorers. | xUnit v3 4.x can't use VSTest mode under the .NET 10 SDK. |
| 2026-09-27 | `path_key` (lower-invariant NFC `rel_path`) is the identity everywhere, including `userdata.db` and media file names. | Survives case-only renames, keeps `Game.cue` and `Game.chd` apart, and makes keys portable. |
| 2026-09-27 | Per-game overrides (title, emulator, hidden) live in `userdata.db`. TOML holds system-level intent. | High-cardinality user data that can't be rebuilt. |
| 2026-09-27 | User model and art overrides are picked up by folder convention, and the scanner indexes them. | No per-item probing at runtime, and no config keys for thousands of games. |
| 2026-09-27 | Background: a canvas layer, not a sky shader. Lights are in view space. | No radiance or cubemap passes, free cross-fades, and exact colours (verified). |
| 2026-09-27 | `library.db` keeps versioned migrations, and rebuilding is only the fallback. | The owner decided on versioned migrations. The design review suggested rebuild-only. |
| 2026-09-27 | `.bat` and `.cmd` emulator targets are rejected. | cmd.exe re-parses arguments, so `&` and `%` in ROM names would break or inject commands. |
| 2026-09-27 | Forward+ with D3D12, set explicitly in `project.godot`. | What 4.7's project manager writes for new projects; the engine's fallback is Vulkan. M1 compares the two. |
| 2026-09-27 | UK English for docs, UI text, our identifiers and our config keys. External names keep their spelling. | Owner's locale and the organisation's standard. |
| 2026-09-27 | **Renderer: Mobile on D3D12**, replacing Forward+. `project.godot` switches when the real grid lands (M5). | M1: the same frame pacing, 36–42% less GPU time at 1280×800, the same or faster start-up, and output within 4/255. The design uses no Forward+-only feature. ([SPIKE_RESULTS.md](SPIKE_RESULTS.md) §3) |
| 2026-09-27 | **Item rendering:** one `MultiMesh` per template plus a `Texture2DArray` with a layer per pool cell, indexed through `INSTANCE_CUSTOM`. Per-node instances only for per-game custom models. The camera scrolls and the grid stays still. | M1: both approaches hold vsync with 64 cells. MultiMesh uses 3 draw calls against 42 and about 20% less render CPU, and its pool memory is fixed (§1). Nodes-only is the fallback. |
| 2026-09-27 | **Cover derivative: BC7 DDS, 512², full mips**, loaded with `Image.LoadDdsFromBuffer(span)` from a pooled buffer. BC1 is optional for low memory. | M1: 0.26 ms to decode against 4–5.4 ms for JPEG and PNG, 4× less VRAM, and the grid textured in 10 ms against about 100 ms. KTX, `.res` and raw were measured and rejected (§2). |
| 2026-09-27 | **Open risk (closed by M4: our own encoder, below):** the export templates have no BCn encoder (`Image.Compress` returns `Unavailable`). M4 picks an encoder: a package (needs approval), our own, or a GPU compute port. JPEG derivatives are the fallback. | Measured in the export (§2a). JPEG met every frame target at 4× the VRAM. |
| 2026-09-27 | **Uploads:** pool textures are created at boot and only updated on the main thread (4 MB per frame). No texture is created on the main thread while browsing. 2 decode workers. | M1: a BC7 layer update takes 0.03 ms. Main-thread creation has 17–66 ms outliers. Creation on a worker doesn't stall the main thread, but blocks the worker for about 12 ms per call. 4 workers didn't help (§2d). |
| 2026-09-27 | **Targets:** the hitch target is reworded as "no hitches caused by the launcher" (measured against a no-texture control, 0 frames over 2×, 0 hitches fullscreen). New targets: textured ≤ 100 ms, ≥ 99% textured while scrolling, working set ≤ 512 MB, pool ≤ 64 MB. Main-thread allocation ceiling: 4 KB per 60 s scroll. **These wait for the owner's sign-off.** | M1: a periodic present delay about every 5 s, outside our code, gives 0–2 hitches per 60 s run in windowed mode even with nothing streaming. The other targets were met with headroom. |
| 2026-09-28 | Packages: Tomlyn 2.10.1 and Microsoft.Data.Sqlite 10.0.12 (with SQLitePCLRaw's bundled `e_sqlite3`), in Launcher.Core only. Both target net8.0. | Part of the decided stack; M2 adds them. Tomlyn 2.x reads TOML 1.1 only. |
| 2026-09-28 | Config is mapped by hand from Tomlyn's syntax tree into a tree that keeps positions. No reflection mapping, no snapshot cache. | Diagnostics must name the file, line, column and key after merging, and only the syntax tree has positions. A warm load is 2 ms ([perf/m2-core.md](perf/m2-core.md)). |
| 2026-09-28 | `Diagnostic` gains a `Key` (dotted path), and prints as `file:line:column: severity: key: message`. A syntax error reports only its first parser error. | Errors must name the key. Tomlyn's recovery reports follow-on errors that aren't real. |
| 2026-09-28 | **Several ROM folders per system:** `rom_dirs` (an array) replaces `rom_dir`. `library.db` gets a `rom_dirs` table and `games.dir_id`. `path_key` stays unique per system across its folders; the earlier folder wins. | The owner asked for several folders per system. Keeping the folder out of the identity means moving ROMs between drives keeps their user data. |
| 2026-09-28 | Multi-file games: `.cue` and `.gdi` hide their tracks, as `.m3u` hides its discs. Parsed playlists are cached in a `playlists` table keyed by size and mtime. Disc systems' default extensions leave out `.bin`. | The owner's grouping rules. The cache keeps an unchanged rescan from reading 1,578 playlists (65 ms with it, against 104 ms for the scanner alone without it). |
| 2026-09-28 | File-name tags are stored in their own columns (`region`, `languages`, `revision`, `disc`, `tags`). The sort key is internal: lower-case, accent-free, leading The/A/An dropped, natural numbers, discs right after their game. `game_overrides` stores the override's sort key too. | Region and revision stay available for scraping and display. A stored key lets SQL sort the grid by plain binary comparison, with no collation or C# re-sort. |
| 2026-09-28 | Readers come from our own pool, with `userdata.db` ATTACHed once and `PRAGMA query_only`, opened read-write rather than read-only. | Microsoft.Data.Sqlite's pool would keep ATTACHes and file handles we can't control during a rebuild swap. A read-only open of a WAL DB can fail when its `-shm` file doesn't exist yet. |
| 2026-09-28 | Built-in emulator profiles use `{retroarch}` (default `C:/RetroArch-Win64`) and `{emulators}` (default `C:/Emulators`), defined in the default `settings.toml`. Their command lines haven't been launched yet; M3 checks them. | Every built-in system needs a valid emulator for config to validate. |
| 2026-09-28 | A scan removes the games of a folder that's gone (an unplugged drive). User data stays. | `library.db` stays a pure function of config and disk, so a rebuild equals an incremental scan. |
| 2026-09-28 | Scan benchmarks run in the normal `dotnet test`, in a non-parallel collection, with budgets at 2–3× the Debug measurements, capped by the M2 targets (ROADMAP.md M2 log). | They take about 12 s, mostly writing the 10,000 files, and catch regressions early. |
| 2026-09-28 | **Network shares:** folders are listed with a 256 KB buffer (not .NET's 4 KB), and systems are scanned 8 at once on dedicated threads. | On a NAS over SMB, an unchanged rescan of 9,422 games took 13.6 s, almost all of it listing folders. The buffer halves the round trips, and parallel systems hide the latency. Locally it costs nothing ([perf/m2-core.md](perf/m2-core.md#network-share-added-2026-09-28)). Dedicated threads, because blocking a dozen thread-pool threads on I/O would stall other work while the pool grows. |
| 2026-09-28 | **Scan exclusions are configurable:** `[scanning] exclude` in `settings.toml` applies to every system, before each system's own `exclude`. The default is `["images", "manuals", "videos", "gamelist.xml"]`. | The owner asked for a configurable list rather than hard-coded folders. ES-DE keeps media inside each system folder: on the NAS, those were 83% of the entries listed. With the three changes, an unchanged rescan there takes 1.4 s. |
| 2026-09-28 | **Launch placeholders (M3):** `{rom_name}` is renamed `{rom_stem}`, and `{emulator}` and `{core}` are added. A profile's RetroArch core is its own `core` key (a path, expanded like `executable`), and the built-in RetroArch profiles pass it as `-L {core}`. | The owner's placeholder set. A `core` key lets config load check that the core exists, and keeps the args readable. Nothing had shipped, so the rename needs no alias. |
| 2026-09-28 | **Missing installs are warnings, checked at config load**, naming the affected systems, for emulators that enabled systems use. The executable is checked, and the core only if the executable exists. | The owner asked for load-time validation that reports affected systems. Disabling the systems instead would drop their games from `library.db` on the next full rescan whenever an emulator drive is unplugged. Launching reports the same problem. |
| 2026-09-28 | **Windows launching:** the emulator starts inside a job object via `PROC_THREAD_ATTRIBUTE_JOB_LIST` and our own `CreateProcessW` call, and the game has ended when the job is empty. The job doesn't kill on close, allows explicit breakaway, and inherits no handles. The wait also polls the job every second. `Process.Start` isn't used on Windows. | `Process.Start` can't put a child in a job from its first instruction, and assigning it afterwards races with stub launchers. The launcher dying mustn't end a game. Job messages aren't guaranteed. Building the command line ourselves means quoting it ourselves, by the C runtime's rules (A5), which the tests check against `CommandLineToArgvW` and a real child process. |
| 2026-09-28 | **Launch outcomes:** one game at a time; events `Starting`, `Running`, then `Exited` or `Failed`, on worker threads. A non-zero exit within 5 s is `Failed` and isn't counted as a play. An unknown per-game or per-launch emulator is an error, never a fallback. `LaunchPlanner` is a static class rather than the `ILaunchPlanner` interface sketched earlier. | "An immediate non-zero exit" must give a clear message (M3 acceptance). Some emulators return non-zero after a normal session, so the window is short. Falling back could run a game in an emulator it doesn't work with. A pure static planner needs no injection to test. |
| 2026-09-28 | **Play history:** `last_played_at` is the session's end; play time is measured on a monotonic clock and rounded to whole seconds. Sessions left open by a crash are closed at the next open at their start time, as a play with no time. No schema change. | Recently played should reflect the latest activity. A wall-clock change mid-game mustn't corrupt play time. The crash case can't know the duration. |
| 2026-09-28 | **Handing over focus:** `AllowSetForegroundWindow(ASFW_ANY)` at launch; minimise with `SW_SHOWMINNOACTIVE` only once another process's window is in front (or after 10 s); on exit, restore and escalate: plain `SetForegroundWindow`, then with the foreground window's input attached, then with a synthetic Alt key held, then flash. Never change the foreground lock timeout. | Windows' foreground rules make one `SetForegroundWindow` after a game unreliable (input went to the emulator). Minimising straight away would activate an unrelated window and could leave the emulator behind it. A stub launcher's real emulator is a grandchild whose id isn't known when the grant is made. Changing system settings isn't acceptable. |
| 2026-09-28 | **Game mode in the app:** render loop off, low-processor mode at 10 iterations a second, tree paused, master bus muted, input swallowed until 500 ms after focus returns. The launch controller is built on first use, and processes input only while swallowing it. | "Rendering near zero" while a game runs. The grace period stops the button that quit the emulator from acting in the launcher. Building it at boot cost 10–24 ms of our start-up, and an always-on `_Input` allocated about 1.9 KB per frame on the Deck ([perf/m3-launching.md](perf/m3-launching.md)). |
| 2026-09-28 | Launcher.Core sets `AllowUnsafeBlocks` for `LibraryImport` and the Win32 structs, and the tests project for `CommandLineToArgvW`. `tests/FakeEmulator` is a console app the tests run as a process; it isn't referenced as an assembly. | Source-generated interop needs it. No new packages. |
| 2026-09-28 | **Debug arguments** `--launch=<system>/<rel path>`, `--user-dir=<folder>` (portable-mode layout in that folder) and `--quit-after-launch` (exit code 0 if the game ran, 1 if the launch failed). `tools/launch-smoke.ps1` uses them, headless, from `verify.ps1`. | The roadmap's `--launch`. The other two make the launch path testable end to end without touching the user's AppData. |
| 2026-09-28 | **Box templates (M5):** `dvd_case`, `jewel_case`, `cartridge_box`, `clamshell` and `umd_case`, generated by a Godot `[Tool]` script and exported with `GLTFDocument`. `tall_jewel_case` is dropped, Saturn uses `jewel_case` and PSP `umd_case`. A generic system model with a `label` slot is generated too. | The owner's template list. Generating from real case sizes keeps them within the A7 budgets (about 220 triangles) and reproducible, and exporting with Godot's own exporter checks that the importer path works. |
| 2026-09-28 | **One item shader, one surface per template:** models are merged at load, with the face id and aspect in `UV2` and the material colour and roughness in `COLOR`; per-instance data packs into `INSTANCE_CUSTOM` (layer + fade, the plain colour as a 24-bit integer, phase, art aspect). | One draw call per template MultiMesh. Godot 4 has no `INSTANCE_COLOR`: it multiplies the instance colour into `COLOR`. A 24-bit integer is exact in a float. |
| 2026-09-28 | **Generated spine and back** from the cover's dominant colour, chosen in the vertex shader from the 4×4 mip; titles from a SubViewport of labels (`TitleAtlas`) sampled by the same shader. | No per-cell CPU work or extra textures to bake, it follows the fade, and the text uses Godot's font stack (any script, system fallbacks). Label3D nodes would add a draw call each and couldn't follow the vertex-shader bob. |
| 2026-09-28 | **Derivatives hold the whole image, squeezed to 512²; the shader crops** by the source's aspect (`media.width`/`height`). `GameRow` carries the cover's aspect, size and time. | One derivative serves every template. With size and time indexed, a worker names a derivative with no file access and one string allocation (2.2 KB per cover before). |
| 2026-09-28 | **User art is indexed in M5** (moved from M4): `ConfigDir/media/<system>/<kind>/`, matched by `path_key` with or without the ROM's extension; migration 0002 stores each file's size and time. | Art needed a source that survives a rebuild before M4. Baking derivatives from it still waits for M4's encoder; until then, missing derivatives show plain boxes. |
| 2026-09-28 | **The items stay still and the grid root moves** to scroll, instead of the camera. | Two grids on screen at once during transitions, each with its own scroll, and one camera. It's still one transform a frame, as the camera was. |
| 2026-09-28 | **Transitions and edges fade opaque items to the background in the shader** (emission becomes the gradient's colour at that pixel), and the two grids' fades are staggered. | No alpha blending and no variant (A3). Opaque grids occlude each other, so they overlap only briefly. |
| 2026-09-28 | **Input is polled** (`NavInput`), with repeat after 0.32 s speeding up from 120 ms to 35 ms over 1.4 s. The actions are registered in code at boot. | `_Input` allocates per event (M3). A continuous ramp feels better than two fixed rates. M7's settings UI will own remapping. |
| 2026-09-28 | **Boot:** config and DB on the thread pool while the main thread builds the scene and creates the cover array; built-in models through the threaded loader; the first upload and every pipeline before `interactive`; the launch controller and glyphs after it, one step a frame. Systems never scanned are scanned after the warm-up, except in benches. | The main thread does no file or DB I/O (CLAUDE.md), and the post-interactive frames stay under 25 ms. Warm start-up of our code: 340 ms with 14,215 games. |
| 2026-09-28 | **The shader baker is on**, so exports are made with a rendering device (not `--headless`). | Cold start-up of our code halves (2.3–2.4 s to 1.2–1.4 s); a headless export bakes nothing. |
| 2026-09-28 | **Godot's staging buffer is capped at 16 MB** (default 128). | Fullscreen at 2560×1440 went from 521–554 MB to 441–447 MB of working set (target 512). Uploads never exceed about 3 MB a frame. |
| 2026-09-28 | **The bench window starts at `interactive`**, and `--bench-scenario=scroll`, `--no-textures`, `--render-scale`, `--upscaler`, `--upload-cap`, `--start-system`, `--start-index` and `--nav-script` are added. The report is format 2. | Frames before `interactive` are start-up. The scroll scenario and the control are what the M1 targets are measured with; the rest make captures and experiments reproducible. |
| 2026-09-28 | **The M1 p99 target isn't met in this session, and the cause is presentation:** p99 is about 21 ms windowed and 22 ms fullscreen with covers, without them, and with both grids hidden. | Recorded rather than papered over; PresentMon (needs approval) is the next step. |
| 2026-09-28 | `project.godot` now uses the **Mobile renderer** (M1's decision, applied when the real grid landed), and the font LCD subpixel layout is off. | M1 chose Mobile. The title atlas is drawn on a transparent viewport, where subpixel antialiasing would put coloured fringes in its alpha. |
| 2026-09-28 | **Scraping has three providers (M4): ScreenScraper, IGDB and SteamGridDB**, each with a capability map. `[scraping] provider` is asked first and `fallback` (in order) fills only what's missing; `cover_sources` is gone (nothing had shipped). Systems gain `igdb_platforms`. | The owner's brief. Only ScreenScraper has back, spine and box texture; IGDB has metadata and front covers; SteamGridDB has community art and no metadata (the research is summarised in [perf/m4-scraping.md](perf/m4-scraping.md) and the M4 log). |
| 2026-09-28 | **ScreenScraper lookups send the file name, size and `romtype`, plus CRC32, MD5 and SHA-1 for files up to `hash_limit_mb` (64)**, hashed once and kept in `games`. Bigger files (disc images) go by name and size. If that finds nothing, a title search, accepting only a hit whose name matches. | ScreenScraper's rules ask for a hash with every lookup. The owner chose this middle way: hashing every PS2 image over the NAS would read terabytes. Misses count against a smaller daily quota, so a name-matched search is the fallback, never a guess. |
| 2026-09-28 | **The BC7 encoder is our own (`Bc7Encoder`: mode 6, plus mode 1 for opaque blocks with edges); images are decoded by the OS (WIC).** BCnEncoder.Net stays in the tests only, as the decoder that checks our blocks bit for bit. | The owner approved BCnEncoder.Net, but it took about 10 s a cover (39 hours for the synthetic library). Ours takes about 0.44 s and scores 40 dB on real box art, slightly above BCnEncoder.Net ([perf/m4-scraping.md](perf/m4-scraping.md)). No image-decoding package is needed. |
| 2026-09-28 | **Scraped files live under `DataDir/scraped/`:** `media/<system>/<kind>/<path_key>.<ext>` (full size) and `responses/<provider>/<system>/<path_key>.json`, not DataDir's `media/`. | In the portable layout ConfigDir and DataDir are one folder, where `media/` is the user's own art: scraped files would have been indexed as the user's. |
| 2026-09-28 | **The saved responses are what rebuilds scraped data:** each carries the matched id and method, the media it supplied, and the raw response (redacted), which the provider's own parser reads back offline. A scan restores them for every game it adds, so a rebuild or a recreated `library.db` gets metadata, matches and media links back with no network. | `library.db` stays a pure function of config, disk and `scraped/` (A4). Re-parsing keeps one code path for live and offline, rather than a second normalised copy. |
| 2026-09-28 | **The scrape queue lives in `userdata.db`** (`scrape_batches`, `scrape_jobs`, keyed by identity). Single games run ahead of batches. Stopping the service pauses (jobs stay queued; `ResumeAsync` carries on); `CancelBatchAsync`, or cancelling an operation's token, abandons a batch. | Resumable after the app closes, and a library rebuild can't lose it. A pause and a cancel are different intents. |
| 2026-09-28 | **A used-up quota, a closure or refused credentials rest the provider** (quota: until ScreenScraper's midnight, French time; credentials: until restart) and shut its gate, so queued requests fail without going out. Games carry on with the other providers and are marked `partial`. "Scrape all missing" is never scraped, `not_found` or `error`, plus no cover: `partial` isn't retried by it. | A batch shouldn't stall for a day, and mustn't keep hitting a closed API. The owner's definition of missing (never successfully scraped, plus no front cover). |
| 2026-09-28 | **The scraped title** is kept in `metadata.title` and written to `games.title` (with " (Disc n)" for a lone disc) for the grid; a case-only rename keeps it. The user's metadata overrides are new `game_overrides` columns, which scraping never writes; details show them over the scraped values. | A4 already said `games.title` holds the scraped title. Keeping overrides in userdata.db means a re-scrape can't touch them. |
| 2026-09-28 | **Clearing a game removes everything scraped and every override of its metadata, including its manual matches and the user's own art files for it** (not a file another game also uses). Favourite, play history, emulator and hidden stay. | The owner's choice of scope (the fullest of the options offered). |
| 2026-09-28 | **IGDB conventions:** rating from `total_rating`, else `aggregated_rating`, else `rating`, over 100; release date from the system's `release_dates` in the most wanted region, as precise as its `date_format` (else `first_release_date`); players from the system's multiplayer modes ("1" for a game whose only mode is single player); companies and genres joined with commas; images at `t_1080p`. The token is cached on disk and requested again a day before expiry or when refused. | IGDB has three ratings, no player-count field, and tokens that can't be refreshed, with a limit of 25 per application. |
| 2026-09-28 | **The app bakes missing derivatives after its background scans** (and after F5), on `DerivativeService`'s below-normal thread; not in benches. Covers baked then show the next time their system is entered. | The M5 carry-over: the user's own art had no derivatives. An A/B against M5 in one session shows no change in scroll or start-up ([perf/m4-scraping.md](perf/m4-scraping.md)). |
| 2026-09-28 | **`odyssey-scrape` (`tools/scrape-cli`) exposes every operation** for live testing with the owner's credentials, on the app's own folders or a `--user-dir`. It's in the solution. | The owner asked for it. In the solution so it always builds with Core. |
| 2026-09-29 | **Theme manifests name everything explicitly (M6):** `[templates.<id>]` (a model and optional slot chains), `[defaults]` (`system_model`, `tint_system_model`, `game_template`), and `[systems.<id>]` (`model`, `tint`, `colour`, `game_template`, `look`), replacing A6's folder convention (`models/systems/<system>.glb`, `models/templates/<system>.glb` inside a theme). | Every file is then named by a key, so a missing or broken one is reported at its key and line; a template can serve several systems; and nothing in a theme is probed. |
| 2026-09-29 | **The built-in theme owns the system-to-box mapping.** The M5 templates moved to `godot/themes/memory-card/`, whose manifest assigns them (and a colour and look) to the 14 built-in systems; `game_model` left the built-in systems.toml and `ConfigLoader.GameModels` is gone. `game_model` is now the user's choice of a template id, looked up in the active theme then the built-in one, and ranks above the theme's own choice. | The owner's brief: no special-case code for default boxes. Config is the user's intent, so a `game_model` the user wrote beats a theme's default. |
| 2026-09-29 | **Resolution order (A7):** games: per-game model; `ConfigDir/models/templates/<system>.glb`; `game_model`; the active theme's system template; its default template; the built-in theme's two. Cards: `ConfigDir/models/systems/<system>.glb`; the theme's system model; its default; the built-in theme's. The app loads candidates in order and uses the first that loads (a game template needs a `cover`). | A6's order, with the built-in theme as the last resort, so a partial theme always has a model for every system. |
| 2026-09-29 | **Media slots are every image kind, each with a fallback chain** of media kinds, `generated` and `authored`, ending with the material's authored texture. A slot a template doesn't list is `[<kind>, "generated"]`. | The owner's brief. `generated` keeps M5's drawn spines, backs and title cards as something any theme can use, not a special case of the default boxes. |
| 2026-09-29 | **Slot media is standardised to two sizes:** the cover at 512² (the derivative whole) and every other slot at 256² (the same derivative from mip 1). Two `Texture2DArray`s, a layer per pool cell and slot channel; only slots whose chains name a media kind get layers, and only those kinds are queried. Per-cell slot state (fallback, aspect, fade, layer) lives in an RGBA32F texture the shader fetches in the vertex stage. Templates share a material unless their authored textures or tint differ (the same shader either way). | Keeps M1's batched MultiMesh plus `Texture2DArray` approach, which needs fixed layer sizes. One derivative serves any slot with no second bake, and all eight slots fit the 64 MB pool target (60.1 MB; three 512² arrays would be 65.5 MB). INSTANCE_CUSTOM has four floats, too few for per-slot state. |
| 2026-09-29 | **The upload cap counts a 256² layer as a quarter of a cover**, and workers take covers first. | The cap guards against bursts of upload cost, which scales with bytes; covers matter most on screen. |
| 2026-09-29 | **`LibraryService.MediaChanged`** is raised after a rescan changed user art or models, a scrape saved media, a clear, a rebuild or a bake; the navigator re-reads the shown list's media and rebinds only the games that changed, in place. Derivatives are baked for every image kind. | The owner's brief: rebind without reloading the model. Covers baked in the background now appear without re-entering the system. |
| 2026-09-29 | **Per-game models are templates too:** a MultiMesh each (not per-node instances), added when they finish loading, scaled to fit the cell; loaded from the `.glb` each session (no `CacheDir/models/` cache yet). Supersedes the 2026-09-27 "per-node instances for custom models". | One path for every model, and the same one draw call per model. Converting on a worker from `GltfDocument`'s CPU-side meshes needs no scene cache for correctness; the cache is a load-time optimisation for M6 part 2. |
| 2026-09-29 | **Switching theme at run time:** T or Menu on the systems screen, or `--nav-script` `theme`; the plan is built on the thread pool, models load in the background, the texture arrays are built on a worker, then templates, layout, look and the shown list are swapped. Session-only until M7 writes `[display] theme`. | The owner's brief: no restart. Creating textures on the main thread can stall for tens of milliseconds (M1). |
| 2026-09-29 | **Corner colours are exact on Forward+ but within 2/255 on Mobile**, because Mobile composites the canvas background through its 3D buffer. We stay on Mobile. | Measured (A6). M1 chose Mobile for 36–42% less GPU time; a 2/255 shift in dark corners isn't visible. |
| 2026-09-29 | **A headless run resolves no theme.** | With `--quit-after`, the engine shut down while the boot task was reading `res://` through Godot's file API on the thread pool, which crashed. Headless runs only launch. |
| 2026-09-29 | **The upload cap is 4 cover-sized uploads per frame**, down from 8. | Measured in M6: a whole row of 5 to 8 covers uploaded in one frame made single uploads take 14–21 ms (so M5's occasional upload maxima); with 4 the longest was 1 ms, and covers stayed 100% textured ([perf/m6-themes.md](perf/m6-themes.md#upload-cap)). |
| 2026-09-30 | **Models are checked by Core before Godot sees them (M6 part 2):** `ModelInspector` validates every range, index, node and image of a user's `.glb` and counts it against `ModelBudget`; `ModelProcessor` scales textures over the budget's side down; only a file that passed is given to `GltfDocument`. Built-in theme models are checked by the tests instead. | "Never crash on a bad file": Godot's glTF parser is native code, and a bad accessor range can crash it. Doing it in Core keeps it testable without Godot, and one validator serves import, the cache and the console. |
| 2026-09-30 | **The processed-model cache holds processed `.glb` files, not Godot scenes:** `CacheDir/models/<hash of path>-<hash of version, size, time, kind>.glb` with its report as `.json`; a rejection is cached too; a changed source gets a new entry and the old one is deleted. Supersedes A7's "caching the converted scene". | Core owns it (no Godot resource files written from users' content), and what's expensive to redo is the checking and texture scaling; parsing a processed file takes about 7 ms on a worker, off the main thread. |
| 2026-09-30 | **A game template needn't have a `cover` material** (nor any slot). | The owner's brief: a CRT showing the screenshot is a template. |
| 2026-09-30 | **Per-game models are drawn on nodes, not MultiMeshes:** one pooled `MeshInstance3D` per grid cell, made with the grid, gets the cell's per-game model when it binds. Supersedes the 2026-09-29 "a MultiMesh each". | The owner's brief: they can't share batched rendering. A MultiMesh of 64 instances per model meant hundreds of MultiMeshes for a list with hundreds of models; now it's at most one draw per visible cell, and binding allocates nothing. |
| 2026-09-30 | **Clips:** a model with clips keeps its node tree (duplicated per cell and pooled); `idle` makes every cell a node, while `focused` and `launch` only swap the focused cell to a node, which blends to a generated `_rest` clip before rejoining the MultiMesh. The launch waits for the launch clip (at most 2 s). | Batching stays for every template without an idle clip. |
| 2026-09-30 | **A node's per-cell data is an instance uniform (`node_custom`), set as a `Vector4`.** | One shader and one material for batched and node-drawn items. Godot converts a `Color` given to an instance uniform from sRGB to linear, which scrambled the cell and the packed colour (found in a capture of the sample theme). |
| 2026-09-30 | **Runtime textures:** the loader tells `GltfDocument` to discard its images and decodes each base colour image itself, with mipmaps. | Godot's runtime glTF import makes RGBA8 textures without mipmaps (measured), which alias on small items. |
| 2026-09-30 | **Importing a game's model** (`ModelImportService`) takes a `.glb`, a zip of an OBJ model or an `.obj`, converts OBJ in Core (`ObjConverter`, no package), fits it to the per-game budget, and writes it to `ConfigDir/models/games/<system>/<rel path>.glb` (the ROM's own name, so it's that game's only). `LibraryService.RefreshUserMediaAsync` indexes it without a ROM scan. A rejected file changes nothing. | The owner's brief. The slot is A7's level 1, so the import is just a file the scanner would find anyway, and a rebuild keeps it. |
| 2026-09-30 | **The model log is `DataDir/logs/models.log`** (about 1 MB, then `models.1.log`): every processing report, rejection (with what's used instead) and import. `odyssey-scrape models-log` prints it; M7 shows it. | "A log the user can view." DataDir holds what the user can't regenerate or should keep. |
| 2026-09-30 | **Only base colour images count as a model's textures.** Other maps (normal, metallic-roughness, occlusion, emissive) are checked but not counted, and noted in the report. | The app decodes base colour images alone, so the others cost nothing. Counting them rejected a user theme's PBR system models (9 and 13 images, 3 and 4 of them base colour) that loaded before M6 part 2. Count them again when they're honoured. |
| 2026-09-30 | **Config is written through Tomlyn's syntax tree (M7):** `TomlEditor` edits the parsed file and writes it back, so everything not edited stays byte for byte; only values that differ from the defaults are written, a value set back to its default is removed unless its line has a comment, and the edited files must load with no new error before anything is written (atomically). | The owner asked for comments to be kept, or to be told the trade-off. Tomlyn 2.10.1's syntax tree round-trips byte for byte and its nodes and trivia can be edited, so no trade-off was needed. The one loss: a changed multi-line array is written on one line, dropping comments inside it. |
| 2026-09-30 | **Paths are written with `/` and braces doubled** (`ConfigWriter.PathValue`). | A5 recommends `/`; `//server/share` still names a share; a folder named `{x}` must not be read as a placeholder. |
| 2026-09-30 | **The settings screens are Godot controls driven by `NavInput`, not by Godot's `ui_*` actions**, which are emptied at boot. Each command is a keyboard action and a gamepad action. | A held D-pad repeats with the grid's acceleration (Godot doesn't repeat joypad buttons), nothing moves twice, and the on-screen keyboard can take physical typing while the pad still drives its keys. The mouse still works through Godot's GUI events. |
| 2026-09-30 | **Menu (or B and Escape on the systems screen) opens the settings.** T alone switches theme for the session; Menu no longer does. | The owner's brief puts theme selection in the settings screen, which saves it. |
| 2026-09-30 | **The on-screen keyboard works like the Xbox keyboard on a pad** (A types, X deletes, Y is a space, LB and RB move the caret, LT shifts, RT switches to symbols, Menu is Done, B cancels), with Paste, and Show for hidden entry. | A familiar layout; B stays "back" as everywhere else in the app. Paste matters for API keys. |
| 2026-09-30 | **The pickers are the app's own** (never the OS dialog): folders listed on a dedicated thread each (a directory read on a share can block for many seconds and can't be interrupted, so a superseded one is just abandoned), a virtualised list, drives listed without touching them and labelled later, a thumbnail decoded by the OS decoder on a worker, and each use's last folder in `DataDir/picker-locations.json`. | The owner's brief: controller-first, thousands of entries, network shares that are slow or gone, never a frozen frame. DataDir, because the history is the user's but worth nothing to rebuild. |
| 2026-09-30 | **Credentials are masked everywhere in the UI, and the keyboard never starts with the old value.** "Test connection" uses a scrape service of its own, built from `secrets.toml` as saved. | "Credentials are masked in the UI and stored in the user config file": `secrets.toml` is the user's config file for them (A5), and the only file they're written to. A test's refusal would otherwise rest the provider for real scrapes until a restart. |
| 2026-09-30 | **Rescans and scrapes are jobs (`LibraryJobs`)** with a progress card over the grid and rows in the settings, cancellable, never blocking navigation; the grid's View/F5 rescan goes through them too. Progress from worker events is coalesced to one refresh a frame. | The owner's brief: progress bound to the M4 events, cancellable, non-blocking. |
| 2026-09-30 | **The settings screen and its services are built in the warm-up after `interactive`.** | Boot stays as it was: our start-up measured 446 ms against 517 ms for M6 part 2 in the same session, and the scroll is unchanged ([perf/m7-settings.md](perf/m7-settings.md)). |
| 2026-10-01 | **Item options open with X** (O or the menu key on a keyboard) on the focused system or game, on the settings screen's layer and with its components. Favourites and Recently played have none. | The owner's brief: the West button. Opening on the same layer gives the panels the pad, mouse and keyboard handling, pickers and dialogs of part 1 for nothing. |
| 2026-10-01 | **A system's options are the settings screen's system page, extended** with its models and "scrape this system", whichever way it's opened. | One page per system, not two that drift apart; ROM folders and the emulator were already there. |
| 2026-10-01 | **The user's own image for a slot is copied to the game's whole ROM name** (`media/<system>/<kind>/<rel path>.<ext>`), one per kind (the game's file in another format is deleted), its derivative baked before it's indexed. Removing it restores the scraped image from the saved responses. | It's the folder convention the scanner already indexes (A4), so a rebuild keeps it, and with the ROM's extension it's that game's only, as models are. Baking first means the grid shows it as soon as it's indexed. A4 had left a removed user image with no row until the next scrape. |
| 2026-10-01 | **The media panel shows the design's eight image slots.** The brief's "support texture" (ScreenScraper's name for a disc or cartridge's art) is the `label` slot. There's no video slot: the design has no video kind, and nothing plays one. | Slots are the media kinds (A7). Adding video would be a new kind, a scraping kind and a player; it's for the owner to decide. |
| 2026-10-01 | **Metadata the user types is checked first** (`MetadataInput`): release dates as a year, a month and year or a day, day first, stored as partial ISO 8601; ratings out of 5, out of another number or as a percentage, stored 0 to 1. A value equal to the scraped one isn't kept as the user's; Y goes back to the scraped value. | M7's "input is validated before saving". UK dates are day first. Not keeping a copy of the scraped value lets a later scrape still correct it. |
| 2026-10-01 | **Titles after a scrape, clear or edit are updated in place** when the shown list's order is unchanged, else the list is bound again on the same game; changes within 0.4 s are read once. `RefreshItem` sets the cell's title too. | The brief: affected items update without a restart. A whole rebind would re-request every visible cover; renaming in place touches only the changed cells. |
| 2026-10-01 | **A system's own models and template choice reload the theme** (a switch to the same theme, in the background) rather than patching the grids. Choosing one of the theme's templates deletes the user's own template file, which would otherwise still win. | System models are resolved with the theme (A7); the theme switch already rebuilds templates and the slot layout without a restart, off the main thread. |
| 2026-10-01 | **One game's scrape is a job of its own**, allowed beside a batch ("scrape all missing" or a system); batches stay one at a time. | The service already puts single games ahead of batches; making the user wait for a batch to scrape one game would be wrong. |
| 2026-10-01 | **A PS2 icon's `.anim` beside an OBJ becomes morph targets and a `focused` clip.** The OBJ is the first frame (ps2iodb turns the PS2's axes a half turn about Z; the converter finds the turn by matching the first frame to the OBJ); every other distinct frame is a target (frames with the same vertices share one, so most icons need 4 to 7 of the 8 allowed); the weights are sampled at every key time, so linear interpolation is exact. Key times are taken as 60 Hz frames over `animSpeed` (the format isn't documented); `playOffset` is ignored, and normals stay the first frame's. An icon with more shapes, or one that doesn't fit its OBJ, is imported still, with a warning. | The owner's imported icons didn't animate: OBJ has no animation, and the `.anim` was ignored. `focused`, not `idle`: the PS2 browser animates the selected icon, and the rest of the grid stays batched. |
| 2026-10-01 | **A user theme's models' node trees are freed once the next theme is applied** (`ModelLoader.FreeRetired`). | Found while checking: switching away from a theme whose models have clips leaked them (since M6 part 2), and importing a system model now reloads the theme. |
| 2026-10-01 | **View (Select) opens a power menu** (Restart system, Shut down system, Sleep system, Quit app) in either grid, instead of rescanning; P opens it from the keyboard, and F5 still rescans. A row acts without a second question. A restart or shutdown quits the app once Windows has accepted it. Power calls are behind `IPowerControl` in Core's Platform; Linux offers only Quit app for now. | The owner's request. Rescans are in the settings (and on F5), and the launcher scans systems never scanned by itself. Opening the menu is the confirmation, as on consoles. Quitting first would leave no app to make the call, and waiting for Windows to end the app risks the databases mid-write. |
| 2026-10-01 | **The built-in catalogue is ES-DE's** (150 systems and about 450 emulator profiles added to the original 14 and 18), converted from its XML; regional twins are aliases, not systems (A5, The ES-DE catalogue). | The owner asked for the systems and emulators ES-DE has. Aliases keep the grid free of duplicates and ES-DE's folders working, at the cost that a user with both `genesis` and `megadrive` folders needs `rom_dirs`. |
| 2026-10-01 | **`run_file` profiles run the game's own file** (programs, batch files through `cmd.exe /d /s /c ""path""`, shortcuts through the shell), never `cmd.exe /C <rom>` as ES-DE does. A `%` in a batch file's path is refused. | The shortcut-style systems (ports, ags, mugen, openbor...) need it, and a plain `CreateProcess` of a `.bat` splits `Sonic & Knuckles.bat` into commands (shown by a test). The owner chose a safe launcher over ES-DE's. |
| 2026-10-01 | **Systems with no games have no card** (`[display] hide_empty_systems`, default on), install warnings cover only systems with games and only their default emulator, and the Emulators page lists only their profiles. | With 164 systems, an empty card for each, and a warning for every emulator the user never installed, would bury the grid and the settings. The owner chose it (like ES-DE). |
| 2026-10-01 | **The built-in defaults and theme are read by `TomlFast`, not Tomlyn.** Boot skips the install checks (they run after `interactive`). | The catalogue made config load 50 ms slower through Tomlyn alone (about 60 ms against 2 ms warm, 114 ms against 46 ms first). `TomlFast` is strict, falls back to Tomlyn for anything else, and a test compares its tree with Tomlyn's. |
| 2026-10-01 | **Windows and Steam are built-in systems** (`windows`, `steam`: shortcuts, batch files and internet shortcuts, run by `run-file`; no `.exe`). **A Steam game's `.url` is handed to Steam and followed through the Steam client's registry state** (`RunningAppID`, the app's `Running` flag once seen clear, `Updating`, and the client's process), not through a process: ended after two polls without it; not seen running within 2 minutes (updates not counted) is a failed launch that isn't a play; cancelling leaves the game to Steam. | The owner's request. The process a Steam shortcut starts only hands the URL to the running client and exits, so following it saw the game end at once (or, with Steam closed, followed the Steam client itself). The registry is what Steam publishes, needs no network or API key, and a check on the owner's PC showed an app's `Running` flag set while nothing ran, hence trusting it only once it has cleared. Watching the install folder's processes (through `libraryfolders.vdf` and the app manifest) would also find the game's processes, at more cost; ending a Steam game could lose a save Steam is syncing. |
| 2026-10-01 | **Scraping media (supersedes part of the 2026-10-01 "eight image slots" row):** box textures aren't scraped any more; ScreenScraper's support texture fills the `label` slot; `video` is a new media kind, scraped from ScreenScraper (its normalised video first) and kept as an MP4, with no slot, derivative or player yet. `[scraping] media` defaults to cover, back, spine, screenshot and logo (the wheel), so fan art (`hero`), support textures and videos are off until chosen; an old `box_texture` in the list is a warning and left out, the rest kept. The settings' Scraping page has a Media page that turns each kind on or off. | The owner's request. A video is megabytes a game and a request against ScreenScraper's quota, so it's off by default with the other extras. Dropping only the retired value keeps a user's other choices instead of the whole list falling back. |
| 2026-10-01 | **Each scraping request is timed per attempt, from leaving the provider's gate** (30 s; 5 minutes for a video), not by `HttpClient.Timeout`. | A video can't download in 30 s on a slow server, and time spent queued at the gate shouldn't count against a request. |
| 2026-10-01 | **A Game Boy box (`gameboy_box`) for Game Boy, Game Boy Color and Super Game Boy:** 125 × 125 × 18.2 mm, square, printed on both sides; Game Boy Advance stays on `cartridge_box`. The spine slot's `extras.aspect` now leaves out the chamfers, on every box. | The tall `cartridge_box` cropped a third off square Game Boy art. The depth follows ScreenScraper's art, not a ruler: its Game Boy fronts and backs are 700 × 700 and its spines 98 × 700, so the spine face must be 0.14 of the height for the whole spine to show (a real box is nearer 22 mm, which would crop a fifth off it). The old spine aspect counted the chamfers the spine art doesn't cover, so it over-cropped every box's spine. |
| 2026-10-01 | **A Steam store provider (`"steam"`), found by title, never by the shortcut's app id**, through Steam's keyless Web API: `IStoreQueryService/SearchSuggestions` (games only, asked as the US store in the first `[scraping] languages` Steam has), whose answer carries each hit's store item (assets, basic info, release, reviews, screenshots), so a lookup is one request; a stored match is fetched by app id with `IStoreBrowseService/GetItems` (`success` 15: gone, so searched again). Images come from `shared.akamai.steamstatic.com/store_item_assets/`: the 2x library capsule as the cover, the library hero, the first screenshot, and `logo.png`, which the API doesn't list, so a HEAD request checks it first. Only systems with `steam_store = true` (Windows and Steam) are looked up. Opt-in: the default order is unchanged. | The owner's request: Steam's own art, which SteamGridDB's API doesn't serve (only community uploads; the originals are shown on its site, not in its API), without relying on a shortcut's app id. The other routes in the ValvePython `steam` library (its maintained fork, solsticegamestudios/steam) need either a Steam client connection and app ids (PICS product info: SteamKit2, a new package, and no name search) or a full app list (`ISteamApps/GetAppList` is gone; `IStoreService/GetAppList` needs a Web API key). Checking the logo matters: a missing one offered as found would keep the fallbacks from being asked for it. A game no longer sold isn't found by the search; the next provider has it. `steam_store` keeps a console ROM from matching a PC re-release. |
| 2026-10-01 | **Windows releases are built by GitHub Actions** (`.github/workflows/release.yml`) when a `v<version>` tag is pushed: build, the tests without the scan benchmarks, Godot's C# build and import, the ExportRelease export, the launch smoke test of the export, and a zip (one folder inside) with its SHA-256, attached to the tag's release (made with generated notes if there isn't one; a pre-release for a version with a `-`). The tag must match `Version` in Directory.Build.props and `config/version` in project.godot. Run by hand, it's a test build kept as the run's artifact, and nothing is released. The runner has no GPU, so the export's shader baker runs on D3D12's software adapter (WARP), which Godot takes as a CPU device; the step fails if the PCK is under 1 MB. MSBuild node reuse and the compiler server are off. Godot and its templates come from godotengine/godot-builds, checked against its SHA-512 sums. | The owner's request. Linux and Android releases wait until the app is further along. A WARP export on the Deck (`--gpu-index 1`) gave a PCK of the same size as the GPU's (2,786,584 bytes) and passed the launch smoke test. The benchmarks' budgets were set on the Deck, so a shared runner's times aren't comparable. Build servers started by the export's `dotnet publish` inherit the console wrapper's output pipe, and kept it waiting about 10 minutes after the export had finished (622 s, against 17 s with them off). |
| 2026-10-01 | **"Scrape this game" matches manually:** it searches every provider at once and lists each one's results (closest name first, with the current match marked), and A on a result scrapes the game with it. The choice is a manual match (`manual_matches`; no schema change), and a game's manual matches are asked first, the latest choice first, in every scrape and rebuild; the configured providers then fill in what it lacks. What the chosen provider had brought in before and doesn't bring again goes, so a corrected match leaves no art or metadata of the wrong game behind; a provider that fails keeps its data. A chosen provider outside `[scraping]`'s order is used for that game. Batch scrapes still match automatically, but keep to the manual matches. | The owner asked for manual matching from the game's options, with every provider's results shown (moved out of M7), and one choice that scrapes at once (no choice per provider, no way to refuse a provider: users don't need to blacklist providers). Asking the chosen game's provider first makes the chosen game's data the one shown, while the others still fill the gaps; the latest choice leads because it's what the user last said is right. Without the replacement, a corrected match would still show the wrong game's art for kinds the right one lacks. |
| 2026-10-01 | **Boxes shaped by the art:** a template's `shape = "media"` (A6) makes each game's box take its front's proportions from its cover and its depth from its spine, reshaped in the item shader from two slot-state columns per cell. The cells fit the list's widest and tallest box. The built-in `big_box` does it for DOS. | DOS big boxes have no standard size, so any fixed box crops most of them. Reshaping in the vertex shader keeps the box in its MultiMesh and costs nothing on the CPU per frame. Moving each half of the rest mesh, rather than scaling it, keeps bevels and corners true. Before and after benches: [perf/box-shapes.md](perf/box-shapes.md). |
| 2026-10-01 | **Every `.glb` in the Godot project has the "keep file" import**, written by `BoxTemplateGenerator` and checked by `BuiltInModelTests`. A `game_template` that names a model's path says how to declare the template. | The exported app reads a built-in theme's models from the PCK as files. `gameboy_box` and `big_box` got Godot's default scene import, so the export packed scenes, the theme dropped both templates, and Game Boy and DOS fell back to the DVD case, though the editor (reading the folder) was right. A theme naming `models/games/big_box.glb` as a `game_template` only said there was no such template. |
| 2026-10-01 | **Textures are filtered at 16× anisotropy** (`rendering/textures/default_filters/anisotropic_filtering_level=4`), not Godot's default 4×. | Scraped DOS spines (60×680) are squeezed into a square derivative, so on a focused box the GPU sees about 8 texels a pixel across the spine and under 1 along it; at 4× it took the 128² mip of a spine slot's 256² layer, and the title on the spine was unreadable. 16× takes the whole layer. On the Deck the scroll's GPU time moved by 0.01–0.02 ms, within the noise, with PS2's 10,000 games and the owner's 951 DOS games alike ([perf/anisotropy.md](perf/anisotropy.md)). Baking strips at another size would also have changed the derivative format and the slot arrays' memory. |
| 2026-10-02 | **Status indicators top right** (the network, the battery's charge and the time), each switched on or off by `[ui]` in settings.toml (the settings screen's UI section), on a canvas layer of their own above the settings screens. The device's state is read behind `IDeviceStatus` (Windows: `GetSystemPowerStatus`; the default route's hardware adapter from the interface table, and the WLAN service's signal quality as 0 to 3 bars), polled every 10 s on the thread pool and at once on a network change, paused while a game runs, and handed to the main thread only when it changes. The clock follows the user's regional short-time format, checked once a second, its text made once a minute. The icons are Lucide's SVGs, imported at 4× with mipmaps. `--fake-status` shows made-up states for captures. | The owner's request, with Lucide named, the clock in Windows' format, signal bars, and the indicators shown over the settings too (so a toggle there shows at once). An `HBoxContainer` leaves hidden children out of its layout, so the shown indicators sit together against the right edge with nothing to work out. Godot 4 has no battery or network state, hence Core's `Platform`. Polling and change detection keep the main thread to one closure per change; none of the OS calls (the WLAN query is an RPC to its service) runs on it. Importing at 4× keeps the icons sharp where the overlay is scaled 2.7× at 2160p. |
| 2026-10-02 | **One media folder (supersedes the 2026-09-28 rows on scraped files under `DataDir/scraped/` and user art indexed from `ConfigDir/media/`, and the 2026-09-30 row's model slot):** every game's media is a file in `DataDir/media/<system>/<kind>/<rel path>.<ext>`, scraped or the user's own, and per-game models are one more kind (`media/<system>/model/<rel path>.glb`). The scanner indexes the whole folder, and `media.source` is gone (migration 0004, which also marks every system never scanned so the app rescans them once). One file per game and kind: a scrape downloads only kinds the game has no file for and never replaces one; the user's own image replaces the kind's file, and removing one leaves the slot empty until a scrape fills it. Scraped files are named by the ROM's `rel_path`, like the user's. Outside the portable layout the folder is in DataDir (`%LOCALAPPDATA%`), so the user's art and models move there from `%APPDATA%`. Files in the old folders aren't moved: the user moves them, or scrapes again. | The owner's request: media straight in `userdata/media`, models as one more kind of media. In the portable layout ConfigDir and DataDir are one folder, so the old two trees (scraped by `path_key`, the user's by `rel_path`) would be one file on Windows, which ignores case; one tree with one file per kind follows. The owner chose no record of where a file came from: a scrape never overwrites, so nothing it can't tell apart is lost, and to get art scraped again you remove the file. DataDir, because scraped art and videos run to gigabytes, which don't belong in a roaming profile. A manual match can no longer take the wrong game's images back (2026-10-01): its metadata and match still go; its images stay until removed. |
| 2026-10-02 | **Saving providers' responses is off by default (supersedes the 2026-09-28 row on saved responses rebuilding scraped data):** `--save-responses`, on the app or `odyssey-scrape`, saves them in `scraped/responses/` (same place and format) for that run, to debug a scrape. A rebuild or a re-added game restores metadata and matches from any that were saved; media comes from the media folder. | The owner's request. Without them a rebuild keeps media and manual matches, but scraped metadata and automatic matches need a scrape again, which `library.db`'s rebuild rule allows ("from config, disk and scrapers"). |
| 2026-10-02 | **One PC big box, two templates:** `big_box` is renamed `generic_box.glb`, used by `generic_box_spine` (DOS: the default chains) and `generic_box_logo` (Windows and Steam: `spine = ["logo", "generated"]`; before, Windows had `big_box` and Steam the DVD case). A logo on a spine is drawn whole along it, over the spine's fallback darkened to a deep shade (A7 Generated faces). The box's front and back chamfers belong to the `cover` and `back` slots (`BoxSpec.PrintedBevels`) and its case is dark. | The owner's request: the light case on the chamfers showed as white lines round the art, and the top and bottom as light edges. Windows and Steam games usually have logos (Steam's store and SteamGridDB) and seldom spines, and a wide logo cropped to fill a tall spine shows only a sliver, so it's turned and fitted; the darkened fallback, not a colour chosen from the logo, because a logo's mips can't tell a light fill from its dark outline, and logos are made to sit on dark art. A user's `game_model = "big_box"` now falls through to the theme's template for the system. Before and after benches: [perf/generic-box.md](perf/generic-box.md). |
| 2026-10-02 | **Manual matching asks ScreenScraper's ROM index for the file first; no MAME name list (yet).** The panel's first search also sends the file lookup a scrape sends (`jeuInfos.php`, `romnom` with size and hashes) and lists its hit first, as the file's match; a ScreenScraper lookup that finds nothing saves its replies with `--save-responses`. | Arcade sets are named by MAME's short names (`3kokushi.zip`). ScreenScraper's ROM index knows them, so a scrape finds them, but the panel only searched titles (`jeuRecherche.php`), which can't find `3kokushi`, and nor can IGDB or SteamGridDB. A short name → title list (ES-DE ships one) would also fix unscraped games' titles and the other providers' searches; it's deferred until the saved replies show it's needed. |
| 2026-10-02 | **A game's metadata has its own screen, on Y** (or I), with all of it, its whole description, and its images and video, each shown full size (or played) with A; the overlay keeps a game's title, system and "Favourite", and a system's details as before. **The favourite moves to L3** (or F). Y stays the settings lists' second action, so on the keyboard that's I now, not F. | The owner's request. The overlay had room for 9 fields and 4 lines of description over the grid, so it cut both; a screen of its own shows everything and the art at full size. Opening it on the settings layer gives it the pad, mouse and keyboard handling of the other panels; the viewer is a full-screen panel on the same stack, so B always goes back one step. F follows the favourite (F for favourite), and I is free. Dropping the play-history query from the focus's details makes resting the focus cheaper. Benches before and after in one session: scroll p99 21.22–21.33 ms before, 21.19–21.51 ms after; main-thread allocation 96 B both; start-up of our code 393 and 387 ms (medians of 3). |
| 2026-10-02 | **Videos are decoded by Media Foundation through Core (`IVideoDecoder`), with raw COM calls as WIC is, and played by the app's own `VideoPlayback`**, timed by the sound. No package. A 4:4:4 H.264 video (Windows can't decode the profile) says why it can't play. | Godot 4.7 plays only Ogg Theora, and scraped videos are MP4 (H.264 and AAC). Media Foundation ships with Windows and needs no package or native binaries; a GDExtension around FFmpeg would play everything, 4:4:4 included, but adds native code and its licence, which is the owner's call. Timing by the sound played keeps the picture in step with it, and holds the picture when decoding falls behind. Decoding the owner's scraped videos: 30 s of 360×480 in about 1.5 s on one thread; 15 of 72 are 4:4:4. |
| 2026-10-02 | **An arcade cabinet template, and a logo drawn whole in any slot.** The built-in theme's `arcade_cabinet` (the top half of an upright cabinet: the `screenshot` slot on its monitor, the `label` slot on its marquee with `["logo", "generated"]`) is the arcade systems' template, replacing the DVD and jewel cases. A slot that resolves to the `logo` kind now draws it whole over its fallback, upright unless it's a spine (A7 Art drawn whole). The cabinet's plain colours come from a palette texture on its one `case` material. | The owner's request, from a 2D mock-up. A cropped logo was cut off and showed its transparent parts as whatever colour they hid, so the marquee needed the spine's treatment; the sample TV's plate gets it too. A palette keeps the model at three materials (four is the budget) and the built-in convention of `case` as the only plain material, and its colours are sRGB pixels, with no doubt about colour space. Benches: [perf/arcade-cabinet.md](perf/arcade-cabinet.md); the cost to watch is 16 MB of texture arrays for the two extra slot channels in every games grid (`SlotLayout` is per theme, not per system). |
| 2026-10-02 | **A template can fit a slot's art whole (`[templates.<id>.fit]`, `"crop"` or `"whole"`), and the arcade cabinet fits its screen whole.** Its screen is bigger (568 × 426 mm in the same cabinet) and matte, and its side panels end inside the control panel. | The owner's requests: a vertical game's screenshot was cropped to its middle on the 4:3 screen, the bezel was wider than it needed to be, and grey bars flickered beside the control panel (its side panels' edges, coplanar with the panel's front and a few millimetres above its top). Fitting is per template and slot, not per media kind, since a box's back showing a screenshot should still be filled. It uses the shader branch logos already had. Screenshots are fitted at their image's proportions, so one saved at an arcade board's native, non-square-pixel resolution looks a little wide; snapping to the monitor's 4:3 or 3:4 would be another option. Benches: [perf/arcade-cabinet.md](perf/arcade-cabinet.md). |
| 2026-10-02 | **Layouts: systems as a grid, a carousel or one at a time; games as a grid, a carousel or a list** (`[display] systems_layout` and `games_layout`), with each grid's columns and rows automatic or set (`systems_columns`, `systems_rows`, `games_columns`, `games_rows`; 1–9 and 1–6), and a system's own games layout and grid size (`games_layout`, `games_columns`, `games_rows` in systems.toml; unset follows `[display]`). They're one `ItemGrid` with four shapes (A1 Grid), not grids of their own; the list's titles are 2D labels in the overlay that follow the games grid's scroll. Set rows fit between the overlay's heading and its details. The settings' Look section has a Layout page, and a system's page its own view, columns and rows. `--layout` overrides them for a run, and the bench report says which were used. | The owner's request. One grid keeps the MultiMesh batching, the pool, streaming, per-game models, clips and the focus effects for every layout, so no layout costs more per frame than the grid (a carousel moves its bound cells while it scrolls, about a dozen transforms). Rows counted against the whole view put a set row under the details (2 rows showed one and a half); a system's bad size is a warning, as display taste shouldn't disable a system. The pool stays at 64 cells, its texture memory unchanged, so 9 columns of tall boxes give up a column rather than grow it. Benches: [perf/layouts.md](perf/layouts.md). |
| 2026-10-02 | **A release carries ScreenScraper's developer credentials** (A5, "Secrets"): the release workflow writes them, XORed, into a gitignored `BuiltInAccounts.Release.g.cs` from the repository's secrets. Users enter only their own account: a release neither lists developer credentials nor reads any from `secrets.toml` or the environment. Builds from source have none, and ask for them. | The owner asked for it: developer credentials are issued for the software, not for each user, and a user shouldn't be offered them. If ScreenScraper revokes the built-in pair, only a new release fixes it. Nothing in a client can be kept from someone determined (every request carries them), so the aim is only to keep them out of the repo and out of plain text; ScreenScraper can revoke them. |
