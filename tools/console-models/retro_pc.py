"""The console theme's DOS, Windows 3.x and Windows 9x system models (godot/themes/console/models/systems/dos.glb,
windows3x.glb, windows9x.glb): a PC of each one's era, its CRT monitor and its keyboard (and for Windows its mouse on
its pad), its screen a video.

Each card's set is its own layout's (dos_layout.py, windows3x_layout.py, windows9x_layout.py), the parts they share
retro_pc_layout.py's. Built in Blender from their measurements:
- the case: a desktop's cover behind its front bezel on four feet, or a tower's; the parts standing proud of its front
  by their depth (the drives' faces, the buttons, the keylock, the power switch), its drive's slot cut through them; its
  front printed (the badge, the turbo display, the lights, the drives' faces);
- the monitor: its front shell, the screen's opening sloping in to the curved glass, the knobs and the button standing
  out of the strip under it, the tube's housing tapering behind, on a tilt-and-swivel foot; its front printed;
- the keyboard: its side outline across its width (the ledge for the palms, the keys' well sloping up to the back, the
  ledge with the lights and the badge), the well cut into it; its keys standing in the well, each tapering to its top,
  the rows sculpted a little, their legends printed on their tops; its cord to the case;
- the floppy, the CD and the mouse where a set has them.
The printing is three textures drawn by retro_pc_print.py: `print` (the keyboard from above, the media), `devices` (the
case's front, the monitor's front) and the glass's still, with the swatches the plain parts take their colours from.

The glass's material is `video`: while the card is focused (in the systems grid and on the system's details), the
launcher plays the theme's video for it there (godot/themes/console/videos/<set>.mp4, drawn by retro_pc_video.py),
starting it again each time the clip loops (A6 Card videos); otherwise, and where there's no decoder, it shows its own
texture, the video's first frame.

A node tree (card.finish()): the root (the turn to the set's three-quarter view; then the model spec's fit) holding the
set and its moving parts: the media (waiting in their seats, shrunk to nothing), the eject button, the lights the clip
turns on (shrunk to nothing while they're off), the keys it presses. The `focused` clip's timing is the set's layout's,
which its video follows frame for frame.

Three materials (print, devices, video) and three textures, within the system model budget. Run from the repo root
(`<set>`: dos, windows3x or windows9x):

    python tools/console-models/retro_pc_print.py <set> artifacts/made-up-games artifacts/retro-pc
    python tools/console-models/retro_pc_video.py <set> artifacts/made-up-games godot/themes/console/videos/<set>.mp4
    blender -b --factory-startup --python tools/console-models/retro_pc.py -- artifacts/retro-pc <set> godot/themes/console/models/systems/<set>.glb
"""

import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retro_pc_layout as K  # noqa: E402
from amiga import curved, paint, rounded, solid  # noqa: E402
from card import Atlas, coloured, curve, finish, materials, smoothed  # noqa: E402
from clip import HIDDEN, Pose  # noqa: E402
from mega_drive_cartridge import bevel, boolean, box, join, new_object, prism_x  # noqa: E402

ROUGHNESS = dict(print=0.5, devices=0.55, dark=0.6, video=0.25)
WELL = Matrix.Translation((0.0, K.WELL_Y, K.WELL_Z)) @ Matrix.Rotation(K.SLOPE, 4, "X")   # the keys' frame


def ring(cx, cy, rx, ry, z, n=24):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n), z) for k in range(n)]


def front_painter(uv, x0, z1):
    """Paints a face seen from the front with a region drawn from (x0, z1), its top left: a across, b down."""
    return lambda co: uv(co.x - x0, z1 - co.z)


