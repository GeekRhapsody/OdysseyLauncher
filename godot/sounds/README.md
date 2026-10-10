Navigation sounds

The sounds the launcher plays as you browse (`src/Ui/UiSounds.cs`), when `[ui] navigation_sounds` is on (the default):

- `nav_tock.wav`: the focus moved to another system or game.
- `nav_whoosh.wav`: a system (or Favourites, or Recently played) was entered.

They're synthesised by `tools/ui-sounds/make_sounds.py` (numpy and scipy; its docstring says how each is made), and are the same on every run. To change them:
1. Edit the script.
2. Run `python tools/ui-sounds/make_sounds.py --preview=$PWD/artifacts/ui-sounds` from the repo root, and look at the PNGs and listen to the WAVs.
3. Run `godot --headless --path godot --import`.

They're imported uncompressed (`compress/mode=0` in each `.import` file): they're a few KB each, and need no decoding to play.
