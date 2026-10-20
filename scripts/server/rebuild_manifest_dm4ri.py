"""Re-add to results/bench/manifest.json and results/bench_wjh/manifest.json the invocations of `tier_b.py dm4ri`
(18 October 2026) that the harnesses running at the same time overwrote.  Arguments as in tier_b.py's phase
dm4ri; times from the run records each harness wrote.  Run on the server from the project root."""
import fcntl, json, sys
from pathlib import Path
sys.path.insert(0, "bench")
import run_matrix, tier_b
from tier_b import DM4_CC, DM4_BR, DM4_RW, DM0_CC_FULL, WJH_DIR, ROOT

tier_a, wjh_a, logs = ROOT / "results" / "bench", ROOT / "results" / "bench_wjh", ROOT / "logs" / "bench"
wl = {t: wjh_a / ("instances_%s.txt" % t) for t in ("circuit", "code")}
base = ["--threads", "1", "--time-limit", "600", "--mem-gb", "16", "--give-up", "2"]
calls = [
    (["--methods", ",".join([DM4_CC, DM4_BR, DM4_RW]), "--instances", "all", "--variants", "sector,full",
      "--heuristic-methods", DM4_RW, "--jobs", "8", "--total-mem-gb", "128", "--out", str(tier_a)] + base, "0-7", tier_a),
    (["--methods", ",".join([DM4_CC, DM4_BR]), "--instances", "all", "--variants", "collapsed",
      "--jobs", "2", "--total-mem-gb", "32", "--out", str(tier_a)] + base, "8-9", tier_a),
    (["--methods", DM0_CC_FULL, "--instances", "all", "--variants", "sector,full,collapsed",
      "--jobs", "6", "--total-mem-gb", "96", "--out", str(tier_a)] + base, "12-17", tier_a),
    (["--methods", ",".join([DM4_CC, DM0_CC_FULL]), "--instances", "@" + str(wl["code"]),
      "--variants", "full", "--instance-dir", str(WJH_DIR), "--jobs", "4", "--total-mem-gb", "64",
      "--out", str(wjh_a)] + base, "20-23", wjh_a),
]
for args, cpus, out in calls:
    mpath = out / "manifest.json"
    with open(str(mpath) + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        man = json.loads(mpath.read_text())
        inv = man["invocations"]
        tmpl = next(e for e in inv if e["started_at"].startswith("2026-10-18T08:50"))     # the entry that survived
        cl = tmpl["command_line"][:2] + args + ["--cpus", cpus]
        if any(e["command_line"] == cl for e in inv):
            print(cpus, "already present"); continue
        if "--redo" in tmpl["command_line"]:
            print("template used --redo; check"); sys.exit(1)
        cset = set(run_matrix.parse_cpus(cpus))
        specs = set(args[args.index("--methods") + 1].split(",distm4ri:"))
        recs = []
        for p in out.glob("distm4ri*/*__t1.json"):
            r = json.loads(p.read_text())
            h = r.get("harness", {})
            if (h.get("started_at", "") >= "2026-10-18T08:50" and h.get("started_at", "") < "2026-10-18T12:00"
                    and set(h.get("cpus") or []) <= cset):
                recs.append(h)
        if not recs:
            print(cpus, "no records"); continue
        e = dict(tmpl)
        e.update(command_line=cl, pid="not recorded (dm4ri %s)" % cpus,
                 started_at=min(h["started_at"] for h in recs), ended_at=max(h["ended_at"] for h in recs),
                 interrupted=None, cpus=run_matrix.parse_cpus(cpus), jobs=int(args[args.index("--jobs") + 1]),
                 total_mem_gb=float(args[args.index("--total-mem-gb") + 1]), planned=len(recs),
                 ran=sum(1 for h in recs if h.get("wall_seconds")), resumed=0,
                 skipped=sum(1 for h in recs if not h.get("wall_seconds")),
                 reconstructed=("entry rebuilt on 2026-10-19: the harnesses of `tier_b.py dm4ri` ran at the same time and "
                                "overwrote each other's manifest entries (fixed by run_matrix.record_invocation); "
                                "arguments as in tier_b.py, started_at/ended_at the first start and last end among "
                                "the %d run records with these cores, other fields as in the entry that survived" % len(recs)))
        inv.append(e)
        run_matrix.write_json(mpath, man)
        print(cpus, out.name, e["started_at"][:19], e["ended_at"][:19], "records", len(recs), "ran", e["ran"], "skipped", e["skipped"])
