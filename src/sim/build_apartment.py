"""
Generate the one-bedroom flat as a MuJoCo model: models/domestic_environment.xml

Rooms: living + dining (open plan, hardwood), hallway (laminate), bedroom (carpet), joined by a
0.90 m and a 0.85 m doorway.  Furniture comes from the original living-room scene (sofa, coffee
table, TV, shelf, lamp, mug/book/remote/ball) plus a dining table with four free chairs, a bed,
wardrobe, nightstands, a kitchen counter, plants, a curled rug edge with slippers (the reason she
trips) and a robot vacuum that moves around as a dynamic obstacle (mocap body).

Conventions used by the rest of the project
  * geom group 0  visible furniture / cut-away walls          (shown)
  * geom group 2  full-height visual walls                     (hidden by default; toggle on)
  * geom group 4  collision slabs and wall colliders (hidden by group; mj_ray hits them, but note it
                  skips geoms with alpha 0, so they must not be made transparent)
  * human capsules are group 3, human skin is group 1          (see build_human_mjcf.py)
  * floor slabs carry priority=1 so their friction wins over the feet/wheels
  * contype/conaffinity: furniture 1/1, human 2/1 (collides with the world, not with itself)

Run:  python src/sim/build_apartment.py     (also regenerates the textures)
"""
import os

import numpy as np

import apartment_layout as L
import make_textures

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "models", "domestic_environment.xml")


def f(v):
    return " ".join(f"{x:.4g}" for x in np.atleast_1d(v))


def geom(kind, size, pos=(0, 0, 0), rgba="0.7 0.7 0.7 1", euler=None, mass=None, group=None,
         solid=True, name=None, material=None, friction=None, extra=""):
    a = []
    if name:
        a.append(f'name="{name}"')
    a.append(f'type="{kind}" size="{f(size)}" pos="{f(pos)}"')
    if euler is not None:
        a.append(f'euler="{f(euler)}"')
    if material:
        a.append(f'material="{material}"')
    else:
        a.append(f'rgba="{rgba}"')
    if mass is not None:
        a.append(f'mass="{mass}"')
    if group is not None:
        a.append(f'group="{group}"')
    if not solid:
        a.append('contype="0" conaffinity="0"')
    if friction:
        a.append(f'friction="{friction}"')
    if extra:
        a.append(extra)
    return "<geom " + " ".join(a) + "/>"


def rug_colliders(hx, hy, h=0.012, ramp=0.12):
    """Rug collider with sloped edges (about 5.7 degrees): a raised block plus four thin tilted ramps. A vertical lip of even 0.5 cm stopped the
    small robot's frictionless front skid at low speed (found by driving it across the living-room door line, see CLAUDE.md)."""
    fr = "0.68 0.005 0.0001"
    kw = dict(solid=True, group=4, rgba="0.5 0.5 0.5 1", friction=fr, extra='priority="1"')
    ang = float(np.degrees(np.arctan2(h, ramp)))
    out = [geom("box", (hx - ramp, hy - ramp, h / 2), (0, 0, h / 2), **kw)]
    half = ramp / 2 / np.cos(np.radians(ang))
    zc = h / 2 - 0.002
    out += [geom("box", (hx - ramp, half, 0.002), (0, -(hy - ramp / 2), zc), euler=(ang, 0, 0), **kw),
            geom("box", (hx - ramp, half, 0.002), (0, (hy - ramp / 2), zc), euler=(-ang, 0, 0), **kw),
            geom("box", (half, hy - ramp, 0.002), ((hx - ramp / 2), 0, zc), euler=(0, ang, 0), **kw),
            geom("box", (half, hy - ramp, 0.002), (-(hx - ramp / 2), 0, zc), euler=(0, -ang, 0), **kw)]
    return out


def body(name, pos, geoms, euler=None, joint=None, mocap=False, ind=2):
    pad = "  " * ind
    a = f'name="{name}" pos="{f(pos)}"' + (f' euler="{f(euler)}"' if euler is not None else "")
    if mocap:
        a += ' mocap="true"'
    out = [f"{pad}<body {a}>"]
    if joint:
        out.append(f'{pad}  <freejoint name="{joint}"/>')
    out += [f"{pad}  {g}" for g in geoms]
    out.append(f"{pad}</body>")
    return out


