"""The Android card's measurements, shared by android_print.py (which draws its printing and screens) and android.py
(which builds it). Plain Python: Blender's Python imports it too.

An unbranded Android phone of the 2020s, after the mid-range slabs (a Galaxy A55 is 161.1 x 77.4 x 8.2 mm): 77 x 161 x
8.2 mm, its 6.6-inch screen about 70 x 152 mm under the glass, a punch hole for its camera at the top; on its back three
lenses in a column near its top right corner (seen from the front), each its own raised ring, and the flash; the volume
rocker and the power key on its right side. It stands on a plain desk stand. Millimetres in handheld.py's frame: x from
its middle (left to right), z up from its bottom edge, y back from its face.

Two textures: the print (ATLAS square, REGIONS: `face`, `back`, and swatches) and the screens (MEDIA_REGIONS: the lock
screen, the home screen of made-up apps with a made-up game among them, and the game's title and two moments of it,
drawn turned for the phone held landscape). A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 77.0, 161.0, 8.2
CORNER = 10.0
SPAN = (-WIDTH / 2, WIDTH / 2, 0.0, HEIGHT)
SCREEN = dict(size=(70.0, 152.0), at=(0.0, 80.5), r=8.0, pixels=(236, 512))
PUNCH = dict(at=(0.0, 153.5), r=2.0)
LENSES = dict(x=WIDTH / 2 - 12.0, z=[HEIGHT - 12.0, HEIGHT - 27.0, HEIGHT - 42.0], r=6.5, proud=1.5, glass=3.4)
FLASH = dict(at=(WIDTH / 2 - 24.0, HEIGHT - 19.0), r=1.6)
KEYS = dict(volume=(103.5, 124.0), power=(86.0, 96.0), height=2.5, proud=0.6)
STAND = dict(base=(90.0, 62.0, 5.0), lip=(80.0, 5.0, 9.0), rest=(70.0, 5.0, 96.0), lean=16.0, gap=1.0)
LANDSCAPE_DROP = (HEIGHT - WIDTH) / 2                      # how far the phone's middle drops when it's turned landscape

MADE_UP = ("Whirligig Karts (Europe)", "n64")
APPS = ["Phone", "Messages", "Camera", "Photos", "Music", "Maps", "Mail", "Clock", "Files", "Weather", "Store",
        "Whirligig"]

COLOURS = dict(glass="#050412", frame="#3A3C40", back="#2B2D31", metal="#D8D8DA", lens="#292927", key="#4A4C50",
               stand="#5A5C60", flash="#E8E0C0")

REGIONS = dict(face=(0, 0, 308, 644), back=(316, 0, 308, 644))
SWATCHES = {name: (650 + 32 * (k % 8), 20 + 32 * (k // 8)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(lock=(0, 0, 236, 512), home=(244, 0, 236, 512), title=(488, 0, 236, 512),
                     game1=(732, 0, 236, 512), game2=(0, 512, 236, 512))

FPS = 30
LENGTH = 240                 # 8 s
