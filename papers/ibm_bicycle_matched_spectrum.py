"""All undetectable logical fault sets of weight at most KMAX of the memory instruction in Tour de gross's own simulation
setting (papers/ibm_bicycle_matched.py, C cycles), for the low-weight failures of a minimum-weight decoder
(papers/ibm_bicycle_matched_mwd.py).  Compute servers without Stim run the search on an exported problem.

    export: python papers/ibm_bicycle_matched_spectrum.py export KEY BASIS CYCLES OUT.pkl   (needs Stim)
    search: OMP_NUM_THREADS=N python papers/ibm_bicycle_matched_spectrum.py search IN.pkl KMIN KMAX OUT.npz SECONDS [k_table]
    translate: python papers/ibm_bicycle_matched_spectrum.py translate SMALL.pkl SMALL.npz BIG.pkl OUT.npz [COMPARE.npz]

translate: a three-column lookup table for many cycles does not fit in memory, but the fault sets are local in time.  Every
translate in time of a fault set of a circuit of few cycles whose mechanisms exist in a circuit of more cycles is a
fault set of that circuit, since its detectors and observables are the same up to the shift.  The script writes
all of them and, given the enumeration of the larger circuit, compares the two.

The schedule comes from IBM_SCHEDULE, as in papers/ibm_bicycle.py.  The search runs without dominance exclusions, which
keep every set of minimum weight but may drop heavier ones, and keeps one set per orbit of the lattice translations.
OUT.npz holds, per weight w, the array sets_w of sector columns (orbit representatives), and the orbit sizes.
"""
import json
import os
import pickle
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from cdist import problem, search


def export(key, basis, cycles, out):
    import ibm_bicycle as IB
    import ibm_bicycle_matched as M
    import run_parallel as RP
    sched, stag = IB.schedule_from_env()
    cycles = int(cycles)
    circ = M.build_matched(key, basis, cycles, 1e-3, sched)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "c.stim")
        circ.to_file(path)
        full = problem.load_dem_problem(path, "c.stim")
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector), "sector reduction not exact"
    sym, kw = RP.sym_of(sector, IB.translations(key))
    assert sym.get("ok"), "the lattice translations are not symmetries"
    colmaps = [list(map(int, c)) for c in sym["colmaps"]]
    pickle.dump({"sector": sector, "kw": kw, "colmaps": colmaps, "key": key, "basis": basis, "cycles": cycles,
                 "schedule": stag}, open(out, "wb"), protocol=4)
    print(f"{key} {stag} {basis} C = {cycles}: sector {sector.nrows} x {sector.ncols}, {len(colmaps)} symmetries, {out}",
          flush=True)


def column_keys(p):
    """For each column of a sector problem: its detectors' coordinates and its observables."""
    out = []
    for h, l in zip(p.h, p.l):
        dets = []
        while h:
            low = h & -h
            dets.append(p.row_meta[low.bit_length() - 1])
            h ^= low
        out.append((tuple(sorted(tuple(d) for d in dets)), l))
    return out


def load_sets(path):
    z = np.load(path)
    meta = json.loads(str(z["meta"]))
    return meta, {int(k[5:]): z[k].astype(np.int64) for k in z.files if k.startswith("sets_")}, \
        {int(k[6:]): z[k].astype(np.int64) for k in z.files if k.startswith("orbit_")}


