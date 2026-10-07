"""Cut rank of the real (uncollapsed) sector problem under a time-ordered
sweep: columns sorted by the rounds they touch, and inside a round by the
position of their collapsed class in a low-cut-rank order of the collapsed
problem.  A heuristic upper bound on the linear rank-width.

Usage: python scripts/experiments_widths_real.py results/widths_real.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root
from cdist import ordering, problem, trellis


def main(out):
    res = {}
    for name in ["bb72_r6_Z", "bb90_r10_Z", "bb108_r10_Z", "bb144_r12_Z", "bb288_r18_Z"]:
        t = time.time()
        full = problem.load_dem_problem(f"circuits/{name}.stim")
        q = problem.sector_problem(full)
        c = problem.collapse_time(q)
        best = None
        for s in range(6):
            o = ordering.greedy_order(c.h, c.nrows, seed=s, noise=0.5 if s else 0.0)
            cost = ordering.profile_cost(trellis.cut_profile(c.h, o))
            if best is None or cost < best[0]:
                best = (cost, o)
        pos = {j: i for i, j in enumerate(best[1])}
        cls = {}
        for j, members in enumerate(c.col_meta):
            for i in members:
                cls[i] = pos[j]

        def key(i):
            a = q.h[i]
            ts = []
            while a:
                low = a & -a
                ts.append(q.row_meta[low.bit_length() - 1][2])
                a ^= low
            return (min(ts), max(ts), cls.get(i, -1), i)

        order = sorted(range(q.ncols), key=key)
        lam = trellis.cut_profile(q.h, order)
        res[name] = {"sector_rows": q.nrows, "sector_columns": q.ncols,
                     "cut_rank_time_ordered": max(lam), "collapsed_cut_rank": best[0][0],
                     "seconds": round(time.time() - t, 1)}
        print(name, res[name], flush=True)
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
