"""
Scripted body poses and motions for her (kinematic, not physics): standing, sitting, lying, squatting, bending, and the
transitions between them.  Used for the daily-living activities (ADLs) of the experiment set and for the pre-collapse
behaviour of the cardiac scenario.  The falls themselves are physics (walk_and_fall.release + ReflexHold).

A pose is described by a few numbers instead of 91 quaternion entries:

    Pose(x, y, yaw, lean, roll, ground, joints={"left_hip": (rx, ry, rz) degrees, ...})

  x, y     pelvis position (m); yaw = direction she faces (rad, 0 = +x)
  lean     whole-body tilt about the pelvis, degrees (+ forward, - backward; -90 = lying on her back, +90 = face down)
  roll     whole-body tilt sideways, degrees (+ = onto her left side)
  ground   height of the surface under her (floor 0.0, mattress 0.50): her pelvis height is solved so that her lowest point
           touches it (so a sitting pose lands on the right height by itself)
  joints   rotations added to the straight standing pose, in the SMPL axes of each joint: x = side-to-side axis
           (hip/shoulder flexion is NEGATIVE x, knee/spine flexion is POSITIVE x), z = along the front-back axis
           (arm raise sideways), y = twist.

Feet stay flat automatically (ankle = hip + knee flexion) unless an ankle is given.

All of this is an assumption-based model of how people move, not measured data (stated as a limitation in the report).
"""
import os
import sys
from dataclasses import dataclass, field

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import walk_and_fall as W  # noqa: E402

C_ROT = W.C_ROT
BODY_JOINTS = W.BODY_JOINTS
SPINE = ("spine1", "spine2", "spine3")


def smooth(u):
    u = float(np.clip(u, 0.0, 1.0))
    return u * u * u * (10 - 15 * u + 6 * u * u)          # minimum-jerk easing


def accel(u):
    u = float(np.clip(u, 0.0, 1.0))
    return u * u                                           # speeds up until it stops abruptly (plopping down)


@dataclass
class Pose:
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    lean: float = 0.0
    roll: float = 0.0
    ground: float = 0.0
    joints: dict = field(default_factory=dict)
    z: float = None            # fixed pelvis height (overrides ground)

    def lerp(self, o, u):
        """Blend towards pose o by u (0..1); yaw takes the short way round."""
        j = {}
        for k in set(self.joints) | set(o.joints):
            a, b = np.array(self.joints.get(k, (0, 0, 0)), float), np.array(o.joints.get(k, (0, 0, 0)), float)
            j[k] = tuple(a + u * (b - a))
        dyaw = (o.yaw - self.yaw + np.pi) % (2 * np.pi) - np.pi
        z = None if (self.z is None or o.z is None) else self.z + u * (o.z - self.z)
        return Pose(self.x + u * (o.x - self.x), self.y + u * (o.y - self.y), self.yaw + u * dyaw,
                    self.lean + u * (o.lean - self.lean), self.roll + u * (o.roll - self.roll),
                    self.ground + u * (o.ground - self.ground), j, z)


