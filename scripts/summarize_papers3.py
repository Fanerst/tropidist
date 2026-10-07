"""Tables for the third batch of papers (results/papers3/), written into
PAPERS.md between the RESULTS3 markers.  Only the lead's server runs
(results/papers3/<slug>/server_*.json) are tabulated."""
import glob
import json
import os
import re

R = "results/papers3"
out = []


def load(slug, key, basis):
    """Best available run for one circuit and basis: the run with the full search if there is one."""
    best = None
    for pat in (f"{R}/{slug}/server_full2_{key}_{basis}.json", f"{R}/{slug}/server_full_{key}_{basis}.json",
                f"{R}/{slug}/server_{key}_{basis}.json"):
        if os.path.exists(pat):
            r = json.load(open(pat))
            if best is None or (r.get("certified_lower_bound") or 0) > (best.get("certified_lower_bound") or 0) \
                    or (r.get("certified_upper_bound") or 99) < (best.get("certified_upper_bound") or 99):
                if best is not None:        # combine: larger lower bound, smaller upper bound
                    r = dict(r)
                    r["certified_lower_bound"] = max(r.get("certified_lower_bound") or 0, best.get("certified_lower_bound") or 0)
                    ubs = [x for x in (r.get("certified_upper_bound"), best.get("certified_upper_bound")) if x]
                    r["certified_upper_bound"] = min(ubs) if ubs else None
                best = r
    return best


def cell(r):
    if r is None:
        return "not run"
    lb, ub = r.get("certified_lower_bound"), r.get("certified_upper_bound")
    if lb is not None and ub is not None and lb == ub:
        return f"**{lb}**"
    return f"{lb if lb is not None else '?'} – {ub if ub is not None else '?'}"


def both(slug, key):
    return f"{cell(load(slug, key, 'Z'))}, {cell(load(slug, key, 'X'))}"


def secs(slug, key):
    v = [load(slug, key, b) for b in "ZX"]
    return ", ".join(str(round(r["seconds"])) if r and r.get("seconds") is not None else "–" for r in v)


# ------------------------------------------------------------------ published circuits with a stated number
out += ["**Circuits with a stated circuit distance.** Six-cycle memory experiments, both bases; bold = exact "
        "(certified lower bound = replayed fault set); otherwise lower bound – upper bound.", "",
        "| paper | circuit | paper's number | circuit distance (Z, X) | seconds (Z, X) |", "|---|---|---|---|---|"]
if load("lrgross", "lr11", "Z"):
    out.append(f"| left-right circuits, 2603.05481 | gross code [[144,12,12]], explicit schedule | 11 (conjecture) | "
               f"{both('lrgross', 'lr11')} | {secs('lrgross', 'lr11')} |")
ROUTING = [("54", "[[54,8,6]]", "≤ 6"), ("70", "[[70,8,7]]", "≤ 7"), ("80", "[[80,8,8]]", "≤ 8"), ("90", "[[90,8,9]]", "≤ 9"),
           ("100", "[[100,8,10]]", "≤ 9"), ("110", "[[110,8,11]]", "≤ 10"), ("140_12", "[[140,8,12]]", "≤ 11"),
           ("140_13", "[[140,8,13]]", "≤ 12"), ("200_24", "[[200,24,14]], weight 11", "≤ 14"),
           ("200_16", "[[200,16,17]], weight 11", "≤ 17")]
for key, name, claim in ROUTING:
    if load("routing", key, "Z"):
        out.append(f"| routing codes, 2606.25330 | {name} | {claim} | {both('routing', key)} | {secs('routing', key)} |")
