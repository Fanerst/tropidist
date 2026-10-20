"""Exact circuit distance of the reported schedule designs, with the current kernel.

A design claim "the best order of the family has circuit distance d" needs an exact distance only for the winning
order: every other order needs an upper bound, which its witness already gives.  This script recomputes, in both
bases, the exact distance of
  - the winning order (`example_order`) of every sequential self-dual BB design, results/papers2/design/sdbb<n>.json
    (papers/design_selfdual_bb.py), which also covers the two-class designs (their reported values equal the
    uniform best);
  - the paper's layer order and one other best order of the sequential GALA [[132,30,12]] design,
    results/papers2/design/gala132.json (papers/design_gala.py).
The distance is that of the effective problem (data faults plus hook suffixes), which the original runs checked to
equal both the one-round window and the time-collapsed problem of the circuit.

usage: python scripts/recert_designs.py out.json [codes] [gala]
  codes: comma-separated n of the sdbb<n> designs, or "all" (default); gala: 1 (default) or 0
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers")]
import design
import design_gala
import design_selfdual_bb
from cdist import search


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def exact(code, order, kmax):
    out = {}
    for basis in "ZX":
        t = time.time()
        p, r = design.exact_distance(code, basis, order, kmax=kmax)
        assert all(x["status"] in ("exhausted", "found") for x in r["runs"])
        out[basis] = {"distance": r["distance"], "lower_bound": r["lower_bound"],
                      "false_hits": sum(x["false_hits"] for x in r["runs"]), "columns": p.ncols,
                      "seconds": round(time.time() - t, 2)}
    return out


def main(out, codes="all", gala="1"):
    only = None if codes == "all" else {int(x) for x in codes.split(",") if x}
    with open(os.path.join(ROOT, "cdist", "gmitm.c"), "rb") as f:
        res = {"kernel_sha256": hashlib.sha256(f.read()).hexdigest(), "threads": search.lib().gm_num_threads(),
               "sdbb_sequential": {}, "gala132_sequential": {}}
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "papers2", "design", "sdbb*.json"))):
        m = re.fullmatch(r"sdbb(\d+)\.json", os.path.basename(path))
        if not m:
            continue
        n = int(m.group(1))
        if only is not None and n not in only:
            continue
        rec = json.load(open(path))
        best, order = rec["best_circuit_distance"], rec["example_order"]
        # the record writes the labels ("L", 0), ("R", 3), ... of make_code as "L0", "R3", ...
        r = exact(design_selfdual_bb.make_code(n), [(s[0], int(s[1:])) for s in order], best)
        res["sdbb_sequential"][n] = {"record": os.path.relpath(path, ROOT), "reported_best": best,
                                     "optimal_over_family": rec.get("optimal_over_family"), "order": order, **r}
        log(f"sdbb{n}: reported {best}; exact Z {r['Z']['distance']}, X {r['X']['distance']}")
    if gala == "1":
        rec = json.load(open(os.path.join(ROOT, "results", "papers2", "design", "gala132.json")))
        best = int(rec["best_value_found"])
        paper = design_gala.PAPER_ORDER[132]
        other = next(o["order"] for o in rec["best_orders"] if o["order"] != paper)
        code = design_gala.make_code(132)
        for name, order in (("paper_order", paper), ("other_best_order", other)):
            r = exact(code, order, best)
            res["gala132_sequential"][name] = {"order": order, "reported": best, **r}
            log(f"gala132 {name}: reported {best}; exact Z {r['Z']['distance']}, X {r['X']['distance']}")
    with open(out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
