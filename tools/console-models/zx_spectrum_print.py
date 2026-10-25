"""The ZX Spectrum's and its television's printing, for the console theme's ZX Spectrum model
(tools/console-models/zx_spectrum.py).

Draws its two atlases, their regions as zx_spectrum_layout.py places them. zx_spectrum_print.png: the computer's top
seen from above, in millimetres as the model's planar UVs map it (the black plate's red and green keywords and the
colours' names, the grey-blue key tops with their letters and keywords, the hump's embossed name and ZX Spectrum, the
rainbow across the corner), the television's front (its badge, the controls' legends, the speaker's slots) and the
swatches small parts take their colour from. zx_spectrum_media.png: the screen at rest, the copyright message on
white, 320 x 256 pixels with its border; the paper's states while a game loads, at the Spectrum's 256 x 192 pixels
(LOAD typed, then LOAD "", blank, the header's name, the loading screen's bitmap a third and two thirds in, all of it
in black and white, then in colour); and the border's states, each a column of its stripes (the pilot tone's red and
cyan, the data's blue and yellow, each twice, and black). The game, Odyssey, is made up. Run it with the system
Python (Pillow):

    python tools/console-models/zx_spectrum_print.py <out folder>

It writes zx_spectrum_print.png and zx_spectrum_media.png there.
"""

import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zx_spectrum_layout as L  # noqa: E402
from retro_pc_print import rgb, shade  # noqa: E402
from windows_pc_print import FONTS, Region  # noqa: E402

# The Spectrum's colours, ink and paper: black, blue, red, magenta, green, cyan, yellow, white; bright ones too.
NORMAL = [(0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215), (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215)]
BRIGHT = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255)]
BLACK, BLUE, RED, MAGENTA, GREEN, CYAN, YELLOW, WHITE = range(8)
WORD_COLOURS = {"BLUE": (60, 110, 255), "RED": (235, 50, 40), "MAGENTA": (200, 60, 200), "GREEN": (60, 190, 70),
                "CYAN": (40, 190, 230), "YELLOW": (240, 210, 40), "WHITE": (240, 240, 240)}
RED_WORD, GREEN_WORD, KEY_WORD = (230, 46, 38), (62, 196, 72), (236, 238, 240)


def top_point(x, y):
    """A point of the computer's top (x from its middle, y back from its front) in the top region's millimetres."""
    return x + L.WIDTH / 2, L.DEPTH - y


# ---- The computer's top ----------------------------------------------------------------------------------------------

def key_top(reg, key, rect):
    name, row, letter, keyword, green, red = key
    x0, y0, x1, y1 = rect
    (a, b), (c, e) = top_point(x0, y1), top_point(x1, y0)
    reg.rect_(a, b, c, e, rgb(L.COLOURS["key"]), r=L.KEY["radius"])
    reg.rect_(a + 0.8, b + 0.6, c - 0.8, e - 1.2, shade(rgb(L.COLOURS["key"]), 0.06), r=L.KEY["radius"] - 0.6)
    if "\n" in letter:                                            # CAPS SHIFT, SYMBOL SHIFT, BREAK SPACE
        top, bottom = letter.split("\n")
        colour = RED_WORD if name == "symbol_shift" else KEY_WORD
        reg.text(top, "arialbd.ttf", 2.6, (a + c) / 2, b + 3.6, colour)
        reg.text(bottom, "arialbd.ttf", 2.6 if name != "space" else 3.4, (a + c) / 2, b + 7.6, colour)
        return
    if name == "enter":
        reg.text("ENTER", "arialbd.ttf", 2.8, (a + c) / 2, (b + e) / 2, KEY_WORD)
        return
    reg.text(letter, "arialbd.ttf", 5.0, a + 3.2, b + 3.6, KEY_WORD)
    if keyword:
        reg.text(keyword, "arialbd.ttf", 2.0, c - 1.2, e - 2.6, KEY_WORD, anchor="rm")
    if row == 1:                                                  # a block graphic and a red symbol
        reg.rect_(c - 5.2, b + 1.6, c - 1.6, b + 5.2, (240, 240, 240))
        reg.rect_(c - 5.2, b + 3.4, c - 3.4, b + 5.2, rgb(L.COLOURS["key"]))
        reg.text("!@#$%&'()_"["1234567890".index(letter)], "arialbd.ttf", 2.4, c - 3.4, e - 2.8, RED_WORD)
    else:
        reg.text("<=" if letter == "Q" else "*", "arialbd.ttf", 2.2, c - 2.4, b + 2.8, RED_WORD)


