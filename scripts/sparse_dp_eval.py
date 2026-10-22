"""Evaluation of the weight-truncated sparse Rank DP (cdist/sparse_dp.py) against the dense Rank DP (cdist/auto.py)
and the weight-bounded search (cdist/search.py) on one column order per instance.

For an instance of known distance d (or known upper bound u, then d = u is tested), a sparse configuration runs
  K = d - 1   for every observable: a full sweep that finds nothing; it proves the lower bound d,
  K = d       observable by observable until one gives a solution; its witness is checked,
and records the states kept at every cut (forward and backward tables), the peak, the time and the process's peak
memory.  The dense DP runs where 2^(cut rank) bytes fit, the search with the benchmark configuration (label-free
table of depth 2, pair exclusions, covering bound) from K = 1.  Every job runs in its own process (clean peak
memory) with one thread.

Instance tokens:
  color:D            6.6.6 color code of distance D, code capacity (the triangular code of dp_vs_search_local.py)
  lowwidth:NAME      a code of bench/export_lowwidth.py (color_cc_dD, concat_steane_LL, hypercube_LL)
  bb:KEY             bivariate bicycle code bb72, bb90, bb108 or gross (papers/bb6_depth7.py), code capacity
  wjh:FAMILY:D       memory-basis sector of the circuit of arXiv:2603.22532 (surface, superdense or midout, D = 3..11);
                     their circuit files are looked up in $WJH_CIRCUITS (default: papers/downloads/codedistance/
                     examples/stim_circuits)
All code-capacity problems are the Z-basis ones (X errors, Z checks), as in the benchmark.

Configurations (comma separated): sparse:MODE:BACKEND:H[:SPLIT] with MODE forward|mitm, BACKEND c|numpy, H 0|1
(the lookahead bound), SPLIT the forward weight a of mitm (default K // 2 + 1, "auto": sparse_dp.choose_split,
"schedule": a split per cut, sparse_dp.choose_schedule; the run at K = d then uses the split of the run at
K = d - 1 plus one, which keeps its backward sweep); dense; search.

usage: python scripts/sparse_dp_eval.py OUT.json TOKEN[,TOKEN...] [--configs C,C] [--search-seconds S]
           [--dense-bits B] [--max-states N] [--max-seconds S] [--upper TOKEN=U,...]
"""
import argparse
import json
import os
import resource
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "scripts"), os.path.join(ROOT, "bench")]

DEFAULT_CONFIGS = ("sparse:mitm:c:0:schedule,sparse:mitm:c:0:auto,sparse:mitm:c:1:auto,sparse:forward:c:1,"
                   "sparse:forward:c:0,dense,search")
