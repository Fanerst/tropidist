"""Exact circuit distance of every valid depth-7 interleaved schedule of a weight-6
bivariate bicycle code (papers/bb6_depth7.py), e.g. the 936 schedules of the standard family
(X checks idle in the first layer, Z checks idle in the last) for the gross code.

Each schedule is run through papers/run_parallel.py in both bases, single-threaded workers.
Schedules that reach `recheck` or more are then re-run with all threads and a longer limit to
decide the next weight.

Usage: python papers/design_bb6_depth7.py key [family: ibm | all] [processes] [seconds per threshold] [recheck weight] [seconds per threshold in the re-run]
"""
import contextlib
import io
import json
import multiprocessing as mp
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import bb6_depth7 as B
import run_parallel

_CFG = None


def _init(cfg):
    global _CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    _CFG = cfg


def evaluate(key, sched, basis, rounds, time_limit, kmax):
    name = f"bb6d7_w{os.getpid()}"
    mod = types.ModuleType(name)
    mod.CODES = B.CODES
    mod.build = lambda size, b, r, p=0.001: B.build(size, b, r, p, schedule=B.to_dicts(*sched))
    mod.translations = B.translations
    mod.tag = lambda size: f"{size}"
    sys.modules[name] = mod
    out = os.path.join(ROOT, "results", "papers3", "bb6", "tmp", f"{name}_{key}_{basis}.json")
    with contextlib.redirect_stdout(io.StringIO()):
        run_parallel.main(name, key, basis, out, rounds, 3, kmax, time_limit, 1)
    r = json.load(open(out))
    for f in (out, os.path.join(ROOT, "circuits", "papers", f"{name}{key}_r{rounds}_{basis}.stim")):
        if os.path.exists(f):
            os.remove(f)
    return r.get("certified_lower_bound"), r.get("certified_upper_bound"), r["collapsed"].get("distance")


def _work(sched):
    key, tl, kmax = _CFG
    try:
        return sched, {b: evaluate(key, sched, b, 6, tl, kmax) for b in "ZX"}
    except Exception as e:
        return sched, {"error": repr(e)[:200]}


def name_of(sched):
    px, pz = sched
    labx = ["A1", "A2", "A3", "B1", "B2", "B3"]
    labz = ["B1", "B2", "B3", "A1", "A2", "A3"]          # Z: (L, j) = B_j^T, (R, i) = A_i^T
    x = ["idle"] * 7
    z = ["idle"] * 7
    for lab, t in zip(labx, px):
        x[t] = lab
    for lab, t in zip(labz, pz):
        z[t] = lab
    return {"X": x, "Z": z}


def main(key, family="ibm", procs=8, tl=900, recheck=11, tl2=7200):
    procs, tl, recheck, tl2 = int(procs), float(tl), int(recheck), float(tl2)
    d = B.CODES[key][2][2]
    scheds = B.all_valid()
    if family == "ibm":
        scheds = [s for s in scheds if 0 not in s[0] and 6 not in s[1]]
    os.makedirs(os.path.join(ROOT, "results", "papers3", "bb6", "tmp"), exist_ok=True)
    out = os.path.join(ROOT, "results", "papers3", "bb6", f"{key}_{family}.json")
    t0 = time.time()
    part = out + ".part"                       # checkpoint: a killed sweep resumes where it stopped
    rows = json.load(open(part))["rows"] if os.path.exists(part) else []
    if family == "all":                        # the standard family is a subset: reuse its exact results
        q = os.path.join(ROOT, "results", "papers3", "bb6", f"{key}_ibm.json")
        if os.path.exists(q):
            seen = {(tuple(r["px"]), tuple(r["pz"])) for r in rows}
            rows += [{k: r[k] for k in ("px", "pz", "Z", "X")} for r in json.load(open(q))["rows"]
                     if "error" not in r and (tuple(r["px"]), tuple(r["pz"])) not in seen]
    have = {(tuple(r["px"]), tuple(r["pz"])) for r in rows}
    todo = [s_ for s_ in scheds if s_ not in have]
    if rows:
        print(time.strftime("%H:%M:%S"), f"resuming: {len(rows)} schedules known, {len(todo)} to do", flush=True)
    with mp.Pool(procs, maxtasksperchild=8, initializer=_init, initargs=((key, tl, d),)) as pool:
        for i, (sched, res) in enumerate(pool.imap_unordered(_work, todo, chunksize=1)):
            rows.append({"px": list(sched[0]), "pz": list(sched[1]), **{b: list(v) if not isinstance(v, str) else v for b, v in res.items()}})
            if (i + 1) % 50 == 0:
                print(time.strftime("%H:%M:%S"), f"{len(rows)}/{len(scheds)} schedules, {time.time() - t0:.0f}s", flush=True)
                json.dump({"key": key, "family": family, "rows": rows}, open(part + ".tmp", "w"))
                os.replace(part + ".tmp", part)

    def summary():
        hist, open_ = {}, 0
        for r in rows:
            if "error" in r:
                open_ += 1
                continue
            if all(r[b][0] == r[b][1] for b in "ZX"):
                k = min(r["Z"][0], r["X"][0])
                hist[k] = hist.get(k, 0) + 1
            else:
                open_ += 1
        return hist, open_
    hist, open_ = summary()
    res = {"code": list(B.CODES[key][2]), "family": family, "schedules": len(scheds),
           "circuit_distance_histogram": {str(k): v for k, v in sorted(hist.items())}, "not_exact": open_,
           "standard_schedule": next((r for r in rows if B.to_dicts(tuple(r["px"]), tuple(r["pz"])) == (B.STANDARD["X"], B.STANDARD["Z"])), None),
           "seconds_sweep": round(time.time() - t0, 1), "rows": rows}
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"{key} {family}: {len(scheds)} schedules; exact circuit distance (min of bases): "
          f"{res['circuit_distance_histogram']}; not exact: {open_}; standard: {res['standard_schedule']}", flush=True)
    # re-run the best ones with all threads
    try:
        import ctypes
        ctypes.CDLL("libgomp.so.1").omp_set_num_threads(procs)
    except OSError:
        pass
    top = [r for r in rows if "error" not in r and min(r["Z"][0], r["X"][0]) >= recheck]
    res["rechecked"] = []
    for r in top:
        sched = (tuple(r["px"]), tuple(r["pz"]))
        rec = {"schedule": name_of(sched), "px": r["px"], "pz": r["pz"]}
        for b in "ZX":
            lb, ub, dc = evaluate(key, sched, b, 6, tl2, d)
            rec[b] = [lb, ub]
            rec["collapsed_" + b] = dc
        res["rechecked"].append(rec)
        json.dump(res, open(out, "w"), indent=1)
        print(time.strftime("%H:%M:%S"), rec, flush=True)
    res["seconds"] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), "done", res["seconds"], flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
