"""Certified lower bounds on the logical error rate of a memory instruction of papers/ibm_bicycle.py, valid for
every decoder.

Let F be an undetectable logical fault set of minimum weight d of the instruction's detector error model (all of
them are listed by the exact search, one per symmetry orbit, then expanded).  Every split F = E + E' with
|E| = floor(d/2) and |E'| = ceil(d/2) gives two fault sets with the same detector outcomes whose logical effects
differ by F, so a decoder, being a function of the detector outcomes, fails on at least one of them.  The events
"the fired mechanisms are exactly E" are disjoint for distinct E, hence

    P_fail >= sum over disjoint pairs {E, E'} of min(P(exactly E), P(exactly E')).

Pairs taken from fault sets that share fewer than floor(d/2) mechanisms are disjoint, so the bound sums over a
family of minimum fault sets with pairwise intersections below floor(d/2), chosen greedily.  With U the union of the
family's sets, every pair {E + S, E' + S} with S a set of mechanisms outside U is a pair as well, and these events are
all distinct, so the sum over S removes the mechanisms outside U from the bound:

    P_fail >= sum over pairs of min(P_U(E), P_U(E')),   P_U(E) = prod_{j in E} p_j prod_{j in U - E} (1 - p_j).

Each sector column is realised by the full-model mechanism that touches no detector outside the sector
(cdist.replay.lift_to_dem), so the two halves also agree on every detector of the full model.  Probabilities are
those of Stim's detector error model at each p, with equal mechanisms merged.

Usage: python papers/ibm_bicycle_bound.py KEY BASIS CYCLES DISTANCE OUT.json [k_table | RECORD.json[,...]] [p ...]
       (RECORD.json: a bench pipeline record of the same instruction, whose witness is used, or the output of
       papers/ibm_bicycle_enum.py, whose fault sets are used; with their symmetry orbits, instead of all minimum
       fault sets)
       (schedule from IBM_SCHEDULE, as in papers/ibm_bicycle.py)
"""
import itertools
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import ibm_bicycle as IB
import run_parallel as RP
from cdist import lift, problem, replay, search

# Tour de gross (arXiv:2506.03094), Table 2: logical error rate of the "Idle" instruction (log10)
IBM_TABLE2 = {"gross": {1e-3: -8.8, 1e-4: -14.8}, "bb288": {1e-3: -20.1, 1e-4: -38.3}}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def merged_probabilities(circ):
    """{(detector mask, observable mask): probability} of the undecomposed detector error model."""
    dem = circ.detector_error_model(decompose_errors=False, flatten_loops=True)
    out = {}
    for inst in dem:
        if inst.type != "error":
            continue
        a = b = 0
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                a ^= 1 << t.val
            elif t.is_logical_observable_id():
                b ^= 1 << t.val
        q = inst.args_copy()[0]
        r = out.get((a, b), 0.0)
        out[(a, b)] = r + q - 2 * r * q              # two independent flips with the same effect
    return out


def pair_terms(logr, d):
    """log of min(prod_E r, prod_E' r) over the unordered splits with |E| = d // 2 (each pair once)."""
    h = d // 2
    idx = range(d)
    total = sum(logr)
    out = []
    if d % 2 == 0:
        for rest in itertools.combinations(range(1, d), h - 1):    # E contains element 0: each pair once
            a = logr[0] + sum(logr[i] for i in rest)
            out.append(min(a, total - a))
    else:
        for E in itertools.combinations(idx, h):
            a = sum(logr[i] for i in E)
            out.append(min(a, total - a))
    return out


