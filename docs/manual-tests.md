# Manual tests

Checks that a script can't observe. Each says what to run, what should happen, and what to send back. Automated checks are in `tools/verify.ps1`.

## M3: launching a real emulator, and focus

This checks what the fake emulator can't: a real emulator taking the foreground, the launcher minimising and idling while the game runs, and the launcher coming back to the front with keyboard focus afterwards. Windows' focus-stealing rules make the last part the one most likely to go wrong, and they behave differently with keyboard and gamepad input, so both are tested.

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
- Don't Alt+Tab to check on the launcher: switching windows is user input, and it changes what Windows allows afterwards. The log shows whether it minimised (`the emulator took the foreground after <n> ms, so the launcher minimised`).

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
- A console window flashes up for a moment: that's the stub, because the fake emulator is a console program. The stub exits within a fraction of a second. The launcher must still treat the game as running: it stays minimised until RetroArch itself quits, and only then comes back.
- RetroArch must still come to the front with keyboard focus. It's a grandchild the launcher didn't start directly, which is why the launcher lets any process take the foreground at launch.
- The log's `ended after <n> s` should match your play time, not a fraction of a second.

Delete `systems.toml` afterwards.

### D. Failure messages

Each should leave the launcher in front, not minimised, with a message at the top of its window for 10 s, and a `Launch failed:` line in the log. Adding `--quit-after-launch` after `++` makes the launcher exit with code 1 after the failure (`$LASTEXITCODE`).

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

1. **Systems grid.** The launcher opens on the systems grid with a system focused (the first one with games). Its name and details are top and bottom left.
   - The D-pad and the left stick move the focus. Held, a move repeats after about a third of a second, then speeds up over the next second and a half.
   - LB and RB move four rows at a time.
   - View opens the power menu (see [the power menu](#the-power-menu)); B closes it. Rescanning is in the settings: Menu, then Rescan the library. A "Scanning your ROM folders" card shows top right with its progress (M7), then the counts update.
2. **Games grid.** Press A on Mega Drive.
   - The systems grid flies towards you and fades while the games come up from behind: clamshell cases with your ROMs' titles, and plain boxes (no art until M4).
   - The title top left follows the focus. After a moment, the details bottom left fill in (Played: Never, Region...).
   - LT and RT jump between letters.
   - Y adds a favourite: "Favourite" shows top right. Y again removes it.
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
2. Create `C:\OdysseyTest\secrets.toml` with whichever providers you have (leave a section out to see it skipped):

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
5. **Keyboard and mouse.** With a physical keyboard: Escape (or F1) on the systems grid opens the settings; the arrows move, Enter chooses, Escape goes back; in the on-screen keyboard, type straight in, Ctrl+V pastes, Enter is Done. With the mouse: click rows and buttons, scroll lists with the wheel, double-click a folder in the picker, and use each screen's Back or Cancel button.
6. **Credentials.** Settings, Scraping, then each provider: enter your credentials (Paste helps with keys), then Test connection: "Connected", and for ScreenScraper your quota for today. They show as dots. `secrets.toml` holds them, and no other file does.
7. **Scrape all missing.** Settings, Scrape all missing metadata: the question gives the count per system and says which providers will be used. Start it and close the settings: the card top right shows its progress while you browse. Cancel it with the card's Cancel button (mouse), or in the settings (the job's row, A).
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
3. **A shortcut as a game.** Make `ports\Notepad.lnk` (a shortcut to notepad.exe) under your ROM root and rescan. Ports shows it; launch it: Notepad opens, the launcher minimises, and when you close Notepad the launcher comes back with focus. A script, `ports\Hello & World.bat` containing `@pause`, does the same (a console window; any key ends it), and nothing after the `&` runs as a separate command. A file with a `%` in its path says so and doesn't start.
4. **A catalogue emulator.** Install one the catalogue lists (for example Stella under `C:\Emulators\Stella\64-bit\`, the folder ES-DE looks in), put an Atari 2600 ROM in `atari2600`, and launch it: Stella opens that game. Set another emulator on Atari 2600's page (X on its card) and launch again.

### Send back

- Any system or emulator that behaved differently from ES-DE, and the log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Launch|doesn.t exist|error|warning'`.

## Windows and Steam games

This checks what the scripts can't: a real Steam game handed to Steam and followed until you quit it, with the focus coming back. It uses the M3 set-up (`C:\OdysseyTest`) and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`. Steam must be installed and signed in, with at least one game installed.

1. **Shortcuts.** In Steam, right-click an installed game, then Manage, Add desktop shortcut. Move the `.url` from your desktop into `steam\` under your ROM root. Put a shortcut to a program (for example Notepad) in `windows\`. Rescan (F5): Steam and Windows have cards, each game titled by its file's name.
2. **A Steam game.** Launch the Steam game: Steam starts it (it may sync saves first), the launcher minimises, and the game takes the foreground. Play for a minute, then quit the game from its own menu: within a few seconds the launcher comes back with focus, and the game's details show one play with about the time you played.
3. **Steam closed.** Exit Steam completely (Steam, then Exit), and launch the game again: Steam opens, signs in and starts the game, and the launcher stays minimised until you quit it, then comes back. Steam stays open.
4. **Never started.** Launch a game Steam has uninstalled (make a shortcut first, then uninstall it in Steam): Steam offers to install it. Close that dialog: about 2 minutes later the launcher comes back and says Steam didn't start the game and that it isn't installed. It isn't counted as a play.
5. **Windows.** Launch the Notepad shortcut from Windows: Notepad opens, and the launcher comes back with focus when you close it.

### Send back

- Anything that differed, especially the launcher coming back while the game still ran (or staying away after it ended), and the log lines: `Select-String -Path "$env:APPDATA\Godot\app_userdata\Odyssey Launcher\logs\godot.log" -Pattern '^Launch|error|warning'`.
- If a game ended too early or too late: run `Get-ItemProperty HKCU:\Software\Valve\Steam | Select RunningAppID` and `Get-ItemProperty HKCU:\Software\Valve\Steam\Apps\<app id>` while the game runs and after it ends (the app id is the number in the `.url`).

## Scraped media kinds

This checks what the fixtures can't: that ScreenScraper really names its media as the scraper expects (`box-2D-back`, `box-2D-side`, `ss`, `wheel-hd`, `fanart`, `support-texture`, `video-normalized`), and the Media page on a real pad. It uses the M3 set-up (`C:\OdysseyTest`) with the M5 Mega Drive ROMs and your credentials from M7 part 1, and the export full screen: `& .\artifacts\export\windows\OdysseyLauncher.exe --fullscreen ++ --user-dir=C:\OdysseyTest`.

1. **The Media page.** Settings, then Providers, media and credentials, then Media to scrape. Front cover, box back, box spine, screenshot and wheel say Yes; fan art, support texture and video say No. Turn on fan art, support texture and video (A, or right). `C:\OdysseyTest\settings.toml` now has a `media` line under `[scraping]` listing all eight, and your own comments are still there.
2. **Scrape a game.** Close the settings, press X on a well-known game (Sonic the Hedgehog 2), then Scrape this game. Then Images: the back, spine, screenshot, logo, hero art and disc or cartridge label cards show ScreenScraper's art.
3. **The files.** `Get-ChildItem C:\OdysseyTest\scraped\media\megadrive -Recurse -File | Select Directory, Name, Length`: a file in `back`, `spine`, `screenshot`, `logo`, `hero`, `label` and `video` (an `.mp4` of a few MB that plays in a video player), and none new in `box_texture`.
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
