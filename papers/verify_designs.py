"""Re-verify every designed schedule in results/papers2/design/sdbb*.json on its
Stim circuit: sector reduction exact, effective columns == one-round window
columns == time-collapsed columns, and a minimum-weight fault set replayed.

Usage: python papers/verify_designs.py [out.json]
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import design
import design_selfdual_bb as D
import seq_circuit

out = sys.argv[1] if len(sys.argv) > 1 else None
res = {}
for f in sorted(glob.glob(os.path.join(os.path.dirname(HERE), "results", "papers2", "design", "sdbb*.json")),
                key=lambda x: int(os.path.basename(x)[4:-5])):
    r = json.load(open(f))
    n = r["code"][0]
    code = D.make_code(n)
    order = [(s[0], int(s[1:])) for s in r["example_order"]]
    rec = {}
    for basis in "ZX":
        p, rr = design.exact_distance(code, basis, order, kmax=r["best_circuit_distance"])
        v = seq_circuit.verify(code, order, order, basis, p, rr["solutions"][0] if rr["solutions"] else None, rounds=4)
        v.pop("physical_faults", None)
        v["effective_distance"] = rr["distance"]
        rec[basis] = v
    ok = all(rec[b]["sector_reduction_exact"] and rec[b]["effective_columns_equal_window_columns"] and
             rec[b]["effective_columns_equal_collapsed_columns"] and rec[b].get("verified") and
             rec[b]["effective_distance"] == r["best_circuit_distance"] for b in "ZX")
    res[str(n)] = {"code": r["code"], "best_circuit_distance": r["best_circuit_distance"], "all_checks_pass": ok, "bases": rec}
    print(r["code"], "distance", r["best_circuit_distance"], "all checks pass:", ok, flush=True)
    if out:
        json.dump(res, open(out, "w"), indent=1)
print(sum(1 for v in res.values() if v["all_checks_pass"]), "of", len(res), "designs pass every check")
