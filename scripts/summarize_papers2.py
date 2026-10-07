"""Tables for the second batch of papers (results/papers2/*.json), written
into PAPERS.md between the RESULTS2 markers."""
import glob
import json
import os
import re

out = []

# ------------------------------------------------------------------ Cornucopia
rows = {}
for f in sorted(glob.glob("results/papers2/cornucopia_q*_r*_[XZ].json")):
    r = json.load(open(f))
    rows.setdefault(tuple(r["code"]), {})[r["basis"]] = r
out += ["**Cornucopia codes** (arXiv:2608.02773; the paper's 12-layer schedule and fault model, 6 rounds). "
        "Bold = exact; otherwise certified lower bound – verified upper bound.", "",
        "| code | paper: code distance | paper: circuit distance | circuit distance, Z basis | circuit distance, X basis | seconds (Z, X) |",
        "|---|---:|---:|---:|---:|---|"]


def cell(r):
    if r is None:
        return "not run"
    lb, ub = r.get("certified_lower_bound"), r.get("certified_upper_bound")
    if lb is not None and ub is not None and lb == ub:
        return f"**{lb}**"
    return f"{lb if lb is not None else '?'} – {ub if ub is not None else '?'}"


for code in sorted(rows):
    v = rows[code]
    any_r = next(iter(v.values()))
    secs = ", ".join(str(round(v[b]["seconds"])) if b in v and "seconds" in v[b] else "running" for b in "ZX")
    out.append(f"| [[{code[0]},{code[1]},{code[2]}]] | {code[2]} | ≤ {any_r['paper_circuit_distance_upper_bound']} | "
               f"{cell(v.get('Z'))} | {cell(v.get('X'))} | {secs} |")
out.append("")

# ------------------------------------------------------------------ code-distance checks
for path, title in (("results/papers2/selfdual_bb_code_distance.json",
                     "**Self-dual bivariate bicycle codes** (arXiv:2510.05211, Tables 1 and 2; no circuit published)"),
                    ("results/papers2/gala_code_distance.json",
                     "**GALA codes over abelian groups** (arXiv:2608.07431, Tables S3 and S5; no usable circuit published)")):
    if not os.path.exists(path):
        continue
    r = json.load(open(path))
    codes = r["codes"]
    ok = [c for c in codes if c["agrees"]]
    ds = sorted({c["claimed"][2] for c in codes})
    ns = [c["claimed"][0] for c in codes]
    secs = sum(c["seconds"] for c in codes)
    out += [title + f": {len(ok)} of {len(codes)} codes rebuilt from the printed definitions have exactly the claimed "
            f"[[n,k,d]] (n = {min(ns)} to {max(ns)}, d = {ds[0]} to {ds[-1]}; exhaustive below d plus a weight-d "
            f"logical operator; {secs:.0f} s in total on one core).", ""]
    bad = [c for c in codes if not c["agrees"]]
    if bad:
        out += ["Differing: " + ", ".join(f"claimed {c['claimed']}, found [[{c['n']},{c['k']},{c['d']}]]" for c in bad), ""]

# ------------------------------------------------------------------ cross-check with the authors' repository
p = "results/papers2/cornucopia_crosscheck_repo.json"
if os.path.exists(p):
    r = json.load(open(p))
    ok = [c for c in r["codes"].values() if c["HX"]["equal_as_row_sets"] and c["HZ"]["equal_as_row_sets"]
          and c["x_check_orders_equal"] and c["z_check_orders_equal"]]
    out += [f"Cross-check of the rebuilt Cornucopia circuits with the authors' repository (commit {r['commit'][:10]}): "
            f"for {len(ok)} of {len(r['codes'])} codes the check matrices are equal as sets of rows and every check "
            f"meets its data qubits in the same order as in the authors' Stim circuit.", ""]

# ------------------------------------------------------------------ Kasai page
p = "results/papers2/kasai_code_distance_server.json"       # the server run includes the d = 18 instance
if not os.path.exists(p):
    p = "results/papers2/kasai_code_distance.json"
if os.path.exists(p):
    r = json.load(open(p))
    extra = "results/papers2/kasai_492.json"                # the d = 20 instance, run separately
    if os.path.exists(extra):
        have = {c["file"] for c in r["codes"]}
        r["codes"] += [c for c in json.load(open(extra))["codes"] if c["file"] not in have]
    done = [c for c in r["codes"] if c.get("d") is not None]
    skipped = [c for c in r["codes"] if c.get("skipped")]
    op = [c for c in r["codes"] if c.get("d") is None and not c.get("skipped")]
    line = ("**Pair-partition CSS codes** (data page of K. Kasai, the family behind arXiv:2607.14091 and the CSS tables of "
            "2609.30069): exact distances of the downloaded instances: " +
            ", ".join(f"[[{c['n']},{c['k']},{c['d']}]]" for c in sorted(done, key=lambda c: (c["n"], c["d"]))) + ". ")
    stated = [c for c in done if (c.get("d_in_file") or (c.get("label_in_file_name") or [0, 0, None])[2]) is not None]
    agree = [c for c in stated if c["d"] == (c.get("d_in_file") or c["label_in_file_name"][2])]
    line += f"{len(agree)} of {len(stated)} with a distance stated in the file or its name agree with it."
    if op:
        line += " Not finished: " + ", ".join(f"{c['file']} (lower bound {c['lower_bound']})" for c in op) + "."
    if skipped:
        line += " Not attempted: " + ", ".join(c["file"] for c in skipped) + "."
    out += [line, ""]

