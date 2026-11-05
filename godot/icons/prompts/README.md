# Button icons

The glyphs the controls' hints show, along the bottom of every screen (`src/Ui/HintBar.cs`, `src/Navigation/ButtonPrompts.cs`; docs/ARCHITECTURE.md A1, "Button icons"). A folder per kind: `xbox`, `playstation`, `nintendo` (a Switch's, which are a Switch 2's too), `gamecube`, `steamdeck` (the Deck's, which are the new Steam Controller's too), `steamcontroller` (the 2015 one) and `keyboard`.

They come from Kenney's [Input Prompts](https://kenney.nl/assets/input-prompts) 1.5A, downloaded from kenney.nl. The licence is CC0 (see `LICENSE`, the pack's own): no credit is needed, but the pack is Kenney's.

`tools/button-prompts/prepare.py` writes every file here from the pack, the same on every run:

- Each glyph is one white shape with its letter or symbol cut out, so the app tints it with `SelfModulate`.
- The D-pads and arrow keys mark the directions meant in red. Those parts become white, and the rest of the pad faint white, so the glyph is still one colour.
- The small View and Menu buttons of PlayStation, the Steam Deck and the 2015 Steam Controller fill little of the pack's 64-unit square, so they're cropped to a square around their shape.
- A pad's files are named by position, as Godot's `JoyButton` is: `a` is the bottom face button, `b` the right, `x` the left and `y` the top. So `nintendo/a.svg` is the Switch's B, and `gamecube/b.svg` is the GameCube's X (SDL maps a GameCube pad with A at the bottom, X on the right, B on the left and Y at the top).
- A pad without a button has no file for it: `gamecube` has no `view`, `lb`, `l3` or `r3`. The hints that need one don't show on that pad.

They're imported at 2× (128 px), with mipmaps, so they stay sharp where the overlay is scaled up for 2160p.

To change a glyph or add one:
1. Change the tables in `tools/button-prompts/prepare.py` (and the prompt's glyph names in `ButtonPrompts.cs`, if it's a new one).
2. Download the pack from kenney.nl, unzip it, and run `python tools/button-prompts/prepare.py <the unzipped folder>`.
3. For a new file, copy an existing `.import` file's options (`mipmaps/generate=true`, `svg/scale=2.0`), or set them in the editor's Import dock.
4. Run `godot --headless --path godot --import`.
