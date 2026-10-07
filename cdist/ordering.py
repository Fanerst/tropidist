"""Column orderings with small cut rank (heuristic linear rank decompositions)."""
from __future__ import annotations

import math
import random

from .trellis import cut_profile, lowbit, rows_from_columns


def profile_cost(lam):
    """(peak, log2 of total table volume) of a cut profile."""
    peak = max(lam)
    vol = sum(2.0 ** (x - peak) for x in lam)
    return peak, peak + math.log2(vol)


def tn_sweep_width(cols, order, nrows):
    """Number of *original* rows straddling each cut.  This is the bond
    dimension exponent of a tensor network that sweeps the same column order
    with the checks kept in their given basis (no GF(2) basis change)."""
    rows = rows_from_columns(cols, order, nrows)
    n = len(order)
    delta = [0] * (n + 2)
    for r in rows:
        if r:
            delta[lowbit(r) + 1] += 1
            delta[r.bit_length()] -= 1
    out = []
    acc = 0
    for i in range(n + 1):
        acc += delta[i]
        out.append(acc)
    return out


def greedy_order(cols, nrows, seed=0, start=None, noise=0.0):
    """Grow the past set one column at a time, always taking a column that
    increases the cut rank least.

    Uses  Δλ(c) = [c in support of rows living purely in the future]
                 - [c is a coloop of the future set].
    Ties are broken towards columns whose rows are already touched.
    """
    rng = random.Random(seed)
    n = len(cols)
    rows = [r for r in rows_from_columns(cols, list(range(n)), nrows) if r]
    # reduced row echelon form of the matrix restricted to future columns
    rref = {}
    for r in rows:
        for p, q in rref.items():
            if (r >> p) & 1:
                r ^= q
        if r:
            p = lowbit(r)
            for p2 in list(rref):
                if (rref[p2] >> p) & 1:
                    rref[p2] ^= r
            rref[p] = r
    # rows supported purely on the future (all of them at the start), kept in
    # echelon form so one pivot removal handles a column leaving the future
    fut = list(rref.values())
    touched_rows = 0          # original rows touched by the past
    remaining = set(range(n))
    order = []
    full = (1 << n) - 1
    while remaining:
        fut_support = 0
        for r in fut:
            fut_support |= r
        coloops = 0
        for p, r in rref.items():
            if r == (1 << p):
                coloops |= 1 << p
        best = None
        cand = []
        for c in remaining:
            d = ((fut_support >> c) & 1) - ((coloops >> c) & 1)
            if start is not None and not order:
                d = 0 if c == start else 9
            tb = -bin(cols[c] & touched_rows).count("1") + bin(cols[c] & ~touched_rows).count("1")
            key = (d, tb + (rng.random() * noise if noise else 0.0))
            if best is None or key < best:
                best = key
                cand = [c]
            elif key == best:
                cand.append(c)
        c = rng.choice(cand)
        order.append(c)
        remaining.discard(c)
        touched_rows |= cols[c]
        bit = 1 << c
        # update future-only rows: one row with bit c stops being future-only
        piv = None
        for i, r in enumerate(fut):
            if r & bit:
                piv = i
                break
        if piv is not None:
            pr = fut.pop(piv)
            fut = [r ^ pr if r & bit else r for r in fut]
        # update RREF of the future restriction: delete column c
        if c in rref:
            r = rref.pop(c) & ~bit
            for p in rref:
                rref[p] &= ~bit
            if r:
                p = lowbit(r)
                for p2 in rref:
                    if (rref[p2] >> p) & 1:
                        rref[p2] ^= r
                rref[p] = r
        else:
            for p in rref:
                rref[p] &= ~bit
    return order


def sweep_orders(cols, row_xy, dims):
    """Geometric sweeps on a torus.  row_xy[r] = integer (x, y) cell of row r,
    dims = (lx, ly).  Yields (label, order) for sweeps along several lattice
    directions and seam offsets; each column is placed at the circular mean
    of its rows along the sweep coordinate."""
    lx, ly = dims
    directions = [(1, 0), (0, 1), (1, 1), (1, -1), (1, 2), (2, 1), (1, -2), (2, -1), (1, 3), (3, 1)]
    for (a, b) in directions:
        # sweep coordinate u = a*x/lx + b*y/ly  (mod 1)
        def u_of(r):
            x, y = row_xy[r]
            return (a * x / lx + b * y / ly) % 1.0
        us = [u_of(r) for r in range(len(row_xy))]
        pos = []
        for c in cols:
            sx = sy = 0.0
            sec = 0.0
            cnt = 0
            v = c
            while v:
                low = v & -v
                r = low.bit_length() - 1
                ang = 2 * math.pi * us[r]
                sx += math.cos(ang)
                sy += math.sin(ang)
                x, y = row_xy[r]
                sec += (x * 7 + y * 13) % 97
                cnt += 1
                v ^= low
            ang = math.atan2(sy, sx) % (2 * math.pi)
            pos.append((ang / (2 * math.pi), sec / max(cnt, 1)))
        nseam = 12
        for k in range(nseam):
            off = k / nseam
            order = sorted(range(len(cols)), key=lambda j: ((pos[j][0] - off) % 1.0, pos[j][1], j))
            yield f"sweep({a},{b})+{k}/{nseam}", order


def improve(cols, order, iters=2000, seed=0, max_block=24, log=None):
    """Local search on the order: move or reverse a short block, accept if the
    (peak, volume) of the cut profile does not get worse."""
    rng = random.Random(seed)
    best = list(order)
    best_cost = profile_cost(cut_profile(cols, best))
    n = len(order)
    for it in range(iters):
        i = rng.randrange(n)
        ln = rng.randint(1, max_block)
        j = min(n, i + ln)
        blk = best[i:j]
        rest = best[:i] + best[j:]
        if rng.random() < 0.25:
            cand = best[:i] + blk[::-1] + best[j:]
        else:
            k = max(0, min(len(rest), i + rng.randint(-3 * max_block, 3 * max_block)))
            cand = rest[:k] + blk + rest[k:]
        cost = profile_cost(cut_profile(cols, cand))
        if cost <= best_cost:
            if cost < best_cost and log:
                log(f"  improve it={it}: peak {cost[0]} vol 2^{cost[1]:.2f}")
            best, best_cost = cand, cost
    return best, best_cost
