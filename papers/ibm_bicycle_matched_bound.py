"""Decoder-independent lower bounds on the per-cycle logical error rate of the memory instruction in Tour de gross's
own simulation setting (papers/ibm_bicycle_matched.py: C cycles, unit-time preparation and measurement, linearised
noise), for comparison with its Table 2, whose rates are failure probabilities of C = d*_circ cycles divided by C.

A minimum fault set of the instruction with C = 1 lies within its one noisy cycle: its mechanisms fire detectors of
rounds 1 and 2 only, which compare the cycle's outcomes with those of the noise-free rounds before and after.  Its
copy in cycle c of a C-cycle circuit (the same faults, c - 1 cycles later) fires the same detectors shifted by c - 1
rounds, so it is again undetected and flips the same observables.  This script

  1. takes the fault sets of the C = 1 instruction with their symmetry orbits, from records of
     papers/ibm_bicycle.py's instruction (fused measurement and reset; its detector error model has the same mechanisms,
     which is checked) or from the exact enumeration of all minimum fault sets of the matched C = 1 instruction;
  2. finds each copy's mechanisms in the detector error model of the matched C-cycle circuit by their shifted detector
     coordinates, checks that the copy fires no detector and flips an observable there, and replays it physically
     with explicit Pauli faults (cdist.replay);
  3. evaluates the bound of papers/ibm_bicycle_bound.py (SI Proposition: disjoint halves, P_U with U the union of the
     family) on all copies in all cycles, and divides it by C.

Usage: python papers/ibm_bicycle_matched_bound.py KEY BASIS CYCLES DISTANCE OUT.json SOURCE [p ...]
       SOURCE: comma-separated records (pipeline records, papers/ibm_bicycle_bound.py or papers/ibm_bicycle_enum.py
       outputs: sector columns of papers/ibm_bicycle.py's C = 1 instruction), or "enumerate"
       (schedule from IBM_SCHEDULE, as in papers/ibm_bicycle.py)
"""
import itertools
import json
import math
import os
import sys
import time

import numpy as np
import stim

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import ibm_bicycle as IB
import ibm_bicycle_bound as BD
import ibm_bicycle_matched as M
import run_parallel as RP
from cdist import lift, problem, replay, search

PS = (1e-4, 2e-4, 5e-4, 7.322e-4, 1e-3)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def mechanisms(circ):
    """The undecomposed detector error model merged by effect: {(sorted detector coordinates, observable mask):
    [probability, detector mask, index of one raw error]}."""
    dem = circ.detector_error_model(decompose_errors=False, flatten_loops=True)
    coords = {i: tuple(v) for i, v in circ.get_detector_coordinates().items()}
    out = {}
    raw = 0
    for inst in dem:
        if inst.type != "error":
            continue
        dets, a, b = [], 0, 0
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                dets.append(coords[t.val])
                a ^= 1 << t.val
            elif t.is_logical_observable_id():
                b ^= 1 << t.val
        k = (tuple(sorted(dets)), b)
        q = inst.args_copy()[0]
        if k in out:
            r = out[k][0]
            out[k][0] = r + q - 2 * r * q                    # two independent flips with the same effect
        else:
            out[k] = [q, a, raw]
        raw += 1
    return out, dem


def sector_of(circ, tmpname):
    path = os.path.join(ROOT, "circuits", "papers", f"{tmpname}_{os.getpid()}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path, os.path.basename(path))
    os.remove(path)
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector), "sector reduction not exact"
    return full, sector


def source_sets(key, basis, d, source, sched, stag):
    """The fault sets of the C = 1 instruction (with their orbits) as lists of (detector coordinates, observables)."""
    circ = (M.build_matched if source == "enumerate" else IB.build_instruction)(key, basis, 1, 1e-3, sched)
    full, sector = sector_of(circ, f"ibm_src_{key}_{stag}_{basis}")
    sym, kw = RP.sym_of(sector, IB.translations(key))
    colmaps = sym.get("colmaps", []) if sym.get("ok") else []
    info = {"source": source, "symmetries": len(colmaps)}
    if source == "enumerate":                                 # every minimum fault set (d is a certified distance)
        S = search.Searcher(sector, labelfree=True, **kw)
        S.build_exclusions()
        table = search.Table(sector, 3, labelfree=True)
        S.add_table(table, exact=True)
        r = S.search(d, enum_all=True, sol_cap=5_000_000)
        table.free()
        assert r["status"] == "exhausted" and r["best"] == d, (r["status"], r["best"])
        assert r["nsol_recorded"] < 5_000_000, "solution cap reached"
        reps = sorted({tuple(sorted(s)) for s in r["solutions"] if len(s) == d})
    else:
        reps = []
        for f in source.split(","):
            rec = json.load(open(f))
            reps += rec["solutions"] if "solutions" in rec else [rec["witness"]] if "witness" in rec else rec["examples"]
        reps = sorted({tuple(sorted(s)) for s in reps})
        assert all(len(s) == d for s in reps)
    sols = sorted(lift.expand_orbits(reps, colmaps)) if colmaps else reps
    for s in sols:
        assert search.verify(sector, s)
    info.update(n_orbit_representatives=len(reps), n_fault_sets=len(sols))
    lookup = {(a, b): j for j, (a, b) in enumerate(zip(full.h, full.l))}
    rows = sector.notes["sector_rows"]
    out = []
    for s in sols:
        fs = []
        for j in s:
            lifted, m = 0, sector.h[j]
            while m:
                low = m & -m
                lifted ^= 1 << rows[low.bit_length() - 1]
                m ^= low
            jf = lookup[(lifted, sector.l[j])]
            dets = tuple(sorted(full.row_meta[i] for i in range(full.nrows) if full.h[jf] >> i & 1))
            assert all(t in (1, 2) for _, _, t, _ in dets), "a mechanism outside the noisy cycle"
            fs.append((dets, sector.l[j]))
        out.append(fs)
    return out, info


