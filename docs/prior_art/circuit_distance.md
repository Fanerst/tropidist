# Front 2: computing and bounding circuit distance; time-collapse relaxation and lifting

Prior-art check, 25 October 2026.

**How this was done.** I opened every source listed below myself: arXiv abstract, HTML or PDF pages, GitHub READMEs and commit histories, the online Stim API reference, and the docstrings of the locally installed stim 1.15.0. Text is paraphrased throughout; the report contains one short direct quotation. Items marked **[unverified]** were not checked beyond what is stated next to them. Internal results of this project (from `docs/RESULTS.md` and the project notes) are labelled **(internal)** and are not literature.

---

## 0. Bottom line

1. **(i) Sector reduction is prior art.**
   - Bravyi et al. (Nature 2024) already decode, and upper-bound d_circ, with separate X-type and Z-type decoding matrices that keep only one check type's syndromes.
   - Beverland–Huang–Kliuchnikov (2024) state a general separation lemma for fault distance.
   - Strikis–Browne–Beverland (2026) use the X/Z split as step 1 of their proof.
   - Webster–Jacob–Higgott (2026) filter DEMs to one basis (no exactness argument).
   - dist-m4ri (12 Oct 2026) drops detectors only when a "twin" certificate proves the drop exact, and recovers exactly the minority-basis detectors on CSS circuits.

2. **(ii) The time-collapse relaxation is prior art as a relaxation.**
   - Strikis–Browne–Beverland (arXiv:2603.05481, v1 5 Mar 2026), Prop. 3: d_circ ≥ d_ext for every single-ancilla, CNOT-based CSS syndrome-extraction circuit, for any number of rounds. Here d_ext is the distance of the "extended code", the check matrix with hook (residual) columns appended. This is the collapsed problem for that circuit class.
   - Liang et al. (arXiv:2609.37231, 29 Sep 2026): a "fault-response certificate" D_P ≤ d_circ. It drops the ordinary syndrome constraints, keeps flags and the final checks, and computes D_P exactly by Dijkstra on small seeds.
   - **dist-m4ri 0.14.5** (commit 6241d59, 15 Oct 2026; benchmark runs dated 14 Oct): `compute_model_lower_bound` sums each check's chain of linked detectors, verifies by a rank test that the sums lie in the detector row space, and certifies the model distance with its connected-cluster (CC) search as a lower bound on d_circ.
     - Its double-gross X-basis model is 144 × 720 with distance 12. That is the same size, and the same value, as our X-basis collapsed problem for [[288,12,18]] (internal, `docs/RESULTS.md`).
     - The circuits are from the same source, the tesseract-decoder SI1000 circuits; our notes say so for our circuits, and the dist-m4ri benchmark says so for theirs.
   - The relaxation itself therefore cannot be claimed as new.

3. **Lifting has a concurrent public analogue.**
   - Pan, *Interleaving recovers the full circuit distance…*, is a GitHub-only preprint: repository created 13 Oct 2026, last push 24 Oct 2026, arXiv version announced but not yet posted, not peer reviewed. It proves a telescoping reduction lemma (the collapse), then decides exactly whether each extended logical of weight d_ext and d_ext+1 "lifts" to an undetected fault set. It covers every number of rounds R through a gap argument, and backs each solver decision with a DRAT or VeriPB certificate.
   - Strikis–Browne–Beverland Cor. 1 is a structural lift: for non-interleaved circuits, d_circ = d_ext.
   - dist-m4ri states that its model minima do not lift on the BB circuits, but it does not implement a lift step.
   - Our lifting is therefore at best independent and concurrent work, not first.

4. **(iii) Each component has close prior art.**
   - Symmetry-anchored enumeration: dist-m4ri's start-column restriction; the symmetry-augmented exact search of Fail Fast (2025); translation-anchored cluster search (Rowshan–Devitt 2026); orbit representatives in Pan's proofs.
   - The covering (LP-dual) bound: Tesseract's admissible A* heuristic (2025) is this dual solution exactly: per residual defect, the minimum cost per defect covered. The syndrome-height bound h3 of decision-tree decoders (2025) is the same bound, and it is already used to prune exhaustive enumeration of minimum-weight logicals.
   - Weight-bounded meet-in-the-middle: the "matching bipartition" algorithm (Webster–Jacob–Higgott §4.3.1, with an implementation in Qiskit QEC), and the MITM modes of Qubitserf and codeDistance.

5. **What still looks defensible.**
   - Certified exact values where the public record has only brackets or heuristic upper bounds. For example (internal): [[288,12,18]] gives 16 in both bases, against dist-m4ri's bracket [12,18] and IBM's ≤ 18; BB360 is 17–21, against dist-m4ri's [12,23].
   - A general-DEM pipeline that closes the relaxation gap automatically (enumeration with slack, orbits, windows).
   - The breadth of the benchmark.

6. **Not claimable: "first exact circuit distance of the gross-code circuit".**
   - dist-m4ri's own benchmark certifies 10 for `gross_144_12_12_si1000_r12_X` in 179 s on 128 threads (0.14.0, 11 Oct 2026).
   - Pan claims 10 for the IBM circuit for R ≤ 3 by exact enumeration.

7. **State of practice.** Of about 20 qLDPC works since 2024 checked here, nearly all report circuit distance as a heuristic upper bound.
   - Methods: BP-OSD random search following Bravyi et al., Stim's heuristic search, GPU estimators, ILPs that did not finish.
   - These bounds are often used as if exact, in p^{d/2} fits and in "distance-preserving" claims.
   - Exact values exist only for small circuits, apart from dist-m4ri's October 2026 runs and Pan's preprint.

---

## Summary table

