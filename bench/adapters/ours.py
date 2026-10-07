"""Adapter for this project's search, minimal form: the weight-bounded search of cdist on the
problem as given (any variant), with the stored symmetries.  It is also the reference example of
the adapter interface.  The full pipeline for circuit problems (collapsed relaxation, lifting,
windows) is added by bench/adapters/ours_pipeline.py.

config: k_table (default 2), cover (1), symmetry (1), kmax (truth-independent cap, default 40)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import common


def main():
    a = common.adapter_args(__doc__)
    os.environ["OMP_NUM_THREADS"] = str(a.threads)      # before the kernel is loaded
    from cdist import search, symmetry
    prob = common.load(a.instance, a.variant)
    tr = common.Trace()
    p = common.to_cdist(prob)
    kw = {}
    if int(a.cfg.get("symmetry", 1)) and prob.perms:
        sym = symmetry.from_row_perms(p, prob.perms)
        if sym.get("ok"):
            kw = {"rank": sym["rank"], "anchors": sym["anchors"]}
    tr.lb(1)

    def on_run(rec):
        if rec["status"] == "exhausted" and rec["best"] is None:
            tr.lb(rec["K"] + 1)
        elif rec["best"] is not None:
            tr.ub(rec["best"])
            tr.lb(rec["best"])

    # one threshold at a time, each with the time that is left of the whole-run limit
    S = search.Searcher(p, labelfree=True, **kw)
    S.build_exclusions()
    tab = search.Table(p, int(a.cfg.get("k_table", 2)), labelfree=True)
    S.add_table(tab, exact=True)
    r = {"distance": None, "solutions": []}
    try:
        for K in range(1, int(a.cfg.get("kmax", 40)) + 1):
            left = a.time_limit - tr.seconds()
            if left <= 0:
                break
            x = S.search(K, time_limit=left, cover=bool(int(a.cfg.get("cover", 1))))
            on_run(x)
            if x["status"] in ("timeout", "too_many_tasks"):
                break
            if x["best"] is not None:
                r = {"distance": x["best"], "solutions": sorted(s_ for s_ in x["solutions"] if len(s_) == x["best"])}
                break
    finally:
        tab.free()
    wit = list(r["solutions"][0]) if r["solutions"] else None
    status = "exact" if r["distance"] is not None else "timeout"
    common.save_result(a.out, prob, "ours_search", tr, status, a.threads, a.time_limit, witness=wit, config=a.cfg,
                       notes=f"symmetries used: {len(prob.perms) if kw else 0}")
    print(status, tr.lower, tr.upper, tr.seconds())


if __name__ == "__main__":
    main()
