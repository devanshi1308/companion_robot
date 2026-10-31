# Devanshi (B029): prep pack for the 31 Oct jury

Your role in the roster: MuJoCo physics, navigation, healthcare economics. Every number below comes from
`results/guide_robot_test/` (120 test trials, seed 2, thresholds frozen from dev seed 1) and
`results/business_analysis/model.json`. No currency anywhere: the unit is U = one attendant-year.

## 1. What the briefing asks for

- Slot 2, MDRIIA-G02. Be seated 12:55, ready 1:00, present 1:10 to 1:20, studio 1:22 to 1:25 (8th floor).
- 10 minutes in front of the panel: 0 to 4 pitch and live demo, 4 to 7 one question from each judge, 7 to 9 one line of advice from each, 9 to 10 scoring.
- Timekeeper rings at 4:00, 7:00, 9:00, 10:00. Keep strictly to 4 minutes.
- No slides. Live MuJoCo simulation, laptop fully charged, charger, HDMI or USB-C adapter. Formals and ID card.
- Every member presents their own part. The faculty judge checks you against the role in the GitHub roster. Work you cannot explain goes to faculty review.
- Marks: 2 x A (industry judge in the lab, averaged with the business judge: costs, savings, who pays, sourced numbers, realistic payback, next step), 2 x B (technology judge: MuJoCo runs live, justified parameters, repeated trials, results feed the business model), D (you, individual, faculty judge: explain your part, link it to the whole, answer confidently).
- Studio (2.5 to 3 min): a different member answers each prompt, everyone speaks once. Prompts 2 and 3 must match your dossier.

The four-minute pitch in the briefing:

| Time | What | Who |
|---|---|---|
| 0:00 to 0:30 | Team and the real problem | one member |
| 0:30 to 2:30 | Live demo, each member shows the part they built | every member |
| 2:30 to 3:30 | Evidence: trials, results, and their limits | one or two members |
| 3:30 to 4:00 | The next real step | one member |

## 2. Your talk track (about 60 s in the demo, 45 s in the evidence slot)

**Demo, your part (physics and navigation), while the simulation runs:**
"This is the flat in MuJoCo, built from one layout file: rooms, doors 0.85 and 0.90 m, and three floors with friction 0.42, 0.50 and 0.68. The robot is 16.5 kg on two driven wheels, with the camera 1.15 m up. It follows her, and when she falls it checks she is lying still, drives to about 1 m, and asks if she is okay. The robot plans around furniture, and it slows to 0.2 m/s near obstacles. Its speed is capped at 0.8 m/s, and its braking is 2.45 m/s squared on the 0.40 floor, above the 1.5 the manual needs. The wheels slip at 3.92 and it would tip at 7.74, so the wheels slip first and it never tips."

**Evidence, your part (economics):**
"We ran 120 seeded trials, 60 falls and 60 everyday activities. The robot dispatched 28 of the 43 falls where she did not answer, 65%. Four fixed cameras got 47% and one camera got 5%. Where both detect, the robot is slower, by about 38 s. The robot's strength is coverage: one device in every room. In the business model only two inputs are measured, the dispatch rate and the false-dispatch rate. The other twelve are labelled assumptions. On clinical value alone the robot does not pay back: kappa is 0.45 against a limit of 0.25, and payback is 5.5 months. It breaks even if it replaces about 10% of monitoring time. We report that honestly."

Do not say: "pays back in a quarter", "reduces latency", "safe", "heart attack detected".

## 3. Numbers to know cold

