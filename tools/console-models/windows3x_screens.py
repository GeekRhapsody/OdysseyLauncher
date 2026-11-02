"""The Windows 3.x card's screens (retro_pc_print.py draws its still with them, retro_pc_video.py its video), following
its clip frame for frame by the timing in windows3x_layout.py. Run with the system Python (Pillow, numpy).

Windows 3.1 at 640 x 480, drawn pixel for pixel as it drew itself: its windows' sizing borders, their title bars (navy
when active, white when not) in the System font, the control-menu boxes and the minimise and maximise buttons, the menu
bars, the icons' titles in MS Sans Serif (raster_fonts.py reads Windows' own bitmap fonts), and the outline that zooms
between an icon and its window as a group or a program opens or closes. Program Manager holds its Main group, open,
and its minimised groups' icons along its foot; the Games group holds the made-up games (tools/made-up-games).

Spellbrick (made up) in its window: its title (a Codex painting, paintings.py's w3x_spell_title, with its logo), then
its playfield over the painting's night sky, in one fixed palette of 256 colours: the castle of glowing bricks, the
wizard on his floating stone (w3x_spell_sprites) following the mouse, the orb (its flights windows3x_layout.ORB's),
breaking a brick each time it goes up, a green potion falling and caught; the status bar under it. Clicking Game in
its menu bar waits the game and drops the menu down; Exit closes it.

The pointer: Windows' arrow, its hourglass while the game loads, hidden over the playfield while the game is played.
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import raster_fonts as R  # noqa: E402
import retro_pc_layout as K  # noqa: E402
import retro_pc_screens as S  # noqa: E402
import windows3x_layout as L  # noqa: E402

TEAL, NAVY, WHITE, BLACK = (0, 128, 128), (0, 0, 128), (255, 255, 255), (0, 0, 0)
GREY, DARK = (192, 192, 192), (128, 128, 128)
YELLOW, RED, GREEN, BLUE, CYAN, MAGENTA = (255, 255, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), \
    (255, 0, 255)

ARROW = ["X", "XX", "X.X", "X..X", "X...X", "X....X", "X.....X", "X......X", "X.......X", "X........X",
         "X.....XXXXX", "X..X..X", "X.X X..X", "XX  X..X", "X    X..X", "     X..X", "      XX"]
HOURGLASS = ["XXXXXXXXXXXXX", "X...........X", " XXXXXXXXXXX", " X.........X", " X.X.X.X.X.X", "  X.X.X.X.X",
             "   X.X.X.X", "    X.X.X", "     X.X", "     X.X", "    X...X", "   X..X..X", "  X.......X",
             " X...X.X...X", " X..X.X.X..X", " XXXXXXXXXXX", "X...........X", "XXXXXXXXXXXXX"]
MAIN_ICONS = [("File Manager", "files"), ("Control Panel", "control"), ("Print Manager", "printer"),
              ("Clipboard Viewer", "clipboard"), ("DOS Prompt", "dos"), ("Windows Setup", "setup"),
              ("PIF Editor", "pif"), ("Read Me", "readme")]
BRICK_COLOURS = [(255, 64, 255), (64, 224, 255), (255, 232, 64), (96, 255, 96), (255, 150, 40), (180, 96, 255),
                 (255, 80, 96)]


def bitmap(img, rows, x, y):
    """A cursor's bitmap at (x, y): X black, . white, the rest clear."""
    px = img.load()
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in "X." and 0 <= x + i < img.width and 0 <= y + j < img.height:
                px[x + i, y + j] = BLACK if ch == "X" else WHITE


