"""Validate exported benchmark instances and independently rerun the reference adapter.

Run with ``OMP_NUM_THREADS=2 .venv/bin/python tests/test_bench_export.py``.
The exact distances are read exclusively from each instance's metadata.  A
Table 3 code that times out is reported as unconfirmed, as the suite request
permits confirming those paper values only where the adapter finishes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import common
import instances as registry
from cdist import problem as cdist_problem, symmetry

RESULTS = ROOT / "results" / "bench_dev" / "suite"
LOGS = ROOT / "logs" / "bench_dev" / "suite"
MEMORY_KIB = 2 * 1024 * 1024
MEMORY_BYTES = MEMORY_KIB * 1024

if sys.platform.startswith("linux") and hasattr(resource, "RLIMIT_AS"):
    MEMORY_RESOURCE = resource.RLIMIT_AS
    MEMORY_POLICY = "Linux RLIMIT_AS: hard 2 GiB address-space ceiling; recorded peak RSS checked after completion"
elif hasattr(resource, "RLIMIT_RSS"):
    MEMORY_RESOURCE = resource.RLIMIT_RSS
    MEMORY_POLICY = "macOS RLIMIT_RSS requested where supported (advisory); rejection is logged; no live RSS monitoring; preflight and recorded peak RSS checked after completion"
else:
    MEMORY_RESOURCE = None
    MEMORY_POLICY = "No supported process memory limit; adapter execution is unavailable"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def peak_rss_kib():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / 1024 if sys.platform == "darwin" else value


def combined_row_basis(prob):
    """Triangular GF(2) basis of the rows of [H; L], over column positions."""
    width = (prob.ncols + 7) // 8
    packed = [bytearray(width) for _ in range(prob.nrows + prob.nobs)]
    for column, (h, logical) in enumerate(zip(prob.h, prob.l)):
        byte, bit = column // 8, 1 << (column % 8)
        for row in common.bits(h):
            packed[row][byte] |= bit
        for row in common.bits(logical):
            packed[prob.nrows + row][byte] |= bit
    basis = {}
    for data in packed:
        value = int.from_bytes(data, "little")
        while value:
            pivot = value.bit_length() - 1
            existing = basis.get(pivot)
            if existing is None:
                basis[pivot] = value
                break
            value ^= existing
    return basis


def row_in_span(value, basis):
    while value:
        existing = basis.get(value.bit_length() - 1)
        if existing is None:
            return False
        value ^= existing
    return True


def validate_logical_map(prob, column_map, basis):
    """Equivalent to cdist.symmetry._labels_consistent's existence of M, B.

    The permuted logical labels satisfy L' = M L + B H precisely when every
    row of L' lies in the row span of [H; L].  Reusing that span avoids solving
    the same large input system again for each stored permutation.
    """
    width = (prob.ncols + 7) // 8
    rows = [bytearray(width) for _ in range(prob.nobs)]
    for column, image in enumerate(column_map):
        byte, bit = column // 8, 1 << (column % 8)
        for row in common.bits(prob.l[image]):
            rows[row][byte] |= bit
    return all(row_in_span(int.from_bytes(row, "little"), basis) for row in rows)


def extend_logical_group(known, generator):
    """Compositions of verified H/L automorphisms also preserve span(H,L).

    All candidates still get an independent column-set check. This cache
    avoids repeating logical elimination for powers/products of checked
    translations; the bounded cache is optional and never accepts a guess.
    """
    queue = list(known)
    known.add(tuple(generator))
    queue.append(tuple(generator))
    position = 0
    while position < len(queue) and len(known) < 512:
        old = queue[position]
        position += 1
        for product in (tuple(generator[r] for r in old), tuple(old[r] for r in generator)):
            if product not in known:
                known.add(product)
                queue.append(product)


def validate_variant(instance, variant, metadata):
    prob = common.load(str(instance), variant)
    require(prob.distance_kind in ("exact", "lower_bound", "unknown"),
            "%s: unsupported distance kind" % variant)
    require(prob.distance is None or (isinstance(prob.distance, int) and not isinstance(prob.distance, bool)
                                    and prob.distance >= 1), "%s: invalid distance metadata" % variant)
    require(prob.distance_kind == "unknown" or prob.distance is not None,
            "%s: certified distance kind has no value" % variant)
    for key, actual in (("rows", prob.nrows), ("cols", prob.ncols), ("obs", prob.nobs)):
        require(metadata.get(key) == actual, "%s: incorrect %s metadata" % (variant, key))
    require(all(0 <= h < (1 << prob.nrows) for h in prob.h), "%s: H row outside matrix" % variant)
    require(all(0 <= l < (1 << prob.nobs) for l in prob.l), "%s: L row outside matrix" % variant)
    if prob.rowmeta is not None:
        require(len(prob.rowmeta) == prob.nrows, "%s: incorrect rowmeta length" % variant)
    p = common.to_cdist(prob)
    perms = prob.perms or []
    require(metadata.get("symmetries", 0) == len(perms), "%s: incorrect symmetry count" % variant)
    column_index = {h: column for column, h in enumerate(prob.h)} if perms else {}
    require(not perms or len(column_index) == prob.ncols,
            "%s: stored symmetries require unique syndrome columns" % variant)
    basis = combined_row_basis(prob) if perms else {}
    logical_group = {tuple(range(prob.nrows))}
    sanity_checked = False
    for index, perm in enumerate(perms):
        label = "%s permutation %d" % (variant, index)
        require(isinstance(perm, list) and len(perm) == prob.nrows, label + ": incorrect length")
        require(all(isinstance(x, int) and not isinstance(x, bool) for x in perm), label + ": noninteger row")
        require(sorted(perm) == list(range(prob.nrows)), label + ": not bijective")
        # Identity is a valid stored permutation, although from_row_perms drops it.
        if all(i == x for i, x in enumerate(perm)):
            continue
        column_map = []
        for h in prob.h:
            image = 0
            for row in common.bits(h):
                image |= 1 << perm[row]
            require(image in column_index, label + ": does not preserve the syndrome column set")
            column_map.append(column_index[image])
        require(len(set(column_map)) == prob.ncols, label + ": column map is not bijective")
        if tuple(perm) not in logical_group:
            require(validate_logical_map(prob, column_map, basis), label + ": logical labels are inconsistent")
            extend_logical_group(logical_group, perm)
        if not sanity_checked and prob.ncols <= 500 and prob.nrows <= 100:
            sym = symmetry.from_row_perms(p, [perm])
            require(sym.get("ok") and sym.get("n_symmetries_kept") == 1,
                    label + ": independent row-span check disagrees with from_row_perms")
            sanity_checked = True
    require(peak_rss_kib() <= MEMORY_KIB, "test process exceeded 2 GiB RSS")
    return prob


def validate_sector(full, sector):
    keys = ("distance", "distance_kind", "distance_source")
    fm, sm = full.meta["variants"]["full"], full.meta["variants"]["sector"]
    require(tuple(fm.get(k) for k in keys) == tuple(sm.get(k) for k in keys),
            "full and sector truth, kind, or source differ")
    require(full.rowmeta is not None and sector.rowmeta is not None,
            "circuit variants require detector row metadata")
    rowindex = {tuple(row): i for i, row in enumerate(full.rowmeta)}
    require(len(rowindex) == full.nrows, "full detector coordinates are not unique")
    rows = [rowindex[tuple(row)] for row in sector.rowmeta]
    require(len(set(rows)) == sector.nrows, "sector detector coordinates are not unique")
    p, q = common.to_cdist(full), common.to_cdist(sector)
    require(set(rows) == set(cdist_problem.sector_rows(p)), "sector rows differ from memory-basis rows")
    projected = cdist_problem.project_rows(p, [[r] for r in rows], q.name, q.row_meta)
    require(projected.nobs == q.nobs and Counter(zip(projected.h, projected.l)) == Counter(zip(q.h, q.l)),
            "stored sector columns differ from the projection of full")
    q.notes["sector_rows"] = rows
    require(cdist_problem.sector_is_exact(p, q), "sector reduction does not preserve distance exactly")


def table3_truth(prob):
    source = str(prob.meta["variants"][prob.variant].get("distance_source") or "").lower()
    return prob.meta.get("track") == "code" and "2308.07915" in source and bool(re.search(r"table\s*3", source))


def adapter_memory_preflight(prob, k_table):
    """Conservative allocation estimate for the chosen truth-independent table size.

    Table(..., load=0.5, labelfree=True) uses one uint64 key and one uint8
    cost per slot; the slot count is rounded up to a power of two.  Reserve
    512 MiB for imports, interpreter, logical elimination, and worker/task
    buffers, then account for the dense C arrays and Python exclusion pairs.
    This estimate supports the advisory macOS guard; it is not a live RSS
    measurement and does not replace the returned peak-RSS check.
    """
    require(prob.ncols < 5000, "adapter preflight requires fewer than 5000 columns")
    n = prob.ncols
    pairs = n * (n - 1) // 2
    entries = sum(math.comb(n, i) for i in range(k_table + 1))
    slots = 1 << max(10, (2 * entries).bit_length())
    rowcounts = [0] * prob.nrows
    nnz = 0
    maximum_weight = 0
    for column in prob.h:
        rows = common.bits(column)
        maximum_weight = max(maximum_weight, len(rows))
        nnz += len(rows)
        for row in rows:
            rowcounts[row] += 1
    seen_pairs_upper = min(pairs, sum(count * (count - 1) // 2 for count in rowcounts))
    words = max(1, (prob.nrows + 63) // 64)
    logical_words = max(1, (prob.nobs + 63) // 64)
    table_bytes = slots * 9 + 4 * 1024 * 1024  # aligned key/cost allocation overhead
    array_bytes = 32 * n * (words + logical_words) + 128 * nnz
    covering_bytes = nnz * (8 * words if words <= 8 else 4 * maximum_weight)
    # Seen tuple/set entries and exclusion partner sets, including spare capacity.
    exclusion_bytes = 256 * seen_pairs_upper
    estimated = table_bytes + array_bytes + covering_bytes + exclusion_bytes + 512 * 1024 * 1024
    return {"k_table": k_table, "fits_memory_ceiling": estimated < MEMORY_BYTES,
            "table_entries_upper": entries, "table_slots": slots,
            "table_estimate_mb": round(table_bytes / 1024 ** 2, 1),
            "process_estimate_mb": round(estimated / 1024 ** 2, 1)}


def apply_adapter_memory_limit():
    """Called in the subprocess before exec; respect any stricter inherited cap."""
    if MEMORY_RESOURCE is None:
        raise RuntimeError("no supported process memory limit")
    soft, hard = resource.getrlimit(MEMORY_RESOURCE)
    ceiling = MEMORY_BYTES if hard == resource.RLIM_INFINITY else min(MEMORY_BYTES, hard)
    desired = ceiling if soft == resource.RLIM_INFINITY else min(ceiling, soft)
    try:
        resource.setrlimit(MEMORY_RESOURCE, (desired, ceiling))
    except (OSError, ValueError) as exc:
        if sys.platform.startswith("linux"):
            raise
        # macOS can reject even an advisory RSS cap; do not bypass sandbox
        # restrictions.  The preflight and returned peak-RSS check remain.
        os.write(2, ("Advisory RSS limit unavailable: %s: %s\n" % (type(exc).__name__, exc)).encode())


def kill_adapter(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait(timeout=5)


def run_adapter(instance, prob, limit):
    preflight = adapter_memory_preflight(prob, 2)
    if prob.meta.get("track") == "code":
        candidate = adapter_memory_preflight(prob, 3)
        if candidate["fits_memory_ceiling"]:
            preflight = candidate
    require(preflight["fits_memory_ceiling"],
            "conservative adapter preflight estimates %.1f MiB, above the 2 GiB ceiling" % preflight["process_estimate_mb"])
    config = {"k_table": str(preflight["k_table"])}
    require(MEMORY_RESOURCE is not None, MEMORY_POLICY)
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    stem = "%s__%s" % (prob.name, prob.variant)
    out, log = RESULTS / (stem + ".json"), LOGS / (stem + ".log")
    if out.exists():
        out.unlink()
    temporary = Path(str(out) + ".tmp")
    if temporary.exists():
        temporary.unlink()
    cmd = [sys.executable, str(ROOT / "bench" / "adapters" / "ours.py"),
           "--instance", str(instance), "--variant", prob.variant,
           "--time-limit", str(limit), "--threads", "2", "--out", str(out)]
    cmd.extend(["--config", "k_table=" + config["k_table"]])
    env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2",
               PYTHONDONTWRITEBYTECODE="1")
    start = time.monotonic()
    termination = None
    with log.open("w") as stream:
        stream.write("command: %s\n" % " ".join(cmd))
        stream.write("memory guard: %s\n" % MEMORY_POLICY)
        stream.write("memory preflight: %s\n" % json.dumps(preflight, sort_keys=True))
        stream.flush()
        proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=stream, stderr=subprocess.STDOUT,
                                start_new_session=True, preexec_fn=apply_adapter_memory_limit)
        try:
            while proc.poll() is None:
                if time.monotonic() - start >= limit + 5:
                    termination = "adapter exceeded its wall-time limit plus 5 seconds"
                    kill_adapter(proc)
                    break
                time.sleep(0.25)
        finally:
            if proc.poll() is None:
                kill_adapter(proc)
    wall = round(time.monotonic() - start, 3)
    if termination is not None:
        return None, {"wall_seconds": wall, "max_rss_mb": None, "memory_preflight": preflight, "config": config,
                      "error": termination, "log": str(log.relative_to(ROOT))}
    require(proc.returncode == 0, "adapter exited %s; see %s" % (proc.returncode, log.relative_to(ROOT)))
    require(out.exists(), "adapter did not write a result; see %s" % log.relative_to(ROOT))
    with out.open() as f:
        record = json.load(f)
    return record, {"wall_seconds": wall, "max_rss_mb": record.get("peak_rss_mb"), "memory_preflight": preflight,
                    "config": config,
                    "result": str(out.relative_to(ROOT)), "log": str(log.relative_to(ROOT))}


def validate_result(prob, record):
    rss = record.get("peak_rss_mb")
    require(isinstance(rss, (int, float)) and not isinstance(rss, bool) and math.isfinite(rss) and rss >= 0,
            "adapter result lacks a finite peak_rss_mb")
    require(rss <= MEMORY_KIB / 1024, "adapter recorded peak RSS above 2 GiB")
    require(record.get("instance") == prob.name and record.get("variant") == prob.variant,
            "adapter result identifies a different problem")
    for key, actual in (("rows", prob.nrows), ("cols", prob.ncols), ("obs", prob.nobs)):
        require(record.get(key) == actual, "adapter result has incorrect %s" % key)
    require(record.get("threads") == 2, "adapter did not record requested threads=2")
    status, lb, ub = record.get("status"), record.get("lower_bound"), record.get("upper_bound")
    require(status in common.STATUSES, "adapter reported an invalid status")
    require(status not in ("error", "unavailable"), "adapter status=%s: %s" % (status, record.get("notes")))
    for label, value in (("lower bound", lb), ("upper bound", ub)):
        require(value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 1),
                "adapter %s is not a positive integer" % label)
    require(lb is None or ub is None or lb <= ub, "adapter bounds contradict each other")
    if ub is not None:
        witness = record.get("witness")
        require(isinstance(witness, list), "upper bound has no witness")
        require(all(isinstance(j, int) and not isinstance(j, bool) and 0 <= j < prob.ncols for j in witness),
                "witness contains an invalid column index")
        check = common.check_witness(prob, witness)
        require(check["ok"] and check["weight"] == ub and record.get("witness_ok") is True,
                "upper-bound witness fails independent validation")
    else:
        require(record.get("witness") is None, "witness has no upper bound")
    if status == "exact":
        require(lb is not None and lb == ub, "exact status lacks matching certified bounds")
    truth, kind = prob.distance, prob.distance_kind
    require(record.get("truth") == truth and record.get("truth_kind") == kind,
            "adapter result truth differs from instance metadata")
    if kind == "exact" and truth is not None:
        require(lb is None or lb <= truth, "adapter lower bound exceeds exact truth")
        require(ub is None or ub >= truth, "adapter upper bound is below exact truth")
        require(record.get("agrees_with_truth") is not False, "adapter disagrees with exact truth")
        if status == "exact":
            require(lb == ub == truth, "adapter exact result differs from recorded truth")
            return "confirmed", True
        return "unconfirmed", table3_truth(prob) and status == "timeout"
    if kind == "lower_bound" and truth is not None:
        require(ub is None or ub >= truth, "adapter witness contradicts the recorded lower bound")
    require(kind in ("exact", "lower_bound", "unknown"), "unsupported distance kind %r" % kind)
    return "compatible_%s" % kind, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated exported instance names")
    parser.add_argument("--checks-only", action="store_true", help="validate matrices and symmetries without running adapters")
    parser.add_argument("--time-limit", type=float, default=120, help="adapter wall-time limit in seconds (default: 120)")
    parser.add_argument("--total-time-limit", type=float, default=900, help="whole test budget in seconds (default: 900; raise for server verification)")
    args = parser.parse_args()
    require(args.time_limit > 0 and args.total_time_limit > 0, "time limits must be positive")
    names = {name.strip() for name in args.only.split(",") if name.strip()} if args.only else None
    instances = sorted((ROOT / "bench" / "instances").glob("*/meta.json"))
    available = {path.parent.name for path in instances}
    if names is not None:
        require(names <= available, "requested instances are not exported: %s" % ", ".join(sorted(names - available)))
        instances = [path for path in instances if path.parent.name in names]
    require(bool(instances), "no exported instances found")
    if not args.checks_only:
        print("Memory guard: " + MEMORY_POLICY, flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    results = []
    failures = 0
    for path in instances:
        instance = path.parent
        rec = {"instance": instance.name}
        try:
            require(time.monotonic() - started < args.total_time_limit, "total test budget exhausted before structural checks")
            with path.open() as f:
                meta = json.load(f)
            require(meta.get("name") == instance.name, "instance name differs from its directory")
            require(meta.get("track") in ("circuit", "code"), "invalid instance track")
            require(bool(meta.get("variants")), "instance has no variants")
            probs = {variant: validate_variant(instance, variant, vm) for variant, vm in meta["variants"].items()}
            if meta["track"] == "circuit":
                if registry.INSTANCES.get(instance.name, {}).get("variants") == ("full",):
                    require(set(probs) == {"full"}, "full-only circuit must have only full variant")
                    variant = "full"
                else:
                    require("full" in probs and "sector" in probs, "circuit instance lacks full or sector variant")
                    validate_sector(probs["full"], probs["sector"])
                    variant = "sector"
            else:
                require(set(probs) == {"full"}, "code instance must have only full variant")
                variant = "full"
            prob = probs[variant]
            rec.update({"variant": variant, "cols": prob.ncols, "truth": prob.distance,
                        "truth_kind": prob.distance_kind, "structural_checks": "passed"})
            if args.checks_only:
                rec["verification"] = "checks_only"
                print("PASS %s: structural checks" % instance.name, flush=True)
            elif prob.ncols >= 5000:
                rec["verification"] = "not_eligible"
                print("PASS %s: structural checks; adapter skipped (%d columns >= 5000)" % (instance.name, prob.ncols), flush=True)
            elif args.total_time_limit - (time.monotonic() - started) < args.time_limit + 5:
                rec["verification"] = "unconfirmed"
                rec["error"] = "remaining total budget cannot accommodate a complete adapter run"
                failures += 1
                print("UNCONFIRMED %s: %s" % (instance.name, rec["error"]), flush=True)
            else:
                record, details = run_adapter(instance, prob, args.time_limit)
                rec.update(details)
                if record is None:
                    rec["verification"] = "unconfirmed"
                    failures += 1
                    print("UNCONFIRMED %s: %s" % (instance.name, rec["error"]), flush=True)
                else:
                    require(record.get("time_limit") == args.time_limit, "adapter did not record requested time limit")
                    require(record.get("config") == rec["config"], "adapter config differs from the memory-based choice")
                    outcome, passed = validate_result(prob, record)
                    rec.update({"verification": outcome, "adapter_status": record["status"],
                                "lower_bound": record["lower_bound"], "upper_bound": record["upper_bound"]})
                    if not passed:
                        failures += 1
                    label = "UNCONFIRMED" if outcome == "unconfirmed" else "PASS"
                    extra = "; paper Table 3 timeout permitted" if outcome == "unconfirmed" and passed else ""
                    print("%s %s: %s; bounds %s..%s, truth %s (%s)%s" %
                          (label, instance.name, record["status"], record["lower_bound"], record["upper_bound"],
                           prob.distance, prob.distance_kind, extra), flush=True)
        except Exception as exc:
            failures += 1
            rec.update({"verification": "failed", "error": "%s: %s" % (type(exc).__name__, exc)})
            print("FAIL %s: %s" % (instance.name, rec["error"]), flush=True)
        results.append(rec)
    summary = {"checks_only": args.checks_only, "time_limit": args.time_limit,
               "memory_guard": MEMORY_POLICY,
               "adapter_config_policy": "circuits: k_table=2; codes: k_table=3 when conservative memory preflight fits 2 GiB, otherwise 2",
               "total_time_limit": args.total_time_limit, "seconds": round(time.monotonic() - started, 3),
               "failures": failures, "instances": results}
    suffix = "__" + hashlib.sha256(",".join(sorted(names)).encode()).hexdigest()[:12] if names is not None else ""
    summary_path = RESULTS / ("export_test_summary" + suffix + ".json")
    with summary_path.open("w") as f:
        json.dump(summary, f, indent=1)
    print("%d instances checked; %d failures; report %s" %
          (len(results), failures, summary_path.relative_to(ROOT)), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
