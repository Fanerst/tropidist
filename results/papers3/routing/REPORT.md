## Summary

Built all ten requested definitions and the alternating forward/backward CXSWAP memory circuit. All reproduce the stated (n,k) and CSS commutation. All eight short definitions have exact code distance in both bases. Six-round circuit distance is exact for 54, 70, 80, 90 and 100; the three remaining short instances retain certified bounds. Length 80 has code distance 8, not Table 1’s 7.

**Instance verification (three rounds; counts apply to both bases)**

| Key | Rebuilt (n,k) | Exact code d: Z/X | Physical qubits | Layers/cycle | Detectors | DEM mechanisms | Sector | Symmetries |
|---|---|---|---:|---:|---:|---:|---|---|
| 54 | (54, 8) | 6/6 | 108 | 7 | 162 | 7020 | exact | 26/26 |
| 70 | (70, 8) | 7/7 | 140 | 7 | 210 | 9100 | exact | 34/34 |
| 80 | (80, 8) | 8/8 | 160 | 7 | 240 | 10480 | exact | 39/39 |
| 90 | (90, 8) | 9/9 | 180 | 7 | 270 | 11790 | exact | 44/44 |
| 100 | (100, 8) | 10/10 | 200 | 7 | 300 | 13100 | exact | 49/49 |
| 110 | (110, 8) | 11/11 | 220 | 7 | 330 | 14410 | exact | 54/54 |
| 140_12 | (140, 8) | 12/12 | 280 | 7 | 420 | 18200 | exact | 69/69 |
| 140_13 | (140, 8) | 13/13 | 280 | 7 | 420 | 18340 | exact | 69/69 |
| 200_24 | (200, 24) | not run (paper d > 13) | 400 | 11 | 600 | 44800 | exact | 99/99 |
| 200_16 | (200, 16) | not run (paper d > 13) | 400 | 11 | 600 | 44800 | exact | 99/99 |

**Local six-round circuit results**

All upper bounds below have an undecomposed-DEM check and physical Stim replay with zero detectors and nonzero, matching logical flips. A timeout does not certify its unfinished threshold.

| Key | Z: lower–upper | X: lower–upper | Paper upper | Pipeline seconds Z / X | Detectors | DEM mechanisms |
|---|---|---|---:|---|---:|---:|
| 54 | 6–6 | 6–6 | ≤ 6 | 20.2 / 17.2 | 324 | 14958 |
| 70 | 7–7 | 7–7 | ≤ 7 | 26.1 / 36.6 | 420 | 19390 |
| 80 | 8–8 | 8–8 | ≤ 8 | 31.1 / 45.6 | 480 | 22240 |
| 90 | 9–9 | 9–9 | ≤ 9 | 51.5 / 50.7 | 540 | 25020 |
| 100 | 9–9 | 9–9 | ≤ 9 | 96.4 / 79.2 | 600 | 27800 |
| 110 | 9–10 | 9–10 | ≤ 10 | 124.7 / 125.8 | 660 | 30580 |
| 140_12 | 9–12 | 9–12 | ≤ 11 | 85.8 / 67.7 | 840 | 38780 |
| 140_13 | 10–13 | 10–13 | ≤ 12 | 58.7 wall; incomplete / 53.3 wall; incomplete | 840 | 38920 |

The 110 pipeline initially returned 9–11; two-round subset searches improved the verified upper bound to 10 in 18.241 s (Z) and 20.294 s (X), 38.538 s total. Their weight-9 exhaustion certifies only the subset, so the full lower bound remains 9. For 140_12 and 140_13, four upper-only target searches at weights 11/12 timed out at about 20 s each. This supplied no improved bound. Direct mapping of already verified code-distance-13 witnesses into first-round windows supplied the 140_13 upper bounds. The 140 auxiliary work took 98.096 s, including 7.422 s for fallback mapping and replay.

## Changes

