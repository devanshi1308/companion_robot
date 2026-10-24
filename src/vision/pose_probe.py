"""
Feasibility probe: can real MediaPipe BlazePose find the simulated woman on camera frames?

Renders her from a robot-height camera (1.15 m, 2.2 m away) from three sides at six moments of the
walk and fall, runs the tracker, prints the detection table and saves a montage.

Run:  MUJOCO_GL=glfw python src/vision/pose_probe.py
"""
import os
import sys

import mujoco
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import walk_and_fall as W  # noqa: E402
from blazepose_tracker import PoseTracker  # noqa: E402

CAM_H, DIST = 1.15, 2.2
VIEWS = {"behind": 270.0, "side": 180.0, "front": 90.0}    # camera azimuth (deg); 0 would sit outside the west wall
MOMENTS = [("walking", -1.0), ("tripping", 0.2), ("falling", 0.45), ("hit floor", 0.8), ("lying 1.5s", 1.5), ("lying 4s", 4.0)]


def main():
    m = mujoco.MjModel.from_xml_path(W.SCENE)
    d = mujoco.MjData(m)
    w = W.Walker(m, 0.8)
    t_fall = w.default_trip_time()
    vac = W.Vacuum(m, 0.25)
    tracker = PoseTracker()
    r = mujoco.Renderer(m, 480, 640)

    def project_gt(rend):
        """Project the 33 ground-truth landmark sites into the image of the last rendered frame."""
        c = rend.scene.camera[0]
        pos, fwd, up = np.array(c.pos), np.array(c.forward), np.array(c.up)
        right = np.cross(fwd, up)
        f = 0.5 * 480 / np.tan(np.radians(m.vis.global_.fovy) / 2)
        out = []
        for i in range(33):
            sid = [j for j in range(m.nsite) if m.site(j).name.startswith(f"lm_{i:02d}_")][0]
            v = d.site_xpos[sid] - pos
            z = v @ fwd
            out.append([320 + f * (v @ right) / z, 240 - f * (v @ up) / z])
        return np.array(out)

    def snapshot(view_az, label_row):
        pel = d.xpos[m.body("pelvis").id].copy()
        look = np.array([pel[0], pel[1], max(0.6 * pel[2], 0.3)])
        el = -np.degrees(np.arctan2(CAM_H - look[2], DIST))
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = look
        cam.distance = float(np.hypot(DIST, CAM_H - look[2]))
        cam.azimuth, cam.elevation = view_az, el
        opt = mujoco.MjvOption()
        opt.geomgroup[2] = 0
        r.update_scene(d, camera=cam, scene_option=opt)
        img = r.render().copy()
        return img, project_gt(r)

    # states: walking before the trip, then physics after release
    frames = {}
    for label, dt_rel in MOMENTS:
        if dt_rel < 0:
            d.qpos[:] = w.pose_at(t_fall + dt_rel)
            vac.update(d, t_fall + dt_rel)
            mujoco.mj_forward(m, d)
            frames[label] = [snapshot(az, label) for az in VIEWS.values()]
    q = w.pose_at(t_fall)
    d.qpos[:] = q
    mujoco.mj_forward(m, d)
    q_rel = W.release(m, d, w, t_fall, 0.8, 1.9, 1.0)
    hold = W.ReflexHold(m, d, 0.45)
    hold.target = W.make_target(m, q_rel, 1.0, 70.0, 1.0)
    marks = {label: int(dt / m.opt.timestep) for label, dt in MOMENTS if dt >= 0}
    for step in range(max(marks.values()) + 1):
        hold.apply(d, step * m.opt.timestep)
        vac.update(d, t_fall + step * m.opt.timestep)
        mujoco.mj_step(m, d)
        for label, s in marks.items():
            if step == s:
                frames[label] = [snapshot(az, label) for az in VIEWS.values()]

    rows, tiles, errs = [], [], []
    print(f"{'moment':12s}" + "".join(f"{v:>16s}" for v in VIEWS))
    for label, _ in MOMENTS:
        line, row_tiles = f"{label:12s}", []
        for vname, (img, gt) in zip(VIEWS, frames[label]):
            det = tracker.detect(img)
            im = Image.fromarray(img)
            dr = ImageDraw.Draw(im)
            if det is not None:
                for (x, y, _), v in zip(det["image"], det["vis"]):
                    if v > 0.5:
                        dr.ellipse([x * 640 - 3, y * 480 - 3, x * 640 + 3, y * 480 + 3], fill=(255, 40, 40))
                pred = det["image"][:, :2] * np.array([640, 480])
                height = max(np.ptp(gt[:, 0]), np.ptp(gt[:, 1]))             # person size in pixels
                err = np.linalg.norm(pred - gt, axis=1) / height
                ok = det["vis"] > 0.5
                errs.append(err[ok])
                line += f"{'err ' + format(100 * np.median(err[ok]), '.1f') + '% (' + str(int(ok.sum())) + ')':>16s}"
            else:
                line += f"{'NOT FOUND':>16s}"
            dr.text((6, 6), f"{label} / {vname}", fill=(255, 255, 255))
            row_tiles.append(np.array(im.resize((320, 240))))
        print(line)
        tiles.append(np.hstack(row_tiles))
    allerr = np.concatenate(errs)
    print(f"\nfound in {len(errs)} of {len(MOMENTS) * len(VIEWS)} views | landmark error vs ground truth (as % of person size): "
          f"median {100 * np.median(allerr):.1f}%, 90th percentile {100 * np.percentile(allerr, 90):.1f}%  ({len(allerr)} landmarks)")
    os.makedirs(os.path.join(ROOT, "..", "outputs"), exist_ok=True)
    out = os.path.join(ROOT, "..", "outputs", "mediapipe_probe.png")
    Image.fromarray(np.vstack(tiles)).save(out)
    print("montage ->", os.path.relpath(out, os.path.join(ROOT, "..")))


if __name__ == "__main__":
    main()
