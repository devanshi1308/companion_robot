"""
Threshold sensitivity of the fall detector (DEV split only).

    python src/experiments/threshold_sensitivity.py dev

Question answered: is the detector over-tuned? We move ONE threshold at a time, all others stay at the FallConfig defaults, and
replay the recorded dev landmark streams (same replay rule as fit_detector.py). For each value we report

    sensitivity = detected falls / falls the camera could see   (a fall stream counts only if the camera saw her >= 3 s after the event began)
    specificity = activity streams with NO 'confirmed' / all activity streams

Swept thresholds: ar_min (bounding box aspect ratio, guide 1.2) and pitch_min_deg (torso angle from vertical, guide 60).
Output: docs/figures/threshold_sensitivity.png and docs/figures/threshold_sensitivity.csv
The TEST split is never read here.  Streams are replayed one at a time to keep memory low.
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src", "vision"))
from fall_detector import FallConfig, FallDetector  # noqa: E402
from fit_detector import FakeObs  # noqa: E402

SWEEPS = dict(
    ar_min=[0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8],
    pitch_min_deg=[30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
)
FIG_DIR = os.path.join(ROOT, "docs", "figures")


def detected(z, sp, over):
    """Replay one recorded stream with config overrides; True if the detector reached 'confirmed' (after the event for falls)."""
    cfg = FallConfig()
    for k, v in over.items():
        setattr(cfg, k, v)
    dt = float(np.median(np.diff(z["t"])))
    cfg.fs = 1.0 / dt
    det = FallDetector(cfg)
    t_ev = sp["clip_meta"]["t_event"]
    fall = sp["spec"]["kind"] == "fall"
    for i in range(len(z["t"])):
        ob = None if z["n_valid"][i] == 0 else FakeObs(z["world"][i].astype(float), z["valid"][i], z["vis"][i], z["aspect"][i], z["n_valid"][i])
        t = float(z["t"][i])
        if det.update(t, ob) == "confirmed":
            return (t >= t_ev - 0.5) if fall else True
    return False


def run(split):
    base = os.path.join(ROOT, "outputs", "experiments", split)
    conds = {"robot": ["features_robot.npz"],
             "static": ["features_static_cam.npz", "features_static_hall_w.npz", "features_static_hall_e.npz", "features_static_bed.npz"]}
    grid = [(name, v) for name, vals in SWEEPS.items() for v in vals]
    # counts[cond][(name, v)] = [tp, n_fall, tn, n_act]
    counts = {c: {g: [0, 0, 0, 0] for g in grid} for c in conds}
    for tid in sorted(os.listdir(base)):
        sp_path = os.path.join(base, tid, "spec.json")
        if not os.path.exists(os.path.join(base, tid, "result.json")):
            continue
        sp = json.load(open(sp_path))
        fall = sp["spec"]["kind"] == "fall"
        t_ev = sp["clip_meta"]["t_event"]
        for cond, files in conds.items():
            for fn in files:
                p = os.path.join(base, tid, fn)
                if not os.path.exists(p):
                    continue
                z = dict(np.load(p))
                dt = float(np.median(np.diff(z["t"])))
                seen = float(((z["t"] > t_ev) & (z["n_valid"] >= 12)).sum() * dt)
                if fall and seen < 3.0:
                    continue                      # camera never saw her after the event: no threshold could detect it
                for g in grid:
                    d = detected(z, sp, {g[0]: g[1]})
                    c = counts[cond][g]
                    if fall:
                        c[1] += 1
                        c[0] += int(d)
                    else:
                        c[3] += 1
                        c[2] += int(not d)
        print(tid, "done", flush=True)
    rows = []
    for cond in conds:
        for (name, v), (tp, nf, tn, na) in counts[cond].items():
            rows.append(dict(condition=cond, threshold=name, value=v, falls=nf, detected=tp, sensitivity=round(tp / nf, 3) if nf else None,
                             activities=na, no_false_alarm=tn, specificity=round(tn / na, 3) if na else None))
    return rows


def plot(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    defaults = dict(ar_min=FallConfig().ar_min, pitch_min_deg=FallConfig().pitch_min_deg)
    guide = dict(ar_min=1.2, pitch_min_deg=60.0)
    labels = dict(ar_min="Bounding-box aspect ratio threshold (ar_min)", pitch_min_deg="Torso angle threshold (pitch_min_deg, degrees)")
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True)
    for r_i, cond in enumerate(("robot", "static")):
        for c_i, name in enumerate(SWEEPS):
            ax = axes[r_i][c_i]
            sel = sorted([r for r in rows if r["condition"] == cond and r["threshold"] == name], key=lambda r: r["value"])
            x = [r["value"] for r in sel]
            ax.plot(x, [r["sensitivity"] for r in sel], "o-", label="sensitivity")
            ax.plot(x, [r["specificity"] for r in sel], "s--", label="specificity")
            ax.axvline(defaults[name], color="grey", ls=":", label="code default")
            ax.axvline(guide[name], color="green", ls=":", label="course guide value")
            ax.set_ylim(-0.02, 1.05)
            ax.set_xlabel(labels[name])
            ax.set_title(("Robot camera" if cond == "robot" else "Fixed cameras") + " (dev split)")
            ax.grid(alpha=0.3)
            if r_i == 0 and c_i == 0:
                ax.legend(fontsize=8, loc="lower left")
        axes[r_i][0].set_ylabel("score")
    fig.suptitle("Threshold sensitivity, one threshold moved at a time, others at defaults")
    fig.tight_layout()
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, "threshold_sensitivity.png"), dpi=150)


def main(split):
    if split != "dev":
        raise SystemExit("this script is for the dev split only")
    rows = run(split)
    os.makedirs(FIG_DIR, exist_ok=True)
    with open(os.path.join(FIG_DIR, "threshold_sensitivity.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    plot(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
