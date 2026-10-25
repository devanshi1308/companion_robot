# Requirements check (supervisor's feedback sheet and the capstone brief)

Status on 2026-10-22. "Done" means built and tested; "needs the new run" means the code exists but the numbers must come from the rerun with the guide's robot
(the earlier numbers belong to the small robot and are archived in outputs/experiments_small_emo_robot/).

## A. MuJoCo model and pipeline
| Requirement | Status | Where |
|---|---|---|
| Rigid-body multi-joint kinematic tree in MJCF with contact friction, joint limits, actuators | Done | models/companion_robot.xml, models/scene_full.xml (built by src/sim/build_robot_mjcf.py): free base, 2 driven wheel joints, neck pan +/-90 deg, head tilt, ball-joint human with limits, floor friction 0.42 / 0.50 / 0.68 |
| Sensor feedback | Done | wheel encoders, joint positions, IMU-style pose and velocity sensors, 72-ray range scan, camera + depth |
| Closed-loop trajectory tracking | Done | A* path + pure pursuit with slew-limited steering and speed limits (src/control/navigation.py) |
| Disturbance injection | Done | random pushes, camera blackouts, odometry noise per trial |
| State estimation | Done | wheel odometry + range-scan matching against the map, wide and whole-map re-localisation |
| Physical obstacle / contact interaction | Done | furniture, clutter, a moving robot vacuum, her body; contact forces logged per body |
| Telemetry: time, position/orientation XYZ, velocities, collision forces, control signals | Done, one gap | telemetry_robot.csv per trial. Gap: velocities are logged as forward speed and yaw rate; add vx, vy, vz columns before submission |
| Kinematic sketch | Done | outputs/robot_kinematic_sketch.png (to scale, guide robot), outputs/robot_look_concept.png (styling concept) |
| Robot matches the guide (1.10 m mast, 16.5 kg, r 0.08, track 0.38) | Done | tests/test_robot.py checks mass, centre of mass, tip-over limit, braking |

## B. Empirical rigour
| Requirement | Status |
|---|---|
| N = 120 simulated falls AND daily activities (sitting, lying on bed, tying shoelaces, dropping keys) | Code done (60 falls, 60 activities incl. all four named); needs the new run |
| Sensitivity, false-positive rate, precision, recall, F1, latency to trigger SOS | Code done (analyze.py: confusion matrices with confidence intervals, latency statistics, paired and Welch t-tests with df, t, exact p, Cohen's d, McNemar); needs the new run |
| Standard-error bars, p-values in a 4-page IEEE/ACM paper | Statistics done; the paper is NOT written; figures currently use confidence intervals, add standard-error bars |

## C. Critical rejection pitfalls
| Pitfall | Status |
|---|---|
| False alarm when sitting abruptly on a low sofa | Tested (12 abrupt + 8 slow sofa sits, sofa seat 0.47 m). With the small robot 5 of 20 raised a heads-up text (none became a dispatch). A map-based fix (ignore an apparent fall whose hip lies over a mapped seat) is NOT implemented yet. The 1.15 m camera may reduce this; the new run will say. If it is still above a few percent, implement the fix and rerun on a new seed |
| Privacy: edge inference, no cloud streaming of cameras | Done: all inference on the robot; telemetry shows 0 bytes left the robot before the first alert in every trial; only text plus one face-blurred picture after a confirmed emergency; the family platform streams no video and sends pictures only if she agreed |
| Physical mobility constraints | Done: friction zones, wheel/skid climb limit (rug ramps), 0.85 m and 0.90 m doors, collisions, braking, tipping limits |

## D. CSBS business statement
| Statement | Status |
|---|---|
| Long lie (more than 1 hour) cuts stay from 18.4 to 4.2 days | Used as the model input exactly as the sheet states it |
| Rhabdomyolysis and pressure necrosis prevented | Motivation only; no clinical model; do not claim it as a result |
| Robot cost under 3 months of a full-time attendant | An ASSUMPTION in the model (capital = 0.25 attendant-years); no bill of materials yet. Build a parts list expressed as a ratio, or state it as given by the brief |
| Immediate return on investment within the first calendar quarter | NOT met by the model: payback = 12 x 0.25 / (1 - kappa) = 3.75 months with kappa 0.20, which is longer than 3 months. It reaches 3 months only if capital is 0.20 attendant-years or less, or kappa is 0.0. Do not tune numbers to hit the claim; report 3.75 months and the sensitivity, or justify different inputs from a real parts list |
| Elder peace of mind measured with the Geriatric Depression Scale | NOT done and cannot be simulated honestly. State it as a planned outcome measure (pre/post GDS in a real deployment), not a result |
| 6-minute window, 134.5-minute rural ambulance, 50% six-month mortality (Tinetti NEJM) | Citations unverified or wrong journal; see docs/literature/LONG_LIE_AND_RESPONSE_TIME.md |

## E. Does the robot have to look like the picture?
No requirement asks for a particular look. The graded items are the MJCF kinematic tree, the sensors and actuators, closed-loop tracking, contact and the telemetry,
all of which exist. The friendly face-screen look is a design choice. A teal shell with arms like the picture can be added as visual-only geoms (no collision, no mass)
after the test run, without changing the physics; until then outputs/robot_look_concept.png shows how it would look on the guide's mechanism.

## F. Still to do before 26 Oct 23:59
1. Finish the dev and test reruns with the guide's robot, refit thresholds on dev, rerun analysis, economics and the family-platform checks.
2. Add velocity columns (vx, vy, vz) to telemetry.
3. Decide on the sofa false-alarm fix after seeing the new numbers.
4. Fill the dossier (Word template from the course pack), export the PDF, record the LinkedIn video, commit from each member's own account.
