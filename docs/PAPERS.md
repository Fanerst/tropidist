# Circuit distance of recently published qLDPC memories

Question: recent papers report qLDPC codes with large distance. What is the distance of the
*circuits* they publish?

All numbers come from `results/papers/*.json`; the full tables are in
[PAPERS_RESULTS.md](PAPERS_RESULTS.md). Methods are described in [BB_CIRCUITS.md](BB_CIRCUITS.md).

## Scope

Only papers that publish a syndrome-extraction circuit or schedule were tested, as agreed.
Deferred until a circuit is available: weight-8 bivariate bicycle codes (arXiv:2609.06572) and
multivariate multicycle codes (arXiv:2601.18879). Not testable because no check matrices are
released: multi-agent discovery (2608.08996), ZSZ-LP (2607.27644).

SciRate could not be read (bot verification), so the selection was ranked by Semantic Scholar
citation counts instead.

| paper | citations | what is published | what is claimed |
|---|---:|---|---|
| IBM bivariate bicycle, 2308.07915 | 857 | Stim circuits (tesseract-decoder test data) | [[360,12,≤24]], [[756,16,≤34]] |
| Mitten codes, 2607.28795 | 9 | check matrices, logicals, gate-by-gate "hook-free" schedules | d = 10 … 18 exact, ≤ 20, 22, 24; schedules chosen so that they "likely preserve the circuit-level distance" |
| Structured mitten codes, same paper (added 25 October 2026) | – | in the paper's repository: matrices and logicals of six codes, "hook-free" schedules for five of them, matrices of a 2×4 abelian lifted-product code | code distances ≤ 9, ≤ 12, ≤ 14, ≤ 16, ≤ 18 and ≤ 14, sampled estimates ([[1200,240,20]] appears only in the repository); no circuit distance is printed for these schedules |
| Amplified qLDPC, 2609.37231 | 0 (days old) | Python circuit builder | circuit distance ≥ 3·2^level, target 4·2^level |

## Results