conv = json.load(open(f"{R}/star/table2_conventions.json")) if os.path.exists(f"{R}/star/table2_conventions.json") else None
if conv:
    def cv(key, s):
        v = conv[f"{key}:{s}"]
        return ", ".join(f"**{v[b][0]}**" if v[b][0] == v[b][1] else f"{v[b][0]} – {v[b][1]}" for b in "ZX")
    for key, name, claim in (("42", "[[42,6,6]]", "5"), ("66", "[[66,6,8]]", "none"), ("78", "[[78,6,10]]", "none")):
        assert conv[f"{key}:1243"] == conv[f"{key}:2134"]
        out.append(f"| STAR architecture, 2606.25011 | {name}, schedule of Table 2, index convention that reproduces the "
                   f"paper's histogram | {claim} | {cv(key, '1243')} | – |")
        out.append(f"| STAR architecture, 2606.25011 | {name}, same table read with B_i = A_i^T | none | {cv(key, '1234')} | – |")
for key, name in (("102", "[[102,22,9]]"), ("70", "[[70,6,9]]"), ("54", "[[54,2,10]]")):
    if load("walkingcat", key, "Z"):
        out.append(f"| Walking Cat, 2604.19481 | {name}, terms numbered as printed | 9 | {both('walkingcat', key)} | "
                   f"{secs('walkingcat', key)} |")
out.append("")

# ------------------------------------------------------------------ shift circuits
variants = [v for v in "sdmb" if glob.glob(f"{R}/shift/server_*{v}_Z.json")]
names = {"s": "static (Table II)", "d": "dynamic pair repeated (Table III)", "m": "one dynamic pair among static cycles",
         "b": "static, gate order of Table III"}
if variants:
    out += ["**Time-dynamic shift circuits** (2601.09911; paper's estimate for every code: the bound in the second "
            "column). Circuit distance (Z, X), six cycles.", "",
            "| code | paper | " + " | ".join(names[v] for v in variants) + " |", "|---|---|" + "---|" * len(variants)]
    for n, name, claim in (("72", "[[72,12,6]]", "≤ 6"), ("120", "[[120,8,12]]", "≤ 10"), ("144", "[[144,12,12]]", "≤ 10"),
                           ("170", "[[170,16,10]]", "≤ 10")):
        out.append(f"| {name} | {claim} | " + " | ".join(both("shift", n + v) for v in variants) + " |")
    out.append("")

# ------------------------------------------------------------------ shift circuits: every numbering of the monomials
lines = []
for n, name in (("72", "[[72,12,6]]"), ("120", "[[120,8,12]]"), ("144", "[[144,12,12]]"), ("170", "[[170,16,10]]")):
    q = f"{R}/shift/numberings_{n}.json"
    if not os.path.exists(q):
        continue
    r = json.load(open(q))
    rows_ = next(v for v in r.values() if isinstance(v, list) and v and isinstance(v[0], dict) and "A" in v[0])
    def val(b):
        return b[0] if isinstance(b, list) and b[0] == b[1] else b if isinstance(b, int) else None
    hs, hd = {}, {}
    for x in rows_:
        for flag, bounds, h in ((x.get("valid_s"), x.get("bounds_s"), hs), (x.get("valid_d"), x.get("bounds_d"), hd)):
            if flag and bounds:
                z, xx = val(bounds["Z"]), val(bounds["X"])
                k = min(z, xx) if z is not None and xx is not None else "open"
                h[k] = h.get(k, 0) + 1
    fmt = lambda h: ", ".join(f"{v} × {k}" for k, v in sorted(h.items(), key=lambda t: str(t[0])))
    lines.append(f"| {name} | {sum(hs.values())}: {fmt(hs)} | {sum(hd.values())}: {fmt(hd)} |")
if lines:
    out += ["**Shift circuits, every numbering of the monomials** (36 ways to call the printed monomials A_1..A_3, "
            "B_1..B_3). Valid numberings and their circuit distance (smaller of the two bases):", "",
            "| code | static table: valid numberings, distances | dynamic table: valid numberings, distances |", "|---|---|---|"]
    out += lines + [""]

