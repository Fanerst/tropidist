# Dense DP, enumeration and branch and bound

Question: can dense Rank DP be given an enumeration-like strategy, and can branch and bound be
merged into it?

Numbers come from `phase4/results/*.json` (probes, local) and `results/phase4/*.json` (server runs).
Earlier parts of the project: [BB_CIRCUITS.md](BB_CIRCUITS.md), [PAPERS.md](PAPERS.md).

## Answer

**The two are the same recursion, and branch and bound is the bridge.** Min-plus Rank DP keeps, for
each boundary state, the cheapest way to reach it. Stored densely this costs 2^width and does not
care about the distance; stored sparsely and cut off at weight K it is the weight-bounded
enumeration, which does not care about the width but grows like b^K. Branch and bound sits between
them: keep a state only if `cost so far + lower bound on the rest <= K`. The lookup table of all
k-column sets that the enumeration already uses is such a bound, exact but only for the last k
steps. What was missing is a bound for the steps before that.

**Measured: that bound is where all the time goes.** On the time-collapsed BB288 problem at
threshold 15, 99.7 to 100 % of the 3 × 10^11 nodes in the last three levels have a residual syndrome
that cannot be cancelled within the remaining budget. The test in use rejected under 1 % of them
at the two levels above the lookups.

**Dense tables are not the right bound here; a covering bound is.**

| bound on the completion | cost per node | nodes pruned at depth 9 / 10 (BB288, K = 15) |
|---|---|---:|
| weight test `|residual| <= wmax · R` (old) | a popcount | under 1 % / under 1 % |
| dense min-plus tables on 24-row patches, best single patch | a table read | 0 % / 0.2 % |
| the same, added over a partition with split costs | six table reads | 0 % / 27 % |
| dominance by low-weight stabiliser sets | counters | 7 to 12 % fewer nodes overall |
| **covering bound** (new) | about 0.3 to 1 µs | **77 to 85 % / 99 to 100 %** (92 to 94 % at depth 9 with the ascent step) |
| covering LP solved exactly | an LP | 96 to 99 % / 100 % |
| LP with parity constraints | a larger LP | 100 % / 100 % (88 % already at depth 8) |

**Effect.** For BB codes the search now grows by a factor of about 6 per unit of weight instead of
about 12, with a lookup table 170 times smaller:

| problem | threshold | before | with the covering bound |
|---|---:|---|---|
| BB288 collapsed, Z | 15 | 2.96 × 10^11 nodes, 184 s, table of 10^10 entries | 7.4 × 10^9 nodes, 67 s, table of 5.9 × 10^7 entries |
| BB360 collapsed, Z | 16 | 3.36 × 10^12 nodes, 5209 s (80 threads) | 4.2 × 10^10 nodes, 658 s (96 threads) |
| BB360 collapsed, X | 16 | 2.31 × 10^12 nodes, 3538 s | 3.3 × 10^10 nodes, 519 s |
| BB360 code distance | 23 | 2.92 × 10^11 nodes, 1289 s | 3.0 × 10^9 nodes, 41 s |
| BB756 code distance | 24 | not finished in 1 h (10^12 nodes) | 2.4 × 10^9 nodes, 33 s |

The whole BB288 Z chain (collapsed distance 15, 1440 minimum solutions in 10 orbits, none lifts,
certified lower bound 16) is reproduced in 95 s.

<!-- NEW-RESULTS:BEGIN -->
**New bounds obtained with it** (state of 2026-10-03, 17:00; all exhaustive, files in
`results/phase4/` and `logs/server/phase4/`):

| quantity | before | now | run |
|---|---|---|---|
| BB756 [[756,16,≤34]] code distance | ≥ 24 | **≥ 28** | weights 24 to 27 excluded in 33 s, 91 s, 305 s and 716 s on 64 threads; paused, can resume at 28 |
| BB360 circuit distance, X basis | 17 – 21 | **19 – 21** | collapsed problem: no solution up to weight 17 (50 min on 96 threads); at weight 18 (1.1 × 10^12 nodes, 4 h) 4380 solutions in 27 orbits, none of which lifts to the circuit |
| BB360, Z basis, distance of the one-round window | 18 – 21 | **exactly 21** | weights 18, 19, 20 excluded in 46 s, 167 s, 667 s on 64 threads; the weight-21 fault set is replayed in Stim |
| BB360, X basis, distance of the one-round window | 19 – 21 | **exactly 21** | weights 19, 20 excluded in 95 s, 358 s; weight-21 fault set replayed in Stim |
| BB360 circuit distance, Z basis | 17 – 21 | 17 – 21 | unchanged so far; see below |

