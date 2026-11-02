"""Rerun the enumerations of minimum collapsed solutions behind lower bounds raised by failed lifting.

papers/run_parallel.py raises the lower bound to d_coll + 1 when no minimum solution of the time-collapsed problem
lifts to the circuit.  Before the kernel fix of 30 October 2026 (commit c4820c8e) the enumeration kept at most
100,000 records (sol_cap) and did not say whether it had dropped any; since completion records a solution once per
search path that reaches it, a full buffer could have hidden minimum solutions.  For each such record this script
rebuilds the circuit exactly as the runner did (same paper module, schedule, rounds, noise, symmetries, table depth
and covering setting), repeats the enumeration with the fixed kernel and reports how many records it produces: the
original list was complete iff this count is at most 100,000.  It checks that the rebuilt collapsed problem and the
number of orbits of minimum solutions agree with the record.  If an enumeration would have overflowed, it collects the
complete list and lifts every orbit as the runner does, which decides whether the record's bound stands.

  python scripts/rerun_lift_enumerations.py jobs JOBS.json            # collect the jobs from the local records
  python scripts/rerun_lift_enumerations.py run JOBS.json OUT_DIR [processes] [threads per job] [index ...]
  python scripts/rerun_lift_enumerations.py summary OUT_DIR

One JSON per job in OUT_DIR (a finished job is skipped on a rerun); the circuits are written to OUT_DIR/circuits.
"""
import glob
import json
import os
import re
import sys
import time
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers")]
SOL_CAP = 100000          # the runner's buffer (cdist.search.Searcher.search default)


def collect_jobs(out):
    jobs = []
    for f in sorted(glob.glob(os.path.join(ROOT, "results", "**", "*.json"), recursive=True)):
        try:
            if os.path.getsize(f) > 80_000_000:
                continue
            r = json.load(open(f))
        except (OSError, ValueError):
            continue
        c = r.get("collapsed") if isinstance(r, dict) else None
        if not isinstance(c, dict) or "n_min_solution_orbits" not in c or c.get("orbits_lifting_slack0") != 0:
            continue
        if c.get("distance") is None or r.get("certified_lower_bound") != c["distance"] + 1:
            continue          # a later search raised the bound further and would have met any missed solution
        jobs.append({"file": os.path.relpath(f, ROOT), "paper": r["paper"], "circuit": r["circuit"],
                     "basis": r["basis"], "rounds": r["rounds"], "noise": r.get("noise", "full"),
                     "cover": bool(r.get("cover")), "k_table": c["k_table"], "d_coll": c["distance"],
                     "orbits": c.get("orbits"), "min_solution_orbits": c["n_min_solution_orbits"],
                     "collapsed_rows": c["rows"], "collapsed_columns": c["columns"],
                     "sector_columns": r["model"]["sector_columns"],
                     "star_schedule_variant": r.get("star_schedule_variant"), "star_schedule": r.get("star_schedule"),
                     "lower_bound": r["certified_lower_bound"], "upper_bound": r.get("certified_upper_bound")})
    json.dump(jobs, open(out, "w"), indent=1)
    print(len(jobs), "jobs ->", out)


