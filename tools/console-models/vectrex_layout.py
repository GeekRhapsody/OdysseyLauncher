"""The Vectrex's measurements, shared by vectrex_print.py (which draws its printing, its tube's still and the pictures
of its video), vectrex_video.py (which draws the video) and vectrex.py (which builds it). Plain Python: Blender's
Python imports it too.

The Vectrex (1982) as Milton Bradley sold it in Europe, 248 mm wide, 292 deep and 362 high (the Museum of the Moving
Image's 9.75 x 11.5 x 14.25 inches), its controller in front of it on the table, a made-up game, Odyssey, in the side.
Millimetres: x from its middle (left to right), y back from the front edge of the screen hood's underside, z up from the
table. The rest was measured from the Bibliothèque nationale de France's photographs of an MB Vectrex on Wikimedia
Commons (straight on from the front, both sides and the back, the controller from above), scaled by its height, and
Evan-Amos's of a GCE one and its controller.

The console: the upper front box (the screen hood, its face leaning back FRONT_TILT degrees, the lid's logo strip over
it) standing 4.5 mm proud of the rest at its sides; behind it the housing of the tube's neck, its top falling to the
back; under the hood the base, set back, with the bay the controller docks in (the vents, the controller port, RESET and
the volume knob inside it) and the cartridge slot in its right side. In the hood: its walls narrowing back to the bezel
and the tube's face. The controller: a box with the joystick at its left and four buttons, MB's white rings round them,
its coiled cord running into the bay.

Two frames: the console's (above) and the front face's (u across, v up the leaning face from the hood's underside, w
into the box). One texture (ATLAS square, REGIONS): the controller's face (`pad`), the bay's back wall (`bay`), the
cartridge's label (`cart`), the lid's logo strip (`strip`), and swatches. A region is (x, y, width, height) in pixels. The tube's glass has its own, vectrex_screen.png (VIDEO_PX): the power-on
screen, the still of the model's `video` material, and the first and last frame of the card's video
(vectrex_video.py), which the launcher plays on the glass while the card is focused.

The `focused` clip's timing, in frames at FPS, is here so that the video follows the clip (vectrex.py) frame for frame:
the launcher starts the video with the clip, and again each time the clip loops. The overlay is the video's: it slides
down into place over the glass and back up and out, as a real one slides into the frame over the screen, so nothing
but the cartridge and the controller moves on the model, as on the other cards whose screens are videos.
"""

import math

from retro_pc_layout import phase, smooth

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 248.0, 292.0, 362.0
FEET = 5.0                       # the feet's height: the body stands on them
HOOD_BOTTOM = 92.5               # the hood's underside, over the base
FRONT_TILT = 5.4                 # degrees the front face leans back from upright
SEAM = 130.0                     # how far back the proud front box goes
STEP = 4.5                       # how far its sides stand out of the rest's

# The side profile (y, z) round the whole console, at its narrower width: the hood's front up to the lid, the top, the
# front box's back face, the tube housing's falling top, the back, the underside and the base's front.
PROFILE_TOP = [(97.0, 361.0), (150.0, 361.0), (186.0, 358.5)]       # through the top, between the rounded corners
TOP_FRONT = dict(r=8.0)          # the lid's front edge, rounded
TOP_BACK = dict(r=10.0, at=202.0)                                    # the front box's back, at y = at
HOUSING = dict(front=310.0, back=278.5, y=DEPTH - 3.0)               # the housing's top, front and back heights
BACK = dict(r=19.0)              # the back's bottom edge
BASE = dict(front=23.0, r=20.0, half=WIDTH / 2 - STEP)              # the base's front, its bottom edge

# The front face's (u, v): the hood's opening and its back (w deep), the tube's face on it, the lid's strip.
HOOD = dict(front=(226.0, 223.0, 12.4), back=(168.0, 200.0, 20.5), r=(10.0, 7.0), depth=46.0)  # (w, h, v of bottom)
TUBE = dict(size=(149.0, 187.0), v=26.5, r=16.0, bulge=5.0, w=45.6)  # its face's size, the bottom's v, the bulge,
                                 # its edge's w (just in front of the hood's back wall)
STRIP = dict(u=(-118.0, 118.0), v=(248.0, 262.0), depth=0.8)          # sunk into the lid's face

