"""Deep certified bounds for a large circuit (BB288) where the real problem is
out of reach of exhaustive search.

  upper bound : exact search of the first-round window (a sub-experiment
                containing only faults before the first syndrome round), whose
                solutions are real undetected logical faults; verified in the
                full DEM and replayed physically
  lower bound : exact weight-bounded search of the time-collapsed relaxation
                (independent of the number of rounds), with translation
                symmetry; if minimum collapsed solutions are found, they are
                enumerated and tested for lifting to the real circuit

Usage: python scripts/run_deep.py circuits/bb288_r18_Z.stim results/bb288_r18_Z.json --kmax 17 --k-table 4
"""
import argparse
import json
import os
import sys
import time

import stim

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # repository root

from cdist import lift, problem, replay, search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("out")
    ap.add_argument("--kmax", type=int, default=16)
    ap.add_argument("--k-table", type=int, default=3)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--sector-high", action="store_true",
                    help="memory-sector detectors are those with 4th coordinate >= 3 (circuits with flags)")
    ap.add_argument("--time-limit", type=float, default=0.0)
    ap.add_argument("--ub-kmax", type=int, default=18)
    ap.add_argument("--ub-time-limit", type=float, default=3600.0)
    ap.add_argument("--skip-ub", action="store_true")
    ap.add_argument("--no-sym", action="store_true")
    ap.add_argument("--table-load", type=float, default=0.5)
    ap.add_argument("--cover", action="store_true", help="prune with the covering bound (phase 4)")
    args = ap.parse_args()

    res = {"circuit": args.circuit, "threads": search.lib().gm_num_threads(), "args": vars(args)}

    def save():
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        tmp = args.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(res, f, indent=1)
        os.replace(tmp, args.out)

    t0 = time.time()
    circ = stim.Circuit.from_file(args.circuit)
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
    assert exact
    save()

    def verify_witness(sector_cols):
        raw = replay.lift_to_dem(full, sector, sector_cols)
        dets, obs, terms = replay.check_in_dem(circ, raw)
        faults = replay.physical_faults(circ, raw)
        d2, o2 = replay.replay(circ, faults)
        ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
        return {
            "weight": len(raw), "dem_error_indices": raw, "dem_errors": terms,
            "dem_check": {"detectors": dets, "observables": obs},
            "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement", "stack")}
                                for f in faults],
            "replay": {"fired_detectors": d2, "flipped_observables": o2}, "verified": ok,
        }

    # ---------------- upper bound from the first-round window
    # single-layer windows: all faults whose detection events lie in one
    # detector layer (t = 0: before the first round; t = 1: a bulk round)
    for tw in ([] if args.skip_ub else [0, 1]):
        win = problem.window_problem(sector, tw, tw)
        sym = {"ok": False} if args.no_sym else symmetry.translations(win)
        kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") and sym["generators"] else {}
        log(f"[window t={tw}] columns={win.ncols} symmetry={sym.get('generators')}")
        r = search.distance(win, k_table=3, kmax=res.get("certified_upper_bound", args.ub_kmax),
                            time_limit=args.ub_time_limit, log=log, **kw)
        st = {"columns": win.ncols, "distance": r["distance"], "lower_bound_of_window": r["lower_bound"],
              "runs": [{"K": x["K"], "status": x["status"], "nodes": sum(x["nodes"]), "seconds": round(x["seconds"], 2)}
                       for x in r["runs"]]}
        if r["distance"] is not None:
            sol = [win.col_meta[j] for j in r["solutions"][0]]
            w = verify_witness(sol)
            st["witness"] = w
            log(f"[window t={tw}] distance {r['distance']}; witness verified={w['verified']} "
                f"(DEM detectors {w['dem_check']['detectors']}, replay detectors {w['replay']['fired_detectors']}, "
                f"observables {w['replay']['flipped_observables']})")
            if w["verified"] and w["weight"] < res.get("certified_upper_bound", 10 ** 9):
                res["certified_upper_bound"] = w["weight"]
        res[f"window_t{tw}"] = st
        save()

    # ---------------- lower bound from the collapsed relaxation
    sym = {"ok": False} if args.no_sym else symmetry.translations(collapsed)
    kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") and sym["generators"] else {}
    st = {"rows": collapsed.nrows, "columns": collapsed.ncols, "symmetry": sym.get("generators"),
          "orbits": len(sym["anchors"]) if sym.get("ok") else None, "k_table": args.k_table, "runs": []}
    res["collapsed"] = st
    res["certified_lower_bound"] = args.start

    def on_run(rec):
        st["runs"].append({"K": rec["K"], "status": rec["status"], "best": rec["best"], "nodes": sum(rec["nodes"]),
                           "nodes_by_depth": rec["nodes"], "lookups": rec["lookups"],
                           "false_hits": rec["false_hits"], "cover_pruned": rec.get("cover_pruned", 0),
                           "seconds": round(rec["seconds"], 2)})
        if rec["status"] == "exhausted" and rec["best"] is None:
            res["certified_lower_bound"] = rec["K"] + 1
        save()

    kmax = min(args.kmax, res.get("certified_upper_bound", args.kmax))
    r = search.distance(collapsed, k_table=args.k_table, kmax=kmax, time_limit=args.time_limit,
                        start=args.start, enum_all=True, log=log, on_run=on_run, table_load=args.table_load,
                        cover=args.cover, **kw)
    st["table_entries"] = r["table_entries"]
    st["exclusion_pairs"] = r["exclusion_pairs"]
    st["distance"] = r["distance"]
    st["lower_bound"] = r["lower_bound"]
    res["certified_lower_bound"] = max(res["certified_lower_bound"], r["lower_bound"]) if r["distance"] is None \
        else r["distance"]
    log(f"[collapsed] distance={r['distance']} certified lower bound={r['lower_bound']}")
    save()

    if r["distance"] is not None:
        allsol = lift.expand_orbits(r["solutions"], sym.get("colmaps", []))
        reps = lift.orbit_representatives(allsol, sym.get("colmaps", []))
        st["n_min_solutions"] = len(allsol)
        st["n_orbits"] = len(reps)
        log(f"[collapsed] {len(allsol)} minimum solutions in {len(reps)} orbits; lifting")
        lifts = []
        best = None
        for rep, size in reps:
            rec = {"classes": list(rep), "orbit_size": size}
            for slack in (0, 1):
                w, cols = lift.lift(sector, collapsed, rep, slack, time_limit=600)
                rec[f"lift_slack{slack}"] = w
                if w is not None and (best is None or w < best[0]):
                    best = (w, cols)
            lifts.append(rec)
        st["lifts"] = lifts
        n0 = sum(1 for x in lifts if x["lift_slack0"] is not None)
        log(f"[collapsed] orbits lifting exactly: {n0} of {len(lifts)}")
        st["minimum_enumeration_complete"] = r["solutions_complete"]
        if n0 == 0 and r["solutions_complete"]:
            # a real solution of weight d_coll would project onto a minimum
            # collapsed solution with one member per class (all of them are in the list)
            res["certified_lower_bound"] = r["distance"] + 1
        if best is not None:
            w = verify_witness(best[1])
            st["lift_witness"] = w
            if w["verified"] and w["weight"] < res.get("certified_upper_bound", 10 ** 9):
                res["certified_upper_bound"] = w["weight"]
    res["seconds"] = round(time.time() - t0, 1)
    save()
    log("done", {k: res.get(k) for k in ("certified_lower_bound", "certified_upper_bound", "seconds")})


if __name__ == "__main__":
    main()
