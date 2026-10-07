## Summary

Builder completed under the lead's readings, including m. All required local full-model distances are exact. Current code parameters/distances: [[72,12,6]], [[120,8,12]], [[144,12,12]], [[170,16,10]], exact in both bases.

| instance | noise | lower | verified upper | seconds | DEM mechanisms | symmetries kept/proposed | paper |
|---|---|---:|---:|---:|---:|---|---|
| 72s Z | full | 6 | 6 | 5.5 | 16164 | 35/35 | <= 6 |
| 72s X | full | 6 | 6 | 6.2 | 16200 | 35/35 | <= 6 |
| 72d Z | full | 6 | 6 | 13.2 | 16200 | 35/35 | <= 6 |
| 72d X | full | 6 | 6 | 14.6 | 16164 | 35/35 | <= 6 |
| 72m Z | full | 6 | 6 | 8.4 | 16164 | 35/35 | <= 6 |
| 72m X | full | 6 | 6 | 10.2 | 16200 | 35/35 | <= 6 |
| 120s Z | full | 10 | 10 | 45.3 | 26940 | 59/59 | <= 10 |
| 120d Z | full | 8 | 8 | 63.5 | 27000 | 59/59 | <= 10 |
| 72s Z | noidle | 6 | 6 | 11.1 | 16164 | 35/35 | <= 6 |
| 72s X | noidle | 6 | 6 | 12.7 | 16200 | 35/35 | <= 6 |
| 72d Z | noidle | 6 | 6 | 28.1 | 16200 | 35/35 | <= 6 |
| 72d X | noidle | 6 | 6 | 31.3 | 16164 | 35/35 | <= 6 |
| 72m Z | noidle | 6 | 6 | 19.8 | 16164 | 35/35 | <= 6 |
| 72m X | noidle | 6 | 6 | 20.3 | 16200 | 35/35 | <= 6 |
| 120s Z | noidle | 9 | 10 | 66.4 | 26940 | 59/59 | <= 10 |
| 120d Z | noidle | 8 | 8 | 77.8 | 27000 | 59/59 | <= 10 |

All 16 sectors are exact; all upper bounds passed DEM and physical replay. 72: 144 qubits/432 detectors, 35/35 symmetries; 120: 240 qubits/720 detectors, 59/59 symmetries. Cycle CNOT depths: s=7, d=8/7 repeated, m=7 with one 8/7 pair. Final builder test: 219.273 s. Circuit batch: 441.077 s.

| instance | rebuilt n,k | test cycles | physical qubits | CNOT layers per cycle | detectors | DEM Z / X | sector exact | circuit symmetries |
|---|---|---:|---:|---|---:|---|---|---|
| 72s | 72,12 | 2 | 144 | [7, 7] | 144 | 4284 / 4320 | yes | not searched (35 candidates) |
| 72d | 72,12 | 4 | 144 | [8, 7, 8, 7] | 288 | 10296 / 10260 | yes | not searched (35 candidates) |
| 72m | 72,12 | 4 | 144 | [7, 8, 7, 7] | 288 | 10260 / 10296 | yes | not searched (35 candidates) |
| 120s | 120,8 | 2 | 240 | [7, 7] | 240 | 7140 / 7200 | yes | not searched (59 candidates) |
| 120d | 120,8 | 4 | 240 | [8, 7, 8, 7] | 480 | 17160 / 17100 | yes | not searched (59 candidates) |
| 120m | 120,8 | 4 | 240 | [7, 8, 7, 7] | 480 | 17100 / 17160 | yes | not searched (59 candidates) |
| 144s | 144,12 | 2 | 288 | [7, 7] | 288 | 8568 / 8640 | yes | not searched (71 candidates) |
| 144d | 144,12 | 4 | 288 | [8, 7, 8, 7] | 576 | 20592 / 20520 | yes | not searched (71 candidates) |
| 144m | 144,12 | 4 | 288 | [7, 8, 7, 7] | 576 | 20520 / 20592 | yes | not searched (71 candidates) |
| 170s | 170,16 | 2 | 340 | [7, 7] | 340 | 10115 / 10200 | yes | not searched (84 candidates) |
| 170d | 170,16 | 4 | 340 | [8, 7, 8, 7] | 680 | 24310 / 24225 | yes | not searched (84 candidates) |
| 170m | 170,16 | 4 | 340 | [7, 8, 7, 7] | 680 | 24225 / 24310 | yes | not searched (84 candidates) |

## Changes

