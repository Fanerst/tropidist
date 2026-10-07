"""Exact code distance of the two weight-11 routing codes (arXiv:2606.25330, Table 4), as a check
that the rebuilt matrices are the paper's codes.  Usage: python papers/routing_code200.py key out.json [seconds]"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import routing
import stabcode
from cdist import search, symmetry

key, out = sys.argv[1], sys.argv[2]
tl = float(sys.argv[3]) if len(sys.argv) > 3 else 3600
hx, hz, n = routing.matrices(key)
_, k = stabcode.css_parameters(hx, hz, n)
d = routing.CODES[key][2][2]
res = {"key": key, "n": n, "k": k, "claimed": list(routing.CODES[key][2]),
       "row_weights": sorted({bin(r).count("1") for r in hx + hz}), "distance": {}}
for basis in "ZX":
    p = stabcode.css_distance_problem(hx, hz, n, basis, name=f"routing{key}")
    sym = symmetry.from_row_perms(p, routing.translations(key))
    kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
    t = time.time()
    r = search.distance(p, k_table=3, kmax=d, cover=True, time_limit=tl,
                        log=lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True), **kw)
    res["distance"][basis] = {"d": r["distance"], "lower_bound": r["lower_bound"],
                              "last": r["runs"][-1]["status"] if r["runs"] else None,
                              "symmetries": sym.get("n_symmetries_kept") if sym.get("ok") else None,
                              "seconds": round(time.time() - t, 1)}
    print(key, basis, res["distance"][basis], flush=True)
    json.dump(res, open(out, "w"), indent=1)
