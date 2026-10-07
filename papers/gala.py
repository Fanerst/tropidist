"""GALA code [[132,30,12]] of Yang, Duckering and Dua, "Designer Codes from
GALA" (arXiv:2608.07431v1), rebuilt from the paper's text.

Code (Definition 11, Table S5): cyclic group C_m (m = 11), L = 12 data blocks
(six "left", six "right"), J = 5 block rows of checks per type, lifts
F_u = x^{f_u}, G_u = x^{g_u}, u in Z_6:

  X check (i, v) acts on  left block j at v + f_{j-i}   and right block j at v + g_{j-i},
  Z check (i, v) acts on  left block j at v - g_{i-j}   and right block j at v - f_{i-j}.

Schedule (section S5.1): the paper prints only the order of the twelve
permutation/CZ layers,  F0 F3 F4 F5 F2 F1 G1 G4 G2 G5 G3 G0,  and says that X
and Z checks are measured in the same cycle, the Z ancillas meeting the data
through the inverse permutation.  The gate-level reading used here is a
reconstruction, not a published gate list:
  layer F_u:  X block i with left block i+u (via F_u);  Z block i with right block i-u (via F_u^T)
  layer G_u:  X block i with right block i+u (via G_u); Z block i with left block i-u (via G_u^T)
It reproduces H_X and H_Z, has no qubit used twice in a layer, and gives
deterministic detectors (checked when the circuit is built).

The paper's own simulations use a different, unspecified "greedy coloration"
circuit, and state no circuit-level distance (only a fitted exponent ~9.5).
Noise model here: as for the Cornucopia circuits (two-qubit depolarizing noise
after every entangling gate, flips after preparation and before measurement,
no idle noise), with CNOTs in place of CZ + Hadamards.
"""
import os
import sys

import stim

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stabcode

# size -> (f, g, (n, k, d), claimed circuit-distance bound, m, J, layer order)
CODES = {
    132: ((2, 4, 3, 6, 3, 9), (9, 2, 8, 5, 8, 7), (132, 30, 12), None, 11, 5,
          ("F0", "F3", "F4", "F5", "F2", "F1", "G1", "G4", "G2", "G5", "G3", "G0")),
}


def supports(size, order=None, mirror=False):
    """Per check, the list of (layer, data qubit) in schedule order.

    mirror=False: X and Z checks use the same label in each layer (the reading
    of the paper's prose; not a valid circuit).
    mirror=True (designed here): the Z checks use the labels in reverse order.
    With an order whose F/G pattern is a palindrome the X and Z gates of a
    layer are on different halves, and an X and a Z check cross their paired
    overlaps in the same order, so the measurements are deterministic."""
    f, g, _, _, m, J, default = CODES[size]
    order = list(order or default)
    order_z = order[::-1] if mirror else order
    xs = [[] for _ in range(J * m)]
    zs = [[] for _ in range(J * m)]
    for t in range(len(order)):
        lab, u = order[t], int(order[t][1:])
        zlab, zu = order_z[t], int(order_z[t][1:])
        for i in range(J):
            for v in range(m):
                if lab[0] == "F":
                    xs[i * m + v].append((t, ((i + u) % 6) * m + (v + f[u]) % m))
                else:
                    xs[i * m + v].append((t, (6 + (i + u) % 6) * m + (v + g[u]) % m))
                if zlab[0] == "F":
                    zs[i * m + v].append((t, (6 + (i - zu) % 6) * m + (v - f[zu]) % m))
                else:
                    zs[i * m + v].append((t, ((i - zu) % 6) * m + (v - g[zu]) % m))
    return xs, zs


def matrices(size):
    f, g, _, _, m, J, _ = CODES[size]
    n = 12 * m
    hx, hz = [], []
    for i in range(J):
        for v in range(m):
            hx.append(sum(1 << (j * m + (v + f[(j - i) % 6]) % m) for j in range(6)) |
                      sum(1 << ((6 + j) * m + (v + g[(j - i) % 6]) % m) for j in range(6)))
            hz.append(sum(1 << (j * m + (v - g[(i - j) % 6]) % m) for j in range(6)) |
                      sum(1 << ((6 + j) * m + (v - f[(i - j) % 6]) % m) for j in range(6)))
    xs, zs = supports(size)
    assert [sum(1 << d for _, d in s) for s in xs] == hx and [sum(1 << d for _, d in s) for s in zs] == hz, \
        "schedule does not reproduce the check matrices"
    return hx, hz, n


def translations(size):
    m, J = CODES[size][4], CODES[size][5]
    return [[i * m + (v + c) % m for i in range(J) for v in range(m)] for c in range(1, m)]


def build(size, basis, rounds, p=0.001, order=None, mirror=False):
    xs, zs = supports(size, order, mirror)
    hx, hz, n = matrices(size)
    lx, lz = stabcode.css_logicals(hx, hz, n)
    nx, nz = len(xs), len(zs)
    data = list(range(n))
    za = [n + i for i in range(nz)]
    xa = [n + nz + i for i in range(nx)]
    layers = []
    for t in range(len(xs[0])):
        tg, used = [], set()
        for i, s in enumerate(xs):
            d = s[t][1]
            tg += [xa[i], d]
            assert d not in used
            used.add(d)
        for i, s in enumerate(zs):
            d = s[t][1]
            tg += [d, za[i]]
            assert d not in used
            used.add(d)
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
            c.append("DETECTOR", [stim.target_rec(-n + d) for _, d in zs[i]] + [stim.target_rec(-n - nx - nz + i)],
                     (i, 0, rounds, 3))
        logs = lz
    else:
        c.append("Z_ERROR", data, p)
        c.append("MX", data)
        for i in range(nx):
            c.append("DETECTOR", [stim.target_rec(-n + d) for _, d in xs[i]] + [stim.target_rec(-n - nx + i)],
                     (i, 0, rounds, 0))
        logs = lx
    for a, v in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)      # raises if a detector is not deterministic
    return c


def four_cycles(h, n):
    """Number of 4-cycles of the Tanner graph of the rows h."""
    t = 0
    for a in range(len(h)):
        for b in range(a):
            o = bin(h[a] & h[b]).count("1")
            t += o * (o - 1) // 2
    return t


if __name__ == "__main__":
    hx, hz, n = matrices(132)
    print("n, k =", stabcode.css_parameters(hx, hz, n), "rank Hx =", stabcode.rank(hx), "Hx == Hz:", sorted(hx) == sorted(hz),
          "row weights", {bin(r).count("1") for r in hx}, "4-cycles", four_cycles(hx, n))
    for b in "ZX":
        c = build(132, b, 4)
        print(b, "circuit ok: qubits", c.num_qubits, "detectors", c.num_detectors, "observables", c.num_observables)
