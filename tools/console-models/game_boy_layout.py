"""The Game Boy's and Game Boy Color's measurements, shared by game_boy_print.py (which draws their printing and their
screens), game_boy_video.py (which draws their cards' videos) and game_boy.py (which builds them). Plain Python:
Blender's Python imports it too.

Two handhelds, standing up and facing the viewer in handheld.py's frame: millimetres, x from the middle (left to
right), z up from the bottom edge, y back from the face (0) to the shell's back (DEPTH).

- `gb`: the original Game Boy, DMG-01 (1989), in its warm grey: 90 x 148 x 32 mm (Nintendo's size; the shell is 30 deep,
  the label panel and the battery cover stand off its back). Measured from straight photographs of its face, back and
  ends on Wikimedia Commons ("Nintendo Game Boy DMG-01-0242" to "-0247", the face at 18.2 pixels a millimetre) and
  Evan-Amos's "Game-Boy-Original" for the lens's printing: the lens set into the face with its big bottom right
  corner, the window onto the LCD (47 x 42.3 mm, 160 x 144 pixels), DOT MATRIX WITH STEREO SOUND between magenta and navy
  stripes, the BATTERY light; Nintendo GAME BOY; the black D-pad, the magenta B and A, the grey rubber SELECT and START
  slanting, the six speaker slots, PHONES; the power switch on the top's left with OFF-ON on the strip above the face;
  the volume wheel and EXT. CONNECTOR in the right end, the contrast wheel and DC 6V in the left; on the back the
  cartridge's open bay at the top, the label panel and its screws, the ribbed band and the battery cover.
- `gbc`: a Game Boy Color, CGB-001 (1998), in Dandelion: 78 x 133.5 x 27.4 mm (Nintendo's). Measured from a straight
  photograph of a yellow one ("Game-Boy-Color-Yellow", 15.2 pixels a millimetre) and a flatbed scan of a green one: the
  black lens with its bowed bottom edge, the window onto the TFT (44.6 x 38.1 mm: its pixels are a little wider than they
  are tall), the POWER light and its arcs, GAME BOY COLOR; COMM. over the infrared port; the Nintendo racetrack; the dark
  D-pad, B and A with their letters, SELECT and START, the speaker's holes; the power switch on the top's left, the
  volume wheel and the link port in the left end; on the back the cartridge's bay and the batteries' bulge.

Each card has two textures besides its screen's: the print (PRINT_ATLAS, PRINT_REGIONS: the face, the back, the ends,
the top and the bottom, each seen square on; the D-pad's top and, on the Color, the buttons' letters; and swatches, each
a block's middle) and the cartridge's (CART_ATLAS, CART_REGIONS: its label side and its other side). A region is (x, y,
width, height) in pixels.

The lens is the card's screen: a `video` material across the whole of it (LENS's box), its texture the lens switched
off, and its video (game_boy_video.py) the lens through the focused clip, frame for frame: the light, the LCD at two
video pixels a dot (LCD_PX: where its 320 x 288 block is in the video's VIDEO pixels), the lens's printing round it.

The focused clip's timing (TIMING, frames at FPS) is shared by game_boy.py and game_boy_video.py.
"""

import math

FPS = 30
LENGTH = 300                      # 10 s

PRINT_ATLAS = 1024
CART_ATLAS = (1024, 512)


def _arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def rounded_rect(x0, x1, z0, z1, radii, bow=0.0, n=8):
    """A rectangle's outline (x, z), anticlockwise from its bottom edge, its corners rounded (radii: bottom left, bottom
    right, top right, top left; a corner's points scale with its radius), its bottom edge bowed down by bow in the
    middle."""
    bl, br, tr, tl = radii

    def steps(r):
        return max(2, int(round(n * max(1.0, r / 4.0) ** 0.5)))
    pts = _arc(x1 - br, z0 + br, br, -90.0, 0.0, steps(br))
    pts += _arc(x1 - tr, z1 - tr, tr, 0.0, 90.0, steps(tr))
    pts += _arc(x0 + tl, z1 - tl, tl, 90.0, 180.0, steps(tl))
    pts += _arc(x0 + bl, z0 + bl, bl, 180.0, 270.0, steps(bl))
    if bow:
        # The bottom edge, from the bottom left corner's end to the bottom right's start, sagging bow at its middle.
        a, b = x0 + bl, x1 - br
        sag = [(a + (b - a) * k / 8, z0 - bow * math.sin(math.pi * k / 8)) for k in range(1, 8)]
        pts = pts + sag
    return pts


