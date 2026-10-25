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
  gurobi     Gurobi (added when a licence became available): the first tier, the collapsed problems,
             then b32 on what it did not solve; 12 and 2 concurrent runs (the licence and a busier machine)
  wjh1       the instances of arXiv:2603.22532 (bench/instances_wjh, bench/export_wjh.py): ours, Gurobi and
             dist-m4ri CC with first-tier resources, on their problems (sector of a circuit = their filtered
             DEM; Z distance of a code); results/bench_wjh
  wjh8h      the protocol of arXiv:2603.22532 itself (1 core, 8 h, 8 GB per run, no give-up rule) for our
             pipeline on every instance of theirs it did not solve in the first tier; results/bench_wjh_8h.
             The circuit and code lists run as two concurrent harnesses on disjoint cores.
  dm4ri      dist-m4ri 0.14.7 (bench/external/dist-m4ri-0.14.7, commit bed621e) next to the 0.9.0 records,
             which are kept: first tier for 0.14.7 (CC, CC+RW, RW; sector and raw problems, the collapsed
             problems, and the raw circuits as Stim DEM input), first tier for 0.9.0 CC without its native
             timeout (cutoff=0: the October runs lost time to its predictive cutoff), both versions on the
             instances of arXiv:2603.22532, then 0.14.7 CC+RW at 32 threads / 90 GB / 3600 s on what its first
             tier left (main suite on cores 0-63 and the paper's instances on 64-95, in parallel)
  dm4mb1     dist-m4ri 0.14.7 with its model lower bound (bound=model: the bound of --model-lb, then the binary
             from that bound), first tier, CC and CC+RW: every circuit of the main suite on its main problem
             (sector; the raw problem when it has no sectors) and as Stim DEM input, and the circuits of
             arXiv:2603.22532 (25 October 2026)
  dm4mb2     its second tier: CC+RW and CC with the model bound, each at 32 threads / 90 GB / 3600 s on the
             circuits its own first tier left; the main suite (two runs at a time per mode) and the paper's
             instances (one per mode) all in parallel, on the physical cores of both sockets.
             DM4MB_MODES=cc or =bracket restricts both phases to one mode (default: both)
  sparseL    the integer-programming and SAT tools again on the code instances, now with the sparse logical
             basis full.L.std.mtx (bench/standard_logicals.py; the problem is the same, only the parity rows
             are lighter): first tier for HiGHS, CP-SAT, Gurobi, SAT, RC2, CASHWMaxSAT and enMaxCDCL on the
             codes of the main suite and for Gurobi on the codes of arXiv:2603.22532, then the second tier
             (32 threads for CP-SAT and Gurobi, 1 thread for the others) on what each left; earlier records kept
  wjh2       our pipeline at 32 threads / 90 GB / 3600 s on what it did not solve; results/bench_wjh_tierB.
             Gurobi and dist-m4ri (CC+RW) can be added with WJH2_METHODS. Gurobi was not run here (the paper
             ran it for 8 h with one thread on every instance); dist-m4ri 0.14.7 got this tier in phase dm4ri
  dp2        our pipeline with config dp=2 (the sparse Rank DP, results/sparse_dp), first tier: the main suite (sector
             and raw problems), then the instances of arXiv:2603.22532 (circuits: sector problem; codes as they are)
  dp2b       its second tier (32 threads / 90 GB / 3600 s) on what its first tier left: the main suite on cores 0-95
             (results/bench_tierB) and the instances of arXiv:2603.22532 on 96-191 (results/bench_wjh_tierB), in
             parallel

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
GUROBI = "milp:backend=gurobi"      # gurobipy, or gurobi_cl from $GUROBI_HOME/bin


# The final pass (Feng, 23 October 2026): dp=2 is our final configuration, the only column of ours in the tables.
# It reruns that configuration on every set with one code version, and runs every other solver on the instances
# added for the Rank DP evaluators (bench/instances.py DP_TRUTH).  dist-m4ri runs as 0.14.7 only (the 0.9.0 build
# has its own section); "ours, plain" and the other configurations of ours are not run.
FINAL = "ours_pipeline:dp=2"
DP_FRIENDLY = ["color_cc_d19", "color_cc_d23", "color_cc_d27", "color_cc_d31", "concat_steane_L3", "concat_steane_L4",
               "hypercube_L4", "dtc_w5_259_2_4", "dtc_w7_269_4_5", "dtc_w9_365_10_4", "dtc_w11_537_14_12",
               "superdense_d7", "superdense_d9", "superdense_d11"]
ABLATION_FINAL = [FINAL + "," + s for s in ("symmetry=0", "cover=0", "collapse=0", "lift=0", "window=0",
                                            "collapse=0,lift=0,window=0",
                                            "symmetry=0,cover=0,collapse=0,lift=0,window=0")] \
    + ["ours_pipeline:dp=1", "ours_pipeline"]          # without the sparse DP; without either DP


def folder(spec):
    return run_matrix.parse_methods(spec, HERE / "adapters", set())[0]["folder"]


DM4 = "distm4ri:build=0.14.7"                  # dist-m4ri 0.14.7; the plain "distm4ri:..." specs are 0.9.0
DM4_CC, DM4_BR, DM4_RW = DM4 + ",mode=cc", DM4 + ",mode=bracket", DM4 + ",mode=rw"
DM4_CC_MB, DM4_BR_MB = DM4_CC + ",bound=model", DM4_BR + ",bound=model"     # with the model lower bound (--model-lb)
MB_MODES = os.environ.get("DM4MB_MODES", "cc,bracket").split(",")
DM0_CC_FULL = "distm4ri:mode=cc,cutoff=0"       # 0.9.0 with the whole time budget
WJH_DIR = HERE / "instances_wjh"
WJH1 = ["ours_pipeline", GUROBI, "distm4ri:mode=cc"]
WJH2 = ["ours_pipeline", GUROBI, "distm4ri:mode=bracket"]
WJH2_DEFAULT = "ours_pipeline"


def instances(directory=None):
    out = []
    for p in sorted(Path(directory or HERE / "instances").glob("*/meta.json")):
        m = json.loads(p.read_text())
        if m.get("family") != "fixture":
            out.append(m)
    return out


def unsolved(spec, tier_a, raw=False, directory=None, first=None, tracks=None, names=None):
    """{variant: [instance names]} that the method did not solve exactly in the first tier.
    raw: the method takes the raw problem of a circuit (variant full) and no code instances.
    first: the first-tier method whose records count (default: the same spec).  names: only these instances."""
    res = {"sector": [], "full": []}
    for m in instances(directory):
        if tracks and m["track"] not in tracks:
            continue
        if names is not None and m["name"] not in names:
            continue
        variant = "full" if m["track"] == "code" or raw else "sector"
        if variant not in m["variants"] or (raw and m["track"] == "code"):
            continue
        rec = tier_a / folder(first or spec) / ("%s__%s__t1.json" % (m["name"], variant))
        status = json.loads(rec.read_text()).get("status") if rec.exists() else "missing"
        if status not in ("exact", "unavailable"):
            res[variant].append(m["name"])
    return res


def harness(args, log, dry, cpus=None):
    cmd = [sys.executable, str(HERE / "run_matrix.py")] + args + ["--cpus", cpus or CPUS] + (["--dry-run"] if dry else [])
    print(time.strftime("%H:%M:%S"), " ".join(a if len(a) < 90 else a[:87] + "..." for a in cmd[2:]), flush=True)
    with open(log, "a") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(ROOT))
    if rc:
        print(time.strftime("%H:%M:%S"), "harness exit code", rc, "see", log, flush=True)


