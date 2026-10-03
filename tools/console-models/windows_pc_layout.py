"""The Windows PC's print atlas, shared by windows_pc_print.py (which draws it) and windows_pc.py (which maps it). Plain
Python: Blender's Python imports it too.

Regions are (x, y, width, height) in the atlas's pixels, from its top left. Each is drawn at its face's millimetres
(windows_pc.py has the faces).
"""

ATLAS = 2048

FRONT = (0, 0, 512, 1024)            # the front panel, 236 x 470 mm: the mesh over three fans
TOP = (512, 0, 512, 1024)            # the top, 230 x 440 mm, front at the bottom: the vent, the buttons and ports
MOBO = (1024, 0, 1024, 1024)         # the inside's back wall behind the glass, 405 x 440 mm: the motherboard
INNER_FRONT = (0, 1024, 512, 1024)   # the inside of the front, 210 x 440 mm: the front fans' backs
GPU = (512, 1024, 1024, 192)         # the graphics card's side, 325 x 57 mm
SHROUD = (512, 1216, 1024, 256)      # the power supply shroud's side, 405 x 105 mm
FINS = (1536, 1024, 512, 448)        # the cooler's top, 150 x 270 mm: its fins
FAN = (512, 1472, 512, 512)          # a cooler fan's face, 126 mm square: its frame, blades and lit ring
PLATE = (1536, 1472, 64, 512)        # the cooler's plate between its fans, 14 x 126 mm

# pc_screen.png: the desktop, the screen's whole lit area.
SCREEN_PX = (2048, 1152)
SCREEN_MM = (528.0, 297.0)           # 16:9