def plate_words(reg, key, rect, index):
    """The words printed on the plate round a key: green above it (or a digit's function and colour), red below."""
    name, row, letter, keyword, green, red = key
    x0, y0, x1, y1 = rect
    (a, top), (_, bottom) = top_point(x0, y1), top_point(x0, y0)
    if row == 1:
        colour = L.COLOUR_NAMES[index]
        if colour == "BLACK":
            reg.rect_(a + 0.5, top - 6.9, a + 10.5, top - 4.3, (236, 236, 236))
            reg.text(colour, "arialbd.ttf", 2.0, a + 5.5, top - 5.6, (0, 0, 0))
        elif colour:
            reg.text(colour, "arialbd.ttf", 2.0, a + 1.0, top - 5.6, WORD_COLOURS[colour], anchor="lm")
        if green:
            reg.text(green, "arialbd.ttf", 2.0, a + 1.0, top - 2.6, KEY_WORD, anchor="lm")
    elif green:
        reg.text(green, "arialbd.ttf", 2.1, a + 1.0, top - 2.3, GREEN_WORD, anchor="lm")
    if red:
        reg.text(red, "arialbd.ttf", 2.1, a + 1.0, bottom + 2.5, RED_WORD, anchor="lm")


def sinclair_logo(reg, x, y, height, colour):
    """The hump's embossed name: lower-case letters drawn as horizontal bars, as the Sinclair logo is."""
    font = ImageFont.truetype(FONTS + "arialbd.ttf", max(1, round(height * 1.9 * reg.sx)))
    mask = Image.new("L", reg.img.size, 0)
    ImageDraw.Draw(mask).text(reg.p(x, y), "sinclair", font=font, fill=255, anchor="ls")
    bars = Image.new("L", reg.img.size, 0)
    db = ImageDraw.Draw(bars)
    step = max(2, round(height / 4.6 * reg.sy))
    for row in range(0, reg.img.size[1], step):
        db.rectangle([0, row, reg.img.size[0], row + step * 0.55], fill=255)
    reg.img.paste(colour, (0, 0), ImageChops.multiply(mask, bars))


def rainbow(reg):
    """The four stripes across the corner, from the front edge up to the right end."""
    r = L.RAINBOW
    for k, colour in enumerate(r["colours"]):
        x0 = r["front_x"] + k * r["width"] / math.sin(math.atan(r["slope"]))
        dx = r["width"] / math.sin(math.atan(r["slope"]))
        far = L.WIDTH / 2 + 5
        points = [(x0, -1.0), (x0 + dx, -1.0), (far, (far - x0 - dx) * r["slope"]), (far, (far - x0) * r["slope"])]
        reg.poly([top_point(x, y) for x, y in points], rgb(colour))


def top():
    reg = Region(L.PRINT_REGIONS["top"], L.WIDTH, L.DEPTH, rgb(L.COLOURS["plate"]))
    # The hump, behind the step: matte black, the embossed name, ZX Spectrum.
    _, step = top_point(0, L.STEP[0])
    reg.rect_(0, 0, L.WIDTH, step, rgb(L.COLOURS["case"]))
    sinclair_logo(reg, *top_point(-112.0, 112.5), 15.0, (34, 34, 38))
    reg.text("ZX Spectrum", "arialbi.ttf", 6.2, *top_point(-110.0, 107.0), (236, 238, 240), anchor="lm")
    rainbow(reg)
    counts = {}
    for key, rect in L.keys_with_rects():
        row = key[1]
        index = counts.get(row, 0)
        counts[row] = index + 1
        plate_words(reg, key, rect, index)
    for key, rect in L.keys_with_rects():
        key_top(reg, key, rect)
    return reg


def tv_front():
    """The television's front, seen from in front: the black bezel, the badge under the screen, the speaker's slots
    and the controls' legends."""
    tv = L.TV
    w, h = tv["width"], tv["height"]
    reg = Region(L.PRINT_REGIONS["tv"], w, h, rgb(L.COLOURS["bezel"]))

    def at(x, z):
        return x + w / 2, h - z
    s = tv["screen"]
    reg.text("ODYSSEY", "arialbd.ttf", 9.0, *at(s["x"], s["z"] - s["opening"][1] / 2 - 14.0), (200, 204, 210))
    reg.text("COLOUR TELEVISION", "arial.ttf", 3.6, *at(s["x"], s["z"] - s["opening"][1] / 2 - 24.0), (150, 154, 160))
    x0, x1 = tv["controls"]["x"]
    for k in range(9):                                            # the speaker's slots, top right
        z = h - 32.0 - k * 4.6
        reg.rect_(*at(x0 + 4.0, z), *at(x1 - 4.0, z - 2.2), (6, 6, 8), r=1.0)
    for k, (bx, bz) in enumerate(tv["buttons"]):
        reg.text(str(k + 1), "arialbd.ttf", 3.6, *at(bx - tv["button"][0] / 2 - 2.6, bz), (200, 204, 210), anchor="rm")
    reg.text("CHANNEL", "arialbd.ttf", 3.0, *at((x0 + x1) / 2, tv["buttons"][0][1] + 14.0), (150, 154, 160))
    reg.text("VOLUME", "arialbd.ttf", 3.0, *at((x0 + x1) / 2, tv["knob"]["z"] + tv["knob"]["r"] + 5.0), (150, 154, 160))
    reg.text("POWER", "arialbd.ttf", 3.0, *at(tv["power"]["x"] - 6.0, tv["power"]["z"] + 9.0), (150, 154, 160))
    reg.circle(*at(tv["power"]["x"] + 12.0, tv["power"]["z"] + 9.0), 1.6, (255, 40, 30))
    return reg


