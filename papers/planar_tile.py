"""Tile codes: the planar codes of arXiv:2504.09171 (Steffan, Choe, Breuckmann, Pereira, Eberhardt) and
the four weight-6 families of arXiv:2607.05897 (Bae, Park; families of Liang, Eberhardt, Chen, PRX Quantum
6(4), 2025).  Interface: papers/planar_common.py.  Notes: papers/new/2504.09171.md, papers/new/2607.05897.md.

Construction (2504.09171: "Tile codes", "Systematic construction of tile codes", conditions (T1)-(T2),
Fig. 1, Appendix A with Fig. 2).  Qubits are the horizontal edges h(i,j) = (i,j)-(i+1,j) and the vertical
edges v(i,j) = (i,j)-(i,j+1) of the square lattice with 0 <= i < Lx, 0 <= j < Ly, at positions
h(i,j) -> (i+0.5, j) and v(i,j) -> (i, j+0.5).  An X tile is a set of edges h(x,y), v(x,y) with
0 <= x < Bx, 0 <= y < By (T1: nothing on the top row or right column of the box).  (T2) fixes the Z tile:
    h(x,y) in the X tile  <->  v(Bx-1-x, By-1-y) in the Z tile,
    v(x,y) in the X tile  <->  h(Bx-1-x, By-1-y) in the Z tile,
so X and Z tiles commute at every relative offset.  A check anchored at the lattice point a covers
a + tile, truncated to the Lx x Ly arrays.  Anchors:
    bulk (X and Z):  [0, Lx-Bx] x [0, Ly-By]
    X boundary:      By-1 rows below and By-1 rows above the bulk rows, bulk x range  (red dots)
    Z boundary:      Bx-1 columns left and Bx-1 right of the bulk columns, bulk y range (blue dots)
Finally ("fine-tuning" in 2504.09171, "grafting" in 2607.05897) every qubit that lies in no X check or in no
Z check is removed and checks left empty are dropped.  2504.09171 uses square boxes (Bx = By = B).  The
2607.05897 families need 3x3 and 3x4 boxes (its "3x3 and 4x3 windows"); the commutation argument (boundary
boxes of opposite type meet only inside the arrays) is unchanged for rectangular boxes.

2607.05897 (Sec. II.A, Eqs. (1)-(2), Table I, Fig. 1): the X check is (f_norm, g_norm): f on the L layer
(horizontal edges), g on the R layer (vertical edges), each shifted to non-negative exponents separately;
x^i y^j is the edge h(i,j) resp. v(i,j) relative to the anchor.  Its Z check, the conjugate pair (gbar, fbar),
is the (T2) image up to a common translation.  Fig. 1 (family [[288,8,12]], Lx = Ly = 6) shows exactly the
anchor layout above (4 x 8 X checks, 8 x 4 Z checks; its weight-6 bulk and weight-4 boundary X checks are
present here).  The removal rule reproduces the n formulas of Table I (2LxLy, 2LxLy-Lx-Ly+1,
2LxLy-2Lx-Ly+2, 2LxLy-Ly), and k matches for every size.

Code equivalences (verified with isomorphic(); rerun with `python papers/planar_tile.py --equiv`): all 16
weight-6 [[288,8,12]] codes of 2504.09171 Appendix B and the 12x12 member of the 2607.05897 [[288,8,12]]
family are one code up to qubit relabeling (SAME_CODE).  The Appendix C weight-8 codes are pairwise
inequivalent under the same relabeling group.  tile_288_18_13, tile_512_18_19 and tile_25_1_4_surface are
X<->Z self-dual under that group (dx = dz); for no other instance was such a map found.
"""
from __future__ import annotations

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stabcode  # noqa: E402
from planar_common import check, from_cells, summary  # noqa: E402

ARXIV_TILE = "2504.09171"
ARXIV_BP = "2607.05897"


# ---------------------------------------------------------------------------------------------------------
# generic construction

def z_tile(xh, xv, bx, by):
    """(T2): Z tile (h, v) from the X tile (h, v) in a Bx x By box."""
    return ([(bx - 1 - x, by - 1 - y) for x, y in xv], [(bx - 1 - x, by - 1 - y) for x, y in xh])


