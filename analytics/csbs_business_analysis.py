"""
CSBS techno-economic business analysis of the companion robot. Strictly dimensionless: no currency anywhere.

Unit of value: U = one full-time attendant-year of cost (1 U = what one attendant costs to employ for a year). Everything is per patient-year.
Measured inputs (sensitivity, false-dispatch rate) come from results/<run>/metrics.json (simulation results). Every other number is an ASSUMPTION
labelled A1..A14 below, with its source status, and is varied in the sensitivity and Monte Carlo analysis. Nothing here is a measured economic fact.

    python analytics/csbs_business_analysis.py        -> results/business_analysis/{model.json, *.png}
"""
import json
import math
import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "results", "business_analysis")
os.makedirs(OUT, exist_ok=True)

# ---- assumption register (value, source status) -------------------------------------------------------------------
A = dict(
    falls_per_year=(1.2, "A1 falls per fall-prone older adult per year [research guide, not independently verified]"),
    bed_days_saved=(14.2, "A2 bed-days saved per early-dispatched fall, 18.4 - 4.2 [titles sheet; NO primary source found]"),
    bed_day_in_att_days=(3.0, "A3 one hospital bed-day in attendant-days [assumption, varied 1 to 5]"),
    adl_events=(1825.0, "A4 look-alike daily events per year, about 5 a day [research guide]"),
    fd_cost_bed_days=(0.65, "A5 one unnecessary emergency dispatch in bed-day equivalents [research guide, assumed]"),
    capex=(0.25, "A6 capital cost of the robot in attendant-years = 3 attendant-months [titles sheet, upper bound; varied 2 to 4 months]"),
    life=(5.0, "A7 service life in years [assumption, varied 3 to 7]"),
    opex_robot=(0.20, "A8 robot running cost per year in attendant-years [assumption, varied 0.10 to 0.30; standards manual limit kappa <= 0.25]"),
    vigil_h_week=(168.0, "A9 continuous vigilance hours per week for one patient [research guide]"),
    alpha=(0.0, "A10 share of vigilance hours the robot really replaces [assumption; base 0 = clinical value only; varied 0 to 0.15]"),
    cam_capex=(0.025, "A11 capital cost of one fixed camera, 10% of the robot [assumption]"),
    cam_opex=(0.03, "A12 running cost of one fixed camera per year [assumption]"),
    service_rate=(12.0, "A13 alerts one caregiver can handle per hour, 5 minutes each [assumption]"),
    hours_per_fte=(2080.0, "A14 hours per full-time attendant-year [standards manual]"),
)
v = {k: x[0] for k, x in A.items()}

# ---- measured inputs ----------------------------------------------------------------------------------------------
def load(run):
    return json.load(open(os.path.join(ROOT, "results", run, "metrics.json")))
MG, MC = load("guide_robot_test"), load("small_robot_test")
SYSTEMS = {
    "Baymax, guide robot (measured)": dict(m=MG, key="robot", devices=1, kind="robot"),
    "Compact robot (earlier run)": dict(m=MC, key="robot", devices=1, kind="robot"),
    "4 fixed cameras": dict(m=MG, key="static4", devices=4, kind="cam"),
    "1 fixed camera": dict(m=MG, key="static", devices=1, kind="cam"),
}
def measured(m, key):
    d = m[f"dispatch_{key}"]
    return d["TP"] / (d["TP"] + d["FN"]), d["FP"] / (d["FP"] + d["TN"]), d["TP"], d["TP"] + d["FN"], d["FP"], d["FP"] + d["TN"]

def model(s, phi, kind, devices, p=v):
    """Per patient-year, in attendant-years. Returns dict of the stack."""
    b = p["bed_day_in_att_days"] / 365.0
    clinical = p["falls_per_year"] * s * p["bed_days_saved"] * b
    labour = p["alpha"] * p["vigil_h_week"] * 52.0 / p["hours_per_fte"]
    if kind == "robot":
        cap_year = p["capex"] / p["life"]; opex = p["opex_robot"]
    else:
        cap_year = devices * p["cam_capex"] / p["life"]; opex = devices * p["cam_opex"]
    fd = p["adl_events"] * phi * p["fd_cost_bed_days"] * b
    benefit, cost = clinical + labour, cap_year + opex + fd
    kappa = (opex + fd) / 1.0                                   # operating cost per attendant-year, false dispatches included (standards-manual kappa)
    capex_total = p["capex"] if kind == "robot" else devices * p["cam_capex"]
    payback_m = 12.0 * capex_total / (1.0 - kappa) if kappa < 1 else float("inf")
    return dict(clinical=clinical, labour=labour, cap_year=cap_year, opex=opex, false_dispatch=fd, benefit=benefit, cost=cost, net=benefit - cost,
                roi=(benefit - cost) / cost if cost else float("nan"), kappa=kappa, ncri=1 - kappa, payback_months=payback_m,
                benefit_cost_ratio=benefit / cost if cost else float("nan"))

