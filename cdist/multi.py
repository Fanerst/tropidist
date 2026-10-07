"""Distance search for problems with more than 64 logical observables.

The observables are split into groups of at most 64; a fault set is logical
iff it flips an observable of some group, so each threshold is searched once
per group.  A symmetry of the *whole* problem may still be used for
anchoring: a minimum solution of the whole problem, moved so that it contains
the anchor of its lowest column orbit, is also a minimum solution of the group
whose observable it flips.
"""
from __future__ import annotations

from . import search
from .problem import Problem, observable_groups


def distance(p: Problem, k_table=2, kmax=20, rank=None, anchors=None, time_limit=0.0, log=None,
             start=1, enum_all=False, on_run=None, table_load=0.5, cover=False, relaxed=None):
    """Iterative deepening over all observable groups.  Same result layout as
    search.distance; solutions are column indices of p.

    relaxed: optional list of (relaxed problem, table size k, relaxed syndrome
    of every column of p); the table of each relaxed problem is an admissible
    pruning test, as in search.distance."""
    groups = [p] if p.nobs <= 64 else observable_groups(p, 64)
    S, tabs = [], []
    n_excl = 0
    rgroups = []
    for rp, rk, img in (relaxed or []):
        rg = [rp] if rp.nobs <= 64 else observable_groups(rp, 64)
        assert len(rg) == len(groups) and all(x.ncols == rp.ncols for x in rg)
        rgroups.append((rg, rk, img))
    for gi, g in enumerate(groups):
        assert g.ncols == p.ncols and g.h == p.h, "group problem must keep the column set"
        s = search.Searcher(g, rank=rank, anchors=anchors)
        n_excl += s.build_exclusions()
        for rg, rk, img in rgroups:
            rt = search.Table(rg[gi], rk, seed=777 + gi, load=table_load)
            zh, zl = rt.hashes_for(img)
            s.add_table(rt, zh, zl)
            tabs.append(rt)
        t = search.Table(g, k_table, load=table_load)
        s.add_table(t, exact=True)
        S.append(s)
        tabs.append(t)
    if log:
        log(f"  {len(groups)} observable group(s); table k={k_table}: {[t.entries for t in tabs]} entries, "
            f"2^{tabs[-1].log2slots} slots each, wide={tabs[-1].wide}")
    out = {"k_table": k_table, "groups": len(groups), "table_entries": [t.entries for t in tabs],
           "exclusion_pairs": n_excl, "runs": [], "lower_bound": start, "distance": None, "solutions": []}
    for K in range(start, kmax + 1):
        rec = {"K": K, "status": "exhausted", "best": None, "nodes": 0, "lookups": 0, "false_hits": 0, "seconds": 0.0}
        sols = []
        for g, s in zip(groups, S):
            r = s.search(K, enum_all=enum_all, time_limit=time_limit, cover=cover)
            rec["nodes"] += sum(r["nodes"])
            rec["lookups"] += r["lookups"]
            rec["false_hits"] += r["false_hits"]
            rec["seconds"] += r["seconds"]
            for sol in r["solutions"]:
                assert search.verify(g, sol) and search.verify(p, sol)
                sols.append(sol)
            if r["status"] in ("timeout", "too_many_tasks"):
                rec["status"] = r["status"]
                break
            if r["best"] is not None:
                rec["best"] = r["best"] if rec["best"] is None else min(rec["best"], r["best"])
                if not enum_all:
                    rec["status"] = "found"
                    break
        out["runs"].append(rec)
        if log:
            log(f"  K={K}: {rec['status']} best={rec['best']} nodes={rec['nodes']} {rec['seconds']:.2f}s")
        if on_run:
            on_run(rec)
        if rec["best"] is not None:
            out["distance"] = rec["best"]
            out["lower_bound"] = rec["best"]
            out["solutions"] = sorted({s for s in sols if len(s) == rec["best"]})
            break
        if rec["status"] in ("timeout", "too_many_tasks"):
            break
        out["lower_bound"] = K + 1
    for t in tabs:
        t.free()
    return out
