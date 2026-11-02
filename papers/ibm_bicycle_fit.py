"""The published extrapolation of Tour de gross (arXiv:2506.03094, App. A.7), compared with the decoder-independent
bounds of papers/ibm_bicycle_matched_bound.py.

The paper's rates come from the failure spectrum f(w), the fraction of configurations of w faults that fail, through
its eq. 87, P(q) = sum_{w >= w0} f(w) binom(N, w) q^w (1 - q)^(N - w) with q = p/15, and the two-parameter ansatz of its
eq. 88, f(w) = a [1 - exp(-(f0/a) (w/w0)^gamma)], a = 1 - 2^-K, w0 = ceil(d*/2).  From the parameters of its Table 6 this
script

  1. reproduces the idle and automorphism entries of its Table 2;
  2. reports which fault weights carry the two-gross idle rate, and what lowering the cut at w0 does to it;
  3. writes that curve for Fig. 4d and, given bound records, the bounds per cycle summed over the two memory bases and
     where they cross the curve.

Usage: python papers/ibm_bicycle_fit.py OUT.json [BOUND.json ...]
       (BOUND.json: output of papers/ibm_bicycle_code_logicals.py for the two-gross code, a dense grid of p, both bases)
"""
import json
import math
import os
import sys

# Tour de gross, Table 6: (ln f0, gamma, w0, K, N); Table 2: {p: (log10 rate, uncertainty)}
SERIES = {
    "gross idle": ((-31.02, 8.66, 5, 24, 210960), {1e-3: (-8.8, 0.2), 1e-4: (-14.8, 0.4)}),
    "gross automorphism": ((-28.63, 7.13, 5, 24, 483840), {1e-3: (-6.4, 0.2), 1e-4: (-12.2, 0.5)}),
    "two-gross idle": ((-95.83, 25.78, 9, 24, 762912), {1e-3: (-20.1, 0.5), 1e-4: (-38.3, 0.9)}),
    "two-gross automorphism": ((-108.53, 28.22, 9, 24, 1748736), {1e-3: (-14.5, 0.4), 1e-4: (-37.0, 1.0)}),
}
LOG10 = math.log(10)


def log_f(w, lnf0, gamma, w0, K):
    """log of the ansatz at weight w; its value does not depend on w0 once f0 is fitted, only the cut does."""
    a = 1 - 2.0 ** -K
    y = lnf0 + gamma * math.log(w / w0) - math.log(a)
    if y < -30:
        return math.log(a) + y                                # 1 - exp(-x) = x
    return math.log(a) + (math.log(-math.expm1(-math.exp(y))) if y < 5 else 0.0)


def terms(p, params, wmin=None):
    """[(log of the term of eq. 87, w)] for w >= wmin (default: the published cut w0)."""
    lnf0, gamma, w0, K, N = params
    q = p / 15
    wmax = min(N, int(N * q + 40 * math.sqrt(N * q + 1) + 600))
    out = []
    for w in range(w0 if wmin is None else wmin, wmax + 1):
        c = math.lgamma(N + 1) - math.lgamma(w + 1) - math.lgamma(N - w + 1)
        out.append((log_f(w, lnf0, gamma, w0, K) + c + w * math.log(q) + (N - w) * math.log1p(-q), w))
    return out


def log10_rate(p, params, wmin=None):
    ts = [t for t, _ in terms(p, params, wmin)]
    m = max(ts)
    return (m + math.log(sum(math.exp(t - m) for t in ts))) / LOG10


def carriers(p, params):
    """The weight with the largest term, the narrowest range of weights holding 90% of the sum, the share of w0."""
    ts = terms(p, params)
    m = max(t for t, _ in ts)
    tot = sum(math.exp(t - m) for t, _ in ts)
    held, ws = 0.0, []
    for t, w in sorted(ts, reverse=True):
        held += math.exp(t - m) / tot
        ws.append(w)
        if held > 0.9:
            break
    lead = max(ts)[1]
    return {"lead_weight": lead, "range_90_percent": [min(ws), max(ws)], "share_of_lowest_weight": math.exp(ts[0][0] - m) / tot}


def crossing(ps, bound, params):
    """The largest p at which the bound falls below the curve when p rises, by log-log interpolation."""
    diff = [b - log10_rate(p, params) for p, b in zip(ps, bound)]
    for k in range(len(ps) - 1):
        if diff[k] > 0 >= diff[k + 1]:
            lo, hi = math.log10(ps[k]), math.log10(ps[k + 1])
            return 10 ** (lo + (hi - lo) * diff[k] / (diff[k] - diff[k + 1]))
    return None


def main(out, bound_files):
    res = {"source": "Tour de gross (arXiv:2506.03094), eqs. 87-88, Tables 2 and 6", "reproduced": {}}
    for name, (params, table2) in SERIES.items():
        res["reproduced"][name] = {str(p): {"log10_sum": log10_rate(p, params), "table_2": v[0], "uncertainty": v[1]}
                                   for p, v in table2.items()}
        print(name, {p: round(v["log10_sum"], 2) for p, v in res["reproduced"][name].items()},
              "Table 2:", {p: v[0] for p, v in table2.items()})
    params = SERIES["two-gross idle"][0]
    idle = {"weights": {str(p): dict(carriers(p, params), log10_sum=log10_rate(p, params),
                                     log10_sum_cut_at_8=log10_rate(p, params, 8),
                                     log10_sum_cut_at_1=log10_rate(p, params, 1))
                        for p in (1e-4, 7.322e-4, 1e-3)},
            "log10_f": {str(w): log_f(w, *params[:4]) / LOG10 for w in (8, 9, 19, 72, 250)},
            "drop_between_table_2_points": log10_rate(1e-3, params) - log10_rate(1e-4, params)}
    p = 1e-4
    while carriers(p, params)["lead_weight"] > params[2]:
        p *= 0.98
    idle["lowest_weight_leads_below_p"] = p
    res["two_gross_idle"] = idle
    grid = [10 ** (-5 + k * 0.025) for k in range(101)]
    res["curve"] = {"p": grid, "log10_rate": [log10_rate(x, params) for x in grid]}
    groups = {}
    for f in bound_files:
        rec = json.load(open(f))
        groups.setdefault(rec["distance"], []).append(rec)
    res["bounds"] = {}
    for w, recs in sorted(groups.items()):
        assert sorted(r["basis"] for r in recs) == ["X", "Z"], "a bound for each memory basis"
        rates = [r["C%d" % r["cycles"]]["rates"] for r in recs]
        ps = sorted(rates[0], key=float)
        fp = [float(x) for x in ps]
        total = [math.log10(sum(10 ** r[x]["log10_lower_bound_per_cycle"] for r in rates)) for x in ps]
        res["bounds"][str(w)] = {
            "weight": w, "p": fp, "log10_per_cycle_two_bases": total,
            "per_basis": {r["basis"]: [q[x]["log10_lower_bound_per_cycle"] for x in ps] for r, q in zip(recs, rates)},
            "n_fault_sets": {r["basis"]: r["sets"]["n_fault_sets"] for r in recs},
            "n_pairs_per_cycle": {r["basis"]: r["C%d" % r["cycles"]]["n_pairs_per_cycle"] for r in recs},
            "crosses_the_curve_at_p": crossing(fp, total, params),
            "orders_above_curve": {x: t - log10_rate(float(x), params) for x, t in zip(ps, total)}}
        print("weight", w, "crosses the curve at", res["bounds"][str(w)]["crosses_the_curve_at_p"],
              {x: round(t, 2) for x, t in zip(ps, total)})
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    print("two-gross idle:", json.dumps(idle, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
