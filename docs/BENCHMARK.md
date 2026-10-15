# Benchmark: exact distance solvers on circuit and code problems

Status, 15 October 2026: all passes are complete, including Gurobi (added on 15 October) and the
instances of the prior benchmark arXiv:2603.22532. Tables are filled by `bench/make_benchmark_md.py`
from the records in `results/bench/`, `results/bench_tierB/`, `results/bench_ablation/`,
`results/bench_wjh/` and `results/bench_wjh_tierB/`.

## Question

Is the method of this project (certified relaxations plus a weight-bounded sparse search, see
[BB_CIRCUITS.md](BB_CIRCUITS.md)) the best available way to compute the circuit distance exactly? The test:
every method gets the same problem, the same machine and the same limits, and every answer is
checked.

## Answer

On these 60 instances, yes, with two qualifications given below.

- **Coverage.** Ours solves 46 instances exactly with one thread in 600 s and 59 with 32 threads in
  an hour. The other exact methods together solve 17 and 28. No instance is solved by another method
  and not by ours; 31 are solved by ours only. The one instance ours leaves open, the mitten
  [[300,60,14]] circuit, is open for every method (ours certifies at least 11).
- **Circuits** (44): ours 34 in the first tier, 43 over both; all others together 12 and 19. Every
  circuit that another method needs the second tier for (13 to 44 minutes on 32 threads for
  dist-m4ri, apart from surface d = 11 in 136 s) ours solves with one thread in 0.2 to 37 s, the
  d = 11 color-code circuit in 240 s. The gross code circuit, BB288, Cornucopia from n = 576, the
  routing circuits from n = 90 and the surface code from d = 13 are solved by ours only.
- **Codes** (16): ours 12 and 16; all others together 5 and 9. The strongest other tool is the
  connected-cluster mode of Qubitserf, which closes the BB288 code in 34 minutes on 32 threads
  (ours: 3 s on one thread).
- **Raw detector error model.** Without the sector reduction no other exact method solves any of the
  27 qLDPC circuits in the first tier; ours solves the same 19 as on the sector problem.
- **MaxSAT as it is used in the literature** (Stim's own WCNF export of the whole circuit, then a
  MaxSAT solver; the recipe behind the published exact values for the BB72 and [[90,8,10]]
  circuits): none of the three solvers proves the distance of any qLDPC circuit, in 600 s or in an
  hour. The best certified lower bound after an hour is 3 (RC2) on circuits of distance 5 to 11. It
  solves the surface code up to d = 5 and the color-code circuits up to d = 7.
- **Where another tool is faster.** On eight instances that several tools solve in under two
  seconds, dist-m4ri or Qubitserf is ahead of ours (0.0 to 0.2 s against 0.1 to 1.6 s); the only
  one above a second is the d = 7 color-code circuit (0.2 s against 1.6 s). On the instances that
  take both sides more than a second, ours is 4 to 200 times faster.
- **Gurobi** (added on 15 October, same protocol): 11 instances in the first tier and 17 over
  both, each of them also solved by another method. Of the circuits it solves the surface code up to
  d = 9, the color code up to d = 7 and the three smallest qLDPC circuits ([[72,12,6]], routing 54,
  STAR 42) in 3 to 9 minutes on 32 threads, where ours needs about a second on one thread. On the
  [[288,12,18]] code it is the fastest other tool (2006 s on 32 threads, Qubitserf 2026 s; ours 3.1 s).
- **The prior benchmark's own instances** (126 CSS codes and circuits of arXiv:2603.22532, section
  below): ours solves 86 with one thread in 600 s and 96 over both tiers; that paper's five exact
  methods together solved 73, with one thread and eight hours each, and their values agree with ours.
- **Correctness.** No record of any method contradicts the ground truth or another method's bounds.

Qualifications:

1. Two things carry the result, and the tables separate them. The time-collapsed relaxation helps
   every solver: on the collapsed problems dist-m4ri and HiGHS solve 20 of 39 each, against 8 and 3
   of the same 39 circuits on the sector problem (first tier). Our search is then still ahead on identical input
   (33 of 39). On the color-code circuits, where no reduction applies, ours and dist-m4ri are close:
   dist-m4ri is faster up to d = 7, ours from d = 9 (33 s against 142 s; d = 11 in 240 s on one
   thread against one hour on 32 threads).
2. The surface-code family is graph-like: a shortest-path computation solves it at any size, and is
   how its ground truth was obtained here. It is in the benchmark because the prior exact-solver
   benchmark uses it, not because it is hard in principle.

## Problem and instances

A problem is a pair of binary matrices (H, L): find the smallest set of columns whose H-columns sum
to zero and whose L-columns do not. For a circuit, columns are the mechanisms of the undecomposed
detector error model, rows of H are detectors and rows of L are logical observables; the optimum is
the circuit distance. For a code, H is one check matrix and L a basis of the logical operators of
the other type; the optimum is the code distance.

Each circuit instance is given in three forms:

| variant | what it is | status |
|---|---|---|
| `full` | the raw detector error model | the problem as a user poses it |
| `sector` | detectors of the memory basis only | exact reduction, checked at export |
| `collapsed` | detectors of one check merged over time | relaxation: a lower bound, with its own optimum |

Solvers other than ours cannot be expected to find the sector reduction themselves, so the main
comparison is on `sector`, which gives them their best case; `full` shows what happens without it.

Instance families ([bench/INSTANCES.md](../bench/INSTANCES.md) lists all 61):

- circuits of bivariate bicycle codes: the standard depth-7 circuits of [[72,12,6]] to [[288,12,18]],
  the best depth-7 schedules found here, the left-right gross circuit, weight-8 and self-dual codes;
- circuits from papers: Cornucopia, mitten, routing, shift, STAR, Walking Cat;
- rotated surface-code memory circuits from Stim's generator, d = 3 to 25, rounds = d. The closest
  prior benchmark (Webster, Jacob, Higgott, arXiv:2603.22532) uses this family with SI1000 noise;
  its own files (24485 mechanisms at d = 11, against 24483 here) are run in the section on its
  instances below;
- Stim's color-code memory circuits (`color_code:memory_xyz`), d = 3 to 11: not a CSS memory
  experiment, so there is no sector or collapsed form and our reductions do not apply;
- code distance of 16 CSS codes with n = 72 to 1044.

Ground truth comes from this project's earlier certified results, from a shortest-path computation
for the surface code (its sector problem is graph-like), or, where marked †, from the runs of the
table itself when their bounds close.

## Methods

