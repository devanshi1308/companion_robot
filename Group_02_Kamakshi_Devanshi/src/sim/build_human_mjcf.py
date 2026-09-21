"""
Build the female human subject for MuJoCo from the Habitat SMPL-X URDF.

Input : models/human/<avatar>/<avatar>.urdf (default female_1)   (skeleton only: 54 "spherical" joints,
        placeholder masses/geometry, Y-up)
Output: models/human_subject.xml      (standalone: floor + human, for inspection)
        models/scene_with_human.xml   (domestic_environment.xml + human)

What this script adds on top of the URDF:
  * MuJoCo ball joints (MuJoCo cannot load URDF "spherical" joints)
  * Y-up -> Z-up conversion (SMPL forward +z becomes MuJoCo -y)
  * capsule / sphere collision geometry per body segment (hidden when the skin exists)
  * a native MuJoCo <skin> (textured, smooth-bending body) from build_human_meshes.py
  * realistic segment masses (about 65 kg total instead of the URDF's 275 kg)
  * 33 BlazePose-compatible landmark sites (lm_00_nose ... lm_32_right_foot_index)
  * human geoms collide with the world (floor, furniture) but not with each other

Fingers, jaw and eyes are dropped (they do not matter for fall kinematics).

Source assets: Habitat Humanoids (Meta, CC-BY-NC-SA 4.0), see models/human/README.md.

Run:  python src/sim/build_human_mjcf.py [female_0|female_1]
"""
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
AVATAR = sys.argv[1] if len(sys.argv) > 1 else "female_1"   # any folder under models/human/ with <name>.urdf
URDF = os.path.join(ROOT, "models", "human", AVATAR, f"{AVATAR}.urdf")
SKIN_XML = os.path.join(ROOT, "models", "human", f"skin_{AVATAR}.xml")
HAS_MESH = os.path.exists(SKIN_XML)     # made by build_human_meshes.py; otherwise capsules are shown
OUT_HUMAN = os.path.join(ROOT, "models", "human_subject.xml")
OUT_SCENE = os.path.join(ROOT, "models", "scene_with_human.xml")
ENV_XML = os.path.join(ROOT, "models", "domestic_environment.xml")

# SMPL-X body-pose joint order (pose_body is 21 x 3 axis-angle, in this order)
BODY_JOINTS = [
    "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2",
    "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot", "neck",
    "left_collar", "right_collar", "head", "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow", "left_wrist", "right_wrist",
]
FOOT_BODIES = ("left_foot", "right_foot", "left_ankle", "right_ankle")

# Y-up (SMPL) -> Z-up (MuJoCo): rotation about x by +90 deg, (x, y, z) -> (x, -z, y)
C = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])

# Segment mass in kg (sums to about 65 kg adult woman)
MASS = {
    "pelvis": 10.0, "spine1": 6.0, "spine2": 6.0, "spine3": 9.0, "neck": 1.2, "head": 4.5,
    "left_collar": 0.8, "right_collar": 0.8, "left_shoulder": 1.7, "right_shoulder": 1.7,
    "left_elbow": 1.0, "right_elbow": 1.0, "left_wrist": 0.5, "right_wrist": 0.5,
    "left_hip": 6.5, "right_hip": 6.5, "left_knee": 2.8, "right_knee": 2.8,
    "left_ankle": 0.7, "right_ankle": 0.7, "left_foot": 0.4, "right_foot": 0.4,
}
# Ball-joint limit (rad, measured from the rest pose) and damping (N m s)
LIMIT = {
    "hip": 2.4, "knee": 2.8, "ankle": 1.2, "foot": 1.0, "spine": 1.0, "neck": 1.2,
    "head": 1.2, "collar": 0.8, "shoulder": 3.0, "elbow": 3.0, "wrist": 1.6,
}
DAMP = {"spine": 3.0, "neck": 1.0, "head": 0.5}
RADIUS = {
    "hip": 0.065, "knee": 0.045, "ankle": 0.035, "foot": 0.03, "spine1": 0.11,
    "spine2": 0.12, "spine3": 0.13, "neck": 0.05, "collar": 0.04, "shoulder": 0.04,
    "elbow": 0.033, "wrist": 0.03,
}

