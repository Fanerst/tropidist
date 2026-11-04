"""Plain-script tests for the dist-m4ri benchmark adapter, without the C binary.

Run: .venv/bin/python tests/test_bench_distm4ri.py
All generated fake executables, witnesses and records stay in
results/bench_dev/distm4ri.  The fake mirrors the checked-in 0.9.0 output
formats; it is not a substitute for the server's real-binary comparison.
"""
from __future__ import annotations

from itertools import combinations
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench import common
from bench.adapters import distm4ri

OUT = ROOT / "results" / "bench_dev" / "distm4ri"
CODE = ROOT / "bench" / "instances" / "fx_bb72_code"
CIRCUIT = ROOT / "bench" / "instances" / "fx_sdbb16_r3"
EXTERNAL = ROOT / "bench" / "external" / "dist-m4ri"
ADAPTER = ROOT / "bench" / "adapters" / "distm4ri.py"
FAKE = OUT / "fake_dist_m4ri"
CALLS = OUT / "fake_calls.jsonl"
ENV = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="1",
           MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")


def signature(error, row_map=None):
    targets = error.dem_error_terms if hasattr(error, "dem_error_terms") else error.targets_copy()
    h = l = 0
    for target in targets:
        target = getattr(target, "dem_target", target)
        if target.is_relative_detector_id():
            row = target.val if row_map is None else row_map.get(target.val)
            if row is not None:
                h ^= 1 << row
        elif target.is_logical_observable_id():
            l ^= 1 << target.val
    return h, l


def fixture_payload():
    """Find witnesses from the matrices/circuit, never from adapter expectations."""
    code = common.load(str(CODE), "full")
    assert code.distance_kind == "exact" and code.distance is not None
    half = code.distance // 2
    seen = {}
    code_witness = None
    for columns in combinations(range(code.ncols), half):
        h = l = 0
        for j in columns:
            h ^= code.h[j]
            l ^= code.l[j]
        if h in seen:
            other, logical = seen[h]
            if logical != l:
                candidate = sorted(set(columns) ^ set(other))
                if common.check_witness(code, candidate)["ok"]:
                    code_witness = candidate
                    break
        else:
            seen[h] = columns, l
    assert code_witness is not None and len(code_witness) == code.distance

    import stim
    circuit = stim.Circuit.from_file(str(CIRCUIT / "circuit.stim"))
    errors = circuit.search_for_undetectable_logical_errors(
        dont_explore_detection_event_sets_with_size_above=4,
        dont_explore_edges_with_degree_above=4,
        dont_explore_edges_increasing_symptom_degree=True)
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    dem_errors = [inst for inst in dem if inst.type == "error"]
    raw_index = {}
    for j, error in enumerate(dem_errors):
        raw_index.setdefault(signature(error), j)
    dem_witness = sorted(raw_index[signature(error)] for error in errors)

    payload = {"code": {"witness": code_witness, "distance": code.distance}}
    for variant in ("full", "sector"):
        prob = common.load(str(CIRCUIT), variant)
        rows = {tuple(row): j for j, row in enumerate(prob.rowmeta)}
        mapping = ({j: j for j in range(circuit.num_detectors)} if variant == "full" else
                   {j: rows[tuple(coords)] for j, coords in circuit.get_detector_coordinates().items()
                    if tuple(coords) in rows})
        index = {pair: j for j, pair in enumerate(zip(prob.h, prob.l))}
        support = set()
        for error in errors:
            pair = signature(error, mapping)
            if pair == (0, 0):
                continue
            j = index[pair]
            support.symmetric_difference_update([j])
        witness = sorted(support)
        assert common.check_witness(prob, witness)["ok"], (variant, witness)
        assert prob.distance_kind == "exact" and len(witness) == prob.distance
        payload[variant] = {"witness": witness, "distance": prob.distance}
    payload["dem"] = {"witness": dem_witness, "distance": payload["full"]["distance"],
                      "error_count": len(dem_errors)}
    (OUT / "fixture_witnesses.json").write_text(json.dumps(payload, indent=1) + "\n")
    print("OK generated and verified code/full/sector fixture witnesses", flush=True)
    return payload


