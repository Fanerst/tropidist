"""Reproducible audit of the existing trellis and ordering implementations.

No solver implementation is changed. Inputs, permutations and individual
observable results are retained. See docs/notes/DENSE_DP_AUDIT.md for the protocol.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'bench'), str(ROOT / 'papers')]
from cdist import ordering, trellis


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + '.tmp')
    if path.suffix == '.gz':
        with gzip.open(staging, 'wt') as f:
            json.dump(obj, f)
    else:
        staging.write_text(json.dumps(obj, indent=1) + '\n')
    staging.replace(path)


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as f:
            return json.load(f)
    return json.loads(Path(path).read_text())


def matrix_hash(cols, nrows):
    """Hash the exact MatrixMarket serialization used by bench.common."""
    h = hashlib.sha256()
    h.update(('%%MatrixMarket matrix coordinate pattern general\n'
              + f'{nrows} {len(cols)} {sum(c.bit_count() for c in cols)}\n').encode())
    for j, c in enumerate(cols):
        while c:
            b = c & -c
            h.update(f'{b.bit_length()} {j + 1}\n'.encode())
            c ^= b
    return h.hexdigest()


def prepare_one(args):
    metapath, out, sources = args
    sources = Path(sources)
    sys.path.insert(0, str(sources / 'amplified' / 'dp_certificates_github-0772a00' / 'simulation' / 'source'))
    import common
    import instances
    import stabcode
    import stim
    from cdist import problem
    meta = read(metapath)
    name = meta['name']
    suite = 'wjh' if 'instances_wjh' in str(metapath) else 'main'
    directory = Path(out) / 'inputs' / name
    status_path = Path(out) / 'preparation' / (name + '.json')
    if status_path.exists() and read(status_path).get('status') == 'ok':
        return name, 'cached'
    t0 = time.monotonic()
    try:
        spec = deepcopy(meta['source'])
        if not isinstance(spec, dict):
            if name == 'fx_bb72_code':
                spec = dict(builder='code_bb', key='bb72', basis='Z', track='code')
            else:
                spec = dict(builder='ordered', module='sdbb_parallel', key=16, basis='Z', rounds=3,
                            track='circuit', order=[(x[0], int(x[1:])) for x in meta['source'].split('order=')[1].rstrip(')').split()])
        typ = spec['builder']
        if 'order' in spec:
            spec['order'] = [tuple(x) for x in spec['order']]
        directory.mkdir(parents=True, exist_ok=True)
        if meta['track'] == 'code':
            if typ == 'wjh_code':
                instances.WJH_CODES = str(sources / 'codedistance_codes.json')
            if typ == 'kasai':
                import kasai_codes
                kasai_codes.DATA = str(sources / 'kasai')
                _, hx, hz, n, _, _ = kasai_codes.load(str(sources / 'kasai' / spec['key']), kasai_codes.shift_convention())
            else:
                hx, hz, n, _ = instances._code(spec)
            _, k = stabcode.css_parameters(hx, hz, n)
            assert (n, k) == (meta['n'], meta['k']), (name, n, k)
            probs = {'full': stabcode.css_distance_problem(hx, hz, n, spec['basis'], name=name)}
            exact_sector = None
        else:
            if typ == 'wjh_circuit':
                source = sources / 'codedistance' / 'codeDistancePYPI-a4afe9c'
                spec['circuit_file'] = str(source / Path(spec['circuit_file']).relative_to('papers/downloads/codedistance'))
            if typ == 'mitten':
                import mitten_circuit
                d = sources / 'yarn' / 'yarn-1b58edd' / 'processor_codes' / 'mitten' / Path(spec['code_dir']).name
                circ = mitten_circuit.build(str(d), spec['basis'], spec['rounds'])
            else:
                circ, _ = instances._circuit(spec)
            path = directory / 'circuit.stim'
            circ.to_file(str(path))
            # Stream the DEM to avoid storing the million-column full variant
            # when the benchmark uses an exact memory-sector reduction.
            coordinate_map = circ.get_detector_coordinates()
            coords = [tuple(coordinate_map.get(i, ())) for i in range(circ.num_detectors)]
            use_sector = 'sector' in meta['variants']
            if use_sector:
                dummy = problem.Problem(name, circ.num_detectors, circ.num_observables, [], [], coords)
                kept = problem.sector_rows(dummy, spec.get('sector_high'))
            else:
                kept = list(range(circ.num_detectors))
            rowmap = {r: i for i, r in enumerate(kept)}
            pairs, pure = {}, set()
            dem = circ.detector_error_model(decompose_errors=False, flatten_loops=True)
            for inst in dem:
                if inst.type != 'error':
                    continue
                h = l = 0
                outside = False
                for v in inst.targets_copy():
                    if v.is_relative_detector_id():
                        if v.val in rowmap:
                            h ^= 1 << rowmap[v.val]
                        else:
                            outside = True
                    elif v.is_logical_observable_id():
                        l ^= 1 << v.val
                if h or l:
                    pairs.setdefault((h, l), len(pairs))
                    if not outside:
                        pure.add((h, l))
            exact_sector = set(pairs).issubset(pure) if use_sector else None
            assert not use_sector or exact_sector, 'sector is not an exact reduction'
            h, l = map(list, zip(*pairs))
            p = problem.Problem(name, len(kept), circ.num_observables, h, l,
                                [coords[i] for i in kept], [[j] for j in range(len(h))])
            probs = {'sector' if use_sector else 'full': p}
            if use_sector:
                probs['collapsed'] = problem.collapse_time(p)
        written = []
        for variant, p in probs.items():
            expected = meta['variants'][variant]
            assert (p.nrows, p.ncols, p.nobs) == (expected['rows'], expected['cols'], expected['obs']), (name, variant, p.nrows, p.ncols, p.nobs, expected)
            rec = dict(name=name, suite=suite, family=meta['family'], track=meta['track'], variant=variant,
                       n=meta['n'], k=meta['k'], basis=meta.get('basis'), nrows=p.nrows, ncols=p.ncols, nobs=p.nobs,
                       h=[hex(x) for x in p.h], l=[hex(x) for x in p.l], rowmeta=p.row_meta,
                       truth=expected.get('distance'), truth_kind=expected.get('distance_kind'),
                       exact_sector=exact_sector, metadata=meta,
                       input_sha256={'H': matrix_hash(p.h, p.nrows), 'L': matrix_hash(p.l, p.nobs)})
            save(directory / (variant + '.json.gz'), rec)
            written.append(variant)
        status = dict(name=name, status='ok', variants=written, seconds=time.monotonic() - t0)
    except Exception:
        status = dict(name=name, status='error', error=traceback.format_exc(), seconds=time.monotonic() - t0)
    save(status_path, status)
    return name, status['status']


class Deadline(Exception):
    pass


def alarm(_signum, _frame):
    raise Deadline()


def limited(seconds, fn, *args, **kwargs):
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, seconds))
    try:
        return fn(*args, **kwargs)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def unpack(path):
    rec = read(path)
    return rec, [int(x, 16) for x in rec['h']], [int(x, 16) for x in rec['l']]


def plans(h, l, order, nrows, nobs):
    hrows = trellis.minimal_span_form(trellis.rows_from_columns(h, order, nrows))
    lrows = trellis.rows_from_columns(l, order, nobs)
    for lr in lrows:
        yield trellis.make_plan(hrows, trellis.reduce_target_row(lr, hrows), len(order))


def width_one(args):
    path, out, greedy_seconds, improve_seconds, seeds, iterations = args
    rec, h, l = unpack(path)
    key = rec['name'] + '__' + rec['variant']
    dest = Path(out) / 'widths' / (key + '.json.gz')
    if dest.exists():
        return key, 'cached'
    t0 = time.monotonic()
    result = {k: v for k, v in rec.items() if k not in ('h', 'l', 'rowmeta', 'metadata')}
    result['protocol'] = dict(greedy_seconds=greedy_seconds, improve_seconds=improve_seconds,
                              seeds=seeds, iterations=iterations)
    trials = []
    best = None

    def consider(label, order):
        nonlocal best
        cost = ordering.profile_cost(trellis.cut_profile(h, order))
        trials.append(dict(label=label, width=cost[0], log2_volume=cost[1]))
        if best is None or cost < best[0]:
            best = cost, order, label

    consider('natural', list(range(len(h))))
    if rec['variant'] == 'sector':
        def time_key(j):
            v = h[j]
            ts = []
            while v:
                b = v & -v
                ts.append(rec['rowmeta'][b.bit_length() - 1][2])
                v ^= b
            return (min(ts, default=-1), max(ts, default=-1), j)
        consider('time', sorted(range(len(h)), key=time_key))
    deadline = time.monotonic() + greedy_seconds
    greedy_timed_out = False
    for seed in range(seeds):
        if time.monotonic() >= deadline:
            greedy_timed_out = True
            break
        try:
            order = limited(deadline - time.monotonic(), ordering.greedy_order, h, rec['nrows'], seed=seed, noise=0.5 if seed else 0.0)
        except Deadline:
            greedy_timed_out = True
            break
        consider(f'greedy-{seed}', order)
    greedy_best = min((x['width'], x['log2_volume']) for x in trials if x['label'].startswith('greedy')) if any(x['label'].startswith('greedy') for x in trials) else None
    before = best[0]
    deadline = time.monotonic() + improve_seconds
    completed_iters = 0
    for block in range(math.ceil(iterations / 100)):
        try:
            order, cost = limited(deadline - time.monotonic(), ordering.improve, h, best[1], iters=min(100, iterations - completed_iters), seed=1 + block)
        except Deadline:
            break
        completed_iters += min(100, iterations - completed_iters)
        if cost < best[0]:
            best = cost, order, 'local'
        if time.monotonic() >= deadline:
            break
    cost, order, label = best
    profile = trellis.cut_profile(h, order)
    # Section width counts H rows active during an update, before row endings.
    pre = trellis.rank_profile(h, order)
    suf = trellis.rank_profile(h, order[::-1])[::-1]
    h_peak = max(pre[i+1] + suf[i] - pre[-1] for i in range(len(h)))
    result.update(status='ok', width=cost[0], log2_volume=cost[1], rank=pre[-1],
                  ordering=label, trials=trials, greedy_best=greedy_best, before_local=before,
                  greedy_timed_out=greedy_timed_out, local_iterations=completed_iters,
                  order=order, profile=profile, h_section_peak=h_peak,
                  peak_bits_bounds=[h_peak, h_peak + 1])
    if cost[0] <= 34:
        summaries = []
        for i, plan in enumerate(plans(h, l, order, rec['nrows'], rec['nobs'])):
            summaries.append(dict(observable=i, peak_bits=plan.peak_bits, work=plan.work(), feasible=plan.feasible))
        result['plans'] = summaries
        result['peak_bits'] = max(p['peak_bits'] for p in summaries)
        result['total_work'] = sum(p['work'] for p in summaries)
    result['seconds'] = time.monotonic() - t0
    save(dest, result)
    return key, (result['width'], result.get('peak_bits', result['peak_bits_bounds']), round(result['seconds'], 2))


def run_one(path, out, max_bits, seconds):
    from cdist import kernel
    w = read(path)
    key = w['name'] + '__' + w['variant']
    dest = Path(out) / 'runs' / (key + '.json')
    if dest.exists() and read(dest).get('status') == 'exact':
        return key, 'cached'
    if w.get('peak_bits', 10000) > max_bits:
        return key, 'memory_skip'
    rec, h, l = unpack(Path(out) / 'inputs' / w['name'] / (w['variant'] + '.json.gz'))
    res = dict(name=w['name'], variant=w['variant'], status='running', peak_bits=w['peak_bits'],
               input_sha256=rec['input_sha256'], threads=kernel.lib().dp_num_threads(),
               ordering_width=w['width'], total_work=w['total_work'],
               order_sha256=hashlib.sha256(json.dumps(w['order']).encode()).hexdigest(),
               max_bits=max_bits, time_limit=seconds, per_observable=[])
    t0 = time.monotonic()
    prepared = list(plans(h, l, w['order'], rec['nrows'], rec['nobs']))
    res['plan_seconds'] = time.monotonic() - t0
    save(dest, res)
    try:
        for i, plan in enumerate(prepared):
            elapsed = time.monotonic() - t0
            if elapsed >= seconds:
                raise Deadline()
            d, st = limited(seconds - elapsed, kernel.run_plan, plan)
            res['per_observable'].append(dict(observable=i, distance=d, **st))
            res['seconds'] = time.monotonic() - t0
            save(dest, res)
        finite = [x['distance'] for x in res['per_observable'] if x['distance'] is not None]
        res['distance'] = min(finite) if finite else None
        res['status'] = 'exact' if finite else 'infeasible_or_uint8_saturated'
        res['agrees_with_truth'] = (res['distance'] == rec['truth']) if rec['truth_kind'] == 'exact' else None
        if res['agrees_with_truth'] is False:
            res['status'] = 'mismatch'
        references = Path(out) / 'reference_distances.json'
        if references.exists() and key in read(references):
            ref = read(references)[key]
            res['reference'] = ref
            res['agrees_with_reference'] = res['distance'] == ref['distance']
            if not res['agrees_with_reference']:
                res['status'] = 'mismatch'
    except Deadline:
        res['status'] = 'timeout'
    res['seconds'] = time.monotonic() - t0
    res['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
    save(dest, res)
    return key, (res['status'], res.get('distance'), round(res['seconds'], 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=['prepare', 'widths', 'run'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sources', type=Path)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--only', default='')
    ap.add_argument('--greedy-seconds', type=float, default=12)
    ap.add_argument('--improve-seconds', type=float, default=6)
    ap.add_argument('--seeds', type=int, default=24)
    ap.add_argument('--iterations', type=int, default=3000)
    ap.add_argument('--max-bits', type=int, default=30)
    ap.add_argument('--seconds', type=float, default=300)
    a = ap.parse_args()
    a.out = a.out.resolve()
    if a.stage == 'prepare':
        paths = sorted((ROOT / 'bench').glob('instances*/**/meta.json'))
        tasks = [(str(p), str(a.out), str(a.sources.resolve())) for p in paths if not a.only or p.parent.name in a.only.split(',')]
        fn = prepare_one
    elif a.stage == 'widths':
        tasks = [(str(p), str(a.out), a.greedy_seconds, a.improve_seconds, a.seeds, a.iterations)
                 for p in sorted((a.out / 'inputs').glob('*/*.json.gz')) if not a.only or p.parent.name in a.only.split(',')]
        fn = width_one
    else:
        # Sequential runs prevent several exponential tables competing for RAM.
        selected = {p.name: p for p in (a.out / 'widths').glob('*.json.gz')}
        for p in (a.out / 'refinements').glob('*.json.gz'):
            old, new = read(selected[p.name]), read(p)
            if (new['width'], new['log2_volume']) < (old['width'], old['log2_volume']):
                selected[p.name] = p
        paths = sorted(selected.values(), key=lambda p: read(p).get('total_work', 10**300))
        paths = [p for p in paths if read(p).get('peak_bits', 10000) <= a.max_bits]
        with ProcessPoolExecutor(max_workers=1, max_tasks_per_child=1) as pool:
            for path in paths:
                if not a.only or read(path)['name'] in a.only.split(','):
                    print(pool.submit(run_one, path, a.out, a.max_bits, a.seconds).result(), flush=True)
        return
    with ProcessPoolExecutor(a.jobs) as pool:
        futures = {pool.submit(fn, x): x[0] for x in tasks}
        for f in as_completed(futures):
            try:
                print(f.result(), flush=True)
            except Exception:
                print(futures[f], traceback.format_exc(), flush=True)


if __name__ == '__main__':
    main()
