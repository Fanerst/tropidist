"""Exhaustive witness search on a column-restricted mitten distance problem: data errors plus hook faults at the
given schedule positions only (every minimum fault set found for the structured mitten codes has hooks at positions
2 and 3 only). A restriction only removes faults, so its minimum is an upper bound for the full problem, found here
by the exact search instead of the randomized one of mitten_restricted_isd.py; the solution is mapped to the Stim
circuit and replayed, with full-problem column indices.

Usage: python papers/mitten_restricted_exact.py "structured_mitten/[[840,168,18]]" Z out.json 2,3 [kmax] [k_table] [seconds_per_threshold] [verify_rounds] [start]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mitten_effective
import mitten_symmetry
from cdist import multi, search
from cdist.problem import Problem
from run_mitten import code_of, verify_on_circuit


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(name, basis, out, positions, kmax=16, k_table=2, seconds=0, verify_rounds=3, start=1):
    kmax, k_table, seconds, verify_rounds, start = int(kmax), int(k_table), float(seconds), int(verify_rounds), int(start)
    pos = {int(x) for x in positions.split(",")}
    code_dir, tag, (n, k, d) = code_of(name)
    eff = mitten_effective.effective_problem(code_dir, basis)
    idx = [j for j in range(eff.ncols)
           if any(x[0] == "data" or (x[0] == "hook" and x[2] in pos) for x in eff.col_meta[j])]
    P = Problem("restricted", eff.nrows, eff.nobs, [eff.h[j] for j in idx], [eff.l[j] for j in idx], eff.row_meta,
                [eff.col_meta[j] for j in idx])
    sym = mitten_symmetry.find(P, code_dir)
    res = {"code": name, "basis": basis, "claimed_distance": d, "hook_positions": sorted(pos),
           "threads": search.lib().gm_num_threads(), "columns": P.ncols, "full_columns": eff.ncols,
           "symmetries": sym["n_symmetries_kept"] + 1, "orbits": len(sym["anchors"]), "restricted_runs": []}
    log(name, basis, {x: res[x] for x in ("hook_positions", "columns", "full_columns", "symmetries", "orbits")})

    def save():
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)

    def on_run(rec):
        res["restricted_runs"].append(rec)
        save()

    r = multi.distance(P, k_table=k_table, kmax=kmax, rank=sym["rank"], anchors=sym["anchors"], time_limit=seconds,
                       log=log, on_run=on_run, start=start)
    # a lower bound of the restricted problem is not one of the circuit: keep it under its own name
    res["restricted_lower_bound"] = r["lower_bound"]
    res["restricted_distance"] = r["distance"]
    if r["distance"] is not None:
        sol = tuple(sorted(idx[j] for j in r["solutions"][0]))
        assert search.verify(eff, sol)
        res["solution_faults"] = [list(eff.col_meta[j][0]) for j in sol]
        w = verify_on_circuit(code_dir, tag, basis, verify_rounds, eff, sol)
        res["witness"] = w
        if w["verified"]:
            res["certified_upper_bound"] = w["weight"]
        log(f"{name} {basis}: restricted minimum {r['distance']} (hooks at {sorted(pos)}); verified={w['verified']}")
    save()


if __name__ == "__main__":
    main(*sys.argv[1:])
