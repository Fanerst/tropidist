# Circuit distance with Rank DP and tensor networks

Question: can Rank DP or a tensor network (TN) compute the circuit distance, which is better, is it
exact or approximate, and does it work on BB288?

A one-page overview of everything, with representative cases and the state of the tool, is in
[SUMMARY.md](SUMMARY.md). All numbers come from `results/*.json`; the full tables are in [RESULTS.md](RESULTS.md).
A follow-up that applies the same tools to circuits published in recent qLDPC papers is in
[PAPERS.md](PAPERS.md); its second batch also designs syndrome-extraction circuits for codes that
come without one (self-dual bivariate bicycle codes, a GALA code) and gives their exact circuit
distances; its third batch takes circuits from a catalog of 2026 papers (gross-code left-right
circuit, routing codes, STAR schedules, Walking Cat, shift circuits) and settles 249 code distances
that papers give only as estimates. A second follow-up, on combining dense DP, enumeration and branch and bound,
is in [PHASE4.md](PHASE4.md); it adds a covering bound that makes the sparse search grow about 6×
instead of 12× per unit of weight on BB problems.

## Answers

**1. Yes, both can, and the computation is exact.** The distance is the min-plus (tropical) version
of the contraction that Rank DP and TN already do for likelihoods: replace (+, ×) by (min, +) in the
nonnegative representation. In linear form, min-plus Rank DP is the Viterbi algorithm on the syndrome
trellis. It reproduces the code distances of [[72,12,6]], [[90,8,10]] and [[144,12,12]]; a tropical
TN contraction of the same instance agrees; and the ordinary sum-product sweep at small fault weight
gives the same exponent together with the number of minimum-weight logical faults.

**2. Rank DP is the better of the two here.** Its interface is the cut rank of the column matroid,
which does not depend on the check basis, whereas a TN is tied to the checks it is given. On every
BB instance the Rank DP width is 4 to 6 bits below the TN width (17 vs 23 for BB72 code capacity,
97 vs 101 for collapsed BB288), and adding a fault is one byte-wise `min` over the table.

**3. Dense contraction, of either kind, does not reach BB circuits.** The cut rank grows linearly
with the code: 26 / 35 / 40 / 52 / 97 for the time-collapsed BB72 / 90 / 108 / 144 / 288 problems and
66 / 86 / 104 / 138 / 282 for the real multi-round circuits. Dense tables fit only up to the collapsed
BB90 problem (64 GB per observable, 50 s); collapsed BB108 would need 2^42 bytes. Truncating the
width is not a usable approximation: dropping one or two of 30 trellis rows lowers the bound from
5 or 6 to 3 or 4, and further truncation gives 1 or 2.

**4. The approximation that works is a certified relaxation, and it can be closed to an exact
answer.** GF(2) row maps of the detector matrix (CSS sector, time collapse) shrink the problem and
give lower bounds; column subsets (the faults of one round) give upper bounds with a witness. On the
reduced problems the same recursion runs in sparse, weight-bounded form. The two bounds met in
every case tested.

**5. Results.** Exact circuit distance, both bases, for the pinned tesseract-decoder circuits
(SI1000, CZ-compiled, rounds = code distance):

| code | rounds | circuit distance (Z, X) | wall time per basis |
|---|---:|---:|---|
| [[72,12,6]] | 6 | 6, 6 | under 1 s |
| [[90,8,10]] | 10 | 8, 8 | 2 s |
| [[108,8,10]] | 10 | 8, 8 | 2 to 3 s |
| [[144,12,12]] | 12 | 10, 10 | 4 to 5 s |
| [[288,12,18]] | 18 | **16, 16** | 22 to 27 min on 128 threads |

BB288 is 16, not 18. There are weight-16 undetected logical fault sets (16 single-qubit faults after
two-qubit gates within one round); each was inserted into the noiseless circuit and simulated: no
detector fires and observables flip. Every fault set of weight 15 or less is excluded exhaustively.
The earlier attempt in `~/Documents/Research/qec/mld/circuit_distance` had certified 6 to 18 (Z) and
6 to 48 (X) by running a weight-bounded Rank DP on the uncollapsed 18-round problem.

## Method

### Problem

From the undecomposed Stim DEM: columns `(h_j, l_j)` (detector and observable flips of mechanism j),

    d = min { |e| : XOR_j e_j h_j = 0, XOR_j e_j l_j != 0 }.

For these channels (depolarizing, X flips, measurement flips) the number of DEM mechanisms equals
the number of faulty circuit locations: a location's outcomes are closed under multiplication, so
two mechanisms from one location can be replaced by one.

### Reductions

All are GF(2) row maps `H -> P H` or column subsets, so each gives a one-sided bound.

