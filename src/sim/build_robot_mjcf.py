"""
Add the companion robot (the research guide's robot: 1.10 m mast, 16.5 kg) to the scene.

Reads   models/scene_with_human.xml   (apartment + woman, from build_apartment.py / build_human_mjcf.py)
Writes  models/scene_full.xml          (+ robot, motors, sensors)
        models/companion_robot.xml     (robot alone on a plane, for unit tests)

Robot (dimensions in src/robot/robot_spec.py, drawing in src/robot/kinematic_sketch.py):
  base body "robot" at the wheel axle; free joint
    wheel_l / wheel_r   hinge about +y (positive = forward), driven by velocity motors (differential drive)
    2 passive casters   frictionless (priority 2, condim 1) so they roll instead of dragging
    neck_pan            hinge about z, +/-90 deg      (position servo)
    head_tilt           hinge about -y, -75..+70 deg joint range (position servo; negative = looking down); the guide's -45..+30 is the default software limit, wide view lifts it
  head: rounded-box body, front screen + cyan eyes (visual, colour/size change with the robot's mood),
        camera "robot_cam" in the top bezel (58 deg vertical FOV, looks along +x of the head)

Run:  python src/sim/build_robot_mjcf.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "robot"))
import robot_spec as S  # noqa: E402
import apartment_layout as L  # noqa: E402

SCENE_IN = os.path.join(ROOT, "models", "scene_with_human.xml")
SCENE_OUT = os.path.join(ROOT, "models", "scene_full.xml")
ROBOT_OUT = os.path.join(ROOT, "models", "companion_robot.xml")


def f(*v):
    return " ".join(f"{x:.5g}" for x in v)


def bell_mesh(n_seg=28):
    """The body shell as a surface of revolution (a soft bell: wide skirt, narrow shoulders), as an inline MuJoCo mesh. Returns (vertex, face) strings."""
    import math
    prof = S.BELL_PROFILE
    verts, faces = [], []
    for zz, rr in prof:
        for k in range(n_seg):
            th = 2 * math.pi * k / n_seg
            verts.append((rr * math.cos(th) * 0.95 - 0.02, rr * math.sin(th) * 1.0, zz))
    nr = len(prof)
    for i in range(nr - 1):
        for k in range(n_seg):
            a, b = i * n_seg + k, i * n_seg + (k + 1) % n_seg
            c, d = (i + 1) * n_seg + k, (i + 1) * n_seg + (k + 1) % n_seg
            faces += [(a, b, d), (a, d, c)]
    bottom = len(verts)
    verts.append((-0.02, 0.0, prof[0][0]))
    for k in range(n_seg):
        faces.append((bottom, (k + 1) % n_seg, k))
    return " ".join(f"{x:.4f} {y:.4f} {z:.4f}" for x, y, z in verts), " ".join(f"{a} {b} {c}" for a, b, c in faces)


def robot_body(x, y, yaw_deg, ind=2):
    """MJCF lines for the robot. Body origin = wheel axle centre, so the free joint z is WHEEL_R."""
    pad = "  " * ind
    r = S.WHEEL_R
    z = lambda z_abs: z_abs - r                       # absolute height -> body-relative height
    eye_y = 0.042
    eye_x = 0.1235                                    # the round visual head (r 0.115) carries a visor, screen and camera on its front
    scr_h = 0.056
    scr_z = 0.045                                     # screen centre relative to the head body (tilt axis)
    cam_z = 0.04 + S.HEAD_H / 2 - S.BEZEL_TOP / 2
    L_ = []
    a = L_.append
    a(f'{pad}<body name="robot" pos="{f(x, y, r)}" euler="0 0 {yaw_deg}">')
    a(f'{pad}  <freejoint name="robot_free"/>')
    a(f'{pad}  <site name="base_link" pos="0 0 0" size="0.004" rgba="0 0 1 0.5" group="5"/>')
    a(f'{pad}  <geom name="deck" type="box" size="{f(S.DECK_L / 2, S.DECK_W / 2, S.DECK_T / 2)}" pos="{f(0, 0, z(S.DECK_Z0 + S.DECK_T / 2))}" '
      f'rgba="0.93 0.93 0.94 1" mass="{S.MASS["deck"]}" friction="0.3 0.005 0.0001"/>')
    a(f'{pad}  <geom name="pedestal" type="cylinder" size="0.02 {S.PED_H / 2}" pos="{f(0, 0, z(S.DECK_Z0 + S.DECK_T + S.PED_H / 2))}" '
      f'rgba="0.93 0.93 0.94 1" mass="{S.MASS["pedestal"]}"/>')                     # the 1.10 m mast tube (it does collide: tables and shelves are overhead obstacles)
    a(f'{pad}  <geom name="status_led" type="box" size="0.002 0.12 0.004" pos="{f(S.DECK_L / 2 + 0.001, 0, z(S.DECK_Z0 + S.DECK_T - 0.02))}" '
      f'rgba="0.2 0.9 0.4 1" contype="0" conaffinity="0" mass="0"/>')
    # ---- look: a soft white shell (visual only: no collision, no mass) so the guide's mass, centre of mass and braking numbers stay valid -----------
    W = "0.93 0.93 0.94 1"
    a(f'{pad}  <geom name="shell_body" type="mesh" mesh="shell_body" pos="0 0 {z(0.0):.5g}" rgba="{W}" contype="0" conaffinity="0" mass="0"/>')
    a(f'{pad}  <geom name="shell_slot" type="capsule" size="0.011 0.075" pos="{f(0.248, 0, z(0.36))}" euler="90 0 0" rgba="0.05 0.05 0.06 1" contype="0" conaffinity="0" mass="0"/>')
    a(f'{pad}  <geom name="shell_grille" type="box" size="0.003 0.07 0.012" pos="{f(-0.27, 0, z(0.36))}" rgba="0.55 0.55 0.58 1" contype="0" conaffinity="0" mass="0"/>')
    for nm, sy in (("l", 1), ("r", -1)):
        a(f'{pad}  <geom name="shell_arm_{nm}" type="capsule" size="0.058 0.15" pos="{f(-0.03, sy * 0.285, z(0.66))}" euler="{sy * -9} 0 0" rgba="{W}" contype="0" conaffinity="0" mass="0"/>')
        hy = sy * 0.31
        a(f'{pad}  <geom name="shell_palm_{nm}" type="ellipsoid" size="0.04 0.034 0.05" pos="{f(-0.03, hy, z(0.455))}" rgba="{W}" contype="0" conaffinity="0" mass="0"/>')
        for k, fx in enumerate((-0.022, 0.0, 0.022)):
            a(f'{pad}  <geom name="shell_finger_{nm}{k}" type="capsule" size="0.0105 0.026" pos="{f(-0.03 + fx, hy, z(0.385))}" rgba="{W}" contype="0" conaffinity="0" mass="0"/>')
        a(f'{pad}  <geom name="shell_thumb_{nm}" type="capsule" size="0.0105 0.024" pos="{f(-0.03 + 0.045, hy, z(0.43))}" euler="0 35 0" rgba="{W}" contype="0" conaffinity="0" mass="0"/>')
    for nm, sx in (("caster_front", 1), ("caster_back", -1)):
        a(f'{pad}  <geom name="{nm}" type="sphere" size="{S.CASTER_R}" pos="{f(sx * S.CASTER_X, 0, z(S.CASTER_R))}" rgba="0.45 0.47 0.5 1" '
          f'mass="{S.MASS["casters"] / 2}" condim="1" priority="2" friction="0.001 0.001 0.001"/>')
    for nm, sy in (("l", 1), ("r", -1)):
        a(f'{pad}  <body name="wheel_{nm}" pos="{f(0, sy * S.TRACK / 2, 0)}">')
        a(f'{pad}    <joint name="wheel_{nm}" type="hinge" axis="0 1 0" damping="0.05" armature="0.02"/>')
        a(f'{pad}    <geom name="wheel_{nm}_geom" type="cylinder" size="{S.WHEEL_R} {S.WHEEL_T / 2}" euler="90 0 0" rgba="0.1 0.1 0.12 1" mass="{S.MASS["wheels"] / 2}"/>')
        a(f'{pad}    <geom name="wheel_{nm}_hub" type="cylinder" size="0.012 {S.WHEEL_T / 2 + 0.0005}" euler="90 0 0" rgba="0.2 0.8 0.4 1" contype="0" conaffinity="0" mass="0"/>')
        a(f'{pad}  </body>')
    a(f'{pad}  <body name="robot_neck" pos="{f(0, 0, z(S.NECK_Z))}">')
    a(f'{pad}    <joint name="neck_pan" type="hinge" axis="0 0 1" range="{f(*S.PAN_RANGE_DEG)}" damping="0.3" armature="0.005"/>')
    a(f'{pad}    <geom name="neck_geom" type="cylinder" size="0.02 0.008" pos="0 0 0.008" rgba="0.2 0.22 0.25 1" mass="{S.MASS["neck"]}" contype="0" conaffinity="0"/>')
    a(f'{pad}    <body name="robot_head" pos="{f(0, 0, S.TILT_Z - S.NECK_Z)}">')
    a(f'{pad}      <joint name="head_tilt" type="hinge" axis="0 -1 0" range="{f(*S.TILT_WIDE_DEG)}" damping="0.3" armature="0.005"/>')
    a(f'{pad}      <geom name="head_geom" type="box" size="{f(S.HEAD_D / 2, S.HEAD_W / 2, S.HEAD_H / 2)}" pos="0 0 0.04" rgba="0.93 0.93 0.94 1" mass="{S.MASS["head"]}"/>')
    a(f'{pad}      <geom name="shell_head" type="ellipsoid" size="{f(*S.HEAD_SHELL)}" pos="{f(0, 0, 0.04)}" rgba="0.93 0.93 0.94 1" contype="0" conaffinity="0" mass="0"/>')
    a(f'{pad}      <geom name="neck_ring" type="cylinder" size="0.085 0.004" pos="{f(0, 0, -0.095)}" rgba="0.5 0.5 0.53 1" contype="0" conaffinity="0" mass="0"/>')
    a(f'{pad}      <geom name="power_button" type="box" size="0.004 0.012 0.016" pos="{f(-0.12, 0, -0.06)}" rgba="0.85 0.1 0.1 1" contype="0" conaffinity="0" mass="0"/>')
    a(f'{pad}      <geom name="shell_mouth_line" type="box" size="0.0012 0.07 0.0016" pos="{f(0.1475, 0, 0.04)}" rgba="0.05 0.05 0.06 1" contype="0" conaffinity="0" mass="0"/>')
    for nm, sy in (("l", 1), ("r", -1)):
        a(f'{pad}      <geom name="eye_{nm}" type="ellipsoid" size="0.003 0.02 0.02" pos="{f(0.1405, sy * 0.075, 0.04)}" rgba="0.05 0.05 0.06 1" contype="0" conaffinity="0" mass="0"/>')
        a(f'{pad}      <geom name="brow_{nm}" type="box" size="0.0012 0.022 0.0025" pos="{f(0.139, sy * 0.075, 0.074)}" euler="{sy * 18} 0 0" rgba="1 0.69 0 0" contype="0" conaffinity="0" mass="0"/>')
    a(f'{pad}      <geom name="mic_array" type="box" size="0.012 0.02 0.001" pos="{f(-0.01, 0, 0.04 + S.HEAD_H / 2 + 0.001)}" rgba="0.1 0.1 0.1 1" contype="0" conaffinity="0" mass="0"/>')
    a(f'{pad}      <camera name="robot_cam" pos="{f(S.CAM_X, 0, cam_z)}" xyaxes="0 -1 0 0 0 1" fovy="{S.FOVY}"/>')
    a(f'{pad}      <site name="camera_optical_frame" pos="{f(S.CAM_X, 0, cam_z)}" size="0.003" rgba="1 0 0 0.6" group="5"/>')
    a(f'{pad}    </body>')
    a(f'{pad}  </body>')
    a(f'{pad}</body>')
    return L_


ACTUATORS_AND_SENSORS = """
  <contact>
    <exclude body1="robot" body2="robot_head"/>
  </contact>
  <actuator>
    <velocity name="act_wheel_l" joint="wheel_l" kv="6.0" ctrllimited="true" ctrlrange="-20 20" forcelimited="true" forcerange="-3 3"/>
    <velocity name="act_wheel_r" joint="wheel_r" kv="6.0" ctrllimited="true" ctrlrange="-20 20" forcelimited="true" forcerange="-3 3"/>
    <position name="act_neck_pan" joint="neck_pan" kp="12.0" kv="1.2" forcelimited="true" forcerange="-4 4"/>
    <position name="act_head_tilt" joint="head_tilt" kp="12.0" kv="1.2" forcelimited="true" forcerange="-4 4"/>
  </actuator>
  <sensor>
    <jointpos name="enc_l" joint="wheel_l"/>
    <jointpos name="enc_r" joint="wheel_r"/>
    <jointvel name="enc_l_vel" joint="wheel_l"/>
    <jointvel name="enc_r_vel" joint="wheel_r"/>
    <jointpos name="neck_pan_pos" joint="neck_pan"/>
    <jointpos name="head_tilt_pos" joint="head_tilt"/>
    <framepos name="robot_pos" objtype="body" objname="robot"/>
    <framequat name="robot_quat" objtype="body" objname="robot"/>
    <framelinvel name="robot_linvel" objtype="body" objname="robot"/>
    <frameangvel name="robot_angvel" objtype="body" objname="robot"/>
  </sensor>
