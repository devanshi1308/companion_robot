"""
Open the apartment in the interactive MuJoCo viewer (macOS: run with mjpython).

    mjpython src/tools/open_scene.py            # empty apartment, cut-away walls
    mjpython src/tools/open_scene.py --human    # the full demo: she walks in, trips and falls on the floor
    mjpython src/tools/open_scene.py --full-walls
"""
import argparse
import os
import sys
import time

import mujoco
import mujoco.viewer

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

ap = argparse.ArgumentParser()
ap.add_argument("--human", action="store_true", help="run the walk-and-fall demo (src/sim/walk_and_fall.py --view)")
ap.add_argument("--full-walls", action="store_true", help="show full-height walls instead of the cut-away view")
a = ap.parse_args()

if a.human:
    # Do not just drop the human model into the room: its default spot is above the sofa.
    sys.path.insert(0, os.path.join(ROOT, "src", "sim"))
    from walk_and_fall import main as demo
    demo(["--view"] + (["--full-walls"] if a.full_walls else []))
    sys.exit(0)

xml = os.path.join(ROOT, "models", "domestic_environment.xml")
model = mujoco.MjModel.from_xml_path(xml)        # path (not string) so texture files resolve
data = mujoco.MjData(model)
print("Loaded", os.path.relpath(xml, ROOT), "- launching viewer...")

with mujoco.viewer.launch_passive(model, data) as viewer:
    viewer.opt.geomgroup[2] = 1 if a.full_walls else 0
    viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
    viewer.cam.fixedcamid = model.camera("overview").id
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(model.opt.timestep)
