"""Parallel 12-layer circuit for GALA [[132,30,12]] (gala_parallel.py): choose
the label order and determine the circuit distance.

  1. random orders with a palindromic F/G pattern are scored by the distance
     of their time-collapsed problem (data errors + hook suffixes), up to `cap`;
  2. for the best few the circuit distance of the parallel circuit is
     determined with papers/run_parallel.py.

Usage: python papers/design_gala_parallel.py 132 [processes] [samples] [cap] [candidates] [rounds] [seconds per threshold] [seed]
"""
import ctypes
import json
import multiprocessing as mp
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import design
import design_gala as G
import gala_parallel
import run_parallel

_CODE = None


def _init(n):
    global _CODE
    os.environ["OMP_NUM_THREADS"] = "1"
    _CODE = G.make_code(n)


def _score(args):
    order, cap = args
    p = design.effective_problem(_CODE, "Z", order)
    sym, kw = design.problem_symmetry(p, _CODE)
    r = design.search.distance(p, k_table=3, kmax=cap, time_limit=900, **kw)
    return order, r["distance"], r["lower_bound"]


def random_palindromic(rng):
    pairs = rng.sample(range(6), 3)
    fpos = sorted(pairs + [11 - t for t in pairs])
    gpos = [t for t in range(12) if t not in fpos]
    fl, gl = [f"F{u}" for u in range(6)], [f"G{u}" for u in range(6)]
    rng.shuffle(fl)
    rng.shuffle(gl)
    order = [None] * 12
    for t, lab in zip(fpos, fl):
        order[t] = lab
    for t, lab in zip(gpos, gl):
        order[t] = lab
    return tuple(order)


def main(n=132, procs=32, samples=400, cap=8, candidates=4, rounds=6, time_limit=3600, seed=1, full=0, tag=""):
    """full = 1: when lifting leaves a gap, search the real circuit problem (pruned by the collapsed table)."""
    n, procs, samples, cap, candidates, rounds = int(n), int(procs), int(samples), int(cap), int(candidates), int(rounds)
    time_limit, seed, full = float(time_limit), int(seed), int(full)
    code = G.make_code(n)
    d = code.claimed[2]
    rng = random.Random(seed)
    t0 = time.time()
    orders = sorted({random_palindromic(rng) for _ in range(samples)})
    with mp.Pool(procs, initializer=_init, initargs=(n,)) as pool:
        scored = list(pool.imap_unordered(_score, [(o, cap) for o in orders], chunksize=1))
    hist = {}
    for _, dist, lb in scored:
        key = str(dist) if dist is not None else f">={lb}"
        hist[key] = hist.get(key, 0) + 1

    def value(x):
        return x[1] if x[1] is not None else x[2]
    top = max(value(x) for x in scored)
    cands = sorted(o for o, dist, lb in scored if (dist if dist is not None else lb) == top)
    print(time.strftime("%H:%M:%S"), f"[[{n},{code.k},{d}]]: {len(orders)} palindromic orders scored up to {cap}: "
          f"{dict(sorted(hist.items()))}; {len(cands)} at the top ({time.time() - t0:.0f}s)", flush=True)
    try:
        ctypes.CDLL("libgomp.so.1").omp_set_num_threads(procs)
    except OSError:
        pass
    outdir = os.path.join(ROOT, "results", "papers2", "design")
    res = {"code": list(code.claimed), "family": "parallel 12-layer circuit, palindromic X label order, reversed Z order",
           "orders_scored": len(orders), "cap": cap, "collapsed_distance_histogram": dict(sorted(hist.items())),
           "candidates": []}

    def save():
        json.dump(res, open(os.path.join(outdir, f"gala{n}_parallel{tag}.json"), "w"), indent=1)

    best = None
    step = max(1, len(cands) // candidates)
    for order in cands[::step][:candidates]:
        json.dump({"order": list(order)}, open(gala_parallel.order_file(n), "w"))
        rec = {"order": list(order)}
        for basis in "ZX":
            out = os.path.join(outdir, f"gala{n}_parallel{tag}_cand{len(res['candidates'])}_{basis}.json")
            run_parallel.main("gala_parallel", n, basis, out, rounds, 3, d, time_limit, full)
            r = json.load(open(out))
            rec[basis] = {k: r.get(k) for k in ("certified_lower_bound", "certified_upper_bound", "sector_symmetries_kept")}
            rec[basis]["collapsed_distance"] = r["collapsed"].get("distance")
            rec[basis]["witness_verified"] = (r.get("witness") or {}).get("verified")
        res["candidates"].append(rec)
        save()
        key = min(rec[b]["certified_lower_bound"] for b in "ZX")
        if best is None or key > best[0]:
            best = (key, rec)
            # keep the files of the best candidate under a fixed name
            json.dump({"order": list(order)}, open(os.path.join(outdir, f"gala{n}_parallel_best_order.json"), "w"))
        print(time.strftime("%H:%M:%S"), f"candidate {list(order)}: Z {rec['Z']}, X {rec['X']}", flush=True)
    res["best"] = best[1]
    res["seconds"] = round(time.time() - t0, 1)
    save()
    print(time.strftime("%H:%M:%S"), f"[[{n},{code.k},{d}]] parallel 12-layer circuit: best candidate {best[1]}; {res['seconds']}s",
          flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
