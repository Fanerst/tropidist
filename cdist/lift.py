"""Lift solutions of a relaxed (time-collapsed / folded) problem to the real one."""
from __future__ import annotations

import numpy as np

from . import search
from .problem import Problem


def expand_orbits(solutions, colmaps):
    """Close a set of solutions under the given column maps (symmetry generators)."""
    out = set()
    frontier = set(solutions)
    while frontier:
        x = frontier.pop()
        if x in out:
            continue
        out.add(x)
        for cm in colmaps:
            frontier.add(tuple(sorted(cm[j] for j in x)))
    return out


def orbit_representatives(solutions, colmaps):
    """One solution per symmetry orbit, with orbit sizes."""
    reps = []
    seen = set()
    for s in sorted(solutions):
        if s in seen:
            continue
        orb = expand_orbits([s], colmaps)
        seen |= orb
        reps.append((s, len(orb)))
    return reps


def lift(sector: Problem, relaxed: Problem, classes, slack=0, time_limit=60.0):
    """Search the real problem restricted to the members of the given relaxed
    classes (plus, if slack > 0, columns whose relaxed image is zero) for an
    undetected logical fault set of weight <= len(classes) + slack.

    Every real solution of that weight whose relaxed image is exactly this
    class set (up to `slack` image-free extras) lies in the restricted
    problem, so an exhausted search proves that none exists.
    Returns (weight, sector columns) or (None, None).
    """
    cols = []
    for j in classes:
        cols.extend(relaxed.col_meta[j])
    if slack > 0:
        cols.extend(i for i, img in enumerate(relaxed.image) if img == 0 and sector.l[i] == 0)
    cols = sorted(set(cols))
    sub = Problem("lift", sector.nrows, sector.nobs, [sector.h[i] for i in cols],
                  [sector.l[i] for i in cols], sector.row_meta)
    K = len(classes) + slack
    r = search.distance(sub, k_table=2, kmax=K, time_limit=time_limit, exclusions=False)
    if r["runs"] and r["runs"][-1]["status"] == "timeout":
        raise TimeoutError("lift search timed out")
    if r["distance"] is None:
        return None, None
    sol = r["solutions"][0]
    return r["distance"], tuple(cols[i] for i in sol)


class TopDown:
    """Exact search of the real problem organised by the solutions of a
    relaxation.

    Every real solution F projects onto a relaxed solution O (the classes hit
    an odd number of times) and uses |F| - |O| further columns (image-free
    columns, or class members beyond the first).  For a given O and slack the
    real problem is searched with exactly that budget, so running it over all
    relaxed solutions O with |O| <= W and slack W - |O| decides whether the
    real problem has a solution of weight <= W.
    """

    def __init__(self, sector: Problem, relaxed: Problem, k_main=2):
        self.sector = sector
        self.relaxed = relaxed
        self.S = search.Searcher(sector)
        self.table = search.Table(sector, k_main)
        self.S.add_table(self.table, exact=True)
        self.cls = np.full(sector.ncols, -1, dtype=np.int32)
        for j, members in enumerate(relaxed.col_meta):
            for i in members:
                self.cls[i] = j

    def lift(self, classes, slack, time_limit=0.0):
        """The record of the restricted search (Searcher.search).  Status "exhausted" with best None proves that
        no real solution projects onto `classes` with at most `slack` further columns; "found" comes with
        verified solutions (complete only if r["solutions_complete"]); any other status proves nothing."""
        onpat = np.zeros(self.relaxed.ncols, dtype=np.uint8)
        onpat[list(classes)] = 1
        anchor_class = min(classes, key=lambda j: len(self.relaxed.col_meta[j]))
        anchors = np.array(sorted(self.relaxed.col_meta[anchor_class]), dtype=np.int32)
        rank = np.full(self.sector.ncols, 1 << 30, dtype=np.int32)
        rank[anchors] = np.arange(len(anchors), dtype=np.int32)
        K = len(classes) + slack
        r = self.S.search(K, pattern=(self.cls, onpat, slack), anchors=anchors, rank=rank,
                          exclusions=False, time_limit=time_limit,
                          task_depth=max(1, min(2, K - self.table.k - 1)))
        for s in r["solutions"]:
            assert search.verify(self.sector, s)
        return r


def trivial_triples(p: Problem):
    """All column triples {a, b, c} with a + b + c = 0 in syndrome and logical label."""
    index = {(a, b): j for j, (a, b) in enumerate(zip(p.h, p.l))}
    row_lists = [[] for _ in range(p.nrows)]
    for j, a in enumerate(p.h):
        m = a
        while m:
            low = m & -m
            row_lists[low.bit_length() - 1].append(j)
            m ^= low
    triples = set()
    for cols in row_lists:
        for i, x in enumerate(cols):
            for y in cols[i + 1:]:
                z = index.get((p.h[x] ^ p.h[y], p.l[x] ^ p.l[y]))
                if z is not None and z != x and z != y:
                    triples.add(tuple(sorted((x, y, z))))
    return triples


def enumerate_solutions(p: Problem, K, k_table=3, rank=None, anchors=None, colmaps=None, sol_cap=2_000_000,
                        cover=False):
    """Every zero-syndrome, nonzero-logical column set of size <= K, provided
    K <= d + 3 where d >= 4 is the distance of p.

    The search (without pair exclusions) yields every solution that has no
    proper zero-syndrome subset.  A solution with such a subset splits into two
    zero-syndrome parts; for K <= d + 3 and d >= 4 these can only be a
    minimum solution and a disjoint trivial triple.

    With a symmetry (rank/anchors/colmaps) the result is closed under it.
    Returns (set of sorted tuples, stats).
    """
    S = search.Searcher(p, rank=rank, anchors=anchors)
    tab = search.Table(p, k_table)
    S.add_table(tab, exact=True)
    # the covering bound only uses that a completion avoids the forbidden
    # columns of its canonical path, so it is valid for non-minimum solutions too
    try:
        r = S.search(K, enum_all=True, exclusions=False, sol_cap=sol_cap, cover=cover)
    finally:
        tab.free()
    assert r["status"] == "exhausted", r["status"]
    assert r["solutions_complete"], "solution buffer overflow: %d found, %d kept" % (r["nsol_found"], sol_cap)
    sols = set(r["solutions"])
    for s in sols:
        assert search.verify(p, s)
    if colmaps:
        sols = expand_orbits(sols, colmaps)
    stats = {"nodes": sum(r["nodes"]), "seconds": r["seconds"], "decomposable_added": 0}
    if sols:
        d = min(len(s) for s in sols)
        stats["distance"] = d
        assert K <= d + 3, "enumeration is only complete up to d + 3"
        if K == d + 3:
            assert d >= 4
            triples = trivial_triples(p)
            stats["trivial_triples"] = len(triples)
            before = len(sols)
            for s in [x for x in sols if len(x) == d]:
                ss = set(s)
                for t in triples:
                    if not ss & set(t):
                        sols.add(tuple(sorted(s + t)))
            stats["decomposable_added"] = len(sols) - before
    return sols, stats
