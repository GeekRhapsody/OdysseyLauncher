"""The TRS-80 card's measurements (computer.py's card `trs80`, the system `trs-80`; computer_layout.py says what a card
holds).

Tandy's TRS-80 Model I (1977), its Video Display and a cassette recorder (unbranded: no photograph of its CTR-41 was
found): the keyboard unit 419 x 216 x 95 mm (a museum's catalogue), the display about 345 x 330 x 300 (scaled from
photographs); the parts placed from photographs. The silver-grey keyboard unit: its rim round the dark deck, the black
keys (ENTER cream) with the keypad apart at the right and the power light between them, the badge strip over the top
row, the raised back with its vents. The display behind it: the black front with the screen at its left and the badge
panel at its right, the silver band under it with the grille and three controls, the grey shell.

The clip: the recorder's lid swings up, a cassette (a made-up game) drops into its well and the lid shuts; PLAY goes down
and its light comes on while Level II BASIC loads the game with SYSTEM; its title, and the game played on the arrows and
the space bar; STOP, and the cassette comes out and goes.
"""

NAME = "TRS-80"
YAW, PITCH = -24.0, 24.0

COLOURS = dict(case="#A3A29C", deck="#2C2925", key="#1E1C1A", cream="#E6DCC6", white="#F2F2EE", ink="#1A1A1A",
               bezel="#1F1C14", red="#E8302A", recorder="#3A3A3E", smoked="#1E1C1A", keycap="#C8C8C4", lit="#3AE060",
               shell="#2A2A2E", label="#F2F0E8", window="#3A3430", vent="#6A6A66", cable="#1A1A1C")

W = 419.0
BLOCKS = [
    dict(shape=("profile", -W / 2, W / 2, [(0.0, 0.0), (216.0, 0.0), (216.0, 92.0), (212.0, 95.0), (178.0, 95.0),
                                          (174.0, 90.0), (174.0, 78.0), (10.0, 35.0), (0.0, 30.0)]), round=3.0,
         colour="case",
         faces=dict(top=[("slots", 30.0, 8.0, 390.0, 30.0, 40, "vent"),
                         ("rect", 24.5, 46.0, 394.5, 206.0, "deck", 4.0),
                         ("rect", 150.0, 88.0, 270.0, 102.0, "#0E0C0A", 1.0),
                         ("text", "Radio Shack  TRS-80", "arialbd.ttf", 3.6, 210.0, 93.0, "white"),
                         ("text", "MICROCOMPUTER SYSTEM", "arialbd.ttf", 2.2, 210.0, 99.0, "white"),
                         ("circle", 310.0, 188.0, 2.2, "red")])),
    dict(shape=("box", 240.0, 400.0, -40.0, 180.0, 0.0, 55.0), round=4.0, colour="recorder",
         cuts=[(265.0, 375.0, 40.0, 130.0, 37.0, 70.0)],
         faces=dict(top=[("text", "CASSETTE RECORDER", "arialbd.ttf", 4.0, 80.0, 24.0, "white"),
                         ("text", "000", "consola.ttf", 6.0, 136.0, 38.0, "white")])),
    dict(shape=("box", -170.0, 170.0, 240.0, 520.0, 0.0, 24.0), round=6.0, colour="case"),
]
for k in range(6):
    if k != 2:
        BLOCKS.append(dict(shape=("box", 250.0 + 23.5 * k, 271.0 + 23.5 * k, -30.0, 6.0, 51.0, 61.0), round=1.5,
                           colour="keycap"))

U = 19.05
X0 = -171.0
S = [6.0 + 4 * U, 6.0 + 3 * U, 6.0 + 2 * U, 6.0 + U, 6.0]
KP = 15.0

KEYBOARD = dict(
    origin=(0.0, 14.0, 36.5), slope=14.7, U=U, gap=1.2, height=9.0, taper=2.2, ink="white", legend=3.0, ground="deck",
    inks=dict(cream="ink"),
    rows=[
        dict(s=S[0], x=X0, keys=[(c, 1, "key") for c in "1234567890:-"] + [("BREAK", 1, "key"), (None, 2.0),
                                                                       ("7", 1, "key"), ("8", 1, "key"),
                                                                       ("9", 1, "key")]),
        dict(s=S[1], x=X0, keys=[("↑", 1, "key")] + [(c, 1, "key") for c in "QWERTYUIOP@"]
             + [("←", 1, "key"), ("→", 1, "key"), (None, 1.0), ("4", 1, "key"), ("5", 1, "key"), ("6", 1, "key")]),
        dict(s=S[2], x=X0, keys=[("↓", 1, "key")] + [(c, 1, "key") for c in "ASDFGHJKL;"]
             + [("ENTER", 2, "cream"), ("CLEAR", 1, "key"), (None, 1.0), ("1", 1, "key"), ("2", 1, "key"),
                ("3", 1, "key")]),
        dict(s=S[3], x=X0, keys=[("SHIFT", 1.5, "key")] + [(c, 1, "key") for c in "ZXCVBNM,./"]
             + [("SHIFT", 1.5, "key"), (None, 2.0), ("0", 1, "key"), (".", 1, "key"), ("ENTER", 1, "cream")]),
        dict(s=S[4], x=X0, keys=[(None, 2.0), (" ", 8, "key")]),
    ])

