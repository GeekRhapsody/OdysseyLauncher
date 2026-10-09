# Manual tests

Checks that a script can't observe. Each says what to run, what should happen, and what to send back. Automated checks are in `tools/verify.ps1`.

## M3: launching a real emulator, and focus

This checks what the fake emulator can't: a real emulator taking the foreground, the launcher showing its black "Running <title>" screen and idling while the game runs, and the launcher coming back to the front with keyboard focus afterwards. Windows' focus-stealing rules make the last part the one most likely to go wrong, and they behave differently with keyboard and gamepad input, so both are tested.

It uses the RetroArch that RetroBat installed (`C:\RetroBat\emulators\retroarch`, which has every built-in core) and a Mega Drive ROM of your own. Everything the launcher writes goes into `C:\OdysseyTest`; your AppData isn't touched.

### Set-up (once)

1. Build and export, from the repo root in PowerShell:

   ```powershell
   dotnet build
   godot --path godot --export-release "Windows Desktop" $PWD/artifacts/export/windows/OdysseyLauncher.exe
   ```

2. Create `C:\OdysseyTest\settings.toml`:

   ```toml
   [paths]
   rom_root = 'C:\OdysseyTest\ROMs'

   [variables]
   retroarch = 'C:\RetroBat\emulators\retroarch'
   ```

3. Copy a Mega Drive ROM you own into `C:\OdysseyTest\ROMs\megadrive\Test Folder é\`. The space and the accent exercise the quoting. Below, `<rom>` stands for its file name, for example `Sonic the Hedgehog (USA, Europe).md`.

4. Create `C:\OdysseyTest\emulators.toml`, with a stub-launcher profile for test C. The fake emulator starts RetroArch and exits at once, as a stub launcher does:

   ```toml
   [emulators.stub-retroarch]
   name = "Stub, then RetroArch"
   executable = 'C:\Users\claudio\Coding\OdysseyLauncher\tests\FakeEmulator\bin\Debug\net8.0\FakeEmulator.exe'
   core = "{retroarch}/cores/genesis_plus_gx_libretro.dll"
   args = ["--fake-start={retroarch}/retroarch.exe", "--", "-L", "{core}", "--fullscreen", "{rom}"]
   ```

5. The export has no console. Its log is `%APPDATA%\Godot\app_userdata\Odyssey Launcher\logs\godot.log`, rewritten on every run. To see the launch lines after a run:

   ```powershell
   Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Launch|warning|error'
   ```

   Use `++` rather than `--` before the launcher's own arguments: Windows PowerShell can swallow `--`.

### A. Windowed, with the keyboard

```powershell
& .\artifacts\export\windows\OdysseyLauncher.exe ++ --user-dir=C:\OdysseyTest "--launch=megadrive/Test Folder é/<rom>"
```

While it starts:
- The launcher window (the systems grid) appears, then RetroArch opens full screen in front of it within a few seconds, and the game responds to the keyboard straight away, with no click needed.
- Don't Alt+Tab to check on the launcher: switching windows is user input, and it changes what Windows allows afterwards. The log shows whether the emulator took the foreground (`the emulator took the foreground after <n> ms`). The launcher isn't minimised: anything showing behind RetroArch, and the launcher for a moment as the game ends, is black with "Running <title>" in the middle, never the desktop.

While you play, in a second PowerShell window, measure the launcher's CPU use over 10 s:

```powershell
$p = Get-Process OdysseyLauncher; $a = $p.TotalProcessorTime; Start-Sleep 10; $p.Refresh(); '{0:N1} ms of CPU per second' -f (($p.TotalProcessorTime - $a).TotalMilliseconds / 10)
```

- Expected: close to 0, a few ms per second at most. In Task Manager, Details tab, the GPU column for OdysseyLauncher.exe should read 0.
- For comparison, run the same measurement against the launcher with no `--launch` (idle on the systems grid).

Then quit RetroArch with the keyboard: F1, then Quit RetroArch, or Esc (twice if it asks to confirm).
- Expected: within about a second, the launcher window is restored at its old size and position, in front, with an active title bar.
- The log should end with:
  - `Launch: back in the launcher; foreground: Direct.` (or `AttachedInput`, or `AltKey`)
  - `Launch: <title> ended after <n> s (exit code 0).`
  - `Launch: the launcher has keyboard focus again, <n> ms after the game ended.`
- **Failure:** `foreground: Failed`, a flashing taskbar button instead of the window coming forward, or no "keyboard focus again" line.

Close the launcher with Alt+F4.

### B. Full screen, gamepad only

The hardest case: with no keyboard or mouse input during the game, Windows is most likely to refuse the launcher's request to come back.

```powershell
& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest "--launch=megadrive/Test Folder é/<rom>"
```

Once RetroArch is up, don't touch the keyboard or mouse. Play with the gamepad, and quit RetroArch from the gamepad (RetroBat's RetroArch config normally maps hotkey + Start to quit; otherwise use the RetroArch menu).
- Expected: the same as in A, and the launcher comes back full screen.
- Note which `foreground:` result the log shows.

### C. A stub launcher

In `C:\OdysseyTest\systems.toml`, point the Mega Drive at the stub profile:

```toml
[systems.megadrive]
emulator = "stub-retroarch"
```

Run the command from A, and play for at least 30 s.
- A console window flashes up for a moment: that's the stub, because the fake emulator is a console program. The stub exits within a fraction of a second. The launcher must still treat the game as running: it keeps its running screen until RetroArch itself quits, and only then comes back.
- RetroArch must still come to the front with keyboard focus. It's a grandchild the launcher didn't start directly, which is why the launcher lets any process take the foreground at launch.
- The log's `ended after <n> s` should match your play time, not a fraction of a second.

Delete `systems.toml` afterwards.

### D. Failure messages

Each should leave the launcher in front, with no running screen, with a message at the top of its window for 10 s, and a `Launch failed:` line in the log. Adding `--quit-after-launch` after `++` makes the launcher exit with code 1 after the failure (`$LASTEXITCODE`).

1. **A missing core.** Add to `emulators.toml`:

   ```toml
   [emulators.retroarch-genesis-plus-gx]
   core = "{retroarch}/cores/nope_libretro.dll"
   ```

   The log starts with a config warning: `emulators.retroarch-genesis-plus-gx.core: the core '...nope_libretro.dll' doesn't exist, so Master System (mastersystem) and Mega Drive (megadrive) can't launch games...`. The message says `The core '...nope_libretro.dll' for RetroArch: Genesis Plus GX doesn't exist.`

   Remove the override afterwards.

