"""
Female human walks through the living room and falls (trip), using real physics for the fall.

Phase 1 (kinematic): a 130-frame SMPL-X walking cycle (AMASS CMU 10_04, frames 300-430,
    as used by Habitat Humanoids) is replayed along a furniture-free path at elderly speed.
Phase 2 (dynamic): at the trip instant the joints are released; MuJoCo simulates the fall
    (gravity, floor contact, joint limits) starting from the exact walking pose and velocity,
    plus a trip impulse.

Run headless with telemetry and a GIF:
    python src/sim/walk_and_fall.py --gif ../outputs/demo_walk_and_fall.gif
Live viewer (macOS needs mjpython):
    mjpython src/sim/walk_and_fall.py --view

Source assets: Habitat Humanoids (Meta, CC-BY-NC-SA 4.0), see models/human/README.md.
"""
import argparse
import csv
import json
import os

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SCENE = os.path.join(ROOT, "models", "scene_with_human.xml")
CLIP = os.path.join(ROOT, "models", "human", "walk_cycle_smplx.json")   # made by src/sim/extract_walk_cycle.py

BODY_JOINTS = [
    "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2",
    "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot", "neck",
    "left_collar", "right_collar", "head", "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow", "left_wrist", "right_wrist",
]
CLIP_FPS = 120.0
BLEND = 14                    # frames used to cross-fade the loop seam
C = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])  # Y-up -> Z-up
C_ROT = Rot.from_matrix(C)

# Path through the living room (x, y in metres); avoids sofa, table, TV stand, lamp, shelf.
PATH = np.array([[4.6, -3.6], [3.0, -3.1], [1.4, -2.4], [-0.2, -1.7], [-1.2, -1.3]])


def load_cycle():
    with open(CLIP) as f:
        z = json.load(f)
    aa = np.array(z["pose_body"])
    ro = np.array(z["root_orient"])
    tr = np.array(z["trans"])
    n = len(aa)
    # AMASS world is already Z-up (trans[:, 2] is the pelvis height). SMPL-X faces +z in its own frame.
    fwd = Rot.from_rotvec(ro).apply([0, 0, 1])
    h0 = float(np.unwrap(np.arctan2(fwd[:, 1], fwd[:, 0])).mean())   # mean travel heading
    rz = Rot.from_euler("z", -h0)
    root_local = rz * Rot.from_rotvec(ro) * C_ROT.inv()               # heading removed, in MuJoCo body frame
    v = (tr[-1] - tr[0]) / (n - 1)                                     # mean travel per frame
    sway = rz.apply(tr - tr[0] - np.outer(np.arange(n), v))            # periodic part, heading-relative
    speed = float(np.hypot(v[0], v[1]) * CLIP_FPS)                     # m/s at clip rate
    # cross-fade the seam so the loop is continuous
    q = np.stack([Rot.from_rotvec(aa[:, j]).as_quat() for j in range(21)], 1)  # (n,21,4) xyzw
    rq = root_local.as_quat()
    for k in range(BLEND):
        w = (k + 1) / (BLEND + 1)
        i = n - BLEND + k
        q[i] = _nlerp_all(q[i], q[0], w)
        rq[i] = _nlerp(rq[i], rq[0], w)
        sway[i] = (1 - w) * sway[i] + w * sway[0]
    return {"q": q, "rq": rq, "sway": sway, "n": n, "speed": speed, "height": tr[:, 2].copy()}


def _nlerp(a, b, w):
    if np.dot(a, b) < 0:
        b = -b
    r = (1 - w) * a + w * b
    return r / np.linalg.norm(r)


def _nlerp_all(a, b, w):
    return np.stack([_nlerp(a[j], b[j], w) for j in range(len(a))])


