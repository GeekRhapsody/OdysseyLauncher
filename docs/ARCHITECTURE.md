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
| `Config` | Loads TOML (Tomlyn), layering user files over built-in defaults (embedded resources). <br>Merges recursively; scalars and arrays are replaced. <br>Validates, with file:line:column diagnostics; unknown keys get a "did you mean" warning. <br>Parsers take text plus a source name, so the app can feed `res://` files from the PCK. <br>From M7, writes go through Tomlyn's syntax tree, so comments survive. |
| `Data` | `LibraryDb` and `UserDb`, plus a migration runner. <br>**Microsoft.Data.Sqlite's async API is synchronous**, so reads run on the thread pool with pooled connections, and writes go through one dedicated writer thread. <br>Every connection sets WAL, `foreign_keys=ON`, `synchronous=NORMAL` and `busy_timeout`. |
| `Scanning` | Walks ROM folders per system (extensions, recursion, excludes). Hides files referenced by an `.m3u`. <br>Rescans incrementally by size and mtime. <br>Normalises paths to `path_key`. <br>Also indexes user override files (models, media), so nothing is probed per item at runtime. |
| `Scraping` | `IScraper` for ScreenScraper and SteamGridDB. <br>Handles quotas and rate limits, and match resolution. <br>Saves raw responses with credentials stripped. |
| `Media` | `MediaStore`: deterministic paths, atomic writes (temp file then rename), and image dimensions read from headers only. |
| `Models` | `ModelInspector` validates a `.glb` against the A7 spec by reading only the GLB JSON chunk and the image headers. It has no Godot dependency. |
| `Launching` | `LaunchPlanner` is pure: it resolves the emulator profile and expands the template into an argument list. <br>`LaunchService` runs the plan and records the play session. |
| `Library` | The façade the app uses: systems summary (boot), games list (on entry), favourites and overrides, and rescan, scrape and rebuild jobs with progress. |
| `Platform` | The only OS-specific code. <br>Interfaces: `IPlatformPaths`, `IProcessRunner`, `IWindowFocus`. <br>Windows implementations use P/Invoke to user32 and kernel32; Linux comes later. |
| `Diagnostics` | Debug-argument parser, `StartupTimeline`, `FrameTimeStats`, `BenchReport` (System.Text.Json source generation), and a minimal `ILog` that redacts secrets. |

Every `await` in Core uses `ConfigureAwait(false)`. Analyser rule CA2007 is an error in `src/`.

### Godot app (`godot/src`, namespace `Launcher.App.*`)

| Area | Responsibility |
|---|---|
| `Boot` | Main scene. Loads settings, theme and the systems summary, builds the systems grid, then marks `interactive`. |
| `Screens` | State machine: Systems → Games → Launching → back. Includes the Favourites and Recently played virtual systems. |
| `Grid` | Virtualised 3D grid. <br>A cell pool covers the visible rows plus one row of margin on each side (8 × 8 cells in M1), and cells are re-bound rather than recreated. <br>Template items are drawn as **one `MultiMesh` per template**. Each pool cell has a fixed instance and a fixed `Texture2DArray` layer, and `INSTANCE_CUSTOM` = (layer, fade, phase). <br>Per-game custom `.glb` models use per-node instances bound to the same cells. <br>**The camera scrolls and the grid stays still**, so a frame only touches newly bound rows, the focused items and fading covers. <br>**One `_Process` drives every item.** <br>Each pooled cell carries a bind generation, so late results for an old binding are dropped. <br>Critically damped scrolling. <br>Hold-to-scroll acceleration, plus page and letter jumps. |
| `Models` | Resolves each item's model (order in A7). <br>Converts each user `.glb` once into a cached native scene. <br>Remaps its materials onto the launcher's fixed shader set. <br>Binds media slots and plays idle, focused and launch clips, or the procedural fallbacks. |
| `Textures` | `TextureStreamer`: prioritised, cancellable requests (one per pool cell); 2 dedicated decode workers; mandatory baked derivatives (BC7 DDS, 512² with mips); pool textures created at boot and only updated while browsing; a per-frame upload budget; an LRU memory budget; and an opaque placeholder-to-cover fade. |
| `Theming` | Four-corner gradient on a background canvas layer (`Environment` background mode Canvas). <br>Three `DirectionalLight3D` children of the camera, plus an ambient colour. <br>Cross-fades between per-system looks. |
| `Diagnostics` | `DebugHooks` autoload (`--capture`, `--bench`), timeline marks, and a log sink that writes to Godot's output and a file. |
| Platform glue | A main-thread queue with a per-frame time budget. <br>Hands the native window handle to `IWindowFocus`. <br>While an emulator runs: `RenderLoopEnabled = false`, textures are evicted and input is ignored until focus returns. |

