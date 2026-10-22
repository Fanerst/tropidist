"""Tables of results/planar_dp/README.md, filled between the markers <!-- TABLE:<name> --> and <!-- /TABLE:<name> -->.

Inputs (all under results/planar_dp/):
  widths_<family>.json         instances, the paper's distances, and the DP width / table of both bases
  code_dp1/, code_dp0/         pipeline records (bench/adapters/ours_pipeline.py) with and without the DP front end
  widths_circuits.json, fold/  vine-code memory circuits: collapsed and fold-2 widths, fold-2 lower bound + window
  circ_dp1/, circ_dp0/         pipeline records on the circuits (sector variant)
  isd/                         upper bounds from bench/adapters/isd.py where no run is exact

usage: python scripts/summarize_planar_dp.py
"""
from __future__ import annotations

import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results", "planar_dp")
FAMILIES = [("vine", "Vine codes, arXiv:2606.20263 (codes read off the authors' Stim circuits)"),
            ("tile", "Tile codes, arXiv:2504.09171 and 2607.05897"),
            ("nngrid", "Nearest-neighbour planar-grid codes, arXiv:2606.19482 (v2)"),
            ("bbsurface", "Bivariate-bicycle surface codes with boundaries, arXiv:2606.08771"),
            ("barbell", "Barbell codes, arXiv:2606.06062"),
            ("spacegroup", "Space-group codes, arXiv:2606.20548 (v3)")]


def records(kind, name):
    out = []
    for path in glob.glob(os.path.join(OUT, kind, "%s__t*.json" % name)):
        r = json.load(open(path))
        try:
            r["_notes"] = json.loads(r["notes"]) if r.get("notes") else {}
        except ValueError:          # adapters other than ours_pipeline write plain-text notes
            r["_notes"] = {}
        out.append(r)
    return out


def interval(recs):
    lo = max((r["lower_bound"] or 0) for r in recs)
    ups = [r["upper_bound"] for r in recs if r["upper_bound"] is not None]
    hi = min(ups) if ups else None
    return lo, hi


def fmt_value(lo, hi):
    if hi is not None and lo == hi:
        return "%d" % lo
    return "[%d, %s]" % (lo, "?" if hi is None else hi)


def basis_cell(name, basis):
    """(value text, front-end text, search-only text, dp_solved, search_solved, lo, hi)"""
    key = "%s_%s" % (name, basis)
    r1, r0 = records("code_dp1", key), records("code_dp0", key)
    allr = r1 + r0
    if not allr:
        return "-", "-", "-", False, False, None, None
    lo, hi = interval(allr)
    if hi is None or hi > lo:
        # upper bounds from our randomised information-set search (bench/adapters/isd.py), records in isd/
        isd = [r for r in records("isd", key) if r.get("upper_bound") is not None and r.get("witness_ok")]
        if isd:
            u = min(r["upper_bound"] for r in isd)
            hi = u if hi is None else min(hi, u)
    dp_solved = any(r["status"] == "exact" and str(r["_notes"].get("dp", {}).get("main", {}).get("decision", ""))
                    .startswith("dp") for r in r1)
    s_exact = [r for r in r0 if r["status"] == "exact"]
    search_solved = bool(s_exact)
    def best(recs):
        ex = [r for r in recs if r["status"] == "exact"]
        if ex:
            r = min(ex, key=lambda r: r["seconds"])
            tag = ""
            if r in r1:
                dec = str(r["_notes"].get("dp", {}).get("main", {}).get("decision", ""))
                tag = " DP" if dec.startswith("dp") else ""
            return "%.1f%s" % (r["seconds"], tag)
        if recs:
            r = max(recs, key=lambda r: r["seconds"])
            return ">%d (%s)" % (r["time_limit"], fmt_value(r["lower_bound"] or 0, r["upper_bound"]))
        return "-"
    fe = best(r1) if r1 else "= search"
    return fmt_value(lo, hi), fe, best(r0), dp_solved, search_solved, lo, hi


def paper_text(rec):
    kind = rec.get("d_kind") or "unknown"
    dx, dz, d = rec.get("dx"), rec.get("dz"), rec.get("d")
    if "d_X is printed as an upper bound" in (rec.get("d_method") or ""):
        return "dx <= %s (upper, QDistRnd), dz %s (exact, IP)" % (dx, dz)
    if dx is not None and dz is not None and dx != dz:
        s = "dx %s, dz %s" % (dx, dz)
    elif d is not None:
        s = "%s" % d
    else:
        s = "-"
    return "%s (%s)" % (s, kind)


def fits_text(bits):
    m = max(bits)
    return "yes" if m <= 33 else ("64 GiB" if m <= 36 else "no")


