"""Tables and the figure of results/sparse_dp/README.md from the records of scripts/sparse_dp_eval.py.

usage: python scripts/summarize_sparse_dp.py [results/sparse_dp]
Writes results/sparse_dp/tables.md (included in the README by hand) and results/sparse_dp/states_per_cut.png.
"""
import glob
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMS = ("narrow", "lowwidth", "bb", "circuits", "d11")
REGIME = {"color": "narrow", "lowwidth": "narrow", "bb": "expanding", "wjh": "local circuit"}
SPARSE = ("sparse:mitm:c:0:auto", "sparse:mitm:c:1:auto", "sparse:forward:c:1", "sparse:forward:c:0")
SHORT = {"sparse:mitm:c:0:auto": "MITM", "sparse:mitm:c:1:auto": "MITM+h", "sparse:forward:c:1": "fwd+h",
         "sparse:forward:c:0": "fwd"}


def load(d):
    out = {}
    for s in STREAMS:
        f = os.path.join(d, s + ".json")
        if os.path.exists(f):
            out.update(json.load(open(f))["instances"])
    return out


def order_key(token):
    kind = token.split(":")[0]
    rank = {"color": 0, "lowwidth": 1, "bb": 2, "wjh": 3}[kind]
    tail = token.split(":")[1:]
    fam = tail[0] if kind == "wjh" else ""
    num = int("".join(ch for ch in tail[-1] if ch.isdigit()) or 0)
    return rank, fam, num, token


def name(token):
    return token.replace("lowwidth:", "").replace("wjh:", "").replace("bb:", "").replace("color:", "color d")


def fmt_t(x):
    if x is None:
        return "–"
    if x < 0.01:
        return "%.3f" % x
    if x < 10:
        return "%.2f" % x
    if x < 100:
        return "%.1f" % x
    return "%.0f" % x


def fmt_n(x):
    if x is None:
        return "–"
    if x < 1e4:
        return "%d" % x
    e = int(math.floor(math.log10(x)))
    return "%.1fe%d" % (x / 10 ** e, e)


def fmt_bytes(b):
    if b is None:
        return "–"
    for unit, k in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if b >= k:
            return "%.1f %s" % (b / k, unit)
    return "%d B" % b


def value(run):
    """The run's outcome as a short string."""
    if run is None:
        return "–"
    r = run.get("result", {})
    st = r.get("status")
    if st == "exact" and r.get("distance") is not None:
        return str(r["distance"]) + ("" if r.get("witness_ok", True) else " (bad witness)")
    if st == "timeout":
        return "≥ %s (timeout)" % r.get("lower_bound", "?")
    if st and st.startswith("no solution"):
        return "≥ %d" % r["lower_bound"]
    if st == "budget":
        return "budget"
    if st == "too wide":
        return "too wide"
    if st == "error":
        return "error"
    return str(st)


def seconds(run):
    if run is None or run.get("result", {}).get("status") in ("too wide", "error", "budget"):
        return None
    return run.get("seconds")


def search_last(run):
    """Seconds of the search's last two thresholds (d - 1 and d), the part comparable to the two sparse runs."""
    if not run or "runs" not in run:
        return None
    return sum(x["seconds"] for x in run["runs"][-2:])


def sparse_stats(run):
    """(split, peak states, peak table bytes, states of the K = d - 1 run summed over cuts and observables)."""
    if not run or "lower_run" not in run:
        return None
    qs = run["lower_run"]["queries"]
    peak = max(q["peak_states"] for q in qs)
    tb = max(q.get("peak_table_bytes", 0) for q in qs)
    tot = sum(q.get("forward_states_total", 0) + q.get("backward_states_total", 0) for q in qs)
    split = sorted({q.get("split") for q in qs if q.get("split")})
    return split, peak, tb, tot