The one-round window result says that the weight-21 fault set found earlier by randomised search is
optimal among fault sets confined to one round. It does not by itself raise the circuit lower
bound, because lighter fault sets spread over several rounds are not excluded by it.

Not pursued further: the enumeration of all weight-17 collapsed solutions of BB360 Z (needed for
Z ≥ 18) was stopped after 2.8 hours when the work moved to sizes within exact reach, and the BB756
run was not resumed.
<!-- NEW-RESULTS:END -->

**It is not a general win.** On the mitten problems the bound halves the node count but costs four
to nine times more time at the thresholds that can be reached; see "Where it does not help".

## One recursion, three ways to run it

Fix an order in which columns are decided. A partial choice A has cost |A| and a state: the
residual syndrome `sigma = H A` together with the logical label. Everything that can still happen
depends on A only through the state.

| | states kept | cost | limited by |
|---|---|---|---|
| dense Rank DP | all 2^width boundary states, one byte each | N · 2^cutrank | width (97 bits for collapsed BB288) |
| enumeration | the states actually reached with cost <= K, one at a time | about b^(K - k) | distance (b is about 12 for BB, 35 for mitten) |
| branch and bound | reached states with `cost + h(state) <= K` | depends on h | quality of the bound h |

Two things could in principle connect them:

1. *Merging*: enumeration visits a state once per way of reaching it, a DP once. Here it does not
   matter. The residual of a prefix can almost never be reproduced by a different, equally light
   set: in 93 to 97 % of sampled nodes of the collapsed BB144 search the cheapest set with the
   same syndrome is the prefix itself (`phase4/headroom.py`). That is what a large distance means,
   and it is also why a truncated sparse DP would store close to one state per enumerated prefix.
2. *Bounding*: this is where the room is. A node at depth a with budget R = K - a is useless as
   soon as its residual needs more than R further columns. For depth below K/2 nothing can be
   said from the residual alone (the prefix itself has only a columns), but beyond K/2 almost
   every node is dead:

   | depth | budget R | nodes at that depth | dead | rejected by the old test |
   |---:|---:|---:|---:|---:|
   | 9 | 6 | 2.0 × 10^9 | 99.7 % | under 1 % |
   | 10 | 5 | 2.3 × 10^10 | 100 % | under 1 % |
   | 11 | 4 | 2.7 × 10^11 | 100 % | 23 % |

   (BB288 collapsed, Z, K = 15; Knuth-weighted random walks through the search tree, 200 per
   depth; the node estimates agree with the counts of the real run.) A perfect residual-only bound
   would stop the search near depth K/2 and take the square root of the work.

## The bounds that were tried

All are admissible: they never exceed the true completion cost, so no solution is lost.

### Dense min-plus tables on row patches ("tropical pattern databases")

For a set P of p rows, one dense DP over 2^p states gives `T_P[x]`, the minimum number of columns
whose syndromes restricted to P add up to x (one in-place pass
`T[s] = min(T[s], T[s ^ v] + c)` per distinct projected column). Forgetting the other rows is a
relaxation, so `T_P[sigma restricted to P]` is a lower bound for any budget, not only the last k
steps. With a partition of the rows and each column's cost split among the patches it touches, the
table values can be added.

This is the direct way to put dense Rank DP inside the enumeration, and on these problems it is
weak (`phase4/pdb_probe.py`, 24-row patches, five partitions, 16 MB per table):

| depth | budget | best single patch | additive | covering bound |
|---:|---:|---:|---:|---:|
| 9 | 6 | 0 % | 0 % | 77 % |
| 10 | 5 | 0.2 % | 27 % | 99 % |
| 11 | 4 | 32 % | 78 % | 100 % |

Two reasons. A BB column touches 2.3 to 2.7 patches on average, however the rows are grouped, so
most of every column falls outside any one table. And a precomputed table cannot know which
columns the search has already ruled out at this node, which turns out to be the decisive
information (next section).

### Dominance by low-weight stabiliser sets

If s is a set of columns with zero syndrome and zero logical label, a minimum solution contains at
most half of it (otherwise exchanging the two halves gives a lighter one). The existing pair
exclusions are the case |s| = 3. `Searcher.kernel_sets` enumerates all such sets up to a weight and
`Searcher.set_kernel` forbids the rest of a set once a prefix holds half of it. Correct (tested
against brute force) and cheap to state, but it removes only 7 to 12 % of the nodes on BB144 with
all 330 156 sets up to weight 8, and the bookkeeping costs more than it saves.

### Covering bound

At a node, call a column *free* if the search has not forbidden it (it is not in the prefix, not an
earlier sibling on the path, not excluded by symmetry rank or by a pair exclusion). The completion
B of any solution that passes through the node in canonical order uses free columns only. B must
also touch every defect row of the residual. Hence

    |B| >= min { sum_f x_f : sum over free f at row r of x_f >= 1 for every defect r, x >= 0 },