rows = {}
for name, cfg in SYSTEMS.items():
    s, phi, tp, nf, fp, nn = measured(cfg["m"], cfg["key"])
    rows[name] = dict(sens=s, phi=phi, tp=tp, falls=nf, fp=fp, neg=nn, **model(s, phi, cfg["kind"], cfg["devices"]))

# ---- break-evens for the guide robot --------------------------------------------------------------------------------
s_g, phi_g = rows["Baymax, guide robot (measured)"]["sens"], rows["Baymax, guide robot (measured)"]["phi"]
base = rows["Baymax, guide robot (measured)"]
L_full = v["vigil_h_week"] * 52.0 / v["hours_per_fte"]            # 4.2 FTE
alpha_star = max(0.0, (base["cost"] - base["clinical"]) / L_full)
b = v["bed_day_in_att_days"] / 365.0
phi_kappa = (0.25 - v["opex_robot"]) / (v["adl_events"] * v["fd_cost_bed_days"] * b)    # false-dispatch rate at which kappa reaches 0.25
cost_no_fd = v["capex"] / v["life"] + v["opex_robot"]
bd_star = (cost_no_fd) / (v["falls_per_year"] * s_g * v["bed_days_saved"] / 365.0)          # bed-day ratio at which clinical value alone covers cost (no false dispatches)
capex_star = max(0.0, (base["clinical"] - v["opex_robot"] - base["false_dispatch"]) * v["life"])

# ---- labour-reallocation scenarios (alpha) ---------------------------------------------------------------------------
alphas = [0, 0.05, 0.10, 0.15, 0.25]
alpha_tab = []
for a in alphas:
    p = dict(v, alpha=a)
    r = model(s_g, phi_g, "robot", 1, p); r2 = model(s_g, 0.0, "robot", 1, p)
    alpha_tab.append(dict(alpha=a, H_hours_per_day=a * 24, fte=a * L_full, net=r["net"], roi=r["roi"], net_no_false_dispatch=r2["net"], roi_no_fd=r2["roi"]))

# ---- Monte Carlo over the model's uncertain inputs ---------------------------------------------------------------------
rng = np.random.default_rng(2026)
N = 20000
def mc(name):
    cfg = SYSTEMS[name]; _, _, tp, nf, fp, nn = measured(cfg["m"], cfg["key"])
    s = rng.beta(tp + 1, nf - tp + 1, N); phi = rng.beta(fp + 1, nn - fp + 1, N)
    f = rng.uniform(0.6, 1.5, N); dh = rng.uniform(6.0, 14.2, N); bd = rng.uniform(1, 5, N); lifeY = rng.uniform(3, 7, N)
    al = rng.uniform(0, 0.15, N)
    if cfg["kind"] == "robot":
        capex = rng.uniform(2, 4, N) / 12.0; opex = rng.uniform(0.10, 0.30, N)
    else:
        capex = cfg["devices"] * rng.uniform(0.01, 0.04, N); opex = cfg["devices"] * rng.uniform(0.01, 0.05, N)
    bb = bd / 365.0
    benefit = f * s * dh * bb + al * L_full
    cost = capex / lifeY + opex + v["adl_events"] * phi * v["fd_cost_bed_days"] * bb
    net = benefit - cost
    kappa = opex + v["adl_events"] * phi * v["fd_cost_bed_days"] * bb
    return dict(net=net, kappa=kappa, roi=net / cost, p_pos=float((net > 0).mean()), p_kappa=float((kappa <= 0.25).mean()),
                q=[float(np.percentile(net, q)) for q in (5, 50, 95)], roi_med=float(np.median(net / cost)))
