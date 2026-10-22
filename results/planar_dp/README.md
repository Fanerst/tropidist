# Dense Rank DP on the planar 2D-local codes of 2026

Question: are there open distance questions narrow enough for the dense Rank DP (cost about 2^(cut rank of a
column order), independent of the distance) that the weight-bounded search (cost growing with the distance)
cannot settle?  Every open case measured before this study was an expanding qLDPC code with a DP width far
beyond reach; planar codes with open boundaries should have widths that grow only with the linear size.

## Verdict

**The DP settles one kind of open question: long, thin patches, whose distance is set by the long side and whose
DP width by the short side.** Table III of arXiv:2606.19482 lists four such directional tile codes whose d_X the
paper could only bound (QDistRnd upper bounds; its integer program does not terminate above 20).  Their d_X
problems have widths 5, 10, 18 and 39:

| code (Table III) | M x N | paper d_X | width | d_X (DP front end, 2 threads) | search alone, 32 threads |
|---|---|---|---|---|---|
| [[259,2,d_X,4]], NESEN | 22 x 3 | <= 37 | 5 | **36** in 1.2 s (DP 0.002 s) | 360 s |
| [[269,4,d_X,5]], N²ESEN² | 22 x 3 | <= 28 | 10 | **28** in 1.3 s (DP 0.015 s) | 69 s |
| [[365,10,d_X,4]], N²E²SE²N² | 19 x 4 | <= 31 | 18 | **31** in 13 s (DP 1.2 s) | running (with 2 threads: lower bound 26 after 1800 s) |
| [[537,14,d_X,12]], N²E²SESE²N² | 12 x 13 | <= 35 | 39 | does not fit | [19, 30]: search lower bound in 1800 s, our ISD upper bound |

So the paper's bound for [[259,2,·,4]] was one too high (a weight-36 X logical exists and is the lightest), the
other two are tight, and the paper's ranking value k d_X d_Z / n of the first code drops from 1.14 to 1.11.  These
are the only problems of this study where the DP is needed in practice.  The DP itself takes 2 ms, 15 ms and 1.2 s
on 2 threads; the search alone reaches the same values on 32 threads, but in minutes to hours, and its time
roughly doubles with every unit of distance (each threshold costs twice the one before), while the DP's cost does
not depend on the distance at all.

**Every other open question here is settled by the weight-bounded search; one published value is wrong:**

- *Tile code [[512,18,≤23]]* (arXiv:2504.09171, weight 10, found by a randomized search; the authors "strongly
  expect" d = 23): **d = 21**.  d_X = 21 exactly (all weights up to 20 excluded, a weight-21 X logical found,
  1740 s on 32 threads); d_Z is in [22, 23] (weights up to 21 excluded; weight 23 from our ISD).  DP widths 42 and
  48: out of reach.
- *Vine codes, Table II of arXiv:2606.20263* (four d = 10 patches whose distances the authors conjecture and
  state as not verified): the code distances are d_X = d_Z = 10 for all four (search, under 1 s), and the circuit
  distances of their syndrome circuits are **10 in X and in Z memory for all four patches** (10 rounds; also 14
  rounds for two of them).  The pipeline (`ours_pipeline`, 16 threads) settles all 8: in 20 to 40 s where its
  time collapse is tight (5 circuits), in 21 to 30 min where it is not (3 circuits: the collapse gives only 6,
  because vine rounds alternate the step sequence and its reverse and their hook errors combine once the round is
  forgotten, so the sector search has to exhaust weights 7 to 9).  A fold of period 2 keeps the alternation and
  settles all 8 by search in 4 to 31 s.  The DP evaluates the collapse where it fits (widths 27 to 31: values 10,
  10, 10 and 6, 6, 6), but the tight fold-2 problem has widths 52 to 82.
- *BB surface codes* (arXiv:2606.08771, every distance a vecdec upper bound, region sizes not given): all
  reported values are exact.  Of the 88 instances with a reported distance (Table II and the worked examples), 87
  have a region size whose exact distance equals the reported value, and in 86 of them exactly one size does, so
  the distance also identifies the authors' region size; no size has a distance above a reported value.  The
  exception is Example 6's amended [[314,12,14]], which our reconstruction gives with d_Z = 12 (see Caveats).
  The search settles the paper's codes in seconds.  The DP is needed only on elongated alternative sizes, which
  are not the paper's codes but show the same regime as Table III: on six of them (d_X or d_Z from 28 to 54, e.g.
  the 4 x 28 region of the k = 7 row with d_Z = 54) the DP front end takes 1 to 90 s and the search alone does not
  finish in 30 min, both on 2 threads.
- *Distances given without a method* — the four tile-code families of 2607.05897 at every size, the 27 barbell
  codes, the square-grid directional tile codes of 2606.19482, the Fig. 4 and Table III space-group codes — are all
  exact now and all equal the reported values (among them the barbell w8 [[450,16,14]], whose jump from d = 11
  at n = 392 to 14 the barbell builder flagged).  The search solves each in at most 10 s, nearly always within the
  1 s head start the DP front end gives it.
- *Reported exact values* (2504.09171's ILP distances, 2606.20548's SAT distances, 2606.19482's IP values, the
  vine paper's Fig. 7 circuit distances) are all reproduced, which checks the constructions.

Why the DP rarely wins on these codes: for a roughly square patch, the DP width and the distance both grow with the
linear size, and at the distances of 2026's planar codes (d ≤ 23) the search is still fast; even [[512,18,19]]
(width 45) takes it 12 to 26 s on 32 threads.  The DP's regime is a patch whose distance grows while its width stays fixed, which among
the published instances only the unbalanced strips of Table III are.  The other hard open cases are wide:
[[537,14,·,12]] (39), tile [[512,18,≤23]] (42/48), barbell w8/w10 at n ≥ 338 (35 to 45), and the space-group
codes, whose checks span most of their small lattices (widths up to 49 at n = 156).

## What was done

**Instances.** Six families from the 2026 catalog (`../code_instances`), with every finite instance their papers
report, built as check matrices by `papers/planar_<family>.py` (interface `papers/planar_common.py`; reading notes
in `papers/new/<arXiv id>.md`):

| family | paper | builder | instances | n and k reproduced |
|---|---|---|---|---|
| vine codes | 2606.20263 | `planar_vine.py`: codes read off the authors' Stim circuits (Zenodo 10.5281/zenodo.20746752) | 11 | all |
| tile codes | 2504.09171, 2607.05897 | `planar_tile.py` | 46 | all |
| nearest-neighbour planar-grid codes | 2606.19482 (v2) | `planar_nngrid.py` | 31 | 30 (hexagonal [[74,10,4]] built at n = 76, see below) |
| BB surface codes with boundaries | 2606.08771 | `planar_bbsurface.py` | 89 (229 with every candidate region size) | all, at every candidate size |
| barbell codes | 2606.06062 | `planar_barbell.py` | 27 | all |
| space-group codes | 2606.20548 (v3) | `planar_spacegroup.py` | 63 | all |

**DP width** (`scripts/planar_dp.py widths`). For each instance and each memory basis (the X-error problem,
distance d_X, and the Z-error problem, d_Z) the width is the cut rank of the best column order found among: the
natural order, geometric sweeps of the lattice (36 directions and the patch vectors), greedy orders
(`cdist.ordering.greedy_order`, up to 2000 columns), and a local search (`cdist.ordering.improve`) started from
the best of these.  "fits" uses the largest table of the DP plan for that order (`cdist.auto` with its +1 margin):
yes = at most 2^33 bytes (8 GiB), 64 GiB = at most 2^36 bytes, no = larger.

**Distances.** Each problem was exported with its qubits renumbered in the best order
(`scripts/planar_dp.py export`, instances in `instances/`, matrices regenerated on demand) and solved by the
pipeline adapter `bench/adapters/ours_pipeline.py` twice: with the DP front end (`dp=1`: the DP when its
predicted time is short or the search has not finished within it) and as the search alone (`dp=0`).  Runs on
the server 5090 with `scripts/planar_jobs.py` (2 threads where the DP table is at most 2^28 bytes, 16 up to 2^33,
32 above; 1800 s limit; the vine instances also locally), and the search-alone runs on the Table III strips again
with 32 threads and a 3 h limit; records in `code_dp1/` and `code_dp0/`, the fastest exact record is shown.  Every exact value has a fault set (witness) checked
against the matrices; no value rests on the DP alone.

**Vine-code circuits.** The authors' noisy Stim files (Fig. 7) were reproduced exactly from their schedules by
`papers/planar_vine.py memory_circuit`: same gates in every layer, same detectors, and the same set of error
mechanisms as the published circuits (all 12 files, X and Z memory), including the CZSWAP routing with one flag
detector per routing qubit and the extra swap the authors' generator puts in the last round.  The d = 10 patches
of Table II exist only as noiseless two-round files (Fig. 5); the same construction turns them into 10-round
X- and Z-memory experiments (`circuits/`), with SI1000 noise on every idle qubit (the authors' files put idle noise
on only part of the idle qubits, so this fault set contains theirs and its circuit distance is a lower bound on
theirs; the upper bound, a code-distance logical on the data qubits at the first round, exists in both).
The adapter's time collapse (`cdist.problem.collapse_time`) is loose for these circuits, because vine rounds
alternate between the step sequence and its reverse: hook errors of a forward and a reversed round combine as if
they happened in one round.  The fold of period 2 (`cdist.problem.fold_time`, detectors of a check XOR-ed over
rounds of equal parity) keeps that distinction and is still a relaxation; `scripts/planar_fold.py` searches it
for the lower bound and the rounds-0..1 window of the circuit for the upper bound (records in `fold/`).

## Code distances

Columns: the paper's distance and how it was obtained ("exact": the paper says computed exactly or proven;
"upper": a heuristic bound; "conjectured"; "unknown": no method given); the DP width of the d_X / d_Z problems;
whether the larger table fits; the distances found (an interval [lower, upper] where no run finished); the time
of the DP front end (`dp=1`, "DP" where the DP gave the value) and of the search alone (`dp=0`), seconds.

### Vine codes, arXiv:2606.20263

<!-- TABLE:vine -->
| instance | n | k | paper: d (status) | width d_X / d_Z | fits | d_X found | d_Z found | front end s (X / Z) | search only s (X / Z) |
|---|---|---|---|---|---|---|---|---|---|
| vine_437_6_10 | 437 | 6 | 10 (conjectured) | 27 / 21 | yes | 10 | 10 | 0.3 / 0.4 | 0.2 / 0.2 |
| vine_538_6_10 | 538 | 6 | 10 (conjectured) | 28 / 32 | 64 GiB | 10 | 10 | 0.5 / 0.5 | 0.2 / 0.2 |
| vine_557_6_10 | 557 | 6 | 10 (conjectured) | 21 / 27 | yes | 10 | 10 | 0.5 / 0.4 | 0.2 / 0.2 |
| vine_435_6_10 | 435 | 6 | 10 (conjectured) | 27 / 21 | yes | 10 | 10 | 0.3 / 0.3 | 0.2 / 0.2 |
| vine_fig7_nSeWwSs_s5 | 62 | 6 | - (unknown) | 8 / 6 | yes | 3 | 4 | 0.1 / 0.1 | 0.1 / 0.1 |
| vine_fig7_nSeWwSs_s7 | 114 | 6 | - (unknown) | 12 / 10 | yes | 5 | 5 | 0.1 / 0.1 | 0.1 / 0.1 |
| vine_fig7_nSeWwSs_s11 | 266 | 6 | - (unknown) | 21 / 17 | yes | 7 | 8 | 0.2 / 0.2 | 0.1 / 0.1 |
| vine_fig7_nSeWWwSs_s10 | 57 | 9 | - (unknown) | 9 / 9 | yes | 3 | 3 | 0.1 / 0.1 | 0.1 / 0.1 |
| vine_fig7_nSeWWwSs_s18 | 173 | 9 | - (unknown) | 19 / 21 | yes | 5 | 5 | 0.2 / 0.2 | 0.1 / 0.1 |
| vine_fig7_nSeWWwSs_s26 | 353 | 9 | - (unknown) | 28 / 33 | 64 GiB | 7 | 7 | 0.3 / 0.3 | 0.1 / 0.2 |
| vine_fig11_nSENESs_d5 | 83 | 4 | - (unknown) | 6 / 10 | yes | 5 | 7 | 0.1 / 0.1 | 0.1 / 0.1 |
<!-- /TABLE:vine -->

