"""The PC-88 card's measurements (computer.py's card `pc88`; computer_layout.py says what a card holds).

NEC's PC-8801mkII SR (1985), its keyboard and a PC-KD851 display: the unit 406.5 x 345 x 127 mm and the keyboard 412 x
195 x 32 (NEC's spec tables), the display about 365 x 380 x 300 (scaled from an advertisement); the parts placed from
photographs. The ivory unit's front in three bands: the two half-height 5.25-inch drives side by side (DRIVE 2, DRIVE 1)
and the mode lamps' panel; the NEC badge and the square POWER button; RESET, the flap and the keyboard's socket, set
back. The keyboard: the function row apart at the back (STOP, COPY, f·1 to f·5, ROLL UP and DOWN, the arrows over the
keypad), the main block with its tall RETURN, the keypad; the letters light grey, the rest dark warm grey; its coiled
cord to the unit's socket. The display stands on the unit.

The clip: DRIVE 1's latch turns up, a disk (a made-up game) slides in and the latch turns down over it; the light
flickers while N88-BASIC runs it; the game's title, and the game played on the arrows and the space bar; the latch
turns up, the disk comes out and goes.
"""

NAME = "PC-88"
YAW, PITCH = -24.0, 22.0

COLOURS = dict(case="#E8E3D0", bezel="#EAD8AC", back="#9C9480", kbd="#D6D8D0", light="#CACBC4", dark="#6C6D64",
               ink="#202020", white="#F2F2EE", slot="#2A2620", lit="#FF3A2C", sleeve="#141416", label="#F2F0E8",
               cable="#C8CAC2", lamp="#5A3A20")

W = 406.5
DRIVE_2, DRIVE_1 = (22.0, 177.0), (180.0, 335.0)
SLOT_Z = 127.0 - 29.0
D1_X = (DRIVE_1[0] + DRIVE_1[1]) / 2 - W / 2


def drive(a0, a1, name):
    return [("rect", a0, 6.0, a1, 53.0, "bezel", 1.5), ("rect", a0 + 8.0, 27.0, a1 - 8.0, 31.0, "slot", 1.0),
            ("circle", a1 - 12.0, 13.0, 1.8, "#5A1A16"), ("text", name, "arialbd.ttf", 3.0, (a0 + a1) / 2, 57.0, "ink")]


BLOCKS = [
    dict(shape=("box", -W / 2, W / 2, 0.0, 345.0, 0.0, 127.0), round=3.0, colour="case",
         cuts=[(D1_X - 70.0, D1_X + 70.0, -5.0, 60.0, SLOT_Z - 2.0, SLOT_Z + 2.0)],
         faces=dict(front=drive(*DRIVE_2, "DRIVE 2") + drive(*DRIVE_1, "DRIVE 1") + [
             ("slots", 6.0, 8.0, 20.0, 52.0, 4, "back"), ("slots", 392.0, 8.0, 402.0, 52.0, 3, "back"),
             ("text", "N-MODE", "arialbd.ttf", 2.6, 384.0, 16.0, "ink", "rm"),
             ("text", "N88V1-MODE", "arialbd.ttf", 2.6, 384.0, 28.0, "ink", "rm"),
             ("text", "N88V2-MODE", "arialbd.ttf", 2.6, 384.0, 40.0, "ink", "rm"),
             ("rect", 386.0, 14.0, 390.0, 17.0, "lamp"), ("rect", 386.0, 26.0, 390.0, 29.0, "lamp"),
             ("rect", 386.0, 38.0, 390.0, 41.0, "lamp"),
             ("line", [(4.0, 60.0), (402.0, 60.0)], "back", 0.6), ("line", [(4.0, 86.0), (402.0, 86.0)], "back", 0.6),
             ("text", "NEC", "arialbi.ttf", 7.0, 30.0, 73.0, "ink"), ("line", [(42.0, 66.0), (42.0, 80.0)], "ink", 0.5),
             ("text", "PC-8801mkIISR", "arialbd.ttf", 5.0, 48.0, 71.0, "ink", "lm"),
             ("text", "PERSONAL COMPUTER", "arial.ttf", 2.4, 48.0, 78.5, "ink", "lm"),
             ("text", "POWER", "arialbd.ttf", 3.0, 358.0, 73.0, "ink"),
             ("rect", 22.0, 98.0, 46.0, 112.0, "back", 7.0), ("rect", 25.0, 100.0, 43.0, 110.0, "bezel", 5.0),
             ("text", "RESET", "arialbd.ttf", 2.6, 34.0, 94.0, "ink"),
             ("frame", 120.0, 92.0, 280.0, 120.0, "back", 0.6, 2.0),
             ("rect", 340.0, 98.0, 380.0, 116.0, "back", 3.0), ("circle", 360.0, 107.0, 6.0, "#1A1A1A"),
             ("text", "KEY BOARD", "arialbd.ttf", 2.4, 360.0, 94.0, "ink")])),
    dict(shape=("box", 165.0, 189.0, -3.0, 0.5, 42.0, 64.0), round=1.5, colour="bezel"),
    dict(shape=("profile", -206.0, 206.0, [(-235.0, 0.0), (-40.0, 0.0), (-40.0, 32.0), (-58.0, 32.0), (-228.0, 20.0),
                                           (-235.0, 15.0)]), round=3.0, colour="kbd",
         faces=dict(top=[("text", "NEC", "arialbi.ttf", 5.0, 300.0, 12.0, "ink"),
                         ("text", "PC-8801mkIISR", "arialbd.ttf", 3.6, 334.0, 12.0, "ink"),
                         ("text", "PERSONAL COMPUTER", "arial.ttf", 2.2, 334.0, 17.0, "ink")])),
]

