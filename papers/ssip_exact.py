"""SSIP's gross-code benchmarks (arXiv:2407.09423; github.com/CQCL/SSIP, benchmarking/gross_code_*.py) rerun with exact
distances in place of QDistRnd.

SSIP's subsystem_distance_GAP returns the smaller of two QDistRnd upper bounds, DistRandCSS([PZ; gauge Zs], PX) and
DistRandCSS([PX; gauge Xs], PZ).  DistRandCSS(P, Q) is the least weight of a vector orthogonal to the rows of P and
independent of the rows of Q (QDistRnd manual, Sec. 3.1), so these are the bare distances: the least weight of an
operator that commutes with the stabilizers and with the gauge logicals of the other type and is not a stabilizer.
Here both are computed exactly, and the scripts choose their merge depth from the exact values.  Each call also
records the dressed distances, over ker(PZ) minus rowsp([PX; gauge Xs]) and ker(PX) minus rowsp([PZ; gauge Zs]):
operators that commute with the stabilizers and are not in the gauge group.  Dressed <= bare; they agree when a merge
leaves no gauge qubit.

Every distance comes from the weight-bounded search up to KMAX (12 by default: a search that exhausts 12 reports
13 as a lower bound), and every lightest operator is checked against the matrices.  With --dressed the scripts choose
their merge depth from the dressed distance instead, the quantity of SSIP's Appendix A.

Usage: python papers/ssip_exact.py PATH/TO/SSIP SCRIPT OUT_DIR [KMAX] [--dressed]
    SCRIPT is a file name in SSIP's benchmarking/, e.g. gross_code_ext_merges.py; OUT_DIR receives its results/ files
    and calls.jsonl, one line per distance call.
"""
import json
import os
import runpy
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import stabcode
from cdist import search
from cdist.problem import Problem, dedupe

KMAX = 12
MAX_CALLS = 2000
LOG = None
CALLS = 0
STEER = "bare"


def least_weight(P, Q, n):
    """Least weight of c with P c = 0 and c outside rowsp(Q), for P Q^T = 0; returns (value or None, lower bound,
    witness)."""
    assert all(stabcode.parity(a & b) == 0 for a in P for b in Q)
    basis, pivots = stabcode.rref(list(P))
    R = []
    for v in stabcode.nullspace(Q, n):
        w = v
        for b, p in zip(basis, pivots):
            if (w >> p) & 1:
                w ^= b
        if w:
            R.append(v)
            basis, pivots = stabcode.rref(basis + [w])
    if not R:                                                 # no logical operator outside rowsp(Q)
        return None, 999, None
    h = [sum(1 << i for i, r in enumerate(P) if (r >> j) & 1) for j in range(n)]
    l = [sum(1 << i for i, r in enumerate(R) if (r >> j) & 1) for j in range(n)]
    hh, ll, cm = dedupe(h, l, [("q", j) for j in range(n)])
    p = Problem("ssip", len(P), len(R), hh, ll, [(i, 0) for i in range(len(P))], cm)
    r = search.distance(p, k_table=2, kmax=KMAX, labelfree=True)
    if r["distance"] is None:
        return None, r["lower_bound"], None
    cols = r["solutions"][0]
    qubits = sorted(j for c in cols for _, j in ([cm[c]] if isinstance(cm[c], tuple) else cm[c][:1]))
    e = sum(1 << j for j in qubits)
    ok = (len(qubits) == r["distance"] and all(stabcode.parity(a & e) == 0 for a in P)
          and stabcode.rank(list(Q) + [e]) == stabcode.rank(Q) + 1)
    assert ok, "witness check failed"
    return r["distance"], r["distance"], qubits


def exact_subsystem_distance(C, gauge_Zs, gauge_Xs, *args, **kwargs):
    global CALLS
    CALLS += 1
    if CALLS > MAX_CALLS:
        raise RuntimeError("call budget exhausted")
    PX, PZ = stabcode.rows_to_ints(C.PX), stabcode.rows_to_ints(C.PZ)
    GX, GZ = stabcode.rows_to_ints(gauge_Xs) if len(gauge_Xs) else [], stabcode.rows_to_ints(gauge_Zs) if len(gauge_Zs) else []
    n = C.PX.shape[1]
    t0 = time.time()
    rec = {"call": CALLS, "n": n, "rank_PX": stabcode.rank(PX), "rank_PZ": stabcode.rank(PZ), "gauge": len(GX)}
    rec["k"] = n - rec["rank_PX"] - rec["rank_PZ"]
    bare = [least_weight(PZ + GZ, PX, n), least_weight(PX + GX, PZ, n)]
    dressed = bare if not GX and not GZ else [least_weight(PZ, PX + GX, n), least_weight(PX, PZ + GZ, n)]
    for name, pair in (("bare", bare), ("dressed", dressed)):
        rec[name] = [{"value": v, "lower_bound": lb} for v, lb, _ in pair]
        rec[name + "_witness"] = [w for _, _, w in pair]
    rec["seconds"] = round(time.time() - t0, 2)
    LOG.write(json.dumps(rec) + "\n")
    LOG.flush()
    print(f"  exact call {CALLS}: n={n} k={rec['k']} gauge={rec['gauge']} bare={[x['value'] or ('>=%d' % x['lower_bound']) for x in rec['bare']]} "
          f"dressed={[x['value'] or ('>=%d' % x['lower_bound']) for x in rec['dressed']]} {rec['seconds']}s", flush=True)
    return min(lb for _, lb, _ in (bare if STEER == "bare" else dressed))


if __name__ == "__main__":
    if "--dressed" in sys.argv:
        sys.argv.remove("--dressed")
        STEER = "dressed"
    repo, script, out = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
    if len(sys.argv) > 4:
        KMAX = int(sys.argv[4])
    sys.path.insert(0, repo)
    import ssip.distance
    ssip.distance.subsystem_distance_GAP = exact_subsystem_distance
    os.makedirs(os.path.join(out, "results"), exist_ok=True)
    LOG = open(os.path.join(out, "calls.jsonl"), "a")
    os.chdir(out)
    runpy.run_path(os.path.join(repo, "benchmarking", script), run_name="__main__")
