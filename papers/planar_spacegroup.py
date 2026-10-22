"""Space-group codes of arXiv:2606.20548v3 (C.-Y. Xu, Z.-C. Liu, Y. Xu, "Topological Codes from Space
Groups: A Route beyond Translation Invariance"), with the interface of planar_common.py.
Reading note: papers/new/2606.20548.md.

instances() holds every row of Tables I, II and III and the three topological reflection-code families
of Fig. 4(a),(b) (L x L lattices, x folded, y periodic, L = 4..11).  The three non-topological families of
Fig. 4(c),(d) do not reproduce the plotted k; they are built only on request (nontopological=True).

Lattice construction (all rows but the two n = 112 ones).  Cells are the points z = (a, b) of
Z_Lx x Z_Ly (finite periodic lattice, Sec. IV F 2, Eqs. (90)-(91)); each cell holds one data qubit of
block L and one of block R.  A group element g = t_b p_rho acts by z -> rho z + b (Eqs. (26)-(27)) with
    t_x: (a, b) -> (a + 1, b)    t_y: (a, b) -> (a, b + 1)
    s_x: (a, b) -> (-a, b)       s_y: (a, b) -> (a, -b)          (Eq. (42); App. B, Eq. (B2))
and, for the n = 96 row of Table I only, s: (a, b) -> (a, -a - b) mod (24, 2) (Table I caption).
A word is a composite map, rightmost factor first (as in the paper's g(xy) = x^-1 for
g = s_x s_y t_y^-1, Sec. IV G).  The tables give f and h with H_X from (f^T, h^T) and H_Z from (h, f)
(Eq. (116)); with Gamma the permutation representation of Eq. (11), Eqs. (15) and (107) give, for every
cell p (coincident terms cancel mod 2),
    X check p:  L block f(p) = {g(p): g in f},         R block h(p)
    Z check p:  L block h^T(p) = {g^-1(p): g in h},    R block f^T(p)
which commute iff Gamma(f h + h f) = 0 on the finite lattice (Theorem III.2).  Table I's group column
(Z_Lx x Z_Ly) x| P fixes (Lx, Ly); Table II gives the shape Lx x Ly; Table III gives no shape, and the
only factorisations with commuting checks and the paper's k are 3 x 8 for [[48,4,8]] and 12 x 4 for
[[96,6,10]] (both match the tier-0 arrays of Fig. 6); the gross code is the usual 12 x 6.

The two n = 112 rows of Table I are two-block group-algebra (2BGA) codes.  (Z_7 x Z_4) x| C_s has only
28 lattice cells (n = 56, and the checks do not commute); no 56-cell lattice reproduces them either.
They are reproduced exactly (n = 112, k = 6 and 16) as 2BGA codes (Lin and Pryadko, App. A's ref. [84])
over the order-56 group G = (Z_7 x Z_4) x| <s_y> itself, qubits being the group elements:
    X check p:  L block {g p: g in f},       R block {p g: g in h}
    Z check p:  L block {p g^-1: g in h},    R block {g^-1 p: g in f}
i.e. H_X = (L(f^T) | R(h^T)), H_Z = (R(h) | L(f)) with L, R the left and right regular representations.
Other actions of C_s or the direct product do not give (6, 16).  This reading is ours; the paper does
not say these two rows use the regular representation.

Conventions that leave n, k and d = min(dx, dz) unchanged: reading words left to right, or taking
X = (f^T p | h^T p), Z = (h p | f p), gives exactly the X <-> Z dual code (checked row by row: equal
row spaces after z -> -z and a block swap); for n = 112, exchanging L and R gives the dual as well.
The paper reports d only, so dx = dz = None; which of our two problems is "X" is a convention.
Mirrors pass through the origin as defined in Eq. (42): shifting the mirror by one cell changes k for
[[24,4,4]], [[40,14,4]], [[160,26,8]] and the Fig. 4 codes.

Geometry.  Following the folded lattice of Sec. IV B (Fig. 2) and the accordion order of Sec. V
(Fig. 3(b): 1, x^7, x, x^6, x^2, x^5, x^3, x^4 for L = 8), an axis on which a reflection acts is folded:
residue a sits at accordion(a, L) in 0..L-1, mirror partners a and -a are adjacent, and the axis has
open ends; a translation by c moves a cell at most 2|c| places.  Axes without a reflection (and axes of
length <= 2, where folding changes nothing) stay periodic: fundamental-domain positions 0..L-1, period in
inst["periods"] and in notes.  The L-block qubit of a cell sits at the cell position and the R-block
qubit at +(0.5, 0.5) (cell layout of Fig. 1(b),(c)); for n = 112 the two cosets e = 0, 1 of a cell use
the four sub-sites (0,0), (.5,.5) [e=0] and (0,.5), (.5,0) [e=1].  inst["xy_open"] folds every axis
(the two-axis accordion fold of Sec. VI D): open boundaries everywhere, translation ranges doubled.
Extra keys: group, f, h, Lx, Ly, construction, geometry, periods, cells, xy_open, check_range,
check_range_open (largest per-axis offset, in cell positions, from a check's own cell to its support).
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import planar_common  # noqa: E402

ARXIV = "2606.20548"
FAMILY = "space-group codes"
FAMILY_BB = "bivariate bicycle codes"

# ----------------------------------------------------------------------------------------------
# group elements: affine maps z -> M z + t of Z^2, M = (m00, m01, m10, m11), t = (t0, t1)

IDENTITY = ((1, 0, 0, 1), (0, 0))
GENERATORS = {
    "t_x": ((1, 0, 0, 1), (1, 0)),
    "t_y": ((1, 0, 0, 1), (0, 1)),
    "s_x": ((-1, 0, 0, 1), (0, 0)),
    "s_y": ((1, 0, 0, -1), (0, 0)),
    "s": ((1, 0, -1, -1), (0, 0)),      # Table I, n = 96 row: (x, y) -> (x, -x - y)
}
_TOKEN = re.compile(r"(t_x|t_y|s_x|s_y|s)(?:\^\{?(-?\d+)\}?)?")


def compose(A, B):
    """The map A o B (B acts first)."""
    (a, b, c, d), (u, v) = A
    (e, f, g, h), (p, q) = B
    return ((a * e + b * g, a * f + b * h, c * e + d * g, c * f + d * h),
            (a * p + b * q + u, c * p + d * q + v))


def inverse(A):
    (a, b, c, d), (u, v) = A
    det = a * d - b * c
    assert det in (1, -1)
    m = (d * det, -b * det, -c * det, a * det)
    return (m, (-(m[0] * u + m[1] * v), -(m[2] * u + m[3] * v)))


def parse(tex):
    """A TeX polynomial of the paper, e.g. r"1+t_x^{13} s_y+t_xt_y^2", as a list of words, each a list
    of (generator, power)."""
    words = []
    for term in tex.replace(" ", "").split("+"):
        if term == "1":
            words.append([])
            continue
        pos, word = 0, []
        while pos < len(term):
            m = _TOKEN.match(term, pos)
            if not m:
                raise ValueError("cannot parse %r in %r" % (term[pos:], tex))
            word.append((m.group(1), int(m.group(2) or 1)))
            pos = m.end()
        words.append(word)
    return words


def element(word):
    g = IDENTITY
    for name, k in word:
        base = GENERATORS[name] if k > 0 else inverse(GENERATORS[name])
        for _ in range(abs(k)):
            g = compose(g, base)
    return g


def act(g, z, L):
    (a, b, c, d), (u, v) = g
    x, y = z
    return ((a * x + b * y + u) % L[0], (c * x + d * y + v) % L[1])


def accordion(a, L):
    """Place of residue a mod L in the folded order 0, L-1, 1, L-2, 2, ... (Sec. V, Fig. 3(b))."""
    a %= L
    if a == 0:
        return 0
    if 2 * a < L:
        return 2 * a
    if 2 * a == L:
        return L - 1
    return 2 * (L - a) - 1


# ----------------------------------------------------------------------------------------------
# codes

def lattice_code(f, h, Lx, Ly):
    """Eq. (107) on the cells of Z_Lx x Z_Ly.  Cell (a, b) has index a*Ly + b; its L-block qubit is that
    index, its R-block qubit N + index.  Row p of hx / hz is the check of cell p."""
    L, N = (Lx, Ly), Lx * Ly
    F = [element(w) for w in parse(f)]
    H = [element(w) for w in parse(h)]
    Fi, Hi = [inverse(g) for g in F], [inverse(g) for g in H]
    idx = lambda z: z[0] * Ly + z[1]  # noqa: E731
    hx, hz = [], []
    for a in range(Lx):
        for b in range(Ly):
            p = (a, b)
            x = z = 0
            for g in F:
                x ^= 1 << idx(act(g, p, L))
            for g in H:
                x ^= 1 << (N + idx(act(g, p, L)))
            for g in Hi:
                z ^= 1 << idx(act(g, p, L))
            for g in Fi:
                z ^= 1 << (N + idx(act(g, p, L)))
            hx.append(x)
            hz.append(z)
    cells = [(blk, a, b) for blk in "LR" for a in range(Lx) for b in range(Ly)]
    homes = [(a, b) for a in range(Lx) for b in range(Ly)]
    return hx, hz, cells, homes


def two_block_code(f, h, Lx, Ly):
    """2BGA code over G = (Z_Lx x Z_Ly) x| <s_y>.  Element t^(a,b) s_y^e has index (a*Ly + b)*2 + e;
    its L-block qubit is that index, its R-block qubit N + index (N = |G|).  Row p is the check of p."""
    N = 2 * Lx * Ly

    def red(g):
        m, (u, v) = g
        assert m in ((1, 0, 0, 1), (1, 0, 0, -1)), "not an element of (Z x Z) x| <s_y>"
        return (m, (u % Lx, v % Ly))

    def index(g):
        m, (u, v) = red(g)
        return (u * Ly + v) * 2 + (m[3] == -1)

    elems = [red(((1, 0, 0, 1 - 2 * e), (a, b))) for a in range(Lx) for b in range(Ly) for e in (0, 1)]
    assert [index(g) for g in elems] == list(range(N))
    F = [element(w) for w in parse(f)]
    H = [element(w) for w in parse(h)]
    Fi, Hi = [inverse(g) for g in F], [inverse(g) for g in H]
    hx, hz = [], []
    for p in elems:
        x = z = 0
        for g in F:
            x ^= 1 << index(compose(g, p))
        for g in H:
            x ^= 1 << (N + index(compose(p, g)))
        for g in Hi:
            z ^= 1 << index(compose(p, g))
        for g in Fi:
            z ^= 1 << (N + index(compose(g, p)))
        hx.append(x)
        hz.append(z)
    cells = [(blk, a, b, e) for blk in "LR" for a in range(Lx) for b in range(Ly) for e in (0, 1)]
    homes = [(a, b) for a in range(Lx) for b in range(Ly) for e in (0, 1)]
    return hx, hz, cells, homes


def folded_axes(f, h, Lx, Ly):
    """(fold x, fold y): an axis is folded when some term reflects it and it has more than 2 cells."""
    fx = fy = False
    for tex in (f, h):
        for w in parse(tex):
            (m00, m01, m10, m11), _ = element(w)
            if m01:
                assert Lx <= 2, "shear into x on a long axis"
            if m10:
                assert Ly <= 2, "shear into y on a long axis"
            fx |= m00 == -1 and Lx > 2
            fy |= m11 == -1 and Ly > 2
    return fx, fy


def _range(rows, cells, homes, pos, periods):
    """Largest per-axis offset (in cell positions) between a check's own cell and its support."""
    best = [0, 0]
    for r, home in zip(rows, homes):
        hp = pos(home)
        v = r
        while v:
            low = v & -v
            q = cells[low.bit_length() - 1]
            qp = pos((q[1], q[2]))
            for ax in (0, 1):
                d = abs(qp[ax] - hp[ax])
                if periods[ax]:
                    d = min(d, periods[ax] - d)
                best[ax] = max(best[ax], d)
            v ^= low
    return tuple(best)


