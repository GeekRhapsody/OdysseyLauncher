"""The Nintendo Switch's measurements, shared by switch_print.py (which draws its printing) and switch.py (which builds
and maps it). Plain Python: Blender's Python imports it too.

Millimetres, seen from the front: x from the middle (left to right), z up from the bottom. The console with its
Joy-Con is 239 x 102 x 14 mm; the positions were measured off a head-on photo.

switch_print.png is two planar projections, one above the other, each covering PRINT_X by PRINT_Z (a little more than
the console, so filtering never brings in the other half): the front in the top half, and the back in the bottom half,
seen from behind (mirrored left to right).
"""

WIDTH, HEIGHT, DEPTH = 239.0, 102.0, 14.0
TABLET = 86.5                         # the tablet's half width; each Joy-Con is the rest, 33 mm wide

PRINT_SIZE = (2048, 2048)
PRINT_X = (-120.5, 120.5)
PRINT_Z = (-3.0, 105.0)

GLASS = (81.3, 3.5, 98.0, 2.5)        # the black glass: half its width, its bottom, its top, its corners' radius
SCREEN = (68.6, 12.4, 89.6)           # the 6.2-inch 16:9 screen: half its width, its bottom, its top

# The Joy-Con's controls: centres (x, z). The right Joy-Con's X, Y, A and B are round ABXY; the left's direction
# buttons round DPAD, in the same pattern (up, left, right, down).
BUTTON_R = 3.7
PATTERN = 7.7                         # how far each of the four buttons is from their middle
LEFT_STICK = (-102.0, 75.1)
DPAD = (-102.0, 47.3)
CAPTURE = (-96.3, 28.5)               # a rounded square, 6 mm
MINUS = (-91.9, 90.7)
RIGHT_STICK = (102.0, 48.2)
ABXY = (101.7, 76.0)
HOME = (96.4, 29.1)
PLUS = (91.5, 91.4)
STICK_R = 7.9                         # the stick's cap
STICK_WELL = 9.6                      # the dark opening round the stick
HOME_R, HOME_RING = 2.9, 3.9


def four(centre):
    """The four buttons round a middle: up, left, right, down."""
    x, z = centre
    return [(x, z + PATTERN), (x - PATTERN, z), (x + PATTERN, z), (x, z - PATTERN)]
