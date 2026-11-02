"""The retro PC cards' shared parts (DOS, Windows 3.x and Windows 9x), read by retro_pc_print.py (which draws a card's
printing and its screen's still), retro_pc_video.py (which draws its video) and retro_pc.py (which builds it), each
card's set described by its own layout (dos_layout.py, windows3x_layout.py, windows9x_layout.py). Plain Python:
Blender's Python imports it too.

Millimetres. Each part is described in its own frame (x across from its middle, left to right as its front is seen; y
back from its front; z up from the desk); the set's layout places it on the desk.

The keyboard: a PC keyboard of the time, the IBM Model M's layout and size (101 keys; 104 with the Windows and menu
keys, the late 1990s'): the main block, the editing keys and the arrows, the keypad, the function keys in a row of
their own behind a half key's gap; 19.05 mm a key (U). Its case is its side outline across its width: a ledge for the
palms at the front, the keys' well sloping up to the back (SLOPE), and a ledge behind it with the three lights over the
keypad and the badge at the left. The keys stand in the well, each tapering to its top, the rows sculpted a little
(ROW_TOP); their legends are printed on their tops, seen from above (the print atlas's `kb_top` region). key_tops()
gives each key's top as seen from above, where its legend is drawn.

The mouse: a two-button mouse of the early 1990s, its outline lofted up to a dome, its buttons' seams printed on its
top; on a pad. The media: a 3.5-inch floppy and a CD.

The CRT's glass: each card's video is the whole glass (GLASS_PX), the raster (RASTER_PX, the screen's own pixels) in its
middle with the tube's unlit margin round it.
"""

import math

U = 19.05

# ---- The keyboard ----------------------------------------------------------------------------------------------------
KB = dict(width=470.0, depth=196.0, front=22.0, back=44.0)   # the case; its front face's and back face's heights
WELL_Y = 30.0                         # the well's front edge, back from the case's front
WELL_Z = 20.0                         # its floor's height there
SLOPE = math.radians(5.5)             # the well's floor rising to the back
WELL_LENGTH = 138.0                   # up the slope
RIM = 6.5                             # the case's top round the well, above its floor
KEYS_S0 = 7.0                         # the front row's front edge, up the slope from the well's front
KEY_GAP = 1.2                         # between two keys' bases
KEY_INSET = (2.4, 3.4, 1.6)           # a key's top inside its base: at its sides, its front, its back
ROW_TOP = {1: 12.0, 2: 12.0, 3: 12.6, 4: 13.2, 5: 14.0, 6: 14.0}   # each row's tops above the floor (sculpted)
PRESS = 3.8                           # how far a key goes down
BACK_LEDGE = (171.0, 41.0)            # the ledge behind the well: its front edge (y) and its top (z)
KEYS_X0 = -23 * U / 2                 # the keys' left edge (the main block's)


def deck(s, h):
    """The keyboard's (y, z) of the point s up the well's floor from its front edge and h off it."""
    c, k = math.cos(SLOPE), math.sin(SLOPE)
    return WELL_Y + s * c - h * k, WELL_Z + s * k + h * c


def row_s(row):
    """A row's front edge up the slope: the five rows from the front, then the function keys after half a key's gap."""
    return KEYS_S0 + (row - 1) * U + (U / 2 if row == 6 else 0.0)


def _row(row, x, keys):
    out = []
    for key in keys:
        name, w = key[0], key[1]
        if name is not None:
            out.append(dict(name=name, row=row, x=x, w=w, legend=key[2], colour=key[3] if len(key) > 3 else "key",
                            tall=key[4] if len(key) > 4 else 1))
        x += w
    return out


