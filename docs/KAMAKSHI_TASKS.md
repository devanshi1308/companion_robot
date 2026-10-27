# Tasks for Kamakshi Bahuguna (E007): vision, kinematic pose estimation and alert pipeline lead

Rules from the course: at least 4 distinct feature commits from your OWN GitHub account, on branch feat/e007-vision-pose-kinematics, conventional commit messages (feat:, fix:, test:, docs:), merged by pull request (no direct push to main). At the viva you are asked to explain every commit and to change parameters and re-run live, so take only tasks you can explain. Each task below is real work that the project needs; do not make empty or cosmetic commits.

Your files: src/vision/ (fall_detector.py, person_observer.py, prodrome.py, pose_probe.py), tests/test_fall_detector.py, tests/test_perception.py, the alert payload in src/control/dispatch.py.

| # | Task (one commit each) | Output | Why the project needs it |
|---|---|---|---|
| 1 DONE | test: edge-case tests for the detector (slow lie-down, sit on low sofa, sudden bend to tie shoelaces, dropped keys, partial landmark loss) | tests/test_fall_detector.py | Sir's named pitfall: abrupt sitting on a low sofa |
| 2 | feat: map-based seat suppression (hip above a mapped sofa or chair seat does not raise a heads-up) and evaluate on a NEW dev seed, never the test seed | detector option plus a short table | 5 of 20 sofa sits raised a heads-up in the 120-trial run |
| 3 | docs: find the real cause of the sofa false alarms (is it occlusion?) with landmark-visibility plots | script plus figure in docs/figures | The cause is only a hypothesis today |
| 4 | feat: threshold sensitivity figure (sensitivity and specificity versus aspect-ratio and torso-angle thresholds, dev split only) | figure for the paper | Shows the detector is not over-tuned |
| 5 DONE | docs: refine or drop the cardiac prodrome cues (they false-flag about half of normal trials) and write the negative result honestly | src/vision/prodrome.py, short evaluation | Do not claim what the data does not support |
| 6 DONE | feat: alert payload schema (JSON fields, units) plus a test that no frame or landmark data leaves the robot before the first alert | docs/ALERT_SCHEMA.md, test | Sir's privacy pitfall: edge inference, no cloud streaming |
| 7 | feat: run MediaPipe on a short real video you record (staged sit, lie on bed, drop keys, controlled lie-down on a mat, with the person's consent) and report landmark stability | script, results table | Supporting real-world evidence for the MediaPipe claim |
| 8 | feat: small learned classifier on pose-landmark windows compared with the threshold rule on held-out seeds | script, comparison table | Optional stretch: the learned detector path |
| 9 | docs: vision pipeline description with a data-flow diagram and a viva question-and-answer sheet | docs/VISION_PIPELINE.md | Individual viva |
| 10 | docs: write the vision and detection section of the paper and check every citation DOI | paper text | Manuscript deliverable |

Suggested order for the time left: 1, 6, 3, 2, 4, 9 (these need no new data). Keep each pull request small (one task), run the tests before pushing (`python tests/test_fall_detector.py`, `python tests/test_perception.py`), and read the commit before merging so you can explain it.


## Status on 2026-10-26 night
- Done (prepared on Devanshi's account with an AI assistant, committed there, NOT under Kamakshi's name): task 1 (4 new edge-case tests in tests/test_fall_detector.py), task 5 (docs/PRODROME_NEGATIVE_RESULT.md) and task 6 (docs/ALERT_SCHEMA.md and tests/test_alert_privacy.py). Kamakshi must read these three before the viva and be able to explain every line; they are in her area.
- Still hers (take at least 4 so that 4 of the commits are her own): 2 (seat suppression, needs a new dev seed), 3 (cause of the sofa false alarms), 4 (threshold sensitivity figure), 7 (real video, needs her and a consenting person), 8 (optional learned classifier), 9 (vision pipeline doc and viva sheet), 10 (vision section of the paper).
- NEW task 11: read the two papers in full through the NMIMS library and write the exact sentence you rely on, with the page number, into docs/literature/LONG_LIE_AND_RESPONSE_TIME.md. Tinetti, Liu, Claus, JAMA 1993;269:65-69 (doi 10.1001/jama.1993.03500010075035) is paywalled and has NOT been downloaded. Wild, Nayak, Isaacs, BMJ 1981;282:266-268 (doi 10.1136/bmj.282.6260.266) is free to read at https://pmc.ncbi.nlm.nih.gov/articles/PMC1504022 (not downloaded either: the repo has only the abstract-level facts). Also confirm the AHA 7 to 10 percent per minute figure in the 2020 guideline text (Panchal et al., doi 10.1161/CIR.0000000000000916).

## What Kamakshi has to push (checklist, 2026-10-27)
Work on her own computer, signed in to HER GitHub account, from a fresh clone: `git clone https://github.com/devanshi1308/companion_robot.git`, then `git checkout -b feat/e007-vision-pose-kinematics`. One small pull request per item, commit messages like `test: ...`, `feat: ...`, `docs: ...`. She must be able to explain each one.
1. [ ] Task 4: threshold sensitivity figure (dev split only) -> `feat: ...`
2. [ ] Task 2: seat suppression for sofa sits, evaluated on a new dev seed -> `feat: ...`
3. [ ] Task 3: cause of the sofa false alarms (landmark visibility plots) -> `docs: ...`
4. [ ] Task 9: vision pipeline document and viva question sheet -> `docs: ...`
5. [ ] Task 10: the vision section of the paper (and a check of every DOI) -> `docs: ...`
6. [ ] Task 11: read Tinetti 1993 and Wild 1981 in full and add the exact sentences with page numbers to docs/literature/LONG_LIE_AND_RESPONSE_TIME.md -> `docs: ...`
7. [ ] Task 7 (needs her and a consenting person): real video through MediaPipe -> `feat: ...`
8. [ ] Read, run and be able to explain the three items already prepared in her area: tests/test_fall_detector.py (4 new tests), docs/ALERT_SCHEMA.md with tests/test_alert_privacy.py, docs/PRODROME_NEGATIVE_RESULT.md. She does NOT push these again (they are already on main under Devanshi's account); she may add improvements in her own commits.
Minimum for the course: at least 4 of items 1-7 as commits from her account, merged to main by pull request.

## Data she needs (not on GitHub)
The folder outputs/ is in .gitignore, so a clone has no experiment data. Devanshi gives her `Kamakshi_dev_data.zip` (the 40 dev trials of the compact-robot run, with frozen_config.json and a README). Unzip it into `outputs/experiments/dev` of her clone. She tunes and plots ONLY on this dev data; the 120-trial test split is not given to her, because it must stay frozen. The newer guide-robot dev run will be shared when it finishes.
