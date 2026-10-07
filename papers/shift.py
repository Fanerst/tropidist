"""Shift circuits of arXiv:2601.09911v1 under readings chosen by the lead.

Nominal twisted lattices use cited arXiv:2503.03827 Table 2. The literal
shift-paper definitions remain as 120lit/170lit (k=0; no circuits). Static
keys s repeat Table II; dynamic keys d repeat literal Table III, implementing
x^-1 per pair; m inserts exactly one Table III pair into static cycles.
Base keys b/b2 repeat the ordinary, unreversed second Table III column.
b1 preserves literal unreversal of its first column for a negative audit:
duplicated A1/A2 gates cancel and its detectors are nondeterministic.
Optional numbering=(pa,pb) maps table labels to 1-based printed monomials;
the default printed numbering preserves every existing circuit.

The full CNOT fault set has depolarization after CX, depolarization of idle
qubits per layer, and flips after resets / before measurements, including
data endpoints. noidle drops idle depolarization. Rates do not define distance.
See papers/new/2601.09911.md for evidence, the lead's readings, and validation.

Cell i*m+j represents x^i*y^j, with y^m=1 and x^ell*y^alpha=1.
Physical blocks, each of size N=ell*m: R, L, X, Z. Hx=[A|B],
Hz=[bar(B)|bar(A)]. The first dynamic half puts data in X,Z and measures R,L;
the second returns data to R,L. Every printed CNOT entry is retained.
"""
from functools import lru_cache
import os
import sys

import stim

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stabcode


# (ell, m, alpha, A exponent pairs, B exponent pairs), Table I, p.3.
DEFINITIONS = {
    "72": (6, 6, 0, ((0, 0), (1, 0), (-1, -3)), ((0, 0), (0, 1), (3, -1))),
    "120": (6, 10, 4, ((0, 0), (1, 0), (-2, 1)), ((0, 0), (0, 1), (1, 2))),
    "144": (12, 6, 0, ((0, 0), (1, 0), (-1, -3)), ((0, 0), (0, 1), (3, -1))),
    "170": (5, 17, -7, ((0, 0), (1, 0), (0, -4)), ((0, 0), (0, 1), (4, 0))),
}
PARAMETERS = {"72": (72, 12, 6), "120": (120, 8, 12),
              "144": (144, 12, 12), "170": (170, 16, 10)}
LITERAL_DEFINITIONS = {
    "120lit": (10, 6, 4, DEFINITIONS["120"][3], DEFINITIONS["120"][4]),
    "170lit": (17, 5, -7, DEFINITIONS["170"][3], DEFINITIONS["170"][4]),
}
DEFINITIONS.update(LITERAL_DEFINITIONS)
READING = (
    "reading chosen by the lead: nominal twisted lattices from arXiv:2503.03827 Table 2 "
    "(120: (0,10),(6,4); 170: (0,17),(5,-7)); literal shifted-table lattices retained "
    "under lit keys; literal Table III implements x^-1, caption says x; "
    "noise full is the uniform CNOT location fault set, including endpoint flips and "
    "idle depolarization on unacted qubits in every layer; noidle drops idle channels. "
    "For layer/order-preserving CNOT=H CZ H compilation, its single-fault DEM support "
    "equals SI1000 support up to probabilities: any 1q Pauli next to CX is among the "
    "15 Paulis after CX; reset/measurement basis faults reduce to anticommuting flips. "
    "Entangling gates are not reordered. Table I numbers are BP-OSD upper bounds, not exact. "
)
CODES = {}
for _size in PARAMETERS:
    for _suffix in ("", "s", "d", "m"):
        _variant = {
            "": "reading chosen by the lead: static Table II every cycle; bare-key alias of s.",
            "s": "reading chosen by the lead: static Table II every cycle.",
            "d": "reading chosen by the lead: literal Table III pair repeated, even cycle count; one x^-1 shift per pair.",
            "m": "reading chosen by the lead: static Table II with exactly one literal Table III pair at cycles rounds/2-1, rounds/2 (zero-based); even cycle count.",
        }[_suffix]
        CODES[_size + _suffix] = (DEFINITIONS[_size], READING + _variant,
                                  PARAMETERS[_size], 6 if _size == "72" else 10)
    CODES[int(_size)] = CODES[_size]  # run_parallel coerces numeric keys
for _key, _definition in LITERAL_DEFINITIONS.items():
    CODES[_key] = (_definition, READING + "reading chosen by the lead: preserve literal Table I / Eq.(1); k=0; no circuit runs.",
                   (120 if _key == "120lit" else 170, 0, None), None)