# ------------------------------------------------------------------ STAR: all valid schedules, all index conventions
p = f"{R}/star/dictionary_42.json"
if os.path.exists(p):
    r = json.load(open(p))
    def hs(h):
        return ", ".join(f"{v} at {k}" for k, v in sorted(h.items()))
    match = [c for c in r["conventions"] if c["distance_histogram"] == {"4": 192, "5": 20}]
    ident = next(c for c in r["conventions"] if c["sigma"] == [1, 2, 3, 4])
    six = [c for c in r["conventions"] if "6" in c["distance_histogram"]]
    out += [f"**STAR, every valid depth-8 schedule of the [[42,6,6]] code** ({r['family']} schedules; paper: 192 with fault "
            "distance 4 and 20 with 5, the schedule of Table 2 among the 20). The paper does not print which monomial each "
            "B_i is, so all 24 conventions B_i = A_σ(i)^T were run; each keeps all "
            f"{r['family']} schedules valid. Exact circuit distance, smaller of the two bases: "
            f"{len(match)} conventions (σ = {' and '.join(''.join(map(str, c['sigma'])) for c in match)}) give exactly the "
            f"paper's histogram, {hs(match[0]['distance_histogram'])}, with the Table 2 schedule at "
            f"{match[0]['table2_schedule']['Z'][0]}; the convention B_i = A_i^T gives {hs(ident['distance_histogram'])}, "
            f"with the Table 2 schedule at {ident['table2_schedule']['Z'][0]}. Schedules of distance 6 exist under "
            f"{len(six)} of the 24 conventions.", ""]
    cc = []
    for b in "ZX":
        q = f"{R}/star/crosscheck_full_42_{b}.json"
        if os.path.exists(q):
            x = json.load(open(q))
            cc.append(f"{b}: no fault set of weight ≤ {x['certified_lower_bound'] - 1} in the full detector error model "
                      f"({x['columns']} mechanisms, {x['detectors']} detectors, {x['seconds']:.0f} s); Stim's own heuristic "
                      f"search finds {x.get('stim_heuristic_upper_bound')}")
    if cc:
        out += ["Independent check of the distance-6 circuit (Table 2 read with B_i = A_i^T) without the sector and collapse "
                "reductions: " + "; ".join(cc) + ".", ""]

# ------------------------------------------------------------------ Walking Cat: all numberings
lines = []
for key, name in ((102, "[[102,22,9]]"), (70, "[[70,6,9]]"), (54, "[[54,2,10]]")):
    p = f"{R}/walkingcat/labelings_{key}.json"
    if not os.path.exists(p):
        continue
    r = json.load(open(p))
    h = r["circuit_distance_histogram"]
    s = f"{name}: {r['valid']} numberings, Z-basis circuit distance " + ", ".join(f"{v} × {k}" for k, v in sorted(h.items()))
    top = r.get("top_numberings_both_bases")
    if top:
        k = max(int(x) for x in h if x.isdigit())
        nboth = sum(1 for t in top if t["Z"] == [k, k] and t["X"] == [k, k])
        xs = sorted({tuple(t["X"]) for t in top})
        s += (f"; of the {len(top)} numberings at {k}, {nboth} also have {k} in the X basis"
              + ("" if nboth == len(top) else f" (the others: X {', '.join(str(a) if a == b else f'{a}–{b}' for a, b in xs if (a, b) != (k, k))})"))
    lines.append(s)
if lines:
    out += ["**Walking Cat, every numbering of the terms** (the paper's Table 10 refers to terms A_i, B_i without "
            "printing which monomial is which): " + ". ".join(lines) + ".", ""]

# ------------------------------------------------------------------ code distances of the weight-11 routing codes
cd = []
for key, name in (("200_24", "[[200,24,14]]"), ("200_16", "[[200,16,17]]")):
    p = f"{R}/routing/code_distance_{key}.json"
    if os.path.exists(p):
        r = json.load(open(p))
        v = r["distance"]
        cd.append(f"{name}: rebuilt [[{r['n']},{r['k']}]], code distance " +
                  ", ".join(f"{b} {'**' + str(x['d']) + '**' if x['d'] is not None else '≥ ' + str(x['lower_bound'])}"
                            for b, x in v.items()))
if cd:
    out += ["Code distances of the rebuilt weight-11 routing codes (exact search): " + "; ".join(cd) + ".", ""]

