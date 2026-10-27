"""The IBM PC card's measurements (computer.py's card `pc`; computer_layout.py says what a card holds).

The IBM Personal Computer 5150 (1981), its 5151 display and its 83-key keyboard: the unit 500 x 410 x 142 mm, the
keyboard 500 x 200 x 57, the display 380 x 350 x 280 (IBM's figures); the parts placed from photographs of each from
the front, from above and from the side. The unit's pearl-white front bezel leans back (its foot 40 mm in front of its
top) on the greyer steel cover: the IBM badge, the 17 vents, the two full-height 5.25-inch drives side by side in the
bay, each with its latch across its slot and its light; the red power switch in the right side. The display stands on
the unit, set back, the control strip with its two knobs right of the screen. The keyboard: a wedge, its 83 keys at
19.05 mm (the ten function keys in two columns at the left, the main block, the keypad with its tall +), the badge on
the ledge behind them, its coiled cord round to the unit's back.

The clip: drive A's latch turns open, a 5.25-inch disk (a made-up game) slides in and the latch turns shut; the light
flickers while it loads, the green screen goes from DOS's prompt to the game's title, and it is played on the keypad's
arrows and the space bar; the latch opens, the disk comes out and goes.
"""

NAME = "IBM PC"
YAW, PITCH = -24.0, 22.0

COLOURS = dict(case="#E2DED3", cover="#D3CFC4", monitor="#CFCCC4", strip="#B2B1AF", light="#E6E1D4", dark="#A8A59B",
               bay="#29282D", drive="#1E1E22", metal="#C8C8C4", red="#D33A3A", cable="#1A1A1C", lit="#FF3A2C",
               sleeve="#141416", label="#F2F0E8", ink="#1E1E1E", knob="#141416", phosphor="#46F071")

DRIVE_A, DRIVE_B = (165.0, 311.0), (318.0, 464.0)          # the drives' faceplates across the bezel (a)
SLOT_Z = 64.0

BLOCKS = [
    dict(shape=("box", -250.0, 250.0, 30.0, 410.0, 0.0, 142.0), round=3.0, colour="cover"),
    dict(shape=("profile", -250.0, 250.0, [(0.0, 0.0), (46.0, 0.0), (46.0, 142.0), (40.0, 142.0)]), round=2.0,
         colour="case", cuts=[(-86.0 + 6.0, 61.0 - 6.0, -5.0, 60.0, SLOT_Z - 2.0, SLOT_Z + 2.0)],
         faces=dict(front=[
             ("rect", 27.0, 30.0, 52.0, 58.0, "metal", 1.0), ("text", "IBM", "ariblk.ttf", 7.0, 39.5, 41.0, "#3A3F4A"),
             ("text", "PC", "arialbi.ttf", 3.2, 39.5, 52.0, "#3A3F4A"),
             ("slots", 27.0, 70.0, 152.0, 100.0, 17, "bay"),
             ("rect", 160.0, 35.0, 475.0, 122.0, "bay", 2.0),
             ("rect", DRIVE_A[0], 37.0, DRIVE_A[1], 120.0, "drive", 1.0),
             ("rect", DRIVE_B[0], 37.0, DRIVE_B[1], 120.0, "drive", 1.0),
             ("rect", DRIVE_A[0] + 8.0, 76.0, DRIVE_A[1] - 8.0, 80.0, "#08080A"),
             ("rect", DRIVE_B[0] + 8.0, 76.0, DRIVE_B[1] - 8.0, 80.0, "#08080A"),
             ("rect", (DRIVE_B[0] + DRIVE_B[1]) / 2 - 3.0, 58.0, (DRIVE_B[0] + DRIVE_B[1]) / 2 + 3.0, 98.0, "#3A3A3E",
              1.5),
             ("circle", DRIVE_A[0] + 10.0, 112.0, 1.6, "#5A1A16"), ("circle", DRIVE_B[0] + 10.0, 112.0, 1.6, "#5A1A16"),
             ("text", "A", "arialbd.ttf", 5.0, DRIVE_A[0] + 10.0, 46.0, "label"),
             ("text", "B", "arialbd.ttf", 5.0, DRIVE_B[0] + 10.0, 46.0, "label")])),
    dict(shape=("box", 250.0, 254.0, 340.0, 376.0, 70.0, 106.0), round=1.0, colour="knob"),
    dict(shape=("box", 250.5, 256.0, 344.0, 372.0, 74.0, 102.0), round=1.5, colour="red"),
    dict(shape=("profile", -250.0, 250.0, [(-240.0, 0.0), (-40.0, 0.0), (-40.0, 50.0), (-60.0, 56.0), (-230.0, 30.0),
                                           (-240.0, 24.0)]), round=3.0, colour="case",
         faces=dict(top=[("rect", 54.0, 18.0, 128.0, 30.0, "metal", 1.0), ("text", "IBM", "ariblk.ttf", 5.0, 70.0,
                                                                            24.0, "#3A3F4A"),
                         ("text", "Personal Computer", "arialbi.ttf", 3.4, 104.0, 24.0, "#3A3F4A")])),
]

U = 19.05
X0 = -200.0
ROW_S = [86.2, 67.15, 48.1, 29.05, 10.0]                    # the rows' front edges up the slope, back row first


def _f(a, b):
    return [(a, 1, "dark"), (b, 1, "dark"), (None, 0.3)]


