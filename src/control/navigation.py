"""
Navigation for the small wheeled robot: occupancy map from the apartment model, A* planning,
pure-pursuit path following with a speed profile, and standoff-pose selection next to a person.

  grid = OccupancyGrid(model, data)                       # static obstacles from the MJCF (furniture, walls)
  path = grid.plan(start_xy, goal_xy, extra_discs=[...])  # list of (x, y); extra_discs = moving obstacles
  ctl  = PathFollower(path); v, w = ctl.command(pose, dt) # call at the control rate
  goal = grid.choose_standoff(person_xy, axis_xy, robot_xy)

Obstacles are any solid geom that reaches into the robot's height band (0.018 m to 0.19 m above the floor):
table tops and the sofa seat above that band do not block it, their legs do. Slippers (4 cm tall) are
obstacles; the 1.2 cm rug edge is not (measured climb limit about 1.9 cm, set by the small front caster).
"""
import heapq
import os
import sys

import mujoco
import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "robot"))
import robot_spec as S  # noqa: E402

SKIP_BODIES = {"robot", "robot_neck", "robot_head", "wheel_l", "wheel_r", "vacuum", "pelvis"}
HEIGHT_BAND = (0.018, 1.25)          # anything taller than 1.8 cm up to the top of the 1.10 m robot blocks it (tables, chairs, shelves: the mast would hit them)
LEVELS = (0.025, 0.07, 0.11, 0.15, 0.185, 0.30, 0.45, 0.60, 0.75, 0.90, 1.05, 1.20)    # heights at which obstacles are rasterised
CIRCUMRADIUS = S.CHASSIS_R            # robot footprint radius (robot_spec): about 0.30 m for the guide's robot


def _inside(m, d, g, pts, pad=0.0):
    """Boolean mask: which world points (N,3) lie inside geom g. `pad` grows the footprint horizontally only
    (conservative rasterisation, so thin legs narrower than a grid cell are not missed)."""
    t = m.geom_type[g]
    size = m.geom_size[g].copy()
    loc = (pts - d.geom_xpos[g]) @ d.geom_xmat[g].reshape(3, 3)
    if t == mujoco.mjtGeom.mjGEOM_BOX:
        size[:2] += pad
        return (np.abs(loc) <= size).all(1)
    if t == mujoco.mjtGeom.mjGEOM_CYLINDER:
        return (np.hypot(loc[:, 0], loc[:, 1]) <= size[0] + pad) & (np.abs(loc[:, 2]) <= size[1])
    if t == mujoco.mjtGeom.mjGEOM_SPHERE:
        return np.linalg.norm(loc, axis=1) <= size[0] + pad
    if t == mujoco.mjtGeom.mjGEOM_CAPSULE:
        z = np.clip(loc[:, 2], -size[1], size[1])
        return np.linalg.norm(loc - np.stack([0 * z, 0 * z, z], 1), axis=1) <= size[0] + pad
    return np.zeros(len(pts), bool)


