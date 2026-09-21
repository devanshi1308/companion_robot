# Week 1 / Sprint 0: Student Onboarding & GitHub Diagnostics
## Practical First-Week Task for All Student Groups
**Course:** Modern Day Robotics and Its Industrial Applications (MDRIIA - 702CO0E012)  
**Academic Year:** 2026–2027 | Semester VI (B.Tech CSBS)  

---

## Purpose of This Week's Task
Welcome to the Problem-Based Learning (PBL) cohort! To ensure that every student is comfortable with professional engineering version control, collaborative development, and our course repository, this week is dedicated to **Sprint 0: The Onboarding Diagnostic**.

By completing this exercise by the end of Week 1, your team will secure its first continuous assessment marks and verify that your local development environment is ready.

---

## Step-by-Step Student Instructions

### Step 1: Clone the Course Monorepo
Open your terminal (PowerShell, Bash, or Command Prompt) and clone your course repository:
```bash
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
python src/test_env.py
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

## Assessment & Grading Criteria (10 Marks Total)
* **Timely Submission (by Sunday 11:59 PM):** 3 Marks
* **Correct Branch Naming & Commit Message:** 2 Marks
* **Valid JSON Formatting in `TEAM_ROSTER.json`:** 3 Marks
* **Successful Test Run Output Verified:** 2 Marks

---

## Project Demonstration & LinkedIn Video Showcase Protocol

As part of your research dissemination and Continuous Assessment (ICA), each student engineering team will record and publish a professional video walkthrough of their project:

### 1. Video Production Specifications
* **Duration:** 60 to 90 seconds (concise, high-impact demonstration).
* **Core Elements to Include:**
  1. **Team Introduction (10s):** Student researchers, roles, and authorized problem statement.
  2. **Live Physics Simulation (40s):** DeepMind MuJoCo simulation showcasing kinematic movement, actuators, and dynamic obstacle avoidance.
  3. **Sensor Telemetry & Data (20s):** Real-time telemetry curves, positioning accuracy, or confusion matrix graphs.
  4. **CSBS Business Impact (10s):** Dimensionless cost parity ratio ($\kappa$) and labor reallocation payback horizon.

### 2. LinkedIn Publication & Tagging Protocol
* **Platform:** LinkedIn (video post from any team member or collaborative post).
* **Mandatory Institutional Tags:**
  * Institution: `@SVKM's NMIMS MPSTME`
  * Academic Directorate & Dean, MPSTME
  * Course Faculty & Mentors
* **Hashtags:** `#NMIMS #MPSTME #Robotics #PBL #EngineeringResearch #DeepMindMuJoCo #Industry40`

### 3. Submission & Automatic Portal Synchronization
1. Once published on LinkedIn, copy the URL of your post.
2. Open your group's `docs/TEAM_ROSTER.json` and paste the URL into `"linkedin_url"` under `"project_showcase"`.
3. Commit and push on your feature branch:
   ```bash
   git add docs/TEAM_ROSTER.json
   git commit -m "docs(showcase): submit LinkedIn demonstration video URL for Group XX"
   git push origin feat/<your-branch-name>
   ```
4. Open a Pull Request. Once merged, the automated synchronization script updates your group's `README.md` and the cohort dashboard.