### Tile codes, arXiv:2504.09171 and 2607.05897

`bp288_*`, `bp188_*`, `bp131_*`, `bp88_*` are the four families of 2607.05897 at the sizes it lists (it gives no
distance method); `tile_*` are the codes of 2504.09171.  All weight-6 [[288,8,12]] codes of 2504.09171's
Appendix B are one code up to relabelling (`papers/new/2504.09171.md`).

<!-- TABLE:tile -->
| instance | n | k | paper: d (status) | width d_X / d_Z | fits | d_X found | d_Z found | front end s (X / Z) | search only s (X / Z) |
|---|---|---|---|---|---|---|---|---|---|
| tile_288_8_12 | 288 | 8 | 12 (exact) | 25 / 25 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_14 | 288 | 8 | 14 (exact) | 25 / 27 | yes | 14 | 15 | 0.9 / 0.5 | 0.8 / 0.4 |
| tile_288_18_13 | 288 | 18 | 13 (exact) | 31 / 32 | 64 GiB | 13 | 13 | 0.2 / 0.2 | 0.2 / 0.2 |
| tile_512_18_19 | 512 | 18 | 19 (exact) | 45 / 46 | no | 19 | 19 | = search / = search | 25.6 / 11.8 |
| tile_512_18_23 | 512 | 18 | 23 (upper) | 42 / 48 | no | 21 | [22, 23] | = search / = search | 1739.8 / >1800 ([22, ?]) |
| tile_288_8_12_b1 | 288 | 8 | 12 (exact) | 25 / 26 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b2 | 288 | 8 | 12 (exact) | 25 / 26 | yes | 12 | 12 | 0.4 / 0.2 | 0.2 / 0.2 |
| tile_288_8_12_b3 | 288 | 8 | 12 (exact) | 24 / 25 | yes | 12 | 12 | 0.3 / 0.4 | 0.2 / 0.3 |
| tile_288_8_12_b4 | 288 | 8 | 12 (exact) | 24 / 26 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b5 | 288 | 8 | 12 (exact) | 26 / 25 | yes | 12 | 12 | 0.2 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b6 | 288 | 8 | 12 (exact) | 26 / 24 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b7 | 288 | 8 | 12 (exact) | 25 / 24 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b1s | 288 | 8 | 12 (exact) | 25 / 25 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b2s | 288 | 8 | 12 (exact) | 25 / 26 | yes | 12 | 12 | 0.3 / 0.2 | 0.2 / 0.2 |
| tile_288_8_12_b3s | 288 | 8 | 12 (exact) | 25 / 25 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b4s | 288 | 8 | 12 (exact) | 24 / 24 | yes | 12 | 12 | 0.2 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b5s | 288 | 8 | 12 (exact) | 26 / 25 | yes | 12 | 12 | 0.2 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b6s | 288 | 8 | 12 (exact) | 25 / 25 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_12_b7s | 288 | 8 | 12 (exact) | 24 / 25 | yes | 12 | 12 | 0.2 / 0.2 | 0.2 / 0.2 |
| tile_288_8_12_b8s | 288 | 8 | 12 (exact) | 25 / 24 | yes | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| tile_288_8_14_c1 | 288 | 8 | 14 (exact) | 26 / 25 | yes | 14 | 14 | 1.0 / 0.9 | 0.9 / 0.8 |
| tile_288_8_14_c3 | 288 | 8 | 14 (exact) | 25 / 28 | yes | 15 | 14 | 4.3 / 0.4 | 4.2 / 0.4 |
| tile_288_8_14_c4 | 288 | 8 | 14 (exact) | 23 / 25 | yes | 14 | 14 | 0.8 / 2.0 | 0.8 / 1.8 |
| tile_25_1_4_surface | 25 | 1 | 4 (exact) | 3 / 3 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| bp288_72_8_4 | 72 | 8 | 4 (unknown) | 9 / 9 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.1 |
| bp288_128_8_6 | 128 | 8 | 6 (unknown) | 15 / 15 | yes | 6 | 6 | 0.2 / 0.2 | 0.1 / 0.1 |
| bp288_200_8_9 | 200 | 8 | 9 (unknown) | 19 / 20 | yes | 9 | 9 | 0.2 / 0.2 | 0.2 / 0.2 |
| bp288_288_8_12 | 288 | 8 | 12 (unknown) | 25 / 26 | yes | 12 | 12 | 0.3 / 0.2 | 0.2 / 0.2 |
| bp288_338_8_13 | 338 | 8 | 13 (unknown) | 28 / 28 | yes | 13 | 13 | 0.3 / 0.2 | 0.2 / 0.2 |
| bp288_392_8_15 | 392 | 8 | 15 (unknown) | 30 / 31 | yes | 15 | 15 | 0.4 / 0.4 | 0.3 / 0.3 |
| bp188_105_8_6 | 105 | 8 | 6 (unknown) | 15 / 12 | yes | 6 | 6 | 0.1 / 0.2 | 0.2 / 0.1 |
| bp188_137_8_7 | 137 | 8 | 7 (unknown) | 18 / 15 | yes | 7 | 7 | 0.2 / 0.2 | 0.1 / 0.1 |
| bp188_173_8_8 | 173 | 8 | 8 (unknown) | 19 / 19 | yes | 8 | 9 | 0.2 / 0.2 | 0.1 / 0.2 |
| bp188_188_8_9 | 188 | 8 | 9 (unknown) | 21 / 19 | yes | 9 | 9 | 0.2 / 0.2 | 0.2 / 0.1 |
| bp188_230_8_10 | 230 | 8 | 10 (unknown) | 21 / 23 | yes | 10 | 10 | 0.2 / 0.2 | 0.2 / 0.2 |
| bp188_276_8_11 | 276 | 8 | 11 (unknown) | 26 / 25 | yes | 11 | 12 | 0.2 / 0.3 | 0.2 / 0.2 |
| bp131_131_7_7 | 131 | 7 | 7 (unknown) | 18 / 13 | yes | 7 | 7 | 0.2 / 0.2 | 0.2 / 0.1 |
| bp131_166_7_8 | 166 | 7 | 8 (unknown) | 21 / 19 | yes | 8 | 8 | 0.2 / 0.2 | 0.1 / 0.1 |
| bp131_205_7_10 | 205 | 7 | 10 (unknown) | 20 / 22 | yes | 10 | 10 | 0.2 / 0.2 | 0.1 / 0.1 |
| bp131_248_7_11 | 248 | 7 | 11 (unknown) | 25 / 20 | yes | 11 | 12 | 0.2 / 0.3 | 0.2 / 0.2 |
| bp131_267_7_12 | 267 | 7 | 12 (unknown) | 28 / 21 | yes | 12 | 12 | 0.2 / 0.3 | 0.2 / 0.2 |
| bp88_88_6_6 | 88 | 6 | 6 (unknown) | 11 / 11 | yes | 6 | 6 | 0.2 / 0.1 | 0.1 / 0.2 |
| bp88_150_6_8 | 150 | 6 | 8 (unknown) | 17 / 14 | yes | 8 | 9 | 0.2 / 0.2 | 0.1 / 0.2 |
| bp88_165_6_9 | 165 | 6 | 9 (unknown) | 15 / 15 | yes | 9 | 9 | 0.2 / 0.2 | 0.2 / 0.2 |
| bp88_228_6_11 | 228 | 6 | 11 (unknown) | 22 / 20 | yes | 11 | 12 | 0.2 / 0.2 | 0.1 / 0.2 |
| bp88_247_6_12 | 247 | 6 | 12 (unknown) | 18 / 20 | yes | 12 | 12 | 0.2 / 0.2 | 0.2 / 0.2 |
<!-- /TABLE:tile -->

### Nearest-neighbour planar-grid codes, arXiv:2606.19482 (v2)

`dtc_w<w>_*` are the square-grid families of the words of weight w; `[[259,2,4]]`, `[[269,4,5]]`,
`[[365,10,4]]`, `[[537,14,12]]` are Table III, whose d_X the paper gives only as QDistRnd upper bounds
(37, 28, 31, 35: the integer program did not terminate above 20).  `dtc_hex_*` are the hexagonal-grid codes:
the paper gives no sizes for them, and our reconstruction does not reproduce its distances at three of the four
sizes (see Caveats), so they are not counted as checks of the paper.

