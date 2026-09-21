import os

BASE_MDRIIA = r"D:\MPSTME\AY 26-27 Odd Sem ICA\GitHub_Repos\NMIMS-MPSTME-MDRIIA-2026"
BASE_IVRAR = r"D:\MPSTME\AY 26-27 Odd Sem ICA\GitHub_Repos\NMIMS-MPSTME-IVRAR-2026"

STANDARDS_MANUAL_MDRIIA = """# Academic & Industrial Engineering Standards Manual
## Modern Day Robotics and Its Industrial Applications (MDRIIA - 702CO0E012)
**Department:** Computer Science & Business Systems (CSBS), SVKM's NMIMS MPSTME  
**Governance Oversight:** Institutional Leadership & Academic Directorate  
**Pedagogical Framework:** Aalborg-UNESCO PBL & CDIO Syllabus 2.0  

---

## 1. Executive Summary & Purpose
This manual establishes the formal, binding technical and academic standards governing all Problem-Based Learning (PBL) projects within the MDRIIA cohort. Under the CDIO (Conceive-Design-Implement-Operate) framework and ABET Criterion 3 Student Outcomes, undergraduate engineering deliverables must adhere to recognized international engineering codes and rigorous statistical protocols rather than ad-hoc heuristics.

---

## 2. Robotics & Autonomous Systems Standards

### 2.1 ISO 13482:2014 — Safety Requirements for Personal Care Robots
* **Applicability:** Groups 01 (ICU AMR), 02 (Elderly Companion), 03 (AED Delivery), 07 (Hospital Housekeeping).
* **Mandated Constraints:**
  * **Operational Speed Limit:** Maximum linear velocity within occupied indoor environments shall not exceed $0.80\\text{ m/s}$ in shared pedestrian zones.
  * **Emergency Braking:** Deceleration rate must reach at least $1.5\\text{ m/s}^2$ without causing chassis pitch overturn or payload ejection.
  * **Dynamic Clearance:** Continuous laser/ultrasonic safety bubble of at least $0.50\\text{ m}$ maintained from any dynamic or static obstacle.

### 2.2 ISO 3691-4:2023 — Driverless Industrial Trucks & Autonomous Mobile Robots (AMRs)
* **Applicability:** Groups 01, 03, 06, 07, 09.
* **Mandated Constraints:**
  * **Speed Profiles & Braking Distance:** Braking distance calculation: $s_{brake} = \\frac{v^2}{2 \\mu g} + v \\cdot t_{detect}$, where sensor detection latency $t_{detect} \\le 50\\text{ ms}$.
  * **Personnel Detection Field:** Minimum field of view (FOV) of 180 degrees forward-facing with dual-zone warning (slowdown at $1.5\\text{ m}$, emergency stop at $0.4\\text{ m}$).

### 2.3 ISO 10218-1/2:2011 & ISO/TS 15066:2016 — Collaborative Industrial Robotics
* **Applicability:** Groups 04 (Orbital Manipulator), 07 (Housekeeping Arm), 10 (Surgical Arm).
* **Mandated Constraints:**
  * **Power and Force Limiting (PFL):** End-effector contact force shall not exceed $140\\text{ N}$ during transient contact and $35\\text{ N}$ during quasi-static contact on human soft tissue.
  * **Speed and Separation Monitoring (SSM):** Dynamic safety margin scaled to joint velocity: $S_p = (v_r + v_h) T_r + C$.

### 2.4 ROS 2 REP Standards (REP 103 & REP 105)
* **Applicability:** All 10 Groups.
* **Coordinate Frame Hierarchy:**
  * Coordinate conventions must strictly follow ISO/REP-103: $X$ forward, $Y$ left, $Z$ upward (Right-Handed System).
  * Frame transformations: `map` -> `odom` -> `base_footprint` -> `base_link` -> `sensor_optical_frame`.
* **Standard Units:** Distances in meters ($m$), angles in radians ($rad$), velocities in $m/s$ and $rad/s$, torques in $N \\cdot m$.

---

## 3. Computer Science & Business Systems (CSBS) Technoeconomic Rigor
To satisfy CSBS accreditation mandates, every group must ground their simulation in a dimensionless mathematical business model:
1. **Strict Currency Exclusion:** Absolutely zero raw currency values ($₹$, $Rs.$) are permitted in code, papers, or presentations.
2. **Operational Cost Parity Ratio ($\\kappa$):**
   $$\\kappa = \\frac{\\text{Annualized Maintenance, Energy, and Infrastructure Operational Cost}}{\\text{Annualized Economic Value of Reclaimed Labor Hours}}$$
   Target benchmark: $\\kappa \\le 0.25$ (demonstrating at least 75% net operational savings).
3. **Payback Horizon in Operational Months ($P_{months}$):**
   $$P_{months} = \\left( \\frac{\\text{CapEx Parity Factor}}{1.0 - \\kappa} \\right) \\times 12$$
4. **Full-Time Equivalent (FTE) Capacity Reallocation:**
   $$\\Delta \\text{FTE} = \\frac{\\text{Annual Reclaimed Task Hours}}{2080\\text{ hours/year}}$$

---

## 4. Empirical Hypothesis Testing & Statistical Evidence Standards
* **Sample Size Mandate:** Minimum $N \\ge 50$ randomized Monte Carlo simulation runs across diverse clutter distributions and obstacle velocities.
* **Significance Testing:** Paired or Independent Student's $t$-test / Welch's $t$-test reporting:
  * Degrees of freedom ($df$)
  * Test statistic ($t$)
  * Exact $p$-value (threshold $p < 0.05$)
  * Practical effect size: Cohen's $d = \\frac{\\mu_1 - \\mu_2}{s_{pooled}} > 0.80$ (Large effect)
  * 95% Confidence Intervals: $\\mu \\pm 1.96 \\cdot SE$.

---

## 5. Software Quality Assurance & Git Version Control (IEEE 730-2014)
* **Branching Model:** Strictly feature-branch workflow (`feat/<roll_no>-<task>`). Direct commits to `main` are prohibited.
* **Commit Standards:** Conventional Commits 1.0.0 (`feat:`, `fix:`, `docs:`, `test:`, `perf:`).
* **Individual Attribution:** Every student must have a minimum of 4 distinct feature commits demonstrating their individual contribution.
"""

