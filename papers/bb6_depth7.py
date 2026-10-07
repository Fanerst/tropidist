"""Depth-7 interleaved syndrome circuits for bivariate bicycle codes with weight-6 checks
(H_X = [A | B], H_Z = [B^T | A^T], |A| = |B| = 3), one ancilla per check: all valid
schedules, and a circuit builder for any of them.

A schedule gives each X check a time slot 0..6 for its six terms (A_i on the left block,
B_j on the right block; one slot idle) and each Z check a slot for its six terms (B_j^T on
the left block, A_i^T on the right block; one slot idle).  It is valid iff
  (1) in no slot do the X checks and the Z checks act on the same block, and
  (2) for all i, j:  [t_X(A_i) < t_Z(B_j^T)] == [t_X(B_j) < t_Z(A_i^T)]
      (X check u and Z check u + A_i + B_j share one left and one right qubit; they must be
      crossed in the same order).
Stim confirms deterministic detectors when a circuit is built.

Codes: "gross" = [[144,12,12]], "bb72" = [[72,12,6]], "bb90" = [[90,8,10]], "bb108" = [[108,8,10]].
Fault set: two-qubit depolarizing after every CNOT, single-qubit depolarizing on every idle
qubit in every layer, flips after reset and before measurement.
"""
import itertools
import json
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stabcode

# (l, m), A terms, B terms as exponent pairs of x^a y^b   (Bravyi et al., arXiv:2308.07915, Table 3)
DEFS = {
    "bb72": (((6, 6), [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)]), "", (72, 12, 6), None),
    "bb90": (((15, 3), [(9, 0), (0, 1), (0, 2)], [(0, 0), (2, 0), (7, 0)]), "", (90, 8, 10), None),
    "bb108": (((9, 6), [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)]), "", (108, 8, 10), None),
    "gross": (((12, 6), [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)]), "", (144, 12, 12), None),
}
CODES = DEFS
PREFIX = "bb6_"
# the standard schedule of arXiv:2308.07915 (Table 5), slots 0..6:  X idle in slot 0, Z idle in slot 6
#   X: A2 B2 B1 B3 A1 A3 in slots 1..6;  Z: A1 A3 B1 B2 B3 A2 in slots 0..5
STANDARD = {"X": {("L", 1): 1, ("R", 1): 2, ("R", 0): 3, ("R", 2): 4, ("L", 0): 5, ("L", 2): 6},
            "Z": {("R", 0): 0, ("R", 2): 1, ("L", 0): 2, ("L", 1): 3, ("L", 2): 4, ("R", 1): 5}}


def tag(key):
    return str(key)


def matrices(key):
    (l, m), A, B = CODES[key][0]
    return stabcode.bb_matrices(l, m, A, B)


def is_valid(tx, tz):
    """tx: {("L", i): slot of A_i, ("R", j): slot of B_j};  tz: {("L", j): slot of B_j^T, ("R", i): slot of A_i^T}."""
    for side in "LR":
        if {tx[(side, a)] for a in range(3)} & {tz[(side, a)] for a in range(3)}:
            return False
    return all((tx[("L", i)] < tz[("L", j)]) == (tx[("R", j)] < tz[("R", i)]) for i in range(3) for j in range(3))


def all_valid():
    """Every valid depth-7 schedule as (tx, tz) with labels in the order L0 L1 L2 R0 R1 R2 -> tuples of slots."""
    labs = [(s, a) for s in "LR" for a in range(3)]
    perms = list(itertools.permutations(range(7), 6))
    out = []
    for px in perms:
        tx = dict(zip(labs, px))
        xl, xr = set(px[:3]), set(px[3:])
        for pz in perms:
            if xl & set(pz[:3]) or xr & set(pz[3:]):
                continue
            if all((px[i] < pz[j]) == (px[3 + j] < pz[3 + i]) for i in range(3) for j in range(3)):
                out.append((px, pz))
    return out


def to_dicts(px, pz):
    labs = [(s, a) for s in "LR" for a in range(3)]
    return dict(zip(labs, px)), dict(zip(labs, pz))