<!-- TABLE:nngrid -->
| instance | n | k | paper: d (status) | width d_X / d_Z | fits | d_X found | d_Z found | front end s (X / Z) | search only s (X / Z) |
|---|---|---|---|---|---|---|---|---|---|
| dtc_w5_18_2_2 | 18 | 2 | dx 3, dz 2 (unknown) | 4 / 2 | yes | 3 | 2 | 0.1 / 0.2 | 0.2 / 0.2 |
| dtc_w5_259_2_4 | 259 | 2 | dx <= 37 (upper, QDistRnd), dz 4 (exact, IP) | 5 / 3 | yes | 36 | 4 | 1.2 DP / 0.2 | 360.0 / 0.2 |
| dtc_w7_24_4_3 | 24 | 4 | 3 (unknown) | 4 / 3 | yes | 3 | 3 | 0.1 / 0.2 | 0.2 / 0.2 |
| dtc_w7_40_4_4 | 40 | 4 | 4 (unknown) | 6 / 5 | yes | 4 | 4 | 0.1 / 0.2 | 0.1 / 0.2 |
| dtc_w7_60_4_5 | 60 | 4 | 5 (unknown) | 8 / 6 | yes | 5 | 5 | 0.1 / 0.1 | 0.2 / 0.1 |
| dtc_w7_84_4_6 | 84 | 4 | 6 (unknown) | 10 / 7 | yes | 6 | 6 | 0.2 / 0.2 | 0.1 / 0.2 |
| dtc_w7_112_4_7 | 112 | 4 | 7 (unknown) | 12 / 9 | yes | 7 | 7 | 0.2 / 0.2 | 0.2 / 0.2 |
| dtc_w7_144_4_8 | 144 | 4 | 8 (unknown) | 14 / 10 | yes | 8 | 8 | 0.2 / 0.2 | 0.2 / 0.1 |
| dtc_w7_180_4_9 | 180 | 4 | 9 (unknown) | 15 / 11 | yes | 9 | 9 | 0.2 / 0.2 | 0.2 / 0.2 |
| dtc_w7_269_4_5 | 269 | 4 | dx <= 28 (upper, QDistRnd), dz 5 (exact, IP) | 10 / 6 | yes | 28 | 5 | 1.3 DP / 0.2 | 69.1 / 0.2 |
| dtc_w9_52_10_3 | 52 | 10 | 3 (unknown) | 8 / 6 | yes | 3 | 3 | 0.2 / 0.2 | 0.2 / 0.1 |
| dtc_w9_76_10_4 | 76 | 10 | 4 (unknown) | 12 / 8 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| dtc_w9_115_10_5 | 115 | 10 | 5 (unknown) | 16 / 11 | yes | 5 | 5 | 0.2 / 0.2 | 0.2 / 0.2 |
| dtc_w9_162_10_6 | 162 | 10 | 6 (unknown) | 20 / 15 | yes | 6 | 6 | 0.1 / 0.2 | 0.1 / 0.2 |
| dtc_w9_351_10_9 | 351 | 10 | 9 (unknown) | 32 / 24 | 64 GiB | 9 | 9 | 0.3 / 0.4 | 0.2 / 0.2 |
| dtc_w9_365_10_4 | 365 | 10 | dx <= 31 (upper, QDistRnd), dz 4 (exact, IP) | 18 / 8 | yes | 31 | 4 | 13.0 DP / 0.3 | >1800 ([26, ?]) / 0.2 |
| dtc_w11_74_14_5 | 74 | 14 | 5 (unknown) | 11 / 10 | yes | 5 | 5 | 0.1 / 0.1 | 0.1 / 0.1 |
| dtc_w11_104_14_6 | 104 | 14 | 6 (unknown) | 16 / 12 | yes | 6 | 6 | 0.2 / 0.2 | 0.1 / 0.1 |
| dtc_w11_182_14_10 | 182 | 14 | 10 (unknown) | 21 / 22 | yes | 10 | 10 | 0.3 / 0.2 | 0.2 / 0.2 |
| dtc_w11_241_14_12 | 241 | 14 | 12 (unknown) | 26 / 25 | yes | 12 | 12 | 0.3 / 0.7 | 0.2 / 0.6 |
| dtc_w11_323_14_15 | 323 | 14 | 15 (unknown) | 31 / 31 | 64 GiB | 15 | 15 | 1.0 / 2.5 | 0.9 / 2.4 |
| dtc_w11_537_14_12 | 537 | 14 | dx <= 35 (upper, QDistRnd), dz 12 (exact, IP) | 39 / 24 | no | [19, 30] | 12 | = search / 1.6 | >1800 ([19, ?]) / 1.4 |
| dtc_hex_52_10_3 | 52 | 10 | 3 (unknown) | 7 / 8 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| dtc_hex_74_10_4 | 76 | 10 | 4 (unknown) | 9 / 12 | yes | 4 | 5 | 0.2 / 0.2 | 0.2 / 0.2 |
| dtc_hex_104_10_5 | 104 | 10 | 5 (unknown) | 10 / 16 | yes | 5 | 6 | 0.2 / 0.2 | 0.1 / 0.2 |
| dtc_hex_104_10_5_m1n7 | 104 | 10 | 5 (unknown) | 4 / 14 | yes | 2 | 12 | 0.2 / 0.2 | 0.1 / 0.2 |
| dtc_hex_199_10_7_m6n7 | 199 | 10 | 7 (unknown) | 12 / 22 | yes | 6 | 12 | 0.2 / 0.7 | 0.2 / 0.6 |
| dtc_hex_199_10_7_m5n8 | 199 | 10 | 7 (unknown) | 10 / 20 | yes | 5 | 13 | 0.2 / 1.2 | 0.2 / 1.1 |
| rsc_9_1_3 | 9 | 1 | 3 (exact) | 1 / 1 | yes | 3 | 3 | 0.2 / 0.2 | 0.1 / 0.2 |
| rsc_25_1_5 | 25 | 1 | 5 (exact) | 2 / 2 | yes | 5 | 5 | 0.2 / 0.2 | 0.2 / 0.1 |
| rsc_49_1_7 | 49 | 1 | 7 (exact) | 4 / 4 | yes | 7 | 7 | 0.2 / 0.2 | 0.2 / 0.2 |
<!-- /TABLE:nngrid -->

### BB surface codes with boundaries, arXiv:2606.08771

