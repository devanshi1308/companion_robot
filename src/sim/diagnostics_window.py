"""
Diagnostics window shown beside the MuJoCo viewer: the three result graphs of the pitch video (dispatch share,
detection by room, time to dispatch) plus a live plan of the flat with the robot and her moving.

It runs as its own process so it does not fight the MuJoCo viewer for the main thread.
run_demo.py --view starts it and appends one JSON line per telemetry sample to <out>/live_diagnostics.jsonl.

Run alone:   python src/sim/diagnostics_window.py --live outputs/demo_run/live_diagnostics.jsonl
Replay:      python src/sim/diagnostics_window.py --replay outputs/demo_run/telemetry.csv [--save fig.png]
"""
import argparse
import csv
import json
import os
import sys

import matplotlib
import matplotlib.patches

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RUN = os.path.join(ROOT, "results", "guide_robot_test")

COLORS = {"WATCH": "#9aa5b1", "FOLLOW": "#2b5fd9", "SEARCH": "#e08a1e", "OBSERVE": "#8e44ad", "SUSPECT": "#d6453d",
          "APPROACH": "#d6453d", "CHECK_IN": "#e0b01e", "ALERT": "#b01e1e"}
SYS = [("robot", "companion robot", "#2a7ab5"), ("static", "1 fixed camera", "#c0602a"), ("static4", "4 fixed cameras", "#7a9a3a")]
KEYS = ("t", "state", "human_hip_z", "x", "y", "yaw", "est_x", "est_y", "human_x", "human_y")


def read_live(path, pos, rows, events):
    """Read new lines from the JSONL file since byte offset pos; returns the new offset."""
    if not os.path.exists(path):
        return pos
    with open(path, "r") as f:
        f.seek(pos)
        while True:
            line = f.readline()
            if not line or not line.endswith("\n"):
                break
            pos = f.tell()
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if "event" not in o:
                o = {k: (float("nan") if v is None else v) for k, v in o.items()}
            (events if "event" in o else rows).append(o)
    return pos


