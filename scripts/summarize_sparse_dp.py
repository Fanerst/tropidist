"""Tables and the figure of results/sparse_dp/README.md from the records of scripts/sparse_dp_eval.py and
scripts/sparse_dp_query.py.

usage: python scripts/summarize_sparse_dp.py [results/sparse_dp]
Writes results/sparse_dp/tables.md (pasted into the README) and results/sparse_dp/states_per_cut.png.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# records of scripts/sparse_dp_eval.py; for a configuration recorded twice the later file wins
STREAMS = ("narrow", "lowwidth", "bb", "circuits", "d11", "schedule", "surface11", "mitm")
# records of scripts/sparse_dp_query.py for the superdense d11 circuit
D11 = (("d11_K10_a5", "K = 10, a = 5"), ("d11_K10_schedule", "K = 10, schedule"), ("d11_K11_a6", "K = 11, a = 6"),
       ("d11_K11_schedule", "K = 11, schedule + 1"))
WIDTH_NOTE = ('Width: the rows of the trellis active at its widest cut, counting the reduced logical row; the dense '
              'table there has 2^width entries. It exceeds the cut rank by one on every color code except d25 and on '
              'the concatenated Steane and hypercube codes, where the reduced logical row is active at the widest cut '
              'without adding to the rank, and equals the cut rank on the bivariate bicycle codes and the circuits.')
REGIME = {"color": "narrow", "lowwidth": "narrow", "bb": "expanding", "wjh": "local circuit"}
SPARSE = ("sparse:mitm:c:0:schedule", "sparse:mitm:c:0:auto", "sparse:mitm:c:1:auto", "sparse:forward:c:1",
          "sparse:forward:c:0")
SHORT = {"sparse:mitm:c:0:schedule": "MITM sched", "sparse:mitm:c:0:auto": "MITM", "sparse:mitm:c:1:auto": "MITM+h",
         "sparse:forward:c:1": "fwd+h", "sparse:forward:c:0": "fwd"}
NUMPY = {"sparse:mitm:c:0:schedule": "sparse:mitm:numpy:0:schedule", "sparse:mitm:c:0:auto": "sparse:mitm:numpy:0:auto"}


def load(d):
    """All records, merged per instance.  A completed run is not replaced by one that stopped at a budget."""
    out = {}
    for s in STREAMS:
        f = os.path.join(d, s + ".json")
        if not os.path.exists(f):
            continue
        for tok, inst in json.load(open(f))["instances"].items():
            cur = out.setdefault(tok, {"runs": {}})
            if "info" in inst:
                cur["info"] = inst["info"]
            for cfg, run in inst["runs"].items():
                old = cur["runs"].get(cfg)
                if old is not None and old.get("result", {}).get("status") != "budget" and \
                        run.get("result", {}).get("status") in ("budget", "error"):
                    continue
                cur["runs"][cfg] = run
    # the C tables hold 56 row slots: wider trellises ran with the numpy tables
    for tok, inst in out.items():
        for c, n in NUMPY.items():
            if n in inst["runs"] and inst["runs"].get(c, {}).get("result", {}).get("status") in (None, "error"):
                inst["runs"][c] = dict(inst["runs"][n], numpy=True)
    d11 = {key: json.load(open(os.path.join(d, key + ".json"))) for key, _ in D11
           if os.path.exists(os.path.join(d, key + ".json"))}
    inst = out.get("wjh:superdense:11")
    if inst is not None:
        for cfg, key, ukey in (("sparse:mitm:c:0:auto", "d11_K10_a5", "d11_K11_a6"),
                               ("sparse:mitm:c:0:schedule", "d11_K10_schedule", "d11_K11_schedule")):
            if key not in d11 or ukey not in d11:
                continue
            low, up = d11[key], d11[ukey]
            assert low["value"] is None and up["value"] == 11 and up["witness_ok"]
            inst["runs"][cfg] = {
                "config": cfg, "d11": True, "seconds": low["seconds"] + up["seconds"],
                "maxrss_gb": max(low["maxrss_gb"], up["maxrss_gb"]),
                "result": {"distance": 11, "witness_ok": True, "status": "exact"},
                "lower_run": {"K": 10, "queries": [_summary(low)], "seconds": low["seconds"],
                              "per_cut": {k: low[k] for k in ("forward_counts", "backward_counts", "changed_counts")}},
                "upper_run": {"K": 11, "queries": [_summary(up)], "seconds": up["seconds"]}}
    return out, d11


def _summary(r):
    out = {k: v for k, v in r.items() if not k.endswith("_counts") and k not in ("witness", "split_values", "width")}
    for k in ("forward_counts", "backward_counts", "changed_counts"):
        if k in r:
            out[k.replace("_counts", "_states_total")] = int(sum(r[k]))
    return out


def order_key(token):
    kind = token.split(":")[0]
    rank = {"color": 0, "lowwidth": 1, "bb": 2, "wjh": 3}[kind]
    tail = token.split(":")[1:]
    fam = tail[0] if kind == "wjh" else ""
    num = int("".join(ch for ch in tail[-1] if ch.isdigit()) or 0)
    return rank, fam, num, token


def name(token):
    if token.startswith("wjh:"):
        fam, d = token.split(":")[1:]
        return "%s d%s" % (fam, d)
    return token.replace("lowwidth:", "").replace("bb:", "").replace("color:", "color d")


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
    mark = "†" if run.get("numpy") else ("‡" if run.get("d11") else "")
    if st == "exact" and r.get("distance") is not None:
        return str(r["distance"]) + mark + ("" if r.get("witness_ok", True) else " (bad witness)")
    if st == "timeout":
        return "≥ %s (timeout)" % r.get("lower_bound", "?")
    if st and st.startswith("no solution"):
        return "≥ %d" % r["lower_bound"] + mark
    if st == "budget":
        low = run.get("lower_run")
        if low and low.get("queries") and all(q["value"] is None for q in low["queries"]):
            return "≥ %d (budget at K = %d)%s" % (low["K"] + 1, low["K"] + 1, mark)
        return "budget" + mark
    return str(st) + mark


def exact(run):
    return run is not None and run.get("result", {}).get("status") == "exact"


def search_last(run):
    """Seconds of the search's last two thresholds (d - 1 and d), the part comparable to the two sparse runs."""
    if not run or "runs" not in run:
        return None
    return sum(x["seconds"] for x in run["runs"][-2:])