<!-- TABLE:bbsurface -->
| row | paper: d (status) | size L1 x L2 | n | k | width d_X / d_Z | fits | d_X found | d_Z found | d = min | equals paper | front end s (X / Z) | search only s (X / Z) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bbs_42_6_4 | 4 (upper) | 7 x 6 (default) | 42 | 6 | 7 / 5 | yes | 4 | 4 | 4 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_42_6_4 | 4 (upper) | 10 x 4 | 42 | 6 | 8 / 2 | yes | 6 | 2 | 2 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_72_6_5 | 5 (upper) | 12 x 3 (default) | 72 | 6 | 12 / 8 | yes | 7 | 4 | 4 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_6_5 | 5 (upper) | 6 x 6 | 72 | 6 | 3 / 10 | yes | 2 | 8 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.2 |
| bbs_72_6_5 | 5 (upper) | 9 x 4 | 72 | 6 | 8 / 11 | yes | 5 | 5 | 5 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_6_5 | 5 (upper) | 18 x 2 | 72 | 6 | 8 / 4 | yes | 13 | 2 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_6_6 | 6 (upper) | 6 x 6 (default) | 72 | 6 | 9 / 9 | yes | 6 | 6 | 6 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_6_6 | 6 (upper) | 3 x 12 | 72 | 6 | 1 / 8 | yes | 2 | 12 | 2 | lower | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_72_6_6 | 6 (upper) | 4 x 9 | 72 | 6 | 5 / 11 | yes | 3 | 8 | 3 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_6_6 | 6 (upper) | 9 x 4 | 72 | 6 | 10 / 5 | yes | 10 | 3 | 3 | lower | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_72_6_6 | 6 (upper) | 12 x 3 | 72 | 6 | 7 / 2 | yes | 14 | 2 | 2 | lower | 0.1 / 0.2 | 0.1 / 0.2 |
| bbs_112_6_7 | 7 (upper) | 8 x 7 (default) | 112 | 6 | 14 / 13 | yes | 9 | 6 | 6 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_112_6_7 | 7 (upper) | 4 x 14 | 112 | 6 | 4 / 11 | yes | 3 | 14 | 3 | lower | 0.1 / 0.1 | 0.1 / 0.2 |
| bbs_112_6_7 | 7 (upper) | 7 x 8 | 112 | 6 | 12 / 15 | yes | 7 | 8 | 7 | yes | 0.2 / 0.1 | 0.2 / 0.2 |
| bbs_112_6_7 | 7 (upper) | 14 x 4 | 112 | 6 | 11 / 5 | yes | 17 | 3 | 3 | lower | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_128_6_8 | 8 (upper) | 8 x 8 (default) | 128 | 6 | 14 / 15 | yes | 9 | 8 | 8 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_128_6_8 | 8 (upper) | 4 x 16 | 128 | 6 | 5 / 11 | yes | 3 | 16 | 3 | lower | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_128_6_8 | 8 (upper) | 16 x 4 | 128 | 6 | 11 / 5 | yes | 19 | 3 | 3 | lower | 0.3 / 0.1 | 0.3 / 0.1 |
| bbs_160_6_9 | 9 (upper) | 8 x 10 (default) | 160 | 6 | 14 / 19 | yes | 9 | 10 | 9 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_160_6_9 | 9 (upper) | 4 x 20 | 160 | 6 | 5 / 11 | yes | 3 | 20 | 3 | lower | 0.1 / 0.4 | 0.1 / 0.3 |
| bbs_160_6_9 | 9 (upper) | 5 x 16 | 160 | 6 | 7 / 13 | yes | 4 | 16 | 4 | lower | 0.1 / 0.3 | 0.1 / 0.3 |
| bbs_160_6_9 | 9 (upper) | 10 x 8 | 160 | 6 | 19 / 16 | yes | 11 | 8 | 8 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_160_6_9 | 9 (upper) | 16 x 5 | 160 | 6 | 14 / 6 | yes | 19 | 4 | 4 | lower | 0.9 / 0.1 | 0.8 / 0.1 |
| bbs_160_6_9 | 9 (upper) | 20 x 4 | 160 | 6 | 11 / 5 | yes | 25 | 3 | 3 | lower | 1.2 DP / 0.1 | 6.5 / 0.2 |
| bbs_180_6_10 | 10 (upper) | 9 x 10 (default) | 180 | 6 | 16 / 21 | yes | 10 | 10 | 10 | yes | 0.2 / 0.2 | 0.1 / 0.1 |
| bbs_180_6_10 | 10 (upper) | 3 x 30 | 180 | 6 | 1 / 9 | yes | 2 | 30 | 2 | lower | 0.1 / 1.1 | 0.1 / 1.1 |
| bbs_180_6_10 | 10 (upper) | 5 x 18 | 180 | 6 | 7 / 13 | yes | 4 | 18 | 4 | lower | 0.2 / 0.5 | 0.1 / 0.6 |
| bbs_180_6_10 | 10 (upper) | 6 x 15 | 180 | 6 | 9 / 16 | yes | 6 | 14 | 6 | lower | 0.2 / 0.2 | 0.1 / 0.1 |
| bbs_180_6_10 | 10 (upper) | 10 x 9 | 180 | 6 | 18 / 19 | yes | 11 | 8 | 8 | lower | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_180_6_10 | 10 (upper) | 15 x 6 | 180 | 6 | 16 / 11 | yes | 18 | 6 | 6 | lower | 0.7 / 0.1 | 0.7 / 0.1 |
| bbs_180_6_10 | 10 (upper) | 18 x 5 | 180 | 6 | 14 / 7 | yes | 22 | 4 | 4 | lower | 1.2 DP / 0.1 | 5.1 / 0.2 |
| bbs_180_6_10 | 10 (upper) | 30 x 3 | 180 | 6 | 7 / 2 | yes | 38 | 2 | 2 | lower | 1.2 DP / 0.2 | 304.3 / 0.1 |
| bbs_216_6_11 | 11 (upper) | 12 x 19 (default) | 216 | 6 | 17 / 21 | yes | 11 | 11 | 11 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_216_6_11 | 11 (upper) | 8 x 28 | 216 | 6 | 11 / 18 | yes | 6 | 17 | 6 | lower | 0.2 / 1.3 DP | 0.1 / 2.8 |
| bbs_216_6_11 | 11 (upper) | 18 x 13 | 216 | 6 | 21 / 13 | yes | 17 | 6 | 6 | lower | 2.3 DP / 0.2 | 2.0 / 0.1 |
| bbs_216_6_11 | 11 (upper) | 24 x 10 | 216 | 6 | 17 / 11 | yes | 25 | 4 | 4 | lower | 1.3 DP / 0.1 | 91.0 / 0.1 |
| bbs_247_6_12 | 12 (upper) | 9 x 13 (default) | 247 | 6 | 21 / 23 | yes | 12 | 12 | 12 | yes | 0.3 / 0.2 | 0.2 / 0.2 |
| bbs_247_6_12 | 12 (upper) | 6 x 19 | 247 | 6 | 13 / 19 | yes | 7 | 18 | 7 | lower | 0.2 / 4.8 DP | 0.1 / 5.3 |
| bbs_275_6_13 | 13 (upper) | 14 x 10 (default) | 275 | 6 | 21 / 21 | yes | 13 | 13 | 13 | yes | 0.3 / 0.4 | 0.2 / 0.3 |
| bbs_275_6_13 | 13 (upper) | 9 x 15 | 275 | 6 | 13 / 19 | yes | 6 | 21 | 6 | lower | 0.3 / 12.2 DP | 0.2 / 29.9 |
| bbs_52_7_4 | 4 (upper) | 4 x 11 (default) | 52 | 7 | 8 / 7 | yes | 4 | 4 | 4 | yes | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_81_7_5 | 5 (upper) | 9 x 9 (default) | 81 | 7 | 12 / 10 | yes | 5 | 5 | 5 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_96_7_6 | 6 (upper) | 8 x 6 (default) | 96 | 7 | 14 / 10 | yes | 8 | 4 | 4 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_96_7_6 | 6 (upper) | 3 x 16 | 96 | 7 | 1 / 8 | yes | 2 | 21 | 2 | lower | 0.1 / 0.2 | 0.1 / 0.2 |
| bbs_96_7_6 | 6 (upper) | 4 x 12 | 96 | 7 | 5 / 11 | yes | 3 | 11 | 3 | lower | 0.1 / 0.1 | 0.2 / 0.2 |
| bbs_96_7_6 | 6 (upper) | 6 x 8 | 96 | 7 | 10 / 16 | yes | 6 | 6 | 6 | yes | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_96_7_6 | 6 (upper) | 12 x 4 | 96 | 7 | 11 / 7 | yes | 14 | 2 | 2 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_126_7_7 | 7 (upper) | 7 x 9 (default) | 126 | 7 | 12 / 15 | yes | 7 | 7 | 7 | yes | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_126_7_7 | 7 (upper) | 3 x 21 | 126 | 7 | 1 / 8 | yes | 2 | 31 | 2 | lower | 0.1 / 1.2 DP | 0.1 / 13.7 |
| bbs_126_7_7 | 7 (upper) | 9 x 7 | 126 | 7 | 17 / 14 | yes | 10 | 5 | 5 | lower | 0.2 / 0.1 | 0.2 / 0.2 |
| bbs_156_7_8 | 8 (upper) | 13 x 12 (default) | 156 | 7 | 16 / 14 | yes | 8 | 8 | 8 | yes | 0.1 / 0.1 | 0.2 / 0.1 |
| bbs_156_7_8 | 8 (upper) | 6 x 26 | 156 | 7 | 6 / 13 | yes | 2 | 26 | 2 | lower | 0.2 / 1.2 DP | 0.1 / 9.7 |
| bbs_156_7_8 | 8 (upper) | 12 x 13 | 156 | 7 | 15 / 16 | yes | 7 | 9 | 7 | lower | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_156_7_8 | 8 (upper) | 26 x 6 | 156 | 7 | 12 / 5 | yes | 18 | 3 | 3 | lower | 0.3 / 0.1 | 0.3 / 0.1 |
| bbs_166_7_9 | 9 (upper) | 12 x 8 (default) | 166 | 7 | 17 / 16 | yes | 9 | 9 | 9 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_166_7_9 | 9 (upper) | 6 x 17 | 166 | 7 | 6 / 13 | yes | 3 | 23 | 3 | lower | 0.2 / 1.2 DP | 0.1 / 16.5 |
| bbs_166_7_9 | 9 (upper) | 16 x 6 | 166 | 7 | 18 / 10 | yes | 14 | 6 | 6 | lower | 0.3 / 0.1 | 0.3 / 0.1 |
| bbs_201_7_10 | 10 (upper) | 14 x 13 (default) | 201 | 7 | 24 / 17 | yes | 10 | 10 | 10 | yes | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_229_7_11 | 11 (upper) | 17 x 14 (default) | 229 | 7 | 20 / 18 | yes | 11 | 11 | 11 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_229_7_11 | 11 (upper) | 9 x 26 | 229 | 7 | 9 / 17 | yes | 4 | 23 | 4 | lower | 0.2 / 1.3 DP | 0.1 / 59.8 |
| bbs_257_7_12 | 12 (upper) | 13 x 9 (default) | 257 | 7 | 19 / 26 | yes | 12 | 12 | 12 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_257_7_12 | 12 (upper) | 4 x 28 | 257 | 7 | 4 / 11 | yes | 2 | 54 | 2 | lower | 0.2 / 1.2 DP | 0.1 / >1800 ([41, ?]) |
| bbs_257_7_12 | 12 (upper) | 9 x 13 | 257 | 7 | 13 / 20 | yes | 6 | 18 | 6 | lower | 0.2 / 3.7 DP | 0.2 / 4.4 |
| bbs_257_7_12 | 12 (upper) | 28 x 4 | 257 | 7 | 18 / 11 | yes | 28 | 4 | 4 | lower | 1.4 DP / 0.2 | >1800 ([27, ?]) / 0.2 |
| bbs_294_7_13 | 13 (upper) | 19 x 16 (default) | 294 | 7 | 24 / 21 | yes | 13 | 13 | 13 | yes | 0.3 / 0.3 | 0.3 / 0.3 |
| bbs_294_7_13 | 13 (upper) | 12 x 25 | 294 | 7 | 13 / 21 | yes | 6 | 22 | 6 | lower | 0.2 / 13.1 DP | 0.1 / 137.1 |
| bbs_294_7_13 | 13 (upper) | 28 x 11 | 294 | 7 | 21 / 14 | yes | 21 | 7 | 7 | lower | 14.0 DP / 0.2 | 127.2 / 0.1 |
| bbs_50_8_4 | 4 (upper) | 5 x 10 (default) | 50 | 8 | 6 / 5 | yes | 4 | 4 | 4 | yes | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_50_8_4 | 4 (upper) | 7 x 7 | 50 | 8 | 10 / 3 | yes | 6 | 2 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_8_5 | 5 (upper) | 6 x 12 (default) | 72 | 8 | 9 / 8 | yes | 6 | 5 | 5 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_8_5 | 5 (upper) | 3 x 24 | 72 | 8 | 1 / 8 | yes | 2 | 12 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.2 |
| bbs_72_8_5 | 5 (upper) | 4 x 18 | 72 | 8 | 4 / 12 | yes | 3 | 8 | 3 | lower | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_72_8_5 | 5 (upper) | 8 x 9 | 72 | 8 | 13 / 4 | yes | 8 | 3 | 3 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_72_8_5 | 5 (upper) | 9 x 8 | 72 | 8 | 12 / 4 | yes | 8 | 3 | 3 | lower | 0.1 / 0.1 | 0.1 / 0.2 |
| bbs_78_8_6 | 6 (upper) | 6 x 13 (default) | 78 | 8 | 9 / 10 | yes | 6 | 6 | 6 | yes | 0.1 / 0.1 | 0.2 / 0.1 |
| bbs_78_8_6 | 6 (upper) | 3 x 26 | 78 | 8 | 1 / 9 | yes | 2 | 12 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_78_8_6 | 6 (upper) | 7 x 11 | 78 | 8 | 11 / 8 | yes | 6 | 4 | 4 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_78_8_6 | 6 (upper) | 11 x 7 | 78 | 8 | 11 / 3 | yes | 10 | 2 | 2 | lower | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_137_8_7 | 7 (upper) | 11 x 7 (default) | 137 | 8 | 15 / 16 | yes | 7 | 7 | 7 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_137_8_7 | 7 (upper) | 7 x 11 | 137 | 8 | 7 / 15 | yes | 4 | 15 | 4 | lower | 0.1 / 0.3 | 0.2 / 0.2 |
| bbs_137_8_7 | 7 (upper) | 20 x 4 | 137 | 8 | 15 / 5 | yes | 18 | 3 | 3 | lower | 0.5 / 0.1 | 0.5 / 0.1 |
| bbs_144_8_8 | 8 (upper) | 9 x 16 (default) | 144 | 8 | 16 / 15 | yes | 8 | 8 | 8 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_144_8_8 | 8 (upper) | 6 x 24 | 144 | 8 | 9 / 18 | yes | 6 | 12 | 6 | lower | 0.1 / 0.2 | 0.2 / 0.1 |
| bbs_144_8_8 | 8 (upper) | 8 x 18 | 144 | 8 | 13 / 18 | yes | 8 | 8 | 8 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_144_8_8 | 8 (upper) | 11 x 13 | 144 | 8 | 20 / 14 | yes | 10 | 6 | 6 | lower | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_144_8_8 | 8 (upper) | 12 x 12 | 144 | 8 | 22 / 9 | yes | 12 | 5 | 5 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_144_8_8 | 8 (upper) | 13 x 11 | 144 | 8 | 19 / 7 | yes | 12 | 4 | 4 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_144_8_8 | 8 (upper) | 16 x 9 | 144 | 8 | 15 / 7 | yes | 16 | 3 | 3 | lower | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_144_8_8 | 8 (upper) | 18 x 8 | 144 | 8 | 14 / 3 | yes | 18 | 3 | 3 | lower | 0.4 / 0.1 | 0.3 / 0.1 |
| bbs_184_8_9 | 9 (upper) | 11 x 8 (default) | 184 | 8 | 23 / 17 | yes | 9 | 9 | 9 | yes | 0.2 / 0.2 | 0.1 / 0.1 |
| bbs_224_8_10 | 10 (upper) | 14 x 17 (default) | 224 | 8 | 19 / 21 | yes | 10 | 10 | 10 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_224_8_10 | 10 (upper) | 8 x 29 | 224 | 8 | 9 / 17 | yes | 4 | 23 | 4 | lower | 0.2 / 1.4 DP | 0.1 / 47.3 |
| bbs_224_8_10 | 10 (upper) | 16 x 15 | 224 | 8 | 22 / 18 | yes | 13 | 8 | 8 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_224_8_10 | 10 (upper) | 28 x 9 | 224 | 8 | 17 / 9 | yes | 26 | 3 | 3 | lower | 1.4 DP / 0.2 | 463.4 / 0.1 |
| bbs_271_8_11 | 11 (upper) | 15 x 19 (default) | 271 | 8 | 21 / 24 | yes | 11 | 11 | 11 | yes | 0.2 / 0.2 | 0.1 / 0.1 |
| bbs_271_8_11 | 11 (upper) | 27 x 11 | 271 | 8 | 20 / 12 | yes | 24 | 4 | 4 | lower | 12.7 DP / 0.2 | 492.5 / 0.1 |
| bbs_288_8_12 | 12 (upper) | 12 x 12 (default) | 288 | 8 | 24 / 27 | yes | 12 | 12 | 12 | yes | 0.3 / 0.2 | 0.2 / 0.2 |
| bbs_288_8_12 | 12 (upper) | 6 x 24 | 288 | 8 | 10 / 18 | yes | 4 | 26 | 4 | lower | 0.2 / 11.8 DP | 0.2 / 856.6 |
| bbs_288_8_12 | 12 (upper) | 8 x 18 | 288 | 8 | 14 / 23 | yes | 6 | 19 | 6 | lower | 0.3 / 15.7 DP | 0.2 / 14.4 |
| bbs_288_8_12 | 12 (upper) | 9 x 16 | 288 | 8 | 17 / 25 | yes | 7 | 17 | 7 | lower | 0.2 / 3.0 | 0.1 / 3.2 |
| bbs_288_8_12 | 12 (upper) | 16 x 9 | 288 | 8 | 31 / 23 | yes | 18 | 7 | 7 | lower | 7.8 DP / 0.2 | 2.7 / 0.1 |
| bbs_288_8_12 | 12 (upper) | 18 x 8 | 288 | 8 | 28 / 20 | yes | 21 | 6 | 6 | lower | 4.7 DP / 0.3 | 18.9 / 0.1 |
| bbs_288_8_12 | 12 (upper) | 24 x 6 | 288 | 8 | 20 / 14 | yes | 28 | 4 | 4 | lower | 11.8 DP / 0.2 | >1800 ([27, ?]) / 0.2 |
| bbs_56_9_4 | 4 (upper) | 7 x 8 (default) | 56 | 9 | 7 / 7 | yes | 4 | 4 | 4 | yes | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_56_9_4 | 4 (upper) | 8 x 7 | 56 | 9 | 8 / 6 | yes | 4 | 3 | 3 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_98_9_5 | 5 (upper) | 9 x 12 (default) | 98 | 9 | 12 / 12 | yes | 5 | 5 | 5 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_98_9_5 | 5 (upper) | 12 x 9 | 98 | 9 | 17 / 7 | yes | 8 | 3 | 3 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_110_9_6 | 6 (upper) | 10 x 5 (default) | 110 | 9 | 14 / 14 | yes | 6 | 6 | 6 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_110_9_6 | 6 (upper) | 22 x 2 | 110 | 9 | 13 / 2 | yes | 20 | 2 | 2 | lower | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_142_9_7 | 7 (upper) | 11 x 14 (default) | 142 | 9 | 17 / 18 | yes | 7 | 7 | 7 | yes | 0.1 / 0.1 | 0.1 / 0.2 |
| bbs_142_9_7 | 7 (upper) | 14 x 11 | 142 | 9 | 22 / 11 | yes | 11 | 4 | 4 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_178_9_8 | 8 (upper) | 12 x 16 (default) | 178 | 9 | 19 / 18 | yes | 8 | 8 | 8 | yes | 0.1 / 0.2 | 0.2 / 0.2 |
| bbs_178_9_8 | 8 (upper) | 16 x 12 | 178 | 9 | 24 / 13 | yes | 13 | 5 | 5 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_206_9_9 | 9 (upper) | 16 x 12 (default) | 206 | 9 | 19 / 19 | yes | 9 | 9 | 9 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_206_9_9 | 9 (upper) | 12 x 16 | 206 | 9 | 18 / 25 | yes | 6 | 14 | 6 | lower | 0.2 / 0.3 | 0.2 / 0.2 |
| bbs_236_9_10 | 10 (upper) | 14 x 18 (default) | 236 | 9 | 23 / 24 | yes | 11 | 10 | 10 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_236_9_10 | 10 (upper) | 12 x 21 | 236 | 9 | 19 / 28 | yes | 8 | 13 | 8 | lower | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_236_9_10 | 10 (upper) | 18 x 14 | 236 | 9 | 30 / 18 | yes | 16 | 7 | 7 | lower | 0.3 / 0.1 | 0.3 / 0.1 |
| bbs_236_9_10 | 10 (upper) | 21 x 12 | 236 | 9 | 23 / 14 | yes | 20 | 5 | 5 | lower | 5.8 DP / 0.1 | 10.7 / 0.1 |
| bbs_250_9_11 | 11 (upper) | 14 x 19 (default) | 250 | 9 | 23 / 32 | 64 GiB | 11 | 11 | 11 | yes | 0.3 / 0.2 | 0.1 / 0.2 |
| bbs_250_9_11 | 11 (upper) | 19 x 14 | 250 | 9 | 30 / 18 | yes | 17 | 7 | 7 | lower | 0.5 / 0.2 | 0.4 / 0.1 |
| bbs_283_9_12 | 12 (upper) | 15 x 20 (default) | 283 | 9 | 25 / 35 | no | 12 | 12 | 12 | yes | 0.2 / = search | 0.2 / 0.2 |
| bbs_283_9_12 | 12 (upper) | 20 x 15 | 283 | 9 | 30 / 21 | yes | 18 | 7 | 7 | lower | 1.1 / 0.3 | 1.0 / 0.1 |
| bbs_65_10_4 | 4 (upper) | 5 x 6 (default) | 65 | 10 | 8 / 8 | yes | 4 | 4 | 4 | yes | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_102_10_5 | 5 (upper) | 6 x 8 (default) | 102 | 10 | 12 / 14 | yes | 6 | 5 | 5 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_114_10_6 | 6 (upper) | 6 x 9 (default) | 114 | 10 | 13 / 15 | yes | 6 | 6 | 6 | yes | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_147_10_7 | 7 (upper) | 7 x 10 (default) | 147 | 10 | 15 / 18 | yes | 7 | 7 | 7 | yes | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_147_10_7 | 7 (upper) | 3 x 24 | 147 | 10 | 1 / 13 | yes | 2 | 27 | 2 | lower | 0.1 / 1.2 DP | 0.1 / 1.8 |
| bbs_184_10_8 | 8 (upper) | 8 x 11 (default) | 184 | 10 | 19 / 21 | yes | 8 | 8 | 8 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_198_10_9 | 9 (upper) | 12 x 17 (default) | 198 | 10 | 27 / 22 | yes | 9 | 9 | 9 | yes | 0.2 / 0.1 | 0.2 / 0.2 |
| bbs_227_10_10 | 10 (upper) | 18 x 13 (default) | 227 | 10 | 30 / 19 | yes | 10 | 10 | 10 | yes | 0.2 / 0.1 | 0.2 / 0.2 |
| bbs_277_10_11 | 11 (upper) | 18 x 15 (default) | 277 | 10 | 29 / 23 | yes | 11 | 12 | 11 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_292_10_12 | 12 (upper) | 20 x 15 (default) | 292 | 10 | 31 / 23 | yes | 12 | 12 | 12 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_292_10_12 | 12 (upper) | 27 x 11 | 292 | 10 | 26 / 16 | yes | 19 | 7 | 7 | lower | 7.2 / 0.2 | 7.1 / 0.1 |
| bbs_75_11_4 | 4 (upper) | 6 x 12 (default) | 75 | 11 | 9 / 9 | yes | 4 | 4 | 4 | yes | 0.2 / 0.1 | 0.1 / 0.2 |
| bbs_115_11_5 | 5 (upper) | 8 x 14 (default) | 115 | 11 | 13 / 12 | yes | 5 | 5 | 5 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_115_11_5 | 5 (upper) | 4 x 26 | 115 | 11 | 2 / 15 | yes | 2 | 13 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_115_11_5 | 5 (upper) | 13 x 9 | 115 | 11 | 17 / 5 | yes | 10 | 2 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_127_11_6 | 6 (upper) | 11 x 5 (default) | 127 | 11 | 16 / 17 | yes | 6 | 6 | 6 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_127_11_6 | 6 (upper) | 5 x 11 | 127 | 11 | 1 / 12 | yes | 2 | 19 | 2 | lower | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_176_11_7 | 7 (upper) | 13 x 6 (default) | 176 | 11 | 21 / 20 | yes | 7 | 7 | 7 | yes | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_176_11_7 | 7 (upper) | 6 x 13 | 176 | 11 | 4 / 16 | yes | 2 | 24 | 2 | lower | 0.1 / 1.3 DP | 0.1 / 4.2 |
| bbs_176_11_7 | 7 (upper) | 19 x 4 | 176 | 11 | 24 / 12 | yes | 11 | 4 | 4 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_210_11_8 | 8 (upper) | 14 x 15 (default) | 210 | 11 | 30 / 19 | yes | 8 | 8 | 8 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_210_11_8 | 8 (upper) | 7 x 30 | 210 | 11 | 11 / 21 | yes | 3 | 20 | 3 | lower | 0.2 / 3.7 DP | 0.1 / 1.8 |
| bbs_210_11_8 | 8 (upper) | 10 x 21 | 210 | 11 | 19 / 29 | yes | 5 | 12 | 5 | lower | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_210_11_8 | 8 (upper) | 15 x 14 | 210 | 11 | 29 / 18 | yes | 10 | 7 | 7 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_210_11_8 | 8 (upper) | 21 x 10 | 210 | 11 | 22 / 11 | yes | 19 | 4 | 4 | lower | 3.7 DP / 0.2 | 2.4 / 0.1 |
| bbs_210_11_8 | 8 (upper) | 30 x 7 | 210 | 11 | 17 / 3 | yes | 30 | 2 | 2 | lower | 1.3 DP / 0.2 | 119.9 / 0.1 |
| bbs_234_11_9 | 9 (upper) | 19 x 12 (default) | 234 | 11 | 28 / 23 | yes | 9 | 9 | 9 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_285_11_10 | 10 (upper) | 15 x 19 (default) | 285 | 11 | 37 / 26 | no | 10 | 10 | 10 | yes | = search / 0.2 | 0.2 / 0.2 |
| bbs_285_11_10 | 10 (upper) | 19 x 15 | 285 | 11 | 30 / 19 | yes | 14 | 8 | 8 | lower | 0.2 / 0.3 | 0.2 / 0.1 |
| bbs_77_12_4 | 4 (upper) | 7 x 12 (default) | 77 | 12 | 5 / 6 | yes | 4 | 4 | 4 | yes | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_77_12_4 | 4 (upper) | 11 x 8 | 77 | 12 | 8 / 2 | yes | 5 | 2 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_120_12_5 | 5 (upper) | 6 x 10 (default) | 120 | 12 | 14 / 16 | yes | 6 | 5 | 5 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_120_12_5 | 5 (upper) | 3 x 20 | 120 | 12 | 1 / 12 | yes | 2 | 17 | 2 | lower | 0.1 / 0.2 | 0.1 / 0.2 |
| bbs_120_12_5 | 5 (upper) | 4 x 15 | 120 | 12 | 6 / 19 | yes | 3 | 9 | 3 | lower | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_120_12_5 | 5 (upper) | 5 x 12 | 120 | 12 | 10 / 21 | yes | 4 | 6 | 4 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_120_12_5 | 5 (upper) | 10 x 6 | 120 | 12 | 18 / 3 | yes | 11 | 2 | 2 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_144_12_6 | 6 (upper) | 12 x 12 (default) | 144 | 12 | 11 / 12 | yes | 6 | 6 | 6 | yes | 0.1 / 0.2 | 0.2 / 0.1 |
| bbs_144_12_6 | 6 (upper) | 6 x 24 | 144 | 12 | 1 / 8 | yes | 2 | 14 | 2 | lower | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_144_12_6 | 6 (upper) | 8 x 18 | 144 | 12 | 7 / 10 | yes | 3 | 10 | 3 | lower | 0.1 / 0.2 | 0.1 / 0.2 |
| bbs_144_12_6 | 6 (upper) | 9 x 16 | 144 | 12 | 7 / 13 | yes | 3 | 9 | 3 | lower | 0.1 / 0.2 | 0.1 / 0.2 |
| bbs_144_12_6 | 6 (upper) | 11 x 13 | 144 | 12 | 10 / 12 | yes | 4 | 6 | 4 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_144_12_6 | 6 (upper) | 13 x 11 | 144 | 12 | 12 / 12 | yes | 6 | 4 | 4 | lower | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_144_12_6 | 6 (upper) | 16 x 9 | 144 | 12 | 13 / 7 | yes | 8 | 3 | 3 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_144_12_6 | 6 (upper) | 18 x 8 | 144 | 12 | 13 / 6 | yes | 8 | 3 | 3 | lower | 0.2 / 0.1 | 0.1 / 0.2 |
| bbs_144_12_6 | 6 (upper) | 24 x 6 | 144 | 12 | 8 / 1 | yes | 12 | 2 | 2 | lower | 0.2 / 0.1 | 0.1 / 0.2 |
| bbs_182_12_7 | 7 (upper) | 7 x 13 (default) | 182 | 12 | 17 / 23 | yes | 7 | 7 | 7 | yes | 0.1 / 0.2 | 0.2 / 0.2 |
| bbs_182_12_7 | 7 (upper) | 13 x 7 | 182 | 12 | 21 / 8 | yes | 17 | 3 | 3 | lower | 0.3 / 0.1 | 0.5 / 0.1 |
| bbs_216_12_8 | 8 (upper) | 12 x 19 (default) | 216 | 12 | 20 / 28 | yes | 8 | 8 | 8 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_216_12_8 | 8 (upper) | 8 x 28 | 216 | 12 | 12 / 25 | yes | 4 | 13 | 4 | lower | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_216_12_8 | 8 (upper) | 9 x 25 | 216 | 12 | 15 / 28 | yes | 5 | 12 | 5 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_216_12_8 | 8 (upper) | 18 x 13 | 216 | 12 | 29 / 14 | yes | 12 | 4 | 4 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_216_12_8 | 8 (upper) | 24 x 10 | 216 | 12 | 23 / 8 | yes | 16 | 3 | 3 | lower | 0.4 / 0.2 | 0.3 / 0.1 |
| bbs_216_12_8 | 8 (upper) | 27 x 9 | 216 | 12 | 20 / 6 | yes | 20 | 2 | 2 | lower | 2.0 DP / 0.1 | 1.4 / 0.2 |
| bbs_260_12_9 | 9 (upper) | 13 x 10 (default) | 260 | 12 | 25 / 27 | yes | 9 | 9 | 9 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_260_12_9 | 9 (upper) | 5 x 26 | 260 | 12 | 2 / 18 | yes | 2 | 41 | 2 | lower | 0.2 / 1.7 DP | 0.1 / >1800 ([36, ?]) |
| bbs_260_12_9 | 9 (upper) | 10 x 13 | 260 | 12 | 17 / 30 | yes | 6 | 12 | 6 | lower | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_260_12_9 | 9 (upper) | 26 x 5 | 260 | 12 | 21 / 10 | yes | 25 | 3 | 3 | lower | 15.0 DP / 0.2 | 214.4 / 0.1 |
| bbs_288_12_10 | 10 (upper) | 9 x 16 (default) | 288 | 12 | 24 / 31 | 64 GiB | 10 | 10 | 10 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_288_12_10 | 10 (upper) | 6 x 24 | 288 | 12 | 14 / 27 | yes | 6 | 18 | 6 | lower | 0.2 / 0.6 | 0.2 / 0.5 |
| bbs_288_12_10 | 10 (upper) | 8 x 18 | 288 | 12 | 21 / 33 | 64 GiB | 8 | 11 | 8 | lower | 0.3 / 0.2 | 0.1 / 0.2 |
| bbs_288_12_10 | 10 (upper) | 12 x 12 | 288 | 12 | 34 / 21 | 64 GiB | 16 | 6 | 6 | lower | 0.3 / 0.2 | 0.2 / 0.1 |
| bbs_288_12_10 | 10 (upper) | 16 x 9 | 288 | 12 | 28 / 13 | yes | 24 | 4 | 4 | lower | 36.7 / 0.2 | 36.8 / 0.2 |
| bbs_288_12_10 | 10 (upper) | 18 x 8 | 288 | 12 | 25 / 11 | yes | 30 | 3 | 3 | lower | 88.4 DP / 0.2 | >1800 ([27, ?]) / 0.1 |
| bbs_288_12_10 | 10 (upper) | 24 x 6 | 288 | 12 | 17 / 6 | yes | 44 | 2 | 2 | lower | 1.5 DP / 0.2 | >1800 ([31, ?]) / 0.1 |
| bbs_85_13_4 | 4 (upper) | 6 x 6 (default) | 85 | 13 | 11 / 9 | yes | 4 | 4 | 4 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_126_13_5 | 5 (upper) | 9 x 14 (default) | 126 | 13 | 17 / 15 | yes | 5 | 5 | 5 | yes | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_126_13_5 | 5 (upper) | 6 x 21 | 126 | 13 | 9 / 22 | yes | 2 | 10 | 2 | lower | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_126_13_5 | 5 (upper) | 7 x 18 | 126 | 13 | 12 / 22 | yes | 3 | 7 | 3 | lower | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_126_13_5 | 5 (upper) | 14 x 9 | 126 | 13 | 18 / 7 | yes | 8 | 2 | 2 | lower | 0.1 / 0.1 | 0.2 / 0.1 |
| bbs_163_13_6 | 6 (upper) | 13 x 13 (default) | 163 | 13 | 20 / 17 | yes | 6 | 6 | 6 | yes | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_163_13_6 | 6 (upper) | 7 x 25 | 163 | 13 | 7 / 20 | yes | 2 | 18 | 2 | lower | 0.2 / 0.4 | 0.1 / 0.3 |
| bbs_189_13_7 | 7 (upper) | 14 x 14 (default) | 189 | 13 | 23 / 19 | yes | 7 | 7 | 7 | yes | 0.1 / 0.2 | 0.1 / 0.1 |
| bbs_189_13_7 | 7 (upper) | 7 x 29 | 189 | 13 | 7 / 19 | yes | 2 | 21 | 2 | lower | 0.2 / 0.9 | 0.1 / 0.8 |
| bbs_189_13_7 | 7 (upper) | 11 x 18 | 189 | 13 | 16 / 27 | yes | 4 | 10 | 4 | lower | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_189_13_7 | 7 (upper) | 15 x 13 | 189 | 13 | 25 / 17 | yes | 8 | 6 | 6 | lower | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_218_13_8 | 8 (upper) | 15 x 15 (default) | 218 | 13 | 25 / 21 | yes | 8 | 8 | 8 | yes | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_218_13_8 | 8 (upper) | 10 x 23 | 218 | 13 | 13 / 27 | yes | 4 | 13 | 4 | lower | 0.2 / 0.2 | 0.2 / 0.1 |
| bbs_218_13_8 | 8 (upper) | 12 x 19 | 218 | 13 | 19 / 29 | yes | 5 | 11 | 5 | lower | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_248_13_9 | 9 (upper) | 16 x 16 (default) | 248 | 13 | 27 / 22 | yes | 9 | 9 | 9 | yes | 0.2 / 0.2 | 0.1 / 0.1 |
| bbs_248_13_9 | 9 (upper) | 17 x 15 | 248 | 13 | 29 / 21 | yes | 10 | 8 | 8 | lower | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_248_13_9 | 9 (upper) | 23 x 11 | 248 | 13 | 27 / 14 | yes | 16 | 4 | 4 | lower | 0.3 / 0.2 | 0.2 / 0.1 |
| bbs_281_13_10 | 10 (upper) | 17 x 17 (default) | 281 | 13 | 29 / 25 | yes | 10 | 10 | 10 | yes | 0.3 / 0.2 | 0.2 / 0.1 |
| bbs_ex1_surface_53_1 | - (unknown) | 4 x 8 (default) | 53 | 1 | 3 / 4 | yes | 4 | 8 | 4 | - | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_ex3_tile_50_8_2 | 2 (upper) | 5 x 5 (default) | 50 | 8 | 6 / 6 | yes | 2 | 2 | 2 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_ex3_tilefix_50_7_3 | 3 (upper) | 5 x 5 (default) | 50 | 7 | 7 / 7 | yes | 3 | 3 | 3 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_ex3_50_7_3 | 3 (upper) | 5 x 5 (default) | 50 | 7 | 6 / 7 | yes | 3 | 3 | 3 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_ex3_72_7_4 | 4 (upper) | 6 x 6 (default) | 72 | 7 | 10 / 10 | yes | 4 | 4 | 4 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_ex3_98_7_5 | 5 (upper) | 7 x 7 (default) | 98 | 7 | 12 / 12 | yes | 5 | 5 | 5 | yes | 0.1 / 0.1 | 0.2 / 0.1 |
| bbs_ex3_128_7_6 | 6 (upper) | 8 x 8 (default) | 128 | 7 | 15 / 14 | yes | 6 | 6 | 6 | yes | 0.2 / 0.1 | 0.1 / 0.1 |
| bbs_ex4_45_6_3 | 3 (upper) | 5 x 5 (default) | 45 | 6 | 4 / 4 | yes | 3 | 3 | 3 | yes | 0.1 / 0.1 | 0.1 / 0.1 |
| bbs_ex5_292_12_14 | dx 14, dz 16 (upper) | 19 x 8 (default) | 292 | 12 | 31 / 31 | 64 GiB | 14 | 16 | 14 | yes | 0.3 / 0.7 | 0.2 / 0.7 |
| bbs_ex5_noladder_292_13_6 | dx 14, dz 6 (upper) | 19 x 8 (default) | 292 | 13 | 31 / 30 | 64 GiB | 14 | 6 | 6 | yes | 0.2 / 0.2 | 0.2 / 0.2 |
| bbs_ex5_lec_292_12_14 | 14 (upper) | 19 x 8 (default) | 292 | 12 | 31 / 30 | 64 GiB | 14 | 14 | 14 | yes | 0.3 / 0.4 | 0.3 / 0.3 |
| bbs_ex6_314_13_6 | dx 6, dz 12 (upper) | 8 x 19 (default) | 314 | 13 | 35 / 32 | no | 6 | 12 | 6 | yes | = search / 0.3 | 0.2 / 0.2 |
| bbs_ex6_fixed_314_12_14 | 14 (upper) | 8 x 19 (default) | 314 | 12 | 35 / 32 | no | 18 | 12 | 12 | lower | = search / 0.2 | 4.4 / 0.2 |
| bbs_rhp_121_9_5 | 5 (upper) | 11 x 11 (default) | 121 | 9 | 14 / 14 | yes | 5 | 5 | 5 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_fig8_66_10_4 | 4 (upper) | 10 x 7 (default) | 66 | 10 | 10 / 7 | yes | 4 | 4 | 4 | yes | 0.1 / 0.1 | 0.1 / 0.2 |
| bbs_fig8_103_10_5 | 5 (upper) | 12 x 9 (default) | 103 | 10 | 15 / 11 | yes | 5 | 5 | 5 | yes | 0.2 / 0.1 | 0.1 / 0.2 |
| bbs_fig8_103_10_5 | 5 (upper) | 21 x 5 | 103 | 10 | 14 / 2 | yes | 13 | 2 | 2 | lower | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_fig8_125_10_6 | 6 (upper) | 13 x 10 (default) | 125 | 10 | 17 / 13 | yes | 6 | 6 | 6 | yes | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_fig8_148_10_7 | 7 (upper) | 14 x 11 (default) | 148 | 10 | 19 / 16 | yes | 7 | 7 | 7 | yes | 0.1 / 0.2 | 0.2 / 0.1 |
| bbs_fig8_148_10_7 | 7 (upper) | 19 x 8 | 148 | 10 | 20 / 10 | yes | 11 | 4 | 4 | lower | 0.2 / 0.2 | 0.1 / 0.1 |
| bbs_fig8_186_10_8 | 8 (upper) | 16 x 12 (default) | 186 | 10 | 20 / 18 | yes | 8 | 9 | 8 | yes | 0.2 / 0.1 | 0.2 / 0.1 |
| bbs_fig8_186_10_8 | 8 (upper) | 27 x 7 | 186 | 10 | 18 / 8 | yes | 19 | 4 | 4 | lower | 0.9 / 0.2 | 1.1 / 0.2 |
| bbs_fig8_198_10_9 | 9 (upper) | 17 x 12 (default) | 198 | 10 | 25 / 18 | yes | 9 | 9 | 9 | yes | 0.2 / 0.2 | 0.1 / 0.2 |
| bbs_fig8_278_10_11 | 11 (upper) | 19 x 15 (default) | 278 | 10 | 30 / 23 | yes | 11 | 12 | 11 | yes | 0.3 / 0.2 | 0.2 / 0.2 |
<!-- /TABLE:bbsurface -->

