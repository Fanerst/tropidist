"""Tables for the rebuilt surface-code circuits of arXiv:2610.03682 (block RESULTS4C of PAPERS.md).

Reads results/papers4/hypsurf/table_s2_square*.json (graph-like survey, papers/hypsurf_table.py),
results/papers4/hypsurf/exact/*.json (exact circuit distances, papers/run_parallel.py) and, if
present, results/papers4/hypsurf/all_q*.json (all schedules, papers/hypsurf_all.py).
"""
import ast
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "papers4", "hypsurf")
KINDS = [("ZZ", False, "ZZ, same order every round"), ("ZZ", True, "ZZ, alternating"),
         ("NZ", False, "NZ, same order every round"), ("NZ", True, "NZ, alternating")]


def exact(name):
    out = {}
    for b in "ZX":
        f = os.path.join(RES, "exact", "%s_%s.json" % (name, b))
        if os.path.exists(f):
            r = json.load(open(f))
            lb, ub = r.get("certified_lower_bound"), r.get("certified_upper_bound")
            out[b] = (lb, ub)
    if len(out) < 2:
        return None
    lb, ub = min(v[0] for v in out.values()), min((v[1] for v in out.values() if v[1] is not None), default=None)
    return str(lb) if lb == ub else "%s–%s" % (lb, ub)


def survey():
    rows = {}
    for f in sorted(glob.glob(os.path.join(RES, "table_s2_square*.json"))):
        for r in json.load(open(f))["rows"]:
            d = r["distances"]
            rows.setdefault((r["q"], r["schedule"], r["alternating"]), {})[r["basis"]] = \
                (ast.literal_eval(d) if isinstance(d, str) else d, r["paper_value"])
    return rows


def main():
    sv = survey()
    lines = ["| tiling | code | schedule | paper (graph-like bound) | graph-like, 256 sampled assignments (count) | exact, first valid assignment | exact, best sampled assignment |",
             "|---|---|---|---:|---|---:|---:|"]
    for q in (6, 8, 10, 12):
        for kind, fb, label in KINDS:
            x, z = sv[(q, kind, fb)]["X"], sv[(q, kind, fb)]["Z"]
            both = [min(a, b) for a, b in zip(x[0], z[0])]
            hist = ", ".join("%d (%d)" % (v, both.count(v)) for v in sorted(set(both)))
            key = "q%d_L5_%s%s" % (q, kind, "_fb" if fb else "")
            best = max(both)
            pick = None
            for i, v in enumerate(both):
                if v == best:
                    e = exact("pick_%s_%d" % (key, i))
                    if e is not None:
                        pick = e
                        break
            lines.append("| {4,%d} | [[%d,%d,10]] | %s | %d | %s | %s | %s |" % (
                q, 25 * q, q - 2, label, x[1], hist, exact(key) or "", pick or ""))
    extra = []
    for f in sorted(glob.glob(os.path.join(RES, "all_q*.json"))):
        d = json.load(open(f))
        for name, s_ in d["summary"].items():
            extra.append("- {4,%d}, %s, all %d valid assignments: graph-like distance (min over bases) %s." % (
                d["q"], name.replace("_fb", ", alternating"), d["assignments_" + name.split("_")[0]],
                ", ".join("%s: %s" % kv for kv in s_["histogram_of_min_over_bases"].items())))
    text = "\n".join(lines) + ("\n\n" + "\n".join(extra) if extra else "")
    path = os.path.join(ROOT, "docs", "PAPERS.md")
    s = open(path).read()
    pat = re.compile(r"(<!-- RESULTS4C:BEGIN -->\n).*?(<!-- RESULTS4C:END -->)", re.S)
    if pat.search(s):
        open(path, "w").write(pat.sub(lambda m: m.group(1) + text + "\n" + m.group(2), s))
        print("PAPERS.md updated")
    print(text)


if __name__ == "__main__":
    main()