for _size in PARAMETERS:
    for _suffix in ("b", "b1", "b2"):
        _description = (
            "static unreversed Table III second column; ancillas remain ancillas; "
            "b aliases b2; six CNOTs per check."
            if _suffix != "b1" else
            "literal static unreversal of all first-column gates, including duplicated "
            "Z A1 and X A2; diagnostic invalid syndrome circuit with nondeterministic detectors."
        )
        CODES[_size + _suffix] = (
            DEFINITIONS[_size], READING + "reading chosen by the lead: " + _description +
            " No separate circuit-distance estimate is stated for this diagnostic base variant.",
            PARAMETERS[_size], None)

BLOCK = {"R": 0, "L": 1, "X": 2, "Z": 3}


def tag(key):
    return str(key)


def base_key(key):
    key = str(key)
    if key not in CODES:
        raise KeyError(key)
    if key.endswith(("b1", "b2")):
        return key[:-2]
    return key[:-1] if key[-1:] in ("s", "d", "m", "b") else key


def variant_key(key):
    key = str(key)
    return key[len(base_key(key)):]


def normalize_numbering(numbering=None):
    """pa[i-1] is the printed monomial called Ai; similarly for B."""
    if numbering is None:
        return ((1, 2, 3), (1, 2, 3))
    try:
        pa, pb = numbering
        pa, pb = tuple(pa), tuple(pb)
        if (any(type(i) is not int for i in pa + pb) or
                sorted(pa) != [1, 2, 3] or sorted(pb) != [1, 2, 3]):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("numbering must be two permutations of (1,2,3)")
    return pa, pb


def numbered_terms(key, numbering=None):
    _, _, _, a, b = DEFINITIONS[base_key(key)]
    pa, pb = normalize_numbering(numbering)
    return tuple(a[i - 1] for i in pa), tuple(b[i - 1] for i in pb)


def pair_shift(key, numbering=None):
    """Literal Table III's intended completed-pair data shift A1/A2."""
    a, _ = numbered_terms(key, numbering)
    return a[0][0] - a[1][0], a[0][1] - a[1][1]


def monomial(dx, dy):
    parts = []
    for variable, exponent in (("x", dx), ("y", dy)):
        if exponent:
            parts.append(variable if exponent == 1 else variable + "^" + str(exponent))
    return "*".join(parts) or "1"


def shift_cell(key, cell, dx, dy):
    ell, m, alpha, _, _ = DEFINITIONS[base_key(key)]
    i, j = divmod(cell, m)
    winding, i = divmod(i + dx, ell)
    return i * m + (j + dy - winding * alpha) % m


def qubit(key, block, cell, dx=0, dy=0):
    ell, m, _, _, _ = DEFINITIONS[base_key(key)]
    return BLOCK[block] * ell * m + shift_cell(key, cell, dx, dy)


@lru_cache(None)
def _matrices(size):
    ell, m, _, a, b = DEFINITIONS[size]
    count = ell * m
    hx, hz = [], []
    for u in range(count):
        x = z = 0
        for dx, dy in a:
            x ^= 1 << qubit(size, "R", u, dx, dy)
            z ^= 1 << qubit(size, "L", u, -dx, -dy)
        for dx, dy in b:
            x ^= 1 << qubit(size, "L", u, dx, dy)
            z ^= 1 << qubit(size, "R", u, -dx, -dy)
        hx.append(x)
        hz.append(z)
    return tuple(hx), tuple(hz), 2 * count


def matrices(key):
    hx, hz, n = _matrices(base_key(key))
    return list(hx), list(hz), n


@lru_cache(None)
def _logicals(size):
    hx, hz, n = matrices(size)
    return stabcode.css_logicals(hx, hz, n)


def translations(key):
    """All nonidentity lattice translations; run_parallel checks survival."""
    ell, m, _, _, _ = DEFINITIONS[base_key(key)]
    return [[shift_cell(key, u, dx, dy) for u in range(ell * m)]
            for dx in range(ell) for dy in range(m) if (dx, dy) != (0, 0)]