def read_replay(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            row = {}
            for k in KEYS:
                v = r.get(k, "")
                try:
                    row[k] = float(v) if k != "state" else v
                except ValueError:
                    row[k] = float("nan")
            rows.append(row)
    return rows


def load_results():
    """Everything the three graphs show, read from the saved 120-trial test run."""
    m = json.load(open(os.path.join(RUN, "metrics.json")))
    dispatch = {k: (m[f"dispatch_{k}"]["TP"], m[f"dispatch_{k}"]["TP"] + m[f"dispatch_{k}"]["FN"]) for k, _, _ in SYS}
    zone = {}
    for r in csv.DictReader(open(os.path.join(RUN, "tables", "by_zone.csv"))):
        zone[(r["condition"], r["zone"])] = int(r["alarm"]) / int(r["n"])
    lat = {k: [] for k, _, _ in SYS}
    n_silent = {k: 0 for k, _, _ in SYS}
    for r in csv.DictReader(open(os.path.join(RUN, "tables", "all_trials.csv"))):
        if r["needs_help"] == "True" and r["condition"] in lat:
            n_silent[r["condition"]] += 1
            if r["lat_dispatch"] not in ("", "nan"):
                lat[r["condition"]].append(float(r["lat_dispatch"]))
    return dict(dispatch=dispatch, zone=zone, lat=lat, n_silent=n_silent)


def draw_dispatch(a, res):
    vals = [res["dispatch"][k][0] / res["dispatch"][k][1] for k, _, _ in SYS]
    a.bar(range(3), vals, color=[c for _, _, c in SYS], width=0.6)
    for i, (k, _, _) in enumerate(SYS):
        tp, n = res["dispatch"][k]
        a.text(i, vals[i] + 0.02, f"{vals[i]:.0%}\n{tp} of {n}", ha="center", fontsize=6.5)
    a.set_xticks(range(3))
    a.set_xticklabels(["companion\nrobot", "1 fixed\ncamera", "4 fixed\ncameras"], fontsize=6)
    a.set_ylim(0, 0.95)
    a.set_title("Unanswered falls that triggered a dispatch", fontsize=7.5)


def draw_zone(a, res):
    zones = ["living", "hallway", "bedroom"]
    w = 0.27
    for j, (k, name, c) in enumerate(SYS):
        a.bar([i + (j - 1) * w for i in range(3)], [res["zone"][(k, z)] for z in zones], w, color=c, label=name)
    a.set_xticks(range(3))
    a.set_xticklabels(zones, fontsize=6.5)
    a.set_ylim(0, 1.1)
    a.set_ylabel("fraction of falls detected", fontsize=6)
    a.set_title("Coverage across rooms", fontsize=7.5)
    a.legend(fontsize=5.5, loc="upper right", frameon=False)


def draw_cdf(a, res):
    for k, name, c in SYS:
        xs = sorted(res["lat"][k])
        n = res["n_silent"][k]
        a.step([0.0] + xs + [110.0], [0.0] + [(i + 1) / n for i in range(len(xs))] + [len(xs) / n], where="post", color=c, label=name, lw=1.6)
    a.axvline(60, color="#777", ls=":", lw=1)
    a.set_xlim(0, 110)
    a.set_ylim(0, 1.0)
    a.set_xlabel("time from fall to dispatch (s)", fontsize=6.5)
    a.set_ylabel("fraction of silent falls dispatched", fontsize=6)
    a.set_title("Time to dispatch (dotted line = 60 s)", fontsize=7.5)
    a.legend(fontsize=5.5, loc="upper left", frameon=False)


def draw_plan(a):
    """Static floor plan (walls, doors, her walking route, the vacuum loop) of the 7 x 6 m flat."""
    import numpy as np
    sys.path.insert(0, os.path.join(ROOT, "src", "sim"))
    import apartment_layout as L
    a.clear()
    a.set_aspect("equal")
    a.set_xlim(L.X0 - 0.2, L.X1 + 0.2)
    a.set_ylim(L.Y0 - 0.2, L.Y1 + 0.2)
    for name, (x0, x1, y0, y1), _, _ in L.FLOORS:
        a.add_patch(matplotlib.patches.Rectangle((x0, y0), x1 - x0, y1 - y0, color={"hardwood": "#e9dcc3", "laminate": "#dfe3e8", "carpet": "#d8e6d4"}[name], lw=0))
    kw = dict(color="#333", lw=2)
    a.plot([L.X0, L.X1, L.X1, L.X0, L.X0], [L.Y0, L.Y0, L.Y1, L.Y1, L.Y0], **kw)
    gaps = sorted([(L.DOOR_LIVING[0] - L.DOOR_LIVING[1] / 2, L.DOOR_LIVING[0] + L.DOOR_LIVING[1] / 2),
                   (L.DOOR_BEDROOM[0] - L.DOOR_BEDROOM[1] / 2, L.DOOR_BEDROOM[0] + L.DOOR_BEDROOM[1] / 2)])
    xs = [L.X0] + [v for g in gaps for v in g] + [L.X1]
    for i in range(0, len(xs), 2):
        a.plot([xs[i], xs[i + 1]], [L.HALL_Y, L.HALL_Y], **kw)
    a.plot([L.PART_X, L.PART_X], [L.HALL_Y, L.Y1], **kw)
    a.plot(L.WALK_PATH[:, 0], L.WALK_PATH[:, 1], color="#2aa66a", lw=1, ls="--", alpha=0.8)
    a.plot(np.append(L.VACUUM_LOOP[:, 0], L.VACUUM_LOOP[0, 0]), np.append(L.VACUUM_LOOP[:, 1], L.VACUUM_LOOP[0, 1]), color="#999", lw=0.8, ls=":")
    rx, ry = L.RUG_CENTER
    a.add_patch(matplotlib.patches.Rectangle((rx - L.RUG_HALF[0], ry - L.RUG_HALF[1]), 2 * L.RUG_HALF[0], 2 * L.RUG_HALF[1], fill=False, ec="#b07", lw=0.8, ls=":"))
    a.set_xticks([])
    a.set_yticks([])
    for nm, (tx, ty) in (("hallway", (0.0, -2.75)), ("living / dining", (-1.5, 2.75)), ("bedroom", (2.1, 2.75))):
        a.text(tx, ty, nm, ha="center", fontsize=6, color="#555")


def draw_map(a, rows, plan):
    for art in plan["dyn"]:
        art.remove()
    plan["dyn"].clear()
    if not rows:
        return
    import numpy as np
    r = rows[-1]
    plan["dyn"] += a.plot([q.get("x", float("nan")) for q in rows], [q.get("y", float("nan")) for q in rows], color="#2b5fd9", lw=1.2, alpha=0.6)
    plan["dyn"] += a.plot([q.get("human_x", float("nan")) for q in rows], [q.get("human_y", float("nan")) for q in rows], color="#2aa66a", lw=1, alpha=0.5)
    down = r.get("human_hip_z", 1.0) < 0.45
    plan["dyn"] += a.plot([r.get("human_x", float("nan"))], [r.get("human_y", float("nan"))], marker="o", ms=11, color="#d6453d" if down else "#2aa66a", mec="black")
    plan["dyn"] += a.plot([r.get("est_x", float("nan"))], [r.get("est_y", float("nan"))], marker="o", ms=9, mfc="none", mec="#e08a1e")
    x, y, yaw = r.get("x", 0.0), r.get("y", 0.0), r.get("yaw", 0.0)
    plan["dyn"] += a.plot([x], [y], marker="o", ms=10, color=COLORS.get(r.get("state", "WATCH"), "#2b5fd9"), mec="black")
    plan["dyn"].append(a.annotate("", xy=(x + 0.5 * np.cos(yaw), y + 0.5 * np.sin(yaw)), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5)))
    a.set_title(f"Flat plan  t = {r['t']:.1f} s  {r.get('state', '')}", fontsize=7.5, weight="bold")
    a.set_xlabel("disc = robot; green/red disc = her (red = on floor);\norange ring = robot's own position estimate", fontsize=5.5)


