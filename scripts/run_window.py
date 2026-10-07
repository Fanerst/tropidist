"""Upper bounds from single-layer windows: the sub-problem of all faults whose
detection events lie in rounds [a, b].  Every solution is a real undetected
logical fault set; it is verified in the full DEM and replayed physically.

Usage: python scripts/run_window.py circuits/bb288_r18_Z.stim results/window_bb288_r18_Z.json 1 1 [kmax] [k_table]
           [time_limit] [start] [cover: 0 | 1 | simple]
"""
import json
import os
import sys
import time

import stim

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import problem, replay, search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(path, out, a, b, kmax=18, k_table=3, time_limit=0, start=1, cover=0):
    a, b, kmax, k_table, time_limit, start = int(a), int(b), int(kmax), int(k_table), float(time_limit), int(start)
    cover = {"0": False, "1": True, "simple": "simple"}[str(cover)]     # covering bound (phase 4)
    circ = stim.Circuit.from_file(path)
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector)
    win = problem.window_problem(sector, a, b)
    sym = symmetry.translations(win)
    kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") and sym["generators"] else {}
    log(f"window t={a}..{b}: columns={win.ncols} symmetry={sym.get('generators')}")
    # start > 1 resumes after thresholds that an earlier run already exhausted
    r = search.distance(win, k_table=k_table, kmax=kmax, log=log, time_limit=time_limit, start=start, cover=cover,
                        **kw)
    res = {"circuit": path, "window": [a, b], "columns": win.ncols, "window_distance": r["distance"],
           "window_lower_bound": r["lower_bound"], "start": start, "threads": search.lib().gm_num_threads(),
           "cover": str(cover),
           "runs": [{"K": x["K"], "status": x["status"], "nodes": sum(x["nodes"]), "seconds": round(x["seconds"], 2)}
                    for x in r["runs"]]}
    if r["distance"] is not None:
        sol = [win.col_meta[j] for j in r["solutions"][0]]
        raw = replay.lift_to_dem(full, sector, sol)
        dets, obs, terms = replay.check_in_dem(circ, raw)
        faults = replay.physical_faults(circ, raw)
        d2, o2 = replay.replay(circ, faults)
        ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
        res["witness"] = {"weight": len(raw), "dem_error_indices": raw, "dem_errors": terms,
                          "dem_check": {"detectors": dets, "observables": obs},
                          "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement", "stack")} for f in faults],
                          "replay": {"fired_detectors": d2, "flipped_observables": o2}, "verified": ok}
        if ok:
            res["certified_upper_bound"] = len(raw)
        log(f"window distance {r['distance']}: witness verified={ok}; replay detectors={d2} observables={o2}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
