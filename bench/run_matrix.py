"""Run adapter matrices with private CPU sets, bounded memory and resumable records.

Comma-separated key=value tokens belong to the preceding method.  For example,
``ours:cover=0,symmetry=0,milp:backend=scipy`` contains two methods.
Give-up sequences are independent for each method/config, family, variant and
thread count.  An explicit --heuristic-methods override or a literal adapter
HEURISTIC=True / METHOD_KIND='heuristic' declaration exempts upper-only tools.
"""
from __future__ import annotations

import argparse
import ast
import ctypes
import fcntl
from collections import deque
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common

THREAD_VARS = ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS",
               "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
               "NUMEXPR_NUM_THREADS", "GOTO_NUM_THREADS", "RAYON_NUM_THREADS")
HEURISTIC_ADAPTERS = {"bposd", "bp_osd", "bp_osd_sampling", "stim", "stim_search",
                      "dist_m4ri", "m4ri", "isd"}
VALID_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")


def config_component(value):
    # Encode data punctuation, leaving '-' and '__' exclusively as separators.
    return "".join(chr(b) if (48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122 or b == 46)
                   else "%%%02X" % b for b in value.encode("utf-8"))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
    with tmp.open("w") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
    os.replace(str(tmp), str(path))


def record_invocation(manifest_path, invocation):
    """Add this invocation to the manifest, or refresh its entry.  Harnesses that share an output directory may run
    at the same time, so the file is re-read under a lock and only this invocation's entry is written."""
    with open(str(manifest_path) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = None
        if manifest_path.exists():
            try:
                previous = json.loads(manifest_path.read_text())
            except (OSError, ValueError):
                pass
        history = list(previous.get("invocations", [])) if isinstance(previous, dict) else []
        key = (invocation["host"], invocation["pid"], invocation["started_at"])
        for i, entry in enumerate(history):
            if (entry.get("host"), entry.get("pid"), entry.get("started_at")) == key:
                history[i] = dict(invocation)
                break
        else:
            history.append(dict(invocation))
        write_json(manifest_path, dict(invocation, invocations=history))


def group_specs(value):
    """Split a comma-separated list of methods; key=value tokens belong to the preceding method."""
    specs = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            raise ValueError("empty method or config token")
        if "=" in token and (":" not in token or token.index("=") < token.index(":")):
            if not specs or ":" not in specs[-1]:
                raise ValueError("config tokens must follow adapter:key=value")
            specs[-1] += "," + token
        else:
            specs.append(token)
    return specs


def parse_methods(value, adapter_dir, heuristic_names):
    specs = group_specs(value)
    methods, folders = [], set()
    for spec in specs:
        adapter, sep, cfg = spec.partition(":")
        if not VALID_NAME.fullmatch(adapter) or adapter in (".", ".."):
            raise ValueError("invalid adapter name: " + adapter)
        config = {}
        if sep:
            if not cfg:
                raise ValueError("empty config for " + adapter)
            for kv in cfg.split(","):
                if "=" not in kv:
                    raise ValueError("config must be key=value: " + kv)
                k, v = kv.split("=", 1)
                if not VALID_NAME.fullmatch(k) or not v or k in config:
                    raise ValueError("invalid or duplicate config key: " + kv)
                config[k] = v
        safe_cfg = "__".join(config_component(k) + "-" + config_component(v) for k, v in config.items())
        folder = adapter + ("__" + safe_cfg if sep else "")
        if len(folder.encode("utf-8")) > 255:
            raise ValueError("method config is too long for a result directory name")
        if folder in folders:
            raise ValueError("methods map to the same result directory: " + folder)
        folders.add(folder)
        path = adapter_dir / (adapter + ".py")
        if not path.is_file():
            raise ValueError("adapter does not exist: " + str(path))
        forced_heuristic = adapter in heuristic_names or spec in heuristic_names
        heuristic = adapter in HEURISTIC_ADAPTERS
        # Read literal capabilities without importing an adapter or its dependencies.
        try:
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in ("HEURISTIC", "METHOD_KIND"):
                            val = ast.literal_eval(node.value)
                            if target.id == "HEURISTIC":
                                heuristic = bool(val)
                            else:
                                heuristic = val in ("heuristic", "upper_only")
        except (SyntaxError, ValueError, TypeError):
            pass
        heuristic = heuristic or forced_heuristic
        methods.append({"spec": spec, "adapter": adapter, "path": path,
                        "config_string": cfg, "config": config, "folder": folder,
                        "kind": "heuristic" if heuristic else "certifying"})
    return methods


def parse_cpus(value):
    cpus = []
    for part in value.split(","):
        if re.fullmatch(r"\d+-\d+", part):
            lo, hi = map(int, part.split("-"))
            if hi < lo:
                raise ValueError("descending CPU range: " + part)
            cpus.extend(range(lo, hi + 1))
        elif part.isdigit():
            cpus.append(int(part))
        else:
            raise ValueError("invalid CPU list: " + value)
    if not cpus or len(set(cpus)) != len(cpus):
        raise ValueError("CPU list must be nonempty and contain no duplicates")
    return cpus


def select_instances(value, root):
    if value == "all":
        names = sorted(p.parent.name for p in root.glob("*/meta.json"))
    elif value.startswith("@"):
        contents = Path(value[1:]).read_text()
        names = []
        for line in contents.splitlines():
            names.extend(x for x in re.split(r"[\s,]+", line.split("#", 1)[0].strip()) if x)
    else:
        names = [x.strip() for x in value.split(",")]
    if not names or len(set(names)) != len(names):
        raise ValueError("instance selection must be nonempty and contain no duplicates")
    instances = []
    for name in names:
        if not VALID_NAME.fullmatch(name) or name in (".", ".."):
            raise ValueError("invalid instance name: " + name)
        path = root / name
        with (path / "meta.json").open() as f:
            meta = json.load(f)
        instances.append((path, meta))
    return instances


def cpu_model():
    try:
        if sys.platform == "darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL).strip()
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return platform.processor() or platform.machine()


def package_versions():
    result = {}
    for module, distribution in (("stim", "stim"), ("scipy", "scipy"),
                                 ("pysat", "python-sat"), ("ldpc", "ldpc")):
        try:
            # Import in a child to avoid initializing BLAS thread pools in the scheduler.
            code = "import importlib; m=importlib.import_module(%r); print(getattr(m,'__version__','unknown'))" % module
            p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
            if p.returncode == 0:
                version = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "unknown"
                if version == "unknown":
                    try:
                        version = importlib.metadata.version(distribution)
                    except importlib.metadata.PackageNotFoundError:
                        pass
                result[module] = version
            else:
                result[module] = None
        except (OSError, subprocess.SubprocessError):
            result[module] = None
    return result


def as_limit_supported(nbytes):
    code = "import resource; n=%d; resource.setrlimit(resource.RLIMIT_AS,(n,n))" % nbytes
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
    return p.returncode == 0, p.stderr.strip()


def limit_address_space(nbytes):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (nbytes, nbytes))
    return apply


