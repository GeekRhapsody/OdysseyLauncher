"""The Spectravideo card's measurements (computer.py's card `spectravideo`; computer_layout.py says what a card holds).

Spectravideo's SV-318 (1983) and a 14-inch television (unbranded) behind it: the SV-318 405 x 215 x 77 mm (the SV-328's
figures, its case the same); the parts placed from photographs of it from above and the right. The off-white case: the
deck with the charcoal chiclet keys in their frame (the spaced function row, the main block, SELECT apart), the built-in
joystick at its right (the charcoal disc with its four arrow pads, the red ball on its stem), the raised back section
with the badge at its left, the cartridge slot and its vents at its right.

The clip: a cartridge (a made-up game) drops into the slot; the SV-318's BASIC banner, the game's title, and the game
played on the joystick and the space bar; the cartridge rises out and goes.
"""

NAME = "Spectravideo"
YAW, PITCH = -24.0, 26.0

COLOURS = dict(case="#EEECE6", key="#26282C", white="#F2F2EE", black="#141416", red="#C8302E", base="#3D3E43",
               silver="#C8C8CC", orange="#F08A2A", yellow="#F2D23A", tv="#2A2A2C", panel="#3A3A3E", cart="#2A2A2E",
               label="#F2F0E8", vent="#C8C6BC", well="#E2E0D8")

W = 405.0
JOY = (142.5, 62.0, 38.5)

BLOCKS = [
    dict(shape=("profile", -W / 2, W / 2, [(0.0, 0.0), (215.0, 0.0), (215.0, 74.0), (212.0, 77.0), (150.0, 77.0),
                                          (145.0, 72.0), (145.0, 52.0), (10.0, 32.0), (0.0, 28.0)]), round=3.0,
         colour="case", cuts=[(100.0, 185.0, 152.0, 207.0, 40.0, 90.0)],
         faces=dict(top=[("rect", 20.0, 26.0, 112.0, 43.0, "black", 1.0),
                         ("line", [(26.0, 30.0), (60.0, 30.0)], "red", 1.0),
                         ("line", [(26.0, 33.0), (60.0, 33.0)], "orange", 1.0),
                         ("line", [(26.0, 36.0), (60.0, 36.0)], "yellow", 1.0),
                         ("text", "SPECTRAVIDEO", "arialbi.ttf", 4.0, 66.0, 33.0, "white", "lm"),
                         ("rect", 140.0, 26.0, 186.0, 43.0, "silver", 1.0),
                         ("text", "SV·318", "arialbd.ttf", 5.0, 163.0, 32.0, "black"),
                         ("text", "PERSONAL COMPUTER", "arial.ttf", 2.0, 163.0, 39.0, "black"),
                         ("slots", 302.0, 2.0, 388.0, 8.0, 9, "vent"),
                         ("circle", 300.0, 88.0, 2.0, "red"), ("text", "POWER ON", "arialbd.ttf", 2.2, 314.0, 88.0,
                                                                "black", "lm")],
                    right=[("rect", 60.0, 30.0, 82.0, 42.0, "black", 2.0), ("rect", 90.0, 30.0, 112.0, 42.0, "black", 2.0),
                           ("text", "JOYSTICK 1     2", "arialbd.ttf", 2.2, 86.0, 26.0, "black"),
                           ("rect", 130.0, 30.0, 146.0, 40.0, "black", 1.5), ("text", "ON/OFF", "arialbd.ttf", 2.2,
                                                                               138.0, 26.0, "black")])),
    dict(shape=("lathe", *JOY, [(0.0, -4.0), (31.0, -4.0), (31.0, 4.0), (29.0, 6.0), (0.0, 6.0)]), colour="base",
         faces=dict(top=[("text", "▲", "seguisym.ttf", 6.0, 31.0, 10.0, "#5A5B60"),
                         ("text", "▼", "seguisym.ttf", 6.0, 31.0, 52.0, "#5A5B60"),
                         ("text", "◀", "seguisym.ttf", 6.0, 10.0, 31.0, "#5A5B60"),
                         ("text", "▶", "seguisym.ttf", 6.0, 52.0, 31.0, "#5A5B60")])),
    dict(shape=("box", -150.0, 150.0, 250.0, 520.0, 0.0, 30.0), round=6.0, colour="tv"),
]

U = 20.0
X0 = -185.0
S = [4.0 + 4 * U, 4.0 + 3 * U, 4.0 + 2 * U, 4.0 + U, 4.0]
FROW = 4.0 + 5 * U + 3.0

