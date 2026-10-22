"""Vine codes (arXiv:2606.20263, Nixon, McLauchlan, van Rest): codes and memory circuits from the authors'
Stim files (Zenodo 10.5281/zenodo.20746752, CC-BY-4.0, read as data from papers/downloads/planar/zenodo_20746752/).

The code of a patch is read off its circuit: every measurement of the first syndrome round is propagated
back to the start of the round (stim.PauliString.before); its support on the data qubits (the qubits reset
in the memory basis at the start) is the measured stabiliser, and its support on the other qubits, which
start in |0>, must be Z-type or empty.  Data qubits are numbered in the order of their stim indices.

Files:
  Fig_5{a,b,c,d}_patch_circuit.stim      the d = 10 patches of Table 2 (noiseless, X memory, two rounds)
  1S2W4S3_{X,Z}_10E-3_noise_distance_{3,5,7}.stim
                                          Fig. 7 simulations (SI1000 noise, max(5, d) rounds); "1S2W4S3" is
                                          the step sequence nSeWwSs with n,e,s,w written 1,2,3,4
  1S2WW4S3_...                            the same for nSeWWwSs
  Fig_11_patch_circuit_{original,reduced_routing}.stim
                                          a d = 5 nSENESs patch before and after the SWAP reduction

Memory circuits (memory_circuit, below): the noisy X- or Z-memory experiment of a patch for any number of rounds,
rebuilt from its schedule as the authors' noisy files do it (validated on all 12 Fig. 7 files: same gates in every
layer, same detectors, same error mechanisms), with detector coordinates (check, 0, round, type) for the pipeline.

Usage: python papers/planar_vine.py                         (prints the parameters of every patch)
       python papers/planar_vine.py export_circuits <root>   (CIRCUITS as benchmark circuit instances under root)
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import planar_common  # noqa: E402

ZENODO = os.path.join(HERE, "downloads", "planar", "zenodo_20746752", "x", "Files_for_paper")
ARXIV = "2606.20263"

RESETS = ("R", "RX", "RY")
MEASURES = ("M", "MX", "MY")
ANNOTATIONS = ("QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS")


def moments(circuit):
    """Moments (lists of (name, targets, args)) of a flattened circuit; annotations are dropped."""
    out = [[]]
    for ins in circuit.flattened():
        if ins.name == "TICK":
            out.append([])
        elif ins.name not in ANNOTATIONS:
            out[-1].append((ins.name, [t.value for t in ins.targets_copy()], ins.gate_args_copy()))
    return out


def coordinates(circuit):
    out = {}
    for ins in circuit.flattened():
        if ins.name == "QUBIT_COORDS":
            for t in ins.targets_copy():
                out[t.value] = tuple(ins.gate_args_copy())
    return out


def first_round(circuit):
    """(data qubits, basis of their reset, unitary circuit of round 1, qubits measured at its end)."""
    import stim
    ms = moments(circuit.without_noise())
    data, basis = [], None
    for name, t, _ in ms[0]:
        if name in ("RX", "RY"):
            data, basis = sorted(t), name
    assert data, "expected the data qubits to be reset in the X basis at the start (an X-memory circuit)"
    unitary = stim.Circuit()
    for i in range(1, len(ms)):
        names = {name for name, _, _ in ms[i]}
        if names & set(MEASURES):
            measured = [q for name, t, _ in ms[i] if name in MEASURES for q in t]
            return data, basis, unitary, measured
        assert not names & set(RESETS), "reset inside the first round"
        for name, t, args in ms[i]:
            unitary.append(name, t, args)
        unitary.append("TICK")
    raise ValueError("no measurement layer found")


def extract_code(path):
    """Stabilisers measured in the first round of an X-memory circuit, as (data, hx, hz, xy, flags)."""
    import stim
    circuit = stim.Circuit.from_file(path)
    data, _, unitary, measured = first_round(circuit)
    index = {q: i for i, q in enumerate(data)}
    nq = circuit.num_qubits
    hx, hz, flags = [], [], 0
    for q in measured:
        p = stim.PauliString(nq)
        p[q] = "Z"
        b = p.before(unitary)
        xs, zs = 0, 0
        for j in range(nq):
            v = b[j]                     # 0 = I, 1 = X, 2 = Y, 3 = Z
            if v == 0:
                continue
            if j in index:
                if v in (1, 2):
                    xs |= 1 << index[j]
                if v in (2, 3):
                    zs |= 1 << index[j]
            else:
                assert v == 3, "measurement %d is random: support %s on a qubit that starts in |0>" % (q, "XYZ"[v - 1])
        if xs and zs:
            raise AssertionError("measurement of qubit %d is not CSS" % q)
        if xs:
            hx.append(xs)
        elif zs:
            hz.append(zs)
        else:
            flags += 1                   # a routing (flag) qubit: deterministic, no data support
    coords = coordinates(circuit)
    xy = [tuple(float(c) for c in coords[q][:2]) for q in data]
    return data, hx, hz, xy, flags


# ----------------------------------------------------------------------------------------------- memory circuits
#
# The authors' noisy circuits (the Fig. 7 files) have, per round: reset of the measure and routing qubits, the
# step sequence (forwards in odd rounds, reversed in even ones) with every SWAP to a routing qubit done as a
# CZSWAP, measurement of the measure qubits and of the routing qubits, and one flag detector per routing
# measurement.  The Fig. 5 files give the same schedule for two rounds without noise, with plain SWAPs, and with
# routing qubits that are never reset or measured.  memory_circuit() rebuilds the noisy experiment from either.
#
# Noise (SI1000, Appendix G of the paper): DEPOLARIZE2(p) after every two-qubit gate, DEPOLARIZE1(p/10) after
# every H, X_ERROR(2p) after R and Z_ERROR(2p) after RX, measurement flips 5p, and idle noise DEPOLARIZE1(p/10)
# in gate layers and DEPOLARIZE1(2p) in measurement and reset layers on EVERY qubit not acted on.  The authors'
# files put idle noise on only part of the idle data and measure qubits (always on the routing qubits), so this
# fault set contains theirs: a circuit distance computed here is a lower bound on the one of their circuits.

SWAPPING = ("SWAP", "CXSWAP", "CZSWAP", "SWAPCX", "ISWAP")
TWO_QUBIT = ("CX", "CY", "CZ", "CXSWAP", "CZSWAP", "SWAPCX", "SWAP", "ISWAP")
ONE_QUBIT = ("H", "S", "S_DAG", "SQRT_X", "SQRT_X_DAG", "X", "Y", "Z", "I")


def _swap_states(where, moment):
    """where[state] = position; apply the position exchanges of one moment."""
    at = {q: s for s, q in where.items()}
    for op in moment:
        name, t = op[0], op[1]
        if name in SWAPPING:
            for a, b in zip(t[::2], t[1::2]):
                sa, sb = at[a], at[b]
                at[a], at[b] = sb, sa
    return {s: q for q, s in at.items()}


def _body(ms):
    return [[(name, t) for name, t, _ in m] for m in ms]


def _permutation(bodies, nq):
    where = {q: q for q in range(nq)}
    for body in bodies:
        for m in body:
            where = _swap_states(where, m)
    return where


def _drop_extra_swaps(forward, reverse, nq):
    """The authors' last round can carry extra SWAPs between a data and a routing qubit that later rounds would
    undo (seen in their multi-round files: periodic rounds, extra swaps in the last round only).  Remove from the
    reversed round the fewest SWAP/CZSWAP gates that make forward + reverse the identity permutation."""
    import itertools
    if all(v == k for k, v in _permutation([forward, reverse], nq).items()):
        return reverse, []
    cands = [(i, j, k) for i, m in enumerate(reverse) for j, (name, t) in enumerate(m) if name in ("SWAP", "CZSWAP")
             for k in range(0, len(t), 2)]

    def without(drop):
        out = []
        for i, m in enumerate(reverse):
            mm = []
            for j, (name, t) in enumerate(m):
                keep = [x for k in range(0, len(t), 2) if (i, j, k) not in drop for x in t[k:k + 2]]
                if keep:
                    mm.append((name, keep))
            out.append(mm)
        return out
    # only gates that touch a state which does not return are candidates
    pi = _permutation([forward, reverse], nq)
    bad = {s for s, q in pi.items() if q != s}
    at = {q: q for q in range(nq)}
    at = _permutation([forward], nq)
    inv = {q: s for s, q in at.items()}
    useful = []
    for i, m in enumerate(reverse):
        for j, (name, t) in enumerate(m):
            for k in range(0, len(t), 2):
                if name in ("SWAP", "CZSWAP") and (inv[t[k]] in bad or inv[t[k + 1]] in bad):
                    useful.append((i, j, k))
        inv = {q: s for s, q in _swap_states({s: q for q, s in inv.items()}, m).items()}
    for size in (1, 2, 3):
        for drop in itertools.combinations(useful, size):
            rev = without(set(drop))
            if all(v == k for k, v in _permutation([forward, rev], nq).items()):
                return rev, [(i, reverse[i][j][0], reverse[i][j][1][k:k + 2]) for (i, j, k) in drop]
    raise AssertionError("no small set of SWAPs makes the schedule periodic")


def schedule(path):
    """Schedule of an X-memory patch circuit (noisy or not): the periodic forward and reversed rounds, the file's
    last round where it differs from them, the roles of the qubits, the stabiliser of every measure qubit (by its
    position at the start of a round) and the authors' X logicals."""
    import stim
    circuit = stim.Circuit.from_file(path)
    ms = moments(circuit.without_noise())
    nq = circuit.num_qubits
    data = sorted(q for name, t, _ in ms[0] if name == "RX" for q in t)
    meas_moments = [i for i, m in enumerate(ms) if any(name == "M" for name, _, _ in m)]
    bodies = []
    for r, i in enumerate(meas_moments):
        if r:
            assert all(name == "R" for name, _, _ in ms[meas_moments[r - 1] + 1]), "expected a reset layer"
        bodies.append(_body(ms[1 if r == 0 else meas_moments[r - 1] + 2:i]))
    nrounds = len(bodies)
    for b in bodies:
        for m in b:
            for name, t in m:
                assert name in ONE_QUBIT or name in TWO_QUBIT, "unexpected operation %s in a round" % name
    forward = bodies[0]
    if nrounds >= 3:
        reverse, dropped = bodies[1], []
    else:
        reverse, dropped = _drop_extra_swaps(bodies[0], bodies[1], nq)
    for r in range(nrounds - 1):
        assert bodies[r] == (forward if r % 2 == 0 else reverse), "round %d is not periodic" % r
    assert all(v == k for k, v in _permutation([forward, reverse], nq).items()), "schedule is not periodic"
    last = {}
    if bodies[-1] != (forward if (nrounds - 1) % 2 == 0 else reverse):
        last["forward" if (nrounds - 1) % 2 == 0 else "reverse"] = bodies[-1]
    after_f = _permutation([forward], nq)
    # roles: measured at the end of round 1 with data support = measure qubit, else routing
    _, hx_rows, hz_rows, measured_types = _round_stabilisers(circuit, data, forward, ms[meas_moments[0]])
    at_f = {q: s for s, q in after_f.items()}
    measure, stab = [], {}
    for q, (typ, sup) in measured_types.items():
        s = at_f[q]
        if typ is not None:
            measure.append(s)
            stab[s] = (typ, sup)
    measure.sort()
    routing = sorted(set(range(nq)) - set(data) - set(measure))
    reset1 = {q for name, t, _ in ms[meas_moments[0] + 1] for q in t}
    assert {after_f[s] for s in measure} <= reset1
    # the authors' observables, read off the final MX records (positions after the file's actual rounds)
    xlog = []
    recs = []
    for ins in circuit.without_noise().flattened():
        if ins.name in MEASURES:
            recs.extend(t.value for t in ins.targets_copy())
        elif ins.name == "OBSERVABLE_INCLUDE":
            idx = int(ins.gate_args_copy()[0])
            while len(xlog) <= idx:
                xlog.append(0)
            for t in ins.targets_copy():
                xlog[idx] ^= 1 << recs[len(recs) + t.value]         # t.value is negative: rec[-k]
    final = _permutation(bodies, nq)
    at_final = {q: s for s, q in final.items()}
    assert all(at_final[q] in set(data) for v in xlog for q in stabcode_bits(v))
    xlog = [sum(1 << at_final[q] for q in stabcode_bits(v)) for v in xlog]
    return dict(path=path, nq=nq, coords=coordinates(circuit), data=data, measure=measure, routing=routing,
                forward=forward, reverse=reverse, last=last, dropped=dropped, stab=stab, xlogicals=xlog,
                rounds_in_file=nrounds)


