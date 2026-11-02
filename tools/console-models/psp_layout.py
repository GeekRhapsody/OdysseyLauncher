"""The PlayStation Portable's measurements, shared by psp_print.py (which draws its printing, its screen's still and the
screens of its video), psp_video.py (which draws the video) and psp.py (which builds it). Plain Python: Blender's
Python imports it too.

The PSP-1000 (2004) in piano black: 170 mm wide, 74 mm high and 23 mm deep (Sony's figures), standing up in
handheld.py's frame: x from the middle (left to right, as the face is seen), z up from the bottom edge, y back from
the face (0) to the back's flat (BACK), the UMD door standing a millimetre proud of it. The face's layout was measured
from a white PSP-1000 straight on (Wikimedia Commons' Psp-front, at 7.13 px a millimetre) for the first PSP card and is
kept; Evan-Amos's two three-quarter views (Commons: Psp-1000.jpg, Sony-PSP-1000-Body.jpg) check it and give the ends,
the band and the shoulders; Commons' Psp-top.jpg (a white one's top edge, 6.06 px a millimetre) places the IR window,
the USB port, its two screws and the OPEN latch between L and R; iFixit's PSP-1000 teardown (a straight view of the
back, its battery cover off) and Commons' UMD slot at PSP-1000 rear (a close view of the door) give the door (73.5 mm
wide over nearly the back's whole height) and its brushed ring (its outer edge 0.7 of the door's width, its inner 0.76
of its outer), and Commons' Psp umd disk.jpg the UMD's label side.

The body's outline (body_outline()) isn't a bar of soap: the middle, the screen's and the bottom row's, is the full
height, and each end is a grip, shorter (GRIP), the outline stepping down to it at the top and up to it at the bottom,
each step a riser at 45 degrees (STEP_TOP, STEP_BOTTOM) between rounded corners (RADII), and each grip's end one flat
arc of radius END_RADIUS about END_CENTRE (mirrored for the left). Measured from Psp-front's straight view of a white
PSP-1000 and checked against a trace of the silhouette of a black one's back on light wood (Commons' PSP-1000 rear
20150930, at 18 px a millimetre: the end's arc is within 0.3 mm of it). Through its depth: the glossy front shell from
the face (its edge rounded over, FRONT_ROUND) to SEAM, the silver band (BAND), standing a quarter millimetre proud, and
the matte back shell, its edge rounded over (BACK_ROUND), all three stepped alike. In the steps, in the band's depth:
at the top, the clear shoulder buttons L and R (SHOULDER: shoulder_outline()), their tops a little under the middle's
and rounding down onto the grip's end; at the bottom left, the strap's silver loop (LOOP: loop_outline()), a bar
sloping from the grip's end down to the bottom and the slot between it and the step; at the bottom right, DC IN's
yellow socket (DC_IN) under the grip, open to the floor. On the face: the screen's glass, the D-pad's four buttons in
their round well, the analogue nub, the four face buttons round their ring, the row along the bottom (HOME, VOL - +,
the display and sound buttons, SELECT, START), the lights and their legends, the speakers' slits. On the top edge, in
the band: the IR window, the USB port and the OPEN latch, which slides towards R to release the door. On the right
end, in the band: the POWER/HOLD switch, which slides up to switch on or off and springs back; on the left end the WLAN
switch. On the back: the UMD door (DOOR, hinged along its bottom edge, its outside the brushed ring round the
logotype) over the bay (BAY: a recess the shape of the door, the spindle and the laser's track printed on its floor),
the battery cover's seams and the back's printing.

Three textures. `psp_print.png` (ATLAS square, PRINT_REGIONS): `front` (the face seen square on), `rear` (the back seen
from behind, its x the face's negated: the bay's floor, the battery cover, the legends), `top` (the top edge seen from
above, the face towards the region's bottom) and the swatches small parts take their colour from. `psp_media.png`
(MEDIA_REGIONS): the UMD's label side and its other side (each as seen looking at it) and the door's outside (seen from
behind). `psp_screen.png`: the screen's still, VIDEO_PX: the glass with the LCD switched off, the first and last frame
of the card's video (psp_video.py), which the launcher plays on the glass while the card is focused. A region is
(x, y, width, height) in pixels, and the box of millimetres it covers, (x0, x1, z0, z1).

The glass is wider than the LCD's lit area: the video's frame is the whole glass, at the PSP's own pixel pitch (480 x
272 over 95 x 53.9 mm), so the LCD's pixels are the video's, one for one, at LCD_AT.

The `focused` clip's timing, in frames at FPS, is here so that the video (psp_video.py) follows the clip (psp.py)
frame for frame: the launcher starts the video with the clip, and again each time the clip loops.
"""