| Item | Value |
|---|---|
| Robot | 16.5 kg, chassis 0.44 x 0.34 x 0.16 m, wheel r 0.08, track 0.38, mast 1.10 m, camera 1.152 m |
| Physics | timestep 0.002 s (500 Hz), floor friction 0.42 / 0.50 / 0.68, telemetry logged at 20 Hz |
| Speed and braking | cruise 0.50 m/s, cap 0.80 (max commanded 0.77), normal braking 1.0, emergency 1.5 required, measured 2.45 m/s2 |
| Tip and slip | a_tip = g d / h = 9.81 x 0.18 / 0.228 = 7.74 m/s2; a_slip = mu g = 3.92 m/s2; force 40.4 N needed vs 64.7 N available (margin 1.60) |
| Standoff and bubble | 1.0 m (band 0.8 to 1.2), bubble 0.50 m, 0.20 m/s inside it |
| Trials | 120 = 60 falls + 60 activities; dev 40 (seed 1), test 120 (seed 2); 43 silent falls (she does not answer) |
| Dispatch level | robot 28/43 = 0.65, 4 cameras 20/43 = 0.47, 1 camera 2/43 = 0.05; false dispatch 2/77 = 0.026 |
| Alarm level (heads-up) | robot 41/60 = 0.68, 4 cameras 31/60 = 0.52, 1 camera 4/60 |
| Latency (from floor contact) | robot median 30.4 s to heads-up, 48.8 s to dispatch (max 99.1 s); 4 cameras 3.8 s and 13.6 s |
| Within 60 s | robot 16/43 = 0.37, 4 cameras 19/43 = 0.44 |
| Significance | robot vs 4 cameras: McNemar p 0.11 (alarm), 0.15 (dispatch), not significant; robot slower, Welch p 1.7e-8, d 1.48; robot vs 1 camera p 1.5e-10 and 2.2e-7 |
| By room (alarm) | living: robot 15/20 (8.6 s), 4 cameras 3/20. hallway: 16/20 vs 15/20. bedroom: 10/20 (69 s) vs 13/20 |
| Safety | hit by her above 50 N in 25 trials; contact above 5 N in 24; localisation lost in 20; max tilt 87 deg; 0 bytes off the robot before the first alert |
| Economics | U = one attendant-year. kappa 0.453, NCRI 0.547, payback 5.49 months, net -0.41 U/year, benefit/cost 0.18 |
| Break-evens | replace 9.8% of supervision (2.35 h/day, 0.41 FTE); false-dispatch rate at or below 0.51% for kappa 0.25 |
| Monte Carlo (20,000 draws) | P(net > 0) 0.22 with 0 to 15% supervision replaced, 0.00 on clinical value alone; P(kappa <= 0.25) 0.05 |
| Others (same model) | compact robot kappa 0.20, payback 3.75 months; 4 cameras kappa 0.12, payback 1.36 months |
| Queue | one agent handles 12 alerts/h; one desk serves 95 patients (1 agent), 468 (2), 923 (3) at wait under 60 s |

## 4. Formulas you must be able to write

- Tip: m a h = m g d, so a_tip = g d / h.
- Slip: F = m a <= mu m g, so a_slip = mu g.
- Clinical benefit = f x s x dH x b, where b = (bed-day value in attendant-days) / 365.
- Labour benefit = alpha x 168 x 52 / 2080 = alpha x 4.2.
- Cost = CapEx / life + running cost + false-dispatch burden; false-dispatch burden = 1825 x phi x 0.65 x b.
- kappa = (running cost + false-dispatch burden) / 1 U; NCRI = 1 - kappa; payback (months) = 12 x CapEx / (1 - kappa).
- Pure pursuit: omega = 2 v sin(alpha) / L_d with L_d = 0.20 m; yaw cap 1.2 rad/s, slew 6 rad/s2.
- Latency L = t_alert - t_impact. Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2PR/(P+R).

## 5. Questions to expect, and honest answers

**Technology judge**
- *Why is the robot slower than four cameras?* Cameras see the fall instantly. The robot must notice she is gone, search, wait for 3 s of stillness (5 s if it did not see her fall), drive and ask. In the living room, where it sees her, the median is 8.6 s; hallway and bedroom 50 to 70 s because of the search. We trade speed for coverage.
- *Why did you miss 15 falls?* 10 were never found (the robot stayed in SEARCH; in 6 of those it had lost its position), 4 got close but the detector never confirmed (2 were falls onto the robot), 1 was too slow. 9 of the 15 had an injected camera blackout (30% base rate), which is a pattern, not proof.
- *Is it safe?* No, not yet. 25 trials with above 50 N from her landing on the robot, tilt up to 87 degrees. Her body is a replayed kinematic motion, so the force magnitudes are inflated by the simulator, but the event is real: the robot follows too close to where she lands. Fix: follow farther back and from the side.
- *Why 500 Hz? Why those friction values?* 500 Hz is the 0.002 s timestep for contact stability; friction 0.42 / 0.50 / 0.68 are the guide's values for hardwood, laminate and low-pile carpet. Contact softness is left at the MuJoCo default and untuned.
- *Did you tune on the test set?* No. Thresholds were fitted on dev (seed 1, 40 trials) and frozen: hip height 0.45 m, torso angle 60 deg.
- *Sim-to-real?* Untested. Scripted motions, one apartment, an adult body. This is a baseline to improve.
- *How does the physics link to the business model?* Two measured outputs, dispatch sensitivity and false-dispatch rate, flow from `metrics.json` into the model.

