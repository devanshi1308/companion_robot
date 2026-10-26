# Literature note: the long lie, the 6-minute window, and what this project does about them

Written 2026-10-22. Every claim below was checked against the publisher or PubMed record (Crossref and Europe PMC, abstracts only). The full texts could not be downloaded
here (JAMA and Europe PMC refuse automated downloads; the Tinetti 1993 paper is paywalled). Read the full texts through the NMIMS library before submission.

## 1. What the sources actually say

**Tinetti, Liu, Claus (1993). "Predictors and prognosis of inability to get up after falls among elderly persons." JAMA 269(1):65-69. DOI 10.1001/jama.1993.03500010075035.**
- Cohort of 1103 community-living people aged 72 or older (New Haven), mean follow-up 21 months.
- 313 fallers without serious injury; 148 of them (47%) reported being unable to get up after at least one fall.
- Risk factors for being unable to get up: age 80 or more (RR 1.6), depression (RR 1.5), poor balance and gait (RR 2.0).
- Fallers who could not get up had more lasting decline in daily activities (35% against 26%). They were also more likely to die, be hospitalised and have an activity decline, but those trends were NOT statistically significant.
- Journal: JAMA, not the New England Journal of Medicine.

**Wild, Nayak, Isaacs (1981). "Prognosis of falls in old people at home." Journal of Epidemiology and Community Health 35(3):200-204. DOI 10.1136/jech.35.3.200.**
- 125 people aged 65 or over in Birmingham who fell at home, followed for a year, against 125 matched controls.
- Deaths two months after the fall: 11 fallers against 1 control. One year after: 32 fallers against 8 controls. The main factor linked to the higher mortality was impaired mobility before the fall.
- The abstract does not contain the "lying for more than an hour, about half died within six months" figure. That figure is widely attributed to this paper's full text; it needs checking in the full text before it is quoted.

**The two Tinetti papers that ARE in the New England Journal of Medicine** (probably what the supervisor's sheet meant): Tinetti, Speechley, Ginter (1988), "Risk factors for falls among elderly persons living in the community," NEJM 319:1701-1707, DOI 10.1056/nejm198812293192604; and Tinetti, Baker, McAvay et al. (1994), "A multifactorial intervention to reduce the risk of falling among elderly people living in the community," NEJM 331:821-827, DOI 10.1056/nejm199409293311301. Both are about fall RISK and prevention. Neither is a long-lie mortality study (titles verified; contents not read).

## 2. Statements that must NOT go into the dossier as written
| Statement | Problem | Safer wording |
|---|---|---|
| "Long lie raises 6-month mortality by 50% (Tinetti et al., NEJM)" | The long-lie paper by Tinetti is in JAMA 1993; its death trend was not significant; the 50% figure is not in either abstract | "Being unable to get up after a fall is associated with lasting decline and worse outcomes (Tinetti et al., JAMA 1993); long lies were associated with high mortality in an early cohort (Wild et al., 1981, figure to be confirmed in the full text)" |
| "Mean unassisted floor time 78.5 minutes" | No source found or verified | Do not use a number; say "hours" only if a verified source states it |
| "134.5 minute rural ambulance response in remote talukas" | No source was supplied or found; regional reports were not checked | Quote only with the report's title, year and page |
| "6-minute window is the AHA/ERC standard for irreversible neurological hypoxia" | The window is a survival-decay rule of thumb (survival falls steeply with every minute without CPR or defibrillation); phrasing as "irreversible hypoxia at 6 min" is stronger than the guidelines | Cite the specific AHA or ERC guideline text and its recommendation; use "every minute counts" phrasing |

## 3. What this project does about it (and does not)
- **The long lie** is time spent on the floor unable to get help. The robot attacks it from the other end: it notices the fall, goes to her, asks "Are you okay?", and tells the family and the ambulance if she does not answer.
- **Measured in simulation (120 test trials, the small-robot version; see the status report):** for falls where she does not answer, the robot dispatched in 37 of 43 cases, median 40 s after the fall (90th percentile 82 s). That is inside the 6-minute window and far below an hour. The comparison that matters is not "versus a one-hour lie" (that figure is a literature value, not something we simulate) but "versus a fixed camera that cannot see her": one camera dispatched 1 of 43; four cameras 20 of 43, faster where they could see her.
- **What it does not show:** that dispatch reduces mortality. The link from faster dispatch to better outcomes comes from the literature, not from the simulation. The simulation has scripted motions, one flat, and simulated calls.
- **What is done outside the simulation:** nothing. No patients, no real robot, no real calls.

## 4. To do before submission
1. Read Tinetti 1993 and Wild 1981 in full through the library and write the exact sentence you rely on, with page number.
2. Find the AHA or ERC guideline text that supports the 6-minute statement, or reword it.
3. Find the source for 134.5 minutes (report name, year) or drop it.
4. Remove the 78.5-minute figure from `analytics/healthcare_economics.py` unless a source is found.

## 5. Verified 2026-10-26 against the sheet's two statements

Checked by reading abstracts online (Crossref for DOIs, PubMed Central for the 1981 BMJ abstract):

| Statement in the sheet | What the sources say | Use in the paper |
|---|---|---|
| "Long lie increases 6-month mortality by 50% (Tinetti et al., NEJM)" | NOT in Tinetti. Tinetti, Liu, Claus, JAMA 1993;269:65-70 (doi 10.1001/jama.1993.03500010075035) is about inability to get up. The half-died figure is from Wild, Nayak, Isaacs, "How dangerous are falls in old people at home?", BMJ 1981;282:266-268 (doi 10.1136/bmj.282.6260.266): "of those who lay on the floor for more than one hour, half died within six months of the fall" (20 people, a small cohort, mobility-impaired). The paired JECH 1981 paper (doi 10.1136/jech.35.3.200) reports fallers vs controls (32 vs 8 deaths at one year), not the 50 percent figure | Paper cites Wild BMJ 1981 for the figure and calls it a small cohort; Tinetti JAMA for inability to get up |
| "6-minute window is the AHA/ERC standard" | AHA says each minute without CPR lowers survival by about 7-10 percent (secondary sources; the guideline text itself not read) and recommends defibrillation within 3-5 minutes (OHCA). A 6-minute irreversible-damage threshold is a common teaching figure, not a sharp cut-off. AHA 2020 adult BLS/ALS guideline: Panchal et al., Circulation 2020 (doi 10.1161/CIR.0000000000000916) | Paper cites the guideline and Nguyen 2024 (delay to CPR and survival); says "time-critical", does not claim a hard 6-minute cut-off |
| "134.5-minute rural ambulance response" | No primary source found. Treat as the sheet's value | Stated in the paper only as a brief-supplied assumption (not a finding) |
| "Long lie slashes hospital stay from 18.4 to 4.2 days" | No primary source found. A UK retrospective review of over-80s long lies reports about 8 days for admitted patients; evidence on length of stay is limited and causal comparisons are missing | Used only as the sheet's assumption in the dimensionless economics; flagged in the paper |
| "Prevents rhabdomyolysis and pressure necrosis" | Plausible complications of long lies (the Sheffield Long Lies Study is investigating kidney injury); not quantified | Not claimed as a result |
| "Robot cost under 3 months of an attendant; ROI in the first quarter; GDS" | Cost/ROI is our model (payback 3.75 months in the evaluated run, longer than a quarter); GDS cannot be simulated | Reported honestly; GDS named as future measurement |

Still to do by hand: read the Tinetti 1993 and Wild 1981 full texts through the NMIMS library; confirm the AHA 7-10 percent figure in the guideline text.
