"""Sequential X-then-Z schedules for the weight-8 self-dual bivariate bicycle
codes of arXiv:2510.05211: exact circuit distance of every gate order.

Family: one cycle = X round then Z round; every check meets its eight qubits
in the same order (labels L0..L3 / R0..R3 = the terms of f on the two
sublattices); the same order is used for X and Z checks (H_X = H_Z, so the two
bases then have the same distance).  Orders that differ by swapping the first
two gates, swapping the last two, or reversal have the same hook faults: 5040
inequivalent orders, all evaluated exactly.

Usage: python papers/design_selfdual_bb.py n [out.json] [processes] [seconds per threshold] [budget seconds]
"""
import json
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import design
import selfdual_bb
import stabcode


def make_code(n):
    row = next(c for c in selfdual_bb.CODES if c[0] == n)
    _, k, d, extra, a1, a2 = row
    T = stabcode.Torus(a1, a2)
    f = [(0, 0), (1, 0)] + list(extra)
    N = T.n
    checks = []
    for s in range(N):
        c = {}
        for t, (a, b) in enumerate(f):
            c[("L", t)] = T.shift(s, a, b)                 # v1 qubit at s + e
            c[("R", t)] = N + T.shift(s, -a, -b)           # v2 qubit at s - e
        assert len(set(c.values())) == 8
        checks.append(c)
    code = design.Code(f"sdbb{n}", 2 * N, checks, checks, T.translations()[1:], claimed=(n, k, d))
    assert code.k == k
    return code


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


_CODE = None
_BEST = None
_TL = 0.0


def _init(n, best, tl):
    global _CODE, _BEST, _TL
    os.environ["OMP_NUM_THREADS"] = "1"
    _CODE = make_code(n)
    _BEST = best
    _TL = tl


def _evaluate(args):
    """Exact distance of one order, abandoning it as soon as it cannot beat the best value seen."""
    cap, order = args
    best = _BEST.value
    if cap <= best:
        return order, None, "screened"
    p = design.effective_problem(_CODE, "Z", order)
    sym, kw = design.problem_symmetry(p, _CODE)
    r = design.search.distance(p, k_table=2, kmax=cap, time_limit=_TL, **kw)
    if r["distance"] is None:
        return order, r["lower_bound"], "open"          # timed out: only a lower bound
    with _BEST.get_lock():
        if r["distance"] > _BEST.value:
            _BEST.value = r["distance"]
    return order, r["distance"], "exact"


def main(n, out=None, procs=8, time_limit=120, budget=0):
    n, procs, time_limit, budget = int(n), int(procs), float(time_limit), float(budget)
    code = make_code(n)
    d = code.claimed[2]
    t0 = time.time()
    dd, logs = design.low_weight_logicals(code, "Z", extra=1)
    assert dd == d
    scr = design.Screen(code, "Z", logs)
    tasks = sorted(((scr.bound(o)[0], o) for o in design.canonical_orders(code.labels_x)),
                   key=lambda x: (-x[0], tuple(map(str, x[1]))))
    log(f"[[{n},{code.k},{d}]]: {len(tasks)} inequivalent orders; single-hook bound at most {tasks[0][0]}")
    best = mp.Value("i", 0)
    hist, open_orders, best_orders = {}, [], []
    done = 0
    with mp.Pool(procs, initializer=_init, initargs=(n, best, time_limit)) as pool:
        for order, val, status in pool.imap_unordered(_evaluate, tasks, chunksize=1 if d > 8 else 4):
            done += 1
            if status == "exact":
                hist[val] = hist.get(val, 0) + 1
                best_orders.append((val, order))
            elif status == "open":
                open_orders.append((val, order))
            if budget and time.time() - t0 > budget:
                pool.terminate()
                break
    top = max(v for v, _ in best_orders)
    winners = sorted(o for v, o in best_orders if v == top)
    res = {"code": list(code.claimed), "family": "sequential X round then Z round; one gate order for every check and both types",
           "orders": len(tasks), "orders_processed": done, "single_hook_bound_max": tasks[0][0],
           "best_circuit_distance": top, "orders_with_best": len(winners),
           "example_order": [f"{a}{b}" for a, b in winners[0]],
           "exact_values_histogram_of_orders_not_abandoned": {str(k): v for k, v in sorted(hist.items())},
           "orders_left_open_by_time_limit": [[v, [f"{a}{b}" for a, b in o]] for v, o in open_orders],
           "optimal_over_family": not open_orders or all(v is not None and False for v, _ in open_orders),
           "seconds": round(time.time() - t0, 1)}
    # an order left open could still beat the best value only if its lower bound allows it
    res["optimal_over_family"] = (not open_orders) and done == len(tasks)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out, "w"), indent=1)
    if out:                 # the search result first; the verification below can take a while
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out, "w"), indent=1)
    # certify the example on the Stim circuit: same columns as a one-round window, witness replayed
    import ctypes
    import seq_circuit
    try:                    # the pool is gone: let the search kernel use all cores again
        ctypes.CDLL("libgomp.so.1").omp_set_num_threads(procs)
    except OSError:
        pass
    order = winners[0]
    res["verification"] = {}
    for basis in "ZX":
        p, r = design.exact_distance(code, basis, order, kmax=top)
        v = seq_circuit.verify(code, order, order, basis, p, r["solutions"][0] if r["solutions"] else None)
        v.pop("physical_faults", None)
        v["effective_distance"] = r["distance"]
        res["verification"][basis] = v
    if out:
        json.dump(res, open(out, "w"), indent=1)
    log(f"[[{n},{code.k},{d}]]: best circuit distance {top} of code distance {d} ({len(winners)} orders, e.g. "
        f"{res['example_order']}); processed {done}/{len(tasks)}, open {len(open_orders)}; verified on Stim: "
        f"{[res['verification'][b].get('verified') for b in 'ZX']}; {res['seconds']}s")


if __name__ == "__main__":
    main(*sys.argv[1:])