**Business judge**
- *Does it pay back?* Not on clinical value alone: payback 5.5 months, kappa 0.45. It reaches break-even if it replaces about 10% of monitoring time, or if false dispatches fall below 0.5%.
- *Who pays?* Families, home-care agencies, care homes and hospitals share the value; no single payer captures it. That is why the labour-reallocation lever matters.
- *Why not just use four cameras?* They are cheaper (kappa 0.12) and faster where they see, but they saw 0 of 20 falls in the living area, because they sit in the hallways and bedroom. The robot's case is one device that reaches every room, at a cost of speed.
- *Where do the costs come from?* Two inputs are measured. The rest are assumptions A1 to A14: A1, A4, A5, A9 from the research guide (not independently verified); A2 (18.4 to 4.2 days) and A6 (3 attendant-months) from the sheet, with no primary source for A2; A14 (2080 h) from the standards manual; the rest are ours and varied in the Monte Carlo run.
- *What would change the answer?* Sourced values for A2, A3, A6, A11, A12; a pilot to measure replaced hours; false dispatches below 0.5%.

**Industry judge**
- *Who is the user and what is the next step?* An older adult living alone, and the family or agency behind her. Next step: a supervised pilot in a care setting to measure missed falls, false alerts and hours saved, after the safety fix.
- *Privacy?* Inference runs on the robot, frames are discarded, and nothing leaves before an alert (0 bytes measured in the simulation); one snapshot after a confirmed emergency.
- *Is the dispatch real?* No. It is simulated and logged. A real service would need a monitored-alarm partner.
- *Why the 6-minute window?* It is the cardiac-arrest teaching figure (AHA 2020). Our measured dispatches went out within 100 s of floor contact. The long lie (an hour or more) is the harm we target. We do not claim to detect a cardiac arrest.

**Faculty judge (individual)**
- Explain tip vs slip with your own numbers (section 4). Explain how the layout file feeds the apartment and robot XML. Explain kappa, NCRI and payback and where each input comes from. Say what you did, what Kamakshi did (vision, kinematics, detector), and where the AI tools helped and where they were wrong (the paper lists three audit lessons).

## 6. Mismatches to fix or avoid saying (found while reading the four documents)

1. **Unlike levels compared (paper abstract and conclusion).** It sets the robot's 41 of 60 (alarm level, 68%) against four cameras' 47% (dispatch level). Same level: alarm 68% vs 52%; dispatch 65% vs 47%. Say the matched pair.
2. **Thresholds listed in the paper are the guide's, not the frozen ones.** Paper section III-B: |vz| 1.80 m/s, aspect ratio 1.20, hip height 0.20 m. The frozen run used hip height 0.45 m, torso angle 60 deg, aspect ratio 1.0 and peak descent 1.2 m/s (code defaults). Either change the paper or say "guide values, adjusted on dev".
3. **Paper limitation (7) says MediaPipe was not part of the benchmark. That is wrong.** `src/experiments/run_trial.py` runs the real MediaPipe pose landmarker on the rendered camera frames in every trial. Tell Kamakshi; it is the paper's own title claim.
4. **"Within 100 s"**: 27 timed dispatches (max 99.1 s) plus one that cannot be timed. Say "27 of 28 timed, all within 100 s".
5. **Paper title** is not the authorised title. The dossier and any slide-free pitch should use the authorised wording.
6. **Medication reminders and the chat feature** are outside the authorised scope. Do not include them in any claim.

## 7. Running the live simulation

```bash
cd /Users/devanshi/Desktop/mriia/companion_robot && source .venv/bin/activate
mjpython src/sim/run_demo.py --view --scenario watch
```
- `watch` is the shorter run (the emergency fires about 14 s after the fall in an earlier check). `follow` starts in the bedroom and can spend 45 s or more searching, which is too long for a 2-minute slot. Time both once.
- The diagnostics window opens beside the 3D view. If it does not, run:
```bash
python src/sim/diagnostics_window.py --live outputs/demo_run/live_diagnostics.jsonl
```
- Backup if the window fails: `MUJOCO_GL=glfw python src/sim/run_demo.py` writes `outputs/demo_run/demo.gif`.
- Viva ask: "change a parameter and re-run". Edit `src/robot/robot_spec.py` (mass, wheel radius, V_MAX) or floor friction in `src/sim/apartment_layout.py`, then `python src/sim/build_all.py`, then run again. Practise one change before 12:00.
- Reproduce a few trials: `python src/experiments/run_experiments.py demo 3 2 --conditions robot --workers 3 --cfg results/guide_robot_test/frozen_config.json` (untested here; MediaPipe timings vary by a few seconds).
