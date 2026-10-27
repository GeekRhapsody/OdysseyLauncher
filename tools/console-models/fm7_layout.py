"""The FM-7 card's measurements (computer.py's card `fm7`; computer_layout.py says what a card holds).

Fujitsu's FM-7 (1982), a colour display behind it and a data recorder (unbranded) beside it: the computer 430 x 288 x
100 mm (Wikipedia), the display a 14-inch colour CRT of about 360 x 380 x 330 (from an advertisement); the parts placed
from photographs of it (and of the FM-NEW7, the same case). The computer: the deck rising gently from its rounded lip,
the keys on it (the two rows of PF keys, the editing and cursor keys set apart at the back; the main block, the letters
and digits cream, the rest brown-grey, its tall RETURN; the keypad), the ivory rear housing across the back, FM-7 on its
front, slats across its top, the power switch and its red light in the recess at its right end.

The clip: the recorder's lid swings up, a cassette (a made-up game) drops into its well and the lid shuts; PLAY goes
down and its light comes on while F-BASIC loads the game; its title, and the game played on the keypad's 8, 4, 6 and 2
and the space bar; STOP, the lid opens, the cassette rises out and goes, and the lid shuts.
"""

NAME = "FM-7"
YAW, PITCH = -24.0, 24.0

COLOURS = dict(case="#D5D8C3", housing="#DDD6AA", light="#E2D8A9", dark="#75705A", ink="#202020", white="#F2F2EE",
               monitor="#CDCBBE", recorder="#3A3A3E", smoked="#1E1C1A", keycap="#C8C8C4", red="#D03A2E",
               lit="#FF3A2C", green="#3AE060", shell="#2A2A2E", label="#F2F0E8", window="#3A3430", cable="#1A1A1C")

W = 430.0
BLOCKS = [
    dict(shape=("profile", -W / 2, W / 2, [(0.0, 0.0), (288.0, 0.0), (288.0, 96.0), (284.0, 100.0), (196.0, 100.0),
                                          (193.0, 96.0), (193.0, 58.0), (35.0, 40.0), (8.0, 28.0), (0.0, 20.0)]),
         round=3.0, colour="case",
         faces=dict(front=[("rect", 0.0, 0.0, 430.0, 42.0, "housing"),
                           ("text", "FM-7", "ariblk.ttf", 9.0, 40.0, 22.0, "ink")],
                    top=[("rect", 0.0, 0.0, 430.0, 95.0, "housing"),
                         ("hslots", 10.0, 12.0, 370.0, 84.0, 7, "#B8B088"),
                         ("rect", 380.0, 20.0, 425.0, 75.0, "#C8C098", 3.0),
                         ("rect", 392.0, 34.0, 408.0, 52.0, "ink", 2.0), ("circle", 400.0, 64.0, 2.0, "red"),
                         ("text", "POWER", "arialbd.ttf", 2.4, 400.0, 28.0, "ink")])),
    dict(shape=("box", 230.0, 390.0, -60.0, 170.0, 0.0, 48.0), round=4.0, colour="recorder",
         cuts=[(255.0, 365.0, 20.0, 110.0, 30.0, 60.0)],
         faces=dict(top=[("text", "DATA RECORDER", "arialbd.ttf", 4.0, 80.0, 20.0, "white"),
                         ("text", "000", "consola.ttf", 6.0, 136.0, 40.0, "white")])),
    dict(shape=("box", -150.0, 150.0, 300.0, 520.0, 0.0, 30.0), round=6.0, colour="monitor"),
]
for k in range(6):
    if k != 2:
        BLOCKS.append(dict(shape=("box", 240.0 + 23.5 * k, 261.0 + 23.5 * k, -50.0, -14.0, 44.0, 54.0), round=1.5,
                           colour="keycap"))

U = 19.05
X0 = -214.0
S5 = 6.0
S = [S5 + 4 * U, S5 + 3 * U, S5 + 2 * U, S5 + U, S5]
F1 = S5 + 5 * U + 3.0
F2 = F1 + 14.0
KP = 16.0

