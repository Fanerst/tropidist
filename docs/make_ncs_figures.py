"""Figures of the Nature Computational Science manuscript (circuit_distance_paper/ncs.tex), drawn from the records.

Usage: .venv/bin/python docs/make_ncs_figures.py OUTDIR [1 2 3 4 table]   writes OUTDIR/ncs_fig{1..4}.pdf with .png
previews, and OUTDIR/si_audit_table.tex (the Supplementary table of audited values)

Figure 1 is a schematic laid out in millimetres; its panel d is the bound trace of a real run. Figures 2 to 4 combine
several panels each. The audit values are in docs/audit_items.csv, collected from docs/AUDIT.md; everything else is
read from the result records.
"""
import csv
import glob
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Polygon
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "bench"), str(ROOT)]
import make_figures as MF          # palette, data loaders
import summary_table as T

WHITE = "#ffffff"
BLUE, BLUE_LIGHT, ORANGE, AQUA = MF.BLUE, MF.BLUE_LIGHT, MF.ORANGE, MF.AQUA
INK, INK2, MUTED, GRID, AXIS, GRAY, GRAY_LIGHT = MF.INK, MF.INK2, MF.MUTED, MF.GRID, MF.AXIS, MF.GRAY, MF.GRAY_LIGHT
ORANGE_PALE, AQUA_PALE, BLUE_PALE, GRAY_PALE, PANEL = "#fbe1d6", "#d6f0e5", "#e3eefb", "#efeee9", "#f6f6f3"
MM = 1 / 25.4

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"], "font.size": 6,
    "axes.titlesize": 6.5, "axes.labelsize": 6, "xtick.labelsize": 5.6, "ytick.labelsize": 5.6, "legend.fontsize": 5.6,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.55, "axes.labelcolor": INK2, "xtick.color": AXIS, "ytick.color": AXIS,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "figure.facecolor": WHITE, "axes.facecolor": WHITE,
    "savefig.facecolor": WHITE, "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "pdf.fonttype": 42, "xtick.major.size": 1.8, "ytick.major.size": 1.8, "xtick.major.width": 0.55,
    "ytick.major.width": 0.55, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5, "axes.labelpad": 2.0,
    "mathtext.fontset": "custom", "mathtext.rm": "Arial", "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold",
    "mathtext.sf": "Arial", "lines.solid_capstyle": "round",
})
OUT = None


# ------------------------------------------------------------------------------------------- helpers
def save(fig, name):
    fig.savefig(OUT / (name + ".pdf"))
    fig.savefig(OUT / (name + ".png"), dpi=300)
    plt.close(fig)
    print("wrote", OUT / (name + ".pdf"))


def canvas(W, H):
    """A figure of W x H millimetres with one invisible axes in millimetre coordinates."""
    fig = plt.figure(figsize=(W * MM, H * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    fig.mm = (W, H)
    return fig, ax


def axes_mm(fig, x, y, w, h):
    W, H = fig.mm
    return fig.add_axes([x / W, y / H, w / W, h / H])


def panel(ax, x, y, s, t=None):
    ax.text(x, y, s, fontsize=8, fontweight="bold", color=INK, ha="left", va="baseline")
    if t:
        ax.text(x + 3.6, y, t, fontsize=6.8, fontweight="bold", color=INK, ha="left", va="baseline")


def txt(ax, x, y, s, size=6.0, color=INK2, ha="left", va="center", **kw):
    return ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, **kw)


def rbox(ax, x, y, w, h, fc=WHITE, ec="none", lw=0.7, r=1.2, z=1, alpha=1.0):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=%g" % r, facecolor=fc, edgecolor=ec,
                       linewidth=lw, zorder=z, alpha=alpha)
    ax.add_patch(p)
    return p


def arrow(ax, x0, y0, x1, y1, color=INK2, lw=0.7, rad=0.0, z=3, ms=5.5, ls="-", style="-|>"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=ms, color=color, linewidth=lw,
                                 connectionstyle="arc3,rad=%g" % rad, zorder=z, linestyle=ls, shrinkA=0, shrinkB=0,
                                 capstyle="round", joinstyle="round"))


def star(ax, x, y, r, color, z=6):
    pts = [(x + (r if k % 2 == 0 else 0.45 * r) * math.cos(math.pi / 2 + k * math.pi / 5),
            y + (r if k % 2 == 0 else 0.45 * r) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor=WHITE, lw=0.4, zorder=z))


def tidy(ax, grid="y"):
    ax.tick_params(length=0)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.45, zorder=0)
    ax.set_axisbelow(True)


def DM4RI():
    return ["dist-m4ri CC", "dist-m4ri CC+RW", "dist-m4ri CC, DEM input", "dist-m4ri CC+RW, DEM input",
            "dist-m4ri CC, model bound", "dist-m4ri CC+RW, model bound", "dist-m4ri CC, DEM input, model bound",
            "dist-m4ri CC+RW, DEM input, model bound"]


# =============================================================================================== figure 1
def layer(x, yc, count, spread):
    return [(x, yc + ((count - 1) / 2 - i) * spread) for i in range(count)]


