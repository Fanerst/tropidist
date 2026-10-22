"""Bin's tree DP (cdist.tree_dp, general binary trees) against the trellis DP (cdist.trellis/kernel, one column
order) on the instances of scripts/dp_vs_search_local.py.  For each instance: the trellis with the best of a few
orders, and the tree DP on three trees built from the repository's own tools (no external decomposition search):
the caterpillar of the trellis order (the same decomposition), a balanced tree over that order, and for local codes
a geometric bisection tree (recursive median cuts of the qubit coordinates, longer side first).  Each tree is
profiled (largest table, largest join exponent J, total join work) and the cheapest is run.  Both DPs on one
thread.

usage: OMP_NUM_THREADS=1 python scripts/tree_vs_trellis.py out.json name[,name...] [max table bits] [max log2 work]
       names as in dp_vs_search_local.py: surface d as "25", color:d, or a benchmark code instance
"""
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "bench"), os.path.join(ROOT, "scripts")]
import stabcode
from cdist import kernel, rankwidth, trellis, tree_dp
import dp_vs_search_local as dvs


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def color_coords(d):
    import stim
    c = stim.Circuit.generated("color_code:memory_xyz", distance=d, rounds=2)
    flat = c.flattened()
    final = [inst for inst in flat if inst.name in ("M", "MX", "MY", "MZ")][-1]
    data = sorted({t.value for t in final.targets_copy()})
    xy = c.get_final_qubit_coordinates()
    return [tuple(xy[q][:2]) for q in data]


def instance(name):
    if name.startswith("color:"):
        d = int(name.split(":")[1])
        hx, hz, n = dvs.color_code(d)
        return stabcode.css_distance_problem(hx, hz, n, "X", name=name), color_coords(d)
    if name.isdigit():
        d = int(name)
        hx, hz, n = dvs.rotated_surface(d)
        return stabcode.css_distance_problem(hx, hz, n, "X", name=name), [divmod(q, d) for q in range(n)]
    import instances
    spec = instances.INSTANCES[name]
    hx, hz, n, _ = instances._code(spec)
    return stabcode.css_distance_problem(hx, hz, n, spec["basis"], name=name), None


def bisection_tree(cols, coords):
    """Recursive median split of the columns by coordinates, along the longer side."""
    def build(ids):
        if len(ids) == 1:
            return ids[0]
        xs = [coords[i][0] for i in ids]
        ys = [coords[i][1] for i in ids]
        axis = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
        ids = sorted(ids, key=lambda i: (coords[i][axis], coords[i][1 - axis]))
        mid = len(ids) // 2
        return (build(ids[:mid]), build(ids[mid:]))
    return build(list(range(len(cols))))


def main(out, names, max_bits=30, max_log_work=40):
    max_bits, max_log_work = int(max_bits), float(max_log_work)
    res = json.load(open(out)) if os.path.exists(out) else {}
    for name in names.split(","):
        if name in res:
            continue
        p, coords = instance(name)
        rec = {"n": p.ncols, "rows": p.nrows, "observables": p.nobs}
        order, cost = dvs.dp_order(p)
        rec["trellis"] = {"width": int(cost[0])}
        if cost[0] <= max_bits:
            t = time.time()
            vals = []
            for i in range(p.nobs):
                plan = trellis.build_plan(p.h, p.l, 1 << i, order, p.nrows)
                vals.append(kernel.run_plan(plan)[0])
                rec["trellis"]["peak_bits"] = max(rec["trellis"].get("peak_bits", 0), plan.peak_bits)
            rec["trellis"].update(distance=min(v for v in vals if v is not None), seconds=round(time.time() - t, 2))
        log(name, "trellis", rec["trellis"])
        # trees, profiled on the augmented matrix of the first observable (as the DP sees it)
        aug = [h | ((bin(l & 1).count("1") & 1) << p.nrows) for h, l in zip(p.h, p.l)]
        trees = {"caterpillar": rankwidth.caterpillar_tree(order), "balanced": rankwidth.balanced_tree(order)}
        if coords:
            trees["bisection"] = bisection_tree(p.h, coords)
        prof = {}
        for tname, tree in trees.items():
            t = time.time()
            pr = rankwidth.tree_profile(aug, tree)
            prof[tname] = {"width": pr["width"], "max_join": pr["max_join_dimension"],
                           "log2_total_work": round(math.log2(pr["total_join_work"]), 2),
                           "profile_seconds": round(time.time() - t, 2)}
        rec["trees"] = prof
        log(name, "trees", prof)
        best = min(prof, key=lambda k: (prof[k]["log2_total_work"], prof[k]["width"]))
        rec["tree_run"] = {"tree": best}
        if prof[best]["log2_total_work"] <= max_log_work and prof[best]["width"] <= max_bits:
            t = time.time()
            vals = []
            try:
                for i in range(p.nobs):
                    v, info = tree_dp.tree_min_distance_for_mask(
                        p.h, p.l, 1 << i, trees[best], max_compile_bytes=8 << 30, max_compile_seconds=3600,
                        max_memory_bytes=32 << 30, max_join_work=1 << int(max_log_work))
                    vals.append(v)
                rec["tree_run"].update(distance=min(v for v in vals if v is not None),
                                       seconds=round(time.time() - t, 2))
            except Exception as exc:          # resource refusal or a solver error: recorded, not hidden
                rec["tree_run"]["error"] = f"{type(exc).__name__}: {exc}"
        else:
            rec["tree_run"]["skipped"] = "beyond the work/table limits"
        log(name, "tree run", rec["tree_run"])
        res[name] = rec
        json.dump(res, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
