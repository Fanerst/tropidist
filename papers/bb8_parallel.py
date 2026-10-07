"""Mirror parallel depth-8 circuits (designed here) for bivariate bicycle codes
with weight-8 checks, H_X = [A | B], H_Z = [B^T | A^T], |A| = |B| = 4: the codes
of arXiv:2609.06572, which gives no syndrome circuit.

Same construction as papers/sdbb_parallel.py.  X check u meets the L qubits
u + A_a (label (L, a)) and the R qubits u + B_a (label (R, a)) in an order whose
side pattern is a palindrome; the Z check u meets the L qubit u - B_a at layer
7 - t_X(R, a) and the R qubit u - A_a at layer 7 - t_X(L, a).  Then in every
layer the X checks act on one block and the Z checks on the other, and an X
check u and a Z check u + A_a + B_b cross on their two shared qubits in the same
order (t_X(L, a) + t_X(R, b) < 7 for both), so detectors are deterministic
(checked by Stim when the circuit is built).

Keys: 1 [[72,14,8]], 2 [[144,16,10]], 3 [[144,10,12]], 4 [[144,10,14]] (published as d >= 11),
5 [[144,6,15]] (published as d >= 15); definitions from papers/estimated_codes.py.
"""
import json
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stabcode

# key: ((l, m), A terms, B terms), source row, (n, k, d), claimed circuit distance (none published)
DEFS = {
    1: (((6, 6), [(0, 0), (4, 4), (0, 5), (1, 5)], [(0, 0), (4, 1), (1, 2), (3, 2)]), "2609.06572 Table 2 row 1", (72, 14, 8), None),
    2: (((12, 6), [(0, 0), (11, 0), (0, 5), (9, 5)], [(3, 2), (8, 2), (4, 3), (9, 3)]), "Table 1 row 1", (144, 16, 10), None),
    3: (((8, 9), [(4, 2), (1, 3), (0, 5), (5, 8)], [(0, 0), (4, 2), (2, 3), (6, 5)]), "Table 1 row 2", (144, 10, 12), None),
    4: (((12, 6), [(0, 0), (8, 1), (1, 3), (2, 5)], [(0, 0), (11, 0), (1, 1), (0, 4)]), "Table 1 row 6", (144, 10, 14), None),
    5: (((8, 9), [(0, 0), (4, 2), (0, 4), (0, 7)], [(0, 0), (2, 6), (5, 7), (7, 8)]), "Table 1 row 9", (144, 6, 15), None),
}
CODES = DEFS
PREFIX = "bb8_"


def tag(key):
    n, k, d = CODES[key][2]
    return f"{n}_{k}_{d}"


def order_file(key):
    return os.path.join(os.path.dirname(HERE), "results", "papers2", "design", f"{PREFIX}{key}_parallel_order.json")


def matrices(key):
    (l, m), A, B = CODES[key][0]
    return stabcode.bb_matrices(l, m, A, B)


def supports(key, order=None):
    if order is None:
        order = [(s[0], int(s[1:])) for s in json.load(open(order_file(key)))["order"]]
    assert all(order[t][0] == order[7 - t][0] for t in range(4)), "side pattern must be a palindrome"
    (l, m), A, B = CODES[key][0]
    N = l * m
    tx = {lab: t for t, lab in enumerate(order)}
    tz = {("R", a): 7 - tx[("L", a)] for a in range(4)}
    tz.update({("L", a): 7 - tx[("R", a)] for a in range(4)})

    def cell(i, j):
        return (i % l) * m + j % m
    xs, zs = [], []
    for i in range(l):
        for j in range(m):
            gx = [(tx[("L", a)], cell(i + A[a][0], j + A[a][1])) for a in range(4)] + \
                 [(tx[("R", a)], N + cell(i + B[a][0], j + B[a][1])) for a in range(4)]
            gz = [(tz[("L", a)], cell(i - B[a][0], j - B[a][1])) for a in range(4)] + \
                 [(tz[("R", a)], N + cell(i - A[a][0], j - A[a][1])) for a in range(4)]
            xs.append(sorted(gx))
            zs.append(sorted(gz))
    return xs, zs, N


def translations(key):
    (l, m), _, _ = CODES[key][0]
    return [[((i + di) % l) * m + (j + dj) % m for i in range(l) for j in range(m)]
            for di in range(l) for dj in range(m) if (di, dj) != (0, 0)]


def build(key, basis, rounds, p=0.001, order=None):
    xs, zs, N = supports(key, order)
    nq = 2 * N
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
    assert (hx, hz, nq) == tuple(matrices(key)), "schedule does not reproduce the check matrices"
    lx, lz = stabcode.css_logicals(hx, hz, nq)
    nx, nz = len(xs), len(zs)
    data = list(range(nq))
    za = [nq + i for i in range(nz)]
    xa = [nq + nz + i for i in range(nx)]
    layers = []
    for t in range(8):
        tg, used = [], set()
        for i, g in enumerate(xs):
            q = g[t][1]
            tg += [xa[i], q]
            assert q not in used
            used.add(q)
        for i, g in enumerate(zs):
            q = g[t][1]
            tg += [q, za[i]]
            assert q not in used
            used.add(q)
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
        c.append("TICK")
        for tg in layers:
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, p)
            c.append("TICK")
        c.append("X_ERROR", za, p)
        c.append("M", za)
        c.append("Z_ERROR", xa, p)
        c.append("MX", xa)
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
    import itertools
    import design_sdbb_parallel as DP
    for key in CODES:
        hx, hz, n = matrices(key)
        nk = stabcode.css_parameters(hx, hz, n)
        cnt = 0
        for order in itertools.islice(DP.palindromic_orders(), 0, 3456, 173):
            for b in "ZX":
                build(key, b, 3, order=order)
            cnt += 1
        print(key, CODES[key][2], "rebuilt", nk, "- valid deterministic circuits for", cnt, "sampled mirror orders (both bases)")
