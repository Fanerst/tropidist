"""Upper-bound witnesses by randomised information-set search on a
single-layer window of a Stim memory circuit (all faults whose detection
events lie in rounds a..b).  Any witness is checked in the full DEM and
replayed physically.  Finding nothing proves nothing.

Usage: python scripts/run_isd.py circuit.stim out.json a b seconds [stop_at] [first_seed] [--sector-high]
"""
import json
import os
import sys
import time

import stim

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import isd, problem, replay


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(argv):
    high = "--sector-high" in argv
    argv = [x for x in argv if x != "--sector-high"]
    path, out, a, b, seconds = argv[0], argv[1], int(argv[2]), int(argv[3]), float(argv[4])
    stop_at = int(argv[5]) if len(argv) > 5 else 1
    seed0 = int(argv[6]) if len(argv) > 6 else 1
    circ = stim.Circuit.from_file(path)
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full, high=True if high else None)
    assert problem.sector_is_exact(full, sector)
    win = problem.window_problem(sector, a, b)
    log(f"{path}: window t={a}..{b}: {win.nrows} rows x {win.ncols} columns, {win.nobs} observables")
    res = {"circuit": path, "window": [a, b], "columns": win.ncols, "threads": isd.lib().isd_num_threads(),
           "seconds_budget": seconds, "history": []}
    best, best_sol = None, None
    t0 = time.time()
    seed = seed0
    while time.time() - t0 < seconds and (best is None or best > stop_at):
        chunk = min(max(30.0, seconds / 20), seconds - (time.time() - t0))
        if chunk <= 0:
            break
        w, sol = isd.search(win, start_best=best, stop_at=stop_at, time_limit=chunk, seed=seed, log=log)
        seed += 1
        if w is not None:
            best, best_sol = w, sol
            res["history"].append({"weight": w, "seconds": round(time.time() - t0, 1)})
            log(f"  witness of weight {w} after {time.time() - t0:.0f}s")
    res["best_weight"] = best
    if best_sol is not None:
        cols = [win.col_meta[j] for j in best_sol]
        raw = replay.lift_to_dem(full, sector, cols)
        dets, obs, terms = replay.check_in_dem(circ, raw)
        faults = replay.physical_faults(circ, raw)
        d2, o2 = replay.replay(circ, faults)
        ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
        res["witness"] = {"weight": len(raw), "dem_error_indices": raw,
                          "dem_check": {"detectors": dets, "observables": obs},
                          "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement", "stack")} for f in faults],
                          "replay": {"fired_detectors": d2, "flipped_observables": o2}, "verified": ok}
        if ok:
            res["certified_upper_bound"] = len(raw)
        log(f"best witness weight {best}: verified={ok}; replay detectors={d2} observables={o2}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
