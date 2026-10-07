"""Independent construction of the hook-augmented ("effective") distance
problem of a mitten code directly from the published matrices and schedule,
without Stim.

For the Z-basis memory the relevant faults are X-type: a single X on a data
qubit, or an X on an X-check ancilla after its m-th entangling gate, which
spreads to the data qubits of the remaining gates of that check.  Rows are the
Z checks, observables the rows of Lz.  (X basis: swap the roles.)

Because the X-check round and the Z-check round are executed one after the
other, every such fault is seen by one and the same round of opposite-type
checks, so this problem is the circuit-level one, not just a bound.
"""
import numpy as np

from cdist.problem import Problem, dedupe
from mitten_circuit import layers_of, load


def effective_problem(code_dir, basis):
    H, sched = load(code_dir)
    if basis == "Z":       # X errors: hooks from X checks, detected by Z checks
        Hhook, Hdet, L, key = H["Hx"], H["Hz"], H["Lz"], "X_layers"
    else:
        Hhook, Hdet, L, key = H["Hz"], H["Hx"], H["Lx"], "Z_layers"
    n = Hdet.shape[1]
    colh = [sum(1 << int(r) for r in np.flatnonzero(Hdet[:, j])) for j in range(n)]
    coll = [sum(1 << int(a) for a in np.flatnonzero(L[:, j])) for j in range(n)]
    order = {}
    for gates in layers_of(sched, key, Hhook):
        for i, j in gates:
            order.setdefault(i, []).append(j)
    h, l, meta = list(colh), list(coll), [("data", j) for j in range(n)]
    for i, js in order.items():
        for m in range(1, len(js)):
            a = b = 0
            for j in js[m:]:
                a ^= colh[j]
                b ^= coll[j]
            h.append(a)
            l.append(b)
            meta.append(("hook", i, m))
    hh, ll, cm = dedupe(h, l, meta)
    return Problem(f"effective:{basis}", Hdet.shape[0], L.shape[0], hh, ll, [(i, 0) for i in range(Hdet.shape[0])], cm)
