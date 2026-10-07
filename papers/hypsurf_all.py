"""All valid lifted schedules of one tiling of arXiv:2610.03682 (square modules, L = 5, r = 5,
multi-rate): Stim's graph-like distance of every assignment, schedule type and basis.

A filter for papers/run_parallel.py (module hypsurf_pick), which gives the exact circuit distance of
chosen assignments.  Usage: python papers/hypsurf_all.py q out.json [processes]
"""
import json
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hypsurf


def _one(job):
    q, kind, fb, basis, values = job
    key = "q%d_L5_%s%s" % (q, kind, "_fb" if fb else "")
    circ = hypsurf.build(key, basis, 5, assignment=values)
    return kind, fb, basis, values, len(circ.shortest_graphlike_error(ignore_ungraphlike_errors=True, canonicalize_circuit_errors=True))


def main(q, out, procs=4):
    q, procs = int(q), int(procs)
    t0 = time.time()
    res = {"q": q, "L": 5, "rounds": 5, "rows": {}}
    jobs = []
    for kind in ("ZZ", "NZ"):
        assigns = [tuple(a) for a in hypsurf.enumerate_schedules(q, kind, L=5)]
        res["assignments_" + kind] = len(assigns)
        for fb in (False, True):
            for basis in "ZX":
                jobs += [(q, kind, fb, basis, a) for a in assigns]
    with mp.Pool(procs) as pool:
        for i, (kind, fb, basis, values, d) in enumerate(pool.imap_unordered(_one, jobs, chunksize=16)):
            res["rows"].setdefault("%s%s" % (kind, "_fb" if fb else ""), {}).setdefault("".join(map(str, values)), {})[basis] = d
            if (i + 1) % 2000 == 0:
                print(time.strftime("%H:%M:%S"), i + 1, "of", len(jobs), flush=True)
    summary = {}
    for name, rows in res["rows"].items():
        hist = {}
        for v in rows.values():
            m = min(v["Z"], v["X"])
            hist[m] = hist.get(m, 0) + 1
        best = max(hist)
        summary[name] = {"histogram_of_min_over_bases": {str(k): hist[k] for k in sorted(hist)},
                         "best": best, "best_assignments": sorted(a for a, v in rows.items() if min(v["Z"], v["X"]) == best)[:50]}
    res["summary"] = summary
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    for name, s_ in summary.items():
        print(name, s_["histogram_of_min_over_bases"], "best", s_["best"], "e.g.", s_["best_assignments"][:3], flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
