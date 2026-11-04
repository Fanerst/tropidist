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
NAVY = "#1b4f91"
# One meaning per color in all figures: blue, a certified result of this work; orange, a fault, a gap to a published value or a rejected case;
# gray, published values and comparison methods.  Figures print at their true width of 183 mm, and no text is below 5 pt.
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
        ax.text(x + 3.6, y, t, fontsize=7.0, fontweight="bold", color=INK, ha="left", va="baseline")


def txt(ax, x, y, s, size=6.0, color=INK2, ha="left", va="center", **kw):
    return ax.text(x, y, s, fontsize=max(size, 5.0), color=color, ha=ha, va=va, **kw)


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
    rbox(ax, 165.0, yb, 12.0, 10.0, fc=BLUE_PALE, r=1.0, z=1)
    ax.scatter(165.6 + rng.random(52) * 10.8, yb + 0.6 + rng.random(52) * 8.8, s=0.95, color=NAVY, linewidths=0,
               zorder=3)
    for xc, name, dims, note, ncol in ((111.0, "full error model", "5,184 × 206,352", None, None),
                                      (148.0, "one memory basis", "2,736 × 26,208", "same distance", BLUE),
                                      (171.0, "collapsed over rounds", "144 × 720", "lower bound", BLUE)):
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
    cards = [(2.0, BLUE, BLUE_PALE, "dense Rank DP"), (31.5, BLUE, BLUE_PALE, "truncated Rank DP"),
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
    trellis(ax, np.linspace(x0 + 3.6, x0 + CW - 3.6, 6), 20.8, [1, 2, 4, 4, 2, 1], BLUE, BLUE_PALE,
            spread=2.6, r=0.7, path=[0, 1, 2, 1, 0, 0])
    txt(ax, x0 + CW / 2, 8.0, r"cost $\approx\sum\,2^{w}$ over the cuts,", 5.2, INK2, ha="center")
    txt(ax, x0 + CW / 2, 4.7, "independent of the distance", 5.2, INK2, ha="center")
    # truncated: light states only, forward and backward, joined at a cut
    x0 = 31.5
    txt(ax, x0 + 7.2, 29.7, r"forward, $\leq T_{\mathrm{f}}$", 4.9, MUTED, ha="center")
    txt(ax, x0 + 20.8, 29.7, r"backward, $\leq T_{\mathrm{b}}$", 4.9, MUTED, ha="center")
    pf = trellis(ax, np.linspace(x0 + 2.9, x0 + 11.5, 4), 20.8, [1, 2, 4, 4], BLUE, BLUE_PALE,
                 spread=2.6, r=0.7, keep=[[1], [1, 1], [1, 1, 1, 0], [1, 0, 1, 1]], path=[0, 0, 1, 3])
    pb = trellis(ax, np.linspace(x0 + 16.5, x0 + 25.1, 4), 20.8, [4, 4, 2, 1], BLUE, BLUE_PALE,
                 spread=2.6, r=0.7, keep=[[1, 1, 0, 1], [0, 1, 1, 1], [1, 1], [1]], path=[3, 3, 1, 0], mirror=True)
    ax.plot([x0 + CW / 2, x0 + CW / 2], [14.0, 27.6], color=INK2, lw=0.55, ls=(0, (2, 1.4)), zorder=1)
    for i in (0, 3):
        on = i == 3
        ax.plot([pf[-1][i][0], pb[0][i][0]], [pf[-1][i][1], pb[0][i][1]], color=BLUE if on else GRAY_LIGHT,
                lw=1.25 if on else 0.5, ls="-" if on else (0, (1.5, 1)), zorder=4)
    txt(ax, x0 + CW / 2, 12.6, "join", 4.9, MUTED, ha="center")
    txt(ax, x0 + CW / 2, 8.0, "keeps only light states;", 5.2, INK2, ha="center")
    txt(ax, x0 + CW / 2, 4.7, "cost set by their number", 5.2, INK2, ha="center")
    # search: canonical branching, pruning, completion by lookup
    x0 = 61.0
    txt(ax, x0 + CW / 2, 29.7, r"a solution of weight $\leq K$?", 5.0, MUTED, ha="center")
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
    txt(ax, x0 + CW - 0.7, 26.6, "× covering\nbound", 5.0, ORANGE, ha="right", va="center", linespacing=1.05)
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
    ours = {r["name"]: r["ours_8h"] for r in W.per_instance()}
    ms = W.metas()
    theirs = {m: {} for m, _ in W.THEIR_EXACT}
    for family, sheet, _ in W.FAMILIES:
        book = W.read_sheet(sheet)
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
            ("all switched off but the Rank DPs", count(abl, "ours, symmetry off cover off collapse off lift off window off")),
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
               "Amplified qLDPC codes": "Amplified", "Tile codes": "Tile", "Nearest-neighbor planar codes": "Planar",
               "Multivariate multicycle codes": "Multicycle", "Modular hyperbolic codes": "Modular hyperbolic",
               "Weight-8 bivariate bicycle codes": "Weight-8 BB", "Balanced-product codes": "Balanced product"}
CIRC_GROUPS = ["Mitten codes", "Mitten codes (repository)", "IBM bivariate bicycle codes", "Distance-finding benchmark",
               "Cornucopia codes", "Routing codes", "Shift automorphism circuits", "Walking Cat", "Left-right circuits",
               "Vine codes", "Amplified qLDPC codes"]
CODE_GROUPS = ["Tile codes", "Nearest-neighbor planar codes", "Multivariate multicycle codes", "Mitten codes (repository)",
               "Weight-8 bivariate bicycle codes", "Modular hyperbolic codes", "IBM bivariate bicycle codes",
               "Balanced-product codes"]
VERDICT_COLOR = {"too_high": ORANGE, "settled": BLUE, "confirmed": GRAY, "open": GRAY, "not_counted": GRAY}
VERDICT_ORDER = {"too_high": 0, "settled": 1, "open": 2, "confirmed": 3, "not_counted": 4}


def audit_rows():
    with open(HERE / "audit_items.csv") as f:
        return list(csv.DictReader(f))


def short_object(s):
    s = s.replace(" circuit", "").replace(" code", "")
    return {"gross, dynamic": "gross code, dynamic", "gross, three-color": "gross code, 3-color",
            "four patches of distance 10": "4 patches, d = 10", "superdense, d = 11": "superdense, d = 11",
            "[[90,8,8]] level-1": "[[90,8,8]], level 1"}.get(s, s).replace(", X distance", ", X")


def stated_text(r):
    lo, hi, st = int(float(r["pub_lo"])), int(float(r["pub_hi"])), r["stated"]
    if lo != hi:
        return "%d–%d" % (lo, hi)
    return {"bound": "≤%d", "estimated_bound": "≤%d", "best_known": "≤%d", "estimate": "≈%d", "expected": "≈%d", "randomized": "≈%d",
            "conjecture": "%d?", "lower_bound": "≥%d", "claim": "%d"}.get(st, "%d") % hi


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


# ---------------------------------------------------------------------------------------------------- Fig. 3
EXT = ROOT / "results" / "bench_extended"
SHEETS = ROOT / "papers" / "downloads" / "codedistance" / "paper results"


def code_distance(s):
    m = re.search(r"\[\[\d+,\d+,(\d+)\]\]", s)
    return int(m.group(1)) if m else None


def signed(stated, v):
    return {"bound": "≤%d", "estimated_bound": "≤%d", "best_known": "≤%d", "estimate": "≈%d", "expected": "≈%d", "randomized": "≈%d",
            "lower_bound": "≥%d", "conjecture": "%d?"}.get(stated, "%d") % v


def closed(*records):
    """Interval from extended-budget records of one problem (those present): the highest lower bound and the lightest verified witness."""
    lo, hi = None, None
    for p in records:
        if not (EXT / p).exists():
            continue
        r = json.load(open(EXT / p))
        if r["lower_bound"] is not None:
            lo = max(lo or 0, r["lower_bound"])
        if r["upper_bound"] is not None and r["witness_ok"]:
            hi = min(hi or 10 ** 6, r["upper_bound"])
    return lo, hi


def best_known():
    import wjh_compare as W
    out = {}
    for sheet in ("12 tanner_codes.xlsx", "07 bivariate_bicycle.xlsx"):
        for r in W.read_sheet(sheet)["best"]:
            if len(r) > 3 and r[1].strip().isdigit():
                out[r[0]] = int(float(r[3]))
    return out


class Column:
    """Rows on one distance axis: code distance as a tick, published value hollow or a gray range, certified value blue, as a point or, if not closed,
    an interval, with an orange line to a published value it lies below; the values in numbers at the right."""
    SUB, SUBGAP = 2.9, 0.6

    def __init__(self, ax, x_name, x_label, x0, x1, dmin, dmax, ynum):
        self.ax, self.x_name, self.x_label, self.x0, self.x1, self.dmin, self.ynum = ax, x_name, x_label, x0, x1, dmin, ynum
        self.unit = (x1 - x0) / (dmax - dmin)
        self.spans = []

    def X(self, d):
        return self.x0 + (d - self.dmin) * self.unit

    def start(self, y):
        self.y, self.ytop = y, y

    def close(self):
        self.spans.append((self.y, self.ytop))

    def sub(self, s, first=False):
        if not first:
            self.y -= self.SUBGAP
        txt(self.ax, self.x_name, self.y - 1.3, s, 5.4, MUTED, fontweight="bold", zorder=1, bbox=dict(facecolor=WHITE, edgecolor="none", pad=0.6))
        self.y -= self.SUB

    def row(self, pitch, label, plo, phi, clo, chi, stated, name=None, tick=None, also=None):
        ax, X = self.ax, self.X
        ym = self.y - pitch / 2
        if name:
            txt(ax, self.x_name, ym, name, 5.8, INK, fontweight="bold")
        txt(ax, self.x_label, ym, label, 5.6, INK2, ha="right")
        if tick is not None:
            ax.plot([X(tick)] * 2, [ym - 1.0, ym + 1.0], color=INK, lw=0.7, zorder=3, solid_capstyle="butt")
        if phi > plo:
            ax.plot([X(plo), X(phi)], [ym, ym], color=GRAY_LIGHT, lw=2.0, solid_capstyle="round", zorder=2)
        elif phi != chi:
            ax.plot([X(chi), X(phi)], [ym, ym], color=ORANGE if chi < phi else BLUE, lw=0.8, zorder=2)
        if clo < chi:
            ax.plot([X(clo), X(chi)], [ym, ym], color=BLUE, lw=2.0, solid_capstyle="round", zorder=3)
        else:
            ax.scatter([X(chi)], [ym], s=11, color=BLUE, edgecolors=WHITE, linewidths=0.4, zorder=5)
        if phi == plo:
            ax.scatter([X(phi)], [ym], s=11, facecolors=WHITE if phi != chi else "none", edgecolors=INK2, linewidths=0.6, zorder=6 if phi == chi else 4)
        if also is not None:
            ax.scatter([X(also)], [ym], s=9, marker="D", color=BLUE_LIGHT, edgecolors=WHITE, linewidths=0.3, zorder=5)
        pub = "%d–%d" % (plo, phi) if phi > plo else signed(stated, phi)
        cert = ("%d–%d" % (clo, chi) if clo < chi else "%d" % chi) + (" (%d)" % also if also is not None else "")
        txt(ax, self.ynum - 0.9, ym, pub, 5.6, INK2, ha="right")
        txt(ax, self.ynum, ym, "→", 5.2, MUTED, ha="center")
        txt(ax, self.ynum + 0.9, ym, cert, 5.6, BLUE, fontweight="bold")
        self.y -= pitch

    def axis(self, ticks, xlabel, yb):
        ax, X = self.ax, self.X
        for lo, hi in self.spans:
            for v in ticks:
                ax.plot([X(v), X(v)], [max(lo, yb), hi], color=GRID, lw=0.4, zorder=0)
        for v in ticks:
            txt(ax, X(v), yb - 1.7, str(v), 5.5, INK2, ha="center")
        ax.plot([self.x0, self.x1], [yb, yb], color=AXIS, lw=0.5, zorder=1)
        txt(ax, (self.x0 + self.x1) / 2, yb - 4.1, xlabel, 5.8, INK2, ha="center")