def compute(key, basis, cycles, d, sched=None, stag="standard", k_table=3, ps=(1e-4, 2e-4, 5e-4, 1e-3, 2e-3),
            quiet=False, given=None):
    """All minimum fault sets of weight d (a certified distance) and the lower bounds; returns a dict.
    given: fault sets of weight d (sector columns) to use with their symmetry orbits instead of enumerating
    all of them; the bound stays valid (it is a sum over a subset), the leading-order estimate does not."""
    global log
    if quiet:
        log = lambda *a: None
    cycles, d, k_table = int(cycles), int(d), int(k_table)
    t0 = time.time()
    circ = IB.build_instruction(key, basis, cycles, 1e-3, sched)
    path = os.path.join(ROOT, "circuits", "papers", f"ibm_{key}_{stag}_c{cycles}_{basis}_{os.getpid()}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path, os.path.basename(path))
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector), "sector reduction not exact"
    sym, kw = RP.sym_of(sector, IB.translations(key))
    colmaps = sym.get("colmaps", []) if sym.get("ok") else []
    res = {"code": key, "schedule": stag, "basis": basis, "cycles": cycles, "distance": d, "k_table": k_table,
           "model": {"detectors": circ.num_detectors, "full_columns": full.ncols, "sector_columns": sector.ncols,
                     "symmetries": len(colmaps)}}
    log(res["model"])
    if given is None:
        # every solution of weight d (d is a certified distance, so the search at K = d is complete for minimum sets)
        S = search.Searcher(sector, labelfree=True, **kw)
        S.build_exclusions()
        table = search.Table(sector, k_table, labelfree=True)
        S.add_table(table, exact=True)
        r = S.search(d, enum_all=True, sol_cap=5_000_000)
        table.free()
        assert r["status"] == "exhausted" and r["best"] == d, (r["status"], r["best"])
        assert r["nsol_recorded"] < 5_000_000, "solution cap reached"
        reps = sorted({tuple(sorted(s)) for s in r["solutions"] if len(s) == d})
        res["source"] = "all minimum fault sets"
    else:
        reps = sorted({tuple(sorted(s)) for s in given})
        assert all(len(s) == d for s in reps)
        res["source"] = "given fault sets and their symmetry orbits"
    sols = sorted(lift.expand_orbits(reps, colmaps)) if colmaps else reps
    for s in sols:
        assert search.verify(sector, s)
    res["n_orbit_representatives"] = len(reps)
    res["n_minimum_fault_sets"] = len(sols)
    res["enumeration_seconds"] = round(time.time() - t0, 1)
    log(f"{len(reps)} orbit representatives, {len(sols)} minimum fault sets of weight {d}")
    # each sector solution as full-model columns (mechanisms touching no detector outside the sector)
    lookup = {(a, b): j for j, (a, b) in enumerate(zip(full.h, full.l))}
    rows = sector.notes["sector_rows"]

    def full_cols(s):
        out = []
        for j in s:
            lifted, m = 0, sector.h[j]
            while m:
                low = m & -m
                lifted ^= 1 << rows[low.bit_length() - 1]
                m ^= low
            out.append(lookup[(lifted, sector.l[j])])
        return out
    fsets = [full_cols(s) for s in sols]
    # greedy family with pairwise intersections below d // 2: all their splitting pairs are disjoint
    family, used = [], []
    for fs in fsets:
        sfs = set(fs)
        if all(len(sfs & u) < d // 2 for u in used):
            family.append(fs)
            used.append(sfs)
    res["n_family"] = len(family)
    union = sorted(set().union(*used)) if used else []
    res["n_family_mechanisms"] = len(union)
    log(f"family of {len(family)} fault sets with pairwise intersections < {d // 2}")
    # leading-order estimate for a minimum-weight decoder: the distinct failing configurations of weight
    # ceil(d/2) (odd d: the larger part of a split; even d: the less likely half of each distinct pair)
    h = d // 2
    configs = None
    if given is None and len(fsets) * math.comb(d, h) <= int(os.environ.get("IBM_CONFIG_CAP", "6000000")):
        configs = set()
        for fs in fsets:
            s = sorted(fs)
            if d % 2:
                configs.update(itertools.combinations(s, h + 1))
            else:
                for E in itertools.combinations(s, h):
                    Ep = tuple(x for x in s if x not in E)
                    configs.add((E, Ep) if E < Ep else (Ep, E))
        res["n_failing_configurations"] = len(configs)

    def logsum(ts):
        mx = max(ts)
        return mx + math.log(sum(math.exp(t - mx) for t in ts))
    rates = {}
    for p in ps:
        probs = merged_probabilities(IB.build_instruction(key, basis, cycles, p, sched))
        pj = [probs[(a, b)] for a, b in zip(full.h, full.l)]
        log0 = sum(math.log1p(-q) for q in pj)                    # every mechanism silent
        log0u = sum(math.log1p(-pj[j]) for j in union)            # every mechanism of the family's union silent
        logr = [math.log(q) - math.log1p(-q) for q in pj]
        terms = []
        for fs in family:
            terms += pair_terms([logr[j] for j in fs], d)
        lb = log0u + logsum(terms)
        rates[p] = {"log10_lower_bound": lb / math.log(10), "n_pairs": len(terms),
                    "log10_P_all_silent": log0 / math.log(10), "log10_P_union_silent": log0u / math.log(10)}
        if configs is not None:
            if d % 2:
                lead = [sum(logr[j] for j in c) for c in configs]
            else:
                lead = [min(sum(logr[j] for j in a), sum(logr[j] for j in b)) for a, b in configs]
            rates[p]["log10_leading_order"] = (log0 + logsum(lead)) / math.log(10)
        ibm = IBM_TABLE2.get(key, {}).get(p)
        if ibm is not None:
            rates[p]["log10_ibm_table2"] = ibm
        log(f"p={p:g}: P_fail >= 10^{lb / math.log(10):.2f} ({len(terms)} disjoint pairs)"
            + (f"; Tour de gross Table 2: 10^{ibm}" if ibm is not None else ""))
    res["rates"] = {str(p): v for p, v in rates.items()}
    res["examples"] = [sols[0]] if sols else []
    res["seconds"] = round(time.time() - t0, 1)
    os.remove(path)
    return res


def main(key, basis, cycles, d, out, k_table=3, ps=(1e-4, 2e-4, 5e-4, 1e-3, 2e-3)):
    sched, stag = IB.schedule_from_env()
    given = None
    if str(k_table).endswith(".json"):             # records with fault sets (sector columns), used with their orbits
        given = []
        for f in str(k_table).split(","):
            rec = json.load(open(f))
            given += rec["solutions"] if "solutions" in rec else [rec["witness"]]   # ibm_bicycle_enum.py, pipeline
        k_table = 3
    res = compute(key, basis, cycles, d, sched, stag, k_table, ps, given=given)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    log("wrote", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    ps = tuple(float(x) for x in a[6:]) or (1e-4, 2e-4, 5e-4, 1e-3, 2e-3)
    main(a[0], a[1], a[2], a[3], a[4], a[5] if len(a) > 5 else 3, ps)
