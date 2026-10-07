"""Pure-Python derivation of the BB72 circuit distance, sharing no search code
with the C kernels (only the DEM import and the row projections are reused).

  1. enumerate all solutions of the time-collapsed problem with weight <= 5
     by a meet-in-the-middle over column pairs and triples
  2. try to lift each of them to the real 6-round problem by trying every
     combination of class members
  3. find a weight-6 real solution among data errors before the first round

Expected: collapsed distance 5; no weight-5 solution lifts  => distance >= 6;
a weight-6 solution exists => distance = 6.
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import problem


def main():
    for name in ("bb72_r6_Z", "bb72_r6_X"):
        full = problem.load_dem_problem(f"circuits/{name}.stim")
        q = problem.sector_problem(full)
        c = problem.collapse_time(q)
        n = c.ncols
        single = {}
        for a in range(n):
            single.setdefault(c.h[a], []).append((a,))
        pair = {}
        for a, b in itertools.combinations(range(n), 2):
            pair.setdefault(c.h[a] ^ c.h[b], []).append((a, b))
        # weights 1..4 by pairs x pairs / singles
        low = None
        for w, (A, B) in ((2, (single, single)), (3, (pair, single)), (4, (pair, pair))):
            for s, la in A.items():
                for x in la:
                    for y in B.get(s, ()):
                        if set(x) & set(y):
                            continue
                        lg = 0
                        for j in x + y:
                            lg ^= c.l[j]
                        if lg:
                            low = w if low is None else min(low, w)
        assert low is None, f"collapsed solution of weight {low}"
        assert all(not (h == 0 and l) for h, l in zip(c.h, c.l))
        sols = set()
        for t in itertools.combinations(range(n), 3):
            s = c.h[t[0]] ^ c.h[t[1]] ^ c.h[t[2]]
            for (a, b) in pair.get(s, ()):
                if a in t or b in t:
                    continue
                if c.l[t[0]] ^ c.l[t[1]] ^ c.l[t[2]] ^ c.l[a] ^ c.l[b]:
                    sols.add(tuple(sorted(t + (a, b))))
        assert sols, "expected collapsed distance 5"
        lifted = 0
        for s in sols:
            cl = [c.col_meta[j] for j in s]
            left = {q.h[m0] ^ q.h[m1] for m0 in cl[0] for m1 in cl[1]}
            if any((q.h[m2] ^ q.h[m3] ^ q.h[m4]) in left for m2 in cl[2] for m3 in cl[3] for m4 in cl[4]):
                lifted += 1
        # weight-6 witness among columns touching only the first detector layer
        t0 = [j for j, a in enumerate(q.h) if all(q.row_meta[i][2] == 0 for i in range(q.nrows) if (a >> i) & 1)]
        trip = {}
        for x in itertools.combinations(t0, 3):
            trip.setdefault(q.h[x[0]] ^ q.h[x[1]] ^ q.h[x[2]], []).append(x)
        w6 = None
        for s, lst in trip.items():
            for x, y in itertools.combinations(lst, 2):
                if set(x) & set(y):
                    continue
                lg = 0
                for j in x + y:
                    lg ^= q.l[j]
                if lg:
                    w6 = x + y
                    break
            if w6:
                break
        print(f"{name}: collapsed distance 5 with {len(sols)} solutions; {lifted} lift to the 6-round circuit; "
              f"weight-6 real solution found: {w6 is not None}  => circuit distance = 6")
        assert lifted == 0 and w6 is not None


if __name__ == "__main__":
    main()