| Work | What it computes | Exact or bound | Largest reported scale | Overlap | Risk |
|---|---|---|---|---|---|
| Stim search tools (Gidney 2021 + docs) | min-weight undetected logical (heuristic / graphlike / MaxSAT export) | heuristic UB / UB unless graphlike / exact if MaxSAT solved | MaxSAT route: BB90 circuit = 8 (Tesseract) | none | low |
| Shutty–Chamberland 2022 | SMT synthesis of FT Clifford circuits | constraint-satisfying circuits | dozens of qubits | net-data-error idea (ii), conceptually | low |
| Tesseract 2025, App. D | d_circ via Stim WCNF + MaxSAT | exact | [[90,8,10]] circuit (180 qubits) = 8 | A* bound ≈ covering bound (iii) | low (MaxSAT); medium (iii) |
| Webster–Jacob–Higgott 2026 | benchmark of 12+ distance methods | exact / heuristic per method | exact BB circuit only for BB72 within 8 h | basis filter (i) | medium |
| dist-m4ri 0.14.x (Oct 2026) | CC / RW / bracket on DEMs; exact detector drop; code-sized model LB | exact (CC), certified LB, RW UB | gross circuit = 10 (179 s, 128 thr); double gross [12,18] | **(i) high, (ii) high, (iii) partial** | **high** |
| Strikis–Browne–Beverland 2026 | extended-code / residual distances; d_circ ≥ d_ext | proven LB; numerics are BP-OSD UBs | gross-code circuit families | **(ii) high**; structural lift | **high** |
| Liang et al. 2026 | fault-response certificate D_P ≤ d_circ; amplification | certified LB (exact D_P on seeds) | seeds [[18,4,4]]; theorems up to [[13320,64,64]] ≥ 48 | **(ii) high** (with flags) | high |
| Pan 2026 (GitHub) | telescoping reduction + exact lifting + all-R gap argument | exact, proof-logged | gross: d_circ = 12 (new circuit); IBM gross = 10 for R ≤ 3 | **(ii) + lifting high**; symmetry | **high (concurrent)** |
| Shaw–Terhal 2026 | d_circ(T) = d_circ(1) for two-round morphing circuits | exact reduction under hypotheses; Gurobi | colour codes to d = 9 | round independence (different mechanism) | medium |
| Beverland–Huang–Kliuchnikov 2024 | fault-distance algorithms; separation; G_red LB | exact if graphlike; LB/UB otherwise | surface-code channels | (i); relaxation-for-LB idea | medium |
| Fail Fast 2025 / DTD 2025 | min-weight logical enumeration; distance via min-weight decoder | exact (small); UB (BB12 ≤ 10) | gross circuit UB only | (iii) high (height bound, symmetry) | medium |
| Formal FT verification (2024–26) | symbolic/SMT/Coq/ZX verification of FT | sound proofs | [[49,1,7]] gadgets (days); 121-qubit codes | none | low |

---

## 1. Stim's distance tools

**C. Gidney, "Stim: a fast stabilizer circuit simulator", Quantum 5, 497 (2021), arXiv:2103.02202.**
- Opened: https://arxiv.org/abs/2103.02202 and the PDF.
- The paper describes the simulator only. I searched its text: it does not mention graphlike errors, undetectable-error search, or DEM-based distance finding. The guarantees below come from the API reference: https://github.com/quantumlib/Stim/blob/main/doc/python_api_reference_vDev.md, read raw, and from the docstrings of stim 1.15.0.

**`Circuit.search_for_undetectable_logical_errors`**
- Starts from each error that flips an observable and repeatedly adds errors touching the lowest-index detection event.
- The search is truncated by three knobs: an edge-degree cap, a cap on intermediate symptom-set size, and an optional rule never to increase the symptom count.
- The docstring opens with "THIS IS A HEURISTIC METHOD" and says results depend on the truncation and on which observable representative is used.
- **Guarantee:** a witness, hence an upper bound only.
- **Scale:** Webster–Jacob–Higgott report that it returned a result only for the smallest BB circuit. QUITS could not run three rounds of a [[144,8,12]] circuit within 100 GB (§6).

**`Circuit.shortest_graphlike_error` / `DetectorErrorModel.shortest_graphlike_error`**
- A breadth-first path/cycle search over errors with at most two symptoms.
- With the default `ignore_ungraphlike_errors=True`, hyperedges are skipped and the result is guaranteed to be an upper bound. With decomposition, even that guarantee can fail.
- **Guarantee:** exact only when every mechanism is graphlike, as on surface codes. Webster–Jacob–Higgott classify it as exact in that case and heuristic otherwise.

**`Circuit.shortest_error_sat_problem` (and `likeliest_error_sat_problem`)**
- Exports a WDIMACS partial-MaxSAT instance whose optimum equals the circuit's fault distance.
- Added by N. Shutty in Stim PR #703 (created 28 Feb 2024, merged 18 Mar 2024; opened via the GitHub API, https://github.com/quantumlib/Stim/pull/703).
- **Guarantee:** exact if the MaxSAT solver proves optimality; an incumbent alone is an upper bound.
- **Scale:** [[72,12,6]] = 6 and [[90,8,10]] = 8 circuits (Tesseract, §2); surface-code gates to d = 5 (§2).

**Overlap and risk.** The tools act on the full DEM, with no sector, collapse, or symmetry step. Novelty risk: low. They are baselines; our benchmark already includes the WCNF route.

---

## 2. SAT, SMT and MaxSAT approaches

**N. Shutty, C. Chamberland, "Decoding merged color-surface codes and finding fault-tolerant Clifford circuits using solvers for satisfiability modulo theories", Phys. Rev. Applied 18, 014072 (2022), arXiv:2201.12450.**
- Opened: https://arxiv.org/pdf/2201.12450.
- Uses Z3 to synthesize Clifford circuits with fault-tolerance constraints. Each single fault is propagated symbolically to its final data error, and constraints forbid propagation parallel to a logical operator.
- Builds FT circuits; does not compute distances at scale. Instances are small, dozens of qubits and time steps.
- Overlap: the conceptual ancestor of judging faults by their net data effect (ii), used for synthesis.
- Risk: low.

