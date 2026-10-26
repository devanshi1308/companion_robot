# Tasks for Kamakshi Bahuguna (E007): vision, kinematic pose estimation and alert pipeline lead

Rules from the course: at least 4 distinct feature commits from your OWN GitHub account, on branch feat/e007-vision-pose-kinematics, conventional commit messages (feat:, fix:, test:, docs:), merged by pull request (no direct push to main). At the viva you are asked to explain every commit and to change parameters and re-run live, so take only tasks you can explain. Each task below is real work that the project needs; do not make empty or cosmetic commits.

Your files: src/vision/ (fall_detector.py, person_observer.py, prodrome.py, pose_probe.py), tests/test_fall_detector.py, tests/test_perception.py, the alert payload in src/control/dispatch.py.

| # | Task (one commit each) | Output | Why the project needs it |
|---|---|---|---|
| 1 | test: edge-case tests for the detector (slow lie-down, sit on low sofa, sudden bend to tie shoelaces, dropped keys, partial landmark loss) | tests/test_fall_detector.py | Sir's named pitfall: abrupt sitting on a low sofa |
| 2 | feat: map-based seat suppression (hip above a mapped sofa or chair seat does not raise a heads-up) and evaluate on a NEW dev seed, never the test seed | detector option plus a short table | 5 of 20 sofa sits raised a heads-up in the 120-trial run |
| 3 | docs: find the real cause of the sofa false alarms (is it occlusion?) with landmark-visibility plots | script plus figure in docs/figures | The cause is only a hypothesis today |
| 4 | feat: threshold sensitivity figure (sensitivity and specificity versus aspect-ratio and torso-angle thresholds, dev split only) | figure for the paper | Shows the detector is not over-tuned |
| 5 | feat: refine or drop the cardiac prodrome cues (they false-flag about half of normal trials) and write the negative result honestly | src/vision/prodrome.py, short evaluation | Do not claim what the data does not support |
| 6 | feat: alert payload schema (JSON fields, units) plus a test that no frame or landmark data leaves the robot before the first alert | docs/ALERT_SCHEMA.md, test | Sir's privacy pitfall: edge inference, no cloud streaming |
| 7 | feat: run MediaPipe on a short real video you record (staged sit, lie on bed, drop keys, controlled lie-down on a mat, with the person's consent) and report landmark stability | script, results table | Supporting real-world evidence for the MediaPipe claim |
| 8 | feat: small learned classifier on pose-landmark windows compared with the threshold rule on held-out seeds | script, comparison table | Optional stretch: the learned detector path |
| 9 | docs: vision pipeline description with a data-flow diagram and a viva question-and-answer sheet | docs/VISION_PIPELINE.md | Individual viva |
| 10 | docs: write the vision and detection section of the paper and check every citation DOI | paper text | Manuscript deliverable |

Suggested order for the time left: 1, 6, 3, 2, 4, 9 (these need no new data). Keep each pull request small (one task), run the tests before pushing (`python tests/test_fall_detector.py`, `python tests/test_perception.py`), and read the commit before merging so you can explain it.