### Barbell codes, arXiv:2606.06062

The barbell code is the tile code of the same tiles and corners (the barbell embedding adds dummy checks and
ancillas only); the paper names no distance method.

<!-- TABLE:barbell -->
| instance | n | k | paper: d (status) | width d_X / d_Z | fits | d_X found | d_Z found | front end s (X / Z) | search only s (X / Z) |
|---|---|---|---|---|---|---|---|---|---|
| barbell_w6a_128_7_6 | 128 | 7 | 6 (unknown) | 12 / 14 | yes | 6 | 6 | 0.2 / 0.2 | 0.2 / 0.2 |
| barbell_w6a_162_7_7 | 162 | 7 | 7 (unknown) | 14 / 17 | yes | 7 | 7 | 0.2 / 0.2 | 0.2 / 0.2 |
| barbell_w6a_200_7_8 | 200 | 7 | 8 (unknown) | 16 / 19 | yes | 8 | 9 | 0.2 / 0.2 | 0.2 / 0.1 |
| barbell_w6a_242_7_9 | 242 | 7 | 9 (unknown) | 19 / 21 | yes | 9 | 11 | 0.2 / 0.2 | 0.1 / 0.1 |
| barbell_w6a_288_7_11 | 288 | 7 | 11 (unknown) | 20 / 23 | yes | 11 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| barbell_w6a_338_7_13 | 338 | 7 | 13 (unknown) | 23 / 25 | yes | 13 | 13 | 0.4 / 0.3 | 0.3 / 0.3 |
| barbell_w6a_392_7_14 | 392 | 7 | 14 (unknown) | 25 / 27 | yes | 14 | 16 | 0.6 / 0.7 | 0.5 / 0.5 |
| barbell_w6b_128_8_6 | 128 | 8 | 6 (unknown) | 14 / 14 | yes | 6 | 6 | 0.2 / 0.2 | 0.1 / 0.1 |
| barbell_w6b_162_8_7 | 162 | 8 | 7 (unknown) | 18 / 16 | yes | 7 | 7 | 0.2 / 0.2 | 0.1 / 0.2 |
| barbell_w6b_200_8_9 | 200 | 8 | 9 (unknown) | 21 / 18 | yes | 9 | 9 | 0.2 / 0.2 | 0.2 / 0.2 |
| barbell_w6b_242_8_10 | 242 | 8 | 10 (unknown) | 23 / 20 | yes | 10 | 10 | 0.2 / 0.2 | 0.1 / 0.1 |
| barbell_w6b_288_8_12 | 288 | 8 | 12 (unknown) | 24 / 22 | yes | 12 | 12 | 0.3 / 0.2 | 0.2 / 0.2 |
| barbell_w6b_338_8_13 | 338 | 8 | 13 (unknown) | 28 / 24 | yes | 13 | 13 | 0.3 / 0.4 | 0.2 / 0.3 |
| barbell_w6b_392_8_15 | 392 | 8 | 15 (unknown) | 30 / 26 | yes | 15 | 15 | 0.4 / 0.4 | 0.3 / 0.3 |
| barbell_w8_242_16_8 | 242 | 16 | 8 (unknown) | 28 / 25 | yes | 8 | 8 | 0.2 / 0.2 | 0.2 / 0.1 |
| barbell_w8_288_16_9 | 288 | 16 | 9 (unknown) | 32 / 28 | 64 GiB | 9 | 9 | 0.2 / 0.2 | 0.2 / 0.2 |
| barbell_w8_338_16_10 | 338 | 16 | 10 (unknown) | 35 / 31 | no | 10 | 10 | = search / 0.3 | 0.2 / 0.2 |
| barbell_w8_392_16_11 | 392 | 16 | 11 (unknown) | 37 / 34 | no | 11 | 11 | = search / = search | 0.2 / 0.2 |
| barbell_w8_450_16_14 | 450 | 16 | 14 (unknown) | 42 / 37 | no | 14 | 14 | = search / = search | 0.5 / 0.3 |
| barbell_w10_162_16_8 | 162 | 16 | 8 (unknown) | 21 / 19 | yes | 8 | 8 | 0.2 / 0.2 | 0.2 / 0.1 |
| barbell_w10_200_16_10 | 200 | 16 | 10 (unknown) | 25 / 22 | yes | 10 | 10 | 0.2 / 0.2 | 0.2 / 0.1 |
| barbell_w10_242_16_11 | 242 | 16 | 11 (unknown) | 28 / 25 | yes | 11 | 11 | 0.2 / 0.3 | 0.2 / 0.2 |
| barbell_w10_288_16_12 | 288 | 16 | 12 (unknown) | 32 / 28 | 64 GiB | 12 | 12 | 0.3 / 0.3 | 0.2 / 0.2 |
| barbell_w10_338_16_13 | 338 | 16 | 13 (unknown) | 35 / 31 | no | 13 | 13 | = search / 0.4 | 0.3 / 0.3 |
| barbell_w10_392_16_14 | 392 | 16 | 14 (unknown) | 38 / 34 | no | 14 | 14 | = search / 0.5 | 0.7 / 0.4 |
| barbell_w10_450_16_15 | 450 | 16 | 15 (unknown) | 42 / 37 | no | 15 | 15 | = search / = search | 2.3 / 0.8 |
| barbell_w10_512_16_16 | 512 | 16 | 16 (unknown) | 45 / 40 | no | 16 | 16 | = search / = search | 9.4 / 2.1 |
<!-- /TABLE:barbell -->

