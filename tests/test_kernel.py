"""Kernel dominance pruning, the covering bound and kernel-set enumeration against brute force."""
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from cdist import search
from cdist.problem import Problem, dedupe
from test_search import brute_all


def brute_kernel(h, l, wmax):
    """Zero-syndrome, zero-logical sets of size 3..wmax with no proper subset
    of zero syndrome."""
    n = len(h)
    zero = []
    for w in range(1, wmax + 1):
        for sup in itertools.combinations(range(n), w):
            s = 0
            for j in sup:
                s ^= h[j]
            if s == 0:
                zero.append(frozenset(sup))
    out = []
    for z in zero:
        lg = 0
        for j in z:
            lg ^= l[j]
        if lg or len(z) < 3:
            continue
        if any(y < z for y in zero):
            continue
        out.append(tuple(sorted(z)))
    return sorted(out)


def main(trials=1500, seed=5):
    rng = random.Random(seed)
    n_feas = n_kernel = 0
    for t in range(trials):
        m = rng.randint(2, 9)
        n = rng.randint(3, 15)
        k = rng.randint(1, 3)
        h = [sum(1 << i for i in range(m) if rng.random() < rng.choice([0.2, 0.35])) for _ in range(n)]
        l = [sum(1 << i for i in range(k) if rng.random() < 0.3) for _ in range(n)]
        h, l, _ = dedupe(h, l)
        if len(h) < 3:
            continue
        p = Problem("rand", m, k, h, l, [()] * m)
        want, wsols = brute_all(h, l)
        ws = rng.randint(3, 6)
        S = search.Searcher(p)
        got, _ = S.kernel_sets(ws)
        bk = brute_kernel(h, l, ws)
        assert set(bk) <= set(got), (t, set(bk) - set(got))
        for s in got:
            sy, lg = p.check(s)
            assert sy == 0 and lg == 0 and len(s) <= ws
        n_kernel += len(got)
        # all zero-logical kernel sets up to ws, not only the minimal ones
        allk = set(got)
        for w in range(3, ws + 1):
            for sup in itertools.combinations(range(len(h)), w):
                sy, lg = p.check(sup)
                if sy == 0 and lg == 0:
                    allk.add(sup)
        for kern, cov in ((None, True), (None, "simple"), (got, True), (sorted(allk), "simple")):
            for kt in (1, 2, 3):
                for ex in (False, True):
                    r = search.distance(p, k_table=kt, kmax=len(h), enum_all=True, exclusions=ex, kernel=kern,
                                        cover=cov)
                    assert r["distance"] == want, (t, kt, ex, want, r["distance"])
                    if want is not None:
                        assert r["solutions"] == wsols, (t, kt, ex, len(wsols), len(r["solutions"]))
        if want is not None:
            n_feas += 1
    print(f"ok: {trials} random problems; {n_feas} feasible; {n_kernel} kernel sets checked")


def test_many_rows(trials=600, seed=17):
    """The covering bound has a second code path for more than 8 syndrome
    words (512 rows): scatter the rows of small problems over 700 positions."""
    rng = random.Random(seed)
    n_feas = pruned = 0
    for t in range(trials):
        m = rng.randint(2, 9)
        n = rng.randint(3, 15)
        k = rng.randint(1, 3)
        pos = rng.sample(range(700), m)
        h = [sum(1 << pos[i] for i in range(m) if rng.random() < rng.choice([0.2, 0.35])) for _ in range(n)]
        l = [sum(1 << i for i in range(k) if rng.random() < 0.3) for _ in range(n)]
        h, l, _ = dedupe(h, l)
        if len(h) < 3:
            continue
        p = Problem("rand", 700, k, h, l, [()] * 700)
        want, wsols = brute_all(h, l)
        for cov in (True, "simple"):
            for kt in (1, 2):
                r = search.distance(p, k_table=kt, kmax=len(h), enum_all=True, cover=cov)
                assert r["distance"] == want, (t, kt, cov, want, r["distance"])
                if want is not None:
                    assert r["solutions"] == wsols, (t, kt, cov)
                pruned += sum(x["cover_pruned"] for x in r["runs"])
        if want is not None:
            n_feas += 1
    assert pruned > 0
    print(f"ok: {trials} random problems on 700 rows; {n_feas} feasible; {pruned} nodes pruned by the covering bound")


if __name__ == "__main__":
    main()
    test_many_rows()
