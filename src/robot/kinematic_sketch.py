"""
Kinematic sketch of the companion robot (the research guide's robot), drawn to scale from robot_spec.py.

    python src/robot/kinematic_sketch.py        ->  outputs/robot_kinematic_sketch.png

Panels: side view (mast, camera, field of view, centre of mass, blind zone), top view (chassis, wheels, casters, footprint), joint table, and the numbers
the guide asks for (tipping and slip limits). Joints: J1/J2 driven wheels (differential drive), J3 neck pan, J4 head tilt, two passive casters.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Polygon, Rectangle, Wedge  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "outputs", "robot_kinematic_sketch.png")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import robot_spec as S  # noqa: E402

INK, SOFT, BLUE, GREEN, RED, CYAN, AMBER = "#2b2f36", "#aeb4bd", "#2f6fdd", "#2aa66a", "#d6453d", "#35e0e8", "#ffb000"


def rbox(ax, cx, cy, w, h, fc, ec=INK, r=0.01, lw=1.4, z=2):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, zorder=z))


def joint(ax, x, y, color, size=0.014):
    ax.add_patch(Circle((x, y), size, fc=color, ec="white", lw=1.2, zorder=8))


def com_height():
    """Centre of mass from the same masses and heights the model uses."""
    m = S.MASS
    parts = [(m["deck"], S.DECK_Z0 + S.DECK_T / 2), (m["wheels"], S.WHEEL_R), (m["casters"], S.CASTER_R), (m["pedestal"], S.DECK_Z0 + S.DECK_T + S.PED_H / 2),
             (m["neck"], S.NECK_Z), (m["head"], S.HEAD_Z)]
    return sum(a * b for a, b in parts) / sum(a for a, _ in parts)


def side_view(ax):
    ax.set_title("Side view (to scale)", fontsize=11, weight="bold")
    ax.axhline(0, color=SOFT, lw=2)
    rbox(ax, 0, S.DECK_Z0 + S.DECK_T / 2, S.DECK_L, S.DECK_T, "#4a4f59", r=0.012)                       # chassis
    ax.add_patch(Circle((0, S.WHEEL_R), S.WHEEL_R, fc="#222", ec=INK, lw=1.4, zorder=3))                # driven wheel
    ax.add_patch(Circle((0, S.WHEEL_R), 0.012, fc=GREEN, ec="white", zorder=4))
    for sx in (-1, 1):
        ax.add_patch(Circle((sx * S.CASTER_X, S.CASTER_R), S.CASTER_R, fc="#8a8f98", ec=INK, lw=1.2, zorder=3))
    ax.add_patch(Rectangle((-0.02, S.DECK_Z0 + S.DECK_T), 0.04, S.PED_H, fc="#6b7078", ec=INK, lw=1.2, zorder=2))   # mast tube
    joint(ax, 0, S.NECK_Z, BLUE)                                                                          # J3 pan axis
    joint(ax, 0, S.TILT_Z, BLUE)                                                                          # J4 tilt axis
    prof = S.BELL_PROFILE
    pts = [(-0.02 + 0.95 * r, z) for z, r in prof] + [(-0.02 - 0.95 * r, z) for z, r in reversed(prof)]
    ax.add_patch(Polygon(pts, closed=True, fc="#eeeef2", ec=INK, lw=1.2, alpha=0.9, zorder=1))               # soft egg body shell (visual only)
    ax.plot([-0.04, -0.23], [0.82, 0.50], color="#eeeef2", lw=9, solid_capstyle="round", zorder=0.5)          # arm shell (visual only, fixed)
    ax.plot([-0.04, -0.23], [0.82, 0.50], color=INK, lw=11, solid_capstyle="round", zorder=0.4)
    ax.add_patch(Ellipse((0.0, S.HEAD_Z), 2 * S.HEAD_SHELL[0], 2 * S.HEAD_SHELL[2], fc="#eeeef2", ec=INK, lw=1.4, zorder=4))          # round head shell
    ax.add_patch(Circle((0.139, S.HEAD_Z), 0.016, fc=INK, ec="none", zorder=6))                           # an eye (dot)
    cam_x, cam_z = S.CAM_X, S.CAM_Z
    ax.add_patch(Circle((cam_x, cam_z), 0.008, fc=RED, ec="white", zorder=9))
    for a in (-S.FOVY / 2, S.FOVY / 2):                                                                    # field of view (camera level)
        ax.plot([cam_x, cam_x + 2.2 * np.cos(np.radians(a))], [cam_z, cam_z + 2.2 * np.sin(np.radians(a))], color=RED, lw=1, ls="--", zorder=1)
    ax.add_patch(Wedge((cam_x, cam_z), 2.2, -S.FOVY / 2, S.FOVY / 2, fc=RED, alpha=0.07, zorder=0))
    # camera tilted fully down (guide: -45 deg): blind zone on the floor
    a_dn = np.radians(S.TILT_RANGE_DEG[0] - S.FOVY / 2)
    blind = cam_z / np.tan(-a_dn)
    ax.plot([cam_x, cam_x + blind], [cam_z, 0], color=AMBER, lw=1.6, zorder=1)
    ax.text(cam_x + blind + 0.03, 0.04, f"blind zone {blind:.2f} m\n(tilt -45 deg)", fontsize=8, color="#b07d00", weight="bold")
    zc = com_height()
    ax.plot([0], [zc], marker="o", color="white", mec=INK, ms=9, zorder=10)
    ax.text(0.07, zc, f"CoM {zc:.3f} m", fontsize=8.5, weight="bold", va="center")
    ax.annotate("", xy=(-0.30, 0), xytext=(-0.30, cam_z), arrowprops=dict(arrowstyle="<->", color=INK))
    ax.text(-0.33, cam_z / 2, f"camera {cam_z:.2f} m", rotation=90, fontsize=9, weight="bold", va="center", ha="right")
    ax.text(0.16, S.HEAD_Z + 0.09, "round head: two dot eyes + line + camera (red)\nJ3 pan +/-90 deg, J4 tilt -45..+30 deg\negg body shell and arms: visual only (no mass)", fontsize=8, color=BLUE, weight="bold")
    ax.text(0.05, 0.55, f"mast tube {S.PED_H:.2f} m", fontsize=8.5)
    ax.text(0.26, 0.015, f"front caster {S.CASTER_X:.2f} m ahead of the CoM", fontsize=8)
    ax.set_xlim(-0.6, 2.4)
    ax.set_ylim(-0.05, 1.4)
    ax.set_aspect("equal")
    ax.axis("off")


def top_view(ax):
    ax.set_title("Top view", fontsize=11, weight="bold")
    rbox(ax, 0, 0, S.DECK_L, S.DECK_W, "#4a4f59", r=0.02)
    for sy in (-1, 1):
        rbox(ax, 0, sy * S.TRACK / 2, 2 * S.WHEEL_R, S.WHEEL_T, "#222", ec=INK, r=0.008, z=3)
        joint(ax, 0, sy * S.TRACK / 2, GREEN, 0.012)
    for sx in (-1, 1):
        ax.add_patch(Circle((sx * S.CASTER_X, 0), S.CASTER_R, fc="#8a8f98", ec=INK, zorder=3))
    joint(ax, 0, 0, BLUE, 0.02)
    ax.add_patch(Circle((0, 0), S.CHASSIS_R, fill=False, ec=RED, ls="--", lw=1.2))
    ax.text(0.0, -0.36, f"footprint radius {S.CHASSIS_R:.2f} m", ha="center", fontsize=8.5, color=RED, weight="bold")
    ax.annotate("", xy=(0.27, -S.TRACK / 2), xytext=(0.27, S.TRACK / 2), arrowprops=dict(arrowstyle="<->", color=INK))
    ax.text(0.29, 0, f"track {S.TRACK:.2f} m", fontsize=8.5, weight="bold", va="center")
    ax.text(0, 0.30, "wheel radius 0.08 m", ha="center", fontsize=8.5)
    ax.annotate("front", xy=(0.45, 0), xytext=(0.30, 0.22), fontsize=9, weight="bold", arrowprops=dict(arrowstyle="->", color=INK))
    ax.set_xlim(-0.45, 0.6)
    ax.set_ylim(-0.42, 0.42)
    ax.set_aspect("equal")
    ax.axis("off")


def table(ax):
    ax.axis("off")
    rows = [("J1 / J2", "left / right drive wheel", "continuous, velocity motor"), ("J3", "neck pan (about z)", "+/-90 deg, position servo"),
            ("J4", "head tilt (about -y)", "-45..+30 deg (guide), joint built to -75..+70"), ("passive", "front and back caster", "free sphere, frictionless")]
    ax.set_title("Joints and numbers", fontsize=11, weight="bold", loc="left")
    y = 0.92
    for a, b, c in rows:
        ax.text(0.0, y, a, fontsize=9, weight="bold", color=BLUE, transform=ax.transAxes)
        ax.text(0.16, y, b, fontsize=9, transform=ax.transAxes)
        ax.text(0.52, y, c, fontsize=8.5, color="#555", transform=ax.transAxes)
        y -= 0.1
    zc, g = com_height(), 9.81
    lines = [f"mass {S.TOTAL_MASS:.1f} kg (chassis 14.0, mast tube 1.2, gimbal + head 1.3); centre of mass {zc:.3f} m (guide 0.231 m)",
             f"tip-over braking limit g * b / h = {g * S.CASTER_X / zc:.2f} m/s2 (guide 7.64)",
             f"wheel slip limit at mu 0.40: {0.4 * g:.2f} m/s2; controller clamps braking to 1.0 m/s2, standards manual needs >= 1.5 m/s2 emergency",
             f"camera optical centre {S.CAM_Z:.3f} m, vertical FOV {S.FOVY:.0f} deg, ground blind zone about 0.33 m at -45 deg tilt",
             f"wheel speed at 0.5 m/s: {0.5 / S.WHEEL_R:.1f} rad/s; standards manual limit 0.80 m/s among people"]
    y = 0.50
    for ln in lines:
        ax.text(0.0, y, ln, fontsize=9, transform=ax.transAxes)
        y -= 0.1


def concept(path):
    """Industrial-design concept: a friendly teal shell with a face screen over the same mechanism (visual styling only: the simulated robot's mass,
    collision shapes and joints are the ones in robot_spec.py)."""
    TEAL, TEAL2, SCREEN = "#2f9fb3", "#6fc3d1", "#cfe6ee"
    fig, ax = plt.subplots(figsize=(6.2, 8.2))
    ax.axhline(0, color=SOFT, lw=2)
    # shell: wide rounded base over the chassis, slim neck over the mast, round head
    rbox(ax, 0, 0.14, 0.50, 0.30, TEAL, ec=INK, r=0.13, z=3)
    rbox(ax, 0, 0.55, 0.26, 0.62, TEAL, ec=INK, r=0.12, z=2)
    ax.add_patch(Circle((0, 1.06), 0.19, fc=TEAL, ec=INK, lw=1.4, zorder=4))
    rbox(ax, 0.0, 1.05, 0.26, 0.20, SCREEN, ec=INK, r=0.07, z=5)                                          # face screen
    for sx in (-1, 1):
        ax.add_patch(Circle((sx * 0.055, 1.06), 0.035, fc="white", ec=INK, lw=1, zorder=6))
        ax.add_patch(Circle((sx * 0.055, 1.06), 0.022, fc="#37b24d", ec=INK, lw=0.8, zorder=7))
    ax.add_patch(Circle((0, 1.235), 0.012, fc=RED, ec="white", lw=1, zorder=8))                             # camera
    for sx in (-1, 1):                                                                                    # fixed arms (cosmetic)
        rbox(ax, sx * 0.17, 0.60, 0.07, 0.30, TEAL2, ec=INK, r=0.03, z=1)
    ax.add_patch(Circle((0, S.WHEEL_R), S.WHEEL_R, fc="#222", ec=INK, lw=1.4, zorder=6))
    ax.add_patch(Rectangle((-0.01, 0.2), 0.02, 0.85, fc="none", ec=INK, ls=":", lw=1, zorder=9))           # the mast inside
    ax.text(0.0, -0.06, "concept shell (visual only)", ha="center", fontsize=9, weight="bold")
    ax.text(0.30, 1.235, "camera 1.15 m", fontsize=8.5, color=RED, weight="bold", va="center")
    ax.text(0.30, 1.06, "face screen: eyes show the feelings", fontsize=8.5, weight="bold", va="center")
    ax.text(0.30, 0.14, "2 driven wheels + casters hidden inside", fontsize=8.5, weight="bold", va="center")
    ax.text(0.30, 0.60, "dotted: the 1.10 m mast", fontsize=8.5, va="center")
    ax.set_xlim(-0.5, 1.05)
    ax.set_ylim(-0.1, 1.35)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Look concept on the guide's mechanism", fontsize=11, weight="bold")
    fig.savefig(path, dpi=130, bbox_inches="tight")


def main():
    concept(os.path.join(ROOT, "outputs", "robot_look_concept.png"))
    fig = plt.figure(figsize=(15, 8.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1], height_ratios=[1.6, 1])
    side_view(fig.add_subplot(gs[:, 0]))
    top_view(fig.add_subplot(gs[0, 1]))
    table(fig.add_subplot(gs[1, 1]))
    fig.suptitle("Companion robot (guide specification): 2 driven wheels + 2 casters, 1.10 m mast, pan-tilt camera head", fontsize=14, weight="bold")
    fig.text(0.5, 0.02, "Blue = revolute joint, green = driven wheel, red = camera. Drawn to scale from src/robot/robot_spec.py (the same numbers build the MuJoCo model).", ha="center", fontsize=9)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, bbox_inches="tight")
    zc = com_height()
    print(f"camera height {S.CAM_Z:.3f} m | mass {S.TOTAL_MASS:.2f} kg | centre of mass {zc:.3f} m | tip-over limit {9.81 * S.CASTER_X / zc:.2f} m/s2 | footprint radius {S.CHASSIS_R:.3f} m")
    print("saved", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
