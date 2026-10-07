"""Routing codes, arXiv:2606.25330v2, Tables 3/4 and Sec. III.

Physical site (x,y) has index x*m+y on Z_l x Z_m. Initially data sites
have x+y even, X ancillas have x odd/y even, and Z ancillas x even/y odd.
Rows and data columns are ordered by increasing initial physical site.
Routing acts on CURRENT role-labelled positions; each primitive is CNOT
followed by SWAP, with X ancilla as control or Z ancilla as target.

One cycle has T parallel CXSWAP layers. Odd-numbered cycles undo the
previous routing with reversed, negated vectors (Sec. III), while repeating
the parity measurements. Detectors follow ancilla labels, and final data
measurements follow the moved data labels, including at odd round counts.

Fault support: all 15 Paulis after each CXSWAP, prep/readout flips and idle
X/Y/Z (Appendices C.2/D.1). Single-qubit gate noise is omitted. Prep and
readout are each one parallel tick, with data idle during each; the paper
does not specify their timing. No qubit idles in a two-qubit layer. The
paper explicitly identifies the noise-free one-qubit iSWAP compilation with
this CXSWAP model (D.1); its circuit-distance claims are sampled upper bounds.
The round count and noisy final memory readout follow the task's convention;
Appendix C.2 does not specify these boundaries for its distance estimates.
"""
from functools import lru_cache
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stabcode


def _entry(l, m, vectors, params, bound, note="Table 3"):
    v = tuple(vectors)
    return ((l, m, v, v[::-1]),
            f"{note}; circuit distance is a randomized BP-OSD upper bound, "
            "not an exact value; CXSWAP compilation, noiseless one-qubit gates.",
            params, bound)


# Table 3 gives the defining vectors; w is reverse(v), not necessarily v.
# Key 80 retains Table 1's reported [[80,8,7]]; Table 3 calls it [[80,8,8]].
CODES = {
    54: _entry(18, 6, [(0, 1), (1, 0), (3, 0), (0, 1), (3, 0), (1, 0), (0, 1)], (54, 8, 6), 6),
    70: _entry(14, 10, [(1, 0), (2, 1), (0, 1), (0, 1), (0, 1), (2, 1), (1, 0)], (70, 8, 7), 7),
    80: _entry(16, 10, [(1, 0), (0, 1), (0, 1), (0, 1), (4, 1), (4, 1), (1, 0)], (80, 8, 7), 8,
               "Table 3; Table 1 reports d=7 but Tables 2/3 report d=8"),
    90: _entry(18, 10, [(1, 0), (0, 1), (0, 1), (0, 1), (2, 1), (2, 1), (1, 0)], (90, 8, 9), 9,
               "Table 3; defining nonlocal vector (2,1), despite Table 1's (4,1)"),
    100: _entry(20, 10, [(1, 0), (0, 1), (0, 1), (2, 1), (2, 1), (2, 1), (1, 0)], (100, 8, 10), 9),
    110: _entry(22, 10, [(1, 0), (0, 1), (0, 1), (6, 1), (6, 1), (0, 1), (1, 0)], (110, 8, 11), 10),
    "140_12": _entry(28, 10, [(1, 0), (0, 1), (0, 1), (4, 1), (0, 1), (0, 1), (1, 0)], (140, 8, 12), 11),
    "140_13": _entry(28, 10, [(1, 0), (6, 1), (6, 1), (0, 1), (0, 1), (0, 1), (1, 0)], (140, 8, 13), 12),
    "200_24": _entry(20, 20, [(1, 0), (0, 1), (1, 0), (1, 0), (6, 1), (6, 1), (6, 1),
                             (1, 0), (1, 0), (0, 1), (1, 0)], (200, 24, 14), 14, "Table 4, weight 11"),
    "200_16": _entry(40, 10, [(1, 0), (0, 1), (1, 0), (1, 0), (6, 1), (6, 1), (6, 1),
                             (1, 0), (1, 0), (0, 1), (1, 0)], (200, 16, 17), 17, "Table 4, weight 11"),
}


def tag(key):
    n, k, d = CODES[key][2]
    # Table 3's label identifies the ambiguous length-80 instance.
    return f"{n}_{k}_{8 if key == 80 else d}"


@lru_cache(None)
def geometry(key):
    """Initial physical sites for data, X checks and Z checks, in row order."""
    l, m, _, _ = CODES[key][0]
    data = tuple(x * m + y for x in range(l) for y in range(m) if (x + y) % 2 == 0)
    xa = tuple(x * m + y for x in range(l) for y in range(m) if x % 2 == 1 and y % 2 == 0)
    za = tuple(x * m + y for x in range(l) for y in range(m) if x % 2 == 0 and y % 2 == 1)
    return data, xa, za


