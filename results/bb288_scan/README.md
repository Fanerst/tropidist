# Schedule scan of the two-gross code [[288,12,18]]

Circuit distance of IBM's memory instruction (`papers/ibm_bicycle.py`) for all 8,496 depth-seven schedules of
`papers/bb6_depth7.py`.

## Symmetries (`screen/symmetry_classes.py`)

A group automorphism of Z_l x Z_m that maps the terms of A and B to translates of themselves (plain), of each other (swap),
of their negatives (inv, X and Z exchanged) or of each other's negatives (swapinv, X and Z exchanged) relabels the schedule and
carries the circuit to the circuit of the relabeled schedule. Reversing the slots (T) keeps the basis. The two-gross code has an
automorphism of order 3 (x -> x y^9, y -> x^9 y^10), which cycles the terms of A and of B, so its group is larger than the gross
code's. The 16,992 problems (schedule, basis) reduce to 708 orbits, and the schedules to 390 classes, each holding one or two
problems.

Checks: all generators reproduce all 16,992 exact values on bb72, bb90, bb108 and gross (`python screen/symmetry_classes.py`).
`screen/iso_check.py` builds both circuits and finds the detector map that carries one column list to the other, up to an
invertible change of the logical basis plus detector terms: 144 of 144 on two-gross (6 schedules, both bases, one cycle), and all
on gross.

## Runs

- `pilot/`: the pilot of 2026-11-01, before the symmetries were known.
- `screen/screen.py`: both one-round windows up to weight 16, one thread per problem, on 5090.
- `screen/deep_run.py`: one problem, any number of threads and cycles. `screen/deep_queue.py`: exact scan of the classes
  (`screen/classes.json`, ranked by distance on the four smaller codes), on 5090b and 5090c. `screen/analyse.py`: state of the screen.

