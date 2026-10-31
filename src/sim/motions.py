"""
Motion clips for the experiment set: what SHE does in one trial, recorded once (independent of the robot) and replayed.

  clip = make_clip(rig, spec)         # spec: see scenarios.py (kind, route, speed, event parameters, seed)
  q91 = clip.at(t)                    # her 91 position entries at time t (interpolated)

Falls (positives) run real physics from the gait (walk_and_fall.release + ReflexHold):
    trip       forward fall over a trip hazard, arms brace
    slip       backward fall (slippery floor), no brace
    syncope    sudden loss of tone while walking: the legs fold and she crumples (sideways or forward)
    cardiac    several seconds of pre-collapse behaviour (she slows, presses a hand to her chest, hunches, sways), then collapses

Daily activities (hard negatives) are scripted poses (human_motion.py):
    sit_sofa_abrupt, sit_sofa_slow, lie_bed, tie_shoelaces, drop_keys, sit_floor, lie_floor

These motion models are assumptions (how a person moves), not measured patient data.
"""
import os
import sys

import mujoco
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apartment_layout as L  # noqa: E402
import human_motion as HM  # noqa: E402
import walk_and_fall as W  # noqa: E402
from human_motion import Pose, Track, blend91, smooth  # noqa: E402

DT = 0.016                      # clip sampling (62.5 Hz; the simulation interpolates)
FALL_TYPES = ("trip", "slip", "syncope", "cardiac")
DEMO_ADL_TYPES = ("take_tablet",)          # used by the demos only (not in the measured experiment set)
ADL_TYPES = ("sit_sofa_abrupt", "sit_sofa_slow", "lie_bed", "tie_shoelaces", "drop_keys", "sit_floor", "lie_floor")

# where each daily activity happens: the route she walks first, and the stand point at its end
SOFA_STAND = (-0.80, -0.35)      # in front of the low sofa (seat top 0.47 m), north end, past the coffee table
SOFA_SEAT = (-0.22, -0.35)       # pelvis when seated (the sofa faces -x)
BED_FOOT = (2.30, 0.62)         # at the foot of the bed
BED_EDGE = (2.30, 1.08)         # pelvis when sitting on the foot edge
BED_LIE = (2.30, 1.93)          # pelvis when lying in the bed (head towards the headboard, +y)
BED_TOP = 0.50


class Clip:
    def __init__(self, q, meta, dt=DT):
        self.q, self.dt, self.meta = np.asarray(q), dt, meta
        self.t_end = (len(q) - 1) * dt

    def at(self, t):
        x = np.clip(t / self.dt, 0, len(self.q) - 1)
        i0 = int(x)
        i1 = min(i0 + 1, len(self.q) - 1)
        return blend91(self.q[i0], self.q[i1], x - i0)


# ---- helpers --------------------------------------------------------------------------------------------
def _sites(m):
    ids = {}
    for i in range(m.nsite):
        n = m.site(i).name
        if n.startswith("lm_"):
            ids[int(n[3:5])] = i
    return ids


def hip_height(rig, q91, sites=None):
    sites = sites or _sites(rig.m)
    rig.d.qpos[rig.sl_q] = q91
    mujoco.mj_kinematics(rig.m, rig.d)
    return float(0.5 * (rig.d.site_xpos[sites[23]][2] + rig.d.site_xpos[sites[24]][2]))


def walk_frames(w, t_to):
    ts = np.arange(0.0, t_to, DT)
    return [w.pose_at(t)[w.sl_q].copy() for t in ts]


def safe_arclengths(path, margin_corner=0.8, start=1.0, end=1.0, step=0.05):
    """Arc lengths along a route where she walks straight (at least `margin_corner` m from any corner): where a fall may start."""
    cum = L.path_arclengths(path)
    s = np.arange(start, cum[-1] - end, step)
    ok = np.array([np.all(np.abs(cum[1:-1] - x) > margin_corner) if len(cum) > 2 else True for x in s])
    return s[ok]


