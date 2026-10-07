"""Stabiliser codes from check matrices: parameters, logical operators and the
code-capacity distance problem (CSS and non-CSS).

Vectors over GF(2) are Python ints (bit j = coordinate j).
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cdist.problem import Problem, dedupe  # noqa: E402


def bits(x):
    out = []
    while x:
        low = x & -x
        out.append(low.bit_length() - 1)
        x ^= low
    return out


def rows_to_ints(M):
    M = np.asarray(M) % 2
    return [sum(1 << int(j) for j in np.flatnonzero(r)) for r in M]


def rref(rows):
    """Reduced row echelon form.  Returns (basis rows, pivot bit of each)."""
    basis, pivots = [], []
    for v in rows:
        for b, p in zip(basis, pivots):
            if (v >> p) & 1:
                v ^= b
        if v:
            p = v.bit_length() - 1
            for i in range(len(basis)):
                if (basis[i] >> p) & 1:
                    basis[i] ^= v
            basis.append(v)
            pivots.append(p)
    return basis, pivots


def rank(rows):
    return len(rref(list(rows))[0])


def nullspace(rows, n):
    """Basis of { x in GF(2)^n : <r, x> = 0 for every row r }."""
    basis, pivots = rref(list(rows))
    pivset = set(pivots)
    out = []
    for f in range(n):
        if f in pivset:
            continue
        x = 1 << f
        for b, p in zip(basis, pivots):
            if (b >> f) & 1:
                x |= 1 << p
        out.append(x)
    return out


def parity(x):
    return bin(x).count("1") & 1


def css_logicals(hx, hz, n):
    """Logical operators of a CSS code: lz[i] spans ker(Hx) / rowspace(Hz) and
    lx[i] spans ker(Hz) / rowspace(Hx), with lx[i] and lz[j] anticommuting iff i == j."""
    def quotient(kernel_of, modulo):
        basis, pivots = rref(list(modulo))
        out = []
        for v in nullspace(kernel_of, n):
            for b, p in zip(basis, pivots):
                if (v >> p) & 1:
                    v ^= b
            if v:
                p = v.bit_length() - 1
                for i in range(len(basis)):
                    if (basis[i] >> p) & 1:
                        basis[i] ^= v
                basis.append(v)
                pivots.append(p)
                out.append(v)
        return out
    lz = quotient(hx, hz)
    lx = quotient(hz, hx)
    assert len(lx) == len(lz)
    # symplectic Gram-Schmidt: pair them up
    k = len(lx)
    for i in range(k):
        j = next(j for j in range(i, k) if parity(lx[i] & lz[j]))
        lz[i], lz[j] = lz[j], lz[i]
        for j in range(k):
            if j != i and parity(lx[i] & lz[j]):
                lz[j] ^= lz[i]
            if j != i and parity(lx[j] & lz[i]):
                lx[j] ^= lx[i]
    for i in range(k):
        for j in range(k):
            assert parity(lx[i] & lz[j]) == (i == j)
    return lx, lz


def css_parameters(hx, hz, n):
    for a in hx:
        for b in hz:
            assert parity(a & b) == 0, "X and Z checks do not commute"
    return n, n - rank(hx) - rank(hz)


def css_distance_problem(hx, hz, n, basis, name="css"):
    """Code-capacity problem for one error type.  basis 'Z': X errors, detected
    by the Z checks, flipping the Z logicals (the Z-basis memory); 'X': the reverse."""
    lx, lz = css_logicals(hx, hz, n)
    det, log = (hz, lz) if basis == "Z" else (hx, lx)
    h = [sum(1 << i for i, r in enumerate(det) if (r >> j) & 1) for j in range(n)]
    l = [sum(1 << i for i, r in enumerate(log) if (r >> j) & 1) for j in range(n)]
    hh, ll, cm = dedupe(h, l, [("data", j) for j in range(n)])
    return Problem(f"{name}:code:{basis}", len(det), len(log), hh, ll, [(i, 0) for i in range(len(det))], cm)


def symplectic(a, b, n):
    """Symplectic product of (x | z) vectors stored as x + (z << n)."""
    mask = (1 << n) - 1
    return parity((a & mask) & (b >> n)) ^ parity((a >> n) & (b & mask))


def stabilizer_logicals(stabs, n):
    """2k vectors (x | z) completing the stabiliser group to its centraliser,
    in symplectic pairs (out[2i], out[2i+1])."""
    mask = (1 << n) - 1
    swapped = [((s >> n) & mask) | ((s & mask) << n) for s in stabs]     # <s, v>_symp = <swap(s), v>
    cent = nullspace(swapped, 2 * n)
    basis, pivots = rref(list(stabs))
    rest = []
    for v in cent:
        for b, p in zip(basis, pivots):
            if (v >> p) & 1:
                v ^= b
        if v:
            p = v.bit_length() - 1
            for i in range(len(basis)):
                if (basis[i] >> p) & 1:
                    basis[i] ^= v
            basis.append(v)
            pivots.append(p)
            rest.append(v)
    out = []
    while rest:
        a = rest.pop(0)
        j = next(j for j, b in enumerate(rest) if symplectic(a, b, n))
        b = rest.pop(j)
        rest = [c ^ (b if symplectic(c, a, n) else 0) ^ (a if symplectic(c, b, n) else 0) for c in rest]
        out += [a, b]
    return out


def stabilizer_parameters(stabs, n):
    for i, a in enumerate(stabs):
        for b in stabs[:i]:
            assert symplectic(a, b, n) == 0, "stabilisers do not commute"
    return n, n - rank(stabs)


def stabilizer_distance_problem(stabs, n, name="stab"):
    """Code-capacity problem of a general stabiliser code: columns are X_j, Z_j
    and Y_j, every one of weight one (the depolarising distance)."""
    logs = stabilizer_logicals(stabs, n)
    h, l, meta = [], [], []
    for j in range(n):
        for tag, v in (("X", 1 << j), ("Z", 1 << (n + j)), ("Y", (1 << j) | (1 << (n + j)))):
            h.append(sum(1 << i for i, s in enumerate(stabs) if symplectic(s, v, n)))
            l.append(sum(1 << i for i, s in enumerate(logs) if symplectic(s, v, n)))
            meta.append((tag, j))
    hh, ll, cm = dedupe(h, l, meta)
    return Problem(f"{name}:code", len(stabs), len(logs), hh, ll, [(i, 0) for i in range(len(stabs))], cm)


class Torus:
    """Cells of Z^2 modulo the lattice spanned by a1 and a2 (a twisted torus).
    `index(x, y)` is the cell of the integer point (x, y); `shift(c, dx, dy)`
    the cell reached from cell c."""

    def __init__(self, a1, a2):
        (a, b), (c, d) = a1, a2
        det = a * d - b * c
        assert det != 0
        g, u, v = _egcd(b, d)
        if g < 0:
            g, u, v = -g, -u, -v
        self.h22 = g                         # (h21, h22) and (h11, 0) span the lattice
        self.h21 = u * a + v * c
        self.h11 = abs(det) // g
        self.n = self.h11 * self.h22
        self.points = [(x, y) for y in range(self.h22) for x in range(self.h11)]

    def index(self, x, y):
        q = y // self.h22
        y -= q * self.h22
        x -= q * self.h21
        return y * self.h11 + (x % self.h11)

    def shift(self, c, dx, dy):
        x, y = self.points[c]
        return self.index(x + dx, y + dy)

    def translations(self):
        """All translations as permutations of the cells."""
        return [[self.shift(c, dx, dy) for c in range(self.n)] for dx, dy in self.points]


def _egcd(a, b):
    if b == 0:
        return a, 1, 0
    g, u, v = _egcd(b, a % b)
    return g, v, u - (a // b) * v


def shift_matrix(T: Torus, P, inverse=False):
    """Rows of the cell-by-cell matrix of the polynomial P = sum x^a y^b: row c
    has ones at the cells c + (a, b)  (c - (a, b) if inverse)."""
    rows = []
    for c in range(T.n):
        v = 0
        for a, b in P:
            v ^= 1 << (T.shift(c, -a, -b) if inverse else T.shift(c, a, b))
        rows.append(v)
    return rows


def bb_matrices(l, m, A, B):
    """Bivariate bicycle check matrices on an untwisted l x m torus.  A and B are
    lists of exponent pairs (a, b) for monomials x^a y^b.  Qubit (L, i, j) has
    index i*m + j, qubit (R, i, j) has index l*m + i*m + j; check (i, j) of
    Hx = [A | B] acts on L qubits (i + a, j + b) and R qubits shifted by B;
    Hz = [B^T | A^T]."""
    N = l * m

    def mat(P, transpose):
        rows = []
        for i in range(l):
            for j in range(m):
                v = 0
                for a, b in P:
                    ii, jj = ((i - a) % l, (j - b) % m) if transpose else ((i + a) % l, (j + b) % m)
                    v ^= 1 << (ii * m + jj)
                rows.append(v)
        return rows
    a, b, at, bt = mat(A, False), mat(B, False), mat(A, True), mat(B, True)
    hx = [a[r] | (b[r] << N) for r in range(N)]
    hz = [bt[r] | (at[r] << N) for r in range(N)]
    return hx, hz, 2 * N


if __name__ == "__main__":
    # self-test on the gross code [[144,12,12]]: A = x^3 + y + y^2, B = y^3 + x + x^2
    hx, hz, n = bb_matrices(12, 6, [(3, 0), (0, 1), (0, 2)], [(0, 3), (1, 0), (2, 0)])
    print("gross code parameters", css_parameters(hx, hz, n))
    from cdist import search
    for basis in "ZX":
        p = css_distance_problem(hx, hz, n, basis)
        r = search.distance(p, k_table=3, kmax=14, cover=True)
        print(basis, "distance", r["distance"], [(x["K"], sum(x["nodes"])) for x in r["runs"][-3:]])
    # the same code as a general stabiliser code
    stabs = [x for x in hx] + [z << n for z in hz]
    print("as stabiliser code", stabilizer_parameters(stabs, n))
    # twisted torus bookkeeping: the untwisted case must reproduce bb_matrices
    T = Torus((12, 0), (0, 6))
    assert T.n == 72 and sorted(T.shift(c, 5, -7) for c in range(T.n)) == list(range(72))
    A = shift_matrix(T, [(3, 0), (0, 1), (0, 2)])
    B = shift_matrix(T, [(0, 3), (1, 0), (2, 0)])
    At = shift_matrix(T, [(3, 0), (0, 1), (0, 2)], inverse=True)
    Bt = shift_matrix(T, [(0, 3), (1, 0), (2, 0)], inverse=True)
    hx2 = [A[r] | (B[r] << 72) for r in range(72)]
    hz2 = [Bt[r] | (At[r] << 72) for r in range(72)]
    print("gross code via Torus", css_parameters(hx2, hz2, 144))
    T2 = Torus((6, 0), (2, 5))
    assert T2.n == 30 and len(set(T2.index(x, y) for x in range(-20, 20) for y in range(-20, 20))) == 30
    assert T2.index(6, 0) == T2.index(0, 0) == T2.index(2, 5) == T2.index(8, 5)
    # five-qubit code
    def pauli(s):
        x = sum(1 << i for i, c in enumerate(s) if c in "XY")
        z = sum(1 << i for i, c in enumerate(s) if c in "ZY")
        return x | (z << len(s))
    five = [pauli(s) for s in ("XZZXI", "IXZZX", "XIXZZ", "ZXIXZ")]
    print("five-qubit code", stabilizer_parameters(five, 5))
    p = stabilizer_distance_problem(five, 5)
    r = search.distance(p, k_table=1, kmax=5)
    print("five-qubit distance", r["distance"])