def kill_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def stderr_tail(path):
    # Reverse-block reading keeps diagnostic memory bounded even for very noisy tools.
    try:
        with Path(path).open("rb") as f:
            f.seek(0, os.SEEK_END)
            pos, chunks, count = f.tell(), [], 0
            while pos and count <= 20 and sum(map(len, chunks)) < 65536:
                n = min(pos, 4096)
                pos -= n
                f.seek(pos)
                chunk = f.read(n)
                chunks.insert(0, chunk)
                count += chunk.count(b"\n")
        return b"".join(chunks).decode("utf-8", "replace").splitlines()[-20:]
    except OSError:
        return []


def group_memory_mb(group_ids):
    # Darwin rejects RLIMIT_AS on some installations; RSS monitoring is a fallback,
    # with a polling overshoot, rather than pretending that an AS limit was installed.
    if sys.platform == "darwin":
        lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        listpids = lib.proc_listallpids
        listpids.argtypes = [ctypes.c_void_p, ctypes.c_int]
        pidinfo = lib.proc_pidinfo
        pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        count = listpids(None, 0)
        if count <= 0:
            raise RuntimeError("cannot list processes for memory monitoring")
        pids = (ctypes.c_int * (count + 256))()
        count = listpids(pids, ctypes.sizeof(pids))
        if count <= 0:
            raise RuntimeError("cannot enumerate processes for memory monitoring")
        result = {}
        for pid in pids[:count]:
            try:
                pgid = os.getpgid(pid)
            except ProcessLookupError:
                continue
            if pgid not in group_ids:
                continue
            # PROC_PIDTASKINFO: first uint64 fields are virtual and resident bytes.
            buf = ctypes.create_string_buffer(96)
            n = pidinfo(pid, 4, 0, buf, 96)
            if n == 96:
                rss = (ctypes.c_uint64 * 2).from_buffer(buf)[1] / 1024 ** 2
                result[pgid] = result.get(pgid, 0) + rss
            elif n > 0 or ctypes.get_errno() not in (0, 3):
                raise RuntimeError("cannot read child-process memory: errno %d" % ctypes.get_errno())
        return result
    if sys.platform.startswith("linux"):
        result = {}
        pagesize = os.sysconf("SC_PAGE_SIZE")
        try:
            entries = list(Path("/proc").iterdir())
        except OSError as e:
            raise RuntimeError("cannot enumerate Linux process memory: " + str(e))
        for entry in entries:
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
                pgid = int(fields[2])
                if pgid in group_ids:
                    rss = int(fields[21]) * pagesize / 1024 ** 2
                    result[pgid] = result.get(pgid, 0) + rss
            except (FileNotFoundError, ProcessLookupError):
                continue
            except (OSError, ValueError, IndexError) as e:
                raise RuntimeError("cannot read Linux process-group RSS: " + str(e))
        return result
    p = subprocess.run(["ps", "-axo", "pgid=,rss="], capture_output=True, text=True, timeout=5)
    result = {}
    if p.returncode != 0:
        raise RuntimeError("cannot monitor process-group RSS: " + p.stderr.strip())
    for line in p.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2:
            pgid, rss = map(int, fields)
            result[pgid] = result.get(pgid, 0) + rss / 1024.0
    return result


