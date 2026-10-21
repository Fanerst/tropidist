# Dense trellis DP: local audit, 21 October 2026

**Status: stopped at the user's request; no experiments are running.** Widths are available for all 251 problems. Dense DP has completed 49/186 formal benchmark instances. 51 formal instances have an observed table peak of at most 4 GiB.

This report evaluates the implementation at commit `b4cfc4493acbd9d279357104ccb23a85fb92b452`. The DP and ordering implementations were not changed. The added scripts perform data reconstruction, ordering searches, resource accounting, execution and reporting.

## Separation from the pulled results

All results in this audit directory were generated locally on 21 October 2026. They are not part of the previously pulled server benchmark records.

The pulled commit contains `results/dense.json`: completed BB72 Z/X t=0 windows (distance 6), BB72 Z/X collapsed problems (distance 5), and the BB90 Z t=0 window (distance 10). Its other BB108/BB144/BB288 entries contain width measurements without completed dense distance results.

The separate pulled `dense_big_*` files contain two large-memory server experiments: BB144 Z t=0/code-capacity window (12 observables, distance 12, cut width 33, table peak 35 bits = 32 GiB) and BB90 Z collapsed (8 observables, distance 7, cut width 34, table peak 36 bits = 64 GiB). Neither the 60-instance benchmark nor the 126-instance WJH benchmark contains a dense-DP solver run. Their `ours`/`ours_search`/`ours_pipeline` records use weight-bounded sparse search and the reduction/lifting pipeline.

## Scope and interpretation

- Main benchmark: 60 instances (16 code-distance problems and 44 circuits).
- WJH benchmark: 126 instances (103 code-distance problems and 23 circuits).
- Two fixtures are reported separately. All 63 exported collapsed variants, including one fixture, are also evaluated.
- A circuit uses its exported memory sector when the reduction is exact. The reconstruction checks that every projected column has an equal-cost pure-sector lift. The five Stim color circuits use their full DEM.
- Collapsed problems are relaxations. Their exact DP values are lower bounds on circuit distance, unless an independent argument establishes equality.
- `amplified_90` is registered but was not exported into the benchmark. The registry marks it `needs_lead`: flag detectors make its default memory-sector selector ambiguous. It is outside the 186-instance count.

For an ordering π, the reported width is the maximum of `rank(H_past) + rank(H_future) - rank(H)`. It is an upper bound obtained from a specific linear ordering, not a certificate of the minimum possible width. It is not the width of a general branch decomposition.

The C kernel allocates one byte per state. Its actual `peak_bits = p` gives a table of `2^p` bytes. The per-column update temporarily includes starting rows before ending rows are removed, and one logical target row may also be active. Consequently, p can be one or two bits above the reported cut width. Every feasible-size problem is checked against the actual plans for **all** logical observables.

| Actual peak bits p | Table memory | Local policy |
|---:|---:|---|
| 28 | 256 MiB | Executed |
| 30 | 1 GiB | Executed |
| 31 | 2 GiB | Executed |
| 32 | 4 GiB | Executed |
| 33 | 8 GiB | Larger than the per-task audit cap |
| 34 | 16 GiB | Leaves limited room for the running desktop |
| 35 | 32 GiB | Exceeds this machine's physical RAM |

## Machine and protocol

Apple M5 Pro, 15 physical cores (5 performance and 10 efficiency), 24 GiB RAM. The repository's macOS build uses one kernel thread; it does not enable OpenMP. Python and package versions, source checksums and limits are retained in `manifest.json`.

For every problem, the baseline considers the native order and, for a sector, a time order. It then attempts greedy seeds 0–23 within 12 seconds and runs up to 3000 existing block-move/reversal iterations within 6 seconds. Local iterations are submitted in blocks of 100 with seeds 1, 2, …; this retains completed improvements at a deadline. Four width workers were used. Large problems can exhaust the ordering budget before one greedy order completes; their native/time ordering still provides the reported upper bound. Every completed trial and final permutation is saved.

Additional searches are identified in the tables. For the two BB144 code problems, 120 existing geometric sweeps seed repeated 3000-step local searches (at most 100 calls, within a 60-second cap). Five other boundary cases receive up to 30 additional seconds of existing greedy/local search. A geometric probe also improves the main BB288 code ordering. These are unequal, explicitly recorded search budgets, not an optimal-width benchmark.