# BlazePose landmark -> (body, offset in SMPL Y-up local coords)
LANDMARKS = [
    ("nose", "head", (0, 0.09, 0.10)),
    ("left_eye_inner", "head", (0.015, 0.115, 0.09)), ("left_eye", "head", (0.032, 0.115, 0.085)),
    ("left_eye_outer", "head", (0.05, 0.115, 0.075)), ("right_eye_inner", "head", (-0.015, 0.115, 0.09)),
    ("right_eye", "head", (-0.032, 0.115, 0.085)), ("right_eye_outer", "head", (-0.05, 0.115, 0.075)),
    ("left_ear", "head", (0.08, 0.10, 0.0)), ("right_ear", "head", (-0.08, 0.10, 0.0)),
    ("mouth_left", "head", (0.025, 0.05, 0.09)), ("mouth_right", "head", (-0.025, 0.05, 0.09)),
    ("left_shoulder", "left_shoulder", (0, 0, 0)), ("right_shoulder", "right_shoulder", (0, 0, 0)),
    ("left_elbow", "left_elbow", (0, 0, 0)), ("right_elbow", "right_elbow", (0, 0, 0)),
    ("left_wrist", "left_wrist", (0, 0, 0)), ("right_wrist", "right_wrist", (0, 0, 0)),
    ("left_pinky", "left_wrist", (0.08, 0, -0.025)), ("right_pinky", "right_wrist", (-0.08, 0, -0.025)),
    ("left_index", "left_wrist", (0.09, 0, 0.02)), ("right_index", "right_wrist", (-0.09, 0, 0.02)),
    ("left_thumb", "left_wrist", (0.05, 0, 0.035)), ("right_thumb", "right_wrist", (-0.05, 0, 0.035)),
    ("left_hip", "left_hip", (0, 0, 0)), ("right_hip", "right_hip", (0, 0, 0)),
    ("left_knee", "left_knee", (0, 0, 0)), ("right_knee", "right_knee", (0, 0, 0)),
    ("left_ankle", "left_ankle", (0, 0, 0)), ("right_ankle", "right_ankle", (0, 0, 0)),
    ("left_heel", "left_ankle", (0, -0.06, -0.05)), ("right_heel", "right_ankle", (0, -0.06, -0.05)),
    ("left_foot_index", "left_foot", (0, 0, 0.08)), ("right_foot_index", "right_foot", (0, 0, 0.08)),
]


def _kind(name):
    for k in ("hip", "knee", "ankle", "foot", "neck", "head", "collar", "shoulder", "elbow", "wrist"):
        if name.endswith(k):
            return k
    return "spine"


def _v(a):
    return " ".join(f"{x:.5f}" for x in a)


def read_urdf():
    root = ET.parse(URDF).getroot()
    parent, offset = {}, {}
    for j in root.findall("joint"):
        c = j.find("child").get("link")
        parent[c] = j.find("parent").get("link")
        offset[c] = C @ np.array([float(x) for x in j.find("origin").get("xyz").split()])
    return parent, offset


def body_xml(name, children, offset, indent, deg=False):
    pad = "  " * indent
    pos = offset.get(name, np.zeros(3))
    kind = _kind(name)
    lines = []
    if name == "pelvis":
        lines.append(f'{pad}<body name="pelvis" pos="0 0 1.0">')
        lines.append(f'{pad}  <freejoint name="human_root"/>')
    else:
        lines.append(f'{pad}<body name="{name}" pos="{_v(pos)}">')
        lim = LIMIT[kind]
        lim = round(float(np.degrees(lim)), 3) if deg else lim
        damp = DAMP.get(kind, 1.5)
        lines.append(f'{pad}  <joint name="{name}" type="ball" limited="true" range="0 {lim}" '
                     f'damping="{damp}" armature="0.01"/>')

    geoms = []  # (xml without mass)
    common = 'contype="2" conaffinity="1" friction="0.8 0.005 0.0001"' + (' group="3"' if HAS_MESH else "")  # group 3 = hidden collision shapes
    kids = [c for c in children.get(name, []) if c in offset]
    rad = RADIUS.get(name, RADIUS.get(kind, 0.04))

    def cap(a, b, r, rgba):
        return f'<geom type="capsule" fromto="{_v(a)} {_v(b)}" size="{r}" rgba="{rgba}" {common}'

    skin = "0.87 0.68 0.58 1"
    cloth = "0.35 0.45 0.70 1"
    if name == "pelvis":
        lh, rh = offset["left_hip"], offset["right_hip"]
        geoms.append(cap(lh, rh, 0.09, cloth))
        geoms.append(cap(np.zeros(3), offset["spine1"], 0.10, cloth))
    elif kind == "head":
        geoms.append(f'<geom type="sphere" pos="{_v(C @ np.array([0, 0.10, 0.0]))}" size="0.095" rgba="{skin}" {common}')
    elif kind == "wrist":
        geoms.append(cap(np.zeros(3), C @ np.array([np.sign(offset[name][0]) * 0.095, -0.015, 0.02]), 0.03, skin))
    elif kind == "foot":
        geoms.append(cap(np.zeros(3), C @ np.array([0, 0, 0.08]), 0.03, "0.25 0.25 0.25 1"))
    elif name == "spine3":
        geoms.append(cap(np.zeros(3), offset["neck"], 0.13, cloth))
        geoms.append(cap(offset["left_collar"], offset["right_collar"], 0.07, cloth))
    elif kids:
        main = kids[0]
        color = cloth if kind in ("spine", "hip", "collar") else skin
        if kind == "ankle":
            color = "0.25 0.25 0.25 1"
        geoms.append(cap(np.zeros(3), offset[main], rad, color))
    n = len(geoms)
    m = MASS[name] / max(n, 1)
    for g in geoms:
        lines.append(f'{pad}  {g} mass="{m:.4f}"/>')

    for lm_idx, (lm, body, off) in enumerate(LANDMARKS):
        if body == name:
            lines.append(f'{pad}  <site name="lm_{lm_idx:02d}_{lm}" pos="{_v(C @ np.array(off))}" size="0.012" rgba="1 0 0 0.6" group="4"/>')

    for c in kids:
        if c in BODY_JOINTS:
            lines.extend(body_xml(c, children, offset, indent + 1, deg))
    lines.append(f"{pad}</body>")
    return lines


