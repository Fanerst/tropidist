"""The other CSS basis of the code instances of the benchmark.

Each code instance of the benchmark is one CSS sector (the instance's `basis`: "X" means checks H_X and labels
L_X, i.e. the distance d_Z of Z-type logical operators; "Z" means d_X).  For the paper's code distance
d_code = min(d_X, d_Z), this script computes the other sector with the label-free search (full-budget
reconstruction), the covering bound and the code's verified symmetries.

usage: python scripts/codes_other_basis.py out.json [seconds per threshold] [names]
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "bench"), str(ROOT / "papers")]
import instances
import stabcode
from cdist import search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def other_perms(spec, hx, hz, n, perms, nrows):
    """Candidate check permutations for the other sector (the instance's were built for its own checks)."""
    if spec["builder"] == "kasai":
        import kasai_codes
        period = kasai_codes.load(str(ROOT / "papers/downloads/kasai" / spec["key"]), kasai_codes.shift_convention())[4]
        return kasai_codes.candidate_perms(nrows, period)
    return [q for q in (perms or []) if len(q) == nrows]


def main(out, seconds=3600, names=""):
    seconds = float(seconds)
    keep = set(names.split(",")) if names else None
    res = {"kernel_sha256": hashlib.sha256((ROOT / "cdist" / "gmitm.c").read_bytes()).hexdigest(),
           "threads": search.lib().gm_num_threads(), "seconds_per_threshold": seconds, "codes": {}}
    for name, spec in instances.INSTANCES.items():
        if spec["track"] != "code" or spec.get("status") != "ready" or (keep and name not in keep):
            continue
        meta = json.loads((ROOT / "bench" / "instances" / name / "meta.json").read_text())
        basis = spec["basis"]
        other = "Z" if basis == "X" else "X"
        hx, hz, n, perms = instances._code(spec)
        _, k = stabcode.css_parameters(hx, hz, n)
        p = stabcode.css_distance_problem(hx, hz, n, other, name=name)
        cand = other_perms(spec, hx, hz, n, perms, p.nrows)
        sym = symmetry.from_row_perms(p, cand) if cand else {"ok": False}
        kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
        t = time.time()
        r = search.distance(p, k_table=3 if n <= 400 else 2, kmax=search.DMAX, cover=True, labelfree=True,
                            time_limit=seconds, **kw)
        names_of = {"X": "d_Z", "Z": "d_X"}        # internal sector -> distance it computes
        rec = {"n": n, "k": k, "benchmark_sector": basis, "benchmark_value": meta["variants"]["full"].get("distance"),
               "benchmark_distance_name": names_of[basis], "other_sector": other, "other_distance_name": names_of[other],
               "distance": r["distance"], "lower_bound": r["lower_bound"],
               "orbits": len(sym["anchors"]) if sym.get("ok") else None,
               "runs": [{x: run[x] for x in ("K", "status", "seconds", "false_hits")} for run in r["runs"]],
               "seconds": round(time.time() - t, 1)}
        if r["solutions"]:
            rec["witness"] = list(r["solutions"][0])
            assert search.verify(p, r["solutions"][0])
        res["codes"][name] = rec
        log(f"{name} [[{n},{k}]]: {names_of[basis]} = {rec['benchmark_value']} (benchmark); "
            f"{names_of[other]} = {r['distance']} (lower bound {r['lower_bound']}), {rec['seconds']}s")
        with open(out, "w") as f:
            json.dump(res, f, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