def tile_code(xh, xv, lx, ly, bx, by, zh=None, zv=None):
    """Tile code on the lx x ly arrays of horizontal and vertical edges (module docstring).

    xh, xv: X tile, lists of (x, y) lower-left corners of its horizontal / vertical edges inside the bx x by
    box; zh, zv: Z tile (default: the (T2) image).  Returns a partial instance dict (hx, hz, xy and the
    construction details, including the removed qubits)."""
    if zh is None:
        zh, zv = z_tile(xh, xv, bx, by)
    for x, y in list(xh) + list(xv) + list(zh) + list(zv):
        assert 0 <= x < bx and 0 <= y < by, "tile outside its box"
    nxa, nya = lx - bx + 1, ly - by + 1          # bulk anchors per direction
    assert nxa >= 1 and nya >= 1
    x_anchors = [(a, b) for b in range(-(by - 1), nya + by - 1) for a in range(nxa)]
    z_anchors = [(a, b) for b in range(nya) for a in range(-(bx - 1), nxa + bx - 1)]

    def support(th, tv, a, b):
        s = [("h", a + x, b + y) for x, y in th if 0 <= a + x < lx and 0 <= b + y < ly]
        s += [("v", a + x, b + y) for x, y in tv if 0 <= a + x < lx and 0 <= b + y < ly]
        return s

    xs = [support(xh, xv, a, b) for a, b in x_anchors]
    zs = [support(zh, zv, a, b) for a, b in z_anchors]
    full = {(t, i, j) for t in "hv" for i in range(lx) for j in range(ly)}
    keep = set().union(*xs) & set().union(*zs)

    def pos(q):
        t, i, j = q
        return (i + 0.5, float(j)) if t == "h" else (float(i), j + 0.5)

    qubits = sorted(keep, key=lambda q: (pos(q)[1], pos(q)[0]))
    index = {q: s for s, q in enumerate(qubits)}
    n = len(qubits)
    return {
        "hx": from_cells([[index[q] for q in s if q in keep] for s in xs], n),
        "hz": from_cells([[index[q] for q in s if q in keep] for s in zs], n),
        "xy": [pos(q) for q in qubits],
        "construction": {
            "Lx": lx, "Ly": ly, "box": (bx, by),
            "x_tile": {"h": sorted(xh), "v": sorted(xv)},
            "z_tile": {"h": sorted(zh), "v": sorted(zv)},
            "bulk_anchors": (nxa, nya),
            "removed_qubits": ["%s(%d,%d)" % q for q in sorted(full - keep)],
        },
    }


def polynomial_tile(f, g):
    """2607.05897 Sec. II.A: X tile (f_norm, g_norm) from the exponent lists of the Laurent polynomials f
    (L = horizontal edges) and g (R = vertical edges), each shifted to non-negative exponents separately.
    Returns (xh, xv, bx, by); the box is the bounding box of both supports."""
    def norm(p):
        mx, my = min(a for a, _ in p), min(b for _, b in p)
        return [(a - mx, b - my) for a, b in p]
    xh, xv = norm(f), norm(g)
    return xh, xv, 1 + max(x for x, _ in xh + xv), 1 + max(y for _, y in xh + xv)


# ---------------------------------------------------------------------------------------------------------
# arXiv:2504.09171: X tiles transcribed from the TikZ source (\horizontalqubits = h edges, \verticalqubits =
# v edges; every Z tile drawn in the paper equals the (T2) image, checked on the source).