def tables(res):
    toks = sorted(res, key=order_key)
    out = []
    out.append("### Validation: distance found by each method\n")
    out.append("| instance | known d | " + " | ".join(SHORT[c] for c in SPARSE) + " | dense DP | search |")
    out.append("|---|---|" + "---|" * (len(SPARSE) + 2))
    for t in toks:
        inst = res[t]
        info = inst.get("info", {})
        known = info.get("distance_known")
        known = str(known) if known is not None else "≤ %s" % info.get("upper_known")
        cells = [value(inst["runs"].get(c)) for c in SPARSE + ("dense", "search")]
        out.append("| %s | %s | %s |" % (name(t), known, " | ".join(cells)))
    out.append("")
    out.append("### Time (seconds, one thread)\n")
    out.append("Sparse: the sweep at K = d - 1 for every observable plus the one at K = d that returns the witness "
               "(the split probe included). Search: all thresholds from K = 1, and in brackets its last two (d - 1 "
               "and d). Dense DP: one untruncated sweep per observable.\n")
    out.append("| instance | regime | columns | cut rank | d | dense DP | search | " +
               " | ".join(SHORT[c] for c in SPARSE) + " |")
    out.append("|---|---|---|---|---|---|---|" + "---|" * len(SPARSE))
    for t in toks:
        inst = res[t]
        info = inst.get("info", {})
        runs = inst["runs"]
        d = info.get("distance_known") or info.get("upper_known")
        s = runs.get("search")
        st = fmt_t(seconds(s)) if s and s.get("result", {}).get("status") == "exact" else value(s)
        if s and s.get("result", {}).get("status") == "exact":
            st += " (%s)" % fmt_t(search_last(s))
        dn = runs.get("dense")
        dt = fmt_t(seconds(dn)) if dn and dn.get("result", {}).get("status") == "exact" else value(dn)
        cells = []
        for c in SPARSE:
            r = runs.get(c)
            cells.append(fmt_t(seconds(r)) if r and r.get("result", {}).get("status") == "exact" else value(r))
        out.append("| %s | %s | %d | %d | %s | %s | %s | %s |" % (
            name(t), REGIME[t.split(":")[0]], info.get("columns", 0), info.get("cut_rank", 0), d, dt, st,
            " | ".join(cells)))
    out.append("")
    out.append("### States kept, against the dense table\n")
    out.append("2^w: entries of the dense table at the widest cut; dense work: entries the dense DP updates per "
               "observable. For the sparse sweeps (K = d - 1 run): the split a of MITM, the largest table (states), "
               "the states summed over all cuts, both directions and all observables, and the tables held at the "
               "peak (checkpoints included).\n")
    out.append("| instance | 2^w | dense work | MITM a | MITM peak | MITM total | MITM tables | fwd+h peak | "
               "fwd+h total | peak memory (MITM) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for t in toks:
        inst = res[t]
        info = inst.get("info", {})
        m = sparse_stats(inst["runs"].get("sparse:mitm:c:0:auto"))
        f = sparse_stats(inst["runs"].get("sparse:forward:c:1"))
        mr = inst["runs"].get("sparse:mitm:c:0:auto", {})
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name(t), fmt_n(2.0 ** info.get("cut_rank", 0)),
            fmt_n(info.get("dense_work_per_query")),
            ",".join(str(x) for x in m[0]) if m else "–", fmt_n(m[1]) if m else "–", fmt_n(m[2 + 1]) if m else "–",
            fmt_bytes(m[2]) if m else "–", fmt_n(f[1]) if f else "–", fmt_n(f[3]) if f else "–",
            ("%.2f GB" % mr["maxrss_gb"]) if mr.get("maxrss_gb") is not None else "–"))
    out.append("")
    return "\n".join(out)


# reference palette of the dataviz guidance (categorical slots 1-3, valid all-pairs in light mode) and its inks
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")
NEUTRAL, SURFACE, INK, INK2 = "#8f8e88", "#fcfcfb", "#0b0b0b", "#52514e"


def figure(res, path, picks):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    picks = [t for t in picks if t in res and "sparse:mitm:c:0:auto" in res[t]["runs"]
             and "lower_run" in res[t]["runs"]["sparse:mitm:c:0:auto"]]
    if not picks:
        return
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "text.color": INK})
    fig, axes = plt.subplots(1, len(picks), figsize=(3.6 * len(picks), 3.3), squeeze=False, facecolor=SURFACE)
    lines = []
    for ax, t in zip(axes[0], picks):
        ax.set_facecolor(SURFACE)
        inst = res[t]
        width = inst["info"]["width"]
        run = inst["runs"]["sparse:mitm:c:0:auto"]["lower_run"]
        pc = run["per_cut"]
        split = run["queries"][0].get("split")
        x = list(range(len(width)))
        lw = 1.1                                              # about 2 px at the saved resolution
        l0, = ax.semilogy(x, [2.0 ** w for w in width], color=NEUTRAL, lw=lw, label="dense table, 2^w states")
        l1, = ax.semilogy(x, [max(v, 0.8) for v in pc["backward_counts"]], color=SERIES[0], lw=lw,
                          label="MITM backward table (weight <= K - a)")
        l2, = ax.semilogy(x, [max(v, 0.8) for v in pc["forward_counts"]], color=SERIES[1], lw=lw,
                          label="MITM forward table (weight <= a - 1)")
        fw = inst["runs"].get("sparse:forward:c:1", {}).get("lower_run", {}).get("per_cut")
        l3 = None
        if fw:
            l3, = ax.semilogy(x, [max(v, 0.8) for v in fw["forward_counts"]], color=SERIES[2], lw=lw,
                              label="forward only, with h (weight <= K)")
        ax.set_title("%s, K = %d, a = %s" % (name(t), run["K"], split), fontsize=9.5, color=INK)
        ax.set_xlabel("cut (columns processed)")
        ax.grid(color="#e4e3df", lw=0.6, which="major")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        if len(lines) < 4:
            lines = [l0, l1, l2] + ([l3] if l3 is not None else [])
    axes[0][0].set_ylabel("states kept at the cut")
    fig.legend(handles=lines, loc="lower center", ncol=len(lines), frameon=False, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path, dpi=130, facecolor=SURFACE)


def main(d=os.path.join(ROOT, "results", "sparse_dp")):
    res = load(d)
    md = tables(res)
    open(os.path.join(d, "tables.md"), "w").write(md + "\n")
    figure(res, os.path.join(d, "states_per_cut.png"),
           ["color:27", "bb:gross", "wjh:superdense:9", "wjh:superdense:11"])
    print(md)


if __name__ == "__main__":
    main(*sys.argv[1:])
