"""Is a row of arXiv:2610.03682 identified by its printed distance range?

LINS lists normal subgroups of equal index in an order that depends on the index bound of the run,
so a position in the list does not fix a tiling by itself.  For every row used in docs/PAPERS.md
that lies in a group of tilings of equal order, this prints the classes of tilings up to renaming
of the generators, with the paper's two bounds (papers/hyperbolic_bounds.py) for one representative
of each class.  The row is identified if exactly one class has the printed range.

Usage: python papers/hyperbolic_classes.py > results/papers4/hyperbolic/classes_check.txt
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hyperbolic as H
import hyperbolic_bounds as B

def canon(gs):
    idx, order = {0: 0}, [0]
    for g in order:
        for p in gs:
            h = p[g]
            if h not in idx:
                idx[h] = len(order); order.append(h)
    return tuple(tuple(idx[p[g]] for g in order) for p in gs)

def classes(tag, N, orders):
    perms = [p for p in itertools.permutations(range(3))]
    # pair orders: (ab, bc, ca) -> indices of the generator pairs
    pairs = [(0, 1), (1, 2), (2, 0)]
    keep = []
    for p in perms:
        new = [orders[[frozenset(q) for q in pairs].index(frozenset((p.index(x), p.index(y))))] for x, y in pairs]
        if tuple(new) == tuple(orders):
            keep.append(p)
    reps = {}
    for name, t in H.TILINGS.items():
        if name.startswith("lins" + tag + "_") and t.N == N:
            key = min(canon([t.generators[i] for i in p]) for p in keep)
            reps.setdefault(key, []).append(int(name.rsplit("_", 1)[1]))
    return sorted(sorted(v) for v in reps.values())

for tag, N, orders, L, used, paper in (("444", 128, (4, 4, 4), 4, 58, "20-24"), ("444", 336, (4, 4, 4), 4, 96, "26-28"),
                                       ("444", 1344, (4, 4, 4), 2, 271, "18-20"), ("666", 432, (6, 6, 6), 4, 445, "20-24"),
                                       ("446", 768, (4, 4, 6), 4, 211, "26-28"), ("446", 1320, (4, 4, 6), 4, 339, "30-32"),
                                       ("566", 1440, (5, 6, 6), 4, 130, "24-28"), ("788", 2688, (7, 8, 8), 1, 189, "6-8")):
    cls = classes(tag, N, orders)
    print("(%s) N=%d L=%d paper %s, used %d: %d classes" % (tag, N, L, paper, used, len(cls)), flush=True)
    for c in cls:
        t = H.tiling("lins%s_%d" % (tag, c[0]))
        r = B.bounds("lins%s_%d_L%d" % (tag, c[0], L))
        print("   class %s orientable=%s: d_res=%d d_string=%d%s" % (c, t.orientable, r["d_res"], r["d_string"], "   <- used" if used in c else ""), flush=True)
