## Summary

**72: 36/36 valid static numberings; 12/36 valid literal dynamic numberings. Every valid circuit has exact distance 6 in both bases (paper reference <=6).**

All 96 pipeline results have exact CSS-sector reduction, one native thread, certified equal bounds and DEM/physical-replay witnesses. The valid dynamic assignments keep printed monomial 1 as A1: A=123 or132, with all six B permutations. Shifts: {'x^-1': 6, 'x y^3': 6}. The independent logical action enumeration finds no valid 72 numbering implementing x.

All experiments have 144 qubits, 432 detectors and 12 observables at six cycles. s uses seven CNOT layers/cycle; d repeats eight/seven. The sweep took 277.3 s; maximum worker time 38.60 s, maximum RSS 175.59 MiB, two concurrent workers.

| circuit/basis | numberings | exact distances | DEM mechanisms | symmetries kept/proposed | pipeline seconds total/range |
|---|---:|---|---|---|---|
| s_Z | 36 | {'6': 36} | [16164] | [(35, 35)] | 121.4 / [1.7, 6.6] |
| s_X | 36 | {'6': 36} | [16200] | [(35, 35)] | 132.2 / [1.9, 6.9] |
| d_Z | 12 | {'6': 12} | [16200] | [(35, 35)] | 89.1 / [3.8, 11.0] |
| d_X | 12 | {'6': 12} | [16164] | [(35, 35)] | 106.0 / [4.0, 12.4] |

| A assignment | B assignment | valid s | s Z/X | valid d | shift d | d Z/X |
|---|---|---|---|---|---|---|
| 123 | 123 | True | 6/6 | True | x^-1 | 6/6 |
| 123 | 132 | True | 6/6 | True | x^-1 | 6/6 |
| 123 | 213 | True | 6/6 | True | x^-1 | 6/6 |
| 123 | 231 | True | 6/6 | True | x^-1 | 6/6 |
| 123 | 312 | True | 6/6 | True | x^-1 | 6/6 |
| 123 | 321 | True | 6/6 | True | x^-1 | 6/6 |
| 132 | 123 | True | 6/6 | True | x y^3 | 6/6 |
| 132 | 132 | True | 6/6 | True | x y^3 | 6/6 |
| 132 | 213 | True | 6/6 | True | x y^3 | 6/6 |
| 132 | 231 | True | 6/6 | True | x y^3 | 6/6 |
| 132 | 312 | True | 6/6 | True | x y^3 | 6/6 |
| 132 | 321 | True | 6/6 | True | x y^3 | 6/6 |
| 213 | 123 | True | 6/6 | False | none | — |
| 213 | 132 | True | 6/6 | False | none | — |
| 213 | 213 | True | 6/6 | False | none | — |
| 213 | 231 | True | 6/6 | False | none | — |
| 213 | 312 | True | 6/6 | False | none | — |
| 213 | 321 | True | 6/6 | False | none | — |
| 231 | 123 | True | 6/6 | False | none | — |
| 231 | 132 | True | 6/6 | False | none | — |
| 231 | 213 | True | 6/6 | False | none | — |
| 231 | 231 | True | 6/6 | False | none | — |
| 231 | 312 | True | 6/6 | False | none | — |
| 231 | 321 | True | 6/6 | False | none | — |
| 312 | 123 | True | 6/6 | False | none | — |
| 312 | 132 | True | 6/6 | False | none | — |
| 312 | 213 | True | 6/6 | False | none | — |
| 312 | 231 | True | 6/6 | False | none | — |
| 312 | 312 | True | 6/6 | False | none | — |
| 312 | 321 | True | 6/6 | False | none | — |
| 321 | 123 | True | 6/6 | False | none | — |
| 321 | 132 | True | 6/6 | False | none | — |
| 321 | 213 | True | 6/6 | False | none | — |
| 321 | 231 | True | 6/6 | False | none | — |
| 321 | 312 | True | 6/6 | False | none | — |
| 321 | 321 | True | 6/6 | False | none | — |

## Changes