# --- walls -------------------------------------------------------------------------------------
def wall(name, axis, fixed, lo, hi, openings=(), full_visible=False):
    """Axis-aligned wall. axis 'x': runs along x at y=fixed; openings are (centre, width) along it."""
    t, h = L.WALL_T, L.WALL_H
    cuts = sorted((c - w / 2, c + w / 2) for c, w in openings)
    spans, cur = [], lo
    for a, b in cuts:
        spans.append((cur, a))
        cur = b
    spans.append((cur, hi))

    def box(a, b, z0, z1, **kw):
        c, half = (a + b) / 2, (b - a) / 2
        zc, zh = (z0 + z1) / 2, (z1 - z0) / 2
        if axis == "x":
            return geom("box", (half, t / 2, zh), (c, fixed, zc), **kw)
        return geom("box", (t / 2, half, zh), (fixed, c, zc), **kw)

    out = []
    for i, (a, b) in enumerate(spans):                       # colliders (invisible, full height)
        out.append(box(a, b, 0, h, group=4, rgba="0.5 0.5 0.5 1", name=f"{name}_col{i}"))
    for i, (a, b) in enumerate(cuts):                        # lintels over doorways
        out.append(box(a, b, L.DOOR_H, h, group=4, rgba="0.5 0.5 0.5 1", name=f"{name}_lintel{i}"))
    vis_group = 0 if full_visible else 2                     # full-height visual copy
    for i, (a, b) in enumerate(spans):
        out.append(box(a, b, 0, h, group=vis_group, solid=False, material="wall_paint"))
    for i, (a, b) in enumerate(cuts):
        out.append(box(a, b, L.DOOR_H, h, group=vis_group, solid=False, material="wall_paint"))
    if not full_visible:                                     # cut-away copy that stays visible
        for i, (a, b) in enumerate(spans):
            out.append(box(a, b, 0, L.CUTAWAY_H, group=0, solid=False, material="wall_cut"))
    return out


