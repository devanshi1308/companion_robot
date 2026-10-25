# Continuous Assessment (ICA) Grading Rubric & Evaluation Policy
**Course:** Modern Day Robotics and Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 | Semester VI (B.Tech CSBS)  
**Institution:** SVKM's NMIMS MPSTME, Mumbai  
**Framework:** ABET Criterion 3 Student Outcomes & CDIO Syllabus  

---

## 1. Overall ICA Marks Distribution (100 Marks Total)

| Milestone / Component | Academic Week | Focus & Deliverables | Weightage |
| :--- | :--- | :--- | :--- |
| **Milestone 1 (Sprint 0)** | Weeks 1–2 | Team Onboarding, Branching Hygiene, Roster Verification, Scope Formulation | **10 Marks** |
| **Milestone 2 (Sprint 1)** | Weeks 3–6 | Minimum Viable Model/Scene, Initial Telemetry, Baseline Hypothesis Testing | **20 Marks** |
| **Milestone 3 (Sprint 2)** | Weeks 7–10 | Closed-Loop Integration, Rigorous Empirical Testing ($N \ge 12/50$), Full Analytics | **20 Marks** |
| **Milestone 4 (Final Viva)** | Weeks 11–12 | 4-Page IEEE Paper Draft, Live Demo to Experts, Individual Oral Viva Defense | **50 Marks** |
| **Total Continuous Assessment** | | **Comprehensive Course Evaluation** | **100 Marks** |

---

## 2. Detailed Milestone Evaluation Criteria

### Milestone 1: Engineering Onboarding & Problem Framing (10 Marks)
* **Git Version Control Setup (3 Marks):** Every group member cloned the monorepo, created their assigned feature branch, and opened a compliant PR.
* **Roster & Toolchain Verification (3 Marks):** `TEAM_ROSTER.json` completed with verified SAP IDs, roles, GitHub handles, and dependencies tested.
* **Aalborg Interrogative Formulation (4 Marks):** Clear problem interrogative, independent/dependent variables identified, null and alternative hypotheses formulated.

### Milestone 2: Minimum Viable Engineering Build (20 Marks)
* **Physical / Spatial Architecture (8 Marks):** Valid MuJoCo MJCF model with proper joint friction/damping OR WebXR/Unity spatial environment with scale calibration.
* **Core Kinematic / Interaction Logic (7 Marks):** Functional control loop or interaction mechanics executing without runtime errors.
* **Initial Telemetry Pipeline (5 Marks):** CSV logging script operational, tracking at least 5 spatial/temporal state variables.

### Milestone 3: Quantitative Experimentation & System Integration (20 Marks)
* **Experimental Execution (8 Marks):** Rigorous testing protocol completed ($N \ge 50$ Monte Carlo physics runs OR $N \ge 12$ human usability trials).
* **Statistical Analysis (6 Marks):** Formal hypothesis testing ($t$-test, $p < 0.05$, Cohen's $d$, 95% confidence intervals).
* **CSBS Economics / Psychometric Impact (6 Marks):** Dimensionless cost parity model $\kappa$ / NASA-TLX, SUS, and SSQ psychometric validation.

### Milestone 4: Final Deliverables, Expert Panel Demo & Individual Viva (50 Marks)
* **IEEE/ACM 4-Page Conference Paper (15 Marks):** Formatted in standard 2-column IEEEtran style with 3 required figures, 2 required tables, and 5 genuine literature citations with DOIs.
* **Working Live Demonstration (15 Marks):** Flawless live execution in front of visiting industry and academic experts.
* **Individual Oral Viva Defense (15 Marks):** Direct questioning of EACH student on their declared specialty. Free-riding is strictly penalized.
* **Git Commit Trajectory & Hygiene (5 Marks):** Verification of individual commit history, conventional commit messages, and zero direct main pushes.

---

## 3. Strict Institutional Compliance Safeguards
1. **Zero Currency Rule:** Any submission containing raw monetary units or fiat currency denominations will receive an immediate 5-mark deduction and must be resubmitted with dimensionless cost parity ratios.
2. **Student Recognition & Attribution Rule:** All student engineering deliverables must be explicitly mapped to verified Git commit trajectories in `TEAM_ROSTER.json` and defended individually during the oral viva.
3. **Plagiarism & Evidence Authenticity:** Fabricated citations or hallucinated DOIs result in an immediate zero for Milestone 4.
