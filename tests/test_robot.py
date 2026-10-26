"""
Robot model checks: drive, turn, braking (standards manual: >= 1.5 m/s2 without tipping), neck, camera, mass.
Run:  MUJOCO_GL=glfw python tests/test_robot.py
"""
import os
import sys

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "robot"))
import robot_spec as S  # noqa: E402
from robot_interface import RobotInterface, wrap  # noqa: E402

SOLO = os.path.join(ROOT, "models", "companion_robot.xml")


def _robot(mu=0.5):
    m = mujoco.MjModel.from_xml_path(SOLO)
    m.geom("floor").friction[0] = mu
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    return m, d, RobotInterface(m, d)


def _run(m, d, robot, seconds, fn=None):
    for k in range(int(seconds / m.opt.timestep)):
        if fn:
            fn(k * m.opt.timestep)
        mujoco.mj_step(m, d)
        robot.update_odometry()


def test_mass_and_com():
    m, d, _ = _robot()
    rid = m.body("robot").id
    assert abs(m.body_subtreemass[rid] - S.TOTAL_MASS) < 1e-6
    # the guide's robot: 16.5 kg, centre of mass about 0.231 m, camera at 1.15 m, wheel radius 0.08 m, track 0.38 m, front caster 0.18 m ahead
    assert abs(d.subtree_com[rid][2] - 0.231) < 0.01, d.subtree_com[rid][2]
    assert abs(S.TOTAL_MASS - 16.5) < 1e-6 and abs(S.CAM_Z - 1.15) < 0.01 and S.WHEEL_R == 0.08 and S.TRACK == 0.38 and S.CASTER_X == 0.18
    a_tip = 9.81 * S.CASTER_X / d.subtree_com[rid][2]
    print(f"  mass {S.TOTAL_MASS} kg, CoM {d.subtree_com[rid][2]:.3f} m, tipping limit {a_tip:.2f} m/s2 (guide 7.64), slip limit at mu 0.40: {0.40 * 9.81:.2f} m/s2")
    assert abs(a_tip - 7.64) < 0.3


def test_drive_straight():
    m, d, r = _robot()
    _run(m, d, r, 5.0, lambda t: r.set_drive(S.V_MAX, 0.0))
    x, y, yaw = r.true_pose()
    v, _ = r.true_velocity()
    print(f"  after 5 s at {S.V_MAX} m/s: x={x:.2f} m, lateral drift {abs(y) * 100:.1f} cm, heading drift {np.degrees(abs(yaw)):.1f} deg, speed {v:.3f}")
    assert abs(v - S.V_MAX) < 0.02 and abs(y) < 0.03 and abs(yaw) < np.radians(3)
    ex, ey, _ = r.est
    assert np.hypot(ex - x, ey - y) < 0.12, "odometry estimate should track the true position"


def test_spin_in_place():
    m, d, r = _robot()
    _run(m, d, r, 1.6, lambda t: r.set_drive(0.0, 1.0))
    yaw = r.true_pose()[2]
    print(f"  spin: commanded about 1.0 rad/s for 1.6 s, yaw = {np.degrees(yaw):.1f} deg (odometry {np.degrees(r.est[2]):.1f})")
    assert abs(wrap(yaw - 1.6)) < np.radians(10)


def test_emergency_braking_without_tipping():
    for mu, vcmd in ((0.40, S.V_MAX), (0.68, S.V_MAX), (0.68, 0.80), (0.40, 0.80)):   # cruise speed and the manual's 0.80 m/s ceiling
        m, d, r = _robot(mu)
        _run(m, d, r, 4.0, lambda t: r.set_drive(vcmd, 0.0))
        v0, x0 = r.true_velocity()[0], r.true_pose()[0]
        pitch_max, t_stop = 0.0, None
        for k in range(int(2.0 / m.opt.timestep)):
            r.set_drive(0.0, 0.0)
            mujoco.mj_step(m, d)
            q = d.qpos[r.qadr + 3:r.qadr + 7]
            pitch = abs(np.degrees(np.arcsin(np.clip(2 * (q[0] * q[2] - q[3] * q[1]), -1, 1))))
            pitch_max = max(pitch_max, pitch)
            if t_stop is None and abs(r.true_velocity()[0]) < 0.01:
                t_stop = (k + 1) * m.opt.timestep
        dist = r.true_pose()[0] - x0
        decel = v0 / t_stop
        print(f"  mu={mu:.2f}: cmd {vcmd:.2f}, from {v0:.2f} m/s, stopped in {t_stop:.2f} s over {dist * 100:.1f} cm, mean decel {decel:.2f} m/s2, max pitch {pitch_max:.1f} deg")
        assert decel >= S.A_EMERGENCY, "standards manual: emergency braking >= 1.5 m/s2"
        assert pitch_max < 10.0, "must not tip"


def test_neck_servos_and_limits():
    m, d, r = _robot()
    _run(m, d, r, 1.5, lambda t: r.set_neck(60.0, -30.0))
    pan, tilt = r.neck_angles_deg()
    print(f"  neck: commanded pan 60, tilt -30 -> {pan:.1f}, {tilt:.1f} deg")
    assert abs(pan - 60) < 2 and abs(tilt + 30) < 2
    _run(m, d, r, 1.5, lambda t: r.set_neck(150.0, 80.0))
    pan, tilt = r.neck_angles_deg()
    assert pan <= 90.5 and tilt <= 32.0, "commands are clamped to the guide's ranges (the servo sags about 1.4 deg under gravity)"


def test_camera_and_face():
    m, d, r = _robot()
    ren = mujoco.Renderer(m, 240, 320)
    rgb, dep = r.grab(ren)
    assert rgb.shape == (240, 320, 3) and dep.shape == (240, 320)
    assert np.isfinite(dep).all() and abs(dep[-1, 160] - S.CAM_Z / np.tan(np.radians(S.FOVY / 2))) < 0.03, "depth at the bottom image edge should match the camera geometry (1.15 m high, 29 deg below the horizon: 2.08 m)"
    r.set_mood("worried")
    assert m.geom_rgba[m.geom("brow_l").id][3] == 0.0, "the face shows no expressions: brows stay hidden"
    assert tuple(m.geom_size[m.geom("eye_l").id]) == (0.003, 0.02, 0.02), "eyes stay the same size in every mood"
    assert m.geom_rgba[m.geom("status_led").id][0] > 0.9, "the chest light turns amber"
    r.set_mood("watching")
    assert m.geom_rgba[m.geom("status_led").id][1] > 0.8, "and green again"


def test_wide_view_looks_far_above_and_below():
    """Family-platform option: the camera tilts from -75 (almost straight down) to +70 deg; the default stays at the guide's -45..+30."""
    from robot_interface import RobotInterface
    m, d, _ = _robot()
    r = RobotInterface(m, d, wide_view=True)
    _run(m, d, r, 2.0, lambda t: r.set_neck(0.0, 80.0))
    up = r.neck_angles_deg()[1]
    _run(m, d, r, 2.0, lambda t: r.set_neck(0.0, -80.0))
    down = r.neck_angles_deg()[1]
    print(f"  wide view: up {up:.0f} deg, down {down:.0f} deg")
    assert 68 < up < 72 and -77 < down < -73


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