- `papers/routing.py` — paper definitions, chronological moving-role routing, matrices, translations and full-noise CXSWAP builder.
- `papers/routing_run.py` — resumable, bounded exact CSS code-distance runner and witness checks.
- `papers/new/2606.25330.md` — exact extraction data, locators and construction/boundary ambiguities.
- `tests/test_routing.py` — all-instance plain-script geometry, noise, detector, DEM, sector and symmetry tests.
- `circuits/papers/routing100_8_10_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing100_8_10_r6_Z.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing110_8_11_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing110_8_11_r6_Z.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing140_8_12_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing140_8_12_r6_Z.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing140_8_13_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing140_8_13_r6_Z.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing54_8_6_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing54_8_6_r6_Z.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing70_8_7_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing70_8_7_r6_Z.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing80_8_8_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing80_8_8_r6_Z.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing90_8_9_r6_X.stim` — six-round physical routing memory circuit.
- `circuits/papers/routing90_8_9_r6_Z.stim` — six-round physical routing memory circuit.
- `logs/papers3/routing/100_8_10_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/100_8_10_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/110_8_11_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/110_8_11_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/110_two_round_windows.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/140_8_12_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/140_8_12_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/140_8_13_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/140_8_13_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/140_two_round_windows.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/54_8_6_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/54_8_6_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/70_8_7_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/70_8_7_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/80_8_8_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/80_8_8_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/90_8_9_X.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/90_8_9_Z.log` — actual command/search output and verification outcomes.
- `logs/papers3/routing/code_distances.log` — actual command/search output and verification outcomes.
- `results/papers3/routing/100_8_10_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/100_8_10_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/110_8_11_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/110_8_11_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/110_two_round_windows.json` — bounded subset searches and independently verified physical witnesses.
- `results/papers3/routing/140_8_12_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/140_8_12_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/140_8_13_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/140_8_13_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/140_two_round_windows.json` — bounded subset searches and independently verified physical witnesses.
- `results/papers3/routing/54_8_6_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/54_8_6_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/70_8_7_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/70_8_7_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/80_8_8_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/80_8_8_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/90_8_9_X.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/90_8_9_Z.json` — unchanged pipeline output, certificates and witness data (possibly incomplete).
- `results/papers3/routing/additional_run_status.json` — six supervised 110/140 pipeline command outcomes and wall times.
- `results/papers3/routing/circuit_models.json` — 20 three-round DEM/sector/symmetry model records.
- `results/papers3/routing/code_distances.json` — 16 exact code-distance certificates and verified witnesses.
- `results/papers3/routing/summary.json` — merged best verified bounds, timings and model metadata.
- `results/papers3/routing/REPORT.md` — complete task report and per-file manifest.

Temporary three-round Stim artifacts used during metadata auditing were deleted. No existing shared project source was edited. No commits, pushes, stashes, branch switches or history rewrites were performed. The directory has no Git repository, so Git diff/status verification was unavailable.

## Verification

- `OMP_NUM_THREADS=2 .venv/bin/python papers/routing.py` — exit 0; all ten (n,k) values and CSS checks reproduced.
- `OMP_NUM_THREADS=2 .venv/bin/python tests/test_routing.py` — final exit 0, 261.56 s. Checks all ten instances in both bases at 2 and 3 rounds, current-role routing, reverse contacts, disjoint layers, atomic gate fault support, moved final readout, detector coordinates, deterministic noiseless detectors/observables, noisy undecomposed DEM, exact sectors and translation generators.
- `OMP_NUM_THREADS=2 .venv/bin/python papers/routing_run.py code 90 1400` — successful full pass: 16 actual basis searches, 40.028 s. Iterative deepening with k_table=3, cover=True, labelfree=True; all smaller weights exhausted, all minimum witnesses independently checked. Resume invocations were no-ops and preserved the elapsed total and certificates.
- `OMP_NUM_THREADS=2 .venv/bin/python` inline independent construction checks — all ten parameter sets, polynomial supports, chronological gates and backward inverses passed.
- Inline Stim tableau/idle audit — exit 0, 21.362 s; CXSWAP equals CX then SWAP, reverse operand gate is the inverse, and every backward schedule is the reversed forward schedule with reversed operands. Deleting idle channels for 54 in both bases at rounds 1/2/3 preserved the entire undecomposed signature support (378/4104/7020).
- Inline all-model audit — interrupted deliberately, exit 130, before ten minutes; all candidate translations were individually verified for the first nine definitions. Resumed metadata collection completed all 20 models; remaining 200_16 translations were proved by verified generators and complete-group comparison. Temporary three-round circuits were removed.
- Inline source compilation with built-in compile(...) — all three Python source files passed without cache writes.
- Inline final JSON checks — all 16 code certificates, all 20 model records and all 16 best full-circuit bounds/witness records parsed and passed consistency assertions.

