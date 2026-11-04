"""The covering bound must not change the set of enumerated solutions
(minimum and non-minimum), here on the BB144 collapsed problem up to d + 2."""
import os
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from cdist import lift, problem, symmetry


def main(circuit="bb144_r12_Z", kmax=11):
    full = problem.load_dem_problem(os.path.join(ROOT, "circuits", circuit + ".stim"))
    c = problem.collapse_time(problem.sector_problem(full))
    sym = symmetry.translations(c)
    for K in range(8, kmax + 1):
        out = []
        for cover in (False, True):
            t = time.time()
            sols, st = lift.enumerate_solutions(c, K, k_table=3, rank=sym["rank"], anchors=sym["anchors"],
                                                colmaps=sym["colmaps"], cover=cover)
            out.append((sols, st["nodes"], time.time() - t))
        assert out[0][0] == out[1][0], (K, len(out[0][0]), len(out[1][0]))
        by_w = {}
        for s in out[0][0]:
            by_w[len(s)] = by_w.get(len(s), 0) + 1
        print(f"K={K}: {len(out[0][0])} solutions {dict(sorted(by_w.items()))} identical; nodes {out[0][1]:.3g} -> "
              f"{out[1][1]:.3g}; {out[0][2]:.1f}s -> {out[1][2]:.1f}s")
    print("ok")


if __name__ == "__main__":
    main(*sys.argv[1:])