def shifted(fs, c):
    """The copy of a fault set of the C = 1 instruction in cycle c."""
    return [(tuple((i, y, t + c - 1, k) for i, y, t, k in dets), b) for dets, b in fs]


def representative_faults(circ, dem, raw_indices):
    """One physical fault per raw detector-error-model error (as cdist.replay.physical_faults), in one call."""
    errs = [inst for inst in dem if inst.type == "error"]
    flt = stim.DetectorErrorModel()
    want = {}
    for i in raw_indices:
        flt.append(errs[i])
        t = errs[i].targets_copy()
        want[(frozenset(x.val for x in t if x.is_relative_detector_id()),
              frozenset(x.val for x in t if x.is_logical_observable_id()))] = i
    out = {}
    for e in circ.explain_detector_error_model_errors(dem_filter=flt, reduce_to_one_representative_error=True):
        t = [x.dem_target for x in e.dem_error_terms]
        i = want[(frozenset(x.val for x in t if x.is_relative_detector_id()),
                  frozenset(x.val for x in t if x.is_logical_observable_id()))]
        loc = e.circuit_error_locations[0]
        out[i] = {"tick": loc.tick_offset, "instruction": loc.instruction_targets.gate,
                  "paulis": [(x.gate_target.pauli_type, x.gate_target.value) for x in loc.flipped_pauli_product],
                  "stack": [(f.instruction_offset, f.iteration_index, f.instruction_repetitions_arg)
                            for f in loc.stack_frames],
                  "flipped_measurement": None if loc.flipped_measurement is None
                  else loc.flipped_measurement.record_index}
    assert set(out) == set(raw_indices)
    return out


def copies_in(key, basis, cycles, sets, sched, check_replay=True):
    """The copies of the given fault sets in every cycle of the matched C-cycle circuit, checked in its detector error
    model and replayed; returns (mechanism table at p = 1e-3, copies as lists of keys, cycle of each copy, report)."""
    circ = M.build_matched(key, basis, cycles, 1e-3, sched)
    mech, dem = mechanisms(circ)
    copies, cyc = [], []
    for c in range(1, cycles + 1):
        for fs in sets:
            ks = shifted(fs, c)
            missing = [k for k in ks if k not in mech]
            assert not missing, f"cycle {c}: {len(missing)} mechanisms not in the C = {cycles} model"
            copies.append(ks)
            cyc.append(c)
    rep = {"circuit": {"qubits": circ.num_qubits, "detectors": circ.num_detectors, "ticks": circ.num_ticks,
                       "mechanisms": len(mech)}, "copies": len(copies)}
    bad = 0
    for ks in copies:                                         # the detector error model's own check
        a = b = 0
        for k in ks:
            a ^= mech[k][1]
            b ^= k[1]
        bad += (a != 0) or (b == 0) or len(set(ks)) != len(ks)
    rep["dem_check_failures"] = bad
    if check_replay:
        t0 = time.time()
        need = sorted({mech[k][2] for ks in copies for k in ks})
        faults = representative_faults(circ, dem, need)
        ok = 0
        for n, ks in enumerate(copies):
            fl = [faults[mech[k][2]] for k in ks]
            dets, obs = replay.replay(circ, fl)
            ok += (not dets) and (obs == sorted(stim_bits(ks)))
            if n % 100 == 99:
                log(f"  replayed {n + 1}/{len(copies)} ({ok} undetected with the expected flips)")
        rep["replay"] = {"replayed": len(copies), "undetected_with_expected_logical_flips": ok,
                         "seconds": round(time.time() - t0, 1)}
    return mech, copies, cyc, rep


def stim_bits(ks):
    b = 0
    for k in ks:
        b ^= k[1]
    return [i for i in range(b.bit_length()) if b >> i & 1]


def pair_index(d):
    """Index arrays of the halves E (|E| = d // 2) of the unordered splits of a set of d elements, each pair once."""
    h = d // 2
    if d % 2 == 0:
        return np.array([(0,) + c for c in itertools.combinations(range(1, d), h - 1)])
    return np.array(list(itertools.combinations(range(d), h)))


