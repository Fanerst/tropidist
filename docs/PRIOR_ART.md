# Prior art and what the paper can claim (25 October 2026)

A literature check of every ingredient of the method, done on 25 October 2026 by three searches of primary
sources (arXiv, publisher pages, repositories), to decide how strong the paper's novelty claims can honestly be.
The detailed reports, with one entry per work (citation, URL opened, what it computes, overlap, risk), are in
`prior_art/`:

- [distance_dp_tropical.md](prior_art/distance_dp_tropical.md): exact distance algorithms, trellis and width-based
  DP, tensor networks, tropical algebra.
- [circuit_distance.md](prior_art/circuit_distance.md): circuit-distance tools, relaxations, how papers obtain
  their circuit distances.
- [mitm_truncated_search.md](prior_art/mitm_truncated_search.md): meet in the middle, truncated and bidirectional
  search, branch and bound.

Spot-checked here on the arXiv and repository pages themselves: arXiv:2604.09797 (Shaw–Terhal), 1108.0840
(Bocharova et al.), 1611.07164 (Dumer–Kovalev–Pryadko), 2606.23161 (Jia et al.), dist-m4ri's README (0.14.7,
`--model-lb`), and G. Pan's repository. Items the reports mark [unverified] must be re-checked before they are
cited.

## Verdict, component by component

| component | verdict | closest prior work |
|---|---|---|
| distance as a tropical (min-plus) partition function | **viewpoint is prior art** | tropical tensor networks as the zero-temperature partition function, equivalent to DP (Liu–Wang–Zhang, PRL 2021; Liu et al., SIAM J. Sci. Comput. 2023); tropical contraction for distances of tree (concatenated) codes (Sommers–Huse–Gullans, PRR 2025); minimum-weight decoding (Nelson et al., PRR 2025) |
| dense Rank DP | **the classical trellis / branch-decomposition recursion in the min-plus semiring** | Wolf 1978; Forney 1994 (state-space theorem: 2^(cut rank) is the minimal-trellis state count); Kschischang–Sorokine 1995; Vardy 1998; Cunningham–Geelen 2007 (the same subspace as DP state); Kashyap 2008; trellis weight distributions: Desaki–Fujiwara–Kasami 1994, for stabilizer codes Ollivier–Tillich 2006; treewidth DP for classical code distance: Peng et al. 2025 |
| rank-width / subspace-overlap width | **an existing width notion** | the width of Jeong–Kim–Oum (2017, 2021); trellis-width and matroid pathwidth (Kashyap); branch-width FPT results (Hliněný 2006). "Rank-width" proper is a graph parameter (Oum–Seymour): do not present a new parameter |
| polynomial extension to weight enumerators | **standard semiring substitution** | generalized distributive law (Aji–McEliece 2000); trellises (Desaki 1994; Ollivier–Tillich 2006); branch decompositions (Hliněný 2006); tensor networks (Farrelly–Tuckett–Stace 2022; Cao–Lackey; Cao–Gullans–Lackey–Wang 2024); circuit weight enumerators (Ghosh–Boche–Tanggara, October 2026) |
| weight-truncated sparse DP with a meet-in-the-middle split | **core is BEAST** | Bocharova–Handlery–Johannesson–Kudryashov, IEEE TIT 2004: partial-syndrome states on the trellis, a split T = T_F + T_B, forward expansion below T_F, a backward table, matching at every depth, iterative thresholds. Balanced split point: Dumer's matching bipartition (1986/1989); bidirectional free-distance search keeping the least weight per state: Larsen 1973; covering lookahead: Bocharova et al. 2012 |
| weight-bounded search | **an assembly of known parts** | branching on the first unsatisfied check: Dumer–Kovalev–Pryadko's irreducible clusters (arXiv:1611.07164; dist-m4ri); duplicate-free cluster enumeration (Kovalev–Dumer–Pryadko 2013); partial-syndrome tree search with a covering bound and fixed root (Bocharova et al. 2012); the last levels by table lookup (Dumer/Stern matching; perimeter search, BIDA*); relaxed-problem tables (pattern databases); iterative deepening (IDA*); the covering bound equals Tesseract's admissible A* heuristic and the decision-tree decoders' height bound |
| sector reduction | **prior art** | separate X/Z decoding matrices (Bravyi et al., Nature 2024); separation lemma (Beverland–Huang–Kliuchnikov 2024); Webster–Jacob–Higgott's basis filter (2026); dist-m4ri's exact detector dropping (12 October 2026) |
| time-collapse relaxation | **prior art** | Strikis–Browne–Beverland, arXiv:2603.05481, Prop. 3: d_circ ≥ d_ext for single-ancilla CNOT CSS circuits, the code plus hook columns (Cor. 1: equality for non-interleaved circuits); Liang et al., arXiv:2609.37231 (fault-response certificate); dist-m4ri 0.14.5 `--model-lb` (15 October 2026), which sums each check's detectors over rounds for any detector error model |
| lifting relaxed minima back to fault sets | **concurrent work** | G. Pan, GitHub preprint gross-code-distance-12 (13 to 24 October 2026, arXiv "to appear", produced with AI agents): decides which extended-code logicals lift, covers all round counts by a gap argument, proof-logged |
| exact circuit distance as such | **exists for small and medium circuits** | MaxSAT on Stim's WCNF (Tesseract, arXiv:2503.10988: [[72,12,6]] 6, [[90,8,10]] 8); integer programming and connected clusters (Webster–Jacob–Higgott 2026); dist-m4ri's benchmark (October 2026): gross 10, [[90,8,10]] and [[108,8,10]] 8, double gross 12–18, [[360,12]] 12–23 |

