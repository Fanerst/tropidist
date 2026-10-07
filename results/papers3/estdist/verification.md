# estdist verification audit

This records completed extraction checks, an independent review, and searches
reported by the lead. Paths are the paths used when commands ran; extraction
scratch files may subsequently be archived. A search timeout or invocation
budget stop retains a certified lower bound and does not establish an exact
distance. Witnesses use physical data-qubit indices. Basis Z searches physical
X operators against H_Z; basis X searches physical Z against H_X.

## Source boundary and extraction

Sources were read only from the five named papers on arxiv.org, including the
MM paper's v1/v2 HTML and v2 PDF. No author repositories, external datasets,
downloaded executable code, package installations, or remote jobs were used.
No source PDF visual verification was completed; definitions were extracted
from arXiv HTML/math and the web tool's PDF text.

| Command or operation | Actual outcome |
|---|---|
| `curl -L --max-time 30 https://arxiv.org/html/2601.18879 -o results/papers3/estdist/extraction_mm/paper.html` | Succeeded. |
| `curl -L --max-time 30 https://arxiv.org/html/2601.18879v1 -o results/papers3/estdist/extraction_mm/paper_v1.html` | Succeeded. |
| `curl -L --max-time 30 https://arxiv.org/pdf/2601.18879v2 -o results/papers3/estdist/extraction_mm/paper_v2.pdf` | Succeeded; visual verification did not follow. |
| `curl -L --fail -o results/papers3/estdist/extraction_qgpu_llm/qgpu.pdf https://arxiv.org/pdf/2603.05398` | Succeeded; downloaded the source PDF. |
| `pdftotext -layout results/papers3/estdist/extraction_qgpu_llm/qgpu.pdf results/papers3/estdist/extraction_qgpu_llm/qgpu.txt` | Failed: `pdftotext` was not installed. No text file was produced by this command. |
| `curl -L --fail -o results/papers3/estdist/extraction_qgpu_llm/llm.html https://arxiv.org/html/2606.02418` | Succeeded; downloaded the source HTML. |
| `.venv/bin/python results/papers3/estdist/extraction_qgpu_llm/extract_html.py` | Passed; extracted tables with the standard-library HTML parser. |
| `CLANG_MODULE_CACHE_PATH=/private/tmp/estdist_qgpu_swift_cache swift -module-cache-path /private/tmp/estdist_qgpu_swift_cache results/papers3/estdist/extraction_qgpu_llm/render.swift results/papers3/estdist/extraction_qgpu_llm/qgpu.pdf results/papers3/estdist/extraction_qgpu_llm/qgpu_table.png results/papers3/estdist/extraction_qgpu_llm/qgpu.txt` | Failed: installed Swift 6.3.3 did not support the SDK built with Swift 6.4. No PNG or local PDF text was produced. |
| ArXiv web reads of MM v1/v2 and QGPU/LLM sources | Completed. QGPU's unversioned HTML endpoint returned 404; its PDF text was available through the web tool. |

The local Python 3.9 environment lacks `int.bit_count()`. Initial QGPU/LLM and
balanced extraction checks failed on that call; replacing it with
`bin(value).count("1")` resolved the compatibility issue. QGPU/LLM table
selection also initially failed with `IndexError` because an assumed DOM
suffix differed from the observed suffix; selecting the observed table fixed
it. These were extraction-tool corrections, not changes to paper polynomials.
The initial MM BeautifulSoup heredoc failed with ModuleNotFoundError (bs4);
standard-library parsing subsequently succeeded. The web PDF inspection failed
on its18.6MB size limit. MM's default Swift SDK attempt failed on the compiler
version mismatch; the older-SDK retry was interrupted(exit130).
`.venv/bin/python -u results/papers3/estdist/extraction_mm/pdf_text.py`
aborted(exit134), and `ps` was denied by the sandbox. None of these failed
operations established PDF typography or process-memory measurements.

## Construction and witness checks

