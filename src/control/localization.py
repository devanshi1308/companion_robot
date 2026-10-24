"""
State estimation: wheel odometry predicts, a range scan matched against the known map of the flat corrects.

Wheel odometry drifts (wheel slip on rug edges, bumps). Every few tenths of a second a 360 degree range scan (72 rays at
6 cm height, a physical sensor) is compared with the occupancy map: each candidate pose near the current estimate is scored
by how close the scan's hit points fall to mapped walls and furniture, with a small pull towards the odometry estimate
(in a straight corridor the scan cannot say where along the corridor you are). Things the map does not contain (her body,
the vacuum) land far from every mapped obstacle; their cost is capped so they cannot drag the pose away.

    loc = Localizer(model, grid)
    ranges = loc.scan(data, true_pose)          # the sensor reading (uses the simulator only as the physical world)
    new_est, info = loc.correct(est, ranges)
"""
import numpy as np
import mujoco

R_START = 0.32                    # rays start just outside the robot's footprint (radius 0.30 m)
R_MAX = 3.0
GROUPS = np.array([1, 0, 0, 1, 1, 0], dtype=np.uint8)      # furniture, her body, colliders (not skins / full-height wall copies)


class Localizer:
    def __init__(self, m, grid, n_rays=72, search_xy=0.30, step_xy=0.05, search_th_deg=12.0, step_th_deg=3.0, pull=0.02, cap=0.15):
        self.m, self.grid = m, grid
        self.angles = np.linspace(-np.pi, np.pi, n_rays, endpoint=False)
        xs = np.arange(-search_xy, search_xy + 1e-9, step_xy)
        ths = np.radians(np.arange(-search_th_deg, search_th_deg + 1e-9, step_th_deg))
        DX, DY, DT = np.meshgrid(xs, xs, ths, indexing="ij")
        self.off = np.stack([DX.ravel(), DY.ravel(), DT.ravel()], 1)
        self.prior = pull * np.hypot(self.off[:, 0], self.off[:, 1]) + 0.0004 * np.abs(np.degrees(self.off[:, 2]))      # weights chosen against the scan cost (about 0.04 for a 0.3 m error)
        self.cap = cap
        self.robot_id = m.body("robot").id
        self.gid = np.zeros(1, dtype=np.int32)

    def scan(self, d, true_pose):
        """Range readings (m, measured from the ray start; NaN = no hit within range)."""
        out = np.full(len(self.angles), np.nan)
        x, y, yaw = true_pose
        for i, a in enumerate(self.angles):
            th = yaw + a
            vec = np.array([np.cos(th), np.sin(th), 0.0])
            org = np.array([x + R_START * vec[0], y + R_START * vec[1], 0.06])
            r = mujoco.mj_ray(self.m, d, org, vec, GROUPS, 1, self.robot_id, self.gid)
            if 0 <= r <= R_MAX:
                out[i] = r
        return out

    @staticmethod
    def _trimmed(res, keep=0.8):
        """Mean of the best `keep` fraction of the ray residuals: things the map does not contain (her body, the vacuum) produce the worst
        residuals and must not pull the pose towards aligning them with mapped obstacles."""
        k = max(int(keep * res.shape[1]), 1)
        return np.partition(res, k - 1, axis=1)[:, :k].mean(1)

    def cost(self, est, ranges):
        ok = np.isfinite(ranges)
        if ok.sum() < 12:
            return None
        g = self.grid
        clear = g.clear_low                                          # the sensor sees table LEGS, not the table top: match against what it can see
        ang, rr = self.angles[ok], R_START + ranges[ok]
        # rays that the map cannot explain at the current estimate (her body, the vacuum, a door someone opened) would drag the pose towards
        # aligning THEM with mapped obstacles: when most rays agree with the map, leave the disagreeing ones out of the sum
        hx0, hy0 = est[0] + rr * np.cos(est[2] + ang), est[1] + rr * np.sin(est[2] + ang)
        r0 = clear[np.clip(((hx0 - g.bounds[0]) / g.res).astype(int), 0, g.nx - 1), np.clip(((hy0 - g.bounds[2]) / g.res).astype(int), 0, g.ny - 1)]
        inl = r0 < 0.30
        if inl.mean() >= 0.6 and inl.sum() >= 12:
            ang, rr = ang[inl], rr[inl]
        th = est[2] + self.off[:, 2][:, None] + ang[None, :]
        hx = est[0] + self.off[:, 0][:, None] + rr[None, :] * np.cos(th)
        hy = est[1] + self.off[:, 1][:, None] + rr[None, :] * np.sin(th)
        ix = np.clip(((hx - g.bounds[0]) / g.res).astype(int), 0, g.nx - 1)
        iy = np.clip(((hy - g.bounds[2]) / g.res).astype(int), 0, g.ny - 1)
        return np.minimum(clear[ix, iy], self.cap).mean(1) + self.prior

    def wide(self):
        """A second, wider search for recovery after a bump moved the robot more than the normal search covers."""
        if not hasattr(self, "_wide"):
            self._wide = Localizer(self.m, self.grid, n_rays=len(self.angles), search_xy=0.9, step_xy=0.1, search_th_deg=60.0, step_th_deg=6.0)
        return self._wide

    def global_search(self, est, ranges, step_xy=0.15, step_th_deg=10.0, pull=0.003):
        """Lost completely (a bump spun or shifted her by more than the wide search covers): score free-floor poses all over the flat at every
        heading (a weak pull towards the old estimate breaks ties), keep the best and refine it with the normal local search."""
        ok = np.isfinite(ranges)
        if ok.sum() < 12:
            return None
        g = self.grid
        if not hasattr(self, "_cand"):
            xs = np.arange(g.bounds[0] + 0.3, g.bounds[1] - 0.3, step_xy)
            ys = np.arange(g.bounds[2] + 0.3, g.bounds[3] - 0.3, step_xy)
            X, Y = np.meshgrid(xs, ys, indexing="ij")
            ix = ((X - g.bounds[0]) / g.res).astype(int)
            iy = ((Y - g.bounds[2]) / g.res).astype(int)
            free = g.clear[ix, iy] > 0.25
            self._cand = np.stack([X[free], Y[free]], 1)
        th = np.radians(np.arange(-180, 180, step_th_deg))
        ang = self.angles[ok]
        r_tot = R_START + ranges[ok]
        cands = []                                         # (cost, x, y, heading)
        for t0 in th:                                     # one heading at a time keeps the arrays small
            a = t0 + ang
            hx = self._cand[:, :1] + r_tot[None, :] * np.cos(a)[None, :]
            hy = self._cand[:, 1:] + r_tot[None, :] * np.sin(a)[None, :]
            ix = np.clip(((hx - g.bounds[0]) / g.res).astype(int), 0, g.nx - 1)
            iy = np.clip(((hy - g.bounds[2]) / g.res).astype(int), 0, g.ny - 1)
            c = self._trimmed(np.minimum(g.clear_low[ix, iy], self.cap)) + pull * np.hypot(*(self._cand - est[:2]).T)
            for k in np.argsort(c)[:4]:
                cands.append((c[k], self._cand[k, 0], self._cand[k, 1], t0))
        cands.sort()
        near = [c for c in cands if np.hypot(c[1] - est[0], c[2] - est[1]) < 1.5]       # the old estimate is usually not far off: always try the best nearby candidates too
        pool = cands[:10] + near[:10]
        best = (np.inf, None)
        zero = int(np.argmin(np.hypot(self.off[:, 0], self.off[:, 1]) + np.abs(self.off[:, 2])))
        for _, x, y, t0 in pool:                          # refine the best coarse candidates with the normal local search
            pose = np.array([x, y, t0])
            for _ in range(4):
                pose, _info = self.correct(pose, ranges)
            c = self.cost(pose, ranges)
            if c is not None:
                score = c[zero] + 0.004 * np.hypot(*(pose[:2] - est[:2]))        # among equally good fits prefer the one near where I thought I was
                if score < best[0]:
                    best = (score, pose, float(c[zero]))
        return None if best[1] is None else (best[1], best[2])

    def correct(self, est, ranges):
        c = self.cost(est, ranges)
        if c is None:
            return est, dict(applied=False, reason="too few range hits")
        k0 = int(np.argmin(np.hypot(self.off[:, 0], self.off[:, 1]) + np.abs(self.off[:, 2])))       # the zero offset
        kb = int(np.argmin(c))
        if kb == k0 or c[kb] > 0.85 * c[k0]:
            return est, dict(applied=False, reason="no clear improvement", cost=float(c[k0]))
        new = np.array([est[0] + self.off[kb, 0], est[1] + self.off[kb, 1], est[2] + self.off[kb, 2]])
        return new, dict(applied=True, shift_m=float(np.hypot(*self.off[kb, :2])), turn_deg=float(np.degrees(self.off[kb, 2])), cost_before=float(c[k0]), cost_after=float(c[kb]))
