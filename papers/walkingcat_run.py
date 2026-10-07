"""Bounded local Walking Cat runs; does not modify the shared search pipeline.

Usage: OMP_NUM_THREADS=2 .venv/bin/python papers/walkingcat_run.py
       OMP_NUM_THREADS=2 .venv/bin/python papers/walkingcat_run.py --code-only
Each unfinished instance invokes run_parallel with rounds=6, k_coll=3,
kmax=12, seconds_per_threshold=600. A subprocess watchdog enforces a total
580-second limit per instance. Completed result files are skipped unless
--rerun is passed. Logs and execution metadata are retained even on timeout.
The largest k=3 table here is comfortably below the 2 GB process budget;
the runner records child peak RSS (macOS reports bytes, Linux reports KiB).
"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def check_codes(results):
    """Reproducible exact checks of both CSS distances, with verified witnesses."""
    sys.path.insert(0, str(ROOT))
    import stabcode
    import walkingcat
    from cdist import search, symmetry

    start = time.monotonic()
    records = {}
    for key in (102, 70, 54):
        hx, hz, n = walkingcat.matrices(key)
        n, k = stabcode.css_parameters(hx, hz, n)
        records[str(key)] = {"n": n, "k": k, "bases": {}}
        for basis in "ZX":
            before = time.monotonic()
            p = stabcode.css_distance_problem(hx, hz, n, basis, name=f"walkingcat{key}")
            sym = symmetry.from_row_perms(p, walkingcat.translations(key))
            assert sym["ok"]
            r = search.distance(p, k_table=3, kmax=walkingcat.CODES[key][2][2],
                                cover=True, time_limit=60,
                                rank=sym["rank"], anchors=sym["anchors"])
            witness = list(r["solutions"][0]) if r["solutions"] else None
            verified = bool(witness is not None and p.check(witness)[0] == 0
                            and p.check(witness)[1] != 0)
            rec = {"distance": r["distance"], "lower_bound": r["lower_bound"],
                   "verified_upper_bound": len(witness) if verified else None,
                   "witness_columns": witness, "verified": verified,
                   "symmetries_retained": sym["n_symmetries_kept"],
                   "symmetries_candidate": len(walkingcat.translations(key)),
                   "seconds": round(time.monotonic() - before, 6),
                   "runs": r["runs"]}
            records[str(key)]["bases"][basis] = rec
            print(f"code Q{key} {basis}: {rec['lower_bound']} <= d <= "
                  f"{rec['verified_upper_bound']}, {rec['seconds']}s", flush=True)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        peak *= 1024
    report = {"method": "css_distance_problem; exact distance(k_table=3,cover=True); "
                         "verified syndrome/logical witnesses",
              "threads_actual": search.lib().gm_num_threads(), "codes": records,
              "seconds": round(time.monotonic() - start, 6), "peak_rss_bytes": peak}
    (results / "code_distances_recheck.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wall-seconds", type=float, default=580)
    parser.add_argument("--threshold-seconds", type=float, default=600)
    parser.add_argument("--k-coll", type=int, choices=(2, 3), default=3)
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--code-only", action="store_true",
                        help="check both exact code distances for all three codes, then exit")
    args = parser.parse_args()
    if not 0 < args.wall_seconds <= 580:
        parser.error("wall-seconds must lie in (0,580]")
    if not 0 < args.threshold_seconds <= 600:
        parser.error("threshold-seconds must lie in (0,600]")
    env = dict(os.environ, OMP_NUM_THREADS="2", PYTHONUNBUFFERED="1")
    results = ROOT / "results/papers3/walkingcat"
    logs = ROOT / "logs/papers3/walkingcat"
    results.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    if args.code_only:
        check_codes(results)
        return
    records = []
    for key in (54, 70, 102):
        for basis in "ZX":
            tag = f"{key}_{basis}"
            out = results / f"{tag}.json"
            execution = results / f"{tag}_execution.json"
            if out.exists() and not args.rerun:
                previous = json.loads(out.read_text())
                if previous.get("seconds") is not None:
                    print(f"{tag}: completed result already present; skipping", flush=True)
                    if execution.exists():
                        records.append(json.loads(execution.read_text()))
                    continue
            cmd = [sys.executable, "papers/run_parallel.py", "walkingcat", str(key), basis,
                   str(out.relative_to(ROOT)), "6", str(args.k_coll), "12",
                   str(args.threshold_seconds)]
            print("Running OMP_NUM_THREADS=2 " + " ".join(cmd), flush=True)
            start = time.monotonic()
            with (logs / f"{tag}.log").open("w") as log:
                try:
                    r = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, timeout=args.wall_seconds)
                    rec = {"returncode": r.returncode, "timeout": False}
                except subprocess.TimeoutExpired:
                    rec = {"returncode": None, "timeout": True}
            peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            if sys.platform != "darwin":
                peak *= 1024
            rec.update(command=["OMP_NUM_THREADS=2"] + cmd,
                       seconds=round(time.monotonic() - start, 2),
                       cumulative_child_peak_rss_bytes=peak,
                       wall_seconds_limit=args.wall_seconds,
                       log=str((logs / f"{tag}.log").relative_to(ROOT)))
            execution.write_text(json.dumps(rec, indent=2) + "\n")
            records.append(rec)
            print(tag, json.dumps(rec), flush=True)
    (results / "executions.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