- `circuits/papers/shift120d_r6_Z.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift120d_r6_Z_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift120s_r6_Z.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift120s_r6_Z_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72d_r6_X.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72d_r6_X_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72d_r6_Z.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72d_r6_Z_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72m_r6_X.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72m_r6_X_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72m_r6_Z.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72m_r6_Z_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72s_r6_X.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72s_r6_X_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72s_r6_Z.stim` — six-cycle noisy circuit used by the named saved search.
- `circuits/papers/shift72s_r6_Z_noidle.stim` — six-cycle noisy circuit used by the named saved search.
- `logs/papers3/shift/120s_X.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/120s_Z.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/72d_X.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/72d_Z.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/72s_X.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/72s_Z.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/code_distance.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/code_distance_driver.py` — reproducible bounded verification/export helper; literal-named helper archives original audit.
- `logs/papers3/shift/code_distance_driver_literal_72_144.py` — reproducible bounded verification/export helper; literal-named helper archives original audit.
- `logs/papers3/shift/code_distance_literal_72_144.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/completion_export.py` — reproducible bounded verification/export helper; literal-named helper archives original audit.
- `logs/papers3/shift/fault_model_check.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/fault_model_check.py` — reproducible bounded verification/export helper; literal-named helper archives original audit.
- `logs/papers3/shift/run_120d_Z.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_120d_Z_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_120s_Z.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_120s_Z_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72d_X.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72d_X_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72d_Z.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72d_Z_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72m_X.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72m_X_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72m_Z.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72m_Z_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72s_X.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72s_X_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `logs/papers3/shift/run_72s_Z_noidle.log` — actual stdout/stderr from the named run/audit (historical blocked logs retained).
- `papers/new/2601.09911.md` — source locators, evidence, lead-chosen readings, historical audit and completed results/server commands.
- `papers/shift.py` — nominal/literal code definitions, s/d/m schedules, moving detectors/observables, full/noidle faults and translation candidates.
- `papers/shift_run.py` — bounded local unchanged-pipeline batch and resumable results.
- `results/papers3/shift/120d_Z.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/120d_Z_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/120s_Z.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/120s_Z_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72d_X.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72d_X_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72d_Z.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72d_Z_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72m_X.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72m_X_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72m_Z.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72m_Z_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72s_X.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72s_X_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72s_Z.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/72s_Z_noidle.json` — named circuit search bounds, exact-sector statistics and physically verified witness.
- `results/papers3/shift/blocked_runs.json` — historical unresolved-source audit/failed-run evidence, preserved.
- `results/papers3/shift/builder_checks.json` — passing 48-case final builder check and logical-action evidence.
- `results/papers3/shift/builder_checks_r6_partial.json` — explicit incomplete six-cycle builder sweep, preserved separately from passing final checks.
- `results/papers3/shift/code_distance.json` — eight exact nominal code-distance searches and verified witnesses.
- `results/papers3/shift/code_distance_literal_72_144.json` — archived original exact 72/144 code-distance check.
- `results/papers3/shift/completion_report.md` — integration report with file manifest, actual commands, statistics, bounds and open issues.
- `results/papers3/shift/completion_summary.json` — validated machine-readable current code distances, circuit bounds, test statistics and source hashes.
- `results/papers3/shift/fault_model_checks.json` — honest 13/24-case independent fault-audit record with interruption/provenance limitations.
- `results/papers3/shift/local_runs.json` — actual local batch command, exits, elapsed times and bounds.
- `results/papers3/shift/source_audit.json` — historical unresolved-source audit/failed-run evidence, preserved.
- `tests/test_shift.py` — plain-script nominal/literal, schedule, detector, DEM, sector and logical-action checks.

## Verification

- `OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u tests/test_shift.py` — exit0, 219.273 s, 48 noisy DEMs and all logical-action checks passed.
- `OMP_NUM_THREADS=2 .venv/bin/python -u logs/papers3/shift/code_distance_driver.py` — exit0, eight exact code distances, 5.894 s.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/shift_run.py --resume` — exit0, required full plus noidle comparisons; batch 441.077 s.
- `OMP_NUM_THREADS=2 .venv/bin/python logs/papers3/shift/fault_model_check.py > logs/papers3/shift/fault_model_check.log 2>&1` — interrupted exit130 after 13/24 independent checks passed; intentionally partial.
- `.venv/bin/python logs/papers3/shift/completion_export.py` — exit0; source ASTs, saved sector flags, all 16 DEM/replay witnesses, all 48 builder cases and output circuit existence validated; report exported.

