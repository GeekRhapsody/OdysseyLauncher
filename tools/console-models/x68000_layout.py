"""The X68000 card's measurements (computer.py's card `x68000`; computer_layout.py says what a card holds).

Sharp's X68000 (CZ-600C, 1987) in office grey, its keyboard, its mouse and a CZ-600DE display: the unit 155 x 270 x 364
mm, the keyboard 463 x 196 x 33 and the mouse 105 x 73 x 32 (Sharp's figures as listed), the display about 380 x 400 x
370 (scaled from photographs); the parts placed from photographs. The unit: two towers on a darker plinth, the round
handle rising from the gap between them, two bridges joining them; the left tower's two vertical 5.25-inch slots with
their lights, X68000 at its top; the right tower's HIGH RESO, TIMER and POWER lights and SHARP; on the plinth the jacks
and the red rocker. The display beside it on its tilt stand; the keyboard in front of the display (the function row,
the main block with its large RETURN, the editing block with the cursor keys, the keypad), the mouse at its right.

The clip: a disk (a made-up game) slides edge-on into the left tower's first slot and the drive's light flickers while
Human68k loads it; the game's title, and the game played on the cursor keys and the space bar; the disk is ejected and
goes.
"""

NAME = "X68000"
YAW, PITCH = -26.0, 18.0

COLOURS = dict(case="#A2A39E", plinth="#7E8180", handle="#757B7E", red="#D8402E", kbd="#8C9192", key="#B8BCBA",
               ink="#333333", mouse="#97A3A6", monitor="#C9CBC6", panel="#B4B6B1", dark="#2A2A2C", slot="#1A1A1C",
               lit="#FF3A2C", green="#3AE060", sleeve="#141416", label="#F2F0E8", cable="#8C9192")

TX = (152.0, 222.0, 236.0, 307.0)                          # the left tower's sides, the right tower's
SLOT_X = (173.0, 201.0)
SLOT_Z = (171.0, 303.0)

BLOCKS = [
    dict(shape=("box", TX[0], TX[3], 0.0, 270.0, 0.0, 31.0), round=3.0, colour="plinth",
         faces=dict(front=[("circle", 14.0, 15.0, 3.0, "dark"), ("text", "PHONES", "arialbd.ttf", 2.0, 14.0, 24.0,
                                                                       "#DDDDDD"),
                           ("rect", 26.0, 10.0, 46.0, 20.0, "dark", 2.0), ("text", "JOY STICK 1", "arialbd.ttf", 1.8,
                                                                             36.0, 24.0, "#DDDDDD"),
                           ("rect", 72.0, 6.0, 82.0, 25.0, "red", 1.5), ("text", "POWER", "arialbd.ttf", 1.8, 77.0,
                                                                          28.0, "#DDDDDD"),
                           ("circle", 102.0, 15.0, 4.0, "dark"), ("circle", 122.0, 15.0, 3.6, "dark"),
                           ("circle", 140.0, 15.0, 3.6, "dark")])),
    dict(shape=("box", TX[0], TX[1], 0.0, 270.0, 31.0, 364.0), round=4.0, colour="case",
         cuts=[(x - 1.6, x + 1.6, -5.0, 60.0, SLOT_Z[0], SLOT_Z[1]) for x in SLOT_X],
         faces=dict(front=[("text", "X68000", "arialbi.ttf", 7.0, 35.0, 14.0, "ink"),
                           ("text", "0", "arialbd.ttf", 2.6, SLOT_X[0] - TX[0], 47.0, "ink"),
                           ("text", "1", "arialbd.ttf", 2.6, SLOT_X[1] - TX[0], 47.0, "ink"),
                           ("circle", SLOT_X[0] - TX[0], 54.0, 1.6, "#5A1A16"),
                           ("circle", SLOT_X[1] - TX[0], 54.0, 1.6, "#5A1A16"),
                           ("line", [(4.0, 150.0), (66.0, 150.0)], "plinth", 1.2),
                           ("rect", SLOT_X[0] - TX[0] - 5.0, 202.0, SLOT_X[0] - TX[0] + 5.0, 210.0, "plinth", 1.5),
                           ("rect", SLOT_X[1] - TX[0] - 5.0, 202.0, SLOT_X[1] - TX[0] + 5.0, 210.0, "plinth", 1.5),
                           ("text", "EJECT", "arialbd.ttf", 2.0, 35.0, 216.0, "ink")],
                    top=[("slots", 8.0, 30.0, 62.0, 240.0, 14, "plinth")])),
    dict(shape=("box", TX[2], TX[3], 0.0, 270.0, 31.0, 364.0), round=4.0, colour="case",
         faces=dict(front=[("text", "HIGH RESO", "arialbd.ttf", 2.0, 14.0, 30.0, "ink"),
                           ("text", "TIMER", "arialbd.ttf", 2.0, 36.0, 30.0, "ink"),
                           ("text", "POWER", "arialbd.ttf", 2.0, 57.0, 30.0, "ink"),
                           ("circle", 14.0, 36.0, 1.5, "#1E4A2A"), ("circle", 36.0, 36.0, 1.5, "#1E4A2A"),
                           ("circle", 57.0, 36.0, 1.6, "green"),
                           ("text", "SHARP", "arialbd.ttf", 5.0, 35.5, 316.0, "ink")],
                    top=[("circle", 18.0, 250.0, 4.0, "plinth"), ("circle", 50.0, 250.0, 4.0, "plinth"),
                         ("text", "RESET   INTERRUPT", "arialbd.ttf", 1.8, 35.0, 258.0, "ink"),
                         ("slots", 8.0, 30.0, 62.0, 230.0, 14, "plinth")])),
    dict(shape=("box", TX[1] - 1.0, TX[2] + 1.0, 10.0, 260.0, 336.0, 348.0), round=2.0, colour="case"),
    dict(shape=("box", TX[1] - 1.0, TX[2] + 1.0, 10.0, 260.0, 40.0, 52.0), round=2.0, colour="case"),
    dict(shape=("box", -230.0, 110.0, 70.0, 330.0, 0.0, 22.0), round=6.0, colour="monitor"),
    dict(shape=("profile", -291.5, 171.5, [(-236.0, 0.0), (-40.0, 0.0), (-40.0, 33.0), (-56.0, 33.0), (-228.0, 20.0),
                                           (-236.0, 15.0)]), round=3.0, colour="kbd",
         faces=dict(top=[("text", "SHARP", "arialbd.ttf", 5.0, 30.0, 14.0, "ink"),
                         ("text", "X68000", "arialbi.ttf", 6.0, 420.0, 186.0, "ink")])),
    dict(shape=("box", 196.0, 268.0, -205.0, -100.0, 0.0, 30.0), round=12.0, colour="mouse",
         faces=dict(top=[("line", [(36.0, 4.0), (36.0, 34.0)], "kbd", 0.8), ("line", [(4.0, 34.0), (68.0, 34.0)],
                                                                              "kbd", 0.8)])),
]