FAKE_SOURCE = r'''
import json
import os
from pathlib import Path
import subprocess
import sys
import time

if sys.argv[1:] == ["--version"]:
    print("dist_m4ri version fake-0.9.0", flush=True)
    sys.exit(0)

root = Path(__file__).resolve().parent
payload = json.loads((root / "fixture_witnesses.json").read_text())
args = dict(arg.split("=", 1) for arg in sys.argv[1:])
case = os.environ.get("DISTM4RI_FAKE_CASE", "success")
with (root / "fake_calls.jsonl").open("a") as f:
    f.write(json.dumps({"args": args, "case": case, "pid": os.getpid()}) + "\n")
assert args["threads"] == "2"
assert args["nothrottle"] == "1"
assert int(args["debug"]) & 1
assert "outC" in args or int(args["debug"]) & 2080 == 2080      # without outC: supports printed on stderr
method = int(args["method"])
if "fdem" in args:
    assert args["pmin"] == "0"
    dem_text = Path(args["fdem"]).read_text()
    assert "repeat" not in dem_text.lower() and "shift_detectors" not in dem_text
    assert "^" not in dem_text
    assert sum(line.lstrip().startswith("error(") for line in dem_text.splitlines()) == payload["dem"]["error_count"]
    problem = payload["dem"]
    confinement = "1,1,1"
else:
    assert "finH" in args and "finL" in args
    if "fx_bb72_code" in args["finH"]:
        problem = payload["code"]
        confinement = "3,4,3,4,3,4"
    else:
        variant = "sector" if Path(args["finH"]).name.startswith("sector.") else "full"
        problem = payload[variant]
        confinement = "2,2,2,2"
d = problem["distance"]
wmax = int(args.get("wmax", "0")) or d

def export():
    columns = problem["witness"]
    if "outC" not in args:
        print("# [thread 0] RW codeword of weight %d (1-based columns): %s" % (
            len(columns), " ".join(str(j + 1) for j in columns)), file=sys.stderr, flush=True)
        return
    Path(args["outC"]).write_text("%% NZLIST\n% generated by dist_m4ri\n" + str(len(columns)) +
                                 " " + " ".join(str(j + 1) for j in columns) + "\n")

def completed(w):
    if method == 2:
        print("# CC w=%d completed in 0.003s (2 CC threads): no codewords found -> dmin=%d" % (w, w + 1),
              file=sys.stderr, flush=True)
    else:
        print("# CC round w=%d finished in 0.003s (1 CC threads, 1 RW threads): no codewords -> dmin=%d" % (w, w + 1),
              file=sys.stderr, flush=True)

if case.startswith("sleep"):
    completed(1)
    completed(2)
    if case == "sleep_witness":
        export()
    elif case == "sleep_partial_export":
        Path(args["outC"]).write_text("%% NZL")
    elif case == "sleep_empty_export":
        Path(args["outC"]).write_text("")
    marker = root / ("descendant_" + case + ".txt")
    # The descendant shares the adapter's process group.  It must be killed
    # before creating this marker, even though the parent process is sleeping.
    child_code = "import time;from pathlib import Path;time.sleep(1.0);Path(%r).write_text('escaped')" % str(marker)
    subprocess.Popen([sys.executable, "-c", child_code])
    time.sleep(30)
    sys.exit(0)

if method in (2, 3):
    for w in range(1, min(wmax, d - 1) + 1):
        time.sleep(0.003)
        completed(w)
if method == 2 and wmax < d:
    print("# confinement: " + confinement, file=sys.stderr, flush=True)
    print("%d 0 0" % (wmax + 1), flush=True)
    sys.exit(0)
if method == 2:
    print("# CC found min-weight codeword: d=%d (using 2 CC threads, total 1 cws)" % d,
          file=sys.stderr, flush=True)
elif method == 3:
    print("# bracketing bounds coincide: dmin = dmax = %d" % d, file=sys.stderr, flush=True)
print("# confinement: " + confinement, file=sys.stderr, flush=True)
print("%d %d %d" % (1 if method == 1 else d, d,
                     0 if method == 2 else int(args.get("steps", "2000"))), flush=True)
if case != "no_witness":
    # Native dist_m4ri flushes its final triple before nzlist_write.  A short
    # delay catches adapters that assume this stdout line means export is done.
    time.sleep(0.01)
    export()
'''


