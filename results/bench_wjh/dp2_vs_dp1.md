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
  - the other circuits never reach the probe, so their records stand for 8ec918b too.

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
