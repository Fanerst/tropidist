"""Dense Rank DP on the planar, 2D-local codes of 2026 (builders papers/planar_<family>.py).

  widths <family> [name ...]      cut rank of the best column order found for both memory bases of every
                                  instance: natural order, geometric sweeps of the lattice (36 directions and the
                                  patch vectors), greedy orders (up to 2000 columns), and a local search on the
                                  best; the DP plan's largest table and work for that order.
                                  -> results/planar_dp/widths_<family>.json
  circuit-widths <variant> <dir>...  the same for the time-collapsed problem (variant "collapsed") or the
                                  period-P time fold of the sector problem ("foldP", cdist.problem.fold_time) of
                                  exported circuit instances (papers/planar_vine.py export_circuits)
                                  -> results/planar_dp/widths_circuits.json
  circuit-dp collapsed <dir>...   the exact distance of the time-collapsed problem by the dense DP on that best
                                  order (a lower bound on the circuit distance) -> results/planar_dp/collapsed_dp/
  export <family> [name ...]      the code-capacity problems as benchmark instances (bench/common.export_code_instance)
                                  with the qubits renumbered in the best order found, so that the pipeline's DP
                                  front end (bench/adapters/ours_pipeline.py --config dp=1) starts from it.
                                  -> results/planar_dp/instances/<name>_<basis>/

Bases follow stabcode.css_distance_problem: "Z" is the X-error problem (distance d_X), "X" the Z-error problem
(distance d_Z).

usage: python scripts/planar_dp.py widths|export <family> [name ...] [--seeds 2] [--improve 3000]
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "papers"), os.path.join(ROOT, "bench")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import stabcode  # noqa: E402
from cdist import auto, ordering, trellis  # noqa: E402

OUT = os.path.join(ROOT, "results", "planar_dp")
GREEDY_MAX = 2000
GIB = 1 << 30


def load_family(family):
    """Instances of papers/planar_<family>.py.  "bbsurface_alt<i>" is chunk i of 3 of the other region sizes of the
    BB surface codes with the paper's n and k (planar_bbsurface.instances(alternates=True) minus the defaults)."""
    import planar_common
    if family.startswith("bbsurface_alt"):
        mod = importlib.import_module("planar_bbsurface")
        default = {i["name"] for i in mod.instances()}
        alts = [i for i in mod.instances(alternates=True) if i["name"] not in default]
        part = int(family[len("bbsurface_alt"):])
        return [planar_common.check(i) for j, i in enumerate(alts) if j % 3 == part]
    mod = importlib.import_module("planar_" + family)
    return [planar_common.check(i) if "n" not in i else i for i in mod.instances()]


def column_xy(p, xy):
    """Position of each column: the mean position of the qubits merged into it."""
    out = []
    for metas in p.col_meta:
        pts = [xy[q] for (_, q) in metas]
        out.append((sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts)))
    return out


def sweep_orders(cxy, vectors=()):
    """Columns sorted by their projection on a direction (ties by the perpendicular coordinate)."""
    dirs = [(math.cos(math.pi * a / 36), math.sin(math.pi * a / 36)) for a in range(36)]
    for v in vectors:
        if v and (v[0] or v[1]):
            r = math.hypot(*v)
            dirs.append((v[0] / r, v[1] / r))
            dirs.append((-v[1] / r, v[0] / r))
    for (c, s) in dirs:
        key = [(round(c * x + s * y, 6), round(-s * x + c * y, 6), j) for j, (x, y) in enumerate(cxy)]
        yield "sweep(%.3f,%.3f)" % (c, s), [j for _, _, j in sorted(key)]


def cost(p, order):
    return ordering.profile_cost(trellis.cut_profile(p.h, order))


def plan_cost(p, order):
    """Largest table (bits, with the +1 margin of cdist.auto.estimate) and work of all logical queries."""
    for _, plan in auto._plans(p, order):
        if plan.feasible:
            return plan.peak_bits + 1, plan.work() * p.nobs
    return 0, 0


def best_orders(p, cxy, vectors, seeds=2, improve_iters=3000, log=print):
    t0 = time.time()
    found = {}
    nat = list(range(p.ncols))
    found["natural"] = (cost(p, nat), nat)
    best_sweep = None
    for label, o in sweep_orders(cxy, vectors):
        c = cost(p, o)
        if best_sweep is None or c < best_sweep[0]:
            best_sweep = (c, o, label)
    found["sweep"] = (best_sweep[0], best_sweep[1])
    found["sweep_label"] = best_sweep[2]
    if p.ncols <= GREEDY_MAX:
        bestg = None
        for s in range(seeds):
            o = ordering.greedy_order(p.h, p.nrows, seed=s, noise=0.5 if s else 0.0)
            c = cost(p, o)
            if bestg is None or c < bestg[0]:
                bestg = (c, o)
        found["greedy"] = bestg
    cands = [(v[0], k) for k, v in found.items() if k != "sweep_label"]
    start_key = min(cands)[1]
    start = found[start_key][1]
    if improve_iters:
        o, c = ordering.improve(p.h, start, iters=improve_iters, seed=1, max_block=24)
        found["improved"] = (c, o)
    best_key = min((v[0], k) for k, v in found.items() if k != "sweep_label")[1]
    found["best_key"] = best_key
    found["seconds"] = time.time() - t0
    return found


