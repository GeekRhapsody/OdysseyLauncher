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
  godot/                     project.godot, OdysseyLauncher.csproj (-> Launcher.Core), src/, scenes/, shaders/, assets/, themes/
  tools/verify.ps1           build, test, Godot headless build/import/smoke run
  docs/  CLAUDE.md
```

### Launcher.Core (namespace `Launcher.Core.*`)

| Namespace | Responsibility |
|---|---|
| `Config` | `ConfigLoader` loads TOML (Tomlyn), layering user files over built-in defaults (embedded resources). <br>Maps Tomlyn's syntax tree by hand into a tree that keeps every key's position, so diagnostics still point at the right file after merging (M2). <br>Merges recursively; scalars and arrays are replaced. <br>Validates, with file:line:column:key diagnostics; unknown keys get a "did you mean" warning. <br>Parsers take text plus a source name, so the app can feed `res://` files from the PCK. <br>From M7, writes go through Tomlyn's syntax tree, so comments survive. |
| `Data` | `LibraryDatabase` and `UserDatabase` (create, migrate, back up), `MigrationRunner`, and the connection helpers. <br>**Microsoft.Data.Sqlite's async API is synchronous**, so reads run on the thread pool, and writes go through one dedicated writer thread (`DbWriter`). <br>Readers come from our own pool (`ReaderPool`), not Microsoft.Data.Sqlite's: each has `userdata.db` ATTACHed once and is `query_only`, and the pool can be closed and held back while a rebuilt library file is swapped in. <br>Every connection sets WAL, `foreign_keys=ON`, `synchronous=NORMAL` and `busy_timeout`. |
| `Scanning` | `RomScanner` walks a system's ROM folders by file name (extensions, recursion, excludes). Several folders per system are allowed; the first folder wins a `path_key` collision. <br>Folders are listed with a 256 KB buffer, and `LibraryService` scans 8 systems at once on dedicated threads, because a network share costs a round trip per listing refill. Excluded folders (by default ES-DE's `images`, `manuals` and `videos`) aren't listed at all. <br>Multi-file games: files referenced by an `.m3u`, `.cue` or `.gdi` are hidden. Parsed playlists are cached in `library.db` by size and mtime, so a rescan doesn't re-read them. <br>`TitleParser` turns No-Intro and Redump names into a display title and a sort key, keeping region, languages, revision, disc and other tags as separate fields. <br>Normalises paths to `rel_path` and `path_key`. <br>From M5, `UserMedia` also indexes the user's own art, `ConfigDir/media/<system>/<kind>/<rel path>.<ext>` (PNG, JPEG or WebP), into `media` with source `user`: a file matches the game with the same `path_key`, or every game whose `path_key` is its name plus an extension. Each file's size and time are stored (migration 0002), so a rescan reads only new or changed headers. Model overrides are M6's. |
| `Scraping` | (M4) `IScraper` for ScreenScraper, IGDB and SteamGridDB, each with a capability map (the fields and media kinds it can supply). <br>`ScrapeService`: scrape a game, a system, or everything missing, and clear a game, as operations with progress events (raised on worker threads). They go through a persistent queue in `userdata.db` (resumed after the app closes; single games jump ahead; cancellable), and games run concurrently within each provider's limits. <br>`ProviderGate` bounds each provider's requests in flight, per second and per minute, and holds them during a rate-limit pause or after a used-up quota; `ScraperHttp` retries rate limits and transient failures with exponential backoff, honouring Retry-After. <br>Provider selection: `[scraping] provider` first, then each `fallback` in order, asked only for what's still missing and what its capability map has; a provider with no credentials is skipped and reported. <br>`ProviderAccounts` reads credentials from `secrets.toml` and `ODYSSEY_*` variables. <br>Match resolution (A2), and the saved responses in `scraped/responses/` (credentials redacted), from which `ScrapedRestore` rebuilds a game's scraped data offline when a scan adds it. |
| `Media` | (M4) `MediaStore`: scraped media at deterministic paths (`scraped/media/...`), written atomically (a temporary file, then a replacing move), with the image checked by its first bytes. <br>`Bc7Encoder` (modes 6 and 1) and `Bc7DdsWriter` make the derivative; `DerivativeBaker` decodes (`IImageDecoder`), squeezes to 512² and encodes; `DerivativeService` bakes on its own below-normal thread, and `BakeMissingAsync` bakes every cover without a derivative and deletes stale ones. <br>From M5: `ImageHeaders` reads a PNG, JPEG or WebP's size from its header only; `TextureDerivatives` names each baked derivative (`CacheDir/textures/<key>.dds`, the key a SHA-256 of the source's root, path, size and time), allocation-light so texture workers can call it per cover; `MediaKinds` lists the kinds. |
| `Models` | `ModelInspector` validates a `.glb` against the A7 spec by reading only the GLB JSON chunk and the image headers. It has no Godot dependency. |
| `Launching` | `LaunchPlanner` is pure and static: it picks the emulator (this launch's choice, then the game's override, then the system's) and expands its templates into a final argument list (A5). A named emulator that isn't configured is an error, never a silent fallback. <br>`LaunchService` checks the ROM, executable, core and working folder exist, runs the plan through `IProcessRunner`, and records the play session through `IPlayHistory`. One game at a time. <br>Events, raised on worker threads: `Starting`, `Running` (process id), then exactly one of `Exited` (exit code, duration) or `Failed` (a reason written for the user). A non-zero exit within 5 s is `Failed`, and isn't counted as a play. Cancelling ends the game's whole process tree. (M3) |
| `Library` | `LibraryService`, the façade the app uses: systems summary (boot), games list (on entry), the Favourites and Recently played lists, favourites and overrides, and rescan and rebuild jobs with progress, and metadata overrides (M4; scrape jobs are `ScrapeService`'s). Scans and rebuilds run one at a time; each writes in one transaction. |
| `Platform` | The only OS-specific code. <br>Interfaces: `IPlatformPaths`, `IProcessRunner`, `IWindowFocus`; `PlatformServices` picks the implementations. <br>**Windows** (`Platform/Windows`, `LibraryImport` to kernel32 and user32): <br>- `WindowsProcessRunner` creates the emulator inside a new job object (`PROC_THREAD_ATTRIBUTE_JOB_LIST`) with `CreateProcessW`, and the game has ended when the job has no processes, so stub launchers are followed. A dedicated thread waits on the job's completion port, and also asks the job every second, because Windows doesn't guarantee job messages. The job doesn't kill the game if the launcher dies, allows explicit breakaway, and no handles are inherited. <br>- `WindowsCommandLine` quotes each argument by the C runtime's rules, since Windows passes one UTF-16 string. <br>- `WindowsWindowFocus`: see Platform glue below. <br>- `WicImageDecoder` (M4) decodes PNG, JPEG and WebP and scales them with the Windows Imaging Component, through raw COM vtable calls (no interop package). <br>**Linux stub:** `PortableProcessRunner` (`Process` with `ArgumentList`; follows the started process only) and `NullWindowFocus`; no image decoder yet, so no derivatives. |
| `Diagnostics` | Debug-argument parser, `StartupTimeline`, `FrameTimeStats`, `BenchReport` (System.Text.Json source generation), a minimal `ILog`, and `Redactor` (M4), which masks every known credential (as written, URL-encoded and JSON-escaped) and the value of any credential-bearing URL parameter or bearer header. |

Every `await` in Core uses `ConfigureAwait(false)`. Analyser rule CA2007 is an error in `src/`.

### Godot app (`godot/src`, namespace `Launcher.App.*`)

| Area | Responsibility |
|---|---|
| `Boot` | Main scene (M5). `AppServices` loads config and opens the library on the thread pool, while the main thread builds the look, the cover array and the grids, and Godot's loader threads load the built-in models. When both are done the systems grid is bound; its first drawn frame is `interactive`. A warm-up follows, one step a frame: the launch controller, then glyphs. Systems never scanned are scanned in the background after it, and then covers without a derivative are baked (M4; also after F5). `MainThreadQueue` carries every background result to the main thread within 3 ms a frame. |
| `Screens` | `Navigator` (M5): Systems → Games → Launching → back. Transitions move the two grids in depth, scale them and fade them into the background, staggered so the opaque grids barely overlap. The last focused game is remembered per system, and the last 3 game lists are cached. Favourites and Recently played are cards in the systems grid, mixing templates. Details (the `metadata` fields, file-name tags and play history) are queried and formatted on the thread pool 0.12 s after the focus rests, so held moves don't query. `InfoOverlay` is the PS2-style text: the title with a soft glow top left, what it belongs to under it, details bottom left and controls bottom right. |
| `Navigation` | `NavInput` (M5) polls `nav_*` actions each frame rather than using `_Input`, which allocates per event: arrows, Enter/Space, Escape/Backspace, Page Up/Down, Home/End, `[` `]`, F and F5; the D-pad, left stick, A/B/Y, shoulders (page), triggers (letter) and View (rescan). A held move repeats after 0.32 s, then speeds up from every 120 ms to every 35 ms over 1.4 s. Input is dropped while `LaunchController.IsInputBlocked`, and a button still held when that ends doesn't count. |
| `Grid` | `ItemGrid` (M5), a virtualised 3D grid. <br>A cell pool (at most 64 for games) covers the visible rows plus spare rows, most of them ahead of the scroll, and cells are re-bound rather than recreated. <br>Template items are drawn as **one `MultiMesh` per template**, all with one material. Each pool cell has a fixed instance in every template's MultiMesh (hidden where unused), a fixed `Texture2DArray` layer and a fixed place in the title atlas. `INSTANCE_CUSTOM` = (layer + fade × 0.999, the plain colour packed as a 24-bit integer, idle phase or −1 when focused, the art's aspect or 0): Godot 4 multiplies a MultiMesh's instance colour into `COLOR`, which carries material data here. <br>Per-game custom `.glb` models (M6) use per-node instances bound to the same cells. <br>**The items never move to scroll: the grid's root does** (one transform), as the camera would, so a frame only touches newly bound rows, the focused items and fading covers. Two grids (systems and games) each have their own root. <br>Items are sized so 3.2 rows of games fit (2.7 of systems), unless that leaves fewer than 5 columns. A single part-filled row is centred. <br>`TitleAtlas`, a SubViewport of labels, draws each cell's title as a square block and a spine strip; it redraws only in a frame where a title changed. <br>**One update drives every item**, called by the main scene each frame. <br>A cell's texture request is superseded when it's re-bound, so late results are dropped. <br>Critically damped scrolling, the focused row always on the focus line, a little above the middle. |
| `Models` | `TemplateLibrary` (M5) loads the built-in models and merges each into one surface for the item shader: per vertex, `COLOR` is the material's base colour (linear) and roughness, and `UV2` the face id (cover, back, spine, case, label, from the material's name) and the face's aspect (`extras.aspect`, or the slot mesh's bounds). <br>Later (M6): resolves each item's model (order in A7), converts each user `.glb` once into a cached native scene, and plays idle, focused and launch clips. The procedural fallbacks are in the grid: lift, scale and sway when focused; bob when not; spin up and fly forward to launch. |
| `Textures` | `TextureStreamer` (M5): prioritised, cancellable requests (one per pool cell); 2 dedicated decode workers; mandatory baked derivatives (BC7 DDS, 512² with mips); the pool's `Texture2DArray` created at boot and only updated while browsing; a per-frame budget of 4 MB and 8 uploads; pooled `Image`s; and an opaque placeholder-to-cover fade in the shader. A missing derivative shows the box as it looks with no art. The LRU cache and the focused item's full-resolution upgrade are later (M6). |
| `Theming` | `Look`: the four-corner gradient on a background canvas layer (`Environment` background mode Canvas), three `DirectionalLight3D` children of the camera, and an ambient colour. The item shader gets the corners too, to fade items into the background. M5 uses the default look; theme loading and cross-fades between per-system looks are M6's. |
| `Diagnostics` | `DebugHooks` autoload (`--capture`, `--bench`), timeline marks, and a log sink that writes to Godot's output and a file. `ScrollBench` (M5) drives `--bench-scenario=scroll`. |
| `Tools` | `BoxTemplateGenerator` (M5), a `[Tool]` node that builds the built-in models (A7) procedurally and exports them with `GLTFDocument`. |
| Platform glue | A main-thread queue with a per-frame time budget. <br>`Launching/LaunchController` (M3), built on first use, not at boot. `LaunchService` events reach it through `CallDeferred`. <br>- **Starting:** `RenderLoopEnabled = false`, low-processor mode with `Engine.MaxFps = 10`, the tree paused (no animation or processing), the master bus muted, and input swallowed. From M5, textures are evicted too. <br>- **Running:** `IWindowFocus.BeforeLaunch` lets any process take the foreground (`AllowSetForegroundWindow(ASFW_ANY)`, withdrawn by Windows at the next keyboard or mouse input), because a stub launcher's real emulator is a grandchild. A 4 Hz timer waits until another process's window is in front (or 10 s), then minimises the launcher with `SW_SHOWMINNOACTIVE`, so nothing unrelated is activated in between. <br>- **Exited or Failed:** game mode is undone, then `AfterExit` restores the window and takes the foreground: restore and `SetForegroundWindow`; then the same with the foreground window's input queue attached; then with a synthetic Alt key held (Windows lifts its lock after keyboard input); otherwise the taskbar button flashes. System settings (the foreground lock timeout) are never changed. Input stays swallowed until 500 ms after focus returns, so the button that quit the emulator doesn't act in the launcher. <br>- Input processing is on only while input is swallowed: an always-on `_Input` allocated about 1.9 KB per frame, because the Deck sends joypad motion all the time ([perf/m3-launching.md](perf/m3-launching.md)). The navigator also drops its input while `IsInputBlocked`. <br>- From M5 the controller is built in the warm-up after `interactive`, takes the shared `AppServices`, and raises `GameModeEntered` and `GameModeLeft`: the cover array is freed while a game runs and recreated afterwards, and the bound covers re-requested. |

