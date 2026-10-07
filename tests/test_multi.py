"""More than 64 observables: grouped search vs brute force."""
import itertools, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import multi
from cdist.problem import Problem, dedupe


def brute(h, l):
    n = len(h)
    for w in range(1, n + 1):
        sols = []
        for sup in itertools.combinations(range(n), w):
            s = 0; lg = 0
            for j in sup:
                s ^= h[j]; lg ^= l[j]
            if s == 0 and lg != 0:
                sols.append(sup)
        if sols:
            return w, sorted(sols)
    return None, []


def main(trials=300, seed=4):
    rng = random.Random(seed)
    feas = 0
    for t in range(trials):
        m = rng.randint(3, 9); n = rng.randint(4, 14); k = rng.randint(65, 200)
        seen = set(); h = []; l = []
        while len(h) < n:
            a = sum(1 << i for i in range(m) if rng.random() < 0.3)
            if a == 0 or a in seen:
                if len(seen) >= (1 << m) - 1: break
                continue
            seen.add(a); h.append(a)
            l.append(sum(1 << rng.randrange(k) for _ in range(rng.randint(0, 2))))
        P = Problem("p", m, k, h, l, [()] * m)
        want, wsols = brute(h, l)
        r = multi.distance(P, k_table=rng.choice([1, 2, 3]), kmax=len(h), enum_all=True)
        assert r["distance"] == want, (t, want, r["distance"])
        if want is not None:
            assert r["solutions"] == wsols, (t, len(wsols), len(r["solutions"]))
            feas += 1
    print(f"ok: grouped search == brute force on {trials} problems with 65-200 observables ({feas} feasible)")


def test_labelfree(trials=900, seed=8):
    """Label-free search (one pass for any number of observables) against
    brute force: forced on problems with 1-64 observables, default above 64;
    with and without the covering bound, and with a relaxed label-free table."""
    from cdist import search
    from cdist.problem import project_rows
    rng = random.Random(seed)
    feas = hits = 0
    for t in range(trials):
        m = rng.randint(3, 9); n = rng.randint(4, 14)
        k = rng.choice([rng.randint(1, 3), rng.randint(17, 64), rng.randint(65, 200)])
        seen = set(); h = []; l = []
        while len(h) < n:
            a = sum(1 << i for i in range(m) if rng.random() < 0.3)
            if a == 0 or a in seen:
                if len(seen) >= (1 << m) - 1: break
                continue
            seen.add(a); h.append(a)
            l.append(sum(1 << rng.randrange(k) for _ in range(rng.randint(0, 2))))
        P = Problem("p", m, k, h, l, [()] * m)
        want, wsols = brute(h, l)
        for cover in (False, True):
            r = search.distance(P, k_table=rng.choice([1, 2, 3]), kmax=len(h), enum_all=True, labelfree=True,
                                cover=cover)
            assert r["distance"] == want, (t, want, r["distance"])
            if want is not None:
                assert r["solutions"] == wsols, (t, len(wsols), len(r["solutions"]))
            hits += sum(x["false_hits"] for x in r["runs"])
            # stop-at-first-solution mode, every table size
            for kt in (1, 2, 3, 4):
                r = search.distance(P, k_table=kt, kmax=len(h), enum_all=False, labelfree=True, cover=cover)
                assert r["distance"] == want, (t, kt, "first-solution mode", want, r["distance"])
                assert want is None or all(s in wsols for s in r["solutions"])
        # relaxed table: merge two rows (a row map, hence a relaxation)
        if m >= 4:
            groups = [[0, 1]] + [[i] for i in range(2, m)]
            Q = project_rows(P, groups, "relaxed", [()] * (m - 1))
            tab = search.Table(Q, 2, seed=5, labelfree=True)
            r = search.distance(P, k_table=2, kmax=len(h), enum_all=True, labelfree=True, relaxed=[(tab, Q.image)])
            assert r["distance"] == want and (want is None or r["solutions"] == wsols), (t, "relaxed")
            tab.free()
        feas += want is not None
    print(f"ok: label-free search == brute force on {trials} problems with 1-200 observables ({feas} feasible, "
          f"{hits} zero-logical hits rejected)")


if __name__ == "__main__":
    main()
    test_labelfree()