# Each entry: (check type, polynomial, term number, reversed control/target).
# Table II steps 2--8.  Blank simultaneous slots are genuinely absent.
STATIC = (
    (("Z", "B", 3, False),),
    (("Z", "B", 2, False), ("X", "B", 1, False)),
    (("Z", "A", 3, False), ("X", "A", 1, False)),
    (("Z", "A", 1, False), ("X", "A", 3, False)),
    (("Z", "A", 2, False), ("X", "A", 2, False)),
    (("Z", "B", 1, False), ("X", "B", 3, False)),
    (("X", "B", 2, False),),
)
# Table III first column, steps 2--9; second column, steps 2--8.
DYNAMIC_ODD = (
    (("Z", "A", 2, False),),
    (("Z", "A", 3, False), ("X", "A", 1, False)),
    (("Z", "B", 3, False), ("X", "B", 3, False)),
    (("Z", "B", 1, False), ("X", "B", 2, False)),
    (("Z", "B", 2, False), ("X", "B", 1, False)),
    (("Z", "A", 1, True), ("X", "A", 3, False)),
    (("Z", "A", 1, False), ("X", "A", 2, True)),
    (("X", "A", 2, False),),
)
DYNAMIC_EVEN = (
    (("Z", "A", 2, True),),
    (("Z", "A", 3, False), ("X", "A", 1, True)),
    (("Z", "B", 3, False), ("X", "B", 3, False)),
    (("Z", "B", 1, False), ("X", "B", 2, False)),
    (("Z", "B", 2, False), ("X", "B", 1, False)),
    (("Z", "A", 1, False), ("X", "A", 3, False)),
    (("X", "A", 2, False),),
)
BASE_FIRST = tuple(tuple((check, poly, term, False) for check, poly, term, _ in layer)
                   for layer in DYNAMIC_ODD)
BASE_SECOND = tuple(tuple((check, poly, term, False) for check, poly, term, _ in layer)
                    for layer in DYNAMIC_EVEN)


