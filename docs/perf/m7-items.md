# M7 part 2, the item options panels: checks and measurements

Measured on 1 October 2026 on the baseline Steam Deck (the machine in [m1-spike.md](m1-spike.md#machine)), docked, windowed at 1280×800.

- Builds are ExportRelease on .NET 8.0.31, Mobile/D3D12, with the shader baker on.
- "Before" is M7 part 1's commit (`634406d`), exported from a worktree and benched in the same session.
- The bench JSON is in [m7/part2/](m7/part2/), and the captures are in [m7/part2/captures.jpg](m7/part2/captures.jpg).
- The brief and the acceptance criteria are in [ROADMAP.md](../ROADMAP.md#m7-settings-ui).

## Performance

Part 2 adds nothing to browsing but two cheap checks:

- Refreshing a cell (after its media changed) now sets its title too, so a title edited in the options shows. The title atlas compares the title with the one it last drew (a managed string: reading the label's text back would allocate) and redraws only when it changed.
- The navigator checks once a frame whether renamed games are due to be read again (a number compared with the clock).

The panels, their services and their reads all run when they're open, and every library read, file copy, model import and image decode happens off the main thread.

The 60 s scroll of the 3,000-game library (M6 part 1's), three runs each after a warm-up:

```powershell
$lib = "$PWD\artifacts\synthetic-3000"
& <worktree of 634406d>\tools\bench-export.ps1 -Runs 3 -Label m7p2-base-scroll -AppArgs "--user-dir=$lib", '--bench-scenario=scroll'
.\tools\bench-export.ps1 -Runs 3 -Label m7p2-scroll -AppArgs "--user-dir=$lib", '--bench-scenario=scroll'
```

| | Before (`634406d`) | Part 2 |
|---|---|---|
| Start-up of our code, median (range) | 375 ms (355–531) | 411 ms (365–435) |
| Scroll mean, p99 | 16.68 ms, 20.77–21.32 ms | 16.68 ms, 21.11–21.30 ms |
| Scroll hitches, frames over 2× | 2, 0, 0; 0 over 2× | 0, 0, 1; 0 over 2× |
| Textured | 100.00% | 100.00% |
| Visible grid textured | 12.7–18.6 ms | 13.2–19.0 ms |
| Main-thread allocation per scroll | 64 B | 64 B |
| GPU | 1.34–1.39 ms | 1.35–1.37 ms |
| Working set (peak) | 426 MB (441) | 425–426 MB (441–442) |

No measurable change. Start-up's ranges overlap, and it moves by more than this between sessions (A3). p99 was 17.6–18.2 ms in part 1's session and about 21 ms in this one, for both builds: the same environmental pacing as M5's (ROADMAP.md, M5).

## Captures

Taken with `--capture` and `--fixed-fps 60` on a small portable library made for them (`artifacts/m7b`: `tools/synthetic-library --games=60 --others=2 --slots=back,spine,screenshot,logo`), restored from a copy before each run that changed it. Its Mega Drive has Sonic the Hedgehog 3 with scraped data restored offline: a saved ScreenScraper response (the recorded test fixture, with dummy credentials) and scraped images drawn for the purpose, picked up by a scan with no network, so the panels show scraped and user sources side by side. A folder of the user's own images (`artifacts/m7b-images`) is where the image picker starts. Every capture ran `--start-system=megadrive --start-index=2` (Sonic) or started on the systems grid (Game Boy), then a `--nav-script` from X:

| Capture | Steps after X | Checked |
|---|---|---|
| Game options | | The emulator (the system's), the model (the system's template, named), the images (3 scraped), metadata (7 of 7, from scraping) and the scrape status |
| Images, scraped | `down,down,accept` | A card per slot, with its image decoded off the main thread, "Scraped from ScreenScraper" or "None", its size, and whether the game's template shows that slot |
| Image picker | `…,accept` | Opens in the images folder (the use's last folder), with a preview |
| Images, three of mine | `…,accept,…` on the cover, back and spine | Each "Yours" once chosen; `media/megadrive/<slot>/Sonic the Hedgehog 3 (Europe).md.png` written; the log says the game was rebound in place after each |
| Mine on the box | the same, then `menu` | In the same run, the box shows the user's cover and spine, with no restart or rescan |
| Removing mine | `favourite` on the cover, then "Remove it" | The scraped cover shows again ("Removed: the image from ScreenScraper shows again") |
| Title and metadata | `down,down,down,accept` | Each field's value (the user's, else the scraped one) and where it came from |
| A bad date | `…,down,accept,type,menu` | "24/02/1994Ok 1" is refused before saving, with the formats it takes |
| Renamed | on Eternal Fighter III: Title, `x,x,x,type,menu`, then `menu` | "Eternal Fighter Ok 1" on its box and in the heading, renamed in place ("Titles: 1 game(s) in megadrive renamed in place") |
| Emulator | `accept`, then Dolphin | Only this game; "The system's emulator" first; saved as its override ("Its own") |
| Clear metadata | `down`×5, `accept` | The dialog lists what goes (scraped data, every image including the user's, the model, edits) and what stays; "Keep it" is focused |
| Cleared | `left,accept`, then `menu` | The box is a plain one with its title in the same run; the user's art and the scraped files are deleted |
| A model of its own | `down,accept,accept` (the sample theme's television) | Imported, with its counts and slots; the box becomes the television in place |
| Scrape, no credentials | `down`×4, `accept` | "None of your providers has its credentials yet: add them in Settings, under Scraping." No request is made |
| System options | on Game Boy: `last` | ROM folders, emulator, models (the theme's card and template, named) and "Scrape this system" with its count (2 games, 2 never scraped) |
| Scrape this system? | `last,accept`, with a dummy SteamGridDB key in a copy | The count, the providers it will use and those skipped. Not started: that would be a live scrape |
| Game template | `down,down,down,accept` | The theme's choice (named), the user's own model, then every template in the active and built-in themes |
| Jewel cases | `jewel_case`, then `menu,accept` | `systems.toml` got `[systems.gb] game_model = "jewel_case"`; the theme reloaded in the background and Game Boy's games are jewel cases |
| My system model | System model, then the sample theme's console | Imported to `models/systems/gb.glb`; the theme reloaded and the Game Boy card is the console |

## Found and fixed while checking

- **Switching away from a theme whose models have clips leaked their node trees** (since M6 part 2): `ModelLoader.ForgetUserModels` dropped a user theme's models without freeing their scenes, which aren't in the scene tree. Godot reported 6 meshes, 6 instances and 27 objects leaked at exit after one switch away from the sample theme. Importing a system model reloads the theme, so this would have grown with every import. The forgotten models are now freed once the next theme is applied: no leak is reported after the same switch.
- "Scrape this game" with no credentials named only ScreenScraper's missing keys; it now says that none of the providers has credentials.
- A model's counts read "1 textures".