MODELS = {
    "gb": dict(
        name="Game Boy",
        width=90.0, height=148.0, depth=30.0,
        corners=(4.0, 20.0, 3.0, 3.0),            # bottom left, bottom right, top right, top left
        round=(1.8, 2.5),                         # the face's edge and the back's, rounded over
        # The lens: its box and corners; set this deep into a recess this much wider than it.
        lens=dict(rect=(-38.2, 38.2, 77.9, 136.1), radii=(2.5, 8.5, 2.5, 2.5), bow=0.0, front=0.25, recess=0.8, gap=0.3),
        window=(-24.6, 24.6, 83.4, 129.7),        # the dark frame round the LCD, on the lens
        led=dict(at=(-32.0, 113.9), r=1.25),
        dpad=dict(at=(-25.8, 46.9), arm=22.4, width=8.0, out=2.8),
        buttons=dict(b=(18.9, 44.9), a=(33.6, 51.5), r=5.0, out=3.0),
        pills=dict(select=(-11.7, 25.1), start=(3.6, 25.1), size=(13.0, 3.6), slant=22.5, out=1.5),
        speaker=dict(first=(15.6, 9.4), step=(4.38, 2.48), count=6, length=13.7, width=1.7, slant=-59.8, deep=2.0),
        switch=dict(x=-29.4, y=(2.6, 6.6), size=(5.0, 2.2), travel=6.0),     # its OFF place; y its front and back
        wheels=[dict(side=1, z=97.6, r=6.5, out=1.2, y=(9.0, 13.0)), dict(side=-1, z=103.0, r=6.5, out=1.2, y=(9.0, 13.0))],
        bay=dict(x=(-30.0, 30.0), z0=119.0, deep=9.0),                       # the cartridge's open bay, from the back
        panel=dict(rect=(-35.0, 35.0, 76.0, 119.0), out=1.2),                # the label panel standing off the back
        cover=dict(rect=(-32.0, 32.0, 2.0, 63.0), out=0.8, tab=(-9.0, 9.0, 62.0, 75.0)),
        cart=dict(kind="dmg", size=(57.0, 65.0, 8.0), protrudes=1.0, back=0.5),
        colours=dict(case="#C9C4BF", lens="#5D5C66", frame="#1F2025", lcd_off="#8E9660", led_off="#4A2324",
                     led_lit="#FF3424", navy="#2C2A8C", magenta="#9A1E5C", stripe_navy="#2D2F8C", ab="#A8195E",
                     dpad="#1B1B1E", rubber="#8B878E", slot="#3C3A38", cart="#A3A1A6", wheel="#4A484C", port="#2A2A2E",
                     gap="#2E2D33", screw="#8F8B88", sticker="#D9D7DE"),
        # The video: the lens's box at two video pixels a dot; the LCD's 320 x 288 block in it.
        video=(520, 396), lcd_px=(100, 57, 320, 288),
        print_regions=dict(face=(0, 0, 450, 740), back=(458, 0, 270, 444), right=(736, 0, 90, 444),
                           left=(834, 0, 90, 444), top=(458, 452, 270, 90), bottom=(458, 550, 270, 90),
                           dpad=(736, 452, 180, 180)),
        made_up=("Kaleidrop (Europe)", "megadrive"),
        code="DMG-KDP-EUR",
    ),
    "gbc": dict(
        name="Game Boy Color",
        width=78.0, height=133.5, depth=24.0,
        corners=(12.0, 12.0, 3.6, 3.6),
        round=(3.0, 3.0),
        lens=dict(rect=(-34.05, 34.05, 68.3, 128.0), radii=(9.0, 9.0, 2.0, 2.0), bow=2.5, front=0.25, recess=0.8,
                  gap=0.25),
        window=(-22.3, 22.3, 82.0, 120.1),
        led=dict(at=(-31.0, 108.6), r=0.7),
        dpad=dict(at=(-22.8, 47.1), arm=19.0, width=6.6, out=2.6),
        buttons=dict(b=(13.5, 44.9), a=(27.8, 49.4), r=4.7, out=2.6),
        pills=dict(select=(-6.0, 25.0), start=(5.6, 25.0), size=(6.9, 2.7), slant=0.0, out=1.4),
        speaker=dict(at=(25.5, 17.5), r=8.6, pitch=2.3, hole=0.55),
        switch=dict(x=-26.0, y=(8.0, 12.0), size=(6.0, 1.8), travel=5.0),
        wheels=[dict(side=-1, z=78.3, r=6.0, out=1.1, y=(9.0, 12.6))],
        bay=dict(x=(-29.5, 29.5), z0=113.0, deep=9.0),
        bulge=dict(rect=(-32.0, 32.0, 5.0, 72.0), out=3.4, r=7.0),             # the batteries' bulge on the back
        cart=dict(kind="dmg", size=(57.0, 65.0, 8.0), protrudes=4.0, back=0.5),
        colours=dict(case="#F2C232", lens="#0D0F14", frame="#2A2C33", lcd_off="#9EA096", led_off="#3C1C1E",
                     led_lit="#FF3A30", logo="#646A76", emboss="#D9A81E", dark="#26272D", slot="#3A2E10",
                     cart="#26272B", wheel="#3A3B40", port="#24252A", gap="#8C7020", screw="#B8B4AE"),
        video=(488, 452), lcd_px=(84, 60, 320, 288),
        print_regions=dict(face=(0, 0, 420, 718), back=(458, 0, 252, 432), right=(736, 0, 78, 432),
                           left=(834, 0, 78, 432), top=(458, 452, 252, 78), bottom=(458, 550, 252, 78),
                           dpad=(736, 452, 180, 180), btn_a=(924, 452, 80, 80), btn_b=(924, 540, 80, 80)),
        made_up=("Ghoulish Gus (Europe)", "megadrive"),
        code="DMG-GHG-EUR",
    ),
}

