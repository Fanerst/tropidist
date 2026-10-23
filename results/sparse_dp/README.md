# Weight-truncated sparse Rank DP

Question (Feng): can the linear Rank DP run with a weight bound, i.e. build the tropical partition function weight
by weight, truncated at K? If it works, the two exact evaluators of the distance become one family: the dense DP
is the untruncated breadth-first evaluation, the search the truncated depth-first one.

**Answer: yes, exactly.** The truncated sweep needs a meet-in-the-middle split of the weight between a forward and
a backward sweep to be useful. With the split, it beats both the dense DP and the search in one regime:
geometrically local circuits that are not graph-like, of cut rank 25–55 and distance 7–11. These are the
superdense color-code circuits of arXiv:2603.22532:

| circuit | sparse DP | dense DP | search |
|---|---|---|---|
| d7 | 0.57 s | 2.6 s | 2.4 s |
| d9 | 10 s | cannot run (cut rank 39) | 378 s |
| d11 | 13 min: d = 11 | cannot run (cut rank 55) | ≥ 8 after 600 s |

It settles the open instance. **The superdense color-code circuit of distance 11 has circuit distance 11.**
This holds for its memory-basis sector (the benchmark's quantity) and for the full detector error model, of
which the sector is an exact reduction. Before, the bounds were 8..11 for every method at 600 s, and 10..11
after an 8 h run of our pipeline and 32-thread runs. The value is now the instance's recorded distance:
- certificate `wjh_superdense_d11.json`;
- `bench/instances.py` WJH_TRUTH and the instance's `meta.json`;
- the WJH table of `docs/BENCHMARK.md`, marked and not counted there, since it comes from outside the
  benchmark protocol.

Elsewhere the old division stays:
- **Narrow codes** go to the dense DP. On color codes the sparse DP is 5–9× slower, but 100× or more faster than
  the search.
- **Expanding qLDPC codes** go to the search, which takes milliseconds. The sparse DP still beats the dense DP
  where that one is slow or cannot run (bb108, gross).
- **Graph-like circuits** (surface code) go to the search too.

## What was built

`cdist/sparse_dp.py` (with the C kernel `cdist/sparse_dp.c`, tests `tests/test_sparse_dp.py`):

- **Same trellis as the dense DP.** Column order from `cdist.auto.best_order` (the pipeline's choice), rows in
  minimal span form plus the reduced target row (`trellis.py`). Each row gets a fixed bit ("slot") by an interval
  colouring of its span, so a state means the same going forward and backward.
- **Sparse tables.** At each cut the table is a sorted array of (state, least weight). One column step is
  `T'[s] = min(T[s], T[s ^ col] + 1)`, followed by the rows that close at that column (filter on the target
  parity, then clear the bit).
- **Truncation.** States of weight > K are dropped. This is exact: along the sweep a state's value only grows,
  and by induction every state through which a solution of weight ≤ K passes keeps its exact value. The sweep
  therefore returns the minimum when it is ≤ K, and "none ≤ K" otherwise.
- **Lookahead h.** States with weight + h > K are dropped too, with h an admissible bound on the remaining
  faults. h = ⌈Σ_{unsatisfied active rows r} y_r⌉ with y_r = 1 / (the most relevant rows any remaining column
  containing r touches). That is a dual solution of the covering LP, and refines the suggested
  ⌈unsatisfied / max rows per column⌉. Admissibility is tested against exact backward tables.
- **Meet in the middle** (mode `mitm`), the change that matters:
  - A backward sweep keeps weights ≤ K − a. A forward sweep keeps weights ≤ a − 1, and its new or improved
    states of weight ≤ a are joined with the backward table at every cut.
  - A forward state at the cap weight a cannot grow further, so it is joined once, where it appears, and is
    not carried.
  - Every solution of weight ≤ K is seen at the cut after its a-th column. The proof is in the docstring of
    `sparse_dp.query`.
  - The tables then hold states of weight about K/2, the analogue of the search's meet-in-the-middle table.
- **Split schedules.** The split may fall along the sweep: a(c) non-increasing, exact if the whole forward
  table is joined once more where a drops. `choose_split` (one a) and `choose_schedule` (a per cut, by a small
  DP) predict the work from probe sweeps at weight ≤ 3. Local circuits need the schedule: forward tables are
  small in the first rounds and backward tables small afterwards (figure below).
- **Witness runs.** The run at K = d stops at its first solution, so it costs mostly its backward sweep. It takes
  the split of the K = d − 1 run plus one, which keeps that backward sweep.
- **Iterative deepening.** `sparse_dp.distance(p, start=LB)` deepens K from a lower bound; each threshold that
  fails for every observable proves the next one.
- **Witness by traceback.** Tables are kept at checkpoints (every √N cuts) and recomputed segment by segment,
  so about 2√N tables are held. Every witness is checked: H e = 0, L e ≠ 0, |e| = value.
- **Dense fallback.** A forward sweep switches to a dense array (`viterbi.c`'s update) where the sparse table
  would hold more than a fraction of the 2^w states, and back below a quarter of it.
- **Two table formats.** `NumpyTables` is the reference (sorted keys and values, up to 64 slots). `CTables`
  packs value and key in one uint64 (up to 56 slots): candidates come from the states below the cap, are
  restored to sorted order by one pass per bit of the column mask, and are merged linearly. Both are
  double-buffered.

**Validation.**
- Brute force: 272,076 random queries in numpy and C (forward, every split, with and without h, with the dense
  fallback), plus 66,814 with random split schedules.
- The test file: 7 tests, 15 s.
- On every instance below the value equals the known distance and the dense DP's value, and every witness
  checks.

**Prototype first.** In numpy, superdense d9 was certified (K = 8 sweep, then K = 9 with a witness) in 95 s on
one laptop core. The search pipeline needs 374 s, and the dense DP cannot run it. That justified the C kernel:
- its first version did the K = 8 sweep in 25.8 s;
- with double-buffered tables, in 6.1 s (11× numpy);
- with the split schedule and the witness rule, the whole certificate (both thresholds, probes included) takes
  10.1 s on the server.

## Results

Instances:
- **narrow:** 6.6.6 color codes d7–27; the other codes of the low-width trial (`bench/export_lowwidth.py`;
  `color_cc_dD` is `color dD`).
- **expanding:** BB72/90/108/144 (gross), code capacity.
- **local circuits:** the memory-basis sector problems of the surface and superdense color-code circuits of
  arXiv:2603.22532, d = 3–11.

Setup:
- Server 5090, one thread per job, each job in its own process, other users' load present.
- The search runs the benchmark configuration (label-free table of depth 2, pair exclusions, covering bound)
  with 600 s per instance.
- The dense DP is limited to 2^33-byte tables.
- Sparse runs are limited to 1e8 states per table and 1 h, except the dedicated d11 runs.

### Validation: distance found by each method

| instance | known d | MITM sched | MITM | MITM+h | fwd+h | fwd | dense DP | search |
|---|---|---|---|---|---|---|---|---|
| color d7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| color d9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| color d11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |
| color d13 | 13 | 13 | 13 | 13 | 13 | 13 | 13 | 13 |
| color d15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 |
| color d17 | 17 | 17 | 17 | 17 | 17 | 17 | 17 | 17 |
| color d19 | 19 | 19 | 19 | 19 | 19 | 19 | 19 | 19 |
| color d21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 |
| color d23 | 23 | 23 | 23 | 23 | 23 | 23 | 23 | ≥ 21 (timeout) |
| color d25 | 25 | 25 | 25 | 25 | 25 | 25 | 25 | ≥ 21 (timeout) |
| color d27 | 27 | 27 | 27 | 27 | 27 | budget | 27 | ≥ 21 (timeout) |
| concat_steane_L2 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| hypercube_L2 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| concat_steane_L3 | 27 | 27 | 27 | 27 | 27 | 27 | 27 | ≥ 22 (timeout) |
| hypercube_L3 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| concat_steane_L4 | 81 | 81 | 81 | 81 | 81 | 81 | 81 | ≥ 18 (timeout) |
| gross | 12 | 12 | 12 | 12 | budget | budget | too wide | 12 |
| bb72 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| bb90 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| bb108 | 10 | 10 | 10 | 10 | 10 | ≥ 10 (budget at K = 10) | 10 | 10 |
| superdense d3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| superdense d5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| superdense d7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| superdense d9 | 9 | 9 | 9 | 9 | ≥ 9 (budget at K = 9) | budget | too wide | 9 |
| superdense d11 | 10..11 (open) | 11‡ | 11‡ | budget | budget | budget | too wide | ≥ 8 (timeout) |
| surface d3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| surface d5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| surface d7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| surface d9 | 9 | 9 | 9 | 9 | 9 | budget | too wide | 9 |
| surface d11 | 11 | 11† | budget† | error | error | error | too wide | 11 |

† numpy tables (the trellis needs 62 row slots, the C tables hold 56). ‡ dedicated runs, see *Superdense d11*.

### Time (seconds, one thread)

Sparse: the sweep at K = d − 1 for every observable, plus the one at K = d that stops at its first solution and returns the witness; the split probes are included. Search: every threshold from K = 1, and in brackets its last two (d − 1 and d). Dense DP: one untruncated sweep per observable. Bold: the fastest method.

| instance | regime | columns | cut rank | d | dense DP | search | MITM sched | MITM | MITM+h | fwd+h | fwd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| color d7 | narrow | 37 | 8 | 7 | **0.001** | 0.003 (0.000) | 0.008 | 0.008 | 0.01 | 0.008 | 0.004 |
| color d9 | narrow | 61 | 9 | 9 | **0.001** | 0.005 (0.000) | 0.01 | 0.01 | 0.02 | 0.01 | 0.006 |
| color d11 | narrow | 91 | 11 | 11 | **0.001** | 0.009 (0.002) | 0.02 | 0.02 | 0.02 | 0.02 | 0.01 |
| color d13 | narrow | 127 | 13 | 13 | **0.001** | 0.04 (0.02) | 0.03 | 0.03 | 0.03 | 0.03 | 0.01 |
| color d15 | narrow | 169 | 16 | 15 | **0.003** | 0.29 (0.18) | 0.05 | 0.04 | 0.05 | 0.11 | 0.02 |
| color d17 | narrow | 217 | 17 | 17 | **0.003** | 2.48 (1.59) | 0.06 | 0.06 | 0.07 | 0.16 | 0.03 |
| color d19 | narrow | 271 | 20 | 19 | **0.03** | 22.2 (14.1) | 0.21 | 0.21 | 0.27 | 1.44 | 0.15 |
| color d21 | narrow | 331 | 22 | 21 | **0.11** | 194 (122) | 0.60 | 0.60 | 0.72 | 6.41 | 0.53 |
| color d23 | narrow | 397 | 23 | 23 | **0.07** | ≥ 21 (timeout) | 0.65 | 0.44 | 0.55 | 8.14 | 0.64 |
| color d25 | narrow | 469 | 25 | 25 | **0.37** | ≥ 21 (timeout) | 1.80 | 1.81 | 2.20 | 50.0 | 4.42 |
| color d27 | narrow | 547 | 28 | 27 | **0.86** | ≥ 21 (timeout) | 6.75 | 4.31 | 5.61 | 168 | budget |
| concat_steane_L2 | narrow | 49 | 7 | 9 | **0.001** | 0.005 (0.000) | 0.01 | 0.01 | 0.01 | 0.009 | 0.004 |
| hypercube_L2 | narrow | 36 | 6 | 4 | **0.002** | 0.002 (0.000) | 0.10 | 0.10 | 0.13 | 0.03 | 0.01 |
| concat_steane_L3 | narrow | 343 | 10 | 27 | **0.002** | ≥ 22 (timeout) | 0.07 | 0.07 | 0.08 | 0.05 | 0.03 |
| hypercube_L3 | narrow | 216 | 22 | 8 | 1.59 | **0.04 (0.03)** | 2.24 | 2.20 | 3.00 | 7.85 | 8.52 |
| concat_steane_L4 | narrow | 2401 | 13 | 81 | **0.02** | ≥ 18 (timeout) | 0.50 | 0.46 | 0.66 | 0.45 | 0.20 |
| gross | expanding | 144 | 40 | 12 | too wide | **0.06 (0.03)** | 5.59 | 5.56 | 7.41 | budget | budget |
| bb72 | expanding | 72 | 20 | 6 | 0.08 | **0.003 (0.000)** | 0.15 | 0.14 | 0.20 | 0.12 | 0.15 |
| bb90 | expanding | 90 | 26 | 10 | 2.85 | **0.01 (0.006)** | 0.19 | 0.18 | 0.25 | 87.2 | 30.1 |
| bb108 | expanding | 108 | 30 | 10 | 78.5 | **0.01 (0.005)** | 0.24 | 0.26 | 0.32 | 28.0 | ≥ 10 (budget at K = 10) |
| superdense d3 | local circuit | 70 | 7 | 3 | **0.001** | 0.002 (0.000) | 0.02 | 0.02 | 0.02 | 0.01 | 0.007 |
| superdense d5 | local circuit | 414 | 15 | 5 | **0.003** | 0.03 (0.01) | 0.10 | 0.10 | 0.12 | 0.22 | 0.06 |
| superdense d7 | local circuit | 1248 | 25 | 7 | 2.59 | 2.42 (2.12) | **0.57** | 0.59 | 0.76 | 19.6 | 66.3 |
| superdense d9 | local circuit | 2788 | 39 | 9 | too wide | 378 (339) | **10.1** | 13.9 | 18.6 | ≥ 9 (budget at K = 9) | budget |
| superdense d11 | local circuit | 5250 | 55 | 11 | too wide | ≥ 8 (timeout) | **772‡** | 1158‡ | budget | budget | budget |
| surface d3 | local circuit | 55 | 6 | 3 | **0.001** | 0.002 (0.000) | 0.01 | 0.01 | 0.02 | 0.01 | 0.005 |
| surface d5 | local circuit | 301 | 14 | 5 | **0.004** | 0.008 (0.001) | 0.07 | 0.06 | 0.09 | 0.04 | 0.05 |
| surface d7 | local circuit | 883 | 26 | 7 | 18.3 | **0.06 (0.02)** | 0.28 | 0.29 | 0.36 | 0.73 | 33.6 |
| surface d9 | local circuit | 1945 | 42 | 9 | too wide | **0.98 (0.61)** | 5.74 | 8.13 | 7.25 | 124 | budget |
| surface d11 | local circuit | 3631 | 62 | 11 | too wide | **36.1 (28.0)** | 1664† | budget† | error | error | error |

### States kept, against the dense table

2^w: entries of the dense table at the widest cut; dense work: entries the dense DP updates per observable. For the sparse sweeps at K = d − 1: the split a (for a schedule, its values along the sweep), the largest table, the states summed over all cuts, both directions and all observables, and the bytes of the tables held at the peak (checkpoints included); then the process's peak memory.

| instance | 2^w | dense work | MITM sched a | peak | total | tables | MITM a | peak | total | fwd+h peak | fwd+h total | peak memory (MITM sched) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| color d7 | 256 | 2956 | 4→3 | 37 | 571 | 992 B | 3 | 37 | 567 | 178 | 1159 | 0.04 GB |
| color d9 | 512 | 9388 | 4 | 57 | 1539 | 2.0 kB | 4 | 57 | 1539 | 216 | 3969 | 0.04 GB |
| color d11 | 2048 | 3.6e4 | 4 | 326 | 5508 | 6.8 kB | 4 | 326 | 5508 | 832 | 1.4e4 | 0.04 GB |
| color d13 | 8192 | 1.6e5 | 6 | 463 | 1.5e4 | 15.7 kB | 6 | 463 | 1.5e4 | 3477 | 5.3e4 | 0.04 GB |
| color d15 | 6.6e4 | 1.8e6 | 5 | 3973 | 1.9e5 | 145.2 kB | 5 | 3973 | 1.9e5 | 6.3e4 | 8.5e5 | 0.04 GB |
| color d17 | 1.3e5 | 3.1e6 | 7 | 7552 | 2.1e5 | 141.4 kB | 7 | 7552 | 2.1e5 | 4.4e4 | 1.1e6 | 0.04 GB |
| color d19 | 1.0e6 | 3.8e7 | 5 | 9.7e4 | 4.9e6 | 2.8 MB | 5 | 9.7e4 | 4.9e6 | 1.0e6 | 1.8e7 | 0.06 GB |
| color d21 | 4.2e6 | 1.7e8 | 6 | 2.8e5 | 1.7e7 | 8.7 MB | 6 | 2.8e5 | 1.7e7 | 4.2e6 | 8.2e7 | 0.09 GB |
| color d23 | 8.4e6 | 2.4e8 | 8 | 5.2e5 | 1.4e7 | 6.0 MB | 9 | 3.1e5 | 9.2e6 | 2.5e6 | 7.6e7 | 0.10 GB |
| color d25 | 3.4e7 | 1.3e9 | 10 | 1.5e6 | 3.9e7 | 26.5 MB | 10 | 1.5e6 | 3.9e7 | 8.9e6 | 3.8e8 | 0.23 GB |
| color d27 | 2.7e8 | 4.1e9 | 10 | 8.8e6 | 1.7e8 | 91.3 MB | 11 | 5.1e6 | 1.1e8 | 5.9e7 | 1.3e9 | 1.13 GB |
| concat_steane_L2 | 128 | 1372 | 4 | 20 | 494 | 464 B | 4 | 20 | 494 | 73 | 716 | 0.04 GB |
| hypercube_L2 | 64 | 1532 | 2 | 6 | 2917 | 160 B | 2 | 6 | 2901 | 29 | 9159 | 0.04 GB |
| concat_steane_L3 | 1024 | 3.4e4 | 9 | 223 | 1.2e4 | 6.5 kB | 10 | 196 | 1.2e4 | 712 | 2.1e4 | 0.04 GB |
| hypercube_L3 | 4.2e6 | 4.5e8 | 4 | 386 | 2.1e6 | 21.6 kB | 4 | 386 | 2.1e6 | 5.2e4 | 1.9e8 | 0.05 GB |
| concat_steane_L4 | 8192 | 8.5e5 | 25 | 1844 | 3.1e5 | 23.4 kB | 27 | 1757 | 3.0e5 | 6216 | 5.4e5 | 0.05 GB |
| gross | 1.1e12 | 2.9e13 | 4 | 4.5e5 | 1.8e8 | 10.0 MB | 4 | 4.5e5 | 1.8e8 | – | – | 0.12 GB |
| bb72 | 1.0e6 | 1.3e7 | 4→3 | 137 | 6.4e4 | 5.9 kB | 3 | 137 | 6.4e4 | 2813 | 5.3e5 | 0.04 GB |
| bb90 | 6.7e7 | 1.3e9 | 4 | 7692 | 1.9e6 | 224.8 kB | 4 | 7692 | 1.9e6 | 2.2e6 | 3.1e8 | 0.04 GB |
| bb108 | 1.1e9 | 3.4e10 | 4 | 1.3e4 | 2.4e6 | 262.7 kB | 4 | 1.3e4 | 2.4e6 | 2.9e6 | 3.6e8 | 0.04 GB |
| superdense d3 | 128 | 4624 | 2→1 | 15 | 527 | 664 B | 2 | 19 | 654 | 16 | 434 | 0.04 GB |
| superdense d5 | 3.3e4 | 3.5e6 | 3→2 | 424 | 5.6e4 | 25.2 kB | 2 | 611 | 7.1e4 | 1710 | 1.8e5 | 0.04 GB |
| superdense d7 | 3.4e7 | 1.2e10 | 4→3 | 9943 | 4.1e6 | 982.7 kB | 3 | 2.9e4 | 5.7e6 | 2.1e5 | 4.6e7 | 0.04 GB |
| superdense d9 | 5.5e11 | 2.8e14 | 5→4 | 4.4e5 | 3.6e8 | 60.2 MB | 4 | 1.6e6 | 5.3e8 | 3.8e7 | 1.2e10 | 0.28 GB |
| superdense d11 | 3.6e16 | 4.4e19 | 7→6→5 | 2.7e7 | 4.4e10 | 5.0 GB | 5 | 1.2e8 | 6.2e10 | – | – | 15.13 GB |
| surface d3 | 64 | 2156 | 2→1 | 10 | 251 | 320 B | 2 | 9 | 290 | 7 | 139 | 0.04 GB |
| surface d5 | 1.6e4 | 2.7e6 | 3→2 | 175 | 2.6e4 | 12.1 kB | 3 | 183 | 3.0e4 | 211 | 2.4e4 | 0.04 GB |
| surface d7 | 6.7e7 | 3.2e10 | 5→4→3 | 5717 | 2.2e6 | 612.3 kB | 4 | 6683 | 3.1e6 | 1.7e4 | 3.7e6 | 0.04 GB |
| surface d9 | 4.4e12 | 4.7e15 | 6→5→4 | 2.8e5 | 2.3e8 | 41.2 MB | 4 | 1.3e6 | 3.5e8 | 2.8e6 | 7.0e8 | 0.18 GB |
| surface d11 | 4.6e18 | 9.2e21 | 8→7→6→5 | 1.8e7 | 2.6e10 | 3.9 GB | – | – | – | – | – | 19.95 GB |

### Superdense d11

The problem:
- The memory-basis sector of `05_r=11,d=11,...,c=superdense_color_code_Z,q=181` (11 rounds, 181 qubits).
- 540 detectors, 5250 columns, one observable.
- Identical, column for column, to `bench/instances_wjh/wjh_superdense_d11` sector, which equals their
  basis-filtered DEM (the benchmark's quantity).
- Cut rank 55 in the DEM order, so the dense DP would need 2^55 bytes.

The runs (last table above, one thread on 5090):
- **K = 10: two independent sweeps, neither finds a solution of weight ≤ 10.**
  - The uniform split a = 5 takes 808 s; its largest table is 1.2e8 states in the first rounds (56 GB).
  - The schedule a = 7 → 6 → 5 takes 670 s with a largest table of 2.7e7 states (11.5 GB).
  - An earlier uniform run, from the first version of the code, finished the same way
    (`logs/first_d11_uniform_a5.log`).
- **K = 11: two witness runs, which stop at their first solution.**
  - Split 6: 351 s, 94 GB. Its traceback recomputes segments of the large backward tables of the first rounds.
  - The K = 10 schedule plus one: 102 s, 15 GB.
  - They return two different weight-11 solutions, both checked on our problem and on the exported instance
    (zero syndrome, observable flipped, 11 distinct columns):
    `[0, 2, 8, 30, 43, 82, 104, 695, 752, 889, 944]` and `[0, 2, 8, 30, 43, 83, 96, 153, 175, 806, 882]`.
  - The pipeline's weight-11 witness (`results/bench_wjh_8h/ours_pipeline`) is a third one.
  - The first witness, lifted column by column to the full detector error model (990 detectors, 41,044
    columns), checks there too: `[0, 5, 16, 89, 137, 271, 319, 523, 604, 4266, 4977]`. The sector reduction
    is exact, which the export checks.

**Hence the distance is 11**, of the sector problem and of the full circuit. With the schedule the whole
certificate takes 13 min and 15 GB on one thread.
The K = 10 runs are complete sweeps of an exact procedure with different splits, hence different tables, so
they guard each other against errors in the split logic.

## Reading the results

**Exactness.** Every method that finished agrees with the known distance on every instance, and every sparse
witness checks.

**Cost per state.** The dense kernel takes ~0.2–0.3 ns per table entry (SIMD); the sparse C step takes ~10 ns per
state and column. The sparse sweep therefore beats the dense DP only when it keeps fewer than about 1/40 of the
dense entries (compare "total" with "dense work" above).

**Narrow codes** (color, concatenated Steane):
- The truncated tables keep 1/5–1/17 of the dense entries (color d19–27), so the dense DP is 5–9× faster.
- The meet-in-the-middle sweep is still 100× or more faster than the search: color d19 takes 0.21 s against
  22 s, d21 0.60 s against 194 s, and the search times out from d23 on and on concatenated Steane L3–L4.
- Forward-only truncation barely helps here: at K = d − 1 nearly every state of a narrow trellis has weight ≤ K
  (figure, color d27).

The hypercube codes are a contrast: hypercube L3 has 64 logical qubits, i.e. 64 queries per method, and the
search wins.

**Expanding codes** (BB):
- On an expander few partial solutions share an interface state, so merging buys little. Meanwhile the
  search's covering bound prunes almost everything: it answers in milliseconds, 15–100× faster than the sparse
  DP.
- The sparse DP still beats the dense DP by 15–300× (bb90 0.19 s against 2.9 s, bb108 0.24 s against 79 s),
  and handles gross (a 2^40 dense table) in 5.6 s.

**Local circuits**, two families:
- **Graph-like** (surface code: every column flips at most two detectors of the sector): the search wins (d9:
  1.0 s against 5.7 s; d11: 36 s against 1664 s with numpy tables).
- **Superdense color code** (columns with up to four detectors): the sparse DP is the fastest method from d7 on,
  and the only one that reaches d11. Many partial chains end on the same interface state; the DP merges them,
  while the search enumerates each.

**Lookahead h:**
- It pays only in forward-only sweeps on local circuits: superdense d7 takes 19.6 s with h against 66 s without,
  surface d7 0.73 s against 34 s.
- On expanding codes its popcounts cost more than they prune (bb90: 87 s against 30 s).
- On narrow codes it keeps the tables just sparse enough to miss the faster dense fallback (color d25: 50 s
  against 4.4 s).
- In the meet-in-the-middle sweep it does not pay: MITM+h is 10–40 % slower, except on surface d9 (11 % faster).
  States hold weight ≤ K/2, so the bound would have to exceed a remaining budget of at least K/2. A useful bound there would have to see the
  remaining problem (a relaxation of it), not only its interface; not pursued.

**Meet in the middle and the split:**
- Holding weights up to about K/2 instead of K is the decisive step. Forward-only truncation (with h) keeps 2–160×
  more states than the meet in the middle (10× or more on the instances that are not graph-like). It exceeds the
  1e8-state budget on gross and superdense d11, and on superdense d9 at K = d; without h also on bb108 and
  surface d9.
- The split itself matters. Superdense d9 at K = 8 costs 1.0e9 state-steps with a = 4, and 6–8e9 with a = 3 or 5;
  `choose_split` picks 4.
- On circuits the two directions differ by 10–30× per cut, in opposite ways in the first rounds and afterwards
  (figure). The schedule exploits this: superdense d9 takes 10.1 s against 13.9 s, and at d11 (K = 10) the
  largest table holds 2.7e7 states against 1.2e8, with 11.5 GB against 56 GB.

**Memory.** Tables are kept at checkpoints every √N cuts plus one segment: at most 1.1 GB on every instance
except superdense d11 (15 GB with the schedule) and surface d11 (20 GB, numpy tables).

**Threads.** Every number here is one thread. The dense DP gains about 13× at 32 threads
(`scripts/calibrate_dp.py`), and the search parallelises over subtrees; the sparse kernel is serial. A parallel
step (partition the state space by its top bits and merge the parts independently) is the obvious next step. It
would not move the regimes, since the gaps above are mostly 10× or more.

## The unified picture (for the paper)

The three evaluators compute the same min-plus sum over the trellis, and differ in what they keep:

| evaluator | keeps | cost | wins when |
|---|---|---|---|
| dense Rank DP | every state at every cut | N · 2^w, independent of d | w small (≤ ~30) |
| weight-bounded search | partial solutions of weight ≤ K, one at a time, no merging | the pruned tree up to d | expanding codes: few partial solutions survive the covering bound |
| truncated sparse DP (MITM) | states of weight ≤ ~K/2 per direction, merged per state | N · (states of weight ≤ K/2 at a cut) | many partial solutions share an interface state (local, not graph-like), w too large for the dense table |

The sparse DP contains the dense one: K = ∞ with the dense fallback is the dense DP. It is breadth-first, like the
dense DP, but truncated and split like the search. Its own regime is where neither special case works:
- The interface is too wide for a dense table.
- d is too large for an unmerged tree.
- Partial solutions merge a lot, so the merged table stays small. Merging is what the search cannot do.

## Reproduce

```
bash scripts/server/sparse_dp_eval.sh            # every record of this folder (about 2 h on 5090)
python scripts/summarize_sparse_dp.py            # tables.md and states_per_cut.png
python -m pytest tests/test_sparse_dp.py
```

The WJH circuits are read from `$WJH_CIRCUITS`, their codeDistance package, as for `bench/export_wjh.py`.

Records in this folder (the summary takes the later file where a configuration appears twice):
- `narrow`, `lowwidth`, `bb`, `circuits`: every configuration, from the first pass.
- `schedule`, then `mitm`: the meet-in-the-middle configurations again, the second with the witness-run rule
  (the final code; it supersedes the first pass's entries for these configurations).
- `d11`: the first pass on d11, with a 1e8-state budget.
- `d11_K10_a5`, `d11_K10_schedule`, `d11_K11_a6`, `d11_K11_schedule`: the dedicated d11 runs.
- `wjh_superdense_d11.json`: the certificate (certified bounds 11..11, the runs, the checked witnesses, the
  hashes of the sector matrices); it is the instance's truth file.
- `surface11`: numpy tables, because that trellis has 62 slots.
- `logs/`: the dedicated d11 runs and the first d11 attempts.