## A2. Key interfaces (sketch)

```csharp
// Launcher.Core.Platform
public interface IPlatformPaths {
    string ConfigDir { get; }   // settings/systems/emulators/secrets .toml, themes/, models/, media/ (user overrides)
    string DataDir { get; }     // library.db, userdata.db, media/, scraped/, logs/
    string CacheDir { get; }    // regenerable without network: textures/, models/
    string HomeDir { get; }
}
public interface IProcessRunner {   // Windows: child created inside a job object; completes when the job has no processes left
    Task<ProcessOutcome> RunAsync(LaunchPlan plan, CancellationToken ct);
}
public interface IWindowFocus {
    void BeforeLaunch(nint launcherWindow, int childProcessId);   // AllowSetForegroundWindow, minimise
    void AfterExit(nint launcherWindow);                           // restore and take foreground back
}

// Launcher.Core.Config
public sealed record Diagnostic(Severity Severity, string Source, int Line, int Column, string Message);
public sealed record ConfigLoadResult(AppConfig Config, IReadOnlyList<Diagnostic> Diagnostics);
public interface IConfigLoader { ConfigLoadResult Load(ConfigSources sources); }   // never throws for user mistakes

// Launcher.Core.Library
public readonly record struct GameKey(string SystemId, string PathKey);   // stable across rebuilds and case-only renames
public interface ILibrary {
    Task<IReadOnlyList<SystemSummary>> GetSystemsAsync(CancellationToken ct);   // boot: one small indexed query
    Task<GameList> GetGamesAsync(string systemId, CancellationToken ct);        // entry: compact, pre-sorted rows
    Task SetFavouriteAsync(GameKey game, bool favourite, CancellationToken ct);
    Task<ScanSummary> RescanAsync(string? systemId, IProgress<JobProgress> progress, CancellationToken ct);
    Task RebuildAsync(IProgress<JobProgress> progress, CancellationToken ct);   // new library.db from disk, no network, swapped in atomically
}

// Launcher.Core.Scraping
public interface IScraper {
    string Id { get; }                                                          // "screenscraper" | "steamgriddb"
    Task<IReadOnlyList<ScrapeCandidate>> SearchAsync(ScrapeQuery query, CancellationToken ct);  // filename now, hashes later
    Task<ScrapedGame> FetchAsync(string scraperGameId, ScrapeContext context, CancellationToken ct);
}

// Launcher.Core.Media
public interface IMediaStore {
    string RelativePathFor(GameKey game, MediaKind kind, string extension);    // deterministic
    Task<StoredMedia> SaveAsync(GameKey game, MediaKind kind, Stream content, string extension, CancellationToken ct);
}

// Launcher.Core.Launching
public sealed record LaunchPlan(string Executable, IReadOnlyList<string> Arguments, string WorkingDirectory);
public interface ILaunchPlanner { LaunchPlanResult Plan(GameKey game, string? emulatorOverride); }   // pure, unit-tested

// Launcher.App.Textures (Godot side)
public interface ITextureStreamer {
    void Request(int slot, int bindGeneration, string sourcePath, float priority);   // calling again re-prioritises
    void Cancel(int slot);
    bool TryGet(int slot, int bindGeneration, out Texture2D texture);
    void PumpUploads(long budgetBytes);                                                // main thread, once per frame
}
```