class Walker:
    """Kinematic playback of the walking cycle along PATH at a chosen speed."""

    def __init__(self, model, speed=0.8):
        self.m = model
        self.cyc = load_cycle()
        self.k = speed / self.cyc["speed"]       # playback-rate factor
        self.speed = speed
        self.qadr = {n: model.joint(n).qposadr[0] for n in BODY_JOINTS}
        self.root_q = model.joint("human_root").qposadr[0]    # scene also holds mug/book/remote/ball
        self.root_v = model.joint("human_root").dofadr[0]
        seg = np.diff(PATH, axis=0)
        self.seg_len = np.hypot(seg[:, 0], seg[:, 1])
        self.cum = np.concatenate([[0], np.cumsum(self.seg_len)])
        self.total = self.cum[-1]
        self.z_off = 0.0
        self._calibrate_height(model)

    # --- path helpers -------------------------------------------------------
    def path_state(self, s):
        s = float(np.clip(s, 0, self.total - 1e-6))
        i = int(np.searchsorted(self.cum, s, side="right") - 1)
        u = (s - self.cum[i]) / self.seg_len[i]
        pos = PATH[i] + u * (PATH[i + 1] - PATH[i])
        # smoothed heading: blend towards the next segment near a corner
        d = (PATH[i + 1] - PATH[i]) / self.seg_len[i]
        ang = np.arctan2(d[1], d[0])
        blend = 0.6
        if i + 1 < len(self.seg_len) and self.cum[i + 1] - s < blend:
            d2 = (PATH[i + 2] - PATH[i + 1]) / self.seg_len[i + 1]
            a2 = np.arctan2(d2[1], d2[0])
            w = 0.5 * (1 - (self.cum[i + 1] - s) / blend)
            ang = ang + w * _wrap(a2 - ang)
        if i > 0 and s - self.cum[i] < blend:
            d0 = (PATH[i] - PATH[i - 1]) / self.seg_len[i - 1]
            a0 = np.arctan2(d0[1], d0[0])
            w = 0.5 * (1 - (s - self.cum[i]) / blend)
            ang = ang + w * _wrap(a0 - ang)
        return pos, ang

    def default_trip_time(self):
        """Trip on a straight stretch: 0.9 m before the last corner, so she is not turning when she goes down."""
        return (self.cum[-2] - 0.9) / self.speed

    # --- pose ---------------------------------------------------------------
    def pose_at(self, t):
        """Return qpos (full vector) for the human at time t (s) of the walk."""
        c = self.cyc
        fidx = (t * CLIP_FPS * self.k) % c["n"]
        i0 = int(fidx) % c["n"]
        i1 = (i0 + 1) % c["n"]
        w = fidx - int(fidx)
        q = _nlerp_all(c["q"][i0], c["q"][i1], w)                 # (21,4) xyzw, Y-up local
        rq = _nlerp(c["rq"][i0], c["rq"][i1], w)
        sway = (1 - w) * c["sway"][i0] + w * c["sway"][i1]
        hz = (1 - w) * c["height"][i0] + w * c["height"][i1]
        pos, psi = self.path_state(self.speed * t)
        rz = Rot.from_euler("z", psi)
        root_mj = rz * Rot.from_quat(rq)
        sw = rz.apply(sway)
        qpos = self.m_qpos0.copy()
        r0 = self.root_q
        qpos[r0:r0 + 2] = pos + sw[:2]
        qpos[r0 + 2] = hz + self.z_off
        x, y, z, wq = root_mj.as_quat()
        qpos[r0 + 3:r0 + 7] = [wq, x, y, z]
        for j, name in enumerate(BODY_JOINTS):
            r = C_ROT * Rot.from_quat(q[j]) * C_ROT.inv()
            x, y, z, wq = r.as_quat()
            a = self.qadr[name]
            qpos[a:a + 4] = [wq, x, y, z]
        return qpos

    def _calibrate_height(self, model):
        d = mujoco.MjData(model)
        self.m_qpos0 = d.qpos.copy()
        foot_geoms = [g for g in range(model.ngeom)
                      if mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.geom_bodyid[g])
                      in ("left_foot", "right_foot", "left_ankle", "right_ankle")]
        lows = []
        for t in np.linspace(0, self.cyc["n"] / (CLIP_FPS * self.k), 60, endpoint=False):
            d.qpos[:] = self.pose_at(t)
            mujoco.mj_kinematics(model, d)
            lows.append(min(d.geom_xpos[g][2] - model.geom_size[g][0] for g in foot_geoms))
        self.z_off = -min(lows)


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


