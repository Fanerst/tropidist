"""Does 'unusable column' propagation explain the strength of the parity LP?

A free column is unusable if it touches a non-defect row where no other usable
free column exists (the defect it creates there could never be cancelled); a
defect row whose usable columns are all gone makes the node infeasible.
Compares, at random search nodes: simple dual, dual + ascent, LP -- each over
free columns and over usable columns -- and the parity LP.

Usage: python phase4/prop_probe.py SPEC K depths samples
"""
import math
import os
import random
import sys

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Walker, bits, load, log  # noqa: E402
from cover_probe import bounds, EPS  # noqa: E402

BIG = 10 ** 6


def usable_columns(p, W, sigma, forb, rounds=10):
    """Iterated removal.  Returns a bytearray 'dead' (1 = forbidden or unusable)."""
    dead = bytearray(forb)
    nfree = [sum(1 for f in W.row_cols[r] if not dead[f]) for r in range(p.nrows)]
    queue = [f for f in range(p.ncols) if not dead[f]]
    sbit = [(sigma >> r) & 1 for r in range(p.nrows)]
    changed = True
    it = 0
    while changed and it < rounds:
        changed = False
        it += 1
        for f in queue:
            if dead[f]:
                continue
            for r in W.rowsof[f]:
                if not sbit[r] and nfree[r] == 1:
                    dead[f] = 1
                    for q in W.rowsof[f]:
                        nfree[q] -= 1
                    changed = True
                    break
    return dead, it


def dual_bounds(W, sigma, dead):
    srows = bits(sigma)
    sset = set(srows)
    cols_at = {r: [f for f in W.row_cols[r] if not dead[f]] for r in srows}
    if any(not c for c in cols_at.values()):
        return BIG, BIG
    ov = {}
    for r in srows:
        for f in cols_at[r]:
            if f not in ov:
                ov[f] = sum(1 for q in W.rowsof[f] if q in sset)
    y = {r: 1.0 / max(ov[f] for f in cols_at[r]) for r in srows}
    simple = sum(y.values())
    load_ = {f: 0.0 for f in ov}
    for r in srows:
        for f in cols_at[r]:
            load_[f] += y[r]
    for r in sorted(srows, key=lambda r: len(cols_at[r])):
        d = min(1.0 - load_[f] for f in cols_at[r])
        if d > 1e-12:
            y[r] += d
            for f in cols_at[r]:
                load_[f] += d
    return math.ceil(simple - EPS), math.ceil(sum(y.values()) - EPS)


def lp_bound(W, sigma, dead):
    srows = bits(sigma)
    cols = sorted({f for r in srows for f in W.row_cols[r] if not dead[f]})
    if not cols:
        return BIG
    ci = {f: i for i, f in enumerate(cols)}
    A = lil_matrix((len(srows), len(cols)))
    for i, r in enumerate(srows):
        for f in W.row_cols[r]:
            if f in ci:
                A[i, ci[f]] = -1.0
    res = linprog(np.ones(len(cols)), A_ub=A.tocsr(), b_ub=-np.ones(len(srows)), bounds=(0, 1), method="highs")
    return math.ceil(res.fun - EPS) if res.status == 0 else BIG


def main(spec, K, depths, samples):
    K, samples = int(K), int(samples)
    p, sym = load(spec)
    W = Walker(p, sym, K)
    W.rowsof = [bits(a) for a in p.h]
    rng = random.Random(11)
    names = ["dual", "asc", "lp", "U:dual", "U:asc", "U:lp", "plp"]
    for d in [int(x) for x in depths.split(",")]:
        R = K - d
        tot = 0.0
        acc = {x: 0.0 for x in names}
        nun = []
        for _ in range(samples):
            w = W.walk(d, rng)
            if w is None:
                continue
            weight, sigma, lg, path, forb = w
            tot += weight
            v = {}
            v["dual"], v["asc"] = dual_bounds(W, sigma, forb)
            v["lp"] = lp_bound(W, sigma, forb)
            dead, it = usable_columns(p, W, sigma, forb)
            nun.append(sum(dead) - sum(forb))
            v["U:dual"], v["U:asc"] = dual_bounds(W, sigma, dead)
            v["U:lp"] = lp_bound(W, sigma, dead)
            v["plp"] = bounds(p, W, sigma, forb, True)["plp"]
            for x in names:
                if v[x] > R:
                    acc[x] += weight
        log(f"depth {d} R={R}: pruned " + " ".join(f"{x}={acc[x] / tot:.3f}" for x in names) +
            f" | unusable columns per node ~{sum(nun) / max(1, len(nun)):.1f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
