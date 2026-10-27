# Experiment results: split 'test'

120 trials (60 falls, 60 daily activities); every trial was run with the robot AND with the fixed-camera baseline on the same recorded motion (paired). All numbers are simulation results.

## Alarm level (heads-up sent; positive = any fall)

| condition | TP | FN | FP | TN | sensitivity (95% CI) | specificity (95% CI) | precision | recall | F1 | false-alarm rate |
|---|---|---|---|---|---|---|---|---|---|---|
| robot | 41 | 19 | 6 | 54 | 0.683 (0.56-0.79) | 0.900 (0.80-0.95) | 0.872 | 0.683 | 0.766 | 0.100 |
| static | 4 | 56 | 3 | 57 | 0.067 (0.03-0.16) | 0.950 (0.86-0.98) | 0.571 | 0.067 | 0.119 | 0.050 |
| static4 | 31 | 29 | 3 | 57 | 0.517 (0.39-0.64) | 0.950 (0.86-0.98) | 0.912 | 0.517 | 0.660 | 0.050 |

## Dispatch level (family emergency + ambulance; positive = fall with no answer)

| condition | TP | FN | FP | TN | sensitivity (95% CI) | specificity (95% CI) | precision | recall | F1 | false-alarm rate |
|---|---|---|---|---|---|---|---|---|---|---|
| robot | 28 | 15 | 2 | 75 | 0.651 (0.50-0.78) | 0.974 (0.91-0.99) | 0.933 | 0.651 | 0.767 | 0.026 |
| static | 2 | 41 | 0 | 77 | 0.047 (0.01-0.15) | 1.000 (0.95-1.00) | 1.000 | 0.047 | 0.089 | 0.000 |
| static4 | 20 | 23 | 0 | 77 | 0.465 (0.33-0.61) | 1.000 (0.95-1.00) | 1.000 | 0.465 | 0.635 | 0.000 |

## By event type

| condition | subtype | n | alarm | dispatch | median_lat_alarm | median_lat_dispatch |
|---|---|---|---|---|---|---|
| robot | cardiac | 15 | 9 | 9 | 17.6 | 34.7 |
| robot | drop_keys | 10 | 0 | 0 |  |  |
| robot | lie_bed | 10 | 1 | 1 |  |  |
| robot | lie_floor | 5 | 5 | 0 |  |  |
| robot | sit_floor | 5 | 0 | 0 |  |  |
| robot | sit_sofa_abrupt | 12 | 0 | 0 |  |  |
| robot | sit_sofa_slow | 8 | 0 | 0 |  |  |
| robot | slip | 15 | 13 | 6 | 10.8 | 40.4 |
| robot | syncope | 15 | 9 | 9 | 67.0 | 82.3 |
| robot | tie_shoelaces | 10 | 0 | 0 |  |  |
| robot | trip | 15 | 10 | 5 | 46.5 | 75.3 |
| static | cardiac | 15 | 1 | 0 | 0.2 |  |
| static | drop_keys | 10 | 1 | 0 |  |  |
| static | lie_bed | 10 | 0 | 0 |  |  |
| static | lie_floor | 5 | 0 | 0 |  |  |
| static | sit_floor | 5 | 2 | 0 |  |  |
| static | sit_sofa_abrupt | 12 | 0 | 0 |  |  |
| static | sit_sofa_slow | 8 | 0 | 0 |  |  |
| static | slip | 15 | 1 | 0 | 3.0 |  |
| static | syncope | 15 | 0 | 1 | -1.3 | 8.8 |
| static | tie_shoelaces | 10 | 0 | 0 |  |  |
| static | trip | 15 | 2 | 1 | 3.0 | 12.6 |
| static4 | cardiac | 15 | 6 | 5 | 3.1 | 13.2 |
| static4 | drop_keys | 10 | 1 | 0 |  |  |
| static4 | lie_bed | 10 | 0 | 0 |  |  |
| static4 | lie_floor | 5 | 0 | 0 |  |  |
| static4 | sit_floor | 5 | 2 | 0 |  |  |
| static4 | sit_sofa_abrupt | 12 | 0 | 0 |  |  |
| static4 | sit_sofa_slow | 8 | 0 | 0 |  |  |
| static4 | slip | 15 | 10 | 3 | 5.1 | 15.2 |
| static4 | syncope | 15 | 9 | 10 | 3.5 | 13.5 |
| static4 | tie_shoelaces | 10 | 0 | 0 |  |  |
| static4 | trip | 15 | 6 | 2 | 5.1 | 13.9 |

## By where she fell

| condition | zone | n | alarm | dispatch | median_lat_alarm |
|---|---|---|---|---|---|
| robot | bedroom | 20 | 10 | 8 | 68.8 |
| robot | hallway | 20 | 16 | 10 | 49.6 |
| robot | living | 20 | 15 | 11 | 8.6 |
| static | bedroom | 20 | 2 | 2 | 2.6 |
| static | hallway | 20 | 0 | 0 |  |
| static | living | 20 | 2 | 0 | 1.8 |
| static4 | bedroom | 20 | 13 | 11 | 3.1 |
| static4 | hallway | 20 | 15 | 9 | 5.1 |
| static4 | living | 20 | 3 | 0 | 3.4 |

## Latency from the hip reaching the floor (s), successful detections only

