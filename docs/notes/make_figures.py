"""Figures of docs/notes/note.md, drawn from the result records (nothing is typed in by hand except the
sizes of the BB288 problem in figure 1, which are in README.md).

Usage: .venv/bin/python docs/notes/make_figures.py                 writes docs/notes/figs/*.png
       .venv/bin/python docs/notes/make_figures.py --paper DIR     writes DIR/figs/*.pdf instead (vector, white background)
"""
import json
import os
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path as MPath

ROOT = Path(__file__).resolve().parent.parent.parent
FIGS = Path(__file__).resolve().parent / "figs"
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import summary_table as T

# palette: reference instance of the data-viz guide (light surface), used unchanged
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
BLUE_LIGHT, GRAY, GRAY_LIGHT = "#86b6ef", "#898781", "#b3b1a8"
PX = 1 / 100.0                      # one layout pixel in inches; figures are saved at 2x
PAPER = Path(sys.argv[sys.argv.index("--paper") + 1]).resolve() if "--paper" in sys.argv else None
if PAPER:                           # print: a white page, fonts embedded as TrueType
    SURFACE = "#ffffff"
    plt.rcParams.update({"pdf.fonttype": 42})

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"],
    "font.size": 9, "axes.edgecolor": AXIS, "axes.linewidth": 0.72, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def save(fig, name):
    if PAPER:
        (PAPER / "figs").mkdir(parents=True, exist_ok=True)
        out = PAPER / "figs" / (Path(name).stem + ".pdf")
        fig.savefig(out)
        plt.close(fig)
        print("wrote", out)
        return
    FIGS.mkdir(exist_ok=True)
    fig.savefig(FIGS / name, dpi=200)
    plt.close(fig)
    print("wrote", (FIGS / name).relative_to(ROOT))


def hbar(ax, y, value, thick_px=16, color=BLUE, x0=0.0):
    """Horizontal bar from the baseline x0 with a 4 px rounded data end (call after limits are set)."""
    fig = ax.figure
    fig.canvas.draw()
    inv = ax.transData.inverted()
    (ax0, ay0), (ax1, ay1) = inv.transform((0, 0)), inv.transform((fig.dpi * PX, fig.dpi * PX))
    ux, uy = ax1 - ax0, ay1 - ay0                       # data units per layout pixel
    h, rx, ry = thick_px * uy / 2, 4 * ux, 4 * uy
    if value - x0 < rx:
        rx = max(value - x0, 0)
    v = [(x0, y - h), (value - rx, y - h), (value, y - h), (value, y - h + ry), (value, y + h - ry),
         (value, y + h), (value - rx, y + h), (x0, y + h), (x0, y - h)]
    c = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3,
         MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(v, c), facecolor=color, edgecolor="none", zorder=3))