def harness_parallel(calls, log, dry):
    """Several harness invocations at once, each with its own CPU list: [(args, cpus), ...]."""
    procs = []
    with open(log, "a") as f:
        for args, cpus in calls:
            cmd = [sys.executable, str(HERE / "run_matrix.py")] + args + ["--cpus", cpus] + (["--dry-run"] if dry else [])
            print(time.strftime("%H:%M:%S"), " ".join(x if len(x) < 90 else x[:87] + "..." for x in cmd[2:]), flush=True)
            procs.append(subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(ROOT)))
        for proc in procs:
            if proc.wait():
                print(time.strftime("%H:%M:%S"), "harness exit code", proc.returncode, "see", log, flush=True)


def frontier(methods, tier_a, out, threads, mem, jobs, name, logs, dry, raw=False, directory=None, firsts=None,
             cpus=None, tracks=None, only=None, variants=None):
    lists = out / "lists"
    lists.mkdir(parents=True, exist_ok=True)
    extra = ["--instance-dir", str(directory)] if directory else []
    for i, spec in enumerate(methods):
        for variant, names in unsolved(spec, tier_a, raw, directory, firsts[i] if firsts else None, tracks,
                                       only).items():
            if not names or (variants and variant not in variants):
                continue
            path = lists / ("%s__%s__%s.txt" % (name, folder(spec)[:60], variant))
            path.write_text("\n".join(names) + "\n")
            print(time.strftime("%H:%M:%S"), name, spec[:60], variant, len(names), "instances", flush=True)
            harness(["--methods", spec, "--instances", "@" + str(path), "--variants", variant,
                     "--threads", str(threads), "--time-limit", "3600", "--mem-gb", str(mem),
                     "--total-mem-gb", "270", "--jobs", str(jobs), "--out", str(out), "--give-up", "1"] + REDO + extra,
                    logs / (name + ".log"), dry, cpus)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phases", nargs="+", choices=["fix", "collapsed", "b32", "b1", "ablation", "stimsat", "b1s", "gurobi", "wjh1", "wjh2",
                                         "wjh8h", "dm4ri", "dm4mb1", "dm4mb2", "sparseL", "sparseL1", "sparseL2", "dp2", "dp2b",
                                         "final1", "final8h", "final2", "final2b"])
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
        elif phase == "gurobi":
            first12 = [x if x != "18" else "12" for x in first]
            harness(["--methods", GUROBI, "--instances", "all", "--variants", "sector,full"] + REDO + first12,
                    logs / "tierA_gurobi.log", a.dry_run)
            harness(["--methods", GUROBI, "--instances", "all", "--variants", "collapsed"] + REDO + first12,
                    logs / "tierA_gurobi_collapsed.log", a.dry_run)
            frontier([GUROBI], tier_a, out, 32, 90, 2, "b32_gurobi", logs, a.dry_run)
        elif phase == "wjh1":
            wjh_a = ROOT / "results" / "bench_wjh"
            wjh_a.mkdir(parents=True, exist_ok=True)
            for track, variant in (("circuit", "sector"), ("code", "full")):
                names = [m["name"] for m in instances(WJH_DIR) if m["track"] == track]
                (wjh_a / ("instances_%s.txt" % track)).write_text("\n".join(names) + "\n")
                harness(["--methods", ",".join(WJH1), "--instances", "@" + str(wjh_a / ("instances_%s.txt" % track)),
                         "--variants", variant, "--instance-dir", str(WJH_DIR)] + REDO
                        + [x if x != str(tier_a) else str(wjh_a) for x in first], logs / "wjh1.log", a.dry_run)
        elif phase == "dm4ri":
            wjh_a = ROOT / "results" / "bench_wjh"
            circuits = [m["name"] for m in instances() if m["track"] == "circuit"]
            (logs / "dm4ri_circuits.txt").write_text("\n".join(circuits) + "\n")
            wl = {t: wjh_a / ("instances_%s.txt" % t) for t in ("circuit", "code")}
            base = ["--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--give-up", "2"] + REDO
            harness_parallel([
                (["--methods", ",".join([DM4_CC, DM4_BR, DM4_RW]), "--instances", "all", "--variants", "sector,full",
                  "--heuristic-methods", DM4_RW, "--jobs", "8", "--total-mem-gb", "128", "--out", str(tier_a)] + base, "0-7"),
                (["--methods", ",".join([DM4_CC, DM4_BR]), "--instances", "all", "--variants", "collapsed",
                  "--jobs", "2", "--total-mem-gb", "32", "--out", str(tier_a)] + base, "8-9"),
                (["--methods", ",".join([DM4_CC + ",input=dem", DM4_BR + ",input=dem"]), "--instances",
                  "@" + str(logs / "dm4ri_circuits.txt"), "--variants", "full",
                  "--jobs", "2", "--total-mem-gb", "32", "--out", str(tier_a)] + base, "10-11"),
                (["--methods", DM0_CC_FULL, "--instances", "all", "--variants", "sector,full,collapsed",
                  "--jobs", "6", "--total-mem-gb", "96", "--out", str(tier_a)] + base, "12-17"),
                (["--methods", ",".join([DM4_CC, DM0_CC_FULL]), "--instances", "@" + str(wl["circuit"]),
                  "--variants", "sector", "--instance-dir", str(WJH_DIR), "--jobs", "2", "--total-mem-gb", "32",
                  "--out", str(wjh_a)] + base, "18-19"),
                (["--methods", ",".join([DM4_CC, DM0_CC_FULL]), "--instances", "@" + str(wl["code"]),
                  "--variants", "full", "--instance-dir", str(WJH_DIR), "--jobs", "4", "--total-mem-gb", "64",
                  "--out", str(wjh_a)] + base, "20-23"),
            ], logs / "dm4ri_tier1.log", a.dry_run)
            import threading
            jobs_ = [threading.Thread(target=frontier, args=([DM4_BR], tier_a, out, 32, 90, 2, "dm4ri_b32", logs, a.dry_run),
                                      kwargs=dict(cpus="0-63")),
                     threading.Thread(target=frontier, args=([DM4_BR], wjh_a, ROOT / "results" / "bench_wjh_tierB", 32, 90, 1,
                                                             "dm4ri_wjh2", logs, a.dry_run),
                                      kwargs=dict(directory=WJH_DIR, firsts=[DM4_CC], cpus="64-95"))]
            for t in jobs_:
                t.start()
            for t in jobs_:
                t.join()
        elif phase == "dm4mb1":
            wjh_a = ROOT / "results" / "bench_wjh"
            ms = [m for m in instances() if m["track"] == "circuit"]
            lists = {"sector": [m["name"] for m in ms if "sector" in m["variants"]],
                     "raw": [m["name"] for m in ms if "sector" not in m["variants"]],
                     "dem": [m["name"] for m in ms]}
            for key, names in lists.items():
                (logs / ("dm4mb_%s.txt" % key)).write_text("\n".join(names) + "\n")
            base = ["--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--give-up", "2"] + REDO
            mb = [spec for key, spec in (("cc", DM4_CC_MB), ("bracket", DM4_BR_MB)) if key in MB_MODES]
            mb_dem = [spec.replace(",bound=model", ",input=dem,bound=model") for spec in mb]
            harness_parallel([
                (["--methods", ",".join(mb), "--instances", "@" + str(logs / "dm4mb_sector.txt"),
                  "--variants", "sector", "--jobs", "5", "--total-mem-gb", "80", "--out", str(tier_a)] + base, "0-4"),
                (["--methods", ",".join(mb), "--instances", "@" + str(logs / "dm4mb_raw.txt"),
                  "--variants", "full", "--jobs", "1", "--total-mem-gb", "16", "--out", str(tier_a)] + base, "5"),
                (["--methods", ",".join(mb_dem), "--instances", "@" + str(logs / "dm4mb_dem.txt"), "--variants", "full",
                  "--jobs", "4", "--total-mem-gb", "64", "--out", str(tier_a)] + base, "6-9"),
                (["--methods", ",".join(mb), "--instances", "@" + str(wjh_a / "instances_circuit.txt"),
                  "--variants", "sector", "--instance-dir", str(WJH_DIR), "--jobs", "2", "--total-mem-gb", "32",
                  "--out", str(wjh_a)] + base, "10-11"),
            ], logs / "dm4mb_tier1.log", a.dry_run)
        elif phase == "dm4mb2":
            # both modes (with the bound, CC alone solved two circuits in the first tier), on the physical cores
            # of both sockets: CC+RW on 0-95, CC on 96-191
            import threading
            wjh_a, wjh_b = ROOT / "results" / "bench_wjh", ROOT / "results" / "bench_wjh_tierB"
            jobs_ = [threading.Thread(target=frontier, args=([spec], tier_a, out, 32, 90, 2, "dm4mb_b32_" + key, logs,
                                                             a.dry_run), kwargs=dict(cpus=cpus, tracks=("circuit",)))
                     for spec, key, cpus in ((DM4_BR_MB, "br", "0-63"), (DM4_CC_MB, "cc", "96-159"))
                     if (key == "br" and "bracket" in MB_MODES) or (key == "cc" and "cc" in MB_MODES)] \
                + [threading.Thread(target=frontier, args=([spec], wjh_a, wjh_b, 32, 90, 1, "dm4mb_wjh2_" + key, logs,
                                                           a.dry_run),
                                    kwargs=dict(directory=WJH_DIR, cpus=cpus, tracks=("circuit",)))
                   for spec, key, cpus in ((DM4_BR_MB, "br", "64-95"), (DM4_CC_MB, "cc", "160-191"))
                   if (key == "br" and "bracket" in MB_MODES) or (key == "cc" and "cc" in MB_MODES)]
            for t in jobs_:
                t.start()
            for t in jobs_:
                t.join()
        elif phase in ("sparseL", "sparseL1", "sparseL2"):
            sl = lambda spec: spec + ",lbasis=std"
            b32_sl = [sl("milp:backend=cpsat"), sl(GUROBI)]
            b1_sl = [sl("milp:backend=scipy"), sl("sat:mode=incremental"), sl("sat:mode=maxsat"), sl(CASHW), sl(ENMAX)]
            codes = [m["name"] for m in instances() if m["track"] == "code"]
            (logs / "sparseL_codes.txt").write_text("\n".join(codes) + "\n")
            wjh_codes = ROOT / "results" / "bench_wjh" / "instances_code.txt"
            base = ["--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--give-up", "2", "--variants", "full"] + REDO
            if phase != "sparseL2":
                harness_parallel([
                    (["--methods", ",".join(b32_sl + b1_sl), "--instances", "@" + str(logs / "sparseL_codes.txt"),
                      "--jobs", "14", "--total-mem-gb", "224", "--out", str(tier_a)] + base, "0-13"),
                    (["--methods", sl(GUROBI), "--instances", "@" + str(wjh_codes), "--instance-dir", str(WJH_DIR),
                      "--jobs", "10", "--total-mem-gb", "160", "--out", str(ROOT / "results" / "bench_wjh")] + base, "14-23"),
                ], logs / "sparseL_tier1.log", a.dry_run)
            if phase == "sparseL1":
                continue
            import threading
            jobs_ = [threading.Thread(target=frontier, args=(b32_sl, tier_a, out, 32, 90, 2, "sparseL_b32", logs, a.dry_run),
                                      kwargs=dict(cpus="0-63", tracks=("code",))),
                     threading.Thread(target=frontier, args=(b1_sl, tier_a, out, 1, 16, 18, "sparseL_b1", logs, a.dry_run),
                                      kwargs=dict(cpus="64-95", tracks=("code",)))]
            for t in jobs_:
                t.start()
            for t in jobs_:
                t.join()
        elif phase == "wjh8h":
            out8 = ROOT / "results" / "bench_wjh_8h"
            (out8 / "lists").mkdir(parents=True, exist_ok=True)
            cpus = run_matrix.parse_cpus(CPUS)
            calls, used = [], 0
            for variant, names in unsolved("ours_pipeline", ROOT / "results" / "bench_wjh", directory=WJH_DIR).items():
                if not names:
                    continue
                path = out8 / "lists" / ("wjh8h__ours_pipeline__%s.txt" % variant)
                path.write_text("\n".join(names) + "\n")
                if used + len(names) > len(cpus):
                    raise SystemExit("not enough CPUs in BENCH_CPUS for one core per run")
                part = ",".join(map(str, cpus[used:used + len(names)]))
                used += len(names)
                print(time.strftime("%H:%M:%S"), "wjh8h", variant, len(names), "instances", flush=True)
                calls.append((["--methods", "ours_pipeline", "--instances", "@" + str(path), "--variants", variant,
                               "--instance-dir", str(WJH_DIR), "--threads", "1", "--time-limit", "28800", "--mem-gb", "8",
                               "--total-mem-gb", str(8 * len(names)), "--jobs", str(len(names)), "--out", str(out8)] + REDO,
                              part))
            harness_parallel(calls, logs / "wjh8h.log", a.dry_run)
        elif phase == "wjh2":
            # WJH2_METHODS (";"-separated subset of WJH2) and BENCH_JOBS let the pass share the socket with others
            chosen = os.environ.get("WJH2_METHODS", WJH2_DEFAULT)
            pick = [i for i, m in enumerate(WJH2) if m in chosen.split(";")]
            frontier([WJH2[i] for i in pick], ROOT / "results" / "bench_wjh", ROOT / "results" / "bench_wjh_tierB", 32, 90,
                     int(os.environ.get("BENCH_JOBS", "2")), "wjh2", logs, a.dry_run, directory=WJH_DIR,
                     firsts=[WJH1[i] for i in pick])
        elif phase == "ablation":
            names = [m["name"] for m in instances() if m["track"] == "circuit"]
            abl = ROOT / "results" / "bench_ablation"
            abl.mkdir(parents=True, exist_ok=True)
            (abl / "instances.txt").write_text("\n".join(names) + "\n")
            harness(["--methods", ",".join(ABLATION), "--instances", "@" + str(abl / "instances.txt"), "--variants", "sector",
                     "--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--total-mem-gb", "288", "--jobs", "18",
                     "--out", str(abl), "--give-up", "2"], logs / "ablation.log", a.dry_run)
        elif phase == "dp2":
            # the flags of the first tier of dp=1 (scripts/server/dp_pass.sh), on the physical cores of socket 1
            spec = "ours_pipeline:dp=2"
            base = ["--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--total-mem-gb", "288", "--jobs", "18",
                    "--give-up", "2"] + REDO
            harness(["--methods", spec, "--instances", "all", "--variants", "sector,full", "--out", str(tier_a)] + base,
                    logs / "dp2_tier1.log", a.dry_run, "96-191")
            wjh = ROOT / "results" / "bench_wjh"
            for track, variant in (("circuit", "sector"), ("code", "full")):
                harness(["--methods", spec, "--instances", "@" + str(wjh / ("instances_%s.txt" % track)), "--variants",
                         variant, "--instance-dir", str(WJH_DIR), "--out", str(wjh)] + base, logs / "dp2_wjh_tier1.log",
                        a.dry_run, "96-191")
        elif phase == "dp2b":
            import threading
            spec = "ours_pipeline:dp=2"
            jobs_ = [threading.Thread(target=frontier, args=([spec], tier_a, out, 32, 90, 3, "b32_dp2", logs, a.dry_run),
                                      kwargs={"cpus": "0-95"}),
                     threading.Thread(target=frontier, args=([spec], ROOT / "results" / "bench_wjh",
                                                             ROOT / "results" / "bench_wjh_tierB", 32, 90, 2, "wjh2_dp2",
                                                             logs, a.dry_run),
                                      kwargs={"directory": WJH_DIR, "cpus": "96-191"})]
            for j in jobs_:
                j.start()
            for j in jobs_:
                j.join()
        elif phase == "final1":
            # First tier.  Socket 0: the final configuration on the main suite, the other solvers on the added
            # instances (then their collapsed problems, DEM input, Stim's WCNF and the sparse logical basis).
            # Socket 1: the final configuration on arXiv:2603.22532, and its ablation (results/bench_ablation_final).
            import threading
            added = logs / "final_added.txt"
            added.write_text("\n".join(DP_FRIENDLY) + "\n")
            circuits = [n for n in DP_FRIENDLY if n.startswith("superdense")]
            (logs / "final_added_circuits.txt").write_text("\n".join(circuits) + "\n")
            # the sparse logical basis exists where bench/standard_logicals.py could write it (not for a code
            # whose problem merges equal columns: dtc_w7_269_4_5)
            codes = [n for n in DP_FRIENDLY if n not in circuits and (HERE / "instances" / n / "full.L.std.mtx").exists()]
            (logs / "final_added_codes.txt").write_text("\n".join(codes) + "\n")
            base = ["--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--give-up", "2"] + REDO
            heur = "bposd,isd,stim_search," + DM4_RW
            others = [DM4_CC, DM4_BR, DM4_RW, "milp:backend=scipy", "milp:backend=cpsat", "sat:mode=incremental",
                      "sat:mode=maxsat", CASHW, ENMAX] + QSERF + ["bposd", "isd", "stim_search"]
            certifying = [DM4_CC, DM4_BR, "milp:backend=scipy", "milp:backend=cpsat", "sat:mode=incremental",
                          "sat:mode=maxsat", CASHW, ENMAX, GUROBI]
            sl = lambda spec: spec + ",lbasis=std"
            sparse_l = [sl(x) for x in ("milp:backend=cpsat", GUROBI, "milp:backend=scipy", "sat:mode=incremental",
                                        "sat:mode=maxsat", CASHW, ENMAX)]
            wjh = ROOT / "results" / "bench_wjh"
            abl = ROOT / "results" / "bench_ablation_final"
            abl.mkdir(parents=True, exist_ok=True)
            (abl / "instances.txt").write_text("\n".join(m["name"] for m in instances() if m["track"] == "circuit") + "\n")

            def socket0():
                harness_parallel([
                    (["--methods", FINAL, "--instances", "all", "--variants", "sector,full", "--jobs", "18",
                      "--total-mem-gb", "288", "--out", str(tier_a)] + base, "0-17"),
                    (["--methods", ",".join(others), "--instances", "@" + str(added), "--variants", "sector,full",
                      "--heuristic-methods", heur, "--jobs", "18", "--total-mem-gb", "288", "--out", str(tier_a)] + base,
                     "18-35"),
                    (["--methods", GUROBI, "--instances", "@" + str(added), "--variants", "sector,full", "--jobs", "6",
                      "--total-mem-gb", "96", "--out", str(tier_a)] + base, "36-41"),
                ], logs / "final1_socket0.log", a.dry_run)
                harness_parallel([
                    (["--methods", ",".join(certifying), "--instances", "@" + str(logs / "final_added_circuits.txt"),
                      "--variants", "collapsed", "--jobs", "9", "--total-mem-gb", "144", "--out", str(tier_a)] + base,
                     "0-8"),
                    (["--methods", ",".join([DM4_CC + ",input=dem", DM4_BR + ",input=dem"] + STIMSAT), "--instances",
                      "@" + str(logs / "final_added_circuits.txt"), "--variants", "full", "--jobs", "5",
                      "--total-mem-gb", "80", "--out", str(tier_a)] + base, "9-13"),
                    (["--methods", ",".join(sparse_l), "--instances", "@" + str(logs / "final_added_codes.txt"),
                      "--variants", "full", "--jobs", "14", "--total-mem-gb", "224", "--out", str(tier_a)] + base,
                     "14-27"),
                ], logs / "final1_socket0b.log", a.dry_run)

            def socket1():
                for track, variant in (("circuit", "sector"), ("code", "full")):
                    harness(["--methods", FINAL, "--instances", "@" + str(wjh / ("instances_%s.txt" % track)),
                             "--variants", variant, "--instance-dir", str(WJH_DIR), "--jobs", "18", "--total-mem-gb",
                             "288", "--out", str(wjh)] + base, logs / "final1_wjh.log", a.dry_run, "142-159")

            def ablation():
                harness(["--methods", ",".join(ABLATION_FINAL), "--instances", "@" + str(abl / "instances.txt"),
                         "--variants", "sector", "--jobs", "18", "--total-mem-gb", "288", "--out", str(abl)] + base,
                        logs / "final1_ablation.log", a.dry_run, "160-177")
            jobs_ = [threading.Thread(target=f) for f in (socket0, socket1, ablation)]
            for j in jobs_:
                j.start()
            for j in jobs_:
                j.join()
        elif phase == "final8h":
            # the protocol of arXiv:2603.22532 (1 core, 8 h, 8 GB, every instance, no give-up rule) for the final
            # configuration on all 126 of its instances, 46 at a time on physical cores of socket 1
            out8 = ROOT / "results" / "bench_wjh_8h"
            wjh = ROOT / "results" / "bench_wjh"
            calls = []
            for (track, variant), cpus in ((("circuit", "sector"), "96-107"), (("code", "full"), "108-141")):
                jobs = len(run_matrix.parse_cpus(cpus))
                calls.append((["--methods", FINAL, "--instances", "@" + str(wjh / ("instances_%s.txt" % track)),
                               "--variants", variant, "--instance-dir", str(WJH_DIR), "--threads", "1", "--time-limit",
                               "28800", "--mem-gb", "8", "--total-mem-gb", str(8 * jobs), "--jobs", str(jobs),
                               "--out", str(out8)] + REDO, cpus))
            harness_parallel(calls, logs / "final8h.log", a.dry_run)
        elif phase == "final2":
            # Second tier on socket 0, one pass after the other: the final configuration on the main suite, the
            # other solvers on the added instances, then the final configuration on arXiv:2603.22532.
            frontier([FINAL], tier_a, out, 32, 90, 3, "final2_ours", logs, a.dry_run, cpus="0-95")
            frontier([DM4_BR, "milp:backend=cpsat"] + QSERF + [GUROBI], tier_a, out, 32, 90, 3, "final2_b32", logs,
                     a.dry_run, cpus="0-95", only=set(DP_FRIENDLY))
            frontier(B1, tier_a, out, 1, 16, 18, "final2_b1", logs, a.dry_run, cpus="0-17", only=set(DP_FRIENDLY))
            frontier(STIMSAT, tier_a, out, 1, 16, 3, "final2_b1s", logs, a.dry_run, raw=True, cpus="18-20",
                     only=set(DP_FRIENDLY))
            sl = lambda spec: spec + ",lbasis=std"
            frontier([sl("milp:backend=cpsat"), sl(GUROBI)], tier_a, out, 32, 90, 2, "final2_sparseL_b32", logs,
                     a.dry_run, cpus="32-95", tracks=("code",), only=set(DP_FRIENDLY))
            frontier([sl(x) for x in ("milp:backend=scipy", "sat:mode=incremental", "sat:mode=maxsat", CASHW, ENMAX)],
                     tier_a, out, 1, 16, 14, "final2_sparseL_b1", logs, a.dry_run, cpus="0-13", tracks=("code",),
                     only=set(DP_FRIENDLY))
            frontier([FINAL], ROOT / "results" / "bench_wjh", ROOT / "results" / "bench_wjh_tierB", 32, 90, 3,
                     "final2_wjh", logs, a.dry_run, directory=WJH_DIR, cpus="0-95")
        elif phase == "final2b":
            # The rest of final2, in parallel (final2 ran its passes one after another: 24 October 2026, after the
            # final configuration's second tier on the main suite, the other solvers' 32-thread pass, and the
            # 1-thread pass of SAT; RC2's sector part was still running).  Every (method, variant) gets its own
            # cores; mitten_200 reruns alone (the give-up order put mitten_300, fewer columns, first).
            import threading
            only = set(DP_FRIENDLY)
            only_std = {n for n in only if (HERE / "instances" / n / "full.L.std.mtx").exists()}
            sl = lambda spec: spec + ",lbasis=std"
            singles = [(["sat:mode=maxsat"], ("full",), "18-21"), ([CASHW], ("sector",), "22"), ([CASHW], ("full",), "23-26"),
                       ([ENMAX], ("sector",), "27"), ([ENMAX], ("full",), "28-31"),
                       (["milp:backend=scipy"], ("sector",), "32"), (["milp:backend=scipy"], ("full",), "33-36")]
            work = [lambda m=m, v=v, c=c: frontier(m, tier_a, out, 1, 16, len(run_matrix.parse_cpus(c)), "final2_b1", logs,
                                                   a.dry_run, cpus=c, only=only, variants=v) for m, v, c in singles]
            work += [lambda m=m, c=c: frontier([m], tier_a, out, 1, 16, 1, "final2_b1s", logs, a.dry_run, raw=True, cpus=c,
                                               only=only) for m, c in zip(STIMSAT, ("37", "38", "39"))]
            work += [lambda m=m, c=c: frontier([sl(m)], tier_a, out, 1, 16, 4, "final2_sparseL_b1", logs, a.dry_run, cpus=c,
                                               tracks=("code",), only=only_std)
                     for m, c in zip(("milp:backend=scipy", "sat:mode=incremental", "sat:mode=maxsat", CASHW, ENMAX),
                                     ("40-43", "44-47", "48-51", "52-55", "56-59"))]

            def cores_60_91():
                harness(["--methods", FINAL, "--instances", "mitten_200", "--variants", "sector", "--threads", "32",
                         "--time-limit", "3600", "--mem-gb", "90", "--total-mem-gb", "90", "--jobs", "1", "--out", str(out),
                         "--give-up", "1", "--redo", "status=skipped"], logs / "final2_mitten200.log", a.dry_run, "60-91")
                frontier([sl("milp:backend=cpsat"), sl(GUROBI)], tier_a, out, 32, 90, 1, "final2_sparseL_b32", logs,
                         a.dry_run, cpus="60-91", tracks=("code",), only=only_std)
            work += [cores_60_91,
                     lambda: frontier([FINAL], ROOT / "results" / "bench_wjh", ROOT / "results" / "bench_wjh_tierB", 32, 90,
                                      3, "final2_wjh", logs, a.dry_run, directory=WJH_DIR, cpus="96-191")]
            jobs_ = [threading.Thread(target=f) for f in work]
            for j in jobs_:
                j.start()
            for j in jobs_:
                j.join()
    print(time.strftime("%H:%M:%S"), "all phases done", flush=True)


if __name__ == "__main__":
    main()
