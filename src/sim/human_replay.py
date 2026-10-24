"""
Record her scripted walk and physical fall once, then replay it frame by frame.

Her motion does not depend on the robot, so a recording can be replayed in any scene that contains her.
Used by the perception tests and (later) by the dataset generator.

    ts, qpos, t_fall = record(model)          # qpos: (n, 91) her joints only
    w = Walker(model); apply_frame(d, w, qpos[i])
"""
import numpy as np
import mujoco

import apartment_layout as L  # noqa: F401
import walk_and_fall as W


def record(m, speed=0.8, after=6.0, fps=30, trip_omega=1.9, direction=1.0, tau=0.45, brace=70.0, straight=1.0, vacuum_speed=0.25):
    d = mujoco.MjData(m)
    w = W.Walker(m, speed)
    vac = W.Vacuum(m, vacuum_speed)
    t_fall = w.default_trip_time()
    dt = 1.0 / fps
    ts, rec = [], []
    t = 0.0
    while t < t_fall:
        w.apply(d, t)
        vac.update(d, t)
        mujoco.mj_forward(m, d)
        ts.append(t)
        rec.append(d.qpos[w.sl_q].copy())
        t += dt
    q_rel = W.release(m, d, w, t_fall, speed, trip_omega, direction)
    hold = W.ReflexHold(m, d, tau)
    hold.target = W.make_target(m, q_rel, direction, brace, straight)
    every = int(round(dt / m.opt.timestep))
    for k in range(int(after / m.opt.timestep)):
        hold.apply(d, k * m.opt.timestep)
        vac.update(d, t_fall + k * m.opt.timestep)
        mujoco.mj_step(m, d)
        if k % every == 0:
            ts.append(t_fall + k * m.opt.timestep)
            rec.append(d.qpos[w.sl_q].copy())
    return np.array(ts), np.array(rec), t_fall


def apply_frame(d, walker, q_human):
    d.qpos[walker.sl_q] = q_human
    d.qvel[walker.sl_v] = 0.0
