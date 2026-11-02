"""The one-round windows of the two-gross problems, by content.  A window of the one-cycle instruction holds the single-qubit columns and, if
the schedule has them in that round, one family of hook columns, so many schedules share the same window problem (same columns and logical
labels on the same checks).  A fault set found in, or excluded from, one such window then holds for all of them.

Usage: python window_types.py OUT.json CLASSES.json PROCESSES
"""
import hashlib
import json
import multiprocessing as mp
import os
import sys
import tempfile

ROOT = os.environ.get("CD_ROOT", os.path.expanduser("~/claude_runs/bb288_scan"))
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench"]


def work(p):
    os.environ["OMP_NUM_THREADS"] = "1"
    import bb6_depth7 as B
    import ibm_bicycle as IB
    from cdist import problem
    s = (tuple(map(int, p[0])), tuple(map(int, p[1])))
    c = IB.build_instruction("bb288", "Z", 1, 1e-3, B.to_dicts(*s))
    with tempfile.TemporaryDirectory() as d:
        c.to_file(d + "/c.stim")
        full = problem.load_dem_problem(d + "/c.stim", "c")
    sector = problem.sector_problem(full)
    out = dict(problem=list(p), windows=[])
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
    out, cpath, procs = sys.argv[1], sys.argv[2], int(sys.argv[3])
    probs = [tuple(map(tuple, [p]))[0] for c in json.load(open(cpath)) for p in c["problems"]]
    with mp.get_context("spawn").Pool(procs) as pool:
        rows = pool.map(work, probs, chunksize=4)
    json.dump(rows, open(out, "w"))
    print("problems", len(rows), "distinct windows", len({w["id"] for r in rows for w in r["windows"]}))


if __name__ == "__main__":
    main()
