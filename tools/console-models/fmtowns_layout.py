"""The FM Towns card's measurements (computer.py's card `fmtowns`; computer_layout.py says what a card holds).

Fujitsu's FM Towns (Model 2, 1989) in Towns grey, its 14-inch display, its keyboard and its pad: the tower 150 x 400 x
328 mm (FM Towns data pages), the keyboard about 450 x 200 x 38 and the display about 345 x 380 x 300 (scaled from
photographs); the parts placed from photographs. The tower: FUJITSU at its top, the two floppy bays, the CD drive's
square door with its black ring and OPEN, the green level meter, VOLUME and POWER, the jacks at its foot; the big FM
TOWNS on its left side; the grille across its top's back. The display beside it, FUJITSU and FM TOWNS on its bezel; the
keyboard in front of it (the function row, the main block, the editing block and the cursor cross, the keypad), the
pad at its right.

The clip: OPEN, the CD's tray slides out of the door, a CD (a made-up game) drops onto it and it slides back in; the
access light flickers while it boots from the CD; the game's title, and the game played on the cursor keys and the
space bar; the tray slides out, the CD rises off it and goes, and the tray slides in.
"""

NAME = "FM Towns"
YAW, PITCH = -26.0, 18.0

COLOURS = dict(case="#4A4E54", black="#1E1F21", grey="#6E7177", white="#F2F2EE", teal="#2FA08C", ring="#141414",
               bezel="#B9BBBD", slot="#101012", green="#3AE060", lit="#6AFF8A", disc="#C8CCD2", label="#F2F0E8",
               cable="#2A2C30", shadow="#3A3E44")

TX = (200.0, 350.0)
H = 328.0
DOOR = dict(x=(TX[0] + 15.0, TX[1] - 15.0), z=(H - 210.0, H - 90.0))
TRAY_Z = (DOOR["z"][0] + DOOR["z"][1]) / 2
TCX = (TX[0] + TX[1]) / 2

BLOCKS = [
    dict(shape=("box", TX[0], TX[1], 0.0, 400.0, 0.0, H), round=4.0, colour="case",
         cuts=[(DOOR["x"][0] + 1.0, DOOR["x"][1] - 1.0, -1.0, 150.0, DOOR["z"][0] + 1.0, DOOR["z"][1] - 1.0)],
         faces=dict(front=[("text", "FUJITSU", "arialbd.ttf", 6.0, 40.0, 14.0, "white"),
                           ("rect", 10.0, 28.0, 140.0, 48.0, "bezel", 2.0), ("rect", 18.0, 36.0, 118.0, 40.0, "slot"),
                           ("rect", 124.0, 34.0, 136.0, 42.0, "shadow", 1.5),
                           ("rect", 10.0, 52.0, 140.0, 72.0, "bezel", 2.0), ("rect", 18.0, 60.0, 118.0, 64.0, "slot"),
                           ("rect", 124.0, 58.0, 136.0, 66.0, "shadow", 1.5),
                           ("circle", 128.0, 82.0, 5.0, "ring"), ("text", "OPEN", "arialbd.ttf", 2.4, 112.0, 82.0,
                                                                  "white"),
                           ("dots", 16.0, 220.0, 70.0, 226.0, 10, 1, 1.2, "#1E5A2E"),
                           ("text", "MIN        MAX", "arialbd.ttf", 2.0, 43.0, 232.0, "white"),
                           ("text", "VOLUME", "arialbd.ttf", 2.2, 90.0, 216.0, "white"),
                           ("rect", 84.0, 220.0, 96.0, 228.0, "black", 1.5),
                           ("rect", 104.0, 218.0, 140.0, 230.0, "black", 2.0),
                           ("text", "POWER", "arialbd.ttf", 2.2, 122.0, 236.0, "white"),
                           ("circle", 22.0, 296.0, 5.0, "black"), ("circle", 44.0, 296.0, 3.0, "black"),
                           ("circle", 60.0, 296.0, 3.0, "black"), ("rect", 82.0, 288.0, 138.0, 304.0, "black", 2.0),
                           ("text", "KEYBOARD  MIC  PHONES   PAD & MOUSE", "arialbd.ttf", 1.6, 75.0, 284.0, "white")],
                    left=[("text", "FM", "arialbd.ttf", 22.0, 120.0, 160.0, "teal"),
                          ("text", "TOWNS", "ariblk.ttf", 40.0, 230.0, 160.0, "teal"),
                          ("text", "FUJITSU FM SERIES PERSONAL COMPUTER", "arialbd.ttf", 6.0, 200.0, 190.0, "white"),
                          ("dots", 330.0, 20.0, 380.0, 60.0, 8, 6, 1.5, "black")],
                    top=[("rect", 65.0, 60.0, 85.0, 340.0, "shadow", 4.0), ("hslots", 10.0, 6.0, 140.0, 50.0, 12,
                                                                              "black")])),
    dict(shape=("box", -200.0, 120.0, 60.0, 320.0, 0.0, 18.0), round=5.0, colour="case"),
    dict(shape=("profile", -265.0, 185.0, [(-236.0, 0.0), (-36.0, 0.0), (-36.0, 38.0), (-54.0, 38.0), (-228.0, 22.0),
                                           (-236.0, 16.0)]), round=3.0, colour="case",
         faces=dict(top=[("text", "FUJITSU", "arialbd.ttf", 5.0, 28.0, 10.0, "white"),
                         ("text", "FM TOWNS", "arialbd.ttf", 6.0, 36.0, 192.0, "teal")])),
    dict(shape=("box", 230.0, 340.0, -190.0, -126.0, 0.0, 14.0), round=6.0, colour="grey",
         faces=dict(top=[("rect", 20.0, 22.0, 30.0, 46.0, "black", 2.0), ("rect", 13.0, 29.0, 37.0, 39.0, "black", 2.0),
                         ("circle", 86.0, 30.0, 6.0, "black"), ("circle", 100.0, 38.0, 6.0, "black"),
                         ("rect", 48.0, 40.0, 58.0, 44.0, "black", 1.5), ("rect", 62.0, 40.0, 72.0, 44.0, "black", 1.5),
                         ("text", "SELECT RUN", "arialbd.ttf", 2.0, 60.0, 50.0, "white")])),
]

