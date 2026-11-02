"""Job lists of the defect study.  Gross code, the matched circuit of chip.py.

Only checks of the memory basis lower the distance: with basis Z, a dead X check removes faults (its gates and hooks) and
changes no other column, because a fault on a data qubit in its slot has the same effect on the Z detectors whether the
slot holds a gate or nothing.  So d_Z(dead_x, dead_z) >= d_Z(none, dead_z) and d_X(dead_x, dead_z) >= d_X(dead_x, none).
The lists below therefore hold the same-type problems; part v checks the inequality, and equality, on whole chips.

  a   standard schedule: perfect chip and one dead check of each type, cycles 1, 2, 3, 4, 6, 10, both bases
  b   standard schedule: every pair of dead checks of one type up to translation, 3 cycles, in the basis of that type
  c   standard schedule: random chips with m dead checks drawn from all 144 checks, 3 cycles, both same-type problems
  v   whole chips (both types dead, both bases, 3 cycles): X Z pairs and random chips, to check the reduction
"""
import json
import random
import sys


def job(dx, dz, b, c, key="gross", s=None):
    return dict(key=key, px=None if s is None else list(s[0]), pz=None if s is None else list(s[1]),
                dead_x=sorted(dx), dead_z=sorted(dz), basis=b, cycles=c)


def part_a():
    return [job(dx, dz, b, c) for c in (1, 2, 3, 4, 6, 10) for dx, dz in (((), ()), ((0,), ()), ((), (0,))) for b in "ZX"]


def part_b():
    out = []
    for j in range(1, 72):
        out.append(job((), (0, j), "Z", 3))
        out.append(job((0, j), (), "X", 3))
    return out


def random_chip(rng, m):
    picks = rng.sample(range(144), m)
    return sorted(i for i in picks if i < 72), sorted(i - 72 for i in picks if i >= 72)


def chips(ms, n, seed=20261101):
    rng = random.Random(seed)
    return [(m,) + random_chip(rng, m) for m in ms for _ in range(n)]


def part_c(ms, n):
    out, seen = [], set()
    for _, dx, dz in chips(ms, n):
        for j in (job((), dz, "Z", 3), job(dx, (), "X", 3)):
            if (j["dead_x"] or j["dead_z"]) and json.dumps(j) not in seen:
                seen.add(json.dumps(j))
                out.append(j)
    return out


def part_v(n=40, seed=7):
    rng = random.Random(seed)
    out = [job((0,), (j,), b, 3) for j in rng.sample(range(72), 12) for b in "ZX"]
    for m in (3, 5):
        for _ in range(n // 4):
            dx, dz = random_chip(rng, m)
            if dx and dz:
                out += [job(dx, dz, b, 3) for b in "ZX"]
    return out


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "a":
        jobs = part_a()
    elif which == "b":
        jobs = part_b()
    elif which == "c":
        jobs = part_c([int(x) for x in sys.argv[2].split(",")], int(sys.argv[3]))
    elif which == "v":
        jobs = part_v()
    for j in jobs:
        print(json.dumps(j))