Small dense runs use a 300-second limit. The five remaining 2–4 GiB cases use 1200 seconds. Each solve processes all observable rows and returns their minimum. Dense times include plan construction and the complete observable sweep; they exclude input reconstruction, ordering, process startup and compilation. Each run has its own process, so its peak RSS is attributable to that solve. Several one-thread runs can overlap; the simultaneous dense-table budget is at most 8 GiB. Timings describe this desktop session, not isolated-core measurements.

## Formal benchmark coverage

| Suite | Type | Total | Table ≤4 GiB | Complete dense solves |
|---|---|---:|---:|---:|
| main | code | 16 | 4 | 4 |
| main | circuit | 44 | 5 | 5 |
| wjh | code | 103 | 30 | 29 |
| wjh | circuit | 23 | 12 | 11 |

Collapsed relaxations: 35/62 completed. These are excluded from the formal circuit-solve counts.

## Ordering sensitivity near the memory boundary

| Problem | Baseline width | Best width | Baseline table bits | Best table bits | Dense distance | Dense seconds |
|---|---:|---:|---:|---:|---:|---:|
| code_bb144 | 34 | 30 | 36 | 32 | 12 | 417.4 |
| wjh_bb_n144 | 33 | 30 | 35 | 32 | — | — |
| wjh_hcc_09_n168 | 33 | 30 | 34 | 31 | 6 | 318.3 |
| wjh_hsc_09_n252 | 30 | 29 | 32 | 31 | 4 | 138.1 |
| wjh_midout_d11 | 31 | 31 | 32 | 32 | — | — |
| code_bb288 | 73 | 68 | ≥74 | ≥69 | — | — |

## All formal benchmark instances

`w` is the best observed cut width. `p` is the actual maximum plan table width; a range is an analytic bound when full logical plans were unnecessary because the H section alone was too large. `refined` marks additional ordering time. A skipped large table establishes infeasibility only for the observed ordering, not for every possible ordering or for a different DP implementation.

### main

