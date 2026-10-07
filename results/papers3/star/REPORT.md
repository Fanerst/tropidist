## Summary

Implemented the literal STAR polynomial and Table 2 schedule, retaining the natural but unprinted convention B_i=A_i^T. Source: [STAR Appendix B](https://arxiv.org/html/2606.25011#A2).

| Key | Rebuilt (n,k) | Exact code distance | Relation to selfdual_bb.py check matrices |
|---|---|---:|---|
|42|(42,6)|6|Inequivalent: 45 versus 39 triangles/check in the check-intersection graph|
|66|(66,6)|8|Equal after explicit check/qubit relabelling|
|78|(78,6)|10|Equal after explicit check/qubit relabelling|

Code distances were obtained by exhaustive exact CSS searches with k_table=2 and translation symmetry; H_X=H_Z proves equality of the two code sectors. Witnesses passed search.verify.

STAR42 Table 2 has exact circuit distance 6 in both bases at six and eighteen rounds, versus the paper's stated 5. All layers use every physical qubit, so full and noidle circuits are identical. The existing 42 mirror cannot be transported by qubit/check relabelling. The 66/78 mirrors can be transported and pass all circuit checks.

The inferred fixed-internal-X-order grammar gives 212 valid schedules from 40,320 candidates. Table 2 is included. The paper's 192-at-4 / 20-at-5 fault-distance histogram was not reproduced or assumed; the 424 basis/schedule searches remain deferred.

All requested chosen-schedule runs completed locally. Across tested bases, the minimum distances are 6, 8 and 9. The separate 78 Z distance remains bounded at 9–10.

## Changes

- `papers/star.py` — literal codes, Table 2 schedule, noise model, schedule enumeration and relabellings.
- `papers/star_run.py` — run_parallel schedule-variant wrapper.
- `papers/new/2606.25011.md` — source locators, definitions, grammar and reconstruction assumptions.
- `tests/test_star.py` — plain-script exact code and circuit checks.
- `results/papers3/star/42_X.json` — certified bounds and physically verified witness.
- `results/papers3/star/42_X_noidle.json` — certified bounds and physically verified witness.
- `results/papers3/star/42_Z.json` — certified bounds and physically verified witness.
- `results/papers3/star/42_Z_noidle.json` — certified bounds and physically verified witness.
- `results/papers3/star/42_execution.json` — command, outcome, timing and resource audit.
- `results/papers3/star/42_r18_X.json` — certified bounds and physically verified witness.
- `results/papers3/star/42_r18_X_run.json` — command, outcome, timing and resource audit.
- `results/papers3/star/42_r18_Z.json` — certified bounds and physically verified witness.
- `results/papers3/star/42_r18_Z_run.json` — command, outcome, timing and resource audit.
- `results/papers3/star/66_X.json` — certified bounds and physically verified witness.
- `results/papers3/star/66_Z.json` — certified bounds and physically verified witness.
- `results/papers3/star/78_X.json` — certified bounds and physically verified witness.
- `results/papers3/star/78_Z.json` — certified bounds and physically verified witness.
- `results/papers3/star/78_Z_k3.json` — certified bounds and physically verified witness.
- `results/papers3/star/78_Z_k3_audit.json` — command, outcome, timing and resource audit.
- `results/papers3/star/REPORT.md` — complete review report and file manifest.
- `results/papers3/star/histogram_commands.txt` — 424 unrun basis/schedule histogram commands.
- `results/papers3/star/reconstruction.json` — explicit matrix-equivalence evidence and reconstruction conventions.
- `results/papers3/star/remaining_commands.txt` — unrun extended 78 Z search command.
- `results/papers3/star/requested_execution.json` — command, outcome, timing and resource audit.
- `results/papers3/star/summary.json` — all local bounds and circuit metrics.
- `results/papers3/star/valid_schedules.json` — 212 inferred-grammar schedules; Table 2 is index 96.
- `logs/papers3/star/42_X.log` — actual pipeline output.
- `logs/papers3/star/42_X_noidle.log` — actual pipeline output.
- `logs/papers3/star/42_Z.log` — actual pipeline output.
- `logs/papers3/star/42_Z_noidle.log` — actual pipeline output.
- `logs/papers3/star/42_Z_requested_check.log` — actual pipeline output.
- `logs/papers3/star/42_r18_X.log` — actual pipeline output.
- `logs/papers3/star/42_r18_Z.log` — actual pipeline output.
- `logs/papers3/star/66_X.log` — actual pipeline output.
- `logs/papers3/star/66_X_run.json` — command, outcome, timing and resource audit.
- `logs/papers3/star/66_Z.log` — actual pipeline output.
- `logs/papers3/star/66_Z_run.json` — command, outcome, timing and resource audit.
- `logs/papers3/star/78_X.log` — actual pipeline output.
- `logs/papers3/star/78_X_run.json` — command, outcome, timing and resource audit.
- `logs/papers3/star/78_Z.log` — actual pipeline output.
- `logs/papers3/star/78_Z_k3.log` — actual pipeline output.
- `logs/papers3/star/78_Z_run.json` — command, outcome, timing and resource audit.
- `logs/papers3/star/focused_tests.log` — successful final schedule-family and rejection checks.
- `logs/papers3/star/larger_launch_failures.json` — failed larger-run launch/monitor attempts.
- `logs/papers3/star/root_launch_failures.json` — failed resource-limit/process-monitor/Git probes.
- `circuits/papers/star42_r18_X.stim` — saved memory circuit.
- `circuits/papers/star42_r18_Z.stim` — saved memory circuit.
- `circuits/papers/star42_r6_X.stim` — saved memory circuit.
- `circuits/papers/star42_r6_X_noidle.stim` — saved memory circuit.
- `circuits/papers/star42_r6_Z.stim` — saved memory circuit.
- `circuits/papers/star42_r6_Z_noidle.stim` — saved memory circuit.
- `circuits/papers/star66_r6_X.stim` — saved memory circuit.
- `circuits/papers/star66_r6_Z.stim` — saved memory circuit.
- `circuits/papers/star78_r6_X.stim` — saved memory circuit.
- `circuits/papers/star78_r6_Z.stim` — saved memory circuit.

No existing shared source file was edited; no packages, environments, remote jobs, commits, pushes, stashes or branch changes were made. The directory is not a Git repository, so Git status could not be used.

## Verification

| Result file | Basis | Rounds | Noise | Certified LB | Verified UB | Seconds | Paper number |
|---|---|---:|---|---:|---:|---:|---|
|42_Z.json|Z|6|full|6|6|17.2|5 (chosen schedule)|
|42_X.json|X|6|full|6|6|14.5|5 (chosen schedule)|
|42_Z_noidle.json|Z|6|noidle|6|6|14.3|5 (chosen schedule)|
|42_X_noidle.json|X|6|noidle|6|6|13.2|5 (chosen schedule)|
|42_r18_Z.json|Z|18|full|6|6|72.0|5 (chosen schedule)|
|42_r18_X.json|X|18|full|6|6|73.0|5 (chosen schedule)|
|66_Z.json|Z|6|full|8|8|43.0|No instance-specific exact value|
|66_X.json|X|6|full|8|8|33.8|No instance-specific exact value|
|78_Z.json|Z|6|full|9|10|277.7|No instance-specific exact value|
|78_X.json|X|6|full|9|9|140.3|No instance-specific exact value|
|78_Z_k3.json|Z|6|full|9|10|225.3|No instance-specific exact value|

Every reported upper bound has distinct undecomposed DEM mechanisms, zero fired detectors, a nonzero logical flip, and matching physical Stim replay. Every CSS sector reduction is exact.

| Circuit | Physical qubits | CNOT layers/cycle | Detectors | DEM mechanisms Z / X | Symmetries Z / X |
|---|---:|---:|---:|---|---|
|42 paper, six rounds, full=noidle|84|8|252|13902 / 13944|20/20 / 20/20|
|42 paper, eighteen rounds, full|84|8|756|43134 / 43176|20/20 / 20/20|
|66 paper, six rounds, full=noidle|132|8|396|21846 / 21912|32/32 / 32/32|
|66 transported mirror, six rounds, full=noidle|132|8|396|21846 / 21846|32/32 / 32/32|
|78 paper, six rounds, full=noidle|156|8|468|25818 / 25896|38/38 / 38/38|
|78 transported mirror, six rounds, full=noidle|156|8|468|25818 / 25818|38/38 / 38/38|

Mirror66/78 rows above are circuit-structure tests, not circuit-distance searches. Every experiment has all six logical observables.

Commands actually run (OMP_NUM_THREADS=2 throughout computational commands):

- `OMP_NUM_THREADS=2 .venv/bin/python tests/test_star.py` — exit 0. The initial full script passed all code and ten available paper/mirror/basis circuit cases. The final guard-related additions were then independently rerun.
- `OMP_NUM_THREADS=2 .venv/bin/python` with `runpy.run_path('tests/test_star.py')`, `check_schedule_family()` and `check_rejected_schedules()` — exit 0 after the final build guard; output saved in focused_tests.log.
- Python wrapper smoke probe — exit 0; verified mirror66/noidle facade dispatch, variant naming and absent paper claim; mirror42 correctly raised ValueError.
- Python enumeration/JSON evidence generation — exit 0; 212 unique schedules, paper index 96, all 212 symbolically clean and disjoint on STAR42.

- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 42 Z results/papers3/star/42_Z.json 6 2 10 120 1 full` — exit 0, 24.82 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 42 X results/papers3/star/42_X.json 6 2 10 120 1 full` — exit 0, 15.84 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 42 Z results/papers3/star/42_Z_noidle.json 6 2 10 120 1 noidle` — exit 0, 15.38 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 42 X results/papers3/star/42_X_noidle.json 6 2 10 120 1 noidle` — exit 0, 14.52 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 42 Z results/papers3/star/42_Z.json 6 3 10 600` — exit 0; exact requested verification command.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 42 Z results/papers3/star/42_r18_Z.json 18 2 10 90` — exit 0, 73.155 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 42 X results/papers3/star/42_r18_X.json 18 2 10 90` — exit 0, 74.584 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 66 Z results/papers3/star/66_Z.json 6 2 12 120` — exit 0, 45.19 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 66 X results/papers3/star/66_X.json 6 2 12 120` — exit 0, 34.85 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 78 Z results/papers3/star/78_Z.json 6 2 12 120` — exit 0, 279.11 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 78 X results/papers3/star/78_X.json 6 2 12 120` — exit 0, 141.04 wall seconds.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 78 Z results/papers3/star/78_Z_k3.json 6 3 10 180` — exit 0; 226.041 wall seconds; weight-9 threshold timeout.

- Final Python JSON audit — exit 0 for all eleven distance outputs; checked bounds, distinct witness indices, empty detector outcomes, matching replay logical outcomes, exact sectors, all symmetries and recorded timings. The k_coll=3 retry model matches the baseline exactly.
- Source reads using cat/sed/rg — succeeded. `cat tests/test_kasai_codes.py` failed because the file does not exist. Initial int.bit_count probes failed under Python 3.9 and corrected bin(...).count('1') probes passed.
- HTML and PDF extraction of the named arXiv paper — successful; Table 2 data agree. PDF visual rendering was unavailable: no pdftoppm or PDF Python dependencies; Swift/Objective-C PDFKit attempts failed due compiler/SDK mismatches. No package was installed.
- Initial RLIMIT_AS/RLIMIT_DATA guards were rejected by macOS; ps/pgrep monitoring was denied by the sandbox. Clean bounded reruns completed and logs were verified free of corruption. Failed attempts are recorded in launch audit JSON files.
- `git status --short` — exit 128: no Git repository.
- Final report-manifest Python audit — exit 0: exactly four requested sections, all 55 listed files present, eleven result records, 424 deferred commands, no mirror42 output, and no NUL bytes in any saved log.

Every controlled distance run had a 590-second subprocess cap and completed within it. The largest measured child peak RSS was 344,735,744 bytes (328.77 MiB), below 2 GiB. OMP_NUM_THREADS was set to 2, but the compiled search kernel reported one actual thread. No remote computation was submitted.

Commands not run:

- `OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py star 78 Z results/papers3/star/78_Z_extended.json 6 3 12 600` — deferred longer search for the lead/server; also saved in remaining_commands.txt.
- The 424 exact schedule/basis commands are listed individually in histogram_commands.txt. They were not executed. Removing idle channels would duplicate these circuits.
- No mirror42 command is valid: the requested prerequisite of equal check matrices up to relabelling fails. The wrapper refuses this variant rather than substituting an analogous circuit.

## Assumptions and open issues

1. Appendix B.2 lists A1=xy^4, A2=xy^2, A3=y^3, A4=1 but omits the B-index dictionary. This rebuild assumes B_i=A_i^T. Symbolic cleanliness holds for other B index assignments too, so determinism cannot establish the author's intended dictionary. The observed distance-6 discrepancy is conditional on this natural reading.
2. Appendix B.2 refers to an omitted schedule grammar via Bravyi et al. The ascending internal X A/B orders are inferred; reproducing 212 does not prove this is precisely the authors' entire search space. The 66/78 mirror schedules enter this grammar after joint monomial-label renaming, not as literal members with the fixed printed dictionary.
3. Section III specifies depolarization after preparation/gates and outcome flips, with idle noise only during entangling layers. Basis resets and measurements are primitive RX/MX operations; no unprinted noisy H implementation is inserted. Every qubit is active in every CNOT layer, so there are zero entangling idle channels.
4. The requested six-round experiment differs from Section III's r=3d Monte Carlo duration. Both eighteen-round 42 checks also give exact 6, so that duration change does not explain the quoted 5.
5. STAR B.1 says its parameters match the cited 2025 code table, but its printed 42 check matrices are inequivalent to the existing selfdual_bb.py instance under check/qubit permutations. The invariant does not rule out equivalence after arbitrary stabilizer-generator changes; that stronger question was not required.
6. Section II.3 has generic d-1 wording. Appendix B.2 explicitly ranks only the d=6 schedules, so CODES[66/78][3] is None rather than an invented instance-specific exact value.
7. The 78 Z distance remains unresolved at 9–10; the tested 78 X circuit is exact 9. The 192/20 fault histogram has not been computed.
