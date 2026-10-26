"""
From a camera image to where her body is in the room.

  obs = PersonObserver(tracker).observe(rgb, depth, base_pose, pan_deg, tilt_deg)

  1. BlazePose finds 33 landmarks in the image (pixels).
  2. The depth image gives the distance along the optical axis at each landmark.
  3. The robot's own pose estimate (wheel odometry) and neck angles place the camera in the room, so each
     landmark becomes a 3D world point. Everything the robot knows comes from its own sensors; no simulator
     ground truth is used here.

A landmark at the body's edge could read the wall behind her, so the depth is taken as the 10th percentile of a
5 x 5 window (the nearest surface); a landmark whose depth is still far from the median depth of the visible
landmarks is moved to that median depth.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "robot"))
import robot_spec as S  # noqa: E402

HEAD_CAM = np.array([S.CAM_X, 0.0, 0.04 + S.HEAD_H / 2 - S.BEZEL_TOP / 2])   # camera in the head frame
TILT_REL_Z = S.TILT_Z - S.WHEEL_R                                                          # tilt axis above the body origin
R_HEAD_CAM = np.array([[0.0, 0.0, -1.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])               # columns: camera x (right), y (up), z (back) in the head frame

LM = dict(nose=0, l_shoulder=11, r_shoulder=12, l_wrist=15, r_wrist=16, l_hip=23, r_hip=24, l_knee=25, r_knee=26, l_ankle=27, r_ankle=28)


def rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1.0, 0], [-s, 0, c]])


def camera_pose(base_pose, pan_deg, tilt_deg):
    """World position and rotation (camera -> world) of the head camera. base_pose = (x, y, yaw) of the wheel axle."""
    x, y, yaw = base_pose
    r_head = rz(yaw + np.radians(pan_deg)) @ ry(-np.radians(tilt_deg))      # tilt axis is -y: positive tilt = looking up
    origin = np.array([x, y, S.WHEEL_R + TILT_REL_Z])
    return origin + r_head @ HEAD_CAM, r_head @ R_HEAD_CAM


class Observation:
    """What the robot knows about her at one instant."""

    def __init__(self, world, valid, vis, pix, shape):
        self.world, self.valid, self.vis, self.pix = world, valid, vis, pix
        self.h, self.w = shape
        ok = valid & (vis > 0.3)
        self.n_valid = int(ok.sum())
        pts = pix[ok]
        if len(pts):
            bx, by, bw_, bh_ = cv2.boundingRect(pts.astype(np.float32))                # OpenCV bounding box around her landmarks
            self.bbox = (float(bx), float(by), float(bx + bw_), float(by + bh_))
        else:
            self.bbox = (0, 0, 0, 0)
        bw, bh = self.bbox[2] - self.bbox[0], self.bbox[3] - self.bbox[1]
        self.aspect = float(bw / max(bh, 1.0))                                     # width / height of the body in the image
        self.center = ((self.bbox[0] + self.bbox[2]) / 2 / self.w, (self.bbox[1] + self.bbox[3]) / 2 / self.h)   # 0..1

    def point(self, *names):
        """Mean world position of the named landmarks that are valid, or None."""
        idx = [LM[n] for n in names if self.valid[LM[n]] and self.vis[LM[n]] > 0.3]
        return self.world[idx].mean(0) if idx else None

    @property
    def hip(self):
        return self.point("l_hip", "r_hip")

    @property
    def shoulder(self):
        return self.point("l_shoulder", "r_shoulder")

    def torso_pitch_deg(self):
        """Angle between the hip-to-shoulder line and vertical (0 = upright, 90 = horizontal)."""
        h, s = self.hip, self.shoulder
        if h is None or s is None:
            return None
        v = s - h
        return float(np.degrees(np.arccos(np.clip(v[2] / max(np.linalg.norm(v), 1e-6), -1, 1))))

    def body_axis_xy(self):
        """Horizontal direction along her body (feet to head), unit vector, or None."""
        s, a = self.point("l_shoulder", "r_shoulder", "nose"), self.point("l_ankle", "r_ankle", "l_knee", "r_knee")
        if s is None or a is None:
            return None
        v = (s - a)[:2]
        n = np.linalg.norm(v)
        return v / n if n > 1e-6 else None


class PersonObserver:
    def __init__(self, tracker, fovy_deg=S.FOVY, depth_outlier=1.2):
        self.tracker, self.fovy, self.depth_outlier = tracker, fovy_deg, depth_outlier

    def observe(self, rgb, depth, base_pose, pan_deg, tilt_deg, cam=None):
        """cam = (position, rotation camera->world) for a camera that is not the robot's head (e.g. a fixed ceiling camera)."""
        det = self.tracker.detect(rgb)
        if det is None:
            return None
        h, w = depth.shape
        f = 0.5 * h / np.tan(np.radians(self.fovy) / 2)
        pix = det["image"][:, :2] * np.array([w, h])
        z = np.full(33, np.nan)
        for i, (u, v) in enumerate(pix):
            ui, vi = int(np.clip(round(u), 2, w - 3)), int(np.clip(round(v), 2, h - 3))
            win = depth[vi - 2:vi + 3, ui - 2:ui + 3]
            z[i] = np.percentile(win, 10)          # closest surface in the window = her body, not the wall behind her
        inside = (pix[:, 0] > 0) & (pix[:, 0] < w) & (pix[:, 1] > 0) & (pix[:, 1] < h) & (det["vis"] > 0.3)
        good = inside & (z < 50)
        valid = good.copy()
        if good.sum() >= 4:
            med = np.median(z[good])
            far = good & (np.abs(z - med) > self.depth_outlier)
            z[far] = med
        valid &= np.isfinite(z) & (z < 50)
        cam_pos, r_wc = cam if cam is not None else camera_pose(base_pose, pan_deg, tilt_deg)
        pts_c = np.stack([(pix[:, 0] - w / 2) / f * z, -(pix[:, 1] - h / 2) / f * z, -z], 1)
        world = cam_pos + pts_c @ r_wc.T
        return Observation(world, valid, det["vis"], pix, (h, w))
