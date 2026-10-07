"""Enumerate every solution of the time-collapsed problem up to weight K,
one representative per translation orbit.

Complete for K <= d_collapsed + 3 (see cdist.lift.enumerate_solutions): the
search is run without pair exclusions, and solutions that contain a proper
zero-syndrome subset (minimum solution + disjoint trivial triple) are added.

Usage: python scripts/enum_collapsed.py circuits/bb288_r18_X.stim results/enum_bb288_r18_X.json K [k_table] [cover: 0 | 1]
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import lift, problem, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def group_maps(sym, ncols):
    """All translations as column maps (closure of the generators)."""
    gens = [np.array(cm, dtype=np.int32) for cm in sym["colmaps"]]
    ident = np.arange(ncols, dtype=np.int32)
    seen = {ident.tobytes(): ident}
    frontier = [ident]
    while frontier:
        g = frontier.pop()
        for h in gens:
            n = h[g]
            key = n.tobytes()
            if key not in seen:
                seen[key] = n
                frontier.append(n)
    return list(seen.values())


def canonical(sols, maps):
    """Lexicographically smallest translate of each solution (rows of equal length)."""
    best = None
    for g in maps:
        m = np.sort(g[sols], axis=1)
        if best is None:
            best = m
        else:
            diff = m != best
            first = diff.argmax(axis=1)
            rows = np.arange(len(m))
            less = diff.any(axis=1) & (m[rows, first] < best[rows, first])
            best[less] = m[less]
    return best


def main(path, out, K, k_table=3, cover=0):
    K, k_table, cover = int(K), int(k_table), bool(int(cover))
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    c = problem.collapse_time(sector)
    sym = symmetry.translations(c)
    maps = group_maps(sym, c.ncols)
    log(f"collapsed {c.nrows}x{c.ncols}, |G|={len(maps)}")
    sols, st = lift.enumerate_solutions(c, K, k_table=k_table, rank=sym["rank"], anchors=sym["anchors"],
                                        colmaps=sym["colmaps"], sol_cap=20_000_000, cover=cover)
    log(f"K={K}: {len(sols)} solutions; search nodes={st['nodes']} ({st['seconds']:.1f}s); "
        f"decomposable added={st['decomposable_added']}")
    res = {"circuit": path, "K": K, "group_order": len(maps), "collapsed_distance": st.get("distance"),
           "stats": st, "weights": {}, "representatives": {}}
    by_w = {}
    for s in sols:
        by_w.setdefault(len(s), []).append(s)
    for w in sorted(by_w):
        arr = np.array(by_w[w], dtype=np.int32)
        can = np.unique(canonical(arr, maps), axis=0)
        res["weights"][w] = {"orbits": len(can), "solutions": len(by_w[w])}
        res["representatives"][str(w)] = [[int(x) for x in row] for row in can]
        log(f"weight {w}: {len(by_w[w])} solutions in {len(can)} orbits")
    json.dump(res, open(out, "w"))
    log("saved", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
