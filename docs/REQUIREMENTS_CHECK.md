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

## Final title sheet (final title.pdf, MDRIIA 2026-27): what it adds and where we stand

Source: "Final PBL Titles, MuJoCo Simulation Blueprints, Business Systems ROI & Robotics Conference Directory". Group 02 page restates the authorised title (unchanged), the N = 120 falls plus ADLs, the three rejection pitfalls and the MuJoCo telemetry list. New or stricter points, and status:

| Requirement in the sheet | Status |
|---|---|
| Title in Aalborg-UNESCO form (stakeholder + MuJoCo mechanism + measurable metric); never altered | Done (title unchanged everywhere) |
| Technical mechanism: mast pan-tilt camera, MediaPipe fall kinematics, mobile chassis, domestic clutter | Done (guide robot: 1.10 m mast, pan-tilt, 0.44 x 0.34 m chassis, cluttered flat) |
| Rapid autonomous navigation to the fallen person; bounding-box / skeletal aspect-ratio velocity thresholding (MediaPipe/OpenCV); automated local dispatch to EMS and caregivers | Built (A* + pure pursuit, aspect ratio and its rise rate, simulated dispatch). Numbers for the guide robot are not final |
| MJCF kinematic tree with friction, limits, actuators; closed loop with disturbance injection and state estimation | Done |
| Telemetry: time, X/Y/Z and orientation, velocities, collision forces, control signals | Mostly: velocity columns vx, vy, vz still to add |
| N = 120 falls and ADLs; precision, recall, F1, latency to SOS | Harness built; the 120-trial run on the guide robot is NOT done. Only the archived small-robot run is complete |
| Pitfall: abrupt low-sofa sitting; edge inference, no cloud streaming; mobility constraints | Sofa sit included (2 to 3 of 20 sofa sits still raised a heads-up text in the small-robot run); privacy: 0 bytes off-board before an alert; mobility: friction, climb limit, doors, collisions modelled |
| Manuscript: 4 pages, standard-error bars, p-values, CSBS ROI model | NOT written |
| COPE: every data point, chart and error bar must come from MuJoCo CSV telemetry in the Git repository | Rule: outputs/ is git-ignored, so the telemetry CSVs the paper cites must be committed (a trimmed set) before submission |
| COPE: citations must be authentic (Hendrich JONA, Tinetti NEJM, AHA ECC) | Open: our check found Tinetti 1993 is in JAMA, not NEJM; Hendrich and AHA/ERC entries still to verify with real DOIs |
| Viva: each student modifies MJCF parameters and re-runs the controller live | Prepare: build_robot_mjcf.py / robot_spec.py constants, run_demo.py |
| Economics: long lie slashes stay 18.4 to 4.2 days (the roster table says "14 days"); robot cost under 3 months of an attendant; return inside the first calendar quarter; GDS peace of mind | Model built, dimensionless. Payback was 3.75 months in the small-robot run, which is MORE than a quarter: report honestly. GDS cannot be simulated: name it as a future measurement |
| Sheet cites decay of 7-10 percent per minute | Our lambda 0.0031/s is about 17 percent per minute: change lambda or wording before submission |
| Venues: IndiaHCI (https://www.indiahci.org/), IEEE RO-MAN (https://ro-man2026.org/, CORE B); faculty mentor listed as co-author | Paper pending; add mentor as co-author |
