"""Circuit distance of a mitten code under its published SE schedule.

The distance problem is built directly from the published matrices and
schedule (mitten_effective.py); because the X-check and Z-check rounds are
sequential it is the circuit-level problem itself.  A minimum-weight solution
is then mapped onto the Stim memory circuit (mitten_circuit.py), checked in
the full DEM and replayed physically.

Usage: python papers/run_mitten.py "[[150,30,10]]" Z out.json [kmax] [k_table] [seconds_per_threshold] [verify_rounds] [start]

A code of another family of the same repository is named with its folder, e.g.
"structured_mitten/[[300,60,9]]" (papers/mitten/structured_mitten/).
"""
import json
import os
import sys
import time

import stim

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mitten_circuit
import mitten_effective
import mitten_symmetry
from cdist import multi, problem, replay, search


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


PREFIX = {"mitten": "mitten", "structured_mitten": "smitten"}


def code_of(name):
    """"[[150,30,10]]" or "structured_mitten/[[300,60,9]]" -> (code folder, circuit file stem, (n, k, d)).
    The stem is mitten<n> for the mitten family, as before; <prefix><n>d<d> otherwise (two structured
    mitten codes share n = 600)."""
    family, _, code = name.rpartition("/")
    family = family or "mitten"
    n, k, d = [int(x) for x in code.strip("[]").split(",")]
    tag = PREFIX[family] + str(n) + ("" if family == "mitten" else "d%d" % d)
    return os.path.join(HERE, "mitten", family, code), tag, (n, k, d)


def verify_on_circuit(code_dir, tag, basis, rounds, eff, sol):
    """Map solution columns onto the Stim circuit and replay them."""
    path = os.path.join(os.path.dirname(HERE), "circuits", "papers", f"{tag}_r{rounds}_{basis}.stim")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    circ = mitten_circuit.build(code_dir, basis, rounds)
    circ.to_file(path)
    full = problem.load_dem_problem(path)
    sector = problem.sector_problem(full)
    assert problem.sector_is_exact(full, sector)
    tw = 0 if basis == "Z" else 1
    win = problem.window_problem(sector, tw, tw)
    # window rows -> check index
    bit = [int(m[0]) for m in win.row_meta]
    table = {}
    for j, (a, b) in enumerate(zip(win.h, win.l)):
        key = 0
        x = a
        while x:
            low = x & -x
            key |= 1 << bit[low.bit_length() - 1]
            x ^= low
        table[(key, b)] = j
    cols = [win.col_meta[table[(eff.h[j], eff.l[j])]] for j in sol]
    raw = replay.lift_to_dem(full, sector, cols)
    dets, obs, terms = replay.check_in_dem(circ, raw)
    faults = replay.physical_faults(circ, raw)
    d2, o2 = replay.replay(circ, faults)
    ok = (not dets) and bool(obs) and (not d2) and (o2 == obs) and len(set(raw)) == len(raw)
    return {"circuit": os.path.relpath(path, os.path.dirname(HERE)), "rounds": rounds, "weight": len(raw),
            "dem_check": {"detectors": dets, "observables": obs},
            "physical_faults": [{k: f[k] for k in ("tick", "instruction", "paulis", "flipped_measurement", "stack")}
                                for f in faults],
            "replay": {"fired_detectors": d2, "flipped_observables": o2}, "verified": ok,
            "collapsed_columns_equal_window_columns": set(table) == set(zip(eff.h, eff.l))}


def main(name, basis, out, kmax=12, k_table=2, time_limit=0, verify_rounds=0, start=1):
    kmax, k_table, time_limit, verify_rounds, start = int(kmax), int(k_table), float(time_limit), int(verify_rounds), int(start)
    code_dir, tag, (n, k, d) = code_of(name)
    eff = mitten_effective.effective_problem(code_dir, basis)
    sym = mitten_symmetry.find(eff, code_dir)
    res = {"code": name, "basis": basis, "claimed_distance": d, "threads": search.lib().gm_num_threads(),
           "rows": eff.nrows, "columns": eff.ncols, "observables": eff.nobs,
           "symmetries": sym["n_symmetries_kept"] + 1, "orbits": len(sym["anchors"]), "runs": []}
    log(name, basis, {x: res[x] for x in ("rows", "columns", "observables", "symmetries", "orbits")})

    def save():
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)

    def on_run(rec):
        res["runs"].append(rec)
        if rec["status"] == "exhausted" and rec["best"] is None:
            res["certified_lower_bound"] = rec["K"] + 1
        save()

    r = multi.distance(eff, k_table=k_table, kmax=kmax, rank=sym["rank"], anchors=sym["anchors"],
                       time_limit=time_limit, log=log, on_run=on_run, start=start)
    res["certified_lower_bound"] = r["lower_bound"]
    res["distance"] = r["distance"]
    if r["distance"] is not None:
        sol = r["solutions"][0]
        res["solution_faults"] = [list(eff.col_meta[j][0]) for j in sol]
        rounds = verify_rounds or d
        w = verify_on_circuit(code_dir, tag, basis, rounds, eff, sol)
        res["witness"] = w
        if w["verified"]:
            res["certified_upper_bound"] = w["weight"]
        log(f"circuit distance {r['distance']} (claimed code distance {d}); witness on the {rounds}-round circuit "
            f"verified={w['verified']}, replay detectors={w['replay']['fired_detectors']}")
    else:
        log(f"no solution up to {r['lower_bound'] - 1}: certified lower bound {r['lower_bound']}")
    save()


if __name__ == "__main__":
    main(*sys.argv[1:])
