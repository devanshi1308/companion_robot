# Project status and results (updated 2026-10-26)

Title (authorised, unchanged): How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?

## What is measured (and what is not)
- The only complete 120-trial evaluation (test split, seed 2, thresholds frozen from the dev split, paired robot vs 1 fixed camera vs 4 fixed cameras) was run on an EARLIER COMPACT-ROBOT VARIANT (0.16 m camera, 1.2 kg). Results: `results/small_robot_test/report.md`, `metrics.json`, `economics.json`, `tables/`, `figures/`; frozen thresholds: `results/small_robot_test/frozen_config.json`; the paper (`paper/paper.pdf`) quotes these files only.
- The guide-specification robot (1.10 m mast, 0.44 x 0.34 m chassis, 16.5 kg) is the robot in the code now and passes its mechanical tests (`tests/test_robot.py`): CoM 0.228 m, tip limit 7.76 m/s2 (guide 7.64), braking 2.43-3.30 m/s2 from 0.50 and 0.79 m/s (manual needs 1.5), pitch 0.1 deg. Its dev run (40 trials) was unsatisfactory (contacts, lost localisation); one cause (jamming while spinning in SEARCH) was fixed; a second dev run was started on 2026-10-26 and a 120-trial test on this robot was NOT completed. No guide-robot number may be quoted as a result.
- Small-robot headline numbers (simulation): alarm sensitivity 0.87 (52/60), specificity 0.75; dispatch sensitivity 0.86 (37/43), 0 false dispatches in 77; 1 camera 0.02, 4 cameras 0.48; median latency to heads-up 20 s (robot) vs 3.7 s (4 cameras); paired difference 30.1 s (95% CI 21.3-39.0, t(23)=7.03, d=1.43). The robot buys coverage, not speed.

## Requirements status
See `docs/REQUIREMENTS_CHECK.md` (final title sheet table, robot-vs-guide measurements, bubble-vs-door note).

## Honest limitations
Scripted motions, adult body; 8/120 robot trials ended lost; one cardiac fall landed on the robot; sofa false alarms (5/20) at alarm level; cardiac prodrome cues false-flag 49% (not used for alerting); payback 3.75 months is longer than the brief's "first quarter"; the 0.50 m bubble cannot hold in 0.85 m doors (speed rule instead, needs sir's confirmation); GDS cannot be simulated; the sheet's 7-10 percent per minute decay differs from our lambda (about 17 percent per minute).

## Demo-only extras (outside the authorised scope, in no metric)
Momo agent, family platform with login and chat, siren, medicine reminder, wide camera.

## Still to do
Dossier (group Word template needed), LinkedIn video (Devanshi), Kamakshi's own commits (>= 4, vision files), reading Tinetti 1993 and Wild 1981 in full, sir's answer on the door/bubble conflict, a guide-robot 120-trial test if time allows.

## Guide-robot dev run (2026-10-26, 40 trials, seed 1, after the SEARCH stall fix) - NOT a result, a status check
Robot: alarm sensitivity 0.60 (12/20), specificity 0.90, dispatch sensitivity 0.47 (7/15), 0 false dispatches; 4 fixed cameras: alarm 0.60, dispatch 0.60 (3 false dispatches); 1 camera 0. Safety: max commanded speed 0.72 m/s, 14 of 40 trials with non-human contact above 5 N (max 145 N), 5 trials with final pose error above 0.5 m, 0 N from her, 0 bytes off-board before the first alert. The guide robot is therefore NOT ready for a 120-trial test: contacts and localisation failures must be fixed first. The submitted 120-trial numbers remain those of the earlier compact robot.
