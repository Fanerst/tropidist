# Chips with dead checks

Certified circuit distance of the gross code's memory instruction on chips with dead check qubits or dead couplers, in
Tour de gross's own setting (`chip.py` is `papers/ibm_bicycle_matched.py` with live-check lists; with no dead check it
writes the identical circuit, checked on 7 schedules, both bases, 1 to 3 cycles).

## Model

A dead check qubit removes its check. So does a dead coupler, because a check missing one data qubit would no longer commute
with the others. The check's gates, preparation, measurement and detectors are dropped in every round, and its data qubits idle
in those slots. Logical operators are those of the perfect code. Dead data qubits are not modeled: such a chip counts as rejected.

## Reduction to same-type problems

With memory basis Z, a dead X check only removes faults, because a fault on a data qubit in its slot has the same effect on the
Z detectors whether the slot holds a gate or nothing. So

    d_Z(dead_x, dead_z) >= d_Z(none, dead_z),   d_X(dead_x, dead_z) >= d_X(dead_x, none).

Only same-type problems are run; the chip's value below is the minimum of the two, a certified lower bound. Whole-chip runs
(`rec_v.jsonl`, 58 runs) agree except where a dead X check also removes the hook faults of the lighter set (one chip: Z-basis
10, not 9).

## Files

- `make_jobs.py`: job lists (a: cycles; b: all pairs; c: random chips; v: whole chips). `make_scan_m1.py`: one dead check, all
  schedules, one job per orbit of the schedule symmetries.
- `run_chips.py`: one thread per run, the benchmark pipeline (`ours_pipeline`, dp=2), then a Stim replay of the fault set.
- `analyse_chips.py`, `analyse_scan1.py`: tables. `explain_nine.py`: replays a chip's fault set in the perfect circuit.
- `chip_spectrum.py`, `rate_chip.py`: all fault sets up to weight 10, order p^5 rate for a minimum-weight decoder.
- `sim_chip.py`, `chips_sim.json`: BP-OSD with the settings of `papers/ibm_bicycle_sim.py`, 10 cycles, run on `itp`.
- `rec/`: records. Fields as in `run_chips.py`; `rec_b.jsonl`, `rec_c.jsonl` hold whole-chip runs from before the reduction.

## Same chips on a distance-11 schedule

`rec_e.jsonl` and `rec_f.jsonl` hold the eight-timestep schedule (5,6,1,2,3,4)/(3,2,4,0,1,5) on the chips of parts b and c (`jobs_f.jsonl`: the chips part e left out). `chip_shares.py`
gives, for both schedules, the chips by distance per number of dead checks and the share of all chips at distance 10 or more at each junction yield (`chip_shares.json`). Fig. 4 draft:
`docs/make_ncs_figures.py` (`fig_design_ibm`).

Final on 2026-11-02 (200 random chips per m on both schedules, all 1,692 runs of part f exact and replayed). Share of all chips at distance 10 or more, perfect / certified standard / certified distance-11:
99.98%: 53, 70, 94; 99.95%: 21, 41, 84; 99.9%: 4, 16, 67. Chips with m = 7, 9 are the mean of the neighbors, m > 10 count as 0 (0.01% of chips at 99.9%).
On the 200 sampled chips each at m = 3, 4, 5, every chip at 8 or less lost a stabilizer, on both schedules (2, 12, 24), and the rank test also rejects a few chips at 9 (1, 2, 2). This is not a rule: among the 1,228 same-type problems with four or five dead checks, five keep every stabilizer and fall to 8 (dead X 1,24,52,55; 18,45,48,68; 0,2,24,51 on the standard schedule; 41,46,48,54 and 0,31,33,64,66 on the distance-11 schedule; external review of 2026-11-02, checked in the records).
From 6 dead checks on, a few chips keep their rank and fall to 8 or below (standard: 2 of 200 at m = 6 and at m = 8; distance-11 schedule: 1 of 200 at m = 8 and at m = 10): only certifying finds those.