def stabcode_bits(x):
    out = []
    while x:
        low = x & -x
        out.append(low.bit_length() - 1)
        x ^= low
    return out


def _round_stabilisers(circuit, data, forward, meas_moment):
    """Operator measured by every qubit measured at the end of round 1: {position: (type or None, data support)}
    with the data support as a set of data positions at the start (None for flags)."""
    import stim
    nq = circuit.num_qubits
    unitary = stim.Circuit()
    for m in forward:
        for name, t in m:
            unitary.append(name, t)
        unitary.append("TICK")
    dset = set(data)
    out, hx, hz = {}, [], []
    for name, t, _ in meas_moment:
        if name != "M":
            continue
        for q in t:
            p = stim.PauliString(nq)
            p[q] = "Z"
            b = p.before(unitary)
            xs, zs = set(), set()
            for j in range(nq):
                v = b[j]
                if v == 0:
                    continue
                if j in dset:
                    if v in (1, 2):
                        xs.add(j)
                    if v in (2, 3):
                        zs.add(j)
                else:
                    assert v == 3, "random measurement"
            assert not (xs and zs)
            if xs:
                out[q] = ("X", frozenset(xs))
                hx.append(xs)
            elif zs:
                out[q] = ("Z", frozenset(zs))
                hz.append(zs)
            else:
                out[q] = (None, None)
    return None, hx, hz, out