| name in the tables | method | implementation | threads |
|---|---|---|---|
| ours | collapsed relaxation, lifting, windows, symmetry, covering bound, weight-bounded search | this project (`bench/adapters/ours_pipeline.py`); plain search on codes and on circuits without CSS sectors | OpenMP |
| ours, plain | the weight-bounded search alone on the problem as given | `bench/adapters/ours.py` | OpenMP |
| dist-m4ri CC | connected-cluster enumeration | dist-m4ri 0.9.0 (commit 1f46277), m4ri 20260122 | yes |
| dist-m4ri CC+RW | the same with random-window upper bounds | same binary, `mode=bracket` | yes |
| HiGHS | integer linear program | HiGHS as bundled with SciPy 1.16.3 | no gain |
| CP-SAT | integer program by lazy clause generation | OR-Tools 9.15.6755 | yes |
| Gurobi | integer linear program, the same model as HiGHS | Gurobi 13.0.3, academic licence, run as `gurobi_cl` on an LP file written by the adapter | yes |
| SAT | incremental SAT with a cardinality bound | PySAT 1.8 with CaDiCaL 1.5.3 | 1 |
| RC2 | core-guided MaxSAT | PySAT RC2 on CaDiCaL 1.5.3 | 1 |
| CASHWMaxSAT | MaxSAT | CASHWMaxSAT-CorePlus (MaxSAT Evaluation 2023) | 1 |
| enMaxCDCL | branch-and-bound MaxSAT | enMaxCDCL (authors' binary, CP 2026) | 1 |
| … (Stim WCNF) | the three MaxSAT solvers on Stim's own WCNF export of the whole circuit | `stim.Circuit.shortest_error_sat_problem`, the recipe used in the literature | 1 |
| Qubitserf CC / BZ / MITM | connected clusters, Brouwer-Zimmermann, meet in the middle; CSS codes only | Qubitserf 0.1.0 (commit ab96b9c) | yes |
| BP+OSD | decoding random logical constraints; upper bounds only | ldpc 2.4.1, min-sum, 100 iterations, OSD-CS order 2 | 1 |
| ISD | randomised information-set search; upper bounds only | this project | 1 |
| Stim search | `search_for_undetectable_logical_errors`; upper bounds only | Stim 1.15.0 | 1 |
| dist-m4ri RW | random window; upper bounds only | dist-m4ri 0.9.0 | yes |

Gurobi was added on 15 October 2026, when a licence became available, with the same protocol; its
records sit next to the others. Not tested: height-bound decision-tree decoding and the
tesseract-based route (no public distance tool found). The instances and published results of the
prior benchmark (arXiv:2603.22532) are compared in a section of their own below. The survey behind
this list is [bench/METHODS.md](../bench/METHODS.md).

## Protocol

- Machine: one socket of an AMD EPYC 9654 server (96 cores), each run pinned to its own cores.
- First tier: 1 thread, 600 s, 16 GB, every method on every instance.
- Second tier: only the instances a method did not solve in the first tier. Tools that use threads
  get 32 threads, 90 GB and 3600 s; single-thread tools get 1 thread, 16 GB and 3600 s.
- Give-up rule: within a family, instances are run in order of size; after two unsolved instances in
  a row (one in the second tier) the larger ones of that family are skipped for that method.
- An answer counts as exact only if the method certifies a lower bound equal to its upper bound and
  the harness verifies the fault set against the matrices. Qubitserf returns a number and no
  codeword; its values are marked with * and compared with the ground truth instead.
- No per-instance tuning for any method, ours included.

Reading a cell: a time means solved exactly; `>=7` a certified lower bound only; `7..12` both
bounds; `<=12` an upper bound only (`ok` if it equals the distance); `t/o` nothing certified;
`mem` out of memory; `skip` not run because of the give-up rule; `-` not applicable.

## Results at a glance

Main problem of each instance (sector problem of a CSS circuit, raw model of a color-code circuit,
the code itself); time of the fastest exact run. Tier 1: 1 thread, 600 s, 16 GB. Tier 2: one hour,
with 32 threads and 90 GB for tools that use threads.

<!-- TABLE:overall:BEGIN -->
| instance | n | columns | distance | ours, tier 1 | ours, tier 2 | best other, tier 1 | best other, tier 2 |
|---|---:|---:|---:|---:|---:|---|---|
| bb108_best_r6 | 108 | 3348 | 10 | 16.7 s |  |  |  |
| gross_best_r6 | 144 | 4464 | 11 | 114 s |  |  |  |
| bb72_r6 | 72 | 2232 | 6 | 0.4 s |  | 5.0 s (dist-m4ri CC+RW) | 534 s (Gurobi, 32 threads) |
| bb90_r10 | 90 | 4590 | 8 | 0.4 s |  |  | 2203 s (dist-m4ri CC+RW, 32 threads) |
| bb108_r10 | 108 | 5508 | 8 | 0.5 s |  |  | 2483 s (dist-m4ri CC+RW, 32 threads) |
| bb144_r12 | 144 | 8784 | 10 | 1.4 s |  |  |  |
| bb288_r18 | 288 | 26208 | 16 |  | 209 s |  |  |
| w8bb_72 | 72 | 3096 | 8 | 4.4 s |  |  | 2659 s (dist-m4ri CC+RW, 32 threads) |
| w8bb_144_16 | 144 | 6192 | 10 | 163 s |  |  |  |
| cornucopia_252 | 252 | 8568 | 5 | 1.6 s |  | 47.3 s (dist-m4ri CC) |  |
| cornucopia_576 | 576 | 19584 | 8 | 376 s |  |  |  |
| cornucopia_900 | 900 | 30600 | 9 |  | 485 s |  |  |
| cornucopia_1044 | 1044 | 35496 | 10 |  | 881 s |  |  |
| lrgross | 144 | 4464 | 11 | 19.8 s |  |  |  |
| mitten_150 | 150 | 9750 | 8 | 130 s |  |  |  |
| mitten_300 | 300 | 11820 | >=12 |  |  |  |  |
| mitten_200 | 200 | 15560 | 9 |  | 1038 s |  |  |
| routing_54 | 54 | 1998 | 6 | 0.9 s |  | 9.3 s (dist-m4ri CC) | 206 s (Gurobi, 32 threads) |
| routing_90 | 90 | 3330 | 9 | 5.4 s |  |  |  |
| routing_110 | 110 | 4070 | 10 | 35.3 s |  |  |  |
| routing_140_13 | 140 | 5180 | 12 |  | 86.2 s |  |  |
| routing_200_24 | 200 | 11700 | 10 |  | 477 s |  |  |
| sdbb_64 | 64 | 2752 | 8 | 3.7 s |  |  | 788 s (dist-m4ri CC+RW, 32 threads) |
| sdbb_120 | 120 | 5160 | 12 |  | 1117 s |  |  |
| shift_120d | 120 | 3720 | 8 | 37.1 s |  |  | 1640 s (dist-m4ri CC+RW, 32 threads) |
| star_42 | 42 | 1806 | 6 | 0.8 s |  | 41.4 s (dist-m4ri CC+RW) | 389 s (Gurobi, 32 threads) |
| color_d3 | 7 | 72 | 2† | 0.1 s |  | 0.0 s (dist-m4ri CC) |  |
| color_d5 | 19 | 1104 | 3† | 0.2 s |  | 0.0 s (dist-m4ri CC) |  |
| color_d7 | 37 | 3651 | 4† | 1.6 s |  | 0.2 s (dist-m4ri CC+RW) | 0.1 s (dist-m4ri CC+RW, 32 threads) |
| color_d9 | 61 | 7683 | 5† | 33.3 s |  | 142 s (dist-m4ri CC) | 1.2 s (dist-m4ri CC+RW, 32 threads) |
| color_d11 | 91 | 16422 | 6† | 240 s |  |  | 3600 s (dist-m4ri CC+RW, 32 threads) |
| surface_d3 | 9 | 55 | 3 | 0.1 s |  | 0.0 s (dist-m4ri CC) |  |
| surface_d5 | 25 | 301 | 5 | 0.1 s |  | 0.0 s (dist-m4ri CC) |  |
| surface_d7 | 49 | 883 | 7 | 0.1 s |  | 0.1 s (dist-m4ri CC) | 82.5 s (CP-SAT, 32 threads) |
| surface_d9 | 81 | 1945 | 9 | 0.1 s |  | 20.0 s (dist-m4ri CC) | 815 s (Gurobi, 32 threads) |
| surface_d11 | 121 | 3631 | 11 | 0.2 s |  |  | 136 s (dist-m4ri CC+RW, 32 threads) |
| surface_d13 | 169 | 6085 | 13 | 0.3 s |  |  |  |
| surface_d15 | 225 | 9451 | 15 | 0.7 s |  |  |  |
| surface_d17 | 289 | 13873 | 17 | 3.7 s |  |  |  |
| surface_d19 | 361 | 19495 | 19 | 26.5 s |  |  |  |
| surface_d21 | 441 | 26461 | 21 | 181 s |  |  |  |
| surface_d23 | 529 | 34915 | 23 |  | 69.3 s |  |  |
| surface_d25 | 625 | 45001 | 25 |  | 564 s |  |  |
| walkingcat_54 | 54 | 2322 | 8 | 6.7 s |  |  |  |
| code_bb72 | 72 | 72 | 6 | 0.2 s |  | 0.0 s (dist-m4ri CC) |  |
| code_bb90 | 90 | 90 | 10 | 0.2 s |  | 0.1 s (Qubitserf CC) |  |
| code_bb108 | 108 | 108 | 10 | 0.3 s |  | 0.1 s (Qubitserf CC) |  |
| code_bb144 | 144 | 144 | 12 | 0.2 s |  | 0.9 s (Qubitserf CC) | 59.5 s (CP-SAT, 32 threads) |
| code_bb288 | 288 | 288 | 18 | 3.1 s |  |  | 2006 s (Gurobi, 32 threads) |
| code_cornucopia_1044 | 1044 | 1044 | 12† | 1.7 s |  |  | 1633 s (Qubitserf CC, 32 threads) |
| code_w8bb_144_6 | 144 | 144 | 15 | 1.2 s |  |  | 456 s (Qubitserf BZ, 32 threads) |
| code_mm_324 | 324 | 324 | 18 | 2.6 s |  |  |  |
| code_llmbb_360 | 360 | 360 | 24 |  | 54.9 s |  |  |
| code_balanced_390 | 390 | 390 | 16 | 39.0 s |  |  |  |
| code_balanced_625 | 625 | 625 | 20 |  | 47.2 s |  |  |
| code_gala_132 | 132 | 132 | 12 | 1.2 s |  |  | 212 s (Gurobi, 32 threads) |
| code_kasai_372 | 372 | 372 | 16 | 104 s |  |  |  |
| code_kasai_444 | 444 | 444 | 18 |  | 57.5 s |  |  |
| code_kasai_492 | 492 | 492 | 20 |  | 776 s |  |  |
| code_sdbb_200 | 200 | 200 | 12 | 0.2 s |  | 30.2 s (Qubitserf CC) | 1204 s (CP-SAT, 32 threads) |

Of 60 instances: ours solves 46 in the first tier and 59 over both tiers; some other exact method solves 17 in the first tier and 28 over both. 31 are solved by ours only; 0 are solved by another method and not by ours.
<!-- TABLE:overall:END -->

## Results, first tier (1 thread, 600 s, 16 GB)

<!-- TABLE:A-check:BEGIN -->
All first-tier records are mutually consistent and consistent with the ground truth.
<!-- TABLE:A-check:END -->

### Circuits, sector problem

<!-- TABLE:A-circuit-sector:BEGIN -->
| instance | n | columns | distance | ours | ours, plain | dist-m4ri CC | dist-m4ri CC+RW | HiGHS | CP-SAT | Gurobi | SAT | RC2 | CASHWMaxSAT | enMaxCDCL | Qubitserf CC | Qubitserf BZ | Qubitserf MITM | BP+OSD | ISD | Stim search | dist-m4ri RW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bb108_best_r6 | 108 | 3348 | 10 | 16.7 s | 12.2 s | >=7 | 7..10 | 1..12 | <=11 | 3..12 | >=5 | >=5 | >=1 | >=1 | - | - | - | <=10 ok | <=10 ok | mem | <=12 |
| gross_best_r6 | 144 | 4464 | 11 | 114 s | 99.4 s | >=7 | 7..12 | 1..31 | t/o | 3..12 | >=3 | >=4 | >=1 | >=1 | - | - | - | <=11 ok | <=11 ok | mem | <=14 |
| bb72_r6 | 72 | 2232 | 6 | 0.4 s | 0.3 s | 5.0 s | 5.0 s | 1..6 | <=6 ok | 3..6 | >=4 | >=5 | >=1 | >=1 | - | - | - | <=6 ok | <=6 ok | <=6 ok | <=6 ok |
| bb90_r10 | 90 | 4590 | 8 | 0.4 s | 1.3 s | >=7 | 7..9 | 1..27 | <=13 | 3..9 | >=4 | >=4 | >=1 | >=1 | - | - | - | <=8 ok | <=8 ok | mem | <=9 |
| bb108_r10 | 108 | 5508 | 8 | 0.5 s | 1.6 s | >=7 | 7..8 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=8 ok | <=8 ok | mem | <=8 ok |
| bb144_r12 | 144 | 8784 | 10 | 1.4 s | 46.0 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=12 | <=11 | mem | <=12 |
| bb288_r18 | 288 | 26208 | 16 | >=14 | >=11 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=26 | <=35 | mem | <=69 |
| w8bb_72 | 72 | 3096 | 8 | 4.4 s | 5.6 s | >=6 | 6..8 | 1..8 | <=8 ok | 3..8 | >=4 | >=4 | >=1 | >=1 | - | - | - | <=8 ok | <=8 ok | <=8 ok | <=8 ok |
| w8bb_144_16 | 144 | 6192 | 10 | 163 s | 178 s | >=6 | 6..11 | t/o | t/o | 2..10 | >=4 | >=4 | >=1 | >=1 | - | - | - | <=10 ok | <=10 ok | mem | <=12 |
| cornucopia_252 | 252 | 8568 | 5 | 1.6 s | 7.7 s | 47.3 s | 600 s | t/o | t/o | 2..6 | >=3 | >=3 | >=1 | >=1 | - | - | - | <=5 ok | <=5 ok | mem | <=5 ok |
| cornucopia_576 | 576 | 19584 | 8 | 376 s | >=7 | >=5 | 5..164 | t/o | t/o | 1..33 | >=2 | >=1 | >=1 | >=1 | - | - | - | <=8 ok | <=8 ok | mem | <=28 |
| cornucopia_900 | 900 | 30600 | 9 | >=9 | >=7 | >=5 | >=5 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=18 | t/o | mem | t/o |
| cornucopia_1044 | 1044 | 35496 | 10 | >=9 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | t/o | t/o | mem | t/o |
| lrgross | 144 | 4464 | 11 | 19.8 s | >=10 | >=6 | 6..12 | t/o | t/o | 3..11 | >=3 | >=4 | >=1 | >=1 | - | - | - | <=11 ok | <=11 ok | mem | <=12 |
| mitten_150 | 150 | 9750 | 8 | 130 s | t/o | >=5 | 5..8 | 1..10 | t/o | 2..10 | >=3 | >=3 | >=1 | >=1 | - | - | - | <=9 | <=8 ok | mem | <=15 |
| mitten_300 | 300 | 11820 | >=12 | >=9 | >=7 | >=5 | 5..89 | t/o | t/o | 2..16 | >=3 | >=2 | >=1 | >=1 | - | - | - | <=14 | <=28 | mem | <=59 |
| mitten_200 | 200 | 15560 | 9 | >=8 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=12 | <=16 | mem | <=34 |
| routing_54 | 54 | 1998 | 6 | 0.9 s | 0.4 s | 9.3 s | 9.4 s | 2..6 | <=6 ok | 4..6 | >=4 | >=5 | >=1 | >=1 | - | - | - | <=6 ok | <=6 ok | <=6 ok | <=6 ok |
| routing_90 | 90 | 3330 | 9 | 5.4 s | 5.8 s | >=7 | 7..10 | 2..26 | t/o | 4..9 | >=4 | >=5 | >=1 | >=1 | - | - | - | <=9 ok | <=9 ok | mem | <=11 |
| routing_110 | 110 | 4070 | 10 | 35.3 s | 33.3 s | >=7 | 7..14 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=10 ok | <=10 ok | mem | <=12 |
| routing_140_13 | 140 | 5180 | 12 | 11..13 | >=11 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=12 ok | <=12 ok | mem | <=21 |
| routing_200_24 | 200 | 11700 | 10 | 9..10 | >=9 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=18 | <=11 | t/o | <=102 |
| sdbb_64 | 64 | 2752 | 8 | 3.7 s | 4.0 s | >=6 | 6..8 | 1..8 | <=12 | 3..8 | >=4 | >=5 | >=1 | >=1 | - | - | - | <=8 ok | <=8 ok | mem | <=8 ok |
| sdbb_120 | 120 | 5160 | 12 | 11..12 | >=10 | >=6 | 6..21 | t/o | t/o | 2..12 | >=3 | >=4 | >=1 | >=1 | - | - | - | <=13 | <=13 | mem | <=20 |
| shift_120d | 120 | 3720 | 8 | 37.1 s | 1.4 s | >=7 | 7..9 | t/o | <=12 | 3..8 | >=4 | >=5 | >=1 | >=1 | - | - | - | <=8 ok | <=8 ok | mem | <=10 |
| star_42 | 42 | 1806 | 6 | 0.8 s | 0.5 s | 42.6 s | 41.4 s | 3..6 | <=6 ok | 4..6 | >=4 | >=5 | >=1 | >=1 | - | - | - | <=6 ok | <=6 ok | <=6 ok | <=6 ok |
| walkingcat_54 | 54 | 2322 | 8 | 6.7 s | 6.2 s | >=6 | 6..11 | 2..11 | <=9 | 4..9 | >=4 | >=4 | >=1 | >=1 | - | - | - | <=8 ok | <=8 ok | mem | <=10 |
| **solved exactly** (of 27) | | | | **19** | **16** | **4** | **4** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** |  |  |  |  |
<!-- TABLE:A-circuit-sector:END -->

### Circuits, raw detector error model

<!-- TABLE:A-circuit-full:BEGIN -->
| instance | n | columns | distance | ours | ours, plain | dist-m4ri CC | dist-m4ri CC+RW | HiGHS | CP-SAT | Gurobi | SAT | RC2 | CASHWMaxSAT | enMaxCDCL | RC2 (Stim WCNF) | CASHWMaxSAT (Stim WCNF) | enMaxCDCL (Stim WCNF) | Qubitserf CC | Qubitserf BZ | Qubitserf MITM | BP+OSD | ISD | Stim search | dist-m4ri RW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bb108_best_r6 | 108 | 24246 | 10 | 12.7 s | >=7 | >=5 | 5..87 | t/o | t/o | 2..10 | >=3 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=12 | <=16 | mem | <=69 |
| gross_best_r6 | 144 | 32328 | 11 | 120 s | >=7 | >=4 | 4..230 | t/o | t/o | 2..12 | >=2 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=14 | <=111 | mem | <=144 |
| bb72_r6 | 72 | 16164 | 6 | 0.3 s | 29.8 s | >=5 | 5..7 | t/o | t/o | 2..6 | >=3 | >=3 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=6 ok | <=6 ok | <=6 ok | <=8 |
| bb90_r10 | 90 | 34965 | 8 | 0.6 s | mem | >=5 | 5..25 | t/o | t/o | 2..8 | >=2 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=11 | <=11 | mem | <=67 |
| bb108_r10 | 108 | 41958 | 8 | 0.7 s | mem | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=11 | <=53 | mem | <=18 |
| bb144_r12 | 144 | 67752 | 10 | 1.9 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=16 | <=31 | mem | t/o |
| bb288_r18 | 288 | 206352 | 16 | >=14 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | mem | t/o |
| w8bb_72 | 72 | 23904 | 8 | 4.5 s | >=6 | >=4 | 4..58 | t/o | t/o | 2..8 | >=2 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=10 | <=10 | <=8 ok | <=26 |
| w8bb_144_16 | 144 | 47808 | 10 | 165 s | mem | >=4 | 4..331 | t/o | t/o | 1..13 | >=2 | >=1 | >=1 | >=1 | >=1 | >=1 | >=1 | - | - | - | <=14 | t/o | mem | <=224 |
| cornucopia_252 | 252 | 65450 | 5 | 2.4 s | mem | >=4 | 4..198 | t/o | t/o | 1..8 | >=1 | mem | >=1 | >=1 | >=1 | >=1 | >=1 | - | - | - | <=6 | <=7 | mem | <=182 |
| cornucopia_576 | 576 | 149760 | 8 | 382 s | mem | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | >=1 | >=1 | skip | skip | skip | mem | t/o | mem | t/o |
| cornucopia_900 | 900 | 234000 | 9 | >=9 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | mem | t/o |
| cornucopia_1044 | 1044 | 271440 | 10 | >=9 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | mem | t/o |
| lrgross | 144 | 31488 | 11 | 19.8 s | >=7 | >=5 | 5..82 | t/o | t/o | 2..12 | >=2 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=11 ok | <=12 | mem | <=78 |
| mitten_150 | 150 | 76395 | 8 | 135 s | mem | >=4 | >=4 | t/o | t/o | 2..10 | >=2 | >=1 | >=1 | >=1 | >=1 | >=1 | >=1 | - | - | - | <=10 | <=67 | mem | <=75 |
| mitten_300 | 300 | 87780 | >=12 | >=9 | mem | >=4 | >=4 | t/o | t/o | 1..16 | >=1 | >=1 | >=1 | >=1 | >=1 | >=1 | >=1 | - | - | - | <=15 | t/o | mem | t/o |
| mitten_200 | 200 | 123792 | 9 | >=8 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | mem | t/o |
| routing_54 | 54 | 14958 | 6 | 0.9 s | 83.7 s | >=4 | 4..8 | t/o | t/o | 3..6 | >=3 | >=3 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=6 ok | <=6 ok | <=6 ok | <=9 |
| routing_90 | 90 | 25020 | 9 | 5.5 s | >=7 | >=4 | 4..83 | t/o | t/o | 2..9 | >=3 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=9 ok | <=38 | mem | <=75 |
| routing_110 | 110 | 30580 | 10 | 35.5 s | >=7 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=11 | <=92 | mem | <=131 |
| routing_140_13 | 140 | 38920 | 12 | 11..13 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=12 ok | t/o | mem | <=189 |
| routing_200_24 | 200 | 95200 | 10 | 9..10 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | t/o | <=426 |
| sdbb_64 | 64 | 21248 | 8 | 3.9 s | t/o | >=4 | 4..40 | t/o | t/o | 2..8 | >=3 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=8 ok | <=8 ok | mem | <=21 |
| sdbb_120 | 120 | 39840 | 12 | 11..12 | mem | >=4 | 4..267 | t/o | t/o | 2..12 | >=2 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=19 | <=116 | mem | <=115 |
| shift_120d | 120 | 27000 | 8 | 46.7 s | >=7 | >=5 | 5..91 | t/o | t/o | 2..14 | >=2 | >=2 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=11 | <=18 | mem | <=19 |
| star_42 | 42 | 13902 | 6 | 0.9 s | 289 s | >=4 | 4..10 | t/o | t/o | 2..6 | >=3 | >=3 | >=1 | >=1 | >=3 | >=1 | >=1 | - | - | - | <=6 ok | <=6 ok | <=6 ok | <=7 |
| walkingcat_54 | 54 | 17820 | 8 | 6.8 s | >=6 | >=4 | 4..37 | t/o | <=68 | 3..9 | >=3 | >=3 | >=1 | >=1 | >=2 | >=1 | >=1 | - | - | - | <=8 ok | <=14 | mem | <=22 |
| **solved exactly** (of 27) | | | | **19** | **3** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** |  |  |  |  |
<!-- TABLE:A-circuit-full:END -->

### Codes

<!-- TABLE:A-code:BEGIN -->
| instance | n | columns | distance | ours | ours, plain | dist-m4ri CC | dist-m4ri CC+RW | HiGHS | CP-SAT | Gurobi | SAT | RC2 | CASHWMaxSAT | enMaxCDCL | Qubitserf CC | Qubitserf BZ | Qubitserf MITM | BP+OSD | ISD | dist-m4ri RW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| code_bb72 | 72 | 72 | 6 | 0.2 s | 0.0 s | 0.0 s | 0.0 s | 0.7 s | 0.3 s | 0.7 s | 0.2 s | 0.2 s | 0.3 s | 0.1 s | 0.1 s* | 0.1 s* | 0.6 s* | <=6 ok | <=6 ok | <=6 ok |
| code_bb90 | 90 | 90 | 10 | 0.2 s | 0.0 s | 0.2 s | 0.2 s | 16.5 s | 49.0 s | 2.5 s | 17.6 s | 16.5 s | 27.4 s | 0.7 s | 0.1 s* | 3.9 s* | mem | <=10 ok | <=10 ok | <=10 ok |
| code_bb108 | 108 | 108 | 10 | 0.3 s | 0.0 s | 0.4 s | 0.2 s | 24.5 s | 36.6 s | 3.7 s | 21.1 s | 17.0 s | 37.0 s | 2.0 s | 0.1 s* | 16.8 s* | mem | <=10 ok | <=10 ok | <=10 ok |
| code_bb144 | 144 | 144 | 12 | 0.2 s | 0.1 s | 7.5 s | 5.7 s | 183 s | <=12 ok | 43.8 s | 168 s | 196 s | 462 s | 28.7 s | 0.9 s* | t/o | skip | <=12 ok | <=12 ok | <=12 ok |
| code_bb288 | 288 | 288 | 18 | 3.1 s | 2.5 s | >=14 | 14..18 | 5..20 | <=18 ok | 10..18 | >=10 | >=11 | >=1 | >=1 | t/o | t/o | skip | <=18 ok | <=18 ok | <=18 ok |
| code_cornucopia_1044 | 1044 | 1044 | 12† | 1.7 s | 1.1 s | >=9 | 9..12 | t/o | <=20 | 2..16 | >=5 | >=5 | >=1 | >=1 | t/o | t/o | mem | <=12 ok | <=12 ok | <=12 ok |
| code_w8bb_144_6 | 144 | 144 | 15 | 1.2 s | 1.1 s | >=12 | 12..15 | 9..15 | <=15 ok | 11..15 | >=10 | >=10 | >=1 | >=1 | t/o | t/o | mem | <=15 ok | <=15 ok | <=15 ok |
| code_mm_324 | 324 | 324 | 18 | 2.6 s | 2.4 s | >=11 | 11..18 | 7..23 | <=20 | 9..24 | >=10 | >=10 | >=1 | >=1 | t/o | t/o | mem | <=20 | <=18 ok | <=22 |
| code_llmbb_360 | 360 | 360 | 24 | >=23 | >=23 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=24 ok | <=24 ok | <=24 ok |
| code_balanced_390 | 390 | 390 | 16 | 39.0 s | 38.8 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=16 ok | <=16 ok | <=16 ok |
| code_balanced_625 | 625 | 625 | 20 | >=19 | >=19 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=20 ok | <=20 ok | <=20 ok |
| code_gala_132 | 132 | 132 | 12 | 1.2 s | 1.1 s | >=10 | 10..12 | 7..12 | <=12 ok | 8..12 | >=7 | >=8 | >=1 | >=1 | t/o | t/o | mem | <=12 ok | <=12 ok | <=12 ok |
| code_kasai_372 | 372 | 372 | 16 | 104 s | 103 s | >=10 | 10..20 | 3..62 | <=30 | 8..62 | >=6 | >=7 | >=1 | >=1 | t/o | t/o | mem | <=16 ok | <=16 ok | <=24 |
| code_kasai_444 | 444 | 444 | 18 | >=17 | >=17 | >=9 | 9..32 | 2..74 | <=52 | 7..64 | >=6 | >=1 | >=1 | >=1 | t/o | t/o | mem | <=20 | <=18 ok | <=24 |
| code_kasai_492 | 492 | 492 | 20 | >=17 | >=17 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=22 | <=20 ok | <=34 |
| code_sdbb_200 | 200 | 200 | 12 | 0.2 s | 0.1 s | >=12 | 155 s | 307 s | <=12 ok | 163 s | >=9 | >=10 | >=1 | 248 s | 30.2 s* | t/o | mem | <=12 ok | <=12 ok | <=12 ok |
| **solved exactly** (of 16) | | | | **12** | **12** | **4** | **5** | **5** | **3** | **5** | **4** | **4** | **4** | **5** | **5** | **3** | **1** |  |  |  |
<!-- TABLE:A-code:END -->

### Stim surface-code circuits, sector problem

<!-- TABLE:A-stim-sector:BEGIN -->
| instance | n | columns | distance | ours | ours, plain | dist-m4ri CC | dist-m4ri CC+RW | HiGHS | CP-SAT | Gurobi | SAT | RC2 | CASHWMaxSAT | enMaxCDCL | Qubitserf CC | Qubitserf BZ | Qubitserf MITM | BP+OSD | ISD | Stim search | dist-m4ri RW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| surface_d3 | 9 | 55 | 3 | 0.1 s | 0.0 s | 0.0 s | 0.0 s | 0.3 s | 0.3 s | 0.3 s | 0.1 s | 0.1 s | 0.2 s | 0.1 s | - | - | - | <=3 ok | <=3 ok | <=3 ok | <=3 ok |
| surface_d5 | 25 | 301 | 5 | 0.1 s | 0.0 s | 0.0 s | 0.0 s | 0.7 s | 21.5 s | 0.5 s | 0.3 s | 0.4 s | 1.4 s | 0.2 s | - | - | - | <=5 ok | <=5 ok | <=5 ok | <=5 ok |
| surface_d7 | 49 | 883 | 7 | 0.1 s | 0.1 s | 0.1 s | 0.2 s | 168 s | 4..7 | 29.0 s | 31.1 s | 62.4 s | >=1 | 131 s | skip | skip | skip | <=7 ok | <=7 ok | mem | <=7 ok |
| surface_d9 | 81 | 1945 | 9 | 0.1 s | 0.9 s | 20.0 s | 20.6 s | 5..9 | 3..9 | 6..9 | >=6 | >=7 | >=1 | >=1 | skip | skip | skip | <=9 ok | <=9 ok | mem | <=9 ok |
| surface_d11 | 121 | 3631 | 11 | 0.2 s | 36.3 s | >=10 | 10..11 | 3..11 | skip | 5..11 | >=6 | >=7 | skip | >=1 | skip | skip | skip | <=11 ok | <=11 ok | err | <=11 ok |
| surface_d13 | 169 | 6085 | 13 | 0.3 s | >=12 | >=9 | 9..13 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=13 ok | <=13 ok | mem | <=13 ok |
| surface_d15 | 225 | 9451 | 15 | 0.7 s | >=11 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=15 ok | <=15 ok | mem | <=15 ok |
| surface_d17 | 289 | 13873 | 17 | 3.7 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=17 ok | <=17 ok | mem | <=17 ok |
| surface_d19 | 361 | 19495 | 19 | 26.5 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=19 ok | <=19 ok | err | <=19 ok |
| surface_d21 | 441 | 26461 | 21 | 181 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=21 ok | <=23 | mem | <=22 |
| surface_d23 | 529 | 34915 | 23 | >=23 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=23 ok | <=27 | mem | <=23 ok |
| surface_d25 | 625 | 45001 | 25 | >=22 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=25 ok | t/o | err | t/o |
| **solved exactly** (of 12) | | | | **10** | **5** | **4** | **4** | **3** | **2** | **3** | **3** | **3** | **2** | **3** | **0** | **0** | **0** |  |  |  |  |
<!-- TABLE:A-stim-sector:END -->

### Stim surface- and color-code circuits, raw detector error model

<!-- TABLE:A-stim-full:BEGIN -->
| instance | n | columns | distance | ours | ours, plain | dist-m4ri CC | dist-m4ri CC+RW | HiGHS | CP-SAT | Gurobi | SAT | RC2 | CASHWMaxSAT | enMaxCDCL | RC2 (Stim WCNF) | CASHWMaxSAT (Stim WCNF) | enMaxCDCL (Stim WCNF) | Qubitserf CC | Qubitserf BZ | Qubitserf MITM | BP+OSD | ISD | Stim search | dist-m4ri RW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| color_d3 | 7 | 72 | 2† | 0.1 s | 0.0 s | 0.0 s | 0.0 s | 0.3 s | 0.3 s | 0.3 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | - | - | - | <=2 ok | <=2 ok | <=2 ok | <=2 ok |
| color_d5 | 19 | 1104 | 3† | 0.2 s | 0.1 s | 0.0 s | 0.0 s | 1.9 s | 35.1 s | 0.3 s | 1.0 s | 1.0 s | 5.8 s | 2.3 s | 0.9 s | 5.0 s | 2.1 s | - | - | - | <=3 ok | <=3 ok | <=3 ok | <=3 ok |
| color_d7 | 37 | 3651 | 4† | 1.6 s | 1.5 s | 0.6 s | 0.2 s | 47.8 s | 2..4 | 6.9 s | 37.4 s | 45.0 s | 63.6 s | >=1 | 49.5 s | 198 s | >=1 | skip | skip | skip | <=4 ok | <=4 ok | <=4 ok | <=4 ok |
| color_d9 | 61 | 7683 | 5† | 33.3 s | 33.4 s | 142 s | 600 s | 2..5 | 2..5 | 4..5 | >=4 | >=4 | >=1 | >=1 | >=4 | >=1 | >=1 | skip | skip | skip | <=5 ok | <=5 ok | <=5 ok | <=5 ok |
| color_d11 | 91 | 16422 | 6† | 240 s | t/o | >=5 | 5..9 | 1..6 | skip | 3..6 | >=4 | >=3 | >=1 | skip | >=3 | >=1 | skip | skip | skip | skip | <=6 ok | <=6 ok | err | <=8 |
| surface_d3 | 9 | 219 | 3 | 0.1 s | 0.0 s | 0.0 s | 0.0 s | 0.3 s | 0.4 s | 0.3 s | 0.1 s | 0.1 s | 0.3 s | 0.1 s | 0.1 s | 0.3 s | 0.1 s | - | - | - | <=3 ok | <=3 ok | <=3 ok | <=3 ok |
| surface_d5 | 25 | 1677 | 5 | 0.1 s | 0.4 s | 0.3 s | 0.4 s | 16.9 s | 3..5 | 7.5 s | 30.8 s | 75.0 s | >=1 | >=1 | 48.0 s | >=1 | >=1 | - | - | - | <=5 ok | <=5 ok | <=5 ok | <=5 ok |
| surface_d7 | 49 | 5471 | 7 | 0.2 s | 122 s | >=6 | 6..7 | 3..7 | 2..7 | 4..7 | >=5 | >=5 | >=1 | >=1 | >=5 | >=1 | >=1 | skip | skip | skip | <=7 ok | <=7 ok | mem | <=7 ok |
| surface_d9 | 81 | 12705 | 9 | 0.2 s | t/o | >=6 | 6..9 | 3..9 | skip | 4..9 | >=4 | >=4 | skip | skip | >=4 | skip | skip | skip | skip | skip | <=9 ok | <=9 ok | mem | <=9 ok |
| surface_d11 | 121 | 24483 | 11 | 0.3 s | >=6 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=11 ok | <=11 ok | err | <=11 ok |
| surface_d13 | 169 | 41909 | 13 | 0.4 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=13 ok | <=13 ok | mem | <=15 |
| surface_d15 | 225 | 66087 | 15 | 1.1 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | <=15 ok | <=20 | mem | <=18 |
| surface_d17 | 289 | 98121 | 17 | 4.8 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | mem | t/o |
| surface_d19 | 361 | 139115 | 19 | 29.0 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | err | t/o |
| surface_d21 | 441 | 190173 | 21 | 191 s | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | mem | t/o |
| surface_d23 | 529 | 252399 | 23 | >=22 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | mem | t/o |
| surface_d25 | 625 | 326897 | 25 | >=22 | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | skip | mem | t/o | err | t/o |
| **solved exactly** (of 17) | | | | **15** | **7** | **6** | **6** | **5** | **3** | **5** | **5** | **5** | **4** | **3** | **5** | **4** | **3** | **0** | **0** | **0** |  |  |  |  |
<!-- TABLE:A-stim-full:END -->

### Time-collapsed relaxation

The optimum here is a lower bound on the circuit distance, not the distance. The pipeline is not
defined on this input; "ours, plain" is our search on the same matrices as the others.

<!-- TABLE:A-collapsed:BEGIN -->
| instance | n | columns | distance | ours, plain | dist-m4ri CC | dist-m4ri CC+RW | HiGHS | CP-SAT | Gurobi | SAT | RC2 | CASHWMaxSAT | enMaxCDCL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bb108_best_r6 | 108 | 270 | 8 | 0.1 s | >=8 | 105 s | 5..8 | <=8 ok | 6..8 | >=6 | >=7 | >=1 | >=1 |
| gross_best_r6 | 144 | 360 | 9 | 0.1 s | >=8 | 8..9 | 4..9 | <=9 ok | 5..9 | >=6 | >=6 | >=1 | >=1 |
| bb72_r6 | 72 | 180 | 5 | 0.0 s | 0.0 s | 0.1 s | 4.3 s | 10.2 s | 2.7 s | 1.9 s | 1.9 s | 7.1 s | 2.6 s |
| bb90_r10 | 90 | 225 | 7 | 0.0 s | 11.0 s | 8.5 s | 114 s | <=7 ok | 37.7 s | 175 s | 177 s | >=1 | 123 s |
| bb108_r10 | 108 | 270 | 7 | 0.0 s | 9.3 s | 7.3 s | 162 s | <=7 ok | 152 s | 237 s | 275 s | >=1 | 183 s |
| bb144_r12 | 144 | 360 | 9 | 0.1 s | >=8 | 8..9 | 3..9 | skip | 5..9 | >=6 | >=6 | skip | >=1 |
| bb288_r18 | 288 | 720 | 15 | >=14 | >=8 | 8..19 | 2..18 | skip | 4..18 | >=5 | >=6 | skip | >=1 |
| w8bb_72 | 72 | 252 | 4† | 0.0 s | 0.0 s | 0.0 s | 5.2 s | 2.4 s | 1.7 s | 1.6 s | 1.2 s | 6.7 s | 5.3 s |
| w8bb_144_16 | 144 | 504 | 6† | 0.2 s | 74.7 s | 18.2 s | 553 s | <=6 ok | 497 s | 242 s | 311 s | >=1 | >=1 |
| cornucopia_252 | 252 | 819 | 5 | 0.5 s | 35.3 s | 20.3 s | 2..5 | <=5 ok | 4..5 | >=3 | >=4 | >=1 | >=1 |
| cornucopia_576 | 576 | 1872 | 8 | 369 s | >=5 | 5..43 | t/o | <=12 | 2..617 | >=3 | >=4 | >=1 | >=1 |
| cornucopia_900 | 900 | 2925 | 9 | t/o | >=5 | 5..73 | skip | skip | skip | skip | skip | skip | skip |
| cornucopia_1044 | 1044 | 3393 | 9 | >=9 | skip | skip | skip | skip | skip | skip | skip | skip | skip |
| lrgross | 144 | 360 | 11 | 36.1 s | >=7 | 7..11 | 3..11 | <=11 ok | 5..11 | >=6 | >=7 | >=1 | >=1 |
| mitten_150 | 150 | 510 | 8 | 243 s | >=6 | 6..9 | 2..10 | <=10 | 5..9 | >=5 | >=6 | >=1 | >=1 |
| mitten_200 | 200 | 680 | 9 | >=8 | >=6 | 6..15 | 2..12 | <=12 | 5..12 | >=5 | >=6 | >=1 | >=1 |
| mitten_300 | 300 | 1020 | >=12 | >=9 | skip | skip | skip | skip | skip | skip | skip | skip | skip |
| routing_54 | 54 | 162 | 4 | 0.0 s | 0.0 s | 0.0 s | 1.5 s | 1.0 s | 0.8 s | 0.3 s | 0.4 s | 1.2 s | 1.0 s |
| routing_90 | 90 | 270 | 7 | 0.1 s | 22.5 s | 16.9 s | 257 s | <=7 ok | 268 s | 104 s | 204 s | >=1 | >=1 |
| routing_110 | 110 | 330 | 7 | 0.1 s | 30.4 s | 20.5 s | 292 s | <=7 ok | 235 s | 277 s | 349 s | >=1 | >=1 |
| routing_140_13 | 140 | 420 | 10 | 1.0 s | >=8 | 8..10 | 3..10 | skip | 6..10 | >=6 | >=7 | skip | skip |
| routing_200_24 | 200 | 900 | 8 | 21.4 s | >=6 | 6..8 | 2..18 | skip | 3..17 | >=4 | >=2 | skip | skip |
| sdbb_64 | 64 | 224 | 4† | 0.0 s | 0.0 s | 0.0 s | 3.4 s | 2.0 s | 0.6 s | 0.9 s | 1.1 s | 2.4 s | 3.8 s |
| sdbb_120 | 120 | 420 | 10 | 36.3 s | >=7 | 7..10 | 3..10 | <=10 ok | 5..10 | >=5 | >=6 | >=1 | >=1 |
| shift_120d | 120 | 1633 | 2 | 0.2 s | 0.0 s | 0.0 s | 36.3 s | 1.0 s | 0.5 s | 0.4 s | 0.6 s | 3.0 s | 1.7 s |
| star_42 | 42 | 147 | 4 | 0.0 s | 0.0 s | 0.0 s | 1.4 s | 1.2 s | 0.6 s | 0.8 s | 0.7 s | 1.5 s | 1.9 s |
| surface_d3 | 9 | 9 | 3 | 0.0 s | 0.0 s | 0.0 s | 0.3 s | 0.3 s | 0.3 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s |
| surface_d5 | 25 | 29 | 5 | 0.0 s | 0.0 s | 0.0 s | 0.3 s | 0.3 s | 0.3 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s |
| surface_d7 | 49 | 61 | 7 | 0.0 s | 0.0 s | 0.0 s | 0.3 s | 0.4 s | 0.3 s | 0.1 s | 0.1 s | 0.6 s | 0.1 s |
| surface_d9 | 81 | 105 | 9 | 0.0 s | 0.0 s | 0.0 s | 1.1 s | 2.0 s | 0.9 s | 1.1 s | 0.5 s | 13.9 s | 1.0 s |
| surface_d11 | 121 | 161 | 11 | 0.0 s | 0.2 s | 0.2 s | 10.6 s | 25.8 s | 15.3 s | 22.9 s | 5.8 s | 157 s | 35.1 s |
| surface_d13 | 169 | 229 | 13 | 0.0 s | 4.0 s | 4.0 s | 54.4 s | 54.6 s | 394 s | 464 s | 208 s | >=1 | >=1 |
| surface_d15 | 225 | 309 | 15 | 0.1 s | 96.1 s | 96.9 s | 84.9 s | 297 s | 10..15 | >=11 | >=13 | >=1 | >=1 |
| surface_d17 | 289 | 401 | 17 | 0.5 s | >=16 | 16..17 | 86.3 s | 13..17 | 10..17 | >=11 | >=12 | skip | skip |
| surface_d19 | 361 | 505 | 19 | 4.0 s | >=15 | 15..19 | 13..19 | 12..19 | skip | skip | skip | skip | skip |
| surface_d21 | 441 | 621 | 21 | 33.4 s | skip | skip | 13..21 | skip | skip | skip | skip | skip | skip |
| surface_d23 | 529 | 749 | 23 | 292 s | skip | skip | skip | skip | skip | skip | skip | skip | skip |
| surface_d25 | 625 | 889 | 25 | >=23 | skip | skip | skip | skip | skip | skip | skip | skip | skip |
| walkingcat_54 | 54 | 189 | 6 | 0.0 s | 4.2 s | 4.0 s | 54.1 s | 249 s | 21.2 s | 49.4 s | 69.2 s | 228 s | 98.5 s |
| **solved exactly** (of 39) | | | | **33** | **20** | **21** | **20** | **14** | **18** | **18** | **18** | **12** | **14** |
<!-- TABLE:A-collapsed:END -->

## Results, second tier

<!-- TABLE:B-check:BEGIN -->
All second-tier records are mutually consistent and consistent with the ground truth.
<!-- TABLE:B-check:END -->

### 32 threads, 90 GB, 3600 s: circuits, sector problem

<!-- TABLE:B32-circuit-sector:BEGIN -->
| instance | n | columns | distance | ours | dist-m4ri CC+RW | CP-SAT | Gurobi | Qubitserf CC | Qubitserf BZ | Qubitserf MITM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bb108_best_r6 | 108 | 3348 | 10 |  | 9..11 | 3..10 | 5..10 |  |  |  |
| gross_best_r6 | 144 | 4464 | 11 |  | skip | skip | skip |  |  |  |
| bb72_r6 | 72 | 2232 | 6 |  |  | 2732 s | 534 s |  |  |  |
| bb90_r10 | 90 | 4590 | 8 |  | 2203 s | 4..8 | 4..8 |  |  |  |
| bb108_r10 | 108 | 5508 | 8 |  | 2483 s | skip | skip | - | - | - |
| bb144_r12 | 144 | 8784 | 10 |  | 8..13 | skip | skip | skip | skip | skip |
| bb288_r18 | 288 | 26208 | 16 | 209 s | skip | skip | skip | skip | skip | skip |
| w8bb_72 | 72 | 3096 | 8 |  | 2659 s | 5..8 | 4..8 |  |  |  |
| w8bb_144_16 | 144 | 6192 | 10 |  | 7..12 | skip | skip |  |  |  |
| cornucopia_252 | 252 | 8568 | 5 |  |  | 3..5 | 2..5 |  |  |  |
| cornucopia_576 | 576 | 19584 | 8 |  | >=6 | skip | skip |  |  |  |
| cornucopia_900 | 900 | 30600 | 9 | 485 s | skip | skip | skip | - | - | - |
| cornucopia_1044 | 1044 | 35496 | 10 | 881 s | skip | skip | skip | skip | skip | skip |
| lrgross | 144 | 4464 | 11 |  | 8..12 | 5..11 | 4..11 |  |  |  |
| mitten_150 | 150 | 9750 | 8 |  | 6..9 | 3..9 | 4..9 |  |  |  |
| mitten_300 | 300 | 11820 | >=12 | >=11 | skip | skip | skip |  |  |  |
| mitten_200 | 200 | 15560 | 9 | 1038 s | skip | skip | skip | - | - | - |
| routing_54 | 54 | 1998 | 6 |  |  | 2457 s | 206 s |  |  |  |
| routing_90 | 90 | 3330 | 9 |  | 8..11 | 1..9 | 5..9 |  |  |  |
| routing_110 | 110 | 4070 | 10 |  | skip | skip | skip | - | - | - |
| routing_140_13 | 140 | 5180 | 12 | 86.2 s | skip | skip | skip | skip | skip | skip |
| routing_200_24 | 200 | 11700 | 10 | 477 s | skip | skip | skip | skip | skip | skip |
| sdbb_64 | 64 | 2752 | 8 |  | 788 s | 5..8 | 5..8 |  |  |  |
| sdbb_120 | 120 | 5160 | 12 | 1117 s | 7..27 | skip | skip |  |  |  |
| shift_120d | 120 | 3720 | 8 |  | 1640 s | 3..8 | 4..8 |  |  |  |
| star_42 | 42 | 1806 | 6 |  |  | 2..6 | 389 s |  |  |  |
| surface_d7 | 49 | 883 | 7 |  |  | 82.5 s |  | - | - | - |
| surface_d9 | 81 | 1945 | 9 |  |  | 1..9 | 815 s | skip | skip | skip |
| surface_d11 | 121 | 3631 | 11 |  | 136 s | skip | mem | skip | skip | skip |
| surface_d13 | 169 | 6085 | 13 |  | 12..13 | skip | skip | skip | skip | skip |
| surface_d15 | 225 | 9451 | 15 |  | skip | skip | skip | skip | skip | skip |
| surface_d17 | 289 | 13873 | 17 |  | skip | skip | skip | skip | skip | skip |
| surface_d19 | 361 | 19495 | 19 |  | skip | skip | skip | skip | skip | skip |
| surface_d21 | 441 | 26461 | 21 |  | skip | skip | skip | skip | skip | skip |
| surface_d23 | 529 | 34915 | 23 | 69.3 s | skip | skip | skip | skip | skip | skip |
| surface_d25 | 625 | 45001 | 25 | 564 s | skip | skip | skip | skip | skip | skip |
| walkingcat_54 | 54 | 2322 | 8 |  | 8..10 | 5..8 | 5..8 |  |  |  |
| **solved exactly** (of 37) | | | | **9** | **6** | **3** | **4** | **0** | **0** | **0** |
<!-- TABLE:B32-circuit-sector:END -->

### 32 threads: Stim color-code circuits, raw detector error model

<!-- TABLE:B32-circuit-full:BEGIN -->
| instance | n | columns | distance | dist-m4ri CC+RW | CP-SAT |
|---|---:|---:|---:|---:|---:|
| color_d7 | 37 | 3651 | 4† | 0.1 s | 379 s |
| color_d9 | 61 | 7683 | 5† | 1.2 s | 2..5 |
| color_d11 | 91 | 16422 | 6† | 3600 s | skip |
| **solved exactly** (of 3) | | | | **3** | **1** |
<!-- TABLE:B32-circuit-full:END -->

### 32 threads: codes

<!-- TABLE:B32-code-full:BEGIN -->
| instance | n | columns | distance | ours | dist-m4ri CC+RW | CP-SAT | Gurobi | Qubitserf CC | Qubitserf BZ | Qubitserf MITM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| code_bb90 | 90 | 90 | 10 |  |  |  |  |  |  | mem |
| code_bb108 | 108 | 108 | 10 |  |  |  |  |  |  | skip |
| code_bb144 | 144 | 144 | 12 |  |  | 59.5 s |  |  | 443 s* | skip |
| code_bb288 | 288 | 288 | 18 |  | 17..18 | 1..18 | 2006 s | 2026 s* | t/o | skip |
| code_cornucopia_1044 | 1044 | 1044 | 12† |  | 3394 s | 6..12 | 7..12 | 1633 s* | t/o | mem |
| code_w8bb_144_6 | 144 | 144 | 15 |  | 14..15 | 14..15 | err | 1075 s* | 456 s* | mem |
| code_mm_324 | 324 | 324 | 18 |  | skip | skip | skip | t/o | t/o | skip |
| code_llmbb_360 | 360 | 360 | 24 | 54.9 s | skip | skip | skip | skip | skip | skip |
| code_balanced_390 | 390 | 390 | 16 |  | skip | skip | skip | skip | skip | skip |
| code_balanced_625 | 625 | 625 | 20 | 47.2 s | skip | skip | skip | skip | skip | skip |
| code_gala_132 | 132 | 132 | 12 |  | 1843 s | 11..12 | 212 s | 236 s* | 682 s* | mem |
| code_kasai_372 | 372 | 372 | 16 |  | 12..24 | 10..16 | 12..32 | t/o | t/o | mem |
| code_kasai_444 | 444 | 444 | 18 | 57.5 s | skip | skip | skip | skip | skip | skip |
| code_kasai_492 | 492 | 492 | 20 | 776 s | skip | skip | skip | skip | skip | skip |
| code_sdbb_200 | 200 | 200 | 12 |  |  | 1204 s |  |  | t/o | mem |
| **solved exactly** (of 15) | | | | **4** | **2** | **2** | **2** | **4** | **3** | **0** |
<!-- TABLE:B32-code-full:END -->

### 1 thread, 16 GB, 3600 s: circuits, sector problem

<!-- TABLE:B1-circuit-sector:BEGIN -->
| instance | n | columns | distance | HiGHS | SAT | RC2 | CASHWMaxSAT | enMaxCDCL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bb108_best_r6 | 108 | 3348 | 10 | 2..10 | >=6 | >=5 | >=1 | >=1 |
| gross_best_r6 | 144 | 4464 | 11 | skip | skip | skip | skip | skip |
| bb72_r6 | 72 | 2232 | 6 | 3..6 | 1406 s | 3168 s | >=1 | >=1 |
| bb90_r10 | 90 | 4590 | 8 | skip | >=5 | >=5 | skip | skip |
| bb108_r10 | 108 | 5508 | 8 | skip | skip | skip | skip | skip |
| bb144_r12 | 144 | 8784 | 10 | skip | skip | skip | skip | skip |
| bb288_r18 | 288 | 26208 | 16 | skip | skip | skip | skip | skip |
| w8bb_72 | 72 | 3096 | 8 | 2..8 | >=4 | >=5 | >=1 | >=1 |
| w8bb_144_16 | 144 | 6192 | 10 | skip | skip | skip | skip | skip |
| cornucopia_252 | 252 | 8568 | 5 | t/o | >=3 | >=3 | >=1 | >=1 |
| cornucopia_576 | 576 | 19584 | 8 | skip | skip | skip | skip | skip |
| cornucopia_900 | 900 | 30600 | 9 | skip | skip | skip | skip | skip |
| cornucopia_1044 | 1044 | 35496 | 10 | skip | skip | skip | skip | skip |
| lrgross | 144 | 4464 | 11 | 1..12 | >=5 | >=5 | >=1 | >=1 |
| mitten_150 | 150 | 9750 | 8 | 1..10 | >=4 | >=4 | >=1 | >=1 |
| mitten_300 | 300 | 11820 | >=12 | skip | skip | skip | skip | skip |
| mitten_200 | 200 | 15560 | 9 | skip | skip | skip | skip | skip |
| routing_54 | 54 | 1998 | 6 | 4..6 | 1458 s | >=5 | >=1 | >=1 |
| routing_90 | 90 | 3330 | 9 | skip | >=5 | skip | skip | skip |
| routing_110 | 110 | 4070 | 10 | skip | skip | skip | skip | skip |
| routing_140_13 | 140 | 5180 | 12 | skip | skip | skip | skip | skip |
| routing_200_24 | 200 | 11700 | 10 | skip | skip | skip | skip | skip |
| sdbb_64 | 64 | 2752 | 8 | 2..8 | >=4 | >=5 | >=1 | >=1 |
| sdbb_120 | 120 | 5160 | 12 | skip | skip | skip | skip | skip |
| shift_120d | 120 | 3720 | 8 | 2..13 | >=5 | >=5 | >=1 | >=1 |
| star_42 | 42 | 1806 | 6 | 5..6 | >=4 | >=5 | >=1 | >=1 |
| surface_d7 | 49 | 883 | 7 |  |  |  | 2165 s |  |
| surface_d9 | 81 | 1945 | 9 | 6..9 | >=7 | >=7 | >=1 | >=1 |
| surface_d11 | 121 | 3631 | 11 | skip | skip | skip | skip | skip |
| surface_d13 | 169 | 6085 | 13 | skip | skip | skip | skip | skip |
| surface_d15 | 225 | 9451 | 15 | skip | skip | skip | skip | skip |
| surface_d17 | 289 | 13873 | 17 | skip | skip | skip | skip | skip |
| surface_d19 | 361 | 19495 | 19 | skip | skip | skip | skip | skip |
| surface_d21 | 441 | 26461 | 21 | skip | skip | skip | skip | skip |
| surface_d23 | 529 | 34915 | 23 | skip | skip | skip | skip | skip |
| surface_d25 | 625 | 45001 | 25 | skip | skip | skip | skip | skip |
| walkingcat_54 | 54 | 2322 | 8 | 3..9 | >=4 | >=5 | >=1 | >=1 |
| **solved exactly** (of 37) | | | | **0** | **2** | **1** | **1** | **0** |
<!-- TABLE:B1-circuit-sector:END -->

### 1 thread, 3600 s: circuits, raw detector error model

<!-- TABLE:B1-circuit-full:BEGIN -->
| instance | n | columns | distance | RC2 (Stim WCNF) | CASHWMaxSAT (Stim WCNF) | enMaxCDCL (Stim WCNF) |
|---|---:|---:|---:|---:|---:|---:|
| bb108_best_r6 | 108 | 24246 | 10 | >=3 | >=1 | >=1 |
| gross_best_r6 | 144 | 32328 | 11 | skip | skip | skip |
| bb72_r6 | 72 | 16164 | 6 | >=3 | >=1 | >=1 |
| bb90_r10 | 90 | 34965 | 8 | skip | skip | skip |
| bb108_r10 | 108 | 41958 | 8 | skip | skip | skip |
| bb144_r12 | 144 | 67752 | 10 | skip | skip | skip |
| bb288_r18 | 288 | 206352 | 16 | skip | skip | skip |
| w8bb_72 | 72 | 23904 | 8 | >=3 | >=1 | >=1 |
| w8bb_144_16 | 144 | 47808 | 10 | skip | skip | skip |
| cornucopia_252 | 252 | 65450 | 5 | >=2 | >=1 | >=1 |
| cornucopia_576 | 576 | 149760 | 8 | skip | skip | skip |
| cornucopia_900 | 900 | 234000 | 9 | skip | skip | skip |
| cornucopia_1044 | 1044 | 271440 | 10 | skip | skip | skip |
| lrgross | 144 | 31488 | 11 | >=2 | >=1 | >=1 |
| mitten_150 | 150 | 76395 | 8 | >=2 | >=1 | >=1 |
| mitten_300 | 300 | 87780 | >=12 | skip | skip | skip |
| mitten_200 | 200 | 123792 | 9 | skip | skip | skip |
| routing_54 | 54 | 14958 | 6 | >=3 | >=1 | >=1 |
| routing_90 | 90 | 25020 | 9 | skip | skip | skip |
| routing_110 | 110 | 30580 | 10 | skip | skip | skip |
| routing_140_13 | 140 | 38920 | 12 | skip | skip | skip |
| routing_200_24 | 200 | 95200 | 10 | skip | skip | skip |
| sdbb_64 | 64 | 21248 | 8 | >=3 | >=1 | >=1 |
| sdbb_120 | 120 | 39840 | 12 | skip | skip | skip |
| shift_120d | 120 | 27000 | 8 | >=3 | >=1 | >=1 |
| star_42 | 42 | 13902 | 6 | >=3 | >=1 | >=1 |
| color_d7 | 37 | 3651 | 4† |  |  | 1010 s |
| color_d9 | 61 | 7683 | ? | >=4 | >=1 | >=1 |
| color_d11 | 91 | 16422 | ? | skip | skip | skip |
| surface_d5 | 25 | 1677 | 5 |  | >=1 | 1516 s |
| surface_d7 | 49 | 5471 | 7 | >=5 | skip | >=1 |
| surface_d9 | 81 | 12705 | 9 | skip | skip | skip |
| surface_d11 | 121 | 24483 | 11 | skip | skip | skip |
| surface_d13 | 169 | 41909 | 13 | skip | skip | skip |
| surface_d15 | 225 | 66087 | 15 | skip | skip | skip |
| surface_d17 | 289 | 98121 | 17 | skip | skip | skip |
| surface_d19 | 361 | 139115 | 19 | skip | skip | skip |
| surface_d21 | 441 | 190173 | 21 | skip | skip | skip |
| surface_d23 | 529 | 252399 | 23 | skip | skip | skip |
| surface_d25 | 625 | 326897 | 25 | skip | skip | skip |
| walkingcat_54 | 54 | 17820 | 8 | >=3 | >=1 | >=1 |
| **solved exactly** (of 41) | | | | **0** | **0** | **2** |
<!-- TABLE:B1-circuit-full:END -->

### 1 thread, 3600 s: codes

<!-- TABLE:B1-code-full:BEGIN -->
| instance | n | columns | distance | HiGHS | SAT | RC2 | CASHWMaxSAT | enMaxCDCL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| code_bb288 | 288 | 288 | 18 | 9..18 | >=11 | >=13 | >=1 | >=1 |
| code_cornucopia_1044 | 1044 | 1044 | >=12 | t/o | >=5 | >=6 | >=1 | >=1 |
| code_w8bb_144_6 | 144 | 144 | 15 | 12..15 | >=10 | >=11 | >=1 | >=1 |
| code_mm_324 | 324 | 324 | 18 | skip | skip | skip | skip | skip |
| code_llmbb_360 | 360 | 360 | 24 | skip | skip | skip | skip | skip |
| code_balanced_390 | 390 | 390 | 16 | skip | skip | skip | skip | skip |
| code_balanced_625 | 625 | 625 | 20 | skip | skip | skip | skip | skip |
| code_gala_132 | 132 | 132 | 12 | 3118 s | >=7 | >=8 | >=1 | >=1 |
| code_kasai_372 | 372 | 372 | 16 | 7..44 | >=6 | >=7 | >=1 | >=1 |
| code_kasai_444 | 444 | 444 | 18 | skip | skip | skip | skip | skip |
| code_kasai_492 | 492 | 492 | 20 | skip | skip | skip | skip | skip |
| code_sdbb_200 | 200 | 200 | 12 |  | >=10 | >=11 | >=1 |  |
| **solved exactly** (of 12) | | | | **1** | **0** | **0** | **0** | **0** |
<!-- TABLE:B1-code-full:END -->

## Ablation of our pipeline (1 thread, 600 s, sector problem)

One component switched off per column; the full pipeline is the column "ours" of the first tier.

<!-- TABLE:ablation:BEGIN -->
| instance | n | columns | distance | ours, collapse off | ours, collapse off lift off window off | ours, cover off | ours, lift off | ours, symmetry off | ours, symmetry off cover off collapse off lift off window off | ours, window off |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bb108_best_r6 | 108 | 3348 | 10 | 12.3 s | 12.9 s | 7.5 s | 12.9 s | 9..10 | 440 s | 12.5 s |
| gross_best_r6 | 144 | 4464 | 11 | 72.0 s | 81.5 s | 55.6 s | 80.3 s | 10..11 | >=10 | 74.1 s |
| bb72_r6 | 72 | 2232 | 6 | 0.2 s | 0.3 s | 0.2 s | 0.4 s | 0.5 s | 0.6 s | 0.4 s |
| bb90_r10 | 90 | 4590 | 8 | 0.4 s | 1.5 s | 0.4 s | 1.2 s | 4.1 s | 13.0 s | 1.4 s |
| bb108_r10 | 108 | 5508 | 8 | 0.5 s | 1.8 s | 0.5 s | 1.6 s | 3.4 s | 16.7 s | 1.8 s |
| bb144_r12 | 144 | 8784 | 10 | 1.4 s | 56.7 s | 1.3 s | 28.0 s | 39.1 s | >=9 | 17.6 s |
| bb288_r18 | 288 | 26208 | 16 | >=1 | >=11 | >=13 | >=14 | >=12 | >=8 | >=14 |
| w8bb_72 | 72 | 3096 | 8 | 4.3 s | 6.4 s | 3.1 s | 4.1 s | 48.0 s | 24.5 s | 6.7 s |
| w8bb_144_16 | 144 | 6192 | 10 | 154 s | 182 s | 124 s | 161 s | 8..10 | >=8 | 192 s |
| cornucopia_252 | 252 | 8568 | 5 | 4.3 s | 4.0 s | 1.6 s | 1.6 s | 2.5 s | 3.6 s | 1.8 s |
| cornucopia_576 | 576 | 19584 | 8 | 6..8 | >=7 | 378 s | 374 s | >=8 | >=7 | >=8 |
| cornucopia_900 | 900 | 30600 | 9 | >=1 | >=7 | >=8 | >=9 | >=7 | >=6 | >=9 |
| cornucopia_1044 | 1044 | 35496 | 10 | skip | skip | >=8 | >=9 | skip | skip | skip |
| lrgross | 144 | 4464 | 11 | 10..11 | >=10 | 7.3 s | 20.6 s | 274 s | >=9 | 19.8 s |
| mitten_150 | 150 | 9750 | 8 | 6..8 | >=6 | 108 s | 335 s | 434 s | >=7 | 130 s |
| mitten_300 | 300 | 11820 | >=12 | >=1 | >=7 | >=9 | >=9 | >=8 | >=7 | >=9 |
| mitten_200 | 200 | 15560 | 9 | skip | skip | >=9 | >=8 | >=8 | skip | >=8 |
| routing_54 | 54 | 1998 | 6 | 0.8 s | 0.8 s | 0.8 s | 0.8 s | 0.7 s | 0.6 s | 0.8 s |
| routing_90 | 90 | 3330 | 9 | 5.2 s | 6.5 s | 3.6 s | 5.4 s | 139 s | 94.6 s | 6.7 s |
| routing_110 | 110 | 4070 | 10 | 35.1 s | 34.8 s | 20.7 s | 35.1 s | 9..11 | >=9 | 35.0 s |
| routing_140_13 | 140 | 5180 | 12 | 11..13 | >=11 | 11..13 | 11..13 | >=10 | >=9 | >=11 |
| routing_200_24 | 200 | 11700 | 10 | 9..10 | >=8 | 9..10 | 8..10 | skip | skip | >=9 |
| sdbb_64 | 64 | 2752 | 8 | 3.7 s | 4.7 s | 2.8 s | 3.8 s | 59.0 s | 34.3 s | 4.8 s |
| sdbb_120 | 120 | 5160 | 12 | 11..12 | >=10 | 11..12 | 10..12 | >=10 | >=8 | >=11 |
| shift_120d | 120 | 3720 | 8 | 25.3 s | 2.3 s | 32.7 s | 2.6 s | 36.5 s | 6.3 s | 32.8 s |
| star_42 | 42 | 1806 | 6 | 0.7 s | 0.7 s | 0.7 s | 0.7 s | 2.0 s | 1.2 s | 0.8 s |
| surface_d3 | 9 | 55 | 3 | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s |
| surface_d5 | 25 | 301 | 5 | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s | 0.1 s |
| surface_d7 | 49 | 883 | 7 | 0.2 s | 0.2 s | 0.1 s | 0.1 s | 0.1 s | 0.2 s | 0.1 s |
| surface_d9 | 81 | 1945 | 9 | 0.9 s | 0.9 s | 0.1 s | 0.1 s | 0.1 s | 0.9 s | 0.1 s |
| surface_d11 | 121 | 3631 | 11 | 35.8 s | 35.6 s | 0.2 s | 0.1 s | 0.2 s | 35.5 s | 0.2 s |
| surface_d13 | 169 | 6085 | 13 | 12..13 | >=12 | 0.3 s | 0.2 s | 0.3 s | >=12 | 0.2 s |
| surface_d15 | 225 | 9451 | 15 | 12..15 | >=12 | 0.7 s | 0.5 s | 0.7 s | >=12 | 0.7 s |
| surface_d17 | 289 | 13873 | 17 | skip | skip | 3.4 s | 1.9 s | 3.4 s | skip | 3.4 s |
| surface_d19 | 361 | 19495 | 19 | skip | skip | 26.0 s | 12.2 s | 25.8 s | skip | 26.0 s |
| surface_d21 | 441 | 26461 | 21 | skip | skip | 184 s | 62.4 s | 184 s | skip | 182 s |
| surface_d23 | 529 | 34915 | 23 | skip | skip | >=23 | 549 s | >=23 | skip | >=23 |
| surface_d25 | 625 | 45001 | 25 | skip | skip | >=22 | >=22 | >=22 | skip | >=22 |
| walkingcat_54 | 54 | 2322 | 8 | 7.0 s | 6.5 s | 2.4 s | 6.3 s | 107 s | 23.7 s | 6.6 s |
| **solved exactly** (of 39) | | | | **21** | **21** | **29** | **30** | **24** | **17** | **28** |
<!-- TABLE:ablation:END -->

## The instances of the prior benchmark (arXiv:2603.22532)

Webster, Jacob and Higgott benchmark exact and heuristic distance methods on classical codes,
quantum codes and circuits, and publish their instances and per-method results in their codeDistance
package (github.com/m-webster/codeDistancePYPI, commit a4afe9c, MIT licence). Here are all of its CSS
instances: 103 codes (hyperbolic surface and colour codes, lifted-product, bivariate bicycle and
quantum Tanner codes) and 23 circuits (rotated surface code, colour code with the midout and the
superdense cycle, bivariate bicycle codes). Their classical and non-CSS codes are left out. The two
long-range-noise variants of their bivariate bicycle circuits are not separate problems: they have
the same mechanisms as the plain circuits, only other probabilities.

- **Same problems.** Circuits are their own `.stim` files. Their problem is the detector error model
  filtered to the detectors of the observable's basis; for every circuit this is exactly our sector
  problem, column for column (checked by `bench/export_wjh.py`). Codes are built by their own
  functions (`papers/codedistance_export.py`), and their (n, k) agree with their tables in order.
  For a CSS code they compute one distance, that of the Z-type logical operators (H = HX, L = LX);
  so do we here.
- **Their protocol.** Five exact methods (Gurobi, MIP with SCIP, the MaxSAT solver CLISAT,
  dist-m4ri connected clusters, Magma's Brouwer-Zimmermann), each with one thread and an 8-hour
  limit on one node of their cluster. A run of theirs counts as exact when it returned a distance
  before the limit; read this way, their sheets give exactly the counts of their own summary sheets.
- **Ours.** The first tier as above for our pipeline, Gurobi and dist-m4ri CC
  (`results/bench_wjh/`); the second tier (32 threads, 90 GB, one hour) for our pipeline only
  (`results/bench_wjh_tierB/`). Gurobi and dist-m4ri were not given a second tier here: the paper ran
  both itself for eight hours on every instance, and those runs are in the last columns.
  Symmetries are used where the structure gives them directly: lattice translations of the
  bivariate bicycle codes and circuits, the cyclic shift of the quasi-cyclic lifted-product codes.
  Hyperbolic and quantum Tanner codes get the plain search.

<!-- TABLE:wjh:BEGIN -->
| family | instances | ours, tier 1 | ours, both tiers | Gurobi, tier 1 | dist-m4ri CC, tier 1 | theirs, 8 h: Gurobi / MIP-SCIP / CLISAT / m4riCC / Magma | any of theirs |
|---|---:|---:|---:|---:|---:|---|---:|
| surface-code circuits | 5 | 5 | 5 | 3 | 4 | 3 / 3 / 2 / 4 / 2 | 4 |
| colour-code circuits, midout | 5 | 5 | 5 | 5 | 5 | 5 / 4 / 5 / 5 / 4 | 5 |
| colour-code circuits, superdense | 6 | 5 | 5 | 3 | 4 | 4 / 4 / 4 / 4 / 3 | 5 |
| bivariate bicycle circuits | 7 | 4 | 5 | 0 | 1 | 1 / 0 / 0 / 1 / 0 | 1 |
| hyperbolic surface codes | 21 | 21 | 21 | 15 | 21 | 21 / 21 / 21 / 21 / 14 | 21 |
| hyperbolic colour codes | 21 | 21 | 21 | 15 | 20 | 20 / 17 / 20 / 21 / 9 | 21 |
| lifted-product codes | 19 | 14 | 19 | 5 | 5 | 6 / 6 / 6 / 6 / 3 | 6 |
| bivariate bicycle codes | 20 | 6 | 8 | 5 | 5 | 5 / 5 / 5 / 5 / 1 | 5 |
| quantum Tanner codes | 22 | 5 | 7 | 4 | 2 | 5 / 4 / 4 / 4 / 3 | 5 |
| **all** | 126 | **86** | **96** | 55 | 67 | 70 / 64 / 67 / 71 / 39 | 73 |

- Our exact values agree with all 73 values certified by their exact methods.
- Below their best known value: wjh_bb288_circuit: 16 (their best 24)

<details><summary>Surface-code circuits (5 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_surface_d3 | 9 | 1 | 55 | 3 | 3 | 0.2 s |  | 0.3 s | 0.0 s | MIP-SCIP, 0.0 s |
| wjh_surface_d5 | 25 | 1 | 301 | 5 | 5 | 0.1 s |  | 0.5 s | 0.0 s | m4riCC, 0.1 s |
| wjh_surface_d7 | 49 | 1 | 883 | 7 | 7 | 0.1 s |  | 29.5 s | 0.2 s | m4riCC, 0.9 s |
| wjh_surface_d9 | 81 | 1 | 1945 | 9 | 9 | 0.1 s |  | 6..9 | 20.7 s | m4riCC, 253 s |
| wjh_surface_d11 | 121 | 1 | 3631 | 11 | 11 | 0.2 s |  | 5..11 | >=10 | none |

</details>

<details><summary>Colour-code circuits, midout (5 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_midout_d3 | 7 | 1 | 33 | 2 | 2 | 0.2 s |  | 0.3 s | 0.0 s | CLISAT, 0.0 s |
| wjh_midout_d5 | 19 | 1 | 171 | 3 | 3 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_midout_d7 | 37 | 1 | 475 | 4 | 4 | 0.1 s |  | 0.5 s | 0.0 s | m4riCC, 0.1 s |
| wjh_midout_d9 | 61 | 1 | 1041 | 5 | 5 | 0.2 s |  | 6.3 s | 0.0 s | m4riCC, 0.3 s |
| wjh_midout_d11 | 91 | 1 | 1907 | 6 | 6 | 0.2 s |  | 288 s | 0.3 s | m4riCC, 2.2 s |

</details>

<details><summary>Colour-code circuits, superdense (6 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_superdense_d3 | 7 | 1 | 70 | 3 | 3 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_superdense_d5 | 19 | 1 | 414 | 5 | 5 | 0.2 s |  | 1.1 s | 0.0 s | m4riCC, 0.1 s |
| wjh_superdense_d7 | 37 | 1 | 1248 | 7 | 7 | 2.0 s |  | 6..7 | 14.6 s | m4riCC, 46.2 s |
| wjh_superdense_d9 | 61 | 1 | 2788 | 9 | 9 | 391 s |  | 5..9 | >=7 | Magma, 28764 s |
| wjh_superdense_d11 | 91 | 1 | 5250 | 10..11 | 11 | 8..11 | 10..11 | skip | >=7 | none |
| wjh_superdense_mpp_d15 | 169 | 1 | 169 | 15 | 15 | 0.3 s |  | 45.1 s | 4.2 s | m4riCC, 6.4 s |

</details>

<details><summary>Bivariate bicycle circuits (7 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_bb72_circuit | 72 | 12 | 2232 | 6 | 6 | 0.2 s |  | 4..6 | 3.2 s | m4riCC, 11.0 s |
| wjh_bb90_circuit | 90 | 8 | 4590 | 8 | 8 | 0.4 s |  | 3..9 | >=7 | none |
| wjh_bb108_circuit | 108 | 8 | 5508 | 8 | 8 | 0.5 s |  | skip | >=7 | none |
| wjh_bb144_circuit | 144 | 12 | 8784 | 10 | 10 | 1.4 s |  | skip | skip | none |
| wjh_bb288_circuit | 288 | 12 | 26208 | 16 | 24 | >=14 | 299 s | skip | skip | none |
| wjh_bb360_circuit | 360 | 12 | 43560 | >=17 | 88 | >=14 | >=17 | skip | skip | none |
| wjh_bb756_circuit | 756 | 16 | 129276 | ? | 56 | skip | skip | skip | skip | none |

</details>

<details><summary>Hyperbolic surface codes (21 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_hsc_00_n6 | 6 | 1 | 6 | 2 | 2 | 0.1 s |  | 0.3 s | 0.0 s | MIP-SCIP, 0.0 s |
| wjh_hsc_01_n24 | 24 | 4 | 24 | 2 | 2 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_02_n48 | 48 | 6 | 48 | 3 | 3 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_03_n84 | 84 | 9 | 84 | 4 | 4 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_04_n84 | 84 | 9 | 84 | 3 | 3 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.1 s |
| wjh_hsc_05_n96 | 96 | 10 | 96 | 4 | 4 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.1 s |
| wjh_hsc_06_n168 | 168 | 16 | 168 | 4 | 4 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.1 s |
| wjh_hsc_07_n168 | 168 | 16 | 168 | 4 | 4 | 0.1 s |  | 0.5 s | 0.0 s | m4riCC, 0.1 s |
| wjh_hsc_08_n180 | 180 | 17 | 180 | 5 | 5 | 0.1 s |  | 1.5 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_09_n252 | 252 | 23 | 252 | 4 | 4 | 0.1 s |  | 0.7 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_10_n360 | 360 | 32 | 360 | 5 | 5 | 0.1 s |  | 2.5 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_11_n384 | 384 | 34 | 384 | 4 | 4 | 0.1 s |  | 0.5 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_12_n504 | 504 | 44 | 504 | 6 | 6 | 0.1 s |  | 329 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_13_n504 | 504 | 44 | 504 | 6 | 6 | 0.1 s |  | 278 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_14_n540 | 540 | 47 | 540 | 5 | 5 | 0.1 s |  | 45.2 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hsc_15_n768 | 768 | 66 | 768 | 6 | 6 | 0.2 s |  | 4..6 | 0.1 s | m4riCC, 0.1 s |
| wjh_hsc_16_n1008 | 1008 | 86 | 1008 | 6 | 6 | 0.2 s |  | 3..6 | 0.1 s | m4riCC, 0.1 s |
| wjh_hsc_17_n1080 | 1080 | 92 | 1080 | 6 | 6 | 0.2 s |  | skip | 0.1 s | m4riCC, 0.1 s |
| wjh_hsc_18_n1080 | 1080 | 92 | 1080 | 5 | 5 | 0.2 s |  | skip | 0.1 s | m4riCC, 0.1 s |
| wjh_hsc_19_n1224 | 1224 | 104 | 1224 | 6 | 6 | 0.2 s |  | skip | 0.1 s | m4riCC, 0.1 s |
| wjh_hsc_20_n1224 | 1224 | 104 | 1224 | 6 | 6 | 0.2 s |  | skip | 0.1 s | m4riCC, 0.1 s |

</details>

<details><summary>Hyperbolic colour codes (21 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_hcc_00_n4 | 4 | 2 | 4 | 2 | 2 | 0.1 s |  | 0.3 s | 0.0 s | MIP-SCIP, 0.0 s |
| wjh_hcc_01_n16 | 16 | 8 | 16 | 2 | 2 | 0.1 s |  | 0.3 s | 0.0 s | CLISAT, 0.0 s |
| wjh_hcc_02_n32 | 32 | 12 | 32 | 4 | 4 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hcc_03_n56 | 56 | 14 | 56 | 6 | 6 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hcc_04_n56 | 56 | 14 | 56 | 4 | 4 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hcc_05_n64 | 64 | 20 | 64 | 4 | 4 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hcc_06_n112 | 112 | 28 | 112 | 6 | 6 | 0.1 s |  | 1.1 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hcc_07_n112 | 112 | 28 | 112 | 8 | 8 | 0.1 s |  | 4.3 s | 0.1 s | m4riCC, 0.2 s |
| wjh_hcc_08_n120 | 120 | 30 | 120 | 8 | 8 | 0.1 s |  | 9.1 s | 0.1 s | m4riCC, 0.2 s |
| wjh_hcc_09_n168 | 168 | 46 | 168 | 6 | 6 | 0.1 s |  | 2.1 s | 0.0 s | m4riCC, 0.0 s |
| wjh_hcc_10_n240 | 240 | 60 | 240 | 8 | 8 | 0.2 s |  | 59.0 s | 0.3 s | m4riCC, 0.4 s |
| wjh_hcc_11_n256 | 256 | 68 | 256 | 8 | 8 | 0.1 s |  | 46.0 s | 0.2 s | m4riCC, 0.4 s |
| wjh_hcc_12_n336 | 336 | 88 | 336 | 6 | 6 | 0.1 s |  | 13.7 s | 0.0 s | m4riCC, 0.1 s |
| wjh_hcc_13_n336 | 336 | 88 | 336 | 8 | 8 | 0.2 s |  | 122 s | 0.3 s | m4riCC, 0.4 s |
| wjh_hcc_14_n360 | 360 | 90 | 360 | 8 | 8 | 0.2 s |  | 313 s | 0.4 s | m4riCC, 0.6 s |
| wjh_hcc_15_n512 | 512 | 132 | 512 | 8 | 8 | 0.2 s |  | 4..8 | 0.5 s | m4riCC, 0.7 s |
| wjh_hcc_16_n672 | 672 | 172 | 672 | 10 | 10 | 0.5 s |  | 2..10 | 14.3 s | m4riCC, 22.5 s |
| wjh_hcc_17_n720 | 720 | 184 | 720 | 8 | 8 | 0.2 s |  | skip | 0.6 s | m4riCC, 0.8 s |
| wjh_hcc_18_n720 | 720 | 180 | 720 | 10 | 10 | 0.5 s |  | skip | 20.1 s | m4riCC, 30.5 s |
| wjh_hcc_19_n816 | 816 | 204 | 816 | 12 | 12 | 5.9 s |  | skip | >=11 | m4riCC, 1149 s |
| wjh_hcc_20_n816 | 816 | 204 | 816 | 6 | 6 | 0.2 s |  | skip | 0.1 s | m4riCC, 0.1 s |

</details>

<details><summary>Lifted-product codes (19 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_lp_aj01 | 34 | 20 | 34 | 2 | 2 | 0.1 s |  | 0.3 s | 0.0 s | CLISAT, 0.0 s |
| wjh_lp_aj04 | 136 | 32 | 136 | 4 | 4 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_lp_aj07 | 238 | 44 | 238 | 6 | 6 | 0.1 s |  | 3.1 s | 0.0 s | m4riCC, 0.0 s |
| wjh_lp_aj10 | 340 | 56 | 340 | 8 | 8 | 0.1 s |  | 29.3 s | 0.3 s | m4riCC, 0.4 s |
| wjh_lp_aj13 | 442 | 68 | 442 | 10 | 10 | 0.1 s |  | 496 s | 13.9 s | m4riCC, 20.4 s |
| wjh_lp_xu16 | 544 | 80 | 544 | 12 | 12 | 0.2 s |  | 6..12 | >=11 | m4riCC, 984 s |
| wjh_lp_xu21 | 714 | 100 | 714 | 16 | 16 | 1.5 s |  | 3..16 | >=11 | none |
| wjh_lp_xu30 | 1020 | 136 | 1020 | 16 | 16 | 1.2 s |  | skip | skip | none |
| wjh_lp_pk31 | 1054 | 140 | 1054 | 20 | 20 | 58.6 s |  | skip | skip | none |
| wjh_lp_xu42 | 1428 | 184 | 1428 | 24 | 24 | >=22 | 133 s | skip | skip | none |
| wjh_lp_aj52 | 1768 | 224 | 1768 | 22 | 22 | 473 s |  | skip | skip | none |
| wjh_lp_aj58 | 1972 | 248 | 1972 | 20 | 20 | 53.4 s |  | skip | skip | none |
| wjh_lp_aj60 | 2040 | 256 | 2040 | 20 | 20 | 66.5 s |  | skip | skip | none |
| wjh_lp_aj61 | 2074 | 260 | 2074 | 24 | 24 | >=22 | 93.5 s | skip | skip | none |
| wjh_lp_aj67 | 2278 | 284 | 2278 | 22 | 22 | 396 s |  | skip | skip | none |
| wjh_lp_aj73 | 2482 | 308 | 2482 | 24 | 24 | >=22 | 70.5 s | skip | skip | none |
| wjh_lp_aj80 | 2720 | 336 | 2720 | 22 | 22 | 286 s |  | skip | skip | none |
| wjh_lp_aj85 | 2890 | 356 | 2890 | 24 | 24 | >=22 | 68.6 s | skip | skip | none |
| wjh_lp_aj95 | 3230 | 396 | 3230 | 24 | 24 | >=23 | 62.8 s | skip | skip | none |

</details>

<details><summary>Bivariate bicycle codes (20 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_bb_n72 | 72 | 12 | 72 | 6 | 6 | 0.1 s |  | 0.3 s | 0.0 s | m4riCC, 0.0 s |
| wjh_bb_n90 | 90 | 8 | 90 | 10 | 10 | 0.1 s |  | 3.3 s | 0.2 s | m4riCC, 0.3 s |
| wjh_bb_n108 | 108 | 8 | 108 | 10 | 10 | 0.1 s |  | 4.9 s | 0.2 s | m4riCC, 0.4 s |
| wjh_bb_n144 | 144 | 12 | 144 | 12 | 12 | 0.1 s |  | 52.7 s | 3.7 s | m4riCC, 5.7 s |
| wjh_bb_n288 | 288 | 12 | 288 | 18 | 18 | 1.6 s |  | 9..18 | >=14 | none |
| wjh_bb_n360 | 360 | 12 | 360 | 24 | 24 | >=23 | 76.1 s | 7..26 | >=14 | none |
| wjh_bb_n756 | 756 | 16 | 756 | ? | 34 | skip | skip | skip | skip | none |
| wjh_bb_n216 | 216 | 8 | 216 | 10 | 10 | 0.1 s |  | 4.3 s | 0.4 s | m4riCC, 0.7 s |
| wjh_bb_n576 | 576 | 8 | 576 | 24 | 24 | >=23 | 44.3 s | skip | skip | none |
| wjh_bb_n864 | 864 | 4 | 864 | ? | 40 | skip | skip | skip | skip | none |
| wjh_bb_n648 | 648 | 4 | 648 | >=28 | 32 | skip | >=28 | skip | skip | none |
| wjh_bb_n1080 | 1080 | 4 | 1080 | ? | 54 | skip | skip | skip | skip | none |
| wjh_bb_n1296 | 1296 | 4 | 1296 | ? | 46 | skip | skip | skip | skip | none |
| wjh_bb_n1152 | 1152 | 4 | 1152 | ? | 36 | skip | skip | skip | skip | none |
| wjh_bb_n1728 | 1728 | 4 | 1728 | ? | 64 | skip | skip | skip | skip | none |
| wjh_bb_n2016 | 2016 | 8 | 2016 | ? | 54 | skip | skip | skip | skip | none |
| wjh_bb_n2160 | 2160 | 8 | 2160 | ? | 64 | skip | skip | skip | skip | none |
| wjh_bb_n2520 | 2520 | 8 | 2520 | ? | 50 | skip | skip | skip | skip | none |
| wjh_bb_n2592 | 2592 | 8 | 2592 | ? | 36 | skip | skip | skip | skip | none |
| wjh_bb_n3024 | 3024 | 4 | 3024 | ? | 78 | skip | skip | skip | skip | none |

</details>

<details><summary>Quantum Tanner codes (22 instances)</summary>

| instance | n | k | columns | distance | their best | ours t1 | ours t2 | Gurobi t1 | dist-m4ri CC t1 | their fastest exact (8 h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wjh_qt_36_8_4 | 36 | 8 | 36 | 4 | 4 | 0.2 s |  | 0.3 s | 0.0 s | CLISAT, 0.0 s |
| wjh_qt_72_8_8 | 72 | 8 | 72 | 8 | 8 | 0.1 s |  | 1.1 s | 0.1 s | m4riCC, 0.2 s |
| wjh_qt_108_2_12 | 108 | 2 | 108 | 12 | 12 | 0.6 s |  | 30.7 s | >=12 | Gurobi, 53.4 s |
| wjh_qt_144_2_13 | 144 | 2 | 144 | 13 | 13 | 3.1 s |  | 257 s | >=12 | Gurobi, 338 s |
| wjh_qt_180_2_17 | 180 | 2 | 180 | 17 | 17 | 243 s |  | 10..17 | skip | Gurobi, 12287 s |
| wjh_qt_216_4_18 | 216 | 4 | 216 | 18 | 18 | >=17 | 27.2 s | 10..18 | skip | none |
| wjh_qt_252_2_21 | 252 | 2 | 252 | 22 | 22 | >=18 | 2390 s | skip | skip | none |
| wjh_qt_288_2_24 | 288 | 2 | 288 | >=22 | 24 | skip | >=22 | skip | skip | none |
| wjh_qt_324_4_25 | 324 | 4 | 324 | ? | 25 | skip | skip | skip | skip | none |
| wjh_qt_360_4_24 | 360 | 4 | 360 | ? | 24 | skip | skip | skip | skip | none |
| wjh_qt_396_4_26 | 396 | 4 | 396 | ? | 27 | skip | skip | skip | skip | none |
| wjh_qt_432_8_33 | 432 | 8 | 432 | ? | 30 | skip | skip | skip | skip | none |
| wjh_qt_468_4_31 | 468 | 4 | 468 | ? | 29 | skip | skip | skip | skip | none |
| wjh_qt_496_2_32 | 496 | 2 | 496 | ? | 30 | skip | skip | skip | skip | none |
| wjh_qt_504_2_45 | 504 | 2 | 504 | ? | 39 | skip | skip | skip | skip | none |
| wjh_qt_540_4_40 | 540 | 4 | 540 | ? | 39 | skip | skip | skip | skip | none |
| wjh_qt_576_2_57 | 576 | 2 | 576 | ? | 39 | skip | skip | skip | skip | none |
| wjh_qt_576_2_59 | 576 | 2 | 576 | ? | 39 | skip | skip | skip | skip | none |
| wjh_qt_612_2_52 | 612 | 2 | 612 | ? | 41 | skip | skip | skip | skip | none |
| wjh_qt_648_10_71 | 648 | 10 | 648 | ? | 33 | skip | skip | skip | skip | none |
| wjh_qt_648_14_50 | 648 | 14 | 648 | ? | 29 | skip | skip | skip | skip | none |
| wjh_qt_684_2_29 | 684 | 2 | 684 | ? | 29 | skip | skip | skip | skip | none |

</details>
<!-- TABLE:wjh:END -->

## What the comparison does not cover

- Gurobi runs through its command-line solver on an LP file (no Python interface is installed on
  the machine), so its time includes reading the model; the adapter gives it the remaining time
  less a small margin for that. Its runs were made on 15 October 2026, when the machine carried more
  load from other users than during the other passes (load average 180 to 320 of 384 threads); each
  run still had its own pinned cores. Two runs were repeated: the 32-thread run on surface d = 11
  stopped after 52 minutes with Gurobi's status "interrupted" and no log kept; repeated, it ended
  after 40 minutes with Gurobi's own "out of memory" error at the 90 GB limit (the harness limits the
  address space, which a 32-thread solver uses more of than resident memory), recorded as `mem`.
  One first-tier run (sdbb_120, raw model) had read an incumbent file while Gurobi was still writing
  it; the adapter now accepts an incumbent only when its fault count equals the objective in the
  file, and the repeated run is the record. A licence-service failure at start-up is retried once.
- Every tool ran with its defaults or the settings its documentation recommends, on one encoding
  per method (plus Stim's own WCNF for MaxSAT). A specialist could probably tune each of them
  further; none was tuned per instance, ours included.
- Our method uses information the others do not get: the check and round of each detector (for the
  collapse) and the stored symmetries. The sector variant hands the others the exact reduction; the
  collapsed tables show what the relaxation alone gives them.
- The instance set leans to the circuits this project studied. The Stim surface- and color-code
  families were added to counter that.
- The Stim-WCNF MaxSAT pass was run twice for the circuits with `REPEAT` blocks (BB72, [[90,8,10]]
  and the larger standard BB circuits, color d = 11): the first time our adapter rejected Stim's
  variable numbering for them (Stim keeps loops folded, so it has more variables than merged
  mechanisms). The records in the tables are from the corrected run, on the same limits, made while
  another user loaded the second socket of the machine.
- Two second-tier runs were made singly after the main pass: ours on mitten 200 (the give-up rule
  had skipped it because mitten 300 has fewer columns and came first), and dist-m4ri and CP-SAT on
  the color-code circuits (left out of the 32-thread pass by the driver). They ran with the same
  limits while the single-thread pass used other cores of the socket.
- Times are single runs, wall clock, with other benchmark jobs on other cores of the same socket.

## Reproduce

```sh
python bench/export_all.py                       # instances (large ones on a server)
python bench/run_matrix.py --methods ... --instances all --variants sector,full \
       --threads 1 --time-limit 600 --mem-gb 16 --jobs 18 --cpus 0-95 --out results/bench --give-up 2
python bench/tier_b.py fix collapsed ablation b32 b1 stimsat b1s
python bench/tier_b.py gurobi                    # needs gurobi_cl ($GUROBI_HOME/bin) or gurobipy
# instances of arXiv:2603.22532: their package in papers/downloads/codedistance
python papers/codedistance_export.py papers/downloads/codedistance papers/downloads/codedistance_codes.json
python bench/export_wjh.py
python bench/tier_b.py wjh1 wjh2
python bench/summary_table.py results/bench --variant sector --track circuit
python bench/make_benchmark_md.py
```
