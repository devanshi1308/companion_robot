"""Privacy contract (docs/ALERT_SCHEMA.md): nothing leaves the robot before the first alert; an alert carries only text, the structured telemetry and at most one
blurred snapshot; no frame or landmark arrays are ever in a message.
Run:  python tests/test_alert_privacy.py
"""
import json
import os
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("control", "robot", "sim", "agent"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
from dispatch import Dispatcher  # noqa: E402

TELEMETRY = dict(event="collapse_unresponsive", witnessed=True, time_of_collapse="14:00:10", seconds_since_collapse=12.0, unresponsive_for_s=10.0,
                 location=dict(room="living room", x=-1.0, y=0.4), posture=dict(hip_height_m=0.12, torso_angle_deg=85.0, box_aspect_ratio=1.8, still=True),
                 robot=dict(x=-1.6, y=0.2, distance_to_person_m=1.0), evidence="hip 0.12 m, torso 85 deg, still")


def _walk(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _walk(v)
    else:
        yield o


def test_nothing_leaves_before_the_first_alert():
    with tempfile.TemporaryDirectory() as d:
        disp = Dispatcher(d)
        assert disp.bytes_off_board == 0 and disp.sent == [] and disp.first_send_t is None


def test_alert_carries_text_telemetry_and_at_most_one_blurred_image():
    with tempfile.TemporaryDirectory() as d:
        disp = Dispatcher(d)
        snap = Image.fromarray(np.zeros((60, 80, 3), np.uint8))
        msgs = disp.emergency(30.0, (-1.0, 0.4), 20.0, 10.0, snapshot=snap, evidence="hip 0.12 m", telemetry=TELEMETRY)
        assert disp.bytes_off_board > 0 and disp.first_send_t == 30.0
        pictures = {m["attachment"] for m in msgs if m["attachment"]}
        assert len(pictures) <= 1, "at most one snapshot"
        for m in msgs:
            for v in _walk(m):
                assert not isinstance(v, (np.ndarray, bytes)), "no frames, landmark arrays or raw bytes in a message"
            json.dumps(m)                                                    # every record is plain JSON
        assert any(m["kind"] == "ambulance_call" for m in msgs) and any(m["kind"] == "emergency" for m in msgs)
        tele = [m["telemetry"] for m in msgs if m.get("telemetry")]
        assert tele and set(tele[0]) == set(TELEMETRY), "telemetry has exactly the documented fields"


def test_heads_up_has_no_picture():
    with tempfile.TemporaryDirectory() as d:
        disp = Dispatcher(d)
        msgs = disp.heads_up(15.0, (-1.0, 0.4), 12.0)
        assert msgs and all(not m["attachment"] for m in msgs)


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("PASS", n)
