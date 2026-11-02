"""Low-weight failures of a minimum-weight decoder on the memory instruction in Tour de gross's own simulation setting
(papers/ibm_bicycle_matched.py, C cycles), from all logical fault sets of weight at most 12
(papers/ibm_bicycle_matched_spectrum.py, one set per orbit of the lattice translations).

The rule is that of papers/ibm_bicycle_mwd.py:

    weight 5 (d = 10):   the less likely half of each split of a weight-10 set into halves;
    weight 6:            the subsets of weight 6 of weight-10 sets (d = 10) and of weight-11 sets, without those that
                         contain a failing configuration of weight 5, and the less likely half of each split of a
                         weight-12 set in which no half contains a reducible pair.

Each configuration contributes the product of its mechanisms' probabilities.  The configurations of weight 6 from
weight-10 and weight-11 sets are counted once, the halves of weight-12 sets without that check.  All probabilities are
invariant under the lattice translations, so each orbit counts with its size.  Rates are failure probabilities of the
C cycles; the record also gives them divided by C, as Tour de gross reports them.

Usage: python papers/ibm_bicycle_matched_mwd.py OUT.json SPECTRUM.npz [SPECTRUM.npz ...] [-- p ...]
       (code, basis, cycles and schedule of each spectrum from its metadata)
"""
import itertools
import json
import math
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import ibm_bicycle as IB
import ibm_bicycle_bound as BD
import ibm_bicycle_matched as M
import ibm_bicycle_matched_spectrum as SP
import ibm_bicycle_mwd as MW
import run_parallel as RP
from cdist import problem

PS = (1e-5, 2e-5, 5e-5, 7e-5, 1e-4, 1.4e-4, 2e-4, 3e-4, 5e-4)


def model(key, basis, cycles, sched):
    """The full model, the map from sector columns to its mechanisms and the sector's column maps."""
    circ = M.build_matched(key, basis, cycles, 1e-3, sched)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "c.stim")
        circ.to_file(path)
        full = problem.load_dem_problem(path, "c.stim")
    sector = problem.sector_problem(full)
    sym, _ = RP.sym_of(sector, IB.translations(key))
    colmaps = [list(map(int, c)) for c in sym["colmaps"]]
    lookup = {(a, b): j for j, (a, b) in enumerate(zip(full.h, full.l))}
    rows = sector.notes["sector_rows"]
    cmap = []
    for j in range(sector.ncols):
        lifted, m = 0, sector.h[j]
        while m:
            low = m & -m
            lifted ^= 1 << rows[low.bit_length() - 1]
            m ^= low
        cmap.append(lookup.get((lifted, sector.l[j]), -1))
    return full, sector, np.array(cmap), colmaps


def logsum(v):
    v = np.asarray(v, dtype=float)
    if len(v) == 0:
        return -math.inf
    m = v.max()
    return m + math.log(np.exp(v - m).sum())


def reducible_mask(sets12, sector, full, cmap, combos):
    """For each weight-12 set (sector columns) the splits in which a half contains a reducible pair."""
    single = set(zip(full.h, full.l))
    h = [full.h[j] for j in cmap]
    l = [full.l[j] for j in cmap]
    bad = {}
    mask = np.zeros((len(combos), 12), dtype=bool)
    for i, c in enumerate(combos):
        mask[i, list(c)] = True
    for k, G in enumerate(sets12.tolist()):
        pr = [(i, j) for i in range(12) for j in range(i + 1, 12) if (h[G[i]] ^ h[G[j]], l[G[i]] ^ l[G[j]]) in single]
        if pr:
            b = np.zeros(len(combos), dtype=bool)
            for i, j in pr:
                b |= mask[:, i] == mask[:, j]
            bad[k] = b
    return bad, mask