**L. Aghababaie Beni, O. Higgott, N. Shutty, "Tesseract: a search-based decoder for quantum error correction", arXiv:2503.10988 (v2, Aug 2025).**
- Opened: https://arxiv.org/html/2503.10988.
- Appendix D: Stim's `shortest_error_sat_problem` plus a MaxSAT Evaluation 2024 solver verify the circuit distance of the [[72,12,6]] circuit (6) and the [[90,8,10]] circuit (8), with d rounds. Larger BB codes use Bravyi et al.'s upper bounds.
- Exact; largest exact instance is the 180-qubit [[90,8,10]] circuit.
- Also relevant to (iii): Tesseract's A* uses an admissible heuristic that sums, over residual detection events, the minimum over allowed errors of weight divided by the number of residual defects that error touches. That is the covering LP-dual solution.
- Risk: low for MaxSAT; medium for the covering-bound claim.

**M. Serra-Peralta, M. H. Shaw, B. M. Terhal, "Decoding across transversal Clifford gates in the surface code", arXiv:2505.13599 (v4, Jul 2026).**
- Opened: https://arxiv.org/html/2505.13599.
- Exact circuit distance of repeated-gate experiments, via the Stim WCNF export and PySAT RC2, for d = 3 and 5 only. The d = 7 run (about 1,600 variables) was stopped after more than 20 h.
- Risk: low. It shows how quickly the full-DEM MaxSAT route stalls.

**W. Lin et al., "Surface code logical operations on a superconducting quantum processor", arXiv:2607.01473 (Jul 2026).**
- Opened: https://arxiv.org/html/2607.01473.
- Appendix K: exact RC2 MaxSAT certificates that the d = 3 experimental circuits have d_circ = 3. Graphlike Stim search (valid there) is used for the scaled schedules up to d = 15.
- Risk: low.

**J. Viszlai et al., "PropHunt: automated optimization of quantum syndrome measurement circuits", arXiv:2601.17580 (ASPLOS 2026).**
- Opened: abstract and https://arxiv.org/html/2601.17580v1.
- MaxSAT (Z3 Tseitin encoding, Loandra solver, 360 s limit) finds minimum-weight logical errors inside randomly grown "ambiguous" subgraphs of the circuit DEM, then rewrites the schedule.
- This is a restricted optimum, hence an upper bound on the global minimum, not a certificate.
- Risk: low.

**Y.-F. Chen, S. M. R. Jafari, C.-Y. Lai, "SAT, MaxSAT, and SMT for QLDPC distance computation: a large-scale empirical study", arXiv:2606.12445 (May 2026).**
- Opened: abstract and HTML.
- Code distance only; the text has no DEM or Stim input. Instances certified within 2 h include LP_544_80_12. BB_288 and BB_360 code distances are listed as not certified.
- Branch-and-bound MaxSAT (MaxCDCL) gives the best coverage.
- Risk: low; not circuits.

**M. Ehatamm, Y. Lee, X. Wu, R. Tao, "End-to-end formalization of quantum error correction" (Lean-QEC), arXiv:2605.16523 (May 2026).**
- Opened: abstract.
- Verified SAT reduction checked in Lean. Lean-checked code-distance proofs for [[90,8,10]] and [[70,6,9]]; scaling to 144 qubits only outside the Lean kernel.
- Code distance only. Risk: low.

**Pan 2026 (§5)** uses CP-SAT, a per-logical SAT model and a frontier DP to decide lift instances, with DRAT (drat-trim, cake_lpr) and VeriPB certificates. This is the only proof-logged circuit-distance work found at gross-code scale.

---

## 3. The Webster–Jacob–Higgott benchmark, dist-m4ri on DEMs, and integer programming

**M. Webster, A. Jacob, O. Higgott, "Distance-finding algorithms for quantum codes and circuits", arXiv:2603.22532 (v1 23 Mar 2026, v2 14 Aug 2026).**
- Opened: https://arxiv.org/abs/2603.22532 and https://arxiv.org/html/2603.22532v2.
- **Methods:**
  - Exact: Brouwer–Zimmermann (Magma), connected cluster (m4riCC = dist-m4ri), MIP (Gurobi, SCIP), MaxSAT (CASHWMaxSAT-CorePlus, PySAT).
  - Heuristic: random information set (m4riRW, QDistRnd), their evolutionary QDistEvol, a BP-OSD syndrome-decoder method, and the three Stim searches.
  - They also describe a matching-bipartition (meet-in-the-middle) enumerator.
- **Circuit handling:** circuits are DEMs (H, L). Algorithm 12 keeps only detectors of one basis and only error mechanisms whose detectors are all in the kept set. No exactness argument is given.
  - BB circuit sizes, raw → filtered: gross 67,752 × 1,728 → 10,368 × 936; double gross 206,352 × 5,184 → 31,104 × 2,736; BB360 346,500 × 8,640 → 51,840 × 4,500.
- **Protocol:** 1 core, 8 GB, 8 h per exact run.
- **Results:**
  - Gurobi and SCIP returned the correct distance for all five rotated-surface circuits (d ≤ 11); two of these finished only after the 8 h limit.
  - m4riCC completed all midout colour circuits.
  - On BB circuits only Gurobi and m4riCC completed any instance within 8 h, the smallest (BB72).
  - No paper-specific lower-bounding technique for circuits, and nothing that merges detectors across rounds.
- **Overlap:** (i), the basis filter. Our notes record that their filtered problems equal our sector problems column for column on all 23 circuits.
- **Risk:** medium for (i), since prior usage exists though without proof. Low otherwise.

**dist-m4ri.** I. Dumer, A. A. Kovalev, L. P. Pryadko, "Distance verification for classical and quantum LDPC codes", IEEE Trans. Inf. Theory 63(7), 4675 (2017), arXiv:1611.07164 (irreducible / connected-cluster technique). Software: https://github.com/QEC-pages/dist-m4ri. Opened: README, `benchmark/BENCHMARK.md`, commit history via the GitHub API.
- **Timeline from the commit log:**
  - 30 Jul 2026: Stim DEM input (`fdem`).
  - 9 Oct: by default, the circuit distance is computed without the minority-basis detectors.
  - 12 Oct: distance-preserving DEM reduction and automatic detector stripping.
  - 15 Oct: a simplified code-sized model as a lower bound on circuit distance.
  - The current version is 0.14.7. Our benchmark ran 0.9.0 and 0.14.7 (internal).
