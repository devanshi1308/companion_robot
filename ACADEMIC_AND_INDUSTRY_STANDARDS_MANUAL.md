# Academic & Industrial Engineering Standards Manual
## Modern Day Robotics and Its Industrial Applications (MDRIIA - 702CO0E012)
**Course:** B.Tech CSBS Semester VI (Elective - II)  
**Academic Year:** 2026–2027 | Semester VI (B.Tech CSBS)  
**Pedagogical Framework:** Aalborg-UNESCO PBL & CDIO Syllabus 2.0  

---

## 1. Executive Summary & Purpose
This manual establishes the formal, binding technical and academic standards governing all Problem-Based Learning (PBL) projects within the MDRIIA cohort. Under the CDIO (Conceive-Design-Implement-Operate) framework and ABET Criterion 3 Student Outcomes, undergraduate engineering deliverables must adhere to recognized international engineering codes and rigorous statistical protocols rather than ad-hoc heuristics.

---

## 2. Robotics & Autonomous Systems Standards

### 2.1 ISO 13482:2014 — Safety Requirements for Personal Care Robots
* **Applicability:** Groups 01 (ICU AMR), 02 (Elderly Companion), 03 (AED Delivery), 07 (Hospital Housekeeping).
* **Mandated Constraints:**
  * **Operational Speed Limit:** Maximum linear velocity within occupied indoor environments shall not exceed $0.80\text{ m/s}$ in shared pedestrian zones.
  * **Emergency Braking:** Deceleration rate must reach at least $1.5\text{ m/s}^2$ without causing chassis pitch overturn or payload ejection.
  * **Dynamic Clearance:** Continuous laser/ultrasonic safety bubble of at least $0.50\text{ m}$ maintained from any dynamic or static obstacle.

### 2.2 ISO 3691-4:2023 — Driverless Industrial Trucks & Autonomous Mobile Robots (AMRs)
* **Applicability:** Groups 01, 03, 06, 07, 09.
* **Mandated Constraints:**
  * **Speed Profiles & Braking Distance:** Braking distance calculation: $s_{brake} = \frac{v^2}{2 \mu g} + v \cdot t_{detect}$, where sensor detection latency $t_{detect} \le 50\text{ ms}$.
  * **Personnel Detection Field:** Minimum field of view (FOV) of 180 degrees forward-facing with dual-zone warning (slowdown at $1.5\text{ m}$, emergency stop at $0.4\text{ m}$).

### 2.3 ISO 10218-1/2:2011 & ISO/TS 15066:2016 — Collaborative Industrial Robotics
* **Applicability:** Groups 04 (Orbital Manipulator), 07 (Housekeeping Arm), 10 (Surgical Arm).
* **Mandated Constraints:**
  * **Power and Force Limiting (PFL):** End-effector contact force shall not exceed $140\text{ N}$ during transient contact and $35\text{ N}$ during quasi-static contact on human soft tissue.
  * **Speed and Separation Monitoring (SSM):** Dynamic safety margin scaled to joint velocity: $S_p = (v_r + v_h) T_r + C$.

### 2.4 ROS 2 REP Standards (REP 103 & REP 105)
* **Applicability:** All 10 Groups.
* **Coordinate Frame Hierarchy:**
  * Coordinate conventions must strictly follow ISO/REP-103: $X$ forward, $Y$ left, $Z$ upward (Right-Handed System).
  * Frame transformations: `map` -> `odom` -> `base_footprint` -> `base_link` -> `sensor_optical_frame`.
* **Standard Units:** Distances in meters ($m$), angles in radians ($rad$), velocities in $m/s$ and $rad/s$, torques in $N \cdot m$.

---

## 3. Computer Science & Business Systems (CSBS) Technoeconomic Rigor
To satisfy CSBS accreditation mandates, every group must ground their simulation in a dimensionless mathematical business model:
1. **Strict Currency Exclusion:** Absolutely zero raw currency denominations or fiat symbols are permitted in code, papers, or presentations. All economic analysis must be strictly dimensionless.
2. **Operational Cost Parity Ratio ($\kappa$):**
   $$\kappa = \frac{\text{Annualized Maintenance, Energy, and Infrastructure Operational Cost}}{\text{Annualized Economic Value of Reclaimed Labor Hours}}$$
   Target benchmark: $\kappa \le 0.25$ (demonstrating at least 75% net operational savings).
3. **Payback Horizon in Operational Months ($P_{months}$):**
   $$P_{months} = \left( \frac{\text{CapEx Parity Factor}}{1.0 - \kappa} \right) \times 12$$
4. **Full-Time Equivalent (FTE) Capacity Reallocation:**
   $$\Delta \text{FTE} = \frac{\text{Annual Reclaimed Task Hours}}{2080\text{ hours/year}}$$

---

## 4. Empirical Hypothesis Testing & Statistical Evidence Standards
* **Sample Size Mandate:** Minimum $N \ge 50$ randomized Monte Carlo simulation runs across diverse clutter distributions and obstacle velocities.
* **Significance Testing:** Paired or Independent Student's $t$-test / Welch's $t$-test reporting:
  * Degrees of freedom ($df$)
  * Test statistic ($t$)
  * Exact $p$-value (threshold $p < 0.05$)
  * Practical effect size: Cohen's $d = \frac{\mu_1 - \mu_2}{s_{pooled}} > 0.80$ (Large effect)
  * 95% Confidence Intervals: $\mu \pm 1.96 \cdot SE$.

---

## 5. Software Quality Assurance & Git Version Control (IEEE 730-2014)
* **Branching Model:** Strictly feature-branch workflow (`feat/<roll_no>-<task>`). Direct commits to `main` are prohibited.
* **Commit Standards:** Conventional Commits 1.0.0 (`feat:`, `fix:`, `docs:`, `test:`, `perf:`).
* **Individual Attribution:** Every student must have a minimum of 4 distinct feature commits demonstrating their individual contribution.
