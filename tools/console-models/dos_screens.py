"""The DOS card's screens (retro_pc_print.py draws its still with them, retro_pc_video.py its video), following its clip
frame for frame by the timing in dos_layout.py. Run with the system Python (Pillow, numpy).

- The commander: a two-panel file manager of the time in text mode, its blue panels framed in double lines, the
  active one listing C:\\GAMES (the made-up games' folders) and the other C:\\, the command line under them and the
  function keys' bar. `a:` and ENTER read drive A and list it; `c:` and ENTER go back.
- The loader: `rotor` and ENTER clear the screen; the game's lines come up as it checks the machine and loads.
- Rotorstorm, made up (tools/made-up-games), at VGA's 320 x 200 in one fixed palette of 256 colours: its title (its key
  art, its logo, PRESS ENTER blinking) fading in from black and out again as VGA games' palettes did; then the game,
  side-on: a stormy dusk sky over the jungle river (a Codex painting, paintings.py's dos_rotor_sky) scrolling slowly,
  the riverbank's jungle (dos_rotor_ground) scrolling past faster, the gunship (dos_rotor_sprites) climbing and diving
  as the arrows are held, a rocket for each press of the space bar, each meeting an enemy gunship flying in at its
  height, which bursts; the score and the fuel at the top.
- The goodbye screen: ESC, and the game's farewell in a box before the commander comes back.
"""

import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dos_layout as L  # noqa: E402
import raster_fonts as R  # noqa: E402
import retro_pc_layout as K  # noqa: E402
import retro_pc_screens as S  # noqa: E402

GAMES = [("DEEPFATH", "06-02-92", " 9:41a"), ("GHOULGUS", "10-14-91", " 7:02p"), ("HALCYON", "01-30-92", " 4:18p"),
         ("KALEIDRP", "11-20-91", " 3:05p"), ("SKYLANCE", "08-19-92", " 4:27p"), ("SPRINGHL", "05-07-92", "11:56a"),
         ("STORMFST", "09-23-92", " 8:30p")]
FILES = [("GAMES   ", "BAT", "412", "02-11-93", " 5:01p"), ("MENU    ", "EXE", "48,213", "02-11-93", " 5:00p")]
ROOT = [("DOS", "06-01-93", " 6:00a"), ("GAMES", "02-11-93", " 4:55p"), ("TEMP", "02-14-93", " 8:30a"),
        ("UTILS", "07-19-92", "12:12p")]
ROOT_FILES = [("AUTOEXEC", "BAT", "362", "02-11-93", " 5:04p"), ("COMMAND ", "COM", "54,645", "06-01-93", " 6:00a"),
              ("CONFIG  ", "SYS", "218", "02-11-93", " 5:04p")]
DISK = [("INSTALL ", "EXE", "23,456"), ("README  ", "TXT", "4,210"), ("ROTOR   ", "CFG", "128"),
        ("ROTOR   ", "DAT", "612,880"), ("ROTOR   ", "EXE", "148,372")]
KEYS = ("Help", "Menu", "View", "Edit", "Copy", "RenMov", "Mkdir", "Delete", "PullDn", "Quit")
READ = L.READ_A[0] + 10                                  # drive A's directory read: the panel lists it


def entry_row(name, ext, size, date, time):
    """A panel's row, 38 characters: its name and extension, its size (or SUB-DIR), its date and time, between the
    columns' lines."""
    return f"{name:<8} {ext:<3}\u2502{size:>9}\u2502{date:>8}\u2502{time:>6}"


