# Questions for the supervisor (Group 02): please answer before the viva

## 1. The 0.50 m clearance bubble and the 0.85 m door
- The standards manual asks for a 0.50 m clearance bubble around the robot. The research guide's apartment has doors 0.85 m and 0.90 m wide, and the guide's robot is 0.42 m wide over the wheels (0.44 x 0.34 m chassis, track 0.38 m).
- A bubble of 0.50 m means 0.25 m free on each side of the robot, so a door of at least 1.0 m. In a 0.85 m door the robot has only 0.215 m on each side, so the bubble cannot be kept.
- What we did: the robot keeps a hard planning margin of 0.045 m outside its 0.304 m footprint and slows to 0.20 m/s whenever it is closer than 0.50 m to a mapped obstacle (doorways, furniture). Braking from 0.80 m/s is 2.43 m/s2 or better (manual needs 1.5).
- Question: is it acceptable to treat the 0.50 m bubble as a speed-reduction zone (not a no-entry zone), or should we widen the doors to at least 1.0 m in the model? If we widen the doors, the flat layout and all results must be re-run, so please say which you prefer.

## 2. Figures in the feedback sheet that we could not trace to a source
We are not allowed to cite anything we cannot verify, so we need the source for each of these (a paper, a report, a page) or permission to label them as assumptions:
1. "Long lie increases 6-month mortality by 50% according to Tinetti et al., NEJM". Tinetti, Liu and Claus (1993) is in JAMA (vol. 269, pp. 65-69) and is about the inability to get up after a fall. The "half died within six months" result we found is in Wild, Nayak and Isaacs, BMJ 1981 (vol. 282, pp. 266-268): of those who lay on the floor for more than one hour, half died within six months (20 people). Which paper did you mean, and may we cite Wild 1981 for the figure and call it a small cohort?
2. "Average ambulance response of 134.5 minutes across Maharashtra districts (rural talukas)". We found no primary source. Do you have the report? If not, we will state it only as the brief's assumption.
3. "Long lie slashes post-fall hospital stay from 18.4 to 4.2 days". We found no primary source (a UK review of long lies in over-80s reports about 8 days for admitted patients). Do you have the source, or may we call it an assumption in the economics model?
4. "6-minute window is the AHA/ERC standard". The AHA guideline says each minute without CPR lowers survival (commonly quoted as 7-10% per minute) and recommends defibrillation within 3-5 minutes; 6 minutes is a commonly taught irreversible-damage figure and not a sharp cut-off in the guideline. Is it fine for the paper to say "time-critical, about 6 minutes" with the AHA 2020 guideline cited?

## 3. Return on investment within the first quarter
The sheet says the robot costs less than 3 months of an attendant AND pays back within the first calendar quarter. With the standards-manual formula, payback = capital cost in months / (1 - kappa), and kappa (operating cost fraction) must be at most 0.25, so payback is always longer than the capital cost: a cost of exactly 3 months gives 3.75 months at kappa 0.20. Both claims agree only if the capital cost is at most 2.4 months of attendant cost (at kappa 0.20). Question: may we report payback as a range (3.0 months at a cost of 2.4 attendant-months, 3.75 months at the 3-month bound) and say which cost we assume?

## 4. Scope and robot
- Medication reminders, a family chat platform, a voice and first-aid guidance were built as demo extras outside the refined scope (rapid navigation, aspect-ratio detection, automated dispatch). They are in no metric. May they be shown at the Expo as demos?
- The 120-trial test in the paper was run on an earlier compact robot (0.16 m camera). The guide-specification robot is the model in the repository now and its 40-trial development run was not yet good enough for a 120-trial test. Is it acceptable to submit the paper with the compact-robot results and a clearly stated deviation, or must the guide robot be re-evaluated?