BP-OSD (`rec/sim_chip.jsonl`, `sim_chip.py`, 10 cycles, 100 iterations, osd_cs 7, 42 runs, ended 2026-11-01): failure per run at p = 3e-3, Z / X basis, perfect 2.81e-3 / 2.84e-3; one dead Z check (z0) 3.51e-3 / 2.61e-3; one dead X check (x0) 2.71e-3 / 3.51e-3;
3 dead checks (m3) 3.91e-3 / 3.04e-3; 5 dead checks (m5) 4.34e-3 / 3.67e-3. So at most 1.5 times the perfect chip's rate in the basis the dead checks affect, at 200 to 480 failures per point.

## Number of cycles

`make_cycle_jobs.py`, `rec/rec_g.jsonl` (11,328 runs), `analyse_cycles.py`, `cycles_base_rate.json`: every orbit of problems of the four smaller codes at one and two cycles, against the six-round tables. Summary in `results/bb288_scan/README.md`.

Rates on the distance-11 schedule: `run_spectra.sh 16 spectra_list_d11_z.txt 561234_324015` and `spectra_list_d11_x.txt` (one dead check, both bases, 3 and 4 cycles), then `rate_summary.py`, which writes `rates_chip.json`. At p = 1e-4, C = 10, the term of order p^5 is 3.79e-18 with one dead Z check (Z basis only) and 8.26e-19 with one dead X check (X basis only): 1.6% and 0.4% of the 2.33e-16 of the perfect chip on the standard schedule. The perfect chip on this schedule starts at order p^6, 5.7e-17 (`results/ibm_matched/mwd_gross_c10.json`), so a dead check adds 7% and 1.4% there, and about 66% and 14% at p = 1e-5. The change of the order-p^6 term under a dead check was not computed. On the standard schedule one dead Z check gives 1.09 times the perfect chip's rate and one dead X check 1.03 times, at 1e-4 and 1e-5.

Rerun 2026-11-04 after the review: `rate_chip.py` now decides each configuration of five faults exactly. Before, every less likely half of a set of weight 10 counted as failing; now a half fails only if no explanation of its own logical class is lighter (a set of weight 9 through its complement with the same class) or as heavy and likelier than every one of the other class (ties fail). Previous values: 3.98e-18, 8.79e-19, 2.34e-16, and 1.10 and 1.04 on the standard schedule.

BP-OSD on this schedule: `sim_chip.py` with `chips_sim_d11.json`, `rec/sim_chip_d11.jsonl` (36 runs, ended 2026-11-03), settings as above, perfect chip from `results/ibm_matched/sim_gross_c10.jsonl`. At p = 3e-3, the largest failure rate is 1.42 times the perfect chip's on this schedule (five dead checks, X basis) and 1.56 times the perfect standard chip's (five dead checks, Z basis), at 100 to 500 failures per point.

Every (chip, basis, p) in `sim_chip.py` starts from the same seed sequence (1, 2, ...), so runs on similar chips share random numbers. Their estimates are each unbiased but correlated, which is why three pairs at p = 5e-3 have equal (shots, failures). A replicate of the 12 runs at p = 5e-3 with seeds from 100001 (`rec/sim_chip_d11_reseed.jsonl`, 5090, ldpc 2.4.1, 2026-11-03) agrees within the statistical error.

`replay_rec_a.py` replays in Stim the 11 fault sets of `rec/rec_a.jsonl` that were stored without a replay (`rec/rec_a_replay.jsonl`): all 11 replay correctly.

Whole-chip check (2026-11-04): `rec/rec_v.jsonl` holds 58 whole-chip runs on 29 chips (both bases). Their same-type problems (dead checks of the memory basis's own type only) were all run with `run_chips.py` (`rec/rec_v_same_type.jsonl`, 47 distinct problems, all exact and replayed). 56 of the 58 runs agree; the two others are [20,46,62,63]/[4] (Z basis) and [11,56]/[70] (X basis), where the whole chip has 10 and the same-type problem 9, because a dead check of the other type also removes the hook faults of the lightest set. The chip values (minimum over the two bases) agree on all 29 chips.
