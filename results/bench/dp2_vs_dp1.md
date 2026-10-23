# The pipeline with the sparse Rank DP (dp=2) against dp=1: main suite, first tier

Records: `ours_pipeline__dp-2/` (23 October) and `ours_pipeline__dp-1/` (22 October).

Setup:
- The 102 instance variants of the main suite.
- First-tier limits, as in the dp=1 pass: one thread, 600 s, 16 GB, give-up after 2 (`bench/tier_b.py dp2`).
- 5090, 18 jobs on cores 96-113, 23 October from 10:10 to 10:37 (UTC+8).
- Code:
  - commit 6798b88;
  - the 10 records whose sparse stage runs its probe were rerun with 8ec918b, which measures weight 3 only where
    that is cheap next to the predicted sweep (`results/bench_recheck`);
  - the other records never reach the probe, so they stand for 8ec918b too.

`python bench/compare_dp.py results/bench --a ours_pipeline__dp-1 --b ours_pipeline__dp-2` lists the variants that
changed by more than 1.5x and 1 s, or in outcome:

| instance variant | ours_pipeline__dp-1 | ours_pipeline__dp-2 | ratio | DP on main problem | DP on collapsed problem | sparse DP |
|---|---|---|---:|---|---|---|
| color_d11 full | exact 235.8 s | timeout 5.. |  | search (w=96) |  |  |
| cornucopia_252 full | exact 3.1 s | exact 7.3 s | 0.42 | search (w=118) | search (w=59) |  |
| cornucopia_252 sector | exact 2.2 s | exact 6.2 s | 0.36 | search (w=118) | search (w=59) |  |
| sdbb_64 full | exact 4.0 s | exact 6.3 s | 0.64 | search (w=54) | search (w=27) | search (finished within its head start of 137.9 s) |
| sdbb_64 sector | exact 3.9 s | exact 6.2 s | 0.64 | search (w=54) | search (w=27) | search (finished within its head start of 138.0 s) |
| surface_d21 sector | exact 1.8 s | exact 3.7 s | 0.48 | search (w=231) | dp (w=16) |  |
| surface_d23 sector | exact 2.6 s | exact 6.7 s | 0.39 | search | dp (w=15) |  |
| surface_d25 sector | exact 7.2 s | exact 15.0 s | 0.48 | search | dp (w=16) |  |

102 variants with both records: 0 solved only with dp=2, 1 only with dp=1; of those solved by both, none faster
with dp=2, 7 slower.

**Apart from sdbb_64, none of these changes comes from dp=2.** The sparse DP never sweeps on this suite:
- On 40 variants the earlier circuit stages settle the sector.
- 11 time out before the sparse stage.
- 19 have a sector too wide for the sparse tables (cut rank above 56).
- 22 are codes or circuits without sectors, which run as with dp=1.
- On the remaining 10 the probe runs, and then the search finishes within its head start, or the sweep would not
  fit.

**The loss of color_d11 full and the slower cornucopia_252 and surface d = 21-25 come from main's table budget fix
(7ef27aa).** That commit came after the dp=1 pass and lets the pipeline build its lookup tables one level deeper,
up to half the memory limit instead of 1 GiB. A rerun of these records with one code and at one time
(`results/bench_recheck/README.md`) shows:
- dp=1 and dp=2 take the same time on them: cornucopia_252 sector 7.3 s and 7.3 s, surface d = 25 sector 16.9 s
  and 17.4 s;
- with 1 GiB tables, dp=1 is back to its times of 22 October: cornucopia_252 sector 2.4 s;
- color_d11 full is solved in 244 s with 1 GiB tables and times out with the weight-2 table of 4.8 GB that the
  larger budget now allows.

**dp=2's own cost is its probe:** up to 2 s, on sdbb_64 (4.3 s → 6.2 s side by side, 1.45x). There the weight-3
probe of the forward direction lowers the predicted sweep from 1,103 s to 306 s, which only matters when the search
is slow. On star_42, routing_54 and walkingcat_54 the probe stops at weight 2 and costs about 0.3 s. Before
8ec918b it measured weight 3 there too: 10.6 s on star_42, whose search takes 0.7 s.
