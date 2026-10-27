"""The device cards' measurements (devices.py builds them, devices_print.py draws their screens and printing): for
systems with no hardware of their own, a device that stands for them. Plain Python: Blender's Python imports it too.

- `tic80`: TIC-80's mascot, the little computer of its icon, made solid in its pixels (TIC80, a pixel a cell);
- `wasm4`: WASM-4's emblem, a notched square with a d-pad and two buttons, made a handheld, its screen on its back;
- `lowresnx`: the handheld of LowRes NX's icon, its screen sliding down over its rubber keyboard;
- `vircon32`: Vircon32's console and gamepad, as its own renders show them;
- `fpinball`: a pinball machine; `vpinball`: a corner of a playfield and its ball;
- `zmachine`: a 1980s terminal and a brass lantern, for the Z-machine's text adventures;
- `steam`: a Steam Deck.
Millimetres: x across (left to right), y back (away from the viewer), z up. Each card has one image,
`<card>_media.png` (MEDIA_SIZE), its regions (x, y, width, height in pixels) in REGIONS; a card of pictures
(JPEG) has `<card>_media.jpg` instead, as the all-games card's art is. OpenBOR's drum (props.py) is drawn with them:
`openbor_media.jpg`, its painting at 1024 wide.
"""

FPS = 30
MEDIA_SIZE = 1024
JPEG = ("fpinball", "steam", "openbor")


def media_file(card):
    return f"{card}_media.{'jpg' if card in JPEG else 'png'}"

REGIONS = {
    "tic80": dict(eyes=(0, 0, 480, 267), blink=(512, 0, 480, 267), game1=(0, 280, 480, 267),
                  game2=(512, 280, 480, 267), label=(0, 560, 360, 300)),
    "wasm4": dict(title=(0, 0, 320, 320), game1=(336, 0, 320, 320), game2=(672, 0, 320, 320)),
    "lowresnx": dict(ready=(0, 0, 480, 384), run=(512, 0, 480, 384), game1=(0, 400, 480, 384),
                     game2=(512, 400, 480, 384)),
    "vircon32": dict(label=(0, 0, 750, 300), card=(0, 320, 200, 240), top=(220, 320, 600, 200),
                     front=(0, 580, 1000, 120)),
    "fpinball": dict(playfield=(0, 0, 400, 800), backglass=(410, 0, 600, 600), apron=(410, 610, 600, 120)),
    "vpinball": dict(ball=(0, 0, 512, 256), playfield=(0, 270, 512, 430), apron=(0, 710, 512, 90)),
    "zmachine": dict(dark=(0, 0, 480, 360), typed=(512, 0, 480, 360), lit=(0, 380, 480, 360),
                     room=(512, 380, 480, 360)),
    "steam": dict(library=(0, 0, 480, 300), game1=(512, 0, 480, 300), game2=(0, 320, 480, 300),
                  boot=(512, 320, 480, 300)),
}

# ---- TIC-80 ----------------------------------------------------------------------------------------------------------

# The mascot, a pixel a character, its top row first: B its blue body, N its navy bands, F its face (the screen), W its
# white smile, D the dark side, S the stub on its right.
TIC80 = [
    ".NNNNNNNNNNN...",
    ".BBBBBBBBBBBD..",
    ".BFFFFFFFFFBD..",
    ".BFFFFFFFFFBD..",
    ".BFFFFFFFFFBDS.",
    ".BFFFFFFFFFBDS.",
    ".BFFFFFFFFFBD..",
    ".BBBBBBBBBBBD..",
    ".BBWBBBBBWBBD..",
    ".BBBWWWWWBBBD..",
    ".BBBBBBBBBBBD..",
    ".NNNNNNNNNNND..",
    "..NNN...NNN....",
]
TIC80_PIXEL = 12.0                # a pixel's size
TIC80_DEPTH = 9                   # in pixels
TIC80_COLOURS = dict(B="#41A6F6", N="#29366F", D="#1A1C2C", S="#1A1C2C", W="#F4F4F4", cart="#333C57",
                     edge="#566C86", contacts="#FFCD75")
SWEETIE16 = ["#1A1C2C", "#5D275D", "#B13E53", "#EF7D57", "#FFCD75", "#A7F070", "#38B764", "#257179", "#29366F",
             "#3B5DC9", "#41A6F6", "#73EFF7", "#F4F4F4", "#94B0C2", "#566C86", "#333C57"]

# ---- WASM-4 ----------------------------------------------------------------------------------------------------------

WASM4 = dict(size=100.0, depth=20.0, notch=11.5, round=3.0,
             dpad=dict(at=(-22.0, 36.0), arm=16.0, width=10.0), buttons=[(31.0, 44.0), (16.0, 26.0)], button_r=8.5,
             screen=dict(at=(0.0, 52.0), size=70.0, bezel=82.0))