| step | what it does | BB288 size (rows × columns) | effect on the distance |
|---|---|---|---|
| full DEM | | 5184 × 206352 | |
| CSS sector | keep detectors of the memory-basis type | 2736 × 26208 | none (checked: every sector column is itself a mechanism with no other detectors) |
| time collapse | XOR each check's detectors over all rounds | 144 × 720 | lower bound, independent of the number of rounds; 1 to 4 below the truth |
| time fold, period P | XOR over rounds with equal t mod P | 144P × about 1400P | lower bound, tighter (period 3 is exact in 7 of the 8 small cases) |
| window [a, b] | keep faults whose detection events lie in rounds a..b | 144 × 432 for one layer | upper bound; one bulk layer gave the exact value in all 10 cases |

The collapsed rows say that the accumulated data error commutes with every check; its columns are
the single data errors plus three hook classes per check. That is why it is small, and why it is
only a bound: it forgets in which round a check saw a fault.

### Dense mode: min-plus Rank DP (`cdist/trellis.py`, `cdist/viterbi.c`)

For a column order, the interface at cut i is `span(past) ∩ span(future)`, of dimension
`rank(past) + rank(future) - rank(all)`. In minimal span form of the row space exactly that many
rows are active at the cut, so the state is their partial parities and adding fault j is
`T[s] <- min(T[s], T[s xor h_j] + 1)`. Cost: (columns) × 2^(cut rank) byte operations, one byte per
state, independent of the distance.

Tree-shaped decompositions need a min-plus XOR-convolution at each join, for which there is no fast
transform, so the linear form is the practical one. The signed (Fourier) representation cannot be
tropicalised because it relies on cancellation.

### Sparse mode: weight-bounded search (`cdist/gmitm.c`, `cdist/search.py`)

The same partial-syndrome recursion, keeping only states reachable with few faults. A solution is
built along a canonical order: pick the unsatisfied row with the fewest free columns, branch over
the columns touching it, forbid earlier siblings. When the remaining budget drops to k, the rest is
one lookup in a table of all column subsets of size at most k keyed by syndrome (meet in the
middle). Three additions carry most of the weight:

- translation symmetry: the solution may be assumed to contain one fixed representative of the
  lowest column orbit it touches (a factor 144 for BB288), after checking that the column set and
  the logical labels are invariant;
- the table of a *relaxed* problem as an admissible pruning test: if the collapsed residual cannot
  be cancelled within the budget, neither can the real one;
- two columns whose sum is again a column never occur together in a minimum solution.

Thresholds are searched in increasing order; each exhausted threshold K certifies `d > K`. For
BB72 to BB144 this is run directly on the real sector problem (`run_bb.py`).

Problems with more than 64 logical observables are searched in one pass in a label-free mode
(`labelfree=True`, the default above 64 observables): tables and states carry no logical label, every
syndrome match counts as a hit, and the logical value is computed for complete zero-syndrome sets only.

An optional fourth addition (`cover=True`, `scripts/run_deep.py --cover`; see [PHASE4.md](PHASE4.md)) is a
lower bound on the number of columns still needed, from a dual solution of the covering LP over
the columns that are still allowed at the node. It discards most nodes in the levels above the
table lookups.

### Top-down: enumerate relaxed solutions, lift with slack (`cdist/lift.py`)

For BB288 the real problem is too large for a direct search. Every real solution F projects onto a
collapsed solution O (the classes hit an odd number of times) and uses `|F| - |O|` further faults.
So: list all collapsed solutions up to weight W, one per translation orbit, and search the real
problem once per O with the budget "one member of each class of O plus W - |O| extra faults". If
nothing is found, W + 1 is a lower bound for the real circuit. The list is complete up to
`d_collapsed + 3`.

| BB288 | collapsed distance | collapsed solutions of weight 12 / 13 / 14 / 15 (orbits) | lift to weight ≤ 15 |
|---|---:|---|---:|
| Z | 15 | – / – / – / 1440 (10) | none |
| X | 12 | 48 (1) / 1728 (12) / 40464 (283) / 754464 (5250) | none |

## Evidence

Upper bounds are unconditional: each witness is checked in the full DEM and replayed physically
(`cdist/replay.py`). Lower bounds rest on exhaustive search code, not on a machine-checkable proof,
so they are cross-checked:

| check | result |
|---|---|
| dense DP, sparse search, tropical TN vs brute force on random problems (`tests/`) | all agree: 3000, 9000 and 1600 runs |
| top-down decision vs exhaustive truth on random problems | 1612 cases agree |
| enumeration up to d + 3 vs brute force | 240 cases agree |
| physical replay vs DEM prediction on random fault sets | 450 of 450 agree |
| stored witnesses replayed a second way (Stim detector sampler, faults as probability-1 channels) | 27 of 27 pass, including the three BB288 weight-16 witnesses (`tests/verify_witnesses.py`) |
| known code distances | sparse search on the data-error window: 6, 10, 10, 12, 18 for BB72, BB90, BB108, BB144, BB288; dense Rank DP: 6, 10, 12 for BB72, BB90, BB144 |
| collapsed BB90 distance by dense Rank DP (2^36-byte tables) | 7, as by sparse search |
| independent solver (MILP, SciPy / HiGHS) on the collapsed problems | proves 5, 5, 7, 7, 7, 6 for BB72, BB90, BB108 (Z, X): all equal to this work |
| same solver on larger problems (collapsed BB144 X, BB72 fold-3, real BB72 circuit) | finds the same values 8, 6, 6 but proves only ≥ 4, 3, 1 within 20 to 25 min |
| BB72 collapsed distance | 5 by dense Rank DP, by sparse search and by a pure-Python enumeration (36 and 252 solutions) |
| BB72 circuit distance | a pure-Python derivation sharing no search code gives 6 (`tests/independent_bb72.py`) |
| direct search vs top-down route | agree on all 8 small circuits at W = d - 1 and W = d |
| search with symmetry and exclusions vs plain search | agree on collapsed BB72, BB144 and BB288 (thresholds, solution sets) |

A MaxSAT run (Stim's formulation with PySAT RC2) on the full BB72 and BB90 circuits gave no result
in 87 minutes and was stopped, so it confirms nothing either way.

## Reproduce

    python3 -m venv .venv && .venv/bin/pip install stim numpy scipy
    for t in test_dp test_search test_kernel test_enum_cover test_multi test_isd test_topdown test_enum test_tn test_replay independent_bb72 verify_witnesses; do .venv/bin/python tests/$t.py; done
    .venv/bin/python run_bb.py circuits/bb144_r12_Z.stim results/bb144_r12_Z.json   # BB72–BB144: seconds
    ./run_bb288_all.sh        # BB288, both bases: about 650 GB RAM, 256 threads
    ./run_post.sh             # small codes by both routes, consistency checks, dense runs (about 520 GB RAM)
    .venv/bin/python scripts/experiments_dense.py results/dense.json                        # widths, dense runs
    .venv/bin/python scripts/experiments_widths_real.py results/widths_real.json            # widths of the real circuits
    .venv/bin/python tests/crosscheck_milp.py results/milp.json bb72_r6_Z:collapsed # HiGHS cross-check
    .venv/bin/python scripts/summarize.py                                                   # RESULTS.md

The C kernels compile on first use (`cc`; OpenMP on Linux). Server logs are in `logs/server/`.

| path | content |
|---|---|
| `cdist/problem.py` | DEM import, sector, collapse, fold, window |
| `cdist/trellis.py`, `viterbi.c`, `kernel.py`, `ordering.py` | dense min-plus Rank DP and column orderings |
| `cdist/gmitm.c`, `search.py`, `multi.py`, `symmetry.py` | sparse weight-bounded search (up to 64 observables per run; more are split into groups) |
| `cdist/isd.c`, `isd.py` | randomised information-set search for upper-bound witnesses |
| `cdist/lift.py` | enumeration of relaxed solutions, lifting with slack |
| `cdist/tn.py` | TN widths and a tropical contraction |
| `cdist/replay.py` | witness to physical faults, stabilizer replay |
| `papers/` | circuit builders, drivers and downloaded author data for the follow-up study |

## Limits

- The distances are for these specific circuits and this fault set, one unit per faulty location.
  Each memory basis tests only its own logical type. Whether the tesseract circuits use the same
  gate schedule as the original bivariate-bicycle paper was not checked, so the value 16 should not
  be read as a statement about that paper's circuit.
- All widths come from heuristic orderings, so they are upper bounds on the true widths, for Rank DP
  and TN alike. The DecisionDiagramDecoder repository reports 65 or 66 (Rank DP) against 71 (TN) for
  BB288 code capacity after a longer search; here a quick greedy order gives 75 against 80.
- The sparse mode is exponential in the distance: about a factor 12 per unit of weight on the
  collapsed BB288 problem. It closed BB288 because the collapsed bound was within 4 of the truth. A
  code of this size with distance well above 20 would probably be out of reach.
- Dense Rank DP remains the right tool where the cut rank is small and the distance large, for
  example codes with low-dimensional locality. That regime was not exercised here beyond the
  code-capacity checks.
- Approximate contraction of the small-fault-weight sum-product network (bond truncation) was not
  tested; only its exact version was.
