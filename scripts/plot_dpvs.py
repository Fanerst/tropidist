"""Figure of the DP-versus-search test: wall time against distance for local codes (rotated surface and 6.6.6
color codes, code capacity) and against length for bivariate bicycle codes.  Reads results/dpvs/server/*.json.

usage: python scripts/plot_dpvs.py out.png
"""
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DP, SEARCH = "#2166ac", "#d95f02"          # blue / orange: distinguishable under the common colour-vision deficiencies


def collect():
    rows = {}
    for f in sorted(glob.glob(str(ROOT / "results/dpvs/server/*.json"))):
        for name, rec in json.load(open(f))["codes"].items():
            r = rows.setdefault(name, {"n": rec["n"]})
            dp = rec.get("dp", {})
            if "cut_rank" in dp:
                r["width"] = dp["cut_rank"]
                if dp.get("status") == "exact":
                    r["dp"] = dp["seconds"]
            s = rec.get("search")
            if s:
                r["search"] = s["seconds"]
                r["search_done"] = s["status"] == "exact"
                r["search_limit"] = max((x["seconds"] for x in s["runs"]), default=None)
    return rows


def main(out):
    rows = collect()
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [1.6, 1]})
    for fam, marker, label in (("surface", "o", "surface"), ("color", "s", "color")):
        pts = sorted((int(k.split(":")[-1]) if ":" in k else int(k), v) for k, v in rows.items()
                     if (fam == "surface" and k.isdigit()) or k.startswith(fam + ":"))
        dp = [(d, v["dp"]) for d, v in pts if "dp" in v]
        se = [(d, v["search"]) for d, v in pts if v.get("search_done")]
        to = [(d, v["search"]) for d, v in pts if "search" in v and not v.get("search_done")]
        a.plot(*zip(*dp), color=DP, marker=marker, lw=1.5, ms=6, label=f"Rank DP, {label} code")
        if se:
            a.plot(*zip(*se), color=SEARCH, marker=marker, lw=1.5, ms=6, ls="--", label=f"search, {label} code")
        if to:
            a.plot(*zip(*to), color=SEARCH, marker="^", ls="none", ms=8, mfc="white")
    a.set_yscale("log")
    a.set_xlabel("code distance d")
    a.set_ylabel("wall time (s), 16-32 threads")
    a.set_title("local codes, code capacity")
    a.grid(True, which="major", color="#dddddd", lw=0.6)
    a.legend(frameon=False, fontsize=8)

    bb = sorted((v["n"], k, v) for k, v in rows.items() if k.startswith("code_bb"))
    xs = list(range(len(bb)))
    labels = [f"[[{n}]]\nw={v.get('width', '?')}" for n, _, v in bb]
    dpv = [(x, v["dp"]) for x, (_, _, v) in zip(xs, bb) if "dp" in v]
    floor = 5e-3                               # times below the 0.01 s resolution of the records
    sev = [(x, max(v["search"], floor)) for x, (_, _, v) in zip(xs, bb) if "search" in v]
    b.plot(*zip(*dpv), color=DP, marker="D", lw=1.5, ms=6, label="Rank DP")
    for x, (_, _, v) in zip(xs, bb):
        if "dp" not in v:
            b.plot([x], [30], color=DP, marker="x", ms=9, mew=2)
            b.annotate("table too\nlarge", (x, 30), xytext=(0, -26), textcoords="offset points", ha="center",
                       fontsize=7, color=DP)
    b.plot(*zip(*sev), color=SEARCH, marker="D", lw=1.5, ms=6, ls="--", label="search")
    b.set_yscale("log")
    b.set_ylim(2e-3, 100)
    b.axhline(floor, color="#bbbbbb", lw=0.6, ls=":")
    b.annotate("< 0.01 s", (len(xs) - 0.6, floor), fontsize=7, color="#888888", va="bottom")
    b.set_xticks(xs, labels, fontsize=8)
    b.set_title("bivariate bicycle codes (w = DP width)")
    b.grid(True, which="major", color="#dddddd", lw=0.6)
    b.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