def resolve(job):
    """The paper module (or the facade of the script that made the record) and the key of mod.CODES."""
    paper, rounds, basis, noise = job["paper"], job["rounds"], job["basis"], job["noise"]
    name = os.path.basename(job["circuit"])[:-len(".stim")]
    if noise != "full":
        name = name[:-len("_" + noise)]
    tag = name[len(paper):-len(f"_r{rounds}_{basis}")]
    m = re.fullmatch(r"shift_num(\d+)_a(\d{3})_b(\d{3})_w\d+", paper)
    if m:                                       # papers/shift_numberings.py: variant()
        import shift
        numbering = (tuple(map(int, m[2])), tuple(map(int, m[3])))
        mod = SimpleNamespace(CODES=shift.CODES, tag=shift.tag, translations=shift.translations,
                              build=lambda k, b, r, p=0.001, noise="full": shift.build(k, b, r, p=p, noise=noise,
                                                                                         numbering=numbering))
    elif paper == "star_schedule":              # papers/star_run.py
        import star
        order = job["star_schedule"]            # {"X": [...], "Z": [...]}, as stored by star_run.py
        mod = SimpleNamespace(CODES=star.CODES, translations=star.translations,
                              tag=lambda size: f"{size}_{job['star_schedule_variant']}",
                              build=lambda size, b, r, p=0.001, noise="full": star.build(size, b, r, p=p, noise=noise,
                                                                                         schedule=order))
    elif paper == "starconv":                   # papers/star_table2_conventions.py
        import star
        import star_dictionary
        sigma = tag.split("_s")[1]
        sched = star_dictionary.relabel(star.PAPER_SCHEDULE, tuple(map(int, sigma)))
        mod = SimpleNamespace(CODES=star.CODES, translations=star.translations, tag=lambda size: f"{size}_s{sigma}",
                              build=lambda size, b, r, p=0.001: star.build(size, b, r, p=p, schedule=sched))
    elif paper == "bb6cc":                      # papers/bb6_crosscheck.py, family "ibm"
        import bb6_depth7 as B
        key, label = tag.rsplit("_", 1)
        rows = json.load(open(os.path.join(ROOT, "results", "papers3", "bb6", f"{key}_ibm.json")))["rows"]
        rows = [r for r in rows if "error" not in r and r["Z"][0] == r["Z"][1] and r["X"][0] == r["X"][1]]
        top = max(min(r["Z"][0], r["X"][0]) for r in rows)
        best = next(r for r in rows if min(r["Z"][0], r["X"][0]) == top)
        std = next(s for s in B.all_valid() if B.to_dicts(*s) == (B.STANDARD["X"], B.STANDARD["Z"]))
        sched = (tuple(best["px"]), tuple(best["pz"])) if label == "best" else std
        mod = SimpleNamespace(CODES=B.CODES, translations=B.translations, tag=lambda k: f"{k}_{label}",
                              build=lambda k, b, r, p=0.001: B.build(k, b, r, p, schedule=B.to_dicts(*sched)))
    else:
        if paper == "ibm_bicycle":
            sched = tag.split("_", 1)[1]
            os.environ["IBM_SCHEDULE"] = "standard" if sched == "standard" else "/".join(
                ",".join(part) for part in sched[1:].split("_"))
        mod = __import__(paper)
        if paper == "hypsurf_pick":             # lazy CODES: the key "<base>@v<digits>" names the assignment
            base, digits = tag.rsplit("_v", 1)
            key = f"{base}@v{digits}"
            if mod.tag(key) == tag:
                return mod, key, name
    for key in mod.CODES:
        t = mod.tag(key) if hasattr(mod, "tag") else mod.CODES[key][2][0]
        if str(t) == tag:
            return mod, key, name
    raise KeyError(f"no key of {paper} has tag {tag}")