class Set:
    """The set being built: its layout, its atlases and its materials."""

    def __init__(self, name, images):
        self.s = importlib.import_module(name + "_layout")
        self.name = name
        self.print = Atlas(K.ATLAS, self.s.PRINT_REGIONS, self.s.SWATCHES)
        self.devices = Atlas(K.ATLAS, self.s.DEVICE_REGIONS, self.s.SWATCHES)
        load = lambda f: bpy.data.images.load(os.path.join(images, f"{name}_{f}.png"))   # noqa: E731
        self.m = materials(dict(print="#FFFFFF", devices="#FFFFFF", dark=self.s.COLOURS["dark"], video="#FFFFFF"),
                           ROUGHNESS, dict(print=load("print"), devices=load("devices"), video=load("screen")))

    def plain(self, obj, colour, atlas=None):
        return coloured(obj, self.m["devices" if atlas is None else "print"], atlas or self.devices, colour)

    # ---- The case ----------------------------------------------------------------------------------------------------

    def case(self):
        """The desktop case: the cover behind the bezel, on its feet; the parts standing proud of the front; drive A's
        slot cut through the bezel and its drive's face. Returns the parts and the slot's middle (x, z)."""
        c, s = self.s.CASE, self.s
        w, d, h, feet, bz = c["width"], c["depth"], c["height"], c["feet"], c["bezel"]
        face = front_painter(self.devices.uv("front", w, h - feet), -w / 2, h)
        cover = box("cover", -w / 2 + 2.5, w / 2 - 2.5, bz - 4.0, d, feet, h - 2.0, self.m["devices"])
        bevel(cover, 3.0, segments=2)
        self.plain(cover, "case")
        bezel = box("bezel", -w / 2, w / 2, 0.0, bz, feet, h, self.m["devices"])
        bevel(bezel, 2.5, segments=2)
        raised = {}
        for kind, a, b, pw, ph, depth, _text in s.FRONT:
            if depth <= 0:
                continue
            x0, z1 = -w / 2 + a, h - b
            if kind == "keylock":
                part = cylinder(kind, x0 + pw / 2, z1 - ph / 2, pw / 2, 1.0, -depth, self.m["devices"])
            else:
                part = box(kind, x0, x0 + pw, -depth, 1.0, z1 - ph, z1, self.m["devices"])
                bevel(part, min(1.2, ph / 6, pw / 6), segments=2)
            raised[kind + str(len(raised))] = part
        cuts = [(s.SLOT, 9.0)] if hasattr(s, "SLOT") else []      # a floppy's slot; a CD tray's opening
        if hasattr(s, "TRAY"):
            cuts.append((s.TRAY["front"], 60.0))
        for (a0, a1, b0, b1), deep in cuts:
            x0, x1, z0, z1 = -w / 2 + a0, -w / 2 + a1, h - b1, h - b0
            for target in [bezel] + [p for p in raised.values() if overlaps(p, x0, x1, z0, z1)]:
                boolean(target, box("cut", x0, x1, -12.0, deep, z0, z1, self.m["dark"]))
        self.plain(bezel, "bezel")
        paint(bezel, self.m["devices"], face, lambda c_, n, name: n.y < -0.9 and name == "devices")
        parts = [cover, bezel]
        for part in raised.values():
            self.plain(part, "bezel")
            paint(part, self.m["devices"], face, lambda c_, n, name: n.y < -0.9 and name == "devices")
            parts.append(part)
        for fx in (-w / 2 + min(30.0, w / 5), w / 2 - min(30.0, w / 5)):
            for fy in (bz + 20.0, d - 30.0):
                parts.append(self.plain(box("foot", fx - 14.0, fx + 14.0, fy - 10.0, fy + 10.0, 0.0, feet + 1.0,
                                            self.m["devices"]), "dark"))
        if hasattr(s, "SLOT"):
            a0, a1, b0, b1 = s.SLOT
            return parts, (-w / 2 + (a0 + a1) / 2, h - (b0 + b1) / 2)
        return parts, (0.0, 0.0)

    def eject_button(self):
        """A drive's eject button, standing out of the drive's face; it moves along y."""
        c, s = self.s.CASE, self.s
        w, h = c["width"], c["height"]
        a0, a1, b0, b1, face, _out = s.EJECT
        x0, x1, z0, z1 = -w / 2 + a0, -w / 2 + a1, h - b1, h - b0
        part = box("eject", x0, x1, -face - 0.8, 3.0, z0, z1, self.m["devices"])
        bevel(part, 0.6, segments=2)
        self.plain(part, "bezel")
        paint(part, self.m["devices"], front_painter(self.devices.uv("front", w, h - c["feet"]), -w / 2, h),
              lambda c_, n, name: n.y < -0.9)
        return part

    def tray(self):
        """The CD-ROM drive's tray, its front's middle at its origin (it slides out along -y): its front panel, printed
        as the drive's face shows it, and the thin tray behind it, its top the tray's well (devices `tray_top`)."""
        c, t = self.s.CASE, self.s.TRAY
        w, h = c["width"], c["height"]
        a0, a1, b0, b1 = t["front"]
        x0, x1, z0, z1 = -w / 2 + a0 + 0.4, -w / 2 + a1 - 0.4, h - b1 + 0.4, h - b0 - 0.4
        face, depth = t["face"], t["depth"]
        panel = box("tray_front", x0, x1, -face, 3.0, z0, z1, self.m["devices"])
        bevel(panel, 0.6, segments=1)
        slab = box("tray", x0 + 2.0, x1 - 2.0, 2.0, depth, z0 + 1.0, z0 + 1.0 + t["thickness"], self.m["devices"])
        part = join([panel, slab], "tray")
        self.plain(part, "tray")
        front = front_painter(self.devices.uv("front", w, h - c["feet"]), -w / 2, h)
        paint(part, self.m["devices"], front, lambda c_, n, name: n.y < -0.9 and c_.y < 0.0)
        top = self.devices.uv("tray_top", x1 - x0 - 4.0, depth - 2.0)
        paint(part, self.m["devices"], lambda co: top(co.x - x0 - 2.0, depth - co.y),
              lambda c_, n, name: n.z > 0.9 and c_.y > 1.0)
        middle = Vector(((x0 + x1) / 2, -face, (z0 + z1) / 2))
        part.data.transform(Matrix.Translation(-middle))
        return part, middle, z0 + 1.0 + t["thickness"] - middle.z

    def cd(self):
        """The CD, its middle at its origin, its label up, its data side silver."""
        r, t = K.CD["radius"], K.CD["thickness"]
        disc = solid("cd", [[(r * math.cos(2 * math.pi * k / 48), r * math.sin(2 * math.pi * k / 48), z)
                             for k in range(48)] for z in (-t / 2, t / 2)], self.m["print"])
        self.plain(disc, "disc", self.print)
        label = self.print.uv("cd", 2 * r, 2 * r)
        paint(disc, self.m["print"], lambda co: label(co.x + r, r - co.y), lambda c_, n, name: n.z > 0.9)
        return disc

    def bead(self, name, size, colour, round_=False):
        """A light lit: a bead standing a little out of its printed one, its middle at its origin."""
        w, h = size
        if round_:
            part = cylinder(name, 0.0, 0.0, w / 2, 0.6, -1.0, self.m["devices"], 12)
        else:
            part = box(name, -w / 2, w / 2, -1.0, 0.6, -h / 2, h / 2, self.m["devices"])
        return self.plain(part, colour)

    # ---- The monitor -------------------------------------------------------------------------------------------------

    def monitor(self):
        """The CRT on its foot: the front shell, the screen's opening sloping in to the glass, the strip's knobs and
        button, the tube's housing; its front printed."""
        mon = self.s.MONITOR
        ax, ay, az = mon["at"]
        w, h, shell = mon["width"], mon["height"], mon["shell"]
        fr, fh = mon["foot"]
        z0 = az + fh
        foot = solid("foot", [ring(ax, ay + 150.0, rx, ry, z) for rx, ry, z in
                              ((fr, fr * 0.9, az), (fr, fr * 0.9, az + 5.0), (fr * 0.62, fr * 0.56, az + fh * 0.6),
                               (fr * 0.5, fr * 0.45, z0 + 4.0))], self.m["devices"])
        self.plain(foot, "stand")
        body = box("monitor", ax - w / 2, ax + w / 2, ay, ay + shell, z0, z0 + h, self.m["devices"])
        bevel(body, 9.0, segments=3)
        (ow, oh, orad), (iw, ih, irad) = mon["opening"], mon["inner"]
        cz = z0 + mon["screen_z"]
        outer, inner = rounded(ax, cz, ow, oh, orad, 5), rounded(ax, cz, iw, ih, irad, 5)
        back = rounded(ax, cz, iw - 24.0, ih - 24.0, irad, 5)
        recess = mon["recess"]
        cutter = solid("opening", [[(x, ay - 6.0, z) for x, z in outer], [(x, ay + 0.01, z) for x, z in outer],
                                   [(x, ay + recess, z) for x, z in inner],
                                   [(x, ay + recess + 16.0, z) for x, z in back]], self.m["devices"])
        boolean(body, cutter)
        self.plain(body, "monitor")
        face = front_painter(self.devices.uv("monitor", w, h), ax - w / 2, z0 + h)
        paint(body, self.m["devices"], face, lambda c_, n, name: n.y < -0.95 and c_.y < ay + 1.0)
        r = mon["rear"]
        (rw, rh), (ew, eh) = r["size"], r["end"]
        mid = z0 + h * 0.5
        sections = ((ay + shell - 3.0, mid, rw, rh, 22.0),         # the tube's housing: y, its middle, its size
                    (ay + shell + r["depth"] * 0.45, mid + r["rise"] * 0.5, (rw + ew) / 2 + 8.0,
                     (rh + eh) / 2 + 6.0, 24.0),
                    (ay + shell + r["depth"], mid + r["rise"], ew, eh, 20.0))
        housing = solid("housing", [[(x, y, z) for x, z in rounded(ax, cz_, cw, ch, cr, 4)]
                                    for y, cz_, cw, ch, cr in sections], self.m["devices"])
        bevel(housing, 4.0, segments=2, angle=50)
        self.plain(housing, "monitor")
        parts = [foot, body, housing]
        for kind, a, b, pw, ph, depth, _text in mon["strip"]:
            if depth <= 0:
                continue
            x0, z1 = ax - w / 2 + a, z0 + h - b
            if kind == "knob":
                part = cylinder(kind, x0 + pw / 2, z1 - ph / 2, pw / 2, ay + 1.0, ay - depth, self.m["devices"], 16)
                bevel(part, 0.8, segments=1, angle=50)
            else:
                part = box(kind, x0, x0 + pw, ay - depth, ay + 1.0, z1 - ph, z1, self.m["devices"])
                bevel(part, 1.2, segments=2)
            self.plain(part, "monitor")
            paint(part, self.m["devices"], face, lambda c_, n, name: n.y < -0.9)
            parts.append(part)
        gh = ih + 8.0
        glass = curved("glass", gh * 4 / 3, gh, mon["bulge"], lambda a, b: (a, 1 - b), self.m["video"], 20, 15)
        glass.data.transform(Matrix.Translation((ax, ay + recess, cz)))
        parts.append(glass)
        return parts

    # ---- The keyboard ------------------------------------------------------------------------------------------------

    def keyboard(self):
        """The keyboard where the set puts it: its case (the well cut into it), its keys; the ones the clip presses
        apart. Returns (static parts, {key name: part}, the keys' travel in the set's frame)."""
        kb = self.s.KEYBOARD
        turn = Matrix.Rotation(math.radians(kb["turn"]), 4, "Z")
        place = Matrix.Translation((kb["at"][0], kb["at"][1], 0.0)) @ turn
        width, depth = K.KB["width"], K.KB["depth"]
        top = self.print.uv("kb_top", width, depth)
        from_above = lambda co: top(co.x + width / 2, depth - co.y)   # noqa: E731
        y0, z0 = K.deck(0.0, K.RIM)
        y1, z1 = K.deck(K.WELL_LENGTH, K.RIM)
        by, bz = K.BACK_LEDGE
        front, back = K.KB["front"], K.KB["back"]
        profile = [(1.5, 0.0), (depth - 1.5, 0.0), (depth, 1.5), (depth, back - 3.0), (depth - 3.0, back), (by, back),
                   (y1 + 1.0, z1 + 1.0), (y1, z1), (y0, z0), (y0 - 9.0, front + 2.6), (3.0, front), (0.0, front - 2.5),
                   (0.0, 1.5)]
        body = prism_x("keyboard", profile, -width / 2, width / 2, self.m["print"])
        bevel(body, 2.0, segments=2, angle=30)
        x0, x1 = K.KEYS_X0 - 5.0, K.KEYS_X0 + 23 * K.U + 5.0
        well = box("well", x0, x1, 2.5, K.WELL_LENGTH - 2.5, 0.0, 30.0, self.m["print"])
        well.data.transform(WELL)
        boolean(body, well)
        self.plain(body, "kbcase", self.print)
        paint(body, self.m["print"], from_above, lambda c_, n, name: n.z > 0.6)
        static, moving = [body], {}
        pressed = set(getattr(self.s, "PRESSES", {}))
        for key in K.keys(kb["windows"]):
            kx0, ks0, kx1, ks1 = K.key_base(key)
            tx0, ts0, tx1, ts1, th = K.key_top(key)
            cap = solid("key_" + key["name"], [[(kx0, ks0, -2.0), (kx1, ks0, -2.0), (kx1, ks1, -2.0), (kx0, ks1, -2.0)],
                                               [(kx0, ks0, 2.0), (kx1, ks0, 2.0), (kx1, ks1, 2.0), (kx0, ks1, 2.0)],
                                               [(tx0, ts0, th), (tx1, ts0, th), (tx1, ts1, th), (tx0, ts1, th)]],
                        self.m["print"])
            bevel(cap, 0.9, segments=1, angle=30)
            cap.data.transform(WELL)
            self.plain(cap, key["colour"], self.print)
            paint(cap, self.m["print"], from_above, lambda c_, n, name: n.z > 0.85)
            cap.data.transform(place)
            (moving.__setitem__(key["name"], cap) if key["name"] in pressed else static.append(cap))
        body.data.transform(place)
        travel = (place.to_3x3() @ WELL.to_3x3()) @ Vector((0.0, 0.0, -K.PRESS))
        return static, moving, travel

    def cables(self):
        out = []
        for cable in getattr(self.s, "CABLES", ()):
            out.append(self.plain(tube(cable["name"], [Vector(p) for p in curve(cable["points"], 8)], cable["r"],
                                       self.m["print"]), "cable", self.print))
        return out

    # ---- The mouse and its pad ---------------------------------------------------------------------------------------

    def mouse(self):
        """The mouse, its middle at its origin on the pad's top, its buttons towards +y: its outline lofted up to a dome
        highest behind its middle; its top printed (the buttons' seams), its sides in its colour."""
        h = K.MOUSE["height"]
        outline = K.mouse_outline()
        rings = []
        for z, k, back in ((0.0, 0.93, 0.0), (2.0, 1.0, 0.0), (h * 0.42, 0.99, 0.0), (h * 0.72, 0.9, -6.0),
                           (h * 0.9, 0.7, -10.0), (h, 0.34, -13.0)):
            rings.append([(x * k, y * k + back, z) for x, y in outline])
        body = solid("mouse", rings, self.m["print"])
        for poly in body.data.polygons:
            poly.use_smooth = True
        length, (wb, _wf) = K.MOUSE["length"], K.MOUSE["width"]
        top = self.print.uv("mouse_top", wb, length)
        self.plain(body, "mouse", self.print)
        paint(body, self.m["print"], lambda co: top(co.x + wb / 2, length / 2 - co.y), lambda c_, n, name: n.z > 0.35)
        return body

    def pad(self):
        """The mouse pad, its top printed."""
        (w, d), t, r = K.PAD["size"], K.PAD["thickness"], K.PAD["radius"]
        mp = self.s.MOUSE
        part = solid("pad", [[(x, y, z) for x, y in rounded(0.0, 0.0, w, d, r, 4)] for z in (0.0, t)], self.m["print"])
        self.plain(part, "pad", self.print)
        top = self.print.uv("pad", w, d)
        paint(part, self.m["print"], lambda co: top(co.x + w / 2, d / 2 - co.y), lambda c_, n, name: n.z > 0.9)
        part.data.transform(Matrix.Translation((mp["pad"][0], mp["pad"][1], 0.0))
                            @ Matrix.Rotation(math.radians(mp["pad_turn"]), 4, "Z"))
        return part

    # ---- The media ---------------------------------------------------------------------------------------------------

    def floppy(self):
        """The 3.5-inch floppy, its middle at its origin, lying flat, its shutter's end towards +y (into the drive),
        its label up."""
        (w, length), t = K.FLOPPY["size"], K.FLOPPY["thickness"]
        part = box("disk", -w / 2, w / 2, -length / 2, length / 2, -t / 2, t / 2, self.m["print"])
        bevel(part, 0.5, segments=1)
        self.plain(part, "disk", self.print)
        top = self.print.uv("floppy", w, length)
        under = self.print.uv("floppy_under", w, length)
        paint(part, self.m["print"], lambda co: top(co.x + w / 2, length / 2 - co.y), lambda c_, n, name: n.z > 0.9)
        paint(part, self.m["print"], lambda co: under(w / 2 - co.x, length / 2 - co.y), lambda c_, n, name: n.z < -0.9)
        return part


