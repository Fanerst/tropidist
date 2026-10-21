"""Exact minimum weight of the faults of one time window of a CSS memory circuit (an upper bound on the circuit
distance), with the circuit's translation symmetries and the covering bound.  The window holds the faults whose
detection events all lie in rounds t0..t1 of the sector problem.  The witness is checked in the full detector error
model and replayed in Stim.

`start` may be any certified lower bound on the circuit distance: no fault set of the window is lighter than the
circuit distance, so thresholds below it need not be searched.

usage: python scripts/window_search.py paper size basis rounds t0 t1 start kmax out.json [seconds per threshold]
example: python scripts/window_search.py cornucopia 64 Z 8 1 1 11 16 out.json 21600
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "papers")]
from cdist import problem, replay, search
import run_parallel


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main(paper, size, basis, rounds, t0, t1, start, kmax, out, seconds=0):
    rounds, t0, t1, start, kmax, seconds = int(rounds), int(t0), int(t1), int(start), int(kmax), float(seconds)
    mod = __import__(paper)
    size = int(size) if str(size).lstrip("-").isdigit() else size
    t = time.time()
    circ = mod.build(size, basis, rounds)
    tag = mod.tag(size) if hasattr(mod, "tag") else mod.CODES[size][2][0]
    path = os.path.join(ROOT, "circuits", "papers", f"{paper}{tag}_r{rounds}_{basis}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path, os.path.basename(path))
    sector = problem.sector_problem(full, None)
    assert problem.sector_is_exact(full, sector)
    win = problem.window_problem(sector, t0, t1)
    sym, kw = run_parallel.sym_of(win, mod.translations(size) if hasattr(mod, "translations") else [])
    res = {"paper": paper, "code": list(mod.CODES[size][2]), "basis": basis, "rounds": rounds, "window": [t0, t1],
           "start": start, "kmax": kmax, "columns": win.ncols, "rows": win.nrows,
           "symmetries_kept": sym.get("n_symmetries_kept"), "threads": search.lib().gm_num_threads(), "runs": []}
    log(f"{path}: window {t0}..{t1}: {win.nrows} rows x {win.ncols} columns; symmetries {res['symmetries_kept']} "
        f"({time.time() - t:.0f}s)")

    def save():
        json.dump(res, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)

    def on_run(rec):
        res["runs"].append({"K": rec["K"], "status": rec["status"], "nodes": sum(rec["nodes"]),
                            "seconds": round(rec["seconds"], 2)})
        save()

    r = search.distance(win, k_table=2, kmax=kmax, time_limit=seconds, log=log, start=start, on_run=on_run,
                        labelfree=True, cover=True, **kw)
    res["window_minimum"] = r["distance"]
    res["window_lower_bound"] = r["lower_bound"]
    if r["distance"] is not None:
        raw = replay.lift_to_dem(full, sector, [win.col_meta[j] for j in r["solutions"][0]])
        dets, obs, terms = replay.check_in_dem(circ, raw)
        faults = replay.physical_faults(circ, raw)
        d2, o2 = replay.replay(circ, faults)
        ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
        res["witness"] = {"weight": len(raw), "dem_error_indices": raw, "dem_errors": terms,
                          "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis",
                                                                 "flipped_measurement", "stack")} for f in faults],
                          "replay": {"fired_detectors": d2, "flipped_observables": o2}, "verified": ok}
        if ok:
            res["certified_upper_bound"] = len(raw)
        log(f"window minimum {r['distance']}: witness verified={ok}")
    else:
        log(f"no fault set of weight <= {kmax} in the window (lower bound {r['lower_bound']})")
    res["seconds"] = round(time.time() - t, 1)
    save()


if __name__ == "__main__":
    main(*sys.argv[1:])