2. **A missing ROM:** `"--launch=megadrive/nothing.md"`. The message says `There's no 'nothing.md' in megadrive's ROM folders.`

3. **An immediate non-zero exit.** Set the stub profile's `args = ["--fake-exit=1"]`, and point the Mega Drive at it as in C. The message says `Stub, then RetroArch closed after 0.<n> s with exit code 1, so the game probably didn't start.`

   Undo both changes afterwards.

### Send back

- The `Select-String` output from the log for A, B and C.
- The CPU figures from A, with and without a game running.
- Anything that differed from what's expected above, especially a `foreground:` result of `Failed`, or a window that didn't come to the front.

## M5: navigation with a controller

This checks what `--nav-script` can't: real buttons, the stick, held moves speeding up, and launching from the grid, where the launcher frees its textures while the game runs. It uses the set-up from M3 (`C:\OdysseyTest`, RetroBat's RetroArch and a Mega Drive ROM of your own). Add a second ROM or two to `ROMs\megadrive` so the grid has something to move through.

```powershell
& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest
```

Use only the gamepad from here on.

1. **Systems grid.** The launcher opens on the systems grid with a system focused (the first one with games). Its name is top left, with its maker, year and games under it. Its details are on its details screen (Y: see [a system's details](#a-systems-details)).
   - The D-pad and the left stick move the focus. Held, a move repeats after about a third of a second, then speeds up over the next second and a half.
   - LB and RB move four rows at a time.
   - View opens the power menu (see [the power menu](#the-power-menu)); B closes it. Rescanning is in the settings: Menu, then Rescan the library. A "Scanning your ROM folders" card shows top right with its progress (M7), then the counts update.
2. **Games grid.** Press A on Mega Drive.
   - The systems grid flies towards you and fades while the games come up from behind: clamshell cases with your ROMs' titles, and plain boxes (no art until M4).
   - The title top left follows the focus, with the system under it. A game's details are on its details screen (Y: see [a game's details](#a-games-details-and-videos)).
   - LT and RT jump between letters.
   - L3 (press the left stick) adds a favourite: "Favourite" shows top right. L3 again removes it.
3. **Back and focus memory.** Move to another game and press B.
   - The games fade back and the systems return.
   - Press A on Mega Drive again: the game you left is focused.
   - Favourites (top left of the systems grid) shows the game you added.
4. **Launching.** Focus your test ROM and press A.
   - The box spins and flies towards you, then RetroArch starts, as in M3 A.
   - While it runs, the launcher's GPU memory (Task Manager, Details, "Dedicated GPU memory" and "Shared GPU memory") should drop by about 20 MB: the cover array is freed.
   - Quit RetroArch from the gamepad. The launcher comes back to the same game, and ignores the button you quit with.
   - Its details now say Played: Once, with the play time. Recently played lists it.

### Send back

- Anything that differed, especially: the stick not moving the focus, a held move that doesn't speed up or overshoots, a button that acts twice, the wrong game focused when you come back, or input reaching the launcher while RetroArch is in front.
- The log lines from the launch: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Launch|^Boot|error'`.

## M4: a live scrape

This is the M4 acceptance's live scrape of a 50-game set, and the check of the built-in `screenscraper_id` values against ScreenScraper's system list. Both need your own credentials, which the repo never has. It uses the M3 set-up (`C:\OdysseyTest`), so your AppData isn't touched.

1. Put 50 Mega Drive ROMs of your own in `C:\OdysseyTest\ROMs\megadrive` (a mix: well-known games, a few obscure ones, one renamed oddly).
2. Create `C:\OdysseyTest\secrets.toml` with whichever providers you have (leave a section out to see it skipped). A build from source has no built-in developer credentials, so `dev_id` and `dev_password` are needed here; a release carries its own (see "A release's built-in ScreenScraper credentials"):

   ```toml
   [screenscraper]
   dev_id = "..."
   dev_password = "..."
   username = "..."
   password = "..."

   [steamgriddb]
   api_key = "..."

   [igdb]
   client_id = "..."
   client_secret = "..."
   ```

   Keep this file out of the repo. `ODYSSEY_*` environment variables work too (`ODYSSEY_IGDB_CLIENT_SECRET` and so on).
3. Build, then check the providers. Each should say `Ready`, and ScreenScraper should print your account's threads and quota:

   ```powershell
   dotnet build
   $cli = ".\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe"
   & $cli --user-dir=C:\OdysseyTest providers
   & $cli --user-dir=C:\OdysseyTest ss-systems
   ```

   `ss-systems` lists each built-in system's `screenscraper_id` beside ScreenScraper's names for it. Every row should name the right console.
4. Scrape one game and look at it:

   ```powershell
   & $cli --user-dir=C:\OdysseyTest game "megadrive/<a ROM's file name>"
   & $cli --user-dir=C:\OdysseyTest show "megadrive/<the same>"
   ```

5. Scrape the whole set, timed, keeping the output. `--save-responses` keeps each provider's answer in `C:\OdysseyTest\scraped\responses\` (off by default), for step 9 and for debugging a wrong match:

   ```powershell
   Measure-Command { & $cli --user-dir=C:\OdysseyTest --save-responses system megadrive | Tee-Object C:\OdysseyTest\scrape-log.txt } | Select-Object TotalSeconds
   ```