### Space-group codes, arXiv:2606.20548 (v3)

Most are small codes on cylinders or tori whose checks reach across most of the lattice, so their widths are not
those of a local code; `sg_f4top_*` are the topological families of Fig. 4 (distances read off its plot).

<!-- TABLE:spacegroup -->
| instance | n | k | paper: d (status) | width d_X / d_Z | fits | d_X found | d_Z found | front end s (X / Z) | search only s (X / Z) |
|---|---|---|---|---|---|---|---|---|---|
| sg_t1_12_8_2 | 12 | 8 | 2 (exact) | 2 / 2 | yes | 2 | 2 | 0.2 / 0.2 | 0.1 / 0.1 |
| sg_t1_14_6_2 | 14 | 6 | 2 (exact) | 3 / 3 | yes | 2 | 2 | 0.2 / 0.2 | 0.1 / 0.2 |
| sg_t1_14_8_2 | 14 | 8 | 2 (exact) | 3 / 3 | yes | 2 | 2 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_18_4_4 | 18 | 4 | 4 (exact) | 5 / 5 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_18_6_3 | 18 | 6 | 3 (exact) | 4 / 4 | yes | 3 | 3 | 0.2 / 0.1 | 0.1 / 0.2 |
| sg_t1_24_4_4 | 24 | 4 | 4 (exact) | 6 / 6 | yes | 4 | 4 | 0.1 / 0.1 | 0.1 / 0.2 |
| sg_t1_24_10_4 | 24 | 10 | 4 (exact) | 6 / 6 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.1 |
| sg_t1_28_6_4 | 28 | 6 | 4 (exact) | 7 / 7 | yes | 4 | 4 | 0.1 / 0.1 | 0.2 / 0.1 |
| sg_t1_30_10_4 | 30 | 10 | 4 (exact) | 8 / 8 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_32_6_6 | 32 | 6 | 6 (exact) | 10 / 10 | yes | 6 | 6 | 0.2 / 0.1 | 0.2 / 0.2 |
| sg_t1_36_4_6 | 36 | 4 | 6 (exact) | 10 / 9 | yes | 6 | 6 | 0.2 / 0.1 | 0.2 / 0.2 |
| sg_t1_40_14_4 | 40 | 14 | 4 (exact) | 6 / 6 | yes | 4 | 4 | 0.1 / 0.2 | 0.2 / 0.2 |
| sg_t1_42_6_6 | 42 | 6 | 6 (exact) | 11 / 11 | yes | 6 | 6 | 0.2 / 0.2 | 0.2 / 0.1 |
| sg_t1_48_4_8 | 48 | 4 | 8 (exact) | 14 / 14 | yes | 8 | 8 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_50_18_4 | 50 | 18 | 4 (exact) | 13 / 12 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_60_8_6 | 60 | 8 | 6 (exact) | 13 / 14 | yes | 6 | 6 | 0.2 / 0.2 | 0.2 / 0.1 |
| sg_t1_70_6_8 | 70 | 6 | 8 (exact) | 18 / 16 | yes | 8 | 8 | 0.2 / 0.1 | 0.1 / 0.2 |
| sg_t1_84_10_9 | 84 | 10 | 9 (exact) | 26 / 29 | yes | 9 | 9 | 0.2 / 0.1 | 0.2 / 0.1 |
| sg_t1_96_8_10 | 96 | 8 | 10 (exact) | 27 / 27 | yes | 10 | 10 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_112_6_12 | 112 | 6 | 12 (exact) | 30 / 32 | 64 GiB | 12 | 12 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_112_16_10 | 112 | 16 | 10 (exact) | 32 / 33 | 64 GiB | 10 | 10 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t1_120_14_12 | 120 | 14 | 12 (exact) | 39 / 38 | no | 12 | 12 | = search / = search | 0.2 / 0.3 |
| sg_t1_132_8_11 | 132 | 8 | 11 (exact) | 35 / 34 | no | 11 | 11 | = search / 0.2 | 0.2 / 0.2 |
| sg_t1_150_8_12 | 150 | 8 | 12 (exact) | 38 / 38 | no | 12 | 12 | = search / = search | 0.2 / 0.2 |
| sg_t1_156_8_12 | 156 | 8 | 12 (exact) | 48 / 49 | no | 12 | 13 | = search / = search | 0.1 / 0.2 |
| sg_t1_160_26_8 | 160 | 26 | 8 (exact) | 29 / 29 | yes | 8 | 8 | 0.2 / 0.2 | 0.2 / 0.1 |
| sg_t2_48_4_8 | 48 | 4 | 8 (exact) | 11 / 11 | yes | 8 | 8 | 0.1 / 0.1 | 0.1 / 0.2 |
| bb_t2_48_4_8 | 48 | 4 | 8 (exact) | 11 / 11 | yes | 8 | 8 | 0.2 / 0.1 | 0.2 / 0.1 |
| sg_t2_56_6_8 | 56 | 6 | 8 (exact) | 14 / 14 | yes | 8 | 8 | 0.2 / 0.1 | 0.1 / 0.1 |
| bb_t2_56_6_8 | 56 | 6 | 8 (exact) | 15 / 15 | yes | 8 | 8 | 0.2 / 0.2 | 0.1 / 0.1 |
| sg_t2_96_4_12 | 96 | 4 | 12 (exact) | 22 / 22 | yes | 12 | 12 | 0.2 / 0.2 | 0.2 / 0.2 |
| bb_t2_96_4_12 | 96 | 4 | 12 (exact) | 30 / 28 | yes | 12 | 12 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_t2_108_12_6 | 108 | 12 | 6 (exact) | 11 / 11 | yes | 6 | 6 | 0.2 / 0.2 | 0.1 / 0.2 |
| bb_t2_108_12_6 | 108 | 12 | 6 (exact) | 11 / 11 | yes | 6 | 6 | 0.2 / 0.2 | 0.2 / 0.1 |
| sg_t2_132_4_14 | 132 | 4 | 14 (exact) | 34 / 34 | no | 14 | 14 | = search / = search | 0.2 / 0.2 |
| bb_t2_132_4_14 | 132 | 4 | 14 (exact) | 38 / 37 | no | 14 | 14 | = search / = search | 0.2 / 0.3 |
| sg_t3_48_4_8 | 48 | 4 | 8 (unknown) | 12 / 12 | yes | 8 | 8 | 0.1 / 0.2 | 0.2 / 0.2 |
| sg_t3_96_6_10 | 96 | 6 | 10 (unknown) | 28 / 29 | yes | 10 | 10 | 0.1 / 0.1 | 0.2 / 0.2 |
| bb_t3_144_12_12 | 144 | 12 | 12 (unknown) | 32 / 32 | 64 GiB | 12 | 12 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_f4top_code1_L4 | 32 | 4 | 4 (unknown) | 8 / 7 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_f4top_code1_L5 | 50 | 2 | 5 (unknown) | 15 / 15 | yes | 5 | 5 | 0.2 / 0.2 | 0.1 / 0.1 |
| sg_f4top_code1_L6 | 72 | 6 | 4 (unknown) | 17 / 18 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.1 |
| sg_f4top_code1_L7 | 98 | 2 | 7 (unknown) | 29 / 30 | yes | 7 | 7 | 0.1 / 0.2 | 0.1 / 0.2 |
| sg_f4top_code1_L8 | 128 | 4 | 8 (unknown) | 32 / 33 | 64 GiB | 8 | 8 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_f4top_code1_L9 | 162 | 4 | 6 (unknown) | 35 / 37 | no | 6 | 6 | = search / = search | 0.2 / 0.2 |
| sg_f4top_code1_L10 | 200 | 4 | 10 (unknown) | 41 / 41 | no | 10 | 10 | = search / = search | 0.2 / 0.2 |
| sg_f4top_code1_L11 | 242 | 2 | 11 (unknown) | 47 / 48 | no | 11 | 11 | = search / = search | 0.2 / 0.2 |
| sg_f4top_code2_L4 | 32 | 2 | 4 (unknown) | 9 / 9 | yes | 4 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_f4top_code2_L5 | 50 | 2 | 5 (unknown) | 15 / 15 | yes | 5 | 5 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_f4top_code2_L6 | 72 | 4 | 6 (unknown) | 22 / 21 | yes | 6 | 6 | 0.1 / 0.1 | 0.1 / 0.1 |
| sg_f4top_code2_L7 | 98 | 2 | 7 (unknown) | 25 / 25 | yes | 7 | 7 | 0.2 / 0.1 | 0.2 / 0.1 |
| sg_f4top_code2_L8 | 128 | 2 | 8 (unknown) | 29 / 29 | yes | 8 | 8 | 0.2 / 0.2 | 0.1 / 0.2 |
| sg_f4top_code2_L9 | 162 | 4 | 9 (unknown) | 34 / 34 | no | 9 | 9 | 0.2 / = search | 0.2 / 0.2 |
| sg_f4top_code2_L10 | 200 | 2 | 10 (unknown) | 37 / 37 | no | 10 | 10 | = search / = search | 0.1 / 0.2 |
| sg_f4top_code2_L11 | 242 | 2 | 11 (unknown) | 41 / 41 | no | 11 | 11 | = search / = search | 0.2 / 0.2 |
| sg_f4top_code3_L4 | 32 | 6 | 3 (unknown) | 6 / 7 | yes | 3 | 4 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_f4top_code3_L5 | 50 | 2 | 5 (unknown) | 12 / 12 | yes | 5 | 5 | 0.2 / 0.2 | 0.1 / 0.2 |
| sg_f4top_code3_L6 | 72 | 4 | 6 (unknown) | 12 / 13 | yes | 6 | 6 | 0.2 / 0.2 | 0.2 / 0.2 |
| sg_f4top_code3_L7 | 98 | 2 | 7 (unknown) | 17 / 17 | yes | 7 | 7 | 0.1 / 0.1 | 0.1 / 0.2 |
| sg_f4top_code3_L8 | 128 | 6 | 6 (unknown) | 18 / 18 | yes | 6 | 8 | 0.1 / 0.1 | 0.2 / 0.1 |
| sg_f4top_code3_L9 | 162 | 2 | 9 (unknown) | 22 / 22 | yes | 9 | 9 | 0.2 / 0.2 | 0.1 / 0.1 |
| sg_f4top_code3_L10 | 200 | 4 | 10 (unknown) | 25 / 25 | yes | 10 | 10 | 0.2 / 0.2 | 0.2 / 0.1 |
| sg_f4top_code3_L11 | 242 | 2 | 11 (unknown) | 28 / 27 | yes | 11 | 11 | 0.2 / 0.2 | 0.2 / 0.2 |
<!-- /TABLE:spacegroup -->