KEYBOARD = dict(
    origin=(0.0, 30.0, 38.0), slope=6.5, U=U, gap=1.2, height=9.0, taper=2.2, ink="ink", legend=3.0, ground="case",
    inks=dict(dark="white"),
    rows=[
        dict(s=F2, x=X0, depth=13.0, keys=[(None, 1.25)] + [(f"PF{k}", 1.75, "dark") for k in range(6, 11)]
             + [(None, 0.5), ("EL", 1, "dark"), ("CLS", 1, "dark"), (None, 1.75), ("INS", 1, "dark"),
                ("↑", 1, "dark"), ("DEL", 1, "dark")]),
        dict(s=F1, x=X0, depth=13.0, keys=[("BREAK", 1, "dark"), (None, 0.25)]
             + [(f"PF{k}", 1.75, "dark") for k in range(1, 6)] + [(None, 0.5), ("DUP", 1, "dark"),
                                                                    ("HOME", 1, "dark"), (None, 1.75),
                                                                    ("←", 1, "dark"), ("↓", 1, "dark"),
                                                                    ("→", 1, "dark")]),
        dict(s=S[0], x=X0, keys=[("ESC", 1, "dark")] + [(c, 1, "light") for c in "1234567890-^¥"]
             + [("BS", 1.5, "dark"), (None, 0.5), ("*", 1, "dark"), ("/", 1, "dark"), ("+", 1, "dark"),
                ("-", 1, "dark")]),
        dict(s=S[1], x=X0, keys=[("TAB", 1.75, "dark")] + [(c, 1, "light") for c in "QWERTYUIOP@["]
             + [("↵", 1.25, "dark", 2), (None, 1.0), ("7", 1, "light"), ("8", 1, "light"), ("9", 1, "light"),
                ("=", 1, "dark")]),
        dict(s=S[2], x=X0, keys=[("CTRL", 1.75, "dark")] + [(c, 1, "light") for c in "ASDFGHJKL;:]"]
             + [(None, 2.25), ("4", 1, "light"), ("5", 1, "light"), ("6", 1, "light"), (",", 1, "dark")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 2.25, "dark")] + [(c, 1, "light") for c in "ZXCVBNM,./_"]
             + [("SHIFT", 2.25, "dark"), (None, 0.5), ("1", 1, "light"), ("2", 1, "light"), ("3", 1, "light"),
                ("↵", 1, "dark", 2)]),
        dict(s=S[4], x=X0, keys=[(None, 1.5), ("CAP", 1.25, "dark"), ("GRAPH", 1.5, "dark"), (" ", 8.5, "dark"),
                                 ("カナ", 1.25, "dark"), (None, 2.0), ("0", 2, "light"), (".", 1, "light")]),
    ])

DISPLAY = dict(at=(0.0, 310.0, 30.0), size=(360.0, 300.0, 70.0), back=(290.0, 230.0, 290.0), radius=12.0,
               colour="monitor", glass=(270.0, 202.0), glass_at=(0.0, 160.0), recess=22.0, bulge=8.0, frame=12.0,
               corner=12.0, back_dz=6.0,
               faces=dict(front=[("rect", 300.0, 272.0, 330.0, 286.0, "#9A9888", 3.0),
                                 ("circle", 290.0, 279.0, 1.8, "lit")]))

LID_HINGE = (310.0, 113.0, 49.0)
MOVERS = [dict(name="lid", shape=("box", 253.0, 367.0, 17.0, 113.0, 46.0, 52.0), round=1.5, colour="smoked",
               origin=LID_HINGE,
               faces=dict(top=[("rect", 22.0, 22.0, 92.0, 70.0, "window", 3.0)]),
               keys=[(0, dict()), (4, dict()), (12, dict(pitch=-62.0)), (32, dict(pitch=-62.0)), (40, dict()),
                     (190, dict()), (198, dict(pitch=-62.0)), (220, dict(pitch=-62.0)), (228, dict())]),
          dict(name="play", shape=("box", 287.0, 308.0, -50.0, -14.0, 44.0, 54.0), round=1.5, colour="keycap",
               origin=(297.5, -32.0, 54.0),
               keys=[(0, dict()), (42, dict()), (46, dict(z=-5.0)), (186, dict(z=-5.0)), (190, dict())])]

MEDIA = dict(kind="box", size=(100.0, 63.0, 12.0), seat=(310.0, 65.0, 37.0), colour="shell",
             label=[("rect", 6.0, 4.0, 94.0, 40.0, "label", 1.5), ("logo", 10.0, 6.0, 90.0, 26.0),
                    ("rect", 26.0, 30.0, 74.0, 38.0, "window", 3.0), ("circle", 36.0, 34.0, 3.0, "white"),
                    ("circle", 64.0, 34.0, 3.0, "white")],
             keys=[(0, dict(z=70.0, scale=0.0)), (8, dict(z=70.0, scale=0.0)), (16, dict(z=70.0)), (30, dict()),
                   (200, dict()), (210, dict(z=70.0)), (212, dict(z=70.0)), (222, dict(z=90.0, scale=0.0))])

LIGHTS = [dict(name="play_light", at=(380.0, -30.0, 48.0), face="top", size=(4.0, 4.0), colour="green",
               on=[(46, 186, "on")])]

CABLES = [dict(points=[(230.0, 100.0, 20.0), (200.0, 140.0, 4.0), (180.0, 230.0, 4.0), (150.0, 289.0, 30.0)], r=2.2,
               colour="cable")]

PRESS = {"8": (110, 150), "4": (122, 170), "6": (134, 180), "2": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(640, 200), palette=["#000000", "#0000FF", "#FF0000", "#FF00FF", "#00FF00", "#00FFFF", "#FFFF00",
                                      "#FFFFFF"],
              ink="#FFFFFF", paper="#000000", border=("#000000", 0.06), prompt="HIT SPACE KEY",
              boot=["FUJITSU F-BASIC Version 3.0", "Copyright (C) 1981 by FUJITSU", "30358 Bytes Free", "Ready"],
              load=["FUJITSU F-BASIC Version 3.0", "Copyright (C) 1981 by FUJITSU", "30358 Bytes Free", "Ready",
                    'LOADM"FAIRWAY",,R', "Searching", "Found:FAIRWAY"],
              game=("Fairway Legends (Europe)", "snes"))
SHOW = [(48, 80, "load"), (80, 100, "title"), (100, 188, "game")]
