"""
Full demo: she walks through the flat and falls; the robot (camera + MediaPipe + its own odometry) notices, drives
to her, checks on her, and tells the family and the ambulance (simulated).

Run:   MUJOCO_GL=glfw python src/sim/run_demo.py                (video + telemetry in outputs/demo_run/)
       MUJOCO_GL=glfw python src/sim/run_demo.py --no-gif       (faster, logs only)
       mjpython src/sim/run_demo.py --view                      (live window, events printed as they happen)
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time

import mujoco
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for sub in ("sim", "robot", "control", "vision"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import apartment_layout as L  # noqa: E402
import robot_spec as S  # noqa: E402
import walk_and_fall as W  # noqa: E402
from behavior import Companion, Params  # noqa: E402
from blazepose_tracker import PoseTracker  # noqa: E402
from dispatch import Dispatcher  # noqa: E402
from fall_detector import FallDetector  # noqa: E402
from navigation import OccupancyGrid  # noqa: E402
from overlay import compose  # noqa: E402
from person_observer import PersonObserver  # noqa: E402
from robot_interface import RobotInterface, quat_to_yaw  # noqa: E402

SCENE = os.path.join(ROOT, "models", "scene_full.xml")
CTRL_DT, PERC_DT = 0.02, 0.032


RING = {"watching": (0.21, 0.88, 0.91), "worried": (1.0, 0.69, 0.0), "happy": (0.2, 0.8, 0.35), "alert": (0.84, 0.27, 0.24)}


def highlight_robot(scene, pos, mood):
    """Translucent disc on the floor under the robot so it can be followed in the overview (it is only 17 cm tall)."""
    if scene.ngeom >= scene.maxgeom - 1:
        return
    g = scene.geoms[scene.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CYLINDER, np.array([0.40, 0.004, 0.0]), np.array([pos[0], pos[1], 0.02]),
                        np.eye(3).ravel(), np.array([*RING[mood], 0.5], dtype=np.float32))
    scene.ngeom += 1


def run(out_dir, make_gif=True, gif_every=3, max_t=60.0, post_alert=12.0, seed=0, obstacle_speed=L.VACUUM_SPEED,
        speed=0.8, dock=None, quiet=False, params=None, detector=None, responds_at=None, view=False, scenario="follow", diagnostics=False):
    t0_wall = time.time()
    os.makedirs(out_dir, exist_ok=True)
    if params is None:
        params = Params()
        params.follow = scenario == "follow"
    if dock is None and scenario == "follow":
        dock = L.ROBOT_START_FOLLOW
    m = mujoco.MjModel.from_xml_path(SCENE)
    d = mujoco.MjData(m)
    w = W.Walker(m, speed)
    vac = W.Vacuum(m, obstacle_speed)
    rb = RobotInterface(m, d, seed=seed)
    if dock is not None:
        x, y, yaw = dock
        d.qpos[rb.qadr:rb.qadr + 7] = [x, y, S.WHEEL_R, np.cos(np.radians(yaw) / 2), 0, 0, np.sin(np.radians(yaw) / 2)]
    w.apply(d, 0.0)
    vac.update(d, 0.0)
    mujoco.mj_forward(m, d)
    for _ in range(300):                                         # let the robot settle on its wheels (she is held in her walking pose)
        w.apply(d, 0.0)
        mujoco.mj_step(m, d)
    w.apply(d, 0.0)
    mujoco.mj_forward(m, d)
    rb.reset_odometry()
    grid = OccupancyGrid(m, d)
    tracker = PoseTracker()
    comp = Companion(m, d, rb, grid, PersonObserver(tracker), detector or FallDetector(), Dispatcher(out_dir), params)
    ren = mujoco.Renderer(m, 480, 640)
    ov_cam = m.camera("overview").id
    opt = mujoco.MjvOption()
    opt.geomgroup[2] = 0

    viewer = None
    if view:                                                      # live window (macOS: run with mjpython)
        from mujoco import viewer as mj_viewer
        viewer = mj_viewer.launch_passive(m, d)
        viewer.opt.geomgroup[2] = 0
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE            # a FREE camera that starts at the overview angle: drag to rotate, scroll to zoom, right-drag to pan
        viewer.cam.lookat[:] = [0.0, -0.3, 0.3]
        viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = 9.1, 90.0, -63.0
        comp.on_event = lambda te, text: print(f"[{te:6.2f} s] {text}", flush=True)
    live = diag_proc = None
    if diagnostics:                                               # integrated diagnostics window: its own process, fed through a JSONL file
        live_path = os.path.join(out_dir, "live_diagnostics.jsonl")
        live = open(live_path, "w")
        py, script = os.path.join(sys.prefix, "bin", "python"), os.path.join(HERE, "diagnostics_window.py")
        if sys.platform == "darwin":                                # a child started from mjpython exits at once; Terminal (via open) keeps the window alive
            cmd_file = os.path.join(out_dir, "open_diagnostics.command")
            with open(cmd_file, "w") as f:
                f.write(f"#!/bin/zsh\ncd '{ROOT}'\nexec '{py}' '{script}' --live '{live_path}'\n")
            os.chmod(cmd_file, 0o755)
            diag_proc = subprocess.Popen(["open", cmd_file])
        else:
            diag_proc = subprocess.Popen([py, script, "--live", live_path], start_new_session=True)
        prev = comp.on_event

        def on_event(te, text):
            if prev is not None:
                prev(te, text)
            live.write(json.dumps(dict(t=round(te, 2), event=text)) + "\n")
            live.flush()
        comp.on_event = on_event

    t_fall = w.default_trip_time()
    hold = None
    dt = m.opt.timestep
    ctrl_every, perc_every = int(round(CTRL_DT / dt)), int(round(PERC_DT / dt))
    log, frames, rows = [], [], []
    pel = m.body("pelvis").id
    site = {i: [j for j in range(m.nsite) if m.site(j).name.startswith(f"lm_{i:02d}_")][0] for i in range(33)}
    t_hit_floor, max_force, perc_n, t_end = None, 0.0, 0, max_t
    step = 0
    while True:
        t = step * dt
        if t < t_fall:
            w.apply(d, t)
        elif hold is None:
            q_rel = W.release(m, d, w, t_fall, speed, 1.9, 1.0)
            hold = W.ReflexHold(m, d, 0.45)
            hold.target = W.make_target(m, q_rel, 1.0, 70.0, 1.0)
        else:
            hold.apply(d, t - t_fall)
        vac.update(d, t)
        if step % ctrl_every == 0:
            comp.update_control(t, CTRL_DT)
        if step % perc_every == 0:
            rgb, dep = rb.grab(ren)
            comp.update_perception(t, rgb, dep)
            perc_n += 1
            if viewer is not None:
                viewer.user_scn.ngeom = 0
                highlight_robot(viewer.user_scn, rb.true_pose(), rb.mood)
                viewer.sync()
                if not viewer.is_running():
                    break
            if make_gif and perc_n % gif_every == 0:
                ren.update_scene(d, camera=ov_cam, scene_option=opt)
                highlight_robot(ren.scene, rb.true_pose(), rb.mood)
                frames.append(compose(ren.render().copy(), rgb, comp.obs, comp, comp.disp, t))
        if step % int(round(0.05 / dt)) == 0:
            hip_true = np.mean([d.site_xpos[site[23]], d.site_xpos[site[24]]], axis=0)
            if t_hit_floor is None and t > t_fall and hip_true[2] < 0.20:
                t_hit_floor = t
            f = rb.collision_force()
            max_force = max(max_force, f)
            tp = rb.true_pose()
            vtr = rb.true_velocity()
            q = d.qpos[rb.qadr + 3:rb.qadr + 7]
            pitch = np.degrees(np.arcsin(np.clip(2 * (q[0] * q[2] - q[3] * q[1]), -1, 1)))
            roll = np.degrees(np.arctan2(2 * (q[0] * q[1] + q[2] * q[3]), 1 - 2 * (q[1] ** 2 + q[2] ** 2)))
            vacp = d.xpos[m.body("vacuum").id]
            lms = np.array([d.site_xpos[site[i]] for i in range(33)])
            rows.append(dict(
                t=round(t, 3), state=comp.state, detector=comp.detector.state,
                x=tp[0], y=tp[1], z=d.qpos[rb.qadr + 2], roll_deg=roll, pitch_deg=pitch, yaw=tp[2],
                v_fwd=vtr[0], yaw_rate=vtr[1], est_x=rb.est[0], est_y=rb.est[1], est_yaw=rb.est[2],
                cmd_v=rb.last_cmd[0], cmd_w=rb.last_cmd[1], wheel_ctrl_l=d.ctrl[rb.a_l], wheel_ctrl_r=d.ctrl[rb.a_r],
                pan_deg=rb.neck_angles_deg()[0], tilt_deg=rb.neck_angles_deg()[1], collision_force_N=f, front_range_m=comp.front_range,
                dist_to_hip_m=float(np.hypot(*(hip_true[:2] - tp[:2]))), dist_to_nearest_body_m=float(np.min(np.hypot(*(lms[:, :2] - tp[:2]).T))),
                human_hip_z=hip_true[2], human_x=hip_true[0], human_y=hip_true[1], seen=int(comp.obs is not None), n_landmarks=0 if comp.obs is None else comp.obs.n_valid,
                vacuum_x=vacp[0], vacuum_y=vacp[1], vacuum_dist_m=float(np.hypot(*(vacp[:2] - tp[:2]))),
                det_hip_z=comp.detector.features.get("hip_z", float("nan")), det_pitch_deg=comp.detector.features.get("pitch", float("nan")),
                det_aspect=comp.detector.features.get("aspect", float("nan")), det_drift_m=comp.detector.features.get("drift") if comp.detector.features.get("drift") is not None else float("nan"), bytes_off_board=comp.disp.bytes_off_board))
        if live is not None and step % int(round(0.05 / dt)) == 0 and rows:
            live.write(json.dumps({k: (None if isinstance(v, float) and v != v else v) for k, v in rows[-1].items()}) + "\n")
            live.flush()
        mujoco.mj_step(m, d)
        step += 1
        if comp.state == "ALERT" and t - comp.t_alert > post_alert:
            break
        if t > max_t:
            break
    t_final = step * dt
    if viewer is not None:
        viewer.close()
    if live is not None:
        live.close()
        if diag_proc is not None and not quiet:
            print("Diagnostics window stays open: close it when you are done.")

    # ---- summary ----------------------------------------------------------------------------------------------------
    sent = comp.disp.sent
    first = lambda kind: next((s["t"] for s in sent if s["kind"] == kind), None)
    approach_rows = [r for r in rows if r["state"] == "CHECK_IN"]
    summary = dict(
        t_fall_start=round(t_fall, 2), t_hip_hit_floor=None if t_hit_floor is None else round(t_hit_floor, 2),
        t_impact_detected=None if comp.detector.t_impact is None else round(comp.detector.t_impact, 2),
        t_confirmed_down=None if comp.detector.t_confirmed is None else round(comp.detector.t_confirmed, 2),
        t_check_in_start=next((t for t, s in comp.events if s.startswith("Robot says: \"Are you okay")), None),
        t_family_heads_up=first("heads_up"), t_family_emergency=first("emergency"), t_ambulance_call=first("ambulance_call"),
        standoff_hip_m=None if not approach_rows else round(approach_rows[0]["dist_to_hip_m"], 2),
        standoff_nearest_body_m=None if not approach_rows else round(approach_rows[0]["dist_to_nearest_body_m"], 2),
        max_collision_force_N=round(max_force, 3), max_tilt_deg=round(max(abs(r["pitch_deg"]) for r in rows), 2),
        bytes_off_board_before_first_alert=0 if comp.disp.first_send_t is None else int(next((r["bytes_off_board"] for r in rows if r["t"] >= comp.disp.first_send_t - 0.06), 0)),
        bytes_off_board_total=comp.disp.bytes_off_board, pose_estimate_final_error_m=round(float(np.hypot(*(rb.est[:2] - rb.true_pose()[:2]))), 3), pose_corrections_by_scan_matching=comp.pose_corrections,
        sim_seconds=round(t_final, 1), wall_seconds=round(time.time() - t0_wall, 1))
    if summary["t_impact_detected"] is not None and t_hit_floor is not None:
        summary["latency_fall_to_detect_s"] = round(summary["t_impact_detected"] - t_hit_floor, 2)
    for key, label in (("t_family_heads_up", "latency_fall_to_family_heads_up_s"), ("t_family_emergency", "latency_fall_to_family_emergency_s"), ("t_ambulance_call", "latency_fall_to_ambulance_call_s")):
        if summary[key] is not None and t_hit_floor is not None:
            summary[label] = round(summary[key] - t_hit_floor, 2)
    with open(os.path.join(out_dir, "telemetry.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    with open(os.path.join(out_dir, "events.json"), "w") as f:
        json.dump(dict(summary=summary, events=comp.events, detector_log=comp.detector.log), f, indent=2)
    comp.disp.save()
    if make_gif and frames:
        pal = [f.convert("P", palette=Image.ADAPTIVE, colors=96) for f in frames]
        pal[0].save(os.path.join(out_dir, "demo.gif"), save_all=True, append_images=pal[1:], duration=int(1000 * PERC_DT * gif_every), loop=0, optimize=True)
    if not quiet:
        print(json.dumps(summary, indent=2))
        for te, text in comp.events:
            print(f"  {te:6.2f}s  {text}")
    return summary, comp


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "demo_run"))
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--gif-every", type=int, default=3)
    ap.add_argument("--max-t", type=float, default=60.0)
    ap.add_argument("--scenario", choices=["follow", "watch"], default="follow", help="follow: starts in the bedroom and follows her; watch: waits on its dock")
    ap.add_argument("--speed", type=float, default=0.8, help="her walking speed in m/s (frail elderly: about 0.6)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--view", action="store_true", help="live window (macOS: use mjpython); implies --no-gif")
    ap.add_argument("--obstacle-speed", type=float, default=L.VACUUM_SPEED)
    ap.add_argument("--no-diag", action="store_true", help="with --view: do not open the integrated diagnostics window")
    a = ap.parse_args()
    run(a.out, make_gif=not (a.no_gif or a.view), gif_every=a.gif_every, max_t=a.max_t, seed=a.seed, obstacle_speed=a.obstacle_speed, view=a.view, scenario=a.scenario, speed=a.speed, diagnostics=a.view and not a.no_diag)
