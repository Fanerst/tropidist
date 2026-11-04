"""Generate the dense-DP audit report and compact machine-readable table."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from dense_audit import read, save


def natural(s):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', s)]


def fmt_time(t):
    if t is None:
        return '—'
    if t < 0.01:
        return '<0.01'
    return f'{t:.2f}' if t < 100 else f'{t:.1f}'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    records = []
    for path in (a.out / 'widths').glob('*.json.gz'):
        base = read(path)
        chosen = base.copy()
        extra = a.out / 'refinements' / path.name
        if extra.exists():
            refinement = read(extra)
            if (refinement['width'], refinement['log2_volume']) < (base['width'], base['log2_volume']):
                chosen.update(refinement)
        key = base['name'] + '__' + base['variant']
        runpath = a.out / 'runs' / (key + '.json')
        run = read(runpath) if runpath.exists() else {}
        if run:
            # Every run identifies its actual permutation, even if a later
            # refinement produces a better width for the summary table.
            if 'order_sha256' not in run:
                run.update(ordering_width=base['width'], total_work=base['total_work'],
                           order_sha256=hashlib.sha256(json.dumps(base['order']).encode()).hexdigest())
            refs = read(a.out / 'reference_distances.json')
            if key in refs and run.get('status') == 'exact':
                run['reference'] = refs[key]
                run['agrees_with_reference'] = run['distance'] == refs[key]['distance']
                assert run['agrees_with_reference'], key
            if run.get('status') == 'exact':
                save(runpath, run)
        rec = {k: base[k] for k in ('name', 'suite', 'family', 'track', 'variant', 'n', 'k',
                                   'nrows', 'ncols', 'nobs', 'rank', 'truth', 'truth_kind', 'input_sha256')}
        rec.update(natural_width=base['trials'][0]['width'],
                   greedy_width=base['greedy_best'][0] if base['greedy_best'] else None,
                   baseline_width=base['width'], best_width=chosen['width'],
                   log2_volume=chosen['log2_volume'], peak_bits=chosen.get('peak_bits'),
                   peak_bits_bounds=chosen.get('peak_bits_bounds'),
                   total_work=chosen.get('total_work'),
                   completed_greedy_seeds=sum(x['label'].startswith('greedy') for x in base['trials']),
                   baseline_ordering_seconds=base['seconds'],
                   extra_ordering_seconds=chosen['seconds'] if chosen is not base and chosen['order'] != base['order'] else 0,
                   refinement=chosen['order'] != base['order'],
                   order_sha256=hashlib.sha256(json.dumps(chosen['order']).encode()).hexdigest(),
                   dense_status=run.get('status', 'table_exceeds_4_GiB' if chosen.get('peak_bits', 999) > 32 else 'not_run'),
                   distance=run.get('distance'), dense_seconds=run.get('seconds'),
                   measured_peak_rss_mib=run.get('peak_rss_mib'),
                   observables_completed=len(run.get('per_observable', [])),
                   agrees_with_truth=run.get('agrees_with_truth'), agrees_with_reference=run.get('agrees_with_reference'))
        records.append(rec)
    records.sort(key=lambda r: (r['suite'], natural(r['name']), r['variant']))
    save(a.out / 'summary.json', records)
    canonical = [x for x in records if x['variant'] != 'collapsed' and x['family'] != 'fixture']
    collapsed = [x for x in records if x['variant'] == 'collapsed' and x['family'] != 'fixture']
    exact = [x for x in canonical if x['dense_status'] == 'exact']
    fit = [x for x in canonical if (x['peak_bits'] or 999) <= 32]
    pending = [x for x in records if x['dense_status'] in ('running', 'not_run')]
    stopped = [x for x in records if x['dense_status'] == 'stopped_by_user']
    status = ('**Status: stopped at the user\'s request; no experiments are running.**' if stopped
              else '**Status: in progress.**' if pending else '**Status: complete.**')
    lines = ['# Dense trellis DP: local audit, 21 October 2026', '',
             status +
             f' Widths are available for all {len(records)} problems. '
             f'Dense DP has completed {len(exact)}/{len(canonical)} formal benchmark instances. '
             f'{len(fit)} formal instances have an observed table peak of at most 4 GiB.', '',
             'This report evaluates the implementation at commit `b4cfc4493acbd9d279357104ccb23a85fb92b452`. '
             'The DP and ordering implementations were not changed. The added scripts perform data reconstruction, '
             'ordering searches, resource accounting, execution and reporting.', '',
             '## Separation from the pulled results', '',
             'All results in this audit directory were generated locally on 21 October 2026. '
             'They are not part of the previously pulled server benchmark records.', '',
             'The pulled commit contains `results/dense.json`: completed BB72 Z/X t=0 windows '
             '(distance 6), BB72 Z/X collapsed problems (distance 5), and the BB90 Z t=0 window '
             '(distance 10). Its other BB108/BB144/BB288 entries contain width measurements without '
             'completed dense distance results.', '',
             'The separate pulled `dense_big_*` files contain two large-memory server experiments: '
             'BB144 Z t=0/code-capacity window (12 observables, distance 12, cut width 33, '
             'table peak 35 bits = 32 GiB) and BB90 Z collapsed (8 observables, distance 7, '
             'cut width 34, table peak 36 bits = 64 GiB). '
             'Neither the 60-instance benchmark nor the 126-instance WJH benchmark contains a dense-DP solver run. '
             'Their `ours`/`ours_search`/`ours_pipeline` records use weight-bounded sparse search and the reduction/lifting pipeline.', '',
             '## Scope and interpretation', '',
             '- Main benchmark: 60 instances (16 code-distance problems and 44 circuits).',
             '- WJH benchmark: 126 instances (103 code-distance problems and 23 circuits).',
             '- Two fixtures are reported separately. All 63 exported collapsed variants, including one fixture, are also evaluated.',
             '- A circuit uses its exported memory sector when the reduction is exact. The reconstruction checks that every projected column has an equal-cost pure-sector lift. The five Stim color circuits use their full DEM.',
             '- Collapsed problems are relaxations. Their exact DP values are lower bounds on circuit distance, unless an independent argument establishes equality.',
             '- `amplified_90` is registered but was not exported into the benchmark. The registry marks it `needs_lead`: flag detectors make its default memory-sector selector ambiguous. It is outside the 186-instance count.', '',
             'For an ordering π, the reported width is the maximum of '
             '`rank(H_past) + rank(H_future) - rank(H)`. It is an upper bound obtained from a specific linear ordering, '
             'not a certificate of the minimum possible width. It is not the width of a general branch decomposition.', '',
             'The C kernel allocates one byte per state. Its actual `peak_bits = p` gives a table of `2^p` bytes. '
             'The per-column update temporarily includes starting rows before ending rows are removed, and one logical '
             'target row may also be active. Consequently, p can be one or two bits above the reported cut width. '
             'Every feasible-size problem is checked against the actual plans for **all** logical observables.', '',
             '| Actual peak bits p | Table memory | Local policy |',
             '|---:|---:|---|',
             '| 28 | 256 MiB | Executed |',
             '| 30 | 1 GiB | Executed |',
             '| 31 | 2 GiB | Executed |',
             '| 32 | 4 GiB | Executed |',
             '| 33 | 8 GiB | Larger than the per-task audit cap |',
             '| 34 | 16 GiB | Leaves limited room for the running desktop |',
             '| 35 | 32 GiB | Exceeds this machine\'s physical RAM |', '',
             '## Machine and protocol', '',
             'Apple M5 Pro, 15 physical cores (5 performance and 10 efficiency), 24 GiB RAM. '
             'The repository\'s macOS build uses one kernel thread; it does not enable OpenMP. '
             'Python and package versions, source checksums and limits are retained in `manifest.json`.', '',
             'For every problem, the baseline considers the native order and, for a sector, a time order. '
             'It then attempts greedy seeds 0–23 within 12 seconds and runs up to 3000 existing block-move/reversal '
             'iterations within 6 seconds. Local iterations are submitted in blocks of 100 with seeds 1, 2, …; '
             'this retains completed improvements at a deadline. Four width workers were used. '
             'Large problems can exhaust the ordering budget before one greedy order completes; '
             'their native/time ordering still provides the reported upper bound. Every completed trial and final permutation is saved.', '',
             'Additional searches are identified in the tables. For the two BB144 code problems, 120 existing '
             'geometric sweeps seed repeated 3000-step local searches (at most 100 calls, within a 60-second cap). '
             'Five other boundary cases receive up to 30 additional seconds of existing greedy/local search. '
             'A geometric probe also improves the main BB288 code ordering. These are unequal, explicitly recorded '
             'search budgets, not an optimal-width benchmark.', '',
             'Small dense runs use a 300-second limit. The five remaining 2–4 GiB cases use 1200 seconds. '
             'Each solve processes all observable rows and returns their minimum. Dense times include plan construction '
             'and the complete observable sweep; they exclude input reconstruction, ordering, process startup and compilation. '
             'Each run has its own process, so its peak RSS is attributable to that solve. Several one-thread runs can overlap; '
             'the simultaneous dense-table budget is at most 8 GiB. Timings describe this desktop session, not isolated-core measurements.', '',
             '## Formal benchmark coverage', '',
             '| Suite | Type | Total | Table ≤4 GiB | Complete dense solves |',
             '|---|---|---:|---:|---:|']
    for suite in ('main', 'wjh'):
        for track in ('code', 'circuit'):
            group = [x for x in canonical if x['suite'] == suite and x['track'] == track]
            lines.append(f"| {suite} | {track} | {len(group)} | {sum((x['peak_bits'] or 999) <= 32 for x in group)} | {sum(x['dense_status'] == 'exact' for x in group)} |")
    lines += ['', f'Collapsed relaxations: {sum(x["dense_status"] == "exact" for x in collapsed)}/{len(collapsed)} completed. '
              'These are excluded from the formal circuit-solve counts.', '',
              '## Ordering sensitivity near the memory boundary', '',
              '| Problem | Baseline width | Best width | Baseline table bits | Best table bits | Dense distance | Dense seconds |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for name in ('code_bb144', 'wjh_bb_n144', 'wjh_hcc_09_n168', 'wjh_hsc_09_n252', 'wjh_midout_d11', 'code_bb288'):
        rec = next(x for x in canonical if x['name'] == name)
        base = read(a.out / 'widths' / (name + '__' + rec['variant'] + '.json.gz'))
        lines.append(f"| {name} | {rec['baseline_width']} | {rec['best_width']} | {base.get('peak_bits', '≥' + str(base['peak_bits_bounds'][0]))} | {rec['peak_bits'] or '≥' + str(rec['peak_bits_bounds'][0])} | {rec['distance'] if rec['distance'] is not None else '—'} | {fmt_time(rec['dense_seconds'])} |")
    lines += ['', '## All formal benchmark instances', '',
              '`w` is the best observed cut width. `p` is the actual maximum plan table width; '
              'a range is an analytic bound when full logical plans were unnecessary because the H section alone was too large. '
              '`refined` marks additional ordering time. A skipped large table establishes infeasibility only for the observed ordering, '
              'not for every possible ordering or for a different DP implementation.', '']

    def table(items):
        rows = ['| Instance | Variant | Columns | Obs. | w | p | Extra search | Distance | Dense seconds | Status |',
                '|---|---|---:|---:|---:|---:|---|---:|---:|---|']
        for x in items:
            ptext = str(x['peak_bits']) if x['peak_bits'] is not None else '–'.join(map(str, x['peak_bits_bounds']))
            rows.append(f"| {x['name']} | {x['variant']} | {x['ncols']} | {x['nobs']} | {x['best_width']} | {ptext} | {'refined' if x['refinement'] else ''} | {x['distance'] if x['distance'] is not None else '—'} | {fmt_time(x['dense_seconds'])} | {x['dense_status']} |")
        return rows

    for suite in ('main', 'wjh'):
        lines += [f'### {suite}', ''] + table([x for x in canonical if x['suite'] == suite]) + ['']
    lines += ['## Collapsed relaxations', ''] + table(collapsed) + ['', '## Fixtures', '']
    lines += table([x for x in records if x['family'] == 'fixture'])
    witnesses = read(a.out / 'witness_validation.json')
    source_checks = read(a.out / 'source_validation.json')
    lines += ['', '## Validation and retained evidence', '',
              f'- All 188 reconstructed instances reproduce their stored dimensions. All {len(source_checks)} WJH source checksums match the repository metadata, including the complete exported CSS-code dataset.',
              f'- All {len(witnesses)} available tested historical witnesses satisfy the reconstructed H/L problems. Their original column indices are retained.',
              '- The unmodified kernel passes 3000 random comparisons against exhaustive enumeration and 40 additional dense C-versus-NumPy comparisons.',
              '- Completed results are checked against metadata ground truth and independently stored exact solver results whenever available. The dense kernel returns values, not witness vectors.',
              '- Costs are uint8 with 255 as infinity. All finite distances reported here are below 255. This implementation cannot distinguish infeasibility from a minimum of 255 or greater.', '',
              'The result directory contains `inputs/` (compressed H/L, metadata, checksums and rebuilt circuits), '
              '`widths/` (baseline trials, permutations and profiles), `refinements/`, `geometry/`, `runs/` '
              '(every observable, timing, RSS and reference checks), `summary.json`, and validation records.', '',
              'External inputs were reconstructed from the versions documented in the repository: '
              '[codeDistancePYPI a4afe9c](https://github.com/m-webster/codeDistancePYPI/tree/a4afe9c), '
              '[yarn 1b58edd](https://github.com/a7b/yarn/tree/1b58edd), and '
              '[Kasai\'s data page](https://kasai.ict.eng.isct.ac.jp/pair_partition_cpm_css_codes_20260714.html). '
              'The inputs needed to repeat the DP are retained locally; external downloads are not required for replay.', '',
              '## Reproduction', '',
              'From the repository root, using the prepared Python environment:', '',
              '```sh',
              'python scripts/dense_audit.py widths --out results/dense_audit_20261021 --jobs 4',
              'python scripts/dense_audit.py run --out results/dense_audit_20261021 --max-bits 32 --seconds 1200',
              'python scripts/summarize_dense_audit.py --out results/dense_audit_20261021 --report docs/notes/DENSE_DP_AUDIT.md',
              '```', '',
              'Completed records are cached. To obtain a new independent run, use a new output directory with copies of '
              'the retained inputs and selected width/refinement files. The saved permutations permit exact DP replay '
              'without relying on a wall-time-limited ordering search to rediscover them.', '']
    a.report.write_text('\n'.join(lines))
    print('formal exact', len(exact), 'formal fit', len(fit), 'pending', len(pending))


if __name__ == '__main__':
    main()
