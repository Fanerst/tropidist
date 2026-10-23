"""Choice between the exact evaluators of the distance.

The dense Rank DP on a linear decomposition (trellis.py, kernel.py) costs about
(number of logical queries) x (table entries touched), which is set by the cut
rank of the column order and not by the distance.  The weight-bounded search
(search.py) costs what its pruning leaves of the tree up to the distance.  On
geometrically local codes the first is small and the second explodes with d; on
expanding qLDPC codes it is the other way round (scripts/dp_vs_search_local.py).

The DP's cost can be computed exactly from its plan before anything is run, so
the front end decides from it:

  estimate(p)       column order, largest table (bytes) and the work of all
                    logical queries, and a predicted time from a calibrated rate
  dp_distance(p)    exact distance by the DP (one query per logical observable)

The third evaluator is the same trellis truncated at a weight threshold K, with a meet-in-the-middle split of the
weight (sparse_dp.py, results/sparse_dp).  Its cost grows with K and with how many low-weight partial solutions
stay distinct at a cut; it wins on wide problems whose partial solutions merge (local circuits that are not
graph-like), and it needs a threshold to aim at, usually an upper bound minus one:

  sparse_estimate(p, K, order)    predicted time, work and memory of the sweep at K, from probe sweeps
  sparse_distance(p, K, order)    the least weight of a solution if it is <= K, with a witness; else None

The choice itself (DP now, search first with the DP as fallback, or search only)
belongs to the caller, which knows its time and memory budget; see the dp option
of bench/adapters/ours_pipeline.py.
"""
from __future__ import annotations

import math
import time

from . import kernel, ordering, trellis

# Table entries touched per second by kernel.run_plan (uint8 tables) on the benchmark server, 2026-10-22
# (scripts/calibrate_dp.py, results/dp_calibration): 1.0e9 to 4.8e9 on one thread (median 1.4e9 over runs of at
# least 0.5 s), median 1.9e10 on 32 threads (13x).  Only used for predictions, slightly conservatively.
RATE_ONE_THREAD = 1.3e9
THREAD_EFFICIENCY = 0.4           # fraction of linear speed-up kept per added thread (13x at 32 threads)


def predicted_seconds(work, threads=1):
    rate = RATE_ONE_THREAD * (1 + THREAD_EFFICIENCY * (max(1, threads) - 1))
    return work / rate


def best_order(p, seeds=2, time_limit=None):
    """Smallest (peak cut rank, log2 volume) among the given column order, its reverse and greedy orders."""
    t0 = time.time()
    cands = [list(range(p.ncols)), list(reversed(range(p.ncols)))]
    best = None
    for c in cands:
        cost = ordering.profile_cost(trellis.cut_profile(p.h, c))
        if best is None or cost < best[0]:
            best = (cost, c)
    for s in range(seeds):
        if time_limit is not None and time.time() - t0 > time_limit:
            break
        o = ordering.greedy_order(p.h, p.nrows, seed=s, noise=0.5 if s else 0.0)
        cost = ordering.profile_cost(trellis.cut_profile(p.h, o))
        if cost < best[0]:
            best = (cost, o)
    return best[1], best[0]


def _plans(p, order):
    """One plan per logical observable; the span form of H is shared."""
    hrows = trellis.minimal_span_form(trellis.rows_from_columns(p.h, order, p.nrows))
    for i in range(p.nobs):
        lrow = 0
        for pos, j in enumerate(order):
            if (p.l[j] >> i) & 1:
                lrow |= 1 << pos
        lrow = trellis.reduce_target_row(lrow, hrows)
        yield i, trellis.make_plan(hrows, lrow, len(order))


def estimate(p, threads=1, seeds=2, time_limit=None, max_table_bytes=None):
    """DP cost of the best order found; nothing is allocated.

    If the order's cut rank alone puts the smallest possible table above max_table_bytes, no plan is built
    (fits=False).  Otherwise the plan of the first feasible observable is built and its work is scaled by the
    number of observables (the plans differ only in the target row: tables differ by at most one bit)."""
    t0 = time.time()
    order, cost = best_order(p, seeds=seeds, time_limit=time_limit)
    out = {"order": order, "cut_rank": int(cost[0]), "queries": p.nobs}
    if max_table_bytes is not None and cost[0] > math.log2(max_table_bytes):
        out.update(peak_bits=int(cost[0]), table_bytes=1 << int(cost[0]), work=None, predicted_seconds=math.inf,
                   fits=False, estimate_seconds=time.time() - t0)
        return out
    peak, work = 0, None
    for _, plan in _plans(p, order):
        if plan.feasible:
            # +1: a margin for the other target rows; a single observable has only this plan
            peak, work = plan.peak_bits + (1 if p.nobs > 1 else 0), plan.work() * p.nobs
            break
    if work is None:
        work = 0
    out.update(peak_bits=peak, table_bytes=1 << peak, work=work, predicted_seconds=predicted_seconds(work, threads),
               fits=max_table_bytes is None or (1 << peak) <= max_table_bytes, estimate_seconds=time.time() - t0)
    return out


