"""Cornucopia codes of Lu, Li and Deng, "Quantum error correction at ultra-low
overhead" (arXiv:2608.02773v2), rebuilt from the paper's text: the check
matrices (Methods Eqs. 1-5 and Extended Data Tab. 1) and the 12-layer parallel
syndrome-extraction schedule (Proposition 1, Extended Data Tab. 3).

Geometry: every block has P = 3q sites (x, y) in Z_3 x Z_q, site index
u = x*q + y.  Data blocks L_0..L_5 then R_0..R_5 (qubit index block*P + u);
check blocks X_0..X_2 and Z_0..Z_2.

  X check (i, u) acts on  L_j at A_{j-i}(u)       and R_j at B_{j-i}(u),
  Z check (i, u) acts on  L_j at B_{i-j}^{-1}(u)  and R_j at A_{i-j}^{-1}(u),
  j = 0..5, subscripts mod 6.
  A_0, B_2: (x, y) -> (x+1, y+s);  A_1, B_3: (x, y) -> (2x+2, y+s);  others (x, y+s).

Schedule, layer t = 0..11:
  X checks:  A_0 A_1 A_2 A_3 A_4 A_5 | B_4 B_5 B_0 B_1 B_2 B_3      (CNOT ancilla -> data)
  Z checks:  B_3' B_2' B_1' B_0' B_5' B_4' | A_5' A_4' A_3' A_2' A_1' A_0'   (CNOT data -> ancilla)
X ancillas are prepared in |+> and measured in X, Z ancillas in |0> and Z.

Noise model of the paper: two-qubit depolarizing noise after every CNOT, a flip
after every preparation/reset and before every measurement, no idle noise.

Usage: python papers/cornucopia.py 7 Z 6 circuits/papers/cornucopia252_r6_Z.stim
"""
import os
import sys

import stim

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stabcode

# Extended Data Tab. 1: q -> (shifts of A_0..A_5, shifts of B_0..B_5), and the claimed [[n,k,d]] and d_circ bound
CODES = {
    7: ((2, 1, 1, 1, 4, 5), (5, 3, 0, 5, 2, 3), (252, 130, 6), 5),
    16: ((1, 5, 10, 12, 12, 8), (6, 12, 10, 11, 6, 3), (576, 292, 8), 8),
    25: ((23, 7, 7, 12, 19, 6), (9, 7, 11, 17, 10, 7), (900, 454, 10), 10),
    29: ((2, 22, 20, 22, 18, 6), (27, 11, 12, 18, 21, 26), (1044, 526, 12), 11),
    49: ((44, 5, 33, 25, 22, 7), (42, 38, 32, 46, 45, 29), (1764, 886, 14), 14),
    64: ((19, 54, 25, 4, 7, 51), (20, 21, 48, 14, 56, 55), (2304, 1156, 16), 16),
    79: ((6, 49, 55, 18, 40, 7), (24, 41, 78, 53, 68, 21), (2844, 1426, 18), 18),
}


def operators(q):
    """A[k], B[k] as permutations of the P sites (lists: image of each site), and their inverses."""
    sa, sb = CODES[q][0], CODES[q][1]
    P = 3 * q

    def perm(kind, s):
        out = []
        for u in range(P):
            x, y = divmod(u, q)
            if kind == "rowcol":
                x = (x + 1) % 3
            elif kind == "invert":
                x = (2 * x + 2) % 3
            out.append(x * q + (y + s) % q)
        return out

    A = [perm("rowcol" if k == 0 else "invert" if k == 1 else "col", sa[k]) for k in range(6)]
    B = [perm("rowcol" if k == 2 else "invert" if k == 3 else "col", sb[k]) for k in range(6)]

    def inv(p):
        r = [0] * len(p)
        for u, v in enumerate(p):
            r[v] = u
        return r
    return A, B, [inv(p) for p in A], [inv(p) for p in B]


def supports(q):
    """Data-qubit supports of the X and Z checks in schedule order: for each
    check, a list of 12 (layer, data qubit)."""
    A, B, Ai, Bi = operators(q)
    P = 3 * q
    xs, zs = [], []
    for i in range(3):
        for u in range(P):
            gx = []
            for t in range(12):
                if t < 6:           # A_t on L_{i+t}
                    gx.append((t, ((i + t) % 6) * P + A[t][u]))
                else:               # B_{t-2} on R_{i+t-2}
                    k = (t - 2) % 6
                    gx.append((t, (6 + (i + k) % 6) * P + B[k][u]))
            xs.append(gx)
            gz = []
            for t in range(12):
                if t < 6:           # B_{3-t}^{-1} on L_{i-(3-t)}
                    k = (3 - t) % 6
                    gz.append((t, ((i - k) % 6) * P + Bi[k][u]))
                else:               # A_{11-t}^{-1} on R_{i-(11-t)}
                    k = 11 - t
                    gz.append((t, (6 + (i - k) % 6) * P + Ai[k][u]))
            zs.append(gz)
    return xs, zs


