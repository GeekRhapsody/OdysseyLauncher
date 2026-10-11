"""The retro PCs' measurements, shared by retro_pc_print.py (which draws their printing) and retro_pc.py (which builds
them). Plain Python: Blender's Python imports it too.

Three sets, one per system: `dos` (a late-80s 386 desktop with a 14-inch VGA monitor on it), `windows3x` (an early-90s
486 desktop with a 14-inch SVGA monitor on it) and `windows9x` (a late-90s mini tower with a 15-inch monitor beside
it). Millimetres throughout. A face is drawn from its top left, x to the right and y down; retro_pc.py maps it onto the
model.

Each set has a print atlas (ATLAS square) of named regions (x, y, width, height in its pixels), each drawn at its
face's millimetres, and a screen image (SCREEN_PX) covering the CRT's glass.

A face's parts are (kind, x, y, width, height, depth, text): drawn by retro_pc_print.py at (x, y), and, when depth
isn't 0, raised that far off the face by retro_pc.py (a drive's bezel, a button, a knob), its front printed too.
"""

ATLAS = 2048
SCREEN_PX = (1024, 768)


def monitor(width, height, depth, tube, opening, inner, screen_z, colour, strip, parts):
    """
    A CRT: its bezel width x height, depth deep, then the tube's housing tube deep. The screen's opening is opening
    (w, h) at the front, narrowing to inner (w, h) where it meets the glass, centred screen_z above the bezel's bottom.
    strip: the band under the opening (its height from the bezel's bottom) printed with parts. The screen image
    covers the glass (a little larger than inner, so its edge is hidden); the lit 4:3 raster is the middle of it.
    """
    gw, gh = inner[0] + 8.0, inner[1] + 8.0
    return dict(width=width, height=height, depth=depth, tube=tube, opening=opening, inner=inner, screen_z=screen_z,
                colour=colour, strip=strip, parts=parts, glass=(gw, gh), raster=(inner[0] - 18.0, (inner[0] - 18.0) * 0.75))


