"""The Windows card's measurements, shared by windows_pc_print.py (which draws its printing, its screen's still and the
screens of its video), windows_pc_video.py (which draws the video) and windows_pc.py (which builds it). Plain Python:
Blender's Python imports it too.

Windows has no hardware of its own: its card is a gaming PC of the 2020s, unbranded. Millimetres: x from the monitor's
middle (left to right), y back from the monitor's panel's front, z up from the desk.

- The tower (TOWER): a black mid-tower the size of the popular cases of its time (the NZXT H5 Flow is 227 x 428 x 464
  mm, the Corsair 4000D 230 x 453 x 466), on four feet, its glass side panel left open (the launcher draws no
  transparency) and its front a frame round three 120 mm fans with lit rings. In its own frame: x across from its left
  side (the open one) to its right, y back from its front, z up from its feet. Inside, through the open side: the
  motherboard on the right panel's inside, the power supply's shroud along the floor, the graphics card across the
  case, a tower cooler (its fan blowing towards the back) with four lit memory sticks beside it, the three front fans'
  backs and the exhaust fan in the back wall. It stands left of the monitor, turned (TOWER["turn"]) so its open side
  faces the viewer and its front faces in towards the monitor.
- The monitor (MONITOR): a 27-inch 16:9 panel (its lit area 597 x 336 mm) with thin bezels and a deeper chin, on a
  column and a flat base, the glass the `video` material.
- The keyboard (KEYBOARD): a full-size 104-key mechanical one, its black keys floating over a black plate, each key's
  legend lit in a rainbow across the board and a glow round each key on the plate; KEYS has every key in units of U
  from its left edge, in rows from the front (5, the space bar's) to the back (0, the function keys').
- The mouse (MOUSE): a wireless gaming mouse on the desk mat (MAT), right of the keyboard, its lit stripe and wheel.

The prints: `windows_case.png` (CASE_ATLAS square, CASE_REGIONS: the tower's faces and its parts) and
`windows_desk.png` (DESK_ATLAS square, DESK_REGIONS: the keys' tops, the plate, the mouse's top, the mat, the monitor's
faces), each with swatches; the glass's still is `windows_screen.png` (VIDEO_PX): the desktop, the video's first and
last frame. A region is (x, y, width, height) in pixels.

The screen is laid out in its own units, SCREEN across the glass (1280 x 720). The pointer (POINTER, a
pointer_path.Path) is the mouse's: the mouse moves on the mat as the pointer moves on the screen, GAIN units a
millimetre, and dips under the finger as it's clicked. The `focused` clip's timing, in frames at FPS, is here so that
the video (windows_pc_video.py) follows the clip (windows_pc.py) frame for frame.
"""

from pointer_path import Path

# ---- The tower -------------------------------------------------------------------------------------------------------
TOWER = dict(width=230.0, depth=450.0, height=470.0, feet=12.0, wall=4.0, glass=12.0, at=(-530.0, 205.0), turn=32.0)
FRONT_OPENING = dict(z=(28.0, 446.0), margin=24.0)          # the front's opening round the fans (z up from the floor)
FAN = dict(size=120.0, depth=25.0, hole=57.0, rotor=55.0, blades=9)   # a 120 mm fan; its rotor's radius
FRONT_FANS = [96.0, 222.0, 348.0]                            # the front fans' middles, up from the case's floor (z)
FRONT_FAN_Y = 8.0                                            # their faces, back from the front
REAR_FAN = dict(x=122.0, z=370.0)                            # the exhaust fan's middle in the back wall
BOARD = dict(x=200.0, y=(120.0, 425.0), z=(196.0, 440.0))    # the motherboard's face, inside the right panel (ATX)
SHROUD = dict(y=66.0, z=100.0)                               # the power supply's shroud: behind the fans, its top
GPU = dict(x=(70.0, 198.0), y=(120.0, 440.0), z=(232.0, 284.0))      # the graphics card: its long side to the glass
COOLER = dict(x=(48.0, 196.0), y=(304.0, 356.0), z=(308.0, 432.0))   # the tower cooler's fins over the socket
COOLER_FAN = dict(x=122.0, y=278.0, z=370.0)                 # its fan on the fins' front face, blowing to the back
RAM = dict(x=(162.0, 198.0), y=(226.0, 262.0), z=(300.0, 434.0), sticks=4)   # four sticks, their light bars outward
FAN_TURNS = dict(front=9, rear=9, cooler=12)                 # whole turns each fan makes in the clip, so it loops