U = 19.05
X0 = -60.0 - 219.0
S5 = 8.0
S = [S5 + 4 * U, S5 + 3 * U, S5 + 2 * U, S5 + U, S5]
FROW = S5 + 5 * U + 4.0
ED = 15.5                    # the editing block's left edge, in U
KP = 19.0                    # the keypad's

KEYBOARD = dict(
    origin=(0.0, -224.0, 21.0), slope=4.6, U=U, gap=1.2, height=8.0, taper=2.0, ink="ink", legend=2.8, ground="kbd",
    rows=[
        dict(s=FROW, x=X0, depth=14.0, keys=[("BREAK", 1, "key"), ("COPY", 1, "key"), (None, 0.5)]
             + [(f"F{k}", 1.3, "key") for k in range(1, 6)] + [(None, 0.25)]
             + [(f"F{k}", 1.3, "key") for k in range(6, 11)] + [(None, 0.25), ("かな", 1, "key"), ("ローマ字", 1, "key"),
                                                                ("コード", 1, "key"), ("CAPS", 1, "key"),
                                                                ("記号", 1, "key"), ("登録", 1, "key"),
                                                                ("HELP", 1, "key")]),
        dict(s=S[0], x=X0, keys=[("ESC", 1, "key")] + [(c, 1, "key") for c in "1234567890-^¥"]
             + [("BS", 1, "key"), (None, 0.5), ("HOME", 1, "key"), ("INS", 1, "key"), ("DEL", 1, "key"), (None, 0.5),
                ("CLR", 1, "key"), ("/", 1, "key"), ("*", 1, "key"), ("-", 1, "key")]),
        dict(s=S[1], x=X0, keys=[("TAB", 1.75, "key")] + [(c, 1, "key") for c in "QWERTYUIOP@["]
             + [("↵", 1.25, "key", 2), (None, 0.5), ("ROLL\nUP", 1, "key"), ("ROLL\nDOWN", 1, "key"),
                ("UNDO", 1, "key"), (None, 0.5), ("7", 1, "key"), ("8", 1, "key"), ("9", 1, "key"),
                ("+", 1, "key")]),
        dict(s=S[2], x=X0, keys=[("CTRL", 1.75, "key")] + [(c, 1, "key") for c in "ASDFGHJKL;:]"]
             + [(None, 1.25), (None, 0.5), ("⇦", 1, "key", 2), ("⇧", 1, "key"), ("⇨", 1, "key", 2), (None, 0.5),
                ("4", 1, "key"), ("5", 1, "key"), ("6", 1, "key"), ("=", 1, "key")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 2.25, "key")] + [(c, 1, "key") for c in "ZXCVBNM,./_"]
             + [("SHIFT", 1.75, "key"), (None, 0.5), (None, 1), ("⇩", 1, "key"), (None, 1), (None, 0.5),
                ("1", 1, "key"), ("2", 1, "key"), ("3", 1, "key"), ("ENTER", 1, "key", 2)]),
        dict(s=S[4], x=X0, keys=[(None, 2.25), ("ひらがな", 1, "key"), ("XF1", 1.25, "key"), ("XF2", 1.25, "key"),
                                 (" ", 4, "key"), ("XF3", 1.25, "key"), ("XF4", 1.25, "key"), ("XF5", 1.25, "key"),
                                 ("全角", 1, "key"), (None, 1.0), ("OPT.1", 1.5, "key"), ("OPT.2", 1.5, "key"),
                                 (None, 0.5), ("0", 1, "key"), (",", 1, "key"), (".", 1, "key")]),
    ])