def run_job(i, job, out_dir):
    out = os.path.join(out_dir, f"job{i:03d}.json")
    if os.path.exists(out):
        return json.load(open(out))
    import run_parallel
    from cdist import lift, problem, search
    t0 = time.time()
    res = {"index": i, "file": job["file"], "paper": job["paper"], "record_lower_bound": job["lower_bound"],
           "record_upper_bound": job["upper_bound"], "d_coll": job["d_coll"], "threads": search.lib().gm_num_threads()}
    mod, key, name = resolve(job)
    res["key"] = str(key)
    noise = job["noise"]
    circ = mod.build(key, job["basis"], job["rounds"], noise=noise) if noise != "full" else \
        mod.build(key, job["basis"], job["rounds"])
    path = os.path.join(out_dir, "circuits", f"job{i:03d}_{name}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path, name)
    high = mod.sector_high(job["basis"]) if hasattr(mod, "sector_high") else None
    sector = problem.sector_problem(full, high)
    coll = problem.collapse_time(sector)
    cperms = mod.translations(key) if hasattr(mod, "translations") else []
    ssym0, _ = run_parallel.sym_of(sector, cperms)
    sector_symmetric = (ssym0.get("n_symmetries_kept") if ssym0.get("ok") else None) == len(cperms)
    sym, kw = run_parallel.sym_of(coll, cperms)
    res["rebuilt"] = {"sector_columns": sector.ncols, "collapsed_rows": coll.nrows, "collapsed_columns": coll.ncols,
                      "orbits": len(sym["anchors"]) if sym.get("ok") else None}
    res["same_problem"] = (sector.ncols == job["sector_columns"] and coll.nrows == job["collapsed_rows"]
                           and coll.ncols == job["collapsed_columns"] and res["rebuilt"]["orbits"] == job["orbits"])
    run_parallel.COVER = job["cover"]
    d = job["d_coll"]
    r = run_parallel.dist(coll, k_table=job["k_table"], kmax=d, time_limit=0, enum_all=True, start=d, **kw)
    last = r["runs"][-1]
    res["enumeration"] = {x: last[x] for x in ("status", "best", "nsol_found", "nsol_recorded", "solutions_complete",
                                               "seconds")}
    colmaps = sym.get("colmaps", []) if sym.get("ok") else []
    if last["solutions_complete"]:
        sols = r["solutions"]
    else:   # the original buffer overflowed: the same call again with a buffer that holds every record
        plain = search.Searcher.search
        cap = last["nsol_found"] + 16
        search.Searcher.search = lambda self, K, **a: plain(self, K, **dict(a, sol_cap=cap))
        try:
            r2 = run_parallel.dist(coll, k_table=job["k_table"], kmax=d, time_limit=0, enum_all=True, start=d, **kw)
        finally:
            search.Searcher.search = plain
        assert r2["solutions_complete"], "the larger buffer still overflowed"
        sols = r2["solutions"]
        res["complete_rerun"] = {"nsol_found": r2["runs"][-1]["nsol_found"], "distinct": len(sols)}
    reps = lift.orbit_representatives(sols, colmaps) if sector_symmetric else \
        [(x, 1) for x in sorted(lift.expand_orbits(sols, colmaps))]
    res["min_solution_orbits"] = len(reps)
    res["record_min_solution_orbits"] = job["min_solution_orbits"]
    res["original_list_complete"] = last["nsol_found"] <= SOL_CAP
    if not res["original_list_complete"]:     # decide the bound as the runner would have with the full list
        lifted = None
        for rep, _ in reps:
            w, cols = run_parallel.lift_multi(sector, coll, rep, 0, 0, start=d)
            if w not in (None, "timeout"):
                lifted = w
                break
        res["lifting_with_complete_list"] = {"lifts": lifted is not None, "weight": lifted}
        res["bound_stands"] = lifted is None
    else:
        res["bound_stands"] = True
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out + ".tmp", "w"), indent=1)
    os.replace(out + ".tmp", out)
    return res


def _init(threads):
    os.environ["OMP_NUM_THREADS"] = str(threads)


def _call(args):
    i, job, out_dir = args
    try:
        r = run_job(i, job, out_dir)
        return i, r.get("bound_stands"), r.get("enumeration", {}).get("nsol_found"), r.get("same_problem"), None
    except Exception as e:      # recorded, so that one broken job does not stop the others
        err = {"index": i, "file": job["file"], "error": f"{type(e).__name__}: {e}"}
        json.dump(err, open(os.path.join(out_dir, f"job{i:03d}.error.json"), "w"), indent=1)
        return i, None, None, None, err["error"]


def run(jobs_path, out_dir, processes=8, threads=1, only=()):
    import concurrent.futures
    import multiprocessing
    jobs = json.load(open(jobs_path))
    os.makedirs(out_dir, exist_ok=True)
    todo = [(i, j, out_dir) for i, j in enumerate(jobs) if not only or i in only]
    todo.sort(key=lambda t: t[1]["collapsed_columns"] * t[1]["d_coll"])     # cheap ones first
    ctx = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(int(processes), mp_context=ctx, initializer=_init,
                                                initargs=(int(threads),)) as ex:
        for i, stands, found, same, err in ex.map(_call, todo):
            print(time.strftime("%H:%M:%S"), f"job {i}", f"error {err}" if err else
                  f"found {found} same_problem {same} bound_stands {stands}", flush=True)


def summary(out_dir):
    rs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(out_dir, "job*.json")))]
    done = [r for r in rs if "enumeration" in r]
    errs = [r for r in rs if "error" in r]
    print(f"finished {len(done)}, errors {len(errs)}")
    print("largest record counts:", sorted((r["enumeration"]["nsol_found"], r["file"]) for r in done)[-5:])
    for key in ("same_problem", "original_list_complete", "bound_stands"):
        print(key, sum(1 for r in done if r.get(key)), "of", len(done))
    print("orbit count differs from the record:",
          [r["file"] for r in done if r["min_solution_orbits"] != r["record_min_solution_orbits"]])
    for r in errs:
        print("ERROR", r["index"], r["file"], r["error"])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "jobs":
        collect_jobs(sys.argv[2])
    elif cmd == "run":
        run(sys.argv[2], sys.argv[3], *(sys.argv[4:6]), only=tuple(int(x) for x in sys.argv[6:]))
    elif cmd == "summary":
        summary(sys.argv[2])