def family_table(fam):
    path = os.path.join(OUT, "widths_%s.json" % fam)
    if not os.path.exists(path):
        return "(not built)\n", []
    W = json.load(open(path))
    lines = ["| instance | n | k | paper: d (status) | width d_X / d_Z | fits | d_X found | d_Z found | "
             "front end s (X / Z) | search only s (X / Z) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    notes = []
    for name, rec in W.items():
        bz, bx = rec["bases"]["Z"], rec["bases"]["X"]
        vz = basis_cell(name, "Z")
        vx = basis_cell(name, "X")
        lines.append("| %s | %d | %d | %s | %d / %d | %s | %s | %s | %s / %s | %s / %s |" % (
            name, rec["n"], rec["k"], paper_text(rec), bz["width"], bx["width"],
            fits_text([bz["table_bits"], bx["table_bits"]]), vz[0], vx[0], vz[1], vx[1], vz[2], vx[2]))
        notes.append(dict(name=name, rec=rec, Z=vz, X=vx, wz=bz["width"], wx=bx["width"],
                          tz=bz["table_bits"], tx=bx["table_bits"]))
    return "\n".join(lines) + "\n", notes


def bbsurface_table():
    """One line per candidate region size of every row of the BB-surface codes (the paper gives no sizes)."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "papers"))
    import planar_bbsurface
    W = {}
    for fam in ("bbsurface", "bbsurface_alt0", "bbsurface_alt1", "bbsurface_alt2"):
        path = os.path.join(OUT, "widths_%s.json" % fam)
        if os.path.exists(path):
            W.update(json.load(open(path)))
    rows = {}
    for inst in planar_bbsurface.instances(alternates=True):
        base = re.sub(r"_L\d+x\d+$", "", inst["name"])
        rows.setdefault(base, []).append(inst)
    lines = ["| row | paper: d (status) | size L1 x L2 | n | k | width d_X / d_Z | fits | d_X found | d_Z found | "
             "d = min | equals paper | front end s (X / Z) | search only s (X / Z) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    summary = {"rows": 0, "rows_match": 0, "rows_all_lower": 0, "sizes": 0, "open": 0}
    for base, insts in rows.items():
        summary["rows"] += 1
        match = False
        lower = True
        for inst in sorted(insts, key=lambda i: (not i.get("primary", True), i.get("L1") or 0)):
            name = inst["name"]
            rec = W.get(name)
            if rec is None:
                continue
            summary["sizes"] += 1
            bz, bx = rec["bases"]["Z"], rec["bases"]["X"]
            vz, vx = basis_cell(name, "Z"), basis_cell(name, "X")
            exact = vz[6] is not None and vz[5] == vz[6] and vx[6] is not None and vx[5] == vx[6]
            dmin = min(vz[5], vx[5]) if exact else None
            eq = "-" if dmin is None or rec.get("d") is None else ("yes" if dmin == rec["d"] else
                                                                ("lower" if dmin < rec["d"] else "higher"))
            if dmin is None:
                summary["open"] += 1
            if eq == "yes":
                match = True
            if eq != "lower":
                lower = False
            lines.append("| %s | %s | %s x %s%s | %d | %d | %d / %d | %s | %s | %s | %s | %s | %s / %s | %s / %s |" % (
                base, paper_text(rec), inst.get("L1"), inst.get("L2"), " (default)" if inst.get("primary", True) else "",
                rec["n"], rec["k"], bz["width"], bx["width"], fits_text([bz["table_bits"], bx["table_bits"]]),
                vz[0], vx[0], "-" if dmin is None else dmin, eq, vz[1], vx[1], vz[2], vx[2]))
        summary["rows_match"] += match
        summary["rows_all_lower"] += lower
    return "\n".join(lines) + "\n", summary


def circuit_table():
    W = json.load(open(os.path.join(OUT, "widths_circuits.json")))
    lines = ["| circuit | rounds | paper d_circ | collapsed: rows x cols, width | fold-2: rows x cols, width | "
             "collapsed d | fold-2 d (lower) | window (upper) | d_circ found | fold + window s | pipeline s (dp=1 / dp=0) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in sorted(glob.glob(os.path.join(OUT, "fold", "*__fold2.json"))):
        r = json.load(open(f))
        name = r["instance"]
        wc = W.get("%s:collapsed" % name, {})
        wf = W.get("%s:fold2" % name, {})
        p1 = records("circ_dp1", name)
        p0 = records("circ_dp0", name)
        coll = None
        cdp = os.path.join(OUT, "collapsed_dp", "%s__collapsed.json" % name)
        if os.path.exists(cdp):
            coll = json.load(open(cdp)).get("value")
        for rr in ([] if coll is not None else p1 + p0):
            st = rr["_notes"].get("stages", {}).get("collapsed", {})
            runs = st.get("runs", [])
            if runs and runs[-1].get("best") is not None:
                coll = runs[-1]["best"]
        def ptime(recs):
            if not recs:
                return "-"
            rr = min(recs, key=lambda x: x["seconds"])
            return "%.0f" % rr["seconds"] if rr["status"] == "exact" else ">%d" % rr["time_limit"]
        paper = (r.get("paper") or {}).get("d_circuit")
        status = (r.get("paper") or {}).get("status")
        lines.append("| %s | %s | %s (%s) | %s x %s, %s | %s x %s, %s | %s | %s | %s | %s | %s | %s / %s |" % (
            name, r.get("rounds"), paper, status, wc.get("rows", "-"), wc.get("cols", "-"), wc.get("width", "-"),
            r["fold"]["rows"], r["fold"]["cols"], wf.get("width", "-"), coll if coll is not None else "-",
            r["fold"]["lower_bound"], r["window"]["distance"],
            r["lower"] if r["exact"] else "[%d, %s]" % (r["lower"], r["upper"]),
            "%.1f (%d thr)" % (r["seconds"], r.get("threads") or 1), ptime(p1), ptime(p0)))
    return "\n".join(lines) + "\n"


def fill(text, name, body):
    pat = re.compile(r"(<!-- TABLE:%s -->\n)(.*?)(<!-- /TABLE:%s -->)" % (name, name), re.S)
    if not pat.search(text):
        raise KeyError("no marker for table %s" % name)
    return pat.sub(lambda m: m.group(1) + body + m.group(3), text)


def main():
    path = os.path.join(OUT, "README.md")
    text = open(path).read()
    for fam, _ in FAMILIES:
        if fam == "bbsurface":
            body, summ = bbsurface_table()
            print("bbsurface:", summ)
        else:
            body, _ = family_table(fam)
        text = fill(text, fam, body)
    text = fill(text, "circuits", circuit_table())
    open(path, "w").write(text)
    print("filled", path)


if __name__ == "__main__":
    main()
