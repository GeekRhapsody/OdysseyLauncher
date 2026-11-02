# Changelog

What changed in each release of Odyssey Launcher, newest first. Releases before this changelog have their notes on the [releases page](https://github.com/GeekRhapsody/OdysseyLauncher/releases).

<!--
Add each change people will notice under "## Unreleased" as it's made, most important first: the launcher's
"Check for updates" shows a release's first five lines. release.ps1 names the section "## <version> (<date>)" when
it releases, and the Release workflow puts it on the release page (tools/release-notes.ps1).
-->

## Unreleased

### New

- **Dreamcast (NA/JP)**, a second Dreamcast system for collections with North American or Japanese art, shown in the standard CD jewel case those games came in. Put those games in a `dreamcastnajp` folder in your ROMs folder. Its art is whatever your scraping regions pick, as for every system. Every theme has a card for it: in Console, the Dreamcast with its orange swirl.

### Changed

- Dreamcast games show in the PAL Dreamcast case: deeper than a CD case, with the blue tray's "Dreamcast" band down its left side. It's sized to ScreenScraper's European scans, so their whole front, back and spine show without cropping. If your Dreamcast art is North American or Japanese, move those games to the new Dreamcast (NA/JP) system.
- The Console theme's DOS, Windows 3.x, Windows 9x and Windows cards are new, each a PC of its time whose monitor plays a game as a video when you focus it, in step with its keyboard, mouse and drives: DOS loads a helicopter game from a floppy, Windows 3.x opens a brick breaker from Program Manager, Windows 9x runs a racing game from its CD, and the Windows gaming PC's fans spin while it plays an adventure from the desktop. Before, those cards didn't move.
- The Console theme's Flash card plays smoothly. Its monitor shows the game as a video, in step with the mouse beside it: the loading bar filling, the title, PLAY clicked, the ship flown with the mouse and firing at each click, and the right-click menu. Before, it swapped a few still pictures in and out.

## 0.21.0 (2026-11-01)

### New

- **LaunchBox's Games DB** is a scraping provider, the first fallback after ScreenScraper. It needs no account: its database (about 110 MB) is downloaded the first time a scrape needs it, then checked for a newer one once a week. Its names and art follow your preferred regions, as ScreenScraper's do, and it has box backs, spines, logos, fan art and disc and cartridge art. Settings > Scraping > LaunchBox Games DB shows your copy and updates it.
- **PlayStation Vita**, run by Vita3K. A game Vita3K has installed boots by its title id, and a package or game folder it hasn't is installed first; ES-DE's `.psvita` files work too. Every theme has a card for it: in Console, a PS Vita playing a game on its screen.
- Emulator profiles can launch a game by its title id (`{title_id}`), and run games kept in an emulator's own storage (`installs` and `install_args`).

### Changed

- ScreenScraper's flat green placeholder images (box backs, mostly) are no longer saved: the next provider's art is used instead. Placeholders downloaded before stay; delete them and scrape the system again to replace them.
- The default scraping order is ScreenScraper, then LaunchBox, IGDB and SteamGridDB. If you chose your own fallbacks, add LaunchBox in Settings > Scraping > Fallbacks.
- Odyssey Launcher is released under the MIT licence, and the zip includes `LICENSE.txt`.

### Fixed

- Video memory grew by about 170 MB with each game launched after the first in a session. It's now given back every time.