# The base's bay, the cartridge slot (on the right side) and its frame.
BAY = dict(x=(-105.0, 105.0), z=(11.0, 87.0), depth=40.0)
RESET = dict(at=(76.0, 32.0), r=5.0, height=4.0)
VOLUME = dict(at=(94.0, 32.0), r=6.5, height=6.0)
PORT = dict(at=(84.0, 66.0), size=(30.0, 12.0))                      # on the bay's back wall (x, z)
SLOT = dict(y=(97.0, 174.0), z=(30.0, 60.0), frame=4.0, lip=2.0)
CART = dict(length=105.0, width=75.0, thickness=19.0, out=44.0, travel=150.0, label=46.0)   # it goes in
                                 # `length - out`; its label covers the outer `label` of its top

# The controller, on the table in front: its box and where it lies, the joystick and the buttons on its face (from
# its middle, x across, y back from its front edge).
PAD = dict(size=(208.0, 76.0, 34.0), r=6.0, at=(-22.0, -168.0), turn=10.0)
STICK = dict(at=(-78.0, 40.0), ring=15.0, r=3.0, height=20.0, knob=(4.6, 9.0), tilt=16.0)
BUTTONS = dict(x=[-36.0, -6.0, 24.0, 54.0], y=40.0, r=7.4, height=4.0, ring=10.0, press=2.5)
NOTCH = dict(x=16.0, size=(20.0, 12.0))                              # the cord's notch in its back edge
CORD = dict(r=4.5, wire=1.5, pitch=4.2)                              # the coil's radius, its wire's, its pitch

COLOURS = dict(case="#2E2F33", bezel="#3B3C40", hood="#26272A", dark="#0B0B0D", silver="#B9BCC2", key="#18181A",
               glass="#FFFFFF", print="#FFFFFF")

# The tube's pictures, in the tube's proportions, even sides for H.264: the video's frames and the glass's still. About
# a texel a pixel on the details screen at 1080p, and minified as little as can be in the grid, where the launcher draws
# a card's video without mipmaps.
VIDEO_PX = (256, 320)
REGIONS = dict(pad=(264, 328, 512, 187), cart=(784, 328, 240, 200), bay=(264, 523, 420, 152), strip=(0, 684, 968, 56))
SWATCHES = dict(case=(712, 560), bezel=(744, 560), hood=(776, 560), dark=(808, 560), silver=(840, 560),
                key=(872, 560))

# ---- The focused clip, in frames at FPS ------------------------------------------------------------------------------
FPS = 30
LENGTH = 240                 # 8 s
CART_SHOW = (12, 17)         # the cartridge grows in out to the right of its slot
CART_IN = (18, 36)           # it slides in, and nudges as it seats
CART_OUT = (196, 214)        # it slides out
CART_GONE = (214, 220)       # and shrinks away
OVERLAY_IN = (46, 60)        # the overlay slides down into place over the power-on screen
ON = 64                      # the tube flickers on (FLICKER) behind it, and the game starts
FLICKER = (0.6, 0.0, 0.35)   # how lit the tube is on the first frames after it comes on
PLAY = (67, 168)             # the game: the joystick rocks, the ship following it
SHOTS = (84, 101, 134)       # button 1 pressed: a bolt each, as the ship turns at an end of its weave, meeting a rock
SHIELDS = (118, 151)         # button 4 pressed: the ship's shield
PRESS = 5                    # frames a button takes to go down and come up
OFF = (162, 168)             # the picture fades, and the tube's off from 168
OVERLAY_OUT = (176, 190)     # the overlay slides up and out
LOGO = (224, 236)            # the cartridge out, the tube flickers on to the power-on screen, its rays rising


def stick(f):
    """The joystick's lean at frame f, in degrees (roll: its top to the right; pitch: towards the player), rocking
    while the game plays. The ship moves as it rolls."""
    if not PLAY[0] <= f < PLAY[1]:
        return 0.0, 0.0
    t = (f - PLAY[0]) / FPS
    tilt = STICK["tilt"] * smooth(phase(f, PLAY[0], PLAY[0] + 7)) * (1 - smooth(phase(f, PLAY[1] - 7, PLAY[1])))
    return tilt * math.sin(2 * math.pi * 0.9 * t), 0.5 * tilt * math.sin(2 * math.pi * 1.7 * t)


def pressed(f, f0):
    """How far down a button pressed at f0 is at frame f, 0 to 1."""
    return math.sin(math.pi * phase(f, f0, f0 + PRESS)) if f0 <= f < f0 + PRESS else 0.0