| level | condition | n | mean | sd | se | median | p95 | max | min |
|---|---|---|---|---|---|---|---|---|---|
| alarm | robot | 40 | 36.24 | 28.80 | 4.55 | 30.43 | 83.84 | 86.45 | 2.82 |
| alarm | static | 4 | 2.27 | 1.46 | 0.73 | 2.76 | 3.35 | 3.41 | 0.15 |
| alarm | static4 | 30 | 4.03 | 1.26 | 0.23 | 3.77 | 5.41 | 5.98 | 0.15 |
| dispatch | robot | 27 | 53.17 | 26.17 | 5.04 | 48.76 | 90.40 | 99.14 | 13.00 |
| dispatch | static | 2 | 10.71 | 2.70 | 1.91 | 10.71 | 12.43 | 12.62 | 8.80 |
| dispatch | static4 | 19 | 13.73 | 1.53 | 0.35 | 13.55 | 15.31 | 15.98 | 8.80 |

## Robot vs 4 fixed cameras

- **alarm detection** (positives only, n=60): robot-only 21, static4-only 11, both 20, neither 8; exact McNemar p = 0.1102
  - latency where BOTH detected (n=20): robot minus static4 = nan s, 95% CI [nan, nan], paired t(19) = nan, p = nan, Cohen's d = nan
  - latency of all successes (robot n=41, static4 n=31): difference 32.21 s, 95% CI [22.99, 41.43], Welch t(39.2) = 7.06, p = 1.706e-08, Cohen's d = 1.48
- **dispatch detection** (positives only, n=43): robot-only 16, static4-only 8, both 12, neither 7; exact McNemar p = 0.1516
  - latency where BOTH detected (n=12): robot minus static4 = nan s, 95% CI [nan, nan], paired t(11) = nan, p = nan, Cohen's d = nan
  - latency of all successes (robot n=28, static4 n=20): difference 39.44 s, 95% CI [29.07, 49.81], Welch t(26.3) = 7.81, p = 2.57e-08, Cohen's d = 1.96

## Robot vs 1 fixed camera

- **alarm detection** (positives only, n=60): robot-only 38, static-only 1, both 3, neither 18; exact McNemar p = 1.455e-10
  - latency where BOTH detected (n=3): robot minus static = 19.77 s, 95% CI [-30.96, 70.50], paired t(2) = 1.68, p = 0.2356, Cohen's d = 0.97
  - latency of all successes (robot n=41, static n=4): difference 33.97 s, 95% CI [24.65, 43.28], Welch t(40.7) = 7.36, p = 5.303e-09, Cohen's d = 1.22
- **dispatch detection** (positives only, n=43): robot-only 27, static-only 1, both 1, neither 14; exact McNemar p = 2.161e-07
  - latency of all successes (robot n=28, static n=2): difference 42.46 s, 95% CI [31.29, 53.63], Welch t(22.1) = 7.88, p = 7.288e-08, Cohen's d = 1.65

### Dispatch within a time window after the fall (positives = fall with no answer)

| window | robot | 1 fixed camera | 4 fixed cameras |
|---|---|---|---|
| 15 s | 1/43 = 0.02 (0.00-0.12) | 2/43 = 0.05 (0.01-0.15) | 14/43 = 0.33 (0.20-0.47) |
| 30 s | 7/43 = 0.16 (0.08-0.30) | 2/43 = 0.05 (0.01-0.15) | 19/43 = 0.44 (0.30-0.59) |
| 60 s | 16/43 = 0.37 (0.24-0.52) | 2/43 = 0.05 (0.01-0.15) | 19/43 = 0.44 (0.30-0.59) |
| 100 s | 27/43 = 0.63 (0.48-0.76) | 2/43 = 0.05 (0.01-0.15) | 19/43 = 0.44 (0.30-0.59) |

## Daily activities: false alarms (alarm / dispatch)

| activity | n | robot | 1 fixed camera | 4 fixed cameras |
|---|---|---|---|---|
| drop_keys | 10 | 0 / 0 | 1 / 0 | 1 / 0 |
| lie_bed | 10 | 1 / 1 | 0 / 0 | 0 / 0 |
| lie_floor | 5 | 5 / 0 | 0 / 0 | 0 / 0 |
| sit_floor | 5 | 0 / 0 | 2 / 0 | 2 / 0 |
| sit_sofa_abrupt | 12 | 0 / 0 | 0 / 0 | 0 / 0 |
| sit_sofa_slow | 8 | 0 / 0 | 0 / 0 | 0 / 0 |
| tie_shoelaces | 10 | 0 / 0 | 0 / 0 | 0 / 0 |

## Robot safety and privacy (all robot trials)

```
{
 "max_commanded_speed_mps": 0.7690989568591542,
 "max_true_speed_mps_incl_being_hit": 3.29,
 "max_collision_force_N_not_human": 4416.215,
 "max_human_contact_N": 40090.57,
 "trials_hit_by_her_over_50N": 25,
 "trials_pose_error_over_0_5m": 20,
 "trials_with_contact_over_5N": 24,
 "max_tilt_deg": 87.49,
 "bytes_before_first_alert_max": 0,
 "pose_error_final_median_m": 0.027,
 "pose_error_final_max_m": 4.339
}
```
