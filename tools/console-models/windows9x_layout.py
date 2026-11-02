"""The Windows 9x card's set, which retro_pc.py builds (retro_pc_layout.py has the parts it shares with the DOS and
Windows 3.x cards' sets), and the timing its clip and its video (windows9x_screens.py, retro_pc_video.py) share. Plain
Python: Blender's Python imports it too.

A PC of about 1998: a beige ATX mini tower of the time's clones (190 x 430 x 420 mm), a 15-inch monitor on its
tilt-and-swivel foot on the desk at its right, a 104-key keyboard (the Windows and menu keys of the late 1990s) and a
two-button mouse on its pad. The tower's front (FRONT, drawn by retro_pc_print.py): a 24-speed CD-ROM drive with its
tray, a blank bay and the 3.5-inch drive, the badge, the round power button, the lights, RESET, the vents and the
speed's sticker. The tower stands on the monitor's left: the focused card sways that way, bringing it forward.

Millimetres: x from the tower's middle (left to right), y back from its front, z up from the desk. The screen's places
are in its 640 x 480 pixels.

The clip (frames at FPS; windows9x_screens.py draws the screen to it, frame for frame), the mouse moving as the pointer
does (pointer_path.py): the desktop (the still). The CD-ROM's eject button is pressed and its tray slides out; a CD (a
made-up game, Apex Circuit) appears over it tipped to show its label and drops into its well; the button again, and the
tray takes it in; the drive's light flickers, and the game's AutoPlay window comes up. The pointer clicks Play: the
screen goes black and the game loads, then the race: the road drawn in perspective, the coast behind it, the player's
car from behind, steered on the arrows (each going down as the car turns), up held all the way, rivals passed. ESC, and
the AutoPlay window again; the pointer clicks Exit. The eject button, the tray out, the CD lifted out and gone, the
button, the tray in; the pointer back to rest.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pointer_path as P  # noqa: E402
import retro_pc_layout as K  # noqa: E402

NAME = "Windows 9x"
YAW, PITCH = -24.0, 18.0

COLOURS = dict(case="#D8D2C2", bezel="#E0DACB", monitor="#DDD7C8", stand="#D2CCBC", key="#ECE8DC", mod="#C9C3B4",
               kbcase="#DCD6C7", dark="#1A1A1C", lit_red="#FF4A2E", lit_green="#62FF7A", lit_amber="#FFB43A",
               mouse="#E2DCCD", pad="#3A3A42", cable="#3A3631", tray="#2C2C30", disc="#C8CACF")
SWATCHES = K.swatches(sorted(COLOURS))
PRINT_REGIONS = dict(kb_top=(0, 0, 1024, 427), mouse_top=(0, 440, 120, 216), pad=(136, 440, 464, 384),
                     cd=(616, 440, 360, 360))
DEVICE_REGIONS = dict(front=(0, 0, 442, 963), monitor=(452, 0, 568, 552), back=(452, 566, 196, 428),
                      tray_top=(660, 566, 266, 348))
CD_LABEL = dict(art="apex-circuit", system="snes", stem="Apex Circuit (Europe)",
                line="WINDOWS 95/98 CD-ROM  ·  © 1998 ARCWAVE")

# ---- The tower -------------------------------------------------------------------------------------------------------
CASE = dict(kind="tower", width=190.0, depth=430.0, height=420.0, feet=8.0, bezel=20.0, at=(0.0, 0.0), plate=False)
FRONT = [
    ("cdrom", 22.0, 26.0, 146.0, 41.3, 1.5, ""),
    ("blank525", 22.0, 70.0, 146.0, 41.3, 1.0, ""),
    ("floppy35", 44.2, 124.0, 101.6, 25.4, 1.5, ""),
    ("badge", 20.0, 172.0, 150.0, 22.0, 0.0, "ODYSSEY|"),
    ("power", 70.0, 206.0, 50.0, 30.0, 4.0, ""),
    ("leds", 50.0, 246.0, 90.0, 18.0, 0.0, "POWER:#36E05A|HDD:#F2A93A:off"),
    ("button", 85.0, 270.0, 20.0, 9.0, 2.5, "RESET"),
    ("vents", 30.0, 294.0, 130.0, 70.0, 0.0, ""),
    ("sticker", 120.0, 374.0, 44.0, 24.0, 0.0, "300|MHz"),
]
# The CD-ROM drive's parts in the front's millimetres (retro_pc_print.cdrom()'s): its tray's front, its eject button
# (a0, a1, b0, b1, how far proud the drive's face is, unused) and its light.
TRAY = dict(front=(26.0, 164.0, 33.0, 51.0), face=1.5, depth=176.0, thickness=7.0, travel=150.0, well=72.0)
EJECT = (134.0, 156.0, 54.5, 61.5, 1.5, 0.0)
CD_LIGHT = (100.0, 58.25)
HDD_LIGHT = (50.0 + 90.0 * 3 / 4, 246.0 + 18.0 * 0.36)
LIGHT_PARTS = dict(cd_light=(CD_LIGHT[0], CD_LIGHT[1], 1.5, (8.0, 2.5), "lit_amber", False),
                   hdd_light=(HDD_LIGHT[0], HDD_LIGHT[1], 0.0, (4.0, 4.0), "lit_amber", True))

# ---- The monitor, on the desk at the tower's right -------------------------------------------------------------------
MONITOR = dict(at=(305.0, 40.0, 0.0), width=380.0, height=368.0, shell=74.0, foot=(118.0, 26.0),
               rear=dict(size=(336.0, 310.0), end=(226.0, 214.0), depth=318.0, rise=16.0),
               opening=(318.0, 246.0, 20.0), inner=(290.0, 220.0, 12.0), recess=26.0, bulge=6.0, screen_z=212.0,
               strip=[("osd", 30.0, 324.0, 90.0, 12.0, 1.5, ""),
                      ("brand", 140.0, 318.0, 110.0, 24.0, 0.0, "ODYSSEY|"),
                      ("led", 306.0, 327.0, 6.0, 6.0, 0.0, "#36E05A"),
                      ("power", 320.0, 320.0, 26.0, 20.0, 4.0, "")])

# ---- The keyboard, the mouse and its pad -----------------------------------------------------------------------------
KEYBOARD = dict(at=(300.0, -262.0), turn=0.0, windows=True)
CABLES = [dict(name="cord", r=2.5, points=[(220.0, -66.0, 12.0), (206.0, -40.0, 3.0), (150.0, -16.0, 3.0),
                                            (100.0, 10.0, 3.0), (96.0, 80.0, 3.0)])]
MOUSE = dict(at=(668.0, -176.0), turn=-6.0, pad=(664.0, -170.0), pad_turn=-4.0)

# ---- The screen, in its pixels ---------------------------------------------------------------------------------------
TASKBAR = 452                         # the taskbar's top
ICONS = [("My Computer", "computer", (34, 34)), ("Recycle Bin", "bin", (34, 104)), ("Inbox", "inbox", (34, 174)),
         ("The Internet", "globe", (34, 244))]
LAUNCHER = (96, 70, 544, 398)         # Apex Circuit's AutoPlay window
BUTTONS = [("Play", (412, 168)), ("Install", (412, 214)), ("Explore CD", (412, 260)), ("Exit", (412, 334))]
BUTTON_SIZE = (120, 34)

# ---- The clip, in frames at FPS --------------------------------------------------------------------------------------
FPS = 30
CLICK = 4
EJECTS = (14, 64, 316, 368)           # the eject button pressed: the tray out, in, out, in
TRAY_MOVE = 14                        # frames the tray takes
CD_IN = (30, 38, 48, 58)              # the CD appears over the tray tipped; holds; levels; drops into the well
CD_OUT = (334, 340, 352)              # lifted out of the well; held up; gone
READ = (82, 106)                      # the drive's light flickering; AutoPlay comes up at its end
CLICK_PLAY = 126
LOADING = (130, 156)                  # the screen black, then the game's loading screen
RACE = (156, 278)                     # the race
QUIT = 278                            # ESC: AutoPlay again
CLICK_EXIT = 304
LENGTH = 392

REST = (500.0, 320.0)
GAIN = 9.0


def _path():
    play, exit_ = BUTTONS[0][1], BUTTONS[3][1]
    return P.Path([(0, REST, True), (108, REST, True), (CLICK_PLAY - 2, play, True), (CLICK_PLAY + 6, play, True),
                   (QUIT + 4, play, True), (CLICK_EXIT - 2, exit_, True), (CLICK_EXIT + 6, exit_, True),
                   (CLICK_EXIT + 34, REST, True), (LENGTH, REST, True)])


POINTER = _path()
CLICKS = [(CLICK_PLAY, CLICK_PLAY + CLICK), (CLICK_EXIT, CLICK_EXIT + CLICK)]


def mouse_offset(f):
    return P.mouse_offset(POINTER.at(f), REST, GAIN, MOUSE["turn"])


# The race: the road's curves by its distance (segments ahead), and the steering: the left or right arrow held as the
# car turns into each curve; up held all the way, ESC at the end.
CURVES = [(40, 70, 2.2), (120, 150, -2.6), (190, 220, 1.8)]     # (first segment, last, curvature)
SPEED = 2.2                                                      # segments a frame
STEER = [(176, 196, "right"), (210, 232, "left"), (246, 262, "right")]
PRESSES = dict(up=[(RACE[0] + 2, RACE[1] - 4)], esc=[(QUIT, QUIT + 2)],
               right=[(a, b) for a, b, k in STEER if k == "right"], left=[(a, b) for a, b, k in STEER if k == "left"])

LIGHTS = dict(cd_light=[(READ[0], READ[1], "flicker"), (LOADING[0], LOADING[1], "flicker")],
              hdd_light=[(LOADING[0] + 4, LOADING[1] - 2, "flicker")])


def lit(name, f):
    for f0, f1, mode in LIGHTS[name]:
        if f0 <= f < f1:
            return mode == "on" or (f // 2) % 5 not in (1, 3)
    return False


def tray(f):
    """How far the tray is out at frame f (mm): it slides out after the first and third ejects, in after the others."""
    out = 0.0
    for k, at in enumerate(EJECTS):
        if f < at + 2:
            break
        t = K.smooth(K.phase(f, at + 2, at + 2 + TRAY_MOVE))
        out = t if k % 2 == 0 else 1 - t
    return TRAY["travel"] * out


def eject(f):
    """The eject button's travel at frame f (mm towards the viewer): pressed in at each eject."""
    return -1.0 * K.pressed(f, [(at, at + 3) for at in EJECTS])


