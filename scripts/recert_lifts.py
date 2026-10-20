"""Repeat, with the current kernel, the slack-0 orbit lifts behind a lower bound d_coll + 1 of scripts/run_deep.py.

The record of run_deep.py stores one representative per translation orbit of the minimum solutions of the
time-collapsed problem (`collapsed.lifts[].classes`, collapsed column indices).  This script rebuilds the sector
and collapsed problems of the circuit and checks that
  - the sector reduction is exact and the sector problem has the translations of the collapsed one, so lifting
    one representative per orbit is enough;
  - every stored representative is a minimum solution of the rebuilt collapsed problem, and the orbits of the
    representatives contain exactly the `n_min_solutions` minimum solutions of the record.
It then searches the sector columns of each representative's classes up to weight d_coll.  If none of them holds
a solution, the circuit distance is at least d_coll + 1 (the one-step lifting rule of the paper, Sec. 5.4).

usage: python scripts/recert_lifts.py circuit.stim run_deep_record.json out.json
"""
import hashlib
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from cdist import lift, problem, search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def kernel_sha256():
    with open(os.path.join(ROOT, "cdist", "gmitm.c"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(path, rec_path, out):
    t0 = time.time()
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector)
    collapsed = problem.collapse_time(sector)
    s_sec, s_col = symmetry.translations(sector), symmetry.translations(collapsed)
    assert s_sec["ok"] and s_col["ok"] and s_sec["generators"] == s_col["generators"], \
        "sector problem lacks the translation symmetry of the collapsed one"
    rec = json.load(open(rec_path))["collapsed"]
    d_coll = rec["distance"]
    reps = [tuple(sorted(x["classes"])) for x in rec["lifts"]]
    for cl in reps:
        assert len(cl) == d_coll and search.verify(collapsed, cl), "a stored representative is not a minimum solution"
    allsol = lift.expand_orbits(reps, s_col["colmaps"])
    assert len(allsol) == rec["n_min_solutions"], (len(allsol), rec["n_min_solutions"])
    log(f"{path}: sector {sector.nrows}x{sector.ncols}, collapsed {collapsed.nrows}x{collapsed.ncols}, "
        f"d_coll {d_coll}, {len(reps)} orbits, {len(allsol)} minimum solutions")
    res = {"circuit": path, "record": rec_path, "kernel_sha256": kernel_sha256(),
           "threads": search.lib().gm_num_threads(), "d_collapsed": d_coll, "orbits": len(reps),
           "min_solutions": len(allsol), "lifts": []}
    found = None
    for i, cl in enumerate(reps):
        t = time.time()
        cols = sorted({j for c in cl for j in collapsed.col_meta[c]})
        sub = problem.Problem("lift", sector.nrows, sector.nobs, [sector.h[j] for j in cols],
                              [sector.l[j] for j in cols], sector.row_meta)
        r = search.distance(sub, k_table=2, kmax=d_coll, exclusions=False)
        assert all(x["status"] in ("exhausted", "found") for x in r["runs"]), [x["status"] for x in r["runs"]]
        res["lifts"].append({"classes": list(cl), "columns": len(cols), "distance": r["distance"],
                             "lower_bound": r["lower_bound"],
                             "false_hits": sum(x["false_hits"] for x in r["runs"]),
                             "nodes": sum(sum(x["nodes"]) for x in r["runs"]), "seconds": round(time.time() - t, 2)})
        log(f"  orbit {i + 1}/{len(reps)}: {len(cols)} columns, distance {r['distance']}, "
            f"lower bound {r['lower_bound']}, {time.time() - t:.1f}s")
        if r["distance"] is not None and found is None:
            found = [cols[j] for j in r["solutions"][0]]
            assert search.verify(sector, found)
    if found is None:
        res["certified_lower_bound"] = d_coll + 1
        log(f"no representative lifts: circuit distance >= {d_coll + 1}")
    else:
        res["lifted_solution"] = found
        log(f"a representative lifts: circuit distance = {d_coll}")
    res["seconds"] = round(time.time() - t0, 1)
    with open(out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