import math

# ---- The body --------------------------------------------------------------------------------------------------------
WIDTH, HEIGHT, DEPTH = 170.0, 74.0, 23.0
BACK = 22.0                                  # the back's flat, the door 1 mm proud of it
# The outline's right half (the left's mirrored): the grip's end an arc; its bottom straight, and its top straight
# through top, falling towards the end; the risers of the steps to it, at 45 degrees through STEP_TOP and STEP_BOTTOM;
# the corners' radii from the bottom up: where the bottom turns up its step (foot), the step meets the grip's bottom
# (under), that meets the end (heel), the end meets the grip's top (head), that meets the top's step (inside), and the
# step turns into the top (brow).
END_RADIUS, END_CENTRE = 52.0, (33.0, 37.4)
GRIP = dict(bottom=7.5, top=(62.0, 68.8), fall=1 / 12)
STEP_TOP, STEP_BOTTOM = (58.5, 71.3), (59.5, 4.0)
RADII = dict(foot=2.0, under=1.5, heel=3.0, head=3.0, inside=2.0, brow=1.5)
FRONT_ROUND = 2.0                            # the radius rounding the face's edge over
SEAM = 7.8                                   # the front shell meets the band
BAND = (8.1, 14.6)                           # the silver band, front to back
BAND_OUT = 0.25                              # how far it stands proud
BACK_ROUND = 4.0                             # the radius rounding the back's edge over
# The back's flat sags towards the face over the grips (from beside the door), more and more towards their ends: none
# at |x| = x[0], depth at x[1], fading out over fade above and below them. Each grip's back a pillow and the back shell
# thin at the ends, as Psp-top's view of the top edge shows (about 1.6, 2.9, 4.7 and 7 mm down at 64, 73, 79, 83).
DOME = dict(x=(40.0, 85.0), depth=6.0, fade=1.5)
# The shoulder buttons L and R in the top's steps, in the band's depth: their top, from x (where the top edge's silver
# strip ends) at z = top, falls (fall) towards the end and rounds (corner) down onto it, out proud of the body (out),
# ending at z = end.
SHOULDER = dict(x=54.7, top=72.6, fall=0.12, corner=7.0, end=64.0, out=0.35)
# The strap's loop in the bottom left step, in the band's depth: a bar (its width bar) whose outside slopes at 45
# degrees through a point (through), from the grip's end, which it leaves at z = top, down to the bottom, out proud of
# the body (out), and along it to x = foot; the strap's slot between the bar and the step, from its floor to its roof
# (slot).
LOOP = dict(through=(-72.4, 3.65), bar=1.4, slot=(1.9, 5.9), top=12.0, foot=-55.0, out=0.35)
DC_IN = dict(x=(62.5, 67.5), z=(5.8, 7.9))   # the yellow socket in the bottom right step, under the grip

COLOURS = dict(case="#18181C", rear="#222227", buttons="#1C1C21", silver="#8E939B", clear="#A5AAB2", umd="#ECEDEF",
               yellow="#F2C230", lit="#7DFFB0", dark="#0B0B0D", metal="#8C9097")