STANDARDS_MANUAL_IVRAR = """# Academic & Industrial Engineering Standards Manual
## Introduction to Virtual Reality & Augmented Reality (IVRAR - 702TG0C003)
**Course:** Open Elective, B.Tech Semester VII  
**Governance Oversight:** Institutional Leadership & Academic Directorate  
**Pedagogical Framework:** Aalborg-UNESCO Problem-Based Learning (PBL) & CDIO  

---

## 1. Executive Summary & Purpose
This manual establishes the formal, binding technical and academic standards governing all 18 Problem-Based Learning (PBL) projects within the IVRAR cohort. Under international XR engineering standards (IEEE, ISO, W3C, Khronos), virtual and augmented reality applications must be evaluated using validated psychometric instruments and quantitative performance benchmarks.

---

## 2. Spatial Computing & XR Systems Standards

### 2.1 IEEE 2888 Standards Family — Spatial Computing, Sensors & Actuators
* **Applicability:** All 18 IVRAR Groups.
* **IEEE 2888.1:** Standard for Specification of Sensor and Actuator for Virtual and Augmented Reality. Defines standardized latency, field-of-view (FOV), and refresh rate requirements for spatial tracking.
* **IEEE 2888.2:** Standard for Interfacing Cyber and Physical Worlds. Governs spatial anchoring, world-locking coordinates, and event telemetry pipelines.

### 2.2 ISO 9241-210 & ISO 9241-920 — Ergonomics of Human-System Interaction
* **Applicability:** All 18 IVRAR Groups.
* **ISO 9241-210:2019:** Human-centred design for interactive systems. Mandates iterative stakeholder feedback, accessibility, and cognitive load minimization.
* **ISO 9241-920:2016:** Guidance on tactile and haptic interactions in virtual environments. Specifies vibration duration, amplitude modulation, and latency thresholds ($< 20\\text{ ms}$) for haptic confirmation.

### 2.3 W3C WebXR Device API & Khronos OpenXR 1.1
* **Applicability:** Web-based, mobile AR, and standalone VR deployments.
* **OpenXR Specification:** Direct hardware runtime interface guaranteeing cross-platform motion-to-photon latency $\\le 20\\text{ ms}$ at $\\ge 72\\text{ Hz}$ (or $90\\text{ Hz}$ on desktop HMDs) to avoid vestibulo-ocular reflex mismatches.
* **Spatial Reference Spaces:** `viewer`, `local`, `local-floor`, and `bounded-floor`.

---

## 3. Validated Psychometric Evaluation Instruments

Every student project presenting empirical human evaluation must employ at least two of the following **three gold-standard instruments**:

### 3.1 System Usability Scale (SUS) — Brooke (1996) / ISO 9241-11
* **Structure:** 10 standardized 5-point Likert questions alternating between positive and negative phrasing.
* **Scoring Formula:**
  $$\\text{SUS Score} = 2.5 \\times \\left( \\sum_{i=1,3,5,7,9} (Q_i - 1) + \\sum_{j=2,4,6,8,10} (5 - Q_j) \\right)$$
* **Benchmark Grading:**
  * $> 80.3$: Grade A (Excellent usability)
  * $> 68.0$: Grade C (Acceptable industry average)
  * $< 51.0$: Grade F (Unacceptable usability)

### 3.2 NASA Task Load Index (NASA-TLX) — Hart & Staveland (1988)
* **Structure:** 6 subjective subscales scored from 0 to 100: Mental Demand, Physical Demand, Temporal Demand, Performance, Effort, Frustration.
* **Target Objective:** VR training or simulation interventions must demonstrate a statistically significant reduction in Cognitive Workload compared to traditional 2D or physical controls.

### 3.3 Kennedy Simulator Sickness Questionnaire (SSQ) — Kennedy et al. (1993)
* **Structure:** 16-symptom diagnostic checklist yielding 3 sub-scores and Total Severity ($TS$):
  * **Nausea ($N$):** Weighted sum $\\times 9.54$
  * **Oculomotor ($O$):** Weighted sum $\\times 3.74$
  * **Disorientation ($D$):** Weighted sum $\\times 13.92$
  * **Total Score ($TS$):** Weighted sum $\\times 3.74$
* **Acceptance Criteria:** Safe VR applications must maintain $TS \\le 15.0$ to prevent adverse cybersickness effects.

---

## 4. Human-Subject Evaluation Protocol & Sample Sizing
* **Target Sample Size:** $N = 12\\text{ to }25$ evaluated participants across within-subject (repeated measures) or between-subject A/B test designs.
* **Statistical Rigor:** Paired Student's $t$-test or Wilcoxon Signed-Rank test for non-parametric Likert scales, with Cohen's $d$ or rank-biserial correlation effect sizes.
"""

