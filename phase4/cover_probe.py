"""Strength of cheap admissible completion bounds at random search nodes.

At a node with prefix A, residual syndrome sigma and budget R = K - |A|, any
completion B uses free columns only (forbidden columns are never in the
canonical completion of a minimum solution) and must touch every defect row
of sigma at least once.  Bounds on |B|:
  pop   ceil(|sigma| / wmax)                      (current test)
  u1    ceil(|sigma| / max_f |h_f & sigma|)       f free
  dual  ceil(sum_{r in sigma} 1 / m_r),  m_r = max over free f touching r of |h_f & sigma|
  lp    fractional set cover of sigma by free columns
  plp   lp plus parity: a used column that touches a non-defect row needs a
        second column there
A node is pruned by a bound if bound > R.  Fractions are Knuth-weighted.

Usage: python phase4/cover_probe.py bb288_r18_Z:collapsed 15 7,8,9,10,11 200
"""
import json
import math
import os
import random
import sys

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Walker, bits, load, log  # noqa: E402

EPS = 1e-6


def bounds(p, W, sigma, forb, with_lp=True):
    srows = bits(sigma)
    sset = set(srows)
    free_touch = set()
    for r in srows:
        for f in W.row_cols[r]:
            if not forb[f]:
                free_touch.add(f)
    ov = {f: sum(1 for r in W.rowsof[f] if r in sset) for f in free_touch}
    out = {"pop": math.ceil(len(srows) / W.wmax)}
    if not free_touch:
        return {k: 10 ** 6 for k in ("pop", "u1", "dual", "lp", "plp")}
    out["u1"] = math.ceil(len(srows) / max(ov.values()))
    tot = 0.0
    for r in srows:
        m = max((ov[f] for f in W.row_cols[r] if not forb[f]), default=0)
        if m == 0:
            return {k: 10 ** 6 for k in ("pop", "u1", "dual", "lp", "plp")}
        tot += 1.0 / m
    out["dual"] = math.ceil(tot - EPS)
    if not with_lp:
        return out
    cols = sorted(free_touch)
    ci = {f: i for i, f in enumerate(cols)}
    # covering rows
    A = lil_matrix((len(srows), len(cols)))
    for i, r in enumerate(srows):
        for f in W.row_cols[r]:
            if f in ci:
                A[i, ci[f]] = -1.0
    res = linprog(np.ones(len(cols)), A_ub=A.tocsr(), b_ub=-np.ones(len(srows)), bounds=(0, 1), method="highs")
    out["lp"] = math.ceil(res.fun - EPS) if res.status == 0 else 10 ** 6
    # parity: for a used column f and a non-defect row r of f, sum of other free columns at r >= x_f
    extra = set()
    for f in cols:
        for r in W.rowsof[f]:
            if r not in sset:
                for g in W.row_cols[r]:
                    if not forb[g]:
                        extra.add(g)
    cols2 = sorted(set(cols) | extra)
    ci2 = {f: i for i, f in enumerate(cols2)}
    nrow = len(srows)
    pairs = []
    for f in cols2:
        for r in W.rowsof[f]:
            if r not in sset:
                pairs.append((f, r))
    A2 = lil_matrix((nrow + len(pairs), len(cols2)))
    b2 = np.concatenate([-np.ones(nrow), np.zeros(len(pairs))])
    for i, r in enumerate(srows):
        for f in W.row_cols[r]:
            if f in ci2:
                A2[i, ci2[f]] = -1.0
    for q, (f, r) in enumerate(pairs):
        A2[nrow + q, ci2[f]] = 1.0
        for g in W.row_cols[r]:
            if g != f and g in ci2:
                A2[nrow + q, ci2[g]] = -1.0
    res = linprog(np.ones(len(cols2)), A_ub=A2.tocsr(), b_ub=b2, bounds=(0, 1), method="highs")
    out["plp"] = math.ceil(res.fun - EPS) if res.status == 0 else 10 ** 6
    return out


def main(spec, K, depths, samples, with_lp=1):
    K, samples, with_lp = int(K), int(samples), int(with_lp)
    depths = [int(x) for x in depths.split(",")]
    p, sym = load(spec)
    W = Walker(p, sym, K)
    W.rowsof = [bits(a) for a in p.h]
    wts = {}
    for a in p.h:
        wts[bin(a).count("1")] = wts.get(bin(a).count("1"), 0) + 1
    log(spec, f"rows={p.nrows} cols={p.ncols} wmax={W.wmax} column weights={dict(sorted(wts.items()))}")
    rng = random.Random(11)
    res = {"spec": spec, "K": K, "column_weights": wts, "depths": {}}
    names = ["pop", "u1", "dual"] + (["lp", "plp"] if with_lp else [])
    for d in depths:
        R = K - d
        tot = 0.0
        acc = {x: 0.0 for x in names}
        gap = {x: [] for x in names}
        n = 0
        for _ in range(samples):
            w = W.walk(d, rng)
            if w is None:
                continue
            weight, sigma, lg, path, forb = w
            n += 1
            tot += weight
            b = bounds(p, W, sigma, forb, with_lp)
            for x in names:
                if b[x] > R:
                    acc[x] += weight
                gap[x].append(min(b[x], 99))
        frac = {x: acc[x] / tot if tot else None for x in names}
        mean = {x: sum(v) / max(1, len(v)) for x, v in gap.items()}
        res["depths"][d] = {"R": R, "reached": n, "est_nodes": tot / samples, "pruned_fraction": frac,
                            "mean_bound": mean}
        log(f"depth {d} R={R} est_nodes={tot / samples:.3g}: pruned " +
            " ".join(f"{x}={frac[x]:.3f}" for x in names) + " | mean bound " +
            " ".join(f"{x}={mean[x]:.2f}" for x in names))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results",
                       "cover_" + spec.replace("/", "_").replace(":", "_").replace("[", "").replace("]", "").replace(",", "-") +
                       f"_K{K}.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    log("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
