"""The pipeline with and without the dense Rank DP front end (config dp=1), first tier, record by record.

For every instance variant with records of both configurations: status and time of each, the ratio, and what the
DP front end decided for the main problem and for the time-collapsed problem (from the record's notes), and, when
the second configuration has it (dp=2), what the sparse Rank DP decided on the sector's gap.

usage: python bench/compare_dp.py [results/bench] [--all] [--a CONFIG] [--b CONFIG]
       --all also lists rows where nothing changed; --a, --b: the two configuration folders (default ours_pipeline
       and ours_pipeline__dp-1), e.g. --a ours_pipeline__dp-1 --b ours_pipeline__dp-2
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


def sparse_decision(rec):
    """What config dp=2 did on the sector's gap: the sweeps of the sparse DP, or why the search kept it."""
    notes = rec.get("notes")
    try:
        notes = json.loads(notes) if isinstance(notes, str) else (notes or {})
    except ValueError:
        return None
    sp = notes.get("sparse")
    if not sp:
        return None
    if sp.get("sweeps"):
        return "sparse DP, K = %s (%.1f s)" % (", ".join(str(x["K"]) for x in sp["sweeps"]),
                                             sum(x["seconds"] for x in sp["sweeps"]))
    d = sp.get("decision", "")
    return d if len(d) < 60 else d[:57] + "..."


def main(argv):
    base = Path(argv[0]) if argv and not argv[0].startswith("--") else ROOT / "results" / "bench"
    show_all = "--all" in argv
    opt = lambda name, default: argv[argv.index(name) + 1] if name in argv else default
    names = opt("--a", "ours_pipeline"), opt("--b", "ours_pipeline__dp-1")
    a, b = load(base / names[0]), load(base / names[1])
    sparse = any(sparse_decision(r) is not None for r in b.values())
    labels = ("default", "+ DP") if names == ("ours_pipeline", "ours_pipeline__dp-1") else names
    print("| instance variant | %s | %s | ratio | DP on main problem | DP on collapsed problem |%s" % (
        labels[0], labels[1], " sparse DP |" if sparse else ""))
    print("|---|---|---|---:|---|---|" + ("---|" if sparse else ""))
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
            if sparse:
                fmt = lambda s, t, r: "%s %.1f s" % (s, t) if s == "exact" else str(s) if r.get("lower_bound") is None \
                    else "%s %s..%s" % (s, r["lower_bound"], r.get("upper_bound") if r.get("upper_bound") is not None else "")
                cells = (fmt(sa, ta, ra), fmt(sb, tb, rb))
            else:
                cells = (fmt(sa, ta), fmt(sb, tb))
            print("| %s | %s | %s | %s | %s | %s |%s" % (name.replace("__t1.json", "").replace("__", " "), cells[0],
                  cells[1], "" if ratio is None else "%.2g" % ratio, main_d, coll_d,
                  " %s |" % (sparse_decision(rb) or "") if sparse else ""))
    print()
    if names == ("ours_pipeline", "ours_pipeline__dp-1"):
        print("%(both)d variants with both records: %(newly)d solved only with the DP front end, %(lost)d only without "
              "it; of those solved by both, %(faster)d at least 1.5x and 1 s faster with it, %(slower)d slower." % n)
    else:
        print(("%(both)d variants with both records: %(newly)d solved only with " + names[1] + ", %(lost)d only with "
               + names[0] + "; of those solved by both, %(faster)d at least 1.5x and 1 s faster with " + names[1] +
               ", %(slower)d slower.") % n)


if __name__ == "__main__":
    main(sys.argv[1:])
