"""Tables for the instances of arXiv:2603.22532 (Webster, Jacob, Higgott): our runs next to their published ones.

Ours: results/bench_wjh (first tier: 1 thread, 600 s, 16 GB: our pipeline, Gurobi, dist-m4ri CC) and
results/bench_wjh_tierB (32 threads, 1 h, 90 GB: our pipeline), on the instances of bench/instances_wjh.
Theirs: the spreadsheets of their codeDistance package (papers/downloads/codedistance/paper results), one per
family, one sheet per method.  Their exact methods are Gurobi, MIP-SCIP, CLISAT (MaxSAT), m4riCC (dist-m4ri
connected clusters) and Magma (Brouwer-Zimmermann), each run with one thread and an 8-hour limit on their
cluster.  A run of theirs counts as exact when it returned a distance before the limit (their 'Completed <
MaxTime'); the counts this gives are checked against the 'analysis' sheet of each spreadsheet.

usage: python bench/wjh_compare.py [--out FILE]      (prints Markdown)
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import summary_table as T
import xlsx_lite

SHEETS = ROOT / "papers" / "downloads" / "codedistance" / "paper results"
INSTANCES = HERE / "instances_wjh"
A, B = ROOT / "results" / "bench_wjh", ROOT / "results" / "bench_wjh_tierB"
MAX_TIME = 28800
# our family tag, their spreadsheet, a title
FAMILIES = [("surface_circuit", "08 qc_SC.xlsx", "surface-code circuits"),
            ("midout_circuit", "09 qc_CC_midout.xlsx", "colour-code circuits, midout"),
            ("superdense_circuit", "10 qc_CC_superdense.xlsx", "colour-code circuits, superdense"),
            ("bb_circuit", "11 qc_BB.xlsx", "bivariate bicycle circuits"),
            ("hsc", "04 hyperbolic_SC.xlsx", "hyperbolic surface codes"),
            ("hcc", "05 hyperbolic_CC.xlsx", "hyperbolic colour codes"),
            ("lp", "06 lifted_product.xlsx", "lifted-product codes"),
            ("bb", "07 bivariate_bicycle.xlsx", "bivariate bicycle codes"),
            ("qt", "12 tanner_codes.xlsx", "quantum Tanner codes")]
THEIR_EXACT = [("Gurobi", "Gurobi"), ("MIP-SCIP", "MIP-SCIP"), ("CLISAT", "CLISAT"), ("m4riCC", "m4ri_CC"),
               ("Magma", "magma")]
OURS = [("ours", "ours"), ("Gurobi", "Gurobi"), ("dist-m4ri CC", "dist-m4ri"), ("dist-m4ri CC+RW", "dist-m4ri")]


def sheet_rows(rows):
    """(name, n, k, d, seconds) for every data row under a 'name | n | k | d | delta d | Time' header."""
    out, on = [], False
    for r in rows:
        if r[:1] == ["name"]:
            on = True
            col = {c: i for i, c in enumerate(r)}
            continue
        if on and len(r) > col["Time"] and r[col["n"]].strip().isdigit():
            try:
                out.append((r[0], int(r[col["n"]]), int(r[col["k"]]), int(float(r[col["d"]] or 0)),
                            float(r[col["Time"]] or 0)))
            except ValueError:
                pass
        elif on and r and r[0] and not r[0].strip()[:1].isdigit() and not r[0].startswith(("[[", "AJ", "xu", "PK")):
            on = False
    return out


def their_counts(analysis):
    """'Completed < MaxTime' per exact method, from the analysis sheet."""
    for i, r in enumerate(analysis):
        if "Exact Methods" in r:
            j = r.index("Exact Methods")
            names = analysis[i + 1][j + 1:j + 6]
            for r2 in analysis[i + 2:i + 8]:
                if len(r2) > j and r2[j].startswith("Completed < Ma"):
                    return dict(zip(names, (int(float(x or 0)) for x in r2[j + 1:j + 6])))
    return {}


def metas():
    out = {}
    for p in sorted(INSTANCES.glob("*/meta.json")):
        m = json.loads(p.read_text())
        out[m["name"]] = m
    return out


def match(family, ms, theirs):
    """{our instance name: their row} for one family."""
    ours = [m for m in ms.values() if m["family"] == "wjh_" + family]
    out = {}
    if family.endswith("_circuit"):
        by_prefix = {m["source"]["key"][:3]: m["name"] for m in ours}
        for row in theirs:
            if row[0][:3] in by_prefix:
                out[by_prefix[row[0][:3]]] = row
        return out
    if family in ("lp", "qt"):
        tag = {m["source"]["key"][1]: m["name"] for m in ours}
        index = {c["name"]: c["index"] for c in json.loads((ROOT / "papers/downloads/codedistance_codes.json").read_text())["codes"]
                 if c["family"] == family}
        for row in theirs:
            if row[0] in index and index[row[0]] in tag:
                out[tag[index[row[0]]]] = row
        return out
    # bb: n is unique; hyperbolic: the i-th code with (n, k) in their sheet is the i-th in their file order
    seen = {}
    ordered = sorted(ours, key=lambda m: m["source"]["key"][1])
    for row in theirs:
        key = (row[1], row[2])
        i = seen.get(key, 0)
        seen[key] = i + 1
        cands = [m["name"] for m in ordered if (m["n"], m["k"]) == key]
        if i < len(cands):
            out[cands[i]] = row
    return out


def per_instance():
    """One dict per instance: name, family, track, our first- and second-tier times (exact runs only, else None)
    and the fastest exact run of theirs as (seconds, method) or None."""
    ms = metas()
    a1 = T.load(A, 1) if A.is_dir() else {}
    b32 = T.load(B, 32) if B.is_dir() else {}
    out = []
    for family, sheet, title in FAMILIES:
        book = xlsx_lite.read(str(SHEETS / sheet))
        fastest = {}
        for method, s in THEIR_EXACT:
            if s not in book:
                continue
            for name, row in match(family, ms, sheet_rows(book[s])).items():
                if row[3] > 0 and row[4] < MAX_TIME and (name not in fastest or row[4] < fastest[name][0]):
                    fastest[name] = (row[4], method)
        variant = "sector" if family.endswith("_circuit") else "full"
        for m in ms.values():
            if m["family"] != "wjh_" + family:
                continue
            t = lambda recs: (recs[("ours", m["name"], variant)]["seconds"] if ("ours", m["name"], variant) in recs
                              and recs[("ours", m["name"], variant)].get("status") == "exact" else None)
            out.append(dict(name=m["name"], family=family, title=title, track=m["track"], ours_t1=t(a1), ours_t2=t(b32),
                            theirs=fastest.get(m["name"])))
    return out


def ours_cell(rec):
    return T.cell(rec, None) if rec is not None else ""


def report():
    """Markdown: a summary table per family, then one table per family (in <details> blocks)."""
    ms = metas()
    a1 = T.load(A, 1) if A.is_dir() else {}
    b32 = T.load(B, 32) if B.is_dir() else {}
    summary = ["| family | instances | ours, tier 1 | ours, both tiers | Gurobi, tier 1 | dist-m4ri CC, tier 1 "
               "| theirs, 8 h: Gurobi / MIP-SCIP / CLISAT / m4riCC / Magma | any of theirs |",
               "|---|---:|---:|---:|---:|---:|---|---:|"]
    detail, notes, total = [], [], {}
    for family, sheet, title in FAMILIES:
        path = SHEETS / sheet
        book = xlsx_lite.read(str(path))
        their = {name: sheet_rows(book[s]) for name, s in THEIR_EXACT if s in book}
        counts = {name: 0 for name, _ in THEIR_EXACT}
        names = [m["name"] for m in sorted((m for m in ms.values() if m["family"] == "wjh_" + family),
                                           key=lambda m: (m["source"]["key"][1] if isinstance(m["source"]["key"], list)
                                                          else m["source"]["key"]))]
        exact_theirs = {n: [] for n in names}
        rows_of = {}
        for method, rows in their.items():
            mm = match(family, ms, rows)
            for name, row in mm.items():
                rows_of.setdefault(name, row)
                if row[3] > 0 and row[4] < MAX_TIME:
                    counts[method] += 1
                    exact_theirs[name].append((row[4], method, row[3]))
        published = their_counts(book.get("analysis", []))
        if published and any(published.get(k) != v for k, v in counts.items() if k in published):
            notes.append("%s: counts read from the sheets %s differ from their analysis sheet %s" % (title, counts, published))
        bestrows = [r for r in book.get("best", [])[1:] if len(r) > 3 and r[1].strip().isdigit()]
        best_map = match(family, ms, [(r[0], int(r[1]), int(r[2]), int(float(r[3] or 0)), 0.0) for r in bestrows])

        def solved(recs, method, name, variant):
            r = recs.get((method, name, variant))
            return r is not None and r.get("status") == "exact"

        variant = "sector" if family.endswith("_circuit") else "full"
        c = {}
        for key, method in (("o", "ours"), ("g", "Gurobi"), ("m", "dist-m4ri CC")):
            m2 = "dist-m4ri CC+RW" if method == "dist-m4ri CC" else method
            c[key + "1"] = sum(solved(a1, method, n, variant) for n in names)
            c[key] = sum(solved(a1, method, n, variant) or solved(b32, m2, n, variant) for n in names)
        anyt = sum(1 for n in names if exact_theirs[n])
        for k, v in c.items():
            total[k] = total.get(k, 0) + v
        total["n"] = total.get("n", 0) + len(names)
        total["any"] = total.get("any", 0) + anyt
        for k, v in counts.items():
            total["t_" + k] = total.get("t_" + k, 0) + v
        summary.append("| %s | %d | %d | %d | %d | %d | %s | %d |" % (
            title, len(names), c["o1"], c["o"], c["g1"], c["m1"],
            " / ".join(str(counts[k]) for k, _ in THEIR_EXACT), anyt))
        lines = ["", "<details><summary>%s (%d instances)</summary>" % (title[0].upper() + title[1:], len(names)), "",
                 "| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 "
                 "| dist-m4ri CC t1 | their fastest exact (8 h) |",
                 "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for n in names:
            m = ms[n]
            v = m["variants"][variant]
            recs = [r for r in (a1.get((x, n, variant)) for x in ("ours", "Gurobi", "dist-m4ri CC"))
                    if r is not None] + [r for r in (b32.get((x, n, variant)) for x in ("ours", "Gurobi", "dist-m4ri CC+RW"))
                                         if r is not None]
            lbs = [r["lower_bound"] for r in recs if r.get("lower_bound") is not None and r.get("status") in ("exact", "bounds", "timeout")]
            ubs = [r["upper_bound"] for r in recs if r.get("upper_bound") is not None and r.get("witness_ok")]
            d = (str(min(ubs)) if lbs and ubs and max(lbs) == min(ubs) else
                 ("%d..%d" % (max(lbs), min(ubs)) if lbs and ubs else (">=%d" % max(lbs) if lbs else "?")))
            fast = min(exact_theirs[n]) if exact_theirs[n] else None
            bk = best_map.get(n)
            lines.append("| %s | %s | %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
                n, m.get("n", ""), m.get("k", ""), v["cols"], d, bk[3] if bk else "",
                ours_cell(a1.get(("ours", n, variant))), ours_cell(b32.get(("ours", n, variant))),
                ours_cell(a1.get(("Gurobi", n, variant))), ours_cell(a1.get(("dist-m4ri CC", n, variant))),
                ("%s, %s" % (fast[1], T.seconds(fast[0]))) if fast else "none"))
        detail += lines + ["", "</details>"]
    summary.append("| **all** | %d | **%d** | **%d** | %d | %d | %s | %d |" % (
        total["n"], total["o1"], total["o"], total["g1"], total["m1"],
        " / ".join(str(total["t_" + k]) for k, _ in THEIR_EXACT), total["any"]))
    notes += agreement(ms, a1, b32)
    return "\n".join(summary + ([""] + ["- " + x for x in notes] if notes else []) + detail)


def agreement(ms, a1, b32):
    """Our exact values against theirs: equal to every value an exact method of theirs certified, and never
    above their best known value (an upper bound found by any of their methods)."""
    same = differ = below = 0
    out, lower = [], []
    for family, sheet, title in FAMILIES:
        book = xlsx_lite.read(str(SHEETS / sheet))
        variant = "sector" if family.endswith("_circuit") else "full"
        exact = {}
        for method, s in THEIR_EXACT:
            if s in book:
                for name, row in match(family, ms, sheet_rows(book[s])).items():
                    if row[3] > 0 and row[4] < MAX_TIME:
                        exact.setdefault(name, set()).add(row[3])
        rows = [r for r in book.get("best", [])[1:] if len(r) > 3 and r[1].strip().isdigit()]
        best = match(family, ms, [(r[0], int(r[1]), int(r[2]), int(float(r[3] or 0)), 0.0) for r in rows])
        for name in (n for n, m in ms.items() if m["family"] == "wjh_" + family):
            recs = [r for r in (a1.get(("ours", name, variant)), b32.get(("ours", name, variant)))
                    if r is not None and r.get("status") == "exact"]
            if not recs:
                continue
            d = recs[0]["upper_bound"]
            if name in exact:
                same += exact[name] == {d}
                differ += exact[name] != {d}
            if name in best and best[name][3] > 0 and best[name][3] != d:
                (lower if best[name][3] > d else out).append("%s: %d (their best %d)" % (name, d, best[name][3]))
    out = (["Our exact values agree with all %d values certified by their exact methods%s." % (
        same, "" if not differ else "; %d differ" % differ)] +
        ["Below their best known value: " + ", ".join(lower) if lower else "No exact value of ours is below their best known value."] +
        (["ABOVE their best known value (contradiction): " + ", ".join(out)] if out else []))
    return out


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