def links(c1, c2):
    """Trellis transitions between layers of c1 and c2 states: each state has two successors, or merges."""
    if c2 >= c1:
        return {i: sorted({(2 * i) % c2, (2 * i + 1) % c2}) for i in range(c1)}
    return {i: [i // (c1 // c2)] for i in range(c1)}


def trellis(ax, xs, yc, counts, color, light, spread=2.9, r=0.78, keep=None, path=None, mirror=False):
    """Draw a small trellis; keep[L] masks the states that survive (others are drawn faded), path is highlighted.
    Returns the node positions per layer."""
    pos = [layer(x, yc, c, spread) for x, c in zip(xs, counts)]
    keep = keep or [[1] * c for c in counts]
    order = range(len(counts) - 1)
    for L in order:
        a, b = (L, L + 1) if not mirror else (L + 1, L)
        for i, js in links(counts[a], counts[b]).items():
            for j in js:
                if keep[a][i] and keep[b][j]:
                    on = path is not None and path[a] == i and path[b] == j
                    ax.plot([pos[a][i][0], pos[b][j][0]], [pos[a][i][1], pos[b][j][1]], color=color if on else GRAY_LIGHT,
                            lw=1.25 if on else 0.45, zorder=4 if on else 2, solid_capstyle="round")
    for L, nodes in enumerate(pos):
        for i, (x, y) in enumerate(nodes):
            if not keep[L][i]:
                ax.add_patch(Circle((x, y), r * 0.75, facecolor=WHITE, edgecolor=GRAY_LIGHT, lw=0.45, zorder=3,
                                    linestyle=(0, (1.2, 0.8))))
                continue
            on = path is not None and path[L] == i
            ax.add_patch(Circle((x, y), r, facecolor=color if on else light, edgecolor=color, lw=0.55, zorder=5))
    return pos


def fig_schematic():
    W, H = 183, 130
    fig, ax0 = canvas(W, H)

    def shifted(dy):
        """An invisible axes in the millimetre coordinates of the original 118-mm layout, raised by dy mm."""
        a = fig.add_axes([0, 0, 1, 1])
        a.set_xlim(0, W)
        a.set_ylim(-dy, H - dy)
        a.axis("off")
        return a
    # top row; the circuit and error model of panel a, 3 mm lower; bottom row (7 mm of room below its cards for
    # the axis labels of panel d, whose plot spans the cards and the formula box)
    axT, axA, axL = shifted(12.0), shifted(9.0), shifted(7.0)

    # ------------------------------------------------------------------ a: a circuit, its error model, the problem
    ax = axT
    panel(ax, 1.5, 114.4, "a", "Faults in a circuit and the distance problem")
    ax = axA
    anc, data = 105.0, [99.6, 94.6, 89.6, 84.6]
    xl, xr = 15.0, 46.5
    txt(ax, xl - 1.4, anc, "ancilla", 5.5, MUTED, ha="right")
    ax.plot([xl, 40.5], [anc, anc], color=INK2, lw=0.75, zorder=1)
    for y in data:
        txt(ax, xl - 1.4, y, "data", 5.5, MUTED, ha="right")
        ax.plot([xl, xr], [y, y], color=INK2, lw=0.75, zorder=1)
    gates = [19.5, 25.5, 31.5, 37.5]
    for g, y in zip(gates[2:], data[2:]):                       # the hook: the fault spreads to later data qubits
        ax.plot([g, xr], [y, y], color=ORANGE, lw=2.6, alpha=0.88, solid_capstyle="round", zorder=2)
    for g, y in zip(gates, data):
        ax.plot([g, g], [anc, y - 1.3], color=INK2, lw=0.75, zorder=3)
        ax.add_patch(Circle((g, anc), 0.75, color=INK2, zorder=4))
        ax.add_patch(Circle((g, y), 1.3, facecolor=WHITE, edgecolor=INK2, lw=0.75, zorder=4))
        ax.plot([g - 1.3, g + 1.3], [y, y], color=INK2, lw=0.75, zorder=5)
        ax.plot([g, g], [y - 1.3, y + 1.3], color=INK2, lw=0.75, zorder=5)
    rbox(ax, 40.5, anc - 2.0, 5.0, 4.0, fc=WHITE, ec=INK2, lw=0.75, r=0.6, z=4)
    ax.add_patch(matplotlib.patches.Arc((43.0, anc - 0.9), 3.2, 3.0, theta1=20, theta2=160, color=INK2, lw=0.6,
                                        zorder=5))
    ax.plot([43.0, 44.2], [anc - 0.9, anc + 0.9], color=INK2, lw=0.6, zorder=5)
    star(ax, 28.5, anc, 1.85, ORANGE)
    txt(ax, 28.5, anc + 2.6, "one fault", 5.7, ORANGE, ha="center", va="bottom", fontweight="bold")
    txt(ax, 42.0, 81.6, "hook: two data errors", 5.5, ORANGE, ha="center", va="center")
    arrow(ax, 47.6, 102.0, 53.0, 102.0, color=INK2, lw=0.7)

    # the detector error model: a fault set whose columns sum to zero on D and to one on O
    cols = [({0}, 0), ({0, 1}, 0), ({4, 5}, 0), ({2, 4}, 0), ({1, 2}, 1), ({5}, 1),
            ({0, 4}, 0), ({2, 3}, 0), ({3, 5}, 0), ({1}, 1), ({0, 3}, 0), ({4}, 0)]
    pick = [1, 4, 7, 10]
    x0, pc, cs, yt, nd = 56.0, 2.3, 1.9, 106.4, 6
    yO = yt - nd * pc - 1.0 - pc
    txt(ax, x0, 110.0, "detector error model", 6.0, INK2, va="baseline", fontweight="bold")
    for c in pick:
        rbox(ax, x0 + c * pc - 0.35, yO - 0.45, cs + 0.7, yt - yO + 0.6, fc=ORANGE_PALE, r=0.5, z=1)
    for c, (dets, obs) in enumerate(cols):
        for r in range(nd + 1):
            on = (r in dets) if r < nd else bool(obs)
            y = yt - (r + 1) * pc if r < nd else yO
            fc = (ORANGE if c in pick else INK2) if on else (WHITE if c in pick else GRAY_PALE)
            ax.add_patch(Rectangle((x0 + c * pc, y + (pc - cs) / 2), cs, cs, facecolor=fc, edgecolor="none", zorder=2))
    xs = x0 + len(cols) * pc + 1.2
    for r in range(nd + 1):
        par = (sum(r in cols[c][0] for c in pick) if r < nd else sum(cols[c][1] for c in pick)) % 2
        y = (yt - (r + 1) * pc if r < nd else yO) + (pc - cs) / 2
        ax.add_patch(Rectangle((xs, y), cs, cs, facecolor=ORANGE if par else WHITE, edgecolor=ORANGE if par else AXIS,
                               lw=0.45, zorder=2))
        txt(ax, xs + cs / 2, y + cs / 2, str(par), 4.8, WHITE if par else MUTED, ha="center", fontweight="bold")
    txt(ax, xs + cs / 2, yt + 1.3, "sum", 5.0, MUTED, ha="center", va="bottom")
    txt(ax, x0 - 1.2, yt - nd * pc / 2, r"$\mathbf{D}$", 6.6, INK, ha="right")
    txt(ax, x0 - 1.2, yO + pc / 2, r"$\mathbf{O}$", 6.6, INK, ha="right")
    ye = yO - 2.6
    txt(ax, x0 - 1.2, ye, r"$e$", 6.6, INK, ha="right")
    for c in range(len(cols)):
        on = c in pick
        ax.add_patch(Circle((x0 + c * pc + cs / 2, ye), 0.62, facecolor=ORANGE if on else WHITE,
                            edgecolor=ORANGE if on else AXIS, lw=0.5, zorder=3))
    txt(ax, xs + cs / 2 + 1.3, ye, r"$|e|{=}4$", 5.4, ORANGE, ha="center")
    txt(ax, x0, ye - 2.7, "columns: fault mechanisms", 5.0, MUTED, va="center")

    # the two distance problems
    ax = axT
    rbox(ax, 2.5, 58.5, 85.5, 15.6, fc=PANEL, r=1.6, z=0)
    txt(ax, 5.0, 69.9, "circuit distance", 6.0, INK, fontweight="bold")
    txt(ax, 26.5, 69.9, r"$d_{\mathrm{circ}}=\min\,\{\,|e|\;:\;\mathbf{D}e=0,\ \mathbf{O}e\neq0\,\}$", 6.8, INK)
    txt(ax, 69.0, 69.9, "D detectors\nO logical observables", 4.9, MUTED, linespacing=1.15)
    txt(ax, 5.0, 62.7, "code distance", 6.0, INK, fontweight="bold")
    txt(ax, 26.5, 62.7, r"$d=\min\,\{\,|e|\;:\;\mathbf{H}e=0,\ \mathbf{L}e\neq0\,\}$", 6.8, INK)
    txt(ax, 69.0, 62.7, "H checks\nL logical operators", 4.9, MUTED, linespacing=1.15)

    # ------------------------------------------------------------------ b: reductions
    ax = axT
    panel(ax, 92.5, 114.4, "b", "Exact reduction, certified relaxation and lifting")
    txt(ax, 96.1, 109.9, "IBM's [[288,12,18]] memory circuit, 18 rounds", 5.4, MUTED, va="baseline")
    rng = np.random.default_rng(7)

    def band(x, y, w, h, nb, bw, bh, n, colors, fc, dot=1.1):
        rbox(ax, x, y, w, h, fc=fc, r=1.0, z=1)
        dx, dy = (w - bw - 1.4) / (nb - 1), (h - bh - 1.4) / (nb - 1)
        for i in range(nb):
            bx, by = x + 0.7 + i * dx, y + h - 0.7 - bh - i * dy
            ax.add_patch(Rectangle((bx, by), bw, bh, facecolor=WHITE, edgecolor="none", alpha=0.65, zorder=2))
            for part, (col, frac) in enumerate(colors):
                m = int(n * frac)
                lo = by + bh * (1 - sum(f for _, f in colors[:part + 1]))
                hi = lo + bh * frac
                ax.scatter(bx + 0.25 + rng.random(m) * (bw - 0.5), lo + 0.2 + rng.random(m) * (hi - lo - 0.4),
                           s=dot, color=col, linewidths=0, zorder=3)

    yb = 72.5                                              # larger drawings over the full width of the column
    band(93.5, yb, 35.0, 31.0, 7, 10.4, 8.7, 34, [(BLUE, 0.5), (GRAY, 0.5)], GRAY_PALE)
    band(137.5, yb, 21.0, 18.0, 7, 6.5, 5.2, 14, [(BLUE, 1.0)], BLUE_PALE, dot=0.95)
    rbox(ax, 165.0, yb, 12.0, 10.0, fc=AQUA_PALE, r=1.0, z=1)
    ax.scatter(165.6 + rng.random(52) * 10.8, yb + 0.6 + rng.random(52) * 8.8, s=0.95, color=AQUA, linewidths=0,
               zorder=3)
    for xc, name, dims, note, ncol in ((111.0, "full error model", "5,184 × 206,352", None, None),
                                      (148.0, "one memory basis", "2,736 × 26,208", "same distance", BLUE),
                                      (171.0, "collapsed over rounds", "144 × 720", "lower bound", AQUA)):
        txt(ax, xc, yb - 2.6, name, 5.8, INK2, ha="center")
        txt(ax, xc, yb - 5.4, dims, 5.3, MUTED, ha="center")
        if note:
            txt(ax, xc, yb - 8.2, note, 5.4, ncol, ha="center", fontweight="bold")
    txt(ax, 111.0, yb - 8.2, "X and Z detectors, all rounds", 5.0, MUTED, ha="center")
    arrow(ax, 129.6, yb + 14.0, 136.6, yb + 14.0)
    txt(ax, 133.1, yb + 15.8, "exact", 5.6, INK2, ha="center", va="bottom", fontweight="bold")
    txt(ax, 133.1, yb + 12.3, "verified", 4.9, MUTED, ha="center", va="top")
    arrow(ax, 159.3, yb + 5.0, 164.3, yb + 5.0)
    txt(ax, 161.8, yb + 6.8, "relax", 5.6, INK2, ha="center", va="bottom", fontweight="bold")
    arrow(ax, 171.0, yb + 10.6, 151.0, yb + 18.9, color=BLUE, lw=0.85, rad=0.5)
    txt(ax, 166.0, yb + 23.6, "lift: circuit fault sets\nof the same weight", 5.3, BLUE, ha="center", va="bottom",
        linespacing=1.1)
    txt(ax, 93.5, yb - 12.7, "The collapsed distance bounds the circuit distance from below for any number of rounds;\n"
        "when a minimum of the collapsed problem lifts, the bound is attained.", 5.2, INK2, va="center",
        linespacing=1.25)

    # ------------------------------------------------------------------ c: three evaluators
    ax = axL
    panel(ax, 1.5, 54.0, "c", "One tropical partition function, three exact evaluators")
    CW = 28.0                                              # card width; the cards fill the left column, under a
    k_ = CW / 34.0                                         # horizontal scale of the drawings inside a card
    rbox(ax, 2.0, 42.2, 56.0, 7.2, fc=WHITE, ec=INK2, lw=0.7, r=1.6, z=2)
    txt(ax, 30.0, 45.8, r"$Z_{\mathbf{M}}(t)\;=\;\min\,\{\,|e|\;:\;\mathbf{M}e=t\,\}$", 7.4, INK, ha="center")
    rbox(ax, 61.0, 42.2, CW, 7.2, fc=PANEL, r=1.6, z=2)
    txt(ax, 61.0 + CW / 2, 45.8, "a cost model runs\nthe cheapest", 5.4, INK2, ha="center", linespacing=1.15)
    cards = [(2.0, AQUA, AQUA_PALE, "dense Rank DP"), (31.5, ORANGE, ORANGE_PALE, "truncated Rank DP"),
             (61.0, BLUE, BLUE_PALE, "weight-bounded search")]
    for x0, col, pale, name in cards:
        arrow(ax, 30.0, 42.0, x0 + CW / 2, 38.4, color=col, lw=0.75, ms=5)
        rbox(ax, x0, 2.0, CW, 36.0, fc=WHITE, ec=col, lw=0.85, r=1.5, z=1)
        rbox(ax, x0, 32.5, CW, 5.5, fc=col, r=1.5, z=2)
        ax.add_patch(Rectangle((x0, 32.5), CW, 2.5, facecolor=col, edgecolor="none", zorder=2))
        txt(ax, x0 + CW / 2, 35.3, name, 5.8, WHITE, ha="center", fontweight="bold")
    # dense: the whole trellis
    x0 = 2.0
    txt(ax, x0 + CW / 2, 29.7, r"$2^{w}$ states at a cut of rank $w$", 5.0, MUTED, ha="center")
    trellis(ax, np.linspace(x0 + 3.6, x0 + CW - 3.6, 6), 20.8, [1, 2, 4, 4, 2, 1], AQUA, AQUA_PALE,
            spread=2.6, r=0.7, path=[0, 1, 2, 1, 0, 0])
    txt(ax, x0 + CW / 2, 8.0, r"cost $\approx\sum\,2^{w}$ over the cuts,", 5.2, INK2, ha="center")
    txt(ax, x0 + CW / 2, 4.7, "independent of the distance", 5.2, INK2, ha="center")
    # truncated: light states only, forward and backward, joined at a cut
    x0 = 31.5
    txt(ax, x0 + 7.2, 29.7, r"forward, $\leq T_{\mathrm{f}}$", 4.9, MUTED, ha="center")
    txt(ax, x0 + 20.8, 29.7, r"backward, $\leq T_{\mathrm{b}}$", 4.9, MUTED, ha="center")
    pf = trellis(ax, np.linspace(x0 + 2.9, x0 + 11.5, 4), 20.8, [1, 2, 4, 4], ORANGE, ORANGE_PALE,
                 spread=2.6, r=0.7, keep=[[1], [1, 1], [1, 1, 1, 0], [1, 0, 1, 1]], path=[0, 0, 1, 3])
    pb = trellis(ax, np.linspace(x0 + 16.5, x0 + 25.1, 4), 20.8, [4, 4, 2, 1], ORANGE, ORANGE_PALE,
                 spread=2.6, r=0.7, keep=[[1, 1, 0, 1], [0, 1, 1, 1], [1, 1], [1]], path=[3, 3, 1, 0], mirror=True)
    ax.plot([x0 + CW / 2, x0 + CW / 2], [14.0, 27.6], color=INK2, lw=0.55, ls=(0, (2, 1.4)), zorder=1)
    for i in (0, 3):
        on = i == 3
        ax.plot([pf[-1][i][0], pb[0][i][0]], [pf[-1][i][1], pb[0][i][1]], color=ORANGE if on else GRAY_LIGHT,
                lw=1.25 if on else 0.5, ls="-" if on else (0, (1.5, 1)), zorder=4)
    txt(ax, x0 + CW / 2, 12.6, "join", 4.9, MUTED, ha="center")
    txt(ax, x0 + CW / 2, 8.0, "keeps only light states;", 5.2, INK2, ha="center")
    txt(ax, x0 + CW / 2, 4.7, "cost set by their number", 5.2, INK2, ha="center")
    # search: canonical branching, pruning, completion by lookup
    x0 = 61.0
    txt(ax, x0 + CW / 2, 29.7, r"a solution of weight $\leq K$?", 4.9, MUTED, ha="center")
    root = (x0 + CW / 2, 25.8)
    l1 = [(x0 + 8.0 * k_, 21.7), (x0 + 17.0 * k_, 21.7), (x0 + 26.0 * k_, 21.7)]
    l2 = [(x0 + v * k_, 17.6) for v in (4.8, 11.2, 14.6, 19.4, 22.8, 29.2)]
    par = [0, 0, 1, 1, 2, 2]
    pruned = {1, 5}
    for p in l1:
        ax.plot([root[0], p[0]], [root[1], p[1]], color=BLUE, lw=0.6, zorder=2)
    for k, (p, q) in enumerate(zip(l2, par)):
        ax.plot([l1[q][0], p[0]], [l1[q][1], p[1]], color=GRAY_LIGHT if k in pruned else BLUE, lw=0.6, zorder=2)
    for k, p in enumerate([root] + l1 + l2):
        faded = k - 4 in pruned
        ax.add_patch(Circle(p, 0.7, facecolor=WHITE if faded else BLUE_PALE, edgecolor=GRAY_LIGHT if faded else BLUE,
                            lw=0.55, zorder=4))
    for k in pruned:
        txt(ax, l2[k][0], l2[k][1], "×", 5.6, ORANGE, ha="center", fontweight="bold", zorder=6)
    tx, ty, cw, ch = x0 + 7.0, 11.2, 1.5, 1.1
    for i in range(6):
        for j in range(2):
            ax.add_patch(Rectangle((tx + i * cw, ty + j * ch), cw * 0.86, ch * 0.8, facecolor=BLUE_PALE if (i + j) % 3
                                   else BLUE_LIGHT, edgecolor="none", zorder=3))
    for k, p in enumerate(l2):
        if k not in pruned:
            ax.plot([p[0], tx + 0.8 + (k * 1.75)], [p[1] - 0.75, ty + 2 * ch], color=BLUE, lw=0.45, alpha=0.6,
                    ls=(0, (1.6, 1.0)), zorder=2)
    txt(ax, tx + 6 * cw + 0.7, ty + ch, "lookup", 4.9, MUTED, ha="left")
    txt(ax, x0 + CW - 0.7, 27.3, "× pruned by a\ncovering bound", 4.3, ORANGE, ha="right", va="center", linespacing=1.1)
    txt(ax, x0 + CW / 2, 8.0, r"$K=1,2,\ldots$ excluded in turn;", 5.2, INK2, ha="center")
    txt(ax, x0 + CW / 2, 4.7, "cost set by d and symmetry", 5.2, INK2, ha="center")

    # ------------------------------------------------------------------ d: certificate of a real run
    panel(ax, 92.5, 54.0, "d", "A certificate: the bounds meet")
    axd = axes_mm(fig, 104.5, 9.0, 76.0, 47.4)                    # from the cards' bottom to the formula's top
    rec = json.load(open(ROOT / "results/bench_tierB/ours_pipeline__dp-2/bb288_r18__sector__t32.json"))
    lbs = [(e["t"], e["lb"]) for e in rec["trace"] if "lb" in e]
    tu, vu = [(e["t"], e["ub"]) for e in rec["trace"] if "ub" in e][-1]
    t_end = 700.0
    xs = [t for t, _ in lbs] + [t_end]
    ys = [v for _, v in lbs] + [lbs[-1][1]]
    axd.fill_between(xs, 0, ys, step="post", color=BLUE, alpha=0.10, linewidth=0, zorder=1)
    axd.step(xs, ys, where="post", color=BLUE, lw=1.3, zorder=3)
    axd.axhline(18, color=GRAY, lw=0.7, ls=(0, (3, 2)), zorder=2)
    txt(axd, 0.115, 18.45, "published upper bound, 18", 5.2, MUTED, va="bottom")
    axd.plot([tu, t_end], [vu, vu], color=ORANGE, lw=1.3, zorder=4)
    axd.plot([tu], [vu], marker="o", ms=4.2, color=ORANGE, markeredgecolor=WHITE, markeredgewidth=0.7, zorder=5)
    txt(axd, 3.4, 4.6, "proved lower bound:\nno lighter fault set exists", 5.2, BLUE, ha="left", linespacing=1.15)
    axd.annotate("fault set of weight 16,\nreplayed in Stim", (tu * 0.93, vu - 0.4), xytext=(150, 9.4),
                 fontsize=5.2, color=ORANGE, ha="right", va="center", linespacing=1.15,
                 arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.5, shrinkA=1, shrinkB=1.5))
    txt(axd, t_end * 0.9, 16.75, "certified 16", 5.6, INK, ha="right", va="bottom", fontweight="bold")
    axd.set_xscale("log")
    axd.set_xlim(0.09, t_end)
    axd.set_ylim(0, 21)
    axd.xaxis.set_minor_locator(NullLocator())
    axd.set_xticks([0.1, 1, 10, 100])
    axd.set_xticklabels(["0.1", "1", "10", "100"])
    axd.set_yticks([4, 8, 12, 16, 20])
    axd.set_xlabel("time on 32 threads (s)")
    axd.set_ylabel("bounds on the circuit distance")
    tidy(axd)
    save(fig, "ncs_fig1")


# =============================================================================================== figure 2
def wjh_cumulative():
    """Times to an exact value on the 126 instances of arXiv:2603.22532: ours under that study's limits (one core,
    8 GB, eight hours: the 600 s tier, else the eight-hour run) and each of its five exact methods (its sheets)."""
    import wjh_compare as W
    import xlsx_lite
    ours = {r["name"]: r["ours_8h"] for r in W.per_instance()}
    ms = W.metas()
    theirs = {m: {} for m, _ in W.THEIR_EXACT}
    for family, sheet, _ in W.FAMILIES:
        book = xlsx_lite.read(str(W.SHEETS / sheet))
        for method, s in W.THEIR_EXACT:
            if s not in book:
                continue
            for name, row in W.match(family, ms, W.sheet_rows(book[s])).items():
                if row[3] > 0 and row[4] < W.MAX_TIME:
                    theirs[method][name] = row[4]
    anyt = {}
    for d in theirs.values():
        for n, t in d.items():
            anyt[n] = min(anyt.get(n, 1e18), t)
    return ours, theirs, anyt, len(ms), W.MAX_TIME


def ablation_rows():
    """Sector problems of the 42 CSS circuits certified in the first tier, by the full method and with parts off."""
    a, b32, b1, metas = MF.bench()
    abl = T.load(ROOT / "results" / "bench_ablation_final", 1)
    circ = [m["name"] for m in metas if m["track"] == "circuit" and "sector" in m["variants"]]
    count = lambda recs, name: sum(MF.exact(recs, name, i, "sector") is not None for i in circ)
    dm = sum(any(MF.exact(a, k, i, "sector") is not None for k in ("dist-m4ri CC", "dist-m4ri CC+RW")) for i in circ)
    rows = [("full method", count(a, "ours")),
            ("without time collapse", count(abl, "ours, collapse off")),
            ("without symmetry", count(abl, "ours, symmetry off")),
            ("without the two Rank DPs", count(abl, "ours, search only")),
            ("plain search (all switched off)", count(abl, "ours, symmetry off cover off collapse off lift off window off")),
            ("dist-m4ri, without its model bound", dm)]
    return rows, len(circ)


def fig_capability():
    W, H = 183, 122
    fig, ax = canvas(W, H)
    a, b32, b1, metas = MF.bench()
    main = {m["name"]: ("full" if (m["track"] == "code" or "sector" not in m["variants"]) else "sector") for m in metas}

    # ------------------------------------------------------------------ a: instances certified by each tool
    panel(ax, 1.5, 118.6, "a", "Our hardware-scale suite: 74 codes and circuits")
    both = lambda name: [name, name + ", sparse L"]
    groups = [("this method", ["ours"]), ("dist-m4ri", DM4RI()),
              ("Gurobi", both("Gurobi")), ("SAT (CaDiCaL)", both("SAT")), ("RC2", both("RC2")),
              ("CP-SAT", both("CP-SAT")), ("HiGHS", both("HiGHS")), ("CASHWMaxSAT", both("CASHWMaxSAT")),
              ("enMaxCDCL", both("enMaxCDCL")), ("Qubitserf (codes)", ["Qubitserf CC", "Qubitserf BZ", "Qubitserf MITM"])]
    solved = lambda recs, ml: {i for i, v in main.items() if any(MF.exact(r, m, i, v) is not None for r in recs
                                                                  for m in ml)}
    rows = [(lab, len(solved((a,), ml)), len(solved((a, b32, b1), ml))) for lab, ml in groups]
    others = sorted(rows[1:], key=lambda r: (-r[2], -r[1]))
    allo = [m for _, ml in groups[1:] for m in ml]
    rows = [rows[0], ("all others together", len(solved((a,), allo)), len(solved((a, b32, b1), allo)))] + others
    axa = axes_mm(fig, 37.0, 70.5, 49.0, 42.5)                    # the left column: bar charts
    total = len(main)
    for y, (lab, t1, t2) in enumerate(rows):
        dark = BLUE if y == 0 else (INK2 if y == 1 else GRAY)
        light = BLUE_LIGHT if y == 0 else (GRAY_LIGHT if y == 1 else "#d9d8d1")
        axa.barh(y, t2, height=0.66, color=light, linewidth=0, zorder=2)
        axa.barh(y, t1, height=0.66, color=dark, linewidth=0, zorder=3)
        txt(axa, t2 + 1.0, y, "%d  |  %d" % (t1, t2), 5.4, INK if y < 2 else INK2,
            fontweight="bold" if y == 0 else "normal")
    axa.set_yticks(range(len(rows)))
    axa.set_yticklabels([r[0] for r in rows])
    for tl, r in zip(axa.get_yticklabels(), rows):
        tl.set_fontsize(5.8)
        if r[0] in ("this method", "all others together"):
            tl.set_fontweight("bold")
            tl.set_color(INK)
    axa.set_ylim(len(rows) - 0.45, -0.75)
    axa.set_xlim(0, total + 2)
    axa.axvline(total, color=AXIS, lw=0.6, zorder=1)
    txt(axa, total - 0.6, -0.78, "all %d" % total, 5.2, MUTED, ha="right", va="bottom")
    axa.set_xticks([0, 20, 40, 60])
    axa.set_xlabel("instances certified")
    tidy(axa, "x")
    axa.spines["left"].set_visible(False)
    for k, (col, lab) in enumerate(((INK2, "1 thread, 600 s"), (GRAY_LIGHT, "with a further hour, 32 threads"))):
        ly = len(rows) - 2.1 + 0.95 * k
        axa.barh(ly, 3.2, left=31.0, height=0.5, color=col, linewidth=0, zorder=3)
        txt(axa, 35.3, ly, lab, 5.2, INK2)

    # ------------------------------------------------------------------ b: the prior benchmark, cumulative
    panel(ax, 96.0, 118.6, "b", "An independent benchmark: 126 codes and circuits")
    ours, theirs, anyt, ninst, tmax = wjh_cumulative()
    axb = axes_mm(fig, 108.0, 70.5, 67.0, 42.5)                   # the right column: line plots
    grid = sorted(set([10 ** (k / 50) for k in range(-100, int(50 * math.log10(tmax)) + 1)] + [tmax]))

    def curve(times):
        ts = sorted(t for t in times if t is not None)
        out, j = [], 0
        for g in grid:
            while j < len(ts) and ts[j] <= g:
                j += 1
            out.append(j)
        return out
    for d in theirs.values():
        axb.plot(grid, curve(d.values()), color=GRAY_LIGHT, lw=0.7, zorder=2)
    cv_any, cv_ours = curve(anyt.values()), curve(ours.values())
    axb.plot(grid, cv_any, color=INK2, lw=1.2, zorder=3)
    axb.plot(grid, cv_ours, color=BLUE, lw=1.6, zorder=4)
    axb.set_xscale("log")
    axb.xaxis.set_minor_locator(NullLocator())
    axb.set_xlim(0.01, tmax)
    axb.set_ylim(0, ninst + 6)
    axb.axhline(ninst, color=AXIS, lw=0.6, zorder=1)
    txt(axb, 0.012, ninst + 1.2, "all %d instances" % ninst, 5.2, MUTED, va="bottom")
    axb.set_xticks([0.01, 0.1, 1, 10, 100, 1000, tmax])
    axb.set_xticklabels(["0.01", "0.1", "1", "10", "100", "1000", "8 h"])
    axb.set_xlabel("time limit per instance (s; one core, 8 GB)")
    axb.set_ylabel("instances certified")
    tidy(axb)
    txt(axb, tmax * 0.75, cv_ours[-1] + 3.0, "this method, %d" % cv_ours[-1], 5.8, BLUE, ha="right", va="bottom",
        fontweight="bold")
    names = {"MIP-SCIP": "SCIP", "m4riCC": "dist-m4ri"}
    each = ["%s %d" % (names.get(m, m), len(d)) for m, d in sorted(theirs.items(), key=lambda kv: -len(kv[1]))]
    each = ", ".join(each[:2]) + ",\n" + ", ".join(each[2:])
    hd = [Line2D([], [], color=INK2, lw=1.2), Line2D([], [], color=GRAY_LIGHT, lw=0.8)]
    axb.legend(hd, ["its five exact methods together, %d" % cv_any[-1], "each of them: " + each], loc="upper left",
               bbox_to_anchor=(0.0, 0.93), fontsize=5.0, handlelength=1.6, borderaxespad=0.3, labelspacing=0.4)

    # ------------------------------------------------------------------ c: surface-code scaling
    panel(ax, 96.0, 57.6, "d", "Scaling with the distance (surface-code memory circuits)")
    axc = axes_mm(fig, 108.0, 10.5, 67.0, 41.5)
    others_c = ["SAT", "RC2", "HiGHS", "CP-SAT", "Gurobi", "CASHWMaxSAT", "enMaxCDCL"]

    def pts(keys, recs=a, label="ours"):
        out = []
        for d in range(3, 27, 2):
            ts = [t for k in keys for t in [MF.exact(recs, k, "surface_d%d" % d, "sector")] if t is not None]
            if ts:
                out.append((d, max(min(ts), 0.01)))
        return out
    for k in others_c:
        p = pts([k])
        if p:
            axc.plot([q[0] for q in p], [q[1] for q in p], color=GRAY_LIGHT, lw=0.8, marker="o", ms=2.0,
                     markeredgewidth=0, zorder=2)
    p_dm = pts(DM4RI())
    axc.plot([q[0] for q in p_dm], [q[1] for q in p_dm], color=INK2, lw=1.0, marker="o", ms=2.6,
             markeredgecolor=WHITE, markeredgewidth=0.5, zorder=3)
    p_ours = pts(["ours"])
    axc.plot([q[0] for q in p_ours], [q[1] for q in p_ours], color=BLUE, lw=1.5, marker="o", ms=3.0,
             markeredgecolor=WHITE, markeredgewidth=0.6, zorder=4)
    txt(axc, p_ours[-1][0] + 0.5, p_ours[-1][1], "this method", 5.6, BLUE, fontweight="bold")
    txt(axc, p_dm[-1][0] + 0.5, p_dm[-1][1], "dist-m4ri", 5.4, INK2)
    txt(axc, 7.6, 300, "integer programming,\nSAT and MaxSAT", 5.2, GRAY, ha="left", linespacing=1.05)
    axc.set_yscale("log")
    axc.yaxis.set_minor_locator(NullLocator())
    axc.set_xlim(2.3, 28.5)
    axc.set_ylim(0.007, 2000)
    axc.axhline(600, color=AXIS, lw=0.6, zorder=1)
    txt(axc, 28.3, 700, "600 s limit", 5.0, MUTED, ha="right", va="bottom")
    axc.set_xticks(range(3, 27, 2))
    axc.set_yticks([0.01, 0.1, 1, 10, 100])
    axc.set_yticklabels(["≤0.01", "0.1", "1", "10", "100"])
    axc.set_xlabel("distance d (memory circuit of d rounds)")
    axc.set_ylabel("time to the certified distance (s, 1 thread)")
    tidy(axc)

    # ------------------------------------------------------------------ d: ablation
    panel(ax, 1.5, 57.6, "c", "What each part contributes")
    rows, ncirc = ablation_rows()
    axd = axes_mm(fig, 37.0, 10.5, 49.0, 41.5)
    for y, (lab, v) in enumerate(rows):
        col = BLUE if y == 0 else (GRAY if y < len(rows) - 1 else INK2)
        axd.barh(y, v, height=0.52, color=col if y else BLUE, linewidth=0, zorder=3,
                 alpha=1.0 if y < len(rows) - 1 else 0.55)
        txt(axd, v + 0.7, y, str(v), 5.4, INK if y == 0 else INK2, fontweight="bold" if y == 0 else "normal")
    axd.set_yticks(range(len(rows)))
    axd.set_yticklabels([r[0] for r in rows])
    for tl in axd.get_yticklabels():
        tl.set_fontsize(5.5)
    axd.set_ylim(len(rows) - 0.45, -0.6)
    axd.set_xlim(0, ncirc + 1)
    axd.axvline(ncirc, color=AXIS, lw=0.6, zorder=1)
    txt(axd, ncirc - 0.4, -0.65, "all %d" % ncirc, 5.0, MUTED, ha="right", va="bottom")
    axd.set_xticks([0, 10, 20, 30, 40])
    axd.set_xlabel("CSS circuits certified (1 thread, 600 s)")
    tidy(axd, "x")
    axd.spines["left"].set_visible(False)
    save(fig, "ncs_fig2")


# =============================================================================================== figure 3
PAPER_SHORT = {"Mitten codes": "Mitten", "Mitten codes (repository)": "Mitten, repository",
               "IBM bivariate bicycle codes": "IBM bivariate bicycle", "Distance-finding benchmark": "Distance benchmark",
               "Cornucopia codes": "Cornucopia", "Routing codes": "Routing", "Shift automorphism circuits": "Shift",
               "Walking Cat": "Walking Cat", "Left-right circuits": "Left-right", "Vine codes": "Vine",
               "Amplified qLDPC codes": "Amplified", "Tile codes": "Tile", "Nearest-neighbour planar codes": "Planar",
               "Multivariate multicycle codes": "Multicycle", "Modular hyperbolic codes": "Modular hyperbolic",
               "Weight-8 bivariate bicycle codes": "Weight-8 BB", "Balanced-product codes": "Balanced product"}
CIRC_GROUPS = ["Mitten codes", "Mitten codes (repository)", "IBM bivariate bicycle codes", "Distance-finding benchmark",
               "Cornucopia codes", "Routing codes", "Shift automorphism circuits", "Walking Cat", "Left-right circuits",
               "Vine codes", "Amplified qLDPC codes"]
CODE_GROUPS = ["Tile codes", "Nearest-neighbour planar codes", "Multivariate multicycle codes", "Mitten codes (repository)",
               "Weight-8 bivariate bicycle codes", "Modular hyperbolic codes", "IBM bivariate bicycle codes",
               "Balanced-product codes"]
VERDICT_COLOR = {"too_high": ORANGE, "settled": BLUE, "confirmed": GRAY, "open": GRAY}
VERDICT_ORDER = {"too_high": 0, "settled": 1, "open": 2, "confirmed": 3}


def audit_rows():
    with open(HERE / "audit_items.csv") as f:
        return list(csv.DictReader(f))


def short_object(s):
    s = s.replace(" circuit", "").replace(" code", "")
    return {"gross, dynamic": "gross code, dynamic", "gross, three-colour": "gross code, 3-colour",
            "four patches of distance 10": "4 patches, d = 10", "superdense, d = 11": "superdense, d = 11",
            "[[90,8,8]] level-1": "[[90,8,8]], level 1"}.get(s, s).replace(", X distance", ", X")


def stated_text(r):
    lo, hi, st = int(float(r["pub_lo"])), int(float(r["pub_hi"])), r["stated"]
    if lo != hi:
        return "%d–%d" % (lo, hi)
    return {"bound": "≤%d", "best_known": "≤%d", "estimate": "≈%d", "expected": "≈%d", "conjecture": "%d?",
            "lower_bound": "≥%d", "claim": "%d"}.get(st, "%d") % hi


def hook_example():
    """The minimum fault set of the structured-mitten [[330,66,12]] circuit (X basis, results/papers): seven hook
    faults, each on the ancilla of a Z check after its first gates, spreading Z errors to the data qubits of the
    remaining gates. Returns the faults, the net data error and the checks on it."""
    sys.path.insert(0, str(ROOT / "papers"))
    from mitten_circuit import layers_of, load
    rec = json.load(open(ROOT / "results/papers/smitten330d12_X.json"))
    Hm, sched = load(str(ROOT / "papers/mitten/structured_mitten/[[330,66,12]]"))
    hook, det, L = Hm["Hz"], Hm["Hx"], Hm["Lx"]
    order = {}
    for gates in layers_of(sched, "Z_layers", hook):
        for i, j in gates:
            order.setdefault(i, []).append(j)
    e = np.zeros(det.shape[1], dtype=np.uint8)
    faults = []
    for kind, i, m in rec["solution_faults"]:
        assert kind == "hook"
        js = order[i]
        faults.append(dict(check=i, after_gate=m, gates=len(js), spread=len(js) - m))
        for j in js[m:]:
            e[j] ^= 1
    assert not (det.astype(int) @ e % 2).any()
    return dict(faults=faults, net_weight=int(e.sum()), flipped=int((L.astype(int) @ e % 2).sum()),
                distance=rec["distance"], n=det.shape[1])


def forest(fig, ax, rows, groups, x0, ytop, pitch, plot_x, plot_w, xlim, xticks, val_x):
    """One audit panel: a row per value, grouped by paper, with the published value (open marker or range) and the
    certified value or interval (filled), joined when they differ."""
    marks = {"bound": "<", "best_known": "<", "claim": "o", "estimate": "D", "expected": "D", "conjecture": "s",
             "lower_bound": ">"}
    lines, y = [], 0.0
    for g in groups:
        sel = sorted([r for r in rows if r["paper"] == g], key=lambda r: VERDICT_ORDER[r["verdict"]])
        for k, r in enumerate(sel):
            lines.append((y, r, k == 0, g))
            y += 1
        y += 0.55
    n = y - 0.55
    h = n * pitch
    axp = axes_mm(fig, plot_x, ytop - h, plot_w, h)
    axp.set_ylim(n - 0.5, -0.5)
    axp.set_xlim(*xlim)
    # zebra by paper
    gy = {}
    for yy, r, first, g in lines:
        gy.setdefault(g, []).append(yy)
    for gi, g in enumerate(groups):
        if gi % 2 == 0:
            lo, hi = min(gy[g]) - 0.5, max(gy[g]) + 0.5
            ax.add_patch(Rectangle((x0, ytop - (hi + 0.5) * pitch), val_x + 12.5 - x0, (hi - lo) * pitch,
                                   facecolor=PANEL, edgecolor="none", zorder=0))
    for yy, r, first, g in lines:
        ym = ytop - (yy + 0.5) * pitch
        if first:
            txt(ax, x0 + 1.0, ym, PAPER_SHORT.get(g, g), 5.3, INK, fontweight="bold")
        txt(ax, plot_x - 1.2, ym, short_object(r["object"]), 5.2, INK2, ha="right")
        col = VERDICT_COLOR[r["verdict"]]
        plo, phi, clo, chi = (float(r[k]) for k in ("pub_lo", "pub_hi", "cert_lo", "cert_hi"))
        if phi > plo:
            axp.plot([plo, phi], [yy, yy], color=GRAY_LIGHT, lw=2.6, alpha=0.8, zorder=2, solid_capstyle="butt")
        if r["verdict"] in ("too_high", "settled") and not (plo <= clo <= chi <= phi and phi > plo):
            near = chi if phi >= chi else clo
            axp.plot([phi if phi >= chi else plo, near], [yy, yy], color=col, lw=0.9, zorder=3)
        if chi > clo:
            axp.plot([clo, chi], [yy, yy], color=col, lw=2.6, zorder=4, solid_capstyle="round")
        else:
            axp.scatter([clo], [yy], s=11, color=col, edgecolors=WHITE, linewidths=0.4, zorder=5)
        if phi == plo:
            axp.scatter([phi], [yy], s=13 if marks.get(r["stated"], "o") != "D" else 9, marker=marks.get(r["stated"], "o"),
                        facecolors=WHITE, edgecolors=INK2 if r["verdict"] != "confirmed" else GRAY, linewidths=0.6,
                        zorder=6 if r["verdict"] != "confirmed" else 4)
        cert = "%d" % clo if chi == clo else "%d–%d" % (clo, chi)
        txt(ax, val_x, ym, stated_text(r), 5.2, INK2, ha="right")
        txt(ax, val_x + 1.0, ym, "→", 5.0, MUTED, ha="left")
        txt(ax, val_x + 3.7, ym, cert, 5.2, col if r["verdict"] != "confirmed" else INK2, ha="left",
            fontweight="bold" if r["verdict"] in ("too_high", "settled") else "normal")
    axp.set_xticks(xticks)
    axp.set_yticks([])
    axp.spines["left"].set_visible(False)
    axp.grid(axis="x", color=GRID, lw=0.45, zorder=0)
    axp.set_axisbelow(True)
    axp.tick_params(length=0)
    axp.set_facecolor("none")
    axp.set_xlabel("distance")
    return axp


def fig_audit():
    """Figure 3: the audited values against their certified values (a), the values published too high (b) and the
    modular hyperbolic codes whose distances their study could only bracket (c)."""
    rows = audit_rows()
    W, H = 183, 134
    fig, ax = canvas(W, H)
    top = H - 3.6
    hyp = [r for r in rows if r["paper"] == "Modular hyperbolic codes"]
    rest = [r for r in rows if r["paper"] != "Modular hyperbolic codes"]
    hi = [r for r in rows if r["verdict"] == "too_high"]
    npap = len({r["ref"] for r in hi})
    panel(ax, 1.5, top, "a", "Published against certified distances")
    panel(ax, 95.5, top, "b", "The %d values published too high, in %d papers" % (len(hi), npap))

    # ------------------------------------------------------------------ a: one point per value, no bars
    axa = axes_mm(fig, 14.0, 66.0, 60.0, 60.0)
    lo_, hi_ = 4.0, 38.5
    axa.fill_between([lo_, hi_], [lo_, lo_], [lo_, hi_], color=ORANGE_PALE, alpha=0.6, lw=0, zorder=0)
    axa.plot([lo_, hi_], [lo_, hi_], color=INK2, lw=0.6, zorder=1)
    txt(axa, 37.6, 6.6, "published value\ntoo high", 5.4, ORANGE, ha="right", va="bottom", linespacing=1.1,
        fontweight="bold")
    seen = {}
    pos = []
    for r in rest:
        x, y = float(r["pub_hi"]), float(r["cert_hi"])      # a range at its upper end; the lightest error found
        seen[(x, y)] = seen.get((x, y), 0) + 1
        pos.append((r, x, y, seen[(x, y)] - 1))
    count = dict(seen)
    for r, x, y, k in pos:
        off = 0.45 * (k - (count[(x, y)] - 1) / 2)              # repeated points spread along the diagonal
        col = VERDICT_COLOR[r["verdict"]]
        closed = float(r["cert_lo"]) == y
        mk = ("o" if r["kind"] == "circuit" else "s") if closed else "v"
        axa.scatter([x + off], [y + off], s=13 if mk == "v" else (11 if mk == "o" else 9), marker=mk, color=col,
                    edgecolors=WHITE, linewidths=0.45, zorder=4)
    notes = [((16, 9), (20.5, 7.0), "mitten [[500,100,16]]"),
             ((12, 7), (13.0, 4.9), "'hook-free' schedule, [[330,66,12]]"),
             ((24, 17), (27.0, 14.2), "mitten [[975,195,24]]"),
             ((24, 16), (26.0, 19.8), "IBM [[288,12,18]], best known 24"),
             ((18, 16), (5.5, 22.0), "IBM [[288,12,18]], at most 18"),
             ((14, 10), (5.0, 15.5), "routing [[200,24,14]]"),
             ((37, 36), (24.0, 34.6), "planar [[259,2]]")]
    for (px, py), (tx, ty), lab in notes:
        axa.annotate(lab, (px, py), xytext=(tx, ty), fontsize=4.8, color=INK2, ha="left", va="center",
                     arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.4, shrinkA=0.5, shrinkB=1.6))
    axa.set_xlim(lo_, hi_)
    axa.set_ylim(lo_, hi_)
    ticks = [5, 10, 15, 20, 25, 30, 35]
    axa.set_xticks(ticks)
    axa.set_yticks(ticks)
    axa.set_xlabel("published distance")
    axa.set_ylabel("certified distance")
    axa.set_aspect("equal", adjustable="box")
    tidy(axa, "both")
    hd = [Line2D([], [], ls="", marker="o", ms=3.4, color=GRAY, markeredgecolor=WHITE),
          Line2D([], [], ls="", marker="s", ms=3.0, color=GRAY, markeredgecolor=WHITE),
          Line2D([], [], ls="", marker="v", ms=3.6, color=GRAY, markeredgecolor=WHITE),
          Line2D([], [], ls="", marker="o", ms=3.4, color=ORANGE, markeredgecolor=WHITE),
          Line2D([], [], ls="", marker="o", ms=3.4, color=BLUE, markeredgecolor=WHITE)]
    axa.legend(hd, ["circuit distance", "code distance", "certified at most (not closed)", "published too high",
                    "settled, or certified higher"], loc="upper left", fontsize=4.8, ncol=1, handlelength=1.0,
               borderaxespad=0.3, labelspacing=0.35, frameon=True, facecolor=WHITE, edgecolor="none", framealpha=0.9)

    # ------------------------------------------------------------------ b: the values published too high
    def pick(paper, kind):
        return [r for r in hi if r["paper"] == paper and r["kind"] == kind]
    repo = lambda r: dict(r, object=r["object"].split(" ")[0] + ", repository")
    groups = [("circuit distances", [
        ("Mitten", pick("Mitten codes", "circuit") + [repo(r) for r in pick("Mitten codes (repository)", "circuit")]),
        ("IBM [[288,12,18]]", [dict(r, object="as stated by IBM") for r in pick("IBM bivariate bicycle codes", "circuit")]
         + [dict(r, object="distance benchmark") for r in pick("Distance-finding benchmark", "circuit")]),
        ("Cornucopia", pick("Cornucopia codes", "circuit")), ("Routing", pick("Routing codes", "circuit")),
        ("Shift", pick("Shift automorphism circuits", "circuit")), ("Walking Cat", pick("Walking Cat", "circuit"))]),
        ("code distances", [
        ("Tile", pick("Tile codes", "code")), ("Planar", pick("Nearest-neighbour planar codes", "code")),
        ("Multicycle", pick("Multivariate multicycle codes", "code")),
        ("Mitten", [repo(r) for r in pick("Mitten codes (repository)", "code")])])]
    assert sum(len(g) for _, gs in groups for _, g in gs) == len(hi)
    items = []
    for sec, gs in groups:
        items.append(("section", sec))
        for name, sel in gs:
            for k, r in enumerate(sel):
                items.append(("row", name if k == 0 else None, r))
            items.append(("gap",))
    x_name, x_obj, x0, unit, x_val = 96.5, 137.5, 139.0, 1.6, 164.5
    y = top - 6.0
    ybot = 8.0                                                 # the bottom of panel c's axes
    nrow = sum(1 for it in items if it[0] == "row")
    pitch = (y - ybot - 0.4 - 3.0 * 2 - 1.0 * sum(1 for it in items if it[0] == "gap")) / nrow
    for it in items:
        if it[0] == "section":
            txt(ax, x_name, y - 0.4, it[1], 5.3, MUTED, fontweight="bold")
            y -= 3.0
        elif it[0] == "gap":
            y -= 1.0
        else:
            _, g, r = it
            ym = y - pitch / 2
            if g:
                txt(ax, x_name, ym, g, 5.2, INK, fontweight="bold")
            txt(ax, x_obj, ym, short_object(r["object"]), 5.0, INK2, ha="right")
            p = float(r["pub_hi"])
            clo, chi = float(r["cert_lo"]), float(r["cert_hi"])
            sure, most = p - chi, p - clo
            hgt = min(1.6, pitch * 0.62)
            ax.add_patch(Rectangle((x0, ym - hgt / 2), unit * sure, hgt, facecolor=ORANGE, edgecolor="none", zorder=3))
            if most > sure:
                ax.add_patch(Rectangle((x0 + unit * sure, ym - hgt / 2), unit * (most - sure), hgt,
                                       facecolor=ORANGE_PALE, edgecolor="none", zorder=3))
            cert = "%d" % clo if chi == clo else "%d–%d" % (clo, chi)
            txt(ax, x_val, ym, "%s → %s" % (stated_text(r), cert), 5.0, INK2)
            y -= pitch
    ybar = y - 0.4
    for v in range(0, 16, 5):
        xv = x0 + unit * v
        ax.plot([xv, xv], [ybar, top - 6.6], color=GRID, lw=0.45, zorder=1)
        txt(ax, xv, ybar - 1.6, str(v), 5.2, INK2, ha="center")
    ax.plot([x0, x0 + unit * 15], [ybar, ybar], color=AXIS, lw=0.55, zorder=1)
    txt(ax, x0 + unit * 7.5, ybar - 4.4, "published minus certified", 5.4, INK2, ha="center")
    txt(ax, x_val, top - 6.4, "published → certified", 4.7, MUTED)

    # ------------------------------------------------------------------ c: modular hyperbolic codes
    panel(ax, 1.5, 51.2, "c", "Modular hyperbolic codes: %d open distances settled" % len(hyp))
    hyp = sorted(hyp, key=lambda r: (float(r["cert_hi"]), float(r["pub_lo"])))
    axc = axes_mm(fig, 14.0, ybot, 60.0, 37.0)                     # the plot area of panel a
    for i, r in enumerate(hyp):
        plo, phi, c = float(r["pub_lo"]), float(r["pub_hi"]), float(r["cert_hi"])
        axc.plot([plo, phi], [i, i], color=GRAY_LIGHT, lw=2.4, solid_capstyle="round", zorder=2)
        axc.scatter([c], [i], s=12, color=BLUE, edgecolors=WHITE, linewidths=0.45, zorder=3)
        txt(axc, -3.6, i, r["object"].split(" ")[0], 4.8, INK2, ha="left")
    axc.set_ylim(len(hyp) - 0.4, -1.6)
    axc.set_xlim(-4.0, 30)
    axc.spines["bottom"].set_bounds(5, 30)
    axc.set_yticks([])
    axc.set_xticks([8, 12, 16, 20, 24, 28])
    axc.set_xlabel("code distance")
    axc.spines["left"].set_visible(False)
    tidy(axc, "x")
    hd = [Line2D([], [], color=GRAY_LIGHT, lw=2.4), Line2D([], [], ls="", marker="o", ms=3.4, color=BLUE)]
    axc.legend(hd, ["bracket in the study", "exact distance, this method"], loc="upper left", ncol=2, fontsize=4.9,
               handlelength=1.4, borderaxespad=0.1, columnspacing=1.0)
    save(fig, "ncs_fig3")


