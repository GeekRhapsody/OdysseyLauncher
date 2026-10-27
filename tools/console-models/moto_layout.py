"""The Thomson MO5 card's measurements (computer.py's card `moto`; computer_layout.py says what a card holds).

Thomson's MO5 (1984), its light pen and a 1980s 14-inch colour television (unbranded) behind it: the MO5 291 x 190 x 51 mm
(French Wikipedia), so small that its keys are at a 16 mm pitch; the parts placed from photographs of it from above,
behind and either side. The charcoal wedge: the deck rising from its lip, the AZERTY keys (grey, white and yellow
legends; SHIFT yellow, BASIC black); along its back the MEMO5 slot in its smoked surround, INITIAL PROG., the vents' slats,
MO5 and UC 50.001 THOMSON; the light pen and the recorder's sockets in the oval recess in its right side. The light pen
lies beside it, its cord to its socket.

The clip: a MEMO5 cartridge (a made-up game) drops into the slot; the MO5's BASIC starts it, its title, and the game is
played on the arrows and the space bar; the cartridge rises out and goes.
"""

NAME = "MO5"
YAW, PITCH = -24.0, 26.0

COLOURS = dict(case="#2D2D2E", key="#8C8984", shift="#E6EA6E", black="#151515", white="#F2F2EE", yellow="#E2D64A",
               logo="#C5CC46", cream="#E8E2C8", smoked="#141416", tv="#B8B8B4", screen="#1A1A1C", alu="#C8C9CB",
               cart="#3A3A3E", label="#F2F0E8", cable="#1A1A1C", wood="#5A4636")

W = 291.0
BLOCKS = [
    dict(shape=("profile", -W / 2, W / 2, [(0.0, 0.0), (190.0, 0.0), (190.0, 48.0), (186.0, 51.0), (140.0, 51.0),
                                          (10.0, 26.0), (0.0, 22.0)]), round=3.0, colour="case",
         cuts=[(-123.0, -52.0, 158.0, 175.0, 10.0, 60.0)],
         faces=dict(top=[("rect", 15.0, 6.0, 98.0, 42.0, "smoked", 3.0), ("rect", 22.0, 14.0, 93.0, 34.0, "black", 1.0),
                         ("rect", 4.0, 18.0, 12.0, 30.0, "cream", 1.5),
                         ("text", "INITIAL PROG.", "arialbd.ttf", 2.0, 8.0, 34.0, "white"),
                         ("hslots", 104.0, 4.0, 196.0, 46.0, 6, "black"),
                         ("text", "MO5", "ariblk.ttf", 14.0, 230.0, 20.0, "logo"),
                         ("text", "UC 50.001 THOMSON", "arialbd.ttf", 3.2, 240.0, 36.0, "white")],
                    right=[("rect", 100.0, 14.0, 150.0, 34.0, "black", 9.0), ("circle", 114.0, 24.0, 5.0, "#0A0A0A"),
                           ("circle", 136.0, 24.0, 5.0, "#0A0A0A")])),
    dict(shape=("box", -215.0, 215.0, 232.0, 560.0, 0.0, 26.0), round=6.0, colour="wood"),
]

U = 16.0
X0 = -124.0
S = [68.0, 52.0, 36.0, 20.0, 4.0]

KEYBOARD = dict(
    origin=(0.0, 14.0, 26.5), slope=10.9, U=U, gap=3.0, height=6.0, taper=1.5, ink="white", legend=2.6, ground="case",
    inks=dict(shift="#202020"),
    rows=[
        dict(s=S[0], x=X0, keys=[("STOP", 1, "key")] + [(c, 1, "key") for c in "123456789Ø-+"]
             + [("ACC", 1, "key"), ("↑", 1, "key")]),
        dict(s=S[1], x=X0, keys=[("CNT", 1, "key"), (None, 0.5)] + [(c, 1, "key") for c in "AZERTYUIOP/*"]
             + [("←", 1, "key"), ("→", 1, "key")]),
        dict(s=S[2], x=X0, keys=[("RAZ", 1, "key"), ("↰", 1, "key")] + [(c, 1, "key") for c in "QSDFGHJKLM"]
             + [("ENTRÉE", 1.75, "key"), (None, 0.75), ("↓", 1, "key")]),
        dict(s=S[3], x=X0, keys=[("", 1.75, "shift"), (None, 0.25)] + [(c, 1, "key") for c in "WXCVBN,.@"]
             + [("BASIC", 1.75, "black"), ("INS", 1, "key"), ("EFF", 1, "key")]),
        dict(s=S[4], x=X0, keys=[(None, 3.0), (" ", 4, "key")]),
    ])