def write_fake():
    FAKE.write_text("#!" + sys.executable + "\n" + FAKE_SOURCE)
    FAKE.chmod(0o755)
    CALLS.write_text("")


# The build's dist_m4ri.py, as far as bound=model uses it: the model bound is one below the distance, so the
# binary run (with dmin = that bound) is still needed for the exact value.
FAKE_WRAPPER = r'''
import json
from pathlib import Path

_cache = [True]


def disable_distance_cache():
    _cache[0] = False


def compute_model_lower_bound(circuit, dist_m4ri=None, method=3, threads=None, timeout=60.0, nothrottle=False,
                              return_info=False):
    root = Path(__file__).resolve().parent
    assert not _cache[0] and nothrottle and Path(circuit).name == "circuit.stim" and Path(dist_m4ri).is_file()
    d = json.loads((root / "fixture_witnesses.json").read_text())["full"]["distance"]
    with (root / "fake_model_calls.jsonl").open("a") as f:
        f.write(json.dumps({"method": method, "threads": threads, "timeout": timeout}) + "\n")
    info = {"model_d_info": [d - 1, d, 0], "rows": 6, "cols": 30, "dem_cols": 100}
    return (d - 1, info) if return_info else d - 1
'''


def test_model_bound():
    (OUT / "dist_m4ri.py").write_text(FAKE_WRAPPER)
    (OUT / "fake_model_calls.jsonl").write_text("")
    d = json.loads((OUT / "fixture_witnesses.json").read_text())["sector"]["distance"]
    for mode, method in (("cc", 2), ("bracket", 3)):
        before = len(CALLS.read_text().splitlines())
        record = run_adapter("model_bound_" + mode, CIRCUIT, "sector", "mode=%s,bound=model" % mode)
        assert record["status"] == "exact" and record["lower_bound"] == record["upper_bound"] == d, record
        assert record["trace"][0].get("lb") == d - 1 and record["config"]["model_bound"] == d - 1, record
        calls = [json.loads(line) for line in CALLS.read_text().splitlines()[before:]]
        assert len(calls) == 1 and calls[0]["args"]["dmin"] == str(d - 1), calls
        args = calls[0]["args"]
        if mode == "bracket":   # no outC: the program stops when the bounds meet; the support comes on stderr
            assert "outC" not in args and int(args["debug"]) & 2080 == 2080 and "maxC" not in args, args
        else:
            assert "outC" in args and args["maxC"] == "1", args
        model = json.loads((OUT / "fake_model_calls.jsonl").read_text().splitlines()[-1])
        assert model["method"] == method and model["threads"] == 2 and 0 < model["timeout"] <= 2, model
    for label, instance, variant, config in (
            ("rw", CIRCUIT, "sector", "mode=rw,bound=model"),
            ("code", CODE, "full", "mode=cc,bound=model"),
            ("collapsed", CIRCUIT, "collapsed", "mode=cc,bound=model"),
            ("dmin", CIRCUIT, "sector", "mode=cc,bound=model,dmin=2")):
        record = run_adapter("model_bound_invalid_" + label, instance, variant, config)
        assert record["status"] == "error", record
    print("OK model bound: certified dmin forwarded, lower bound claimed from it, invalid uses rejected", flush=True)


