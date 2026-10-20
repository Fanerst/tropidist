"""Completeness of the search when table fingerprints collide.

The counterexample of the paper's Appendix C.2: M = (1 1), R = I_2.  The unique feasible support is {0, 1}, so
the distance is 2.  With every row hash zero, all syndromes share one fingerprint; at threshold 2 the table then
reports a completion of cost 0 for either anchor (the empty set, whose label differs).  A reconstruction limited
to that cost finds nothing; the full remaining budget finds the other column.  Both table modes must find the
solution.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cdist import search
from cdist.problem import Problem


def colliding_table(p, k, labelfree):
    """A table whose syndrome fingerprints all collide (every row hash is zero)."""
    real = search.row_hashes
    search.row_hashes = lambda nrows, seed: ([0] * nrows, [0] * nrows)
    try:
        return search.Table(p, k, labelfree=labelfree)
    finally:
        search.row_hashes = real


def test_forced_collision():
    p = Problem("collide", 1, 2, [1, 1], [1, 2], [()])
    for labelfree in (False, True):
        S = search.Searcher(p, labelfree=labelfree)
        tab = colliding_table(p, 1, labelfree)
        S.add_table(tab, exact=True)
        r1 = S.search(1)
        r2 = S.search(2)
        tab.free()
        mode = "label-free" if labelfree else "labelled"
        assert r1["status"] == "exhausted" and not r1["solutions"], (mode, r1["status"])
        assert r2["solutions"] and sorted(r2["solutions"][0]) == [0, 1], (mode, r2["status"], r2["solutions"])


if __name__ == "__main__":
    test_forced_collision()
    print("ok: forced fingerprint collisions do not hide the weight-2 solution in either table mode")
