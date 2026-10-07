"""Does any mirror order give a parallel depth-8 circuit with the FULL code
distance?  For the larger self-dual BB codes the exact circuit distance of all
3456 orders (design_sdbb_parallel_all.py) is too expensive, so the orders are
filtered first:

  stage 1  windows of the real circuit (upper bounds on the circuit distance):
           first the faults of one round, then those of two consecutive rounds.
           Search for a fault set of weight <= target - 1; an order is rejected
           as soon as one is found and survives only if both windows are
           exhausted up to target - 1.
  stage 2  survivors: exact circuit distance with papers/run_parallel.py.

target defaults to the code distance d.  The result lists, per order, the
window distance (or ">= target"), and for survivors the exact circuit distance.

Orders whose stage-1 search times out are kept as candidates with their window lower bound.

Usage: python papers/design_sdbb_parallel_funnel.py n [processes] [target] [seconds per order, stage 1] [seconds per threshold, stage 2] [max survivors to evaluate] [module]
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
import sdbb_parallel
from cdist import problem

_CFG = None


def _init(cfg, module="sdbb_parallel"):
    global _CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    FAM.set_module(module)
    _CFG = cfg


def _window(order):
    n, target, tl = _CFG
    try:
        circ = FAM.MOD.build(n, "Z", 4, order=order)
        path = os.path.join(ROOT, "circuits", "papers", f"{FAM.prefix()}fun_w{os.getpid()}.stim")
        circ.to_file(path)
        full = problem.load_dem_problem(path, "x")
        os.remove(path)
        sector = problem.sector_problem(full)
        # stage 1a: faults of one round; stage 1b: faults of two consecutive rounds (both are upper bounds)
        for hi in (1, 2):
            win = problem.window_problem(sector, 1, hi)
            sym, kw = run_parallel.sym_of(win, FAM.MOD.translations(n))
            r = run_parallel.dist(win, k_table=2, kmax=target - 1, time_limit=tl, **kw)
            if r["distance"] is not None:
                return order, r["distance"], "rejected"
            if r["runs"] and r["runs"][-1]["status"] == "timeout":
                return order, r["lower_bound"], "timeout"
        return order, target, "survivor"
    except Exception as e:
        return order, repr(e)[:200], "error"


def main(n, procs=8, target=0, tl1=300, tl2=1800, max_eval=24, module="sdbb_parallel"):
    n, procs, target, tl1, tl2, max_eval = int(n), int(procs), int(target), float(tl1), float(tl2), int(max_eval)
    FAM.set_module(module)
    code = FAM.MOD.CODES[n][2]
    target = target or code[2]
    orders = list(DP.palindromic_orders())
    suffix = "" if target == code[2] else "_t" + str(target)
    out = os.path.join(ROOT, "results", "papers2", "design", f"{FAM.prefix()}{n}_parallel_funnel{suffix}.json")
    t0 = time.time()
    hist, surv, timeouts, errors, rejected = {}, [], [], [], []
    part = out + ".part"                       # checkpoint of stage 1: a killed run resumes where it stopped
    done = [(tuple(tuple(x) for x in o), v, st) for o, v, st in json.load(open(part))] if os.path.exists(part) else []
    have = {o for o, _, _ in done}
    todo = [o for o in orders if o not in have]
    if done:
        print(time.strftime("%H:%M:%S"), f"resuming stage 1: {len(done)} orders from the checkpoint, {len(todo)} to do", flush=True)

    def stream():
        for rec in done:
            yield rec
        with mp.Pool(procs, maxtasksperchild=8, initializer=_init, initargs=((n, target, tl1), module)) as pool:
            for k, rec in enumerate(pool.imap_unordered(_window, todo, chunksize=2)):
                done.append(rec)
                if (k + 1) % 100 == 0:
                    json.dump(done, open(part + ".tmp", "w"))
                    os.replace(part + ".tmp", part)
                yield rec
        json.dump(done, open(part, "w"))
    if True:
        for i, (order, val, status) in enumerate(stream()):
            if status == "rejected":
                hist[val] = hist.get(val, 0) + 1
                rejected.append((val, order))
            elif status == "survivor":
                surv.append(order)
            elif status == "timeout":
                timeouts.append((val, order))
            else:
                errors.append((val, order))
            if (i + 1) % 400 == 0:
                print(time.strftime("%H:%M:%S"), f"{i + 1}/{len(orders)} orders, {len(surv)} survivors, {len(timeouts)} timeouts, "
                      f"{time.time() - t0:.0f}s", flush=True)
    res = {"code": list(code), "target": target, "orders": len(orders),
           "window_distance_histogram_of_rejected": {str(k): v for k, v in sorted(hist.items())},
           "survivors": [[f"{a}{b}" for a, b in o] for o in sorted(surv)],
           "stage1_timeouts": [[v, [f"{a}{b}" for a, b in o]] for v, o in timeouts], "stage1_errors": len(errors),
           "seconds_stage1": round(time.time() - t0, 1), "evaluated": []}
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"[[{code[0]},{code[1]},{code[2]}]] target {target}: {len(surv)} survivors of {len(orders)}; "
          f"rejected by window distance {res['window_distance_histogram_of_rejected']}; {len(timeouts)} timeouts", flush=True)
    try:
        import ctypes
        ctypes.CDLL("libgomp.so.1").omp_set_num_threads(procs)
    except OSError:
        pass
    step = max(1, len(surv) // max(max_eval, 1)) if surv else 1
    cands = sorted(surv)[::step][:max_eval]
    if len(cands) < max_eval:       # then the orders whose window search timed out, largest lower bound first
        cands += [o for _, o in sorted(timeouts, key=lambda x: -x[0])][:max_eval - len(cands)]
    if not cands and rejected and max_eval > 0:      # nobody reaches the target: the orders with the largest window distance
        top = max(v for v, _ in rejected)
        best = sorted(o for v, o in rejected if v == top)
        cands = best[::max(1, len(best) // max_eval)][:max_eval]
        res["no_order_reaches_target_in_the_window"] = True
        res["best_window_distance"] = top
        res["orders_with_best_window_distance"] = len(best)
    for order in cands:
        rec = {"order": [f"{a}{b}" for a, b in order]}
        for basis in "ZX":
            lb, ub, dc = FAM.evaluate(n, order, basis, 6, tl2, k_coll=3)
            rec[basis] = [lb, ub]
            rec["collapsed"] = dc
            if surv and not (isinstance(lb, int) and lb >= target):
                break                      # this order does not reach the target in this basis
        res["evaluated"].append(rec)
        json.dump(res, open(out, "w"), indent=1)
        print(time.strftime("%H:%M:%S"), rec, flush=True)
    full = [r for r in res["evaluated"] if all(r.get(b, [0])[0] == target for b in "ZX")]
    res["orders_with_target_in_both_bases"] = [r["order"] for r in full]
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"[[{code[0]},{code[1]},{code[2]}]]: {len(full)} of {len(res['evaluated'])} evaluated survivors "
          f"have circuit distance {target} in both bases; {res['seconds']}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