U = 19.05
X0 = -40.0 - 219.0
S5 = 8.0
S = [S5 + 4 * U, S5 + 3 * U, S5 + 2 * U, S5 + U, S5]
FROW = S5 + 5 * U + 4.0

KEYBOARD = dict(
    origin=(0.0, -224.0, 23.0), slope=5.5, U=U, gap=1.2, height=8.0, taper=2.0, ink="white", legend=3.0, ground="case",
    rows=[
        dict(s=FROW, x=X0, depth=13.0, keys=[("BREAK", 1, "black"), ("COPY", 1, "black"), (None, 0.5)]
             + [(f"PF{k}", 1, "black") for k in range(1, 6)] + [(None, 0.25)]
             + [(f"PF{k}", 1, "black") for k in range(6, 11)] + [(None, 0.25), ("PF11", 1, "black"),
                                                                  ("PF12", 1, "black"), (None, 0.5),
                                                                  ("辞書", 1, "black"), ("抹消", 1, "black"),
                                                                  ("登録", 1, "black"), (None, 0.5)]
             + [(f"PF{k}", 1, "black") for k in range(13, 17)]),
        dict(s=S[0], x=X0, keys=[("ESC", 1, "black")] + [(c, 1, "grey") for c in "1234567890-^¥"]
             + [("BS", 1, "black"), (None, 0.5), ("前行", 1, "black"), ("HOME", 1, "black"), ("次行", 1, "black"),
                (None, 0.5), ("*", 1, "black"), ("/", 1, "black"), ("+", 1, "black"), ("-", 1, "black")]),
        dict(s=S[1], x=X0, keys=[("英字", 1.5, "black")] + [(c, 1, "grey") for c in "あえりゃれよにるまえぴ゛"]
             + [("↵", 1.5, "black", 2), (None, 0.5), ("半角", 1, "black"), ("削除", 1, "black"),
                ("挿入", 1, "black"), (None, 0.5), ("7", 1, "grey"), ("8", 1, "grey"), ("9", 1, "grey"),
                ("=", 1, "black")]),
        dict(s=S[2], x=X0, keys=[("カナ", 1.75, "black")] + [(c, 1, "grey") for c in "をあなゅもみおのょっ"]
             + [("後退", 1.75, "black"), (None, 1.5), (None, 0.5), (None, 1), ("↑", 1, "black"), (None, 1),
                (None, 0.5), ("4", 1, "grey"), ("5", 1, "grey"), ("6", 1, "grey"), (".", 1, "black")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 2.25, "black")] + [(c, 1, "grey") for c in "ぅーろやぃぬゆむわぉ゛"]
             + [("SHIFT", 1.75, "black"), (None, 0.5), ("←", 1, "black"), ("↓", 1, "black"), ("→", 1, "black"),
                (None, 0.5), ("1", 1, "grey"), ("2", 1, "grey"), ("3", 1, "grey"), ("↵", 1, "black", 2)]),
        dict(s=S[4], x=X0, keys=[("CTRL", 1.25, "black"), ("タブ", 1.75, "black"), ("左", 1.25, "black"),
                                 ("空白", 5, "black"), ("右", 1.25, "black"), ("かな漢字", 1.5, "black"), (None, 3.0),
                                 (None, 0.5), ("実行", 3, "black"), (None, 0.5), ("0", 2, "grey"),
                                 ("000", 1, "grey")]),
    ])

