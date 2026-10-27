"""The SAM Coupé card's measurements (computer.py's card `samcoupe`; computer_layout.py says what a card holds).

Miles Gordon Technology's SAM Coupé (1989) with a SAM Drive in its right bay, and a 14-inch television (unbranded)
behind it: the SAM 438 x 260 x 81 mm (World of SAM's specification); the parts placed from photographs of it from
above, the front and the side. The off-white fastback: the base slab with the drive bays across its front lip (the SAM
Drive at the right, a blank cover at the left), the flat deck with the SAM coupé logo, the keyboard's housing rising
behind it to the back, the keys in its well (the main block, the grey named keys, the function keys and the cursor keys
at the right), MGT at its back right; the blue rubber feet.

The clip: a 3.5-inch disk (a made-up game) slides into the SAM Drive and its light flickers; SAM BASIC boots it, its
title, and the game is played on the cursor keys and the space bar; the disk is ejected and goes.
"""

NAME = "SAM Coupé"
YAW, PITCH = -24.0, 24.0

COLOURS = dict(case="#E2E3DE", key="#DADBD3", grey="#9A9C90", ink="#1E1E1E", blue="#1C57BB", red="#D0303A",
               feet="#2A48A8", drive="#2E6BC8", white="#F4F4F2", black="#141416", lit="#3AE060", tv="#2A2A2C",
               panel="#3A3A3E", shell="#2A2A2E", label="#F2F0E8", shutter="#B4B8BC", well="#C8C9C2")

W = 438.0
RIGHT_BAY = (274.0, 424.0)
SLOT_X = (RIGHT_BAY[0] + RIGHT_BAY[1]) / 2 - W / 2
SLOT_Z = 18.0

BLOCKS = [
    dict(shape=("profile", -W / 2, W / 2, [(0.0, 0.0), (260.0, 0.0), (260.0, 75.0), (254.0, 81.0), (140.0, 76.0),
                                          (118.0, 44.0), (6.0, 40.0), (0.0, 35.0)]), round=3.0, colour="case",
         cuts=[(-178.0, 178.0, 146.0, 250.0, 71.0, 92.0), (SLOT_X - 40.0, SLOT_X + 40.0, -5.0, 60.0, SLOT_Z - 2.0,
                                                           SLOT_Z + 2.0)],
         faces=dict(front=[("rect", 14.0, 48.0, 164.0, 78.0, "well", 2.0),
                           ("rect", RIGHT_BAY[0], 48.0, RIGHT_BAY[1], 78.0, "white", 2.0),
                           ("rect", RIGHT_BAY[0] + 12.0, 61.0, RIGHT_BAY[1] - 30.0, 66.0, "drive", 1.5),
                           ("rect", RIGHT_BAY[1] - 24.0, 58.0, RIGHT_BAY[1] - 10.0, 68.0, "drive", 2.0),
                           ("text", "SAM", "ariblk.ttf", 4.0, 219.0, 63.0, "blue")],
                    top=[("text", "MGT", "ariblk.ttf", 7.0, 400.0, 6.0, "blue"),
                         ("circle", 383.0, 4.0, 1.0, "red"), ("circle", 417.0, 4.0, 1.0, "red"),
                         ("text", "MILES GORDON TECHNOLOGY plc", "arialbd.ttf", 2.0, 400.0, 12.0, "blue"),
                         ("text", "SAM", "ariblk.ttf", 16.0, 50.0, 200.0, "blue"),
                         ("line", [(22.0, 212.0), (60.0, 216.0), (96.0, 206.0)], "blue", 1.5),
                         ("text", "coupé", "arialbi.ttf", 12.0, 104.0, 206.0, "red")])),
    dict(shape=("box", -150.0, 150.0, 290.0, 560.0, 0.0, 30.0), round=6.0, colour="tv"),
]
for x in (-W / 2 + 18.0, W / 2 - 18.0):
    for y in (24.0, 236.0):
        BLOCKS.append(dict(shape=("box", x - 15.0, x + 15.0, y - 15.0, y + 15.0, -0.5, 12.0), corner=14.0, round=4.0,
                           colour="feet"))

U = 19.05
X0 = -174.0
S = [4.0 + 4 * U, 4.0 + 3 * U, 4.0 + 2 * U, 4.0 + U, 4.0]
RB = 15.25

