"""Dense min-plus Rank DP at the memory limit: one 2^w-entry table of byte
costs, swept over the columns in a low-cut-rank order (C kernel, OpenMP).

Usage: python scripts/run_dense_big.py circuits/bb144_r12_Z.stim capacity results/dense_big_bb144_Z.json [max_bits] [obs,obs,...]
       (problem = capacity | collapsed; the optional last argument restricts the observables)
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import kernel, ordering, problem, trellis


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(path, which, out, max_bits=38, only=None):
    max_bits = int(max_bits)
    only = None if only is None else {int(x) for x in str(only).split(",")}
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    p = problem.window_problem(sector, 0, 0) if which == "capacity" else problem.collapse_time(sector)
    best = None
    for s in range(24):
        o = ordering.greedy_order(p.h, p.nrows, seed=s, noise=0.5 if s else 0.0)
        cost = ordering.profile_cost(trellis.cut_profile(p.h, o))
        if best is None or cost < best[0]:
            best = (cost, o)
    order, cost = ordering.improve(p.h, best[1], iters=3000, seed=1)
    log(f"{path} {which}: {p.ncols} columns, cut rank {cost[0]} (log2 volume {cost[1]:.1f})")
    res = {"circuit": path, "problem": which, "columns": p.ncols, "cut_rank": cost[0],
           "threads": kernel.lib().dp_num_threads(), "per_observable": []}
    for i in range(p.nobs):
        if only is not None and i not in only:
            continue
        plan = trellis.build_plan(p.h, p.l, 1 << i, order, p.nrows)
        if plan.peak_bits > max_bits:
            log(f"observable {i}: table of 2^{plan.peak_bits} bytes exceeds the limit 2^{max_bits}")
            res["per_observable"].append({"observable": i, "peak_bits": plan.peak_bits, "distance": "skipped"})
            continue
        d, st = kernel.run_plan(plan, log=log, progress_every=120.0)
        res["per_observable"].append({"observable": i, "peak_bits": plan.peak_bits, "distance": d,
                                      "seconds": round(st["seconds"], 1)})
        log(f"observable {i}: distance {d}, table 2^{plan.peak_bits} bytes, {st['seconds']:.1f}s")
        json.dump(res, open(out, "w"), indent=1)
    ds = [x["distance"] for x in res["per_observable"] if isinstance(x["distance"], int)]
    res["distance"] = min(ds) if len(ds) == p.nobs else None
    res["observables_run"] = sorted(x["observable"] for x in res["per_observable"])
    json.dump(res, open(out, "w"), indent=1)
    log("done", res["distance"])


if __name__ == "__main__":
    main(*sys.argv[1:])