def translate(small_pk, small_npz, big_pk, out, compare=None):
    a, b = pickle.load(open(small_pk, "rb")), pickle.load(open(big_pk, "rb"))
    assert (a["key"], a["basis"], a["schedule"]) == (b["key"], b["basis"], b["schedule"])
    meta, sets, _ = load_sets(small_npz)
    assert meta["cycles"] == a["cycles"] and meta["runs"][-1]["complete"]
    ka = column_keys(a["sector"])
    lookup = {k: j for j, k in enumerate(column_keys(b["sector"]))}
    res = {"key": b["key"], "basis": b["basis"], "cycles": b["cycles"], "schedule": b["schedule"],
           "translated_from_cycles": a["cycles"], "source_runs": meta["runs"],
           "runs": [{"K": meta["runs"][-1]["K"], "complete": True, "sets": {}, "orbits": {}}]}
    arrays, largest = {}, {}
    for w, R in sets.items():
        found = []
        for s in range(b["cycles"] - a["cycles"] + 1):
            cmap = np.array([lookup.get((tuple((x, y, t + s, kk) for x, y, t, kk in dets), l), -1) for dets, l in ka])
            C = cmap[R]
            found.append(C[(C >= 0).all(axis=1)])
        canon, sizes = canonical(np.concatenate(found), b["colmaps"])
        for G in canon[:: max(1, len(canon) // 2000)]:         # a sample: the construction guarantees the rest
            assert search.verify(b["sector"], G.tolist()), "a translate is not a logical fault set"
        arrays[f"sets_{w}"] = canon.astype(np.uint16)
        arrays[f"orbit_{w}"] = sizes.astype(np.int32)
        res["runs"][0]["sets"][w] = int(sizes.sum())
        res["runs"][0]["orbits"][w] = len(canon)
    print("translated:", json.dumps(res["runs"][0]), flush=True)
    if compare:
        _, cs, co = load_sets(compare)
        res["compared_with_enumeration"] = {}
        for w in sorted(set(cs) | set(sets)):
            x = {tuple(g) for g in arrays[f"sets_{w}"].tolist()} if f"sets_{w}" in arrays else set()
            y = {tuple(g) for g in cs[w].tolist()} if w in cs else set()
            res["compared_with_enumeration"][w] = {"same": x == y, "orbits_translated": len(x), "orbits_enumerated": len(y),
                                                   "only_translated": len(x - y), "only_enumerated": len(y - x)}
        print("compared:", json.dumps(res["compared_with_enumeration"]), flush=True)
    np.savez_compressed(out, meta=json.dumps(res), **arrays)


def canonical(reps, colmaps):
    """The sets reps (one weight) reduced to one per orbit of the group given by colmaps (without the identity): the
    lexicographically smallest image of each, without repeats, and the orbit sizes.  The search keeps at least one set
    per orbit, not exactly one."""
    maps = np.vstack([np.arange(len(colmaps[0]), dtype=np.int32)[None, :], np.array(colmaps, dtype=np.int32)])
    w = len(reps[0])
    canon, sizes = [], []
    for lo in range(0, len(reps), 1 << 14):
        img = np.sort(maps[:, np.array(reps[lo:lo + (1 << 14)], dtype=np.int32)], axis=2)   # (group, sets, w)
        keep = np.ones(img.shape[:2], dtype=bool)
        for j in range(w):
            col = np.where(keep, img[:, :, j], np.iinfo(np.int32).max)
            keep &= col == col.min(axis=0)
        canon.append(img[keep.argmax(axis=0), np.arange(img.shape[1])])
        sizes.append(len(maps) // keep.sum(axis=0))
    canon, sizes = np.concatenate(canon), np.concatenate(sizes)
    canon, first = np.unique(canon, axis=0, return_index=True)
    return canon, sizes[first]


def run(inp, kmin, kmax, out, seconds, k_table=3):
    kmin, kmax, seconds, k_table = int(kmin), int(kmax), float(seconds), int(k_table)
    d = pickle.load(open(inp, "rb"))
    sector, kw, colmaps = d["sector"], d["kw"], d["colmaps"]
    print(d["key"], d["schedule"], d["basis"], "C =", d["cycles"], "sector", sector.nrows, "x", sector.ncols, flush=True)
    t0 = time.time()
    S = search.Searcher(sector, labelfree=True, **kw)
    table = search.Table(sector, k_table, labelfree=True)
    S.add_table(table, exact=True)
    print(f"table k = {k_table}: {time.time() - t0:.1f} s", flush=True)
    res = {k: d[k] for k in ("key", "basis", "cycles", "schedule")}
    res["runs"] = []
    for K in range(kmin, kmax + 1):
        t1 = time.time()
        r = S.search(K, enum_all=True, time_limit=seconds, sol_cap=2_000_000_000, exclusions=False)
        reps = sorted({tuple(sorted(s)) for s in r["solutions"]})
        by = {}
        for s in reps:
            by.setdefault(len(s), []).append(s)
        canon = {w: canonical(v, colmaps) for w, v in by.items()}
        info = {"K": K, "status": r["status"], "complete": bool(r["solutions_complete"]) and r["status"] == "exhausted",
                "threads": r["threads"], "seconds": round(time.time() - t1, 1), "raw": int(r["nsol_found"]),
                "orbits": {w: len(v[0]) for w, v in sorted(canon.items())},
                "sets": {w: int(v[1].sum()) for w, v in sorted(canon.items())}}
        res["runs"].append(info)
        print(json.dumps(info), flush=True)
        np.savez_compressed(out, meta=json.dumps(res), **{f"sets_{w}": v[0].astype(np.uint16) for w, v in canon.items()},
                            **{f"orbit_{w}": v[1].astype(np.int32) for w, v in canon.items()})
        if not info["complete"]:
            break
    table.free()
    print(f"done in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "export":
        export(*sys.argv[2:])
    elif sys.argv[1] == "translate":
        translate(*sys.argv[2:])
    else:
        run(*sys.argv[2:])