def keys(windows=False):
    """Every key: dict(name, row, x (its left edge, in keys from KEYS_X0), w (in keys), legend (its lines, top first,
    split by line breaks), colour ("key" or "mod"), tall (rows it spans towards the front)). windows: the 104-key
    layout's bottom row, with the Windows and menu keys."""
    digits = [("d1", "!\n1"), ("d2", "@\n2"), ("d3", "#\n3"), ("d4", "$\n4"), ("d5", "%\n5"), ("d6", "^\n6"),
              ("d7", "&\n7"), ("d8", "*\n8"), ("d9", "(\n9"), ("d0", ")\n0")]
    out = _row(6, 0.0, [("esc", 1, "Esc", "mod"), (None, 1)] + [(f"f{k}", 1, f"F{k}", "mod") for k in range(1, 5)]
               + [(None, 0.5)] + [(f"f{k}", 1, f"F{k}", "mod") for k in range(5, 9)] + [(None, 0.5)]
               + [(f"f{k}", 1, f"F{k}", "mod") for k in range(9, 13)])
    out += _row(5, 0.0, [("grave", 1, "~\n`")] + [(n, 1, l) for n, l in digits]
                + [("minus", 1, "_\n-"), ("equals", 1, "+\n="), ("backspace", 2, "←", "mod")])
    out += _row(4, 0.0, [("tab", 1.5, "Tab", "mod")] + [(c.lower(), 1, c) for c in "QWERTYUIOP"]
                + [("lbracket", 1, "{\n["), ("rbracket", 1, "}\n]"), ("backslash", 1.5, "|\n\\")])
    out += _row(3, 0.0, [("caps", 1.75, "Caps\nLock", "mod")] + [(c.lower(), 1, c) for c in "ASDFGHJKL"]
                + [("semicolon", 1, ":\n;"), ("quote", 1, "\"\n'"), ("enter", 2.25, "Enter", "mod")])
    out += _row(2, 0.0, [("lshift", 2.25, "Shift", "mod")] + [(c.lower(), 1, c) for c in "ZXCVBNM"]
                + [("comma", 1, "<\n,"), ("period", 1, ">\n."), ("slash", 1, "?\n/"), ("rshift", 2.75, "Shift", "mod")])
    if windows:
        bottom = [("lctrl", 1.25, "Ctrl", "mod"), ("lwin", 1.25, "WIN", "mod"), ("lalt", 1.25, "Alt", "mod"),
                  ("space", 6.25, ""), ("ralt", 1.25, "Alt", "mod"), ("rwin", 1.25, "WIN", "mod"),
                  ("menu", 1.25, "MENU", "mod"), ("rctrl", 1.25, "Ctrl", "mod")]
    else:
        bottom = [("lctrl", 1.5, "Ctrl", "mod"), (None, 1), ("lalt", 1.5, "Alt", "mod"), ("space", 7, ""),
                  ("ralt", 1.5, "Alt", "mod"), (None, 1), ("rctrl", 1.5, "Ctrl", "mod")]
    out += _row(1, 0.0, bottom)
    edit = 15.5                                                          # the editing keys and arrows
    out += _row(6, edit, [("prtsc", 1, "Print\nScrn", "mod"), ("scrlk", 1, "Scroll\nLock", "mod"),
                          ("pause", 1, "Pause", "mod")])
    out += _row(5, edit, [("insert", 1, "Insert", "mod"), ("home", 1, "Home", "mod"), ("pgup", 1, "Page\nUp", "mod")])
    out += _row(4, edit, [("delete", 1, "Delete", "mod"), ("end", 1, "End", "mod"), ("pgdn", 1, "Page\nDown", "mod")])
    out += _row(2, edit, [(None, 1), ("up", 1, "↑", "mod")])
    out += _row(1, edit, [("left", 1, "←", "mod"), ("down", 1, "↓", "mod"), ("right", 1, "→", "mod")])
    pad = 19.0                                                           # the keypad
    out += _row(5, pad, [("numlock", 1, "Num\nLock", "mod"), ("kp_div", 1, "/", "mod"), ("kp_mul", 1, "*", "mod"),
                         ("kp_minus", 1, "-", "mod")])
    out += _row(4, pad, [("kp7", 1, "7\nHome"), ("kp8", 1, "8\n↑"), ("kp9", 1, "9\nPgUp"),
                         ("kp_plus", 1, "+", "mod", 2)])
    out += _row(3, pad, [("kp4", 1, "4\n←"), ("kp5", 1, "5"), ("kp6", 1, "6\n→")])
    out += _row(2, pad, [("kp1", 1, "1\nEnd"), ("kp2", 1, "2\n↓"), ("kp3", 1, "3\nPgDn"),
                         ("kp_enter", 1, "Enter", "mod", 2)])
    out += _row(1, pad, [("kp0", 2, "0\nIns"), ("kp_dot", 1, ".\nDel")])
    return out


