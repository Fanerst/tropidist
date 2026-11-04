# Second-tier record outside the benchmark protocol

`ours_pipeline__dp-2/mitten_200__sector__t32.json` (exact, 9, 184.5 s on 32 threads) was produced by the rerun in
`bench/tier_b.py`, phase `final2b` (`--redo status=skipped`): in the second tier the give-up order put the mitten
[[300,60,14]] circuit (fewer columns) before [[200,40,12]], and after its failure the protocol skips the larger
instance for every solver. Only our method was rerun, so the record is kept here, outside `results/bench_tierB`,
and is not counted (2026-11-03). The value 9 is also certified by the audit runs (`docs/audit_items.csv`).
