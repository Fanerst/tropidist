"""Code distances (data errors only) of the structured-mitten codes and of the abelian lifted-product code
[[560,112,14]] of arXiv:2607.28795, from the authors' matrices (github.com/a7b/yarn; papers/mitten/, commit and
sha256 in papers/mitten/manifest.json).

basis Z: X-type logical operators (Hz e = 0, e flips a Z logical), the distance d_X that bounds the Z-basis memory;
basis X: Z-type operators, d_Z.

Upper bound: an information-set search (cdist.isd); the operator found is checked against the published matrices
(Hz e = 0 and e Lz^T != 0 for basis Z; Hx e = 0 and e Lx^T != 0 for basis X). Lower bound: exhaustive iterative
deepening (cdist.multi) up to one below that weight, with the symmetries that cdist.symmetry.from_row_perms
verifies among the group translations e -> u e v of every check block (all u, v in G, from the multiplication table
of the schedule file) or, for the abelian code, the cyclic shifts of its 28-row blocks. [[1200,240,20]] ships no
schedule, hence no group table: it is searched without symmetry.

usage: python papers/smitten_code_distance.py FAMILY/CODE BASIS out.json [kmax] [seconds_per_threshold] [isd_seconds] [k_table]
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]

import stabcode
from cdist import isd, multi, search, symmetry


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def rows(H):
    return [int("".join("1" if x else "0" for x in r[::-1]), 2) for r in np.asarray(H, dtype=np.uint8)]


def candidates(code_dir, nrows, Hx):
    """Row permutations to try: e -> u e v on every block of |G| checks; for the abelian code (|G| = 28, element
    numbering not given), the index maps of its single-element blocks of Hx (multiplication by that element)."""
    path = os.path.join(code_dir, "hook_free_SE_cycle_schedule.json")
    if os.path.exists(path):
        mul = json.load(open(path))["group"]["multiplication_table"]
        g = len(mul)
        for u in range(g):
            for v in range(g):
                yield [b * g + mul[mul[u][e]][v] for b in range(nrows // g) for e in range(g)]
    elif "abelian_poly_LP" in code_dir:
        g = 28
        for b in range(Hx.shape[0] // g):
            for c in range(Hx.shape[1] // g):
                blk = Hx[b * g:(b + 1) * g, c * g:(c + 1) * g]
                if (blk.sum(1) == 1).all():
                    pi = blk.argmax(1)
                    yield [r * g + int(pi[e]) for r in range(nrows // g) for e in range(g)]


def check_operator(H, basis, qubits):
    """qubits: support of the operator. Returns (commutes with the opposite checks, flips a published logical)."""
    e = np.zeros(H["Hx"].shape[1], dtype=np.int64)
    e[list(qubits)] = 1
    det, lg = (H["Hz"], H["Lz"]) if basis == "Z" else (H["Hx"], H["Lx"])
    return not ((det.astype(np.int64) @ e) % 2).any(), bool(((lg.astype(np.int64) @ e) % 2).any())


def main(name, basis, out, kmax=30, seconds=0, isd_seconds=600, k_table=2):
    kmax, seconds, isd_seconds, k_table = int(kmax), float(seconds), float(isd_seconds), int(k_table)
    family, _, code = name.rpartition("/")
    code_dir = os.path.join(HERE, "mitten", family, code)
    H = {k: np.load(os.path.join(code_dir, k + ".npy")).astype(np.uint8) for k in ("Hx", "Hz", "Lx", "Lz")}
    n = H["Hx"].shape[1]
    hx, hz = rows(H["Hx"]), rows(H["Hz"])
    _, k = stabcode.css_parameters(hx, hz, n)
    p = stabcode.css_distance_problem(hx, hz, n, basis, name=code)
    res = {"code": name, "basis": basis, "operator_type": "X" if basis == "Z" else "Z", "n": n, "k": k,
           "named_distance": int(code.strip("[]").split(",")[2]), "rows": p.nrows, "columns": p.ncols,
           "threads": search.lib().gm_num_threads()}

    def save():
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(res, open(out + ".tmp", "w"), indent=1)
        os.replace(out + ".tmp", out)

    t = time.time()
    sym = symmetry.from_row_perms(p, candidates(code_dir, p.nrows, H["Hx"]))
    if not sym["ok"]:
        sym = {"ok": True, "orbit_sizes": [1], "rank": None, "anchors": None}
    # translations act freely on the qubits: the largest orbit is the order of the group the kept maps generate
    res.update(symmetries=max(sym["orbit_sizes"]), orbits=len(sym["anchors"]) if sym["anchors"] else p.ncols,
               symmetry_seconds=round(time.time() - t, 1))
    log(name, basis, {x: res[x] for x in ("n", "k", "rows", "columns", "symmetries", "orbits")})

    # upper bound: information-set search, operator checked against the published matrices
    best, best_sol, seed, t0 = None, None, 1, time.time()
    while time.time() - t0 < isd_seconds:
        w, sol = isd.search(p, start_best=best, time_limit=min(60.0, isd_seconds - (time.time() - t0)), seed=seed)
        seed += 1
        if w is not None:
            best, best_sol = w, sol
            log(f"  isd: weight {w} after {time.time() - t0:.0f}s")
    res["isd_seconds"] = round(time.time() - t0, 1)
    if best_sol is not None:
        assert search.verify(p, best_sol)
        qubits = sorted(q for j in best_sol for _, q in p.col_meta[j][:1])
        ok = check_operator(H, basis, qubits)
        res["witness"] = {"weight": len(qubits), "qubits": qubits, "commutes_with_checks": ok[0],
                          "flips_published_logical": ok[1]}
        if all(ok):
            res["certified_upper_bound"] = len(qubits)
    save()

    # lower bound: exhaustive search below the witness weight
    def on_run(rec):
        res.setdefault("runs", []).append(rec)
        if rec["status"] == "exhausted" and rec["best"] is None:
            res["certified_lower_bound"] = rec["K"] + 1
        save()

    top = min(kmax, res["certified_upper_bound"] - 1) if "certified_upper_bound" in res else kmax
    r = multi.distance(p, k_table=k_table, kmax=top, rank=sym["rank"], anchors=sym["anchors"], time_limit=seconds,
                       log=log, on_run=on_run)
    res["certified_lower_bound"] = r["lower_bound"]
    if r["distance"] is not None:
        qubits = sorted(q for j in r["solutions"][0] for _, q in p.col_meta[j][:1])
        ok = check_operator(H, basis, qubits)
        res["witness"] = {"weight": len(qubits), "qubits": qubits, "commutes_with_checks": ok[0],
                          "flips_published_logical": ok[1]}
        if all(ok):
            res["certified_upper_bound"] = len(qubits)
    if res.get("certified_upper_bound") == res["certified_lower_bound"]:
        res["distance"] = res["certified_lower_bound"]
    log(f"{name} {basis}: lower bound {res['certified_lower_bound']}, upper bound {res.get('certified_upper_bound')}")
    save()


if __name__ == "__main__":
    main(*sys.argv[1:])
