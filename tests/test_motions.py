"""
Checks for the scripted motions and the scenario generator.
Run:  python tests/test_motions.py
"""
import os
import sys

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("sim", "experiments", "robot", "control", "vision"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import human_motion as HM  # noqa: E402
import motions as M  # noqa: E402
import scenarios as SC  # noqa: E402

_m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "scene_with_human.xml"))
_rig = HM.Rig(_m)
_sites = M._sites(_m)


def hip(q):
    return M.hip_height(_rig, q, _sites)


def test_poses_have_sensible_hip_heights():
    P = HM.Pose
    stand = hip(_rig.qpos91(P(-2.2, -0.6, 0.0)))
    sit = hip(_rig.qpos91(P(-2.2, -0.6, 0.0, joints=M.sitting_joints())))
    squat = hip(_rig.qpos91(P(-2.2, -0.6, 0.0, joints=M.squat_joints())))
    lie = hip(_rig.qpos91(P(-2.2, -0.6, 0.0, lean=-90, joints=M.lying_joints())))
    print(f"  hip height: stand {stand:.2f} m, sit {sit:.2f} m, squat {squat:.2f} m, lying on the floor {lie:.2f} m")
    assert 0.8 < stand < 1.05 and 0.4 < sit < 0.6 and 0.2 < squat < 0.45 and lie < 0.2


def test_every_activity_clip_ends_without_touching_the_floor_like_a_fall():
    """Activities must not produce the signature of a fall in the TRUTH: sitting and bending keep the hip above 0.45 m,
    the squat stays above 0.25 m; only the deliberate floor activities go low."""
    rng = np.random.default_rng(0)
    specs = SC.make_specs("t", 120, 5)
    seen = {}
    for sp in specs:
        if sp["kind"] != "adl" or sp["subtype"] in seen:
            continue
        seen[sp["subtype"]] = sp
    assert set(seen) == set(M.ADL_TYPES), set(M.ADL_TYPES) - set(seen)
    for sub, sp in seen.items():
        clip = M.make_clip(_m, _rig, sp)
        hz = [hip(clip.at(t)) for t in np.arange(0, clip.t_end, 0.1)]
        print(f"  {sub:16s} min hip {min(hz):.2f} m over {clip.t_end:.0f} s")
        lo = dict(sit_sofa_abrupt=0.45, sit_sofa_slow=0.45, lie_bed=0.45, drop_keys=0.6, tie_shoelaces=0.25, sit_floor=0.15, lie_floor=0.05)[sub]
        assert min(hz) > lo, sub


def test_trip_ends_on_the_floor_and_cardiac_has_a_prodrome():
    sp = dict(kind="fall", subtype="trip", path=SC.L.ROUTES["bed_to_front_door"].tolist(), speed=0.75, seed=3, fall_s=5.5, omega=1.9, tau=0.45)
    clip = M.make_clip(_m, _rig, sp)
    assert clip.meta["t_floor"] is not None and hip(clip.at(clip.t_end)) < 0.2
    sp = dict(kind="fall", subtype="cardiac", path=SC.L.ROUTES["bed_to_front_door"].tolist(), speed=0.75, seed=3, prodrome_start_s=3.0, prodrome_s=9.0,
              chest_side="right", omega=0.6, tau=0.12, side=1.0, lateral=False)
    clip = M.make_clip(_m, _rig, sp)
    assert clip.meta["t_event"] - 3.0 > 8 and clip.meta["t_floor"] is not None
    # during the prodrome her right wrist is near her chest
    rig, m = _rig, _m
    t = clip.meta["t_event"] - 2.0
    rig.d.qpos[rig.sl_q] = clip.at(t)
    mujoco.mj_kinematics(m, rig.d)
    wrist = rig.d.site_xpos[_sites[16]]
    chest = 0.5 * (rig.d.site_xpos[_sites[11]] + rig.d.site_xpos[_sites[12]]) * 0.65 + 0.5 * (rig.d.site_xpos[_sites[23]] + rig.d.site_xpos[_sites[24]]) * 0.35
    print(f"  wrist to chest during the prodrome: {np.linalg.norm(wrist - chest):.2f} m")
    assert np.linalg.norm(wrist - chest) < 0.3


def test_scenario_generator_is_seeded_and_balanced():
    a, b = SC.make_specs("x", 120, 7), SC.make_specs("x", 120, 7)
    assert [s["id"] for s in a] == [s["id"] for s in b] and a[5]["path"] == b[5]["path"] and a[5]["friction_scale"] == b[5]["friction_scale"]
    counts = {}
    for s in a:
        counts[s["subtype"]] = counts.get(s["subtype"], 0) + 1
    assert counts == SC.MIX_120, counts
    assert sum(1 for s in a if s["kind"] == "fall") == 60 and sum(1 for s in a if s["kind"] == "adl") == 60
    assert all(not s["conscious"] for s in a if s["subtype"] in ("syncope", "cardiac"))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