def print_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), rgb(L.COLOURS["plate"]))
    top().paste(image)
    tv_front().paste(image)
    d = ImageDraw.Draw(image)
    for name, colour in (("black", rgb(L.COLOURS["bezel"])), ("silver", rgb(L.COLOURS["handle"])),
                         ("red", (255, 40, 30))):
        x, y = L.PRINT_SWATCHES[name]
        d.rectangle([x - 12, y - 12, x + 11, y + 11], fill=colour)
    return image


# ---- The screens -----------------------------------------------------------------------------------------------------

FONT = ImageFont.truetype(FONTS + "consolab.ttf", 10)


def chars(img, col, row, text, ink=BLACK, paper=WHITE, inverse=False):
    """Text in the Spectrum's character cells, 8 x 8 pixels each, from column col of row row of the paper."""
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    fg, bg = (NORMAL[paper], NORMAL[ink]) if inverse else (NORMAL[ink], NORMAL[paper])
    for k, ch in enumerate(text):
        x, y = (col + k) * 8, row * 8
        d.rectangle([x, y, x + 7, y + 7], fill=bg)
        d.text((x + 4, y + 4), ch, font=FONT, fill=fg, anchor="mm")


def paper(lines=()):
    img = Image.new("RGB", (256, 192), NORMAL[WHITE])
    for col, row, text, inverse in lines:
        chars(img, col, row, text, inverse=inverse)
    return img


def loading_screen():
    """Odyssey's loading screen, 256 x 192, drawn in 8 x 8 cells of one ink and one paper each (so its colours clash
    as the Spectrum's do): a night sky, a ringed planet, the ship, the title, a ground of bright tiles. Returns the
    bitmap (ink pixels set) and the cells' attributes."""
    ink_pixels = Image.new("1", (256, 192), 0)
    d = ImageDraw.Draw(ink_pixels)
    attributes = [[(WHITE, BLACK, False)] * 32 for _ in range(24)]   # (ink, paper, bright)
    rng = random.Random(48)
    for _ in range(70):                                           # stars
        d.point((rng.randrange(256), rng.randrange(120)), fill=1)
    d.ellipse([168, 40, 232, 104], fill=1)                        # the planet, its shadowed side clear
    d.ellipse([180, 44, 240, 104], fill=0)
    d.arc([140, 62, 252, 86], 160, 380, fill=1, width=2)
    d.polygon([(110, 88), (62, 74), (72, 88), (62, 102)], fill=1)  # the ship
    d.polygon([(76, 82), (52, 62), (62, 84)], fill=1)
    d.polygon([(76, 94), (52, 114), (62, 92)], fill=1)
    for k in range(3):
        d.line([(16 + k * 6, 84 + k * 4), (50, 84 + k * 4)], fill=1)
    font = ImageFont.truetype(FONTS + "ariblk.ttf", 26)
    d.text((128, 22), "ODYSSEY", font=font, fill=1, anchor="mm")
    for y in range(136, 192):                                    # the ground: tiles narrowing to the horizon
        for x in range(256):
            z = 600.0 / (y - 120)
            if (int((x - 128) * z / 60.0 + 40) + int(z)) % 2:
                d.point((x, y), fill=1)
    for row in range(24):
        for col in range(32):
            if row < 6:
                attributes[row][col] = (YELLOW, BLUE, True)          # the title on blue
            elif row < 16:
                attributes[row][col] = (CYAN if col < 18 else RED, BLACK, col >= 18)
            else:
                attributes[row][col] = (MAGENTA, BLUE, row % 2 == 0)
    for col in range(8, 14):                                      # the ship's flame
        attributes[11][col] = (YELLOW, BLACK, True)
    chars_mask = Image.new("1", (256, 192), 0)
    dc = ImageDraw.Draw(chars_mask)
    dc.fontmode = "1"
    for k, ch in enumerate("PRESS ANY KEY"):
        dc.text(((9 + k) * 8 + 4, 22 * 8 + 4), ch, font=FONT, fill=1, anchor="mm")
    for col in range(9, 22):
        attributes[22][col] = (WHITE, BLACK, True)
    for y in range(176, 184):                                     # the message's row: its own cells
        for x in range(72, 176):
            ink_pixels.putpixel((x, y), chars_mask.getpixel((x, y)))
    return ink_pixels, attributes


