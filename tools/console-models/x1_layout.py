"""The X1 card's measurements (computer.py's card `x1`; computer_layout.py says what a card holds).

Sharp's X1 (CZ-800C, 1982) in Rose Red, its keyboard and its CZ-800D display: the unit 390 x 331.5 x 108 mm and the
keyboard 391 x 188.5 x 52.5 (Sharp's figures), the display 390 wide (the set's unified width), about 320 x 400 (from
photographs); the parts placed from photographs. The unit's front: the X1 logo, the keyboard's jack, the built-in
cassette deck's door in the middle, the black transport panel and the red POWER button; slanted vents across the top's
back. The keyboard: the flat keys on the case behind the rows (F1 to F5, CHANNEL, VOLUME, COMPUTER/TV, the tape keys),
the dark main keys in their dark well, the khaki named keys, the yellow keypad digits; its coiled cord to the jack. The
display stands on the unit: its black smoked front, SHARP under the screen, the silver band along its foot.

The clip: the deck's door swings open, a cassette (a made-up game) drops into it and it shuts; the X1's IPL, Hu-BASIC
loading the game from tape, its title, and the game played on the keypad's arrows and the space bar; the door opens,
the cassette rises out and goes, and the door shuts.
"""

NAME = "X1"
YAW, PITCH = -24.0, 22.0

COLOURS = dict(case="#A33A44", well="#2B2D2B", dark="#3A3E3A", khaki="#C4C6B3", yellow="#C9B85E", fkey="#3E4448",
               silver="#D5D8E0", black="#1A1A16", red="#C83A3A", white="#F2F2EE", smoked="#1E1A19",
               body="#BDBAAE", vent="#6A2A30", shell="#2A2A2E", label="#F2F0E8", ink="#1E1E1E", window="#3A3430",
               cable="#2A2A2E")

W, D, H = 390.0, 331.5, 108.0
DOOR = dict(x=(-90.0, 78.0), z=(24.0, 86.0))


BLOCKS = [
    dict(shape=("box", -W / 2, W / 2, 0.0, D, 0.0, H), round=3.0, colour="case",
         cuts=[(DOOR["x"][0] + 0.5, DOOR["x"][1] - 0.5, -1.0, 24.0, DOOR["z"][0] + 0.5, DOOR["z"][1] - 0.5)],
         faces=dict(front=[
             ("line", [(4.0, 13.0), (386.0, 13.0)], "vent", 0.8),
             ("text", "X1", "arialbi.ttf", 16.0, 38.0, 36.0, "case"), ("text", "X1", "arialbi.ttf", 16.0, 37.4, 35.4,
                                                                         "white"),
             ("rect", 15.0, 70.0, 36.0, 91.0, "black", 2.0), ("circle", 25.5, 80.5, 3.0, "#0A0A0A"),
             ("text", "KEY BOARD", "arialbd.ttf", 2.4, 25.5, 66.0, "white"),
             ("rect", 278.0, 22.0, 342.0, 84.0, "black", 2.0),
             ("text", "EJECT", "arialbd.ttf", 2.4, 290.0, 28.0, "white"), ("text", "000", "consola.ttf", 5.0, 326.0,
                                                                             29.0, "white"),
             ("rect", 282.0, 46.0, 293.0, 54.0, "fkey", 1.0), ("rect", 296.0, 46.0, 307.0, 54.0, "fkey", 1.0),
             ("rect", 310.0, 46.0, 323.0, 54.0, "fkey", 1.0), ("rect", 326.0, 46.0, 338.0, 54.0, "fkey", 1.0),
             ("text", "REW   FF   PLAY  STOP", "arialbd.ttf", 2.0, 310.0, 59.0, "white"),
             ("text", "SHARP", "arialbd.ttf", 4.0, 310.0, 76.0, "silver"),
             ("rect", 350.0, 22.0, 370.0, 33.0, "red", 1.5), ("text", "POWER", "arialbd.ttf", 2.6, 377.0, 27.5,
                                                               "white", "lm")],
                    top=[("slots", 30.0, 12.0, 360.0, 52.0, 24, "vent")])),
    dict(shape=("profile", -195.5, 195.5, [(-230.0, 0.0), (-41.5, 0.0), (-41.5, 52.5), (-60.0, 52.5), (-222.0, 26.0),
                                           (-230.0, 20.0)]), round=3.0, colour="case",
         faces=dict(top=[("text", "SHARP", "arialbd.ttf", 5.0, 24.0, 8.0, "white")],
                    front=[("text", "X1", "arialbi.ttf", 9.0, 30.0, 12.0, "white")])),
]

