"""
Checks for Baymax's answers, the siren and the medicine-taking motion (no simulation run needed).
Run:  python tests/test_platform.py
"""
import os
import sys

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("agent", "sim", "experiments", "control"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import siren as SI  # noqa: E402


def test_baymax_answers_from_the_facts():
    import chat
    f = dict(patient="Asha", person=dict(room="living room", posture="sitting", seen_now=True), alert=dict(title="All well", emergency=False),
             doses=[dict(label="your 8 o'clock tablet", status="taken", clock_taken="08:00:14", clock_due="08:00:01", welfare=False)], robot=dict(feeling=dict(label="happy")))
    r, a = chat.answer("Has she taken her tablet?", f)
    assert "08:00:14" in r and a == []
    f["doses"][0]["status"] = "missed"
    assert "did not answer" in chat.answer("did she take her medicine", f)[0]
    r, a = chat.answer("where is she?", f)
    assert "living room" in r and "sitting" in r
    r, a = chat.answer("call 108", f)
    assert a == [] and "cannot place calls" in r                                        # it never places a call on request


def test_siren_signal_and_levels():
    x = SI.synth_siren(2.0)
    assert x.dtype == np.float32 and abs(x).max() <= 0.51 and len(x) == 2 * SI.SR
    spec = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / SI.SR)
    peak = f[np.argmax(spec)]
    assert 600 < peak < 1000, peak                        # the two tones sit around 650 and 950 Hz
    assert abs(SI.level_at(1.0) - 95) < 1e-6 and abs(SI.level_at(2.0) - 89) < 0.1 and SI.level_at(2.0, wall_loss_db=25) < 65
    print(f"  siren: strongest component {peak:.0f} Hz; 60 dB out to {SI.distance_for_level(60):.0f} m open, {SI.distance_for_level(60, wall_loss_db=25):.1f} m behind one closed door")


def test_taking_a_tablet_brings_the_hand_to_the_mouth():
    import human_motion as HM
    import motions as M
    m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "scene_with_human.xml"))
    rig = HM.Rig(m)
    sv = M._sites(m)
    spec = dict(kind="adl", subtype="take_tablet", path=[(-2.2, -1.3), (-2.2, 0.55), (-1.0, 0.55), M.SOFA_STAND], speed=0.7, hold_s=5.0, intake_after_s=6.0, seed=1)
    clip = M.make_clip(m, rig, spec)
    best = 9.0
    for t in np.arange(clip.meta["t_intake"] - 0.5, clip.meta["t_intake"] + 4.0, 0.1):
        rig.d.qpos[rig.sl_q] = clip.at(t)
        mujoco.mj_kinematics(m, rig.d)
        X = rig.d.site_xpos
        best = min(best, np.linalg.norm(X[sv[16]] - 0.5 * (X[sv[9]] + X[sv[10]])))
    print(f"  closest wrist-to-mouth distance while taking the tablet: {best * 100:.1f} cm")
    assert best < 0.08


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