# ---- falls ----------------------------------------------------------------------------------------------
def prodrome_post(rig, w, t0, side, ramp=1.5, sway=0.07, sway_hz=0.55):
    """Pre-collapse behaviour from t0: a hand pressed to the chest, a hunched back and a swaying (staggering) gait."""
    sgn = 1.0 if side == "left" else -1.0
    arm = {f"{side}_shoulder": (-15, -sgn * 40, 0), f"{side}_elbow": (0, 0, -sgn * 145)}   # found by search: hand within 5 cm of the chest; elbow flexion is about z (right +, left -)
    spine = {"spine1": (7, 0, 0), "spine2": (9, 0, 0), "spine3": (9, 0, 0), "neck": (14, 0, 0)}
    targets = {n: rig.joint_quat(n, deg) for n, deg in {**arm, **spine}.items()}

    def post(t, q):
        g = smooth((t - t0) / ramp)
        if g <= 0:
            return q
        for n, tq in targets.items():
            a = w.qadr[n]
            cur = q[a:a + 4]
            tq_ = tq if np.dot(cur, tq) >= 0 else -tq
            r = (1 - g) * cur + g * tq_
            q[a:a + 4] = r / np.linalg.norm(r)
        _, psi = w.path_state(w.s_at(t))
        lat = np.array([-np.sin(psi), np.cos(psi)])
        amp = sway * g * (0.6 + 0.4 * np.sin(0.7 * t))
        q[w.root_q:w.root_q + 2] += lat * amp * np.sin(2 * np.pi * sway_hz * (t - t0))
        return q
    return post


def record_fall(m, rig, spec, rng):
    """Walk (kinematic), then the fall (physics). Returns (frames, meta)."""
    kind = spec["subtype"]
    path = np.asarray(spec["path"], float)
    v0 = spec["speed"]
    meta = dict(kind="fall", subtype=kind)
    profile, post = None, None
    if kind == "cardiac":
        t_p, P = spec["prodrome_start_s"], spec["prodrome_s"]
        v1 = 0.35 * v0
        def profile(t):
            return v0 - (v0 - v1) * smooth((t - t_p) / 4.0)
        meta.update(prodrome_start_s=t_p, prodrome_s=P)
    w = W.Walker(m, v0, path=path, profile=profile)
    if kind == "cardiac":
        w.post = prodrome_post(rig, w, spec["prodrome_start_s"] + 1.0, spec["chest_side"])
        t_fall = spec["prodrome_start_s"] + spec["prodrome_s"]
        t_fall = min(t_fall, w.time_at(w.total - 1.0))
    else:
        t_fall = w.time_at(spec["fall_s"])
    frames = walk_frames(w, t_fall)
    d = mujoco.MjData(m)
    d.qpos[:] = w.pose_at(t_fall)
    params = dict(
        trip=dict(omega=spec["omega"], direction=1.0, lateral=False, tau=spec["tau"], brace=70.0),
        slip=dict(omega=spec["omega"], direction=-1.0, lateral=False, tau=spec["tau"], brace=0.0),
        syncope=dict(omega=spec["omega"], direction=spec.get("side", 1.0), lateral=spec.get("lateral", False), tau=spec["tau"], brace=0.0),
        cardiac=dict(omega=spec["omega"], direction=spec.get("side", 1.0), lateral=spec.get("lateral", False), tau=spec["tau"], brace=0.0),
    )[kind]
    q_rel = W.release(m, d, w, t_fall, v0, params["omega"], params["direction"], params["lateral"])
    hold = W.ReflexHold(m, d, params["tau"])
    hold.target = W.make_target(m, q_rel, params["direction"], params["brace"], 1.0)
    dt_sim = m.opt.timestep
    every = int(round(DT / dt_sim))
    n = int(spec.get("after", 8.0) / dt_sim)
    sites = _sites(m)
    t_hit = None
    for k in range(n):
        hold.apply(d, k * dt_sim)
        mujoco.mj_step(m, d)
        if k % every == 0:
            frames.append(d.qpos[w.sl_q].copy())
            if t_hit is None:
                hz = 0.5 * (d.site_xpos[sites[23]][2] + d.site_xpos[sites[24]][2])
                if hz < 0.20:
                    t_hit = t_fall + k * dt_sim
    meta.update(t_event=t_fall, t_floor=t_hit, t_walk_start=0.0)
    return frames, meta


