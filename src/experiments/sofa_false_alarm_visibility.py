"""
Why does the detector raise a heads-up on sofa sits?  Is it occlusion?  (DEV split only.)

    python src/experiments/sofa_false_alarm_visibility.py dev

Hypothesis tested: the false alarm comes from low landmark visibility (the sofa hides her hips, so the 3D hip height is wrong).
For every sofa-sit trial (abrupt and slow) the robot camera's recorded landmarks are compared with the simulator's ground truth:
  - estimated hip height (det_hip_z in the telemetry) against the TRUE hip height (human_hip_z)
  - hip/shoulder landmark visibility score and number of valid landmarks (features_robot.npz)
  - the moment the detector raised 'suspect' (impact), from the detector log
Outputs: docs/figures/sofa_false_alarm_visibility.png and docs/figures/sofa_false_alarm_visibility.csv
The TEST split is never read.
"""
import csv
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src", "vision"))
from fall_detector import FallConfig, FallDetector  # noqa: E402
from fit_detector import FakeObs  # noqa: E402

FIG_DIR = os.path.join(ROOT, "docs", "figures")
HIP, SHOULDER = [23, 24], [11, 12]
GROSS_ERR_M = 0.40            # estimate this far below the true hip height counts as a gross error


def replay(z, sp):
    cfg = FallConfig()
    cfg.fs = 1.0 / float(np.median(np.diff(z["t"])))
    det = FallDetector(cfg)
    t_suspect = None
    for i in range(len(z["t"])):
        ob = None if z["n_valid"][i] == 0 else FakeObs(z["world"][i].astype(float), z["valid"][i], z["vis"][i], z["aspect"][i], z["n_valid"][i])
        det.update(float(z["t"][i]), ob)
        if t_suspect is None and det.log and "impact" in det.log[0][1]:
            t_suspect = det.log[0][0]
    confirmed = any("confirmed" in x for _, x in det.log)
    return t_suspect, confirmed


def analyse(base, tid):
    sp = json.load(open(os.path.join(base, tid, "spec.json")))
    z = dict(np.load(os.path.join(base, tid, "features_robot.npz")))
    tel = pd.read_csv(os.path.join(base, tid, "telemetry_robot.csv"))
    t_sus, confirmed = replay(z, sp)
    hip_vis = z["vis"][:, HIP].mean(1)
    sh_vis = z["vis"][:, SHOULDER].mean(1)
    seen = z["n_valid"] > 0
    t0 = sp["clip_meta"]["t_event"]
    win = (z["t"] > t0 - 3) & (z["t"] < t0 + 6)
    # gross hip-height errors, matched in time with the telemetry (0.05 s steps)
    m = tel.dropna(subset=["det_hip_z", "human_hip_z"])
    m = m[(m.t > t0 - 3) & (m.t < t0 + 6)]
    gross = (m.human_hip_z - m.det_hip_z) > GROSS_ERR_M
    idx = np.searchsorted(z["t"], m.t.values).clip(0, len(z["t"]) - 1)
    sel = gross.values & seen[idx]                 # only frames where a person was actually found (otherwise the score is 0 by default)
    vis_at_gross = float(hip_vis[idx][sel].mean()) if sel.any() else float("nan")
    return dict(trial=tid, subtype=sp["spec"]["subtype"], t_event=round(t0, 1), false_alarm=bool(confirmed),
                t_first_suspect=None if t_sus is None else round(t_sus, 1),
                frames_with_no_person=round(float((~seen[win]).mean()), 2),
                mean_hip_vis_when_seen=round(float(hip_vis[win & seen].mean()), 2) if (win & seen).any() else None,
                mean_shoulder_vis_when_seen=round(float(sh_vis[win & seen].mean()), 2) if (win & seen).any() else None,
                gross_error_samples=int(gross.sum()), mean_hip_vis_at_gross_error=None if np.isnan(vis_at_gross) else round(vis_at_gross, 2)), z, tel, sp, t_sus


def plot(items):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(items), 2, figsize=(11, 3.0 * len(items)), squeeze=False)
    for r, (row, z, tel, sp, t_sus) in enumerate(items):
        ax = axes[r][0]
        ax.plot(tel.t, tel.human_hip_z, label="true hip height (simulator)", color="tab:green")
        ax.plot(tel.t, tel.det_hip_z, label="hip height the detector saw", color="tab:red", lw=1)
        ax.axvline(row["t_event"], color="grey", ls=":", label="start of sit")
        if t_sus is not None:
            ax.axvline(t_sus, color="red", ls="--", label="detector says 'fall'")
        ax.set_ylabel("hip height (m)")
        ax.set_title(f"{row['trial']} ({row['subtype']}), false alarm: {'YES' if row['false_alarm'] else 'no'}", fontsize=10)
        ax.set_xlim(max(0, row["t_event"] - 4), row["t_event"] + 8)
        ax.grid(alpha=0.3)
        ax2 = axes[r][1]
        ax2.plot(z["t"], z["vis"][:, HIP].mean(1), label="hip landmark visibility", color="tab:blue")
        ax2.plot(z["t"], z["vis"][:, SHOULDER].mean(1), label="shoulder landmark visibility", color="tab:orange", lw=1)
        ax2.fill_between(z["t"], 0, (z["n_valid"] == 0).astype(float), color="grey", alpha=0.3, step="mid", label="no person found")
        ax2.axvline(row["t_event"], color="grey", ls=":")
        if t_sus is not None:
            ax2.axvline(t_sus, color="red", ls="--")
        ax2.set_ylim(-0.02, 1.05)
        ax2.set_xlim(max(0, row["t_event"] - 4), row["t_event"] + 8)
        ax2.set_ylabel("visibility score (0-1)")
        ax2.grid(alpha=0.3)
        if r == 0:
            ax.legend(fontsize=7, loc="lower left")
            ax2.legend(fontsize=7, loc="lower left")
    for ax in (axes[-1][0], axes[-1][1]):
        ax.set_xlabel("time (s)")
    fig.suptitle("Sofa sits, robot camera, dev split: what the detector saw versus what happened", fontsize=11)
    fig.tight_layout()
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, "sofa_false_alarm_visibility.png"), dpi=150)


def main(split):
    if split != "dev":
        raise SystemExit("this script is for the dev split only")
    base = os.path.join(ROOT, "outputs", "experiments", split)
    items = []
    for tid in sorted(d for d in os.listdir(base) if d.startswith("dev_")):
        sp = json.load(open(os.path.join(base, tid, "spec.json")))
        if sp["spec"].get("subtype", "").startswith("sit_sofa"):
            items.append(analyse(base, tid))
    rows = [i[0] for i in items]
    os.makedirs(FIG_DIR, exist_ok=True)
    with open(os.path.join(FIG_DIR, "sofa_false_alarm_visibility.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    # plot the false-alarm trials first, then one trial that did not alarm, so the contrast is visible
    shown = [i for i in items if i[0]["false_alarm"]] + [i for i in items if not i[0]["false_alarm"] and i[0]["frames_with_no_person"] < 0.8][:2]
    plot(shown)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
