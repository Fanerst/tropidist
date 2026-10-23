"""Directional tile codes: the planar codes of arXiv:2606.19482v2 (Gu, Noszko, Steffan, Eberhardt, Roffe, Eisert,
Koutsioumpas, "Nearest-neighbour gates are all you need: High-rate quantum low-density parity-check codes on a planar
grid").  Interface: papers/planar_common.py.  Note: papers/new/2606.19482.md.

Construction (Sec. IV "Directional tile codes", Definition 1, Fig. 1(b),(c); the tile conventions are those of the
tile codes of arXiv:2504.09171, which the paper adopts):
  * A directional word D = d_1...d_w (letters N, E, S, W; "N2ESEN2" = NNESENN) is a lattice path.  The X tile is the
    set of the w edges the path traverses from its start vertex: from (x,y), N is v(x,y), E is h(x,y), S is v(x,y-1),
    W is h(x-1,y), with h(i,j) = (i,j)-(i+1,j) and v(i,j) = (i,j)-(i,j+1).  Qubit positions: h(i,j) -> (i+0.5, j),
    v(i,j) -> (i, j+0.5) (the paper's hardware grid is this lattice at half spacing: X checks on vertices, Z checks
    on plaquettes, data on edges, routing sites on the leftover boundary sites).
  * Translated into its bounding box [0,Bx-1] x [0,By-1] (the box's lower-left vertex is the anchor), the Z tile is
    the mutual-condition image (Sec. IV; condition (T2) of 2504.09171): h(a,b) -> v(Bx-1-a, By-1-b) and
    v(a,b) -> h(Bx-1-a, By-1-b).  For the paper's words (all palindromes) this is the same word walked on the dual
    lattice from a plaquette (asserted in tiles()); the walk order is the CXSWAP schedule of Algorithm 1, recorded per
    check in x_order / z_order.  Definition 1's parity condition holds for every word used (asserted).  The paper
    writes a square B x B box; the square box gives the same codes and the same check counts (verified).
  * Anchors.  The paper's M x N (Table III, Table IV, Example 4, Fig. 8) counts the CELLS of the anchor subgrid: its
    (M+1) x (N+1) vertices are the bulk anchors, M+1 ROWS (y) and N+1 COLUMNS (x).  Bulk anchors carry an X and a Z
    tile; By-1 rows of X-only anchors below and above the bulk (bulk columns); Bx-1 columns of Z-only anchors left
    and right (bulk rows) (Fig. 1(c), the tile-code layout).  The edge arrays are the union of the bulk boxes:
    Lx = N+Bx by Ly = M+By vertices, each with its right and up edge.  Check supports are truncated to the arrays.
  * Pruning (Sec. IV): edges contained in tiles of at most one type are removed, then checks left empty.
  X logicals run between the bottom and top (X-boundary) sides, so dx grows with M; Z logicals run left-right and dz
  grows with N (Table IV fits; Fig. 9).

Calibration of the M,N convention (the Sec. IV wording "the vertices of an M x N subgrid", an "(M+B-1) x (N+B-1)"
grid and Lemma 3's "MN anchors" would mean M x N anchors, which does not reproduce Table III): Table III's explicit
(M,N) and n for all rows, also the TeX's commented-out w=13 row [[611,20]] at (16,9); Example 4's 346 -> 165 routing
sites for [[323,14,15]] = Table IV's formulas at (M,N) = (5,16); Fig. 8's plotted routing counts = Table IV's formulas
at the sizes used here; the data / X-check / Z-check counts of Fig. 1(b) (60/28/28), Fig. 3 (52/22/20) and Fig. 5
(18/6/10); and Fig. 5's dx = 3, dz = 2 (exhaustive check of the 18-qubit code).  Fig. 8's circuit-qubit formula
n_circ = data + checks + routing(Table IV) is reproduced exactly for w = 7; for w = 9 the paper's n_circ is 8 higher at
every size, for w = 11 it agrees with Fig. 2's points (the Fig. 8 w = 11 fit is approximate).

Hexagonal grid (word ENES2WS2ENE): the same square-lattice tile code.  The degree-3 (brick-wall) hardware graph is a
subgraph of the half-spacing square grid, and every horizontal step of this word uses a bond present in it (Fig. 3 is
drawn rotated by 90 degrees).  The paper gives no M, N for the hexagonal codes: [[52,10,3]] is fixed by Fig. 3;
[[104,10,5]] and [[199,10,7]] each have two sizes with the paper's n and k (both are built); [[74,10,4]] (Table VI) is
reachable by no rectangular patch of this word in any orientation and is built at the nearest natural size, n = 76.

Rotated surface codes (Table VI baselines) are included as rsc_*.
"""
from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from planar_common import check, summary  # noqa: E402

