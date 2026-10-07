"""How much could an admissible completion bound prune from the guided DFS?

For random nodes of the K-threshold search (Knuth walks), compute the exact
minimum number of columns that cancel the residual syndrome
  c_free : ignoring logicals, disjointness and forbidden columns
  c_log  : additionally requiring a nonzero total logical
and compare with the remaining budget R = K - depth.  A node with c > R can be
pruned by a bound that depends only on (residual, logical).  The fractions
are Knuth-weighted, i.e. fractions of the actual node counts.

Usage: python phase4/headroom.py bb288_r18_Z:collapsed 15 3 8,9,10,11 400 [validate_K]
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CancelCost, Walker, bits, load, log, search  # noqa: E402


def main(spec, K, k, depths, samples, validate_K=0, log_too=1):
    K, k, samples, log_too = int(K), int(k), int(samples), int(log_too)
    depths = [int(x) for x in depths.split(",")]
    p, sym = load(spec)
    log(spec, f"rows={p.nrows} cols={p.ncols} obs={p.nobs} anchors={len(sym['anchors']) if sym.get('ok') else 'all'}")
    W = Walker(p, sym, K)
    res = {"spec": spec, "K": K, "k": k, "rows": p.nrows, "cols": p.ncols, "wmax": W.wmax, "depths": {}}
    if int(validate_K):
        # Knuth estimates of the node counts against an actual run
        VK = int(validate_K)
        W2 = Walker(p, sym, VK)
        main_tab = search.Table(p, k)
        W2.S.add_table(main_tab, exact=True)
        r = W2.S.search(VK, task_depth=1)
        rng = random.Random(7)
        est = {}
        for d in range(1, VK - k):
            tot = 0
            n = 4000
            for _ in range(n):
                w = W2.walk(d, rng)
                if w:
                    tot += w[0]
            est[d] = tot / n
        res["validate"] = {"K": VK, "actual": r["nodes"], "knuth": est}
        log("validate K", VK, "actual", r["nodes"][:VK - k], "knuth", {d: f"{v:.3g}" for d, v in est.items()})
        main_tab.free()
    cc = CancelCost(W.S, k)
    rng = random.Random(1)
    for d in depths:
        R = K - d
        tot_w = 0.0
        n_reach = 0
        acc = {"popcount": 0.0, "free": 0.0, "log": 0.0}
        hist_free, hist_log = {}, {}
        pcs = []
        for _ in range(samples):
            w = W.walk(d, rng)
            if w is None:
                continue
            weight, sigma, lg, path, forb = w
            n_reach += 1
            tot_w += weight
            if sigma == 0 or len(bits(sigma)) > W.wmax * R:
                acc["popcount"] += weight
                acc["free"] += weight
                acc["log"] += weight
                continue
            # c_free <= depth always (the prefix itself), so only depth > R can be pruned;
            # cap = R decides prunability without the expensive exact value
            cf = cc(sigma, lg, False, R)
            cl = cf if cf > R or not log_too else cc(sigma, lg, True, R)
            pcs.append(len(bits(sigma)))
            hist_free[cf] = hist_free.get(cf, 0) + 1
            hist_log[cl] = hist_log.get(cl, 0) + 1
            if cf > R:
                acc["free"] += weight
            if cl > R:
                acc["log"] += weight
        frac = {x: (v / tot_w if tot_w else None) for x, v in acc.items()}
        res["depths"][d] = {"R": R, "walks": samples, "reached": n_reach, "est_nodes": tot_w / samples,
                            "prunable_fraction": frac, "mean_residual_weight": sum(pcs) / max(1, len(pcs)),
                            "hist_free": dict(sorted(hist_free.items())), "hist_log": dict(sorted(hist_log.items()))}
        log(f"depth {d} R={R}: reached {n_reach}/{samples} est_nodes={tot_w / samples:.3g} "
            f"|sigma|~{sum(pcs) / max(1, len(pcs)):.1f} prunable popcount={frac['popcount']:.3f} free={frac['free']:.3f} log={frac['log']:.3f} "
            f"hist_free={dict(sorted(hist_free.items()))} hist_log={dict(sorted(hist_log.items()))}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results",
                       f"headroom_{spec.replace(':', '_').replace('[', '').replace(']', '').replace(',', '-')}_K{K}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    log("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
