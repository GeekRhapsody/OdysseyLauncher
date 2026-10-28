# Odyssey Launcher

**A fully 3D game launcher for your emulators and PC games, inspired by the PlayStation 2's memory card browser.**

Every system and every game is a floating 3D model. Depending on the theme, systems appear as their own consoles, as slabs with their logos or as flat logo cards, and games come in their real boxes, cases and cabinets, wrapped in their own cover art. Pick a system, pick a game, and it launches in the emulator you've set up. When you quit the game you're back where you left off.

![Browsing the systems, entering the Mega Drive and moving through its games](docs/readme/navigation.webp)

*The games in these screenshots are made up, and their art is AI-generated: no real game's art is shown ([how they're made](tools/made-up-games/README.md)).*

Odyssey Launcher is built with Godot 4 and C# for Windows. **Performance is the headline feature:** it starts fast, aims to stay locked to your display's refresh rate while you scroll through thousands of games, and keeps its memory use low.

## Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Getting started](#getting-started)
- [Controls](#controls)
- [Configuration](#configuration)
- [Themes and models](#themes-and-models)
- [Credits](#credits)

## Features

### A 3D library

- **Systems, then games, then play.** The main screen is a 3D grid of your systems; enter one for a grid of its games. Moving between them flies the grids in and out of depth over the theme's background (a gradient, as on the PS2, or a wallpaper).
- **Real boxes for real games.** Each system's games use a model of their packaging: Mega Drive clamshells, landscape SNES and N64 boxes, PlayStation jewel cases, black PS2 and PSP cases, jewel cases for other CD systems, DVD cases, Switch cases, and arcade cabinets with the marquee and screen filled in. Other systems' games get a box shaped by their own cover art. The front, back, spine and label each take the matching scraped art.
- **Your choice of model.** Any game or system can use another of the theme's models instead: a flat cover, a flat screenshot, a blue PS2 case, or a 1990s television that plays the focused game's video, with its sound.
- **Animated items.** The focused item lifts and sways, and models can carry their own animations: most of the Console theme's machines load a made-up game when you focus them (the Mega Drive takes a cartridge and its pad is played; the Game Boys', Game Gear's, PSP's and PS Vita's screens and the Amstrad CPC's and Commodore 64's monitors play the game as a video, in step with the buttons; the PS Vita's is played by touch, from its lock screen to its LiveArea), and the Recently played alarm clock rocks and rings. A theme can calm the motion or stop it.
- **Pick it up and turn it round.** Press R3 to bring the focused game up large in the middle of the screen. Turn it with the right stick to read the back of the box or look along its spine.
- **Several layouts.** Show systems and games as a grid (automatic size, or your own columns and rows), a carousel, one item at a time, or a list of titles beside the focused game's model. Each system can have its own layout.
- **Favourites, Recently played and All games** appear as cards of their own at the start of the systems grid.

![Inspecting a game and turning it with the right stick](docs/readme/inspect.webp)

### Your collection, as it is

- **Multi-disc games** show as one game: an `.m3u`, `.cue` or `.gdi` hides the files it lists. PS3, PS4 and PS5 games kept as folders (`Game.ps3`) count as one game too.
- **Clean titles** come from No-Intro and Redump file names. The region, languages, revision and disc number are kept as details, and titles sort naturally ("The Legend of Zelda" under L).
- **Sorting:** order systems by name, maker or release year. Order games by title, last played, time played, date added or release date, per system if you like.
- **Play history:** play counts, total play time and last played, recorded for every launch.
- **Import from RetroBat/Batocera:** a system's `gamelist.xml` brings in its titles, metadata, favourites and media without overwriting anything you already have.
- **Network drives work well.** Folders are listed in large batches and scanned in parallel, and unplugging a drive never loses your favourites or history.

### Scraping

- **Four providers:** ScreenScraper, IGDB, SteamGridDB and the Steam store. Ask them in the order you choose; each later one fills only what the earlier ones didn't find.
- **ScreenScraper works out of the box** in releases. Add your own account in the settings for higher limits; IGDB and SteamGridDB need free keys of your own.
- **Every kind of media:** front and back covers, spines, screenshots, logos, fan art, disc and cartridge labels, videos, and PDF manuals. You choose which kinds to download.
- **Accurate matching:** ScreenScraper identifies files by name, size and checksum, and a title search only counts a hit when the name really matches. When a match is wrong, "scrape this game" searches every provider at once, shows each result with its cover, and lets you choose. For a SteamGridDB result you can also pick the cover, logo and hero from its alternatives.
- **Runs in the background** in a queue that survives closing the app, and respects each provider's rate limits and quotas.
- **Your own art and edits win.** Set any image, the video or the manual yourself, edit a title or any metadata field, and a later scrape never overwrites it. Remove any of a game's media from its options.
- **Media layout:** media is stored in `covers/`, `screenshots/`, `videos/` and so on, under a folder you can move to any drive.

### Details and media

- **Game details (Y)** show everything the library knows: the description, release date, genre, developer, publisher, players, rating, region, play history and file.
- **Images, videos and manuals:** every scraped image appears as a card. Open one to view it full screen, play the game's video with sound, or read its manual a page at a time, zoomed to the page's width and scrolled with the right stick (Windows).
- **System details** show the system's model large, ready to turn, beside its history, emulators, folders and settings.

### Launching

- **Emulator profiles** RetroArch cores, standalone emulators (PCSX2, Dolphin, PPSSPP, DuckStation and more), and games that are their own program, script or shortcut.
- **Per-game overrides:** run one game with another of its system's emulators, from its options.
- **Switch controllers** are set up in Eden before each launch, the pad that chose the game as player 1, with an option to swap A/B and X/Y for non-Nintendo pads.
- **Steam games** are handed to Steam and followed until Steam says they've ended, so their play time is recorded too.
- **Clean hand-off:** while a game runs, the launcher stops drawing and frees its textures, so the emulator gets the machine. When the game ends, the launcher takes the foreground back so the controller works at once.

### Everything from the sofa

- **A full settings screen driven by the controller:** ROM folders, the media folder, emulators, themes (and downloading more), layouts and sorting, graphics, the status indicators and sounds, scraping providers, regions and credentials, rescanning and scraping the whole library, problems in your config files, and checking for updates. It includes an on-screen keyboard, file and folder pickers, and a "test connection" button for each provider.
- **Options for each game (X):** the emulator, the 3D model, its media (images, video and manual), title and metadata, scraping, clearing metadata and deleting the game.
- **Options for each system (X):** its ROM folders, emulator, layout and sorting, card and game models, scraping all its games (or only those missing a cover or a screenshot, or not scraped lately), and importing an existing `gamelist.xml`.
- **Power menu (View):** restart, shut down or sleep the PC, or quit the app.
- **Status indicators:** the clock, the battery, and the Wi-Fi signal or cable, top right, plus an optional FPS and video memory readout.
- **Navigation sounds:** a tock as the focus moves and a whoosh as you enter a system (they can be turned off).
- **Graphics options:** borderless, exclusive fullscreen or windowed; 3D resolution; Direct3D 12 or Vulkan; anisotropic filtering.
- The keyboard works everywhere, and the mouse in the menus.

### Built for speed

- It aims to be interactive within a second of its own start-up, even with a 10,000-game library. Nothing is scanned or decoded before the first frame.
- It aims to stay locked to the refresh rate while scrolling. The UI thread never touches the disk, the network or the database, and nothing allocates per frame.
- Covers stream in on background threads and are uploaded within a strict per-frame budget, so the visible grid is textured almost at once.
- Each kind of model is drawn in one batch, whatever the number of games.
- The baseline hardware is a Steam Deck, handheld at 1280×800 and docked to a 4K display.

## Screenshots

### Themes

The **Slab** theme (the default) shows each system as a dark slab with its logo. **Console** shows each system as its console, modelled in 3D: every built-in system has its own, from the Channel F to the PlayStation 5 and the PS Vita (with a PC for Windows and DOS, and a laptop for desktop apps), most of them loading a made-up game when you focus them; a system you add yourself gets a plain card. **Classic View** looks like a 2D launcher: flat logo cards and flat covers over a wallpaper, with nothing swaying. Switch themes from the settings, or for the session with <kbd>T</kbd> on the systems screen, without a restart. Get more from **Download themes** in the settings: themes checked before they're listed, then kept up to date from their own repositories.

![Switching from the Console theme to Slab, then Classic View](docs/readme/themes.webp)

| Console | Slab |
|---|---|
| ![The systems screen in the Console theme, Recently played's alarm clock focused](docs/readme/systems-console.jpg) | ![The systems screen in the Slab theme](docs/readme/systems-slab.jpg) |
| **Classic View** | |
| ![The systems screen in the Classic View theme: logo cards over a wallpaper](docs/readme/systems-classic-view.jpg) | |

### Games

| Mega Drive | Super Nintendo |
|---|---|
| ![Mega Drive games in their clamshell cases](docs/readme/games-megadrive.jpg) | ![SNES games in landscape boxes](docs/readme/games-snes.jpg) |
| **Arcade** | **Nintendo 64** |
| ![Arcade games as cabinets, each with its marquee and screen](docs/readme/games-arcade.jpg) | ![N64 games in their big boxes](docs/readme/games-n64.jpg) |

### Layouts

| Carousel | List |
|---|---|
| ![SNES games in the carousel layout](docs/readme/layout-carousel.jpg) | ![Mega Drive games in the list layout, the focused game's box beside the titles](docs/readme/layout-list.jpg) |

### Details and options

| Game details | System details |
|---|---|
| ![A game's details: its description, metadata and play history, and its images](docs/readme/game-details.jpg) | ![The Mega Drive's details, its model beside them](docs/readme/system-details.jpg) |
| **Game options** | |
| ![A game's options: emulator, model, images, metadata, scraping](docs/readme/game-options.jpg) | |

## Getting started

1. **Download** the latest `OdysseyLauncher-<version>-windows-x86_64.zip` from [Releases](https://github.com/GeekRhapsody/OdysseyLauncher/releases), unzip it anywhere, and run `OdysseyLauncher.exe`. The .NET runtime is included, so there's nothing else to install. It needs 64-bit Windows 10 or 11 and a GPU with Direct3D 12 or Vulkan.
2. **Point it at your games.** By default each system's games are expected in `<your user folder>\ROMs\<system id>` (`ROMs\megadrive`, `ROMs\snes`...), as in other frontends. In **Settings > ROM folders** you can set another root folder, or give any system its own folders.
3. **Point it at your emulators.** In **Settings > Emulators**, set the folder your emulators live in and RetroArch's folder. Each system's emulator can be changed from its options (X on its card). The settings list any emulator that's missing.
4. **Scrape** from **Settings > Library**: "Scrape all missing metadata" fetches art and metadata for every game never scraped, not found before, or without a front cover. Add your ScreenScraper account (or IGDB and SteamGridDB keys) under **Settings > Scraping** for faster, fuller results.

**Portable mode:** put an empty `portable.txt` beside `OdysseyLauncher.exe`, and settings, databases, media and caches stay in a `userdata` folder next to it, instead of `%APPDATA%` and `%LOCALAPPDATA%`.

**Updating:** **Settings > Check for updates** fetches the newest release from GitHub, installs it and restarts the launcher. Your settings, library and media are kept.

## Controls

| Action | Controller | Keyboard |
|---|---|---|
| Move | D-pad, left stick | Arrow keys |
| Open, play | A | Enter, Space |
| Back | B | Escape, Backspace |
| Options for the focused system or game | X | O, or the Menu key |
| Details | Y | I |
| Favourite (a game) | L3 | F |
| Inspect (bring the game up close) | R3 | Z |
| Turn the focused item | Right stick | |
| Page up, page down | LB, RB | Page Up, Page Down |
| Previous, next letter (a system's games) | LT, RT | <kbd>[</kbd>, <kbd>]</kbd> |
| First, last | | Home, End |
| Settings | Menu (or B on the systems screen) | F1 (or Escape on the systems screen) |
| Power menu | View | P |
| Next theme, for the session (systems screen) | | T |
| Rescan the library: ROM folders, and media for new games (systems screen) | | F5 |
| Rescan the library and media (systems screen) | | Shift+F5 |

## Configuration

Everything in the settings screen is saved to plain TOML files in `%APPDATA%\OdysseyLauncher` (or `userdata\` in portable mode). You can edit them by hand too. They hold only what differs from the built-in defaults, and the app keeps your comments and formatting when it writes to them:

- `settings.toml`: folders (ROMs, media and emulators), display and graphics, layouts and sorting, the status indicators and sounds, scanning and scraping.
- `systems.toml`: each system's ROM folders, file types, emulator, layout and sorting.
- `emulators.toml`: emulator profiles (program, core and arguments, with placeholders such as `{rom}` and `{core}`).
- `secrets.toml`: scraping credentials.

Your own themes, and the ones you download, go in a `themes` folder beside them.

## Themes and models

Themes are folders of glTF 2.0 (`.glb`) models and images, plus a `theme.toml`. The manifest sets the background (a gradient, or a wallpaper for the theme and for each system), the lighting, the menus' colours and font, how much items sway, each system's colour, model and logo, and each system's game template. A theme only states what it changes; everything else comes from the built-in base theme.

You can also replace any single model from the system and game options, without writing a theme:

- **A system's card,** or the template for all its games.
- **A single game's model,** as a `.glb`, or an OBJ model in a zip. PS2 save icons (an OBJ with its `.anim`) keep their animation.

Models are checked against the model spec and its budgets, oversized textures are scaled down, and any problem is written to a log you can read.

The guide for theme authors is [docs/THEMING.md](docs/THEMING.md). It covers the manifest, media slots and fallbacks, the model spec and budgets, animation clips, making models in Blender, testing, and getting a theme onto the download list. A sample theme to copy is in [samples/themes/retro-tv](samples/themes/retro-tv).

## Credits

### Slab theme logos: canvas-es-de

The system logos in the **Slab** theme (`godot/themes/slab/logos/`) come from [**canvas-es-de**](https://github.com/Siddy212/canvas-es-de) by [Siddy212](https://github.com/Siddy212), a theme for ES-DE. canvas-es-de credits its original artwork and layouts to fagnerpc.

They're used under the [Creative Commons Attribution-NonCommercial-ShareAlike 2.0](https://creativecommons.org/licenses/by-nc-sa/2.0/) licence (CC BY-NC-SA 2.0). **Changes:** each image was cropped to its content, scaled to at most 512 pixels on its longer side and converted to WebP, and a few were renamed to match Odyssey Launcher's system ids. The PlayStation 5's image (`ps5.webp`) isn't from canvas-es-de: it was made for Odyssey Launcher in the same layout. The adapted logos are shared under the same licence.

### Classic View theme logos: es-theme-carbon

The system logos in the **Classic View** theme (`godot/themes/classic-view/logos/`) come from [**es-theme-carbon**](https://github.com/fabricecaruso/es-theme-carbon), Batocera's default theme, by Rookervik (based on simple by Nils Bonenberger). Its readme names the licence as Creative Commons Attribution-NonCommercial-ShareAlike (CC BY-NC-SA); its heading says version 2.0 and the licence text below it 4.0. The logos and trademarks themselves are their owners'.

**Changes:** each SVG was rendered to an image, each image cropped to its content, scaled to at most 512 pixels on its longer side and converted to WebP, and a few were renamed to match Odyssey Launcher's system ids. The adapted logos are shared under the same licence.

### Also

- [Godot Engine](https://godotengine.org), which renders everything.
- [ES-DE](https://es-de.org), whose systems catalogue, folder names, emulator commands, release years and descriptions are the basis of the built-in systems.
- [Lucide](https://lucide.dev) for the status indicator icons (ISC licence).
- [LibGit2Sharp](https://github.com/libgit2/libgit2sharp) (MIT licence) and [libgit2](https://libgit2.org) (GPLv2 with a linking exception), with which the theme downloader clones and updates themes.
- [ScreenScraper](https://www.screenscraper.fr), [IGDB](https://www.igdb.com), [SteamGridDB](https://www.steamgriddb.com) and Steam for game metadata and art.
