"""Stim memory circuit for a designed sequential schedule (design.py): one
cycle = X-check round then Z-check round, every check meeting its data qubits
in the given label order.  Noise: two-qubit depolarizing after every CNOT, a
flip after every preparation and before every measurement, no idle noise.

`verify` checks a design on the circuit: the columns of the effective problem
equal the columns of a one-round window of the circuit's detector error model,
and a minimum-weight solution, mapped to circuit faults, fires no detector and
flips an observable when replayed.
"""
import os
import sys

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import stabcode
from cdist import problem, replay


def build(code, order_x, order_z, basis, rounds, p=0.001):
    n, nx, nz = code.n, len(code.checks_x), len(code.checks_z)
    data = list(range(n))
    xa = [n + i for i in range(nx)]
    za = [n + nx + i for i in range(nz)]
    xl = [[q for i, c in enumerate(code.checks_x) for q in (xa[i], c[lab])] for lab in order_x]
    zl = [[q for i, c in enumerate(code.checks_z) for q in (c[lab], za[i])] for lab in order_z]
    for lay in xl + zl:
        assert len(set(lay)) == len(lay), "a qubit is used twice in one layer"
    c = stim.Circuit()
    c.append("RX" if basis == "X" else "R", data)
    c.append("Z_ERROR" if basis == "X" else "X_ERROR", data, p)
    c.append("TICK")
    per = nx + nz
    for t in range(rounds):
        c.append("RX", xa)
        c.append("Z_ERROR", xa, p)
        for tg in xl:
            c.append("TICK")
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, p)
        c.append("Z_ERROR", xa, p)
        c.append("MX", xa)
        c.append("TICK")
        c.append("R", za)
        c.append("X_ERROR", za, p)
        for tg in zl:
            c.append("TICK")
            c.append("CX", tg)
            c.append("DEPOLARIZE2", tg, p)
        c.append("X_ERROR", za, p)
        c.append("M", za)
        c.append("TICK")
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
    c.append("Z_ERROR" if basis == "X" else "X_ERROR", data, p)
    c.append("MX" if basis == "X" else "M", data)
    checks = code.checks_x if basis == "X" else code.checks_z
    for i, chk in enumerate(checks):
        back = -n - nz - nx + i if basis == "X" else -n - nz + i
        c.append("DETECTOR", [stim.target_rec(-n + q) for q in chk.values()] + [stim.target_rec(back)],
                 (i, 0, rounds, 0 if basis == "X" else 3))
    for a, v in enumerate(code.lx if basis == "X" else code.lz):
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-n + j) for j in stabcode.bits(v)], a)
    c.detector_error_model(decompose_errors=False)
    return c


def verify(code, order_x, order_z, basis, eff, sol, rounds=3, path=None):
    circ = build(code, order_x, order_z, basis, rounds)
    path = path or os.path.join(os.path.dirname(HERE), "circuits", "papers", f"{code.name}_seq_r{rounds}_{basis}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    exact = problem.sector_is_exact(full, sector)
    # X faults of a cycle are seen by the Z round of the same cycle; Z faults by the X round of the next
    tw = 0 if basis == "Z" else 1
    win = problem.window_problem(sector, tw, tw)
    bit = [int(m[0]) for m in win.row_meta]
    table = {}
    for j, (a, b) in enumerate(zip(win.h, win.l)):
        key = 0
        for r in stabcode.bits(a):
            key |= 1 << bit[r]
        table[(key, b)] = j
    same = set(table) == set(zip(eff.h, eff.l))
    # time-collapsed problem of the whole circuit: a lower bound for any number of rounds
    coll = problem.collapse_time(sector)
    cbit = [int(m[0]) for m in coll.row_meta]
    ccols = set()
    for a, b in zip(coll.h, coll.l):
        key = 0
        for r in stabcode.bits(a):
            key |= 1 << cbit[r]
        ccols.add((key, b))
    out = {"circuit": os.path.relpath(path, os.path.dirname(HERE)), "rounds": rounds, "sector_reduction_exact": exact,
           "effective_columns_equal_window_columns": same,
           "effective_columns_equal_collapsed_columns": ccols == set(zip(eff.h, eff.l))}
    if sol is not None and all((eff.h[j], eff.l[j]) in table for j in sol):
        cols = [win.col_meta[table[(eff.h[j], eff.l[j])]] for j in sol]
        raw = replay.lift_to_dem(full, sector, cols)
        dets, obs, terms = replay.check_in_dem(circ, raw)
        faults = replay.physical_faults(circ, raw)
        d2, o2 = replay.replay(circ, faults)
        out.update({"weight": len(raw), "replay": {"fired_detectors": d2, "flipped_observables": o2},
                    "verified": (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw),
                    "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis")} for f in faults]})
    return out
