# The pipeline with the sparse Rank DP (dp=2) against dp=1: main suite, first tier

Records: `ours_pipeline__dp-2/` (23 October) and `ours_pipeline__dp-1/` (22 October).

Setup:
- The 102 instance variants of the main suite.
- First-tier limits, as in the dp=1 pass: one thread, 600 s, 16 GB, give-up after 2 (`bench/tier_b.py dp2`).
- 5090, 18 jobs on cores 96-113, 23 October from 10:10 to 10:37 (UTC+8).
- Code:
  - commit 6798b88;
  - the 10 records whose sparse stage runs its probe were rerun with 8ec918b. That commit measures weight 3 only
    where that is cheap next to the predicted sweep (`results/bench_recheck`);
  - the 19 records whose lookup tables got deeper with main's table budget fix 7ef27aa were rerun under the depth
    rule of c030477 (`scripts/server/rule_reruns.sh`, cores 96-114, 23 October 16:50, `results/table_depth`);
  - the other records never reach the probe and build the same tables, so they stand for c030477 too.

`python bench/compare_dp.py results/bench --a ours_pipeline__dp-1 --b ours_pipeline__dp-2` lists the variants that
changed by more than 1.5x and 1 s, or in outcome:

| instance variant | ours_pipeline__dp-1 | ours_pipeline__dp-2 | ratio | DP on main problem | DP on collapsed problem | sparse DP |
|---|---|---|---:|---|---|---|
| sdbb_64 full | exact 4.0 s | exact 6.3 s | 0.64 | search (w=54) | search (w=27) | search (finished within its head start of 137.9 s) |
| sdbb_64 sector | exact 3.9 s | exact 6.2 s | 0.64 | search (w=54) | search (w=27) | search (finished within its head start of 138.0 s) |

102 variants with both records: 0 solved only with dp=2, 0 only with dp=1; of those solved by both, none faster
with dp=2, 2 slower.

**dp=2 solves what dp=1 solves.** The sparse DP never sweeps on this suite:
- On 40 variants the earlier circuit stages settle the sector.
- 11 time out before the sparse stage.
- 19 have a sector too wide for the sparse tables (cut rank above 56).
- 22 are codes or circuits without sectors, which run as with dp=1.
- On the remaining 10 the probe runs, and then the search finishes within its head start, or the sweep would not
  fit.

In the first pass, 19 records were slower or lost: color_d11 full timed out, cornucopia_252 and surface d = 21-25
took 2-3x as long. That came from main's table budget fix (7ef27aa), which landed between the dp=1 and dp=2
passes and built the lookup tables as deep as half the memory limit allows:
- the recheck, side by side, is in `results/bench_recheck/README.md`;
- the depth rule that replaced it is in `results/table_depth/README.md`.

Rerun under the rule, these records are back to the dp=1 times:
- color_d11 full: 246 s, against 236 s;
- cornucopia_252 sector 2.2 s, surface d = 23 sector 2.5 s;
- w8bb_144_16: 165 s, against 154 s with the deep table up front and 163 s with dp=1.

**dp=2's own cost is its probe:** up to 2 s, on sdbb_64 (4.3 s → 6.2 s side by side, 1.45x). There the weight-3
probe of the forward direction lowers the predicted sweep from 1,103 s to 306 s, which only matters when the search
is slow. On star_42, routing_54 and walkingcat_54 the probe stops at weight 2, and the sparse stage costs
0.3-0.7 s. Before 8ec918b it measured weight 3 there too: 10.6 s on star_42, whose search takes 0.7 s.

## Second tier (32 threads, 90 GB, 3600 s), against the default configuration

Records: `results/bench_tierB/ours_pipeline__dp-2`.
- The second tier of dp=2 ran on what its first tier left (`bench/tier_b.py dp2b`): the circuits' sector problems
  and the codes, 3 jobs on cores 0-95 of 5090, 23 October 11:45-13:00 (UTC+8), code of 6798b88.
- None of these runs reaches the sparse stage's probe, so they stand for 8ec918b too.
- In that chain, give-up 1 skipped mitten_200 after mitten_300's timeout. mitten_200 then ran on its own
  (`scripts/server/dp2_tier2_mitten200.sh`, 8ec918b, cores 160-191), as the default's record of it did on 5 October.

The default's records are `results/bench_tierB/ours_pipeline`.
- From 4 to 22 October, they predate 7ef27aa, so they ran with 1 GiB lookup tables.
- mitten_200 was rerun on 23 October under the depth rule of c030477 (`scripts/server/rule_reruns.sh`, cores
  0-31).
- dp=2's second-tier records ran with 45 GiB of tables up front (7ef27aa), not yet under the rule.


| instance variant | default, tier 2 | dp=2, tier 2 |
|---|---:|---:|
| bb288_r18 sector | 242 s | 215 s |
| code_balanced_625 full | 47.2 s | 50.4 s |
| code_kasai_444 full | 57.5 s | 61.0 s |
| code_kasai_492 full | 776 s | 797 s |
| code_llmbb_360 full | 54.9 s | 56.9 s |
| cornucopia_1044 sector | 881 s | 919 s |
| cornucopia_900 sector | 485 s | 507 s |
| mitten_200 sector | 148 s (1038 s before the rule) | 144 s |
| mitten_300 sector | timeout 11.. | timeout 11.. |
| routing_140_13 sector | 103 s | 88.3 s |
| routing_200_24 sector | 477 s | 492 s |
| sdbb_120 sector | 1117 s | 1088 s |
| surface_d23 sector | 23.7 s | (solved in tier 1) |
| surface_d25 sector | 196 s | (solved in tier 1) |

- surface d = 23 and 25: the default's second-tier records come from the rerun of 22 October after the lift fix. dp=2
  solves both in its first tier, through the dense DP of dp=1.
- **mitten_200: 1,038 s → 144 s with dp=2, and 148 s for the default rerun under the rule.** This is the deeper
  table, not the sparse DP:
  - the time-collapsed problem (680 columns) gets its weight-3 table, and the collapsed search at weight 9 takes
    100 s instead of 965 s;
  - under the rule the default switches to that table after a trial at weight 8;
  - in the first tier the same table lifts mitten_200's lower bound from 8 to 9.
- The others agree within 15%. In this tier the sparse stage is either not reached, or the sector is too wide for
  the sparse tables (cut rank above 56).

Solved on the main suite, by its main problem (`bench/compare_dp2.py`):

| configuration | instances | tier 1 | tiers 1 and 2 |
|---|---:|---:|---:|
| ours | 60 | 47 | 59 |
| ours + DP | 60 | 48 | (tier 1 only) |
| ours + sparse DP | 60 | 48 | 59 |

The two configurations solve the same 59 instances. dp=2 needs the second tier for one fewer: surface d = 25, which
dp=1's dense DP settles in the first tier. Before the rerun under the rule, dp=2 lost color_d11 full in the first
tier, and a circuit without a sector problem gets no second tier (`bench/tier_b.py`, `unsolved`).