ARXIV = "2606.19482"
FAMILY = "directional tile codes"

WORDS = {   # notation of Tables II, III, VI and Fig. 5
    "w5": "NESEN",
    "w7": "N2ESEN2",
    "w9": "N2E2SE2N2",
    "w11": "N2E2SESE2N2",
    "hex": "ENES2WS2ENE",
}


# ---------------------------------------------------------------------------------------------------------
# generic construction

def letters(word):
    """'N2ESEN2' -> ['N','N','E','S','E','N','N'] (a digit repeats the preceding letter)."""
    out, i = [], 0
    while i < len(word):
        c = word[i]
        assert c in "NESW", "bad letter %r" % c
        i += 1
        num = ""
        while i < len(word) and word[i].isdigit():
            num += word[i]
            i += 1
        out += [c] * (int(num) if num else 1)
    return out


def _primal_step(c, x, y):
    """Edge traversed by a step from the vertex (x,y), and the new vertex."""
    if c == "N":
        return ("v", x, y), (x, y + 1)
    if c == "S":
        return ("v", x, y - 1), (x, y - 1)
    if c == "E":
        return ("h", x, y), (x + 1, y)
    return ("h", x - 1, y), (x - 1, y)


def _dual_step(c, x, y):
    """Edge crossed by a step from the plaquette with lower-left vertex (x,y), and the new plaquette."""
    if c == "N":
        return ("h", x, y + 1), (x, y + 1)
    if c == "S":
        return ("h", x, y), (x, y - 1)
    if c == "E":
        return ("v", x + 1, y), (x + 1, y)
    return ("v", x, y), (x - 1, y)


def _fine(e):
    """Edge midpoint in half-lattice units (the hardware grid)."""
    t, i, j = e
    return (2 * i + 1, 2 * j) if t == "h" else (2 * i, 2 * j + 1)


def parity_condition(word):
    """Definition 1: every displacement vector (from an edge of the ordered string to a later one) with odd
    vertical displacement, in hardware-grid units, occurs an even number of times."""
    path, v = [], (0, 0)
    for c in letters(word):
        e, v = _primal_step(c, *v)
        path.append(_fine(e))
    cnt = Counter((path[j][0] - path[i][0], path[j][1] - path[i][1])
                  for i in range(len(path)) for j in range(i + 1, len(path)))
    return all(m % 2 == 0 for (dx, dy), m in cnt.items() if dy % 2)


def tiles(word):
    """X and Z tiles of a directional word, in walk order, in box coordinates.

    Returns dict with x_tile, z_tile (ordered edge lists), box (Bx, By), x_start (vertex where the X walk starts),
    z_start (lower-left vertex of the plaquette where the Z walk starts)."""
    steps = letters(word)
    path, v = [], (0, 0)
    for c in steps:
        e, v = _primal_step(c, *v)
        path.append(e)
    assert len(set(path)) == len(path), "the string revisits an edge"
    mx, my = min(e[1] for e in path), min(e[2] for e in path)
    xt = [(t, i - mx, j - my) for t, i, j in path]
    bx, by = 1 + max(e[1] for e in xt), 1 + max(e[2] for e in xt)

    def t2(e):
        t, a, b = e
        return ("v" if t == "h" else "h", bx - 1 - a, by - 1 - b)

    zt = [t2(e) for e in reversed(xt)]
    # the Z walk: same word on the dual lattice, starting at the plaquette that crosses zt[0] with step d_1
    t, a, b = zt[0]
    c = steps[0]
    start = {"N": (a, b - 1), "S": (a, b), "E": (a - 1, b), "W": (a, b)}[c]
    walk, p = [], start
    for c in steps:
        e, p = _dual_step(c, *p)
        walk.append(e)
    assert walk == zt, "Z tile is not the same word on the dual lattice (word not palindromic?)"
    assert parity_condition(word), "Definition 1 parity condition fails"
    return {"x_tile": xt, "z_tile": zt, "box": (bx, by), "x_start": (-mx, -my), "z_start": start}