def style_axes(ax, grid="x"):
    ax.grid(axis=grid, color=GRID, linewidth=0.72, linestyle="-", zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


# ------------------------------------------------------------------------------------- data
def bench():
    a, b32, b1 = T.load(ROOT / "results" / "bench", 1), T.load(ROOT / "results" / "bench_tierB", 32), \
        T.load(ROOT / "results" / "bench_tierB", 1)
    metas = [json.loads(p.read_text()) for p in sorted((ROOT / "bench" / "instances").glob("*/meta.json"))]
    metas = [m for m in metas if m.get("family") != "fixture"]
    return a, b32, b1, metas


def exact(recs, method, inst, variant):
    r = recs.get((method, inst, variant))
    return r["seconds"] if r is not None and r.get("status") == "exact" else None


# --------------------------------------------------------------------------- figure 1: method
def fig_method():
    fig = plt.figure(figsize=(7.2, 3.9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 720)
    ax.set_ylim(0, 390)
    ax.axis("off")

    def box(x, y, w, h, title, lines, fill="#ffffff", edge=AXIS):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=6", facecolor=fill,
                                    edgecolor=edge, linewidth=0.9, zorder=2))
        ax.text(x + 10, y + h - 16, title, fontsize=9.5, color=INK, fontweight="bold", va="center")
        for i, line in enumerate(lines):
            ax.text(x + 10, y + h - 35 - 14 * i, line, fontsize=8, color=INK2, va="center")

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1,
                                                                    shrinkA=0, shrinkB=0), zorder=1)

    def note(x, y, text, ha="left"):
        ax.text(x, y, text, fontsize=7.8, color=INK2, ha=ha, va="center")

    # row 1: the three problems (sizes of the BB288 circuit, rows x columns)
    box(14, 290, 196, 86, "Circuit fault model", ["all mechanisms and detectors", "5184 × 206,352", "the problem as posed"])
    box(262, 290, 196, 86, "Memory-basis sector", ["detectors of one check type", "2736 × 26,208", "exact reduction (checked)"])
    box(510, 290, 196, 86, "Time-collapsed problem", ["detectors merged over rounds", "144 × 720", "lower bound for any rounds"],
        fill="#eef4fd", edge=BLUE_LIGHT)
    arrow(210, 333, 262, 333)
    arrow(458, 333, 510, 333)
    note(236, 345, "reduce", "center")
    note(484, 345, "relax", "center")
    # row 2: the engine
    box(262, 172, 444, 72, "Weight-bounded search, one threshold K at a time",
        ["branch on an unsatisfied detector · finish by table lookup (meet in the middle)",
         "one start per symmetry orbit · each exhausted K certifies distance > K"])
    arrow(608, 290, 608, 244)
    arrow(360, 290, 360, 244)
    note(616, 267, "always")
    note(368, 267, "if the relaxation is not tight")
    # row 3: the two ends of the interval
    box(510, 86, 196, 52, "Lower bound", ["all lighter fault sets excluded"])
    box(262, 86, 196, 52, "Upper bound", ["lifted fault set, replayed in Stim"])
    arrow(608, 172, 608, 138)
    arrow(360, 172, 360, 138)
    # row 4: the result
    box(262, 12, 444, 44, "Certified circuit distance", ["when the two bounds meet"], fill="#eef4fd", edge=BLUE_LIGHT)
    arrow(608, 86, 608, 56)
    arrow(360, 86, 360, 56)
    ax.text(112, 208, "Sizes (rows × columns) are those of\nthe [[288,12,18]] bivariate bicycle\nmemory circuit with 18 rounds.",
            fontsize=7.8, color=MUTED, ha="center", va="center", linespacing=1.4)
    save(fig, "fig1_method.png")


# ------------------------------------------------------------------- figure 2: benchmark counts
DM4RI = ["dist-m4ri CC", "dist-m4ri CC+RW", "dist-m4ri CC, DEM input", "dist-m4ri CC+RW, DEM input",
         "dist-m4ri CC, model bound", "dist-m4ri CC+RW, model bound", "dist-m4ri CC, DEM input, model bound",
         "dist-m4ri CC+RW, DEM input, model bound"]


