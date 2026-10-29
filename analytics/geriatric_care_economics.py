"""
Geriatric-care economics entry point (the starter file's name, now wired to the real model).  Strictly dimensionless: no currency.

The starter printed fixed constants.  This file runs the CSBS techno-economic model (analytics/csbs_business_analysis.py), whose measured
inputs (sensitivity, false-dispatch rate) come from results/guide_robot_test/metrics.json, and whose every other number is a labelled assumption
(A1..A14) varied by sensitivity and Monte Carlo analysis.

    python analytics/geriatric_care_economics.py
    -> results/business_analysis/{model.json, cost_benefit.png, tornado.png, montecarlo.png, profit_vs_alpha.png}

Definitions (standards manual): FTE = hours / 2080;  payback (months) = 12 * K0 / (1 - kappa);  kappa = operating cost per unit of attendant cost, limit 0.25.
"""
import json
import os
import runpy

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    runpy.run_path(os.path.join(ROOT, "analytics", "csbs_business_analysis.py"), run_name="__csbs__")
    m = json.load(open(os.path.join(ROOT, "results", "business_analysis", "model.json")))
    print("\n==================================================")
    print("GROUP 02 - GERIATRIC CARE ECONOMICS (dimensionless)")
    print("==================================================")
    for name, r in m["systems"].items():
        print(f"{name:34s} sensitivity {r['sens']:.2f}  kappa {r['kappa']:.3f} (limit 0.25)  payback {r['payback_months']:.2f} months  net {r['net']:+.3f} attendant-years/patient-year")
    print("All economic formulations are dimensionless indices; every non-measured input is a labelled assumption (see model.json).")


if __name__ == "__main__":
    main()