# ---- The monitor -----------------------------------------------------------------------------------------------------
MONITOR = dict(width=614.0, height=368.0, thick=18.0, bottom=128.0, bezel=8.5, chin=23.5,
               housing=(420.0, 250.0, 36.0), column=(60.0, 28.0), column_y=86.0, base=(236.0, 176.0, 8.0),
               base_y=78.0)
SCREEN_MM = (597.0, 336.0)

# ---- The keyboard ----------------------------------------------------------------------------------------------------
U = 19.05
# at: its middle (x) and its front edge (y)
KEYBOARD = dict(at=(-40.0, -200.0), width=446.0, depth=142.0, front=20.0, back=29.0, margin=8.0,
                cap=dict(base=18.2, top=(13.4, 14.2), height=7.6, lift=3.6), press=3.2)
ROW_Y = {5: 8.0, 4: 8.0 + U, 3: 8.0 + 2 * U, 2: 8.0 + 3 * U, 1: 8.0 + 4 * U, 0: 8.0 + 5 * U + 9.0}   # front edges


def _row(row, x, keys):
    """A row's keys: (name, x, row, width, legend, rows tall), each key's width in units, from x."""
    out = []
    for item in keys:
        if item is None:
            x += 0.25
            continue
        name, legend, w = item[0], item[1], item[2] if len(item) > 2 else 1.0
        tall = item[3] if len(item) > 3 else 1
        out.append((name, x, row, w, legend, tall))
        x += w
    return out


def _keys():
    k = []
    k += _row(0, 0.0, [("esc", "Esc")])
    k += _row(0, 2.0, [(f"f{i}", f"F{i}") for i in range(1, 5)])
    k += _row(0, 6.5, [(f"f{i}", f"F{i}") for i in range(5, 9)])
    k += _row(0, 11.0, [(f"f{i}", f"F{i}") for i in range(9, 13)])
    k += _row(0, 15.25, [("prtsc", "PrtSc"), ("scrlk", "ScrLk"), ("pause", "Pause")])
    k += _row(1, 0.0, [("grave", "~\n`")] + [(f"d{c}", f"{s}\n{c}") for c, s in zip("1234567890", "!@#$%^&*()")]
              + [("minus", "_\n-"), ("equals", "+\n="), ("backspace", "Backspace", 2.0)])
    k += _row(1, 15.25, [("ins", "Ins"), ("home", "Home"), ("pgup", "PgUp")])
    k += _row(1, 18.5, [("numlk", "Num"), ("ndiv", "/"), ("nmul", "*"), ("nsub", "-")])
    k += _row(2, 0.0, [("tab", "Tab", 1.5)] + [(c.lower(), c) for c in "QWERTYUIOP"]
              + [("lbracket", "{\n["), ("rbracket", "}\n]"), ("backslash", "|\n\\", 1.5)])
    k += _row(2, 15.25, [("del", "Del"), ("end", "End"), ("pgdn", "PgDn")])
    k += _row(2, 18.5, [("n7", "7"), ("n8", "8"), ("n9", "9"), ("nadd", "+", 1.0, 2)])
    k += _row(3, 0.0, [("caps", "Caps Lock", 1.75)] + [(c.lower(), c) for c in "ASDFGHJKL"]
              + [("semicolon", ":\n;"), ("quote", "\"\n'"), ("enter", "Enter", 2.25)])
    k += _row(3, 18.5, [("n4", "4"), ("n5", "5"), ("n6", "6")])
    k += _row(4, 0.0, [("lshift", "Shift", 2.25)] + [(c.lower(), c) for c in "ZXCVBNM"]
              + [("comma", "<\n,"), ("period", ">\n."), ("slash", "?\n/"), ("rshift", "Shift", 2.75)])
    k += _row(4, 16.25, [("up", "↑")])
    k += _row(4, 18.5, [("n1", "1"), ("n2", "2"), ("n3", "3"), ("nenter", "Enter", 1.0, 2)])
    k += _row(5, 0.0, [("lctrl", "Ctrl", 1.25), ("lwin", "Win", 1.25), ("lalt", "Alt", 1.25), ("space", "", 6.25),
                       ("ralt", "Alt", 1.25), ("fn", "Fn", 1.25), ("menu", "Menu", 1.25), ("rctrl", "Ctrl", 1.25)])
    k += _row(5, 15.25, [("left", "←"), ("down", "↓"), ("right", "→")])
    k += _row(5, 18.5, [("n0", "0", 2.0), ("ndot", ".")])
    return k