def run_adapter(label, instance=CODE, variant="full", config="", seconds=4,
                fake=True, case="success"):
    out = OUT / (label + ".json")
    out.unlink(missing_ok=True)
    if fake:
        config = "binary=" + str(FAKE) + ("," + config if config else "")
    cmd = [sys.executable, str(ADAPTER), "--instance", str(instance), "--variant", variant,
           "--time-limit", str(seconds), "--threads", "2", "--out", str(out)]
    if config:
        cmd += ["--config", config]
    env = dict(ENV, DISTM4RI_FAKE_CASE=case)
    print("RUN", shlex.join(cmd), "[fake case=" + case + "]", flush=True)
    wall_start = time.monotonic()
    result = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True,
                            timeout=seconds + 4)
    elapsed = time.monotonic() - wall_start
    assert result.returncode == 0, (cmd, result.returncode, result.stdout, result.stderr)
    assert out.is_file(), (cmd, result.stdout, result.stderr)
    record = json.loads(out.read_text())
    assert record["threads"] == 2 and record["time_limit"] == seconds, record
    assert record["seconds"] <= seconds + 2 and elapsed <= seconds + 3, record
    if fake and seconds > 0 and record["status"] in ("exact", "bounds", "timeout"):
        assert record["version"] == "fake-0.9.0", record
    events = record["trace"]
    assert [event["t"] for event in events] == sorted(event["t"] for event in events), record
    assert all(0 <= event["t"] <= record["seconds"] + 0.01 for event in events), record
    for field in ("lb", "ub"):
        values = [event[field] for event in events if field in event]
        assert values == sorted(set(values), reverse=(field == "ub")), record
    if record["upper_bound"] is not None:
        prob = common.load(str(instance), variant)
        assert record["witness_ok"] is True, record
        assert common.check_witness(prob, record["witness"])["ok"], record
        assert len(record["witness"]) == record["upper_bound"], record
    else:
        assert record["witness"] is None, record
    print("OK", label, record["status"], record["lower_bound"], record["upper_bound"], flush=True)
    return record


def test_parsers():
    # The source tree does not include saved process logs.  These literal
    # stdout expectations and the NZLIST heredoc are the shipped real-format
    # fixtures in its shell tests; do not claim these are captured local runs.
    if not (EXTERNAL / "src" / "tests" / "test_run.sh").exists():
        try:
            import pytest
        except ImportError:
            return
        pytest.skip("needs the dist-m4ri sources in bench/external/dist-m4ri (README, external material)")
    shell_tests = (EXTERNAL / "src" / "tests" / "test_run.sh").read_text()
    triples = re.findall(r'"\^([0-9]+ [0-9]+ [0-9]+)\$"', shell_tests)
    assert len(set(triples)) >= 3
    for literal in triples:
        text = "# confinement: 1,1,1\n# ignored 9 9 9\n" + literal + "\n# trailing diagnostics\n"
        assert distm4ri.parse_triple(text) == tuple(map(int, literal.split()))
    assert distm4ri.parse_triple("2 0 0\n# debug\n6 6 2000\n") == (6, 6, 2000)

    nz_text = re.search(r"(%% NZLIST\n.*?)\nEOF", shell_tests, re.S).group(1)
    nz_path = OUT / "upstream_codewords.nz"
    nz_path.write_text(nz_text + "\n")
    assert distm4ri.read_codewords(str(nz_path), 32) == [[0, 2, 22], [0], [0, 1, 6, 16, 27]]
    for label, text in (
            ("bad_weight", "%% NZLIST\n3 1 2\n"),
            ("bad_zero", "%% NZLIST\n1 0\n"),
            ("bad_range", "%% NZLIST\n1 33\n"),
            ("bad_duplicate", "%% NZLIST\n2 1 1\n"),
            ("bad_integer", "%% NZLIST\n1 x\n"),
            ("bad_header", "1 1\n")):
        path = OUT / (label + ".nz")
        path.write_text(text)
        try:
            distm4ri.read_codewords(str(path), 32)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed NZLIST accepted: " + label)

    for line in (
        "# CC w=1 completed in 0.003s (2 CC threads): no codewords found -> dmin=2",
        "# CC round w=1 finished in 0.003s (1 CC threads, 1 RW threads): no codewords -> dmin=2"):
        assert distm4ri.parse_progress(line) == (1, 2), line
    for line in (
        "# CC for w=4 (est 20.00s) exceeds remaining timeout 0.10s, terminating early (dmin=4)",
        "# CC found min-weight codeword: d=4 (using 2 CC threads, total 1 cws)",
        "# confinement: 1,1,1"):
        assert distm4ri.parse_progress(line) is None, line
    print("OK parsers: upstream shell-test triples/NZLIST and source progress formats", flush=True)


