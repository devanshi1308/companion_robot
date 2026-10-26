# Cardiac prodrome cues: a negative result (reported, not hidden)

**What was built.** src/vision/prodrome.py watches a short window of pose landmarks for four pre-collapse cues described in clinical text: a hand held to the chest, a hunched torso, a slowed or staggering gait, and sway. The cues are SCRIPTED in the simulated person (the cardiac fall clip has a 9 s prodrome); they are not validated on patients.

**Thresholds** (fitted on the dev split only, never on the test split): chest radius 0.25 m, chest fraction 0.6, hunch 14 degrees (results/small_robot_test/prodrome.json).

**Result on the test split (120 trials, compact robot).**
- Cardiac falls flagged before the collapse: 13 of 15 (87%).
- Non-cardiac trials flagged (false flags): 51 of 105 (49%). They include sofa sits, bed lying, tying shoelaces, dropping keys and ordinary slips and trips: bending over looks like a hunched, hand-to-chest pose.

**Conclusion.** The cues are NOT specific enough to alert on: a 49% false-flag rate would flood the family with warnings. They are therefore not used for any alert decision. In the demo they only change the wording and loudness of the siren after a collapse that has already been confirmed (the siren sounds either way). The paper reports this as a negative result and does not claim early warning of a heart attack.

**What would be needed next** (future work): real recordings of chest-clutching and gait changes (with consent), a model that uses time (does the pose persist for several seconds, is it followed by a collapse), and an evaluation on new seeds with the false-flag rate as the primary metric.
