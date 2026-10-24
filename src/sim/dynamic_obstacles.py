"""
Moving obstacles for the apartment (kinematic: driven by setting the mocap pose each step).

The robot vacuum loops around the open-plan area at VACUUM_SPEED (override per trial to randomise
obstacle velocity, as the standards manual asks).  It still collides with everything else, so the
robot and the human have to avoid it.
"""
import numpy as np

import apartment_layout as L


class Vacuum:
    def __init__(self, m, speed=L.VACUUM_SPEED, loop=L.VACUUM_LOOP):
        self.mid = m.body("vacuum").mocapid[0]
        self.speed = float(speed)
        pts = np.vstack([loop, loop[:1]])
        seg = np.diff(pts, axis=0)
        self.pts, self.seg = pts, seg
        self.len = np.hypot(seg[:, 0], seg[:, 1])
        self.cum = np.concatenate([[0.0], np.cumsum(self.len)])
        self.perimeter = self.cum[-1]

    def pose(self, t):
        s = (self.speed * t) % self.perimeter
        i = int(np.searchsorted(self.cum, s, side="right") - 1)
        i = min(i, len(self.len) - 1)
        u = (s - self.cum[i]) / self.len[i]
        xy = self.pts[i] + u * self.seg[i]
        yaw = np.arctan2(self.seg[i][1], self.seg[i][0])
        return xy, yaw

    def start_at(self, s0):
        """Distance already travelled along the loop (used with advance())."""
        self.s = float(s0) % self.perimeter

    def advance(self, d, dt, blockers=(), stop_dist=0.55):
        """Move on by speed * dt unless something (the robot, her) is within stop_dist of the vacuum: a real robot vacuum stops when its bumper
        touches something, it does not push through it."""
        xy, _ = self.pose_s(self.s)
        if not any(np.hypot(b[0] - xy[0], b[1] - xy[1]) < stop_dist for b in blockers):
            self.s = (self.s + self.speed * dt) % self.perimeter
        xy, yaw = self.pose_s(self.s)
        d.mocap_pos[self.mid] = [xy[0], xy[1], 0.0]
        d.mocap_quat[self.mid] = [np.cos(yaw / 2), 0.0, 0.0, np.sin(yaw / 2)]

    def pose_s(self, s):
        i = int(np.searchsorted(self.cum, s, side="right") - 1)
        i = min(i, len(self.len) - 1)
        u = (s - self.cum[i]) / self.len[i]
        return self.pts[i] + u * self.seg[i], np.arctan2(self.seg[i][1], self.seg[i][0])

    def update(self, d, t):
        xy, yaw = self.pose(t)
        d.mocap_pos[self.mid] = [xy[0], xy[1], 0.0]
        d.mocap_quat[self.mid] = [np.cos(yaw / 2), 0.0, 0.0, np.sin(yaw / 2)]