| Instance | Variant | Columns | Obs. | w | p | Extra search | Distance | Dense seconds | Status |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| bb72_r6 | sector | 2232 | 12 | 61 | 61–62 |  | — | — | table_exceeds_4_GiB |
| bb90_r10 | sector | 4590 | 8 | 76 | 76–77 |  | — | — | table_exceeds_4_GiB |
| bb108_best_r6 | sector | 3348 | 8 | 93 | 93–94 |  | — | — | table_exceeds_4_GiB |
| bb108_r10 | sector | 5508 | 8 | 87 | 87–88 |  | — | — | table_exceeds_4_GiB |
| bb144_r12 | sector | 8784 | 12 | 103 | 103–104 |  | — | — | table_exceeds_4_GiB |
| bb288_r18 | sector | 26208 | 12 | 211 | 211–212 |  | — | — | table_exceeds_4_GiB |
| code_balanced_390 | full | 390 | 78 | 78 | 79–80 |  | — | — | table_exceeds_4_GiB |
| code_balanced_625 | full | 625 | 125 | 125 | 126–127 |  | — | — | table_exceeds_4_GiB |
| code_bb72 | full | 72 | 12 | 16 | 18 |  | 6 | 0.01 | exact |
| code_bb90 | full | 90 | 8 | 23 | 24 |  | 10 | 0.65 | exact |
| code_bb108 | full | 108 | 8 | 28 | 30 |  | 10 | 33.38 | exact |
| code_bb144 | full | 144 | 12 | 30 | 32 | refined | 12 | 417.4 | exact |
| code_bb288 | full | 288 | 12 | 68 | 69–70 | refined | — | — | table_exceeds_4_GiB |
| code_cornucopia_1044 | full | 1044 | 526 | 183 | 184–185 |  | — | — | table_exceeds_4_GiB |
| code_gala_132 | full | 132 | 30 | 41 | 41–42 |  | — | — | table_exceeds_4_GiB |
| code_kasai_372 | full | 372 | 130 | 98 | 99–100 |  | — | — | table_exceeds_4_GiB |
| code_kasai_444 | full | 444 | 154 | 119 | 120–121 |  | — | — | table_exceeds_4_GiB |
| code_kasai_492 | full | 492 | 170 | 128 | 129–130 |  | — | — | table_exceeds_4_GiB |
| code_llmbb_360 | full | 360 | 12 | 69 | 70–71 |  | — | — | table_exceeds_4_GiB |
| code_mm_324 | full | 324 | 12 | 87 | 88–89 |  | — | — | table_exceeds_4_GiB |
| code_sdbb_200 | full | 200 | 12 | 40 | 40–41 |  | — | — | table_exceeds_4_GiB |
| code_w8bb_144_6 | full | 144 | 6 | 46 | 47–48 |  | — | — | table_exceeds_4_GiB |
| color_d3 | full | 72 | 1 | 6 | 7 |  | 2 | <0.01 | exact |
| color_d5 | full | 1104 | 1 | 20 | 21 |  | 3 | 0.25 | exact |
| color_d7 | full | 3651 | 1 | 40 | 40–41 |  | — | — | table_exceeds_4_GiB |
| color_d9 | full | 7683 | 1 | 65 | 65–66 |  | — | — | table_exceeds_4_GiB |
| color_d11 | full | 16422 | 1 | 96 | 96–97 |  | — | — | table_exceeds_4_GiB |
| cornucopia_252 | sector | 8568 | 130 | 118 | 118–119 |  | — | — | table_exceeds_4_GiB |
| cornucopia_576 | sector | 19584 | 292 | 271 | 271–272 |  | — | — | table_exceeds_4_GiB |
| cornucopia_900 | sector | 30600 | 454 | 424 | 424–425 |  | — | — | table_exceeds_4_GiB |
| cornucopia_1044 | sector | 35496 | 526 | 492 | 492–493 |  | — | — | table_exceeds_4_GiB |
| gross_best_r6 | sector | 4464 | 12 | 116 | 116–117 |  | — | — | table_exceeds_4_GiB |
| lrgross | sector | 4464 | 12 | 98 | 98–99 |  | — | — | table_exceeds_4_GiB |
| mitten_150 | sector | 9750 | 30 | 83 | 83–84 |  | — | — | table_exceeds_4_GiB |
| mitten_200 | sector | 15560 | 40 | 149 | 149–150 |  | — | — | table_exceeds_4_GiB |
| mitten_300 | sector | 11820 | 60 | 153 | 153–154 |  | — | — | table_exceeds_4_GiB |
| routing_54 | sector | 1998 | 8 | 47 | 47–48 |  | — | — | table_exceeds_4_GiB |
| routing_90 | sector | 3330 | 8 | 69 | 69–70 |  | — | — | table_exceeds_4_GiB |
| routing_110 | sector | 4070 | 8 | 97 | 97–98 |  | — | — | table_exceeds_4_GiB |
| routing_140_13 | sector | 5180 | 8 | 124 | 124–125 |  | — | — | table_exceeds_4_GiB |
| routing_200_24 | sector | 11700 | 24 | 179 | 179–180 |  | — | — | table_exceeds_4_GiB |
| sdbb_64 | sector | 2752 | 8 | 54 | 54–55 |  | — | — | table_exceeds_4_GiB |
| sdbb_120 | sector | 5160 | 8 | 109 | 109–110 |  | — | — | table_exceeds_4_GiB |
| shift_120d | sector | 3720 | 8 | 99 | 99–100 |  | — | — | table_exceeds_4_GiB |
| star_42 | sector | 1806 | 6 | 38 | 38–39 |  | — | — | table_exceeds_4_GiB |
| surface_d3 | sector | 55 | 1 | 4 | 6 |  | 3 | <0.01 | exact |
| surface_d5 | sector | 301 | 1 | 13 | 15 |  | 5 | <0.01 | exact |
| surface_d7 | sector | 883 | 1 | 24 | 26 |  | 7 | 1.56 | exact |
| surface_d9 | sector | 1945 | 1 | 45 | 46–47 |  | — | — | table_exceeds_4_GiB |
| surface_d11 | sector | 3631 | 1 | 66 | 67–68 |  | — | — | table_exceeds_4_GiB |
| surface_d13 | sector | 6085 | 1 | 91 | 92–93 |  | — | — | table_exceeds_4_GiB |
| surface_d15 | sector | 9451 | 1 | 120 | 121–122 |  | — | — | table_exceeds_4_GiB |
| surface_d17 | sector | 13873 | 1 | 153 | 154–155 |  | — | — | table_exceeds_4_GiB |
| surface_d19 | sector | 19495 | 1 | 190 | 191–192 |  | — | — | table_exceeds_4_GiB |
| surface_d21 | sector | 26461 | 1 | 231 | 232–233 |  | — | — | table_exceeds_4_GiB |
| surface_d23 | sector | 34915 | 1 | 276 | 277–278 |  | — | — | table_exceeds_4_GiB |
| surface_d25 | sector | 45001 | 1 | 325 | 326–327 |  | — | — | table_exceeds_4_GiB |
| w8bb_72 | sector | 3096 | 14 | 62 | 62–63 |  | — | — | table_exceeds_4_GiB |
| w8bb_144_16 | sector | 6192 | 16 | 131 | 131–132 |  | — | — | table_exceeds_4_GiB |
| walkingcat_54 | sector | 2322 | 2 | 52 | 52–53 |  | — | — | table_exceeds_4_GiB |

