# Foundational Literature Review and Research Benchmark Dossier

## Project: AI Companion Robot for Remote Elderly Supervision and Fall Emergency Response
## Group: MDRIIA_GROUP_02

---

> **Correction notice (2026-10-28).** Each of the six PDFs was read against this file. The bibliographic data (authors, years, venues, DOIs) are correct. The 'Mathematical Formulations Extracted' were wrong for five of the six papers (the arccos joint angle for Kothari, the mast overturning formula for CLARA, the CSI phase difference for Ding, the 18.4 / 4.2 days and odds ratio 2.45 for Kubitza, the ellipse axis ratio for Chen) and the Wang and Deng thresholds were not in the paper. They have been replaced by what each paper actually states, with PDF page numbers. The original text appears to have been AI-generated: use this as a case for dossier Section 5.1.

## 1. Executive Summary of Foundational Literature

This dossier establishes the comprehensive academic foundation for MDRIIA_GROUP_02. Rigorous engineering research requires grounding problem formulations, mathematical models, and performance metrics in peer-reviewed literature indexed across top-tier international venues.

This dossier provides:
1. Complete, verified citations with active, clickable DOI links validated against the global CrossRef registry.
2. In-depth technical methodologies and control principles extracted from each publication.
3. Mathematical formulations and physical equations adapted for simulation inside MuJoCo.
4. Critical research gaps in prior literature that MDRIIA_GROUP_02 directly resolves.
5. Individual student ownership mapping for literature defense during oral examination vivas.

---

## 2. Comparative Literature Matrix (6 Verified Papers)

