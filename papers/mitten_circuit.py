"""Memory circuits for the mitten codes of "High-rate qLDPC processors"
(arXiv:2607.28795), built from the authors' published check matrices, logical
bases and gate-by-gate "hook-free" syndrome-extraction schedules
(github.com/a7b/yarn, processor_codes/mitten).

One cycle = an X-check round followed by a Z-check round, 12 entangling layers
each, in the order given by the schedule file.  Fault model of the paper:
depolarizing noise on state preparation, two-qubit gates and measurements,
no idle noise.  `idle=True` adds a depolarizing fault on every data qubit
that sits out an entangling layer (sensitivity check, not the paper's model).

Detector coordinates are (check index, 0, round, type) with type 3 for Z
checks and 0 for X checks, the convention `cdist.problem` expects.
"""
import json
import os

import numpy as np
import stim


def load(code_dir):
    H = {k: np.load(os.path.join(code_dir, k + ".npy")).astype(np.uint8) for k in ("Hx", "Hz", "Lx", "Lz")}
    sched = json.load(open(os.path.join(code_dir, "hook_free_SE_cycle_schedule.json")))
    return H, sched


def layers_of(sched, key, H):
    """Entangling layers as lists of (check row, data column); checked to
    reproduce the parity-check matrix exactly, with disjoint gates per layer."""
    out = []
    M = np.zeros_like(H)
    for lay in sched[key]["layers"]:
        gates = [(int(i), int(j)) for mv in lay["moves"] for i, j in mv["cz_gates"]]
        assert len({i for i, _ in gates}) == len(gates) and len({j for _, j in gates}) == len(gates)
        for i, j in gates:
            M[i, j] += 1
        out.append(gates)
    assert (M == H).all(), "schedule does not reproduce the check matrix"
    return out


def build(code_dir, basis, rounds, p=0.001, idle=False):
    H, sched = load(code_dir)
    Hx, Hz = H["Hx"], H["Hz"]
    n, nx, nz = Hx.shape[1], Hx.shape[0], Hz.shape[0]
    xa = [n + i for i in range(nx)]
    za = [n + nx + i for i in range(nz)]
    data = list(range(n))
    xl = layers_of(sched, "X_layers", Hx)
    zl = layers_of(sched, "Z_layers", Hz)
    c = stim.Circuit()
    c.append("RX" if basis == "X" else "R", data)
    c.append("DEPOLARIZE1", data, p)
    c.append("TICK")

    def x_round():
        c.append("RX", xa)
        c.append("DEPOLARIZE1", xa, p)
        for gates in xl:
            c.append("TICK")
            tg = [q for i, j in gates for q in (xa[i], j)]
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, p)
            if idle:
                busy = {j for _, j in gates}
                c.append("DEPOLARIZE1", [q for q in data if q not in busy], p)
        c.append("DEPOLARIZE1", xa, p)
        c.append("MX", xa)
        c.append("TICK")

    def z_round():
        c.append("R", za)
        c.append("DEPOLARIZE1", za, p)
        for gates in zl:
            c.append("TICK")
            tg = [q for i, j in gates for q in (j, za[i])]
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, p)
            if idle:
                busy = {j for _, j in gates}
                c.append("DEPOLARIZE1", [q for q in data if q not in busy], p)
        c.append("DEPOLARIZE1", za, p)
        c.append("M", za)
        c.append("TICK")

    for t in range(rounds):
        x_round()
        z_round()
        # after a cycle the last nx + nz records are [X checks, Z checks]
        per = nx + nz
        for i in range(nx):
            cur = stim.target_rec(-per + i)
            if t == 0:
                if basis == "X":
                    c.append("DETECTOR", [cur], (i, 0, 0, 0))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-2 * per + i)], (i, 0, t, 0))
        for i in range(nz):
            cur = stim.target_rec(-nz + i)
            if t == 0:
                if basis == "Z":
                    c.append("DETECTOR", [cur], (i, 0, 0, 3))
            else:
                c.append("DETECTOR", [cur, stim.target_rec(-nz - per + i)], (i, 0, t, 3))
    c.append("DEPOLARIZE1", data, p)
    c.append("MX" if basis == "X" else "M", data)
    Hm = Hx if basis == "X" else Hz
    nm = Hm.shape[0]
    for i in range(nm):
        recs = [stim.target_rec(-n + int(j)) for j in np.flatnonzero(Hm[i])]
        # last ancilla outcome of this check: X checks are measured before Z checks
        back = -n - nz - nx + i if basis == "X" else -n - nz + i
        c.append("DETECTOR", recs + [stim.target_rec(back)], (i, 0, rounds, 0 if basis == "X" else 3))
    L = H["Lx"] if basis == "X" else H["Lz"]
    for a in range(L.shape[0]):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + int(j)) for j in np.flatnonzero(L[a])], a)
    return c


if __name__ == "__main__":
    import sys
    code_dir, basis, rounds, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    idle = len(sys.argv) > 5 and sys.argv[5] == "idle"
    circ = build(code_dir, basis, rounds, idle=idle)
    circ.detector_error_model(decompose_errors=False)      # raises if a detector is not deterministic
    circ.to_file(out)
    print(out, "qubits", circ.num_qubits, "detectors", circ.num_detectors, "observables", circ.num_observables)
