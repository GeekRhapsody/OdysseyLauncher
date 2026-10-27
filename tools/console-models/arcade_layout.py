"""The arcade cards' measurements: the cabinets, and what each card shows. Shared by arcade_print.py (which draws each
card's printing and screens) and arcade.py (which builds it). Plain Python: Blender's Python imports it too.

An arcade system is a board, played in cabinets, so its card is a cabinet typical of it (CARDS): its marquee (or its
POP sign, or its control panel's front) names the board, and its screen plays one of tools/made-up-games's arcade games
(made up: no real game's art) from start-up to a credit's play. Millimetres: x from the cabinet's middle (left to
right), y back from the control panel's front edge, z up from the floor.

A cabinet (CABINETS) is one of two kinds:
- `upright`: an American upright: two side panels (`outline`, their side outline (y, z), anticlockwise seen from the
  right; `side` thick, edged with T-moulding) and the body between them (`body`, its own outline, its front faces set
  back between the panels);
- `candy`: a Japanese candy cabinet, one rounded body across its whole width (`body`), its sides printed.
Either way the control panel is a box of its own (`panel`) standing out in front, its plan's front corners cut
(`corner`) or rounded (`round`). The body's front faces are named by their spans ((y, z) to (y, z)): the marquee and
the speaker panel (top, foot), the bezel's slope (foot, top: the monitor's recess cut into it, a CRT's curved glass
set in), the lower front (foot, top); `spans` paints others a swatch. `tops` are boxes standing on the cabinet (a
marquee's lightbox, speakers, a POP sign), their fronts printed. Each cabinet names its monitor's glass as a 4:3 game
shows it; a vertical game turns it (glass()).

Three textures a card: `<card>_print.png` (PRINT_ATLAS square, PRINT_REGIONS: the marquee, the speakers, the control
panel's overlay, the lower front, the bezel's art, a POP sign, the control panel's front strip; swatches),
`<card>_side.jpg` (SIDE_PX: the side art, the side outline's bounds fitted to it, seen from the right) and
`<card>_media.jpg` (the screens, media_regions()). A region is (x, y, width, height) in pixels.
"""

import math

FPS = 30
LENGTH = 240                 # 8 s

PRINT_ATLAS = 1024
PRINT_REGIONS = dict(marquee=(0, 0, 1024, 232), speakers=(0, 240, 1024, 112), panel=(0, 360, 1024, 300),
                     front=(0, 668, 392, 300), bezel=(400, 668, 400, 300), pop=(808, 668, 216, 300),
                     strip=(0, 976, 400, 48))
SWATCH_NAMES = ("case", "side", "moulding", "black", "metal", "dark", "coin", "white", "red", "red_lit", "b1", "b2",
                "b3", "b4", "start", "start_lit", "ball1", "ball2", "panel_edge", "kick", "lower", "top", "trim",
                "grille", "stick", "seat", "seat2", "base", "rubber", "chrome", "dash", "pedal", "lit", "lit2")