KEYS = _keys()
PRESSED = ("w", "a", "d", "e", "lshift", "esc")               # the keys the clip presses


def key_rect(x, row, w, tall=1):
    """A key's base on the plate, (x0, y0, x1, y1) in the keyboard's frame (x from its left edge, y back from its
    front): rows tall keys reach forward over the rows in front."""
    m, g = KEYBOARD["margin"], (U - KEYBOARD["cap"]["base"]) / 2
    y0 = ROW_Y[row + tall - 1] if tall > 1 else ROW_Y[row]
    return m + x * U + g, y0 + g, m + (x + w) * U - g, ROW_Y[row] + U - g


# ---- The mouse and the mat -------------------------------------------------------------------------------------------
MOUSE = dict(at=(296.0, -114.0), turn=-8.0, size=(64.0, 124.0, 39.0), split=52.0)   # w, length, h; buttons' length
MAT = dict(x=(-318.0, 420.0), y=(-238.0, 52.0), thick=3.0)

# ---- The prints ------------------------------------------------------------------------------------------------------
CASE_ATLAS = 1024
CASE_REGIONS = dict(
    front=(0, 0, 256, 524),        # the front round the fans' opening, its width x height (a across, b down)
    top=(264, 0, 236, 462),        # the top, its front edge at the bottom: the dust filter, the buttons and ports
    back=(508, 0, 236, 482),       # the back: the exhaust fan's grille, the I/O, the slots, the power supply
    board=(752, 0, 272, 218),      # the motherboard's face, seen through the open side (a from the back, b down)
    gpu=(752, 226, 272, 46),       # the graphics card's long side, facing the glass (a from the back)
    gpu_top=(752, 280, 272, 110),  # its backplate from above (a from the back, b from the glass side)
    shroud=(752, 398, 272, 62),    # the shroud's side, facing the glass (a from the back)
    fins=(752, 468, 62, 148),      # the cooler's fins' end, facing the glass (a from the back)
    ram=(822, 468, 44, 160),       # a memory stick's side, its lit top along it (a from the back)
    fan=(0, 532, 240, 240),        # a fan's frame from its front: its lit ring round the hole
    blades=(248, 532, 240, 240),   # a fan's rotor from its front: its hub and its lit blades
)
CASE_SWATCHES = dict(case="#16171A", inside="#0E0F12", metal="#3A3D44", dark="#08090A", lit="#9FE8FF",
                     pcb="#14161B", fins="#5D6168", ram="#1E2026", shroud="#111215")


def swatch_places(swatches, x0, y0):
    """Each swatch's block's middle, (x, y) pixels, in a row from (x0, y0)."""
    return {name: (x0 + 32 * k, y0) for k, name in enumerate(swatches)}


CASE_SWATCH_AT = swatch_places(CASE_SWATCHES, 16, 1004)
DESK_ATLAS = 1024
DESK_REGIONS = dict(
    keys=(0, 0, 1024, 340),        # the keyboard from above: the keys' tops and the plate's glow round them
    mat=(0, 348, 1024, 372),       # the mat from above, its lit edge
    mouse=(0, 728, 132, 248),      # the mouse from above, its buttons forward
    chin=(140, 728, 600, 26),      # the monitor's chin under the glass
    back=(140, 762, 420, 252),     # the monitor's housing from behind
)
DESK_SWATCHES = dict(black="#121316", plate="#191A1E", grey="#2A2C31", stand="#3A3D44", lit="#7FD8FF",
                     rubber="#0B0B0D", keycap="#141519", bezel="#0A0A0C")
