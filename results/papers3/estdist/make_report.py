"""Regenerate estdist summary.csv and remaining.md from one local snapshot.

Usage: .venv/bin/python results/papers3/estdist/make_report.py [local.json]

No distance searches or logical-basis computations are performed.  Existing
rebuilt parameters and separate row weights are reused; missing values need
only matrix construction and integer GF(2) ranks.  Python 3.9, standard library.
"""
from __future__ import annotations

import csv
import io
import json
import math
import shlex
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "results/papers3/estdist"
sys.path.insert(0, str(ROOT / "papers"))
sys.path.insert(0, str(ROOT))
import estimated_codes as codes


def _rank(rows):
    pivots = {}
    for row in rows:
        while row:
            pivot = row.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = row
                break
            row ^= pivots[pivot]
    return len(pivots)


def _rebuilt(code, record):
    weights = record.get("row_weights_by_type", {})
    checks = record.get("checks", {})
    if (isinstance(record.get("n"), int) and isinstance(record.get("k"), int)
            and all(b in weights and b in checks for b in "XZ")):
        return record["n"], record["k"], weights, checks, "local_checkpoint"
    hx, hz, n = codes.matrices(code["name"])
    k = n - _rank(hx) - _rank(hz)
    weights = {b: sorted({bin(row).count("1") for row in rows})
               for b, rows in (("X", hx), ("Z", hz))}
    checks = {"X": len(hx), "Z": len(hz)}
    return n, k, weights, checks, "matrix_and_rank"


def _overall(record):
    sectors = record.get("distance", {})
    ds = [sectors.get(b, {}).get("d") for b in "ZX"]
    lbs = [sectors.get(b, {}).get("lower_bound") for b in "ZX"]
    ubs = [sectors.get(b, {}).get("upper_bound") for b in "ZX"]
    lower = min(lbs) if all(x is not None for x in lbs) else None
    upper = min(x for x in ubs if x is not None) if any(x is not None for x in ubs) else None
    exact = min(ds) if all(x is not None for x in ds) else record.get("d")
    if lower is not None and lower == upper:
        exact = lower
    seconds = (sum(sectors[b].get("seconds", 0) for b in "ZX")
               if all(b in sectors for b in "ZX") else record.get("seconds"))
    return exact, lower, upper, seconds


def _estimate(result, target):
    """Empirical cost through target, using only completed exhaustive runs."""
    if result.get("d") is not None:
        return {"seconds": 0.0, "text": "Already exact; no remaining search."}
    # Resumption may repeat a K.  Use the latest completed exhaustive run at K.
    complete = {int(r["K"]): r for r in result.get("runs", [])
                if r.get("status") == "exhausted" and r.get("nodes") is not None}
    if not complete:
        return {"seconds": None, "text": "Pilot needed: no exhausted threshold history."}
    last = max(complete)
    window = [complete[last]]
    while len(window) < 4 and last - len(window) in complete:
        window.append(complete[last - len(window)])
    window.reverse()
    counts = [sum(r["nodes"]) for r in window]
    history = "; ".join("K={}: {} nodes, {:.4g}s".format(r["K"], count, r.get("seconds", 0))
                        for r, count in zip(window, counts))
    if len(window) < 2 or any(count <= 0 for count in counts):
        return {"seconds": None, "text": "Pilot needed: fewer than two usable consecutive exhausted thresholds. " + history}
    growth = statistics.median(counts[i] / counts[i - 1] for i in range(1, len(counts)))
    timed = [complete[k] for k in sorted(complete)
             if complete[k].get("seconds", 0) >= 0.01 and sum(complete[k]["nodes"]) > 0]
    details = "g={:.4g}; exhausted history: {}".format(growth, history)
    timing = timed[-1] if timed else window[-1]
    timing_seconds = timing["seconds"] if timed else max(timing.get("seconds", 0), 0.01)
    unit = timing_seconds / sum(timing["nodes"])
    details += "; seconds/node={:.4g} from K={} ({:.4g}s)".format(unit, timing["K"], timing_seconds)
    if not timed:
        details += "; explicit 0.01s timing floor: measured sub-10ms timings are noisy; empirical estimate only"
    start = max(last + 1, result.get("lower_bound") or 1)
    if start > target:
        return {"seconds": None, "text": "Claimed weight {} already exhausted; a higher-distance pilot is needed. ".format(target) + details}
    predicted_nodes = sum(counts[-1] * growth ** (k - last) for k in range(start, target + 1))
    estimate = unit * predicted_nodes
    if not math.isfinite(estimate):
        return {"seconds": None, "text": "Pilot needed: extrapolation overflowed. " + details}
    text = "Through K={}: approximately {}; broad range {}–{}. ".format(
        target, _duration(estimate), _duration(estimate / 3), _duration(estimate * 10))
    return {"seconds": estimate, "text": text + details}


