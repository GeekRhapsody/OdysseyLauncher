"""The Sega Master System's measurements, shared by master_system_print.py (which draws its printing) and
master_system.py (which builds it). Plain Python: Blender's Python imports it too.

The first Master System (1986), 365 x 168 x 73 mm (the Computer History Museum's record), with its Control Pad.
Millimetres: x from the console's middle (left to right), y back from its front edge, z up from the table. The rest was
measured from photographs on Wikimedia Commons (Evan-Amos's views of the console from each corner, of its pads and of a
cartridge; a view of it from above with a cartridge in), scaled by its width; the cartridge is the community's
measured 108 x 69 x 16 mm.

The console: a slab whose front band carries POWER at its left, the two control ports in a recess and the card slot at
its right, a red stripe along its top edge; on it the hood, its top rising from the stripe to the ridge along the back,
its ends and back sloping down (the back's slope full of vent holes), ribs along the slab's ends. In the hood's right
part a red panel is sunk, sloping more gently than the hood, RESET and PAUSE across it and the diagram under them; at
its back the cartridge slot, its dust flap hinged along its front edge. The Control Pad lies in front of its left end.

One texture (ATLAS square, REGIONS): `top` (the whole console seen from above: the hood's lettering and stripe, the red
panel's printing, the vent holes; planar-mapped onto every face facing up), `front` (the front band seen from in
front: POWER's label, the ports' and the card slot's legends), `label` (the cartridge's: a made-up game, Odyssey, on
the red grid), `pad` (the Control Pad's top), and swatches. A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 365.0, 168.0, 73.0
BAND = dict(z=(4.0, 28.0), bevel=(8.0, 36.0))     # the front face's bottom and top; the bevel up to the hood's front
FOOT = 4.0                                         # the base's recessed foot band
RIDGE = (128.0, 136.0)                             # the hood's flat ridge, along y
BACK = (DEPTH, 42.0)                               # the back slope's foot, (y, z)
ENDS = dict(top=34.0, inset=38.0)                  # the hood's ends slope in from the slab's ends to inset at its top


def hood_z(y):
    """The hood's top at y, from the stripe up to the ridge."""
    (y0, z0), y1 = BAND["bevel"], RIDGE[0]
    t = min(1.0, max(0.0, (y - y0) / (y1 - y0)))
    return z0 + (HEIGHT - z0) * t


def profile():
    """The console's side outline, (y, z), anticlockwise seen from the right end."""
    return [(2.0, 0.0), (DEPTH - 2.0, 0.0), (DEPTH, FOOT), BACK, (RIDGE[1], HEIGHT), (RIDGE[0], HEIGHT), BAND["bevel"],
            (0.0, BAND["z"][1]), (0.0, FOOT), (2.0, FOOT)]


PANEL = dict(x=(4.0, 117.0), y=(10.0, 117.0), z=(33.5, 56.0))   # the red panel: across, along, its height there
SLOT = dict(x=(5.5, 115.5), y=(117.5, 135.5), bottom=30.0, flap=62.0)   # the cartridge slot; its flap's height
BUTTONS = dict(reset=(8.0, 30.0), pause=(92.0, 114.0), y=(98.0, 108.0), height=3.0)   # RESET and PAUSE
RIBS = dict(z=[8.0 + 2.6 * k for k in range(9)], depth=1.4, width=1.2)   # along both ends of the slab

POWER = dict(x=(-145.0, -119.0), z=(7.0, 21.0), out=2.5)
PORTS = dict(x=(-34.0, 22.0), z=(FOOT, 18.0), depth=7.0, at=(-19.0, 7.0), size=(21.0, 9.0))
CARD = dict(x=(54.0, 111.0), z=(FOOT, 27.0), depth=9.0, slot=(60.0, 105.0, 13.0, 15.5))

CART = dict(size=(108.0, 16.0, 69.0), label=(102.0, 27.0), inserted=40.0)   # w, thick, tall; its label, w x h

PAD = dict(at=(-125.0, -64.0), size=(115.0, 52.0, 19.0), turn=6.0,   # its middle; w, d, h; turned (degrees)
           block=dict(x=(10.0, 57.5), y=(6.0, 26.0), height=5.0),      # the raised block at its back right
           well=(-52.0, -14.0, -18.0, 14.0),                          # the D-pad's well: x0, x1, y0, y1
           dpad=dict(size=27.0, height=6.0), buttons=dict(x=(19.0, 40.0), y=-9.0, r=6.6, height=3.0),
           stripes=(-9.0, 8.0, -20.0, 2.0))                           # behind SEGA: x0, x1, y0, y1

COLOURS = dict(case="#1E1E20", dark="#0B0B0C", grey="#5E5F62", red="#C8262C", cart="#232325", button="#151516")

REGIONS = dict(top=(0, 0, 1024, 472), front=(0, 480, 1024, 120), label=(0, 608, 408, 108), pad=(416, 608, 460, 208))
SWATCHES = dict(dark=(904, 624), grey=(936, 624), red=(968, 624), button=(1000, 624))

FPS = 30
LENGTH = 240                 # 8 s
