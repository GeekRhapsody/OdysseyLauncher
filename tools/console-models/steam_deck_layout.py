"""The Steam Deck's measurements, shared by steam_deck_print.py (which draws its printing and its screens) and
steam_deck.py (which builds it). Plain Python: Blender's Python imports it too.

The first Steam Deck (the LCD model, 2022), 298 x 117 x 49 mm (Valve's figures, the 49 with its thumbsticks), standing
up in handheld.py's frame: x from the middle (left to right, as the face is seen), z up from the bottom edge, y back
from the face. Its shape is measured from Valve's own drawings on steamdeck.com's tech specs page, three orthographic
views of the shell (the face, the top edge and the back, read at 5.90 px a millimetre; drawn for the OLED model, whose
shell is the LCD model's), and from GIGAZINE's photographs: its appearance review (2022-11-24: the face, the back, the
top and bottom edges, the corners close up), which also gives the colours, and its comparison with the Switch
(2022-12-14), whose photograph of the end gives the grips' profile.

The body is one shell, its outline from the face a rounded rectangle (TOP_CORNER, BOTTOM_CORNER: each corner a
superellipse, a straight bottom edge), only 19.3 mm deep behind the screen (DEPTH), with a grip at each end reaching
38.1 mm back. Seen from above, the end's outline is traced from the top edge's drawing: the face's edge rounding back
to the end (FRONT_EDGE), the end rounding over to the grip's crest, about 20 mm in from the end, and a gentle flank
down to the back (LOBE). The gentle flank is the grip's near the bottom, where it sweeps in as it rounds over (the
back's seam follows it, and the end's photograph limits it to there); higher up, where the back buttons are, the flank
is steep (FLANK), the buttons standing on the flat back right beside it, as the photographs of the back show. Seen
from the end, the grip rounds over from the bottom edge (GRIP_RISE) and again at its top (GRIP_TOP), down into the
notch under the trigger. The face's outer edges are rounded broadly (FRONT_EDGE), and below the seam that runs round
each grip (SEAM_FRONT) the face rolls back into the grip (ROLL). At each top corner the bumper (L1, R1) lies over the
top edge and wraps round the corner, 0.85 mm proud along the top (BUMPER), and behind it the trigger (L2, R2) is a
rounded hump (TRIGGER_PROFILE, TRIGGER_BACK).

Checked against the drawings by the overlap of the model's silhouettes with theirs, seen straight on from the front,
from above and from behind (each about 0.99), and with the photograph of the end (about 0.89, the photograph's
perspective and the shadow under the grips taking the rest).

Two textures. `steam_deck_print.png` (ATLAS square, REGIONS): `front` (the face seen square on, the buttons' and the
sticks' tops where they stand), `rear` (the back seen from behind, its x the face's negated), `top` (the top edge seen
from above, the face towards the region's bottom), `bottom` (the bottom edge seen from below, the face towards the
region's top), and the swatches the other faces take their colour from. `steam_deck_screens.jpg` (SCREENS): the
display's four states at 960 x 600 (16:10). A region is (x, y, width, height) in pixels, and the box of millimetres it
covers, (x0, x1, z0, z1) or, for the edges, (x0, x1, y0, y1).
"""

ATLAS = 1024
FPS = 30
LENGTH = 180                        # the clip: 6 s

# ---- The shell -------------------------------------------------------------------------------------------------------
WIDTH, HEIGHT = 298.8, 116.4        # the face's outline (Valve's 117 is to the bumpers' tops)
HALF = WIDTH / 2
DEPTH = 19.3                        # the back behind the screen

# The face's outline: a rounded rectangle, each corner a quarter superellipse (across, up, exponent).
TOP_CORNER = (25.0, 24.0, 2.4)
BOTTOM_CORNER = (40.0, 34.0, 2.5)

# The right end seen from above (x, y), mirrored for the left: the face's edge rounding back to the end (FRONT_EDGE),
# then the grip's outline round its crest and down its inner flank to the back (LOBE).
FRONT_EDGE = [(138.8, 0.0), (140.3, 0.3), (141.8, 0.8), (143.3, 1.5), (144.3, 2.2), (145.4, 3.1), (146.4, 4.1),
              (147.4, 5.3), (147.9, 6.1), (148.4, 7.1), (148.9, 8.3), (149.4, 10.3)]
LOBE = [(149.4, 10.3), (149.4, 13.0), (148.9, 16.9), (148.4, 20.7), (147.9, 24.6), (147.4, 27.5), (146.4, 30.2),
        (145.4, 31.9), (144.3, 33.0), (143.3, 34.2), (142.3, 34.9), (140.8, 35.9), (139.3, 36.6), (137.7, 37.3),
        (135.7, 37.6), (133.2, 37.9), (130.6, 38.1), (127.1, 38.1), (125.5, 37.8), (124.0, 37.3), (122.5, 36.6),
        (121.0, 35.8), (119.4, 34.6), (117.9, 32.9), (116.4, 30.7), (114.9, 28.3), (113.3, 26.1), (111.8, 23.7),
        (110.3, 21.7), (108.8, 20.3), (107.8, 19.8), (106.8, 19.5), (105.8, 19.3)]