- `circuits/papers/shift_num72_a123_b123_w8947772d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b123_w8947772d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b123_w8947772s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b123_w8947772s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b132_w8947872d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b132_w8947872d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b132_w8947872s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b132_w8947872s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b213_w8957772d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b213_w8957772d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b213_w8957772s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b213_w8957772s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b231_w8957872d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b231_w8957872d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b231_w8957872s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b231_w8957872s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b312_w8960972d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b312_w8960972d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b312_w8960972s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b312_w8960972s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b321_w8961372d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b321_w8961372d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b321_w8961372s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a123_b321_w8961372s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b123_w8971272d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b123_w8971272d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b123_w8971272s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b123_w8971272s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b132_w8972172d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b132_w8972172d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b132_w8972172s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b132_w8972172s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b213_w8975872d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b213_w8975872d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b213_w8975872s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b213_w8975872s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b231_w8975972d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b231_w8975972d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b231_w8975972s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b231_w8975972s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b312_w8978972d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b312_w8978972d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b312_w8978972s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b312_w8978972s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b321_w8979672d_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b321_w8979672d_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b321_w8979672s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a132_b321_w8979672s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b123_w8983172s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b123_w8983172s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b132_w8983372s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b132_w8983372s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b213_w8984072s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b213_w8984072s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b231_w8985272s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b231_w8985272s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b312_w8985972s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b312_w8985972s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b321_w8986572s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a213_b321_w8986572s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b123_w8987672s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b123_w8987672s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b132_w8987772s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b132_w8987772s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b213_w8989072s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b213_w8989072s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b231_w8989272s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b231_w8989272s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b312_w8989572s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b312_w8989572s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b321_w8989672s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a231_b321_w8989672s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b123_w8991172s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b123_w8991172s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b132_w8991572s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b132_w8991572s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b213_w8993072s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b213_w8993072s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b231_w8993272s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b231_w8993272s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b312_w8993872s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b312_w8993872s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b321_w8994072s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a312_b321_w8994072s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b123_w8994972s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b123_w8994972s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b132_w8995272s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b132_w8995272s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b213_w8995972s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b213_w8995972s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b231_w8996672s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b231_w8996672s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b312_w8997272s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b312_w8997272s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b321_w8997372s_r6_X.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `circuits/papers/shift_num72_a321_b321_w8997372s_r6_Z.stim` — named six-cycle full-noise numbering circuit used by the saved pipeline result.
- `logs/papers3/shift/numbering_algebra_audit.py` — reproducible independent algebra or saved-result verification/export helper.
- `logs/papers3/shift/numbering_builder_checks.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `logs/papers3/shift/numberings_72.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `logs/papers3/shift/numberings_export.py` — reproducible independent algebra or saved-result verification/export helper.
- `papers/new/2601.09911.md` — numbering semantics, formulas, literal-bar qualification, audit evidence and local/server results.
- `papers/shift.py` — optional monomial numbering, literal barred entry and general measurement/detector/final frames; defaults unchanged.
- `papers/shift_numberings.py` — 36 fresh one-thread workers, unique modules, validation/logical action, both-basis exact searches, checkpoints and limits.
- `results/papers3/shift/builder_checks.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numbering_algebra_audit.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B123/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B123/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B123/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B123/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B123/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B123/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B123/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B123/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B123/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A123_B132/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B132/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B132/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B132/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B132/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B132/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B132/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B132/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B132/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A123_B213/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B213/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B213/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B213/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B213/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B213/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B213/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B213/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B213/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A123_B231/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B231/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B231/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B231/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B231/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B231/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B231/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B231/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B231/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A123_B312/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B312/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B312/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B312/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B312/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B312/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B312/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B312/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B312/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A123_B321/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B321/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B321/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B321/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B321/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B321/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B321/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A123_B321/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A123_B321/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A132_B123/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B123/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B123/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B123/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B123/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B123/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B123/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B123/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B123/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A132_B132/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B132/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B132/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B132/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B132/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B132/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B132/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B132/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B132/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A132_B213/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B213/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B213/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B213/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B213/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B213/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B213/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B213/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B213/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A132_B231/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B231/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B231/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B231/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B231/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B231/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B231/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B231/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B231/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A132_B312/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B312/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B312/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B312/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B312/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B312/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B312/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B312/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B312/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A132_B321/d_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B321/d_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B321/d_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B321/d_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B321/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B321/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B321/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A132_B321/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A132_B321/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A213_B123/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B123/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B123/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B123/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B123/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A213_B132/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B132/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B132/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B132/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B132/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A213_B213/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B213/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B213/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B213/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B213/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A213_B231/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B231/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B231/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B231/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B231/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A213_B312/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B312/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B312/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B312/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B312/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A213_B321/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B321/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B321/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A213_B321/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A213_B321/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A231_B123/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B123/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B123/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B123/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B123/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A231_B132/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B132/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B132/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B132/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B132/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A231_B213/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B213/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B213/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B213/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B213/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A231_B231/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B231/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B231/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B231/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B231/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A231_B312/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B312/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B312/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B312/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B312/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A231_B321/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B321/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B321/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A231_B321/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A231_B321/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A312_B123/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B123/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B123/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B123/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B123/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A312_B132/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B132/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B132/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B132/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B132/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A312_B213/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B213/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B213/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B213/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B213/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A312_B231/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B231/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B231/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B231/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B231/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A312_B312/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B312/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B312/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B312/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B312/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A312_B321/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B321/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B321/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A312_B321/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A312_B321/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A321_B123/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B123/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B123/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B123/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B123/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A321_B132/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B132/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B132/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B132/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B132/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A321_B213/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B213/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B213/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B213/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B213/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A321_B231/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B231/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B231/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B231/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B231/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A321_B312/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B312/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B312/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B312/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B312/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_72/A321_B321/s_X.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B321/s_X.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B321/s_Z.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `results/papers3/shift/numberings_72/A321_B321/s_Z.log` — actual stdout/stderr from the named test, sweep or per-basis search.
- `results/papers3/shift/numberings_72/A321_B321/worker.json` — numbering validity, exact logical action, certified per-basis distances, process/RSS/time record.
- `results/papers3/shift/numberings_report.md` — complete task-phase report, per-numbering table, file manifest and commands.
- `results/papers3/shift/numberings_verification.json` — named certified search/verification data; witnesses checked in DEM and physical replay where applicable.
- `tests/test_shift.py` — numbering validation, default equivalence and all 36 schedule/action checks on 72.

