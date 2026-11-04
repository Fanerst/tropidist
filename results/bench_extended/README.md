# Runs outside the benchmark

Extended-budget runs of the pipeline (`dp=2`, more threads, limits of up to seven days) on instances the two benchmark tiers left open. They do not enter the tier counts.

- `ours_pipeline__dp-2*/`, `isd*/`: records of the lower-bound runs and of the explicit errors, by configuration.
- `tanner_x/`: X distances of the four quantum Tanner codes (`scripts/server/tanner_x_h200.sh`); the Z distances are the benchmark's instances. `xz_symmetry_check.py`: these codes have no qubit permutation exchanging X and Z. `wjh_qt_324_4_25_Xdist_kmin24.json` is a rerun of the last weight on more threads. The X distances are 24, 25, 24 and 26: equal to the Z distances except for [[396,4]], whose Z distance is 27, so its code distance is 26.
- `transfer/`: the 3-round weight-12 fault set of mitten [[300,60,14]] replayed in the 6-round circuit.
- `combine_certificates.py` -> `certificates.json`: a run started at a threshold (`kmin`) proves its bound only with the run below it, so this checks that the records of each instance chain without a gap, on the same problem, and names the record of the explicit error.

Cornucopia [[2304,1156,16]], Z basis, 8 cycles: `results/cornucopia/circ_q64_r8_Z_k13.json` excludes weights up to 12, and `results/cornucopia/win_q64_r8_Z_t1.json` holds the fault set of weight 14, so 13 to 14. The weight-13 search was lost in the reboot of 5090 on 2026-11-02; it restarted with the task ledger of `cdist/gmitm.c` (`GM_LEDGER`, `GM_SLICE`, `tests/test_ledger.py`) and runs in slices on several machines (`results/cornucopia/circ_q64_r8_Z_w13_s*.json`). A slice reports `slice_done`, never exhausted; only one run without a slice, over the concatenated ledgers of all slices, can report weight 13 exhausted.
