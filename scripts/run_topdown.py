"""Decide whether the real circuit has an undetected logical fault set of
weight <= W, organised by the solutions of the time-collapsed relaxation.

Input: the complete list of collapsed solutions up to weight W (one per
translation orbit) from scripts/enum_collapsed.py.  For each solution O the real
(sector) problem is searched with the budget "one column from each class of
O, plus W - |O| further columns".  If no search succeeds, W + 1 is a
certified lower bound on the circuit distance.

Usage: python scripts/run_topdown.py circuits/bb288_r18_X.stim results/enum_bb288_r18_X.json 15 results/topdown_bb288_r18_X.json
"""
import json
import os
import sys
import time

import stim

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import lift, problem, replay, search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(path, enum_path, W, out):
    W = int(W)
    t0 = time.time()
    circ = stim.Circuit.from_file(path)
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector)
    collapsed = problem.collapse_time(sector)
    # lifting one representative per translation orbit is enough only if the
    # real problem has the same translations
    s_sec = symmetry.translations(sector)
    s_col = symmetry.translations(collapsed)
    assert s_sec["ok"] and s_col["ok"] and s_sec["generators"] == s_col["generators"], \
        "sector problem lacks the translation symmetry of the collapsed one"
    enum = json.load(open(enum_path))
    assert enum["K"] >= W, "enumeration does not reach W"
    td = lift.TopDown(sector, collapsed, k_main=2)
    log(f"sector {sector.nrows}x{sector.ncols}; main table {td.table.entries} entries ({td.table.build_seconds:.1f}s)")
    res = {"circuit": path, "W": W, "enumeration": enum_path, "by_weight": {}, "found": None}
    found = None
    for w in sorted(int(x) for x in enum["representatives"]):
        if w > W:
            continue
        reps = enum["representatives"][str(w)]
        slack = W - w
        t = time.time()
        nodes = 0
        nfound = 0
        worst = 0.0
        for i, O in enumerate(reps):
            t1 = time.time()
            r = td.lift(O, slack)
            assert r["status"] in ("exhausted", "found"), r["status"]
            nodes += sum(r["nodes"])
            worst = max(worst, time.time() - t1)
            if r["best"] is not None:
                nfound += 1
                if found is None or r["best"] < found[0]:
                    found = (r["best"], r["solutions"][0], O, slack)
            if (i + 1) % 500 == 0:
                log(f"  weight {w}: {i + 1}/{len(reps)} orbits, {nfound} lift, {time.time() - t:.0f}s")
        res["by_weight"][w] = {"orbits": len(reps), "slack": slack, "lifting_orbits": nfound, "nodes": nodes,
                               "seconds": round(time.time() - t, 1), "slowest_single_search": round(worst, 2)}
        log(f"collapsed weight {w} (slack {slack}): {len(reps)} orbits, {nfound} lift to weight <= {W}; "
            f"nodes={nodes} {time.time() - t:.1f}s")
    if found is None:
        res["certified_lower_bound"] = W + 1
        log(f"no real solution of weight <= {W}: certified lower bound {W + 1}")
    else:
        wt, sol, O, slack = found
        raw = replay.lift_to_dem(full, sector, sol)
        dets, obs, terms = replay.check_in_dem(circ, raw)
        faults = replay.physical_faults(circ, raw)
        d2, o2 = replay.replay(circ, faults)
        ok = (not dets) and bool(obs) and (not d2) and (o2 == obs)
        res["found"] = {"weight": wt, "collapsed_solution": O, "slack": slack, "dem_error_indices": raw,
                        "dem_check": {"detectors": dets, "observables": obs},
                        "replay": {"fired_detectors": d2, "flipped_observables": o2}, "verified": ok}
        log(f"real solution of weight {wt} found (verified={ok})")
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
