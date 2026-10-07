"""STAR depth-8 schedules (arXiv:2606.25011): dependence on the unprinted index convention.

papers/star.py reads the paper's B_i as A_i^T.  The paper does not print the B_i, so this script
tries every convention B_i = A_sigma(i)^T (24 permutations sigma): each of the 212 schedules of
the family is relabelled accordingly (X couplings "R, B_i" and Z couplings "L, B_i^T" move to
index sigma(i)), checked for validity on the [[42,6,6]] code, and its exact circuit distance is
computed in both bases.  The paper reports 192 schedules at fault distance 4 and 20 at 5, with
the Table 2 schedule among the 20.

Usage: python papers/star_dictionary.py [processes] [key]
"""
import contextlib
import io
import itertools
import json
import multiprocessing as mp
import os
import sys
import time
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import run_parallel
import star

KEY = 42


def relabel(schedule, sigma):
    """sigma: tuple, sigma[i-1] = index that B_i refers to."""
    x = tuple(f"R{sigma[int(l[1]) - 1]}" if l[0] == "R" else l for l in schedule["X"])
    z = tuple(f"L{sigma[int(l[1]) - 1]}" if l[0] == "L" else l for l in schedule["Z"])
    return {"X": x, "Z": z}


def _init():
    os.environ["OMP_NUM_THREADS"] = "1"


def _work(job):
    sigma, idx, sched = job
    try:
        if not star.schedule_is_valid(KEY, sched):
            return sigma, idx, "invalid", None
    except ValueError:
        return sigma, idx, "invalid", None
    name = f"stardict_w{os.getpid()}"
    codes = dict(star.CODES)
    d0 = codes[KEY]
    codes[KEY] = (d0[0], d0[1], d0[2], None)
    sys.modules[name] = SimpleNamespace(
        CODES=codes, translations=star.translations, tag=lambda size: f"{size}",
        build=lambda size, basis, rounds, p=0.001: star.build(size, basis, rounds, p=p, schedule=sched))
    out = {}
    for basis in "ZX":
        path = os.path.join(ROOT, "results", "papers3", "star", "dict_tmp", f"{name}_{basis}.json")
        with contextlib.redirect_stdout(io.StringIO()):
            run_parallel.main(name, KEY, basis, path, 6, 2, 8, 600, 1)
        r = json.load(open(path))
        out[basis] = (r.get("certified_lower_bound"), r.get("certified_upper_bound"))
        for f in (path, os.path.join(ROOT, "circuits", "papers", f"{name}{KEY}_r6_{basis}.stim")):
            if os.path.exists(f):
                os.remove(f)
    return sigma, idx, "valid", out


def main(procs=8, key=42):
    global KEY
    procs, KEY = int(procs), int(key)
    family = star.valid_schedules(KEY)
    paper = dict(star.PAPER_SCHEDULE)
    pidx = next(i for i, s in enumerate(family) if tuple(s["X"]) == tuple(paper["X"]) and tuple(s["Z"]) == tuple(paper["Z"]))
    jobs = [(sigma, i, relabel(s, sigma)) for sigma in itertools.permutations(range(1, 5)) for i, s in enumerate(family)]
    os.makedirs(os.path.join(ROOT, "results", "papers3", "star", "dict_tmp"), exist_ok=True)
    t0 = time.time()
    res = {}
    with mp.Pool(procs, maxtasksperchild=8, initializer=_init) as pool:
        for n, (sigma, idx, status, out) in enumerate(pool.imap_unordered(_work, jobs, chunksize=4)):
            res.setdefault(sigma, {})[idx] = (status, out)
            if (n + 1) % 500 == 0:
                print(time.strftime("%H:%M:%S"), f"{n + 1}/{len(jobs)}, {time.time() - t0:.0f}s", flush=True)
    rows = []
    for sigma in sorted(res):
        v = res[sigma]
        valid = [i for i in v if v[i][0] == "valid"]
        hist = {}
        for i in valid:
            z, x = v[i][1]["Z"], v[i][1]["X"]
            k = str(min(z[0], x[0])) if z[0] == z[1] and x[0] == x[1] else "open"
            hist[k] = hist.get(k, 0) + 1
        pt = v[pidx]
        rows.append({"sigma": list(sigma), "valid_schedules": len(valid), "distance_histogram": dict(sorted(hist.items())),
                     "table2_schedule": None if pt[0] != "valid" else {b: list(pt[1][b]) for b in "ZX"}})
        print(sigma, "valid", len(valid), "histogram", dict(sorted(hist.items())), "Table 2:", rows[-1]["table2_schedule"], flush=True)
    out = os.path.join(ROOT, "results", "papers3", "star", f"dictionary_{KEY}.json")
    json.dump({"code": list(star.CODES[KEY][2]), "family": len(family), "paper": {"4": 192, "5": 20, "table2": 5},
               "conventions": rows, "seconds": round(time.time() - t0, 1)}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
