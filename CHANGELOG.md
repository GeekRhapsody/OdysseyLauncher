# Changelog

What changed in each release of Odyssey Launcher, newest first. Releases before this changelog have their notes on the [releases page](https://github.com/GeekRhapsody/OdysseyLauncher/releases).

<!--
Add each change people will notice under "## Unreleased" as it's made, most important first: the launcher's
"Check for updates" shows a release's first five lines. release.ps1 names the section "## <version> (<date>)" when
it releases, and the Release workflow puts it on the release page (tools/release-notes.ps1).
-->

## Unreleased

### Fixed

- **Black system cards and games on a computer without Vulkan**, such as a Linux virtual machine with no Vulkan driver: the launcher now draws them in their proper colours there too.

## 0.22.1 (2026-11-03)

### New

- **Super Famicom**, a system of its own for Japanese SNES games, shown in the tall box they came in, where SNES games keep the wide European and North American box. Put them in an `sfc` folder in your ROMs folder, as in ES-DE: they appear in the SNES's card. Every theme has a card for it: in Console, the Super Famicom.
- **Mega-CD, Sega CD and Mega-CD (JP)** are three systems, one for each region's box: European games in the PAL Mega-CD case, North American games in the Sega CD long box, and Japanese games in the CD jewel case. Each box is sized to ScreenScraper's scans for its region, so the whole front, back and spine show without cropping. Put your games in a `megacd`, `segacd` or `megacdjp` folder in your ROMs folder, as in ES-DE. They all appear in the Mega-CD's card. Every theme has a card for each: in Console, the Mega-CD on the Mega Drive as Europe, North America and Japan sold them.
- **Dreamcast (NA/JP)**, a second Dreamcast system for collections with North American or Japanese art, shown in the standard CD jewel case those games came in. Put those games in a `dreamcastnajp` folder in your ROMs folder: they appear in the Dreamcast's card, next to your other Dreamcast games, each in its own case. Its art is whatever your scraping regions pick, as for every system.
- **Grouped regional variants:** a regional variant such as Dreamcast (NA/JP) has no card of its own. Its games are in its console's card, sorted together with the others, each in its own box and labelled with its system. To give one variant its own card, press X on its console's card and set "Dreamcast (NA/JP) in this card" to No (set it to Yes to put it back); to give every variant its own card, turn off Settings, Look, Group regional variants. A console's card shows even when only its variant has games. Every theme has a card for Dreamcast (NA/JP) for when it's shown on its own: in Console, the Dreamcast with its orange swirl.
- **Grid with labels**, a new layout for systems and for games: the grid, with each system's name or each game's title under it, on up to two lines. Choose it in Settings, Look, Layout (Systems view or Games view), or for one system's games on its own page. Columns and rows work as they do for the grid.

### Changed

- Games in an `sfc` or `superfamicom` folder are now Super Famicom games, in the tall box. Their art, favourites and play history stay with SNES; to bring the art back, move its files from `media/snes` to `media/sfc`.
- Sega CD / Mega-CD is now three systems (see above). Games in a `segacd` folder are now Sega CD games, in the long box. Games in a `megacd` or `megacdjp` folder become Mega-CD or Mega-CD (JP) games: their art, favourites and play history stay with Sega CD. To bring the art back, move its files from `media/segacd` to `media/megacd` or `media/megacdjp`. If you set your own folders for Sega CD, its games stay Sega CD games until you move the European and Japanese ones to the new systems' folders.
- Dreamcast games show in the PAL Dreamcast case: deeper than a CD case, with the blue tray's "Dreamcast" band down its left side. It's sized to ScreenScraper's European scans, so their whole front, back and spine show without cropping. If your Dreamcast art is North American or Japanese, move those games to the new Dreamcast (NA/JP) system.
- The Console theme's DOS, Windows 3.x, Windows 9x and Windows cards are new, each a PC of its time whose monitor plays a game as a video when you focus it, in step with its keyboard, mouse and drives: DOS loads a helicopter game from a floppy, Windows 3.x opens a brick breaker from Program Manager, Windows 9x runs a racing game from its CD, and the Windows gaming PC's fans spin while it plays an adventure from the desktop. Before, those cards didn't move.
- The Console theme's Flash card plays smoothly. Its monitor shows the game as a video, in step with the mouse beside it: the loading bar filling, the title, PLAY clicked, the ship flown with the mouse and firing at each click, and the right-click menu. Before, it swapped a few still pictures in and out.
- The Console theme's PSP has the real PSP-1000's shape. Its ends are grips a little shorter than the middle, so it steps in at each corner: the clear L and R buttons sit in the top corners, the strap loop in the bottom left and the charging socket in the bottom right, and its back curves in towards the ends. Before, it was rounded like a bar of soap.

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
