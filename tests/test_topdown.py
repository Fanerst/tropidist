"""Top-down (relax, enumerate, lift with slack) vs exhaustive enumeration."""
import itertools, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import lift, problem
from cdist.problem import Problem, dedupe


def sols(h, l, W):
    out = []
    n = len(h)
    for w in range(1, min(W, n) + 1):
        for sup in itertools.combinations(range(n), w):
            s = 0; lg = 0
            for j in sup:
                s ^= h[j]; lg ^= l[j]
            if s == 0 and lg != 0:
                out.append(sup)
    return out


def main(trials=300, seed=21):
    rng = random.Random(seed)
    checked = 0
    for t in range(trials):
        m = rng.randint(3, 9); n = rng.randint(3, 11); k = rng.randint(1, 2)
        h = [sum(1 << i for i in range(m) if rng.random() < 0.3) for _ in range(n)]
        l = [sum(1 << i for i in range(k) if rng.random() < 0.3) for _ in range(n)]
        h, l, _ = dedupe(h, l)
        if len(h) < 3:
            continue
        P = Problem("p", m, k, h, l, [()] * m)
        # random relaxation: merge rows into groups, drop some
        ng = rng.randint(1, m)
        groups = [[] for _ in range(ng)]
        for r in range(m):
            if rng.random() < 0.85:
                groups[rng.randrange(ng)].append(r)
        groups = [g for g in groups if g]
        if not groups:
            continue
        R = problem.project_rows(P, groups, "r", [()] * len(groups))
        if R.ncols == 0:
            continue
        td = lift.TopDown(P, R, k_main=rng.choice([1, 2]))
        truth = sols(P.h, P.l, len(P.h))
        dP = min((len(s) for s in truth), default=None)
        Wmax = min(len(P.h), 7)
        rel = sols(R.h, R.l, Wmax)
        for W in range(1, Wmax + 1):
            best = None
            for O in rel:
                if len(O) > W:
                    continue
                r = td.lift(O, W - len(O))
                assert r["status"] in ("exhausted", "found")
                if r["best"] is not None:
                    best = r["best"] if best is None else min(best, r["best"])
            exists = dP is not None and dP <= W
            assert (best is not None) == exists, (t, W, dP, best)
            if exists:
                assert best <= W
            checked += 1
        td.table.free()
    print(f"ok: top-down decision == exhaustive truth in {checked} (problem, W) cases")


if __name__ == "__main__":
    main()