def build_figure():
    """Sized for half of a 1280 x 832 pt screen (MuJoCo viewer on the left, this window on the right)."""
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 6.5, "axes.titlesize": 7.5, "axes.titlepad": 3, "xtick.labelsize": 6, "ytick.labelsize": 6})
    fig = plt.figure(figsize=(6.3, 7.4), dpi=100)
    fig.suptitle("Baymax: results from 120 simulated trials, and the live run", fontsize=9.5, y=0.992)
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1.15, 1.7], hspace=0.5, wspace=0.28, left=0.085, right=0.975, top=0.94, bottom=0.05)
    res = load_results()
    draw_dispatch(fig.add_subplot(gs[0, 0]), res)
    draw_zone(fig.add_subplot(gs[0, 1]), res)
    cdf = fig.add_subplot(gs[1, :])
    draw_cdf(cdf, res)
    ax = dict(cdf=cdf, map=fig.add_subplot(gs[2, 0]), log=fig.add_subplot(gs[2, 1]), plan=dict(dyn=[]), cursor=[])
    draw_plan(ax["map"])
    return fig, ax


def draw_live(ax, rows, events):
    if not rows:
        return
    draw_map(ax["map"], rows, ax["plan"])
    for art in ax["cursor"]:                                       # live marker on the time-to-dispatch graph: seconds since she reached the floor
        art.remove()
    ax["cursor"].clear()
    t_floor = next((r["t"] for r in rows if r.get("human_hip_z", 1.0) < 0.20), None)
    if t_floor is not None:
        since = min(rows[-1]["t"] - t_floor, 110)
        ax["cursor"].append(ax["cdf"].axvline(since, color="#d6453d", lw=1.4))
        ax["cursor"].append(ax["cdf"].text(since + (1 if since < 60 else -1), 0.70, f"this run: {since:.0f} s since the fall", ha="left" if since < 60 else "right", fontsize=6, color="#d6453d"))
    a = ax["log"]
    a.clear()
    a.axis("off")
    last = events[-14:]
    text = "\n".join(f"{e['t']:6.1f}s {e['event'][:36]}" for e in last) or "waiting for events"
    a.set_title("Events", fontsize=7.5)
    a.text(0.0, 1.0, text, va="top", fontsize=5.6, family="monospace", transform=a.transAxes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", help="JSONL file written by run_demo.py --view")
    ap.add_argument("--replay", help="telemetry.csv of a finished run")
    ap.add_argument("--save", help="save the figure as PNG and exit (replay only)")
    a = ap.parse_args()
    if a.save:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    fig, ax = build_figure()
    if a.replay:
        draw_live(ax, read_replay(a.replay), [])
        if a.save:
            fig.savefig(a.save, dpi=130)
            return
        plt.show()
        return
    rows, events, state = [], [], {"pos": 0}

    def tick(_):
        state["pos"] = read_live(a.live, state["pos"], rows, events)
        draw_live(ax, rows, events)
    anim = FuncAnimation(fig, tick, interval=200, cache_frame_data=False)  # noqa: F841
    plt.show()


if __name__ == "__main__":
    main()