def widths(family, names=None, seeds=2, improve_iters=3000):
    insts = load_family(family)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "widths_%s.json" % family)
    records = json.load(open(path)) if os.path.exists(path) else {}
    for inst in insts:
        if names and inst["name"] not in names:
            continue
        rec = {k: inst.get(k) for k in ("name", "family", "arxiv", "locator", "n", "k", "n_paper", "k_paper", "dx",
                                        "dz", "d", "d_kind", "d_method", "notes")}
        rec["bases"] = {}
        for basis in ("Z", "X"):
            p = stabcode.css_distance_problem(inst["hx"], inst["hz"], inst["n"], basis, name=inst["name"])
            cxy = column_xy(p, inst["xy"])
            vectors = [v for v in (inst.get("v1"), inst.get("v2")) if v]
            f = best_orders(p, cxy, vectors, seeds=seeds, improve_iters=improve_iters)
            order = f[f["best_key"]][1]
            peak, work = plan_cost(p, order)
            b = dict(rows=p.nrows, cols=p.ncols, obs=p.nobs,
                     cut_rank={k: int(v[0][0]) for k, v in f.items() if isinstance(v, tuple)},
                     best=f["best_key"], sweep_label=f["sweep_label"], width=int(f[f["best_key"]][0][0]),
                     log2_volume=round(f[f["best_key"]][0][1], 2), table_bits=peak, work=work,
                     predicted_seconds_1t=round(auto.predicted_seconds(work, 1), 2),
                     predicted_seconds_32t=round(auto.predicted_seconds(work, 32), 2),
                     fits_8GiB=peak <= 33, fits_64GiB=peak <= 36, order_seconds=round(f["seconds"], 1),
                     order=order, distance_name="dx" if basis == "Z" else "dz")
            rec["bases"][basis] = b
            print("%-28s basis %s cols %5d  width %2d (%s; natural %d, sweep %d%s)  table 2^%d B  work %.2e  "
                  "pred %.1f s/1t  %.1f s/32t" % (inst["name"], basis, p.ncols, b["width"], b["best"],
                                                   b["cut_rank"]["natural"], b["cut_rank"]["sweep"],
                                                   (", greedy %d" % b["cut_rank"]["greedy"]) if "greedy" in
                                                   b["cut_rank"] else "", peak, work, b["predicted_seconds_1t"],
                                                   b["predicted_seconds_32t"]), flush=True)
        records[inst["name"]] = rec
        json.dump(records, open(path, "w"), indent=1)
    return records


def export(family, names=None):
    import common
    insts = {i["name"]: i for i in load_family(family)}
    rec = json.load(open(os.path.join(OUT, "widths_%s.json" % family)))
    root = os.path.join(OUT, "instances")
    out = []
    for name, inst in insts.items():
        if names and name not in names:
            continue
        for basis in ("Z", "X"):
            b = rec[name]["bases"][basis]
            p = stabcode.css_distance_problem(inst["hx"], inst["hz"], inst["n"], basis, name=name)
            # qubit order: the columns of the best order, each followed by the qubits merged into it
            qorder = [q for j in b["order"] for (_, q) in p.col_meta[j]]
            assert sorted(qorder) == list(range(inst["n"]))
            new = {q: i for i, q in enumerate(qorder)}

            def relabel(rows):
                return [sum(1 << new[q] for q in stabcode.bits(r)) for r in rows]
            dkey = "dx" if basis == "Z" else "dz"
            truth = {}
            if inst.get(dkey) is not None and inst.get("d_kind") == "exact":
                truth = {"full": (inst[dkey], "exact", "%s %s" % (inst["arxiv"], inst.get("locator")))}
            meta = dict(family=inst["family"], description="%s, %s distance (%s)" % (name, dkey, inst.get("locator")),
                        k=inst["k"], source="scripts/planar_dp.py from papers/planar_%s.py" % family,
                        paper={"arxiv": inst["arxiv"], dkey: inst.get(dkey), "d_kind": inst.get("d_kind")},
                        qubit_order="best order of results/planar_dp/widths_%s.json (%s)" % (family, b["best"]),
                        truth=truth)
            iname = "%s_%s" % (name, basis)
            common.export_code_instance(iname, relabel(inst["hx"]), relabel(inst["hz"]), inst["n"], basis, None, meta,
                                        root=root)
            out.append(iname)
            print("exported", iname)
    return out


