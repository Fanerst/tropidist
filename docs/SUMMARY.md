# Summary (4 October 2026)

Details and all tables: [BB_CIRCUITS.md](BB_CIRCUITS.md) (method, BB72–BB288), [PAPERS.md](PAPERS.md) (published and
designed circuits), [PHASE4.md](PHASE4.md) (branch and bound). Every number below is exact unless a
range is given: all lighter fault sets are excluded exhaustively, and the fault set that realises the
value was replayed in Stim.

## What was achieved

1. **Exact circuit distance of real memory circuits**, as certified intervals that close: the
   minimum number of faults (undecomposed DEM mechanisms) that fire no detector and flip a logical
   observable. Largest closed cases: BB288 (576 qubits, 206k mechanisms, distance 16) and Cornucopia
   [[1044,526,12]] (1566 qubits, 271k mechanisms, distance 10).
2. **Claims of 17 recent papers checked**: BP-OSD upper bounds turned into exact values, one
   conjecture confirmed, several claimed distances shown not to survive at circuit level.
3. **Circuits designed and certified** where papers give none, or where the standard one is not
   the best: mirror depth-8 circuits for weight-8 codes, and all 8496 depth-7 schedules of the
   standard bivariate bicycle (BB) codes.
4. **249 code distances** that papers give only as estimates or bounds, settled exactly.

## Representative cases

**The circuit keeps the code distance.**

| code | circuit | circuit distance |
|---|---|---:|
| [[72,12,6]] | standard BB depth-7 circuit | 6 |
| [[576,292,8]] Cornucopia | paper's 12-layer circuit | 8 |
| [[90,8,9]] routing code | paper's CNOT+SWAP circuit | 9 |
| [[170,16,10]] | static and time-dynamic shift circuits (2601.09911) | 10 |
| [[90,8,8]] amplified, level 1 | authors' circuit (they certify ≥ 6) | 8 |
| [[108,8,10]] | depth-7 schedule found here (standard schedule: 8) | 10 |
| [[120,8,12]] self-dual BB | mirror depth-8 circuit designed here | 12 |
| [[144,16,10]] weight-8 BB | mirror depth-8 circuit designed here | 10 |

**The circuit distance is below the code distance.**

| code | circuit | code distance | circuit distance | paper's statement |
|---|---|---:|---:|---|
| [[288,12,18]] | standard BB circuit | 18 | 16 | ≤ 18 |
| [[144,12,12]] gross | standard depth-7 circuit | 12 | 10 | ≤ 10 |
| [[144,12,12]] gross | best of all 8496 depth-7 schedules; left-right circuit of 2603.05481 | 12 | 11 | 11 conjectured |
| [[1044,526,12]] Cornucopia | paper's circuit | 12 | 10 | ≤ 11 |
| [[900,454,10]] Cornucopia | paper's circuit | 10 | 9 | ≤ 10 |
| [[300,60,14]] mitten | "hook-free" schedule | 14 | 12 | 14 |
| [[150,30,10]] mitten | "hook-free" schedule | 10 | 8 | 10 |
| [[200,24,14]] routing, weight 11 | paper's circuit | 14 | 10 | ≤ 14 |
| [[54,2,10]] Walking Cat | paper's circuit, best numbering | 10 | 9 | 9 |
| [[132,30,12]] GALA | best circuit designed here | 12 | 10 | fit ≈ 9.5 |
| [[360,12,≤24]] BB360 | standard circuit | 24 | 17–21 (Z), 19–21 (X) | ≤ 24 |

Pattern: the loss comes from hook faults and from mid-cycle states. With a good gate order it is 0
to 2 up to distance about 12; it is larger for heavier checks and higher distance (4 for the
weight-11 routing code, 7 for mitten [[500,100,16]] in the X basis). The gate order matters as much
as the code: for the gross code the 8496 valid depth-7 schedules range from 6 to 11.

## Is there a general tool others can use?

**The method is general; a packaged tool is not there yet.**

What exists (`cdist/`, 3.4k lines of Python and C, plus drivers):

- input: any Stim memory circuit with its noise; the undecomposed DEM is the problem;
- certified reductions: CSS sector (checked exact), time collapse / fold (lower bounds, independent
  of the number of rounds), one- and two-round windows (upper bounds);
- exact search with translation symmetry, a covering bound, and one pass for any number of logical
  qubits; top-down lifting for the largest cases;
- every upper bound replayed as physical faults in Stim;
- two drivers: `run_bb.py circuit.stim out.json` and `papers/run_parallel.py <module> <key> <basis> out.json`.

Evidence that it transfers: thirteen circuit families went through the same pipeline unchanged
(CNOT, CZ, CNOT+SWAP, time-dynamic circuits; check weight 6 to 12; 2 to 526 logical qubits), five of
them with builders written by Codex from the interface description alone.

**Where Rank DP stands.** Dense min-plus Rank DP is exact, and it is the right formulation: the state
is the partial syndrome at a cut, the width is the cut rank. But the cut rank grows linearly with the
code (35 for the time-collapsed [[90,8,10]], 97 for collapsed BB288, 282 for the real BB288 circuit),
so the dense table stops at the collapsed [[90,8,10]] problem (64 GB). What solves the large cases is
the same recursion kept sparse (only syndromes reachable within the weight budget, meet in the middle)
on certified relaxations. A fair description is "weight-bounded sparse Rank DP with relaxations", not
dense Rank DP.

**Reach today.**

| circuit | qubits | DEM mechanisms | result | cost |
|---|---:|---:|---|---|
| gross, standard | 288 | 68k | 10, exact | 4 s, 128 threads |
| routing [[200,24,14]] | 400 | 95k | 10, exact | 4 min, 16 threads |
| Cornucopia [[1044,526,12]] | 1566 | 271k | 10, exact | 13 min, 128 threads |
| BB288 | 576 | 206k | 16, exact | 12 to 27 min, 128 threads |
| BB360 | 720 | – | 17–21 | hours, not closed |
| mitten n ≥ 500, amplified level 2, BB756 | | | lower bounds only | not closed |

Rule of thumb: exact for circuit distance up to about 10–12 at any size tried (n up to 1000), up to
16 with translation symmetry; each further unit of distance costs about a factor 6.

**What is missing before others can use it.**

1. One command for an arbitrary Stim file. The drivers rely on a detector-coordinate convention
   (check id, round, X/Z type) or on a small builder module per code.
2. Symmetry is supplied by the user (check permutations); it is found automatically only for BB-style
   coordinates. Without it the reach drops by one to two units of distance.
3. CSS memory experiments only. Non-CSS and Floquet circuits fall back to the full DEM, which is
   feasible only for small cases.
4. Packaging: no version control, no installable package, no user documentation, kernel compiled on
   first use, and until 4 October a memory leak in batch use (fixed).