### wjh

| Instance | Variant | Columns | Obs. | w | p | Extra search | Distance | Dense seconds | Status |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| wjh_bb72_circuit | sector | 2232 | 12 | 61 | 61–62 |  | — | — | table_exceeds_4_GiB |
| wjh_bb90_circuit | sector | 4590 | 8 | 76 | 76–77 |  | — | — | table_exceeds_4_GiB |
| wjh_bb108_circuit | sector | 5508 | 8 | 87 | 87–88 |  | — | — | table_exceeds_4_GiB |
| wjh_bb144_circuit | sector | 8784 | 12 | 103 | 103–104 |  | — | — | table_exceeds_4_GiB |
| wjh_bb288_circuit | sector | 26208 | 12 | 211 | 211–212 |  | — | — | table_exceeds_4_GiB |
| wjh_bb360_circuit | sector | 43560 | 12 | 282 | 283–284 |  | — | — | table_exceeds_4_GiB |
| wjh_bb756_circuit | sector | 129276 | 16 | 569 | 569–570 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n72 | full | 72 | 12 | 16 | 18 |  | 6 | 0.01 | exact |
| wjh_bb_n90 | full | 90 | 8 | 23 | 24 |  | 10 | 0.54 | exact |
| wjh_bb_n108 | full | 108 | 8 | 27 | 29 |  | 10 | 19.61 | exact |
| wjh_bb_n144 | full | 144 | 12 | 30 | 32 | refined | — | — | stopped_by_user |
| wjh_bb_n216 | full | 216 | 8 | 26 | 28 |  | 10 | 3.00 | exact |
| wjh_bb_n288 | full | 288 | 12 | 74 | 75–76 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n360 | full | 360 | 12 | 76 | 77–78 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n576 | full | 576 | 8 | 92 | 93–94 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n648 | full | 648 | 4 | 119 | 120–121 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n756 | full | 756 | 16 | 148 | 149–150 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n864 | full | 864 | 4 | 176 | 177–178 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n1080 | full | 1080 | 4 | 137 | 138–139 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n1152 | full | 1152 | 4 | 190 | 191–192 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n1296 | full | 1296 | 4 | 173 | 174–175 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n1728 | full | 1728 | 4 | 244 | 245–246 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n2016 | full | 2016 | 8 | 155 | 156–157 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n2160 | full | 2160 | 8 | 281 | 282–283 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n2520 | full | 2520 | 8 | 176 | 177–178 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n2592 | full | 2592 | 8 | 208 | 208–209 |  | — | — | table_exceeds_4_GiB |
| wjh_bb_n3024 | full | 3024 | 4 | 325 | 326–327 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_00_n4 | full | 4 | 2 | 1 | 2 |  | 2 | <0.01 | exact |
| wjh_hcc_01_n16 | full | 16 | 8 | 3 | 4 |  | 2 | <0.01 | exact |
| wjh_hcc_02_n32 | full | 32 | 12 | 8 | 9 |  | 4 | <0.01 | exact |
| wjh_hcc_03_n56 | full | 56 | 14 | 14 | 15 |  | 6 | <0.01 | exact |
| wjh_hcc_04_n56 | full | 56 | 14 | 14 | 15 |  | 4 | <0.01 | exact |
| wjh_hcc_05_n64 | full | 64 | 20 | 13 | 14 |  | 4 | <0.01 | exact |
| wjh_hcc_06_n112 | full | 112 | 28 | 24 | 25 |  | 6 | 4.98 | exact |
| wjh_hcc_07_n112 | full | 112 | 28 | 23 | 24 |  | 8 | 1.90 | exact |
| wjh_hcc_08_n120 | full | 120 | 30 | 25 | 26 |  | 8 | 13.54 | exact |
| wjh_hcc_09_n168 | full | 168 | 46 | 30 | 31 | refined | 6 | 318.3 | exact |
| wjh_hcc_10_n240 | full | 240 | 60 | 48 | 48–49 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_11_n256 | full | 256 | 68 | 46 | 46–47 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_12_n336 | full | 336 | 88 | 53 | 53–54 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_13_n336 | full | 336 | 88 | 62 | 62–63 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_14_n360 | full | 360 | 90 | 65 | 65–66 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_15_n512 | full | 512 | 132 | 87 | 87–88 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_16_n672 | full | 672 | 172 | 119 | 119–120 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_17_n720 | full | 720 | 184 | 119 | 119–120 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_18_n720 | full | 720 | 180 | 98 | 98–99 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_19_n816 | full | 816 | 204 | 142 | 142–143 |  | — | — | table_exceeds_4_GiB |
| wjh_hcc_20_n816 | full | 816 | 204 | 136 | 136–137 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_00_n6 | full | 6 | 1 | 2 | 3 |  | 2 | <0.01 | exact |
| wjh_hsc_01_n24 | full | 24 | 4 | 4 | 5 |  | 2 | <0.01 | exact |
| wjh_hsc_02_n48 | full | 48 | 6 | 8 | 10 |  | 3 | <0.01 | exact |
| wjh_hsc_03_n84 | full | 84 | 9 | 12 | 14 |  | 4 | <0.01 | exact |
| wjh_hsc_04_n84 | full | 84 | 9 | 12 | 14 |  | 3 | <0.01 | exact |
| wjh_hsc_05_n96 | full | 96 | 10 | 14 | 16 |  | 4 | <0.01 | exact |
| wjh_hsc_06_n168 | full | 168 | 16 | 21 | 23 |  | 4 | 0.23 | exact |
| wjh_hsc_07_n168 | full | 168 | 16 | 20 | 21 |  | 4 | 0.23 | exact |
| wjh_hsc_08_n180 | full | 180 | 17 | 22 | 24 |  | 5 | 0.69 | exact |
| wjh_hsc_09_n252 | full | 252 | 23 | 29 | 31 | refined | 4 | 138.1 | exact |
| wjh_hsc_10_n360 | full | 360 | 32 | 40 | 41–42 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_11_n384 | full | 384 | 34 | 42 | 43–44 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_12_n504 | full | 504 | 44 | 48 | 49–50 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_13_n504 | full | 504 | 44 | 54 | 55–56 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_14_n540 | full | 540 | 47 | 55 | 56–57 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_15_n768 | full | 768 | 66 | 78 | 79–80 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_16_n1008 | full | 1008 | 86 | 102 | 103–104 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_17_n1080 | full | 1080 | 92 | 105 | 106–107 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_18_n1080 | full | 1080 | 92 | 92 | 92–93 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_19_n1224 | full | 1224 | 104 | 122 | 123–124 |  | — | — | table_exceeds_4_GiB |
| wjh_hsc_20_n1224 | full | 1224 | 104 | 107 | 108–109 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj01 | full | 34 | 20 | 2 | 3 |  | 2 | <0.01 | exact |
| wjh_lp_aj04 | full | 136 | 32 | 24 | 26 |  | 4 | 5.88 | exact |
| wjh_lp_aj07 | full | 238 | 44 | 52 | 53–54 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj10 | full | 340 | 56 | 78 | 79–80 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj13 | full | 442 | 68 | 105 | 106–107 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj52 | full | 1768 | 224 | 404 | 405–406 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj58 | full | 1972 | 248 | 494 | 494–495 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj60 | full | 2040 | 256 | 526 | 527–528 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj61 | full | 2074 | 260 | 559 | 560–561 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj67 | full | 2278 | 284 | 561 | 562–563 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj73 | full | 2482 | 308 | 687 | 688–689 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj80 | full | 2720 | 336 | 744 | 745–746 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj85 | full | 2890 | 356 | 793 | 794–795 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_aj95 | full | 3230 | 396 | 893 | 894–895 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_pk31 | full | 1054 | 140 | 264 | 265–266 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_xu16 | full | 544 | 80 | 131 | 132–133 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_xu21 | full | 714 | 100 | 175 | 176–177 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_xu30 | full | 1020 | 136 | 250 | 251–252 |  | — | — | table_exceeds_4_GiB |
| wjh_lp_xu42 | full | 1428 | 184 | 404 | 405–406 |  | — | — | table_exceeds_4_GiB |
| wjh_midout_d3 | sector | 33 | 1 | 3 | 5 |  | 2 | <0.01 | exact |
| wjh_midout_d5 | sector | 171 | 1 | 8 | 9 |  | 3 | <0.01 | exact |
| wjh_midout_d7 | sector | 475 | 1 | 15 | 16 |  | 4 | <0.01 | exact |
| wjh_midout_d9 | sector | 1041 | 1 | 22 | 23 |  | 5 | 0.50 | exact |
| wjh_midout_d11 | sector | 1907 | 1 | 31 | 32 | refined | — | — | stopped_by_user |
| wjh_qt_36_8_4 | full | 36 | 8 | 9 | 10 |  | 4 | <0.01 | exact |
| wjh_qt_72_8_8 | full | 72 | 8 | 17 | 18 |  | 8 | 0.01 | exact |
| wjh_qt_108_2_12 | full | 108 | 2 | 25 | 26 |  | 12 | 0.81 | exact |
| wjh_qt_144_2_13 | full | 144 | 2 | 40 | 41–42 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_180_2_17 | full | 180 | 2 | 46 | 47–48 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_216_4_18 | full | 216 | 4 | 46 | 47–48 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_252_2_21 | full | 252 | 2 | 70 | 71–72 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_288_2_24 | full | 288 | 2 | 77 | 77–78 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_324_4_25 | full | 324 | 4 | 81 | 82–83 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_360_4_24 | full | 360 | 4 | 97 | 98–99 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_396_4_26 | full | 396 | 4 | 89 | 89–90 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_432_8_33 | full | 432 | 8 | 111 | 112–113 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_468_4_31 | full | 468 | 4 | 106 | 107–108 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_496_2_32 | full | 496 | 2 | 109 | 110–111 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_504_2_45 | full | 504 | 2 | 131 | 132–133 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_540_4_40 | full | 540 | 4 | 140 | 141–142 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_576_2_57 | full | 576 | 2 | 149 | 150–151 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_576_2_59 | full | 576 | 2 | 149 | 150–151 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_612_2_52 | full | 612 | 2 | 154 | 155–156 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_648_10_71 | full | 648 | 10 | 161 | 162–163 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_648_14_50 | full | 648 | 14 | 156 | 156–157 |  | — | — | table_exceeds_4_GiB |
| wjh_qt_684_2_29 | full | 684 | 2 | 96 | 97–98 |  | — | — | table_exceeds_4_GiB |
| wjh_superdense_d3 | sector | 70 | 1 | 5 | 7 |  | 3 | <0.01 | exact |
| wjh_superdense_d5 | sector | 414 | 1 | 14 | 15 |  | 5 | <0.01 | exact |
| wjh_superdense_d7 | sector | 1248 | 1 | 24 | 25 |  | 7 | 2.17 | exact |
| wjh_superdense_d9 | sector | 2788 | 1 | 38 | 38–39 |  | — | — | table_exceeds_4_GiB |
| wjh_superdense_d11 | sector | 5250 | 1 | 54 | 54–55 |  | — | — | table_exceeds_4_GiB |
| wjh_superdense_mpp_d15 | sector | 169 | 1 | 12 | 13 |  | 15 | <0.01 | exact |
| wjh_surface_d3 | sector | 55 | 1 | 4 | 6 |  | 3 | <0.01 | exact |
| wjh_surface_d5 | sector | 301 | 1 | 13 | 14 |  | 5 | <0.01 | exact |
| wjh_surface_d7 | sector | 883 | 1 | 25 | 27 |  | 7 | 1.66 | exact |
| wjh_surface_d9 | sector | 1945 | 1 | 41 | 42–43 |  | — | — | table_exceeds_4_GiB |
| wjh_surface_d11 | sector | 3631 | 1 | 61 | 61–62 |  | — | — | table_exceeds_4_GiB |