and by LP duality any weights y_r >= 0 on the defects with `sum of y_r over the defects of f <= 1`
for every free column f give `|B| >= sum_r y_r`. Two cheap choices of y:

1. `y_r = 1 / m_r`, where m_r is the largest number of defects that a single free column at r
   covers. A column covering o defects then carries at most o · (1/o) = 1.
2. One greedy ascent pass: go through the defects, fewest free columns first, and raise each y_r
   until some column at r is tight.

The node is discarded if the bound exceeds the budget R. Why it is so much stronger than the old
test, which is the same inequality with every m_r replaced by the largest column weight: at depth
10 the residual has about 21 defects, and although a hook column has weight 6, the free columns at
a typical defect cover only 2 defects. The old test says 21/6 = 4 columns might do; the covering
bound says 21/2 = 10.

The bound can exceed the depth, which a bound built from the residual alone never can, because the
cheap way of cancelling the residual, undoing the prefix, uses forbidden columns.

Cost: one pass over the free columns at each defect, with early exit as soon as the partial sum
decides. It is evaluated only above the lookup levels (R > k), where the table is not yet exact.

Sampled comparison of the variants, with the LP optimum and with an LP that also requires every
newly created defect to be touched twice (`phase4/prop_probe.py`, 120 walks per depth):

| depth | budget | first dual | + ascent | covering LP | LP with parity |
|---:|---:|---:|---:|---:|---:|
| 7 | 8 | 0.1 % | 2.9 % | 9.4 % | 52 % |
| 8 | 7 | 42 % | 49 % | 55 % | 88 % |
| 9 | 6 | 83 % | 94 % | 99.5 % | 100 % |

## Results of the search with the covering bound

Server: 2 × EPYC 9654, shared with other jobs during these runs. Baselines are the earlier runs of
this project. "Nodes" counts every node entered, including those the bound rejects.

BB288 collapsed, Z basis, 128 threads:

| K | no bound, table k = 3 | no bound, table k = 4 | covering bound, table k = 3 |
|---:|---|---|---|
| 12 | 2.24 × 10^9, 1.3 s | | 3.6 × 10^7, 0.3 s |
| 13 | 2.56 × 10^10, 13 s | | 2.1 × 10^8, 1.7 s |
| 14 | 2.82 × 10^11, 138 s | 2.60 × 10^10, 19 s | 1.23 × 10^9, 8 to 11 s |
| 15 | | 2.96 × 10^11, 184 s | 7.4 × 10^9, 67 s |

Tables: 5.9 × 10^7 entries for k = 3, 1.0 × 10^10 for k = 4. The node ratio doubles with every
unit of K (62, 122, 228 against the k = 3 baseline). Both variants report the same 36 anchored
weight-15 solutions.

BB360 collapsed (old: k = 4 table with 2.5 × 10^10 entries, 80 threads; new: k = 3 table with
1.2 × 10^8 entries, 96 threads per basis, both bases at once):

| basis | K | old nodes, seconds | new nodes, seconds |
|---|---:|---|---|
| Z | 14 | 2.59 × 10^10, 51 | 1.27 × 10^9, 19 |
| Z | 15 | 2.98 × 10^11, 572 | 7.2 × 10^9, 116 |
| Z | 16 | 3.36 × 10^12, 5209 | 4.2 × 10^10, 658 |
| X | 14 | 1.97 × 10^10, 29 | 1.03 × 10^9, 14 |
| X | 15 | 2.15 × 10^11, 349 | 5.8 × 10^9, 89 |
| X | 16 | 2.31 × 10^12, 3538 | 3.3 × 10^10, 519 |

In the Z basis the new run finds the same 180 weight-16 solutions (one translation orbit), none of
which lifts to the circuit: lower bound 17, as before, in 810 s in total.

Code distance (faults before the first round, Z basis):

| code | K | old nodes, seconds | new nodes, seconds |
|---|---:|---|---|
| BB360 | 22 | 1.29 × 10^11, 810 | 1.01 × 10^9, 13 |
| BB360 | 23 | 2.92 × 10^11, 1289 | 3.0 × 10^9, 41 |
| BB756 | 24 | more than 10^12, stopped at 3600 | 2.4 × 10^9, 33 |

BB360 gives distance 24 again, with the weight-24 operator replayed in Stim.

## Where it does not help