**Match resolution for scraping (per game, per scraper):**
1. A manual match in `userdata.db`.
2. Otherwise, the match stored in `library.db`.
3. Otherwise, a filename search, and later a hash search.

Once matched, re-scrapes use `FetchAsync(id)` and never search again. Saved responses carry the matched id, so a rebuild recovers automatic matches offline, and manual corrections always win.

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
  - **Format (M1): BC7 in DDS, 512×512, full mip chain (341 KB).**
    - Decode is 0.26 ms per cover, against 5.4 ms for PNG and 4.1 ms for JPEG.
    - GPU memory is 4× smaller than RGBA8.
    - The visible grid is textured 10 ms after the first frame, against about 100 ms.
    - BC1 (171 KB) is an option for a low-memory setting. KTX, Godot `.res` and raw blobs were measured and rejected.
    - Real art is centre-cropped to the square canonical size.
  - **Open (M4): the encoder.** `Image.Compress` returns `Unavailable` in export templates (measured), so the shipped app can't bake BCn itself. The options:
    - a managed BCn encoder package (ask the owner first)
    - our own encoder
    - a `RenderingDevice` compute port of Godot's Betsy encoder
    - JPEG derivatives, which met every frame target in M1 at 4× the VRAM and 5× less disk
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
  - Warm the first upload during the post-`interactive` warm-up, because the first one takes up to 43 ms.
- **Memory:** an LRU cache with a starting budget of 256 MB.
  - Evicted textures and uploaded `Image`s are `Dispose()`d at once.
  - The focused item upgrades to the full-resolution art.

**Rendering:**
- **The Mobile renderer, on D3D12** (M1). Its GPU time is 36–42% lower than Forward+ with the same frame pacing, and its output matches within 4/255.
- No shadows, GI, SSAO, SSR or glow; the tonemapper is Linear.
- 3D renders at ≤1080p internally when docked at 4K, upscaled with bilinear. The 2D UI renders at native resolution.
  - At 2560×1440 fullscreen, Forward+ took 6.45 ms of GPU time native and 2.43 ms at 0.5 scale; Mobile took 1.70 ms at 0.5 scale.
  - Native 4K on Forward+ would be about 14.5 ms.
  - FSR1 and 3840×2160 still need measuring (M5).
- Unfocused idle motion runs in the vertex shader (`TIME` plus a per-instance phase), so it costs nothing in C#.
- The placeholder-to-cover fade happens **inside one opaque cover shader**, through a per-instance `fade` parameter. There's no alpha blending and no extra variant.
- User `.glb` materials are remapped onto the fixed shader set.
- Every variant is drawn once, off-screen, just after `interactive`. Ubershaders and the on-disk pipeline cache cover warm starts.
- Font glyph ranges, including fallbacks, are pre-rendered at import.

**C# rules:**
- No allocations in per-frame code: no LINQ, closures, boxing, string formatting or implicit `string`→`StringName` conversions. Cache every `StringName` and `NodePath`.
- `GCSettings.LatencyMode = SustainedLowLatency` while browsing.
- Update transforms only for items that move.
- Never `.Wait()` or `.Result` on the main thread.
- The bench reports `GC.GetAllocatedBytesForCurrentThread()` for the main thread. **The ceiling is 4 KB per 60 s scripted scroll** (M1 measured 0.6 KB), with no GC caused by the main thread.

