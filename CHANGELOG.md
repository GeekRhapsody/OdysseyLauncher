# Changelog

What changed in each release of Odyssey Launcher, newest first. Releases before this changelog have their notes on the [releases page](https://github.com/GeekRhapsody/OdysseyLauncher/releases).

<!--
Add each change people will notice under "## Unreleased" as it's made, most important first: the launcher's
"Check for updates" shows a release's first five lines. release.ps1 names the section "## <version> (<date>)" when
it releases, and the Release workflow puts it on the release page (tools/release-notes.ps1).
-->

## Unreleased

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