MCR = {n: mc(n) for n in SYSTEMS}
mc_clin = {}
for n in SYSTEMS:                                   # the same, clinical value only (alpha forced to 0)
    cfg = SYSTEMS[n]; _, _, tp, nf, fp, nn = measured(cfg["m"], cfg["key"])
    s = rng.beta(tp + 1, nf - tp + 1, N); phi = rng.beta(fp + 1, nn - fp + 1, N); f = rng.uniform(0.6, 1.5, N); dh = rng.uniform(6, 14.2, N); bd = rng.uniform(1, 5, N); lifeY = rng.uniform(3, 7, N)
    if cfg["kind"] == "robot": capex = rng.uniform(2, 4, N) / 12.0; opex = rng.uniform(0.10, 0.30, N)
    else: capex = cfg["devices"] * rng.uniform(0.01, 0.04, N); opex = cfg["devices"] * rng.uniform(0.01, 0.05, N)
    bb = bd / 365.0; net = f * s * dh * bb - (capex / lifeY + opex + v["adl_events"] * phi * v["fd_cost_bed_days"] * bb)
    mc_clin[n] = float((net > 0).mean())

# ---- tornado: one-at-a-time swings on the guide robot net ------------------------------------------------------------------
def net_with(**kw):
    p = dict(v); p.update(kw); return model(s_g, phi_g, "robot", 1, p)["net"]
TORN = {
 "value of a bed-day (1 to 5 attendant-days)": (net_with(bed_day_in_att_days=1), net_with(bed_day_in_att_days=5)),
 "share of vigilance replaced (0 to 0.15)": (net_with(alpha=0), net_with(alpha=0.15)),
 "robot running cost (0.30 to 0.10)": (net_with(opex_robot=0.30), net_with(opex_robot=0.10)),
 "capital cost (4 to 2 attendant-months)": (net_with(capex=4 / 12), net_with(capex=2 / 12)),
 "falls per year (0.6 to 1.5)": (net_with(falls_per_year=0.6), net_with(falls_per_year=1.5)),
 "bed-days saved per fall (6 to 14.2)": (net_with(bed_days_saved=6), net_with(bed_days_saved=14.2)),
 "service life (3 to 7 years)": (net_with(life=3), net_with(life=7)),
}

# ---- capacity: M/M/c alert desk ------------------------------------------------------------------------------------------
lam_pat = (v["falls_per_year"] * s_g + v["adl_events"] * rows["Baymax, guide robot (measured)"]["phi"] * 0 + v["adl_events"] * MG["alarm_robot"]["FP"] / (MG["alarm_robot"]["FP"] + MG["alarm_robot"]["TN"])) / 8760.0   # heads-up alerts per patient-hour
mu = v["service_rate"]
def erlang_wq(c, lam):
    a = lam / mu; rho = a / c
    if rho >= 1: return float("inf")
    s_ = sum(a ** k / math.factorial(k) for k in range(c)); top = a ** c / math.factorial(c) / (1 - rho)
    pw = top / (s_ + top); return pw / (c * mu - lam) * 3600.0      # seconds
cap = []
for c in (1, 2, 3):
    Nmax = max(n for n in range(1, 200000) if erlang_wq(c, n * lam_pat) <= 60.0 and n * lam_pat / (c * mu) < 1) if erlang_wq(c, lam_pat) <= 60 else 0
    cap.append(dict(caregivers=c, patients_per_desk=Nmax, rho=Nmax * lam_pat / (c * mu)))
    if Nmax > 20000: break

# ---- figures ----------------------------------------------------------------------------------------------------------------------
names = list(rows)
fig, ax = plt.subplots(figsize=(7.0, 3.6), dpi=180); x = np.arange(len(names)); w = 0.38
ax.bar(x - w / 2, [rows[n]["benefit"] for n in names], w, label="benefit (clinical value + labour)", color="#2aa66a")
cs = [rows[n]["cap_year"] for n in names]; op = [rows[n]["opex"] for n in names]; fd = [rows[n]["false_dispatch"] for n in names]
ax.bar(x + w / 2, cs, w, label="capital per year", color="#8fb5f2"); ax.bar(x + w / 2, op, w, bottom=cs, label="running cost", color="#2b5fd9")
ax.bar(x + w / 2, fd, w, bottom=[a + b_ for a, b_ in zip(cs, op)], label="false-dispatch burden", color="#d6453d")
ax.set_xticks(x); ax.set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=6.5); ax.set_ylabel("attendant-years per patient-year", fontsize=8); ax.tick_params(labelsize=7); ax.legend(fontsize=6.5)
ax.set_title("Benefit (left bar) and cost stack (right bar) per patient-year, clinical value only", fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(OUT, "cost_benefit.png")); plt.close()

