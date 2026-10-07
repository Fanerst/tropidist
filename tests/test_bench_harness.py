"""Local integration test; generated artifacts stay in bench_dev/harness.

Run: OMP_NUM_THREADS=2 .venv/bin/python tests/test_bench_harness.py
No optional packages, remote jobs, or environment installation are needed.
The sleep test deliberately exercises the fixed 30-second hard-kill grace.
"""
from __future__ import annotations

import csv
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "results" / "bench_dev" / "harness"
LOGS = ROOT / "logs" / "bench_dev" / "harness"
OUT = DEV / "records"
PYTHON = sys.executable
CPU_IDS = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else list(range(os.cpu_count() or 1))
CPU_PAIR = ",".join(map(str, CPU_IDS[:2]))
CPU_ONE = str(CPU_IDS[0])
sys.path.insert(0, str(ROOT / "bench"))
import common


FAKE_SOURCE = r'''
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import common

a = common.adapter_args("Deliberate benchmark fault injection")
mode = a.cfg.get("mode", "exit")
if mode == "sleep":
    for i in range(30):
        print("stderr-line-%02d" % i, file=sys.stderr, flush=True)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    Path(a.out + ".pid").write_text(str(child.pid))
    time.sleep(300)
elif mode == "memory":
    chunks = []
    while True:
        chunks.append(bytearray(4 * 1024 ** 2))
        time.sleep(.03)
elif mode == "exit":
    print("deliberate nonzero exit", file=sys.stderr)
    sys.exit(7)
elif mode == "malformed":
    Path(a.out).write_text('{"status":')
    sys.exit(0)
elif mode == "nan":
    Path(a.out).write_text(json.dumps(dict(instance=Path(a.instance).name, variant=a.variant,
        status="bounds", seconds=float("nan"), threads=a.threads, trace=[], lower_bound=None, upper_bound=None)))
    sys.exit(0)

prob = common.load(a.instance, a.variant)
tr = common.Trace()
bank = json.loads((Path(__file__).parent / "witnesses.json").read_text())
source = prob.meta.get("fixture_source", prob.name)
wit = bank[source + ":" + a.variant]
w = len(wit)
status, witness = "bounds", None
if mode == "wrong":
    tr.lb(1)
    tr.ub(1)
    witness = []
    status = "exact"
elif mode == "unavailable":
    status = "unavailable"
elif mode == "bounds":
    tr.lb(max(1, w - 1))
    tr.ub(w)
    witness, status = wit, "timeout"
elif mode == "heuristic":
    tr.ub(w)
    witness = wit
elif mode == "sequence":
    if prob.meta.get("test_status") != "exact":
        sys.exit(9)
    tr.ub(w)
    tr.lb(w)
    witness, status = wit, "exact"
elif mode == "blocker":
    time.sleep(.15)
elif mode == "env":
    names = ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "GOTO_NUM_THREADS", "RAYON_NUM_THREADS")
    assert all(os.environ.get(k) == str(a.threads) for k in names)
    if hasattr(os, "sched_getaffinity"):
        assert len(os.sched_getaffinity(0)) == a.threads
else:
    raise ValueError(mode)
common.save_result(a.out, prob, "fake", tr, status, a.threads, a.time_limit,
                   witness=witness, config=a.cfg, notes="deliberate test adapter mode=" + mode)
'''


def run(args, expected=0, timeout=180):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "2"
    command = [PYTHON] + [str(x) for x in args]
    print("$ " + shlex.join(command), flush=True)
    p = subprocess.run(command, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=timeout)
    with (LOGS / "commands.log").open("a") as f:
        f.write("$ " + shlex.join(command) + "\nexit=" + str(p.returncode) + "\n" + p.stdout + p.stderr + "\n")
    if p.returncode != expected:
        raise AssertionError("exit %s expected %s\n%s\n%s" % (p.returncode, expected, p.stdout, p.stderr))
    return p


def harness(methods, output=OUT, **options):
    values = dict(instances="fx_bb72_code,fx_sdbb16_r3", variants="full,sector", threads="1",
                  time_limit="30", mem_gb="1.5", total_mem_gb="3", jobs="2", cpus=CPU_PAIR, out=output)
    values.update(options)
    args = [ROOT / "bench" / "run_matrix.py", "--methods", methods]
    for key, value in values.items():
        if value is True:
            args.append("--" + key.replace("_", "-"))
        elif value is not None:
            args.extend(["--" + key.replace("_", "-"), str(value)])
    return run(args)


def records(output=OUT):
    return {str(p.relative_to(output)): json.loads(p.read_text())
            for p in output.glob("*/*.json")}