- **(i) Exact detector dropping (`drop=auto`):**
  - A set M of detectors may be dropped if every column touching M has a twin: a column with the same kept detectors that touches no detector of M, with compatible observables. This is checked for each dropped set.
  - On all CSS circuits tested, up to `bb_756` with 1.04 M columns, it finds exactly the minority-basis detectors. Example: gross 1,728 × 67,752 is reduced in 0.08 s.
  - This is our sector reduction, with an exactness certificate.
- **(ii) Code-sized model:**
  - Detectors sharing a non-final measurement record are grouped into one chain per check, and each chain is summed into one model row. For a measured-basis check this telescopes to the parity of the final data measurements on its support, so a column becomes the syndrome of the error's net data or hook error.
  - Measurement errors vanish and equal columns merge. A rank test, rank [H; O] = rank H, certifies that every DEM codeword maps to a model codeword of no larger weight.
  - Reported model distances against circuit distances: bb_72 5/6, bb_90 7/8, bb_108 6/8, gross 8/10, double gross 12/[12,18], bb_360 ≥ 12/[12,23]; tight for some Mitten and torus circuits. Each model takes about 0.1–1 s, except double gross: CC on its 144 × 720 model took 550 s + 467 s.
  - The README notes that the model ignores timing within rounds. The benchmark notes that its lightest codewords do not lift.
- **Certified full-DEM results (0.14.0, 128 threads):** gross 10 in 179 s; BB90 8 in 0.68 s; mitten_270 (custom schedule) 9 in 182 s. Double gross: CC certified only ≥ 11 after 2.8 h.
- **(iii):** connected-cluster search can be restricted to clusters starting at given columns (`start`, `cbeg`, `cend`). Webster–Jacob–Higgott note its use on symmetric codes.
- **Risk: high.** The tool now contains the sector reduction (with proof), the time-collapse lower bound, and certified exact values up to the gross circuit. Nothing in it does lifting.

**Integer programming for circuit distance (state of use).**
- Bravyi et al. 2024 (§6): ILP for code distance only; circuit distance by BP-OSD upper bounds.
- Yoder et al., *Tour de gross*, arXiv:2506.03094: phenomenological distances exact by MIP (CPLEX); circuit distances only upper bounds (≤ 10 gross, ≤ 18 two-gross).
- Shaw–Terhal 2026: Gurobi on the one-round reduced problem, colour codes to d = 9.
- Jacoby–Retzker–Pastawski, *Stairway codes*, arXiv:2603.00228: an ILP decoder gives circuit distances, reported as upper bounds when not optimal (≤ 7, ≤ 8, ≤ 14).
- Sun–Cai, *Layer codes as quantum memories*, arXiv:2609.39522: IP certification affordable only at small distances; otherwise a residual-distance BP-OSD proxy.
- Webster–Jacob–Higgott: Gurobi completed only BB72 among the BB circuits within 8 h.
- Fail Fast 2025: an integer-programming min-weight decoder per logical row gives exact distances where it terminates. Gross circuit: ≤ 10 only.
- Risk to us: low (baselines).

---

## 4. Formal verification and checking of fault tolerance

**W. Fang, M. Ying, "Symbolic execution for quantum error correction programs" (QuantumSE.jl), PLDI 2024, PACMPL 8, art. 189; arXiv:2311.11313.**
- Opened: abstract.
- Symbolic stabilizer states with symbolic Pauli-error phases; debugging QEC programs with over 1,000 qubits (repetition, toric, quantum Tanner codes).
- It is not a fault-distance computation. Risk: low.

**K. Chen, Y. Liu, W. Fang, J. Paykin, X.-C. Wu, A. Schmitz, S. Zdancewic, G. Li, "Verifying fault-tolerance of quantum error correction codes", CAV 2025, pp. 3–27; arXiv:2501.14380 (v3 Jun 2025).**
- Opened: abstract and https://arxiv.org/html/2501.14380v3.
- Fault semantics plus symbolic execution plus an SMT solver (Bitwuzla 0.7.0) decide whether a gadget tolerates t faults. Sound and complete under loop assumptions; returns propagation paths on failure.
- **Scale (Table 1):**
  - Rotated surface [[25,1,5]]: EC gadget 52 s.
  - Rotated surface [[49,1,7]]: EC gadget 435,011 s; CNOT gadget out of time.
  - Toric [[50,2,5]]: EC gadget 1,919 s.
- Proves fault tolerance up to t faults, a distance-type statement, on small gadgets. Risk: low.

**Q. Huang, L. Zhou, W. Fang, M. Zhao, M. Ying, "Efficient formal verification of quantum error correcting programs" (Veri-QEC), PACMPL 9 (PLDI 2025) 1068–1093; arXiv:2504.07732.**
- Opened: abstract and the v1 HTML.
- Assertion and program logic formalized in Coq; Pauli verification conditions discharged by Z3/CVC5.
- 14 codes (5–361 qubits). For surface codes: all error configurations up to 121 qubits in about 200 min; user-constrained errors up to 361 qubits.
- I found no circuit-level measurement-error model in the text. Risk: low.

**B. Rodatz, B. Poór, A. Kissinger, "Fault tolerance by construction", arXiv:2506.17181 (v4 Mar 2026).**
- Opened: abstract.
- "Fault equivalence" means every undetectable fault of one circuit has a counterpart in the other. ZX rewrites restricted to preserve it are used to verify, optimize and synthesize syndrome extraction and cat-state circuits.
- No distance computation at scale is stated on the abstract page **[full text not read]**. Risk: low.

**T. Peham, L. Schmid, L. Berent, M. Müller, R. Wille, "Automated synthesis of fault-tolerant state preparation circuits for quantum error correction codes", PRX Quantum 6, 020330 (2025); arXiv:2408.11894.**
- Opened: abstract.
- SAT synthesis of depth- and gate-optimal FT preparation and verification circuits; evaluations at d = 3 and 5. Risk: low.

**Lean-QEC (§2)** formally verifies code distances only.

