# MDRIIA PBL Git Contribution Guidelines

All students enrolled in MDRIIA (CSBS Sem VI, AY 2026-27) must adhere to these software and research guidelines.

## 1. Branch Naming Standard
* Feature Branch: `feat/<roll_no>-<module_name>` (e.g. `feat/e006-amr-chassis`)
* Fix Branch: `fix/<roll_no>-<issue>` (e.g. `fix/e016-pid-overshoot`)
* Documentation/Paper: `docs/<roll_no>-<section>` (e.g. `docs/e054-csbs-roi-model`)

## 2. Conventional Commit Prefixes
* `feat(scope)`: New physics model, kinematics solver, or business equation.
* `fix(scope)`: Bugfix in controller loop, collision mesh, or data parsing.
* `perf(scope)`: Simulation speedup, vectorized NumPy operations.
* `docs(scope)`: Research paper sections, README updates, mathematical derivations.
* `test(scope)`: Monte Carlo validation runs, unit test assertions.

## 3. CSBS Technoeconomic Constraint
All business and ROI models must be **dimensionless** or expressed in terms of **operational cost-parity ratios, labor reallocation percentages, or payback cycles**. Never use raw currency amounts.