class OccupancyGrid:
    def __init__(self, m, d, res=0.05, bounds=(-3.7, 3.7, -3.2, 3.2), margin=0.045):
        self.res, self.bounds = res, bounds
        self.nx = int(round((bounds[1] - bounds[0]) / res))
        self.ny = int(round((bounds[3] - bounds[2]) / res))
        xs = bounds[0] + (np.arange(self.nx) + 0.5) * res
        ys = bounds[2] + (np.arange(self.ny) + 0.5) * res
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        self.X, self.Y = X, Y
        occ = np.zeros((self.nx, self.ny), bool)
        occ_low = np.zeros((self.nx, self.ny), bool)                # what the 6 cm-high range sensor can see (legs, walls, low furniture, clutter): used for localisation
        mujoco.mj_forward(m, d)
        for g in range(m.ngeom):
            if not (m.geom_contype[g] or m.geom_conaffinity[g]) or m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE:
                continue
            body = m.body(m.geom_bodyid[g]).name
            name = m.geom(g).name or ""
            if body in SKIP_BODIES or name.startswith("floor_") or m.geom_bodyid[g] in self._human_bodies(m):
                continue
            R_, size_ = np.abs(d.geom_xmat[g].reshape(3, 3)), m.geom_size[g]
            half_z = {int(mujoco.mjtGeom.mjGEOM_BOX): R_[2] @ size_, int(mujoco.mjtGeom.mjGEOM_CYLINDER): size_[0] * np.hypot(R_[2, 0], R_[2, 1]) + size_[1] * R_[2, 2],
                      int(mujoco.mjtGeom.mjGEOM_SPHERE): size_[0], int(mujoco.mjtGeom.mjGEOM_CAPSULE): size_[0] + size_[1] * R_[2, 2]}.get(int(m.geom_type[g]), 0.0)     # (int keys: the enum and the numpy int do not hash alike)
            zc_ = d.geom_xpos[g][2]
            zs = sorted({round(zc_, 3)} | {z for z in LEVELS if zc_ - half_z <= z <= zc_ + half_z})     # the geom's own centre height catches thin slabs (table tops) between the levels
            for z in zs:
                if z < HEIGHT_BAND[0] or z > HEIGHT_BAND[1]:
                    continue
                pts = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], 1)
                hit = _inside(m, d, g, pts, pad=res * 0.71).reshape(occ.shape)
                occ |= hit
                if z <= 0.11:
                    occ_low |= hit
        # cells under table tops, shelves etc. (something overhead between the robot's top and 1.2 m): passable but not preferred
        over = np.zeros((self.nx, self.ny), bool)
        for g in range(m.ngeom):
            if not (m.geom_contype[g] or m.geom_conaffinity[g]) or m.geom_type[g] in (mujoco.mjtGeom.mjGEOM_PLANE,):
                continue
            body = m.body(m.geom_bodyid[g]).name
            if body in SKIP_BODIES or (m.geom(g).name or "").startswith(("floor_", "wall_")) or m.geom_bodyid[g] in self._human_bodies(m):
                continue
            R, size = np.abs(d.geom_xmat[g].reshape(3, 3)), m.geom_size[g]
            half_z = {int(mujoco.mjtGeom.mjGEOM_BOX): R[2] @ size, int(mujoco.mjtGeom.mjGEOM_CYLINDER): size[0] * np.hypot(R[2, 0], R[2, 1]) + size[1] * R[2, 2],
                      int(mujoco.mjtGeom.mjGEOM_SPHERE): size[0], int(mujoco.mjtGeom.mjGEOM_CAPSULE): size[0] + size[1] * R[2, 2]}.get(int(m.geom_type[g]))
            if half_z is None:
                continue
            zc = d.geom_xpos[g][2]
            if HEIGHT_BAND[1] <= zc - half_z <= 1.2:
                pts = np.stack([X.ravel(), Y.ravel(), np.full(X.size, zc)], 1)
                over |= _inside(m, d, g, pts, pad=res * 0.71).reshape(over.shape)
        self.overhead = over
        # outside the apartment is blocked
        occ[(X < -3.5) | (X > 3.5) | (Y < -3.0) | (Y > 3.0)] = True
        self.occ = occ
        occ_low[(X < -3.5) | (X > 3.5) | (Y < -3.0) | (Y > 3.0)] = True
        self.clear_low = distance_transform_edt(~occ_low) * res      # distance to the nearest thing the range sensor can see
        self.clear = distance_transform_edt(~occ) * res            # distance to the nearest obstacle (m)
        self.r_infl = CIRCUMRADIUS + margin

    @staticmethod
    def _human_bodies(m):
        cache = getattr(OccupancyGrid, "_hb", None)
        if cache is None or cache[0] is not m:
            ids = set()
            try:
                root = m.body("pelvis").id
                for b in range(m.nbody):
                    a = b
                    while a > 0 and a != root:
                        a = m.body_parentid[a]
                    if a == root:
                        ids.add(b)
            except KeyError:
                pass
            OccupancyGrid._hb = (m, ids)
        return OccupancyGrid._hb[1]

    # ---- coordinates ------------------------------------------------------------------------
    def to_cell(self, x, y):
        return (int(np.clip((x - self.bounds[0]) / self.res, 0, self.nx - 1)), int(np.clip((y - self.bounds[2]) / self.res, 0, self.ny - 1)))

    def to_xy(self, i, j):
        return (self.bounds[0] + (i + 0.5) * self.res, self.bounds[2] + (j + 0.5) * self.res)

    def blocked(self, extra_discs=(), avoid_overhead=True):
        blk = self.clear < self.r_infl
        if avoid_overhead:
            blk = blk | self.overhead                       # never drive under tables and shelves
        for (x, y, r) in extra_discs:
            blk |= np.hypot(self.X - x, self.Y - y) < (r + self.r_infl)
        return blk

    def is_free(self, x, y, extra_discs=()):
        i, j = self.to_cell(x, y)
        return not self.blocked(extra_discs)[i, j]

    # ---- planning ---------------------------------------------------------------------------
    def plan(self, start, goal, extra_discs=()):
        """A* on the inflated grid (8-connected, prefers clearance). Returns [(x, y), ...] or None."""
        blk = self.blocked(extra_discs)
        s, g = self.to_cell(*start), self.to_cell(*goal)
        s, g = self._nearest_free(blk, s), self._nearest_free(blk, g)
        if s is None or g is None:
            return None
        pen = 1.0 + 1.5 * np.clip((0.45 - self.clear) / 0.45, 0, 1) + 3.0 * self.overhead     # stay away from walls and furniture; avoid driving under tables
        moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        h = lambda c: np.hypot(c[0] - g[0], c[1] - g[1])
        openq, came, cost = [(h(s), 0.0, s)], {}, {s: 0.0}
        while openq:
            _, c, cur = heapq.heappop(openq)
            if cur == g:
                break
            if c > cost.get(cur, 1e9):
                continue
            for di, dj, w in moves:
                n = (cur[0] + di, cur[1] + dj)
                if not (0 <= n[0] < self.nx and 0 <= n[1] < self.ny) or blk[n]:
                    continue
                if di and dj and (blk[cur[0] + di, cur[1]] or blk[cur[0], cur[1] + dj]):
                    continue                                                   # no corner cutting
                nc = c + w * pen[n]
                if nc < cost.get(n, 1e9):
                    cost[n], came[n] = nc, cur
                    heapq.heappush(openq, (nc + h(n), nc, n))
        if g not in came and g != s:
            return None
        cells = [g]
        while cells[-1] != s:
            cells.append(came[cells[-1]])
        cells.reverse()
        pts = [self.to_xy(*c) for c in cells]
        pts = self._shortcut(blk, pts)
        pts[0] = tuple(start[:2])
        return pts

    def _nearest_free(self, blk, c, radius=20):
        if not blk[c]:
            return c
        best, bd = None, 1e9
        for di in range(-radius, radius + 1):
            for dj in range(-radius, radius + 1):
                n = (c[0] + di, c[1] + dj)
                if 0 <= n[0] < self.nx and 0 <= n[1] < self.ny and not blk[n] and di * di + dj * dj < bd:
                    best, bd = n, di * di + dj * dj
        return best

    def _line_free(self, blk, a, b):
        n = max(2, int(np.hypot(b[0] - a[0], b[1] - a[1]) / (self.res * 0.5)))
        for t in np.linspace(0, 1, n):
            if blk[self.to_cell(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))]:
                return False
        return True

    def _shortcut(self, blk, pts):
        out, i = [pts[0]], 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1 and not self._line_free(blk, pts[i], pts[j]):
                j -= 1
            out.append(pts[j])
            i = j
        return out

    # ---- one search from the robot to every cell -------------------------------------------------
    def _dijkstra(self, blk, s):
        pen = 1.0 + 1.5 * np.clip((0.45 - self.clear) / 0.45, 0, 1) + 3.0 * self.overhead
        moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        cost = np.full((self.nx, self.ny), np.inf)
        parent = {}
        cost[s] = 0.0
        q = [(0.0, s)]
        while q:
            c, cur = heapq.heappop(q)
            if c > cost[cur]:
                continue
            for di, dj, w in moves:
                n = (cur[0] + di, cur[1] + dj)
                if not (0 <= n[0] < self.nx and 0 <= n[1] < self.ny) or blk[n]:
                    continue
                if di and dj and (blk[cur[0] + di, cur[1]] or blk[cur[0], cur[1] + dj]):
                    continue
                nc = c + w * pen[n]
                if nc < cost[n]:
                    cost[n], parent[n] = nc, cur
                    heapq.heappush(q, (nc, n))
        return cost, parent

    # ---- standoff next to a person ----------------------------------------------------------
    def choose_standoff(self, person_xy, axis_xy, robot_xy, body_xy=None, radius=S.STANDOFF + 0.1, extra_discs=(), clearance_min=0.9):
        """Pick a free pose about `radius` from the nearest part of her body (standards: 0.8 to 1.2 m, never touching),
        preferring the side of her body axis (best view for the pose estimator) and a short drive.
        body_xy: (N, 2) estimated positions of her body points; falls back to the hip. Returns (x, y, heading, path) or None."""
        px, py = person_xy
        pts = np.array(body_xy) if body_xy is not None and len(body_xy) else np.array([[px, py]])
        ax = np.arctan2(axis_xy[1], axis_xy[0])
        blk = self.blocked(extra_discs)
        start = self._nearest_free(blk, self.to_cell(*robot_xy))
        if start is None:
            return None
        cost, parent = self._dijkstra(blk, start)
        best = None
        for r in (radius, radius + 0.25, radius + 0.5, radius + 0.9, radius + 1.4):          # rings around her hip
            for ang in np.radians(np.arange(0, 360, 10)):
                x, y = px + r * np.cos(ang), py + r * np.sin(ang)
                c = self.to_cell(x, y)
                if blk[c] or not np.isfinite(cost[c]):
                    continue
                d_near = float(np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y)))
                if d_near < clearance_min:
                    continue
                off_side = abs(np.sin(ang - ax))
                score = cost[c] * self.res + 2.5 * (1.0 - off_side) + 5.0 * abs(d_near - radius)
                if best is None or score < best[0]:
                    best = (score, x, y, c)
        if best is None:
            return None
        _, x, y, c = best
        cells = [c]
        while cells[-1] != start:
            cells.append(parent[cells[-1]])
        cells.reverse()
        path = self._shortcut(blk, [self.to_xy(*k) for k in cells])
        path[0] = tuple(robot_xy[:2])
        return x, y, float(np.arctan2(py - y, px - x)), path


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class PathFollower:
    """Pure pursuit with a trapezoidal speed profile (cruise V_MAX, comfort deceleration, slower in turns)."""

    def __init__(self, path, v_max=S.V_MAX, a=S.A_COMFORT, lookahead=0.20, tol=0.06, v0=0.0):
        self.path = [np.array(p, float) for p in path]
        self.v_max, self.a, self.ld, self.tol = v_max, a, lookahead, tol
        self.v_cmd = float(v0)
        self.w_cmd = 0.0
        self.i = 0
        self.done = False

    def remaining(self, pos):
        d = np.hypot(*(self.path[min(self.i + 1, len(self.path) - 1)] - pos))
        for a, b in zip(self.path[self.i + 1:], self.path[self.i + 2:]):
            d += np.hypot(*(b - a))
        return d

    def _corner_ahead(self, pos):
        """Distance along the path to the next sharp turn (more than 35 degrees), or a large number."""
        d = float(np.hypot(*(self.path[min(self.i + 1, len(self.path) - 1)] - pos)))
        for k in range(self.i + 1, len(self.path) - 1):
            a, b, c = self.path[k - 1], self.path[k], self.path[k + 1]
            v1, v2 = b - a, c - b
            if np.hypot(*v1) < 1e-6 or np.hypot(*v2) < 1e-6:
                continue
            turn = abs(wrap(np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])))
            if turn > np.radians(35):
                return d
            d += float(np.hypot(*v2))
        return 9.0

    def command(self, pose, dt, stop=False):
        """pose = (x, y, yaw) estimate. Returns (v, w). `stop` brakes at the emergency rate."""
        pos = np.array(pose[:2])
        end = self.path[-1]
        if np.hypot(*(end - pos)) < self.tol:
            self.done = True                                  # arrived (independent of the safety brake)
        while self.i < len(self.path) - 2 and np.hypot(*(self.path[self.i + 1] - pos)) < self.ld * 0.8:
            self.i += 1
        # lookahead point along the path
        target = end
        for k in range(self.i, len(self.path) - 1):
            a, b = self.path[k], self.path[k + 1]
            if np.hypot(*(b - pos)) >= self.ld:
                seg = b - a
                tt = np.clip(np.dot(pos - a, seg) / max(np.dot(seg, seg), 1e-9), 0, 1)
                near = a + tt * seg
                target = near + seg / max(np.hypot(*seg), 1e-9) * self.ld
                if np.hypot(*(target - a)) > np.hypot(*seg):
                    target = b
                break
        alpha = wrap(np.arctan2(target[1] - pos[1], target[0] - pos[0]) - pose[2])
        corner = self._corner_ahead(pos)
        v_goal = self.v_max * max(0.25, np.cos(alpha)) if abs(alpha) < np.radians(75) else 0.0
        v_goal = min(v_goal, 0.18 + 0.5 * corner) if corner < 0.5 else v_goal           # ease off before a sharp turn (doorways)
        v_goal = min(v_goal, np.sqrt(2 * self.a * max(self.remaining(pos), 0.0)))      # brake into the goal
        if self.done or stop:
            v_goal = 0.0
        rate = (S.A_EMERGENCY if stop else self.a) * dt
        self.v_cmd += np.clip(v_goal - self.v_cmd, -rate * 1.0 if stop else -self.a * dt, self.a * dt)
        if stop:
            self.v_cmd = max(0.0, self.v_cmd - (S.A_EMERGENCY - self.a) * dt)
        w = 2.0 * alpha if abs(alpha) > np.radians(75) else 2 * max(self.v_cmd, 0.15) * np.sin(alpha) / self.ld
        # no bang-bang steering: the yaw rate is slew-limited and, while driving, capped; fast turns at speed made the small wheels skid
        # and the odometry lose 45 degrees in a second (found in the dev split)
        w_max = 1.8 if self.v_cmd < 0.15 else 1.2
        w = float(np.clip(w, -w_max, w_max))
        self.w_cmd += float(np.clip(w - self.w_cmd, -6.0 * dt, 6.0 * dt))
        if abs(self.w_cmd) > 0.6:
            self.v_cmd = min(self.v_cmd, 0.5 / abs(self.w_cmd))                      # centripetal acceleration v*w kept below 0.5 m/s2
        return float(self.v_cmd), float(self.w_cmd)


def turn_to(pose, heading, k=2.0, w_max=1.5):
    """Spin-in-place command towards a heading; returns (w, error)."""
    e = wrap(heading - pose[2])
    return float(np.clip(k * e, -w_max, w_max)), float(e)