# --- skeleton sketch (BlazePose-style 33 landmarks) ------------------------------
BONES = [(0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10), (11, 12),
         (11, 13), (13, 15), (12, 14), (14, 16), (15, 17), (15, 19), (15, 21), (16, 18), (16, 20),
         (16, 22), (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28),
         (27, 29), (27, 31), (28, 30), (28, 32)]


def draw_skeleton(scene, m, d):
    """Append the landmark skeleton (green bones, red joints) to an mjvScene."""
    lm = {}
    for i in range(m.nsite):
        n = m.site(i).name
        if n.startswith("lm_"):
            lm[int(n[3:5])] = d.site_xpos[i].copy()
    ident = np.eye(3).ravel()
    for a, b in BONES:
        if scene.ngeom >= scene.maxgeom - 2:
            return
        g = scene.geoms[scene.ngeom]
        mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), ident, np.array([0.2, 0.9, 0.2, 1.0], dtype=np.float32))
        mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_CAPSULE, 0.012, lm[a], lm[b])
        scene.ngeom += 1
    for i, p in lm.items():
        if scene.ngeom >= scene.maxgeom - 1:
            return
        g = scene.geoms[scene.ngeom]
        mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_SPHERE, np.array([0.025, 0, 0]), p, ident, np.array([1.0, 0.15, 0.15, 1.0], dtype=np.float32))
        scene.ngeom += 1


def render_frame(renderer, m, d, cam, skeleton):
    opt = mujoco.MjvOption()
    if skeleton:
        opt.geomgroup[1] = 0        # hide the body, show only the sketch (skins have their own switch)
        opt.skingroup[1] = 0
        opt.geomgroup[4] = 0
    renderer.update_scene(d, camera=cam, scene_option=opt)
    if skeleton:
        draw_skeleton(renderer.scene, m, d)
    return renderer.render().copy()


# --- metrics ---------------------------------------------------------------
LM = {"l_sh": "lm_11_left_shoulder", "r_sh": "lm_12_right_shoulder",
      "l_hip": "lm_23_left_hip", "r_hip": "lm_24_right_hip"}


def features(m, d):
    site = lambda n: d.site_xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, n)]
    hip = 0.5 * (site(LM["l_hip"]) + site(LM["r_hip"]))
    sh = 0.5 * (site(LM["l_sh"]) + site(LM["r_sh"]))
    torso = sh - hip
    pitch = np.degrees(np.arccos(np.clip(torso[2] / np.linalg.norm(torso), -1, 1)))
    lm = np.array([d.site_xpos[i] for i in range(m.nsite) if m.site(i).name.startswith("lm_")])
    ext_h = max(np.ptp(lm[:, 0]), np.ptp(lm[:, 1]))
    ext_v = np.ptp(lm[:, 2])
    return hip, pitch, ext_h, ext_v


# Reflex stiffness while toppling (N m/rad); fades to zero so she goes limp on impact
KP = {"hip": 300, "knee": 300, "ankle": 120, "foot": 40, "spine": 250, "neck": 40, "head": 25,
      "collar": 40, "shoulder": 90, "elbow": 35, "wrist": 8}


def _kind(name):
    for k in ("hip", "knee", "ankle", "foot", "neck", "head", "collar", "shoulder", "elbow", "wrist"):
        if name.endswith(k):
            return k
    return "spine"


# Reflex duration relative to tau: legs buckle first, arms hold longest to break the fall
TAU_SCALE = {"hip": 0.5, "knee": 0.4, "ankle": 0.5, "foot": 0.5, "spine": 1.0, "neck": 1.0,
             "head": 1.0, "collar": 1.2, "shoulder": 1.3, "elbow": 1.3, "wrist": 1.0}


