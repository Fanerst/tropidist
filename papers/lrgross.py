"""Gross-code left-right schedule, arXiv:2603.05481v2, Appendix H Fig. 12.

The printed times are phases of an eight-step PERIOD, not a sorted gate
order.  Each check starts at its preparation phase and ends at the following
measurement phase.  X/Z operations share layers on disjoint data blocks;
this is a staggered non-interleaved circuit, not seq_circuit's X-then-Z cycle.
The residual problem uses Theorem 1 of the paper.  No deposited files used.

Standard BB coordinates: site (i,j) = 6*i+j, i mod 12, j mod 6;
Hx=[A|B], Hz=[B^T|A^T], A=x^3+y+y^2, B=y^3+x+x^2.
Fig. 10 has X at (2i,2j) and Z at (2i+1,2j+1).  Its hollow
data at (2i+1,2j) maps to R(i+2,j), its filled data at (2i,2j+1)
to L(i,j+2).  The drawn Z check (i,j) maps to BB row (i+2,j+2).
Colours in BB coordinates: X i+j, Z i+j-4 (mod 3), R/G/B=0/1/2.

Finite memory boundary: prepare all data, then start each check at its first
printed reset phase, run exactly `rounds` complete checks of each type, and
measure all data perfectly after the last check finishes.  Boundary padding
does not change the eight-step bulk period.  Full noise is Section II.3:
CNOT depolarization, idle depolarization, reset and measurement flips.
"""
from __future__ import annotations

from functools import lru_cache
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import design
import stabcode

PERIOD = 8
DIRECTIONS = ("N", "E", "S", "W", "NE", "SW")
A = ((3, 0), (0, 1), (0, 2))
B = ((0, 3), (1, 0), (2, 0))
# Figure 12, in DIRECTIONS order, colour R/G/B.  Times are 1-based phases.
TIMES_X = ((2, 8, 1, 7, 3, 6), (2, 7, 1, 6, 3, 8), (2, 1, 4, 8, 3, 7))
TIMES_Z = ((4, 6, 2, 7, 5, 3), (4, 7, 2, 5, 6, 3), (4, 8, 5, 6, 7, 3))
RESET_X, MEASURE_X = (5, 5, 6), (4, 4, 5)
RESET_Z, MEASURE_Z = (1, 1, 2), (8, 8, 1)
CODES = {
    "lr11": (
        {"l": 12, "m": 6, "A": A, "B": B, "schedule": "Appendix H, Fig. 12"},
        "Nonuniform three-colour left-right schedule; circuit distance 11 is a conjecture (H.2).",
        (144, 12, 12),
        11,
    ),
}


def tag(key):
    CODES[key]
    return key


def colour(kind, ci):
    i, j = divmod(ci, 6)
    return (i + j - (4 if kind == "Z" else 0)) % 3


def _q(block, i, j):
    return 72 * block + (i % 12) * 6 + j % 6


def matrices(key):
    CODES[key]
    return stabcode.bb_matrices(12, 6, A, B)


def supports(key):
    """Each check's six labelled data qubits in the paper's drawing."""
    CODES[key]
    xs, zs = [], []
    for ci in range(72):
        i, j = divmod(ci, 6)
        xs.append(dict(zip(DIRECTIONS, (
            _q(0, i, j + 1), _q(1, i + 2, j), _q(0, i, j + 2),
            _q(1, i + 1, j), _q(0, i + 3, j), _q(1, i, j + 3),
        ))))
        zs.append(dict(zip(DIRECTIONS, (
            _q(1, i, j - 2), _q(0, i - 1, j), _q(1, i, j - 1),
            _q(0, i - 2, j), _q(0, i, j - 3), _q(1, i - 3, j),
        ))))
    return xs, zs


def gate_order(kind, ci):
    co = colour(kind, ci)
    times, resets = (TIMES_X, RESET_X) if kind == "X" else (TIMES_Z, RESET_Z)
    return sorted(DIRECTIONS, key=lambda d: (times[co][DIRECTIONS.index(d)] - resets[co]) % PERIOD)


def code_translations():
    """All 71 nonidentity BB translations (for checking code distance)."""
    return [[_q(0, i + di, j + dj) for i in range(12) for j in range(6)]
            for di in range(12) for dj in range(6) if (di, dj) != (0, 0)]


def translations(key):
    """The 23 nonidentity translations preserving both check colours."""
    CODES[key]
    return [[_q(0, i + di, j + dj) for i in range(12) for j in range(6)]
            for di in range(12) for dj in range(6)
            if (di, dj) != (0, 0) and (di + dj) % 3 == 0]


@lru_cache(maxsize=None)
def make_code(key):
    xs, zs = supports(key)
    return design.Code("lrgross" + tag(key), 144, xs, zs, translations(key), claimed=(144, 12, 12))


def effective(key, basis):
    """Paper's extended-code problem (Theorem 1), using cyclic gate orders.

    Although the Stim circuit is staggered rather than sequential, it is
    non-interleaved.  The DEM comparisons in verify_effective independently
    check whether this problem equals its time collapse and an interior window.
    """
    if basis not in ("X", "Z"):
        raise ValueError("basis must be X or Z")
    kind = "X" if basis == "Z" else "Z"
    return design.effective_problem(make_code(key), basis, lambda ci: gate_order(kind, ci))


