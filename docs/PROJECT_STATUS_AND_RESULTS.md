# Project status and results (updated 2026-10-26)

Title (authorised, unchanged): How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?

## What is measured (and what is not)
- The only complete 120-trial evaluation (test split, seed 2, thresholds frozen from the dev split, paired robot vs 1 fixed camera vs 4 fixed cameras) was run on an EARLIER COMPACT-ROBOT VARIANT (0.16 m camera, 1.2 kg). Results: `results/small_robot_test/report.md`, `metrics.json`, `economics.json`, `tables/`, `figures/`; frozen thresholds: `results/small_robot_test/frozen_config.json`; the paper (`paper/paper.pdf`) quotes these files only.
- The guide-specification robot (1.10 m mast, 0.44 x 0.34 m chassis, 16.5 kg) is the robot in the code now and passes its mechanical tests (`tests/test_robot.py`): CoM 0.228 m, tip limit 7.76 m/s2 (guide 7.64), braking 2.43-3.30 m/s2 from 0.50 and 0.79 m/s (manual needs 1.5), pitch 0.1 deg. Its dev run (40 trials) was unsatisfactory (contacts, lost localisation); one cause (jamming while spinning in SEARCH) was fixed; a second dev run was started on 2026-10-26 and a 120-trial test on this robot was NOT completed. No guide-robot number may be quoted as a result.
- Small-robot headline numbers (simulation): alarm sensitivity 0.87 (52/60), specificity 0.75; dispatch sensitivity 0.86 (37/43), 0 false dispatches in 77; 1 camera 0.02, 4 cameras 0.48; median latency to heads-up 20 s (robot) vs 3.7 s (4 cameras); paired difference 30.1 s (95% CI 21.3-39.0, t(23)=7.03, d=1.43). The robot buys coverage, not speed.

## Requirements status
See `docs/REQUIREMENTS_CHECK.md` (final title sheet table, robot-vs-guide measurements, bubble-vs-door note).

## Honest limitations
Scripted motions, adult body; 8/120 robot trials ended lost; one cardiac fall landed on the robot; sofa false alarms (5/20) at alarm level; cardiac prodrome cues false-flag 49% (not used for alerting); payback 3.75 months is longer than the brief's "first quarter"; the 0.50 m bubble cannot hold in 0.85 m doors (speed rule instead, needs sir's confirmation); GDS cannot be simulated; no survival-decay constant is used anywhere (the sheet's 7-10 percent per minute is only quoted as context).

## Demo-only extras (outside the authorised scope, in no metric)
Baymax agent, family platform with login and chat, siren, medicine reminder, wide camera.

## Still to do
Dossier (group Word template needed), LinkedIn video (Devanshi), Kamakshi's own commits (>= 4, vision files), reading Tinetti 1993 and Wild 1981 in full, sir's answer on the door/bubble conflict, a guide-robot 120-trial test if time allows.

## Guide-robot dev run (2026-10-26, 40 trials, seed 1, after the SEARCH stall fix) - NOT a result, a status check
Robot: alarm sensitivity 0.60 (12/20), specificity 0.90, dispatch sensitivity 0.47 (7/15), 0 false dispatches; 4 fixed cameras: alarm 0.60, dispatch 0.60 (3 false dispatches); 1 camera 0. Safety: max commanded speed 0.72 m/s, 14 of 40 trials with non-human contact above 5 N (max 145 N), 5 trials with final pose error above 0.5 m, 0 N from her, 0 bytes off-board before the first alert. The guide robot is therefore NOT ready for a 120-trial test: contacts and localisation failures must be fixed first. The submitted 120-trial numbers remain those of the earlier compact robot.

## Guide-robot dev run 3 (2026-10-26 night, after SEARCH tight-clearance fix) - status, NOT a result
Robot alarm sensitivity 0.70 (14/20, was 0.60), specificity 0.90; dispatch sensitivity 0.53 (8/15, was 0.47), 0 false dispatches; 4 fixed cameras alarm 0.50, dispatch 0.53, 0 false dispatches. The fix (no turning on the spot when the map clearance is under 0.43 m: look with the camera only) raised detection but did NOT remove the contacts: 13 of 40 trials still had non-human contact above 5 N (max 187 N, mostly the coffee table during SEARCH with small position error), one trial had 29 N from her, 5 trials ended lost (pose error above 0.5 m, max 3.9 m). Cause of the coffee-table contacts is still unknown (likely the swept footprint near the table corner or leg during SEARCH moves; not isolated). Therefore NO 120-trial test was run on the guide robot and the paper keeps the compact-robot numbers with the deviation stated.

## Guide-robot contacts: root cause found (2026-10-27)
The dock (-1.05, -1.10) was a one-cell pocket: map clearance 0.350 m there against the 0.349 m the planner needs, and 0.2 m or less one step away. Leaving the dock the robot always crossed blocked cells and brushed the south-east leg of the coffee table (about 0.30 m away). Moving the dock to (-1.85, -1.35) (clearance 0.45 m) removed the contact in 10 of the 14 trials that had it (dev trials re-run, robot condition only): 4 still touch (86 to 170 N) and 1 ended lost (pose error 1.97 m). The full dev split and the 120-trial test on the guide robot were started after this change (see the end of this file for the outcome when they finish).

## FINAL: guide-robot 120-trial test (finished 2026-10-27; thresholds fitted on the new dev run, frozen, test seed 2)
Files: results/guide_robot_test/ (report.md, metrics.json, economics.json, tables, figures, frozen_config.json, telemetry_robot_csv.tar.gz). The paper now reports THIS run as the main result and the earlier compact-robot run (results/small_robot_test/) as a comparison.
Alarm level: robot sensitivity 0.68 (41/60), specificity 0.90, F1 0.77; 4 cameras 0.52 / 0.95; 1 camera 0.07. Dispatch level: robot 0.65 (28/43), 2 false dispatches in 77 (specificity 0.97), F1 0.77; 4 cameras 0.47, 0 false; 1 camera 0.05. Latency: robot median 30.4 s to the heads-up and 48.8 s to dispatch; 4 cameras 3.8 s and 13.5 s. McNemar robot vs 4 cameras: alarm p 0.11, dispatch p 0.15 (not significant). Sofa sits: 0/20 alarms (the compact robot had 5/20).
FAILURES: 24 trials with non-human contact above 5 N (peak 4.4 kN); 25 trials with contact from her above 50 N (peak 40 kN, robot tilted up to 87 deg); 20 trials with pose error above 0.5 m (max 4.3 m); 0 bytes off-board before the first alert. Economics with these numbers: net benefit negative (-19.7 bed-days per patient-year), kappa 0.45 (limit 0.25), payback 5.5 months. The robot is NOT safe and does not beat four cameras statistically.
