"""The decoder-independent bound on the logical error rate per cycle in Tour de gross's own simulation setting (C cycles),
from all logical operators of the code of a given weight, or from given fault sets.

The code's logical operators of minimum weight d are the undetectable logical fault sets among the mechanisms of one
round that act as a single data-qubit error each.  They are enumerated exactly in that window of the sector problem of
the one-cycle instruction (for the two-gross code: 336 of weight 18 of one Pauli type, the number in Tour de gross, its
App. A.1).  Each has a copy in every cycle.  These sets overlap in up to d - 3 qubits, so instead of a family of sets
with small intersections this script keeps pairs: a greedy matching over all splits F = E + E' in which no half is used
twice (the SI Proposition asks only that all halves be distinct; a hash collision can only drop a pair).

The bound for one cycle c needs the silence of the mechanisms U_c of that cycle only: every pair {E + S, E' + S}, with S
any set of mechanisms outside U_c, is a pair, so the failure probability restricted to the event H_c that the mechanisms
of U_c fired are a half of cycle c is at least B_c, the Proposition's sum with U = U_c.  The U_c are disjoint, so the
H_c are independent, and by Bonferroni

    P_fail >= sum_c B_c - sum_{c < c'} P(H_c) P(H_c').

The last term is of second order and is computed; it is negligible.

All copies are checked in the detector error model of the C-cycle circuit, and the copies in cycles IBM_BOUND_REPLAY
(default 1,2,9; empty for none) are replayed with explicit Pauli faults.

Usage: python papers/ibm_bicycle_code_logicals.py KEY BASIS CYCLES WEIGHT OUT.json SOURCE [p ...]
       SOURCE: "code", or comma-separated records of fault sets of the one-cycle instruction, as in
       papers/ibm_bicycle_matched_bound.py
"""
import json
import math
import os
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import ibm_bicycle as IB
import ibm_bicycle_matched as M
import ibm_bicycle_matched_bound as MB
import run_parallel as RP
from cdist import lift, problem, replay, search

REPLAY_CYCLES = tuple(int(x) for x in os.environ.get("IBM_BOUND_REPLAY", "1,2,9").split(",") if x)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def code_logicals(key, basis, d):
    """All logical operators of weight d, as columns of the sector problem of the one-cycle instruction."""
    circ = IB.build_instruction(key, basis, 1, 1e-3, None)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "c.stim")
        circ.to_file(path)
        full = problem.load_dem_problem(path, "c.stim")
    sector = problem.sector_problem(full)
    # the round whose mechanisms are the data-qubit errors alone: as many columns as data qubits
    w = min((problem.window_problem(sector, t, t) for t in (1, 2)), key=lambda q: q.ncols)
    sym, kw = RP.sym_of(w, IB.translations(key))
    colmaps = sym.get("colmaps", []) if sym.get("ok") else []
    S = search.Searcher(w, labelfree=True, **kw)
    table = search.Table(w, 3, labelfree=True)
    S.add_table(table, exact=True)
    r = S.search(d, enum_all=True, sol_cap=5_000_000, exclusions=False)
    table.free()
    assert r["status"] == "exhausted" and r["solutions_complete"], r["status"]
    reps = sorted({tuple(sorted(s)) for s in r["solutions"]})
    sols = sorted(lift.expand_orbits(reps, colmaps)) if colmaps else reps
    assert all(len(s) == d and search.verify(w, s) for s in sols)
    out = [sorted(w.col_meta[j] for j in s) for s in sols]
    assert all(search.verify(sector, s) for s in out)
    return out, {"window_columns": w.ncols, "orbit_representatives": len(reps), "symmetries": len(colmaps)}


def matching(sets, d):
    """Greedy matching over the splits of all sets (lists of positions): for the pairs kept, the positions of the
    halves E (pairs x d // 2) and the index of the set; no half is used twice."""
    rng = np.random.default_rng(20261031)
    code = rng.integers(1, 2 ** 63, max(j for s in sets for j in s) + 1, dtype=np.uint64)
    E = MB.pair_index(d)                                       # positions within a set of the halves E, each split once
    halves, which, used = [], [], set()
    for i, s in enumerate(sets):
        s = np.array(s, dtype=np.uint16)
        a = np.bitwise_xor.reduce(code[s[E]], axis=1)
        b = a ^ np.bitwise_xor.reduce(code[s])
        ok = np.fromiter((x not in used and y not in used for x, y in zip(a.tolist(), b.tolist())), bool, len(a))
        used.update(a[ok].tolist())
        used.update(b[ok].tolist())
        halves.append(s[E[ok]])
        which.append(np.full(int(ok.sum()), i, dtype=np.int32))
    return np.concatenate(halves), np.concatenate(which)