| Paper & Citation | Publication Venue & Indexing | Primary Methodology | Key Formulations Extracted | Critical Research Gap Addressed | Student Lead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Wang & Deng (2024)**<br>`10.1177/20552076241233690` | *Digital Health* | Cascaded (dual-stage) random forests on five features from BlazePose's 33 landmarks: contour height, contour width, aspect ratio, centroid height and vertical velocity. UR Fall and part of the Le2i dataset; 89.99% accuracy, 29.7 FPS on a laptop CPU (PDF pp. 1, 6-7). | Width-to-height ratio r = w_contour / h_contour with w, h from the min and max of the 33 landmarks (eqs 1-3); centroid height h_centroid from the hip midpoint to the foot midpoint (eq 4); vertical velocity from the change of h_centroid per frame step (eq 5); classifier = random forests (eq 6). The paper gives NO fixed threshold such as v_z < -1.8 m/s or AR > 1.3: those are our own values, fitted on the dev split. | Evaluated exclusively on fixed, ceiling-mounted RGB cameras; does not address mobile base ego-motion, camera mast jitter, or occlusion by living room furniture. | **Kamakshi Bahuguna (E007)** |
| **Kothari & Chakurkar (2025)**<br>`10.1016/j.mex.2025.103623` | *MethodsX* | YOLO person detection (confidence above 80%) followed by MediaPipe landmarks; body proportions from Euclidean distances between landmarks (upper-body height, leg height), activity ratio (sitting below 0.5, walking above 1.2) and bounding-box aspect ratio below 0.9; an SMS alert through Twilio. 96.06% accuracy, 100% recall (PDF pp. 2-3). | h_upper = d(shoulder,hip) summed over both sides, h_leg = d(hip,knee) summed over both sides, activity ratio = h_upper / h_leg, aspect_ratio from the YOLO box. The paper has NO joint-angle (arccos) formula. | Lacks cyber-physical actuation; unable to physically navigate toward the fallen elder to verify responsiveness or provide emergency audio/visual link. | **Kamakshi Bahuguna (E007)** |
| **Romero-Garces et al. (2022)**<br>`10.3390/designs6060125` | *Designs* | Design and implementation phases of the socially assistive robot CLARA from 2016 to 2022 and its CORTEX cognitive architecture, used in hospital and care settings. The robot height was set at 1.2 m so the user is comfortable in human-robot interaction sessions (PDF p. 4). | None: the paper contains no mast stability or overturning formula. Our tip-over limit a_tip = g b / h is our own derivation, checked in tests/test_robot.py. | Designed primarily for cognitive stimulation and social interaction; lacks fast reactive fall-triage and emergency dispatch within the golden 6-minute window. | **Devanshi Sachin Kambli (B029)** |
| **Ding & Wang (2020)**<br>`10.1109/TCE.2020.3021398` | *IEEE Transactions on Consumer Electronics* | Device-free WiFi sensing: CSI amplitude variation, discrete wavelet transform denoising and an LSTM-based recurrent network over six motions (jumping, walking, bending, falling, standing up, lying), with a web application for alerts (PDF pp. 3-9). | CSI amplitude f(t) of the subcarriers, discrete wavelet transform (approximation and detail coefficients), LSTM gates (forget, input, output). The paper uses amplitude, NOT a CSI phase difference or dynamic time warping. | RF sensing provides zero visual confirmation, high false alarm rates from pet movement, and zero mobility to check vital signs or establish visual dispatch. | **Devanshi Sachin Kambli (B029)** |
| **Kubitza et al. (2022)**<br>`10.1186/s12877-022-03258-2` | *BMC Geriatrics* | Scoping review (Arksey and O'Malley six steps, PRISMA-ScR) of care options for long lies. One in eight older fallers lie on the floor for more than an hour; complications include fluid deficit and electrolyte disturbance, hypothermia, infections, skin damage with pressure ulcers, rhabdomyolysis and acute renal failure; hospitalisation and mortality rise in the first year; a one-year cohort cited in the paper reports that 60% of fallers with a long lie of at least one hour were readmitted and 29% moved to long-term care (PDF pp. 1, 7). | None: the paper has NO hospital-stay figure (18.4 or 4.2 days) and NO mortality odds ratio of 2.45. Those numbers must not be attributed to it. | Analyzes clinical pathology retrospectively; lacks an active robotic engineering intervention capable of compressing discovery latency to under 30 seconds. | **Devanshi Sachin Kambli (B029)** |
| **Chen et al. (2021)**<br>`10.1109/ICET51757.2021.9450950` | *IEEE International Conference on Electronics Technology (ICET)* | NanoDet-Lite (ShuffleNetV2 0.5x backbone, FPN and PAN neck, Generalized Focal Loss) running on a Raspberry Pi 4B for a mobile robot, with a person-following module after detection. mAP 0.912, model size 2.17 MB; 22.03 FPS and mAP 0.902 in the ncnn framework (PDF pp. 1, 3-5). | Quality Focal Loss QFL = -|y - sigma|^beta ((1 - y) log(1 - sigma) + y log sigma) (eq 1, PDF p. 3). The paper has NO ellipse-fitting, axis-ratio or background-subtraction rule. | Evaluated on flat 2D images without multi-body contact dynamics, domestic furniture obstacle avoidance, or simulated recovery confirmation. | **Kamakshi Bahuguna (E007) & Devanshi Sachin Kambli (B029)** |

---

## 3. Exhaustive Analysis of Foundational Papers

### 3.1 Paper 1: Enhancing elderly care: Efficient and reliable real-time fall detection algorithm (Wang & Deng, 2024)
* **Full Title:** Enhancing elderly care: Efficient and reliable real-time fall detection algorithm
* **Authors:** Wang & Deng
* **Journal / Venue:** *Digital Health*, 2024
* **Verified Active DOI:** [10.1177/20552076241233690](https://doi.org/10.1177/20552076241233690)

#### Technical Methodology
Cascaded (dual-stage) random forests on five features from BlazePose's 33 landmarks: contour height, contour width, aspect ratio, centroid height and vertical velocity. UR Fall and part of the Le2i dataset; 89.99% accuracy, 29.7 FPS on a laptop CPU (PDF pp. 1, 6-7).

#### Mathematical Formulations Extracted
* Width-to-height ratio r = w_contour / h_contour with w, h from the min and max of the 33 landmarks (eqs 1-3); centroid height h_centroid from the hip midpoint to the foot midpoint (eq 4); vertical velocity from the change of h_centroid per frame step (eq 5); classifier = random forests (eq 6). The paper gives NO fixed threshold such as v_z < -1.8 m/s or AR > 1.3: those are our own values, fitted on the dev split.

#### Direct Applicability to MDRIIA_GROUP_02 Implementation
This publication establishes the empirical and theoretical benchmark for MDRIIA_GROUP_02. The algorithmic parameters and constraint formulations directly inform the controller design in `src/control/behavior.py` and `src/vision/fall_detector.py` and the validation framework in `outputs/experiments/<split>/analysis` (generated by `src/experiments/analyze.py` from the seeded runs).

---

### 3.2 Paper 2: Towards safer environments: A YOLO and MediaPipe-based human fall detection system (Kothari & Chakurkar, 2025)
* **Full Title:** Towards safer environments: A YOLO and MediaPipe-based human fall detection system
* **Authors:** Kothari & Chakurkar
* **Journal / Venue:** *MethodsX*, 2025
* **Verified Active DOI:** [10.1016/j.mex.2025.103623](https://doi.org/10.1016/j.mex.2025.103623)

#### Technical Methodology
YOLO person detection (confidence above 80%) followed by MediaPipe landmarks; body proportions from Euclidean distances between landmarks (upper-body height, leg height), activity ratio (sitting below 0.5, walking above 1.2) and bounding-box aspect ratio below 0.9; an SMS alert through Twilio. 96.06% accuracy, 100% recall (PDF pp. 2-3).

#### Mathematical Formulations Extracted
* h_upper = d(shoulder,hip) summed over both sides, h_leg = d(hip,knee) summed over both sides, activity ratio = h_upper / h_leg, aspect_ratio from the YOLO box. The paper has NO joint-angle (arccos) formula.

#### Direct Applicability to MDRIIA_GROUP_02 Implementation
This publication establishes the empirical and theoretical benchmark for MDRIIA_GROUP_02. The algorithmic parameters and constraint formulations directly inform the controller design in `src/control/behavior.py` and `src/vision/fall_detector.py` and the validation framework in `outputs/experiments/<split>/analysis` (generated by `src/experiments/analyze.py` from the seeded runs).

---

### 3.3 Paper 3: CLARA: Building a Socially Assistive Robot to Interact with Elderly People (Romero-Garces et al., 2022)
* **Full Title:** CLARA: Building a Socially Assistive Robot to Interact with Elderly People
* **Authors:** Romero-Garces et al.
* **Journal / Venue:** *Designs*, 2022
* **Verified Active DOI:** [10.3390/designs6060125](https://doi.org/10.3390/designs6060125)

#### Technical Methodology
Design and implementation phases of the socially assistive robot CLARA from 2016 to 2022 and its CORTEX cognitive architecture, used in hospital and care settings. The robot height was set at 1.2 m so the user is comfortable in human-robot interaction sessions (PDF p. 4).

#### Mathematical Formulations Extracted
* None: the paper contains no mast stability or overturning formula. Our tip-over limit a_tip = g b / h is our own derivation, checked in tests/test_robot.py.

#### Direct Applicability to MDRIIA_GROUP_02 Implementation
This publication establishes the empirical and theoretical benchmark for MDRIIA_GROUP_02. The algorithmic parameters and constraint formulations directly inform the controller design in `src/control/behavior.py` and `src/vision/fall_detector.py` and the validation framework in `outputs/experiments/<split>/analysis` (generated by `src/experiments/analyze.py` from the seeded runs).

---

### 3.4 Paper 4: A WiFi-Based Smart Home Fall Detection System Using Recurrent Neural Network (Ding & Wang, 2020)
* **Full Title:** A WiFi-Based Smart Home Fall Detection System Using Recurrent Neural Network
* **Authors:** Ding & Wang
* **Journal / Venue:** *IEEE Transactions on Consumer Electronics*, 2020
* **Verified Active DOI:** [10.1109/TCE.2020.3021398](https://doi.org/10.1109/TCE.2020.3021398)

#### Technical Methodology
Device-free WiFi sensing: CSI amplitude variation, discrete wavelet transform denoising and an LSTM-based recurrent network over six motions (jumping, walking, bending, falling, standing up, lying), with a web application for alerts (PDF pp. 3-9).

#### Mathematical Formulations Extracted
* CSI amplitude f(t) of the subcarriers, discrete wavelet transform (approximation and detail coefficients), LSTM gates (forget, input, output). The paper uses amplitude, NOT a CSI phase difference or dynamic time warping.

#### Direct Applicability to MDRIIA_GROUP_02 Implementation
This publication establishes the empirical and theoretical benchmark for MDRIIA_GROUP_02. The algorithmic parameters and constraint formulations directly inform the controller design in `src/control/behavior.py` and `src/vision/fall_detector.py` and the validation framework in `outputs/experiments/<split>/analysis` (generated by `src/experiments/analyze.py` from the seeded runs).

---

### 3.5 Paper 5: Therapy options for those affected by a long lie after a fall: a scoping review (Kubitza et al., 2022)
* **Full Title:** Therapy options for those affected by a long lie after a fall: a scoping review
* **Authors:** Kubitza et al.
* **Journal / Venue:** *BMC Geriatrics*, 2022
* **Verified Active DOI:** [10.1186/s12877-022-03258-2](https://doi.org/10.1186/s12877-022-03258-2)

#### Technical Methodology
Scoping review (Arksey and O'Malley six steps, PRISMA-ScR) of care options for long lies. One in eight older fallers lie on the floor for more than an hour; complications include fluid deficit and electrolyte disturbance, hypothermia, infections, skin damage with pressure ulcers, rhabdomyolysis and acute renal failure; hospitalisation and mortality rise in the first year; a one-year cohort cited in the paper reports that 60% of fallers with a long lie of at least one hour were readmitted and 29% moved to long-term care (PDF pp. 1, 7).

#### Mathematical Formulations Extracted
* None: the paper has NO hospital-stay figure (18.4 or 4.2 days) and NO mortality odds ratio of 2.45. Those numbers must not be attributed to it.

#### Direct Applicability to MDRIIA_GROUP_02 Implementation
This publication establishes the empirical and theoretical benchmark for MDRIIA_GROUP_02. The algorithmic parameters and constraint formulations directly inform the controller design in `src/control/behavior.py` and `src/vision/fall_detector.py` and the validation framework in `outputs/experiments/<split>/analysis` (generated by `src/experiments/analyze.py` from the seeded runs).

---

### 3.6 Paper 6: Vision-Based Elderly Fall Detection Algorithm for Mobile Robot (Chen et al., 2021)
* **Full Title:** Vision-Based Elderly Fall Detection Algorithm for Mobile Robot
* **Authors:** Chen et al.
* **Journal / Venue:** *IEEE International Conference on Electronics Technology (ICET)*, 2021
* **Verified Active DOI:** [10.1109/ICET51757.2021.9450950](https://doi.org/10.1109/ICET51757.2021.9450950)

#### Technical Methodology
NanoDet-Lite (ShuffleNetV2 0.5x backbone, FPN and PAN neck, Generalized Focal Loss) running on a Raspberry Pi 4B for a mobile robot, with a person-following module after detection. mAP 0.912, model size 2.17 MB; 22.03 FPS and mAP 0.902 in the ncnn framework (PDF pp. 1, 3-5).

#### Mathematical Formulations Extracted
* Quality Focal Loss QFL = -|y - sigma|^beta ((1 - y) log(1 - sigma) + y log sigma) (eq 1, PDF p. 3). The paper has NO ellipse-fitting, axis-ratio or background-subtraction rule.

#### Direct Applicability to MDRIIA_GROUP_02 Implementation
This publication establishes the empirical and theoretical benchmark for MDRIIA_GROUP_02. The algorithmic parameters and constraint formulations directly inform the controller design in `src/control/behavior.py` and `src/vision/fall_detector.py` and the validation framework in `outputs/experiments/<split>/analysis` (generated by `src/experiments/analyze.py` from the seeded runs).

---


## 4. Theoretical & Empirical Cross-Paper Synthesis Matrix

| Literature Evaluation Dimension | Prior State of the Art (Papers 1-6) | MDRIIA_GROUP_02 Proposed Framework | Target Performance Benefit |
| :--- | :--- | :--- | :--- |
| **Physics Simulation Fidelity** | Simplified 2D planar models or abstract numerical approximations | High-fidelity 3D multi-body physics in Google DeepMind MuJoCo | Continuous contact friction, restitution, and multi-joint dynamics |
| **Control Robustness** | Open-loop kinematics or unconstrained local optimization | Closed-loop feedback control with explicit physical constraint bounds | Zero collision events, smooth actuator torque profiles |
| **Technoeconomic Alignment** | Engineering control analyzed in complete isolation from operational cost | Dimensionless CSBS operational economics and labor reallocation models | Direct quantifiable payback horizon and workflow optimization |

---

## 5. Methodological Research Gap Formulation

### GAP-1: Static vs Mobile Vision Disconnect in Fall Detection
Prior computer vision models assume static overhead cameras. When placed on a moving domestic companion, camera ego-motion and mast vibrations trigger false alarms during routine navigation.

### GAP-2: The 'Long Lie' Resuscitation Latency Bottleneck
Commercial pendant panic buttons require conscious activation, which is impossible in syncope or traumatic head injury. Per Kubitza et al. (2022, PDF p. 1) about one in eight older people who fall report lying on the floor for more than an hour, and more than half of older people living alone cannot get up or get help alone after a fall. (An earlier line here, '50% of elder cases', was not supported.)

### GAP-3: Absence of Physical Proximity Verification
Remote telecare systems lack mobile base relocation to visually inspect breathing or establish clear bi-directional line-of-sight audio with the fallen senior.


---

## 6. Proposed Architectural Innovation & Value Proposition

Group 02 combines a threshold-based MediaPipe landmark detector (aspect ratio, hip descent, torso angle; no ego-motion compensation: the robot judges her response only while it stands still) with a MuJoCo-simulated companion robot with a 1.15 m camera on a 1.10 m mast, obstacle avoidance and simulated dispatch. Measured in 120 seeded trials (guide robot): median 48.8 s from floor contact to dispatch, every dispatch within 100 s (the earlier compact robot: median 40 s). The '12.4 seconds' in an earlier version of this file was not a measured value.

---

## 7. Literature-Grounded Student Viva Defense Questions

### Student: Kamakshi Bahuguna (`E007`) - Branch: `feat/e007-vision-pose-kinematics`
* **Assigned Literature Domain:** MediaPipe skeletal landmark tracking, bounding-box aspect ratio inversion, vertical centroid velocity thresholding, and confusion matrix validation.
* **Viva Defense Question 1:** Explain how the mathematical formulations extracted from your assigned literature directly constrain your engineering implementation in `src/` or `analytics/`.
* **Viva Defense Question 2:** In your assigned branch commits, how did you validate that your experimental results overcome the specific literature limitation identified in the comparative matrix?

### Student: Devanshi Sachin Kambli (`B029`) - Branch: `feat/b029-mujoco-physics-navigation`
* **Assigned Literature Domain:** Differential mobile base physics, pan-tilt mast observation angles, post-fall approach trajectory, and 'long lie' clinical cost model.
* **Viva Defense Question 1:** Explain how the mathematical formulations extracted from your assigned literature directly constrain your engineering implementation in `src/` or `analytics/`.
* **Viva Defense Question 2:** In your assigned branch commits, how did you validate that your experimental results overcome the specific literature limitation identified in the comparative matrix?