def fig_hook():
    """Supplementary figure: the minimum fault set of the structured mitten [[330,66,12]] circuit (formerly
    panel c of figure 3)."""
    ex = hook_example()
    W, H = 183, 40
    fig, ax = canvas(W, H)
    txt(ax, 2.0, 36.6, "structured mitten [[330,66,12]] circuit, published schedule; one row per Z check, its nine "
        "gates in schedule order", 5.2, MUTED)
    gx, gy0, cw, rh = 16.0, 31.0, 3.15, 3.55
    faults = ex["faults"]
    for r, f in enumerate(faults):
        y = gy0 - (r + 1) * rh
        txt(ax, gx - 1.5, y + rh * 0.42, "fault %d" % (r + 1), 5.0, MUTED, ha="right")
        for g in range(f["gates"]):
            hit = g >= f["after_gate"]
            ax.add_patch(Rectangle((gx + g * cw, y), cw * 0.84, rh * 0.8, facecolor=ORANGE if hit else GRAY_PALE,
                                   edgecolor="none", alpha=0.85 if hit else 1.0, zorder=2))
        star(ax, gx + f["after_gate"] * cw - cw * 0.08, y + rh * 0.4, 1.25, ORANGE, z=5)
    for g in range(faults[0]["gates"]):
        txt(ax, gx + g * cw + cw * 0.42, gy0 + 0.9, str(g + 1), 4.8, MUTED, ha="center")
    hits = sum(f["spread"] for f in faults)
    gx_end = gx + faults[0]["gates"] * cw
    arrow(ax, gx_end + 2.2, gy0 - 3.5 * rh, gx_end + 8.5, gy0 - 3.5 * rh, color=INK2, lw=0.8, ms=6)
    tiles = [("%d" % len(faults), "ancilla faults", ORANGE), ("%d" % hits, "data errors spread", ORANGE),
             ("%d" % ex["net_weight"], "net data error weight", INK), ("0", "detectors fire", INK),
             ("%d" % ex["flipped"], "logical qubits flip", ORANGE)]
    tx = gx_end + 12.0
    tw = (181.0 - tx) / len(tiles)
    for k, (big, lab, col) in enumerate(tiles):
        rbox(ax, tx + k * tw + 0.6, 13.0, tw - 1.2, 17.5, fc=PANEL, r=1.4, z=0)
        txt(ax, tx + k * tw + tw / 2, 23.6, big, 13.0, col, ha="center", fontweight="bold")
        txt(ax, tx + k * tw + tw / 2, 16.6, lab, 5.3, INK2, ha="center")
    txt(ax, tx + 0.6, 7.4, "Circuit distance %d against code distance 12. Each fault spreads to six or seven data "
        "qubits, and sampling-based" % ex["distance"], 5.4, INK2)
    txt(ax, tx + 0.6, 3.9, "searches rarely produce such combinations; the exact search excludes every set of six or "
        "fewer and finds this one.", 5.4, INK2)
    save(fig, "si_hook")


