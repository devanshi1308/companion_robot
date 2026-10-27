"""
Healthcare economics of the companion robot: strictly dimensionless (no currency of any kind: bed-days, attendant-years and ratios only).

The model is driven by the MEASURED results of the experiment set (sensitivity, false-alarm rate, latency of the robot and of the fixed
camera, from outputs/experiments/<split>/analysis/metrics.json) combined with a small set of ASSUMED constants that are named below with
their source.  Nothing in this file is a measured economic fact; it shows how the measured detection quality moves the economics.

  python analytics/healthcare_economics.py [split]          (default split: test)

Definitions (standards manual): FTE = hours / 2080;  payback (months) = 12 * K0 / (1 - kappa), where K0 is the capital cost in attendant-years
and kappa the operating cost of the robot per unit of attendant cost (must stay <= 0.25).
"""
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ---- assumed constants (source in brackets; none is measured here) -------------------------------------
N_FALL_PER_YEAR = 1.2             # falls per fall-prone older adult per year [research guide]
N_ADL_EVENTS_PER_YEAR = 1825.0    # high-motion daily-living events that could be mistaken for a fall, about 5 a day [research guide]
BED_DAYS_NO_RAPID, BED_DAYS_RAPID = 18.4, 4.2     # acute stay after a fall without / with rapid response [sir's feedback sheet]
RHO_DISPATCH = 0.65               # one unnecessary emergency dispatch, in bed-day equivalents [research guide, assumed]
BED_DAY_IN_ATTENDANT_DAYS = 3.0   # one hospital bed-day expressed in attendant-days [assumed; sweep below]
K0 = 0.25                         # capital cost in attendant-years: 'under 3 months of a full-time attendant' [sir's feedback sheet]
KAPPA_OPS = 0.20                  # robot running cost (power, maintenance, connectivity, amortised repair) per attendant-year, WITHOUT false dispatches [assumed]
KAPPA_LIMIT = 0.25                # standards manual
VIGILANCE_H_PER_WEEK = 168.0      # continuous supervision replaced [research guide]
T_LONG_LIE_MIN = 78.5             # unassisted time on the floor, minutes [literature figure quoted in the guide; citation NOT yet verified]
WINDOW_MIN = 6.0                  # cardiac-arrest survival window (AHA / ERC)