KEYBOARD = dict(
    origin=(0.0, 14.0, 32.5), slope=8.4, U=U, gap=5.0, height=6.0, taper=1.2, ink="white", legend=3.0, ground="well",
    rows=[
        dict(s=FROW, x=X0, depth=14.0, keys=[(f"F{k}", 1.25, "key") if j == 0 else (None, 0.25)
                                             for k in range(1, 6) for j in (0, 1)]
             + [(None, 0.5), ("STOP", 1, "key"), ("CLS", 1, "key"), ("INS", 1, "key"), ("DEL", 1, "key")]),
        dict(s=S[0], x=X0, depth=16.0, keys=[("ESC", 1, "key")] + [(c, 1, "key") for c in "1234567890-="]
             + [("⇐", 1.5, "key"), (None, 1.5), ("SELECT", 1, "key")]),
        dict(s=S[1], x=X0, depth=16.0, keys=[("⇒", 1.5, "key")] + [(c, 1, "key") for c in "QWERTYUIOP[]\\"]),
        dict(s=S[2], x=X0, depth=16.0, keys=[("CAPS", 1, "key"), (None, 0.25), ("CTRL", 1, "key")]
             + [(c, 1, "key") for c in "ASDFGHJKL;'"] + [("ENTER", 1.75, "key")]),
        dict(s=S[3], x=X0, depth=16.0, keys=[("SHIFT", 1.5, "key")] + [(c, 1, "key") for c in "ZXCVBNM,./"]
             + [("SHIFT", 1.5, "key")]),
        dict(s=S[4], x=X0, depth=16.0, keys=[(None, 2.0), ("GRPH", 1.25, "key"), ("GRPH", 1.25, "key"),
                                             (" ", 6.5, "key")]),
    ])

DISPLAY = dict(at=(0.0, 260.0, 30.0), size=(390.0, 310.0, 50.0), back=(320.0, 250.0, 250.0), radius=14.0, colour="tv",
               glass=(268.0, 200.0), glass_at=(-45.0, 162.0), recess=18.0, bulge=10.0, frame=13.0, corner=18.0,
               back_dz=0.0,
               faces=dict(front=[("rect", 325.0, 24.0, 382.0, 286.0, "panel", 4.0),
                                 ("hslots", 333.0, 32.0, 374.0, 130.0, 10, "black"),
                                 ("dots", 336.0, 160.0, 371.0, 242.0, 2, 4, 5.0, "black"),
                                 ("circle", 333.0, 263.0, 1.4, "#FF3A2C")]))

WAGGLE = [(100 + 6 * k, dict(pitch=(14.0, 0.0, -14.0, 0.0)[k % 4], roll=(0.0, 14.0, 0.0, -14.0)[(k + 1) % 4]))
          for k in range(15)]
MOVERS = [dict(name="stick", shape=("lathe", JOY[0], JOY[1], JOY[2] + 6.0,
                                     [(0.0, -2.0), (4.0, -2.0), (4.0, 26.0), (10.0, 28.0), (14.0, 33.0), (15.0, 38.0),
                                      (14.0, 43.0), (10.0, 47.0), (0.0, 49.0)]),
               colour="red", origin=(JOY[0], JOY[1], JOY[2] + 6.0),
               keys=[(0, dict()), (96, dict())] + WAGGLE + [(196, dict())])]

SEAT = (142.5, 180.0, 75.0)
MEDIA = dict(kind="box", size=(80.0, 70.0, 18.0), seat=SEAT, turn=(90.0, 0.0, 0.0), colour="cart",
             label=[("rect", 5.0, 4.0, 75.0, 52.0, "label", 1.5), ("cover", 7.0, 6.0, 73.0, 50.0),
                    ("text", "SPECTRAVIDEO", "arialbd.ttf", 3.6, 40.0, 60.0, "white")],
             keys=[(0, dict(z=60.0, scale=0.0)), (6, dict(z=60.0, scale=0.0)), (14, dict(z=60.0)),
                   (20, dict(z=64.0, spin=180.0)), (28, dict(z=60.0, spin=360.0)), (40, dict(spin=360.0)),
                   (198, dict(spin=360.0)), (210, dict(z=60.0, spin=360.0)), (222, dict(z=80.0, spin=360.0, scale=0.0))])

PRESS = {" ": (104, 128, 150, 176, 188), "SELECT": (90,)}

SCREEN = dict(px=(256, 192), palette=["#000000", "#21C842", "#5EDC78", "#5455ED", "#7D76FC", "#D4524D", "#42EBF5",
                                      "#FC5554", "#FF7978", "#D4C154", "#E6CE80", "#21B03B", "#C95BBA", "#CCCCCC",
                                      "#FFFFFF"],
              ink="#FFFFFF", paper="#5455ED", border=("#5455ED", 0.1), prompt="PRESS SPACE",
              boot=["SV extended BASIC version 1.1", "Copyright 1983 (C)", "by Microsoft corp.", "12815 Bytes free", "Ok"],
              load=["", "", "", "    SPECTRAVIDEO", "", "    RING ROYALE", "", "    Cartridge"],
              game=("Ring Royale (Europe)", "n64"))
SHOW = [(42, 72, "load"), (72, 96, "title"), (96, 196, "game")]
