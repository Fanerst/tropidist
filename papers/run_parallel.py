"""Circuit distance of a CSS memory circuit whose X and Z checks are measured in
the same cycle (Cornucopia, GALA), with any number of logical observables.

  1. undecomposed DEM -> CSS sector problem (checked to preserve the distance)
  2. time-collapsed relaxation: exact distance d_coll and all minimum solutions
     -> certified lower bound d_coll
  3. each minimum collapsed solution is lifted to the real circuit (one fault
     per class, then one extra fault); a lifted solution is checked in the full
     DEM and replayed physically -> verified upper bound.  If no minimum
     solution lifts exactly, the lower bound is d_coll + 1.
  4. if still open: exact search of a one-round window (upper bound) and of the
     real sector problem pruned by the collapsed table (exact value).

A paper module provides CODES[size] = (..., ..., (n, k, d), claimed circuit distance or None),
build(size, basis, rounds), and optionally translations(size) (check permutations that are
symmetries of the circuit) and tag(size) (name used in file names).

Usage: python papers/run_parallel.py cornucopia 7 Z out.json [rounds] [k_coll] [kmax] [seconds_per_threshold] [full: 0|1] [noise: full|cx] [cover: 0|1]

cover = 1 adds the covering bound to every search (fewer nodes, more work per node; it pays off from a
threshold of about 8 on these circuits).  The default 0 is the setting of the October 2026 records.
"""
import json
import os
import sys
import time

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from cdist import lift, problem, replay, search, symmetry
from cdist.problem import Problem


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def row_perms(p, check_perms):
    """Lift permutations of the check index to the rows of p (row_meta[0] = check, the rest unchanged)."""
    index = {tuple(m): i for i, m in enumerate(p.row_meta)}
    out = []
    for cp in check_perms:
        perm = []
        for m in p.row_meta:
            t = index.get((float(cp[int(m[0])]),) + tuple(m[1:]))
            if t is None:
                perm = None
                break
            perm.append(t)
        if perm is not None:
            out.append(perm)
    return out


def sym_of(p, check_perms):
    if not check_perms:
        return {"ok": False}, {}
    sym = symmetry.from_row_perms(p, row_perms(p, check_perms))
    kw = {"rank": sym["rank"], "anchors": sym["anchors"]} if sym.get("ok") else {}
    return sym, kw


COVER = False


def dist(p, **kw):
    """One pass over the search tree for any number of observables (label-free mode)."""
    r = search.distance(p, labelfree=True, cover=COVER, **kw)
    for x in r["runs"]:
        x["nodes"] = sum(x["nodes"])
    return r


def lift_multi(sector, relaxed, classes, slack, time_limit, start=1):
    """As cdist.lift.lift, for any number of observables.  start: a certified lower bound on the circuit distance;
    every solution of the restriction is a sector solution, so lighter thresholds need no search."""
    cols = []
    for j in classes:
        cols.extend(relaxed.col_meta[j])
    if slack > 0:
        cols.extend(i for i, img in enumerate(relaxed.image) if img == 0 and sector.l[i] == 0)
    cols = sorted(set(cols))
    sub = Problem("lift", sector.nrows, sector.nobs, [sector.h[i] for i in cols], [sector.l[i] for i in cols],
                  sector.row_meta)
    kmax = len(classes) + slack
    r = dist(sub, k_table=2 if slack == 0 else 1, kmax=kmax, time_limit=time_limit, start=min(start, kmax))
    if r["runs"] and r["runs"][-1]["status"] == "timeout":
        return "timeout", None
    if r["distance"] is None:
        return None, None
    return r["distance"], tuple(cols[i] for i in r["solutions"][0])


