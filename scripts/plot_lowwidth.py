"""Figure of the low-width trial (bench/export_lowwidth.py, results/bench_lowwidth): time to the certified distance
against the distance, one line per exact method, for the color codes and the concatenated Steane codes (first tier:
one thread, 600 s).  Each line ends at the last distance the method certified.

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
    metas = {m["name"]: m for m in (json.loads(p.read_text())
                                     for p in (ROOT / "bench" / "instances_lowwidth").glob("*/meta.json"))}
    methods = sorted({k[0] for k in recs} - set(T.HEURISTIC))
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, fam, title in ((axes[0], "color_cc", "triangular color codes"),
                           (axes[1], "concat_steane", "concatenated Steane codes")):
        names = sorted((m["variants"]["full"]["distance"], n) for n, m in metas.items() if m["family"] == fam)
        for meth in methods:
            pts = []
            for d, n in names:
                r = recs.get((meth, n, "full"))
                if r is not None and r.get("status") == "exact":
                    pts.append((d, max(r["seconds"], 0.01)))
            if not pts:
                continue
            label, color, marker, ls = OURS.get(meth, (meth, GRAY, "o", "-"))
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, marker=marker, linestyle=ls,
                    linewidth=1.8 if meth in OURS else 1.2, markersize=5.5, zorder=4 if meth in OURS else 2,
                    label=label if meth in OURS else None)
            if meth not in OURS:
                ax.annotate(meth, pts[-1], xytext=(4, 0), textcoords="offset points", fontsize=7, color=INK2,
                            va="center")
        ax.axhline(600, color=AXIS, linewidth=0.7)
        ax.set_yscale("log")
        ax.set_ylim(0.007, 1500)
        ax.set_xlabel("distance d", fontsize=8.5)
        ax.set_title(title, fontsize=9.5)
        ax.grid(True, which="major", color="#e1e0d9", linewidth=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("seconds to the certified distance, 1 thread", fontsize=8.5)
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