def screen_bitmap(ink_pixels, lines):
    """The bitmap in black and white, the pixel lines loaded so far (the Spectrum loads a third at a time, each
    character row's first pixel line, then its second, and so on)."""
    img = Image.new("RGB", (256, 192), NORMAL[WHITE])
    for y in range(192):
        third, line, row = y // 64, y % 8, (y % 64) // 8
        order = third * 64 + line * 8 + row
        if order < lines:
            for x in range(256):
                if ink_pixels.getpixel((x, y)):
                    img.putpixel((x, y), NORMAL[BLACK])
    return img


def coloured(ink_pixels, attributes):
    img = Image.new("RGB", (256, 192))
    for y in range(192):
        for x in range(256):
            ink, paper_colour, bright = attributes[y // 8][x // 8]
            palette = BRIGHT if bright else NORMAL
            img.putpixel((x, y), palette[ink] if ink_pixels.getpixel((x, y)) else palette[paper_colour])
    return img


def border_column(kind, phase):
    """A column of the border's stripes, 16 x 256: the pilot tone's broad red and cyan, the data's thin blue and
    yellow, or plain black."""
    img = Image.new("RGB", (16, 256), NORMAL[BLACK])
    d = ImageDraw.Draw(img)
    rng = random.Random(phase + 7)
    y = -phase * 5
    while y < 256:
        if kind == "pilot":
            d.rectangle([0, y, 15, y + 9], fill=NORMAL[RED])
            d.rectangle([0, y + 10, 15, y + 19], fill=NORMAL[CYAN])
            y += 20
        elif kind == "data":
            a, b = rng.choice((2, 2, 4)), rng.choice((2, 4, 4))
            d.rectangle([0, y, 15, y + a - 1], fill=NORMAL[BLUE])
            d.rectangle([0, y + a, 15, y + a + b - 1], fill=NORMAL[YELLOW])
            y += a + b
        else:
            break
    return img


def glass():
    """The screen at rest: the white border round the paper, the copyright message on its last line."""
    img = Image.new("RGB", L.GLASS_PX, NORMAL[WHITE])
    img.paste(paper([(0, 23, "© 1982 Sinclair Research Ltd", False)]), (32, 32))
    return img


def bled(img, n=4):
    """img with n pixels round it repeating its edge, so filtering at the region's edge sees its own colours."""
    w, h = img.size
    out = img.resize((w + 2 * n, h + 2 * n), Image.NEAREST)
    out.paste(img.crop((0, 0, w, 1)).resize((w, n)), (n, 0))
    out.paste(img.crop((0, h - 1, w, h)).resize((w, n)), (n, h + n))
    out.paste(img.crop((0, 0, 1, h)).resize((n, h)), (0, n))
    out.paste(img.crop((w - 1, 0, w, h)).resize((n, h)), (w + n, n))
    out.paste(img, (n, n))
    return out


def media_atlas():
    image = Image.new("RGB", (L.ATLAS, L.ATLAS), (24, 24, 24))
    ink_pixels, attributes = loading_screen()
    papers = {
        "load": paper([(0, 22, "LOAD ", False), (5, 22, "L", True)]),
        "load2": paper([(0, 22, 'LOAD ""', False), (7, 22, "L", True)]),
        "blank": paper(),
        "header": paper([(0, 0, "Program: ODYSSEY", False)]),
        "third1": screen_bitmap(ink_pixels, 64 + 24),
        "third2": screen_bitmap(ink_pixels, 128 + 40),
        "mono": screen_bitmap(ink_pixels, 192),
        "colour": coloured(ink_pixels, attributes),
    }
    x, y, w, h = L.MEDIA_REGIONS["glass"]
    image.paste(glass(), (x, y))
    for name, img in papers.items():
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(bled(img), (x - 4, y - 4))
    for name, kind, phase in (("pilot_a", "pilot", 0), ("pilot_b", "pilot", 1), ("data_a", "data", 0),
                              ("data_b", "data", 1), ("black", "black", 0)):
        x, y, w, h = L.MEDIA_REGIONS[name]
        image.paste(border_column(kind, phase), (x, y))
    return image


def main(out):
    os.makedirs(out, exist_ok=True)
    for name, image in (("zx_spectrum_print.png", print_atlas()), ("zx_spectrum_media.png", media_atlas())):
        path = os.path.join(out, name)
        image.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main(sys.argv[1])
