"""Tropical TN contraction vs brute force on random small problems."""
import itertools, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import tn


def brute(h, l, obs_mask):
    n = len(h)
    for w in range(1, n + 1):
        for sup in itertools.combinations(range(n), w):
            s = 0; lg = 0
            for j in sup:
                s ^= h[j]; lg ^= l[j]
            if s == 0 and bin(lg & obs_mask).count("1") & 1:
                return w
    return None


def main(trials=800, seed=11):
    rng = random.Random(seed)
    feas = 0
    for t in range(trials):
        m = rng.randint(1, 8); n = rng.randint(1, 13); k = rng.randint(1, 3)
        h = [sum(1 << i for i in range(m) if rng.random() < 0.3) for _ in range(n)]
        l = [sum(1 << i for i in range(k) if rng.random() < 0.3) for _ in range(n)]
        om = rng.randrange(1, 1 << k)
        want = brute(h, l, om)
        got, _ = tn.tropical_contract(h, l, om, m)
        assert got == want, (t, want, got)
        co = list(range(n)); rng.shuffle(co)
        got2, _ = tn.tropical_contract(h, l, om, m, col_order=co)
        assert got2 == want, (t, want, got2)
        feas += want is not None
    print(f"ok: tropical TN == brute force on {trials} random problems ({feas} feasible)")


if __name__ == "__main__":
    main()