## Vine-code memory circuits

"collapsed d" is the distance of the adapter's time collapse (by the DP on our order, `collapsed_dp/`, where it
fits, otherwise by the pipeline's search); "fold-2 d" is the certified lower bound from the period-2 fold,
"window" the weight of the fault set found in rounds 0..1; d_circ is exact where the two meet.

<!-- TABLE:circuits -->
| circuit | rounds | paper d_circ | collapsed: rows x cols, width | fold-2: rows x cols, width | collapsed d | fold-2 d (lower) | window (upper) | d_circ found | fold + window s | pipeline s (dp=1 / dp=0) |
|---|---|---|---|---|---|---|---|---|---|---|
| vine_435_6_10_memX_r10 | 10 | 10 (conjectured) | 319 x 1247, 27 | 638 x 3144, 52 | 6 | 10 | 10 | 10 | 4.3 (16 thr) | 1289 / - |
| vine_435_6_10_memZ_r10 | 10 | 10 (conjectured) | 332 x 1155, 31 | 664 x 3198, 64 | 10 | 10 | 10 | 10 | 12.4 (16 thr) | 20 / - |
| vine_437_6_10_memX_r10 | 10 | 10 (conjectured) | 320 x 1276, 28 | 640 x 3171, 53 | 6 | 10 | 10 | 10 | 4.4 (16 thr) | 1428 / - |
| vine_437_6_10_memX_r14 | 14 | 10 (conjectured) | - x -, - | 640 x 3171, - | - | 10 | 10 | 10 | 42.7 (1 thr) | - / - |
| vine_437_6_10_memZ_r10 | 10 | 10 (conjectured) | 335 x 1169, 31 | 670 x 3234, 64 | 10 | 10 | 10 | 10 | 30.9 (8 thr) | 21 / - |
| vine_437_6_10_memZ_r14 | 14 | 10 (conjectured) | - x -, - | 670 x 3234, - | - | 10 | 10 | 10 | 166.6 (1 thr) | - / - |
| vine_538_6_10_memX_r10 | 10 | 10 (conjectured) | 339 x 1416, 37 | 678 x 3747, 72 | 10 | 10 | 10 | 10 | 11.3 (8 thr) | 22 / - |
| vine_538_6_10_memZ_r10 | 10 | 10 (conjectured) | 327 x 1365, 41 | 654 x 3669, 82 | 10 | 10 | 10 | 10 | 11.4 (8 thr) | 22 / - |
| vine_557_6_10_memX_r10 | 10 | 10 (conjectured) | 431 x 1585, 31 | 862 x 4209, 64 | 10 | 10 | 10 | 10 | 25.9 (8 thr) | 40 / - |
| vine_557_6_10_memX_r14 | 14 | 10 (conjectured) | - x -, - | 862 x 4209, - | - | 10 | 10 | 10 | 156.1 (1 thr) | - / - |
| vine_557_6_10_memZ_r10 | 10 | 10 (conjectured) | 400 x 1580, 27 | 800 x 4048, 54 | 6 | 10 | 10 | 10 | 14.0 (8 thr) | 1793 / - |
| vine_557_6_10_memZ_r14 | 14 | 10 (conjectured) | - x -, - | 800 x 4048, - | - | 10 | 10 | 10 | 74.2 (1 thr) | - / - |
| vine_fig7_nSeWwSs_s11_memX_r7 | 7 | 8 (reported) | 246 x 839, 22 | 492 x 2016, 42 | 5 | 8 | 8 | 8 | 1.4 (1 thr) | 100 / 110 |
| vine_fig7_nSeWwSs_s11_memZ_r7 | 7 | 7 (reported) | 256 x 759, 26 | 512 x 2058, 54 | 7 | 7 | 7 | 7 | 1.1 (1 thr) | 5 / 4 |
| vine_fig7_nSeWwSs_s5_memX_r5 | 5 | 4 (reported) | 78 x 230, 9 | 156 x 492, 18 | 3 | 4 | 4 | 4 | 0.0 (1 thr) | 0 / 0 |
| vine_fig7_nSeWwSs_s5_memZ_r5 | 5 | 3 (reported) | 82 x 198, 15 | 164 x 510, 28 | 3 | 3 | 3 | 3 | 0.0 (1 thr) | 0 / 0 |
| vine_fig7_nSeWwSs_s7_memX_r5 | 5 | 5 (reported) | 126 x 393, 14 | 252 x 888, 26 | 4 | 5 | 5 | 5 | 0.1 (1 thr) | 2 / 1 |
| vine_fig7_nSeWwSs_s7_memZ_r5 | 5 | 5 (reported) | 132 x 345, 18 | 264 x 914, 39 | 5 | 5 | 5 | 5 | 0.1 (1 thr) | 1 / 0 |
<!-- /TABLE:circuits -->

