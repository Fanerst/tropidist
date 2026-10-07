"""Walking Cat base syndrome circuits, arXiv:2604.19481.

Definitions: Appendix C Table 30 (starred rows), Hx=[A|B], Hz=[B^T|A^T]
as in IX.1/IX.2, and paired term orders in Table 10. Terms are numbered in
their printed polynomial order. A monomial x^a y^b maps row (i,j) to column
(i+a,j+b), modulo (ell,m); transposition reverses both exponents.

Algorithm 1 uses *bare* |+> ancillas: CX ancilla->data for X checks, CZ for
Z checks, then MX for both. The cat factories of XI/XIII are for logical
measurements, not this SEC. Data L then R occupy 0..n-1, Z ancillas n..n+N-1,
X ancillas n+N..2n-1, N=ell*m. Qubit IDs follow the transported ions, so the
ring shifts change the aligned partners without adding SWAP gates.

Noise is the Pauli restriction of III/IV.3's moving-qubit model: two-qubit
depolarization p, preparation depolarization and measurement flips p/10,
idle depolarization p/100 per computational cycle, and depolarization
p/2000 on every qubit (moving or idle) per transport step. There is one
joint transport step between successive Table 10 pairs, as Algorithm 1
lines 5-7 specify; the first alignment is a software relabeling. Loss and
leakage, and Algorithm 2's beacon/reloading/leakage gadgets, are excluded.
Table 10 does not separately state which non-gate Pauli locations were
included in its distance calculation; this adopts the paper's stated
default noise model, with that limitation recorded in the extraction notes.

Memory initialization and final destructive readout use the same p/10
single-qubit rates. All k logical operators of the memory basis are tracked.
Usage: python papers/walkingcat.py 54 Z 6 circuits/papers/walkingcat54_r6_Z.stim
"""
from __future__ import annotations

import os
import sys

import stim

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stabcode


# definition = (ell, m, ordered A monomials, ordered B monomials).
CODES = {
    102: ((51, 1, ((22, 0), (26, 0), (37, 0), (50, 0)),
           ((19, 0), (28, 0), (29, 0), (35, 0))),
          "Q102 GB8; Tables 9-10 state circuit distance 9 as an exact value.",
          (102, 22, 9), 9),
    70: ((7, 5, ((0, 2), (2, 0), (3, 0), (4, 0)),
          ((0, 1), (1, 0), (3, 0))),
         "Q70 BB7; Tables 9-10 state circuit distance 9 as an exact value.",
         (70, 6, 9), 9),
    54: ((27, 1, ((8, 0), (13, 0), (15, 0), (16, 0)),
          ((7, 0), (8, 0), (10, 0), (15, 0))),
         "Q54 GB8; code distance 10, Tables 9-10 state circuit distance 9 as an exact value.",
         (54, 2, 10), 9),
}

# Table 10: (family, X term number, Z transposed term number), one-based.
SCHEDULES = {
    102: (("B", 1, 4), ("A", 1, 2), ("A", 3, 4), ("B", 2, 3),
          ("B", 3, 2), ("A", 4, 3), ("A", 2, 1), ("B", 4, 1)),
    70: (("B", 1, 3), ("A", 1, 3), ("A", 4, 2), ("B", 2, 2),
         ("A", 3, 1), ("A", 2, 4), ("B", 3, 1)),
    54: (("B", 2, 1), ("A", 1, 4), ("B", 4, 3), ("A", 3, 2),
         ("A", 2, 3), ("B", 3, 4), ("A", 4, 1), ("B", 1, 2)),
}


def tag(key):
    return str(key)


def matrices(key):
    ell, m, a, b = CODES[key][0]
    return stabcode.bb_matrices(ell, m, a, b)