KEYBOARD = dict(
    origin=(0.0, -226.0, 28.5), slope=8.9, U=U, gap=1.2, height=10.0, taper=2.4, ink="ink", legend=3.0, ground="case",
    rows=[
        dict(s=ROW_S[0], x=X0, keys=_f("F1", "F2") + [("Esc", 1, "dark")]
             + [(c, 1, "light") for c in "1234567890-="] + [("←", 1.75, "dark"), ("Num\nLock", 2, "dark"),
                                                            ("Scroll\nLock", 2, "dark")]),
        dict(s=ROW_S[1], x=X0, keys=_f("F3", "F4") + [("Tab", 1.5, "dark")] + [(c, 1, "light") for c in "QWERTYUIOP[]"]
             + [(None, 0.25), ("↵", 1, "dark", 2), ("7", 1, "light"), ("8\n↑", 1, "light"), ("9", 1, "light"),
                ("-", 1, "dark")]),
        dict(s=ROW_S[2], x=X0, keys=_f("F5", "F6") + [("Ctrl", 1.75, "dark")]
             + [(c, 1, "light") for c in "ASDFGHJKL;'`"] + [(None, 1), ("4\n←", 1, "light"), ("5", 1, "light"),
                                                           ("6\n→", 1, "light"), ("+", 1, "dark", 3)]),
        dict(s=ROW_S[3], x=X0, keys=_f("F7", "F8") + [("⇧", 1.25, "dark")] + [(c, 1, "light") for c in "\\ZXCVBNM,./"]
             + [("⇧", 1.5, "dark"), ("PrtSc", 1, "dark"), ("1", 1, "light"), ("2\n↓", 1, "light"), ("3", 1, "light")]),
        dict(s=ROW_S[4], x=X0, keys=_f("F9", "F10") + [("Alt", 1.9, "dark"), (" ", 9.85, "light"),
                                                       ("Caps\nLock", 2, "dark"), ("0\nIns", 2, "light"),
                                                       (".\nDel", 2, "light")]),
    ])

DISPLAY = dict(at=(0.0, 75.0, 148.0), size=(380.0, 272.0, 70.0), back=(300.0, 220.0, 280.0), radius=22.0,
               colour="monitor", glass=(250.0, 190.0), glass_at=(-22.0, 140.0), recess=24.0, bulge=8.0, frame=8.0,
               corner=16.0, back_dz=6.0,
               faces=dict(front=[("rect", 334.0, 20.0, 372.0, 252.0, "strip", 3.0),
                                 ("rect", 338.0, 30.0, 368.0, 44.0, "metal", 1.0),
                                 ("text", "IBM", "ariblk.ttf", 5.0, 353.0, 37.0, "#3A3F4A"),
                                 ("circle", 353.0, 150.0, 9.0, "knob"), ("circle", 353.0, 190.0, 9.0, "knob"),
                                 ("text", "◐", "seguisym.ttf", 5.0, 353.0, 136.0, "#3A3A3A"),
                                 ("text", "☀", "seguisym.ttf", 5.0, 353.0, 176.0, "#3A3A3A")]))

DRIVE_X = (DRIVE_A[0] + DRIVE_A[1]) / 2 - 250.0
SEAT_Y = 84.0
OUT = -150.0
MEDIA = dict(kind="box", size=(133.0, 133.0, 1.6), seat=(DRIVE_X, SEAT_Y, SLOT_Z), colour="sleeve",
             label=[("circle", 66.5, 66.5, 19.0, "#08080A"), ("circle", 66.5, 66.5, 14.0, "#5A5A5E"),
                    ("rect", 64.0, 100.0, 69.0, 118.0, "#08080A", 2.0),
                    ("rect", 14.0, 6.0, 119.0, 40.0, "label", 1.0), ("logo", 18.0, 8.0, 115.0, 38.0)],
             keys=[(0, dict(y=OUT, scale=0.0)), (8, dict(y=OUT, scale=0.0)), (16, dict(y=OUT)), (32, dict(y=0.0)),
                   (198, dict(y=0.0)), (212, dict(y=OUT)), (218, dict(y=OUT)), (228, dict(y=OUT, z=30.0, scale=0.0))])

MOVERS = [dict(name="latch", shape=("box", DRIVE_X - 4.0, DRIVE_X + 4.0, 7.0, 14.0, SLOT_Z - 20.0, SLOT_Z + 20.0),
               round=1.0, colour="bay", origin=(DRIVE_X, 10.0, SLOT_Z),
               keys=[(0, dict()), (4, dict()), (10, dict(roll=90.0)), (34, dict(roll=90.0)), (40, dict()),
                     (192, dict()), (198, dict(roll=90.0)), (220, dict(roll=90.0)), (226, dict())])]

LIGHTS = [dict(name="drive_light", at=(DRIVE_A[0] + 10.0 - 250.0, 8.6, 30.0), face="front", size=(3.4, 2.4),
               colour="lit", on=[(42, 92, "flicker"), (192, 198, "flicker")])]

CABLES = [dict(points=[(-180.0, -40.0, 26.0), (-196.0, -20.0, 6.0), (-262.0, 40.0, 3.0), (-262.0, 300.0, 3.0),
                       (-240.0, 412.0, 30.0)], r=2.6, colour="cable")]

PRESS = {"8\n↑": (110, 150), "4\n←": (122, 170), "6\n→": (134, 180), "2\n↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(400, 200), palette=["#0A140C", "#2E8A48", "#46F071", "#B8FFC8"], ink="phosphor", paper="#0A140C",
              border=("#0A140C", 0.06), title_ink="phosphor", prompt="PRESS SPACE",
              boot=["", "Current date is Tue  1-01-1980", "Enter new date:", "Current time is  0:00:12.34",
                    "Enter new time:", "", "A>"],
              load=["", "A>MANOR", "", "BLACKWATER MANOR", "Loading..."],
              game=("Blackwater Manor (Europe)", "n64"))
SHOW = [(44, 72, "load"), (72, 98, "title"), (98, 196, "game")]
