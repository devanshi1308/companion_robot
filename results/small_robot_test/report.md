# Experiment results: split 'test'

120 trials (60 falls, 60 daily activities); every trial was run with the robot AND with the fixed-camera baseline on the same recorded motion (paired). All numbers are simulation results.

## Alarm level (heads-up sent; positive = any fall)

| condition | TP | FN | FP | TN | sensitivity (95% CI) | specificity (95% CI) | precision | recall | F1 | false-alarm rate |
|---|---|---|---|---|---|---|---|---|---|---|
| robot | 52 | 8 | 15 | 45 | 0.867 (0.76-0.93) | 0.750 (0.63-0.84) | 0.776 | 0.867 | 0.819 | 0.250 |
| static | 1 | 59 | 0 | 60 | 0.017 (0.00-0.09) | 1.000 (0.94-1.00) | 1.000 | 0.017 | 0.033 | 0.000 |
| static4 | 29 | 31 | 1 | 59 | 0.483 (0.36-0.61) | 0.983 (0.91-1.00) | 0.967 | 0.483 | 0.644 | 0.017 |

## Dispatch level (family emergency + ambulance; positive = fall with no answer)

| condition | TP | FN | FP | TN | sensitivity (95% CI) | specificity (95% CI) | precision | recall | F1 | false-alarm rate |
|---|---|---|---|---|---|---|---|---|---|---|
| robot | 37 | 6 | 0 | 77 | 0.860 (0.73-0.93) | 1.000 (0.95-1.00) | 1.000 | 0.860 | 0.925 | 0.000 |
| static | 1 | 42 | 0 | 77 | 0.023 (0.00-0.12) | 1.000 (0.95-1.00) | 1.000 | 0.023 | 0.045 | 0.000 |
| static4 | 20 | 23 | 0 | 77 | 0.465 (0.33-0.61) | 1.000 (0.95-1.00) | 1.000 | 0.465 | 0.635 | 0.000 |

## By event type

| condition | subtype | n | alarm | dispatch | median_lat_alarm | median_lat_dispatch |
|---|---|---|---|---|---|---|
| robot | cardiac | 15 | 13 | 13 | 15.3 | 30.8 |
| robot | drop_keys | 10 | 0 | 0 |  |  |
| robot | lie_bed | 10 | 0 | 0 |  |  |
| robot | lie_floor | 5 | 5 | 0 |  |  |
| robot | sit_floor | 5 | 5 | 0 |  |  |
| robot | sit_sofa_abrupt | 12 | 2 | 0 |  |  |
| robot | sit_sofa_slow | 8 | 3 | 0 |  |  |
| robot | slip | 15 | 14 | 6 | 14.5 | 19.8 |
| robot | syncope | 15 | 12 | 12 | 43.1 | 55.5 |
| robot | tie_shoelaces | 10 | 0 | 0 |  |  |
| robot | trip | 15 | 13 | 6 | 30.8 | 58.9 |
| static | cardiac | 15 | 0 | 0 |  |  |
| static | drop_keys | 10 | 0 | 0 |  |  |
| static | lie_bed | 10 | 0 | 0 |  |  |
| static | lie_floor | 5 | 0 | 0 |  |  |
| static | sit_floor | 5 | 0 | 0 |  |  |
| static | sit_sofa_abrupt | 12 | 0 | 0 |  |  |
| static | sit_sofa_slow | 8 | 0 | 0 |  |  |
| static | slip | 15 | 0 | 0 |  |  |
| static | syncope | 15 | 0 | 0 |  |  |
| static | tie_shoelaces | 10 | 0 | 0 |  |  |
| static | trip | 15 | 1 | 1 | 10.8 | 20.9 |
| static4 | cardiac | 15 | 5 | 5 | 3.2 | 13.3 |
| static4 | drop_keys | 10 | 0 | 0 |  |  |
| static4 | lie_bed | 10 | 0 | 0 |  |  |
| static4 | lie_floor | 5 | 0 | 0 |  |  |
| static4 | sit_floor | 5 | 0 | 0 |  |  |
| static4 | sit_sofa_abrupt | 12 | 0 | 0 |  |  |
| static4 | sit_sofa_slow | 8 | 0 | 0 |  |  |
| static4 | slip | 15 | 9 | 3 | 5.1 | 15.2 |
| static4 | syncope | 15 | 10 | 10 | 3.5 | 13.5 |
| static4 | tie_shoelaces | 10 | 1 | 0 |  |  |
| static4 | trip | 15 | 5 | 2 | 4.0 | 17.4 |

## By where she fell

| condition | zone | n | alarm | dispatch | median_lat_alarm |
|---|---|---|---|---|---|
| robot | bedroom | 20 | 15 | 11 | 51.9 |
| robot | hallway | 20 | 18 | 12 | 36.0 |
| robot | living | 20 | 19 | 14 | 5.6 |
| static | bedroom | 20 | 0 | 0 |  |
| static | hallway | 20 | 1 | 1 | 10.8 |
| static | living | 20 | 0 | 0 |  |
| static4 | bedroom | 20 | 12 | 9 | 3.1 |
| static4 | hallway | 20 | 17 | 11 | 5.1 |
| static4 | living | 20 | 0 | 0 |  |