def tanner_distance(z, *xrecords):
    """(value, closed in both bases): the code distance when the X search has ended, else the Z distance."""
    xlo, xhi = closed(*xrecords)
    if xlo is not None and xlo == xhi:
        return min(z, xhi), True
    return z, False


def fig_audit():
    rows = {(r["paper"], r["object"]): r for r in audit_rows()}
    bk = best_known()
    q288 = closed("ours_pipeline__dp-2/wjh_qt_288_2_24__full__t32.json")
    q324 = closed("ours_pipeline__dp-2/wjh_qt_324_4_25__full__t32.json")
    q360 = closed("ours_pipeline__dp-2/wjh_qt_360_4_24__full__t32.json")
    q396 = closed("ours_pipeline__dp-2/wjh_qt_396_4_26__full__t32.json", "ours_pipeline__dp-2__kmin-26__kmax-26/wjh_qt_396_4_26__full__t89.json",
                  "isd__stop%5Fat-27/wjh_qt_396_4_26__full__t16.json")
    b648 = closed("ours_pipeline__dp-2/wjh_bb_n648__full__t32.json", "ours_pipeline__dp-2__kmin-31__kmax-31/wjh_bb_n648__full__t57.json",
                  "isd__stop%5Fat-32/wjh_bb_n648__full__t16.json")
    # BB [[756,16]]: the threshold-33 run closes it at 34 when its record is here
    b756 = closed("ours_pipeline__dp-2__kmax-32/wjh_bb_n756__full__t57.json", "isd/wjh_bb_n756__full__t16.json",
                  "ours_pipeline__dp-2__kmin-33__kmax-33/wjh_bb_n756__full__t134.json")
    assert q288 == (24, 24) and q324 == (25, 25) and q360 == (24, 24) and q396 == (27, 27) and b648 == (32, 32) and b756[1] == 34 and b756[0] >= 33
    x288 = tanner_distance(q288[0], "tanner_x/wjh_qt_288_2_24_Xdist__full__t12.json", "tanner_x/wjh_qt_288_2_24_Xdist_isd.json")
    x324 = tanner_distance(q324[0], "tanner_x/wjh_qt_324_4_25_Xdist_kmin24.json", "tanner_x/wjh_qt_324_4_25_Xdist_isd.json")
    x360 = tanner_distance(q360[0], "tanner_x/wjh_qt_360_4_24_Xdist_kmax23.json", "tanner_x/wjh_qt_360_4_24_Xdist_isd.json")
    x396 = tanner_distance(q396[0], "tanner_x/wjh_qt_396_4_26_Xdist_kmax25.json", "tanner_x/wjh_qt_396_4_26_Xdist_isd.json")
    too_high_rows = [k for k, r in rows.items() if r["verdict"] == "too_high"]
    settled_rows = [k for k, r in rows.items() if r["verdict"] == "settled" and r["paper"] != "Modular hyperbolic codes"]
    used = []

    # One row pitch in every panel. The left column holds a (22 rows) and d, Google's surface-code circuits (8 rows); the
    # right column b (13 rows) and c, Google's color codes (15 rows), with the key under its axis, so the columns end together.
    SUB, SUBGAP = Column.SUB, Column.SUBGAP
    p, gap, KEY = 3.0, 0.9, 2.9
    h_left = 1.3 + (2 * SUB + SUBGAP) + 5 * gap + 22 * p + 3.8 + 1.0 + (2 * SUB + SUBGAP) + 8 * p
    h_right = 1.3 + (2 * SUB + SUBGAP) + 13 * p + 3.8 + 1.0 + SUB + 15 * p
    below_axis, key_top = 5.6, 8.0                       # axis labels; first line of the key below the axis
    W = 183
    H = round(1.0 + 3.0 + max(h_left + 0.4 + below_axis, h_right + 0.4 + key_top + 4 * KEY + 1.2) + 1.0, 1)
    fig, ax = canvas(W, H)
    y0 = H - 4.0
    print("columns: left %.1f, right %.1f mm; figure height %.1f mm" % (h_left, h_right, H))

    # ------------------------------------------------------------------ a: all values published too high
    panel(ax, 1.5, y0, "a", "Published too high")
    L = Column(ax, 1.5, 54.0, 56.0, 87.0, 6, 38, 94.0)
    txt(ax, 100.5, y0 + 0.9, "published → certified", 5.2, MUTED, ha="right")
    L.start(y0 - 1.3)

    def too_high(paper, obj, name=None, label=None, tick=True):
        r = rows[(paper, obj)]
        assert r["verdict"] == "too_high", (paper, obj)
        used.append((paper, obj))
        s = label or obj.replace(" circuit", "").replace(" code", "")
        L.row(p, s, float(r["pub_lo"]), float(r["pub_hi"]), float(r["cert_lo"]), float(r["cert_hi"]), r["stated"], name,
              (tick if not isinstance(tick, bool) else code_distance(obj)) if tick else None)

    # rows not counted (verdict not_counted: a numbering the paper does not print, or no circuit distance printed) are only in
    # the Supplementary table
    M, MR = "Mitten codes", "Mitten codes (repository)"
    # papers in the order of the Results, largest losses first
    L.sub("circuit distance", first=True)
    too_high(M, "[[200,40,12]] circuit", "Mitten codes")
    too_high(M, "[[300,60,14]] circuit")
    too_high(M, "[[500,100,16]] circuit")
    too_high(M, "[[540,108,18]] circuit")
    too_high(M, "[[630,126,20]] circuit")
    too_high(M, "[[780,156,22]] circuit")
    too_high(M, "[[975,195,24]] circuit")
    L.y -= gap
    too_high("IBM bivariate bicycle codes", "[[288,12,18]] circuit", "Two-gross bicycle code", label="[[288,12,18]], IBM's bound")
    too_high("Distance-finding benchmark", "[[288,12,18]] circuit", label="[[288,12,18]], benchmark's best known", tick=18)
    L.y -= gap
    too_high("Cornucopia codes", "[[900,454,10]] circuit", "Cornucopia codes")
    too_high("Cornucopia codes", "[[1044,526,12]] circuit")
    too_high("Cornucopia codes", "[[2304,1156,16]] circuit", label="[[2304,1156,16]], Z basis")
    too_high("Cornucopia codes", "[[2844,1426,18]] circuit", label="[[2844,1426,18]], Z basis")
    L.y -= gap
    too_high("Routing codes", "[[200,24,14]] circuit", "Routing codes")
    too_high("Routing codes", "[[200,16,17]] circuit")
    L.y -= gap
    too_high("Shift automorphism circuits", "gross code, dynamic circuit", "Shift-automorphism circuit", label="gross code, dynamic", tick=12)
    L.y -= gap
    too_high("Walking Cat", "[[70,6,9]] circuit", "Walking Cat trapped-ion circuit")
    L.sub("code distance")
    too_high("Tile codes", "[[512,18]] code", "Tile code", tick=False)
    too_high("Nearest-neighbor planar codes", "[[259,2]] code, X distance", "Nearest-neighbor planar codes", label="[[259,2]], X distance", tick=False)
    too_high("Nearest-neighbor planar codes", "[[537,14]] code, X distance", label="[[537,14]], X distance", tick=False)
    too_high("Multivariate multicycle codes", "[[324,12]] code", "Multivariate multicycle code", tick=False)
    too_high(MR, "[[840,168,18]] code", "Mitten code, repository", tick=False)
    L.close()
    assert sorted(set(used)) == sorted(too_high_rows), set(too_high_rows) - set(used)

    # ------------------------------------------------------------------ d: Google's surface-code circuits, under a
    yd = L.y - 3.8
    panel(ax, 1.5, yd, "d", "Google's modular hyperbolic codes: surface-code circuits")
    L.start(yd - 1.0)
    L.sub("rebuilt circuits, NZ alternating", first=True)
    for lab, pub, ex, also in (("[[150,4,10]]", 8, 8, 9), ("[[200,6,10]]", 8, 8, 9), ("[[250,8,10]]", 8, 8, None), ("[[300,10,10]]", 8, 8, None)):
        L.row(p, lab, pub, pub, ex, ex, "bound", None, 10, also)
    L.sub("rebuilt circuits, ZZ alternating")
    for lab, pub, ex, also in (("[[150,4,10]]", 6, 6, 8), ("[[200,6,10]]", 8, 8, None), ("[[250,8,10]]", 6, 6, 8), ("[[300,10,10]]", 6, 6, 8)):
        L.row(p, lab, pub, pub, ex, ex, "bound", None, 10, also)
    L.close()
    assert abs(L.y - (y0 - h_left)) < 0.05, (L.y, y0 - h_left)
    L.axis((10, 15, 20, 25, 30, 35), "distance", L.y - 0.4)

    # ------------------------------------------------------------------ b: left open by other papers
    panel(ax, 103.0, y0, "b", "Left open by other papers: settled or narrowed")
    C = Column(ax, 103.0, 144.0, 146.0, 168.0, 5, 35, 175.4)
    txt(ax, 182.8, y0 + 0.9, "published → certified", 5.2, MUTED, ha="right")
    C.start(y0 - 1.3)
    done = []

    def settled(paper, obj, name, label, tick=None):
        r = rows[(paper, obj)]
        assert r["verdict"] == "settled" and r["cert_lo"] == r["cert_hi"], (paper, obj)
        done.append((paper, obj))
        C.row(p, label, float(r["pub_lo"]), float(r["pub_hi"]), float(r["cert_lo"]), float(r["cert_hi"]), r["stated"], name, tick)

    def wjh(label, key, lo, hi, name=None):
        C.row(p, label, bk[key], bk[key], lo, hi, "best_known", name)

    def tanner(label, key, x3, name=None):
        wjh(label if x3[1] else label + ", Z distance", key, x3[0], x3[0], name)

    C.sub("circuit distance", first=True)
    settled("Distance-finding benchmark", "superdense circuit, d = 11", "Superdense color code", "d = 11", 11)
    settled("Amplified qLDPC codes", "[[90,8,8]] level-1 circuit", "Amplified qLDPC code", "[[90,8,8]], level 1", 8)
    settled("Left-right circuits", "gross code, three-color circuit", "Three-color gross circuit", "[[144,12,12]]", 12)
    settled("Vine codes", "four patches of distance 10", "Vine planar-grid code", "four patches", 10)
    C.sub("code distance")
    tanner("[[288,2]]", "288_2_24", x288, "Quantum Tanner codes")
    tanner("[[324,4]]", "324_4_25", x324)
    tanner("[[360,4]]", "360_4_24", x360)
    tanner("[[396,4]]", "396_4_26", x396)
    wjh("[[648,4]]", "[[648,4,32]]", b648[0], b648[1], "Bivariate bicycle codes")
    wjh("[[756,16]]", "[[756,16,34]]", b756[0], b756[1])
    settled("Weight-8 bivariate bicycle codes", "[[144,10]] code", "Weight-8 bivariate bicycle", "[[144,10]]")
    settled("Weight-8 bivariate bicycle codes", "[[144,6]] code", None, "[[144,6]]")
    settled(MR, "[[300,60,9]] code", "Mitten code, repository", "[[300,60,9]]")
    C.close()
    assert sorted(done) == sorted(settled_rows), set(settled_rows) - set(done)

    # ------------------------------------------------------------------ c: Google's color codes, under b
    yc = C.y - 3.8
    panel(ax, 103.0, yc, "c", "Google's modular hyperbolic codes: color codes")
    C.start(yc - 1.0)
    hyp = sorted([r for r in rows.values() if r["paper"] == "Modular hyperbolic codes"], key=lambda r: (float(r["cert_hi"]), float(r["pub_lo"])))
    assert len(hyp) == 15
    C.sub("code distance", first=True)
    for r in hyp:
        C.row(p, r["object"].split(" ")[0], float(r["pub_lo"]), float(r["pub_hi"]), float(r["cert_lo"]), float(r["cert_hi"]), r["stated"])
    C.close()
    assert abs(C.y - (y0 - h_right)) < 0.05, (C.y, y0 - h_right)
    ybr = C.y - 0.4
    C.axis((10, 15, 20, 25, 30, 35), "distance", ybr)

    # key, in two columns under the right column's axis: symbol in a 4 mm slot, text after it
    def key(x, y, kind, label):
        if kind == "pub":
            ax.scatter([x + 2.0], [y], s=11, facecolors=WHITE, edgecolors=INK2, linewidths=0.6)
        elif kind == "cert":
            ax.scatter([x + 2.0], [y], s=11, color=BLUE, edgecolors=WHITE, linewidths=0.4)
        elif kind == "other":
            ax.scatter([x + 2.0], [y], s=9, marker="D", color=BLUE_LIGHT, edgecolors=WHITE, linewidths=0.3)
        elif kind == "tick":
            ax.plot([x + 2.0] * 2, [y - 1.0, y + 1.0], color=INK, lw=0.7, solid_capstyle="butt")
        elif kind in ("range", "interval"):
            ax.plot([x, x + 4.0], [y, y], color=GRAY_LIGHT if kind == "range" else BLUE, lw=2.0, solid_capstyle="round")
        elif kind == "gap":
            ax.plot([x, x + 4.0], [y, y], color=ORANGE, lw=0.8)
        txt(ax, x + 5.4 if kind else x, y, label, 5.4)

    k1, k2 = 104.0, 144.0
    for i, entries in enumerate(((("pub", "published value"), ("range", "published range")),
                                 (("cert", "certified value"), ("interval", "certified interval, not closed")),
                                 (("gap", "gap to the published value"), ("tick", "code distance")),
                                 (("other", "other valid schedule"),),
                                 ((None, "≤ bound   ≈ estimate   ≥ lower bound   ? conjecture"),))):
        for kx, (kind, label) in zip((k1, k2), entries):
            key(kx, ybr - key_top - i * KEY, kind, label)
    assert ybr - key_top - 4 * KEY > 1.5 and y0 - h_left - 0.4 - below_axis > 0.5

    print("rows a", len(used), "rows b", len(done) + 6)
    save(fig, "ncs_fig3")


