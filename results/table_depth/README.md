# Depth of the pipeline's lookup tables (23 October 2026)

## The problem

Every search of the pipeline (`bench/adapters/ours_pipeline.py`) keeps a lookup table: all column subsets of size
up to k_table = 2 (k_coll = 3 on the time-collapsed problem), keyed by syndrome. A search at weight K enumerates
prefixes of weight K - k and finds the rest by one lookup per leaf.

Until commit 7ef27aa (22 October), the worker process silently had a 1 GiB budget for these tables, so larger
ones were built one weight shallower. Every record of the default configuration and of dp=1 in the benchmark
tables ran that way. Since then the budget is half the memory limit (8 GiB in the first tier, 45 GiB in the
second), and the tables are built as deep as that allows.

The same-time recheck (`results/bench_recheck/README.md`) showed the effect on dp=1 and dp=2 alike:
- color_d11 full is lost in the first tier;
- surface d = 21-25 and cornucopia_252 take 1.3-3x as long;
- mitten_200's second tier gets 7x faster.

## Where the time goes

`scripts/table_depth_probe.py` runs the pipeline (config dp=1) in one process and logs:
- every table: width, depth, bytes, build time;
- every search level: stage, K, depth, time, nodes per depth, lookups, covering-bound calls.

Runs (`scripts/server/table_depth_runs.sh`): 1 GiB (`*__b1__*`) against 8 GiB up front (`*__b8__*`), on one thread
with the first-tier limits, and mitten_200 on 16 threads.

- **Building a table costs about 40 ns per entry** (32-47 ns measured): 2-3 s for a 1.2 GB weight-3 table, 5-6 s
  for 4.8 GB.
- **Short searches only pay for the build.**
  - surface d = 23 sector: the collapsed problem's 2.3 GB table is built twice.
    - The first build falls in the search's 1 s head start before the dense DP. It cannot be interrupted, and the
      soft deadline then discards it: the run reaches its second build after 3.5 s, against 0.5 s with 1 GiB.
    - The second build (2.6 s) confirms the DP's value at K = 23.
    - The whole run takes 7.1 s, against 2.3 s with 1 GiB.
  - cornucopia_252: build 3.5 s, and its levels are slower with the deeper table (K = 4: 0.82 s against 0.31 s).
- **On the full error model of color_d11 (16,422 columns) the weight-2 table loses at every level:** K = 3 is 3x
  slower, K = 4 17x (55 s against 3.3 s), K = 5 9x.
  - The table is label-free, so every syndrome match is a hit that the kernel completes explicitly.
  - At weight 2 such a circuit has many matches with zero logical, which cost more than the covering bound saves
    at the level above.
- **Long collapsed searches gain:**
  - mitten_200's level 9 takes 153 s instead of 1,168 s (16 threads), level 8 40 s instead of 72 s;
  - mitten_300's level 8 takes 72 s instead of 181 s;
  - routing_200_24's minimum enumeration takes 13 s instead of 47 s;
  - bb288_r18's levels are 6-15% faster.
- **A wider sector table** (w8bb_144_16, 6,192 columns, 604 MB) is 4% faster.

So the deeper table pays only after a level has taken long, and not always then.

## The rule

`bench/adapters/ours_pipeline.py`, config `deepen=1` (default):
1. **Up front, tables are built within EAGER_TABLE_BYTES = 1 GiB for all live tables.** This is the depth of every
   record before 7ef27aa. The dense and sparse DP keep the full memory budget, as since 7ef27aa.
2. **A level may trigger a trial.** That happens after an exhausted level that took DEEPEN_FACTOR = 4 times the
   predicted build time (40 ns per entry) of the table one weight deeper, if that table fits in the budget.
3. **The trial is paired.** The deeper table is built, and both tables run the same level on DEEPEN_SAMPLE = 5% of
   the anchors.
   - Each run is limited to 5% of that level's time, 0.5 s at least.
   - The task depth is 1, so the kernel does not enumerate the prefixes of deeper tasks before its clock starts.
   - The two runs are compared by the nodes visited per second at depth K - k - 2, the deepest that both tables
     expand alike, or by their times if both finish.