**Takeaway.** Formal or SMT fault-tolerance verification works up to about d = 7 gadgets or code-capacity-style settings of about 100 qubits. Nothing in this line computes circuit distance at 10^4–3×10^5 mechanisms. The one proof-logged circuit-distance computation at scale is Pan's (DRAT/VeriPB). If our certificates are not proof-logged, a reviewer may point to it.

---

## 5. Spacetime codes, DEMs, hook analyses, and prior uses of the relaxation and lifting

### 5a. Circuit-to-code reductions and DEM formalism

**D. Bacon, S. T. Flammia, A. W. Harrow, J. Shi, "Sparse quantum codes from quantum circuits", STOC'15, 327–334; IEEE TIT 63(4), 2464 (2017); arXiv:1411.3334.**
- Opened: abstract.
- Maps circuits to sparse subsystem codes; a stabilizer code becomes a subsystem code with the same distance and constant-weight gauge generators. Conceptual. Risk: low.

**N. Delfosse, A. Paetznick, "Spacetime codes of Clifford circuits", arXiv:2304.05943 (v2 May 2023).**
- Opened: abstract and HTML.
- Outcome code to spacetime code; most-likely-error decoding of the spacetime code equals most-likely-fault decoding of the circuit; low-weight check generation.
- I found no fault-distance algorithm or bound in the text. Risk: low.

**D. Gottesman, "Opportunities and challenges in fault-tolerant quantum computation", arXiv:2210.15844 (Solvay 2022).**
- Opened: abstract and PDF.
- Spacetime-code framework. Theorem 6.1 relates correctable fault paths to the spacetime code with its always-unmasked stabilizers, and the correctable number to the "unmasked distance".
- He remarks that conventional FT protocols are degenerate spacetime codes, because different temporal locations produce the same overall error. That is the intuition behind collapsing time, stated informally, with no bound or algorithm. Risk: low.

**M. E. Beverland, S. Huang, V. Kliuchnikov, "Fault tolerance of stabilizer channels", arXiv:2401.12017 (v2 Feb 2024).**
- Opened: https://arxiv.org/html/2401.12017v2.
- Rigorous fault-distance and hook-fault definitions.
- Exact distance when the channel check matrix can be made graphlike (shortest odd cycle).
- An upper bound from the "restricted syndrome graph".
- A **lower bound from the "reduced syndrome graph"**: each hyperedge of weight s is split into s star edges of weight w/s. That is a certified relaxation, but of hyperedges, not of time.
- A separation lemma: if faults split into parts with linearly independent check spans, and composite faults are sums of at most one fault per part, distances combine. That is the general form of the X/Z sector argument.
- Algorithm for hazardous and brazen hooks.
- Overlap: (i), and the idea of certified relaxations for lower bounds. Risk: medium.

**V. Kliuchnikov, M. E. Beverland (Microsoft), US patent US12481909B2, "Lower-bounding distance of stabilizer channel sequence" (priority 11 Dec 2023, granted 25 Nov 2025).**
- Opened: https://patents.google.com/patent/US12481909B2/en; summary only, claims not read **[partly unverified]**.
- A lower bound on the distance of a sequence of three or more channels, from lower bounds on adjacent-pair compositions (computed via shortest graphlike undetectable errors) and "time-local partition" counts.
- A way to bound many-round distances from short windows: related to round independence, but not a time collapse. Risk: low–medium.

**P.-J. H. S. Derks, A. Townsend-Teague, A. G. Burchards, J. Eisert, "Designing fault-tolerant circuits using detector error models", Quantum 9, 1905 (2025); arXiv:2407.13826.**
- Opened: HTML v3.
- Pedagogical DEM formalism. Corollary 8: circuit distance does not depend on the choice of detector matrix, i.e. it is invariant under change of row basis.
- This is the fact behind a certified collapse: keeping only a subspace of the detector row space (chain sums) can only lower the minimum. dist-m4ri states this argument explicitly.
- No distance computation. Risk: low.

### 5b. Hook analyses in code-capacity models with hook columns (the conceptual lineage of the collapse)

**A. G. Manes, J. Claes, "Distance-preserving stabilizer measurements in hypergraph product codes", Quantum 9, 1618 (2025); arXiv:2308.15520 (v1 Aug 2023).**
- Opened: HTML v2.
- Effective distance is analysed in a model where an ancilla fault may deposit any subset of its check's support on the data (a hook column). Analytic proof that HGP codes keep distance d under any single-ancilla schedule.
- Implicitly the extended-code lower bound, applied analytically to one code family; no general multi-round theorem or computation. Risk: low–medium.

**S. J. S. Tan, L. Stambler, "Effective distance of higher dimensional HGPs and weight-reduced quantum LDPC codes", Quantum 9, 1897 (2025); arXiv:2409.02193.**
- Opened: HTML v5.
- Effective (fault) distance under single-ancilla circuits for weight-reduced and higher-dimensional HGP codes; analytic propagation and hook arguments. Risk: low.

**M. Pacenti, A. K. Pradhan, S. K. Borah, B. Vasić, "Turbo-annihilation of hook errors in stabilizer measurement circuits", arXiv:2504.21200 (Apr 2025).**
- Opened: abstract only.
- A decoder. It names the "extended Tanner graph" (hook columns appended) as the standard circuit-level approach; Strikis–Browne–Beverland credit it for the extended-code concept. Risk: low.

**G. Kishony, A. Fowler**, arXiv:2603.28852 (2026), and **Y. Hirai et al.**, arXiv:2603.01628 (v2 Jun 2026).
- Opened: HTML.
- Colour- and surface-code hook avoidance. Distances are checked numerically: Kishony–Fowler up to d = 13 (method not stated in the text read); Hirai et al. with Stim's graphlike search as an upper bound. Risk: low.

### 5c. Explicit uses of the time-collapse relaxation (all 2026)

