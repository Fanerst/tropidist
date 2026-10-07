"""Independent check of a lower bound: exhaustive search of the FULL undecomposed
detector error model of a circuit (all detectors of both types, no CSS sector
reduction, no time collapse, no symmetry, no pair exclusions) for an undetected
logical fault set of weight <= K.  Only feasible for small circuits; it does
not share the reductions that papers/run_parallel.py relies on.

Also runs Stim's own heuristic search for an undetectable logical error
(an upper bound obtained by a different program).

Usage: python papers/crosscheck_full.py circuit.stim K out.json [k_table]
"""
import json
import os
import sys
import time

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from cdist import problem, search


def main(path, K, out, k_table=2):
    K, k_table = int(K), int(k_table)
    full = problem.load_dem_problem(path, os.path.basename(path))
    t = time.time()
    r = search.distance(full, k_table=k_table, kmax=K, exclusions=False, labelfree=True,
                        log=lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True))
    res = {"circuit": path, "detectors": full.nrows, "columns": full.ncols, "observables": full.nobs, "K": K,
           "distance_if_found": r["distance"], "certified_lower_bound": r["lower_bound"],
           "runs": [{"K": x["K"], "status": x["status"], "best": x["best"], "nodes": sum(x["nodes"]) if isinstance(x["nodes"], list) else x["nodes"],
                     "seconds": round(x["seconds"], 2)} for x in r["runs"]],
           "seconds": round(time.time() - t, 1)}
    t = time.time()
    circ = stim.Circuit.from_file(path)
    try:
        err = circ.search_for_undetectable_logical_errors(dont_explore_detection_event_sets_with_size_above=4,
                                                          dont_explore_edges_with_degree_above=4,
                                                          dont_explore_edges_increasing_symptom_degree=False)
        res["stim_heuristic_upper_bound"] = len(err)
    except Exception as e:                      # the heuristic may fail to find anything
        res["stim_heuristic_upper_bound"] = None
        res["stim_heuristic_error"] = repr(e)[:200]
    res["stim_seconds"] = round(time.time() - t, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "runs"}), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