**M1 experiments.** Results are in [SPIKE_RESULTS.md](SPIKE_RESULTS.md). Items marked "later" moved to the milestone named when M1 closed.
- Done: renderer (Forward+ against Mobile, on the grid) → Mobile/D3D12. The driver matrix was run on the scaffold only; Compatibility wasn't benched on the grid.
- Done: per-node materials against a `Texture2DArray` indexed per instance, and MultiMesh against nodes → MultiMesh plus `Texture2DArray` for templates.
- Done: derivative format and upload path → BC7 DDS; update pre-created textures on the main thread. The encoder is open (M4).
- Done: upload budget and decode worker count → 4 MB per frame (measured) and 2 workers. The cap of 8 uploads per frame is proposed but untested (M5).
- Partly done: the 4K render scale. Measured at 2560×1440 only; 3840×2160 and FSR1 are later (M5).
- Later (M5): ReadyToRun, and the export shader baker.
- Later (M2): config parse. Tomlyn reflection mapping, versus hand mapping from `TomlTable`, versus a cached snapshot keyed by file mtimes.
- Later (M2): Microsoft.Data.Sqlite loading its native library, both in an editor run and in an export.
- Later (M6): runtime `.glb` conversion on a worker thread.
- Later (M2): a net10.0 comparison build. Adopting it needs the owner's approval.
- Later (M5): PresentMon, to explain the periodic present delay, if the owner is happy to install it.

## A4. Storage

| Location | Windows default | Contents |
|---|---|---|
| ConfigDir | `%APPDATA%\OdysseyLauncher` | `settings.toml`, `systems.toml`, `emulators.toml`, `secrets.toml`, `themes/<id>/`, `models/{systems,templates,games}/`, `media/` (user art overrides) |
| DataDir | `%LOCALAPPDATA%\OdysseyLauncher` | `library.db`, `userdata.db` (plus the last 3 backups), `media/<system>/<kind>/<path_key>.<ext>`, `scraped/<scraper>/<system>/<path_key>.json`, `logs/` |
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
  - A system can list `aliases` (such as `genesis`). They're tried as default folder names, and `userdata.db` rows stored under an alias are re-keyed to the canonical id.
- **Identity:**
  - `rel_path` is the path as on disk: relative to the ROM folder, `/`-separated, Unicode NFC.
  - `path_key` is `rel_path` lower-cased (invariant) on every OS. It's the stable identity, and it keeps keys portable.
  - On Linux, if two files collide after case-folding, the scanner keeps the first and warns.
- **Why `path_key`:** keying on the full path, extension included, keeps `Game.cue` and `Game.chd` apart, and a case-only rename keeps its user data.
- **Stored paths:** app-written files are named by `path_key`. The DB stores paths relative to their root, never absolute paths.
- **Rebuildable:** `library.db` is a pure function of config, the ROM folders, `media/`, `scraped/`, and the user's model and media override folders.
  - A rebuild writes a new file offline and swaps it in atomically.
  - A golden test checks that a rebuild equals the incrementally built DB.
- **Back up:** ConfigDir and `userdata.db`, plus `media/` and `scraped/` to avoid a re-scrape.
- **Orphans:** when a file disappears, its `userdata.db` rows are kept, so moving a ROM out and back loses nothing.

### `library.db` (schema version 1, `PRAGMA user_version = 1`)