SETS = {
    "dos": dict(
        name="386 desktop and 14-inch VGA monitor",
        case=dict(kind="desktop", width=460.0, depth=420.0, height=150.0, feet=8.0, colour="#CDC3A8",
                  bezel_colour="#D3C9AE", front=[
                      ("badge", 24, 16, 160, 24, 0, "ODYSSEY|386/33"),
                      ("display", 24, 52, 52, 26, 0, "33"),
                      ("leds", 88, 52, 84, 26, 0, "POWER:#36E05A|TURBO:#F2D33A|HDD:#F04A3A"),
                      ("button", 24, 92, 26, 13, 3.5, "TURBO"),
                      ("button", 60, 92, 26, 13, 3.5, "RESET"),
                      ("keylock", 182, 58, 18, 18, 3.0, ""),
                      ("vents", 24, 116, 176, 14, 0, ""),
                      ("floppy525", 250, 16, 146, 41.3, 1.5, "5.25"),
                      ("floppy35adapter", 250, 62, 146, 41.3, 1.5, "3.5"),
                      ("power", 410, 88, 30, 34, 4.0, ""),
                  ]),
        monitor=monitor(350.0, 330.0, 70.0, 290.0, (292.0, 224.0), (272.0, 206.0), 186.0, "#D8D0B8", 64.0, [
            ("brand", 20, 14, 120, 22, 0, "ODYSSEY|VGA 14"),
            ("knob", 226, 18, 16, 16, 4.0, ""),
            ("knob", 252, 18, 16, 16, 4.0, ""),
            ("led", 286, 23, 6, 6, 0, "#36E05A"),
            ("button", 300, 15, 22, 22, 4.0, ""),
        ]),
        place="stacked", yaw=18.0,
        atlas=dict(front=(0, 0, 2048, 640), back=(0, 640, 1536, 448), strip=(0, 1088, 1536, 296),
                   vents=(1536, 640, 512, 512), label=(1536, 1152, 512, 384)),
        screen="commander",
    ),
    "windows3x": dict(
        name="486 desktop and 14-inch SVGA monitor",
        case=dict(kind="desktop", width=440.0, depth=410.0, height=140.0, feet=8.0, colour="#D6D0BF",
                  bezel_colour="#DCD6C6", front=[
                      ("floppy525", 22, 14, 146, 41.3, 1.5, "5.25"),
                      ("cdcaddy", 22, 60, 146, 41.3, 1.5, "CD-ROM"),
                      ("floppy35", 186, 14, 101.6, 25.4, 1.5, "3.5"),
                      ("badge", 300, 14, 118, 22, 0, "ODYSSEY|486DX2"),
                      ("display", 186, 50, 46, 24, 0, "66"),
                      ("leds", 240, 50, 84, 24, 0, "POWER:#36E05A|TURBO:#F2D33A|HDD:#F04A3A"),
                      ("keylock", 336, 53, 18, 18, 3.0, ""),
                      ("button", 186, 88, 24, 12, 3.5, "TURBO"),
                      ("button", 218, 88, 24, 12, 3.5, "RESET"),
                      ("vents", 254, 86, 104, 30, 0, ""),
                      ("power", 372, 78, 46, 32, 4.0, ""),
                  ]),
        monitor=monitor(360.0, 345.0, 72.0, 300.0, (300.0, 230.0), (280.0, 212.0), 196.0, "#DDD7C7", 70.0, [
            ("brand", 22, 16, 130, 24, 0, "ODYSSEY|SVGA 1024"),
            ("knob", 214, 22, 14, 14, 3.5, ""),
            ("knob", 236, 22, 14, 14, 3.5, ""),
            ("knob", 258, 22, 14, 14, 3.5, ""),
            ("led", 292, 26, 6, 6, 0, "#F2A93A"),
            ("button", 306, 18, 24, 20, 4.0, ""),
        ]),
        place="stacked", yaw=18.0,
        atlas=dict(front=(0, 0, 2048, 600), back=(0, 640, 1536, 448), strip=(0, 1088, 1536, 312),
                   vents=(1536, 640, 512, 512), label=(1536, 1152, 512, 384)),
        screen="program_manager",
    ),
    "windows9x": dict(
        name="mini tower and 15-inch monitor",
        case=dict(kind="tower", width=190.0, depth=430.0, height=420.0, feet=10.0, colour="#D9D5C9",
                  bezel_colour="#DFDBD0", front=[
                      ("cdrom", 22, 20, 146, 41.3, 1.5, "CD-ROM"),
                      ("blank525", 22, 64, 146, 41.3, 1.0, ""),
                      ("floppy35", 44.2, 122, 101.6, 25.4, 1.5, "3.5"),
                      ("badge", 20, 166, 150, 22, 0, "ODYSSEY|"),
                      ("power", 70, 204, 50, 30, 4.0, ""),
                      ("leds", 50, 244, 90, 18, 0, "POWER:#36E05A|HDD:#F2A93A"),
                      ("button", 85, 268, 20, 9, 2.5, "RESET"),
                      ("vents", 30, 292, 130, 70, 0, ""),
                      ("sticker", 120, 372, 44, 24, 0, "200|MHz"),
                  ]),
        monitor=monitor(380.0, 370.0, 82.0, 330.0, (314.0, 240.0), (294.0, 222.0), 210.0, "#E0DCD1", 76.0, [
            ("brand", 130, 20, 120, 26, 0, "ODYSSEY|"),
            ("osd", 30, 26, 80, 12, 1.5, ""),
            ("led", 300, 29, 6, 6, 0, "#36E05A"),
            ("power", 316, 22, 26, 20, 4.0, ""),
        ]),
        place="beside", yaw=18.0,
        atlas=dict(front=(0, 0, 928, 2048), back=(928, 0, 464, 1024), strip=(928, 1024, 1120, 224),
                   vents=(1392, 0, 512, 512), label=(1392, 512, 512, 384)),
        screen="desktop95",
    ),
}