GRADING_RUBRIC = """# Continuous Assessment (ICA) Grading Rubric & Evaluation Policy
**Academic Year:** 2026–2027 Odd Semester  
**Institution:** SVKM's NMIMS MPSTME, Mumbai  
**Governance Oversight:** Institutional Leadership & Academic Directorate  
**Framework:** ABET Criterion 3 Student Outcomes & CDIO Syllabus  

---

## 1. Overall ICA Marks Distribution (100 Marks Total)

| Milestone / Component | Academic Week | Focus & Deliverables | Weightage |
| :--- | :--- | :--- | :--- |
| **Milestone 1 (Sprint 0)** | Weeks 1–2 | Team Onboarding, Branching Hygiene, Roster Verification, Scope Formulation | **10 Marks** |
| **Milestone 2 (Sprint 1)** | Weeks 3–6 | Minimum Viable Model/Scene, Initial Telemetry, Baseline Hypothesis Testing | **20 Marks** |
| **Milestone 3 (Sprint 2)** | Weeks 7–10 | Closed-Loop Integration, Rigorous Empirical Testing ($N \\ge 12/50$), Full Analytics | **20 Marks** |
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
* **Experimental Execution (8 Marks):** Rigorous testing protocol completed ($N \\ge 50$ Monte Carlo physics runs OR $N \\ge 12$ human usability trials).
* **Statistical Analysis (6 Marks):** Formal hypothesis testing ($t$-test, $p < 0.05$, Cohen's $d$, 95% confidence intervals).
* **CSBS Economics / Psychometric Impact (6 Marks):** Dimensionless cost parity model $\\kappa$ / NASA-TLX, SUS, and SSQ psychometric validation.

### Milestone 4: Final Deliverables, Expert Panel Demo & Individual Viva (50 Marks)
* **IEEE/ACM 4-Page Conference Paper (15 Marks):** Formatted in standard 2-column IEEEtran style with 3 required figures, 2 required tables, and 5 genuine literature citations with DOIs.
* **Working Live Demonstration (15 Marks):** Flawless live execution in front of visiting industry and academic experts.
* **Individual Oral Viva Defense (15 Marks):** Direct questioning of EACH student on their declared specialty. Free-riding is strictly penalized.
* **Git Commit Trajectory & Hygiene (5 Marks):** Verification of individual commit history, conventional commit messages, and zero direct main pushes.

---

## 3. Strict Institutional Compliance Safeguards
1. **Zero Currency Rule:** Any submission containing raw monetary units ($₹$, $Rs.$) will receive an immediate 5-mark deduction and must be resubmitted with dimensionless cost parity ratios.
2. **Restricted Names Rule:** Project documentation must refer to academic leadership exclusively as *"Institutional Leadership & Academic Directorate"*.
3. **Plagiarism & Evidence Authenticity:** Fabricated citations or hallucinated DOIs result in an immediate zero for Milestone 4.
"""