def memory_circuit(sched, basis, rounds, p=1e-3):
    """Noisy memory experiment in `basis` ("X" or "Z") with `rounds` rounds from a schedule.  Detector
    coordinates (check, 0, round, type): check = index of the stabiliser among those of the memory basis, then
    the routing qubits (flags, check = number of stabilisers + routing index); type 0 (X memory) or 3 (Z memory)
    for stabiliser detectors and 1 or 4 for flags, so all detectors are in the memory sector."""
    import stim
    assert basis in ("X", "Z") and rounds >= 1
    nq = sched["nq"]
    data, measure, routing = sched["data"], sched["measure"], sched["routing"]
    stab = sched["stab"]
    mine = sorted(s for s in measure if stab[s][0] == basis)
    check_of = {s: i for i, s in enumerate(mine)}
    flag_of = {s: len(mine) + i for i, s in enumerate(routing)}
    t_stab, t_flag = (0, 1) if basis == "X" else (3, 4)
    c = stim.Circuit()
    for q in range(nq):
        c.append("QUBIT_COORDS", [q], list(sched["coords"].get(q, ())))
    pos = {s: s for s in range(nq)}
    nmeas = 0
    rec = {}

    def target(k):
        return stim.target_rec(k - nmeas)

    def idle_noise(touched, prob):
        idle = [q for q in range(nq) if q not in touched]
        if idle:
            c.append("DEPOLARIZE1", idle, prob)

    # start: data in the memory basis, every other qubit in |0>
    c.append("RX" if basis == "X" else "R", data)
    c.append("Z_ERROR" if basis == "X" else "X_ERROR", data, 2 * p)
    others = sorted(measure + routing)
    c.append("R", others)
    c.append("X_ERROR", others, 2 * p)
    c.append("TICK")
    for r in range(rounds):
        kind = "forward" if r % 2 == 0 else "reverse"
        body = sched["last"].get(kind, sched[kind]) if r == rounds - 1 else sched[kind]
        for m in body:
            touched = set()
            for name, t in m:
                name = "CZSWAP" if name == "SWAP" else name
                c.append(name, t)
                touched |= set(t)
                if name in TWO_QUBIT:
                    c.append("DEPOLARIZE2", t, p)
                else:
                    c.append("DEPOLARIZE1", t, p / 10)
            idle_noise(touched, p / 10)
            c.append("TICK")
            pos = _swap_states(pos, m)
        # measurement layer: measure qubits, then routing qubits (flags)
        mq = [pos[s] for s in measure]
        rq = [pos[s] for s in routing]
        c.append("M", mq + rq, 5 * p)
        for i, s in enumerate(measure + routing):
            rec[(s, r)] = nmeas + i
        nmeas += len(mq) + len(rq)
        idle_noise(set(mq + rq), 2 * p)
        for s in mine:
            targets = [target(rec[(s, r)])] + ([target(rec[(s, r - 1)])] if r else [])
            c.append("DETECTOR", targets, [check_of[s], 0, r, t_stab])
        for s in routing:
            c.append("DETECTOR", [target(rec[(s, r)])], [flag_of[s], 0, r, t_flag])
        c.append("TICK")
        if r < rounds - 1:
            c.append("R", mq + rq)
            c.append("X_ERROR", mq + rq, 2 * p)
            idle_noise(set(mq + rq), 2 * p)
            c.append("TICK")
    # final readout of the data, at their positions after the last round (records keyed by the data label)
    c.append("MX" if basis == "X" else "M", [pos[s] for s in data], 5 * p)
    drec = {s: nmeas + i for i, s in enumerate(data)}
    nmeas += len(data)
    for s in mine:
        targets = [target(rec[(s, rounds - 1)])] + [target(drec[q]) for q in sorted(stab[s][1])]
        c.append("DETECTOR", targets, [check_of[s], 0, rounds, t_stab])
    if basis == "X":
        logicals = sched["xlogicals"]
    else:
        logicals = z_logicals(sched)
    for i, v in enumerate(logicals):
        c.append("OBSERVABLE_INCLUDE", [target(drec[q]) for q in stabcode_bits(v)], i)
    return c


