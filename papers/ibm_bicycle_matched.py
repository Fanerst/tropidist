"""The memory instruction of papers/ibm_bicycle.py as Tour de gross (arXiv:2506.03094) simulated it, for comparison
with the logical error rates of its Table 2:

  - unit-time initialisation and measurement (its Sec. 2.2): CNOT slot s of a cycle (0..6, as in papers/bb6_depth7.py)
    runs in timestep 1 + s, and each check qubit is prepared in the timestep before its first CNOT and measured in
    the timestep after its last.  In the standard schedule the X checks idle in slot 0 and the Z checks in slot 6, so
    the Z check qubit is prepared in timestep 0 and measured in 7, and the X check qubit prepared in 1 and measured
    in 8 while the Z check qubit is prepared for the next cycle (its Fig. 4): C cycles take 8C + 1 timesteps.  A check
    qubit with CNOTs in slots 0 and 6 is busy for nine timesteps, so a schedule with such checks takes nine
    timesteps per cycle (9C in all);
  - check qubits idle only between their preparation and their measurement; data qubits idle in every timestep
    without a CNOT;
  - noise linearised as in its App. A.7: every fault is an independent event of probability q = p/15, and an event of
    probability m p/15 is m such faults (each of the 15 Paulis after a CNOT once; X, Y and Z on an idle qubit five
    times each; the flip of a preparation or a measurement fifteen times), so that a mechanism made of m faults
    occurs with probability (1 - (1 - 2q)^m) / 2;
  - C noisy cycles between an error-free code state and a noise-free final stabilizer round, with the detectors
    (and their coordinates) and observables of papers/ibm_bicycle.py.  Tour de gross simulated the idle instruction
    with C = d*_circ cycles (10 for the gross code, 18 for the two-gross code) and reported the failure probability
    divided by C (App. A.7).

noise="stim" keeps this timing with the depolarizing channels of papers/ibm_bicycle.py.

Paper-module interface of papers/run_parallel.py, as papers/ibm_bicycle.py (schedule from IBM_SCHEDULE).

Usage: python papers/ibm_bicycle_matched.py KEY BASIS CYCLES OUT.json [kmax] [seconds per threshold]
"""
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bb6_depth7 as B
import ibm_bicycle as IB
import stabcode

CODES = IB.CODES
schedule_from_env = IB.schedule_from_env
translations = B.translations


def timing(schedule=None):
    """{check type: (preparation, measurement) timestep within a cycle} and the cycle's period in timesteps."""
    tx, tz = (B.STANDARD["X"], B.STANDARD["Z"]) if schedule is None else schedule
    pm = {typ: (min(t.values()), max(t.values()) + 2) for typ, t in (("X", tx), ("Z", tz))}
    return pm, max(m - a + 1 for a, m in pm.values())


def flip(m, q):
    """Probability that an odd number of m independent faults of probability q occur."""
    return (1 - (1 - 2 * q) ** m) / 2