# --- furniture ---------------------------------------------------------------------------------
def sofa():
    hl = 0.9                                                   # half length (1.8 m sofa)
    c = lambda r: f"{r}"
    g = [
        geom("box", (hl, 0.5, 0.20), (0, 0, 0.20), "0.22 0.26 0.32 1"),                      # base: top 0.40 m
        geom("box", (hl, 0.55, 0.045), (0, -0.05, 0.425), "0.27 0.32 0.40 1"),               # seat cushion: top 0.47 m (a low sofa)
        geom("box", (hl, 0.15, 0.35), (0, 0.45, 0.85), "0.24 0.29 0.36 1"),
        geom("box", (0.10, 0.55, 0.25), (-(hl - 0.05), 0, 0.75), "0.23 0.28 0.35 1"),
        geom("box", (0.10, 0.55, 0.25), (hl - 0.05, 0, 0.75), "0.23 0.28 0.35 1"),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.append(geom("cylinder", (0.05, 0.08), (sx * (hl - 0.15), sy * 0.45, 0.08), "0.15 0.10 0.06 1"))
    g.append(geom("box", (0.22, 0.05, 0.2), (-0.55, 0.3, 0.8), "0.80 0.62 0.40 1", euler=(-12, 0, 0), solid=False))
    g.append(geom("box", (0.22, 0.05, 0.2), (0.55, 0.3, 0.8), "0.55 0.65 0.55 1", euler=(-12, 0, 0), solid=False))
    return g


def coffee_table():
    g = [geom("box", (0.275, 0.5, 0.02), (0, 0, 0.42), "0.45 0.28 0.16 1")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.append(geom("cylinder", (0.025, 0.2), (sx * 0.235, sy * 0.45, 0.2), "0.35 0.22 0.13 1"))
    return g


def dining_table(cx, cy):
    g = [geom("box", (0.7, 0.4, 0.025), (0, 0, 0.725), "0.55 0.38 0.22 1")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.append(geom("box", (0.03, 0.03, 0.35), (sx * 0.65, sy * 0.35, 0.35), "0.42 0.28 0.16 1"))
    return body("dining_table", (cx, cy, 0), g)


def chair(name, x, y, yaw):
    g = [
        geom("box", (0.21, 0.21, 0.02), (0, 0, 0.45), "0.60 0.43 0.26 1", mass=1.8),
        geom("box", (0.21, 0.02, 0.22), (0, -0.19, 0.69), "0.55 0.38 0.22 1", mass=0.9),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.append(geom("box", (0.02, 0.02, 0.22), (sx * 0.18, sy * 0.18, 0.22), "0.45 0.30 0.18 1", mass=0.25))
    return body(name, (x, y, 0), g, euler=(0, 0, yaw), joint=f"{name}_free")


def bed(cx, cy):
    g = [
        geom("box", (0.78, 1.0, 0.14), (0, 0, 0.14), "0.42 0.30 0.20 1"),              # frame
        geom("box", (0.74, 0.96, 0.11), (0, 0, 0.39), "0.92 0.92 0.90 1"),             # mattress (top 0.50 m)
        geom("box", (0.75, 0.58, 0.035), (0, -0.36, 0.535), "0.38 0.50 0.62 1", solid=False),   # duvet
        geom("box", (0.80, 0.04, 0.45), (0, 0.98, 0.55), "0.40 0.28 0.18 1"),         # headboard
        geom("box", (0.30, 0.17, 0.07), (-0.38, 0.75, 0.58), "0.97 0.97 0.97 1", solid=False),
        geom("box", (0.30, 0.17, 0.07), (0.38, 0.75, 0.58), "0.97 0.97 0.97 1", solid=False),
    ]
    return body("bed", (cx, cy, 0), g)


def bookshelf(cx, cy):
    rng = np.random.default_rng(7)
    g = [geom("box", (0.6, 0.16, 0.9), (0, 0, 0.9), "0.62 0.45 0.28 1")]
    for k in range(4):                                                    # shelf lines
        g.append(geom("box", (0.58, 0.01, 0.012), (0, 0.165, 0.35 + 0.42 * k), "0.40 0.28 0.17 1", solid=False))
    for k in range(4):                                                    # books
        x = -0.55
        while x < 0.52:
            w = rng.uniform(0.018, 0.04)
            hgt = rng.uniform(0.14, 0.27)
            col = " ".join(f"{c:.2f}" for c in rng.uniform(0.2, 0.85, 3)) + " 1"
            g.append(geom("box", (w, 0.008, hgt / 2), (x + w, 0.168, 0.362 + 0.42 * k + hgt / 2), col, solid=False))
            x += 2 * w + 0.004
    return body("bookshelf", (cx, cy, 0), g)


def floor_lamp(cx, cy):
    g = [
        geom("cylinder", (0.16, 0.02), (0, 0, 0.02), "0.15 0.15 0.15 1"),
        geom("cylinder", (0.025, 0.8), (0, 0, 0.8), "0.20 0.20 0.20 1"),
        geom("cylinder", (0.2, 0.18), (0, 0, 1.55), "0.95 0.92 0.80 1", solid=False),
    ]
    return body("floor_lamp", (cx, cy, 0), g)


def plant(name, cx, cy, h=0.9):
    g = [geom("cylinder", (0.17, 0.17), (0, 0, 0.17), "0.55 0.35 0.25 1"),
         geom("cylinder", (0.03, h / 2), (0, 0, 0.3 + h / 2 - 0.1), "0.25 0.4 0.2 1", solid=False)]
    for dx, dy, dz, r in ((0, 0, h, 0.22), (0.15, 0.05, h - 0.2, 0.17), (-0.14, -0.06, h - 0.25, 0.18), (0.02, -0.15, h - 0.1, 0.15)):
        g.append(geom("sphere", (r,), (dx, dy, dz), "0.18 0.45 0.22 1", solid=False))
    return body(name, (cx, cy, 0), g)


def vacuum(x, y):
    g = [geom("cylinder", (0.17, 0.045), (0, 0, 0.045), "0.15 0.15 0.18 1", name="vacuum_body"),
         geom("cylinder", (0.12, 0.004), (0, 0, 0.092), "0.75 0.75 0.78 1", solid=False),
         geom("sphere", (0.02,), (0.1, 0, 0.1), "0.2 0.8 0.3 1", solid=False)]
    return body("vacuum", (x, y, 0), g, mocap=True)


def build():
    make_textures.main()
    c = L.RUG_CENTER
    rh = L.RUG_HALF
    A = ["<mujoco model=\"apartment\">",
         "  <!-- Generated by src/sim/build_apartment.py. Edit apartment_layout.py / the builder, not this file. -->",
         '  <compiler angle="degree" inertiafromgeom="true"/>',
         '  <option timestep="0.002" gravity="0 0 -9.81" integrator="implicitfast"/>',
         '  <size memory="256M"/>',
         '  <statistic center="0 -0.3 0.6" extent="8"/>',
         "  <visual>",
         '    <headlight ambient="0.42 0.42 0.42" diffuse="0.45 0.45 0.45" specular="0.1 0.1 0.1"/>',
         '    <global azimuth="90" elevation="-58" offwidth="1280" offheight="960"/>',
         '    <quality shadowsize="4096"/>',
         '    <map znear="0.02" zfar="60"/>',
         "  </visual>",
         "  <asset>",
         '    <texture name="sky" type="skybox" builtin="gradient" rgb1="0.72 0.82 0.92" rgb2="0.96 0.96 0.98" width="512" height="512"/>']
    for nm in ("hardwood", "laminate", "carpet", "rug"):
        A.append(f'    <texture name="tex_{nm}" type="2d" file="textures/{nm}.png"/>')
    for nm, (_, (x0, x1, y0, y1), _, tile) in zip(("hardwood", "laminate", "carpet"), L.FLOORS):
        A.append(f'    <material name="mat_{nm}" texture="tex_{nm}" texrepeat="{(x1 - x0) / tile:.3f} {(y1 - y0) / tile:.3f}" specular="0.1" shininess="0.2"/>')
    A += ['    <material name="mat_rug" texture="tex_rug" texrepeat="1 1" specular="0.02"/>',
          '    <material name="wall_paint" rgba="0.93 0.91 0.87 1" specular="0.02"/>',
          '    <material name="wall_cut" rgba="0.84 0.82 0.78 1" specular="0.02"/>',
          "  </asset>",
          "  <worldbody>"]

    # floors: invisible friction slabs (group 4, priority 1) + textured visual planes
    for nm, (x0, x1, y0, y1), mu, _ in L.FLOORS:
        cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
        A.append("    " + geom("box", (hx, hy, 0.05), (cx, cy, -0.05), group=4, rgba="0.5 0.5 0.5 1",
                               friction=f"{mu} 0.005 0.0001", name=f"floor_{nm}", extra='priority="1"'))
        A.append("    " + geom("plane", (hx, hy, 0.05), (cx, cy, 0.002), solid=False, material=f"mat_{nm}"))

    # walls
    W = []
    W += wall("wall_n", "x", L.Y1, L.X0 - L.WALL_T / 2, L.X1 + L.WALL_T / 2, full_visible=True)
    W += wall("wall_w", "y", L.X0, L.Y0 - L.WALL_T / 2, L.Y1 + L.WALL_T / 2, full_visible=True)
    W += wall("wall_s", "x", L.Y0, L.X0 - L.WALL_T / 2, L.X1 + L.WALL_T / 2)
    W += wall("wall_e", "y", L.X1, L.Y0 - L.WALL_T / 2, L.Y1 + L.WALL_T / 2)
    W += wall("wall_hall", "x", L.HALL_Y, L.X0, L.X1, openings=[L.DOOR_LIVING, L.DOOR_BEDROOM])
    W += wall("wall_part", "y", L.PART_X, L.HALL_Y, L.Y1)
    A += ["    <body name=\"walls\" pos=\"0 0 0\">"] + ["      " + w for w in W] + ["    </body>"]

    # decorative windows and front door (not solid)
    A += body("window_dining", (-0.6, L.Y1 - 0.065, 1.45), [
        geom("box", (0.85, 0.02, 0.6), rgba="0.85 0.85 0.85 1", solid=False),
        geom("box", (0.78, 0.025, 0.53), (0, -0.005, 0), "0.62 0.80 0.93 0.45", solid=False),
        geom("box", (0.012, 0.03, 0.53), (0, -0.01, 0), "0.85 0.85 0.85 1", solid=False)])
    A += body("window_west", (L.X0 + 0.065, 1.3, 1.45), [
        geom("box", (0.02, 0.55, 0.6), rgba="0.85 0.85 0.85 1", solid=False),
        geom("box", (0.025, 0.48, 0.53), (0.005, 0, 0), "0.62 0.80 0.93 0.45", solid=False)])
    A += body("front_door", (L.X0 + 0.07, -2.45, 1.0), [
        geom("box", (0.03, 0.45, 1.0), rgba="0.45 0.30 0.18 1", solid=False),
        geom("sphere", (0.03,), (0.05, 0.33, 0), "0.80 0.72 0.25 1", solid=False)])

    # living room
    A += body("sofa", (-0.06, -0.3, 0), sofa(), euler=(0, 0, -90))
    A += body("coffee_table", (-1.55, -0.3, 0), coffee_table())
    A += body("tv_stand", (-3.24, -0.3, 0), [
        geom("box", (0.2, 0.75, 0.25), (0, 0, 0.25), "0.30 0.18 0.10 1"),
        geom("box", (0.2, 0.75, 0.015), (0, 0, 0.5), "0.32 0.20 0.11 1")])
    A += body("tv", (-3.27, -0.3, 0.515), [
        geom("box", (0.1, 0.3, 0.015), (0, 0, 0.015), "0.08 0.08 0.08 1"),
        geom("box", (0.04, 0.08, 0.1), (0, 0, 0.11), "0.08 0.08 0.08 1"),
        geom("box", (0.025, 0.58, 0.34), (0.01, 0, 0.5), "0.04 0.05 0.07 1")])
    A += bookshelf(-0.8, -1.68)
    # (no floor lamp: its pole and shade made MediaPipe hallucinate a standing person from the fixed camera, see src/experiments/audit_phantoms.py)
    A += plant("plant_dining", 0.28, 2.65, 0.35)
    A += plant("plant_hall", 3.15, -2.7, 0.35)

    # rug with curled south edge (trip hazard)
    A += body("rug", (c[0], c[1], 0), rug_colliders(rh[0], rh[1]) + [
        geom("plane", (rh[0], rh[1], 0.05), (0, 0, 0.0125), solid=False, material="mat_rug")])
    # curled corner of the rug: a visual cue only (no collision) so the living-room doorway stays passable for the robot,
    # whose climb limit is about 1.9 cm (see src/control/navigation.py)
    A += body("rug_curl", (-2.2, c[1] - rh[1] + 0.03, 0.018), [
        geom("box", (0.4, 0.07, 0.012), (0, 0, 0), "0.47 0.14 0.17 1", euler=(-9, 0, 0), solid=False)])
    # slippers left in the corner by the door (4 cm tall: obstacles for the robot, kept clear of the door exit)
    A += body("slipper_left", (-3.18, c[1] - rh[1] - 0.35, 0.021), [
        geom("box", (0.12, 0.045, 0.02), rgba="0.90 0.55 0.65 1", mass=0.15)], euler=(0, 0, 25), joint="slipper_left_free")
    A += body("slipper_right", (-3.10, c[1] - rh[1] - 0.13, 0.021), [
        geom("box", (0.12, 0.045, 0.02), rgba="0.90 0.55 0.65 1", mass=0.15)], euler=(0, 0, -12), joint="slipper_right_free")

    # things on the coffee table and the toy ball on the rug
    top = 0.44
    A += body("mug", (-1.47, -0.05, top), [
        geom("cylinder", (0.045, 0.05), (0, 0, 0.05), "0.90 0.90 0.92 1", mass=0.3),
        geom("capsule", (0.012,), rgba="0.90 0.90 0.92 1", mass=0.02, extra='fromto="0.045 0 0.07 0.085 0 0.07"')], joint="mug_free")
    A += body("book", (-1.60, -0.4, top + 0.016), [geom("box", (0.12, 0.08, 0.015), rgba="0.10 0.35 0.75 1", mass=0.4)], joint="book_free")
    A += body("remote", (-1.50, -0.3, top + 0.013), [geom("box", (0.08, 0.02, 0.012), rgba="0.05 0.05 0.05 1", mass=0.12)], joint="remote_free")
    # (no toy ball: seen from the 1.15 m camera the red ball on the red rug was taken for a person lying on the floor, like the lamp and the tall plants before)

    # dining
    A += dining_table(-0.6, 1.53)
    A += chair("chair_s1", -0.95, 0.93, 0)
    A += chair("chair_s2", -0.25, 0.93, 0)
    A += chair("chair_n1", -0.95, 2.13, 180)
    A += chair("chair_n2", -0.25, 2.13, 180)
    A += body("kitchen_counter", (-2.32, 2.67, 0), [
        geom("box", (1.12, 0.27, 0.43), (0, 0, 0.43), "0.88 0.88 0.86 1"),
        geom("box", (1.14, 0.28, 0.02), (0, 0, 0.88), "0.30 0.30 0.32 1"),
        geom("box", (0.25, 0.2, 0.012), (0.5, 0, 0.9), "0.75 0.78 0.80 1", solid=False),
        geom("cylinder", (0.07, 0.01), (-0.6, 0.0, 0.91), "0.12 0.12 0.12 1", solid=False)])

    # bedroom
    A += bed(2.3, 1.94)
    A += body("wardrobe", (0.96, 1.0, 0), [
        geom("box", (0.3, 0.8, 1.0), (0, 0, 1.0), "0.78 0.72 0.62 1"),
        geom("box", (0.005, 0.005, 0.95), (0.305, 0, 1.0), "0.35 0.30 0.25 1", solid=False)])
    for nm, x in (("nightstand_e", 3.25), ("nightstand_w", 1.33)):
        A += body(nm, (x, 2.68, 0), [geom("box", (0.2, 0.2, 0.25), (0, 0, 0.25), "0.55 0.40 0.26 1"),
                                    geom("cylinder", (0.07, 0.01), (0, 0, 0.51), "0.9 0.9 0.9 1", solid=False),
                                    geom("cylinder", (0.11, 0.09), (0, 0, 0.62), "0.96 0.90 0.78 1", solid=False)])
    A += body("bedroom_rug", (2.3, -0.3, 0), rug_colliders(0.8, 0.55) + [
        geom("plane", (0.8, 0.55, 0.05), (0, 0, 0.0125), "0.35 0.42 0.50 1", solid=False)])

    # robot charging pad (visual only; the robot starts on it)
    dx, dy, dyaw = L.ROBOT_DOCK
    A += body("dock", (dx, dy, 0), [
        geom("box", (0.17, 0.14, 0.004), (0, 0, 0.004), "0.22 0.24 0.27 1", solid=False),
        geom("box", (0.012, 0.10, 0.0045), (-0.14, 0, 0.0075), "0.2 0.8 0.35 1", solid=False)], euler=(0, 0, dyaw))

    # moving obstacle
    A += vacuum(*L.VACUUM_LOOP[0])

    A.append("    <!-- Lighting -->")
    A += ['    <light name="sun" pos="0 0 6" dir="0.15 0.25 -1" directional="true" diffuse="0.55 0.55 0.52" specular="0.1 0.1 0.1" castshadow="true"/>',
          '    <light name="light_living" pos="-1.5 -0.5 2.3" dir="0 0 -1" diffuse="0.3 0.3 0.28" specular="0.05 0.05 0.05" castshadow="false"/>',
          '    <light name="light_dining" pos="-1.0 1.8 2.3" dir="0 0 -1" diffuse="0.3 0.3 0.28" specular="0.05 0.05 0.05" castshadow="false"/>',
          '    <light name="light_bedroom" pos="2.0 0.5 2.3" dir="0 0 -1" diffuse="0.28 0.28 0.28" specular="0.05 0.05 0.05" castshadow="false"/>',
          '    <light name="light_hall" pos="0 -2.45 2.3" dir="0 0 -1" diffuse="0.28 0.28 0.28" specular="0.05 0.05 0.05" castshadow="false"/>']

    # cameras: dollhouse overview, straight-down plan view, fixed ceiling camera (static-sensor baseline)
    def cam(name, pos, target, fovy):
        return f'    <camera name="{name}" pos="{f(pos)}" xyaxes="{f(L.lookat_xyaxes(pos, target))}" fovy="{fovy}"/>'
    A += [cam("overview", (0, -4.4, 8.4), (0, -0.3, 0.3), 45),
          '    <camera name="top" pos="0 0 10.5" xyaxes="1 0 0 0 1 0" fovy="42"/>',
          cam("static_cam", (0.45, 2.85, 2.3), (-1.6, 0.0, 0.5), 85),              # the one fixed camera (living-dining corner)
          cam("static_hall_w", (-3.35, -2.45, 2.25), (0.5, -2.45, 0.7), 70),       # extra fixed cameras of the 4-camera baseline:
          cam("static_hall_e", (3.35, -2.45, 2.25), (-0.5, -2.45, 0.7), 70),       # hallway west half / east half, bedroom corner
          cam("static_bed", (3.4, -1.75, 2.3), (2.0, 0.8, 0.5), 85)]

    # named places for patrol / fall scenarios (tiny hidden sites on a fixed body)
    A.append('    <body name="places" pos="0 0 0">')
    for nm, (x, y) in {**L.WAYPOINTS, **L.FALL_ZONES}.items():
        A.append(f'      <site name="{nm}" pos="{x} {y} 0.02" size="0.05" rgba="0.2 0.6 1 0.5" group="5"/>')
    A += ["    </body>", "  </worldbody>", "</mujoco>", ""]

    with open(OUT, "w") as fh:
        fh.write("\n".join(A))
    print("wrote", os.path.relpath(OUT, ROOT), f"({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    build()