def expect_exact(record, with_full_trace=True):
    assert record["status"] == "exact", record
    assert record["truth_kind"] == "exact" and record["truth"] is not None, record
    assert record["lower_bound"] == record["upper_bound"] == record["truth"], record
    assert record["witness_ok"] is True and record["agrees_with_truth"] is True, record
    if with_full_trace:
        lbs = [event["lb"] for event in record["trace"] if "lb" in event]
        assert set(range(2, record["truth"] + 1)).issubset(lbs), record


def test_unavailable():
    record = run_adapter("missing_binary", fake=False,
                         config="binary=" + str(OUT / "not_present"))
    assert record["status"] == "unavailable" and record["upper_bound"] is None, record
    nonexecutable = OUT / "nonexecutable"
    nonexecutable.write_text("not a program\n")
    nonexecutable.chmod(0o644)
    record = run_adapter("nonexecutable_binary", fake=False,
                         config="binary=" + str(nonexecutable))
    assert record["status"] == "unavailable", record
    default = EXTERNAL / "src" / "dist_m4ri"
    if not default.is_file() or not os.access(str(default), os.X_OK):
        record = run_adapter("default_unavailable", fake=False)
        assert record["status"] == "unavailable", record
    else:
        print("SKIP default unavailable branch: real binary is present", flush=True)


def test_modes():
    for label, instance, variant, input_kind in (
            ("code", CODE, "full", "mtx"),
            ("sector", CIRCUIT, "sector", "mtx"),
            ("dem", CIRCUIT, "full", "dem")):
        for mode in ("cc", "bracket"):
            config = "mode=%s,input=%s,wmax=8,steps=2000,debug=0" % (mode, input_kind)
            expect_exact(run_adapter(label + "_" + mode, instance, variant, config))
        record = run_adapter(label + "_rw", instance, variant,
                             "mode=rw,input=%s,steps=2000,seed=17,dest=3" % input_kind)
        assert record["status"] == "bounds", record
        assert record["lower_bound"] is None and all("lb" not in e for e in record["trace"]), record
        assert record["upper_bound"] == record["truth"] and record["witness_ok"] is True, record

    record = run_adapter("cc_exhausted", config="mode=cc,wmax=2")
    assert record["status"] == "bounds" and record["lower_bound"] == 3, record
    assert record["upper_bound"] is None, record
    assert [e["lb"] for e in record["trace"] if "lb" in e][-2:] == [2, 3], record

    record = run_adapter("missing_witness", config="mode=cc,wmax=8", case="no_witness")
    assert record["status"] == "bounds" and record["lower_bound"] == record["truth"], record
    assert record["upper_bound"] is None and "witness" in record["notes"].lower(), record


def test_timeout():
    for case in ("sleep", "sleep_witness", "sleep_partial_export", "sleep_empty_export"):
        marker = OUT / ("descendant_" + case + ".txt")
        marker.unlink(missing_ok=True)
        record = run_adapter("timeout_" + case, config="mode=cc,wmax=8", seconds=0.5, case=case)
        assert record["status"] == "timeout" and record["lower_bound"] == 3, record
        assert [e["lb"] for e in record["trace"] if "lb" in e][-2:] == [2, 3], record
        if case == "sleep_witness":
            assert record["upper_bound"] == record["truth"] and record["witness_ok"] is True, record
        else:
            assert record["upper_bound"] is None, record
        time.sleep(1.1)
        assert not marker.exists(), "adapter left its descendant running after timeout"
    record = run_adapter("zero_budget", config="mode=cc", seconds=0)
    assert record["status"] == "timeout", record