class ReflexHold:
    """PD torques that keep the joints near the pose at release, with gain decaying as exp(-t/tau)."""

    def __init__(self, m, d, tau):
        self.m, self.tau = m, tau
        self.joints = [(m.joint(n).qposadr[0], m.joint(n).dofadr[0], KP[_kind(n)], TAU_SCALE[_kind(n)]) for n in BODY_JOINTS]
        self.base_damp = {da: m.dof_damping[da] for _, da, _, _ in self.joints}
        self.target = d.qpos.copy()
        self.err = np.zeros(3)
        m.opt.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST   # damping below is then handled implicitly

    def apply(self, d, t_since):
        d.qfrc_applied[:] = 0
        for qa, da, kp, sc in self.joints:
            g = np.exp(-t_since / (self.tau * sc)) if self.tau > 0 else 0.0
            self.m.dof_damping[da:da + 3] = self.base_damp[da] + g * 0.1 * kp      # D term (implicit)
            if g > 1e-3:
                mujoco.mju_subQuat(self.err, self.target[qa:qa + 4], d.qpos[qa:qa + 4])
                d.qfrc_applied[da:da + 3] = g * kp * self.err                       # P term


HEAD_UP_DEG = 20.0      # protective reflex: keep the head up while falling forward


def _nlerp_q(a, b, w):
    """Blend two (w, x, y, z) quaternions."""
    if np.dot(a, b) < 0:
        b = -b
    r = (1 - w) * np.asarray(a) + w * np.asarray(b)
    return r / np.linalg.norm(r)


def straighten(m, target, amount=1.0):
    """Remove the walking asymmetry from the reflex target so she goes down straight, not twisted.

    Spine, neck and head are eased toward the straight rest pose; the two arms are replaced by
    their mirror-symmetric average (the walk swings them oppositely)."""
    ident = np.array([1.0, 0.0, 0.0, 0.0])
    blend = {"spine": 0.9, "neck": 0.8, "head": 0.8}          # legs are left as walked (easing them to rest splays them)
    for n in BODY_JOINTS:
        k = _kind(n)
        if k in blend:
            a = m.joint(n).qposadr[0]
            target[a:a + 4] = _nlerp_q(target[a:a + 4], ident, blend[k] * amount)
    mirror = lambda q: np.array([q[0], q[1], -q[2], -q[3]])       # reflect across the sagittal plane
    for side in ("shoulder", "elbow", "collar"):
        al, ar = m.joint(f"left_{side}").qposadr[0], m.joint(f"right_{side}").qposadr[0]
        avg = _nlerp_q(target[al:al + 4], mirror(target[ar:ar + 4]), 0.5)
        target[al:al + 4] = _nlerp_q(target[al:al + 4], avg, amount)
        target[ar:ar + 4] = _nlerp_q(target[ar:ar + 4], mirror(avg), amount)


def make_target(m, q_rel, direction, brace, straight):
    t = q_rel.copy()
    if straight:
        straighten(m, t, straight)
    if direction > 0 and brace:
        brace_arms(m, t, brace)
    return t


def brace_arms(m, target, degrees):
    """Protective reflex: swing both arms forward/up by `degrees` (about the body's lateral axis)."""
    add = C_ROT * Rot.from_euler("x", -np.radians(degrees)) * C_ROT.inv()   # SMPL lateral axis -> MuJoCo frame
    up = C_ROT * Rot.from_euler("x", -np.radians(HEAD_UP_DEG)) * C_ROT.inv()   # same axis: arms forward, head back
    for n, rot in (("left_shoulder", add), ("right_shoulder", add), ("neck", up), ("head", up)):
        a = m.joint(n).qposadr[0]
        w_, x_, y_, z_ = target[a:a + 4]
        q = rot * Rot.from_quat([x_, y_, z_, w_])
        x_, y_, z_, w_ = q.as_quat()
        target[a:a + 4] = [w_, x_, y_, z_]


