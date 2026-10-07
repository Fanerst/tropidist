## Summary

Rebuilt the printed nonuniform three-colour gross-code schedule `lr11` without
fetching deposited circuits or author code. Both six-round memory experiments
have certified exact circuit distance 11: all lower weights exhausted, and a
weight-11 fault set checked in the undecomposed DEM and physically replayed.
Separate effective-problem searches independently certified 11 in both bases.
This agrees with the paper's conjecture in Appendix H.2 / Figure 12.

The gross code rebuilt as [[144,12]], with rank(Hx)=rank(Hz)=66. Exact
code-capacity search (k_table=3, covering bound, 71 surviving translations)
certified distance 12 in both bases; final searches took Z 0.577 s and X 0.459 s.

| Search | Basis | Certified lower bound | Verified upper bound | Seconds | Paper | Peak RSS MiB |
| --- | --- | --- | --- | --- | --- | --- |
| lr11 | Z | 11 | 11 | 69.400 | 11 (conjecture) | 184.8 |
| lr11 | X | 11 | 11 | 59.000 | 11 (conjecture) | 189.0 |
| effective | Z | 11 | 11 | 162.823 | 11 (conjecture) | 198.2 |
| effective | X | 11 | 11 | 157.438 | 11 (conjecture) | 209.8 |

Times above are each worker's recorded complete runtime; monitored wall times
were 71.421/60.373 s for run_parallel Z/X, and 164.988/159.042 s for effective
Z/X. No run exceeded ten minutes; no process reached 2 GiB. OMP_NUM_THREADS=2
was set; this Darwin build reports one search-kernel thread. No remote job ran.

## Changes

- `papers/lrgross.py` — Printed Figure 12 builder, matrices, per-check cyclic orders, symmetries and effective/DEM comparison.
- `papers/lrgross_run.py` — Bounded local pipeline/effective runners, RSS/wall monitoring, and physical witness verification.
- `papers/new/2603.05481.md` — Exact paper extraction, figure-to-BB relabelling, schedule numbers, locators and assumptions.
- `tests/test_lrgross.py` — Plain exact-code/builder/DEM/symmetry/effective-column checks.
- `results/papers3/lrgross/builder_checks.json` — Passing builder and code-distance evidence.
- `results/papers3/lrgross/effective_X.json` — Exact distance certificate data and replayed witness.
- `results/papers3/lrgross/effective_X_execution.json` — Execution status, elapsed time and peak RSS.
- `results/papers3/lrgross/effective_Z.json` — Exact distance certificate data and replayed witness.
- `results/papers3/lrgross/effective_Z_execution.json` — Execution status, elapsed time and peak RSS.
- `results/papers3/lrgross/lr11_X.json` — Exact distance certificate data and replayed witness.
- `results/papers3/lrgross/lr11_X_execution.json` — Execution status, elapsed time and peak RSS.
- `results/papers3/lrgross/lr11_Z.json` — Exact distance certificate data and replayed witness.
- `results/papers3/lrgross/lr11_Z_execution.json` — Execution status, elapsed time and peak RSS.
- `logs/papers3/lrgross/effective_X.log` — Search stdout and physical-replay outcome.
- `logs/papers3/lrgross/effective_Z.log` — Search stdout and physical-replay outcome.
- `logs/papers3/lrgross/lr11_X.log` — Search stdout and physical-replay outcome.
- `logs/papers3/lrgross/lr11_Z.log` — Search stdout and physical-replay outcome.
- `circuits/papers/lrgrosslr11_r6_X.stim` — Six-round Stim memory circuit used by the recorded search/replay.
- `circuits/papers/lrgrosslr11_r6_X_effective.stim` — Six-round Stim memory circuit used by the recorded search/replay.
- `circuits/papers/lrgrosslr11_r6_Z.stim` — Six-round Stim memory circuit used by the recorded search/replay.
- `circuits/papers/lrgrosslr11_r6_Z_effective.stim` — Six-round Stim memory circuit used by the recorded search/replay.
- `results/papers3/lrgross/report.md` — This integration report and verification history.

