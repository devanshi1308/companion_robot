"""
Statistics, tables and figures for one finished split.

    python src/experiments/analyze.py test           ->  outputs/experiments/test/analysis/{report.md, tables/*.csv, figures/*.png, metrics.json}

Definitions (stated again in the report):
  Alarm level      positive = a fall trial; predicted positive = the family heads-up (detector confirmed a person down) was sent.
  Dispatch level   positive = a fall after which she does NOT answer (syncope, cardiac, and the trips/slips where she stays silent);
                   predicted positive = family emergency + ambulance call was sent. A dispatch in an activity trial or after she answered
                   is a false dispatch.
  Latency          from the instant her hip reaches the floor (simulator truth) to the simulated message / call.
Everything is simulation: no real call or message is ever sent.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONDS = ("robot", "static", "static4")
NAMES = dict(robot="companion robot", static="1 fixed camera", static4="4 fixed cameras")


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def L_zone(sp):
    r = sp.get("event_room")
    return {"hallway": "hallway", "bedroom": "bedroom"}.get(r, "living")


def load(split):
    base = os.path.join(ROOT, "outputs", "experiments", split)
    rows = []
    for tid in sorted(os.listdir(base)):
        fn = os.path.join(base, tid, "result.json")
        if not os.path.exists(fn):
            continue
        res = json.load(open(fn))
        sp = json.load(open(os.path.join(base, tid, "spec.json")))
        spec, meta = sp["spec"], sp["clip_meta"]
        for cond, r in res.items():
            row = dict(r)
            row.update(condition=cond, route=spec.get("route"), friction=spec["friction_scale"], n_clutter=spec["n_clutter"],
                       vacuum_speed=spec["vacuum_speed"], odom_noise=spec["odom_noise"], push=spec["push"] is not None,
                       blackout=spec["blackout"] is not None, reply_latency=spec["reply_latency"], robot_start_mode=spec["robot_start_mode"],
                       walk_speed=spec["speed"], zone=spec.get("zone", L_zone(sp)))
            if cond == "robot":
                tel = os.path.join(base, tid, "telemetry_robot.csv")
                row["max_cmd_speed_mps"] = float(pd.read_csv(tel, usecols=["cmd_v"]).cmd_v.abs().max()) if os.path.exists(tel) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def derive(df):
    df = df.copy()
    df["is_fall"] = df.kind == "fall"
    df["needs_help"] = df.is_fall & ~df.conscious
    df["alarm"] = df.t_heads_up.notna()
    df["dispatch"] = df.t_emergency.notna()
    # a heads-up/dispatch that precedes the event is not a detection of it
    pre = df.t_heads_up.notna() & (df.t_heads_up < df.t_event - 0.5) & df.is_fall
    df.loc[pre, "alarm"] = False
    df["lat_alarm"] = df.t_heads_up - df.t_floor
    df["lat_dispatch"] = df.t_emergency - df.t_floor
    return df


def confusion(tp, fn, fp, tn):
    n_pos, n_neg = tp + fn, fp + tn
    sens = tp / n_pos if n_pos else np.nan
    spec = tn / n_neg if n_neg else np.nan
    prec = tp / (tp + fp) if (tp + fp) else np.nan
    f1 = 2 * prec * sens / (prec + sens) if (prec + sens) and not np.isnan(prec + sens) else np.nan
    return dict(TP=tp, FN=fn, FP=fp, TN=tn, sensitivity=sens, sens_ci=wilson(tp, n_pos), specificity=spec, spec_ci=wilson(tn, n_neg),
                precision=prec, recall=sens, f1=f1, false_alarm_rate=1 - spec if not np.isnan(spec) else np.nan, fa_ci=wilson(fp, n_neg))


def level_metrics(d, level):
    if level == "alarm":
        pos, pred = d.is_fall, d.alarm
    else:
        pos, pred = d.needs_help, d.dispatch
    tp = int((pos & pred).sum())
    fn = int((pos & ~pred).sum())
    fp = int((~pos & pred).sum())
    tn = int((~pos & ~pred).sum())
    return confusion(tp, fn, fp, tn)


def md(df, floatfmt=".2f"):
    """Markdown table without extra dependencies."""
    def cell(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else format(v, floatfmt)
        return str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(cell(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep] + rows)


def lat_stats(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return dict(n=0)
    return dict(n=len(x), mean=x.mean(), sd=x.std(ddof=1) if len(x) > 1 else np.nan, se=x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan,
                median=np.median(x), p95=np.percentile(x, 95), max=x.max(), min=x.min())


def compare(a, b, paired):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not paired:
        a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    """Welch (or paired) t-test with df, t, exact p, Cohen's d and the 95% CI of the mean difference (a - b)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if paired:
        diff = a - b
        n = len(diff)
        if n < 2:
            return None
        t, p = stats.ttest_rel(a, b)
        se = diff.std(ddof=1) / np.sqrt(n)
        h = stats.t.ppf(0.975, n - 1) * se
        return dict(test="paired t", n=n, df=n - 1, t=t, p=p, d=diff.mean() / diff.std(ddof=1), mean_diff=diff.mean(), ci=(diff.mean() - h, diff.mean() + h))
    if len(a) < 2 or len(b) < 2:
        return None
    t, p = stats.ttest_ind(a, b, equal_var=False)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    md = a.mean() - b.mean()
    h = stats.t.ppf(0.975, df) * np.sqrt(va + vb)
    return dict(test="Welch t", n=(len(a), len(b)), df=df, t=t, p=p, d=md / sp, mean_diff=md, ci=(md - h, md + h))