def analyse(spectrum, ps):
    z = np.load(spectrum)
    meta = json.loads(str(z["meta"]))
    key, basis, cycles = meta["key"], meta["basis"], meta["cycles"]
    assert meta["runs"][-1]["complete"] and meta["runs"][-1]["K"] >= 12
    stag = meta["schedule"]
    sched = MW.schedule_of(stag)
    full, sector, cmap, colmaps = model(key, basis, cycles, sched)
    sets = {w: z[f"sets_{w}"].astype(np.int64) for w in (10, 11, 12) if f"sets_{w}" in z}
    orbit = {w: z[f"orbit_{w}"].astype(float) for w in sets}
    for w in sets:
        assert (cmap[sets[w]] >= 0).all(), "a column without a mechanism in the sector"
    d = min(sets)
    res = {"code": key, "schedule": stag, "basis": basis, "cycles": cycles, "distance": d,
           "sets_by_weight": {str(w): int(orbit[w].sum()) for w in sorted(sets)},
           "orbits_by_weight": {str(w): len(sets[w]) for w in sorted(sets)}, "search": meta["runs"][-1],
           "translated_from_cycles": meta.get("translated_from_cycles"), "rates": {}}
    # weight 5 from weight-10 sets, both halves of every split, with the set's orbit size
    pairs5 = None
    if d == 10:
        combos = np.array([c for c in itertools.combinations(range(10), 5) if 0 in c])
        rest = np.array([[x for x in range(10) if x not in c] for c in combos])
        pairs5 = (sets[10][:, combos], sets[10][:, rest], np.repeat(orbit[10], len(combos)))
        res["n_splits_weight10"] = int(orbit[10].sum()) * len(combos)
    # weight-6 subsets of weight-10 and weight-11 sets, one per orbit, without repeats
    subs = []
    for g in (10, 11):
        if g in sets:
            c6 = np.array(list(itertools.combinations(range(g), 6)))
            subs.append(sets[g][:, c6].reshape(-1, 6))
    six, six_orbit = (SP.canonical(np.concatenate(subs), colmaps) if subs else (np.zeros((0, 6), int), np.zeros(0)))
    res["n_w6_from_10_11"] = int(six_orbit.sum())
    # weight 6 from weight-12 sets
    combos12 = np.array([c for c in itertools.combinations(range(12), 6) if 0 in c])
    rest12 = np.array([[x for x in range(12) if x not in c] for c in combos12])
    bad, _ = reducible_mask(sets[12], sector, full, cmap, combos12) if 12 in sets else ({}, None)
    res["n_sets12_orbits_with_reducible_pairs"] = len(bad)
    rng = np.random.default_rng(20261031)
    code = rng.integers(1, 2 ** 63, sector.ncols, dtype=np.uint64)
    for p in ps:
        probs = BD.merged_probabilities(M.build_matched(key, basis, cycles, p, sched))
        pj = np.array([probs[(full.h[j], full.l[j])] if j >= 0 else 1e-300 for j in cmap])
        logr = np.log(pj)
        r = {}
        terms5, fail5 = [], np.zeros(0, dtype=np.uint64)
        if pairs5 is not None:
            a, b = logr[pairs5[0]].sum(axis=2), logr[pairs5[1]].sum(axis=2)     # (sets, splits)
            v = np.minimum(a, b).ravel()
            terms5 = v + np.log(pairs5[2])
            r["log10_w5"] = logsum(terms5) / math.log(10)
            # the failing configurations, in all translates, by hash
            worse = np.where((a <= b)[:, :, None], pairs5[0], pairs5[1]).reshape(-1, 5)
            maps = np.vstack([np.arange(sector.ncols)[None, :], np.array(colmaps)])
            hashes = [np.bitwise_xor.reduce(code[maps[:, worse[lo:lo + 4096]]], axis=2).ravel()
                      for lo in range(0, len(worse), 4096)]
            fail5 = np.unique(np.concatenate(hashes))
        else:
            r["log10_w5"] = -math.inf
        keep = np.ones(len(six), dtype=bool)
        if len(fail5) and len(six):
            h = np.bitwise_xor.reduce(code[six], axis=1)
            for j in range(6):
                sub = h ^ code[six[:, j]]
                i = np.searchsorted(fail5, sub).clip(max=len(fail5) - 1)
                keep &= fail5[i] != sub
        t6a = logr[six[keep]].sum(axis=1) + np.log(six_orbit[keep]) if len(six) else np.zeros(0)
        r["log10_w6_from_10_11"] = logsum(t6a) / math.log(10)
        r["n_w6_from_10_11_kept"] = int(six_orbit[keep].sum()) if len(six) else 0
        sums, n = [], 0.0
        for lo in range(0, len(sets[12]), 8192):
            block = sets[12][lo:lo + 8192]
            a = logr[block[:, combos12]].sum(axis=2)
            b = logr[block[:, rest12]].sum(axis=2)
            v = np.minimum(a, b)
            for k in range(len(block)):
                if lo + k in bad:
                    v[k, bad[lo + k]] = -np.inf
            good = np.isfinite(v)
            sums.append(logsum(v[good] + np.log(np.repeat(orbit[12][lo:lo + 8192], good.sum(axis=1)))))
            n += float((good.sum(axis=1) * orbit[12][lo:lo + 8192]).sum())
        r["log10_w6_from_12"] = logsum(sums) / math.log(10)
        r["n_w6_from_12"] = n
        total = logsum([x * math.log(10) for x in (r["log10_w5"], r["log10_w6_from_10_11"], r["log10_w6_from_12"])
                        if x != -math.inf])
        r["log10_total"] = total / math.log(10)
        r["log10_total_per_cycle"] = (total - math.log(cycles)) / math.log(10)
        res["rates"][str(p)] = r
        print(key, stag, basis, p, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    return res


def main(out, *rest):
    rest = list(rest)
    ps = PS
    if "--" in rest:
        i = rest.index("--")
        ps = tuple(float(x) for x in rest[i + 1:])
        rest = rest[:i]
    res = [analyse(f, ps) for f in rest]
    json.dump({"p": list(ps), "entries": res}, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
