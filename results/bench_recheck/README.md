# First tier rerun with one code and at one time (23 October 2026)

## Why

The first dp=2 pass on the main suite (`results/bench/ours_pipeline__dp-2`, 23 October) differed from the dp=1
pass of 22 October (`results/bench/ours_pipeline__dp-1`):
- it lost color_d11 full;
- 9 records were slower.

There were two candidate causes besides the machine's load:
1. **The probe of the sparse stage.** On star_42 it took 10.6 s, against 0.7 s for the search. Commit 8ec918b
   makes it measure weight 3 only where that is cheap next to the predicted sweep.
2. **The table budget fix of 7ef27aa** (main, 22 October 19:12), which came after the dp=1 pass. Since then, the
   pipeline's worker builds its lookup tables as deep as half the memory limit allows (8 GiB in this tier).
   Before, they were silently held to 1 GiB. 19 records of the main suite get a deeper table.

## What ran

- Code 8ec918b on 5090 (`~/claude_runs/sparse_dp/repo4`), 23 October 12:04-12:30 (UTC+8).
- Cores 160-191, one job per core. The second tier of dp=2 ran on cores 0-159 at the same time.
- 1 thread, 600 s, 16 GB, no give-up.
- Scripts: `scripts/server/dp2_recheck.sh`, `dp2_recheck_pairs.sh`, `dp1_table1gb.sh`. The server run wrote this
  folder as `results/bench_dp1_current` (and `results/bench_recheck` for the 1 GiB runs); those are the paths
  inside the records.

Folders:

| folder | configuration | records |
|---|---|---|
| `ours_pipeline__dp-1` | dp=1 | the 14 whose sparse stage runs the probe (10 main suite, 4 superdense circuits of arXiv:2603.22532) and the 19 whose tables got deeper |
| `ours_pipeline__dp-2` | dp=2 | the 19 whose tables got deeper |
| `ours_pipeline__dp-1__table%5Fgb-1` | dp=1 with `table_gb=1` (1 GiB tables, as before 7ef27aa) | the 11 solved ones of the 19 |

dp=2's reruns of the 14 probe records replaced its first pass in `results/bench/ours_pipeline__dp-2` and
`results/bench_wjh/ours_pipeline__dp-2`. They ran on cores 174-177 in the same half hour.

## Table

`python bench/compare_dp2.py`, section "First tier rerun with one code and at one time":

| instance variant | dp=1, 22 Oct | dp=1, 1 GiB tables | dp=1 | dp=2 | dp=2: sparse stage | dp=2: probe |
|---|---:|---:|---:|---:|---|---|
| bb288_r18 full | timeout 14.. |  | timeout 14.. | timeout 14.. |  |  |
| bb288_r18 sector | timeout 14.. |  | timeout 14.. | timeout 14.. |  |  |
| color_d11 full | 236 s | 244 s | timeout 5.. | timeout 5.. |  |  |
| cornucopia_252 full | 3.1 s | 3.5 s | 8.3 s | 8.3 s |  |  |
| cornucopia_252 sector | 2.2 s | 2.4 s | 7.3 s | 7.3 s |  |  |
| fx_sdbb16_r3 full | 0.2 s |  | 0.2 s | 0.3 s | search (finished within its head start of 0.1 s) | 0.02 s (weights 2/2) |
| fx_sdbb16_r3 sector | 0.2 s |  | 0.2 s | 0.2 s | search (finished within its head start of 0.1 s) | 0.02 s (weights 2/2) |
| mitten_200 full | timeout 8.. |  | timeout 9.. | timeout 9.. |  |  |
| mitten_200 sector | timeout 8.. |  | timeout 9.. | timeout 9.. |  |  |
| mitten_300 full | timeout 9.. |  | timeout 9.. | timeout 9.. |  |  |
| mitten_300 sector | timeout 9.. |  | timeout 9.. | timeout 9.. |  |  |
| routing_200_24 full | timeout 9..10 |  | timeout 9..10 | timeout 9..10 | search (cut rank above the row slots of the sparse tables) |  |
| routing_200_24 sector | timeout 9..10 |  | timeout 9..10 | timeout 9..10 | search (cut rank above the row slots of the sparse tables) |  |
| routing_54 full | 0.9 s |  | 1.0 s | 1.7 s | search (finished within its head start of 5.6 s) | 0.29 s (weights 2/2) |
| routing_54 sector | 0.9 s |  | 1.2 s | 1.5 s | search (finished within its head start of 5.6 s) | 0.29 s (weights 2/2) |
| sdbb_64 full | 4.0 s |  | 4.3 s | 6.3 s | search (finished within its head start of 137.9 s) | 1.48 s (weights 3/2) |
| sdbb_64 sector | 3.9 s |  | 4.3 s | 6.2 s | search (finished within its head start of 138.0 s) | 1.49 s (weights 3/2) |
| star_42 full | 0.8 s |  | 0.9 s | 1.2 s | search (finished within its head start of 3.8 s) | 0.27 s (weights 2/2) |
| star_42 sector | 0.7 s |  | 0.8 s | 1.2 s | search (finished within its head start of 3.8 s) | 0.27 s (weights 2/2) |
| surface_d21 full | 5.2 s | 5.6 s | 8.0 s | 8.3 s |  |  |
| surface_d21 sector | 1.8 s | 1.9 s | 4.2 s | 4.2 s |  |  |
| surface_d23 full | 8.9 s | 10.3 s | 13.7 s | 13.9 s |  |  |
| surface_d23 sector | 2.6 s | 2.5 s | 7.3 s | 7.8 s |  |  |
| surface_d25 full | 18.1 s | 19.1 s | 26.3 s | 27.8 s |  |  |
| surface_d25 sector | 7.2 s | 7.5 s | 16.9 s | 17.4 s |  |  |
| w8bb_144_16 full | 164 s | 169 s | 174 s | 176 s | search (cut rank above the row slots of the sparse tables) |  |
| w8bb_144_16 sector | 163 s | 169 s | 173 s | 178 s | search (cut rank above the row slots of the sparse tables) |  |
| walkingcat_54 full | 6.9 s |  | 7.3 s | 8.0 s | search (the sparse DP would exceed the table budget) | 0.46 s (weights 2/2) |
| walkingcat_54 sector | 6.8 s |  | 7.3 s | 7.9 s | search (the sparse DP would exceed the table budget) | 0.46 s (weights 2/2) |
| wjh_superdense_d11 sector | timeout 8..11 |  | timeout 8..11 | timeout 8..11 | search (the sparse DP would exceed the table budget) | 0.46 s (weights 2/2) |
| wjh_superdense_d5 sector | 0.2 s |  | 0.2 s | 0.3 s | search (finished within its head start of 0.0 s) | 0.04 s (weights 2/2) |
| wjh_superdense_d7 sector | 3.3 s |  | 3.5 s | 0.7 s | sparse DP, K = 6 (0.2 s) | 0.07 s (weights 2/2) |
| wjh_superdense_d9 sector | 375 s |  | 390 s | 17.0 s | sparse DP, K = 8 (6.5 s) | 1.89 s (weights 3/3) |