DESK_SWATCH_AT = swatch_places(DESK_SWATCHES, 584, 790)

# ---- The screen ------------------------------------------------------------------------------------------------------
SCREEN = (1280, 720)               # the screen's units across the glass
VIDEO_PX = (800, 450)              # the video's frames and the still: 16:9, even sides for H.264

# ---- The focused clip, in frames at FPS ------------------------------------------------------------------------------
FPS = 30
LENGTH = 360                       # 12 s
CLICK = 3                          # frames a mouse button is held down
POINT_ICON = (16, 40)              # the pointer glides from its rest to the game's icon on the desktop
DOUBLE = (44, 50)                  # the icon double-clicked
LAUNCH = (54, 64)                  # the busy pointer while the game starts; at its end the screen goes black
SPLASH = (66, 96)                  # the developer's logo fades in and out
TITLE = (96, 148)                  # the title: its art comes up, the menu slides in; Continue clicked; it fades out
POINT_CONTINUE = (108, 124)        # the game's pointer to Continue
CLICK_CONTINUE = 130
LOADING = (148, 160)               # the loading screen
PLAY = (160, 294)                  # the game, run on W, sprinting on Shift, looked round with the mouse
RUN = (162, 290)                   # W held
SPRINT = (176, 226)                # Shift held
STRAFE = dict(a=(196, 208), d=(214, 222))   # A and D held: she steps aside
BEAST = (190, 292)                 # the beast: it prowls in, rears, takes two thrusts and falls
ATTACKS = (242, 258)               # clicks: a spear thrust each
TAKE = 272                         # E: the spoils taken
ESC = 294                          # Esc: the pause menu comes up over the game
POINT_QUIT = (304, 320)            # the pointer to Quit to Desktop
CLICK_QUIT = 324
QUIT = (328, 344)                  # the game fades out, the desktop fades in
CLICKS = (DOUBLE[0], DOUBLE[1], CLICK_CONTINUE) + ATTACKS + (CLICK_QUIT,)
KEY_PRESSES = dict(w=[RUN], lshift=[SPRINT], a=[STRAFE["a"]], d=[STRAFE["d"]], e=[(TAKE, TAKE + 4)],
                   esc=[(ESC, ESC + 4)])

# ---- The pointer and the mouse ---------------------------------------------------------------------------------------
GAIN = 10.0                        # the screen's units the pointer moves for each millimetre the mouse moves
REST = (690.0, 452.0)              # the pointer's tip at rest, on the wallpaper
ICON = (62.0, 180.0)               # on the game's desktop icon
CONTINUE = (178.0, 372.0)          # on the title's Continue
QUIT_AT = (642.0, 474.0)           # on the pause menu's Quit to Desktop
POINTER = Path([
    (0, REST, True), (POINT_ICON[0], REST, True), (POINT_ICON[1], ICON, True), (POINT_CONTINUE[0], ICON, True),
    (POINT_CONTINUE[1], CONTINUE, True), (CLICK_CONTINUE + 6, CONTINUE, True),
    (PLAY[0], (196.0, 368.0), False), (184, (262.0, 360.0), False), (206, (150.0, 374.0), False),
    (230, (232.0, 362.0), False), (252, (204.0, 368.0), False), (276, (238.0, 362.0), True),
    (ESC + 6, (238.0, 362.0), True), (POINT_QUIT[1], QUIT_AT, True), (CLICK_QUIT + 4, QUIT_AT, True),
    (QUIT[1] + 4, REST, True), (LENGTH, REST, True)])
LOOK = 0.9                         # the camera's turn, in the painting's pixels, for each unit the pointer moves


def pressed(name, f):
    """Whether key name is down at frame f."""
    return any(f0 <= f < f1 for f0, f1 in KEY_PRESSES.get(name, ()))