| Command | Actual outcome |
|---|---|
| `OMP_NUM_THREADS=2 .venv/bin/python results/papers3/estdist/extraction_qgpu_llm/prototype.py` | First failed on `int.bit_count()`, then failed on the table DOM selector; final runs passed all 23 reconstructed CSS `(n,k)` checks. |
| `OMP_NUM_THREADS=2 .venv/bin/python results/papers3/estdist/extraction_qgpu_llm/prototype.py > results/papers3/estdist/extraction_qgpu_llm/prototype_output.json` | Passed; saved final reconstruction output. |
| `OMP_NUM_THREADS=2 .venv/bin/python results/papers3/estdist/extraction_qgpu_llm/check_control.py` | Passed: QGPU `[[24,8,3]]` has exact distance 3 in both bases after exhausting weights 1 and 2. Both returned `[0,1,2]` witnesses passed zero-syndrome/nonzero-logical checks. |
| `OMP_NUM_THREADS=2 .venv/bin/python results/papers3/estdist/extraction_qgpu_llm/check_pbb.py` | Passed general stabilizer commutation and `(360,12)` checks for both excluded PBB definitions. X-support rank 174 plus Z-support rank 322 differs from stabilizer rank 348, proving the supplied groups are not CSS under row operations. |
| `OMP_NUM_THREADS=2 .venv/bin/python -` — final inline QGPU symmetry assertion | Passed: the CSS class-V target was present among 23 extraction records; all ten QGPU codes retained all `p-1` nonidentity cyclic shifts in both bases. |
| `OMP_NUM_THREADS=2 .venv/bin/python results/papers3/estdist/extraction_balanced/prototype.py` | After the Python compatibility fix, passed CSS, `(n,k)`, weight-9 check rows, and all proposed center symmetries in both bases. Paper witnesses for 160/240/320/390/550 were logical operators of weights 10/12/14/16/18 in both sectors. This command verified witnesses; it did not certify minimum distance. |
| `OMP_NUM_THREADS=2 .venv/bin/python -u results/papers3/estdist/extraction_mm/extract.py` | Final run passed sparse CSS checks for all214 literal rows. Published dimensions matched except the288 row, rebuilding k0. Two earlier slow shared-check attempts were interrupted (exit130). |
| `.venv/bin/python -` — MM interpreted-row heredoc | Passed CSS and rebuilt(294,6) for the documented `1+w^48` interpretation. |
| `OMP_NUM_THREADS=2 .venv/bin/python -u results/papers3/estdist/extraction_mm/verify_controls.py` | Passed both controls' witness checks in both bases; 96 control independently exact8 in0.066/0.049s. |
| `OMP_NUM_THREADS=2 .venv/bin/python -u results/papers3/estdist/extraction_mm/search486.py` | First failed on an incorrect callback signature; corrected rerun certified12 in both bases in0.105/0.150s. |

## Independent review of the merged files

The reviewer used read-only inline Python commands, with `OMP_NUM_THREADS=2`
and `.venv/bin/python -B -`, to compare constructions and check target coverage.
All 23 QGPU/LLM matrices matched their extraction prototypes exactly; all seven
balanced matrices and available paper witnesses matched the balanced
prototype; all 214 literal MM definitions were present unchanged. Both
witnesses for all nine controls had the stated weight, zero detecting syndrome,
and nonzero reduction modulo the appropriate stabilizer row space. A separate
assertion found every one of the 19 requested CSS interpretations, using
`paper_n,paper_k` for the documented MM discrepancy.

Independent inline audits compared literal source cells with fixed t=4
block matrices for156/336/576/624, and fixed t=6 matrices for400. Matrix
equality, CSS, dimensions and all saved witnesses passed. For400,
`search.distance(..., k_table=2, start=11, kmax=11, cover=False, rank=None,
anchors=None, time_limit=10)` exhausted without solutions in both bases:
Z0.782s/2,141,789nodes; X0.579s/2,081,438nodes. A later independent324
inline audit passed in0.616s: explicit matrices agree, check ranks156,
all check weights9, both weight18 witnesses increase stabilizer rank to157.

```sh
OMP_NUM_THREADS=2 .venv/bin/python -B tests/test_estimated_codes.py
```

Passed during independent review:

```text
PASS: CSS and (n,k) for 250 codes; both witnesses for 9 controls; 92 local witnesses
```

This is a snapshot of the results available at that time. The final post-search test output is recorded below. The review found no
matrix/sign/basis-label/certification defect. Its QGPU estimator metadata
correction, from BP-OSD to QDistRnd, was applied by the lead. The final extraction
notes were also inspected and agreed with the source definitions and documented
non-CSS exclusions.

The driver reviewer separately audited all498 saved basis histories without
searches: every smaller weight below every recorded lower bound had an
exhausted/no-best run; all exact basis distances equaled both bounds; all
upper bounds had matching witnesses; overall exact minima equaled the minimum
sector lower/upper bounds. This passed, including39 overall certificates with
one still-unknown, higher-distance sector. The plain test was then strengthened
to cover these lower-bound histories and overall certificates explicitly.

The requested command `.venv/bin/python tests/test_estimated_codes.py` was run
after those changes and passed:250 codes, both witnesses for9 controls,
445 local witnesses. The final post-search snapshot is checked again below.

## Lead-reported distance-driver runs

The following invocation arguments and outcomes were supplied by the lead.
They were not rerun by the audit writer. Commands omit stdout/stderr
redirections; associated log names are recorded where supplied. Each completed
invocation below exited 0. Exact distances apply to both bases unless stated
otherwise. Default invocation budget is 570 seconds; a budget stop is a normal
resumable exit, not completion of all selected codes.