# ------------------------------------------------------------------ estimated code distances
p = f"{R}/estdist/server.json"
if os.path.exists(p):
    codes = {c["name"]: c for c in json.load(open(p))["codes"]}
    for f in glob.glob(f"{R}/estdist/server_*.json"):          # the open cases, run separately with longer limits
        for c in json.load(open(f))["codes"]:
            old = codes.get(c["name"])
            if old is None or (c.get("d") is not None and old.get("d") is None) or \
                    (c.get("lower_bound") or 0) > (old.get("lower_bound") or 0):
                codes[c["name"]] = c
    PAPER = {"2601.18879": "multivariate multicycle codes", "2609.06572": "weight-8 bivariate bicycle codes",
             "2603.05398": "clustered lifted-product codes (QGPU)", "2607.27644": "balanced-product codes, design rate 1/5",
             "2606.02418": "LLM-guided bivariate bicycle search"}
    out += ["**Code distances that the papers give as estimates or bounds** (`papers/estimated_codes.py`: "
            f"{len(codes)} codes rebuilt from the papers' tables; exact search = all smaller weights exhausted and a "
            "logical operator of that weight found, for both error types).", "",
            "| paper | codes rebuilt | exact here | equal to the paper's value | different | open |", "|---|---:|---:|---:|---:|---:|"]
    for ax, name in PAPER.items():
        cs = [c for c in codes.values() if c["arxiv"] == ax]
        ex = [c for c in cs if c.get("d") is not None]
        eq = [c for c in ex if c["d"] == c["d_claimed"]]
        out.append(f"| {name}, {ax} | {len(cs)} | {len(ex)} | {len(eq)} | {len(ex) - len(eq)} | {len(cs) - len(ex)} |")
    out.append("")
    KIND = {"randomized_estimate": "estimate", "upper_bound": "upper bound", "lower_bound": "lower bound", "exact": "stated exact"}
    TARGETS = ["mm_t4_r5_216_12_14", "mm_t3_r5_288_12_16", "mm_t3_r6_324_12_20", "mm_t10_r1_630_70_9", "w8bb_144_6_ge15",
               "w8bb_144_10_ge11", "qgpu_136_8_14", "qgpu_198_18_10", "balanced_390_78_16", "balanced_525_105_18",
               "balanced_550_110_18", "balanced_625_125_20", "llmbb_360_12_24_V"]
    out += ["| code | paper's statement | this work | seconds |", "|---|---|---|---:|"]
    for t in TARGETS:
        c = codes.get(t)
        if c is None:
            continue
        claim = f"{'≥ ' if c['claim_kind'] == 'lower_bound' else '≤ ' if c['claim_kind'] == 'upper_bound' else ''}{c['d_claimed']} ({KIND.get(c['claim_kind'], c['claim_kind'])})"
        if not c.get("parameters_match_paper", True):
            mine = f"the printed definition gives [[{c['n']},{c['k']}]], not [[{c['paper_n']},{c['paper_k']}]]"
        elif c.get("d") is not None:
            mine = f"**{c['d']}**"
        else:
            mine = f"{c.get('lower_bound')} – {c.get('upper_bound') or '?'}"
        out.append(f"| {PAPER[c['arxiv']].split(',')[0].split(' (')[0]} [[{c['paper_n']},{c['paper_k']}]] | {claim} | {mine} | "
                   f"{c.get('seconds', 0):.0f} |")
    out.append("")
    diff = [c for c in codes.values() if c.get("d") is not None and c["d"] != c["d_claimed"] and c["name"] not in TARGETS]
    if diff:
        out += ["Other rows where the exact value differs from the printed one (code, printed → exact): " +
                ", ".join(f"[[{c['n']},{c['k']}]] {c['d_claimed']} → {c['d']}" for c in sorted(diff, key=lambda c: (c['n'], c['k']))) +
                ". See the caution in the text.", ""]