STEFFAN_W6 = {   # Appendix B, Table II: the eight drawn weight-6 pairs, in source order
    1: ([(0, 0), (0, 1), (2, 2)], [(0, 2), (1, 0), (2, 0)]),
    2: ([(0, 0), (0, 1), (2, 2)], [(0, 2), (1, 2), (2, 0)]),
    3: ([(0, 0), (1, 0), (2, 2)], [(0, 1), (0, 2), (2, 0)]),
    4: ([(0, 0), (1, 0), (2, 2)], [(0, 2), (2, 0), (2, 1)]),
    5: ([(0, 0), (1, 2), (2, 2)], [(0, 1), (0, 2), (2, 0)]),
    6: ([(0, 0), (1, 2), (2, 2)], [(0, 2), (2, 0), (2, 1)]),
    7: ([(0, 0), (2, 1), (2, 2)], [(0, 2), (1, 0), (2, 0)]),
    8: ([(0, 0), (2, 1), (2, 2)], [(0, 2), (1, 2), (2, 0)]),   # = Table I row 1 = Fig. 1 = main-text example
}
STEFFAN_W8 = {   # Appendix C, Table III: four of the >300 weight-8 [[288,8,14]] pairs, in source order
    1: ([(0, 0), (0, 1), (0, 2), (2, 0)], [(0, 0), (0, 1), (1, 1), (2, 2)]),
    2: ([(0, 0), (0, 1), (0, 2), (2, 0)], [(0, 0), (0, 2), (1, 1), (2, 2)]),   # = Table I row 2
    3: ([(0, 0), (0, 1), (0, 2), (2, 0)], [(0, 0), (1, 2), (2, 1), (2, 2)]),
    4: ([(0, 0), (0, 1), (0, 2), (2, 0)], [(0, 1), (1, 0), (1, 1), (2, 2)]),
}
STEFFAN_B4_W8 = ([(0, 0), (0, 3), (2, 2), (3, 0)], [(0, 1), (1, 0), (1, 1), (3, 3)])   # Table I rows 3-4
STEFFAN_B4_W10 = ([(0, 0), (1, 0), (2, 1), (2, 3), (3, 0)],
                  [(0, 3), (1, 0), (3, 1), (3, 2), (3, 3)])                         # text after Table I
SURFACE_B2 = ([(0, 1), (1, 1)], [(1, 0), (1, 1)])   # vertex-star X tile of the surface-code example

# same code as the representative up to qubit relabeling; True = X and Z exchanged (dx, dz swap roles)
SAME_CODE = {
    "tile_288_8_12_b1": ("tile_288_8_12", False), "tile_288_8_12_b2": ("tile_288_8_12", True),
    "tile_288_8_12_b3": ("tile_288_8_12", True), "tile_288_8_12_b4": ("tile_288_8_12", False),
    "tile_288_8_12_b5": ("tile_288_8_12", False), "tile_288_8_12_b6": ("tile_288_8_12", True),
    "tile_288_8_12_b7": ("tile_288_8_12", True),
    "tile_288_8_12_b1s": ("tile_288_8_12", False), "tile_288_8_12_b2s": ("tile_288_8_12", True),
    "tile_288_8_12_b3s": ("tile_288_8_12", True), "tile_288_8_12_b4s": ("tile_288_8_12", False),
    "tile_288_8_12_b5s": ("tile_288_8_12", False), "tile_288_8_12_b6s": ("tile_288_8_12", True),
    "tile_288_8_12_b7s": ("tile_288_8_12", True), "tile_288_8_12_b8s": ("tile_288_8_12", False),
    "bp288_288_8_12": ("tile_288_8_12", True),
}
SELF_DUAL = {"tile_288_18_13", "tile_512_18_19", "tile_25_1_4_surface"}

D_ILP = ("QDistRnd (GAP) estimate, then confirmed by an integer linear program (main text, 'Examples of "
         "tile codes'); Table I caption: 'exact values, calculated using integer linear programming'")
D_SEARCH = ("exhaustive search over %s tiles in 3x3 boxes on the 10x10-anchor square layout (Appendix %s); "
            "distances by the paper's stated workflow, QDistRnd estimate then ILP confirmation (main text, "
            "'Examples of tile codes'); the explicit per-code ILP statement is only in the Table I caption")


def _steffan(name, locator, xh, xv, B, L, n, k, d, d_kind, d_method, notes, zt=None):
    inst = tile_code(xh, xv, L, L, B, B, *(zt or (None, None)))
    # the paper gives only d; dx = dz = d is filled in only where an X<->Z self-duality proves it (SELF_DUAL)
    dxz = d if name in SELF_DUAL else None
    if dxz is not None:
        notes += " dx = dz = d: the paper gives d only; equality follows from the X<->Z self-duality (SELF_DUAL)."
    inst.update(name=name, family="tile codes", arxiv=ARXIV_TILE, locator=locator,
                n_paper=n, k_paper=k, dx=dxz, dz=dxz, d=d, d_kind=d_kind, d_method=d_method, notes=notes)
    return inst