def panel(screen, col, title, rows, cursor, active, info):
    """A panel at col: framed, titled, its columns' heads and lines, its rows, the cursor bar on one if it's active, and
    the line under them (info) with what's under the cursor."""
    screen.frame(col, 0, col + 39, 22, S.LIGHT_CYAN, S.BLUE, S.DOUBLE, f" {title} ",
                 (S.BLACK, S.CYAN) if active else (S.LIGHT_CYAN, S.BLUE))
    for k, head in ((5, "Name"), (16, "Size"), (24, "Date"), (32, "Time")):
        screen.put(col + 1 + k, 1, head, S.YELLOW)
    for row in range(1, 20):
        for c in (13, 23, 32):
            screen.put(col + c, row, "\u2502", S.LIGHT_CYAN)
    screen.put(col, 20, "\u255f" + "\u2500" * 38 + "\u2562", S.LIGHT_CYAN)
    for c in (13, 23, 32):
        screen.put(col + c, 20, "\u2534", S.LIGHT_CYAN)
    for k, (text, folder) in enumerate(rows):
        fg = S.WHITE if folder else S.LIGHT_CYAN
        bg = None
        if active and k == cursor:
            fg, bg = S.BLACK, S.CYAN
        screen.put(col + 1, 2 + k, text, fg, bg)
    screen.put(col + 1, 21, info.ljust(38)[:38], S.LIGHT_CYAN)


def commander(on_a, typed, prompt, cursor_on):
    """The commander: the left panel on C:\\GAMES or A:\\, the right on C:\\; the command line (prompt, then what's been
    typed) and the cursor after it; the function keys."""
    s = S.TextScreen()
    if on_a:
        rows = [(entry_row(n, e, z, "03-14-92", "10:12a"), False) for n, e, z in DISK]
        panel(s, 0, "A:\\", rows, 4, True, entry_row("ROTOR   ", "EXE", "148,372", "03-14-92", "10:12a"))
    else:
        rows = [(entry_row("..", "", "\u25baUP--DIR\u25c4", "", ""), True)]
        rows += [(entry_row(n, "", "\u25baSUB-DIR\u25c4", d, t), True) for n, d, t in GAMES]
        rows += [(entry_row(*f), False) for f in FILES]
        panel(s, 0, "C:\\GAMES", rows, 1, True, entry_row("DEEPFATH", "", "\u25baSUB-DIR\u25c4", "06-02-92", " 9:41a"))
    rows = [(entry_row(n, "", "\u25baSUB-DIR\u25c4", d, t), True) for n, d, t in ROOT]
    rows += [(entry_row(*f), False) for f in ROOT_FILES]
    panel(s, 40, "C:\\", rows, 0, False, "55,225 bytes in 3 files")
    line = prompt + typed
    s.put(0, 23, line, S.GREY)
    if cursor_on:
        s.cursor = (len(line), 23)
    col = 0
    for k, name in enumerate(KEYS):
        number = str(k + 1)
        s.put(col, 24, number, S.WHITE, S.BLACK)
        col += len(number)
        s.put(col, 24, name.ljust(6), S.BLACK, S.CYAN)
        col += 6
    return s


def loader(f):
    """The game's loader in text mode, f frames after the screen cleared."""
    s = S.TextScreen()
    lines = [(0, "ROTORSTORM  version 1.02", S.WHITE),
             (0, "Copyright (C) 1992 Ninebolt Software.  Published by Arcwave.", S.GREY),
             (4, "Checking for a VGA adapter ...... found, 256 colours", S.GREY),
             (8, "Checking for sound ............... Sound Blaster at 220h, IRQ 7", S.GREY),
             (13, "Loading ROTOR.DAT ", S.GREY)]
    row = 0
    for k, (at, text, fg) in enumerate(lines):
        if f >= at:
            s.put(0, row, text, fg)
        row += 2 if k in (1, 3) else 1
    if f >= 13:
        s.put(18, row - 1, "." * min(40, (f - 13) * 3), S.GREY)
    s.cursor = (0, row + 1) if f < 13 else None
    return s


