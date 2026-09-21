"""
Extract the walking gait cycle from the AMASS clip into a small text file (JSON).

Why: the course audit script scans every file in the group folder as text and false-flags
binary data, and only 130 of the clip's 549 frames are used anyway.

Input : external_assets/habitat_humanoids/CMU_10_04_stageii.npz  (kept outside the group folder)
Output: models/human/walk_cycle_smplx.json

Run:  python src/sim/extract_walk_cycle.py [path/to/CMU_10_04_stageii.npz]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_NPZ = os.path.normpath(os.path.join(ROOT, "..", "external_assets", "habitat_humanoids", "CMU_10_04_stageii.npz"))
OUT = os.path.join(ROOT, "models", "human", "walk_cycle_smplx.json")
CYCLE = (300, 430)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NPZ
    z = np.load(src, allow_pickle=False)     # numeric arrays only; object arrays are never read
    a, b = CYCLE
    data = {
        "source": "AMASS CMU subject 10 trial 04 (CMU_10_04_stageii) via Habitat Humanoids; SMPL Body Motion File License",
        "fps": float(z["mocap_frame_rate"]),
        "frames": [a, b],
        "world": "Z-up (AMASS); pose_body is 21 joints x axis-angle in SMPL-X body order; root_orient axis-angle; trans in metres",
        "pose_body": np.round(z["pose_body"][a:b].reshape(-1, 21, 3), 6).tolist(),
        "root_orient": np.round(z["root_orient"][a:b], 6).tolist(),
        "trans": np.round(z["trans"][a:b], 6).tolist(),
    }
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print("wrote", os.path.relpath(OUT, ROOT), os.path.getsize(OUT) // 1024, "KB,", b - a, "frames")


if __name__ == "__main__":
    main()