def dp_distance(p, order, max_table_bytes=None, deadline=None):
    """Exact distance min over observables i of min{|e| : H e = 0, (L e)_i = 1}; None if no logical exists.
    Raises MemoryError if a table would exceed max_table_bytes, TimeoutError past deadline (time.monotonic)."""
    best = None
    per = []
    for i, plan in _plans(p, order):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError("DP stopped at the time limit")
        if not plan.feasible:
            per.append(None)
            continue
        if max_table_bytes is not None and (1 << plan.peak_bits) > max_table_bytes:
            raise MemoryError("DP table of 2^%d bytes exceeds the limit" % plan.peak_bits)
        v, _ = kernel.run_plan(plan)
        per.append(v)
        if v is not None and (best is None or v < best):
            best = v
    return best, per


def dp_witness(p, order, obs, max_bytes=1 << 30):
    """Columns of a minimum-weight solution of min{|e| : H e = 0, (L e)_obs = 1}, by a traceback of the DP on the
    given order; None if no logical exists or the tables of all column steps (the plan's work, one byte each)
    exceed max_bytes.  The trellis plan is replayed with numpy, keeping the table before every column step."""
    import numpy as np
    INF = kernel.INF
    hrows = trellis.minimal_span_form(trellis.rows_from_columns(p.h, order, p.nrows))
    lrow = 0
    for pos, j in enumerate(order):
        if (p.l[j] >> obs) & 1:
            lrow |= 1 << pos
    lrow = trellis.reduce_target_row(lrow, hrows)
    if lrow == 0:
        return None
    if trellis.make_plan(hrows, lrow, len(order)).work() > max_bytes:
        return None
    rows = [(r, 0) for r in hrows] + [(lrow, 1)]
    start_at, end_at = {}, {}
    for idx, (r, _) in enumerate(rows):
        start_at.setdefault(trellis.lowbit(r), []).append(idx)
        end_at.setdefault(r.bit_length() - 1, []).append(idx)
    active, hist = [], []
    T = np.zeros(1, dtype=np.uint8)
    for j in range(len(order)):                  # the steps of trellis.make_plan, executed and recorded
        for idx in start_at.get(j, ()):
            active.append(idx)
            T = np.concatenate([T, np.full(T.size, INF, dtype=np.uint8)])
            hist.append(("expand", len(active) - 1))      # the new row is the highest bit of the state
        mask = sum(1 << pos for pos, idx in enumerate(active) if (rows[idx][0] >> j) & 1)
        if mask:
            other = T[np.arange(T.size, dtype=np.int64) ^ mask]
            other = np.where(other == INF, INF, other + 1).astype(np.uint8)
            hist.append(("update", mask, j, T))
            T = np.minimum(T, other)
        for pos in sorted((active.index(idx) for idx in end_at.get(j, ())), reverse=True):
            target = rows[active[pos]][1]
            T = T[((np.arange(T.size, dtype=np.int64) >> pos) & 1) == target]
            hist.append(("select", pos, target))
            active.pop(pos)
    if int(T[0]) == INF:
        return None
    state, value, used = 0, int(T[0]), []
    for step in reversed(hist):
        if step[0] == "select":
            _, pos, target = step
            state = ((state >> pos) << (pos + 1)) | (target << pos) | (state & ((1 << pos) - 1))
        elif step[0] == "expand":
            # entries with the new row's bit set start at infinity, so on the minimum path that bit is 0 here
            assert not (state >> step[1]) & 1
        else:
            _, mask, j, before = step
            if int(before[state]) != value:          # the minimum at this step uses column j
                used.append(order[j])
                state ^= mask
                value -= 1
                assert int(before[state]) == value
    assert value == 0
    return sorted(used)


# ---------------------------------------------------------------------- the sparse (weight-truncated) Rank DP
# Seconds per state and column of the C tables (one thread, 5090, results/sparse_dp: 7-14 ns on large sweeps) and
# per column step (Python and call overhead), for predictions only.  A meet-in-the-middle sweep makes about three
# passes over the columns (backward, forward, recomputation of the backward tables).
SPARSE_SECONDS_PER_STATE = 1.0e-8
SPARSE_SECONDS_PER_STEP = 2.0e-5
SPARSE_MAX_SLOTS = 56                # row slots of the C tables
# The probe measures the states of weight <= 2 in both directions, and those of weight 3 in a direction whose
# weight-3 states (estimated from weights 1 and 2, 1.4-4x high on the benchmark circuits) cost at most this share
# of the sweep predicted from weight 2, and only when that prediction is within SPARSE_PROBE_SLACK of the caller's
# limits.  Measuring weight 3 lowers the prediction 1.2-4x on the superdense circuits; on star_42 it cost 10.7 s
# against a 0.7 s search and changed the prediction by 3% (results/sparse_dp).
SPARSE_PROBE_SHARE = 0.25
SPARSE_PROBE_SLACK = 10.0