```sql
CREATE TABLE systems (
  system_id   TEXT PRIMARY KEY,               -- config id, e.g. 'megadrive'
  rom_dir     TEXT NOT NULL,                  -- resolved absolute folder at last scan
  scanned_at  INTEGER,                        -- unix ms; NULL = never scanned
  game_count  INTEGER NOT NULL DEFAULT 0      -- denormalised for the boot query
) STRICT;

CREATE TABLE games (
  game_id     INTEGER PRIMARY KEY,
  system_id   TEXT NOT NULL REFERENCES systems(system_id) ON DELETE CASCADE,
  rel_path    TEXT NOT NULL,                  -- as on disk: relative, '/' separators, NFC
  path_key    TEXT NOT NULL,                  -- lower-invariant rel_path: the stable identity
  size_bytes  INTEGER NOT NULL,
  mtime_ms    INTEGER NOT NULL,
  crc32 TEXT, md5 TEXT, sha1 TEXT,            -- NULL until hash matching lands
  title       TEXT NOT NULL,                  -- scraped title, else cleaned file name (user overrides live in userdata)
  sort_title  TEXT NOT NULL,
  UNIQUE (system_id, path_key)
) STRICT;
CREATE INDEX games_by_system ON games(system_id, sort_title);

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

### `userdata.db` (schema version 1)

This DB can't be rebuilt. It's keyed by `(system_id, path_key)`, never by `library.db` ids.

```sql
CREATE TABLE favourites     (system_id TEXT NOT NULL, path_key TEXT NOT NULL, added_at INTEGER NOT NULL,
                             PRIMARY KEY (system_id, path_key)) STRICT, WITHOUT ROWID;
CREATE TABLE play_stats     (system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             play_count INTEGER NOT NULL DEFAULT 0, total_seconds INTEGER NOT NULL DEFAULT 0,
                             last_played_at INTEGER, PRIMARY KEY (system_id, path_key)) STRICT, WITHOUT ROWID;
CREATE TABLE play_sessions  (session_id INTEGER PRIMARY KEY, system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             emulator TEXT NOT NULL, started_at INTEGER NOT NULL,
                             ended_at INTEGER, exit_code INTEGER) STRICT;      -- ended_at NULL = launcher died; closed on next start
CREATE TABLE manual_matches (system_id TEXT NOT NULL, path_key TEXT NOT NULL, scraper TEXT NOT NULL,
                             scraper_game_id TEXT NOT NULL, matched_at INTEGER NOT NULL,
                             PRIMARY KEY (system_id, path_key, scraper)) STRICT, WITHOUT ROWID;
CREATE TABLE game_overrides (system_id TEXT NOT NULL, path_key TEXT NOT NULL,
                             title TEXT, emulator TEXT,                       -- NULL = use scraped title / system default
                             hidden INTEGER NOT NULL DEFAULT 0,
                             PRIMARY KEY (system_id, path_key)) STRICT, WITHOUT ROWID;
```

### Migrations (versioned)

- Each DB has its own ordered SQL files, embedded in Core (`Data/Migrations/{Library,User}/NNNN_name.sql`). A shipped file is never edited.
- The runner follows SQLite's documented procedure:
  1. `foreign_keys=OFF` before `BEGIN`.
  2. Apply every migration newer than `user_version`.
  3. `foreign_key_check`.
  4. Bump `user_version` and commit.
- `userdata.db` is copied with `VACUUM INTO` first, and the last 3 backups are kept.
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

[variables]                          # expanded at config load; may reference each other (cycles are errors)
retroarch = "C:/Emulators/RetroArch"

[display]
theme = "memory-card"
fullscreen = true

[scraping]
regions = ["eu", "wor", "us", "jp"]  # first available wins
languages = ["en"]
cover_sources = ["screenscraper", "steamgriddb"]
```

### System definition

Built-in definitions ship in `Launcher.Core/Defaults/systems.toml`. The user's `ConfigDir/systems.toml` holds only what changes.

```toml
# built-in
[systems.megadrive]
name = "Mega Drive"
manufacturer = "Sega"
year = 1988
aliases = ["genesis"]
extensions = [".md", ".gen", ".smd", ".bin", ".zip", ".7z"]
emulator = "retroarch-genesis-plus-gx"
alt_emulators = ["blastem"]
game_model = "clamshell"             # built-in box template id
screenscraper_id = 1

# user override
[systems.megadrive]
rom_dir = "E:/Sega/Mega Drive"       # default "{rom_root}/megadrive"
emulator = "blastem"

[systems.mastersystem]
enabled = false
```

### Emulator profiles

Built-in profiles ship in `Defaults/emulators.toml`, using variables like `{retroarch}`. The user's `ConfigDir/emulators.toml` layers over them.