def schedule(key, rounds):
    """Absolute layers: (resets X/Z, CNOT targets, measurements X/Z).

    Measurements are (check index, logical round, ancilla) triples.  Each
    check is unwrapped after its first preparation phase; no partial checks
    appear at either memory boundary.
    """
    if not isinstance(rounds, int) or rounds < 1:
        raise ValueError("rounds must be a positive integer")
    xs, zs = supports(key)
    events = {}

    def at(t):
        return events.setdefault(t, {"RX": [], "R": [], "CX": [], "MX": [], "M": []})

    for kind, checks, times, resets, measures, offset in (
        ("X", xs, TIMES_X, RESET_X, MEASURE_X, 144),
        ("Z", zs, TIMES_Z, RESET_Z, MEASURE_Z, 216),
    ):
        for ci, check in enumerate(checks):
            co, anc = colour(kind, ci), offset + ci
            reset, measure = resets[co], measures[co]
            for r in range(rounds):
                start = reset + PERIOD * r
                at(start)["RX" if kind == "X" else "R"].append(anc)
                for direction, phase in zip(DIRECTIONS, times[co]):
                    t = start + (phase - reset) % PERIOD
                    assert t > start
                    data = check[direction]
                    at(t)["CX"].extend((anc, data) if kind == "X" else (data, anc))
                end = start + (measure - reset) % PERIOD
                assert end - start == 7
                at(end)["MX" if kind == "X" else "M"].append((ci, r, anc))
    out = []
    for t in range(1, max(events) + 1):
        e = at(t)
        used = e["RX"] + e["R"] + e["CX"] + [q for _, _, q in e["MX"] + e["M"]]
        assert len(used) == len(set(used)), f"qubit collision at absolute time {t}"
        out.append(e)
    return out


def build(key, basis, rounds, p=0.001, noise="full"):
    if basis not in ("X", "Z"):
        raise ValueError("basis must be X or Z")
    if noise not in ("full", "noidle"):
        raise ValueError("noise must be full or noidle")
    code = make_code(key)
    data, all_qubits = list(range(144)), set(range(288))
    circ = stim.Circuit()
    # Appendix E starts with a product state.  Its final data measurement is
    # the perfect terminal check round, hence carries no measurement noise.
    circ.append("RX" if basis == "X" else "R", data)
    circ.append("Z_ERROR" if basis == "X" else "X_ERROR", data, p)
    circ.append("TICK")
    record, nmeas = {}, 0
    for layer in schedule(key, rounds):
        used = set(layer["RX"] + layer["R"] + layer["CX"])
        for reset, flip in (("RX", "Z_ERROR"), ("R", "X_ERROR")):
            if layer[reset]:
                circ.append(reset, layer[reset])
                circ.append(flip, layer[reset], p)
        if layer["CX"]:
            circ.append("CX", layer["CX"])
            circ.append("DEPOLARIZE2", layer["CX"], p)
        for measure, flip, kind in (("MX", "Z_ERROR", "X"), ("M", "X_ERROR", "Z")):
            triples = layer[measure]
            if triples:
                qubits = [anc for _, _, anc in triples]
                used.update(qubits)
                circ.append(flip, qubits, p)
                circ.append(measure, qubits)
                base = nmeas
                nmeas += len(qubits)
                for k, (ci, r, _) in enumerate(triples):
                    rec = base + k
                    targets = [stim.target_rec(rec - nmeas)]
                    if r:
                        targets.append(stim.target_rec(record[kind, ci, r - 1] - nmeas))
                    if r or kind == basis:
                        circ.append("DETECTOR", targets, (ci, 0, r, 0 if kind == "X" else 3))
                    record[kind, ci, r] = rec
        if noise == "full":
            idle = sorted(all_qubits - used)
            if idle:
                circ.append("DEPOLARIZE1", idle, p)
        circ.append("TICK")
    circ.append("MX" if basis == "X" else "M", data)
    nmeas += len(data)
    checks = code.hx if basis == "X" else code.hz
    for ci, row in enumerate(checks):
        targets = [stim.target_rec(-144 + q) for q in stabcode.bits(row)]
        targets.append(stim.target_rec(record[basis, ci, rounds - 1] - nmeas))
        circ.append("DETECTOR", targets, (ci, 0, rounds, 0 if basis == "X" else 3))
    for li, row in enumerate(code.lx if basis == "X" else code.lz):
        circ.append("OBSERVABLE_INCLUDE", [stim.target_rec(-144 + q) for q in stabcode.bits(row)], li)
    circ.detector_error_model(decompose_errors=False)
    return circ


def verify_effective(key, basis, rounds=3, noise="full"):
    """Check the actual staggered DEM, without assuming sequential timing."""
    from cdist import problem
    import tempfile
    circ = build(key, basis, rounds, noise=noise)
    with tempfile.NamedTemporaryFile(suffix=".stim") as f:
        circ.to_file(f.name)
        full = problem.load_dem_problem(f.name)
    sector = problem.sector_problem(full)
    eff = effective(key, basis)
    want = set(zip(eff.h, eff.l))

    def columns(p):
        out = set()
        for h, l in zip(p.h, p.l):
            mask = sum(1 << int(p.row_meta[j][0]) for j in stabcode.bits(h))
            out.add((mask, l))
        return out

    collapsed = problem.collapse_time(sector)
    return {
        "sector_reduction_exact": problem.sector_is_exact(full, sector),
        "effective_columns": eff.ncols,
        "collapsed_columns": collapsed.ncols,
        "effective_columns_equal_collapsed_columns": columns(collapsed) == want,
        "window_equal": {str(t): columns(problem.window_problem(sector, t, t)) == want
                         for t in range(rounds + 1)},
    }


if __name__ == "__main__":
    key, basis, rounds, path = sys.argv[1:5]
    build(key, basis, int(rounds)).to_file(path)