def build(name, family, locator, nkd, f, h, Lx, Ly, group, d_kind, d_method, notes="",
          construction="lattice"):
    """One instance dict (n, k filled in by planar_common.check)."""
    n_p, k_p, d_p = nkd
    if construction == "lattice":
        hx, hz, cells, homes = lattice_code(f, h, Lx, Ly)
    else:
        hx, hz, cells, homes = two_block_code(f, h, Lx, Ly)
    fx, fy = folded_axes(f, h, Lx, Ly)
    periods = (None if (fx or Lx == 1) else Lx, None if (fy or Ly == 1) else Ly)

    def pos(c, fold=(fx, fy)):
        return (accordion(c[0], Lx) if fold[0] else c[0], accordion(c[1], Ly) if fold[1] else c[1])

    def pos_open(c):
        return pos(c, (True, True))

    def offset(c):
        blk = c[0] == "R"
        e = c[3] if len(c) > 3 else 0
        return (0.5 * blk, 0.5 * ((blk + e) % 2))

    xy, xy_open = [], []
    for c in cells:
        o = offset(c)
        p, q = pos((c[1], c[2])), pos_open((c[1], c[2]))
        xy.append((p[0] + o[0], p[1] + o[1]))
        xy_open.append((q[0] + o[0], q[1] + o[1]))
    rng = tuple(max(a, b) for a, b in zip(_range(hx, cells, homes, pos, periods),
                                          _range(hz, cells, homes, pos, periods)))
    rng_open = tuple(max(a, b) for a, b in zip(_range(hx, cells, homes, pos_open, (None, None)),
                                               _range(hz, cells, homes, pos_open, (None, None))))
    axis = lambda nm, L, fold, per: ("%s %s L%s=%d" % (nm, "folded (open)" if fold else  # noqa: E731
                                     ("periodic" if per else "single cell"), nm, L))
    if Ly == 1:
        geometry = "chain"
    else:
        geometry = {0: "planar", 1: "cylinder", 2: "torus"}[sum(p is not None for p in periods)]
    geo = "%s: %s; %s; check range x<=%d, y<=%d xy positions (open fold of both axes: %d, %d)" % (
        geometry, axis("x", Lx, fx, periods[0]), axis("y", Ly, fy, periods[1]),
        rng[0], rng[1], rng_open[0], rng_open[1])
    if geometry == "torus":
        geo += "; torus Lx=%d Ly=%d" % (Lx, Ly)
    elif geometry == "cylinder":
        geo += "; periodic %s with period %d" % (("x", Lx) if periods[0] else ("y", Ly))
    return {
        "name": name, "family": family, "arxiv": ARXIV, "locator": locator,
        "n_paper": n_p, "k_paper": k_p, "dx": None, "dz": None, "d": d_p,
        "d_kind": d_kind, "d_method": d_method,
        "hx": hx, "hz": hz, "xy": xy,
        "notes": "; ".join(s for s in (geo, notes) if s),
        "group": group, "f": f, "h": h, "Lx": Lx, "Ly": Ly, "construction": construction,
        "geometry": geometry, "periods": periods, "cells": cells, "xy_open": xy_open,
        "check_range": rng, "check_range_open": rng_open,
    }


