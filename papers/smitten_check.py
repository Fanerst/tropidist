"""Construction and fault-model checks for the structured-mitten circuits of arXiv:2607.28795 (docs/AUDIT.md).

The five structured-mitten codes of github.com/a7b/yarn that ship a hook-free schedule (papers/mitten/
structured_mitten/, commit in papers/mitten/manifest.json) are built with papers/mitten_circuit.py, as the mitten
codes. For every code and memory basis this script checks:

  - the schedule reproduces Hx and Hz, with disjoint gates in every layer (asserted by the builder), and Stim's
    detector error model exists, so every detector and observable is deterministic (Stim raises otherwise);
  - the sector reduction is exact;
  - the matrix-level problem of papers/mitten_effective.py has the same columns (detector pattern, logical action)
    as the time-collapsed Stim sector problem and as its single-round window, the map papers/run_mitten.py uses
    to lift a solution onto the circuit;
  - the sector problems under the fault models of papers/mitten_fault_model_check.py, and with idle data faults:
      two           a two-qubit depolarizing fault after every CX, preparation and measurement faults (the
                    paper's simulations; the model of all our runs);
      single        single-qubit depolarizing faults on both qubits of every CX instead (the paper's estimator);
      single_gates  single-qubit faults after the CX gates only (a sub-model of the other two);
      two_idle      two, plus a depolarizing fault on every data qubit that sits out a layer.
    Two problems with the same columns have the same distance.

`witnesses` lists the fault kinds of every witness in results/papers/smitten*.json. single_gates is a sub-model of
the other two (each of its faults is a weight-1 fault there), so its distance is at least theirs, and a witness
made of single-qubit Paulis right after CX gates is also a witness for it. A witness found on a 3-round circuit is
also replayed on the circuit with as many rounds as the named distance.

usage: python papers/smitten_check.py [rounds] [code ...]   -> results/papers/smitten_checks.json, key "circuits"
       python papers/smitten_check.py witnesses              -> the same file, key "witnesses"
"""
import collections
import glob
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]

import mitten_circuit
import mitten_effective
from cdist import problem

CODES = ["[[300,60,9]]", "[[330,66,12]]", "[[600,120,14]]", "[[600,120,16]]", "[[840,168,18]]"]
MODELS = {"two": dict(), "single": dict(gate_noise="single"),
          "single_gates": dict(gate_noise="single", prep_meas=False), "two_idle": dict(idle=True)}


def sector(code_dir, basis, rounds, kw, tmp):
    circ = mitten_circuit.build(code_dir, basis, rounds, **kw)
    path = os.path.join(tmp, "c.stim")
    circ.to_file(path)
    full = problem.load_dem_problem(path)          # detector_error_model raises on a non-deterministic detector
    q = problem.sector_problem(full)
    return circ, full, q


def window_columns(q, basis):
    """Columns of the single-round window of the sector problem with rows renamed to check indices (as in
    run_mitten.verify_on_circuit)."""
    tw = 0 if basis == "Z" else 1
    win = problem.window_problem(q, tw, tw)
    bit = [int(m[0]) for m in win.row_meta]
    out = set()
    for a, b in zip(win.h, win.l):
        key = 0
        while a:
            low = a & -a
            key |= 1 << bit[low.bit_length() - 1]
            a ^= low
        out.add((key, b))
    return out


def witness_faults():
    """Fault kinds of every recorded circuit witness. Without idle noise DEPOLARIZE1 sits only at preparation and
    measurement; a single-qubit Pauli of a DEPOLARIZE2 is a single-qubit fault right after a CX. A witness found on
    a circuit with fewer rounds than the named distance d is also replayed on the d-round circuit."""
    import run_mitten
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "papers", "smitten[0-9]*.json"))):
        r = json.load(open(path))
        w = r.get("witness")
        if not w or "physical_faults" not in w:
            continue
        kinds = collections.Counter("two_qubit" if len(f["paulis"]) > 1 else
                                    "after_cx" if f["instruction"] == "DEPOLARIZE2" else "prep_meas"
                                    for f in w["physical_faults"])
        rec = dict(circuit=w["circuit"], weight=w["weight"], verified=w["verified"], faults=dict(kinds),
                   in_single_gates=set(kinds) == {"after_cx"})
        code_dir, tag, (n, k, d) = run_mitten.code_of(r["code"])
        if w["rounds"] < d:
            eff = mitten_effective.effective_problem(code_dir, r["basis"])
            index = {tuple(m[0]): j for j, m in enumerate(eff.col_meta)}
            v = run_mitten.verify_on_circuit(code_dir, tag, r["basis"], d, eff,
                                             [index[tuple(x)] for x in r["solution_faults"]])
            rec["replayed_at_named_rounds"] = dict(rounds=d, weight=v["weight"], verified=v["verified"])
        out[os.path.basename(path)] = rec
    return out


def main(rounds=3, codes=None):
    out_path = os.path.join(ROOT, "results", "papers", "smitten_checks.json")
    res = json.load(open(out_path)) if os.path.exists(out_path) else {}
    if rounds == "witnesses":
        res["witnesses"] = witness_faults()
        print(json.dumps(res["witnesses"], indent=1))
        json.dump(res, open(out_path, "w"), indent=1)
        return
    circuits = res.setdefault("circuits", {})
    with tempfile.TemporaryDirectory() as tmp:
        for code in codes or CODES:
            code_dir = os.path.join(HERE, "mitten", "structured_mitten", code)
            for basis in ("Z", "X"):
                t0 = time.time()
                eff = mitten_effective.effective_problem(code_dir, basis)
                e = set(zip(eff.h, eff.l))
                cols, rec = {}, dict(rounds=rounds)
                for m, kw in MODELS.items():
                    circ, full, q = sector(code_dir, basis, rounds, kw, tmp)
                    cols[m] = set(zip(q.h, q.l))
                    if m == "two":
                        coll = problem.collapse_time(q)
                        rec.update(qubits=circ.num_qubits, detectors=circ.num_detectors,
                                   observables=circ.num_observables, raw_mechanisms=full.notes["raw_mechanisms"],
                                   full_columns=full.ncols, sector_rows=q.nrows, deterministic=True,
                                   sector_is_exact=problem.sector_is_exact(full, q),
                                   effective_columns=eff.ncols, collapsed_columns=coll.ncols,
                                   effective_equals_collapsed=e == set(zip(coll.h, coll.l)),
                                   effective_equals_window=e == window_columns(q, basis))
                two = cols["two"]
                rec.update(columns={m: len(c) for m, c in cols.items()},
                           single_equals_two=cols["single"] == two, single_gates_equals_two=cols["single_gates"] == two,
                           single_gates_subset_of_two=cols["single_gates"] <= two,
                           only_in_two_not_single_gates=len(two - cols["single_gates"]),
                           idle_equals_two=cols["two_idle"] == two, seconds=round(time.time() - t0, 1))
                circuits["%s %s r%d" % (code, basis, rounds)] = rec
                print(code, basis, json.dumps(rec), flush=True)
                json.dump(res, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "3"
    main(a if a == "witnesses" else int(a), sys.argv[2:] or None)