class Rig:
    """Turns a Pose into her 91 position entries (free root + 21 ball joints)."""

    def __init__(self, model):
        self.m = model
        self.d = mujoco.MjData(model)
        self.w = W.Walker(model, 0.8)
        self.sl_q = self.w.sl_q
        self.root_q = self.w.root_q
        self.qadr = self.w.qadr
        hb = model.body("pelvis").id
        def below(b):
            while b > 0:
                if b == hb:
                    return True
                b = model.body_parentid[b]
            return False
        self.geoms = [g for g in range(model.ngeom) if below(model.geom_bodyid[g])]
        self.base = self._stand_base()

    # ---- the straight standing pose ---------------------------------------------------------------
    def _stand_base(self):
        """Joint quaternions (w, x, y, z) of a relaxed stand: legs, spine and head straight, arms hanging (symmetric average of
        the walking arms)."""
        m = self.m
        q = self.w.pose_at(0.3).copy()
        W.straighten(m, q, 1.0)
        base = {}
        ident = np.array([1.0, 0, 0, 0])
        for n in BODY_JOINTS:
            a = self.qadr[n]
            kind = W._kind(n)
            base[n] = ident.copy() if kind in ("hip", "knee", "ankle", "foot", "spine", "neck", "head") else q[a:a + 4].copy()
        return base

    def joint_quat(self, name, deg):
        base = Rot.from_quat(np.roll(self.base[name], -1))                     # (x, y, z, w)
        delta = C_ROT * Rot.from_rotvec(np.radians(deg)) * C_ROT.inv()          # SMPL-axis rotation in MuJoCo's frame
        x, y, z, w = (delta * base).as_quat()
        return np.array([w, x, y, z])

    def qpos91(self, p: Pose):
        q = np.zeros(91)
        joints = dict(p.joints)
        for side in ("left", "right"):                                          # feet flat unless told otherwise
            if f"{side}_ankle" not in joints:
                h, k = joints.get(f"{side}_hip", (0, 0, 0)), joints.get(f"{side}_knee", (0, 0, 0))
                joints[f"{side}_ankle"] = (-(h[0] + k[0]), 0.0, 0.0)
        for n in BODY_JOINTS:
            a = self.qadr[n] - self.root_q
            q[a:a + 4] = self.joint_quat(n, joints.get(n, (0.0, 0.0, 0.0)))
        up = Rot.from_euler("z", p.yaw + np.pi / 2)                              # rest pose faces -y; this faces (cos yaw, sin yaw)
        fwd = np.array([np.cos(p.yaw), np.sin(p.yaw), 0.0])
        lat = np.cross([0, 0, 1.0], fwd)
        r = Rot.from_rotvec(lat * np.radians(p.lean)) * Rot.from_rotvec(fwd * np.radians(p.roll)) * up
        x, y, z, w = r.as_quat()
        q[0:3] = [p.x, p.y, 1.0 if p.z is None else p.z]
        q[3:7] = [w, x, y, z]
        if p.z is None:
            q[2] = self._solve_height(q, p.ground)
        return q

    def lowest(self, q91):
        d = self.d
        d.qpos[self.sl_q] = q91
        mujoco.mj_kinematics(self.m, d)
        low = np.inf
        for g in self.geoms:
            c = d.geom_xpos[g]
            r = self.m.geom_size[g][0]
            if self.m.geom_type[g] == mujoco.mjtGeom.mjGEOM_CAPSULE:
                half = self.m.geom_size[g][1]
                ax = d.geom_xmat[g].reshape(3, 3)[:, 2]
                low = min(low, c[2] - abs(ax[2]) * half - r)
            else:
                low = min(low, c[2] - r)
        return low

    def _solve_height(self, q91, ground):
        q91 = q91.copy()
        q91[2] = 1.0
        return 1.0 + (ground - self.lowest(q91))


# ---- keyframed motions ---------------------------------------------------------------------------
class Track:
    """Poses at times (s from the start of the clip), eased between neighbours.  keys = [(t, Pose, ease)]; the ease belongs to the
    segment that ENDS at that key ("smooth" or "accel")."""

    def __init__(self, rig, keys):
        self.rig, self.keys = rig, keys
        self.t_end = keys[-1][0]

    def pose(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        for (t0, p0, _), (t1, p1, ease) in zip(ks[:-1], ks[1:]):
            if t <= t1:
                u = (t - t0) / max(t1 - t0, 1e-6)
                return p0.lerp(p1, accel(u) if ease == "accel" else smooth(u))
        return ks[-1][1]

    def qpos(self, t):
        return self.rig.qpos91(self.pose(t))


def blend91(a, b, u):
    """Blend two 91-vectors of her position (root position linear, the 22 quaternions normalised-lerp)."""
    out = (1 - u) * a + u * b
    qa, qb = a[3:].reshape(22, 4), b[3:].reshape(22, 4)
    qb = np.where((qa * qb).sum(1, keepdims=True) < 0, -qb, qb)
    r = (1 - u) * qa + u * qb
    out[3:] = (r / np.linalg.norm(r, axis=1, keepdims=True)).ravel()
    return out
