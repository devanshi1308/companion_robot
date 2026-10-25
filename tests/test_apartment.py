"""
Geometry and stability checks for the apartment. Run:  python tests/test_apartment.py
(also collected by pytest if installed).
"""
import os
import sys

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "sim"))
import apartment_layout as L  # noqa: E402
from dynamic_obstacles import Vacuum  # noqa: E402

ENV = os.path.join(ROOT, "models", "domestic_environment.xml")
SCENE = os.path.join(ROOT, "models", "scene_with_human.xml")
SOLID_GROUPS = np.array([1, 0, 0, 0, 1, 0], dtype=np.uint8)      # furniture (0) + colliders (4)


def _model():
    m = mujoco.MjModel.from_xml_path(ENV)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    return m, d


def _ray_solid(m, d, pnt, vec, exclude=-1):
    """Distance to the first geom that is solid (decorative geoms are skipped)."""
    pnt = np.array(pnt, float)
    vec = np.array(vec, float)
    total = 0.0
    gid = np.zeros(1, dtype=np.int32)
    for _ in range(20):
        dist = mujoco.mj_ray(m, d, pnt, vec, SOLID_GROUPS, 1, exclude, gid)
        if dist < 0:
            return np.inf
        g = gid[0]
        if m.geom_contype[g] or m.geom_conaffinity[g]:
            return total + dist
        pnt = pnt + vec * (dist + 1e-4)
        total += dist + 1e-4
    return np.inf


def test_models_load():
    m, _ = _model()
    assert m.nmocap == 1 and m.ncam >= 3
    m2 = mujoco.MjModel.from_xml_path(SCENE)
    assert m2.nskin == 1 and m2.nsite >= 33


def test_doorway_widths():
    m, d = _model()
    for (cx, width) in (L.DOOR_LIVING, L.DOOR_BEDROOM):
        left = _ray_solid(m, d, (cx, L.HALL_Y, 1.0), (-1, 0, 0))
        right = _ray_solid(m, d, (cx, L.HALL_Y, 1.0), (1, 0, 0))
        assert abs((left + right) - width) < 0.01, (cx, left + right, width)
        assert 0.80 <= left + right <= 0.90 + 1e-9, "guide: doorways 0.80 to 0.90 m clear width"


def test_walk_path_clearance():
    """Her walking line stays at least 0.40 m from every solid object and wall.

    The limit is the 0.85 m bedroom doorway (0.425 m each side of the centre line). The standards
    manual's 0.50 m clearance bubble cannot hold inside a doorway of the guide's width."""
    m, d = _model()
    s = np.arange(0, L.path_arclengths()[-1], 0.1)
    cum = L.path_arclengths()
    worst = np.inf
    for si in s:
        i = min(int(np.searchsorted(cum, si, side="right") - 1), len(L.WALK_PATH) - 2)
        u = (si - cum[i]) / (cum[i + 1] - cum[i])
        p = L.WALK_PATH[i] + u * (L.WALK_PATH[i + 1] - L.WALK_PATH[i])
        for z in (0.3, 0.9):
            for a in np.linspace(0, 2 * np.pi, 24, endpoint=False):
                worst = min(worst, _ray_solid(m, d, (p[0], p[1], z), (np.cos(a), np.sin(a), 0)))
    print(f"  minimum clearance along her path: {worst:.2f} m")
    assert worst >= 0.40, worst


def test_free_objects_settle():
    m, d = _model()
    free = [i for i in range(m.nbody) if m.body_dofnum[i] == 6]
    start = {i: d.xpos[i].copy() for i in free}
    for _ in range(int(3.0 / m.opt.timestep)):
        mujoco.mj_step(m, d)
    drift = max(np.linalg.norm(d.xpos[i] - start[i]) for i in free)
    print(f"  largest drift of {len(free)} free objects after 3 s: {drift * 1000:.1f} mm")
    assert drift < 0.01


def test_vacuum_stays_in_its_loop():
    m, d = _model()
    v = Vacuum(m)
    lo, hi = L.VACUUM_LOOP.min(0), L.VACUUM_LOOP.max(0)
    for t in np.linspace(0, 40, 400):
        xy, _ = v.pose(t)
        assert (xy >= lo - 1e-6).all() and (xy <= hi + 1e-6).all()
    # the loop clears every solid object by at least 2 cm (vacuum radius is 0.17 m)
    mujoco.mj_forward(m, d)
    for p in L.VACUUM_LOOP:
        dist = min(_ray_solid(m, d, (p[0], p[1], 0.05), (np.cos(a), np.sin(a), 0), exclude=m.body("vacuum").id)
                   for a in np.linspace(0, 2 * np.pi, 24, endpoint=False))
        assert dist - 0.17 >= 0.02 - 1e-6, (p, dist)


def test_floor_friction_zones():
    m, _ = _model()
    for name, _, mu, _ in L.FLOORS:
        g = m.geom(f"floor_{name}")
        assert abs(g.friction[0] - mu) < 1e-9 and g.priority == 1
    assert 0.40 <= min(f[2] for f in L.FLOORS) and max(f[2] for f in L.FLOORS) <= 0.70


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