def directional_tile_code(word, M, N):
    """Directional tile code of the word on the paper's M x N patch ((M+1) rows x (N+1) columns of bulk anchors).

    Returns a partial instance dict: hx, hz, xy, x_order / z_order (per check, the qubit met at each step of the
    word, None where the edge was pruned or lies outside the arrays), check positions and construction details."""
    tl = tiles(word)
    xt, zt = tl["x_tile"], tl["z_tile"]
    bx, by = tl["box"]
    ncol, nrow = N + 1, M + 1
    lx, ly = ncol + bx - 1, nrow + by - 1
    arrays = {(t, i, j) for t in "hv" for i in range(lx) for j in range(ly)}
    x_anchors = [(a, b) for b in range(-(by - 1), nrow + by - 1) for a in range(ncol)]
    z_anchors = [(a, b) for b in range(nrow) for a in range(-(bx - 1), ncol + bx - 1)]

    def support(tile, a, b):
        return [(t, a + i, b + j) if (t, a + i, b + j) in arrays else None for t, i, j in tile]

    xs = [support(xt, a, b) for a, b in x_anchors]
    zs = [support(zt, a, b) for a, b in z_anchors]
    in_x = {e for s in xs for e in s if e is not None}
    in_z = {e for s in zs for e in s if e is not None}
    keep = in_x & in_z

    def pos(e):
        t, i, j = e
        return (i + 0.5, float(j)) if t == "h" else (float(i), j + 0.5)

    qubits = sorted(keep, key=lambda e: (pos(e)[1], pos(e)[0]))
    index = {e: s for s, e in enumerate(qubits)}

    def rows(sups, anchors, start, dual):
        mats, orders, starts, anch = [], [], [], []
        for s, (a, b) in zip(sups, anchors):
            order = [index.get(e) if e is not None else None for e in s]
            r = 0
            for q in order:
                if q is not None:
                    r ^= 1 << q
            if r:
                mats.append(r)
                orders.append(order)
                anch.append((a, b))
                sx, sy = a + start[0], b + start[1]
                starts.append((sx + 0.5, sy + 0.5) if dual else (float(sx), float(sy)))
        return mats, orders, starts, anch

    hx, x_order, x_pos, x_anch = rows(xs, x_anchors, tl["x_start"], False)
    hz, z_order, z_pos, z_anch = rows(zs, z_anchors, tl["z_start"], True)
    return {
        "hx": hx, "hz": hz, "xy": [pos(e) for e in qubits],
        "x_order": x_order, "z_order": z_order,
        "x_check_xy": x_pos, "z_check_xy": z_pos,
        "construction": {
            "word": word, "w": len(letters(word)), "M": M, "N": N,
            "bulk_anchors": (ncol, nrow), "box": (bx, by), "arrays": (lx, ly),
            "x_tile": xt, "z_tile": zt, "x_walk_start": tl["x_start"], "z_walk_start_plaquette": tl["z_start"],
            "x_anchors": x_anch, "z_anchors": z_anch,
            "qubits": ["%s(%d,%d)" % e for e in qubits],
            "removed_edges": len(arrays) - len(keep),
        },
    }


def rotated_surface_code(d):
    """[[d^2,1,d]] rotated surface code: data on a d x d grid at (i, j); weight-4 plaquettes in a checkerboard,
    weight-2 X checks on the bottom/top sides and weight-2 Z checks on the left/right sides."""
    qubit = {(i, j): j * d + i for j in range(d) for i in range(d)}
    hx, hz = [], []
    for b in range(-1, d):
        for a in range(-1, d):
            cell = [qubit[(a + u, b + v)] for u in (0, 1) for v in (0, 1) if (a + u, b + v) in qubit]
            xtype = (a + b) % 2 == 0
            bulk = len(cell) == 4
            x_side = len(cell) == 2 and xtype and b in (-1, d - 1)          # bottom / top
            z_side = len(cell) == 2 and not xtype and a in (-1, d - 1)      # left / right
            if bulk or x_side or z_side:
                (hx if xtype else hz).append(sum(1 << q for q in cell))
    return {"hx": hx, "hz": hz, "xy": [(float(i), float(j)) for j in range(d) for i in range(d)]}


