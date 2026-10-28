"""All undetectable logical fault sets of weight at most KMAX of a memory instruction of papers/ibm_bicycle.py (one
set per symmetry orbit from the enumeration of the search, then expanded), with their numbers by weight, for the
low-weight failures of a minimum-weight decoder (papers/ibm_bicycle_mwd.py).

Usage: OMP_NUM_THREADS=32 python papers/ibm_bicycle_spectrum.py KEY BASIS CYCLES KMAX OUT.json SECONDS [k_table]
       (schedule from IBM_SCHEDULE, as in papers/ibm_bicycle.py; OUT.json gets the sets as sector columns)
"""
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import ibm_bicycle as IB
import run_parallel as RP
from cdist import lift, problem, search


def main(key, basis, cycles, kmax, out, seconds, k_table=3):
    cycles, kmax, seconds, k_table = int(cycles), int(kmax), float(seconds), int(k_table)
    sched, stag = IB.schedule_from_env()
    t0 = time.time()
    circ = IB.build_instruction(key, basis, cycles, 1e-3, sched)
    path = os.path.join(ROOT, "circuits", "papers", f"ibm_{key}_{stag}_c{cycles}_{basis}_{os.getpid()}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path, os.path.basename(path))
    os.remove(path)
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector), "sector reduction not exact"
    sym, kw = RP.sym_of(sector, IB.translations(key))
    colmaps = sym.get("colmaps", []) if sym.get("ok") else []
    S = search.Searcher(sector, labelfree=True, **kw)
    table = search.Table(sector, k_table, labelfree=True)
    S.add_table(table, exact=True)
    # no dominance exclusions: they keep every set of minimum weight but may drop heavier ones
    r = S.search(kmax, enum_all=True, time_limit=seconds, sol_cap=20_000_000, exclusions=False)
    table.free()
    assert r["nsol_recorded"] < 20_000_000, "solution cap reached"
    reps = sorted({tuple(sorted(s)) for s in r["solutions"]})
    sols = sorted(lift.expand_orbits(reps, colmaps)) if colmaps else reps
    assert all(search.verify(sector, s) for s in sols)
    res = {"code": key, "schedule": stag, "basis": basis, "cycles": cycles, "kmax": kmax, "status": r["status"],
           "complete": r["status"] == "exhausted", "n_orbit_representatives": len(reps),
           "by_weight": dict(sorted(Counter(len(s) for s in sols).items())),
           "threads": r["threads"], "search_seconds": round(r["seconds"], 1), "seconds": round(time.time() - t0, 1),
           "sets": [list(s) for s in sols]}
    json.dump(res, open(out, "w"))
    print(f"{key} {stag} {basis}: status {r['status']}, {len(reps)} representatives, by weight {res['by_weight']}, "
          f"{res['seconds']} s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
