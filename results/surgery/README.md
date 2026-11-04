# Codes of qLDPC logical measurements (2026-11-03)

Certified distances of the codes that published constructions of logical measurements produce.

## Universal adapters, arXiv:2410.03628

Check matrices from the authors' Zenodo record 10.5281/zenodo.17527545 (`data_qLDPC_surgery.zip`, CC-BY 4.0; not
stored here). `papers/surgery_codes.py` certifies the X and Z distances of each pair by the weight-bounded search (no
symmetry supplied) and checks the lightest logical operator against the matrices: `adapters.json`, `adapters.log`.

| code | n | k | d_X | d_Z |
|---|---|---|---|---|
| [[98,6,12]] original | 98 | 6 | 12 | 12 |
| [[200,20,10]] original | 200 | 20 | 10 | 10 |
| BB, auxiliary graph for Z_1 | 121 | 5 | 12 | 12 |
| BB, auxiliary graph for Z_3 | 115 | 5 | 12 | 12 |
| BB, naive joint Z_1 Z_3 | 137 | 5 | 12 | 12 |
| LP, auxiliary graph for Z_2 | 220 | 19 | 10 | 10 |
| BB intracode adapter, Z_1 Z_3 | 150 | 5 | 12 | 12 |
| BB-LP intercode adapter, Z_1 Z_2 | 355 | 25 | 10 | 10 |

Every value the paper reports holds; each code takes under 0.2 s.

## SSIP, arXiv:2407.09423 (gross-code merges)

SSIP's merged codes are subsystem codes: logical qubits that a merge introduces are relegated to gauge qubits. Its
Appendix A defines their distance by dressed logical operators (append the gauge Z logicals to P_Z and take the Z
distance, and the same with X and Z exchanged). Its routine `subsystem_distance_GAP` (ssip/distance.py, repository
commit 8e4d771) instead calls QDistRnd as `DistRandCSS([P_Z; gauge Zs], P_X)` and `DistRandCSS([P_X; gauge Xs], P_Z)`.
`DistRandCSS(P, Q)` returns the least weight of a vector orthogonal to the rows of P and independent of the rows of Q
(QDistRnd manual, Sec. 3.1), so these are the bare distances: operators that also commute with the gauge logicals
of the other type. Dressed <= bare, with equality when a merge leaves no gauge qubit.

`papers/ssip_exact.py` runs SSIP's own scripts `benchmarking/gross_code_*.py` with that routine replaced by exact
computations of both distances (weight-bounded search up to 12, every lightest operator checked against the
matrices), in two modes: steered by the bare distance (SSIP's quantity, `<script>_bare/`) and by the dressed one
(`<script>_dressed/`). Each directory holds the script's result files and `calls.jsonl` (one line per distance call:
n, k, gauge qubits, bare and dressed X and Z distances, witnesses). `ssip_summary.py` matches calls to SSIP's
recorded results (`benchmarking/results/`) and writes `ssip_summary.json`.