## Verification

Final `.venv/bin/python tests/test_lrgross.py` exited 0 in 158.077 s.
It checks all physical extraction supports, uniqueness of ideal-operation
qubits within layers, frozen printed gate orders, an eight-step bulk repeat,
noiseless deterministic detectors/observables, full/noidle noise channels,
undecomposed DEMs, exact CSS sector reductions, detector coordinate sets,
all logical observables, translations, and effective-column equality.

| Basis | Rounds | Noise | Qubits | Ideal/CNOT layers including boundaries | Detectors | DEM mechanisms | Sector rows x columns | Sector | Symmetries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Z | 3 | full | 288 | 31 / 27 | 432 | 13776 | 288 x 2304 | exact | 23/23 |
| Z | 3 | noidle | 288 | 31 / 27 | 432 | 13776 | 288 x 2304 | exact | 23/23 |
| Z | 6 | full | 288 | 55 / 51 | 864 | 31488 | 504 x 4464 | exact | 23/23 |
| Z | 6 | noidle | 288 | 55 / 51 | 864 | 31488 | 504 x 4464 | exact | 23/23 |
| X | 3 | full | 288 | 31 / 27 | 432 | 13776 | 288 x 2304 | exact | 23/23 |
| X | 3 | noidle | 288 | 31 / 27 | 432 | 13776 | 288 x 2304 | exact | 23/23 |
| X | 6 | full | 288 | 55 / 51 | 864 | 31488 | 504 x 4464 | exact | 23/23 |
| X | 6 | noidle | 288 | 55 / 51 | 864 | 31488 | 504 x 4464 | exact | 23/23 |

The bulk period is eight layers. The counts above include data preparation,
staggered startup/completion and final readout. The collapsed/effective problem
has 72 rows, 360 columns and 12 observables in both bases. It equals the actual
interior one-round window at t=1. Z t=0 is a startup boundary and differs;
X t=0 also matches. Full and noidle FULL DEM column sets are identical for
both tested round counts/bases. Thus removing idle channels preserves distance
for these finite models; separate noidle distance searches were not run.

Meaningful verification commands and their actual outcomes:

- `.venv/bin/python tests/test_lrgross.py`: first invocation failed before
  searches because Python 3.9 lacks int.bit_count; test corrected to
  bin(...).count('1'). Second invocation passed in 139.783 s. After adding
  schedule/noise/effective assertions, the final invocation passed in 158.077 s.
