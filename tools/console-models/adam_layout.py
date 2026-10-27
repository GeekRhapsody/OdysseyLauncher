"""The Coleco ADAM card's measurements (computer.py's card `adam`; computer_layout.py says what a card holds).

Coleco's ADAM (1983, the stand-alone one), its keyboard with a controller in its holder, its SmartWriter printer and a
14-inch television (unbranded): the memory console about 476 x 364 x 105 mm, the keyboard 387 x 165 x 57 and the printer
375 x 343 x 178 (the Computer History Museum's figures); the parts placed from photographs. The beige console: the badge
strip with ADAM and its rainbow line over the tape section, data drive 1 behind its door and the bay for drive 2, the
cartridge slot on top of its right section, vents along its back. The keyboard: the top row (ESCAPE/WP, WILD CARD, the
six slate SmartKeys, UNDO, BACK SPACE, MOVE/COPY, STORE/GET, CLEAR), the cream main keys and the grey named keys, the
cursor cross with HOME; the controller in its holder at its right end. The printer beside the console: its body, its
cover with the badge strip, the platen and a sheet of paper.

The clip: a Digital Data Pack (a made-up game) slides into drive 1, pushing its door in; the console reads it while the
SmartWriter screen gives way to the game's title, and the game is played on the cursor keys and the space bar; the pack
comes out and goes, the door swinging shut.
"""

NAME = "ADAM"
YAW, PITCH = -24.0, 22.0

COLOURS = dict(case="#D8CFC0", light="#ECE5C7", grey="#A69C90", slate="#4A4752", badge="#3A2E2A", white="#F2F2EE",
               smoked="#2A2A2E", ink="#1E1E1E", red="#D83A2E", orange="#F08A2A", yellow="#F2D23A", green="#3AA84A",
               blue="#3A6AD8", tv="#2A2A2C", panel="#3A3A3E", paper="#F8F6F0", platen="#1E1E20", pack="#2C2C30",
               label="#F2F0E8", key="#C8C8C4", black="#141416", cable="#9A9488")

CW, CD, CH = 476.0, 364.0, 105.0
DRIVE = dict(x=(-190.0, -80.0), z=(48.0, 66.0))
DX = (DRIVE["x"][0] + DRIVE["x"][1]) / 2


def rainbow(a0, a1, b):
    colours = ("red", "orange", "yellow", "green", "blue")
    step = (a1 - a0) / len(colours)
    return [("rect", a0 + step * k, b, a0 + step * (k + 1), b + 1.4, c) for k, c in enumerate(colours)]