First result: schedule px = 046135, pz = 531620 (a self-dual class of 12 schedules, nine timesteps per cycle in IBM's setting) has no logical fault set up to
weight 16 at one cycle, by direct runs in both bases (`deep_run.py`; Z 961 s on 64 threads, X 2,640 s on 24 threads, 5090b), against 16 for the standard schedule.
Weight 17 and two cycles are running.  Runs that move past one cycle are the test that counts, since a value at one cycle is only an upper bound for more cycles.

At one cycle all columns have detectors in rounds 1, 2 or both. The fault sets of the standard schedule lie wholly in one
round: round 1 in the X basis, round 2 in the Z basis. The pipeline searches window t1 only, so the queue runs the T image when t2 is
the larger window.

## The limit on the new schedule

`screen/limit_candidate.py` runs `papers/ibm_bicycle_code_logicals.py` on the circuit of 046135_531620 (records in `limit/`, 18 cycles, about 400 s per basis on 5090c). All 336 logical operators of weight 18 per type are fault sets of this circuit; 1,008 copies replayed in each basis. Per cycle, both bases: 10^-28.40 at p = 1e-4 and 10^-19.52 at 1e-3, against 10^-28.22 and 10^-19.34 on the standard schedule's circuit.

## More cycles

Schedule 046135_531620, basis Z, Tour de gross's instruction: two cycles, sector 720 x 3168, weights 13 to 16 exhausted in 56, 443, 3,400 and 22,462 s on 32 threads of 5090c, lower bound 17 (`deep/ibm_bb288_s046135_531620_c2_Z_k16.json`). `screen/chain_c2.log`: the X basis at two cycles carried to the Z basis by the code's symmetries. `screen/matched_c2.log`: the matched circuit has the same 3,168 sector columns as the fused one in both bases. Three cycles, weight <= 16: running on 5090c cores 0-31 from 2026-11-01 23:27 (`logs/deep_c3.log`).

Base rate: `results/defect_study/make_cycle_jobs.py` puts every orbit of problems of the four smaller codes through 2 and 1 cycles in the matched circuit (`rec_g.jsonl`, on 5090b), to compare with the six-round tables.

## One-round windows (2026-11-02)

The one-round windows of the one-cycle instruction come in only 7 distinct problems over all 708 problems (`window_types.py`, `window_types.json`): the plain one (288 columns, single-qubit
columns only, the code itself) and six with 144 hook columns more. Each of the six has a low-weight fault set, found once with the translation symmetry (`window_search.py`, `window_search.jsonl`; `screen_k16.jsonl` for two of them):
weight 16 for five, weight 12 for one. Identical windows have identical columns, so the fault set holds in every problem with that window; `window_transfer.py` replays it in each problem's own circuit (`window_transfer.jsonl`).
Hence every schedule with a hook family inside one round stays at 16 or below (7,056 of 8,496), and only the 78 classes with no such family (1,440 schedules, 120 problems) can exceed 16. The candidate's class is one of them.

`screen.py` was stopped at 556 of 708 problems and the K <= 15 queue on hook classes was stopped: the first is superseded, and the second would only split those classes into 15 and 16. Run instead: K <= 16 on the
72 open no-hook classes (`only_*.json`, records `exact_nohook_*.jsonl` on 5090, 5090b, 5090c) and K <= 12 on all 708 problems for the worst schedule (`triage_low.jsonl` on 5090). Settled before the stop: 27 classes (`exact_scan*.jsonl`).

Low-end pass (`triage_low.jsonl`, K <= 12 on all 708 problems): 4 problems are exactly 12 (classes 382, 384, 385, 389, 12 schedules each, 48 in all, the window `0b59`), the other 704 have lower bound 13. `window_transfer.jsonl`: 588 of 588 transferred fault sets replay in their own circuits.

The no-hook condition is not a general rule (`window_types_key.py`, `window_types_KEY.json`, against the exact table): it is needed for the best value on [[90,8,10]] (9 only without a hook family, hooks reach 8) and on two-gross, but on [[72,12,6]], [[108,8,10]] and gross the best value is also reached with a hook family (272, 320 and 168 problems at the best value).

## Base rate for the number of cycles (2026-11-02)

Every orbit of problems of the four smaller codes at one and two cycles, matched circuit (`results/defect_study/rec/rec_g.jsonl`, 11,328 runs, all exact and replayed; `results/defect_study/analyse_cycles.py`, `results/defect_study/cycles_base_rate.json`), against the six-round tables, counted by the 16,992 (schedule, basis) problems of each code:

- Two cycles equal six rounds on all 67,968 problems.
- One cycle equals six rounds on 67,352. On the other 616 it is exactly one higher: bb72 48, bb90 256, bb108 128, gross 184.
- Without a hook family inside one round, the case of two-gross's candidate, one cycle is too high on only 32 of 11,520 problems (gross, 10 to 9). At each code's top value it never is: 3,560 of 3,560 problems. With a hook family, the top value does drop: bb108 128 of 2,688 problems at 10, gross 128 of 1,472 at 11.

So a value at one cycle is an upper bound that is usually right, and two cycles have been enough on every problem where the answer is known. For 046135_531620 the deciding run is two cycles at K = 17: started 2026-11-02 04:00 on 5090b, on 48 physical cores from 15:50 (`logs/deep_c2_k17.log`, `deep/ibm_bb288_s046135_531620_c2_Z_k17_only17.json`, config `dp=2,kmin=17,kmax=17`; K <= 16 is in the earlier record on 5090c, so its lower bound holds together with that one). Three cycles, K <= 16: exhausted in 69,779 s on 32 threads (`deep/ibm_bb288_s046135_531620_c3_Z_k16.json`). The plain cross-check (no reductions, `deep/ibm_bb288_s046135_531620_c1_Z_k16_plain.json`) was stopped on 2026-11-02 to free the cores: it had excluded K <= 14, in agreement, and K = 15 was unfinished.

## Exact scan of the classes without a hook family (2026-11-02)

`screen/deep_queue.py` runs the pipeline on a class's first problem, then on its second below the first's value; `DEEP_ONLY` lists the classes, `DEEP_KMIN` starts the final search at that weight. K <= 16 first, then K = 17 on the classes left (`DEEP_KMIN=17`; classes 342, 345, 348 went straight to K <= 17). A witness at 17 ends the run, so classes at 17 take seconds to about 3 hours on 16 threads; a class at 18 needs the exhaustive search, about 110 to 190 thread-hours per problem. Records from all servers are in `records/`; `python tally_scan.py` tallies them into `scan_table.json`, from which `docs/make_ncs_figures.py` draws Fig. 4a and writes the tables and numbers of the paper. A skipped record marks a class handed to another server.

The queue records of classes 12 and 14 were seeded from `deep/`, without a replay flag; both fault sets (`deep/ibm_bb288_s026135_531640_c1_Z_k16.json`, `deep/ibm_bb288_s036412_254630_c1_Z_k16.json`) replayed in Stim on 2026-11-02: no detector fires and logical qubits flip. The class 16 record in `records/` stops at K <= 16; its K = 17 is `deep/ibm_bb288_s046135_531620_c1_Z_k17.json`, and the X basis follows from `screen/chain_c1.log`.
