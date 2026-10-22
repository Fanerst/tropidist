"""One threshold K of the sparse Rank DP (meet in the middle, C tables, no lookahead) on one instance of
scripts/sparse_dp_eval.py, with a given split, saving the full record (per-cut state counts included).  With
--stop-at-K the sweep stops at the first solution of weight K (for a witness when the distance is known to be at
least K).  Used for the superdense d11 circuit (results/sparse_dp/README.md).

usage: python scripts/sparse_dp_query.py OUT.json TOKEN K SPLIT [--stop-at-K] [--max-states N]
       SPLIT: an integer, auto or schedule (cdist.sparse_dp.query), or schedule+1: the schedule chosen for K - 1
       raised by one at every cut (the backward sweep of the run at K - 1, for a witness run)
"""
import argparse
import json
import os
import resource
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "scripts"), os.path.join(ROOT, "bench")]
import sparse_dp_eval as ev
from cdist import sparse_dp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("token")
    ap.add_argument("K", type=int)
    ap.add_argument("split")
    ap.add_argument("--stop-at-K", action="store_true")
    ap.add_argument("--max-states", type=int, default=3_000_000_000)
    a = ap.parse_args()
    p, d, ub, kind = ev.build(a.token)
    order = ev.column_order(p, kind)
    tr = sparse_dp.Trellis.for_query(p, 0, order)
    t = time.time()
    if a.split == "schedule+1":
        split = [x + 1 for x in sparse_dp.choose_schedule(tr, a.K - 1, "c")[0]]
    else:
        split = a.split if a.split in ("auto", "schedule") else int(a.split)
    r = sparse_dp.query(tr, a.K, mode="mitm", split=split, use_h=False, witness=True,
                        lower=a.K if a.stop_at_K else 0, backend="c", max_states=a.max_states,
                        log=lambda m: print(time.strftime("%H:%M:%S"), m, file=sys.stderr, flush=True))
    rec = {k: v for k, v in r.items()}
    rec.update(token=a.token, columns=p.ncols, width=tr.width, wall_seconds=round(time.time() - t, 1),
               witness_ok=r["witness"] is not None and ev.check(p, r["witness"]),
               maxrss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 3))
    json.dump(rec, open(a.out, "w"))
    print(json.dumps({k: rec[k] for k in ("K", "value", "witness_ok", "seconds", "split", "peak_states",
                                          "maxrss_gb") if k in rec}))


if __name__ == "__main__":
    main()
