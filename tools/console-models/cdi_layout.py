"""The Philips CD-i 220's measurements, shared by cdi_print.py (which draws its printing and its display) and cdi.py
(which builds it). Plain Python: Blender's Python imports it too.

The CD-i 220, one of Philips's consumer 200 series of CD-i players, a grey hi-fi box: 420 x 286 x 90 mm (HiFi Engine's figures, its feet
included), and its gamepad in front of it. Millimetres: x from its middle (left to right), y back from its front face,
z up from the table. The rest was measured from photographs on Wikimedia Commons (Evan-Amos's views of it from the
front left and right and with its gamepad, a view of it from in front, the gamepad from above), scaled by its width.

The body: a box on four feet, the vents in its top at the back right. Its front, left to right: the disc tray's door
(the dots and the Compact Disc Interactive logo on it, PHILIPS on the strip under it), the panel with PREVIOUS, PLAY,
NEXT and OPEN, the display's smoked window (it pulls down: the gamepad's socket is behind it), and the panel with
ON/OFF, PAUSE and STOP. The tray: its door, and behind it the platform the disc lies in, sliding out of the body's
opening. The gamepad (in front of the display, clear of the tray's way): the CD-i's own, its outline (PAD_OUTLINE) a wide arch, a raised plate on it, the thumbpad in its
ring at the left, three buttons in a slanted recess at the right.

One texture (ATLAS square, REGIONS): `front` (the front seen from in front: the door's dots and logo, PHILIPS, the
buttons' names, the lines between the panels), `display` (the window: smoked red, the display's segments unlit, the
model's name and PULL TO OPEN), `display_disc` and `display_play` (the window lit: the disc read, CD-i's logo; and
playing, the track and its time), `disc_top` (the disc's label: a made-up game, Odyssey), `pad` (the gamepad's top:
CD-i, the thumbpad's marks, the buttons' dots, SPEED), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 420.0, 286.0, 88.0
FOOT = 8.0                                                  # the feet's height: the body stands on them
FEET = dict(x=(-196.0, -166.0, 166.0, 196.0), y=((14.0, 34.0), (252.0, 272.0)))   # each foot's x0, x1; y0, y1

# The front, (x, z): the tray's door, the panels, the display's window; the strip along the top.
DOOR = dict(x=(-206.4, -28.7), z=(25.6, 78.0), inset=1.5)
OPENING = dict(x=(-204.0, -31.0), z=(27.0, 76.0), depth=150.0)     # the body's opening behind the door
MIDDLE = dict(x=(-27.0, 20.0))
WINDOW = dict(x=(21.5, 165.0), z=(24.0, 74.0), out=1.0)
RIGHT_PANEL = dict(x=(167.0, 208.0))
TOP_STRIP = 78.0                                            # the line along the front under the top strip

# The buttons, (name, x0, x1, z0, z1), each 2 mm proud of the front.
BUTTONS = [("previous", 0.0, 11.0, 58.0, 62.5), ("play", 0.0, 11.0, 46.0, 50.5), ("next", 0.0, 11.0, 34.0, 38.5),
           ("open", -21.0, -10.0, 34.0, 38.5), ("onoff", 172.0, 204.0, 58.0, 64.0), ("pause", 172.0, 184.0, 26.0, 30.5),
           ("stop", 192.0, 204.0, 26.0, 30.5)]
BUTTON_OUT = 2.0

# The tray: its door, and behind it the platform (x0, x1, its depth, its top) with the disc's recess; how far it
# slides out.
PLATFORM = dict(x=(-195.0, -40.0), depth=140.0, top=46.0, thickness=6.0)
DISC = dict(diameter=120.0, hole=15.0, thickness=1.2)
RECESS = dict(centre=((-195.0 - 40.0) / 2, 72.0), diameter=122.0, depth=1.6)   # (x, y back from the door's front)
TRAY_OUT = 128.0

# The vents in the top: three columns of slots running across, at the back right.
VENTS = dict(columns=[(104.0, 128.0), (136.0, 160.0), (168.0, 192.0)], y=(152.0, 268.0), count=24, width=1.8, depth=1.5)

# The gamepad: its outline in its own plan (x across, y away from the player), its middle where AT puts it, turned by
# TURN degrees; its base, the plate on it, the thumbpad and the buttons.
PAD_OUTLINE = [(60.0, 2.0), (75.0, 8.0), (88.0, 25.0), (95.0, 45.0), (94.0, 62.0), (88.0, 78.0), (75.0, 90.0),
               (55.0, 97.0), (25.0, 100.0), (0.0, 101.0), (-25.0, 100.0), (-55.0, 97.0), (-75.0, 90.0),
               (-88.0, 78.0), (-94.0, 62.0), (-95.0, 45.0), (-88.0, 25.0), (-75.0, 8.0), (-60.0, 2.0), (-46.0, 5.0),
               (-36.0, 15.0), (-24.0, 30.0), (-12.0, 38.0), (0.0, 40.0), (12.0, 38.0), (24.0, 30.0), (36.0, 15.0),
               (46.0, 5.0)]
PAD = dict(at=(96.0, -112.0), turn=-9.0, base=14.0, plate=(7.0, 22.0),    # its base's height; the plate's inset, top
           dpad=dict(at=(-50.0, 62.0), ring=22.0, disc=16.0, height=5.0),
           buttons=dict(at=[(34.0, 48.0), (52.0, 55.0), (70.0, 62.0)], r=8.0, height=4.0, margin=2.5))

COLOURS = dict(case="#5D5E61", button="#4C4D50", black="#111113", glass="#FFFFFF")

REGIONS = dict(front=(0, 0, 1024, 195), display=(0, 203, 300, 105), display_disc=(308, 203, 300, 105),
               display_play=(616, 203, 300, 105), disc_top=(0, 316, 256, 256), pad=(264, 316, 380, 202))
SWATCHES = dict(case=(680, 340), button=(712, 340), black=(744, 340), silver=(776, 340), dark=(808, 340))

FPS = 30
LENGTH = 240                 # 8 s