4. **The search continues with the deeper table only if it is DEEPEN_GAIN = 1.25 times faster.** Otherwise it
   keeps the shallow one, and that stage tries no more.

`deepen=0` keeps the tables of step 1 only.

The kernel (`cdist/gmitm.c`) now reads its clock every 1,024 node visits and completions of a thread.
- Before, it read the clock when a per-depth node count reached a multiple of 65,536.
- The leaf fast path raises those counts by whole batches, and the completions of table hits were not counted at
  all.
- So a time limit could be overrun many times: an early version of the trial ran 31 s against a limit of 4.7 s on
  color_d11 (`iterations/`).

## Results

`python scripts/summarize_table_depth.py`.
- Runs of the rule (`scripts/server/table_depth_new.sh`, TAG=final): `*__final__*`.
- Earlier versions of the trial, all with the same decisions: `iterations/`.
  - `new`: the shallow sample had no time limit, and the kernel's clock was read too seldom.
  - `new2`: the kernel fix.
  - `rule`: time-boxed, but with the kernel's default task depth, which fills the node counts it compares.

| instance variant | threads | 1 GiB (before 7ef27aa) | 8 GiB up front (7ef27aa) | rule |
|---|---:|---:|---:|---:|
| bb288_r18 sector | 1 | timeout 14.. | timeout 14.. | timeout 14.. |
| color_d11 full | 1 | 241.9 s | timeout 6.. | 249.0 s |
| cornucopia_252 full | 1 | 3.1 s | 7.5 s | 3.0 s |
| cornucopia_252 sector | 1 | 2.1 s | 6.6 s | 2.1 s |
| mitten_200 sector | 16 | 1243.7 s | 200.0 s | 227.3 s |
| mitten_300 sector | 1 | timeout 9.. | timeout 9.. | timeout 9.. |
| routing_200_24 sector | 1 | timeout 9..10 | timeout 9..10 | timeout 9..10 |
| surface_d21 full | 1 | 5.7 s | 6.9 s | 5.0 s |
| surface_d21 sector | 1 | 1.7 s | 3.9 s | 1.7 s |
| surface_d23 full | 1 | 11.5 s | 15.7 s | 8.1 s |
| surface_d23 sector | 1 | 2.3 s | 7.1 s | 2.4 s |
| surface_d25 full | 1 | 18.7 s | 24.2 s | 17.2 s |
| surface_d25 sector | 1 | 7.0 s | 15.6 s | 7.5 s |
| w8bb_144_16 full | 1 | 167.6 s | 161.0 s | 167.7 s |
| w8bb_144_16 sector | 1 | 168.2 s | 160.2 s | 166.9 s |

Trials of the rule (level K with depth k - 1 took level_seconds; build of depth k; the same sample of anchors with both):

| instance variant | stage | K | k | level | build | anchors | shallow | deep | decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| bb288_r18 sector | collapsed | 12 | 3 | 20.3 s | 2.2 s | 1 | 1.02 s, 1,044,875 nodes (limit) | 1.02 s, 1,185,214 nodes (limit) | kept |
| color_d11 full | plain | 5 | 2 | 71.6 s | 4.4 s | 822 | 3.53 s, 11,859 nodes | 3.58 s, 1,560 nodes (limit) | kept |
| mitten_200 sector | collapsed | 8 | 3 | 70.6 s | 2.1 s | 9 | 3.53 s, 59,739 nodes (limit) | 3.53 s, 208,555 nodes (limit) | deeper table |
| mitten_300 sector | collapsed | 8 | 3 | 174.6 s | 6.1 s | 6 | 8.73 s, 152,127 nodes (limit) | 4.71 s, 280,815 nodes | deeper table |
| w8bb_144_16 full | sector | 8 | 2 | 13.5 s | 0.6 s | 5 | 0.68 s, 353,568 nodes (limit) | 0.68 s, 370,889 nodes (limit) | kept |
| w8bb_144_16 sector | sector | 8 | 2 | 13.6 s | 0.6 s | 5 | 0.68 s, 354,544 nodes (limit) | 0.68 s, 377,075 nodes | kept |

