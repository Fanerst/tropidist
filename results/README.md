# Result records

Every number in the paper comes from a record here. A record is a JSON file with the certified lower bound, the upper
bound, the log of every weight threshold and the fault set that attains the upper bound. Records were written on our
servers and contain their absolute paths. Folders with their own README describe their runs in detail.

| folder | what it holds |
|---|---|
| `bench/`, `bench_tierB/` | the benchmark of 74 instances: first tier (one thread, 600 s) and second tier (32 threads, one hour), one subfolder per method and configuration; the reported configuration of ours is `ours_pipeline__dp-2` |
| `bench_wjh/`, `bench_wjh_tierB/`, `bench_wjh_8h/` | the 126 CSS instances of the prior benchmark (arXiv:2603.22532): the same two tiers, and runs under its own limits (one core, 8 GB, eight hours) |
| `bench_ablation_final/` | the pipeline with one component removed at a time (`bench_ablation/`: an earlier pass) |
| `bench_extended/` | longer runs outside the benchmark that close its open instances |
| `bench_tierB_off_protocol/` | a rerun outside the protocol, kept apart and not counted |
| `bench_replay/` | every circuit witness of the pipeline replayed in Stim (`bench/replay_witnesses.py`) |
| `bench_recheck/`, `bench_tables/`, `table_depth/` | a rerun of the first tier, and the study of the depth of the lookup tables |
| `bench_lowwidth/`, `bench_lowwidth_tierB/`, `bench_lowwidth_extra/` | the trial of the Rank DP evaluators on problems of small width |
| `papers/`, `papers2/`, `papers3/`, `papers4/` | published circuits and codes, in the four batches of [../docs/notes/PAPERS.md](../docs/notes/PAPERS.md); the audit's values are in [../docs/audit_items.csv](../docs/audit_items.csv) |
| `cornucopia/`, `planar_dp/`, `failfast/` | the Cornucopia codes, the planar codes of 2026, and the circuits of Bravyi et al.'s public code |
| `ibm/`, `ibm_matched/`, `bb288_scan/` | the memory instruction of IBM's bicycle architecture: distances, decoder-independent bounds, low-weight failures and simulations, and all depth-seven schedules of the two-gross code |
| `defect_study/`, `defect_test/` | gross-code chips with dead checks, and the first test of that study |
| `surgery/` | the merged codes of published logical measurements (universal adapters, SSIP) |
| `sparse_dp/`, `dpvs/`, `dp_calibration/` | the weight-truncated Rank DP, the dense DP against the search on local codes, and the rates that turn the DP's work into time |
| `recert/`, `rerun_lift/`, `lift_fix_test/` | values recomputed after the kernel fixes of 20 and 30 October 2026, and a test of the lifting fix |
| `dense_audit_20261021/`, `rw_tree_audit_20261021/` | audits of the dense Rank DP and of rank-width solvers ([../docs/notes/](../docs/notes/)) |
| `phase4/`, `validate/`, `pilot/`, `codes_other_basis/` | covering-bound runs, small enumerations that validate lifting, the first runs on the largest circuits, code distances in the other basis |
| top level | the first study, bivariate bicycle memory circuits from [[72,12,6]] to [[288,12,18]] ([../docs/notes/BB_CIRCUITS.md](../docs/notes/BB_CIRCUITS.md)) |
