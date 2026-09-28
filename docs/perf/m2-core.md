# M2 core data layer: measurements

Measured on 28 September 2026 on the baseline Steam Deck (the machine in [m1-spike.md](m1-spike.md#machine)), with Launcher.Core only: no Godot. The acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m2-core-data-layer).

## Method

- **Library:** `FakeRomTree` (`tests/Launcher.Core.Tests/Benchmarks/`) writes exactly 10,000 empty files across 12 systems (gb, gbc, gba, nes, snes, n64, mastersystem, megadrive, saturn, dreamcast, psx, ps2), named like No-Intro and Redump sets. It includes every multi-file layout: `.gdi` plus 3 tracks, `.cue` plus 2 `.bin` tracks, `.m3u` plus 2 discs, a sub-folder in every 7th game, and some `.txt` files the extension filter drops. That's **6,213 games**.
- **Runs:** each figure is a median. Full scans go into a new, empty library each run. The file cache is warm, because the files were just written; a cold first scan after boot will be slower.
- **Two builds:**
  - `dotnet test`: Debug, on the .NET 10.0.12 runtime (the tests roll forward; this machine has no .NET 8 runtime). Benchmarks run in their own non-parallel collection.
  - `tools/core-bench`: ExportRelease (optimised), **self-contained .NET 8.0.31**, the runtime Godot 4.7.2's export bundles. This is the number to compare with the targets, until the app itself uses Core (M5).

```powershell
# Debug, with the asserted budgets
.\tests\Launcher.Core.Tests\bin\Debug\net8.0\Launcher.Core.Tests.exe -trait "Category=Benchmark" -showLiveOutput

# ExportRelease on .NET 8.0.31
dotnet publish tools/core-bench -c ExportRelease -o artifacts/core-bench
artifacts/core-bench/core-bench.exe $PWD/artifacts/core-bench-work
```

## Results

| Operation | Target (M2) | ExportRelease, .NET 8 (ms) | Debug, .NET 10 (ms) | Budget in the test (ms) |
|---|---|---|---|---|
| Full scan, 10,000 files, 12 systems, into an empty library | < 3,000 | 275–281 | 235–314 | 1,000 |
| Rescan, nothing changed | < 500 | 65–71 | 63–72 | 200 |
| Rescan, 1% changed (30 touched, 35 added, 35 deleted) | | 55–57 | 63–75 | 250 |
| Rebuild (new DB from disk, then swap) | | 237–249 | | |
| `GetGamesAsync`, one 10,000-game system, 200 favourites | < 50 | 17.6–19.2 | 20–28 | 45 |
| `GetGamesAsync`, the same with a title override | | 17.2–19.3 | | |
| `GetSystemsAsync` (the boot query) | ~5 (A3) | 0.03 | | |
| Config load, 3 default files, warm | ~10 (A3, with theme) | 2.1–2.6 | 0.6–2.8 | 10 |
| Config load, first in process | | 46–64 | | |
| `LibraryService.OpenAsync`, first in process, creating both DBs | | 117–142 | | |
| Full scan, first in process | | 356–368 | | |

The ranges are the medians of 2–3 separate invocations in the same session.

### Where the time goes

- **Unchanged rescan.** Enumerating the folders and diffing 6,213 rows. No playlist is read: all 1,578 are served from the `playlists` cache, keyed by size and mtime. With the cache off, the scanner alone takes 104 ms, so the cache saves more than the whole rescan costs.
- **Full scan.** About 100 ms scanning (every playlist read), and the rest parsing titles and inserting in one transaction.
- **`GetGamesAsync`.** Measured with the query alone: reading 10,000 rows from `games_by_system` takes 8.8 ms, the three LEFT JOINs (overrides, favourites, cover) add 4.9 ms, and sorting by `COALESCE(o.sort_title, g.sort_title)` in a temporary B-tree adds 2.4 ms. SQLite uses the primary keys for every join. A covering index or index-order sorting could save 2–5 ms; that isn't needed for the target.
- **First use.** The first config load in a process takes about 50 ms, almost all JIT for Tomlyn and the loader; warm it's 2 ms. Opening the library the first time costs about 120 ms, including loading `e_sqlite3.dll` and creating and migrating both DBs. Both are inside the boot budget but are its largest Core items. ReadyToRun (M5) should cut the JIT share.

## Config-parse options (A3 experiment, carried over from M1)

- **Chosen: hand mapping from Tomlyn's syntax tree** (`SyntaxParser.Parse` → our own `TomlTableNode`). Diagnostics need the line and column of every key after user files are merged over the defaults, and the syntax tree is the only Tomlyn 2.x API that carries them.
- **Reflection mapping** (`TomlSerializer.Deserialize<T>`) wasn't measured. It loses positions, so it can't produce the required diagnostics.
- **A cached snapshot keyed by file mtimes** isn't needed: a warm load is 2 ms. The 50 ms first load is JIT, which a snapshot would only partly avoid (its reader would need JIT too). Revisit after ReadyToRun in M5.

## net10.0 comparison (carried over from M1)

The same bench, built as net10.0 (a copy of Core retargeted, framework-dependent on .NET 10.0.12), in the same session:

| Operation | .NET 8.0.31 (ms) | .NET 10.0.12 (ms) |
|---|---|---|
| Full scan | 274 | 304 |
| Rescan, nothing changed | 69 | 80 |
| Rescan, 1% changed | 57 | 59 |
| `GetGamesAsync`, 10,000 games | 17.6 | 17.9 |
| Config load, first / warm | 46 / 2.1 | 54 / 2.2 |

There's no gain from net10.0 for Core: this work is file-system and SQLite bound. The Godot-side comparison (start-up and frame times in an export) is still open, and so is the .NET 8 end-of-support risk (ARCHITECTURE.md decisions log).

## Not measured here

- SQLite's native load **inside Godot**, in an editor run and in an export. The self-contained console above does load `e_sqlite3.dll` from the publish folder, as an export would, but Godot's export layout isn't tested until the app uses Core (M5).
- The M1 boot target with real config and DB loading, and the 20-system `boot` bench scenario. Both need the Godot app (M5).
