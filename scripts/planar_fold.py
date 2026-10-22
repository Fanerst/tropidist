"""Circuit distance of an exported memory circuit through the time-fold relaxation (cdist.problem.fold_time).

Vine-code circuits alternate a forward and a reversed syndrome round.  The full time collapse
(cdist.problem.collapse_time) then combines hook errors of forward and reversed rounds as if they happened in the
same round, and its distance is far below the circuit distance (5 against 8 for the authors' s = 11 patch).
Folding with the schedule's period 2 (detectors of a check XOR-ed over the rounds of the same parity) keeps that
distinction and is still a relaxation: every undetected logical fault set of the circuit is one of the folded
problem, so its distance is a certified lower bound.

  1. lower bound: weight-bounded search (cdist.search) on the folded problem, thresholds 1, 2, ... up to the
     first solution or kmax;
  2. upper bound: a search at the same thresholds on the rounds-0..1 window of the circuit problem (a
     restriction: its solutions are fault sets of the circuit), each solution checked on the circuit problem;
  3. optionally (--dp-width) the cut rank of the folded problem for a greedy and a local-search order.

usage: python scripts/planar_fold.py <instance dir> [--period 2] [--kmax 12] [--out results/planar_dp/fold/<name>.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "bench"), os.path.join(ROOT, "papers")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import common  # noqa: E402
from cdist import problem, search  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instance")
    ap.add_argument("--period", type=int, default=2)
    ap.add_argument("--kmax", type=int, default=12)
    ap.add_argument("--k-table", type=int, default=2)
    ap.add_argument("--window", type=int, default=1, help="last round of the window searched for the upper bound")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    prob = common.load(a.instance, "sector")
    q = common.to_cdist(prob)
    name = prob.meta["name"]
    out = a.out or os.path.join(ROOT, "results", "planar_dp", "fold", "%s__fold%d.json" % (name, a.period))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    rec = dict(instance=name, period=a.period, kmax=a.kmax, k_table=a.k_table, threads=search.lib().gm_num_threads(),
               sector=dict(rows=q.nrows, cols=q.ncols, obs=q.nobs), paper=prob.meta.get("paper"),
               rounds=prob.meta.get("rounds"), basis=prob.meta.get("basis"))
    t0 = time.time()
    f = problem.fold_time(q, a.period)
    rec["fold"] = dict(rows=f.nrows, cols=f.ncols)
    runs = []
    r = search.distance(f, k_table=a.k_table, kmax=a.kmax, on_run=runs.append)
    rec["fold"].update(distance=r["distance"], lower_bound=r["lower_bound"], seconds=round(time.time() - t0, 2),
                       runs=[{k: v for k, v in x.items() if k in ("K", "status", "best", "seconds")} for x in runs])
    lb = r["lower_bound"]
    print("%s fold%d: %d x %d, distance %s, certified lower bound %d (%.1f s)" % (
        name, a.period, f.nrows, f.ncols, r["distance"], lb, rec["fold"]["seconds"]), flush=True)
    json.dump(rec, open(out, "w"), indent=1)
    # upper bound from the window of the first rounds, at thresholds from the lower bound up
    t1 = time.time()
    w = problem.window_problem(q, 0, a.window)
    runs = []
    rw = search.distance(w, k_table=a.k_table, kmax=a.kmax, start=lb, on_run=runs.append)
    witness = None
    if rw["distance"] is not None:
        cols = [w.col_meta[j] for j in rw["solutions"][0]]
        assert search.verify(q, cols), "window solution is not a fault set of the circuit"
        witness = sorted(cols)
    rec["window"] = dict(rounds=[0, a.window], rows=w.nrows, cols=w.ncols, distance=rw["distance"],
                         seconds=round(time.time() - t1, 2),
                         runs=[{k: v for k, v in x.items() if k in ("K", "status", "best", "seconds")} for x in runs])
    ub = len(witness) if witness else None
    rec.update(lower=lb, upper=ub, exact=ub is not None and ub == lb, witness_sector_columns=witness,
               seconds=round(time.time() - t0, 2))
    json.dump(rec, open(out, "w"), indent=1)
    print("%s: circuit distance %s (lower %d, upper %s from the rounds 0-%d window), %.1f s" % (
        name, lb if rec["exact"] else "open", lb, ub, a.window, rec["seconds"]), flush=True)


if __name__ == "__main__":
    main()
