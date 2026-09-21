# Master Prompt: Companion Robot (MDRIIA Group 02)

Status: DRAFT v0.1, written 2026-09-21. The owner will add further requirements; every phase below is open to change.
Audience: Claude Code (or any coding agent) working in this repository, and the two team members.

---

## 0. How to work in this repo

1. **Use the graph first.** `code-review-graph` is installed and configured (see `CLAUDE.md`). Use its MCP tools (`semantic_search_nodes_tool`, `query_graph_tool`, `get_impact_radius_tool`, `detect_changes_tool`) to narrow scope, then read the source. The source wins over the graph.
   - Limitation today: the graph indexes only git-tracked files, so `Group_02_Kamakshi_Devanshi/` (untracked) is not in it. Re-run `code-review-graph build` after each phase is committed.
2. **Plan before coding.** For each phase, state the plan and the Definition of Done (DoD), then implement, then run the verification listed.
3. **Never invent results.** Every number in the paper, README or dashboard must come from a script that can be re-run. No hardcoded confusion matrices, latencies or economics outputs presented as measurements.
4. **Follow the teacher's rules** (section 2). They are enforced by `Group_02_Kamakshi_Devanshi/scripts/audit_course_boundaries_and_rules.py`.

---

## 1. Project in one paragraph

A MuJoCo simulation of a wheeled companion robot with an elevated camera mast that patrols a living room, detects when a simulated elderly person falls (kinematic features from pose landmarks), approaches to a safe standoff distance (0.80 to 1.20 m), issues a simulated voice check-in, and on no response emits a simulated emergency-dispatch alert. We measure detection quality (sensitivity, specificity, precision, F1) and fall-to-alert latency over N >= 50 (target 100) randomized trials, compare against a static ambient-sensor baseline, and add a dimensionless healthcare-economics model.

**Authorized title (do not alter):**
"How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?"

**Team and ownership**

| Person | Roll | Branch (roster value) | Owns |
|---|---|---|---|
| Kamakshi Bahuguna | E007 | `feat/e007-vision-pose-kinematics` | Vision, pose kinematics, filtering, confusion-matrix benchmark |
| Devanshi Sachin Kambli | B029 | `feat/b029-mujoco-physics-navigation` | MJCF models, physics, navigation and standoff control, economics |

---

## 2. Hard constraints from the teacher's package

- **Edit only inside `Group_02_Kamakshi_Devanshi/`.** Never touch root files of the course monorepo or another group's folder.
- **Zero-currency rule:** no currency symbols or words (rupees, dollars, INR/USD + number). Economics must be dimensionless ratios (kappa, payback in months, bed-day ratios). Violation is a 5-mark deduction.
- **No emojis, no faculty names, no forbidden tokens** in any file inside the group folder (the audit script scans for these).
- **Citations:** 5 to 6 real papers with working DOIs. Fabricated or hallucinated DOIs give zero for Milestone 4. Verify each DOI resolves before citing.
- **Git:** conventional commits (`feat(scope)`, `fix`, `perf`, `docs`, `test`), branch names `feat/<roll>-<module>`, PRs only, zero direct pushes to `main`. Each student's work must be traceable to their own commits.
- **Paper:** 4 pages, IEEEtran two-column, 3 figures, 2 tables, 5 genuine citations with DOIs.
- **Video:** 60 to 90 s (intro 10 s, simulation 40 s, telemetry 20 s, business impact 10 s), posted on LinkedIn with the mandatory tags; URL goes in `docs/TEAM_ROSTER.json` under `project_showcase.linkedin_url`.
- **Rubric milestones:** M1 weeks 1-2 (10 marks), M2 weeks 3-6 (20), M3 weeks 7-10 (20), M4 weeks 11-12 (50: paper 15, live demo 15, individual viva 15, git hygiene 5).

---

## 3. Feasibility verdict (from reading every file in the teacher's folder)

**Overall: doable in 3 to 4 weeks by two people, but only if the scaffold's "results" are replaced with real simulation output.** Details:

### 3.1 What is solid
- Physics engine, robot type and scope are realistic: differential-drive base, mast, scripted human fall, kinematic discrimination, state machine.
- The kinematic feature set (mid-hip descent velocity, torso pitch, bounding-box aspect ratio, hip height, post-fall stillness window) is standard and implementable from either MediaPipe landmarks or MuJoCo ground truth.
- The 2nd-order Butterworth at fc = 5 Hz, fs = 30 Hz gives about 45 ms group delay; the viva answer is correct.
- ISO-style stopping arithmetic checks out: S_stop = 0.50*(0.10+0.05) + 0.50^2/(2*1.0) = 0.20 m. Rollover and slip numbers in the B029 viva answer also check out (CoM height about 0.231 m, a_slip about 3.92 m/s^2, a_tip about 7.64 m/s^2).

### 3.2 Problems that must be fixed or consciously handled

| # | Issue | Evidence | Resolution |
|---|---|---|---|
| 1 | **Scaffold results are synthetic.** `src/fall_detection_kinematics.py` never touches MuJoCo or MediaPipe. It loops 100 times, assigns hardcoded feature values (e.g. `i in [14, 37]` are forced false negatives, `i == 77` a forced false positive), and latency comes from `48.3 + 6.4*sin(i*0.4)`. The 96% / 98% / 48.3 s figures in the guide and dashboard are therefore not measurements. | `src/fall_detection_kinematics.py`, guide section 9 | Replace with a real pipeline (phases 3 to 6). Keep the scaffold file only as the interface reference, and regenerate `analytics/fall_triage_benchmark.csv` from real runs. Submitting the synthetic CSV as empirical data is an integrity and grading risk. |
| 2 | **MediaPipe on a MuJoCo render is unreliable.** BlazePose is trained on real human photos; capsule/box avatars usually are not detected. | Title requires MediaPipe | Use a two-track design: (A) primary, MuJoCo ground-truth joint positions mapped to a 33-landmark-compatible vector plus calibrated noise, dropout and occlusion (state this honestly as a landmark surrogate); (B) MediaPipe evaluated on real fall video or a public dataset (e.g. UR Fall Detection) by E007 to justify the thresholds; (C) stretch: try MediaPipe on rendered frames of a MuJoCo humanoid and report the detection rate. |
| 3 | **Latency is a sum of constants.** 48.30 s = 0.35 + 3.00 + 4.50 + 10.00 + 0.45 + 30.00; the last two (and the 10 s voice challenge) are assumed, not measured. | Guide section 7.2 | Measure in simulation: detection time, stillness window, navigation time, and challenge timer from sim clock. Keep packet transit and EMS gateway as clearly labelled model parameters with cited ranges, and report them separately. |
| 4 | **Survival-decay numbers disagree.** exp(-0.0031 * 60) = 0.83, which is about a 17% relative drop per minute, not "about 10%". For 10% per minute, lambda is about 0.00176 s^-1. | Guide section 7.1 | Fix lambda or the wording. Also earlier team notes (`docs/problem_statement_and_literature.md`) recommend citing the AHA per-minute decay (7 to 10% per minute) rather than a hard "6-minute" claim; reconcile with the authorized title in the paper's limitations. |
| 5 | **Falls are not the same as cardiac arrest.** The framing conflates a fall with cardiac arrest; the "Devil's Advocate" box in the README already flags false-alarm risk. | README section 1 | Frame in the paper as: detection-to-alert latency for unwitnessed collapse, with cardiac arrest as the motivating worst case. Report false-alarm cost (already in B029 viva Q2). |
| 6 | **Economics outputs are asserted constants.** kappa = 0.255, monthly savings = 0.242, bed-days 18.4 vs 4.2, baseline lie 78.5 min are typed in. | `analytics/geriatric_care_economics.py` | Make it a parameterised model with a sensitivity sweep; take inputs from the cited papers (verify 78.5 min and 18.4 days in Kubitza et al. 2022 before using them) and tie sensitivity/specificity to the measured values from phase 6. |
| 7 | **Existing robot model is a stub.** `models/elderly_companion_base.xml` is a single free-joint cylinder: no wheels, no actuators, no pan-tilt, no camera, no human. | model file | Build phases 1 to 3. |
| 8 | **Doc inconsistencies.** Branch is `feat/...` in the roster but `feature/...` in guide section 11; requirements list no `mediapipe`; guide lists deliverable paths (`src/vision/...`, `src/control/...`, `benchmarks/...`) that differ from the scaffold's flat `src/`. | roster vs guide | Follow the roster branch names; adopt the guide's deliverable paths (they are what the viva refers to); add `mediapipe` only if track B/C is used. Ask the faculty if unsure. |
| 9 | **Two competing repos.** The owner's own `companion_robot/` (scenes, scripts, venv) and the teacher's group folder overlap. | repo root | Resolve with the structure in section 4. |
| 10 | **Tooling.** `sceneenv/` is a broken venv (created at another path, `bin/python` missing). System Python is 3.13 and has no `mujoco`. MediaPipe wheels may lag newest Python versions. | shell checks | Create a fresh `.venv` with Python 3.12 inside the group folder (or repo root), install teacher's `requirements.txt`, pin what actually installs. |

