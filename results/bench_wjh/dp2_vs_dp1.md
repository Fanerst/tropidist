# The pipeline with the sparse Rank DP (dp=2) against dp=1: WJH circuits, first tier

Records: `ours_pipeline__dp-2/` (this run) and `ours_pipeline__dp-1/` (22 October).

Setup:
- The 23 circuits of arXiv:2603.22532, sector problem.
- First-tier limits, the flags of the dp=1 pass (`scripts/server/dp_pass.sh`): one thread, 600 s, 16 GB,
  give-up after 2.
- 5090, cores of socket 1, 23 October; code of commit 7c38b1f.
- A later commit only reuses the dense estimate's column order in the sparse stage; the decisions are identical.

What dp=2 adds: `bench/adapters/ours_pipeline.py`.
- The circuit stages (collapse, lift, window) leave a gap [l, u) on the sector.
- The search then runs for the sparse DP's predicted time; one meet-in-the-middle sweep at u − 1 decides.
- Prediction: `cdist.auto.sparse_estimate`, probe sweeps up to weight 3.
- Code instances run exactly as with dp=1, so the 103 codes were not rerun.

`python bench/compare_dp.py results/bench_wjh --a ours_pipeline__dp-1 --b ours_pipeline__dp-2 --all`:

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
| wjh_superdense_d5 sector | exact 0.2 s | exact 0.2 s | 0.86 | search (w=14) | search (w=6) | search (finished within its head start of 0.0 s) |
| wjh_superdense_d7 sector | exact 3.3 s | exact 0.8 s | 3.9 | search (w=24) | search (w=7) | sparse DP, K = 6 (0.1 s) |
| wjh_superdense_d9 sector | exact 374.5 s | exact 15.8 s | 24 | search (w=38) | search (w=8) | sparse DP, K = 8 (5.9 s) |
| wjh_superdense_mpp_d15 sector | exact 0.3 s | exact 0.3 s | 1 | search (w=12) | search (w=12) |  |
| wjh_surface_d11 sector | exact 0.2 s | exact 0.2 s | 1.2 | search (w=61) | search (w=7) |  |
| wjh_surface_d3 sector | exact 0.2 s | exact 0.1 s | 1.5 | search (w=5) | search (w=2) |  |
| wjh_surface_d5 sector | exact 0.1 s | exact 0.1 s | 1.2 | search (w=13) | search (w=4) |  |
| wjh_surface_d7 sector | exact 0.1 s | exact 0.1 s | 1 | search (w=25) | search (w=5) |  |
| wjh_surface_d9 sector | exact 0.1 s | exact 0.1 s | 1 | search (w=41) | search (w=6) |  |

23 variants with both records: 0 solved only with ours_pipeline__dp-2, 0 only with ours_pipeline__dp-1; of those solved by both, 2 at least 1.5x and 1 s faster with ours_pipeline__dp-2, 0 slower.

**Outcomes are unchanged, and nothing is slower.** Two runs are faster, the superdense colour-code circuits:
- **d9: 374.5 s → 15.8 s.** The search had a 7.7 s head start, then one sweep at K = 8 (5.9 s, probe 1.7 s) left
  no solution of weight ≤ 8. Before, the sector search from 6 to 8 took 374 s.
- **d7: 3.3 s → 0.8 s.** The sweep at K = 6 runs inside the dense DP's head start, so the dense DP is not needed.

Superdense d11 stays open in this tier (8..11):
- The sweep at K = 10 is predicted at 1,122 s and 66 GB, beyond the run's 600 s and its 8 GiB table budget.
  The prediction is pessimistic: the sweep takes 670 s and 11.5 GB.
- In a dedicated run that settles the distance at 11 (`results/sparse_dp/README.md`).

Elsewhere the sparse stage is not reached:
- The surface, midout and BB circuits up to [[144,12,12]] are settled by the earlier stages.
- bb288 and bb360 stop in the collapsed search. Their sector problems (cut rank 61 to 211) would be too wide for
  the sparse tables anyway.