def bevel(d, x0, y0, x1, y1, pressed=False):
    """A 3D button's face: white and grey edges (swapped while it's pressed), its black frame."""
    d.rectangle([x0, y0, x1, y1], fill=GREY, outline=BLACK)
    hi, lo = (DARK, GREY) if pressed else (WHITE, DARK)
    d.line([(x0 + 1, y1 - 1), (x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], fill=hi)
    d.line([(x0 + 2, y1 - 2), (x0 + 2, y0 + 2), (x1 - 2, y0 + 2)], fill=hi)
    d.line([(x1 - 1, y0 + 1), (x1 - 1, y1 - 1), (x0 + 1, y1 - 1)], fill=lo)
    d.line([(x1 - 2, y0 + 2), (x1 - 2, y1 - 2), (x0 + 2, y1 - 2)], fill=lo)


def triangle(d, cx, cy, down, size=4):
    if down:
        d.polygon([(cx - size, cy - size // 2), (cx + size, cy - size // 2), (cx, cy + size // 2 + 1)], fill=BLACK)
    else:
        d.polygon([(cx - size, cy + size // 2), (cx + size, cy + size // 2), (cx, cy - size // 2 - 1)], fill=BLACK)


def window(img, rect, title, active, menu=None, child=False, pressed_min=False, menu_open=None):
    """A Windows 3.1 window in rect: its sizing border, its title bar, the control-menu box, the minimise and maximise
    buttons, its menu bar if it has one (menu_open: the title held down, inverted); its client area cleared to white.
    Returns the client area."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = rect
    d.rectangle([x0, y0, x1, y1], fill=GREY, outline=BLACK)
    d.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], outline=BLACK)
    for x in (x0 + 22, x1 - 22):                                 # the border's corners' notches
        d.line([(x, y0), (x, y0 + 4)], fill=BLACK)
        d.line([(x, y1 - 4), (x, y1)], fill=BLACK)
    for y in (y0 + 22, y1 - 22):
        d.line([(x0, y), (x0 + 4, y)], fill=BLACK)
        d.line([(x1 - 4, y), (x1, y)], fill=BLACK)
    t0, t1 = y0 + 5, y0 + 23
    d.rectangle([x0 + 5, t0, x1 - 5, t1], fill=NAVY if active else WHITE)
    d.line([(x0 + 5, t1 + 1), (x1 - 5, t1 + 1)], fill=BLACK)
    d.rectangle([x0 + 5, t0, x0 + 23, t1], fill=GREY, outline=BLACK)          # the control-menu box
    bar = 9 if child else 13
    d.rectangle([x0 + 14 - bar // 2, t0 + 8, x0 + 14 + bar // 2, t0 + 10], fill=WHITE, outline=BLACK)
    d.line([(x0 + 15 - bar // 2, t0 + 11), (x0 + 15 + bar // 2, t0 + 11)], fill=BLACK)
    bevel(d, x1 - 42, t0, x1 - 24, t1, pressed=pressed_min)
    triangle(d, x1 - 33 + (1 if pressed_min else 0), t0 + 9 + (1 if pressed_min else 0), down=True)
    bevel(d, x1 - 23, t0, x1 - 5, t1)
    triangle(d, x1 - 14, t0 + 9, down=False)
    font = R.system()
    tw = font.width(title)
    font.draw(img, (x0 + x1) // 2 - tw // 2 + 4, t0 + 1, title, WHITE if active else BLACK)
    top = t1 + 2
    if menu:
        d.rectangle([x0 + 5, top, x1 - 5, top + 18], fill=WHITE)
        d.line([(x0 + 5, top + 19), (x1 - 5, top + 19)], fill=BLACK)
        x = x0 + 10
        for item in menu:
            w = font.width(item)
            if item == menu_open:
                d.rectangle([x - 4, top, x + w + 4, top + 18], fill=BLACK)
            font.draw(img, x, top + 1, item, WHITE if item == menu_open else BLACK)
            x += w + 16
        top += 20
    d.rectangle([x0 + 5, top, x1 - 5, y1 - 5], fill=WHITE)
    return (x0 + 5, top, x1 - 5, y1 - 5)


def icon(img, kind, x, y):
    """A 32 x 32 icon, its top left at (x, y)."""
    d = ImageDraw.Draw(img)
    if kind == "files":                                          # a filing cabinet
        d.rectangle([x + 6, y + 2, x + 25, y + 30], fill=(200, 160, 40), outline=BLACK)
        for k in range(3):
            d.rectangle([x + 8, y + 4 + k * 9, x + 23, y + 10 + k * 9], fill=(240, 200, 70), outline=BLACK)
            d.rectangle([x + 14, y + 6 + k * 9, x + 17, y + 8 + k * 9], fill=BLACK)
    elif kind == "control":                                      # a monitor and a slider
        d.rectangle([x + 2, y + 4, x + 22, y + 20], fill=GREY, outline=BLACK)
        d.rectangle([x + 5, y + 7, x + 19, y + 17], fill=TEAL)
        d.rectangle([x + 8, y + 21, x + 16, y + 25], fill=GREY, outline=BLACK)
        d.rectangle([x + 24, y + 4, x + 30, y + 28], fill=GREY, outline=BLACK)
        d.rectangle([x + 25, y + 14, x + 29, y + 18], fill=RED)
    elif kind == "printer":
        d.rectangle([x + 8, y + 4, x + 24, y + 14], fill=WHITE, outline=BLACK)
        d.rectangle([x + 3, y + 13, x + 29, y + 26], fill=GREY, outline=BLACK)
        d.rectangle([x + 6, y + 22, x + 26, y + 28], fill=WHITE, outline=BLACK)
        d.rectangle([x + 23, y + 16, x + 26, y + 18], fill=GREEN)
    elif kind == "clipboard":
        d.rectangle([x + 6, y + 4, x + 26, y + 30], fill=(170, 110, 50), outline=BLACK)
        d.rectangle([x + 9, y + 8, x + 23, y + 27], fill=WHITE, outline=BLACK)
        d.rectangle([x + 12, y + 2, x + 20, y + 6], fill=GREY, outline=BLACK)
        for k in range(4):
            d.line([(x + 11, y + 12 + k * 4), (x + 21, y + 12 + k * 4)], fill=DARK)
    elif kind == "dos":                                          # a prompt in a window
        d.rectangle([x + 2, y + 5, x + 30, y + 27], fill=BLACK, outline=GREY)
        d.rectangle([x + 2, y + 5, x + 30, y + 9], fill=NAVY)
        R.terminal(8, 8).draw(img, x + 5, y + 14, "C:\\>", WHITE)
    elif kind == "setup":                                        # a computer and a box
        d.rectangle([x + 2, y + 16, x + 20, y + 28], fill=GREY, outline=BLACK)
        d.rectangle([x + 5, y + 4, x + 19, y + 15], fill=GREY, outline=BLACK)
        d.rectangle([x + 7, y + 6, x + 17, y + 13], fill=NAVY)
        d.rectangle([x + 20, y + 12, x + 30, y + 28], fill=(240, 200, 70), outline=BLACK)
    elif kind == "pif":
        d.rectangle([x + 6, y + 2, x + 26, y + 30], fill=WHITE, outline=BLACK)
        d.rectangle([x + 9, y + 6, x + 23, y + 14], fill=BLACK)
        for k in range(3):
            d.line([(x + 9, y + 18 + k * 4), (x + 23, y + 18 + k * 4)], fill=BLUE)
    elif kind == "readme":
        d.polygon([(x + 7, y + 2), (x + 21, y + 2), (x + 26, y + 7), (x + 26, y + 30), (x + 7, y + 30)], fill=WHITE,
                  outline=BLACK)
        for k in range(5):
            d.line([(x + 10, y + 9 + k * 4), (x + 23, y + 9 + k * 4)], fill=DARK)
    elif kind == "group":                                        # a minimised group: a window of little icons
        d.rectangle([x + 2, y + 4, x + 29, y + 28], fill=WHITE, outline=BLACK)
        d.rectangle([x + 2, y + 4, x + 29, y + 8], fill=NAVY)
        for k, c in enumerate((RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA)):
            cx, cy = x + 6 + (k % 3) * 8, y + 12 + (k // 3) * 8
            d.rectangle([cx, cy, cx + 4, cy + 4], fill=c, outline=BLACK)
    elif kind == "spellbrick":                                   # a wizard's hat over a row of bricks
        for k, c in enumerate(BRICK_COLOURS[:4]):
            d.rectangle([x + 2 + k * 7, y + 22, x + 8 + k * 7, y + 28], fill=c, outline=BLACK)
        d.polygon([(x + 16, y + 1), (x + 24, y + 19), (x + 8, y + 19)], fill=(110, 40, 180), outline=BLACK)
        d.rectangle([x + 5, y + 18, x + 27, y + 20], fill=(110, 40, 180), outline=BLACK)
        d.point([(x + 14, y + 10), (x + 18, y + 14), (x + 15, y + 15)], fill=YELLOW)
    elif kind == "kaleidrop":                                    # three gems
        for k, (c, gx, gy) in enumerate(((RED, 8, 8), (CYAN, 20, 12), (YELLOW, 12, 22))):
            d.polygon([(x + gx, y + gy - 6), (x + gx + 6, y + gy), (x + gx, y + gy + 6), (x + gx - 6, y + gy)], fill=c,
                      outline=BLACK)
    elif kind == "hive":                                         # a bee over a comb
        for k in range(3):
            d.regular_polygon((x + 9 + k * 8, y + 24, 5), 6, fill=(240, 190, 40), outline=BLACK)
        d.ellipse([x + 9, y + 4, x + 23, y + 14], fill=YELLOW, outline=BLACK)
        d.line([(x + 14, y + 5), (x + 14, y + 13)], fill=BLACK, width=2)
        d.line([(x + 18, y + 5), (x + 18, y + 13)], fill=BLACK, width=2)
    elif kind == "pinball":                                      # a ball between two flippers
        d.ellipse([x + 11, y + 3, x + 21, y + 13], fill=GREY, outline=BLACK)
        d.polygon([(x + 3, y + 22), (x + 14, y + 27), (x + 13, y + 30), (x + 3, y + 26)], fill=RED, outline=BLACK)
        d.polygon([(x + 29, y + 22), (x + 18, y + 27), (x + 19, y + 30), (x + 29, y + 26)], fill=RED, outline=BLACK)


def title_under(img, text, cx, y, selected=False):
    """An icon's title under it, centred, in MS Sans Serif; highlighted when the icon's selected."""
    font = R.sans(13)
    w = font.width(text)
    if selected:
        ImageDraw.Draw(img).rectangle([cx - w // 2 - 2, y, cx + w // 2 + 2, y + 13], fill=NAVY)
    font.draw(img, cx - w // 2, y, text, WHITE if selected else BLACK)


def zoom(img, a, b, t):
    """The outline Windows draws as an icon opens into its window (or back): rectangles from a towards b."""
    d = ImageDraw.Draw(img)
    for k in (0.0, 0.08):
        u = max(0.0, min(1.0, t - k))
        rect = [a[i] + (b[i] - a[i]) * u for i in range(4)]
        d.rectangle(rect, outline=BLACK)
        d.rectangle([rect[0] + 1, rect[1] + 1, rect[2] - 1, rect[3] - 1], outline=DARK)


def night_sky(size, seed=4):
    """The playfield's sky, in the title painting's colours: deep violet darkening to the top, stars and sparkles."""
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(round(18 + 34 * t), round(6 + 12 * t), round(46 + 56 * t)))
    rng = __import__("random").Random(seed)
    for _ in range(70):
        x, y = rng.randrange(w), rng.randrange(h)
        v = rng.choice((140, 190, 255))
        d.point((x, y), fill=(v, v, min(255, v + 40)))
    for _ in range(8):                                           # a few four-pointed sparkles
        x, y = rng.randrange(8, w - 8), rng.randrange(8, h // 2)
        d.line([(x - 3, y), (x + 3, y)], fill=(230, 210, 255))
        d.line([(x, y - 3), (x, y + 3)], fill=(230, 210, 255))
    return img


class Spellbrick:
    """The game in its window's playfield: its title, and its play at each frame."""

    def __init__(self, made_up):
        x0, y0, x1, y1 = L.FIELD
        self.size = (x1 - x0, y1 - y0)
        art = S.painting("w3x_spell_title")
        k = max(self.size[0] / art.width, self.size[1] / art.height)
        art = art.resize((round(art.width * k), round(art.height * k)), Image.LANCZOS)
        art = art.crop(((art.width - self.size[0]) // 2, 0, (art.width - self.size[0]) // 2 + self.size[0],
                        self.size[1]))
        logo = Image.open(os.path.join(made_up, "library", "media", "arcade", "logos", "spellbrk.png")).convert("RGBA")
        logo = S.scaled(logo, self.size[0] * 0.8)
        title = art.copy()
        title.paste(logo, ((self.size[0] - logo.width) // 2, 18), logo)
        self.sky = night_sky(self.size)
        wizard, orb, green, _red = S.sprites("w3x_spell_sprites")
        self.wizard = S.scaled(wizard, 92)
        self.orb = S.scaled(orb, 2 * L.ORB_R + 6)
        self.potion = S.scaled(green, 18)
        bricks = Image.new("RGB", (8 * len(BRICK_COLOURS), 24))
        for k, c in enumerate(BRICK_COLOURS):                    # the bricks' faces, lit edges and shadows, exactly
            for j, tone in enumerate((c, tuple(min(255, v + 70) for v in c), tuple(v // 2 for v in c))):
                bricks.paste(tone, (8 * k, 8 * j, 8 * k + 8, 8 * j + 8))
        self.palette = S.palette_of([self.sky, bricks, bricks, S.scaled(self.wizard, 240).convert("RGB"),
                                     S.scaled(self.orb, 80).convert("RGB"), S.scaled(self.potion, 120).convert("RGB")])
        self.title_art = S.to_palette(title, S.palette_of([title]))
        self.font = R.sans(13)

    def title(self, prompt):
        img = self.title_art.copy()
        if prompt:
            text = "Click to start"
            w = R.system().width(text)
            R.system().draw(img, (self.size[0] - w) // 2, self.size[1] - 34, text, WHITE)
        return img

    def orb_at(self, f):
        """The orb's middle at frame f (the screen's pixels): on the stone until it leaves, then along its flights."""
        orb = L.ORB
        if f <= orb[0][0]:
            return None
        for (f0, a), (f1, b) in zip(orb, orb[1:]):
            if f < f1:
                t = (f - f0) / (f1 - f0)
                return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        f0, a = orb[-1]
        f1, b = orb[-2]
        t = (f - f0) / (f0 - f1)
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t

    def bat_x(self, f):
        x0, _, x1, _ = L.FIELD
        half = self.wizard.width / 2
        return max(x0 + half, min(x1 - half, L.POINTER.at(f)[0] - 24))

    def play(self, f):
        """The playfield at frame f (the game waits from PAUSE)."""
        f = min(f, L.PAUSE)
        x0, y0 = L.FIELD[0], L.FIELD[1]
        img = self.sky.copy()
        d = ImageDraw.Draw(img)
        b = L.BRICK
        gone = {(c, r) for at, c, r in L.BRICKS if f >= at}
        for r in range(-2, b["rows"]):
            for c in range(12):
                tower = c in (0, 1, 10, 11)
                if r < 0 and not tower or r == 0 and not tower and c % 2 == 1 or (c, r) in gone:
                    continue
                bx, by = b["x0"] + c * b["w"] - x0, b["y0"] + r * b["h"] - y0
                colour = BRICK_COLOURS[(r + 2) % len(BRICK_COLOURS)]
                d.rectangle([bx, by, bx + b["w"] - 2, by + b["h"] - 2], fill=colour)
                d.line([(bx, by + b["h"] - 2), (bx, by), (bx + b["w"] - 2, by)],
                       fill=tuple(min(255, v + 70) for v in colour))
                d.line([(bx + b["w"] - 2, by + 1), (bx + b["w"] - 2, by + b["h"] - 2), (bx + 1, by + b["h"] - 2)],
                       fill=tuple(v // 2 for v in colour))
        score = 10 * len(gone)
        pf, (px, py), speed = L.POTION
        bat = self.bat_x(f)
        caught = None
        if f >= pf:
            fall = py + speed * (f - pf)
            if fall < L.BAT_Y - 4:
                at = (round(px - x0 - self.potion.width / 2), round(fall - y0 - self.potion.height / 2))
                img.paste(self.potion, at, self.potion)
            else:
                caught = pf + (L.BAT_Y - 4 - py) / speed
                score += 50
        wizard = self.wizard
        if caught is not None:                                   # the potion widens the stone a little
            grow = 1 + 0.3 * K.smooth((f - caught) / 6)
            wizard = wizard.resize((round(wizard.width * grow), wizard.height), Image.LANCZOS)
            if f - caught < 18:
                tag = "+50"
                self.font.draw(img, round(px - x0 - 8), round(L.BAT_Y - y0 - 40 - (f - caught)), tag, YELLOW)
        img.paste(wizard, (round(bat - x0 - wizard.width / 2), round(L.BAT_Y - y0 - wizard.height * 0.72)), wizard)
        at = self.orb_at(f)
        if at is None:
            at = (bat + 24, L.BAT_Y - L.ORB_R)
        img.paste(self.orb, (round(at[0] - x0 - self.orb.width / 2), round(at[1] - y0 - self.orb.height / 2)), self.orb)
        return S.to_palette(img, self.palette), score


class Screens:
    """The glass at each frame of the clip."""

    def __init__(self, made_up):
        self.game = Spellbrick(made_up)
        self.glass = S.Glass()

    def frame(self, f):
        return self.glass(self.raster(f))

    def raster(self, f):
        img = Image.new("RGB", K.RASTER_PX, TEAL)
        opened = L.OPEN_GROUP[1] <= f < L.MINIMISE[0]
        game_up = L.OPEN_GAME[1] <= f < L.CLOSE
        progman = window(img, L.PROGMAN, "Program Manager", active=not game_up, menu=["File", "Options", "Window",
                                                                                     "Help"])
        main = window(img, L.MAIN_GROUP, "Main", active=False, child=True)
        for k, (name, kind) in enumerate(MAIN_ICONS):
            cx, cy = main[0] + 44 + (k % 4) * 96, main[1] + 12 + (k // 4) * 70
            icon(img, kind, cx - 16, cy)
            title_under(img, name, cx, cy + 36)
        for name, (cx, cy) in L.GROUP_ICONS.items():
            if name == "Games" and opened:
                continue
            icon(img, "group", cx - 16, cy - 16)
            title_under(img, name, cx, cy + 20, selected=name == "Games" and 36 <= f < L.OPEN_GROUP[0])
        if opened:
            pressed = L.MINIMISE_CLICK <= f < L.MINIMISE_CLICK + L.CLICK
            group = window(img, L.GAMES_GROUP, "Games", active=not game_up, child=True, pressed_min=pressed)
            kinds = ("spellbrick", "kaleidrop", "hive", "pinball")
            for (name, (cx, cy)), kind in zip(L.GAME_ICONS, kinds):
                icon(img, kind, cx - 16, cy - 16)
                title_under(img, name, cx, cy + 20, selected=name == "Spellbrick" and f >= 78)
        icon_rect = lambda c: (c[0] - 16, c[1] - 16, c[0] + 16, c[1] + 16)   # noqa: E731
        if L.OPEN_GROUP[0] <= f < L.OPEN_GROUP[1]:
            zoom(img, icon_rect(L.GROUP_ICONS["Games"]), L.GAMES_GROUP,
                 (f - L.OPEN_GROUP[0]) / (L.OPEN_GROUP[1] - L.OPEN_GROUP[0]))
        if L.MINIMISE[0] <= f < L.MINIMISE[1]:
            zoom(img, L.GAMES_GROUP, icon_rect(L.GROUP_ICONS["Games"]),
                 (f - L.MINIMISE[0]) / (L.MINIMISE[1] - L.MINIMISE[0]))
        if L.OPEN_GAME[0] <= f < L.OPEN_GAME[1]:
            zoom(img, icon_rect(L.GAME_ICONS[0][1]), L.SPELL, (f - L.OPEN_GAME[0]) / (L.OPEN_GAME[1] - L.OPEN_GAME[0]))
        menu_open = L.PAUSE <= f < L.CLOSE
        if game_up:
            self.spellbrick(img, f, menu_open)
        self.pointer(img, f)
        return img

    def spellbrick(self, img, f, menu_open):
        client = window(img, L.SPELL, "Spellbrick", active=True, menu=["Game", "Skill", "Help"],
                        menu_open="Game" if menu_open else None)
        x0, y0, x1, y1 = L.FIELD
        d = ImageDraw.Draw(img)
        score = 0
        if f < L.START + L.CLICK:
            img.paste(self.game.title((f // 12) % 2 == 0), (x0, y0))
        else:
            field, score = self.game.play(f)
            img.paste(field, (x0, y0))
        d.rectangle([client[0], y1, client[2], client[3]], fill=GREY)
        d.line([(client[0], y1), (client[2], y1)], fill=BLACK)
        font = R.sans(13)
        font.draw(img, client[0] + 6, y1 + 2, f"Score: {score:04d}", BLACK)
        font.draw(img, client[0] + 130, y1 + 2, "Wall 1", BLACK)
        font.draw(img, client[0] + 220, y1 + 2, "Orbs: 3", BLACK)
        if menu_open:                                           # the Game menu, dropped down
            mx0, my0 = L.SPELL[0] + 5, L.FIELD[1] - 1
            items = [("New Game", "F2"), ("Pause", "F3"), None, ("Exit", "")]
            mx1, my1 = mx0 + 140, my0 + 8 + 20 * 3 + 8
            d.rectangle([mx0 + 2, my0 + 2, mx1 + 2, my1 + 2], fill=BLACK)
            d.rectangle([mx0, my0, mx1, my1], fill=WHITE, outline=BLACK)
            y = my0 + 4
            px, py = L.POINTER.at(f)
            for item in items:
                if item is None:
                    d.line([(mx0 + 1, y + 4), (mx1 - 1, y + 4)], fill=BLACK)
                    y += 8
                    continue
                lit = mx0 < px < mx1 and y <= py < y + 20 and f >= L.PAUSE + L.CLICK
                if lit:
                    d.rectangle([mx0 + 1, y, mx1 - 1, y + 19], fill=NAVY)
                R.system().draw(img, mx0 + 12, y + 2, item[0], WHITE if lit else BLACK)
                if item[1]:
                    R.system().draw(img, mx1 - 30, y + 2, item[1], WHITE if lit else BLACK)
                y += 20

    def pointer(self, img, f):
        x, y = (round(v) for v in L.POINTER.at(f))
        fx0, fy0, fx1, fy1 = L.FIELD
        if L.START <= f < L.PAUSE and fx0 <= x < fx1 and fy0 <= y < fy1:
            return                                               # hidden while the game's played
        if L.LOAD[0] <= f < L.OPEN_GAME[1]:
            bitmap(img, HOURGLASS, x - 6, y - 9)
        else:
            bitmap(img, ARROW, x, y)


def still(made_up):
    """Program Manager, the pointer at rest: the video's first frame."""
    return Screens(made_up).frame(0)
