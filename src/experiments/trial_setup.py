"""
Everything a trial needs before it runs: the scene (with its clutter and floor friction), her recorded motion, the robot's start pose.

    ctx = prepare(spec, work_dir)      # -> TrialContext(model_path, clip, clutter, robot_start)
"""
import json
import os
import sys

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for sub in ("sim", "robot", "control", "vision"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import apartment_layout as L  # noqa: E402
import human_motion as HM  # noqa: E402
import motions as M  # noqa: E402
from navigation import OccupancyGrid  # noqa: E402

MODELS = os.path.join(ROOT, "models")
SCENE_FULL = os.path.join(MODELS, "scene_full.xml")            # flat + her + robot
SCENE_HUMAN = os.path.join(MODELS, "scene_with_human.xml")     # flat + her (the clip is recorded here)

CLUTTER_KINDS = [      # name, geom type, half-size (m), rgba
    ("shoe_box", "box", (0.16, 0.10, 0.07), "0.75 0.55 0.30 1"),
    ("laundry_basket", "cylinder", (0.20, 0.17, 0.0), "0.35 0.55 0.75 1"),
    ("shopping_bag", "box", (0.14, 0.09, 0.14), "0.85 0.30 0.30 1"),
    ("stool", "cylinder", (0.16, 0.20, 0.0), "0.55 0.40 0.25 1"),
    ("toy_crate", "box", (0.20, 0.15, 0.10), "0.30 0.65 0.40 1"),
    ("floor_cushion", "box", (0.22, 0.22, 0.06), "0.70 0.45 0.70 1"),
]
DOORS = [(-2.2, L.HALL_Y), (2.0, L.HALL_Y)]


def set_friction(m, scale):
    """Scale the sliding friction of the floor slabs and rugs (priority-1 geoms)."""
    for g in range(m.ngeom):
        if m.geom_priority[g] == 1:
            m.geom_friction[g, 0] *= scale


def _write_model(base_path, extra_bodies, tag):
    txt = open(base_path).read()
    if extra_bodies:
        assert txt.count("</worldbody>") == 1
        txt = txt.replace("</worldbody>", "\n".join(extra_bodies) + "\n  </worldbody>")
    path = os.path.join(MODELS, f"_trial_{tag}_{os.getpid()}.xml")
    with open(path, "w") as f:
        f.write(txt)
    return path


def load_model(base_path, spec, clutter):
    bodies = []
    for i, c in enumerate(clutter):
        _, typ, size, rgba = [k for k in CLUTTER_KINDS if k[0] == c["name"]][0]
        sz = " ".join(str(s) for s in (size if typ == "box" else size[:2]))
        bodies.append(f'    <body name="clutter_{i}" pos="{c["x"]:.3f} {c["y"]:.3f} {c["z"]:.3f}" euler="0 0 {np.degrees(c["yaw"]):.1f}">'
                      f'<geom type="{typ}" size="{sz}" rgba="{rgba}"/></body>')
    path = _write_model(base_path, bodies, spec["id"])
    try:
        m = mujoco.MjModel.from_xml_path(path)
    finally:
        os.remove(path)
    set_friction(m, spec["friction_scale"])
    return m


def penetration(m, d, tol=0.03):
    """Deepest penetration (m) between her body and anything that is not the floor, at the current state."""
    hb = m.body("pelvis").id
    def human(b):
        while b > 0:
            if b == hb:
                return True
            b = m.body_parentid[b]
        return False
    worst = 0.0
    for i in range(d.ncon):
        c = d.contact[i]
        b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
        if human(b1) == human(b2):
            continue
        other = b2 if human(b1) else b1
        if other == 0 and abs(c.pos[2]) < 0.05:
            continue                                            # floor (world body, low): her feet on it
        worst = max(worst, -c.dist)
    return worst


def clip_for(spec, cache_dir=None):
    """Record her motion for this spec (cached as .npz).  The clip depends on the spec (and friction), not on the robot."""
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        fn = os.path.join(cache_dir, spec["id"] + ".npz")
        if os.path.exists(fn):
            z = np.load(fn, allow_pickle=True)
            return M.Clip(z["q"], json.loads(str(z["meta"])))
    base = os.path.join(MODELS, "scene_with_human.xml")
    m = load_model(base, spec, [])
    rig = HM.Rig(m)
    clip = M.make_clip(m, rig, spec)
    if cache_dir:
        np.savez_compressed(fn, q=clip.q, meta=json.dumps(clip.meta))
    return clip


def pelvis_track(clip, step=0.25):
    """Her pelvis xy over the clip (for keeping clutter out of her way)."""
    return np.array([clip.at(t)[:2] for t in np.arange(0, clip.t_end, step)])


def _dist_to_polyline(p, pts, closed=False):
    pts = np.asarray(pts, float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    best = np.inf
    for a, b in zip(pts[:-1], pts[1:]):
        ab = b - a
        u = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
        best = min(best, np.hypot(*(p - (a + u * ab))))
    return best


def place_clutter(m, d, spec, clip, rng, robot_xy=None):
    """Random clutter on the floor, away from her whole trajectory, the doors, the hallway and each other."""
    n = spec["n_clutter"]
    if n == 0:
        return []
    grid = OccupancyGrid(m, d)
    track = pelvis_track(clip)
    start = np.array(spec["path"][0])
    out = []
    tries = 0
    while len(out) < n and tries < 400:
        tries += 1
        x, y = rng.uniform(L.X0 + 0.4, L.X1 - 0.4), rng.uniform(L.HALL_Y + 0.5, L.Y1 - 0.4)       # rooms only (not the hallway)
        if np.min(np.hypot(*(track - [x, y]).T)) < 0.9 or np.hypot(*(start - [x, y])) < 0.9:
            continue
        if robot_xy is not None and np.hypot(x - robot_xy[0], y - robot_xy[1]) < 0.8:
            continue
        if _dist_to_polyline(np.array([x, y]), L.VACUUM_LOOP, closed=True) < 0.7:
            continue
        if any(np.hypot(x - dx, y - L.HALL_Y) < 1.2 for dx, _ in DOORS):
            continue
        if grid.clear[grid.to_cell(x, y)] < 0.45 or any(np.hypot(x - c["x"], y - c["y"]) < 0.6 for c in out):
            continue
        kind = CLUTTER_KINDS[int(rng.integers(len(CLUTTER_KINDS)))]
        typ, size = kind[1], kind[2]
        h = size[2] if typ == "box" else size[1]
        out.append(dict(name=kind[0], x=float(x), y=float(y), z=float(h), yaw=float(rng.uniform(0, np.pi))))
    return out


def robot_start(m, d, spec, rng, track=None):
    """Where the robot starts: near her starting point (65%) or somewhere else in the flat (35%); always on free floor."""
    grid = OccupancyGrid(m, d)
    her = np.array(spec["path"][0])
    for _ in range(500):
        if spec["robot_start_mode"] == "near":
            r, a = rng.uniform(1.0, 2.0), rng.uniform(0, 2 * np.pi)
            x, y = her[0] + r * np.cos(a), her[1] + r * np.sin(a)
        else:
            x, y = rng.uniform(L.X0 + 0.4, L.X1 - 0.4), rng.uniform(L.Y0 + 0.4, L.Y1 - 0.4)
            if np.hypot(*(her - [x, y])) < 3.0:
                continue
        if not (L.X0 + 0.3 < x < L.X1 - 0.3 and L.Y0 + 0.3 < y < L.Y1 - 0.3):
            continue
        if grid.blocked()[grid.to_cell(x, y)]:                 # the planner's own free space for the 0.30 m-radius robot
            continue
        p = np.array([x, y])
        if _dist_to_polyline(p, spec["path"]) < 1.1 or _dist_to_polyline(p, L.VACUUM_LOOP, closed=True) < 0.7:
            continue                                            # never start in her way or in the vacuum's way
        if track is not None and np.min(np.hypot(*(track - p).T)) < 1.0:
            continue
        # not through a wall from her start (near mode): same room as she starts in
        if spec["robot_start_mode"] == "near" and L.room_of(x, y) != L.room_of(*her):
            continue
        yaw = np.degrees(np.arctan2(her[1] - y, her[0] - x)) + rng.uniform(-30, 30) if spec["robot_start_mode"] == "near" else rng.uniform(-180, 180)
        return (float(x), float(y), float(yaw))
    return L.ROBOT_DOCK


class TrialContext:
    def __init__(self, spec, clip, clutter, start):
        self.spec, self.clip, self.clutter, self.start = spec, clip, clutter, start


def prepare(spec, cache_dir=None):
    clip = clip_for(spec, cache_dir)
    rng = np.random.default_rng(spec["seed"] + 7)
    m = load_model(SCENE_FULL, spec, [])
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    start = robot_start(m, d, spec, np.random.default_rng(spec["robot_start_seed"]), pelvis_track(clip))
    clutter = []
    for attempt in range(30):                              # clutter must not wall the robot in: every named place must stay reachable from its start
        clutter = place_clutter(m, d, spec, clip, rng, robot_xy=start[:2])
        if not clutter:
            break
        m2 = load_model(SCENE_FULL, spec, clutter)
        d2 = mujoco.MjData(m2)
        mujoco.mj_forward(m2, d2)
        g2 = OccupancyGrid(m2, d2)
        if all(g2.plan(start[:2], wp) is not None for wp in L.WAYPOINTS.values()):
            break
        clutter = []
    return TrialContext(spec, clip, clutter, start)
