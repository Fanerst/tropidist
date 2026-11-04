"""The memory circuits of Bravyi et al.'s public code (github.com/sbravyi/BivariateBicycleCodes, decoder_setup.py at
commit fa77e33), which arXiv:2511.15177 uses for its circuit-noise systems BB(6), BB(12) and BB(18):

  - the depth-8 cycle of arXiv:2308.07915 with its standard schedule (decoder_setup.py's sX, sZ, which are
    bb6_depth7.STANDARD): the X checks are prepared in round 0, the Z checks measured in round 6, and in round 7 the
    X checks are measured and the Z checks prepared, while the data qubits idle;
  - C noisy cycles followed by two noise-free cycles, from an error-free start (the Z checks start in |0>, since
    their first preparation is in round 7);
  - noise as in decoder_setup.py: the 15 two-qubit Paulis after every CNOT, X, Y or Z on every idle data qubit,
    a flip after every preparation and before every measurement;
  - detectors as its syndrome sparsification (each check's outcome against its previous one, the first against
    zero), observables read from a noise-free data measurement after the last cycle.

papers/bravyi_repo_check.py compares the detector error model with the decoding matrices that decoder_setup.py itself
computes.

Paper-module interface of papers/run_parallel.py: CODES, build(size, basis, rounds), translations, tag.

Usage: python papers/bravyi_repo_circuit.py KEY BASIS CYCLES OUT.json [kmax] [seconds per threshold]
"""
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bb6_depth7 as B
import stabcode

CODES = {k: B.CODES[k] for k in ("bb72", "bb90", "bb108", "gross", "bb288")}


def build_memory(key, basis, cycles, p=1e-3):
    xs, zs, N = B.supports(key, None)
    nq = 2 * N
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
    assert (hx, hz, nq) == tuple(B.matrices(key))
    lx, lz = stabcode.css_logicals(hx, hz, nq)
    data = list(range(nq))
    za = [nq + i for i in range(N)]
    xa = [nq + N + i for i in range(N)]
    xl = [[(xa[i], q) for i, g in enumerate(xs) for tt, q in g if tt == t] for t in range(7)]
    zl = [[(q, za[i]) for i, g in enumerate(zs) for tt, q in g if tt == t] for t in range(7)]
    assert not xl[0] and not zl[6]
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)
    c.append("R", za)
    c.append("TICK")

    def cnot(pairs, noisy):
        flat = [v for pair in pairs for v in pair]
        c.append("CX", flat)
        if noisy:
            c.append("DEPOLARIZE2", flat, p)

    def idle(qubits, noisy):
        if noisy and qubits:
            c.append("DEPOLARIZE1", qubits, p)

    def detectors(r, kind):
        for i in range(N):
            cur = stim.target_rec(-N + i)
            targets = [cur] if r == 0 else [cur, stim.target_rec(-3 * N + i)]
            c.append("DETECTOR", targets, (i, 0, r, 3 if kind == "Z" else 0))

    for cycle in range(cycles + 2):
        noisy = cycle < cycles
        r = cycle
        c.append("RX", xa)                                    # round 0
        if noisy:
            c.append("Z_ERROR", xa, p)
        cnot(zl[0], noisy)
        busy = {q for q, _ in zl[0]}
        idle([q for q in data if q not in busy], noisy)
        c.append("TICK")
        for t in range(1, 6):                                 # rounds 1-5: every data qubit is in a CNOT
            cnot(xl[t], noisy)
            cnot(zl[t], noisy)
            c.append("TICK")
        if noisy:                                             # round 6
            c.append("X_ERROR", za, p)
        c.append("M", za)
        if basis == "Z":
            detectors(r, "Z")
        cnot(xl[6], noisy)
        busy = {q for _, q in xl[6]}
        idle([q for q in data if q not in busy], noisy)
        c.append("TICK")
        idle(data, noisy)                                     # round 7
        if noisy:
            c.append("Z_ERROR", xa, p)
        c.append("MX", xa)
        if basis == "X":
            detectors(r, "X")
        c.append("R", za)
        if noisy:
            c.append("X_ERROR", za, p)
        c.append("TICK")
    c.append("M" if basis == "Z" else "MX", data)
    for a, v in enumerate(lz if basis == "Z" else lx):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-nq + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)          # raises if a detector is not deterministic
    return c


def build(size, basis, rounds, p=1e-3):
    return build_memory(size, basis, rounds, p)


translations = B.translations


def tag(size):
    return f"{size}_bravyi_repo"


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(HERE))
    import run_parallel
    key, basis, cycles, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    kmax = int(sys.argv[5]) if len(sys.argv) > 5 else 20
    tl = float(sys.argv[6]) if len(sys.argv) > 6 else 0
    run_parallel.main("bravyi_repo_circuit", key, basis, out, cycles, 3, kmax, tl, 1)
