"""Copies the button glyphs the hints use from Kenney's Input Prompts into godot/icons/prompts/.

Usage: python tools/button-prompts/prepare.py <pack folder>

<pack folder> is Kenney's Input Prompts 1.5A (CC0), unzipped as kenney.nl gives it: a folder per set ("Xbox Series",
"Nintendo Gamecube"...), each with its SVGs in Vector/. The filled glyphs are one white shape with the letter or symbol
cut out, so the app tints them with Modulate, and they're copied unchanged.
The D-pads and arrow keys mark the directions meant in red: those become white, and the rest faint white
(FAINT), so they stay one colour. Any other colour is an error, so a change of pack can't slip in a glyph the tint
would spoil. A few glyphs (CROPPED: the small View and Menu buttons of PlayStation, the Deck and the 2015 Steam
Controller) fill little of their 64-unit square, so they're cropped to a square around their shape, and show as large
as the others.

The face buttons are named by position, as Godot's JoyButton is: `a` is the bottom one (Xbox A, PlayStation's cross,
Nintendo's B, GameCube's A), `b` the right (GameCube's X), `x` the left (GameCube's B) and `y` the top. A pad without a
button (a GameCube pad has no View, LB, L3 or R3) leaves it out, and the hints for it don't show. The Switch 2's glyphs
are the Switch's, and the new Steam Controller's the Deck's, so they have no folder of their own.
docs/ARCHITECTURE.md A1, "Button icons".
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "godot" / "icons" / "prompts"

# Our name -> the pack's file (in <set>/Vector/), per kind. A pad's table names a, b, x and y, and any of the rest it has.
PADS = ["a", "b", "x", "y", "view", "menu", "lb", "rb", "lt", "rt", "l3", "r3", "dpad_vertical", "dpad_horizontal", "stick_r"]

GLYPHS = {
    "xbox": ("Xbox Series", {
        "a": "xbox_button_a", "b": "xbox_button_b", "x": "xbox_button_x", "y": "xbox_button_y",
        "view": "xbox_button_view", "menu": "xbox_button_menu",
        "lb": "xbox_lb", "rb": "xbox_rb", "lt": "xbox_lt", "rt": "xbox_rt",
        "l3": "xbox_stick_l_press", "r3": "xbox_stick_r_press",
        "dpad_vertical": "xbox_dpad_vertical", "dpad_horizontal": "xbox_dpad_horizontal", "stick_r": "xbox_stick_r",
    }),
    "playstation": ("PlayStation Series", {
        "a": "playstation_button_cross", "b": "playstation_button_circle",
        "x": "playstation_button_square", "y": "playstation_button_triangle",
        "view": "playstation5_button_create", "menu": "playstation5_button_options",
        "lb": "playstation_trigger_l1", "rb": "playstation_trigger_r1",
        "lt": "playstation_trigger_l2", "rt": "playstation_trigger_r2",
        "l3": "playstation_button_l3", "r3": "playstation_button_r3",
        "dpad_vertical": "playstation_dpad_vertical", "dpad_horizontal": "playstation_dpad_horizontal",
        "stick_r": "playstation_stick_r",
    }),
    # By position: Nintendo's B is at the bottom, A on the right, Y on the left, X at the top.
    "nintendo": ("Nintendo Switch", {
        "a": "switch_button_b", "b": "switch_button_a", "x": "switch_button_y", "y": "switch_button_x",
        "view": "switch_button_minus", "menu": "switch_button_plus",
        "lb": "switch_button_l", "rb": "switch_button_r", "lt": "switch_button_zl", "rt": "switch_button_zr",
        "l3": "switch_stick_l_press", "r3": "switch_stick_r_press",
        "dpad_vertical": "switch_dpad_vertical", "dpad_horizontal": "switch_dpad_horizontal",
        "stick_r": "switch_stick_r",
    }),
    # By position, as SDL maps a GameCube pad: A at the bottom, X on the right, B on the left, Y at the top.
    "gamecube": ("Nintendo Gamecube", {
        "a": "gamecube_button_a", "b": "gamecube_button_x", "x": "gamecube_button_b", "y": "gamecube_button_y",
        "menu": "gamecube_button_start", "rb": "gamecube_button_z", "lt": "gamecube_trigger_l", "rt": "gamecube_trigger_r",
        "dpad_vertical": "gamecube_dpad_vertical", "dpad_horizontal": "gamecube_dpad_horizontal", "stick_r": "gamecube_stick_c",
    }),
    "steamdeck": ("Steam Deck", {
        "a": "steamdeck_button_a", "b": "steamdeck_button_b", "x": "steamdeck_button_x", "y": "steamdeck_button_y",
        "view": "steamdeck_button_view", "menu": "steamdeck_button_options",
        "lb": "steamdeck_button_l1", "rb": "steamdeck_button_r1", "lt": "steamdeck_button_l2", "rt": "steamdeck_button_r2",
        "l3": "steamdeck_stick_l_press", "r3": "steamdeck_stick_r_press",
        "dpad_vertical": "steamdeck_dpad_vertical", "dpad_horizontal": "steamdeck_dpad_horizontal",
        "stick_r": "steamdeck_stick_r",
    }),
    # The 2015 Steam Controller: one stick, and the right trackpad, which SDL reads as the right stick.
    "steamcontroller": ("Steam Controller", {
        "a": "steam_button_a", "b": "steam_button_b", "x": "steam_button_x", "y": "steam_button_y",
        "view": "steam_button_back_icon", "menu": "steam_button_start_icon",
        "lb": "steam_lb", "rb": "steam_rb", "lt": "steam_lt", "rt": "steam_rt",
        "l3": "steam_stick_l_press", "r3": "steam_button_rp",
        "dpad_vertical": "steam_dpad_vertical", "dpad_horizontal": "steam_dpad_horizontal", "stick_r": "steam_pad",
    }),
    "keyboard": ("Keyboard & Mouse", {
        "enter": "keyboard_return", "escape": "keyboard_escape", "i": "keyboard_i", "o": "keyboard_o",
        "f1": "keyboard_f1", "p": "keyboard_p", "f": "keyboard_f", "z": "keyboard_z",
        "page_up": "keyboard_page_up", "page_down": "keyboard_page_down",
        "bracket_open": "keyboard_bracket_open", "bracket_close": "keyboard_bracket_close",
        "arrows_vertical": "keyboard_arrows_vertical", "arrows_horizontal": "keyboard_arrows_horizontal",
        "w": "keyboard_w", "a": "keyboard_a", "s": "keyboard_s", "d": "keyboard_d",
    }),
}

# The glyphs cropped to their shape, as <set>/<file>.
CROPPED = {
    "playstation5_button_create", "playstation5_button_options", "steamdeck_button_view", "steamdeck_button_options",
    "steam_button_back_icon", "steam_button_start_icon",
}

# The space left around a cropped shape, in the pack's units (of 64).
CROP_MARGIN = 3

FILL = re.compile(r'fill="([^"]+)"')
PATH = re.compile(r' d="([^"]+)"')
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
WHITE = "#FFFFFF"
HIGHLIGHT = "#E73246"
FAINT = "0.35"


def monochrome(path: Path) -> str:
    """The glyph as one white shape, its highlight (if any) white and the rest faint."""
    svg = path.read_text(encoding="utf-8")
    fills = set(FILL.findall(svg))
    if fills == {WHITE}:
        return svg

    if fills != {WHITE, HIGHLIGHT}:
        raise SystemExit(f"{path}: fills {sorted(fills)}, not one white shape")

    svg = svg.replace(f'fill="{WHITE}"', f'fill="{WHITE}" fill-opacity="{FAINT}"')
    return svg.replace(f'fill="{HIGHLIGHT}"', f'fill="{WHITE}"')


def cropped(svg: str, path: Path) -> str:
    """The glyph with a viewBox: the smallest square around its shape (and CROP_MARGIN), centred on it."""
    data = " ".join(PATH.findall(svg))
    # Kenney's paths are absolute moves, lines and quadratic curves: every number pair is a point (or a control point,
    # which is near enough for a margin).
    if set(re.findall(r"[A-Za-z]", data)) - {"M", "L", "Q"}:
        raise SystemExit(f"{path}: a path with commands other than M, L and Q can't be cropped")

    numbers = [float(n) for n in NUMBER.findall(data)]
    xs, ys = numbers[0::2], numbers[1::2]
    side = max(max(xs) - min(xs), max(ys) - min(ys)) + 2 * CROP_MARGIN
    left = (min(xs) + max(xs) - side) / 2
    top = (min(ys) + max(ys) - side) / 2
    return svg.replace('<svg width="64" height="64"', f'<svg width="64" height="64" viewBox="{left:g} {top:g} {side:g} {side:g}"', 1)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    pack = Path(sys.argv[1])
    for kind, (folder, table) in GLYPHS.items():
        if kind != "keyboard" and not ({"a", "b", "x", "y"} <= set(table) <= set(PADS)):
            raise SystemExit(f"{kind}: the table must name a, b, x and y, and only glyphs from {PADS}")

        out = OUT / kind
        out.mkdir(parents=True, exist_ok=True)
        for name, source in table.items():
            path = pack / folder / "Vector" / f"{source}.svg"
            svg = monochrome(path)
            if source in CROPPED:
                svg = cropped(svg, path)
            (out / f"{name}.svg").write_text(svg, encoding="utf-8", newline="\n")

        print(f"{kind}: {len(table)} glyphs")

    return 0


if __name__ == "__main__":
    sys.exit(main())
