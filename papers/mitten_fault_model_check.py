"""Fault-model check for the mitten circuits of arXiv:2607.28795 (docs/AUDIT.md).

The circuit distances of the published hook-free schedules (docs/PAPERS.md) were computed with the noise of the
paper's simulations: a two-qubit depolarizing fault after every CX, and preparation and measurement faults. The
paper's distance estimator, sQetch, used single-qubit Pauli faults. This script builds every published circuit
under three fault models and compares their memory-sector problems column by column:

  two           the simulation model above (what the published runs used);
  single        single-qubit depolarizing faults on both qubits of every CX, with the same preparation and
                measurement faults;
  single_gates  single-qubit faults after the CX gates only.

Two problems with the same set of columns (detector pattern, logical action) have the same distance. The
argument behind it: the X-check and Z-check rounds run one after the other, so within a memory sector the part
of a two-qubit fault that matters is a single-qubit fault or the hook of a single-qubit ancilla fault one gate
earlier.

single_gates is a sub-model of the other two (each of its faults is a weight-1 fault there), so its distance is
at least theirs; a recorded witness made of single-qubit Paulis after CX gates only is also a witness for it.
The script lists, for every witness in results/papers/mitten*.json, the kinds of faults it uses. The direct exact
runs under single_gates (`exact_single_gates` in the results) are the pipeline (bench/adapters/ours_pipeline.py,
dp=2) on the sector problem of the 3-round circuit, exported with export_circuit_instance of bench/common.py;
threads and symmetries are in each record.

usage: python papers/mitten_fault_model_check.py [rounds] [code ...]   -> results/papers/mitten_fault_models.json
"""
import collections
import glob
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]

import mitten_circuit
from cdist import problem

CODES = ["[[150,30,10]]", "[[200,40,12]]", "[[300,60,14]]", "[[500,100,16]]", "[[540,108,18]]", "[[630,126,20]]",
         "[[780,156,22]]", "[[975,195,24]]"]
MODELS = {"two": dict(), "single": dict(gate_noise="single"), "single_gates": dict(gate_noise="single", prep_meas=False)}


def sector_columns(code, basis, rounds, kw, tmp):
    circ = mitten_circuit.build(os.path.join(HERE, "mitten", "mitten", code), basis, rounds, **kw)
    path = os.path.join(tmp, "c.stim")
    circ.to_file(path)
    q = problem.sector_problem(problem.load_dem_problem(path))
    return set(zip(q.h, q.l)), q.nrows


def witness_faults():
    """Fault kinds of every recorded witness. In these circuits (no idle noise) DEPOLARIZE1 sits only at preparation
    and measurement; a single-qubit Pauli of a DEPOLARIZE2 is a single-qubit fault after a CX, in all three models."""
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "papers", "mitten*.json"))):
        r = json.load(open(path))
        w = r.get("witness") if isinstance(r, dict) else None
        if not w or "physical_faults" not in w:
            continue
        kinds = collections.Counter("two_qubit" if len(f["paulis"]) > 1 else
                                    "after_cx" if f["instruction"] == "DEPOLARIZE2" else "prep_meas"
                                    for f in w["physical_faults"])
        out[os.path.basename(path)] = dict(circuit=w.get("circuit", r.get("circuit")), weight=w["weight"],
                                           verified=w.get("verified"), faults=dict(kinds),
                                           in_single_gates=set(kinds) == {"after_cx"})
    return out


def main(rounds=3, codes=None):
    out_path = os.path.join(ROOT, "results", "papers", "mitten_fault_models.json")
    res = json.load(open(out_path)) if os.path.exists(out_path) else {}
    res["witnesses"] = witness_faults()
    with tempfile.TemporaryDirectory() as tmp:
        for code in codes or CODES:
            for basis in ("Z", "X"):
                cols = {m: sector_columns(code, basis, rounds, kw, tmp) for m, kw in MODELS.items()}
                two, single, gates = cols["two"][0], cols["single"][0], cols["single_gates"][0]
                rec = dict(rounds=rounds, rows=cols["two"][1], columns={m: len(c[0]) for m, c in cols.items()},
                           single_equals_two=single == two, single_gates_equals_two=gates == two,
                           single_gates_subset_of_two=gates <= two, only_in_two=len(two - single),
                           only_in_single=len(single - two), only_in_two_not_gates=len(two - gates))
                res.setdefault("sector_columns", {})["%s %s r%d" % (code, basis, rounds)] = rec
                print(code, basis, json.dumps(rec), flush=True)
                json.dump(res, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3, sys.argv[2:] or None)