# =============================================================================================== figure 4
def selfdual_rows():
    """Self-dual BB codes with a parallel circuit: (n, k, d, best sequential, sequential exact?, parallel lo, hi)."""
    D = ROOT / "results/papers2/design"
    seq = {}
    for f in glob.glob(str(D / "sdbb*.json")):
        if re.fullmatch(r"sdbb\d+\.json", os.path.basename(f)):
            r = json.load(open(f))
            seq[tuple(r["code"])] = (r["best_circuit_distance"], r["optimal_over_family"])
    out = []
    for f in glob.glob(str(D / "sdbb*_parallel.json")):
        if not re.fullmatch(r"sdbb\d+_parallel\.json", os.path.basename(f)):
            continue
        r = json.load(open(f))
        n, k, d = r["code"]
        lo, hi = [], []
        for basis in "ZX":
            v = dict(r["circuit_distance"][basis])
            q = D / ("sdbb_parallel%d_rounds6_%s.json" % (n, basis))
            if q.exists():
                rr = json.load(open(q))
                v["certified_lower_bound"] = max(v["certified_lower_bound"], rr.get("certified_lower_bound") or 0)
                if rr.get("certified_upper_bound"):
                    v["certified_upper_bound"] = min(v.get("certified_upper_bound") or 99, rr["certified_upper_bound"])
            lo.append(v["certified_lower_bound"])
            hi.append(v.get("certified_upper_bound") or 99)
        plo, phi = min(lo), min(hi)
        fam = D / ("sdbb%d_parallel_family.json" % n)
        if fam.exists():
            fr = json.load(open(fam))
            bb = fr.get("best_orders_both_bases") or []
            b = fr.get("best_circuit_distance")
            if b is not None and b > plo and bb and all(list(x["Z"]) == list(x["X"]) == [b] * 2 for x in bb):
                plo = phi = b
        s, s_exact = seq.get((n, k, d), (None, False))
        out.append((n, k, d, s, s_exact, plo, phi))
    return sorted(out)


