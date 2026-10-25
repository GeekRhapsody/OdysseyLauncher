"""Flash's card, a 2000s monitor playing a Flash game: the measurements shared by flash_print.py (which draws its
printing and screens) and flash.py (which builds it). Plain Python: Blender's Python imports it too.

Flash has no hardware: its games were played in a web browser, the Flash Player's red logo on their preloaders, its
right-click menu ending in About Adobe Flash Player. The card is that: a silver 17-inch LCD monitor of the time on its
oval foot, a browser window filling its screen with a Flash game in the page (a made-up game, Odyssey), and a mouse
beside its foot. Millimetres: x from the monitor's middle (left to right), y back from its panel's front, z up from the
table. A 17-inch 4:3 panel's active area is 338 x 270 mm; the rest is typical of the monitors of the time.

The Flash logo (F_LOGO) is the white f traced from the Flash Player icon on Wikimedia Commons, normalised to its
square (x right, y down, 0 to 1).

One texture (ATLAS square, REGIONS): the screens, each the glass's whole area (`rest`, the preloader's splash with the
Flash logo; `load`, its bar filling; `title`, Odyssey's title with the pointer on PLAY; `game1` and `game2`, two frames
of play; `menu`, the right-click menu over the game), the brand plate under the screen, the mouse's top, and swatches.
A region is (x, y, width, height) in pixels.
"""

ATLAS = 1024

PANEL = dict(width=370.0, height=306.0, depth=52.0, bottom=92.0, bezel=16.0, lip=24.0)   # the bezel; the deeper bottom
GLASS = (338.0, 270.0)
STAND = dict(base=(240.0, 196.0, 16.0), base_y=70.0, neck=(70.0, 30.0), neck_y=96.0, top=150.0)
LED = (156.0, -14.0, 2.2)                                   # the power light: x, z from the panel's bottom edge, radius
BUTTONS = dict(x=[96.0 + 13.0 * k for k in range(4)], z=-12.0, size=(8.0, 3.0))   # under the screen, at the right

MOUSE = dict(at=(196.0, -62.0), turn=-12.0, size=(64.0, 116.0, 36.0), split=50.0)   # w, length, h; buttons' length

F_LOGO = [(0.742, 0.179), (0.761, 0.179), (0.761, 0.307), (0.714, 0.312), (0.693, 0.319), (0.664, 0.338),
          (0.628, 0.377), (0.597, 0.435), (0.695, 0.436), (0.695, 0.563), (0.547, 0.563), (0.506, 0.655),
          (0.477, 0.703), (0.434, 0.752), (0.384, 0.788), (0.351, 0.804), (0.318, 0.815), (0.273, 0.823),
          (0.242, 0.824), (0.242, 0.697), (0.283, 0.692), (0.320, 0.678), (0.346, 0.659), (0.373, 0.627),
          (0.410, 0.557), (0.463, 0.422), (0.497, 0.347), (0.518, 0.312), (0.545, 0.276), (0.583, 0.238),
          (0.636, 0.205), (0.694, 0.186)]

COLOURS = dict(silver="#B8BBC0", black="#121214", glass="#FFFFFF", mouse="#C9CBCF", dark="#2A2B2E")

SCREEN_PX = (400, 320)
REGIONS = dict(rest=(0, 0) + SCREEN_PX, load=(408, 0) + SCREEN_PX, title=(0, 328) + SCREEN_PX,
               game1=(408, 328) + SCREEN_PX, game2=(0, 656) + SCREEN_PX, menu=(408, 656) + SCREEN_PX,
               plate=(816, 0, 208, 60), mouse=(816, 68, 120, 216))
SWATCHES = dict(silver=(832, 312), black=(864, 312), blue=(896, 312), grey=(928, 312))

FPS = 30
LENGTH = 240                 # 8 s
