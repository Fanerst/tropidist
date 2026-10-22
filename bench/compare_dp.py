"""The pipeline with and without the dense Rank DP front end (config dp=1), first tier, record by record.

For every instance variant with records of both configurations: status and time of each, the ratio, and what the
DP front end decided for the main problem and for the time-collapsed problem (from the record's notes).

usage: python bench/compare_dp.py [results/bench] [--all]   (--all also lists rows where nothing changed)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(folder):
    out = {}
    for f in sorted(Path(folder).glob("*__t1.json")):
        r = json.loads(f.read_text())
        out[f.name] = r
    return out


def decision(rec):
    notes = rec.get("notes")
    try:
        notes = json.loads(notes) if isinstance(notes, str) else (notes or {})
    except ValueError:
        return "", ""
    dp = notes.get("dp", {})
    def short(info):
        if not info:
            return ""
        d = info.get("decision", "")
        tag = "dp" if d.startswith("dp") else "search first" if d.startswith("search first") else "search"
        width = info.get("cut_rank")
        return tag + ("" if width is None else " (w=%d)" % width)
    return short(dp.get("main")), short(dp.get("collapsed"))


def main(argv):
    base = Path(argv[0]) if argv and not argv[0].startswith("--") else ROOT / "results" / "bench"
    show_all = "--all" in argv
    a, b = load(base / "ours_pipeline"), load(base / "ours_pipeline__dp-1")
    print("| instance variant | default | + DP | ratio | DP on main problem | DP on collapsed problem |")
    print("|---|---|---|---:|---|---|")
    n = dict(both=0, faster=0, slower=0, newly=0, lost=0)
    for name in sorted(set(a) & set(b)):
        ra, rb = a[name], b[name]
        sa, sb = ra.get("status"), rb.get("status")
        ta, tb = ra.get("seconds") or 0, rb.get("seconds") or 0
        n["both"] += 1
        if sa == "exact" and sb == "exact":
            ratio = ta / tb if tb > 0 else float("inf")
            n["faster"] += ratio > 1.5 and ta - tb > 1
            n["slower"] += ratio < 1 / 1.5 and tb - ta > 1
            changed = abs(ta - tb) > 1 and (ratio > 1.5 or ratio < 1 / 1.5)
        else:
            ratio = None
            n["newly"] += sb == "exact" and sa != "exact"
            n["lost"] += sa == "exact" and sb != "exact"
            changed = sa != sb
        if changed or show_all:
            main_d, coll_d = decision(rb)
            fmt = lambda s, t: "%s %.1f s" % (s, t) if s == "exact" else str(s)
            print("| %s | %s | %s | %s | %s | %s |" % (name.replace("__t1.json", "").replace("__", " "), fmt(sa, ta),
                  fmt(sb, tb), "" if ratio is None else "%.2g" % ratio, main_d, coll_d))
    print()
    print("%(both)d variants with both records: %(newly)d solved only with the DP front end, %(lost)d only without it; "
          "of those solved by both, %(faster)d at least 1.5x and 1 s faster with it, %(slower)d slower." % n)


if __name__ == "__main__":
    main(sys.argv[1:])