def asset_xml():
    """Textured skinned mesh (linear blend skinning done by MuJoCo), see build_human_meshes.py."""
    if not HAS_MESH:
        return ""
    return f'    <include file="human/skin_{AVATAR}.xml"/>\n'


def build():
    parent, offset = read_urdf()
    children = {}
    for c, p in parent.items():
        if c in BODY_JOINTS or c == "pelvis":
            children.setdefault(p, []).append(c)
    # deterministic child order: main limb chain first
    order = {n: i for i, n in enumerate(BODY_JOINTS)}
    for p in children:
        children[p].sort(key=lambda n: order.get(n, 99))
    # keep the "main" child first for limbs
    main_child = {"pelvis": "spine1", "left_hip": "left_knee", "right_hip": "right_knee",
                  "left_knee": "left_ankle", "right_knee": "right_ankle",
                  "left_ankle": "left_foot", "right_ankle": "right_foot",
                  "spine1": "spine2", "spine2": "spine3", "spine3": "neck", "neck": "head",
                  "left_collar": "left_shoulder", "right_collar": "right_shoulder",
                  "left_shoulder": "left_elbow", "right_shoulder": "right_elbow",
                  "left_elbow": "left_wrist", "right_elbow": "right_wrist"}
    for p, mc in main_child.items():
        if mc in children.get(p, []):
            children[p].remove(mc)
            children[p].insert(0, mc)

    body_txt = "\n".join(body_xml("pelvis", children, offset, 2, deg=False))
    body_txt_deg = "\n".join(body_xml("pelvis", children, offset, 2, deg=True))  # env file uses angle="degree"
    total = sum(MASS.values())

    standalone = f"""<mujoco model="female_human_subject">
  <!-- Generated by src/sim/build_human_mjcf.py from Habitat female_0.urdf. Do not edit by hand. -->
  <compiler angle="radian"/>
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <asset>
{asset_xml()}  </asset>
  <worldbody>
    <geom name="floor" type="plane" size="8 8 0.1" rgba="0.8 0.75 0.7 1"/>
    <light directional="true" pos="0 0 5" dir="0 0 -1"/>
{body_txt}
  </worldbody>
</mujoco>
"""
    with open(OUT_HUMAN, "w") as f:
        f.write(standalone)

    env = open(ENV_XML).read()
    marker = "    <!-- Lighting -->"
    assert marker in env, "domestic_environment.xml changed; update marker"
    human_block = ("    <!-- Female human subject (generated by src/sim/build_human_mjcf.py) -->\n"
                   + body_txt_deg + "\n\n")
    scene = env.replace(marker, human_block + marker, 1)
    assert "</asset>" in scene
    scene = scene.replace("</asset>", asset_xml() + "  </asset>", 1)
    scene = scene.replace('<mujoco model="living_room">', '<mujoco model="living_room_with_human">', 1)
    with open(OUT_SCENE, "w") as f:
        f.write(scene)
    print(f"wrote {os.path.relpath(OUT_HUMAN, ROOT)} and {os.path.relpath(OUT_SCENE, ROOT)} (human mass {total:.1f} kg)")


if __name__ == "__main__":
    build()