```sh
OMP_NUM_THREADS=2 ESTDIST_TOTAL_SECONDS=90 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/bb_pilot.json 12 10 w8bb
```

Passed: the three requested weight-eight BB controls were exact at 8, 10, and
12 in both bases.

```sh
OMP_NUM_THREADS=2 ESTDIST_TOTAL_SECONDS=300 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/bb_pilot.json 20 60 ge
```

Passed: open `[[144,6,d>=15]]` certified exact distance 15; open
`[[144,10,d>=11]]` certified exact distance 14, both bases.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 12 300
```

Run twice, associated with `local_initial` and `local_resume` logs. Both exited
0. The first stopped at its invocation budget after recording 154 codes; the
second resumed and recorded all 250 codes. Recording a code does not mean its
distance was certified.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 20 3
```

Run twice, associated with `extended` and `extended_resume` logs. Both exited
0. The first stopped at the invocation budget. After the second, the lead
reported 238 codes with exact code distances.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 13 120 balanced_320_64_14
```

Passed: exhaustive lower bound 14 and independently verified weight-14 paper
witnesses certified exact distance 14 in both bases.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 20 60 mm_t3_r6_324_12_20
```

Passed: certified exact distance 18 in both bases, below the paper's randomized
estimate of 20. The construction was unchanged.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 16 120 balanced_390_78_16
```

Passed: certified exact distance 16 in both bases, matching the paper's upper
bound.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/control_sanity.json 12 5 qgpu_24_8_3
```

Passed: fresh exact distance 3 in both bases, weights 1/2 exhausted and a known
weight-3 logical witness verified. The lead's subsequent inline assertion also
passed.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 16 120 balanced_550_110_18
```

Exited0. Both bases exhausted through15 and timed out at16 after120.10/120.08s.
The independently verified paper witnesses have weight18, giving16<=d<=18.
No exact distance is claimed. Total log span340.740s.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 20 60 mm_t4_r7_240_12_16
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 20 60 mm_t4_r11_324_18_18
```