def check_schedule(recs, jobs, total_mem):
    events = []
    for name, rec in recs.items():
        h = rec.get("harness", {})
        if "started_at" in h:
            events.append((datetime.fromisoformat(h["started_at"]), 1, name, h))
            events.append((datetime.fromisoformat(h["ended_at"]), -1, name, h))
    active = {}
    for _, direction, name, info in sorted(events, key=lambda e: (e[0], e[1])):
        if direction < 0:
            active.pop(name)
        else:
            active[name] = info
        assert len(active) <= jobs
        assert sum(h["memory_limit_gb"] for h in active.values()) <= total_mem + 1e-9
        allocated = [cpu for h in active.values() for cpu in h["cpus"]]
        assert len(set(allocated)) == len(allocated), active


def fixture_clones():
    root = DEV / "giveup_instances"
    original = ROOT / "bench" / "instances" / "fx_bb72_code"
    _, _, h = common.read_mtx(str(original / "full.H.mtx"))
    _, _, l = common.read_mtx(str(original / "full.L.mtx"))
    names = []
    for i in range(4):
        name = "chain_%d" % i
        names.append(name)
        dest = root / name
        dest.mkdir(parents=True)
        meta = json.loads((original / "meta.json").read_text())
        meta.update(name=name, family="giveup-test", fixture_source="fx_bb72_code",
                    test_status="exact" if i == 3 else "error")
        meta["variants"]["full"]["cols"] += i
        (dest / "meta.json").write_text(json.dumps(meta))
        common.write_mtx(str(dest / "full.H.mtx"), h + [0] * i, meta["variants"]["full"]["rows"])
        common.write_mtx(str(dest / "full.L.mtx"), l + [0] * i, meta["variants"]["full"]["obs"])
    return root, names