def supports(key, schedule=None):
    tx, tz = (STANDARD["X"], STANDARD["Z"]) if schedule is None else schedule
    assert is_valid(tx, tz), "invalid schedule"
    (l, m), A, B = CODES[key][0]
    N = l * m

    def cell(i, j):
        return (i % l) * m + j % m
    xs, zs = [], []
    for i in range(l):
        for j in range(m):
            gx = [(tx[("L", a)], cell(i + A[a][0], j + A[a][1])) for a in range(3)] + \
                 [(tx[("R", a)], N + cell(i + B[a][0], j + B[a][1])) for a in range(3)]
            gz = [(tz[("L", a)], cell(i - B[a][0], j - B[a][1])) for a in range(3)] + \
                 [(tz[("R", a)], N + cell(i - A[a][0], j - A[a][1])) for a in range(3)]
            xs.append(sorted(gx))
            zs.append(sorted(gz))
    return xs, zs, N


def translations(key):
    (l, m), _, _ = CODES[key][0]
    return [[((i + di) % l) * m + (j + dj) % m for i in range(l) for j in range(m)]
            for di in range(l) for dj in range(m) if (di, dj) != (0, 0)]


def build(key, basis, rounds, p=0.001, schedule=None):
    xs, zs, N = supports(key, schedule)
    nq = 2 * N
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
    assert (hx, hz, nq) == tuple(matrices(key))
    lx, lz = stabcode.css_logicals(hx, hz, nq)
    nx, nz = len(xs), len(zs)
    data = list(range(nq))
    za = [nq + i for i in range(nz)]
    xa = [nq + nz + i for i in range(nx)]
    everything = data + za + xa
    layers = []
    for t in range(7):
        tg = []
        for i, g in enumerate(xs):
            tg += [v for tt, q in g if tt == t for v in (xa[i], q)]
        for i, g in enumerate(zs):
            tg += [v for tt, q in g if tt == t for v in (q, za[i])]
        assert len(set(tg)) == len(tg)
        layers.append(tg)
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)
    c.append("X_ERROR" if basis == "Z" else "Z_ERROR", data, p)
    c.append("TICK")
    per = nz + nx
    for t in range(rounds):
        c.append("R", za)
        c.append("X_ERROR", za, p)
        c.append("RX", xa)
        c.append("Z_ERROR", xa, p)
        c.append("DEPOLARIZE1", data, p)
        c.append("TICK")
        for tg in layers:
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, p)
            idle = sorted(set(everything) - set(tg))
            if idle:
                c.append("DEPOLARIZE1", idle, p)
            c.append("TICK")
        c.append("X_ERROR", za, p)
        c.append("M", za)
        c.append("Z_ERROR", xa, p)
        c.append("MX", xa)
        c.append("DEPOLARIZE1", data, p)
        for i in range(nz):
            cur = stim.target_rec(-per + i)
            if t == 0:
                if basis == "Z":
                    c.append("DETECTOR", [cur], (i, 0, 0, 3))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-2 * per + i)], (i, 0, t, 3))
        for i in range(nx):
            cur = stim.target_rec(-nx + i)
            if t == 0:
                if basis == "X":
                    c.append("DETECTOR", [cur], (i, 0, 0, 0))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-nx - per + i)], (i, 0, t, 0))
        c.append("TICK")
    if basis == "Z":
        c.append("X_ERROR", data, p)
        c.append("M", data)
        for i in range(nz):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in zs[i]] + [stim.target_rec(-nq - nx - nz + i)],
                     (i, 0, rounds, 3))
        logs = lz
    else:
        c.append("Z_ERROR", data, p)
        c.append("MX", data)
        for i in range(nx):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in xs[i]] + [stim.target_rec(-nq - nx + i)],
                     (i, 0, rounds, 0))
        logs = lx
    for a, v in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-nq + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)      # raises if a detector is not deterministic
    return c


if __name__ == "__main__":
    import time
    t = time.time()
    v = all_valid()
    print(len(v), "valid depth-7 schedules", f"({time.time() - t:.0f}s)")
    assert is_valid(STANDARD["X"], STANDARD["Z"])
    idle = {}
    for px, pz in v:
        k = (next(s for s in range(7) if s not in px), next(s for s in range(7) if s not in pz))
        idle[k] = idle.get(k, 0) + 1
    print("by (X idle slot, Z idle slot):", dict(sorted(idle.items())))
    for key in CODES:
        print(key, CODES[key][2], stabcode.css_parameters(*matrices(key)))
    import random
    random.seed(1)
    for px, pz in random.sample(v, 12):
        for b in "ZX":
            build("bb72", b, 3, schedule=to_dicts(px, pz))
    print("12 random valid schedules give deterministic circuits on bb72 (both bases)")