# ---- The face (x, z) -------------------------------------------------------------------------------------------------
SCREEN = dict(x=0.0, z=40.85, width=95.04, height=53.86)   # the LCD's lit area: 4.3 inches, 16:9
GLASS = dict(x=(-50.9, 50.9), z=(13.3, 68.4))               # the glass over it, black round the LCD
DPAD = dict(x=-68.0, z=42.5, well=13.6)
FACE = dict(x=68.0, z=43.0, reach=9.5, radius=4.6, ring=10.4)
NUB = dict(x=-69.4, z=19.1, radius=6.0, well=7.0, travel=1.4)
ROW_Z = 6.7  # the buttons along the bottom: (name, x, shape) with shape "shield" (11.5 x 4.4) or "oval" (5.8 x 4.8)
ROW = [("HOME", -51.0, "shield"), ("VOL-", -38.6, "oval"), ("VOL+", -27.0, "oval"),
       ("DISPLAY", 18.3, "oval"), ("SOUND", 26.7, "oval"), ("SELECT", 38.0, "shield"), ("START", 50.0, "shield")]
SPEAKERS = [(-60.2, 12.0), (60.2, 12.0)]   # the two slits by the screen's lower corners
GRILLE = dict(x=(-54.0, 54.0), z=70.4, rows=3, pitch=0.82)  # the speaker's holes along the top
LIGHTS = dict(memory=(-82.2, 23.6), wlan=(-79.4, 15.8), power=(80.4, 24.4), hold=(77.0, 16.3), r=0.5)

FACE_BUTTONS = [("triangle", 90.0), ("circle", 0.0), ("cross", 270.0), ("square", 180.0)]
DPAD_BUTTONS = [("up", 90.0), ("right", 0.0), ("down", 270.0), ("left", 180.0)]

# ---- The edges -------------------------------------------------------------------------------------------------------
TOP = dict(ir=(-48.8, -36.5), usb=(-4.0, 4.0), screws=(-21.5, 21.5))   # x along the top edge
LATCH = dict(x=(34.0, 48.5), travel=2.6)    # the OPEN latch on the top edge: it slides towards R
POWER = dict(z=(10.5, 18.5), travel=3.0)    # the POWER/HOLD switch on the right end: up to switch on or off
WLAN = dict(z=(27.0, 33.0))                 # the WLAN switch on the left end

# ---- The back --------------------------------------------------------------------------------------------------------
DOOR = dict(x=(-36.75, 36.75), z=(7.5, 72.4), thick=2.0, radii=(7.0, 2.0, 2.0, 7.0))  # as rounded_rect() takes them
RING = dict(z=42.0, outer=25.6, inner=19.5)   # the brushed ring on the door, about the spindle
BAY = dict(inset=1.3, depth=3.6)              # the recess under the door
OPEN = -40.0                                  # degrees the door opens to (its top away from the back)
UMD = dict(width=65.0, bottom=-31.5, radius=32.5, corner=5.0, thickness=4.2, disc=30.0)  # its middle the disc's
UMD_SEAT = 0.6                                # its flat edge above the door's bottom


def region(px, mm):
    return dict(px=px, mm=mm)


ATLAS = 1024
PRINT_REGIONS = dict(
    front=region((0, 0, 1024, 452), (-86.0, 86.0, -1.0, 75.0)),
    rear=region((0, 460, 1024, 452), (-86.0, 86.0, -1.0, 75.0)),
    top=region((0, 920, 1024, 80), (-86.0, 86.0, -0.5, 23.5)),    # (x0, x1, y0, y1): the face at the bottom
)
SWATCHES = dict(yellow=(16, 1012), dark=(48, 1012), lit=(80, 1012), metal=(112, 1012), silver=(144, 1012),
                clear=(176, 1012), case=(208, 1012), umd=(240, 1012), rear=(272, 1012))   # 20 x 20 blocks' middles

MEDIA_REGIONS = dict(
    umd=region((8, 8, 402, 396), (-33.5, 33.5, -32.5, 33.5)),
    umd_rear=region((424, 8, 300, 296), (-33.5, 33.5, -32.5, 33.5)),
    door=region((8, 420, 456, 404), (-38.0, 38.0, 6.5, 73.5)),
)
MEDIA_SWATCHES = dict(umd=(760, 40), inside=(800, 40), edge=(840, 40))

