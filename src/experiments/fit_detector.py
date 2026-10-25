"""
Fit the fall-detector thresholds on the DEV split only (offline replay of the recorded landmark streams), then freeze them.

    python src/experiments/fit_detector.py dev            ->  outputs/experiments/frozen_config.json  (+ a log of every step)

The streams are the per-frame landmark features recorded during the dev trials (fixed camera and robot camera).  A stream is
scored like a trial: positive if it belongs to a fall, predicted positive if the detector reached "confirmed" after the fall began;
a "confirmed" in an activity trial (or before the fall) is a false alarm.  Search: coordinate descent over a small grid around the
defaults (objective: F1 over all streams, ties broken by fewer false alarms, then lower latency).
The robot streams are not exactly what a re-run would see (the robot would react differently), so this is an approximation that
is fine for choosing thresholds, and the TEST split is only ever run with the frozen result.
"""
import json
import os
import sys
from dataclasses import asdict

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "vision"))
from fall_detector import FallConfig, FallDetector  # noqa: E402


class FakeObs:
    def __init__(self, world, valid, vis, aspect, n_valid):
        self.world, self.valid, self.vis, self.aspect, self.n_valid = world, valid, vis, float(aspect), int(n_valid)

    def _pt(self, *idx):
        ok = [i for i in idx if self.valid[i] and self.vis[i] > 0.3 and np.isfinite(self.world[i]).all()]
        return self.world[ok].mean(0) if ok else None

    @property
    def hip(self):
        return self._pt(23, 24)

    def torso_pitch_deg(self):
        h, s = self._pt(23, 24), self._pt(11, 12)
        if h is None or s is None:
            return None
        v = s - h
        return float(np.degrees(np.arccos(np.clip(v[2] / max(np.linalg.norm(v), 1e-6), -1, 1))))


def load_streams(split):
    base = os.path.join(ROOT, "outputs", "experiments", split)
    out = []
    for tid in sorted(os.listdir(base)):
        fn = os.path.join(base, tid, "result.json")
        if not os.path.exists(fn):
            continue
        sp = json.load(open(os.path.join(base, tid, "spec.json")))
        for cond, name in (("robot", "features_robot.npz"), ("static", "features_static_cam.npz"), ("static", "features_static_hall_w.npz"),
                           ("static", "features_static_hall_e.npz"), ("static", "features_static_bed.npz")):
            p = os.path.join(base, tid, name)
            if not os.path.exists(p):
                continue
            z = np.load(p)
            obs = [None if z["n_valid"][i] == 0 else FakeObs(z["world"][i].astype(float), z["valid"][i], z["vis"][i], z["aspect"][i], z["n_valid"][i]) for i in range(len(z["t"]))]
            dt = float(np.median(np.diff(z["t"])))
            t_ev = sp["clip_meta"]["t_event"]
            seen_s = float(((z["t"] > t_ev) & (z["n_valid"] >= 12)).sum() * dt)           # how long this camera saw her after the event began
            out.append(dict(id=tid, cond=cond, kind=sp["spec"]["kind"], t_event=t_ev, t=z["t"], obs=obs, fs=1.0 / dt, seen_after=seen_s))
    return out


def replay(streams, cfg_over):
    """Returns (list of (kind, detected, latency)), where detected means 'confirmed' at some time after the event began."""
    res = []
    for s in streams:
        if s["kind"] == "fall" and s["seen_after"] < 3.0:
            continue                                         # this camera never saw her after the event: no threshold could detect it
        cfg = FallConfig()
        for k, v in cfg_over.items():
            setattr(cfg, k, v)
        cfg.fs = float(s["fs"])
        det = FallDetector(cfg)
        t_conf = None
        for t, ob in zip(s["t"], s["obs"]):
            st = det.update(float(t), ob)
            if st == "confirmed" and t_conf is None:
                t_conf = float(t)
            if st == "confirmed" and det.t_confirmed is not None:
                t_conf = t_conf if t_conf is not None else float(t)
        fall = s["kind"] == "fall"
        ok = t_conf is not None and (t_conf >= s["t_event"] - 0.5 or not fall)
        res.append((fall, t_conf is not None and (t_conf >= s["t_event"] - 0.5 if fall else True), None if t_conf is None else t_conf - s["t_event"]))
    return res


def score(res):
    tp = sum(1 for f, d, _ in res if f and d)
    fn = sum(1 for f, d, _ in res if f and not d)
    fp = sum(1 for f, d, _ in res if not f and d)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    lat = np.mean([l for f, d, l in res if f and d and l is not None]) if tp else 99.0
    return (round(f1, 4), -fp, -lat), dict(tp=tp, fn=fn, fp=fp, f1=f1, latency=lat)


GRID = dict(
    down_z=[0.30, 0.35, 0.40, 0.45],
    min_peak_descent=[0.8, 1.0, 1.2, 1.5, 1.8],
    pitch_min_deg=[40.0, 50.0, 60.0],
    ar_min=[0.8, 1.0, 1.2],
    # quiet_s (the guide's 3 s immobility check) and lie_s (5 s found-lying rule) are NOT searched: shorter windows only buy latency on a small dev set and
    # would cost specificity, which sir's sheet puts first
    quiet_move_m=[0.20, 0.25, 0.35],
    min_drop_m=[0.30, 0.40, 0.50],
)


def fit(streams, label):
    print(f"[{label}] {len(streams)} streams from {len({s['id'] for s in streams})} trials", flush=True)
    base = asdict(FallConfig())
    cur = {}
    key0, info0 = score(replay(streams, cur))
    print(f"[{label}] defaults:", info0, flush=True)
    best_key = key0
    log = [dict(step="defaults", **info0)]
    for rnd in range(2):
        improved = False
        for name, vals in GRID.items():
            for v in vals:
                if cur.get(name, base[name]) == v:
                    continue
                trial = dict(cur, **{name: v})
                key, info = score(replay(streams, trial))
                if key > best_key:
                    best_key, cur, improved = key, trial, True
                    print(f"[{label}] round {rnd}: {name} -> {v}: {info}", flush=True)
                    log.append(dict(step=f"{name}={v}", **info))
        if not improved:
            break
    final_key, final = score(replay(streams, cur))
    return cur, final, info0, log


def main(split):
    streams = load_streams(split)
    out = dict(note="fitted on the dev split only (offline replay of recorded landmark streams); frozen before the test split")
    for cond, key in (("robot", "fall_config"), ("static", "static_fall_config")):
        cur, final, info0, log = fit([s for s in streams if s["cond"] == cond], cond)
        out[key] = cur
        out[f"{cond}_dev_result"] = final
        out[f"{cond}_defaults_result"] = info0
        out[f"{cond}_log"] = log
        print(f"[{cond}] frozen:", cur, final)
    path = os.path.join(ROOT, "outputs", "experiments", "frozen_config.json")
    json.dump(out, open(path, "w"), indent=1)
    print("->", path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