U = 19.05
X0 = -190.5
S5 = 8.0
ROW_S = [S5 + 4 * U, S5 + 3 * U, S5 + 2 * U, S5 + U, S5]
FROW = S5 + 5 * U + 5.0

KEYBOARD = dict(
    origin=(0.0, -222.0, 21.0), slope=4.0, U=U, gap=1.2, height=9.0, taper=2.2, ink="ink", legend=3.0, ground="kbd",
    inks=dict(dark="white"),
    rows=[
        dict(s=FROW, x=X0, depth=15.0, keys=[("STOP", 1, "dark"), ("COPY", 1, "dark"), (None, 0.5)]
             + [(f"f·{k}", 2, "dark") for k in range(1, 6)] + [(None, 0.5), ("ROLL\nUP", 1, "dark"),
                                                                 ("ROLL\nDOWN", 1, "dark"), (None, 1.0), ("↑", 1, "dark"),
                                                                 ("↓", 1, "dark"), ("←", 1, "dark"), ("→", 1, "dark")]),
        dict(s=ROW_S[0], x=X0, keys=[("ESC", 1.25, "dark")] + [(c, 1, "light") for c in "1234567890-^¥"]
             + [("INS\nDEL", 1.25, "dark"), (None, 0.5), ("HOME\nCLR", 1, "dark"), ("HELP", 1, "dark"),
                ("-", 1, "dark"), ("/", 1, "dark")]),
        dict(s=ROW_S[1], x=X0, keys=[("TAB", 2, "dark")] + [(c, 1, "light") for c in "QWERTYUIOP@["]
             + [("↵", 1.5, "dark", 2), (None, 0.5), ("7", 1, "light"), ("8", 1, "light"), ("9", 1, "light"),
                ("*", 1, "dark")]),
        dict(s=ROW_S[2], x=X0, keys=[("CTRL", 1, "dark"), ("CAPS", 1, "dark")] + [(c, 1, "light") for c in "ASDFGHJKL;:]"]
             + [(None, 2.0), ("4", 1, "light"), ("5", 1, "light"), ("6", 1, "light"), ("+", 1, "dark")]),
        dict(s=ROW_S[3], x=X0, keys=[("SHIFT", 2.5, "dark")] + [(c, 1, "light") for c in "ZXCVBNM,./_"]
             + [("SHIFT", 2, "dark"), (None, 0.5), ("1", 1, "light"), ("2", 1, "light"), ("3", 1, "light"),
                ("=", 1, "dark")]),
        dict(s=ROW_S[4], x=X0, keys=[(None, 2.5), ("カナ", 1, "dark"), ("GRPH", 1, "dark"), (" ", 8, "light"),
                                     (None, 3.5), ("0", 1, "light"), (",", 1, "light"), (".", 1, "light"),
                                     ("↵", 1, "dark")]),
    ])

