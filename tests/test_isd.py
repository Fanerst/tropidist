"""Information-set search: anything it returns must be a genuine solution and
never lighter than the true minimum; on small problems it should find the minimum."""
import itertools, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import isd
from cdist.problem import Problem, dedupe


def brute(h, l):
    n = len(h)
    for w in range(1, n + 1):
        for sup in itertools.combinations(range(n), w):
            s = 0; lg = 0
            for j in sup:
                s ^= h[j]; lg ^= l[j]
            if s == 0 and lg != 0:
                return w
    return None


def main(trials=200, seed=2):
    rng = random.Random(seed)
    exact = tot = 0
    for t in range(trials):
        m = rng.randint(3, 9); n = rng.randint(4, 15); k = rng.randint(1, 150)
        h = [sum(1 << i for i in range(m) if rng.random() < 0.3) for _ in range(n)]
        l = [sum(1 << rng.randrange(k) for _ in range(rng.randint(0, 2))) for _ in range(n)]
        h, l, _ = dedupe(h, l)
        if len(h) < 3:
            continue
        P = Problem("p", m, k, h, l, [()] * m)
        want = brute(h, l)
        w, sol = isd.search(P, time_limit=0.05, seed=t + 1)     # verify() is asserted inside
        tot += 1
        assert w is None or (want is not None and w >= want), (t, want, w)
        exact += (w == want)
    assert exact >= 0.95 * tot
    print(f"ok: information-set search returned only valid solutions on {tot} problems; exact minimum in {exact}")


if __name__ == "__main__":
    main()
