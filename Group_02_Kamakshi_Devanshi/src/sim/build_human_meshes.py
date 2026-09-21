"""
Turn the textured Habitat avatar (.glb) into a native MuJoCo skinned mesh (<skin>).

MuJoCo deforms a <skin> with its bodies (linear blend skinning), in the viewer and in offscreen
renders, so the body bends smoothly with no gaps or tears. The glb's own skin weights are used;
finger, eye and jaw weights are folded into wrist / head (those bodies are not simulated).

Input : external_assets/habitat_humanoids/<avatar>.glb   (kept outside the group folder)
Output: models/human/skin_<avatar>.xml           texture + material + skin (included by the scene)
        models/human/meshes/<avatar>/skin.png    texture image

The skin is defined in the rest pose of the MuJoCo model, i.e. with the pelvis body at
PELVIS_POS = (0, 0, 1.0) and every body frame aligned with the world axes.

Run:  python src/sim/build_human_meshes.py [female_0|female_1]
Source asset: Habitat Humanoids (Meta, CC-BY-NC-SA 4.0), see models/human/README.md.
"""
import io
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
AVATAR = sys.argv[1] if len(sys.argv) > 1 else "female_1"
GLB = os.path.normpath(os.path.join(ROOT, "..", "external_assets", "habitat_humanoids", f"{AVATAR}.glb"))
TEX_DIR = os.path.join(ROOT, "models", "human", "meshes", AVATAR)
OUT_XML = os.path.join(ROOT, "models", "human", f"skin_{AVATAR}.xml")

PELVIS_POS = np.array([0.0, 0.0, 1.0])       # must match the pelvis body pos in build_human_mjcf.py
C = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])  # Y-up -> Z-up
BODIES = [
    "pelvis", "left_hip", "left_knee", "left_ankle", "left_foot", "right_hip", "right_knee",
    "right_ankle", "right_foot", "spine1", "spine2", "spine3", "neck", "head", "left_collar",
    "left_shoulder", "left_elbow", "left_wrist", "right_collar", "right_shoulder",
    "right_elbow", "right_wrist",
]
CT = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    b = open(path, "rb").read()
    jl = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    off = 20 + jl
    bl = struct.unpack("<I", b[off:off + 4])[0]
    binc = b[off + 8:off + 8 + bl]

    def acc(i):
        a = j["accessors"][i]
        v = j["bufferViews"][a["bufferView"]]
        n = NC[a["type"]]
        dt = CT[a["componentType"]]
        start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = v.get("byteStride")
        if stride and stride != n * np.dtype(dt).itemsize:
            raw = np.frombuffer(binc, dtype=np.uint8, count=stride * a["count"], offset=start).reshape(a["count"], stride)
            arr = np.frombuffer(raw[:, :n * np.dtype(dt).itemsize].tobytes(), dtype=dt)
        else:
            arr = np.frombuffer(binc, dtype=dt, count=a["count"] * n, offset=start)
        return arr.reshape(a["count"], n) if n > 1 else arr

    return j, binc, acc


def owner_body(name):
    """Map every skeleton joint to one of our 22 bodies (fingers -> wrist, face -> head)."""
    if name in BODIES:
        return name
    if name == "root":
        return "pelvis"
    if name.startswith("left_") and any(k in name for k in ("index", "middle", "ring", "pinky", "thumb")):
        return "left_wrist"
    if name.startswith("right_") and any(k in name for k in ("index", "middle", "ring", "pinky", "thumb")):
        return "right_wrist"
    if name in ("jaw", "left_eye_smplhf", "right_eye_smplhf"):
        return "head"
    raise KeyError(name)


def fmt(a, p=5):
    return " ".join(f"{x:.{p}f}" for x in np.asarray(a).ravel())