def overlaps(obj, x0, x1, z0, z1):
    """Whether obj's vertices span a box that overlaps x0..x1 and z0..z1."""
    xs = [v.co.x for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return min(xs) < x1 and max(xs) > x0 and min(zs) < z1 and max(zs) > z0


def cylinder(name, x, z, r, y0, y1, mat, n=20):
    """A cylinder along y, from y0 to y1, its axis at (x, z)."""
    return solid(name, [[(x + r * math.cos(2 * math.pi * k / n), y, z + r * math.sin(2 * math.pi * k / n))
                         for k in range(n)] for y in (y0, y1)], mat)


def tube(name, points, r, mat, sides=8):
    """A cable along points (Vectors), r thick, its ends capped."""
    bm = bmesh.new()
    rings = []
    normal = Vector((0.0, 0.0, 1.0))
    n = len(points) - 1
    for k, p in enumerate(points):
        tangent = (points[min(k + 1, n)] - points[max(k - 1, 0)]).normalized()
        normal = (normal - tangent * normal.dot(tangent))
        normal = normal.normalized() if normal.length > 1e-6 else tangent.orthogonal().normalized()
        binormal = tangent.cross(normal)
        rings.append([bm.verts.new(p + (normal * math.cos(2 * math.pi * j / sides)
                                        + binormal * math.sin(2 * math.pi * j / sides)) * r) for j in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            bm.faces.new([a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


# ---- The clip --------------------------------------------------------------------------------------------------------

def timeline_for(s, travel):
    """The set's clip: its layout's poses for its media and buttons, its lights on or off, its keys pressed."""
    def timeline(f):
        poses = {}
        if hasattr(s, "disk"):
            p = s.disk(f)
            poses["disk"] = Pose(x=p.get("x", 0.0), y=p.get("y", 0.0), z=p.get("z", 0.0), pitch=p.get("pitch", 0.0),
                                 scale=max(HIDDEN, p.get("scale", 1.0)))
        if hasattr(s, "eject"):
            poses["eject"] = Pose(y=-s.eject(f))
        if hasattr(s, "tray"):
            poses["tray"] = Pose(y=-s.tray(f))
        if hasattr(s, "cd"):
            p = s.cd(f)
            poses["cd"] = Pose(y=p.get("y", 0.0), z=p.get("z", 0.0), pitch=p.get("pitch", 0.0),
                               scale=max(HIDDEN, p.get("scale", 1.0)))
        for name in getattr(s, "LIGHTS", {}):
            poses[name] = Pose() if s.lit(name, f) else Pose(scale=HIDDEN)
        for name, presses in getattr(s, "PRESSES", {}).items():
            down = travel * K.pressed(f, presses)
            poses["key_" + name] = Pose(x=down.x, y=down.y, z=down.z)
        if hasattr(s, "mouse_offset"):                   # the mouse where the screen's pointer is, dipping as it clicks
            x, y = s.mouse_offset(f)
            click = K.pressed(f, s.CLICKS)
            poses["mouse"] = Pose(x=x, y=y, z=-1.0 * click, squash=0.04 * click)
        return poses
    return timeline


# ---- Main ------------------------------------------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    images, name, out = os.path.abspath(args[0]), args[1], os.path.abspath(args[2])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    built = Set(name, images)
    s = built.s
    bpy.context.scene.render.fps = s.FPS
    case, (slot_x, slot_z) = built.case()
    static, keys, travel = built.keyboard()
    extras = [built.pad()] if hasattr(s, "MOUSE") else []
    whole = smoothed(join(case + built.monitor() + static + built.cables() + extras, name), 35.0)
    parts = {}
    if hasattr(s, "MOUSE"):
        mx, my = s.MOUSE["at"]
        rodent = built.mouse()
        rodent.rotation_euler = (0.0, 0.0, math.radians(s.MOUSE["turn"]))
        parts["mouse"] = (rodent, Vector((mx, my, K.PAD["thickness"])))
    for key, cap in keys.items():
        parts["key_" + key] = (smoothed(cap, 35.0), Vector())
    if hasattr(s, "disk"):
        seat = Vector((slot_x, K.FLOPPY["size"][1] / 2 + 1.0, slot_z))
        parts["disk"] = (smoothed(built.floppy(), 40.0), seat)
    if hasattr(s, "eject"):
        parts["eject"] = (built.eject_button(), Vector())
    if hasattr(s, "TRAY"):
        tray, tray_at, top = built.tray()
        parts["tray"] = (smoothed(tray, 30.0), tray_at)
        well = Vector((0.0, s.TRAY["face"] + s.TRAY["well"], top + K.CD["thickness"] / 2 + 0.3))
        parts["cd"] = (built.cd(), well, "tray")
    w, h = s.CASE["width"], s.CASE["height"]
    for light, (a, b, out_, size, colour, round_) in s.LIGHT_PARTS.items():
        parts[light] = (built.bead(light, size, colour, round_), Vector((-w / 2 + a, -out_, h - b)))
    finish(name, whole, parts, timeline_for(s, travel), s.LENGTH, s.YAW, s.PITCH, out, s.NAME)


if __name__ == "__main__":
    main()
