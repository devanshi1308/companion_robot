"""
Pre-collapse (prodrome) cues from a SEQUENCE of pose landmarks: what she does in the seconds BEFORE she goes down.

A camera cannot diagnose a heart attack.  What it can see over a time window is behaviour that is often described before a cardiac
event: a hand pressed to the chest, a hunched torso, slowing down, swaying.  These cues are scripted in the simulation from clinical
descriptions and are NOT validated on patients; they only change what the alert says ("collapse after a chest-clutch pattern") and
give an early warning, never a diagnosis.

    mon = ProdromeMonitor()
    for t, obs in stream: flag = mon.update(t, obs)       # obs: person_observer.Observation (or any object with world/valid/vis)

Cues over a sliding window (W seconds):
  chest      either wrist stays within CHEST_R of her chest point (shoulders to hips, 35% of the way down) for at least CHEST_FRAC of the window
  hunch      the hip-to-shoulder line leans forward by at least HUNCH_DEG (smoothed), while she is upright (hip higher than 0.6 m)
  slowdown   her hip speed over the last 3 s is below SLOW_RATIO of the speed over the 3 s before that, which was at least 0.25 m/s
  sway       the hip's sideways wobble about its path exceeds SWAY_M
Flag: chest cue AND at least one of hunch / slowdown / sway.  The monitor stays flagged for HOLD_S seconds after the last positive window.
"""
from collections import deque

import numpy as np

W_S = 6.0
CHEST_R = 0.28
CHEST_FRAC = 0.5
HUNCH_DEG = 12.0
SLOW_RATIO = 0.5
SWAY_M = 0.04
HOLD_S = 8.0


DEFAULTS = dict(W_S=W_S, CHEST_R=CHEST_R, CHEST_FRAC=CHEST_FRAC, HUNCH_DEG=HUNCH_DEG, SLOW_RATIO=SLOW_RATIO, SWAY_M=SWAY_M, HOLD_S=HOLD_S)


class ProdromeMonitor:
    def __init__(self, **cfg):
        self.c = dict(DEFAULTS, **cfg)
        self.hist = deque()                      # (t, hip(3), shoulder(3), wrist_dist_min, pitch)
        self.flag_since = None
        self.last_pos = -1e9
        self.t_first_flag = None
        self.cues = {}

    @staticmethod
    def _pt(obs, idx):
        ok = [i for i in idx if obs.valid[i] and obs.vis[i] > 0.3 and np.isfinite(obs.world[i]).all()]
        return obs.world[ok].mean(0) if ok else None

    def update(self, t, obs):
        if obs is not None:
            hip, sh = self._pt(obs, (23, 24)), self._pt(obs, (11, 12))
            if hip is not None and sh is not None:
                chest = sh + 0.35 * (hip - sh)
                dists = [np.linalg.norm(obs.world[i] - chest) for i in (15, 16) if obs.valid[i] and obs.vis[i] > 0.3 and np.isfinite(obs.world[i]).all()]
                v = sh - hip
                pitch = float(np.degrees(np.arccos(np.clip(v[2] / max(np.linalg.norm(v), 1e-6), -1, 1))))
                self.hist.append((t, hip.copy(), sh.copy(), min(dists) if dists else np.inf, pitch))
        while self.hist and t - self.hist[0][0] > self.c['W_S'] + 3.0:
            self.hist.popleft()
        self._k = getattr(self, '_k', 0) + 1
        pos = self._evaluate(t) if self._k % 5 == 0 else False          # the cues change on a scale of seconds: evaluate at about 4 Hz
        if pos:
            self.last_pos = t
        flagged = t - self.last_pos <= self.c['HOLD_S']
        if flagged and self.flag_since is None:
            self.flag_since = t
            self.t_first_flag = t if self.t_first_flag is None else self.t_first_flag
        if not flagged:
            self.flag_since = None
        return flagged

    def _evaluate(self, t):
        win = [h for h in self.hist if t - h[0] <= self.c['W_S']]
        if len(win) < 12:
            return False
        upright = np.median([h[1][2] for h in win]) > 0.6
        chest = np.mean([h[3] < self.c['CHEST_R'] for h in win]) >= self.c['CHEST_FRAC']
        pitch = np.median([h[4] for h in win[-15:]])
        hunch = upright and pitch >= self.c['HUNCH_DEG']
        recent = [h for h in self.hist if t - h[0] <= 3.0]
        before = [h for h in self.hist if 3.0 < t - h[0] <= 6.0]
        slow = False
        if len(recent) >= 6 and len(before) >= 6:
            sp = lambda seg: np.hypot(*(seg[-1][1][:2] - seg[0][1][:2])) / max(seg[-1][0] - seg[0][0], 1e-6)
            s_old, s_new = sp(before), sp(recent)
            slow = s_old >= 0.25 and s_new < self.c['SLOW_RATIO'] * s_old
        sway = False
        if len(win) >= 20:
            xy = np.array([h[1][:2] for h in win])
            d = xy[-1] - xy[0]
            if np.linalg.norm(d) > 0.3:
                n = np.array([-d[1], d[0]]) / np.linalg.norm(d)
                off = (xy - xy[0]) @ n
                sway = float(off.max() - off.min()) > 2 * self.c['SWAY_M']
        self.cues = dict(chest=bool(chest), hunch=bool(hunch), slowdown=bool(slow), sway=bool(sway))
        return bool(chest and (hunch or slow or sway))


def replay(npz_path, t_from=0.0, **cfg):
    """Run the monitor over a saved landmark stream (features_*.npz); returns the first flag time or None, and the flag history."""
    z = np.load(npz_path)

    class O:
        pass
    mon = ProdromeMonitor(**cfg)
    first, hist = None, []
    for i, t in enumerate(z["t"]):
        if z["n_valid"][i] == 0:
            flag = mon.update(float(t), None)
        else:
            o = O()
            o.world, o.valid, o.vis = z["world"][i].astype(float), z["valid"][i], z["vis"][i]
            flag = mon.update(float(t), o)
        hist.append((float(t), flag))
        if flag and first is None and t >= t_from:
            first = float(t)
    return first, hist