def live_process(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    if sys.platform.startswith("linux"):
        try:
            return (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
        except FileNotFoundError:
            return False
    if sys.platform == "darwin":
        lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        f = lib.proc_pidinfo
        f.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        buf = ctypes.create_string_buffer(96)
        return f(pid, 4, 0, buf, 96) == 96
    return True


def main():
    if DEV.exists():
        shutil.rmtree(str(DEV))
    if LOGS.exists():
        shutil.rmtree(str(LOGS))
    DEV.mkdir(parents=True)
    LOGS.mkdir(parents=True)
    adapter_dir = DEV / "adapters"
    adapter_dir.mkdir()
    (adapter_dir / "fake.py").write_text(FAKE_SOURCE)

    # Real adapter runs on both fixtures and both available requested variants.
    harness("ours,ours:cover=0")
    real = records()
    assert len(real) == 6, real
    bank = {}
    for rec in real.values():
        assert rec["status"] == "exact" and rec["witness_ok"] is True, rec
        prob = common.load(str(ROOT / "bench" / "instances" / rec["instance"]), rec["variant"])
        assert rec["lower_bound"] == rec["upper_bound"] == prob.distance
        bank[rec["instance"] + ":" + rec["variant"]] = rec["witness"]
    (adapter_dir / "witnesses.json").write_text(json.dumps(bank))
    check_schedule(real, 2, 3)
    snapshot = {p: (OUT / p).read_bytes() for p in real}
    harness("ours,ours:cover=0")
    assert all((OUT / p).read_bytes() == contents for p, contents in snapshot.items())
    manifest = json.loads((OUT / "manifest.json").read_text())
    assert manifest["resumed"] == 6 and manifest["ran"] == 0 and manifest["ended_at"]
    assert all(k in manifest for k in ("command_line", "host", "cpu_model", "versions", "started_at"))
    assert set(manifest["versions"]) == {"stim", "scipy", "pysat", "ldpc"}

    # Every failure type writes a record; tiny memory allocation is intentional.
    modes = "sleep,memory,exit,wrong,unavailable,bounds,heuristic,malformed,nan,env".split(",")
    method_specs = ",".join("fake:mode=" + mode for mode in modes)
    harness(method_specs, instances="fx_bb72_code", variants="full", time_limit=".2",
            mem_gb=".0625", total_mem_gb=".125", adapter_dir=adapter_dir,
            heuristic_methods="fake:mode=heuristic")
    all_recs = records()
    for mode in ("sleep", "memory", "exit", "wrong", "malformed", "nan"):
        rec = all_recs["fake__mode-%s/fx_bb72_code__full__t1.json" % mode]
        assert rec["status"] == "error", rec
    sleep = all_recs["fake__mode-sleep/fx_bb72_code__full__t1.json"]
    assert "wall-time deadline" in sleep["harness"]["error_reason"]
    assert 30.2 <= sleep["harness"]["wall_seconds"] < 36
    assert sleep["harness"]["stderr_tail"] == ["stderr-line-%02d" % i for i in range(10, 30)]
    child_pid = int((OUT / "fake__mode-sleep" / "fx_bb72_code__full__t1.json.pid").read_text())
    deadline = time.monotonic() + 2
    while live_process(child_pid) and time.monotonic() < deadline:
        time.sleep(.05)
    assert not live_process(child_pid), "sleeping descendant survived process-group kill: %d" % child_pid
    assert "memory" in all_recs["fake__mode-memory/fx_bb72_code__full__t1.json"]["harness"]["error_reason"]
    assert "code 7" in all_recs["fake__mode-exit/fx_bb72_code__full__t1.json"]["harness"]["error_reason"]
    wrong = all_recs["fake__mode-wrong/fx_bb72_code__full__t1.json"]
    assert wrong["witness_ok"] is False and wrong["agrees_with_truth"] is False
    assert all_recs["fake__mode-unavailable/fx_bb72_code__full__t1.json"]["status"] == "unavailable"
    assert all_recs["fake__mode-env/fx_bb72_code__full__t1.json"]["status"] == "bounds"
    check_schedule({k: v for k, v in all_recs.items() if k.startswith("fake")}, 2, .125)
    timeout_path = OUT / "fake__mode-bounds" / "fx_bb72_code__full__t1.json"
    before = {p: (OUT / p).read_bytes() for p in all_recs}
    harness(method_specs, instances="fx_bb72_code", variants="full", time_limit=".2",
            mem_gb=".0625", total_mem_gb=".125", adapter_dir=adapter_dir,
            heuristic_methods="fake:mode=heuristic", redo="status=timeout")
    assert timeout_path.read_bytes() != before[str(timeout_path.relative_to(OUT))]
    assert all((OUT / p).read_bytes() == contents for p, contents in before.items() if "mode-bounds/" not in p)

    # Invalid allocation is refused before any output is created; dry-run is inert.
    refusal = DEV / "refused"
    for opts in (("--jobs", "2", "--threads", "2", "--cpus", CPU_PAIR),
                 ("--mem-gb", "2", "--total-mem-gb", "1")):
        p = run([ROOT / "bench" / "run_matrix.py", "--methods", "ours", "--instances", "fx_bb72_code",
                 "--out", refusal] + list(opts), expected=2)
        assert "error:" in p.stderr and not refusal.exists()
    selection = DEV / "instances.txt"
    selection.write_text("fx_bb72_code # fixture\nfx_sdbb16_r3\n")
    dry = DEV / "dry"
    p = harness("ours:cover=0,symmetry=0", output=dry, instances="@" + str(selection),
                threads="1,2", jobs="1", cpus=CPU_PAIR, dry_run=True)
    assert "6 combinations" in p.stdout and not dry.exists()
    p = harness("fake:mode=env,label=2:2:1;3:3:1", output=DEV / "colon", instances="fx_bb72_code",
                variants="full", threads="1,2", jobs="1", cpus=CPU_PAIR, adapter_dir=adapter_dir)
    assert len(records(DEV / "colon")) == 2
    harness("fake:mode=env,label=2_2_1;3_3_1", output=DEV / "colon", instances="fx_bb72_code",
            variants="full", jobs="1", cpus=CPU_ONE, adapter_dir=adapter_dir)
    assert len(records(DEV / "colon")) == 3, "config punctuation must not collide across invocations"
    repair = DEV / "repair" / "fake__mode-env" / "fx_bb72_code__full__t1.json"
    repair.parent.mkdir(parents=True)
    repair.write_text("[]")
    harness("fake:mode=env", output=DEV / "repair", instances="fx_bb72_code", variants="full",
            jobs="1", cpus=CPU_ONE, adapter_dir=adapter_dir, redo="status=error")
    assert json.loads(repair.read_text())["status"] == "bounds"

    # Give-up uses column size ordering, replays resume, and exempts heuristics.
    clone_root, names = fixture_clones()
    giveup = DEV / "giveup"
    giveup_opts = dict(instance_dir=clone_root, instances=",".join(reversed(names)), variants="full",
                      give_up="2", adapter_dir=adapter_dir, heuristic_methods="fake:mode=heuristic")
    harness("fake:mode=sequence,fake:mode=heuristic", output=giveup, **giveup_opts)
    grows = records(giveup)
    assert [grows["fake__mode-sequence/%s__full__t1.json" % name]["status"] for name in names] == ["error", "error", "skipped", "skipped"]
    assert all(grows["fake__mode-heuristic/%s__full__t1.json" % name]["status"] == "bounds" for name in names)
    old = {p: (giveup / p).read_bytes() for p in grows}
    harness("fake:mode=sequence,fake:mode=heuristic", output=giveup, **giveup_opts)
    assert all((giveup / p).read_bytes() == contents for p, contents in old.items())
    # Include skipped outcomes in the final report without merging unlike runs.
    for folder in giveup.iterdir():
        if folder.is_dir():
            shutil.copytree(str(folder), str(OUT / folder.name), dirs_exist_ok=True)

    # A later existing exact result cannot be replayed ahead of an earlier queued run.
    ordering = DEV / "ordering"
    task_instance = clone_root / names[1]
    prob = common.load(str(task_instance), "full")
    tr = common.Trace()
    wit = bank["fx_bb72_code:full"]
    tr.lb(len(wit))
    tr.ub(len(wit))
    common.save_result(str(ordering / "fake__mode-sequence" / (names[1] + "__full__t1.json")),
                       prob, "fake", tr, "exact", 1, 30, witness=wit, config={"mode": "sequence"})
    harness("fake:mode=blocker,fake:mode=sequence", output=ordering, jobs="1", cpus=CPU_ONE,
            instance_dir=clone_root, instances=",".join(names), variants="full", give_up="2", adapter_dir=adapter_dir)
    ordered = records(ordering)
    assert ordered["fake__mode-sequence/chain_3__full__t1.json"]["status"] == "exact", ordered

    # Synthetic timing records test statistics from traces, not final run duration.
    exact = dict(next(iter(real.values())))
    exact.pop("harness")
    exact.update(method="trace_test", seconds=900, time_limit=3600,
                 trace=[{"t": 1, "lb": 1}, {"t": 58, "ub": exact["upper_bound"]},
                        {"t": 59, "lb": exact["lower_bound"]}])
    trace_dir = OUT / "trace_test"
    trace_dir.mkdir()
    (trace_dir / (exact["instance"] + "__" + exact["variant"] + "__t1.json")).write_text(json.dumps(exact))
    missing_trace = dict(exact, method="untimed", trace=[])
    untimed_dir = OUT / "untimed"
    untimed_dir.mkdir()
    (untimed_dir / "untimed.json").write_text(json.dumps(missing_trace))
    deadline = dict(exact, method="deadline", status="timeout", lower_bound=exact["lower_bound"] - 1,
                    time_limit=100, seconds=105, trace=[{"t": 99, "lb": 1}, {"t": 101, "lb": exact["lower_bound"] - 1},
                                                       {"t": 102, "ub": exact["upper_bound"]}])
    deadline_dir = OUT / "deadline"
    deadline_dir.mkdir()
    (deadline_dir / "deadline.json").write_text(json.dumps(deadline))
    report = DEV / "BENCHMARK.md"
    run([ROOT / "bench" / "report.py", OUT, "--out", report])
    text = report.read_text()
    assert all("Table %d." % i in text for i in range(1, 5))
    assert "WRONG results" in text and "WRONG:" in text and "witness failed" in text
    assert "exact in 59.0 s" in text and "exact (trace timing unavailable)" in text
    assert "true distance first reached" in text and "(heuristic)" in text
    assert ">= 5, <= 6 (timeout)" in text and "unavailable" in text and "skipped" in text and "(error)" in text
    assert ">= 1 at 100.0 s" in text
    assert "fake__mode" in text and ".json)" in text
    with (OUT / "summary.csv").open() as f:
        summary = list(csv.DictReader(f))
    assert len(summary) == len(records())
    timing = next(row for row in summary if row["method"] == "trace_test")
    assert float(timing["time_to_exact"]) == 59 and float(timing["seconds"]) == 900
    with (OUT / "profile.csv").open() as f:
        profile = list(csv.DictReader(f))
    assert any(row["method"] == "trace_test" and float(row["time_to_exact"]) == 59 for row in profile)
    assert not any(row["method"] == "untimed" or "wrong" in row["method"] for row in profile)
    for method in {row["method"] for row in profile}:
        times = [float(row["time_to_exact"]) for row in profile if row["method"] == method]
        assert times == sorted(times)
    print("PASS: matrix, resources, failures, resume/redo, give-up, trace tables and CSVs")
    print("BENCHMARK: " + str(report))
    print("COMMAND LOG: " + str(LOGS / "commands.log"))


if __name__ == "__main__":
    main()
