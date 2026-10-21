# Rank-width solver audit, 21 October 2026

Existing algorithms were applied to the saved QEC matrices, not only reviewed.
The audit used upstream `rw` 0.10 for exact small instances, Gericom's simulated annealing implementation for ten larger instances, and the existing NNI implementation in the sibling decoder repository.
All external trees were independently checked over GF(2).
The resulting larger-instance widths are constructive upper bounds, not optimality certificates.

## Matrix and tree conventions

For the columns of a binary matrix H, the boundary dimension is
`lambda_H(S) = rank(H_S) + rank(H_(E\S)) - rank(H)`.
The graph supplied to the external solvers is the fundamental graph of a systematic representation `[I | A]`.
Its vertices are the original columns, and its cut-rank equals this boundary dimension.
The original Tanner graph is not substituted for this graph.
The choice of column basis affects a heuristic's search trajectory but not any fixed column partition's cut-rank.

For a join inducing the column partition A, B, C, the compatible-pair count is `2**J`, where `J = rank(H_A) + rank(H_B) + rank(H_C) - rank(H)`.
This algebraic count was checked by independent small-space enumeration.
A reduction in the largest edge width can be accompanied by a large increase in J.
Consequently, the records retain both quantities.
Actual distance queries require the augmented matrix `[H; l_i]` for each logical row.
Its cut dimension can increase or decrease by one, and its resource profile must be checked separately.

## Exact algorithm and available implementations

