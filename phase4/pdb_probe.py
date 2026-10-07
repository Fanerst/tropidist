"""Dense min-plus tables on row patches as completion bounds ("tropical
pattern databases"), measured at random nodes of the guided enumeration.

For a row patch P, T_P[x] = minimum number of columns whose syndromes
restricted to P sum to x: an exact dense DP over 2^|P| states (one in-place
pass T[s] = min(T[s], T[s ^ v] + c) per distinct projected column v).  It is
a relaxation (rows outside P are ignored), so T_P[sigma|P] bounds the
completion cost from below.
  max : max over the patches of a partition (unit costs)
  add : the patches partition the rows; a column touching m patches costs 1/m
        in each, so the sum over patches is still a lower bound
Neither can know which columns are forbidden at the node.

Usage: python phase4/pdb_probe.py bb288_r18_Z:collapsed 15 9,10,11 150 [patch_bits]
"""
import ctypes
import json
import math
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Walker, bits, load, log  # noqa: E402
from cover_probe import bounds  # noqa: E402
from cdist import kernel  # noqa: E402

U = 60


def partitions(p, size):
    """Candidate partitions of the rows into patches of at most `size` rows."""
    xs = sorted({m[0] for m in p.row_meta})
    ys = sorted({m[1] for m in p.row_meta})
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}
    out = {}
    nx, ny = len(xs), len(ys)
    for bx in range(1, nx + 1):
        for by in range(1, ny + 1):
            if bx * by != size or nx % bx or ny % by:
                continue
            groups = {}
            for r, m in enumerate(p.row_meta):
                groups.setdefault((xi[m[0]] // bx, yi[m[1]] // by), []).append(r)
            out[f"rect{bx}x{by}"] = list(groups.values())
    # greedy clustering: grow each patch by the row sharing the most columns with it
    rows_of = [bits(a) for a in p.h]
    adj = [dict() for _ in range(p.nrows)]
    for rs in rows_of:
        for a in rs:
            for b in rs:
                if a != b:
                    adj[a][b] = adj[a].get(b, 0) + 1
    left = set(range(p.nrows))
    groups = []
    while left:
        seed = min(left)
        g = [seed]
        left.discard(seed)
        score = dict(adj[seed])
        while len(g) < size and left:
            cand = [(score.get(r, 0), -r) for r in left]
            best = -max(cand)[1]
            g.append(best)
            left.discard(best)
            for b, w in adj[best].items():
                score[b] = score.get(b, 0) + w
        groups.append(g)
    out["greedy"] = groups
    return out


def build_tables(p, groups, weighted):
    L = kernel.lib()
    L.dp_update_w.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint64, ctypes.c_uint64, ctypes.c_int]
    L.dp_update_w.restype = None
    u8p = ctypes.POINTER(ctypes.c_uint8)
    which = {}
    for gi, g in enumerate(groups):
        for i, r in enumerate(g):
            which[r] = (gi, i)
    proj = [dict() for _ in groups]      # projected value -> min cost
    for a in p.h:
        parts = {}
        for r in bits(a):
            gi, i = which[r]
            parts[gi] = parts.get(gi, 0) | (1 << i)
        cost = (U // len(parts)) if weighted else 1
        for gi, v in parts.items():
            if v not in proj[gi] or proj[gi][v] > cost:
                proj[gi][v] = cost
    tabs = []
    for gi, g in enumerate(groups):
        n = 1 << len(g)
        T = np.full(n, 255, dtype=np.uint8)
        T[0] = 0
        ptr = T.ctypes.data_as(u8p)
        for v, cst in proj[gi].items():
            if weighted:
                L.dp_update_w(ptr, n, v, cst)
            else:
                L.dp_update(ptr, n, v)
        tabs.append(T)
    return which, tabs, [len(x) for x in proj]


def lookup(which, tabs, sigma):
    idx = [0] * len(tabs)
    for r in bits(sigma):
        gi, i = which[r]
        idx[gi] |= 1 << i
    return [int(tabs[g][idx[g]]) for g in range(len(tabs))]


def main(spec, K, depths, samples, size=24):
    K, samples, size = int(K), int(samples), int(size)
    p, sym = load(spec)
    W = Walker(p, sym, K)
    W.rowsof = [bits(a) for a in p.h]
    res = {"spec": spec, "K": K, "patch_rows": size, "partitions": {}, "depths": {}}
    parts = partitions(p, size)
    built = {}
    for name, groups in parts.items():
        t = time.time()
        cut = sum(len({next(gi for gi, g in enumerate(groups) if r in g) for r in rs}) - 1 for rs in W.rowsof)
        w1, t1, n1 = build_tables(p, groups, False)
        w2, t2, n2 = build_tables(p, groups, True)
        built[name] = (w1, t1, t2)
        res["partitions"][name] = {"patches": len(groups), "extra_patch_incidences": cut,
                                   "distinct_projected_columns": n1,
                                   "max_table_value_unit": [int(x.max()) for x in t1],
                                   "seconds": round(time.time() - t, 1)}
        log(f"partition {name}: {len(groups)} patches of <= {size} rows, columns span {cut / p.ncols + 1:.2f} patches "
            f"on average; max table value (unit costs) {[int(x.max()) for x in t1]} ({time.time() - t:.1f}s)")
    rng = random.Random(11)
    for d in [int(x) for x in depths.split(",")]:
        R = K - d
        tot = 0.0
        acc = {}
        mean = {}
        n = 0
        for _ in range(samples):
            w = W.walk(d, rng)
            if w is None:
                continue
            weight, sigma, lg, path, forb = w
            tot += weight
            n += 1
            v = {"cover(dual)": bounds(p, W, sigma, forb, False)["dual"]}
            for name, (which, t1, t2) in built.items():
                v[f"max:{name}"] = max(lookup(which, t1, sigma))
                v[f"add:{name}"] = math.ceil(sum(lookup(which, t2, sigma)) / U - 1e-9)
            v["max:all"] = max(x for k_, x in v.items() if k_.startswith("max:"))
            v["add:all"] = max(x for k_, x in v.items() if k_.startswith("add:"))
            for x, val in v.items():
                acc[x] = acc.get(x, 0.0) + (weight if val > R else 0.0)
                mean[x] = mean.get(x, 0.0) + min(val, 99)
        frac = {x: acc[x] / tot for x in acc}
        res["depths"][d] = {"R": R, "pruned_fraction": frac, "mean_bound": {x: mean[x] / n for x in mean}}
        log(f"depth {d} R={R}: pruned " + " ".join(f"{x}={frac[x]:.3f}" for x in sorted(frac)))
        log(f"          mean bound " + " ".join(f"{x}={mean[x] / n:.2f}" for x in sorted(mean)))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results",
                       "pdb_" + spec.replace(":", "_").replace("[", "").replace("]", "").replace(",", "-") + f"_K{K}.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    log("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