def release(m, d, w, t_fall, speed, trip_omega, direction):
    """Hand over from kinematic playback to physics: keep pose and velocity, add the trip impulse."""
    eps = 0.01
    q0 = w.pose_at(t_fall)
    q1 = w.pose_at(t_fall + eps)
    d.qpos[:] = q0
    v = np.zeros(m.nv)
    mujoco.mj_differentiatePos(m, v, eps, q0, q1)
    d.qvel[:] = v
    mujoco.mj_forward(m, d)
    v0_ = w.root_v
    Rr = d.xmat[m.body("pelvis").id].reshape(3, 3)
    om = Rr @ d.qvel[v0_ + 3:v0_ + 6]
    om[2] = 0.0                                            # no leftover turning: she goes down straight
    d.qvel[v0_ + 3:v0_ + 6] = Rr.T @ om
    _, psi = w.path_state(speed * t_fall)
    fwd = np.array([np.cos(psi), np.sin(psi), 0.0])
    axis = np.cross([0, 0, 1.0], fwd) * direction      # pitch about the horizontal axis normal to heading
    Rm = d.xmat[m.body("pelvis").id].reshape(3, 3)
    v0 = w.root_v
    omega = trip_omega * axis                              # world angular velocity of the trip
    # Pivot about the planted (lower) foot, like a real trip: the whole body tips over the toes.
    sid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, n)
    feet = [d.site_xpos[sid("lm_27_left_ankle")].copy(), d.site_xpos[sid("lm_28_right_ankle")].copy()]
    pivot = min(feet, key=lambda p: p[2]); pivot[2] = 0.0
    pelvis = d.xpos[m.body("pelvis").id]
    d.qvel[v0:v0 + 3] += np.cross(omega, pelvis - pivot)   # linear velocity of the pelvis about the pivot
    d.qvel[v0 + 3:v0 + 6] += Rm.T @ omega                  # free-joint angular velocity is in the body frame
    return d.qpos.copy()


def run(speed=0.8, t_fall=None, trip_omega=1.9, direction=1.0, after=6.0, log_hz=30, frames=None, fps=15, tau=0.45, brace=70.0, skeleton=False, straight=1.0):
    m = mujoco.MjModel.from_xml_path(SCENE)
    d = mujoco.MjData(m)
    w = Walker(m, speed)
    if t_fall is None:
        t_fall = w.default_trip_time()
    rows, imgs = [], []
    renderer = mujoco.Renderer(m, 360, 480) if frames is not None else None
    cam = None
    if renderer is not None:
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = [1.0, -1.5, 0.6]
        cam.distance, cam.azimuth, cam.elevation = 7.0, 100, -28

    def log(t, phase):
        hip, pitch, eh, ev = features(m, d)
        rows.append({"t": round(t, 4), "phase": phase, "hip_x": hip[0], "hip_y": hip[1], "hip_z": hip[2],
                     "torso_pitch_deg": pitch, "extent_h": eh, "extent_v": ev,
                     "aspect_ratio": eh / max(ev, 1e-6)})

    def snap(t):
        if renderer is not None and len(imgs) < int((t) * fps) + 1:
            imgs.append(render_frame(renderer, m, d, cam, skeleton))

    # phase 1: kinematic walk
    dt = 1.0 / log_hz
    t = 0.0
    while t < t_fall:
        d.qpos[:] = w.pose_at(t)
        d.qvel[:] = 0
        mujoco.mj_forward(m, d)
        log(t, "walk")
        snap(t)
        t += dt

    q_rel = release(m, d, w, t_fall, speed, trip_omega, direction)
    hold = ReflexHold(m, d, tau)
    hold.target = make_target(m, q_rel, direction, brace, straight)
    steps = int(after / m.opt.timestep)
    log_every = int(round(1.0 / (log_hz * m.opt.timestep)))
    snap_every = int(round(1.0 / (fps * m.opt.timestep)))
    for s in range(steps):
        hold.apply(d, s * m.opt.timestep)
        mujoco.mj_step(m, d)
        if s % log_every == 0:
            log(t_fall + (s + 1) * m.opt.timestep, "fall")
        if renderer is not None and s % snap_every == 0:
            imgs.append(render_frame(renderer, m, d, cam, skeleton))
    return m, d, rows, imgs, t_fall


