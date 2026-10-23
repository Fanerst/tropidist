"""Our pipeline with config dp=2 (the sparse Rank DP, results/sparse_dp) against the default configuration and dp=1:
solved counts per suite and tier, and the instances whose outcome or time changed.

Main suite: one row per instance on its main problem, as in the overall table of docs/BENCHMARK.md
(make_benchmark_md.overall_rows), tier 1 = results/bench, tier 2 = results/bench_tierB (32 threads).  Instances of
arXiv:2603.22532: per family as in bench/wjh_compare.py, tier 1 = results/bench_wjh, tier 2 = results/bench_wjh_tierB.
dp=1 ("ours + DP") has first-tier records only.

usage: python bench/compare_dp2.py [--out FILE]
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
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


def report():
    return "\n".join(["### Main suite", "", main_suite(), "", "### Instances of arXiv:2603.22532", "", wjh()])


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
