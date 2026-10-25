"""How often does the pose tracker 'find a person' when nobody is there?  She is moved out of the flat; the fixed camera and the robot's
head camera (at 200 random poses, random pan and tilt) are run through MediaPipe.  Run: python src/experiments/audit_phantoms.py"""
import os, sys
import numpy as np, mujoco
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trial_setup as TS, run_trial as RT
from person_observer import PersonObserver
import robot_spec as S
from robot_interface import RobotInterface

def main():
    spec = dict(id="audit", friction_scale=1.0)
    m = TS.load_model(TS.SCENE_FULL, spec, [])
    d = mujoco.MjData(m)
    import walk_and_fall as W
    w = W.Walker(m, 0.8)
    q = w.pose_at(0.0)[w.sl_q].copy(); q[:3] = [0, 0, -20]          # she is below the floor, out of every view
    rb = RobotInterface(m, d)
    ren = mujoco.Renderer(m, 480, 640)
    tr = RT.tracker()
    cam = m.camera("static_cam").id
    obs_s = PersonObserver(tr, fovy_deg=float(m.cam_fovy[cam]))
    obs_r = PersonObserver(tr)
    d.qpos[w.sl_q] = q
    mujoco.mj_forward(m, d)
    ren.update_scene(d, camera=cam); rgb = ren.render().copy()
    det = tr.detect(rgb)
    print("static camera, empty flat:", "PHANTOM" if det is not None else "nothing")
    if det is not None:
        ren.enable_depth_rendering(); ren.update_scene(d, camera=cam); dep = ren.render().copy(); ren.disable_depth_rendering()
        o = obs_s.observe(rgb, dep, None, 0, 0, cam=(d.cam_xpos[cam].copy(), d.cam_xmat[cam].reshape(3, 3).copy()))
        print("  hip at", None if o is None or o.hip is None else np.round(o.hip, 2), "landmarks", None if o is None else o.n_valid)
    rng = np.random.default_rng(0)
    hits = []
    for k in range(200):
        x, y = rng.uniform(-3.2, 3.2), rng.uniform(-2.8, 2.8)
        yaw = rng.uniform(-np.pi, np.pi)
        d.qpos[rb.qadr:rb.qadr + 7] = [x, y, S.WHEEL_R, np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
        pan, tilt = rng.uniform(-60, 60), rng.uniform(-40, 15)                     # the camera nods and pans while searching
        rb.set_neck(pan, tilt)
        for _ in range(250):
            mujoco.mj_step(m, d)
        d.qpos[w.sl_q] = q
        mujoco.mj_forward(m, d)
        rgb, dep = rb.grab(ren)
        o = obs_r.observe(rgb, dep, np.array([x, y, yaw]), pan, tilt)
        if o is not None and o.hip is not None and o.n_valid >= 12:
            hits.append((k, round(x, 1), round(y, 1), np.round(o.hip, 2), o.n_valid))
    print(f"robot camera: phantom person in {len(hits)} of 200 random views")
    for h in hits: print("  ", h)

main()