# ----------------------------------------------------------------------------------------------
# the paper's instances; polynomials copied verbatim from the TeX source of v3

_T1 = ("exact", "SAT solving (Sec. VI B; Table I caption: every displayed distance determined exactly by SAT)")
TABLE1 = [
    # [[n,k,d]], group, (Lx, Ly), f, h
    ((12, 8, 2), r"(Z_2 x Z_3) x| C_s", (2, 3), r"s_yt_y+s_yt_y^2+t_xs_yt_y+t_xs_yt_y^2", r"1+t_y^2+t_x+t_xt_y^2"),
    ((14, 6, 2), r"Z_7 x| C_s", (7, 1), r"s_x+s_x t_x^{2}+s_x t_x^{6}", r"s_x t_x^{3}+s_x t_x^{4}+s_x t_x^{6}"),
    ((14, 8, 2), r"Z_7 x| C_s", (7, 1), r"s_x+s_x t_x+s_x t_x^2+s_x t_x^4", r"s_x+s_x t_x+s_x t_x^2+s_x t_x^4"),
    ((18, 4, 4), r"(Z_3 x Z_3) x| C_s", (3, 3), r"s_xt_x+s_xt_x^{2}+s_xt_x^{2}t_y", r"s_xt_y+s_xt_y^{2}+s_xt_xt_y^{2}"),
    ((18, 6, 3), r"(Z_3 x Z_3) x| C_2v", (3, 3), r"s_y+t_xs_y+t_xs_yt_y+t_x^2s_yt_y", r"s_x+s_xt_y^2+s_xt_x+s_xt_xt_y"),
    ((24, 4, 4), r"(Z_3 x Z_4) x| C_2v", (3, 4), r"s_yt_y+s_x+s_xt_x^{2}s_y", r"s_yt_y^{3}+s_x+s_xt_x^{2}s_y"),
    ((24, 10, 4), r"(Z_6 x Z_2) x| C_s", (6, 2), r"s_x+s_xt_y+s_xt_x^2+s_xt_x^5t_y",
     r"s_xt_x+s_xt_xt_y+s_xt_x^2t_y+s_xt_x^5t_y"),
    ((28, 6, 4), r"(Z_7 x Z_2) x| C_s", (7, 2), r"s_xt_y+s_xt_x^{2}+s_xt_x^{3}t_y", r"s_xt_xt_y+s_xt_x^{3}+s_xt_x^{4}"),
    ((30, 10, 4), r"(Z_5 x Z_3) x| C_s", (5, 3), r"s_yt_y+s_yt_y^2+t_xs_yt_y+t_x^2s_y",
     r"t_xs_y+t_x^2s_y+t_x^2s_yt_y^2+t_x^3s_y"),
    ((32, 6, 6), r"Z_16 x| C_s", (16, 1), r"t_x^{7} s_x+t_x^{8} s_x+t_x^{9}s_x+t_x^{14}s_x",
     r"t_x s_x+t_x^{11}s_x+t_x^{12}s_x+t_x^{14}s_x"),
    ((36, 4, 6), r"(Z_3 x Z_6) x| C_2v", (3, 6), r"t_xs_y+s_xs_yt_y+s_xt_xs_yt_y", r"t_x+s_xt_y^{5}+s_xt_xt_y"),
    ((40, 14, 4), r"(Z_4 x Z_5) x| C_2v", (4, 5), r"t_x^2t_y^3+t_y^2s_x+t_xs_xs_y+t_xt_ys_xs_y",
     r"t_x^2t_y^3+t_y^2s_x+t_x^3s_xs_y+t_x^3t_ys_xs_y"),
    ((42, 6, 6), r"(Z_7 x Z_3) x| C_s", (7, 3), r"t_y+t_x^{4}s_yt_y^{2}+t_x^{5}", r"t_x^{2}s_yt_y^{2}+t_x^{3}+t_x^{5}t_y^{2}"),
    ((48, 4, 8), r"(Z_6 x Z_4) x| C_2v", (6, 4), r"s_xt_y+s_xt_xs_yt_y^{2}+s_xt_x^{2}", r"s_xt_y+s_xt_x^{2}t_y^{3}+s_xt_x^{4}"),
    ((50, 18, 4), r"(Z_5 x Z_5) x| C_s", (5, 5), r"s_xt_y^3+s_xt_y^4+s_xt_xt_y^2+s_xt_x^4",
     r"s_x+s_xt_y^3+s_xt_x^2t_y+s_xt_x^3t_y^2"),
    ((60, 8, 6), r"(Z_6 x Z_5) x| C_s", (6, 5), r"1+t_y^{3}+t_xs_yt_y^{4}", r"t_y^{2}+t_xs_yt_y^{4}+t_x^{4}"),
    ((70, 6, 8), r"(Z_5 x Z_7) x| C_s", (5, 7), r"t_x^{3}t_y^{6}+s_xt_xt_y+s_xt_x^{2}t_y^{2}",
     r"t_x^{2}t_y^{6}+s_xt_xt_y+s_xt_x^{2}t_y^{2}"),
    ((84, 10, 9), r"(Z_14 x Z_3) x| C_s", (14, 3), r"t_x^6t_y^2+t_x^7+t_x^8t_y+t_xt_y^2s_y",
     r"t_x+t_x^{12}t_y+t_x^{12}t_y^2+t_x^{13}"),
    ((96, 8, 10), r"(Z_24 x Z_2) x| C_s, s: (x,y) -> (x,-x-y)", (24, 2), r"1+t_x+s t_x^{17}t_y", r"1+t_x^{2}t_y+t_x^{22}"),
    ((112, 6, 12), r"(Z_7 x Z_4) x| C_s", (7, 4), r"1+t_x^6s_y+t_x^4t_y^2s_y", r"1+t_x^4t_y^3+t_x^6t_y^3 s_y"),
    ((112, 16, 10), r"(Z_7 x Z_4) x| C_s", (7, 4), r"1+t_x^2t_y s_y+t_x^4 s_y+t_x^3t_y^2 s_y",
     r"1+t_xt_y^2 s_y+t_x^4t_y+t_x^6t_y^3"),
    ((120, 14, 12), r"(Z_15 x Z_4) x| C_s", (15, 4), r"s_y+t_x^7t_y^2+t_x^{10}t_y^3 s_y+t_x^{12}",
     r"t_x^2+t_x^7+t_x^8t_y^3 s_y+t_x^{13}t_y^2 s_y"),
    ((132, 8, 11), r"(Z_22 x Z_3) x| C_s", (22, 3), r"1+t_x^{13} s_y+t_x^{13}t_y s_y+t_x^{16}t_y", r"1+t_x^{20}"),
    ((150, 8, 12), r"(Z_15 x Z_5) x| C_s", (15, 5), r"t_y^3+t_x^3+t_x^9t_y^2 s_y", r"t_x^5t_y^2+t_x^6+t_x^{14}t_y^2 s_y"),
    ((156, 8, 12), r"(Z_26 x Z_3) x| C_s", (26, 3), r"1+t_x^{24}t_y^2+t_x^9 s_y+t_x^3 t_y^2 s_y", r"1+t_x^2"),
    ((160, 26, 8), r"(Z_20 x Z_4) x| C_s", (20, 4), r"t_xt_y^3+t_x^{16}s_y+t_x^{14}+t_x^{19}t_y^2",
     r"t_xs_y+t_x^3+t_x^6t_y+t_x^8"),
]
BOLD = {(24, 10, 4), (30, 10, 4), (32, 6, 6), (40, 14, 4), (50, 18, 4), (84, 10, 9), (96, 8, 10),
        (112, 16, 10), (120, 14, 12), (132, 8, 11), (156, 8, 12), (160, 26, 8)}