def fig_design_ibm():
    """Figure 4: certified design of syndrome-extraction circuits (a, b) and the memory instruction of IBM's bicycle
    architecture (c-e; papers/ibm_bicycle*.py, results/ibm)."""
    W, H = 183, 130
    fig, ax = canvas(W, H)
    top = H - 3.6

    # ------------------------------------------------------------------ a: every schedule of six BB codes
    panel(ax, 1.5, top, "a", "Circuit distances of every schedule of six bivariate bicycle codes")
    rows = []
    for key, name, dc in (("bb72", "[[72,12,6]]", 6), ("bb90", "[[90,8,10]]", 10), ("bb108", "[[108,8,10]]", 10),
                          ("gross", "[[144,12,12]] gross", 12)):
        allr = json.load(open(ROOT / ("results/papers3/bb6/%s_all.json" % key)))
        std = json.load(open(ROOT / ("results/papers3/bb6/%s_ibm.json" % key)))
        s_ = allr["standard_schedule"]
        rows.append(dict(name=name, dcode=dc, dstd=min(s_["X"][0], s_["Z"][0]),
                         all={int(d): c for d, c in allr["circuit_distance_histogram"].items()},
                         std={int(d): c for d, c in std["circuit_distance_histogram"].items()}))
    D = ROOT / "results/papers2/design"
    for f, name, dc in (("bb8_1_parallel_family.json", "[[72,14,8]]", 8),
                        ("bb8_2_parallel_family.json", "[[144,16,10]]", 10)):
        r = json.load(open(D / f))
        rows.append(dict(name=name, dcode=dc, dstd=None, std={},
                         all={int(d): c for d, c in r["circuit_distance_histogram"].items()}))
    axa = axes_mm(fig, 12.0, 72.0, 109.0, 41.0)
    area = lambda c: 26.0 * math.log10(1 + c)                  # marker area grows with the logarithm of the count
    ys = [0.0, 1.0, 2.0, 3.0, 4.55, 5.55]
    for y, r in zip(ys, rows):
        for d, c in r["all"].items():
            axa.scatter([d], [y], s=area(c), color=GRAY_LIGHT, edgecolors="none", zorder=2)
        for d, c in r["std"].items():                       # the standard family, inside the bubble of all
            axa.scatter([d], [y], s=0.45 * area(c), color=BLUE, edgecolors="none", zorder=3)
        axa.plot([r["dcode"]] * 2, [y - 0.36, y + 0.36], color=INK2, lw=0.8, zorder=4)
        best = max(r["all"])
        axa.scatter([best], [y], s=area(r["all"][best]) + 14, facecolors="none", edgecolors=ORANGE, linewidths=0.9,
                    zorder=5)
        txt(axa, best + 0.32, y - 0.02, "{:,}".format(r["all"][best]), 4.8, ORANGE, fontweight="bold")
        if r["dstd"] is not None:
            axa.scatter([r["dstd"]], [y - 0.47], marker="v", s=9, color=BLUE, edgecolors="none", zorder=5)
        txt(axa, 1.2, y, r["name"], 5.3, INK, ha="right", fontweight="bold" if "gross" in r["name"] else "normal")
    txt(axa, -2.9, -0.95, "weight 6: all 8,496 depth-seven schedules each", 4.8, MUTED)
    txt(axa, -2.9, 3.85, "weight 8: all 3,456 mirror-symmetric depth-eight orders each ($Z$ basis)", 4.8, MUTED)
    axa.set_ylim(6.2, -1.45)
    axa.set_xlim(-3.0, 12.6)
    axa.set_xticks(range(2, 13))
    axa.spines["bottom"].set_bounds(1.6, 12.6)
    axa.set_yticks([])
    axa.spines["left"].set_visible(False)
    axa.set_xlabel("circuit distance")
    tidy(axa, "x")
    # legend above the plot
    ly, lx = top - 6.6, 14.0
    for k, (c, lab) in enumerate(((10, "10"), (100, "100"), (1000, "1,000"))):
        ax.scatter([lx + 4.0 * k], [ly], s=area(c), color=GRAY_LIGHT, edgecolors="none")
    txt(ax, lx + 10.2, ly, "schedules (10, 100, 1,000)", 4.9, INK2)
    ax.scatter([lx + 36.0], [ly], s=10, color=BLUE, edgecolors="none")
    txt(ax, lx + 37.6, ly, "standard family", 4.9, INK2)
    ax.scatter([lx + 54.0], [ly], marker="v", s=9, color=BLUE, edgecolors="none")
    txt(ax, lx + 55.4, ly, "standard schedule", 4.9, INK2)
    ax.scatter([lx + 73.0], [ly], s=20, facecolors="none", edgecolors=ORANGE, linewidths=0.9)
    txt(ax, lx + 74.6, ly, "best, with count", 4.9, INK2)
    ax.plot([lx + 91.0, lx + 91.0], [ly - 1.2, ly + 1.2], color=INK2, lw=0.8)
    txt(ax, lx + 92.4, ly, "code distance", 4.9, INK2)

    # ------------------------------------------------------------------ b: self-dual BB codes
    panel(ax, 124.5, top, "b", "Self-dual BB codes, n ≤ 132")
    sd = [r for r in selfdual_rows() if r[0] <= 132]
    assert all(se and plo == phi for n, k, d, s2, se, plo, phi in sd)
    seq = {g: sum(1 for n, k, d, s2, se, plo, phi in sd if d - s2 == g) for g in range(4)}
    par = {g: sum(1 for n, k, d, s2, se, plo, phi in sd if d - plo == g) for g in range(4)}
    axb = axes_mm(fig, 136.0, 72.0, 45.0, 41.0)
    w = 0.36
    for g in range(4):
        for dx, v, col in ((-w / 2 - 0.02, seq[g], GRAY_LIGHT), (w / 2 + 0.02, par[g], BLUE)):
            if v:
                axb.bar(g + dx, v, width=w, color=col, linewidth=0, zorder=3)
                txt(axb, g + dx, v + 0.5, str(v), 5.0, INK2 if col == GRAY_LIGHT else BLUE, ha="center", va="bottom",
                    fontweight="bold" if col == BLUE else "normal")
    axb.set_xticks(range(4))
    axb.set_xticklabels(["d", "d − 1", "d − 2", "d − 3"])
    axb.set_xlim(-0.6, 3.6)
    axb.set_ylim(0, len(sd) + 4)
    axb.set_yticks([0, 10, 20, 30])
    axb.set_xlabel("circuit distance (d: code distance)")
    axb.set_ylabel("codes")
    tidy(axb)
    hd = [Rectangle((0, 0), 1, 1, facecolor=GRAY_LIGHT, edgecolor="none"),
          Rectangle((0, 0), 1, 1, facecolor=BLUE, edgecolor="none")]
    axb.legend(hd, ["best sequential circuit", "parallel circuit, this work"], loc="upper right", fontsize=4.8,
               handlelength=1.1, borderaxespad=0.2, labelspacing=0.3)

    # ------------------------------------------------------------------ IBM's bicycle architecture
    cur = json.load(open(IBM_DIR / "curves.json"))
    ps = cur["p"]
    ent = {(e["code"], "standard" if e["schedule"] == "standard" else "best"): e for e in cur["entries"]}
    d2 = ent[("bb288", "standard")]["distance"]
    row2 = 61.0

    # ------------------------------------------------------------------ c: the instruction and its distances
    panel(ax, 1.5, row2, "c", "IBM's memory instruction")
    y0, hh = 48.0, 6.6
    rbox(ax, 2.0, y0, 11.0, hh, fc=GRAY_PALE, r=0.9, z=1)
    txt(ax, 7.5, y0 + hh / 2, "error-free\ncode state", 4.5, INK2, ha="center", linespacing=1.0)
    rbox(ax, 15.6, y0, 29.0, hh, fc=ORANGE_PALE, r=0.9, z=1)
    for t in range(8):
        ax.add_patch(Rectangle((16.4 + t * 3.53, y0 + 1.5), 3.1, 2.9, facecolor=WHITE if t < 7 else GRAY_PALE,
                               edgecolor=ORANGE, lw=0.45, zorder=2))
        txt(ax, 16.4 + t * 3.53 + 1.55, y0 + 2.95, "M/R" if t == 7 else "CX", 3.4, INK2, ha="center", zorder=3)
    txt(ax, 30.1, y0 + hh + 1.3, "one noisy cycle, 8 timesteps", 4.6, ORANGE, ha="center")
    rbox(ax, 47.2, y0, 11.0, hh, fc=GRAY_PALE, r=0.9, z=1)
    txt(ax, 52.7, y0 + hh / 2, "noise-free\nfinal round", 4.5, INK2, ha="center", linespacing=1.0)
    arrow(ax, 13.3, y0 + hh / 2, 15.3, y0 + hh / 2, ms=4)
    arrow(ax, 44.9, y0 + hh / 2, 46.9, y0 + hh / 2, ms=4)
    txt(ax, 30.1, y0 - 2.3, "CNOT: 15 Paulis, p/15 each; idle: p/3; preparation, measurement: p", 4.3, MUTED,
        ha="center")
    axc = axes_mm(fig, 12.0, 11.0, 46.0, 28.0)
    drows = [("gross,\nstandard", 10, ent[("gross", "standard")]["distance"]),
             ("two-gross,\nstandard", 18, d2),
             ("gross, best\ndepth-7", None, ent[("gross", "best")]["distance"])]
    for x, (lab, assumed, cert) in enumerate(drows):
        col = BLUE if (assumed is None or cert == assumed) else ORANGE
        if assumed is not None:
            axc.scatter([x], [assumed], s=26, marker="s", facecolors=WHITE, edgecolors=INK2, linewidths=0.8, zorder=4)
        if assumed is not None and assumed != cert:
            axc.annotate("", (x, cert + 0.5), xytext=(x, assumed - 0.5),
                         arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=0.8, mutation_scale=5))
        axc.scatter([x], [cert], s=24, color=col, edgecolors=WHITE, linewidths=0.5, zorder=5)
        txt(axc, x + 0.13, cert, "%d" % cert, 5.2, col, fontweight="bold")
    axc.set_xticks(range(3))
    axc.set_xticklabels([r[0] for r in drows], fontsize=4.9, linespacing=1.0)
    axc.set_xlim(-0.5, 2.6)
    axc.set_ylim(8.0, 21.5)
    axc.set_yticks([8, 12, 16, 20])
    axc.set_ylabel("circuit distance")
    tidy(axc)
    h = [Line2D([], [], ls="", marker="s", ms=3.4, markerfacecolor=WHITE, markeredgecolor=INK2),
         Line2D([], [], ls="", marker="o", ms=3.4, color=BLUE)]
    axc.legend(h, ["assumed by IBM", "certified"], loc="upper left", fontsize=4.7, ncol=2, handletextpad=0.2,
               columnspacing=0.7, borderaxespad=0.2)

    # ------------------------------------------------------------------ d: two-gross, bound against extrapolation
    panel(ax, 63.5, row2, "d", "Two-gross code: below any decoder")
    axd = axes_mm(fig, 75.0, 11.0, 46.0, 43.0)
    e2 = ent[("bb288", "standard")]
    lb2 = [max(v["rates"][str(p)]["log10_lower_bound"] for v in e2["bases"].values()) for p in ps]
    axd.fill_between(ps, [1e-60] * len(ps), [10 ** v for v in lb2], color=BLUE, alpha=0.10, lw=0, zorder=1)
    axd.plot(ps, [10 ** v for v in lb2], color=BLUE, lw=1.4, zorder=3)
    ibm = {1e-3: -20.1, 1e-4: -38.3}
    axd.plot(list(ibm), [10 ** v for v in ibm.values()], color=GRAY, lw=0.9, ls=(0, (3, 2)), zorder=2)
    axd.scatter(list(ibm), [10 ** v for v in ibm.values()], s=20, marker="s", facecolors=WHITE, edgecolors=INK2,
                linewidths=0.8, zorder=4)
    i4 = ps.index(1e-4)
    gap = lb2[i4] - ibm[1e-4]
    axd.annotate("", (1e-4, 10 ** (lb2[i4] - 0.3)), xytext=(1e-4, 10 ** (ibm[1e-4] + 0.5)),
                 arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=0.8, mutation_scale=5))
    txt(axd, 1.13e-4, 10 ** ((lb2[i4] + ibm[1e-4]) / 2), "%.0f orders" % gap, 5.0, ORANGE, fontweight="bold")
    txt(axd, 1.9e-3, 10 ** (lb2[-1] - 4.6), "lower bound,\nany decoder", 4.9, BLUE, ha="right", va="top",
        linespacing=1.05)
    txt(axd, 1.15e-3, 10 ** (ibm[1e-3] + 0.8), "projected by IBM\n(assumes d = 18)", 4.7, INK2, ha="right",
        va="bottom", linespacing=1.05)
    txt(axd, 2.6e-4, 10 ** (ibm[1e-4] + 0.4), "excluded for every decoder", 4.6, BLUE, ha="left", va="center",
        alpha=0.8)
    axd.set_xscale("log")
    axd.set_yscale("log")
    axd.xaxis.set_minor_locator(NullLocator())
    axd.yaxis.set_minor_locator(NullLocator())
    axd.set_xlim(ps[0] * 0.9, ps[-1] * 1.1)
    axd.set_ylim(10 ** (min(ibm[1e-4], lb2[0]) - 3), 10 ** (max(ibm[1e-3], lb2[-1]) + 3))
    axd.set_yticks([1e-40, 1e-35, 1e-30, 1e-25, 1e-20])
    axd.set_xlabel("physical error rate p")
    axd.set_ylabel("logical error rate per instruction")
    tidy(axd)

    # ------------------------------------------------------------------ e: gross code, standard against best
    panel(ax, 124.5, row2, "e", "Gross code: what distance 11 gains")
    axe = axes_mm(fig, 136.0, 11.0, 45.0, 43.0)
    sims = {}
    for f in sorted(IBM_DIR.glob("sim_gross_c1_*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            sims.setdefault(r["schedule"], {}).setdefault(r["p"], {})[r["basis"]] = r
    mwd = json.load(open(IBM_DIR / "mwd_gross_c1.json"))
    lp = [p for p in mwd["p"] if p <= 5e-4]
    tot = {}
    for e in mwd["entries"]:
        for p in lp:
            r = e["rates"][str(p)]
            t = tot.setdefault(e["schedule"], {}).setdefault(p, [0.0, 0.0])
            t[0] += 10 ** r["log10_total"]
            t[1] += 10 ** r["log10_w5"] if r["n_w5"] else 0.0
    best_tag = ent[("gross", "best")]["schedule"]
    for tag, col, lab in (("standard", GRAY, "standard, d = 10"), (best_tag, BLUE, "best depth-7, d = 11")):
        axe.plot(lp, [tot[tag][p][0] for p in lp], color=col, lw=1.3, zorder=3)
        pts = sorted((p, v) for p, v in sims.get(tag, {}).items() if len(v) == 2)
        xs = [p for p, _ in pts]
        ys2 = [sum(v[b]["rate"] for b in "ZX") for _, v in pts]
        er = [math.sqrt(sum(v[b]["failures"] / v[b]["shots"] ** 2 for b in "ZX")) for _, v in pts]
        hollow = tag == "standard"
        axe.errorbar(xs, ys2, yerr=er, fmt="o", ms=3.0 if hollow else 2.2, color=col, mfc=WHITE if hollow else col,
                     mec=col, mew=0.6 if hollow else 0.3, elinewidth=0.5, capsize=0, zorder=4 if hollow else 5,
                     label=lab)
        if xs:
            axe.plot(xs, ys2, color=col, lw=0.7, zorder=3)
    axe.plot(lp, [tot["standard"][p][1] for p in lp], color=GRAY, lw=0.8, ls=(0, (1.2, 1.2)), zorder=3)
    ibmg = {1e-4: -14.8, 1e-3: -8.8}
    axe.scatter(list(ibmg), [10 ** v for v in ibmg.values()], s=16, marker="s", facecolors=WHITE, edgecolors=INK2,
                linewidths=0.7, zorder=5, label="projected by IBM")
    ratio = tot["standard"][1e-4][0] / tot[best_tag][1e-4][0]
    txt(axe, 1.5e-4, tot[best_tag][2e-4][0] / 400, "%.0f× lower\nat $p=10^{-4}$" % ratio, 4.9, BLUE, ha="left",
        fontweight="bold", linespacing=1.05)
    txt(axe, 4.5e-5, 2e-11, "exact to $p^{6}$,\nminimum-weight\ndecoder", 4.5, MUTED, ha="left", linespacing=1.05)
    txt(axe, 4.6e-3, 1e-7, "BP-OSD\nsimulation", 4.5, MUTED, ha="center", linespacing=1.05)
    axe.set_xscale("log")
    axe.set_yscale("log")
    axe.xaxis.set_minor_locator(NullLocator())
    axe.yaxis.set_minor_locator(NullLocator())
    axe.set_xlim(4e-5, 1.2e-2)
    axe.set_ylim(1e-20, 1)
    axe.set_yticks([1e-20, 1e-15, 1e-10, 1e-5, 1])
    axe.set_xlabel("physical error rate p")
    axe.set_ylabel("logical error rate per instruction")
    axe.legend(loc="upper left", fontsize=4.6, handlelength=1.0, borderaxespad=0.2, labelspacing=0.3)
    tidy(axe)
    save(fig, "ncs_fig4")


def sdbb_table(path):
    """Supplementary table of the self-dual BB designs (the rows of figure 4c)."""
    out = [r"\begin{tabular}{@{}lrrr@{\hspace{2.5em}}lrrr@{}}", r"\toprule",
           r"code & $d$ & sequential & parallel & code & $d$ & sequential & parallel \\", r"\midrule"]
    cells = []
    for n, k, d, s, s_exact, plo, phi in selfdual_rows():
        seq = "" if s is None else ("%d" % s if s_exact else r"$\ge$%d" % s)
        par = "%d" % plo if plo == phi else "%d--%d" % (plo, phi)
        cells.append(r"\qc{%d,%d,%d} & %d & %s & %s" % (n, k, d, d, seq, par))
    half = (len(cells) + 1) // 2
    for i in range(half):
        right = cells[half + i] if half + i < len(cells) else " & & & "
        out.append(cells[i] + " & " + right + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/papers2/design; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


# =============================================================================================== figure 5
IBM_DIR = ROOT / "results" / "ibm"


def ibm_table(path):
    """Supplementary table of the decoder-independent lower bounds and leading-order terms of the memory instruction
    (results/ibm/curves.json), with the rates of ref. (Tour de gross, Table 2)."""
    cur = json.load(open(IBM_DIR / "curves.json"))
    name = {"gross": "gross", "bb288": "two-gross"}
    ibm = {"gross": {1e-4: -14.8, 1e-3: -8.8}, "bb288": {1e-4: -38.3, 1e-3: -20.1}}
    e10 = lambda v: "--" if v is None else r"$10^{%.1f}$" % v
    out = [r"\begin{tabular}{@{}lcrrrrrrr@{}}", r"\toprule",
           r" & & & \multicolumn{2}{c}{minimum fault sets} & \multicolumn{2}{c}{bound, any decoder} & "
           r"\multicolumn{2}{c}{ref.~\citenum{yoder_2025_tour}} \\",
           r"\cmidrule(lr){4-5}\cmidrule(lr){6-7}\cmidrule(l){8-9}",
           r"code, schedule & basis & $d$ & used & family & $p=10^{-4}$ & $10^{-3}$ & $10^{-4}$ & $10^{-3}$ \\",
           r"\midrule"]
    for e in cur["entries"]:
        sched = "standard" if e["schedule"] == "standard" else "best"
        for k, b in enumerate(x for x in "ZX" if x in e["bases"]):
            r = e["bases"][b]
            rate = lambda p, f: r["rates"][str(p)].get(f)
            used = "%d" % r["n_minimum_fault_sets"] if r["source"] == "all minimum fault sets" else \
                r"%d\textsuperscript{a}" % r["n_minimum_fault_sets"]
            ref = [e10(ibm[e["code"]][p]) if k == 0 and e["schedule"] == "standard" else "" for p in (1e-4, 1e-3)]
            out.append(" & ".join([name[e["code"]] + ", " + sched if k == 0 else "", "$%s$" % b,
                                   "%d" % r.get("distance", e["distance"]), used, "%d" % r["n_family"],
                                   e10(rate(1e-4, "log10_lower_bound")), e10(rate(1e-3, "log10_lower_bound"))]
                                  + ref) + r" \\")
        out.append(r"\addlinespace[2pt]")
    out[-1] = r"\bottomrule"
    out.append(r"\end{tabular}")
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/ibm/curves.json; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


def ibm_spectrum_table(path):
    """Supplementary table of the logical fault sets of weight <= 12 of the gross code's instruction and the expansion
    of a minimum-weight decoder's logical error rate to order p^6 at p = 1e-4 (results/ibm/mwd_gross_c1.json)."""
    mwd = json.load(open(IBM_DIR / "mwd_gross_c1.json"))
    e10 = lambda v: "--" if v is None or v == -math.inf else r"$10^{%.1f}$" % v
    out = [r"\begin{tabular}{@{}lcrrrrrrrr@{}}", r"\toprule",
           r" & & & \multicolumn{3}{c}{logical fault sets of weight} & \multicolumn{4}{c}{failures at $p=10^{-4}$} \\",
           r"\cmidrule(lr){4-6}\cmidrule(l){7-10}",
           r"schedule & basis & $d$ & 10 & 11 & 12 & weight 5 & weight 6 (sets 10, 11) & weight 6 (sets 12) & total \\",
           r"\midrule"]
    for k, e in enumerate(mwd["entries"]):
        n = {int(w): c for w, c in e["sets_by_weight"].items()}
        r = e["rates"][str(1e-4)]
        sched = "standard" if e["schedule"] == "standard" else "best"
        first = k == 0 or mwd["entries"][k - 1]["schedule"] != e["schedule"]
        out.append(" & ".join([sched if first else "", "$%s$" % e["basis"], "%d" % e["distance"],
                               "{:,}".format(n.get(10, 0)), "{:,}".format(n.get(11, 0)), "{:,}".format(n.get(12, 0)),
                               e10(r["log10_w5"] if r["n_w5"] else None), e10(r["log10_w6_from_10_11"]),
                               e10(r["log10_w6_from_12"]), e10(r["log10_total"])]) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/ibm/mwd_gross_c1.json; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


def ibm_sim_table(path):
    """Supplementary table of the BP-OSD simulations of the gross code's instruction (results/ibm/sim_gross_c1_*.jsonl):
    rates with failures and shots per schedule and basis, and the ratio of the summed rates."""
    sims = {}
    for f in sorted(IBM_DIR.glob("sim_gross_c1_*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            sims.setdefault(r["p"], {})[("standard" if r["schedule"] == "standard" else "best", r["basis"])] = r
    def cell(r):
        e = math.floor(math.log10(r["rate"]))
        return r"$%.2f\times10^{%d}$ (%d)" % (r["rate"] / 10 ** e, e, r["failures"])

    out = [r"\begin{tabular}{@{}lccccc@{}}", r"\toprule",
           r" & \multicolumn{2}{c}{standard schedule} & \multicolumn{2}{c}{best schedule} & \\",
           r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
           r"$p$ & $Z$ basis & $X$ basis & $Z$ basis & $X$ basis & standard/best \\", r"\midrule"]
    for p in sorted(sims, reverse=True):
        v = sims[p]
        keys = [("standard", "Z"), ("standard", "X"), ("best", "Z"), ("best", "X")]
        cells = [cell(v[k]) if k in v else "" for k in keys]
        ratio = ""
        if all(k in v for k in keys):
            a = v[keys[0]]["rate"] + v[keys[1]]["rate"]
            b = v[keys[2]]["rate"] + v[keys[3]]["rate"]
            ratio = "%.2f" % (a / b)
        out.append(" & ".join([r"$%g\times10^{-3}$" % (p * 1e3)] + cells + [ratio]) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/ibm/sim_gross_c1_*.jsonl; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


# =============================================================================================== audit table
def audit_table(path):
    """Supplementary table of every audited value (docs/audit_items.csv) as a LaTeX longtable, in the order of
    figure 3."""
    stated = {"claim": "stated as the distance", "bound": "upper bound", "best_known": "best known value",
              "estimate": "estimate", "expected": "expected", "conjecture": "conjecture", "range": "range",
              "open": "open", "lower_bound": "lower bound"}
    rows = audit_rows()

    def tex(x):
        x = re.sub(r"\[\[([0-9,]+)\]\]", lambda m: r"\qc{%s}" % m.group(1), x)
        return x.replace("–", "--").replace("_", r"\_").replace("d = ", "$d=$").replace("n = ", "$n=$")
    out = [r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{2.4cm}>{\raggedright\arraybackslash}p{2.9cm}"
           r">{\raggedright\arraybackslash}p{2.5cm}>{\raggedright\arraybackslash}p{1.35cm}c"
           r">{\raggedright\arraybackslash}p{4.1cm}@{}}",
           r"\caption{Every audited value of \cref{sec:audit}, in the order of Fig.~3 of the main text. Published: the value "
           r"and how the paper states it. Certified: the exact value (bold where it differs from the published one), or the "
           r"interval between the proved lower bound and the lightest error found. Prov.: A, the authors' circuit or data "
           r"files; R, rebuilt from the paper's text and checked against values it reports as exact.}\label{tab:audit}\\",
           r"\toprule paper & object & published (how stated) & certified & prov. & note \\ \midrule \endfirsthead",
           r"\toprule paper & object & published (how stated) & certified & prov. & note \\ \midrule \endhead",
           r"\bottomrule \endlastfoot"]
    refs = {r["paper"]: r["ref"] for r in rows}
    for kind, groups, title in (("circuit", CIRC_GROUPS, "Circuit distances"), ("code", CODE_GROUPS, "Code distances")):
        out.append(r"\multicolumn{6}{@{}l}{\textit{%s}} \\[2pt]" % title)
        for g in groups:
            sel = sorted([r for r in rows if r["kind"] == kind and r["paper"] == g],
                         key=lambda r: VERDICT_ORDER[r["verdict"]])
            for k, r in enumerate(sel):
                lo, hi = int(float(r["pub_lo"])), int(float(r["pub_hi"]))
                pub = ("%d--%d" % (lo, hi) if lo != hi else {"bound": "$\\le$%d", "best_known": "$\\le$%d",
                                                            "lower_bound": "$\\ge$%d"}.get(r["stated"], "%d") % hi)
                clo, chi = int(float(r["cert_lo"])), int(float(r["cert_hi"]))
                cert = "%d" % clo if clo == chi else "%d--%d" % (clo, chi)
                if r["verdict"] in ("too_high", "settled") and clo == chi:
                    cert = r"\textbf{%s}" % cert
                paper = (tex(g) + r"~\cite{%s}" % refs[g]) if k == 0 else ""
                out.append(" & ".join([paper, tex(r["object"]), "%s (%s)" % (pub, stated[r["stated"]]), cert, r["prov"],
                                       tex(r["note"])]) + r" \\")
            out.append(r"\addlinespace[2pt]")
        if kind == "circuit":
            out.append(r"\midrule")
    out.append(r"\end{longtable}")
    Path(path).write_text("% generated by docs/make_ncs_figures.py from docs/audit_items.csv; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


if __name__ == "__main__":
    OUT = Path(sys.argv[1]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    which = sys.argv[2:] or ["1", "2", "3", "4", "hook", "table"]
    for k in which:
        if k == "table":
            audit_table(OUT / "si_audit_table.tex")
            sdbb_table(OUT / "si_sdbb_table.tex")
            if (IBM_DIR / "curves.json").exists():
                ibm_table(OUT / "si_ibm_table.tex")
            if (IBM_DIR / "mwd_gross_c1.json").exists():
                ibm_spectrum_table(OUT / "si_ibm_spectrum_table.tex")
            if list(IBM_DIR.glob("sim_gross_c1_*.jsonl")):
                ibm_sim_table(OUT / "si_ibm_sim_table.tex")
            continue
        {"1": fig_schematic, "2": fig_capability, "3": fig_audit, "4": fig_design_ibm, "hook": fig_hook}[k]()
