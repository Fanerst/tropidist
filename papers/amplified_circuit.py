"""Memory circuits of "Ultra-high-distance quantum memories from amplified
qLDPC codes" (arXiv:2609.37231), from the authors' own circuit description
(github.com/zijian-liang/dp_certificates_github, simulation/source/circuits.py).

`build` reproduces their `build_memory(level, basis, rounds, p)` gate for gate
(asserted below) and only changes the detector coordinates to the convention
of cdist.problem: (detector id, 0, round, type), type 3 for detectors that see
the errors relevant to this memory basis and 0 for the others.  A detector id
names one check or one flag qubit, so the time-collapse groups each of them
over the rounds.

Fault model of the paper's simulations: preparation flips, measurement flips
and two-qubit depolarizing faults after every CNOT; no idle noise.
"""
import os
import sys

import stim

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amplified", "repo", "simulation", "source")
if not os.path.isfile(os.path.join(REPO, "circuits.py")):
    raise ImportError("papers/amplified_circuit.py needs the authors' repository (github.com/zijian-liang/"
                      "dp_certificates_github, commit 0772a00) in papers/amplified/repo/; see README.md")
sys.path.insert(0, REPO)
import circuits as theirs  # noqa: E402


def build(level, basis, rounds, p=0.001, check=True, idle=False):
    """idle=True adds a depolarizing fault on every data qubit that sits out a
    CNOT layer (a sensitivity check; not the paper's fault model)."""
    d = theirs.description(level)
    n = d["n"]
    c = stim.Circuit()
    count = 0
    ident = {}

    def det_id(key):
        if key not in ident:
            ident[key] = len(ident)
        return ident[key]

    def prep(qs, typ):
        if qs:
            c.append("RX" if typ == "X" else "R", qs)
            c.append("Z_ERROR" if typ == "X" else "X_ERROR", qs, p)

    def meas(qs, typ):
        nonlocal count
        if not qs:
            return []
        c.append("MX" if typ == "X" else "M", qs, p)
        out = list(range(count, count + len(qs)))
        count += len(qs)
        return out

    def detector(records, typ, key, r):
        c.append("DETECTOR", [stim.target_rec(i - count) for i in records],
                 (det_id(key), 0, r, 3 if typ == basis else 0))

    prep(list(range(n)), basis)
    c.append("TICK")
    previous = {}
    for r in range(rounds):
        prep(d["xs"] + d["zf"], "X")
        prep(d["zs"] + d["xf"], "Z")
        c.append("TICK")
        for kind, targets in d["events"]:
            if kind == "CX":
                flat = [q for pair in targets for q in pair]
                if flat:
                    c.append("CX", flat)
                    c.append("DEPOLARIZE2", flat, p)
                    if idle:
                        busy = set(flat)
                        c.append("DEPOLARIZE1", [q for q in range(n) if q not in busy], p)
            else:
                typ = kind[-1]
                for q, rec in zip(targets, meas(targets, typ)):
                    detector([rec], typ, ("flag", q), r)
            c.append("TICK")
        for typ, qs in (("X", d["xs"]), ("Z", d["zs"])):
            for j, rec in enumerate(meas(qs, typ)):
                key = (typ, j)
                if r:
                    detector([rec, previous[key]], typ, ("check", typ, j), r)
                elif typ == basis:
                    detector([rec], typ, ("check", typ, j), r)
                previous[key] = rec
        c.append("TICK")
    readout = meas(list(range(n)), basis)
    for j, support in enumerate(d["h" + basis.lower() + "_supports"]):
        detector([previous[(basis, j)]] + [readout[q] for q in support], basis, ("check", basis, j), rounds)
    for j, support in enumerate(d["l" + basis.lower() + "_supports"]):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(readout[q] - count) for q in support], j)
    if check and not idle:
        ref, _ = theirs.build_memory(level, basis, rounds, p)
        assert len(ref) == len(c)
        for a, b in zip(ref, c):
            assert a.name == b.name and a.targets_copy() == b.targets_copy(), (a, b)
            if a.name != "DETECTOR":
                assert a.gate_args_copy() == b.gate_args_copy()
    meta = {k: d[k] for k in ("level", "n", "k", "n_phys", "target_dc", "static_distance", "cnot_layers_per_round")}
    return c, meta


if __name__ == "__main__":
    level, basis, rounds, out = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
    circ, meta = build(level, basis, rounds, idle=len(sys.argv) > 5 and sys.argv[5] == "idle")
    circ.to_file(out)
    print(out, meta, "detectors", circ.num_detectors, "observables", circ.num_observables)
