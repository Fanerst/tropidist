"""Run the pipeline adapter on many exported instances of the planar study under a thread budget.

  make <out file> [--root results/planar_dp/instances] [--time-limit 1800]
      one job per (instance, dp in {1, 0}; dp=0 only where no DP table fits in 2^36 B); threads from the instance's DP plan in results/planar_dp/widths_*.json:
      tables up to 2^28 B get 2 threads, up to 2^33 B 16, larger 32; table_gb large enough for tables up to 2^36 B
  run <job file> [--budget 200]
      runs the jobs, largest first, with at most `budget` threads in use; skips jobs whose record exists

Job line: threads time_limit table_gb dp variant instance_dir out_json
Records: results/planar_dp/code_dp{1,0}/<instance>__t<threads>.json (the format of bench/common.save_result).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def plan_bits():
    out = {}
    for path in glob.glob(os.path.join(ROOT, "results", "planar_dp", "widths_*.json")):
        if path.endswith("widths_circuits.json"):
            continue
        for name, rec in json.load(open(path)).items():
            for basis, b in rec["bases"].items():
                out["%s_%s" % (name, basis)] = b["table_bits"]
    return out


def make(out, root, time_limit):
    bits = plan_bits()
    jobs = []
    for d in sorted(glob.glob(os.path.join(root, "*"))):
        name = os.path.basename(d)
        tb = bits.get(name)
        if tb is None:
            continue
        threads = 2 if tb <= 28 else (16 if tb <= 33 else 32)
        gb = max(4, min(96, (1 << max(0, tb - 30)) + 2))
        for dp in ((1, 0) if tb <= 36 else (0,)):         # no table fits: the front end is the search itself
            rec = os.path.join("results", "planar_dp", "code_dp%d" % dp, "%s__t%d.json" % (name, threads))
            jobs.append((tb, "%d %d %d %d full %s %s" % (threads, time_limit, gb, dp, os.path.relpath(d, ROOT), rec)))
    jobs.sort(key=lambda x: -x[0])
    with open(out, "w") as f:
        for _, line in jobs:
            f.write(line + "\n")
    print("%d jobs -> %s" % (len(jobs), out))


def run(jobfile, budget, python):
    jobs = []
    for line in open(jobfile):
        if line.strip():
            t, tl, gb, dp, variant, inst, rec = line.split()
            jobs.append((int(t), float(tl), int(gb), int(dp), variant, inst, rec))
    running = []
    log = open(os.path.join(ROOT, "logs", "planar_dp", "jobs_%s.log" % os.path.basename(jobfile)), "a")
    while jobs or running:
        running = [(p, t, j) for (p, t, j) in running if p.poll() is None]
        used = sum(t for _, t, _ in running)
        started = False
        for i, job in enumerate(jobs):
            t, tl, gb, dp, variant, inst, rec = job
            if os.path.exists(os.path.join(ROOT, rec)):
                jobs.pop(i)
                started = True
                break
            if used + t <= budget:
                os.makedirs(os.path.dirname(os.path.join(ROOT, rec)), exist_ok=True)
                env = dict(os.environ, OMP_NUM_THREADS=str(t))
                cmd = [python, "bench/adapters/ours_pipeline.py", "--instance", inst, "--variant", variant,
                       "--time-limit", str(tl), "--threads", str(t), "--out", rec,
                       "--config", "dp=%d,table_gb=%d" % (dp, gb)]
                p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL)
                log.write("%s start %s dp=%d t=%d\n" % (time.strftime("%H:%M:%S"), inst, dp, t))
                log.flush()
                running.append((p, t, job))
                jobs.pop(i)
                started = True
                break
        if not started:
            time.sleep(1.0)
    log.write("%s all done\n" % time.strftime("%H:%M:%S"))
    log.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["make", "run"])
    ap.add_argument("file")
    ap.add_argument("--root", default=os.path.join(ROOT, "results", "planar_dp", "instances"))
    ap.add_argument("--time-limit", type=int, default=1800)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--python", default=sys.executable)
    a = ap.parse_args()
    if a.command == "make":
        make(a.file, a.root, a.time_limit)
    else:
        run(a.file, a.budget, a.python)


if __name__ == "__main__":
    main()