BLOCKS = [
    dict(shape=("box", -CW / 2, CW / 2, 0.0, CD, 0.0, CH), round=5.0, colour="case",
         cuts=[(DRIVE["x"][0] + 1.0, DRIVE["x"][1] - 1.0, -2.0, 80.0, DRIVE["z"][0] + 1.0, DRIVE["z"][1] - 1.0)],
         faces=dict(front=[("rect", 40.0, 35.0, 162.0, 63.0, "smoked", 3.0),
                           ("rect", 176.0, 35.0, 298.0, 63.0, "smoked", 3.0),
                           ("rect", 180.0, 39.0, 294.0, 59.0, "case", 2.0),
                           ("text", "DIGITAL DATA DRIVE", "arialbd.ttf", 2.6, 101.0, 30.0, "ink"),
                           ("circle", 450.0, 80.0, 2.0, "smoked")],
                    top=[("slots", 20.0, 8.0, 456.0, 50.0, 40, "grey"),
                         ("rect", 20.0, 330.0, 300.0, 356.0, "badge", 2.0)]
                    + rainbow(30.0, 200.0, 348.0)
                    + [("text", "ADAM", "ariblk.ttf", 9.0, 252.0, 342.0, "white"),
                       ("text", "The ColecoVision Family Computer System", "arialbd.ttf", 2.6, 110.0, 340.0, "white"),
                       ("rect", 340.0, 150.0, 430.0, 172.0, "black", 2.0), ("circle", 330.0, 161.0, 4.0, "grey"),
                       ("circle", 440.0, 161.0, 4.0, "grey")])),
    dict(shape=("box", -640.0, -265.0, 0.0, 343.0, 0.0, 110.0), round=6.0, colour="case"),
    dict(shape=("profile", -635.0, -270.0, [(10.0, 105.0), (300.0, 105.0), (300.0, 150.0), (40.0, 128.0),
                                            (10.0, 120.0)]), round=4.0, colour="case",
         faces=dict(top=[("rect", 20.0, 250.0, 200.0, 270.0, "badge", 2.0)] + rainbow(26.0, 140.0, 264.0)
                    + [("text", "ADAM", "ariblk.ttf", 7.0, 170.0, 260.0, "white")])),
    dict(shape=("box", -610.0, -295.0, 300.0, 302.0, 150.0, 255.0), colour="paper",
         faces=dict(front=[("hslots", 24.0, 14.0, 290.0, 80.0, 9, "#8A8A8A")])),
    dict(shape=("box", -CW / 2 + 20.0, CW / 2 - 20.0, 380.0, 640.0, 0.0, 30.0), round=6.0, colour="tv"),
    dict(shape=("profile", -193.5, 193.5, [(-260.0, 0.0), (-95.0, 0.0), (-95.0, 57.0), (-110.0, 57.0),
                                           (-252.0, 25.0), (-260.0, 20.0)]), round=3.0, colour="case"),
    dict(shape=("box", 193.5, 278.0, -260.0, -95.0, 0.0, 34.0), round=4.0, colour="case"),
    dict(shape=("box", 206.0, 266.0, -250.0, -105.0, 30.0, 52.0), round=6.0, colour="case",
         faces=dict(top=[("dots", 10.0, 70.0, 50.0, 130.0, 3, 4, 4.0, "key"), ("rect", 6.0, 135.0, 54.0, 141.0,
                                                                             "grey", 2.0)])),
    dict(shape=("lathe", 236.0, -130.0, 52.0, [(0.0, 0.0), (14.0, 0.0), (13.0, 6.0), (6.0, 9.0), (0.0, 10.0)]),
         colour="case"),
]

U = 19.05
X0 = -176.0
S = [5.0 + 4 * U, 5.0 + 3 * U, 5.0 + 2 * U, 5.0 + U, 5.0]
TOP = 5.0 + 5 * U + 3.0

KEYBOARD = dict(
    origin=(0.0, -250.0, 25.5), slope=12.7, U=U, gap=1.2, height=9.0, taper=2.2, ink="ink", legend=2.8, ground="case",
    inks=dict(slate="white"),
    rows=[
        dict(s=TOP, x=X0, depth=15.0, keys=[("ESC\nWP", 1, "grey"), ("WILD\nCARD", 1, "grey")]
             + [(r, 1.5, "slate") for r in ("I", "II", "III", "IV", "V", "VI")]
             + [("UNDO", 1, "grey"), ("BACK\nSPACE", 1, "grey"), (None, 2.5), ("MOVE\nCOPY", 1, "grey"),
                ("STORE\nGET", 1, "grey"), ("CLEAR", 1, "grey")]),
        dict(s=S[0], x=X0, keys=[(c, 1, "light") for c in "\\1234567890-=^"]
             + [(None, 1.5), ("INS", 1, "grey"), ("PRINT", 1, "grey"), ("DEL", 1, "grey")]),
        dict(s=S[1], x=X0, keys=[("TAB", 1.5, "grey")] + [(c, 1, "light") for c in "QWERTYUIOP[]"]
             + [("↵", 1.5, "grey", 2), (None, 0.5), (None, 1), ("↑", 1, "grey")]),
        dict(s=S[2], x=X0, keys=[("CTRL", 1.75, "grey")] + [(c, 1, "light") for c in "ASDFGHJKL;'"]
             + [(None, 0.75), (None, 1.5), (None, 0.5), ("←", 1, "grey"), ("HOME", 1, "grey"), ("→", 1, "grey")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 2.25, "grey")] + [(c, 1, "light") for c in "ZXCVBNM,./"]
             + [("SHIFT", 2.25, "grey"), (None, 1.0), (None, 1), ("↓", 1, "grey")]),
        dict(s=S[4], x=X0, keys=[("LOCK", 1, "grey"), (None, 2.0), (" ", 8.5, "light")]),
    ])