# ---- The screen and its video ----------------------------------------------------------------------------------------
LCD_PX = (480, 272)
PITCH = LCD_PX[0] / SCREEN["width"]                             # pixels a millimetre: 5.05
VIDEO_PX = (514, 278)                                           # the glass, 101.8 x 55.1 mm, even sides for H.264
LCD_AT = (17, 3)                                                # the LCD's top left in the video's frame

MADE_UP = ("Skylance (Europe)", "n64")   # the UMD's game, from tools/made-up-games (made up: Arcwave's shoot 'em up)

# ---- The focused clip, in frames at FPS --------------------------------------------------------------------------------
FPS = 30
LENGTH = 300                 # 10 s
TURN_OUT = (8, 36)           # the console turns round on the spot to show its back
LATCH_OPEN = (38, 43)        # OPEN slides towards R ...
DOOR_OPEN = (42, 54)         # ... and the door springs open
UMD_SHOWN = (50, 58)         # the UMD appears over the open door, its label out
UMD_SLIDE = (66, 82)         # it slides down into the door and seats
DOOR_SHUT = (86, 96)         # the door shuts on it; the latch springs back
TURN_BACK = (100, 128)       # the console turns back to its face
POWER_ON = 132               # POWER slides up (and springs back): the light and the screen come on
BOOT = (136, 154)            # the PSP's start-up
XMB = (154, 188)             # the XMB: the game's icon, then its background; CROSS chooses it
CROSS = 178
GAME_BOOT = (188, 198)       # black while the game loads
TITLE = (198, 222)           # its title, PRESS START; START pressed
START = 212
PLAY = (222, 286)            # the game, played on the nub and CROSS
FIRE = (230, 240, 251, 262, 273)
HITS = (246, 268)            # enemies blown up
POWER_OFF = 284              # POWER held up: the screen goes off
SCREEN_OFF = (288, 296)
LIGHT_OFF = 294


def steer(f):
    """The nub's push at frame f while the game is played, (x, z), each from -1 to 1: a slow weave from side to side and
    a little up and down, easing in and out. The ship on the screen slides and banks with it."""
    a, b = PLAY
    if not a <= f <= b:
        return 0.0, 0.0
    t = (f - a) / FPS
    ease = min(1.0, (f - a) / 8.0, (b - f) / 8.0)
    ease = ease * ease * (3 - 2 * ease)
    return (ease * 0.9 * math.sin(2 * math.pi * t / 1.9 + 0.2), ease * 0.45 * math.sin(2 * math.pi * t / 1.3))


def arc(cx, cz, r, a0, a1, steps):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / steps), cz + r * math.sin(a0 + (a1 - a0) * k / steps))
            for k in range(steps + 1)]


def line(a, b, steps):
    """a to b, without b."""
    return [(a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps) for k in range(steps)]


def meet(p, t, q, u):
    """Where the line through p along t crosses the line through q along u."""
    dx, dz = q[0] - p[0], q[1] - p[1]
    a = (u[0] * dz - u[1] * dx) / (u[0] * t[1] - u[1] * t[0])
    return p[0] + a * t[0], p[1] + a * t[1]


def on_end(p, t, r):
    """Where the line through p along t (a unit vector) crosses the right end's arc moved to radius r, on its outer
    side."""
    cx, cz = END_CENTRE
    fx, fz = p[0] - cx, p[1] - cz
    b = fx * t[0] + fz * t[1]
    root = math.sqrt(b * b - (fx * fx + fz * fz - r * r))
    a = max((-b + root, -b - root), key=lambda a: p[0] + a * t[0])
    return p[0] + a * t[0], p[1] + a * t[1]


