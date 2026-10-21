"""Table of the distance check of arXiv:2608.02773 (Cornucopia codes), from the records in results/cornucopia and
results/papers2.

  code distance: scripts/cornucopia_code_distance.py, both CSS sectors
  one cycle, CNOT faults only (the setting of the authors' circuit-distance search):
      exact values from papers/run_parallel.py (circ_q*_r1_*_cx.json); otherwise an interval whose lower bound is
      the time-collapsed bound of the N_c-cycle run (the collapsed columns of one cycle are a subset of those of N_c
      cycles) and whose upper bound is the best verified fault set: a window minimum of the one-cycle circuit
      (win_q*_r1_Z_t1.json) or an N_c-cycle fault set replayed in one cycle (transfer.json)
  N_c cycles, the paper's fault model (its memory experiments): papers/run_parallel.py (lower bound, and upper
      bound from lifting or the one-round window) and scripts/window_search.py (win_q*_r*_Z_t1.json)

usage: python scripts/summarize_cornucopia_check.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "papers"))
import cornucopia

NC = {7: 6, 16: 6, 25: 6, 29: 6, 49: 7, 64: 8, 79: 8}      # cycles of the paper's memory simulations
R = ROOT / "results"


def load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


def fmt(lb, ub):
    if lb is not None and ub is not None and lb == ub:
        return f"**{lb}**"
    if ub is None:
        return f"≥ {lb}" if lb else "–"
    return f"{lb}–{ub}" if lb else f"≤ {ub}"


def collapsed_lb(rec):
    """Certified lower bound of the time-collapsed relaxation alone (valid for any number of cycles >= 1)."""
    c = (rec or {}).get("collapsed") or {}
    if c.get("distance"):
        return c["distance"]
    done = [r["K"] for r in c.get("runs", []) if r["status"] == "exhausted" and r.get("best") is None]
    return max(done) + 1 if done else None


def code_distances():
    out = {}
    for f in sorted(R.glob("cornucopia/code_distance*.json")):
        d = load(f)
        for c in (d or {}).get("codes", []):
            out.setdefault((c["q"], c["distance_name"]), c["distance"])
    return out


def main():
    cd = code_distances()
    transfer = load(R / "cornucopia/transfer.json") or {}
    print("| code | paper: d | d_X, d_Z | paper: d_circ | one cycle, CNOT faults | N_c cycles, paper's faults |")
    print("|---|---:|---|---:|---|---|")
    for q, row in cornucopia.CODES.items():
        n, k, d = row[2]
        name = f"[[{n},{k},{d}]]"
        nc = NC[q]
        exact1 = [load(R / f"cornucopia/circ_q{q}_r1_{b}_cx.json") for b in "ZX"]
        if all(r and r.get("certified_lower_bound") == r.get("certified_upper_bound") for r in exact1):
            one = "; ".join(fmt(r["certified_lower_bound"], r["certified_upper_bound"]) for r in exact1) + " (Z; X)"
        else:
            recN = load(R / f"cornucopia/circ_q{q}_r{nc}_Z.json")
            ubs = []
            w = load(R / f"cornucopia/win_q{q}_r1_Z_t1.json")
            if w and w.get("certified_upper_bound"):
                ubs.append(w["certified_upper_bound"])
            t = transfer.get(name)
            if t and t.get("undetected_logical_in_one_cycle"):
                ubs.append(t["weight"])
            one = fmt(collapsed_lb(recN), min(ubs) if ubs else None) + " (Z)"
        many = []
        for b in "ZX":
            r = load(R / f"cornucopia/circ_q{q}_r{nc}_{b}.json") or load(R / f"papers2/cornucopia_q{q}_r{nc}_{b}.json")
            if r is None:
                continue
            lb, ub = r.get("certified_lower_bound"), r.get("certified_upper_bound")
            w = load(R / f"cornucopia/win_q{q}_r{nc}_{b}_t1.json")
            if w and w.get("certified_upper_bound"):
                ub = min(ub or 99, w["certified_upper_bound"])
            many.append(f"{fmt(lb, ub)} ({b})")
        print(f"| {name} | {d} | {cd.get((q, 'd_X'), '–')}, {cd.get((q, 'd_Z'), '–')} | ≤ {row[3]} | {one} "
              f"| {nc} cycles: {'; '.join(many) if many else '–'} |")


if __name__ == "__main__":
    main()