DISPLAY = dict(at=(-60.0, 40.0, 22.0), size=(380.0, 345.0, 70.0), back=(300.0, 260.0, 320.0), radius=14.0,
               colour="monitor", glass=(296.0, 222.0), glass_at=(0.0, 188.0), recess=24.0, bulge=8.0, frame=14.0,
               corner=12.0, back_dz=8.0,
               faces=dict(front=[("rect", 6.0, 298.0, 374.0, 339.0, "panel", 3.0),
                                 ("text", "SHARP", "arialbd.ttf", 6.0, 40.0, 318.0, "ink"),
                                 ("text", "CZ-600DE", "arialbd.ttf", 3.0, 80.0, 318.0, "ink", "lm"),
                                 ("dots", 230.0, 310.0, 330.0, 326.0, 5, 1, 3.0, "dark"),
                                 ("rect", 344.0, 308.0, 360.0, 328.0, "red", 2.0)]))

SEAT = (SLOT_X[0], 76.0, (SLOT_Z[0] + SLOT_Z[1]) / 2)
OUT = -150.0
MEDIA = dict(kind="box", size=(133.0, 133.0, 1.6), seat=SEAT, turn=(0.0, 90.0, 0.0), colour="sleeve",
             label=[("circle", 66.5, 66.5, 19.0, "#08080A"), ("circle", 66.5, 66.5, 14.0, "#5A5A5E"),
                    ("rect", 64.0, 100.0, 69.0, 118.0, "#08080A", 2.0),
                    ("rect", 14.0, 6.0, 119.0, 40.0, "label", 1.0), ("logo", 18.0, 8.0, 115.0, 38.0)],
             keys=[(0, dict(y=OUT, scale=0.0)), (8, dict(y=OUT, scale=0.0)), (16, dict(y=OUT)), (32, dict(y=0.0)),
                   (198, dict(y=0.0)), (206, dict(y=-60.0)), (212, dict(y=-60.0)),
                   (224, dict(y=-90.0, z=40.0, scale=0.0))])

LIGHTS = [dict(name="drive_light", at=(SLOT_X[0], -0.1, 364.0 - 54.0), face="front", size=(3.0, 3.0), colour="lit",
               on=[(34, 92, "flicker"), (196, 204, "flicker")])]

CABLES = [dict(points=[(229.0, 40.0, 344.0), (229.0, 40.0, 374.0), (229.0, 230.0, 374.0), (229.0, 230.0, 344.0)], r=8.0,
               colour="handle"),
          dict(points=[(232.0, -100.0, 18.0), (226.0, -80.0, 4.0), (190.0, -66.0, 4.0), (168.0, -60.0, 20.0)], r=1.8,
               colour="cable")]

PRESS = {"⇦": (122, 170), "⇨": (134, 180), "⇧": (110, 150), "⇩": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(512, 256), palette=None, ink="#FFFFFF", paper="#101830", border=("#000000", 0.05),
              prompt="PUSH START",
              boot=["X68000 IPL-ROM", "", "Insert a disk into drive 0"],
              load=["Human68k version 3.02", "Copyright 1987-93 SHARP/Hudson", "", "A>STORMFST", "Loading..."],
              game=("Stormfist (Europe)", "megadrive"))
SHOW = [(40, 74, "load"), (74, 98, "title"), (98, 196, "game")]
