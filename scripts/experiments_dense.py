"""Dense (width-limited) experiments: Rank DP vs tensor network, exact vs approximate.

  A. widths: cut rank of the linear Rank DP vs TN widths for the same problem
  B. dense min-plus Rank DP (Viterbi over the syndrome trellis): exact distances
  C. tropical tensor-network contraction of the same instance (cross-check)
  D. ordinary sum-product DP at small fault weight x: exponent = distance,
     prefactor = number of minimum-weight logical faults
  E. width-truncated Rank DP (drop trellis rows until the cut rank fits):
     a certified but weak lower bound

Usage: python scripts/experiments_dense.py results/dense.json [code ...]
"""
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import kernel, ordering, problem, search, tn, trellis


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def best_order(p, tries=8):
    best = None
    for s in range(tries):
        o = ordering.greedy_order(p.h, p.nrows, seed=s, noise=0.5 if s else 0.0)
        cost = ordering.profile_cost(trellis.cut_profile(p.h, o))
        if best is None or cost < best[0]:
            best = (cost, o)
    return best[1], best[0]


def sumproduct(plan, x):
    """Same sweep with ordinary (+, *) arithmetic: Z(x) = sum over undetected
    logical fault sets e of x^|e|."""
    T = np.ones(1, dtype=np.float64)
    for op in plan.ops:
        if op[0] == "expand":
            T = np.concatenate([T, np.zeros(T.size)])
        elif op[0] == "update":
            T = T + x * T[np.arange(T.size, dtype=np.int64) ^ op[1]]
        else:
            idx = np.arange(T.size, dtype=np.int64)
            T = T[((idx >> op[1]) & 1) == op[2]]
    return float(T[0])


def truncated_plan(p, obs_mask, order, wmax):
    """Drop trellis rows (in minimal span form) until at most wmax constraint
    rows are active at any cut.  Fewer constraints = a relaxation."""
    hrows = trellis.minimal_span_form(trellis.rows_from_columns(p.h, order, p.nrows))
    n = len(order)
    rows = list(hrows)
    dropped = 0
    while True:
        act = [0] * (n + 1)
        for r in rows:
            for i in range(trellis.lowbit(r), r.bit_length() - 1):
                act[i] += 1
        peak = max(act)
        if peak <= wmax:
            break
        cut = act.index(peak)
        live = [r for r in rows if trellis.lowbit(r) <= cut < r.bit_length() - 1]
        victim = max(live, key=lambda r: r.bit_length() - trellis.lowbit(r))
        rows.remove(victim)
        dropped += 1
    lrow = 0
    for pos, j in enumerate(order):
        if bin(p.l[j] & obs_mask).count("1") & 1:
            lrow |= 1 << pos
    lrow = trellis.reduce_target_row(lrow, hrows)
    return trellis.make_plan(rows, lrow, n), dropped, len(hrows)


def run(code, res):
    path = f"circuits/{code}.stim"
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    collapsed = problem.collapse_time(sector)
    capacity = problem.window_problem(sector, 0, 0)
    out = {}
    for label, p in (("code_capacity", capacity), ("collapsed_circuit", collapsed)):
        order, cost = best_order(p)
        tnw = max(ordering.tn_sweep_width(p.h, order, p.nrows))
        _, tw = tn.greedy_elimination(tn.tanner_graph(p.h, p.nrows), "min_fill")
        _, twd = tn.greedy_elimination(tn.row_graph(p.h, p.nrows), "min_fill")
        rec = {"columns": p.ncols, "rank": trellis.rank_profile(p.h, range(p.ncols))[-1],
               "rankdp_cut_rank": cost[0], "rankdp_log2_volume": round(cost[1], 2),
               "tn_sweep_width_original_checks": tnw, "tn_tanner_treewidth_minfill": tw,
               "tn_detector_graph_treewidth_minfill": twd}
        log(code, label, rec)
        # B. dense min-plus Rank DP
        if cost[0] <= 28:
            t = time.time()
            ds = []
            peak = 0
            for i in range(p.nobs):
                plan = trellis.build_plan(p.h, p.l, 1 << i, order, p.nrows)
                d, st = kernel.run_plan(plan)
                ds.append(d)
                peak = max(peak, plan.peak_bits)
            rec["dense_rankdp"] = {"per_observable": ds, "distance": min(x for x in ds if x is not None),
                                   "peak_table_bits": peak, "seconds": round(time.time() - t, 2)}
            log(code, label, "dense Rank DP", rec["dense_rankdp"])
        if cost[0] > 28:
            # too wide for a dense table here: widths only
            out[label] = rec
            continue
        # reference by the sparse search (all minimum solutions)
        r = search.distance(p, k_table=2, enum_all=True)
        rec["search_distance"] = r["distance"]
        mult = [sum(1 for s in r["solutions"] if (problem.Problem.check(p, s)[1] >> i) & 1) for i in range(p.nobs)]
        rec["min_weight_solutions"] = len(r["solutions"])
        # C. tropical TN contraction (one observable), if it fits
        t = time.time()
        val, peak = tn.tropical_contract(p.h, p.l, 1, p.nrows, max_rank=28, col_order=order)
        rec["tropical_tn"] = {"observable_0": val, "largest_tensor_rank": peak, "seconds": round(time.time() - t, 2)}
        log(code, label, "tropical TN (direct picture, same sweep order)", rec["tropical_tn"])
        # D. sum-product at small x
        if cost[0] <= 20:
            t = time.time()
            x1, x2 = 1e-3, 1e-4
            sp = []
            for i in range(p.nobs):
                plan = trellis.build_plan(p.h, p.l, 1 << i, order, p.nrows)
                z1, z2 = sumproduct(plan, x1), sumproduct(plan, x2)
                dexp = math.log(z1 / z2) / math.log(x1 / x2)
                d = round(dexp)
                sp.append({"exponent": round(dexp, 4), "distance": d, "multiplicity": round(z2 / x2 ** d, 3),
                           "multiplicity_by_enumeration": mult[i] if d == r["distance"] else None})
            rec["sum_product_small_x"] = {"x": [x1, x2], "per_observable": sp, "seconds": round(time.time() - t, 2)}
            log(code, label, "sum-product", sp[:3], "...")
        # E. width-truncated Rank DP
        if cost[0] <= 28:
            tr = []
            for wmax in (4, 8, 12, 16, 20, 24):
                if wmax >= cost[0]:
                    continue
                ds = []
                drop = tot = 0
                for i in range(p.nobs):
                    plan, drop, tot = truncated_plan(p, 1 << i, order, wmax)
                    d, _ = kernel.run_plan(plan)
                    ds.append(d)
                tr.append({"max_cut_rank": wmax, "rows_dropped": drop, "rows_total": tot,
                           "lower_bound": min(x for x in ds if x is not None)})
            rec["truncated_rankdp"] = tr
            log(code, label, "truncated Rank DP", tr)
        out[label] = rec
    res[code] = out


def main(out, *codes):
    codes = codes or ["bb72_r6_Z", "bb72_r6_X", "bb90_r10_Z", "bb108_r10_Z", "bb144_r12_Z", "bb288_r18_Z"]
    res = json.load(open(out)) if os.path.exists(out) else {}
    for c in codes:
        run(c, res)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
