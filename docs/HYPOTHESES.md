# Aalborg formulation: variables, hypotheses and what the data say

Interrogative (authorised title): How can a vision-based mobile companion robot in MuJoCo integrate MediaPipe fall-detection kinematics to reduce emergency dispatch latency within the critical 6-minute cardiac arrest survival window for elderly individuals living alone?

**Independent variables:** system (robot, 1 fixed camera, 4 fixed cameras); event type (trip, slip, syncope, cardiac fall; sitting, lying, tying shoelaces, dropping keys); where she fell (hallway, bedroom, living area); robot start; floor friction, clutter, disturbances (all randomised, seeds recorded).
**Dependent variables:** dispatch sensitivity, false-dispatch rate, alarm-level sensitivity and specificity, latency from floor contact to heads-up and to dispatch, safety (contact forces), economics (kappa, payback).

| # | Null hypothesis H0 | Alternative H1 | Test | Result (120 trials, guide robot) | Decision |
|---|---|---|---|---|---|
| H1 | Robot and 4 fixed cameras dispatch the same share of silent falls | Robot dispatches more | McNemar | 28/43 vs 20/43; discordant 16 vs 8, p = 0.15 | H0 not rejected |
| H2 | Robot and 1 fixed camera dispatch the same share | Robot dispatches more | McNemar | 27 vs 1 discordant, p = 2.2e-7 | H0 rejected, robot better |
| H3 | Robot latency to heads-up is not shorter than 4 cameras | Robot is shorter | Welch t / paired t | Robot 36.2 s vs 4.0 s; Welch p = 1.7e-8, paired +38.3 s p = 7e-6 | H0 stands: robot is significantly SLOWER |
| H4 | Specificity at dispatch level is below 98% | At least 98% | Wilson interval | 75/77 = 0.974, 95% CI [0.91, 0.99] | Not shown (interval includes values below 0.98) |
| H5 | Every detected fall is dispatched after the 6-minute window | Dispatch inside 360 s | descriptive | maximum 99.1 s | H1 holds descriptively (28 dispatches all under 100 s) |
| H6 | Operating-cost fraction kappa exceeds the 0.25 limit | kappa at most 0.25 | model | kappa = 0.45 | Not met |

Thresholds were fitted on a separate 40-trial dev split (seed 1) and frozen before the test split (seed 2). Alpha = 0.05 throughout; effect sizes, confidence intervals and exact p-values are in `results/guide_robot_test/significance.json` and the paper.
