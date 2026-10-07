"""Node counts of the weight-bounded search with and without kernel dominance.

Usage: python phase4/bench_kernel.py bb288_r18_Z:collapsed 3 11,12,13 0,6,c:0,c2:0 [time_limit]
  args: problem spec, table size k, thresholds K, variants: a kernel-set weight limit
  (0 = off), optionally prefixed by "c<gate>:" for the covering bound (with dual
  ascent) evaluated at nodes with |residual| >= gate * R, or "s:" for the
  covering bound without the ascent
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, log, search  # noqa: E402


def main(spec, k, Ks, wlist, time_limit=0.0, load_factor=0.5, tag=""):
    k = int(k)
    load_factor = float(load_factor)
    Ks = [int(x) for x in Ks.split(",")]
    variants = wlist.split(",")
    wlist = sorted({int(v.split(":")[-1]) for v in variants})
    time_limit = float(time_limit)
    p, sym = load(spec)
    rank = sym["rank"] if sym.get("ok") else None
    anchors = sym["anchors"] if sym.get("ok") else None
    colmaps = sym.get("colmaps", [])
    S = search.Searcher(p, rank=rank, anchors=anchors)
    npairs = S.build_exclusions()
    t = time.time()
    tab = search.Table(p, k, load=load_factor)
    S.add_table(tab, exact=True)
    log(spec, f"rows={p.nrows} cols={p.ncols} obs={p.nobs} anchors={len(S.anchors)} pairs={npairs} "
        f"table k={k} {tab.entries} entries {time.time() - t:.1f}s threads={search.lib().gm_num_threads()}")
    res = {"spec": spec, "k": k, "rows": p.nrows, "cols": p.ncols, "threads": search.lib().gm_num_threads(),
           "table_entries": tab.entries, "kernel": {}, "runs": []}
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results",
                       "kernel_" + spec.replace(":", "_").replace("[", "").replace("]", "").replace(",", "-") +
                       (f"_{tag}" if tag else "") + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    kernels = {}
    for w in wlist:
        if w <= 0:
            continue
        t = time.time()
        # enumerate with the full column set as anchors (no symmetry needed for correctness;
        # with symmetry the orbits are expanded afterwards)
        sets, r = S.kernel_sets(w, colmaps=colmaps)
        by_w = {}
        for s in sets:
            by_w[len(s)] = by_w.get(len(s), 0) + 1
        kernels[w] = sets
        res["kernel"][w] = {"sets": len(sets), "by_weight": by_w, "seconds": round(time.time() - t, 2),
                            "enum_nodes": sum(r["nodes"])}
        log(f"kernel sets up to weight {w}: {len(sets)} {dict(sorted(by_w.items()))} ({time.time() - t:.1f}s)")
    for K in Ks:
        base = None
        for v in variants:
            # variant: [c<gate>:]<kernel weight>, e.g. "0", "c:0", "c1.5:0", "c2:6"
            cover = False
            if v.startswith("c") or v.startswith("s"):
                g, v2 = v[1:].split(":")
                cover = "simple" if v[0] == "s" else (float(g) if g else True)
            else:
                v2 = v
            w = int(v2)
            if w > 0:
                S.set_kernel(kernels[w])
            else:
                S.kernel = None
            r = S.search(K, time_limit=time_limit, cover=cover, enum_all=True)
            rec = {"K": K, "variant": v, "kernel_w": w, "cover": cover, "status": r["status"], "best": r["best"],
                   "nodes": sum(r["nodes"]), "nodes_by_depth": r["nodes"], "lookups": r["lookups"],
                   "cover_pruned": r["cover_pruned"], "ascent_pruned": r["ascent_pruned"],
                   "cover_calls": r["cover_calls"], "seconds": round(r["seconds"], 3)}
            if base is None:
                base = rec
            ratio = (base["nodes"] / rec["nodes"]) if base and rec["nodes"] else None
            tr = (base["seconds"] / rec["seconds"]) if base and rec["seconds"] else None
            rec["node_reduction"] = ratio
            rec["solutions"] = len(r["solutions"])
            rec["time_reduction"] = tr
            res["runs"].append(rec)
            with open(out, "w") as f:
                json.dump(res, f, indent=1)
            log(f"K={K} {v:>4}: {r['status']} best={r['best']} nodes={rec['nodes']:.4g} "
                f"lookups={r['lookups']:.4g} {r['seconds']:.2f}s"
                + (f"  x{ratio:.2f} nodes, x{tr:.2f} time" if ratio and tr else ""))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results",
                       "kernel_" + spec.replace(":", "_").replace("[", "").replace("]", "").replace(",", "-") +
                       (f"_{tag}" if tag else "") + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    log("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
