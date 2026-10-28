"""Certified circuit distance of the memory instruction of papers/ibm_bicycle.py (IBM's setting) for many depth-seven
schedules at once, both bases, one single-threaded worker per schedule; results are appended to a JSON-lines file
and the scan resumes where it stopped.

  schedules = "d11"        the 428 gross-code schedules whose six-cycle memory circuits have distance 11
                           (results/papers3/bb6/gross_all.json), and the standard schedule
              "all"        every valid depth-seven schedule (papers/bb6_depth7.py, 8,496)
              "standard"   the standard schedule only

Usage: python papers/ibm_bicycle_scan.py KEY SCHEDULES CYCLES OUT.jsonl [processes] [seconds per threshold] [kmax]
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
import ibm_bicycle as IB

_CFG = None


def _init(cfg):
    global _CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    _CFG = cfg


def evaluate(key, sched, basis, cycles, time_limit, kmax):
    import run_parallel
    name = f"ibmscan_w{os.getpid()}"
    mod = types.ModuleType(name)
    mod.CODES = IB.CODES
    mod.build = lambda size, b, r, p=1e-3: IB.build_instruction(size, b, r, p, B.to_dicts(*sched))
    mod.translations = B.translations
    mod.tag = lambda size: f"{size}"
    sys.modules[name] = mod
    out = os.path.join(ROOT, "results", "ibm", "tmp", f"{name}_{key}_{basis}.json")
    with contextlib.redirect_stdout(io.StringIO()):
        run_parallel.main(name, key, basis, out, cycles, 3, kmax, time_limit, 1)
    r = json.load(open(out))
    for f in (out, os.path.join(ROOT, "circuits", "papers", f"{name}{key}_r{cycles}_{basis}.stim")):
        if os.path.exists(f):
            os.remove(f)
    return [r.get("certified_lower_bound"), r.get("certified_upper_bound"), r["collapsed"].get("distance")]


def _work(sched):
    key, cycles, tl, kmax = _CFG
    t = time.time()
    try:
        res = {b: evaluate(key, sched, b, cycles, tl, kmax) for b in "ZX"}
    except Exception as e:                                    # recorded, so that the scan can go on
        res = {"error": repr(e)[:300]}
    res.update(px=list(sched[0]), pz=list(sched[1]), seconds=round(time.time() - t, 1))
    return res


def schedules(key, which):
    std = (tuple(B.STANDARD["X"][l] for l in [(s, a) for s in "LR" for a in range(3)]),
           tuple(B.STANDARD["Z"][l] for l in [(s, a) for s in "LR" for a in range(3)]))
    if which == "standard":
        return [std]
    if which == "all":
        return [std] + [s for s in B.all_valid() if s != std]
    if which == "d11":
        rows = json.load(open(os.path.join(ROOT, "results", "papers3", "bb6", f"{key}_all.json")))["rows"]
        best = [(tuple(r["px"]), tuple(r["pz"])) for r in rows if min(r["Z"][0], r["X"][0]) == 11]
        return [std] + best
    raise ValueError(which)


def main(key, which, cycles, out, procs=8, tl=600, kmax=24):
    cycles, procs, tl, kmax = int(cycles), int(procs), float(tl), int(kmax)
    todo = schedules(key, which)
    done = set()
    if os.path.exists(out):
        for line in open(out):
            r = json.loads(line)
            done.add((tuple(r["px"]), tuple(r["pz"])))
    todo = [s for s in todo if s not in done]
    print(time.strftime("%H:%M:%S"), f"{key} {which}: {len(todo)} schedules to evaluate ({len(done)} done)", flush=True)
    os.makedirs(os.path.join(ROOT, "results", "ibm", "tmp"), exist_ok=True)
    with mp.Pool(procs, initializer=_init, initargs=((key, cycles, tl, kmax),), maxtasksperchild=20) as pool, \
            open(out, "a") as f:
        for i, res in enumerate(pool.imap_unordered(_work, todo), 1):
            f.write(json.dumps(res) + "\n")
            f.flush()
            if i % 20 == 0 or i == len(todo):
                print(time.strftime("%H:%M:%S"), f"{i}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
