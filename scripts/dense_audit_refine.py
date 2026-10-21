"""Spend additional ordering time on explicitly selected audit problems.

Uses only cdist.ordering's existing geometric sweeps, greedy order and local
search. The baseline audit remains intact; refinements retain their orders.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time

from dense_audit import Deadline, limited, ordering, plans, read, save, trellis, unpack


def refine(args):
    key, out, seconds = args
    out = Path(out)
    base = read(out / 'widths' / (key + '.json.gz'))
    dest = out / 'refinements' / (key + '.json.gz')
    if dest.exists():
        return key, 'cached'
    rec, h, l = unpack(out / 'inputs' / base['name'] / (base['variant'] + '.json.gz'))
    best = (base['width'], base['log2_volume']), base['order']
    t0 = time.monotonic()
    deadline = t0 + seconds
    trials = []
    for seed in range(100):
        try:
            if seed % 4 == 0 and len(h) <= 2000:
                start = limited(deadline - time.monotonic(), ordering.greedy_order, h, rec['nrows'], seed=24 + seed, noise=0.5)
            else:
                start = best[1]
            order, cost = limited(deadline - time.monotonic(), ordering.improve, h, start, iters=3000, seed=100 + seed)
        except Deadline:
            break
        trials.append(dict(seed=100 + seed, width=cost[0], log2_volume=cost[1], greedy_seed=24 + seed if seed % 4 == 0 and len(h) <= 2000 else None))
        if cost < best[0]:
            best = cost, order
        if time.monotonic() >= deadline:
            break
    cost, order = best
    pre = trellis.rank_profile(h, order)
    suf = trellis.rank_profile(h, order[::-1])[::-1]
    hp = max(pre[i + 1] + suf[i] - pre[-1] for i in range(len(h)))
    result = dict(name=rec['name'], variant=rec['variant'], width=cost[0], log2_volume=cost[1],
                  order=order, trials=trials, h_section_peak=hp, peak_bits_bounds=[hp, hp + 1],
                  seconds=time.monotonic() - t0, protocol='Additional greedy restarts and 3000-step local searches',
                  time_limit=seconds)
    if cost[0] <= 34:
        summaries = [dict(observable=i, peak_bits=p.peak_bits, work=p.work(), feasible=p.feasible)
                     for i, p in enumerate(plans(h, l, order, rec['nrows'], rec['nobs']))]
        result.update(plans=summaries, peak_bits=max(x['peak_bits'] for x in summaries),
                      total_work=sum(x['work'] for x in summaries))
    save(dest, result)
    return key, (base['width'], cost[0], result.get('peak_bits'), result['seconds'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--only', required=True, help='Comma-separated name__variant keys')
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--jobs', type=int, default=2)
    a = p.parse_args()
    with ProcessPoolExecutor(a.jobs) as pool:
        for result in pool.map(refine, [(key, str(a.out.resolve()), a.seconds) for key in a.only.split(',')]):
            print(result, flush=True)


if __name__ == '__main__':
    main()
