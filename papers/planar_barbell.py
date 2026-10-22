"""Barbell codes of arXiv:2606.06062 (Choe, Steffan, Vigneau, Parrado-Rodriguez, Ku, Leib, Pereira, Simkovic,
"Barbell Codes: qLDPC Codes for Superconducting Quantum Hardware"), in the interface of planar_common.py.

A barbell code is a tile code (arXiv:2504.09171) whose X and Z checks can be measured pairwise on IQM's six-qubit
star lattice plus one near-local coupler per check pair. The construction (Supp. Sec. 3.2) only adds dummy checks with
empty support, adds one ancilla per check, and translates each of the four qubit sublattices (X checks, Z checks,
horizontal and vertical data qubits) by a fixed integer vector. None of this changes the stabilizer group: hx and hz
below are exactly the tile code's checks, and only the positions differ. The paper says so itself: barbell codes are
"a special case of tile codes".

Conventions (Supp. Sec. 3.1, Eqs. (6)-(12)):
  data qubits   q(h,u), q(v,u) for u in [0,L-1] x [0,M-1]; q(h,u) is the edge {u, u+(1,0)}, q(v,u) is {u, u+(0,1)},
                so n = 2*L*M (Table 3's caption writes n = 2(L+D)(M+D); its L is the number of bulk tiles per side,
                L - D here). Qubit j = 2*(u2*L + u1) + (0 for h, 1 for v).
  X check at u  support {q(h,u+a) : a in tile_X.h} + {q(v,u+b) : b in tile_X.v}, truncated to existing qubits;
                u in U_X,tile = ([0,L-D-1] x [-D,M-1]) + corners          (Eqs. (9), (11))
  Z check at u  the same with tile_Z, at u in U_Z,tile = ([-D,L-1] x [0,M-D-1]) + corners (Eqs. (10), (12));
                its ancilla sits on the plaquette u + (1/2, 1/2)
  tiles         edges of the (D+1) x (D+1) box anchored at its lower-left vertex (tile-code convention of 2504.09171);
                read from the vector content of the figure files weight{6_1,6_2,8_1,10_1}_tile.pdf (Table 3, column
                "Tile"). Each X/Z pair satisfies the tile-code duality (T2) of 2504.09171.

Three sets of data-qubit positions, all planar:
  xy        the barbell layout of Supp. Sec. 3.2: q(t,u) moved to translated index w = u + v_t and drawn at
            w + (1/2,0) (t = h) or w + (0,1/2) (t = v); X ancilla at u, its partner Z ancilla at u + v_XZ + v_Z + (1/2,1/2).
            In these square-grid coordinates the six-qubit-star hexagons are drawn as slanted parallelograms.
  xy_chip   the same lattice drawn with regular hexagons of unit edge (the physical chip picture, Fig. 1(a) and Fig. 7):
            index w of sublattice t goes to w1*(3,-sqrt3) + w2*(-3/2, 3*sqrt3/2) + c_t, c_X = (0,0), c_Z = (1,0),
            c_h = (3/2,-sqrt3/2), c_v = (-1/2, sqrt3/2). Derived here, not given in the paper; it makes every type-A/B
            hexagon regular, gives the weight-8 coupler length sqrt(139) = 11.79 (Supp. Eq. (5): 11.8a) and matches
            the label geometry of Fig. 1(a) up to a 30 degree rotation.
  xy_tile   the untranslated edge midpoints of the tile-code drawing (Fig. 3, Fig. 5(a)).

check_barbell() re-derives the hardware adjacency from the type-A/B hexagons of the methods section and confirms both
barbell conditions of Supp. Sec. 3.2 for every check, an independent test of the tile reading and of the coordinates.
For the weight-8 family, W8_SCHEDULE is the CNOT order of Fig. 1(b), with the data labels of Fig. 1(a) located on the
lattice; check_w8_schedule() confirms that it covers every check exactly and never uses a data qubit twice in a layer.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import planar_common  # noqa: E402

ARXIV = "2606.06062"
FAMILY = "barbell codes"

D_METHOD = ("not stated: Supp. Table 3 lists [[n,k,d]] (only d, no separate dX/dZ) and the paper never says how d "
            "was obtained (no ILP, QDistRnd or BP-OSD is named); the companion tile-code paper 2504.09171 used "
            "QDistRnd, then ILP for its own codes")

# Tiles: "h" entry (x, y) = horizontal edge {(x,y),(x+1,y)}, "v" entry (x, y) = vertical edge {(x,y),(x,y+1)}.
FAMILIES = {
    "w6a": dict(
        label="weight 6, first row of Supp. Table 3",
        figure="weight6_1_tile.pdf / weight_6_1_barbell.pdf",
        D=2,
        tile_x=dict(h=[(0, 0), (1, 2), (2, 0)], v=[(0, 0), (0, 1), (2, 2)]),
        tile_z=dict(h=[(0, 0), (2, 1), (2, 2)], v=[(0, 2), (1, 0), (2, 2)]),
        corners_x=lambda L, M, D: [],
        corners_z=lambda L, M, D: [(-D, -1)],
        v_xz=(0, 0), v_z=(-1, 1), v_h=(-2, 0), v_v=(-1, -1),
        table=[(128, 7, 6), (162, 7, 7), (200, 7, 8), (242, 7, 9), (288, 7, 11), (338, 7, 13), (392, 7, 14)],
    ),
    "w6b": dict(
        label="weight 6, second row of Supp. Table 3",
        figure="weight6_2_tile.pdf / weight_6_2_barbell.pdf",
        D=2,
        tile_x=dict(h=[(0, 1), (0, 2), (2, 0)], v=[(0, 0), (1, 0), (2, 2)]),
        tile_z=dict(h=[(0, 0), (1, 2), (2, 2)], v=[(0, 2), (2, 0), (2, 1)]),
        corners_x=lambda L, M, D: [],
        corners_z=lambda L, M, D: [],
        v_xz=(-1, 0), v_z=(-1, 1), v_h=(-2, 0), v_v=(-1, -1),
        table=[(128, 8, 6), (162, 8, 7), (200, 8, 9), (242, 8, 10), (288, 8, 12), (338, 8, 13), (392, 8, 15)],
    ),
    "w8": dict(
        label="weight 8, third row of Supp. Table 3 (the family simulated in the main text, Fig. 2)",
        figure="weight8_1_tile.pdf / weight_8_1_barbell.pdf; also Fig. 3(a) and Fig. 5",
        D=3,
        tile_x=dict(h=[(0, 1), (2, 3), (3, 0), (3, 1)], v=[(0, 3), (1, 0), (1, 3), (3, 2)]),
        tile_z=dict(h=[(0, 1), (2, 0), (2, 3), (3, 0)], v=[(0, 2), (0, 3), (1, 0), (3, 2)]),
        corners_x=lambda L, M, D: [(L - D, -D)],
        corners_z=lambda L, M, D: [(-D, M - D)],
        v_xz=(0, 0), v_z=(-2, 2), v_h=(-3, 0), v_v=(-2, -1),
        table=[(242, 16, 8), (288, 16, 9), (338, 16, 10), (392, 16, 11), (450, 16, 14)],
    ),
    "w10": dict(
        label="weight 10, fourth row of Supp. Table 3",
        figure="weight10_1_tile.pdf / weight_10_1_barbell.pdf",
        D=3,
        tile_x=dict(h=[(0, 1), (1, 3), (2, 3), (3, 0), (3, 1)], v=[(0, 2), (0, 3), (1, 0), (2, 0), (3, 2)]),
        tile_z=dict(h=[(0, 1), (1, 3), (2, 3), (3, 0), (3, 1)], v=[(0, 2), (0, 3), (1, 0), (2, 0), (3, 2)]),
        corners_x=lambda L, M, D: [(L - D, -D)],
        corners_z=lambda L, M, D: [(-D, M - D)],
        v_xz=(0, 0), v_z=(-2, 2), v_h=(-3, 0), v_v=(-2, -1),
        table=[(162, 16, 8), (200, 16, 10), (242, 16, 11), (288, 16, 12), (338, 16, 13), (392, 16, 14),
               (450, 16, 15), (512, 16, 16)],
    ),
}

# Local neighbours of the ancillas on the six-qubit star lattice, Supp. Sec. 3.3, Eqs. (28)-(31).
N_XH = {(-1, -1), (-1, 0), (0, 0), (0, 1)}
N_XV = {(-1, -1), (0, -1), (0, 0), (1, 1)}
N_ZH = {(-1, -1), (0, 0), (0, 1), (1, 1)}
N_ZV = {(0, -1), (0, 0), (1, 0), (1, 1)}

# Type-A and type-B hexagons of the six-qubit star lattice (methods, "Barbell codes on the six-qubit star lattice"),
# in doubled coordinates so that all vertices are integers.
HEX_A = [(0, 0), (1, 1), (2, 2), (2, 3), (1, 2), (0, 1)]
HEX_B = [(0, 0), (-1, -1), (-1, -2), (0, -1), (1, 0), (1, 1)]

# Regular-hexagon chip coordinates (see the module docstring).
_S3 = math.sqrt(3.0)
CHIP_E1, CHIP_E2 = (3.0, -_S3), (-1.5, 1.5 * _S3)
CHIP_C = {"X": (0.0, 0.0), "Z": (1.0, 0.0), "h": (1.5, -_S3 / 2), "v": (-0.5, _S3 / 2)}

# Weight-8 CNOT order of Fig. 1(b). Layer r = 1..8 lists (type, offset) of the data qubit hit by the X ancilla and by
# the Z ancilla; offsets are relative to the translated index of that ancilla (u for a^X, u + v_XZ + v_Z for a^Z).
# Layers 1-4: CNOT ancilla -> data on X-check qubits; layers 5-8: CNOT data -> ancilla on Z-check qubits. Fig. 1 labels:
# at a^X 1 = h(-1,0), 2 = v(-1,-1), 3 = h(0,0), 4 = v(1,1), 5 = h(0,1); at a^Z 1 = v(1,0), 2 = h(1,1), 3 = v(0,0),
# 4 = h(-1,-1), 5 = v(0,-1). The full cycle is RX a^X, R a^Z | CNOT a^X a^Z | layers 1-8 | CNOT a^X a^Z | MX a^X, M a^Z.
W8_SCHEDULE = [
    (("h", (0, 1)), ("v", (1, 0))),     # 1: a^X -> 5, a^Z -> 1
    (("h", (0, 0)), ("v", (0, 0))),     # 2: a^X -> 3, a^Z -> 3
    (("v", (-1, -1)), ("h", (1, 1))),   # 3: a^X -> 2, a^Z -> 2
    (("v", (1, 1)), ("h", (-1, -1))),   # 4: a^X -> 4, a^Z -> 4
    (("v", (-1, -1)), ("h", (-1, -1))),  # 5: 2 -> a^X, 4 -> a^Z
    (("v", (1, 1)), ("h", (1, 1))),     # 6: 4 -> a^X, 2 -> a^Z
    (("h", (-1, 0)), ("v", (0, -1))),   # 7: 1 -> a^X, 5 -> a^Z
    (("h", (0, 0)), ("v", (0, 0))),     # 8: 3 -> a^X, 3 -> a^Z
]


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def chip_xy(t, w):
    """Regular-hexagon position of the qubit of sublattice t ('X', 'Z', 'h', 'v') with translated index w."""
    c = CHIP_C[t]
    return (w[0] * CHIP_E1[0] + w[1] * CHIP_E2[0] + c[0], w[0] * CHIP_E1[1] + w[1] * CHIP_E2[1] + c[1])


def build(key, L, M=None):
    """The barbell code of family `key` on the L x M qubit region (L, M as in Supp. Eqs. (6)-(7))."""
    f = FAMILIES[key]
    M = L if M is None else M
    D = f["D"]
    index = {}
    for u2 in range(M):
        for u1 in range(L):
            index[("h", (u1, u2))] = len(index)
            index[("v", (u1, u2))] = len(index)
    n = len(index)

    def support(tile, u):
        out = []
        for t in ("h", "v"):
            for a in tile[t]:
                j = index.get((t, _add(u, a)))
                if j is not None:
                    out.append(j)
        return sorted(out)

    ux_tile = [(u1, u2) for u2 in range(-D, M) for u1 in range(0, L - D)] + f["corners_x"](L, M, D)
    uz_tile = [(u1, u2) for u2 in range(0, M - D) for u1 in range(-D, L)] + f["corners_z"](L, M, D)
    xs = [(u, support(f["tile_x"], u)) for u in ux_tile]
    zs = [(u, support(f["tile_z"], u)) for u in uz_tile]
    # Step 4 of the tile-code construction: drop qubits outside every X or every Z check, then empty checks.
    in_x = set(j for _, s in xs for j in s)
    in_z = set(j for _, s in zs for j in s)
    assert in_x & in_z == set(range(n)), "qubits outside all X or all Z checks (the paper removes none)"
    xs = [(u, s) for u, s in xs if s]
    zs = [(u, s) for u, s in zs if s]

    rev = {j: tu for tu, j in index.items()}
    shift = {"h": f["v_h"], "v": f["v_v"]}
    half = {"h": (0.5, 0.0), "v": (0.0, 0.5)}
    xy, xy_tile, xy_chip = [], [], []
    for j in range(n):
        t, u = rev[j]
        w = _add(u, shift[t])
        xy_tile.append((u[0] + half[t][0], u[1] + half[t][1]))
        xy.append((w[0] + half[t][0], w[1] + half[t][1]))
        xy_chip.append(chip_xy(t, w))

    # Barbells (Supp. Eqs. (13)-(15), (25)-(26)): X anchors with dummies, partner Z anchor u + v_XZ.
    xrow = {u: i for i, (u, _) in enumerate(xs)}
    zrow = {u: i for i, (u, _) in enumerate(zs)}
    ux_all = list(dict.fromkeys(ux_tile + [_sub(u, f["v_xz"]) for u in uz_tile]))
    barbells = []
    for u in ux_all:
        uzt = _add(u, f["v_xz"])
        az = _add(uzt, f["v_z"])
        barbells.append(dict(x_row=xrow.get(u), z_row=zrow.get(uzt), x_anchor=u, z_anchor=uzt,
                             anc_x=(float(u[0]), float(u[1])), anc_z=(az[0] + 0.5, az[1] + 0.5),
                             anc_x_chip=chip_xy("X", u), anc_z_chip=chip_xy("Z", az)))
    return dict(n=n, index=index, rev=rev, xs=xs, zs=zs, xy=xy, xy_tile=xy_tile, xy_chip=xy_chip,
                barbells=barbells, D=D, L=L, M=M)


def _hex_mates(p2):
    """Doubled-coordinate positions sharing a type-A or type-B hexagon with the doubled position p2."""
    mates = set()
    for shape in (HEX_A, HEX_B):
        for off in shape:
            a = _sub(p2, off)
            if a[0] % 2 or a[1] % 2:
                continue  # hexagon anchors (a, b) are integer points
            for o in shape:
                mates.add(_add(a, o))
    mates.discard(p2)
    return mates


def _d2(p):
    return (round(2 * p[0]), round(2 * p[1]))


def check_barbell(key, code):
    """Both barbell conditions of Supp. Sec. 3.2, with adjacency taken (i) from the neighbour sets of Eqs. (28)-(31)
    and (ii) independently from the hexagons; returns counts of the split of every check over the two ancillas."""
    f = FAMILIES[key]
    rev = code["rev"]
    shift = {"h": f["v_h"], "v": f["v_v"]}
    xy2 = [_d2(p) for p in code["xy"]]
    splits = {}
    for b in code["barbells"]:
        ux, uz = b["x_anchor"], _add(b["z_anchor"], f["v_z"])  # translated ancilla indices
        mx, mz = _hex_mates(_d2(b["anc_x"])), _hex_mates(_d2(b["anc_z"]))
        for kind, row in (("X", b["x_row"]), ("Z", b["z_row"])):
            if row is None:
                continue
            nx = nz = 0
            for j in (code["xs"] if kind == "X" else code["zs"])[row][1]:
                t, u = rev[j]
                w = _add(u, shift[t])
                adj_x = _sub(w, ux) in (N_XH if t == "h" else N_XV)
                adj_z = _sub(w, uz) in (N_ZH if t == "h" else N_ZV)
                assert adj_x == (xy2[j] in mx) and adj_z == (xy2[j] in mz), "neighbour sets disagree with hexagons"
                assert adj_x or adj_z, "%s check at %s not measurable by its barbell" % (kind, b["x_anchor"])
                assert not (adj_x and adj_z), "qubit adjacent to both ancillas of one barbell"
                nx += adj_x
                nz += adj_z
            splits[(kind, nx, nz)] = splits.get((kind, nx, nz), 0) + 1
    return splits


def check_w8_schedule(code):
    """W8_SCHEDULE on a weight-8 code: every check's support is hit exactly once (gates on absent boundary qubits are
    skipped, as the paper prescribes), and no data qubit is used twice in one layer."""
    f = FAMILIES["w8"]
    index = code["index"]
    shift = {"h": f["v_h"], "v": f["v_v"]}
    hits = [{} for _ in W8_SCHEDULE]
    for b in code["barbells"]:
        anc = (b["x_anchor"], _add(b["z_anchor"], f["v_z"]))
        for kind, row, layers in (("X", b["x_row"], range(0, 4)), ("Z", b["z_row"], range(4, 8))):
            if row is None:
                continue
            sup = set((code["xs"] if kind == "X" else code["zs"])[row][1])
            got = []
            for r in layers:
                for side in (0, 1):
                    t, off = W8_SCHEDULE[r][side]
                    w = _add(anc[side], off)
                    j = index.get((t, _sub(w, shift[t])))
                    if j is not None and j in sup:
                        got.append(j)
                        hits[r][j] = hits[r].get(j, 0) + 1
            assert sorted(got) == sorted(sup), "schedule does not cover a %s check exactly" % kind
    assert all(c == 1 for h in hits for c in h.values()), "a data qubit is used twice in one layer"
    return [sum(h.values()) for h in hits]


def instances():
    out = []
    for key, f in FAMILIES.items():
        for (n_p, k_p, d_p) in f["table"]:
            L = int(round((n_p / 2) ** 0.5))
            assert 2 * L * L == n_p
            code = build(key, L)
            n = code["n"]
            hx = planar_common.from_cells([s for _, s in code["xs"]], n)
            hz = planar_common.from_cells([s for _, s in code["zs"]], n)
            splits = check_barbell(key, code)
            if key == "w8":
                check_w8_schedule(code)
            n_dummy = sum((b["x_row"] is None) + (b["z_row"] is None) for b in code["barbells"])
            d_method = D_METHOD
            if key == "w6b" and n_p == 288:
                d_method += ("; this instance is the [[288,8,12]] tile code of 2504.09171 App. B, Table II, sixth pair "
                             "with its X and Z tiles exchanged, a distance that paper says was confirmed by ILP")
            notes = ("%s; D=%d, L=M=%d (Table 3 caption's L would be %d); tiles from %s; %d X and %d Z checks "
                     "(%d corner X, %d corner Z), all independent; %d barbells (%d dummy checks); split of each "
                     "support over the two ancillas (kind, #at X ancilla, #at Z ancilla): count = %s; "
                     "xy = barbell square-grid positions (h moved by %s, v by %s), xy_chip = regular-hexagon chip "
                     "positions, xy_tile = tile-code edge midpoints; the code is identical to the tile code with "
                     "these tiles and corners"
                     % (f["label"], f["D"], L, L - f["D"], f["figure"], len(hx), len(hz),
                        len(f["corners_x"](L, L, f["D"])), len(f["corners_z"](L, L, f["D"])),
                        len(code["barbells"]), n_dummy, dict(sorted(splits.items())), f["v_h"], f["v_v"]))
            inst = dict(
                name="barbell_%s_%d_%d_%d" % (key, n_p, k_p, d_p),
                family=FAMILY,
                arxiv=ARXIV,
                locator="Supp. Sec. 3.3, Table 3 (%s); construction Supp. Secs. 3.1-3.2, Eqs. (6)-(31)%s"
                        % (f["label"], "; main text Fig. 2(b)" if key == "w8" else ""),
                n_paper=n_p, k_paper=k_p,
                dx=None, dz=None, d=d_p,
                d_kind="unknown",
                d_method=d_method,
                hx=hx, hz=hz,
                xy=code["xy"],
                xy_chip=code["xy_chip"],
                xy_tile=code["xy_tile"],
                barbells=code["barbells"],
                notes=notes,
            )
            out.append(planar_common.check(inst))
    return out


if __name__ == "__main__":
    print(planar_common.summary(instances()))
