# Changelog

What changed in each release of Odyssey Launcher, newest first. Releases before this changelog have their notes on the [releases page](https://github.com/GeekRhapsody/OdysseyLauncher/releases).

<!--
Add each change people will notice under "## Unreleased" as it's made, most important first: the launcher's
"Check for updates" shows a release's first five lines. release.ps1 names the section "## <version> (<date>)" when
it releases, and the Release workflow puts it on the release page (tools/release-notes.ps1).
-->

## Unreleased

### Fixed

- Removing or replacing a game's art, video, manual or model is now quick when the media folder is on a network drive. It could take several seconds, because the launcher looked through every media file of the game's system.
- The power menu is tall enough for all its choices, without a scroll bar.

## 1.2.0 (2026-11-10)

### New

- Favourites and All games have their own options, like a system: press X on their card, or Menu inside them, to set their view, columns, rows and sort order.
- W, A, S and D turn the focused game or system, like the right stick, including a game brought up close with Z. In a system's details they turn its model; on a zoomed manual page, W and S scroll.

### Changed

- Cleaner menus: a solid highlight instead of an outline and glow, no panel borders, and headings no longer in capitals. Titles over games and systems have a plain shadow instead of a coloured glow.
- Favourites follow the game sort order in Settings > Appearance, like All games, unless you give them their own. Before, they were always A to Z.
- New case colours: white for DS, 3DS and Wii, teal for Wii U, and Xbox green for Xbox and Xbox 360.
- The Console theme's PlayStation now matches the real console: its buttons, lid, memory card slots, controller ports, back sockets and end vents. While focused, it presses POWER to switch on and off.
- The Console theme's All games pile has four more boxes: PlayStation 2, PSP, PlayStation and Dreamcast.
- Switch covers show in full, no longer cut off at the top and bottom.
- Mega Drive and Genesis cases are slightly deeper, so their spine art is no longer cut off at the sides.
- The clamshell case for 32X, SG-1000 and SuperGrafx games (and the new coloured cases) takes its shape from each game's cover and spine, like DOS big boxes, so every size shows all its art. Its cover folds straight round the spine, with no black lines on the edges.

## 1.1.0 (2026-11-09)

### New

- Sort titles: a game can have a separate name for A to Z order. Set it in the game's options, under Edit the title and metadata. Jumping by letter follows it, and importing a gamelist brings in its sort names.

### Changed

- Clearer menu names: the media you choose to scrape uses the game's media names (Back cover, Spine and so on) instead of ScreenScraper's. "Clear metadata" is now "Reset this game", "Scrape all missing metadata" is "Scrape what's missing", "Auto scan the library at launch" is "Rescan when the launcher starts", and "Video driver" is "Renderer". The power menu reads Restart, Shut down, Sleep and Quit Odyssey Launcher.
- Settings pages say in plain words what they hold, and no longer show config file names and keys.
- A scrape's question says why a provider is skipped: it has reached its limit or is closed (and until when), or it refused its credentials.
- The Console theme's Amiga and Vectrex cards have been improved.

### Fixed

- A system card's video no longer plays fast to catch up with its animation after you close the settings.

## 1.0.0 (2026-11-07)

### New

- **A Showcase layout** for games, in Settings, Appearance (or a system's own view): a strip of boxes along the bottom with the focused game in the middle, and above it that game's logo, description, details and screenshot, over its hero art if it has one.
- **A Coverflow layout** for systems and games, in Settings, Appearance (or a system's own view): one row, with the focused game facing you in the middle and the rest showing their spines either side, like a shelf. Moving turns the next game round to face you and the last one back to its spine. Boxes with their spine on top, such as SNES and N64 boxes, stand on end to show it.
- **UI size: small, medium or large**, in Settings, Interface: the menus, text and controls get smaller for a monitor on your desk, or larger for a handheld's small screen or a television across the room. It changes at once. The game and system cards keep their size.

### Changed

- **The settings are easier to find your way around.** The first page is a short list: Library, Systems, Emulators, Scraping, Appearance, Interface, Graphics and About, each showing what it's set to. Each system's own settings (its ROM folders, emulator, games view and models) are under Systems, the systems you have games for first. Anything running, such as a scan or a scrape, shows at the top while it runs. Problems in your config files are under About, on a wide page that scrolls instead of a dialog with small, cramped text. Scrape all missing metadata is on the Scraping page.
- **Start (Menu) in a system's games opens that system's settings**: its emulator, games view, sort and models. On the systems screen, and in Favourites, Recently played and All games, it still opens the main settings.
- **Larger controls along the bottom of the screen**: their buttons and words are a little bigger, to read more easily on a small screen such as the Steam Deck's.
- **The Console theme's PlayStation 3 looks like the original one**: its top curves from front to back as the real one's does, with the chrome strip along its front edge, the drive's chrome face with its slot, the flap, the vents in its end and PLAYSTATION 3 along its top. It no longer has a controller beside it.
- **The Console theme's PICO-8 card is PICO-8's logo, built from coloured cubes**: the sparkle of eight colours round a white cross, which turns round while it's focused. It replaces the cartridge.
- **The Console theme's Steam Deck looks like the real one**: its shape is taken from Valve's own drawings, with the grips curving out behind it, the bumpers and rounded triggers on its top corners and the four buttons on its back, and its sticks, trackpads, buttons, vents and ports where the real ones are. While it's focused it still wakes up, shows its library and plays a game, now pulling a trigger too.

### Removed

- **The FPS and VRAM display** under the clock is gone, with its setting in Graphics.

### Fixed

- **The ↑ and ↓ buttons on the Regions and Fallbacks pages work with a controller**: press right to reach them, then A to move a region or provider earlier or later. The list no longer jumps to the top when you move one or turn it on or off: it only scrolls if the row would go out of view.
- **No more game card passing through the Nintendo DS and 3DS** in the Console theme: when you focus either, it switches on and the stylus comes out to tap TOUCH TO START.

## 0.24.0 (2026-11-05)

### New

- **Button icons in the controls along the bottom**: each screen's controls show your controller's buttons (Xbox, PlayStation, Switch and Switch 2, GameCube, Steam Deck or Steam Controller) or your keyboard's keys, following whatever you pressed last, in your theme's colours. Settings, Button icons chooses one kind always, for when Steam shows your controller as an Xbox one.

## 0.23.0 (2026-11-05)

### New

- **Odyssey Launcher for Linux**: each release now has an AppImage beside the Windows zip, `OdysseyLauncher-<version>-linux-x86_64.AppImage`. Make it executable and run it: nothing else to install. It needs a 64-bit distribution with glibc 2.34 or later (Ubuntu 22.04, Linux Mint 21, Fedora 35, current Arch, or newer).
- **Check for updates works on Linux**: it downloads the new AppImage, checks it, puts it in place of yours (keeping its file name) and restarts the launcher with it. Tools that update AppImages, such as AppImageUpdate and Gear Lever, can update it too.
- **Manuals open on Linux**, as on Windows: a game's manual from its details screen, with its pages' thumbnails, turning, zooming and scrolling.
- **Videos play on Linux**, as on Windows: a game's video on its details screen and on a television's screen, and the videos on the Console theme's system cards. Arcade videos in H.264's 4:4:4 format, which Windows can't play, play on Linux, as do HEVC and VP9 videos.
- **Steam games are followed until you quit them on Linux**, as on Windows: a game's desktop shortcut made by Steam (Manage, Add desktop shortcut) in the Steam system's folder keeps the launcher on its running screen while Steam updates and runs the game, and brings it back when the game ends, instead of coming straight back.
- **Games started by a launcher script are followed until the game ends on Linux**, as on Windows: a `.sh` script or program that starts the emulator and exits no longer brings the launcher straight back.
- **USB drives and mounted shares in the file and folder pickers on Linux**: whatever your desktop has mounted (under `/run/media` or `/media`), and anything mounted under `/mnt`, such as a NAS's share.
- **The battery and the Wi-Fi signal in the status indicators on Linux**, top right, as on Windows. A controller's battery isn't mistaken for the computer's.
- **Restart, shut down and sleep from the power menu on Linux** (View), as on Windows. An option your system would ask a password for, such as when another user is logged in, isn't offered.
- **Emulators are found on their own on Linux**: a distribution's package, a Flatpak, or an AppImage in `~/Applications`, `~/.local/bin` or `~/bin`, with RetroArch's cores wherever RetroArch keeps them. Every system has its Linux emulators built in, under the same names as on Windows, so on Linux you no longer need to set each one up yourself. Settings, Emulators shows where each program was found.
- **Desktop shortcuts and scripts as games on Linux:** Desktop Apps, Ports and Steam take `.desktop` files (run as your desktop runs them), `.sh` scripts and AppImages.
- **An emulator's program can be a list of places to look** in your `emulators.toml`, the first that has it winning: a program name to find on your PATH, or a file name with a `*` for the newest match.

### Changed

- **A launch makes the emulator's working folder if it isn't there yet**, instead of refusing to start.

### Fixed

- **On Linux, a PlayStation Vita game Vita3K has installed starts straight away**, instead of being installed again on every launch: the launcher now looks where Vita3K keeps its games on Linux (its portable folder, the folder its settings name, or `~/.local/share/Vita3K`).
- **On Linux, ROM folders whose names differ only in case** (`snes` and `SNES`) are both scanned: they're separate folders there, and only the first was.
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
