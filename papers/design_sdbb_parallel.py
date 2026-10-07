"""Parallel depth-8 circuits for the self-dual BB codes (sdbb_parallel.py):
choose the gate order and determine the exact circuit distance.

  1. every order with a palindromic side pattern (3456 of them) is scored by
     the distance of its time-collapsed problem (data errors + hook suffixes),
     which is a lower bound on the circuit distance of the parallel circuit;
  2. for the best few orders the circuit distance of the actual parallel
     circuit is determined with papers/run_parallel.py (collapsed bound,
     lifting of collapsed solutions, one-round windows, replay).

Usage: python papers/design_sdbb_parallel.py n [processes] [candidates] [rounds] [seconds per threshold]
"""
import ctypes
import itertools
import json
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import design
import design_selfdual_bb as D
import run_parallel
import sdbb_parallel

_CODE = None


def _init(n):
    global _CODE
    os.environ["OMP_NUM_THREADS"] = "1"
    _CODE = D.make_code(n)


def _score(args):
    order, cap = args
    p = design.effective_problem(_CODE, "Z", order)
    sym, kw = design.problem_symmetry(p, _CODE)
    r = design.search.distance(p, k_table=2, kmax=cap, time_limit=300, **kw)
    return order, r["distance"], r["lower_bound"]


def palindromic_orders():
    for pairs_l in itertools.combinations(range(4), 2):          # which mirror pairs (t, 7-t) are on side L
        lpos = sorted([t for t in pairs_l] + [7 - t for t in pairs_l])
        rpos = [t for t in range(8) if t not in lpos]
        for pl in itertools.permutations(range(4)):
            for pr in itertools.permutations(range(4)):
                order = [None] * 8
                for t, a in zip(lpos, pl):
                    order[t] = ("L", a)
                for t, a in zip(rpos, pr):
                    order[t] = ("R", a)
                yield tuple(order)


def main(n, procs=8, candidates=4, rounds=6, time_limit=600):
    n, procs, candidates, rounds, time_limit = int(n), int(procs), int(candidates), int(rounds), float(time_limit)
    code = D.make_code(n)
    d = code.claimed[2]
    t0 = time.time()
    orders = list(palindromic_orders())
    with mp.Pool(procs, initializer=_init, initargs=(n,)) as pool:
        scored = list(pool.imap_unordered(_score, [(o, d) for o in orders], chunksize=4))
    hist = {}
    for _, dist, lb in scored:
        v = dist if dist is not None else lb
        hist[v] = hist.get(v, 0) + 1
    top = max(hist)
    cands = sorted(o for o, dist, lb in scored if (dist if dist is not None else lb) == top)
    print(time.strftime("%H:%M:%S"), f"[[{n},{code.k},{d}]]: {len(orders)} palindromic orders; collapsed distance histogram "
          f"{dict(sorted(hist.items()))}; {len(cands)} orders at {top} ({time.time() - t0:.0f}s)", flush=True)
    try:
        ctypes.CDLL("libgomp.so.1").omp_set_num_threads(procs)
    except OSError:
        pass
    outdir = os.path.join(ROOT, "results", "papers2", "design")
    res = {"code": list(code.claimed), "family": "parallel depth-8 circuit, palindromic X order, mirrored Z order",
           "orders": len(orders), "collapsed_distance_histogram": {str(k): v for k, v in sorted(hist.items())},
           "best_collapsed_distance": top, "candidates": []}
    step = max(1, len(cands) // candidates)
    best = None
    for order in cands[::step][:candidates]:
        json.dump({"order": [f"{a}{b}" for a, b in order]}, open(sdbb_parallel.order_file(n), "w"))
        rec = {"order": [f"{a}{b}" for a, b in order]}
        tmp = os.path.join(outdir, f"sdbb{n}_parallel_tmp_Z.json")
        run_parallel.main("sdbb_parallel", n, "Z", tmp, rounds, 2 if d <= 8 else 3, d, time_limit, 1)
        r = json.load(open(tmp))
        rec["Z"] = {k: r.get(k) for k in ("certified_lower_bound", "certified_upper_bound", "sector_symmetries_kept")}
        rec["Z"]["collapsed_distance"] = r["collapsed"].get("distance")
        res["candidates"].append(rec)
        lb, ub = rec["Z"]["certified_lower_bound"], rec["Z"]["certified_upper_bound"]
        if best is None or (lb, -(ub or 99)) > (best[0], -(best[1] or 99)):
            best = (lb, ub, order)
        if lb == d:
            break
    lb, ub, order = best
    json.dump({"order": [f"{a}{b}" for a, b in order]}, open(sdbb_parallel.order_file(n), "w"))
    final = {}
    for basis in "ZX":
        out = os.path.join(outdir, f"sdbb{n}_parallel_{basis}.json")
        run_parallel.main("sdbb_parallel", n, basis, out, rounds, 2 if d <= 8 else 3, d, time_limit, 1)
        r = json.load(open(out))
        final[basis] = {k: r.get(k) for k in ("certified_lower_bound", "certified_upper_bound")}
        final[basis]["witness_verified"] = (r.get("witness") or {}).get("verified")
    res["best_order"] = [f"{a}{b}" for a, b in order]
    res["circuit_distance"] = final
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(outdir, f"sdbb{n}_parallel.json"), "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"[[{n},{code.k},{d}]] parallel depth-8 circuit: collapsed {top}, circuit distance "
          f"Z {final['Z']}, X {final['X']}; order {res['best_order']}; {res['seconds']}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
