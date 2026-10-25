"""The ColecoVision's measurements, shared by colecovision_print.py (which draws its printing) and colecovision.py
(which builds it). Plain Python: Blender's Python imports it too.

The ColecoVision (1982), 356 x 205 x 52 mm (HobbyDB's 14 x 8 x 2 inches), one controller in its bay and the other out
in front of it. Millimetres: x from the console's middle (left to right), y back from its front, z up from the table.
The rest was measured from photographs on Wikimedia Commons (Evan-Amos's views of the console from each corner and with
a controller, and of the controller; views from above, and with a cartridge in), scaled by the console's width.

The console: a black box, the silver band across its front (COLECOVISION's rainbow lettering, VIDEO GAME SYSTEM,
EXPANSION MODULE INTERFACE) with the expansion interface's door standing out below its right half. On its top, the
controller bay at the back left; the cartridge panel at the back right, slats along its back, the cartridge standing in
the slot at its front, behind the silver INSERT CARTRIDGE HERE plate (ON and OFF, RESET); along the front, slats at the
left, the power switch, and RESET's button at the right. The controller: a slab, the knob (a joystick with an
aluminium cap) at one end, the twelve keys at the other, a grey fire button down each side.

One texture (ATLAS square, REGIONS): `top` (the console seen from above: the slats' frames, the plate, COLECO on the
controllers' docks; planar-mapped onto every face facing up), `front` (its front face), `pad` (a controller's top: the
keys' numbers, COLECO), `label` (the cartridge's: a made-up game, Odyssey), and swatches. A region is (x, y, width,
height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, HEIGHT = 356.0, 205.0, 52.0
EDGE = 4.0
BAND = dict(z=(12.0, 32.0), depth=0.8)                     # the silver band across the front, sunk a little
EXPANSION = dict(x=(48.0, 150.0), z=(0.0, 20.0), out=12.0)  # the expansion interface's door, below the band
BAY = dict(x=(-165.0, -9.0), y=(64.0, 197.0), depth=24.0)   # the controller bay
PANEL = dict(x=(0.0, 166.0), y=(72.0, 196.0), depth=1.5)    # the cartridge panel, sunk a little
SLATS = [dict(x=(-160.0, -36.0), y=(16.0, 58.0), count=26, vertical=True),       # the front left's slats
         dict(x=(4.0, 162.0), y=(178.0, 196.0), count=36, vertical=True)]       # along the panel's back
SWITCH = dict(x=(-14.0, -2.0), y=(24.0, 46.0), travel=10.0)                    # the power switch's slot
RESET = dict(x=(140.0, 160.0), y=(22.0, 48.0))                                 # RESET's button, its recess
PLATE = dict(x=(18.0, 130.0), y=(18.0, 52.0))                                  # INSERT CARTRIDGE HERE
SLOT = dict(x=(30.0, 116.0), y=(56.0, 80.0), depth=48.0)                       # the cartridge slot

CART = dict(size=(82.0, 20.0, 104.0), label=(70.0, 66.0), inserted=44.0, ribs=9)   # w, thick, tall; label; in slot

# The controllers: each length x width x height, its knob at one end, its keys at the other.
PAD = dict(length=150.0, width=66.0, height=22.0, knob=(-46.0, 14.0, 20.0), keys=(17.0, 16.0, 13.0, 12.5),
           first_row=16.0, side=(-30.0, 9.0, 3.0))  # the knob's middle (along it), radius, height; the keys' pitch
                                                    # across and along, their size across and along; the first
                                                    # row's middle (along it); the side buttons' middle, length, out
BAY_PAD = dict(at=(-87.0, 162.0), turn=0.0)          # the one in the bay: its middle, its knob's end to the left
FREE_PAD = dict(at=(-232.0, -40.0), turn=-64.0)      # the one in front: its knob towards the back

COLOURS = dict(case="#18181A", dark="#0A0A0B", silver="#C6C8CC", key="#D9DBD6", grey="#8C8E91", cart="#141416")

REGIONS = dict(top=(0, 0, 1024, 590), front=(0, 598, 1024, 162), pad=(0, 768, 470, 207), label=(478, 768, 280, 256))
SWATCHES = dict(dark=(784, 792), silver=(816, 792), key=(848, 792), grey=(880, 792), aluminium=(912, 792),
                red=(944, 792))

FPS = 30
LENGTH = 240                 # 8 s