Both exited0 and certified the paper's estimates16/18 in both bases.

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 18 60 llmbb_360_8_18
```

Exited0: both selected classes cprime/dprime have exact distance18 in both bases.
An `OMP_NUM_THREADS=2 .venv/bin/python -` logical-span enumeration over the12
deterministic CSS logical generators of classV found and independently checked
weight30 supports in both bases. These give certified upper bounds30; the
paper's unwitnessed upper bound24 is still only its claim.

## Other lead-reported checks and limitations

- In-memory Python syntax compilation of the four final files passed. The
  earlier `py_compile` attempt failed because its cache destination was outside
  the writable roots; that failure did not establish a syntax defect.
- `git status --short` failed (exit128) because the working directory was not a Git repository.
  No commit, push, stash, branch switch, or history rewrite was performed.
- The macOS search library reported one actual thread although
  `OMP_NUM_THREADS=2` was requested. JSON records requested and actual counts.
- The audit writer ran no additional distance searches while producing this
  file. Final tests and search outcomes are recorded below.

## Final local snapshot

```sh
OMP_NUM_THREADS=2 .venv/bin/python papers/estimated_codes_run.py results/papers3/estdist/local.json 20 60 llmbb_360_12_24_V
```

Exited0. Both bases exhausted through20, giving21<=d<=30 with independently verified weight30 supports. The paper claims only an upper bound24; this remains separate from the verified bounds.

The final requested `.venv/bin/python tests/test_estimated_codes.py` passed:250 reconstructed CSS codes, both witnesses for9 controls,455 local witnesses. Exhaustive histories below every lower bound and all overall exact minimum certificates also passed. In-memory compilation of all four Python files passed; `make_report.py` exited0 and generated250 CSV rows/four remaining commands/one parameter discrepancy.

Final totals:250 registry entries;245 exact code distances; four unresolved logical codes; one k0 definition mismatch. All nine controls are exact in both bases. Open status remains the original paper classification.

The12 logged driver invocations span2691.228s (44.85min), maximum570.755s per invocation; BB pilots and lightweight construction/audit checks were additional. The final invocation took147.474s with56.75MiB peakRSS. Main-sweep RSS snapshots reached190.3MiB. Requested thread count2, actual macOS serial kernel1. No server/remote jobs were started.

Full250-code parameters, row weights, check counts, per-basis bounds/statuses/times/symmetries appear in summary.csv. Witnesses and threshold-level nodes/timings are in local.json. The four continuation commands and empirical node-growth forecasts are in remaining.md. All extraction facts/proofs/scripts and pilots are in extraction.zip; raw paper downloads were removed. Native logs are archived in logs/papers3/estdist/local_runs.zip. Circuit qubit/layer/detector/DEM quantities and sector reduction are inapplicable to this code-distance-only task.

### Requested instances

| Name | Rebuilt(n,k) | Paper d | Z result | X result | Code result | Accumulated search s | Symmetries Z;X |
|---|---|---|---|---|---|---|---|
| `w8bb_72_14_8` | (72,14) | 8 | exact8 | exact8 | exact8 | 0.265 | 2/2;2/2 |
| `w8bb_144_16_10` | (144,16) | 10 | exact10 | exact10 | exact10 | 0.431 | 2/2;2/2 |
| `w8bb_144_10_12` | (144,10) | 12 | exact12 | exact12 | exact12 | 1.601 | 2/2;2/2 |
| `w8bb_144_6_ge15` | (144,6) | 15 | exact15 | exact15 | exact15 | 20.918 | 2/2;2/2 |
| `qgpu_24_8_3` | (24,8) | 3 | exact3 | exact3 | exact3 | 0.192 | 2/3;2/3 |
| `mm_t5_r2_96_12_8` | (96,12) | 8 | exact8 | exact8 | exact8 | 0.508 | 15/15;15/15 |
| `balanced_160_32_10` | (160,32) | 10 | exact10 | exact10 | exact10 | 1.054 | 7/7;7/7 |
| `balanced_240_48_12` | (240,48) | 12 | exact12 | exact12 | exact12 | 3.122 | 11/11;11/11 |
| `mm_t4_r17_486_24_12` | (486,24) | 12 | exact12 | exact12 | exact12 | 1.210 | 80/80;80/80 |
| `qgpu_136_8_14` | (136,8) | 14 | 14<=d<=? | exact14 | exact14 | 9.464 | 16/17;16/17 |
| `qgpu_198_18_10` | (198,18) | 10 | exact10 | exact10 | exact10 | 2.986 | 10/11;10/11 |
| `mm_t4_r5_216_12_14` | (216,12) | 14 | exact14 | exact14 | exact14 | 11.168 | 35/35;35/35 |
| `mm_t3_r5_288_12_16` | (288,0) | 16 | undefined(k0) | undefined(k0) | undefined(k0) | 0.050 | -;- |
| `balanced_320_64_14` | (320,64) | 14 | exact14 | exact14 | exact14 | 31.640 | 1/1;1/1 |
| `mm_t3_r6_324_12_20` | (324,12) | 20 | exact18 | exact18 | exact18 | 37.938 | 53/53;53/53 |
| `llmbb_360_12_24_V` | (360,12) | 24 | 21<=d<=30 | 21<=d<=30 | 21<=d<=30 | 174.814 | 2/2;2/2 |
| `balanced_390_78_16` | (390,78) | 16 | exact16 | exact16 | exact16 | 171.456 | 1/1;1/1 |
| `balanced_550_110_18` | (550,110) | 18 | 16<=d<=18 | 16<=d<=18 | 16<=d<=18 | 362.951 | 1/1;1/1 |
| `mm_t10_r1_630_70_9` | (630,70) | 9 | exact9 | exact9 | exact9 | 1.946 | 8/8;8/8 |

### MM randomized estimates corrected by exact searches

These are literal source definitions, with the two explicitly documented polynomial interpretations retained. The624 result is conditional on the literal xz^{1}1 reading.156/576 source rows repeat one seed, potentially a paper typo; none was changed.

| Name | Paper estimate | Exact code distance |
|---|---|---|
| `mm_t6_r1_156_6_10` | 10 | 6 |
| `mm_t3_r6_324_12_20` | 20 | 18 |
| `mm_t6_r32_336_6_14` | 14 | 6 |
| `mm_t7_r52_370_10_9` | 9 | 8 |
| `mm_t8_r16_400_20_11` | 11 | 12 |
| `mm_t8_r17_400_20_12` | 12 | 11 |
| `mm_t7_r60_450_10_10` | 10 | 9 |
| `mm_t6_r62_516_6_20` | 20 | 18 |
| `mm_t7_r68_530_10_12` | 12 | 7 |
| `mm_t2_r27_576_6_16` | 16 | 6 |
| `mm_t7_r76_610_10_12` | 12 | 11 |
| `mm_t2_r33_624_12_14` | 14 | 10 |
| `mm_t7_r79_640_10_13` | 13 | 8 |

Final archive/consistency check (`.venv/bin/python -` inline): passed both ZIP integrity checks, all12 native-log entries,250 matching CSV/JSON rows,245 exact code distances and four continuation commands. Temporary extraction files and paper downloads were removed only after archiving the task facts/scripts/proofs. A final no-op documentation patch failed its context match and changed nothing; this subsequent append succeeded.