Individual run_parallel commands (72s Z full was executed before the resumed batch):

- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72s Z results/papers3/shift/72s_Z.json 6 2 16 30 1 full` — completed earlier; resumed batch skipped it.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72s X results/papers3/shift/72s_X.json 6 2 16 30 1 full` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72d Z results/papers3/shift/72d_Z.json 6 2 16 30 1 full` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72d X results/papers3/shift/72d_X.json 6 2 16 30 1 full` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72m Z results/papers3/shift/72m_Z.json 6 2 16 30 1 full` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72m X results/papers3/shift/72m_X.json 6 2 16 30 1 full` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120s Z results/papers3/shift/120s_Z.json 6 2 16 30 1 full` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120d Z results/papers3/shift/120d_Z.json 6 2 16 30 1 full` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72s Z results/papers3/shift/72s_Z_noidle.json 6 2 16 30 1 noidle` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72s X results/papers3/shift/72s_X_noidle.json 6 2 16 30 1 noidle` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72d Z results/papers3/shift/72d_Z_noidle.json 6 2 16 30 1 noidle` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72d X results/papers3/shift/72d_X_noidle.json 6 2 16 30 1 noidle` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72m Z results/papers3/shift/72m_Z_noidle.json 6 2 16 30 1 noidle` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72m X results/papers3/shift/72m_X_noidle.json 6 2 16 30 1 noidle` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120s Z results/papers3/shift/120s_Z_noidle.json 6 2 16 30 1 noidle` — exit0.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120d Z results/papers3/shift/120d_Z_noidle.json 6 2 16 30 1 noidle` — exit0.

Failures and incomplete checks retained honestly: initial audited builder/pipeline runs failed on unresolved paper definitions; blocked_runs.json lists all six exact commands (exit1, no bounds). Historical tests hit Python3.9's missing int.bit_count; fixed. During completion an indentation error was fixed, and two redundant six-cycle symmetry-heavy builder sweeps were intentionally interrupted (exit130). The final short transition sweep passed. Two final JSON inspection snippets exited1 on incorrect field names (cases/detectors), then a corrected validation exited0. git status failed128 because this directory is not a Git repository; ps and direct process signalling were sandbox-denied. No numerical check is inferred from those failures. Read-only discovery used pwd/rg/sed/head/tail/cat/ls and arXiv HTML/PDF reads. No packages installed, no jobs submitted remotely.

## Assumptions and open issues

The five lead choices are recorded in every CODES entry and extraction notes next to source evidence: cited twisted lattices; literal inverse shift; layer/order-preserving CNOT fault support with noisy endpoints; printed repeated/middle-pair schedules; candidate lattice symmetries. Literal 120lit/170lit have k=0 and cannot build circuits. The noise-support equivalence is conditioned on preserving entangling-gate layers/order and the chosen endpoints; the paper's ideal endpoints and benchmark probabilities are not claimed reproduced. No counterexample was found within that conditioned reading.

144/170 circuit-distance searches and the other 120 variants were not run locally. Their noisy DEM/sector/logical checks passed at the transition-test cycle counts; six/ten/twelve-cycle bounds and surviving circuit symmetries remain for the lead. Suggested server commands (600 seconds is per threshold, not a local wall cap):

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144s Z results/papers3/shift/144s_Z.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144s X results/papers3/shift/144s_X.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144d Z results/papers3/shift/144d_Z.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144d X results/papers3/shift/144d_X.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144m Z results/papers3/shift/144m_Z.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144m X results/papers3/shift/144m_X.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170s Z results/papers3/shift/170s_Z.json 10 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170s X results/papers3/shift/170s_X.json 10 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170d Z results/papers3/shift/170d_Z.json 10 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170d X results/papers3/shift/170d_X.json 10 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170m Z results/papers3/shift/170m_Z.json 10 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170m X results/papers3/shift/170m_X.json 10 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120s X results/papers3/shift/120s_X.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120d X results/papers3/shift/120d_X.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120m Z results/papers3/shift/120m_Z.json 12 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120m X results/papers3/shift/120m_X.json 12 2 16 600
```

For noidle, append `1 noidle` and use an output filename ending `_noidle.json`. 120s Z noidle is a saved 9--10 pipeline bound; do not silently replace it with a claimed completed exact search. Full/noidle support comparisons are documented separately. No remote jobs, commits, pushes, stashes, branch switches, package installations, or shared-source/report edits were performed.
