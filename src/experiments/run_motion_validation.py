"""
Motion-control validation (dossier Section 4): N seeded robot runs with a 500 Hz log of the channels the guide asks for.

  python src/experiments/run_motion_validation.py 30 3 --workers 5 --cfg outputs/experiments/frozen_config.json
  python src/experiments/analyze_motion.py

Per physics step (0.002 s = 500 Hz) and per trial, saved to outputs/experiments/motion/<id>/fast_log.npz:
  t, true x y yaw, world velocity vx vy, actuator forces (wheel torques N.m, neck pan and head tilt N.m), FSM state code,
  distance from the robot's true position to the planned path that the path follower is tracking (NaN when no path is active), and the commanded speed and turn rate.
Tracking RMSE is computed only on steps where the follower is actually driving (commanded speed above 0.05 m/s), so waiting, turning on the spot and the reactive final creep are excluded.
Tracking RMSE = sqrt(mean(d^2)) over the steps where the follower tracks a path; control effort = integral of the sum of torque^2 dt.
Only the robot condition runs (the fixed cameras do not move, so they have no tracking error or torque).
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
STATES = ["WATCH", "FOLLOW", "SEARCH", "OBSERVE", "SUSPECT", "APPROACH", "CHECK_IN", "ALERT"]


class Recorder:
    def __init__(self):
        self.rows = []
        self.act = None

    def step(self, t, comp, d, m, rb):
        import mujoco
        if self.act is None:
            self.act = [rb.a_l, rb.a_r, rb.a_pan, rb.a_tilt]
        tp = rb.true_pose()
        f = comp.follower
        dist = np.nan
        if f is not None and not getattr(f, "done", False) and len(f.path) >= 2:
            P = np.array(f.path)
            a, b = P[:-1], P[1:]
            ab = b - a
            L2 = np.maximum((ab ** 2).sum(1), 1e-12)
            u = np.clip((((tp[:2] - a) * ab).sum(1)) / L2, 0, 1)
            dist = float(np.min(np.hypot(*(a + ab * u[:, None] - tp[:2]).T)))
        st = STATES.index(comp.state) if comp.state in STATES else -1
        fa = d.actuator_force
        self.rows.append((t, tp[0], tp[1], tp[2], d.qvel[rb.vadr], d.qvel[rb.vadr + 1], fa[self.act[0]], fa[self.act[1]], fa[self.act[2]], fa[self.act[3]], st, dist, rb.last_cmd[0], rb.last_cmd[1]))


def _work(args):
    spec, out_root, cfg = args
    os.environ.setdefault("MUJOCO_GL", "glfw")
    import run_trial as RT
    rec = Recorder()
    cfg = dict(cfg or {}); cfg["on_step"] = rec.step
    t0 = time.time()
    try:
        RT.run_one(spec, out_root, cfg, ("robot",))
        a = np.array(rec.rows, float)
        np.savez_compressed(os.path.join(out_root, spec["id"], "fast_log.npz"), data=a,
                            columns=np.array(["t", "x", "y", "yaw", "vx", "vy", "tau_l", "tau_r", "tau_pan", "tau_tilt", "state", "path_dist", "cmd_v", "cmd_w"]), states=np.array(STATES))
        return spec["id"], None, time.time() - t0
    except Exception:
        return spec["id"], traceback.format_exc(), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int); ap.add_argument("seed0", type=int)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--cfg")
    a = ap.parse_args()
    import scenarios as SC
    specs = SC.make_specs("motion", a.n, a.seed0)
    cfg = json.load(open(a.cfg)) if a.cfg else {}
    out_root = os.path.join(ROOT, "outputs", "experiments", "motion"); os.makedirs(out_root, exist_ok=True)
    todo = [s for s in specs if not os.path.exists(os.path.join(out_root, s["id"], "fast_log.npz"))]
    print(f"{len(specs)} trials, {len(todo)} to run", flush=True)
    t0 = time.time(); done = 0
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context("spawn")) as ex:
        futs = [ex.submit(_work, (s, out_root, cfg)) for s in todo]
        for f in as_completed(futs):
            tid, err, dt = f.result(); done += 1
            print(f"[{done}/{len(todo)}] {tid} {'ok' if err is None else 'ERROR'} {dt:.0f}s (elapsed {(time.time() - t0) / 60:.1f} min)", flush=True)
            if err: print(err, flush=True)


if __name__ == "__main__":
    main()
