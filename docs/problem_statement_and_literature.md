# Group 2 — Problem Statement Refinement & Literature Check

**Project:** AI companion robot for elderly living alone — emergency response
**Roster:** E007 Kamakshi Bahuguna · B029 Devanshi Sachin Kambli
**Date:** 2026-09-07

---

## 1. What the feedback asked for

From the review sheet, the current title *"AI integrated companion robot for remote supervision, medication reminders and emergency response"* fails on four points:

| Gap flagged | Fix |
|---|---|
| Three functions listed → too broad for a 3–4 week build | Pick **one** function. Emergency response is the most impactful and the most measurable. |
| Descriptive phrase, not an interrogative | Rewrite as a "How can…?" / "Can…?" question. |
| No stakeholder named | Name the beneficiary: **elderly people living alone in India**. |
| No measurable consequence / current gap | State the current delay and the clinical window it misses, with a citation. |

Required shape: **interrogative + stakeholder + measurable consequence.**

> Caution: The reviewer's *suggested* refinement cites "NSSO (2018) … 87% of 13.8 million elderly single-person households … median 23-minute delay". Those exact numbers could not be located in any NSSO/NSO publication (see §4). Use the grounded version below instead — every figure in it is traceable to a named source.

---

## 2. Refined problem statement

### Primary (use this one)

> **How can an autonomous indoor companion robot shorten the time between an unwitnessed fall and notification of a family member or emergency services for elderly people living alone in India — a group of roughly 8 million (5.7% of the ~138 million people aged 60+, NSO *Elderly in India 2021*) — given that more than half of fallers are still on the floor when help finally arrives, and that out-of-hospital cardiac-arrest survival drops by about 7–10% for every minute that CPR and defibrillation are delayed (American Heart Association)?**

Why it works:
- **Interrogative** — "How can…?"
- **Stakeholder** — elderly people living alone in India, quantified.
- **Measurable consequence** — the "long lie" (>1 h on the floor) and the per-minute survival decay give you a concrete baseline to beat in simulation: *time from fall to alert*.
- **Scoped to one function** — detection → alert. No medication reminders, no remote video supervision.

### Alternative A — framed on the "long lie"

> Can a mobile companion robot that patrols an elderly person's home detect a fall and raise a verified alert within 60 seconds, so that a person living alone does not experience a "long lie" — the >1-hour floor time that around 20% of non-injury fall admissions involve and that independently predicts 6-month mortality (Fleming & Brayne, BMJ 2008)?

### Alternative B — framed on the notification chain, not the ambulance

> For the ~8 million elderly Indians who live alone, the first bottleneck in a medical emergency is not ambulance speed but the absence of anyone to raise the alarm. How can an in-home companion robot close this "detection-to-notification" gap for fall events, and how much of the total pre-hospital delay does that gap represent?

Pick **Primary** for the title. Keep A and B in the report as framing options.

---

## 3. Measurable target and simulation scope

**One scenario to simulate in MuJoCo:** a person model in the living-room scene transitions to a fall (rapid CoM drop + horizontal torso + no recovery within N seconds). The robot, which is navigating/tracking, must:

1. classify the event as a fall,
2. approach and issue a check-in prompt ("Are you okay?"),
3. on no response, fire a **simulated** emergency-contact protocol (log an alert payload with timestamp, location, confidence).

**Metrics to report:**

| Metric | Baseline (from literature) | Target |
|---|---|---|
| Fall → alert latency | "Long lie" ≥ 60 min in ~20% of cases; avg floor time up to ~4 h in care settings | < 60 s in simulation |
| Detection sensitivity / specificity | Wearables ~95% in lab; vision higher precision but degrades with occlusion/lighting | report both; discuss false-alarm cost |
| Missed-fall rate under occlusion | Vision systems degrade under occlusion/poor light | quantify across 2–3 furniture layouts |

Business/feasibility member: cost of the robot vs. a wearable pendant vs. no system, and the adherence problem (elderly users forget/refuse to wear devices — a robot needs no compliance).