def matrices(q):
    xs, zs = supports(q)
    n = 36 * q
    hx = [sum(1 << d for _, d in g) for g in xs]
    hz = [sum(1 << d for _, d in g) for g in zs]
    # the definition, independently of the schedule
    A, B, Ai, Bi = operators(q)
    P = 3 * q
    for i in range(3):
        for u in range(P):
            ex = sum(1 << (j * P + A[(j - i) % 6][u]) for j in range(6)) | \
                sum(1 << ((6 + j) * P + B[(j - i) % 6][u]) for j in range(6))
            ez = sum(1 << (j * P + Bi[(i - j) % 6][u]) for j in range(6)) | \
                sum(1 << ((6 + j) * P + Ai[(i - j) % 6][u]) for j in range(6))
            assert ex == hx[i * P + u] and ez == hz[i * P + u], "schedule does not reproduce the check matrices"
    return hx, hz, n


def translations(q):
    """Row permutations of the checks (same for X and Z) under y -> y + c."""
    P = 3 * q
    out = []
    for c in range(1, q):
        out.append([i * P + (u // q) * q + (u % q + c) % q for i in range(3) for u in range(P)])
    return out


def build(q, basis, rounds, p=0.001, noise="full"):
    """noise = "full": the paper's simulation model (gates, preparation/reset,
    measurement).  noise = "cx": faults after CNOT gates only, the fault set
    the authors' repository describes for its circuit-distance search."""
    full = noise == "full"
    xs, zs = supports(q)
    hx, hz, n = matrices(q)
    lx, lz = stabcode.css_logicals(hx, hz, n)
    nx, nz = len(xs), len(zs)
    data = list(range(n))
    za = [n + i for i in range(nz)]
    xa = [n + nz + i for i in range(nx)]
    layers = []
    for t in range(12):
        tg = []
        used = set()
        for i, g in enumerate(xs):
            d = g[t][1]
            tg += [xa[i], d]
            assert d not in used
            used.add(d)
        for i, g in enumerate(zs):
            d = g[t][1]
            tg += [d, za[i]]
            assert d not in used
            used.add(d)
        layers.append(tg)
    c = stim.Circuit()

    def flip(kind, qs):
        if full:
            c.append(kind, qs, p)

    if basis == "Z":
        c.append("R", data)
        flip("X_ERROR", data)
    else:
        c.append("RX", data)
        flip("Z_ERROR", data)
    c.append("TICK")
    for t in range(rounds):
        c.append("R", za)
        flip("X_ERROR", za)
        c.append("RX", xa)
        flip("Z_ERROR", xa)
        c.append("TICK")
        for tg in layers:
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, p)
            c.append("TICK")
        flip("X_ERROR", za)
        c.append("M", za)
        flip("Z_ERROR", xa)
        c.append("MX", xa)
        per = nz + nx
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
        flip("X_ERROR", data)
        c.append("M", data)
        for i in range(nz):
            recs = [stim.target_rec(-n + d) for _, d in zs[i]]
            c.append("DETECTOR", recs + [stim.target_rec(-n - nx - nz + i)], (i, 0, rounds, 3))
        logs = lz
    else:
        flip("Z_ERROR", data)
        c.append("MX", data)
        for i in range(nx):
            recs = [stim.target_rec(-n + d) for _, d in xs[i]]
            c.append("DETECTOR", recs + [stim.target_rec(-n - nx + i)], (i, 0, rounds, 0))
        logs = lx
    for a, v in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + j) for j in stabcode.bits(v)], a)
    return c


def check_code(q):
    hx, hz, n = matrices(q)
    nn, k = stabcode.css_parameters(hx, hz, n)
    assert all(bin(r).count("1") == 12 for r in hx + hz)
    colw = [sum((r >> j) & 1 for r in hx) for j in range(n)]
    assert set(colw) == {3} and {sum((r >> j) & 1 for r in hz) for j in range(n)} == {3}
    return nn, k, stabcode.rank(hx), stabcode.rank(hz)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        for q in CODES:
            print(q, CODES[q][2], "rebuilt (n, k, rank Hx, rank Hz) =", check_code(q))
    else:
        q, basis, rounds, out = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
        circ = build(q, basis, rounds)
        circ.detector_error_model(decompose_errors=False)      # raises if a detector is not deterministic
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        circ.to_file(out)
        print(out, "qubits", circ.num_qubits, "detectors", circ.num_detectors, "observables", circ.num_observables)
