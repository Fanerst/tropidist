"""A parallel depth-8 syndrome-extraction circuit for the weight-8 self-dual
bivariate bicycle codes of arXiv:2510.05211 (designed here; the paper gives none).

X check s acts on the v1 qubits s + e_a and the v2 qubits s - e_a (a = 0..3);
the Z check s has the same support.  Label (side, a), side in {L, R}.

Schedule: the X checks use an order whose side pattern is a palindrome (the
gates at layers t and 7 - t are on the same sublattice); the Z checks use
label (R, a) at layer 7 - t_X(L, a) and (L, a) at layer 7 - t_X(R, a).  Then
  - in every layer the X checks act on one sublattice and the Z checks on the
    other, so no qubit is used twice;
  - an X check and a Z check that share qubits share them in pairs, one on each
    sublattice, and the two are crossed in the same order, so the stabilisers
    are measured deterministically (checked by Stim when the circuit is built).

The order used for each code is read from results/papers2/design/sdbb<n>_parallel_order.json
(written by design_sdbb_parallel.py).  Interface as papers/cornucopia.py.
"""
import json
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import selfdual_bb
import stabcode

CODES = {c[0]: (None, None, (c[0], c[1], c[2]), None) for c in selfdual_bb.CODES}


def order_file(n):
    return os.path.join(os.path.dirname(HERE), "results", "papers2", "design", f"sdbb{n}_parallel_order.json")


def is_palindromic(order):
    return all(order[t][0] == order[7 - t][0] for t in range(4))


def supports(n, order=None):
    """Per check, the list of (layer, data qubit) for the X checks and for the Z checks."""
    if order is None:
        order = [(s[0], int(s[1:])) for s in json.load(open(order_file(n)))["order"]]
    assert is_palindromic(order)
    row = next(c for c in selfdual_bb.CODES if c[0] == n)
    T = stabcode.Torus(row[4], row[5])
    f = [(0, 0), (1, 0)] + list(row[3])
    N = T.n
    tx = {lab: t for t, lab in enumerate(order)}
    tz = {("R", a): 7 - tx[("L", a)] for a in range(4)}
    tz.update({("L", a): 7 - tx[("R", a)] for a in range(4)})

    def qubit(s, lab):
        side, a = lab
        return T.shift(s, *f[a]) if side == "L" else N + T.shift(s, -f[a][0], -f[a][1])
    xs = [sorted((tx[lab], qubit(s, lab)) for lab in tx) for s in range(N)]
    zs = [sorted((tz[lab], qubit(s, lab)) for lab in tz) for s in range(N)]
    return xs, zs, T


def translations(n):
    row = next(c for c in selfdual_bb.CODES if c[0] == n)
    return stabcode.Torus(row[4], row[5]).translations()[1:]


def build(n, basis, rounds, p=0.001, order=None):
    xs, zs, T = supports(n, order)
    nq = 2 * T.n
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
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
    # every palindromic order must give a valid circuit: test a few on the two smallest codes
    for n in (16, 40):
        cnt = 0
        for sides in ("LLRRRRLL", "LRLRRLRL", "RLLRRLLR", "RRLLLLRR"):
            Ls = [t for t in range(8) if sides[t] == "L"]
            Rs = [t for t in range(8) if sides[t] == "R"]
            for pl in itertools.islice(itertools.permutations(range(4)), 3):
                for pr in itertools.islice(itertools.permutations(range(4)), 3):
                    order = [None] * 8
                    for t, a in zip(Ls, pl):
                        order[t] = ("L", a)
                    for t, a in zip(Rs, pr):
                        order[t] = ("R", a)
                    for b in "ZX":
                        build(n, b, 3, order=order)
                    cnt += 1
        print(n, "valid deterministic circuits for", cnt, "palindromic orders (both bases)")
