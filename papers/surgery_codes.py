"""Certified X and Z distances of codes given as pairs of check matrices in Matrix Market format, such as the deformed
(merged) codes of qLDPC logical measurements: arXiv:2410.03628 (universal adapters, Zenodo 10.5281/zenodo.17527545)
and arXiv:2407.09423 (SSIP).  For each pair: n, k, and both distances by the weight-bounded search (no symmetry
supplied), with the lightest logical operator found checked again against the matrices.

d_X is the least weight of an X-type logical operator (basis "Z" of stabcode.css_distance_problem: X errors, detected by
the Z checks, flipping a Z logical), d_Z the reverse.

Usage: python papers/surgery_codes.py OUT.json NAME=HX.mtx,HZ.mtx [NAME=HX.mtx,HZ.mtx ...] [--kmax K] [--seconds S]
"""
import json
import os
import sys
import time

from scipy.io import mmread

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import stabcode
from cdist import search


def rows(path):
    a = mmread(path).tocsr()
    out = []
    for i in range(a.shape[0]):
        cols = a.indices[a.indptr[i]:a.indptr[i + 1]]
        vals = a.data[a.indptr[i]:a.indptr[i + 1]]
        out.append(sum(1 << int(j) for j, v in zip(cols, vals) if int(v) % 2))
    return out, a.shape[1]


def parity(x):
    return bin(x).count("1") & 1


def certify(hx, hz, n, basis, kmax, seconds):
    p = stabcode.css_distance_problem(hx, hz, n, basis)
    t0 = time.time()
    r = search.distance(p, k_table=2, kmax=kmax, time_limit=seconds, labelfree=True)
    rec = {"basis": basis, "columns": p.ncols, "rows": p.nrows, "lower_bound": r["lower_bound"], "distance": r["distance"],
           "seconds": round(time.time() - t0, 2), "runs": [{k: v for k, v in x.items() if k in ("K", "status", "seconds")}
                                                         for x in r["runs"]]}
    if r["distance"] is not None:
        lx, lz = stabcode.css_logicals(hx, hz, n)
        det, log = (hz, lz) if basis == "Z" else (hx, lx)
        cols = r["solutions"][0]
        qubits = sorted(q for c in cols for q in ([p.col_meta[c]] if isinstance(p.col_meta[c], tuple) else p.col_meta[c][:1]))
        e = sum(1 << j for _, j in qubits)
        rec["witness"] = [j for _, j in qubits]
        rec["witness_ok"] = (bin(e).count("1") == r["distance"] and all(parity(s & e) == 0 for s in det)
                             and any(parity(v & e) for v in log))
    return rec


if __name__ == "__main__":
    args = sys.argv[1:]
    kmax = int(args[args.index("--kmax") + 1]) if "--kmax" in args else 20
    seconds = float(args[args.index("--seconds") + 1]) if "--seconds" in args else 0.0
    out, specs = args[0], [a for a in args[1:] if "=" in a]
    results = json.load(open(out)) if os.path.exists(out) else {}
    for spec in specs:
        name, paths = spec.split("=")
        px, pz = paths.split(",")
        (hx, n), (hz, n2) = rows(px), rows(pz)
        assert n == n2
        assert all(parity(a & b) == 0 for a in hx for b in hz), "X and Z checks do not commute"
        _, k = stabcode.css_parameters(hx, hz, n)
        rec = {"hx": os.path.basename(px), "hz": os.path.basename(pz), "n": n, "k": k}
        for basis in "ZX":
            rec["d_X" if basis == "Z" else "d_Z"] = certify(hx, hz, n, basis, kmax, seconds)
        dx, dz = rec["d_X"], rec["d_Z"]
        rec["d"] = min(x["distance"] for x in (dx, dz)) if None not in (dx["distance"], dz["distance"]) else None
        print(name, n, k, "d_X", dx["distance"], dx["seconds"], "d_Z", dz["distance"], dz["seconds"],
              "witnesses ok", dx.get("witness_ok"), dz.get("witness_ok"), flush=True)
        results[name] = rec
        json.dump(results, open(out, "w"), indent=1)
