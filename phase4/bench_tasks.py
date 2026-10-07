"""Effect of the task depth (parallel granularity) and of the bound variant.
Usage: python phase4/bench_tasks.py SPEC k K[,K..] depths [variants: 0,simple,ascent] [table load]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, log, search  # noqa: E402

spec, k, depths = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[4].split(",")]
Ks = [int(x) for x in sys.argv[3].split(",")]
variants = sys.argv[5].split(",") if len(sys.argv) > 5 else ["ascent"]
ld = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5
p, sym = load(spec)
S = search.Searcher(p, rank=sym["rank"], anchors=sym["anchors"])
S.build_exclusions()
S.add_table(search.Table(p, k, load=ld), exact=True)
log(spec, f"rows={p.nrows} cols={p.ncols} k={k} threads={search.lib().gm_num_threads()}")
for K in Ks:
    for v in variants:
        for td in depths:
            cover = {"0": False, "simple": "simple", "ascent": True}[v]
            r = S.search(K, task_depth=td, cover=cover, enum_all=True)
            log(f"K={K} {v:>6} task_depth={td}: {r['status']} best={r['best']} sols={len(r['solutions'])} tasks={r['tasks']} "
                f"nodes={sum(r['nodes']):.4g} calls={r['cover_calls']:.3g} pruned={r['cover_pruned']:.3g} "
                f"(ascent {r['ascent_pruned']:.3g}) {r['seconds']:.2f}s")
