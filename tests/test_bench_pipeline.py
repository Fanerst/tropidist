"""Pipeline adapter acceptance tests; run directly with the project's Python.

The default run checks all five-switch combinations on both fixture variants,
then exports and compares three six-cycle circuits with the actual paper runner.
Every child process has a wall-time guard shorter than five minutes.  The paper
runner's ROOT is redirected so that its generated circuits stay in the test's
output directory; its search and physical replay are otherwise unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "bench_dev" / "pipeline"
LOGS = ROOT / "logs" / "bench_dev" / "pipeline"
SCRIPT = Path(__file__).resolve()
SWITCHES = ("symmetry", "cover", "collapse", "lift", "window")
FIXTURE_LIMIT = 120
COMPARISON_LIMIT = 240
REFERENCE_THRESHOLD_LIMIT = 120
TOTAL_LIMIT = 25 * 60

sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "papers"))
import common


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(value, f, indent=1)


def read_json(path):
    with path.open() as f:
        return json.load(f)


def run_process(command, name, threads, timeout, started, runs):
    remaining = TOTAL_LIMIT - (time.monotonic() - started)
    if remaining <= 0:
        raise AssertionError("pipeline tests reached the 25-minute total wall guard")
    timeout = min(timeout, remaining)
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / (name + ".log")
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["OPENBLAS_NUM_THREADS"] = str(threads)
    env["MKL_NUM_THREADS"] = str(threads)
    begin = time.monotonic()
    entry = {"name": name, "command": command, "omp_num_threads": threads,
             "timeout_seconds": timeout, "log": str(log_path.relative_to(ROOT))}
    try:
        with log_path.open("w") as log:
            proc = subprocess.run(command, cwd=str(ROOT), env=env, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=timeout)
        entry["returncode"] = proc.returncode
    except subprocess.TimeoutExpired:
        entry["timed_out"] = True
        raise AssertionError("{} exceeded {:.1f}s; see {}".format(name, timeout, log_path))
    finally:
        entry["wall_seconds"] = round(time.monotonic() - begin, 6)
        runs.append(entry)
        write_json(OUTPUT / "commands.json", runs)
    assert proc.returncode == 0, "{} exited {}; see {}".format(name, proc.returncode, log_path)
    return entry


def check_adapter(record, prob, exact=None):
    assert record["variant"] == prob.variant, record
    assert record["instance"] == prob.name, record
    assert record["status"] == "exact", record
    assert record["lower_bound"] == record["upper_bound"], record
    if exact is not None:
        assert record["lower_bound"] == exact, record
    assert record["witness_ok"] is True, record
    assert common.check_witness(prob, record["witness"])["ok"], record
    assert len(record["witness"]) == record["upper_bound"], record
    assert record["seconds"] <= record["time_limit"] + 5, record
    assert record["peak_rss_mb"] < 2048, record
    lower = upper = None
    last_time = -1
    for event in record["trace"]:
        assert event["t"] >= last_time, record
        last_time = event["t"]
        if "lb" in event:
            assert lower is None or event["lb"] > lower, record
            lower = event["lb"]
        if "ub" in event:
            assert upper is None or event["ub"] < upper, record
            upper = event["ub"]
    assert lower == record["lower_bound"] and upper == record["upper_bound"], record


def adapter_command(instance, variant, out, threads, limit, config=""):
    command = [sys.executable, str(ROOT / "bench" / "adapters" / "ours_pipeline.py"),
               "--instance", str(instance), "--variant", variant, "--time-limit", str(limit),
               "--threads", str(threads), "--out", str(out)]
    if config:
        command.extend(["--config", config])
    return command


def check_fixture(started, runs):
    instance = ROOT / "bench" / "instances" / "fx_sdbb16_r3"
    checked = 0
    for variant in ("sector", "full"):
        prob = common.load(str(instance), variant)
        assert prob.distance_kind == "exact" and prob.distance is not None
        for values in itertools.product((0, 1), repeat=len(SWITCHES)):
            config = ",".join("{}={}".format(key, value) for key, value in zip(SWITCHES, values))
            tag = "fx_sdbb16_r3__{}__{}".format(variant, "".join(map(str, values)))
            out = OUTPUT / "fixture" / (tag + ".json")
            run_process(adapter_command(instance, variant, out, 2, FIXTURE_LIMIT, config),
                        tag, 2, FIXTURE_LIMIT + 5, started, runs)
            record = read_json(out)
            assert record["threads"] == 2, record
            check_adapter(record, prob, exact=prob.distance)
            checked += 1
        print("ok: {}: all 32 ablations give exact {}".format(variant, prob.distance), flush=True)
    write_json(OUTPUT / "fixture_summary.json", {"checked": checked, "variants": ["sector", "full"],
               "switches": list(SWITCHES), "threads": 2, "distance": prob.distance})


def export_case(paper, key, name, distance):
    module = importlib.import_module(paper)
    code = module.CODES[key][2]
    circ = module.build(key, "Z", 6)
    source = "papers/{}.py::build({}, 'Z', 6), module translations".format(paper, key)
    if paper == "sdbb_parallel":
        source += "; stored order: " + " ".join(read_json(Path(module.order_file(key)))["order"])
    meta = {"family": paper, "description": "pipeline acceptance circuit, Z memory, six cycles",
            "n": code[0], "k": code[1], "basis": "Z", "rounds": 6, "source": source,
            "truth": {"sector": (distance, "exact", "task acceptance target; independently compared with "
                                                  "papers/run_parallel.py in test_bench_pipeline.py")}}
    instance = OUTPUT / "instances" / name
    required = [instance / "meta.json", instance / "circuit.stim"]
    required += [instance / (variant + suffix) for variant in ("full", "sector", "collapsed")
                 for suffix in (".H.mtx", ".L.mtx", ".rowmeta.json", ".perms.json")]
    if all(path.exists() for path in required):
        stored = read_json(instance / "meta.json")
        same_source = all(stored.get(field) == meta[field]
                          for field in ("family", "n", "k", "basis", "rounds", "source"))
        same_circuit = (instance / "circuit.stim").read_text().rstrip() == str(circ).rstrip()
        same_truth = stored["variants"]["sector"].get("distance") == distance
        if same_source and same_circuit and same_truth:
            for variant in ("full", "sector", "collapsed"):
                p = common.load(str(instance), variant)
                dimensions = stored["variants"][variant]
                assert (p.nrows, p.ncols, p.nobs) == (dimensions["rows"], dimensions["cols"], dimensions["obs"])
            print("reusing validated export: " + name, flush=True)
            return instance
    common.export_circuit_instance(name, circ, module.translations(key), meta,
                                   root=str(OUTPUT / "instances"))
    return instance


def reference_run(paper, key, out, root, k_coll):
    # This entry point runs in its own process with OMP_NUM_THREADS=1 set before
    # importing cdist.  Redirect only output placement, never algorithm stages.
    import run_parallel
    run_parallel.ROOT = str(root)
    run_parallel.main(paper, key, "Z", str(out), rounds=6, k_coll=k_coll, kmax=40,
                      time_limit=REFERENCE_THRESHOLD_LIMIT, do_full=1)
    record = read_json(out)
    record["test_peak_rss_mb"] = common.peak_rss_mb()
    record["test_k_coll"] = k_coll
    write_json(out, record)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_comparisons(started, runs):
    # The task's known distances are metadata supplied to the exporter.  All
    # result assertions use loaded metadata and the independently run reference.
    cases = (("cornucopia", 7, "cornucopia_q7_r6_Z", 5),
             ("sdbb_parallel", 40, "sdbb_parallel_n40_r6_Z", 6),
             ("routing", 54, "routing_key54_r6_Z", 6))
    comparisons = []
    reference_root = OUTPUT / "reference_root"
    for paper, key, name, distance in cases:
        instance = export_case(paper, key, name, distance)
        prob = common.load(str(instance), "sector")
        n_coll = common.load(str(instance), "collapsed").ncols
        slots = 1 << max(10, math.ceil(math.log2(sum(math.comb(n_coll, i) for i in range(4)) / 0.5 + 1)))
        default_table_mib = slots * 9 / (1024 * 1024)
        # Cornucopia's default k=3 table alone needs 2304 MiB.  Use the
        # permitted k_coll config, matched in both methods, within the local
        # 2 GiB process ceiling.  All five ablation switches remain enabled.
        k_coll = 2 if default_table_mib >= 2048 else 3
        reference_out = OUTPUT / "comparisons" / (name + "__reference.json")
        reference_out.parent.mkdir(parents=True, exist_ok=True)
        reference_command = [sys.executable, str(SCRIPT), "--reference-run", paper, str(key),
                             str(reference_out), str(reference_root), str(k_coll)]
        reference_timing = run_process(reference_command, name + "__reference", 1,
                                       COMPARISON_LIMIT + 5, started, runs)
        reference = read_json(reference_out)
        assert reference["threads"] == 1, reference
        assert reference["collapsed"]["k_table"] == k_coll, reference
        assert reference["test_peak_rss_mb"] < 2048, reference
        assert reference["model"]["sector_reduction_exact"] is True, reference
        circuit = reference_root / reference["circuit"]
        assert file_hash(circuit) == file_hash(instance / "circuit.stim"), name
        reference_bounds = (reference.get("certified_lower_bound"), reference.get("certified_upper_bound"))
        assert reference_bounds == (prob.distance, prob.distance), reference
        assert reference["witness"]["verified"] is True, reference
        adapter_out = OUTPUT / "comparisons" / (name + "__pipeline.json")
        config = "k_coll={}".format(k_coll) if k_coll != 3 else ""
        adapter_timing = run_process(adapter_command(instance, "sector", adapter_out, 1, COMPARISON_LIMIT, config),
                                     name + "__pipeline", 1, COMPARISON_LIMIT + 5, started, runs)
        adapter = read_json(adapter_out)
        assert adapter["threads"] == 1, adapter
        check_adapter(adapter, prob, exact=prob.distance)
        adapter_bounds = (adapter["lower_bound"], adapter["upper_bound"])
        assert adapter_bounds == reference_bounds, (reference_bounds, adapter_bounds)
        entry = {"instance": name, "paper": paper, "key": key, "basis": "Z", "rounds": 6,
                 "threads": 1, "circuit_sha256": file_hash(instance / "circuit.stim"),
                 "config": {"switches": {switch: 1 for switch in SWITCHES},
                            "k_coll_requested": 3, "k_coll_effective": k_coll, "k_table": 2, "kmax": 40,
                            "default_collapsed_table_mib": default_table_mib,
                            "deviation": ("matched k_coll=2: default k_coll=3 table exceeds the task's "
                                          "2 GiB local process memory ceiling") if k_coll != 3 else None},
                 "reference": {"lower_bound": reference_bounds[0], "upper_bound": reference_bounds[1],
                               "wall_seconds": reference_timing["wall_seconds"],
                               "reported_seconds": reference.get("seconds"),
                               "peak_rss_mb": reference["test_peak_rss_mb"],
                               "record": str(reference_out.relative_to(ROOT))},
                 "pipeline": {"lower_bound": adapter_bounds[0], "upper_bound": adapter_bounds[1],
                              "wall_seconds": adapter_timing["wall_seconds"],
                              "reported_seconds": adapter["seconds"],
                              "peak_rss_mb": adapter["peak_rss_mb"],
                              "record": str(adapter_out.relative_to(ROOT))}}
        comparisons.append(entry)
        write_json(OUTPUT / "comparisons.json", comparisons)
        print("ok: {}: reference [{}, {}] {:.3f}s; pipeline [{}, {}] {:.3f}s (one thread)".format(
            name, *reference_bounds, reference_timing["wall_seconds"],
            *adapter_bounds, adapter_timing["wall_seconds"]), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fixtures-only", action="store_true")
    group.add_argument("--comparisons-only", action="store_true")
    group.add_argument("--reference-run", nargs=5, metavar=("PAPER", "KEY", "OUT", "ROOT", "K_COLL"),
                       help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reference_run:
        paper, key, out, root, k_coll = args.reference_run
        reference_run(paper, int(key), Path(out), Path(root), int(k_coll))
        return
    started = time.monotonic()
    runs = []
    if not args.comparisons_only:
        check_fixture(started, runs)
    if not args.fixtures_only:
        check_comparisons(started, runs)
    print("ok: pipeline tests passed in {:.3f}s".format(time.monotonic() - started), flush=True)


if __name__ == "__main__":
    main()
