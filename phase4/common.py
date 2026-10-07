"""Shared helpers for the phase-4 experiments (dense DP inside the enumeration)."""
from __future__ import annotations

import ctypes
import os
import pickle
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "papers"))

from cdist import problem, search, symmetry  # noqa: E402

CACHE = os.path.join(ROOT, "phase4", "cache")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load(spec):
    """spec: 'bb288_r18_Z:collapsed', 'bb144_r12_Z:collapsed', 'mitten:[[300,60,14]]:X', ...
    Returns (problem, symmetry dict)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, spec.replace("/", "_").replace(":", "__") + ".pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    if spec.startswith("mitten:"):
        import mitten_effective
        import mitten_symmetry
        _, name, basis = spec.split(":")
        code_dir = os.path.join(ROOT, "papers", "mitten", "mitten", name)
        p = mitten_effective.effective_problem(code_dir, basis)
        sym = mitten_symmetry.find(p, code_dir)
        sym = {"ok": True, "rank": sym["rank"], "anchors": sym["anchors"]}
    else:
        # "<circuit>:<collapsed | foldP | sector>[:high]"; ":high" selects the memory
        # sector of circuits with flag detectors (as scripts/run_deep.py --sector-high)
        parts = spec.split(":")
        circ, which = parts[0], parts[1]
        high = True if len(parts) > 2 and parts[2] == "high" else None
        full = problem.load_dem_problem(os.path.join(ROOT, "circuits", circ + ".stim"), circ)
        sector = problem.sector_problem(full, high=high)
        assert problem.sector_is_exact(full, sector)
        if which == "collapsed":
            p = problem.collapse_time(sector)
        elif which.startswith("fold"):
            p = problem.fold_time(sector, int(which[4:]))
        else:
            p = sector
        sym = {"ok": False} if high else symmetry.translations(p)
    out = (p, sym)
    with open(path, "wb") as f:
        pickle.dump(out, f)
    return out


def bits(x):
    out = []
    while x:
        low = x & -x
        out.append(low.bit_length() - 1)
        x ^= low
    return out


class CancelCost:
    """Exact minimum completion cost of a residual syndrome (gm_cancel_cost)."""

    def __init__(self, S: search.Searcher, k):
        p = S.p
        self.S = S
        L = search.lib()
        L.gm_cancel_cost.restype = ctypes.c_int
        self.L = L
        self.free_tab = search.Table(problem.Problem(p.name + ":nolog", p.nrows, 1, p.h, [0] * p.ncols, p.row_meta), k)
        self.log_tab = search.Table(p, k)
        self.rh = self.log_tab.rh
        assert self.free_tab.rh == self.rh

    def __call__(self, sigma, lg, use_logical, cap):
        S = self.S
        tab = self.log_tab if use_logical else self.free_tab
        zh, zl = search.column_hashes([sigma], self.rh)
        sig = np.zeros(S.W, dtype=np.uint64)
        x = sigma
        for w in range(S.W):
            sig[w] = x & 0xFFFFFFFFFFFFFFFF
            x >>= 64
        P = search._ptr
        return self.L.gm_cancel_cost(
            ctypes.c_int(S.W), ctypes.c_int(S.p.ncols), ctypes.c_int(S.p.nrows), ctypes.c_int(S.wmax),
            P(S.col), P(S.lg), P(S.row_start), P(S.row_cols), ctypes.c_void_p(tab.handle),
            P(tab.zh), P(tab.zl), P(sig), ctypes.c_uint64(int(zh[0])), ctypes.c_uint64(int(zl[0])),
            ctypes.c_uint64(lg), ctypes.c_int(1 if use_logical else 0), ctypes.c_int(cap))


class Walker:
    """Random root-to-depth walks through the guided canonical DFS of gmitm.c
    (same pivot rule, sibling order, rank and pair exclusions).  The product
    of branching factors along a walk is Knuth's unbiased weight for the node
    it reaches."""

    def __init__(self, p, sym, K):
        self.p = p
        self.K = K
        S = search.Searcher(p, rank=sym["rank"] if sym.get("ok") else None,
                            anchors=sym["anchors"] if sym.get("ok") else None)
        S.build_exclusions()
        self.S = S
        self.rank = list(S.rank)
        self.anchors = [int(a) for a in S.anchors]
        self.row_cols = S._row_lists
        self.partners = [list(S.ex_cols[S.ex_start[j]:S.ex_start[j + 1]]) for j in range(p.ncols)]
        self.wmax = S.wmax

    def walk(self, depth, rng):
        """Returns (weight, sigma, lg, path, forbidden) for the node reached at
        `depth`, or None if the walk stops earlier (dead end, pruned by the
        weight test, or a solution)."""
        p = self.p
        a0 = rng.randrange(len(self.anchors))
        anchor = self.anchors[a0]
        weight = len(self.anchors)
        ra = self.rank[anchor]
        forb = bytearray(1 if self.rank[f] < ra else 0 for f in range(p.ncols))
        sigma, lg = p.h[anchor], p.l[anchor]
        forb[anchor] = 1
        for g in self.partners[anchor]:
            forb[g] = 1
        path = [anchor]
        for a in range(1, depth):
            if sigma == 0:
                return None
            R = self.K - a
            rows = bits(sigma)
            if R <= 0 or len(rows) > self.wmax * R:
                return None
            best, piv = None, None
            for r in rows:
                c = sum(1 for f in self.row_cols[r] if not forb[f])
                if best is None or c < best:
                    best, piv = c, r
            if best == 0:
                return None
            kids = [f for f in self.row_cols[piv] if not forb[f]]
            i = rng.randrange(len(kids))
            weight *= len(kids)
            for f in kids[:i + 1]:
                forb[f] = 1
            f = kids[i]
            for g in self.partners[f]:
                forb[g] = 1
            sigma ^= p.h[f]
            lg ^= p.l[f]
            path.append(f)
        return weight, sigma, lg, path, forb