## Collapsed relaxations

| Instance | Variant | Columns | Obs. | w | p | Extra search | Distance | Dense seconds | Status |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| bb72_r6 | collapsed | 180 | 12 | 26 | 28 |  | 5 | 18.54 | exact |
| bb90_r10 | collapsed | 225 | 8 | 34 | 35 | refined | — | — | table_exceeds_4_GiB |
| bb108_best_r6 | collapsed | 270 | 8 | 40 | 41–42 |  | — | — | table_exceeds_4_GiB |
| bb108_r10 | collapsed | 270 | 8 | 40 | 41–42 |  | — | — | table_exceeds_4_GiB |
| bb144_r12 | collapsed | 360 | 12 | 51 | 52–53 |  | — | — | table_exceeds_4_GiB |
| bb288_r18 | collapsed | 720 | 12 | 97 | 98–99 |  | — | — | table_exceeds_4_GiB |
| cornucopia_252 | collapsed | 819 | 130 | 59 | 59–60 |  | — | — | table_exceeds_4_GiB |
| cornucopia_576 | collapsed | 1872 | 292 | 136 | 136–137 |  | — | — | table_exceeds_4_GiB |
| cornucopia_900 | collapsed | 2925 | 454 | 211 | 211–212 |  | — | — | table_exceeds_4_GiB |
| cornucopia_1044 | collapsed | 3393 | 526 | 247 | 248–249 |  | — | — | table_exceeds_4_GiB |
| gross_best_r6 | collapsed | 360 | 12 | 50 | 51–52 |  | — | — | table_exceeds_4_GiB |
| lrgross | collapsed | 360 | 12 | 52 | 53–54 |  | — | — | table_exceeds_4_GiB |
| mitten_150 | collapsed | 510 | 30 | 58 | 59–60 |  | — | — | table_exceeds_4_GiB |
| mitten_200 | collapsed | 680 | 40 | 78 | 78–79 |  | — | — | table_exceeds_4_GiB |
| mitten_300 | collapsed | 1020 | 60 | 112 | 112–113 |  | — | — | table_exceeds_4_GiB |
| routing_54 | collapsed | 162 | 8 | 19 | 20 |  | 4 | 0.06 | exact |
| routing_90 | collapsed | 270 | 8 | 35 | 36–37 | refined | — | — | table_exceeds_4_GiB |
| routing_110 | collapsed | 330 | 8 | 41 | 42–43 |  | — | — | table_exceeds_4_GiB |
| routing_140_13 | collapsed | 420 | 8 | 54 | 55–56 |  | — | — | table_exceeds_4_GiB |
| routing_200_24 | collapsed | 900 | 24 | 80 | 80–81 |  | — | — | table_exceeds_4_GiB |
| sdbb_64 | collapsed | 224 | 8 | 26 | 27 |  | 4 | 15.05 | exact |
| sdbb_120 | collapsed | 420 | 8 | 50 | 51–52 |  | — | — | table_exceeds_4_GiB |
| shift_120d | collapsed | 1633 | 8 | 51 | 51–52 |  | — | — | table_exceeds_4_GiB |
| star_42 | collapsed | 147 | 6 | 18 | 19 |  | 4 | 0.03 | exact |
| surface_d3 | collapsed | 9 | 1 | 2 | 4 |  | 3 | <0.01 | exact |
| surface_d5 | collapsed | 29 | 1 | 3 | 5 |  | 5 | <0.01 | exact |
| surface_d7 | collapsed | 61 | 1 | 4 | 6 |  | 7 | <0.01 | exact |
| surface_d9 | collapsed | 105 | 1 | 5 | 7 |  | 9 | <0.01 | exact |
| surface_d11 | collapsed | 161 | 1 | 7 | 8 |  | 11 | <0.01 | exact |
| surface_d13 | collapsed | 229 | 1 | 8 | 9 |  | 13 | <0.01 | exact |
| surface_d15 | collapsed | 309 | 1 | 9 | 10 |  | 15 | <0.01 | exact |
| surface_d17 | collapsed | 401 | 1 | 10 | 11 |  | 17 | <0.01 | exact |
| surface_d19 | collapsed | 505 | 1 | 11 | 12 |  | 19 | <0.01 | exact |
| surface_d21 | collapsed | 621 | 1 | 13 | 14 |  | 21 | <0.01 | exact |
| surface_d23 | collapsed | 749 | 1 | 14 | 15 |  | 23 | <0.01 | exact |
| surface_d25 | collapsed | 889 | 1 | 16 | 17 |  | 25 | <0.01 | exact |
| w8bb_72 | collapsed | 252 | 14 | 28 | 30 |  | 4 | 83.02 | exact |
| w8bb_144_16 | collapsed | 504 | 16 | 51 | 52–53 |  | — | — | table_exceeds_4_GiB |
| walkingcat_54 | collapsed | 189 | 2 | 26 | 27 |  | 6 | 1.52 | exact |
| wjh_bb72_circuit | collapsed | 180 | 12 | 26 | 28 |  | 5 | 18.79 | exact |
| wjh_bb90_circuit | collapsed | 225 | 8 | 34 | 36 |  | — | — | table_exceeds_4_GiB |
| wjh_bb108_circuit | collapsed | 270 | 8 | 40 | 41–42 |  | — | — | table_exceeds_4_GiB |
| wjh_bb144_circuit | collapsed | 360 | 12 | 51 | 52–53 |  | — | — | table_exceeds_4_GiB |
| wjh_bb288_circuit | collapsed | 720 | 12 | 97 | 98–99 |  | — | — | table_exceeds_4_GiB |
| wjh_bb360_circuit | collapsed | 900 | 12 | 101 | 102–103 |  | — | — | table_exceeds_4_GiB |
| wjh_bb756_circuit | collapsed | 1890 | 16 | 211 | 212–213 |  | — | — | table_exceeds_4_GiB |
| wjh_midout_d3 | collapsed | 14 | 1 | 3 | 4 |  | 2 | <0.01 | exact |
| wjh_midout_d5 | collapsed | 43 | 1 | 5 | 7 |  | 3 | <0.01 | exact |
| wjh_midout_d7 | collapsed | 85 | 1 | 7 | 9 |  | 4 | <0.01 | exact |
| wjh_midout_d9 | collapsed | 145 | 1 | 10 | 12 |  | 5 | <0.01 | exact |
| wjh_midout_d11 | collapsed | 217 | 1 | 13 | 15 |  | 6 | <0.01 | exact |
| wjh_superdense_d3 | collapsed | 10 | 1 | 3 | 4 |  | 2 | <0.01 | exact |
| wjh_superdense_d5 | collapsed | 34 | 1 | 4 | 6 |  | 3 | <0.01 | exact |
| wjh_superdense_d7 | collapsed | 73 | 1 | 6 | 8 |  | 4 | <0.01 | exact |
| wjh_superdense_d9 | collapsed | 127 | 1 | 7 | 9 |  | 5 | <0.01 | exact |
| wjh_superdense_d11 | collapsed | 196 | 1 | 9 | 11 |  | 6 | <0.01 | exact |
| wjh_superdense_mpp_d15 | collapsed | 169 | 1 | 12 | 13 |  | 15 | <0.01 | exact |
| wjh_surface_d3 | collapsed | 9 | 1 | 2 | 4 |  | 3 | <0.01 | exact |
| wjh_surface_d5 | collapsed | 29 | 1 | 3 | 5 |  | 5 | <0.01 | exact |
| wjh_surface_d7 | collapsed | 61 | 1 | 4 | 6 |  | 7 | <0.01 | exact |
| wjh_surface_d9 | collapsed | 105 | 1 | 5 | 7 |  | 9 | <0.01 | exact |
| wjh_surface_d11 | collapsed | 161 | 1 | 7 | 8 |  | 11 | <0.01 | exact |

