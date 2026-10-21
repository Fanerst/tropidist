"""Exact code distances of the Cornucopia codes (arXiv:2608.02773, Tab. 1), both CSS sectors.

The check matrices are rebuilt by papers/cornucopia.py.  Each sector is searched with the label-free search
(full-budget reconstruction), the covering bound and the column translations y -> y + c of the code, which
are verified as symmetries of the sector problem before use.

Every check of H_X and of H_Z has twelve qubits and every qubit lies in three checks of each type, so the sum
of all rows of either matrix is the all-ones vector.  Every logical operator is orthogonal to it and has even
weight.  With --parity (default) odd thresholds are not searched: threshold 2t+1 adds nothing to 2t.

usage: python scripts/cornucopia_code_distance.py out.json q[,q...] [sectors=XZ] [seconds per threshold]
       [--no-parity]
"""
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "papers")]
import cornucopia
import stabcode
from cdist import search, symmetry

NAME = {"X": "d_Z", "Z": "d_X"}      # internal sector (checks of that type) -> distance it computes


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def is_logical(w, checks, other):
    """w commutes with `checks` and is not a product of `other` (the stabilizers of its own type)."""
    return all(bin(w & r).count("1") % 2 == 0 for r in checks) and stabcode.rank(other + [w]) > stabcode.rank(other)


def run(q, sector, seconds, parity):
    hx, hz, n = cornucopia.matrices(q)
    _, k = stabcode.css_parameters(hx, hz, n)
    ones = (1 << n) - 1
    other = hz if sector == "X" else hx                  # same-type stabilizers of the logical operators searched
    even = stabcode.rank(other + [ones]) == stabcode.rank(other)
    p = stabcode.css_distance_problem(hx, hz, n, sector, name="cornucopia_%d_%s" % (n, sector))
    sym = symmetry.from_row_perms(p, cornucopia.translations(q))
    assert sym.get("ok"), sym
    kw = {"rank": sym["rank"], "anchors": sym["anchors"]}
    rec = {"q": q, "n": n, "k": k, "claimed": list(cornucopia.CODES[q][2]), "sector": sector,
           "distance_name": NAME[sector], "rows": p.nrows, "columns": p.ncols, "labels": p.nobs,
           "translations_kept": sym["n_symmetries_kept"],
           "orbits": len(sym["anchors"]), "all_ones_is_stabilizer": even, "parity_skip": parity and even,
           "runs": []}
    t0 = time.time()
    lower, found = 0, None
    S = search.Searcher(p, rank=kw["rank"], anchors=kw["anchors"], labelfree=True)
    S.build_exclusions()
    tab = search.Table(p, 3 if n <= 400 else 2, labelfree=True)
    S.add_table(tab, exact=True)
    rec["k_table"], rec["table_entries"], rec["table_seconds"] = tab.k, tab.entries, round(tab.build_seconds, 2)
    for K in range(1, search.DMAX + 1):
        if parity and even and K % 2 == 1:
            rec["runs"].append({"K": K, "status": "excluded by parity"})
            lower = K
            continue
        r = S.search(K, time_limit=seconds, cover=True)
        run_rec = {x: r[x] for x in ("K", "status", "nodes", "lookups", "hits", "false_hits", "seconds")}
        run_rec["seconds"] = round(run_rec["seconds"], 2)
        run_rec["nodes"] = int(sum(r["nodes"]))
        rec["runs"].append(run_rec)
        log(f"  q={q} {NAME[sector]} K={K}: {r['status']} {r['seconds']:.1f}s nodes={run_rec['nodes']} "
            f"false_hits={r['false_hits']}")
        if r["status"] == "exhausted":
            lower = K
        elif r["status"] == "found":
            found = list(r["solutions"][0])
            break
        else:
            break
    rec["lower_bound"] = lower + 1 if found is None else len(found)
    rec["distance"] = len(found) if found else None
    if found:
        w = sum(1 << j for j in found)
        checks = hx if sector == "X" else hz
        assert search.verify(p, found) and is_logical(w, checks, other), "witness failed verification"
        rec["witness"] = found
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main(argv):
    parity = "--no-parity" not in argv
    argv = [a for a in argv if a != "--no-parity"]
    out, qs = argv[0], [int(x) for x in argv[1].split(",")]
    sectors = argv[2] if len(argv) > 2 else "XZ"
    seconds = float(argv[3]) if len(argv) > 3 else 0.0
    res = {"paper": "arXiv:2608.02773 (Cornucopia codes)", "host": socket.gethostname(),
           "kernel_sha256": hashlib.sha256((ROOT / "cdist" / "gmitm.c").read_bytes()).hexdigest(),
           "threads": search.lib().gm_num_threads(), "seconds_per_threshold": seconds, "codes": []}
    if os.path.exists(out):
        res["codes"] = json.load(open(out)).get("codes", [])
    done = {(c["q"], c["sector"]) for c in res["codes"] if c.get("distance")}
    for q in qs:
        for s in sectors:
            if (q, s) in done:
                continue
            log(f"q={q} [[{cornucopia.CODES[q][2]}]] sector {s} ({NAME[s]})")
            rec = run(q, s, seconds, parity)
            res["codes"] = [c for c in res["codes"] if (c["q"], c["sector"]) != (q, s)] + [rec]
            with open(out + ".tmp", "w") as f:
                json.dump(res, f, indent=1)
            os.replace(out + ".tmp", out)
            log(f"q={q} {NAME[s]} = {rec['distance']} (lower bound {rec['lower_bound']}), {rec['seconds']}s")


if __name__ == "__main__":
    main(sys.argv[1:])