fig, ax = plt.subplots(figsize=(6.6, 3.2), dpi=180)
items = sorted(TORN.items(), key=lambda kv: abs(kv[1][1] - kv[1][0]))
for i, (k, (lo, hi)) in enumerate(items):
    ax.barh(i, hi - lo, left=lo, color="#2b5fd9" if hi >= lo else "#d6453d")
ax.axvline(base["net"], color="k", lw=0.8); ax.axvline(0, color="#2aa66a", ls="--", lw=1); ax.set_yticks(range(len(items))); ax.set_yticklabels([k for k, _ in items], fontsize=6.5)
ax.set_xlabel("net benefit per patient-year (attendant-years); green dashed = break-even", fontsize=7); ax.tick_params(labelsize=7); ax.set_title("Guide robot: which assumption moves the result most", fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(OUT, "tornado.png")); plt.close()

fig, ax = plt.subplots(figsize=(6.6, 3.2), dpi=180)
for n, c in zip(names, ["#2b5fd9", "#8fb5f2", "#e08a1e", "#999"]):
    ax.hist(MCR[n]["net"], bins=80, alpha=0.55, color=c, label=f"{n.split(' (')[0]}: P(net>0) = {MCR[n]['p_pos']:.2f}", range=(-1.0, 1.0))
ax.axvline(0, color="k", lw=0.8); ax.set_xlabel("net benefit per patient-year (attendant-years), with 0 to 0.15 of vigilance replaced", fontsize=7); ax.set_ylabel("Monte Carlo draws", fontsize=7); ax.tick_params(labelsize=7); ax.legend(fontsize=6); ax.set_title("Uncertainty analysis (20,000 draws, inputs varied over their stated ranges)", fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(OUT, "montecarlo.png")); plt.close()

fig, ax = plt.subplots(figsize=(6.2, 3.1), dpi=180)
al = np.linspace(0, 0.25, 60)
ax.plot(al, [model(s_g, phi_g, "robot", 1, dict(v, alpha=a))["roi"] for a in al], color="#2b5fd9", label="as measured (false-dispatch rate %.3f)" % phi_g)
ax.plot(al, [model(s_g, 0.0, "robot", 1, dict(v, alpha=a))["roi"] for a in al], color="#2aa66a", label="if false dispatches are removed")
ax.axhline(0, color="k", lw=0.8); ax.axvline(alpha_star, color="#d6453d", ls="--", lw=1); ax.text(alpha_star + 0.003, ax.get_ylim()[0] * 0.8, f"break-even share {alpha_star:.2f}", fontsize=6.5, color="#d6453d")
ax.set_xlabel("share of continuous vigilance hours the robot replaces (alpha)", fontsize=7); ax.set_ylabel("yearly return on cost, (benefit - cost) / cost", fontsize=7); ax.tick_params(labelsize=7); ax.legend(fontsize=6.5); ax.set_title("Where the profit comes from: labour reallocation", fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(OUT, "profit_vs_alpha.png")); plt.close()

json.dump(dict(assumptions={k: dict(value=x[0], source=x[1]) for k, x in A.items()}, systems=rows, break_even=dict(alpha_star=alpha_star, false_dispatch_rate_for_kappa_025=phi_kappa, bed_day_ratio_clinical_only=bd_star, capex_attendant_years_for_zero_net=capex_star, vigilance_fte=L_full),
                alpha_table=alpha_tab, monte_carlo={n: {k: x for k, x in r.items() if k in ("p_pos", "p_kappa", "q", "roi_med")} for n, r in MCR.items()}, mc_clinical_only_p_pos=mc_clin,
                tornado={k: list(x) for k, x in TORN.items()}, capacity=dict(alerts_per_patient_hour=lam_pat, service_rate=mu, desk=cap)), open(os.path.join(OUT, "model.json"), "w"), indent=1, default=float)
print(json.dumps({n: {k: round(x, 3) for k, x in r.items() if isinstance(x, float)} for n, r in rows.items()}, indent=0)[:1800])
print("break-even", {k: round(x, 3) for k, x in dict(alpha=alpha_star, phi=phi_kappa, bd=bd_star, capex=capex_star).items()})
print("MC", {n: (round(r["p_pos"], 3), round(r["p_kappa"], 3)) for n, r in MCR.items()}, "clinical-only", {n: round(x, 3) for n, x in mc_clin.items()})
print("capacity", cap, "lam/patient-hour", lam_pat)