def bound(key, basis, cycles, d, copies, cyc, sched, ps):
    """The SI Proposition's bound on all given copies (a greedy family with pairwise intersections below d // 2)."""
    ids = {}
    fam, used = [], []
    for ks, c in zip(copies, cyc):
        s = {ids.setdefault(k, len(ids)) for k in ks}
        if all(len(s & u) < d // 2 for u in used):
            fam.append(([ids[k] for k in ks], c))
            used.append(s)
    union = sorted(set().union(*used))
    keys = [None] * len(ids)
    for k, j in ids.items():
        keys[j] = k
    E = pair_index(d)
    res = {"n_family": len(fam), "n_family_mechanisms": len(union), "rates": {}}
    for p in ps:
        mech, _ = mechanisms(M.build_matched(key, basis, cycles, p, sched))
        pj = np.array([mech[k][0] for k in keys])
        logr = np.log(pj) - np.log1p(-pj)
        log0u = float(np.log1p(-pj[union]).sum())
        A = np.array([f for f, _ in fam])                    # family x d
        per_set = np.empty(len(fam))                          # log of the sum of the set's pair terms
        for lo in range(0, len(fam), 64):
            lr = logr[A[lo:lo + 64]]
            a = lr[:, E].sum(axis=2)                          # sets x pairs: log of the product over E
            terms = np.minimum(a, lr.sum(axis=1)[:, None] - a)
            m = terms.max(axis=1)
            per_set[lo:lo + 64] = m + np.log(np.exp(terms - m[:, None]).sum(axis=1))
        mx = per_set.max()
        lb = log0u + mx + math.log(np.exp(per_set - mx).sum())
        by_cycle = {}
        for (f, c), v in zip(fam, per_set):
            by_cycle.setdefault(c, []).append(v)
        cyc_log10 = {c: (log0u + max(v) + math.log(sum(math.exp(x - max(v)) for x in v))) / math.log(10)
                     for c, v in sorted(by_cycle.items())}
        ibm = BD.IBM_TABLE2.get(key, {}).get(p)
        r = {"log10_lower_bound_C_cycles": lb / math.log(10),
             "log10_lower_bound_per_cycle": (lb - math.log(cycles)) / math.log(10),
             "n_pairs": len(fam) * len(E), "log10_P_union_silent": log0u / math.log(10),
             "log10_contribution_by_cycle": {str(c): v for c, v in cyc_log10.items()}}
        if ibm is not None:
            r["log10_ibm_table2"] = ibm
            r["orders_above_ibm"] = r["log10_lower_bound_per_cycle"] - ibm
        res["rates"][str(p)] = r
        log(f"p={p:g}: C = {cycles}: P_fail >= 10^{r['log10_lower_bound_C_cycles']:.2f}, per cycle "
            f">= 10^{r['log10_lower_bound_per_cycle']:.2f}" + (f"; Table 2: 10^{ibm}, {r['orders_above_ibm']:.2f} "
                                                              "orders above" if ibm is not None else ""))
    return res


def main(key, basis, cycles, d, out, source, ps=PS):
    cycles, d = int(cycles), int(d)
    sched, stag = IB.schedule_from_env()
    t0 = time.time()
    sets, info = source_sets(key, basis, d, source, sched, stag)
    log(f"{key} {stag} {basis}: {info['n_fault_sets']} fault sets of weight {d} ({info['n_orbit_representatives']} "
        f"orbit representatives)")
    pm, period = M.timing(sched)
    res = {"code": key, "schedule": stag, "basis": basis, "cycles": cycles, "distance": d,
           "timing": {"period": period, "noisy_timesteps": period * (cycles - 1) + max(m for _, m in pm.values()) + 1,
                      "preparation_measurement": {t: list(v) for t, v in pm.items()}},
           "noise": "linearised: independent faults of probability p/15 (Tour de gross App. A.7)",
           "sets": info, "example": [list(map(list, (dets, [b]))) for dets, b in sets[0]]}
    # the matched C = 1 instruction against papers/ibm_bicycle.py's: the same mechanisms, so the same distance
    m1, _ = mechanisms(M.build_matched(key, basis, 1, 1e-4, sched))
    f1, _ = mechanisms(IB.build_instruction(key, basis, 1, 1e-4, sched))
    ratio = sorted(f1[k][0] / m1[k][0] for k in f1 if k in m1)
    res["c1_vs_fused"] = {"same_mechanisms": set(m1) == set(f1), "mechanisms": len(m1),
                          "probability_ratio_fused_over_matched_at_1e-4": {
                              "min": ratio[0], "max": ratio[-1],
                              "n_changed_by_1pct": sum(abs(x - 1) > 0.01 for x in ratio)}}
    log("C = 1, matched vs fused timing:", res["c1_vs_fused"])
    for C in sorted({1, cycles}):
        log(f"copies in the matched C = {C} circuit")
        mech, copies, cyc, rep = copies_in(key, basis, C, sets, sched)
        log(f"C = {C}: {rep}")
        b = bound(key, basis, C, d, copies, cyc, sched, ps)
        res[f"C{C}"] = dict(rep, **b)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out, "w"), indent=1)
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    log("wrote", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], a[4], a[5], tuple(float(x) for x in a[6:]) or PS)