## What appears new

As far as the three searches reach:

1. **Trellis / rank DP for circuit-level distance.** The dense form and the weight-truncated sparse form, applied
   to the exact distance of detector error models at 10^4 to 3·10^5 fault mechanisms. No DP, trellis or
   tensor-network method appears in any circuit-distance work found, and Webster–Jacob–Higgott's benchmark has none.
2. **One exact framework with three evaluators, chosen by a cost model.** A min-plus treatment of distances for
   general (non-tree) codes and circuits: dense DP, truncated DP and search, picked by predicted cost. The novelty is
   the unification and the orchestration, not the semiring.
3. **The specific contributions inside the truncated DP:**
   - merging equal states (BEAST works on code trees);
   - a split that varies along the sweep, with joins at every cut;
   - use for Le ≠ 0 on quantum codes and detector error models.
4. **The integrated pipeline**, with an ablation showing what each part buys:
   - sector reduction;
   - the time-collapse bound for any detector error model;
   - lifting with slack;
   - symmetry anchors;
   - covering bound;
   - a syndrome table with k ≥ 2;
   - the DP evaluators.
5. **Certified values beyond everything published:**

   | instance | ours | best previously published or reported |
   |---|---|---|
   | [[288,12,18]] bivariate bicycle circuit | 16, both bases | IBM ≤ 18; Webster–Jacob–Higgott best known 24; dist-m4ri 12–18 |
   | [[360,12]] circuit | 17–21 | dist-m4ri 12–23 |
   | Cornucopia [[900]] and [[1044]] circuits | 9 and 10 | published bounds ≤ 10 and ≤ 11 |
   | mitten [[300,60,14]] circuit | 12 | – |
   | superdense color-code circuit, d = 11 | 11 | – |
   | modular hyperbolic codes up to n = 31,200 | 15 open ranges closed | – |
   | prior benchmark of Webster–Jacob–Higgott | 97 of 126 | 73 |

6. **The audit** ([AUDIT.md](AUDIT.md)): published circuit distances checked across 26 papers; 10 have values that
   are too high.
7. **A small proposition.** The trellis width of a time-ordered detector error model is bounded by the checks
   per round, independent of the number of rounds. It is a corollary of the state-space theorem; present it as an
   observation.

## Wording rules for the paper

- **Dense DP:** not "a new dynamic program for the distance". Say instead "the classical trellis
  (branch-decomposition) recursion in the min-plus semiring, specialised to ker H with a logical label and applied
  to detector error models", and state the identity with Forney's state count.
- **Rank-width:** do not introduce it as a new width. If the name stays, say that it coincides with Jeong–Kim–Oum's
  width and, for linear layouts, with trellis-width.
- **"Tropical partition function":** a viewpoint borrowed from Liu–Wang–Zhang 2021 and the statistical-mechanics
  mapping of decoding. Claim the general circuit-level formulation and its evaluators, not the concept.
- **Truncated sparse DP:** "a min-plus, weight-truncated variant of BEAST with Dumer's split argument, adapted to
  detector error models". Do not claim meet in the middle at a cut, weight splits, threshold truncation,
  partial-syndrome states or iterative deepening.
- **Search:** credit DKP's connected clusters, Bocharova et al.'s Algorithm MD, Dumer/Stern matching, pattern
  databases and IDA*. Claim the combination and its measured reach.
- **Time collapse:** cite Strikis–Browne–Beverland (Prop. 3), Liang et al. and dist-m4ri's model lower bound.
  Present the relaxation as known. Our statement covers any CSS memory detector error model, with no circuit-class
  assumption; state precisely how it reduces to d_ext in the single-ancilla case.
- **Lifting:** independent and concurrent with Pan's preprint. Our lifting is for a fixed number of rounds, while
  Pan covers every round count by a gap argument; a reviewer will ask about this.
- **"First exact" or "first certified":** only for named instances, never in general.
- **Benchmark against dist-m4ri:** name the commit (0.14.7, bed621e). dist-m4ri changed 49 times in a month and
  now has a model lower bound, exact DEM reduction, first-row cluster extension and a hash-table last step.
  Re-run against its newest version before submission, and against Pan's code if it is released.

## What this means for the paper

- **Algorithms and theory are not where the novelty is.** The tropical view, the DP recursion and its width, the
  enumerator extension, meet in the middle, the truncated bidirectional DP, the cluster search and the time-collapse
  bound all have direct prior art. The theory sections (Bin's) must be rewritten as an application and unification
  of known machinery, with the prior work cited at each step.
- **The defensible contribution is capability and results:**
  - one exact framework that applies the trellis / rank DP family to circuit-level distance for the first time,
    with three evaluators under a cost model;
  - certified values beyond all published ones;
  - an audit showing that published circuit distances are often too high;
  - the strongest benchmark of exact distance tools so far.
- **The field is moving now.** dist-m4ri gained a model lower bound, exact DEM reduction and a cluster search close
  to ours within the last four weeks, and Pan's preprint is about to appear. That argues for posting on arXiv soon,
  with the related work stated plainly.

## Housekeeping done with this check

- `bench/METHODS.md`: arXiv:2604.09797 is Shaw–Terhal, not "Webster–Higgott" (checked on arXiv).
- [AUDIT.md](AUDIT.md):
  - IBM's ≤ 18 for the [[288,12,18]] circuit is now a row: we find 16.
  - The mitten rows wait for a fault-model check: version 2 of that paper states 8 for [[150,30,10]], as we find,
    and its other values come from a single-qubit-fault estimator on two rounds.