**Unchanged pipeline commands actually run**

The first six commands were supervised at a 580-second total wall limit; the remaining ten at 180 seconds. Every command process exited 0. Search timeouts below are algorithm timeouts, not successful exact proofs. `OMP_NUM_THREADS=2` was set; the macOS kernel reported one actual thread.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 54 Z results/papers3/routing/54_8_6_Z.json 6 2 16 90
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 54 X results/papers3/routing/54_8_6_X.json 6 2 16 60
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 70 Z results/papers3/routing/70_8_7_Z.json 6 2 16 60
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 70 X results/papers3/routing/70_8_7_X.json 6 2 16 60
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 80 Z results/papers3/routing/80_8_8_Z.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 80 X results/papers3/routing/80_8_8_X.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 90 Z results/papers3/routing/90_8_9_Z.json 6 2 16 60
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 90 X results/papers3/routing/90_8_9_X.json 6 2 16 60
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 100 Z results/papers3/routing/100_8_10_Z.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 100 X results/papers3/routing/100_8_10_X.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 110 Z results/papers3/routing/110_8_11_Z.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 110 X results/papers3/routing/110_8_11_X.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_12 Z results/papers3/routing/140_8_12_Z.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_12 X results/papers3/routing/140_8_12_X.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_13 Z results/papers3/routing/140_8_13_Z.json 6 2 16 30
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_13 X results/papers3/routing/140_8_13_X.json 6 2 16 30
```

110 K=9 and 140_12 K=9 full-sector thresholds timed out. The 140_13 enumeration of all minimum collapsed solutions at K=10 timed out, so those baseline JSON files have a certified lower bound but no upper bound or completed-run seconds. Supervisor wall times are reported above. Other circuit searches completed exact certificates.

- Supervised inline `OMP_NUM_THREADS=2 .venv/bin/python -u -` two-round-window scripts — exit 0. 110: start=9, kmax=10, k_table=2, time_limit=20; exact subset searches and 10-fault physical witnesses verified. 140: start=kmax=11 or 12, k_table=2, time_limit=20; all four searches timed out without witnesses. Returned lower bounds from skipped-weight searches were deliberately not treated as certified. Direct code-witness mapping for 140_13 verified 13-fault full-circuit upper witnesses. Both scripts remained below their 150-second wall limits.

**Failed exploratory commands and corrections**

- `curl -L --fail --silent https://arxiv.org/html/2606.25330v2 -o /tmp/routing2606.html` — succeeded. BeautifulSoup parsing failed because bs4 is absent; standard-library HTMLParser extraction succeeded.
- Named-paper PDF download succeeded; pdftotext was unavailable, and pypdf import failed. No package was installed; paper HTML supplied the definitions.
- Initial test/code-runner attempts failed on int.bit_count(), unavailable in this Python; replaced with bin(...).count('1'). Final runs passed.
- An intermediate full-symmetry test was interrupted, exit 130; redundant group-element checks were replaced by generator verification and complete-group comparison before the successful complete run.
- `.venv/bin/python -m py_compile papers/routing_run.py` failed because its configured bytecode cache was outside writable paths; in-memory source compilation passed.
- An exploratory inline call to cdist.problem.from_dem failed: that API does not exist. Corrected to load_dem_problem or the test’s in-memory DEM parser.
- `ps ...` failed because process inspection is sandbox-denied. Peak RSS was not measured; allocations were sized below the 2 GB limit (largest short-code table about 9 MB; largest full short-circuit table about 302 MB).
- `git status --short` failed, exit 128: this directory is not a Git repository.
- One malformed rg character-class search and searches for nonexistent test/PDF-extraction files failed; corrected HTML/source searches succeeded. Other ls/rg/sed/tail/JSON inspections succeeded.