"""


def build():
    x, y, yaw = L.ROBOT_DOCK
    body = "\n".join(robot_body(x, y, yaw))
    scene = open(SCENE_IN).read()
    marker = "    <!-- Lighting -->"
    assert marker in scene, "scene_with_human.xml has no lighting marker; run build_apartment.py and build_human_mjcf.py first"
    scene = scene.replace(marker, "    <!-- Companion robot (generated by src/sim/build_robot_mjcf.py) -->\n" + body + "\n\n" + marker, 1)
    scene = scene.replace('<mujoco model="apartment_with_human">', '<mujoco model="apartment_full">', 1)
    vv, ff = bell_mesh()
    assert "<asset>" in scene
    scene = scene.replace("<asset>", f'<asset>\n    <mesh name="shell_body" vertex="{vv}" face="{ff}"/>', 1)
    assert scene.rstrip().endswith("</mujoco>")
    scene = scene.rstrip()[: -len("</mujoco>")] + ACTUATORS_AND_SENSORS + "</mujoco>\n"
    with open(SCENE_OUT, "w") as fh:
        fh.write(scene)

    solo = f"""<mujoco model="companion_robot">
  <!-- Generated by src/sim/build_robot_mjcf.py: the robot alone on a plane, for unit tests. -->
  <compiler angle="degree" inertiafromgeom="true"/>
  <option timestep="0.002" gravity="0 0 -9.81" integrator="implicitfast"/>
  <asset>
    <mesh name="shell_body" vertex="{bell_mesh()[0]}" face="{bell_mesh()[1]}"/>
  </asset>
  <worldbody>
    <geom name="floor" type="plane" size="10 10 0.1" friction="0.5 0.005 0.0001" priority="1" rgba="0.8 0.75 0.7 1"/>
    <light directional="true" pos="0 0 5" dir="0 0 -1"/>
{body.replace(f'pos="{f(x, y, S.WHEEL_R)}" euler="0 0 {yaw}"', f'pos="{f(0, 0, S.WHEEL_R)}" euler="0 0 0"')}
  </worldbody>{ACTUATORS_AND_SENSORS}</mujoco>
"""
    with open(ROBOT_OUT, "w") as fh:
        fh.write(solo)
    print("wrote", os.path.relpath(SCENE_OUT, ROOT), "and", os.path.relpath(ROBOT_OUT, ROOT))


if __name__ == "__main__":
    build()
