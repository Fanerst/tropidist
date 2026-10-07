"""Witness search on column-restricted versions of a mitten distance problem:
data errors plus hook faults at one or two positions of the schedule.
A restriction only removes faults, so every solution is a solution of the
full problem (an upper bound).  Results are stored with the full-problem
column indices so they can be replayed on the circuit.

Usage: python papers/mitten_restricted_isd.py "[[780,156,22]]" Z out.json seconds_per_subset [verify_rounds]
"""
import itertools
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mitten_effective
from cdist import isd, search
from cdist.problem import Problem
from run_mitten import verify_on_circuit


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(name, basis, out, seconds, verify_rounds=3):
    seconds, verify_rounds = float(seconds), int(verify_rounds)
    code_dir = os.path.join(HERE, "mitten", "mitten", name)
    n, k, d = [int(x) for x in name.strip("[]").split(",")]
    eff = mitten_effective.effective_problem(code_dir, basis)
    positions = sorted({x[2] for ms in eff.col_meta for x in ms if x[0] == "hook"})
    subsets = [()] + [(m,) for m in positions] + list(itertools.combinations(positions, 2))
    res = {"code": name, "basis": basis, "claimed_distance": d, "threads": isd.lib().isd_num_threads(),
           "seconds_per_subset": seconds, "subsets": []}
    best, best_sol = None, None
    for sub in subsets:
        idx = [j for j in range(eff.ncols)
               if any(x[0] == "data" or (x[0] == "hook" and x[2] in sub) for x in eff.col_meta[j])]
        P = Problem("restricted", eff.nrows, eff.nobs, [eff.h[j] for j in idx], [eff.l[j] for j in idx], eff.row_meta)
        w, sol = isd.search(P, time_limit=seconds, seed=1 + sum(sub))
        res["subsets"].append({"hook_positions": list(sub), "columns": P.ncols, "best_weight": w})
        if w is not None and (best is None or w < best):
            best, best_sol = w, tuple(sorted(idx[j] for j in sol))
            assert search.verify(eff, best_sol)
            log(f"{name} {basis}: data + hooks at {sub}: weight {w}")
    res["best_weight"] = best
    if best_sol is not None:
        res["solution_faults"] = [list(eff.col_meta[j][0]) for j in best_sol]
        w = verify_on_circuit(code_dir, n, basis, verify_rounds, eff, best_sol)
        res["witness"] = w
        if w["verified"]:
            res["certified_upper_bound"] = w["weight"]
        log(f"{name} {basis}: best witness weight {best} (claimed code distance {d}); verified={w['verified']}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
