"""The DOS card's set, which retro_pc.py builds (retro_pc_layout.py has the parts it shares with the Windows 3.x and 9x
cards' sets), and the timing its clip and its video (dos_screens.py, retro_pc_video.py) share. Plain Python: Blender's
Python imports it too.

A PC of about 1991: a 386 desktop in the "baby AT" case of the time's clones (420 x 400 x 150 mm), a 14-inch VGA
monitor on its tilt-and-swivel foot on top, and a 101-key keyboard in front. The case's front (FRONT, drawn by
retro_pc_print.py; its parts standing proud of it by their depth): on the left the badge, the turbo display reading 33
(MHz) in red segments, the POWER, TURBO and HDD lights, the TURBO and RESET buttons, the keylock and the vents; on the
right drive A, a 3.5-inch drive in a 5.25-inch bay's frame, over drive B, a 5.25-inch one, and the power switch under
them. The monitor (MONITOR): its bezel round the screen's opening, which slopes in to the curved glass; under it the
badge, two knobs, the power light and the button; the tube's housing tapering behind; the foot.

Millimetres: x from the case's middle (left to right), y back from its front, z up from the desk. A front's parts are
(kind, a, b, w, h, depth, text): a across from the face's left edge, b down from its top.

The clip (frames at FPS; dos_screens.py draws the screen to it, frame for frame): the screen is a file commander at
C:\\GAMES (the still). A 3.5-inch floppy (a made-up game, Rotorstorm) appears in front of drive A tipped to show its
label, levels at the slot and slides in, and the eject button pops out; `a:` is typed on the commander's command line,
each key going down as its character appears (SHIFT with ; for the colon), and ENTER: the drive's light comes on and the
panel lists A:\\; `rotor` and ENTER: the screen clears, the light flickers while the game loads, and its title comes up
in VGA's 256 colours; ENTER, and the game is played on the arrows and the space bar; ESC: its goodbye screen, then the
commander again (the hard disk's light flickers as it reloads); the eject button is pressed and the floppy comes out
and goes; `c:` and ENTER, and the panel is back at C:\\GAMES, the first frame.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retro_pc_layout as K  # noqa: E402

NAME = "DOS"
YAW, PITCH = -24.0, 20.0

COLOURS = dict(case="#CDC09F", bezel="#D7CBAC", monitor="#D5C9AB", stand="#C8BC9E", key="#E5DDC8", mod="#BCB29A",
               kbcase="#CEC2A4", dark="#1A1A1C", slot="#0C0C0E", lit_green="#62FF7A", lit_red="#FF4A2E",
               disk="#2A2D33", shutter="#B9BCC2", cable="#3A3631")
SWATCHES = K.swatches(sorted(COLOURS))

# Two atlases (retro_pc_print.py): `print` (the keyboard from above, the floppy's two sides) and `devices` (the case's
# front, the monitor's front). A region is (x, y, width, height) in pixels.
PRINT_REGIONS = dict(kb_top=(0, 0, 1024, 427), floppy=(0, 440, 240, 251), floppy_under=(256, 440, 240, 251))
DEVICE_REGIONS = dict(front=(0, 0, 1024, 351), monitor=(0, 368, 560, 531), back=(570, 368, 448, 154))

# The floppy's label: the made-up game's logo from the library, its publisher on the band, its lines under the logo.
FLOPPY_LABEL = dict(system="megadrive", stem="Rotorstorm (Europe)", publisher="ARCWAVE", band="#4E5B2E",
                    lines=["ROTORSTORM", "PC VGA  ·  Disk 1 of 1  ·  © 1992"])

# ---- The case --------------------------------------------------------------------------------------------------------
CASE = dict(kind="desktop", width=420.0, depth=400.0, height=150.0, feet=6.0, bezel=20.0, at=(0.0, 0.0))
FRONT = [
    ("badge", 22.0, 18.0, 150.0, 22.0, 0.0, "ODYSSEY|386/33"),
    ("display", 22.0, 52.0, 50.0, 26.0, 0.0, "33"),
    ("leds", 84.0, 52.0, 90.0, 26.0, 0.0, "POWER:#36E05A|TURBO:#F2D33A|HDD:#F04A3A:off"),
    ("button", 22.0, 94.0, 26.0, 13.0, 3.0, "TURBO"),
    ("button", 58.0, 94.0, 26.0, 13.0, 3.0, "RESET"),
    ("keylock", 182.0, 58.0, 18.0, 18.0, 3.0, ""),
    ("vents", 106.0, 92.0, 104.0, 40.0, 0.0, ""),
    ("floppy35adapter", 250.0, 16.0, 146.0, 41.3, 1.5, "A"),
    ("floppy525", 250.0, 62.0, 146.0, 41.3, 1.5, "B"),
    ("power", 340.0, 112.0, 46.0, 24.0, 4.0, ""),
]
DRIVE_A = (250.0 + 22.2, 16.0 + 7.95)          # the 3.5-inch drive's face (101.6 x 25.4) in its frame: its top left
SLOT = (DRIVE_A[0] + 4.8, DRIVE_A[0] + 96.8, DRIVE_A[1] + 7.6, DRIVE_A[1] + 12.0)   # its slot: a0, a1, b0, b1
EJECT = (DRIVE_A[0] + 78.0, DRIVE_A[0] + 95.0, DRIVE_A[1] + 15.5, DRIVE_A[1] + 21.0, 1.5, 2.5)   # its eject button:
#   a0, a1, b0, b1, how far proud its face is, how far the button stands out with a disk in
A_LIGHT = (8.0, 14.0, 17.0, 19.5)               # its light, on its face
HDD_LIGHT = (84.0 + 90.0 * 5 / 6, 52.0 + 26.0 * 0.36)   # the HDD light's middle (a, b): leds()'s third

# ---- The monitor: its front's bottom middle at `at`, on its foot -----------------------------------------------------
MONITOR = dict(at=(0.0, 34.0, 150.0), width=344.0, height=326.0, shell=62.0, foot=(112.0, 22.0),
               rear=dict(size=(300.0, 272.0), end=(200.0, 186.0), depth=292.0, rise=16.0),
               opening=(290.0, 224.0, 16.0), inner=(266.0, 202.0, 9.0), recess=24.0, bulge=5.0, screen_z=184.0,
               strip=[("brand", 22.0, 284.0, 120.0, 20.0, 0.0, "ODYSSEY|VGA 14"),
                      ("knob", 224.0, 288.0, 15.0, 15.0, 4.0, ""),
                      ("knob", 248.0, 288.0, 15.0, 15.0, 4.0, ""),
                      ("led", 282.0, 293.0, 6.0, 6.0, 0.0, "#36E05A"),
                      ("button", 298.0, 285.0, 24.0, 20.0, 4.0, "")])

# ---- The keyboard: its front's middle on the desk, turned ------------------------------------------------------------
KEYBOARD = dict(at=(-6.0, -282.0), turn=3.0, windows=False)
CABLES = [dict(name="cord", r=2.6, points=[(-86.0, -86.0, 14.0), (-100.0, -60.0, 4.0), (-150.0, -20.0, 3.0),
                                            (-196.0, 30.0, 3.0), (-206.0, 90.0, 3.0)])]

# ---- The clip, in frames at FPS --------------------------------------------------------------------------------------
FPS = 30
PER_KEY = 4                       # frames between typed characters
DISK_IN = (12, 20, 30, 44, 52)    # appears tipped; holds; levels at the slot; slides in; seated
TYPE_A = 58                       # "a:" typed, then ENTER
READ_A = (72, 88)                 # drive A's light: the commander reads its directory
TYPE_GAME = 94                    # "rotor" typed, then ENTER
LOADING = (118, 150)              # the screen black, the loader's line, drive A's light flickering
TITLE = 150                       # the game's title (VGA), fading in
START = 178                       # ENTER: the game starts
PLAY = (184, 286)                 # flown on the arrows, fired on the space bar
QUIT = 286                        # ESC: the goodbye screen
BACK = 314                        # the commander again, the hard disk's light flickering
EJECT_AT = 322                    # the eject button: the floppy pops out, and goes
TYPE_C = 346                      # "c:" typed, then ENTER: C:\GAMES again
BLINK = 8                         # the cursor's frames on, then off; it starts on at each keystroke


def typed(text, at):
    """[(frame, character)]: text typed from frame at, PER_KEY frames apart, then ENTER ("\\n")."""
    return [(at + k * PER_KEY, ch) for k, ch in enumerate(text)] + [(at + len(text) * PER_KEY + 2, "\n")]


TYPING = typed("a:", TYPE_A) + typed("rotor", TYPE_GAME) + typed("c:", TYPE_C)
LENGTH = TYPING[-1][0] + 2 * BLINK   # the cursor's blink comes round to on as the clip loops, as it starts

# The game: the gunship's height on the screen (VGA's 320 x 200 pixels) at its frames, eased between them; the up and
# down arrows held while it climbs and dives; the space bar's shots; the right arrow held all the way.
HELI = [(184, 96.0), (198, 96.0), (210, 70.0), (228, 70.0), (242, 112.0), (258, 112.0), (270, 86.0), (286, 86.0)]
FIRE = (194, 216, 248, 272)       # a rocket each, at a gunship coming in at the gunship's height
FLIGHT = 10                       # frames a rocket flies to its target

# The keys the clip presses: {key name: [(down, up)]} (retro_pc_layout.keys()'s names).
_CHARS = {"a": "a", ":": "semicolon", "r": "r", "o": "o", "t": "t", "c": "c", "\n": "enter"}


def presses():
    out = {}
    for f, ch in TYPING:
        out.setdefault(_CHARS[ch], []).append((f, f + 2))
        if ch == ":":
            out.setdefault("lshift", []).append((f - 3, f + 4))
    out["enter"].append((START, START + 2))
    out["esc"] = [(QUIT, QUIT + 2)]
    out["space"] = [(f, f + 2) for f in FIRE]
    out["right"] = [(PLAY[0] + 2, PLAY[1] - 4)]
    for (f0, a), (f1, b) in zip(HELI, HELI[1:]):
        if b != a:
            out.setdefault("up" if b < a else "down", []).append((f0, f1))
    return out


PRESSES = presses()

# The lights the clip turns on: drive A's (green) and the hard disk's (red), {name: [(f0, f1, "on" or "flicker")]}.
LIGHTS = dict(a_light=[(READ_A[0], READ_A[1], "on"), (LOADING[0], LOADING[1] - 4, "flicker")],
              hdd_light=[(LOADING[0] - 2, LOADING[0] + 4, "flicker"), (BACK, BACK + 12, "flicker")])


# The lights' beads: {name: (a, b, out, (w, h), colour, round)}: their middles on the case's front, how far proud of the
# bezel their face is, their size.
LIGHT_PARTS = dict(a_light=(DRIVE_A[0] + (A_LIGHT[0] + A_LIGHT[1]) / 2, DRIVE_A[1] + (A_LIGHT[2] + A_LIGHT[3]) / 2,
                            1.5, (A_LIGHT[1] - A_LIGHT[0], A_LIGHT[3] - A_LIGHT[2]), "lit_green", False),
                   hdd_light=(HDD_LIGHT[0], HDD_LIGHT[1], 0.0, (4.0, 4.0), "lit_red", True))


def lit(name, f):
    for f0, f1, mode in LIGHTS[name]:
        if f0 <= f < f1:
            return mode == "on" or (f // 2) % 5 not in (1, 3)
    return False


# The floppy's and the eject button's moves, from their seats in drive A, in the set's millimetres and degrees.
OUT_Y, LIFT, TIP = 130.0, 46.0, 38.0   # where the floppy appears: in front of its seat, above it, tipped to the viewer
MOUTH = K.FLOPPY["size"][1] + 1.0      # its trailing edge at the slot's lips when it's this far out
POP = 28.0                             # how far the spring pushes it out when it's ejected


def disk(f):
    """The floppy's pose at frame f: dict(y, z, pitch, scale) from its seat (hidden there at rest)."""
    a, b, c, d, e = DISK_IN
    o = EJECT_AT
    if f < a or f >= o + 26:
        return dict(scale=0.0)
    if f < b:
        return dict(y=-OUT_Y, z=LIFT, pitch=TIP, scale=K.back_out(K.phase(f, a, b), 1.4))
    if f < c:
        return dict(y=-OUT_Y, z=LIFT + 2.0 * K.smooth(K.phase(f, b, c)), pitch=TIP)
    if f < d:
        t = K.smooth(K.phase(f, c, d))
        return dict(y=-OUT_Y + (OUT_Y - MOUTH) * t, z=(LIFT + 2.0) * (1 - t), pitch=TIP * (1 - t))
    if f < e:
        return dict(y=-MOUTH * (1 - K.smooth(K.phase(f, d, e))))
    if f < o + 2:
        return dict(y=1.0 * K.smooth(K.phase(f, e, e + 3)) * (1 - K.smooth(K.phase(f, e + 3, e + 6))))
    if f < o + 8:
        return dict(y=-POP * K.back_out(K.phase(f, o + 2, o + 8), 1.6))
    if f < o + 20:
        t = K.smooth(K.phase(f, o + 8, o + 20))
        return dict(y=-POP - (OUT_Y - POP) * t, z=LIFT * t, pitch=TIP * t)
    t = K.phase(f, o + 20, o + 26)
    return dict(y=-OUT_Y, z=LIFT + 10.0 * K.ease_out(t), pitch=TIP, scale=1 - K.ease_in(t))


def eject(f):
    """The eject button's travel out of the drive's face at frame f (mm, towards the viewer): out while a floppy is in,
    pressed home to eject it."""
    seated = K.smooth(K.phase(f, DISK_IN[4] - 1, DISK_IN[4] + 2)) * (1 - K.smooth(K.phase(f, EJECT_AT, EJECT_AT + 2)))
    return EJECT[5] * seated - 0.8 * K.pressed(f, [(EJECT_AT, EJECT_AT + 3)])
