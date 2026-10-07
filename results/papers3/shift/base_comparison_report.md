## Summary

**The 120 Z loss is already caused by Table III's CNOT order: s=10, b=8, d=8. The 120 X comparison is s=b=d=10; 72 has s=b=d=6 in both bases. No additional loss from dynamics is seen in these comparisons. The 144 attribution remains pending its b searches.**

| instance | certified lower | replay-verified upper | seconds | qubits | detectors | DEM mechanisms | exact sector | symmetries kept/proposed | Table I reference |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| 72b Z | 6 | 6 | 5.4 | 144 | 432 | 16200 | yes | 35/35 | <=6 |
| 72b X | 6 | 6 | 4.5 | 144 | 432 | 16164 | yes | 35/35 | <=6 |
| 120b Z | 8 | 8 | 7.5 | 240 | 720 | 27000 | yes | 59/59 | <=10 |
| 120b X | 10 | 10 | 55.6 | 240 | 720 | 26940 | yes | 59/59 | <=10 |

Six cycles, full noise. Every b cycle has seven CNOT layers, plus reset and measurement. Table I values are reference upper bounds, not separately stated estimates for b; CODES[b][3] is None.

The eight-fault 120d Z witness contains hooks from X checks 0 and 5, caused by X faults after XB2 at tick 5. In b, each spreads through the remaining XB1,XA3,XA2 gates to L(u),R(A3u),R(A2u). Six data singles complete a weight-12 X logical with zero Hz syndrome. The mapped base faults keep X on qubits 120,9,125,4 at tick 5 and 51,56 at tick 6; the tick-7 faults map X221->X101 and X226->X106, after ordinary ZA1. Both undecomposed DEM verification and physical replay give no detectors and flipped observables [0,2]. Keeping the same last-two qubits without mapping fires six detectors. Thus this witness needs the order's hooks, not data/ancilla exchange.

Un-reversing the second column gives the valid seven-layer base, b=b2. Literal unreversal of the first column gives duplicate ZA1 and XA2 gates that cancel, and nondeterministic detectors; b1 preserves this invalid diagnostic. Undoing the added SWAP remnants instead recovers the same valid base from both columns.

Independent Table III recheck (PDF text p.5 and HTML Table 3):

| round | quoted Step label | quoted gate label | CNOT layer | reversed control -> target |
|---|---|---|---:|---|
| 1 | "7" | "CNOT_A1" | 6 | Z(u) -> L(barA1 u) |
| 1 | "8" | "CNOT_A2" | 7 | R(A2 u) -> X(u) |
| 2 | "2" | "CNOT_A2" | 1 | Z(u) -> L(barA2 u) |
| 2 | "3" | "CNOT_A1" | 2 | R(A1 u) -> X(u) |

All four entries match the existing builder. No dynamic gate was changed. Sources: https://arxiv.org/html/2601.09911v1#S2.T3 and https://arxiv.org/pdf/2601.09911v1.

144/170 b were not searched; their two-cycle builder tests passed both bases/models. 144b has 288 qubits/288 detectors, DEM Z/X=8640/8568; 170b has 340 qubits/340 detectors, DEM Z/X=10200/10115. Sector reduction is exact. Circuit symmetries are unmeasured there; 71/84 are candidate counts only.

## Changes

