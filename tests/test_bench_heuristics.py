"""Plain-script fixture checks for the upper-bound benchmark adapters.

Run: OMP_NUM_THREADS=2 .venv/bin/python tests/test_bench_heuristics.py
All generated records stay in results/bench_dev/heuristics.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import random
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench import common
from bench.adapters import bposd, stim_search
import stim

OUT = ROOT / "results" / "bench_dev" / "heuristics"
CODE = ROOT / "bench" / "instances" / "fx_bb72_code"
CIRCUIT = ROOT / "bench" / "instances" / "fx_sdbb16_r3"


def run_adapter(method, instance, variant="full", config="", seconds=10, threads=1,
                unavailable=False, suffix=""):
    out = OUT / (method + "_" + instance.name + "_" + variant + suffix + ".json")
    adapter = ROOT / "bench" / "adapters" / (method + ".py")
    cmd = [sys.executable]
    if unavailable:
        # This also verifies the missing-package branch on hosts with ldpc.
        wrapper = ("import importlib.util,runpy,sys; original=importlib.util.find_spec; "
                   "importlib.util.find_spec=lambda name,*a,**kw: "
                   "None if name=='ldpc' else original(name,*a,**kw); "
                   "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')")
        cmd += ["-c", wrapper]
    cmd += [str(adapter), "--instance", str(instance), "--variant", variant,
            "--time-limit", str(seconds), "--threads", str(threads), "--out", str(out)]
    if config:
        cmd += ["--config", config]
    env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="1",
               MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    print("RUN", shlex.join(cmd), flush=True)
    result = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True,
                            timeout=seconds + 8)
    assert result.returncode == 0, (cmd, result.returncode, result.stdout, result.stderr)
    with out.open() as f:
        record = json.load(f)
    assert record["seconds"] <= seconds + 3, record
    assert record["lower_bound"] is None, record
    assert all("lb" not in event for event in record["trace"]), record
    events = record["trace"]
    assert [event["t"] for event in events] == sorted(event["t"] for event in events), record
    assert all(0 <= event["t"] <= record["seconds"] + 0.01 for event in events), record
    assert all(events[i]["ub"] > events[i + 1]["ub"] for i in range(len(events) - 1)), record
    if record["upper_bound"] is not None:
        prob = common.load(str(instance), variant)
        assert record["witness_ok"] is True, record
        assert common.check_witness(prob, record["witness"])["ok"], record
        assert len(record["witness"]) == record["upper_bound"] == events[-1]["ub"], record
    print("OK", method, instance.name, variant, record["status"],
          record["upper_bound"], record["seconds"], flush=True)
    return record


def expect_truth(record):
    assert record["status"] in ("bounds", "timeout"), record
    assert record["truth_kind"] == "exact" and record["truth"] is not None, record
    assert record["upper_bound"] == record["truth"], record
    assert record["witness_ok"] is True and record["agrees_with_truth"] is True, record


def test_signatures():
    circuit = stim.Circuit.from_file(str(CIRCUIT / "circuit.stim"))
    dem = circuit.detector_error_model(decompose_errors=False).flattened()
    full = common.load(str(CIRCUIT), "full")
    full_index = stim_search.build_signature_index(full)
    row_map = stim_search.detector_row_map(full, circuit)
    seen = set()
    errors = [instruction for instruction in dem if instruction.type == "error"]
    assert errors
    for error in errors:
        signature = stim_search.dem_error_signature(error, row_map)
        matches = [j for j, pair in enumerate(zip(full.h, full.l)) if pair == signature]
        assert len(matches) == 1, (signature, matches)
        assert matches[0] == full_index[signature]
        assert stim_search.map_errors_to_witness([error], full, row_map, full_index) == matches
        assert stim_search.map_errors_to_witness([error, error], full, row_map, full_index) == []
        seen.add(signature)
    assert seen == set(full_index), (len(seen), len(full_index))

    # Check ExplainedError terms as well as raw DEM instructions, including
    # sector projection and GF(2) cancellation of repeated merged columns.
    found = circuit.search_for_undetectable_logical_errors(
        dont_explore_detection_event_sets_with_size_above=4,
        dont_explore_edges_with_degree_above=4,
        dont_explore_edges_increasing_symptom_degree=True)
    for variant in ("full", "sector", "collapsed"):
        prob = common.load(str(CIRCUIT), variant)
        mapping = stim_search.detector_row_map(prob, circuit)
        index = stim_search.build_signature_index(prob)
        for error in errors:
            signature = stim_search.dem_error_signature(error, mapping)
            assert signature == (0, 0) or signature in index, (variant, signature)
        witness = stim_search.map_errors_to_witness(found, prob, mapping, index)
        assert common.check_witness(prob, witness)["ok"], (variant, witness)
        assert stim_search.map_errors_to_witness(found + found, prob, mapping, index) == []
        if prob.distance_kind == "exact":
            assert len(witness) == prob.distance, (variant, witness, prob.distance)
    print("OK signatures:", len(errors), "DEM errors map uniquely to", full.ncols, "full columns")


def test_sampling_inputs():
    prob = common.load(str(CODE), "full")
    for mode in ("single", "random"):
        rng = random.Random(21)
        seen = set()
        for _ in range(64):
            c, row = bposd.logical_constraint(prob, rng, mode)
            assert 0 < c < (1 << prob.nobs)
            if mode == "single":
                assert c & (c - 1) == 0
            expected = [bin(logical & c).count("1") % 2 for logical in prob.l]
            assert row == expected
            seen.add(c)
        assert len(seen) > 1
    cfg = bposd.settings({})
    first = bposd.perturbed_priors(prob.ncols, random.Random(5), cfg["error_rate"], cfg["jitter"])
    assert first == bposd.perturbed_priors(prob.ncols, random.Random(5), cfg["error_rate"], cfg["jitter"])
    assert len(set(first)) > 1 and all(0 < p < 0.5 for p in first)
    assert bposd.perturbed_priors(3, random.Random(5), 0.01, 0) == [0.01] * 3
    print("OK BP+OSD random logical constraints and reproducible prior jitter")


def test_graphlike_search():
    # The supplied circuit fixture has hyperedges, so exercise the graphlike
    # subprocess on a small generated repetition memory circuit as well.
    circuit = stim.Circuit.generated("repetition_code:memory", distance=3, rounds=3,
                                     before_round_data_depolarization=0.01)
    path = OUT / "graphlike_circuit.stim"
    circuit.to_file(str(path))
    signatures = sorted({stim_search.dem_error_signature(error) for error in
                         circuit.detector_error_model(decompose_errors=False).flattened()
                         if error.type == "error"} - {(0, 0)})
    prob = common.Prob("generated_graphlike", "full", circuit.num_detectors,
                       circuit.num_observables, [h for h, _ in signatures],
                       [l for _, l in signatures], {"track": "circuit"})
    deadline = time.monotonic() + 10
    state, prepared = stim_search._run_call(str(path), "prepare", None, deadline)
    assert state == "ok" and prepared["graphlike"], (state, prepared)
    state, payload = stim_search._run_call(str(path), "graphlike", None, deadline)
    assert state == "ok", (state, payload)
    errors = [[stim.target_relative_detector_id(r) for r in common.bits(h)] +
              [stim.target_logical_observable_id(r) for r in common.bits(l)] for h, l in payload]
    witness = stim_search.map_errors_to_witness(errors, prob)
    assert common.check_witness(prob, witness)["ok"], witness
    print("OK graphlike subprocess returned a verified witness")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    test_signatures()
    test_sampling_inputs()
    test_graphlike_search()
    for instance, variant in ((CODE, "full"), (CIRCUIT, "full"), (CIRCUIT, "sector")):
        expect_truth(run_adapter("isd", instance, variant,
                                 config="chunks=12,chunk_seconds=0.03", threads=2))
    for variant in ("full", "sector"):
        expect_truth(run_adapter("stim_search", CIRCUIT, variant,
                                 config="ladder=2:2:1;3:3:1;4:4:1", threads=2))
    record = run_adapter("stim_search", CODE, seconds=3)
    assert record["status"] == "unavailable" and "code-capacity" in record["notes"], record
    for instance in (CODE, CIRCUIT):
        record = run_adapter("bposd", instance, seconds=3, unavailable=True, suffix="_missing")
        assert record["status"] == "unavailable" and "ldpc" in record["notes"], record
        assert record["upper_bound"] is None and record["witness"] is None, record
    for method in ("isd", "stim_search"):
        record = run_adapter(method, CIRCUIT, seconds=0, suffix="_timeout")
        assert record["status"] == "timeout", record
    print("ok: heuristic adapters have verified fixture witnesses, traces, and unavailable/timeout records")


if __name__ == "__main__":
    main()
