# Audit of published distance values (inventory, 25 October 2026)

Every published code or circuit distance that this project has checked with its exact method, collected for the
paper's "audit" figure. It is an inventory of results already obtained, not new runs. Sources:
[PAPERS.md](PAPERS.md) (four batches of papers and the Cornucopia check),
[results/planar_dp/README.md](../results/planar_dp/README.md) (2026 planar codes),
[BENCHMARK.md](BENCHMARK.md) (the instances of arXiv:2603.22532) and
[results/sparse_dp/README.md](../results/sparse_dp/README.md). Every exact value here has a certified lower bound
(all lighter fault sets excluded) and an explicit fault set, checked against the matrices and, for circuits,
replayed in Stim. An interval gives the certified lower bound and the lightest fault set found.

**Provenance.** A: the authors' own circuit or data files. R: rebuilt from the paper's text (with the
cross-checks named in the notes). Fault models are the papers' own unless a note says otherwise.

## Summary

- 26 papers (and one data page) with checked numbers.
- **Published values that are too high:** in 10 papers at least one is above the exact or certified value. These
  are counted where the paper states a distance, an estimate, an expectation or a bound that a reader takes as
  the distance; misprinted table rows are not counted. All 10 are circuit distances, or code distances
  estimated by sampling. The mitten values were also checked under the fault model of that paper's
  estimator: they hold.
- **Settled:** 2 conjectures confirmed. 15 open ranges of one paper closed, plus several single open values,
  among them the superdense color-code circuit of d = 11 that no method had certified.
- **Confirmed:** hundreds of published values, among them every code distance that a paper states as exact.
- **The pattern:** the code distances that authors report are almost always right. The circuit distances,
  usually upper bounds from a sampling search (BP-OSD, QDistRnd, randomized information sets), are where claims
  fail. Those searches miss the fault sets that combine hook errors of high-weight checks.

## 1. Published values that are too high

| paper | object | published value (how stated) | here | prov. | notes |
|---|---|---|---|---|---|
| mitten codes, 2607.28795 v2 | [[200,40,12]] circuit | 12 (stated as distance-preserving; an upper bound from the GPU estimator sQetch on a two-round circuit with single-qubit Pauli faults) | **9** | A | v2 states 8 for [[150,30,10]], as we find. The values hold under the estimator's fault model too (note below the table). The data-only distances are as stated |
| mitten codes | [[300,60,14]] circuit | 14 (same) | **12** | A | weight 11 excluded in 2.7 h (X) and 4.0 h (Z) on 64 threads |
| mitten codes | [[500,100,16]] circuit | 16 (same) | **9** (X basis), 11–16 (Z) | A | |
| mitten codes | [[540,108,18]] to [[975,195,24]] circuits | 18, 20, 22, 24 (same) | 10–13, 9–12, 9–16, 9–17 | A | intervals over both bases: certified lower bound and lightest fault set found; every upper bound is below the claim |
| Cornucopia codes, 2608.02773 | [[900,454,10]] circuit | ≤ 10 (BP-OSD) | **9** | R | matrices and gate orders equal to the authors' repository; same value in their own one-cycle, CNOT-only setting |
| Cornucopia codes | [[1044,526,12]] circuit | ≤ 11 (BP-OSD) | **10** | R | |
| Cornucopia codes | [[2304,1156,16]] circuit | ≤ 16 (BP-OSD) | 12–14 | R | a weight-14 fault set, also in the authors' one-cycle setting |
| Cornucopia codes | [[2844,1426,18]] circuit | ≤ 18 (BP-OSD) | 12–16 (8 cycles), 12–17 (1 cycle) | R | |
| a modular architecture on Cornucopia, 2610.19073 | [[2844,1426,18]] logical error rate | 2.6e-16 per qubit and cycle, from a fit with exponent d/2 | optimistic | – | consequence of the row above: the leading order is at most p^8, not p^9 |
| routing codes, 2606.25330 | [[200,24,14]] circuit, weight-11 checks | ≤ 14 (BP-OSD) | **10** | R | rebuilt code has distance 14; the loss is in the circuit |
| routing codes | [[200,16,17]] circuit | ≤ 17 (BP-OSD) | 11–14 | R | |
| time-dynamic shift circuits, 2601.09911 | gross code [[144,12,12]], dynamic circuit (Table III) | ≤ 10 (estimate) | **8** under all 12 valid numberings | R | the static circuit with the same CNOT order also has 8: the cost is Table III's gate order, not the dynamics |
| Walking Cat, 2604.19481 | [[102,22,9]], [[70,6,9]], [[54,2,10]] circuits | 9 | **8** with the terms numbered as printed | R | the numbering is not printed; the best numberings give 9 for two codes, and for [[70,6,9]] 9 only in the Z basis |
| tile codes, 2504.09171 | [[512,18,≤23]] code, weight 10 | ≤ 23, authors "strongly expect" 23 | **21** (d_X = 21; d_Z 22–23) | R | layout inferred (the only square layout with n = 512); the same layout reproduces their ILP-exact [[512,18,19]] |
| nearest-neighbour planar codes, 2606.19482 | [[259,2]] thin tile code, X distance | ≤ 37 (QDistRnd) | **36** | R | reproduces all of Table III's n, routing counts and IP-exact d_Z; the paper's ranking value drops from 1.14 to 1.11 |
| multivariate multicycle codes, 2601.18879 | [[324,12]] code | 20 (estimate) | **18** | R | 12 more table rows differ, several with visible misprints; only the distance of the printed code is established |
| benchmark of distance methods, 2603.22532 | [[288,12,18]] bivariate bicycle circuit | 24 (best known value, heuristic) | **16** | A | their own circuit file |
| IBM bivariate bicycle codes, 2308.07915 (Nature 2024) | [[288,12,18]] circuit, standard depth-7 schedule | ≤ 18 (BP-OSD) | **16** (both bases) | A | tesseract-decoder SI1000 files of the IBM schedule. The same bound recurs in later papers; dist-m4ri's benchmark (October 2026) leaves it at 12–18 |