DISPLAY = dict(at=(0.0, 250.0, 26.0), size=(390.0, 310.0, 50.0), back=(320.0, 250.0, 250.0), radius=14.0, colour="tv",
               glass=(268.0, 200.0), glass_at=(-45.0, 162.0), recess=18.0, bulge=10.0, frame=13.0, corner=18.0,
               back_dz=0.0, back_colour="screen",
               faces=dict(front=[("rect", 325.0, 24.0, 382.0, 286.0, "#A8A8A4", 4.0),
                                 ("hslots", 333.0, 32.0, 374.0, 130.0, 10, "screen"),
                                 ("dots", 336.0, 160.0, 371.0, 242.0, 2, 4, 5.0, "screen"),
                                 ("rect", 341.0, 258.0, 366.0, 268.0, "screen", 3.0),
                                 ("circle", 333.0, 263.0, 1.4, "#FF3A2C")]))

SEAT = (-87.5, 166.5, 44.0)
MEDIA = dict(kind="box", size=(70.0, 64.0, 16.0), seat=SEAT, turn=(90.0, 0.0, 0.0), colour="cart",
             label=[("rect", 4.0, 4.0, 66.0, 48.0, "label", 1.5), ("cover", 6.0, 6.0, 64.0, 46.0),
                    ("text", "MEMO5", "ariblk.ttf", 4.0, 35.0, 56.0, "white")],
             keys=[(0, dict(z=60.0, scale=0.0)), (6, dict(z=60.0, scale=0.0)), (14, dict(z=60.0)),
                   (20, dict(z=64.0, spin=180.0)), (28, dict(z=60.0, spin=360.0)), (40, dict(spin=360.0)),
                   (198, dict(spin=360.0)), (210, dict(z=60.0, spin=360.0)), (222, dict(z=80.0, spin=360.0, scale=0.0))])

CABLES = [dict(points=[(185.0, 22.0, 6.0), (185.0, 160.0, 6.0)], r=6.0, colour="alu"),
          dict(points=[(185.0, 8.0, 6.0), (185.0, 24.0, 6.0)], r=3.0, colour="black"),
          dict(points=[(185.0, 160.0, 6.0), (182.0, 182.0, 3.0), (160.0, 182.0, 3.0), (150.0, 150.0, 6.0),
                       (146.5, 126.0, 24.0)], r=1.8, colour="cable")]

PRESS = {"↑": (110, 150), "←": (122, 170), "→": (134, 180), "↓": (144,), " ": (100, 128, 160, 188)}

SCREEN = dict(px=(320, 200), palette=["#000000", "#FF0000", "#00FF00", "#FFFF00", "#0000FF", "#FF00FF", "#00FFFF",
                                      "#FFFFFF", "#777777", "#FF7777", "#77FF77", "#FFFF77", "#7777FF", "#FF77FF",
                                      "#77FFFF", "#FFAA00"],
              ink="#0000AA", paper="#55FFFF", border=("#55FFFF", 0.08), prompt="APPUYEZ SUR ESPACE",
              boot=["MO5 BASIC 1.0", "(c) Microsoft 1984", "OK"],
              load=["MO5 BASIC 1.0", "(c) Microsoft 1984", "OK", "", "MEMO5", "CRIMSON KUNAI"],
              game=("Crimson Kunai (Europe)", "megadrive"))
SHOW = [(42, 72, "load"), (72, 96, "title"), (96, 196, "game")]