def basic_record(task, a, status, reason):
    meta, v = task["meta"], task["vmeta"]
    return {"method": task["method"]["adapter"], "version": None,
            "config": task["method"]["config"], "instance": meta["name"],
            "variant": task["variant"], "rows": v.get("rows"), "cols": v.get("cols"),
            "obs": v.get("obs"), "threads": task["threads"], "time_limit": a.time_limit,
            "status": status, "lower_bound": None, "upper_bound": None,
            "witness": None, "witness_ok": None, "seconds": 0.0, "trace": [],
            "peak_rss_mb": None, "truth": v.get("distance"),
            "truth_kind": v.get("distance_kind"), "agrees_with_truth": None, "notes": reason}


def harness_info(task, a):
    return {"method_spec": task["method"]["spec"], "adapter": task["method"]["adapter"],
            "config_string": task["method"]["config_string"], "method_kind": task["method"]["kind"],
            "instance_dir": str(task["instance"]), "family": task["meta"].get("family", "unknown"),
            "memory_limit_gb": a.mem_gb, "time_limit": a.time_limit}


def finalize(run, a):
    task, process = run["task"], run["process"]
    elapsed = round(time.monotonic() - run["started_monotonic"], 6)
    run["stdout"].close()
    run["stderr"].close()
    tail = stderr_tail(run["stderr_path"])
    reason = run.get("kill_reason")
    rec = None
    try:
        with task["out"].open() as f:
            rec = json.load(f)
        if not isinstance(rec, dict):
            raise ValueError("record must be an object")
        for key in ("instance", "variant", "status", "seconds", "trace", "lower_bound", "upper_bound"):
            if key not in rec:
                raise ValueError("record missing " + key)
        if rec["instance"] != task["meta"]["name"] or rec["variant"] != task["variant"]:
            raise ValueError("record instance/variant does not match the requested run")
        if rec["status"] not in common.STATUSES:
            raise ValueError("invalid status: " + str(rec["status"]))
        json.dumps(rec, allow_nan=False)
        seconds = rec["seconds"]
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("seconds must be finite and nonnegative")
        if rec.get("threads") != task["threads"]:
            raise ValueError("record threads do not match the requested run")
        for field in ("lower_bound", "upper_bound"):
            value = rec[field]
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError(field + " must be a nonnegative integer or null")
        if not isinstance(rec["trace"], list):
            raise ValueError("trace must be a list")
        for event in rec["trace"]:
            if not isinstance(event, dict):
                raise ValueError("trace events must be objects")
            t = event.get("t")
            if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or t < 0:
                raise ValueError("trace time must be finite and nonnegative")
            for field in ("lb", "ub"):
                if field in event and (isinstance(event[field], bool) or not isinstance(event[field], int) or event[field] < 0):
                    raise ValueError("trace bounds must be nonnegative integers")
        if rec["upper_bound"] is not None and not (rec.get("value_only") is True and rec.get("witness") is None):
            witness = rec.get("witness")
            if witness is None or any(not isinstance(j, int) or isinstance(j, bool) or j < 0 for j in witness):
                raise ValueError("upper bound has no valid column-index witness")
            prob = common.load(str(task["instance"]), task["variant"])
            chk = common.check_witness(prob, witness)
            rec["witness_ok"] = chk["ok"] and chk["weight"] == rec["upper_bound"]
            if not rec["witness_ok"]:
                reason = reason or "witness failed independent harness check: " + str(chk)
        value_only = rec.get("value_only") is True and rec.get("witness") is None
        if rec["status"] == "exact" and (rec["lower_bound"] is None or
                rec["lower_bound"] != rec["upper_bound"] or not (rec.get("witness_ok") or value_only)):
            reason = reason or "exact record lacks equal certified bounds and a checked witness"
    except (OSError, ValueError, TypeError, KeyError, IndexError) as e:
        rec = None
        reason = reason or "adapter did not write a valid record: " + str(e)
    if process.returncode != 0 and not run.get("kill_reason"):
        if any(x in "\n".join(tail).lower() for x in ("memoryerror", "bad_alloc", "cannot allocate memory", "out of memory")):
            exit_reason = "memory limit/allocation failure (stderr evidence)"
        elif process.returncode < 0:
            exit_reason = "terminated by signal %s; memory or external kill possible" % signal.Signals(-process.returncode).name
        else:
            exit_reason = "adapter exited with code %d" % process.returncode
        reason = exit_reason + ("; " + reason if reason else "")
    if rec is None:
        rec = basic_record(task, a, "error", reason or "adapter exited without a record")
        rec["seconds"] = elapsed
    adapter_seconds = rec.get("seconds", 0)
    if not isinstance(adapter_seconds, (int, float)) or not math.isfinite(adapter_seconds) or adapter_seconds < 0:
        adapter_seconds = elapsed
        reason = reason or "record has invalid elapsed seconds"
    if reason:
        rec["status"] = "error"
        rec["notes"] = reason + ("; " + str(rec["notes"]) if rec.get("notes") and rec["notes"] != reason else "")
    info = harness_info(task, a)
    info.update({"cpus": run["cpus"], "started_at": run["started_at"], "ended_at": utc_now(),
                 "wall_seconds": elapsed, "adapter_seconds": adapter_seconds,
                 "trace_offset_seconds": round(max(0.0, elapsed - adapter_seconds), 6),
                 "exit_code": process.returncode, "error_reason": reason, "stderr_tail": tail,
                 "stdout_file": str(run["stdout_path"]), "stderr_file": str(run["stderr_path"]),
                 "memory_enforcement": a.memory_enforcement,
                 # the authoritative memory figure: the record's own peak_rss_mb is the adapter's view
                 # (its process and reaped children) and misses workers and external solvers
                 "peak_group_rss_mb": round(run.get("peak_rss_mb", 0.0), 1),
                 "peak_group_rss_sampling": "process-group RSS sampled every 0.1 s (short spikes can be missed)"})
    rec["harness"] = info
    write_json(task["out"], rec)
    return rec


