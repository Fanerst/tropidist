"""Minimum fault sets of a memory instruction of papers/ibm_bicycle.py found by a time-limited enumeration at its
certified distance (one set per symmetry orbit, as sector columns), for the lower bounds of
papers/ibm_bicycle_bound.py when the complete enumeration is too long (the two-gross code).  A bound summed over the
sets found, with their orbits, is valid; it only grows with more sets.

Usage: OMP_NUM_THREADS=32 python papers/ibm_bicycle_enum.py KEY BASIS CYCLES DISTANCE OUT.json SECONDS [k_table] [round]
       (schedule from IBM_SCHEDULE, as in papers/ibm_bicycle.py; with a round, only the fault sets whose detectors all
       lie in that round, a window of cdist.problem.window_problem, are enumerated: there the enumeration completes)
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import ibm_bicycle as IB
import run_parallel as RP
from cdist import problem, search


def main(key, basis, cycles, d, out, seconds, k_table=3, window=None):
    cycles, d, seconds, k_table = int(cycles), int(d), float(seconds), int(k_table)
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
    target, back = sector, list(range(sector.ncols))
    if window is not None:
        target = problem.window_problem(sector, int(window), int(window))
        back = list(target.col_meta)
    sym, kw = RP.sym_of(target, IB.translations(key))
    S = search.Searcher(target, labelfree=True, **kw)
    S.build_exclusions()
    table = search.Table(target, k_table, labelfree=True)
    S.add_table(table, exact=True)
    r = S.search(d, enum_all=True, time_limit=seconds, sol_cap=2_000_000)
    table.free()
    sols = sorted({tuple(sorted(back[j] for j in s)) for s in r["solutions"] if len(s) == d})
    assert all(search.verify(sector, s) for s in sols)
    assert r["best"] is None or r["best"] >= d, "a fault set below the certified distance"
    res = {"code": key, "schedule": stag, "basis": basis, "cycles": cycles, "distance": d, "status": r["status"],
           "window_round": None if window is None else int(window), "searched_columns": target.ncols,
           "complete": r["status"] == "exhausted", "n_orbit_representatives": len(sols), "solutions": [list(s) for s in sols],
           "nodes": r["nodes"], "threads": r["threads"], "search_seconds": round(r["seconds"], 1),
           "seconds": round(time.time() - t0, 1)}
    json.dump(res, open(out, "w"))
    print(f"{key} {basis}: {len(sols)} orbit representatives of weight {d}, status {r['status']}, "
          f"{res['seconds']} s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
