"""Bivariate-bicycle surface (BBS) codes of arXiv:2606.08771 (R. Wang and L. P. Pryadko,
"Algebra of Bivariate-Bicycle Surface Codes"): every finite instance of Table II (Appendix I)
and of the worked examples, built with the paper's Algorithm 1.  Reading note: papers/new/2606.08771.md.

Lattice convention (Sec. II E, Eq. (12), Fig. 1; Sec. III, Eqs. (18)-(19)).  Binary Laurent polynomials a, b are
lists of exponent pairs.  Vertices carry the X checks, plaquettes the Z checks, and the qubits sit on
horizontal edges h(i,j) (drawn at (i+1/2, j)) and vertical edges v(i,j) (drawn at (i, j+1/2)):
  X at vertex p:     h(p - s) for s in a,   v(p - s) for s in b     (H_X = [A | B])
  Z at plaquette p:  h(p + s) for s in b,   v(p + s) for s in a     (H_Z^T = [B ; A])
Figs. 1, 2, 3, 5, 6, 7 of the paper are drawn in exactly this convention.

Algorithm 1 (Sec. V), with the strips of Eqs. (46')/(48') and the qubit sets "in practice" below them:
  R1 (smooth): horizontal edges with 0 <= m1.(i,j) < L1, plus the vertical edges of the plaquettes
               whose horizontal edges all lie in R1;
  R2 (rough):  horizontal edges with 0 <= m2.(i,j) < L2, plus the vertical edges of the vertices
               whose horizontal edges all lie in R2.
  Step 1: S1X = every vertex touching R1, truncated to R1; S1Z = plaquettes inside R1.
  Step 2: S2Z = S1Z truncated to R1 n R2; S2X = elements of S1X supported in R1 n R2 (true shortening,
          by elimination over a window of uncut generators extending `buf` beyond R2).
  Step 3: drop the qubits outside supp(S2X) n supp(S2Z).
Rectangular ("regular") codes: m1 = (0,1), m2 = (1,0), so L1 = L_y and L2 = L_x of Statement 7;
Examples 5 and 6 (n = 292 at L_x=8, L_y=19 and n = 314 at L_x=19, L_y=8, with 75+60 Z and 84+60+1 X
generators) fix this orientation.  Rotated codes: m1 = (1,1), m2 = (1,-1); the text says
m2 = (-1,1), which defines a strip with the other parity.  Of eight such conventions only this one gives
the paper's (n, k) for all 40 rotated rows of Table II (the others miss 4 to 7 rows).

Table II gives n_min, k, d and the polynomials but not L1, L2.  SIZES lists every (L1, L2) with
L1, L2 <= 30 that reproduces the paper's n and k exactly (no two are equivalent codes); the first entry
is the default instance, chosen as the size with the largest Statement-7 lower bound
min(L1/D1, L2/D2) (D = largest spread of a, b across the strip), ties to the more balanced and then
the larger L1.  instances(alternates=True) also returns the other sizes.

Distances: the paper computes all distances with vecdec (Sec. V D), a randomized search, so every d here
is an upper bound ("upper").  The paper has no syndrome circuits and no circuit distances.
"""
from __future__ import annotations

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import planar_common  # noqa: E402
import stabcode  # noqa: E402

ARXIV = "2606.08771"
FAMILY = "bivariate-bicycle surface (BBS) codes"
RECT = ((0, 1), (1, 0))      # (smooth normal m1, rough normal m2)
ROT = ((1, 1), (1, -1))
VECDEC = ("vecdec (Sec. V D: all distances computed with the vecdec package, a randomized search; "
          "no trial counts are given)")

_TERM = re.compile(r"^(?:x(?:\^\{?(-?\d+)\}?)?)?(?:y(?:\^\{?(-?\d+)\}?)?)?$")


def parse_poly(s):
    """'1+xy^{-3}+x^2y' -> [(0, 0), (1, -3), (2, 1)] (binary Laurent polynomial)."""
    out = []
    for t in s.replace(" ", "").split("+"):
        if t == "1":
            out.append((0, 0))
            continue
        m = _TERM.match(t)
        if not t or not m:
            raise ValueError("cannot parse monomial %r" % t)
        i = (int(m.group(1)) if m.group(1) else 1) if t.startswith("x") else 0
        j = (int(m.group(2)) if m.group(2) else 1) if "y" in t else 0
        out.append((i, j))
    if len(set(out)) != len(out):
        raise ValueError("repeated monomial in %r" % s)
    return out


def _dot(m, p):
    return m[0] * p[0] + m[1] * p[1]