### 3.3 Scope call
Keep the scope to exactly one scenario: **unwitnessed fall -> detect -> approach -> check-in -> simulated alert.** Anything else (medication reminders, remote video, companion app, conversation) is out of scope for grading and should be a "future work" paragraph only. The root README mentions a future companion app and person tracking; treat those as future work.

---

## 4. Target repository structure

Decision needed from the owner (see section 8): the teacher's package is the graded deliverable and must live in the monorepo's group folder. Recommended layout, keeping the owner's existing work by moving it in:

```
Group_02_Kamakshi_Devanshi/            <- the only place edits are allowed in the course monorepo
|-- README.md, RESEARCH_AND_IMPLEMENTATION_GUIDE.md, CONTRIBUTING.md, ...   (teacher-provided, keep)
|-- requirements.txt                   (teacher's; extend, do not shrink)
|-- models/
|   |-- companion_chassis.xml          <- B029: diff-drive base, mast, pan-tilt, camera site, actuators
|   |-- domestic_environment.xml       <- B029: from scenes/living_room.xml + friction zones + doorways
|   |-- human_subject.xml              <- B029/E007: articulated humanoid with named landmark sites
|   |-- scene_composed.xml             <- includes the three above
|   `-- elderly_companion_base.xml     (scaffold, keep until superseded)
|-- src/
|   |-- test_env.py                    (teacher's)
|   |-- sim/        world.py, scenario_generator.py, human_fall_driver.py
|   |-- vision/     landmark_source.py, blazepose_tracker.py, butterworth_filter.py, kinematics_engine.py
|   |-- control/    diff_drive.py, standoff_controller_iso13482.py, state_machine.py, dispatch.py
|   |-- analytics/  healthcare_economics.py
|   `-- fall_detection_kinematics.py   (scaffold; becomes a thin wrapper around the real pipeline)
|-- benchmarks/     run_trials.py, eval_confusion_matrix.py, baseline_static_sensor.py
|-- analytics/      fall_triage_benchmark.csv (regenerated), generate_paper_figures.py, stats.py
|-- tests/          test_model_loads.py, test_filter.py, test_kinematics.py, test_controller.py
|-- docs/           TEAM_ROSTER.json, paper blueprint, figures/
`-- scripts/        (teacher's scripts; do not modify)
```

Root of `companion_robot/` (owner's workspace, outside the graded folder):
- Keep `prompt.md`, `CLAUDE.md` and friends, `.venv`. Consider adding the tool-generated files (`.cursor/`, `.gemini/`, `.qoder/`, `.codebuddy/`, `.kiro/`, `.windsurfrules`, `AGENTS.md`, `GEMINI.md`, `QODER.md`, `CODEBUDDY.md`, `opencode.jsonc`) to `.gitignore` so they never reach the course PR.
- `scenes/living_room.xml` and `scripts/open_scene.py` move into the group folder (phase 1) and the root `README.md` is reduced to a pointer.

---

## 5. Phases

Each phase lists: goal, tasks, owner, DoD, verification. Phases map to rubric milestones.

### Phase 0: Foundation, environment and hygiene (M1, days 1-2)
**Goal:** a clean, reproducible workspace and correct git setup.
- Tasks
  1. Create `.venv` on Python 3.12; install `Group_02_Kamakshi_Devanshi/requirements.txt`; confirm `mujoco` imports; add `mediapipe`, `opencv-python`, `pytest` only when needed.
  2. Run `python src/test_env.py` (all green) and the teacher's audit script; save outputs.
  3. Update `docs/TEAM_ROSTER.json` (`github_handle`, `institutional_email`) for both members.
  4. Create the two feature branches; agree on commit-message scopes; one PR per module.
  5. Update root `.gitignore`; decide the repo layout (section 4).
  6. Rebuild the code graph after the first commit.
- Owner: both (each does their own roster entry).
- DoD: `test_env.py` passes; audit script reports no violations; roster is valid JSON; first PR opened.

### Phase 1: Domestic environment (M2, week 3)
**Goal:** the living room as a proper MJCF world with the features the guide requires.
- Tasks
  1. Move `scenes/living_room.xml` to `models/domestic_environment.xml`; keep the room, sofa, table, TV, shelf, lamp.
  2. Add floor friction zones (hardwood 0.42, laminate 0.50, low-pile carpet 0.68) and give the existing rug the carpet friction and real contact (it currently has `contype=0`).
  3. Add clutter/obstacles that create occlusion layouts (2 to 3 configurations) and doorway(s) 0.80 to 0.90 m wide.
  4. Replace the decorative non-colliding door/window as needed; make walls a sensible height; fix the hidden-shelf and inconsistent geometry noted in the file comments.
  5. Provide named sites/bodies: `patrol_waypoints`, `fall_zone_*`.
- Owner: B029.
- DoD: scene loads headless and in the viewer; `tests/test_model_loads.py` passes; screenshot of each layout saved for the paper.

### Phase 2: Robot model and low-level control (M2, week 3-4)
**Goal:** a physically credible differential-drive robot with mast, pan-tilt and camera.
- Tasks
  1. `models/companion_chassis.xml`: chassis, two driven wheels (r = 0.08 m, track L = 0.38 m), two passive casters (low-friction spheres), mast to 1.10 m, 2-DOF pan (+/-90 deg) / tilt (-45..+30 deg) with position actuators, camera with 58 deg vertical FOV, mass properties matching the guide (chassis about 14 kg, mast about 2.5 kg).
  2. `src/control/diff_drive.py`: (v, omega) -> wheel velocity commands; odometry from MuJoCo state.
  3. Validate against the guide: kinematics equations, stopping distance at v = 0.5 m/s and mu = 0.40 (no tipping, no slip at 1.0 m/s^2 decel), camera blind-zone about 0.33 m.
- Owner: B029.
- DoD: robot drives straight and turns within tolerance; stops within 0.20 m of commanded stop at 0.5 m/s; pan-tilt reaches commanded angles; unit tests pass.

### Phase 3: Human subject and scenario generator (M2 to M3, week 4)
**Goal:** repeatable, randomized falls and ADLs.
- Tasks
  1. `models/human_subject.xml`: articulated body (about 12 to 17 links) with sites at all landmarks needed (nose, shoulders, hips, knees, ankles, etc.) so a 33-landmark-compatible vector can be produced.
  2. `src/sim/human_fall_driver.py`: scripted motions: forward trip, backward slip (mu = 0.40), lateral syncope, chair collapse; ADLs: rapid sitting, bending to tie shoes, lying down on a bed/sofa, couch reclining, floor exercise.
  3. `src/sim/scenario_generator.py`: seeded randomization (start position, heading, speed, friction, layout, occlusion) so that N = 100 (50 falls + 50 difficult ADLs) is reproducible from a seed.
  4. Sanity check that fall descent speeds and postures fall into plausible ranges (compare to the guide's table in section 5.2); document where the simulation differs from real people.
- Owner: B029 (models, driver) with E007 (which landmarks and ranges are needed).
- DoD: 100 scenarios run headless without physics blow-ups; feature ranges per class are plotted; seed reproduces identical trials.

### Phase 4: Perception and kinematics (M2 to M3, weeks 3-5)
**Goal:** the detector, computed from landmarks, robust to noise and occlusion.
- Tasks
  1. `src/vision/landmark_source.py`: interface with two implementations: `GroundTruthLandmarks` (MuJoCo sites + Gaussian noise + dropout + occlusion mask by line-of-sight) and `MediaPipeLandmarks` (optional, on rendered frames).
  2. `src/vision/butterworth_filter.py`: 2nd-order low-pass, fc = 5 Hz, fs = 30 Hz; causal (no look-ahead); unit test for group delay < 60 ms.
  3. `src/vision/kinematics_engine.py`: mid-hip and mid-shoulder centroids, v_z (filtered), torso pitch, bounding-box aspect ratio, hip height; camera-to-base transform using pan/tilt and mast height; metric scaling via torso length when depth is unavailable.
  4. Detector: impact rule (|v_z| >= 1.80 m/s, theta >= 60 deg, AR >= 1.20, z_h <= 0.20 m) followed by the 3.0 s stillness window (mean hip speed < 0.05 m/s). Thresholds live in one config file.
  5. Track B: run real MediaPipe on public fall/ADL video to show the thresholds are plausible for real data (report as supporting evidence, not as the main result).
- Owner: E007 (B029 provides the transform frames).
- DoD: on recorded trial telemetry, the detector produces a confusion matrix; filter/kinematics unit tests pass; thresholds are justified in comments and paper.

### Phase 5: Response behaviour and state machine (M3, week 5-6)
**Goal:** closed loop from patrol to alert.
- Tasks
  1. `src/control/state_machine.py`: PATROL -> SUSPECT -> CONFIRMED -> APPROACH -> CHECK_IN -> DISPATCH (plus RECOVERED/CANCELLED for false alarms and person-responds cases).
  2. `src/control/standoff_controller_iso13482.py`: go-to-pose with obstacle avoidance (start with a simple potential-field or A* on a grid); stop at 1.00 m from the person (allowed 0.80 to 1.20 m); never touch the person; clamp deceleration to 1.0 m/s^2.
  3. Check-in model: a simulated "Are you okay?" prompt with a response probability and delay for ADL cases (this is what keeps specificity high, per viva Q2); no response within the timer (default 10 s) triggers dispatch.
  4. `src/control/dispatch.py`: builds the alert payload (timestamp, location, confidence, trial id) and appends it to the log; the network/EMS step is a labelled parameter.
  5. Patrol policy: waypoint loop covering the room; report time-to-first-observation as a dependent variable because the robot must first see the person.
- Owner: B029 (control, navigation), E007 (detector hooks, confidence score).
- DoD: end-to-end run of a single trial prints the event timeline; standoff distance recorded; no collisions with the human in the trial set.

### Phase 6: Experiments and telemetry (M3, weeks 6-8)
**Goal:** real, reproducible data.
- Tasks
  1. `benchmarks/run_trials.py`: runs the 100 scenarios (seeded), logs per-step telemetry (at least 5 variables: time, robot x/y/yaw, v, omega, hip height, v_z, torso angle, AR, state) and per-trial summary rows.
  2. Regenerate `analytics/fall_triage_benchmark.csv` from the runs; keep the raw telemetry files.
  3. `benchmarks/baseline_static_sensor.py`: the comparison arm (fixed ambient camera with limited field of view) for the "robot vs static" independent variable.
  4. Sweeps: friction (0.40, 0.50, 0.68), 2 to 3 furniture layouts (occlusion), landmark noise level.
  5. `benchmarks/eval_confusion_matrix.py`: TP/FP/FN/TN, sensitivity, specificity, precision, F1, latency distribution (mean, SD, median, P95, max).
- Owner: both; E007 leads metrics, B029 leads run orchestration.
- DoD: `python benchmarks/run_trials.py --seed 0` reproduces the same CSV; N >= 50 (target 100); results reported even if worse than the scaffold's claims.

### Phase 7: Statistics and economics (M3, week 8-9)
**Goal:** formal hypothesis testing and a dimensionless economics model tied to measured data.
- Tasks
  1. `analytics/stats.py`: t-test (or Mann-Whitney if not normal), p-value, Cohen's d, 95% confidence intervals for latency robot vs baseline and for sensitivity/specificity (Wilson intervals).
  2. `src/analytics/healthcare_economics.py`: parameterised model (bed-days, long-lie duration, kappa, payback), inputs cited; sensitivity sweep over specificity and fall rate; compute the minimum specificity for viability from the measured false-positive rate; strictly no currency anywhere.
  3. Reconcile the survival-decay constant (issue 4).
- Owner: E007 (classification and latency stats), B029 (economics).
- DoD: every economics output is produced by code from cited inputs; both null and alternative hypotheses are explicitly accepted or rejected with numbers.

### Phase 8: Figures, paper, video, viva (M4, weeks 10-12)
**Goal:** all graded deliverables.
- Tasks
  1. Run `analytics/generate_paper_figures.py` on live data: Figure 1 architecture, Figure 2 kinematic telemetry, Figure 3 comparative performance; export at 300 DPI.
  2. Write the 4-page IEEE paper in `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` (then port to IEEEtran): 3 figures, 2 tables, 5 verified citations with DOIs, honest limitations (landmark surrogate, simulation-to-real gap, assumed EMS constants).
  3. Record the 60 to 90 s demo, post on LinkedIn with the mandatory tags and hashtags, put the URL in `TEAM_ROSTER.json`, sync via `scripts/sync_showcase_links.py`.
  4. Individual viva prep: each person can explain, run and modify their own modules; rehearse the two viva questions per person in the guide, using the real numbers.
  5. Final audit: run `scripts/audit_course_boundaries_and_rules.py`, check DOIs, check commit history per person, open the final PR.
- Owner: both.
- DoD: rubric checklist in section 7 fully ticked.

---

## 6. Suggested schedule (adjust to the actual academic week)

| Week | Focus | Milestone |
|---|---|---|
| 1-2 (done or in progress) | Phase 0, problem statement, roster, PR | M1 |
| 3 | Phases 1, 2 start; Phase 4 landmark interface | M2 |
| 4 | Phases 2 finish, 3, 4 | M2 |
| 5-6 | Phases 4 finish, 5 | M2 to M3 |
| 7-8 | Phase 6 | M3 |
| 9-10 | Phase 7, first figure set | M3 |
| 11-12 | Phase 8 | M4 |

Critical path: Phase 2 (robot) -> Phase 3 (human) -> Phase 5 (loop) -> Phase 6 (data). Phase 4 can run in parallel using recorded telemetry from Phase 3.

---

## 7. Final acceptance checklist (rubric-aligned)

- [ ] Roster complete, both branches exist, PR(s) merged with conventional commits
- [ ] MJCF model valid, friction and damping set, loads without warnings
- [ ] Control loop runs end to end without runtime errors
- [ ] Telemetry CSV with >= 5 state variables
- [ ] N >= 50 (target 100) seeded runs, reproducible from one command
- [ ] t-test, p-value, Cohen's d, 95% CI reported; H0 and H1 resolved
- [ ] Dimensionless economics (kappa, payback) computed from inputs; zero currency
- [ ] 4-page IEEEtran paper, 3 figures, 2 tables, 5 verified DOIs
- [ ] 60 to 90 s LinkedIn video, tags correct, URL in roster
- [ ] Live demo script rehearsed; each student can defend their own code
- [ ] Audit script clean; no results anywhere that are hardcoded or synthetic

---

## 8. Open questions for the owner

1. **Repo layout:** move everything into `Group_02_Kamakshi_Devanshi/` (recommended), or keep the root repo and copy the group folder into the monorepo only at submission?
2. **Human model:** is a simple articulated capsule human acceptable, or should we use MuJoCo's stock humanoid (more realistic falls, harder to script)?
3. **MediaPipe depth:** is ground-truth landmarks plus noise (tracks A and B) acceptable to the faculty, or must MediaPipe run inside the simulation loop (track C)? Worth confirming with the faculty early.
4. **Division of work:** the roster splits vision (E007) and physics/navigation/economics (B029). Which of the shared items (state machine, run orchestration) does each person take?
5. **Which week are we in**, and are there deadlines earlier than the rubric ranges?
6. **Extra requirements** the owner wants to add on top of this plan (to be merged into these phases).

---

## 9. Prompt template for each phase

Paste this into a fresh Claude Code session, replacing the bracketed parts:

> Read `prompt.md` sections 0 to 3 and Phase [N]. Use the code-review-graph tools to see what already exists, then propose a short plan with the exact files you will create or change. Wait for my approval. After approval implement it, run the phase verification, and report: what changed, what passed, what did not, and any number that came from a script (with the command that produced it). Do not hardcode results. Stay inside `Group_02_Kamakshi_Devanshi/`. No currency terms, no emojis. Use conventional commits on branch `[branch]`.