def mcnemar(r, s):
    """Exact McNemar test on paired detections (r, s boolean arrays)."""
    b = int((r & ~s).sum())
    c = int((~r & s).sum())
    n = b + c
    p = 1.0 if n == 0 else min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5))
    return dict(robot_only=b, static_only=c, both=int((r & s).sum()), neither=int((~r & ~s).sum()), p=p)


def main(split):
    df = derive(load(split))
    out = os.path.join(ROOT, "outputs", "experiments", split, "analysis")
    os.makedirs(os.path.join(out, "tables"), exist_ok=True)
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    M = {}
    lines = [f"# Experiment results: split '{split}'", ""]
    trials = df[df.condition == "robot"]
    lines += [f"{trials.id.nunique()} trials ({int(trials.is_fall.sum())} falls, {int((~trials.is_fall).sum())} daily activities); every trial was run with the "
              f"robot AND with the fixed-camera baseline on the same recorded motion (paired). All numbers are simulation results.", ""]
    # ---- confusion tables -----------------------------------------------------------------------------------
    for level, title in (("alarm", "Alarm level (heads-up sent; positive = any fall)"), ("dispatch", "Dispatch level (family emergency + ambulance; positive = fall with no answer)")):
        lines += [f"## {title}", "", "| condition | TP | FN | FP | TN | sensitivity (95% CI) | specificity (95% CI) | precision | recall | F1 | false-alarm rate |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in CONDS:
            m = level_metrics(df[df.condition == c], level)
            M[f"{level}_{c}"] = m
            lines.append(f"| {c} | {m['TP']} | {m['FN']} | {m['FP']} | {m['TN']} | {m['sensitivity']:.3f} ({m['sens_ci'][0]:.2f}-{m['sens_ci'][1]:.2f}) | "
                         f"{m['specificity']:.3f} ({m['spec_ci'][0]:.2f}-{m['spec_ci'][1]:.2f}) | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['false_alarm_rate']:.3f} |")
        lines.append("")
    # ---- per subtype -------------------------------------------------------------------------------------------
    sub = []
    for (c, st), g in df.groupby(["condition", "subtype"]):
        sub.append(dict(condition=c, subtype=st, n=len(g), alarm=int(g.alarm.sum()), dispatch=int(g.dispatch.sum()),
                        median_lat_alarm=g.lat_alarm.median(), median_lat_dispatch=g.lat_dispatch.median()))
    sub = pd.DataFrame(sub)
    sub.to_csv(os.path.join(out, "tables", "by_subtype.csv"), index=False)
    lines += ["## By event type", "", md(sub, ".1f"), ""]
    if "zone" in df.columns:
        zt = df[df.is_fall].groupby(["condition", "zone"]).agg(n=("id", "count"), alarm=("alarm", "sum"), dispatch=("dispatch", "sum"), median_lat_alarm=("lat_alarm", "median")).reset_index()
        zt.to_csv(os.path.join(out, "tables", "by_zone.csv"), index=False)
        lines += ["## By where she fell", "", md(zt, ".1f"), ""]
    # ---- latency ---------------------------------------------------------------------------------------------------
    lines += ["## Latency from the hip reaching the floor (s), successful detections only", ""]
    lat_rows = []
    for key, col, mask in (("alarm", "lat_alarm", lambda g: g.is_fall & g.alarm), ("dispatch", "lat_dispatch", lambda g: g.needs_help & g.dispatch)):
        for c in CONDS:
            g = df[df.condition == c]
            s = lat_stats(g.loc[mask(g), col])
            lat_rows.append(dict(level=key, condition=c, **s))
            M[f"lat_{key}_{c}"] = s
    lat = pd.DataFrame(lat_rows)
    lat.to_csv(os.path.join(out, "tables", "latency.csv"), index=False)
    lines += [md(lat, ".2f"), ""]
    # ---- paired comparisons ------------------------------------------------------------------------------------
    R = df[df.condition == "robot"].set_index("id")
    for base in ("static4", "static"):
        S = df[df.condition == base].set_index("id").loc[R.index]
        lines += [f"## Robot vs {NAMES[base]}", ""]
        for level, pos_col, pred_col, lat_col in (("alarm", "is_fall", "alarm", "lat_alarm"), ("dispatch", "needs_help", "dispatch", "lat_dispatch")):
            pos = R[pos_col].values
            mc = mcnemar(R[pred_col].values[pos], S[pred_col].values[pos])
            M[f"mcnemar_{level}_{base}"] = mc
            lines.append(f"- **{level} detection** (positives only, n={int(pos.sum())}): robot-only {mc['robot_only']}, {base}-only {mc['static_only']}, both {mc['both']}, neither {mc['neither']}; exact McNemar p = {mc['p']:.4g}")
            both = pos & R[pred_col].values & S[pred_col].values
            if both.sum() >= 2:
                cp = compare(R.loc[both, lat_col].values, S.loc[both, lat_col].values, paired=True)
                M[f"paired_{level}_{base}"] = cp
                lines.append(f"  - latency where BOTH detected (n={cp['n']}): robot minus {base} = {cp['mean_diff']:.2f} s, 95% CI [{cp['ci'][0]:.2f}, {cp['ci'][1]:.2f}], paired t({cp['df']}) = {cp['t']:.2f}, p = {cp['p']:.4g}, Cohen's d = {cp['d']:.2f}")
            ar, as_ = R.loc[pos & R[pred_col].values, lat_col].values, S.loc[pos & S[pred_col].values, lat_col].values
            cp = compare(ar, as_, paired=False)
            if cp:
                M[f"welch_{level}_{base}"] = cp
                lines.append(f"  - latency of all successes (robot n={len(ar)}, {base} n={len(as_)}): difference {cp['mean_diff']:.2f} s, 95% CI [{cp['ci'][0]:.2f}, {cp['ci'][1]:.2f}], Welch t({cp['df']:.1f}) = {cp['t']:.2f}, p = {cp['p']:.4g}, Cohen's d = {cp['d']:.2f}")
        lines.append("")
    # within-window success
    lines += ["### Dispatch within a time window after the fall (positives = fall with no answer)", "", "| window | robot | 1 fixed camera | 4 fixed cameras |", "|---|---|---|---|"]
    D3 = {c: df[df.condition == c].set_index("id").loc[R.index] for c in CONDS}
    pos = R.needs_help.values
    for win in (15, 30, 60, 100):
        row = []
        for c in CONDS:
            ok = (D3[c].lat_dispatch.values <= win) & pos
            k, n = int(ok.sum()), int(pos.sum())
            lo, hi = wilson(k, n)
            row.append(f"{k}/{n} = {k / n:.2f} ({lo:.2f}-{hi:.2f})")
            M[f"within{win}_{c}"] = k / n
        lines.append(f"| {win} s | " + " | ".join(row) + " |")
    lines.append("")
    # by zone
    if "zone" in df.columns:
        pass
    # ---- activities ------------------------------------------------------------------------------------------------
    adl = df[~df.is_fall]
    lines += ["## Daily activities: false alarms (alarm / dispatch)", "", "| activity | n | robot | 1 fixed camera | 4 fixed cameras |", "|---|---|---|---|---|"]
    for st, g in adl[adl.condition == "robot"].groupby("subtype"):
        cells = []
        for c in CONDS:
            h = adl[(adl.condition == c) & (adl.subtype == st)]
            cells.append(f"{int(h.alarm.sum())} / {int(h.dispatch.sum())}")
        lines.append(f"| {st} | {len(g)} | " + " | ".join(cells) + " |")
    lines.append("")
    # ---- robot safety/privacy ----------------------------------------------------------------------------------------
    r = df[df.condition == "robot"]
    safety = dict(max_commanded_speed_mps=float(r.max_cmd_speed_mps.max()), max_true_speed_mps_incl_being_hit=float(r.max_speed_mps.max()),
                  max_collision_force_N_not_human=float(r.max_collision_force_N.max()), max_human_contact_N=float(r.max_human_contact_N.max()),
                  trials_hit_by_her_over_50N=int((r.max_human_contact_N > 50).sum()), trials_pose_error_over_0_5m=int((r.pose_error_final_m > 0.5).sum()),
                  trials_with_contact_over_5N=int((r.max_collision_force_N > 5).sum()), max_tilt_deg=float(r.max_tilt_deg.max()),
                  bytes_before_first_alert_max=int(r.bytes_off_board_before_first_alert.max()), pose_error_final_median_m=float(r.pose_error_final_m.median()),
                  pose_error_final_max_m=float(r.pose_error_final_m.max()))
    M["safety"] = safety
    lines += ["## Robot safety and privacy (all robot trials)", "", "```", json.dumps(safety, indent=1), "```", ""]
    json.dump(M, open(os.path.join(out, "metrics.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    df.to_csv(os.path.join(out, "tables", "all_trials.csv"), index=False)
    open(os.path.join(out, "report.md"), "w").write("\n".join(lines))
    figures(df, out)
    print("\n".join(lines))


def figures(df, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = dict(robot="#2a7ab0", static="#c0602a", static4="#7a9a3a")
    R = df[df.condition == "robot"].set_index("id")
    D = {c: df[df.condition == c].set_index("id").loc[R.index] for c in CONDS}
    pos = R.needs_help.values
    n = int(pos.sum())
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    for c in CONDS:
        x = np.sort(D[c].loc[pos, "lat_dispatch"].dropna().values)
        ax.step(np.r_[0, x, 110], np.r_[0, np.arange(1, len(x) + 1) / max(n, 1), len(x) / max(n, 1)], where="post", color=col[c], label=NAMES[c])
    ax.axvline(60, ls=":", color="gray")
    ax.set_xlabel("time from fall to dispatch (s)")
    ax.set_ylabel("fraction of silent falls dispatched", fontsize=8)
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 1.02)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "dispatch_latency_cdf.png"), dpi=200)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    types = ["trip", "slip", "syncope", "cardiac"]
    w = 0.27
    for k, c in enumerate(CONDS):
        v, lo, hi = [], [], []
        for t in types:
            g = D[c][D[c].subtype == t]
            kk, nn = int(g.alarm.sum()), len(g)
            p = kk / nn if nn else 0
            a, b = wilson(kk, nn)
            v.append(p)
            lo.append(p - a)
            hi.append(b - p)
        ax.bar(np.arange(len(types)) + (k - 1) * w, v, w, yerr=[lo, hi], color=col[c], label=NAMES[c], capsize=2)
    ax.set_xticks(range(len(types)))
    ax.set_xticklabels(types)
    ax.set_ylabel("fraction detected (alarm level)")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "detection_by_type.png"), dpi=200)
    plt.close(fig)
    adl = df[~df.is_fall]
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    acts = sorted(adl.subtype.unique())
    for k, c in enumerate(CONDS):
        g = adl[adl.condition == c]
        ax.bar(np.arange(len(acts)) + (k - 1) * w, [g[g.subtype == a].alarm.mean() for a in acts], w, color=col[c], label=NAMES[c])
    ax.set_xticks(range(len(acts)))
    ax.set_xticklabels([a.replace("_", "\n") for a in acts], fontsize=6)
    ax.set_ylabel("false-alarm rate (alarm level)")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "false_alarms_by_activity.png"), dpi=200)
    plt.close(fig)
    if "zone" in df.columns:
        fig, ax = plt.subplots(figsize=(4.4, 3.0))
        zones = ["living", "hallway", "bedroom"]
        for k, c in enumerate(CONDS):
            g = D[c][D[c].is_fall]
            ax.bar(np.arange(3) + (k - 1) * w, [g[g.zone == z].alarm.mean() if (g.zone == z).any() else 0 for z in zones], w, color=col[c], label=NAMES[c])
        ax.set_xticks(range(3))
        ax.set_xticklabels(zones)
        ax.set_ylabel("fraction of falls detected")
        ax.legend(frameon=False, fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "figures", "detection_by_zone.png"), dpi=200)
        plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
