# MDRIIA Git Branching & Submission Step-by-Step Guide

```
main (Faculty Reviewed & Protected)
  ▲
  │ Pull Request (via GitHub UI)
  │
feat/e006-amr-chassis (Individual Student Working Branch)
```

### Step 1: Clone the Monorepo
```bash
git clone https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026.git
cd NMIMS-MPSTME-MDRIIA-2026
```

### Step 2: Create Your Feature Branch
```bash
git checkout -b feat/<your-roll-no>-onboarding
```

### Step 3: Verify Your Local Environment
```bash
cd Group_XX_<Your_Names>
python src/test_env.py
```

### Step 4: Stage and Commit
```bash
git status
git add .
git commit -m "feat(group-XX): complete sprint 0 team roster and verify mujoco env"
```

### Step 5: Push Branch to GitHub
```bash
git push -u origin feat/<your-roll-no>-onboarding
```

### Step 6: Open a Pull Request
Visit `https://github.com/sunny-nanade/NMIMS-MPSTME-MDRIIA-2026` on your browser, click **Compare & pull request**, set the base to `main`, and submit!
