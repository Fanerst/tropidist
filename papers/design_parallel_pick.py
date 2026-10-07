"""A first exact circuit distance for the mirror depth-8 circuits of a code that is too large
for a full sweep (design_sdbb_parallel_all.py) and where the window filter
(design_sdbb_parallel_funnel.py) leaves too many undecided orders.

  stage A  every mirror order: distance of the time-collapsed problem of its circuit (a lower
           bound, cheap), capped; and a short one-round-window search that discards orders
           with a fault set of low weight.
  stage B  the orders with the best collapsed bound among those not discarded are evaluated
           exactly with papers/run_parallel.py (all threads, both bases, limited time per
           threshold); the result is a certified interval for each.

The best evaluated order gives a circuit and its circuit distance; it is a lower bound on the
optimum of the mirror family, not the optimum.

Usage: python papers/design_parallel_pick.py module key [processes] [orders to evaluate] [seconds per threshold] [cap of the collapsed search]
"""
import json
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import design_sdbb_parallel as DP
import design_sdbb_parallel_all as FAM
import run_parallel
from cdist import problem

_CFG = None


def _init(cfg, module):
    global _CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    FAM.set_module(module)
    _CFG = cfg


def _score(order):
    key, cap, wcap = _CFG
    try:
        circ = FAM.MOD.build(key, "Z", 3, order=order)
        path = os.path.join(ROOT, "circuits", "papers", f"{FAM.prefix()}pick_w{os.getpid()}.stim")
        circ.to_file(path)
        full = problem.load_dem_problem(path, "x")
        os.remove(path)
        sector = problem.sector_problem(full)
        coll = problem.collapse_time(sector)
        sym, kw = run_parallel.sym_of(coll, FAM.MOD.translations(key))
        r = run_parallel.dist(coll, k_table=2, kmax=cap, time_limit=60, **kw)
        c = r["distance"] if r["distance"] is not None else r["lower_bound"]
        win = problem.window_problem(sector, 1, 1)
        sym, kw = run_parallel.sym_of(win, FAM.MOD.translations(key))
        r = run_parallel.dist(win, k_table=2, kmax=wcap, time_limit=20, **kw)
        w = r["distance"] if r["distance"] is not None else r["lower_bound"]
        return order, c, w, r["distance"] is not None
    except Exception as e:
        return order, -1, repr(e)[:100], True


def main(module, key, procs=8, n_eval=6, tl=1800, cap=10):
    key, procs, n_eval, tl, cap = int(key), int(procs), int(n_eval), float(tl), int(cap)
    FAM.set_module(module)
    code = FAM.MOD.CODES[key][2]
    d = code[2]
    orders = list(DP.palindromic_orders())
    out = os.path.join(ROOT, "results", "papers2", "design", f"{FAM.prefix()}{key}_parallel_pick.json")
    t0 = time.time()
    scored = []
    wcap = min(d - 1, cap + 1)
    with mp.Pool(procs, maxtasksperchild=8, initializer=_init, initargs=((key, cap, wcap), module)) as pool:
        for i, rec in enumerate(pool.imap_unordered(_score, orders, chunksize=4)):
            scored.append(rec)
            if (i + 1) % 800 == 0:
                print(time.strftime("%H:%M:%S"), f"{i + 1}/{len(orders)} orders scored, {time.time() - t0:.0f}s", flush=True)
    hist = {}
    for _, c, w, found in scored:
        hist[c] = hist.get(c, 0) + 1
    # candidates: best collapsed bound; among equals, the largest window value, undiscarded first
    ranked = sorted(scored, key=lambda x: (-x[1], x[3], -(x[2] if isinstance(x[2], int) else 0), x[0]))
    res = {"code": list(code), "orders": len(orders), "collapsed_bound_histogram": {str(k): v for k, v in sorted(hist.items())},
           "collapsed_cap": cap, "window_cap": wcap, "seconds_scoring": round(time.time() - t0, 1), "evaluated": []}
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"[[{code[0]},{code[1]},{code[2]}]]: collapsed bound histogram {res['collapsed_bound_histogram']}; "
          f"{res['seconds_scoring']}s", flush=True)
    try:
        import ctypes
        ctypes.CDLL("libgomp.so.1").omp_set_num_threads(procs)
    except OSError:
        pass
    top = ranked[:max(n_eval * 40, 1)]
    step = max(1, len([x for x in top if x[1] == top[0][1]]) // n_eval)
    cands = [x for x in top if x[1] == top[0][1]][::step][:n_eval]
    for order, c, w, found in cands:
        rec = {"order": [f"{a}{b}" for a, b in order], "collapsed": c, "window_lower_or_value": w, "window_solution_found": found}
        for basis in "ZX":
            lb, ub, dc = FAM.evaluate(key, order, basis, 6, tl, k_coll=3)
            rec[basis] = [lb, ub]
        res["evaluated"].append(rec)
        json.dump(res, open(out, "w"), indent=1)
        print(time.strftime("%H:%M:%S"), rec, flush=True)
    best = max(res["evaluated"], key=lambda e: min(e[b][0] or 0 for b in "ZX")) if res["evaluated"] else None
    res["best"] = best
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"[[{code[0]},{code[1]},{code[2]}]] best evaluated: {best}; {res['seconds']}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
