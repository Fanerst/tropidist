"""Tensor-network view of the same problem: widths and a small tropical
(min-plus) contraction by bucket elimination, used as an independent check.

Direct picture: one binary variable per column (fault), one parity tensor per
row (check).  A parity tensor of degree k is a chain of k-2 three-leg XOR
tensors, so the natural graph is the Tanner graph (variables and checks as
vertices); a contraction of width w stores tensors with w binary legs.
"""
from __future__ import annotations

import itertools

import numpy as np

INF = 255


def tanner_graph(h, nrows):
    """Adjacency of the bipartite Tanner graph: vertices ('c', j) and ('r', i)."""
    adj = {}
    for j, a in enumerate(h):
        adj.setdefault(("c", j), set())
        m = a
        while m:
            low = m & -m
            r = low.bit_length() - 1
            adj[("c", j)].add(("r", r))
            adj.setdefault(("r", r), set()).add(("c", j))
            m ^= low
    return adj


def row_graph(h, nrows):
    """Rows adjacent when some column touches both (detector/Fourier picture:
    one variable per row, one factor per column)."""
    adj = {i: set() for i in range(nrows)}
    for a in h:
        rows = []
        m = a
        while m:
            low = m & -m
            rows.append(low.bit_length() - 1)
            m ^= low
        for x, y in itertools.combinations(rows, 2):
            adj[x].add(y)
            adj[y].add(x)
    return adj


def greedy_elimination(adj, rule="min_fill"):
    """Elimination order and its induced width (an upper bound on treewidth)."""
    adj = {v: set(n) for v, n in adj.items()}
    order = []
    width = 0
    while adj:
        best = None
        for v, nb in adj.items():
            if rule == "min_degree":
                key = len(nb)
            else:
                nbl = list(nb)
                fill = 0
                for i in range(len(nbl)):
                    ai = adj[nbl[i]]
                    for k in range(i + 1, len(nbl)):
                        if nbl[k] not in ai:
                            fill += 1
                key = (fill, len(nb))
            if best is None or key < best[0]:
                best = (key, v)
                if key == 0 or key == (0, 0):
                    break
        v = best[1]
        nb = adj.pop(v)
        width = max(width, len(nb))
        for a in nb:
            adj[a].discard(v)
        for a, b in itertools.combinations(nb, 2):
            adj[a].add(b)
            adj[b].add(a)
        order.append(v)
    return order, width


def tropical_contract(h, l, obs_mask, nrows, order=None, max_rank=26, col_order=None):
    """min { |e| : H e = 0, (obs_mask . L) e = 1 } by min-plus bucket
    elimination on the direct-picture network.

    Variables: one per column, plus a running partial-parity variable for
    every row (the chain decomposition of its parity tensor).  Returns
    (minimum or None, largest tensor rank).
    """
    n = len(h)
    # col_order: sweep order of the columns.  Each parity chain then follows
    # the sweep, and variables are eliminated as the sweep passes them, so the
    # open legs at any time are the partial parities of the checks that
    # straddle the cut (in the given check basis).
    pos = {j: i for i, j in enumerate(col_order)} if col_order is not None else {j: j for j in range(n)}
    lrow_cols = sorted((j for j in range(n) if bin(l[j] & obs_mask).count("1") & 1), key=pos.get)
    rows = [[] for _ in range(nrows)]
    for j, a in enumerate(h):
        m = a
        while m:
            low = m & -m
            rows[low.bit_length() - 1].append(j)
            m ^= low
    for r in range(nrows):
        rows[r].sort(key=pos.get)
    factors = []   # (vars tuple, uint8 array)
    nxt = [n]
    when = {j: float(pos[j]) for j in range(n)}   # elimination time of each variable

    def new_var():
        nxt[0] += 1
        return nxt[0] - 1

    def xor3(a, b, c, target=0):
        t = np.full((2, 2, 2), INF, dtype=np.uint8)
        for x in (0, 1):
            for y in (0, 1):
                t[x, y, x ^ y ^ target] = 0
        return ((a, b, c), t)

    def parity_chain(cols, target):
        if not cols:
            return target == 0
        if len(cols) == 1:
            t = np.full(2, INF, dtype=np.uint8)
            t[target] = 0
            factors.append(((cols[0],), t))
            return True
        if len(cols) == 2:
            t = np.full((2, 2), INF, dtype=np.uint8)
            for x in (0, 1):
                t[x, x ^ target] = 0
            factors.append(((cols[0], cols[1]), t))
            return True
        acc = cols[0]
        for i in range(1, len(cols) - 1):
            nv = new_var()
            # partial parity up to cols[i]; it is consumed when cols[i+1] arrives
            when[nv] = pos[cols[i + 1]] + 0.5
            factors.append(xor3(acc, cols[i], nv))
            acc = nv
        t = np.full((2, 2), INF, dtype=np.uint8)
        for x in (0, 1):
            t[x, x ^ target] = 0
        factors.append(((acc, cols[-1]), t))
        return True

    for r in range(nrows):
        if rows[r]:
            parity_chain(rows[r], 0)
    if not lrow_cols:
        return None, 0
    parity_chain(lrow_cols, 1)
    for j in range(n):
        factors.append(((j,), np.array([0, 1], dtype=np.uint8)))

    nvars = nxt[0]
    adj = {v: set() for v in range(nvars)}
    for vs, _ in factors:
        for a, b in itertools.combinations(vs, 2):
            adj[a].add(b)
            adj[b].add(a)
    if order is None:
        if col_order is not None:
            order = sorted(range(nvars), key=lambda v: when[v])
        else:
            order, _ = greedy_elimination(adj, "min_fill")
    # dry run: the largest intermediate tensor this order would create
    scopes = [set(f[0]) for f in factors]
    dry = 0
    for v in order:
        mine = [sc for sc in scopes if v in sc]
        if not mine:
            continue
        scopes = [sc for sc in scopes if v not in sc]
        u = set().union(*mine)
        dry = max(dry, len(u))
        u.discard(v)
        if u:
            scopes.append(u)
    if dry > max_rank:
        return "skipped", dry
    peak = 0
    buckets = list(factors)
    scalar = 0
    for v in order:
        mine = [f for f in buckets if v in f[0]]
        buckets = [f for f in buckets if v not in f[0]]
        if not mine:
            continue
        scope = sorted(set().union(*[set(f[0]) for f in mine]))
        peak = max(peak, len(scope))
        acc = np.zeros((2,) * len(scope), dtype=np.uint16)
        for vs, t in mine:
            perm = sorted(range(len(vs)), key=lambda i: vs[i])
            tt = np.transpose(t, perm).astype(np.uint16)
            shape = [2 if s in vs else 1 for s in scope]
            acc = acc + tt.reshape(shape)
        acc = np.minimum(acc, INF).astype(np.uint8)
        out = acc.min(axis=scope.index(v))
        rest = tuple(s for s in scope if s != v)
        if rest:
            buckets.append((rest, out))
        else:
            val = int(out)
            if val >= INF:
                return None, peak
            scalar += val
    return scalar, peak
