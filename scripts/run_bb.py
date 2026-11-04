"""Circuit distance of a Stim memory experiment: certified bounds and witnesses.

Pipeline
  1. undecomposed DEM -> CSS sector problem (checked to preserve the distance)
  2. relaxations: time-collapse (fold 1) and time-fold with period P
  3. exact weight-bounded search on each relaxation  -> certified lower bounds
  4. exact search on the real sector problem, pruned by the collapsed table
  5. witness: checked in the full DEM and replayed as physical circuit faults

Usage: python scripts/run_bb.py circuits/bb144_r12_Z.stim results/bb144_r12_Z.json [options]
"""
import argparse
import json
import os
import sys
import time

import stim

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdist import problem, replay, search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def runs_summary(r):
    return [{"K": x["K"], "status": x["status"], "best": x["best"], "nodes": sum(x["nodes"]),
             "nodes_by_depth": x["nodes"], "lookups": x["lookups"], "false_hits": x["false_hits"],
             "seconds": round(x["seconds"], 3)} for x in r["runs"]]


def solve(p, label, k_table, kmax, relaxed, use_sym, time_limit, start, enum_all=False):
    sym = symmetry.translations(p) if use_sym else {"ok": False}
    kw = {}
    if sym.get("ok") and sym["generators"]:
        kw = {"rank": sym["rank"], "anchors": sym["anchors"]}
    t = time.time()
    r = search.distance(p, k_table=k_table, kmax=kmax, relaxed=relaxed, time_limit=time_limit,
                        start=start, enum_all=enum_all, log=log, **kw)
    out = {
        "problem": label, "rows": p.nrows, "columns": p.ncols,
        "symmetry_generators": sym.get("generators") if sym.get("ok") else None,
        "orbits": len(sym["anchors"]) if sym.get("ok") else None,
        "k_table": k_table, "table_entries": r["table_entries"],
        "lower_bound": r["lower_bound"], "distance": r["distance"],
        "n_solutions_recorded": len(r["solutions"]),
        "runs": runs_summary(r), "seconds": round(time.time() - t, 2),
    }
    log(f"[{label}] distance={r['distance']} certified_lower_bound={r['lower_bound']} "
        f"solutions={len(r['solutions'])} ({out['seconds']}s)")
    return out, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("out")
    ap.add_argument("--folds", default="2,3")
    ap.add_argument("--k-collapsed", type=int, default=3, help="subset size of the collapsed lookup table")
    ap.add_argument("--k-main", type=int, default=2)
    ap.add_argument("--kmax", type=int, default=20)
    ap.add_argument("--sector-high", action="store_true",
                    help="memory-sector detectors are those with 4th coordinate >= 3 (circuits with flags)")
    ap.add_argument("--time-limit", type=float, default=0.0, help="seconds per threshold (0 = none)")
    ap.add_argument("--no-full", action="store_true")
    ap.add_argument("--no-sym", action="store_true")
    ap.add_argument("--enum-collapsed", action="store_true", help="list all minimum collapsed solutions")
    args = ap.parse_args()

    res = {"circuit": args.circuit, "threads": search.lib().gm_num_threads(), "stages": {}}
    circ = stim.Circuit.from_file(args.circuit)
    t0 = time.time()
    full = problem.load_dem_problem(args.circuit, os.path.basename(args.circuit))
    sector = problem.sector_problem(full, high=True if args.sector_high else None)
    exact = problem.sector_is_exact(full, sector)
    collapsed = problem.collapse_time(sector)
    res["model"] = {
        "qubits": circ.num_qubits, "detectors": circ.num_detectors, "observables": circ.num_observables,
        "dem_mechanisms": full.notes["raw_mechanisms"], "dem_distinct_columns": full.ncols,
        "sector_rows": sector.nrows, "sector_columns": sector.ncols, "sector_reduction_exact": exact,
        "collapsed_rows": collapsed.nrows, "collapsed_columns": collapsed.ncols,
    }
    log("model", res["model"], f"({time.time() - t0:.1f}s)")
    assert exact, "sector reduction is only a relaxation for this circuit"
    use_sym = not args.no_sym

    def save():
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(res, f, indent=1)

    # --- collapsed relaxation
    out, r = solve(collapsed, "collapsed", args.k_collapsed, args.kmax, None, use_sym, args.time_limit, 1,
                   enum_all=args.enum_collapsed)
    res["stages"]["collapsed"] = out
    lb = out["lower_bound"]
    save()

    ctab = search.Table(collapsed, args.k_collapsed, seed=777)
    log(f"collapsed pruning table: k={args.k_collapsed} entries={ctab.entries} ({ctab.build_seconds:.1f}s)")

    # --- folded relaxations
    for P in [int(x) for x in args.folds.split(",") if x]:
        f = problem.fold_time(sector, P)
        img = [collapsed.image[f.col_meta[j][0]] for j in range(f.ncols)]
        out, r = solve(f, f"fold{P}", args.k_main, args.kmax, [(ctab, img)], use_sym, args.time_limit, lb)
        res["stages"][f"fold{P}"] = out
        lb = max(lb, out["lower_bound"])
        save()

    res["certified_lower_bound"] = lb

    # --- the real problem
    if not args.no_full:
        out, r = solve(sector, "sector(full circuit)", args.k_main, args.kmax, [(ctab, collapsed.image)],
                       use_sym, args.time_limit, lb)
        res["stages"]["full"] = out
        lb = max(lb, out["lower_bound"])
        res["certified_lower_bound"] = lb
        if r["distance"] is not None:
            sol = r["solutions"][0]
            raw = replay.lift_to_dem(full, sector, sol)
            dets, obs, terms = replay.check_in_dem(circ, raw)
            faults = replay.physical_faults(circ, raw)
            d2, o2 = replay.replay(circ, faults)
            ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
            res["witness"] = {
                "weight": len(raw), "dem_error_indices": raw, "dem_errors": terms,
                "dem_check": {"detectors": dets, "observables": obs},
                "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement", "stack")}
                                    for f in faults],
                "replay": {"fired_detectors": d2, "flipped_observables": o2},
                "verified": ok,
            }
            log(f"witness weight {len(raw)}: DEM detectors={dets} obs={obs}; replay detectors={d2} obs={o2}; verified={ok}")
            if ok:
                res["certified_upper_bound"] = len(raw)
        save()
    res["seconds"] = round(time.time() - t0, 2)
    save()
    log("done", {k: res.get(k) for k in ("certified_lower_bound", "certified_upper_bound", "seconds")})


if __name__ == "__main__":
    main()