def z_logicals(sched):
    """Z logical operators (as bitmasks over qubit positions) of the code read off the schedule."""
    import stabcode
    data = sched["data"]
    idx = {q: i for i, q in enumerate(data)}
    hx = [sum(1 << idx[q] for q in sup) for typ, sup in sched["stab"].values() if typ == "X"]
    hz = [sum(1 << idx[q] for q in sup) for typ, sup in sched["stab"].values() if typ == "Z"]
    _, lz = stabcode.css_logicals(hx, hz, len(data))
    return [sum(1 << data[i] for i in stabcode.bits(v)) for v in lz]


PATCHES = [
    # name, file, sequence, cut, v1, v2, paper [[n,k]], (dx, dz), d_circ, d_kind, locator
    ("vine_437_6_10", "Fig_5a_patch_circuit.stim", "nSeWwSs", "rotated", (-14, 14), (29, 29), (437, 6), (10, 10),
     10, "conjectured", "Table II and Fig. 5(a)"),
    ("vine_538_6_10", "Fig_5b_patch_circuit.stim", "nSeWwSs", "square", (0, 38), (28, 0), (538, 6), (10, 10),
     10, "conjectured", "Table II and Fig. 5(b)"),
    ("vine_557_6_10", "Fig_5c_patch_circuit.stim", "nSeWwSs", "horizontal parallelogram", (38, 38), (28, 0),
     (557, 6), (10, 10), 10, "conjectured", "Table II and Fig. 5(c)"),
    ("vine_435_6_10", "Fig_5d_patch_circuit.stim", "nSeWwSs", "vertical parallelogram", (0, 28), (28, 28),
     (435, 6), (10, 10), 10, "conjectured", "Table II and Fig. 5(d)"),
    ("vine_fig7_nSeWwSs_s5", "1S2W4S3_X_10E-3_noise_distance_3.stim", "nSeWwSs", "rotated", (-5, 5), (10, 10),
     (None, 6), (None, None), (3, 4), "reported", "Fig. 7(a)-(b): circuit distances (d_X, d_Z) = (3, 4)"),
    ("vine_fig7_nSeWwSs_s7", "1S2W4S3_X_10E-3_noise_distance_5.stim", "nSeWwSs", "rotated", (-7, 7), (14, 14),
     (None, 6), (None, None), (5, 5), "reported", "Fig. 7(a)-(b): (5, 5)"),
    ("vine_fig7_nSeWwSs_s11", "1S2W4S3_X_10E-3_noise_distance_7.stim", "nSeWwSs", "rotated", (-11, 11), (22, 22),
     (None, 6), (None, None), (7, 8), "reported", "Fig. 7(a)-(b): (7, 8)"),
    ("vine_fig7_nSeWWwSs_s10", "1S2WW4S3_X_10E-3_noise_distance_3.stim", "nSeWWwSs", "horizontal parallelogram",
     (10, 10), (12, 0), (None, 9), (None, None), 3, "reported", "Fig. 7(c)-(d): minimum circuit distance 3"),
    ("vine_fig7_nSeWWwSs_s18", "1S2WW4S3_X_10E-3_noise_distance_5.stim", "nSeWWwSs", "horizontal parallelogram",
     (18, 18), (20, 0), (None, 9), (None, None), 5, "reported", "Fig. 7(c)-(d): minimum circuit distance 5"),
    ("vine_fig7_nSeWWwSs_s26", "1S2WW4S3_X_10E-3_noise_distance_7.stim", "nSeWWwSs", "horizontal parallelogram",
     (26, 26), (28, 0), (None, 9), (None, None), 7, "reported", "Fig. 7(c)-(d): minimum circuit distance 7"),
    ("vine_fig11_nSENESs_d5", "Fig_11_patch_circuit_original.stim", "nSENESs", "unknown", None, None, (None, 4),
     (None, None), 5, "reported", "Fig. 11 (d = 5 patch; caption)"),
]