def _points(m1, s_lo, s_hi, m2, t_lo, t_hi):
    """Integer points p with s_lo <= m1.p < s_hi and t_lo <= m2.p < t_hi."""
    det = m1[0] * m2[1] - m1[1] * m2[0]
    out = []
    for s in range(s_lo, s_hi):
        for t in range(t_lo, t_hi):
            x, y = m2[1] * s - m1[1] * t, -m2[0] * s + m1[0] * t
            if x % det == 0 and y % det == 0:
                out.append((x // det, y // det))
    return out


def _weight(r):
    return bin(r).count("1")


def bbs_code(a, b, m1, L1, m2, L2, mode="alg1", buf=None):
    """Algorithm 1 (mode 'alg1') or the tile construction of Sec. V B (mode 'tile': X checks are the
    vertices whose edges all lie in R2, truncated to R1).  Returns qubits [('h'|'v', (i, j))], hx, hz
    (int bitmasks), xy, and info.  hx = truncated vertex checks followed by the extra elements of the
    shortened group (info['extra'] of them, weight-reduced greedily)."""
    D = max(abs(_dot(m, s)) for m in (m1, m2) for s in a + b) + 1
    if buf is None:
        buf = L1 + L2 + 4 * D

    def r1h(p):
        return 0 <= _dot(m1, p) < L1

    def r2h(p):
        return 0 <= _dot(m2, p) < L2

    def r1v(v):
        return any(all(r1h((v[0] - s[0] + u[0], v[1] - s[1] + u[1])) for u in b) for s in a)

    def r2v(v):
        return any(all(r2h((v[0] + s[0] - u[0], v[1] + s[1] - u[1])) for u in a) for s in b)

    near = _points(m1, -3 * D, L1 + 3 * D, m2, -3 * D, L2 + 3 * D)
    q0 = sorted([("h", p) for p in near if r1h(p) and r2h(p)] + [("v", p) for p in near if r1v(p) and r2v(p)],
                key=lambda q: (q[1][1], q[1][0], q[0]))
    q0set = set(q0)

    zsup = []
    for g in near:
        if all(r1h((g[0] + u[0], g[1] + u[1])) for u in b):
            supp = [("h", (g[0] + u[0], g[1] + u[1])) for u in b] + [("v", (g[0] + s[0], g[1] + s[1])) for s in a]
            sup = [q for q in supp if q in q0set]
            if sup:
                zsup.append(sup)

    xsup, extra = [], []
    if mode == "tile":
        for v in near:
            if all(r2h((v[0] - s[0], v[1] - s[1])) for s in a):
                supp = [("h", (v[0] - s[0], v[1] - s[1])) for s in a] + [("v", (v[0] - s[0], v[1] - s[1])) for s in b]
                sup = [q for q in supp if q in q0set]
                if sup:
                    xsup.append(sup)
    elif mode == "alg1":
        win = _points(m1, -2 * D, L1 + 2 * D, m2, -buf, L2 + buf)
        win.sort(key=lambda v: (_dot(m2, v), _dot(m1, v)))
        gens = []
        for v in win:
            sup = [("h", (v[0] - s[0], v[1] - s[1])) for s in a if r1h((v[0] - s[0], v[1] - s[1]))] + \
                  [("v", (v[0] - s[0], v[1] - s[1])) for s in b if r1v((v[0] - s[0], v[1] - s[1]))]
            if sup:
                gens.append(sup)
        n0 = len(q0)
        col = {q: i for i, q in enumerate(q0)}
        for q in sorted({q for sup in gens for q in sup if q not in q0set},
                        key=lambda q: (_dot(m2, q[1]), _dot(m1, q[1]), q[0])):
            col[q] = len(col)
        simple, basis = [], {}
        for sup in gens:
            r = 0
            for q in sup:
                r ^= 1 << col[q]
            if r >> n0 == 0:          # truncated vertex check inside R1 n R2
                xsup.append(sup)
                simple.append(r)
                continue
            while r:                  # forward elimination, outside columns first
                p = r.bit_length() - 1
                if p in basis:
                    r ^= basis[p]
                else:
                    basis[p] = r
                    break
        span = {}

        def insert(r):
            while r:
                p = r.bit_length() - 1
                if p in span:
                    r ^= span[p]
                else:
                    span[p] = r
                    return True
            return False
        for r in simple:
            insert(r)
        for p in sorted(basis):
            if p < n0 and insert(basis[p]):
                e = basis[p]
                improved = True
                while improved:       # greedy weight reduction by the truncated checks
                    improved = False
                    for g in simple:
                        if _weight(e ^ g) < _weight(e):
                            e ^= g
                            improved = True
                extra.append([q0[i] for i in stabcode.bits(e)])
    else:
        raise ValueError(mode)

    sx = {q for sup in xsup + extra for q in sup}
    sz = {q for sup in zsup for q in sup}
    qubits = [q for q in q0 if q in sx and q in sz]
    idx = {q: i for i, q in enumerate(qubits)}

    def mask(sup):
        r = 0
        for q in sup:
            if q in idx:
                r ^= 1 << idx[q]
        return r
    hx = [r for r in (mask(s) for s in xsup + extra) if r]
    hz = [r for r in (mask(s) for s in zsup) if r]
    xy = [(p[0] + 0.5, float(p[1])) if t == "h" else (float(p[0]), p[1] + 0.5) for t, p in qubits]
    info = dict(n_region=len(q0), extra=len(extra), extra_weights=[len(e) for e in extra], buf=buf)
    return dict(qubits=qubits, hx=hx, hz=hz, xy=xy, info=info)


def _mask(code, qs):
    idx = {q: i for i, q in enumerate(code["qubits"])}
    return sum(1 << idx[q] for q in qs)


# ---------------------------------------------------------------- Appendix I, Table II
TABLE = """
6 4 42 1+y^2+xy | 1+x^2+x^3 | Yes
6 5 72 1+xy^{-3}+xy^{-1} | 1+y+xy^3 | No
6 6 72 1+xy^{-1}+x^2y | 1+xy^{-2}+x^2y^{-1} | No
6 7 112 1+xy^{-1}+x^2y | 1+xy^{-2}+x^2y^{-1} | No
6 8 128 1+xy^{-1}+x^2y | 1+xy^{-2}+x^2y^{-1} | No
6 9 160 1+xy^{-1}+x^2y | 1+xy^{-2}+x^2y^{-1} | No
6 10 180 1+xy^{-1}+x^2y | 1+xy^{-2}+x^2y^{-1} | No
6 11 216 1+xy^{-3}+xy^{-2} | 1+xy^{-1}+x^2 | Yes
6 12 247 1+x^2y^{-2}+x^2y^{-1} | 1+xy+x^2y | No
6 13 275 1+xy^2+x^2y^{-1} | 1+y^2+xy | No
7 4 52 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3y^{-2} | Yes
7 5 81 1+x^2y^{-1}+x^2y | 1+x^{-1}y^2+xy^2 | Yes
7 6 96 1+x^2y^{-2}+x^2y^{-1} | 1+xy^2+x^2y | No
7 7 126 1+x^2y^{-2}+x^2y^{-1} | 1+xy^2+x^2y | No
7 8 156 1+x^2y^{-1}+x^2y | 1+xy^2+x^2 | Yes
7 9 166 1+x+x^2y | 1+y^2+xy^{-1} | No
7 10 201 1+xy^{-2}+x^2y | 1+x+x^2y^{-1} | Yes
7 11 229 1+xy^{-1}+xy^2 | 1+y+x^2y | Yes
7 12 257 1+xy^{-1}+xy^2 | 1+xy^{-2}+x^2y^{-1} | No
7 13 294 1+xy^{-1}+xy^2 | 1+y+x^2y | Yes
8 4 50 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3y^{-1} | Yes
8 5 72 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3y^{-1} | Yes
8 6 78 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3y^{-1} | Yes
8 7 137 1+x+x^2y^2 | 1+y^2+xy^{-1} | No
8 8 144 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3y^{-1} | Yes
8 9 184 1+xy^{-1}+x^2y^2 | 1+xy^2+x^2 | No
8 10 224 1+xy^2+x^2y^{-1} | 1+y+x^2y | Yes
8 11 271 1+xy^2+x^2y^{-1} | 1+y+x^2y | Yes
8 12 288 1+x^2y^{-2}+x^2y^{-1} | 1+x+x^2y^2 | No
9 4 56 1+y^2+y^3 | 1+x^2+x^3 | Yes
9 5 98 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3 | Yes
9 6 110 1+y^2+xy^{-1} | 1+xy+x^2y^3 | No
9 7 142 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3 | Yes
9 8 178 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3 | Yes
9 9 206 1+y+xy^3 | 1+xy^{-1}+x^3 | Yes
9 10 236 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3 | Yes
9 11 250 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3 | Yes
9 12 283 1+xy^{-3}+xy^{-2} | 1+x^2y^{-1}+x^3 | Yes
10 4 65 1+y+x^2y^{-1} | 1+xy+x^3y^2 | No
10 5 102 1+y+x^2y^{-1} | 1+x^2y+x^3y^2 | No
10 6 114 1+y+x^2y^{-1} | 1+xy+x^3y^2 | No
10 7 147 1+y+x^2y^{-1} | 1+xy+x^3y^2 | No
10 8 184 1+y+x^2y^{-1} | 1+xy+x^3y^2 | No
10 9 198 1+y^3+x | 1+x^2y^{-1}+x^3 | Yes
10 10 227 1+y^3+xy^2 | 1+x^3+x^3y | Yes
10 11 277 1+y^3+xy^3 | 1+x^2y+x^3 | Yes
10 12 292 1+y^3+xy^2 | 1+x^3+x^3y | Yes
11 4 75 1+y^2+xy^{-2} | 1+x+x^3y^{-1} | Yes
11 5 115 1+y^2+xy^{-2} | 1+x^2+x^3y^{-1} | Yes
11 6 127 1+y^2+xy^{-2} | 1+xy^2+x^2y^3 | No
11 7 176 1+y^2+xy^{-2} | 1+xy^2+x^2y^3 | No
11 8 210 1+y^3+x | 1+x^2y^{-2}+x^3 | Yes
11 9 234 1+y^2+x^3y^2 | 1+x+xy^3 | Yes
11 10 285 1+y^3+x | 1+x^2y^{-2}+x^3 | Yes
12 4 77 1+y^2+xy^{-2} | 1+x+x^3 | Yes
12 5 120 1+y+x^3y^{-1} | 1+xy+x^3y^2 | No
12 6 144 1+y^2+x^3y | 1+xy^{-3}+x^2 | Yes
12 7 182 1+y+x^3y^{-1} | 1+xy+x^3y^2 | No
12 8 216 1+y+xy^{-3} | 1+xy+x^3 | Yes
12 9 260 1+y^2+x^2y^{-1} | 1+xy+x^2y^3 | No
12 10 288 1+y+x^3y^{-1} | 1+xy+x^3y^2 | No
13 4 85 1+y^2+x^2y^{-1} | 1+x+x^3y^2 | No
13 5 126 1+y^2+x^3 | 1+x^2y^{-3}+x^2 | Yes
13 6 163 1+y+x^3 | 1+xy^{-2}+xy^2 | Yes
13 7 189 1+y+x^3 | 1+xy^{-2}+xy^2 | Yes
13 8 218 1+y+x^3 | 1+xy^{-2}+xy^2 | Yes
13 9 248 1+y+x^3 | 1+xy^{-2}+xy^2 | Yes
13 10 281 1+y+x^3 | 1+xy^{-2}+xy^2 | Yes
"""

# (k, d) -> every (L1, L2), L1, L2 <= 30, giving the paper's n and k; the first one is the default.
SIZES = {
    (6, 4): [(7, 6), (10, 4)],
    (6, 5): [(12, 3), (9, 4), (18, 2), (6, 6)],
    (6, 6): [(6, 6), (9, 4), (4, 9), (12, 3), (3, 12)],
    (6, 7): [(8, 7), (7, 8), (14, 4), (4, 14)],
    (6, 8): [(8, 8), (16, 4), (4, 16)],
    (6, 9): [(8, 10), (10, 8), (16, 5), (5, 16), (20, 4), (4, 20)],
    (6, 10): [(9, 10), (10, 9), (6, 15), (15, 6), (18, 5), (5, 18), (3, 30), (30, 3)],
    (6, 11): [(12, 19), (8, 28), (18, 13), (24, 10)],
    (6, 12): [(9, 13), (6, 19)],
    (6, 13): [(14, 10), (9, 15)],
    (7, 4): [(4, 11)],
    (7, 5): [(9, 9)],
    (7, 6): [(8, 6), (6, 8), (12, 4), (4, 12), (3, 16)],
    (7, 7): [(7, 9), (9, 7), (3, 21)],
    (7, 8): [(13, 12), (12, 13), (26, 6), (6, 26)],
    (7, 9): [(12, 8), (16, 6), (6, 17)],
    (7, 10): [(14, 13)],
    (7, 11): [(17, 14), (9, 26)],
    (7, 12): [(13, 9), (9, 13), (28, 4), (4, 28)],
    (7, 13): [(19, 16), (12, 25), (28, 11)],
    (8, 4): [(5, 10), (7, 7)],
    (8, 5): [(6, 12), (8, 9), (9, 8), (4, 18), (3, 24)],
    (8, 6): [(6, 13), (7, 11), (11, 7), (3, 26)],
    (8, 7): [(11, 7), (7, 11), (20, 4)],
    (8, 8): [(9, 16), (8, 18), (11, 13), (12, 12), (6, 24), (13, 11), (16, 9), (18, 8)],
    (8, 9): [(11, 8)],
    (8, 10): [(14, 17), (16, 15), (8, 29), (28, 9)],
    (8, 11): [(15, 19), (27, 11)],
    (8, 12): [(12, 12), (16, 9), (9, 16), (18, 8), (8, 18), (24, 6), (6, 24)],
    (9, 4): [(7, 8), (8, 7)],
    (9, 5): [(9, 12), (12, 9)],
    (9, 6): [(10, 5), (22, 2)],
    (9, 7): [(11, 14), (14, 11)],
    (9, 8): [(12, 16), (16, 12)],
    (9, 9): [(16, 12), (12, 16)],
    (9, 10): [(14, 18), (12, 21), (18, 14), (21, 12)],
    (9, 11): [(14, 19), (19, 14)],
    (9, 12): [(15, 20), (20, 15)],
    (10, 4): [(5, 6)],
    (10, 5): [(6, 8)],
    (10, 6): [(6, 9)],
    (10, 7): [(7, 10), (3, 24)],
    (10, 8): [(8, 11)],
    (10, 9): [(12, 17)],
    (10, 10): [(18, 13)],
    (10, 11): [(18, 15)],
    (10, 12): [(20, 15), (27, 11)],
    (11, 4): [(6, 12)],
    (11, 5): [(8, 14), (13, 9), (4, 26)],
    (11, 6): [(11, 5), (5, 11)],
    (11, 7): [(13, 6), (19, 4), (6, 13)],
    (11, 8): [(14, 15), (15, 14), (10, 21), (21, 10), (7, 30), (30, 7)],
    (11, 9): [(19, 12)],
    (11, 10): [(15, 19), (19, 15)],
    (12, 4): [(7, 12), (11, 8)],
    (12, 5): [(6, 10), (5, 12), (4, 15), (10, 6), (3, 20)],
    (12, 6): [(12, 12), (11, 13), (13, 11), (16, 9), (9, 16), (18, 8), (8, 18), (24, 6), (6, 24)],
    (12, 7): [(7, 13), (13, 7)],
    (12, 8): [(12, 19), (9, 25), (8, 28), (18, 13), (24, 10), (27, 9)],
    (12, 9): [(13, 10), (10, 13), (26, 5), (5, 26)],
    (12, 10): [(9, 16), (12, 12), (8, 18), (16, 9), (6, 24), (18, 8), (24, 6)],
    (13, 4): [(6, 6)],
    (13, 5): [(9, 14), (7, 18), (6, 21), (14, 9)],
    (13, 6): [(13, 13), (7, 25)],
    (13, 7): [(14, 14), (15, 13), (11, 18), (7, 29)],
    (13, 8): [(15, 15), (12, 19), (10, 23)],
    (13, 9): [(16, 16), (17, 15), (23, 11)],
    (13, 10): [(17, 17)],
}

# Fig. 8 caption: the family of a = 1+y^3+xy^2, b = 1+x^3+x^3y (rotated), n -> (d, sizes).
# n = 227 and 292 are Table II rows and are not repeated here.
FIG8 = {66: (4, [(10, 7)]), 103: (5, [(12, 9), (21, 5)]), 125: (6, [(13, 10)]),
        148: (7, [(14, 11), (19, 8)]), 186: (8, [(16, 12), (27, 7)]), 198: (9, [(17, 12)]),
        278: (11, [(19, 15)])}

TABLE1 = {(6, 4), (6, 6), (7, 7), (8, 9), (8, 12)}      # rows repeated in Table I (Sec. V D)


def table_rows():
    rows = []
    for line in TABLE.strip().splitlines():
        head, b, rot = [s.strip() for s in line.split("|")]
        k, d, n, a = head.split()
        rows.append(dict(k=int(k), d=int(d), n=int(n), a=a, b=b, rotated=(rot == "Yes")))
    return rows


def _spreads(a, b, m1, m2):
    def sp(p, m):
        v = [_dot(m, s) for s in p]
        return max(v) - min(v)
    return max(sp(a, m1), sp(b, m1)), max(sp(a, m2), sp(b, m2))


def _strips(rotated, L1, L2):
    if rotated:
        return "smooth strip 0<=i+j<%d, rough strip 0<=i-j<%d" % (L1, L2)
    return "smooth strip 0<=j<%d (L_y), rough strip 0<=i<%d (L_x)" % (L1, L2)


def _instance(name, code, locator, n_paper, k_paper, dx, dz, d, d_kind, d_method, notes, **extra):
    inst = dict(name=name, family=FAMILY, arxiv=ARXIV, locator=locator, n_paper=n_paper, k_paper=k_paper,
                dx=dx, dz=dz, d=d, d_kind=d_kind, d_method=d_method,
                hx=code["hx"], hz=code["hz"], xy=code["xy"], notes=notes)
    inst.update(extra)
    if code["info"]["extra"]:
        inst["notes"] += (" The shortening (Step 2) adds %d X check(s) beyond the truncated vertex checks, "
                          "of weight %s." % (code["info"]["extra"], code["info"]["extra_weights"]))
    return inst


def _table_instances(alternates):
    out = []
    for r in table_rows():
        a, b = parse_poly(r["a"]), parse_poly(r["b"])
        m1, m2 = ROT if r["rotated"] else RECT
        D1, D2 = _spreads(a, b, m1, m2)
        sizes = SIZES[(r["k"], r["d"])]
        for i, (L1, L2) in enumerate(sizes if alternates else sizes[:1]):
            code = bbs_code(a, b, m1, L1, m2, L2)
            name = "bbs_%d_%d_%d" % (r["n"], r["k"], r["d"]) + ("" if i == 0 else "_L%dx%d" % (L1, L2))
            loc = "Appendix I, Table II, row k=%d d=%d (n_min=%d, %s)" % (
                r["k"], r["d"], r["n"], "rotated" if r["rotated"] else "regular")
            if (r["k"], r["d"]) in TABLE1:
                loc += "; also Table I (Sec. V D)"
            if r["a"] == "1+y^3+xy^2" and r["rotated"]:
                loc += "; also in the Fig. 8 family"
            others = [s for s in sizes if s != (L1, L2)]
            notes = ("Algorithm 1 (Sec. V), a = %s, b = %s, %s. Table II does not give L1, L2: %d size(s) with "
                     "L1, L2 <= 30 reproduce n and k (%s). %s Statement-7 lower bounds d_X >= L1/%d, d_Z >= L2/%d."
                     % (r["a"], r["b"], _strips(r["rotated"], L1, L2), len(sizes),
                        ", ".join("%dx%d" % s for s in sizes),
                        ("Default size (largest Statement-7 bound)%s." % ("" if not others else
                         "; the others are alternates, unresolved without distances")) if i == 0 else
                        "Alternate size; the default is %dx%d." % sizes[0], D1, D2))
            out.append(_instance(name, code, loc, r["n"], r["k"], None, None, r["d"], "upper", VECDEC, notes,
                                 a=r["a"], b=r["b"], rotated=r["rotated"], L1=L1, L2=L2,
                                 normals=dict(smooth=m1, rough=m2), primary=(i == 0), sizes=sizes))
    return out


def _example_instances(alternates):
    out = []
    ex = "not stated per example; " + VECDEC
    # Example 1, Fig. 2: conventional surface code, a = 1+x, b = 1+y (n, k read off the figure)
    a, b = parse_poly("1+x"), parse_poly("1+y")
    code = bbs_code(a, b, *RECT[:1], 4, RECT[1], 8)
    out.append(_instance("bbs_ex1_surface_53_1", code, "Example 1, Fig. 2 (Sec. IV D)", 53, 1, None, None, None,
                         "unknown", "the paper gives no distance for this illustration",
                         "Unrotated surface code drawn in Fig. 2: 4 rows of 8 horizontal edges, 3 rows of 7 vertical "
                         "edges (n = 53 counted from the figure). The paper states no parameters; as a surface code it "
                         "has d_X = 4, d_Z = 8. %s." % _strips(False, 4, 8),
                         a="1+x", b="1+y", rotated=False, L1=4, L2=8, normals=dict(smooth=RECT[0], rough=RECT[1])))
    # Example 3, Fig. 5: a = 1+x^2+xy^2, b = 1+y^2+x^2y (invalid tile pair)
    a3, b3 = parse_poly("1+x^2+xy^2"), parse_poly("1+y^2+x^2y")
    tile = bbs_code(a3, b3, RECT[0], 5, RECT[1], 5, mode="tile")
    common = dict(a="1+x^2+xy^2", b="1+y^2+x^2y", rotated=False, normals=dict(smooth=RECT[0], rough=RECT[1]))
    out.append(_instance("bbs_ex3_tile_50_8_2", tile, "Example 3, Fig. 5 (Sec. V B)", 50, 8, None, 2, 2, "upper",
                         "Fig. 5 shows a weight-2 Z codeword; " + ex,
                         "Tile construction of Refs. [29,31] on the 5x5 grid, as read by the paper: Z checks are the "
                         "plaquettes inside the horizontal strip, X checks the vertices inside the vertical strip, both "
                         "truncated to the intersection (r_X = r_Z = 21). The weight-2 Z codeword of Fig. 5 is "
                         "Z on h(0,4), v(0,3).", L1=5, L2=5, **common))
    fix = dict(tile, hz=tile["hz"] + [_mask(tile, [("h", (0, 4)), ("v", (0, 3))])])
    out.append(_instance("bbs_ex3_tilefix_50_7_3", fix, "Example 3, Fig. 5 caption (Sec. V B)", 50, 7, None, None, 3,
                         "upper", ex,
                         "The tile code with its weight-2 Z codeword Z h(0,4) v(0,3) promoted to a Z check (hatched "
                         "square of Fig. 5). Same parameters as the Algorithm-1 code bbs_ex3_50_7_3 but a different code: "
                         "Algorithm 1 instead keeps one more X check, a weight-2 truncated corner vertex.", L1=5, L2=5,
                         **common))
    for L, d in ((5, 3), (6, 4), (7, 5), (8, 6)):
        code = bbs_code(a3, b3, RECT[0], L, RECT[1], L)
        out.append(_instance("bbs_ex3_%d_7_%d" % (2 * L * L, d), code,
                             "Example 3 and Fig. 5 caption (Sec. V B)", 2 * L * L, 7, None, None, d, "upper", ex,
                             "Algorithm 1 with L_x = L_y = %d (%s)." % (L, _strips(False, L, L)), L1=L, L2=L,
                             **common))
    # Example 4, Fig. 6: a = y^2+xy+x^2y^2, b = 1+x^2+y^2; tile construction and Algorithm 1 coincide
    code = bbs_code(parse_poly("y^2+xy+x^2y^2"), parse_poly("1+x^2+y^2"), RECT[0], 5, RECT[1], 5)
    out.append(_instance("bbs_ex4_45_6_3", code, "Example 4, Fig. 6 (Sec. V B)", 45, 6, None, None, 3, "upper", ex,
                         "Algorithm 1 with L_x = L_y = 5 (%s); identical to the tile construction after dropping the "
                         "lowest row of vertical edges (5 qubits) and 3 X checks, as the paper says." % _strips(False, 5, 5),
                         a="y^2+xy+x^2y^2", b="1+x^2+y^2", rotated=False, L1=5, L2=5,
                         normals=dict(smooth=RECT[0], rough=RECT[1])))
    # Example 5, Fig. 7: the weight-4 pair of LEC Sec. IV D, L_x = 8, L_y = 19
    a5, b5 = parse_poly("y^2+xy^2+x^2+x^2y^5"), parse_poly("1+y^4+xy+xy^2")
    c5 = bbs_code(a5, b5, RECT[0], 19, RECT[1], 8)
    common = dict(a="y^2+xy^2+x^2(1+y^5)", b="1+y^4+xy(1+y)", rotated=False, L1=19, L2=8,
                  normals=dict(smooth=RECT[0], rough=RECT[1]))
    out.append(_instance("bbs_ex5_292_12_14", c5, "Example 5, Fig. 7 (Sec. V C)", 292, 12, 14, 16, 14, "upper", ex,
                         "Algorithm 1 with L_x = 8, L_y = 19 (%s): 135 Z checks (75 bulk + 60 edge) and 145 X checks "
                         "(84 bulk + 60 edge + the weight-38 'ladder', X on the horizontal edges of the two leftmost "
                         "columns, h(0..1, 0..18)), as in the paper. The pair violates the vertical edge condition "
                         "gcd(a_max(y), b_max(y)) = 1+y." % _strips(False, 19, 8), **common))
    ladder = _mask(c5, [("h", (i, j)) for i in (0, 1) for j in range(19)])
    assert ladder in c5["hx"]
    c5b = dict(c5, hx=[r for r in c5["hx"] if r != ladder], info=dict(c5["info"], extra=0, extra_weights=[]))
    out.append(_instance("bbs_ex5_noladder_292_13_6", c5b, "Example 5, Fig. 7 (Sec. V C)", 292, 13, 14, 6, 6, "upper",
                         "Fig. 7 shows the weight-6 Z codewords; " + ex,
                         "bbs_ex5_292_12_14 without the weight-38 ladder X check. Its 16 weight-6 Z codewords "
                         "Z h(0,g+1) v(1,g..g+4), g = 0..15 (sea-green tile of Fig. 7) are mutually degenerate.",
                         **common))
    c5c = dict(c5b, hz=c5["hz"] + [_mask(c5, [("h", (0, 1))] + [("v", (1, t)) for t in range(5)])])
    out.append(_instance("bbs_ex5_lec_292_12_14", c5c, "Example 5 and Fig. 7 caption (Sec. V C)", 292, 12, 14, None, 14,
                         "upper", ex,
                         "bbs_ex5_noladder_292_13_6 with the weight-6 edge Z operator Z h(0,1) v(1,0..4) promoted to a "
                         "Z check (any of the 16 gives the same group); the paper says this equals the original LEC "
                         "[[292,12,14]] code. The text gives d_X/d_Z = 14/16, the Fig. 7 caption 14/14, so dz is left "
                         "unset.", **common))
    # Example 6: the same pair with x and y swapped, L_x = 19, L_y = 8
    a6, b6 = parse_poly("x^2+x^2y+y^2+x^5y^2"), parse_poly("1+x^4+xy+x^2y")
    c6 = bbs_code(a6, b6, RECT[0], 8, RECT[1], 19)
    common = dict(a="x^2+yx^2+y^2(1+x^5)", b="1+x^4+yx(1+x)", rotated=False, L1=8, L2=19,
                  normals=dict(smooth=RECT[0], rough=RECT[1]))
    out.append(_instance("bbs_ex6_314_13_6", c6, "Example 6 (Sec. V C)", 314, 13, 6, 12, 6, "upper", ex,
                         "Algorithm 1 with L_x = 19, L_y = 8 (%s). The pair violates the horizontal edge condition "
                         "gcd(a_max(x), b_max(x)) = 1+x at the top smooth edge, leaving weight-6 X logicals "
                         "X h(c-4..c, 7) v(c-1, 8); 15 translates (c = 4..18) fit in the region, the paper says 16."
                         % _strips(False, 8, 19), **common))
    c6b = dict(c6, hx=c6["hx"] + [_mask(c6, [("h", (4 - t, 7)) for t in range(5)] + [("v", (3, 8))])])
    out.append(_instance("bbs_ex6_fixed_314_12_14", c6b, "Example 6 (Sec. V C)", 314, 12, 14, 14, 14, "upper", ex,
                         "bbs_ex6_314_13_6 with one weight-6 edge X logical, X h(0..4, 7) v(3, 8), added as an X check "
                         "(all 15 are degenerate, so the choice does not matter).", **common))
    # Fig. 4 (Sec. V A): rotated HP code, a = 1+x+x^3, b = 1+y+y^3, L = 11
    code = bbs_code(parse_poly("1+x+x^3"), parse_poly("1+y+y^3"), ROT[0], 11, ROT[1], 11)
    out.append(_instance("bbs_rhp_121_9_5", code, "Fig. 4 (Sec. V A)", 121, 9, None, None, 5, "upper", ex,
                         "Algorithm 1 with diagonal boundaries, %s; 56 X and 56 Z checks as in Fig. 4."
                         % _strips(True, 11, 11), a="1+x+x^3", b="1+y+y^3", rotated=True, L1=11, L2=11,
                         normals=dict(smooth=ROT[0], rough=ROT[1])))
    # Fig. 8: the rotated family of a = 1+y^3+xy^2, b = 1+x^3+x^3y
    a8, b8 = parse_poly("1+y^3+xy^2"), parse_poly("1+x^3+x^3y")
    for n, (d, sizes) in sorted(FIG8.items()):
        for i, (L1, L2) in enumerate(sizes if alternates else sizes[:1]):
            code = bbs_code(a8, b8, ROT[0], L1, ROT[1], L2)
            name = "bbs_fig8_%d_10_%d" % (n, d) + ("" if i == 0 else "_L%dx%d" % (L1, L2))
            notes = ("Algorithm 1, rotated, a = 1+y^3+xy^2, b = 1+x^3+x^3y, %s. L1, L2 reconstructed from n and k "
                     "(%s); the defaults of the family, 10x7, 12x9, 13x10, 14x11, 16x12, 17x12, 18x13, 19x15, 20x15 "
                     "for d = 4..12, grow monotonically." % (_strips(True, L1, L2), ", ".join("%dx%d" % s for s in sizes)))
            if n == 103:
                notes += (" Fig. 8 draws the CSS dual of this code (45 X / 48 Z checks here, 48 X / 45 Z in the "
                          "figure, which is reflected in y): swap hx and hz to get the drawn code (checked to be "
                          "isomorphic).")
            loc = "Fig. 8 (Sec. V D)" + (" caption" if n != 103 else "")
            out.append(_instance(name, code, loc, n, 10, None, None, d, "upper", ex, notes,
                                 a="1+y^3+xy^2", b="1+x^3+x^3y", rotated=True, L1=L1, L2=L2,
                                 normals=dict(smooth=ROT[0], rough=ROT[1]), primary=(i == 0), sizes=sizes))
    return out


def instances(alternates=False):
    """One instance per Table II row and per worked example; alternates=True adds the other region sizes
    that reproduce the paper's n and k (names ending in _L<L1>x<L2>)."""
    return _table_instances(alternates) + _example_instances(alternates)


if __name__ == "__main__":
    print(planar_common.summary(instances(alternates="--alternates" in sys.argv)))