U = 19.05
X0 = -190.5
S6 = 6.0
S = [S6 + 5 * U, S6 + 4 * U, S6 + 3 * U, S6 + 2 * U, S6 + U, S6]
FROW = S6 + 6 * U + 3.0

KEYBOARD = dict(
    origin=(0.0, -216.0, 27.0), slope=9.3, U=U, gap=1.2, height=8.0, taper=2.0, ink="ink", legend=3.0, ground="well",
    inks=dict(dark="white", fkey="white"),
    rows=[
        dict(s=FROW, x=X0, depth=13.0, keys=[(f"F{k}", 1.5, "fkey") for k in range(1, 6)]
             + [(None, 1.0), ("∨", 1, "silver"), ("∧", 1, "silver"), (None, 0.5), ("∨", 1, "silver"),
                ("∧", 1, "silver"), (None, 0.5), ("TV", 1.5, "silver"), (None, 1.0), ("◀◀", 1, "fkey"),
                ("■", 2, "fkey"), ("▶▶", 1, "fkey")]),
        dict(s=S[0], x=X0, keys=[("ESC", 1, "khaki")] + [(c, 1, "dark") for c in "1234567890-^¥"]
             + [("BREAK", 1.5, "khaki"), (None, 0.5), ("CLR", 1, "khaki"), ("/", 1, "khaki"), ("*", 1, "khaki"),
                ("-", 1, "khaki")]),
        dict(s=S[1], x=X0, keys=[("TAB", 1.5, "khaki")] + [(c, 1, "dark") for c in "QWERTYUIOP@["]
             + [("INS\nDEL", 1, "khaki"), ("↵", 1, "khaki"), (None, 0.5), ("7", 1, "yellow"), ("8", 1, "yellow"),
                ("9", 1, "yellow"), ("+", 1, "khaki")]),
        dict(s=S[2], x=X0, keys=[("CTRL", 1.75, "khaki")] + [(c, 1, "dark") for c in "ASDFGHJKL;:]"]
             + [("↵", 1.75, "khaki"), (None, 0.5), ("4", 1, "yellow"), ("5", 1, "yellow"), ("6", 1, "yellow"),
                ("=", 1, "khaki")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 2.25, "khaki")] + [(c, 1, "dark") for c in "ZXCVBNM,./_"]
             + [("SHIFT", 2.25, "khaki"), (None, 0.5), ("1", 1, "yellow"), ("2", 1, "yellow"), ("3", 1, "yellow"),
                (".", 1, "khaki")]),
        dict(s=S[4], x=X0, keys=[(None, 2.0), ("GRAPH", 1, "khaki"), ("CAPS", 1, "khaki"), (" ", 8.3, "dark"),
                                 ("カナ", 1, "khaki"), (None, 2.7), ("0", 1, "yellow"), (",", 1, "khaki"),
                                 ("⇧", 1, "khaki"), ("↵", 1, "khaki", 2)]),
        dict(s=S[5], x=X0 + 16.0 * U, keys=[("⇦", 1, "khaki"), ("⇨", 1, "khaki"), ("⇩", 1, "khaki")]),
    ])

