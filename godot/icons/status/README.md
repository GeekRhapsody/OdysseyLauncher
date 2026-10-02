# Status indicator icons

These are the icons for the status indicators in the top-right corner (`src/Screens/StatusBar.cs`). They come from [Lucide](https://lucide.dev): `lucide-static` 1.49.0, from unpkg. The licence is ISC (see `LICENSE`).

Each file is unchanged except for `stroke="currentColor"`, which becomes `#ffffff` so the app can tint the icon with `Modulate`.

They're imported at 4× (96 px), with mipmaps, so they stay sharp where the overlay is scaled up for 2160p.

To add an icon:
1. Take its SVG from the same version.
2. Make the same stroke change.
3. Copy an existing `.import` file's options, or set them in the editor's Import dock.
4. Run `godot --headless --path godot --import`.