def instances():
    out = []
    for (name, fname, seq, cut, v1, v2, nk, dxz, dcirc, kind, loc) in PATCHES:
        path = os.path.join(ZENODO, fname)
        data, hx, hz, xy, flags = extract_code(path)
        dx, dz = dxz
        inst = dict(name=name, family="vine codes", arxiv=ARXIV, locator=loc, n_paper=nk[0], k_paper=nk[1],
                    dx=dx, dz=dz, d=None if dx is None else min(dx, dz),
                    d_kind=kind if dx is not None else "unknown",
                    d_method=("Table II: d_x = d_z = d_circuit conjectured from smaller patches, not verified"
                              if kind == "conjectured" else "circuit distance reported in the figure; code distance "
                              "not given"),
                    d_circ=dcirc, d_circ_kind=kind, hx=hx, hz=hz, xy=xy, sequence=seq, cut=cut, v1=v1, v2=v2,
                    circuit_file=fname, data_qubits=data, flag_measurements=flags,
                    notes="code read off the first round of the authors' circuit %s" % fname)
        out.append(planar_common.check(inst))
    return out


if __name__ == "__main__" and len(sys.argv) == 1:
    print(planar_common.summary(instances()))


# ------------------------------------------------------------------------------------- export as circuit instances
CIRCUITS = {
    # name: (file, rounds, {memory basis: reported circuit distance}, status)
    "vine_437_6_10": ("Fig_5a_patch_circuit.stim", 10, {"X": 10, "Z": 10}, "conjectured"),
    "vine_538_6_10": ("Fig_5b_patch_circuit.stim", 10, {"X": 10, "Z": 10}, "conjectured"),
    "vine_557_6_10": ("Fig_5c_patch_circuit.stim", 10, {"X": 10, "Z": 10}, "conjectured"),
    "vine_435_6_10": ("Fig_5d_patch_circuit.stim", 10, {"X": 10, "Z": 10}, "conjectured"),
    # Fig. 7: X memory is limited by d_Z, Z memory by d_X; (d_X, d_Z) = (3, 4), (5, 5), (7, 8)
    "vine_fig7_nSeWwSs_s5": ("1S2W4S3_X_10E-3_noise_distance_3.stim", 5, {"X": 4, "Z": 3}, "reported"),
    "vine_fig7_nSeWwSs_s7": ("1S2W4S3_X_10E-3_noise_distance_5.stim", 5, {"X": 5, "Z": 5}, "reported"),
    "vine_fig7_nSeWwSs_s11": ("1S2W4S3_X_10E-3_noise_distance_7.stim", 7, {"X": 8, "Z": 7}, "reported"),
}