# ---------------------------------------------------------------------------------------------------------
# instances

D_UNSTATED = ("method not stated for this table; the paper's only statement on distance computation (App. B, "
              "Table III caption) is integer programming, which terminated for distances <= 20, and QDistRnd upper "
              "bounds above 20; all values here are <= 15, so presumably exact IP values")
D_TABLE3 = ("d_Z by integer programming (exact; App. B, Table III caption); d_X is printed as an upper bound "
            "'<= %d' from QDistRnd because the IP did not terminate for distances above 20 (same caption)")
FIG8 = ("Fig. 8 plots this size on its 'uniform distance d = d_X = d_Z' axis (the Table IV fits suggest the larger "
        "of d_X, d_Z may exceed d by 1-2 for w = 11)")
HEX = ("square-lattice tile code of ENES2WS2ENE; the hexagonal grid enters only through the hardware embedding "
       "(Fig. 3, degree-3 brick-wall graph, drawn rotated by 90 degrees). The paper gives no M, N for hexagonal codes")


def _dtc(name, word_key, M, N, n, k, d, locator, dx=None, dz=None, d_kind="unknown", d_method=D_UNSTATED, notes="",
         dx_kind=None):
    """dx_kind: the kind of the paper's dx where it differs from d_kind (Table III: d_Z exact, d_X an upper bound)."""
    inst = directional_tile_code(WORDS[word_key], M, N)
    inst.update(name=name, family=FAMILY, arxiv=ARXIV, locator=locator, grid="hexagonal" if word_key == "hex"
                else "square", n_paper=n, k_paper=k, dx=dx, dz=dz, d=d, d_kind=d_kind, d_method=d_method,
                notes=("(M,N) = (%d,%d), word %s. " % (M, N, WORDS[word_key])) + notes)
    if dx_kind is not None:
        inst["dx_kind"] = dx_kind
    return inst