6. Resume: run `& $cli --user-dir=C:\OdysseyTest missing`, press Ctrl+C after a few games, then run `& $cli --user-dir=C:\OdysseyTest resume`. It should carry on with the games left, not start again. (With every game already found, `missing` picks only games without a cover.)
7. Clear one game: `& $cli --user-dir=C:\OdysseyTest clear "megadrive/<a ROM>"`, then `show` it: "Never scraped", no cover.
8. Look at the result in the launcher: `& .\artifacts\export\windows\OdysseyLauncher.exe ++ --user-dir=C:\OdysseyTest` (export first, as in M3). Covers show on the boxes; the details show the scraped metadata.
9. Check that no credential was written anywhere. For each of your values, this finds nothing (`tokens\igdb.json` holds IGDB's access token by design, not your secret):

   ```powershell
   Get-ChildItem C:\OdysseyTest\scraped, C:\OdysseyTest\*.db -Recurse -File | Select-String -Pattern '<value>' -SimpleMatch
   ```

### Send back

- The timing, and the summary lines of `scrape-log.txt` (the `[n/50]` lines and the batch line). They contain no credentials.
- Which games were wrong: not found, matched to the wrong game, or with the wrong cover.
- Any `ss-systems` row that names the wrong console.
- Whether resume carried on, and anything in the output that looked like a credential.

## M6: themes with a controller

This checks what captures can't: switching themes on the real display, the look cross-fading as you enter and leave a system, and a model of your own. It uses the M3 set-up (`C:\OdysseyTest`) with the M5 Mega Drive ROMs.

1. Copy the test theme into the user folder: `Copy-Item -Recurse tests\themes\slot-showcase C:\OdysseyTest\themes\`.
2. Start the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`, and use only the gamepad.
3. **Looks.** Press A on Mega Drive: the background and lights cross-fade to Mega Drive's blue look over about a third of a second while the games come up. B cross-fades back.
4. **Switching.** On the systems grid, press Menu, choose Theme, then Slot Showcase (from M7 the settings choose the theme; Menu used to cycle through them). The cards become square tiles, the background turns plum and teal, and nothing restarts. Close the settings and enter Mega Drive: the games are tall cases with a screenshot panel; games with no screenshot show a test card there. Choose Memory Card the same way to go back.
5. **Your own model.** Quit, copy any `.glb` with a material named `cover` (for example `tests\themes\slot-showcase\models\templates\showcase_case.glb`) to `C:\OdysseyTest\media\megadrive\model\<a ROM's name without its extension>.glb`, start again and press F5 to rescan. Enter Mega Drive: that one game shows your model, the same height as its neighbours, with its cover on the `cover` material.

### Send back

- Anything that differed: a stutter as a theme switches or a look cross-fades, a look that snaps instead of fading, the wrong model or a missing cover on a game, or a model that isn't the size of its neighbours.
- The log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Theme|^Models|^Media|error|warning'`.

## M6 part 2: your own models, the sample theme and clips

This checks what the scripts can't: a model made in Blender (or downloaded) imported for a real game, the sample theme's clips on the real display, and the model log. It uses the M3 set-up (`C:\OdysseyTest`) with the M5 Mega Drive ROMs. Build the tools first (`dotnet build`), and set `$cli = '.\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe'`.

1. **Check a model.** Pick a `.glb` of your own (or export one from Blender as [THEMING.md](THEMING.md#9-making-models-in-blender) says), and run `& $cli --user-dir=C:\OdysseyTest inspect-model <file>`. It prints the triangles, materials and textures against the per-game budget, the slots and clips found, and any warnings. Nothing is changed.
2. **Import it.** `& $cli --user-dir=C:\OdysseyTest import-model --from=<file> "megadrive/<a ROM's file name>"`. It says `Imported:` and where the model went (`C:\OdysseyTest\models\games\megadrive\<ROM file name>.glb`). A textures-too-large model is imported with its textures scaled down (a `note:` line says so).
3. **An OBJ zip.** Zip an `.obj` with its `.mtl` and textures, and import it for another game the same way: `Imported (converted from OBJ)`.
   - **An animated PS2 icon.** Import a PS2 icon database zip (`ICON.ICO.obj` with its `ICON.ICO.anim`) for a PS2 game. The report says `clips focused` and gives the morph targets. In the app, the icon moves only while it's focused, at the speed it has in the PS2 browser.
4. **A bad file.** Import any non-model file renamed to `.glb`: `Rejected: nothing was changed.`, and `& $cli --user-dir=C:\OdysseyTest models-log` shows why.
5. **In the app.** Copy the sample theme: `Copy-Item -Recurse samples\themes\retro-tv C:\OdysseyTest\themes\`. Start the export full screen (`& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`) and use only the gamepad.
   - Enter Mega Drive: your two games show your models, fitted into their cells, with their art on any slot materials.
   - Press Menu on the systems grid, choose Theme, then Retro TV, and close the settings. The cards are consoles whose cartridges rise and settle (the idle clip). The focused console lifts its cartridge higher and wobbles (focused).
   - Enter Mega Drive: every game is a television showing its screenshot (else its cover, else colour bars), with its logo (else its title) on the stand. The focused television's aerials sway. Press A: the television spins and its aerials fold before the emulator starts (at most 2 s).
6. **Clearing removes the model.** `& $cli --user-dir=C:\OdysseyTest clear "megadrive/<the first ROM's file name>"`, then press F5 in the app: that game shows its template again, and its file in `models\games\megadrive\` is gone.

### Send back

- Anything that differed: a model the wrong size or facing the wrong way, art missing from a slot, a clip that doesn't play or snaps back instead of blending, a stutter when a model loads or a clip starts.
- The model log (`& $cli --user-dir=C:\OdysseyTest models-log`), and the `inspect-model` output for any model that looked wrong.

## M7 part 1: the settings screen

This checks what the scripts can't: a real pad, the mouse and a physical keyboard on the Deck, a real network share, a live connection test, and "scrape all missing" with your credentials. It uses the M3 set-up (`C:\OdysseyTest`) with the M5 Mega Drive ROMs, and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`. Before you start, add a comment of your own to `C:\OdysseyTest\settings.toml` and `systems.toml` (a line starting with `#`), to check they survive.

1. **Pad only.** On the systems grid press Menu. Go through every page with the D-pad (hold it: it repeats and speeds up), A to open, B to go back, Menu to close. On Scraping, left and right change the default provider in place; on Fallbacks, A turns one on or off and left and right move it.
2. **A system's ROM folder.** Settings, ROM folders, Mega Drive, then its folder. In the picker: LB and RB page, LT and RT jump by letter, A opens a folder, B goes up (from a drive's root, to the places and drives), X uses the open folder. A "Scanning Mega Drive" card shows when you close the settings. Open `systems.toml`: Mega Drive has `rom_dirs`, and your comment is still there.
3. **A network share.** In a picker, press Y and type `\\<your NAS>\<share>` with the pad (Symbols has `\`), then Menu: it opens. Then type a share that doesn't exist (or unplug the network): "Still opening …" after a couple of seconds, the app keeps moving, and B stops waiting. The places and drives list shows your mapped drives with their shares, and a disconnected one as disconnected.
4. **Emulators.** Settings, Emulators, a RetroArch profile, then your `retroarch.exe`: it asks whether to change all the RetroArch profiles; choose All. `settings.toml` now has `retroarch` under `[variables]`, with your comment still there. Launch a Mega Drive game: it uses the new path.
5. **Keyboard and mouse.** With a physical keyboard: Escape (or F1) on the systems grid opens the settings; the arrows move, Enter chooses, Escape goes back; in the on-screen keyboard, type straight in, Ctrl+V pastes, Enter is Done. With the mouse: click rows and buttons, scroll lists with the wheel, and double-click a folder in the picker.
6. **Credentials.** Settings, Scraping, then each provider: enter your credentials (Paste helps with keys), then Test connection: "Connected", and for ScreenScraper your quota for today. They show as dots. `secrets.toml` holds them, and no other file does.
7. **Scrape all missing.** Settings, Scrape all missing metadata: the question gives the count per system and says which providers will be used. Start it and close the settings: the card top right shows its progress while you browse. Cancel it in the settings (the job's row under Library, A).
8. **Theme.** Settings, Theme, Retro TV: it switches at once. Quit and start again: still Retro TV.

### Send back

- Anything that didn't answer the pad, the mouse or the keyboard, any frame that froze, any message that was unclear, and any config file whose comments or layout changed beyond the value you set.
- The log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Settings|^Scan|^Scrape|^Theme|error|warning'`.

## M7 part 2: item options

This checks what the scripts can't: a real pad on the options panels, and a live "scrape this game" and "scrape this system" with your credentials. It uses the M3 set-up (`C:\OdysseyTest`) with the M5 Mega Drive ROMs and your credentials from M7 part 1, and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`. Keep two or three images of your own (PNG or JPEG) and a `.glb` somewhere handy.

1. **A game's options.** Enter Mega Drive, focus a game and press X. Move with the D-pad, A to choose, B to go back. With a physical keyboard, O opens them too.
2. **Scrape this game.** Choose it: every provider's results are listed (see [Manual matching](#manual-matching)); press A on the right one. The panel says "Scraping …", then which provider found it. Press B: the game's box shows its scraped cover at once, and the details (bottom left) its metadata.
3. **Your own images.** Images: a card per slot shows the scraped art and its file. Choose the front cover, pick one of your images in the picker (it shows a preview), then do the same for the back. Close the options: the box shows your cover straight away, and `C:\OdysseyTest\media\megadrive\cover\` holds only yours. Scrape this game again: your cover stays. Reopen Images, focus your cover and press Y, then Remove it: the slot is empty. Scrape this game again: the scraped cover comes back.
4. **Metadata.** Edit the title and metadata, then Title: type a new title on the on-screen keyboard and press Menu. The grid shows the new title when you close the options (and the game moves if it now sorts elsewhere). Try Released with nonsense: it's refused with the formats it takes. Focus a field you changed and press Y: it's the scraped value again.
5. **Emulator and model.** Emulator: choose another profile; launch the game: it uses that one. Model: choose your `.glb`; the box becomes your model. Y on Model removes it.
6. **Clear metadata.** Read the question (it says your images go too), then Clear it. The game shows a plain box and its file-name title, and your image files for it are gone from `C:\OdysseyTest\media\megadrive\`.
7. **A system's options.** On the systems grid, focus Mega Drive and press X. Game template: choose `jewel_case`; the theme reloads and Mega Drive's games are jewel cases. Choose "The theme's choice" to put it back. Scrape this system: the question says how many games, and which providers; start it, close the options and watch the progress card while the boxes fill in.

### Send back

- Anything that didn't answer the pad, any frame that froze while a panel saved or loaded, any message that was unclear, and any change that needed a restart or a rescan to show.
- The log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Options|^Titles|^Media|^Scrape|^Theme|error|warning'`.

## The power menu

This checks what a script mustn't do: restart, shut down and sleep the PC from the launcher. Save your work in other apps first. It uses the M3 set-up (`C:\OdysseyTest`) and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`. Use the gamepad.

1. **Opening and closing.** On the systems grid, press View: the Power menu shows Restart system, Shut down system, Sleep system and Quit app, with Restart focused. B closes it, and so does View again. Enter a system and press View: it opens there too. With a keyboard, P opens it.
2. **Sleep.** Choose Sleep system: the PC sleeps within a few seconds. Wake it: the launcher is where you left it, and the button that woke the PC didn't act in it. (On a Modern Standby PC the row is dimmed and says why; tell me if yours is.)
3. **Quit.** Choose Quit app: the launcher closes straight away.
4. **Restart.** Start the launcher again and choose Restart system: the launcher closes and Windows restarts, as it does from the Start menu (an app with unsaved work holds it up and asks).
5. **Shut down.** After the restart, start the launcher and choose Shut down system: the PC turns off.

### Send back

- Anything that differed: a row that did nothing, a "Couldn't …" message (with its text), or the launcher still open after a restart or shutdown started.
- After step 2, the log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Power|error|warning'`. (The log is rewritten each run, so steps 4 and 5 leave nothing to send.)

## The ES-DE catalogue and launching shortcuts

This checks what the scripts can't: the grid and settings with the whole catalogue, and a real shortcut or script as a game. It uses the M3 set-up (`C:\OdysseyTest`) and the export.

1. **Only what you have.** Start the launcher with your ROM folders: the systems grid shows the systems that have games (Favourites and Recently played first), not the other 150 or so. Settings, then Emulators, lists only the programs those systems use. In `C:\OdysseyTest\config\settings.toml` set `[display]` `hide_empty_systems = false`, restart: every system has a card, empty ones with "0 games".
2. **ES-DE folders.** Put a ROM in a folder named `genesis` (and none in `megadrive`): the Mega Drive system finds it after a rescan (View, then F5, or Settings, Library).
3. **A shortcut as a game.** Make `ports\Notepad.lnk` (a shortcut to notepad.exe) under your ROM root and rescan. Ports shows it; launch it: Notepad opens in front of the launcher's running screen, and when you close Notepad the launcher comes back with focus. A script, `ports\Hello & World.bat` containing `@pause`, does the same (a console window; any key ends it), and nothing after the `&` runs as a separate command. A file with a `%` in its path says so and doesn't start.
4. **A catalogue emulator.** Install one the catalogue lists (for example Stella under `C:\Emulators\Stella\64-bit\`, the folder ES-DE looks in), put an Atari 2600 ROM in `atari2600`, and launch it: Stella opens that game. Set another emulator on Atari 2600's page (X on its card) and launch again.

### Send back

- Any system or emulator that behaved differently from ES-DE, and the log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Launch|doesn.t exist|error|warning'`.

## Windows and Steam games

This checks what the scripts can't: a real Steam game handed to Steam and followed until you quit it, with the focus coming back. It uses the M3 set-up (`C:\OdysseyTest`) and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`. Steam must be installed and signed in, with at least one game installed.

1. **Shortcuts.** In Steam, right-click an installed game, then Manage, Add desktop shortcut. Move the `.url` from your desktop into `steam\` under your ROM root. Put a shortcut to a program (for example Notepad) in `windows\`. Rescan (F5): Steam and Windows have cards, each game titled by its file's name.
2. **A Steam game.** Launch the Steam game: Steam starts it (it may sync saves first), the launcher shows its running screen, and the game takes the foreground. Play for a minute, then quit the game from its own menu: within a few seconds the launcher comes back with focus, and the game's details show one play with about the time you played.
3. **Steam closed.** Exit Steam completely (Steam, then Exit), and launch the game again: Steam opens, signs in and starts the game, and the launcher keeps its running screen until you quit it, then comes back. Steam stays open.
4. **Never started.** Launch a game Steam has uninstalled (make a shortcut first, then uninstall it in Steam): Steam offers to install it. Close that dialog: about 2 minutes later the launcher comes back and says Steam didn't start the game and that it isn't installed. It isn't counted as a play.
5. **Windows.** Launch the Notepad shortcut from Windows: Notepad opens, and the launcher comes back with focus when you close it.

### Send back

- Anything that differed, especially the launcher coming back while the game still ran (or staying away after it ended), and the log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Launch|error|warning'`.
- If a game ended too early or too late: run `Get-ItemProperty HKCU:\Software\Valve\Steam | Select RunningAppID` and `Get-ItemProperty HKCU:\Software\Valve\Steam\Apps\<app id>` while the game runs and after it ends (the app id is the number in the `.url`).

## Scraped media kinds

This checks what the fixtures can't: that ScreenScraper really names its media as the scraper expects (`box-2D-back`, `box-2D-side`, `ss`, `wheel-hd`, `fanart`, `support-texture`, `video-normalized`, `manuel`), and the Media page on a real pad. It uses the M3 set-up (`C:\OdysseyTest`) with the M5 Mega Drive ROMs and your credentials from M7 part 1, and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`.

1. **The Media page.** Settings, then Providers, media and credentials, then Media to scrape. Front cover, box back, box spine, screenshot and wheel say Yes; fan art, support texture, video and manual say No. Turn on fan art, support texture, video and manual (A, or right). `C:\OdysseyTest\settings.toml` now has a `media` line under `[scraping]` listing all nine, and your own comments are still there.
2. **Scrape a game.** Close the settings, press X on a well-known game (Sonic the Hedgehog 2), then Scrape this game. Then Images: the back, spine, screenshot, logo, hero art and disc or cartridge label cards show ScreenScraper's art.
3. **The files.** `Get-ChildItem C:\OdysseyTest\media\megadrive -Recurse -File | Select Directory, Name, Length`: a file named `Sonic the Hedgehog 2 (World).<ext>`, without the ROM's `.md`, in `covers`, `backcovers`, `spines`, `screenshots`, `logos`, `heroes`, `labels`, `videos` (an `.mp4` of a few MB that plays in a video player) and `manuals` (a `.pdf` that opens in a PDF reader), and none new in `box_texture`.
4. **Off again.** Turn video off on the Media page and scrape another game: no `.mp4` for it.

### Send back

- Any kind that didn't arrive for a game ScreenScraper's website shows it for, and the warnings: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern 'screenscraper.*(download|isn.t)'`.

## Steam store scraping

This checks what the fixtures can't: Steam's live store answering searches, its art arriving, and its titles matching your shortcuts' names. It needs no credentials. It uses the M3 set-up (`C:\OdysseyTest`) with the Steam shortcuts from [Windows and Steam games](#windows-and-steam-games), and the scrape CLI built with `dotnet build`: `$cli = '.\tools\scrape-cli\bin\Debug\net8.0\odyssey-scrape.exe'`.

1. **Opt in.** Under `[scraping]` in `C:\OdysseyTest\settings.toml`, set `provider = "steam"` and `fallback = ["screenscraper", "igdb", "steamgriddb"]`, and add `"hero"` to `media`. `& $cli --user-dir=C:\OdysseyTest providers` lists "Steam store: Ready" first. (Or in the app: Settings, Providers, media and credentials, Default provider, then right until it says Steam store; Steam store's own page says no credentials are needed, and Test connection says "The Steam store answered.")
2. **One game.** `& $cli --user-dir=C:\OdysseyTest game "steam/<a shortcut>.url"`, then `show` for it: the title, description, developer, publisher and release date are Steam's, the metadata source is `steam`, and the cover, hero, logo and screenshot are from `steam`. Genre and players come from ScreenScraper or IGDB.
3. **Every game.** `& $cli --user-dir=C:\OdysseyTest system steam`, and the same for `windows` if it has shortcuts to games. Note the time and any games not found.
4. **Not a Steam system.** Scrape a Mega Drive game: the log has no `steam:` lines and nothing changed for it.
5. **In the app.** In the export, the Steam system's cards show Steam's library capsules, and a game's Images show its hero and logo.

### Send back

- Games matched to the wrong Steam game, and games not found with their file names (a game Steam no longer sells isn't found: that's expected).
- The `steam:` warnings: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern 'steam:'`, or the CLI's output.

## Manual matching

This checks what the fixtures can't: each provider's live search results, and scraping with the games you chose. It uses the M3 set-up (`C:\OdysseyTest`) with the M5 Mega Drive ROMs, your credentials from M7 part 1, and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`. A game whose file name isn't the game's name helps (rename a copy of a ROM to `Zz Mystery.md`, then rescan with F5).

1. **The search.** Focus a Mega Drive game, press X, then Scrape this game. "Search for" shows its title, and after a moment each provider has a section of results, the closest name first, with the year, the id and how close the name is. A game scraped before has its match marked "In use". Providers without credentials, and the Steam store, are under "Couldn't be searched", saying why.
   **Covers.** Each result has its cover on the left: "…" at first, then each provider's filling in from the top of its list within a few seconds (SteamGridDB's last: one request each). A result with no cover says "No cover". Look for a game with namesakes (Sonic the Hedgehog: the Mega Drive game, the 2006 one, the Master System one) and check you can tell them apart. Press B and Scrape this game again: the covers show at once (nothing is downloaded again). A warning in the log beginning `Match:` names a cover that failed to download; it must never show a password or `devpassword`.
2. **Another name.** On `Zz Mystery`, nothing matches. Press X, type the game's real name, Done: every provider is searched again.
3. **Choose.** Press A on the right result: the options say "Scraping …", then which providers found it. Close the options: the box shows the art of the game you chose, and the details its metadata.
4. **Another provider's game.** Scrape this game again and press A on an IGDB result: its cover and description now show (ScreenScraper's fill in only what IGDB lacks, such as the spine). Do it once more with the ScreenScraper result: ScreenScraper's are back.
5. **Correcting a match.** On a game matched to the wrong game, choose the right one. The wrong game's images (a back or spine the right one lacks too) are gone, not left behind.
6. **It sticks.** Scrape Mega Drive from its options (X on the system): the games you matched keep the games you chose. Clear metadata on one, then Scrape this game: nothing is marked "In use" (your choice went with the clear).
7. **Arcade sets by their MAME names.** With Arcade's `rom_dirs` on your sets (`S:\Arcade`), Scrape this game on `1on1gov`, `3stooges` and `3wonders`. ScreenScraper's first result is the real game (1 On 1 Government, The Three Stooges In Brides Is Brides, Three Wonders), saying "matches the file's name" (or "contents"), even though "Search for" shows the short name. The log's `Match:` line says `screenscraper <n> (file: <id> by filename)`.
8. **Not found, saved.** Start the export with `--save-responses` added, and scrape Arcade from its options. For each game not found, `C:\OdysseyTest\scraped\responses\screenscraper\arcade\<file>.json` holds ScreenScraper's answer to the file lookup and what the title search found.

### Send back

- Games whose right result wasn't listed, with the name searched for, and any provider whose results looked wrong (wrong system, wrong names).
- Arcade sets whose file match was missing or wrong, and the `not_found` response files from step 8 (zip `scraped\responses\screenscraper\arcade`).
- Anything that took long or didn't answer the pad, and any message that was unclear.
- The log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Match|^Scrape|error|warning'`.

## Status indicators

This checks what a capture can't: the indicators following the device's real state as it changes. Use the Deck (or a laptop) and the export: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen`.

1. **What shows.** In the top-right corner you see the network, the battery's charge, and the time in your Windows time format (24-hour or 12-hour, as Windows' clock shows it).
2. **The battery.** Plug the charger in and out. Within 10 s, the icon changes to the charging one (green) and back. Below 10% on battery, it turns red.
3. **The network.** Turn Wi-Fi off: within a few seconds the crossed-out Wi-Fi icon (dimmed) shows. Turn it back on: it returns, with its bars. On the dock with a cable, the cable icon shows. Walk away from the router: the bars drop.
4. **The clock.** Watch the minute change: the clock follows within a second. Sleep the Deck for a few minutes, then wake it: the time is right at once.
5. **The settings.** Open Settings (Menu). In the UI section, turn Clock, Battery and Network off and on, with A and with left and right. Each one disappears and comes back at once, top right, and the others close up against the right edge with no gap. Close Settings and restart the app: your choices are kept.
6. **A game.** Launch a game and quit it. The indicators are still right, including the time.

### Send back

- Any state that showed wrong or late: which one, what it showed, and what Windows' own tray icons showed.
- A Wi-Fi signal that never shows bars (all arcs bright, always): the WLAN service couldn't answer.

## A game's details and videos

This checks what a capture can't: a real pad's L3, and a video's sound. Use the export on a library with scraped art and videos (`[scraping] media` with `video`, then scrape a system), on the Deck or a PC with speakers.

1. **The screen.** In a system's games, press Y on a game. Its details open: its whole description, then every field it has, in two columns, and its file. Up on the pad moves to the details block (it lights up); up and down scroll a long description, and down at its end goes to the cards. Y or B goes back to the grid.
2. **Images.** Along the bottom is a card for each image and the video, with a thumbnail (a video's shows a frame from a little way in, with a play mark). Press A on the front cover: it fills the window on black, with no status icons. Left and right go through the others; the caption at the bottom fades after a few seconds and comes back with any button. B goes back to the details.
3. **The video.** Video is the first card, then the front cover and the screenshot. Press A on Video. It plays at full size with its sound, in step with the picture (watch a hit or an explosion). A pauses it, picture and sound together; A again carries on. Let it finish: "A Play again" shows, and A plays it from the start. Left goes back to the images while it plays, and the sound stops at once.
4. **A video Windows can't play.** On a game whose video is H.264 4:4:4 (about a fifth of ScreenScraper's arcade videos), the card says it can't be played, and A shows why, full screen.
5. **The favourite.** In the details, press L3: "Added to your favourites." shows, and Favourite says Yes. Go back: "Favourite" shows top right of the grid. L3 in the grid takes it out again.

### Send back

- A video whose sound drifts away from its picture, or stutters: which game, and whether it was on the Deck or docked.
- A video that wouldn't play with a reason that isn't the 4:4:4 one: the reason it gave.

## Turning an item with the right stick

This checks what a capture can't: a real stick's feel (its speed, its deadzone, and a stick that drifts). Use the export on the Deck, with only the pad.

1. **A game.** In a system's games, push the right stick right: the focused game turns round its vertical, the front going right, slowly with the stick a little way over and fast at its edge; it stops swaying. Left turns it back and keeps going round. Up tips its front up towards the top of the screen, down the other way; either stops before it turns over. It turns in place, about its middle, and nothing else moves.
2. **Let go.** Let the stick go: the game stays where you left it, and holds still. A resting stick (or one that drifts a little) turns nothing.
3. **Moving on.** Move the focus with the D-pad or the left stick: the game you left goes back square at once, and the new one starts square, swaying. Go back to the first: it's square.
4. **A system.** Back on the systems grid, the right stick turns the focused system's card (or console) the same way, and moving on sets it square.
5. **Elsewhere.** With the settings, a game's options or its details open, the right stick does nothing to the grid behind. Launch a game: the item spins up and flies forward as before, whether or not you'd turned it.

### Send back

- A speed that feels wrong (too fast to aim, or too slow to go round), which way up and down should turn it if it feels backwards, and an item that turns by itself with the stick at rest.

## Inspecting a game with R3

This checks what a capture can't: a real pad's R3 (pressing the right stick), and whether pressing it turns the game too. Use the export on the Deck, with only the pad.

1. **Inspect.** In a system's games, press R3: the focused game moves to the middle of the screen, facing you, and grows until it's nearly as tall as the screen. The rest of the grid stays where it was, behind it. The game isn't faded at the top or bottom of the screen.
2. **Turn it.** Push the right stick: the big game turns in place, as it does in the grid. Pressing R3 can nudge the stick, so watch whether the game turns a little as you press it.
3. **Back with R3.** Press R3 again: the game goes back to its place in the grid, swaying.
4. **Back with B.** Inspect again and press B: the game goes back, and you're still in the system's games. B again goes back to the systems.
5. **Back by moving.** Inspect again and move the focus with the D-pad: the game goes back as the next one is focused, at its normal size.
6. **Play.** Inspect a game and press A: it spins up from where it is and the game starts. After it ends, the game is still inspected; R3 or B puts it back.

### Send back

- A game that leaves the screen when inspected without being turned (which system and game), one that's clearly smaller than the screen, and whether the size feels right on the Deck and docked.
- Whether pressing R3 turns the game noticeably.

## A system's details

This checks what a capture can't: a real pad on the screen, and how the model looks on the Deck and docked. Use the export on your own library, with the console theme.

1. **The screen.** On the systems grid, press Y on Mega Drive. Its details open: the console on the left, large, on Mega Drive's background, with the cartridge going in as it does when focused in the grid; on the right its whole description, then its details (maker, year, games, last scan, emulator and alternatives, ROM folder, file types, view, sort, models, ScreenScraper and IGDB ids). Y or B goes back to the grid, on Mega Drive.
2. **Scrolling.** Up and down scroll the description and details; LB and RB a page at a time.
3. **Turning.** Push the right stick: the console turns as it does in the grid, and stays turned when you let go. Left and right on the D-pad turn it a step at a time, held to keep turning.
4. **Others.** Try Game Gear and Game Boy (the console theme's other consoles), a system with a memory card (its name on the label), and Favourites and Recently played (their games counted). A system whose ROM folder you set in the settings lists that folder.
5. **Docked.** Docked to the 4K display, open Mega Drive's details: the console is as sharp as the grid's items, not blurred.

### Send back

- A model cut off at the frame's edge (which system), or one that looks much smaller than the others.
- A field that's wrong for your setup (a folder, an emulator, a sort), with what it said.

## Deleting a game

This checks what a capture can't: deleting from a network share, and your own playlists. **Use copies, never the only copy of a game:** a deleted file doesn't go to the Recycle Bin. Copy a multi-disc game (an `.m3u` with its `.cue`/`.bin` or `.chd` discs) and a single-file game into a writable folder on the NAS that a system's `rom_dirs` lists, and rescan.

1. **The question.** X on the multi-disc game, then down to the last row, "Delete this game" (in red: "Deletes <name>.m3u and every file it lists"). A: the question lists the `.m3u`, then its discs and their tracks, the size and the folder, and starts on "Keep it". B, or "Keep it", leaves everything as it was.
2. **Delete.** Again, then left to "Delete it" and A. The options close, the game is gone from the grid and the focus is on the next game. In Explorer, the `.m3u`, its discs and their tracks are gone, and so is their own folder if nothing else was in it; nothing else in the ROM folder is touched.
3. **A single file.** Delete the single-file game the same way.
4. **A read-only share.** On a system whose folder is on the read-only share (`S:\`), try to delete a game: "Not deleted" says why, and the game stays in the grid.
5. **Coming back.** Copy the deleted single-file game back and rescan: it comes back with its art, favourite and play history.

### Send back

- A file the question listed that shouldn't go (or one missing from it), with the playlist's lines.
- Anything left behind in the ROM folder after step 2.

## A release's built-in ScreenScraper credentials

A release carries ScreenScraper's developer credentials (ARCHITECTURE.md A5, "Secrets"), written by the release workflow from the repository's secrets, so a user only enters their own account. Only a release built by the workflow has them: a script can't check them against ScreenScraper without a network call.

1. Run the release workflow by hand (Actions > Release > Run workflow), or push a tag, and unzip its `OdysseyLauncher-<version>-windows-x86_64.zip`. In the log, "Built-in credentials" should say it wrote the file, and "Build and test" should pass (`BuiltInAccountsTests` fails if the file wasn't compiled in).
2. Use an empty user folder, so your own `secrets.toml` isn't read: `.\OdysseyLauncher.exe -- --user-dir=C:\OdysseyRelease`.
3. Open Settings > Scraping. ScreenScraper should say `Ready, anonymous`. Its page should list only "Your account" (username and password): no developer credentials. Then add `dev_id = "x"` under `[screenscraper]` in `C:\OdysseyRelease\secrets.toml`, reopen the page, and check nothing changes (after Test connection, the log says it's ignored).
4. Test connection: it should connect, as an anonymous user.
5. Set your username and password, then test again: it should connect with your account's threads and quota, and ScreenScraper should now say `Ready`.
6. Scrape one game (X on it, then scrape) and check it gets its metadata and cover.
7. Look for the credentials where they mustn't be: `Get-ChildItem C:\OdysseyRelease -Recurse -File | Select-String -Pattern '<your dev password>' -SimpleMatch` finds nothing, and neither does the same over `"$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs"`.

### Send back

- Any step that differed, especially a ScreenScraper refusal at step 4 (the message it gave), or a credential found at step 7 (which file).

## Importing an ES-DE gamelist

An import copies a whole system's media off the NAS (the NES folder has 4.7 GB of videos), so it's yours to run. Use a user folder of its own, so your library isn't changed: `C:\OdysseyGamelist\systems.toml` with `[systems.nes]` and `rom_dirs = ['S:/Nintendo Entertainment System']`, then `godot --path godot -- --user-dir=C:\OdysseyGamelist` (or the export, with `-- --user-dir=...`).

1. **Find it.** Once NES is scanned, X on it, then down to Import > "Import gamelist.xml". The question names `S:\Nintendo Entertainment System\gamelist.xml` and says all 1,196 of its games are in the library, how many get metadata, about 1,150 of each kind of file (and its manuals, if the gamelist names any), and the ScreenScraper matches.
2. **Import.** Choose Import, then B back to the grid. The progress card counts files; titles change at once (Adventure Island 2 becomes Adventure Island II), and covers appear in the grid as the import goes. It should take about a quarter of an hour.
3. **Cancel and finish.** Cancel the card part way (its Cancel), then import again: the question now offers only what's left, and the import finishes it.
4. **A game.** Y on 720 Degrees: its description, release date (1 November 1989), developer, publisher, genre and players, "Metadata: Yours", and cards for its video (it plays), front cover, screenshot and logo. X > Metadata shows the values as yours.
5. **Nothing moved.** In Explorer, `S:\Nintendo Entertainment System\images` and `videos` still have their files (the share is read-only anyway); the copies are in `C:\OdysseyGamelist\media\nes\{covers,screenshots,logos,videos,manuals}\`, named without the ROM's extension (`720 Degrees (USA).png`), as ES-DE names them.
6. **Again.** Import once more: "Nothing new to import".

### Send back

- The question's numbers at step 1, and the card's outcome at step 2, with how long it took.
- A game whose title or art came out wrong, with its `<game>` entry.

## Preferred regions and partial system scrapes

A live scrape needs your credentials, so it's yours to run. Use a user folder of its own with a system you've scraped before (the M7 part 2 set-up, `C:\OdysseyTest`, with Mega Drive, is fine).

1. **Regions.** Settings, then Providers, media and credentials, then Preferred regions: Europe 1st, World 2nd, USA 3rd, Japan 4th, the rest Off. Move USA up twice (left, or its ↑): it's 1st, the focus stays on it, and `settings.toml` has `regions = ["us", "eu", "wor", "jp"]`. Turn Japan off and United Kingdom on. Turning off the last one left says it needs at least one.
2. **A region at work.** X on a game with different US and European covers (Sonic the Hedgehog 3, say), Clear metadata, then Scrape this game: the cover is the US box. Put Europe first again and repeat: the European box.
3. **No front cover.** On Mega Drive's options, delete one game's cover file in `media\megadrive\covers\` first and rescan (F5). "Scrape games without a front cover" says 1 game of the system's; start it. Only that game is scraped (the progress card counts 1), and it gets its cover back.
4. **No screenshot.** With Screenshot on under Media to scrape, "Scrape games without a screenshot" counts the games without one; start it, then open it again: the count is now the games no provider has a screenshot for.
5. **Not scraped recently.** Right after step 4, "Scrape games not scraped in the last 30 days" counts only the games steps 2 to 4 didn't scrape; with every game scraped today it says there's nothing to scrape.

### Send back

- Step 2's covers, and each step's count and the card's outcome.
- ScreenScraper's quota (the providers page) before and after step 3, to show only the one game was asked for.

## Moving the media folder

Moving between drives copies every file, so it's yours to run on real media. Use a user folder of its own with media in it (the gamelist test's `C:\OdysseyGamelist`, or `C:\OdysseyTest` once scraped), and a second drive or a USB stick with room for it.

1. **The page.** Settings, then Media folder: the folder is `<user folder>\media`, "Use the default folder" says In use, and the note counts its files and size.
2. **Another drive.** Change, open the other drive, make a folder there in Explorer (`E:\Launcher media`), choose it. The question says how many files and that each is copied, then deleted from the old folder. Choose Move it there: the dialog counts files and bytes, then says how many moved. `settings.toml` has `media = "E:/Launcher media"`, the old folder's system folders are gone, and the grid's covers, a game's details (its video plays) and its images (X, then Images) all show.
3. **Stop.** Change back to the default and Stop part way: "Not moved", everything still on the other drive, nothing in the old folder but empty folders, `settings.toml` unchanged.
4. **Back.** Use the default folder again and let it finish: the media is back in `<user folder>\media`, and `media` is gone from `settings.toml`.
5. **Use it as it is.** Copy the media folder to the other drive in Explorer, then choose that copy and Use the folder as it is: the library rescans, and everything still shows.
6. **Busy.** Start "Scrape all missing metadata", then open Media folder and choose Change: it says to wait for scraping to finish.

### Send back

- Step 2's file count and how long it took, with the drive types (SSD, USB stick, share).
- Anything that showed a placeholder afterwards, with its file.

## Graphics settings

This checks what the scripts can't: exclusive fullscreen around a real emulator, and Vulkan on your PCs. It uses the M3 set-up (`C:\OdysseyTest`) and the export, started without window arguments so settings.toml's screen mode applies: `& .\artifacts\export\windows\OdysseyLauncher.exe ++ --user-dir=C:\OdysseyTest`. Use the gamepad.

1. **Screen modes.** Settings, then Graphics. Step Screen mode with left and right through Fullscreen, Borderless and Windowed: each applies at once (a window is centred at Window size). In Windowed, step Window size: the window follows, never bigger than the screen.
2. **Exclusive fullscreen and a game.** Choose Fullscreen, close the settings and launch a Mega Drive game: the emulator takes the screen (it may flash black once), and when you quit it the launcher comes back in exclusive fullscreen, with focus. Alt+Tab away and back once while browsing: the launcher returns as it was.
3. **3D resolution.** Back in Borderless, step 3D resolution through Automatic, Native and the heights: the boxes get softer or sharper, the menus and text don't.
4. **Vulkan.** Choose Video driver, Vulkan: the row says "From the next start", and a question offers to restart. Choose Restart now: the launcher closes and opens again, and the row now says "Running now". `override.cfg` beside the executable has the driver line. Browse and launch a game as in step 2.
5. **Back to Direct3D 12.** Choose Direct3D 12 and Later, then quit and start the launcher: it runs Direct3D 12, and `override.cfg` is gone.
6. **FPS and VRAM.** Turn Show FPS and VRAM on: a line under the clock shows the frame rate and the video memory, updating once a second, over the settings too.

### Send back

- Anything that differed, especially the launcher not coming back in exclusive fullscreen after step 2, or not restarting in step 4.
- Step 6's VRAM on each driver, and the log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Display|^Launch|error|warning'`.

## Windows' full screen experience

This checks what only a reboot can: the launcher coming back after a full-screen game when Windows starts straight into the full screen experience (2026-10-09 in ARCHITECTURE.md's decisions log). There, the shell hides (cloaks) the windows behind a full-screen game and, after a boot into it, doesn't show the launcher again when the game ends, so the launcher minimises and restores itself. It needs a machine whose full screen experience is set to start at sign-in, and the launcher with a RetroArch system.

1. **A RetroArch game.** Restart into the full screen experience, start the launcher, and launch a game through RetroArch (it starts full screen). Quit RetroArch: within about a second the launcher is back with focus, never a black screen that stays until you switch apps.
2. **Another.** Launch a game on a different system through RetroArch, and quit it: the same.
3. **A program.** Launch a program from Windows (a shortcut to Firefox, say) and close it: the launcher comes back.
4. **After desktop mode.** Switch to desktop mode and back to the full screen experience without restarting, and repeat step 1: the same.

### Send back

- Anything that differed, and the log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Launch|error|warning'`. `the launcher window is shown again, <n> ms after the game ended` means the shell had hidden it and the minimise and restore showed it; `Launch window (...)` lines describe the windows when it didn't come back cleanly.
