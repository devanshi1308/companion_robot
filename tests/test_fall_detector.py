"""
Fall-detector logic on synthetic movements (no camera): the real fall is caught; the false-alarm cases the sheet names
(sitting down abruptly on a low sofa, lying on the bed, tying shoelaces, dropping keys, floor exercise) are not.
Run:  python tests/test_fall_detector.py
"""
import os
import sys

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "vision"))
from fall_detector import FallDetector  # noqa: E402


class FakeObs:
    def __init__(self, z, pitch, x=0.0):
        self.hip = np.array([x, 0.0, z])
        self._p = pitch
        self.aspect = 0.4 if pitch < 45 else 2.0
        self.n_valid = 28

    def torso_pitch_deg(self):
        return self._p


def run(profile, seconds, fs=30.0, noise=0.02, seed=0):
    """profile(t) -> (hip_z, torso_pitch_deg). Returns the detector after feeding noisy observations."""
    rng = np.random.default_rng(seed)
    det = FallDetector()
    for k in range(int(seconds * fs)):
        t = k / fs
        z, p = profile(t)
        det.update(t, FakeObs(z + noise * rng.standard_normal(), p + 3 * rng.standard_normal(), 0.02 * rng.standard_normal()))
    return det


def smooth(t, t0, t1, a, b):
    u = np.clip((t - t0) / (t1 - t0), 0, 1)
    return a + (b - a) * u * u * (3 - 2 * u)


def test_real_fall_is_confirmed():
    det = run(lambda t: (smooth(t, 3.0, 3.6, 0.9, 0.12), smooth(t, 3.0, 3.6, 8, 88)), 10)
    assert det.state == "confirmed" and det.witnessed
    print(f"  fall at 3.0 s: impact flagged at {det.t_impact:.2f} s, confirmed at {det.t_confirmed:.2f} s")
    assert 3.2 < det.t_impact < 3.8 and det.t_confirmed - det.t_impact >= 3.0


def test_false_alarm_cases_are_ignored():
    """None of these may raise an alarm."""
    cases = {
        "abrupt sit on a low sofa (hip 0.9 -> 0.45 in 0.4 s, torso upright)": lambda t: (smooth(t, 3, 3.4, 0.9, 0.45), 12),
        "lying down on the bed (hip 0.9 -> 0.52 in 3 s, torso horizontal)": lambda t: (smooth(t, 3, 6, 0.9, 0.52), smooth(t, 3, 6, 8, 88)),
        "tying shoelaces (bend over, hip stays 0.62)": lambda t: (smooth(t, 3, 4, 0.9, 0.62), smooth(t, 3, 4, 8, 75)),
        "dropping keys (squat to 0.4 m and stand again)": lambda t: (0.9 - 0.5 * np.sin(np.pi * np.clip((t - 3) / 3, 0, 1)), 15),
    }
    for name, prof in cases.items():
        det = run(prof, 14)
        print(f"  {name}: {det.state}")
        assert det.state == "normal" and det.t_impact is None, name


def test_deliberate_floor_lying_is_flagged_and_left_to_the_check_in():
    """Lowering yourself slowly to the floor and lying still is indistinguishable from a long lie on camera alone:
    the detector flags it (never as a witnessed fall) and the robot's 'Are you okay?' check-in clears it."""
    det = run(lambda t: (smooth(t, 3, 7, 0.9, 0.15), smooth(t, 3, 7, 8, 88)), 16)
    print(f"  slow lowering to the floor then still: {det.state}, witnessed={det.witnessed}")
    assert det.state == "confirmed" and det.witnessed is False


def test_found_lying_without_seeing_the_fall():
    det = run(lambda t: (0.12, 88), 12)
    assert det.state == "confirmed" and det.witnessed is False
    print(f"  seen lying from the start: confirmed at {det.t_confirmed:.1f} s (fall not witnessed)")
    bed = run(lambda t: (0.5, 88), 14)
    assert bed.state == "normal", "lying on a bed (hip 0.5 m) is not a floor fall"


def test_she_gets_up_again():
    det = run(lambda t: (smooth(t, 3, 3.6, 0.9, 0.12) if t < 6 else smooth(t, 6, 8, 0.12, 0.9), smooth(t, 3, 3.6, 8, 88) if t < 6 else smooth(t, 6, 8, 88, 8)), 12)
    assert det.state == "normal"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