def filleted(corners, radii, segments=6):
    """A closed polygon's outline (its corners in order) with each corner rounded by its radius, whichever way it turns:
    the same number of points for the same corners and radii (a radius of 0 keeps its corner)."""
    points = []
    for i, r in enumerate(radii):
        (px, pz), (cx, cz), (nx, nz) = corners[i - 1], corners[i], corners[(i + 1) % len(corners)]
        if r <= 0:
            points.append((cx, cz))
            continue
        ux, uz, wx, wz = px - cx, pz - cz, nx - cx, nz - cz
        lu, lw = math.hypot(ux, uz), math.hypot(wx, wz)
        ux, uz, wx, wz = ux / lu, uz / lu, wx / lw, wz / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uz * wz))) / 2
        t = r / math.tan(half)
        bx, bz = ux + wx, uz + wz
        lb = math.hypot(bx, bz)
        ox, oz = cx + bx / lb * r / math.sin(half), cz + bz / lb * r / math.sin(half)
        a1 = math.atan2(cz + uz * t - oz, cx + ux * t - ox)
        a2 = math.atan2(cz + wz * t - oz, cx + wx * t - ox)
        sweep = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi     # the short way round, back where the corner turns in
        points += [(ox + r * math.cos(a1 + sweep * k / segments), oz + r * math.sin(a1 + sweep * k / segments))
                   for k in range(segments + 1)]
    return points


def end_corners(inset, arc_steps):
    """The outline's right half as corners and their radii, from where the bottom turns up its step round the grip to
    where the top's step turns into the top, moved in by inset: a corner turning out rounds less as it moves in, one
    turning in more."""
    s = math.sqrt(0.5)
    f = 1 / math.hypot(1.0, GRIP["fall"])
    along, inwards = (-f, GRIP["fall"] * f), (-GRIP["fall"] * f, -f)      # the grip's top, anticlockwise
    grip_top = (GRIP["top"][0] + inwards[0] * inset, GRIP["top"][1] + inwards[1] * inset)
    riser_b = (STEP_BOTTOM[0] - s * inset, STEP_BOTTOM[1] + s * inset)
    riser_t = (STEP_TOP[0] - s * inset, STEP_TOP[1] - s * inset)
    foot = meet((0.0, inset), (1.0, 0.0), riser_b, (s, s))
    under = meet(riser_b, (s, s), (0.0, GRIP["bottom"] + inset), (1.0, 0.0))
    heel = on_end((0.0, GRIP["bottom"] + inset), (1.0, 0.0), END_RADIUS - inset)
    head = on_end(grip_top, (-along[0], -along[1]), END_RADIUS - inset)
    inside = meet(grip_top, along, riser_t, (-s, s))
    brow = meet(riser_t, (-s, s), (0.0, HEIGHT - inset), (-1.0, 0.0))
    cx, cz = END_CENTRE
    a0, a1 = math.atan2(heel[1] - cz, heel[0] - cx), math.atan2(head[1] - cz, head[0] - cx)
    end = arc(cx, cz, END_RADIUS - inset, a0, a1, arc_steps)[1:-1]
    runs = [line(foot, under, 2)[1:], line(under, heel, 4)[1:], end, line(head, inside, 4)[1:], line(inside, brow, 2)[1:]]
    corners, radii = [], []
    for name, corner, run in zip(("foot", "under", "heel", "head", "inside", "brow"),
                                 (foot, under, heel, head, inside, brow), runs + [[]]):
        r = RADII[name]
        corners += [corner] + run
        radii += [r + inset if name in ("under", "inside") else max(0.3, r - inset)] + [0.0] * len(run)
    return corners, radii


def body_outline(inset=0.0, arc_steps=24, fillet_steps=6):
    """The body's outline moved in by inset (out, if negative), anticlockwise from the front, from the right's step up
    from the bottom: the same number of points at every inset, so outlines can be joined into rings."""
    corners, radii = end_corners(inset, arc_steps)
    left = [(-x, z) for x, z in reversed(corners)]
    (x0, _), (x1, _) = corners[0], corners[-1]
    top = line((x1, HEIGHT - inset), (-x1, HEIGHT - inset), 8)[1:]
    bottom = line((-x0, inset), (x0, inset), 8)[1:]
    return filleted(corners + top + left + bottom,
                    radii + [0.0] * len(top) + radii[::-1] + [0.0] * len(bottom), fillet_steps)


