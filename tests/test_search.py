"""Check the weight-bounded search against exhaustive enumeration."""
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cdist import search
from cdist.problem import Problem, dedupe


def brute_all(h, l):
    """Minimum weight and all minimum-weight solutions (any nonzero logical)."""
    n = len(h)
    for w in range(1, n + 1):
        sols = []
        for sup in itertools.combinations(range(n), w):
            s = 0
            lg = 0
            for j in sup:
                s ^= h[j]
                lg ^= l[j]
            if s == 0 and lg != 0:
                sols.append(sup)
        if sols:
            return w, sorted(sols)
    return None, []


def main(trials=1500, seed=3):
    rng = random.Random(seed)
    stats = {"feasible": 0, "max_d": 0}
    for t in range(trials):
        m = rng.randint(2, 10)
        n = rng.randint(2, 16)
        k = rng.randint(1, 3)
        h = [sum(1 << i for i in range(m) if rng.random() < rng.choice([0.2, 0.35])) for _ in range(n)]
        l = [sum(1 << i for i in range(k) if rng.random() < 0.3) for _ in range(n)]
        h, l, _ = dedupe(h, l)
        if not h:
            continue
        p = Problem("rand", m, k, h, l, [()] * m)
        want, wsols = brute_all(h, l)
        for kt in (1, 2, 3):
            for ex in (False, True):
                r = search.distance(p, k_table=kt, kmax=len(h), enum_all=True, exclusions=ex)
                assert r["distance"] == want, (t, kt, ex, want, r["distance"])
                if want is not None:
                    assert r["solutions"] == wsols, (t, kt, ex, len(wsols), len(r["solutions"]))
                    assert r["lower_bound"] == want
        if want is not None:
            stats["feasible"] += 1
            stats["max_d"] = max(stats["max_d"], want)
    print(f"ok: {trials} random problems x 3 table sizes; {stats}")


def test_wide(trials=500, seed=9):
    """More than 16 observables: wide tables (full 64-bit logical labels) and
    the observable-group split must both agree with brute force."""
    from cdist import problem as prob
    rng = random.Random(seed)
    n_feas = 0
    for t in range(trials):
        m = rng.randint(2, 9)
        n = rng.randint(3, 15)
        k = rng.randint(17, 64)
        h = [sum(1 << i for i in range(m) if rng.random() < rng.choice([0.2, 0.35])) for _ in range(n)]
        # sparse labels placed mostly in high bits, so the low 16 bits alone cannot tell them apart
        l = [sum(1 << rng.randrange(16, k) for _ in range(rng.randint(0, 2))) for _ in range(n)]
        h, l, _ = dedupe(h, l)
        if not h:
            continue
        p = Problem("rand", m, k, h, l, [()] * m)
        want, wsols = brute_all(h, l)
        for kt in (1, 2, 3):
            r = search.distance(p, k_table=kt, kmax=len(h), enum_all=True)
            assert r["distance"] == want, (t, kt, want, r["distance"])
            if want is not None:
                assert r["solutions"] == wsols, (t, kt, len(wsols), len(r["solutions"]))
        groups = prob.observable_groups(p, 16)
        ds = [search.distance(g, k_table=2, kmax=len(h))["distance"] for g in groups]
        ds = [d for d in ds if d is not None]
        assert (min(ds) if ds else None) == want, (t, want, ds)
        n_feas += want is not None
    print(f"ok: {trials} random problems with 17-64 observables (wide tables and group split); {n_feas} feasible")


if __name__ == "__main__":
    main()
    test_wide()