_T2 = ("exact", "Fig. 5 caption: the pair shares identical exact [[n,k,d]]; no method stated "
                "(Table I's SAT statement covers Table I only)")
TABLE2 = [
    # [[n,k,d]], kind, (Lx, Ly) = Shape, f, h
    ((48, 4, 8), "sg", (3, 8), r"1+t_xt_y^6+t_x^2t_y^6", r"1+t_x^2t_y^6+s_xt_y^7"),
    ((48, 4, 8), "bb", (3, 8), r"1+t_xt_y+t_x^2t_y^2", r"1+t_xt_y^2+t_x^2t_y^2"),
    ((56, 6, 8), "sg", (4, 7), r"s_xt_y^4+s_xt_x^3t_y+s_xt_x^3t_y^3", r"t_y+t_x^2t_y^3+t_x^2t_y^4"),
    ((56, 6, 8), "bb", (4, 7), r"t_y+t_x+t_x^3t_y^3", r"1+t_xt_y+t_x^3t_y^3"),
    ((96, 4, 12), "sg", (6, 8), r"1+t_x^2t_y+t_x^4t_y", r"1+t_x^2t_y^2+s_xt_xt_y"),
    ((96, 4, 12), "bb", (6, 8), r"t_y^2+t_xt_y^7+t_x^5t_y^2", r"1+t_x^4t_y+t_x^5t_y^2"),
    ((108, 12, 6), "sg", (6, 9), r"1+t_y+s_xt_x^3t_y^5", r"t_y+s_xt_x^3t_y^2+s_xt_x^3t_y^3"),
    ((108, 12, 6), "bb", (2, 27), r"1+t_y^{24}+t_xt_y^{21}", r"1+t_xt_y^{15}+t_xt_y^{21}"),
    ((132, 4, 14), "sg", (6, 11), r"1+t_x^4t_y^3+s_xt_x^5", r"t_y+t_x^4t_y^3+s_xt_x^5"),
    ((132, 4, 14), "bb", (6, 11), r"1+t_x+t_x^2t_y^{10}", r"1+t_xt_y^2+t_x^2t_y^4"),
]
L_M = {(48, "bb"): 56, (48, "sg"): 52, (56, "bb"): 96, (56, "sg"): 80, (96, "bb"): 96, (96, "sg"): 80,
       (108, "bb"): 200, (108, "sg"): 80, (132, "bb"): 112, (132, "sg"): 88}