def circuit_widths(dirs, variant="collapsed", seeds=2, improve_iters=3000):
    """Widths of the time-collapsed (or other) problem of exported circuit instances; columns are placed at the
    mean position of their checks (meta check_xy).  -> results/planar_dp/widths_circuits.json"""
    import common
    path = os.path.join(OUT, "widths_circuits.json")
    records = json.load(open(path)) if os.path.exists(path) else {}
    from cdist import problem
    for d in dirs:
        if variant.startswith("fold"):
            prob = common.load(d, "sector")
            p = problem.fold_time(common.to_cdist(prob), int(variant[4:]))
        else:
            prob = common.load(d, variant)
            p = common.to_cdist(prob)
        meta = prob.meta
        rxy = [meta["check_xy"][int(m[0])] for m in p.row_meta]  # position of the check of every row
        cxy = []
        for a in p.h:
            rows = stabcode.bits(a)
            if not rows:
                cxy.append((0.0, 0.0))
                continue
            cxy.append((sum(rxy[r][0] for r in rows) / len(rows), sum(rxy[r][1] for r in rows) / len(rows)))
        f = best_orders(p, cxy, [], seeds=seeds, improve_iters=improve_iters)
        order = f[f["best_key"]][1]
        peak, work = plan_cost(p, order)
        b = dict(variant=variant, rows=p.nrows, cols=p.ncols, obs=p.nobs,
                 cut_rank={k: int(v[0][0]) for k, v in f.items() if isinstance(v, tuple)},
                 best=f["best_key"], sweep_label=f["sweep_label"], width=int(f[f["best_key"]][0][0]),
                 table_bits=peak, work=work, predicted_seconds_1t=round(auto.predicted_seconds(work, 1), 2),
                 predicted_seconds_32t=round(auto.predicted_seconds(work, 32), 2), fits_8GiB=peak <= 33,
                 fits_64GiB=peak <= 36, order_seconds=round(f["seconds"], 1), order=order,
                 paper=meta.get("paper"))
        records["%s:%s" % (meta["name"], variant)] = b
        json.dump(records, open(path, "w"), indent=1)
        print("%-34s %-9s %4dx%5d width %2d (%s; natural %d, sweep %d%s)  table 2^%d B  work %.2e  pred %.1f s/1t"
              % (meta["name"], variant, p.nrows, p.ncols, b["width"], b["best"], b["cut_rank"]["natural"],
                 b["cut_rank"]["sweep"], (", greedy %d" % b["cut_rank"]["greedy"]) if "greedy" in b["cut_rank"]
                 else "", peak, work, b["predicted_seconds_1t"]), flush=True)
    return records


def circuit_dp(dirs, variant="collapsed", max_gib=64):
    """Exact distance of the time-collapsed problem by the dense DP on the best order of widths_circuits.json
    (cdist.auto.dp_distance); a lower bound on the circuit distance.  -> results/planar_dp/collapsed_dp/"""
    import common
    W = json.load(open(os.path.join(OUT, "widths_circuits.json")))
    os.makedirs(os.path.join(OUT, "collapsed_dp"), exist_ok=True)
    for d in dirs:
        prob = common.load(d, variant)
        p = common.to_cdist(prob)
        key = "%s:%s" % (prob.meta["name"], variant)
        w = W[key]
        order = w["order"]
        peak, work = plan_cost(p, order)
        rec = dict(instance=prob.meta["name"], variant=variant, rows=p.nrows, cols=p.ncols, width=w["width"],
                   table_bits=peak, work=work, threads=int(os.environ.get("OMP_NUM_THREADS", "0") or 0))
        if peak > math.log2(max_gib * GIB):
            rec.update(value=None, note="table 2^%d B above the %d GiB limit" % (peak, max_gib))
        else:
            t = time.time()
            value, per = auto.dp_distance(p, order, max_table_bytes=max_gib * GIB)
            rec.update(value=value, per_observable=per, seconds=round(time.time() - t, 2))
        json.dump(rec, open(os.path.join(OUT, "collapsed_dp", "%s__%s.json" % (prob.meta["name"], variant)), "w"),
                  indent=1)
        print("%-34s %s width %d table 2^%d B: DP value %s (%s s)" % (rec["instance"], variant, rec["width"], peak,
                                                                    rec.get("value"), rec.get("seconds")), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["widths", "export", "circuit-widths", "circuit-dp"])
    ap.add_argument("family", help="builder family, or for circuit-widths the variant (collapsed, sector)")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--improve", type=int, default=3000)
    a = ap.parse_args()
    if a.command == "circuit-dp":
        circuit_dp(a.names, variant=a.family)
    elif a.command == "circuit-widths":
        circuit_widths(a.names, variant=a.family, seeds=a.seeds, improve_iters=a.improve)
    elif a.command == "widths":
        widths(a.family, a.names, seeds=a.seeds, improve_iters=a.improve)
    else:
        export(a.family, a.names)


if __name__ == "__main__":
    main()