def check_positions(sched, basis):
    """Lattice position of every check id of memory_circuit (stabilisers of the memory basis, then routing qubits),
    at the start of a round."""
    mine = sorted(s for s in sched["measure"] if sched["stab"][s][0] == basis)
    return [list(sched["coords"][q][:2]) for q in mine + sched["routing"]]


def export_circuits(root, names=None, rounds=None):
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bench"))
    import common
    out = []
    for name, (fname, r0, dcirc, status) in CIRCUITS.items():
        if names and name not in names:
            continue
        sched = schedule(os.path.join(ZENODO, fname))
        r = rounds or r0
        for basis in ("X", "Z"):
            circ = memory_circuit(sched, basis, r)
            iname = "%s_mem%s_r%d" % (name, basis, r)
            truth = {}
            meta = dict(family="vine codes", description="%s, %s-memory circuit, %d rounds, SI1000 noise on every "
                        "idle qubit, CZSWAP routing with flags (rebuilt from %s)" % (name, basis, r, fname),
                        n=len(sched["data"]), k=None, basis=basis, rounds=r,
                        source="papers/planar_vine.py memory_circuit from Zenodo 10.5281/zenodo.20746752 " + fname,
                        paper={"arxiv": ARXIV, "d_circuit": dcirc[basis], "status": status}, truth=truth)
            meta["check_xy"] = check_positions(sched, basis)
            common.export_circuit_instance(iname, circ, None, meta, root=root)
            out.append(iname)
            print("exported", iname, "qubits", circ.num_qubits, "detectors", circ.num_detectors, flush=True)
    return out


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "export_circuits":
    export_circuits(sys.argv[2], sys.argv[3:] or None)
