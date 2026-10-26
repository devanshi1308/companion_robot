# Companion Robot (Group 02): what the project is, what is done, what the results say

Written 2026-10-19 for Devanshi Sachin Kambli (B029) and Kamakshi Bahuguna (E007). Everything here is a SIMULATION result. No real call, message or patient data is involved. Money never appears in this project: all economics are bed-days, attendant-years and ratios.

---

## 1. Problem statement (authorised title, unchanged)

"How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?"

In plain words: an older woman lives alone. If she collapses (fall, faint, cardiac event) and nobody sees it, every minute counts, and a long time on the floor makes outcomes worse. Our robot lives in the flat, follows her, watches her with its own camera, and if she goes down and does not answer "Are you okay?", it tells the family and calls an ambulance (all simulated). The question is whether this beats a system that cannot move.

### What the supervisor's feedback sheet asked for (this is what we answered)

| Sheet requirement | Status |
|---|---|
| N = 120 simulated falls AND daily-living activities | Done: 120 test trials (60 falls, 60 activities) |
| Activities: sitting down, lying on bed, tying shoelaces, dropping keys | Done, plus sitting and lying on the floor |
| Sensitivity, false-alarm rate, precision, recall, F1, latency to SOS | Done (tables in section 5) |
| Pitfall: false alarms when sitting abruptly on a low sofa | Included as a hard negative; 5 of 20 sofa sits still raised a heads-up text (section 6) |
| Pitfall: privacy (edge inference, no cloud streaming) | Done: all inference on the robot, 0 bytes left the robot before the first alert in every trial |
| Pitfall: mobility constraints (friction, climb limit, doorways, collisions) | Modelled: floor friction zones, climb limit, 0.85 m and 0.90 m doors, collision forces logged |
| MuJoCo rigid-body model with friction, joint limits, actuators | Done |
| Closed loop with trajectory tracking, disturbance injection, state estimation | Done: pushes, camera blackouts, odometry noise; odometry plus range-scan matching |
| Telemetry: time, position/orientation, velocities, collision forces, control signals | Done: one CSV per trial |
| Diverse clutter and obstacle velocities | Done: 0, 4 or 8 clutter items, moving robot vacuum at 0.1 to 0.5 m/s |
| Baseline for "reduces latency" | Done: one fixed camera and four fixed cameras |
| Heart attack: look at behaviour over a time window | Built (scripted pre-collapse cues and a cue monitor); result is negative, see section 6 |
| 4-page paper with error bars, p-values, CSBS ROI model | Statistics and economics model done; the paper itself is NOT written |
| Medicine reminder (user's extra wish) | Built as a demo only; outside the authorised scope; in no metric |

---

## 2. What was built

### 2.1 The flat (MuJoCo)
A 7 m by 6 m one-bedroom flat generated from one layout file (`src/sim/apartment_layout.py`, `build_apartment.py`): living-dining area, hallway, bedroom, 0.90 m and 0.85 m doorways, hardwood / laminate / carpet floors (friction 0.42 / 0.50 / 0.68), a low sofa (seat 0.47 m), coffee table, dining table with chairs, bed, wardrobe, a moving robot vacuum, rugs with ramped edges, a charging dock, and four fixed ceiling cameras for the baseline.

### 2.2 The woman
Habitat female_1 body (CC-BY-NC-SA 4.0, attribution required) turned into a MuJoCo skinned model with 33 MediaPipe-compatible landmark sites. Walking is a motion-capture gait replay. Falls are real physics (she trips about a planted foot, joint stiffness fades, arms brace). Scripted motions for daily activities are in `src/sim/human_motion.py` and `motions.py`.

Fall types (positives, 15 each in the test set): trip (forward), slip (backward), syncope (sudden loss of tone, sideways or forward), cardiac collapse (several seconds of pre-collapse behaviour first: she slows, presses a hand to her chest, hunches, sways).
Daily activities (hard negatives): abrupt sofa sit (12), slow sofa sit (8), lie down on the bed (10), tie shoelaces (10), drop keys and bend (10), sit on the floor (5), lie on the floor to stretch (5).

### 2.3 The robot
Small EMO-style wheeled robot (user's choice): deck 0.26 by 0.18 m, 1.2 kg, head with a face screen, pan-tilt camera at 0.16 m, differential drive, two passive skids. Design drawing: `outputs/robot_kinematic_sketch.png`.
Behaviour (`src/control/behavior.py`): WATCH, FOLLOW her, SEARCH when she is lost (go where she was heading, scan, tour the rooms), OBSERVE when she is on the floor, SUSPECT, APPROACH to about 1 m (controlled by a range sensor), CHECK_IN ("Are you okay?", repeat louder after 5 s, 10 s total), ALERT (family text with a face-blurred snapshot, ambulance call, updates).
Perception: MediaPipe pose landmarks plus depth give 3D body points. The fall detector (`src/vision/fall_detector.py`) uses hip drop speed, torso angle, bounding-box aspect ratio and its rise rate, then a 3-second stillness check; a second path flags a person found lying still for 5 seconds (fall not seen).
Navigation: occupancy map, A*, pure pursuit, wheel odometry corrected by 72-ray scan matching, wide and whole-map re-localisation, stuck recovery.
Dispatch (`src/control/dispatch.py`): heads-up text when a person is confirmed down, family messages plus ambulance call after an unanswered check-in, all-clear when she answers. Contacts are fictional. Wording never claims a diagnosis: "possible cardiac emergency".

### 2.4 The experiment machinery (`src/experiments/`)
- `scenarios.py`: seeded generator for 120 test trials and 40 dev trials. Falls are spread evenly over hallway, bedroom and living-dining area. Per trial it randomises: route, walking speed (0.5 to 0.9 m/s), event point, floor friction (x0.75 to x1.15), clutter (0, 4 or 8 items), vacuum speed, odometry noise, a push disturbance (50 percent), a camera blackout (30 percent), robot start (near her or far), and whether she answers the check-in.
- `run_trial.py`: the same recorded motion is run in three conditions, which makes the comparison paired:
  - robot: follow mode, 20 Hz perception, state machine, voice check-in;
  - 1 fixed camera: living-dining corner, same MediaPipe and detector, speaker and microphone within 4 m, no mobility;
  - 4 fixed cameras: living-dining, hallway west, hallway east, bedroom, one shared check-in.
- `fit_detector.py`: thresholds fitted on the dev split only (offline replay of recorded landmark streams) and then frozen. The 3-second stillness window (the guide's value) and the 5-second found-lying rule were deliberately not searched.
- `analyze.py`: confusion matrices with Wilson 95 percent intervals, latency statistics, paired and Welch t-tests (df, t, exact p, Cohen's d, 95 percent CI of the difference), exact McNemar test, figures.
- `eval_prodrome.py`, `src/vision/prodrome.py`: pre-collapse cue monitor.
- `analytics/healthcare_economics.py`: dimensionless economics driven by the measured results.
- Tests: `tests/test_apartment.py`, `test_robot.py`, `test_navigation.py`, `test_perception.py`, `test_fall_detector.py`, `test_motions.py` (all passing at the last run).

---

## 3. How it was run (so it can be repeated)

```bash
export MUJOCO_GL=glfw
source .venv/bin/activate
python src/experiments/run_experiments.py dev 40 1 --workers 5                 # development split
python src/experiments/fit_detector.py dev                                       # fit and freeze thresholds
python src/experiments/run_experiments.py test 120 2 --workers 5 --cfg outputs/experiments/frozen_config.json
python src/experiments/analyze.py test                                           # tables, statistics, figures
python src/experiments/eval_prodrome.py test
python analytics/healthcare_economics.py test
```
The test split was run once with frozen thresholds and never used for tuning. About 85 minutes with 5 workers. Results: `outputs/experiments/test/` (one folder per trial with spec, telemetry CSV, events, landmark streams, alerts) and `outputs/experiments/test/analysis/` (report.md, tables, figures, metrics.json, economics.json).

---

## 4. Problems found on the way (and fixed)
These matter because they show the setup is honest, and they are good "limitations and lessons" material for the paper.
1. MediaPipe hallucinated a full 28-point person from the floor lamp, as seen by the fixed camera, and preferred it to her. The lamp was removed; an audit now shows 0 phantom detections in the empty flat.
2. The 1.2 cm vertical rug edge stopped and spun the robot's small front skid, causing 0.3 to 1.3 m odometry error. Rug edges are now ramps; the error after crossing is at most 0.09 m.
3. Pure-pursuit steering flipped between full left and full right every step, which made the small wheels skid. Yaw rate is now slew-limited and capped, and speed is limited by the free space around the robot.
4. The whole-map re-localisation could jump the robot 3 m to a wrong pose. It is now accepted only when it is clearly better than the current estimate.
5. Random clutter sometimes walled the robot in. Layouts with unreachable places are now rejected.
6. The first version put 70 percent of falls where a living-room camera cannot see; falls are now spread evenly over the three zones.
7. The vacuum is a kinematic object that pushes through anything; it now pauses when the robot or the woman is within 0.55 m, like a real bumper.
8. Four early development rounds were discarded when these fixes changed the experiment.

---

## 5. Results (test split, 120 trials, frozen thresholds)

Alarm level means the family heads-up text was sent (positive = any of the 60 falls). Dispatch level means family emergency plus ambulance call (positive = a fall where she does not answer, 43 trials; a dispatch after she answered or in an activity trial counts as false).

| | Robot | 4 fixed cameras | 1 fixed camera |
|---|---|---|---|
| Alarm: sensitivity | 0.87 (52/60), CI 0.76 to 0.93 | 0.48 (29/60) | 0.02 (1/60) |
| Alarm: specificity | 0.75 (45/60) | 0.98 (59/60) | 1.00 |
| Alarm: precision / F1 | 0.78 / 0.82 | 0.97 / 0.64 | 1.00 / 0.03 |
| Dispatch: sensitivity (silent falls) | 0.86 (37/43), CI 0.73 to 0.93 | 0.47 (20/43) | 0.02 (1/43) |
| Dispatch: false dispatches | 0 of 77 | 0 of 77 | 0 of 77 |
| Fall to heads-up, median (mean, P95) | 20 s (26.5, 67) | 3.7 s | n/a |
| Fall to dispatch, median (mean, P95) | 40 s (42.5, 82) | 13.6 s | n/a |
| Dispatch within 60 s of the fall | 0.65 | 0.44 | 0.02 |
| Dispatch within 100 s of the fall | 0.86 | 0.44 | 0.02 |

Where she fell (alarm level, 20 falls per zone):

| Zone | Robot | 4 fixed cameras | 1 fixed camera |
|---|---|---|---|
| Living-dining | 19/20 (median 5.6 s) | 0/20 | 0/20 |
| Hallway | 18/20 (median 36 s) | 17/20 | 1/20 |
| Bedroom | 15/20 (median 52 s) | 12/20 | 0/20 |

Statistics, robot against 4 fixed cameras:
- Detection (60 falls): robot-only 28, cameras-only 5, both 24, neither 3; exact McNemar p = 7e-5.
- Latency where both detected (n = 24): robot slower by 30.1 s, 95 percent CI 21.3 to 39.0, paired t(23) = 7.03, p = 4e-7, Cohen's d = 1.43.
- Dispatch where both detected (n = 16): robot slower by 32.8 s, 95 percent CI 21.8 to 43.8, paired t(15) = 6.34, p = 1e-5, d = 1.58.
- Robot against 1 fixed camera: McNemar p below 1e-10 for both levels.

### What this means (the honest reading)
- The robot's advantage is COVERAGE: one device finds falls in every room, including the living area where the four fixed cameras saw nothing (0 of 20).
- Where fixed cameras do see her they are MUCH FASTER (about 4 s against 20 s to the heads-up).
- So "the robot reduces dispatch latency" is true only against a system that cannot see her (1 camera), and is false against four cameras on latency. What is supported: the robot dispatches for 86 percent of silent falls within 100 s from one device, against 47 percent for four cameras that cost four devices.
- Everything lands inside the 6-minute window in these trials (the slowest robot dispatch was 89 s), but trials were capped at 100 s after the fall.

### False alarms on daily activities (alarm level, robot)
Lie on floor 5/5 and sit on floor 5/5 (flagged by every camera type; her answer to the check-in cleared all 10, so no dispatch), abrupt sofa sit 2/12, slow sofa sit 3/8, drop keys 0/10, lie on bed 0/10, tie shoelaces 0/10. Specificity at alarm level is 0.75 (0.90 if the deliberate floor activities are excluded). The requirement of at least 98 percent holds only at dispatch level (1.00, 95 percent CI 0.95 to 1.00). In the sofa false alarms the detector logs show the landmark estimates collapsing (hip estimated at 0.0 to 0.1 m while she was seated at about 0.55 m); occlusion by the sofa or table is my guess and was not checked.

### Safety and privacy (robot, 120 trials)
- Commanded speed never exceeded 0.80 m/s (the standards manual limit).
- 0 bytes left the robot before the first alert in every trial.
- Median final position error 0.02 m; 8 trials ended above 0.5 m (lost, mostly while searching).
- Non-human contact at most 12 N (4 trials above 5 N).
- One trial: a collapsing cardiac patient landed on the robot (4580 N, robot thrown to 1.46 m/s, tilt 16.7 degrees). The robot follows too close to the landing zone.

### Heart-attack cue monitor (pre-collapse behaviour over a time window)
Chest-clutch plus hunch, slowing or sway, from landmark windows. Test: it flagged 13 of 15 cardiac trials before the collapse (median lead 6.5 s, minimum 1.7 s) but also flagged 51 of 105 other trials. That is a NEGATIVE result: it is not fit to trigger an alert, and the cues are scripted by us, not measured on patients. The system therefore detects collapse plus no answer, not a heart attack.

### Economics (dimensionless, assumptions named in the file)
- Net bed-days saved per patient-year: robot 14.7, 4 cameras 7.9, 1 camera 0.4.
- Operating cost ratio kappa = 0.20 (limit 0.25); payback 3.75 months (12 x 0.25 / (1 - kappa)); continuous vigilance replaced 4.2 FTE (168 h/week / 2080).
- Caveat: 0 false dispatches in 77 negatives only bounds the false-dispatch rate below 4.8 percent (95 percent), while kappa needs at most 0.51 percent; about 585 negative trials would be needed to show that. Alarm-level false alarms are 25 percent for the robot, which would mean many family texts a year if look-alike events were common.
- The 78.5-minute long-lie figure is still unverified; do not cite it until the source is checked.

---

## 6. Limitations to state in the paper
- Simulation only. Motions are scripted assumptions, not patient data; the body is an adult; syncope and cardiac patients stay unresponsive for the whole trial; "conscious but injured" is not modelled (an answer cancels the emergency).
- One floor plan (with randomised clutter, friction, obstacle speed, start pose). A second floor plan is future work.
- The fixed-camera baselines use our own camera positions; a better-placed set could do better. Their check-in assumes a microphone range of 4 m.
- Detector thresholds were fitted on replayed landmark streams; the robot's real stream would differ because its own motion changes what it sees.
- The robot is much smaller than the guide's 1.10 m robot (camera at 0.16 m, mass 1.2 kg). Deviations from the guide need the supervisor's approval, and the viva numbers must be recomputed for this robot. The 0.50 m clearance bubble in the standards manual conflicts with 0.85 m doors and needs a decision from the supervisor.
- The medicine reminder is outside the authorised scope: demo only, to be mentioned as future work.

## 7. What is NOT done yet
- The 4-page paper (figures exist in `outputs/experiments/test/analysis/figures/`), the 60 to 90 second video, and the viva preparation.
- Git: nothing is committed. Rules: conventional commits on feature branches (feat/b029-mujoco-physics-navigation and feat/e007-vision-pose-kinematics), at least 4 distinct feature commits each, vision and detector files under Kamakshi's branch. Local main differs from GitHub main, so a push needs a decision and is yours to run.
- Improvements for a NEW seed (never re-tune on the test split): keep the robot out of a person's fall landing zone; use the map to suppress alarms for low seats; better recovery from lost localisation; shorter patrol; a learned classifier on landmark sequences (the "data engine" idea); verify the long-lie and survival-decay citations; check that the survival decay wording matches the 17 percent per minute implied by lambda = 0.0031 per second.
- Run `scripts/audit_course_boundaries_and_rules.py` before submission (its "12 groups / 33 students" check cannot pass for one group). Remove tracked `__pycache__` files from the repository.

## 8. Where things are

| What | Where |
|---|---|
| Full test report with every table and test | `outputs/experiments/test/analysis/report.md` |
| Figures (latency CDF, detection by type and zone, false alarms) | `outputs/experiments/test/analysis/figures/` |
| Per-trial telemetry and events | `outputs/experiments/test/<trial id>/` |
| Frozen detector thresholds | `outputs/experiments/frozen_config.json` |
| Economics output | `outputs/experiments/test/analysis/economics.json` |
| Medicine reminder demos | `outputs/reminder_demo/`, `outputs/reminder_demo_missed/` |
| Pose contact sheets (activities, falls) | `outputs/poses/` |
| Local project memory (decisions, lessons) | `CLAUDE.md` (git-ignored) |

---

## 9. Added later (2026-10-19): demo features, not part of the measured results
These four were requested after the experiments. They are built, tested and shown live, but they are NOT in the 120-trial numbers above (the experiment code path is unchanged: a regression trial reproduced its earlier times exactly).

1. **Momo, an agent with feelings** (`src/agent/`). A Strands agent whose feelings (worry, alarm, joy, calm) change with events and colour the robot's face and tone. Everything the robot says to her and every text to the family is phrased by Momo. The simulator decides the facts; Momo decides the wording; answers are checked (facts present, no diagnosis wording, short); the ambulance script is never rephrased. No model key was available here, so only the offline wording and the checking logic were exercised; real model output is untested. With a key (`ANTHROPIC_API_KEY`), a local model (`OLLAMA_HOST`) or AWS credentials it switches to a real model. Only text reaches a model, never video.
2. **Family platform** (`src/family_platform/`). A local web page: where she is on the floor plan, what she is doing, last seen, whether she took the tablet (and whether the robot saw her do it), alerts, the siren, Momo's feelings and every message Momo said or sent. The family can talk to her through Momo, send a reminder now, ask Momo to check on her, tilt the camera, ask for a face-blurred picture (only if she agreed), and silence the siren. No video is streamed, you must sign in (per-person login), the server listens only on this computer. Checked in a browser: tablet flow (reminded, said OK, taken and seen), cardiac flow (emergency banner, siren rings, snapshot, silence), wrong PIN rejected.
3. **Camera that looks above and below.** The head camera tilts from -75 to +70 degrees (the guide's default is -45 to +30; the experiments used the default), nods while searching, and obeys "look up / level / down" from the family page. I read "see above and below" as one wider-range tilting camera, not a second camera; tell me if you meant two cameras.
4. **Siren for a collapse.** When she has collapsed and does not answer, the robot sounds a loud two-tone alarm (95 dB at 1 m; 100 dB if a chest-clutch pattern was seen just before), calls out "HELP! A woman has collapsed in the living room! Please come now and call 108!", and texts the family and the neighbour. It sounds for any unanswered collapse, because a camera cannot tell a heart attack from another collapse; the cue only makes it louder. A closed door cuts it to about 60 dB at 3 m, so it reaches people close by and the texts reach everyone else. It stops when she gets up, when the family silences it, or after 180 s. The sound is simulated (a WAV file, optional playback).

Run: `python src/sim/run_platform_demo.py --scenario medicine --agent` (or `cardiac`), open http://127.0.0.1:8765, PIN 1234. Tests: `tests/test_agent.py`, `tests/test_platform.py`.
Limits: the "tablet taken" check is verified only on a scripted hand-to-mouth gesture; the prodrome cue monitor has a 49 percent false-flag rate, so it must not decide whether to sound the siren; the family PIN and local-only server are demo-grade security, not a production design.