@lru_cache(None)
def routing(key):
    """Forward/backward layers as (control,target) pairs and label positions.

    Return (forward, backward, positions_after_forward, xs, zs). positions
    maps an initial physical-site label to its current physical site; xs/zs
    list data COLUMN indices in chronological contact order for each check.
    """
    l, m, v, w = CODES[key][0]
    data, xa, za = geometry(key)
    data_index = {q: i for i, q in enumerate(data)}
    pos = list(range(l * m))
    at = pos.copy()
    xs, zs = [[] for _ in xa], [[] for _ in za]

    def cycle(vectors_x, vectors_z, collect):
        layers = []
        for vx, vz in zip(vectors_x, vectors_z):
            pairs, swaps = [], []
            for ancillas, vector, supports, is_x in ((xa, vx, xs, True), (za, vz, zs, False)):
                dx, dy = vector
                for i, label in enumerate(ancillas):
                    a = pos[label]
                    x, y = divmod(a, m)
                    b = ((x + dx) % l) * m + (y + dy) % m
                    dlabel = at[b]
                    assert dlabel in data_index, "routing targets a syndrome role"
                    if collect:
                        supports[i].append(data_index[dlabel])
                    pairs.append((a, b) if is_x else (b, a))
                    swaps.append((a, b))
            touched = [q for pair in pairs for q in pair]
            assert len(touched) == l * m and len(set(touched)) == l * m, "routing layer conflicts"
            for a, b in swaps:
                at[a], at[b] = at[b], at[a]
                pos[at[a]], pos[at[b]] = a, b
            layers.append(tuple(pairs))
        return tuple(layers)

    forward = cycle(v, w, True)
    moved = tuple(pos)
    backward = cycle(tuple((-dx, -dy) for dx, dy in v[::-1]),
                     tuple((-dx, -dy) for dx, dy in w[::-1]), False)
    assert pos == list(range(l * m)), "backward routing did not restore labels"
    assert all(len(set(g)) == len(v) for g in xs + zs), "a check revisits a data label"
    return forward, backward, moved, tuple(map(tuple, xs)), tuple(map(tuple, zs))


def matrices(key):
    _, _, _, xs, zs = routing(key)
    return [sum(1 << q for q in g) for g in xs], [sum(1 << q for q in g) for g in zs], len(geometry(key)[0])


def translations(key):
    """All nonidentity even-even torus translations, identical on X/Z rows."""
    l, m, _, _ = CODES[key][0]
    a, b = l // 2, m // 2
    return [[((x + dx) % a) * b + (y + dy) % b for x in range(a) for y in range(b)]
            for dx in range(a) for dy in range(b) if dx or dy]


def build(key, basis, rounds, p=0.001):
    """CSS memory with all k observables and physical routing retained."""
    if basis not in ("Z", "X") or not isinstance(rounds, int) or rounds < 1:
        raise ValueError("basis must be Z or X and rounds a positive integer")
    hx, hz, n = matrices(key)
    lx, lz = stabcode.css_logicals(hx, hz, n)
    data, xa, za = geometry(key)
    forward, backward, moved, _, _ = routing(key)
    identity = tuple(range(2 * n))
    nx, nz, per = len(xa), len(za), len(xa) + len(za)
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)
    c.append("X_ERROR" if basis == "Z" else "Z_ERROR", data, p)

    for t in range(rounds):
        before = identity if t % 2 == 0 else moved
        after = moved if t % 2 == 0 else identity
        dp = [before[q] for q in data]
        xp, zp = [before[q] for q in xa], [before[q] for q in za]
        c.append("R", zp)
        c.append("X_ERROR", zp, p)
        c.append("RX", xp)
        c.append("Z_ERROR", xp, p)
        c.append("DEPOLARIZE1", dp, p)
        c.append("TICK")
        for pairs in forward if t % 2 == 0 else backward:
            targets = [q for pair in pairs for q in pair]
            c.append("CXSWAP", targets)
            c.append("DEPOLARIZE2", targets, p)
            c.append("TICK")
        xp, zp = [after[q] for q in xa], [after[q] for q in za]
        c.append("X_ERROR", zp, p)
        c.append("M", zp)
        c.append("Z_ERROR", xp, p)
        c.append("MX", xp)
        c.append("DEPOLARIZE1", [after[q] for q in data], p)
        for checks, offset, color, kind in ((za, -per, 3, "Z"), (xa, -nx, 0, "X")):
            for i in range(len(checks)):
                if t or basis == kind:
                    records = [stim.target_rec(offset + i)]
                    if t:
                        records.append(stim.target_rec(offset - per + i))
                    c.append("DETECTOR", records, (i, 0, t, color))
        c.append("TICK")

    # Measure in INITIAL DATA LABEL order, at their actual final positions.
    final = moved if rounds % 2 else identity
    c.append("X_ERROR" if basis == "Z" else "Z_ERROR", [final[q] for q in data], p)
    c.append("M" if basis == "Z" else "MX", [final[q] for q in data])
    checks, logs, offset, color = (hz, lz, -n - per, 3) if basis == "Z" else (hx, lx, -n - nx, 0)
    for i, row in enumerate(checks):
        records = [stim.target_rec(-n + d) for d in stabcode.bits(row)]
        c.append("DETECTOR", records + [stim.target_rec(offset + i)], (i, 0, rounds, color))
    for i, row in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + d) for d in stabcode.bits(row)], i)
    return c


if __name__ == "__main__":
    if len(sys.argv) == 1:
        for key in CODES:
            print(key, CODES[key][2], "rebuilt", stabcode.css_parameters(*matrices(key)))
    else:
        key = int(sys.argv[1]) if sys.argv[1].isdigit() else sys.argv[1]
        circuit = build(key, sys.argv[2], int(sys.argv[3]))
        circuit.detector_error_model(decompose_errors=False)
        os.makedirs(os.path.dirname(os.path.abspath(sys.argv[4])), exist_ok=True)
        circuit.to_file(sys.argv[4])
        print(sys.argv[4], "qubits", circuit.num_qubits, "detectors", circuit.num_detectors)
