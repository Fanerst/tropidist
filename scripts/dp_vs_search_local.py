"""Quick test of the two exact evaluators on geometrically local codes: dense tropical Rank DP (linear
decomposition) against the weight-bounded search, on rotated surface codes under code-capacity noise.

The DP's cost is set by the cut rank of the column order (about d for a row-by-row sweep); the search's by the
distance and by how well the covering bound prunes (a partial string has only two unsatisfied checks, so it
prunes little here).  For each d both are run on the same problem (one CSS sector: checks H_X, logical L_X,
i.e. the Z distance) with the same number of threads; the search uses the benchmark configuration (label-free
table of depth 2, pair exclusions, covering bound).

A token color:d is the triangular 6.6.6 color code of distance d (three checks per bulk qubit, so not solvable by
shortest paths, unlike the surface code under code-capacity noise).  Any other token that is not an integer names a code instance of the benchmark (e.g. code_bb144), searched in the
benchmark's sector, for the opposite regime (wide decompositions, small distance).  A search time of 0 runs the
DP only.

usage: python scripts/dp_vs_search_local.py out.json d|code_name[,...] [search seconds per threshold] [dp max bits]
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "bench")]
import stabcode
from cdist import kernel, ordering, search, trellis


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def rotated_surface(d):
    """Rotated surface code: qubit (i, j) -> i*d + j; plaquette (a, b) has corners (a..a+1, b..b+1).
    Bulk plaquettes alternate X/Z; weight-2 X checks on the top and bottom edges, Z checks on the left and right."""
    xs, zs = [], []
    for a in range(-1, d):
        for b in range(-1, d):
            cells = [(i, j) for i in (a, a + 1) for j in (b, b + 1) if 0 <= i < d and 0 <= j < d]
            typ = "X" if (a + b) % 2 == 0 else "Z"
            if len(cells) == 2:
                if typ == "X" and a not in (-1, d - 1):
                    continue
                if typ == "Z" and b not in (-1, d - 1):
                    continue
            elif len(cells) != 4:
                continue
            (xs if typ == "X" else zs).append(sum(1 << (i * d + j) for i, j in cells))
    return xs, zs, d * d


def color_code(d):
    """Triangular 6.6.6 color code of distance d, read off Stim's color_code:memory_xyz circuit: the data qubits are
    those of the final measurement, and each measure qubit's two-qubit-gate partners are one plaquette.  The code is
    self-dual (H_X = H_Z = the plaquettes)."""
    import stim
    flat = stim.Circuit.generated("color_code:memory_xyz", distance=d, rounds=2).flattened()
    final = [inst for inst in flat if inst.name in ("M", "MX", "MY", "MZ")][-1]
    data = sorted({t.value for t in final.targets_copy()})
    dset = set(data)
    plaq = {}
    for inst in flat:
        if stim.gate_data(inst.name).is_two_qubit_gate:
            ts = [t.value for t in inst.targets_copy()]
            for a, b in zip(ts[::2], ts[1::2]):
                if (a in dset) != (b in dset):
                    m, q = (b, a) if a in dset else (a, b)
                    plaq.setdefault(m, set()).add(q)
    idx = {q: i for i, q in enumerate(data)}
    rows = sorted({sum(1 << idx[q] for q in s_) for s_ in plaq.values()})
    return rows, list(rows), len(data)


def dp_order(p):
    """Best cut-rank profile among the row-major order, its reverse and a few greedy orders."""
    cands = [list(range(p.ncols)), list(reversed(range(p.ncols)))]
    cands += [ordering.greedy_order(p.h, p.nrows, seed=s, noise=0.5 if s else 0.0) for s in range(4)]
    best = None
    for o in cands:
        cost = ordering.profile_cost(trellis.cut_profile(p.h, o))
        if best is None or cost < best[0]:
            best = (cost, o)
    return best[1], best[0]


def run_dp(p, max_bits):
    t = time.time()
    order, cost = dp_order(p)
    rec = {"cut_rank": int(cost[0]), "order_seconds": round(time.time() - t, 2)}
    if cost[0] > max_bits:
        rec["status"] = f"skipped (cut rank {cost[0]} > {max_bits})"
        return rec
    t = time.time()
    vals = []
    for i in range(p.nobs):
        plan = trellis.build_plan(p.h, p.l, 1 << i, order, p.nrows)
        v, st = kernel.run_plan(plan)
        vals.append(v)
        rec["peak_bits"] = max(rec.get("peak_bits", 0), plan.peak_bits)
        rec["threads"] = st.get("threads")
    rec.update({"distance": min(v for v in vals if v is not None), "seconds": round(time.time() - t, 2),
                "status": "exact"})
    return rec


def run_search(p, seconds):
    t0 = time.time()
    S = search.Searcher(p, labelfree=True)
    S.build_exclusions()
    tab = search.Table(p, 2, labelfree=True)
    S.add_table(tab, exact=True)
    rec = {"runs": [], "status": "timeout", "lower_bound": 1}
    try:
        for K in range(1, p.ncols + 1):
            r = S.search(K, time_limit=seconds, cover=True)
            rec["runs"].append({"K": K, "status": r["status"], "nodes": int(sum(r["nodes"])),
                                "seconds": round(r["seconds"], 2)})
            if r["status"] == "exhausted" and r["best"] is None:
                rec["lower_bound"] = K + 1
                continue
            if r["best"] is not None:
                rec.update({"distance": r["best"], "status": "exact", "lower_bound": r["best"]})
            break
    finally:
        tab.free()
    rec["seconds"] = round(time.time() - t0, 2)
    rec["threads"] = search.lib().gm_num_threads()
    return rec


def main(out, ds, seconds=600, max_bits=33):
    seconds, max_bits = float(seconds), int(max_bits)
    res = json.load(open(out)) if os.path.exists(out) else {"family": "rotated surface code, code capacity",
                                                            "sector": "checks H_X, logical L_X", "codes": {}}
    for d in ds.split(","):
        if d in res["codes"]:
            continue
        if d.startswith("color:"):
            dd = int(d.split(":")[1])
            hx, hz, n = color_code(dd)
            nn, k = stabcode.css_parameters(hx, hz, n)
            assert k == 1 and n == (3 * dd * dd + 1) // 4, (k, n)
            p = stabcode.css_distance_problem(hx, hz, n, "X", name=f"color_d{dd}")
        elif d.isdigit():
            dd = int(d)
            hx, hz, n = rotated_surface(dd)
            nn, k = stabcode.css_parameters(hx, hz, n)
            assert k == 1 and len(hx) == len(hz) == (dd * dd - 1) // 2, (k, len(hx), len(hz))
            p = stabcode.css_distance_problem(hx, hz, n, "X", name=f"surface_d{dd}")
        else:
            import instances
            spec = instances.INSTANCES[d]
            hx, hz, n, _ = instances._code(spec)
            nn, k = stabcode.css_parameters(hx, hz, n)
            p = stabcode.css_distance_problem(hx, hz, n, spec["basis"], name=d)
        rec = {"n": n, "k": k, "rows": p.nrows, "columns": p.ncols}
        rec["dp"] = run_dp(p, max_bits)
        log(f"{d}: DP: {rec['dp']}")
        if seconds > 0:
            rec["search"] = run_search(p, seconds)
            log(f"{d}: search: { {k: v for k, v in rec['search'].items() if k != 'runs'} } "
                f"last thresholds {rec['search']['runs'][-2:]}")
        res["codes"][d] = rec
        json.dump(res, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
