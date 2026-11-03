"""Checks of the schedule px = 046135, pz = 531620 of the two-gross code that need no search:
  1. upper bound: a weight-18 logical of the code, put on the data qubits at one tick, is a fault set of the circuit in both bases;
  2. X and Z: the chain of symmetries from (s, Z) to (s, X), each step checked on the two circuits (iso_check.py), at C = 1, 2 and 3;
  3. IBM's timing: the sector columns of papers/ibm_bicycle_matched.py against those of papers/ibm_bicycle.py at C = 1."""
import collections as C
import json
import os
import sys
import tempfile

import stim

ROOT = os.environ.get("CD_ROOT", "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance")
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench", ROOT + "/results/bb288_scan/screen"]
import bb6_depth7 as B
import ibm_bicycle as IB
import ibm_bicycle_matched as M
import iso_check as ISO
import stabcode
import symmetry_classes as SC
from cdist import problem

S = ((0, 4, 6, 1, 3, 5), (5, 3, 1, 6, 2, 0))
assert S in set(B.all_valid())


def strip(c):
    out = stim.Circuit()
    for inst in c.flattened():
        if inst.name not in ("X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"):
            out.append(inst)
    return out


def inject_between_rounds(c, pauli, qubits, n_tick):
    out = stim.Circuit()
    t = 0
    for inst in c.flattened():
        if inst.name == "TICK":
            if t == n_tick:
                out.append(pauli + "_ERROR", qubits, 1.0)
            t += 1
        out.append(inst)
    return out


def weight18():
    """All X-type logicals of weight 18 from the standard schedule's record (a fault set of data qubits at one tick), and its Z-type image."""
    from cdist import replay
    r = json.load(open(ROOT + "/results/ibm/pipe_bb288_standard_c1_Z_2h.json"))
    c = IB.build_instruction("bb288", "Z", 1, 1e-3, None)
    with tempfile.TemporaryDirectory() as d:
        c.to_file(d + "/c.stim")
        full = problem.load_dem_problem(d + "/c.stim", "c")
    sec = problem.sector_problem(full)
    raw = replay.lift_to_dem(full, sec, r["witness"])
    f = replay.physical_faults(c, raw)
    q = sorted(q for x in f for p, q in x["paulis"])
    assert len(q) == 18 and all(p == "X" for x in f for p, _ in x["paulis"]), f[:2]
    print("weight-18 X-type support", q, "ticks", sorted({x["tick"] for x in f}))
    return q


def sigma(qs, N=144, l=12, m=12):
    neg = lambda u: ((-(u // m)) % l) * m + (-(u % m)) % m
    return sorted(N + neg(q) if q < N else neg(q - N) for q in qs)


def check_upper():
    qx = weight18()
    qz = sigma(qx)
    hx, hz, n = B.matrices("bb288")
    vx, vz = sum(1 << q for q in qx), sum(1 << q for q in qz)
    print("X-type commutes with all Z checks", all(bin(vx & r).count("1") % 2 == 0 for r in hz), "; Z-type with all X checks", all(bin(vz & r).count("1") % 2 == 0 for r in hx))
    for basis, pauli, q in (("Z", "X", qx), ("X", "Z", qz)):
        c = IB.build_instruction("bb288", basis, 1, 1e-3, B.to_dicts(*S))
        # the tick after the first noise-free round: the data qubits idle in the extra timestep there
        ticks = 0
        res = {}
        total = sum(1 for inst in c.flattened() if inst.name == "TICK")
        for t in range(total):
            d = inject_between_rounds(strip(c), pauli, q, t)
            det, obs = d.compile_detector_sampler().sample(1, separate_observables=True)
            res[t] = (int(det[0].sum()), int(obs[0].sum()))
        silent = [t for t, (a, b) in res.items() if a == 0 and b > 0]
        print("basis", basis, "weight", len(q), "ticks where the set is silent and flips a logical:", silent[:8], "of", total)


def chain(cycles):
    rep = {}
    gens = SC.group("bb288", None)
    start = (S, "Z")
    prev = {start: None}
    stack = [start]
    while stack:
        x = stack.pop(0)
        s, b = x
        for name, flip, f in gens:
            y = (f(s), ("X" if b == "Z" else "Z") if flip else b)
            if y not in prev:
                prev[y] = (x, name, flip)
                stack.append(y)
    target = (S, "X")
    assert target in prev
    path = []
    y = target
    while prev[y] is not None:
        x, name, flip = prev[y]
        path.append((x, y, name))
        y = x
    path.reverse()
    print("orbit size", len(prev), "chain", [p[2] for p in path])
    au = {f"{k}{phi}{pi}{rho}": (k, phi, pi, rho) for k, phi, pi, rho in SC.automorphisms("bb288")}
    (l, m), _, _ = B.CODES["bb288"][0]
    identity = [{i: i for i in range(l * m)}]
    ok = True
    for x, y, name in path:
        p = ISO.sector("bb288", x[0], x[1], cycles)
        q = ISO.sector("bb288", y[0], y[1], cycles)
        rounds = sorted({mm[2] for mm in p.row_meta})
        top = rounds[0] + rounds[-1]
        if name == "T":
            r = ISO.isomorphic(p, q, identity, [lambda t: top - t])
        else:
            k, phi, pi, rho = au[name]
            r = ISO.isomorphic(p, q, ISO.check_map_candidates("bb288", phi, k in ("inv", "swapinv")), [lambda t: t, lambda t: top - t])
        print("  step", name, "C", cycles, "isomorphic" if r else "NOT FOUND", flush=True)
        ok = ok and bool(r)
    print("X basis carried to Z basis at C =", cycles, ":", ok, flush=True)


def check_matched(cycles=1):
    for basis in "ZX":
        out = {}
        for tag, c in (("fused", IB.build_instruction("bb288", basis, cycles, 1e-3, B.to_dicts(*S))), ("matched", M.build_matched("bb288", basis, cycles, 1e-3, B.to_dicts(*S)))):
            with tempfile.TemporaryDirectory() as d:
                c.to_file(d + "/c.stim")
                full = problem.load_dem_problem(d + "/c.stim", "c")
            sec = problem.sector_problem(full)
            assert problem.sector_is_exact(full, sec)
            coords = lambda h: tuple(sorted(tuple(sec.row_meta[b]) for b in range(sec.nrows) if (h >> b) & 1))
            out[tag] = (set((coords(h), l) for h, l in zip(sec.h, sec.l)), sec.nrows, sec.ncols)
        a, b = out["fused"][0], out["matched"][0]
        print("basis", basis, "sector columns fused", len(a), "matched", len(b), "same set", a == b, "only fused", len(a - b), "only matched", len(b - a))
    pm, period = M.timing(B.to_dicts(*S))
    print("matched timing", pm, "timesteps per cycle", period)


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "upper":
        check_upper()
    elif which == "chain":
        chain(int(sys.argv[2]))
    elif which == "matched":
        check_matched(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