- A Python heredoc for the added frozen orders, periodic bulk, effective equality
  and full/noidle full-column equality passed before the final script rerun.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/lrgross_run.py parallel Z` and
  the corresponding X command: initial monitor attempt failed because spawning
  ps is forbidden by the sandbox. The monitor was corrected to read child RSS
  through libproc, checked on the current process, then both commands exited 0.
  The initial launches produced no model/search output. A final read-only
  process-argument audit confirmed no live lrgross search processes remained.
  The successful runs executed unchanged:

```text
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py lrgross lr11 Z results/papers3/lrgross/lr11_Z.json 6 3 12 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py lrgross lr11 X results/papers3/lrgross/lr11_X.json 6 3 12 600
```

- `OMP_NUM_THREADS=2 .venv/bin/python papers/lrgross_run.py effective Z`
  and the corresponding X command: both exited 0 with exact 11. The worker
  uses design.effective_problem and design.problem_symmetry, exact search
  k_table=3/kmax=12/cover=True, plus DEM and physical replay. ISD only supplies
  a verified upper bound; it is never used for lower-bound certification.
- The preliminary Python smoke script built r3 circuits for Z/X full/noidle:
  parameters [[144,12]], 288 qubits, 432 detectors, 13,776 DEM mechanisms,
  exact sectors, effective=collapse=window t1; exited 0.
- Final Python JSON audit asserted all four search bounds 11/11, verified
  witnesses, normal process exits, wall time <600 and RSS <2 GiB; passed.
- Final ctypes libproc/sysctl audit inspected only process arguments and found
  no live lrgross runner or run_parallel process; passed.
- A reporting-only JSON query used a nonexistent schedule result key and failed
  with KeyError; corrected query inspected actual schedule_checks and the
  final effective-collapse/window assertions successfully.
- `pwd` / `rg --files` and local `cat`, `sed`, `rg` reads of design.py,
  seq_circuit.py, run_parallel.py, stabcode.py, cornucopia.py, kasai_codes.py,
  sdbb_parallel.py, run_bb.py, README.md, cdist problem/search/symmetry/replay/isd,
  and reference tests succeeded. The first chained read began with
  `git status --short`, which failed: this workspace directory is not a Git
  repository; the reads after that `&&` did not execute and were run separately.
- arXiv HTML/PDF/SVG reads/downloads succeeded for the named paper and cited
  base-code paper. An attempted 2308.07915v3 HTML page returned 404; the
  unversioned page resolved to published v2. No other web sources fetched.
- The PDF curl succeeded, but `pdftotext` failed as unavailable. Searches for
  Poppler binaries and import checks found no PDF rendering packages.
  `swift /tmp/lrgross_render.swift` failed due to SDK/compiler mismatch;
  the Clang PDFKit renderer failed on SDK architecture entries. The agent's
  qlmanage fallback failed its sandbox initialization. Browser discovery found
  no browser; PDF web screenshots supplied no image payload. Finally,
  `.venv/bin/python /tmp/lrgross_render.py` (our own ctypes CoreGraphics/ImageIO
  renderer) succeeded for pages 19-21, followed by visual inspection of
  pages 20/21 and independent schedule/geometry agreement between agents.
- Test syntax AST parsing passed; preliminary test-file searches and a module
  existence read before builder creation returned no match/missing file.

Instances not run: none among the required lr11 full-noise six-round searches
and effective problems. No server continuation is needed. The two unchanged
run_parallel commands above are also the exact server reproduction commands
if the lead wishes to rerun; ordinary remote submission must use the shared
remote-compute workflow.

## Assumptions and open issues

- Printed Figure 10/12 numerical labels count as permitted paper-supplied text
  data. They determine the schedule; no GitHub/Zenodo files were needed.
  Paper locators and all numbers are in papers/new/2603.05481.md.
- Gate phases wrap modulo eight after each check's reset. X gates at 6-8 occur
  before gates at 1-3/4 of the next cycle. No ordering was optimized or changed
  to obtain the paper's conjectured number.
- The lower Figure 12 panel says 'residuals'; caption, times and reset/readout
  table determine that its labels are gate times. This is treated as a heading
  typo, and the precise interpretation is recorded.
- Figure 12 is periodic and does not draw finite memory boundaries. We prepare
  data, start each check at its first printed reset phase, run exactly the
  requested number of complete extractions, finish the last X check at
  8*rounds+5, then measure data. These are the reported finite circuits.
- Final data readout is perfect, as Section II.3 / Appendix E prescribe.
  Initial resets and every ancilla reset/measurement carry the stated flips;
  every idle layer and CNOT have full Pauli support in full noise.
- This is staggered non-interleaved extraction with X and Z sharing disjoint
  layers, rather than the literal X-stage-then-Z-stage seq_circuit builder.
  Paper Theorem 1 applies, and equal collapse/interior-window column sets
  independently establish the effective equivalence for our physical circuit.
- Appendix H prints no explicit best uniform schedule, so CODES has only lr11;
  the uniform <=10 statement is not silently converted into a guessed schedule.
- Figure 12 calls its depth eight and says it matches the original. This
  project's README calls its standard interleaved circuit depth seven and
  reports distance 10. We preserve Figure 12's eight-layer timing; the standard
  project circuit was not rebuilt or altered in this task.
- No shared source or report was edited; no packages/environments were created.
  Changes remain in the workspace; no commit, push, stash, or branch operation
  was performed. No unresolved construction/search issue remains.