def instances():
    """Every code whose n and k are printed in v2: Tables II, III, V, VI and the captions of Figs. 1, 3, 5, 9."""
    out = []
    # w = 5, NESEN
    out.append(_dtc("dtc_w5_18_2_2", "w5", 1, 1, 18, 2, 2, "Fig. 5 caption (one extraction round drawn)",
                    dx=3, dz=2, notes="Paper: [[18,2,dx=3,dz=2]]; method not stated. Fig. 5 shows 18 data, 6 X and "
                    "10 Z checks, as built. Exhaustive check here (sanity check of the dx/dz orientation): dx = 3, "
                    "dz = 2."))
    out.append(_dtc("dtc_w5_259_2_4", "w5", 22, 3, 259, 2, 4, "Table III row 1 (App. B, biased noise)",
                    dx=37, dz=4, d_kind="exact", d_method=D_TABLE3 % 37, dx_kind="upper_bound",
                    notes="Paper: [[259,2,<=37,4]], n_r = 58. dx = 37 is an upper bound only."))
    # w = 7, N2ESEN2: M = N = d - 2 (Table V lists d = 3..9; Table VI d = 3..6; Table II d = 5, 9; Figs. 1, 9)
    w7 = {3: "Table V; Table VI", 4: "Table V; Table VI", 5: "Table II; Table V; Table VI; Fig. 1(b); Fig. 7; "
          "Fig. 9", 6: "Table V; Table VI", 7: "Table V; Fig. 9", 8: "Table V", 9: "Table II; Table V"}
    fig1 = (" Fig. 1(b) shows 60 data, 28 X and 28 Z checks (routing-optimised layout with shifted boundary "
            "qubits), as built.")
    for d, loc in w7.items():
        n = 2 * d * (d + 1)
        out.append(_dtc("dtc_w7_%d_4_%d" % (n, d), "w7", d - 2, d - 2, n, 4, d, loc,
                        notes=FIG8 + "." + (fig1 if d == 5 else "")))
    out.append(_dtc("dtc_w7_269_4_5", "w7", 22, 3, 269, 4, 5, "Table III row 2", dx=28, dz=5, d_kind="exact",
                    d_method=D_TABLE3 % 28, dx_kind="upper_bound",
                    notes="Paper: [[269,4,<=28,5]], n_r = 87. dx = 28 is an upper bound only."))
    # w = 9, N2E2SE2N2: (M,N) from the Fig. 8 routing counts (= Table IV formulas)
    for (M, N, n, d, loc) in [(1, 3, 52, 3, "Table VI"), (2, 4, 76, 4, "Table VI"), (3, 6, 115, 5, "Table VI"),
                              (4, 8, 162, 6, "Table II; Table VI"), (7, 14, 351, 9, "Table II")]:
        out.append(_dtc("dtc_w9_%d_10_%d" % (n, d), "w9", M, N, n, 10, d, loc, notes=FIG8 + "."))
    out.append(_dtc("dtc_w9_365_10_4", "w9", 19, 4, 365, 10, 4, "Table III row 3", dx=31, dz=4, d_kind="exact",
                    d_method=D_TABLE3 % 31, dx_kind="upper_bound",
                    notes="Paper: [[365,10,<=31,4]], n_r = 196. dx = 31 is an upper bound "
                    "only."))
    # w = 11, N2E2SESE2N2
    for (M, N, n, d, loc) in [(1, 5, 74, 5, "Table VI"), (2, 6, 104, 6, "Table VI"), (3, 11, 182, 10, "Table VI"),
                              (4, 13, 241, 12, "Table II; Table VI"),
                              (5, 16, 323, 15, "Table II; abstract; Example 4 (346 -> 235 -> 165 routing sites)")]:
        out.append(_dtc("dtc_w11_%d_14_%d" % (n, d), "w11", M, N, n, 14, d, loc, notes=FIG8 + "."))
    out.append(_dtc("dtc_w11_537_14_12", "w11", 12, 13, 537, 14, 12, "Table III row 4", dx=35, dz=12,
                    d_kind="exact", d_method=D_TABLE3 % 35, dx_kind="upper_bound",
                    notes="Paper: [[537,14,<=35,12]], n_r = 216. dx = 35 is an upper bound only."))
    # hexagonal grid, ENES2WS2ENE
    out.append(_dtc("dtc_hex_52_10_3", "hex", 3, 1, 52, 10, 3, "Table II; Table VI; Fig. 3", notes=HEX +
                    "; Fig. 3 shows 52 data, 22 X and 20 Z checks, exactly this size (the other size with n = 52, "
                    "(M,N) = (6,0), has 14 X and 28 Z checks)."))
    out.append(_dtc("dtc_hex_74_10_4", "hex", 4, 2, 74, 10, 4, "Table VI", notes=HEX + ". MISMATCH: n = 74 is not "
                    "reachable: for this word n = ((2x+3)(2y+7) - 1)/2 with x = N+1 columns and y = M+1 rows, and "
                    "2*74+1 = 149 is prime; no rotation or reflection of the word helps either. Built at (M,N) = "
                    "(4,2), n = 76, the step between [[52,10,3]] at (3,1) and [[104,10,5]] at (5,3); the other "
                    "near sizes are n = 73 at (6,1) and n = 77 at (11,0). The paper's 74 may be a typo for 76: the "
                    "square w = 9 family obeys the same n formula with M and N exchanged and has [[76,10,4]] at the "
                    "mirrored size (2,4). Whether this matrix has d = 4 is not established."))
    out.append(_dtc("dtc_hex_104_10_5", "hex", 5, 3, 104, 10, 5, "Table VI", notes=HEX + "; size chosen as the "
                    "continuation of (3,1), (4,2); the other size with n = 104 is dtc_hex_104_10_5_m1n7."))
    out.append(_dtc("dtc_hex_104_10_5_m1n7", "hex", 1, 7, 104, 10, 5, "Table VI (alternative size)", notes=HEX +
                    "; alternative to dtc_hex_104_10_5 with the same n, k (2 bulk anchor rows, 8 columns)."))
    out.append(_dtc("dtc_hex_199_10_7_m6n7", "hex", 6, 7, 199, 10, 7, "Table II; Table VI (one of two sizes)",
                    notes=HEX + "; the two sizes (6,7) and (5,8) both give n = 199, k = 10; which one the paper used is "
                    "not determinable from the text (circuit-qubit count in Fig. 2 ~ 522 fits both)."))
    out.append(_dtc("dtc_hex_199_10_7_m5n8", "hex", 5, 8, 199, 10, 7, "Table II; Table VI (one of two sizes)",
                    notes=HEX + "; see dtc_hex_199_10_7_m6n7."))
    # rotated surface codes, the baselines of Table VI / Fig. 2
    for d in (3, 5, 7):
        inst = rotated_surface_code(d)
        inst.update(name="rsc_%d_1_%d" % (d * d, d), family="rotated surface code (baseline)", arxiv=ARXIV,
                    locator="Table VI (4-CX and 4-CXSWAP rows); Fig. 2", grid="square", n_paper=d * d, k_paper=1,
                    dx=d, dz=d, d=d, d_kind="exact", d_method="standard (proven) distance of the rotated surface "
                    "code; the paper only labels it", notes="Comparison code, not a directional tile code. Both "
                    "circuit variants (4-CX, 4-CXSWAP) use this same code.")
        out.append(inst)
    return [check(i) for i in out]