DISPLAY = dict(at=(0.0, 40.0, 127.0), size=(365.0, 290.0, 80.0), back=(290.0, 230.0, 300.0), radius=14.0,
               colour="case", glass=(280.0, 210.0), glass_at=(0.0, 158.0), recess=22.0, bulge=8.0, frame=10.0,
               corner=12.0, back_dz=10.0,
               faces=dict(front=[("text", "NEC", "arialbi.ttf", 7.0, 26.0, 274.0, "ink"),
                                 ("text", "PC-KD851", "arialbd.ttf", 3.4, 60.0, 274.0, "ink"),
                                 ("rect", 320.0, 268.0, 344.0, 280.0, "back", 3.0),
                                 ("circle", 310.0, 274.0, 1.6, "#2A6A2A")]))

SEAT_Y = 86.0
OUT = -150.0
MEDIA = dict(kind="box", size=(133.0, 133.0, 1.6), seat=(D1_X, SEAT_Y, SLOT_Z), colour="sleeve",
             label=[("circle", 66.5, 66.5, 19.0, "#08080A"), ("circle", 66.5, 66.5, 14.0, "#5A5A5E"),
                    ("rect", 64.0, 100.0, 69.0, 118.0, "#08080A", 2.0),
                    ("rect", 14.0, 6.0, 119.0, 40.0, "label", 1.0), ("logo", 18.0, 8.0, 115.0, 38.0)],
             keys=[(0, dict(y=OUT, scale=0.0)), (8, dict(y=OUT, scale=0.0)), (16, dict(y=OUT)), (32, dict(y=0.0)),
                   (198, dict(y=0.0)), (212, dict(y=OUT)), (218, dict(y=OUT)), (228, dict(y=OUT, z=30.0, scale=0.0))])

PIVOT = (D1_X - 64.0, SLOT_Z)
MOVERS = [dict(name="latch", shape=("box", PIVOT[0] - 3.0, PIVOT[0] + 3.0, -4.0, 0.2, PIVOT[1] - 4.0, PIVOT[1] + 22.0),
               round=1.0, colour="bezel", origin=(PIVOT[0], -2.0, PIVOT[1]),
               keys=[(0, dict()), (4, dict()), (10, dict(roll=-90.0)), (34, dict(roll=-90.0)), (40, dict()),
                     (192, dict()), (198, dict(roll=-90.0)), (220, dict(roll=-90.0)), (226, dict())])]

LIGHTS = [dict(name="drive_light", at=(DRIVE_1[1] - 12.0 - W / 2, -0.1, 127.0 - 13.0), face="front", size=(3.4, 3.4),
               colour="lit", on=[(42, 92, "flicker"), (192, 198, "flicker")])]

CABLES = [dict(points=[(150.0, -40.0, 20.0), (162.0, -26.0, 6.0), (166.0, -10.0, 8.0), (158.0, -1.0, 20.0)], r=2.6,
               colour="cable")]

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(640, 200), palette=["#000000", "#0000FF", "#FF0000", "#FF00FF", "#00FF00", "#00FFFF", "#FFFF00",
                                      "#FFFFFF"],
              ink="#FFFFFF", paper="#000000", border=("#000000", 0.06), prompt="PUSH SPACE KEY",
              boot=["NEC N88-BASIC Version 2.3", "Copyright (C) 1985 by NEC", "30000 Bytes free", "Ok"],
              load=["NEC N88-BASIC Version 2.3", "Copyright (C) 1985 by NEC", "30000 Bytes free", "Ok",
                    'run"STARHLW"', "Loading..."],
              game=("Starhallow - The Sundered Crown (Europe)", "snes"))
SHOW = [(44, 72, "load"), (72, 98, "title"), (98, 196, "game")]