# ---- daily activities --------------------------------------------------------------------------------------
def _j(**kw):
    return kw


def sitting_joints(hip=90.0, knee=90.0, arms=True):
    j = {"left_hip": (-hip, 0, 0), "right_hip": (-hip, 0, 0), "left_knee": (knee, 0, 0), "right_knee": (knee, 0, 0)}
    if arms:
        j.update({"left_shoulder": (-18, 0, 0), "right_shoulder": (-18, 0, 0), "left_elbow": (0, 0, -45), "right_elbow": (0, 0, 45)})
    return j


def squat_joints(depth=1.0):
    f, k, sp = 115 * depth, 135 * depth, 12 * depth
    return {"left_hip": (-f, 0, 0), "right_hip": (-f, 0, 0), "left_knee": (k, 0, 0), "right_knee": (k, 0, 0),
            "spine1": (sp, 0, 0), "spine2": (sp, 0, 0), "spine3": (sp, 0, 0),
            "left_shoulder": (-60 * depth, 0, 0), "right_shoulder": (-60 * depth, 0, 0),
            "left_elbow": (0, 0, -50 * depth), "right_elbow": (0, 0, 50 * depth)}


def bend_joints(depth=1.0):
    return {"left_hip": (-45 * depth, 0, 0), "right_hip": (-45 * depth, 0, 0), "left_knee": (15 * depth, 0, 0), "right_knee": (15 * depth, 0, 0),
            "spine1": (12 * depth, 0, 0), "spine2": (12 * depth, 0, 0), "spine3": (12 * depth, 0, 0),
            "left_shoulder": (-80 * depth, 0, 0), "right_shoulder": (-80 * depth, 0, 0)}


def lying_joints():
    return {"left_hip": (-8, 0, 0), "right_hip": (-8, 0, 0), "left_knee": (18, 0, 0), "right_knee": (18, 0, 0),
            "left_shoulder": (0, 0, 0), "right_shoulder": (0, 0, 0)}