def sparse_trellises(p, order):
    """One trellis per observable of p in the given column order (sparse_dp.Trellis; infeasible where the
    observable is a combination of the checks)."""
    from . import sparse_dp
    return [sparse_dp.Trellis.for_query(p, i, order) for i in range(p.nobs)]


def sparse_estimate(p, K, order, trellises=None, probe=3, max_seconds=None, max_bytes=None):
    """Predicted cost of one meet-in-the-middle sweep at threshold K on every observable: the split schedule and
    the work come from probe sweeps of the first observable, whose trellis differs from the others only in the
    target row, and are scaled by the number of observables.  The probe keeps weights <= 2, and <= `probe` in a
    direction where that is cheap next to the predicted sweep (SPARSE_PROBE_SHARE), unless the prediction from
    weight 2 exceeds max_seconds or max_bytes more than SPARSE_PROBE_SLACK times.  On circuits the prediction is
    within 0.8-1.0x of the work done with weight 3 measured, and 1-2.5x high from weight 2; on codes it can be 10x
    low (sparse_dp.choose_schedule).  fits=False if a trellis needs more row slots than the C tables hold.
    Memory: the checkpoints, one recomputed segment of tables and the step buffers, 8 bytes per state, from the
    predicted table at every cut."""
    from . import sparse_dp
    t0 = time.time()
    out = {"K": K, "fits": False}
    try:
        trs = sparse_trellises(p, order) if trellises is None else trellises
    except ValueError as exc:                          # more row slots than a 64-bit state holds
        out.update(reason=str(exc), slots=None, estimate_seconds=time.time() - t0)
        return out
    feas = [t for t in trs if t.feasible]
    out["queries"] = len(feas)
    if not feas:
        out.update(reason="no observable can be flipped", estimate_seconds=time.time() - t0)
        return out
    slots = max(t.nslots for t in feas)
    out.update(slots=slots, cut_rank=max(max(t.width) for t in feas))
    if slots > SPARSE_MAX_SLOTS:
        out.update(reason="the trellis needs %d row slots, the C tables hold %d" % (slots, SPARSE_MAX_SLOTS),
                   estimate_seconds=time.time() - t0)
        return out
    n = feas[0].N
    steps = 3 * n * len(feas)
    seconds = lambda info: (info["predicted_work"] * len(feas) * SPARSE_SECONDS_PER_STATE
                            + steps * SPARSE_SECONDS_PER_STEP)
    sched, info = sparse_dp.choose_schedule(feas[0], K, "c", probe=min(2, probe))
    probe_seconds = info["probe_seconds"]
    if probe > 2 and (max_seconds is None or seconds(info) <= SPARSE_PROBE_SLACK * max_seconds) \
            and (max_bytes is None or info["predicted_bytes"] <= SPARSE_PROBE_SLACK * max_bytes):
        budget = min(2e9, SPARSE_PROBE_SHARE * info["predicted_work"] * len(feas))
        sched, info = sparse_dp.choose_schedule(feas[0], K, "c", probe=probe, budget=budget)
        probe_seconds += info["probe_seconds"]
    out.update(fits=True, schedule=sched, schedule_runs=info["schedule"],
               predicted_work=info["predicted_work"] * len(feas), predicted_seconds=seconds(info),
               predicted_bytes=info["predicted_bytes"],                 # the queries run one after the other
               predicted_peak_states=info["predicted_peak_states"], probe_seconds=probe_seconds,
               probe_weights=[len(info["forward_profile"]) - 1, len(info["backward_profile"]) - 1],
               estimate_seconds=time.time() - t0)
    return out


def sparse_distance(p, K, order, trellises=None, schedule=None, lower=0, deadline=None, max_bytes=None, log=None):
    """The least weight of a solution of min{|e| : H e = 0, L e != 0} if it is <= K, as (value, columns of p,
    observable); None if no solution has weight <= K.  One meet-in-the-middle sweep per observable (after a
    solution of weight v the others are swept at v - 1); schedule: a split per cut (e.g. sparse_estimate's), else
    one is chosen per observable.  lower: a certified lower bound, a solution of that weight ends the sweeps.
    Raises TimeoutError past deadline (time.monotonic()), MemoryError where the tables would exceed max_bytes."""
    from . import sparse_dp
    trs = sparse_trellises(p, order) if trellises is None else trellises
    best = None
    for i, tr in enumerate(trs):
        if not tr.feasible:
            continue
        k = K if best is None else best[0] - 1
        if k < max(1, lower):
            break
        split = schedule if schedule is not None and len(schedule) == tr.N + 1 else "schedule"
        every = max(1, int(math.isqrt(tr.N)))
        cap = None if max_bytes is None else max(1, int(max_bytes // (8 * (every + 4))))
        try:
            r = sparse_dp.query(tr, k, mode="mitm", split=split, use_h=False, witness=True, lower=lower,
                                backend="c", deadline=deadline, max_states=cap, log=log)
        except sparse_dp.BudgetExceeded as exc:
            raise (TimeoutError if exc.kind == "deadline" else MemoryError)(str(exc))
        if r["value"] is not None:
            best = (r["value"], r["witness"], i)
            if r["value"] <= lower:
                break
    return best