WASM4_COLOURS = dict(body="#638F34", controls="#D2E6BC", bezel="#1A2412")
WASM4_PALETTE = ["#E0F8CF", "#86C06C", "#306850", "#071821"]

# ---- LowRes NX -------------------------------------------------------------------------------------------------------

LOWRES = dict(width=176.0, height=70.0, depth=24.0, grip=35.0,
              column=(72.0, 64.0),                    # the keyboard's column: its width, its height up the body
              panel=dict(width=72.0, height=58.0, depth=8.0, z=66.0, slide=-60.0),   # the screen's panel, at rest up
              screen=(54.0, 43.2), keys=(6, 3), dpad=(-62.0, 38.0), buttons=[(54.0, 44.0), (66.0, 32.0)],
              teal=(60.0, 54.0))
LOWRES_COLOURS = dict(body="#8A8A8A", dark="#1E1E1E", key="#C6C6C6", teal="#1A8C8C", button="#2A2A2A")
LOWRES_PALETTE = ["#0F0F0F", "#07B0B0", "#4CFFFF", "#F4F4F4", "#FF8400", "#FF5900", "#5A3A8A", "#3A8A3A"]

# ---- Vircon32 --------------------------------------------------------------------------------------------------------

VIRCON = dict(base=(220.0, 150.0, 46.0), top=(150.0, 70.0, 10.0), cart=(100.0, 18.0, 60.0), slot_y=24.0,
              pad=dict(at=(40.0, -150.0), size=(150.0, 64.0, 18.0)), card=(24.0, 2.0, 32.0))
VIRCON_COLOURS = dict(body="#E2E4D6", inset="#F2F4E4", dark="#5A6264", mint="#85C8A8", red="#D83A2A", led="#5AE07A",
                      cart="#3A3E42")

# ---- Pinball ---------------------------------------------------------------------------------------------------------

PINBALL = dict(width=560.0, length=1315.0, front=870.0, back=1000.0, side_depth=300.0, legs=60.0,
               backbox=dict(width=620.0, depth=240.0, height=720.0), playfield=(533.0, 1093.0), ball=13.5,
               bumpers=[(-100.0, 760.0), (90.0, 790.0), (-5.0, 900.0)], bumper_r=38.0,
               flippers=[(-95.0, 140.0), (95.0, 140.0)], flipper=(75.0, 12.0),
               lane=(240.0, 0.0, 1000.0))      # the shooter lane: its x, where it starts and ends up the playfield
PINBALL_COLOURS = dict(cabinet="#1A1A20", trim="#C8CCD2", bumper="#F2F2EE", cap="#3ADA6A", lit="#C8FFD0",
                       rubber="#D82A2A", ball="#D8DCE2")
VPIN = dict(slab=(220.0, 180.0, 16.0), ball=20.0, bumper=((0.0, 70.0), 34.0), flippers=[(-62.0, -42.0),
                                                                                          (62.0, -42.0)],
            flipper=(66.0, 13.0), sling=[(-96.0, -10.0), (-96.0, 40.0), (-70.0, -28.0)])
VPIN_COLOURS = dict(wood="#3A2A1C", bumper="#F2F2EE", cap="#E8302A", lit="#FFD0A0", rubber="#D82A2A",
                    post="#C8CCD2")

# ---- The terminal ----------------------------------------------------------------------------------------------------

TERMINAL = dict(base=(460.0, 330.0, 80.0), housing=(410.0, 300.0, 300.0), screen=(250.0, 188.0), keys=(14, 4),
                lantern=dict(at=(330.0, -40.0), r=55.0, height=210.0))
TERMINAL_COLOURS = dict(case="#E4DCC4", bezel="#3A3630", keys="#3E3A36", keytop="#5A5650", brass="#B8862A",
                        dark_glass="#3A3A30", lit_glass="#FFE08A", flame="#FFFFFF")

# ---- Steam Deck ------------------------------------------------------------------------------------------------------

DECK = dict(size=(298.0, 117.0), depth=20.0, round=26.0, screen=(150.7, 94.2), bezel=(168.0, 104.0),
            sticks=[(-104.0, 26.0), (104.0, 26.0)], pads=[(-104.0, -24.0), (104.0, -24.0)], pad=32.5,
            dpad=(-128.0, 30.0), abxy=(128.0, 30.0), steam=(-104.0, -48.0), dots=(104.0, -48.0))
DECK_COLOURS = dict(body="#2A2A2E", grip="#232326", stick="#3A3A3E", cap="#1C1C1E", button="#1C1C1E",
                    legend="#C8C8CC")
