"""All logical fault sets of weight <= KMAX of a chip (chip.py), without dominance exclusions (papers/ibm_bicycle_matched_spectrum.py
explains why), by exhaustive search; no symmetry, since dead checks break the translations.  Output: sector columns of each set,
with the data to compute rates at any p (rate_chip.py).

Usage: OMP_NUM_THREADS=N python chip_spectrum.py OUT.npz BASIS CYCLES DEAD_X DEAD_Z KMIN KMAX SECONDS [k_table] [px_pz]
       DEAD_X, DEAD_Z: comma-separated check indices or "-"
"""
import json
import os
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chip
from cdist import problem, search


def parse(x):
    return () if x == "-" else tuple(int(v) for v in x.split(","))


def main(out, basis, cycles, dx, dz, kmin, kmax, seconds, k_table="3", sched="standard"):
    cycles, kmin, kmax, seconds, k_table = int(cycles), int(kmin), int(kmax), float(seconds), int(k_table)
    dx, dz = parse(dx), parse(dz)
    s = None if sched == "standard" else chip.B.to_dicts(*(tuple(map(int, p)) for p in sched.split("_")))
    c = chip.build_chip("gross", basis, cycles, 1e-3, s, dx, dz)
    with tempfile.TemporaryDirectory() as tmp:
        c.to_file(tmp + "/c.stim")
        full = problem.load_dem_problem(tmp + "/c.stim", "c")
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector)
    t0 = time.time()
    S = search.Searcher(sector, labelfree=True)
    table = search.Table(sector, k_table, labelfree=True)
    S.add_table(table, exact=True)
    print(f"sector {sector.nrows} x {sector.ncols}, table k = {k_table}: {time.time() - t0:.1f} s, threads {search.lib().gm_num_threads()}",
          flush=True)
    res = dict(basis=basis, cycles=cycles, dead_x=list(dx), dead_z=list(dz), schedule=sched, runs=[])
    arrays = {}
    for K in range(kmin, kmax + 1):
        t1 = time.time()
        r = S.search(K, enum_all=True, time_limit=seconds, sol_cap=2_000_000_000, exclusions=False)
        reps = sorted({tuple(sorted(x)) for x in r["solutions"]})
        by = {}
        for x in reps:
            by.setdefault(len(x), []).append(x)
        info = {"K": K, "status": r["status"], "complete": bool(r["solutions_complete"]) and r["status"] == "exhausted",
                "seconds": round(time.time() - t1, 1), "sets": {w: len(v) for w, v in sorted(by.items())}}
        res["runs"].append(info)
        print(json.dumps(info), flush=True)
        arrays = {f"sets_{w}": np.array(v, dtype=np.uint16) for w, v in by.items()}
        np.savez_compressed(out, meta=json.dumps(res), **arrays)
        if not info["complete"]:
            break
    table.free()
    print(f"done in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