- `circuits/papers/shift120b_r6_X.stim` — six-cycle full-noise base circuit searched.
- `circuits/papers/shift120b_r6_Z.stim` — six-cycle full-noise base circuit searched.
- `circuits/papers/shift72b_r6_X.stim` — six-cycle full-noise base circuit searched.
- `circuits/papers/shift72b_r6_Z.stim` — six-cycle full-noise base circuit searched.
- `logs/papers3/shift/base_builder_checks.log` — actual output of named run/test; initial X timeout retained in its original log.
- `logs/papers3/shift/base_comparison_export.py` — reproducible independent audit or saved-output export.
- `logs/papers3/shift/base_witness_audit.py` — reproducible independent audit or saved-output export.
- `logs/papers3/shift/run_120b_X.log` — actual output of named run/test; initial X timeout retained in its original log.
- `logs/papers3/shift/run_120b_X_extended.log` — actual output of named run/test; initial X timeout retained in its original log.
- `logs/papers3/shift/run_120b_Z.log` — actual output of named run/test; initial X timeout retained in its original log.
- `logs/papers3/shift/run_72b_X.log` — actual output of named run/test; initial X timeout retained in its original log.
- `logs/papers3/shift/run_72b_Z.log` — actual output of named run/test; initial X timeout retained in its original log.
- `logs/papers3/shift/tableiii_rev_audit.py` — reproducible independent audit or saved-output export.
- `papers/new/2601.09911.md` — base definitions, SWAP-remnant distinction, reversed-entry evidence, hook explanation and comparisons.
- `papers/shift.py` — b/b2 valid ordinary Table III base; literal b1 diagnostic; key/schedule handling; old s/d/m gates retained.
- `papers/shift_run.py` — base-only/noise batch options and separate base-run metadata.
- `results/papers3/shift/120b_X.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/120b_X_partial.json` — initial 120b X 9--10 threshold-timeout result archived before extension.
- `results/papers3/shift/120b_Z.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/72b_X.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/72b_Z.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/base_comparison_report.md` — comparison report with complete task-phase changes/commands/outcomes.
- `results/papers3/shift/base_comparison_summary.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/base_extended_run.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/base_runs.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/base_witness_audit.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/builder_checks.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `results/papers3/shift/tableiii_rev_audit.json` — named verification evidence, run metadata or certified bounds with physically replayed witness.
- `tests/test_shift.py` — b/b2 aliases, ordinary frames, valid DEMs and expected b1 nondeterminism for all codes/bases/models.

## Verification

- `OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u tests/test_shift.py > logs/papers3/shift/base_builder_checks.log 2>&1` — exit0, 183.260 s; 64 valid noisy cases, 16 expected b1 failures, aliases and logical maps passed.
- `OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u papers/shift_run.py --base-only --noise full --resume` — exit0; four full-noise base runs; initial 120b X partial result preserved.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72b Z results/papers3/shift/72b_Z.json 6 2 16 30 1 full` — exit0, bounds 6--6.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 72b X results/papers3/shift/72b_X.json 6 2 16 30 1 full` — exit0, bounds 6--6.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120b Z results/papers3/shift/120b_Z.json 6 2 16 30 1 full` — exit0, bounds 8--8.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120b X results/papers3/shift/120b_X.json 6 2 16 30 1 full` — exit0, bounds 9--10.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 120b X results/papers3/shift/120b_X.json 6 2 12 180` — exit0, bounds 10--10, 56.323 s child wall time, 570 s cap.
- `OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python logs/papers3/shift/base_witness_audit.py` — exit0, 10.545 s; mapped eight-fault DEM and physical replay verified.
- `OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python logs/papers3/shift/tableiii_rev_audit.py` — exit0, 9.1 s; four reversed entries, recovered-base identity and all four codes/bases validated.
- `.venv/bin/python logs/papers3/shift/base_comparison_export.py` — exit0; source ASTs, saved exact bounds, sectors, DEM/physical witnesses and passing test metadata validated; report exported.

Root's initial inline ordinary-memory probe exited0: b/b2 deterministic and b1 invalid on 72/120, both bases. Read-only pwd/rg/sed/head/tail/JSON inspections succeeded. The first report-export invocation exited1 on an incorrect replay field name; it was corrected to the audit's detectors/observables schema and rerun successfully. Named-paper HTML/PDF reads succeeded. PDF screenshot rendering failed with cache miss; pdftoppm was unavailable; Swift/Clang rendering failed with SDK/compiler mismatch. Only PDF text/HTML, not a visual PDF render, were cross-checked. No failed render was counted as verification.

## Assumptions and open issues

b uses the ordinary-memory second column as explicitly requested, with the existing lead-chosen lattice and full/noidle fault readings. The base first-column duplicate gates were retained under b1, not silently deleted. The paper's dynamic transcription was audited and retained exactly. Additional server s/d/m numbers are supplied by the lead and were not independently replayed locally. Prior completion_report.md and its export helper describe the preceding task phase; this report records current changes.

Run the following on the lead's server to match the six-cycle comparison. These are unrun commands; 3600 is per threshold and exceeds the local-run allowance.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144b Z results/papers3/shift/144b_Z.json 6 3 12 3600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 144b X results/papers3/shift/144b_X.json 6 3 12 3600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170b Z results/papers3/shift/170b_Z.json 6 3 12 3600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py shift 170b X results/papers3/shift/170b_X.json 6 3 12 3600
```

144 may likewise have order-induced loss, but that conclusion is not yet certified. The first 120b X run timed out at K9 with bounds9--10; its extension exhausted K9 in 37.73 s and certified10. No packages, environments, remote jobs or commits were created. Shared sources and top-level reports were not changed.