# ------------------------------------------------------------------ designed here: weight-8 BB codes of 2609.06572
D2 = "results/papers2/design"
fam = sorted(glob.glob(f"{D2}/bb8_*_parallel_family.json"))
fun = sorted(glob.glob(f"{D2}/bb8_*_parallel_funnel*.json"))
if fam or fun:
    out += ["**Mirror depth-8 circuits designed here for the weight-8 bivariate bicycle codes of 2609.06572** "
            "(`papers/bb8_parallel.py`; the paper gives no circuit). For the first two codes the exact circuit distance of all "
            "3456 mirror orders was computed; for the larger ones a few orders with the best collapsed bound were "
            "evaluated exactly (`papers/design_parallel_pick.py`), which gives a circuit and its distance but not the "
            "optimum of the family.", "",
            "| code | orders | result | example order of the X checks (L_a = A_a on the left block, R_a = B_a on the right block) |",
            "|---|---|---|---|"]
    for f in fam:
        r = json.load(open(f))
        n, k, d = r["code"]
        h = r["circuit_distance_histogram"]
        best = r["best_circuit_distance"]
        bb = r.get("best_orders_both_bases") or []
        okb = bool(bb) and all(list(x["Z"]) == list(x["X"]) == [best, best] for x in bb)
        out.append(f"| [[{n},{k},{d}]] | all 3456, exact: " + ", ".join(f"{v} at {kk}" for kk, v in sorted(h.items(), key=lambda x: int(x[0]))) +
                   (f"; {r['n_not_exact']} open" if r.get("n_not_exact") else "") +
                   f" | best **{best}**" + (" in both bases" if okb else " (Z basis)") + f" ({h[str(best)]} orders) | "
                   f"{' '.join(r['best_orders'][0])} |")
    for f in fun:
        r = json.load(open(f))
        if not r.get("evaluated"):
            continue
        n, k, d = r["code"]
        ev = r.get("evaluated", [])
        def rng(v):
            return f"{v[0]}" if v[0] == v[1] else f"{v[0]}–{v[1] if v[1] is not None else '?'}"
        if ev:
            key = lambda e: min((e[b][0] if isinstance(e.get(b, [None])[0], int) else 0) for b in "ZX" if b in e)
            e = max(ev, key=key)
            res = "best evaluated: Z " + rng(e["Z"]) + (", X " + rng(e["X"]) if "X" in e else "") + f" ({len(ev)} orders evaluated exactly)"
            order = " ".join(e["order"])
        else:
            res, order = "evaluation running", "–"
        wh = r["window_distance_histogram_of_rejected"]
        top = max(map(int, wh)) if wh else None
        out.append(f"| [[{n},{k},{d}]] | window filter with target {r['target']}: {len(r['survivors'])} orders pass, "
                   f"{len(r['stage1_timeouts'])} undecided" + (f", the others have window distance at most {top}" if top else "") +
                   f" | {res} | {order} |")
    for f in sorted(glob.glob(f"{D2}/bb8_*_parallel_pick.json")):
        r = json.load(open(f))
        n, k, d = r["code"]
        ev = [e for e in r.get("evaluated", []) if "Z" in e and "X" in e]
        if not ev:
            continue
        def rng(v):
            return f"{v[0]}" if v[0] == v[1] else f"{v[0]}–{v[1] if v[1] is not None else '?'}"
        e = max(ev, key=lambda e: (min(e["Z"][0] or 0, e["X"][0] or 0), -max(e["Z"][1] or 99, e["X"][1] or 99)))
        lo = min(e["Z"][0], e["X"][0])
        exact = e["Z"][0] == e["Z"][1] and e["X"][0] == e["X"][1]
        h = r["collapsed_bound_histogram"]
        out.append(f"| [[{n},{k},{d}]] | {len(ev)} orders with the best collapsed bound ({max(map(int, h))}) evaluated exactly | "
                   f"best found {'**' + str(lo) + '**' if exact else 'Z ' + rng(e['Z']) + ', X ' + rng(e['X'])}"
                   f"{' in both bases' if exact else ''} (not the optimum of the family) | {' '.join(e['order'])} |")
    out.append("")