Oum's direct subset recurrence minimizes the larger child width over every nontrivial split, with the current cut-rank included.
Its running time is `O(3^n log n + 2^n n^3)` under the paper's arithmetic model.
The faster construction uses ranked subset convolution and obtains `O(2^n n^3 log^2 n log log n)` for rank-width.
Both retain an exponential dependence on the graph's vertex count.
The new Python routine implements the direct recurrence, not the faster convolution method.
An arXiv title search did not identify an arXiv version of this paper.
The author-hosted PDF was therefore read using the pdf-skill fallback; no local Python PDF script was needed.
The author-hosted preprint and journal record support the complexity statements. [Oum, author preprint](https://mathsci.kaist.ac.kr/~sangil/pdf/2008exp.pdf), [journal article](https://doi.org/10.1016/j.ipl.2009.03.018).

| Implementation | Verified scope | Use in this audit |
|---|---|---|
| [`rw` 0.10](https://sourceforge.net/projects/rankwidth/files/) | C implementation of the direct subset recurrence; exact width and decomposition; GPL-2.0-or-later | Downloaded, compiled with a small bounded driver, and applied to 22 matrices. |
| [`hmyuuu/RankWidthSolver.jl`](https://github.com/hmyuuu/RankWidthSolver.jl) | Exact rank-width; separate exact linear rank-width; heuristic decomposition/ordering paths; multiword cut oracle | Source inspected at `a3b9641359a9dbed5a2ffb6989a15ac0ffa59c85`; not executed because no Julia runtime was installed. |
| [Friedmanský, 2012](https://is.muni.cz/th/tgow6/) | Primary thesis catalog describes an exponential implementation and lists `rwd.cpp` and executable/source archives | Catalog verified. Direct source retrieval returned a JavaScript proof-of-work page, so implementation details and runtime are not claimed as verified. |
| [`Gericom/RankWidthApproximate`](https://github.com/Gericom/RankWidthApproximate) | Simulated annealing that emits a subcubic tree; no certified approximation ratio or optimality proof from a run | Applied at commit `9a4743a1e0f55302ce1438a22f630eb35f0f96ab`; every emitted edge label replayed. |
| [`sangiloum/rwd2`](https://github.com/sangiloum/rwd2) | Rank-width-at-most-two oracle and obstruction-catalog computations | Primary repository reviewed. This threshold-specific package is not a general solver for widths around 20–40. No run performed. |
| [`twalgor/bw`](https://github.com/twalgor/bw) | Exact ordinary graph branchwidth; decomposition leaves are graph edges | Primary repository reviewed. Its graph edge-boundary function is not automatically the binary column-matroid connectivity required here. No unsupported substitution was made. |

The Julia source uses a default `max_n=20` for exact rank-width and a UInt64 subset representation for that routine.
Its exact linear rank-width routine has `O(n 2^n)` subset transitions.
Its general graph storage and cut oracle support more than 64 vertices through multiple words.
These are different capabilities; multiword graph support does not establish practical large exact search.
The retrieved repository has no LICENSE file, so its code was not copied into this repository.

Gericom was built with a portable .NET 8 SDK under the project's `temp/` directory.
The recorded portability patch changes the target to `net8.0`, uses `AnyCPU`, and limits `Parallel.ForEach` to one worker.
The rank and annealing algorithms were unchanged.
Apply the saved zero-context portability patch from the upstream project directory with `git apply --unidiff-zero`.
Its replay was checked byte-for-byte against the sources used to build the executable; see `portability_patch_validation.json`.
The wrapper preserves isolated vertices through diagonal DIMACS records, which never cross a cut.
It rejects malformed trees and checks each DOT edge's rank against the original loop-free graph.
The interchange follows the audited approach already used by `DecisionDiagramDecoder-github`.

## What the 32-vertex limit means

In the inspected `rw` source, `subset_t` is `uint_least32_t` and `MAX_VERTICES` is 32.
The full-set lookup also contains the literal `0xffffffff >> (32-n)`.
Changing only the typedef is therefore insufficient.
More importantly, its width and witness tables contain one entry for each subset.
With one-byte width entries and four-byte witnesses, 32 vertices already require 20 GiB for those tables alone.
A 64-bit witness variant at 33 vertices would require 72 GiB.
The number of split transitions remains exponential even when these tables fit.

The new graph and tree functions use arbitrary-size Python bitsets and were checked on 320 columns and 160 syndrome-row bits.
The direct exact routine is deliberately bounded: default 18 vertices, 256 MiB for its packed tables, 250 million worst-case split evaluations, and a wall-clock deadline.
It chooses 32- or 64-bit witness entries and explicitly refuses beyond the packed exact routine's 64-vertex representation ceiling.
In practice, the resource guards apply much earlier.
This ceiling does not apply to the graph oracle, tree validation, or heuristic witnesses.

Disconnected components give a legitimate structural escape from a limit on total vertex count.
Rank-width of a disjoint union is the maximum component rank-width: restriction supplies the lower bound, and joining component trees introduces rank-zero cuts.
A synthetic 320-column union of 160 independent parallel pairs was certified exactly by 160 two-vertex solves.
This is a validation of the reduction, not an exact large QEC benchmark result.

## Small exact results

The two independent direct-DP implementations agreed on all 22 tested matrices.
Each completed solver returned a tree that was replayed on the original column matrix.
The largest direct solve had 16 vertices; the Python packed tables occupied 393,216 bytes.
Across all 22 matrices, measured Python-DP time was about 1.82 seconds, and upstream-driver wall time was about 0.87 seconds.
These are local validation timings, not isolated-core performance benchmarks.

| Saved instance | Columns | Exact width of H | Exact widths of `[H; l_i]` |
|---|---:|---:|---|
| `wjh_hcc_00_n4`, full | 4 | 1 | 1 for both logical rows |
| `wjh_hsc_00_n6`, full | 6 | 1 | 2 |
| `surface_d3`, collapsed | 9 | 2 | 1 |
| `wjh_surface_d3`, collapsed | 9 | 2 | 1 |
| `wjh_superdense_d3`, collapsed | 10 | 2 | 3 |
| `wjh_midout_d3`, collapsed | 14 | 2 | 3 |
| `wjh_hcc_01_n16`, full | 16 | 2 | 2 for all eight logical rows |

The collapsed instances retain their relaxation status.
These width certificates do not establish equality between a collapsed distance and the original circuit distance.

## Larger constructive witnesses

The table compares the saved best ordering's caterpillar with the smallest H-width found in this bounded audit.
Ties choose the smaller actual J.
All values refer to H alone; this table is not an allocation plan for a logical distance query.

| Instance | Columns | Caterpillar width / J | Best observed tree width / J | Method |
|---|---:|---:|---:|---|
| `code_bb72`, full | 72 | 16 / 17 | 11 / 15 | Gericom, seed 17 |
| `code_bb90`, full | 90 | 23 / 24 | 21 / 31 | Balanced tree / NNI |
| `code_bb108`, full | 108 | 28 / 29 | 27 / 33 | NNI |
| `code_bb144`, full | 144 | 30 / 31 | 29 / 35 | NNI |
| `bb90_r10`, collapsed | 225 | 34 / 35 | 32 / 49 | NNI, target 0 |
| `routing_90`, collapsed | 270 | 35 / 36 | 34 / 39 | NNI |
| `code_sdbb_200`, full | 200 | 40 / 40 | 38 / 60 | Gericom, seed 17 |
| `wjh_hcc_09_n168`, full | 168 | 30 / 30 | 28 / 44 | Gericom, seed 17 |
| `wjh_hsc_09_n252`, full | 252 | 29 / 30 | 28 / 31 | NNI |
| `wjh_qt_144_2_13`, full | 144 | 40 / 41 | 35 / 54 | NNI from balanced tree |

Ten Gericom runs used seed 17 and a 10-second search limit.
Two additional runs on BB90 and BB144 used seed 37 and 15 seconds; neither improved the best width.
The sibling NNI implementation used seed 17, a 5-second limit, a 200,000-move cap, and a 10,000-entry rank cache.
The initial run stops after reaching one less than its starting width.
Four refinement cases used target zero; their recorded elapsed times were below one second.
The sibling's legacy join proxy guides its search, while the exact matroid J is independently reported here.
All CPU-intensive experiments ran with at most two concurrent workers and numerical-library thread counts of one.
No large dense-distance run was started by this script.

BB72 is a positive result for both interface size and join work.
For most other cases, the narrowest found tree has a worse join exponent than the caterpillar.
For example, the collapsed BB90 width improves by two bits, but J increases from 35 to 49.
That witness does not establish a practical dense solve on this desktop.
A failed or expensive witness also does not prove that every decomposition is infeasible.
Actual augmented-table and distance validation is recorded separately under `results/rw_tree_audit_20261021/integration/`.

## Reproduction and validation

The records under `results/rw_tree_audit_20261021/rw/` retain source hashes, input hashes, column-basis choices, baseline permutations, all flat tree witnesses, external stdout/stderr, exact certificates, search parameters, and a portability patch.
The main ten candidate files are supplemented by `nni_refined/` and `seed37/`.
The source archives and portable runtime are retained under `../temp/rw_tree_audit_20261021/rw/` relative to this repository.
No global dependency installation is required.

`scripts/rankwidth_audit.py` reconstructs the graph from a saved input, runs the selected bounded search, and independently evaluates the result.
The optional sibling NNI adapter uses that repository's Python 3.11–3.12 environment; the new core module retains this repository's Python 3.9-compatible syntax and popcount fallback.
`scripts/rankwidth_exact_audit.py` checks the saved small cases against `rw` 0.10 through `scripts/rw_exact_driver.c`.
The manifest records the external build and source details.

The rank-width tests exhaustively compare all cuts for small matrices, compare exact DP against all six-leaf binary trees, enumerate compatible syndrome pairs, check dependent and zero rows, verify cyclic/invalid witness rejection, reject fractional bitsets, check external-label tampering, and exercise 320-column bitsets and the disconnected exact reduction.
Run them with `python -m unittest discover -s tests -p test_rankwidth.py -v` from the repository root.