DISPLAY = dict(at=(0.0, 390.0, 30.0), size=(390.0, 310.0, 50.0), back=(320.0, 250.0, 220.0), radius=14.0, colour="tv",
               glass=(268.0, 200.0), glass_at=(-45.0, 162.0), recess=18.0, bulge=10.0, frame=13.0, corner=18.0,
               back_dz=0.0,
               faces=dict(front=[("rect", 325.0, 24.0, 382.0, 286.0, "panel", 4.0),
                                 ("hslots", 333.0, 32.0, 374.0, 130.0, 10, "black"),
                                 ("dots", 336.0, 160.0, 371.0, 242.0, 2, 4, 5.0, "black"),
                                 ("circle", 333.0, 263.0, 1.4, "#FF3A2C")]))

MOVERS = [dict(name="door", shape=("box", DRIVE["x"][0] + 2.0, DRIVE["x"][1] - 2.0, -2.5, 0.0, DRIVE["z"][0] + 1.5,
                                   DRIVE["z"][1] - 0.5),
               round=0.6, colour="smoked", origin=(DX, -1.2, DRIVE["z"][1] - 1.0),
               keys=[(0, dict()), (20, dict()), (26, dict(pitch=80.0)), (32, dict(pitch=80.0)), (38, dict()),
                     (196, dict()), (200, dict(pitch=80.0)), (210, dict(pitch=80.0)), (216, dict())])]

OUT = -100.0
MEDIA = dict(kind="box", size=(96.0, 64.0, 12.0), seat=(DX, 40.0, (DRIVE["z"][0] + DRIVE["z"][1]) / 2), colour="pack",
             label=[("rect", 6.0, 4.0, 90.0, 44.0, "label", 1.5), ("cover", 8.0, 6.0, 88.0, 42.0),
                    ("text", "DIGITAL DATA PACK", "arialbd.ttf", 3.4, 48.0, 54.0, "white")],
             keys=[(0, dict(y=OUT, scale=0.0)), (8, dict(y=OUT, scale=0.0)), (16, dict(y=OUT)), (36, dict(y=0.0)),
                   (196, dict(y=0.0)), (210, dict(y=OUT)), (214, dict(y=OUT)), (226, dict(y=OUT, z=30.0, scale=0.0))])

CABLES = [dict(points=[(40.0, -95.0, 30.0), (46.0, -70.0, 5.0), (60.0, -30.0, 5.0), (70.0, -1.0, 20.0)], r=2.4,
               colour="cable"),
          dict(points=[(-625.0, 300.0, 150.0), (-280.0, 300.0, 150.0)], r=22.0, colour="platen")]

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(256, 192), palette=["#000000", "#21C842", "#5EDC78", "#5455ED", "#7D76FC", "#D4524D", "#42EBF5",
                                      "#FC5554", "#FF7978", "#D4C154", "#E6CE80", "#21B03B", "#C95BBA", "#CCCCCC",
                                      "#FFFFFF"],
              ink="#0A2A6A", paper="#42C8C8", border=("#42C8C8", 0.1), prompt="PRESS SPACE",
              boot=["", " SMARTWRITER", "", " ELECTRONIC TYPEWRITER", "", " Press ESCAPE/WP", " for word processing"],
              load=["", " SMARTWRITER", "", " Reading drive 1...", "", " APEX CIRCUIT 64"],
              game=("Apex Circuit 64 (Europe)", "n64"))
SHOW = [(40, 74, "load"), (74, 98, "title"), (98, 196, "game")]
