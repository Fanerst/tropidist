#!/usr/bin/env python3
"""Turn benchmark JSON records into auditable Markdown tables and CSV data.

Timing comparisons use cumulative certified bounds in each adapter's trace.  A
harness trace_offset_seconds is added when present, so the clock starts at
process launch.  Exact records without a convergent trace are shown but excluded
from timed comparisons; completion time is not silently substituted for a trace.
Only instance metadata with distance_kind == "exact" is an exact ground truth.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote


HERE = Path(__file__).resolve().parent
DEFAULT_INSTANCES = HERE / "instances"
TERMINAL_STATUSES = {"exact", "bounds", "timeout", "unavailable", "error", "skipped"}


def number(value: Any) -> Optional[float]:
    """A finite, nonnegative JSON number (not a boolean)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def bound(value: Any) -> Optional[int]:
    value = number(value)
    return int(value) if value is not None and value.is_integer() else None


def escaped(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def pretty_seconds(value: float) -> str:
    return "{:.1f}".format(value)


def normalized_trace(data: Dict[str, Any], offset: float = 0.0) -> List[Dict[str, Any]]:
    """Return finite bound events, ordered by time, on the harness wall clock."""
    events = []
    raw = data.get("trace", [])
    if not isinstance(raw, list):
        return events
    for event in raw:
        if not isinstance(event, dict):
            continue
        t = number(event.get("t"))
        if t is None:
            continue
        clean = {"t": t + offset}
        for name in ("lb", "ub"):
            value = bound(event.get(name))
            if value is not None:
                clean[name] = value
        if len(clean) > 1:
            events.append(clean)
    return sorted(events, key=lambda event: event["t"])


def time_to_exact(data: Dict[str, Any], offset: float = 0.0) -> Optional[float]:
    """First trace time at which cumulative certified bounds meet, if exact."""
    lb, ub = None, None
    final_lb, final_ub = bound(data.get("lower_bound")), bound(data.get("upper_bound"))
    if data.get("status") != "exact" or final_lb is None or final_lb != final_ub:
        return None
    for event in normalized_trace(data, offset):
        if "lb" in event:
            lb = event["lb"] if lb is None else max(lb, event["lb"])
        if "ub" in event:
            ub = event["ub"] if ub is None else min(ub, event["ub"])
        if lb is not None and ub is not None and lb == ub == final_lb:
            return event["t"]
    return None


def time_to_truth(data: Dict[str, Any], truth: Optional[int], offset: float = 0.0) -> Optional[float]:
    """First trace time reaching a known exact distance with an upper bound."""
    if truth is None:
        return None
    for event in normalized_trace(data, offset):
        if event.get("ub") == truth:
            return event["t"]
    return None


class Record:
    def __init__(self, path: Path, data: Dict[str, Any], metadata: Dict[str, Any],
                 metadata_path: Optional[Path], metadata_fallback: bool = False,
                 result_root: Optional[Path] = None):
        self.path, self.data, self.metadata, self.metadata_path = path, data, metadata, metadata_path
        self.result_root = result_root
        self.harness = data.get("harness") if isinstance(data.get("harness"), dict) else {}
        self.instance, self.variant = str(data["instance"]), str(data["variant"])
        self.threads = bound(data.get("threads")) or 1
        self.method = self._method()
        self.method_key = (self.method, self.threads)
        self.problem_key = (self.instance, self.variant)
        self.status = str(data.get("status", "error"))
        self.variant_metadata = metadata.get("variants", {}).get(self.variant, {})
        self.truth_kind = self.variant_metadata.get("distance_kind", "unknown")
        self.truth = bound(self.variant_metadata.get("distance"))
        self.rows = bound(self.variant_metadata.get("rows"))
        self.cols = bound(self.variant_metadata.get("cols"))
        self.rows = self.rows if self.rows is not None else bound(data.get("rows"))
        self.cols = self.cols if self.cols is not None else bound(data.get("cols"))
        self.lb, self.ub = bound(data.get("lower_bound")), bound(data.get("upper_bound"))
        self.offset = number(self.harness.get("trace_offset_seconds")) or 0.0
        self.seconds = number(self.harness.get("wall_seconds"))
        if self.seconds is None:
            self.seconds = number(data.get("seconds"))
        self.limit = number(data.get("time_limit"))
        self.wrong: List[str] = []
        self.issues: List[str] = []
        self.metadata_fallback = metadata_fallback
        self._validate()
        self.valid = not self.wrong and not self.issues and self.status not in {"error", "unavailable", "skipped"}
        self.exact_time = time_to_exact(data, self.offset) if self.valid else None
        self.truth_time = time_to_truth(data, self.truth if self.truth_kind == "exact" else None, self.offset) if self.valid else None
        self.lb_at_limit = self._lower_at_limit()

    def _method(self) -> str:
        spec = self.harness.get("method_spec")
        if spec:
            return str(spec)
        adapter = self.harness.get("adapter")
        config_string = self.harness.get("config_string")
        if adapter:
            return str(adapter) + (":" + str(config_string) if config_string else "")
        # The record's tool name can differ from the adapter name (ours_search).
        # A matrix directory is the most reliable legacy identifier for configs.
        if self.result_root is not None and self.path.parent != self.result_root:
            return self.path.parent.name
        config = self.data.get("config")
        suffix = ",".join("{}={}".format(k, config[k]) for k in sorted(config)) if isinstance(config, dict) else ""
        return str(self.data.get("method", "unknown")) + (":" + suffix if suffix else "")

    def _validate(self) -> None:
        if bound(self.data.get("threads")) is None or bound(self.data.get("threads")) == 0:
            self.issues.append("threads must be a positive integer")
        if self.status not in TERMINAL_STATUSES:
            self.issues.append("unknown status {!r}".format(self.status))
        for name in ("lower_bound", "upper_bound"):
            if self.data.get(name) is not None and bound(self.data[name]) is None:
                self.issues.append("invalid " + name)
        if self.lb is not None and self.ub is not None and self.lb > self.ub:
            self.wrong.append("lower bound {} exceeds upper bound {}".format(self.lb, self.ub))
        if self.truth is not None and self.truth_kind == "exact":
            if self.lb is not None and self.lb > self.truth:
                self.wrong.append("lower bound {} exceeds exact truth {}".format(self.lb, self.truth))
            if self.ub is not None and self.ub < self.truth:
                self.wrong.append("upper bound {} is below exact truth {}".format(self.ub, self.truth))
            if self.status == "exact" and self.ub != self.truth:
                self.wrong.append("claimed exact answer {} differs from exact truth {}".format(self.ub, self.truth))
        elif self.truth is not None and self.truth_kind == "lower_bound" and self.ub is not None and self.ub < self.truth:
            self.wrong.append("upper bound {} is below known lower bound {}".format(self.ub, self.truth))
        if self.status == "exact" and (self.lb is None or self.lb != self.ub):
            self.issues.append("exact status requires equal non-null certified bounds")
        if self.ub is not None and not (self.data.get("value_only") is True and self.data.get("witness") is None):
            witness = self.data.get("witness")
            if self.data.get("witness_ok") is not True:
                self.issues.append("upper-bound witness failed validation or was not checked")
            if not isinstance(witness, list) or len(witness) != self.ub:
                self.issues.append("upper bound does not match a stored witness")
            elif any(bound(j) is None or (self.cols is not None and j >= self.cols) for j in witness) or len(set(witness)) != len(witness):
                self.issues.append("stored witness has invalid or duplicate column indices")
        for name, actual in (("rows", self.rows), ("cols", self.cols)):
            reported = bound(self.data.get(name))
            if actual is not None and reported is not None and reported != actual:
                self.issues.append("record {} disagrees with instance metadata".format(name))
        # Final bounds must cover all trace claims; otherwise statistics could
        # silently attribute a stronger proof than the record actually retains.
        for event in normalized_trace(self.data, self.offset):
            if "lb" in event and (self.lb is None or event["lb"] > self.lb):
                self.issues.append("trace lower bound exceeds the final certified lower bound")
                break
            if "ub" in event and (self.ub is None or event["ub"] < self.ub):
                self.issues.append("trace upper bound improves on the final stored witness")
                break

    def _lower_at_limit(self) -> Optional[int]:
        if not self.valid or self.lb is None:
            return None
        timed = []
        for event in normalized_trace(self.data, self.offset):
            if "lb" in event and (self.limit is None or event["t"] <= self.limit):
                timed.append(event["lb"])
        if timed:
            return max(timed)
        # A final bound on a run that ended before the limit is a conservative
        # fallback. It is explicitly labelled "final record" in Table 4.
        if self.seconds is not None and (self.limit is None or self.seconds <= self.limit):
            return self.lb
        return None


def read_records(root: Path, instance_root: Path) -> Tuple[List[Record], List[str]]:
    records, warnings = [], []
    metadata_cache: Dict[Path, Tuple[Dict[str, Any], Optional[Path]]] = {}
    for path in sorted(root.rglob("*.json")):
        if path.name in {"manifest.json", "meta.json"}:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            warnings.append("Could not read {}: {}".format(path, exc))
            continue
        if not isinstance(data, dict) or not {"instance", "variant", "status"}.issubset(data):
            continue
        harness = data.get("harness") if isinstance(data.get("harness"), dict) else {}
        candidates = []
        if harness.get("instance_dir"):
            original = Path(str(harness["instance_dir"]))
            candidates.append(original / "meta.json")
            if not original.is_absolute():
                candidates.append(HERE.parent / original / "meta.json")
        candidates.append(instance_root / str(data["instance"]) / "meta.json")
        metadata, metadata_path = {}, None
        for candidate in candidates:
            if not candidate.is_file():
                continue
            candidate = candidate.resolve()
            if candidate not in metadata_cache:
                try:
                    meta = json.loads(candidate.read_text(encoding="utf-8"))
                    if not isinstance(meta, dict) or not isinstance(meta.get("variants", {}), dict):
                        raise ValueError("metadata is not an instance object")
                    metadata_cache[candidate] = (meta, candidate)
                except (OSError, ValueError) as exc:
                    warnings.append("Could not read metadata {}: {}".format(candidate, exc))
                    metadata_cache[candidate] = ({}, None)
            metadata, metadata_path = metadata_cache[candidate]
            if metadata_path is not None:
                break
        fallback = metadata_path is None or not isinstance(metadata.get("variants", {}).get(str(data["variant"])), dict)
        if fallback:
            warnings.append("{}: instance metadata unavailable for this variant; using record truth and dimensions".format(path))
            metadata = {"name": data["instance"], "family": "unknown", "variants": {
                data["variant"]: {"rows": data.get("rows"), "cols": data.get("cols"),
                                  "distance": data.get("truth"), "distance_kind": data.get("truth_kind", "unknown")}}}
        records.append(Record(path.resolve(), data, metadata, metadata_path, fallback, root.resolve()))
    return records, warnings


class Sources:
    """A compact source ledger lets aggregate cells link to all contributing files."""
    def __init__(self, report_path: Path):
        self.report_path = report_path
        self.entries: List[Tuple[Path, ...]] = []
        self.index: Dict[Tuple[Path, ...], int] = {}

    def link(self, label: Any, path: Path) -> str:
        relative = os.path.relpath(str(path), str(self.report_path.parent))
        target = quote(relative.replace(os.sep, "/"), safe="/.-_")
        return "[{}]({})".format(escaped(label).replace("[", "\\[").replace("]", "\\]"), target)

    def cell(self, label: Any, paths: Sequence[Path]) -> str:
        unique = tuple(sorted(set(paths), key=str))
        if not unique:
            return escaped(label)
        if len(unique) == 1:
            return self.link(label, unique[0])
        if unique not in self.index:
            self.entries.append(unique)
            self.index[unique] = len(self.entries)
        return "[{}](#source-{:03d})".format(escaped(label), self.index[unique])

    def markdown(self) -> List[str]:
        if not self.entries:
            return []
        lines = ["## Aggregate sources", "", "Each linked set contains the record files used for that cell, including its fastest-method comparisons.", ""]
        for index, paths in enumerate(self.entries, 1):
            links = [self.link(os.path.relpath(str(path), str(self.report_path.parent)), path) for path in paths]
            lines.append('<a id="source-{:03d}"></a>Source {:03d}: {}.'.format(index, index, ", ".join(links)))
            lines.append("")
        return lines


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines + [""]


def is_heuristic(records: Sequence[Record]) -> bool:
    if any(record.lb is not None for record in records):
        return False
    kinds = {record.harness.get("method_kind") for record in records}
    if kinds.intersection({"proving", "certifying", "exact"}):
        return False
    return "heuristic" in kinds or any(record.ub is not None for record in records)


def bounds_text(record: Record) -> str:
    parts = []
    if record.lb is not None:
        parts.append(">= {}".format(record.lb))
    if record.ub is not None:
        parts.append("<= {}".format(record.ub))
    return ", ".join(parts)


def outcome(record: Optional[Record], heuristic: bool, sources: Sources) -> str:
    if record is None:
        return "not run"
    prefix = "WRONG: " if record.wrong else ""
    if record.status in {"unavailable", "skipped"}:
        text = record.status
    elif record.status == "error" or record.issues:
        text = (bounds_text(record) + " (error)") if record.lb is not None or record.ub is not None else "error"
    elif record.status == "exact":
        if record.exact_time is not None:
            text = "exact in {} s".format(pretty_seconds(record.exact_time))
            if record.data.get("value_only") is True:
                text += " (value only, no witness)"
        else:
            text = "exact (trace timing unavailable)"
            if record.seconds is not None:
                text += "; run {} s".format(pretty_seconds(record.seconds))
    elif heuristic and record.ub is not None:
        text = "<= {}".format(record.ub)
        if record.seconds is not None:
            text += " in {} s".format(pretty_seconds(record.seconds))
        text += " (heuristic{})".format("; timeout" if record.status == "timeout" else "")
    else:
        text = bounds_text(record) or "no bounds"
        text += " ({})".format(record.status)
    return sources.link(prefix + text, record.path)


def problem_sort(key: Tuple[str, str], records: Sequence[Record]) -> Tuple[Any, ...]:
    candidates = [record for record in records if record.problem_key == key]
    first = candidates[0]
    return (str(first.metadata.get("family", "unknown")), first.cols if first.cols is not None else math.inf,
            first.rows if first.rows is not None else math.inf, key[0], key[1])


def selected_records(records: Sequence[Record]) -> Tuple[Dict[Tuple[str, str, str, int], Record], List[str]]:
    chosen, warnings = {}, []
    for record in records:
        key = (record.instance, record.variant, record.method, record.threads)
        old = chosen.get(key)
        if old is None:
            chosen[key] = record
            continue
        newer, older = sorted((old, record), key=lambda rec: (rec.path.stat().st_mtime_ns, str(rec.path)), reverse=True)
        chosen[key] = newer
        warnings.append("Duplicate combination: using {}; retaining {} in summary.csv only".format(newer.path, older.path))
    return chosen, warnings


def write_csvs(root: Path, records: Sequence[Record], active: Sequence[Record]) -> Tuple[Path, Path]:
    summary_path, profile_path = root / "summary.csv", root / "profile.csv"
    active_paths = {record.path for record in active}
    columns = ["method", "adapter_method", "threads", "instance", "variant", "rows", "cols", "status",
               "lower_bound", "upper_bound", "truth", "truth_kind", "seconds", "time_limit", "time_to_exact",
               "time_to_truth", "lower_bound_at_limit", "wrong", "validation_issues", "selected_for_tables",
               "config", "record", "metadata"]
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow({"method": record.method, "adapter_method": record.data.get("method"), "threads": record.threads,
                             "instance": record.instance, "variant": record.variant, "rows": record.rows, "cols": record.cols,
                             "status": record.status, "lower_bound": record.lb, "upper_bound": record.ub,
                             "truth": record.truth, "truth_kind": record.truth_kind, "seconds": record.seconds,
                             "time_limit": record.limit, "time_to_exact": record.exact_time, "time_to_truth": record.truth_time,
                             "lower_bound_at_limit": record.lb_at_limit, "wrong": "; ".join(record.wrong),
                             "validation_issues": "; ".join(record.issues), "selected_for_tables": record.path in active_paths,
                             "config": json.dumps(record.data.get("config", {}), sort_keys=True),
                             "record": os.path.relpath(str(record.path), str(root)),
                             "metadata": str(record.metadata_path) if record.metadata_path else ""})
    with profile_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["method", "threads", "rank", "time_to_exact", "instance", "variant", "record"])
        methods = sorted({record.method_key for record in active})
        for method_key in methods:
            solved = sorted((record for record in active if record.method_key == method_key and record.exact_time is not None),
                            key=lambda record: (record.exact_time, record.instance, record.variant))
            for rank, record in enumerate(solved, 1):
                writer.writerow([record.method, record.threads, rank, record.exact_time, record.instance, record.variant,
                                 os.path.relpath(str(record.path), str(root))])
    return summary_path, profile_path


