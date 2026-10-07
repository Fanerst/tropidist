"""Compare cheap dual heuristics for the covering LP at random search nodes."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Walker, bits, load, log  # noqa: E402
from cover_probe import bounds, EPS  # noqa: E402


def setup(W, sigma, forb):
    srows = bits(sigma)
    sset = set(srows)
    cols_at = {r: [f for f in W.row_cols[r] if not forb[f]] for r in srows}
    ov = {}
    for r in srows:
        for f in cols_at[r]:
            if f not in ov:
                ov[f] = sum(1 for q in W.rowsof[f] if q in sset)
    return srows, cols_at, ov


def greedy(srows, cols_at, ov, order, start_uniform):
    y = {}
    load_ = {f: 0.0 for f in ov}
    for r in srows:
        if not cols_at[r]:
            return 10 ** 6
        y[r] = 1.0 / max(ov[f] for f in cols_at[r]) if start_uniform else 0.0
        for f in cols_at[r]:
            load_[f] += y[r]
    for r in order:
        d = min(1.0 - load_[f] for f in cols_at[r])
        if d > 1e-12:
            y[r] += d
            for f in cols_at[r]:
                load_[f] += d
    return math.ceil(sum(y.values()) - EPS)


def main(spec, K, depths, samples):
    K, samples = int(K), int(samples)
    p, sym = load(spec)
    W = Walker(p, sym, K)
    W.rowsof = [bits(a) for a in p.h]
    rng = random.Random(11)
    for d in [int(x) for x in depths.split(",")]:
        R = K - d
        tot = 0.0
        names = ["uni", "uni+asc", "g:maxov", "g:ncols", "g:sumov", "uni+asc(maxov)", "best", "lp"]
        acc = {x: 0.0 for x in names}
        for _ in range(samples):
            w = W.walk(d, rng)
            if w is None:
                continue
            weight, sigma, lg, path, forb = w
            tot += weight
            srows, cols_at, ov = setup(W, sigma, forb)
            if any(not cols_at[r] for r in srows):
                for x in names:
                    acc[x] += weight
                continue
            mx = {r: max(ov[f] for f in cols_at[r]) for r in srows}
            sm = {r: sum(ov[f] for f in cols_at[r]) for r in srows}
            v = {}
            v["uni"] = greedy(srows, cols_at, ov, [], True)
            v["uni+asc"] = greedy(srows, cols_at, ov, sorted(srows, key=lambda r: len(cols_at[r])), True)
            v["uni+asc(maxov)"] = greedy(srows, cols_at, ov, sorted(srows, key=lambda r: mx[r]), True)
            v["g:maxov"] = greedy(srows, cols_at, ov, sorted(srows, key=lambda r: (mx[r], sm[r])), False)
            v["g:ncols"] = greedy(srows, cols_at, ov, sorted(srows, key=lambda r: len(cols_at[r])), False)
            v["g:sumov"] = greedy(srows, cols_at, ov, sorted(srows, key=lambda r: sm[r]), False)
            v["best"] = max(v.values())
            v["lp"] = bounds(p, W, sigma, forb, True)["lp"]
            for x in names:
                if v[x] > R:
                    acc[x] += weight
        log(f"depth {d} R={R}: pruned " + " ".join(f"{x}={acc[x] / tot:.3f}" for x in names))


if __name__ == "__main__":
    main(*sys.argv[1:])
