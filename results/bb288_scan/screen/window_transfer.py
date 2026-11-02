"""Replay, in each problem's own circuit, the fault set of its one-round window: the fault set found in one representative of a distinct window
(window_search.jsonl, screen_k16.jsonl) has the same columns in every problem with that window (window_types.py), and is checked here problem by
problem in the detector error model and with explicit Pauli faults in Stim.

Usage: python window_transfer.py OUT.jsonl TYPES.json SEARCH.jsonl SCREEN.jsonl PROCESSES
"""
import json
import multiprocessing as mp
import os
import sys
import tempfile

ROOT = os.environ.get("CD_ROOT", os.path.expanduser("~/claude_runs/bb288_scan"))
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench"]


def model(p):
    import bb6_depth7 as B
    import ibm_bicycle as IB
    from cdist import problem
    s = (tuple(map(int, p[0])), tuple(map(int, p[1])))
    c = IB.build_instruction("bb288", "Z", 1, 1e-3, B.to_dicts(*s))
    with tempfile.TemporaryDirectory() as d:
        c.to_file(d + "/c.stim")
        full = problem.load_dem_problem(d + "/c.stim", "c")
    return c, full, problem.sector_problem(full)


def content(win, j):
    idx, a, rows = [int(m[0]) for m in win.row_meta], win.h[j], []
    while a:
        b = a & -a
        rows.append(idx[b.bit_length() - 1])
        a ^= b
    return tuple(sorted(rows)), int(win.l[j])


def witness_content(p, t, raw):
    """The fault set of raw detector-model indices in window t of problem p, by content (checks, logical label)."""
    from cdist import problem
    c, full, sector = model(p)
    win = problem.window_problem(sector, t, t)
    rows = sector.notes["sector_rows"]
    lookup = {(a, b): k for k, (a, b) in enumerate(zip(full.h, full.l))}
    of_raw = {}
    for j in range(win.ncols):
        sj, lifted, m = win.col_meta[j], 0, None
        m = sector.h[sj]
        while m:
            low = m & -m
            lifted ^= 1 << rows[low.bit_length() - 1]
            m ^= low
        for r in full.col_meta[lookup[(lifted, sector.l[sj])]]:
            of_raw[r] = j
    return [content(win, of_raw[r]) for r in raw]


def work(item):
    os.environ["OMP_NUM_THREADS"] = "1"
    from cdist import problem, replay
    p, t, wid, cols = item
    out = dict(problem=list(p), t=t, id=wid, weight=len(cols))
    try:
        c, full, sector = model(p)
        win = problem.window_problem(sector, t, t)
        where = {content(win, j): j for j in range(win.ncols)}
        raw = replay.lift_to_dem(full, sector, [win.col_meta[where[tuple(x)]] for x in cols])
        dets, obs, _ = replay.check_in_dem(c, raw)
        faults = replay.physical_faults(c, raw)
        d2, o2 = replay.replay(c, faults)
        out["verified"] = (not dets) and bool(obs) and (not d2) and o2 == obs and len(set(raw)) == len(raw)
    except Exception as e:
        out["verified"] = False
        out["error"] = repr(e)[:300]
    return out


def main():
    out, tpath, spath, scpath, procs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    rows = json.load(open(tpath))
    wid_of = {(tuple(r["problem"]), w["t"]): w["id"] for r in rows for w in r["windows"]}
    wit = {}
    for line in open(spath):
        r = json.loads(line)
        if r.get("witness", {}).get("verified"):
            full_id = next(i for (_, _), i in wid_of.items() if i.startswith(r["id"]))
            wit[full_id] = (r["problem"], r["t"], r["witness"]["dem_error_indices"])
    for line in open(scpath):
        r = json.loads(line)
        w = r.get("witness")
        if w and w.get("verified"):
            p = ("".join(map(str, r["px"])), "".join(map(str, r["pz"])))
            wid = wid_of.get((p, w["window"]))
            if wid is not None and wid not in wit:
                wit[wid] = (list(p), w["window"], w["dem_error_indices"])
    cols = {k: witness_content(*v) for k, v in wit.items()}
    print("windows with a fault set", {k[:4]: len(v) for k, v in cols.items()}, flush=True)
    todo = [(r["problem"], w["t"], w["id"], cols[w["id"]]) for r in rows for w in r["windows"] if w["id"] in cols]
    print("problems to replay", len(todo), flush=True)
    with mp.get_context("spawn").Pool(procs) as pool, open(out, "w") as f:
        n = ok = 0
        for r in pool.imap_unordered(work, todo, chunksize=2):
            f.write(json.dumps(r) + "\n")
            f.flush()
            n += 1
            ok += bool(r["verified"])
    print("replayed", n, "verified", ok, flush=True)


if __name__ == "__main__":
    main()
