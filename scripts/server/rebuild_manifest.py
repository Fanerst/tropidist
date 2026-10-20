"""Re-add to results/bench_tierB/manifest.json the invocations of the sparse-basis second tier that concurrent
harnesses (before run_matrix.record_invocation existed) overwrote.  Run on the server from the project root."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, "bench")
import run_matrix

OUT = Path("results/bench_tierB")
man = json.loads((OUT / "manifest.json").read_text())
tmpl = next(e for e in man["invocations"] if "sparseL2_b32__cpsat__full.txt" in " ".join(e["command_line"]))
split = Path("logs/bench/sparseL2_split.log").read_text()
cpus = {"scipy": "160-165", "incremental": "166-171", "rc2": "172-177", "cashw": "178-183", "enmax": "184-189"}
# drop entries a previous run of this script added (they shared one key), under the manifest's lock
import fcntl
with open(str(OUT / "manifest.json") + ".lock", "a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    cur = json.loads((OUT / "manifest.json").read_text())
    cur["invocations"] = [e for e in cur["invocations"] if "reconstructed" not in e]
    run_matrix.write_json(OUT / "manifest.json", cur)
have = {" ".join(e["command_line"]) for e in cur["invocations"]}
for key, cp in cpus.items():
    lst = "results/bench_tierB/lists/sparseL2_b1__%s__full.txt" % key
    spec = Path("results/bench_tierB/lists/sparseL2_b1__%s__spec.txt" % key).read_text().strip()
    starts = re.findall(r"^(\d\d:\d\d:\d\d) start %s cpus" % key, split, re.M)
    dones = re.findall(r"^(\d\d:\d\d:\d\d) done %s " % key, split, re.M)
    start, end = starts[-1], dones[-1]            # incremental: the relaunch (the first attempt never ran)
    utc = lambda t: "2026-10-18T%02d:%s.000000+00:00" % (int(t[:2]) - 8 + 24, t[3:]) if int(t[:2]) < 8 else \
        "2026-10-19T%02d:%s.000000+00:00" % (int(t[:2]) - 8, t[3:])
    log = Path("logs/bench/sparseL2_%s.log" % key).read_text()
    cl = tmpl["command_line"][:2] + ["--methods", spec, "--instances", "@" + lst, "--variants", "full", "--threads", "1",
                                     "--time-limit", "3600", "--mem-gb", "16", "--total-mem-gb", "270", "--jobs", "6",
                                     "--out", "results/bench_tierB", "--give-up", "1", "--cpus", cp]
    if " ".join(cl) in have:
        print(key, "already present"); continue
    e = dict(tmpl)
    e.update(command_line=cl, pid="not recorded (%s)" % key, started_at=utc(start), ended_at=utc(end), interrupted=None,
             cpus=run_matrix.parse_cpus(cp), jobs=6, threads=1, mem_gb=16.0, total_mem_gb=270.0, time_limit=3600.0,
             give_up=1, planned=len(Path(lst).read_text().split()),
             ran=len(re.findall(r"^done ", log, re.M)), resumed=0, skipped=len(re.findall(r"^skipped ", log, re.M)),
             reconstructed=("entry rebuilt on 2026-10-19 from logs/bench/sparseL2_split.log and logs/bench/sparseL2_%s.log: "
                            "harnesses sharing this directory had overwritten each other's manifest entries "
                            "(fixed by run_matrix.record_invocation); host, versions and settings as in the CP-SAT "
                            "invocation started at the same time" % key))
    run_matrix.record_invocation(OUT / "manifest.json", e)
    print(key, e["started_at"], e["ended_at"], "ran", e["ran"], "skipped", e["skipped"])
