"""Cross-check of the single-pass (label-free) lower bounds with the older
grouped search (one labelled pass per 64 observables): time-collapsed problem
of a Cornucopia circuit, thresholds up to kmax.

Usage: python papers/crosscheck_grouped.py 25 Z 8 out.json
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import cornucopia
import run_parallel
from cdist import multi, problem

q, basis, kmax, out = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
path = os.path.join(os.path.dirname(HERE), "circuits", "papers", f"cornucopia{36 * q}_r6_{basis}.stim")
if not os.path.exists(path):
    cornucopia.build(q, basis, 6).to_file(path)
full = problem.load_dem_problem(path, "x")
sector = problem.sector_problem(full)
coll = problem.collapse_time(sector)
sym, kw = run_parallel.sym_of(coll, cornucopia.translations(q))
t = time.time()
r = multi.distance(coll, k_table=2, kmax=kmax, log=run_parallel.log, **kw)
res = {"q": q, "basis": basis, "method": "grouped labelled search, k=2", "kmax": kmax, "distance": r["distance"],
       "lower_bound": r["lower_bound"], "groups": r["groups"],
       "runs": [{k: x[k] for k in ("K", "status", "best", "nodes", "seconds")} for x in r["runs"]],
       "seconds": round(time.time() - t, 1)}
json.dump(res, open(out, "w"), indent=1)
print("grouped search:", {k: res[k] for k in ("q", "basis", "distance", "lower_bound", "seconds")})
