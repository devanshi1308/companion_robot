"""
Navigation checks on the real apartment model: free dock, doorway passage, furniture avoided, standoff choice.
Run:  python tests/test_navigation.py
"""
import os
import sys

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("sim", "robot", "control"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import apartment_layout as L  # noqa: E402
from navigation import OccupancyGrid  # noqa: E402

_m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "scene_full.xml"))
_d = mujoco.MjData(_m)
GRID = OccupancyGrid(_m, _d)


def _length(p):
    return sum(np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:]))


def test_dock_and_waypoints_are_free():
    assert GRID.is_free(*L.ROBOT_DOCK[:2])
    for name, (x, y) in L.WAYPOINTS.items():
        assert GRID.is_free(x, y), name


def test_furniture_blocks_and_tabletop_does_not():
    assert not GRID.is_free(-0.3, -0.3)            # sofa
    assert not GRID.is_free(-1.315, -0.75)         # a coffee-table leg
    assert not GRID.is_free(-1.55, -0.3)           # under the coffee table: the 1.10 m robot cannot go under it (its mast would hit the top)
    assert not GRID.is_free(-0.6, 1.53)            # under the dining table: blocked as well
    assert not GRID.is_free(-3.18, -1.60)          # slipper (4 cm tall)
    assert GRID.is_free(-2.2, -1.25)               # rug edge (1.2 cm) is climbable, so it does not block


def test_plan_through_doorways():
    path = GRID.plan((2.0, 0.0), (-2.2, 0.0))      # bedroom -> hallway -> living room
    assert path is not None
    xy = np.array(path)
    through_bed_door = any(abs(x - L.DOOR_BEDROOM[0]) < 0.45 and abs(y - L.HALL_Y) < 0.1 for x, y in _densify(path))
    through_liv_door = any(abs(x - L.DOOR_LIVING[0]) < 0.45 and abs(y - L.HALL_Y) < 0.1 for x, y in _densify(path))
    print(f"  bedroom -> living room: {len(path)} waypoints, {_length(path):.1f} m, via both doorways: {through_bed_door and through_liv_door}")
    assert through_bed_door and through_liv_door


def _densify(path, step=0.05):
    out = []
    for a, b in zip(path, path[1:]):
        n = max(2, int(np.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])) for t in np.linspace(0, 1, n)]
    return out


def test_path_keeps_clear_of_obstacles():
    path = GRID.plan((-2.85, 1.0), (2.0, -0.5))
    assert path is not None
    worst = min(GRID.clear[GRID.to_cell(x, y)] for x, y in _densify(path))
    print(f"  smallest clearance along a long plan: {worst:.2f} m (robot radius 0.158 m)")
    assert worst >= 0.158


def test_moving_obstacle_is_avoided():
    base = GRID.plan((-2.85, 1.0), (-1.7, 1.0))
    block = [(-2.3, 1.0, 0.17)]                     # vacuum parked in the way
    detour = GRID.plan((-2.85, 1.0), (-1.7, 1.0), extra_discs=block)
    assert base is not None and detour is not None
    print(f"  direct {_length(base):.2f} m, with the vacuum in the way {_length(detour):.2f} m")
    assert _length(detour) > _length(base)
    assert all(np.hypot(x + 2.3, y - 1.0) > 0.17 + 0.158 for x, y in _densify(detour))


def test_standoff_keeps_a_safe_distance_and_is_free():
    person, axis, robot = (-2.2, 0.27), (0.0, 1.0), (-2.85, 1.0)
    out = GRID.choose_standoff(person, axis, robot)
    assert out is not None
    x, y, heading, path = out
    dist = np.hypot(x - person[0], y - person[1])
    print(f"  standoff pose ({x:.2f}, {y:.2f}), {dist:.2f} m from her, drive {_length(path):.2f} m")
    assert 0.9 <= dist <= 1.3 and GRID.is_free(x, y), "aims about 1.1 m from her; never closer than 0.9 m to any body point"


def test_scan_matching_corrects_a_drifted_estimate():
    """Start the robot at the dock, give it a badly drifted pose estimate, and let the range scan pull it back."""
    from localization import Localizer
    from robot_interface import RobotInterface
    m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "scene_full.xml"))
    d = mujoco.MjData(m)
    for _ in range(300):
        mujoco.mj_step(m, d)
    rb = RobotInterface(m, d)
    loc = Localizer(m, GRID)
    true = rb.true_pose()
    ranges = loc.scan(d, true)
    worst_after, worst_before = 0.0, 0.0
    for off in ((0.22, -0.18, np.radians(7)), (-0.25, 0.20, np.radians(-9)), (0.15, 0.25, 0.0)):
        est = true + np.array(off)
        before = np.hypot(est[0] - true[0], est[1] - true[1])
        for _ in range(4):                                  # a few correction steps, as the robot would do while driving
            est, info = loc.correct(est, ranges)
        after = np.hypot(est[0] - true[0], est[1] - true[1])
        worst_before, worst_after = max(worst_before, before), max(worst_after, after)
        print(f"  drift {before:.2f} m, {np.degrees(off[2]):+.0f} deg -> after scan matching {after:.3f} m, heading error {abs(np.degrees(est[2] - true[2])):.1f} deg")
    assert worst_after < 0.10 < worst_before


def test_global_search_recovers_a_lost_robot():
    """Wrong by more than a metre and 90 degrees (after a bump or a spin): the whole-map search finds the true pose."""
    from localization import Localizer
    from robot_interface import RobotInterface
    m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "scene_full.xml"))
    d = mujoco.MjData(m)
    rb = RobotInterface(m, d)
    loc = Localizer(m, GRID)
    for pose in ((-1.05, -1.10, 180.0), (-2.2, 0.0, 90.0), (2.7, 0.2, -45.0), (2.0, -0.5, 90.0)):          # (corridors and the open dining/kitchen floor have too few features for a global fix: not used, a known limit)
        x, y, yaw = pose
        d.qpos[rb.qadr:rb.qadr + 7] = [x, y, 0.035, np.cos(np.radians(yaw) / 2), 0, 0, np.sin(np.radians(yaw) / 2)]
        for _ in range(150):
            mujoco.mj_step(m, d)
        true = rb.true_pose()
        ranges = loc.scan(d, true)
        est = true + np.array([1.2, -0.9, np.radians(95)])
        new, cost = loc.global_search(est, ranges)
        err = np.hypot(*(new[:2] - true[:2]))
        derr = abs(np.degrees((new[2] - true[2] + np.pi) % (2 * np.pi) - np.pi))
        print(f"  lost at {pose[:2]}: after global search {err:.2f} m, {derr:.1f} deg (cost {cost:.3f})")
        assert err < 0.15 and derr < 6, pose


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