def steffan_instances():
    out = []
    xh, xv = STEFFAN_W6[8]
    out.append(_steffan(
        "tile_288_8_12", "Table I row 1 (B=3, w=6); Fig. 1; main-text example; = Appendix B Table II pair 8",
        xh, xv, 3, 12, 288, 8, 12, "exact", D_ILP,
        "10x10 bulk anchors (main text); Fig. 1 layout: 12x12 h and v edges, X boundary anchors 2 rows "
        "below/above, Z boundary anchors 2 columns left/right; no qubit removed. The paper credits the "
        "[[288,8,12]] parameters first to Liang et al. Representative of the class SAME_CODE (16 Appendix B "
        "codes and bp288_288_8_12)."))
    xh, xv = STEFFAN_W8[2]
    out.append(_steffan(
        "tile_288_8_14", "Table I row 2 (B=3, w=8); main-text example; = Appendix C Table III pair 2",
        xh, xv, 3, 12, 288, 8, 14, "exact", D_ILP, "10x10 bulk anchors (main text); no qubit removed."))
    xh, xv = STEFFAN_B4_W8
    out.append(_steffan(
        "tile_288_18_13", "Table I row 3 (B=4, w=8); main text after the w=8 example",
        xh, xv, 4, 12, 288, 18, 13, "exact", D_ILP,
        "9x9 bulk anchors (main text); no qubit removed. Same tiles as tile_512_18_19; the TikZ source of "
        "these tiles carries an author comment 'I have to fix this', yet n and k are reproduced."))
    out.append(_steffan(
        "tile_512_18_19", "Table I row 4 (B=4, w=8); abstract; main text after the w=8 example",
        xh, xv, 4, 16, 512, 18, 19, "exact", D_ILP,
        "13x13 bulk anchors (main text); no qubit removed."))
    xh, xv = STEFFAN_B4_W10
    out.append(_steffan(
        "tile_512_18_23", "main text after Table I (w=10, B=4 tiles drawn there)",
        xh, xv, 4, 16, 512, 18, 23, "upper",
        "randomized tile search, probabilistic distance estimate d <= 23; not verified by ILP (main text "
        "after Table I: the authors 'strongly expect' d = 23)",
        "Layout not stated; the 13x13-anchor square layout is assumed (it gives n = 512, no qubit removed). "
        "Paper: [[512,18,<=23]], conjectured d = 23."))
    for p in range(1, 8):
        xh, xv = STEFFAN_W6[p]
        out.append(_steffan(
            "tile_288_8_12_b%d" % p, "Appendix B, Table II pair %d (drawn)" % p,
            xh, xv, 3, 12, 288, 8, 12, "exact", D_SEARCH % ("weight-6", "B"), "10x10 bulk anchors."))
    for p in range(1, 9):
        xh, xv = STEFFAN_W6[p]
        zh, zv = z_tile(xh, xv, 3, 3)
        out.append(_steffan(
            "tile_288_8_12_b%ds" % p,
            "Appendix B, Table II caption: pair %d with the roles of X and Z tiles swapped (not drawn)" % p,
            zh, zv, 3, 12, 288, 8, 12, "exact", D_SEARCH % ("weight-6", "B"),
            "The caption says the other 8 of the 16 codes follow by swapping the X and Z tiles. Built with "
            "X tile = drawn Z tile and Z tile = drawn X tile, same layout (X boundary rows top/bottom).",
            zt=(xh, xv)))
    for p in (1, 3, 4):
        xh, xv = STEFFAN_W8[p]
        out.append(_steffan(
            "tile_288_8_14_c%d" % p, "Appendix C, Table III pair %d" % p,
            xh, xv, 3, 12, 288, 8, 14, "exact", D_SEARCH % ("weight-8", "C"),
            "10x10 bulk anchors; no qubit removed. Table III shows 4 of more than 300 weight-8 pairs."))
    xh, xv = SURFACE_B2
    out.append(_steffan(
        "tile_25_1_4_surface", "main text, 'Tile codes': surface-code tiles and the d=4 layout example",
        xh, xv, 2, 4, 25, 1, 4, "exact", "standard unrotated surface code of distance 4, as stated in the text",
        "Illustrative example (B=2 vertex/plaquette tiles, 3x3 bulk anchors). The paper draws X boundary "
        "anchors only below and Z only on the right; the symmetric layout used here adds only checks that "
        "end up empty, so the code is the same."))
    return out


# ---------------------------------------------------------------------------------------------------------
# arXiv:2607.05897, Table I: exponent lists of f = 1 + x + x^a y^b (L layer) and g = 1 + y + x^c y^d (R layer)

