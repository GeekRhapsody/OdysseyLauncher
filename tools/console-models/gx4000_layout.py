"""The Amstrad GX4000's measurements, shared by gx4000_print.py (which draws its printing) and gx4000.py (which builds
it). Plain Python: Blender's Python imports it too.

The GX4000 (1990) and its controller, a made-up game, Odyssey, in its slot. The console is 250 mm wide, 184 deep and 44
high (the Video Games Museum's 25 x 18.4 x 4.4 cm; Evan-Amos's straight photographs of it on Wikimedia Commons, from the
front and from below, have the same proportions). Millimetres: x from its middle (left to right), y back from the tip of
its front's curve, z up from the table. The plan's front curve and the heights across it were traced from those two
photographs, scaled by its width; the top from a museum's photograph of one from above (Wikimedia Commons) and
Evan-Amos's from the front left and right; the controller from his photographs of it.

The console: its body lofted along its width (the front's vertical face under the slope that rises to the top, flat
behind, the back face; lower towards the ends, which are rounded off), the two raised rails along its top (vents on
their inner sides) ending in round pads at the front (the power light's on the left, PAUSE on the right), the pink power
switch on the right rail, the cartridge slot between them (its two flaps meeting in the middle), AMSTRAD on the front
slope, the ports in the front (the stereo jack, the joystick ports either side of the analogue one, the light gun's);
the louvres along the back. The controller: its outline, the raised hood at its back where the cord comes out, the D-pad
in its dish, buttons 1 and 2, AMSTRAD.

One texture (ATLAS square, REGIONS): `top` (the console from above: x across, y down from the back), `front` (its front
face, x across, z down from the top of the region), `pad` (the controller from above), `cart` (the cartridge's label),
and swatches. A region is (x, y, width, height) in pixels."""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 250.0, 184.0, 44.0
FEET = 2.0
# The plan's front edge: (|x|, how far back from the tip), traced from below.
FRONT_CURVE = [(0.0, 0.0), (15.0, 0.5), (25.0, 1.7), (35.0, 3.5), (45.0, 5.9), (55.0, 9.0), (65.0, 12.8), (75.0, 16.3),
               (85.0, 19.3), (95.0, 21.4), (105.0, 23.0), (115.0, 23.7), (125.0, 23.8)]
# The top's height across the console (|x|, z), traced from the front: flat between the rails, falling to the ends.
TOP_HEIGHT = [(0.0, 37.0), (60.0, 37.0), (75.0, 36.0), (85.0, 34.6), (95.0, 32.0), (105.0, 28.7), (115.0, 24.7),
              (125.0, 18.0)]
FACE = 22.0                      # the front face's top, where the slope starts (at most a little under the top)
SLOPE = 34.0                     # how far back the slope reaches its crest
CREST = 34.0                     # the crest's height (at the middle; the top's height scales it towards the ends)
ROUND = dict(plan=14.0, bottom=8.0, back=8.0)

RAILS = dict(x=69.0, half=20.5, rise=7.0, y=(60.0, 170.0))   # each rail's middle, half width, height over the top,
                                                              # front and back ends (y)
PADS = dict(y=48.0, r=19.0, height=1.2)                       # the round pads at the rails' fronts
LIGHT = dict(at=(-69.0, 58.0), size=(5.0, 2.0))               # the power light, at the left pad's back
SWITCH = dict(x=(60.0, 71.0), y=(66.0, 92.0), travel=10.0, height=5.0)   # the pink switch, its slot on the right rail
SLOT = dict(at=(-4.0, 76.0), size=(72.0, 18.0), depth=30.0)
FLAPS = dict(thickness=1.6, sunk=1.4, droop=6.0, open=84.0)   # the slot's two flaps, hinged along its long edges
LOGO = dict(at=(-3.0, 30.0), size=(35.0, 15.0))               # AMSTRAD on the front slope (x, y), from above
# The front face's ports: (x, z) of their middles, their sizes.
PORTS = dict(jack=((-81.0, 14.8), 3.0), joy_1=((-45.0, 17.2), (21.0, 10.8)), analogue=((-0.6, 17.2), (30.0, 11.5)),
             joy_2=((42.8, 17.2), (21.0, 10.8)), gun=((77.0, 16.4), (15.0, 12.6)))

CART = dict(size=(68.0, 16.0, 78.0), seat=30.0, label=(56.0, 44.0), above=60.0)   # w, t, h; how deep it sits

# The controller, from above in its own frame (x across, y back from its front edge), and where it lies.
PAD = dict(size=(128.0, 58.0, 20.0), r=7.0, corner=20.0, at=(-118.0, -96.0), turn=12.0)
HOOD = dict(x=(-30.0, 32.0), y=(30.0, 58.0), height=5.0, point=12.0)   # the raised hood at its back
DPAD = dict(at=(-41.0, 28.0), dish=15.0, size=24.0, arm=8.4, height=2.6)
BUTTONS = dict(at=[(25.0, 15.0), (45.0, 13.0)], r=6.6, height=3.4, press=2.2)

COLOURS = dict(body="#E3E3DE", grey="#B9B9B5", pink="#D7206A", red="#D2223A", dark="#2A2A2C", print="#FFFFFF")

REGIONS = dict(top=(0, 0, 750, 552), front=(0, 560, 750, 108), pad=(0, 676, 512, 232), cart=(520, 676, 240, 189))
SWATCHES = dict(body=(800, 40), grey=(832, 40), pink=(864, 40), red=(896, 40), dark=(928, 40), lit=(960, 40))

FPS = 30
LENGTH = 240                 # 8 s
