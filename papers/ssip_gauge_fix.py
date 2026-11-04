"""Are the gauge qubits of SSIP's merged codes fixed by the preparation of the new qubits?

Reruns one of SSIP's gross-code benchmark scripts (benchmarking/gross_code_*.py) as papers/ssip_exact.py does, but
replays the exact bare distances that papers/ssip_exact.py recorded (REFERENCE_CALLS, its calls.jsonl), so that the
script builds the same merged codes at the same depths without computing distances again.  For each merged code, with
the original blocks in a code state:
- with the new qubits in |0>, a Z-type operator has a definite value iff its restriction to the original qubits lies in
  the span of the original Z checks; with the new qubits in |+>, likewise for X-type operators;
- the preparation is the one under which every merged check of that type is definite: |0> for X measurements, whose
  Z checks reach onto the new qubits, and |+> for Z measurements;
- then the test is whether every gauge logical of that type is definite.  Gauge logicals commute with every check, so
  they keep these values through the merge, and measuring the new qubits out at the split recovers them.
When they are, the merged code acts as the stabilizer code with those gauge logicals added as checks, whose distance is
the bare distance in the measured basis and the dressed distance in the other basis (both in REFERENCE_CALLS).

Usage: python papers/ssip_gauge_fix.py PATH/TO/SSIP SCRIPT REFERENCE_CALLS OUT_DIR
    writes OUT_DIR/gauge.jsonl, one line per distance call, in the order of REFERENCE_CALLS.
"""
import json
import os
import runpy
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import stabcode

REF = []
REG = []
LOG = None
CALLS = 0
GROSS = None


def reducer(M):
    """Membership test for the row space of M over GF(2)."""
    basis, pivots = stabcode.rref(stabcode.rows_to_ints(M))

    def inside(v):
        w = stabcode.rows_to_ints(v[None, :])[0]
        for b, p in zip(basis, pivots):
            if (w >> p) & 1:
                w ^= b
        return w == 0
    return inside


def gauge_check(C, gauge_Zs, gauge_Xs, *args, **kwargs):
    global CALLS
    CALLS += 1
    ref = REF[CALLS - 1]
    mr = next((r for r in reversed(REG) if r.NewZLogicals is gauge_Zs and r.NewXLogicals is gauge_Xs), None)
    assert mr is not None, "no merge result for this call"
    PX, PZ = np.array(C.PX, dtype=np.uint8) % 2, np.array(C.PZ, dtype=np.uint8) % 2
    GX = np.array(gauge_Xs, dtype=np.uint8).reshape(-1, PX.shape[1]) % 2
    GZ = np.array(gauge_Zs, dtype=np.uint8).reshape(-1, PX.shape[1]) % 2
    n = PX.shape[1]
    M = np.array(mr.MergeMap, dtype=np.uint8) % 2          # merged qubit i <- original qubit j where M[i, j] = 1
    assert M.shape[0] == n and (M.sum(axis=0) == 1).all() and M.shape[1] % GROSS[0].shape[1] == 0
    old = [int(np.argmax(M[:, j])) for j in range(M.shape[1])]
    # the test needs only the images of the original qubits; SSIP's parallel merges list their new qubits as if
    # appended after the original ones, which the merge map need not follow, so only their number is compared
    assert len(set(old)) == len(old) and n - len(old) == len(mr.NewQubits)
    blocks = M.shape[1] // GROSS[0].shape[1]
    origZ = np.kron(np.eye(blocks, dtype=np.uint8), GROSS[0])
    origX = np.kron(np.eye(blocks, dtype=np.uint8), GROSS[1])
    inZ, inX = reducer(origZ), reducer(origX)
    defZ = lambda v: inZ(v[old])                            # definite with the new qubits in |0>
    defX = lambda v: inX(v[old])                            # definite with the new qubits in |+>
    rec = {"call": CALLS, "n": n, "gauge": len(GX), "blocks": blocks, "new_qubits": len(mr.NewQubits),
           "Z_checks_definite_with_0": all(defZ(r) for r in PZ), "X_checks_definite_with_plus": all(defX(r) for r in PX),
           "gauge_Z_definite_with_0": int(sum(defZ(g) for g in GZ)), "gauge_X_definite_with_plus": int(sum(defX(g) for g in GX))}
    assert (rec["n"], rec["gauge"]) == (ref["n"], ref["gauge"]), "replay diverged from the reference calls"
    LOG.write(json.dumps(rec) + "\n")
    LOG.flush()
    print(f"  call {CALLS}: n={n} gauge={rec['gauge']} Z checks definite with |0> {rec['Z_checks_definite_with_0']}, "
          f"X checks with |+> {rec['X_checks_definite_with_plus']}; definite gauge Z {rec['gauge_Z_definite_with_0']}, "
          f"gauge X {rec['gauge_X_definite_with_plus']}", flush=True)
    return min(x["value"] if x["value"] is not None else x["lower_bound"] for x in ref["bare"])


if __name__ == "__main__":
    repo, script, ref_path, out = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3]), os.path.abspath(sys.argv[4])
    REF = [json.loads(l) for l in open(ref_path)]
    sys.path.insert(0, repo)
    import ssip.distance
    import ssip.merge_result
    from ssip.lifted_product import bivariate_bicycle_code

    init = ssip.merge_result.MergeResult.__init__

    def registered_init(self, *a, **k):
        init(self, *a, **k)
        REG.append(self)
        del REG[:-8]
    ssip.merge_result.MergeResult.__init__ = registered_init
    ssip.distance.subsystem_distance_GAP = gauge_check
    gross = bivariate_bicycle_code(12, 6, ([3], [1, 2]), ([1, 2], [3]))
    GROSS = (np.array(gross.PZ, dtype=np.uint8) % 2, np.array(gross.PX, dtype=np.uint8) % 2)
    os.makedirs(os.path.join(out, "results"), exist_ok=True)
    LOG = open(os.path.join(out, "gauge.jsonl"), "w")
    os.chdir(out)
    runpy.run_path(os.path.join(repo, "benchmarking", script), run_name="__main__")
    assert CALLS == len(REF), "fewer calls than the reference"