## Findings

**The deeper tables of 7ef27aa make the search slower, for dp=1 and dp=2 alike.** These pairs ran side by
side.
- color_d11 full is lost: 244 s with 1 GiB tables, a timeout at 5.. with 8 GiB. Its full detector error model
  has 16,422 columns, so the weight-2 table now built takes 4.8 GB. With it, the search at weight 4 took 52.9 s
  in the first dp=2 pass, against 3.3 s with the weight-1 table (dp=1, 22 October).
- The time-collapsed problems of cornucopia_252 and of surface d = 21-25 get weight-3 tables:
  - their sector problems take 2.2-3x as long (cornucopia_252 2.4 s → 7.3 s, surface d = 23 2.5 s → 7.3 s);
  - their full problems take 1.3-2.4x as long.
- w8bb_144_16 gains nothing (169 s → 173 s). The deeper tables of bb288_r18, mitten and routing_200_24 settle
  nothing in this tier. mitten_200 ends at the lower bound 9 instead of 8.

These differences are not dp=2's. They apply to the default configuration as well: its records and dp=1's, on
the main suite and on the instances of arXiv:2603.22532, predate 7ef27aa, so they all ran with 1 GiB tables.

**dp=2's own cost on the main suite is its probe.**
- About 0.3 s on star_42, routing_54 and walkingcat_54 (both variants), with weight 2 only.
- About 2 s on sdbb_64 (4.3 s → 6.2 s, 1.45x). There the weight-3 probe of the forward direction (about 1 s) lowers
  the predicted sweep from 1,103 s to 306 s. That would decide the race if the search were slow, but here it
  finishes within its head start.
- Nothing is lost. The sparse DP never sweeps on the main suite, whose 102 records split as follows:

  | what happened | records |
  |---|---:|
  | settled by the earlier circuit stages | 40 |
  | timed out before the sparse stage | 11 |
  | sector too wide for the sparse tables (cut rank above 56) | 19 |
  | code instances, or circuits without sectors (run as with dp=1) | 22 |
  | the probe ran, and the search finished first or the sweep would not fit | 10 |

**dp=2's gains are on the superdense colour-code circuits:** d = 7 3.5 s → 0.7 s, d = 9 390 s → 17.0 s. d = 11
stays open in this tier: weight 2 already predicts 118 GB, 14 times the table budget, so the probe stops there
(0.46 s; it took 7.9 s before 8ec918b).