def generate_report(results_dir: Any, out_path: Any = None, instance_dir: Any = DEFAULT_INSTANCES) -> Dict[str, Any]:
    root = Path(results_dir).resolve()
    if not root.is_dir():
        raise ValueError("results directory does not exist: {}".format(root))
    report_path = Path(out_path).resolve() if out_path is not None else root / "BENCHMARK.md"
    records, warnings = read_records(root, Path(instance_dir).resolve())
    if not records:
        raise ValueError("no benchmark result records found in {}".format(root))
    chosen, duplicate_warnings = selected_records(records)
    warnings.extend(duplicate_warnings)
    active = list(chosen.values())
    summary_path, profile_path = write_csvs(root, records, active)
    sources = Sources(report_path)
    methods = sorted({record.method_key for record in active})
    method_records = {key: [record for record in active if record.method_key == key] for key in methods}
    heuristic = {key: is_heuristic(method_records[key]) for key in methods}
    multiple_threads = len({key[1] for key in methods}) > 1
    method_label = {key: key[0] + (" (t={})".format(key[1]) if multiple_threads else "") for key in methods}
    problems = sorted({record.problem_key for record in active}, key=lambda key: problem_sort(key, active))

    def find(problem: Tuple[str, str], method: Tuple[str, int]) -> Optional[Record]:
        return chosen.get((problem[0], problem[1], method[0], method[1]))

    def problem_cell(problem: Tuple[str, str]) -> str:
        record = next(record for record in active if record.problem_key == problem)
        label = "{} / {}".format(*problem)
        return sources.link(label, record.metadata_path or record.path)

    lines = ["# Circuit-distance benchmark", ""]
    wrong_records = [record for record in records if record.wrong]
    if wrong_records:
        lines += ["## WRONG results", "", "These records contradict ground truth or their own bounds. They are excluded from all performance statistics.", ""]
        for record in wrong_records:
            lines.append("- {}: {}.".format(sources.link("{} / {} / {} (t={})".format(record.method, record.instance, record.variant, record.threads), record.path),
                                            escaped("; ".join(record.wrong))))
        lines.append("")
    invalid = [record for record in records if record.issues]
    if invalid:
        lines += ["## Record validation issues", "", "These records are shown as errors and excluded from performance statistics.", ""]
        for record in invalid:
            lines.append("- {}: {}.".format(sources.link("{} / {} / {}".format(record.method, record.instance, record.variant), record.path),
                                            escaped("; ".join(record.issues))))
        lines.append("")
    if warnings:
        lines += ["## Input warnings", ""]
        lines.extend("- " + escaped(warning) for warning in warnings)
        lines.append("")
    lines += ["Each outcome links to its JSON record; instance names link to metadata. Aggregate cells link to every contributing record. Ground truth is taken from instance metadata; a known lower bound is shown with `>=` and is never treated as an exact answer.", "",
              "Exact and first-hit times come from cumulative trace bounds, with `harness.trace_offset_seconds` added when supplied. This conservative offset includes startup, instance loading, and shutdown overhead. Without a harness offset, times use the adapter trace clock. Exact results without a convergent trace have no time-to-exact statistic. Heuristic runtime cells use the total run time.", "",
              "Comparisons use the same thread count. Ties share first place; the geometric mean compares each exact time with the fastest valid exact run on the same instance, variant, and thread count. Errors, WRONG records, unavailable tools, skipped runs, and untimed exact results do not contribute. The CSV files retain every record, including duplicate combinations; tables select the newest duplicate.", ""]
    lines.append("Thread counts represented: {}. Data: {}, {}.".format(
        ", ".join(sources.cell(threads, [record.path for record in active if record.threads == threads]) for threads in sorted({key[1] for key in methods})),
        sources.link("summary.csv", summary_path), sources.link("profile.csv", profile_path)))
    lines.append("")

    lines += ["## Table 1. Outcomes", ""]
    rows = []
    for problem in problems:
        candidates = [record for record in active if record.problem_key == problem]
        first = candidates[0]
        provenance = [first.path] + ([first.metadata_path] if first.metadata_path else [])
        size = "{} x {}".format(first.rows if first.rows is not None else "?", first.cols if first.cols is not None else "?")
        truth = str(first.truth) if first.truth is not None and first.truth_kind == "exact" else (
            ">= {}".format(first.truth) if first.truth is not None and first.truth_kind == "lower_bound" else "unknown")
        rows.append([problem_cell(problem), sources.cell(size, provenance), sources.cell(truth, provenance)] +
                    [outcome(find(problem, method), heuristic[method], sources) for method in methods])
    lines += table(["Instance / variant", "H size (rows x columns)", "Ground truth"] + [escaped(method_label[key]) for key in methods], rows)

    lines += ["## Table 2. Exact performance", "", "Counts use time-to-exact from the trace. Ratios cover the instances both the method and a fastest exact method solved; the final column gives that comparison count. A zero-second trace produces no finite ratio and is excluded from the geometric mean.", ""]
    fastest: Dict[Tuple[str, str, int], List[Record]] = {}
    for record in active:
        if record.exact_time is None:
            continue
        key = (record.instance, record.variant, record.threads)
        current = fastest.get(key)
        if current is None or record.exact_time < current[0].exact_time and not math.isclose(record.exact_time, current[0].exact_time, rel_tol=1e-9, abs_tol=1e-9):
            fastest[key] = [record]
        elif math.isclose(record.exact_time, current[0].exact_time, rel_tol=1e-9, abs_tol=1e-9):
            current.append(record)
    rows = []
    for method in methods:
        all_method = method_records[method]
        solved = [record for record in all_method if record.exact_time is not None]
        cells = [escaped(method_label[method])]
        for limit in (60, 600, 3600):
            contributing = [record.path for record in solved if record.exact_time <= limit]
            cells.append(sources.cell(len(contributing), contributing or [record.path for record in all_method]))
        firsts, ratios, ratio_sources = [], [], []
        for record in solved:
            winners = fastest[(record.instance, record.variant, record.threads)]
            if record in winners:
                firsts.extend([record.path] + [winner.path for winner in winners])
            fastest_time = winners[0].exact_time
            if fastest_time > 0 and record.exact_time > 0:
                ratios.append(record.exact_time / fastest_time)
                ratio_sources.extend([record.path] + [winner.path for winner in winners])
        first_count = sum(record in fastest[(record.instance, record.variant, record.threads)] for record in solved)
        cells.append(sources.cell(first_count, firsts or [record.path for record in all_method]))
        geomean = math.exp(sum(math.log(ratio) for ratio in ratios) / len(ratios)) if ratios else None
        cells.append(sources.cell("{:.3f}".format(geomean) if geomean is not None else "n/a", ratio_sources or [record.path for record in all_method]))
        cells.append(sources.cell(len(ratios), ratio_sources or [record.path for record in all_method]))
        rows.append(cells)
    lines += table(["Method", "Exact <= 60 s", "Exact <= 600 s", "Exact <= 3600 s", "First-place finishes", "Geometric mean time ratio", "Compared instances"], rows)

    lines += ["## Table 3. Upper-bound-only methods", "", "A first-hit time is reported only for an independently known exact ground truth. Otherwise the cell gives the best stored upper bound and its additive gap, when known. Reaching a known lower bound alone does not establish the true distance.", ""]
    upper_methods = [method for method in methods if heuristic[method]]
    if not upper_methods:
        lines += ["No upper-bound-only methods were identified in these records.", ""]
    else:
        rows = []
        for problem in problems:
            cells = [problem_cell(problem)]
            for method in upper_methods:
                record = find(problem, method)
                if record is None or not record.valid or record.ub is None:
                    cells.append(outcome(record, True, sources))
                    continue
                if record.truth_time is not None:
                    text = "true distance first reached in {} s".format(pretty_seconds(record.truth_time))
                else:
                    text = "<= {}".format(record.ub)
                    text += ", gap {}".format(record.ub - record.truth) if record.truth is not None and record.truth_kind == "exact" else ", gap unknown"
                    if record.truth_kind == "exact" and record.ub == record.truth:
                        text += " (true distance; trace timing unavailable)"
                cells.append(sources.link(text, record.path))
            rows.append(cells)
        lines += table(["Instance / variant"] + [escaped(method_label[method]) for method in upper_methods], rows)

    lines += ["## Table 4. Certified lower bounds at the time limit", "", "Bounds persist after an early finish. Only trace events at or before the record's time limit are counted; `final record` marks a fallback when the run finished within the limit but supplied no timely lower-bound event. A run with no certified lower bound is shown explicitly.", ""]
    proof_methods = [method for method in methods if not heuristic[method]]
    if not proof_methods:
        lines += ["No methods proving lower bounds were identified in these records.", ""]
    else:
        rows = []
        for problem in problems:
            cells = [problem_cell(problem)]
            for method in proof_methods:
                record = find(problem, method)
                if record is None or not record.valid:
                    cells.append(outcome(record, False, sources))
                    continue
                limit = "{} s".format(pretty_seconds(record.limit)) if record.limit is not None else "unspecified limit"
                if record.lb_at_limit is None:
                    text = "no certified lower bound at " + limit
                else:
                    text = ">= {} at {}".format(record.lb_at_limit, limit)
                    has_event = any("lb" in event and (record.limit is None or event["t"] <= record.limit) for event in normalized_trace(record.data, record.offset))
                    if not has_event:
                        text += " (final record)"
                cells.append(sources.link(text, record.path))
            rows.append(cells)
        lines += table(["Instance / variant"] + [escaped(method_label[method]) for method in proof_methods], rows)
    lines += sources.markdown()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"report": str(report_path), "summary": str(summary_path), "profile": str(profile_path),
            "records": len(records), "wrong": len(wrong_records), "validation_issues": len(invalid), "warnings": warnings}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", help="directory containing matrix result records")
    parser.add_argument("--out", default=None, help="Markdown output (default: RESULTS/BENCHMARK.md)")
    parser.add_argument("--instance-dir", default=str(DEFAULT_INSTANCES), help="root containing instance metadata directories")
    args = parser.parse_args(argv)
    try:
        result = generate_report(args.results, args.out, args.instance_dir)
    except (ValueError, OSError) as exc:
        parser.exit(2, "report: {}\n".format(exc))
    print("Wrote {} ({} records, {} WRONG, {} validation issues)".format(result["report"], result["records"], result["wrong"], result["validation_issues"]))
    print("Wrote {} and {}".format(result["summary"], result["profile"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
