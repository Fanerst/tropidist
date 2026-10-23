# The pipeline with the sparse Rank DP (dp=2) against dp=1: instances of arXiv:2603.22532, first tier

Records: `ours_pipeline__dp-2/` (23 October) and `ours_pipeline__dp-1/` (22 October).

Setup:
- All 126 instances: the 23 circuits on their sector problem, the 103 codes on their full problem.
- First-tier limits, the flags of the dp=1 pass (`scripts/server/dp_pass.sh`): one thread, 600 s, 16 GB,
  give-up after 2.
- 5090, cores of socket 1, 23 October.
- Code:
  - the circuits ran with commit 7c38b1f, the codes with 6798b88 (`bench/tier_b.py dp2`);
  - the four superdense circuits whose sparse stage runs its probe (d = 5 to 11) were rerun with 8ec918b, which
    measures weight 3 only where that is cheap next to the predicted sweep (`results/bench_recheck`);
  - the bb288 and bb360 circuits were rerun under the lookup-table depth rule of c030477
    (`scripts/server/rule_reruns.sh`, `results/table_depth`). They had run with deeper tables than the rule builds
    up front, and both still time out at the lower bound 14;
  - the other circuits never reach the probe and build the same tables, so their records stand for c030477 too.

What dp=2 adds: `bench/adapters/ours_pipeline.py`.
- The circuit stages (collapse, lift, window) leave a gap [l, u) on the sector.
- The search then runs for the sparse DP's predicted time; one meet-in-the-middle sweep at u − 1 decides.
- Prediction: `cdist.auto.sparse_estimate`, from probe sweeps.
- Code instances run as with dp=1.

`python bench/compare_dp.py results/bench_wjh --a ours_pipeline__dp-1 --b ours_pipeline__dp-2 --all`, the
circuits:

| instance variant | ours_pipeline__dp-1 | ours_pipeline__dp-2 | ratio | DP on main problem | DP on collapsed problem | sparse DP |
|---|---|---|---:|---|---|---|
| wjh_bb108_circuit sector | exact 0.6 s | exact 0.5 s | 1.1 | search (w=87) | search (w=40) |  |
| wjh_bb144_circuit sector | exact 1.4 s | exact 1.3 s | 1.1 | search (w=103) | search (w=57) |  |
| wjh_bb288_circuit sector | timeout 14.. | timeout 14.. |  | search (w=211) | search (w=106) |  |
| wjh_bb360_circuit sector | timeout 14.. | timeout 14.. |  | search | search (w=118) |  |
| wjh_bb72_circuit sector | exact 0.3 s | exact 0.3 s | 1.1 | search (w=61) | search (w=27) |  |
| wjh_bb756_circuit sector | skipped | skipped |  |  |  |  |
| wjh_bb90_circuit sector | exact 0.5 s | exact 0.4 s | 1.1 | search (w=76) | search (w=35) |  |
| wjh_midout_d11 sector | exact 0.2 s | exact 0.2 s | 0.97 | search (w=31) | search (w=13) |  |
| wjh_midout_d3 sector | exact 0.1 s | exact 0.1 s | 1.1 | search (w=4) | search (w=3) |  |
| wjh_midout_d5 sector | exact 0.1 s | exact 0.1 s | 1.2 | search (w=9) | search (w=6) |  |
| wjh_midout_d7 sector | exact 0.1 s | exact 0.1 s | 1.1 | search (w=15) | search (w=8) |  |
| wjh_midout_d9 sector | exact 0.2 s | exact 0.1 s | 1.1 | search (w=22) | search (w=12) |  |
| wjh_superdense_d11 sector | timeout 8..11 | timeout 8..11 |  | search (w=54) | search (w=14) | search (the sparse DP would exceed the table budget) |
| wjh_superdense_d3 sector | exact 0.2 s | exact 0.1 s | 1.9 | search (w=6) | search (w=3) |  |
| wjh_superdense_d5 sector | exact 0.2 s | exact 0.3 s | 0.6 | search (w=14) | search (w=6) | search (finished within its head start of 0.0 s) |
| wjh_superdense_d7 sector | exact 3.3 s | exact 0.7 s | 4.7 | search (w=24) | search (w=7) | sparse DP, K = 6 (0.2 s) |
| wjh_superdense_d9 sector | exact 374.5 s | exact 17.0 s | 22 | search (w=38) | search (w=8) | sparse DP, K = 8 (6.5 s) |
| wjh_superdense_mpp_d15 sector | exact 0.3 s | exact 0.3 s | 1 | search (w=12) | search (w=12) |  |
| wjh_surface_d11 sector | exact 0.2 s | exact 0.2 s | 1.2 | search (w=61) | search (w=7) |  |
| wjh_surface_d3 sector | exact 0.2 s | exact 0.1 s | 1.5 | search (w=5) | search (w=2) |  |
| wjh_surface_d5 sector | exact 0.1 s | exact 0.1 s | 1.2 | search (w=13) | search (w=4) |  |
| wjh_surface_d7 sector | exact 0.1 s | exact 0.1 s | 1 | search (w=25) | search (w=5) |  |
| wjh_surface_d9 sector | exact 0.1 s | exact 0.1 s | 1 | search (w=41) | search (w=6) |  |