def main():
    j, binc, acc = read_glb(GLB)
    nodes = j["nodes"]
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}

    def world_pos(i):
        p = np.zeros(3)
        while i is not None:
            p = p + np.array(nodes[i].get("translation", [0, 0, 0]))
            i = parent.get(i)
        return p

    skin = j["skins"][0]
    jn = [nodes[i]["name"] for i in skin["joints"]]
    jpos = {n: world_pos(i) for n, i in zip(jn, skin["joints"])}
    # root (-90 deg X) and its parent (+90 deg X) cancel; verify against the inverse-bind matrices
    ibm = acc(skin["inverseBindMatrices"]).reshape(-1, 4, 4).astype(np.float64)
    err = max(np.abs(ibm[k].T[:3, 3] + jpos[n]).max() for k, n in enumerate(jn))
    assert err < 1e-3, f"joint positions disagree with inverse-bind matrices by {err}"

    body_idx = {b: k for k, b in enumerate(BODIES)}
    joint_to_body = np.array([body_idx[owner_body(n)] for n in jn])

    prim = j["meshes"][0]["primitives"][0]
    at = prim["attributes"]
    pos = acc(at["POSITION"]).astype(np.float64)
    uv = acc(at["TEXCOORD_0"]).astype(np.float64)
    jt = acc(at["JOINTS_0"]).astype(int)
    wt = acc(at["WEIGHTS_0"]).astype(np.float64)
    idx = acc(prim["indices"]).astype(int).reshape(-1, 3)

    # rest-pose vertices in the MuJoCo world (pelvis body at PELVIS_POS)
    pel = jpos["pelvis"]
    verts = (pos - pel) @ C.T + PELVIS_POS
    bind = {b: (jpos[b] - pel) @ C.T + PELVIS_POS for b in BODIES}

    # weights per body, normalised per vertex
    W = np.zeros((len(pos), len(BODIES)))
    for k in range(4):
        np.add.at(W, (np.arange(len(pos)), joint_to_body[jt[:, k]]), wt[:, k])
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)

    os.makedirs(TEX_DIR, exist_ok=True)
    for f in os.listdir(TEX_DIR):
        if f.endswith(".obj"):
            os.remove(os.path.join(TEX_DIR, f))     # rigid-piece meshes from the earlier approach
    from PIL import Image                            # MuJoCo reads PNG textures only
    img = j["images"][0]
    view = j["bufferViews"][img["bufferView"]]
    data = binc[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
    Image.open(io.BytesIO(data)).convert("RGB").save(os.path.join(TEX_DIR, "skin.png"))

    lines = ["<mujoco>",
             f"  <!-- Generated by src/sim/build_human_meshes.py from {AVATAR}.glb (Habitat Humanoids, CC-BY-NC-SA 4.0). Do not edit. -->",
             f'  <texture name="human_skin_tex" type="2d" file="human/meshes/{AVATAR}/skin.png"/>',
             '  <material name="human_skin" texture="human_skin_tex" specular="0.1" shininess="0.1"/>',
             f'  <skin name="{AVATAR}_skin" material="human_skin" group="1"',
             f'        vertex="{fmt(verts)}"',
             f'        texcoord="{fmt(uv, 4)}"',
             f'        face="{" ".join(map(str, idx.ravel()))}">']
    for b in BODIES:
        k = body_idx[b]
        ids = np.nonzero(W[:, k] > 1e-4)[0]
        if len(ids) == 0:
            continue
        lines.append(f'    <bone body="{b}" bindpos="{fmt(bind[b])}" bindquat="1 0 0 0" '
                     f'vertid="{" ".join(map(str, ids))}" vertweight="{fmt(W[ids, k], 4)}"/>')
    lines += ["  </skin>", "</mujoco>", ""]
    with open(OUT_XML, "w") as f:
        f.write("\n".join(lines))
    print(f"{AVATAR}: {len(pos)} vertices, {len(idx)} triangles -> {os.path.relpath(OUT_XML, ROOT)} "
          f"({os.path.getsize(OUT_XML) // 1024} KB), height {pos[:, 1].max() - pos[:, 1].min():.2f} m")


if __name__ == "__main__":
    main()
