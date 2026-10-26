"""
One experiment trial, two conditions on the SAME recorded woman (paired design):

  robot    the companion robot (follow mode, head camera + MediaPipe, state machine, check-in, dispatch)
  static   baseline: one fixed ceiling camera in the dining corner (static_cam), the same MediaPipe pipeline and the same fall detector
           with the same thresholds, a speaker/microphone next to it, no mobility. Protocol: fall confirmed -> text heads-up and
           "Are you okay?" over the speaker -> 10 s wait for an answer -> family + ambulance if none.

Both write their own telemetry and the per-frame landmark features (so thresholds can be re-fitted offline on the dev split).
"""
import csv
import json
import os
import sys
import time

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for sub in ("sim", "robot", "control", "vision", "experiments"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import apartment_layout as L  # noqa: E402
import robot_spec as S  # noqa: E402
import trial_setup as TS  # noqa: E402
import walk_and_fall as W  # noqa: E402
from behavior import Companion, Params  # noqa: E402
from blazepose_tracker import PoseTracker  # noqa: E402
from dispatch import Dispatcher  # noqa: E402
from fall_detector import FallConfig, FallDetector  # noqa: E402
from navigation import OccupancyGrid  # noqa: E402
from overlay import compose  # noqa: E402
from person_observer import PersonObserver  # noqa: E402
from robot_interface import RobotInterface  # noqa: E402

CTRL_DT, PERC_DT, STATIC_DT = 0.02, 0.05, 1.0 / 15.0          # robot perception 20 Hz, fixed camera 15 Hz
POST_ALERT_S = 6.0
HEAR_RANGE_ROBOT = 3.5                     # m: she is heard by the robot's microphone array within this distance
HEAR_RANGE_STATIC = 4.0                    # m: ... and by the ceiling unit's speaker/microphone (a favourable assumption for the baseline)
SPEAKER_XY = (0.45, 2.85)

_TRACKER = None


def tracker():
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = PoseTracker()
    return _TRACKER


def fall_config(cfg, which="fall_config"):
    """Detector thresholds: cfg['fall_config'] for the robot, cfg['static_fall_config'] for the fixed cameras (each fitted on its own dev streams)."""
    fc = FallConfig()
    for k, v in (cfg or {}).get(which, {}).items():
        setattr(fc, k, v)
    return fc


def trial_end_time(clip, spec):
    return clip.meta["t_event"] + 100.0 if spec["kind"] == "fall" else max(clip.meta["t_event_end"] + 30.0, clip.t_end)


def _site_ids(m):
    return {i: [j for j in range(m.nsite) if m.site(j).name.startswith(f"lm_{i:02d}_")][0] for i in range(33)}


class FeatureLog:
    """Per-perception-tick landmark features (enough to replay the fall detector offline)."""

    def __init__(self):
        self.t, self.world, self.vis, self.valid, self.aspect, self.nv = [], [], [], [], [], []

    def add(self, t, obs):
        self.t.append(t)
        if obs is None:
            self.world.append(np.full((33, 3), np.nan))
            self.vis.append(np.zeros(33))
            self.valid.append(np.zeros(33, bool))
            self.aspect.append(np.nan)
            self.nv.append(0)
        else:
            self.world.append(obs.world.astype(np.float32))
            self.vis.append(obs.vis.astype(np.float32))
            self.valid.append(obs.valid)
            self.aspect.append(obs.aspect)
            self.nv.append(obs.n_valid)

    def save(self, path):
        np.savez_compressed(path, t=np.array(self.t), world=np.array(self.world, dtype=np.float32), vis=np.array(self.vis, dtype=np.float32),
                            valid=np.array(self.valid), aspect=np.array(self.aspect), n_valid=np.array(self.nv))


def _is_below(m, b, root):
    while b > 0:
        if b == root:
            return True
        b = m.body_parentid[b]
    return False


def _setup(ctx, wide_view=False):
    spec = ctx.spec
    m = TS.load_model(TS.SCENE_FULL, spec, ctx.clutter)
    d = mujoco.MjData(m)
    w = W.Walker(m, 0.8)                                     # only for her slices
    vac = W.Vacuum(m, spec["vacuum_speed"])
    off = spec["vacuum_phase"] * vac.perimeter / max(spec["vacuum_speed"], 1e-6)
    rb = RobotInterface(m, d, seed=spec["seed"] % 100000, odom_noise=spec["odom_noise"], wide_view=wide_view)
    x, y, yaw = ctx.start
    d.qpos[rb.qadr:rb.qadr + 7] = [x, y, S.WHEEL_R, np.cos(np.radians(yaw) / 2), 0, 0, np.sin(np.radians(yaw) / 2)]
    return m, d, w, vac, off, rb


def run_robot(ctx, out_dir, cfg=None):
    t0_wall = time.time()
    os.makedirs(out_dir, exist_ok=True)
    cfg = cfg or {}
    spec, clip = ctx.spec, ctx.clip
    m, d, w, vac, voff, rb = _setup(ctx, bool(cfg.get("wide_view")))
    d.qpos[w.sl_q] = clip.at(0.0)
    vac.start_at(voff * vac.speed)
    vac.update(d, voff)
    mujoco.mj_forward(m, d)
    for _ in range(300):                                     # the robot settles on its wheels; she is held
        d.qpos[w.sl_q] = clip.at(0.0)
        d.qvel[w.sl_v] = 0
        mujoco.mj_step(m, d)
    rb.reset_odometry()
    grid = OccupancyGrid(m, d)
    params = Params()
    params.follow = True
    for k, v in cfg.get("params", {}).items():
        setattr(params, k, v)                                  # e.g. siren, cardiac_cues, vertical_sweep, snapshot_consent (family-platform demo)
    fcfg = fall_config(cfg)
    fcfg.fs = 1.0 / PERC_DT                                  # the filter is designed for this camera's rate
    detector = FallDetector(fcfg)
    voice = cfg.get("voice")
    comp = Companion(m, d, rb, grid, PersonObserver(tracker()), detector, Dispatcher(out_dir, voice=voice), params, voice=voice)
    ren = mujoco.Renderer(m, 480, 640)
    feats = FeatureLog()
    site = _site_ids(m)
    rbody = m.body("robot").id
    hb = m.body("pelvis").id
    human_bodies = {b for b in range(m.nbody) if _is_below(m, b, hb)}
    dt = m.opt.timestep
    ctrl_every, perc_every, log_every = int(round(CTRL_DT / dt)), int(round(PERC_DT / dt)), int(round(0.05 / dt))
    t_end = cfg.get("t_end") or trial_end_time(clip, spec)
    push, blackout = spec["push"], spec["blackout"]
    rows, max_force, max_force_h, step = [], 0.0, 0.0, 0
    frames, perc_n, rem_started = [], 0, False
    ov_cam = m.camera("overview").id
    opt = mujoco.MjvOption()
    opt.geomgroup[2] = 0
    viewer = None
    if cfg.get("view"):                                       # live MuJoCo window (macOS: run with mjpython), same overview camera as the GIF
        from mujoco import viewer as mj_viewer
        viewer = mj_viewer.launch_passive(m, d)
        viewer.opt.geomgroup[2] = 0
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE            # a FREE camera that starts at the overview angle: drag to rotate, scroll to zoom, right-drag to pan
        viewer.cam.lookat[:] = [0.0, -0.3, 0.3]
        viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = 9.1, 90.0, -63.0
    t_reply = None
    stopped_at = None
    while True:
        t = step * dt
        d.qpos[w.sl_q] = clip.at(t)
        d.qvel[w.sl_v] = 0.0
        vac.advance(d, dt, [rb.true_pose()[:2], d.xpos[m.body("pelvis").id][:2]])      # the vacuum pauses when it touches the robot or her
        d.xfrc_applied[rbody, :3] = 0.0
        if push and push["t"] <= t < push["t"] + push["dur"]:
            d.xfrc_applied[rbody, :2] = push["force"] * np.array([np.cos(push["angle"]), np.sin(push["angle"])])
        if step % ctrl_every == 0:
            comp.update_control(t, CTRL_DT)
        if step % perc_every == 0:
            if blackout and blackout["t"] <= t < blackout["t"] + blackout["dur"]:
                rgb, dep = np.zeros((480, 640, 3), np.uint8), np.full((480, 640), 20.0)       # lens glare / dropout
            else:
                rgb, dep = rb.grab(ren)
            comp.update_perception(t, rgb, dep)
            feats.add(t, comp.obs)
            perc_n += 1
            if cfg.get("on_tick"):
                cfg["on_tick"](t, comp, d, m, rb)
            if viewer is not None:
                import run_demo as RD
                viewer.user_scn.ngeom = 0
                RD.highlight_robot(viewer.user_scn, rb.true_pose(), rb.mood)             # ring under the 17 cm robot so it can be followed
                viewer.sync()
                if not viewer.is_running():
                    break
            if cfg.get("reminder_at") is not None and not rem_started and t >= cfg["reminder_at"]:
                rem_started = comp.start_reminder(t)
            if cfg.get("gif") and perc_n % cfg.get("gif_every", 2) == 0:
                import run_demo as RD
                ren.update_scene(d, camera=ov_cam, scene_option=opt)
                RD.highlight_robot(ren.scene, rb.true_pose(), rb.mood)
                frames.append(compose(ren.render().copy(), rgb, comp.obs, comp, comp.disp, t))
            # her answer to "Are you okay?": she is awake, the robot has asked, her reply latency has passed and she is within earshot
            if spec["conscious"] and comp.state == "CHECK_IN" and t - comp.t_state >= spec["reply_latency"]:
                hip = np.mean([d.site_xpos[site[23]], d.site_xpos[site[24]]], axis=0)
                if np.hypot(*(hip[:2] - rb.true_pose()[:2])) <= HEAR_RANGE_ROBOT and comp.hear_reply(t):
                    t_reply = t
        if step % log_every == 0:
            hip_true = np.mean([d.site_xpos[site[23]], d.site_xpos[site[24]]], axis=0)
            f, f_who = rb.collision_force(exclude=human_bodies, detail=True)
            fh = rb.collision_force(only=human_bodies)
            max_force = max(max_force, f)
            max_force_h = max(max_force_h, fh)
            tp, vtr = rb.true_pose(), rb.true_velocity()
            q = d.qpos[rb.qadr + 3:rb.qadr + 7]
            pitch = np.degrees(np.arcsin(np.clip(2 * (q[0] * q[2] - q[3] * q[1]), -1, 1)))
            roll = np.degrees(np.arctan2(2 * (q[0] * q[1] + q[2] * q[3]), 1 - 2 * (q[1] ** 2 + q[2] ** 2)))
            vacp = d.xpos[m.body("vacuum").id]
            lms = np.array([d.site_xpos[site[i]] for i in range(33)])
            rows.append(dict(
                t=round(t, 3), state=comp.state, detector=detector.state,
                x=tp[0], y=tp[1], z=d.qpos[rb.qadr + 2], roll_deg=roll, pitch_deg=pitch, yaw=tp[2],
                vx=d.qvel[rb.vadr], vy=d.qvel[rb.vadr + 1], vz=d.qvel[rb.vadr + 2], v_fwd=vtr[0], yaw_rate=vtr[1], est_x=rb.est[0], est_y=rb.est[1], est_yaw=rb.est[2],
                cmd_v=rb.last_cmd[0], cmd_w=rb.last_cmd[1], wheel_ctrl_l=d.ctrl[rb.a_l], wheel_ctrl_r=d.ctrl[rb.a_r],
                pan_deg=rb.neck_angles_deg()[0], tilt_deg=rb.neck_angles_deg()[1], collision_force_N=f, contact_body=(f_who if f > 0.5 else ""), human_contact_N=fh, front_range_m=comp.front_range,
                dist_to_hip_m=float(np.hypot(*(hip_true[:2] - tp[:2]))), dist_to_nearest_body_m=float(np.min(np.hypot(*(lms[:, :2] - tp[:2]).T))),
                human_hip_z=hip_true[2], human_x=hip_true[0], human_y=hip_true[1], seen=int(comp.obs is not None),
                vacuum_x=vacp[0], vacuum_y=vacp[1], vacuum_dist_m=float(np.hypot(*(vacp[:2] - tp[:2]))),
                det_hip_z=detector.features.get("hip_z", float("nan")), det_pitch_deg=detector.features.get("pitch", float("nan")),
                bytes_off_board=comp.disp.bytes_off_board))
        mujoco.mj_step(m, d)
        step += 1
        if comp.state == "ALERT" and t - comp.t_alert > cfg.get("post_alert_s", POST_ALERT_S):
            break
        if cfg.get("stop_when") and cfg["stop_when"](t, comp):
            break
        if cfg.get("stop_after_reminder") and comp.reminder and (comp.reminder["t_ack"] or comp.reminder["t_missed"]) and t - (comp.reminder["t_ack"] or comp.reminder["t_missed"]) > 4.0:
            break
        if t > t_end:
            break
    t_final = step * dt
    sent = comp.disp.sent
    first = lambda kind: next((s["t"] for s in sent if s["kind"] == kind), None)
    hu = np.array([r["human_x"] for r in rows])
    sp = np.abs([r["v_fwd"] for r in rows])
    dist = np.hypot(np.diff([r["x"] for r in rows]), np.diff([r["y"] for r in rows])).sum()
    check_rows = [r for r in rows if r["state"] == "CHECK_IN"]
    summary = dict(
        id=spec["id"], condition="robot", kind=spec["kind"], subtype=spec["subtype"], conscious=spec["conscious"],
        t_event=clip.meta["t_event"], t_floor=clip.meta.get("t_floor"), t_end=round(t_final, 2),
        t_first_detect=detector.t_impact if detector.t_confirmed is not None or detector.t_impact is not None else None,
        t_confirmed=detector.t_confirmed, t_heads_up=first("heads_up"), t_emergency=first("emergency"), t_ambulance=first("ambulance_call"),
        t_all_clear=first("all_clear"), t_reply_heard=t_reply, check_in_started=comp.checkin_started_t is not None,
        n_alarms=sum(1 for _, s in comp.events if s.startswith(("Fall suspected", "Person down"))),
        standoff_nearest_body_m=None if not check_rows else round(check_rows[0]["dist_to_nearest_body_m"], 2),
        max_collision_force_N=round(max_force, 3), max_human_contact_N=round(max_force_h, 3), max_speed_mps=round(float(sp.max()), 3), distance_travelled_m=round(float(dist), 2),
        max_tilt_deg=round(max(abs(r["pitch_deg"]) for r in rows), 2),
        bytes_off_board_before_first_alert=0 if comp.disp.first_send_t is None else int(next((r["bytes_off_board"] for r in rows if r["t"] >= comp.disp.first_send_t - 0.06), 0)),
        bytes_off_board_total=comp.disp.bytes_off_board, pose_error_final_m=round(float(np.hypot(*(rb.est[:2] - rb.true_pose()[:2]))), 3),
        reminder=comp.reminder, pose_corrections=comp.pose_corrections, first_seen_t=next((r["t"] for r in rows if r["seen"]), None),
        sim_seconds=round(t_final, 1), wall_seconds=round(time.time() - t0_wall, 1))
    with open(os.path.join(out_dir, "telemetry_robot.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    feats.save(os.path.join(out_dir, "features_robot.npz"))
    with open(os.path.join(out_dir, "events_robot.json"), "w") as f:
        json.dump(dict(summary=summary, events=comp.events, detector_log=detector.log), f, indent=1)
    comp.disp.save()
    if frames:
        from PIL import Image
        pal = [f.convert("P", palette=Image.ADAPTIVE, colors=96) for f in frames]
        pal[0].save(os.path.join(out_dir, "demo.gif"), save_all=True, append_images=pal[1:], duration=int(1000 * PERC_DT * cfg.get("gif_every", 2)), loop=0, optimize=True)
    ren.close()
    return summary


STATIC_CAMS = ("static_cam", "static_hall_w", "static_hall_e", "static_bed")


class House:
    """Shared state of a set of fixed-camera units: one check-in at a time; once she answers, the others stay quiet until everybody sees her up."""

    def __init__(self):
        self.active = None
        self.silenced = False


class Unit:
    """One fixed camera's protocol: fall confirmed -> text heads-up + 'Are you okay?' over its speaker -> 10 s -> family + ambulance."""

    def __init__(self, house, speaker_xy, disp, spec):
        self.house, self.speaker, self.disp, self.spec = house, np.asarray(speaker_xy[:2]), disp, spec
        self.state, self.t_state = "WATCH", 0.0
        self.t_heads_up = self.t_emergency = self.t_reply = None
        self.n_alarms = 0
        self.log = []

    def step(self, t, ds, obs, hip, t_impact):
        h = self.house
        if self.state == "WATCH" and ds == "confirmed" and not h.silenced and h.active is None:
            self.state, self.t_state = "CHECK_IN", t
            h.active = self
            self.n_alarms += 1
            xy = obs.hip[:2] if obs is not None and obs.hip is not None else hip[:2]
            self.disp.heads_up(t, xy, t_impact)
            self.t_heads_up = self.t_heads_up if self.t_heads_up is not None else t
            self.log.append((round(t, 2), "fall confirmed: text heads-up sent, speaker asks 'Are you okay?'"))
        elif self.state == "CHECK_IN":
            if ds == "normal":
                self.state, h.active = "WATCH", None
                self.log.append((round(t, 2), "alarm cancelled: she is up again"))
            elif self.spec["conscious"] and t - self.t_state >= self.spec["reply_latency"] and np.hypot(*(hip[:2] - self.speaker)) <= HEAR_RANGE_STATIC:
                self.state, self.t_reply, h.active, h.silenced = "WATCH", t, None, True
                self.disp.all_clear(t)
                self.log.append((round(t, 2), "she answered: all clear"))
            elif t - self.t_state >= 10.0:
                self.state, self.t_emergency = "ALERT", t
                xy = obs.hip[:2] if obs is not None and obs.hip is not None else hip[:2]
                self.disp.emergency(t, xy, t_impact, 10.0, evidence="fixed camera")
                self.log.append((round(t, 2), "no answer for 10 s: EMERGENCY (family + ambulance, simulated)"))


def in_view(d, cam, fovy_deg, pts, w=640, h=480):
    """True if any of the 3D points (her landmarks) projects inside this camera's image (a cheap field-of-view test used to skip
    rendering and pose estimation for cameras that cannot possibly see her; walls and furniture are still rendered when she may be in view)."""
    f = 0.5 * h / np.tan(np.radians(fovy_deg) / 2)
    R = d.cam_xmat[cam].reshape(3, 3)
    pc = (pts - d.cam_xpos[cam]) @ R
    z = -pc[:, 2]
    ok = z > 0.1
    u = w / 2 + f * pc[:, 0] / np.where(ok, z, 1)
    v = h / 2 - f * pc[:, 1] / np.where(ok, z, 1)
    return bool(np.any(ok & (u > 0) & (u < w) & (v > 0) & (v < h)))


def run_static(ctx, out_dir, cfg=None):
    """Baselines on the same recorded motion: 'static' = one fixed camera in the living-dining corner; 'static4' = four fixed cameras that
    cover every room (living-dining, hallway west, hallway east, bedroom). Same MediaPipe pipeline, same detector thresholds, no mobility."""
    t0_wall = time.time()
    os.makedirs(out_dir, exist_ok=True)
    spec, clip = ctx.spec, ctx.clip
    m, d, w, vac, voff, rb = _setup(ctx)
    cams = [m.camera(n).id for n in STATIC_CAMS]
    fc = fall_config(cfg, "static_fall_config")
    fc.fs = 1.0 / STATIC_DT                                  # the filter is designed for the sampling rate of this camera
    dets = [FallDetector(fc) for _ in cams]
    observers = [PersonObserver(tracker(), fovy_deg=float(m.cam_fovy[c])) for c in cams]
    house1, house4 = House(), House()
    disp1 = Dispatcher(os.path.join(out_dir, "static_alerts"))
    disp4 = Dispatcher(os.path.join(out_dir, "static4_alerts"))
    units1 = [Unit(house1, d.cam_xpos[cams[0]], disp1, spec)]
    mujoco.mj_forward(m, d)
    units1 = [Unit(house1, d.cam_xpos[cams[0]], disp1, spec)]
    units4 = [Unit(house4, d.cam_xpos[c], disp4, spec) for c in cams]
    ren = mujoco.Renderer(m, 480, 640)
    feats = [FeatureLog() for _ in cams]
    site = _site_ids(m)
    t_end = trial_end_time(clip, spec)
    blackout = spec["blackout"]
    t_stop = clip.meta["t_event"] + 60.0 if spec["kind"] == "fall" else t_end          # nothing changes after she is down: 60 s without a detection is a miss
    t = 0.0
    while t <= t_end:
        d.qpos[w.sl_q] = clip.at(t)
        d.qvel[w.sl_v] = 0.0
        vac.update(d, t + voff)
        mujoco.mj_forward(m, d)
        hip = np.mean([d.site_xpos[site[23]], d.site_xpos[site[24]]], axis=0)
        lm_pts = np.array([d.site_xpos[site[i]] for i in range(33)])
        for k, c in enumerate(cams):
            if (blackout and blackout["t"] <= t < blackout["t"] + blackout["dur"]) or not in_view(d, c, float(m.cam_fovy[c]), lm_pts):
                obs = None
            else:
                ren.update_scene(d, camera=c)
                rgb = ren.render().copy()
                ren.enable_depth_rendering()
                ren.update_scene(d, camera=c)
                dep = ren.render().copy()
                ren.disable_depth_rendering()
                obs = observers[k].observe(rgb, dep, None, 0, 0, cam=(d.cam_xpos[c].copy(), d.cam_xmat[c].reshape(3, 3).copy()))
            feats[k].add(t, obs)
            ds = dets[k].update(t, obs)
            if k == 0:
                units1[0].step(t, ds, obs, hip, dets[0].t_impact)
            units4[k].step(t, ds, obs, hip, dets[k].t_impact)
        if all(dd.state == "normal" for dd in dets):
            house4.silenced = house1.silenced = False
        done1 = units1[0].state == "ALERT" and t - units1[0].t_emergency > POST_ALERT_S
        done4 = any(u.state == "ALERT" and t - u.t_emergency > POST_ALERT_S for u in units4)
        if (done1 or t > t_stop) and (done4 or t > t_stop) and all(u.state != "CHECK_IN" for u in units4) and units1[0].state != "CHECK_IN":
            break
        t += STATIC_DT

    def summ(name, units, disp, which):
        e = [u.t_emergency for u in units if u.t_emergency is not None]
        hu = [u.t_heads_up for u in units if u.t_heads_up is not None]
        rp = [u.t_reply for u in units if u.t_reply is not None]
        det = [dets[k] for k in which]
        return dict(id=spec["id"], condition=name, kind=spec["kind"], subtype=spec["subtype"], conscious=spec["conscious"],
                    t_event=clip.meta["t_event"], t_floor=clip.meta.get("t_floor"), t_end=round(t, 2),
                    t_first_detect=min([x.t_impact for x in det if x.t_impact is not None], default=None),
                    t_confirmed=min([x.t_confirmed for x in det if x.t_confirmed is not None], default=None),
                    t_heads_up=min(hu, default=None), t_emergency=min(e, default=None), t_ambulance=min(e, default=None),
                    t_reply_heard=min(rp, default=None), n_alarms=sum(u.n_alarms for u in units), bytes_off_board_total=disp.bytes_off_board,
                    frames_with_person=int(max(sum(1 for n in feats[k].nv if n >= 12) for k in which)), frames_total=len(feats[0].nv),
                    wall_seconds=round(time.time() - t0_wall, 1))
    out = dict(static=summ("static", units1, disp1, [0]), static4=summ("static4", units4, disp4, [0, 1, 2, 3]))
    for k, nm in enumerate(("static_cam", "static_hall_w", "static_hall_e", "static_bed")):
        feats[k].save(os.path.join(out_dir, f"features_{nm}.npz"))
    with open(os.path.join(out_dir, "events_static.json"), "w") as f:
        json.dump(dict(summary=out, events_static=units1[0].log, events_static4={STATIC_CAMS[k]: u.log for k, u in enumerate(units4)},
                       detector_log={STATIC_CAMS[k]: dets[k].log for k in range(4)}), f, indent=1)
    ren.close()
    return out


def run_one(spec, out_root, cfg=None, conditions=("robot", "static", "static4")):
    """Prepare (record her motion, place clutter, pick the robot start) and run the requested conditions; one folder per trial."""
    out_dir = os.path.join(out_root, spec["id"])
    os.makedirs(out_dir, exist_ok=True)
    ctx = TS.prepare(spec, os.path.join(out_root, "..", "clips"))
    q_after = ctx.clip.at(ctx.clip.meta["t_event"] + 3.0)
    fall_xy = [float(q_after[0]), float(q_after[1])]
    with open(os.path.join(out_dir, "spec.json"), "w") as f:
        json.dump(dict(spec=spec, clutter=ctx.clutter, robot_start=ctx.start, clip_meta=ctx.clip.meta, event_xy=fall_xy, event_room=L.room_of(*fall_xy)), f, indent=1)
    res = {}
    if "robot" in conditions:
        res["robot"] = run_robot(ctx, out_dir, cfg)
    if "static" in conditions or "static4" in conditions:
        res.update(run_static(ctx, out_dir, cfg))
    with open(os.path.join(out_dir, "result.json"), "w") as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    import scenarios as SC
    split, n, seed0, idx = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    cond = tuple(sys.argv[5].split(",")) if len(sys.argv) > 5 else ("robot", "static", "static4")
    spec = SC.make_specs(split, n, seed0)[idx]
    out = os.path.join(ROOT, "outputs", "experiments", split)
    r = run_one(spec, out, None, cond)
    print(json.dumps(r, indent=1))