---

## 4. Statistics check — what is verifiable and what is not

| Claim in the reviewer's suggested title | Status | What the sources actually say |
|---|---|---|
| "NSSO (2018)" | Caution: misattributed | The relevant release is **NSO/MoSPI, *Elderly in India 2021*** (draws on NSS 75th round, 2017–18, and Census projections). |
| "13.8 million elderly single-person households" | Not found: not found | Not in *Elderly in India 2021*. Best available: **5.7% of the 60+ population live alone** → with ~138 million elderly (2021 projection) that is **~7.9 million people** (not households). |
| "87% … experience a median 23-minute delay before family notification" | Not found: not found | No NSO/NSSO source reports a "notification delay" statistic at all. This number appears fabricated. Drop it. |
| "6-minute clinical intervention window for cardiac arrest" | Verified: defensible, phrase carefully | Brain injury begins within ~4–6 min of arrest; survival falls **~7–10% per minute** without CPR/defibrillation (AHA). Better to cite the per-minute decay than a hard "6-minute window". |
| "Delhi CATS 18-minute mean response" (Group 3) | Caution: verify | Not confirmed in sources checked. Maharashtra district data shows emergency ambulance response averaging **134.5 min** across districts — far worse — so a defensible urban figure needs a direct CATS/108 citation. |

**Numbers you *can* stand behind:**

- ~138 million Indians aged 60+ in 2021; projected ~194 million by 2031 (*Elderly in India 2021*).
- 5.7% of the elderly live alone; ~20% of urban elderly live alone or with only a spouse (NSO 2021).
- Falls affect ~30% of people 65+ each year, ~50% of those 80+ (WHO / standard geriatrics).
- India-specific: **11.6% one-year fall prevalence** among community-dwelling older adults, n≈28,285 (LASI wave 1, 2017–18).
- >53% of older fallers who need an ambulance are still on the floor when it arrives; ~20% of non-injury fall admissions involved >1 h on the floor.
- Half of those who lay >1 h on the floor died within 6 months, independent of fall injury (Fleming & Brayne, BMJ 2008).
- OHCA survival decreases ~7–10% per minute of delay to CPR/defibrillation (multiple AHA statements).
- 108 ambulance target: 20 min urban / 40 min rural; real district averages far exceed this.

---

## 5. Annotated bibliography

### A. The problem — elderly living alone, falls, and the "long lie"

1. **NSO / MoSPI (2021). *Elderly in India 2021.*** Government report. Source for the 60+ population size, projections, and the share living alone. → your stakeholder numbers.
   https://mospi.gov.in/sites/default/files/publication_reports/Elderly%20in%20India%202021.pdf

2. **Sinha et al. (2024). Prevalence of fall and its associated factors among the elderly population in India: evidence from LASI.** Community fall prevalence 11.6%, n≈28,285. → India-specific baseline.
   https://www.researchgate.net/publication/380376022

3. **Muhammad & Srivastava (2022). Cross-sectional associations of physical frailty with fall, multiple falls and fall-injury among older Indian adults: LASI 2018.** *PLOS ONE.* Frailty → 15.4% vs 11.9% fall rate. → risk stratification.
   https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0272669

4. **Fleming J, Brayne C (2008). Inability to get up after falling, subsequent time on floor, and summoning help: prospective cohort study.** *BMJ* 337:a2227. The core "long lie" paper — 6-month mortality after >1 h on floor. → your measurable consequence.
   https://www.bmj.com/content/337/bmj.a2227

5. **Systematic review (2022): Impact of experiencing a long-lie fall on physical and clinical outcomes in older people requiring an ambulance.** *International Emergency Nursing.* Consolidates rhabdomyolysis, pressure injury, hospitalisation, mortality. → consequences section.
   https://www.sciencedirect.com/science/article/abs/pii/S1755599X22000052

### B. Emergency response timing — why minutes matter

