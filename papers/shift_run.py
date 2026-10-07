"""Bounded local run_parallel batch for the lead-chosen shift experiments.

No search implementation is changed. Each child uses OMP_NUM_THREADS=2,
k_coll=2, a per-threshold time limit, and a hard wall limit below ten minutes.
Results are saved by run_parallel even when only partial bounds are found.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true", help="skip finished matching JSON files")
    parser.add_argument("--base-only", action="store_true", help="run 72b/120b in both bases")
    parser.add_argument("--noise", choices=("full", "noidle", "both"), default="both")
    parser.add_argument("--threshold-seconds", type=float, default=30)
    parser.add_argument("--wall-seconds", type=float, default=570)
    parser.add_argument("--total-seconds", type=float, default=2400)
    args = parser.parse_args()
    if not 0 < args.wall_seconds < 600 or args.threshold_seconds <= 0:
        parser.error("wall limit must be below 600 seconds and threshold limit positive")
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    result_dir = root / "results/papers3/shift"
    log_dir = root / "logs/papers3/shift"
    result_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2",
               MKL_NUM_THREADS="2", PYTHONDONTWRITEBYTECODE="1")
    cases = [(key, basis) for key in ("72s", "72d", "72m") for basis in "ZX"]
    cases += [(key, "Z") for key in ("120s", "120d")]
    if args.base_only:
        cases = [(key, basis) for key in ("72b", "120b") for basis in "ZX"]
    report = {"command": " ".join(sys.argv), "readings": "chosen by the lead",
              "rounds": 6, "k_coll": 2, "kmax": 16,
              "seconds_per_threshold": args.threshold_seconds,
              "wall_seconds_per_process": args.wall_seconds, "attempts": []}
    start = time.monotonic()
    report_path = result_dir / ("base_runs.json" if args.base_only else "local_runs.json")

    def save():
        report["seconds"] = time.monotonic() - start
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    # Required full runs first; noidle comparisons afterwards.
    for noise in (("full", "noidle") if args.noise == "both" else (args.noise,)):
        for key, basis in cases:
            suffix = "" if noise == "full" else "_noidle"
            out = result_dir / f"{key}_{basis}{suffix}.json"
            cmd = [sys.executable, "papers/run_parallel.py", "shift", key, basis,
                   str(out.relative_to(root)), "6", "2", "16",
                   str(args.threshold_seconds), "1", noise]
            rec = {"key": key, "basis": basis, "noise": noise,
                   "command": "OMP_NUM_THREADS=2 " + " ".join(cmd),
                   "result": str(out.relative_to(root))}
            if args.resume and out.exists():
                previous = json.loads(out.read_text())
                if (previous.get("paper") == "shift" and previous.get("rounds") == 6
                        and previous.get("noise") == noise and "seconds" in previous
                        and previous.get("witness", {}).get("verified")):
                    rec["status"] = "existing_completed_result"
                    rec["result_seconds"] = previous["seconds"]
                    report["attempts"].append(rec)
                    save()
                    print(key, basis, noise, rec["status"], flush=True)
                    continue
            remaining = args.total_seconds - (time.monotonic() - start)
            if remaining <= 1:
                rec["status"] = "not_run_global_time_budget"
                report["attempts"].append(rec)
                save()
                continue
            log_path = log_dir / f"run_{key}_{basis}{suffix}.log"
            rec["log"] = str(log_path.relative_to(root))
            t0 = time.monotonic()
            with log_path.open("w") as log:
                log.write(rec["command"] + "\n")
                log.flush()
                child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
                try:
                    rec["exit_code"] = child.wait(timeout=min(args.wall_seconds, remaining))
                    rec["status"] = "finished" if rec["exit_code"] == 0 else "failed"
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                    rec["exit_code"] = child.returncode
                    rec["status"] = "wall_timeout_partial_result"
            rec["seconds"] = time.monotonic() - t0
            if out.exists():
                result = json.loads(out.read_text())
                rec["certified_lower_bound"] = result.get("certified_lower_bound")
                rec["verified_upper_bound"] = result.get("certified_upper_bound")
            report["attempts"].append(rec)
            save()
            print(key, basis, noise, rec["status"],
                  rec.get("certified_lower_bound"), rec.get("verified_upper_bound"),
                  round(rec["seconds"], 2), "s", flush=True)
    save()
    return int(any(r["status"] == "failed" for r in report["attempts"]))


if __name__ == "__main__":
    raise SystemExit(main())
