"""window_types.py for any bivariate bicycle code in the table of all schedules: the distinct one-round windows of each problem (schedule up to the
symmetries of symmetry_classes.py, memory basis Z), against the exact value of that problem in results/papers3/bb6/KEY_all.json.

Usage: python window_types_key.py KEY OUT.json PROCESSES
"""
import collections as C
import hashlib
import json
import multiprocessing as mp
import os
import sys
import tempfile

R = "/Users/feng/Documents/Research/projects/qec/mld/circuit_distance"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [R + "/papers", R, R + "/bench", HERE]
KEY = sys.argv[1]


def work(s):
    import bb6_depth7 as B
    import ibm_bicycle as IB
    from cdist import problem
    c = IB.build_instruction(KEY, "Z", 1, 1e-3, B.to_dicts(*s))
    with tempfile.TemporaryDirectory() as d:
        c.to_file(d + "/c.stim")
        full = problem.load_dem_problem(d + "/c.stim", "c")
    sector = problem.sector_problem(full)
    out = dict(px=list(s[0]), pz=list(s[1]), windows=[])
    for t in (1, 2):
        win = problem.window_problem(sector, t, t)
        idx = [int(m[0]) for m in win.row_meta]
        cols = []
        for a, l in zip(win.h, win.l):
            rows = []
            while a:
                b = a & -a
                rows.append(idx[b.bit_length() - 1])
                a ^= b
            cols.append((sorted(rows), int(l)))
        cols.sort()
        out["windows"].append(dict(t=t, columns=win.ncols, id=hashlib.sha1(json.dumps(cols).encode()).hexdigest()[:12]))
    return out


def main():
    import bb6_depth7 as B
    import symmetry_classes as SC
    out, procs = sys.argv[2], int(sys.argv[3])
    sch = B.all_valid()
    rep, reps = SC.z_problems(KEY, sch)
    assert all(b == "Z" for _, b in reps)
    with mp.get_context("spawn").Pool(procs) as pool:
        rows = pool.map(work, [r[0] for r in reps], chunksize=4)
    d = json.load(open(f"{R}/results/papers3/bb6/{KEY}_all.json"))
    val = {(tuple(r["px"]), tuple(r["pz"])): r["Z"][1] for r in d["rows"]}
    for r in rows:
        r["Z"] = val[(tuple(r["px"]), tuple(r["pz"]))]
    json.dump(rows, open(out, "w"))
    tab = C.Counter((tuple(sorted(w["columns"] for w in r["windows"])), r["Z"]) for r in rows)
    print(KEY, "problems", len(rows), "distinct windows", len({w["id"] for r in rows for w in r["windows"]}))
    for k, v in sorted(tab.items()):
        print(" ", k, v)


if __name__ == "__main__":
    main()