WEEK_1_ASSIGNMENT = """# Week 1 / Sprint 0: Student Onboarding & GitHub Diagnostics
## Practical First-Week Task for All Student Groups
**Academic Year:** 2026–2027 Odd Semester  
**Course Coordination:** Dr. Sunny Nanade  
**Governance Oversight:** Institutional Leadership & Academic Directorate  

---

## 🎯 Purpose of This Week's Task
Welcome to the Problem-Based Learning (PBL) cohort! To ensure that every student is comfortable with professional engineering version control, collaborative development, and our course repository, this week is dedicated to **Sprint 0: The Onboarding Diagnostic**.

By completing this exercise by the end of Week 1, your team will secure its first continuous assessment marks and verify that your local development environment is ready.

---

## 📋 Step-by-Step Student Instructions

### Step 1: Clone the Course Monorepo
Open your terminal (PowerShell, Bash, or Command Prompt) and clone your course repository:
```bash
# For IVRAR Students:
git clone https://github.com/sunny-nanade/NMIMS-MPSTME-IVRAR-2026.git
cd NMIMS-MPSTME-IVRAR-2026

# For MDRIIA Students:
git clone https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026.git
cd NMIMS-MPSTME-MDRIIA-2026
```

### Step 2: Create Your Assigned Git Feature Branch
Every student has been assigned an official feature branch in your group's `RESEARCH_AND_IMPLEMENTATION_GUIDE.md`.  
Switch to your feature branch immediately:
```bash
# Example for student E006:
git checkout -b feat/e006-amr-chassis
```

### Step 3: Locate Your Group Folder
Navigate directly to your designated group folder (e.g., `Group_01_...`).  
**STRICT RULE:** You are only permitted to edit files inside your own group folder. Never touch root files or another group's folder!

### Step 4: Update `docs/TEAM_ROSTER.json`
Open `docs/TEAM_ROSTER.json` inside your group folder. Find your student record and update:
1. `"github_handle"`: Replace with your actual GitHub username.
2. `"institutional_email"`: Ensure your `@nmims.edu.in` or official student email is present.
3. Save the file.

### Step 5: Test Your Local Starter Toolchain
Run the verification script provided in your group folder to ensure your computer has the necessary runtime:
```bash
# For MDRIIA:
python src/test_env.py

# For IVRAR:
python telemetry/test_evaluation_tools.py
```
Verify that the output displays all green checkmarks.

### Step 6: Commit and Push Your Work
Commit your changes using the Conventional Commits standard:
```bash
git add docs/TEAM_ROSTER.json
git commit -m "docs(roster): onboard <Roll_No> <Student_Name> to Group XX"
git push origin feat/<your-branch-name>
```

### Step 7: Open Your First Pull Request (PR)
1. Go to the GitHub repository page.
2. Click **Pull requests** -> **New pull request**.
3. Select your branch to merge into `main`.
4. Fill out the provided PR Checklist template.
5. Title your PR: `Sprint 0 Onboarding - <Roll_No> <Name> (Group XX)`.
6. Submit the PR for faculty review.

---

## 🏆 Assessment & Grading Criteria (10 Marks Total)
* **Timely Submission (by Sunday 11:59 PM):** 3 Marks
* **Correct Branch Naming & Commit Message:** 2 Marks
* **Valid JSON Formatting in `TEAM_ROSTER.json`:** 3 Marks
* **Successful Test Run Output Verified:** 2 Marks
"""

