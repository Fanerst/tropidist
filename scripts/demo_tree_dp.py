#!/usr/bin/env python3
"""Bounded exact tree-DP demonstration, optionally replaying a saved problem.

Examples (run from the repository root):
  python scripts/demo_tree_dp.py
  python scripts/demo_tree_dp.py --input results/dense_audit_20261021/inputs/code_bb72/full.json.gz \
      --order results/dense_audit_20261021/widths/code_bb72__full.json.gz --shape chunks \
      --output results/rw_tree_audit_20261021/tree/code_bb72_chunks.json

The chunked tree has balanced four-column subtrees joined in a comb. It is
a genuine binary tree with internal/internal joins, but is not claimed to
minimize width. All observable rows are solved before reporting distance.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

# Bound library execution before importing NumPy or a legacy kernel.
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cdist import kernel, trellis
from cdist.tree_dp import CompiledTreeDP, TreeDPResourceError, build_tree_kernel


def balanced(order):
    if not order:
        return None
    if len(order) == 1:
        return order[0]
    middle = len(order) // 2
    return balanced(order[:middle]), balanced(order[middle:])


def comb(parts):
    if not parts:
        return None
    tree = parts[0]
    for part in parts[1:]:
        tree = tree, part
    return tree


def read_json(path):
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--order", type=Path)
    parser.add_argument("--shape", choices=("balanced", "comb", "chunks"), default="balanced")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-memory-bytes", type=int, default=256 << 20)
    parser.add_argument("--max-join-work", type=int, default=100_000_000,
                        help="aggregate bound across all observable queries")
    parser.add_argument("--max-seconds", type=float, default=60.0,
                        help="aggregate bound, including compilation and trellis comparisons")
    args = parser.parse_args()
    if args.input:
        problem = read_json(args.input)
        h, l = ([int(v, 16) for v in problem[key]] for key in ("h", "l"))
        nobs, nrows = problem["nobs"], problem["nrows"]
        identity = {"path": str(args.input), "compressed_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
                    "input_sha256": problem.get("input_sha256"), "name": problem["name"],
                    "variant": problem["variant"]}
    else:
        h, l = [1, 2, 4, 7, 3, 5, 6, 1], [1, 0, 0, 0, 0, 0, 0, 0]
        nobs, nrows = 1, 3
        identity = {"name": "synthetic_branching_demo", "h": h, "l": l}
    order = read_json(args.order)["order"] if args.order else list(range(len(h)))
    if sorted(order) != list(range(len(h))):
        raise ValueError("saved order must contain every column exactly once")
    tree = (balanced(order) if args.shape == "balanced" else comb(order) if args.shape == "comb"
            else comb([balanced(order[i:i + 4]) for i in range(0, len(order), 4)]))
    # Build outside timed execution, then record hashes of exactly used sources.
    build_tree_kernel()
    kernel.build()
    source = Path(__file__).resolve().parents[1] / "cdist"
    results = {
        "input": identity, "shape": args.shape, "order": order,
        "ncols": len(h), "nobs": nobs, "limits": vars(args).copy(),
        "sources_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                           for name in ("tree_dp.py", "tree_dp.c", "trellis.py", "kernel.py")},
        "queries": [], "status": "incomplete", "distance": None,
        "threads": 1, "rss_scope": "whole fresh process, including Python, NumPy and retained query reports",
    }
    for key in ("input", "order", "output"):
        results["limits"][key] = str(results["limits"][key]) if results["limits"][key] else None
    # Retain an unambiguous flat postorder witness without recursive JSON depth.
    witness = CompiledTreeDP(h, tree)
    results["tree_nodes"] = [node.leaf if node.leaf is not None else [node.left, node.right]
                              for node in witness.nodes]
    results["internal_internal_joins"] = sum(
        node.leaf is None and witness.nodes[node.left].leaf is None and witness.nodes[node.right].leaf is None
        for node in witness.nodes)
    del witness
    begin, used_work = time.monotonic(), 0

    def remaining_seconds():
        remaining = args.max_seconds - (time.monotonic() - begin)
        if remaining <= 0:
            raise TreeDPResourceError("aggregate wall-time budget exhausted")
        return remaining

    try:
        for observable in range(nobs):
            columns = [hc | (((lc >> observable) & 1) << nrows) for hc, lc in zip(h, l)]
            program = CompiledTreeDP(columns, tree, max_compile_seconds=remaining_seconds())
            distance, stats = program.run(
                1 << nrows, max_memory_bytes=args.max_memory_bytes,
                max_join_work=args.max_join_work - used_work, max_seconds=remaining_seconds())
            used_work += stats["join_work_done"]
            row = {"observable": observable, "distance": distance, "tree": stats}
            plan = trellis.build_plan(h, l, 1 << observable, order, nrows)
            if (1 << plan.peak_bits) <= args.max_memory_bytes and len(h) < 255:
                expected, legacy = kernel.run_plan(plan)
                if expected != distance:
                    raise AssertionError((observable, expected, distance))
                row["trellis"] = dict(legacy, distance=expected, peak_table_bytes=1 << plan.peak_bits,
                                       plan_work=plan.work(), crosscheck="equal")
            remaining_seconds()
            results["queries"].append(row)
        feasible = [row["distance"] for row in results["queries"] if row["distance"] is not None]
        results["distance"] = min(feasible) if feasible else None
        results["status"] = "exact"
    except TreeDPResourceError as error:
        results["status"] = "resource_rejected"
        results["rejection"] = str(error)
        results["rejection_profile"] = error.profile
    results["seconds"] = time.monotonic() - begin
    results["join_work_done"] = used_work
    results["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n")
    summary = {key: results[key] for key in ("status", "distance", "ncols", "nobs", "shape", "internal_internal_joins", "seconds", "join_work_done", "peak_rss_bytes")}
    summary["max_dense_bytes"] = max((row["tree"]["peak_dense_bytes"] for row in results["queries"]), default=0)
    print(json.dumps(summary, sort_keys=True))
    return 0 if results["status"] == "exact" else 2


if __name__ == "__main__":
    raise SystemExit(main())
