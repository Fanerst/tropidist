"""Sequential X-then-Z schedules for monomial GALA codes (arXiv:2608.07431,
Table S5, L = 12, J = 5): search over the order of the twelve lift labels and
exact circuit distance.

Family: one cycle = X round then Z round; in the layer labelled F_u every X
check of block row i meets left block i+u, in the layer G_u right block i+u
(the Z checks have the same supports, the code being self-dual, and use the
same order).  The paper's own layer order for [[132,30,12]] is one member of
this family when read as a sequential schedule.

Usage: python papers/design_gala.py 132 out.json [processes] [samples] [cap] [seconds per threshold] [seed] [deep] [deep seconds]
"""
import json
import multiprocessing as mp
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import design
import gala_codes

PAPER_ORDER = {132: ["F0", "F3", "F4", "F5", "F2", "F1", "G1", "G4", "G2", "G5", "G3", "G0"]}


def make_code(n):
    (nn, k, d), L, J, factors, F, G = next(c for c in gala_codes.CODES if c[0][0] == n)
    assert all(len(x) == 1 for x in F + G), "monomial lifts only"
    els, add = gala_codes.group(factors)
    m, h = len(els), L // 2
    checks = []
    for i in range(J):
        for v in range(m):
            c = {}
            for u in range(h):
                c[f"F{u}"] = ((i + u) % h) * m + add(v, F[u][0])
                c[f"G{u}"] = (h + (i + u) % h) * m + add(v, G[u][0])
            checks.append(c)
    perms = [[i * m + add(v, g) for i in range(J) for v in range(m)] for g in els[1:]]
    code = design.Code(f"gala{n}", L * m, checks, checks, perms, claimed=(nn, k, d))
    assert code.k == k and sorted(code.hx) == sorted(gala_codes.build(L, J, factors, F, G)[0])
    return code


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


_CODE = None
_TL = 0.0
_KT = 2


def _init(n, tl, kt):
    global _CODE, _TL, _KT
    os.environ["OMP_NUM_THREADS"] = "1"
    _CODE, _TL, _KT = make_code(n), tl, kt


def _evaluate(args):
    """(order, cap) -> (order, exact distance or None, certified lower bound)."""
    order, cap = args
    p = design.effective_problem(_CODE, "Z", order)
    sym, kw = design.problem_symmetry(p, _CODE)
    r = design.search.distance(p, k_table=_KT, kmax=cap, time_limit=_TL, **kw)
    return order, r["distance"], r["lower_bound"]


def main(n, out, procs=8, samples=2000, cap=8, time_limit=600, seed=1, deep=0, deep_limit=3600):
    """Stage 1: `samples` random orders, exact distance up to `cap`.
    Stage 2: hill climbing by transpositions among the best.
    Stage 3 (deep > 0): the best `deep` orders are re-evaluated up to cap + 1."""
    n, procs, samples, cap, time_limit, seed = int(n), int(procs), int(samples), int(cap), float(time_limit), int(seed)
    deep, deep_limit = int(deep), float(deep_limit)
    code = make_code(n)
    d = code.claimed[2]
    labels = code.labels_x
    rng = random.Random(seed)
    t0 = time.time()
    res = {"code": list(code.claimed), "family": "sequential X round then Z round; one label order for all checks",
           "cap": cap, "samples": samples, "rounds": []}
    seen = {}

    def save():
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out, "w"), indent=1)

    def run(orders, cap_, tl):
        todo = [o for o in orders if seen.get(tuple(o), (None, 0, 0))[2] < cap_]
        with mp.Pool(procs, initializer=_init, initargs=(n, tl, 3)) as pool:
            for order, dist, lb in pool.imap_unordered(_evaluate, [(o, cap_) for o in todo], chunksize=1):
                seen[tuple(order)] = (dist, lb, cap_)
        return [(seen[tuple(o)][:2], o) for o in orders]

    def value(x):
        dist, lb = x
        return lb if dist is None else dist            # lb = cap + 1 when nothing was found up to cap

    if n in PAPER_ORDER:
        (dist, lb), _ = run([PAPER_ORDER[n]], d, time_limit)[0]
        res["paper_order"] = {"order": PAPER_ORDER[n], "distance": dist, "lower_bound": lb}
        log(f"paper's layer order as a sequential schedule: distance {dist} (lower bound {lb})")
        save()
    pop = []
    for _ in range(samples):
        o = list(labels)
        rng.shuffle(o)
        pop.append(o)
    scored = run(pop, cap, time_limit)
    hist = {}
    for x, _ in scored:
        key = str(x[0]) if x[0] is not None else f">={x[1]}"
        hist[key] = hist.get(key, 0) + 1
    res["random_sample_histogram"] = dict(sorted(hist.items()))
    log(f"{samples} random orders, exact up to {cap}: {dict(sorted(hist.items()))} ({time.time() - t0:.0f}s)")
    save()
    nfront = max(4, procs // 16)
    front = sorted(scored, key=lambda x: -value(x[0]))[:nfront]
    best = front[0]
    for rnd in range(4):
        if value(best[0]) > cap:
            break                                       # already beyond what this stage can resolve
        cand = []
        for _, o in front:
            for i in range(len(o)):
                for j in range(i + 1, len(o)):
                    q = list(o)
                    q[i], q[j] = q[j], q[i]
                    cand.append(q)
        rng.shuffle(cand)
        sc = run(cand[:max(samples // 2, 300)], cap, time_limit)
        allc = sorted(sc + front, key=lambda x: -value(x[0]))
        improved = value(allc[0][0]) > value(best[0])
        best = allc[0]
        front = allc[:nfront]
        res["rounds"].append({"round": rnd, "candidates": len(sc), "best_value": value(best[0])})
        log(f"hill-climb round {rnd}: best value {value(best[0])} ({time.time() - t0:.0f}s)")
        save()
        if not improved and rnd >= 1:
            break

    def ranked():
        return sorted(((seen[k][:2], list(k)) for k in seen), key=lambda x: -value(x[0]))

    top = value(ranked()[0][0])
    if deep and top > cap:
        cands = [o for x, o in ranked() if value(x) > cap][:deep]
        log(f"{sum(1 for x, o in ranked() if value(x) > cap)} orders have no solution up to {cap}; "
            f"evaluating {len(cands)} of them up to {cap + 1}")
        run(cands, cap + 1, deep_limit)
        top = value(ranked()[0][0])
    res["best_value_found"] = top
    r0 = ranked()
    res["best_is_lower_bound_only"] = r0[0][0][0] is None
    res["best_orders"] = [{"order": o, "distance": x[0], "lower_bound": x[1]} for x, o in r0 if value(x) == top][:30]
    res["orders_evaluated"] = len(seen)
    hist2 = {}
    for x, _ in r0:
        key = str(x[0]) if x[0] is not None else f">={x[1]}"
        hist2[key] = hist2.get(key, 0) + 1
    res["all_evaluated_histogram"] = dict(sorted(hist2.items()))
    res["seconds"] = round(time.time() - t0, 1)
    save()
    log(f"[[{n},{code.k},{d}]]: best value {top} ({'lower bound only' if res['best_is_lower_bound_only'] else 'exact'}); "
        f"all evaluated: {res['all_evaluated_histogram']}; {res['seconds']}s")


if __name__ == "__main__":
    main(*sys.argv[1:])
