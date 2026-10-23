"""Where the pipeline's time goes with lookup tables of different depths.

Runs bench/adapters/ours_pipeline.py's Pipeline in this process on one instance variant, with a given table budget
(1 GiB: the depth before commit 7ef27aa; 8 GiB: since then, in the first tier; the pipeline builds tables up
front within its EAGER_TABLE_BYTES and deepens them within this budget), and logs every table it builds
(problem width, depth asked and used, bytes, build time) and every search level (stage, K, depth of the main
table, seconds, nodes per depth, lookups, covering-bound calls and prunes).  The address-space limit is set
as the harness sets it, so the run sees what a benchmark run sees.

usage: python scripts/table_depth_probe.py INSTANCE_DIR VARIANT --budget-gb 8 [--config dp=1] [--seconds 600]
       [--mem-gb 16] [--out FILE.json]
"""
import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "bench" / "adapters"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instance")
    ap.add_argument("variant")
    ap.add_argument("--budget-gb", type=float, required=True, help="bytes allowed for live lookup tables")
    ap.add_argument("--config", default="dp=1", help="pipeline config, key=value[,key=value]")
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--mem-gb", type=float, default=16, help="address-space limit, as the harness sets it (0: none)")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.mem_gb > 0:
        lim = int(a.mem_gb * 2 ** 30)
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))

    import common
    import ours_pipeline as OP
    from cdist import search

    values = dict(kv.split("=", 1) for kv in a.config.split(",") if kv)
    cfg = OP.configuration(values)
    OP.TABLE_BUDGET = int(a.budget_gb * 2 ** 30)
    log = {"instance": a.instance, "variant": a.variant, "budget_gb": a.budget_gb, "config": a.config,
           "threads": search.lib().gm_num_threads(), "tables": [], "levels": []}
    stage = {"name": None}
    t0 = time.monotonic()

    orig_table = OP.Pipeline.table
    def table(self, p, k, seed=12345, **kw):
        t = time.monotonic()
        tab = orig_table(self, p, k, seed, **kw)
        if tab is not None:
            log["tables"].append({"stage": stage["name"], "cols": p.ncols, "k_asked": k, "k": tab.k,
                                  "bytes": tab._pipeline_bytes, "entries": int(tab.entries),
                                  "build_seconds": round(tab.build_seconds, 3),
                                  "seconds": round(time.monotonic() - t, 3), "at": round(t - t0, 3),
                                  "deepened": bool(kw.get("exact"))})
        return tab
    OP.Pipeline.table = table

    orig_distance = OP.Pipeline.distance
    def distance(self, p, st, k, *args, **kw):
        prev, stage["name"] = stage["name"], st
        try:
            return orig_distance(self, p, st, k, *args, **kw)
        finally:
            stage["name"] = prev
    OP.Pipeline.distance = distance

    orig_sector = OP.Pipeline.sector_search
    def sector_search(self, coll):
        prev, stage["name"] = stage["name"], "sector (relaxed table)"
        try:
            return orig_sector(self, coll)
        finally:
            stage["name"] = prev
    OP.Pipeline.sector_search = sector_search

    orig_search = search.Searcher.search
    def searched(self, K, *args, **kw):
        r = orig_search(self, K, *args, **kw)
        main = self.tables[self.main][0]
        log["levels"].append({"stage": stage["name"], "cols": self.p.ncols, "K": K, "k": main.k,
                              "trial": kw.get("anchors") is not None,
                              "relaxed": [t[0].k for i, t in enumerate(self.tables) if i != self.main],
                              "status": r["status"], "seconds": round(r["seconds"], 3), "nodes": r["nodes"],
                              "lookups": r["lookups"], "cover_calls": r["cover_calls"],
                              "cover_pruned": r["cover_pruned"], "hits": r["hits"], "false_hits": r["false_hits"]})
        return r
    search.Searcher.search = searched

    prob = common.load(a.instance, a.variant)
    tr = common.Trace()
    tr.t0 = time.monotonic()
    tr.lb(1)
    deadline = time.monotonic() + a.seconds
    pipe = OP.Pipeline(prob, cfg, tr, deadline, lambda trace, wit, notes: None)
    status = "bounds"
    try:
        pipe.run()
        status = "exact" if tr.upper is not None and tr.lower == tr.upper else "bounds"
    except OP.Deadline as exc:
        status = "timeout"
        log["stop_reason"] = str(exc)
    except (OP.ResourceLimit, MemoryError) as exc:
        status = "resource"
        log["stop_reason"] = str(exc) or "memory allocation failed"
    finally:
        pipe.close()
    log.update(status=status, seconds=round(time.monotonic() - t0, 3), lower=tr.lower, upper=tr.upper,
               notes={k: v for k, v in pipe.notes.items() if k in ("dp", "mode", "table_k_reduced", "sparse")},
               deepen={st: v["deepen"] for st, v in pipe.notes.get("stages", {}).items() if v.get("deepen")})
    text = json.dumps(log, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(json.dumps({k: log[k] for k in ("instance", "variant", "budget_gb", "status", "seconds", "lower", "upper")}))


if __name__ == "__main__":
    main()