Environment. SSIP's merged codes depend on the networkx version, which SSIP does not pin: with networkx 3.6.1
(`ssip_5090/`, 5090, numpy 2.5) 13 of the 84 external merges at depth 1 differ from those with networkx 3.7. The
reference set `ssip/` uses Python 3.12, numpy 1.26 (SSIP's pin) and networkx 3.7: locally (scratchpad `ssip_env`),
and on 5090 with networkx 3.7 placed in the SSIP directory, which gives the same codes and distances
(checked on all external merges and on the dressed internal merges). A second local run of the external merges
(`ext_merges_repeat/`) is identical to the first, witnesses included.

Findings (reference set, `ssip_summary.json`; tables and macros from `docs/make_ncs_figures.py`):
- The bare reruns reproduce SSIP's recorded depths in every script, and its result files line for line except
  the omega value (largest check weight) of the parallel X merge, 13 against SSIP's 12, in every environment we ran:
  QDistRnd was tight for the quantity SSIP computes. All bare distances at the published depths are >= 12.
- At SSIP's depths the dressed distance is below 12 in 78 of the 141 measurements: external merges 24 of 42 (X) and
  21 of 42 (Z), least 9; internal merges 6 of 12 (X, least 6) and 10 of 15 (Z, least 8); single-qubit 6 of 12 in
  each basis, least 8; parallel external merges 1 of 2 (X, least 2, 75 gauge qubits); parallel single-qubit
  measurements 4 of 4, least 2 (36 gauge qubits).
- Steered by the dressed distance, all 141 measurements together need 12,834 ancilla qubits instead of 5,664: the
  external, internal and single-qubit measurements 6,570 instead of 4,080; the four parallel single-qubit
  measurements depth 6 instead of 1 or 3 (dressed distance 2, 4, ..., 12 at depths 1 to 6), 4,032 instead of 1,152;
  the parallel external X merge depth 6 instead of 1 (dressed X distance 2 to 12 in steps of 2), 2,016 instead of
  216, while the parallel Z merge keeps depth 1 (216). The parallel dressed runs were made on 5090 with networkx 3.7
  (`par_singleqs_dressed/`, `par_ext_merges_dressed/`).
- Independent checks with numpy only (scratchpad scripts, recorded here in words): the external X merge (2,2) at
  depth 1 (n 306, k 26, 3 gauge qubits) has a weight-9 X operator that commutes with every Z check and lies outside
  span(X checks, gauge X); the parallel X measurement of logicals 6-11 at depth 1 (n 252, k 42, 36 gauge qubits) has
  such an operator of weight 2 on two ancilla qubits. In the latter, the gauge logicals SSIP returns are independent
  modulo the checks and pair off (rank 36 each, pairing rank 36), 6 data Z logicals remain, and the weight-2 operator
  anticommutes with four of them.

The dressed distance depends on which new logical qubits are taken as gauge; these numbers use the gauge logicals
SSIP's code returns, with the definition of its Appendix A.

## Gauge fixing (added 2026-11-03 evening)

Every shortfall lies in the measured basis: at the published depths the dressed distance in the other basis is at
least 12 in all 141 measurements (`ssip_summary.json`, `least_gauge_fixed_at_ssip_depth`). With the gauge logicals of
the other basis fixed, the merged code is the stabilizer code with them added as checks; its distance is the bare
distance in the measured basis and the dressed distance in the other, so 12 in all 141.

`papers/ssip_gauge_fix.py` reruns SSIP's scripts, replaying the exact bare distances of `<script>_bare/calls.jsonl` so
that they build the same merged codes, and tests for each merged code (`<script>_gauge/gauge.jsonl`): with the
original blocks in a code state and the new qubits in |0> (X measurements) or |+> (Z measurements), are all merged
checks of that type definite, and are all gauge logicals of that type definite (restriction to the original qubits in
the span of the original checks)? Gauge logicals commute with every check, so they keep these values through the merge
and are read out at the split (new qubits measured, next round of the original checks). A decoder that compares the two
values sees the gauge-fixed distance; the light dressed operators (weight 9 and 2 in the two numpy checks above) each
flip a definite gauge logical. Results: in all 200 merged codes that the scripts build (the 141 at the published
depths and the shallower ones), exactly one preparation makes every merged check of its type definite, |0> for X
measurements and |+> for Z measurements, and with it every gauge logical of that type is definite (up to 75 and 77 in
the parallel external merges); `fixed_by_preparation` equals the number of measurements in every file of
`ssip_summary.json`. The replayed runs reproduce every result file of the bare runs. (SSIP's parallel merges list
their new qubits as if appended after the original ones, which their merge map does not follow; the test uses only
the map's images of the original qubits.)
Later surgery constructions fix the gauge explicitly (Williamson and Yoder, arXiv:2410.02213, initial state of the edge
qubits; Cross et al., arXiv:2407.18393, gauge checks); SSIP's paper, following Cohen et al., leaves it free.
