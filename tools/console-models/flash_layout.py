"""Flash's card, a 2000s monitor playing a Flash game: the measurements shared by flash_print.py (which draws its
printing, its screen's still and the screens of its video), flash_video.py (which draws the video) and flash.py (which
builds it). Plain Python: Blender's Python imports it too.

Flash has no hardware: its games were played in a web browser, the Flash Player's red logo on their preloaders, its
right-click menu ending in About Adobe Flash Player. The card is that: a silver 17-inch LCD monitor of the time on its
oval foot, a browser window filling its screen with a Flash game in the page (a made-up game, Odyssey), and a mouse
beside its foot. Millimetres: x from the monitor's middle (left to right), y back from its panel's front, z up from the
table. A 17-inch 5:4 panel's active area (1280 x 1024 pixels) is 338 x 270 mm; the rest is typical of the monitors of
the time.

The Flash logo (F_LOGO) is the white f traced from the Flash Player icon on Wikimedia Commons, normalised to its
square (x right, y down, 0 to 1).

One texture (ATLAS square, REGIONS): the brand plate under the screen, the mouse's top, and swatches. A region is
(x, y, width, height) in pixels. The glass has its own, flash_screen.png (VIDEO_PX): the browser with the preloader at
0% and the pointer on Go, the still of the model's `video` material, and the first and last frame of the card's video
(flash_video.py), which the launcher plays on the glass while the card is focused.

The screen is laid out in its own units, SCREEN across the glass (3.2 of the panel's pixels each, so the browser's text
reads on the card): the browser's title bar, menus and address bar with Go (GO) at the top, its status bar at the
bottom, and the page between them with the Flash movie in it (MOVIE). The pointer (pointer()) is the mouse's: the mouse
moves on the table as the pointer moves on the screen, GAIN units a millimetre along its own axes (mouse_offset()), and
dips under the finger as it's clicked.

The `focused` clip's timing, in frames at FPS, is here so that the video (flash_video.py) follows the clip (flash.py)
frame for frame: the launcher starts the video with the clip, and again each time the clip loops.
"""

import math

ATLAS = 512

PANEL = dict(width=370.0, height=306.0, depth=52.0, bottom=92.0, bezel=16.0, lip=24.0)   # the bezel; the deeper bottom
GLASS = (338.0, 270.0)
STAND = dict(base=(240.0, 196.0, 16.0), base_y=70.0, neck=(70.0, 30.0), neck_y=96.0, top=150.0)
LED = (156.0, -14.0, 2.2)                                   # the power light: x, z from the panel's bottom edge, radius
BUTTONS = dict(x=[96.0 + 13.0 * k for k in range(4)], z=-12.0, size=(8.0, 3.0))   # under the screen, at the right

MOUSE = dict(at=(196.0, -62.0), turn=-12.0, size=(64.0, 116.0, 36.0), split=50.0)   # w, length, h; buttons' length

F_LOGO = [(0.742, 0.179), (0.761, 0.179), (0.761, 0.307), (0.714, 0.312), (0.693, 0.319), (0.664, 0.338),
          (0.628, 0.377), (0.597, 0.435), (0.695, 0.436), (0.695, 0.563), (0.547, 0.563), (0.506, 0.655),
          (0.477, 0.703), (0.434, 0.752), (0.384, 0.788), (0.351, 0.804), (0.318, 0.815), (0.273, 0.823),
          (0.242, 0.824), (0.242, 0.697), (0.283, 0.692), (0.320, 0.678), (0.346, 0.659), (0.373, 0.627),
          (0.410, 0.557), (0.463, 0.422), (0.497, 0.347), (0.518, 0.312), (0.545, 0.276), (0.583, 0.238),
          (0.636, 0.205), (0.694, 0.186)]

COLOURS = dict(silver="#B8BBC0", black="#121214", print="#FFFFFF", mouse="#C9CBCF", video="#FFFFFF", dark="#2A2B2E")

REGIONS = dict(plate=(0, 0, 208, 60), mouse=(0, 68, 120, 216))
SWATCHES = dict(silver=(148, 92), black=(180, 92), blue=(212, 92), grey=(244, 92))

# ---- The screen ------------------------------------------------------------------------------------------------------
SCREEN = (400, 320)            # the screen's units across the glass
VIDEO_PX = (640, 512)          # the video's frames and the still: the glass's proportions, even sides for H.264
MOVIE = (40, 74, 360, 290)     # the Flash movie in the page: x0, y0, x1, y1
GO = (366, 35, 394, 47)        # the Go button at the address bar's end
PLAY = (160, 232, 240, 256)    # the title's PLAY button
MENU_ITEMS = ["Zoom In", "Zoom Out", "Show All", "Quality", "", "Settings...", "Global Settings...", "",
              "About Adobe Flash Player 10..."]       # the Flash Player's right-click menu; "" a separator
MENU_WIDTH, MENU_ROW, MENU_RULE = 150, 15, 6          # its width, an item's height, a separator's


def menu_rows(x, y):
    """The menu's rows with its top left at (x, y): (item, top, bottom), "" for a separator."""
    rows, top = [], y + 2
    for item in MENU_ITEMS:
        height = MENU_ROW if item else MENU_RULE
        rows.append((item, top, top + height))
        top += height
    return rows


def menu_height():
    return sum(MENU_ROW if item else MENU_RULE for item in MENU_ITEMS) + 4


