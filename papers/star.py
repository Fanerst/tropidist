"""Literal depth-eight STAR bicycle-chain circuits (arXiv:2606.25011).

Appendix B.1, Eq. (8): a=1+y^3+x*y^2+x*y^4, b=a^dagger,
H_X=H_Z=[A|A^T] on Z_3 x Z_m, m=7,11,13.  Table 2 supplies
the default schedule, including its printed middle two Z couplings.

Schedule format: a mapping with keys ``X`` and ``Z``, each an eight-item
sequence of labels ``L1``..``L4``, ``R1``..``R4`` in time order.  Labels
denote actual data supports: Li = A_i, Ri = A_i^T, where
(A1,A2,A3,A4)=(xy^4,xy^2,y^3,1).  Thus a Z coupling printed as
``L,B_i^T`` becomes Li, and ``R,A_i^T`` becomes Ri.  B_i=A_i^T
is the natural index convention (the paper does not explicitly list B_i).
``schedule='paper'`` or None uses Table 2; ``schedule='mirror'`` transports
the saved sdbb_parallel circuit through an explicitly checked relabelling.

The Section III fault model is depolarization after preparation and gates,
measurement flips at p, and idle depolarization during entangling layers.
RX/MX are primitive X preparation/measurement, not additional H gates.
Every qubit participates in every CNOT layer, so full and noidle coincide.

Relation to selfdual_bb.py: 66 and 78 have identical check matrices after
the explicit relabelling below.  The 42 matrices are inequivalent: their
check-intersection graphs have 45 versus 39 triangles at each vertex.
This excludes arbitrary qubit/check permutations; it makes no stronger
claim about equivalence after changing stabilizer generators.
"""
from __future__ import annotations

import os
import sys
from itertools import combinations, permutations
from functools import lru_cache

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stabcode

