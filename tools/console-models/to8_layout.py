"""The Thomson TO8 card's measurements (computer.py's card `to8`; computer_layout.py says what a card holds).

Thomson's TO8D (1986) and a colour monitor (unbranded, the case's off-white) behind it: the TO8D 440 x 280 x 85 mm (French
Wikipedia), its keys at the standard 19.05 mm pitch; the parts placed from photographs of it from above and the right.
The off-white case: the deck with the keys over its front half (the five flat function keys, the main block with its
yellow ENT, the cursor keys, the keypad), the raised back section with its vents, the cartridge slot under its
periwinkle strip and the black band with TO8D and THOMSON, the two lights above the cursor keys; the 3.5-inch drive's
black bezel set into its right side.

The clip: a 3.5-inch disk (a made-up game) slides into the drive in the right side and its light flickers; from the
TO8D's start-up menu the game is called, its title, and it is played on the cursor keys and the space bar; the disk is
ejected and goes.
"""

NAME = "TO8D"
YAW, PITCH = -26.0, 24.0

COLOURS = dict(case="#E3E3DC", key="#DCDCD8", grey="#C7C9CB", yellow="#F2D45E", band="#2A2826", white="#F2F2EE",
               periwinkle="#8FA8E6", black="#141416", ink="#1E1E1E", green="#3FA66A", lit="#3AE060", red="#D03A2E",
               monitor="#DCDBD2", shell="#2A2A2E", label="#F2F0E8", shutter="#B4B8BC", vent="#B8B8B0")

W = 440.0
BLOCKS = [
    dict(shape=("profile", -W / 2, W / 2, [(0.0, 0.0), (280.0, 0.0), (280.0, 82.0), (277.0, 85.0), (160.0, 85.0),
                                          (154.0, 78.0), (154.0, 56.0), (12.0, 32.0), (0.0, 26.0)]), round=3.0,
         colour="case", cuts=[(W / 2 - 25.0, W / 2 + 5.0, 168.0, 252.0, 49.0, 53.0)],
         faces=dict(top=[("slots", 10.0, 6.0, 430.0, 58.0, 45, "vent"),
                         ("rect", 96.0, 62.0, 171.0, 68.0, "periwinkle"), ("rect", 96.0, 68.0, 171.0, 93.0, "black", 2.0),
                         ("rect", 176.0, 70.0, 438.0, 90.0, "band"),
                         ("text", "TO8D", "ariblk.ttf", 9.0, 230.0, 80.0, "white"),
                         ("text", "THOMSON", "arialbd.ttf", 5.0, 380.0, 80.0, "white"),
                         ("circle", 330.0, 112.0, 2.0, "#5A1A16"), ("circle", 346.0, 112.0, 2.0, "#1E4A2A"),
                         ("text", "⏻", "seguisym.ttf", 3.0, 330.0, 105.0, "ink")],
                    right=[("rect", 165.0, 20.0, 255.0, 50.0, "black", 2.0), ("rect", 170.0, 32.0, 250.0, 36.0, "#050506"),
                           ("rect", 236.0, 40.0, 250.0, 46.0, "#2A2A2E", 1.0)])),
    dict(shape=("box", -150.0, 150.0, 300.0, 560.0, 0.0, 26.0), round=6.0, colour="monitor"),
]

U = 19.05
X0 = -203.0
S5 = 6.0
S = [S5 + 4 * U, S5 + 3 * U, S5 + 2 * U, S5 + U, S5]
FROW = S5 + 5 * U + 3.0
CX = 15.3                   # the cursor keys' left edge, in U
KX = 17.6                   # the keypad's