def key_base(key):
    """A key's base in the well's frame: (x0, s0, x1, s1), its gap taken off; a tall key reaches the rows in front."""
    x0 = KEYS_X0 + key["x"] * U + KEY_GAP / 2
    x1 = KEYS_X0 + (key["x"] + key["w"]) * U - KEY_GAP / 2
    s0 = row_s(key["row"] - key["tall"] + 1) + KEY_GAP / 2
    return x0, s0, x1, row_s(key["row"]) + U - KEY_GAP / 2


def key_top(key):
    """A key's top in the well's frame: (x0, s0, x1, s1, h)."""
    x0, s0, x1, s1 = key_base(key)
    side, front, back = KEY_INSET
    return x0 + side, s0 + front, x1 - side, s1 - back, ROW_TOP[key["row"]]


def key_tops(windows=False):
    """Each key's top as seen from above, where its legend is printed: {name: (x0, y0, x1, y1)} in the keyboard's
    frame (y back from its front)."""
    out = {}
    for key in keys(windows):
        x0, s0, x1, s1, h = key_top(key)
        out[key["name"]] = (x0, deck(s0, h)[0], x1, deck(s1, h)[0])
    return out


LIGHTS = [("num", "Num Lock"), ("caps", "Caps Lock"), ("scroll", "Scroll Lock")]
LIGHTS_X = KEYS_X0 + 19.0 * U          # over the keypad, on the ledge behind the well
BADGE = (KEYS_X0 + 4.0, KEYS_X0 + 64.0)  # the badge on the ledge, over the main block's left
CORD_AT = (-80.0, KB["depth"])          # where the cord leaves the case's back

# ---- The mouse and its pad -------------------------------------------------------------------------------------------
MOUSE = dict(length=108.0, width=(60.0, 56.0), height=34.0, split=46.0)   # width at the back, at the front; split
PAD = dict(size=(232.0, 192.0), thickness=3.0, radius=10.0)


def mouse_outline(n=36):
    """The mouse from above, its middle at the origin, its front (the buttons, the cord) towards +y: a rounded box
    narrowing a little to the front. Anticlockwise from the back."""
    length, (wb, wf) = MOUSE["length"], MOUSE["width"]
    points = []
    for k in range(n):
        a = 2 * math.pi * k / n - math.pi / 2
        c, s = math.cos(a), math.sin(a)
        y = length / 2 * math.copysign(abs(s) ** 0.62, s)            # a superellipse: flatter sides, rounder ends
        half = (wb + (wf - wb) * (y / length + 0.5)) / 2
        points.append((half * math.copysign(abs(c) ** 0.55, c), y))
    return points


# ---- The media -------------------------------------------------------------------------------------------------------
FLOPPY = dict(size=(90.0, 94.0), thickness=3.3)         # a 3.5-inch floppy: across, along (its shutter's end first)
CD = dict(radius=60.0, hole=7.5, thickness=1.2)

# ---- The CRT's glass and its video -----------------------------------------------------------------------------------
GLASS_PX = (720, 540)                 # the video's frames and the still: the whole glass, even sides for H.264
RASTER_PX = (640, 480)                # the lit raster, a 4:3 VGA screen's own pixels
RASTER_AT = (40, 30)                  # its top left in the glass

# ---- The atlases' swatches -------------------------------------------------------------------------------------------
ATLAS = 1024                          # each texture is drawn at most 1024 pixels (docs/THEMING.md section 7)
SWATCH_Y = ATLAS - 40                 # the swatches' row at the atlases' foot


def swatches(names):
    """Each colour's swatch in an atlas: its 24-pixel block's middle, (x, y)."""
    return {name: (16 + 32 * k, SWATCH_Y + 16) for k, name in enumerate(names)}


# ---- The clips' easing, in plain Python (the layouts' poses and the videos use it) -----------------------------------

def phase(f, f0, f1):
    return min(1.0, max(0.0, (f - f0) / (f1 - f0)))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_in(t):
    return t * t


def ease_out(t):
    return 1 - (1 - t) ** 2


def back_out(t, s=2.2):
    """Overshoots, then settles at 1."""
    t -= 1
    return 1 + t * t * ((s + 1) * t + s)


def pressed(f, presses):
    """How far down a key or button is at frame f (0 to 1), for its presses [(down, up)]: down in two frames, held, up
    in three."""
    return max((smooth(phase(f, a, a + 2)) * (1 - smooth(phase(f, b, b + 3))) for a, b in presses), default=0.0)