**Fault model of the mitten rows.** Our runs use the noise of the paper's simulations: a two-qubit depolarizing
fault after every CX, plus preparation and measurement faults. The paper's estimator, sQetch, used single-qubit
Pauli faults. `papers/mitten_fault_model_check.py` compares the memory-sector problems column by column (results
in `results/papers/mitten_fault_models.json`):

- **Single-qubit faults on both qubits of every CX**, with the same preparation and measurement faults: the
  problems have exactly the same columns as ours. This holds for all eight codes in both bases, at 3 rounds and
  at the 10 and 12 rounds of the [[150]] and [[200]] runs. The distances are the same.
- **Single-qubit faults after the CX gates only:** the Z-basis problems are again identical. The X-basis problems
  lack one column per data qubit (a Z fault before the first round).
  - Every fault of this model is a single fault of ours, so its distances are at least ours.
  - Every X-basis fault set on record uses only single-qubit faults right after a CX, so each is also a fault
    set of this model.
  - Every exact value and interval in the mitten rows therefore holds in this model too.
  - Direct runs in this model (X basis, 3 rounds): exactly 8 for [[150,30,10]]. For [[200,40,12]], weight 8 is
    excluded; the 25-minute run stopped before it found the weight-9 fault set.
- **Idle faults** can only lower a distance, so they cannot make a published value correct. For the three smallest
  codes they leave the problem unchanged ([PAPERS.md](PAPERS.md)).

## 2. Conjectures confirmed and open values settled