## Verification

- `OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u papers/shift_numberings.py 72 2 6 30 > logs/papers3/shift/numberings_72.log 2>&1` — exit0, complete36/36; 96 exact basis searches; 277.3 s.
- `OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u tests/test_shift.py > logs/papers3/shift/numbering_builder_checks.log 2>&1` — exit0, 79.323 s; existing checks plus all36 numbering validity/logical tests passed.
- `OMP_NUM_THREADS=1 .venv/bin/python -u logs/papers3/shift/numbering_algebra_audit.py` — exit0, 4.187 s; all144 code/numbering assignments independently checked in both bases, peakRSS34.67MiB.
- `.venv/bin/python logs/papers3/shift/numberings_export.py` — exit0; source ASTs/hashes, all96 equal-bound results, saved circuits, native threads, sector flags, DEM/replay witnesses and resource records validated.

Initial inline default-equivalence check exited0: all20 previously saved default circuits unchanged. Inline helper check for A132/B123 exited0 and confirmed x*y^3, all12 logical generators/basis and unique matching translation(1,3). Read-only rg/sed/tail/JSON checks succeeded, except an early rg probe while the new driver file was still being created (exit2, missing file). No failed distance commands or timed-out numbering workers occurred. Individual run_parallel invocations/results are preserved in each numbering directory. No existing/shared search module was edited.

## Assumptions and open issues

The default remains printed order. numbering=(pa,pb) maps table labels to 1-based printed positions. Check matrices do not change. Table III's first-cycle XA1 uses barA1 literally; it was previously indistinguishable from A1 because A1=1. For other A1 assignments it makes the first extracted X polynomial barA1+A2+A3, and the remaining24 dynamic assignments are invalid. This reading was retained rather than silently unbarring the gate. The measured valid pair shift is A1/A2; labels/readout follow that frame.

72's distances do not discriminate among the valid numberings. No120/144/170 numbering-distance sweep was run locally. An independent GF(2) validity/action audit on all four codes passed (36 static/12 dynamic each); distance recovery for the larger codes awaits the lead's server runs. Prior server b=d values were supplied by the lead and not independently rerun here. No paper reread, network access, package/environment installation, remote job or commit occurred during this task phase.

Server commands (two workers, six cycles, k_coll=2, kmax=12, full noise; disable the local worker/sweep wall caps explicitly):

```sh
SHIFT_NUMBERINGS_WORKER_SECONDS=0 SHIFT_NUMBERINGS_TOTAL_SECONDS=0 OMP_NUM_THREADS=1 .venv/bin/python -u papers/shift_numberings.py 120 2 6 3600
SHIFT_NUMBERINGS_WORKER_SECONDS=0 SHIFT_NUMBERINGS_TOTAL_SECONDS=0 OMP_NUM_THREADS=1 .venv/bin/python -u papers/shift_numberings.py 144 2 6 3600
SHIFT_NUMBERINGS_WORKER_SECONDS=0 SHIFT_NUMBERINGS_TOTAL_SECONDS=0 OMP_NUM_THREADS=1 .venv/bin/python -u papers/shift_numberings.py 170 2 6 3600
```

Outputs are results/papers3/shift/numberings_120.json, numberings_144.json and numberings_170.json. Exact finished basis results resume; partial bounds are retained as bounds rather than exact distances.