CREST = 17                         # LOBE's index of the crest's inner end
# The grip's inner flank where the back buttons are (the right one's), from the crest's inner end down to the back:
# steep, where LOBE's from the crest on is gentle. LOBE's is the grip's near the bottom, where it sweeps in as it rounds
# over (the back's seam follows it): the top edge's drawing sees it, and the end's photograph limits it to that height.
FLANK = [(127.1, 38.1), (125.7, 37.2), (124.7, 35.3), (123.8, 32.5), (123.0, 29.0), (122.1, 25.0), (121.3, 22.0),
         (120.0, 20.2), (118.5, 19.5), (117.0, 19.3)]
STEEPEN = (13.0, 22.0)             # the flank goes from LOBE's to FLANK's between these heights
BACK_CORNER = 6.0                  # where there's no grip, the back's corner at the end rounds over this far
SQUEEZE = 100.0                    # where the outline narrows at the corners, the shell's ends move in beyond here
# The grips round over from the bottom edge, from GRIP_RISE's first height to its second (its depth there a power,
# the third, of the way up: the end's photograph); and over again at their tops (GRIP_TOP: from its first height to
# its second they sink to the notch under the trigger, its third of their depth, and from its fourth height to its
# fifth into the trigger's piece).
GRIP_RISE = (1.2, 16.0, 0.6)
GRIP_TOP = (68.0, 84.0, 0.45, 93.0, 97.0)
# The face's and the back's edges along the top and the bottom edge round over this far (the back's from the top
# edge's seam).
FRONT_ROUND, BACK_ROUND = 2.8, 5.3

# The seam round each grip on the face (the right one; mirrored), from the outline to the bottom edge: below it the
# face rolls back into the grip, ROLL at the end.
SEAM_FRONT = [(149.4, 74.2), (135.5, 74.2), (132.0, 72.6), (130.6, 69.1), (130.3, 56.0), (129.9, 44.7),
              (101.8, 0.0)]
ROLL = 5.0
# The same seam on the back (the right grip's, seen from behind; x as the face's).
SEAM_BACK = [(149.4, 75.2), (129.6, 75.2), (127.5, 73.2), (127.0, 70.0), (127.0, 21.8), (124.0, 13.0),
             (117.0, 5.5), (110.0, 1.8), (104.4, 0.0)]

# ---- The face (x, z) -------------------------------------------------------------------------------------------------
GLASS = dict(x=0.0, z=58.0, width=172.3, height=106.8, r=2.0)      # the black glass round the display
SCREEN = dict(x=0.0, z=58.0, width=150.8, height=94.2)             # the LCD: 7 inches, 1280 x 800
DPAD = dict(x=-130.6, z=97.3, span=22.6, arm=7.1, height=2.6)
ABXY = dict(x=131.3, z=97.2, reach=8.8, r=4.65, height=2.6)
FACE_BUTTONS = [("y", 90.0), ("b", 0.0), ("a", 270.0), ("x", 180.0)]
STICKS = dict(left=(-102.3, 92.4), right=(102.3, 92.4))
STICK = dict(base=14.1, top=10.25, housing=3.7, dome=10.0, dome_rise=1.6, shaft=4.5, cap=8.0, cap_y=(8.7, 12.2),
             dish=0.6, tilt=14.0)
PADS = dict(left=(-105.6, 59.3), right=(105.6, 59.3), size=32.1, r=3.5)
PILLS = dict(view=(-114.6, 109.1, 9.2, 4.4), menu=(114.6, 109.1, 9.2, 4.4), steam=(-97.7, 34.1, 16.3, 6.8),
             qam=(97.7, 34.1, 16.3, 6.8))
PILL_HEIGHT = 1.4
# The speakers' grilles under the pills: three rows of slots (z, [(x0, x1), ...]), the left one's; mirrored.
SPEAKER = [(24.4, [(-105.9, -101.8), (-101.5, -97.4), (-97.1, -93.0), (-92.7, -88.8)]),
           (21.3, [(-103.7, -100.5), (-99.3, -95.2), (-94.9, -88.8)]),
           (18.1, [(-101.5, -97.4), (-97.1, -93.2), (-92.7, -88.8)])]
SPEAKER_SLOT = 1.75
MICS = [(-58.9, 110.6), (58.9, 110.6)]

# ---- The top and bottom edges (x, y) ---------------------------------------------------------------------------------
TOP = dict(volume=(-81.9, -70.8), jack=-50.8, vent=(-26.5, 27.0, 12), vent_y=(4.1, 12.7), usb=(51.5, 9.8, 3.4),
           led=64.8, power=77.6, y=8.2, button_r=3.55, button_height=0.3, seam=14.0)   # the buttons all but flush
MICRO_SD = (78.0, 9.4, 13.0, 1.6)  # on the bottom edge: x, y, length, height