HOVER = (78.0, 38.0)                 # where the CD is shown over the tray: in front of its well, above it


def cd(f):
    """The CD's pose at frame f, from its seat in the tray's well (it rides the tray): dict(y, z, pitch, scale)."""
    a, b, c, d = CD_IN
    o0, o1, o2 = CD_OUT
    if f < a or f >= o2:
        return dict(scale=0.0)
    if f < b:
        return dict(z=HOVER[1], y=-HOVER[0], pitch=40.0, scale=K.back_out(K.phase(f, a, b), 1.4))
    if f < c:
        return dict(z=HOVER[1] + 2.0 * K.smooth(K.phase(f, b, c)), y=-HOVER[0], pitch=40.0)
    if f < d:
        t = K.smooth(K.phase(f, c, d))
        return dict(z=(HOVER[1] + 2.0) * (1 - t), y=-HOVER[0] * (1 - t), pitch=40.0 * (1 - t))
    if f < o0:
        return dict(z=0.8 * K.smooth(K.phase(f, d, d + 2)) * (1 - K.smooth(K.phase(f, d + 2, d + 5))))
    if f < o1:
        t = K.smooth(K.phase(f, o0, o1))
        return dict(z=HOVER[1] * t, y=-HOVER[0] * t, pitch=36.0 * t)
    t = K.phase(f, o1, o2)
    return dict(z=HOVER[1] + 12.0 * K.ease_out(t), y=-HOVER[0], pitch=36.0, scale=1 - K.ease_in(t))