All 126: 0 solved only with dp=2, 0 only with dp=1; of those solved by both, 2 at least 1.5x and 1 s faster with
dp=2, 0 slower. The 103 codes change nowhere by more than 1.5x and 1 s. Among them, qt_216_4_18 finishes at the
limit with both (588 s and 586 s).

**Outcomes are unchanged, and nothing is slower.** Two runs are faster, the superdense colour-code circuits:
- **d9: 374.5 s → 17.0 s.** After a 1.9 s probe (weights up to 3), the search has a 7.7 s head start. Then one
  sweep at K = 8 (6.5 s) leaves no solution of weight ≤ 8. Before, the sector search from 6 to 8 took 374 s.
- **d7: 3.3 s → 0.7 s.** The sweep at K = 6 (0.2 s) runs inside the dense DP's head start, so the dense DP is not
  needed.

Superdense d11 stays open in this tier (8..11):
- Its probe stops at weight 2 (0.46 s). The prediction from weight 2 for the sweep at K = 10 is 4,815 s and
  118 GB. That is 14 times the run's 8 GiB table budget, beyond the probe's slack of 10.
- With weight 3 measured, the prediction is 1,122 s and 27.6 GB, and the sweep takes 670 s and 11.5 GB.
- A dedicated run settles the distance at 11 (`results/sparse_dp/README.md`).

Elsewhere the sparse stage is not reached:
- The surface, midout and BB circuits up to [[144,12,12]] are settled by the earlier stages.
- bb288 and bb360 stop in the collapsed search. Their sector problems (cut rank 61 to 211) would be too wide for
  the sparse tables anyway.

## Second tier (32 threads, 90 GB, 3600 s), against the default configuration

Records: `results/bench_wjh_tierB/ours_pipeline__dp-2`.
- The run (`bench/tier_b.py dp2b`, code of 6798b88) covers what dp=2's first tier left: 4 circuits on their sector
  problem and 35 codes.
- With give-up 1, a family's larger instances are skipped after its first timeout: 26 of the 39 (the default:
  27 of 40).
- 2 jobs on cores 96-159 of 5090, 23 October 11:45-14:25 (UTC+8).
- Only superdense d11 reaches the sparse stage. Under 8ec918b its probe would measure the same weights, so its
  decision and schedule stand for 8ec918b too.
- The second tier ran with 45 GiB of lookup tables up front (7ef27aa), not yet under the depth rule of c030477.

The default's records (`results/bench_wjh_tierB/ours_pipeline`, October) ran with 1 GiB lookup tables, those of
dp=2 with 45 GiB (7ef27aa):

| instance variant | default, tier 2 | dp=2, tier 2 |
|---|---:|---:|
| wjh_bb288_circuit sector | 196 s | 236 s |
| wjh_bb360_circuit sector | timeout 17.. | timeout 17.. |
| wjh_bb_n360 full | 76.1 s | 56.4 s |
| wjh_bb_n576 full | 44.3 s | 39.5 s |
| wjh_bb_n648 full | timeout 28.. | timeout 28.. |
| wjh_lp_aj61 full | 93.5 s | 73.6 s |
| wjh_lp_aj73 full | 70.5 s | 63.1 s |
| wjh_lp_aj85 full | 68.6 s | 55.5 s |
| wjh_lp_aj95 full | 62.8 s | 44.3 s |
| wjh_lp_xu42 full | 133 s | 105 s |
| wjh_qt_216_4_18 full | 27.2 s | (solved in tier 1) |
| wjh_qt_252_2_21 full | 2390 s | 1847 s |
| wjh_qt_288_2_24 full | timeout 22.. | timeout 22.. |
| wjh_superdense_d11 sector | timeout 10..11 | 1803 s |

**Superdense d11 is settled within the protocol: 11, in 1,803 s and 11.3 GB.**
- The window stage finds a weight-11 fault set after 1 s.
- The sector search then has its 1,122 s head start (the sparse DP's predicted time) and exhausts the weights 7
  to 9 on 32 threads.
- One sweep of the sparse DP at K = 10 (one thread, 672 s) leaves no solution of weight up to 10.
- The default stops at 10..11 after 3,600 s.

The other second-tier runs:
- The codes run as with dp=1 and take 0.7-0.9x the default's time.
- bb288 takes 1.2x.
- The timeouts end at the same lower bounds (bb360 17, bb_n648 28, qt_288 22).
- qt_216_4_18 is settled in dp=2's first tier (586 s, at the limit, as with dp=1).

Solved over both tiers (`bench/compare_dp2.py`): **97 of the 126 instances with dp=2, 96 with the default.** The one more
is superdense d11.
