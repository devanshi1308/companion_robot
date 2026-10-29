"""
Fall-detection pipeline entry point (the starter file's name and call, now wired to the real pipeline).

The starter generated scripted values.  This file runs nothing scripted: it reads the MEASURED trials of the seeded simulation
(MuJoCo + MediaPipe + src/vision/fall_detector.py) and prints the benchmark, or, with --run, re-runs the trials first.

    python src/fall_detection_kinematics.py                 print the measured benchmark (results/guide_robot_test)
    python src/fall_detection_kinematics.py --run 120       re-run N seeded test trials (about 1 min each with 5 workers), then print
    python src/fall_detection_kinematics.py --split dev     read another split from outputs/experiments/<split>

Fall rule actually used (src/vision/fall_detector.py, thresholds frozen from the dev split in results/guide_robot_test/frozen_config.json):
hip height drop from standing, peak descent speed, torso pitch, bounding-box aspect ratio and its rise rate, then a 3 s quiet window; a person
found lying and still for 5 s is the second path.  State machine (src/control/behavior.py): WATCH, FOLLOW, SEARCH, OBSERVE, SUSPECT, APPROACH,
CHECK_IN, ALERT.  Dispatch latency = t_emergency - t_floor (hip reaches the floor).
"""
import argparse
import csv
import json
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "vision"))
from fall_detector import FallConfig, FallDetector  # noqa: E402,F401  (the real detector, importable from here)

FROZEN = os.path.join(ROOT, "results", "guide_robot_test", "frozen_config.json")
CSV_OUT = os.path.join(ROOT, "analytics", "fall_triage_benchmark.csv")


def _tables(split):
    live = os.path.join(ROOT, "outputs", "experiments", split, "analysis", "tables", "all_trials.csv")
    kept = os.path.join(ROOT, "results", "guide_robot_test", "tables", "all_trials.csv")
    return live if os.path.exists(live) else kept


def _metrics(split):
    live = os.path.join(ROOT, "outputs", "experiments", split, "analysis", "metrics.json")
    kept = os.path.join(ROOT, "results", "guide_robot_test", "metrics.json")
    return json.load(open(live if os.path.exists(live) else kept))


def run_trials(n, split="test", workers=5):
    exp = os.path.join(ROOT, "src", "experiments")
    env = dict(os.environ, MUJOCO_GL=os.environ.get("MUJOCO_GL", "glfw"))
    seed = 2 if split == "test" else 1
    cfg = ["--cfg", FROZEN] if split == "test" else []
    subprocess.check_call([sys.executable, os.path.join(exp, "run_experiments.py"), split, str(n), str(seed), "--workers", str(workers)] + cfg, env=env)
    subprocess.check_call([sys.executable, os.path.join(exp, "analyze.py"), split], env=env)


def detect_fall_and_respond(split="test"):
    m = _metrics(split)
    df = pd.read_csv(_tables(split))
    rob = df[df["condition"] == "robot"]
    print("==================================================")
    print("GROUP 02 - ELDERLY FALL KINEMATICS & TRIAGE BENCHMARK (measured)")
    print("==================================================")
    cfg = json.load(open(FROZEN))["fall_config"] if os.path.exists(FROZEN) else {}
    print(f"Trials (robot condition): {len(rob)}   detector thresholds fitted on dev only: {cfg}")
    for level, key in (("alarm (heads-up to family)", "alarm_robot"), ("dispatch (family emergency + ambulance)", "dispatch_robot")):
        r = m[key]
        print(f"\n[{level}]  TP {r['TP']}  FN {r['FN']}  FP {r['FP']}  TN {r['TN']}")
        print(f"  Sensitivity (Recall): {100 * r['sensitivity']:.2f}%   95% CI {100 * r['sens_ci'][0]:.0f}-{100 * r['sens_ci'][1]:.0f}%")
        print(f"  Specificity (TNR):    {100 * r['specificity']:.2f}%   95% CI {100 * r['spec_ci'][0]:.0f}-{100 * r['spec_ci'][1]:.0f}%")
        print(f"  Precision (PPV):      {100 * r['precision']:.2f}%")
        print(f"  F1-Score:             {100 * r['f1']:.2f}%")
    L = m["lat_dispatch_robot"]
    print(f"\nDispatch latency, robot: mean {L['mean']:.1f} s (SE {L['se']:.1f}), median {L['median']:.1f} s, P95 {L['p95']:.1f} s (n = {L['n']})")
    print(f"Survival window budget kept for EMS transit at the mean: {360 - L['mean']:.1f} s (360 s window; the window itself is a teaching figure)")
    cols = ["id", "kind", "subtype", "conscious", "t_event", "t_floor", "t_heads_up", "t_emergency", "t_ambulance", "max_collision_force_N", "bytes_off_board_before_first_alert"]
    cols = [c for c in cols if c in rob.columns]
    rob[cols].to_csv(CSV_OUT, index=False)
    print(f"\n[OK] Measured per-trial table exported to: {CSV_OUT}")
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, default=None, help="re-run this many seeded trials first")
    ap.add_argument("--split", default="test")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    if a.run:
        run_trials(a.run, a.split, a.workers)
    detect_fall_and_respond(a.split)
