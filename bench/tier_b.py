"""Later passes of the benchmark, chained behind the first tier (1 thread, 600 s, 16 GB).

  fix        the first tier on instances added after it started (Stim surface and color codes), then
             first-tier runs that have to be repeated for reasons of the harness: Qubitserf (the
             harness that ran the first tier rejected an exact value without a codeword) and the
             random-window mode of dist-m4ri (a heuristic that was subject to the give-up rule)
  collapsed  every certifying method on the time-collapsed relaxation, first-tier resources
  b32        tools that use threads: 32 threads, 90 GB, 3600 s
  b1         single-thread tools: 1 thread, 16 GB, 3600 s
  stimsat    the MaxSAT recipe of the literature (Stim's own WCNF of the whole circuit, then a MaxSAT
             solver) on the raw problem of every circuit, first-tier resources
  b1s        the same recipe with 3600 s on the circuits it did not solve
  ablation   our pipeline with one component switched off at a time, first-tier resources, sector
             problems of the circuits (results/bench_ablation)

In b32 and b1 a method runs only on the instances it did not solve exactly in the first tier
(sector problem of a circuit, the code itself on the code track), in order of size within a
family, and stops in a family after the first instance it does not solve.

Usage: python bench/tier_b.py phase [phase ...] [--dry-run] [--tier-a DIR] [--out DIR]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import run_matrix

EXT = ROOT / "bench" / "external"
CASHW = "sat:mode=maxsat,binary=%s" % (EXT / "CASHWMaxSAT-CorePlus" / "bin" / "cashwmaxsatcoreplus")
ENMAX = "sat:mode=maxsat,binary=%s" % (EXT / "enMaxCDCL")
QSERF = ["qserf:method=cc", "qserf:method=bz", "qserf:method=mitm"]
HEUR = "bposd,isd,stim_search,distm4ri:mode=rw"
CPUS = os.environ.get("BENCH_CPUS", "0-95")       # default: the physical cores of socket 0
REDO = ["--redo", "status=error", "--redo", "status=skipped"] if os.environ.get("BENCH_REDO") else []

CERTIFYING = ["ours_pipeline", "ours", "distm4ri:mode=cc", "distm4ri:mode=bracket", "milp:backend=scipy",
              "milp:backend=cpsat", "sat:mode=incremental", "sat:mode=maxsat", CASHW, ENMAX]
B32 = ["ours_pipeline", "distm4ri:mode=bracket", "milp:backend=cpsat"] + QSERF
ABLATION = ["ours_pipeline:symmetry=0", "ours_pipeline:cover=0", "ours_pipeline:collapse=0", "ours_pipeline:lift=0",
            "ours_pipeline:window=0", "ours_pipeline:collapse=0,lift=0,window=0",
            "ours_pipeline:symmetry=0,cover=0,collapse=0,lift=0,window=0"]
STIMSAT = ["sat:mode=maxsat,encoding=stim", CASHW.replace("mode=maxsat,", "mode=maxsat,encoding=stim,"),
           ENMAX.replace("mode=maxsat,", "mode=maxsat,encoding=stim,")]
B1 = ["sat:mode=incremental", "sat:mode=maxsat", CASHW, ENMAX, "milp:backend=scipy"]


def folder(spec):
    return run_matrix.parse_methods(spec, HERE / "adapters", set())[0]["folder"]


def instances():
    out = []
    for p in sorted((HERE / "instances").glob("*/meta.json")):
        m = json.loads(p.read_text())
        if m.get("family") != "fixture":
            out.append(m)
    return out


def unsolved(spec, tier_a, raw=False):
    """{variant: [instance names]} that the method did not solve exactly in the first tier.
    raw: the method takes the raw problem of a circuit (variant full) and no code instances."""
    res = {"sector": [], "full": []}
    for m in instances():
        variant = "full" if m["track"] == "code" or raw else "sector"
        if variant not in m["variants"] or (raw and m["track"] == "code"):
            continue
        rec = tier_a / folder(spec) / ("%s__%s__t1.json" % (m["name"], variant))
        status = json.loads(rec.read_text()).get("status") if rec.exists() else "missing"
        if status not in ("exact", "unavailable"):
            res[variant].append(m["name"])
    return res


def harness(args, log, dry):
    cmd = [sys.executable, str(HERE / "run_matrix.py")] + args + ["--cpus", CPUS] + (["--dry-run"] if dry else [])
    print(time.strftime("%H:%M:%S"), " ".join(a if len(a) < 90 else a[:87] + "..." for a in cmd[2:]), flush=True)
    with open(log, "a") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(ROOT))
    if rc:
        print(time.strftime("%H:%M:%S"), "harness exit code", rc, "see", log, flush=True)


def frontier(methods, tier_a, out, threads, mem, jobs, name, logs, dry, raw=False):
    lists = out / "lists"
    lists.mkdir(parents=True, exist_ok=True)
    for spec in methods:
        for variant, names in unsolved(spec, tier_a, raw).items():
            if not names:
                continue
            path = lists / ("%s__%s__%s.txt" % (name, folder(spec)[:60], variant))
            path.write_text("\n".join(names) + "\n")
            print(time.strftime("%H:%M:%S"), name, spec[:60], variant, len(names), "instances", flush=True)
            harness(["--methods", spec, "--instances", "@" + str(path), "--variants", variant,
                     "--threads", str(threads), "--time-limit", "3600", "--mem-gb", str(mem),
                     "--total-mem-gb", "270", "--jobs", str(jobs), "--out", str(out), "--give-up", "1"] + REDO,
                    logs / (name + ".log"), dry)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phases", nargs="+", choices=["fix", "collapsed", "b32", "b1", "ablation", "stimsat", "b1s"])
    ap.add_argument("--tier-a", default=str(ROOT / "results" / "bench"))
    ap.add_argument("--out", default=str(ROOT / "results" / "bench_tierB"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tier_a, out, logs = Path(a.tier_a), Path(a.out), ROOT / "logs" / "bench"
    logs.mkdir(parents=True, exist_ok=True)
    first = ["--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--total-mem-gb", "288", "--jobs", "18",
             "--out", str(tier_a), "--give-up", "2", "--heuristic-methods", HEUR]
    for phase in a.phases:
        print(time.strftime("%H:%M:%S"), "phase", phase, flush=True)
        if phase == "fix":
            # instances added after the first tier started: the same run, existing records are kept
            tier_a_methods = CERTIFYING + QSERF + ["bposd", "isd", "stim_search", "distm4ri:mode=rw"]
            harness(["--methods", ",".join(tier_a_methods), "--instances", "all", "--variants", "sector,full"] + first,
                    logs / "tierA_added.log", a.dry_run)
            harness(["--methods", ",".join(QSERF + ["distm4ri:mode=rw"]), "--instances", "all", "--variants", "sector,full",
                     "--redo", "status=error", "--redo", "status=skipped"] + first, logs / "tierA_fix.log", a.dry_run)
        elif phase == "collapsed":
            harness(["--methods", ",".join(CERTIFYING), "--instances", "all", "--variants", "collapsed"] + first,
                    logs / "tierA_collapsed.log", a.dry_run)
        elif phase == "b32":
            frontier(B32, tier_a, out, 32, 90, 3, "b32", logs, a.dry_run)
        elif phase == "b1":
            frontier(B1, tier_a, out, 1, 16, 18, "b1", logs, a.dry_run)
        elif phase == "stimsat":
            names = [m["name"] for m in instances() if m["track"] == "circuit"]
            (logs / "stimsat_instances.txt").write_text("\n".join(names) + "\n")
            harness(["--methods", ",".join(STIMSAT), "--instances", "@" + str(logs / "stimsat_instances.txt"),
                     "--variants", "full"] + REDO + first, logs / "tierA_stimsat.log", a.dry_run)
        elif phase == "b1s":
            frontier(STIMSAT, tier_a, out, 1, 16, 18, "b1s", logs, a.dry_run, raw=True)
        elif phase == "ablation":
            names = [m["name"] for m in instances() if m["track"] == "circuit"]
            abl = ROOT / "results" / "bench_ablation"
            abl.mkdir(parents=True, exist_ok=True)
            (abl / "instances.txt").write_text("\n".join(names) + "\n")
            harness(["--methods", ",".join(ABLATION), "--instances", "@" + str(abl / "instances.txt"), "--variants", "sector",
                     "--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--total-mem-gb", "288", "--jobs", "18",
                     "--out", str(abl), "--give-up", "2"], logs / "ablation.log", a.dry_run)
    print(time.strftime("%H:%M:%S"), "all phases done", flush=True)


if __name__ == "__main__":
    main()