DISPLAY = dict(at=(0.0, 20.0, H), size=(390.0, 320.0, 60.0), back=(320.0, 250.0, 330.0), radius=10.0,
               colour="body", glass=(290.0, 218.0), glass_at=(0.0, 165.0), recess=20.0, bulge=8.0, frame=12.0,
               corner=10.0, back_dz=6.0,
               faces=dict(front=[("rect", 6.0, 6.0, 384.0, 262.0, "smoked", 4.0),
                                 ("text", "SHARP", "arialbd.ttf", 7.0, 195.0, 251.0, "body"),
                                 ("circle", 18.0, 18.0, 2.0, "#3A3634"), ("circle", 372.0, 18.0, 2.0, "#3A3634"),
                                 ("circle", 18.0, 240.0, 2.0, "#3A3634"), ("circle", 372.0, 240.0, 2.0, "#3A3634"),
                                 ("text", "X1", "arialbi.ttf", 12.0, 36.0, 292.0, "case"),
                                 ("rect", 250.0, 284.0, 266.0, 296.0, "silver", 2.0),
                                 ("rect", 272.0, 284.0, 288.0, 296.0, "silver", 2.0),
                                 ("rect", 300.0, 284.0, 316.0, 296.0, "silver", 2.0),
                                 ("rect", 322.0, 284.0, 338.0, 296.0, "silver", 2.0),
                                 ("text", "CHANNEL      VOLUME", "arialbd.ttf", 2.6, 294.0, 278.0, "#3A3A3A"),
                                 ("rect", 352.0, 283.0, 372.0, 297.0, "red", 2.0)]))

DOOR_PIVOT = ((DOOR["x"][0] + DOOR["x"][1]) / 2, 0.0, DOOR["z"][0])
MOVERS = [dict(name="door", shape=("box", DOOR["x"][0] + 1.0, DOOR["x"][1] - 1.0, -2.5, 0.2, DOOR["z"][0] + 0.5,
                                   DOOR["z"][1] - 0.5),
               round=1.0, colour="smoked", origin=DOOR_PIVOT,
               faces=dict(front=[("rect", 2.0, 2.0, 166.0, 10.0, "case"),
                                 ("text", "CENTRAL PROCESSING UNIT", "arialbd.ttf", 2.8, 83.0, 6.0, "white"),
                                 ("rect", 42.0, 18.0, 126.0, 40.0, "window", 2.0),
                                 ("text", "▼", "seguisym.ttf", 4.0, 83.0, 52.0, "white")]),
               keys=[(0, dict()), (6, dict()), (14, dict(pitch=28.0)), (38, dict(pitch=28.0)), (46, dict()),
                     (190, dict()), (198, dict(pitch=28.0)), (214, dict(pitch=28.0)), (222, dict())])]

MEDIA = dict(kind="box", size=(100.0, 63.0, 12.0), seat=(DOOR_PIVOT[0], 8.0, DOOR["z"][0] + 33.0), turn=(90.0, 0.0, 0.0),
             colour="shell", rides="door",
             label=[("rect", 6.0, 4.0, 94.0, 40.0, "label", 1.5), ("logo", 10.0, 6.0, 90.0, 26.0),
                    ("rect", 26.0, 30.0, 74.0, 38.0, "window", 3.0), ("circle", 36.0, 34.0, 3.0, "white"),
                    ("circle", 64.0, 34.0, 3.0, "white")],
             keys=[(0, dict(z=90.0, scale=0.0)), (10, dict(z=90.0, scale=0.0)), (18, dict(z=90.0)), (32, dict()),
                   (200, dict()), (210, dict(z=90.0)), (212, dict(z=90.0)), (222, dict(z=110.0, scale=0.0))])

CABLES = [dict(points=[(-160.0, -41.5, 30.0), (-166.0, -25.0, 7.0), (-172.0, -8.0, 12.0), (-169.5, -0.5, 28.0)],
               r=2.4, colour="cable")]

PRESS = {"⇦": (122, 170), "⇨": (134, 180), "⇧": (110, 150), "⇩": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(320, 200), palette=["#000000", "#0000FF", "#FF0000", "#FF00FF", "#00FF00", "#00FFFF", "#FFFF00",
                                      "#FFFFFF"],
              ink="#FFFFFF", paper="#000000", border=("#000000", 0.06), prompt="HIT SPACE KEY",
              boot=["", "IPL is looking for a program", "", "F:Floppy R:ROM C:CMT T:Timer"],
              load=["SHARP-HuBASIC CZ-8CB01", "(C) 1982 SHARP/Hudson", "20989 Bytes free", "Ok",
                    'LOAD"COGWORK"', "Found:COGWORK", "Ok", "RUN"],
              game=("Cogwork Castle (Europe)", "snes"))
SHOW = [(50, 78, "load"), (78, 98, "title"), (98, 190, "game")]