## Fixtures

| Instance | Variant | Columns | Obs. | w | p | Extra search | Distance | Dense seconds | Status |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| fx_bb72_code | full | 72 | 12 | 16 | 18 |  | 6 | 0.01 | exact |
| fx_sdbb16_r3 | collapsed | 56 | 4 | 6 | 7 |  | 2 | <0.01 | exact |
| fx_sdbb16_r3 | sector | 352 | 4 | 14 | 15 |  | 4 | <0.01 | exact |

## Validation and retained evidence

- All 188 reconstructed instances reproduce their stored dimensions. All 126 WJH source checksums match the repository metadata, including the complete exported CSS-code dataset.
- All 211 available tested historical witnesses satisfy the reconstructed H/L problems. Their original column indices are retained.
- The unmodified kernel passes 3000 random comparisons against exhaustive enumeration and 40 additional dense C-versus-NumPy comparisons.
- Completed results are checked against metadata ground truth and independently stored exact solver results whenever available. The dense kernel returns values, not witness vectors.
- Costs are uint8 with 255 as infinity. All finite distances reported here are below 255. This implementation cannot distinguish infeasibility from a minimum of 255 or greater.

The result directory contains `inputs/` (compressed H/L, metadata, checksums and rebuilt circuits), `widths/` (baseline trials, permutations and profiles), `refinements/`, `geometry/`, `runs/` (every observable, timing, RSS and reference checks), `summary.json`, and validation records.

External inputs were reconstructed from the versions documented in the repository: [codeDistancePYPI a4afe9c](https://github.com/m-webster/codeDistancePYPI/tree/a4afe9c), [yarn 1b58edd](https://github.com/a7b/yarn/tree/1b58edd), and [Kasai's data page](https://kasai.ict.eng.isct.ac.jp/pair_partition_cpm_css_codes_20260714.html). The inputs needed to repeat the DP are retained locally; external downloads are not required for replay.

## Reproduction

From the repository root, using the prepared Python environment:

```sh
python scripts/dense_audit.py widths --out results/dense_audit_20261021 --jobs 4
python scripts/dense_audit.py run --out results/dense_audit_20261021 --max-bits 32 --seconds 1200
python scripts/summarize_dense_audit.py --out results/dense_audit_20261021 --report docs/DENSE_DP_AUDIT.md
```

Completed records are cached. To obtain a new independent run, use a new output directory with copies of the retained inputs and selected width/refinement files. The saved permutations permit exact DP replay without relying on a wall-time-limited ordering search to rediscover them.