def _duration(seconds):
    if seconds < 60:
        return "{:.3g}s".format(seconds)
    if seconds < 3600:
        return "{:.3g}min".format(seconds / 60)
    if seconds < 86400:
        return "{:.3g}h".format(seconds / 3600)
    return "{:.3g}days".format(seconds / 86400)


def _atomic_text(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main(local_path=None):
    local_path = Path(local_path) if local_path else OUTPUT / "local.json"
    snapshot = json.loads(local_path.read_text()) if local_path.exists() else {"codes": []}
    local = {r["name"]: r for r in snapshot["codes"]}
    fields = ["name", "arxiv", "status", "claim_kind", "locator", "n", "k", "paper_n", "paper_k",
              "d_claimed", "parameters_match_paper", "checks_X", "checks_Z", "row_weights_X", "row_weights_Z"]
    for basis in "ZX":
        fields += ["{}_{}".format(key, basis) for key in
                   ("d", "lower_bound", "upper_bound", "last", "stop_reason", "seconds",
                    "symmetries_candidates", "symmetries_kept")]
    fields += ["d", "lower_bound", "upper_bound", "seconds", "local_record", "parameters_source"]
    rows, unresolved, discrepancies = [], [], []
    for code in codes.CODES:
        record = local.get(code["name"], {})
        n, k, weights, checks, source = _rebuilt(code, record)
        paper_n, paper_k = code.get("paper_n", code["n"]), code.get("paper_k", code["k"])
        exact, lower, upper, seconds = _overall(record)
        row = {key: code.get(key) for key in ("name", "arxiv", "status", "claim_kind", "locator", "d_claimed")}
        row.update(n=n, k=k, paper_n=paper_n, paper_k=paper_k,
                   parameters_match_paper=(n, k) == (paper_n, paper_k), d=exact,
                   lower_bound=lower, upper_bound=upper, seconds=seconds,
                   local_record=bool(record), parameters_source=source)
        for b in "XZ":
            row["checks_" + b] = checks[b]
            row["row_weights_" + b] = ";".join(str(w) for w in weights[b])
        for b in "ZX":
            result = record.get("distance", {}).get(b, {})
            for key in ("d", "lower_bound", "upper_bound", "last", "stop_reason", "seconds",
                        "symmetries_candidates", "symmetries_kept"):
                row[key + "_" + b] = result.get(key)
        rows.append(row)
        if (n, k) != (paper_n, paper_k) or k == 0:
            discrepancies.append((code, n, k, paper_n, paper_k))
        if k > 0 and exact is None:
            unresolved.append((code, row, record))

    csv_text = io.StringIO(newline="")
    writer = csv.DictWriter(csv_text, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    lines = ["# Remaining estimated-code distance searches", "",
             "Snapshot: `{}`; {} registry entries, {} unresolved logical codes. Actual local kernel threads: {}.".format(
                 local_path.name, len(rows), len(unresolved), snapshot.get("threads", "unknown")), "",
             "CSV blanks mean unknown or not run. Per-basis unknown distances remain blank even when the overall code distance is exact.", "",
             "Cost estimates use the last two to four consecutive exhausted thresholds only. Found and timed-out searches are excluded because their counts are incomplete. Growth g is the median successive node-count ratio; seconds per node comes from the latest exhausted timing of at least 0.01s. When all timings are shorter, an explicitly labeled 0.01s floor at the last exhausted threshold supplies a conservative baseline for noisy sub-10ms measurements. Predicted threshold costs are summed through the paper's claimed weight across unresolved bases, or one less than an independently verified upper bound when that already closes the certificate. The displayed /3 to ×10 range is empirical, not rigorous, and excludes setup/table building, server speed differences, and work above the claim. No family estimates are borrowed.", "",
             "Commands use independent output files, so they start from weight 1. A matching matrix-hash checkpoint copied from local.json into that file permits resumption. Forecasts concern remaining work after the local certificates, so fresh runs repeat completed thresholds. Per-threshold caps are at least1800s, increased to three times the largest predicted remaining basis cost when needed. A timeout preserves completed thresholds, but the interrupted threshold restarts; increase its cap if it repeatedly times out.", ""]
    if discrepancies:
        lines += ["## Parameter discrepancies", ""]
        for code, n, k, pn, pk in discrepancies:
            extra = " No logical distance exists and no server command is supplied." if k == 0 else ""
            lines.append("- `{}`: rebuilt [[{},{}]], paper [[{},{}]], claimed d={}.{} Locator: {}.".format(
                code["name"], n, k, pn, pk, code["d_claimed"], extra, code["locator"]))
        lines.append("")
    lines += ["## Commands and empirical cost", ""]
    if not unresolved:
        lines += ["Every rebuilt code with k>0 has a certified overall distance.", ""]
    for code, row, record in unresolved:
        name, target = code["name"], int(code["d_claimed"])
        lines += ["### {}".format(name), "",
                  "arXiv:{}; {}; rebuilt [[{},{}]], paper [[{},{}]], claimed d={}. Local overall bounds: {} ≤ d ≤ {}.".format(
                      code["arxiv"], code["status"], row["n"], row["k"], row["paper_n"], row["paper_k"], target,
                      row["lower_bound"] if row["lower_bound"] is not None else "unknown",
                      row["upper_bound"] if row["upper_bound"] is not None else "unknown"), ""]
        estimates = []
        for basis in "ZX":
            result = record.get("distance", {}).get(basis, {})
            endpoint = min(target, result["upper_bound"] - 1) if result.get("upper_bound") else target
            estimate = _estimate(result, endpoint)
            estimates.append(estimate)
            lines.append("- {} basis: {}".format(basis, estimate["text"]))
        if all(e["seconds"] is not None for e in estimates):
            total = sum(e["seconds"] for e in estimates)
            lines += ["", "Combined remaining search estimate through claimed weight: approximately {}; broad range {}–{}.".format(
                _duration(total), _duration(total / 3), _duration(total * 10))]
        else:
            lines += ["", "Combined cost: pilot needed for the basis without adequate exhaustive history; no complete numeric estimate is available."]
        measured = [e["seconds"] for e in estimates if e["seconds"] is not None]
        cap = max(1800, math.ceil(3 * max(measured))) if measured else 1800
        command = "OMP_NUM_THREADS=2 ESTDIST_TOTAL_SECONDS=0 .venv/bin/python papers/estimated_codes_run.py {} {} {} {}".format(
            shlex.quote("results/papers3/estdist/server_" + name + ".json"), max(20, target), cap, shlex.quote(name))
        lines += ["", "```sh", command, "```", "", "Locator: {}.".format(code["locator"]), ""]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _atomic_text(OUTPUT / "summary.csv", csv_text.getvalue())
    _atomic_text(OUTPUT / "remaining.md", "\n".join(lines))
    print("Wrote summary.csv ({} codes) and remaining.md ({} commands, {} parameter discrepancies).".format(
        len(rows), len(unresolved), len(discrepancies)))


if __name__ == "__main__":
    main(*sys.argv[1:])
