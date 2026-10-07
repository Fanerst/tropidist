"""Code-distance check of pair-partition CSS codes from K. Kasai's data page
(kasai.ict.eng.isct.ac.jp/pair_partition_cpm_css_codes_20260714.html), the
family behind arXiv:2607.14091 and the CSS tables of arXiv:2609.30069.
Files are read as data from papers/downloads/kasai/ (downloaded 2026-10-03).

  .npz : Hx, Hz are used as given.
  .cpm : "CPM_CSS_V1", then "name P L Jx Jz", then the Jx x L exponent array of
         H_X and the Jz x L exponent array of H_Z; block (j, l) is the P x P
         circulant shift by the exponent (direction fixed by comparing an .npz
         file that carries both the exponents and the matrix).

Usage: python papers/kasai_codes.py [out.json] [max_d] [seconds per threshold] [only: substring of the file name]
"""
import glob
import json
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import stabcode
from cdist import search, symmetry

DATA = os.path.join(HERE, "downloads", "kasai")


def from_exponents(E, P, sign):
    rows = []
    for j in range(len(E)):
        for v in range(P):
            rows.append(sum(1 << (l * P + (v + sign * int(e)) % P) for l, e in enumerate(E[j])))
    return rows


def shift_convention():
    """Sign s such that row (j, v) of a circulant block with exponent e has its one at column v + s*e."""
    z = np.load(os.path.join(DATA, "pp_232_62_12_cw8_P29.npz"), allow_pickle=False)
    P = int(z["P"])
    want = set(stabcode.rows_to_ints(z["Hx"]))
    for sign in (1, -1):
        if set(from_exponents(z["E_x"], P, sign)) == want:
            return sign
    raise AssertionError("exponent convention not recognised")


def load(path, sign):
    name = os.path.basename(path)
    if path.endswith(".npz"):
        z = np.load(path, allow_pickle=False)
        hx, hz = stabcode.rows_to_ints(z["Hx"]), stabcode.rows_to_ints(z["Hz"])
        return name, hx, hz, int(z["Hx"].shape[1]), int(z["P"]), (int(z["d"]) if "d" in z.files else None)
    lines = open(path).read().split("\n")
    assert lines[0].strip() == "CPM_CSS_V1"
    _, P, L, Jx, Jz = lines[1].split()
    P, L, Jx, Jz = int(P), int(L), int(Jx), int(Jz)
    arr = [[int(x) for x in ln.split()] for ln in lines[2:2 + Jx + Jz]]
    assert all(len(r) == L for r in arr)
    return name, from_exponents(arr[:Jx], P, sign), from_exponents(arr[Jx:], P, sign), L * P, P, None


def candidate_perms(nrows, P):
    """Cyclic shifts inside blocks of P rows, for Z_P and for every way of
    writing the block index as a pair (a, b); invalid ones are dropped later."""
    J = nrows // P
    out = [[j * P + (v + c) % P for j in range(J) for v in range(P)] for c in range(1, P)]
    for p1 in range(2, P):
        if P % p1 == 0:
            p2 = P // p1
            for da, db in ((1, 0), (0, 1)):
                out.append([j * P + ((v // p2 + da) % p1) * p2 + (v % p2 + db) % p2 for j in range(J) for v in range(P)])
    return out


def claimed(name):
    m = re.search(r"(\d+)_(\d+)_(?:ge|d)?(\d+)", name)
    return [int(m.group(1)), int(m.group(2)), int(m.group(3))] if m else None


def main(out=None, max_d=16, time_limit=1800, only=""):
    max_d, time_limit = int(max_d), float(time_limit)
    sign = shift_convention()
    res = []
    for path in sorted(glob.glob(os.path.join(DATA, "*.cpm")) + glob.glob(os.path.join(DATA, "*.npz"))):
        if only not in os.path.basename(path):
            continue
        name, hx, hz, n, P, d_file = load(path, sign)
        _, k = stabcode.css_parameters(hx, hz, n)
        cl = claimed(name)
        d_claim = d_file if d_file is not None else (cl[2] if cl else None)
        rec = {"file": name, "n": n, "k": k, "P": P, "label_in_file_name": cl, "d_in_file": d_file,
               "row_weights": sorted({bin(r).count("1") for r in hx + hz}), "distance": {}}
        if d_claim is not None and d_claim > max_d:
            rec["skipped"] = f"claimed distance {d_claim} above the limit {max_d}"
            res.append(rec)
            print(name, rec["skipped"], flush=True)
            continue
        t = time.time()
        for basis in "ZX":
            p = stabcode.css_distance_problem(hx, hz, n, basis, name=name)
            sym = symmetry.from_row_perms(p, candidate_perms(p.nrows, P))
            kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
            r = search.distance(p, k_table=3 if n <= 300 else 2, kmax=(d_claim or max_d), cover=True,
                                time_limit=time_limit, **kw)
            rec["distance"][basis] = {"d": r["distance"], "lower_bound": r["lower_bound"],
                                      "orbits": len(sym["anchors"]) if sym.get("ok") else None,
                                      "last": r["runs"][-1]["status"] if r["runs"] else None,
                                      "witness": list(r["solutions"][0]) if r["solutions"] else None}
        ds = [rec["distance"][b]["d"] for b in "ZX"]
        rec["d"] = min(ds) if all(x is not None for x in ds) else None
        rec["lower_bound"] = min(rec["distance"][b]["lower_bound"] for b in "ZX")
        rec["seconds"] = round(time.time() - t, 1)
        res.append(rec)
        print(f"{name}: n={n} k={k} d_Z, d_X = {ds} (lower bounds {[rec['distance'][b]['lower_bound'] for b in 'ZX']}) "
              f"claimed {d_claim} {rec['seconds']}s", flush=True)
        if out:
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            json.dump({"source": "https://kasai.ict.eng.isct.ac.jp/pair_partition_cpm_css_codes_20260714.html",
                       "threads": search.lib().gm_num_threads(), "codes": res}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
