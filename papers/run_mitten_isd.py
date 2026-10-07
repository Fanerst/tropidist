"""Upper-bound witnesses for a mitten code by information-set search on the
effective (hook-augmented) problem; the best one is mapped to the Stim memory
circuit, checked in the DEM and replayed physically.

Usage: python papers/run_mitten_isd.py "[[540,108,18]]" Z out.json seconds [verify_rounds] [stop_at] [first_seed]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mitten_effective
from cdist import isd
from run_mitten import verify_on_circuit


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(name, basis, out, seconds, verify_rounds=3, stop_at=1, seed0=1):
    seconds, verify_rounds, stop_at, seed0 = float(seconds), int(verify_rounds), int(stop_at), int(seed0)
    code_dir = os.path.join(HERE, "mitten", "mitten", name)
    n, k, d = [int(x) for x in name.strip("[]").split(",")]
    eff = mitten_effective.effective_problem(code_dir, basis)
    log(name, basis, f"{eff.nrows} x {eff.ncols}, {eff.nobs} observables")
    res = {"code": name, "basis": basis, "claimed_distance": d, "columns": eff.ncols,
           "threads": isd.lib().isd_num_threads(), "seconds_budget": seconds, "history": []}
    best, best_sol = None, None
    t0 = time.time()
    seed = seed0
    while time.time() - t0 < seconds and (best is None or best > stop_at):
        chunk = min(max(30.0, seconds / 20), seconds - (time.time() - t0))
        if chunk <= 0:
            break
        w, sol = isd.search(eff, start_best=best, stop_at=stop_at, time_limit=chunk, seed=seed, log=log)
        seed += 1
        if w is not None:
            best, best_sol = w, sol
            res["history"].append({"weight": w, "seconds": round(time.time() - t0, 1)})
            log(f"  witness of weight {w} after {time.time() - t0:.0f}s")
    res["best_weight"] = best
    if best_sol is not None:
        res["solution_faults"] = [list(eff.col_meta[j][0]) for j in best_sol]
        w = verify_on_circuit(code_dir, n, basis, verify_rounds, eff, best_sol)
        res["witness"] = w
        if w["verified"]:
            res["certified_upper_bound"] = w["weight"]
        log(f"best witness weight {best} (claimed code distance {d}); on the {verify_rounds}-round circuit: "
            f"verified={w['verified']}, replay detectors={w['replay']['fired_detectors']}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
