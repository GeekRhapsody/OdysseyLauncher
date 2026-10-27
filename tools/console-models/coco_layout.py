"""The TRS-80 Color Computer card's measurements (computer.py's card `coco`; computer_layout.py says what a card holds).

Tandy's TRS-80 Color Computer (the first, grey one, 1980) and a 14-inch television (unbranded) behind it: the CoCo 362 x
349 x 89 mm (Tandy's figures); the parts placed from photographs of it from above, the right and behind. The silver-grey
case: the raised flat back section with vents down both its sides, stepping down to the sloping front with the black
keyboard well, the chiclet keys staggered in it (grey, the arrows, SHIFT, ENTER and CLEAR cream, BREAK red), the badge
strip behind them, the RAM plate at the right; the Program Pak slot low in its right side, towards the back.

The clip: a Program Pak (a made-up game) slides into the slot in the right side; the green screen of Extended Color
BASIC gives way to the game's title, and it is played on the arrows and the space bar; the Pak slides out and goes.
"""

NAME = "Color Computer"
YAW, PITCH = -26.0, 26.0

COLOURS = dict(case="#9A9A98", well="#0D0B10", key="#A39C94", cream="#E8E0C8", red="#D0302E", white="#F2F2EE",
               ink="#1A1A1A", black="#141416", rgb_r="#D83A2E", rgb_g="#3AA84A", rgb_b="#3A6AD8", metal="#C8C8C4",
               tv="#2A2A2C", panel="#3A3A3E", pak="#3A3A3E", label="#F2F0E8", vent="#6A6A68")

W = 362.0
SLOT = dict(y=(210.0, 320.0), z=(8.0, 33.0))

BLOCKS = [
    dict(shape=("profile", -W / 2, W / 2, [(0.0, 0.0), (349.0, 0.0), (349.0, 86.0), (346.0, 89.0), (196.0, 89.0),
                                          (186.0, 62.0), (8.0, 30.0), (0.0, 25.0)]), round=3.0, colour="case",
         cuts=[(W / 2 - 16.0, W / 2 + 5.0, SLOT["y"][0], SLOT["y"][1], SLOT["z"][0], SLOT["z"][1])],
         faces=dict(top=[("hslots", 8.0, 14.0, 34.0, 146.0, 14, "vent"), ("hslots", 328.0, 14.0, 354.0, 146.0, 14,
                                                                           "vent"),
                         ("rect", 36.0, 184.0, 326.0, 326.0, "well", 6.0),
                         ("rect", 121.0, 160.0, 241.0, 178.0, "black", 1.0),
                         ("text", "Radio Shack", "arialbi.ttf", 3.6, 141.0, 169.0, "white"),
                         ("text", "TRS-80", "arialbd.ttf", 3.4, 181.0, 166.0, "white"),
                         ("rect", 170.0, 171.0, 176.0, 175.0, "rgb_r"), ("rect", 178.0, 171.0, 184.0, 175.0, "rgb_g"),
                         ("rect", 186.0, 171.0, 192.0, 175.0, "rgb_b"),
                         ("text", "COLOR COMPUTER", "arialbd.ttf", 3.0, 218.0, 169.0, "white"),
                         ("rect", 300.0, 162.0, 326.0, 176.0, "metal", 1.0),
                         ("text", "16K RAM", "arialbd.ttf", 2.6, 313.0, 169.0, "ink")],
                    right=[("rect", SLOT["y"][0] - 4.0, 89.0 - SLOT["z"][1] - 4.0, SLOT["y"][1] + 4.0,
                            89.0 - SLOT["z"][0] + 4.0, "black", 3.0)])),
    dict(shape=("box", -150.0, 150.0, 370.0, 640.0, 0.0, 30.0), round=6.0, colour="tv"),
]

U = 19.05
X0 = -140.0
S = [6.0 + 4 * U, 6.0 + 3 * U, 6.0 + 2 * U, 6.0 + U, 6.0]

