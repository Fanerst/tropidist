# Dense DP on binary trees

The distance library now supports general binary-tree realizations through `cdist.tree_dp`. The existing trellis engine is retained. The new engine solves the same exact unit-cost problem, including arbitrary affine targets; it is not a width-truncated relaxation.

## Interface and correctness

A tree is an original column index at a leaf and a pair of child trees at a join. `CompiledTreeDP(M, tree).run(t)` minimizes Hamming weight subject to `M e = t`. `tree_min_distance_for_mask(H, L, mask, tree)` evaluates one logical parity query. `scripts/experiments_tree_dense.py` profiles or executes all observable rows and takes their minimum; an explicitly selected observable is labelled separately.

For each query, `M = [H; l_i]` and `t = [0; 1]`. A particular solution shifts the target to zero and changes the leaf costs. The state at a cut S is `im(M_S) ∩ im(M_notS)`, with exactly `2^lambda_M(S)` values. The tree engine uses a minimal augmented boundary even when adding the logical row reduces a cut rank. This differs from the older trellis representation, which retains the zero-target H basis and an additional logical row.

At a join with children A and B and exterior C, the compatible-pair exponent is

```text
J = rank(M_A) + rank(M_B) + rank(M_C) - rank(M).
```

Every compatible pair is enumerated once in Gray-code order. The single-thread C kernel allocates no pair tensor. The Python planner selects a depth-first child order and reserves one arena holding both children, their parent, and pending siblings. In-place compaction requires no proportional scratch.

## Resources and safeguards

- The cost dtype is the smallest unsigned type containing N+1, used as infinity. It is uint8 for N≤254, uint16 for N≤65534, and widens thereafter.
- Preflight reports actual augmented edge dimensions, each J, total compatible pairs, largest single table, complete live arena, and two uint64 map arrays. Python plan storage is reported separately; dense payload is not process RSS.
- Memory and work limits are checked before exponential allocation. A conservative polynomial compilation limit and wall-clock checks also apply.
- Defaults permit a 256 MiB dense payload and 100 million compatible pairs per query. Resource rejection or a time limit does not return an exact distance.
- This task used an aggregate budget of six CPU execution threads and 10 GiB experimental RAM, below half of the 15-core, 24 GiB desktop. The two delegated tasks each had a two-thread/four-GiB allocation; integration used at most two single-thread processes and two GiB. No previous stopped large run was resumed.

## Applied decomposition algorithms

The graph supplied to graph rank-width solvers is the fundamental graph of H, whose vertices are the original columns. Its cut ranks equal the column-matroid connectivity. The unmodified upstream `rw` 0.10 direct subset DP was cross-checked against an independent bounded Python implementation on 22 small matrices. General graph/tree operations have arbitrary-size bitsets; a 320-column disconnected example was solved exactly through two-vertex components. This does not make a general exponential exact solve on 72 or more columns practical.

For ten larger representative inputs, the experiment used Gericom simulated annealing and the existing sibling-repository NNI search. All emitted cuts were replayed exactly. The saved candidates include the previous ordering as a caterpillar. These are achieved upper bounds, not exact rank-width certificates. The solver review, primary sources, exact certificates, and limitations are in [RANKWIDTH_SOLVER_REVIEW.md](RANKWIDTH_SOLVER_REVIEW.md).

## Effect on actual table sizes

Every logical row was profiled for 72 saved candidate records (60 distinct instance/tree pairs). This is a ten-instance comparison, not a new scan of all 186 benchmark instances. The table selects the candidate minimizing the actual largest augmented table, then live memory, then work. The smallest-table tree need not be the best tree to execute.

| Instance / variant | Old trellis table | New largest table | New complete dense workspace | Max J |
|---|---:|---:|---:|---:|
| bb90_r10 / collapsed | 32 GiB | 8 GiB | 12 GiB | 52 |
| code_bb108 / full | 1 GiB | 256 MiB | 512 MiB | 40 |
| code_bb144 / full | 4 GiB | 1 GiB | 2 GiB | 36 |
| code_bb72 / full | 256 KiB | 4 KiB | 12.3 KiB | 17 |
| code_bb90 / full | 16 MiB | 4 MiB | 5.5 MiB | 33 |
| code_sdbb_200 / full | 2 TiB | 512 GiB | 1.5 TiB | 62 |
| routing_90 / collapsed | 128 GiB | 64 GiB | 128 GiB | 40 |
| wjh_hcc_09_n168 / full | 2 GiB | 512 MiB | 1 GiB | 46 |
| wjh_hsc_09_n252 / full | 2 GiB | 512 MiB | 1 GiB | 33 |
| wjh_qt_144_2_13 / full | 4 TiB | 64 GiB | 76 GiB | 54 |

The selected collapsed BB90 workspace is exactly 12,893,291,328 bytes, slightly more than 12 GiB even before Python and interpreter memory. Its largest join requires `2^52` compatible pairs. It therefore remains outside the resource budget despite the substantial single-table reduction.

None of the four selected cases whose old single table exceeded 24 GiB becomes a practical solve under this task's half-machine constraint. This is a conclusion about these saved trees and this implementation, not a lower bound excluding all better decompositions.

The HCC n168 tree illustrates the runtime tradeoff: its largest actual table drops from 2 GiB to 512 MiB, but a join has J=46. Only structural profiling was performed for this tree. A separate work-minimizing candidate is retained in `integration/summary.json`; minimizing rank-width alone is insufficient.

## Completed distance checks

| Input | Tree | Full distance | Max single table | Max complete dense payload | Compile + solve, seconds |
|---|---|---:|---:|---:|---:|
| code_bb72 / full | caterpillar | 6 | 128 KiB | 256 KiB | 0.0650 |
| code_bb72 / full | gericom_annealing | 6 | 4 KiB | 12.3 KiB | 0.0262 |
| code_bb90 / full | sibling_nni_caterpillar | 10 | 8 MiB | 16 MiB | 1.9791 |

All these runs completed every observable and agree with the previous exact distances. The old BB72 trellis reserved 262,144 bytes. The new engine on the same ordering's caterpillar needs 262,434 bytes of dense workspace, while the annealed tree needs only 12,560 bytes. This controlled comparison attributes the main memory reduction to branching, rather than only to a different boundary representation.

The tree engine is not claimed to be faster than the optimized trellis. For BB72 its measured compile-and-solve time is about 0.026 s, compared with about 0.014 s for the previous trellis run. Decomposition search time is additional. For the chosen BB90 tree, a smaller single table does not reduce the complete workspace materially relative to the older 16 MiB trellis buffer.

The independent tree demonstrations additionally verify a branching BB72 tree, surface_d3, and wjh_hcc_02_n32 against the trellis. The regression suite checks 2728 exhaustive affine queries, 160 random logical queries, C/Python agreement, dtype widening through distance 300, and resource refusal before allocation. The rank-width suite verifies cut identities, exact optimality against all small binary trees, external witness replay, and bitsets beyond 32 vertices.

## Reproduction

From the repository root, profile the saved BB72 tree without allocating a dense table:

```sh
python scripts/experiments_tree_dense.py \
  --input results/dense_audit_20261021/inputs/code_bb72/full.json.gz \
  --candidates results/rw_tree_audit_20261021/rw/code_bb72__full/candidates.json \
  --method gericom_annealing --out results/tree_bb72_profile.json
```

Add `--run` to execute all observables under the default memory, work and time limits. Use `--observable i` only for a deliberately partial query. The saved trees avoid rerunning external searches. Optional external solvers remain in project `temp/`; the tree executor itself requires only the repository's Python/NumPy/C environment.
