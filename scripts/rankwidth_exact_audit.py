"""Cross-check small saved QEC instances with upstream rw 0.10 and Python DP."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.rankwidth_audit import read, save
from cdist import rankwidth as rw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rw-driver', required=True)
    parser.add_argument('--output', default=str(ROOT / 'results/rw_tree_audit_20261021/rw/exact.json'))
    args = parser.parse_args()
    executable = Path(args.rw_driver).resolve()
    result = dict(method='independent Python direct subset DP and upstream rw 0.10',
                  binary_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                  per_run_timeout_seconds=20, max_vertices=18, numerical_threads=1,
                  cases=[], structural_examples=[])
    files = sorted((ROOT / 'results/dense_audit_20261021/inputs').rglob('*.json.gz'))
    for path in files:
        data = read(path)
        if data['ncols'] > 18:
            continue
        h, l = [[int(c, 16) for c in data[key]] for key in ('h', 'l')]
        # Every logical row is small enough here; independence is not assumed.
        for observable in [None] + list(range(data['nobs'])):
            columns = h if observable is None else [c | (((v >> observable) & 1) << data['nrows'])
                                                   for c, v in zip(h, l)]
            graph = rw.fundamental_graph(columns)
            text = str(len(h)) + '\n' + '\n'.join(map(str, graph.adjacency)) + '\n'
            start = time.monotonic()
            process = subprocess.run([str(executable)], input=text, text=True, capture_output=True,
                                     timeout=20, check=True)
            external_seconds = time.monotonic() - start
            external = json.loads(process.stdout)
            external_profile = rw.tree_profile(columns, external['tree'])
            if external_profile['width'] != external['width']:
                raise RuntimeError('external exact witness failed independent replay')
            direct = rw.exact_rankwidth(graph.adjacency, max_n=18, time_limit=20)
            if direct['width'] != external['width']:
                raise RuntimeError('independent exact algorithms disagree')
            flat, _ = rw.flatten_tree(direct['tree'], len(h))
            external_flat, _ = rw.flatten_tree(external['tree'], len(h))
            result['cases'].append(dict(name=data['name'], variant=data['variant'],
                                        input_sha256=data['input_sha256'], ncols=len(h),
                                        logical_row=observable, status='exact_crosschecked',
                                        width=direct['width'], nodes=flat, external_nodes=external_flat,
                                        python_seconds=direct['seconds'], external_seconds=external_seconds,
                                        split_evaluations=direct['split_evaluations'],
                                        preflight=direct['preflight']))
            save(args.output, result)
        print(json.dumps(dict(name=data['name'], variant=data['variant'], ncols=len(h),
                              widths=[r['width'] for r in result['cases']
                                      if (r['name'],r['variant'])==(data['name'],data['variant'])])), flush=True)
    columns = [1 << (i // 2) for i in range(320)]
    graph = rw.fundamental_graph(columns)
    exact = rw.exact_rankwidth_by_components(graph.adjacency)
    flat, _ = rw.flatten_tree(exact['tree'], len(columns))
    result['structural_examples'].append(dict(name='160_independent_parallel_pairs',
                                             ncols=320, width=exact['width'],
                                             status=exact['status'], nodes=flat,
                                             max_component_vertices=exact['max_component_vertices'],
                                             components=exact['components'],
                                             seconds=exact['seconds'],
                                             note='Synthetic validation, not a benchmark QEC certificate'))
    result['large_exact_preflights'] = [rw.exact_preflight(n) for n in (18, 20, 24, 28, 32, 33, 40, 72)]
    save(args.output, result)


if __name__ == '__main__':
    main()
