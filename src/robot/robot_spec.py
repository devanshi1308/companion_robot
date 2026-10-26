"""
Single source of truth for the robot's dimensions (metres, kilograms).
Used by kinematic_sketch.py (the drawing) and build_robot_mjcf.py (the simulator model).

Frame convention (REP-103): x forward, y left, z up. The robot body frame sits at the wheel axle.
"""
ROBOT_PROFILE = "guide"     # the robot of the research guide: 1.10 m mast, 16.5 kg, wheel radius 0.08 m, track 0.38 m (replaced the small EMO-style robot on 2026-10-22)
DECK_L, DECK_W, DECK_T, DECK_Z0 = 0.44, 0.34, 0.16, 0.04      # chassis box (underside at 0.04 m, top at 0.20 m, centre at 0.12 m: the guide's chassis CoM height)
WHEEL_R, WHEEL_T, TRACK = 0.08, 0.04, 0.38                    # guide: wheel radius 0.08 m, track gauge 0.38 m
CASTER_R, CASTER_X = 0.03, 0.18                                # guide: front caster 0.18 m from the centre of mass
NECK_Z = 1.05                                                  # top of the mast tube / pan axis above the floor
PED_H = NECK_Z - (DECK_Z0 + DECK_T)                            # mast tube length (0.85 m)
HEAD_W, HEAD_H, HEAD_D = 0.12, 0.10, 0.10                     # rounded-square head with the face screen (front)
BEZEL_SIDE, BEZEL_TOP, BEZEL_BOT = 0.008, 0.016, 0.008         # thin bezel; the camera sits in the top bezel
TILT_Z = 1.07                                                  # head tilt axis height above the floor (mast height 1.10 m with the gimbal)
HEAD_Z = TILT_Z + 0.04                                         # head centre height
CAM_Z = HEAD_Z + HEAD_H / 2 - BEZEL_TOP / 2                    # camera height above the floor: 1.152 m (guide: 1.15 m)
# kg: chassis 14.0 (box 11.4 + wheels 2.4 + casters 0.2), mast tube 1.2, gimbal + head 1.3 -> 16.5 kg total, CoM about 0.23 m (guide: 0.231 m)
MASS = dict(deck=11.4, pedestal=1.2, wheels=2.4, casters=0.2, neck=0.05, head=1.25)
TOTAL_MASS = sum(MASS.values())
FOVY = 58.0                                                    # guide: vertical field of view (deg)
PAN_RANGE_DEG = (-90.0, 90.0)                                  # guide
TILT_RANGE_DEG = (-45.0, 30.0)                                 # guide (negative = looking down)
TILT_WIDE_DEG = (-75.0, 70.0)                                  # 'wide view' option for the family platform; the head joint is built with this range

V_MAX = 0.50           # m/s cruise (guide); standards manual limit is 0.80 m/s
A_COMFORT = 1.00       # m/s2 normal braking (guide: the controller clamps braking to 1.00 m/s2)
BUBBLE = 0.50          # m: standards-manual clearance bubble; doors are 0.85-0.90 m (half 0.43), so inside the bubble the robot only SLOWS (BUBBLE_V), see docs/REQUIREMENTS_CHECK.md
BUBBLE_V = 0.20        # m/s: speed cap while closer than BUBBLE to a mapped obstacle (doorways, furniture)
A_EMERGENCY = 1.50     # m/s2 emergency braking required by the standards manual
STANDOFF = 1.00        # m from the person (guide: 0.80 to 1.20 m)
CHASSIS_R = ((DECK_L / 2) ** 2 + (TRACK / 2 + WHEEL_T / 2) ** 2) ** 0.5   # m: footprint radius (chassis front corner / outer wheel), about 0.30
LIDAR_X = DECK_L / 2 + 0.02                                    # m: range-sensor rays start just in front of the chassis
LIDAR_Z = 0.06                                                 # m above the floor (sees low obstacles: the robot vacuum, clutter)

HEAD_SHELL = (0.16, 0.20, 0.13)   # m: radii (x, y, z) of the flattened egg-shaped visual head (no collision, no mass)
HEAD_SHELL_R = HEAD_SHELL[0]
BELL_PROFILE = [(0.11, 0.232), (0.13, 0.246), (0.17, 0.257), (0.28, 0.262), (0.40, 0.266), (0.52, 0.25), (0.62, 0.215), (0.72, 0.178), (0.82, 0.15), (0.89, 0.125), (0.94, 0.08), (0.965, 0.03), (0.97, 0.0)]  # (height, radius): egg-shaped body shell
CAM_X = 0.152             # m: camera forward offset in the head frame (on the front of the round head)
