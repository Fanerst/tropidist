"""IBM's bicycle architecture (Tour de gross, arXiv:2506.03094): the memory instructions of the gross code
[[144,12,12]] and of the two-gross code [[288,12,18]], in that paper's own setting (its Sec. 2.2 and 2.6).

  - the syndrome cycle of Bravyi et al. (arXiv:2308.07915, Table 5), or any other valid depth-seven schedule of
    papers/bb6_depth7.py: one check qubit per check, seven CNOT layers, then measurement and reset of the check
    qubits in one timestep, so that C cycles take 8C + 1 timesteps;
  - the instruction starts from an error-free code state and ends with a noise-free stabilizer round;
  - noise: every CNOT is followed by one of the 15 non-trivial two-qubit Paulis with probability p/15 each; every idle
    qubit in a timestep by X, Y or Z with probability p/3 each; preparations and measurements fail with probability p.

The paper's "Idle" instruction (Table 2) is one cycle (C = 1).  Its logical error rates were extrapolated with a
failure-spectrum ansatz that assumes circuit distances of 10 (gross) and 18 (two-gross).

Paper-module interface of papers/run_parallel.py: CODES, build(size, basis, rounds) with rounds = C, translations,
tag.  The schedule is chosen with the environment variable IBM_SCHEDULE ("standard", or slot tuples
"px0,...,px5/pz0,...,pz5" in the order L0 L1 L2 R0 R1 R2 of papers/bb6_depth7.py).

Usage: python papers/ibm_bicycle.py KEY BASIS CYCLES OUT.json [kmax] [seconds per threshold]
"""
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bb6_depth7 as B
import stabcode

CODES = {k: B.CODES[k] for k in ("gross", "bb288")}


def schedule_from_env():
    s = os.environ.get("IBM_SCHEDULE", "standard")
    if s == "standard":
        return None, "standard"
    px, pz = (tuple(int(x) for x in part.split(",")) for part in s.split("/"))
    return B.to_dicts(px, pz), "s" + "".join(map(str, px)) + "_" + "".join(map(str, pz))


def build_instruction(key, basis, cycles, p=1e-3, schedule=None):
    """C = cycles noisy syndrome cycles between an error-free code state and a noise-free final stabilizer round;
    detectors compare consecutive rounds, observables are read from a noise-free data measurement."""
    xs, zs, N = B.supports(key, schedule)
    nq = 2 * N
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
    assert (hx, hz, nq) == tuple(B.matrices(key))
    lx, lz = stabcode.css_logicals(hx, hz, nq)
    nx, nz = len(xs), len(zs)
    data = list(range(nq))
    za = [nq + i for i in range(nz)]
    xa = [nq + nz + i for i in range(nx)]
    everything = data + za + xa
    layers = []
    for t in range(7):
        tg = []
        for i, g in enumerate(xs):
            tg += [v for tt, q in g if tt == t for v in (xa[i], q)]
        for i, g in enumerate(zs):
            tg += [v for tt, q in g if tt == t for v in (q, za[i])]
        assert len(set(tg)) == len(tg)
        layers.append(tg)
    per = nz + nx
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)            # error-free code state: noise-free data preparation ...
    c.append("TICK")

    def syndrome_round(t, noisy, prep_noise):
        c.append("R", za)
        c.append("RX", xa)
        if prep_noise:                                        # preparation of the check qubits fails with p
            c.append("X_ERROR", za, p)
            c.append("Z_ERROR", xa, p)
        c.append("TICK")
        for tg in layers:
            c.append("CX", tg)
            if noisy:
                c.append("DEPOLARIZE2", tg, p)
                idle = sorted(set(everything) - set(tg))
                if idle:
                    c.append("DEPOLARIZE1", idle, p)
            c.append("TICK")
        if noisy:                                             # measurement fails with p; data idle in this timestep
            c.append("X_ERROR", za, p)
            c.append("Z_ERROR", xa, p)
        c.append("M", za)
        c.append("MX", xa)
        if noisy:
            c.append("DEPOLARIZE1", data, p)
        for i in range(nz):
            cur = stim.target_rec(-per + i)
            if t == 0:
                if basis == "Z":
                    c.append("DETECTOR", [cur], (i, 0, 0, 3))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-2 * per + i)], (i, 0, t, 3))
        for i in range(nx):
            cur = stim.target_rec(-nx + i)
            if t == 0:
                if basis == "X":
                    c.append("DETECTOR", [cur], (i, 0, 0, 0))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-nx - per + i)], (i, 0, t, 0))
        c.append("TICK")

    syndrome_round(0, noisy=False, prep_noise=False)          # ... and a noise-free round (the reference outcomes)
    for t in range(1, cycles + 1):
        # the check qubits of cycle t are prepared in the measurement timestep of the round before; in the first
        # cycle that timestep is the extra one of the 8C + 1, so its data qubits idle there too
        if t == 1:
            c.append("DEPOLARIZE1", data, p)
        syndrome_round(t, noisy=True, prep_noise=True)
    syndrome_round(cycles + 1, noisy=False, prep_noise=False)  # noise-free final stabilizer round
    if basis == "Z":
        c.append("M", data)
        for i in range(nz):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in zs[i]] + [stim.target_rec(-nq - nx - nz + i)],
                     (i, 0, cycles + 2, 3))
        logs = lz
    else:
        c.append("MX", data)
        for i in range(nx):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in xs[i]] + [stim.target_rec(-nq - nx + i)],
                     (i, 0, cycles + 2, 0))
        logs = lx
    for a, v in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-nq + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)          # raises if a detector is not deterministic
    return c


def build(size, basis, rounds, p=1e-3):
    sched, _ = schedule_from_env()
    return build_instruction(size, basis, rounds, p, sched)


translations = B.translations


def tag(size):
    return f"{size}_{schedule_from_env()[1]}"


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(HERE))
    import run_parallel
    key, basis, cycles, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    kmax = int(sys.argv[5]) if len(sys.argv) > 5 else 20
    tl = float(sys.argv[6]) if len(sys.argv) > 6 else 0
    run_parallel.main("ibm_bicycle", key, basis, out, cycles, 3, kmax, tl, 1)