def summarize(rows):
    fall = [r for r in rows if r["phase"] == "fall"]
    z = np.array([r["hip_z"] for r in fall]); t = np.array([r["t"] for r in fall])
    vz = np.gradient(z, t)
    return {
        "hip_height_walking_m": round(float(np.median([r["hip_z"] for r in rows if r["phase"] == "walk"])), 3),
        "hip_height_final_m": round(float(z[-1]), 3),
        "peak_descent_speed_mps": round(float(-vz.min()), 2),
        "final_torso_pitch_deg": round(float(fall[-1]["torso_pitch_deg"]), 1),
        "final_aspect_ratio": round(float(fall[-1]["aspect_ratio"]), 2),
        "time_to_floor_s": round(float(t[np.argmax(z <= 0.20)] - t[0]), 2) if (z <= 0.20).any() else None,
    }


def _sketch(v, m, d, on):
    if on:
        v.user_scn.ngeom = 0
        draw_skeleton(v.user_scn, m, d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=0.8, help="walking speed m/s (elderly about 0.8)")
    ap.add_argument("--omega", type=float, default=1.9, help="trip pitch rate rad/s about the planted foot")
    ap.add_argument("--direction", type=float, default=1.0, help="+1 forward trip, -1 backward slip")
    ap.add_argument("--tau", type=float, default=0.45, help="seconds for reflex stiffness to fade (0 = fully limp)")
    ap.add_argument("--brace", type=float, default=70.0, help="arm brace angle in degrees (forward falls only, 0 = off)")
    ap.add_argument("--skeleton", action="store_true", help="sketch view: hide the body, show the 33-landmark skeleton")
    ap.add_argument("--straight", type=float, default=1.0, help="0..1: how strongly the fall is straightened / made symmetric (0 = keep the walking twist)")
    ap.add_argument("--csv", default=os.path.join(ROOT, "analytics", "human_walk_fall_telemetry.csv"))
    ap.add_argument("--gif", default=None)
    ap.add_argument("--view", action="store_true")
    a = ap.parse_args()

    if a.view:
        import time
        import mujoco.viewer
        m = mujoco.MjModel.from_xml_path(SCENE); d = mujoco.MjData(m); w = Walker(m, a.speed)
        t_fall = w.default_trip_time()
        with mujoco.viewer.launch_passive(m, d) as v:
            if a.skeleton:
                v.opt.geomgroup[1] = 0
                v.opt.skingroup[1] = 0
                v.opt.geomgroup[4] = 0
            t = 0.0
            while v.is_running() and t < t_fall:
                d.qpos[:] = w.pose_at(t); mujoco.mj_forward(m, d); _sketch(v, m, d, a.skeleton); v.sync(); time.sleep(1 / 60); t += 1 / 60
            hold = ReflexHold(m, d, a.tau)
            hold.target = make_target(m, release(m, d, w, t_fall, a.speed, a.omega, a.direction),
                                      a.direction, a.brace, a.straight)
            n_step = 0
            while v.is_running():
                for _ in range(8):
                    hold.apply(d, n_step * m.opt.timestep); n_step += 1
                    mujoco.mj_step(m, d)
                _sketch(v, m, d, a.skeleton); v.sync(); time.sleep(1 / 60)
        return

    m, d, rows, imgs, t_fall = run(a.speed, trip_omega=a.omega, direction=a.direction,
                                   frames=(a.gif is not None) or None, tau=a.tau, brace=a.brace, skeleton=a.skeleton, straight=a.straight)
    os.makedirs(os.path.dirname(a.csv), exist_ok=True)
    with open(a.csv, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
    print("trip at t = %.2f s" % t_fall)
    for k, v in summarize(rows).items():
        print(f"  {k}: {v}")
    print("telemetry ->", os.path.relpath(a.csv, ROOT))
    if a.gif and imgs:
        from PIL import Image
        os.makedirs(os.path.dirname(a.gif), exist_ok=True)
        ims = [Image.fromarray(i) for i in imgs]
        ims[0].save(a.gif, save_all=True, append_images=ims[1:], duration=int(1000 / 15), loop=0)
        print("gif ->", os.path.relpath(a.gif, ROOT), f"({len(imgs)} frames)")


if __name__ == "__main__":
    main()