```toml
[emulators.retroarch-genesis-plus-gx]
name = "RetroArch: Genesis Plus GX"
executable = "{retroarch}/retroarch.exe"
args = ["-L", "{retroarch}/cores/genesis_plus_gx_libretro.dll", "--fullscreen", "{rom}"]

[emulators.blastem]
name = "BlastEm"
executable = "C:/Emulators/BlastEm/blastem.exe"
args = ["-f", "--rom={rom}"]         # placeholders can sit anywhere inside an entry
working_dir = "{emulator_dir}"       # default
```

### Launch placeholders (expanded at launch time)

| Placeholder | Expands to |
|---|---|
| `{rom}` | Absolute ROM path, with native separators. |
| `{rom_dir}` | The folder containing the ROM. |
| `{rom_file}` | The ROM's file name. |
| `{rom_name}` | The ROM's file name without its extension. |
| `{system}` | The system id. |
| `{emulator_dir}` | The folder of the expanded `executable`. |
| `{home}`, `{rom_root}`, `{<variable>}` | Resolved already at config load. |

Write `{{` or `}}` for a literal brace.

### Expansion rules

- Each `args` entry becomes exactly one argument (`ProcessStartInfo.ArgumentList`). There's no shell and no hand-quoting.
- Expansion is single-pass, so a ROM named `{x}.zip` stays literal.
- An unknown placeholder is a validation error.
- **`.bat` and `.cmd` executables are rejected.** cmd.exe re-parses their arguments, so a name like "Sonic & Knuckles" would break or inject commands. M3 may add an explicitly escaped mode.

### Paths in config

- Use forward slashes or TOML literal strings (`'C:\Emulators'`).
- Relative paths resolve against ConfigDir, or against the theme folder in `theme.toml`.
- Extension matching ignores case.

### Merge and validation

- Tables merge recursively; scalars and arrays are replaced whole.
- `enabled = false` switches off a built-in entry.
- A new id must be complete, and any missing required keys are listed.
- A TOML syntax error means the whole file is ignored, and its diagnostic is shown.
- A semantic error disables only the offending entry.

### Secrets

ScreenScraper account and developer credentials, and the SteamGridDB API key, live only in `ConfigDir/secrets.toml` or in `ODYSSEY_*` environment variables. ScreenScraper embeds credentials in its URLs, media URLs included, so they're stripped from saved responses, logs and bench output.

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

The built-in templates are `dvd_case`, `jewel_case`, `tall_jewel_case`, `cartridge_box` and `clamshell`.

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
| 2026-09-27 | **Open risk:** the export templates have no BCn encoder (`Image.Compress` returns `Unavailable`). M4 picks an encoder: a package (needs approval), our own, or a GPU compute port. JPEG derivatives are the fallback. | Measured in the export (§2a). JPEG met every frame target at 4× the VRAM. |
| 2026-09-27 | **Uploads:** pool textures are created at boot and only updated on the main thread (4 MB per frame). No texture is created on the main thread while browsing. 2 decode workers. | M1: a BC7 layer update takes 0.03 ms. Main-thread creation has 17–66 ms outliers. Creation on a worker doesn't stall the main thread, but blocks the worker for about 12 ms per call. 4 workers didn't help (§2d). |
| 2026-09-27 | **Targets:** the hitch target is reworded as "no hitches caused by the launcher" (measured against a no-texture control, 0 frames over 2×, 0 hitches fullscreen). New targets: textured ≤ 100 ms, ≥ 99% textured while scrolling, working set ≤ 512 MB, pool ≤ 64 MB. Main-thread allocation ceiling: 4 KB per 60 s scroll. **These wait for the owner's sign-off.** | M1: a periodic present delay about every 5 s, outside our code, gives 0–2 hitches per 60 s run in windowed mode even with nothing streaming. The other targets were met with headroom. |
