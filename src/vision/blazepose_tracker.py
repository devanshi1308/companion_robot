"""
MediaPipe BlazePose wrapper: camera image in, 33 landmarks out.

Uses the MediaPipe Tasks API. The pose model file is not stored in git (the course audit
false-flags binary files); download it once:

    mkdir -p external_assets/mediapipe && curl -sSL -o external_assets/mediapipe/pose_landmarker_lite.task \
      https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
"""
import os

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEFAULT_MODEL = os.path.join(ROOT, "external_assets", "mediapipe", "pose_landmarker_lite.task")


class PoseTracker:
    """detect(rgb) -> dict(image=(33,3) normalised x,y,z; world=(33,3) metres, hip-centred; vis=(33,)) or None."""

    def __init__(self, model_path=DEFAULT_MODEL, min_conf=0.3):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"pose model not found: {model_path} (see the download command in this file's docstring)")
        opts = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE, num_poses=1,
            min_pose_detection_confidence=min_conf, min_pose_presence_confidence=min_conf,
            min_tracking_confidence=min_conf)
        self._lm = vision.PoseLandmarker.create_from_options(opts)

    def detect(self, rgb):
        res = self._lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        if not res.pose_landmarks:
            return None
        pts = res.pose_landmarks[0]
        world = res.pose_world_landmarks[0]
        return {
            "image": np.array([[p.x, p.y, p.z] for p in pts]),
            "world": np.array([[p.x, p.y, p.z] for p in world]),
            "vis": np.array([p.visibility for p in pts]),
        }