# Plain colours: blocks of the print atlas, each SWATCH pixels square, named by their middles.
SWATCH = 32
SWATCH_NAMES = ("case", "lens", "frame", "gap", "dark", "ab", "rubber", "slot", "wheel", "port", "cart", "cart_edge",
                "metal")
SWATCHES = {name: (472 + SWATCH * (k % 17), 662 + SWATCH * (k // 17)) for k, name in enumerate(SWATCH_NAMES)}

# The cartridge: the Game Boy's (57 x 65 x 8 mm, its corner cut), its label side seen looking at it (the console's
# back), and its other side.
CART_REGIONS = dict(label=(0, 0, 440, 502), front=(452, 0, 300, 342))
CART_SWATCHES = {"cart": (800, 40), "edge": (850, 40), "pins": (900, 40)}


def lens_outline(kind, grow=0.0):
    lens = MODELS[kind]["lens"]
    x0, x1, z0, z1 = lens["rect"]
    return rounded_rect(x0 - grow, x1 + grow, z0 - grow + lens["bow"], z1 + grow, [r + grow for r in lens["radii"]],
                        bow=lens["bow"])


def body_outline(kind):
    """The face's outline; the Color's bottom edge bows down 1.5 mm, to z = 0 at its middle."""
    m = MODELS[kind]
    w, h = m["width"], m["height"]
    bow = 1.5 if kind == "gbc" else 0.0
    return rounded_rect(-w / 2, w / 2, bow, h, m["corners"], bow=bow, n=6)


def cart_outline(size, inset=0.0):
    """The Game Boy cartridge seen from the console's front (x right, z up, from its bottom edge), its top left corner
    cut, moved in by inset."""
    w, h, _ = size
    x0, x1, z0, z1, cut = -w / 2 + inset, w / 2 - inset, inset, h - inset, 4.5
    return ([(x0 + 1.0, z0), (x1 - 1.0, z0)] + _arc(x1 - 1.0, z0 + 1.0, 1.0, -90.0, 0.0, 3)[1:]
            + [(x1, z1 - 1.0)] + _arc(x1 - 1.0, z1 - 1.0, 1.0, 0.0, 90.0, 3)[1:]
            + [(x0 + cut, z1), (x0, z1 - cut)] + _arc(x0 + 1.0, z0 + 1.0, 1.0, 180.0, 270.0, 3)[:-1])


# ---- The focused clip's timing (frames) ------------------------------------------------------------------------------
# The cartridge appears above the slot, its label towards the viewer; hovers; turns round; drops in and settles. The
# switch slides ON and the light comes on with the LCD; the boot; the game's title, START; play; the switch slides OFF
# and the picture fades; the cartridge rises out and goes.
TIMING = {
    "gb": dict(appear=(6, 14), turn=(36, 50), drop=(50, 62), switch_on=(70, 75), power=75, boot=(82, 128),
               handover=150, title=156, start=184, play=196, switch_off=(264, 269), lcd_off=(269, 277),
               out=(278, 290), gone=(290, 298)),
    "gbc": dict(appear=(6, 14), turn=(36, 50), drop=(50, 62), switch_on=(70, 75), power=75, boot=(80, 128),
                handover=146, title=152, start=182, play=194, switch_off=(264, 269), lcd_off=(269, 277),
                out=(278, 290), gone=(290, 298)),
}

# The game's moves, frames after `play`: the buttons pressed and the D-pad's directions held, as (frame, length).
MOVES = {
    "gb": dict(left=[(10, 4), (18, 4)], down=[(30, 5)], a=[24], b=[60]),
    "gbc": dict(right=[(4, 62)], a=[16, 46], b=[30]),
}
