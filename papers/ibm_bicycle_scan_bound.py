"""All minimum fault sets and the decoder-independent lower bounds of papers/ibm_bicycle_bound.py for many schedules
(the rows of a scan by papers/ibm_bicycle_scan.py whose instruction distance is d in both bases), in parallel;
JSON-lines output, resumable.

Usage: python papers/ibm_bicycle_scan_bound.py KEY SCAN.jsonl D CYCLES OUT.jsonl [processes]
"""
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bb6_depth7 as B
import ibm_bicycle_bound as BD

_CFG = None


def _init(cfg):
    global _CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    _CFG = cfg


def _work(sched):
    key, d, cycles = _CFG
    stag = "s" + "".join(map(str, sched[0])) + "_" + "".join(map(str, sched[1]))
    out = {"px": list(sched[0]), "pz": list(sched[1])}
    for b in "ZX":
        try:
            r = BD.compute(key, b, cycles, d, B.to_dicts(*sched), stag, 3, (1e-4, 1e-3), quiet=True)
            out[b] = {k: r[k] for k in ("n_orbit_representatives", "n_minimum_fault_sets", "n_family", "rates",
                                        "seconds")}
        except Exception as e:
            out[b] = {"error": repr(e)[:300]}
    return out


def main(key, scan, d, cycles, out, procs=32):
    d, cycles, procs = int(d), int(cycles), int(procs)
    todo = []
    for line in open(scan):
        r = json.loads(line)
        if "error" not in r and all(r[b][0] == r[b][1] == d for b in "ZX"):
            todo.append((tuple(r["px"]), tuple(r["pz"])))
    done = set()
    if os.path.exists(out):
        done = {(tuple(json.loads(l)["px"]), tuple(json.loads(l)["pz"])) for l in open(out)}
    todo = [s for s in todo if s not in done]
    print(f"{len(todo)} schedules", flush=True)
    with mp.Pool(procs, initializer=_init, initargs=((key, d, cycles),), maxtasksperchild=10) as pool, \
            open(out, "a") as f:
        for i, res in enumerate(pool.imap_unordered(_work, todo), 1):
            f.write(json.dumps(res) + "\n")
            f.flush()
            if i % 20 == 0:
                print(i, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