<!-- RESULTS:BEGIN -->
**Mitten codes** (published "hook-free" schedules; paper's fault model). Bold = exact; otherwise certified lower bound – verified upper bound.

| code | claimed distance | circuit distance, Z basis | circuit distance, X basis | below the claim? |
|---|---:|---:|---:|---|
| [[150,30,10]] | 10 | **8** | **8** | yes |
| [[200,40,12]] | 12 | **9** | **9** | yes |
| [[300,60,14]] | 14 | **12** | **12** | yes |
| [[500,100,16]] | 16 | 11 – 16 | **9** | yes |
| [[540,108,18]] | 18 | 10 – 16 | 11 – 13 | yes |
| [[630,126,20]] | ≤ 20 | 9 – 12 | 9 – 12 | yes |
| [[780,156,22]] | ≤ 22 | 9 – 17 | 9 – 16 | yes |
| [[975,195,24]] | ≤ 24 | 9 – 17 | 9 – 19 | yes |

**Structured mitten codes** (the same paper's repository; published "hook-free" schedules, paper's fault model). Named distance: the d of the folder name, an estimate in the paper. Code distance d_X / d_Z from the matrices. Bold = exact; otherwise certified lower bound – verified upper bound.

| code | named distance | code distance d_X / d_Z | circuit distance, Z basis | circuit distance, X basis | below the named distance? |
|---|---:|---|---:|---:|---|
| [[300,60,9]] | 9 | **10** / **10** | **9** | **9** | no |
| [[330,66,12]] | 12 | **12** / **12** | **7** | **7** | yes |
| [[560,112,14]] | 14 | **14** / **14** | – | – | no schedule (abelian LP code) |
| [[600,120,14]] | 14 | **14** / **14** | **11** | **10** | yes |
| [[600,120,16]] | 16 | **16** / **16** | **10** | **11** | yes |
| [[840,168,18]] | 18 | **17** / 17 – 18 | 11 – 14 | 11 – 14 | yes |
| [[1200,240,20]] | 20 | 15 – 20 / 15 – 20 | – | – | no schedule published |

**Amplified qLDPC memories** (authors' circuits, 8 rounds for levels 0 and 1; paper's fault model).

| level | code | paper: certified ≥ | paper: target | circuit distance, Z | circuit distance, X |
|---:|---|---:|---:|---:|---:|
| 0 | [[18,4,4]] | 4 | 4 | **4** | **4** |
| 1 | [[90,8,8]] | 6 | 8 | **8** | **8** |
| 2 | [[468,16,16]] | 12 | 16 | ours ≥ 11; with the paper's bound: 12 – 16 | ours ≥ 11; with the paper's bound: 12 – 16 |

**IBM bivariate bicycle codes** (tesseract-decoder SI1000 circuits, rounds = claimed distance).

| circuit | claimed code distance | code distance (from the Z-basis data-error window) | distance within one round | circuit distance |
|---|---:|---|---|---|
| bb360_r24_X | ≤ 24 | – | 21 (exact) | 19 – 21 |
| bb360_r24_Z | ≤ 24 | 24 (exact) | 21 (exact) | 17 – 21 |
| bb756_r34_X | ≤ 34 | – | – | ≥ 15 (no informative upper bound) |
| bb756_r34_Z | ≤ 34 | ≥ 28 | – | ≥ 15 (no informative upper bound) |
<!-- RESULTS:END -->

## What the results say

**Mitten codes: the published schedules lose distance.** For every one of the eight codes there is a
verified fault set lighter than the claimed distance. Where the search could be completed the
circuit distance is exact: 8 against 10, 9 against 12, 12 against 14, and 9 against 16
([[500,100,16]], X basis). The loss comes from hook faults: an ancilla fault in the middle of a
round spreads to up to four data qubits of one weight-9 check. With data errors only, the same
search returns 10 and 12 for the two smallest codes, so the code distances themselves are as
stated. The paper selected these schedules with a randomised distance estimator; an exhaustive
search finds what it missed.

**Structured mitten codes: their published schedules lose more.** The paper's repository also
ships "hook-free" schedules for five codes of the structured subfamily (its Appendix A.4). The
paper times their syndrome-extraction cycles (Table XI) but prints no circuit distance for them.
- [[330,66,12]] has circuit distance 7 in both bases, against a code distance of exactly 12. A
  minimum fault set is seven ancilla faults alone, each after the second or third of its check's
  nine gates. Up to the check itself, each such fault is a data error of weight 2 or 3.
- [[600,120,14]] has 11 (Z) and 10 (X), and [[600,120,16]] has 10 (Z) and 11 (X), against code
  distances of exactly 14 and 16.
- [[840,168,18]] lies between 11 and 14 in both bases: weight 10 is excluded, and verified fault
  sets of weight 14 exist. Even the fault sets made of data errors and hooks after a check's
  second or third gate alone need weight 12 or more (weight 11 excluded in that class).
- [[300,60,9]] has circuit distance exactly 9 in both bases, its name, while its code distance is
  10 in both bases. The paper prints "≤ 9" for this code (Tables XI and XIII; Table VI has
  [[280,56,≤10]] in its place). So the name matches its circuit, not its code.
- The other code distances are as named: 12, 14, 16, and 14 for the abelian lifted-product code
  [[560,112,14]], whose 14 the paper calls attaining its proven ceiling. [[840,168,18]] has
  distance exactly 17: an X-type logical operator of weight 17, and weight 16 excluded in both
  types. Its sampled estimate 18 is too high (dist-m4ri's benchmark had 15–17).
- The dp=2 pipeline, run on the Stim circuits alone, confirms 9 and 7 for the two smaller codes.

**Amplified qLDPC memories: the first level is better than certified.** The seed circuit has
distance 4 and the first amplification has distance exactly 8 in both bases, the full code
distance, where the paper certifies 6 and fits its simulations with exponent 6. The second level
could not be decided: the lightest fault set found has weight 16, and the exhaustive bound reached
here (11) is below the paper's proven 12.

**IBM bivariate bicycle codes.** The [[360,12,≤24]] code has distance exactly 24: weight 23 and
below is excluded and a weight-24 logical operator is found. Its 24-round circuit has distance
between 17 and 21 in the Z basis and between 19 and 21 in the X basis (later runs with the covering
bound of [PHASE4.md](PHASE4.md)), so below 24, in line with the gross code (10 against 12) and BB288
(16 against 18). Within one round the lightest undetected fault set has weight exactly 21 in both
bases. For [[756,16,≤34]] nothing informative could be obtained beyond a lower bound of 15 on the
circuit distance and 24 on the code distance.

## How each number was obtained

- **Lower bounds** are exhaustive: every fault set up to the stated weight is excluded by the
  weight-bounded search, on a problem that is either the circuit problem itself or a relaxation
  of it. Nothing here rests on sampling.
- **Upper bounds** are explicit fault sets. Each one is checked in the full detector error model
  and inserted into the noiseless Stim circuit, which is then simulated: no detector fires and an
  observable flips. For the larger mitten codes they come from a randomised information-set
  search (`cdist/isd.c`); such a search can miss lighter fault sets, so those upper bounds may
  not be tight.
- **Mitten circuits** are built by `papers/mitten_circuit.py` from the authors' schedule files
  (github.com/a7b/yarn, commit in `papers/mitten/manifest.json`): one cycle is the X-check round
  followed by the Z-check round, 12 entangling layers each, in the published order. Because the
  two rounds are sequential, a fault's effect is seen by a single round of opposite-type checks,
  and the distance problem can be written down directly from the matrices and the gate order
  (`papers/mitten_effective.py`). That matrix-level problem and the one extracted from the Stim
  circuit have identical column sets.
- **Structured mitten circuits** are built the same way from the repository's other five schedule
  files (`papers/mitten/structured_mitten/`, same commit; the drivers take names such as
  `structured_mitten/[[330,66,12]]`). `papers/smitten_check.py` checks, for every code and basis on
  the 3-round circuit: every detector is deterministic, the sector reduction is exact, and the
  matrix-level problem has exactly the columns of the time-collapsed Stim problem and of its
  single-round window. The dp=2 pipeline run on the Stim sector problem alone
  (`papers/smitten_pipeline.py`, independent of the matrix-level construction) gives the same
  values for the two smaller codes. The deeper exhaustive levels used a depth-3 lookup table
  (`k_table` 3: about 24 times faster per thread, 143 GB per search for n = 600). Witnesses for
  [[840,168,18]] also come from an exhaustive search restricted to data errors and hooks after a
  check's second or third gate (`papers/mitten_restricted_exact.py`), the only hooks in the
  minimum fault sets of the other codes. Code distances: `papers/smitten_code_distance.py` (an
  information-set witness checked against the published matrices, then an exhaustive search
  below it).
- **Amplified circuits** are the authors' `build_memory(level, basis, rounds, p)`, reproduced gate
  for gate (asserted) with detector annotations added (`papers/amplified_circuit.py`).
- **Fault models** are the papers' own: faults on preparation, two-qubit gates (depolarizing) and
  measurement, no idle noise. Adding a depolarizing fault on every idle data qubit leaves the
  distance problem identical for the three smallest mitten codes (the others were not checked)
  and leaves the first amplified level at 8.
- **Checks.** All stored fault sets were replayed a second way (Stim's detector sampler with the
  faults as probability-1 channels, `tests/verify_witnesses.py`). The search kernels are tested
  against brute force (`tests/`), including the paths added for this study: more than 16 and
  more than 64 observables, and the information-set search. A mixed-integer solver (HiGHS) run
  on the [[150,30,10]] problem for 50 minutes found a weight-9 solution in each basis and proved
  nothing beyond weight 3, so it confirms "below 10" but neither the value 8 nor its optimality.

## Second batch: four more papers (3 October 2026)

Sizes were chosen where the search can give exact or nearly exact answers: circuit distance up to
about 16 for bivariate-bicycle-type circuits and about 10 to 12 for circuits with weight-12 checks
and heavy hook faults. Larger members of each family are left out.

| paper | what is published | tested here |
|---|---|---|
| Cornucopia codes, 2608.02773 | check matrices (formulas and shift table), the full 12-layer schedule with X and Z checks measured in the same cycle, the fault model; circuit-distance upper bounds from BP-OSD, no lower bounds | circuit distance of the four smallest codes (the three larger ones, with bounds 14 to 18, are out of exact reach) |
| Self-dual bivariate bicycle codes, 2510.05211 | polynomials and twisted tori for 57 codes up to n = 200; code distances by integer programming; no circuit | code distance of all 57; circuit distance of schedules designed here |
| GALA codes, 2608.07431 | lifts for 39 codes; for [[132,30,12]] and [[672,336,12]] only the order of the 12 permutation layers; the simulated circuit is a different one and is not given | code distance of the 11 codes over abelian groups; circuit distance of schedules designed here for [[132,30,12]] |
| Ultra-high-rate codes, 2609.30069 | parameter tables; the non-CSS codes of the abstract have no printed construction, the linked repository is empty, and no schedule is given | code distance of 11 CSS instances of the same family from K. Kasai's data page; nothing for the non-CSS codes |

<!-- RESULTS2:BEGIN -->
**Cornucopia codes** (arXiv:2608.02773; the paper's 12-layer schedule and fault model, 6 rounds). Bold = exact; otherwise certified lower bound – verified upper bound.

| code | paper: code distance | paper: circuit distance | circuit distance, Z basis | circuit distance, X basis | seconds (Z, X) |
|---|---:|---:|---:|---:|---|
| [[252,130,6]] | 6 | ≤ 5 | **5** | **5** | 10, 9 |
| [[576,292,8]] | 8 | ≤ 8 | **8** | **8** | 66, 71 |
| [[900,454,10]] | 10 | ≤ 10 | **9** | **9** | 306, 306 |
| [[1044,526,12]] | 12 | ≤ 11 | **10** | **10** | 754, 796 |

**Self-dual bivariate bicycle codes** (arXiv:2510.05211, Tables 1 and 2; no circuit published): 57 of 57 codes rebuilt from the printed definitions have exactly the claimed [[n,k,d]] (n = 16 to 200, d = 4 to 16; exhaustive below d plus a weight-d logical operator; 17 s in total on one core).

**GALA codes over abelian groups** (arXiv:2608.07431, Tables S3 and S5; no usable circuit published): 11 of 11 codes rebuilt from the printed definitions have exactly the claimed [[n,k,d]] (n = 132 to 672, d = 8 to 12; exhaustive below d plus a weight-d logical operator; 14 s in total on one core).

Cross-check of the rebuilt Cornucopia circuits with the authors' repository (commit fc12c975a5): for 7 of 7 codes the check matrices are equal as sets of rows and every check meets its data qubits in the same order as in the authors' Stim circuit.

**Pair-partition CSS codes** (data page of K. Kasai, the family behind arXiv:2607.14091 and the CSS tables of 2609.30069): exact distances of the downloaded instances: [[232,62,12]], [[248,66,12]], [[264,70,12]], [[276,98,14]], [[280,74,12]], [[296,78,12]], [[372,130,16]], [[392,102,14]], [[444,154,18]], [[472,122,14]], [[472,122,16]], [[488,126,14]], [[492,170,20]]. 10 of 10 with a distance stated in the file or its name agree with it.

**Designed schedules for the self-dual bivariate bicycle codes** (no published circuit). Family: an X-check round followed by a Z-check round, every check using the same gate order; all 5040 inequivalent orders evaluated exactly, so the value is the optimum of the family. 57 codes done; loss against the code distance: 15 codes lose 0, 12 codes lose 1, 14 codes lose 2, 1 codes lose 3. Best order verified on a Stim circuit in both bases for 56 codes.

| code | best circuit distance | example gate order | all orders evaluated |
|---|---:|---|---|
| [[16,4,4]] | **2** | L0 L1 L2 L3 R2 R0 R1 R3 | yes |
| [[24,8,4]] | **2** | L0 L1 L2 L3 R0 R1 R2 R3 | yes |
| [[30,6,5]] | **4** | L0 L2 R0 L1 R2 R1 L3 R3 | yes |
| [[32,12,4]] | **2** | L0 L1 L2 L3 R0 R1 R2 R3 | yes |
| [[36,10,4]] | **4** | L0 L1 L2 R2 L3 R0 R1 R3 | yes |
| [[40,6,6]] | **5** | L0 R1 R3 R0 L2 R2 L1 L3 | yes |
| [[42,6,6]] | **5** | L0 L2 L1 R1 L3 R2 R0 R3 | yes |
| [[48,16,4]] | **2** | L0 L1 L2 L3 R0 R1 R2 R3 | yes |
| [[50,10,5]] | **5** | L0 L2 L3 R3 L1 R0 R1 R2 | yes |
| [[54,10,6]] | **5** | L0 L2 L1 L3 R1 R2 R0 R3 | yes |
| [[56,6,8]] | **6** | L0 L1 L2 L3 R0 R2 R1 R3 | yes |
| [[60,12,5]] | **5** | L0 L2 L3 R3 L1 R0 R1 R2 | yes |
| [[64,8,8]] | **6** | L1 L2 R0 R1 R2 L0 L3 R3 | yes |
| [[66,6,8]] | **7** | L0 R0 L1 L2 L3 R3 R1 R2 | yes |
| [[70,10,6]] | **6** | L0 L3 L1 R3 L2 R0 R1 R2 | yes |
| [[72,12,6]] | **6** | L0 L1 L2 L3 R0 R1 R2 R3 | yes |
| [[78,6,10]] | **8** | L0 L1 R0 L3 L2 R3 R1 R2 | yes |
| [[80,10,8]] | **6** | L0 L2 L1 R2 L3 R0 R1 R3 | yes |
| [[84,6,10]] | **8** | L0 L1 L2 R0 L3 R1 R2 R3 | yes |
| [[90,18,6]] | **6** | L0 L1 L2 L3 R0 R1 R2 R3 | yes |
| [[96,12,8]] | **7** | L0 L3 L1 R0 R1 L2 R2 R3 | yes |
| [[98,14,6]] | **6** | L0 L3 L1 R3 L2 R0 R1 R2 | yes |
| [[100,12,8]] | **7** | L0 R0 L2 L3 R2 R3 L1 R1 | yes |
| [[102,6,10]] | **9** | L0 L3 L2 R2 R0 R3 L1 R1 | yes |
| [[104,6,12]] | **9** | L0 L1 R1 L2 R2 R0 L3 R3 | yes |
| [[108,20,6]] | **5** | L0 L1 L2 L3 R1 R0 R2 R3 | yes |
| [[110,10,8]] | **8** | L0 L2 L1 R1 R0 R2 L3 R3 | yes |
| [[112,6,12]] | **10** | L0 L1 L2 L3 R1 R2 R0 R3 | yes |
| [[114,6,10]] | **10** | L0 R0 L3 L1 R3 R1 L2 R2 | yes |
| [[120,8,12]] | **10** | L1 L2 L0 L3 R0 R2 R1 R3 | yes |
| [[126,22,6]] | **6** | L0 L1 L2 L3 R0 R1 R2 R3 | yes |
| [[128,16,8]] | **8** | L0 R0 L1 L3 L2 R1 R2 R3 | yes |
| [[130,10,10]] | **9** | L0 R0 L3 L1 R3 R1 L2 R2 | yes |
| [[132,8,12]] | **10** | L0 L2 L1 L3 R0 R3 R1 R2 | yes |
| [[136,6,14]] | ≥ 10 | L0 L1 L2 L3 R0 R1 R2 R3 | 5040 of 5040 |
| [[138,6,12]] | ≥ 11 | L3 R3 L0 R2 L2 L1 R0 R1 | 5040 of 5040 |
| [[140,16,8]] | **7** | L0 L2 L3 R0 R2 R3 L1 R1 | yes |
| [[144,6,14]] | ≥ 11 | L0 L3 R1 L1 R0 R3 L2 R2 | 5040 of 5040 |
| [[150,6,14]] | ≥ 10 | L0 L1 L2 R0 R3 L3 R1 R2 | 899 of 5040 |
| [[152,6,16]] | ≥ 11 | L0 L2 R0 R3 L3 R1 L1 R2 | 976 of 5040 |
| [[154,14,8]] | **8** | L0 L2 L1 R1 R0 R2 L3 R3 | yes |
| [[156,12,10]] | **8** | L0 L1 R0 L3 L2 R3 R1 R2 | yes |
| [[160,8,16]] | ≥ 11 | L0 R0 R2 L3 L1 L2 R1 R3 | 981 of 5040 |
| [[162,6,14]] | ≥ 11 | L0 L2 L3 R2 R0 R3 L1 R1 | 2178 of 5040 |
| [[168,6,16]] | ≥ 10 | L0 L1 L2 L3 R0 R1 R2 R3 | 3019 of 5040 |
| [[170,10,10]] | **10** | L0 R0 L1 R1 L3 R3 L2 R2 | yes |
| [[174,6,14]] | ≥ 11 | L0 L1 R1 L2 R2 L3 R0 R3 | 1535 of 5040 |
| [[176,8,16]] | ≥ 10 | L0 L1 L2 L3 R2 R0 R1 R3 | 580 of 5040 |
| [[180,10,12]] | ≥ 10 | L0 L1 L2 L3 R0 R2 R1 R3 | 5040 of 5040 |
| [[182,14,10]] | **9** | L0 R0 L3 L2 R3 R2 L1 R1 | yes |
| [[184,6,16]] | ≥ 11 | L0 R1 R3 L3 R2 L1 L2 R0 | 437 of 5040 |
| [[186,6,14]] | ≥ 11 | L0 L1 L3 R2 L2 R0 R1 R3 | 1448 of 5040 |
| [[190,10,10]] | **10** | L0 R0 L1 R1 L2 L3 R2 R3 | yes |
| [[192,12,12]] | **10** | L0 L1 L2 L3 R0 R2 R1 R3 | yes |
| [[196,14,10]] | **10** | L2 R2 L0 R0 L1 R1 L3 R3 | yes |
| [[198,10,12]] | ≥ 11 | L0 L1 R0 R3 L2 L3 R1 R2 | 5040 of 5040 |
| [[200,12,12]] | ≥ 10 | L0 L1 L2 L3 R0 R2 R1 R3 | 5040 of 5040 |

**Parallel depth-8 circuits designed here for the self-dual bivariate bicycle codes** (X and Z checks in the same eight layers, one ancilla per check; the X order has a palindromic sublattice pattern and the Z order is its mirror image). Column 4: the gate order is chosen among the 3456 such orders by the time-collapsed bound and the circuit distance of the best few is determined exactly (6 cycles). Column 5, for the small codes: the exact circuit distance of all 3456 orders, i.e. the optimum of the family.

| code | best sequential circuit | parallel circuit: collapsed bound | circuit distance (Z, X) of the order chosen by the bound | optimum over all 3456 mirror orders (number of orders reaching it) | gate order of the X checks |
|---|---:|---:|---|---|---|
| [[16,4,4]] | 2 | 2 | **3**, **3** | **4** (448) | L0 R3 L1 R0 R2 L2 R1 L3 |
| [[24,8,4]] | 2 | 2 | **4**, **4** | – | R0 L0 L1 R1 R2 L2 L3 R3 |
| [[30,6,5]] | 4 | 4 | **5**, **5** | – | L0 R0 L1 R2 R3 L3 R1 L2 |
| [[32,12,4]] | 2 | 2 | **3**, **3** | **4** (576) | L0 R2 L1 R1 R3 L2 R0 L3 |
| [[36,10,4]] | 4 | 3 | **4**, **4** | – | R0 L2 L0 R1 R2 L1 L3 R3 |
| [[40,6,6]] | 5 | 5 | **6**, **6** | – | L0 R2 L2 R3 R0 L3 R1 L1 |
| [[42,6,6]] | 5 | 5 | **6**, **6** | – | R0 L2 L1 R1 R3 L3 L0 R2 |
| [[48,16,4]] | 2 | 2 | **4**, **4** | – | R2 L0 L1 R0 R1 L2 L3 R3 |
| [[50,10,5]] | 5 | 4 | **5**, **5** | – | L0 L2 R0 R1 R2 R3 L1 L3 |
| [[54,10,6]] | 5 | 5 | **6**, **6** | – | R0 L0 L1 R3 R1 L3 L2 R2 |
| [[56,6,8]] | 6 | 6 | **7**, **7** | **8** (20) | L2 R2 L1 R0 R1 L0 R3 L3 |
| [[60,12,5]] | 5 | 4 | **5**, **5** | – | L0 L2 R0 R1 R2 R3 L1 L3 |
| [[64,8,8]] | 6 | 6 | **6**, **6** | **8** (8) | L0 R3 R2 L2 L3 R1 R0 L1 |
| [[66,6,8]] | 7 | 7 | **8**, **8** | – | L1 R1 L0 R0 R3 L3 R2 L2 |
| [[70,10,6]] | 6 | 6 | **6**, **6** | – | L0 L3 R0 R1 R2 R3 L1 L2 |
| [[72,12,6]] | 6 | 6 | **6**, **6** | – | L0 R0 L1 R2 R1 L2 R3 L3 |
| [[78,6,10]] | 8 | 7 | **9**, **9** | **10** (72) | L0 R0 L2 R2 R1 L1 R3 L3 |
| [[80,10,8]] | 6 | 6 | **7**, **7** | **7** (1912) | L0 L2 R0 R1 R2 R3 L1 L3 |
| [[84,6,10]] | 8 | 8 | **9**, **9** | **10** (140) | L0 R0 L2 R3 R2 L3 R1 L1 |
| [[90,18,6]] | 6 | 6 | **6**, **6** | – | L0 R0 L1 R3 R1 L3 R2 L2 |
| [[96,12,8]] | 7 | 6 | **8**, **8** | – | R0 L0 L1 R2 R1 L2 L3 R3 |
| [[98,14,6]] | 6 | 6 | **6**, **6** | – | L0 L3 R0 R1 R2 R3 L1 L2 |
| [[100,12,8]] | 7 | 7 | **8**, **8** | – | R0 L0 L1 R2 R1 L2 L3 R3 |
| [[102,6,10]] | 9 | 8 | **10**, **10** | – | R0 L0 L2 R2 R3 L3 L1 R1 |
| [[104,6,12]] | 9 | 9 | **11**, **11** | – | L1 R1 L0 R3 R0 L3 R2 L2 |
| [[110,10,8]] | 8 | 8 | **8**, **8** | – | L0 R0 L2 R2 R1 L1 R3 L3 |
| [[112,6,12]] | 10 | 9 | **11**, **11** | – | L1 R1 R3 L3 L0 R0 R2 L2 |
| [[114,6,10]] | 10 | 9 | **10**, **10** | – | L0 R0 L2 R1 R2 L1 R3 L3 |
| [[120,8,12]] | 10 | 10 | **12**, **12** | – | R1 L1 L3 R0 R3 L0 L2 R2 |
| [[128,16,8]] | 8 | 8 | **8**, **8** | – | L0 R0 L1 R2 R1 L2 R3 L3 |
| [[130,10,10]] | 9 | 8 | **10**, **10** | – | R0 L0 L1 R1 R3 L3 L2 R2 |
| [[132,8,12]] | 10 | 10 | **11**, **11** | – | R0 L0 L1 R1 R3 L3 L2 R2 |
| [[152,6,16]] | 11 | 11 | 12 – 13, 12 – 13 | – | R0 R3 L3 L1 L0 L2 R1 R2 |
| [[160,8,16]] | 11 | 10 | **12**, **12** | – | L2 R1 R2 L3 L1 R3 R0 L0 |

Filtered search for a mirror order with the full distance (windows of one and two cycles, then exact evaluation of a few candidates; not exhaustive): [[104,6,12]], target 12: 3001 orders have a fault set of weight at most 10 within two consecutive cycles, 0 pass the filter, 455 are undecided within the time limit; 6 of the undecided evaluated exactly: 10. [[112,6,12]], target 12: 2034 orders have a fault set of weight at most 10 within two consecutive cycles, 0 pass the filter, 1422 are undecided within the time limit; 6 of the undecided evaluated exactly: 10, 11.

**Parallel 12-layer circuit designed here for GALA [[132,30,12]]** (palindromic label order for the X checks, reversed order for the Z checks). 600 random orders scored by the collapsed bound up to 8: {'5': 5, '6': 55, '7': 393, '8': 147}. Circuit distance (smaller of the two bases) of the 14 orders evaluated among those with bound 8: 5 × 10, 1 × 10 (one basis 10–11), 1 × 8, 7 × 9. An order with circuit distance exactly 10 in both bases: F0 F1 G5 G3 G1 F5 F3 G0 G4 G2 F2 F4.

Two gate orders on alternating checks (each class varied over all 5040 orders, starting from the best uniform order): [[40,6,6]]: 5 with one order, 5 with two; [[56,6,8]]: 6 with one order, 6 with two; [[64,8,8]]: 6 with one order, 6 with two.

**Designed schedules for GALA [[132,30,12]]** (same family, twelve gates per check). The paper's own layer order, run as an X round followed by a Z round, has circuit distance 8. Search over 2024 orders: best value 8 (exact), e.g. F0 F3 F4 F5 F2 F1 G1 G4 G2 G5 G3 G0. Histogram of evaluated orders: {'5': 12, '6': 151, '7': 1197, '8': 664}.

<!-- RESULTS2:END -->

**Cornucopia.** The circuits were rebuilt from the text of the paper (`papers/cornucopia.py`): all
seven codes come out with the stated n and k and two redundant checks per type, and the schedule of
Extended Data Tab. 3 reproduces the check matrices with deterministic detectors. The paper gives
upper bounds on the circuit distance from a BP-OSD search and no lower bounds. Exact values:

- [[252,130,6]]: 5. The paper's bound is tight; the circuit loses one unit against the code.
- [[576,292,8]]: 8. The schedule preserves the distance.
- [[900,454,10]]: 9, one below the paper's bound of 10. Weight 8 and below is excluded; weight-9
  fault sets are undetected and flip logical observables.
- [[1044,526,12]]: 10, one below the paper's bound of 11 and two below the code distance. The
  time-collapsed relaxation has distance 9 with a single translation orbit of minimum solutions;
  none of them is realised by nine faults in the circuit, and with one more fault a real fault
  set of weight 10 exists. This value is for the six-cycle memory experiment the paper simulates;
  the bound of 9 from the relaxation holds for any number of cycles, the step from 9 to 10 was
  checked on the six-cycle circuit.

Every upper bound is a fault set replayed in Stim. The paper's simulations include preparation,
reset and measurement flips, while the authors' repository says their distance search used faults
after CNOT gates only. For these circuits the two models have the same set of fault mechanisms
(checked for the two smallest codes: identical detector-error-model columns), because every such
flip is equivalent to a component of the depolarizing fault of a neighbouring CNOT. The values
above therefore hold for both.

**Self-dual bivariate bicycle codes.** Every one of the 57 table rows is reproduced: n, k and the
exact distance. The paper gives no syndrome-extraction circuit (X and Z checks act on the same
eight qubits, so the standard bivariate-bicycle schedule does not carry over), so there is no
circuit distance to test yet.

**GALA codes.** The eleven codes over abelian groups, including [[132,30,12]] and [[672,336,12]],
have exactly the claimed parameters; for [[132,30,12]] the rebuilt matrices also match the stated
rank, self-duality and number of 4-cycles. A circuit could not be rebuilt: the paper prints only the
order of the permutation layers. Read as its text suggests (X checks on one half of the data, Z
checks on the other half through the inverse permutation, in the same layer), the stabiliser
measurements are not deterministic (`papers/gala.py`), and that reading cannot be repaired by
reordering layers of the printed form. The condition the authors used is mentioned but not stated.

**Ultra-high-rate codes.** The non-CSS codes of the abstract ([[90,21,11]], [[140,31,15]],
[[200,43,20]]) cannot be rebuilt: neither their construction data nor a circuit is available. Eleven
CSS instances of the same pair-partition family, downloaded from K. Kasai's data page, have exactly
the distances stated there (up to [[472,122,16]] and [[372,130,16]]).

### Schedules designed here

For the codes without a published circuit the question changes from "does the paper's circuit keep
the distance" to "what can a simple circuit achieve". Two families were built, both with one
ancilla per check and no flags, and both with the same gate order for every check.

**Sequential circuits.** One cycle is an X-check round followed by a Z-check round. The circuit
distance is then a matrix problem (data errors plus the suffixes of each check's gate order),
exact for the multi-round circuit; this is re-checked on the Stim circuit of every reported design
(same columns as the one-round window and as the time-collapsed problem, witness replayed).

- *Self-dual bivariate bicycle codes.* All 5040 inequivalent gate orders of the weight-8 check are
  evaluated exactly for each code, so the tabulated value is the optimum of the family. About a
  third of the codes keep the full distance; most lose one or two units ([[64,8,8]] reaches 6,
  [[120,8,12]] reaches 10); the four codes [[16,4,4]], [[24,8,4]], [[32,12,4]], [[48,16,4]] fall to 2
  under every order. For the codes with distance 14 and 16 the exact evaluation of all orders does
  not fit a 30-minute budget per code, so the tabulated value is the best found ("≥"): 10 or 11
  for all of them, three to five units below the code distance. Using two different orders on alternating checks does not help for
  [[40,6,6]], [[56,6,8]] and [[64,8,8]] (each class varied over all 5040 orders, three colourings).
- *GALA [[132,30,12]].* The layer order printed in the paper, which does not give a valid circuit
  when X and Z checks share the layers, is valid as an X round followed by a Z round; its circuit
  distance is then 8. Among 2024 other orders (random sample and hill climbing) none exceeds 8.
  The search over the 12!/8 orders is not exhaustive, so 8 is the best found, not a proven optimum.

**Parallel circuits.** X and Z checks share the layers (depth 8 for the weight-8 codes, 12 for
GALA), as in the Cornucopia schedule. Such a circuit is valid if no qubit is used twice in a layer
and every pair of an X and a Z check is crossed consistently. Both hold when the X checks use an
order whose pattern of sublattices (halves) is a palindrome and the Z checks use the mirror image:
the reversed order, with the two sublattices exchanged for the self-dual bivariate bicycle codes
(`papers/sdbb_parallel.py`, `papers/gala_parallel.py`; Stim confirms deterministic detectors). The
time-collapsed problem of such a circuit is the matrix problem of the sequential circuit with the
same order, so its circuit distance is at least that value, and it can be larger when the
collapsed solutions cannot be realised in the interleaved circuit. The exact value is determined
as for the Cornucopia circuits.

- *Self-dual bivariate bicycle codes.* The parallel circuit is never worse than the best
  sequential one in the cases run, and usually better. Of the 34 codes done (n up to 132, plus
  [[152,6,16]] and [[160,8,16]]), 28 reach the full code distance in both bases, where the
  sequential family reaches it for 9 of the same codes. Examples: [[40,6,6]] 6 (sequential 5),
  [[48,16,4]] 4 (sequential 2), [[64,8,8]] 8 (sequential 6), [[78,6,10]] 10 (sequential 8),
  [[120,8,12]] 12 (sequential 10).
  Choosing the order by the collapsed bound is not enough: the circuit distance exceeds that bound
  by up to five, and the orders with the best bound are often not the best circuits. For the
  seven smallest codes that fell short with the bound-selected orders, the exact circuit distance
  of all 3456 mirror orders was computed (4 October). Six of them reach the full distance:
  [[16,4,4]] (448 orders), [[32,12,4]] (576), [[56,6,8]] (20), [[64,8,8]] (8), [[78,6,10]] (72) and
  [[84,6,10]] (140); the first report of this section had 3, 3, 7, 6, 9 and 9 for them. For
  [[80,10,8]] the optimum of the family is 7. The best circuits of [[16,4,4]], [[32,12,4]],
  [[56,6,8]], [[64,8,8]] and [[78,6,10]] were re-run with twelve cycles and with the original
  pipeline of this project (no symmetry): same values.
  Still below full distance with the orders tried: [[104,6,12]], [[112,6,12]], [[132,8,12]] (11),
  [[160,8,16]] (12), [[152,6,16]] (12 to 13). A full sweep is too expensive there. A filter
  (reject an order as soon as a fault set lighter than the code distance exists within one or two
  consecutive cycles) removes most orders cheaply but leaves several hundred undecided per code;
  a sample of those gave nothing above the values already found (line "Filtered search" with the
  tables). Whether these codes have a mirror circuit with the full distance is open.
- *GALA [[132,30,12]].* Of 600 random orders of the required form, 147 have collapsed bound 8.
  Of the 14 parallel circuits evaluated, six have circuit distance 10 (five of them exactly 10 in
  both bases), seven have 9 and one has 8, against 8 for every sequential order found. None
  exceeds 10. For comparison, the
  paper fits an exponent of about 9.5 to simulations of its own circuit, which it does not
  specify.

The circuit distance can exceed the collapsed bound by several units (for example [[24,8,4]]:
bound 2, distance 4; in the full sweeps the gap goes up to five): the collapsed solutions, and
those with a few extra faults, cannot be arranged in time in the interleaved circuit, which is
decided by an exhaustive search of the real circuit problem.
These steps were established on six-cycle circuits, as for [[1044,526,12]] above; for
[[24,8,4]], [[40,6,6]] and [[48,16,4]] the same value was obtained again with ten cycles, and for
[[24,8,4]] and [[40,6,6]] also with the original pipeline of this project (`run_bb.py`, labelled
search without symmetry).

Method for the Cornucopia circuits (`papers/run_parallel.py`): undecomposed DEM, CSS sector
(checked exact), time-collapsed relaxation searched exhaustively for the lower bound, then a real
fault set of the same weight from lifting or from a one-round window, checked in the full DEM and
replayed in Stim. When the minimum solutions of the relaxation do not lift, all of them are
enumerated and each translation orbit is tested, which raises the lower bound by one (the circuit
problem is checked to have the same translations). All observables are handled in one pass
(`labelfree` mode of the search; tested against brute force in `tests/test_multi.py`); for
[[252,130,6]] and [[576,292,8]] the older grouped search gives the same lower bounds.

## Third batch: circuits from the 2026 code-instance catalog (3 and 4 October 2026)

The catalog in `../code_instances` (296 papers of 2026, 369 code instances, collected by Codex)
was screened for papers that publish a syndrome-extraction circuit together with a number for its
circuit distance, at sizes within exact reach. Eleven papers have such numbers:

| catalog paper | its circuit-distance statement | here |
|---|---|---|
| left-right circuits, 2603.05481 | gross code: 11, conjectured | exact |
| routing codes, 2606.25330 | BP-OSD upper bounds for ten codes | exact for nine, interval for one |
| STAR architecture, 2606.25011 | 5 for 20 schedules of [[42,6,6]], 4 for 192 | exact for all 212, under every index convention |
| Walking Cat, 2604.19481 | 9 for three codes | exact, for every numbering of the terms |
| shift circuits, 2601.09911 | BP-OSD estimates for four codes | exact, static and dynamic, for every numbering of the terms |
| Cornucopia, 2608.02773 | upper bounds | second batch above |
| amplified codes, 2609.37231 | certified lower bounds | first batch above |
| coset codes, 2606.17268 | BP-OSD upper bounds for seven codes | blocked: needs GAP or the authors' repository |
| Stairway codes, 2603.00228 | exact for two Floquet circuits, upper bounds for four | blocked: needs the Zenodo supplement |
| vine codes, 2606.20263 | exact values for four codes | not attempted (Stim files on Zenodo) |
| bunny codes, 2606.22853 | 3 or 5 for [[30,2,5]] | not attempted |

The code and circuit of each paper were rebuilt from the paper's text by Codex (one module per
paper in `papers/`, extraction notes with the paper locators in `papers/new/`, tests in `tests/`);
author repositories were not used. Every number below comes from runs I made on the server with
those modules, every upper bound is a fault set replayed in Stim, and where a result contradicts a
paper the reading of the paper that it depends on is stated.

<!-- RESULTS3:BEGIN -->
**Circuits with a stated circuit distance.** Six-cycle memory experiments, both bases; bold = exact (certified lower bound = replayed fault set); otherwise lower bound – upper bound.

| paper | circuit | paper's number | circuit distance (Z, X) | seconds (Z, X) |
|---|---|---|---|---|
| left-right circuits, 2603.05481 | gross code [[144,12,12]], explicit schedule | 11 (conjecture) | **11**, **11** | 3, 3 |
| routing codes, 2606.25330 | [[54,8,6]] | ≤ 6 | **6**, **6** | 2, 2 |
| routing codes, 2606.25330 | [[70,8,7]] | ≤ 7 | **7**, **7** | 3, 2 |
| routing codes, 2606.25330 | [[80,8,8]] | ≤ 8 | **8**, **8** | 3, 3 |
| routing codes, 2606.25330 | [[90,8,9]] | ≤ 9 | **9**, **9** | 4, 4 |
| routing codes, 2606.25330 | [[100,8,10]] | ≤ 9 | **9**, **9** | 6, 8 |
| routing codes, 2606.25330 | [[110,8,11]] | ≤ 10 | **10**, **10** | 8, 9 |
| routing codes, 2606.25330 | [[140,8,12]] | ≤ 11 | **11**, **11** | 25, 28 |
| routing codes, 2606.25330 | [[140,8,13]] | ≤ 12 | **12**, **12** | 193, 245 |
| routing codes, 2606.25330 | [[200,24,14]], weight 11 | ≤ 14 | **10**, **10** | 224, 278 |
| routing codes, 2606.25330 | [[200,16,17]], weight 11 | ≤ 17 | 11 – 14, 11 – 14 | –, – |
| STAR architecture, 2606.25011 | [[42,6,6]], schedule of Table 2, index convention that reproduces the paper's histogram | 5 | **5**, **5** | – |
| STAR architecture, 2606.25011 | [[42,6,6]], same table read with B_i = A_i^T | none | **6**, **6** | – |
| STAR architecture, 2606.25011 | [[66,6,8]], schedule of Table 2, index convention that reproduces the paper's histogram | none | **8**, **8** | – |
| STAR architecture, 2606.25011 | [[66,6,8]], same table read with B_i = A_i^T | none | **8**, **8** | – |
| STAR architecture, 2606.25011 | [[78,6,10]], schedule of Table 2, index convention that reproduces the paper's histogram | none | **8**, **8** | – |
| STAR architecture, 2606.25011 | [[78,6,10]], same table read with B_i = A_i^T | none | **10**, **9** | – |
| Walking Cat, 2604.19481 | [[102,22,9]], terms numbered as printed | 9 | **8**, **8** | 9, 12 |
| Walking Cat, 2604.19481 | [[70,6,9]], terms numbered as printed | 9 | **8**, **8** | 2, 3 |
| Walking Cat, 2604.19481 | [[54,2,10]], terms numbered as printed | 9 | **8**, **8** | 2, 3 |

**Time-dynamic shift circuits** (2601.09911; paper's estimate for every code: the bound in the second column). Circuit distance (Z, X), six cycles.

| code | paper | static (Table II) | dynamic pair repeated (Table III) | one dynamic pair among static cycles | static, gate order of Table III |
|---|---|---|---|---|---|
| [[72,12,6]] | ≤ 6 | **6**, **6** | **6**, **6** | **6**, **6** | **6**, **6** |
| [[120,8,12]] | ≤ 10 | **10**, **10** | **8**, **10** | **8**, **10** | **8**, **10** |
| [[144,12,12]] | ≤ 10 | **10**, **10** | **8**, **8** | **8**, **8** | **8**, **8** |
| [[170,16,10]] | ≤ 10 | **10**, **10** | **10**, **10** | **10**, **10** | **10**, **10** |

**Shift circuits, every numbering of the monomials** (36 ways to call the printed monomials A_1..A_3, B_1..B_3). Valid numberings and their circuit distance (smaller of the two bases):

| code | static table: valid numberings, distances | dynamic table: valid numberings, distances |
|---|---|---|
| [[72,12,6]] | 36: 36 × 6 | 12: 12 × 6 |
| [[120,8,12]] | 36: 27 × 10, 4 × 8, 5 × 9 | 12: 7 × 10, 2 × 8, 3 × 9 |
| [[144,12,12]] | 36: 18 × 10, 3 × 11, 12 × 8, 3 × 9 | 12: 12 × 8 |
| [[170,16,10]] | 36: 32 × 10, 4 × 9 | 12: 12 × 10 |

**STAR, every valid depth-8 schedule of the [[42,6,6]] code** (212 schedules; paper: 192 with fault distance 4 and 20 with 5, the schedule of Table 2 among the 20). The paper does not print which monomial each B_i is, so all 24 conventions B_i = A_σ(i)^T were run; each keeps all 212 schedules valid. Exact circuit distance, smaller of the two bases: 2 conventions (σ = 1243 and 2134) give exactly the paper's histogram, 192 at 4, 20 at 5, with the Table 2 schedule at 5; the convention B_i = A_i^T gives 192 at 4, 12 at 5, 8 at 6, with the Table 2 schedule at 6. Schedules of distance 6 exist under 5 of the 24 conventions.

Independent check of the distance-6 circuit (Table 2 read with B_i = A_i^T) without the sector and collapse reductions: Z: no fault set of weight ≤ 5 in the full detector error model (13902 mechanisms, 252 detectors, 801 s); Stim's own heuristic search finds 6; X: no fault set of weight ≤ 5 in the full detector error model (13944 mechanisms, 252 detectors, 911 s); Stim's own heuristic search finds 6.

**Walking Cat, every numbering of the terms** (the paper's Table 10 refers to terms A_i, B_i without printing which monomial is which): [[102,22,9]]: 576 numberings, Z-basis circuit distance 24 × 6, 132 × 7, 412 × 8, 8 × 9; of the 8 numberings at 9, 8 also have 9 in the X basis. [[70,6,9]]: 144 numberings, Z-basis circuit distance 26 × 7, 114 × 8, 4 × 9; of the 4 numberings at 9, 0 also have 9 in the X basis (the others: X 8). [[54,2,10]]: 576 numberings, Z-basis circuit distance 4 × 4, 82 × 6, 224 × 7, 264 × 8, 2 × 9; of the 2 numberings at 9, 2 also have 9 in the X basis.

Code distances of the rebuilt weight-11 routing codes (exact search): [[200,24,14]]: rebuilt [[200,24]], code distance Z **14**, X **14**; [[200,16,17]]: rebuilt [[200,16]], code distance Z **17**, X **17**.

**Code distances that the papers give as estimates or bounds** (`papers/estimated_codes.py`: 250 codes rebuilt from the papers' tables; exact search = all smaller weights exhausted and a logical operator of that weight found, for both error types).

| paper | codes rebuilt | exact here | equal to the paper's value | different | open |
|---|---:|---:|---:|---:|---:|
| multivariate multicycle codes, 2601.18879 | 215 | 214 | 201 | 13 | 1 |
| weight-8 bivariate bicycle codes, 2609.06572 | 5 | 5 | 4 | 1 | 0 |
| clustered lifted-product codes (QGPU), 2603.05398 | 10 | 10 | 10 | 0 | 0 |
| balanced-product codes, design rate 1/5, 2607.27644 | 7 | 7 | 7 | 0 | 0 |
| LLM-guided bivariate bicycle search, 2606.02418 | 13 | 13 | 13 | 0 | 0 |

| code | paper's statement | this work | seconds |
|---|---|---|---:|
| multivariate multicycle codes [[216,12]] | 14 (estimate) | **14** | 1 |
| multivariate multicycle codes [[288,12]] | 16 (estimate) | the printed definition gives [[288,0]], not [[288,12]] | 0 |
| multivariate multicycle codes [[324,12]] | 20 (estimate) | **18** | 1 |
| multivariate multicycle codes [[630,70]] | 9 (estimate) | **9** | 0 |
| weight-8 bivariate bicycle codes [[144,6]] | ≥ 15 (lower bound) | **15** | 0 |
| weight-8 bivariate bicycle codes [[144,10]] | ≥ 11 (lower bound) | **14** | 0 |
| clustered lifted-product codes [[136,8]] | 14 (estimate) | **14** | 0 |
| clustered lifted-product codes [[198,18]] | 10 (estimate) | **10** | 0 |
| balanced-product codes [[390,78]] | ≤ 16 (upper bound) | **16** | 5 |
| balanced-product codes [[525,105]] | ≤ 18 (upper bound) | **18** | 19 |
| balanced-product codes [[550,110]] | ≤ 18 (upper bound) | **18** | 31 |
| balanced-product codes [[625,125]] | ≤ 20 (upper bound) | **20** | 137 |
| LLM-guided bivariate bicycle search [[360,12]] | ≤ 24 (upper bound) | **24** | 145 |

Other rows where the exact value differs from the printed one (code, printed → exact): [[156,6]] 10 → 6, [[336,6]] 14 → 6, [[370,10]] 9 → 8, [[400,20]] 11 → 12, [[400,20]] 12 → 11, [[450,10]] 10 → 9, [[516,6]] 20 → 18, [[530,10]] 12 → 7, [[576,6]] 16 → 6, [[610,10]] 12 → 11, [[624,12]] 14 → 10, [[640,10]] 13 → 8. See the caution in the text.

**Mirror depth-8 circuits designed here for the weight-8 bivariate bicycle codes of 2609.06572** (`papers/bb8_parallel.py`; the paper gives no circuit). For the first two codes the exact circuit distance of all 3456 mirror orders was computed; for the larger ones a few orders with the best collapsed bound were evaluated exactly (`papers/design_parallel_pick.py`), which gives a circuit and its distance but not the optimum of the family.

| code | orders | result | example order of the X checks (L_a = A_a on the left block, R_a = B_a on the right block) |
|---|---|---|---|
| [[72,14,8]] | all 3456, exact: 8 at 2, 192 at 4, 260 at 5, 2452 at 6, 532 at 7, 12 at 8 | best **8** in both bases (12 orders) | L0 R2 L1 R3 R1 L2 R0 L3 |
| [[144,16,10]] | all 3456, exact: 48 at 3, 8 at 4, 900 at 6, 192 at 7, 1066 at 8, 760 at 9, 482 at 10 | best **10** in both bases (482 orders) | L0 R0 L1 R1 R2 L3 R3 L2 |
| [[144,10,14]] | 2 orders with the best collapsed bound (10) evaluated exactly | best found **12** in both bases (not the optimum of the family) | L0 R2 L3 R1 R0 L1 R3 L2 |

**Every valid depth-7 schedule of the weight-6 bivariate bicycle codes** (`papers/bb6_depth7.py`, `papers/design_bb6_depth7.py`; designed here). One ancilla per check, seven CNOT layers; a schedule is valid iff X and Z checks never act on the same block in a layer and every overlapping pair of checks is crossed consistently. There are 8496 valid schedules, 936 of them in the standard family (X checks idle in the first layer, Z checks idle in the last). Exact circuit distance of every schedule, both bases, six cycles; the number is the smaller of the two bases. In the Z rows of a schedule, A_i and B_j stand for the transposed terms.

| code | family | standard schedule (2308.07915) | schedules by exact circuit distance | best | a best schedule |
|---|---|---:|---|---:|---|
| [[72,12,6]] | standard, 936 | 6 | 24 at 3, 12 at 4, 108 at 5, 792 at 6 | **6** | X: – A1 B1 B2 B3 A2 A3; Z: A3 A2 B3 B2 B1 A1 – |
| [[72,12,6]] | all, 8496 | 6 | 48 at 3, 24 at 4, 1008 at 5, 7416 at 6 | **6** | X: – A1 B1 B2 B3 A2 A3; Z: A3 A2 B3 B2 B1 A1 – |
| [[90,8,10]] | standard, 936 | 8 | 16 at 6, 64 at 7, 856 at 8 | **8** | X: – A1 B1 B2 B3 A2 A3; Z: A2 A3 B3 B2 B1 A1 – |
| [[90,8,10]] | all, 8496 | 8 | 32 at 6, 416 at 7, 7888 at 8, 160 at 9 | **9** | X: B2 A1 A2 B3 A3 – B1; Z: B1 A3 – B3 A1 A2 B2 |
| [[108,8,10]] | standard, 936 | 8 | 10 at 7, 630 at 8, 166 at 9, 130 at 10 | **10** | X: – B1 A1 A2 A3 B2 B3; Z: B2 B3 A2 A1 A3 B1 – |
| [[108,8,10]] | all, 8496 | 8 | 68 at 7, 4932 at 8, 2072 at 9, 1424 at 10 | **10** | X: – B1 A1 A2 A3 B2 B3; Z: B2 B3 A2 A1 A3 B1 – |
| [[144,12,12]] | standard, 936 | 10 | 24 at 6, 2 at 7, 310 at 8, 114 at 9, 436 at 10, 50 at 11 | **11** | X: – B3 A2 A1 A3 B1 B2; Z: B1 B2 A1 A2 A3 B3 – |
| [[144,12,12]] | all, 8496 | 10 | 48 at 6, 4 at 7, 2364 at 8, 1420 at 9, 4232 at 10, 428 at 11 | **11** | X: – B3 A2 A1 A3 B1 B2; Z: B1 B2 A1 A2 A3 B3 – |

Cross-checks of a best schedule (six and twelve cycles in both bases; the original pipeline `run_bb.py` without symmetry in both bases): [[108,8,10]]: all 6 re-runs give 10; [[144,12,12]]: all 6 re-runs give 11.

<!-- RESULTS3:END -->

**Left-right circuits for the gross code (2603.05481).** The paper proves that uniformly tiled
non-interleaved circuits for [[144,12,12]] cannot exceed circuit distance 10 and gives an explicit
three-colour schedule (its Figures 10 and 12) whose distance it conjectures to be 11. Rebuilt from
the figure labels (`papers/lrgross.py`), that circuit has circuit distance exactly 11 in both bases:
every fault set of weight 10 or less is excluded and a weight-11 fault set is replayed. The
conjecture holds. Two routes agree: the pipeline on the Stim circuit, and the paper's own reduction
to a matrix problem (data errors plus residual hook errors, the same statement as the "effective
problem" used for the sequential designs above).

**Routing codes (2606.25330).** The codes are defined by a sequence of routing vectors, and the
circuit by CNOT-plus-SWAP layers along them, so data and ancilla roles move from cycle to cycle;
the paper gives BP-OSD upper bounds only. For all eight weight-7 codes the bounds are exactly
tight: 6, 7, 8, 9, 9, 10, 11, 12. (The [[80,8,·]] code has distance 8, as in the paper's Tables 2
and 3; its Table 1 says 7.) For the two weight-11 codes the paper's bounds equal the code distances
(14 and 17), and they are far from tight: the circuit distance of [[200,24,14]] is exactly 10, and
that of [[200,16,17]] lies between 11 and 14 (weight 10 and below excluded in both bases). The rebuilt codes have the stated distances 14 and 17
(exact search), so the difference is in the circuit, not in the code: an eleven-gate check has
hook faults that the sampling search of the paper does not find at this weight.

**STAR architecture (2606.25011).** The paper reports that 212 depth-8 schedules are valid for its
[[42,6,6]] code, of which 192 have fault distance 4 and 20 have 5, the chosen one (its Table 2)
among the 20. The schedules are written in terms of indexed monomials A_i and B_i, and the paper
does not print which monomial each B_i is. All 24 possibilities B_i = A_σ(i)^T were run (each keeps
the 212 schedules valid). Two of them reproduce the paper exactly: 192 schedules at 4, 20 at 5,
and the Table 2 schedule at 5 in both bases. So the paper's numbers are confirmed, and its
convention is identified up to that pair. With the natural reading B_i = A_i^T the same tables
describe different circuits, and those are better: 192 at 4, 12 at 5 and 8 at 6, the full code
distance, the Table 2 schedule among the 8 (lower bound re-checked by an exhaustive search of the
full detector error model with no reduction). For the larger codes the Table 2 schedule gives
8 for [[66,6,8]] under either reading, and for [[78,6,10]] 8 under the paper's reading against 9
(X basis 9, Z basis 10) under B_i = A_i^T; the paper states no number for these two.
[[66,6,8]] and [[78,6,10]] are the self-dual bivariate bicycle codes of the second batch, for
which the mirror circuits designed here, also of depth 8, reach the full distances 8 and 10; the
paper's [[42,6,6]] is a different code from the [[42,6,6]] of that table.

**Walking Cat (2604.19481).** The paper gives the order in which each check meets its terms
(Table 10) in terms of indexed monomials A_i, B_i, and states circuit distance 9 for [[102,22,9]],
[[70,6,9]] and [[54,2,10]]. With the monomials numbered in the order they are printed, all three
circuits have circuit distance exactly 8. Since the numbering is not printed, every numbering was
run: 9 is the maximum for all three codes in the Z basis, reached by 8 of 576, 4 of 144 and 2 of
576 numberings. For [[102,22,9]] and [[54,2,10]] those numberings also give 9 in the X basis, so
the paper's value is reproduced if its numbering is one of them. For [[70,6,9]] the four numberings
with 9 in the Z basis have 8 in the X basis, so no numbering gives 9 in both bases; the paper's 9
for this code is reproduced only as a Z-basis value.

**Time-dynamic shift circuits (2601.09911).** The paper replaces SWAP-based shift automorphisms by
syndrome circuits in which some CNOTs are reversed, so that data and ancillas exchange roles, and
states that the fault structure of the memory circuit is kept; its distance estimates are ≤ 6 and
≤ 10. Readings that had to be fixed: the twisted lattices of [[120,8,12]] and [[170,16,10]] are
taken from the cited base paper (the lattices as printed give k = 0), and the fault set is the
uniform circuit-level one, which has the same single-fault effects as the paper's CZ-compiled
SI1000 model. With the monomials numbered in the order printed, the static example circuit
(Table II) has circuit distance exactly 6, 10, 10, 10 and the dynamic circuit (Table III) has
6, 8, 8, 10 (for [[120,8,12]]: 8 in the Z basis, 10 in the X basis). The dynamics are not the
cause of the loss: the static circuit with the CNOT order that Table III is derived from has the
same values, and the same weight-8 fault set is undetected in both, so the paper's statement about
the dynamics holds. As the numbering of the monomials is not printed, all 36 numberings were run.
The static table is a valid circuit for all of them, the dynamic table for 12. For [[72,12,6]] and
[[170,16,10]] every valid numbering gives 6 and 10. For [[120,8,12]] seven of the twelve give 10
in both bases, so the paper's estimate is reproduced and the printed order is simply not the
paper's numbering. For the gross code the dynamic circuit has circuit distance 8 under all twelve
numberings: whichever way the terms are numbered, the CNOT order of Table III costs the gross code
two units against the static circuit and against the paper's estimate of 10.

**Code distances given as estimates.** Several papers quote distances from randomized searches or
as one-sided bounds. The registry `papers/estimated_codes.py` rebuilds 250 codes from the tables of
five papers; the exact search settles 249 of them (minutes on 32 threads; the remaining row cannot
be rebuilt). Among the
cases asked for: the multivariate multicycle code [[324,12]] (estimate 20) has distance 18;
[[216,12,14]] and [[630,70,9]] are confirmed; the weight-8 bivariate bicycle codes published with
lower bounds, [[144,6]] (d ≥ 15) and [[144,10]] (d ≥ 11), have distances exactly 15 and 14; the
clustered lifted-product codes [[136,8,14]] and [[198,18,10]] are confirmed; and the four
balanced-product codes published with upper bounds only, [[390,78]], [[525,105]], [[550,110]] and
[[625,125]], have distances exactly 16, 18, 18 and 20, so those bounds are tight, as is the bound
24 for the [[360,12]] code of 2606.02418. One table row of the multicycle paper, [[288,12,16]],
encodes no qubits as printed.
Over the whole registry 235 exact values equal the printed ones and 14 differ. The differences
inside the multicycle tables are not claimed as corrections of the codes the authors had: several
of these rows carry visible misprints (a polynomial printed twice in the [[156,6]] and [[576,6]]
rows, exponents larger than the period in the [[450,10]] and [[640,10]] rows), and two neighbouring
[[400,20]] rows printed with 11 and 12 come out as 12 and 11. What is established is the distance
of the code as printed.

**All depth-7 schedules of the standard bivariate bicycle codes (designed here).** The numbering
sweep of the shift circuits turned up static schedules for the gross code with circuit distance
11, one more than the standard schedule of 2308.07915. To see how far that goes, every valid
depth-7 schedule with one ancilla per check was enumerated (`papers/bb6_depth7.py`): 8496 in total,
of which 936 have the standard form (X checks idle in the first layer, Z checks idle in the last),
the number quoted in the literature for the gross code. The exact circuit distance of all 936 was
computed in both bases for four codes (`papers/design_bb6_depth7.py`, 14 minutes on 40 cores for
the gross code):

- [[144,12,12]]: 50 schedules have circuit distance 11 in both bases and none has 12; the standard
  schedule has 10 (436 schedules do), and 336 schedules are at 8 or below.
- [[108,8,10]]: 130 schedules reach the full code distance 10; the standard schedule has 8.
- [[90,8,10]]: no schedule of the family exceeds 8.
- [[72,12,6]]: 792 schedules reach 6; the worst have 3.

So within the standard family the optimum is 11 for the gross code and 10 for [[108,8,10]], and
which schedule is best depends on the code: the standard schedule is not among the best for
either. The distance-11 result for the gross code was obtained twice independently (the builder
Codex wrote for the shift paper and the one written here); for both codes a best schedule gives
the same value with six and twelve cycles in both bases and in the original pipeline of this
project without symmetry, and the standard schedule gives 10 and 8 through the same six runs.

The other 7560 valid schedules place the idle layers elsewhere; all 8496 were evaluated exactly
for the four codes. For [[72,12,6]] and [[108,8,10]] the maximum does not change (6, and 10 for
1424 schedules). For [[90,8,10]] the extra freedom helps: 160 schedules have circuit distance 9,
none has 10, where the standard family stops at 8. For the gross code 428 schedules have circuit
distance 11 and none has 12. So 11 is the optimum for the gross code over every depth-7 circuit
with one ancilla per check and one gate order per check type; reaching 12 needs something else
(different orders on different checks, more layers, or flags).

**Circuits designed here for the weight-8 bivariate bicycle codes (2609.06572).** That paper gives
codes with weight-8 checks that beat the standard bivariate bicycle codes in distance at equal
length, and no circuit. The mirror construction of the second batch carries over unchanged
(`papers/bb8_parallel.py`): the X check meets A_a on the left block and B_a on the right block in
an order with a palindromic block pattern, the Z check meets B_a^T and A_a^T in the mirrored order,
eight CNOT layers, one ancilla per check. For [[72,14,8]] all 3456 orders were evaluated exactly:
12 of them have circuit distance 8, the full code distance, in both bases (also with twelve cycles
and with the original pipeline). For [[144,16,10]] the same sweep gives 482 orders with the full
distance 10. For comparison, the standard codes [[72,12,6]] and [[144,12,12]] have circuit distance
6 and at most 11 with depth-7 circuits. For the higher-distance codes a full sweep is too
expensive; the table gives the best of a few orders picked by the collapsed bound, for example a
circuit with circuit distance exactly 12 for the code [[144,10,14]].

**Not testable from the papers alone.**

- *Coset codes, 2606.17268* (circuit-distance bounds 5 to 14 for seven codes): the codes are
  defined by indices into GAP's SmallGroups library and GAP's coset enumeration. Without GAP or the
  authors' repository the matrices cannot be rebuilt. The builder is written (`papers/coset.py`)
  and waits for either.
- *Stairway codes, 2603.00228* (Floquet circuits, bounds 7 to 14 for four instances): three of the
  six instance definitions and the memory-experiment boundaries are only in the Zenodo supplement.

Not attempted in this round, although the catalog lists a circuit-distance statement: vine codes
(2606.20263, exact values 6, 7, 6, 7 reported; Stim circuits on Zenodo), bunny codes (2606.22853,
[[30,2,5]] with 3 or 5 depending on the circuit), morphing circuits (2604.09797), the greedy
schedules of the rate-1/5 codes (2607.27644; only their code distances are in the registry above)
and the non-CSS mirror codes (2603.05496).

## Fourth batch: modular hyperbolic codes of arXiv:2610.03682 (6 October 2026)

Higgott et al. (Google Quantum AI), "Low-Overhead Quantum Error Correction with Boundary-Connected
Planar Modules", build color codes on closed hyperbolic tilings that are fine-grained with side
length L (n = L²·N for a tiling with N triangles). The paper certifies a distance only when two
graph bounds coincide: d_res (median systole of the three restricted lattices, a lower bound) and
d_string (shortest string-like logical operator, an upper bound). Otherwise it prints a range; its
only exact tool is a connected-cluster search, limited to n ≤ 2000 and 300 s. No code, data or
circuit files are published.

**Result.** Every range we could reach closes, and always at the upper bound: the shortest logical
operator of these codes is string-like in all cases tried.

<!-- RESULTS4:BEGIN -->
| tiling in the paper | L | n | k | paper | bounds recomputed | exact distance | search time |
|---|---:|---:|---:|---:|---:|---:|---:|
| (4,4,4) 32 | 1 | 16 | 8 | 2 | 2–4 | 2 | < 1 s |
| (4,4,4) 32 | 2 | 64 | 8 | 6 | 6 | 6 | < 1 s |
| (4,4,4) 32 | 3 | 144 | 8 | 8 | 8 | 8 | < 1 s |
| (4,4,4) 32 | 4 | 256 | 8 | 12 | 10–12 | 12 | < 1 s |
| (4,4,4) 40 | 1 | 32 | 12 | 4 | 4 | 4 | < 1 s |
| (4,4,4) 40 | 2 | 128 | 12 | 8 | 8 | 8 | < 1 s |
| (4,4,4) 40 | 3 | 288 | 12 | 12 | 12 | 12 | < 1 s |
| (4,4,4) 58 | 1 | 128 | 36 | 8 | 4–8 | 8 | < 1 s |
| (4,4,4) 58 | 2 | 512 | 36 | 12 | 12 | 12 | 2 s |
| (4,4,4) 58 | 3 | 1152 | 36 | 16 | 16 | 16 | 20 s |
| (4,4,4) 58 | 4 | 2048 | 36 | 20–24 | 20–24 | **24** | 91 s |
| (4,4,4) 96 | 2 | 1344 | 88 | 14 | 14 | 14 | 13 s |
| (4,4,4) 96 | 3 | 3024 | 88 | 20 | 20 | 20 | 2 s |
| (4,4,4) 96 | 4 | 5376 | 88 | 26–28 | 26–28 | **28** | 6815 s |
| (4,4,4) 109 | 2 | 1600 | 104 | 14–16 | 14–16 | **16** | 28 s |
| (4,4,4) 109 | 3 | 3600 | 104 | 22 | 22 | 22 | 15 s |
| (4,4,4) 109 | 4 | 6400 | 104 | 30 | 30 | ≥ 25 | 249 s |
| (4,4,4) 120 | 2 | 2048 | 132 | 16 | 16 | 16 | 60 s |
| (4,4,4) 120 | 3 | 4608 | 132 | 24 | 24 | 24 | 125 s |
| (4,4,4) 271 | 1 | 1344 | 340 | 10–12 | 8–12 | **12** | 17 s |
| (4,4,4) 271 | 2 | 5376 | 340 | 18–20 | 18–20 | **20** | 3 s |
| (4,4,4) onto PSL(2,25) | 2 | 31200 | 1954 | 22–24 | 22–24 | **24** | 389 s |
| (4,4,4) onto PSL(2,25) × Z2 | 1 | 15600 | 3904 | 10–14 | 10–14 | **14** | 5 s |
| (6,6,6) 445 | 4 | 6912 | 220 | 20–24 | 20–24 | **24** | 446 s |
| (7,7,7) 16 | 4 | 10976 | 396 | 22–24 | 22–24 | **24** | 509 s |
| (4,4,6) 211 | 4 | 12288 | 260 | 26–28 | 26–28 | **28** | 10621 s |
| (5,6,6) 130 | 4 | 23040 | 676 | 24–28 | 24–28 | **28** | 11908 s |
| (4,4,6) 340 (our entry 339) | 4 | | | 30–32 | 30–32 | not run | |
| (7,8,8) 189 | 1 | 2688 | 1636 | 6–8 | 6–8 | **8** | < 1 s |
| (4,6,6) onto PGL(2,17), class 1 | 1 | 4896 | 2044 | 8–10 | 8–10 | **10** | < 1 s |
| (5,5,5) onto PSL(2,29), class 1 | 1 | 12180 | 4876 | 8–10 | 8–10 | **10** | 3 s |
| (4,4,5) onto PGL(2,19) × Z2, class 1 | 1 | 13680 | 4108 | 8–12 | 8–12 | **12** | 4 s |

15 open ranges closed; 15 certified values of the paper reproduced.
<!-- RESULTS4:END -->

Search times are wall-clock on 32 threads of one server socket; the (7,7,7), (7,8,8) and (6,6,6) rows
and the first part of the (4,4,6) "211" run used 8 threads, and the first seven rows ran on a laptop.

"Bounds recomputed" are the paper's two bounds from my own implementation
(`papers/hyperbolic_bounds.py`). They equal the printed range in every open row. For three rows with
n ≤ 2000 the paper prints a better lower bound than d_res (it gives 12 for [[256,8]], 8 for
[[128,36]] and 10–12 for [[1344,340]]); I assume these come from its connected-cluster runs.

**How the codes were rebuilt.**

- *Tilings.* A tiling is a finite group with three generating involutions a, b, c whose pairwise
  products have the orders (r, s, t). The paper names its tilings by a subscript and gives no group
  relations. GAP 4.15 with the LINS package (the tool the authors cite) lists all normal subgroups
  of the triangle group up to an index bound; the paper's subscripts are the positions in that
  list, counted from zero (`papers/hyperbolic_lins.g`, lists in `results/papers4/hyperbolic/`). The
  one exception met: its (4,4,6) "340" is entry 339 of our list. A position alone does not fix a
  tiling, though: LINS orders subgroups of equal index differently for different index bounds (the
  two order-400 quotients of (4,4,4) swap between our runs to 1344 and to 4096; they are the same
  tiling up to renaming the generators).
- *Tilings onto PSL(2,q) and PGL(2,q)* come from an exhaustive search for generating triples of
  involutions in those groups (no GAP needed). Where several inequivalent triples exist, the one the
  paper lists is the one whose two bounds equal the printed range; the others have other distances
  (for example 8 and 10 for the two maps of (4,6,6) onto PGL(2,17)).
- *Codes.* One qubit per small triangle of the fine triangulation, one X and one Z check per vertex
  (`papers/hyperbolic.py`, written by Codex and checked against the paper's certified values).
- *Identification.* A rebuilt tiling is taken to be the paper's row only if the position in the
  list, the certified distances and both bounds agree. The certified rows in the table are those
  checks. The bounds decide: in every group of tilings of equal order, exactly one tiling (up to
  renaming of the generators) has the range the paper prints, and it is the one used
  (`papers/hyperbolic_classes.py`, output in `results/papers4/hyperbolic/classes_check.txt`).

**How the distances were computed.** The same weight-bounded search as for the other code
distances, with the tiling's own symmetry group (left multiplication) reducing the starting points
to L² orbits of qubits; `papers/hyperbolic_run.py`. A lower bound is the exhaustion of all lighter
operators; every upper bound is a codeword that the driver checks against the check matrix.

**Not reached.** [[21504,340,36–38]], [[21120,444,30–32]] and the other codes with d of 30 or more:
the search grows by a factor of about 3 per unit of weight on these lattices (weight 27 took 1 to
1.7 hours on 32 threads for the three codes of distance 28). The PSL(2,23) and PSL(2,25) codes at L ≥ 3
have more than 16320 checks, the limit of the current kernel.

### Circuit distance of the modular surface-code circuits

For its modular hyperbolic surface codes the paper states the circuit distance only as an upper
bound, the shortest graph-like error found by Stim (its Table S2: 6 to 8 for codes of distance 10).
The circuits are not published. Codex rebuilt them from the text (`papers/hypsurf.py`, notes in
`papers/new/2610.03682_circuits.md`): the four {4,q} tilings of Table S2 at L = 5, square modules,
cat-state measurement of every check that touches several modules, the lifted "ZZ" and "NZ"
schedules, alternating rounds, and the multi-rate variant with 5 rounds that the table uses.

The schedule is not unique: each base face chooses one of 8 orders subject to constraints, which
leaves 4^F valid assignments for F faces, and the paper used the one its solver returned. So the
test of the rebuild is the distribution of Stim's graph-like distance over valid assignments. All 32
values of the table (four tilings, four schedule types, two bases) occur, and 30 of them are the
most frequent value.

<!-- RESULTS4C:BEGIN -->
| tiling | code | schedule | paper (graph-like bound) | graph-like, 256 sampled assignments (count) | exact, first valid assignment | exact, best sampled assignment |
|---|---|---|---:|---|---:|---:|
| {4,6} | [[150,4,10]] | ZZ, same order every round | 6 | 6 (150), 7 (106) | 6 | 7 |
| {4,6} | [[150,4,10]] | ZZ, alternating | 6 | 6 (150), 8 (106) | 6 | 8 |
| {4,6} | [[150,4,10]] | NZ, same order every round | 6 | 6 (212), 7 (44) | 6 | 7 |
| {4,6} | [[150,4,10]] | NZ, alternating | 8 | 8 (256) | 8 | 8 |
| {4,8} | [[200,6,10]] | ZZ, same order every round | 6 | 6 (186), 7 (70) | 6 | 7 |
| {4,8} | [[200,6,10]] | ZZ, alternating | 8 | 6 (186), 8 (70) | 6 | 8 |
| {4,8} | [[200,6,10]] | NZ, same order every round | 6 | 6 (230), 7 (26) | 6 | 7 |
| {4,8} | [[200,6,10]] | NZ, alternating | 8 | 8 (255), 9 (1) | 8 | 9 |
| {4,10} | [[250,8,10]] | ZZ, same order every round | 6 | 6 (192), 7 (64) | 6 | 7 |
| {4,10} | [[250,8,10]] | ZZ, alternating | 6 | 6 (192), 8 (64) | 6 | 8 |
| {4,10} | [[250,8,10]] | NZ, same order every round | 6 | 6 (233), 7 (23) | 6 | 7 |
| {4,10} | [[250,8,10]] | NZ, alternating | 8 | 8 (256) | 8 | 8 |
| {4,12} | [[300,10,10]] | ZZ, same order every round | 6 | 6 (218), 7 (38) | 6 | 7 |
| {4,12} | [[300,10,10]] | ZZ, alternating | 6 | 6 (218), 8 (38) | 6 | 8 |
| {4,12} | [[300,10,10]] | NZ, same order every round | 6 | 6 (250), 7 (6) | 6 | 7 |
| {4,12} | [[300,10,10]] | NZ, alternating | 8 | 8 (256) | 8 | 8 |

- {4,6}, ZZ, all 4096 valid assignments: graph-like distance (min over bases) 6: 2528, 7: 1568.
- {4,6}, ZZ, alternating, all 4096 valid assignments: graph-like distance (min over bases) 6: 2528, 8: 1568.
- {4,6}, NZ, all 4096 valid assignments: graph-like distance (min over bases) 6: 3416, 7: 680.
- {4,6}, NZ, alternating, all 4096 valid assignments: graph-like distance (min over bases) 8: 4072, 9: 24.
<!-- RESULTS4C:END -->

Graph-like distances are the smaller of the two bases; exact values are certified in both bases
(undecomposed detector error model, all lighter fault sets excluded, the fault set replayed in Stim).

- **The paper's upper bounds are exact** for these circuits: in all 64 circuits computed (32 with the
  first valid assignment, 32 with the best sampled one, each in both bases) the exact circuit
  distance equals the graph-like bound. Faults that flip three or more detectors (flag detectors
  included) do not give anything shorter.
- **The assignment matters as much as the schedule type.** With the "ZZ" schedule and alternating
  rounds the paper reports 6 for {4,6}, {4,10} and {4,12} and concludes that alternation alone does
  not help there. Among valid assignments 15 % to 41 % reach 8 on those tilings. With "NZ" and
  alternating rounds one sampled assignment of {4,8} reaches 9 (the table has 8). For {4,6} all
  4096 assignments of each type were scored (lines below the table): 24 of the "NZ" alternating
  ones have graph-like distance 9, and the exact circuit distance of one of them (faces
  0,4,3,5,2,6) is 9 in both bases. None reaches the code distance 10.

Choices the text leaves open and that the rebuild had to make (where each cat chain is cut and
rooted, the alignment of preparation layers, how the 5-round experiment ends for checks measured
every third round, the gate decomposition) are listed in the notes. They affect idle locations and
could change individual values. Rectangle modules are not rebuilt. The color-code circuits, for
which the paper states no circuit distance at all, are not rebuilt either: the placement of measure
qubits on skewed module boundaries is given only in figures.

## Check of the Cornucopia distances (20 October 2026)

Feng asked whether the distances of arXiv:2608.02773 (Cornucopia codes) and arXiv:2610.19073 (a modular
architecture built on the [[2844,1426,18]] Cornucopia code) are valid. Notes on the second paper are in
`papers/new/2610.19073.md`.

**Code distances: all seven are correct.** Both CSS distances were computed exactly
(`scripts/cornucopia_code_distance.py`). The search is label-free, with the covering bound and the q column
translations of each code, verified as symmetries. Each witness is checked to commute with the opposite checks and
to lie outside the stabilizer row space. Every row of H_X and H_Z has weight 12 and every column weight 3, so
the all-ones vector is a stabilizer of both types and every logical operator has even weight. The runs skip odd
thresholds for that reason. For [[2844,1426]] the run was repeated without this shortcut and gave the same values.

| code | paper | d_X | d_Z | search time |
|---|---:|---:|---:|---|
| [[252,130,6]] | 6 | **6** | **6** | < 0.1 s, 1 thread |
| [[576,292,8]] | 8 | **8** | **8** | < 0.1 s, 1 thread |
| [[900,454,10]] | 10 | **10** | **10** | 0.1 s, 1 thread |
| [[1044,526,12]] | 12 | **12** | **12** | 0.3 s, 1 thread |
| [[1764,886,14]] | 14 | **14** | **14** | 0.2 s, 64 threads |
| [[2304,1156,16]] | 16 | **16** | **16** | 0.8 s, 64 threads |
| [[2844,1426,18]] | 18 | **18** | **18** | 12–15 s, 64 threads (46 s without the parity shortcut) |

Building the matrices and the symmetry check take longer than the search: about one minute for the largest code.

**Circuit distances.** The paper's column d_circ holds upper bounds from a randomized BP-OSD search. The
authors' repository (commit fc12c97, `circuit_distance/estimate_distance.py`) runs that search on a memory circuit
with one syndrome cycle (`--rounds` defaults to 1 and the notebook that configures the long searches does not set
it) and with CNOT faults only. We rebuilt exactly that setting (`papers/cornucopia.py`, noise `cx`, one cycle) and
the memory experiment the paper simulates (N_c cycles, the paper's full fault model). The two fault models have the
same fault mechanisms: every preparation, reset and measurement flip is a component of the depolarizing fault of
an adjacent CNOT. Bold = exact; otherwise certified lower bound – verified upper bound. Every upper bound is a fault
set checked in the detector error model and replayed in Stim (no detector fires, logical observables flip). Table
from `scripts/summarize_cornucopia_check.py`:

| code | paper: d | d_X, d_Z | paper: d_circ | one cycle, CNOT faults | N_c cycles, paper's faults |
|---|---:|---|---:|---|---|
| [[252,130,6]] | 6 | 6, 6 | ≤ 5 | **5**; **5** (Z; X) | 6 cycles: **5** (Z); **5** (X) |
| [[576,292,8]] | 8 | 8, 8 | ≤ 8 | **8**; **8** (Z; X) | 6 cycles: **8** (Z); **8** (X) |
| [[900,454,10]] | 10 | 10, 10 | ≤ 10 | **9**; **9** (Z; X) | 6 cycles: **9** (Z); **9** (X) |
| [[1044,526,12]] | 12 | 12, 12 | ≤ 11 | **10**; **10** (Z; X) | 6 cycles: **10** (Z); **10** (X) |
| [[1764,886,14]] | 14 | 14, 14 | ≤ 14 | 11–14 (Z) | 7 cycles: 12–14 (Z) |
| [[2304,1156,16]] | 16 | 16, 16 | ≤ 16 | 12–14 (Z) | 8 cycles: 12–14 (Z) |
| [[2844,1426,18]] | 18 | 18, 18 | ≤ 18 | 12–17 (Z) | 8 cycles: 12–16 (Z) |

For [[900]] and [[1044]] the published bound is one too high even in the authors' own setting: BP-OSD missed fault
sets of weight 9 and 10. One cycle and six cycles give the same value for all four codes, so the number of cycles is
not the cause.

For the three largest codes the published bounds equal the code distances. Two of them are too high:

- [[2304,1156,16]] has an undetected logical fault set of weight 14 (598 observables flip). It lies in the first
  cycle of the 8-cycle circuit and replays unchanged in the one-cycle circuit (`scripts/cornucopia_transfer_check.py`),
  so the authors' own setting also has a weight-14 fault set.
- [[2844,1426,18]] has one of weight 16 in the 8-cycle circuit, and one of weight 17 in the one-cycle circuit.
- For [[1764,886,14]] the best fault set found has weight 14, the published bound.

How the large intervals were obtained (`papers/run_parallel.py` with the covering bound, and
`scripts/window_search.py`):

- Lower bounds: the time-collapsed problem. [[1764]] has collapsed distance 11, with a single symmetry orbit of
  minimum solutions that does not lift to the circuit, so its lower bound is 12. For [[2304]] and [[2844]], weight 11 is
  excluded, about 3 h each on 64 threads.
- The collapsed columns of one cycle are a subset of those of N_c cycles, so the collapsed bounds also hold for one
  cycle. The lifting step for [[1764]] was done on 7 cycles only.
- Upper bounds: exact searches of a one-cycle window, the faults whose detection events lie in one round. In the
  N_c-cycle circuits the window minima are 14, 14 and 16. In the one-cycle circuits, the faults seen only by the final
  readout have minima 14 ([[1764]]) and 17 ([[2844]]).
- Exact values at 12 to 16 are out of reach on the full problems. The exact search of all of [[1764]]'s 7-cycle
  problem ran 3 h at weight 12 without finishing.

Consequence for the paper's error rates: it fits the logical error rate as p^(d/2) exp(c0 + c1 p + c2 p^2) with the
code distance d. With circuit distances below d the leading order is lower: p^5 instead of p^6 for [[1044]], at most
p^7 instead of p^8 for [[2304]], at most p^8 instead of p^9 for [[2844]]. The extrapolated values at p = 1e-3 and
1e-4 in Tab. 1 are therefore optimistic, and so is the 2.6e-16 per logical qubit and cycle that arXiv:2610.19073
quotes for [[2844,1426,18]].

The randomized witness search of `scripts/run_isd.py` finds the optimum for [[900]] (one cycle: 9, in 4 min) and
[[1044]] (a two-cycle window of the 6-cycle circuit: 10, in 3 min). It finds nothing on the large circuits: it
inspects only one free column plus pivot columns, and with about 900 rows against 11,000 to 20,000 columns a
minimum-weight solution almost never has that form.

**arXiv:2610.19073.** Its only computed distance is d = 18 of [[2844,1426]], cited from the first paper and confirmed
above. The distances of its merged codes (surgery gadgets, extractor, bridges) follow from its Theorem 2 (expansion
h2 ≥ 1 with a complete cycle basis) and Proposition 1 (bridges of b ≥ d edges); the expansion is certified through
λ2 > 2 with exact integer arithmetic. "Verified exactly" in its Extended Data Tabs. 3 and 4 refers to rank,
commutation, weights and these certificates; no merged-code distance is computed. The gadget graphs are not public,
so these distances cannot be checked here without the authors' data. The paper makes no circuit-level distance
claim.

## Reproduce

    .venv/bin/python papers/run_mitten.py "[[150,30,10]]" Z results/papers/mitten150_Z.json 10 2 600
    .venv/bin/python papers/run_mitten_isd.py "[[540,108,18]]" X out.json 1500           # witness search
    .venv/bin/python papers/mitten_restricted_isd.py "[[780,156,22]]" X out.json 60     # restricted witness search
    .venv/bin/python papers/smitten_check.py 3                                          # structured mitten: construction and fault-model checks
    .venv/bin/python papers/run_mitten.py "structured_mitten/[[330,66,12]]" Z out.json 12 2 0 0      # 7, in seconds
    .venv/bin/python papers/run_mitten.py "structured_mitten/[[600,120,14]]" Z out.json 14 3 0 0 10  # from the certified bound 10, k_table 3
    .venv/bin/python papers/mitten_restricted_exact.py "structured_mitten/[[840,168,18]]" Z out.json 2,3 16 2   # hooks after gate 2 or 3 only
    .venv/bin/python papers/smitten_code_distance.py "structured_mitten/[[840,168,18]]" Z out.json 30 21600 900 3   # code distance
    .venv/bin/python papers/smitten_pipeline.py "structured_mitten/[[330,66,12]]" X out.json 3 6 1800   # cross-check: dp=2 pipeline on the Stim circuit
    .venv/bin/python papers/smitten_check.py witnesses                                  # fault kinds of every structured-mitten witness
    .venv/bin/python papers/amplified_circuit.py 1 Z 8 circuits/papers/amp1_r8_Z.stim
    .venv/bin/python run_bb.py circuits/papers/amp1_r8_Z.stim results/papers/amp1_r8_Z.json --sector-high --no-sym --folds 2
    .venv/bin/python scripts/run_deep.py circuits/bb360_r24_Z.stim out.json --skip-ub --kmax 16 --k-table 4 --table-load 0.8
    .venv/bin/python scripts/run_isd.py circuits/bb360_r24_Z.stim out.json 1 1 600
    .venv/bin/python scripts/summarize_papers.py                                                # PAPERS_RESULTS.md and the tables above
    .venv/bin/python papers/run_parallel.py cornucopia 7 Z out.json 6 2 8               # [[252,130,6]]: seconds on a laptop
    .venv/bin/python papers/run_parallel.py cornucopia 25 Z out.json 6 3 12             # [[900,454,10]]: needs about 80 GB
    .venv/bin/python papers/selfdual_bb.py out.json                                     # 57 self-dual BB codes, 18 s
    .venv/bin/python papers/gala_codes.py out.json                                      # 11 GALA codes, 14 s
    .venv/bin/python papers/gala.py                                                     # shows that the printed layer order is not a valid circuit
    .venv/bin/python papers/cornucopia_crosscheck.py                                    # rebuilt circuits against the authors' repository
    .venv/bin/python papers/kasai_codes.py out.json 16                                  # pair-partition CSS instances
    .venv/bin/python papers/design_selfdual_bb.py 64 out.json 8                         # all 5040 gate orders of [[64,8,8]]
    .venv/bin/python papers/design_gala.py 132 out.json 64 1500 8 900 1 64 5400         # order search for GALA [[132,30,12]]
    .venv/bin/python scripts/summarize_papers2.py                                               # tables of the second batch
    .venv/bin/python papers/run_parallel.py lrgross lr11 Z out.json 6 3 12              # gross code, left-right circuit: 11
    .venv/bin/python papers/run_parallel.py routing 140_13 Z out.json 6 3 14            # routing [[140,8,13]]: 12
    .venv/bin/python papers/run_parallel.py routing 200_24 Z out.json 6 3 12 7200 1     # routing [[200,24,14]]: 10
    .venv/bin/python papers/star_run.py paper 42 Z out.json 6 2 10                      # STAR Table 2 schedule: 6
    .venv/bin/python papers/crosscheck_full.py circuits/papers/star42_r6_Z.stim 5 out.json   # same, full DEM, no reductions
    .venv/bin/python papers/walkingcat_labelings.py 70 8 Z                              # all numberings of the Walking Cat terms
    .venv/bin/python papers/run_parallel.py shift 120d Z out.json 6 3 12                # dynamic shift circuit: 8 (120s: 10, 120b: 8)
    .venv/bin/python papers/estimated_codes_run.py out.json 20 1800                     # 250 codes with estimated distances
    .venv/bin/python papers/design_sdbb_parallel_all.py 56 8                            # all 3456 mirror orders of [[56,6,8]]
    .venv/bin/python scripts/summarize_papers3.py                                               # tables of the third batch
    gap -q -c 'r:=4;; s:=4;; t:=4;; bound:=1344;; out:="lins_444_1344.jsonl";;' papers/hyperbolic_lins.g   # tilings (GAP + LINS)
    .venv/bin/python papers/hyperbolic_run.py out.json lins444_109_L2 40 3600           # [[1600,104,14-16]]: 16
    .venv/bin/python papers/hyperbolic_bounds.py lins444_109_L2                         # the paper's two bounds: 14, 16
    .venv/bin/python scripts/summarize_hyperbolic.py                                            # table of the fourth batch
    .venv/bin/python papers/run_parallel.py hypsurf q6_L5_NZ_fb Z out.json 5 3 12       # {4,6} surface-code circuit: 8
    .venv/bin/python papers/run_parallel.py hypsurf_pick q8_L5_NZ_fb@228 Z out.json 5 3 12   # a better assignment: 9
    .venv/bin/python scripts/summarize_hypsurf.py                                               # circuit table of the fourth batch
    .venv/bin/python scripts/cornucopia_code_distance.py out.json 7,16,25,29,49,64,79 XZ    # Cornucopia code distances
    .venv/bin/python papers/run_parallel.py cornucopia 29 Z out.json 1 3 20 3600 1 cx     # one cycle, CNOT faults: 10
    .venv/bin/python papers/run_parallel.py cornucopia 49 Z out.json 7 2 18 10800 1 full 1   # 7 cycles, covering bound
    .venv/bin/python scripts/summarize_cornucopia_check.py                                      # table of the Cornucopia check

The exhaustive runs for [[300,60,14]] at weight 11 took 2.7 hours (X) and 4.0 hours (Z) on 64
threads each;
the BB360 lower bound took 1.5 to 2 hours on 80 threads per basis with a 300 GB lookup table.
For the structured mitten codes with n = 600 and 840, weight 9 took 27 to 46 minutes on 32
threads with the depth-2 table, and weight 10 took 11 to 26 minutes (n = 600, 32 threads) and
31 to 35 minutes (n = 840, 48 threads) with the depth-3 table (143 GB and about 430 GB, built
in 2 to 15 minutes).
Everything else ran in minutes. Server logs are in `logs/server/papers/`.

## Limits

- "Circuit distance" is for the circuit as I built it from the published schedule and the stated
  fault model. If the authors' simulations used a different gate order than the published file,
  the numbers do not transfer.
- For mitten codes with n ≥ 500 only the X-basis value of [[500,100,16]] is exact. The other
  entries are intervals; the upper ends may drop with a longer search.
- The structured [[840,168,18]] circuits stay at 11–14. The full search at weight 11 would take
  about 16 hours on 48 threads with a 430 GB lookup table per basis; the upper end comes from
  witness searches that can miss lighter fault sets. [[1200,240,20]] has no published schedule,
  and its code distance is only bounded (15–20).
- The second amplification level could not be decided: the search grows by a factor of about 30
  per unit of weight on that problem, and the gap between the paper's bound (12) and the code
  distance (16) is out of reach.
- BB756 is out of reach in both directions; only a lower bound is reported.