def main(paper, size, basis, out, rounds=6, k_coll=3, kmax=14, time_limit=0, do_full=1, noise="full", cover=0):
    global COVER
    rounds, k_coll, kmax, time_limit, do_full = int(rounds), int(k_coll), int(kmax), float(time_limit), int(do_full)
    COVER = bool(int(cover))
    mod = __import__(paper)
    size = int(size) if str(size).lstrip("-").isdigit() else size       # keys of mod.CODES are ints or strings
    t0 = time.time()
    circ = mod.build(size, basis, rounds, noise=noise) if noise != "full" else mod.build(size, basis, rounds)
    # modules with several instances of the same length name them with tag(size)
    tag = mod.tag(size) if hasattr(mod, "tag") else mod.CODES[size][2][0]
    name = f"{paper}{tag}_r{rounds}_{basis}" + ("" if noise == "full" else f"_{noise}")
    path = os.path.join(ROOT, "circuits", "papers", name + ".stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ.to_file(path)
    full = problem.load_dem_problem(path, name)
    # circuits with flag detectors of both classes in round 0 say which class the memory basis uses
    high = mod.sector_high(basis) if hasattr(mod, "sector_high") else None
    sector = problem.sector_problem(full, high)
    exact = problem.sector_is_exact(full, sector)
    coll = problem.collapse_time(sector)
    res = {"paper": paper, "code": list(mod.CODES[size][2]), "paper_circuit_distance_upper_bound": mod.CODES[size][3],
           "basis": basis, "rounds": rounds, "noise": noise, "cover": COVER, "circuit": os.path.relpath(path, ROOT),
           "threads": search.lib().gm_num_threads(),
           "model": {"qubits": circ.num_qubits, "detectors": circ.num_detectors, "observables": circ.num_observables,
                     "dem_mechanisms": full.notes["raw_mechanisms"], "sector_rows": sector.nrows,
                     "sector_columns": sector.ncols, "sector_reduction_exact": exact,
                     "collapsed_rows": coll.nrows, "collapsed_columns": coll.ncols}}
    log(name, res["model"], f"({time.time() - t0:.1f}s)")
    assert exact, "sector reduction is only a relaxation for this circuit"

    def save():
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)

    def verify(sector_cols):
        raw = replay.lift_to_dem(full, sector, sector_cols)
        dets, obs, terms = replay.check_in_dem(circ, raw)
        faults = replay.physical_faults(circ, raw)
        d2, o2 = replay.replay(circ, faults)
        ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
        return {"weight": len(raw), "dem_error_indices": raw, "dem_errors": terms,
                "dem_check": {"detectors": dets, "observables": obs},
                "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement", "stack")}
                                    for f in faults],
                "replay": {"fired_detectors": d2, "flipped_observables": o2}, "verified": ok}

    cperms = mod.translations(size) if hasattr(mod, "translations") else []
    # lifting one representative per orbit needs the real problem to have the same symmetries
    ssym0, _ = sym_of(sector, cperms)
    res["sector_symmetries_kept"] = ssym0.get("n_symmetries_kept") if ssym0.get("ok") else None
    res["symmetries_expected"] = len(cperms)
    sector_symmetric = res["sector_symmetries_kept"] == len(cperms)
    log(f"translation symmetries of the sector problem: {res['sector_symmetries_kept']} of {len(cperms)}")
    # ---------------- collapsed relaxation
    sym, kw = sym_of(coll, cperms)
    st = {"rows": coll.nrows, "columns": coll.ncols, "k_table": k_coll,
          "orbits": len(sym["anchors"]) if sym.get("ok") else None, "runs": []}
    res["collapsed"] = st
    res["certified_lower_bound"] = 1

    def on_run(rec):
        st["runs"].append({"K": rec["K"], "status": rec["status"], "best": rec["best"], "nodes": sum(rec["nodes"]),
                           "false_hits": rec["false_hits"], "seconds": round(rec["seconds"], 2)})
        if rec["status"] == "exhausted" and rec["best"] is None:
            res["certified_lower_bound"] = rec["K"] + 1
        save()

    # first pass stops at the first solution: enough for the lower bound
    r = dist(coll, k_table=k_coll, kmax=kmax, time_limit=time_limit, enum_all=False, log=log, on_run=on_run, **kw)
    st["distance"] = r["distance"]
    res["certified_lower_bound"] = r["lower_bound"]
    log(f"[collapsed] distance={r['distance']} lower bound={r['lower_bound']}")
    save()
    if r["distance"] is None:
        log("collapsed search did not finish; stopping")
        return
    d_coll = r["distance"]
    colmaps = sym.get("colmaps", []) if sym.get("ok") else []
    best = None
    # ---------------- quick upper bounds at weight d_coll: the solutions just found, then one-layer windows
    for sol in r["solutions"][:20]:
        w, cols = lift_multi(sector, coll, sol, 0, 600, start=res["certified_lower_bound"])
        if w not in (None, "timeout"):
            best = (w, cols)
            break
    if best is None:
        for tw in (0, 1):
            win = problem.window_problem(sector, tw, tw)
            wsym, wkw = sym_of(win, cperms)
            rw = dist(win, k_table=2, kmax=d_coll, time_limit=time_limit or 1800, log=log, start=d_coll, **wkw)
            res[f"window_t{tw}_at_d_coll"] = {"columns": win.ncols, "distance": rw["distance"],
                                              "status": rw["runs"][-1]["status"] if rw["runs"] else None}
            if rw["distance"] is not None:
                best = (rw["distance"], [win.col_meta[j] for j in rw["solutions"][0]])
                break
    reps = []
    if best is None:
        # all minimum collapsed solutions, to decide whether weight d_coll is possible at all
        r = dist(coll, k_table=k_coll, kmax=d_coll, time_limit=time_limit, enum_all=True, log=log, start=d_coll,
                 **kw)
        if r["runs"][-1]["status"] != "exhausted":
            log("enumeration of minimum collapsed solutions did not finish")
            save()
            return
        if sector_symmetric:
            reps = lift.orbit_representatives(r["solutions"], colmaps)
        else:           # no symmetry argument available: lift every solution
            reps = [(x, 1) for x in sorted(lift.expand_orbits(r["solutions"], colmaps))]
        st["n_min_solution_orbits"] = len(reps)
        log(f"[collapsed] {len(reps)} orbits of minimum solutions; lifting")
    # ---------------- lifting
    lifts = {0: 0, 1: 0}
    for slack in ((0, 1) if best is None else ()):
        for rep, size_ in reps:
            w, cols = lift_multi(sector, coll, rep, slack, 600, start=res["certified_lower_bound"])
            if w == "timeout":
                lifts[slack] = None
                break
            if w is not None:
                lifts[slack] += 1
                if best is None or w < best[0]:
                    best = (w, cols)
                    break
        st[f"orbits_lifting_slack{slack}"] = lifts[slack]
        log(f"[lift] slack {slack}: {'a solution lifts' if lifts[slack] else 'no orbit lifts' if lifts[slack] == 0 else 'timeout'}")
        if slack == 0 and lifts[0] == 0:
            # a real solution of weight d_coll would project onto a minimum collapsed solution, one fault per class
            res["certified_lower_bound"] = d_coll + 1
        if best is not None:
            break
    if best is not None:
        w = verify(best[1])
        res["witness"] = w
        if w["verified"]:
            res["certified_upper_bound"] = w["weight"]
        log(f"[lift] real fault set of weight {w['weight']}: verified={w['verified']} "
            f"(replay detectors {w['replay']['fired_detectors']}, observables {w['replay']['flipped_observables'][:6]}...)")
    save()
    lb, ub = res["certified_lower_bound"], res.get("certified_upper_bound")
    if ub is None or ub > lb:
        # ---------------- one-round window (upper bound)
        win = problem.window_problem(sector, 1, 1)
        wsym, wkw = sym_of(win, cperms)
        log(f"[window t=1] columns={win.ncols}")
        rw = dist(win, k_table=2, kmax=(ub - 1) if ub else kmax, time_limit=time_limit or 3600, log=log, start=lb,
                  **wkw)
        res["window_t1"] = {"columns": win.ncols, "distance": rw["distance"], "lower_bound": rw["lower_bound"],
                            "runs": [{k: x[k] for k in ("K", "status", "best", "nodes", "seconds")} for x in rw["runs"]]}
        if rw["distance"] is not None:
            w = verify([win.col_meta[j] for j in rw["solutions"][0]])
            res["window_t1"]["witness_verified"] = w["verified"]
            if w["verified"] and (ub is None or w["weight"] < ub):
                res["witness"] = w
                res["certified_upper_bound"] = ub = w["weight"]
        save()
    if do_full and (ub is None or ub > lb):
        # ---------------- the real sector problem, pruned by the collapsed table
        ssym, skw = sym_of(sector, cperms)
        log(f"[sector] rows={sector.nrows} columns={sector.ncols}")
        st2 = {"runs": []}
        res["sector"] = st2

        def on_run2(rec):
            st2["runs"].append({"K": rec["K"], "status": rec["status"], "best": rec["best"],
                                "nodes": sum(rec["nodes"]), "seconds": round(rec["seconds"], 2)})
            if rec["status"] == "exhausted" and rec["best"] is None:
                res["certified_lower_bound"] = max(res["certified_lower_bound"], rec["K"] + 1)
            save()

        ctab = search.Table(coll, k_coll, seed=777, labelfree=True)
        try:
            rs = dist(sector, k_table=2, kmax=(ub - 1) if ub else kmax, time_limit=time_limit, log=log, start=lb,
                      relaxed=[(ctab, coll.image)], on_run=on_run2, **skw)
        finally:
            ctab.free()         # callers that evaluate many circuits in one process would otherwise leak the table
        if rs["distance"] is not None:
            w = verify(list(rs["solutions"][0]))
            if w["verified"]:
                res["witness"] = w
                res["certified_upper_bound"] = w["weight"]
                res["certified_lower_bound"] = max(res["certified_lower_bound"], rs["distance"])
        elif rs["runs"] and rs["runs"][-1]["status"] == "exhausted":
            res["certified_lower_bound"] = max(res["certified_lower_bound"], rs["lower_bound"])
    res["seconds"] = round(time.time() - t0, 1)
    save()
    log("done", {k: res.get(k) for k in ("code", "basis", "certified_lower_bound", "certified_upper_bound", "seconds")})


if __name__ == "__main__":
    main(*sys.argv[1:])