def sparse_stats(run):
    """(splits, peak states, peak table bytes, states of the K = d - 1 run summed over cuts and observables)."""
    if not run or "lower_run" not in run:
        return None
    qs = run["lower_run"]["queries"]
    peak = max(q["peak_states"] for q in qs)
    tb = max(q.get("peak_table_bytes", 0) for q in qs)
    tot = sum(q.get("forward_states_total", 0) + q.get("backward_states_total", 0) for q in qs)
    splits = sorted({str(q.get("split")) for q in qs if q.get("split")})
    return splits, peak, tb, tot


def short_split(s):
    """A schedule 'a@cut,a@cut,...' as its values along the sweep, without the forced ends (all weight in one
    direction at the first and the last cuts)."""
    if "@" not in s:
        return s
    vals = [int(x.split("@")[0]) for x in s.split(",")]
    if len(vals) > 2:
        vals = vals[1:-1]
    return "→".join(str(v) for v in vals)


def tables(res, d11):
    toks = sorted(res, key=order_key)
    out = []
    out.append("### Validation: distance found by each method\n")
    out.append("| instance | known d | " + " | ".join(SHORT[c] for c in SPARSE) + " | dense DP | search |")
    out.append("|---|---|" + "---|" * (len(SPARSE) + 2))
    for t in toks:
        inst = res[t]
        info = inst.get("info", {})
        known = info.get("distance_known")
        known = str(known) if known is not None else "10..11 (open)"
        cells = [value(inst["runs"].get(c)) for c in SPARSE + ("dense", "search")]
        out.append("| %s | %s | %s |" % (name(t), known, " | ".join(cells)))
    out.append("")
    out.append("† numpy tables (the trellis needs 62 row slots, the C tables hold 56). ‡ dedicated runs, see "
               "*Superdense d11*.\n")
    out.append("### Time (seconds, one thread)\n")
    out.append("Sparse: the sweep at K = d − 1 for every observable, plus the one at K = d that stops at its first "
               "solution and returns the witness; the split probes are included. Search: every threshold from "
               "K = 1, and in brackets its last two (d − 1 and d). Dense DP: one untruncated sweep per observable. "
               "Bold: the fastest method. " + WIDTH_NOTE + "\n")
    out.append("| instance | regime | columns | width | d | dense DP | search | " +
               " | ".join(SHORT[c] for c in SPARSE) + " |")
    out.append("|---|---|---|---|---|---|---|" + "---|" * len(SPARSE))
    for t in toks:
        inst = res[t]
        info = inst.get("info", {})
        runs = inst["runs"]
        d = info.get("distance_known") or info.get("upper_known")
        times = {c: runs[c]["seconds"] for c in ("dense", "search") + SPARSE if exact(runs.get(c))}
        best = min(times, key=times.get) if times else None

        def cell(c):
            r = runs.get(c)
            if not exact(r):
                return value(r)
            txt = fmt_t(r["seconds"]) + ("†" if r.get("numpy") else "") + ("‡" if r.get("d11") else "")
            if c == "search":
                txt += " (%s)" % fmt_t(search_last(r))
            return "**%s**" % txt if c == best else txt
        out.append("| %s | %s | %d | %d | %s | %s | %s | %s |" % (
            name(t), REGIME[t.split(":")[0]], info.get("columns", 0), info.get("cut_rank", 0), d, cell("dense"),
            cell("search"), " | ".join(cell(c) for c in SPARSE)))
    out.append("")
    out.append("### States kept, against the dense table\n")
    out.append("2^w: entries of the dense table at the widest cut; dense work: entries the dense DP updates per "
               "observable. For the sparse sweeps at K = d − 1: the split a (for a schedule, its values along the "
               "sweep), the largest table, the states summed over all cuts, both directions and all observables, "
               "and the bytes of the tables held at the peak (checkpoints included); then the process's peak "
               "memory.\n")
    out.append("| instance | 2^w | dense work | MITM sched a | peak | total | tables | MITM a | peak | total | "
               "fwd+h peak | fwd+h total | peak memory (MITM sched) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t in toks:
        inst = res[t]
        info = inst.get("info", {})
        s = sparse_stats(inst["runs"].get("sparse:mitm:c:0:schedule"))
        m = sparse_stats(inst["runs"].get("sparse:mitm:c:0:auto"))
        f = sparse_stats(inst["runs"].get("sparse:forward:c:1"))
        sr = inst["runs"].get("sparse:mitm:c:0:schedule", {})
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name(t), fmt_n(2.0 ** info.get("cut_rank", 0)), fmt_n(info.get("dense_work_per_query")),
            "; ".join(short_split(x) for x in s[0]) if s else "–", fmt_n(s[1]) if s else "–",
            fmt_n(s[3]) if s else "–", fmt_bytes(s[2]) if s else "–",
            ",".join(m[0]) if m else "–", fmt_n(m[1]) if m else "–", fmt_n(m[3]) if m else "–",
            fmt_n(f[1]) if f else "–", fmt_n(f[3]) if f else "–",
            ("%.2f GB" % sr["maxrss_gb"]) if sr.get("maxrss_gb") is not None else "–"))
    out.append("")
    if d11:
        out.append("### Superdense d11: the four runs\n")
        out.append("| run | split a | result | backward sweep | forward sweep | traceback | total | largest table | "
                   "states (all cuts) | peak memory |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for key, label in D11:
            r = d11.get(key)
            if r is None:
                continue
            res_txt = "none of weight ≤ %d" % r["K"] if r["value"] is None else \
                "weight %d, witness %s" % (r["value"], "checked" if r["witness_ok"] else "FAILED")
            tot = sum(r["forward_counts"]) + sum(r["backward_counts"])
            out.append("| %s | %s | %s | %s s | %s s | %s | %s s | %s | %s | %.1f GB |" % (
                label, short_split(str(r["split"])), res_txt, fmt_t(r["backward_seconds"]),
                fmt_t(r["forward_seconds"]), (fmt_t(r["traceback_seconds"]) + " s") if r.get("traceback_seconds")
                else "–", fmt_t(r["seconds"]), fmt_n(r["peak_states"]), fmt_n(tot), r["maxrss_gb"]))
        out.append("")
    return "\n".join(out)


# reference palette of the dataviz guidance (categorical slots 1-3, valid all-pairs in light mode) and its inks
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")
NEUTRAL, SURFACE, INK, INK2 = "#8f8e88", "#fcfcfb", "#0b0b0b", "#52514e"


def figure(res, path, picks):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cfg = "sparse:mitm:c:0:schedule"
    picks = [t for t in picks if t in res and "lower_run" in res[t]["runs"].get(cfg, {})]
    if not picks:
        return
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "text.color": INK})
    fig, axes = plt.subplots(1, len(picks), figsize=(3.6 * len(picks), 3.4), squeeze=False, facecolor=SURFACE)
    handles = []
    for ax, t in zip(axes[0], picks):
        ax.set_facecolor(SURFACE)
        inst = res[t]
        width = inst["info"]["width"]
        run = inst["runs"][cfg]["lower_run"]
        pc = run["per_cut"]
        x = list(range(len(width)))
        lw = 1.1                                              # about 2 px at the saved resolution
        hs = [ax.semilogy(x, [2.0 ** w for w in width], color=NEUTRAL, lw=lw, label="dense table, 2^w states")[0],
              ax.semilogy(x, [max(v, 0.8) for v in pc["backward_counts"]], color=SERIES[0], lw=lw,
                          label="MITM backward table (weight ≤ K − a)")[0],
              ax.semilogy(x, [max(v, 0.8) for v in pc["forward_counts"]], color=SERIES[1], lw=lw,
                          label="MITM forward table (weight ≤ a − 1)")[0]]
        fw = inst["runs"].get("sparse:forward:c:1", {}).get("lower_run", {}).get("per_cut")
        if fw:
            hs.append(ax.semilogy(x, [max(v, 0.8) for v in fw["forward_counts"]], color=SERIES[2], lw=lw,
                                  label="forward only, with h (weight ≤ K)")[0])
        if len(hs) > len(handles):
            handles = hs
        ax.set_title("%s, K = %d" % (name(t), run["K"]), fontsize=9.5, color=INK)
        ax.set_xlabel("cut (columns processed)")
        ax.grid(color="#e4e3df", lw=0.6, which="major")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0][0].set_ylabel("states kept at the cut")
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path, dpi=130, facecolor=SURFACE)


def main(d=os.path.join(ROOT, "results", "sparse_dp")):
    res, d11 = load(d)
    md = tables(res, d11)
    open(os.path.join(d, "tables.md"), "w").write(md + "\n")
    figure(res, os.path.join(d, "states_per_cut.png"),
           ["color:27", "bb:gross", "wjh:superdense:9", "wjh:superdense:11"])
    print(md)


if __name__ == "__main__":
    main(*sys.argv[1:])