# ------------------------------------------------------------------ all depth-7 schedules of the weight-6 BB codes
B6 = f"{R}/bb6"
if glob.glob(f"{B6}/*_ibm.json"):
    def sched_name(px, pz):
        labx = ["A1", "A2", "A3", "B1", "B2", "B3"]
        labz = ["B1", "B2", "B3", "A1", "A2", "A3"]
        x, z = ["–"] * 7, ["–"] * 7
        for lab, t in zip(labx, px):
            x[t] = lab
        for lab, t in zip(labz, pz):
            z[t] = lab
        return "X: " + " ".join(x) + "; Z: " + " ".join(z)
    out += ["**Every valid depth-7 schedule of the weight-6 bivariate bicycle codes** (`papers/bb6_depth7.py`, "
            "`papers/design_bb6_depth7.py`; designed here). One ancilla per check, seven CNOT layers; a schedule is valid iff "
            "X and Z checks never act on the same block in a layer and every overlapping pair of checks is crossed "
            "consistently. There are 8496 valid schedules, 936 of them in the standard family (X checks idle in the first "
            "layer, Z checks idle in the last). Exact circuit distance of every schedule, both bases, six cycles; the "
            "number is the smaller of the two bases. In the Z rows of a schedule, A_i and B_j stand for the transposed terms.", "",
            "| code | family | standard schedule (2308.07915) | schedules by exact circuit distance | best | a best schedule |",
            "|---|---|---:|---|---:|---|"]
    for key, name in (("bb72", "[[72,12,6]]"), ("bb90", "[[90,8,10]]"), ("bb108", "[[108,8,10]]"), ("gross", "[[144,12,12]]")):
        for famn, label in (("ibm", "standard, 936"), ("all", "all, 8496")):
            q = f"{B6}/{key}_{famn}.json"
            if not os.path.exists(q):
                continue
            r = json.load(open(q))
            h = r["circuit_distance_histogram"]
            best = max(map(int, h))
            rows_ = [x for x in r["rows"] if "error" not in x and x["Z"][0] == x["Z"][1] and x["X"][0] == x["X"][1]
                     and min(x["Z"][0], x["X"][0]) == best]
            std = r.get("standard_schedule")
            sv = min(std["Z"][0], std["X"][0]) if std else "–"
            out.append(f"| {name} | {label} | {sv} | " + ", ".join(f"{v} at {k}" for k, v in sorted(h.items(), key=lambda t: int(t[0]))) +
                       (f"; {r['not_exact']} not exact" if r.get("not_exact") else "") +
                       f" | **{best}** | {sched_name(rows_[0]['px'], rows_[0]['pz'])} |")
    out.append("")
    cc = []
    for key, name in (("bb108", "[[108,8,10]]"), ("gross", "[[144,12,12]]")):
        q = f"{B6}/{key}_ibm_crosscheck.json"
        if os.path.exists(q):
            r = json.load(open(q))
            b_ = r.get("best", {})
            vals = {k: v[:2] for k, v in b_.items() if k.startswith("run_")}
            if vals:
                same = all(v == [r["family_value"], r["family_value"]] for v in vals.values())
                cc.append(f"{name}: " + ("all " + str(len(vals)) + " re-runs give " + str(r["family_value"]) if same else str(vals)))
    q = f"{R}/shift/gross11_check.json"
    if cc:
        out += ["Cross-checks of a best schedule (six and twelve cycles in both bases; the original pipeline `run_bb.py` "
                "without symmetry in both bases): " + "; ".join(cc) + ".", ""]

text = "\n".join(out)
print(text)
if os.path.exists("docs/PAPERS.md"):
    t = open("docs/PAPERS.md").read()
    a, b = "<!-- RESULTS3:BEGIN -->", "<!-- RESULTS3:END -->"
    if a in t and b in t:
        t = t[:t.index(a) + len(a)] + "\n" + text + "\n" + t[t.index(b):]
        open("docs/PAPERS.md", "w").write(t)
