"""Exact scan of the two-gross schedule classes (classes.json): for each class, the benchmark pipeline (dp=2) on the one-cycle
instruction (IBM's setting) of its first problem up to weight KMAX, then on the second problem only below the first's value, which
is enough for the distance of the schedule.  Each problem runs on the image under slot reversal T whose window t1 is the larger
one, because the pipeline looks for an upper bound in window t1 only (T carries t1 to t2 and leaves the distance unchanged).
Classes already settled in OUT.jsonl are skipped.  A class goes to this server if its index mod M equals R; with DEEP_ONLY in the
environment (a JSON file of class indices) only those classes run; the file is read again before each class, so a class taken out of it
while the queue runs is skipped (to hand it to another server).  With DEEP_KMIN in the environment the final search starts at that
weight, for classes whose lighter thresholds are excluded by an earlier record (OUT.jsonl must then be a separate file).  With DEEP_SECOND
in the environment only the second problem of each class runs; tally_scan.py reads the results per problem.

Usage: python deep_queue.py OUT.jsonl CLASSES.json THREADS JOBS KMAX SECONDS R M
"""
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.environ.get("CD_ROOT", os.path.expanduser("~/claude_runs/defect_study"))
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench"]
HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.environ.get("CHIP_TMP", tempfile.gettempdir())
CFG = None


def init(cfg):
    global CFG
    CFG = cfg


def run_problem(p, kmax):
    """(record fields) of one problem up to kmax."""
    import bb6_depth7 as B
    import common
    import ibm_bicycle as IB
    import stabcode
    from cdist import problem
    threads, seconds = CFG
    s = (tuple(map(int, p[0])), tuple(map(int, p[1])))
    t = (tuple(6 - x for x in s[0]), tuple(6 - x for x in s[1]))
    tmp = tempfile.mkdtemp(dir=TMP, prefix="deep_")
    try:
        c = IB.build_instruction("bb288", "Z", 1, 1e-3, B.to_dicts(*s))
        c.to_file(tmp + "/c.stim")
        full = problem.load_dem_problem(tmp + "/c.stim", "c")
        sector = problem.sector_problem(full)
        sizes = [problem.window_problem(sector, w, w).ncols for w in (1, 2)]
        used = s
        if sizes[1] > sizes[0]:
            used = t
            c = IB.build_instruction("bb288", "Z", 1, 1e-3, B.to_dicts(*t))
        n, k = stabcode.css_parameters(*B.matrices("bb288"))[:2]
        common.export_circuit_instance("inst", c, B.translations("bb288"), {"track": "circuit", "family": "bb288_scan", "n": n, "k": k,
                                                                            "basis": "Z", "rounds": 1, "description": "inst",
                                                                            "source": {"px": used[0], "pz": used[1]}}, root=tmp)
        env = dict(os.environ, OMP_NUM_THREADS=str(threads))
        rec = tmp + "/rec.json"
        r = subprocess.run([sys.executable, ROOT + "/bench/adapters/ours_pipeline.py", "--instance", tmp + "/inst", "--variant", "sector",
                            "--config", f"dp=2,kmax={kmax}" + (f",kmin={os.environ['DEEP_KMIN']}" if os.environ.get("DEEP_KMIN") else ""),
                            "--threads", str(threads), "--time-limit", str(seconds), "--out", rec],
                           capture_output=True, text=True, env=env)
        x = json.load(open(rec))
        out = dict(problem=list(p), used=["".join(map(str, used[0])), "".join(map(str, used[1]))], windows=sizes, kmax=kmax,
                   kmin=int(os.environ.get("DEEP_KMIN", "1")), status=x["status"],
                   lb=x["lower_bound"], ub=x["upper_bound"], witness_ok=x["witness_ok"], seconds=x["seconds"], threads=threads,
                   witness=x["witness"], trace=x["trace"])
        if x["witness"] is not None:
            from cdist import replay
            full = problem.load_dem_problem(tmp + "/inst/circuit.stim", "c")
            sector = problem.sector_problem(full)
            raw = replay.lift_to_dem(full, sector, x["witness"])
            dets, obs, _ = replay.check_in_dem(c, raw)
            faults = replay.physical_faults(c, raw)
            d2, o2 = replay.replay(c, faults)
            out["replay_ok"] = (not dets) and bool(obs) and (not d2) and o2 == obs and len(set(raw)) == len(raw)
            out["ticks"] = sorted(f["tick"] for f in faults)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def work(item):
    idx, cl, kmax = item
    os.environ["OMP_NUM_THREADS"] = str(CFG[0])
    t0 = time.time()
    res = dict(index=idx, score=cl["score"], n=cl["n"], s=cl["s"], runs=[])
    if os.environ.get("DEEP_ONLY") and idx not in json.load(open(os.environ["DEEP_ONLY"])):
        res.update(skipped=True, seconds=0.0)
        return res
    try:
        probs = cl["problems"]
        if os.environ.get("DEEP_SECOND"):        # the second problem alone, beside a queue that is still on the first
            b = run_problem(probs[1], kmax)
            res["runs"].append(b)
            res.update(second_only=True, settled=False, ub=b["ub"], lb=None, seconds=round(time.time() - t0, 1))
            return res
        a = run_problem(probs[0], kmax)
        res["runs"].append(a)
        settled = a["status"] in ("exact", "bounds") and (a["ub"] == a["lb"] or a["lb"] == kmax + 1)
        top = a["ub"] - 1 if a["ub"] is not None else kmax
        # below DEEP_KMIN an earlier record has already excluded both problems
        if settled and len(probs) > 1 and top >= int(os.environ.get("DEEP_KMIN", "1")):
            b = run_problem(probs[1], top)
            res["runs"].append(b)
            settled = b["status"] in ("exact", "bounds") and (b["ub"] == b["lb"] or b["lb"] == top + 1)
        ubs = [x["ub"] for x in res["runs"] if x["ub"] is not None]
        lbs = [x["lb"] for x in res["runs"]]
        res.update(settled=settled, ub=min(ubs) if ubs else None, lb=min(lbs) if settled or len(lbs) == len(probs) else None)
    except Exception as e:
        res["error"] = repr(e)[:400]
    res["seconds"] = round(time.time() - t0, 1)
    return res


def main():
    out, cpath, threads, jobs, kmax, seconds, R, M = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), \
        float(sys.argv[6]), int(sys.argv[7]), int(sys.argv[8])
    classes = json.load(open(cpath))
    done = set()
    if os.path.exists(out):
        done = {r["index"] for r in map(json.loads, open(out)) if r.get("settled") or r.get("second_only")}    # a run that failed or was stopped runs again
    only = set(json.load(open(os.environ["DEEP_ONLY"]))) if os.environ.get("DEEP_ONLY") else None
    todo = [(i, c, kmax) for i, c in enumerate(classes) if i % M == R and i not in done and (only is None or i in only)]
    print(time.strftime("%F %T"), "classes", len(classes), "to do here", len(todo), flush=True)
    with mp.get_context("spawn").Pool(jobs, initializer=init, initargs=((threads, seconds),), maxtasksperchild=1) as pool, open(out, "a") as f:
        for i, r in enumerate(pool.imap_unordered(work, todo), 1):
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(time.strftime("%F %T"), i, "of", len(todo), "class", r["index"], "ub", r.get("ub"), "lb", r.get("lb"), "settled", r.get("settled"),
                  "%.0f s" % r["seconds"], r.get("error", ""), flush=True)
    print(time.strftime("%F %T"), "end", flush=True)


if __name__ == "__main__":
    main()
