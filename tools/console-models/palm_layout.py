"""The Palm OS card's measurements, shared by palm_print.py (which draws its printing and screens) and palm.py (which
builds it). Plain Python: Blender's Python imports it too.

The PalmPilot (U.S. Robotics, 1996): 81 x 117 x 17 mm (Wikipedia, the Centre for Computing History), its parts placed
from a photograph of its face square on (0.0622 mm a pixel); its LCD 160 x 160 in four greys; its stylus about 110 mm.
Millimetres in handheld.py's frame: x from its middle (left to right), z up from its bottom edge, y back from its face.

Its face: charcoal, Palm Pilot and U.S.Robotics in white along the top; one glass window (WINDOW) holding the LCD above
the silkscreened Graffiti area (its four round icons and the writing box); the button row (BUTTONS: Date Book, Address,
the scroll rocker's two bars, To Do List, Memo Pad), the teal power key at the left edge (POWER); the lower lip, a
shallow curved step across under the buttons (LIP). The stylus lives in its silo along the right edge (STYLUS).

Two textures: the print (ATLAS square, REGIONS: `face` from the front, and swatches) and the screens (MEDIA_REGIONS:
the application launcher, a made-up game's title and two moments of it, in the LCD's four greys). A region is (x, y,
width, height) in pixels.
"""

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 81.0, 117.0, 17.0
HALF = WIDTH / 2
CORNER = 6.0
SPAN = (-HALF, HALF, 0.0, HEIGHT)
WINDOW = dict(rect=(-30.0, 30.0, 32.0, 107.0), lcd=(57.0, 55.0), lcd_at=(0.0, 79.0), r=2.0)
BUTTONS = dict(apps=[(-25.5, "date"), (-11.5, "address"), (15.0, "todo"), (29.5, "memo")], z=20.0, r=4.5,
               rocker=(0.0, 22.5, 17.0), bar=(9.0, 3.0))
POWER = dict(at=(-HALF + 1.2, 20.0), size=(4.5, 6.0))
LIP = dict(ends=10.5, middle=8.0, step=1.2)               # the lip's top edge's height at the ends and the middle
STYLUS = dict(x=HALF - 3.4, y=10.0, r=2.5, length=110.0, cap=8.0)
SILO = dict(r=3.0)

PALETTE = ["#22241E", "#4E5446", "#7A8270", "#A9B4A0"]     # the LCD's four greys, darkest first
MADE_UP = ("Banners of Valour (Europe)", "megadrive")
APPS = ["Banners", "Date Book", "Address", "To Do", "Memo Pad", "Calc", "Expense", "Mail", "HotSync", "Prefs",
        "Security", "Games"]
TAPS = [(-16.0, 96.0), (-4.0, 72.0), (10.0, 84.0), (-12.0, 66.0)]   # where the stylus touches: the launcher, then play

COLOURS = dict(body="#323136", lip="#201D1B", lcd="#9AA59A", silk="#8B8D88", ink="#5B575C", button="#2C2C31",
               teal="#22A596", white="#EDEDEA", stylus="#1A1A1E", gold="#E0A040")

REGIONS = dict(face=(0, 0, 486, 702))
SWATCHES = {name: (520 + 32 * (k % 10), 20 + 32 * (k // 10)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(launcher=(0, 0, 320, 320), title=(328, 0, 320, 320), game1=(656, 0, 320, 320),
                     game2=(0, 328, 320, 320))

FPS = 30
LENGTH = 240                 # 8 s