def fig_benchmark():
    a, b32, b1, metas = bench()
    main = {m["name"]: ("full" if (m["track"] == "code" or "sector" not in m["variants"]) else "sector") for m in metas}
    # a tool counts an instance as solved with any of its configurations: dist-m4ri 0.14.7 in CC or CC+RW mode
    # (from our matrices or Stim's DEM, with or without its model lower bound), the integer-programming and SAT
    # tools with either logical basis of a code
    both = lambda name: [name, name + ", sparse L"]
    groups = [("this method", ["ours"]), ("dist-m4ri", DM4RI),
              ("CP-SAT", both("CP-SAT")), ("HiGHS", both("HiGHS")), ("Gurobi", both("Gurobi")), ("SAT (CaDiCaL)", both("SAT")),
              ("RC2", both("RC2")), ("enMaxCDCL", both("enMaxCDCL")), ("CASHWMaxSAT", both("CASHWMaxSAT")),
              ("Qubitserf (codes only)", ["Qubitserf CC", "Qubitserf BZ", "Qubitserf MITM"])]
    rows = []
    for label, ms in groups:
        t1 = sum(any(exact(a, m, i, v) is not None for m in ms) for i, v in main.items())
        t2 = sum(any(exact(r, m, i, v) is not None for r in (a, b32, b1) for m in ms) for i, v in main.items())
        rows.append((label, t1, t2))
    rows = rows[:1] + sorted(rows[1:], key=lambda r: (-r[2], -r[1]))      # the others by count
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True)
    fig.subplots_adjust(left=0.235, right=0.975, top=0.86, bottom=0.14, wspace=0.12)
    total = len(main)
    for ax, col, title in ((axes[0], 1, "1 thread, 600 s, 16 GB"), (axes[1], 2, "plus one hour (32 threads where supported)")):
        ax.set_xlim(0, total * 1.12)
        ax.set_ylim(len(rows) - 0.5, -0.5)
        ax.set_xticks([0, 20, 40, 60, total] if total - 60 > 6 else [0, 20, 40, total])
        style_axes(ax)
        ax.spines["left"].set_color(AXIS)
        ax.set_title(title, fontsize=9, color=INK, loc="left", pad=8)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([r[0] for r in rows])
        for y, r in enumerate(rows):
            hbar(ax, y, r[col], color=BLUE if y == 0 else GRAY)
            ax.text(r[col] + 1.4, y, str(r[col]), va="center", fontsize=8.5, color=INK,
                    fontweight="bold" if y == 0 else "normal")
        ax.axvline(total, color=AXIS, linewidth=0.72, zorder=1)
        ax.set_xlabel("instances solved exactly (of %d)" % total, fontsize=8.5)
    save(fig, "fig2_benchmark.png")
    return rows