def redo_matches(rec, filters):
    # Each --redo is an OR clause; comma-separated fields within a clause are AND.
    for clause in filters:
        if all(str(rec.get(k)) in values for k, values in clause):
            return True
    return False


def make_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--methods", required=True)
    ap.add_argument("--instances", default="all")
    ap.add_argument("--variants", default="sector,full")
    ap.add_argument("--threads", default="1", help="one count or comma-separated counts")
    ap.add_argument("--time-limit", type=float, default=3600)
    ap.add_argument("--mem-gb", type=float, default=32)
    ap.add_argument("--total-mem-gb", type=float, default=200)
    ap.add_argument("--jobs", type=int, default=8)
    allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else list(range(os.cpu_count() or 1))
    ap.add_argument("--cpus", default=",".join(map(str, allowed)))
    ap.add_argument("--out", default="results/bench")
    ap.add_argument("--give-up", type=int)
    ap.add_argument("--redo", action="append", default=[], help="e.g. status=timeout|error; repeat for OR")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--adapter-dir", default=str(HERE / "adapters"))
    ap.add_argument("--instance-dir", default=str(HERE / "instances"))
    ap.add_argument("--heuristic-methods", default="", help="comma-separated adapters or complete specs exempt from give-up")
    return ap


def main(argv=None):
    ap = make_parser()
    a = ap.parse_args(argv)
    try:
        for key in ("time_limit", "mem_gb", "total_mem_gb"):
            val = getattr(a, key)
            if not math.isfinite(val) or val <= 0:
                raise ValueError(key.replace("_", "-") + " must be positive and finite")
        threads = [int(x) for x in a.threads.split(",")]
        if not threads or min(threads) < 1 or len(set(threads)) != len(threads):
            raise ValueError("threads must be unique positive counts")
        cpus = parse_cpus(a.cpus)
        if a.jobs < 1 or a.jobs * max(threads) > len(cpus):
            raise ValueError("jobs x maximum threads must fit the private CPU pool")
        if hasattr(os, "sched_getaffinity") and not set(cpus).issubset(os.sched_getaffinity(0)):
            raise ValueError("requested CPUs are outside this process's permitted affinity")
        if a.mem_gb > a.total_mem_gb:
            raise ValueError("one job's memory limit exceeds total-mem-gb")
        if a.give_up is not None and a.give_up < 1:
            raise ValueError("give-up must be positive")
        variants = a.variants.split(",")
        if len(set(variants)) != len(variants) or any(not VALID_NAME.fullmatch(v) for v in variants):
            raise ValueError("invalid or duplicate variants")
        heuristic_names = set(group_specs(a.heuristic_methods)) if a.heuristic_methods.strip() else set()
        methods = parse_methods(a.methods, Path(a.adapter_dir).resolve(), heuristic_names)
        instances = select_instances(a.instances, Path(a.instance_dir).resolve())
        filters = []
        for clause in a.redo:
            pairs = []
            for term in clause.split(","):
                k, sep, v = term.partition("=")
                if not sep or not k or not v:
                    raise ValueError("redo filters must be key=value")
                pairs.append((k, v.split("|")))
            filters.append(pairs)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as e:
        ap.error(str(e))
    out = Path(a.out).resolve()
    tasks = []
    for path, meta in instances:
        for variant in variants:
            if variant not in meta.get("variants", {}):
                print("warning: %s has no %s variant; omitted" % (meta["name"], variant), file=sys.stderr)
                continue
            for method in methods:
                for thread in threads:
                    vm = meta["variants"][variant]
                    tasks.append({"instance": path, "meta": meta, "variant": variant, "vmeta": vm,
                                  "method": method, "threads": thread,
                                  "chain": (method["spec"], meta.get("family", "unknown"), variant, thread),
                                  "out": out / method["folder"] / (meta["name"] + "__" + variant + "__t%d.json" % thread)})
    tasks.sort(key=lambda t: (t["meta"].get("family", "unknown"), t["vmeta"]["cols"],
                              t["meta"]["name"], t["variant"], t["method"]["spec"], t["threads"]))
    if not tasks:
        ap.error("selection contains no available instance variants")
    for task in tasks:
        task["existing"] = None
        if task["out"].exists():
            try:
                rec = json.loads(task["out"].read_text())
                if not isinstance(rec, dict):
                    rec = {"status": "error"}
            except (OSError, ValueError):
                rec = {"status": "error"}
            saved_spec = rec.get("harness", {}).get("method_spec") if isinstance(rec.get("harness"), dict) else None
            if saved_spec is not None and saved_spec != task["method"]["spec"]:
                ap.error("existing record method identity differs: " + str(task["out"]))
            if not redo_matches(rec, filters):
                task["existing"] = rec
    a.taskset = None
    warnings = []
    if sys.platform == "darwin":
        warnings.append("macOS: taskset pinning skipped; CPU sets are reserved logically only")
    else:
        a.taskset = shutil.which("taskset")
        if not a.taskset:
            ap.error("taskset is required for CPU pinning on this platform")
    if a.dry_run:
        for warning in warnings:
            print("warning: " + warning, file=sys.stderr)
        for task in tasks:
            print(("resume " if task["existing"] is not None else "run ") + str(task["out"]))
        print("%d combinations; at most %d concurrent runs" % (len(tasks), min(a.jobs, int(a.total_mem_gb // a.mem_gb))))
        return 0
    nbytes = int(a.mem_gb * 1024 ** 3)
    supported, limit_error = as_limit_supported(nbytes)
    if supported:
        a.memory_enforcement = "RLIMIT_AS plus process-group RSS polling (0.1 s; possible RSS overshoot)"
    elif sys.platform == "darwin":
        a.memory_enforcement = "process-group RSS polling (0.1 s; possible overshoot)"
        warnings.append("macOS rejected RLIMIT_AS; using process-group RSS monitoring: " + limit_error.splitlines()[-1])
    else:
        ap.error("cannot enforce RLIMIT_AS: " + limit_error)
    for warning in warnings:
        print("warning: " + warning, file=sys.stderr)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    invocation = {"command_line": [sys.executable, str(Path(__file__).resolve())] + (list(argv) if argv is not None else sys.argv[1:]),
                  "host": platform.node(), "pid": os.getpid(), "cpu_model": cpu_model(), "platform": platform.platform(),
                  "python": sys.version, "started_at": utc_now(), "ended_at": None,
                  "versions": package_versions(), "cpus": cpus, "jobs": a.jobs,
                  "threads": threads, "mem_gb": a.mem_gb, "total_mem_gb": a.total_mem_gb,
                  "time_limit": a.time_limit, "hard_kill_grace_seconds": 30,
                  "give_up": a.give_up, "give_up_grouping": "method/config, family, variant, threads",
                  "memory_enforcement": a.memory_enforcement, "warnings": warnings,
                  "trace_timing": "adapter trace plus conservative wall_seconds - adapter_seconds offset",
                  "planned": len(tasks), "ran": 0, "resumed": 0, "skipped": 0}
    record_invocation(manifest_path, invocation)
    pending, running, active_chains = deque(tasks), [], set()
    state = {}
    free_cpus = list(cpus)
    memory_slots = max(1, int((a.total_mem_gb + 1e-9) // a.mem_gb))
    maximum_runs = min(a.jobs, memory_slots)

    def record_outcome(task, rec):
        if task["method"]["kind"] == "heuristic" or not a.give_up:
            return
        chain = state.setdefault(task["chain"], {"failures": 0, "cutoff": None})
        if rec.get("status") == "skipped":
            return
        if rec.get("status") == "exact":
            chain["failures"] = 0
            chain["cutoff"] = None
        else:
            chain["failures"] += 1
            if chain["failures"] >= a.give_up and chain["cutoff"] is None:
                chain["cutoff"] = task["vmeta"]["cols"]

    interrupted = None
    try:
        while pending or running:
            count = len(pending)
            blocked_chains = set()
            for _ in range(count):
                task = pending.popleft()
                ordered = a.give_up and task["method"]["kind"] != "heuristic"
                if ordered and (task["chain"] in active_chains or task["chain"] in blocked_chains):
                    pending.append(task)
                    continue
                if task["existing"] is not None:
                    invocation["resumed"] += 1
                    record_outcome(task, task["existing"])
                    print("resume " + str(task["out"]), flush=True)
                    continue
                chain = state.get(task["chain"], {})
                if chain.get("cutoff") is not None and task["vmeta"]["cols"] > chain["cutoff"]:
                    reason = "give-up after %d consecutive non-exact results in method/family/variant/threads; larger than %d columns" % (a.give_up, chain["cutoff"])
                    rec = basic_record(task, a, "skipped", reason)
                    rec["harness"] = dict(harness_info(task, a), skip_reason=reason)
                    write_json(task["out"], rec)
                    invocation["skipped"] += 1
                    print("skipped " + str(task["out"]), flush=True)
                    continue
                if len(running) >= maximum_runs or len(free_cpus) < task["threads"]:
                    pending.append(task)
                    if ordered:
                        blocked_chains.add(task["chain"])
                    continue
                private = free_cpus[:task["threads"]]
                del free_cpus[:task["threads"]]
                task["out"].parent.mkdir(parents=True, exist_ok=True)
                # A redo must never mistake a stale adapter result for this run's output.
                if task["out"].exists():
                    task["out"].unlink()
                command = [sys.executable, str(task["method"]["path"]), "--instance", str(task["instance"]),
                           "--variant", task["variant"], "--time-limit", str(a.time_limit),
                           "--threads", str(task["threads"]), "--out", str(task["out"])]
                if task["method"]["config_string"]:
                    command += ["--config", task["method"]["config_string"]]
                if a.taskset:
                    command = [a.taskset, "-c", ",".join(map(str, private))] + command
                env = os.environ.copy()
                env.update({k: str(task["threads"]) for k in THREAD_VARS})
                env["PYTHONPATH"] = os.pathsep.join([str(HERE), str(HERE.parent)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
                stdout_path = task["out"].with_suffix(".stdout.log")
                stderr_path = task["out"].with_suffix(".stderr.log")
                stdout, stderr = stdout_path.open("w"), stderr_path.open("w")
                start = time.monotonic()
                started_at = utc_now()
                try:
                    process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env,
                                               start_new_session=True,
                                               preexec_fn=limit_address_space(nbytes) if supported else None)
                except (OSError, subprocess.SubprocessError) as e:
                    stdout.close()
                    stderr.close()
                    free_cpus.extend(private)
                    free_cpus.sort(key=cpus.index)
                    rec = basic_record(task, a, "error", "could not launch adapter: " + str(e))
                    rec["harness"] = dict(harness_info(task, a), error_reason=rec["notes"], cpus=private)
                    write_json(task["out"], rec)
                    record_outcome(task, rec)
                    invocation["ran"] += 1
                    continue
                running.append({"task": task, "process": process, "cpus": private,
                                "started_monotonic": start, "started_at": started_at,
                                "stdout": stdout, "stderr": stderr,
                                "stdout_path": stdout_path, "stderr_path": stderr_path})
                active_chains.add(task["chain"])
                invocation["ran"] += 1
                print("start %s cpus=%s" % (task["out"], private), flush=True)
            rss = group_memory_mb({run["process"].pid for run in running}) if running else {}
            for run in list(running):
                process = run["process"]
                # peak resident memory of the whole process group (adapter, workers, external solvers)
                run["peak_rss_mb"] = max(run.get("peak_rss_mb", 0.0), rss.get(process.pid, 0.0))
                if process.poll() is None:
                    if time.monotonic() - run["started_monotonic"] >= a.time_limit + 30:
                        run["kill_reason"] = "killed by harness wall-time deadline (time-limit + 30 s)"
                        kill_group(process)
                    elif rss.get(process.pid, 0) > a.mem_gb * 1024:
                        run["kill_reason"] = "killed by memory limit (process-group RSS exceeded %.3f GiB)" % a.mem_gb
                        kill_group(process)
                    if process.poll() is None:
                        continue
                # Terminate descendants even if the adapter's main process exited first.
                kill_group(process)
                rec = finalize(run, a)
                running.remove(run)
                active_chains.discard(run["task"]["chain"])
                free_cpus.extend(run["cpus"])
                free_cpus.sort(key=cpus.index)
                record_outcome(run["task"], rec)
                print("done %s %s (%.3f s)" % (run["task"]["out"], rec["status"], rec["harness"]["wall_seconds"]), flush=True)
            if running:
                time.sleep(0.1)
    except (KeyboardInterrupt, RuntimeError) as e:
        interrupted = str(e) or "interrupted by user"
    finally:
        for run in running:
            run["kill_reason"] = "harness interrupted: " + (interrupted or "unexpected failure")
            kill_group(run["process"])
            run["process"].wait()
            finalize(run, a)
        invocation["ended_at"] = utc_now()
        invocation["interrupted"] = interrupted
        record_invocation(manifest_path, invocation)
    return 130 if interrupted else 0


if __name__ == "__main__":
    sys.exit(main())
