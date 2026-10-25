"""
Python interface to the simulated companion robot: motors, encoders/odometry, camera, face screen.

    robot = RobotInterface(model, data)
    robot.set_drive(v, w)                 # m/s, rad/s  (differential drive)
    robot.set_neck(pan_deg, tilt_deg)     # guide ranges: pan +/-90, tilt -45..+30 (negative = down)
    robot.update_odometry()               # call every control step; wheel encoders only (noisy)
    rgb, depth = robot.grab(renderer)     # head camera (58 deg vertical FOV)
    robot.set_mood("worried")             # watching | worried | happy | alert

Ground truth (true_pose) is for logging and tests only; the robot's own behaviour uses the odometry estimate.
"""
import os
import sys

import mujoco
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import robot_spec as S  # noqa: E402

MOODS = {   # eye colour, eye half-size (x, y, z), brows visible, status LED colour
    "watching": ((0.21, 0.88, 0.91), (0.0012, 0.010, 0.014), False, (0.2, 0.9, 0.4)),
    "worried": ((1.00, 0.69, 0.00), (0.0012, 0.010, 0.012), True, (1.0, 0.69, 0.0)),
    "happy": ((0.20, 0.80, 0.35), (0.0012, 0.010, 0.006), False, (0.2, 0.9, 0.4)),
    "alert": ((0.84, 0.27, 0.24), (0.0012, 0.012, 0.016), False, (0.84, 0.27, 0.24)),
}


def quat_to_yaw(q):
    w, x, y, z = q
    return float(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class RobotInterface:
    def __init__(self, m, d, seed=0, odom_noise=0.01, wide_view=False):
        self.m, self.d = m, d
        self.tilt_range = S.TILT_WIDE_DEG if wide_view else S.TILT_RANGE_DEG       # wide view: the camera looks well above and below the guide's range
        self.rng = np.random.default_rng(seed)
        self.odom_noise = odom_noise                       # relative encoder error (1 sigma per step)
        j = m.joint
        self.qadr = j("robot_free").qposadr[0]
        self.vadr = j("robot_free").dofadr[0]
        self.q_l, self.q_r = j("wheel_l").qposadr[0], j("wheel_r").qposadr[0]
        self.q_pan, self.q_tilt = j("neck_pan").qposadr[0], j("head_tilt").qposadr[0]
        self.a_l, self.a_r = m.actuator("act_wheel_l").id, m.actuator("act_wheel_r").id
        self.a_pan, self.a_tilt = m.actuator("act_neck_pan").id, m.actuator("act_head_tilt").id
        self.cam_id = m.camera("robot_cam").id
        self.body_ids = {m.body(n).id for n in ("robot", "wheel_l", "wheel_r", "robot_neck", "robot_head")}
        names = {m.body(i).name: i for i in range(m.nbody)}
        self.floor_bodies = {0} | {names[n] for n in ("rug", "bedroom_rug") if n in names}
        self.eyes = [m.geom("eye_l").id, m.geom("eye_r").id]
        self.brows = [m.geom("brow_l").id, m.geom("brow_r").id]
        self.led = m.geom("status_led").id
        self.last_cmd = (0.0, 0.0)
        self.reset_odometry()

    # ---- motors -----------------------------------------------------------------------------
    def set_drive(self, v, w):
        """Differential drive: left wheel is at +y, so turning left (w > 0) speeds up the right wheel."""
        self.last_cmd = (float(v), float(w))
        wl = (v - w * S.TRACK / 2) / S.WHEEL_R
        wr = (v + w * S.TRACK / 2) / S.WHEEL_R
        self.d.ctrl[self.a_l], self.d.ctrl[self.a_r] = wl, wr

    def set_neck(self, pan_deg, tilt_deg):
        pan = np.clip(pan_deg, *S.PAN_RANGE_DEG)
        tilt = np.clip(tilt_deg, *self.tilt_range)
        self.d.ctrl[self.a_pan], self.d.ctrl[self.a_tilt] = np.radians(pan), np.radians(tilt)

    def neck_angles_deg(self):
        return float(np.degrees(self.d.qpos[self.q_pan])), float(np.degrees(self.d.qpos[self.q_tilt]))

    # ---- state ------------------------------------------------------------------------------
    def true_pose(self):
        q = self.d.qpos[self.qadr:self.qadr + 7]
        return np.array([q[0], q[1], quat_to_yaw(q[3:7])])

    def true_velocity(self):
        """(forward speed m/s, yaw rate rad/s) in the robot frame, ground truth."""
        v = self.d.qvel[self.vadr:self.vadr + 6]
        yaw = self.true_pose()[2]
        return float(np.cos(yaw) * v[0] + np.sin(yaw) * v[1]), float(v[5])

    def reset_odometry(self, pose=None):
        self.est = np.array(self.true_pose() if pose is None else pose, dtype=float)
        self._enc = (self.d.qpos[self.q_l], self.d.qpos[self.q_r])

    def update_odometry(self):
        """Dead reckoning from the wheel encoders with multiplicative noise (the robot's own pose estimate)."""
        el, er = self.d.qpos[self.q_l], self.d.qpos[self.q_r]
        dl, dr = (el - self._enc[0]) * S.WHEEL_R, (er - self._enc[1]) * S.WHEEL_R
        self._enc = (el, er)
        dl *= 1 + self.odom_noise * self.rng.standard_normal()
        dr *= 1 + self.odom_noise * self.rng.standard_normal()
        ds, dth = (dl + dr) / 2, (dr - dl) / S.TRACK
        x, y, th = self.est
        self.est = np.array([x + ds * np.cos(th + dth / 2), y + ds * np.sin(th + dth / 2), wrap(th + dth)])
        return self.est

    # ---- collisions -------------------------------------------------------------------------
    def collision_force(self, only=None, exclude=None, detail=False):
        """Largest normal contact force (N) between the robot and anything that is not floor. only / exclude: sets of body ids
        (e.g. her body) to restrict the contacts that count."""
        m, d, worst, f6 = self.m, self.d, 0.0, np.zeros(6)
        who = None
        for i in range(d.ncon):
            c = d.contact[i]
            b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
            if (b1 in self.body_ids) == (b2 in self.body_ids):
                continue                                    # both robot (self) or neither
            other = b2 if b1 in self.body_ids else b1
            if other in self.floor_bodies:
                continue
            if (only is not None and other not in only) or (exclude is not None and other in exclude):
                continue
            mujoco.mj_contactForce(m, d, i, f6)
            if abs(float(f6[0])) > worst:
                worst, who = abs(float(f6[0])), other
        return (worst, None if who is None else m.body(who).name) if detail else worst

    # ---- camera and face ----------------------------------------------------------------------
    def grab(self, renderer, depth=True):
        """RGB (uint8) and depth (metres) from the head camera."""
        renderer.update_scene(self.d, camera=self.cam_id)
        rgb = renderer.render().copy()
        dep = None
        if depth:
            renderer.enable_depth_rendering()
            renderer.update_scene(self.d, camera=self.cam_id)
            dep = renderer.render().copy()
            renderer.disable_depth_rendering()
        return rgb, dep

    def set_mood(self, mood):
        colour, size, brows, led = MOODS[mood]
        for g in self.eyes:
            self.m.geom_rgba[g] = (*colour, 1.0)
            self.m.geom_size[g] = size
        for g in self.brows:
            self.m.geom_rgba[g] = (*colour, 1.0 if brows else 0.0)
        self.m.geom_rgba[self.led] = (*led, 1.0)
        self.mood = mood