BP_FAMILIES = {
    # family label: (f exponents, g exponents, n formula of Table I)
    288: ([(0, 0), (1, 0), (-1, 2)], [(0, 0), (0, 1), (-2, -1)], "2LxLy"),
    188: ([(0, 0), (1, 0), (-1, 2)], [(0, 0), (0, 1), (1, 3)], "2LxLy-Lx-Ly+1"),
    131: ([(0, 0), (1, 0), (-1, 1)], [(0, 0), (0, 1), (1, 3)], "2LxLy-2Lx-Ly+2"),
    88: ([(0, 0), (1, 0), (-1, -2)], [(0, 0), (0, 1), (1, -1)], "2LxLy-Ly"),
}
BP_LABEL = {288: "[[288,8,12]]", 188: "[[188,8,9]]", 131: "[[131,7,7]]", 88: "[[88,6,6]]"}
BP_TABLE = [   # (family, Lx, Ly, n, k, d, locator)
    (288, 6, 6, 72, 8, 4, "Table I; Fig. 1 (Lx=Ly=6, d=4)"),
    (288, 8, 8, 128, 8, 6, "Table I"),
    (288, 10, 10, 200, 8, 9, "Table I"),
    (288, 12, 12, 288, 8, 12, "Table I"),
    (288, 13, 13, 338, 8, 13, "Sec. III.C (footprint study, 'two larger family members')"),
    (288, 14, 14, 392, 8, 15, "Sec. III.C (footprint study, 'two larger family members')"),
    (188, 6, 10, 105, 8, 6, "Table I"),
    (188, 7, 11, 137, 8, 7, "Table I"),
    (188, 8, 12, 173, 8, 8, "Table I"),
    (188, 8, 13, 188, 8, 9, "Table I"),
    (188, 9, 14, 230, 8, 10, "Table I"),
    (188, 10, 15, 276, 8, 11, "Table I"),
    (131, 7, 11, 131, 7, 7, "Table I"),
    (131, 8, 12, 166, 7, 8, "Table I"),
    (131, 9, 13, 205, 7, 10, "Table I"),
    (131, 10, 14, 248, 7, 11, "Table I"),
    (131, 10, 15, 267, 7, 12, "Table I"),
    (88, 6, 8, 88, 6, 6, "Table I"),
    (88, 8, 10, 150, 6, 8, "Table I"),
    (88, 8, 11, 165, 6, 9, "Table I"),
    (88, 10, 12, 228, 6, 11, "Table I"),
    (88, 10, 13, 247, 6, 12, "Table I"),
]
D_BP = ("not stated in 2607.05897: Table I lists [[n,k,d]] without a method and attributes the families to "
        "Liang et al., Ref. [17], PRX Quantum 6(4) (2025), doi:10.1103/qv65-vmzr")


def bp_instances():
    out = []
    for fam, lx, ly, n, k, d, loc in BP_TABLE:
        f, g, nform = BP_FAMILIES[fam]
        xh, xv, bx, by = polynomial_tile(f, g)
        inst = tile_code(xh, xv, lx, ly, bx, by)
        rem = inst["construction"]["removed_qubits"]
        notes = ("%s family of Table I: f, g exponents %s, %s; box %dx%d; Table I n = %s; grafting here removes "
                 "%d R (vertical-edge) qubits. " % (BP_LABEL[fam], f, g, bx, by, nform, len(rem)))
        d_method = D_BP
        if lx in (13, 14):
            notes += ("Sec. III.C gives only [[n,k,d]]; Lx = Ly assumed (n = 2LxLy; every Table I size of this "
                      "family is square; 392 would also allow 7x28). ")
        if fam == 288 and lx == 12:
            notes += ("Same code as tile_288_8_12 of 2504.09171 up to qubit relabeling, with X and Z exchanged "
                      "(SAME_CODE; checked with isomorphic()). ")
            d_method += ("; the code equals 2504.09171's Table I [[288,8,12]] (X and Z exchanged), whose d = 12 "
                         "is exact by ILP there")
        inst.update(name="bp%d_%d_%d_%d" % (fam, n, k, d), family="tile codes", arxiv=ARXIV_BP,
                    locator="%s; (Lx,Ly)=(%d,%d)" % (loc, lx, ly), n_paper=n, k_paper=k, dx=None, dz=None, d=d,
                    d_kind="unknown", d_method=d_method, notes=notes.strip())
        out.append(inst)
    return out


