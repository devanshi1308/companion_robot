"""
Fall detector: watches how her body moves over time (not a single frame) and decides
normal -> suspect (impact) -> confirmed (down and still) or back to normal (she got up / was only moving low).

Features come from the robot's own camera pipeline (Observation): hip height (world), torso pitch, aspect ratio.
Hip height is smoothed with the guide's 2nd-order Butterworth low-pass (5 Hz at 30 Hz), causally.

Rule, from the guide, with documented adaptations for camera-estimated (noisy) landmarks:
  impact    : within the last window_s she was upright (hip >= up_z) and now the hip is <= down_z (guide: 0.20 m on
              ground truth; the camera's 3D landmarks are about 17 cm off when she is lying, so 0.35 m here),
              the drop is >= min_drop_m and the peak descent speed over a 0.15-0.5 s stretch is >= min_peak_descent
              (guide: 1.8 m/s on ground truth; filtered camera estimates peak lower, 1.2 m/s here), and the torso is
              near horizontal (>= 50 deg; guide 60), and her bounding box has turned wider than tall (aspect >= 1.0; guide 1.2)
              and is changing fast (aspect rises >= 1.0 per second). These values were set while building the first demo (one fall);
              they must be re-fitted on a separate training split before any result is reported.
  confirmed : after quiet_s (guide: 3.0 s) the body has stayed low and still. If she stands back up the alarm is
              cancelled; if she keeps moving about while low for longer than give_up_s it is treated as a
              deliberate low movement (e.g. floor exercise), not a collapse.
All thresholds live in FallConfig so experiments can change them in one place.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, lfilter, lfilter_zi


@dataclass
class FallConfig:
    fs: float = 30.0
    cutoff_hz: float = 5.0
    up_z: float = 0.60
    down_z: float = 0.35
    window_s: float = 1.2
    min_drop_m: float = 0.40
    ar_min: float = 1.0                  # bounding box wider than tall (guide: AR >= 1.2 on ground truth)
    min_ar_rate: float = 1.0             # per second, peak rise of the aspect ratio over a 0.15-0.5 s stretch
    min_peak_descent: float = 1.2        # m/s, peak over a 0.15-0.5 s stretch (guide: 1.8 on ground truth; filtered camera estimates peak lower)
    pitch_min_deg: float = 50.0
    quiet_s: float = 3.0
    quiet_move_m: float = 0.25          # 'still': the median hip position moved less than this between the two halves of the last 2 s
    give_up_s: float = 8.0
    standing_z: float = 0.60
    gap_reset_s: float = 0.3
    lie_s: float = 5.0                  # found lying on the floor (fall not seen): still this long -> confirmed


class FallDetector:
    def __init__(self, cfg=None):
        self.cfg = cfg or FallConfig()
        self.b, self.a = butter(2, self.cfg.cutoff_hz, fs=self.cfg.fs)
        self.reset()

    def reset(self):
        self.zi = None
        self.hist = deque()                      # (t, z_filtered, pitch, hip_xyz, aspect)
        self.state = "normal"
        self.t_impact = None
        self.t_confirmed = None
        self.t_last = None
        self.lying_since = None
        self.witnessed = None
        self.pitch = 0.0
        self.ar = 0.0
        self.log = []                            # (t, text)
        self.features = {}

    def _say(self, t, text):
        self.log.append((t, text))

    def drift(self, t, span=2.0):
        """How far the body moved over the last `span` seconds: distance between the median hip positions of the first and
        second half (a median shrugs off the jitter of single landmark estimates). None until enough samples."""
        recent = [h for h in self.hist if t - h[0] <= span]
        if len(recent) < 10:
            return None
        mid = len(recent) // 2
        a = np.median(np.array([h[3] for h in recent[:mid]]), axis=0)
        b = np.median(np.array([h[3] for h in recent[mid:]]), axis=0)
        return float(np.linalg.norm(a - b))

    def update(self, t, obs):
        """Feed one observation (or None). Returns the state."""
        c = self.cfg
        hip = None if obs is None else obs.hip
        if hip is None:
            if self.lying_since is not None and self.t_last is not None and t - self.t_last > 2.0:
                self.lying_since = None                          # nothing seen for 2 s: an old 'lying' reading must not linger (a single phantom detection once blocked the robot for good)
            return self.state
        if self.t_last is None or t - self.t_last > c.gap_reset_s:
            self.zi = lfilter_zi(self.b, self.a) * hip[2]                    # restart the filter after a gap
        zf, self.zi = lfilter(self.b, self.a, [hip[2]], zi=self.zi)
        zf = float(zf[0])
        self.t_last = t
        p = obs.torso_pitch_deg()
        if p is not None:
            self.pitch = 0.7 * self.pitch + 0.3 * p if self.hist else p        # light smoothing
        self.ar = obs.aspect if len(self.hist) == 0 else 0.6 * self.ar + 0.4 * obs.aspect          # light smoothing of the bounding-box aspect ratio
        self.hist.append((t, zf, self.pitch, hip.copy(), self.ar))
        while self.hist and t - self.hist[0][0] > max(c.window_s, c.quiet_s + 1.0, 3.0):
            self.hist.popleft()
        self.features = dict(t=t, hip_z=zf, pitch=self.pitch, aspect=obs.aspect, n_valid=obs.n_valid, drift=self.drift(t))

        # found on the floor without having seen the fall (unwitnessed): low, horizontal and still for lie_s
        if zf <= c.down_z and self.pitch >= c.pitch_min_deg:
            self.lying_since = self.lying_since if self.lying_since is not None else t
        else:
            self.lying_since = None
        if self.state == "normal" and self.lying_since is not None and t - self.lying_since >= c.lie_s:
            wander = self.drift(t)
            if wander is not None and wander <= c.quiet_move_m:
                self.state, self.t_impact, self.t_confirmed, self.witnessed = "confirmed", self.lying_since, t, False
                self._say(t, f"found lying on the floor, still for {c.lie_s:.0f} s (fall not seen)")
                return self.state

        if self.state == "normal":
            win = [h for h in self.hist if t - h[0] <= c.window_s]
            if len(win) >= 5:
                t_hi, z_hi = max(((h[0], h[1]) for h in win), key=lambda x: x[1])
                drop = z_hi - zf
                peak = ar_rate = 0.0
                for i, (ta, za, _, _, ara) in enumerate(win):
                    for tb, zb, _, _, arb in win[i + 1:]:
                        if 0.15 <= tb - ta <= 0.5:
                            peak = max(peak, (za - zb) / (tb - ta))
                            ar_rate = max(ar_rate, (arb - ara) / (tb - ta))
                box_ok = (self.ar >= c.ar_min and ar_rate >= c.min_ar_rate) if obs.n_valid >= 12 else True      # skip the box test when little of her is visible
                if z_hi >= c.up_z and zf <= c.down_z and drop >= c.min_drop_m and peak >= c.min_peak_descent and self.pitch >= c.pitch_min_deg and box_ok:
                    self.state, self.t_impact, self.witnessed = "suspect", t, True
                    self._say(t, f"impact: hip {z_hi:.2f} -> {zf:.2f} m, peak descent {peak:.1f} m/s, torso {self.pitch:.0f} deg, box aspect {self.ar:.1f} (rising {ar_rate:.1f}/s)")
        elif self.state == "suspect":
            if zf >= c.standing_z:
                self._say(t, "cancelled: she is upright again")
                self.state, self.t_impact = "normal", None
            elif t - self.t_impact >= c.quiet_s:
                wander = self.drift(t)
                if wander is not None and wander <= c.quiet_move_m and zf <= c.down_z + 0.15:
                    self.state, self.t_confirmed = "confirmed", t
                    self._say(t, f"confirmed down and still ({c.quiet_s:.0f} s window, wander {wander * 100:.0f} cm)")
                elif t - self.t_impact >= c.give_up_s:
                    self._say(t, "cancelled: she keeps moving while low")
                    self.state, self.t_impact = "normal", None
        elif self.state == "confirmed" and zf >= c.standing_z:
            self._say(t, "cancelled: she is upright again")
            self.state, self.t_impact, self.t_confirmed, self.lying_since = "normal", None, None, None
        return self.state
