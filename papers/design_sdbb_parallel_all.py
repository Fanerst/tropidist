"""Parallel depth-8 mirror circuits for a self-dual BB code: exact circuit
distance of EVERY palindromic order (3456 of them), not only of the orders
ranked best by the collapsed bound.

Each order is run through papers/run_parallel.py (Z basis; the circuit of the
mirror construction maps the X problem onto the Z problem of the mirrored
order, and the best orders are re-run in both bases at the end).  Workers are
single-threaded; every worker registers its own module so that file names do
not collide.

The last argument selects the code family: sdbb_parallel (default) or bb8_parallel
(weight-8 bivariate bicycle codes of arXiv:2609.06572, keys 1..5).

Usage: python papers/design_sdbb_parallel_all.py n [processes] [rounds] [seconds per threshold] [module]
"""
import contextlib
import io
import json
import multiprocessing as mp
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import design_sdbb_parallel as DP
import run_parallel
import sdbb_parallel

_N = None
_ARGS = None
MOD = sdbb_parallel


def set_module(name):
    global MOD
    MOD = __import__(name)
    return MOD


def prefix():
    return getattr(MOD, "PREFIX", "sdbb")


def _init(n, rounds, time_limit, module="sdbb_parallel"):
    global _N, _ARGS
    os.environ["OMP_NUM_THREADS"] = "1"
    set_module(module)
    _N, _ARGS = n, (rounds, time_limit)


def evaluate(n, order, basis, rounds, time_limit, k_coll=None):
    """Exact circuit distance of the mirror circuit with this X order: (lower, upper, collapsed distance)."""
    d = MOD.CODES[n][2][2]
    name = f"{prefix()}fam_w{os.getpid()}"
    mod = types.ModuleType(name)
    mod.CODES = MOD.CODES
    mod.build = lambda size, b, r, p=0.001: MOD.build(size, b, r, p, order=order)
    mod.translations = MOD.translations
    mod.tag = lambda size: f"{size}"
    sys.modules[name] = mod
    out = os.path.join(ROOT, "results", "papers2", "design", "family_tmp", f"{name}_{n}_{basis}.json")
    with contextlib.redirect_stdout(io.StringIO()):
        run_parallel.main(name, n, basis, out, rounds, k_coll or (2 if d <= 8 else 3), d, time_limit, 1)
    r = json.load(open(out))
    for f in (out, os.path.join(ROOT, "circuits", "papers", f"{name}{n}_r{rounds}_{basis}.stim")):
        if os.path.exists(f):
            os.remove(f)
    return r.get("certified_lower_bound"), r.get("certified_upper_bound"), r["collapsed"].get("distance")


def _work(order):
    try:
        return order, evaluate(_N, order, "Z", *_ARGS)
    except Exception as e:                     # keep the pool alive; the order is reported as failed
        return order, ("error", repr(e)[:200], None)


def main(n, procs=8, rounds=6, time_limit=300, module="sdbb_parallel"):
    n, procs, rounds, time_limit = int(n), int(procs), int(rounds), float(time_limit)
    set_module(module)
    code = MOD.CODES[n][2]
    orders = list(DP.palindromic_orders())
    out = os.path.join(ROOT, "results", "papers2", "design", f"{prefix()}{n}_parallel_family.json")
    t0 = time.time()
    part = out + ".part"                       # checkpoint: a killed sweep resumes where it stopped
    rows = json.load(open(part)) if os.path.exists(part) else []
    have = {tuple(r["order"]) for r in rows}
    todo = [o for o in orders if tuple(f"{a}{b}" for a, b in o) not in have]
    if rows:
        print(time.strftime("%H:%M:%S"), f"resuming: {len(rows)} orders from the checkpoint, {len(todo)} to do", flush=True)
    with mp.Pool(procs, maxtasksperchild=8, initializer=_init, initargs=(n, rounds, time_limit, module)) as pool:
        for i, (order, (lb, ub, dc)) in enumerate(pool.imap_unordered(_work, todo, chunksize=1)):
            rows.append({"order": [f"{a}{b}" for a, b in order], "lower": lb, "upper": ub, "collapsed": dc})
            if (i + 1) % 100 == 0:
                json.dump(rows, open(part + ".tmp", "w"))
                os.replace(part + ".tmp", part)
            if (i + 1) % 200 == 0:
                print(time.strftime("%H:%M:%S"), f"{len(rows)}/{len(orders)} orders, {time.time() - t0:.0f}s", flush=True)
    json.dump(rows, open(part, "w"))
    exact = [r for r in rows if isinstance(r["lower"], int) and r["lower"] == r["upper"]]
    hist, gap = {}, {}
    for r in exact:
        hist[r["lower"]] = hist.get(r["lower"], 0) + 1
        g = r["lower"] - r["collapsed"]
        gap[g] = gap.get(g, 0) + 1
    best = max(hist) if hist else None
    open_rows = [r for r in rows if r not in exact]
    res = {"code": list(code), "family": "parallel depth-8 circuit, palindromic X order, mirrored Z order",
           "basis": "Z", "rounds": rounds, "orders": len(orders), "orders_exact": len(exact),
           "circuit_distance_histogram": {str(k): v for k, v in sorted(hist.items())},
           "circuit_minus_collapsed_histogram": {str(k): v for k, v in sorted(gap.items())},
           "not_exact": open_rows[:50], "n_not_exact": len(open_rows),
           "best_circuit_distance": best,
           "best_orders": [r["order"] for r in exact if r["lower"] == best][:40],
           "seconds_search": round(time.time() - t0, 1)}
    json.dump(res, open(out, "w"), indent=1)
    # the best orders in both bases, with all threads
    try:
        import ctypes
        ctypes.CDLL("libgomp.so.1").omp_set_num_threads(procs)
    except OSError:
        pass
    both = []
    for o in res["best_orders"][:4]:
        order = [(s[0], int(s[1:])) for s in o]
        both.append({"order": o, **{b: evaluate(n, order, b, rounds, time_limit)[:2] for b in "ZX"}})
    res["best_orders_both_bases"] = both
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"[[{code[0]},{code[1]},{code[2]}]]: exact circuit distance of {len(exact)}/{len(orders)} "
          f"mirror orders: {res['circuit_distance_histogram']}; circuit - collapsed: {res['circuit_minus_collapsed_histogram']}; "
          f"both bases for the best: {both}; {res['seconds']}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
