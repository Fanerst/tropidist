"""Profile or execute exact tree DP on a retained distance-audit input.

No decomposition search is repeated here. All logical observables are
profiled unless --observable explicitly selects one. A partial query is
never labelled the full distance. Profiles include actual augmented cuts,
join work, live table memory, and the safe integer dtype.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cdist.rankwidth import tree_from_flat, tree_profile
from cdist.tree_dp import CompiledTreeDP, TreeDPResourceError


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as f:
            return json.load(f)
    return json.loads(Path(path).read_text())


def save(path, result):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    if str(path).endswith('.gz'):
        with gzip.open(temporary, 'wt') as f:
            json.dump(result, f)
    else:
        temporary.write_text(json.dumps(result, indent=1) + '\n')
    temporary.replace(path)


def evaluate(input_path, candidate, *, execute=False, observable=None,
             max_memory_bytes=256 << 20, max_join_work=100_000_000,
             max_seconds=60.0, max_compile_bytes=256 << 20):
    data = read(input_path)
    h, l = [int(x, 16) for x in data['h']], [int(x, 16) for x in data['l']]
    nobs = data['nobs']
    if observable is not None and not 0 <= observable < nobs:
        raise ValueError('observable index out of range')
    queries = list(range(nobs)) if observable is None else [observable]
    tree = tree_from_flat(candidate['nodes'])
    # Exact replay on H is independent of the graph solver's advertised width.
    structural = tree_profile(h, tree)
    if structural['width'] != candidate['width']:
        raise ValueError('candidate cut width does not replay on the actual H matrix')
    row_bit = max((x.bit_length() for x in h), default=0)
    result = dict(name=data['name'], variant=data['variant'], input_sha256=data['input_sha256'],
                  input_file=str(input_path), method=candidate['method'],
                  tree_nodes=candidate['nodes'],
                  tree_sha256=hashlib.sha256(json.dumps(candidate['nodes']).encode()).hexdigest(),
                  h_profile=structural, ncols=len(h), nobs=nobs,
                  requested_observables=queries, mode='run' if execute else 'profile',
                  truth=data.get('truth'), truth_kind=data.get('truth_kind'),
                  threads=1, limits=dict(memory_bytes=max_memory_bytes,
                                        join_work_per_query=max_join_work,
                                        compile_bytes=max_compile_bytes,
                                        case_seconds=max_seconds),
                  queries=[], status='running')
    started = time.monotonic()
    try:
        for obs in queries:
            remaining = max_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise TreeDPResourceError('whole-case time limit exceeded')
            columns = [a | (((b >> obs) & 1) << row_bit) for a, b in zip(h, l)]
            program = CompiledTreeDP(columns, tree, max_compile_bytes=max_compile_bytes,
                                     max_compile_seconds=remaining)
            profile = program.preflight(max_memory_bytes=max_memory_bytes,
                                        max_join_work=max_join_work)
            query = dict(observable=obs, feasible=program.solver.solve(1 << row_bit) is not None,
                         profile=profile)
            if execute:
                remaining = max_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    raise TreeDPResourceError('whole-case time limit exceeded')
                value, stats = program.run(1 << row_bit, max_memory_bytes=max_memory_bytes,
                                           max_join_work=max_join_work, max_seconds=remaining)
                query.update(distance=value, execution=stats)
            result['queries'].append(query)
            del program
        result['status'] = 'profiled'
        if execute:
            finite = [q['distance'] for q in result['queries'] if q['distance'] is not None]
            result['distance'] = min(finite) if finite else None
            result['status'] = 'exact' if observable is None else 'exact_observable'
            if observable is None and data.get('truth_kind') == 'exact':
                result['agrees_with_truth'] = result['distance'] == data['truth']
                if not result['agrees_with_truth']:
                    result['status'] = 'mismatch'
    except TreeDPResourceError as exc:
        result.update(status='resource_limited', resource_error=str(exc),
                      rejected_profile=exc.profile)
    result['seconds'] = time.monotonic() - started
    result['peak_process_rss_bytes'] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                                          * (1 if sys.platform == 'darwin' else 1024))
    result['complete_observable_coverage'] = len(result['queries']) == nobs and observable is None
    profiles = [q['profile'] for q in result['queries']]
    if profiles:
        result.update(max_augmented_edge_width=max(p['max_interface_rank'] for p in profiles),
                      max_augmented_join_dimension=max(p['max_join_dimension'] for p in profiles),
                      max_single_table_bytes=max(p['largest_table_bytes'] for p in profiles),
                      max_dense_workspace_bytes=max(p['peak_dense_bytes'] for p in profiles),
                      total_join_work=sum(p['join_work'] for p in profiles))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--candidates', type=Path, required=True)
    p.add_argument('--method', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--run', action='store_true')
    p.add_argument('--observable', type=int)
    p.add_argument('--max-memory-mib', type=float, default=256)
    p.add_argument('--max-compile-mib', type=float, default=256)
    p.add_argument('--max-pairs', type=int, default=100_000_000)
    p.add_argument('--seconds', type=float, default=60)
    a = p.parse_args()
    if min(a.max_memory_mib, a.max_compile_mib, a.max_pairs, a.seconds) <= 0:
        p.error('resource limits must be positive')
    candidates = read(a.candidates)
    matches = [c for c in candidates['candidates'] if c['method'] == a.method]
    if len(matches) != 1:
        p.error('method must select exactly one candidate')
    result = evaluate(a.input, matches[0], execute=a.run, observable=a.observable,
                      max_memory_bytes=int(a.max_memory_mib * (1 << 20)),
                      max_compile_bytes=int(a.max_compile_mib * (1 << 20)),
                      max_join_work=a.max_pairs, max_seconds=a.seconds)
    save(a.out, result)
    print(json.dumps({k: result.get(k) for k in ('name', 'variant', 'method', 'status',
                     'distance', 'max_augmented_edge_width', 'max_augmented_join_dimension',
                     'max_single_table_bytes', 'max_dense_workspace_bytes', 'seconds')}))
    if result['status'] == 'mismatch':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