# ------------------------------------------------------------------ designed schedules
rows = []
for f in glob.glob("results/papers2/design/sdbb*.json"):
    if not re.fullmatch(r"sdbb\d+\.json", os.path.basename(f)):
        continue
    r = json.load(open(f))
    rows.append(r)
rows.sort(key=lambda r: r["code"][0])
if rows:
    loss = {}
    for r in rows:
        if r["optimal_over_family"]:
            loss[r["code"][2] - r["best_circuit_distance"]] = loss.get(r["code"][2] - r["best_circuit_distance"], 0) + 1
    ver = sum(1 for r in rows if all(r.get("verification", {}).get(b, {}).get("verified") for b in "ZX"))
    out += ["**Designed schedules for the self-dual bivariate bicycle codes** (no published circuit). Family: an X-check "
            "round followed by a Z-check round, every check using the same gate order; all 5040 inequivalent orders "
            "evaluated exactly, so the value is the optimum of the family. "
            f"{len(rows)} codes done; loss against the code distance: " +
            ", ".join(f"{v} codes lose {k}" for k, v in sorted(loss.items())) +
            f". Best order verified on a Stim circuit in both bases for {ver} codes.", "",
            "| code | best circuit distance | example gate order | all orders evaluated |", "|---|---:|---|---|"]
    for r in rows:
        n, k, d = r["code"]
        b = r["best_circuit_distance"]
        out.append(f"| [[{n},{k},{d}]] | {'**' + str(b) + '**' if r['optimal_over_family'] else '≥ ' + str(b)} | "
                   f"{' '.join(r['example_order'])} | {'yes' if r['optimal_over_family'] else str(r['orders_processed']) + ' of ' + str(r['orders'])} |")
    out.append("")
par = []
for f in glob.glob("results/papers2/design/sdbb*_parallel.json"):
    if re.fullmatch(r"sdbb\d+_parallel\.json", os.path.basename(f)):
        par.append(json.load(open(f)))
par.sort(key=lambda r: r["code"][0])
if par:
    seq = {tuple(r["code"]): r["best_circuit_distance"] for r in rows}

    def cd(v):
        lb, ub = v.get("certified_lower_bound"), v.get("certified_upper_bound")
        return f"**{lb}**" if lb is not None and lb == ub else f"{lb} – {ub if ub is not None else '?'}"
    fam = {}
    for f in glob.glob("results/papers2/design/sdbb*_parallel_family.json"):
        fr = json.load(open(f))
        fam[tuple(fr["code"])] = fr
    out += ["**Parallel depth-8 circuits designed here for the self-dual bivariate bicycle codes** (X and Z checks in "
            "the same eight layers, one ancilla per check; the X order has a palindromic sublattice pattern and the Z "
            "order is its mirror image). Column 4: the gate order is chosen among the 3456 such orders by the "
            "time-collapsed bound and the circuit distance of the best few is determined exactly (6 cycles). "
            "Column 5, for the small codes: the exact circuit distance of all 3456 orders, i.e. the optimum of the family.", "",
            "| code | best sequential circuit | parallel circuit: collapsed bound | circuit distance (Z, X) of the order chosen by the bound | optimum over all 3456 mirror orders (number of orders reaching it) | gate order of the X checks |",
            "|---|---:|---:|---|---|---|"]
    for r in par:
        n, k, d = r["code"]
        z, x = r["circuit_distance"]["Z"], r["circuit_distance"]["X"]
        for basis, v in (("Z", z), ("X", x)):       # a longer re-run of the same circuit, where one exists
            q = f"results/papers2/design/sdbb_parallel{n}_rounds6_{basis}.json"
            if os.path.exists(q):
                rr = json.load(open(q))
                v["certified_lower_bound"] = max(v["certified_lower_bound"], rr.get("certified_lower_bound") or 0)
                if rr.get("certified_upper_bound"):
                    v["certified_upper_bound"] = min(v.get("certified_upper_bound") or 99, rr["certified_upper_bound"])
        fr = fam.get((n, k, d))
        order = r["best_order"]
        if fr and fr.get("best_circuit_distance") is not None:
            cnt = fr["circuit_distance_histogram"][str(fr["best_circuit_distance"])]
            bb = fr.get("best_orders_both_bases") or []
            okb = bool(bb) and all(list(x_["Z"]) == list(x_["X"]) == [fr["best_circuit_distance"]] * 2 for x_ in bb)
            ftxt = f"**{fr['best_circuit_distance']}** ({cnt})" + ("" if okb else "; Z basis") + \
                   (f"; {fr['n_not_exact']} orders open" if fr.get("n_not_exact") else "")
            if fr["best_circuit_distance"] > (z.get("certified_lower_bound") or 0):
                order = fr["best_orders"][0]
        else:
            ftxt = "–"
        out.append(f"| [[{n},{k},{d}]] | {seq.get((n, k, d), '–')} | {r['best_collapsed_distance']} | {cd(z)}, {cd(x)} | "
                   f"{ftxt} | {' '.join(order)} |")
    out.append("")
