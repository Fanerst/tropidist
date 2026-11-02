"""Share of chips usable when dead checks are accepted, memory only.  Junction counts as in Tour de gross (qubit 2 junctions, coupler 3 in series) and 864
data-check couplers: a check is dead with probability 1 - y^20 (its qubit and six couplers), a data qubit with 1 - y^2; chips with a dead data qubit are
rejected.  A chip is accepted when the live checks keep the rank of H_X and of H_Z (a test that takes microseconds)."""
import json
import math
import random
import sys

import numpy as np

sys.path[:0] = ["results/defect_study", "papers", "."]
import bb6_depth7 as B
import chip

hx, hz, _ = B.matrices("gross")
rng = random.Random(1)
N = 200000
P = {}
for m in range(0, 26):
    ok = 0
    n = N if m <= 12 else N // 4
    cache = {}
    for _ in range(n):
        picks = rng.sample(range(144), m)
        dx = frozenset(i for i in picks if i < 72)
        dz = frozenset(i - 72 for i in picks if i >= 72)
        for t, d, h in (("x", dx, hx), ("z", dz, hz)):
            if d not in cache:
                cache[d if t == "x" else ("z", d)] = None
        a = cache.get(dx)
        if a is None:
            a = chip.gf2_rank([v for i, v in enumerate(hx) if i not in dx]) == 66
            cache[dx] = a
        b = cache.get(("z", dz))
        if b is None:
            b = chip.gf2_rank([v for i, v in enumerate(hz) if i not in dz]) == 66
            cache[("z", dz)] = b
        ok += a and b
    P[m] = ok / n
    print("m", m, "rank kept %.4f" % P[m], flush=True)
    if P[m] == 0:
        break
out = {}
for y in (0.9998, 0.9995, 0.999):
    pc = 1 - y ** 20
    data = y ** (2 * 144)
    pm = [math.comb(144, m) * pc ** m * (1 - pc) ** (144 - m) for m in range(145)]
    perfect = data * pm[0]
    acc = data * sum(pm[m] * P.get(m, 0.0) for m in range(145))
    out[str(y)] = dict(per_check=pc, expected_dead=144 * pc, no_dead_data=data, perfect=perfect, accepted=acc,
                       upto=[data * sum(pm[:k + 1]) for k in range(6)], pm=pm[:8])
    print("y", y, "dead per check %.4f, expected %.2f; no dead data qubit %.3f; perfect %.3f; rank test %.3f" % (pc, 144 * pc, data, perfect, acc))
json.dump(dict(rank_kept=P, yields=out), open("results/defect_study/yield.json", "w"), indent=1)