def fig_hook():
    """Supplementary figure: the minimum fault set of the structured mitten [[330,66,12]] circuit (formerly
    panel c of figure 3)."""
    ex = hook_example()
    W, H = 183, 40
    fig, ax = canvas(W, H)
    txt(ax, 2.0, 36.6, "one row per Z check, its nine gates in schedule order", 5.4, MUTED)
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
        txt(ax, tx + k * tw + tw / 2, 22.5, big, 9.0, col, ha="center", fontweight="bold")
        txt(ax, tx + k * tw + tw / 2, 17.5, lab.replace(" ", "\n", 1), 5.4, INK2, ha="center", va="top", linespacing=1.05)
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


def fig_design_si():
    """Supplementary figure: certified design of syndrome-extraction circuits (a, b) and the memory instruction of IBM's bicycle
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
            axa.scatter([d], [y], s=0.45 * area(c), color=INK2, edgecolors="none", zorder=3)
        axa.plot([r["dcode"]] * 2, [y - 0.36, y + 0.36], color=INK2, lw=0.8, zorder=4)
        best = max(r["all"])
        axa.scatter([best], [y], s=area(r["all"][best]) + 14, facecolors="none", edgecolors=BLUE, linewidths=0.9,
                    zorder=5)
        txt(axa, best + 0.32, y - 0.02, "{:,}".format(r["all"][best]), 5.0, BLUE, fontweight="bold")
        if r["dstd"] is not None:
            axa.scatter([r["dstd"]], [y - 0.47], marker="v", s=9, color=INK2, edgecolors="none", zorder=5)
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
    ax.scatter([lx + 36.0], [ly], s=10, color=INK2, edgecolors="none")
    txt(ax, lx + 37.6, ly, "standard family", 4.9, INK2)
    ax.scatter([lx + 54.0], [ly], marker="v", s=9, color=INK2, edgecolors="none")
    txt(ax, lx + 55.4, ly, "standard schedule", 4.9, INK2)
    ax.scatter([lx + 73.0], [ly], s=20, facecolors="none", edgecolors=BLUE, linewidths=0.9)
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
    axb.legend(hd, ["best sequential circuit", "parallel circuit, this work"], loc="upper right", fontsize=5.2,
               handlelength=1.1, borderaxespad=0.2, labelspacing=0.3)

    # ------------------------------------------------------------------ IBM's bicycle architecture
    cur = json.load(open(IBM_DIR / "curves.json"))
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
        col = BLUE
        if assumed is not None:
            axc.scatter([x], [assumed], s=26, marker="s", facecolors=WHITE, edgecolors=INK2, linewidths=0.8, zorder=4)
        if assumed is not None and assumed != cert:
            axc.annotate("", (x, cert + 0.5), xytext=(x, assumed - 0.5),
                         arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=0.8, mutation_scale=5))
        axc.scatter([x], [cert], s=24, color=col, edgecolors=WHITE, linewidths=0.5, zorder=5)
        txt(axc, x + 0.13, cert, "%d" % cert, 5.2, col, fontweight="bold")
    axc.set_xticks(range(3))
    axc.set_xticklabels([r[0] for r in drows], fontsize=5.2, linespacing=1.0)
    axc.set_xlim(-0.5, 2.6)
    axc.set_ylim(8.0, 21.5)
    axc.set_yticks([8, 12, 16, 20])
    axc.set_ylabel("circuit distance")
    tidy(axc)
    h = [Line2D([], [], ls="", marker="s", ms=3.4, markerfacecolor=WHITE, markeredgecolor=INK2),
         Line2D([], [], ls="", marker="o", ms=3.4, color=BLUE)]
    axc.legend(h, ["assumed by IBM", "certified"], loc="upper left", fontsize=5.2, ncol=2, handletextpad=0.2,
               columnspacing=0.7, borderaxespad=0.2)

    # ------------------------------------------------------------------ d: two-gross, bounds against the extrapolation
    panel(ax, 63.5, row2, "d", "Two-gross code: bounds for every decoder")
    axd = axes_mm(fig, 75.0, 11.0, 46.0, 43.0)
    fit = json.load(open(MATCHED_DIR / "fit_tour_de_gross.json"))
    bounds = fit["bounds"]
    keep = [k for k, p in enumerate(bounds["16"]["p"]) if 4e-5 <= p <= 1.4e-3]
    bp = [bounds["16"]["p"][k] for k in keep]
    lb16, lb18 = ([bounds[w]["log10_per_cycle_two_bases"][k] for k in keep] for w in ("16", "18"))
    top = [max(v) for v in zip(lb16, lb18)]
    axd.fill_between(bp, [1e-60] * len(bp), [10 ** v for v in top], color=BLUE, alpha=0.10, lw=0, zorder=1)
    axd.plot(bp, [10 ** v for v in lb18], color=BLUE, lw=1.4, zorder=3)
    axd.plot(bp, [10 ** v for v in lb16], color=BLUE, lw=0.9, ls=(0, (1.2, 1.2)), zorder=3)
    axd.plot(fit["curve"]["p"], [10 ** v for v in fit["curve"]["log10_rate"]], color=INK2, lw=0.9, ls=(0, (3, 2)),
             zorder=2)
    table2 = {float(k): v for k, v in fit["reproduced"]["two-gross idle"].items()}
    for p, v in table2.items():
        axd.plot([p, p], [10 ** (v["table_2"] - v["uncertainty"]), 10 ** (v["table_2"] + v["uncertainty"])],
                 color=INK2, lw=0.6, zorder=4)
    axd.scatter(list(table2), [10 ** v["table_2"] for v in table2.values()], s=20, marker="s", facecolors=WHITE,
                edgecolors=INK2, linewidths=0.8, zorder=5)
    b4, t4 = top[bp.index(1e-4)], table2[1e-4]["table_2"]
    axd.annotate("", (1e-4, 10 ** (b4 - 0.15)), xytext=(1e-4, 10 ** (t4 + 0.5)),
                 arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=0.8, mutation_scale=5, shrinkA=0, shrinkB=0))
    txt(axd, 9.2e-5, 10 ** ((b4 + t4) / 2), "%.0f\norders" % (b4 - t4), 5.0, ORANGE, ha="right", fontweight="bold",
        linespacing=1.05)
    txt(axd, 1.4e-3, 10 ** -41.3, "impossible for every decoder", 4.9, BLUE, ha="right", va="center", alpha=0.85)
    hd = [Line2D([], [], color=BLUE, lw=1.4), Line2D([], [], color=BLUE, lw=0.9, ls=(0, (1.2, 1.2))),
          Line2D([], [], color=INK2, lw=0.9, ls=(0, (3, 2)), marker="s", ms=3.2, markerfacecolor=WHITE,
                 markeredgecolor=INK2, markeredgewidth=0.7)]
    axd.legend(hd, ["bound, weight-18 code logicals", "bound, weight-16 fault sets", "extrapolated by IBM"],
               loc="upper left", fontsize=5.2, handlelength=2.0, borderaxespad=0.2, labelspacing=0.35)
    axd.set_xscale("log")
    axd.set_yscale("log")
    axd.xaxis.set_minor_locator(NullLocator())
    axd.yaxis.set_minor_locator(NullLocator())
    axd.set_xlim(bp[0] * 0.9, bp[-1] * 1.1)
    axd.set_ylim(1e-43, 1e-16)
    axd.set_yticks([1e-40, 1e-35, 1e-30, 1e-25, 1e-20])
    axd.set_xlabel("physical error rate p")
    axd.set_ylabel("logical error rate per cycle")
    tidy(axd)

    # ------------------------------------------------------------------ e: gross code, standard against best
    panel(ax, 124.5, row2, "e", "Gross code: what distance 11 gains")
    axe = axes_mm(fig, 136.0, 11.0, 45.0, 43.0)
    sims = {}
    for line in open(MATCHED_DIR / "sim_gross_c10.jsonl"):
        r = json.loads(line)
        sims.setdefault(r["schedule"], {}).setdefault(r["p"], {})[r["basis"]] = r
    mwd = json.load(open(MATCHED_DIR / "mwd_gross_c10.json"))
    lp = [p for p in mwd["p"] if 4e-5 <= p <= 5e-4]
    tot = {}
    for e in mwd["entries"]:
        for p in lp:
            r = e["rates"][str(p)]
            t = tot.setdefault(e["schedule"], {}).setdefault(p, [0.0, 0.0])
            t[0] += 10 ** r["log10_total_per_cycle"]
            t[1] += 10 ** r["log10_w5"] / e["cycles"]
    TAG8, TAG9 = "s561234_324015", ent[("gross", "best")]["schedule"]
    for tag, col, lab, lw in (("standard", INK2, "standard, d = 10", 1.3), (TAG8, BLUE, "d = 11, 8 timesteps", 1.3),
                              (TAG9, BLUE_LIGHT, "d = 11, 9 timesteps", 1.3)):
        axe.plot(lp, [tot[tag][p][0] for p in lp], color=col, lw=lw, zorder=3)
        pts = sorted((p, v) for p, v in sims.get(tag, {}).items() if len(v) == 2)
        xs = [p for p, _ in pts]
        cyc = [v["Z"]["cycles"] for _, v in pts]
        ys2 = [sum(v[b]["rate"] for b in "ZX") / c for (_, v), c in zip(pts, cyc)]
        er = [math.sqrt(sum(v[b]["failures"] / v[b]["shots"] ** 2 for b in "ZX")) / c for (_, v), c in zip(pts, cyc)]
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
    gain = [tot["standard"][1e-4][0] / tot[t][1e-4][0] for t in (TAG8, TAG9)]
    txt(axe, 1.5e-4, tot[TAG8][2e-4][0] / 400, "at $p=10^{-4}$: %.0f× lower (8 timesteps),\n%.0f× lower (9 timesteps)" % tuple(gain), 4.9,
        BLUE, ha="left", fontweight="bold", linespacing=1.05)
    txt(axe, 4.5e-5, 2e-11, "expansion to $p^{6}$,\nminimum-weight\ndecoder", 4.5, MUTED, ha="left", linespacing=1.05)
    txt(axe, 4.6e-3, 1e-7, "BP-OSD\nsimulation", 4.5, MUTED, ha="center", linespacing=1.05)
    axe.set_xscale("log")
    axe.set_yscale("log")
    axe.xaxis.set_minor_locator(NullLocator())
    axe.yaxis.set_minor_locator(NullLocator())
    axe.set_xlim(4e-5, 1.2e-2)
    axe.set_ylim(1e-20, 1)
    axe.set_yticks([1e-20, 1e-15, 1e-10, 1e-5, 1])
    axe.set_xlabel("physical error rate p")
    axe.set_ylabel("logical error rate per cycle")
    axe.legend(loc="upper left", fontsize=5.2, handlelength=1.0, borderaxespad=0.2, labelspacing=0.3)
    tidy(axe)
    save(fig, "si_design")


# ---------------------------------------------------------------------------------------------------- Fig. 4
CAND = "046135_531620"       # the two-gross schedule with px = (0,4,6,1,3,5), pz = (5,3,1,6,2,0)


def tint(hexcolor, f):
    """The color mixed with white, f = 1 being the color itself."""
    c = [int(hexcolor[k:k + 2], 16) for k in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(255 + (x - 255) * f) for x in c)


D11, D10, D9, DLOW = BLUE, tint(BLUE, 0.58), tint(BLUE, 0.24), ORANGE


def f4_schedules(ax, top):
    panel(ax, 1.5, top, "a", "The schedule sets the circuit distance")
    rows = []
    for key, name, dc in (("bb72", "[[72,12,6]]", 6), ("bb90", "[[90,8,10]]", 10), ("bb108", "[[108,8,10]]", 10),
                          ("gross", "[[144,12,12]] gross", 12)):
        allr = json.load(open(ROOT / ("results/papers3/bb6/%s_all.json" % key)))
        s_ = allr["standard_schedule"]
        rows.append(dict(name=name, dcode=dc, dstd=min(s_["X"][0], s_["Z"][0]),
                         all={int(d): c for d, c in allr["circuit_distance_histogram"].items()}))
    assert all(sum(r["all"].values()) == 8496 for r in rows)
    # two-gross: the standard schedule exact in both bases; every other schedule at one cycle (results/bb288_scan/tally_scan.py)
    two = [json.load(open(ROOT / ("results/ibm/pipe_bb288_standard_c1_%s.json" % b))) for b in "XZ"]
    assert all(r["status"] == "exact" and r["lower_bound"] == r["upper_bound"] == 16 for r in two)
    scan = json.load(open(ROOT / "results/bb288_scan/scan_table.json"))
    assert scan["best"] == 18 and scan["worst"] == 12

    x0, x1, dmin, dmax = 33.0, 93.0, 3, 18
    Xd = lambda d: x0 + (d - dmin) * (x1 - x0) / (dmax - dmin)
    xc1, xc2 = x1 + 7.0, x1 + 13.5
    ly = top - 5.0
    lx = 4.0
    ax.plot([lx, lx + 5], [ly, ly], color=GRAY_LIGHT, lw=2.6, solid_capstyle="round")
    txt(ax, lx + 6.4, ly, "all 8,496 schedules, worst to best", 5.0)
    ax.scatter([lx + 37.5], [ly], s=13, facecolors=WHITE, edgecolors=INK2, linewidths=0.7)
    txt(ax, lx + 38.9, ly, "standard schedule", 5.0)
    ax.scatter([lx + 55.5], [ly], s=15, color=BLUE, edgecolors=WHITE, linewidths=0.4)
    txt(ax, lx + 56.9, ly, "best schedule", 5.0)
    ax.plot([lx + 70.5] * 2, [ly - 1.2, ly + 1.2], color=INK, lw=0.9)
    txt(ax, lx + 71.9, ly, "code distance", 5.0)
    txt(ax, xc1, ly, "standard\n→ best", 4.8, MUTED, fontweight="bold", ha="center", linespacing=1.0)
    txt(ax, xc2, ly, "schedules reaching\nthe best", 5.0, MUTED, fontweight="bold", linespacing=1.0)
    pitch = 5.5
    y = top - 8.0
    ytop = y
    txt(ax, 4.0, y - 1.5, "memory circuits, six rounds", 5.4, MUTED, fontweight="bold")
    y -= 3.0
    for r in rows:
        ym = y - pitch / 2
        lo, best = min(r["all"]), max(r["all"])
        gross = "gross" in r["name"]
        txt(ax, x0 - 1.5, ym, r["name"], 5.4, INK, ha="right", fontweight="bold" if gross else "normal")
        ax.plot([Xd(lo), Xd(best)], [ym, ym], color=GRAY_LIGHT, lw=2.6, solid_capstyle="round", zorder=2)
        ax.plot([Xd(r["dcode"])] * 2, [ym - 1.5, ym + 1.5], color=INK, lw=0.9, zorder=3)
        if r["dstd"] != best:
            ax.plot([Xd(r["dstd"]), Xd(best)], [ym, ym], color=BLUE, lw=2.6, solid_capstyle="butt", zorder=3)
            ax.scatter([Xd(r["dstd"])], [ym], s=13, facecolors=WHITE, edgecolors=INK2, linewidths=0.7, zorder=4)
        ax.scatter([Xd(best)], [ym], s=16, color=BLUE, edgecolors=WHITE, linewidths=0.4, zorder=5)
        if r["dstd"] == best:
            ax.scatter([Xd(best)], [ym], s=26, facecolors="none", edgecolors=INK2, linewidths=0.7, zorder=6)
        better = r["dstd"] != best
        txt(ax, xc1, ym, "%d → %d" % (r["dstd"], best), 5.2, BLUE if better else INK2, ha="center", fontweight="bold" if better else "normal")
        txt(ax, xc2, ym, "{:,} of 8,496".format(r["all"][best]), 4.9, INK2)
        y -= pitch
    txt(ax, 4.0, y - 1.5, "memory instruction, one noisy cycle", 5.4, MUTED, fontweight="bold", bbox=dict(facecolor=WHITE, edgecolor="none", pad=0.6), zorder=1)
    y -= 3.0
    ym = y - pitch / 2
    txt(ax, x0 - 1.5, ym, "[[288,12,18]] two-gross", 5.4, INK, ha="right", fontweight="bold")
    ax.plot([Xd(scan["worst"]), Xd(scan["best"])], [ym, ym], color=GRAY_LIGHT, lw=2.6, solid_capstyle="round", zorder=2)
    ax.plot([Xd(18)] * 2, [ym - 1.5, ym + 1.5], color=INK, lw=0.9, zorder=3)
    ax.plot([Xd(16), Xd(18)], [ym, ym], color=BLUE, lw=2.6, solid_capstyle="butt", zorder=3)
    ax.scatter([Xd(16)], [ym], s=13, facecolors=WHITE, edgecolors=INK2, linewidths=0.7, zorder=4)
    ax.scatter([Xd(18)], [ym], s=16, color=BLUE, edgecolors=WHITE, linewidths=0.4, zorder=5)
    txt(ax, xc1, ym, "16 → 18", 5.2, BLUE, ha="center", fontweight="bold")
    txt(ax, xc2, ym, "{:,}{} of 8,496".format(scan["n_best"], "+" if scan["open"] else ""), 4.9, INK2)
    y -= pitch
    yb = y - 0.2
    for d in range(dmin, dmax + 1):
        ax.plot([Xd(d)] * 2, [yb, ytop], color=GRID, lw=0.45, zorder=0)
        txt(ax, Xd(d), yb - 1.6, str(d), 5.0, INK2, ha="center")
    ax.plot([x0, x1], [yb, yb], color=AXIS, lw=0.55, zorder=1)
    txt(ax, (x0 + x1) / 2, yb - 3.9, "circuit distance", 5.4, INK2, ha="center")
    return yb - 3.9


def f4_limit_line():
    """The limit from the code's weight-18 logical operators on the new schedule's circuit, both bases (results/bb288_scan/limit)."""
    rates = [json.load(open(ROOT / ("results/bb288_scan/limit/bb288_s%s_w18_c18_%s.json" % (CAND, b))))["C18"]["rates"] for b in "XZ"]
    ps = sorted(rates[0], key=float)
    return [float(x) for x in ps], [math.log10(sum(10 ** r[x]["log10_lower_bound_per_cycle"] for r in rates)) for x in ps]


SURGERY_DIR = ROOT / "results" / "surgery"
# rows of the logical-measurement panel: SSIP scripts (results/surgery/ssip_summary.json) and the size unit of their ancilla figure
SSIP_ROWS = (("external merges", ["ext_merges"]), ("internal merges", ["int_merges"]), ("single-qubit", ["singleqs"]),
             ("parallel", ["par_ext_merges", "par_singleqs"]))
SSIP_UNIT = {"ext_merges": 288, "par_ext_merges": 288, "int_merges": 144, "singleqs": 144, "par_singleqs": 144}


def surgery_rows():
    """Adapter codes and SSIP's gross-code measurements: per row the measurements, how many keep dressed distance 12 at the
    published depth, the least dressed distance there, and the ancilla qubits at the published and at the dressed depths."""
    ad = json.load(open(SURGERY_DIR / "adapters.json"))
    reported = {"BB98_original": 12, "LP200_original": 10, "BB98_Z1": 12, "BB98_Z3": 12, "BB98_Z1Z3_naive": 12, "LP200_Z2": 10,
                "BB98_intracode_Z1Z3": 12, "BB98_LP200_intercode_Z1Z2": 10}
    assert set(ad) == set(reported) and all(r["d"] == reported[k] for k, r in ad.items())
    adapters = {"label": "adapter codes", "n": len(ad), "keep": len(ad), "least": min(r["d"] for r in ad.values()),
                "anc": None, "codes": ad}
    summ = json.load(open(SURGERY_DIR / "ssip_summary.json"))
    rows = []
    for label, scripts in SSIP_ROWS:
        n = keep = 0
        least, a0, a1, complete = 99, 0.0, 0.0, True
        fixed, prep = 99, True
        for s in scripts:
            for f in summ[s]["files"].values():
                assert f["bare_at_least_12"]
                n += f["measurements"]
                keep += f["measurements"] - f["dressed_below_12_at_ssip_depth"]
                least = min(least, f["least_dressed_at_ssip_depth"])
                # gauge logicals of the other basis fixed (by the preparation of the new qubits, papers/ssip_gauge_fix.py)
                fixed = min(fixed, f["least_gauge_fixed_at_ssip_depth"])
                prep = prep and f.get("fixed_by_preparation") == f["measurements"]
                if "size_sum_dressed" in f:
                    a0 += f["size_sum_ssip"] * SSIP_UNIT[s]
                    a1 += f["size_sum_dressed"] * SSIP_UNIT[s]
                else:
                    complete = False
        rows.append({"label": label, "n": n, "keep": keep, "least": least, "fixed": fixed, "prep": prep,
                     "anc": (round(a0), round(a1)) if complete else None})
    return adapters, rows


def f4_surgery(ax, top, ybottom):
    """Panel b: do the codes of published logical measurements keep the distance?  Adapter codes certified as published;
    SSIP's merged gross-code blocks keep 12 with the gauge logicals of the other basis fixed, as the preparation of the
    new qubits does, and fall below 12 with the gauge qubits free (the dressed distance of its Appendix A)."""
    panel(ax, 123.5, top, "b", "Logical measurements: certified merged codes")
    adapters, rows = surgery_rows()
    assert all(r["prep"] and r["fixed"] >= 12 for r in rows)
    x0, x1 = 146.0, 162.0
    xl, xa, xf = 165.6, 174.6, 180.4               # columns: least and ancilla with the gauge free, distance with it fixed
    ly = top - 5.0
    for x, c, lab in ((126.0, BLUE, "distance kept"), (146.0, ORANGE, "distance below 12")):
        ax.add_patch(Rectangle((x, ly - 1.0), 2.4, 2.0, facecolor=c, edgecolor="none", zorder=3))
        txt(ax, x + 3.1, ly, lab, 4.8)
    hy = ly - 5.2
    txt(ax, (x0 + x1) / 2, hy + 2.1, "gauge qubits free", 4.5, MUTED, ha="center", fontweight="bold")
    ax.plot([x0, xa + 0.4], [hy + 1.0, hy + 1.0], color=MUTED, lw=0.4)
    txt(ax, xf, hy + 2.1, "gauge", 4.5, MUTED, ha="center", fontweight="bold")
    txt(ax, xl, hy - 0.4, "least", 4.5, MUTED, ha="center", fontweight="bold")
    txt(ax, xa, hy - 0.4, "ancilla", 4.5, MUTED, ha="right", fontweight="bold")
    txt(ax, xf, hy - 0.4, "fixed", 4.5, MUTED, ha="center", fontweight="bold")
    pitch, hbar = 5.0, 3.1
    y = hy - 1.8

    def row(lab, sub, r, right2, least=None, fixed=""):
        nonlocal y
        ym = y - pitch / 2
        txt(ax, x0 - 1.4, ym + 0.75, lab, 5.0, INK, ha="right")
        txt(ax, x0 - 1.4, ym - 1.35, sub, 4.3, MUTED, ha="right")
        wk = (x1 - x0) * r["keep"] / r["n"]
        if r["keep"]:
            ax.add_patch(Rectangle((x0, ym - hbar / 2), max(wk - 0.25, 0.2), hbar, facecolor=BLUE, edgecolor="none", zorder=3))
            if wk > 4.0:
                txt(ax, x0 + wk / 2, ym - 0.05, str(r["keep"]), 4.6, WHITE, ha="center", zorder=4)
        if r["keep"] < r["n"]:
            ax.add_patch(Rectangle((x0 + wk, ym - hbar / 2), x1 - x0 - wk, hbar, facecolor=ORANGE, edgecolor="none", zorder=3))
            if x1 - x0 - wk > 4.0:
                txt(ax, x0 + wk + (x1 - x0 - wk) / 2, ym - 0.05, str(r["n"] - r["keep"]), 4.6, WHITE, ha="center", zorder=4)
        if least is None:
            txt(ax, xl, ym, str(r["least"]), 5.0, ORANGE if r["least"] < 12 else BLUE, ha="center", fontweight="bold")
        else:
            txt(ax, xl, ym, least, 4.8, BLUE, ha="center", fontweight="bold")
        txt(ax, xa, ym, right2, 4.6, INK2, ha="right")
        txt(ax, xf, ym, fixed, 5.0, BLUE, ha="center", fontweight="bold")
        y -= pitch

    ds = sorted({c["d"] for c in adapters["codes"].values()})
    n_orig = sum(k.endswith("_original") for k in adapters["codes"])
    row("adapter codes", "%d merged + %d original" % (adapters["n"] - n_orig, n_orig), adapters, "", "%d–%d" % (ds[0], ds[-1]))
    txt(ax, x0 - 1.4, y - 1.2, "SSIP, gross-code surgery", 4.6, INK2, ha="right", fontweight="bold")
    y -= 2.2
    for r in rows:
        anc = "×%.1f" % (r["anc"][1] / r["anc"][0]) if r["anc"] else "–"
        row(r["label"], "%d measurements" % r["n"], r, anc, fixed=str(r["fixed"]))
    yn = y - 2.1
    assert yn - 2.2 > ybottom - 2.0, "notes run into the panel below"
    txt(ax, 125.0, yn, "gauge fixed by preparing the new qubits", 4.5, MUTED, ha="left")
    txt(ax, 125.0, yn - 2.2, "bare distance 12 in all, as SSIP reports", 4.5, MUTED, ha="left")


def limit_axes(fig, x, y, w, h):
    """The two-gross limit plot (formerly Fig. 4b, now a supplementary figure) on axes at (x, y, w, h) mm."""
    axb = axes_mm(fig, x, y, w, h)
    fit = json.load(open(MATCHED_DIR / "fit_tour_de_gross.json"))
    ps, vals = f4_limit_line()
    keep = [k for k, p in enumerate(ps) if 4e-5 <= p <= 1.4e-3]
    bp = [ps[k] for k in keep]
    lb = [vals[k] for k in keep]
    axb.fill_between(bp, [1e-60] * len(bp), [10 ** v for v in lb], color=BLUE, alpha=0.10, lw=0, zorder=1)
    axb.plot(bp, [10 ** v for v in lb], color=BLUE, lw=1.4, zorder=3)
    axb.plot(fit["curve"]["p"], [10 ** v for v in fit["curve"]["log10_rate"]], color=INK2, lw=0.9, ls=(0, (3, 2)), zorder=2)
    table2 = {float(k): v for k, v in fit["reproduced"]["two-gross idle"].items()}
    for p, v in table2.items():
        axb.plot([p, p], [10 ** (v["table_2"] - v["uncertainty"]), 10 ** (v["table_2"] + v["uncertainty"])], color=INK2, lw=0.6, zorder=4)
    axb.scatter(list(table2), [10 ** v["table_2"] for v in table2.values()], s=18, marker="s", facecolors=WHITE, edgecolors=INK2,
                linewidths=0.8, zorder=5)
    b4, t4 = lb[bp.index(1e-4)], table2[1e-4]["table_2"]
    print("limit at 1e-4 %.2f, IBM %.1f, gap %.2f, from the bar's edge %.2f" % (b4, t4, b4 - t4, b4 - (t4 + table2[1e-4]["uncertainty"])))
    axb.annotate("", (1e-4, 10 ** (b4 - 0.15)), xytext=(1e-4, 10 ** (t4 + 0.6)),
                 arrowprops=dict(arrowstyle="<->", color=ORANGE, lw=0.8, mutation_scale=5, shrinkA=0, shrinkB=0))
    txt(axb, 9.2e-5, 10 ** ((b4 + t4) / 2), "%d\norders" % round(b4 - t4), 5.0, ORANGE, ha="right", fontweight="bold", linespacing=1.05)
    k = bp.index(3e-4)
    txt(axb, bp[k] * 0.86, 10 ** (lb[k] + 1.1), r"$\propto p^{9}$", 5.4, BLUE, ha="right", fontweight="bold")
    txt(axb, 1.3e-3, 10 ** -40.6, "no decoder can reach this region", 4.9, BLUE, ha="right", va="center", alpha=0.9)
    hd = [Line2D([], [], color=BLUE, lw=1.4),
          Line2D([], [], color=INK2, lw=0.9, ls=(0, (3, 2)), marker="s", ms=3.0, markerfacecolor=WHITE, markeredgecolor=INK2, markeredgewidth=0.7)]
    axb.legend(hd, ["limit from weight-18 logical operators", "IBM's extrapolation"], loc="upper left", fontsize=5.2, handlelength=1.9,
               borderaxespad=0.15, labelspacing=0.3)
    axb.set_xscale("log")
    axb.set_yscale("log")
    axb.xaxis.set_minor_locator(NullLocator())
    axb.yaxis.set_minor_locator(NullLocator())
    axb.set_xlim(bp[0] * 0.9, bp[-1] * 1.1)
    axb.set_ylim(1e-43, 1e-14)
    axb.set_yticks([1e-40, 1e-30, 1e-20])
    axb.set_xlabel("physical error rate p")
    axb.set_ylabel("logical error rate per cycle")
    tidy(axb)


ADAPTER_NAMES = {"BB98_original": r"bivariate bicycle \qc{98,6,12}", "LP200_original": r"lifted product \qc{200,20,10}",
                 "BB98_Z1": r"BB, auxiliary graph for $\bar Z_1$", "BB98_Z3": r"BB, auxiliary graph for $\bar Z_3$",
                 "BB98_Z1Z3_naive": r"BB, joint $\bar Z_1\bar Z_3$, naive", "LP200_Z2": r"LP, auxiliary graph for $\bar Z_2$",
                 "BB98_intracode_Z1Z3": r"BB, intracode adapter, $\bar Z_1\bar Z_3$",
                 "BB98_LP200_intercode_Z1Z2": r"BB and LP, intercode adapter, $\bar Z_1\bar Z_2$"}
SSIP_NAMES = {"ext_merges": "external merges", "int_merges": "internal merges", "singleqs": "single-qubit measurements",
              "par_ext_merges": "parallel external merges", "par_singleqs": "parallel single-qubit measurements"}


def surgery_tables(out):
    """Supplementary tables of the logical-measurement codes and the macros \\surg* and \\ssip* for the text
    (results/surgery/adapters.json, results/surgery/ssip_summary.json)."""
    adapters, rows = surgery_rows()
    head = "% generated by docs/make_ncs_figures.py from results/surgery; do not edit\n"
    lines = [r"\begin{tabular}{@{}lrrcc@{}}", r"\toprule", r"code & $n$ & $k$ & $d_X$ & $d_Z$ \\", r"\midrule"]
    for key, name in ADAPTER_NAMES.items():
        r = adapters["codes"][key]
        lines.append(r"%s & %d & %d & %d & %d \\" % (name, r["n"], r["k"], r["d_X"]["distance"], r["d_Z"]["distance"]))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_surgery_adapters_table.tex").write_text(head + "\n".join(lines) + "\n")
    summ = json.load(open(SURGERY_DIR / "ssip_summary.json"))
    lines = [r"\begin{tabular}{@{}llrcrrrrr@{}}", r"\toprule",
             r" & & & published & \multicolumn{2}{c}{dressed at published depth} & deeper & ancilla qubits & gauge \\",
             r"measurement & basis & number & depths & below 12 & least & with dressed & published $\to$ dressed & fixed \\",
             r"\midrule"]
    for s, name in SSIP_NAMES.items():
        for fname, f in summ[s]["files"].items():
            basis = "X" if "_X_" in fname else "Z"
            depths = sorted({x["r_ssip"] for x in f["rows"]})
            dep = "%d" % depths[0] if len(depths) == 1 else "%d--%d" % (depths[0], depths[-1])
            if "size_sum_dressed" in f:
                deeper = str(f["deeper_with_dressed"])
                anc = r"{:,} $\to$ {:,}".format(round(f["size_sum_ssip"] * SSIP_UNIT[s]), round(f["size_sum_dressed"] * SSIP_UNIT[s]))
            else:
                deeper, anc = "--", r"{:,} $\to$ --".format(round(sum(x["size_ssip"] for x in f["rows"]) * SSIP_UNIT[s]))
            assert f["fixed_by_preparation"] == f["measurements"]
            lines.append(r"%s & $%s$ & %d & %s & %d & %d & %s & %s & %d \\" % (name, basis, f["measurements"], dep,
                                                                              f["dressed_below_12_at_ssip_depth"],
                                                                              f["least_dressed_at_ssip_depth"], deeper, anc,
                                                                              f["least_gauge_fixed_at_ssip_depth"]))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_surgery_ssip_table.tex").write_text(head + "\n".join(lines) + "\n")
    n = sum(r["n"] for r in rows)
    below = sum(r["n"] - r["keep"] for r in rows)
    comp = [r for r in rows if r["anc"]]
    assert len(comp) == len(rows), "the paper gives the ancilla qubits in total, over all measurements"
    assert all(r["prep"] and r["fixed"] >= 12 for r in rows), "the paper says every merged code keeps 12 with the gauge fixed"
    a0, a1 = sum(r["anc"][0] for r in comp), sum(r["anc"][1] for r in comp)
    macros = {"surgAdapters": adapters["n"], "ssipN": n, "ssipBelow": below, "ssipLeast": min(r["least"] for r in rows),
              "ssipAncFrom": "{:,}".format(a0), "ssipAncTo": "{:,}".format(a1), "ssipAncN": sum(r["n"] for r in comp)}
    (out / "si_surgery_numbers.tex").write_text(head + "".join(r"\newcommand{\%s}{%s}" % (k, v) + "\n" for k, v in macros.items()))
    print("surgery: adapters %d; SSIP %d measurements, %d with dressed distance below 12, least %d; ancilla %d -> %d over %d" % (
        adapters["n"], n, below, macros["ssipLeast"], a0, a1, macros["ssipAncN"]))


def fig_limit_si():
    """Supplementary figure: the decoder-independent limit on the two-gross code's logical error rate against the published
    extrapolation (results/bb288_scan/limit, results/ibm_matched/fit_tour_de_gross.json)."""
    W, H = 92, 62
    fig, ax = canvas(W, H)
    limit_axes(fig, 14.0, 10.0, 75.0, 49.0)
    save(fig, "si_limit")


def f4_chips(ax, top, tab, n, res, best8):
    panel(ax, 1.5, top, "c", "Gross-code chips with dead checks")
    S0, S1 = None, best8
    # more dead checks are in the yields of panel d; chips with 5 or fewer cover 99.97% of chips at 99.98% junction yield
    ms = [m for m in sorted(tab[S1]) if m in tab[S0] and m <= 5]
    assert set(n.values()) == {200}
    xa, xb, wbar = 26.0, 68.0, 38.0
    xs = 118.5
    # legend of the distances
    ly = top - 5.0
    txt(ax, 26.0, ly, "certified lower bound on the distance", 5.2, INK2)
    lx = 62.0
    for c, lab, step in ((D11, "11", 9.0), (D10, "10", 9.0), (D9, "9", 7.5), (DLOW, "8 or less", 0)):
        ax.add_patch(Rectangle((lx, ly - 1.0), 2.4, 2.0, facecolor=c, edgecolor="none", zorder=3))
        txt(ax, lx + 3.1, ly, lab, 5.0)
        lx += step
    hy = top - 9.0
    txt(ax, xa, hy, "Standard schedule", 5.3, INK, fontweight="bold")
    txt(ax, xb, hy, "Distance-11 schedule", 5.3, BLUE, fontweight="bold")
    txt(ax, xs, hy, "chips at 99.98%\njunction yield", 4.6, MUTED, ha="right", fontweight="bold", linespacing=1.0)
    pitch, hbar = 4.7, 3.3
    y = hy - 2.2
    share = res["yields"]["0.9998"]["share_by_m"]
    names = {0: "no dead check", 1: "1 dead check"}
    for m in ms:
        ym = y - pitch / 2
        txt(ax, xa - 1.5, ym, names.get(m, "%d dead checks" % m), 5.2, INK, ha="right")
        for s, x in ((S0, xa), (S1, xb)):
            cum = 0.0
            t = tab[s][m]
            parts = [(t.get(11, 0), D11, WHITE), (t.get(10, 0), D10, INK), (t.get(9, 0), D9, INK),
                     (sum(v for d, v in t.items() if d <= 8), DLOW, WHITE)]
            for v, c, tc in parts:
                if v <= 0:
                    continue
                w = v * wbar
                ax.add_patch(Rectangle((x + cum, ym - hbar / 2), max(w - 0.25, 0.2), hbar, facecolor=c, edgecolor="none", zorder=3))
                if v >= 0.07:
                    txt(ax, x + cum + w / 2, ym - 0.05, "%d%%" % round(100 * v), 4.8, tc, ha="center", zorder=4)
                cum += w
        pct = 100 * share[m]
        txt(ax, xs, ym, ("%.0f%%" if pct >= 10 else "%.1f%%" if pct >= 1 else "%.2f%%") % pct, 5.0, INK2, ha="right")
        y -= pitch


def f4_yields(ax, top, res):
    panel(ax, 123.5, top, "d", "Estimated share of chips at distance ≥10")
    x0, x1 = 141.0, 179.0
    Xp = lambda v: x0 + v * (x1 - x0)
    ly = top - 5.0
    ax.scatter([126.0], [ly], s=9, color=MUTED, edgecolors="none")
    txt(ax, 127.3, ly, "perfect chips only", 4.7)
    ax.scatter([126.0], [ly - 3.0], s=13, facecolors=WHITE, edgecolors=INK2, linewidths=0.7)
    txt(ax, 127.3, ly - 3.0, "plus certified chips, standard schedule", 4.7)
    ax.scatter([126.0], [ly - 6.0], s=15, color=BLUE, edgecolors=WHITE, linewidths=0.4)
    txt(ax, 127.3, ly - 6.0, "plus certified chips, distance-11 schedule", 4.7)
    ytop = top - 15.5
    pitch = 6.8
    txt(ax, x0 - 2.0, ytop + 1.0, "junction yield", 4.6, MUTED, ha="right", fontweight="bold", va="center")
    y = ytop
    for key, lab in (("0.9998", "99.98%"), ("0.9995", "99.95%"), ("0.999", "99.9%")):
        ym = y - pitch / 2 - 0.5
        row = res["yields"][key]
        a, b, c = row["perfect"], row["standard_d10"], row["best8_d10"]
        txt(ax, x0 - 2.0, ym, lab, 5.2, INK, ha="right")
        ax.plot([Xp(a), Xp(b)], [ym, ym], color=GRAY_LIGHT, lw=2.6, solid_capstyle="butt", zorder=2)
        ax.plot([Xp(b), Xp(c)], [ym, ym], color=BLUE, lw=2.6, solid_capstyle="butt", zorder=3)
        ax.scatter([Xp(a)], [ym], s=9, color=MUTED, edgecolors="none", zorder=4)
        ax.scatter([Xp(b)], [ym], s=13, facecolors=WHITE, edgecolors=INK2, linewidths=0.7, zorder=5)
        ax.scatter([Xp(c)], [ym], s=16, color=BLUE, edgecolors=WHITE, linewidths=0.4, zorder=6)
        for v, col, wt in ((a, MUTED, "normal"), (b, INK2, "normal"), (c, BLUE, "bold")):
            txt(ax, Xp(v), ym + 2.0, "%d" % round(100 * v), 4.8, col, ha="center", fontweight=wt)
        y -= pitch
    yb = y - 0.5
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        ax.plot([Xp(v)] * 2, [yb, ytop], color=GRID, lw=0.45, zorder=0)
        txt(ax, Xp(v), yb - 1.6, "%d" % (100 * v), 5.0, INK2, ha="center")
    ax.plot([x0, x1], [yb, yb], color=AXIS, lw=0.55, zorder=1)
    txt(ax, (x0 + x1) / 2, yb - 3.9, "share of all chips (%)", 5.4, INK2, ha="center")


def fig_design_ibm():
    """Figure 4: the schedule sets the circuit distance (a); the merged codes of published logical measurements, certified (b); on the gross
    code, each chip with dead checks is a new circuit, certified chip by chip (c, d)."""
    sys.path[:0] = [str(ROOT / "papers"), str(ROOT / "results" / "defect_study")]
    import chip_shares as CS
    tab, n, res = CS.main()
    W, H = 183, 100
    fig, ax = canvas(W, H)
    top = H - 3.8
    ybot = f4_schedules(ax, top)
    f4_surgery(ax, top, ybot + 3.3)
    top2 = ybot - 5.5
    f4_chips(ax, top2, tab, n, res, CS.BEST8)
    f4_yields(ax, top2, res)
    save(fig, "ncs_fig4")


def fig_ablation_si():
    """Supplementary figure: what each part of the method contributes, one part switched off at a time."""
    a, b32, b1, metas = MF.bench()
    abl = T.load(ROOT / "results" / "bench_ablation_final", 1)
    circ = [m["name"] for m in metas if m["track"] == "circuit" and "sector" in m["variants"]]
    count = lambda recs, name: sum(MF.exact(recs, name, i, "sector") is not None for i in circ)
    rows = [("full method", count(a, "ours")),
            ("without the truncated Rank DP", count(abl, "ours + DP")),
            ("without either Rank DP", count(abl, "ours, search only")),
            ("without lifting", count(abl, "ours, lift off")),
            ("without the covering bound", count(abl, "ours, cover off")),
            ("without windows", count(abl, "ours, window off")),
            ("without symmetry", count(abl, "ours, symmetry off")),
            ("without time collapse", count(abl, "ours, collapse off")),
            ("no collapse, lifting or windows", count(abl, "ours, collapse off lift off window off")),
            ("also no symmetry or covering bound (Rank DPs kept)", count(abl, "ours, symmetry off cover off collapse off lift off window off"))]
    W, pitch = 140.0, 4.4
    H = pitch * len(rows) + 13.0
    fig, ax = canvas(W, H)
    x0, x1, n = 68.0, 134.0, len(circ)
    X = lambda v: x0 + (x1 - x0) * v / n
    ytop = H - 2.0
    for k, (lab, v) in enumerate(rows):
        ym = ytop - (k + 0.5) * pitch
        txt(ax, x0 - 1.5, ym, lab, 5.8, INK if k == 0 else INK2, ha="right", fontweight="bold" if k == 0 else "normal")
        ax.add_patch(Rectangle((x0, ym - 1.5), X(v) - x0, 3.0, facecolor=BLUE if k == 0 else GRAY, edgecolor="none", zorder=2))
        txt(ax, X(v) + 1.0, ym, str(v), 5.6, INK if k == 0 else INK2, fontweight="bold" if k == 0 else "normal")
    yb = ytop - len(rows) * pitch
    for v in (0, 10, 20, 30, 40):
        ax.plot([X(v)] * 2, [yb, ytop], color=GRID, lw=0.4, zorder=0)
        txt(ax, X(v), yb - 1.7, str(v), 5.5, INK2, ha="center")
    ax.plot([x0, x1], [yb, yb], color=AXIS, lw=0.5, zorder=1)
    txt(ax, (x0 + x1) / 2, yb - 4.3, "CSS circuits certified (of %d; one thread, 600 s)" % n, 5.8, INK2, ha="center")
    save(fig, "si_ablation")


def fig_hyperbolic_si():
    """Supplementary figure: the ranges of the modular hyperbolic codes and their exact distances, with the marks of Fig. 3."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import summarize_hyperbolic as S
    res = S.load_results()
    rows = []
    for name, label, stated in S.ROWS:
        if "–" not in stated or name not in res or res[name].get("d") is None:
            continue
        lo, hi = map(int, stated.split("–"))
        r = res[name]
        short = re.sub(r" \(our entry \d+\)", "", label).replace(", class 1", "")
        rows.append((r["d"], r["n"], "[[%d,%d]]  %s, L = %d" % (r["n"], r["k"], short, int(name.rsplit("_L", 1)[1])), lo, hi))
    rows.sort(key=lambda t: (t[0], t[1]))
    assert len(rows) == 15 and all(d == hi for d, _, _, _, hi in rows)
    W, pitch = 140.0, 3.4
    H = pitch * len(rows) + 15.0
    fig, ax = canvas(W, H)
    x0, x1, dmin, dmax = 76.0, 136.0, 4, 30
    X = lambda d: x0 + (x1 - x0) * (d - dmin) / (dmax - dmin)
    ly = H - 2.0
    ax.plot([x0, x0 + 4.0], [ly, ly], color=GRAY_LIGHT, lw=2.0, solid_capstyle="round")
    txt(ax, x0 + 5.4, ly, "range in the paper", 5.4)
    ax.scatter([x0 + 30.0], [ly], s=11, color=BLUE, edgecolors=WHITE, linewidths=0.4)
    txt(ax, x0 + 31.4, ly, "exact distance", 5.4)
    ytop = H - 5.0
    for k, (d, n, lab, lo, hi) in enumerate(rows):
        ym = ytop - (k + 0.5) * pitch
        txt(ax, x0 - 2.0, ym, lab, 5.6, INK2, ha="right")
        ax.plot([X(lo), X(hi)], [ym, ym], color=GRAY_LIGHT, lw=2.0, solid_capstyle="round", zorder=2)
        ax.scatter([X(d)], [ym], s=11, color=BLUE, edgecolors=WHITE, linewidths=0.4, zorder=5)
    yb = ytop - len(rows) * pitch
    for v in range(4, 31, 4):
        ax.plot([X(v)] * 2, [yb, ytop], color=GRID, lw=0.4, zorder=0)
        txt(ax, X(v), yb - 1.7, str(v), 5.5, INK2, ha="center")
    ax.plot([x0, x1], [yb, yb], color=AXIS, lw=0.5, zorder=1)
    txt(ax, (x0 + x1) / 2, yb - 4.3, "code distance", 5.8, INK2, ha="center")
    save(fig, "si_hyperbolic")


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
MATCHED_DIR = ROOT / "results" / "ibm_matched"


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
            used = "{:,}".format(r["n_minimum_fault_sets"]) if r["source"] == "all minimum fault sets" else \
                "{:,}".format(r["n_minimum_fault_sets"]) + r"\textsuperscript{a}"
            ref = [e10(ibm[e["code"]][p]) if k == 0 and e["schedule"] == "standard" else "" for p in (1e-4, 1e-3)]
            out.append(" & ".join([name[e["code"]] + ", " + sched if k == 0 else "", "$%s$" % b,
                                   "%d" % r.get("distance", e["distance"]), used, "{:,}".format(r["n_family"]),
                                   e10(rate(1e-4, "log10_lower_bound")), e10(rate(1e-3, "log10_lower_bound"))]
                                  + ref) + r" \\")
        out.append(r"\addlinespace[2pt]")
    out[-1] = r"\bottomrule"
    out.append(r"\end{tabular}")
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/ibm/curves.json; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