fl = []
for f in sorted(glob.glob("results/papers2/design/sdbb*_parallel_funnel*.json")):
    r = json.load(open(f))
    n, k, d = r["code"]
    wh = r["window_distance_histogram_of_rejected"]
    ev = r.get("evaluated", [])
    vals = sorted({min(e[b][0] for b in "ZX" if b in e and isinstance(e[b][0], int)) for e in ev if any(b in e for b in "ZX")})
    fl.append(f"[[{n},{k},{d}]], target {r['target']}: {sum(wh.values())} orders have a fault set of weight at most "
              f"{max(map(int, wh))} within two consecutive cycles, {len(r['survivors'])} pass the filter, "
              f"{len(r['stage1_timeouts'])} are undecided within the time limit" +
              (f"; {len(ev)} of the undecided evaluated exactly: {', '.join(map(str, vals))}" if ev else ""))
if fl:
    out += ["Filtered search for a mirror order with the full distance (windows of one and two cycles, then exact "
            "evaluation of a few candidates; not exhaustive): " + ". ".join(fl) + ".", ""]
p = "results/papers2/design/gala132_parallel_all.json"
if not os.path.exists(p):
    p = "results/papers2/design/gala132_parallel.json"
if os.path.exists(p):
    r = json.load(open(p))
    cands = [c for c in r.get("candidates", []) if "X" in c]
    line = ("**Parallel 12-layer circuit designed here for GALA [[132,30,12]]** (palindromic label order for the X "
            f"checks, reversed order for the Z checks). {r['orders_scored']} random orders scored by the collapsed bound "
            f"up to {r['cap']}: {r['collapsed_distance_histogram']}. ")
    if cands:
        tally = {}
        for c in cands:
            lo = min(c[b]["certified_lower_bound"] for b in "ZX")
            hi = max(c[b]["certified_upper_bound"] or 99 for b in "ZX")
            exact = all(c[b]["certified_lower_bound"] == c[b]["certified_upper_bound"] for b in "ZX")
            key = f"{lo}" if exact else f"{lo} (one basis {lo}–{hi})"
            tally[key] = tally.get(key, 0) + 1
        top = max(min(c[b]["certified_lower_bound"] for b in "ZX") for c in cands)
        ex = next(c for c in cands if all(c[b]["certified_lower_bound"] == top == c[b]["certified_upper_bound"] for b in "ZX"))
        line += (f"Circuit distance (smaller of the two bases) of the {len(cands)} orders evaluated among those with bound 8: "
                 + ", ".join(f"{v} × {k}" for k, v in sorted(tally.items())) +
                 f". An order with circuit distance exactly {top} in both bases: {' '.join(ex['order'])}.")
    out += [line, ""]
two = []
for f in sorted(glob.glob("results/papers2/design/sdbb*_two_class.json")):
    r = json.load(open(f))
    two.append(f"[[{r['code'][0]},{r['code'][1]},{r['code'][2]}]]: {r['uniform_best']} with one order, "
               f"{r['best_two_class']} with two")
if two:
    out += ["Two gate orders on alternating checks (each class varied over all 5040 orders, starting from the best "
            "uniform order): " + "; ".join(two) + ".", ""]
p = "results/papers2/design/gala132.json"
if os.path.exists(p):
    r = json.load(open(p))
    po = r.get("paper_order", {})
    line = ("**Designed schedules for GALA [[132,30,12]]** (same family, twelve gates per check). The paper's own layer "
            f"order, run as an X round followed by a Z round, has circuit distance {po.get('distance')}. ")
    if "best_value_found" in r:
        b = r["best_orders"][0] if r.get("best_orders") else None
        line += (f"Search over {r['orders_evaluated']} orders: best value {r['best_value_found']}"
                 f"{' (lower bound, not yet resolved)' if r['best_is_lower_bound_only'] else ' (exact)'}"
                 + (f", e.g. {' '.join(b['order'])}" if b else "") + f". Histogram of evaluated orders: {r.get('all_evaluated_histogram')}.")
    out += [line, ""]

text = "\n".join(out)
print(text)
if os.path.exists("docs/PAPERS.md"):
    t = open("docs/PAPERS.md").read()
    a, b = "<!-- RESULTS2:BEGIN -->", "<!-- RESULTS2:END -->"
    if a in t and b in t:
        t = t[:t.index(a) + len(a)] + "\n" + text + "\n" + t[t.index(b):]
        open("docs/PAPERS.md", "w").write(t)