Mitten [[300,60,14]], X basis, K = 9, table k = 3, 64 threads: 9.2 × 10^9 nodes in 4.8 s without the
bound; 7.7 × 10^9 nodes in 18.6 s with the first dual; 4.6 × 10^9 nodes in 41 s with the ascent.
The rows of that problem have about 68 columns each and columns of weight up to 18, so one
evaluation costs 3 to 9 µs while a table lookup costs 30 ns, and the bound only starts to reject
nodes one level above the lookups. The exact covering LP would reject 67 % one level higher
(`phase4/cover_probe.py`), which the cheap dual solutions do not reach (0.4 % and 8 %). The bound
is therefore an option, off unless requested, and meant for BB-type problems.

## What dense DP is still for

- The lookup table of the enumeration is a min-plus table in sparse form: the exact environment
  of the last k columns. That part of the hybrid already existed and remains necessary.
- Dense DP remains the exact method when the width is small (collapsed BB72 and BB90, code
  capacity problems).
- As a bound inside the enumeration it loses to the covering bound on these codes, for the two
  reasons given above. It may do better on geometrically local codes, where a column falls into
  one patch; that was not tested.

## Open directions

1. **A cheap parity-aware bound.** The LP with parity constraints rejects 88 % of the nodes at
   depth 8 and 52 % at depth 7 where the dual ascent rejects 49 % and 3 %. In the LP solutions the
   effect is diffuse (heavy hook columns that cover two defects but create four are discounted);
   forbidding columns that would create an uncancellable defect captures none of it
   (`phase4/prop_probe.py`). Any nonnegative multipliers (y, z) give a valid bound after scaling
   by the largest column load, so a few iterations of a first-order method are a candidate.
2. **Cheaper evaluation.** 0.3 to 1 µs per node against 30 to 60 ns for a lookup. The inner loop is
   a popcount over the columns of a row and would vectorise (AVX-512 VPOPCNTQ is available on the
   server).
3. **Symmetry-reduced lookup tables.** Storing one entry per translation orbit divides the table by
   the group order (144 for BB288), which buys one more exact level at the same memory.
4. **Mitten-type problems** need the LP-level bound or a different branching rule; the present
   bound is too weak one level up and too expensive per node.

## Reproduce

    .venv/bin/python tests/test_kernel.py            # bound, dominance and kernel enumeration against brute force
    .venv/bin/python tests/test_enum_cover.py        # enumeration of all solutions unchanged by the bound (BB144, up to d + 2)
    .venv/bin/python phase4/headroom.py bb288_r18_Z:collapsed 15 3 11,10,9 200 0 0
    .venv/bin/python phase4/cover_probe.py bb288_r18_Z:collapsed 15 6,7,8,9,10,11 150
    .venv/bin/python phase4/pdb_probe.py bb288_r18_Z:collapsed 15 9,10,11 150 24
    .venv/bin/python phase4/bench_kernel.py bb288_r18_Z:collapsed 3 11,12 0,s:0,c:0   # no bound / first dual / ascent
    .venv/bin/python scripts/run_deep.py circuits/bb288_r18_Z.stim out.json --cover --skip-ub --k-table 3 --kmax 16
    .venv/bin/python scripts/run_window.py circuits/bb360_r24_Z.stim out.json 0 0 24 4 0 18 1  # code distance with the bound

In code: `Searcher.search(K, cover=True)` (ascent), `cover="simple"` (first dual only), or
`search.distance(..., cover=True)`.

| file | content |
|---|---|
| `cdist/gmitm.c` | `cover_prune` (the bound), `kd_take` / `kd_undo` (dominance), kernel enumeration mode, `gm_cancel_cost` |
| `cdist/search.py` | `cover=` option, `set_kernel`, `kernel_sets`, automatic task depth |
| `phase4/common.py` | problem cache, Knuth random walks through the search tree, exact completion cost |
| `phase4/headroom.py` | fraction of dead nodes per depth |
| `phase4/cover_probe.py`, `prop_probe.py`, `dual_heur_probe.py` | bound variants against the LP at sampled nodes |
| `phase4/pdb_probe.py` | dense patch tables as bounds |
| `phase4/bench_kernel.py`, `bench_tasks.py` | node counts and times of the search variants |

## Checks

- 1500 random problems: distance and the complete list of minimum solutions agree with brute force
  for every combination of table size, pair exclusions, kernel sets and bound variant; 600 more on
  700 rows exercise the second code path of the bound (more than 512 rows).
- The bound leaves the enumeration of all solutions up to d + 2 of collapsed BB144 unchanged
  (360, 13 788 and 297 504 solutions).
- The random-walk estimator of node counts agrees with the real run (BB144: 5 / 58 / 673 / 8410
  estimated against 5 / 58 / 680 / 8197).
- BB288 and BB360 end results are identical to the earlier runs, including the number of minimum
  solutions and orbits.
