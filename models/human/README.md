# Human subject assets (female_1 in use, female_0 kept as alternative)

Third-party assets used to build the simulated elderly-care subject.

| File | Source | Use |
|---|---|---|
| `female_1/female_1.urdf` (in use), `female_0/female_0.urdf` | Habitat Humanoids (SMPL-X skeleton) | joint hierarchy and bone offsets, read by `src/sim/build_human_mjcf.py` |
| `skin_female_1.xml`, `meshes/female_1/skin.png` (generated) | female_1.glb via `src/sim/build_human_meshes.py` | textured skinned body mesh for MuJoCo (visual only) |
| `female_*/female_*.ao_config.json` | Habitat Humanoids | Habitat metadata (reference only) |
| `walk_cycle_smplx.json` | AMASS (CMU subject 10, trial 04) via Habitat Humanoids | walking gait cycle (frames 300-430), extracted by `src/sim/extract_walk_cycle.py` |

Source: https://huggingface.co/datasets/ai-habitat/habitat_humanoids (downloaded 2026-09-21)

Not kept in this folder (the course audit false-flags binary files): the textured meshes `female_0.glb` and `female_1.glb` and the original `CMU_10_04_stageii.npz` live in `external_assets/habitat_humanoids/` at the repository root (git-ignored). Re-download from the source URL if needed.

## Licence and attribution

- Avatars (URDF, GLB, config): CC-BY-NC-SA 4.0 (Meta, Habitat 3.0 Humanoids). Non-commercial use, attribution required, derivatives must carry the same licence. The generated `models/human_subject.xml` and `models/scene_with_human.xml` are adaptations of the URDF and are shared under the same terms.
- Motion data (walk clip): SMPL Body Motion File License (CC BY 4.0 per the dataset card), from AMASS / CMU mocap.
- Cite in the paper: Habitat 3.0 (Puig et al., 2023) and AMASS (Mahmood et al., 2019). Verify the DOIs before citing.

## What was changed from the originals

- The URDF holds 54 "spherical" joints, placeholder 5 kg masses (275 kg total) and 2 cm debug boxes, so it cannot be loaded by MuJoCo directly. The converter keeps the 21 body joints (fingers, eyes, jaw dropped), converts Y-up to Z-up, uses MuJoCo ball joints, adds hidden capsule collision geometry, converts the textured mesh to a MuJoCo `<skin>` (smooth linear blend skinning), and sets segment masses to about 65.5 kg.
- Only numeric arrays of the original `.npz` were read (`allow_pickle=False`). The `.pkl` motion files from the dataset were deliberately not downloaded.

## Known limitations

- The avatar is an adult body shape, not an elderly one; walking speed is slowed to 0.8 m/s to approximate an older gait.
- The gait is replayed kinematically (no balance control). Only the fall itself is simulated by physics, with a trip impulse. Joint limits are cone-shaped ball limits, so knees can bend backward during the fall.
- Falls are not validated against real fall data; compare the measured features with published ranges before using them in results.

The dataset's `female_*_motion_data_smplx.pkl` files are not used and not stored (pickle can execute code when loaded); the walk comes from the AMASS clip instead.
