"""The Uzebox card's measurements, shared by uzebox_print.py (which draws its printing) and uzebox.py (which builds it).
Plain Python: Blender's Python imports it too.

The Uzebox (Belogic, 2008) is open hardware with no case of its own: the common one is the Uzebox V1.2 kit's red board,
about 100 x 80.5 mm, measured on a photograph of it from straight above against its 40-pin chip (52.3 mm long), every
part placed from that photograph. Its pad is an SNES-style one (unbranded here), about 144 x 61 mm. Millimetres: x from
the board's middle (left to right), y back from its front edge (the SNES ports' side), z up from the table.

The board stands on four nylon standoffs (STANDOFF); on it: the two SNES ports overhanging its front edge (PORTS), LED1
between them, RESET and POWER behind them, the UZEBOX logo in white outline letters; the 40-pin microcontroller (MCU), its
crystal, the video encoder, the regulator, the capacitors (CAPS) and resistors (RESISTORS); along the back edge the DC
jack, S-Video, the yellow and red RCA jacks, the blue ISP header and the SD card's socket with its card; the EXT header's
pins at the left. Games come on the SD card.

The pad (PAD), lying at the board's left: a dog bone, its top towards its cable; the D-pad, A B X Y in the PAL colours, SELECT and START slanting,
the shoulder buttons; its cable to SNES P1, its plug in the port.

One texture (ATLAS square, REGIONS): `board` (the board from above: its silk screen, traces and pads, the small parts
too small to build), `card` (the SD card's label), `pad` (the pad from above, in its own frame), and swatches. A region is
(x, y, width, height) in pixels.
"""

ATLAS = 1024

WIDTH, DEPTH, THICK = 100.0, 80.5, 1.6
HALF = WIDTH / 2
STANDOFF = dict(height=8.0, r=2.6, at=[(-46.0, 3.5), (46.0, 3.5), (-46.0, 77.0), (46.0, 77.0)])
TOP = STANDOFF["height"] + THICK                           # the board's top face

# Boxes: (x0, x1, y0, y1, height above the board).
PORTS = dict(p1=(-48.5, -6.9), p2=(7.5, 49.5), y=(-17.0, 4.9), height=15.0, socket=(30.0, 10.0, 6.0))
MCU = (-31.9, 21.7, 23.7, 39.5, 4.2)
CRYSTAL = (-2.8, 9.5, 16.8, 21.4, 3.5)
ENCODER = (-13.4, -3.6, 52.8, 62.0, 1.8)
REGULATOR = dict(body=(-46.9, -37.6, 47.4, 56.4, 4.5), tab=(-46.9, -37.6, 56.4, 62.0, 1.3))
DC = (-48.0, -37.6, 65.4, 81.7, 11.0)
SVIDEO = (-37.1, -22.4, 65.0, 82.0, 12.0)
RCA = dict(video=(-21.2, -10.1, "yellow"), audio=(-8.8, 2.1, "red"), y=(68.0, 79.0), height=11.5, barrel=(4.2, 9.0))
ISP = (3.3, 18.5, 73.5, 82.5, 9.0)
SD = dict(socket=(19.6, 48.7, 52.3, 80.9, 3.0), card=(24.0, 32.0, 2.1), out=6.5)
EXT = dict(x=(-44.4, -40.4), y=(10.6, 31.0), height=2.5, pins=8, pin=8.5)
BUTTONS = dict(reset=(-29.4, 14.7), power=(27.5, 14.7), size=6.0, height=3.5, cap=1.8)
LED = dict(at=(1.1, 2.8), r=2.5, height=8.0)
# Capacitors (x, y, r, height) and resistors (x, y, turned: 0 along x, 1 along y).
CAPS = [(-31.4, 52.0, 3.2, 9.0), (-34.4, 44.0, 3.2, 9.0), (-24.9, 47.7, 3.2, 9.0), (-17.6, 49.0, 3.0, 8.0),
        (-18.3, 62.9, 4.2, 7.0), (-10.0, 66.6, 3.0, 8.0), (-3.9, 51.6, 2.8, 7.0)]
RESISTORS = ([(2.0 + 2.5 * k, 46.0, 1) for k in range(8)] + [(27.0, 34.0 + 2.6 * k, 0) for k in range(6)]
             + [(-26.0, 59.0, 1), (-22.6, 59.0, 1), (12.0, 64.0, 0), (12.0, 67.0, 0)])

# The pad, in its own frame (x across, y towards its top, where its cable leaves), placed at AT turned TURN degrees.
PAD = dict(points=[(0.0, 22.0), (-20.0, 24.5), (-40.0, 30.5), (-58.0, 25.5), (-69.5, 12.0), (-72.0, 0.0),
                   (-69.0, -14.0), (-58.0, -26.0), (-42.0, -30.5), (-25.0, -27.5), (-12.0, -22.5), (0.0, -21.0),
                   (12.0, -22.5), (25.0, -27.5), (42.0, -30.5), (58.0, -26.0), (69.0, -14.0), (72.0, 0.0),
                   (69.5, 12.0), (58.0, 25.5), (40.0, 30.5), (20.0, 24.5)],
           height=20.0, dpad=(-43.0, 0.0, 11.0, 4.0), buttons=dict(a=(57.0, 0.0), b=(44.0, -11.0), x=(44.0, 11.0),
                                                                    y=(31.0, 0.0)),
           button_r=5.4, select=(-8.0, -6.0), start=(6.0, -6.0), pill=(9.0, 3.4), slant=30.0, shoulders=(46.0, 24.0),
           at=(-118.0, 30.0), turn=-70.0)
PAD_SPAN = (-74.0, 74.0, -33.0, 33.0)

COLOURS = dict(board="#E8402A", silk="#FFFFFF", black="#1E1E22", metal="#C9CACC", gold="#D8B25A", yellow="#F2C21B",
               red="#D8302A", blue="#1F5FBF", sd="#2A4FA8", nylon="#E9E4D2", green="#5BE36B", green_off="#2F6E38",
               pad="#C9C9CB", pad_dark="#8E8E96", a="#D23A36", b="#F0C83A", x="#3A62C2", y="#3FA35A", white="#F2F2EE",
               cable="#2A2A2C", plug="#B4B4B8")

REGIONS = dict(board=(0, 0, 600, 483), card=(608, 0, 144, 192), pad=(0, 491, 444, 198))
SWATCHES = {name: (624 + 32 * (k % 12), 216 + 32 * (k // 12)) for k, name in
            enumerate(("board", "black", "metal", "gold", "yellow", "red", "blue", "sd", "nylon", "green",
                       "green_off", "pad", "pad_dark", "a", "b", "x", "y", "white", "plug"))}

FPS = 30
LENGTH = 240                 # 8 s