## A2. Key interfaces (sketch)

```csharp
// Launcher.Core.Platform
public interface IPlatformPaths {
    string ConfigDir { get; }   // settings/systems/emulators/secrets .toml, themes/, models/, media/ (user overrides)
    string DataDir { get; }     // library.db, userdata.db, media/, scraped/, logs/
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
public readonly record struct ProcessOutcome(int ExitCode, TimeSpan Elapsed, bool Terminated);
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
public readonly record struct GameRow(long GameId, string Title, string? CoverPath, MediaRoot CoverRoot, bool IsFavourite);  // only what a cell draws
public interface ILibrary {
    Task<IReadOnlyList<SystemSummary>> GetSystemsAsync(CancellationToken ct);   // boot: one small indexed query
    Task<GameList> GetGamesAsync(string systemId, CancellationToken ct);        // entry: compact, pre-sorted rows
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

// Launcher.Core.Scraping (M4)
public interface IScraper {                                                     // thread-safe; bounds its own requests
    string Id { get; }                                                          // "screenscraper" | "igdb" | "steamgriddb"
    ScraperCapabilities Capabilities { get; }                                   // the fields and media kinds it can supply
    string? Unavailable { get; }                                                // null, or why not (missing credentials, and where to put them)
    string? Unsupported(SystemConfig system);                                   // e.g. no screenscraper_id / igdb_platforms
    int MaxConcurrency { get; }
    Task PrepareAsync(CancellationToken ct);                                    // once per run: account limits (ScreenScraper)
    Task<ProviderResult> LookupAsync(ScrapeQuery query, CancellationToken ct);  // by file (name, size, hashes) or a title search
    Task<ProviderResult> FetchAsync(string providerGameId, ScrapeQuery query, CancellationToken ct);  // a stored or manual match
    Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(string title, SystemConfig system, CancellationToken ct);  // for manual matching (M7)
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
    Task<IReadOnlyList<ScrapeBatchResult>> ResumeAsync(CancellationToken ct);   // batches a stopped run left unfinished
    Task CancelBatchAsync(long batchId);                                        // cancelling a call's token does this too
    Task<ClearResult> ClearGameAsync(GameKey game, CancellationToken ct);
    DerivativeService Derivatives { get; }
}

// Launcher.Core.Media (M4)
public sealed class MediaStore {
    static string RelativePathFor(GameKey game, string kind, string extension); // scraped/media/<system>/<kind>/<path_key><ext>
    Task<StoredMedia> SaveAsync(GameKey game, string kind, ReadOnlyMemory<byte> content, CancellationToken ct);  // atomic; sniffs the format
}
public interface IImageDecoder {                                                // the OS's codecs; Windows: WIC
    bool TryDecodeScaled(string path, int width, int height, Span<byte> rgba, out string? error);
}

// Launcher.Core.Launching
public sealed record LaunchPlan(string EmulatorId, string EmulatorName, string Executable,
    IReadOnlyList<string> Arguments, string WorkingDirectory, string? Core);    // arguments final and unquoted
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

// Launcher.App.Textures (Godot side), as built in M5: a class, not an interface
public sealed class TextureStreamer {
    Texture2DArray CreateArray();                                                  // at boot: one layer per pool slot
    void Request(int slot, int row, MediaRoot root, string relPath, long sizeBytes, long mtimeMs);   // supersedes the slot's last request
    void Cancel(int slot);
    void SetView(float centreRow, float direction);                                // priorities: nearest first, ahead of the scroll
    void PumpUploads(ITextureSink sink, long budgetBytes, int cap);               // main thread, once per frame
    void Evict();                                                                   // while a game runs
}
public interface ITextureSink { void OnLayerReady(int slot); void OnLayerMissing(int slot); }
```