def adl_keys(kind, stand, rng, hold_s, spec=None):
    """Keyframes (relative times) for a daily activity that starts with her standing at `stand` = (x, y, yaw)."""
    x, y, yaw = stand
    st = Pose(x, y, yaw)
    meta = {}
    if kind in ("sit_sofa_abrupt", "sit_sofa_slow"):
        sx, sy = SOFA_SEAT
        turn = Pose(x, y, np.pi)                                       # turns round (the sofa faces -x), back to the seat
        abrupt = kind.endswith("abrupt")
        d_sit = float(rng.uniform(0.40, 0.60)) if abrupt else float(rng.uniform(1.4, 2.0))
        seated = Pose(sx, sy, np.pi, ground=0.07, joints=sitting_joints())     # a little above the floor: she sits ON the cushion
        pre = Pose(x + 0.3 * (sx - x), y, np.pi, joints={"left_hip": (-25, 0, 0), "right_hip": (-25, 0, 0), "left_knee": (30, 0, 0), "right_knee": (30, 0, 0)})
        t0 = 0.4
        keys = [(0.0, st, "smooth"), (t0, st, "smooth"), (t0 + 1.2, turn, "smooth")]
        if abrupt:   # drops the last part: starts to fold, then lets herself fall onto the cushion
            keys += [(t0 + 1.2 + 0.25, pre, "smooth"), (t0 + 1.2 + 0.25 + d_sit, seated, "accel")]
        else:
            keys += [(t0 + 1.2 + d_sit, seated, "smooth")]
        t_act = t0 + 1.2
        keys += [(keys[-1][0] + hold_s, seated, "smooth")]
        meta.update(t_activity=t_act, t_activity_end=keys[-1][0], descent_s=d_sit)
    elif kind == "take_tablet":
        sx, sy = SOFA_SEAT
        turn = Pose(x, y, np.pi)
        seated = Pose(sx, sy, np.pi, ground=0.07, joints=sitting_joints())
        mouth = Pose(sx, sy, np.pi, ground=0.07, joints={**sitting_joints(), "right_shoulder": (-100, 40, 45), "right_elbow": (0, 0, 130), "neck": (10, 0, 0)})   # hand 4 cm from the mouth
        wait = float((spec or {}).get("intake_after_s", 12.0))
        t0 = 0.4
        keys = [(0.0, st, "smooth"), (t0, st, "smooth"), (t0 + 1.2, turn, "smooth"), (t0 + 1.2 + 1.8, seated, "smooth")]
        t = keys[-1][0] + wait
        keys += [(t, seated, "smooth"), (t + 1.2, mouth, "smooth"), (t + 1.2 + 2.0, mouth, "smooth"), (t + 2.4 + 2.0, seated, "smooth"), (t + 2.4 + 2.0 + hold_s, seated, "smooth")]
        meta.update(t_activity=t0 + 1.2, t_activity_end=keys[-1][0], descent_s=1.8, t_intake=t + 1.2)
    elif kind == "lie_bed":
        ex, ey = BED_EDGE
        turn = Pose(x, y, -np.pi / 2)
        edge = Pose(ex, ey, -np.pi / 2, ground=0.07, joints=sitting_joints())
        d_lie = float(rng.uniform(2.2, 3.2))
        mid = Pose(BED_LIE[0], 0.5 * (ey + BED_LIE[1]), -np.pi / 2, lean=-45, ground=0.50, joints={**sitting_joints(70, 40), "spine1": (0, 0, 0)})
        lie = Pose(BED_LIE[0], BED_LIE[1], -np.pi / 2, lean=-90, ground=BED_TOP + 0.06, joints=lying_joints())
        t0 = 0.4
        keys = [(0.0, st, "smooth"), (t0, st, "smooth"), (t0 + 1.2, turn, "smooth"), (t0 + 1.2 + 1.8, edge, "smooth"),
                (t0 + 1.2 + 1.8 + 0.6, edge, "smooth"), (t0 + 1.2 + 1.8 + 0.6 + 0.5 * d_lie, mid, "smooth"),
                (t0 + 1.2 + 1.8 + 0.6 + d_lie, lie, "smooth")]
        keys += [(keys[-1][0] + hold_s, lie, "smooth")]
        meta.update(t_activity=t0 + 1.2 + 1.8, t_activity_end=keys[-1][0], descent_s=d_lie)
    elif kind == "tie_shoelaces":
        d_dn = float(rng.uniform(1.2, 1.8))
        sq = Pose(x, y, yaw, joints=squat_joints())
        t0 = 0.5
        keys = [(0.0, st, "smooth"), (t0, st, "smooth"), (t0 + d_dn, sq, "smooth"), (t0 + d_dn + hold_s, sq, "smooth"), (t0 + 2 * d_dn + hold_s, st, "smooth"),
                (t0 + 2 * d_dn + hold_s + 1.0, st, "smooth")]
        meta.update(t_activity=t0, t_activity_end=keys[-1][0], descent_s=d_dn)
    elif kind == "drop_keys":
        d_dn = float(rng.uniform(0.9, 1.4))
        bd = Pose(x, y, yaw, joints=bend_joints())
        t0 = 0.8                                                       # keys slip from her hand, a moment of looking down
        keys = [(0.0, st, "smooth"), (t0, st, "smooth"), (t0 + d_dn, bd, "smooth"), (t0 + d_dn + hold_s, bd, "smooth"), (t0 + 2 * d_dn + hold_s, st, "smooth"),
                (t0 + 2 * d_dn + hold_s + 1.0, st, "smooth")]
        meta.update(t_activity=t0, t_activity_end=keys[-1][0], descent_s=d_dn)
    elif kind in ("sit_floor", "lie_floor"):
        d_dn = float(rng.uniform(1.5, 2.2))
        sq = Pose(x, y, yaw, joints=squat_joints(0.9))
        # long sitting on the floor: her pelvis ends up behind the stand point (she sits back)
        fwd = np.array([np.cos(yaw), np.sin(yaw)])
        px, py = np.array([x, y]) - 0.35 * fwd
        floor_sit = Pose(px, py, yaw, joints={"left_hip": (-85, 0, 0), "right_hip": (-85, 0, 0), "left_knee": (12, 0, 0), "right_knee": (12, 0, 0),
                                            "left_shoulder": (-25, 0, 0), "right_shoulder": (-25, 0, 0), "left_elbow": (0, 0, -30), "right_elbow": (0, 0, 30)})
        t0 = 0.5
        keys = [(0.0, st, "smooth"), (t0, st, "smooth"), (t0 + 1.0, sq, "smooth"), (t0 + 1.0 + d_dn, floor_sit, "smooth")]
        if kind == "sit_floor":
            keys += [(keys[-1][0] + hold_s, floor_sit, "smooth"), (keys[-1][0] + hold_s + 1.8, sq, "smooth"), (keys[-1][0] + hold_s + 2.8, st, "smooth")]
        else:
            d_lie = float(rng.uniform(1.5, 2.5))
            lie = Pose(px - 0.55 * fwd[0], py - 0.55 * fwd[1], yaw, lean=-90, joints=lying_joints())
            keys += [(keys[-1][0] + 0.5, floor_sit, "smooth"), (keys[-1][0] + 0.5 + d_lie, lie, "smooth"), (keys[-1][0] + 0.5 + d_lie + hold_s, lie, "smooth")]
            keys += [(keys[-1][0] + d_lie, floor_sit, "smooth"), (keys[-1][0] + d_lie + 1.8, sq, "smooth"), (keys[-1][0] + d_lie + 2.8, st, "smooth")]
        meta.update(t_activity=t0, t_activity_end=keys[-1][0], descent_s=d_dn)
    else:
        raise ValueError(kind)
    return keys, meta