MONOMIALS = ((1, 4), (1, 2), (0, 3), (0, 0))
PAPER_SCHEDULE = {
    "X": ("L1", "R1", "L2", "R2", "R3", "L3", "R4", "L4"),
    "Z": ("R4", "L4", "R3", "L2", "L3", "R2", "L1", "R1"),
}
CODES = {
    n: ((3, n // 6, MONOMIALS),
        "Appendix B.1 Eq. (8) and B.2 Table 2; " +
        ("check matrices inequivalent to selfdual_bb42; " if n == 42 else
         "check matrices equal to selfdual_bb up to explicit relabelling; ") +
        ("fault distance 5 stated as exact for the chosen d=6 schedule"
         if n == 42 else "no instance-specific exact fault-distance claim"),
        (n, 6, d), 5 if n == 42 else None)
    for n, d in ((42, 6), (66, 8), (78, 10))
}


def tag(key):
    return str(int(key))


def torus(key):
    key = int(key)
    if key not in CODES:
        raise KeyError(key)
    return stabcode.Torus((0, key // 6), (3, 0))


def matrices(key):
    T = torus(key)
    a = stabcode.shift_matrix(T, MONOMIALS)
    b = stabcode.shift_matrix(T, MONOMIALS, inverse=True)
    h = [u | (v << T.n) for u, v in zip(a, b)]
    return h, h.copy(), 2 * T.n


def _schedule(key, schedule):
    if schedule is None or schedule == "paper":
        schedule = PAPER_SCHEDULE
    elif schedule == "mirror":
        schedule = mirror_schedule(key)
    if not isinstance(schedule, dict) or set(schedule) != {"X", "Z"}:
        raise ValueError("schedule must have X and Z gate-order sequences")
    expected = {f"{side}{a}" for side in "LR" for a in range(1, 5)}
    orders = {}
    for basis in "XZ":
        order = tuple(schedule[basis])
        if len(order) != 8 or set(order) != expected:
            raise ValueError(f"{basis} order must contain each L1..L4,R1..R4 once")
        orders[basis] = order
    if any(x[0] == z[0] for x, z in zip(orders["X"], orders["Z"])):
        raise ValueError("X and Z checks must couple to opposite halves in each layer")
    return orders


def supports(key, schedule=None):
    T = torus(key)
    orders = _schedule(key, schedule)

    def data(s, label):
        side, a = label[0], int(label[1:]) - 1
        dx, dy = MONOMIALS[a]
        return T.shift(s, dx, dy) if side == "L" else T.n + T.shift(s, -dx, -dy)

    xs = [[(t, data(s, lab)) for t, lab in enumerate(orders["X"])] for s in range(T.n)]
    zs = [[(t, data(s, lab)) for t, lab in enumerate(orders["Z"])] for s in range(T.n)]
    return xs, zs, T


def layers(key, schedule=None):
    xs, zs, T = supports(key, schedule)
    n = 2 * T.n
    out = []
    for t in range(8):
        targets = [v for i, g in enumerate(xs) for v in (n + T.n + i, g[t][1])]
        targets += [v for i, g in enumerate(zs) for v in (g[t][1], n + i)]
        if len(targets) != len(set(targets)):
            raise ValueError("a CNOT layer touches a qubit more than once")
        out.append(targets)
    return out


@lru_cache(None)
def selfdual_relabelling(key):
    """(checks, data) mapping selfdual_bb indices to STAR indices.

    For 66/78, old (x,y) -> (-x,x+y), left data additionally +(1,2),
    right data additionally +(-1,-2).  Equality is checked row by row.
    For 42, a check-intersection graph invariant proves inequivalence.
    """
    import selfdual_bb
    key = int(key)
    if key == 42:
        raise ValueError("STAR42 and selfdual_bb42 check matrices are inequivalent: "
                         "check-intersection triangles per vertex are 45 versus 39")
    if key not in (66, 78):
        raise KeyError(key)
    row = next(c for c in selfdual_bb.CODES if c[0] == key)
    oldx, oldz, n, oldT, _ = selfdual_bb.build(row[3], row[4], row[5])
    T = torus(key)
    cp = [T.index(-x, x + y) for x, y in oldT.points]
    dp = [T.index(-x + 1, x + y + 2) for x, y in oldT.points]
    dp += [T.n + T.index(-x - 1, x + y - 2) for x, y in oldT.points]
    hx, hz, _ = matrices(key)
    assert sorted(cp) == list(range(T.n)) and sorted(dp) == list(range(n))
    for old, new in ((oldx, hx), (oldz, hz)):
        assert all(sum(1 << dp[q] for q in stabcode.bits(v)) == new[cp[s]]
                   for s, v in enumerate(old))
    return cp, dp


def mirror_schedule(key):
    """Transport the existing saved mirror circuit, preserving gate times."""
    import sdbb_parallel
    cp, dp = selfdual_relabelling(key)
    xs, zs, _ = sdbb_parallel.supports(int(key))
    T = torus(key)
    mapped = {}
    reference = {}
    for side in "LR":
        for a, (dx, dy) in enumerate(MONOMIALS, 1):
            reference[T.shift(0, dx, dy) if side == "L" else T.n + T.shift(0, -dx, -dy)] = f"{side}{a}"
    for basis, supports_ in (("X", xs), ("Z", zs)):
        old_s = cp.index(0)
        mapped[basis] = tuple(reference[dp[q]] for _, q in supports_[old_s])
    # Verify the entire circuit, rather than only the reference check.
    newx, newz, _ = supports(key, mapped)
    for old, new in ((xs, newx), (zs, newz)):
        assert all([(t, dp[q]) for t, q in g] == new[cp[s]] for s, g in enumerate(old))
    return mapped


def build_mirror(key, basis, rounds, p=0.001, noise="full"):
    return build(key, basis, rounds, p=p, noise=noise, schedule="mirror")


def translations(key):
    return torus(key).translations()[1:]


def schedule_is_valid(key, schedule=None):
    """Exact symbolic no-back-action check for simultaneous CSS extraction.

    For each X/Z ancilla pair, a shared data qubit contributes a residual
    ancilla CNOT iff its X interaction precedes its Z interaction.  The
    residual parity must be zero.  Together with complete supports and
    disjoint layers this is the clean-extraction correctness condition.
    """
    xs, zs, _ = supports(key, schedule)
    for x in xs:
        xt = {q: t for t, q in x}
        for z in zs:
            if sum(xt[q] < t for t, q in z if q in xt) % 2:
                return False
    return True


@lru_cache(None)
def _valid_orders():
    # Inferred extension of the cited BB grammar: preserve the internal
    # A1..A4 and B1..B4 X orders, interleave them, and permute the Z orders.
    # Each polynomial-product pair must cancel independent of exponents.
    out = []
    for left in combinations(range(8), 4):
        right = tuple(t for t in range(8) if t not in left)
        x = [None] * 8
        for i, t in enumerate(left, 1):
            x[t] = f"L{i}"
        for i, t in enumerate(right, 1):
            x[t] = f"R{i}"
        for pr in permutations(range(1, 5)):
            tzr = {i: t for t, i in zip(left, pr)}
            for pl in permutations(range(1, 5)):
                tzl = {i: t for t, i in zip(right, pl)}
                if all((left[i-1] < tzl[j]) == (right[j-1] < tzr[i])
                       for i in range(1, 5) for j in range(1, 5)):
                    z = [None] * 8
                    for t, i in zip(left, pr):
                        z[t] = f"R{i}"
                    for t, i in zip(right, pl):
                        z[t] = f"L{i}"
                    out.append((tuple(x), tuple(z)))
    return tuple(out)


def valid_schedules(key=42):
    """212 schedules in the inferred monomial-independent grammar.

    STAR refers to a schedule grammar without giving its full rules.
    This fixes the X internal monomial subsequences and enumerates 70*24^2
    candidates, retaining pairwise symbolic cancellation.  It reproduces
    the paper's count; it is not an assertion that these are all clean
    translation-invariant schedules with arbitrary X orders.
    """
    torus(key)  # validate the instance
    return [{"X": x, "Z": z} for x, z in _valid_orders()]


def build(key, basis, rounds, p=0.001, noise="full", schedule=None):
    if basis not in ("X", "Z"):
        raise ValueError("basis must be X or Z")
    if noise not in ("full", "noidle"):
        raise ValueError("noise must be full or noidle")
    if int(rounds) != rounds or rounds < 1:
        raise ValueError("rounds must be a positive integer")
    if not schedule_is_valid(key, schedule):
        raise ValueError("schedule has residual ancilla back-action")
    xs, zs, T = supports(key, schedule)
    hx, hz, n = matrices(key)
    lx, lz = stabcode.css_logicals(hx, hz, n)
    data = list(range(n))
    za, xa = list(range(n, n + T.n)), list(range(n + T.n, 2 * n))
    gates = layers(key, schedule)
    all_qubits = set(range(2 * n))
    per = n
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)
    c.append("DEPOLARIZE1", data, p)
    c.append("TICK")
    for t in range(int(rounds)):
        c.append("R", za)
        c.append("DEPOLARIZE1", za, p)
        c.append("RX", xa)
        c.append("DEPOLARIZE1", xa, p)
        c.append("TICK")
        for targets in gates:
            c.append("CX", targets)
            c.append("DEPOLARIZE2", targets, p)
            idle = sorted(all_qubits - set(targets))
            if noise == "full" and idle:
                c.append("DEPOLARIZE1", idle, p)
            c.append("TICK")
        c.append("M", za, p)
        c.append("MX", xa, p)
        for i in range(T.n):
            for check_basis, offset, coord in (("Z", -per, 3), ("X", -T.n, 0)):
                rec = [stim.target_rec(offset + i)]
                if t:
                    rec.append(stim.target_rec(offset - per + i))
                if t or basis == check_basis:
                    c.append("DETECTOR", rec, (i, 0, t, coord))
        c.append("TICK")
    c.append("M" if basis == "Z" else "MX", data, p)
    checks, logs, prev = (hz, lz, -n - per) if basis == "Z" else (hx, lx, -n - T.n)
    for i, row in enumerate(checks):
        c.append("DETECTOR", [stim.target_rec(-n + q) for q in stabcode.bits(row)] +
                 [stim.target_rec(prev + i)], (i, 0, rounds, 3 if basis == "Z" else 0))
    for i, logical in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + q) for q in stabcode.bits(logical)], i)
    c.detector_error_model(decompose_errors=False)
    return c
