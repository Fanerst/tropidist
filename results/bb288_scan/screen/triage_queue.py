"""Quick first pass over the two-gross problems: the benchmark pipeline (dp=2), as in deep_queue.py, on each problem of a list for a short
time.  The pipeline finds a fault set of weight 16 within seconds on most problems, long before it could exhaust weight 15, and a replayed
fault set is all it takes to show that a schedule stays at 16 or below; the problems left without one are the ones that need long runs.
Results are appended per problem to a JSON-lines file, and problems already there are skipped.

Usage: python triage_queue.py OUT.jsonl LIST.json THREADS JOBS KMAX SECONDS
LIST.json holds [class index, problem] pairs, in order (make_triage.py).
"""
import json
import multiprocessing as mp
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deep_queue as Q


def work(item):
    idx, p, kmax = item
    os.environ["OMP_NUM_THREADS"] = str(Q.CFG[0])
    t0 = time.time()
    res = dict(index=idx, problem=list(p))
    try:
        res.update(Q.run_problem(p, kmax))
    except Exception as e:
        res["error"] = repr(e)[:400]
    res["total_seconds"] = round(time.time() - t0, 1)
    return res


def main():
    out, lpath, threads, jobs, kmax, seconds = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])
    done = set()
    if os.path.exists(out):
        done = {tuple(json.loads(x)["problem"]) for x in open(out)}
    todo = [(i, p, kmax) for i, p in json.load(open(lpath)) if tuple(p) not in done]
    print(time.strftime("%F %T"), "to do here", len(todo), flush=True)
    with mp.get_context("spawn").Pool(jobs, initializer=Q.init, initargs=((threads, seconds),), maxtasksperchild=1) as pool, open(out, "a") as f:
        for i, r in enumerate(pool.imap_unordered(work, todo), 1):
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(time.strftime("%F %T"), i, "of", len(todo), "class", r["index"], "ub", r.get("ub"), "lb", r.get("lb"), r.get("status"),
                  "replay", r.get("replay_ok"), r.get("windows"), "%.0f s" % r["total_seconds"], r.get("error", ""), flush=True)
    print(time.strftime("%F %T"), "end", flush=True)


if __name__ == "__main__":
    main()
