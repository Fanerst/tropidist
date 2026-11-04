"""Fill the tables of docs/BENCHMARK.md from the result directories.

Each block `<!-- TABLE:<name>:BEGIN -->` ... `<!-- TABLE:<name>:END -->` of that file is replaced
by the table of that name; the text around the blocks is written by hand.

Usage: python bench/make_benchmark_md.py [docs/BENCHMARK.md]
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import summary_table as T

A, B = ROOT / "results" / "bench", ROOT / "results" / "bench_tierB"
ABL = ROOT / "results" / "bench_ablation_final"       # one component off at a time, relative to the final configuration
EXACT = [name for _, name in T.SHORT if name not in T.HEURISTIC]
OLD_DM4RI = lambda name: name.startswith("dist-m4ri 0.9.0")      # superseded build: own section only
# The tables carry one column of ours, the final configuration dp=2 ("ours"; Feng, 23 October 2026).  The other
# configurations of our pipeline are compared in the text of docs/BENCHMARK.md and in the ablation.
OTHER_CONFIGS = ("ours, search only", "ours + DP", "ours, plain")
HIDE = lambda name: OLD_DM4RI(name) or name in OTHER_CONFIGS
# with the model lower bound of --model-lb (bound=model, 25 October 2026) next to the runs without it
DM4RI_VERSIONS = ["dist-m4ri 0.9.0 CC", "dist-m4ri 0.9.0 CC, no cutoff", "dist-m4ri CC", "dist-m4ri CC+RW",
                  "dist-m4ri CC, model bound", "dist-m4ri CC+RW, model bound"]
DM4RI_VERSIONS_RAW = DM4RI_VERSIONS + ["dist-m4ri CC, DEM input", "dist-m4ri CC+RW, DEM input",
                                       "dist-m4ri CC, DEM input, model bound", "dist-m4ri CC+RW, DEM input, model bound"]
# tools whose code results depend on the logical basis: the main tables keep their runs on the instances' first
# basis; their runs on the sparse basis (full.L.std.mtx) are side by side in a section of their own, and the
# coverage counts credit a tool with either basis
BASIS_TOOLS = ["HiGHS", "CP-SAT", "Gurobi", "SAT", "RC2", "CASHWMaxSAT", "enMaxCDCL"]
SPARSE_L = lambda name: name.endswith(", sparse L")
BASIS_COLUMNS = [x for t in BASIS_TOOLS for x in (t, t + ", sparse L")]


STIM = ("surface", "stim_color")


def main_set(m):
    return m.get("family") not in STIM


def stim_set(m):
    return m.get("family") in STIM


def overall_rows(config="ours"):
    """One row per instance on its main problem (sector for CSS circuits, the code itself, the raw
    model for circuits without sectors): our best time and the best other exact method, per tier.  The superseded
    dist-m4ri 0.9.0 is left out (it solves no instance that 0.14.7 does not).  config: the configuration of ours
    counted (one configuration, not the better of two; the tables use "ours").
    Rows: (is_code, family, columns, name, n, distance, ours t1, ours t2, (t, method) t1, (t, method) t2)."""
    import json
    a, b32, b1 = T.load(A, 1), T.load(B, 32), T.load(B, 1)
    ours = (config,)
    mine = ("ours",) + OTHER_CONFIGS

    def ex(recs, method, inst, variant):
        r = recs.get((method, inst, variant))
        return r["seconds"] if r is not None and r.get("status") == "exact" else None

    rows = []
    for path in sorted((HERE / "instances").glob("*/meta.json")):
        m = json.loads(path.read_text())
        if m.get("family") == "fixture":
            continue
        variant = "full" if (m["track"] == "code" or "sector" not in m["variants"]) else "sector"
        name = m["name"]
        comp = sorted(c for c in {k[0] for recs in (a, b32, b1) for k in recs if k[1] == name and k[2] == variant}
                      - set(mine) - set(T.HEURISTIC) if not OLD_DM4RI(c))
        oa = min((t for t in (ex(a, o, name, variant) for o in ours) if t is not None), default=None)
        ob = ex(b32, config, name, variant)
        ca = min(((t, c) for c in comp for t in [ex(a, c, name, variant)] if t is not None), default=None)
        cb = min(((t, c + (", 32 threads" if recs is b32 else ", 1 thread")) for recs in (b32, b1) for c in comp
                  for t in [ex(recs, c, name, variant)] if t is not None), default=None)
        v = m["variants"][variant]
        d = v.get("distance")
        if v.get("distance_kind") != "exact":
            closed = [r["upper_bound"] for recs in (a, b32) for o in ours for r in [recs.get((o, name, variant))]
                      if r is not None and r.get("status") == "exact"]
            # an open instance shows the strongest certified lower bound: the metadata's or one of our runs
            lbs = [r["lower_bound"] for recs in (a, b32) for o in ours for r in [recs.get((o, name, variant))]
                   if r is not None and r.get("lower_bound")]
            d = ("%d†" % closed[0]) if closed else (">=%s" % max([d] + lbs) if d is not None else "?")
        rows.append((m["track"] != "circuit", m.get("family", ""), v["cols"], name, m.get("n", ""), d, oa, ob, ca, cb))
    rows.sort()
    return rows


def overall():
    """overall_rows() as a markdown table with a summary line."""
    rows = overall_rows()
    f = lambda t: "" if t is None else T.seconds(t)
    g = lambda x: "" if x is None else "%s (%s)" % (T.seconds(x[0]), x[1])
    lines = ["| instance | n | columns | distance | ours, tier 1 | ours, tier 2 | best other, tier 1 | best other, tier 2 |",
             "|---|---:|---:|---:|---:|---:|---|---|"]
    n = dict(all=0, o1=0, o=0, c1=0, c=0, only=0, lost=0)
    for _, fam, cols, name, nq, d, oa, ob, ca, cb in rows:
        lines.append("| %s | %s | %d | %s | %s | %s | %s | %s |" % (name, nq, cols, d, f(oa), f(ob), g(ca), g(cb)))
        o, c = oa is not None or ob is not None, ca is not None or cb is not None
        n["all"] += 1; n["o1"] += oa is not None; n["o"] += o; n["c1"] += ca is not None; n["c"] += c
        n["only"] += o and not c; n["lost"] += c and not o
    lines.append("")
    verb = lambda k: "is" if n[k] == 1 else "are"
    lines.append("Of %(all)d instances: ours solves %(o1)d in the first tier and %(o)d over both tiers; some other exact "
                 "method solves %(c1)d in the first tier and %(c)d over both. " % n
                 + "%d %s solved by ours only; %d %s solved by another method and not by ours."
                 % (n["only"], verb("only"), n["lost"], verb("lost")))
    return "\n".join(lines)


def tables():
    t = {}
    if A.is_dir() and B.is_dir():
        t["overall"] = overall()
    if A.is_dir():
        t["A-circuit-sector"] = T.table(A, "sector", "circuit", 1, select=main_set, exclude=HIDE)
        t["A-circuit-full"] = T.table(A, "full", "circuit", 1, select=main_set, exclude=HIDE)
        t["A-code"] = T.table(A, "full", "code", 1, exclude=lambda n: HIDE(n) or SPARSE_L(n))
        t["L-code"] = T.table(A, "full", "code", 1, methods=BASIS_COLUMNS)
        # our plain search stays in this table: it is ours on the same relaxed input as the other solvers
        t["A-collapsed"] = T.table(A, "collapsed", "circuit", 1, methods=[m for m in EXACT if m != "ours"],
                                   exclude=lambda n: OLD_DM4RI(n) or (n in OTHER_CONFIGS and n != "ours, plain"))
        t["A-stim-sector"] = T.table(A, "sector", "circuit", 1, select=stim_set, exclude=HIDE)
        t["A-stim-full"] = T.table(A, "full", "circuit", 1, select=stim_set, exclude=HIDE)
        # the two dist-m4ri builds side by side (first tier)
        t["DM-sector"] = T.table(A, "sector", "circuit", 1, methods=DM4RI_VERSIONS)
        t["DM-code"] = T.table(A, "full", "code", 1, methods=DM4RI_VERSIONS)
        t["DM-full"] = T.table(A, "full", "circuit", 1, methods=DM4RI_VERSIONS_RAW)
        t["DM-collapsed"] = T.table(A, "collapsed", "circuit", 1, methods=DM4RI_VERSIONS)
        bad = T.consistency(A, 1)
        t["A-check"] = "\n".join("- " + b for b in bad) if bad else "All first-tier records are mutually consistent and consistent with the ground truth."
    if B.is_dir():
        for threads, key in ((32, "B32"), (1, "B1")):
            for variant, track in (("sector", "circuit"), ("full", "circuit"), ("full", "code")):
                try:
                    excl = (lambda n: HIDE(n) or SPARSE_L(n)) if track == "code" else HIDE
                    t["%s-%s-%s" % (key, track, variant)] = T.table(B, variant, track, threads, exclude=excl)
                except (OSError, ValueError):
                    pass
            try:
                t["L-%s-code" % key] = T.table(B, "full", "code", threads, methods=BASIS_COLUMNS)
            except (OSError, ValueError):
                pass
        for variant, track in (("sector", "circuit"), ("full", "code")):
            t["DM-B32-%s" % track] = T.table(B, variant, track, 32, methods=["dist-m4ri 0.9.0 CC+RW", "dist-m4ri CC+RW", "dist-m4ri CC",
                                                                              "dist-m4ri CC+RW, model bound"])
        bad = T.consistency(B, 32) + T.consistency(B, 1)
        t["B-check"] = "\n".join("- " + b for b in bad) if bad else "All second-tier records are mutually consistent and consistent with the ground truth."
    if ABL.is_dir():
        t["ablation"] = T.table(ABL, "sector", "circuit", 1)
    if (ROOT / "results" / "bench_wjh").is_dir():
        import wjh_compare
        t["wjh"] = wjh_compare.report()
    return t


def main(path=str(ROOT / "docs" / "BENCHMARK.md")):
    text = open(path).read()
    done = []
    for name, body in tables().items():
        if "(of 0)" in body:
            body = "No runs."
        pat = re.compile(r"(<!-- TABLE:%s:BEGIN -->\n).*?(<!-- TABLE:%s:END -->)" % (re.escape(name), re.escape(name)), re.S)
        if pat.search(text):
            text = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
            done.append(name)
    open(path, "w").write(text)
    print("filled:", ", ".join(done))


if __name__ == "__main__":
    main(*sys.argv[1:])