def shoulder_outline(side=1, arc_steps=4):
    """A shoulder button's outline (side 1 R, the right's; -1 L), clockwise as the face is seen: its top from where the
    top edge's strip ends, out to the grip's end and rounding down onto it, proud of the body, down it to SHOULDER's
    end; then back inside the body, where the rest of it is hidden."""
    sh = SHOULDER
    cx, cz = END_CENTRE
    r = END_RADIUS + sh["out"]
    f = 1 / math.hypot(1.0, sh["fall"])
    start = (sh["x"], sh["top"])
    corner = on_end(start, (f, -sh["fall"] * f), r)
    a0 = math.atan2(corner[1] - cz, corner[0] - cx) - math.radians(4.0)   # the end's first chord long enough to round
    a1 = math.asin((sh["end"] - cz) / r)
    corners = [start] + line(start, corner, 3)[1:] + [corner] + arc(cx, cz, r, a0, a1, arc_steps) + [(sh["x"], sh["end"])]
    radii = [0.0, 0.0, 0.0, sh["corner"]] + [0.0] * (arc_steps + 2)
    points = filleted(corners, radii, 8)
    return points if side > 0 else [(-x, z) for x, z in reversed(points)]


def loop_outline(arc_steps=3):
    """The strap's loop's outline at the bottom left, anticlockwise as the face is seen: from inside the body out to the
    grip's end and down it, proud of the body, down the bar and along the bottom to LOOP's foot; back inside the body
    to the slot's floor, round the slot to its roof, and inside the body again."""
    lp = LOOP
    cx, cz = END_CENTRE
    s = math.sqrt(0.5)
    r = END_RADIUS + lp["out"]
    tx, tz = lp["through"]
    a0 = math.asin((lp["top"] - cz) / r)
    jx, jz = on_end((-tx, tz), (s, s), r)                    # where the bar leaves the end, mirrored to the right
    end = [(-x, z) for x, z in arc(cx, cz, r, a0, math.atan2(jz - cz, jx - cx), arc_steps)]
    floor, roof = lp["slot"]
    inner = tx + tz + lp["bar"] / s                           # x + z along the bar's inside (tx + tz along its outside)
    step = STEP_BOTTOM[1] - STEP_BOTTOM[0] + 0.8              # x + z just inside the body's step
    corners = ([(-(end_x(lp["top"]) - 1.2), lp["top"])] + end
               + [(tx + tz + lp["out"], -lp["out"]), (lp["foot"], -lp["out"]), (step - floor, floor),
                  (inner - floor, floor), (inner - roof, roof), (step - roof, roof), (step - roof, lp["top"])])
    radii = [0.0] * (arc_steps + 1) + [3.0, 2.0, 0.0, 0.0, 0.8, 0.8, 0.0, 0.0]   # those in the body sharp
    return filleted(corners, radii, 6)


def sag(x, z):
    """How far the back's flat sags towards the face at (x, z) (DOME)."""
    x0, x1 = DOME["x"]
    u = min(1.0, max(0.0, (abs(x) - x0) / (x1 - x0)))
    w = min(1.0, max(0.0, min(z - GRIP["bottom"], GRIP["top"][1] - z) / DOME["fade"] + 1.0))
    return DOME["depth"] * u * u * w * w * (3 - 2 * w)


def end_x(z, inset=0.0):
    """Where the right end's arc is at height z (the outline moved in by inset)."""
    cx, cz = END_CENTRE
    r = END_RADIUS - inset
    return cx + math.sqrt(max(0.0, r * r - (z - cz) ** 2))


def rounded_rect(x0, x1, z0, z1, radii, inset=0.0, steps=6):
    """A rectangle's outline with its corners rounded (bottom right, top right, top left, bottom left), moved in by
    inset, anticlockwise from its bottom edge: the same number of points at every inset."""
    corners = [(x1, z0, -90.0), (x1, z1, 0.0), (x0, z1, 90.0), (x0, z0, 180.0)]
    pts = []
    for (x, z, a0), r in zip(corners, radii):
        r = max(r - inset, 0.2)
        sx = -1 if x == x1 else 1
        sz = 1 if z == z0 else -1
        cx, cz = x + sx * (r + inset), z + sz * (r + inset)
        pts += [(cx + r * math.cos(math.radians(a0 + 90 * k / steps)), cz + r * math.sin(math.radians(a0 + 90 * k / steps)))
                for k in range(steps + 1)]
    return pts