TABLE3 = [
    # [[n,k,d]], kind, (Lx, Ly) (not given in the paper), f, h, (Tiers, Length, Bumps, TSVs)
    ((48, 4, 8), "sg", (3, 8), r"t_y^3s_xs_y+t_xt_y^3s_xs_y+t_x^2t_ys_xs_y", r"t_xt_y^3+t_x^2t_y^5+t_x^2s_x",
     (5, 4.55, 3.36, 2.70)),
    ((96, 6, 10), "sg", (12, 4), r"t_x^4t_ys_y+t_x^5t_y^3", r"t_ys_y+t_xt_y+t_x^3+t_x^7t_y^2", (5, 6.95, 3.54, 2.93)),
    ((144, 12, 12), "bb", (12, 6), r"t_y^3+t_x+t_x^2", r"t_x^3+t_y+t_y^2", (5, 7.09, 5.14, 3.06)),
]

FIG4_TOPOLOGICAL = [
    # label, f, h, k for L = 4..11 (Fig. 4(a); reproduced), d for L = 4..11 (read off Fig. 4(b))
    ("code1", r"1+t_y", r"1+t_xt_y^2+s_xt_y+t_x^3", [4, 2, 6, 2, 4, 4, 4, 2], [4, 5, 4, 7, 8, 6, 10, 11]),
    ("code2", r"1+t_y", r"1+t_x+s_xt_y+s_xt_x^2t_y^2", [2, 2, 4, 2, 2, 4, 2, 2], [4, 5, 6, 7, 8, 9, 10, 11]),
    ("code3", r"1+t_y", r"1+t_x+s_xt_y+s_xt_x^3t_y", [6, 2, 4, 2, 6, 2, 4, 2], [3, 5, 6, 7, 6, 9, 10, 11]),
]
FIG4_NONTOPOLOGICAL = [
    # label, f, h; Fig. 4(c): code1 k = 16,10,24,14,32,18,40,22; codes 2, 3 (drawn as one double line)
    # k = 8,6,12,8,16,10,20,12; Fig. 4(d): code1 d = 2 for all L, code2 d = 2,2,2,3,3,3,4,4,
    # code3 d = 2,3,3,3,3,3,3,3.  Our matrices do NOT reproduce these k (see note).
    ("code1", r"t_y+t_y^{-1}", r"t_xt_y^{-1}+t_x^{-2}+s_xt_x^{-1}t_y+s_xt_x^2t_y^2",
     [16, 10, 24, 14, 32, 18, 40, 22], [2, 2, 2, 2, 2, 2, 2, 2]),
    ("code2", r"t_y+t_y^{-1}", r"s_xs_yt_x^{-2}+s_xs_yt_x^{-2}t_y+s_yt_y^{-1}+s_yt_y^{-2}",
     [8, 6, 12, 8, 16, 10, 20, 12], [2, 2, 2, 3, 3, 3, 4, 4]),
    ("code3", r"t_y+t_y^{-1}", r"s_xs_yt_xt_y^2+s_xs_yt_x^{-1}t_y+s_yt_x+s_yt_x^{-1}t_y^{-1}",
     [8, 6, 12, 8, 16, 10, 20, 12], [2, 3, 3, 3, 3, 3, 3, 3]),
]


