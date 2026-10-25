"""
Simulated emergency dispatch: message the family, call the ambulance.

NOTHING REAL IS SENT. Every message and call is written to a log with its simulated time, so the experiments can
measure fall-to-alert latency. Privacy: the robot processes video on board; nothing leaves it until an alert, and
an alert carries text plus at most one snapshot taken after a confirmed emergency, with the face blurred.
`bytes_off_board` counts everything that left the robot (it must be 0 until the first alert).

The robot never diagnoses. Wording is "collapsed and not responding, possible cardiac emergency".
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim"))
import apartment_layout as L  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "family_contacts.json")


START_CLOCK = "14:00:00"      # simulated time of day at t = 0 (a demo may set it, e.g. so that a reminder lands on 08:00)


def clock(t, start=None):
    """Simulated wall-clock string for sim time t (seconds)."""
    h, m, s = (int(x) for x in (start or START_CLOCK).split(":"))
    tot = h * 3600 + m * 60 + s + int(t)
    return f"{tot // 3600 % 24:02d}:{tot // 60 % 60:02d}:{tot % 60:02d}"


def blur_face(rgb, centre_px, radius_px):
    """OpenCV: blur a disc around the face (centre and radius in pixels); returns a PIL image."""
    u, v = int(centre_px[0]), int(centre_px[1])
    r = max(int(radius_px), 12)
    k = max(r // 2, 6) | 1
    blurred = cv2.GaussianBlur(rgb, (2 * k + 1, 2 * k + 1), 0)
    mask = np.zeros(rgb.shape[:2], np.uint8)
    cv2.circle(mask, (u, v), r, 255, -1)
    return Image.fromarray(np.where(mask[..., None] > 0, blurred, rgb).astype(np.uint8))


class Dispatcher:
    def __init__(self, out_dir, config_path=DEFAULT_CONFIG, voice=None):
        self.voice = voice                  # optional agent voice (src/agent): rephrases family texts; the ambulance script is never rephrased
        with open(config_path) as f:
            self.cfg = json.load(f)
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.sent = []                  # every message / call: dict(t, clock, to, channel, kind, text, ...)
        self.bytes_off_board = 0
        self.first_send_t = None

    # ---- helpers ----------------------------------------------------------------------------
    def _send(self, t, to, channel, kind, text, attachment=None, size=0, telemetry=None):
        rec = dict(t=round(float(t), 2), clock=clock(t), to=to, channel=channel, kind=kind, text=text, attachment=attachment)
        if telemetry is not None:
            rec["telemetry"] = telemetry                       # structured payload sent with the alert
        self.sent.append(rec)
        self.bytes_off_board += len(text.encode()) + size + (len(json.dumps(telemetry)) if telemetry is not None else 0)
        if self.first_send_t is None:
            self.first_send_t = t
        return rec

    def _where(self, xy):
        return L.room_of(*xy)

    def _say(self, kind, t, facts, default, audience="family"):
        if self.voice is None:
            return default
        return self.voice.phrase(kind, dict(facts, clock=clock(t)), default, audience=audience, t=t)

    # ---- the messages -----------------------------------------------------------------------
    def heads_up(self, t, xy, t_impact):
        """Text only, no picture: sent as soon as the fall is confirmed, while the robot drives over."""
        p = self.cfg["patient"]["display_name"]
        text = (f"[Companion robot] Possible fall at {clock(t_impact)}. {p} is on the floor in the {self._where(xy)} and has not moved. "
                f"The robot is going to check on her now.")
        text = self._say("heads_up", t_impact, dict(room=self._where(xy)), text)
        return [self._send(t, c["name"], c["channels"][0], "heads_up", text) for c in self.cfg["family"] if c["priority"] == 1]

    def emergency(self, t, xy, t_impact, unresponsive_s, snapshot=None, evidence=None, telemetry=None):
        """After the check-in fails: message every family contact (with the blurred snapshot) and call the ambulance."""
        p, addr = self.cfg["patient"]["display_name"], self.cfg["patient"]["address"]
        room = self._where(xy)
        snap_path, snap_bytes = None, 0
        if snapshot is not None:
            snap_path = os.path.join(self.out_dir, "snapshot_face_blurred.png")
            snapshot.save(snap_path)
            snap_bytes = os.path.getsize(snap_path)
        family_text = (f"[URGENT] {p} collapsed in the {room} at {clock(t_impact)} and is NOT responding "
                       f"(no answer to 'Are you okay?' for {unresponsive_s:.0f} s). Possible cardiac emergency. "
                       f"An ambulance has been called to {addr}. Photo attached (face blurred).")
        family_text = self._say("emergency", t_impact, dict(room=room, seconds=unresponsive_s), family_text)
        out = []
        for c in self.cfg["family"]:
            for ch in c["channels"]:
                out.append(self._send(t, c["name"], ch, "emergency", family_text, attachment=snap_path if ch in ("app_push", "sms") else None,
                                      size=snap_bytes if ch in ("app_push", "sms") else 0, telemetry=telemetry))
        amb = self.cfg["ambulance"]
        call_text = (f"Automated call to {amb['service']}: elderly woman living alone collapsed at {clock(t_impact)}, not responding for "
                     f"{unresponsive_s:.0f} s. Address: {addr}, in the {room}. Robot is with her. Suspected cardiac emergency. "
                     f"Basis: camera showed a fall and no movement ({evidence or 'no detail'}).")
        out.append(self._send(t, amb["service"], amb["channel"], "ambulance_call", call_text, telemetry=telemetry))
        return out

    def all_clear(self, t):
        """She answered the check-in: tell the family it was a false alarm (only if they had been told something)."""
        if not self.sent:
            return []
        p = self.cfg["patient"]["display_name"]
        text = f"[Companion robot] All clear: {p} answered the robot and says she is fine."
        text = self._say("all_clear", t, {}, text)
        return [self._send(t, c["name"], c["channels"][0], "all_clear", text) for c in self.cfg["family"] if c["priority"] == 1]

    def missed_reminder(self, t, label):
        """Demo-only medicine reminder was not acknowledged: text to the first-priority family contacts (never an emergency)."""
        p = self.cfg["patient"]["display_name"]
        text = f"[Companion robot] {p} has not acknowledged the reminder for {label.replace("your ", "her ")}. She looks well; please check in with her when you can."
        text = self._say("reminder_missed", t, dict(label=label), text)
        return [self._send(t, c["name"], c["channels"][0], "reminder_missed", text) for c in self.cfg["family"] if c["priority"] == 1]

    def medicine_report(self, t, label, status):
        """Tell the first-priority family contacts how a medicine reminder ended: 'taken' (seen), 'acknowledged' or 'missed'."""
        p = self.cfg["patient"]["display_name"]
        her = label.replace("your ", "her ")
        base = {"taken": f"[Companion robot] {p} took {her} (the robot saw it).",
                "acknowledged": f"[Companion robot] {p} said she would take {her}; the robot did not see her take it.",
                }[status]
        text = self._say("tablet_taken" if status == "taken" else "reminder_ack", t, dict(label=label), base)
        return [self._send(t, c["name"], c["channels"][0], "medicine_" + status, text) for c in self.cfg["family"] if c["priority"] == 1]

    def welfare_missed(self, t):
        p = self.cfg["patient"]["display_name"]
        text = f"[Companion robot] {p} did not answer when I checked on her as you asked. She looks well; please call her when you can."
        text = self._say("welfare_missed", t, {}, text)
        return [self._send(t, c["name"], c["channels"][0], "welfare_missed", text) for c in self.cfg["family"] if c["priority"] == 1]

    def siren(self, t, xy, level_db, cardiac_cue=False):
        """A loud alarm is sounding in the flat: tell the neighbour (priority 2) and the family so they know why the building is noisy."""
        p = self.cfg["patient"]["display_name"]
        room = self._where(xy)
        base = f"[Companion robot] A loud alarm ({level_db:.0f} dB at 1 m) is sounding in {p}'s flat, {room}, to attract help. She has collapsed and is not responding." + (" She pressed a hand to her chest just before." if cardiac_cue else "")
        text = self._say("siren_neighbour", t, dict(room=room, cardiac_cue=cardiac_cue), base)
        return [self._send(t, c["name"], c["channels"][0], "siren_on", text) for c in self.cfg["family"]]

    def update(self, t, since_s):
        p = self.cfg["patient"]["display_name"]
        text = f"[Update] {p} is still not responding ({since_s:.0f} s since the collapse). Ambulance on its way. Robot remains with her."
        text = self._say("update", t, dict(seconds=since_s), text)
        return [self._send(t, c["name"], c["channels"][0], "update", text) for c in self.cfg["family"] if c["priority"] == 1]

    def save(self):
        path = os.path.join(self.out_dir, "alerts.json")
        with open(path, "w") as f:
            json.dump(dict(messages=self.sent, bytes_off_board=self.bytes_off_board, first_send_t=self.first_send_t), f, indent=2)
        return path
