"""Cost pilot for a circuit: problem sizes, symmetry, and search growth per
threshold on (a) single-layer windows and (b) the collapsed relaxation, each
stopped at the first threshold exceeding the time limit.

Usage: python scripts/pilot.py circuit.stim out.json [seconds_per_threshold]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import problem, search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def probe(p, label, tl, k_table=3, kmax=40):
    sym = symmetry.translations(p)
    kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") and sym["generators"] else {}
    deg = sum(bin(a).count("1") for a in p.h)
    used = 0
    for a in p.h:
        used |= a
    nrow = bin(used).count("1")
    r = search.distance(p, k_table=k_table, kmax=kmax, time_limit=tl, **kw)
    runs = [{"K": x["K"], "status": x["status"], "nodes": sum(x["nodes"]), "seconds": round(x["seconds"], 2)} for x in r["runs"]]
    out = {"columns": p.ncols, "rows_used": nrow, "mean_row_degree": round(deg / max(nrow, 1), 1),
           "max_column_weight": max(bin(a).count("1") for a in p.h),
           "symmetry": sym.get("generators") if sym.get("ok") else None,
           "orbits": len(sym["anchors"]) if sym.get("ok") else None,
           "distance": r["distance"], "lower_bound": r["lower_bound"], "runs": runs}
    big = [x for x in runs if x["nodes"] > 1e5 and x["status"] == "exhausted"]
    if len(big) >= 2:
        out["growth_per_threshold"] = round((big[-1]["nodes"] / big[0]["nodes"]) ** (1 / (big[-1]["K"] - big[0]["K"])), 2)
    log(label, {k: v for k, v in out.items() if k != "runs"}, "last", runs[-2:])
    return out


def main(path, out, tl=60):
    tl = float(tl)
    t0 = time.time()
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    exact = problem.sector_is_exact(full, sector)
    collapsed = problem.collapse_time(sector)
    res = {"circuit": path, "threads": search.lib().gm_num_threads(),
           "full": [full.nrows, full.ncols], "sector": [sector.nrows, sector.ncols], "sector_exact": exact,
           "collapsed": [collapsed.nrows, collapsed.ncols], "load_seconds": round(time.time() - t0, 1)}
    log(res)
    res["window_t0"] = probe(problem.window_problem(sector, 0, 0), "window t=0", tl)
    json.dump(res, open(out, "w"), indent=1)
    res["window_t1"] = probe(problem.window_problem(sector, 1, 1), "window t=1", tl)
    json.dump(res, open(out, "w"), indent=1)
    res["collapsed_search"] = probe(collapsed, "collapsed", tl)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