def record_adl(m, rig, spec, rng):
    kind = spec["subtype"]
    path = np.asarray(spec["path"], float)
    v0 = spec["speed"]
    w = W.Walker(m, v0, path=path)
    t_w = w.time_at(w.total)
    frames = walk_frames(w, t_w)
    q_end = w.pose_at(t_w)[w.sl_q].copy()
    pos, psi = w.path_state(w.total)
    stand = spec.get("stand") or (float(pos[0]), float(pos[1]), float(psi))
    keys, meta = adl_keys(kind, stand, rng, spec["hold_s"], spec)
    track = Track(rig, keys)
    # she settles from the stride into the first pose of the activity
    q0 = track.qpos(0.0)
    n_b = int(0.7 / DT)
    for i in range(1, n_b + 1):
        frames.append(blend91(q_end, q0, smooth(i / n_b)))
    t_start = len(frames) * DT
    t = 0.0
    while t <= track.t_end:
        frames.append(track.qpos(t))
        t += DT
    if "t_intake" in meta:
        meta["t_intake"] += t_start
    if "t_hurt" in meta:
        meta["t_hurt"] += t_start
    meta.update(kind="adl", subtype=kind, t_event=t_start + meta["t_activity"], t_event_end=t_start + meta["t_activity_end"], t_floor=None)
    return frames, meta


def make_clip(m, rig, spec):
    rng = np.random.default_rng(spec["seed"])
    frames, meta = (record_fall if spec["kind"] == "fall" else record_adl)(m, rig, spec, rng)
    meta["duration"] = len(frames) * DT
    return Clip(np.array(frames), meta)
