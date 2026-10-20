"""Code distances of the mitten codes [[150,30,10]] and [[200,40,12]] (data errors only), with the current kernel.

Replaces the producer of results/papers/mitten_code_distance.json, which is not in the repository.  The check
matrices are the authors' published ones (papers/mitten/mitten/<code>/Hx.npy, Hz.npy; github.com/a7b/yarn).

usage: python scripts/recert_mitten_codes.py out.json
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers")]
import stabcode
from cdist import search

CODES = {"[[150,30,10]]": 10, "[[200,40,12]]": 12}


def rows(H):
    return [int("".join("1" if x else "0" for x in r[::-1]), 2) for r in np.asarray(H, dtype=np.uint8)]


def main(out):
    with open(os.path.join(ROOT, "cdist", "gmitm.c"), "rb") as f:
        res = {"kernel_sha256": hashlib.sha256(f.read()).hexdigest(), "threads": search.lib().gm_num_threads(),
               "codes": {}}
    for name, d in CODES.items():
        base = os.path.join(ROOT, "papers", "mitten", "mitten", name)
        hx, hz = rows(np.load(os.path.join(base, "Hx.npy"))), rows(np.load(os.path.join(base, "Hz.npy")))
        n = np.load(os.path.join(base, "Hx.npy")).shape[1]
        _, k = stabcode.css_parameters(hx, hz, n)
        rec = {"n": n, "k": k}
        for basis in "ZX":
            t = time.time()
            p = stabcode.css_distance_problem(hx, hz, n, basis, name=name)
            r = search.distance(p, k_table=3, kmax=d + 1, cover=True, labelfree=True)
            rec[basis] = {"distance": r["distance"], "lower_bound": r["lower_bound"],
                          "false_hits": sum(x["false_hits"] for x in r["runs"]), "seconds": round(time.time() - t, 2)}
            print(name, basis, rec[basis], flush=True)
        res["codes"][name] = rec
    with open(out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