SWATCHES = {name: (420 + 24 * (k % 25), 988 + 24 * (k // 25)) for k, name in enumerate(SWATCH_NAMES)}

SIDE_PX = (512, 1024)        # the side art's image
SCREEN_SIZES = {"4:3": (640, 480), "3:4": (480, 640), "16:9": (768, 432)}   # each screen's picture, before the atlas
SCREENS = ("boot", "title", "game1", "game2")
MENUS = ("menu", "menu2")    # a twin-monitor cabinet's top screen: the game menu, a game chosen


def screen_names(card):
    return SCREENS + (MENUS if card.get("twin") else ())


def media_size(card):
    """The media atlas: 1024 wide, a row of two screens each 512 down."""
    return 1024, 512 * ((len(screen_names(card)) + 1) // 2)


def media_regions(card):
    """The screens' regions in the media atlas, two to a row: the board starting up, the title, two frames of play;
    a twin-monitor cabinet's menus."""
    out = {}
    for i, name in enumerate(screen_names(card)):
        w, h = SCREEN_SIZES["4:3" if name in MENUS else card["screen"]]
        k = min(504 / w, 504 / h)
        out[name] = ((i % 2) * 512, (i // 2) * 512, round(w * k), round(h * k))
    return out


def glass(cab, card):
    """The monitor's glass (width, height) as the card's game shows it: the cabinet's tube, turned for a vertical
    game."""
    w, h = cab["screen"]["glass"]
    return {"4:3": (w, h), "3:4": (h, w), "16:9": (w, w * 9 / 16)}[card["screen"]]


def recess(cab, card):
    """The monitor's recess in the bezel's slope: (x0, x1), (s0, s1), s up the slope from its foot."""
    gw, gh = glass(cab, card)
    s = cab["screen"]
    m = s.get("margin", 16.0)
    return (-gw / 2 - m, gw / 2 + m), (s["middle"] - gh / 2 - m, s["middle"] + gh / 2 + m)


# Each player's buttons beside their stick, (dx, dv) from it, by how many the game has: two rows of three for a
# fighter, Neo Geo's arc of four, a row of three, two, one. The first two are the ones the clip presses.
BUTTON_SPOTS = {
    6: [(60.0, -20.0), (100.0, -24.0), (140.0, -20.0), (60.0, 22.0), (100.0, 18.0), (140.0, 22.0)],
    4: [(56.0, 12.0), (92.0, -6.0), (130.0, -12.0), (168.0, -10.0)],
    3: [(62.0, -4.0), (102.0, -10.0), (142.0, -6.0)],
    2: [(64.0, -4.0), (106.0, -4.0)],
    1: [(72.0, 0.0)],
}


def buttons(cab, card):
    """Each player's buttons, {player: [(x, v), ...]}, on the control panel."""
    if "sticks" not in cab:                               # a driving cabinet: a wheel, no sticks
        return {}
    spots = BUTTON_SPOTS[card.get("n_buttons", 6)]
    return {player: [(cab["sticks"][player][0] + dx, cab["sticks"][player][1] + dv) for dx, dv in spots]
            for player in ("p1", "p2") if player in cab["sticks"]}


# ---- Cabinets --------------------------------------------------------------------------------------------------------

CABINETS = {
    # Capcom's American dedicated cabinet of the early 1990s, the first "Big Blue" (Street Fighter II Champion Edition):
    # blue laminate sides with a white T-moulding, the top leaning forward over the screen like a hood, the wide
    # control panel with cut corners standing out in front, the waist under it. Traced from a side photograph.
    "bigblue": dict(
        kind="upright", width=660.0, side=19.0, height=1830.0, depth=960.0,
        outline=[(380.0, 0.0), (960.0, 0.0), (960.0, 1480.0), (470.0, 1830.0), (595.0, 1390.0), (345.0, 905.0),
                 (150.0, 868.0), (160.0, 760.0), (230.0, 690.0), (330.0, 660.0), (360.0, 600.0)],
        body=[(395.0, 0.0), (955.0, 0.0), (955.0, 1470.0), (512.0, 1800.0), (512.0, 1640.0), (612.0, 1395.0),
              (370.0, 905.0), (330.0, 860.0), (330.0, 700.0), (390.0, 640.0)],
        marquee=((512.0, 1800.0), (512.0, 1640.0)), speakers=((512.0, 1640.0), (612.0, 1395.0)),
        bezel=((370.0, 905.0), (612.0, 1395.0)),
        screen=dict(glass=(480.0, 360.0), middle=268.0, margin=15.0, depth=40.0, bulge=12.0),
        lower=((395.0, 0.0), (390.0, 640.0)),
        panel=dict(top=((0.0, 905.0), (345.0, 945.0)), front=820.0, width=900.0, corner=110.0, back=380.0),
        coin=dict(kind="door", x=(-110.0, 110.0), z=(170.0, 560.0)),
        kick=(0.0, 70.0),
        sticks=dict(p1=(-250.0, 130.0), p2=(170.0, 130.0), shaft=(5.0, 50.0), ball=17.0),
        start=[(-40.0, 200.0), (40.0, 200.0)], button=dict(r=13.0, height=9.0),
    ),
    # Its successor, the Q-Sound "Big Blue" (Super Street Fighter II): the top square, the marquee a lightbox standing
    # on it, the speaker panel upright under it, the screen set back in its black surround, the control panel's front
    # carrying the maker's badge, a tall coin door.
    "bigblue_q": dict(
        kind="upright", width=660.0, side=19.0, height=1890.0, depth=960.0,
        outline=[(380.0, 0.0), (960.0, 0.0), (960.0, 1660.0), (530.0, 1660.0), (530.0, 1420.0), (345.0, 905.0),
                 (150.0, 868.0), (160.0, 760.0), (230.0, 690.0), (330.0, 660.0), (360.0, 600.0)],
        body=[(395.0, 0.0), (955.0, 0.0), (955.0, 1645.0), (545.0, 1645.0), (545.0, 1430.0), (375.0, 905.0),
              (330.0, 860.0), (330.0, 700.0), (390.0, 640.0)],
        speakers=((545.0, 1645.0), (545.0, 1430.0)),
        bezel=((375.0, 905.0), (545.0, 1430.0)),
        screen=dict(glass=(480.0, 360.0), middle=282.0, margin=16.0, depth=70.0, bulge=12.0),
        lower=((395.0, 0.0), (390.0, 640.0)),
        panel=dict(top=((0.0, 905.0), (345.0, 945.0)), front=800.0, width=900.0, corner=120.0, back=380.0,
                   strip=True),
        coin=dict(kind="door", x=(-90.0, 90.0), z=(130.0, 600.0)),
        kick=(0.0, 70.0),
        sticks=dict(p1=(-250.0, 130.0), p2=(170.0, 130.0), shaft=(5.0, 50.0), ball=17.0),
        start=[(-40.0, 205.0), (40.0, 205.0)], button=dict(r=13.0, height=9.0),
        tops=[dict(x=(-311.0, 311.0), y=(570.0, 720.0), z=(1640.0, 1890.0), face="marquee", colour="black", r=5.0)],
    ),
    # Capcom's Japanese 25-inch cabinet, the BGS-25 ("Q25"): white, blue under the control panel, a broad blue band
    # rising across each side with CAPCOM along the screen's slope, two Q-Sound speakers on top with a POP sign
    # between them, the control panel's front carrying the maker's strip.
    "bgs25": dict(
        kind="candy", width=760.0, height=1680.0, depth=800.0, round=10.0,
        body=[(180.0, 0.0), (800.0, 0.0), (800.0, 1290.0), (735.0, 1450.0), (500.0, 1460.0), (455.0, 1420.0),
              (440.0, 1370.0), (250.0, 850.0), (180.0, 805.0)],
        bezel=((250.0, 850.0), (440.0, 1370.0)),
        screen=dict(glass=(500.0, 375.0), middle=282.0, margin=14.0, depth=50.0, bulge=12.0),
        lower=((180.0, 0.0), (180.0, 700.0)),
        panel=dict(top=((0.0, 800.0), (270.0, 840.0)), front=690.0, width=760.0, round=40.0, back=290.0,
                   strip=True),
        coin=dict(kind="plate", at=(322.0, 236.0), plate=(40.0, 50.0), slot=(4.0, 24.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(-270.0, 120.0), p2=(90.0, 120.0), shaft=(5.0, 46.0), ball=17.0),
        start=[(-30.0, 215.0), (30.0, 215.0)], button=dict(r=12.0, height=8.0),
        tops=[dict(x=(-370.0, -150.0), y=(480.0, 680.0), z=(1452.0, 1650.0), face="speakers", colour="black",
                   r=8.0),
              dict(x=(150.0, 370.0), y=(480.0, 680.0), z=(1452.0, 1650.0), face="speakers", colour="black", r=8.0),
              dict(x=(-108.0, 108.0), y=(560.0, 580.0), z=(1455.0, 1625.0), face="pop", colour="white", r=3.0)],
    ),
    # Capcom's Impress: white and rounded, two speaker boxes on its top and the POP sign standing between them, the
    # control panel's overlay blue edged with pink.
    "impress": dict(
        kind="candy", width=740.0, height=1720.0, depth=880.0, round=12.0,
        body=[(165.0, 0.0), (880.0, 0.0), (880.0, 1420.0), (840.0, 1460.0), (475.0, 1460.0), (452.0, 1345.0),
              (255.0, 840.0), (165.0, 795.0)],
        bezel=((255.0, 840.0), (452.0, 1345.0)),
        screen=dict(glass=(560.0, 420.0), middle=262.0, margin=14.0, depth=55.0, bulge=13.0),
        lower=((165.0, 0.0), (165.0, 700.0)),
        panel=dict(top=((0.0, 800.0), (275.0, 830.0)), front=690.0, width=740.0, round=70.0, back=280.0,
                   strip=True),
        coin=dict(kind="plate", at=(312.0, 222.0), plate=(42.0, 52.0), slot=(4.0, 24.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(-262.0, 118.0), p2=(98.0, 118.0), shaft=(5.0, 46.0), ball=17.0),
        start=[(-28.0, 210.0), (28.0, 210.0)], button=dict(r=12.0, height=8.0),
        tops=[dict(x=(-365.0, -150.0), y=(500.0, 700.0), z=(1452.0, 1640.0), face="speakers", colour="black",
                   r=10.0),
              dict(x=(150.0, 365.0), y=(500.0, 700.0), z=(1452.0, 1640.0), face="speakers", colour="black", r=10.0),
              dict(x=(-125.0, 125.0), y=(585.0, 605.0), z=(1458.0, 1720.0), face="pop", colour="white", r=4.0)],
    ),
    # Sega's Blast City: white, its back leaning in to a narrow top, the marquee under a hood leaning out over the
    # screen, the swoosh along each side; the coin door on the lower front.
    "blastcity": dict(
        kind="candy", width=730.0, height=1650.0, depth=870.0, round=12.0,
        body=[(210.0, 0.0), (870.0, 0.0), (870.0, 1130.0), (600.0, 1650.0), (468.0, 1650.0), (500.0, 1395.0),
              (300.0, 830.0), (210.0, 790.0)],
        marquee=((468.0, 1650.0), (500.0, 1395.0)),
        bezel=((300.0, 830.0), (500.0, 1395.0)),
        screen=dict(glass=(560.0, 420.0), middle=300.0, margin=14.0, depth=60.0, bulge=13.0),
        lower=((210.0, 0.0), (210.0, 700.0)),
        panel=dict(top=((0.0, 790.0), (310.0, 822.0)), front=690.0, width=730.0, round=30.0, back=300.0),
        coin=dict(kind="door", x=(170.0, 300.0), z=(330.0, 590.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(-250.0, 125.0), p2=(110.0, 125.0), shaft=(5.0, 46.0), ball=17.0),
        start=[(-30.0, 215.0), (30.0, 215.0)], button=dict(r=12.0, height=8.0),
    ),
    # Sega's Versus City: two players face each other through it, so it is two cabinets back to back under one
    # roof, the roof orange-red with WINNER on it; each side's control panel is one player's.
    "versuscity": dict(
        kind="candy", width=870.0, height=1530.0, depth=1500.0, round=10.0,
        body=[(200.0, 0.0), (1300.0, 0.0), (1300.0, 740.0), (1200.0, 800.0), (980.0, 1255.0), (960.0, 1355.0),
              (750.0, 1530.0), (540.0, 1355.0), (520.0, 1255.0), (300.0, 800.0), (200.0, 740.0)],
        marquee=((540.0, 1355.0), (520.0, 1255.0)),
        speakers=((750.0, 1530.0), (540.0, 1355.0)),
        bezel=((300.0, 800.0), (520.0, 1255.0)),
        spans=[(((750.0, 1530.0), (960.0, 1355.0)), "top"), (((960.0, 1355.0), (980.0, 1255.0)), "black"),
               (((980.0, 1255.0), (1200.0, 800.0)), "black")],
        screen=dict(glass=(560.0, 420.0), middle=252.0, margin=14.0, depth=55.0, bulge=13.0),
        lower=((200.0, 0.0), (200.0, 690.0)),
        panel=dict(top=((0.0, 760.0), (310.0, 790.0)), front=660.0, width=870.0, round=40.0, back=300.0),
        coin=dict(kind="plate", at=(-345.0, 200.0), plate=(44.0, 60.0), slot=(4.0, 26.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(-90.0, 125.0), shaft=(5.0, 46.0), ball=17.0),
        start=[(240.0, 160.0)], button=dict(r=12.0, height=8.0),
    ),
    # Sammy's Atomiswave cabinet: white, the hood over the screen bulging out to its lit marquee, the band down each
    # side green to black, flames at its foot; the control panel's ends rounded.
    "aw_sd": dict(
        kind="candy", width=760.0, height=1710.0, depth=940.0, round=14.0,
        body=[(220.0, 0.0), (940.0, 0.0), (940.0, 1560.0), (880.0, 1660.0), (760.0, 1710.0), (560.0, 1710.0),
              (450.0, 1672.0), (400.0, 1592.0), (400.0, 1470.0), (470.0, 1330.0), (300.0, 820.0), (220.0, 780.0)],
        marquee=((400.0, 1592.0), (400.0, 1470.0)),
        bezel=((300.0, 820.0), (470.0, 1330.0)),
        screen=dict(glass=(560.0, 420.0), middle=262.0, margin=14.0, depth=55.0, bulge=13.0),
        lower=((220.0, 0.0), (220.0, 700.0)),
        panel=dict(top=((0.0, 795.0), (315.0, 825.0)), front=690.0, width=780.0, round=110.0, back=300.0),
        coin=dict(kind="plate", at=(300.0, 238.0), plate=(44.0, 54.0), slot=(4.0, 24.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(-250.0, 120.0), p2=(100.0, 120.0), shaft=(5.0, 46.0), ball=17.0),
        start=[(-40.0, 200.0), (40.0, 200.0)], button=dict(r=12.0, height=8.0),
    ),
    # A classic upright of the early 1980s, a dedicated game's cabinet: tall and narrow, the side panels' front edge
    # coming forward round the control panel and in under it, the marquee upright under the top, the monitor deep in
    # its bezel; one stick, for players taking turns. Traced from a side photograph of one.
    "classic": dict(
        kind="upright", width=620.0, side=19.0, height=1750.0, depth=790.0,
        outline=[(48.0, 0.0), (790.0, 0.0), (790.0, 1725.0), (209.0, 1751.0), (157.0, 1564.0), (133.0, 1014.0),
                 (29.0, 907.0), (0.0, 880.0), (0.0, 720.0), (48.0, 693.0), (57.0, 425.0)],
        body=[(62.0, 0.0), (785.0, 0.0), (785.0, 1720.0), (232.0, 1738.0), (232.0, 1575.0), (330.0, 1525.0),
              (178.0, 1010.0), (150.0, 960.0), (150.0, 700.0), (62.0, 690.0)],
        marquee=((232.0, 1738.0), (232.0, 1575.0)), speakers=((232.0, 1575.0), (330.0, 1525.0)),
        bezel=((178.0, 1010.0), (330.0, 1525.0)),
        screen=dict(glass=(390.0, 292.0), middle=268.0, margin=18.0, depth=50.0, bulge=10.0),
        lower=((62.0, 0.0), (62.0, 690.0)),
        panel=dict(top=((0.0, 880.0), (190.0, 915.0)), front=720.0, width=582.0, corner=2.0, back=200.0),
        coin=dict(kind="door", x=(-110.0, 110.0), z=(250.0, 560.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(-130.0, 95.0), shaft=(5.0, 50.0), ball=17.0),
        start=[(160.0, 70.0), (220.0, 70.0)], button=dict(r=13.0, height=9.0),
    ),
    # A four-slot multi-game cabinet of the 1990s, its marquee a lightbox on its top showing the four games inside;
    # red sides, the control panel with each player's four buttons in an arc.
    "bigred": dict(
        kind="upright", width=640.0, side=19.0, height=1960.0, depth=880.0,
        outline=[(370.0, 0.0), (880.0, 0.0), (880.0, 1640.0), (520.0, 1640.0), (520.0, 1450.0), (340.0, 920.0),
                 (150.0, 890.0), (150.0, 770.0), (220.0, 720.0), (360.0, 700.0), (370.0, 640.0)],
        body=[(385.0, 0.0), (875.0, 0.0), (875.0, 1625.0), (535.0, 1625.0), (535.0, 1455.0), (365.0, 925.0),
              (330.0, 880.0), (330.0, 720.0), (385.0, 650.0)],
        speakers=((535.0, 1625.0), (535.0, 1455.0)),
        bezel=((365.0, 925.0), (535.0, 1455.0)),
        screen=dict(glass=(480.0, 360.0), middle=278.0, margin=16.0, depth=60.0, bulge=12.0),
        lower=((385.0, 0.0), (385.0, 650.0)),
        panel=dict(top=((0.0, 895.0), (340.0, 930.0)), front=790.0, width=860.0, corner=120.0, back=360.0),
        coin=dict(kind="door", x=(-110.0, 110.0), z=(170.0, 560.0)),
        kick=(0.0, 70.0),
        sticks=dict(p1=(-260.0, 130.0), p2=(130.0, 130.0), shaft=(5.0, 50.0), ball=17.0),
        start=[(-40.0, 215.0), (40.0, 215.0)], button=dict(r=13.0, height=9.0),
        tops=[dict(x=(-301.0, 301.0), y=(560.0, 760.0), z=(1625.0, 1960.0), face="marquee", colour="black", r=5.0)],
    ),
    # A laserdisc game's cabinet of 1983: tall, narrow and black, the marquee leaning out at the top, the score panel's
    # LED readouts under it, the monitor deep in its bezel, a painted control panel with one stick and a button
    # either side of it.
    "laser": dict(
        kind="upright", width=635.0, side=19.0, height=1838.0, depth=762.0,
        outline=[(70.0, 0.0), (762.0, 0.0), (762.0, 1838.0), (230.0, 1838.0), (200.0, 1660.0), (270.0, 1600.0),
                 (160.0, 1000.0), (20.0, 960.0), (0.0, 930.0), (0.0, 790.0), (60.0, 760.0), (70.0, 700.0)],
        body=[(85.0, 0.0), (757.0, 0.0), (757.0, 1823.0), (240.0, 1823.0), (215.0, 1665.0), (300.0, 1615.0),
              (185.0, 1010.0), (150.0, 960.0), (150.0, 770.0), (85.0, 700.0)],
        marquee=((240.0, 1823.0), (215.0, 1665.0)), speakers=((215.0, 1665.0), (300.0, 1615.0)),
        bezel=((185.0, 1010.0), (300.0, 1615.0)),
        screen=dict(glass=(390.0, 292.0), middle=300.0, margin=18.0, depth=60.0, bulge=10.0),
        lower=((85.0, 0.0), (85.0, 700.0)),
        panel=dict(top=((0.0, 930.0), (150.0, 975.0)), front=790.0, width=597.0, corner=30.0, back=160.0),
        coin=dict(kind="door", x=(-110.0, 110.0), z=(250.0, 560.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(0.0, 85.0), shaft=(5.0, 50.0), ball=18.0),
        more_buttons=[(-72.0, 85.0)],
        start=[(-200.0, 70.0), (-160.0, 70.0)], button=dict(r=14.0, height=9.0),
    ),
    # A twin-monitor cabinet of a console arcade system: the game menu and the time left on a small monitor over the
    # main one, both in their own bezels; tall, black and plain, two players' sticks.
    "twin": dict(
        kind="upright", width=650.0, side=19.0, height=1880.0, depth=800.0,
        outline=[(70.0, 0.0), (800.0, 0.0), (800.0, 1880.0), (240.0, 1880.0), (240.0, 1720.0), (285.0, 1440.0),
                 (185.0, 1000.0), (30.0, 975.0), (0.0, 950.0), (0.0, 800.0), (60.0, 780.0)],
        body=[(85.0, 0.0), (795.0, 0.0), (795.0, 1865.0), (255.0, 1865.0), (255.0, 1725.0), (345.0, 1700.0),
              (298.0, 1450.0), (335.0, 1405.0), (195.0, 1005.0), (160.0, 965.0), (160.0, 785.0), (85.0, 770.0)],
        marquee=((255.0, 1865.0), (255.0, 1725.0)),
        bezel=((195.0, 1005.0), (335.0, 1405.0)),
        screen=dict(glass=(390.0, 292.0), middle=212.0, margin=16.0, depth=50.0, bulge=10.0),
        screen2=dict(span=((298.0, 1450.0), (345.0, 1700.0)), glass=(300.0, 225.0), middle=127.0, margin=12.0,
                     depth=35.0, bulge=8.0),
        spans=[(((298.0, 1450.0), (345.0, 1700.0)), "black")],
        lower=((85.0, 0.0), (85.0, 770.0)),
        panel=dict(top=((0.0, 950.0), (185.0, 985.0)), front=800.0, width=612.0, corner=6.0, back=180.0),
        coin=dict(kind="door", x=(-100.0, 100.0), z=(260.0, 600.0)),
        kick=(0.0, 60.0),
        sticks=dict(p1=(-225.0, 95.0), p2=(75.0, 95.0), shaft=(5.0, 50.0), ball=17.0),
        start=[(-30.0, 150.0), (30.0, 150.0)], button=dict(r=12.0, height=8.0),
    ),
    # Taito's Vewlix: a widescreen LCD's cabinet, black, a white slash down each side with a red stripe in it, the
    # lit red header leaning back over the screen, the speakers in the screen's surround, the control panel's ends
    # white.
    "vewlix": dict(
        kind="candy", width=790.0, height=1630.0, depth=800.0, round=8.0, yaw=-30.0,
        body=[(230.0, 0.0), (800.0, 0.0), (800.0, 700.0), (660.0, 1630.0), (452.0, 1630.0), (422.0, 1462.0),
              (330.0, 850.0), (230.0, 800.0)],
        marquee=((452.0, 1630.0), (422.0, 1462.0)),
        bezel=((330.0, 850.0), (422.0, 1462.0)),
        screen=dict(glass=(700.0, 394.0), middle=300.0, margin=20.0, depth=30.0, bulge=0.0),
        lower=((230.0, 0.0), (230.0, 700.0)),
        panel=dict(top=((0.0, 800.0), (320.0, 832.0)), front=700.0, width=790.0, corner=90.0, back=310.0,
                   strip=True),
        coin=dict(kind="plate", at=(330.0, 250.0), plate=(44.0, 60.0), slot=(4.0, 26.0)),
        kick=(0.0, 50.0),
        sticks=dict(p1=(-265.0, 140.0), p2=(105.0, 140.0), shaft=(5.0, 46.0), ball=18.0),
        start=[(-40.0, 230.0), (40.0, 230.0)], button=dict(r=13.0, height=8.0),
    ),
    # A sit-down driving cabinet of the mid-1990s: the monitor's housing (its sides curved fins), a long canopy over it
    # carrying the marquee, the dash with the wheel, START, the view buttons and the shifter, the pedals; the seat on
    # its base behind, the player facing the screen from the viewer's side.
    "daytona": dict(
        kind="driver", width=840.0, height=1720.0, depth=1660.0, round=14.0, yaw=-34.0, pitch=16.0,
        body=[(0.0, 0.0), (560.0, 0.0), (560.0, 1500.0), (150.0, 1500.0), (150.0, 1440.0), (40.0, 860.0),
              (0.0, 820.0)],
        bezel=((40.0, 860.0), (150.0, 1440.0)),
        screen=dict(glass=(560.0, 420.0), middle=300.0, margin=14.0, depth=60.0, bulge=13.0),
        lower=((0.0, 0.0), (0.0, 820.0)),
        panel=dict(top=((-260.0, 770.0), (0.0, 800.0)), front=690.0, width=700.0, corner=60.0, back=260.0),
        coin=dict(kind="door", x=(300.0, 400.0), z=(240.0, 520.0)),
        kick=(0.0, 60.0),
        tops=[dict(x=(-430.0, 430.0), y=(-140.0, 600.0), z=(1500.0, 1720.0), face="marquee", colour="black",
                   r=12.0)],
        wheel=dict(hub=(0.0, -310.0, 830.0), tilt=32.0, r=170.0, tube=16.0, spokes=(90.0, 210.0, 330.0),
                   hub_r=42.0),
        shifter=dict(at=(270.0, 150.0), length=170.0),
        start=[(-270.0, 140.0)], views=[(-215.0, 150.0), (-175.0, 150.0), (-135.0, 150.0), (-95.0, 150.0)],
        button=dict(r=13.0, height=8.0),
        base=dict(y=(-1060.0, 0.0), z=(0.0, 150.0), width=800.0),
        seat=dict(base=(-940.0, -500.0, 150.0, 420.0), cushion=(-850.0, -470.0, 420.0, 530.0),
                  back=(-880.0, 450.0, 1120.0, 140.0, 12.0), width=560.0, bolsters=False),
        pedals=[(-90.0, -430.0), (90.0, -430.0)],
    ),
    # A sit-down kart racer of the 2000s: a tall housing with speaker rings beside the screen, the marquee standing on
    # its top, a bucket seat with high bolsters on a checkered base.
    "kart": dict(
        kind="driver", width=780.0, height=1960.0, depth=1600.0, round=18.0, yaw=-34.0, pitch=16.0,
        body=[(0.0, 0.0), (600.0, 0.0), (600.0, 1530.0), (170.0, 1530.0), (170.0, 1460.0), (60.0, 860.0),
              (0.0, 820.0)],
        bezel=((60.0, 860.0), (170.0, 1460.0)),
        screen=dict(glass=(560.0, 420.0), middle=305.0, margin=14.0, depth=60.0, bulge=13.0),
        lower=((0.0, 0.0), (0.0, 820.0)),
        panel=dict(top=((-250.0, 780.0), (0.0, 810.0)), front=690.0, width=680.0, round=90.0, back=250.0),
        coin=dict(kind="door", x=(270.0, 370.0), z=(240.0, 520.0)),
        kick=(0.0, 60.0),
        tops=[dict(x=(-390.0, 390.0), y=(180.0, 300.0), z=(1530.0, 1960.0), face="marquee", colour="red", r=14.0)],
        wheel=dict(hub=(0.0, -300.0, 840.0), tilt=30.0, r=150.0, tube=18.0, spokes=(30.0, 150.0, 270.0),
                   hub_r=48.0),
        start=[(240.0, 140.0)], views=[(-240.0, 140.0)],
        button=dict(r=15.0, height=9.0),
        base=dict(y=(-1000.0, 0.0), z=(0.0, 140.0), width=760.0),
        seat=dict(base=(-900.0, -470.0, 140.0, 400.0), cushion=(-830.0, -460.0, 400.0, 500.0),
                  back=(-860.0, 430.0, 1180.0, 130.0, 14.0), width=560.0, bolsters=True),
        pedals=[(-90.0, -420.0), (90.0, -420.0)],
    ),
}

# ---- Cards -----------------------------------------------------------------------------------------------------------

BLUE = "#1F4FB0"
YELLOW = "#F6D23A"

CARDS = {
    "cps1": dict(cabinet="bigblue", game="stormfst", screen="4:3", marquee="CP SYSTEM", maker="CAPCOM",
                 colours=dict(case="#141418", side="#2E5EB4", lower="#2E5EB4", moulding="#E8E8E4",
                              panel_edge="#141416", bezel="#121318", speakers="#141418", metal="#2C2D31",
                              kick="#1C1D22", marquee="#1A2E8C", marquee_glow="#80B8FF", marquee_text=YELLOW,
                              marquee_edge="#C0241C"),
                 buttons=("#F2D23A", "#E83A30", "#3A78E8"), balls=("#E83A30", "#E83A30"),
                 panel_art=dict(ground="#9EA0A6", speckle=True, cards=True, rings=True),
                 bezel_art=dict(lines=("#F2D23A", "#E83A30", "#3A78E8"), logo=True),
                 side=[("fill", "#2E5EB4")]),
    "cps2": dict(cabinet="bigblue_q", game="conknuck", screen="4:3", marquee="CP SYSTEM II", maker="CAPCOM",
                 colours=dict(case="#141418", side="#2D50A8", lower="#2D50A8", moulding="#16161A",
                              panel_edge="#16161A", bezel="#0E0E11", speakers="#2D50A8", metal="#1A1A1E",
                              kick="#1C1D22", marquee="#141C52", marquee_glow="#5AC8FF", marquee_text="#FFFFFF",
                              marquee_edge="#2D50A8", strip="#2D50A8"),
                 buttons=("#F2F2EE", "#F2F2EE", "#F2F2EE"), balls=("#16161A", "#16161A"),
                 panel_art=dict(ground="#3A3B40", diamond=True, rings=True),
                 bezel_art=dict(lines=(), logo=False),
                 strip_art=dict(badge="CAPCOM", fill=YELLOW, edge="#16161A", ground="#2D50A8"),
                 side=[("fill", "#2D50A8")]),
    "cps": dict(cabinet="bgs25", game="crimkuna", screen="4:3", marquee="CP SYSTEM", maker="CAPCOM",
                colours=dict(case="#EEEEE8", side="#EEEEE8", lower=BLUE, panel_edge="#E4E4DC", bezel="#EEEEE8",
                             speakers="#18181B", metal="#B4B6BA", kick="#D8D8D0", top="#18181B", strip="#E8DFC0"),
                buttons=("#E83A30", "#F6D23A", "#3A78E8"), balls=("#3A78E8", "#E83A30"),
                panel_art=dict(ground="#EEEEE8", band=BLUE, pads="#A9C8F0", rings=False),
                bezel_art=dict(surround="#121216", lines=(), logo=False),
                strip_art=dict(text="CP SYSTEM", fill="#C8A020", ground="#E8DFC0"),
                grilles=dict(kind="round"),
                front_art=dict(doors="#1A47A0"),
                side=[("fill", "#EEEEE8"),
                      ("poly", [(560.0, 0.0), (800.0, 0.0), (800.0, 520.0), (560.0, 0.0)], BLUE),
                      ("poly", [(180.0, 300.0), (330.0, 0.0), (520.0, 0.0), (800.0, 610.0), (800.0, 1000.0),
                                (180.0, 700.0)], BLUE),
                      ("text", "CAPCOM", "ariblk.ttf", 92.0, (420.0, 1140.0), 70.0, YELLOW, (BLUE, 7.0))]),
    "cps3": dict(cabinet="impress", game="halcystk", screen="4:3", marquee="CP SYSTEM III", maker="CAPCOM",
                 colours=dict(case="#F0EEF0", side="#F0EEF0", lower="#F0EEF0", panel_edge="#E8E6EA",
                              bezel="#F0EEF0", speakers="#141416", metal="#B4B6BA", kick="#D8D6DA", top="#141416",
                              strip="#E890B8"),
                 buttons=("#E85A9A", "#F4F4F4", "#E85A9A"), balls=("#E85A9A", "#3A6AD8"),
                 panel_art=dict(ground="#F0EEF0", band="#2F5CC8", band_edge="#E85A9A", rings=False),
                 bezel_art=dict(surround="#121216", lines=(), logo=False),
                 strip_art=dict(text="CP SYSTEM III", fill="#FFFFFF", ground="#E85A9A"),
                 grilles=dict(kind="slots"),
                 front_art=dict(doors="#D0CED4"),
                 side=[("fill", "#F0EEF0"),
                       ("line", [(250.0, 760.0), (870.0, 1390.0)], "#7A4CC0", 14.0),
                       ("line", [(250.0, 720.0), (870.0, 1350.0)], "#E85A9A", 6.0)]),
    "model3": dict(cabinet="blastcity", game="stllotus", screen="4:3", marquee="MODEL 3", maker="SEGA",
                   colours=dict(case="#F2F2EE", side="#F2F2EE", lower="#F2F2EE", panel_edge="#ECECE6",
                                bezel="#F2F2EE", metal="#2A2A2E", kick="#B8B8B2", marquee="#1A0C24",
                                marquee_glow="#FF6A3A", marquee_text="#FFFFFF", marquee_edge="#C02060"),
                   buttons=("#3A9AE8", "#3A9AE8", "#3A9AE8"), balls=("#E83A30", "#3A9AE8"), n_buttons=3,
                   panel_art=dict(sunset=("#3A1A6A", "#E8406A", "#F8A030", "#3A1A6A"), rings=True),
                   bezel_art=dict(surround="#121216", fins=True, lines=(), logo=False),
                   front_art=dict(doors="#DADAD4"),
                   side=[("fill", "#F2F2EE"),
                         ("swoosh", [(330.0, 560.0), (520.0, 1160.0), (760.0, 1430.0)], 150.0,
                          ("#3A1A6A", "#E8406A", "#F8A030")),
                         ("swoosh", [(470.0, 520.0), (610.0, 930.0), (800.0, 1160.0)], 46.0,
                          ("#3A6AD8", "#9A5AE8"))]),
    "stv": dict(cabinet="versuscity", game="bubbarr", screen="4:3", marquee="ST-V", maker="SEGA",
                colours=dict(case="#E8E6E2", side="#E8E6E2", lower="#E8E6E2", panel_edge="#E2E0DC",
                             bezel="#E8E6E2", speakers="#E8642A", metal="#9A9CA0", kick="#B8B6B2", top="#E8642A",
                             marquee="#2A1450", marquee_glow="#C040E0", marquee_text="#FFE040",
                             marquee_edge="#B02070"),
                buttons=("#40C060", "#E84A8A", "#3A9AE8"), balls=("#30B050", "#30B050"),
                panel_art=dict(ground="#4A1C78", stripes=("#E82A6A", "#F8C030"), rings=True),
                bezel_art=dict(surround="#121216", lines=(), logo=False),
                roof_art=dict(text="WINNER", fill="#C81E1E"),
                front_art=dict(doors="#D8D6D2"),
                side=[("fill", "#E8E6E2"),
                      ("flame", (450.0, 140.0), (610.0, 1250.0), 150.0, ("#3A1A8A", "#B03ADA", "#F06A9A", "#F8D040")),
                      ("flame", (1050.0, 140.0), (890.0, 1250.0), 150.0, ("#3A1A8A", "#B03ADA", "#F06A9A",
                                                                         "#F8D040"))]),
    "atomiswave": dict(cabinet="aw_sd", game="hoophero", screen="4:3", marquee="ATOMISWAVE", maker="SAMMY",
                       colours=dict(case="#F2F2F0", side="#F2F2F0", lower="#F2F2F0", panel_edge="#EAEAE8",
                                    bezel="#F2F2F0", metal="#9A9CA0", kick="#C0C0BC", marquee="#0E3A12",
                                    marquee_glow="#9AF040", marquee_text="#FFFFFF", marquee_edge="#1A8A2A"),
                       buttons=("#30C040", "#2A2A2E", "#30C040"), balls=("#30C040", "#E8402A"),
                       panel_art=dict(ground="#F2F2F0", wave=("#1A9A2A", "#B8E030", "#F0A020"), rings=True),
                       bezel_art=dict(surround="#121216", lines=(), logo=False),
                       front_art=dict(doors="#DCDCDA"),
                       side=[("fill", "#F2F2F0"),
                             ("band", [(780.0, 1560.0), (560.0, 900.0), (560.0, 0.0)], 150.0,
                              ("#B8E030", "#1A9A2A", "#101010", "#101010")),
                             ("flames", (485.0, 0.0), (635.0, 420.0)),
                             ("text", "ATOMISWAVE", "ariblk.ttf", 76.0, (670.0, 1180.0), 71.6, "#FFFFFF",
                              ("#101010", 4.0))]),
    # The generic systems: a dedicated cabinet each, its made-up game's side art (artifacts/console-paintings).
    "arcade": dict(cabinet="classic", game="musemyhm", screen="4:3", marquee="ARCADE", maker="",
                   colours=dict(case="#141416", side="#B81E1A", lower="#141416", moulding="#141416",
                                panel_edge="#141416", bezel="#0E0E10", speakers="#141416", metal="#2A2A2E",
                                kick="#1A1A1E", marquee="#1A1030", marquee_glow="#FFB040", marquee_text="#FFD040",
                                marquee_edge="#B81E1A"),
                   buttons=("#E83A30", "#E83A30", "#E83A30"), balls=("#E83A30", "#E83A30"), n_buttons=1,
                   boot=dict(big="ARCWAVE", small="©1982 ARCWAVE"),
                   panel_art=dict(ground="#1C1C22", frame="#FFD040", rings=True),
                   bezel_art=dict(lines=("#FFD040", "#B81E1A"), logo=True),
                   side=[("fill", "painting:side_musemyhm"),
                         ("art", "side_musemyhm", (130.0, 400.0, 775.0, 1580.0), 0.0, "contain")]),
    "mame": dict(cabinet="classic", game="hivehstl", screen="3:4", marquee="MAME", maker="",
                 colours=dict(case="#141416", side="#0A0A0A", lower="#141416", moulding="#F2C230",
                              panel_edge="#141416", bezel="#0E0E10", speakers="#141416", metal="#2A2A2E",
                              kick="#1A1A1E", marquee="#2A1A04", marquee_glow="#FFC020", marquee_text="#FFD040",
                              marquee_edge="#6A3A00"),
                 buttons=("#F2C230", "#F2C230", "#F2C230"), balls=("#F2C230", "#F2C230"), n_buttons=1,
                 boot=dict(big="MAME", small="MULTIPLE ARCADE MACHINE EMULATOR"),
                 panel_art=dict(ground="#141416", frame="#F2C230", rings=True),
                 bezel_art=dict(lines=("#F2C230",), logo=False),
                 side=[("fill", "painting:side_hivehstl"),
                       ("art", "side_hivehstl", (130.0, 400.0, 775.0, 1580.0), 0.0, "contain")]),
    "fbneo": dict(cabinet="bigred", game="sandlanc", screen="4:3", marquee="FINALBURN NEO", maker="",
                  colours=dict(case="#141416", side="#C41A1A", lower="#C41A1A", moulding="#141416",
                               panel_edge="#141416", bezel="#0E0E10", speakers="#C41A1A", metal="#1A1A1E",
                               kick="#1A1A1E", marquee="#101014", marquee_glow="#FF4040", marquee_text="#FFFFFF",
                               marquee_edge="#C41A1A"),
                  buttons=("#E8302A", "#F6D23A", "#30B050", "#3A78E8"), balls=("#E8302A", "#E8302A"), n_buttons=4,
                  marquee_art=dict(kind="slots", games=("sandlanc", "crimkuna", "nebswarm", "dustygul")),
                  boot=dict(big="FINALBURN NEO", small="4 GAMES IN ONE"),
                  panel_art=dict(ground="#1E1E22", rings=True),
                  bezel_art=dict(lines=("#C41A1A",), logo=False),
                  side=[("fill", "#C41A1A"),
                        ("poly", [(380.0, 0.0), (880.0, 0.0), (880.0, 300.0), (380.0, 560.0)], "#101014"),
                        ("line", [(380.0, 600.0), (880.0, 340.0)], "#F6D23A", 12.0),
                        ("text", "FINALBURN NEO", "ariblk.ttf", 54.0, (700.0, 1230.0), 64.0, "#FFFFFF",
                         ("#101014", 5.0))]),
    "daphne": dict(cabinet="laser", screen="4:3", marquee="LASERDISC", maker="",
                   laserdisc=dict(title="CINDERSPIRE", year="1983", publisher="ARCWAVE", attract="daphne_attract",
                                  frames=("daphne_frame1", "daphne_frame2")),
                   colours=dict(case="#0E0E10", side="#0A0A0A", lower="#0E0E10", moulding="#0E0E10",
                                panel_edge="#0E0E10", bezel="#0A0A0C", speakers="#0A0A0C", metal="#1A1A1E",
                                kick="#141416", marquee="#1A0E20", marquee_glow="#FF8A20", marquee_text="#FFD040",
                                marquee_edge="#7A1A0A"),
                   buttons=("#E02A20", "#E02A20", "#E02A20"), balls=("#E02A20", "#E02A20"), n_buttons=1,
                   start="#F2F2EE",
                   marquee_art=dict(kind="painting", painting="daphne_attract", font="ALGER.TTF"),
                   score_art=True,
                   panel_art=dict(painting="daphne_frame1", rings=False),
                   bezel_art=dict(lines=("#C8A040",), logo=True),
                   side=[("fill", "#0A0A0A"), ("art", "daphne_side", (150.0, 300.0, 750.0, 1680.0), 0.0, "contain")]),
    "consolearcade": dict(cabinet="twin", screen="4:3", twin=True, marquee="CONSOLE ARCADE", maker="",
                          console=dict(system="megadrive", stem="Springheel Sam (Europe)",
                                       menu=("Springheel Sam", "Stormfist", "Crimson Kunai", "Puck Rush",
                                             "Ghoulish Gus", "Deep Fathom", "Gravel Kings", "Kaleidrop")),
                          colours=dict(case="#101012", side="#101012", lower="#101012", moulding="#E8E8E4",
                                       panel_edge="#101012", bezel="#0A0A0C", metal="#1A1A1E", kick="#141416",
                                       marquee="#141418", marquee_glow="#FF3A3A", marquee_text="#F2F2EE",
                                       marquee_edge="#C81E1E"),
                          buttons=("#F6D23A", "#F6D23A", "#F6D23A"), balls=("#141416", "#141416"), n_buttons=3,
                          boot=dict(big="CONSOLE ARCADE", small="SELECT A GAME"),
                          panel_art=dict(ground="#B81E1E", lines="#141416",
                                         strip=("#7A64C8", "#9A9AA0", "#3A9AE0"), rings=False),
                          bezel_art=dict(lines=(), logo=False),
                          side=[("fill", "#101012"),
                                ("rrect", (150.0, 420.0, 760.0, 1780.0), 40.0, "#A8A8AC"),
                                ("stripes", (170.0, 460.0, 740.0, 1740.0), 13, "#C81E1E", 4),
                                ("text", "Console Arcade", "BRUSHSCI.TTF", 120.0, (455.0, 1060.0), 64.0,
                                 "#F2F2EE", ("#101012", 5.0))]),
    "pcarcade": dict(cabinet="vewlix", game="voltcrwn", screen="16:9", marquee="PC ARCADE", maker="",
                     colours=dict(case="#121214", side="#121214", lower="#121214", panel_edge="#EEEAE0",
                                  bezel="#0C0C0E", metal="#2A2A2E", kick="#1A1A1E", marquee="#8A0C18",
                                  marquee_glow="#FF4A5A", marquee_text="#FFFFFF", marquee_edge="#3A0006"),
                     buttons=("#F2F2EE", "#F2F2EE", "#F2F2EE"), balls=("#F2F2EE", "#F2F2EE"),
                     boot=dict(kind="bios", lines=("PC ARCADE SYSTEM BIOS", "", "CPU : 2.4 GHz  OK",
                                                   "Memory Test : 2097152K OK", "Graphics : OK", "",
                                                   "Detecting drives ... OK", "Loading game ...")),
                     panel_art=dict(ground="#9A101C", border="#121214", lit_strip="#F4F2EC", rings=True),
                     bezel_art=dict(surround="#0C0C0E", speakers=True),
                     strip_art=dict(text="", fill="#FFFFFF", ground="#121214"),
                     front_art=dict(doors="#2A2A2E"),
                     side=[("fill", "#121214"),
                           ("band", [(540.0, 1610.0), (600.0, 1000.0), (770.0, 30.0)], 170.0, ("#EEEAE0", "#EEEAE0")),
                           ("band", [(540.0, 1610.0), (600.0, 1000.0), (770.0, 30.0)], 54.0,
                            ("#C81E3A", "#C81E3A"))]),
    "model2": dict(cabinet="daytona", game="turbotar", screen="4:3", marquee="MODEL 2", maker="SEGA",
                   colours=dict(case="#141416", side="#F0601A", lower="#141416", panel_edge="#1A1A1E",
                                bezel="#0C0C0E", metal="#2A2A2E", kick="#1A1A1E", marquee="#1A1030",
                                marquee_glow="#FF5A9A", marquee_text="#FFE040", marquee_edge="#2040C0",
                                seat="#E8501A", seat2="#222226", base="#18181C", dash="#1E1E22"),
                   buttons=("#E83A30", "#3A78E8", "#F6D23A", "#30B050"), balls=("#141416", "#141416"),
                   boot=dict(big="SEGA", small="MODEL 2"),
                   seat_art=dict(ground="#E8501A", number="1", logo=True),
                   panel_art=dict(ground="#1E1E22", legends=("VIEW CHANGE", "START")),
                   bezel_art=dict(surround="#0C0C0E", lines=(), logo=False),
                   front_art=dict(doors="#2A2A2E"),
                   side=[("fill", "#141416"),
                         ("poly", [(0.0, 760.0), (0.0, 1500.0), (560.0, 1500.0), (560.0, 1180.0), (260.0, 860.0)],
                          "#F0601A"),
                         ("line", [(0.0, 730.0), (260.0, 830.0), (560.0, 1150.0)], "#F2F2EE", 10.0)]),
    "triforce": dict(cabinet="kart", game="redlnriv", screen="4:3", marquee="TRIFORCE", maker="",
                     colours=dict(case="#1A3A9A", side="#1A3A9A", lower="#141416", panel_edge="#141416",
                                  bezel="#2A5AD0", metal="#2A2A2E", kick="#141416", marquee="#0E2A80",
                                  marquee_glow="#FFD040", marquee_text="#FFFFFF", marquee_edge="#D8201E",
                                  seat="#D8201E", seat2="#1A3A9A", base="#1A3A9A", dash="#141416", top="#D8201E"),
                     buttons=("#D8201E", "#D8201E", "#D8201E"), balls=("#141416", "#141416"),
                     boot=dict(big="TRIFORCE", small="NAMCO  SEGA  NINTENDO"),
                     seat_art=dict(ground="#D8201E", number="", logo=True),
                     panel_art=dict(ground="#141416", legends=("ITEM", "START")),
                     bezel_art=dict(surround="#2A5AD0", rings="#D8201E"),
                     front_art=dict(doors="#2A2A2E"),
                     side=[("fill", "#1A3A9A"),
                           ("swoosh", [(40.0, 700.0), (300.0, 1050.0), (580.0, 1450.0)], 180.0,
                            ("#D8201E", "#F04030", "#D8201E")),
                           ("checks", (0.0, 0.0, 600.0, 180.0), 45.0, "#F2F2EE", "#1A3A9A")]),
}


# ---- Shared measurements ---------------------------------------------------------------------------------------------

def span_length(span):
    (y0, z0), (y1, z1) = span
    return ((y1 - y0) ** 2 + (z1 - z0) ** 2) ** 0.5


def inner_width(cab):
    """The body's width: between the side panels of an upright, the whole width of a candy cabinet."""
    return cab["width"] - 2 * cab.get("side", 0.0)


def top_with(cab, face):
    return next((t for t in cab.get("tops", ()) if t.get("face") == face), None)


def region_size(cab, name):
    """The size (width, height) in millimetres a print region is drawn at: the face it is printed on."""
    if name in ("marquee", "speakers") and name in cab:
        return inner_width(cab), span_length(cab[name])
    if name == "speakers" and top_with(cab, "speakers"):
        t = top_with(cab, "speakers")
        return cab["width"], t["z"][1] - t["z"][0]
    if name == "pop" and "seat" in cab:                # a driving cabinet's seat back
        y, z0, z1, _, tilt = cab["seat"]["back"]
        return cab["seat"]["width"], (z1 - z0) / math.cos(math.radians(tilt))
    if name in ("marquee", "pop") and top_with(cab, name):
        t = top_with(cab, name)
        return t["x"][1] - t["x"][0], t["z"][1] - t["z"][0]
    if name == "bezel":
        return inner_width(cab), span_length(cab["bezel"])
    if name == "panel":
        return cab["panel"]["width"], cab["panel"]["back"]
    if name == "front":
        return inner_width(cab), cab["lower"][1][1]
    if name == "strip":
        p = cab["panel"]
        return p["width"], p["top"][0][1] - p["front"]
    return None


def side_outline(cab):
    return cab["outline"] if cab["kind"] == "upright" else cab["body"]


def side_bounds(cab):
    """The side art's bounds: (lo_y, hi_y, hi_z) of the side outline."""
    ys = [p[0] for p in side_outline(cab)]
    return min(ys), max(ys), max(p[1] for p in side_outline(cab))