**Match resolution for scraping (per game, per scraper):**
1. A manual match in `userdata.db`.
2. Otherwise, the match stored in `library.db` (if the provider no longer has that game, it's looked up again).
3. Otherwise, a lookup: ScreenScraper by file name, size and system id, plus CRC32, MD5 and SHA-1 for files up to `hash_limit_mb` (ScreenScraper asks for a hash); if that finds nothing, a title search. IGDB and SteamGridDB can only search by title. A search hit counts only if its name matches the ROM's cleaned title (`TitleMatcher`, similarity ≥ 0.85, case-, accent-, punctuation- and article-blind).

Once matched, re-scrapes use `FetchAsync(id)` and never search again; the stored method (`filename`, `hash`, `search`, `manual`) is kept. Saved responses carry the matched id and method, so a rebuild recovers automatic matches offline, and manual corrections always win.

**Provider selection (M4).** Each game is scraped by `[scraping] provider` first. Each `fallback` provider, in order, is then asked only if its capability map has a field or media kind still missing, and it fills only those: every field comes from the first provider that has it. Media: each wanted kind (less the kinds the user has their own art for) is downloaded from the first provider that offers it, falling through to the next if a download fails. Capabilities: ScreenScraper has every field and every kind; IGDB every field, the cover, a screenshot and artwork (as the hero); SteamGridDB the cover (community capsule art), hero and logo, and no metadata. Only ScreenScraper has back, spine and box texture.

**Scrape status.** A game is `ok` (found, nothing failed), `partial` (found, but a provider failed or was resting), `not_found` or `error` (nothing found; something failed); no `scrape_state` row means never scraped. "Scrape all missing" takes games never scraped, `not_found` or `error`, plus every game without a cover row.

**Limits and failures.** Each provider's `ProviderGate` holds its requests in flight (ScreenScraper: the account's `maxthreads`; IGDB 4 of its 8; SteamGridDB 2), its rate (IGDB 4 a second; SteamGridDB 4 a second; ScreenScraper the account's `maxrequestspermin`) and pauses. A 429 or 5xx is retried up to 5 times with exponential backoff (2 s doubling, jitter, capped at 2 minutes; Retry-After honoured), pausing the whole gate on a 429. A used-up quota (ScreenScraper 430, 431, or its reported counters) rests the provider until ScreenScraper's midnight (French time), and refused credentials until the app restarts; the gate refuses queued requests at once, games carry on with the other providers and are marked `partial`, and a `ProviderNotice` says why.

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
2. Settings, theme and systems config, in about 10 ms. M1 measures Tomlyn's first-use cost.
3. Open `library.db` read-only and run `SELECT system_id, game_count FROM systems`, in about 5 ms.
4. System models: built-ins are Godot-imported, and user models come from the converted-scene cache, behind proxies.
5. First frame, then the `interactive` mark.

Everything else waits until after `interactive`, and nothing is scanned at boot. The boot splash is off, with the theme's colour behind it.

**Entering a system:**
- One indexed query on the thread pool: games joined to their effective `cover`, with `userdata.db` ATTACHed for favourites and overrides.
- Results reach nodes through the budgeted main-thread queue, **not** through plain `await` continuations. Godot's `SynchronizationContext` runs every pending continuation each frame, with no budget.
- Only the visible cells are bound.

**Texture streaming:**
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
  - The budget is **4 MB per frame**; BC7 only reaches it in the first frames. Add a cap of at most 8 uploads per frame (proposed, untested), because a few M1 hitch frames followed a burst of uploads.
  - Warm the first upload at boot, while the DB opens (M5), because the first one takes up to 43 ms.
  - Godot's upload staging buffer is capped at 16 MB (`rendering_device/staging_buffer/max_size_mb`; the default is 128). At 2560×1440 the default grew the working set past 512 MB ([perf/m5-navigation.md](perf/m5-navigation.md)).
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
- The placeholder-to-cover fade happens **inside one opaque cover shader**, through a per-instance `fade` parameter. There's no alpha blending and no extra variant.
- User `.glb` materials are remapped onto the fixed shader set.
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
- Later (M6): runtime `.glb` conversion on a worker thread.
- Partly done (M2): a net10.0 comparison build. For Core it's no faster (full scan 304 ms against 274 ms). The Godot-side comparison is later (M5). Adopting it needs the owner's approval.
- Later: PresentMon, to explain the periodic present delay and M5's frame-pacing jitter (p99 about 21 ms with or without the grid), if the owner is happy to install it.

## A4. Storage

| Location | Windows default | Contents |
|---|---|---|
| ConfigDir | `%APPDATA%\OdysseyLauncher` | `settings.toml`, `systems.toml`, `emulators.toml`, `secrets.toml`, `themes/<id>/`, `models/{systems,templates,games}/`, `media/<system>/<kind>/<rel path>.<ext>` (user art, indexed from M5) |
| DataDir | `%LOCALAPPDATA%\OdysseyLauncher` | `library.db`, `userdata.db` (plus the last 3 backups), `scraped/media/<system>/<kind>/<path_key>.<ext>` (full size, as downloaded), `scraped/responses/<provider>/<system>/<path_key>.json`, `tokens/igdb.json` (IGDB's cached access token), `logs/` |
| CacheDir | `%LOCALAPPDATA%\OdysseyLauncher\cache` | `textures/` (derivatives), `models/` (converted `.glb`) |

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
- **Stored paths:** app-written files are named by `path_key`. The DB stores paths relative to their root, never absolute paths.
- **Rebuildable:** `library.db` is a pure function of config, the ROM folders, `media/`, `scraped/`, and the user's model and media override folders.
  - A rebuild writes a new file offline (`library.db.rebuild`, in rollback-journal mode so it's one self-contained file), then closes every connection and swaps it in with a replacing move.
  - A golden test checks that a rebuild equals the incrementally built DB, ids and timestamps excluded.
- **Missing folders:** a scan of a folder that no longer exists (an unplugged drive) removes its games from `library.db`; their user data stays (see Orphans).
- **Multi-file games:** an `.m3u` hides the discs it lists, a `.cue` its `FILE` tracks, and a `.gdi` its track files, so the playlist is the one game. References resolve against the playlist's folder, match by `path_key`, and can't point outside the ROM folder. A playlist over 256 KB isn't read. Disc systems' default extensions leave out `.bin`, so stray tracks never show.
- **Titles:** `TitleParser` peels trailing `(...)` and `[...]` groups off the file name. The first all-region group is the region, the first language list (`En,Fr,De`) is the languages, and the first `Rev`/`v` and `Disc` tags are the revision and disc. Everything else is kept, as written, in `tags`. A trailing article moves to the front (`Legend of Zelda, The` → `The Legend of Zelda`), and a lone disc keeps " (Disc n)" in its title. The sort key is lower-case and accent-free, drops a leading The/A/An, sorts numbers naturally, and puts a game's discs right after it.
- **Back up:** ConfigDir and `userdata.db`, plus `scraped/` to avoid a re-scrape.
- **Scraped files (M4)** live under `scraped/`, not DataDir's own `media/`: in the portable layout ConfigDir and DataDir are one folder, and `media/` there is the user's own art.
- **Orphans:** when a file disappears, its `userdata.db` rows are kept, so moving a ROM out and back loses nothing.

### `library.db` (schema version 3, `PRAGMA user_version = 3`)

The shipped files are `src/Launcher.Core/Data/Migrations/Library/0001_initial.sql`, `0002_media_file_stamps.sql` (M5: `media.size_bytes` and `mtime_ms`, the indexed file's size and time, so an unchanged file's header isn't read again, and so the grid can name its derivative without touching it; scraped media rows have them too), and `0003_scraping.sql` (M4: `metadata.title`, the scraped title, and `scrape_state`, below). This copy is version 1, for reading.

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

**Restoring scraped data (M4).** When a scan adds a game (after a rebuild, a recreated library, or a ROM moved back), its saved responses are read back offline: each provider's parser turns its response into a game, the results merge in config order as a live scrape does, matches return with their method, and media rows point at the files in `scraped/media/` that still exist (the user's own art keeps its rows).

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
  scraper          TEXT NOT NULL,             -- 'screenscraper' | 'steamgriddb'
  scraper_game_id  TEXT NOT NULL,
  method           TEXT NOT NULL,             -- 'filename' | 'hash' | 'manual'
  matched_at       INTEGER NOT NULL,
  PRIMARY KEY (game_id, scraper)
) STRICT;

CREATE TABLE media (                          -- one row per kind: the effective file (user override beats scraped)
  game_id  INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  kind     TEXT NOT NULL,                     -- cover | back | spine | box_texture | label | screenshot | logo | hero | model
  path     TEXT NOT NULL,                     -- relative to the root named by source
  width INTEGER, height INTEGER,
  source   TEXT NOT NULL,                     -- 'screenscraper' | 'steamgriddb' (DataDir/media) | 'user' (ConfigDir)
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

### `userdata.db` (schema version 2)

This DB can't be rebuilt. It's keyed by `(system_id, path_key)`, never by `library.db` ids. The shipped files are `Data/Migrations/User/0001_initial.sql` and `0002_scraping.sql` (M4):

```sql
-- 0002 (M4): the user's metadata overrides, which scraping never writes (NULL = the scraped value)
ALTER TABLE game_overrides ADD COLUMN description TEXT;  -- and release_date, developer, publisher, genre, players (TEXT), rating (REAL)
-- The scrape queue: a batch survives the app closing. Jobs are deleted as they finish; a batch keeps its counts.
CREATE TABLE scrape_batches (batch_id INTEGER PRIMARY KEY, kind TEXT NOT NULL,   -- 'game' | 'system' | 'missing'
                             target TEXT, priority INTEGER NOT NULL,             -- single games (0) before batches (1)
                             total INTEGER NOT NULL, done INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
                             created_at INTEGER NOT NULL, finished_at INTEGER,   -- NULL = resume it
                             cancelled INTEGER NOT NULL DEFAULT 0) STRICT;
CREATE TABLE scrape_jobs    (batch_id INTEGER NOT NULL REFERENCES scrape_batches(batch_id) ON DELETE CASCADE,
                             seq INTEGER NOT NULL, system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             PRIMARY KEY (batch_id, seq)) STRICT, WITHOUT ROWID;
```

**Clearing a game (M4)** deletes its scraped metadata, scrape state and log, every match (manual ones too), every media row, the title and metadata overrides, the scraped files and their derivatives, its saved responses, and the user's own art files for it, except a file another game also uses (matched by stem). The title goes back to the file name. Favourite, play history, emulator override and hidden stay.

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
                             scraper_game_id TEXT NOT NULL, matched_at INTEGER NOT NULL,
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

[scraping]
provider = "screenscraper"           # asked first for every game
fallback = ["igdb", "steamgriddb"]   # then these, in order, for what's still missing
regions = ["eu", "wor", "us", "jp"]  # ScreenScraper region codes; first available wins (IGDB's release regions map from them)
languages = ["en"]
media = ["cover", "box_texture"]     # also: back, spine, screenshot, logo, hero
hash_limit_mb = 64                   # ROMs up to this size are hashed for ScreenScraper; 0 = none
```

### System definition

Built-in definitions ship in `Launcher.Core/Defaults/systems.toml`: Game Boy, Game Boy Color, Game Boy Advance, NES, SNES, N64, GameCube, Master System, Mega Drive, Saturn, Dreamcast, PlayStation, PlayStation 2 and PSP. The user's `ConfigDir/systems.toml` holds only what changes.

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
game_model = "clamshell"             # built-in box template id; default "dvd_case"
screenscraper_id = 1
igdb_platforms = [29]                # IGDB platform ids; NES and SNES add their Japanese twins (99, 58)

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
```

- A game launches with, in order: an emulator chosen for that launch, the game's own override (`game_overrides.emulator` in `userdata.db`), or the system's `emulator`. Any configured profile can be chosen, not only the system's `alt_emulators`. An override naming a profile that's gone is a launch error that says where it was named.
- The built-in RetroArch core file names and `pcsx2-qt.exe` were checked against a RetroBat install (2026-09-28). The flags follow each emulator's documentation; a launch with each real emulator is still to do (M3 log).

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
- **Installs are checked at load (M3).** For every emulator an enabled system uses (as its `emulator` or in `alt_emulators`), a missing `executable`, or else a missing `core`, is a **warning** that names the systems affected: `emulators.retroarch-genesis-plus-gx.executable: the executable 'C:\RetroArch-Win64\retroarch.exe' doesn't exist, so Master System (mastersystem) and Mega Drive (megadrive) can't launch games (it's their emulator)...`. The systems stay enabled, so an unplugged drive doesn't empty the library, and launching reports the same problem. Emulators no system uses aren't checked, and each path is checked once. `ConfigSources.FileExists = null` turns the check off.
- A `core` that no `args` entry uses as `{core}` is a warning.
- Every diagnostic has the file, line, column and dotted key: `user/systems.toml:3:1: error: systems.megadrive.emulator: unknown emulator 'blastemm' (did you mean 'blastem'?)`. Values from the defaults point at `built-in/<file>`.

### Secrets

ScreenScraper account and developer credentials, the SteamGridDB API key and the IGDB (Twitch application) client id and secret live only in `ConfigDir/secrets.toml` or in `ODYSSEY_*` environment variables, which override the file value by value (M4, `ProviderAccounts`):

```toml
[screenscraper]      # ODYSSEY_SCREENSCRAPER_DEV_ID, _DEV_PASSWORD, _USERNAME, _PASSWORD
dev_id = "..."       # developer credentials, issued by ScreenScraper (on its forum) for this software
dev_password = "..."
username = "..."     # the user's account; optional (anonymous limits otherwise)
password = "..."

[steamgriddb]        # ODYSSEY_STEAMGRIDDB_API_KEY
api_key = "..."

[igdb]               # ODYSSEY_IGDB_CLIENT_ID, ODYSSEY_IGDB_CLIENT_SECRET
client_id = "..."
client_secret = "..."
```

- A provider without its credentials is skipped, and the message says which keys or variables to set and where. Diagnostics about the file never quote a value, and a syntax error shows only its position.
- ScreenScraper embeds the credentials in every URL, and echoes them back in each response (`header.commandRequested`, every media URL). `Redactor` masks them in saved responses and logs; a test scans every file the scrape writes, and the log, for every credential.
- IGDB's app access token (about 60 days, and a Twitch application may only have 25) is cached in `DataDir/tokens/igdb.json`, keyed by a hash of the client id, and replaced a day before expiry or when IGDB refuses it. The client secret travels in a form body, never a URL.

## A6. Theme manifest (`themes/<id>/theme.toml`)

```toml
format = 1
name = "Memory Card"
author = "Odyssey Launcher"
look_transition_ms = 300

[look.background]                    # icon.sys-style: one sRGB colour per screen corner
top_left     = "#1B1F4A"
top_right    = "#1B1F4A"
bottom_left  = "#04040C"
bottom_right = "#0B0B24"

[look.ambient]
colour = "#303038"
energy = 1.0

[[look.lights]]                      # 1-3 directional lights, as in icon.sys
direction = [-0.5, -0.4, -0.75]      # direction the light travels, in view space: +X right, +Y up, +Z towards the viewer
colour = "#FFFFFF"
energy = 1.0

[[look.lights]]
direction = [0.7, -0.2, -0.6]
colour = "#8090FF"
energy = 0.5

[[look.lights]]
direction = [0.0, 0.9, -0.4]
colour = "#FF9060"
energy = 0.25

[systems.saturn.look.background]     # per-system look, used while that system's games are shown
top_left = "#2A1A3A"
top_right = "#2A1A3A"
bottom_left = "#050008"
bottom_right = "#100818"
```

- **Colours:** `#RRGGBB` sRGB. `energy` is a linear multiplier.
- **Background:**
  - The four corners interpolate in sRGB, as on the PS2.
  - The gradient is drawn on a background canvas layer rather than a sky, which avoids radiance-map and cubemap-pass problems and makes cross-fades free.
  - With the Linear tonemapper, glow off and ambient source Colour, each corner pixel renders as its exact hex value. The scaffold capture confirms this: all four corners match with a delta of 0.
  - Reflections are disabled.
- **Lights:**
  - Directions are in **view space**, as in icon.sys, so the three `DirectionalLight3D`s are children of the camera.
  - Any non-zero direction is valid, including straight up and down.
  - Lights the theme doesn't define are switched off.
- **Per-system looks:**
  - Entering a system cross-fades to its look.
  - A per-system `background`, `ambient` or `lights` block **replaces** the default block whole. A background needs all four corners.
  - Anything left unspecified falls back to the default look.
- **Theme models:** a theme can ship `models/systems/<system>.glb` and `models/templates/<system>.glb`.
- **Locations:** built-in themes live in `res://themes/`, and user themes in `ConfigDir/themes/`. A user theme with the same id replaces the built-in one.
- **Later:** a `[ui]` section is reserved for fonts, sounds and UI colours.

## A7. glTF model spec

| Rule | Value |
|---|---|
| Format | glTF 2.0 binary `.glb`, one scene, everything embedded. Images are PNG or JPEG. |
| Units and axes | glTF defaults, with no conversion: metres, right-handed, +Y up, the front facing +Z (towards the viewer). |
| Origin | The bottom-centre of the rest-pose bounding box. The model stands on y=0, and spin is about +Y through the origin. |
| Size | The bounding box fits x∈[-0.5,0.5], y∈[0,1], z∈[-0.5,0.5], with the largest side about 1 m. <br>The loader fits the rest-pose bounding box to the grid cell by scaling a **wrapper node**, so animation clips are never touched. <br>Anything off by more than 10× gets a "wrong units?" warning. |
| Media slots | A material whose name matches a media kind gets that image as its base colour. <br>`cover` is required on game templates. `back`, `spine`, `label` and `screenshot` are optional. <br>Matching ignores case and a trailing Blender `.NNN` suffix. <br>TEXCOORD_0 spans 0..1 across the face, upright, and sampling is clamped. <br>Art is centre-cropped to fill. The face's aspect ratio comes from the material's `extras.aspect`, or else from the slot mesh's bounds. <br>With no art, the slot keeps its authored placeholder texture. <br>Set the base colour factor to white. |
| Materials | Remapped onto the launcher's fixed shader set (lit, unlit, slot), so a user model never adds a shader variant. <br>Supported: base colour, metallic/roughness, normal, emissive, vertex colours, `KHR_materials_unlit`, `KHR_texture_transform`, alpha OPAQUE or MASK, and double-sided. BLEND counts as MASK. <br>Anything else is ignored. |
| Animations (optional; names match like slots) | `idle` loops while not focused. <br>`focused` loops while focused. <br>`launch` plays once; the emulator starts when it ends or after 2 s, whichever comes first. <br>Node TRS, skinning (≤64 joints, 4 influences per vertex) and morph targets (≤8) are supported. Other clips are ignored. |
| Procedural fallbacks | The grid's focus lift and scale always apply. <br>Spin or bob runs only for a state without a clip. <br>The launch fallback spins up and moves towards the camera. |
| Ignored | Cameras, `KHR_lights_punctual` and extra scenes. Theme lights are the only lights. |
| Runtime handling | The first time a user `.glb` is used, a worker converts it to a native scene in `CacheDir/models/`, keyed by path, size and mtime. Textures are mipmapped and scaled to fit the budget. <br>A proxy shows until it's ready. |

### Budgets

These are provisional; M1 and M6 confirm them on the Deck.

| Model | Triangles | Textures (excluding media slots) | Materials |
|---|---|---|---|
| Game template (built-in or per system) | ≤ 2,000 | ≤ 2 × 1024² | ≤ 4 |
| Per-game custom model | ≤ 5,000 | ≤ 2 × 1024² | ≤ 4 |
| System model | ≤ 30,000 | ≤ 4 × 2048² | ≤ 8 |

`ModelInspector` checks each model first:
- Over budget: the model loads, with a warning.
- More than 2× any budget: the model is rejected, and the next model in the resolution order is used.

### Resolution order (first hit wins)

User files are matched by `path_key`, with or without the ROM's extension.

- **System:**
  1. `ConfigDir/models/systems/<system>.glb`
  2. the theme's `models/systems/<system>.glb`
  3. the built-in `res://assets/models/systems/<system>.glb`
  4. the generic built-in
- **Game:**
  1. `ConfigDir/models/games/<system>/<rel path>.glb`
  2. `ConfigDir/models/templates/<system>.glb`
  3. the theme's `models/templates/<system>.glb`
  4. the built-in template named by `game_model`

The built-in templates (M5) are `dvd_case` (PlayStation 2, GameCube), `jewel_case` (PlayStation, Saturn, Dreamcast), `cartridge_box` (NES, SNES, N64, the Game Boy family), `clamshell` (Mega Drive, Master System) and `umd_case` (PSP), plus the generic system model `generic`, a memory-card-shaped slab with a `label` slot. `BoxTemplateGenerator` builds them from real case sizes in millimetres: a rounded-rectangle front outline extruded to the depth, with bevelled edges, one surface per material (the front slot, `back`, `spine`, `case`), and `extras.aspect` on each slot. It exports them with Godot's glTF exporter; the output is deterministic, and `BuiltInModelTests` checks each file against this spec. About 220 triangles each.

**Generated faces (M5).** With front art only, the item shader makes the rest. The spine is the cover's dominant colour, with the title reading top to bottom and a darker band where a logo would be. The back is a darker gradient of that colour, with the title and a strip of the cover. The dominant colour is chosen per vertex from the cover's 4×4 mip, as the texel most like the others, preferring saturated ones. With no art, the front is the plain colour (the system's colour, varied per game) with the title and a thin frame. Titles come from the title atlas.

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
