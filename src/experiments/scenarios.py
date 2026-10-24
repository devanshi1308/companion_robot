"""
Seeded scenario generator for the experiment set.

    specs = make_specs("test", n_total=120, seed0=1000)       # list of plain dicts (JSON-serialisable)

Every spec fully determines a trial (her route, speed and event, floor friction, clutter, vacuum speed, robot start, sensor and
disturbance settings, whether she answers the check-in), so a trial can be re-run exactly and the robot and the static-camera baseline
see the same woman doing the same thing.

Mix (as sir's feedback sheet asks: falls AND daily-living activities):
  falls (positives):  trip, slip, syncope, cardiac (with pre-collapse behaviour)
  activities (hard negatives):  abrupt and slow sitting on the low sofa, lying down on the bed, tying shoelaces (squat), dropping keys
  (bending), sitting on the floor, lying on the floor (exercise)
"""
import os
import sys

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "sim"))
import apartment_layout as L  # noqa: E402
import motions as M  # noqa: E402

# mix per 120 trials (the dev split uses the same proportions at a third of the size)
MIX_120 = dict(trip=15, slip=15, syncope=15, cardiac=15, sit_sofa_abrupt=12, sit_sofa_slow=8, lie_bed=10, tie_shoelaces=10, drop_keys=10, sit_floor=5, lie_floor=5)
P_CONSCIOUS = dict(trip=0.65, slip=0.65, syncope=0.0, cardiac=0.0)       # she answers the check-in (if she is awake and able to)

ROUTE_SOFA = [(-2.2, -1.3), (-2.2, 0.55), (-1.0, 0.55), (M.SOFA_STAND[0], M.SOFA_STAND[1])]
ROUTE_BED = [(-2.2, -2.45), (2.0, -2.45), (2.0, 0.0), (M.BED_FOOT[0], M.BED_FOOT[1])]
FALL_ROUTES = ("bed_to_living", "living_to_bed", "bed_to_front_door", "hall_to_bedroom")
LONG_ROUTES = ("bed_to_living", "living_to_bed", "bed_to_front_door", "hall_to_bedroom")
ADL_ROUTES = dict(
    sit_sofa_abrupt=[ROUTE_SOFA], sit_sofa_slow=[ROUTE_SOFA], lie_bed=[ROUTE_BED],
    tie_shoelaces=[L.ROUTES["bed_to_front_door"], L.ROUTES["hall_to_bedroom"]],
    drop_keys=[L.ROUTES["living_to_dining"], L.ROUTES["bed_to_living"], L.ROUTES["hall_to_bedroom"]],
    sit_floor=[L.ROUTES["living_to_dining"], L.ROUTES["living_south_to_north"]],
    lie_floor=[L.ROUTES["living_to_dining"], L.ROUTES["living_south_to_north"]],
)


def _f(x):
    return float(x)


def _fall_spec(sub, rng, zone):
    """Events are spread evenly over the three zones (hallway, bedroom, open-plan living-dining) so that no condition is favoured by where she falls."""
    routes = FALL_ROUTES if sub != "cardiac" else LONG_ROUTES
    options = []
    for name in routes:
        path = np.asarray(L.ROUTES[name], float)
        ss = M.safe_arclengths(path)
        ss = ss[[L.zone_of(*L.path_xy(path, x)) == zone for x in ss]]
        if sub == "cardiac":
            ss = ss[ss > 4.0]                                  # room for the pre-collapse behaviour before it
        if len(ss):
            options.append((name, path, ss))
    name, path, ss = options[int(rng.integers(len(options)))]
    v = _f(rng.uniform(0.5, 0.9))
    s_ev = _f(rng.choice(ss))
    spec = dict(route=str(name), path=path.tolist(), speed=v, zone=zone)
    if sub == "cardiac":
        P = _f(rng.uniform(8.0, 14.0))
        while True:
            dist = v * (2.7 + 0.35 * (P - 4.0))                # distance walked during the pre-collapse behaviour
            t_p = (s_ev - dist) / v
            if t_p >= 0.3 or P <= 6.0:
                break
            P = max(6.0, P - 0.5)
        t_p = max(t_p, 0.3)
        spec.update(prodrome_start_s=_f(t_p), prodrome_s=P, chest_side=str(rng.choice(["left", "right"])),
                    omega=_f(rng.uniform(0.4, 0.9)), tau=_f(rng.uniform(0.08, 0.2)), side=_f(rng.choice([-1.0, 1.0])),
                    lateral=bool(rng.random() < 0.5))
        return spec
    spec["fall_s"] = s_ev
    if sub == "trip":
        spec.update(omega=_f(rng.uniform(1.5, 2.3)), tau=_f(rng.uniform(0.35, 0.55)))
    elif sub == "slip":
        spec.update(omega=_f(rng.uniform(1.2, 2.0)), tau=_f(rng.uniform(0.3, 0.5)))
    else:                                                       # syncope
        spec.update(omega=_f(rng.uniform(0.3, 0.8)), tau=_f(rng.uniform(0.08, 0.2)), side=_f(rng.choice([-1.0, 1.0])), lateral=bool(rng.random() < 0.5))
    return spec


