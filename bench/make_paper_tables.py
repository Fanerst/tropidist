"""Numbers and tables of the paper's numerical sections, computed from the result records.

usage: python bench/make_paper_tables.py PAPER_DIR
writes PAPER_DIR/numbers.tex (one macro per quoted number) and PAPER_DIR/tables/*.tex.
Nothing here is typed in by hand except instance labels and the solver list.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT)]
import make_benchmark_md as MB
import summary_table as T
import wjh_compare as W

A, B, ABL = ROOT / "results/bench", ROOT / "results/bench_tierB", ROOT / "results/bench_ablation_final"
MINE = {"ours", "ours, search only", "ours, plain", "ours + DP"}
CODE_D = {72: 6, 90: 10, 108: 10, 144: 12, 288: 18}          # code distances of the BB codes, for labels


# ----------------------------------------------------------------------------------------------- instances
def metas():
    out = {}
    for p in sorted((HERE / "instances").glob("*/meta.json")):
        m = json.loads(p.read_text())
        if m.get("family") != "fixture":
            out[m["name"]] = m
    return out


def main_variant(m):
    return "full" if (m["track"] == "code" or "sector" not in m["variants"]) else "sector"


def label(m):
    """A readable name for a benchmark instance."""
    f, n, k, name = m.get("family"), m.get("n"), m.get("k"), m["name"]
    if f == "surface":
        return "surface code, $d=%d$" % m["rounds"]
    if f == "stim_color":
        return "color code, $d=%d$" % m["rounds"]
    if f == "superdense":
        return "superdense color code, $d=%d$" % m["rounds"]
    if m["track"] == "code":
        kind = {"bb6": "BB", "cornucopia": "Cornucopia", "gala": "GALA", "kasai": "Kasai", "selfdual_bb": "self-dual BB",
                "estimated_codes": None, "color_cc": "color", "concat_steane": "concatenated Steane",
                "hypercube": "many-hypercube", "dtc_strip": "thin tile"}[f]
        if kind is None:
            kind = {"balanced": "balanced product", "llmbb": "LLM-searched BB", "mm": "multivariate multicycle",
                    "w8bb": "weight-8 BB"}[name.split("_")[1]]
        v = m["variants"]["full"]
        if v.get("distance_kind") != "exact":            # a thin tile code whose X distance is open
            return "%s $[[%d,%d]]$" % (kind, n, k)
        if f == "dtc_strip":                             # one sector only: the paper's d_Z is 4 or 5
            return "%s $[[%d,%d]]$, $d_X=%d$" % (kind, n, k, v["distance"])
        return "%s $[[%d,%d,%d]]$" % (kind, n, k, v["distance"])
    if f == "bb6_si1000":
        return "BB $[[%d,%d,%d]]$, %d rounds" % (n, k, CODE_D[n], m["rounds"])
    if f == "bb6_depth7":
        return "BB $[[%d,%d,%d]]$, best depth-7 schedule" % (n, k, CODE_D[n])
    kind = {"cornucopia": "Cornucopia", "mitten": "mitten", "routing": "routing", "sdbb_parallel": "self-dual BB",
            "shift": "shift automorphism", "star": "STAR", "walkingcat": "Walking Cat", "bb8_parallel": "weight-8 BB",
            "lrgross": "left-right gross"}[f]
    return "%s $[[%d,%d]]$" % (kind, n, k)


# ----------------------------------------------------------------------------------------------- crediting
def tool(meth):
    """The tool a configuration belongs to: a tool is credited with an instance if any configuration solves it."""
    base = meth.replace(", sparse L", "")
    if base.startswith("dist-m4ri 0.9.0"):
        return "dist-m4ri 0.9.0"
    if base.startswith("dist-m4ri"):
        return "dist-m4ri"
    return base


class Records:
    def __init__(self):
        self.a, self.b32, self.b1 = T.load(A, 1), T.load(B, 32), T.load(B, 1)
        self.m = metas()
        self.main = {n: main_variant(m) for n, m in self.m.items()}

    def ex(self, recs, meth, i, v):
        r = recs.get((meth, i, v))
        return r is not None and r.get("status") == "exact"

    def tools_solving(self, i, v, tiers=("t1", "t2"), old=False):
        out = {}
        for name, recs in (("t1", self.a), ("t2", self.b32), ("t2", self.b1)):
            if name not in tiers:
                continue
            for (m, ii, vv), r in recs.items():
                if ii != i or vv != v or m in MINE or m in T.HEURISTIC or r.get("status") != "exact":
                    continue
                if m.startswith("dist-m4ri 0.9.0") and not old:
                    continue
                out[tool(m)] = min(out.get(tool(m), 1e18), r["seconds"])
        return out

    def ours(self, i, v, tier):
        return self.ex(self.a, "ours", i, v) or (tier == 2 and self.ex(self.b32, "ours", i, v))


# ----------------------------------------------------------------------------------------------- numbers
def numbers(R):
    N = {}
    names = list(R.m)
    circ = [n for n in names if R.m[n]["track"] == "circuit"]
    codes = [n for n in names if R.m[n]["track"] == "code"]
    N["NumInst"], N["NumCirc"], N["NumCode"] = len(names), len(circ), len(codes)
    for suffix, sel in (("", names), ("Circ", circ), ("Code", codes)):
        N["OursFirst" + suffix] = sum(R.ours(n, R.main[n], 1) for n in sel)
        N["OursBoth" + suffix] = sum(R.ours(n, R.main[n], 2) for n in sel)
        N["OthersFirst" + suffix] = sum(bool(R.tools_solving(n, R.main[n], ("t1",))) for n in sel)
        N["OthersBoth" + suffix] = sum(bool(R.tools_solving(n, R.main[n])) for n in sel)
    N["OursOnly"] = sum(1 for n in names if R.ours(n, R.main[n], 2) and not R.tools_solving(n, R.main[n], old=True))
    N["OthersOnly"] = sum(1 for n in names if R.tools_solving(n, R.main[n], old=True) and not R.ours(n, R.main[n], 2))
    per = {}
    for n in names:
        for t in R.tools_solving(n, R.main[n], ("t1",), old=True):
            per.setdefault(t, [0, 0])[0] += 1
        for t in R.tools_solving(n, R.main[n], old=True):
            per.setdefault(t, [0, 0])[1] += 1
    for key, t in (("Dm", "dist-m4ri"), ("DmOld", "dist-m4ri 0.9.0"), ("Gurobi", "Gurobi"), ("Cpsat", "CP-SAT"),
                   ("Highs", "HiGHS"), ("Sat", "SAT"), ("Rc", "RC2"), ("Cashw", "CASHWMaxSAT"), ("Enmax", "enMaxCDCL"),
                   ("QserfCC", "Qubitserf CC"), ("QserfBZ", "Qubitserf BZ")):
        N[key + "First"], N[key + "Both"] = per.get(t, [0, 0])
    # the current dist-m4ri without its model lower bound (its configurations without ", model bound")
    def dm_nobound(i, v, tiers):
        return any(tool(m) == "dist-m4ri" and "model bound" not in m and r.get("status") == "exact"
                   for name, recs in (("t1", R.a), ("t2", R.b32), ("t2", R.b1)) if name in tiers
                   for (m, ii, vv), r in recs.items() if ii == i and vv == v)
    N["DmNoBoundFirst"] = sum(dm_nobound(n, R.main[n], ("t1",)) for n in names)
    N["DmNoBoundBoth"] = sum(dm_nobound(n, R.main[n], ("t1", "t2")) for n in names)
    # where dist-m4ri is faster (first tier, both exact)
    new = ["dist-m4ri CC", "dist-m4ri CC+RW", "dist-m4ri CC, DEM input", "dist-m4ri CC+RW, DEM input"]
    new += [m + ", model bound" for m in new]          # with its model lower bound (25 October 2026)
    faster, slower = [], []
    for n in names:
        v = R.main[n]
        if not R.ex(R.a, "ours", n, v):
            continue
        o = R.a[("ours", n, v)]["seconds"]
        ts = [R.a[(m, n, v)]["seconds"] for m in new if R.ex(R.a, m, n, v)]
        if ts and min(ts) < o:
            faster.append((n, o, min(ts)))
        elif ts and min(o, min(ts)) > 1:
            slower.append(min(ts) / o)
    N["FasterAll"] = len(faster)
    N["FasterSmall"] = sum(1 for _, o, t in faster if o < 2)
    N["SlowerCount"] = len(slower)
    N["SlowerMin"], N["SlowerMax"] = "%d" % min(slower), "%d" % max(slower)
    # the time-collapsed relaxation and the raw model
    sec_circ = [n for n in circ if "sector" in R.m[n]["variants"]]
    dm = lambda n, v: R.ex(R.a, "dist-m4ri CC", n, v) or R.ex(R.a, "dist-m4ri CC+RW", n, v)
    N["NumSector"] = len(sec_circ)
    N["CollDm"], N["SecDm"] = sum(dm(n, "collapsed") for n in sec_circ), sum(dm(n, "sector") for n in sec_circ)
    N["CollHighs"] = sum(R.ex(R.a, "HiGHS", n, "collapsed") for n in sec_circ)
    N["SecHighs"] = sum(R.ex(R.a, "HiGHS", n, "sector") for n in sec_circ)
    N["CollPlain"] = sum(R.ex(R.a, "ours, plain", n, "collapsed") for n in sec_circ)
    qldpc = [n for n in circ if R.m[n].get("family") not in ("surface", "stim_color")]
    N["NumQldpc"] = len(qldpc)
    N["RawOurs"] = sum(R.ex(R.a, "ours", n, "full") for n in qldpc)
    N["SecOursQldpc"] = sum(R.ex(R.a, "ours", n, "sector") for n in qldpc)
    N["RawDmMatrix"] = sum(dm(n, "full") for n in qldpc)
    N["RawDmDem"] = sum(any(R.ex(R.a, m + b, n, "full") for m in ("dist-m4ri CC, DEM input", "dist-m4ri CC+RW, DEM input")
                            for b in ("", ", model bound")) for n in qldpc)
    stim = [m for m in ("RC2 (Stim WCNF)", "CASHWMaxSAT (Stim WCNF)", "enMaxCDCL (Stim WCNF)")]
    N["WcnfQldpc"] = sum(any(R.ex(recs, m, n, "full") for recs in (R.a, R.b1) for m in stim) for n in qldpc)
    lbs = [r.get("lower_bound") or 0 for recs in (R.a, R.b1) for (m, n, v), r in recs.items()
           if m in stim and n in qldpc and v == "full"]
    N["WcnfBestLB"] = max(lbs)
    # ablation (first tier, circuits with a sector problem)
    abl = T.load(ABL, 1)
    for key, m in (("AblNoCollapse", "ours, collapse off"), ("AblNoSymmetry", "ours, symmetry off"),
                   ("AblNoLift", "ours, lift off"), ("AblNoCover", "ours, cover off"), ("AblNoWindow", "ours, window off")):
        N[key] = sum(R.ex(abl, m, n, "sector") for n in sec_circ)
    N["AblFull"] = sum(R.ex(R.a, "ours", n, "sector") for n in sec_circ)
    # surface codes
    surf = sorted((R.m[n]["rounds"], n) for n in circ if R.m[n].get("family") == "surface")
    N["SurfMaxFirst"] = max(d for d, n in surf if R.ex(R.a, "ours", n, "sector"))
    N["SurfMaxBoth"] = max(d for d, n in surf if R.ours(n, "sector", 2))
    top = [n for d, n in surf if d == N["SurfMaxBoth"]][0]
    if not R.ex(R.a, "ours", top, "sector"):                           # seconds of the largest, in the second tier
        N["SurfMaxBothSeconds"] = "%.0f" % R.b32[("ours", top, "sector")]["seconds"]
    # the dense Rank DP front end (configuration ours + DP, first tier)
    dp_surf = [(d, n) for d, n in surf if R.ex(R.a, "ours + DP", n, "sector")]
    if dp_surf:
        d_dp, n_dp = max(dp_surf)
        N["SurfDpMax"] = d_dp
        N["SurfDpMaxSeconds"] = "%.0f" % R.a[("ours + DP", n_dp, "sector")]["seconds"]
    # the prior benchmark
    rep = W.report()
    c = wjh_summary_rows()[-1]
    N["WjhNum"], N["WjhOursFirst"], N["WjhOursEight"], N["WjhOursBoth"] = c[1], c[2], c[3], c[4]
    N["WjhGurobiFirst"], N["WjhDmOld"], N["WjhDmFirst"], N["WjhDmBoth"] = c[5], c[7], c[8], c[9]
    # columns 10 and 11: dist-m4ri with its model bound (circuits only); 12 and 13: the paper's own methods
    their = [int(x) for x in c[12].split(" / ")]
    N["WjhTheirGurobi"], N["WjhTheirScip"], N["WjhTheirClisat"], N["WjhTheirDm"], N["WjhTheirMagma"] = their
    N["WjhTheirs"] = c[13]
    m = re.search(r"agree with all (\d+) values", rep)
    N["WjhAgree"] = m.group(1)
    N["WjhNew"] = int(c[4]) - int(c[13])
    N["WjhCodes"] = sum(1 for x in W.metas().values() if x["track"] == "code")
    N["WjhCircuits"] = sum(1 for x in W.metas().values() if x["track"] == "circuit")
    return N, faster


# ----------------------------------------------------------------------------------------------- tables
def sec(t):
    return "" if t is None else (r"%.1f\,s" % t if t < 100 else "{:,.0f}".format(t) + r"\,s")


def other(x, tier):
    if x is None:
        return ""
    t, m = x
    m = m.replace(", 32 threads", "").replace(", 1 thread", "")
    return r"%s (%s%s)" % (sec(t), m.replace("dist-m4ri CC+RW", "dist-m4ri").replace("dist-m4ri CC", "dist-m4ri"),
                          "" if tier == 1 else "")


def overall_table(R):
    rows = MB.overall_rows()
    out = {"circuit": [], "code": []}
    for is_code, fam, cols, name, nq, d, oa, ob, ca, cb in rows:
        m = R.m[name]
        dd = str(d).replace("†", r"$^\dagger$").replace(">=", r"$\geq$")
        out["code" if is_code else "circuit"].append(" & ".join(
            [label(m), "{:,}".format(cols), dd, sec(oa), sec(ob), other(ca, 1), other(cb, 2)]) + r" \\")
    head = (r"\begin{tabular}{@{}lrrllll@{}}" "\n" r"\toprule" "\n"
            r"instance & columns & $d$ & ours, tier 1 & ours, tier 2 & best other, tier 1 & best other, tier 2 \\"
            "\n" r"\midrule")
    for key, rws in out.items():
        Path(PAPER / "tables" / ("overall_%s.tex" % key)).write_text(
            head + "\n" + "\n".join(rws) + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def representative_table(R):
    pick = ["bb72_r6", "bb90_r10", "bb144_r12", "bb288_r18", "cornucopia_1044", "code_bb288", "code_balanced_625"]
    rows = {r[3]: r for r in MB.overall_rows()}
    lines = [r"\begin{tabular}{@{}lrrll@{}}", r"\toprule",
             r"instance & columns & $d$ & this method & best other exact method \\", r"\midrule"]
    for n in pick:
        is_code, fam, cols, name, nq, d, oa, ob, ca, cb = rows[n]
        ours = sec(oa) if oa is not None else sec(ob) + ", 32 threads"
        best = ca if ca is not None else cb
        tier2 = ca is None and cb is not None
        o = "none" if best is None else "%s, %s%s" % (best[1].split(" (")[0].replace(" CC+RW", "").replace(" CC", "").split(",")[0],
                                                     sec(best[0]), ", 32 threads" if tier2 else "")
        lines.append(" & ".join([label(R.m[n]), "{:,}".format(cols), str(d).replace("†", ""), ours, o]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (PAPER / "tables" / "representative.tex").write_text("\n".join(lines) + "\n")


def wjh_summary_rows():
    """The rows of the summary table of wjh_compare.report(), up to and including the total."""
    rows = []
    for l in W.report().splitlines():
        if not l.startswith("|") or l.startswith("|---") or l.startswith("| family"):
            continue
        rows.append([x.strip().strip("*") for x in l.strip("|").split("|")])
        if rows[-1][0] == "all":
            return rows
    raise ValueError("no total row in the summary of wjh_compare.report()")


FAMILY_LABEL = {"surface-code circuits": "surface-code circuits", "colour-code circuits, midout": "color-code circuits, midout",
                "colour-code circuits, superdense": "color-code circuits, superdense",
                "bivariate bicycle circuits": "BB circuits", "hyperbolic surface codes": "hyperbolic surface codes",
                "hyperbolic colour codes": "hyperbolic color codes", "lifted-product codes": "lifted-product codes",
                "bivariate bicycle codes": "BB codes", "quantum Tanner codes": "quantum Tanner codes", "all": "all"}


def wjh_table():
    lines = [r"\begin{tabular}{@{}lrrrrrrll@{}}", r"\toprule",
             r" & & \multicolumn{3}{c}{this method} & dist-m4ri & Gurobi & \multicolumn{2}{c}{ref.~\citenum{webster_2026_distance}} \\",
             r"\cmidrule(lr){3-5}\cmidrule(lr){8-9}",
             r"family & inst. & 600\,s & 8\,h & +32 thr. & 600\,s & 600\,s & per method & any \\", r"\midrule"]
    for c in wjh_summary_rows():
        if c[0] == "all":
            lines.append(r"\midrule")
        lines.append(" & ".join([FAMILY_LABEL[c[0]], c[1], c[2], c[3], c[4], c[8], c[5], c[12].replace(" / ", "/"), c[13]])
                     + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (PAPER / "tables" / "wjh.tex").write_text("\n".join(lines) + "\n")


def codes_table(R):
    """Both CSS distances of the 16 codes: the benchmark's sector and the other one (scripts/codes_other_basis.py)."""
    path = ROOT / "results" / "codes_other_basis" / "other_basis.json"
    if not path.exists():
        return False
    ob = json.loads(path.read_text())["codes"]
    lines = [r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule", r"code & $n$ & $k$ & $d_X$ & $d_Z$ \\", r"\midrule"]
    for name, m in sorted(R.m.items(), key=lambda kv: (kv[1]["n"], kv[0])):
        if m["track"] != "code":
            continue
        r = ob.get(name)
        v = m["variants"]["full"]
        # an open instance shows the strongest certified lower bound: the metadata's or one of our runs
        lbs = [r.get("lower_bound") or 0 for recs in (R.a, R.b32) for r in [recs.get(("ours", name, "full"))] if r]
        bench = (r"$\geq%d$" % max([v["distance"]] + lbs)) if v.get("distance_kind") == "lower_bound" else v["distance"]
        if r is None:
            vals = {"d_X": str(bench) if m["basis"] == "Z" else "", "d_Z": str(bench) if m["basis"] == "X" else ""}
        else:
            o = str(r["distance"]) if r["distance"] is not None else r"$\geq%d$" % r["lower_bound"]
            vals = {r["benchmark_distance_name"]: str(bench), r["other_distance_name"]: o}
        lines.append(" & ".join([label(m), str(m["n"]), str(m["k"]), vals.get("d_X", ""), vals.get("d_Z", "")]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (PAPER / "tables" / "codes.tex").write_text("\n".join(lines) + "\n")
    return True


def write_numbers(N):
    lines = ["% generated by bench/make_paper_tables.py from the result records; do not edit"]
    for k in sorted(N):
        lines.append(r"\newcommand{\%s}{%s}" % (k, N[k]))
    (PAPER / "numbers.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    PAPER = Path(sys.argv[1]).resolve()
    (PAPER / "tables").mkdir(parents=True, exist_ok=True)
    R = Records()
    N, faster = numbers(R)
    write_numbers(N)
    overall_table(R)
    representative_table(R)
    wjh_table()
    print("codes table:", codes_table(R))
    for k in sorted(N):
        print("  %s = %s" % (k, N[k]))
