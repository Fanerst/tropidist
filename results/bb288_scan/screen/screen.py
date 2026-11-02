"""Screen of the two-gross schedules: for each of the 708 distinct problems (schedule, basis) under the symmetries of
symmetry_classes.py, search the two one-round windows of the one-cycle instruction (IBM's setting, papers/ibm_bicycle.py) for a
logical fault set of weight <= KMAX.  A set found is a real fault set of the circuit (replayed in Stim); a window without one
says nothing about the circuit.  One thread per problem; results are appended to a JSON-lines file and the run resumes.

Usage: python screen.py OUT.jsonl PROCESSES KMAX SECONDS_PER_WINDOW [ORDER_FILE]
"""
import contextlib
import io
import json
import multiprocessing as mp
import os
import sys
import tempfile
import time

ROOT = os.environ.get("CD_ROOT", os.path.expanduser("~/claude_runs/bb288_scan"))
sys.path[:0] = [ROOT + "/papers", ROOT, ROOT + "/bench", os.path.dirname(os.path.abspath(__file__))]
KEY = "bb288"
CFG = None


def init(cfg):
    global CFG
    os.environ["OMP_NUM_THREADS"] = "1"
    CFG = cfg


def work(rep):
    import bb6_depth7 as B
    import ibm_bicycle as IB
    import run_parallel as RP
    from cdist import problem, replay
    kmax, tl = CFG
    t0 = time.time()
    s, basis = rep
    out = dict(px=list(s[0]), pz=list(s[1]), basis=basis)
    try:
        circ = IB.build_instruction(KEY, basis, 1, 1e-3, B.to_dicts(*s))
        with tempfile.TemporaryDirectory() as d:
            path = d + "/c.stim"
            circ.to_file(path)
            full = problem.load_dem_problem(path, "c")
        sector = problem.sector_problem(full)
        assert problem.sector_is_exact(full, sector)
        out["model"] = [sector.nrows, sector.ncols]
        cperms = B.translations(KEY)
        best = None
        for t in (1, 2):
            win = problem.window_problem(sector, t, t)
            _, kw = RP.sym_of(win, cperms)
            with contextlib.redirect_stdout(io.StringIO()):
                r = RP.dist(win, k_table=2, kmax=kmax, time_limit=tl, start=1, **kw)
            runs = r["runs"]
            rec = dict(columns=win.ncols, distance=r["distance"], lower=r["lower_bound"],
                       status=runs[-1]["status"] if runs else None, seconds=round(sum(x["seconds"] for x in runs), 1))
            out[f"t{t}"] = rec
            if r["distance"] is not None and (best is None or r["distance"] < best[0]):
                best = (r["distance"], [win.col_meta[j] for j in r["solutions"][0]], t)
            if best is not None and best[0] <= kmax:
                break
        if best is not None:
            raw = replay.lift_to_dem(full, sector, best[1])
            dets, obs, terms = replay.check_in_dem(circ, raw)
            faults = replay.physical_faults(circ, raw)
            d2, o2 = replay.replay(circ, faults)
            ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
            out["witness"] = dict(weight=len(raw), window=best[2], verified=ok, dem_error_indices=raw,
                                  faults=[{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement")}
                                          for f in faults])
    except Exception as e:
        out["error"] = repr(e)[:300]
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    import bb6_depth7 as B
    import symmetry_classes as SC
    path, procs, kmax, tl = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    sch = B.all_valid()
    rep, reps = SC.z_problems(KEY, sch)
    assert len(reps) == 708 and all(b == "Z" for _, b in reps)
    if len(sys.argv) > 5:
        order = [(tuple(a), tuple(b)) for a, b in json.load(open(sys.argv[5]))]
        rank = {x: i for i, x in enumerate(order)}
        reps.sort(key=lambda r: rank.get(r[0], len(order)))
    done = set()
    if os.path.exists(path):
        for line in open(path):
            r = json.loads(line)
            done.add((tuple(r["px"]), tuple(r["pz"])))
    todo = [r for r in reps if r[0] not in done]
    print(time.strftime("%F %T"), "problems", len(reps), "to do", len(todo), flush=True)
    ctx = mp.get_context("spawn")
    with ctx.Pool(procs, initializer=init, initargs=((kmax, tl),), maxtasksperchild=4) as pool, open(path, "a") as f:
        for i, r in enumerate(pool.imap_unordered(work, todo), 1):
            f.write(json.dumps(r) + "\n")
            f.flush()
            if i % 10 == 0 or i == len(todo):
                print(time.strftime("%F %T"), i, "of", len(todo), flush=True)
    print(time.strftime("%F %T"), "end", flush=True)


if __name__ == "__main__":
    main()
