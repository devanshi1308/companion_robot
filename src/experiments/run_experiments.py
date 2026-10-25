"""
Run a whole split of trials in parallel (one process per trial, MediaPipe and MuJoCo renderers are not shared).

    python src/experiments/run_experiments.py dev  40 1    --workers 4
    python src/experiments/run_experiments.py test 120 2   --workers 4 --cfg outputs/experiments/frozen_config.json

Trials whose result.json already exists are skipped, so an interrupted run can simply be started again.
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


def _work(args):
    spec, out_root, cfg, conds = args
    os.environ.setdefault("MUJOCO_GL", "glfw")
    import run_trial as RT
    t0 = time.time()
    try:
        RT.run_one(spec, out_root, cfg, conds)
        return spec["id"], None, time.time() - t0
    except Exception:
        return spec["id"], traceback.format_exc(), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("n", type=int)
    ap.add_argument("seed0", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cfg", default=None, help="JSON file with {'fall_config': {...}} overriding the detector thresholds")
    ap.add_argument("--conditions", default="robot,static,static4")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", default=None, help="comma-separated trial indices")
    a = ap.parse_args()
    import scenarios as SC
    specs = SC.make_specs(a.split, a.n, a.seed0)
    if a.only:
        keep = {int(x) for x in a.only.split(",")}
        specs = [s for i, s in enumerate(specs) if i in keep]
    out_root = os.path.join(ROOT, "outputs", "experiments", a.split)
    os.makedirs(out_root, exist_ok=True)
    cfg = json.load(open(a.cfg)) if a.cfg else None
    todo = [s for s in specs if not os.path.exists(os.path.join(out_root, s["id"], "result.json"))]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(specs)} trials in the split, {len(todo)} to run with {a.workers} workers", flush=True)
    t0 = time.time()
    done = 0
    log = open(os.path.join(out_root, "progress.log"), "a")
    with ProcessPoolExecutor(a.workers, mp_context=mp.get_context("spawn")) as ex:
        futs = [ex.submit(_work, (s, out_root, cfg, tuple(a.conditions.split(",")))) for s in todo]
        for f in as_completed(futs):
            tid, err, dt = f.result()
            done += 1
            msg = f"[{done}/{len(todo)}] {tid} {'ERROR' if err else 'ok'} {dt:.0f}s (elapsed {(time.time() - t0) / 60:.1f} min)"
            print(msg, flush=True)
            log.write(msg + "\n")
            if err:
                log.write(err + "\n")
                print(err, flush=True)
            log.flush()


if __name__ == "__main__":
    main()