## Caveats

- **Constructions are ours, except the vine codes**, which are read off the authors' circuits.  Every instance
  reproduces the paper's n and k, and every distance a paper gives as exact is reproduced; the reading notes in
  `papers/new/` list the conventions that had to be inferred.  Two of them matter for the results above:
  the w = 10 tile code [[512,18,≤23]] uses the paper's tiles on the only square layout with n = 512 (the paper
  does not state the layout; the weight-8 [[512,18,19]] on the same layout reproduces its ILP-exact 19), and the
  Table III codes of 2606.19482 use the M x N convention that reproduces all of Table III's n, routing counts and
  IP-exact d_Z.
- **Hexagonal directional tile codes (`dtc_hex_*`)**: the paper gives no sizes; our reconstruction reproduces n,
  k and the check counts of its Fig. 3, but not its distances: 4 instead of 3 at n = 52, and 5 or 6 instead of 7
  at the two sizes with n = 199 (at n = 104 one of the two sizes gives the paper's 5, the other 2); [[74,10,4]] is
  not reachable and is built at n = 76.  These are therefore not the authors' codes and are not used as checks of
  the paper.
- **BB surface code of Example 6 (`bbs_ex6_fixed_314_12_14`)**: reproduces n = 314 and k = 12 but has d_Z = 12,
  not 14; the example's text is inconsistent (it promotes 16 weight-6 X logicals, of which only 15 fit in the
  region), so our amended code is probably not the authors'.
- **BB surface codes**: the paper gives no region sizes.  Every size with the paper's n and k (up to 30 x 30) is
  listed; a row is consistent with the paper where some size has d equal to the reported value.
- **Vine-code circuits**: the d = 10 circuits are rebuilt from the authors' noiseless two-round files with the
  construction of their noisy multi-round files (validated on all 12 of those: identical gates, detectors and
  error mechanisms).  Idle noise is on every idle qubit, a superset of the authors' locations, so the lower bound
  holds for their noise placement as well; the upper bound (a weight-10 logical of data errors right after the
  data reset) exists in both.  The values are for 10 rounds (the authors' max(5, d)); 14 rounds give the same
  for the two patches tried, and the fold-2 problem is the same for both round counts.
- **Threads**: the search-alone runs of the first table use 32 threads; most other runs use 2 to 32 threads by
  table size (`scripts/planar_jobs.py`).  The macOS build of the kernels has no OpenMP, so the local vine runs are
  single-threaded whatever OMP_NUM_THREADS says.
- **"exact"** always comes with a fault set checked against the matrices (records' `witness_ok`); intervals give the
  search's certified lower bound and the lightest logical found (by the search or by our ISD, `isd/`).

## Reproduce

```sh
python papers/planar_vine.py                          # n, k of the vine patches (needs the Zenodo files)
python scripts/planar_dp.py widths <family>           # -> widths_<family>.json
python scripts/planar_dp.py export <family>           # -> instances/
python scripts/planar_jobs.py make jobs.txt && python scripts/planar_jobs.py run jobs.txt --budget 200
python papers/planar_vine.py export_circuits results/planar_dp/circuits
python scripts/planar_dp.py circuit-widths collapsed results/planar_dp/circuits/*
python scripts/planar_dp.py circuit-dp collapsed results/planar_dp/circuits/<name>
python scripts/planar_fold.py results/planar_dp/circuits/<name> --kmax 11
python scripts/summarize_planar_dp.py                 # fills the tables of this file
```