DISPLAY = dict(at=(0.0, 250.0, 24.0), size=(345.0, 300.0, 60.0), back=(300.0, 260.0, 240.0), radius=12.0,
               colour="case", glass=(230.0, 172.0), glass_at=(-42.0, 178.0), recess=18.0, bulge=8.0, frame=12.0,
               corner=12.0, back_dz=0.0,
               faces=dict(front=[("rect", 0.0, 0.0, 345.0, 232.0, "bezel", 6.0),
                                 ("rect", 282.0, 20.0, 334.0, 210.0, "#0E0C0A", 2.0),
                                 ("text", "VIDEO", "arialbd.ttf", 4.0, 308.0, 160.0, "white"),
                                 ("text", "DISPLAY", "arialbd.ttf", 4.0, 308.0, 170.0, "white"),
                                 ("circle", 308.0, 40.0, 3.0, "red"),
                                 ("hslots", 30.0, 244.0, 200.0, 288.0, 6, "deck"),
                                 ("circle", 240.0, 266.0, 8.0, "deck"), ("circle", 272.0, 266.0, 8.0, "deck"),
                                 ("circle", 304.0, 266.0, 8.0, "deck")]))

LID_HINGE = (320.0, 133.0, 56.0)
MOVERS = [dict(name="lid", shape=("box", 263.0, 377.0, 37.0, 133.0, 53.0, 59.0), round=1.5, colour="smoked",
               origin=LID_HINGE, faces=dict(top=[("rect", 22.0, 22.0, 92.0, 70.0, "window", 3.0)]),
               keys=[(0, dict()), (4, dict()), (12, dict(pitch=-62.0)), (32, dict(pitch=-62.0)), (40, dict()),
                     (190, dict()), (198, dict(pitch=-62.0)), (220, dict(pitch=-62.0)), (228, dict())]),
          dict(name="play", shape=("box", 297.0, 318.0, -30.0, 6.0, 51.0, 61.0), round=1.5, colour="keycap",
               origin=(307.5, -12.0, 61.0),
               keys=[(0, dict()), (42, dict()), (46, dict(z=-5.0)), (186, dict(z=-5.0)), (190, dict())])]

MEDIA = dict(kind="box", size=(100.0, 63.0, 12.0), seat=(320.0, 85.0, 44.0), colour="shell",
             label=[("rect", 6.0, 4.0, 94.0, 40.0, "label", 1.5), ("logo", 10.0, 6.0, 90.0, 26.0),
                    ("rect", 26.0, 30.0, 74.0, 38.0, "window", 3.0), ("circle", 36.0, 34.0, 3.0, "white"),
                    ("circle", 64.0, 34.0, 3.0, "white")],
             keys=[(0, dict(z=70.0, scale=0.0)), (8, dict(z=70.0, scale=0.0)), (16, dict(z=70.0)), (30, dict()),
                   (200, dict()), (210, dict(z=70.0)), (212, dict(z=70.0)), (222, dict(z=90.0, scale=0.0))])

LIGHTS = [dict(name="play_light", at=(390.0, -20.0, 55.0), face="top", size=(4.0, 4.0), colour="lit",
               on=[(46, 186, "on")])]

CABLES = [dict(points=[(240.0, 120.0, 20.0), (225.0, 150.0, 4.0), (214.0, 190.0, 30.0)], r=2.2, colour="cable")]

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(384, 192), palette=["#000000", "#3A4048", "#8A92A0", "#E8F0FF"], ink="#E8F0FF", paper="#000000",
              border=("#000000", 0.08), prompt="PRESS SPACE",
              boot=["MEMORY SIZE?", "RADIO SHACK LEVEL II BASIC", "READY", ">"],
              load=["MEMORY SIZE?", "RADIO SHACK LEVEL II BASIC", "READY", ">SYSTEM", "*? PUCK", "* *", "*? /"],
              game=("Puck Rush (Europe)", "megadrive"))
SHOW = [(48, 80, "load"), (80, 100, "title"), (100, 188, "game")]