def test_validation():
    for label, config in (
            ("unknown", "made_up_parameter=7"),
            ("probability_cut", "input=dem,pmin=0.01"),
            ("classical", "classical=1"),
            ("throttle", "nothrottle=0"),
            ("method_override", "method=1"),
            ("dem_sector", "input=dem"),
            ("threads_mismatch", "threads=1"),
            ("negative_seed", "seed=-2147483648"),
            ("weight_overflow", "dW=2147483647")):
        instance = CIRCUIT if label in ("probability_cut", "dem_sector") else CODE
        variant = "sector" if label == "dem_sector" else "full"
        record = run_adapter("invalid_" + label, instance, variant, config)
        assert record["status"] == "error", record
    for label, config in (
            ("dmin", "dmin=2"),
            ("noscan", "noscan=1"),
            ("column_start", "start=1")):
        record = run_adapter("uncertified_" + label, config="mode=cc,wmax=8," + config)
        assert record["status"] == "bounds" and record["lower_bound"] is None, record
        assert all("lb" not in e for e in record["trace"]), record
        assert record["upper_bound"] == record["truth"] and record["witness_ok"] is True, record
    binary, _, _, options, _, _ = distm4ri.settings({"mode": "cc", "finC": str(OUT / "upstream_codewords.nz")}, 2)
    assert Path(binary).is_absolute(), binary
    assert "maxC" not in options, options
    assert distm4ri.settings({"binary": "results/bench_dev/distm4ri/fake_dist_m4ri"}, 2)[0] == str(FAKE)
    print("OK absolute executable path and uncapped warm-start codeword collection", flush=True)


def test_forwarding():
    calls = [json.loads(line) for line in CALLS.read_text().splitlines()]
    assert calls and {int(call["args"]["method"]) for call in calls} == {1, 2, 3}
    assert any("fdem" in call["args"] for call in calls)
    for call in calls:
        args = call["args"]
        assert args["threads"] == "2" and args["nothrottle"] == "1", call
        assert int(args["debug"]) & 1, call
        assert 0 < float(args["timeout"]) <= (0.5 if call["case"].startswith("sleep") else 4), call
        if "fdem" in args:
            assert args["pmin"] == "0", call
    rw_calls = [call["args"] for call in calls if call["args"]["method"] == "1"]
    assert all(args["seed"] == "17" and args["dest"] == "3" for args in rw_calls), rw_calls
    print("OK thread count, throttle override, debug progress, native time cap and probability forwarding", flush=True)


def test_instance_read_deadline():
    original = distm4ri.common.load

    def slow_load(instance, variant):
        time.sleep(0.1)
        return original(instance, variant)

    distm4ri.common.load = slow_load
    started = time.monotonic()
    try:
        prob, read_timed_out = distm4ri.load_instance(str(CIRCUIT), "full", started + 0.02)
    finally:
        distm4ri.common.load = original
    elapsed = time.monotonic() - started
    meta = json.loads((CIRCUIT / "meta.json").read_text())
    shape = meta["variants"]["full"]
    assert read_timed_out and elapsed < 0.1, (read_timed_out, elapsed)
    assert (prob.name, prob.variant) == (meta["name"], "full"), prob
    assert (prob.nrows, prob.ncols, prob.nobs) == (shape["rows"], shape["cols"], shape["obs"]), prob
    assert prob.distance == shape["distance"] and prob.meta == meta, prob
    print("OK instance-read deadline preserves metadata dimensions", flush=True)


def setup_module(module=None):
    """Under pytest, the setup that main() does before the tests that need it."""
    OUT.mkdir(parents=True, exist_ok=True)
    CALLS.touch()
    fixture_payload()
    write_fake()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    test_parsers()
    test_instance_read_deadline()
    fixture_payload()
    write_fake()
    test_unavailable()
    test_modes()
    test_timeout()
    test_validation()
    test_forwarding()
    test_model_bound()
    print("ok: dist-m4ri adapter parsers, modes, proofs, witnesses, timeout and unavailable records", flush=True)


if __name__ == "__main__":
    main()
