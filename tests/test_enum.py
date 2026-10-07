"""Completeness of enumerate_solutions (all solutions up to d+3) vs brute force."""
import itertools, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cdist import lift
from cdist.problem import Problem, dedupe


def brute(h, l, W):
    out = set()
    n = len(h)
    for w in range(1, min(W, n) + 1):
        for sup in itertools.combinations(range(n), w):
            s = 0; lg = 0
            for j in sup:
                s ^= h[j]; lg ^= l[j]
            if s == 0 and lg != 0:
                out.add(sup)
    return out


def main(target=60, seed=5):
    rng = random.Random(seed)
    done = 0; with_dec = 0; tries = 0
    while done < target:
        tries += 1
        m = rng.randint(7, 11); n = rng.randint(12, 17); k = rng.randint(1, 2)
        # structured columns so that trivial triples exist: random base columns plus some pairwise sums
        base = [(sum(1 << i for i in range(m) if rng.random() < 0.3), rng.randrange(1 << k) if rng.random() < 0.4 else 0)
                for _ in range(n - 4)]
        cols = list(base)
        for _ in range(4):
            a, b = rng.sample(base, 2)
            cols.append((a[0] ^ b[0], a[1] ^ b[1]))
        h, l, _ = dedupe([c[0] for c in cols], [c[1] for c in cols])
        if len(h) < 8:
            continue
        P = Problem("p", m, k, h, l, [()] * m)
        truth_all = brute(h, l, min(len(h), 9))
        if not truth_all:
            continue
        d = min(len(s) for s in truth_all)
        if d < 4 or d + 3 > 9:
            continue
        for K in range(d, d + 4):
            want = {s for s in truth_all if len(s) <= K}
            got, st = lift.enumerate_solutions(P, K, k_table=rng.choice([1, 2, 3]))
            assert got == want, (tries, K, d, len(got), len(want))
            if K == d + 3 and st["decomposable_added"]:
                with_dec += 1
        done += 1
    print(f"ok: enumeration complete on {done} random problems with d >= 4 (K = d..d+3); "
          f"{with_dec} needed decomposable solutions")


if __name__ == "__main__":
    main()