def _adl_spec(sub, rng):
    routes = ADL_ROUTES[sub]
    path = np.asarray(routes[int(rng.integers(len(routes)))], float)
    hold = dict(sit_sofa_abrupt=(6, 20), sit_sofa_slow=(6, 20), lie_bed=(8, 25), tie_shoelaces=(6, 14), drop_keys=(1.5, 4.0), sit_floor=(6, 16), lie_floor=(6, 18))[sub]
    return dict(route="adl", path=path.tolist(), speed=_f(rng.uniform(0.5, 0.9)), hold_s=_f(rng.uniform(*hold)))


def make_specs(split, n_total=120, seed0=1000):
    """Seeded list of trial specs; the mix follows MIX_120 scaled to n_total (largest-remainder rounding), shuffled."""
    rng = np.random.default_rng(seed0)
    tot = sum(MIX_120.values())
    raw = {k: v * n_total / tot for k, v in MIX_120.items()}
    cnt = {k: int(np.floor(v)) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - cnt[k], reverse=True)[: n_total - sum(cnt.values())]:
        cnt[k] += 1
    order = [k for k, c in cnt.items() for _ in range(c)]
    rng.shuffle(order)
    n_falls = sum(1 for k in order if k in M.FALL_TYPES)
    zones = (["hallway", "bedroom", "living"] * (n_falls // 3 + 1))[:n_falls]          # stratified: the same number of falls in each zone (+-1)
    rng.shuffle(zones)
    zi = iter(zones)
    specs = []
    for i, sub in enumerate(order):
        seed = int(seed0 * 1000 + i)
        r = np.random.default_rng(seed)
        kind = "fall" if sub in M.FALL_TYPES else "adl"
        spec = dict(id=f"{split}_{i:03d}", split=split, seed=seed, kind=kind, subtype=sub)
        spec.update(_fall_spec(sub, r, next(zi)) if kind == "fall" else _adl_spec(sub, r))
        conscious = bool(r.random() < P_CONSCIOUS.get(sub, 1.0))
        spec.update(
            friction_scale=_f(r.uniform(0.75, 1.15)),
            n_clutter=int(r.choice([0, 4, 8])),
            vacuum_speed=_f(r.uniform(0.10, 0.50)), vacuum_phase=_f(r.uniform(0, 1)),
            odom_noise=_f(r.uniform(0.005, 0.03)),
            push=None if r.random() < 0.5 else dict(t=_f(r.uniform(3, 20)), force=_f(r.uniform(15.0, 40.0)),                    # a shove, scaled to the 16.5 kg robot (same impulse as 1.5-4 N on the old 1.2 kg one)
                angle=_f(r.uniform(0, 2 * np.pi)), dur=0.15),
            blackout=None if r.random() < 0.7 else dict(t=_f(r.uniform(2, 30)), dur=_f(r.uniform(0.5, 1.5))),
            conscious=conscious, reply_latency=_f(r.uniform(1.5, 6.5) if kind == "fall" else r.uniform(1.0, 4.0)),
            robot_start_mode=str(r.choice(["near", "far"], p=[0.65, 0.35])), robot_start_seed=int(r.integers(1 << 30)),
        )
        specs.append(spec)
    return specs
