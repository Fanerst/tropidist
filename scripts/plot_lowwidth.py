"""Figure of the low-width trial (bench/export_lowwidth.py, results/bench_lowwidth): time to the certified distance
against the distance, one line per exact method, for the color codes and the concatenated Steane codes (first tier:
one thread, 600 s).  Each line ends at the last distance the method certified.  Hollow markers: our configurations
in the second tier (32 threads, 3600 s, results/bench_lowwidth_tierB), run only on what their first tier left.

usage: python scripts/plot_lowwidth.py out.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import summary_table as T

SURFACE, INK, INK2, MUTED, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#c3c2b7"
BLUE, AQUA, GRAY = "#2a78d6", "#1baf7a", "#898781"
OURS = {"ours": ("this method (search pipeline)", BLUE, "o", "-"),
        "ours + DP": ("this method with the Rank DP front end", AQUA, "s", (0, (4, 2)))}


def main(out):
    recs = T.load(ROOT / "results" / "bench_lowwidth", 1)
    tier2 = ROOT / "results" / "bench_lowwidth_tierB"
    recs2 = T.load(tier2, 32) if tier2.is_dir() else {}
    metas = {m["name"]: m for m in (json.loads(p.read_text())
                                     for p in (ROOT / "bench" / "instances_lowwidth").glob("*/meta.json"))}
    methods = sorted({k[0] for k in recs} - set(T.HEURISTIC))
    n_other = len([m for m in methods if m not in OURS and m != "ours, plain"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, fam, title, offset in ((axes[0], "color_cc", "triangular color codes", (6, -12)),
                                   (axes[1], "concat_steane", "concatenated Steane codes", (6, 4))):
        names = sorted((m["variants"]["full"]["distance"], n) for n, m in metas.items() if m["family"] == fam)
        lines = {}
        for meth in methods:
            if meth == "ours, plain":                # the same search as "ours" on code instances
                continue
            pts = []
            for d, n in names:
                r = recs.get((meth, n, "full"))
                if r is not None and r.get("status") == "exact":
                    pts.append((d, max(r["seconds"], 0.01)))
            if pts:
                lines[meth] = pts
        others = [m for m in lines if m not in OURS]
        best = max(others, key=lambda m: (lines[m][-1][0], -lines[m][-1][1])) if others else None
        for meth, pts in lines.items():
            label, color, marker, ls = OURS.get(meth, (meth, GRAY, "o", "-"))
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, marker=marker, linestyle=ls,
                    linewidth=1.8 if meth in OURS else 1.0, markersize=5.5 if meth in OURS else 3.5,
                    alpha=1.0 if meth in OURS else 0.75, zorder=4 if meth in OURS else 2,
                    label=label if meth in OURS else None)
        for meth, (label, color, marker, ls) in OURS.items():
            pts = [(d, recs2[(meth, n, "full")]["seconds"]) for d, n in names
                   if recs2.get((meth, n, "full"), {}).get("status") == "exact"]
            if pts:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], linestyle="none", marker=marker, markersize=6.5,
                        markerfacecolor=SURFACE, markeredgecolor=color, markeredgewidth=1.6, zorder=5)
        if best:
            ax.annotate("best other: " + best, lines[best][-1], xytext=offset, textcoords="offset points",
                        fontsize=7.5, color=INK2, va="center")
        ax.plot([], [], color=GRAY, linewidth=1.0, label="the other %d exact methods" % n_other)
        if recs2:
            ax.plot([], [], linestyle="none", marker="o", markersize=6.5, markerfacecolor=SURFACE,
                    markeredgecolor=INK2, markeredgewidth=1.4, label="this method, 32 threads, 3600 s (second tier)")
        for limit, text in ((600, "600 s, 1 thread"), (3600, "3600 s, 32 threads")):
            ax.axhline(limit, color=AXIS, linewidth=0.7)
            ax.annotate(text, (1, limit), xycoords=("axes fraction", "data"), xytext=(-2, 2),
                        textcoords="offset points", ha="right", va="bottom", fontsize=6.5, color=MUTED)
        ax.set_yscale("log")
        ax.set_ylim(0.007, 9000)
        ax.set_xlabel("distance d", fontsize=8.5)
        ax.set_title(title, fontsize=9.5)
        ax.grid(True, which="major", color="#e1e0d9", linewidth=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("seconds to the certified distance", fontsize=8.5)
    for ax in axes:
        ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
