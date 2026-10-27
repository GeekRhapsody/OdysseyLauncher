"""The Symbian card's measurements, shared by symbian_print.py (which draws its printing and screens) and symbian.py
(which builds it). Plain Python: Blender's Python imports it too.

An unbranded two-way slider phone of the late 2000s, the kind Symbian games were played on, after the Nokia N95 (2007):
53 x 99 x 21 mm closed (GSMArena), its face sliding up about 29 mm to show the keypad; its screen 2.6 inches, 240 x 320.
Millimetres in handheld.py's frame: x from its middle (left to right), z up from its bottom edge, y back from its face.

Two halves: the face (FACE_DEPTH thick: silver, plum at its edges: the earpiece and the front camera at its top, the
screen's black window, the navi cluster at its bottom: the chrome ring round the five-way key, the menu and multimedia
keys, the soft keys, call and end, edit and C) and the back half behind it (plum: on its front the twelve silver keys,
shown when the face slides up, and the media keys' black strip at its top, shown when it slides down; on its back the
camera's silver ring).

Two textures: the print (ATLAS square, REGIONS: `face` (the face's front), `keypad` (the back half's front), `back`,
and swatches) and the screens (MEDIA_REGIONS: the standby screen, the menu with a made-up game among its icons, the
game's title and two moments of it). A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, HEIGHT, DEPTH = 53.0, 99.0, 21.0
FACE_DEPTH = 10.0
SPAN = (-WIDTH / 2, WIDTH / 2, 0.0, HEIGHT)
CORNER = 7.0
SLIDE = 29.0                  # how far the face slides up to show the keypad
WINDOW = dict(size=(42.0, 57.0), at=(0.0, 60.0))
SCREEN = dict(size=(40.0, 53.0), pixels=(240, 320))
NAVI = dict(at=(0.0, 12.0), size=(44.0, 18.0), pad=13.0, centre=5.0)
EARPIECE = dict(at=(0.0, 95.4), size=(9.0, 2.0))
CAMERA = dict(at=(14.5, 95.4), r=2.5)
KEYPAD = dict(rows=[25.5, 19.6, 13.7, 7.8], cols=[-13.5, 0.0, 13.5], key=(12.5, 5.2))
LEGENDS = [["1", "2 abc", "3 def"], ["4 ghi", "5 jkl", "6 mno"], ["7 pqrs", "8 tuv", "9 wxyz"], ["* +", "0 _", "# ⇧"]]
MEDIA_KEYS = dict(z=(84.0, 96.0), icons=["⏭", "⏯", "⏹", "⏮"])
LENS = dict(at=(10.0, 80.0), r=9.0, proud=1.6)

MADE_UP = ("Halcyon Strike (Europe)", "megadrive")
APPS = ["Messaging", "Contacts", "Web", "Gallery", "Music", "Maps", "Camera", "Calendar", "Games", "Halcyon",
        "Settings", "Help"]

COLOURS = dict(silver="#C9C7C2", plum="#4A373A", key="#C2BDB4", ink="#1E1E22", window="#0C0B0A", chrome="#A8A49A",
               blue="#2A7CC0", green="#1A9A6A", red="#C0392B", black="#2E2E2E", white="#F0F0F0")

REGIONS = dict(face=(0, 0, 318, 594), keypad=(326, 0, 318, 594), back=(652, 0, 318, 594))
SWATCHES = {name: (40 + 32 * (k % 11), 640 + 32 * (k // 11)) for k, name in enumerate(COLOURS)}
MEDIA_REGIONS = dict(standby=(0, 0, 240, 320), menu=(248, 0, 240, 320), title=(496, 0, 240, 320),
                     game1=(744, 0, 240, 320), game2=(0, 328, 240, 320))

FPS = 30
LENGTH = 240                 # 8 s