class Rotorstorm:
    """The game at VGA's 320 x 200: its title, and its play, frame by frame."""

    def __init__(self, made_up):
        sky = S.painting("dos_rotor_sky")
        self.sky = sky.resize((round(sky.width * 200 / sky.height), 200), Image.LANCZOS)
        ground = S.keyed(S.painting("dos_rotor_ground"))
        self.ground = ground.resize((round(ground.width * 200 / ground.height), 200), Image.LANCZOS)
        heli, enemy, _jeep, boom = S.sprites("dos_rotor_sprites")
        self.heli = S.scaled(heli, 66)
        self.enemy = S.scaled(enemy, 56)
        self.boom = S.scaled(boom, 52)
        key = Image.open(os.path.join(made_up, "paintings", "rotorstorm", "keyart.png")).convert("RGB")
        k = 320 / key.width
        key = key.resize((320, round(key.height * k)), Image.LANCZOS)
        self.key = key.crop((0, (key.height - 200) // 2, 320, (key.height - 200) // 2 + 200))
        logo = Image.open(os.path.join(made_up, "library", "media", L.FLOPPY_LABEL["system"], "logos",
                                       L.FLOPPY_LABEL["stem"] + ".png")).convert("RGBA")
        self.logo = S.scaled(logo, 236)
        self.font = R.terminal(8, 8)
        title = self.key.copy()
        title.paste(self.logo, ((320 - self.logo.width) // 2, 36), self.logo)
        sample = [self.sky, self.ground.convert("RGB"), self.heli.convert("RGB"), self.enemy.convert("RGB"),
                  self.boom.convert("RGB")]
        self.palette = S.palette_of(sample)
        self.title_palette = S.palette_of([title])
        self.title_art = title
        self.targets = self._targets()

    def heli_y(self, f):
        for (f0, a), (f1, b) in zip(L.HELI, L.HELI[1:]):
            if f0 <= f < f1:
                t = (f - f0) / (f1 - f0)
                return a + (b - a) * t * t * (3 - 2 * t)
        return L.HELI[-1][1] if f >= L.HELI[-1][0] else L.HELI[0][1]

    NOSE, SPEED = (98.0, 8.0), 9.0                       # the rocket pods' mouth (x, below the middle) and speed

    def _targets(self):
        """Each rocket and the gunship it meets: (fired, hit, y): the enemy is where the rocket is at its hit frame."""
        return [(f, f + L.FLIGHT, self.heli_y(f) + self.NOSE[1]) for f in L.FIRE]

    def title(self, n, prompt):
        img = self.title_art.copy()
        if prompt:
            text = "PRESS ENTER TO START"
            self.font.draw(img, (320 - self.font.width(text)) // 2, 168, text, (255, 255, 120))
        self.font.draw(img, (320 - self.font.width("(C) 1992 ARCWAVE")) // 2, 184, "(C) 1992 ARCWAVE",
                       (200, 200, 200))
        return S.to_palette(img, self.title_palette)

    def play(self, f):
        """The game at frame f (from L.PLAY[0])."""
        t = f - L.PLAY[0]
        img = self.sky.crop((round(t * 0.45), 0, round(t * 0.45) + 320, 200))
        gx = round(t * 1.7)
        img.paste(self.ground.crop((gx, 0, gx + 320, 200)), (0, 0), self.ground.crop((gx, 0, gx + 320, 200)))
        d = ImageDraw.Draw(img)
        score = 4800
        for fired, hit, y in self.targets:
            x_hit = self.NOSE[0] + self.SPEED * (hit - fired)
            if f < hit:
                ex = x_hit + 1.6 * (hit - f)                 # the enemy flying in, bobbing
                ey = y + 2.0 * math.sin(f * 0.35)
                if ex - self.enemy.width / 2 < 330:
                    img.paste(self.enemy, (round(ex - self.enemy.width / 2), round(ey - self.enemy.height / 2)),
                              self.enemy)
                if f >= fired:
                    rx = self.NOSE[0] + self.SPEED * (f - fired)
                    d.line([(rx - 12, y), (rx, y)], fill=(255, 220, 120), width=2)
                    d.line([(rx - 26, y), (rx - 12, y)], fill=(170, 170, 170), width=1)
            elif f < hit + 14:
                k = 0.55 + 0.7 * min(1.0, (f - hit) / 4)
                boom = self.boom.resize((round(self.boom.width * k), round(self.boom.height * k)), Image.LANCZOS)
                if f - hit > 8:
                    boom.putalpha(boom.getchannel("A").point(lambda v, a=1 - (f - hit - 8) / 6: int(v * a)))
                img.paste(boom, (round(x_hit - boom.width / 2), round(y - boom.height / 2)), boom)
            if f >= hit + 2:
                score += 500
        y = self.heli_y(f) + 1.5 * math.sin(f * 0.5)
        climb = self.heli_y(f + 2) - self.heli_y(f - 2)
        heli = self.heli.rotate(-4.0 - climb * 0.9, resample=Image.BICUBIC, expand=True)
        img.paste(heli, (round(56 - heli.width / 2), round(y - heli.height / 2)), heli)
        d.rectangle([0, 0, 319, 11], fill=(0, 0, 0))
        self.font.draw(img, 4, 2, f"SCORE {score:06d}", (255, 220, 80))
        self.font.draw(img, 196, 2, "FUEL", (255, 255, 255))
        fuel = 0.82 - 0.0012 * t
        d.rectangle([232, 3, 316, 8], outline=(160, 160, 160))
        d.rectangle([234, 5, 234 + round(80 * fuel), 6], fill=(255, 210, 60) if fuel < 0.6 else (80, 220, 80))
        return S.to_palette(img, self.palette)


def goodbye():
    s = S.TextScreen()
    s.frame(6, 6, 73, 17, S.WHITE, S.BLUE, S.DOUBLE)
    s.put(26, 8, "Thanks for playing ROTORSTORM!", S.YELLOW)
    s.put(10, 10, "Thirty missions in four campaigns: jungle valleys, oil rigs and", S.WHITE)
    s.put(10, 11, "island fortresses. Rescue the hostages and fly them home before", S.WHITE)
    s.put(10, 12, "your fuel runs dry.", S.WHITE)
    s.put(19, 14, "Ninebolt Software \u00b7 Published by Arcwave", S.LIGHT_CYAN)
    s.put(31, 15, "(C) 1992 Arcwave", S.LIGHT_CYAN)
    return s


class Screens:
    """The glass at each frame of the clip."""

    def __init__(self, made_up):
        self.game = Rotorstorm(made_up)
        self.glass = S.Glass()

    def frame(self, f):
        return self.glass(self.raster(f))

    def raster(self, f):
        if f < L.LOADING[0] or f >= L.BACK:
            return self.commander(f).raster()
        if f < L.TITLE - 4:
            return loader(f - L.LOADING[0]).raster()
        if f < L.TITLE:
            return Image.new("RGB", (640, 480))              # the mode switch: a moment's black
        if f < L.PLAY[0]:
            n = f - L.TITLE
            prompt = f < L.START and (n // 12) % 2 == 0 or f >= L.START and f % 4 < 2
            fade = min(K.smooth(n / 6), 1 - K.smooth((f - L.START) / 6))
            return S.vga(S.faded(self.game.title(n, prompt), fade))
        if f < L.QUIT + 4:
            fade = min(K.smooth((f - L.PLAY[0] + 1) / 4), 1 - K.smooth((f - L.QUIT) / 4))
            return S.vga(S.faded(self.game.play(min(f, L.QUIT)), fade))
        return goodbye().raster()

    def commander(self, f):
        typed, prompt, since = "", "C:\\GAMES>", 0
        on_a = False
        for at, ch in L.TYPING:
            if at > f:
                break
            since = at
            if ch == "\n":
                on_a = typed.lower() == "a:" or (on_a and typed.lower() != "c:")
                prompt = "A:\\>" if on_a else "C:\\GAMES>"
                typed = ""
            else:
                typed += ch
        if f >= L.BACK and since < L.BACK:
            since = L.BACK
        listed = on_a and (f >= READ or f >= L.BACK)
        return commander(listed, typed, prompt, ((f - since) // L.BLINK) % 2 == 0)


def still(made_up):
    """The commander at C:\\GAMES, the cursor on: the video's first frame."""
    return S.Glass()(commander(False, "", "C:\\GAMES>", True).raster())
