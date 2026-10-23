"""Our pipeline with config dp=2 (the sparse Rank DP, results/sparse_dp) against the default configuration and dp=1:
solved counts per suite and tier, and the instances whose outcome or time changed.

Main suite: one row per instance on its main problem, as in the overall table of docs/BENCHMARK.md
(make_benchmark_md.overall_rows), tier 1 = results/bench, tier 2 = results/bench_tierB (32 threads).  Instances of
arXiv:2603.22532: per family as in bench/wjh_compare.py, tier 1 = results/bench_wjh, tier 2 = results/bench_wjh_tierB.
dp=1 ("ours + DP") has first-tier records only.

Then the first-tier records rerun with one code and at one time (results/bench_recheck, scripts/server/
dp2_recheck*.sh, dp1_table1gb.sh): those whose sparse stage runs the probe and those whose lookup tables got deeper
with the table budget fix of 7ef27aa, under dp=1, dp=2 and dp=1 with the former 1 GiB table budget, beside the
first dp=1 pass.

usage: python bench/compare_dp2.py [--out FILE]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import compare_dp as C
import make_benchmark_md as M
import summary_table as T
import wjh_compare as W

CONFIGS = ("ours", "ours + DP", "ours + sparse DP")


def changes(rows_a, rows_b, label_a, label_b):
    """Rows (name, a, b) where one solves and the other does not, or both solve and the time differs by more than
    1.5x and 1 s; per tier."""
    out = []
    for ra, rb in zip(rows_a, rows_b):
        name = ra[3]
        for tier, i in (("tier 1", 6), ("tier 2", 7)):
            ta, tb = ra[i], rb[i]
            if (ta is None) != (tb is None) or (ta is not None and abs(ta - tb) > 1 and max(ta, tb) > 1.5 * min(ta, tb)):
                out.append((name, tier, ta, tb))
    return out


def main_suite():
    rows = {c: M.overall_rows(c) for c in CONFIGS}
    lines = ["| configuration | instances | solved, tier 1 | solved, tiers 1 and 2 |", "|---|---:|---:|---:|"]
    for c in CONFIGS:
        r = rows[c]
        t1 = sum(x[6] is not None for x in r)
        both = sum(x[6] is not None or x[7] is not None for x in r)
        lines.append("| %s | %d | %d | %s |" % (c, len(r), t1, both if c != "ours + DP" else "(tier 1 only)"))
    f = lambda t: "–" if t is None else T.seconds(t)
    lines += ["", "Changed against the default (time differs by more than 1.5x and 1 s, or solved by one only):", "",
              "| instance | tier | ours | ours + sparse DP |", "|---|---|---:|---:|"]
    for name, tier, ta, tb in changes(rows["ours"], rows["ours + sparse DP"], "ours", "ours + sparse DP"):
        lines.append("| %s | %s | %s | %s |" % (name, tier, f(ta), f(tb)))
    return "\n".join(lines)


def wjh():
    ms = W.metas()
    a1, b32 = T.load(W.A, 1), T.load(W.B, 32)

    def solved(recs, method, name, variant):
        r = recs.get((method, name, variant))
        return r is not None and r.get("status") == "exact"

    def secs(recs, method, name, variant):
        r = recs.get((method, name, variant))
        return r["seconds"] if r is not None and r.get("status") == "exact" else None

    lines = ["| family | instances | ours, tier 1 | ours, tiers 1 and 2 | ours + sparse DP, tier 1 | "
             "ours + sparse DP, tiers 1 and 2 |", "|---|---:|---:|---:|---:|---:|"]
    total = [0] * 5
    diff = []
    for family, _, title in W.FAMILIES:
        variant = "sector" if family.endswith("_circuit") else "full"
        names = [m["name"] for m in ms.values() if m["family"] == "wjh_" + family]
        c = [len(names)]
        for method in ("ours", "ours + sparse DP"):
            c.append(sum(solved(a1, method, n, variant) for n in names))
            c.append(sum(solved(a1, method, n, variant) or solved(b32, method, n, variant) for n in names))
        for n in names:
            for tier, recs in (("tier 1", a1), ("tier 2", b32)):
                ta, tb = secs(recs, "ours", n, variant), secs(recs, "ours + sparse DP", n, variant)
                if tier == "tier 2":            # tier 2 ran only on what each configuration's tier 1 left
                    ta = ta if secs(a1, "ours", n, variant) is None else None
                    tb = tb if secs(a1, "ours + sparse DP", n, variant) is None else None
                if (ta is None) != (tb is None) or (ta is not None and abs(ta - tb) > 1 and
                                                    max(ta, tb) > 1.5 * min(ta, tb)):
                    diff.append((n, tier, ta, tb))
        total = [x + y for x, y in zip(total, c)]
        lines.append("| %s | %d | %d | %d | %d | %d |" % ((title,) + tuple(c)))
    lines.append("| **all** | %d | %d | %d | %d | %d |" % tuple(total))
    f = lambda t: "–" if t is None else T.seconds(t)
    lines += ["", "Changed (time differs by more than 1.5x and 1 s, or solved by one only; tier 2 counts the runs of "
              "what tier 1 left):", "", "| instance | tier | ours | ours + sparse DP |", "|---|---|---:|---:|"]
    lines += ["| %s | %s | %s | %s |" % (n, tier, f(ta), f(tb)) for n, tier, ta, tb in diff]
    return "\n".join(lines)


def recheck(folder=ROOT / "results" / "bench_recheck"):
    """One row per record of the recheck (its dp=1 runs): the first dp=1 pass, then dp=1 with 1 GiB tables, dp=1
    and dp=2 rerun side by side, and what dp=2's sparse stage did (its probe time and weights).  dp=2's reruns of
    the records whose sparse stage runs the probe replaced the first pass in results/bench and results/bench_wjh;
    those of the others are in the recheck folder."""
    res = ROOT / "results"
    first = [res / "bench" / "ours_pipeline__dp-1", res / "bench_wjh" / "ours_pipeline__dp-1"]
    cols = [("dp=1, 22 Oct", first), ("dp=1, 1 GiB tables", [folder / "ours_pipeline__dp-1__table%5Fgb-1"]),
            ("dp=1", [folder / "ours_pipeline__dp-1"]),
            ("dp=2", [folder / "ours_pipeline__dp-2", res / "bench" / "ours_pipeline__dp-2",
                      res / "bench_wjh" / "ours_pipeline__dp-2"])]
    names = sorted(f.name for f in (folder / "ours_pipeline__dp-1").glob("*__t1.json"))

    def record(dirs, name):
        for d in dirs:
            if (d / name).exists():
                return json.loads((d / name).read_text())
        return None

    def cell(r):
        if r is None:
            return ""
        if r.get("status") == "exact":
            return T.seconds(r["seconds"])
        lb, ub = r.get("lower_bound"), r.get("upper_bound")
        return r.get("status", "") + ("" if lb is None else " %s..%s" % (lb, "" if ub is None else ub))

    def probe(r):
        notes = r.get("notes") if r else None
        try:
            notes = json.loads(notes) if isinstance(notes, str) else (notes or {})
        except ValueError:
            notes = {}
        sp = notes.get("sparse") or {}
        if "probe_seconds" not in sp:
            return ""
        return "%.2f s (weights %s)" % (sp["probe_seconds"], "/".join(map(str, sp.get("probe_weights", ["≤3"]))))

    lines = ["| instance variant | " + " | ".join(c for c, _ in cols) + " | dp=2: sparse stage | dp=2: probe |",
             "|---|" + "---:|" * len(cols) + "---|---|"]
    for name in names:
        rs = [record(dirs, name) for _, dirs in cols]
        lines.append("| %s | %s | %s | %s |" % (name.replace("__t1.json", "").replace("__", " "),
                                                " | ".join(cell(r) for r in rs),
                                                (C.sparse_decision(rs[-1]) or "") if rs[-1] else "", probe(rs[-1])))
    return "\n".join(lines)


def report():
    parts = ["### Main suite", "", main_suite(), "", "### Instances of arXiv:2603.22532", "", wjh()]
    if (ROOT / "results" / "bench_recheck").exists():
        parts += ["", "### First tier rerun with one code and at one time", "", recheck()]
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out")
    a = ap.parse_args()
    text = report()
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