PR_TEMPLATE = """## 📌 PBL Cohort Pull Request (PR)

### 1. Author Identification
* **Group Folder:** `Group_XX_...`
* **Student Name:** 
* **Roll Number:** 
* **SAP ID:** 
* **Declared Engineering Role:** 

---

### 2. Nature of Changes
- [ ] `docs`: Roster update, literature citation, or documentation
- [ ] `feat`: New MuJoCo physics model, Python controller, or XR scene component
- [ ] `test`: Telemetry logging script, unit test, or Monte Carlo run
- [ ] `analytics`: Dimensionless economic model or psychometric assessment calculation

---

### 3. Institutional Quality & Compliance Checklist
Please verify the following before submitting:
- [ ] **Folder Isolation:** All modified files are strictly inside my assigned group folder.
- [ ] **No Currency Mentioned:** Zero raw currency symbols (`₹`, `Rs.`) exist in my code, documentation, or commit messages. Dimensionless ratios and labor hours have been used.
- [ ] **Restricted Names Compliance:** Academic leadership is referred to as *"Institutional Leadership & Academic Directorate"*.
- [ ] **Code Runs Cleanly:** I have executed my script locally and verified that it finishes without unhandled exceptions.
- [ ] **Conventional Commit:** My commit message follows `feat:`, `fix:`, `docs:`, or `test:` syntax.

---

### 4. Verification Evidence
*Provide a brief explanation or paste 3-5 lines of terminal output demonstrating successful execution:*
```
[Paste terminal test output here]
```
"""

ISSUE_TEMPLATE = """---
name: PBL Sprint Task
about: Track an individual engineering task within your group's sprint
title: "[TASK] <Roll_No>: <Brief Description>"
labels: sprint-task
assignees: ''

---

### Task Description
*Provide a clear, 2-3 sentence description of the engineering module you are building this sprint.*

### Expected Deliverables
- [ ] Code / Model deliverable: `src/...` or `models/...` or `telemetry/...`
- [ ] Automated execution test script
- [ ] CSV telemetry or benchmark dataset

### Target Academic Milestone
- [ ] Milestone 1 (Sprint 0 - Onboarding)
- [ ] Milestone 2 (Sprint 1 - Minimum Viable Build)
- [ ] Milestone 3 (Sprint 2 - Closed Loop & Statistical Validation)
- [ ] Milestone 4 (Final Presentation & IEEE Paper)
"""