6. **Sasson C et al. / AHA scientific statements on OHCA.** Survival ~7–10% decrease per minute without bystander CPR/defibrillation. → the clinical urgency argument.
   https://www.ahajournals.org/doi/10.1161/CIRCOUTCOMES.123.010116

7. **Association Between Delays in Time to Bystander CPR and Survival for Witnessed Cardiac Arrest in the United States (2023).** *Circ Cardiovasc Qual Outcomes.* Quantifies survival loss by delay bucket. → baseline table.
   https://pubmed.ncbi.nlm.nih.gov/38146663/

8. **Examining district-level disparity and determinants of timeliness of emergency medical services in Maharashtra, India (2023).** *BMC.* Real Indian ambulance response times, urban/rural gap. → the "current gap" evidence for India.
   https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10692338/

### C. Fall detection methods — the technical landscape

9. **Real-Time Vision-Based Fall Detection Systems for the Elderly: A Systematic Review (2024).** *Sensors.* Deep-learning vision methods, accuracy, and failure modes (occlusion, lighting, privacy). → justifies robot-mounted camera + why it is hard.
   https://pmc.ncbi.nlm.nih.gov/articles/PMC13517638/

10. **A Decade of Progress in Wearable Sensors for Fall Detection (2015–2024): Network-Based Visualization Review.** *Sensors.* 582 articles; wearable accuracy ~95% in lab, adherence is the weakness. → your comparison baseline (robot needs no compliance).
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11991334/

11. **Reduction of Vision-Based Models for Fall Detection (2024).** *Sensors.* Lightweight models suitable for on-robot / edge inference. → feasibility of running detection on the robot.
    https://pmc.ncbi.nlm.nih.gov/articles/PMC11598268/

12. **AI for fall detection in older adults: comprehensive survey of ML/DL approaches and future directions (2025).** *Expert Systems with Applications.* Taxonomy + open problems. → your "gaps" section.
    https://www.sciencedirect.com/science/article/abs/pii/S1568163725002946

### D. Companion / socially assistive robots with emergency features

13. **Employing Socially Assistive Robots in Elderly Care (2023).** arXiv 2304.14944. Survey — NAO fall alerting, HOBBIT emergency recognition, CompanionAble fall detection + emergency call. → prior art; position your contribution against these.
    https://arxiv.org/pdf/2304.14944

14. **Robotics in Elderly Healthcare: A Review of 20 Recent Research Projects (2023).** arXiv 2302.04478. → related-work table.
    https://arxiv.org/pdf/2302.04478

15. **Abdi J et al. (2018). Scoping review of the use of socially assistive robots in the care of older people.** *BMJ Open.* Acceptability / usability evidence. → adoption argument.
    https://bmjopen.bmj.com/content/8/2/e018815

### E. Simulation

16. **Todorov E, Erez T, Tassa Y (2012). MuJoCo: A physics engine for model-based control.** *IROS.* Cite for the simulator itself.
    https://ieeexplore.ieee.org/document/6386109

---

## 6. How the literature maps to your build

- **§A** gives the problem statement its stakeholder count and its measurable consequence (long lie → mortality).
- **§B** gives the "6-minute / per-minute" urgency line — cite the AHA per-minute figure, not a fabricated NSSO delay.
- **§C** tells you to expect ~95% accuracy in clean conditions and to *test occlusion and lighting* as your novel contribution in MuJoCo.
- **§D** shows fall-alerting robots already exist (NAO, HOBBIT, CompanionAble) — so your framing must be "in an Indian living-alone context, measuring detection-to-alert latency under realistic occlusion", not "first ever companion robot".
- **§E** justifies the tool.

## 7. Immediate next actions (from the review sheet)

1. Submit the **Primary** problem statement from §2 as the revised title.
2. Confirm group membership (only 2 named — state whether anyone else is joining).
3. Add the NSO 2021 stakeholder figure and the AHA per-minute survival figure to the title/abstract.
4. In the proposal, scope the simulation to the single fall-detection → alert scenario in §3 with the metrics table.
