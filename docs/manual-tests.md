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
   - View rescans: "Scanning your ROM folders…" shows, then the counts update.
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

5. Scrape the whole set, timed, keeping the output:

   ```powershell
   Measure-Command { & $cli --user-dir=C:\OdysseyTest system megadrive | Tee-Object C:\OdysseyTest\scrape-log.txt } | Select-Object TotalSeconds
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