KEYBOARD = dict(
    origin=(0.0, 10.0, 31.5), slope=9.6, U=U, gap=1.2, height=8.5, taper=2.0, ink="ink", legend=3.0, ground="case",
    rows=[
        dict(s=FROW, x=X0, depth=12.0, keys=[(f"F{k}", 2, "key") for k in range(1, 6)]),
        dict(s=S[0], x=X0, keys=[(c, 1, "key") for c in "@1234567890°\\+"] + [("ACC", 1, "key"), (None, 0.3),
                                                                            ("↑", 2, "key"), (None, 0.3),
                                                                            ("7", 1, "grey"), ("8", 1, "grey"),
                                                                            ("9", 1, "grey")]),
        dict(s=S[1], x=X0, keys=[("STOP", 1.5, "key")] + [(c, 1, "key") for c in "AZERTYUIOP¨&"]
             + [(None, 0.5), ("ENT", 1, "yellow", 2), (None, 0.3), ("←", 1, "key"), ("→", 1, "key"), (None, 0.3),
                ("4", 1, "grey"), ("5", 1, "grey"), ("6", 1, "grey")]),
        dict(s=S[2], x=X0, keys=[("CNT", 1, "key")] + [(c, 1, "key") for c in "!QSDFGHJKLM%|"]
             + [(None, 1.0), (None, 0.3), ("↓", 2, "key"), (None, 0.3), ("1", 1, "grey"), ("2", 1, "grey"),
                ("3", 1, "grey")]),
        dict(s=S[3], x=X0, keys=[("CAPS", 1.25, "key"), ("▲", 1.25, "key")] + [(c, 1, "key") for c in "WXCVBN?./<"]
             + [("▲", 1.5, "key"), ("RAZ", 1, "key"), (None, 0.3), ("INS", 1, "key"), ("EFF", 1, "key"),
                (None, 0.3), ("Ø", 1, "grey"), (".", 1, "grey"), ("ENT", 1, "grey")]),
        dict(s=S[4], x=X0, keys=[(None, 2.5), (" ", 8, "key")]),
    ])

DISPLAY = dict(at=(0.0, 310.0, 26.0), size=(360.0, 310.0, 60.0), back=(300.0, 250.0, 280.0), radius=14.0,
               colour="monitor", glass=(270.0, 202.0), glass_at=(0.0, 168.0), recess=20.0, bulge=8.0, frame=13.0,
               corner=14.0, back_dz=6.0,
               faces=dict(front=[("rect", 290.0, 282.0, 330.0, 294.0, "grey", 3.0),
                                 ("circle", 280.0, 288.0, 1.6, "red"), ("dots", 30.0, 282.0, 90.0, 294.0, 6, 1, 2.0,
                                                                         "grey")]))

SEAT = (W / 2 - 52.0, 210.0, 51.0)
OUT = 150.0
MEDIA = dict(kind="box", size=(90.0, 94.0, 3.3), seat=SEAT, turn=(0.0, 0.0, 90.0), colour="shell",
             label=[("rect", 18.0, 0.0, 72.0, 30.0, "shutter"), ("rect", 49.0, 4.0, 59.0, 26.0, "#3A3A3E"),
                    ("rect", 6.0, 36.0, 84.0, 90.0, "label", 1.0), ("cover", 8.0, 38.0, 82.0, 88.0)],
             keys=[(0, dict(x=OUT, scale=0.0)), (8, dict(x=OUT, scale=0.0)), (16, dict(x=OUT)), (32, dict(x=0.0)),
                   (198, dict(x=0.0)), (204, dict(x=34.0)), (212, dict(x=34.0)), (224, dict(x=90.0, z=30.0, scale=0.0))])

LIGHTS = [dict(name="drive_light", at=(126.0, 168.0, 85.0), face="top", size=(4.0, 4.0), colour="lit",
               on=[(34, 92, "flicker"), (196, 202, "flicker")])]

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(320, 200), palette=None, ink="#00006A", paper="#AAFFFF", border=("#AAFFFF", 0.08),
              prompt="APPUYEZ SUR ESPACE",
              boot=["TO8D                    THOMSON", "", "DATE: jj-mm-aa        RAM: 512K", "",
                    "1 BASIC 512 MICROSOFT 1.0", "2 BASIC MICROSOFT 1.0", "3 Reglage et preferences",
                    "4 Appel de programme", "5 Exploitation de fichiers"],
              load=["TO8D                    THOMSON", "", "4 Appel de programme", "", "Chargement...", "",
                    "BASELINE HEROES"],
              game=("Baseline Heroes (Europe)", "megadrive"))
SHOW = [(40, 72, "load"), (72, 96, "title"), (96, 196, "game")]
