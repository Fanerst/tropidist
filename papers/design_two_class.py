"""Self-dual BB codes: sequential schedules with two gate orders, used on the
two classes of a 2-colouring of the checks (a homomorphism of the translation
group onto Z_2).  Coordinate ascent from the best uniform order: fix the order
of one class, evaluate all 5040 orders of the other exactly, repeat.

The circuit distance of a sequential schedule depends only on the gate order
inside each check, so any assignment of orders is a valid circuit (its depth
may exceed eight layers per round when different orders collide on a qubit).

Usage: python papers/design_two_class.py n out.json [processes] [sweeps]
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
import design_selfdual_bb as D
import selfdual_bb
import stabcode
from cdist import symmetry


def colourings(n):
    """Homomorphisms Z^2/<a1,a2> -> Z_2 as lists (class of each cell)."""
    row = next(c for c in selfdual_bb.CODES if c[0] == n)
    a1, a2 = row[4], row[5]
    T = stabcode.Torus(a1, a2)
    out = {}
    for name, (cx, cy) in (("x", (1, 0)), ("y", (0, 1)), ("x+y", (1, 1))):
        if (cx * a1[0] + cy * a1[1]) % 2 == 0 and (cx * a2[0] + cy * a2[1]) % 2 == 0:
            out[name] = [(cx * x + cy * y) % 2 for x, y in T.points]
    return T, out


_S = {}


def _init(n, cname):
    os.environ["OMP_NUM_THREADS"] = "1"
    code = D.make_code(n)
    T, cols = colourings(n)
    cls = cols[cname]
    # translations that preserve the colouring
    perms = [p for p, (x, y) in zip(T.translations(), T.points) if cls[T.index(x, y)] == cls[0]][1:]
    _S.update(code=code, cls=cls, perms=perms)


def _evaluate(args):
    o0, o1, cap = args
    code, cls = _S["code"], _S["cls"]
    p = design.effective_problem(code, "Z", lambda ci: o0 if cls[ci] == 0 else o1)
    sym = symmetry.from_row_perms(p, _S["perms"]) if _S["perms"] else {"ok": False}
    kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
    r = design.search.distance(p, k_table=2, kmax=cap, time_limit=120, **kw)
    return o0, o1, r["distance"], r["lower_bound"]


def main(n, out, procs=8, sweeps=2):
    n, procs, sweeps = int(n), int(procs), int(sweeps)
    uni = json.load(open(os.path.join(os.path.dirname(HERE), "results", "papers2", "design", f"sdbb{n}.json")))
    d = uni["code"][2]
    base = [(s[0], int(s[1:])) for s in uni["example_order"]]
    code = D.make_code(n)
    orders = list(design.canonical_orders(code.labels_x))
    T, cols = colourings(n)
    res = {"code": uni["code"], "uniform_best": uni["best_circuit_distance"], "colourings": {}}
    t0 = time.time()
    for cname in cols:
        best = (uni["best_circuit_distance"], base, base)
        hist_all = []
        with mp.Pool(procs, initializer=_init, initargs=(n, cname)) as pool:
            for sweep in range(sweeps):
                for side in (1, 0):
                    fixed = best[1] if side == 1 else best[2]
                    tasks = [((fixed, o, d) if side == 1 else (o, fixed, d)) for o in orders]
                    hist = {}
                    for o0, o1, dist, lb in pool.imap_unordered(_evaluate, tasks, chunksize=4):
                        v = dist if dist is not None else lb
                        hist[v] = hist.get(v, 0) + 1
                        if v > best[0]:
                            best = (v, o0, o1)
                    hist_all.append({"sweep": sweep, "varied_class": side, "histogram": {str(k): v for k, v in sorted(hist.items())}})
                    print(time.strftime("%H:%M:%S"), f"[[{n}]] colouring {cname} sweep {sweep} class {side}: best {best[0]} "
                          f"histogram {dict(sorted(hist.items()))}", flush=True)
                if best[0] == d:
                    break
        res["colourings"][cname] = {"best": best[0], "order_class0": [f"{a}{b}" for a, b in best[1]],
                                    "order_class1": [f"{a}{b}" for a, b in best[2]], "sweeps": hist_all}
    res["best_two_class"] = max(v["best"] for v in res["colourings"].values()) if res["colourings"] else None
    res["seconds"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    print(f"[[{n},{uni['code'][1]},{d}]]: uniform best {uni['best_circuit_distance']}, two-class best {res['best_two_class']} "
          f"({ {k: v['best'] for k, v in res['colourings'].items()} }) {res['seconds']}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