# ---------------------------------------------------------------- figure 4: surface-code scaling
def fig_surface():
    a, b32, b1, metas = bench()
    # dist-m4ri: its fastest configuration at each distance (with its model lower bound from d = 9 on)
    series = [("this method", "ours", BLUE), ("dist-m4ri", DM4RI, GRAY), ("SAT", "SAT", GRAY),
              ("RC2", "RC2", GRAY), ("HiGHS", "HiGHS", GRAY), ("CP-SAT", "CP-SAT", GRAY), ("Gurobi", "Gurobi", GRAY)]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    fig.subplots_adjust(left=0.1, right=0.86, top=0.9, bottom=0.15)
    ax.set_yscale("log")
    ax.set_xlim(2.4, 26.2)
    ax.set_ylim(0.006, 1500)
    style_axes(ax, "y")
    ax.axhline(600, color=AXIS, linewidth=0.72, zorder=1)
    ax.text(26.4, 600, "600 s limit", fontsize=7.8, color=MUTED, va="center", ha="left")
    ends = {}
    for label, key, color in series:
        keys = key if isinstance(key, list) else [key]
        pts = [(d, min((t for k in keys for t in [exact(a, k, "surface_d%d" % d, "sector")] if t is not None),
                       default=None)) for d in range(3, 27, 2)]
        pts = [(d, t) for d, t in pts if t is not None]
        xs, ys = [p[0] for p in pts], [max(p[1], 0.01) for p in pts]
        ax.plot(xs, ys, color=color, linewidth=1.5 if color == GRAY else 1.8, solid_capstyle="round", solid_joinstyle="round",
                marker="o", markersize=6.2, markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4 if color == BLUE else 3)
        if xs:
            ends[label] = (xs[-1], ys[-1])
    # the same pipeline without its Rank DP evaluators (ablation of the final pass): the search alone
    abl = T.load(ROOT / "results" / "bench_ablation_final", 1)
    so = [(d, exact(abl, "ours, search only", "surface_d%d" % d, "sector")) for d in range(3, 27, 2)]
    so = [(d, max(t, 0.01)) for d, t in so if t is not None]
    if so:
        ax.plot([d for d, _ in so], [t for _, t in so], color=AQUA, linewidth=1.8, linestyle=(0, (4, 2)),
                marker="s", markersize=5.6, markeredgecolor=SURFACE, markeredgewidth=1.3, zorder=5)
        ax.text(so[-1][0] + 0.45, so[-1][1], "without the\nRank DP evaluators", fontsize=7.8, color=INK2,
                ha="left", va="center", linespacing=1.3)
    # second tier of this method (32 threads, one hour) where its first tier did not solve the circuit
    t2 = [(d, exact(b32, "ours", "surface_d%d" % d, "sector")) for d in range(3, 27, 2)
          if exact(a, "ours", "surface_d%d" % d, "sector") is None]
    t2 = [(d, t) for d, t in t2 if t is not None]
    if t2:
        ax.plot([d for d, _ in t2], [t for _, t in t2], color=BLUE, linewidth=0, marker="o", markersize=6.2,
                markerfacecolor=SURFACE, markeredgecolor=BLUE, markeredgewidth=1.5, zorder=4)
    if "this method" in ends:
        x, y = ends["this method"]
        ax.text(x + 0.45, y, "this method", fontsize=8.5, color=INK, fontweight="bold", ha="left", va="center")
    # labels at the end of each line; SAT and Gurobi end at the same point, so they share a label
    shared = "SAT" in ends and "Gurobi" in ends and ends["SAT"][0] == ends["Gurobi"][0] and \
        0.7 < ends["SAT"][1] / ends["Gurobi"][1] < 1.4
    for label, (dx, ha) in {"dist-m4ri": (0.45, "left"), "SAT": (0.45, "left"), "RC2": (0.45, "left"),
                            "HiGHS": (0.45, "left"), "CP-SAT": (-0.45, "right"), "Gurobi": (0.45, "left")}.items():
        if label not in ends or (shared and label == "Gurobi"):
            continue
        x, y = ends[label]
        ax.text(x + dx, y, "SAT, Gurobi" if (shared and label == "SAT") else label, fontsize=8.2, color=INK2,
                va="center", ha=ha)
    ax.set_xticks(range(3, 27, 2))
    ax.set_yticks([0.01, 0.1, 1, 10, 100, 1000])
    ax.set_yticklabels(["≤ 0.01", "0.1", "1", "10", "100", "1000"])
    ax.set_xlabel("distance d of the rotated surface-code memory circuit (d rounds)", fontsize=8.5)
    ax.set_ylabel("seconds to the certified distance, 1 thread", fontsize=8.5)
    ax.spines["left"].set_visible(False)
    ax.minorticks_off()
    save(fig, "fig4_surface.png")


# ---------------------------------------------------------------------- figure 5: ablation
def fig_ablation():
    a, b32, b1, metas = bench()
    abl = T.load(ROOT / "results" / "bench_ablation_final", 1)     # relative to the final configuration (dp=2)
    circ = [m["name"] for m in metas if m["track"] == "circuit" and "sector" in m["variants"]]
    count = lambda recs, name: sum(exact(recs, name, i, "sector") is not None for i in circ)
    rows = [("full pipeline", count(a, "ours")),
            ("without the sparse DP", count(abl, "ours + DP")),
            ("without either DP", count(abl, "ours, search only")),
            ("without lifting", count(abl, "ours, lift off")),
            ("without covering bound", count(abl, "ours, cover off")),
            ("without windows", count(abl, "ours, window off")),
            ("without symmetry", count(abl, "ours, symmetry off")),
            ("without time collapse", count(abl, "ours, collapse off")),
            ("search only (no collapse, lifting, windows)", count(abl, "ours, collapse off lift off window off")),
            ("search only, no symmetry, no covering bound", count(abl, "ours, symmetry off cover off collapse off lift off window off"))]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    fig.subplots_adjust(left=0.43, right=0.96, top=0.95, bottom=0.15)
    ax.set_xlim(0, len(circ) + 3)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    style_axes(ax)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    for y, (label, v) in enumerate(rows):
        hbar(ax, y, v, color=BLUE if y == 0 else GRAY)
        ax.text(v + 0.9, y, str(v), va="center", fontsize=8.5, color=INK, fontweight="bold" if y == 0 else "normal")
    ax.axvline(len(circ), color=AXIS, linewidth=0.72, zorder=1)
    ax.set_xticks([0, 10, 20, 30, len(circ)])
    ax.set_xlabel("circuits solved exactly (of %d), 1 thread, 600 s" % len(circ), fontsize=8.5)
    save(fig, "fig5_ablation.png")
    return rows


