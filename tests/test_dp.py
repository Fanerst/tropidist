"""Check the trellis DP against exhaustive enumeration on random small problems."""
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cdist import kernel, trellis


def brute(h, l, obs_mask):
    n = len(h)
    for w in range(1, n + 1):
        for sup in itertools.combinations(range(n), w):
            s = 0
            lg = 0
            for j in sup:
                s ^= h[j]
                lg ^= l[j]
            if s == 0 and bin(lg & obs_mask).count("1") & 1:
                return w
    return None


def random_problem(rng):
    m = rng.randint(1, 9)
    n = rng.randint(1, 14)
    k = rng.randint(1, 3)
    dens = rng.choice([0.15, 0.3, 0.5])
    h = [sum(1 << i for i in range(m) if rng.random() < dens) for _ in range(n)]
    l = [sum(1 << i for i in range(k) if rng.random() < 0.3) for _ in range(n)]
    return m, k, h, l


def main(trials=3000, seed=1):
    rng = random.Random(seed)
    n_feasible = 0
    max_bits = 0
    for t in range(trials):
        m, k, h, l = random_problem(rng)
        order = list(range(len(h)))
        rng.shuffle(order)
        obs_mask = rng.randrange(1, 1 << k)
        want = brute(h, l, obs_mask)
        plan = trellis.build_plan(h, l, obs_mask, order, m)
        got_np = kernel.run_plan_numpy(plan)
        got_c, _ = kernel.run_plan(plan)
        assert got_np == want, (t, want, got_np)
        assert got_c == want, (t, want, got_c)
        if plan.feasible:
            # active rows after column i must equal the cut rank of [H; L-row]
            # up to the extra target row
            cols = [h[j] | ((bin(l[j] & obs_mask).count("1") & 1) << m) for j in range(len(h))]
            lam = trellis.cut_profile(cols, order)
            lam_h = trellis.cut_profile(h, order)
            for i, w in enumerate(plan.widths):
                assert lam_h[i + 1] <= w <= lam_h[i + 1] + 1, (t, i, w, lam_h[i + 1])
                assert w >= lam[i + 1] - 0
            max_bits = max(max_bits, plan.peak_bits)
        n_feasible += want is not None
    print(f"ok: {trials} random problems, {n_feasible} feasible, max table bits {max_bits}")


def test_big_tables(seed=7, trials=40):
    """Exercise the blocked/parallel code paths (tables >= 128 entries)."""
    rng = random.Random(seed)
    for t in range(trials):
        m = rng.randint(10, 16)
        n = rng.randint(m + 4, m + 14)
        h = [rng.randrange(1, 1 << m) for _ in range(n)]
        l = [rng.randrange(0, 2) for _ in range(n)]
        order = list(range(n))
        plan = trellis.build_plan(h, l, 1, order, m)
        a = kernel.run_plan_numpy(plan)
        b, _ = kernel.run_plan(plan)
        assert a == b, (t, a, b)
    print(f"ok: {trials} dense problems, numpy == C")


if __name__ == "__main__":
    main()
    test_big_tables()