def _tag(nkd):
    return "%d_%d_%d" % nkd


def table1():
    out = []
    for nkd, group, (Lx, Ly), f, h in TABLE1:
        notes = ["Table I%s, group %s" % (" (bold: beats the same-n, same-weight BB benchmark)"
                                           if nkd in BOLD else "", group)]
        construction = "lattice"
        if nkd[0] == 112:
            construction = "2BGA"
            notes.append("2BGA over the order-56 group (Z_7 x Z_4) x| <s_y> (left action on block L, right "
                         "action on block R): the group label (Z_7 x Z_4) has only 28 lattice cells (n = 56, "
                         "checks do not commute), so n = 112 requires the regular representation; this "
                         "reading reproduces n and k exactly but is not stated in the paper")
        if nkd[0] == 96:
            notes.append("mod 2, s acts as (x, y) -> (x, x + y): it stays inside a column, so no fold is "
                         "needed and the code is a 24 x 2 torus code")
        out.append(build("sg_t1_" + _tag(nkd), FAMILY, "Table I, row [[%d,%d,%d]] (Sec. VI B, Eq. (116))" % nkd,
                         nkd, f, h, Lx, Ly, group, _T1[0], _T1[1], "; ".join(notes), construction))
    return out


def table2():
    out = []
    for nkd, kind, (Lx, Ly), f, h in TABLE2:
        if kind == "sg":
            name, family, group = "sg_t2_" + _tag(nkd), FAMILY, "Z_%d x Z_%d x| C_s (s_x)" % (Lx, Ly)
            who = "reflection code"
        else:
            name, family, group = "bb_t2_" + _tag(nkd), FAMILY_BB, "Z_%d x Z_%d" % (Lx, Ly)
            who = "BB comparator, taken by the paper from Ref. [63] (Wang and Mueller, Quantum 10, 2009 (2026))"
        notes = "Table II %s, shape %d x %d; optimized AOD movement cost L_m = %d (Fig. 5)" % (
            who, Lx, Ly, L_M[(nkd[0], kind)])
        out.append(build(name, family, "Table II, %s row [[%d,%d,%d]] (Sec. VI C, Fig. 5)" % ((kind,) + nkd),
                         nkd, f, h, Lx, Ly, group, _T2[0], _T2[1], notes))
    return out