# ---- The focused clip, in frames at FPS ------------------------------------------------------------------------------
FPS = 30
LENGTH = 300                 # 10 s
CLICK = 4                    # frames a mouse button is held: PLAY and Go act as it comes up, a bolt as it goes down
LOAD = (6, 58)               # the preloader's bar fills, in LOADING's bursts
PRELOADER_OUT = (58, 64)     # at 100% the preloader fades out
TITLE = 64                   # Odyssey's title: its sky fades in, the name drops in, the ship slides in, PLAY pops up
POINT_PLAY = (84, 106)       # the pointer glides from Go to PLAY
CLICK_PLAY = 110             # PLAY clicked
TITLE_OUT = (114, 122)       # the title fades out
GAME = 122                   # the game fades in, the pointer hidden: the ship follows the mouse
SHOTS = (146, 160, 174, 188)  # clicks, a bolt each, as the ship turns at the top or the bottom of its weave
RIGHT_CLICK = 210            # the right click: as it's let go, the menu fades in and the game freezes under it
MENU_PATH = (218, 240)       # the pointer down the menu's items to About Adobe Flash Player
TO_GO = (246, 270)           # the pointer out of the menu and up to Go
CLICK_GO = 272               # Go clicked: the menu goes; let go, the page loads again
BLANK = (279, 285)           # the page white while it loads
RELOADED = 285               # the page again, the preloader at 0%, as in the first frame
CLICKS = (CLICK_PLAY,) + SHOTS + (RIGHT_CLICK, CLICK_GO)
FREEZE = RIGHT_CLICK + CLICK  # the game's last frame: the Flash Player stops the movie while its menu is open
LOADING = [(LOAD[0], 0.0), (14, 0.18), (20, 0.31), (30, 0.36), (42, 0.74), (50, 0.86), (LOAD[1], 1.0)]  # the bar


def loaded(f):
    """How far the preloader's bar is at frame f, 0 to 1: the download's bursts, linear between them."""
    if f <= LOADING[0][0]:
        return 0.0
    for (f0, a), (f1, b) in zip(LOADING, LOADING[1:]):
        if f < f1:
            return a + (b - a) * (f - f0) / (f1 - f0)
    return 1.0


# ---- The pointer and the mouse ---------------------------------------------------------------------------------------
GAIN = 8.0                   # the screen's units the pointer moves for each millimetre the mouse moves
REST = (376.0, 46.0)         # the pointer's tip at rest: on Go, which has just loaded the page
PLAY_AT = (222.0, 246.0)     # on PLAY, beside its word
MENU_AT = (136.0, 136.0)     # where it right-clicks: the menu's top left


def _path():
    """The pointer's waypoints: (frame, (x, y), whether it stops there). In the game it weaves through its points, the
    ship's nose following it, and it right-clicks where the menu fits below it; in the menu it goes down to About Adobe
    Flash Player, then along that row and out by the menu's right edge (not across the other items), and up to Go."""
    about = next((MENU_AT[0] + 62.0, (top + bottom) / 2 + 2) for item, top, bottom in menu_rows(*MENU_AT)
                 if item.startswith("About"))
    right = MENU_AT[0] + MENU_WIDTH
    return [(0, REST, True), (POINT_PLAY[0], REST, True), (POINT_PLAY[1], PLAY_AT, True),
            (CLICK_PLAY + CLICK, PLAY_AT, True), (130, (124.0, 170.0), False), (144, (140.0, 138.0), False),
            (158, (112.0, 202.0), False), (172, (146.0, 150.0), False), (186, (118.0, 198.0), False),
            (RIGHT_CLICK, MENU_AT, True), (MENU_PATH[0], MENU_AT, True), (MENU_PATH[1], about, True),
            (TO_GO[0], about, True), (TO_GO[0] + 5, (right - 24.0, about[1]), False),
            (TO_GO[0] + 9, (right + 20.0, about[1] - 11.0), False), (TO_GO[1], REST, True), (LENGTH, REST, True)]


PATH = _path()


def _velocity(i):
    """The pointer's velocity at waypoint i, in units a frame: none where it stops, else along its neighbours."""
    _f, _p, stops = PATH[i]
    if stops or i in (0, len(PATH) - 1):
        return (0.0, 0.0)
    (fa, a, _), (fb, b, _) = PATH[i - 1], PATH[i + 1]
    return tuple((q - p) / (fb - fa) for p, q in zip(a, b))


def pointer(f):
    """The pointer's tip at frame f, in the screen's units: a cubic through the waypoints, easing into and out of
    its stops."""
    for i in range(len(PATH) - 1):
        (f0, p0, _), (f1, p1, _) = PATH[i], PATH[i + 1]
        if f0 <= f < f1:
            if p0 == p1:                                     # a hold
                return p0
            t, span = (f - f0) / (f1 - f0), f1 - f0
            h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
            h01, h11 = 3 * t ** 2 - 2 * t ** 3, t ** 3 - t ** 2
            return tuple(h00 * a + h10 * span * va + h01 * b + h11 * span * vb
                         for a, b, va, vb in zip(p0, p1, _velocity(i), _velocity(i + 1)))
    return PATH[-1][1] if f >= PATH[-1][0] else PATH[0][1]


def mouse_offset(f):
    """The mouse's offset from its rest at frame f, in the set's millimetres (x, y): the pointer's travel from its rest
    over GAIN, along the mouse's own axes (its forward, +y, is the screen's up), turned with it."""
    x, y = pointer(f)
    dx, dy = (x - REST[0]) / GAIN, -(y - REST[1]) / GAIN
    turn = math.radians(MOUSE["turn"])
    return dx * math.cos(turn) - dy * math.sin(turn), dx * math.sin(turn) + dy * math.cos(turn)


def held(f, f0):
    """Whether a button clicked at f0 is down at frame f."""
    return f0 <= f < f0 + CLICK
