"""The Mega Drive card's measurements for its pad, its lights and its clip, shared by mega_drive_print.py (which draws
the pad's printing and the cartridge's label) and mega_drive.py (which builds the card). Plain Python: Blender's Python
imports it too. The console's own measurements stay in mega_drive.py, whose build() the 32X's and Mega-CD's cards use.

Millimetres, as mega_drive.py's: x from the console's middle (left to right), y from its middle towards the back, z up
from the table; its front face at y = -106.

The control pad (the three-button one the Mega Drive came with), 165 mm wide, 98 deep and 26 high over its top (as
dimensions.com gives it, 165 x 98), its outline drawn from Evan-Amos's photographs on Wikimedia Commons (the European
Mega Drive with its pad, the Japanese one with its pad): two lobes, the top edge nearly straight, the front curving in
between the grips (PAD["points"], x across, y away from the player, smoothed); the D-pad's disc in the left lobe, A B C
in an arc rising to the right, START above them. It lies in front of the console at its left, its cable from its top to
its plug in CONTROL 1 (plugs.py's 9-pin D, black, as Sega's is).

The power switch slides to ON (SWITCH["on"], along -x) and the POWER light on the 16-BIT plate's white strip comes on
(LIGHT). The cartridge is mega_drive_cartridge.py's, with a made-up game, Odyssey, on its label.

The pad's printing is its own texture (PAD_ATLAS square, PAD_REGIONS): `pad` (the pad from above: MEGA DRIVE CONTROL
PAD, SEGA, START, A B C, TRIGGER, the D-pad's arrows), and swatches for the small parts. A region is (x, y, width,
height) in pixels.
"""

PAD = dict(points=[(82.0, 5.0), (78.0, 25.0), (66.0, 40.0), (45.0, 47.0), (20.0, 47.0), (0.0, 45.0), (-20.0, 47.0),
                   (-45.0, 47.0), (-66.0, 40.0), (-78.0, 25.0), (-82.0, 5.0), (-80.0, -18.0), (-70.0, -38.0),
                   (-52.0, -49.0), (-34.0, -46.0), (-20.0, -34.0), (0.0, -27.0), (20.0, -34.0), (34.0, -46.0),
                   (52.0, -49.0), (70.0, -38.0), (80.0, -18.0)],
           height=26.0, disc=((-46.0, 4.0), 21.0), dpad=(16.0, 9.0), abc=[(26.0, -12.0), (44.0, -4.0), (60.0, 9.0)],
           abc_r=8.0, start=((22.0, 25.0), (12.0, 5.5)), cable=(-14.0, 46.0), at=(-150.0, -176.0, 10.0))
PORT = dict(x=22.0, z=11.0, front=-106.0)                 # CONTROL 1, on the console's front
SWITCH = dict(on=-12.0)                                   # how far the power switch slides to ON (x)
LIGHT = dict(at=(33.4, -65.2), z=56.0, r=1.3)             # the POWER light on the plate's white strip
CART = dict(above=40.0, inserted=14.0)                    # how far over its seat it appears; how far it goes in

PAD_ATLAS = 512
PAD_REGIONS = dict(pad=(0, 0, 512, 304))
SWATCHES = dict(pad=(24, 340), button=(56, 340), black=(88, 340), lit=(120, 340), off=(152, 340), start=(184, 340))

FPS = 30
LENGTH = 240                 # 8 s
