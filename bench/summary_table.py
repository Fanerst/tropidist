"""Compact tables of benchmark results (Markdown), one row per instance and one column per method.

A cell is the time of an exact run, or what the run certified at the limit:
  3.2 s      exact (lower bound = upper bound, witness checked by the harness)
  3.2 s*     value returned by a tool that gives no witness
  >=7        certified lower bound only;  7..12  both bounds;  <=12  upper bound only (heuristics)
  †          no stored ground truth: the distance is the value on which the runs of the table close
  t/o        nothing certified at the limit;  skip  not run (give-up rule);  mem / err  failed;  -  not applicable

Usage: python bench/summary_table.py results/bench [--variant sector] [--track circuit] [--threads 1]
                                     [--methods "a;b;..."] [--out FILE]
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SHORT = [("ours_pipeline", "ours"), ("ours", "ours, plain"), ("distm4ri__mode-cc", "dist-m4ri CC"),
         ("distm4ri__mode-bracket", "dist-m4ri CC+RW"), ("milp__backend-scipy", "HiGHS"), ("milp__backend-cpsat", "CP-SAT"), ("milp__backend-gurobi", "Gurobi"),
         ("sat__mode-incremental", "SAT"), ("sat__mode-maxsat", "RC2"), ("CASHW", "CASHWMaxSAT"), ("enMaxCDCL", "enMaxCDCL"),
         ("-", "RC2 (Stim WCNF)"), ("-", "CASHWMaxSAT (Stim WCNF)"), ("-", "enMaxCDCL (Stim WCNF)"),
         ("qserf__method-cc", "Qubitserf CC"), ("qserf__method-bz", "Qubitserf BZ"), ("qserf__method-mitm", "Qubitserf MITM"),
         ("bposd", "BP+OSD"), ("isd", "ISD"), ("stim_search", "Stim search"), ("distm4ri__mode-rw", "dist-m4ri RW")]
HEURISTIC = ("BP+OSD", "ISD", "Stim search", "dist-m4ri RW")


def short(folder):
    if folder.startswith("ours_pipeline__"):
        return "ours, " + folder[len("ours_pipeline__"):].replace("__", " ").replace("-0", " off")
    stim = " (Stim WCNF)" if "encoding-stim" in folder else ""
    for key, name in SHORT:
        if key in ("CASHW", "enMaxCDCL"):
            if key in folder:
                return name + stim
        elif folder == key:
            return name
    if folder == "sat__mode-maxsat__encoding-stim":
        return "RC2" + stim
    return folder


def seconds(x):
    return "%.1f s" % x if x < 100 else "%.0f s" % x


def cell(rec, truth):
    if rec is None:
        return ""
    st, lb, ub = rec.get("status"), rec.get("lower_bound"), rec.get("upper_bound")
    notes = str(rec.get("notes") or "")
    if st == "exact":
        return seconds(rec.get("seconds") or 0) + ("*" if rec.get("value_only") and rec.get("witness") is None else "")
    if st == "unavailable":
        return "-"
    if st == "skipped":
        return "skip"
    if st == "error":
        low = (notes + " " + " ".join(map(str, (rec.get("harness") or {}).get("stderr_tail") or []))).lower()
        if "wall-time deadline" in low:
            return "t/o"
        return "mem" if ("memory" in low or "bad_alloc" in low or "sigkill" in low or "sigabrt" in low) else "err"
    if lb is not None and lb > 0 and ub is not None:
        return "%d..%d" % (lb, ub)
    if lb is not None and lb > 0:
        return ">=%d" % lb
    if ub is not None:
        return "<=%d" % ub + ("" if truth is None or ub != truth else " ok")
    return "t/o"


def load(results, threads):
    recs = {}
    for folder in sorted(os.listdir(results)):
        d = os.path.join(results, folder)
        if not os.path.isdir(d) or folder in ("lists", "logs"):
            continue
        for f in os.listdir(d):
            if not f.endswith("__t%d.json" % threads):
                continue
            inst, variant = f[:-5].split("__")[:2]
            try:
                recs[(short(folder), inst, variant)] = json.load(open(os.path.join(d, f)))
            except ValueError:
                pass
    return recs


def table(results, variant, track, threads, methods=None, instance_dir=HERE / "instances", select=None):
    recs = load(results, threads)
    names = [name for _, name in SHORT] + sorted({m for m, _, _ in recs} - {name for _, name in SHORT})
    cols = [m for m in names if any(k[0] == m and k[2] == variant for k in recs)]
    if methods:
        cols = [m for m in cols if m in methods]
    metas = []
    for p in sorted(Path(instance_dir).glob("*/meta.json")):
        m = json.loads(p.read_text())
        if m.get("track") == track and variant in m.get("variants", {}) and m.get("family") != "fixture" \
                and (select is None or select(m)):
            metas.append(m)
    metas = [m for m in metas if any((c, m["name"], variant) in recs for c in names)]     # rows with at least one run
    metas.sort(key=lambda m: (m.get("family", ""), m["variants"][variant]["cols"], m["name"]))
    cols = [c for c in cols if any(cell(recs.get((c, m["name"], variant)), None) not in ("", "-") for m in metas)]
    lines = ["| instance | n | columns | distance | " + " | ".join(cols) + " |",
             "|---|---:|---:|---:|" + "---:|" * len(cols)]
    solved = {c: 0 for c in cols}
    for m in metas:
        v = m["variants"][variant]
        truth = v.get("distance") if v.get("distance_kind") == "exact" else None
        agreed = None
        if truth is None:          # no stored ground truth: the value the runs of this table certify, if they close
            here = [recs[(c, m["name"], variant)] for c in names if (c, m["name"], variant) in recs]
            lbs = [r["lower_bound"] for r in here if r.get("lower_bound") is not None and r.get("status") in ("exact", "bounds", "timeout")]
            ubs = [r["upper_bound"] for r in here if r.get("upper_bound") is not None and (r.get("witness_ok") or r.get("value_only"))]
            if lbs and ubs and max(lbs) == min(ubs):
                agreed = truth = min(ubs)
        row = []
        for c in cols:
            rec = recs.get((c, m["name"], variant))
            row.append(cell(rec, truth))
            if rec is not None and rec.get("status") == "exact":
                solved[c] += 1
        shown = (str(truth) + ("†" if agreed is not None else "")) if truth is not None else (
            "?" if v.get("distance") is None else ">=%s" % v["distance"])
        lines.append("| %s | %s | %d | %s | " % (m["name"], m.get("n", ""), v["cols"], shown) + " | ".join(row) + " |")
    lines.append("| **solved exactly** (of %d) | | | | " % len(metas) +
                 " | ".join("" if c in HEURISTIC else "**%d**" % solved[c] for c in cols) + " |")
    return "\n".join(lines)


def consistency(results, threads, instance_dir=HERE / "instances"):
    """Checks that need no ground truth: on every problem the largest certified lower bound must not
    exceed the smallest upper bound over all methods, and nothing may contradict an exact ground truth.
    Returns a list of text lines, empty if all records agree."""
    recs = load(results, threads)
    by = {}
    for (method, inst, variant), r in recs.items():
        if r.get("status") in ("unavailable", "skipped") or (r.get("status") == "error" and r.get("witness_ok") is False):
            continue
        by.setdefault((inst, variant), []).append((method, r.get("lower_bound"), r.get("upper_bound"),
                                                   method in HEURISTIC))
    out = []
    for (inst, variant), rows in sorted(by.items()):
        lbs = [(lb, m) for m, lb, ub, heur in rows if lb is not None and not heur]
        ubs = [(ub, m) for m, lb, ub, heur in rows if ub is not None]
        if lbs and ubs and max(lbs)[0] > min(ubs)[0]:
            out.append("%s/%s: lower bound %d (%s) above upper bound %d (%s)" % ((inst, variant) + max(lbs) + min(ubs)))
        try:
            v = json.loads((Path(instance_dir) / inst / "meta.json").read_text())["variants"][variant]
        except (OSError, KeyError, ValueError):
            continue
        if v.get("distance_kind") == "exact" and v.get("distance") is not None:
            d = v["distance"]
            out += ["%s/%s: %s certifies lower bound %d above the distance %d" % (inst, variant, m, lb, d) for lb, m in lbs if lb > d]
            out += ["%s/%s: %s gives upper bound %d below the distance %d" % (inst, variant, m, ub, d) for ub, m in ubs if ub < d]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--variant", default="sector")
    ap.add_argument("--track", default="circuit")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--methods")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true", help="only the consistency checks")
    a = ap.parse_args()
    if a.check:
        bad = consistency(a.results, a.threads)
        print("\n".join(bad) if bad else "all records consistent")
        return 1 if bad else 0
    text = table(a.results, a.variant, a.track, a.threads, a.methods.split(";") if a.methods else None)
    if a.out:
        open(a.out, "w").write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