| paper | object | published | here | prov. |
|---|---|---|---|---|
| left-right circuits, 2603.05481 | gross code [[144,12,12]], explicit three-colour schedule | 11, conjectured | **11** (both bases) | R |
| vine codes, 2606.20263 | the four d = 10 patches of Table II | 10, conjectured and stated as unverified | code distance **10** and circuit distance **10** in X and Z memory, all four | A (their Stim files) |
| benchmark of distance methods, 2603.22532 | superdense color-code circuit, d = 11 | open (every method 8–11; best heuristic value 11) | **11** (sparse DP; four sweeps, two witnesses) | A |
| modular hyperbolic codes, 2610.03682 (Google) | 15 codes with printed ranges, n up to 31,200 | ranges, e.g. [[2048,36,20–24]], [[5376,88,26–28]], [[31200,1954,22–24]], [[23040,676,24–28]] | all **closed at the upper bound** (24, 28, 24, 28, …) | R |
| modular hyperbolic codes | 16 surface-code circuits of Table S2 | graph-like upper bounds (Stim) | the bounds are **exact** in all 64 circuits computed | R |
| amplified qLDPC codes, 2609.37231 | level-1 [[90,8,8]] circuit | certified ≥ 6, target 8 | **8** | A (their builder) |
| amplified qLDPC codes | level-2 [[468,16,16]] circuit | certified ≥ 12 | 12–16 (ours alone ≥ 11) | A |
| nearest-neighbour planar codes, 2606.19482 | [[269,4]], [[365,10]] thin tile codes, X distance | ≤ 28, ≤ 31 (QDistRnd) | **28**, **31** (bounds tight) | R |
| nearest-neighbour planar codes | [[537,14]], X distance | ≤ 35 | 20–30 | R |
| weight-8 bivariate bicycle codes, 2609.06572 | [[144,6]], [[144,10]] codes | ≥ 15, ≥ 11 | **15**, **14** | R |
| IBM bivariate bicycle codes, 2308.07915 | [[360,12,≤24]] code | ≤ 24 | **24** | A |
| IBM bivariate bicycle codes | [[360,12]] circuit (24 rounds) | none | 17–21 (Z), 19–21 (X): below the code distance | A |
| benchmark of distance methods, 2603.22532 | 24 instances without an exact value there | heuristic values | **exact**; 23 confirm their best heuristic value, one does not ([[288,12,18]], section 1) | A |

## 3. Published bounds and estimates that are exact, and values confirmed