def figure_instances():
    """Fig. 8 sizes whose n is not printed in v2 (uniform-distance points beyond the tables).

    (M,N) are recovered from the plotted routing counts with the Table IV formulas (w = 7: M = N = d-2;
    w = 9: M = d-2, N = 2(d-2)).  n_paper is None except for [[217,10,7]], which the task description lists
    (presumably v1's Table II)."""
    out = []
    for d in range(10, 16):
        n = 2 * d * (d + 1)
        out.append(_dtc("dtc_w7_%d_4_%d" % (n, d), "w7", d - 2, d - 2, None, None, d, "Fig. 8 (w = 7 point at d = "
                        "%d)" % d, notes="Figure only; n not printed. " + FIG8 + "."))
    for d in (7, 8, 10):
        M, N = d - 2, 2 * (d - 2)
        inst = _dtc("", "w9", M, N, None, None, d, "Fig. 8 (w = 9 point at d = %d)" % d,
                    notes="Figure only; n not printed in v2. " + FIG8 + ".")
        n = len(inst["xy"])
        inst["name"] = "dtc_w9_%d_10_%d" % (n, d)
        if d == 7:
            inst.update(n_paper=217, k_paper=10, notes=inst["notes"] + " [[217,10,7]] is not printed in v2; the task "
                        "description lists it in Table II (presumably v1).")
        out.append(inst)
    return [check(i) for i in out]


def sanity():
    """Small checks against the figures (no distance computations)."""
    msgs = []
    for word in WORDS.values():
        tiles(word)                       # Z tile = same word on the dual lattice; Definition 1 parity
    for key, M, N, counts, where in [("w7", 3, 3, (60, 28, 28), "Fig. 1(b)"), ("hex", 3, 1, (52, 22, 20), "Fig. 3"),
                                     ("w5", 1, 1, (18, 6, 10), "Fig. 5")]:
        c = directional_tile_code(WORDS[key], M, N)
        got = (len(c["xy"]), len(c["hx"]), len(c["hz"]))
        assert got == counts, (where, got, counts)
        msgs.append("%s: data/X/Z checks %s as drawn" % (where, got))
    # Fig. 8 bottom: w = 7 circuit qubits per logical (4d^2+9d+1)/4 with routing 3M+2N+15 (Table IV)
    for d in range(3, 16):
        c = directional_tile_code(WORDS["w7"], d - 2, d - 2)
        n_circ = len(c["xy"]) + len(c["hx"]) + len(c["hz"]) + 5 * (d - 2) + 15
        assert n_circ == 4 * d * d + 9 * d + 1, (d, n_circ)
    msgs.append("Fig. 8: w = 7 n_circ = data + checks + (3M+2N+15) equals k(4d^2+9d+1)/4 for d = 3..15")
    return msgs


if __name__ == "__main__":
    print(summary(instances()))
    print("-- figure-only sizes (Fig. 8; n not printed in v2, so not compared)")
    for inst in figure_instances():
        print("%-28s n=%4d  k=%3d  d=%d  (M,N)=(%d,%d)  %s" % (
            inst["name"], inst["n"], inst["k"], inst["d"], inst["construction"]["M"], inst["construction"]["N"],
            "task lists [[217,10,7]]" if inst["n_paper"] else ""))
    print("-- sanity")
    print("\n".join(sanity()))