def main(key, basis, cycles, d, out, source, ps=MB.PS):
    cycles, d = int(cycles), int(d)
    t0 = time.time()
    info = {}
    if source == "code":
        sols, info = code_logicals(key, basis, d)
        log(f"{len(sols)} logical operators of weight {d}: {info}")
        source = os.path.join(tempfile.gettempdir(), f"code_logicals_{os.getpid()}.json")
        json.dump({"solutions": sols}, open(source, "w"))
        sets, sinfo = MB.source_sets(key, basis, d, source, None, "standard")
        os.remove(source)
        assert sinfo["n_fault_sets"] == len(sols)
        sinfo["source"] = "all logical operators of the code of this weight"
    else:
        sets, sinfo = MB.source_sets(key, basis, d, source, None, "standard")
    mech, copies, cyc, rep = MB.copies_in(key, basis, cycles, sets, None, check_replay=False)
    assert rep["dem_check_failures"] == 0, rep
    log("checked in the detector error model:", rep)
    if REPLAY_CYCLES:
        circ = M.build_matched(key, basis, cycles, 1e-3, None)
        dem = circ.detector_error_model(decompose_errors=False, flatten_loops=True)
        chosen = [ks for ks, c in zip(copies, cyc) if c in REPLAY_CYCLES]
        faults = MB.representative_faults(circ, dem, sorted({mech[k][2] for ks in chosen for k in ks}))
        good = 0
        for n, ks in enumerate(chosen):
            dets, obs = replay.replay(circ, [faults[mech[k][2]] for k in ks])
            good += (not dets) and (obs == sorted(MB.stim_bits(ks)))
            if n % 200 == 199:
                log(f"  replayed {n + 1}/{len(chosen)} ({good} undetected with the expected flips)")
        rep["replay"] = {"cycles": list(REPLAY_CYCLES), "replayed": len(chosen),
                         "undetected_with_expected_logical_flips": good}
        assert good == len(chosen)
    # one matching, used in every cycle: the copies of the sets in one cycle, by position
    nsets = len(sets)
    by_cycle = {c: [ks for ks, x in zip(copies, cyc) if x == c] for c in range(1, cycles + 1)}
    order = {c: sorted({k for s in v for k in s}) for c, v in by_cycle.items()}
    pos = {c: {k: i for i, k in enumerate(v)} for c, v in order.items()}
    place = {c: [[pos[c][k] for k in s] for s in by_cycle[c]] for c in by_cycle}
    assert all(place[c] == place[1] for c in place), "a cycle whose fault sets are not those of the first by position"
    assert all(not set(order[c]) & set(order[c + 1]) for c in range(1, cycles)), "copies in adjacent cycles share a mechanism"
    he, fi = matching(place[1], d)
    sets_pos = np.array(place[1])
    n_pairs = len(he)
    log(f"matching: {n_pairs} pairs per cycle (all splits: {nsets * len(MB.pair_index(d))})")
    res = {"code": key, "schedule": "standard", "basis": basis, "cycles": cycles, "distance": d,
           "noise": "linearised: independent faults of probability p/15 (Tour de gross App. A.7)",
           "sets": dict(sinfo, **info),
           f"C{cycles}": dict(rep, n_family=nsets * cycles, n_pairs_per_cycle=int(n_pairs),
                              n_family_mechanisms=sum(map(len, order.values())), rates={})}
    for p in ps:
        probs, _ = MB.mechanisms(M.build_matched(key, basis, cycles, p, None))
        groups = {}
        for c in by_cycle:
            pj = np.array([probs[k][0] for k in order[c]])
            groups.setdefault(tuple(np.round(pj / (p / 15), 6)), (pj, []))[1].append(c)
        contrib, halves = {}, {}
        for pj, cs in groups.values():
            log0 = float(np.log1p(-pj).sum())                  # the silence of this cycle's mechanisms
            lr = np.log(pj) - np.log1p(-pj)
            a = np.empty(n_pairs)
            for lo in range(0, n_pairs, 1 << 20):
                a[lo:lo + (1 << 20)] = lr[he[lo:lo + (1 << 20)]].sum(axis=1)
            b = lr[sets_pos].sum(axis=1)[fi] - a
            v = np.minimum(a, b)
            m = v.max()
            bound_c = log0 + m + math.log(np.exp(v - m).sum())
            m2 = max(a.max(), b.max())
            both = log0 + m2 + math.log(np.exp(a - m2).sum() + np.exp(b - m2).sum())
            for c in cs:
                contrib[c], halves[c] = bound_c, both
        logs = np.array([contrib[c] for c in sorted(contrib)])
        top = logs.max()
        total = math.exp(0) * np.exp(logs - top).sum()         # in units of exp(top)
        hv = np.array([halves[c] for c in sorted(halves)])
        pair_sum = sum(math.exp(hv[i] + hv[j] - top) for i in range(len(hv)) for j in range(i + 1, len(hv)))
        assert pair_sum < total, "the second-order term is not small here"
        lb = top + math.log(total - pair_sum)
        res[f"C{cycles}"]["rates"][str(p)] = {
            "log10_lower_bound_C_cycles": lb / math.log(10),
            "log10_lower_bound_per_cycle": (lb - math.log(cycles)) / math.log(10),
            "log10_second_order_term": (top + math.log(pair_sum)) / math.log(10) if pair_sum > 0 else None,
            "n_pairs": int(n_pairs) * cycles,
            "log10_contribution_by_cycle": {str(c): contrib[c] / math.log(10) for c in sorted(contrib)},
            "mechanism_probability_over_q": {str(c): sorted({round(probs[k][0] / (p / 15), 2) for k in order[c]})
                                             for c in (1, 2)}}
        log(f"p={p:g}: per cycle >= 10^{(lb - math.log(cycles)) / math.log(10):.2f}")
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    log("wrote", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], a[4], a[5], tuple(float(x) for x in a[6:]) or MB.PS)