def table3():
    out = []
    for nkd, kind, (Lx, Ly), f, h, hw in TABLE3:
        hwtxt = "HAL layout (Tiers, Length, Bumps, TSVs) = (%d, %.2f, %.2f, %.2f)" % hw
        if kind == "sg":
            group = "Z_%d x Z_%d x| %s" % (Lx, Ly, "C_2v" if "s_xs_y" in f else "C_s (s_y)")
            notes = ("Table III reflection code; the paper gives no shape: %d x %d is the only factorisation of "
                     "%d cells with commuting checks and k = %d, and matches the tier-0 array of Fig. 6; %s"
                     % (Lx, Ly, Lx * Ly, nkd[1], hwtxt))
            out.append(build("sg_t3_" + _tag(nkd), FAMILY, "Table III, row [[%d,%d,%d]] (Sec. VI D, Fig. 6)" % nkd,
                             nkd, f, h, Lx, Ly, group, "unknown",
                             "parameters stated in Sec. VI D / Table III without a method", notes))
        else:
            notes = ("Table III: the gross code (A = x^3 + y + y^2, B = y^3 + x + x^2 of Bravyi et al., the "
                     "paper's ref. [22]) with f = B, h = A; %s (published layout of Ref. [71]: "
                     "(5, 11.08, 5.06, 3.27))" % hwtxt)
            out.append(build("bb_t3_" + _tag(nkd), FAMILY_BB, "Table III, row [[144,12,12]] (Sec. VI D, Fig. 6)",
                             nkd, f, h, Lx, Ly, "Z_12 x Z_6", "unknown",
                             "quoted as the known gross code [[144,12,12]] (ref. [22]); this paper gives no "
                             "method", notes))
    return out


