"""Consistency check of the search machinery on the collapsed problem:
the same thresholds searched (a) with translation anchoring + pair exclusions
and (b) plainly (every column an anchor, no exclusions, different table size).
Both must agree on "no solution up to K" and on the number of minimum solutions.

Usage: python scripts/crosscheck_plain.py circuits/bb288_r18_X.stim results/crosscheck_bb288_r18_X.json K
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import lift, problem, search, symmetry


def main(path, out, K):
    K = int(K)
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    c = problem.collapse_time(sector)
    sym = symmetry.translations(c)
    t = time.time()
    a = search.distance(c, k_table=3, kmax=K, rank=sym["rank"], anchors=sym["anchors"], enum_all=True, exclusions=True)
    ta = time.time() - t
    t = time.time()
    b = search.distance(c, k_table=2, kmax=K, enum_all=True, exclusions=False)
    tb = time.time() - t
    sa = lift.expand_orbits(a["solutions"], sym["colmaps"])
    sb = set(b["solutions"])
    res = {"circuit": path, "K": K,
           "anchored": {"distance": a["distance"], "lower_bound": a["lower_bound"], "solutions": len(sa),
                        "nodes": [sum(x["nodes"]) for x in a["runs"]], "seconds": round(ta, 1)},
           "plain": {"distance": b["distance"], "lower_bound": b["lower_bound"], "solutions": len(sb),
                     "nodes": [sum(x["nodes"]) for x in b["runs"]], "seconds": round(tb, 1)},
           "agree": a["distance"] == b["distance"] and a["lower_bound"] == b["lower_bound"] and sa == sb}
    print(json.dumps({k: (v if k != "anchored" and k != "plain" else {kk: vv for kk, vv in v.items() if kk != "nodes"})
                      for k, v in res.items()}), flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