**A. Strikis, D. E. Browne, M. E. Beverland, "High-performance syndrome extraction circuits for quantum codes", arXiv:2603.05481 (v1 5 Mar 2026; v2 14 Sep 2026).**
- Opened: abstract and https://arxiv.org/html/2603.05481v2.
- **Definitions:**
  - Residual errors are the data errors left by one ancilla (hook) fault.
  - Residual distance Δ(E).
  - Extended code: H_X and L_X with one appended column per residual.
- **Prop. 3:** for any single-ancilla, CNOT-based CSS syndrome-extraction circuit (interleaved or not, any number of rounds, perfect final data readout), d_circ ≥ d_ext(ℰ).
  - Proof: propagate every fault to its data support at the end of the circuit. Every mechanism maps to a data column, a residual column, or nothing. An undetected logical fault set ends as a code-capacity logical.
  - This is the time-collapse relaxation for that circuit class.
- **Cor. 1:** for non-interleaved circuits d_circ = d_ext(ℰ). The proof realizes every extended logical inside one X- or Z-partition, a structural lift.
- **Numerics:** d_ext and Δ are upper-bounded with BP-OSD (App. D), or the Fail Fast adaptive-prior method for the gross code.
  - Results: no non-interleaved circuit reaches 12 for the gross code; uniformly tiled ones reach at most 10.
  - A depth-8 circuit is conjectured to have d_circ = 11.
- **Overlap: (ii) high,** including round independence, for the dominant circuit class; structural lifting.
- **Risk: high.** Cite as the origin of the relaxation.

**Z. Liang, B. Gu, Y.-A. Chen, J. Eisert, Z. Wang, "Ultra-high-distance quantum memories from amplified qLDPC codes", arXiv:2609.37231 (v1 29 Sep 2026).**
- Opened: abstract and HTML v1.
- **The certificate D_P:** the minimum assigned fault count over decompositions of a nontrivial logical into zero-flag gadget responses and weight-one data responses. Ordinary syndrome outcomes are unrestricted; flags and final checks are kept. Hence D_P ≤ d_circ,P.
- **Computation:** exact, by Dijkstra/BFS over the 2^{n−rank H} response states modulo stabilizers (2,048 states for the [[18,4,4]] seed). Amplification theorems multiply certificates.
- **Scale:** seed certificate 3 (seed d_circ = 4) gives [[9738,4,76]] in 57–76 and [[13320,64,64]] in 48–64. Small exhaustive enumerations check seeds for 1, 2 and 8 rounds.
- **Overlap: (ii) high,** a collapse with flags retained. Risk: high.

**dist-m4ri 0.14.5 code-sized model (14–15 Oct 2026):** see §3. A generic DEM implementation of the same relaxation, certified by a rank test. Risk: high.

**G. Pan, "Interleaving recovers the full circuit distance of the gross and [[90,8,10]] bivariate-bicycle codes" (README title; also listed as "A single-ancilla syndrome circuit with circuit distance 12 for the gross code"), GitHub preprint, https://github.com/GavinNull/gross-code-distance-12.**
- Opened: README, `paper/draft.tex`, the v1.0 release page.
- Repository created 13 Oct 2026, last push 24 Oct 2026; arXiv version announced but not yet posted; not peer reviewed. The README says AI agents produced the hypotheses, code and proofs, with a human acting as PI.
- **Lemma 1 (Reduction):** an undetected logical of size w yields an extended-code logical of weight at most w. The proof is the telescoping identity: each check's detectors sum to the final-readout parity.
- **Lemma 2 (light logicals):** weight d_ext and d_ext+1 cases, including one zero-image fault.
- Deciding d_circ ≥ d_ext+2 becomes a finite **lift** problem over complete lists of extended logicals. Gross: 144 of weight 10 and 7,344 of weight 11 per basis. [[90,8,10]]: 585 and 16,830.
- Lift instances are decided for R ≤ 31 (or 25) with CP-SAT, a frontier DP and SAT. A gap argument (a fault-free window splits a logical) extends the result to every R.
- **Certificates:** VeriPB for d_ext and list completeness; DRAT/LRAT for lift instances.
- **Claims:**
  - New period-11 circuits with d_circ = 12 (gross) and 10 ([[90,8,10]]) for all R.
  - The SBB Fig. 12 circuit has d_circ = 11.
  - The IBM gross circuit has d_circ = 10 for R ≤ 3, by exact enumeration.
- **Overlap: (ii) and lifting, very high;** symmetry (orbit representatives); a DP evaluator, cf. (iv).
- **Risk: high, as concurrent work.** It covers specific single-ancilla circuit families, not general DEMs.

### 5d. Other round-reduction results (different mechanism)

**M. H. Shaw, B. M. Terhal, "Optimising quantum error correction using morphing circuits", arXiv:2604.09797 (v2 20 Apr 2026).**
- Opened: abstract and HTML v2.
- Prop. 1: for any two-round morphing circuit (CSS), d_circ(T) = d_circ(1). Exact, by a time-reversal "fold-up" that never increases weight (App. B).
- Prop. 3: alternating normal circuits satisfy d_circ^alt(T) = d_circ^alt(1) = d_circ^non-alt(1) ≥ d_circ^non-alt(T).
- Circuit distances are checked with Gurobi on one round (colour codes, d ≤ 9).
- Overlap: round independence, but by exact folding under structural hypotheses, not by a relaxation. Risk: medium. Cite it.
- **Correction for our own docs:** `bench/METHODS.md` attributes arXiv:2604.09797 to "Webster–Higgott 2026"; the authors are Shaw and Terhal.

**M. T. P. Nguyen, M. Rimbach-Russ, S. Bosco, "Disassembling qLDPC codes for depth-optimal parity-check circuits", arXiv:2608.19917 (v2 4 Oct 2026).**
- Opened: HTML v2.
- Proposes, as future work, screening schedules with the Strikis–Browne–Beverland lower bound plus the Shaw–Terhal single-round reduction. Risk: low.

---

## 6. How recent qLDPC papers state circuit distances (state of practice)