Where the deeper table does not pay, the rule's times are those of 1 GiB: 0.70-1.07x, the noise between runs made
at different times. The paired suite below compares the two at one time.
- color_d11 full keeps its weight-1 table: in the trial the deeper table visits 1,560 nodes in the time the shallow
  one needs for 11,859. It takes 249 s, against 242 s, and is solved again.
- mitten_200 (16 threads) and mitten_300 switch after their trial:
  - mitten_200 takes 227 s, against 1,244 s with 1 GiB and 200 s with the deep table up front;
  - mitten_300 still times out in the first tier.
- A trial costs the deeper table's build plus about a tenth of the level that triggered it.

## Main suite, first tier, with the rule and with 1 GiB side by side

`results/bench_tables`, `scripts/server/table_depth_suite.sh`: config dp=1 under the rule (`ours_pipeline__dp-1`) and
with `table_gb=1` (`ours_pipeline__dp-1__table%5Fgb-1`).
- `table_gb=1` holds the lookup tables and the DP front end to 1 GiB, exactly the behaviour before 7ef27aa.
- First-tier limits, 18 jobs each, cores 0-17 and 18-35 of 5090 at the same time, 23 October.
- The 9 records whose run under the rule held a trial were rerun after the trial's last change, again side by side
  (`scripts/server/table_depth_trials.sh`).

`python bench/compare_dp.py results/bench_tables --a "ours_pipeline__dp-1__table%5Fgb-1" --b ours_pipeline__dp-1`:
- **Of the 102 variants, none is solved by one configuration only, and none is 1.5x and 1 s faster or slower.**
- Over the 51 solved by both in more than 1 s, the rule takes 1.02x the time (0.97-1.22x, the extremes on runs of
  1-3 s).
- The 20 unsolved end at the same bounds, except mitten_200: the rule reaches the lower bound 9, 1 GiB 8.
- 9 records hold a trial:
  - bb288_r18, color_d11 full and w8bb_144_16 keep their table (the deeper one is 1.05-1.13x faster on bb288_r18
    and w8bb, and 7x slower on color_d11);
  - mitten_200 and mitten_300 take the deeper one (1.6-3.4x faster).
- With 8 GiB the dense DP fits on 5 more records, where the search wins anyway.

Against the dp=1 pass of 22 October, both configurations take 1.12-1.14x the time: that is the load of the machine
on 23 October.

## What changes for the published records

Under the rule, the tables built up front are again those of every published record of the default
configuration and of dp=1 (1 GiB). A record changes only where a trial switches to a deeper table, a level being
slow:
- **Main suite, first tier:** nothing changes in outcome. mitten_200 times out with the lower bound 9 instead of 8.
  mitten_300 also switches and times out where it did.
- **Second tier:** mitten_200 now takes 148 s (32 threads; `results/bench_tierB/ours_pipeline`), instead of the
  default's 1,038 s of 5 October.
  - It switches to the deeper table after a trial at weight 8, and comes close to the 144 s of dp=2 with the deep
    table up front.
  - Other long searches may switch as well; they are not rerun.

Reruns approved by Feng and done on 23 October (`scripts/server/rule_reruns.sh`, c030477):
- The default configuration's second-tier mitten_200, as above.
- dp=2's 21 first-tier records whose tables 7ef27aa had made deeper: the 19 of results/bench_recheck, and the bb288
  and bb360 circuits of arXiv:2603.22532.
  - color_d11 full is solved again (246 s).
  - surface d = 21-25 and cornucopia_252 are back to their dp=1 times.
  - w8bb_144_16 takes 165 s, against 154 s with the deep table up front: its trial found the deeper table only
    1.05x faster.
  - The timeouts end at the same lower bounds.
- dp=2's second-tier records still ran with the deep tables up front.
