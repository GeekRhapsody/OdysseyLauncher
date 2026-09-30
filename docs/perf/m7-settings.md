# M7 part 1, the shared UI components and the settings screen: checks and measurements

Measured on 30 September 2026 on the baseline Steam Deck (the machine in [m1-spike.md](m1-spike.md#machine)), docked, windowed at 1280×800.

- Builds are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on.
- "Before" is M6 part 2's commit (`550e1e6`), exported from a worktree and benched in the same session.
- The bench JSON is in [m7/](m7/), and the captures are in [m7/captures.jpg](m7/captures.jpg).
- The brief and the acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m7-settings-ui).

## Performance

Part 1 adds nothing to browsing but a few calls a frame: the settings layer's update (it returns at once while the settings are closed), the jobs' tick (an empty list), and a second input action per navigation command (NavInput now polls a keyboard action and a gamepad action for each, so the on-screen keyboard can take typing while the pad still navigates). The settings screen, the job runner and the progress cards are built in a warm-up step after `interactive`, so start-up doesn't do them.

The 60 s scroll of the 3,000-game library (M6 part 1's), three runs each after a warm-up:

```powershell
$lib = "$PWD\artifacts\synthetic-3000"
& <worktree of 550e1e6>\tools\bench-export.ps1 -SkipExport -Runs 3 -Label m7-base-scroll -AppArgs "--user-dir=$lib", '--bench-scenario=scroll'
.\tools\bench-export.ps1 -Runs 3 -Label m7-scroll -AppArgs "--user-dir=$lib", '--bench-scenario=scroll'
```

| | Before (`550e1e6`) | Part 1 |
|---|---|---|
| Start-up of our code, median (range) | 517 ms (511–603) | 446 ms (404–634) |
| Scroll mean, p99 | 16.68 ms, 17.69–18.08 ms | 16.68 ms, 17.59–18.18 ms |
| Scroll hitches, frames over 2× | 0, 0 in every run | 0, 0 in every run |
| Textured | 100.00% | 100.00% |
| Visible grid textured | 17.0–17.1 ms | 15.8–17.2 ms |
| Main-thread allocation per scroll | 64 B | 64 B |
| GPU | 1.33–1.36 ms | 1.30–1.32 ms |
| Working set (peak) | 426 MB (440–443) | 425–426 MB (441–442) |

No measurable change: start-up moves by more than this between sessions (A3), and every scroll figure is the same.

## Captures

Taken with `--capture` and `--fixed-fps 60` on a copy of the 3,000-game library's config and databases (`artifacts/m7/user`), so the saves the settings screen made couldn't touch the bench libraries. `--open=<screen>` shows a screen or component once the app is interactive; `--nav-script` then drives it as the pad would, and its `click`, `scroll` and `type` steps send real mouse and keyboard events.

| Capture | Command (after `godot --path godot --resolution 1280x800 --fixed-fps 60 -- --user-dir=<copy>`) | Checked |
|---|---|---|
| Settings | `--open=settings` | The main page; the grid's overlay steps aside while it's open |
| ROM folders, a system, emulators, scraping | `--open=settings --nav-script=accept,down,…` | Focus moves row to row with the D-pad; a page replaces the one below it; install checks fill in off the main thread |
| Theme | `…,down,down,accept,wait,down,accept` | Chosen from a list of the themes' names; `settings.toml` got `theme = "retro-tv"` below the user's comments, and the theme switched in 0.22 s without a restart |
| A system's ROM folder | `…accept,wait,down,accept,wait,accept,wait,x` | The picker opened at the system's folder; X used it; `systems.toml` got `[systems.gb] rom_dirs = [...]`, and the system was rescanned |
| Credentials | `…accept` into SteamGridDB, then keys typed with A and Menu | Typed hidden (dots, with Show); saved to `secrets.toml` only (no other file, and not the log, holds the value); shown masked after |
| On-screen keyboard | `--open=keyboard --nav-script=x,x,favourite,accept,right,accept,letterprevious` and `…=type` | X deletes, Y is a space, A types the focused key, LT shifts; physical key events type straight in |
| Image picker, folder picker, program picker | `--open=image-picker --open-path=<5,000-file folder> --nav-script=last,letterprevious,down` | 300 folders and 5,000 images listed in a virtualised list (6 other files not shown); letter jumps; a 512² thumbnail decoded off the main thread; the program picker shows only `.exe` |
| Places and drives | `--open=folder-picker` | Your folder, the ROM folder, Desktop, Downloads, local and removable drives, and the NAS's mapped drive with its label and share |
| NAS share | `--open-path=S:/` | 95 folders listed from the share |
| Slow and unreachable shares | `--open-path=//10.255.255.1/roms`, `--open-path=//odyssey-no-such-host/roms` | "Still opening … B stops waiting" after 2.5 s while the app keeps drawing (the capture fired on schedule); an unreachable share falls back to the top level, saying why |
| Wheel and click | `--open=image-picker … --nav-script=scroll,click` | The wheel scrolls the list 9 rows without moving the selection; a click selects the row under it |
| Confirmation, scrape all missing | `--open=confirm`; `--open=settings` then the Library row | The safe answer is focused for a destructive action; "Scrape 3,000 games?" counts games per system and names the providers skipped for want of credentials (not started: that would be a live scrape) |
| Progress | `--open=progress` | A job card per operation over the grid, with a bar, counts, a provider notice and Cancel; the same jobs as rows in the settings' Library section, where A cancels |

## Found and fixed while checking

- A page pushed over another showed the one below through its translucent frame: pages now hide the page under them (dialogs still show it, dimmed).
- The grid's overlay text and the progress cards showed beside the settings panel: both step aside while the settings are open.
- A new `secrets.toml` got its table above its header comment: Tomlyn keeps a comment-only file's text as the document's own trailing trivia, written last. The editor now moves it in front of the first key or table it adds.
- A new table added a second blank line to a file that already ended with one.
- B while the picker's first folder was still opening (a slow share) left an empty list: it now falls back to the places and drives.
- A progress card with a long title ran off the screen: cards are a fixed width, and titles are cut short with an ellipsis.
