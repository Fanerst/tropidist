# Exact dense tree realization: validation evidence

The implementation is `cdist/tree_dp.py`, with an allocation-free,
single-thread C join kernel in `cdist/tree_dp.c`.
`scripts/demo_tree_dp.py` replays a saved input and records every observable
query, its resource profile, a flat postorder tree witness, source/input
checksums, and the legacy trellis comparison.
All results here use unit fault costs and the unchanged condition
`H e = 0, L e != 0`.
Each reported distance is the minimum over **all** logical rows.

## Correctness and arithmetic

For each logical query, the augmented matrix is `[H; l]`, with target
`[0; 1]`.
A particular solution shifts the constraint to a homogeneous one.
The cut state is exactly the intersection of the two augmented column spans.
The shift changes leaf costs, not the state spaces or joins.
No independence assumption on detector rows, logical rows, or columns is used.
Infeasible targets, zero columns, loops, coloops, and repeated columns are
handled directly.

At a binary join, compatible child pairs map onto the parent interface.
The kernel is the common child-span intersection.
The exact join exponent is therefore
`J = rank(M_left) + rank(M_right) + rank(M_outside) - rank(M)`.
The kernel enumerates exactly `2**J` candidate pairs; it does not allocate a
pair tensor.
The source module includes the induction establishing the table invariant
and the join argument.

Costs use the smallest unsigned integer type that can represent `N+1`,
where `N` is the number of columns; `N+1` represents infinity.
Thus, `uint8` applies only through 254 columns, and `uint16` applies through
65534 columns.
Tests with exact distances 254, 255, and 300 check the first dtype boundary.

## Memory and work accounting

`peak_live_table_bytes` is the complete numeric table arena.
The schedule explicitly includes both child tables and the newly allocated
parent table, plus any pending sibling tables.
The better of the two depth-first child orders is selected at each join.
After a join, `memmove` compacts the evaluation stack without proportional
scratch, including when source and destination overlap.

`scratch_bytes = 16 * max_join_dimension` is the payload of two `uint64`
generator-mask arrays, allocated once and reused.
`peak_dense_bytes` is the sum of this scratch and the arena.
For every completed solve, the executor checks that observed live payload
and actual allocated numeric payload equal the preflight values.
These are numeric payload bytes, **not process RAM**.
Python plan storage is reported separately using recursive object-size
accounting; array-object headers, interpreter/libraries, compiler activity,
and allocator overhead are outside the dense-payload figure.
Each saved demonstration also records the peak RSS of its fresh process.

The independent compilation guard uses a conservative polynomial-storage
bound and can reject a case whose actual compilation would fit.
Execution rejects unaffordable memory or aggregate candidate-pair work
before allocating the arena.
Execution time is checked between nodes and between chunks of at most
`2**20` C candidate pairs.
Resource rejection never returns a partial distance as exact.

## Completed demonstrations

| Input | Tree | Observables | Distance | Internal/internal joins | Maximum dense payload |
|---|---|---:|---:|---:|---:|
| synthetic 8-column example | balanced | 1 | 2 | 3 | 86 bytes |
| code_bb72/full | balanced blocks of 4, then a comb | 12 | 6 | 35 | 164160 bytes |
| surface_d3/sector | balanced saved order | 1 | 3 | 22 | 416 bytes |
| wjh_hcc_02_n32/full | balanced saved order | 12 | 4 | 15 | 720 bytes |

Every observable result agrees with the existing C trellis.
The surface-sector input retains the previous audit's exact-sector
interpretation; this validation does not strengthen any relaxation.
The trees are concrete witnesses, with no optimal-width claim.
These examples establish execution on genuinely branching trees; they do
not by themselves attribute a speed or memory improvement to branching.
Adding the logical row can decrease a cut dimension, and the new affine
realization can therefore save states even on a caterpillar.

## Regression command

Run `python tests/test_tree_dp.py -v` from the repository root.
The suite checks all 341 binary matrices with at most four columns and two
rows, with eight targets each (2728 affine queries); 160 reproducible random
logical queries on comb, balanced, and random trees; independent brute force;
the existing C trellis; and the Python tree reference.
It also checks arbitrary affine targets, the decreasing augmented-rank
example, malformed trees, a 1300-leaf comb, dtype widening, Gray-code chunk
restarts, exact arena accounting, and resource refusal before `np.empty`.
No prior stopped large DP run was resumed.
