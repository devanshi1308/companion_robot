"""Record every clip of a split and report problems: her body passing through furniture/walls, no floor contact for falls, durations.
Run: python src/experiments/check_clips.py dev 40 1"""
import os, sys, time
import numpy as np, mujoco
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenarios as SC, trial_setup as TS, motions as M, human_motion as HM


def main(split, n, seed0, only=None):
    specs = SC.make_specs(split, n, seed0)
    cache = os.path.join(TS.ROOT, "outputs", "experiments", "clips")
    m0 = TS.load_model(TS.SCENE_HUMAN, specs[0], [])
    rig = HM.Rig(m0)
    d = mujoco.MjData(m0)
    sv = M._sites(m0)
    rows = []
    for sp in specs:
        if only and sp["subtype"] != only:
            continue
        t0 = time.time()
        clip = TS.clip_for(sp, cache)
        worst, tw = 0.0, 0
        for t in np.arange(0, clip.t_end, 0.1):
            d.qpos[rig.sl_q] = clip.at(t)
            mujoco.mj_forward(m0, d)
            p = TS.penetration(m0, d)
            if p > worst:
                worst, tw = p, t
        hz = [M.hip_height(rig, clip.at(t), sv) for t in np.arange(0, clip.t_end, 0.1)]
        print(f"{sp['id']} {sp['subtype']:16s} {sp['route']:18s} dur {clip.t_end:5.1f} t_event {clip.meta['t_event']:5.1f} t_floor {clip.meta['t_floor']} min_hip {min(hz):.2f} max_pen {worst*100:4.1f} cm at {tw:4.1f}  ({time.time()-t0:.1f}s)", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else None)