## Assumptions and open issues

Construction and fault-model locators are recorded in `papers/new/2606.25330.md`, with exact vectors and supports. Source: [arXiv:2606.25330v2, Sections II–III and Appendices B–F](https://arxiv.org/html/2606.25330v2).

- Default is the CSS-preserving CXSWAP compilation. D.1 explicitly identifies noiseless single-qubit iSWAP compilation with this model; local Clifford wrappers preserve the complete depolarizing Pauli support. Physical iSWAP needs Appendix B’s wrappers and basis changes. Adding wrapper noise changes the fault model.
- Eq. (2) role predicates are read at current moved positions, as Section III requires. Eq. (3)’s S_t shorthand has composition order reversed relative to its explicit recurrence; chronological swaps follow the recurrence and preceding palindrome expression.
- Table 1 labels the length-80 definition d=7; Tables 2/3 label d=8. Both actual basis searches prove d=8. CODES[80][2] preserves Table 1’s tuple, and its unique tag is 80_8_8.
- Table 1 lists the length-90 nonlocal vector (4,1), but Table 3 defines (2,1). Used the complete Table 3 sequence.
- Preparation and readout each consume one parallel tick with idle data depolarization. D.1 does not give tick durations. These boundary-idle supports duplicate full two-qubit gate-fault supports; a direct 54 support check confirmed equivalence.
- Appendix C.2 does not specify the distance-sampling round count or noisy versus ideal final-data-syndrome boundary. Used task-requested finite memory experiments with noisy data preparation/readout. D.2’s N=10 concerns logical-error simulations.
- Proposition 2’s sufficient subclass does not cover all Table 3 vectors, and Proposition 3’s no-wrap condition fails for the weight-11 (20,20) instance. Explicit commutation, matching and deterministic circuit tests were used.
- Exact circuit distance remains open for 110, 140_12 and 140_13. The 140 paper upper bounds were not reproduced by the bounded local searches; larger verified upper witnesses do not contradict those bounds. Both weight-11 circuit distances and code distances above 13 were not searched locally.

**Commands not run locally (lead/server follow-up)**

Use the lead’s authorized remote-compute workflow for these larger searches. The following are the concrete pipeline commands; they can exceed the laptop’s memory/time limits.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 110 Z results/papers3/routing/110_8_11_Z.json 6 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 110 X results/papers3/routing/110_8_11_X.json 6 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_12 Z results/papers3/routing/140_8_12_Z.json 6 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_12 X results/papers3/routing/140_8_12_X.json 6 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_13 Z results/papers3/routing/140_8_13_Z.json 6 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 140_13 X results/papers3/routing/140_8_13_X.json 6 2 16 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 200_24 Z results/papers3/routing/200_24_14_Z.json 6 2 20 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 200_24 X results/papers3/routing/200_24_14_X.json 6 2 20 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 200_16 Z results/papers3/routing/200_16_17_Z.json 6 2 20 600
OMP_NUM_THREADS=2 .venv/bin/python papers/run_parallel.py routing 200_16 X results/papers3/routing/200_16_17_X.json 6 2 20 600
```

Optional exact weight-11 code-distance checks (not run):

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/routing_run.py worker 200_24 Z 600
OMP_NUM_THREADS=2 .venv/bin/python papers/routing_run.py worker 200_24 X 600
OMP_NUM_THREADS=2 .venv/bin/python papers/routing_run.py worker 200_16 Z 600
OMP_NUM_THREADS=2 .venv/bin/python papers/routing_run.py worker 200_16 X 600
```

No packages or environments were installed, no author repositories or data sets were fetched, and no remote compute jobs were launched.