def ibm_fit_table(path):
    """Supplementary table of the two-gross rates in the setting of Tour de gross: its Table 2, the sum of its eq. 82 with
    its fit parameters (papers/ibm_bicycle_fit.py) and the per-cycle bounds of papers/ibm_bicycle_matched_bound.py."""
    fit = json.load(open(MATCHED_DIR / "fit_tour_de_gross.json"))
    t2 = fit["reproduced"]["two-gross idle"]
    bnd = fit["bounds"]
    out = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
           r" & \multicolumn{2}{c}{ref.~\citenum{yoder_2025_tour}} & \multicolumn{2}{c}{bound per cycle, any decoder} & \\",
           r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
           r"$p$ & Table 2 & sum of its eq.~82 & weight 16 & weight 18 & higher bound minus sum \\", r"\midrule"]
    for p, lab in ((1e-4, "$10^{-4}$"), (2e-4, r"$2\times10^{-4}$"), (5e-4, r"$5\times10^{-4}$"),
                   (7.322e-4, r"$7.322\times10^{-4}$"), (1e-3, "$10^{-3}$")):
        k = str(p)
        b16, b18 = (bnd[w]["log10_per_cycle_two_bases"][bnd[w]["p"].index(p)] for w in ("16", "18"))
        cell = r"$10^{%.1f\pm%.1f}$" % (t2[k]["table_2"], t2[k]["uncertainty"]) if k in t2 else ""
        curve = b16 - bnd["16"]["orders_above_curve"][k]
        out.append(" & ".join([lab, cell, r"$10^{%.2f}$" % curve, r"$10^{%.2f}$" % b16, r"$10^{%.2f}$" % b18,
                               "$%+.2f$" % (max(b16, b18) - curve)]) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/ibm_matched; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


def ibm_spectrum_table(path):
    """Supplementary table of the logical fault sets of weight <= 12 of the gross code's instruction in the setting of Tour
    de gross (10 cycles) and the expansion of a minimum-weight decoder's logical error rate to order p^6 at p = 1e-4, per
    cycle (results/ibm_matched/mwd_gross_c10.json)."""
    mwd = json.load(open(MATCHED_DIR / "mwd_gross_c10.json"))
    e10 = lambda v: "--" if v is None or v == -math.inf else r"$10^{%.1f}$" % v
    name = {"standard": "standard (8 timesteps)", "s561234_324015": "best of 8 timesteps", "s106432_342560": "best of 9 timesteps"}
    out = [r"\begin{tabular}{@{}lcrrrrrrrr@{}}", r"\toprule",
           r" & & & \multicolumn{3}{c}{logical fault sets of weight} & \multicolumn{4}{c}{failures of weight, per cycle at $p=10^{-4}$} \\",
           r"\cmidrule(lr){4-6}\cmidrule(l){7-10}",
           r"schedule & basis & $d$ & 10 & 11 & 12 & 5 & 6 (sets 10, 11) & 6 (sets 12) & total \\",
           r"\midrule"]
    for k, e in enumerate(mwd["entries"]):
        n = {int(w): c for w, c in e["sets_by_weight"].items()}
        r = e["rates"][str(1e-4)]
        per = -math.log10(e["cycles"])
        first = k == 0 or mwd["entries"][k - 1]["schedule"] != e["schedule"]
        out.append(" & ".join([name[e["schedule"]] if first else "", "$%s$" % e["basis"], "%d" % e["distance"],
                               "{:,}".format(n.get(10, 0)), "{:,}".format(n.get(11, 0)), "{:,}".format(n.get(12, 0)),
                               e10(r["log10_w5"] + per if r["log10_w5"] != -math.inf else None),
                               e10(r["log10_w6_from_10_11"] + per), e10(r["log10_w6_from_12"] + per),
                               e10(r["log10_total_per_cycle"])]) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/ibm_matched/mwd_gross_c10.json; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


def ibm_sim_table(path):
    """Supplementary table of the BP-OSD simulations of the gross code's instruction in the setting of Tour de gross
    (results/ibm_matched/sim_gross_c10.jsonl): failure probabilities of the 10 cycles with failures, per schedule and
    basis."""
    sims = {}
    for line in open(MATCHED_DIR / "sim_gross_c10.jsonl"):
        r = json.loads(line)
        sims.setdefault(r["p"], {})[(r["schedule"], r["basis"])] = r
    tags = ("standard", "s561234_324015", "s106432_342560")

    def cell(r, e):
        x = r["rate"] / 10 ** e
        return ("%.2f" if x < 10 else "%.1f") % x + " ({:,})".format(r["failures"])

    out = [r"\begin{tabular}{@{}lccccccc@{}}", r"\toprule",
           r" & & \multicolumn{2}{c}{standard} & \multicolumn{2}{c}{best of 8 timesteps} & \multicolumn{2}{c}{best of 9 timesteps} \\",
           r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(l){7-8}",
           r"$p$ & unit & $Z$ & $X$ & $Z$ & $X$ & $Z$ & $X$ \\", r"\midrule"]
    for p in sorted(sims, reverse=True):
        v = sims[p]
        e = math.floor(math.log10(min(r["rate"] for r in v.values())))
        cells = [cell(v[(t, b)], e) if (t, b) in v else "" for t in tags for b in "ZX"]
        out.append(" & ".join([r"$%g\times10^{-3}$" % (p * 1e3), r"$10^{%d}$" % e] + cells) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/ibm_matched/sim_gross_c10.jsonl; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


def audit_table(path):
    """Supplementary table of every audited value (docs/audit_items.csv) as a LaTeX longtable, in the order of
    figure 3."""
    stated = {"claim": "stated as the distance", "bound": "upper bound", "estimated_bound": "estimated upper bound",
              "best_known": "best known value", "estimate": "estimate", "randomized": "randomized search", "expected": "expected",
              "conjecture": "conjecture", "range": "range", "open": "open", "lower_bound": "lower bound"}
    rows = audit_rows()

    def tex(x):
        x = re.sub(r"\[\[([0-9,]+)\]\]", lambda m: r"\qc{%s}" % m.group(1), x)
        return x.replace("–", "--").replace("_", r"\_").replace("d = ", "$d=$").replace("n = ", "$n=$")
    out = [r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{2.4cm}>{\raggedright\arraybackslash}p{2.9cm}"
           r">{\raggedright\arraybackslash}p{2.5cm}>{\raggedright\arraybackslash}p{1.35cm}c"
           r">{\raggedright\arraybackslash}p{4.1cm}@{}}",
           r"\caption{Every audited value of \cref{sec:audit}, by paper. Published: the value "
           r"and how the paper states it. Certified: the exact value (bold where it corrects the published value or settles one "
           r"left open), or the "
           r"interval between the proved lower bound and the lightest error found. Values whose note begins with "
           r"``not counted'' are listed but not counted as too high (\cref{subsec:audit-protocol}). Prov.: A, the authors' circuit or data "
           r"files; P, public circuit files of the paper's schedule from another source; R, rebuilt from the paper's text "
           r"and checked against values it reports as exact.}\label{tab:audit}\\",
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
                pub = ("%d--%d" % (lo, hi) if lo != hi else {"bound": "$\\le$%d", "estimated_bound": "$\\le$%d", "best_known": "$\\le$%d",
                                                            "lower_bound": "$\\ge$%d"}.get(r["stated"], "%d") % hi)
                if r["stated"] == "hook_free":          # no circuit distance printed (pub_lo, pub_hi hold the code distance)
                    how = "none (schedule called hook-free)"
                else:
                    how = "%s (%s)" % (pub, stated[r["stated"]])
                clo, chi = int(float(r["cert_lo"])), int(float(r["cert_hi"]))
                cert = "%d" % clo if clo == chi else "%d--%d" % (clo, chi)
                if r["verdict"] in ("too_high", "settled") and clo == chi:
                    cert = r"\textbf{%s}" % cert
                paper = (tex(g) + r"~\cite{%s}" % refs[g]) if k == 0 else ""
                out.append(" & ".join([paper, tex(r["object"]), how, cert, r["prov"], tex(r["note"])]) + r" \\")
            out.append(r"\addlinespace[2pt]")
        if kind == "circuit":
            out.append(r"\midrule")
    out.append(r"\end{longtable}")
    Path(path).write_text("% generated by docs/make_ncs_figures.py from docs/audit_items.csv; do not edit\n" +
                          "\n".join(out) + "\n")
    print("wrote", path)


def scan_tables(out):
    """Numbers and tables of the two-gross schedule scan (results/bb288_scan/tally_scan.py) and of the number of cycles (results/defect_study)."""
    tally = json.load(open(ROOT / "results" / "bb288_scan" / "scan_table.json"))
    by = tally["by_value"]
    steps = json.load(open(ROOT / "results" / "bb288_scan" / "screen" / "timesteps.json"))
    assert steps["8"]["without"] == 0 and steps["8"]["with_hook_family"] + steps["9"]["with_hook_family"] == tally["cap_16_schedules"]
    macros = {"scanNbest": tally["n_best"], "scanNseventeen": by.get("17", 0), "scanNsixteen": by.get("16", 0), "scanNfifteen": by.get("15", 0),
              "scanNopen": sum(o[2] for o in tally["open"]), "scanNeight": steps["8"]["with_hook_family"]}
    head = "% generated by docs/make_ncs_figures.py from results/bb288_scan/scan_table.json; do not edit\n"
    (out / "si_scan_numbers.tex").write_text(head + "".join("\\newcommand{\\%s}{%s}\n" % (k, "{:,}".format(v)) for k, v in macros.items()))
    # one-round windows
    types = json.load(open(ROOT / "results" / "bb288_scan" / "screen" / "window_types.json"))
    transfer = [json.loads(x) for x in open(ROOT / "results" / "bb288_scan" / "screen" / "window_transfer.jsonl")]
    assert all(r["verified"] for r in transfer)
    count, cols = {}, {}
    for e in types:
        for w in e["windows"]:
            count[w["id"]] = count.get(w["id"], 0) + 1
            cols[w["id"]] = w["columns"]
    weight = {r["id"]: r["weight"] for r in transfer}
    lines = [r"\begin{tabular}{@{}lrrl@{}}", r"\toprule", r"one-round window & columns & occurrences & lightest fault set \\", r"\midrule"]
    for k in sorted(count, key=lambda i: (cols[i], -count[i], -weight.get(i, 0))):
        fault = "weight %d, replayed in every occurrence" % weight[k] if k in weight else "the code's own logical operators, weight 18"
        lines.append(r"\texttt{%s} & %d & %d & %s \\" % (k[:4], cols[k], count[k], fault))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_scan_windows_table.tex").write_text(head + "\n".join(lines) + "\n")
    # values of the schedules
    lines = [r"\begin{tabular}{@{}lrr@{}}", r"\toprule", r"schedules & number & circuit distance at one cycle \\", r"\midrule",
             r"with a family of hook columns in one round & %s & at most 16, of which %d exactly %d \\" % ("{:,}".format(tally["cap_16_schedules"]), tally["schedules_at_worst"], tally["worst"])]
    classes = tally["classes_by_value"]
    for v in sorted(by, key=int):
        lines.append(r"without such a family, %d classes & %s & %s \\" % (len(classes[v]), "{:,}".format(by[v]), v))
    if tally["open"]:
        lines.append(r"without such a family, not yet decided, %d classes & %s & 17 or 18 \\" % (len(tally["open"]), "{:,}".format(macros["scanNopen"])))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_scan_values_table.tex").write_text(head + "\n".join(lines) + "\n")
    # the classes at the best value
    sys.path[:0] = [str(ROOT / "papers")]
    import bb6_depth7 as B6
    import ibm_bicycle_matched as IBM6
    classes_all = json.load(open(ROOT / "results" / "bb288_scan" / "screen" / "classes.json"))
    lines = [r"\begin{tabular}{@{}llrr@{}}", r"\toprule", r"$p_X$ & $p_Z$ & schedules & timesteps per cycle \\", r"\midrule"]
    for i in tally["classes_at_best"]:
        a, b = classes_all[i]["problems"][0]
        sched = (tuple(map(int, a)), tuple(map(int, b)))
        lines.append(r"(%s) & (%s) & %d & %d \\" % (",".join(a), ",".join(b), classes_all[i]["n"], IBM6.timing(B6.to_dicts(*sched))[1]))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_scan_best_table.tex").write_text(head + "\n".join(lines) + "\n")
    # number of cycles
    base = json.load(open(ROOT / "results" / "defect_study" / "cycles_base_rate.json"))
    names = {"bb72": r"\qc{72,12,6}", "bb90": r"\qc{90,8,10}", "bb108": r"\qc{108,8,10}", "gross": r"\qc{144,12,12}"}
    lines = [r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule", r"code & problems & orbits run & one cycle equals six & two cycles equal six \\", r"\midrule"]
    for k, n in names.items():
        b = base[k]
        lines.append(r"%s & %s & %s & %s & %s \\" % (n, "{:,}".format(b["problems"]), "{:,}".format(b["orbits"]), "{:,}".format(b["same_c1"]), "{:,}".format(b["same_c2"])))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_cycles_table.tex").write_text("% generated by docs/make_ncs_figures.py from results/defect_study/cycles_base_rate.json; do not edit\n" + "\n".join(lines) + "\n")


def chips_tables(out):
    """Tables of the chips with dead checks (results/defect_study)."""
    sys.path[:0] = [str(ROOT / "papers"), str(ROOT / "results" / "defect_study")]
    import chip_shares as CS
    tab, n, res = CS.main()
    head = "% generated by docs/make_ncs_figures.py from results/defect_study; do not edit\n"
    S1 = CS.BEST8

    def pct(v):
        return ("%.1f" % (100 * v)) if v > 0 else ""

    lines = [r"\begin{tabular}{@{}lrrrrrrr@{}}", r"\toprule", r" & \multicolumn{3}{c}{standard schedule} & \multicolumn{4}{c}{distance-11 schedule} \\",
             r"dead checks & 10 & 9 & $\le$8 & 11 & 10 & 9 & $\le$8 \\", r"\midrule"]
    for m in sorted(set(tab[None]) & set(tab[S1])):
        a, b = tab[None][m], tab[S1][m]
        low = lambda t: sum(v for d, v in t.items() if d <= 8)
        lines.append(r"%d & %s & %s & %s & %s & %s & %s & %s \\" % (m, pct(a.get(10, 0)), pct(a.get(9, 0)), pct(low(a)), pct(b.get(11, 0)), pct(b.get(10, 0)), pct(b.get(9, 0)), pct(low(b))))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_chips_table.tex").write_text(head + "\n".join(lines) + "\n")
    rank = json.load(open(ROOT / "results" / "defect_study" / "yield.json"))["yields"]
    lines = [r"\begin{tabular}{@{}lrrrrrr@{}}", r"\toprule", r" & & \multicolumn{2}{c}{distance $\ge$10} & \multicolumn{2}{c}{distance $\ge$9} & \\",
             r"junction yield & perfect & standard & distance-11 & standard & distance-11 & rank test accepts \\", r"\midrule"]
    for key, lab in (("0.9998", "99.98\\%"), ("0.9995", "99.95\\%"), ("0.999", "99.9\\%")):
        y = res["yields"][key]
        lines.append(r"%s & %.0f & %.0f & %.0f & %.1f & %.1f & %.0f \\" % (lab, 100 * y["perfect"], 100 * y["standard_d10"], 100 * y["best8_d10"], 100 * y["standard_d9"], 100 * y["best8_d9"], 100 * rank[key]["accepted"]))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_chips_yield_table.tex").write_text(head + "\n".join(lines) + "\n")
    # BP-OSD
    sims = [json.loads(x) for x in open(ROOT / "results" / "defect_study" / "rec" / "sim_chip.jsonl")]
    sims11 = [json.loads(x) for x in open(ROOT / "results" / "defect_study" / "rec" / "sim_chip_d11.jsonl")]
    sims11 += [dict(x, name="d11_perfect") for x in map(json.loads, open(MATCHED_DIR / "sim_gross_c10.jsonl")) if x["schedule"] == "s561234_324015"]
    names = [("perfect", "perfect chip"), ("z0", "one dead $Z$ check"), ("x0", "one dead $X$ check"), ("x0_z5", "dead $X$ and $Z$ checks"), ("z0_z5", "two dead $Z$ checks"),
             ("m3", "three dead checks"), ("m5", "five dead checks")]
    ps = sorted({r["p"] for r in sims})
    lines = [r"\begin{tabular}{@{}l" + "rr" * len(ps) + "@{}}", r"\toprule", " & ".join([""] + [r"\multicolumn{2}{c}{$p=%g\times10^{-3}$}" % (1e3 * p) for p in ps]) + r" \\",
             " & ".join(["chip"] + ["$Z$", "$X$"] * len(ps)) + r" \\"]
    for title, recs, prefix in (("standard schedule", sims, ""), ("distance-11 schedule", sims11, "d11_")):
        lines += [r"\midrule", r"\multicolumn{%d}{@{}l}{%s} \\" % (1 + 2 * len(ps), title)]
        for key, lab in names:
            row = [lab]
            for p in ps:
                for b in "ZX":
                    r = [x for x in recs if x["name"] == prefix + key and x["p"] == p and x["basis"] == b]
                    assert len(r) == 1, (prefix + key, p, b)
                    row.append("%.2f" % (1e3 * r[0]["rate"]))
            lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "si_chips_sim_table.tex").write_text(head + "\n".join(lines) + "\n")


def extended_table(path):
    """Longer runs outside the benchmark (results/bench_extended): lower-bound runs and the explicit error, from the records."""
    def run(p, thresholds=""):
        r = json.load(open(EXT / p))
        return r"%s%.1f h on %d threads" % (thresholds + ", " if thresholds else "", r["seconds"] / 3600, r["threads"]), r
    rows = []

    def add(name, value, *parts):
        rows.append(" & ".join([name, value, "; ".join(parts)]) + r" \\")

    a, r = run("ours_pipeline__dp-2/wjh_qt_288_2_24__full__t32.json")
    assert r["lower_bound"] == r["upper_bound"] == 24
    b, r = run("tanner_x/wjh_qt_288_2_24_Xdist__full__t12.json")
    assert r["lower_bound"] == 24
    add(r"Tanner \qc{288,2}", "24", "$Z$: " + a, "$X$: " + b + ", with a logical of weight 24")
    a, r = run("ours_pipeline__dp-2/wjh_qt_324_4_25__full__t32.json")
    assert r["lower_bound"] == r["upper_bound"] == 25
    if (EXT / "tanner_x/wjh_qt_324_4_25_Xdist_kmin24.json").exists():
        r1 = json.load(open(EXT / "tanner_x/wjh_qt_324_4_25_Xdist__full__t12.json"))
        assert r1["lower_bound"] == 24
        b1 = "up to weight 23, %.1f h on %d threads" % (r1["trace"][-1]["t"] / 3600, r1["threads"])
        b, r2 = run("tanner_x/wjh_qt_324_4_25_Xdist_kmin24.json", "weight 24")
        assert r2["lower_bound"] == 25
        add(r"Tanner \qc{324,4}", "25", "$Z$: " + a, "$X$: " + b1 + ", " + b + ", with a logical of weight 25")
    else:
        add(r"Tanner \qc{324,4}", "$Z$: 25", "$Z$: " + a, "$X$: a logical of weight 25, search running")
    a, r = run("ours_pipeline__dp-2/wjh_qt_360_4_24__full__t32.json")
    assert r["lower_bound"] == r["upper_bound"] == 24
    b, r = run("tanner_x/wjh_qt_360_4_24_Xdist_kmax23.json")
    assert r["lower_bound"] == 24
    add(r"Tanner \qc{360,4}", "24", "$Z$: " + a, "$X$: " + b + ", with a logical of weight 24")
    a, r = run("ours_pipeline__dp-2/wjh_qt_396_4_26__full__t32.json", "up to weight 25")
    assert r["lower_bound"] == 26
    b, r = run("ours_pipeline__dp-2__kmin-26__kmax-26/wjh_qt_396_4_26__full__t89.json", "weight 26")
    assert r["lower_bound"] == 27
    if (EXT / "tanner_x/wjh_qt_396_4_26_Xdist_kmax25.json").exists():
        c, r2 = run("tanner_x/wjh_qt_396_4_26_Xdist_kmax25.json")
        assert r2["lower_bound"] == 26
        add(r"Tanner \qc{396,4}", "26", "$Z$ distance 27: " + a + ", " + b + ", with a logical of weight 27", "$X$ distance 26: " + c + ", with a logical of weight 26")
    else:
        add(r"Tanner \qc{396,4}", "$Z$: 27", "$Z$: " + a + ", " + b + ", with a logical of weight 27", "$X$: a logical of weight 26, search running")
    a, r = run("ours_pipeline__dp-2/wjh_bb_n648__full__t32.json", "up to weight 30")
    assert r["lower_bound"] == 31
    b, r = run("ours_pipeline__dp-2__kmin-31__kmax-31/wjh_bb_n648__full__t57.json", "weight 31")
    assert r["lower_bound"] == 32
    add(r"bivariate bicycle \qc{648,4}", "32", a, b, "a logical of weight 32")
    a, r = run("ours_pipeline__dp-2__kmax-32/wjh_bb_n756__full__t57.json", "up to weight 32")
    assert r["lower_bound"] == 33
    rec = "ours_pipeline__dp-2__kmin-33__kmax-33/wjh_bb_n756__full__t134.json"
    if (EXT / rec).exists():
        b, r2 = run(rec, "weight 33")
        assert r2["lower_bound"] == 34
        add(r"bivariate bicycle \qc{756,16}", "34", a, b, "a logical of weight 34")
    else:
        add(r"bivariate bicycle \qc{756,16}", "33--34", a, "a logical of weight 34; weight 33 still running")
    a, r = run("ours_pipeline__dp-2/hypercube_L4__full__t32.json")
    assert r["lower_bound"] == r["upper_bound"] == 16
    add(r"many-hypercube $L=4$", "16", a)
    a, r = run("ours_pipeline__dp-2/mitten_300__sector__t32.json", "up to weight 11")
    assert r["lower_bound"] == 12
    add(r"mitten \qc{300,60,14} circuit", "12", a, "the 3-round fault set of weight 12 replayed in the 6-round circuit")
    k13 = json.load(open(ROOT / "results" / "cornucopia" / "circ_q64_r8_Z_k13.json"))
    assert k13["certified_lower_bound"] == 13
    last = k13["collapsed"]["runs"][-1]
    assert last["K"] == 12 and last["status"] == "exhausted" and last["best"] is None
    add(r"Cornucopia \qc{2304,1156,16} circuit, $Z$ basis, 8 cycles", "13--14", "time-collapsed problem up to weight 12, last weight %.1f h on %d threads" % (last["seconds"] / 3600, k13["threads"]), "a fault set of weight 14")
    Path(path).write_text("% generated by docs/make_ncs_figures.py from results/bench_extended; do not edit\n" + "\n".join(
        [r"\begin{tabular}{@{}>{\raggedright\arraybackslash}p{4.0cm}l>{\raggedright\arraybackslash}p{9.0cm}@{}}", r"\toprule", r"instance & value & runs \\", r"\midrule"] + rows + [r"\bottomrule", r"\end{tabular}"]) + "\n")


if __name__ == "__main__":
    OUT = Path(sys.argv[1]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    which = sys.argv[2:] or ["1", "2", "3", "4", "hook", "design", "ablation", "hyperbolic", "limit", "table"]
    for k in which:
        if k == "table":
            audit_table(OUT / "si_audit_table.tex")
            scan_tables(OUT)
            chips_tables(OUT)
            surgery_tables(OUT)
            extended_table(OUT / "si_extended_table.tex")
            sdbb_table(OUT / "si_sdbb_table.tex")
            if (IBM_DIR / "curves.json").exists():
                ibm_table(OUT / "si_ibm_table.tex")
            if (MATCHED_DIR / "mwd_gross_c10.json").exists():
                ibm_spectrum_table(OUT / "si_ibm_spectrum_table.tex")
            if (MATCHED_DIR / "fit_tour_de_gross.json").exists():
                ibm_fit_table(OUT / "si_ibm_fit_table.tex")
            if (MATCHED_DIR / "sim_gross_c10.jsonl").exists():
                ibm_sim_table(OUT / "si_ibm_sim_table.tex")
            continue
        {"1": fig_schematic, "2": fig_capability, "3": fig_audit, "4": fig_design_ibm, "hook": fig_hook, "design": fig_design_si, "ablation": fig_ablation_si, "hyperbolic": fig_hyperbolic_si,
         "limit": fig_limit_si}[k]()