KEYBOARD = dict(
    origin=(0.0, 30.0, 34.0), slope=10.2, U=U, gap=5.0, height=6.0, taper=1.0, ink="ink", legend=3.0, ground="well",
    inks=dict(red="white"),
    rows=[
        dict(s=S[0], x=X0 + 0.5 * U, keys=[(c, 1, "key") for c in "1234567890:-"] + [("BREAK", 1, "red")]),
        dict(s=S[1], x=X0, keys=[("↑", 1, "cream")] + [(c, 1, "key") for c in "QWERTYUIOP@"]
             + [("←", 1, "cream"), ("→", 1, "cream")]),
        dict(s=S[2], x=X0 + 0.25 * U, keys=[("↓", 1, "cream")] + [(c, 1, "key") for c in "ASDFGHJKL;"]
             + [("ENTER", 2, "cream"), ("CLEAR", 1, "cream")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 1.75, "cream")] + [(c, 1, "key") for c in "ZXCVBNM,./"]
             + [("SHIFT", 1.75, "cream")]),
        dict(s=S[4], x=X0, keys=[(None, 3.0), (" ", 6, "key")]),
    ])

DISPLAY = dict(at=(0.0, 380.0, 30.0), size=(390.0, 310.0, 50.0), back=(320.0, 250.0, 220.0), radius=14.0, colour="tv",
               glass=(268.0, 200.0), glass_at=(-45.0, 162.0), recess=18.0, bulge=10.0, frame=13.0, corner=18.0,
               back_dz=0.0,
               faces=dict(front=[("rect", 325.0, 24.0, 382.0, 286.0, "panel", 4.0),
                                 ("hslots", 333.0, 32.0, 374.0, 130.0, 10, "black"),
                                 ("dots", 336.0, 160.0, 371.0, 242.0, 2, 4, 5.0, "black"),
                                 ("circle", 333.0, 263.0, 1.4, "#FF3A2C")]))

SEAT = (W / 2 - 90.0 + 60.0, (SLOT["y"][0] + SLOT["y"][1]) / 2, (SLOT["z"][0] + SLOT["z"][1]) / 2)
OUT = 140.0
MEDIA = dict(kind="box", size=(120.0, 100.0, 20.0), seat=SEAT, turn=(0.0, 0.0, 180.0), colour="pak",
             label=[("rect", 30.0, 6.0, 114.0, 94.0, "label", 1.5), ("cover", 32.0, 8.0, 112.0, 80.0),
                    ("text", "PROGRAM PAK", "arialbd.ttf", 4.0, 72.0, 87.0, "ink"),
                    ("hslots", 4.0, 10.0, 24.0, 90.0, 8, "#2A2A2E")],
             keys=[(0, dict(x=OUT, scale=0.0)), (8, dict(x=OUT, scale=0.0)), (16, dict(x=OUT)), (34, dict(x=0.0)),
                   (198, dict(x=0.0)), (212, dict(x=OUT)), (216, dict(x=OUT)), (228, dict(x=OUT, z=30.0, scale=0.0))])

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(256, 192), palette=["#000000", "#07FF00", "#FFFF00", "#3B08FF", "#CC003B", "#FFFFFF", "#07E399",
                                      "#FF1CFF", "#FF8100"],
              ink="#0A2A0A", paper="#07FF00", border=("#000000", 0.1), prompt="PRESS SPACE",
              boot=["EXTENDED COLOR BASIC 1.0", "COPYRIGHT (C) 1980 BY TANDY", "UNDER LICENSE FROM MICROSOFT", "",
                    "OK"],
              load=["", "", "", "  MOONCREST CHRONICLE", "", "  PROGRAM PAK"],
              game=("Mooncrest Chronicle (Europe)", "snes"))
SHOW = [(42, 72, "load"), (72, 96, "title"), (96, 196, "game")]