def load_metrics(split):
    p = os.path.join(ROOT, "outputs", "experiments", split, "analysis", "metrics.json")
    if not os.path.exists(p):                                   # a fresh clone has no outputs/: fall back to the committed results
        p = os.path.join(ROOT, "results", "guide_robot_test" if split == "test" else f"{split}_test", "metrics.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def model(sens, far, lat_s, label):
    """sens: detection of a fall with no answer; far: false dispatches per daily-activity event; lat_s: median fall-to-dispatch time (s)."""
    gross = N_FALL_PER_YEAR * sens * (BED_DAYS_NO_RAPID - BED_DAYS_RAPID)           # bed-days saved per patient-year
    false_dispatches = N_ADL_EVENTS_PER_YEAR * far                                    # per patient-year
    fa_burden_bed_days = false_dispatches * RHO_DISPATCH
    net = gross - fa_burden_bed_days
    # false dispatches expressed against the yearly attendant: bed-days -> attendant-days -> attendant-years
    kappa = KAPPA_OPS + fa_burden_bed_days * BED_DAY_IN_ATTENDANT_DAYS / 365.0
    payback = 12.0 * K0 / (1.0 - kappa) if kappa < 1 else float("inf")
    long_lie_reduction = 1.0 - (lat_s / 60.0) / T_LONG_LIE_MIN if lat_s == lat_s else float("nan")
    # largest false-dispatch rate per ADL event that still keeps kappa within the limit
    far_max = (KAPPA_LIMIT - KAPPA_OPS) * 365.0 / BED_DAY_IN_ATTENDANT_DAYS / (N_ADL_EVENTS_PER_YEAR * RHO_DISPATCH)
    return dict(system=label, sensitivity=sens, false_dispatch_rate_per_adl_event=far, false_dispatches_per_year=false_dispatches,
                gross_bed_days_saved_per_year=gross, false_dispatch_burden_bed_days=fa_burden_bed_days, net_bed_days_saved_per_year=net,
                kappa=kappa, kappa_within_limit=bool(kappa <= KAPPA_LIMIT), payback_months=payback, median_response_min=lat_s / 60.0 if lat_s == lat_s else float("nan"),
                long_lie_reduction=long_lie_reduction, max_false_dispatch_rate_for_kappa_limit=far_max, min_specificity_for_kappa_limit=1.0 - far_max)


def payback_table():
    """Payback months = capital cost in months of attendant cost / (1 - kappa) (standards manual: 12 * K0 / (1 - kappa), K0 in attendant-years).
    The sheet claims BOTH 'robot cost under 3 months of an attendant' AND 'return within the first calendar quarter (3 months)'. With kappa > 0 the payback is
    always longer than the capital cost, so the two claims fit together only if the capital cost is at most 3 * (1 - kappa) months of attendant cost."""
    rows = []
    for cost_m in (1.5, 2.0, 2.4, 3.0):
        for kap in (0.10, 0.20, 0.25):
            rows.append(dict(capital_cost_in_attendant_months=cost_m, kappa=kap, payback_months=round(cost_m / (1 - kap), 2), within_one_quarter=bool(cost_m / (1 - kap) <= 3.0)))
    limits = {f"kappa_{k}": round(3.0 * (1 - k), 2) for k in (0.10, 0.20, 0.25)}
    return rows, limits


def print_payback_table():
    rows, limits = payback_table()
    print("\nPayback against the sheet's two claims (dimensionless):")
    print("  capital cost (attendant-months)   kappa   payback (months)   within one quarter?")
    for r in rows:
        print(f"  {r['capital_cost_in_attendant_months']:>30.1f}   {r['kappa']:.2f}   {r['payback_months']:>16.2f}   {'yes' if r['within_one_quarter'] else 'NO'}")
    print(f"  Largest capital cost that still pays back within 3 months: {limits['kappa_0.1']} months of attendant cost at kappa 0.10, "
          f"{limits['kappa_0.2']} at kappa 0.20, {limits['kappa_0.25']} at kappa 0.25. The model used here (cost = 3 months, kappa 0.20) gives 3.75 months.")
    out = os.path.join(ROOT, "results", "small_robot_test")
    if os.path.isdir(out):
        json.dump(dict(rows=rows, max_capital_cost_months_for_one_quarter=limits), open(os.path.join(out, "payback_sensitivity.json"), "w"), indent=1)


def main(split="test"):
    if split == "payback":
        print_payback_table()
        return None
    M = load_metrics(split)
    print("=" * 78)
    print("HEALTHCARE ECONOMICS (dimensionless: bed-days, attendant-years, ratios)")
    print("=" * 78)
    if M is None:
        print(f"No measured results for split '{split}' yet (run the experiments and analyze.py). Nothing printed from the model.")
        return None
    out = []
    for c, name in (("robot", "companion robot"), ("static4", "4 fixed cameras"), ("static", "1 fixed camera")):
        d = M[f"dispatch_{c}"]
        far = d["FP"] / max(d["FP"] + d["TN"], 1)
        lat = M[f"lat_dispatch_{c}"].get("median", float("nan"))
        out.append(model(d["sensitivity"], far, lat, name))
    for r in out:
        print(f"\n{r['system']}")
        for k, v in r.items():
            if k != "system":
                print(f"  {k:48s} {v:.4g}" if isinstance(v, float) else f"  {k:48s} {v}")
    print("\nEvidence behind the false-dispatch rate (observed on the test split):")
    for c in ("robot", "static4", "static"):
        d, a = M[f"dispatch_{c}"], M[f"alarm_{c}"]
        n_neg = d["FP"] + d["TN"]
        z = 1.96
        p = d["FP"] / n_neg
        upper = (p + z * z / (2 * n_neg) + z * (p * (1 - p) / n_neg + z * z / (4 * n_neg * n_neg)) ** 0.5) / (1 + z * z / n_neg)
        fa_alarm = a["FP"] / max(a["FP"] + a["TN"], 1)
        print(f"  {c:8s} false dispatches {d['FP']}/{n_neg}; 95% upper bound of the rate {upper:.3f} (the kappa limit needs <= {out[0]['max_false_dispatch_rate_for_kappa_limit']:.4f});"
              f" family heads-up false-alarm rate {fa_alarm:.2f} per negative trial = about {fa_alarm * N_ADL_EVENTS_PER_YEAR:.0f} texts a year at {N_ADL_EVENTS_PER_YEAR:.0f} look-alike events")
    print(f"  With no false dispatch seen, roughly {3 / out[0]['max_false_dispatch_rate_for_kappa_limit']:.0f} negative trials would be needed to show the rate is below the kappa limit (rule of three); 77 cannot.")
    fte = VIGILANCE_H_PER_WEEK * 52 / 2080.0
    print(f"\nContinuous vigilance replaced: {VIGILANCE_H_PER_WEEK:.0f} h/week = {fte:.2f} FTE (hours / 2080)")
    print("\nSensitivity of the robot's kappa to the one assumption that is hardest to defend (bed-day in attendant-days):")
    d = M["dispatch_robot"]
    far = d["FP"] / max(d["FP"] + d["TN"], 1)
    global BED_DAY_IN_ATTENDANT_DAYS
    keep = BED_DAY_IN_ATTENDANT_DAYS
    for v in (1.0, 2.0, 3.0, 5.0):
        BED_DAY_IN_ATTENDANT_DAYS = v
        r = model(d["sensitivity"], far, M["lat_dispatch_robot"].get("median", float("nan")), "robot")
        print(f"  bed-day = {v:.0f} attendant-days: kappa = {r['kappa']:.3f}, payback = {r['payback_months']:.1f} months")
    BED_DAY_IN_ATTENDANT_DAYS = keep
    print_payback_table()
    print("\nAssumed constants are listed at the top of this file; the 78.5-minute long-lie figure still needs its citation verified.")
    od = os.path.join(ROOT, "outputs", "experiments", split, "analysis"); os.makedirs(od, exist_ok=True)
    json.dump(out, open(os.path.join(od, "economics.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "test")