KEYBOARD = dict(
    origin=(0.0, 146.0, 72.0), slope=2.5, U=U, gap=1.2, height=12.0, taper=2.2, ink="ink", legend=3.0, ground="well",
    rows=[
        dict(s=S[0], x=X0, keys=[("ESC", 1, "grey")] + [(c, 1, "key") for c in "1234567890-+"]
             + [("DELETE", 1.75, "grey"), (None, 0.5), ("F7", 1, "key"), ("F8", 1, "key"), ("F9", 1, "key")]),
        dict(s=S[1], x=X0, keys=[("TAB", 1.5, "grey")] + [(c, 1, "key") for c in "QWERTYUIOP=\""]
             + [("↵", 1.25, "grey"), (None, 0.5), ("F4", 1, "key"), ("F5", 1, "key"), ("F6", 1, "key")]),
        dict(s=S[2], x=X0, keys=[("CAPS", 1.75, "grey")] + [(c, 1, "key") for c in "ASDFGHJKL;:"]
             + [("RETURN", 2.0, "grey"), (None, 0.5), ("F1", 1, "key"), ("F2", 1, "key"), ("F3", 1, "key")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 2.25, "grey")] + [(c, 1, "key") for c in "ZXCVBNM,.\\"]
             + [("SHIFT", 2.25, "grey"), (None, 0.25), (None, 0.5), ("F0", 1, "key"), ("↑", 1, "key"),
                (".", 1, "key")]),
        dict(s=S[4], x=X0, keys=[("SYMBOL", 1.75, "grey"), ("CNTRL", 1.5, "grey"), (" ", 8, "key"),
                                 ("EDIT", 1.5, "grey"), ("SYMBOL", 1.75, "grey"), (None, 0.25), (None, 0.5),
                                 ("←", 1, "key"), ("↓", 1, "key"), ("→", 1, "key")]),
    ])

DISPLAY = dict(at=(0.0, 300.0, 30.0), size=(390.0, 310.0, 50.0), back=(320.0, 250.0, 250.0), radius=14.0, colour="tv",
               glass=(268.0, 200.0), glass_at=(-45.0, 162.0), recess=18.0, bulge=10.0, frame=13.0, corner=18.0,
               back_dz=0.0,
               faces=dict(front=[("rect", 325.0, 24.0, 382.0, 286.0, "panel", 4.0),
                                 ("hslots", 333.0, 32.0, 374.0, 130.0, 10, "black"),
                                 ("dots", 336.0, 160.0, 371.0, 242.0, 2, 4, 5.0, "black"),
                                 ("circle", 333.0, 263.0, 1.4, "#FF3A2C")]))

SEAT = (SLOT_X, 52.0, SLOT_Z)
OUT = -150.0
MEDIA = dict(kind="box", size=(90.0, 94.0, 3.3), seat=SEAT, colour="shell",
             label=[("rect", 18.0, 0.0, 72.0, 30.0, "shutter"), ("rect", 49.0, 4.0, 59.0, 26.0, "#3A3A3E"),
                    ("rect", 6.0, 36.0, 84.0, 90.0, "label", 1.0), ("cover", 8.0, 38.0, 82.0, 88.0)],
             keys=[(0, dict(y=OUT, scale=0.0)), (8, dict(y=OUT, scale=0.0)), (16, dict(y=OUT)), (32, dict(y=0.0)),
                   (198, dict(y=0.0)), (204, dict(y=-34.0)), (212, dict(y=-34.0)),
                   (224, dict(y=-90.0, z=30.0, scale=0.0))])

LIGHTS = [dict(name="drive_light", at=(SLOT_X - 62.0, -0.1, 23.0), face="front", size=(3.0, 2.4), colour="lit",
               on=[(34, 92, "flicker"), (196, 202, "flicker")])]

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(256, 192), palette=None, ink="#000000", paper="#FFFFFF", border=("#FFFFFF", 0.1),
              prompt="PRESS SPACE",
              boot=["", "", "", "", " SAM BASIC", " (C) 1990 MGT"],
              load=["", "", "", "", " SAM BASIC", " (C) 1990 MGT", "", " BOOT", " Loading POWDER PEAK"],
              game=("Powder Peak (Europe)", "n64"))
SHOW = [(40, 72, "load"), (72, 96, "title"), (96, 196, "game")]
