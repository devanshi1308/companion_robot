"""Summarise the 500 Hz motion-validation runs (run_motion_validation.py): tracking RMSE on the approach path and control effort.

  python src/experiments/analyze_motion.py   ->  results/motion_validation/{summary.json, per_trial.csv, tracking_example.png}
"""
import glob
import json
import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "results", "motion_validation"); os.makedirs(OUT, exist_ok=True)
STATES = ["WATCH", "FOLLOW", "SEARCH", "OBSERVE", "SUSPECT", "APPROACH", "CHECK_IN", "ALERT"]
rows = []
for f in sorted(glob.glob(os.path.join(ROOT, "outputs", "experiments", "motion", "*", "fast_log.npz"))):
    z = np.load(f); a = z["data"]; tid = f.split("/")[-2]
    t, state, dist = a[:, 0], a[:, 10].astype(int), a[:, 11].copy(); dist[np.abs(a[:, 12]) <= 0.05] = np.nan      # only while the follower is really driving
    dt = np.median(np.diff(t)); tau2 = (a[:, 6:10] ** 2).sum(1)
    def rmse(mask):
        v = dist[mask & np.isfinite(dist)]
        return (float(np.sqrt((v ** 2).mean())) if v.size > 50 else np.nan, int(v.size))
    ap_r, ap_n = rmse(state == STATES.index("APPROACH")); fo_r, fo_n = rmse(state == STATES.index("FOLLOW")); al_r, al_n = rmse(np.ones_like(state, bool))
    rows.append(dict(id=tid, rate_hz=1 / dt, duration_s=float(t[-1] - t[0]), rmse_approach=ap_r, n_approach=ap_n, rmse_follow=fo_r, n_follow=fo_n, rmse_all_paths=al_r, n_all=al_n,
                     effort_total=float((tau2 * dt).sum()), effort_approach=float((tau2[state == STATES.index("APPROACH")] * dt).sum()), tau_wheel_max=float(np.abs(a[:, 6:8]).max()), sat_frac=float((np.abs(a[:, 6:8]) >= 2.99).mean())))
import csv
with open(os.path.join(OUT, "per_trial.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def stat(key):
    v = np.array([r[key] for r in rows], float); v = v[np.isfinite(v)]
    return dict(n=int(v.size), mean=float(v.mean()) if v.size else None, sd=float(v.std(ddof=1)) if v.size > 1 else None, median=float(np.median(v)) if v.size else None)
summ = dict(trials=len(rows), logging_rate_hz=float(np.median([r["rate_hz"] for r in rows])), tracking_rmse_approach_m=stat("rmse_approach"), tracking_rmse_follow_m=stat("rmse_follow"), tracking_rmse_all_paths_m=stat("rmse_all_paths"),
            control_effort_total_Nm2s=stat("effort_total"), control_effort_approach_Nm2s=stat("effort_approach"), wheel_torque_max_Nm=stat("tau_wheel_max"), wheel_torque_saturated_fraction=stat("sat_frac"))
json.dump(summ, open(os.path.join(OUT, "summary.json"), "w"), indent=1); print(json.dumps(summ, indent=1))
# example: planned vs actual
best = max((r for r in rows if r["n_approach"] > 400 and r["rmse_approach"] < 0.15), key=lambda r: r["n_approach"], default=None)
if best:
    z = np.load(os.path.join(ROOT, "outputs", "experiments", "motion", best["id"], "fast_log.npz")); a = z["data"]; st = a[:, 10].astype(int)
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), dpi=180)
    m = st == STATES.index("APPROACH")
    ax[0].plot(a[:, 1], a[:, 2], color="#bbb", lw=0.6, label="whole run"); ax[0].plot(a[m, 1], a[m, 2], color="#2b5fd9", lw=1.2, label="approach (actual)"); ax[0].set_aspect("equal"); ax[0].legend(fontsize=6); ax[0].set_title(f"{best['id']}: robot path", fontsize=8)
    dd = a[:, 11].copy(); dd[np.abs(a[:, 12]) <= 0.05] = np.nan; ax[1].plot(a[m, 0], dd[m] * 100, color="#d6453d", lw=0.8); ax[1].set_xlabel("time (s)", fontsize=7); ax[1].set_ylabel("distance to planned path (cm)", fontsize=7); ax[1].set_title("tracking error on the approach path (500 Hz)", fontsize=8)
    for x in ax: x.tick_params(labelsize=6)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "tracking_example.png")); print("example", best["id"])