# -------------------------------------------------------- figure 6: the open ranges of 2610.03682
def fig_ranges():
    import summarize_hyperbolic as S
    res = S.load_results()
    rows = []
    for name, label, stated in S.ROWS:
        if "–" not in stated or name not in res or res[name].get("d") is None:
            continue
        lo, hi = map(int, stated.split("–"))
        r = res[name]
        L = int(name.rsplit("_L", 1)[1])
        short = re.sub(r" \(our entry \d+\)", "", label).replace(", class 1", "")
        rows.append((r["d"], r["n"], "[[%d, %d]]   %s, L = %d" % (r["n"], r["k"], short, L), lo, hi))
    rows.sort(key=lambda t: (t[0], t[1]))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    fig.subplots_adjust(left=0.5, right=0.97, top=0.9, bottom=0.12)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xlim(4, 30)
    style_axes(ax)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[2] for r in rows], fontsize=8)
    for y, (d, n, label, lo, hi) in enumerate(rows):
        ax.plot([lo, hi], [y, y], color=GRAY_LIGHT, linewidth=5, solid_capstyle="round", zorder=2)
        ax.plot([d], [y], marker="o", markersize=7, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)
    ax.plot([], [], color=GRAY_LIGHT, linewidth=5, solid_capstyle="round", label="range certified in the paper")
    ax.plot([], [], marker="o", markersize=7, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=1.5, linewidth=0,
            label="exact distance (this method)")
    ax.legend(loc="lower left", bbox_to_anchor=(-1.0, 1.0), ncol=2, fontsize=8.2, handlelength=1.6, columnspacing=1.6,
              borderaxespad=0.2)
    ax.set_xticks(range(4, 31, 4))
    ax.set_xlabel("code distance", fontsize=8.5)
    save(fig, "fig6_ranges.png")
    return rows


# -------------------------------------------------------- figure 7: cost per unit of weight
def fig_growth():
    runs = {}
    for tag, name, label in (("D", "lins444_96_L4", "[[5376, 88, 28]]"), ("F", "lins566_130_L4", "[[23040, 676, 28]]"),
                             ("F", "psl25_444_c1_L2", "[[31200, 1954, 24]]")):
        data = json.load(open(ROOT / "results" / "papers4" / "hyperbolic" / ("server_%s.json" % tag)))
        r = next(c for c in data["codes"] if c["name"] == name)["distance"]["Z"]
        pts = [(x["K"], x["seconds"]) for x in r["runs"] if x["status"] == "exhausted" and x.get("seconds", 0) >= 1]
        runs[label] = pts
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    fig.subplots_adjust(left=0.1, right=0.8, top=0.93, bottom=0.17)
    ax.set_yscale("log")
    style_axes(ax, "y")
    for (label, pts), color in zip(runs.items(), (BLUE, ORANGE, AQUA)):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(xs, ys, color=color, linewidth=1.5, marker="o", markersize=6.2, markeredgecolor=SURFACE,
                markeredgewidth=1.5, label=label, solid_capstyle="round", zorder=3)
        if xs[-1] >= 27:
            ax.text(xs[-1] + 0.25, ys[-1], label, fontsize=8.2, color=INK2, va="center", ha="left")
        else:
            ax.text(xs[-1] - 0.2, ys[-1] * 1.55, label, fontsize=8.2, color=INK2, va="center", ha="right")
    ax.set_xlim(right=ax.get_xlim()[1] + 0.2)
    ax.set_yticks([1, 10, 100, 1000])
    ax.set_yticklabels(["1", "10", "100", "1000"])
    ax.set_ylim(1, 9000)
    ax.set_xticks(range(int(min(p[0] for v in runs.values() for p in v)), 28))
    ax.set_xlabel("weight threshold K (all fault sets of weight ≤ K excluded)", fontsize=8.5)
    ax.set_ylabel("seconds for threshold K, 32 threads", fontsize=8.5)
    ax.spines["left"].set_visible(False)
    ax.legend(loc="upper left", fontsize=8.2, handlelength=1.6)
    ax.minorticks_off()
    save(fig, "fig7_growth.png")
    return runs