def build_matched(key, basis, cycles, p=1e-3, schedule=None, noise="linear"):
    xs, zs, N = B.supports(key, schedule)
    nq = 2 * N
    hx = [sum(1 << q for _, q in g) for g in xs]
    hz = [sum(1 << q for _, q in g) for g in zs]
    assert (hx, hz, nq) == tuple(B.matrices(key))
    lx, lz = stabcode.css_logicals(hx, hz, nq)
    nx, nz = len(xs), len(zs)
    data = list(range(nq))
    anc = {"Z": [nq + i for i in range(nz)], "X": [nq + nz + i for i in range(nx)]}
    layers = []
    for t in range(7):
        tg = []
        for i, g in enumerate(xs):
            tg += [v for tt, q in g if tt == t for v in (anc["X"][i], q)]
        for i, g in enumerate(zs):
            tg += [v for tt, q in g if tt == t for v in (q, anc["Z"][i])]
        assert len(set(tg)) == len(tg)
        layers.append(tg)
    pm, period = timing(schedule)
    q = p / 15
    if noise == "linear":
        # Stim splits DEPOLARIZE2(r) into the 15 Paulis as independent events of probability
        # (1 - (1 - 16r/15)^(1/8)) / 2, which is q for this r
        cx_p, idle_ps, flip_p = 15 / 16 * (1 - (1 - 2 * q) ** 8), flip(5, q), flip(15, q)
    else:
        assert noise == "stim"
        cx_p, idle_ps, flip_p = p, None, p
    c = stim.Circuit()
    c.append("R" if basis == "Z" else "RX", data)            # error-free code state: noise-free data preparation ...
    c.append("TICK")
    first = {}                                                # (round, type) -> its first measurement record
    count = [0]

    def measure(r, typ):
        first[(r, typ)] = count[0]
        c.append("M" if typ == "Z" else "MX", anc[typ])
        count[0] += len(anc[typ])

    def detectors(r):
        for typ, n, k in (("Z", nz, 3), ("X", nx, 0)):
            for i in range(n):
                cur = stim.target_rec(first[(r, typ)] + i - count[0])
                if r == 0:
                    if typ == basis:
                        c.append("DETECTOR", [cur], (i, 0, 0, k))
                else:
                    c.append("DETECTOR", [cur, stim.target_rec(first[(r - 1, typ)] + i - count[0])], (i, 0, r, k))

    def clean_round(r):
        c.append("R", anc["Z"])
        c.append("RX", anc["X"])
        c.append("TICK")
        for tg in layers:
            c.append("CX", tg)
            c.append("TICK")
        measure(r, "Z")
        measure(r, "X")
        detectors(r)
        c.append("TICK")

    def idle(qs):
        if not qs:
            return
        if idle_ps is None:
            c.append("DEPOLARIZE1", qs, p)
        else:
            for e in ("X_ERROR", "Y_ERROR", "Z_ERROR"):
                c.append(e, qs, idle_ps)

    clean_round(0)                                            # ... and a noise-free round (the reference outcomes)
    last = max(m for _, m in pm.values())
    for T in range(period * (cycles - 1) + last + 1):         # the noisy timesteps, 8C + 1 or 9C
        busy = set()
        for typ in "ZX":                                      # measurements fail with probability p
            a, m = pm[typ]
            r = (T - m) // period + 1
            if (T - m) % period == 0 and 1 <= r <= cycles:
                c.append("X_ERROR" if typ == "Z" else "Z_ERROR", anc[typ], flip_p)
                measure(r, typ)
                busy.update(anc[typ])
        for typ in "ZX":                                      # preparations fail with probability p
            a, m = pm[typ]
            r = (T - a) // period + 1
            if (T - a) % period == 0 and 1 <= r <= cycles:
                c.append("R" if typ == "Z" else "RX", anc[typ])
                c.append("X_ERROR" if typ == "Z" else "Z_ERROR", anc[typ], flip_p)
                busy.update(anc[typ])
        r, s = (T - 1) // period + 1, (T - 1) % period        # CNOT slot s of cycle r
        if T >= 1 and s < 7 and r <= cycles:
            tg = layers[s]
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, cx_p)
            assert not busy & set(tg)
            busy.update(tg)
        live = list(data)                                     # check qubits idle between preparation and measurement
        for typ in "ZX":
            a, m = pm[typ]
            if any(a <= T - period * (r - 1) <= m for r in range(1, cycles + 1)):
                live += anc[typ]
        idle(sorted(set(live) - busy))
        r = (T - last) // period + 1                          # the round whose last measurement was in this timestep
        if (T - last) % period == 0 and 1 <= r <= cycles:
            detectors(r)
        c.append("TICK")
    clean_round(cycles + 1)                                   # noise-free final stabilizer round
    if basis == "Z":
        c.append("M", data)
        count[0] += nq
        for i in range(nz):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in zs[i]]
                     + [stim.target_rec(first[(cycles + 1, "Z")] + i - count[0])], (i, 0, cycles + 2, 3))
        logs = lz
    else:
        c.append("MX", data)
        count[0] += nq
        for i in range(nx):
            c.append("DETECTOR", [stim.target_rec(-nq + q) for _, q in xs[i]]
                     + [stim.target_rec(first[(cycles + 1, "X")] + i - count[0])], (i, 0, cycles + 2, 0))
        logs = lx
    for a, v in enumerate(logs):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-nq + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)          # raises if a detector is not deterministic
    return c


def build(size, basis, rounds, p=1e-3):
    sched, _ = schedule_from_env()
    return build_matched(size, basis, rounds, p, sched)


def tag(size):
    return f"{size}_{schedule_from_env()[1]}_matched"


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(HERE))
    import run_parallel
    key, basis, cycles, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    kmax = int(sys.argv[5]) if len(sys.argv) > 5 else 20
    tl = float(sys.argv[6]) if len(sys.argv) > 6 else 0
    run_parallel.main("ibm_bicycle_matched", key, basis, out, cycles, 3, kmax, tl, 1)