DISPLAY = dict(at=(-40.0, 70.0, 18.0), size=(345.0, 290.0, 70.0), back=(280.0, 230.0, 290.0), radius=12.0,
               colour="case", glass=(262.0, 196.0), glass_at=(0.0, 160.0), recess=22.0, bulge=8.0, frame=14.0,
               corner=12.0, back_dz=6.0,
               faces=dict(front=[("text", "FUJITSU", "arialbd.ttf", 5.0, 34.0, 16.0, "white"),
                                 ("text", "FM TOWNS", "arialbd.ttf", 6.0, 46.0, 276.0, "teal"),
                                 ("rect", 300.0, 270.0, 330.0, 282.0, "black", 2.0),
                                 ("circle", 290.0, 276.0, 1.6, "green")]))

ORIGIN = (TCX, 0.0, TRAY_Z)
MOVERS = [dict(name="tray", shape=("profile", DOOR["x"][0] + 2.0, DOOR["x"][1] - 2.0,
                                   [(-3.0, DOOR["z"][0] + 2.0), (0.0, DOOR["z"][0] + 2.0), (0.0, TRAY_Z - 3.0),
                                    (128.0, TRAY_Z - 3.0), (128.0, TRAY_Z + 1.0), (0.0, TRAY_Z + 1.0),
                                    (0.0, DOOR["z"][1] - 2.0), (-3.0, DOOR["z"][1] - 2.0)]),
               round=0.8, colour="case", origin=ORIGIN,
               faces=dict(front=[("circle", 58.0, 58.0, 50.0, "ring"), ("circle", 58.0, 58.0, 44.0, "case")]),
               keys=[(0, dict()), (6, dict()), (16, dict(y=-118.0)), (32, dict(y=-118.0)), (42, dict()), (192, dict()),
                     (202, dict(y=-118.0)), (222, dict(y=-118.0)), (232, dict())])]

MEDIA = dict(kind="disc", size=(120.0, 120.0, 1.2), seat=(TCX, 66.0, TRAY_Z + 1.8), colour="disc", rides="tray",
             label=[("circle", 60.0, 60.0, 59.0, "label"), ("cover", 18.0, 18.0, 102.0, 102.0),
                    ("circle", 60.0, 60.0, 16.0, "disc"), ("circle", 60.0, 60.0, 7.5, "#8A8E94")],
             keys=[(0, dict(z=80.0, scale=0.0)), (12, dict(z=80.0, scale=0.0)), (18, dict(z=80.0)), (30, dict()),
                   (204, dict()), (212, dict(z=80.0)), (214, dict(z=80.0)), (222, dict(z=100.0, scale=0.0))])

LIGHTS = [dict(name="access_light", at=(TX[0] + 22.0, -0.1, H - 223.0), face="front", size=(4.0, 3.0), colour="lit",
               on=[(44, 96, "flicker")])]

CABLES = [dict(points=[(250.0, -126.0, 8.0), (240.0, -80.0, 3.0), (232.0, -20.0, 3.0), (300.0, -1.0, 30.0)], r=1.8,
               colour="cable")]

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), "空白": (100, 128, 160, 188)}

SCREEN = dict(px=(320, 240), palette=None, ink="#FFFFFF", paper="#000010", border=("#000000", 0.05),
              prompt="PUSH RUN BUTTON", title_ink="#FFFFFF",
              boot=["", "", "   FM TOWNS", "", "   Insert a CD-ROM", "   or a floppy disk"],
              load=["", "", "   FM TOWNS", "", "   Booting from CD-ROM", "", "   ORBITAL STRIKER"],
              game=("Orbital Striker (Europe)", "n64"))
SHOW = [(46, 78, "load"), (78, 100, "title"), (100, 190, "game")]