| paper | what | result |
|---|---|---|
| routing codes, 2606.25330 | the eight weight-7 circuits | all eight BP-OSD bounds exact (6, 7, 8, 9, 9, 10, 11, 12); Table 1's 7 for [[80,8]] is a misprint (Tables 2 and 3 say 8) |
| Cornucopia codes, 2608.02773 | code distances, both CSS types, all seven codes | all correct |
| Cornucopia codes | [[252,130,6]] and [[576,292,8]] circuits | bounds exact (5 and 8) |
| STAR architecture, 2606.25011 | the 212 valid depth-8 schedules of [[42,6,6]] | the paper's histogram (192 at 4, 20 at 5) reproduced exactly under two index conventions, which identifies its convention |
| time-dynamic shift circuits, 2601.09911 | the other three codes | estimates reproduced (for [[120,8,12]] with 7 of 12 numberings) |
| self-dual bivariate bicycle codes, 2510.05211 | 57 codes | all 57 distances as stated |
| GALA codes, 2608.07431 | 11 codes over abelian groups | all 11 as stated |
| pair-partition codes (K. Kasai's data page; 2607.14091, 2609.30069) | 13 codes | 10 of 10 stated distances agree |
| multivariate multicycle codes, 2601.18879 | 215 codes | 214 exact, 201 equal to the printed value (differences: section 1 and its note) |
| weight-8 BB 2609.06572, clustered lifted-product 2603.05398, balanced-product 2607.27644, LLM-guided BB 2606.02418 | 35 codes | all consistent; the balanced-product upper bounds (16, 18, 18, 20) and the bound 24 of [[360,12]] are exact |
| planar codes: tile families 2607.05897, barbell codes 2606.06062, BB surface codes 2606.08771, space-group codes 2606.20548 | every reported instance (about 200) | all reported values reproduced; for the BB surface codes, whose randomized bounds come without region sizes, the exact distance identifies the authors' size in 86 of 88 rows |
| vine codes, 2606.20263 | Fig. 7 circuit distances | reproduced |
| benchmark of distance methods, 2603.22532 | 73 values certified by its five exact methods | all agree |
| IBM bivariate bicycle codes, 2308.07915 | [[72,12,6]], [[90,8,10]], [[108,8,10]], [[144,12,12]] circuits | the BP-OSD bounds ≤ 6, ≤ 8, ≤ 8, ≤ 10 are exact (6, 8, 8, 10); also certified by others: 6 and 8 by MaxSAT (Tesseract, 2503.10988), 8, 8 and 10 by dist-m4ri (October 2026) |
| mitten codes, 2607.28795 v2 | [[150,30,10]] circuit | 8 as stated in v2 (v1 implied 10) |

## 4. Exact distance as a design tool (circuits found here)

| code | published or standard circuit | best found here | how |
|---|---|---|---|
| gross code [[144,12,12]] | 10 (standard depth-7 schedule of 2308.07915) | **11**; no depth-7 one-ancilla schedule reaches 12 | all 8496 valid depth-7 schedules, exact |
| [[108,8,10]] | 8 (standard schedule) | **10**, the full distance | same |
| [[90,8,10]] | 8 | **9** (outside the standard family) | same |
| weight-8 BB [[72,14,8]], [[144,16,10]], [[144,10,14]] (2609.06572, no circuit published) | – | **8**, **10** (full distances), **12** | mirror depth-8 circuits, all 3456 orders exact for the first two |
| self-dual BB codes (2510.05211, no circuit published) | – | the full distance for most codes up to n = 130, e.g. [[120,8,12]] at **12** | parallel depth-8 mirror circuits |
| GALA [[132,30,12]] | 8 (the paper's layer order, read as sequential rounds) | **10** | parallel 12-layer circuit |
| STAR [[42,6,6]] | 5 (the paper's best) | **6**, the full distance (8 schedules, natural index reading) | all 212 schedules exact |
| hyperbolic surface codes of 2610.03682 | 6 and 8 (Table S2) | 8 and **9** for some valid assignments of the same schedule types | graph-like screening, exact check |

## 5. Not tested or not decided

- Coset codes, 2606.17268: needs GAP's SmallGroups or the authors' repository (builder written).
- Stairway codes, 2603.00228: three of six instances only in the Zenodo supplement.
- Bunny codes 2606.22853, morphing circuits 2604.09797, non-CSS mirror codes 2603.05496: not attempted.
- Ultra-high-rate non-CSS codes, 2609.30069: no construction published.
- GALA circuits, 2608.07431: the printed layer order does not give deterministic measurements as read.
- 2610.19073's merged codes: graphs not public.
- Still open: mitten codes from n = 500 (intervals), [[1764,886,14]] Cornucopia circuit (12–14, the paper's
  bound ≤ 14), [[756,16,≤34]] IBM circuit (only lower bounds), amplified level 2 (12–16).

## For the paper

- **Clean headline items:**
  - the mitten circuits (authors' own schedules, exact, losses of 2 to 7);
  - Cornucopia (authors' setting reproduced; consequence for their extrapolated error rates);
  - routing [[200,24,14]] (10 against 14);
  - the WJH [[288,12,18]] circuit (16 against 24);
  - superdense d = 11 (open, now 11);
  - the left-right gross conjecture and the vine-code conjectures;
  - the 15 hyperbolic ranges;
  - the depth-7 schedule optimum for the gross code (11 against the standard 10).
- **Needs careful wording:**
  - Walking Cat, the shift circuits and STAR, where the index numbering is not printed: state the reading.
  - The tile code [[512,18]], whose layout is inferred.
  - The multicycle rows, which have misprints.
  - The strip [[259,2]], whose published value is an upper bound: "one below the published bound", not "wrong".
- **Before using any row:**
  - Recheck its record.
  - Recheck the paper's version: the mitten paper changed between versions.
  - Recheck the fault model behind its number. A circuit distance depends on what counts as one fault. For the
    mitten codes, see the fault-model note in section 1.