def figure4(families=FIG4_TOPOLOGICAL, topological=True):
    out = []
    for label, f, h, ks, ds in families:
        for L, k_p, d_p in zip(range(4, 12), ks, ds):
            nkd = (2 * L * L, k_p, d_p)
            if topological:
                name = "sg_f4top_%s_L%d" % (label, L)
                loc = "Fig. 4(a),(b), topological %s, L = %d (caption; f, h of Eq. (116))" % (label, L)
                notes = ("Fig. 4 topological reflection-code family; k read off Fig. 4(a) (k computed from "
                         "the binary rank, Sec. VI A), d read off the plot of Fig. 4(b)")
                method = "read off the plot of Fig. 4(b); the paper does not say how it was computed"
            else:
                name = "sg_f4non_%s_L%d" % (label, L)
                loc = "Fig. 4(c),(d), non-topological %s, L = %d (caption)" % (label, L)
                notes = ("NOT REPRODUCED: the caption polynomials give a different k at most L (our reading "
                         "matches the topological families at every L, the conventions being the same); "
                         "k and d read off Fig. 4(c),(d)")
                method = "read off the plot of Fig. 4(d); method not stated"
            out.append(build(name, FAMILY, loc, nkd, f, h, L, L, "Z_%d x Z_%d x| C_2v" % (L, L)
                             if "s_y" in h else "Z_%d x Z_%d x| C_s (s_x)" % (L, L),
                             "unknown", method, notes))
    return out


def instances(figure4_topological=True, nontopological=False):
    """Every row of Tables I-III, plus (default) the Fig. 4 topological families; nontopological=True
    adds the Fig. 4(c),(d) families, whose k our matrices do not reproduce."""
    insts = table1() + table2() + table3()
    if figure4_topological:
        insts += figure4(FIG4_TOPOLOGICAL, True)
    if nontopological:
        insts += figure4(FIG4_NONTOPOLOGICAL, False)
    return [planar_common.check(i) for i in insts]


if __name__ == "__main__":
    insts = instances(nontopological="--all" in sys.argv)
    print(planar_common.summary(insts))
    bad = [i["name"] for i in insts if (i["n"], i["k"]) != (i["n_paper"], i["k_paper"])]
    print("%d instances, %d do not reproduce the paper's (n, k)%s"
          % (len(insts), len(bad), (": " + ", ".join(bad)) if bad else ""))
    if "-v" in sys.argv:
        for i in insts:
            print("%-26s %-9s periods=%-12s range=%s open=%s" % (i["name"], i["geometry"], i["periods"],
                                                                  i["check_range"], i["check_range_open"]))
