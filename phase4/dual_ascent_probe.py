"""Greedy dual ascent for the covering LP versus the simple dual and the LP.

Usage: python phase4/dual_ascent_probe.py SPEC K depths samples
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Walker, bits, load, log  # noqa: E402
from cover_probe import bounds, EPS  # noqa: E402


def ascent(W, sigma, forb, rounds=1):
    srows = bits(sigma)
    sset = set(srows)
    cols_at = {r: [f for f in W.row_cols[r] if not forb[f]] for r in srows}
    ov = {}
    for r in srows:
        for f in cols_at[r]:
            if f not in ov:
                ov[f] = sum(1 for q in W.rowsof[f] if q in sset)
    y = {}
    for r in srows:
        if not cols_at[r]:
            return 10 ** 6, 10 ** 6
        y[r] = 1.0 / max(ov[f] for f in cols_at[r])
    simple = sum(y.values())
    load_ = {f: 0.0 for f in ov}
    for r in srows:
        for f in cols_at[r]:
            load_[f] += y[r]
    for _ in range(rounds):
        # raise the defects with the fewest columns first
        for r in sorted(srows, key=lambda r: len(cols_at[r])):
            d = min(1.0 - load_[f] for f in cols_at[r])
            if d > 1e-12:
                y[r] += d
                for f in cols_at[r]:
                    load_[f] += d
    return math.ceil(simple - EPS), math.ceil(sum(y.values()) - EPS)


def main(spec, K, depths, samples):
    K, samples = int(K), int(samples)
    p, sym = load(spec)
    W = Walker(p, sym, K)
    W.rowsof = [bits(a) for a in p.h]
    rng = random.Random(11)
    for d in [int(x) for x in depths.split(",")]:
        R = K - d
        tot = 0.0
        acc = {"dual": 0.0, "ascent": 0.0, "lp": 0.0}
        for _ in range(samples):
            w = W.walk(d, rng)
            if w is None:
                continue
            weight, sigma, lg, path, forb = w
            tot += weight
            s, a = ascent(W, sigma, forb)
            b = bounds(p, W, sigma, forb, True)
            for x, v in (("dual", s), ("ascent", a), ("lp", b["lp"])):
                if v > R:
                    acc[x] += weight
        log(f"depth {d} R={R}: pruned " + " ".join(f"{x}={v / tot:.3f}" for x, v in acc.items()))


if __name__ == "__main__":
    main(*sys.argv[1:])