def door_outline(inset=0.0, steps=8):
    (x0, x1), (z0, z1) = DOOR["x"], DOOR["z"]
    return rounded_rect(x0, x1, z0, z1, DOOR["radii"], inset, steps)


def umd_outline(inset=0.0, corner_steps=6, top_steps=36):
    """The UMD's outline about its disc's middle, anticlockwise from its label side: a flat bottom with rounded corners,
    straight sides, and a half circle over the top."""
    hw, r = UMD["width"] / 2 - inset, UMD["radius"] - inset
    c = max(UMD["corner"] - inset, 0.3)
    z0 = UMD["bottom"] + inset
    points = line((-hw + c, z0), (hw - c, z0), 10)
    points += arc(hw - c, z0 + c, c, -math.pi / 2, 0.0, corner_steps)[:-1]
    points += line((hw, z0 + c), (hw, 0.0), 6)
    points += arc(0.0, 0.0, r, 0.0, math.pi, top_steps)[:-1]
    points += line((-hw, 0.0), (-hw, z0 + c), 6)
    points += arc(-hw + c, z0 + c, c, math.pi, 3 * math.pi / 2, corner_steps)[:-1]
    return points


def pentagon(x, z, degrees):
    """A D-pad button: a home plate pointing at the pad's middle, (x, z), from direction degrees. Corners
    anticlockwise, and their radii."""
    local = [(3.7, 0.0), (6.3, -4.3), (12.2, -4.3), (12.2, 4.3), (6.3, 4.3)]
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(x + u * c - v * s, z + u * s + v * c) for u, v in local], [1.0, 1.3, 1.8, 1.8, 1.3]


def shield(x, z):
    """HOME, SELECT and START: a flat top, its bottom bowed. Corners anticlockwise, and their radii."""
    return [(x, z - 2.6), (x + 5.75, z - 0.9), (x + 5.75, z + 1.8), (x - 5.75, z + 1.8), (x - 5.75, z - 0.9)], \
        [7.0, 1.4, 1.1, 1.1, 1.4]


def face_centres():
    """Each face button: (name, x, z)."""
    return [(n, FACE["x"] + FACE["reach"] * math.cos(math.radians(a)), FACE["z"] + FACE["reach"] * math.sin(math.radians(a)))
            for n, a in FACE_BUTTONS]


def rounded_polygon(corners, radii, segments=10):
    """A convex polygon's outline (anticlockwise corners) with each corner rounded by its radius."""
    n = len(corners)
    points = []
    for i in range(n):
        (px, pz), (cx, cz), (nx, nz) = corners[i - 1], corners[i], corners[(i + 1) % n]
        ux, uz = px - cx, pz - cz
        wx, wz = nx - cx, nz - cz
        lu, lw = math.hypot(ux, uz), math.hypot(wx, wz)
        ux, uz, wx, wz = ux / lu, uz / lu, wx / lw, wz / lw
        half = math.acos(max(-1.0, min(1.0, ux * wx + uz * wz))) / 2
        r = radii[i]
        t = r / math.tan(half)
        bx, bz = ux + wx, uz + wz
        lb = math.hypot(bx, bz)
        ox, oz = cx + bx / lb * r / math.sin(half), cz + bz / lb * r / math.sin(half)
        a1 = math.atan2(cz + uz * t - oz, cx + ux * t - ox)
        a2 = math.atan2(cz + wz * t - oz, cx + wx * t - ox)
        while a2 < a1:
            a2 += 2 * math.pi
        points += [(ox + r * math.cos(a1 + (a2 - a1) * k / segments), oz + r * math.sin(a1 + (a2 - a1) * k / segments))
                   for k in range(segments + 1)]
    return points