# ---- The shoulders ---------------------------------------------------------------------------------------------------
# The bumper (the right one, R1; mirrored for L1): a strip over the top corner, from INNER along the top edge round the
# corner to SIDE_Z down the end, from the face's edge (y 7.9) back to the trigger; PROUD over the top edge, flush with
# the end from round the corner (FLUSH: from where it starts to go flush to where it is, across).
BUMPER = dict(inner=104.3, side_z=100.0, proud=0.85, flush=(130.0, 137.0), front=7.9)
BUMPER_BACK = [(149.4, 16.4), (116.5, 22.0)]  # the trigger's front edge on the top, seen from above
# The trigger (the right one, R2; mirrored for L2): a rounded hump behind the bumper. Its top ramps gently back and
# down from the bumper's back edge, then rounds over into its steep back, which ends in a tip just above the grip, the
# notch between them. Seen from the end (y, z), TRIGGER_PROFILE, its back from the bumper to the tip, then its
# underside into the body; from behind (x, z), TRIGGER_BACK, the drawing's outline of its back, whose top edge is where
# the ramp turns down (printed); from above, the grip's outline behind BUMPER_BACK. The drawing's line round it from
# behind, the socket it sits in, carries on up its inner side to the top edge as a seam (SOCKET, printed).
SOCKET = [(149.0, 96.9), (147.3, 92.6), (125.3, 92.6), (120.2, 97.7), (116.8, 107.0), (113.4, 112.1), (104.9, 114.7)]
TRIGGER_BACK = [(148.1, 101.9), (147.0, 104.8), (143.9, 107.0), (136.0, 109.7), (128.7, 110.8), (122.0, 110.8),
                (118.5, 110.1), (116.8, 107.9), (117.5, 105.0), (121.0, 100.2), (124.4, 96.0), (127.5, 94.6),
                (131.2, 94.3), (145.6, 94.3), (147.4, 95.6), (148.1, 98.5)]
TRIGGER_PROFILE = [(16.0, 116.9), (20.0, 115.8), (24.0, 114.0), (28.0, 111.6), (31.0, 109.6), (33.4, 107.6),
                   (35.1, 105.0), (36.2, 101.8), (36.8, 98.4), (37.1, 95.4), (36.9, 93.4), (35.8, 92.3)]
TRIGGER_UNDER = [(33.5, 92.0), (29.0, 92.9), (24.0, 95.4), (19.5, 99.0), (15.0, 104.0)]
TRIGGER_PROUD = (0.6, (126.0, 134.0))  # its top over the top edge, flush round the corner as the bumper is
TRIGGER_PIVOT = (20.0, 112.0)      # (y, z): pulled, it turns about here, its tip coming forward
TRIGGER_PULL = 7.0                 # degrees

# ---- The back (x, z, as the face's) ----------------------------------------------------------------------------------
PADDLES = dict(r4=(109.7, 57.2), r5=(109.7, 34.3), l4=(-109.7, 57.2), l5=(-109.7, 34.3), size=20.9, r=3.5,
               proud=0.9)
VENTS = dict(x=[34.4, 44.0, 53.5, 63.0, 72.5, 82.0], z=32.8, width=8.1, height=24.9)
VALVE = dict(x=0.0, z=67.5, width=33.0, height=9.6)
SCREWS = [(-92.0, 112.6), (92.0, 112.6), (-26.5, 101.5), (26.5, 101.5), (-108.5, 12.0), (108.5, 12.0),
          (-28.5, 7.5), (28.5, 7.5)]

# ---- Colours (sRGB) --------------------------------------------------------------------------------------------------
COLOURS = dict(case="#34353A", seam="#1E1F22", button="#1D1D20", legend="#E8E8EA", glass="#0E0F11", dome="#CDCED0",
               cap="#242427", pad="#303135", vent="#141416", plate="#2B2C30", port="#0B0B0C", shoulder="#2E2F33")

# ---- The atlas -------------------------------------------------------------------------------------------------------
REGIONS = dict(front=(0, 0, 1024, 400), rear=(0, 404, 1024, 400), top=(0, 808, 1024, 68), bottom=(0, 880, 1024, 68))
SPANS = dict(front=(-HALF, HALF, 0.0, HEIGHT), rear=(-HALF, HALF, 0.0, HEIGHT), top=(-HALF, HALF, 0.0, 19.8),
             bottom=(-HALF, HALF, 0.0, 19.8))
SWATCHES = {name: (16 + 32 * k, 972) for k, name in enumerate(COLOURS)}
SCREENS = dict(boot=(0, 0, 480, 300), library=(512, 0, 480, 300), game1=(0, 320, 480, 300), game2=(512, 320, 480, 300))
SCREEN_SIZE = 1024
MADE_UP = ["Springheel Sam", "Stormfist", "Kaleidrop", "Deep Fathom", "Ghoulish Gus", "Redline Riviera"]

# ---- The clip (frames at FPS) ----------------------------------------------------------------------------------------
LIFT = (6, 22, 154, 170)           # picked up over these frames, put down over these
WAKE = 26                          # STEAM pressed: the boot screen, then the library
SHOWING = [(30, 40, "boot"), (40, 76, "library")]
LAUNCH = 70                        # A on the game
PLAY = (76, 150)                   # the game, its two frames swapped every 8
PAD_TAPS = (100, 116)
TRIGGER_PULLS = (92, 104, 132)
RUMBLE = (120, 130)