WJH_FOLDERS = {"surface": "01_surfacecodes", "midout": "03_colorcodes_midout", "superdense": "04_colorcodes_superdense"}
# distances established by the benchmark (results/bench_wjh): surface and superdense d (superdense d11 open:
# 8..11), midout (d + 1) / 2
WJH_KNOWN = {"surface": lambda d: d, "superdense": lambda d: None if d == 11 else d, "midout": lambda d: (d + 1) // 2}
WJH_UPPER = {("superdense", 11): 11}
BB_DISTANCE = {"bb72": 6, "bb90": 10, "bb108": 10, "gross": 12}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def wjh_circuit(family, d):
    base = os.environ.get("WJH_CIRCUITS", os.path.join(ROOT, "papers", "downloads", "codedistance", "examples",
                                                         "stim_circuits"))
    folder = os.path.join(base, WJH_FOLDERS[family])
    for name in sorted(os.listdir(folder)):
        if ",d=%d," % d in name and "color_code_mpp" not in name:
            return os.path.join(folder, name)
    raise FileNotFoundError("no %s circuit of distance %d in %s" % (family, d, folder))


def build(token):
    """(problem, known distance or None, known upper bound or None, kind)."""
    import stabcode
    kind, _, rest = token.partition(":")
    if kind == "color":
        import dp_vs_search_local as dvs
        d = int(rest)
        hx, hz, n = dvs.color_code(d)
        return stabcode.css_distance_problem(hx, hz, n, "Z", name=token), d, d, "code"
    if kind == "lowwidth":
        import export_lowwidth as el
        import dp_vs_search_local as dvs
        if rest.startswith("color_cc_d"):
            d = int(rest[len("color_cc_d"):])
            hx, hz, n = dvs.color_code(d)
        elif rest.startswith("concat_steane_L"):
            L = int(rest[len("concat_steane_L"):])
            (hx, hz, n), d = el.concat_steane(L), 3 ** L
        elif rest.startswith("hypercube_L"):
            L = int(rest[len("hypercube_L"):])
            (hx, hz, n), d = el.hypercube(L), 2 ** L
        else:
            raise ValueError(token)
        return stabcode.css_distance_problem(hx, hz, n, "Z", name=token), d, d, "code"
    if kind == "bb":
        import bb6_depth7
        hx, hz, n = bb6_depth7.matrices(rest)
        d = BB_DISTANCE[rest]
        return stabcode.css_distance_problem(hx, hz, n, "Z", name=token), d, d, "code"
    if kind == "wjh":
        from cdist import problem
        family, d = rest.split(":")
        d = int(d)
        p = problem.sector_problem(problem.load_dem_problem(wjh_circuit(family, d), name=token), high=True)
        known = WJH_KNOWN[family](d)
        return p, known, known if known is not None else WJH_UPPER.get((family, d)), "circuit"
    raise ValueError("unknown instance token " + token)


def column_order(p, kind):
    """The pipeline's choice: a few greedy orders for codes, the given order or its reverse for circuits."""
    from cdist import auto
    return auto.best_order(p, seeds=2 if kind == "code" and p.ncols <= 2000 else 0)[0]


def check(p, cols, obs=None):
    s = lg = 0
    for j in cols:
        s ^= p.h[j]
        lg ^= p.l[j]
    return s == 0 and len(set(cols)) == len(cols) and (lg != 0 if obs is None else (lg >> obs) & 1 == 1)


# ---------------------------------------------------------------------------------------------- jobs
def job_info(token):
    """Order, width profile and the dense DP's work for the instance (cheap)."""
    from cdist import sparse_dp, trellis
    t = time.time()
    p, d, ub, kind = build(token)
    order = column_order(p, kind)
    tr = None
    for i in range(p.nobs):
        tr = sparse_dp.Trellis.for_query(p, i, order)
        if tr.feasible:
            break
    plan = trellis.build_plan(p.h, p.l, 1 << i, order, p.nrows)
    return {"token": token, "kind": kind, "columns": p.ncols, "rows": p.nrows, "observables": p.nobs,
            "distance_known": d, "upper_known": ub, "cut_rank": max(tr.width), "slots": tr.nslots,
            "width": tr.width, "dense_peak_bits": plan.peak_bits, "dense_work_per_query": plan.work(),
            "setup_seconds": round(time.time() - t, 2)}


def job_sparse(token, cfg, args):
    from cdist import sparse_dp
    parts = cfg.split(":")
    mode, backend, use_h = parts[1], parts[2], parts[3] == "1"
    split = (parts[4] if parts[4] in ("auto", "schedule") else int(parts[4])) if len(parts) > 4 else None
    t0 = time.time()
    p, d, ub, kind = build(token)
    order = column_order(p, kind)
    trs = [sparse_dp.Trellis.for_query(p, i, order) for i in range(p.nobs)]
    rec = {"config": cfg, "order_seconds": round(time.time() - t0, 2)}
    target = d if d is not None else ub
    deadline = time.monotonic() + args.max_seconds if args.max_seconds else None
    kw = dict(mode=mode, backend=backend, use_h=use_h, split=split, max_states=args.max_states, deadline=deadline,
              dense=args.dense_fraction if mode == "forward" else None, dense_max=1 << args.dense_bits,
              log=lambda msg: print(time.strftime("%H:%M:%S"), token, cfg, msg, file=sys.stderr, flush=True))
    t1 = time.time()
    used = {}                                                     # split of the K = target - 1 run, per observable
    try:
        lower = []                                                # K = target - 1, every observable
        big = None
        for i, tr in enumerate(trs):
            if not tr.feasible:
                continue
            r = sparse_dp.query(tr, target - 1, witness=True, lower=target - 1, **kw)
            used[i] = r.get("split_values")
            s = sparse_dp.summary(r)
            s["obs"] = i
            lower.append(s)
            tot = sum(r["forward_counts"]) + sum(r.get("backward_counts", []))
            if big is None or tot > big[0]:
                big = (tot, i, {k: r[k] for k in ("forward_counts", "backward_counts", "changed_counts") if k in r})
            if r["value"] is not None:                            # below the known distance: report it
                s["witness_ok"] = check(p, r["witness"], i)
                s["witness"] = r["witness"]
                break
        rec["lower_run"] = {"K": target - 1, "queries": lower, "seconds": round(time.time() - t1, 3),
                            "per_cut_obs": big[1] if big else None, "per_cut": big[2] if big else None}
        found = [q for q in lower if q["value"] is not None]
        if found:
            rec["result"] = {"distance": min(q["value"] for q in found), "status": "below the known value"}
        else:
            t2 = time.time()
            upper = []
            for i, tr in enumerate(trs):
                if not tr.feasible:
                    continue
                # the run at K = target stops at its first solution, so its cost is mostly the backward sweep:
                # with a chosen split, raise the split of the K = target - 1 run by one at every cut, which keeps
                # that run's backward caps (and cost)
                kw_up = dict(kw)
                if mode == "mitm" and split in ("auto", "schedule") and used.get(i) is not None:
                    kw_up["split"] = [x + 1 for x in used[i]]
                r = sparse_dp.query(tr, target, witness=True, lower=target, **kw_up)
                s = sparse_dp.summary(r)
                s["obs"] = i
                upper.append(s)
                if r["value"] is not None:
                    s["witness_ok"] = check(p, r["witness"], i)
                    s["witness"] = r["witness"]
                    break
            rec["upper_run"] = {"K": target, "queries": upper, "seconds": round(time.time() - t2, 3)}
            w = [q for q in upper if q["value"] is not None]
            rec["result"] = ({"distance": w[0]["value"], "witness_ok": w[0]["witness_ok"], "status": "exact"} if w
                             else {"lower_bound": target + 1, "status": "no solution <= %d" % target})
    except sparse_dp.BudgetExceeded as e:
        rec["result"] = {"status": "budget", "detail": str(e)}
        low = rec.get("lower_run")
        if low and low["queries"] and all(q["value"] is None for q in low["queries"]):
            rec["result"]["lower_bound"] = target                # the run at K = target - 1 was complete
    rec["seconds"] = round(time.time() - t1, 3)
    return rec


def job_dense(token, args):
    from cdist import auto
    p, d, ub, kind = build(token)
    order = column_order(p, kind)
    t = time.time()
    try:
        value, per = auto.dp_distance(p, order, max_table_bytes=1 << args.dense_bits)
    except MemoryError as e:
        return {"config": "dense", "result": {"status": "too wide", "detail": str(e)}}
    sec = time.time() - t
    out = {"config": "dense", "seconds": round(sec, 3), "result": {"distance": value, "status": "exact"}}
    if value is not None and auto.trellis.build_plan(p.h, p.l, 1 << per.index(value), order, p.nrows).work() <= 1 << 31:
        t = time.time()
        cols = auto.dp_witness(p, order, per.index(value), max_bytes=1 << 31)
        if cols is not None:
            out["result"]["witness_ok"] = check(p, cols)
            out["traceback_seconds"] = round(time.time() - t, 3)
    return out


def job_search(token, args):
    from cdist import search
    p, d, ub, kind = build(token)
    t0 = time.time()
    S = search.Searcher(p, labelfree=True)
    S.build_exclusions()
    tab = search.Table(p, 2, labelfree=True)
    S.add_table(tab, exact=True)
    runs, out = [], {"config": "search", "result": {"status": "timeout"}}
    deadline = time.time() + args.search_seconds
    try:
        for K in range(1, p.ncols + 1):
            left = deadline - time.time()
            if left <= 0:
                break
            r = S.search(K, time_limit=left, cover=True)
            runs.append({"K": K, "status": r["status"], "nodes": int(sum(r["nodes"])), "seconds": round(r["seconds"], 3)})
            if r["status"] == "exhausted" and r["best"] is None:
                out["result"]["lower_bound"] = K + 1
                continue
            if r["best"] is not None:
                sol = r["solutions"][0]
                out["result"] = {"distance": r["best"], "status": "exact", "witness_ok": check(p, sol)}
            break
    finally:
        tab.free()
    out.update(runs=runs, seconds=round(time.time() - t0, 3), threads=search.lib().gm_num_threads())
    return out


def worker(spec):
    args = argparse.Namespace(**spec["args"])
    token, cfg = spec["token"], spec["config"]
    if cfg == "info":
        rec = job_info(token)
    elif cfg == "dense":
        rec = job_dense(token, args)
    elif cfg == "search":
        rec = job_search(token, args)
    else:
        rec = job_sparse(token, cfg, args)
    rec["maxrss_gb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1e9 if sys.platform == "darwin"
                                                                                   else 1e6), 3)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("tokens")
    ap.add_argument("--configs", default=DEFAULT_CONFIGS)
    ap.add_argument("--search-seconds", type=float, default=600.0)
    ap.add_argument("--dense-bits", type=int, default=30)
    ap.add_argument("--dense-fraction", type=float, default=0.25)
    ap.add_argument("--max-states", type=int, default=400_000_000)
    ap.add_argument("--max-seconds", type=float, default=7200.0)
    ap.add_argument("--redo", default="", help="configs to rerun even if recorded")
    ap.add_argument("--job", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.job:
        print(json.dumps(worker(json.loads(a.job))))
        return
    res = json.load(open(a.out)) if os.path.exists(a.out) else {"instances": {}}
    redo = set(a.redo.split(",")) - {""}
    jargs = {k: getattr(a, k) for k in ("search_seconds", "dense_bits", "dense_fraction", "max_states", "max_seconds")}
    env = dict(os.environ, OMP_NUM_THREADS="1")
    for token in a.tokens.split(","):
        inst = res["instances"].setdefault(token, {"runs": {}})
        for cfg in ["info"] + a.configs.split(","):
            if cfg == "info" and "info" in inst:
                continue
            if cfg != "info" and cfg in inst["runs"] and cfg not in redo:
                continue
            spec = {"token": token, "config": cfg, "args": jargs}
            t = time.time()
            # the job's progress messages and errors go to this process's stderr
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "x", "x", "--job", json.dumps(spec)],
                               stdout=subprocess.PIPE, text=True, env=env)
            if r.returncode != 0:
                rec = {"config": cfg, "result": {"status": "error", "detail": "exit code %d" % r.returncode}}
            else:
                rec = json.loads(r.stdout.strip().splitlines()[-1])
            rec["wall_seconds"] = round(time.time() - t, 2)
            if cfg == "info":
                inst["info"] = rec
            else:
                inst["runs"][cfg] = rec
            brief = {k: v for k, v in rec.items() if k in ("result", "seconds", "maxrss_gb", "cut_rank", "columns")}
            log(token, cfg, json.dumps(brief)[:300])
            json.dump(res, open(a.out + ".tmp", "w"))
            os.replace(a.out + ".tmp", a.out)


if __name__ == "__main__":
    main()