# ------------------------------------------- figure 3: the instances of arXiv:2603.22532
def fig_wjh():
    """Both sides under the paper's limits: our single-thread time (600 s tier, else the 8-hour run; 8 GB)
    against the fastest exact method of the paper (1 core, 8 h, 8 GB on their cluster), one point per
    instance; instances only one side solved within 8 h sit in the margins."""
    import wjh_compare as W
    rows = W.per_instance()
    NONE, FLOOR = 2.5e5, 0.01
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    fig.subplots_adjust(left=0.13, right=0.97, top=0.89, bottom=0.13)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.006, 6e5)
    ax.set_ylim(0.006, 6e5)
    style_axes(ax, "both")
    ax.plot([0.006, 28800], [0.006, 28800], color=AXIS, linewidth=0.9, zorder=1)
    ax.text(900, 2600, "equal time", fontsize=7.8, color=MUTED, rotation=33, ha="center", va="center")
    ax.axvline(28800 * 1.9, color=AXIS, linewidth=0.72, zorder=1)
    ax.axhline(28800 * 1.9, color=AXIS, linewidth=0.72, zorder=1)
    counts = {}
    for track, color, label in (("circuit", BLUE, "circuits"), ("code", ORANGE, "codes")):
        xs, ys = [], []
        for r in rows:
            if r["track"] != track:
                continue
            o, t = r["ours_8h"], r["theirs"]
            key = (o is not None, t is not None)
            counts[key] = counts.get(key, 0) + 1
            if o is None and t is None:
                continue
            xs.append(max(t[0], FLOOR) if t else NONE)
            ys.append(max(o, FLOOR) if o is not None else NONE)
        ax.plot(xs, ys, linewidth=0, marker="o", markersize=6.2, color=color, markeredgecolor=SURFACE,
                markeredgewidth=1.5, label=label, zorder=3, alpha=0.95)
    only = sum(v for (o, t), v in counts.items() if o and not t)
    ax.text(NONE, 0.03, "%d solved by\nthis method only" % only, fontsize=7.8, color=INK2, ha="center", va="center",
            linespacing=1.3)
    ticks = [0.01, 1, 100, 10000, NONE]
    ax.set_xticks(ticks)
    ax.set_xticklabels(["≤ 0.01", "1", "100", "10000", "not solved\nin 8 h"])
    ax.set_yticks(ticks)
    ax.set_yticklabels(["≤ 0.01", "1", "100", "10000", "not solved\nin 8 h"])
    ax.minorticks_off()
    ax.set_xlabel("fastest exact method of arXiv:2603.22532 (seconds; 1 core, 8 h, 8 GB, their cluster)", fontsize=8.5)
    ax.set_ylabel("this method (seconds; 1 thread, 8 h, 8 GB)", fontsize=8.5)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, fontsize=8.2, handlelength=1.2, borderaxespad=0.3)
    save(fig, "fig3_prior.png")
    return counts


if __name__ == "__main__":
    fig_method()
    print(fig_benchmark())
    fig_surface()
    print(fig_ablation())
    print([(r[2], r[3], r[4], r[0]) for r in fig_ranges()])
    print({k: [(K, round(s)) for K, s in v] for k, v in fig_growth().items()})
    print(fig_wjh())