CI_WORKFLOW = """name: PBL Cohort Automated Compliance & Build Audit

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  audit-compliance-and-syntax:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install Linting & Verification Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8

      - name: Validate All JSON Team Rosters
        run: |
          python -c "
          import os, json, glob
          rosters = glob.glob('**/docs/TEAM_ROSTER.json', recursive=True)
          print(f'Found {len(rosters)} team rosters.')
          for r in rosters:
              with open(r, 'r', encoding='utf-8') as f:
                  data = json.load(f)
                  assert 'group_number' in data, f'Missing group_number in {r}'
                  assert 'students' in data, f'Missing students in {r}'
          print('All team rosters are valid JSON!')
          "

      - name: Verify Institutional Policy Compliance (No Forbidden Names or Raw Currency)
        run: |
          python -c "
          import os, glob, re, sys
          violations = []
          for root, dirs, files in os.walk('.'):
              if '.git' in root:
                  continue
              for file in files:
                  if file.endswith(('.md', '.py', '.json', '.txt', '.xml', '.html')):
                      p = os.path.join(root, file)
                      with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                          txt = f.read()
                          # Word boundary search for forbidden currencies
                          if re.search(r'\\brs\\b|\\brs\\.|[₹]|\\brupees\\b|\\binr\\b', txt, re.I):
                              violations.append(f'Currency violation in {p}')
                          # Check restricted names
                          if 'Archana Bhise' in txt:
                              violations.append(f'Restricted name violation in {p}')
          if violations:
              print('COMPLIANCE AUDIT FAILED:')
              for v in violations:
                  print(' - ' + v)
              sys.exit(1)
          else:
              print('COMPLIANCE AUDIT PASSED: 100% compliant with Institutional Governance.')
          "

      - name: Python Syntax Audit
        run: |
          # Stop the build if there are Python syntax errors
          python -m compileall .
"""

def write_root_files(repo_path, is_ivrar=False):
    # Standards Manual
    manual_content = STANDARDS_MANUAL_IVRAR if is_ivrar else STANDARDS_MANUAL_MDRIIA
    with open(os.path.join(repo_path, "ACADEMIC_AND_INDUSTRY_STANDARDS_MANUAL.md"), "w", encoding="utf-8") as f:
        f.write(manual_content)
        
    # Grading Rubric
    with open(os.path.join(repo_path, "GRADING_RUBRIC_AND_EVALUATION_POLICY.md"), "w", encoding="utf-8") as f:
        f.write(GRADING_RUBRIC)
        
    # Week 1 Assignment
    with open(os.path.join(repo_path, "WEEK_1_STUDENT_ONBOARDING_ASSIGNMENT.md"), "w", encoding="utf-8") as f:
        f.write(WEEK_1_ASSIGNMENT)
        
    # .github directory
    gh_dir = os.path.join(repo_path, ".github")
    os.makedirs(gh_dir, exist_ok=True)
    
    # PR Template
    with open(os.path.join(gh_dir, "pull_request_template.md"), "w", encoding="utf-8") as f:
        f.write(PR_TEMPLATE)
        
    # Issue template directory
    issue_dir = os.path.join(gh_dir, "ISSUE_TEMPLATE")
    os.makedirs(issue_dir, exist_ok=True)
    with open(os.path.join(issue_dir, "sprint_task.md"), "w", encoding="utf-8") as f:
        f.write(ISSUE_TEMPLATE)
        
    # Workflows directory
    wf_dir = os.path.join(gh_dir, "workflows")
    os.makedirs(wf_dir, exist_ok=True)
    with open(os.path.join(wf_dir, "cohort_audit.yml"), "w", encoding="utf-8") as f:
        f.write(CI_WORKFLOW)
        
    print(f"Deployed root governance files to {repo_path}")

if __name__ == "__main__":
    write_root_files(BASE_MDRIIA, is_ivrar=False)
    write_root_files(BASE_IVRAR, is_ivrar=True)
    print("All root governance, standards, rubrics, and CI files generated successfully.")
