"""
Perception checks: the camera model matches MuJoCo's own camera, and the 3D landmarks the robot computes from
(MediaPipe pixels + depth + its own odometry) are close to the simulator's ground truth.
Run:  MUJOCO_GL=glfw python tests/test_perception.py
"""
import os
import sys

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("sim", "robot", "control", "vision"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import robot_spec as S  # noqa: E402
import walk_and_fall as W  # noqa: E402
from human_replay import record, apply_frame  # noqa: E402
from person_observer import PersonObserver, camera_pose  # noqa: E402
from robot_interface import RobotInterface  # noqa: E402

SCENE = os.path.join(ROOT, "models", "scene_full.xml")


def test_camera_model_matches_mujoco():
    m = mujoco.MjModel.from_xml_path(SCENE)
    d = mujoco.MjData(m)
    rb = RobotInterface(m, d)
    for pan, tilt, yaw in ((0, 0, 0.0), (35, -20, 1.0), (-60, 15, -2.0)):
        q = d.qpos[rb.qadr:rb.qadr + 7]
        q[0], q[1], q[3:7] = 0.4, -0.7, [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
        d.qpos[rb.q_pan], d.qpos[rb.q_tilt] = np.radians(pan), np.radians(tilt)
        mujoco.mj_forward(m, d)
        pos, R = camera_pose(rb.true_pose(), pan, tilt)
        assert np.allclose(pos, d.cam_xpos[rb.cam_id], atol=1e-4), (pos, d.cam_xpos[rb.cam_id])
        assert np.allclose(R, d.cam_xmat[rb.cam_id].reshape(3, 3), atol=1e-4)


def test_landmarks_in_world_match_ground_truth():
    from blazepose_tracker import PoseTracker
    m = mujoco.MjModel.from_xml_path(SCENE)
    ts, rec, t_fall = record(m)
    d = mujoco.MjData(m)
    w = W.Walker(m, 0.8)
    rb = RobotInterface(m, d)
    ren = mujoco.Renderer(m, 480, 640)
    obs_fn = PersonObserver(PoseTracker())
    pel = m.body("pelvis").id
    site = {i: [j for j in range(m.nsite) if m.site(j).name.startswith(f"lm_{i:02d}_")][0] for i in range(33)}
    rows = {}
    for phase, (a, b) in {"walking": (t_fall - 2.5, t_fall - 0.2), "lying": (t_fall + 2.0, t_fall + 5.0)}.items():
        errs = []
        for i in [k for k in range(len(ts)) if a <= ts[k] <= b][::5]:
            apply_frame(d, w, rec[i])
            mujoco.mj_forward(m, d)
            p = d.xpos[pel]
            x, y = -2.85, 1.0
            yaw = np.arctan2(p[1] - y, p[0] - x)
            q = d.qpos[rb.qadr:rb.qadr + 7]
            q[0], q[1], q[3:7] = x, y, [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
            tilt = np.degrees(np.arctan2(max(0.5 * p[2], 0.25) - S.CAM_Z, np.hypot(p[0] - x, p[1] - y)))
            d.qpos[rb.q_tilt] = np.radians(tilt)
            mujoco.mj_forward(m, d)
            rgb, dep = rb.grab(ren)
            obs = obs_fn.observe(rgb, dep, rb.true_pose(), 0.0, tilt)
            if obs is None:
                continue
            gt = np.array([d.site_xpos[site[i]] for i in range(33)])
            ok = obs.valid & (obs.vis > 0.5)
            errs.append(np.linalg.norm(obs.world[ok] - gt[ok], axis=1))
        e = np.concatenate(errs)
        rows[phase] = (np.median(e), np.percentile(e, 90), len(errs))
        print(f"  {phase:8s}: 3D landmark error median {100 * np.median(e):.0f} cm, 90th percentile {100 * np.percentile(e, 90):.0f} cm ({len(errs)} frames)")
    assert rows["walking"][0] < 0.20 and rows["lying"][0] < 0.30


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
