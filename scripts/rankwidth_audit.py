"""Bounded rank-decomposition experiments on saved dense-audit inputs.

Run with one worker.  This script constructs and checks trees; it never runs
distance DP.  External sources/builds stay under project temp and all witness
data stays in results.  The optional sibling implementation is imported only
when its existing NNI search is requested.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
            'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'DOTNET_PROCESSOR_COUNT'):
    os.environ[key] = '1'
os.environ['DOTNET_GCHeapHardLimit'] = '0x60000000'
os.environ['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
os.environ['DOTNET_SKIP_FIRST_TIME_EXPERIENCE'] = '1'
os.environ['DOTNET_GENERATE_ASPNET_CERTIFICATE'] = 'false'
os.environ['DOTNET_gcConcurrent'] = '0'

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT))
from cdist import rankwidth as rw


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as stream:
            return json.load(stream)
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(path.suffix + '.tmp')
    staging.write_text(json.dumps(value, indent=1) + '\n')
    staging.replace(path)


def candidate(columns, graph, tree, method, seconds=0.0, **extra):
    profile = rw.tree_profile(columns, tree, include_nodes=True)
    replay = rw.graph_tree_width(graph.adjacency, tree)
    if replay != profile['width']:
        raise RuntimeError('fundamental-graph cut width differs from matroid connectivity')
    return dict(method=method, status='verified_upper_bound', seconds=seconds,
                graph_width_replayed=replay, **profile, **extra)


def sibling_nni(graph, initial, seconds, seed, target=None):
    sys.path.insert(0, str(PROJECT / 'DecisionDiagramDecoder-github/src'))
    from rank_width_qec.decomposition import (
        Decomposition, DecompositionNode, improve_decomposition_nni,
    )
    flat, _ = rw.flatten_tree(initial, len(graph.adjacency))
    source = Decomposition(len(graph.adjacency), tuple(
        DecompositionNode.leaf(node) if isinstance(node, int)
        else DecompositionNode.join(*node) for node in flat), len(flat) - 1)
    start = time.monotonic()
    result = improve_decomposition_nni(graph.adjacency, source, seed=seed,
                                      time_budget_seconds=seconds,
                                      target_max_cut_rank=target,
                                      cache_limit=10_000, max_moves=200_000)
    converted = {}
    for i in result.decomposition.postorder():
        node = result.decomposition.nodes[i]
        converted[i] = node.vertex if node.is_leaf else (converted[node.left], converted[node.right])
    return converted[result.decomposition.root], time.monotonic() - start


def run_case(args, name, variant):
    started = time.monotonic()
    path = ROOT / 'results/dense_audit_20261021/inputs' / name / (variant + '.json.gz')
    data = read(path)
    columns = [int(c, 16) for c in data['h']]
    if len(columns) > args.max_columns:
        raise ValueError(f'case has {len(columns)} columns, exceeds --max-columns')
    identifier = name + '__' + variant
    width_root = ROOT / 'results/dense_audit_20261021'
    order_sources = [width_root / 'widths' / (identifier + '.json.gz'),
                     width_root / 'refinements' / (identifier + '.json.gz'),
                     width_root / 'geometry' / (identifier + '.json.gz')]
    existing = [(q, read(q)) for q in order_sources if q.is_file()]
    existing = [(q, d) for q, d in existing if 'order' in d]
    source, old = min(existing, key=lambda item: (item[1]['width'], item[1].get('log2_volume', float('inf'))))
    order = old['order']
    graph = rw.fundamental_graph(columns, order)
    graph_text = rw.graph_to_dimacs(graph.adjacency)
    out = Path(args.output) / identifier
    out.mkdir(parents=True, exist_ok=True)
    (out / 'fundamental.dgf').write_text(graph_text)
    result = dict(name=name, variant=variant, ncols=len(columns), nrows=data['nrows'],
                  nobs=data['nobs'], input_sha256=data['input_sha256'],
                  input_file=str(path.relative_to(ROOT)),
                  input_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  baseline_file=str(source.relative_to(ROOT)), baseline_width=old['width'],
                  baseline_peak_bits=old.get('peak_bits'), order=order,
                  fundamental_basis_columns=list(graph.basis_columns),
                  fundamental_sha256=hashlib.sha256(graph_text.encode()).hexdigest(),
                  candidates=[], failures=[], protocol=dict(
                      seed=args.seed, nni_seconds=args.nni_seconds,
                      nni_target=args.nni_target,
                      gericom_seconds=args.gericom_seconds, worker_count=1,
                      numerical_threads=1, max_columns=args.max_columns,
                      sibling_nni_objective='legacy width / Cartesian join proxy; actual matroid J independently replayed'))
    trees = [('caterpillar', rw.caterpillar_tree(order)), ('balanced', rw.balanced_tree(order))]
    for method, tree in trees:
        result['candidates'].append(candidate(columns, graph, tree, method))
    save(out / 'candidates.json', result)
    if args.nni_seconds:
        for method, initial in trees:
            try:
                tree, seconds = sibling_nni(graph, initial, args.nni_seconds, args.seed, args.nni_target)
                result['candidates'].append(candidate(columns, graph, tree, 'sibling_nni_' + method, seconds))
            except Exception as exc:
                result['failures'].append(dict(method='sibling_nni_' + method, error=repr(exc)))
            save(out / 'candidates.json', result)
    if args.gericom_seconds:
        if not args.dotnet or not args.gericom_dll:
            raise ValueError('Gericom search requires --dotnet and --gericom-dll')
        command = [args.dotnet, args.gericom_dll, '-s', str(args.seed), '-is', str(args.seed),
                   '-tl', str(args.gericom_seconds), str((out / 'fundamental.dgf').resolve())]
        start = time.monotonic()
        try:
            process = subprocess.run(command, text=True, capture_output=True,
                                     timeout=args.gericom_seconds + 15, check=False)
            (out / 'gericom.stdout.txt').write_text(process.stdout)
            (out / 'gericom.stderr.txt').write_text(process.stderr)
            if process.returncode:
                raise RuntimeError(f'Gericom exit {process.returncode}: {process.stderr[-1000:]}')
            parsed = rw.parse_gericom_dot(process.stdout, graph.adjacency)
            result['candidates'].append(candidate(columns, graph, parsed['tree'], 'gericom_annealing',
                                                 time.monotonic() - start,
                                                 edges_replayed=parsed['edges_replayed']))
        except Exception as exc:
            result['failures'].append(dict(method='gericom_annealing', error=repr(exc)))
        save(out / 'candidates.json', result)
    result['seconds'] = time.monotonic() - started
    result['python_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result['best_width'] = min(c['width'] for c in result['candidates'])
    save(out / 'candidates.json', result)
    print(json.dumps(dict(case=identifier, baseline=result['baseline_width'],
                          candidates=[{k: c[k] for k in ('method', 'width', 'max_join_dimension', 'seconds')}
                                      for c in result['candidates']], failures=result['failures'])), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', action='append', required=True, help='name:variant')
    parser.add_argument('--output', default=str(ROOT / 'results/rw_tree_audit_20261021/rw'))
    parser.add_argument('--max-columns', type=int, default=400)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--nni-seconds', type=float, default=0)
    parser.add_argument('--nni-target', type=int)
    parser.add_argument('--gericom-seconds', type=int, default=0)
    parser.add_argument('--dotnet')
    parser.add_argument('--gericom-dll')
    args = parser.parse_args()
    if args.nni_seconds < 0 or args.nni_seconds > 20 or args.gericom_seconds < 0 or args.gericom_seconds > 30:
        parser.error('initial audit budgets: NNI 0..20 s, Gericom 0..30 s')
    for spec in args.case:
        name, variant = spec.rsplit(':', 1)
        run_case(args, name, variant)


if __name__ == '__main__':
    main()
