"""The Windows 3.x card's set, which retro_pc.py builds (retro_pc_layout.py has the parts it shares with the DOS and
Windows 9x cards' sets), and the timing its clip and its video (windows3x_screens.py, retro_pc_video.py) share. Plain
Python: Blender's Python imports it too.

A PC of about 1993: a 486DX2 desktop of the time's clones (430 x 410 x 156 mm), a 14-inch SVGA monitor on its foot on
top, the 101-key keyboard, and a two-button mouse on its pad at the keyboard's right. The case's front (FRONT, drawn by
retro_pc_print.py): on the left the badge printed on the plastic, the turbo display reading 66, the lights, TURBO and
RESET, the keylock, the vents and the power switch; on the right a caddy-loading double-speed CD-ROM drive, a 5.25-inch
drive and a 3.5-inch one.

Millimetres: x from the case's middle (left to right), y back from its front, z up from the desk. The screen's places
are in its 640 x 480 pixels (Windows 3.1 at VGA's resolution, in 256 colours).

The clip (frames at FPS; windows3x_screens.py draws the screen to it, frame for frame), the mouse moving as the pointer
does (pointer_path.py) and dipping as it clicks: Program Manager, its Main group open and the others minimised (the
still). The pointer goes to the Games group's icon and double-clicks it: the group opens out of it. It double-clicks
Spellbrick (made up, tools/made-up-games): the hourglass while the hard disk's light flickers, and the game's window
opens out of the icon on its title. A click starts it: the pointer hidden, the wizard's stone follows the mouse across
the bottom, catching the orb, which breaks a brick each time it goes up (the orb's flights are ORB's, the pointer's
path meeting it at each catch); a potion falls from one. The pointer goes up to Game and down to Exit, and the window
closes; then to the Games group's minimise button: the group shrinks back to its icon, and the pointer back to rest.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pointer_path as P  # noqa: E402
import retro_pc_layout as K  # noqa: E402

NAME = "Windows 3.x"
YAW, PITCH = -24.0, 20.0

COLOURS = dict(case="#D1C8B0", bezel="#DAD2BC", monitor="#D8D0BA", stand="#CBC2AA", key="#E6E0D0", mod="#BFB8A6",
               kbcase="#D2CAB4", dark="#1A1A1C", lit_red="#FF4A2E", mouse="#DCD5C2", pad="#27406E", cable="#3A3631")
SWATCHES = K.swatches(sorted(COLOURS))
PRINT_REGIONS = dict(kb_top=(0, 0, 1024, 427), mouse_top=(0, 440, 120, 216), pad=(136, 440, 464, 384))
DEVICE_REGIONS = dict(front=(0, 0, 1024, 351), monitor=(0, 368, 560, 534), back=(570, 368, 448, 154))

# ---- The case --------------------------------------------------------------------------------------------------------
CASE = dict(kind="desktop", width=430.0, depth=410.0, height=156.0, feet=6.0, bezel=20.0, at=(0.0, 0.0), plate=False,
            sound=True)
FRONT = [
    ("badge", 22.0, 16.0, 140.0, 20.0, 0.0, "ODYSSEY|486DX2"),
    ("display", 22.0, 46.0, 54.0, 26.0, 0.0, "66"),
    ("leds", 86.0, 46.0, 90.0, 26.0, 0.0, "POWER:#36E05A|TURBO:#F2D33A|HDD:#F04A3A:off"),
    ("button", 22.0, 88.0, 26.0, 13.0, 3.0, "TURBO"),
    ("button", 58.0, 88.0, 26.0, 13.0, 3.0, "RESET"),
    ("keylock", 190.0, 52.0, 18.0, 18.0, 3.0, ""),
    ("vents", 100.0, 92.0, 116.0, 40.0, 0.0, ""),
    ("power", 22.0, 112.0, 50.0, 22.0, 4.0, ""),
    ("cdcaddy", 262.0, 12.0, 146.0, 41.3, 1.5, ""),
    ("floppy525", 262.0, 56.0, 146.0, 41.3, 1.5, ""),
    ("floppy35", 262.0 + 22.2, 104.0, 101.6, 25.4, 1.5, ""),
]
HDD_LIGHT = (86.0 + 90.0 * 5 / 6, 46.0 + 26.0 * 0.36)
LIGHT_PARTS = dict(hdd_light=(HDD_LIGHT[0], HDD_LIGHT[1], 0.0, (4.0, 4.0), "lit_red", True))

# ---- The monitor -----------------------------------------------------------------------------------------------------
MONITOR = dict(at=(0.0, 36.0, 156.0), width=352.0, height=336.0, shell=66.0, foot=(114.0, 22.0),
               rear=dict(size=(306.0, 280.0), end=(204.0, 190.0), depth=300.0, rise=14.0),
               opening=(298.0, 230.0, 18.0), inner=(274.0, 206.0, 10.0), recess=24.0, bulge=5.5, screen_z=190.0,
               strip=[("brand", 24.0, 292.0, 130.0, 22.0, 0.0, "ODYSSEY|SVGA 1024  ·  0.28"),
                      ("knob", 214.0, 296.0, 13.0, 13.0, 3.5, ""),
                      ("knob", 234.0, 296.0, 13.0, 13.0, 3.5, ""),
                      ("knob", 254.0, 296.0, 13.0, 13.0, 3.5, ""),
                      ("led", 288.0, 300.0, 6.0, 6.0, 0.0, "#F2A93A"),
                      ("button", 304.0, 292.0, 24.0, 20.0, 4.0, "")])

# ---- The keyboard, the mouse and its pad -----------------------------------------------------------------------------
KEYBOARD = dict(at=(-62.0, -282.0), turn=2.0, windows=False)
CABLES = [dict(name="cord", r=2.6, points=[(-142.0, -86.0, 14.0), (-156.0, -60.0, 4.0), (-196.0, -20.0, 3.0),
                                            (-232.0, 30.0, 3.0), (-240.0, 90.0, 3.0)])]
MOUSE = dict(at=(316.0, -196.0), turn=-8.0, pad=(310.0, -190.0), pad_turn=-5.0)

# ---- The screen, in its pixels ---------------------------------------------------------------------------------------
PROGMAN = (24, 18, 616, 462)            # Program Manager's window
MAIN_GROUP = (36, 70, 436, 316)         # its Main group, open
GROUP_ICONS = dict(Accessories=(78, 398), Games=(178, 398), StartUp=(278, 398))   # the minimised groups' icons' middles
GAMES_GROUP = (196, 132, 588, 350)      # the Games group, open
GAME_ICONS = [("Spellbrick", (240, 194)), ("Kaleidrop", (330, 194)), ("Hive Hustle", (420, 194)),
              ("Flipside Pinball", (510, 194))]
GAMES_MINIMISE = (588 - 5 - 28, 132 + 5 + 9)      # the Games group's minimise button's middle
SPELL = (150, 36, 530, 458)             # Spellbrick's window
FIELD = (155, 81, 525, 438)             # its playfield
GAME_MENU = (174, 70)                   # its menu bar's Game
EXIT_ITEM = (196, 134)                  # Game's Exit
BAT_Y = 412                             # the wizard's stone's top

# ---- The clip, in frames at FPS --------------------------------------------------------------------------------------
FPS = 30
CLICK = 4                    # frames a button is held down
OPEN_GROUP = (42, 52)        # the Games group opening out of its icon
LOAD = (84, 98)              # the hourglass, the hard disk's light flickering
OPEN_GAME = (98, 104)        # the game's window opening out of its icon
START = 118                  # the click that starts the game: the orb leaves the stone

# The orb: its middle where it leaves the stone and at each bounce, in straight flights at ORB_SPEED pixels a frame;
# up to a brick in the wall's bottom row (which breaks), down to the stone, whose catch is the brick's bounce mirrored.
# The pointer's path (and the stone, which follows it) meets it at each catch.
ORB_R, ORB_SPEED = 7, 10.0
BRICK = dict(x0=160, w=30, y0=136, h=14, rows=7)          # the wall: its left edge and top, a brick's size, its rows
_BOUNCES = [(340, BAT_Y - ORB_R), (380, 241), (420, BAT_Y - ORB_R), (318, 241), (216, BAT_Y - ORB_R), (272, 241),
            (328, BAT_Y - ORB_R), (415, 241)]


def _orb():
    out, f = [], 122.0
    for k, p in enumerate(_BOUNCES):
        if k:
            q = _BOUNCES[k - 1]
            f += ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 / ORB_SPEED
        out.append((round(f), p))
    return out


ORB = _orb()
BRICKS = [(f, (x - BRICK["x0"]) // BRICK["w"], BRICK["rows"] - 1) for f, (x, y) in ORB if y < 300]
POTION = (ORB[3][0], ORB[3][1], 3.0)    # the green potion falling from the second brick: when, where, how fast
PAUSE = ORB[-1][0] + 2                  # the Game menu clicked, just after the last brick: the game waits
EXIT_CLICK = PAUSE + 16                 # Exit clicked
CLOSE = EXIT_CLICK + CLICK              # let go: the window goes
MINIMISE_CLICK = CLOSE + 22             # the Games group's minimise button
MINIMISE = (MINIMISE_CLICK + 2, MINIMISE_CLICK + 10)   # the group shrinking back to its icon
LENGTH = MINIMISE_CLICK + 40

REST = (470.0, 300.0)
GAIN = 9.0                               # the pointer's pixels for a millimetre of the mouse


def _path():
    games, spell = GROUP_ICONS["Games"], GAME_ICONS[0][1]
    catches = [(f, (x, BAT_Y)) for f, (x, y) in ORB if y > 300]
    return P.Path([(0, REST, True), (10, REST, True), (34, (games[0], games[1] - 2), True),
                   (44, (games[0], games[1] - 2), True), (76, (spell[0], spell[1] - 2), True),
                   (96, (spell[0], spell[1] - 2), True), (116, catches[0][1], True),
                   (catches[0][0], catches[0][1], True)]
                  + [(f, p, False) for f, p in catches[1:]]
                  + [(PAUSE - 2, GAME_MENU, True), (PAUSE + 4, GAME_MENU, True), (EXIT_CLICK - 2, EXIT_ITEM, True),
                     (EXIT_CLICK + 4, EXIT_ITEM, True), (MINIMISE_CLICK - 2, GAMES_MINIMISE, True),
                     (MINIMISE_CLICK + 6, GAMES_MINIMISE, True), (MINIMISE_CLICK + 30, REST, True),
                     (LENGTH, REST, True)])


POINTER = _path()
CLICKS = [(f, f + CLICK) for f in (36, 40, 78, 82, START, PAUSE, EXIT_CLICK, MINIMISE_CLICK)]


def mouse_offset(f):
    return P.mouse_offset(POINTER.at(f), REST, GAIN, MOUSE["turn"])


LIGHTS = dict(hdd_light=[(LOAD[0] + 2, LOAD[1], "flicker")])


def lit(name, f):
    for f0, f1, mode in LIGHTS[name]:
        if f0 <= f < f1:
            return mode == "on" or (f // 2) % 5 not in (1, 3)
    return False