| Paper | Circuits | Stated d_circ | Method | Exact? |
|---|---|---|---|---|
| Bravyi, Cross, Gambetta, Maslov, Rall, Yoder, Nature 627, 778 (2024); arXiv:2308.07915 ([html v2](https://arxiv.org/html/2308.07915v2)) | BB [[72]], [[90]], [[108]], [[144]], [[288]] | ≤ 6, ≤ 8, ≤ 8, ≤ 10 (conjectured = 10; all 936 depth-7 variants ≤ 10), ≤ 18 | BP-OSD on [D_X; η] with random logical η, separate X/Z decoding matrices | UB |
| Tesseract, arXiv:2503.10988 | BB72, BB90 | 6, 8 | Stim WCNF + MaxSAT | **exact** |
| Yoder et al., Tour de gross, arXiv:2506.03094 ([html](https://arxiv.org/html/2506.03094)) | gross, two-gross instructions | ≤ 10, ≤ 18 (≤ 17) | low-weight logical search; MIP only for phenomenological distance | UB |
| Beverland, Carroll, Cross, Yoder, Fail fast, arXiv:2511.15177 | BB(6), BB(12), BB(18) circuits | 6, ≤ 10, ≤ 18 | min-weight decoder (exact) / random BP-OSD (UB) | UB for gross |
| Kang et al., QUITS, arXiv:2504.02673 ([html](https://arxiv.org/html/2504.02673)) (Quantum 9, 1931 (2025) per SBB's bibliography **[journal page not opened]**) | BPC [[72,8,8]], [[90,8,10]], [[144,8,12]] | ≤ 6, ≤ 8, ≤ 9 (2–3 rounds) | Stim `search_for_undetectable_logical_errors`; 3 rounds of [[144]] infeasible at 100 GB | UB |
| Shaw, Terhal, PRL 134, 090602 (2025); arXiv:2407.16336 ([html v3](https://arxiv.org/html/2407.16336v3)) | morphing BB | UBs | BP-OSD, two-round circuit, X-only noise | UB |
| Strikis, Browne, Beverland, arXiv:2603.05481 | gross families | non-interleaved ≤ 11; Fig. 12 circuit conjectured 11 | d_ext UBs (BP-OSD / adaptive priors) | UB / conjecture |
| Jacoby, Retzker, Pastawski, arXiv:2603.00228 ([html](https://arxiv.org/html/2603.00228)) | Stairway (Floquet BB) | 4, 6 exact; ≤ 7, ≤ 8, ≤ 8, ≤ 14 | ILP decoder; UB when not optimal | mixed |
| Zhang, Chen, Duan et al., Routing codes, arXiv:2606.25330 v2 ([html](https://arxiv.org/html/2606.25330)) | weight-7/11 routing codes | UBs, at most one below d | BP-OSD random, > 10^6 trials | UB |
| Bi, Chang, Puri, arXiv:2606.30592 ([html](https://arxiv.org/html/2606.30592)) | BB72/90/144, biased ancillas | depolarizing ≤ 8, ≤ 10; biased "restored" to 10, 12 | BP random search | UB |
| Bhardwaj, Ma, …, Preskill, Cain, Xu, Huang, "High-rate qLDPC processors" (mitten), arXiv:2607.28795 v2 2 Oct 2026 ([html](https://arxiv.org/html/2607.28795)) | mitten [[150]]…[[975]] | 8, 12, 14, 16, 18, 20, 22, 24 (claimed distance-preserving except [[150]]) | GPU estimator sQetch on a two-round circuit, single-qubit Pauli faults; Table 8 calls the values upper bounds | UB |
| Lu, Li, Deng, Cornucopia, arXiv:2608.02773 v2 ([html](https://arxiv.org/html/2608.02773)) | [[252]]…[[2844]] | ≤ 5, 8, 10, 11, 14, 16, 18 | BP-OSD (method of Bravyi et al.); p_L fits use p^{d/2} with the code distance | UB |
| Liang et al., arXiv:2609.37231 | amplified | e.g. 57–76, 48–64; level-1 [[90,8]] 6–8 | certified LB + constructive UB | interval |
| Sun, Cai, arXiv:2609.39522 | layer codes | proxy (residual distance); IP proofs only where affordable | BP-OSD proxy / IP | mostly proxy |
| Wills et al., arXiv:2605.21898 ([html](https://arxiv.org/html/2605.21898)) | gross idling, morphing | "believed" 12; regular circuit stated as 10 | simulation | belief |
| Webster–Jacob–Higgott 2026 | 7 BB circuits | exact only BB72 within 8 h | 5 exact + 7 heuristic methods | mostly open |
| dist-m4ri benchmark (Oct 2026) | BB72–BB360, mitten, torus | gross 10, BB90/108 8; double gross [12,18]; bb_360 [12,23] | CC on exactly reduced DEM; model LB | **exact to gross** |
| Pan 2026 (GitHub) | gross, [[90,8,10]] | 12, 10 (new circuits); IBM gross 10 (R ≤ 3) | lift computations, proof-logged | **exact (claimed)** |

**Internal context.** The project's notes and docs record cases where published heuristic values were too high:
- Cornucopia: [[900]] 9 vs ≤ 10; [[1044]] 10 vs ≤ 11; [[2304]] ≤ 14 vs 16; [[2844]] ≤ 16 vs 18.
- Mitten published schedules: [[200,40,12]] 9; [[300,60,14]] 12; [[500,100,16]] 9 in the X basis.
  - Noise models may differ from the paper's single-qubit-fault estimator. Check that before stating this as a contradiction.
- Double gross: 16 vs IBM ≤ 18, and vs a heuristic best-known value of 24 in Webster–Jacob–Higgott's data.

**Pattern.** Since 2024 the default is the Bravyi et al. randomized BP-OSD upper bound, or a Stim/GPU heuristic, often on 1–2 rounds or restricted noise. These values are then used as d_circ in p_L ∝ p^{d/2} fits and in "distance-preserving" claims. Certified values were confined to:
- surface/colour circuits up to d ≈ 11 (MIP, CC), or d ≤ 5 by MaxSAT on full gate circuits;
- BB72 and BB90 (MaxSAT);
- small seeds (exhaustive or Dijkstra).

This changed only in October 2026, with dist-m4ri 0.14 (gross circuit) and Pan's preprint.

---

## Implications for our novelty claims

**(i) Exact sector reduction: prior art.**
- Bravyi et al. 2024 define d_circ^Z on the Z-error/X-check decoding matrix and decode the sectors separately.
- Beverland–Huang–Kliuchnikov 2024 give the general separation lemma.
- Strikis–Browne–Beverland 2026 (proof of Prop. 3, step 1) argue it for CSS circuits.
- Webster–Jacob–Higgott 2026 use a basis filter.
- dist-m4ri (12 Oct 2026) implements exact detector dropping with a per-instance twin certificate.
- Present it as a standard, known reduction with our exactness condition, citing these. Do not list it as a contribution.

**(ii) Time-collapse relaxation: prior art as a relaxation.**
- It is Strikis–Browne–Beverland's extended-code bound d_circ ≥ d_ext (March 2026, single-ancilla CNOT circuits, any number of rounds).
- Liang et al.'s fault-response certificate (September 2026) is the same idea with flags.
- dist-m4ri's code-sized model (14–15 Oct 2026) is the generic DEM version, certified by a rank test. On the double-gross X circuit it yields the same 144 × 720 problem and the same value (12) as our collapse.
- Pan's Lemma 1 (October 2026) states the telescoping identity explicitly.
- Our internal notes show the collapse in use by 2 Oct 2026. That predates dist-m4ri and Pan, but not Strikis–Browne–Beverland or Liang et al., and our work is unpublished.
- Recommended wording: "we use the extended-code relaxation of [Strikis–Browne–Beverland], which for a detector error model amounts to summing each check's detector chain (cf. dist-m4ri 0.14.5); it gives a round-independent certified lower bound."
- Any genuinely new element (for example handling flags or non-single-ancilla circuits generically, or the slack analysis) must be argued specifically.

**Lifting: independent and concurrent, not first.**
- Pan's preprint does exact, proof-logged lifting of complete lists of the lightest extended logicals, extended to every R, for the gross and [[90,8,10]] circuit families.
- Strikis–Browne–Beverland Cor. 1 lifts structurally for non-interleaved circuits.
- dist-m4ri observes non-lifting but closes the gap only by full-DEM search, and leaves the double-gross bracket at [12,18].
- Defensible claims:
  - (a) a general, automated lift-with-slack plus enumeration plus symmetry procedure for arbitrary CSS memory DEMs;
  - (b) its success at scales where others stop: [[288,12,18]] = 16 in both bases, BB360 17–21, Cornucopia, mitten (all internal). It should be benchmarked against dist-m4ri ≥ 0.14.7, and against Pan's method if the code is released.
- Cite Pan as concurrent work if it appears on arXiv or remains public. Note that our lifting fixes R, whereas Pan proves all R through a gap argument. A reviewer may ask for the same.

**(iii) Symmetry, covering bound, meet in the middle: each component is prior art.**
- Symmetry-anchored enumeration: dist-m4ri start columns; Fail Fast's symmetry-augmented exact search; Rowshan–Devitt's translation-anchored cluster search (arXiv:2609.39395, code distance); orbit representatives in Pan's VeriPB proofs.
- Covering bound: Tesseract's admissible A* heuristic, and the decision-tree decoders' syndrome-height bound h3, which already prunes exhaustive minimum-weight-logical enumeration. Our greedy dual ascent is at most a refinement.
- Weight-bounded meet in the middle: matching bipartition (Webster–Jacob–Higgott §4.3.1; Qiskit QEC); Qubitserf and codeDistance MITM modes (from our `bench/METHODS.md`, not re-opened here).
- Claim the integration and its measured effect (ablations), not the components.

**(iv) Rank-DP evaluators: outside this front.**
- Pan uses a frontier dynamic program as one of three lift evaluators, so DP-based exact evaluation of lift instances also has a concurrent analogue. I did not search the trellis/DP literature.

**Claims to avoid.**
- "First exact circuit distance of the [[144,12,12]] circuit": dist-m4ri certifies 10 in 179 s; Pan claims 10 for R ≤ 3.
- "First certified lower bound independent of rounds": Strikis–Browne–Beverland and Liang et al. predate it.
- "First to reduce circuit distance to a code-capacity problem": Strikis–Browne–Beverland; earlier analytic uses in Manes–Claes and Tan–Stambler.
- "First to reduce rounds exactly": Shaw–Terhal (morphing/alternating circuits).
- "Only certifying tool at 10^4–10^5 mechanisms": dist-m4ri 0.14 now certifies DEMs of 72,576 columns (gross; reduced to 8,784).

**State of practice.** Circuit distances in the 2024–2026 qLDPC literature are overwhelmingly heuristic upper bounds; I count about 15 of the roughly 20 works in the §6 table. Some are later shown too high: by our internal results, and in dist-m4ri's benchmark, which warns that the nominal distances in its circuit file names are not always correct. Exact certification beyond about 10^4 mechanisms appeared in public only in October 2026. This makes a strong motivation paragraph. Phrase it as "most reported values are heuristic upper bounds", citing the §6 table, rather than "no exact values exist".

**Recheck before submission.** dist-m4ri changes fast (49 commits between 18 Sep and 15 Oct 2026). Also check whether Pan's preprint has reached arXiv and whether Strikis–Browne–Beverland v3 or a follow-up adds computational lifting.

---

## Not verified or left open

- Microsoft patent US12481909B2: claims not read, only the Google Patents summary.
- Pacenti et al.: abstract only.
- Rodatz–Poór–Kissinger: abstract only.
- QUITS: journal reference taken from a bibliography.
- Kishony–Fowler: method for the d ≤ 13 check not stated in the part read.
- dist-m4ri and Pan numbers are as reported by their authors; I did not rerun them. Our benchmark ran dist-m4ri 0.14.7 separately (internal).
- I did not find a pre-2026 paper that states the extended-code / time-collapse inequality as a general theorem or computes it at scale. Earlier work uses it only implicitly in analytic hook arguments. Older coding-theory or fault-tolerance texts were not searched exhaustively.