def cycle_kinds(key, rounds):
    """s = Table II; b1/b2 = unreversed columns; first/second = Table III."""
    base_key(key)
    if rounds < 1:
        raise ValueError("rounds must be positive")
    variant = variant_key(key)
    if variant in ("d", "m") and rounds % 2:
        raise ValueError("dynamic and middle-pair keys require an even cycle count")
    kinds = ["s"] * rounds
    if variant == "d":
        kinds = ["first", "second"] * (rounds // 2)
    elif variant == "m":
        kinds[rounds // 2 - 1:rounds // 2 + 1] = ["first", "second"]
    elif variant in ("b", "b1", "b2"):
        kinds = ["b1" if variant == "b1" else "b2"] * rounds
    return kinds


@lru_cache(None)
def _layer_targets(size, kind, numbering=((1, 2, 3), (1, 2, 3))):
    ell, m, _, _, _ = DEFINITIONS[size]
    a, b = numbered_terms(size, numbering)
    schedule = {"s": STATIC, "first": DYNAMIC_ODD, "second": DYNAMIC_EVEN,
                "b1": BASE_FIRST, "b2": BASE_SECOND}[kind]
    out = []
    for layer_index, entries in enumerate(schedule):
        targets = []
        for check, poly, term, reverse in entries:
            dx, dy = (a if poly == "A" else b)[term - 1]
            # Table III Round 1 Step 3 prints R(barA1*u), unlike the
            # other X/A entries. A1=1 concealed this distinction before
            # renumbering. Honor the literal entry, also in audit b1.
            if kind in ("first", "b1") and layer_index == 1 and check == "X" and poly == "A" and term == 1:
                dx, dy = -dx, -dy
            for u in range(ell * m):
                if check == "X":
                    pair = [qubit(size, "X", u), qubit(size, "R" if poly == "A" else "L", u, dx, dy)]
                else:
                    pair = [qubit(size, "L" if poly == "A" else "R", u, -dx, -dy), qubit(size, "Z", u)]
                targets.extend(pair[::-1] if reverse else pair)
        assert len(targets) == len(set(targets)), "a CNOT layer touches a qubit twice"
        out.append(tuple(targets))
    return tuple(out)


def layers(key, cycle=0, rounds=None, numbering=None):
    """Literal CNOT pairs in fixed physical coordinates, without noise."""
    if rounds is None:
        if str(key).endswith("m"):
            raise ValueError("middle-pair layer lookup requires rounds")
        variant = variant_key(key)
        if variant in ("b", "b1", "b2"):
            kind = "b1" if variant == "b1" else "b2"
        else:
            kind = ("first" if cycle % 2 == 0 else "second") if variant == "d" else "s"
    else:
        kind = cycle_kinds(key, rounds)[cycle]
    return _layer_targets(base_key(key), kind, normalize_numbering(numbering))


def data_map(key, rounds, numbering=None):
    """Image of every initial data position at the completed experiment."""
    n = matrices(key)[2]
    count = n // 2
    pairs = cycle_kinds(key, rounds).count("second")
    dx, dy = pair_shift(key, numbering)
    return [qubit(key, "R", u, pairs * dx, pairs * dy) for u in range(count)] + [
        qubit(key, "L", u, pairs * dx, pairs * dy) for u in range(count)]


def _noise(circ, gate, targets, p):
    if p and targets:
        circ.append(gate, targets, p)


def _idle(circ, n, active, p, noise):
    if noise == "full":
        used = set(active)
        _noise(circ, "DEPOLARIZE1", [q for q in range(2 * n) if q not in used], p)


def append_cycles(circ, key, rounds, basis=None, p=0, noise="full", numbering=None):
    """Append table cycles. basis=None omits detectors for logical checks."""
    if noise not in ("full", "noidle"):
        raise ValueError("noise must be full or noidle")
    n = matrices(key)[2]
    count = n // 2
    numbering = normalize_numbering(numbering)
    a, _ = numbered_terms(key, numbering)
    dx, dy = pair_shift(key, numbering)
    for t, kind in enumerate(cycle_kinds(key, rounds)):
        second = kind == "second"
        zreset = [qubit(key, "L" if second else "Z", u) for u in range(count)]
        xreset = [qubit(key, "R" if second else "X", u) for u in range(count)]
        circ.append("R", zreset)
        _noise(circ, "X_ERROR", zreset, p)
        circ.append("RX", xreset)
        _noise(circ, "Z_ERROR", xreset, p)
        _idle(circ, n, zreset + xreset, p, noise)
        circ.append("TICK")
        for targets in _layer_targets(base_key(key), kind, numbering):
            circ.append("CX", targets)
            _noise(circ, "DEPOLARIZE2", targets, p)
            _idle(circ, n, targets, p, noise)
            circ.append("TICK")
        first = kind == "first"
        # Check u follows first-half swaps Z(u)<->L(barA1*u) and
        # X(u)<->R(A2*u); its label is independent of that physical site.
        zmeas = [qubit(key, "L" if first else "Z", u,
                       -a[0][0] if first else 0, -a[0][1] if first else 0)
                 for u in range(count)]
        xmeas = [qubit(key, "R" if first else "X", u,
                       a[1][0] if first else 0, a[1][1] if first else 0)
                 for u in range(count)]
        _noise(circ, "X_ERROR", zmeas, p)
        circ.append("M", zmeas)
        _noise(circ, "Z_ERROR", xmeas, p)
        circ.append("MX", xmeas)
        _idle(circ, n, zmeas + xmeas, p, noise)
        if basis is not None:
            for check, offset in (("Z", 0), ("X", count)):
                for u in range(count):
                    cur = stim.target_rec(-n + offset + u)
                    if t == 0:
                        if basis == check:
                            circ.append("DETECTOR", [cur], (u, 0, t, 3 if check == "Z" else 0))
                    else:
                        prev = shift_cell(key, u, -dx, -dy) if second else u
                        circ.append("DETECTOR", [cur, stim.target_rec(-2 * n + offset + prev)],
                                    (u, 0, t, 3 if check == "Z" else 0))
        circ.append("TICK")


def build(key, basis, rounds, p=0.001, noise="full", numbering=None):
    """Memory experiment using the schedules and fault set chosen by the lead."""
    size = base_key(key)
    numbering = normalize_numbering(numbering)
    if size.endswith("lit"):
        raise ValueError("literal twisted definitions have k=0 and are audit-only; no circuit runs")
    cycle_kinds(key, rounds)
    if basis not in ("X", "Z") or noise not in ("full", "noidle"):
        raise ValueError("basis must be X or Z and noise must be full or noidle")
    if not 0 <= p <= 1:
        raise ValueError("p must lie in [0,1]")
    hx, hz, n = matrices(key)
    count = n // 2
    lx, lz = _logicals(size)
    circ = stim.Circuit()
    data = list(range(n))
    circ.append("R" if basis == "Z" else "RX", data)
    _noise(circ, "X_ERROR" if basis == "Z" else "Z_ERROR", data, p)
    _idle(circ, n, data, p, noise)
    circ.append("TICK")
    append_cycles(circ, key, rounds, basis, p, noise, numbering)
    image = data_map(key, rounds, numbering)
    _noise(circ, "X_ERROR" if basis == "Z" else "Z_ERROR", image, p)
    circ.append("M" if basis == "Z" else "MX", image)
    _idle(circ, n, image, p, noise)
    checks, logs = (hz, lz) if basis == "Z" else (hx, lx)
    # Every supported final cycle ends with data on R,L. Their records are in
    # initial-data order; invert the data permutation for current check rows.
    inverse = {q: j for j, q in enumerate(image)}
    for u, row in enumerate(checks):
        recs = [stim.target_rec(-n + inverse[q]) for q in stabcode.bits(row)]
        recs.append(stim.target_rec(-2 * n + (0 if basis == "Z" else count) + u))
        circ.append("DETECTOR", recs, (u, 0, rounds, 3 if basis == "Z" else 0))
    for obs, row in enumerate(logs):
        circ.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + j) for j in stabcode.bits(row)], obs)
    return circ