def supports(key):
    """Per-check ordered (gate layer, data qubit) lists, X checks then Z checks."""
    ell, m, a, b = CODES[key][0]
    N = ell * m
    xs, zs = [], []
    for i in range(ell):
        for j in range(m):
            xg, zg = [], []
            for layer, (family, ix, iz) in enumerate(SCHEDULES[key]):
                terms = a if family == "A" else b
                dx, dy = terms[ix - 1]
                zx, zy = terms[iz - 1]
                # Hx=[A|B], Hz=[B^T|A^T]: same-family terms
                # always touch opposite data blocks within a gate layer.
                xq = ((i + dx) % ell) * m + (j + dy) % m
                zq = ((i - zx) % ell) * m + (j - zy) % m
                xg.append((layer, xq + (N if family == "B" else 0)))
                zg.append((layer, zq + (N if family == "A" else 0)))
            xs.append(xg)
            zs.append(zg)
    return xs, zs


def translations(key):
    """All nonidentity translations of Z_ell x Z_m, same for X and Z checks."""
    ell, m, _, _ = CODES[key][0]
    return [[((i + di) % ell) * m + (j + dj) % m
             for i in range(ell) for j in range(m)]
            for di in range(ell) for dj in range(m) if (di, dj) != (0, 0)]


def build(key, basis, rounds, p=0.001):
    if basis not in ("Z", "X"):
        raise ValueError("basis must be Z or X")
    if not isinstance(rounds, int) or rounds < 1:
        raise ValueError("rounds must be a positive integer")
    if not 0 <= p <= 1:
        raise ValueError("p must lie in [0,1]")
    hx, hz, n = matrices(key)
    xs, zs = supports(key)
    lx, lz = stabcode.css_logicals(hx, hz, n)
    N = n // 2
    data = list(range(n))
    za, xa = list(range(n, n + N)), list(range(n + N, 2 * n))
    ancillas, all_qubits = za + xa, list(range(2 * n))
    c = stim.Circuit()

    def depol1(qs, rate):
        if p:
            c.append("DEPOLARIZE1", qs, rate)

    c.append("R" if basis == "Z" else "RX", data)
    depol1(data, p / 10)
    c.append("TICK")
    for t in range(rounds):
        c.append("RX", ancillas)
        depol1(ancillas, p / 10)
        depol1(data, p / 100)
        c.append("TICK")
        for layer in range(len(SCHEDULES[key])):
            if layer:
                # Algorithm 1's single composite ring-transport step.
                depol1(all_qubits, p / 2000)
                c.append("TICK")
            xt = [q for i, g in enumerate(xs) for q in (xa[i], g[layer][1])]
            zt = [q for i, g in enumerate(zs) for q in (za[i], g[layer][1])]
            assert len(set(xt + zt)) == len(xt + zt)
            c.append("CX", xt)
            c.append("CZ", zt)
            if p:
                c.append("DEPOLARIZE2", xt + zt, p)
            c.append("TICK")
        c.append("MX", ancillas, p / 10)
        depol1(data, p / 100)
        for i in range(N):
            if t or basis == "Z":
                recs = [stim.target_rec(-n + i)]
                if t:
                    recs.append(stim.target_rec(-2 * n + i))
                c.append("DETECTOR", recs, (i, 0, t, 3))
            if t or basis == "X":
                recs = [stim.target_rec(-N + i)]
                if t:
                    recs.append(stim.target_rec(-n - N + i))
                c.append("DETECTOR", recs, (i, 0, t, 0))
        c.append("TICK")
    c.append("M" if basis == "Z" else "MX", data, p / 10)
    checks, logs = (hz, lz) if basis == "Z" else (hx, lx)
    last_offset = -2 * n if basis == "Z" else -n - N
    for i, row in enumerate(checks):
        recs = [stim.target_rec(-n + d) for d in stabcode.bits(row)]
        recs.append(stim.target_rec(last_offset + i))
        c.append("DETECTOR", recs, (i, 0, rounds, 3 if basis == "Z" else 0))
    for i, row in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + d) for d in stabcode.bits(row)], i)
    return c


if __name__ == "__main__":
    if len(sys.argv) == 1:
        for key in CODES:
            print(key, "paper", CODES[key][2], "rebuilt", stabcode.css_parameters(*matrices(key)))
    else:
        key, basis, rounds, out = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
        circ = build(key, basis, rounds)
        circ.detector_error_model(decompose_errors=False)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        circ.to_file(out)
        print(out, "qubits", circ.num_qubits, "detectors", circ.num_detectors,
              "observables", circ.num_observables)
