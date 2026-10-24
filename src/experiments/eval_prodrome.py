"""
Evaluate the pre-collapse (prodrome) cue monitor on the recorded landmark streams (robot camera and the fixed cameras, whichever sees her first).

    python src/experiments/eval_prodrome.py dev            fit the cue thresholds on dev  ->  outputs/experiments/frozen_prodrome.json
    python src/experiments/eval_prodrome.py test           apply the frozen thresholds to test

Score: for a cardiac trial the monitor must flag BEFORE the collapse (hip reaches the floor); a flag in any other trial (other falls, daily
activities) is a false flag. Lead time = collapse time minus first flag. These cues are scripted in the simulation, so this measures whether a
landmark-window monitor can see a scripted behaviour, not how patients behave.
"""
import itertools
import json
import os
import sys

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "vision"))
import prodrome as PR  # noqa: E402

STREAMS = ("features_robot.npz", "features_static_cam.npz", "features_static_hall_w.npz", "features_static_hall_e.npz", "features_static_bed.npz")


def trials(split):
    base = os.path.join(ROOT, "outputs", "experiments", split)
    out = []
    for tid in sorted(os.listdir(base)):
        fn = os.path.join(base, tid, "spec.json")
        if not os.path.exists(fn):
            continue
        sp = json.load(open(fn))
        out.append((tid, sp["spec"]["subtype"], sp["clip_meta"].get("t_floor"), [os.path.join(base, tid, s) for s in STREAMS if os.path.exists(os.path.join(base, tid, s))]))
    return out


_cache = {}


def first_flag(paths, t_end, cfg):
    best = None
    for p in paths:
        key = (p, tuple(sorted(cfg.items())))
        if key not in _cache:
            _cache[key] = PR.replay(p, **cfg)
        first, hist = _cache[key]
        if first is not None and (best is None or first < best):
            best = first
    return best


def evaluate(split, cfg):
    rows = []
    for tid, sub, t_floor, paths in trials(split):
        t_ff = first_flag(paths, None, cfg)
        rows.append((tid, sub, t_floor, t_ff))
    card = [r for r in rows if r[1] == "cardiac"]
    other = [r for r in rows if r[1] != "cardiac"]
    hit = [r for r in card if r[3] is not None and r[3] < r[2]]
    fp = [r for r in other if r[3] is not None]
    lead = [r[2] - r[3] for r in hit]
    return dict(n_cardiac=len(card), flagged_before_collapse=len(hit), n_other=len(other), false_flags=len(fp), false_flag_trials=[r[0] + ":" + r[1] for r in fp],
                median_lead_s=float(np.median(lead)) if lead else None, min_lead_s=float(min(lead)) if lead else None), rows


def fit(split):
    grid = dict(CHEST_R=[0.25, 0.35], CHEST_FRAC=[0.4, 0.6], HUNCH_DEG=[8.0, 14.0])
    best = (-1e9, None, None)
    for vals in itertools.product(*grid.values()):
        cfg = dict(zip(grid, vals))
        res, _ = evaluate(split, cfg)
        score = res["flagged_before_collapse"] - 2.0 * res["false_flags"]
        if score > best[0]:
            best = (score, cfg, res)
    return best[1], best[2]


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    path = os.path.join(ROOT, "outputs", "experiments", "frozen_prodrome.json")
    if split == "dev":
        cfg, res = fit("dev")
        json.dump(dict(prodrome_config=cfg, dev_result=res, note="fitted on dev only"), open(path, "w"), indent=1)
        print("frozen:", cfg)
    else:
        cfg = json.load(open(path))["prodrome_config"]
        res, rows = evaluate(split, cfg)
        json.dump(dict(prodrome_config=cfg, result=res, rows=rows), open(os.path.join(ROOT, "outputs", "experiments", split, "analysis", "prodrome.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