## Latency from the hip reaching the floor (s), successful detections only

| level | condition | n | mean | sd | se | median | p95 | max | min |
|---|---|---|---|---|---|---|---|---|---|
| alarm | robot | 52 | 26.45 | 22.58 | 3.13 | 20.32 | 67.15 | 75.04 | 2.92 |
| alarm | static | 1 | 10.79 |  |  | 10.79 | 10.79 | 10.79 | 10.79 |
| alarm | static4 | 28 | 4.26 | 1.58 | 0.30 | 3.71 | 5.34 | 10.79 | 2.99 |
| dispatch | robot | 37 | 42.51 | 23.17 | 3.81 | 39.76 | 82.44 | 89.10 | 14.37 |
| dispatch | static | 1 | 20.86 |  |  | 20.86 | 20.86 | 20.86 | 20.86 |
| dispatch | static4 | 19 | 14.27 | 1.82 | 0.42 | 13.55 | 15.97 | 20.86 | 13.06 |

## Robot vs 4 fixed cameras

- **alarm detection** (positives only, n=60): robot-only 28, static4-only 5, both 24, neither 3; exact McNemar p = 6.619e-05
  - latency where BOTH detected (n=24): robot minus static4 = 30.14 s, 95% CI [21.27, 39.02], paired t(23) = 7.03, p = 3.673e-07, Cohen's d = 1.43
  - latency of all successes (robot n=52, static4 n=29): difference 22.19 s, 95% CI [15.88, 28.50], Welch t(51.9) = 7.05, p = 4.098e-09, Cohen's d = 1.21
- **dispatch detection** (positives only, n=43): robot-only 21, static4-only 4, both 16, neither 2; exact McNemar p = 0.0009105
  - latency where BOTH detected (n=16): robot minus static4 = 32.80 s, 95% CI [21.77, 43.83], paired t(15) = 6.34, p = 1.332e-05, Cohen's d = 1.58
  - latency of all successes (robot n=37, static4 n=20): difference 28.24 s, 95% CI [20.48, 36.01], Welch t(36.9) = 7.37, p = 9.346e-09, Cohen's d = 1.49

## Robot vs 1 fixed camera

- **alarm detection** (positives only, n=60): robot-only 51, static-only 0, both 1, neither 8; exact McNemar p = 8.882e-16
- **dispatch detection** (positives only, n=43): robot-only 36, static-only 0, both 1, neither 6; exact McNemar p = 2.91e-11

### Dispatch within a time window after the fall (positives = fall with no answer)

| window | robot | 1 fixed camera | 4 fixed cameras |
|---|---|---|---|
| 15 s | 2/43 = 0.05 (0.01-0.15) | 0/43 = 0.00 (0.00-0.08) | 14/43 = 0.33 (0.20-0.47) |
| 30 s | 14/43 = 0.33 (0.20-0.47) | 1/43 = 0.02 (0.00-0.12) | 19/43 = 0.44 (0.30-0.59) |
| 60 s | 28/43 = 0.65 (0.50-0.78) | 1/43 = 0.02 (0.00-0.12) | 19/43 = 0.44 (0.30-0.59) |
| 100 s | 37/43 = 0.86 (0.73-0.93) | 1/43 = 0.02 (0.00-0.12) | 19/43 = 0.44 (0.30-0.59) |

## Daily activities: false alarms (alarm / dispatch)

| activity | n | robot | 1 fixed camera | 4 fixed cameras |
|---|---|---|---|---|
| drop_keys | 10 | 0 / 0 | 0 / 0 | 0 / 0 |
| lie_bed | 10 | 0 / 0 | 0 / 0 | 0 / 0 |
| lie_floor | 5 | 5 / 0 | 0 / 0 | 0 / 0 |
| sit_floor | 5 | 5 / 0 | 0 / 0 | 0 / 0 |
| sit_sofa_abrupt | 12 | 2 / 0 | 0 / 0 | 0 / 0 |
| sit_sofa_slow | 8 | 3 / 0 | 0 / 0 | 0 / 0 |
| tie_shoelaces | 10 | 0 / 0 | 0 / 0 | 1 / 0 |

## Robot safety and privacy (all robot trials)

```
{
 "max_commanded_speed_mps": 0.7999935415304875,
 "max_true_speed_mps_incl_being_hit": 1.455,
 "max_collision_force_N_not_human": 11.957,
 "max_human_contact_N": 4580.481,
 "trials_hit_by_her_over_50N": 1,
 "trials_pose_error_over_0_5m": 8,
 "trials_with_contact_over_5N": 4,
 "max_tilt_deg": 16.69,
 "bytes_before_first_alert_max": 0,
 "pose_error_final_median_m": 0.021,
 "pose_error_final_max_m": 4.559
}
```