def instances():
    insts = steffan_instances() + bp_instances()
    for inst in insts:
        rep = SAME_CODE.get(inst["name"])
        inst["same_code_as"] = None if rep is None else (
            "%s (%s)" % (rep[0], "X and Z exchanged: dx, dz swap" if rep[1] else "dx, dz preserved"))
        if rep is not None and "SAME_CODE" not in inst["notes"]:
            inst["notes"] += " Same code as %s up to qubit relabeling (%s); see SAME_CODE." % (
                rep[0], "X and Z exchanged" if rep[1] else "X and Z preserved")
        check(inst)
    return insts


# ---------------------------------------------------------------------------------------------------------
# equivalence check over the structural relabeling group: each edge layer mapped by a symmetry of its
# Lx x Ly array (reflections; transposes when square), optionally exchanging the two layers, with or
# without exchanging X and Z.  A hit is a proof of equivalence; a miss proves nothing beyond this group.

def _labels(inst):
    out = []
    for x, y in inst["xy"]:
        if abs(x - round(x)) > 0.25:
            out.append(("h", int(round(x - 0.5)), int(round(y))))
        else:
            out.append(("v", int(round(x)), int(round(y - 0.5))))
    return out


def _array_maps(lx, ly):
    maps = [lambda i, j: (i, j), lambda i, j: (lx - 1 - i, j), lambda i, j: (i, ly - 1 - j),
            lambda i, j: (lx - 1 - i, ly - 1 - j)]
    if lx == ly:
        maps += [lambda i, j: (j, i), lambda i, j: (lx - 1 - j, i), lambda i, j: (j, ly - 1 - i),
                 lambda i, j: (lx - 1 - j, ly - 1 - i)]
    return maps


def _same_space(a, b):
    ra = stabcode.rank(a)
    return ra == stabcode.rank(b) and stabcode.rank(list(a) + list(b)) == ra


def _permute(rows, perm):
    out = []
    for r in rows:
        v = 0
        while r:
            low = r & -r
            v |= 1 << perm[low.bit_length() - 1]
            r ^= low
        out.append(v)
    return out


def isomorphic(a, b, exchange=None):
    """Search the structural relabeling group for a map from code a to code b.  exchange: None (either),
    False (X->X only) or True (X->Z only).  Returns (layer_swap, exchanged) of the first hit, or None."""
    la, lb = _labels(a), _labels(b)
    if len(la) != len(lb):
        return None
    ib = {q: s for s, q in enumerate(lb)}
    lx, ly = a["construction"]["Lx"], a["construction"]["Ly"]
    for swap in (False, True):
        for mh, mv in itertools.product(_array_maps(lx, ly), repeat=2):
            perm = []
            for t, i, j in la:
                q = (("v" if t == "h" else "h") if swap else t,) + (mh if t == "h" else mv)(i, j)
                if q not in ib:
                    break
                perm.append(ib[q])
            else:
                px, pz = _permute(a["hx"], perm), _permute(a["hz"], perm)
                if exchange in (None, False) and _same_space(px, b["hx"]) and _same_space(pz, b["hz"]):
                    return swap, False
                if exchange in (None, True) and _same_space(px, b["hz"]) and _same_space(pz, b["hx"]):
                    return swap, True
    return None


def verify_equivalences(insts=None):
    by = {i["name"]: i for i in (insts or instances())}
    lines = []
    for name, (rep, exch) in SAME_CODE.items():
        hit = isomorphic(by[name], by[rep], exchange=exch)
        lines.append("%-20s -> %s %s: %s" % (name, rep, "(X<->Z)" if exch else "(X->X)", "OK" if hit else "FAILED"))
    for name in SELF_DUAL:
        inst = by[name]
        hit = isomorphic(inst, dict(inst, hx=inst["hz"], hz=inst["hx"]), exchange=False)
        lines.append("%-20s X<->Z self-dual: %s" % (name, "OK" if hit else "FAILED"))
    return "\n".join(lines)


if __name__ == "__main__":
    insts = instances()
    print(summary(insts))
    if "--equiv" in sys.argv[1:]:
        print(verify_equivalences(insts))
