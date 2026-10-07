# Methods for quantum code and circuit distance

Survey date: 4 October 2026. This is an evidence-linked competitor inventory and execution guide, **not a benchmark result or a claim that our method wins**. Sources are the read-only local 2026 catalog and allowed primary paper/tool pages. Unknown means the inspected sources did not verify the fact; it does not mean a tool lacks the feature. Published scale examples below are not asserted to be world records.

The target is `min |e| : H e = 0, L e != 0` over GF(2). A column costs one original, undecomposed fault mechanism. The benchmark's MatrixMarket coordinate-pattern files and result contract are specified by [common.py](common.py); [ours.py](adapters/ours.py) is the adapter reference. Classical minimum distance of `ker(H)` is generally wrong because it includes logically trivial errors. General stabilizer Pauli distance also needs qubit support weight, with an X/Z pair counted once; ordinary Hamming weight of a doubled symplectic vector is different. CSS sector distance and the supplied DEM fault objective do use the benchmark's unit column weights.

Use the same `full`, `sector`, or `collapsed` variant for every competitor. `sector` is an export-checked exact reduction; `collapsed` is a relaxation and has its own ground truth. Charge matrix loading, conversion, logical-basis construction, model building, solver startup, and witness recovery to wall time. Do not seed a search with metadata ground truth. A timeout incumbent needs a checked witness; a lower bound needs exhaustive exclusion, UNSAT, or a valid optimization bound. A solver's completed optimum is a computational certificate in the benchmark sense; a separately checkable DRAT/LRAT/Lean proof is a stronger and distinct deliverable. Float MILP bounds rely on solver tolerances; round conservatively and record them.

## 1. Competitor inventory

Each row separates mathematical capability from a documented interface. Parallelism means a verified native control unless explicitly described as independent processes. All instance sizes refer to data qubits unless labelled total qubits or fault variables; decoding simulations are not distance solves.

| Method/tool and reference | Algorithm class | Return / proof | Accepted input | Parallelism | Licence; installation and dependencies | Source-reported solved scale / limitations |
|---|---|---|---|---|---|---|
| Stim `shortest_graphlike_error` ([API](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimcircuitshortest_graphlike_error), [paper](https://arxiv.org/abs/2103.02202)) | Breadth-first path/cycle search | Exact restricted graphlike optimum; exact full target only when **all original mechanisms have detector degree ≤2**; otherwise witness upper bound after dropping hyperedges. | Stim circuit or DEM; H,L via the synthetic encoding in §2. | No thread option verified in search API; run one process. | Apache-2.0; `pip install stim`; Python/C++ wheel ([repo](https://github.com/quantumlib/Stim), [PyPI](https://pypi.org/project/stim/)). | Local installed doc example repetition distance 7, 10 rounds; largest distance-search solve not verified. A decomposition may change the fault-count objective; do not infer an original-mechanism witness from its component count. |
| Stim `search_for_undetectable_logical_errors` ([API](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimcircuitsearch_for_undetectable_logical_errors)) | Truncated syndrome-state / hyperedge search | Heuristic witness upper bound; failure does not prove a lower bound. | Circuit API; arbitrary H,L or a DEM via synthetic circuit in §2. | No thread control verified; independent parameter/seed-label runs are separate budgets. | Same Stim installation/licence as above ([repo](https://github.com/quantumlib/Stim)). | Local doc example surface distance 5, 5 rounds; maximum verified solve unknown. Truncation depends on intermediate detector count, edge degree, and logical representatives. |
| Stim WCNF route + PySAT RC2 / external complete MaxSAT ([Stim API](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimcircuitshortest_error_sat_problem), [RC2](https://pysathq.github.io/docs/html/api/examples/rc2.html)) | Uniform-weight partial MaxSAT; core-guided RC2 or external solver | Exact on completed optimization; incumbent alone upper bound; bounds/proof logging depend on backend. | `Circuit.shortest_error_sat_problem(format='WDIMACS')`; H,L/DEM through §2; generic WCNF keeps an explicit column map. | RC2 has no general thread option in inspected API; backend-dependent external parallelism. | Stim Apache-2.0; PySAT MIT, bundled solvers have separate licences; `pip install python-sat` ([PySAT repo](https://github.com/pysathq/pysat), [PyPI](https://pypi.org/project/python-sat/)). | [Tesseract Appendix D](https://arxiv.org/html/2503.10988#A4) reports exact circuit BB72=6, BB90=8 using this route; 144/180 total qubits. This does not establish an RC2-specific scale record. |
| Direct H,L SAT + cardinality (PySAT/CaDiCaL/Glucose etc.; [solver API](https://pysathq.github.io/docs/html/api/solvers.html), [cardinality API](https://pysathq.github.io/docs/html/api/card.html)) | XOR-to-CNF Tseitin encoding, bounded SAT, iterative/binary search in weight | UNSAT at weight ≤K proves d≥K+1; SAT supplies an upper witness; exact when they meet. Optional proof log needs an independent checker and verified encoding. | Boolean H,L matrices, converted from MatrixMarket/undecomposed DEM; not a dedicated native DEM distance entry point. | Typical PySAT backends one thread; solver portfolios or independent logical-row subproblems must be charged. | PySAT MIT plus backend licences; `pip install python-sat` ([repo](https://github.com/pysathq/pysat)). | Dedicated implementations and actual published code-size benchmarks appear in the QDistSAT/DistQLDPC/Qubitserf rows; no measured performance claimed for the survey's reference encoding. |
| SciPy `milp` / HiGHS ([API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html), [HiGHS](https://github.com/ERGO-Code/HiGHS)) | MILP with integer parity quotients | Optimal value/incumbent plus MIP dual bound; exact if checked witness closes valid rounded dual bound. | Sparse numeric linear model; H,L and DEM by §2. | SciPy's documented options do not include `threads`; do not claim OMP_NUM_THREADS alone enforces HiGHS threads. Direct highspy settings require separate version verification. | SciPy BSD ([PyPI](https://pypi.org/project/scipy/)); HiGHS MIT ([repo](https://github.com/ERGO-Code/HiGHS)); `pip install scipy`, NumPy and bundled HiGHS. | Only a 3-column encoding smoke check run in this survey; no source-reported largest quantum distance solve verified for this frontend. Commercial/open-source alternative solver rows below are necessary competitors. |
| Lean-QEC ([paper](https://arxiv.org/abs/2605.16523), [repo](https://github.com/VerifiedQC/Lean-QEC)) | Verified SAT reduction; CaDiCaL/LRAT through Lean `bv_decide` | Machine-checked code-distance **lower** bound; exact needs a matching witness. | Lean CSS/stabilizer definitions and generated BitVec instances; generic H,L/DEM command not verified. | Native distance thread controls not verified. | Apache-2.0; Lean4/Mathlib4; after approved source acquisition: `lake exe cache get`, `lake build` ([README](https://github.com/VerifiedQC/Lean-QEC)). | Paper reports Lean-checked [[90,8,10]], [[70,6,9]]; [[144,12,12]] SAT scaling outside kernel is explicitly a different validation level ([paper](https://arxiv.org/html/2605.16523)). |
| Tensor-network weight enumerators: Farrelly–Tuckett–Stace; Cao–Gullans–Lackey–Wang ([2021](https://arxiv.org/abs/2109.11996), [2023, revised 2024](https://arxiv.org/abs/2308.05152)) | Exact tensor contraction / polynomial enumerators / dynamic programming | Exact distance from nontrivial logical coefficients when contraction/arithmetic is exact; truncation is not a certificate. | Seed/encoding tensor networks; an arbitrary H,L factor graph is a possible derivation, not a verified public DEM CLI. | Depends on contraction implementation; unverified here. | Runnable distance repository, installation, dependency set and software licence not verified from inspected papers. | Quantum Lego reports calculations of order 100–200 qubits; Table2 has 85-qubit HaPPY central-logical stabilizer distance 23, which is **not** the whole code's distance 3 ([paper](https://arxiv.org/html/2308.05152)). No general DEM scale verified. |
| Fault-response certificates / amplifier transfer (`dp_certificates`) ([paper](https://arxiv.org/abs/2609.37231), [repo](https://github.com/zijian-liang/dp_certificates_github)) | Dijkstra/BFS on response quotient; analytical certificate multiplication | Exact fault-response optimum D_P, a **lower bound** on full circuit distance; exact circuit value only if matching upper history and theorem hypotheses hold. | Structured CSS gadget/check/order/fault-response inputs; no arbitrary DEM distance CLI verified. | Thread control unverified. | Licence unverified; Python≥3.10, no runtime packages; `pip install -e ./dp_certificates`; `python -m dp_certificates solve --example flagged422` ([README](https://github.com/zijian-liang/dp_certificates_github)). | [[9738,4,76]]: circuit interval [57,76]; [[13320,64,64]]: [48,64]. These are theorem/certificate bounds, not generic exact DEM solves ([paper](https://arxiv.org/html/2609.37231)). Local Python3.9 cannot run this package. |
| Morphing/alternating-round reduction ([Webster–Higgott 2026](https://arxiv.org/abs/2604.09797)) | Structure-specific exact reduction, followed by integer programming | Exact if two-round morphing hypotheses hold and reduced optimization completes; no universal DEM guarantee. | Designed morphing circuits / one-round reduced matrices; generic package API not verified. | Depends on reduced solver; not verified. | Independent solver/reduction distribution and licence unverified; uses Gurobi in paper. | Proposition1/§2.5 reduction and Table6 circuit examples; sizes in §3. It is a preprocessing competitor on matching structured instances, not a separately installed general solver. |
| PropHunt distance scoring ([paper](https://arxiv.org/abs/2601.17580), [repo](https://github.com/jviszlai/PropHunt)) | Connected ambiguous subgraph selection + MaxSAT | Restricted subgraph optimum / candidate upper bound; inspected formulation does not certify unrestricted global distance. | Syndrome extraction circuits and selected DEM subgraphs; direct arbitrary H,L invocation unverified. | Controls unverified. | Licence/build/dependencies not independently verified; source available on GitHub. | Circuit scheduling/optimization examples in §3; no certified unrestricted scale record established by this survey. |
| Gurobi native MILP ([API example](https://pypi.org/project/gurobipy/), [bounds](https://docs.gurobi.com/projects/optimizer/en/12.0/reference/attributes/model.html), [parameters](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html)) | Integer parity-quotient MILP | Incumbent UB and valid dual LB; completed optimum exact within solver numerical tolerances. | Generic H,L linear model (§2), undecomposed DEM converted to H,L. | `Threads`; seed and time controls. | Proprietary; `pip install gurobipy`, full licence needed beyond restricted wheel licence ([PyPI](https://pypi.org/project/gurobipy/)). | [[544,80,12]] code solved in 3580.673s ([QDistSAT Table19](https://arxiv.org/html/2606.12445v1#A1.T19)); circuit examples in §3 and codeDistance scale note. Global largest not verified. |
| SCIP via OR-Tools MPSolver ([example](https://developers.google.com/optimization/mip/mip_example), [API](https://or-tools.github.io/docs/python/classortools_1_1linear__solver_1_1pywraplp_1_1Solver.html)) | Integer parity-quotient MILP | `OPTIMAL` or checked incumbent plus `BestBound`; numerical certificate caveat as above. | Generic H,L model (§2); DEM conversion. | `SetNumThreads`, subject to backend support; `SetTimeLimit` in milliseconds. | OR-Tools Apache-2.0; current SCIP Apache-2.0 ([OR-Tools](https://github.com/google/or-tools), [SCIP](https://github.com/scipopt/scip)); `pip install ortools` includes SCIP. | Published MIPDist circuit-family results in codeDistance scale note; individual maximum not verified ([paper](https://arxiv.org/html/2603.22532v1)). |
| OR-Tools CP-SAT ([docs](https://developers.google.com/optimization/cp/cp_solver), [repo](https://github.com/google/or-tools)) | Integer constraint programming / SAT with linear parity equations | Integer optimum and `best_objective_bound`; exact when checked witness and certified integer bound meet. | H,L parity-quotient model; DEM conversion; not a dedicated native distance API. | `num_search_workers`; `random_seed`, `max_time_in_seconds`. | Apache-2.0; same `ortools` distribution as above. | Largest quantum/DEM distance solve for this direct frontend not verified; codeDistance lists CP_SAT as an optional MIP backend ([README](https://github.com/m-webster/codeDistancePYPI)). |
| Generic MaxCDCL2024 / enMaxCDCL CP2026 ([authors' repo](https://github.com/zjl9959/enMaxCDCL_CP26), [QDistSAT comparison](https://arxiv.org/abs/2606.12445)) | Branch-and-bound MaxSAT with CDCL / lower-bound strengthening | Completed `OPTIMUM FOUND` exact; interrupted incumbent needs model; independently checked proof logging not verified for these releases. | WCNF from explicit H,L encoding or Stim circuit export (§2); WCNF dialect/model-print configuration needs smoke audit. | No native thread flag verified; CPU limit needs wall watchdog. | Inherited MIT text in [Main.cc](https://github.com/zjl9959/enMaxCDCL_CP26/blob/main/codes/enMaxCDCL/simp/Main.cc); project/new-modification licence unverified. Linux GCC≥15.2, static libstdc++/zlib; `make rs`; public binary. | QDistSAT's MaxCDCL code results [[544,80,12]] in2775.920s and [[250,10,15]] in6525.009s ([Tables19/24](https://arxiv.org/html/2606.12445v1#A1.T19)); these do not benchmark the newer enMaxCDCL release. |
| Proof-logging WMaxCDCL ([Vandesande–Coll–Bogaerts](https://arxiv.org/abs/2511.10273)) | Branch-and-bound MaxSAT with VeriPB certificates | Separately checkable optimum proof described; usable release not verified. | Weighted partial MaxSAT; H,L reduction applies mathematically. | Unverified. | Checked paper promises later software/data release; source, licence, install, dependencies and size unverified ([paper v1](https://arxiv.org/html/2511.10273v1)). | Quantum/circuit distance scale not verified. Do not attribute this proof feature to MaxCDCL2024/enMaxCDCL. |
| Open-WBO ([repo](https://github.com/sat-group/open-wbo), [CSS decoding paper](https://arxiv.org/abs/2410.01673)) | Core-guided / linear-search partial MaxSAT | `s OPTIMUM FOUND` exact; `s SATISFIABLE` and model UB only; `o` alone insufficient. | WCNF; H,L via explicit encoding, DEM via extraction or synthetic Stim export. | Thread controls unverified. | MIT ([licence](https://github.com/sat-group/open-wbo/blob/master/LICENSE)); `make rs`, bundled MiniSAT/Glucose ([INSTALL](https://github.com/sat-group/open-wbo/blob/master/INSTALL)); C++/zlib I/O ([source](https://github.com/sat-group/open-wbo/blob/master/Main.cc)); no pip package verified. | Dedicated distance maximum unverified; CSS paper's decoding performance is not a distance certification. |
| Fail Fast / adaptive decoder-prior perturbation ([2025 paper](https://arxiv.org/abs/2511.15177), [LR circuit application](https://arxiv.org/html/2603.05481v1)) | Repeated decoder search with perturbed priors | Witness UB; repeated failure/confidence conjecture is not an exhaustive LB. | Detector/check matrices plus decoder; complete public arbitrary H,L CLI not verified. | Independent trials; native controls unverified. | Download source, software licence/install/dependencies unverified from inspected pages. | LR gross-code d=11 conjecture after10,000 outer loops, UB only; see §3. |
| dist-m4ri random window (`method=1`) ([repo](https://github.com/QEC-pages/dist-m4ri), [Dumer–Kovalev–Pryadko](https://arxiv.org/abs/1611.07164)) | Random window / information-set search | Witness UB only. | GF(2) MatrixMarket H,L or Hx/Hz; native Stim DEM `fdem`. | POSIX `threads`; independent seeded trials. | GPL-2.0; GCC/POSIX/libm4ri; `cd src`, `make all` ([README](https://github.com/QEC-pages/dist-m4ri)). | Largest dedicated RW distance search verified here unknown; quantum examples in prior comparisons, not exact certificates ([survey](https://arxiv.org/abs/2603.22532)). |
| dist-m4ri connected cluster (`method=2`) ([repo](https://github.com/QEC-pages/dist-m4ri), [paper](https://arxiv.org/abs/1611.07164)) | Exhaustive irreducible connected-cluster enumeration | Completed exclusions give LB; matching checked minimum witness exact. | Same native H,L/DEM format. | POSIX threads; unrestricted complete scan required. | Same GPL/GCC/libm4ri build ([README](https://github.com/QEC-pages/dist-m4ri)). | Code [[544,80,12]] in3641.403s ([Table19](https://arxiv.org/html/2606.12445v1#A1.T19)); Vine circuits total683 qubits/d6, total535/d7 ([Table1](https://arxiv.org/html/2606.20263v1)); versions/resource counts not necessarily current release. |
| dist-m4ri concurrent bracketing (`method=3`) ([repo](https://github.com/QEC-pages/dist-m4ri), [wrapper](https://github.com/QEC-pages/dist-m4ri/blob/master/dist_m4ri.py)) | Concurrent RW UB + CC LB | `(dmin,dmax,rw_steps)`; exact when proved bounds meet and witness checks. | Same H,L/DEM; `pmin=0` preserves all mechanisms. | POSIX threads; auto-throttling documented. | Same build/licence; Python wrapper optional. | Current multithreaded bracketing's largest verified solve not stated in inspected source; do not transfer old single-thread timing as a new result. |
| QDistRnd ([repo](https://github.com/QEC-pages/QDistRnd), [paper](https://arxiv.org/abs/2308.15140)) | Random information sets, CSS/stabilizer low-weight search | UB; empirical/conditional failure estimate is not a certificate ([confidence discussion](https://qec-pages.github.io/QDistRnd/doc/chap3.html)). | GF(q) CSS checks or interleaved symplectic stabilizer; MTXE/MTX; H,L via derived CSS Z-sector (§2); native DEM interface unverified. | Native threads/seed controls not verified. | GPL-2.0-or-later; GAP/GUAVA, bundled GAP≥4.13; no compile step ([install](https://github.com/QEC-pages/QDistRnd/blob/main/README.md)). | Manual [[900,182,8]]:1000 sets/about15s notebook, UB only ([example](https://qec-pages.github.io/QDistRnd/doc/chap2.html)); global largest unknown. |
| ldpc BP+OSD distance sampling ([repo](https://github.com/quantumgizmos/ldpc), [paper](https://arxiv.org/abs/1904.02703), [API](https://software.roffe.eu/ldpc/ldpc/bposd_decoder.html)) | BP+ordered-statistics syndrome decoding as repeated searcher | Checked logical residual or augmented-syndrome witness UB; no LB/confidence guarantee. | Binary NumPy/SciPy PCM + syndrome; H,L sampling/DEM extraction (§2). | `omp_thread_count`, BP schedules; independent trials. | MIT; `pip install ldpc==2.4.1`; Python≥3.10, NumPy/SciPy/stim/sinter/pymatching/tqdm/pytest; Cython/compiler for source ([manifest](https://github.com/quantumgizmos/ldpc/blob/main/pyproject.toml)). | Bravyi BB288 circuit UB18 ([paper](https://arxiv.org/html/2308.07915v1)); Cornucopia data2844 circuit UB18 ([paper](https://arxiv.org/html/2608.02773v1)); no certified scale. |
| ldpc classical distance functions ([mod2 API](https://software.roffe.eu/ldpc/ldpc/mod2.html)) | Exhaustive classical kernel distance; separate random estimate routine | Classical exact value or estimate/saved words; not native logical-excluded quantum distance. | H only; low stabilizers can invalidate target. | Native controls not verified for these routines. | Same ldpc MIT installation ([repo](https://github.com/quantumgizmos/ldpc)). | Largest dedicated distance solve not verified; include only as classical control or after correct adaptation. |
| Qubitserf BZ (`method='bz'`) ([repo](https://github.com/Quantinuum/Qubitserf), [distance API](https://github.com/Quantinuum/Qubitserf/blob/main/docs/distance.md)) | Brouwer–Zimmermann / information-set enumeration | Exact on exhaustive completion; public int-only interface lacks verified witness/timeout bounds. | NumPy CSS/classical/symplectic/subsystem matrices; H,L by Z-sector reduction (§2); no DEM importer verified. | CPU threads; optional CUDA/Metal BZ. | MIT; Python≥3.9/NumPy, CMake≥3.20/C++17; `pip install .` or `./build.sh` ([README](https://github.com/Quantinuum/Qubitserf)). | README hundreds of qubits/d≤20 without specific largest; gross time-limited BZ interval[8,12] ([benchmarks](https://github.com/Quantinuum/Qubitserf/blob/main/docs/benchmarks.md)); not a completed optimum. |
| Qubitserf CC (`method='cc'`) ([distance API](https://github.com/Quantinuum/Qubitserf/blob/main/docs/distance.md)) | Connected-cluster enumeration | Exact algorithm; witness/deadline API audit still required. | Same matrix interface and derived fixed Z sector. | CPU threads. | Same MIT/C++17/CMake build ([repo](https://github.com/Quantinuum/Qubitserf)). | Toric [[200,2,10]]2.5ms; gross [[144,12,12]]377.6ms, source-reported settings ([benchmarks](https://github.com/Quantinuum/Qubitserf/blob/main/docs/benchmarks.md)); no general DEM scale. |
| Qubitserf MITM (`method='mitm'`) ([distance API](https://github.com/Quantinuum/Qubitserf/blob/main/docs/distance.md)) | Meet-in-middle exact search | Exact algorithm; public witness/partial bounds unverified. | Same matrix interface / fixed Z-sector bridge. | CPU threads documented; method-specific scaling not verified. | Same MIT/C++17/CMake build ([repo](https://github.com/Quantinuum/Qubitserf)). | Largest solved instance/distance not verified for this engine. |
| QDistSAT ([repo](https://github.com/guluchen/QDistSAT), [paper](https://arxiv.org/abs/2606.12445)) | SAT thresholds, MaxSAT, SMT frontends | Completed SAT exclusions/optimum exact; backend-dependent witness/bounds. | Dense space-separated four files `{stem}_Hx/Hz/Gx/Gz.txt`; native arbitrary H,L/DEM library signature not verified. | Backend-dependent; seed/thread controls unverified. | GPL-3.0-or-later; `pip install -e '.[dev]'`; PySAT, optional z3-solver/cvc5; external solvers separately ([README](https://github.com/guluchen/QDistSAT)). | Paper's backend-specific code results in MaxCDCL/CC/Gurobi rows; **no circuit-distance maximum** verified. |
| DistQLDPC ([repo](https://github.com/guluchen/DistQLDPC), [paper](https://arxiv.org/abs/2606.12445)) | Specialized branch-bound MaxSAT / symplectic code distance | `d_lb/d_ub` proof/primal bounds; final optimum exact; witness export unverified. | Same four dense CSS files; minimizes full Pauli code distance. No verified fixed-sector generic DEM route. | Native threads/seed unverified; parent wall deadline documented. | GPL-3.0-or-later, MIT upstream; `make` with g++/zlib -> `bin/distqldpc` ([README](https://github.com/guluchen/DistQLDPC)). | [[544,80,12]]4954.660s(no-card)/5047.318s(MTO); [[250,10,15]]timeout[8,15] ([Tables19/24](https://arxiv.org/html/2606.12445v1#A1.T19)). |
| Magma minimum-weight routines ([classical](https://magma.maths.usyd.edu.au/magma/handbook/text/1977), [quantum](https://magma.maths.usyd.edu.au/magma/handbook/text/2039)) | BZ / Grassl enumeration, quantum logical exclusion | Exact when proved bounds meet; current bounds on time restriction. | Classical/quantum code objects; no native DEM or direct H,L API verified; derived cosets (§2). | POSIX/distributed workers ([parallel docs](https://magma.maths.usyd.edu.au/magma/handbook/text/69)). | Commercial licensed binary; no source build/size verified ([install](https://magma.maths.usyd.edu.au/magma/faq/install)). | Classical[256,56,68]20560s/160threads/five machines; quantum[[40,30,4]]doc example. Not DEM records. Quantum multithread bug fixed≥2.29-9 ([notes](https://magma.maths.usyd.edu.au/magma/releasenotes/2/29/9/)). |
| GAP/GUAVA exact / coset minimum distance ([API](https://gap-packages.github.io/guava/doc/chap4.html)) | Classical enumeration and exact coset minimum | Exact classical/coset value; target requires all nonzero logical cosets (§2), witness audit. | GAP code C and coset rep w; H,L converted to quotient; no native DEM. | Threads not verified. | GPL-2.0-or-later; GAP≥4.11, SONATA≥2.3; included or unpack to `pkg`; optional Leon `./configure ../..`, `make` ([package](https://gap-packages.github.io/guava/)). | Largest solved instance not verified. Code-table bounds do not certify supplied matrix ([bounds docs](https://gap-packages.github.io/guava/doc/chap7.html)). |
| GAP/GUAVA Leon heuristic ([API](https://gap-packages.github.io/guava/doc/chap4.html)) | Randomized information-set upper-bound search | Weight plus word UB; no exact certificate by repeated agreement. | Classical code object; logical filter/coset bridge needed for H,L/DEM. | Native controls unverified. | Same GUAVA/GAP installation; optional Leon binary build above ([install](https://gap-packages.github.io/guava/doc/chap1.html)). | Dedicated quantum/circuit largest bound not verified. |
| codeDistance / QDistEvol | [Repository](https://github.com/m-webster/codeDistancePYPI), [Webster–Jacob–Higgott 2026](https://arxiv.org/abs/2603.22532); evolutionary information-set search | Witness upper bound; no certified confidence interval. Wrapper dictionary is not an optimality certificate. | Binary NumPy H,L; CSS Hx,Hz; Stim circuit through wrapper. | QDistEvol native parallelism is not established; package nThreads support is incomplete. | See package manifest and approval recipe below. | Verified examples in scale note below; largest attained instance not verified. |
| codeDistance / GurobiDist | [Backend inventory](https://github.com/m-webster/codeDistancePYPI#solver-based-methods); MILP | Exact after backend optimality termination; incumbent alone is UB. Wrapper d alone does not establish that termination. | Same package H,L interface. | Backend-specific; wrapper thread enforcement not verified. | Package plus gurobipy and Gurobi licence; package licence discrepancy below. | See scale note. |
| codeDistance / MIPDist (SCIP; other OR-Tools backends) | [Backend inventory](https://github.com/m-webster/codeDistancePYPI#solver-based-methods); MILP | Exact when backend proves optimality; otherwise valid solver bound and incumbent only. | Same package H,L interface. | Backend-specific; wrapper enforcement not verified. | Package plus OR-Tools; default backend SCIP. Other listed backends include CBC, CP_SAT, GUROBI, CPLEX, XPRESS, GLPK, with additional installations where applicable. | See scale note. |
| codeDistance / CLISATDist | [Backend inventory](https://github.com/m-webster/codeDistancePYPI#solver-based-methods); MaxSAT | Optimal solve certifies exact distance. A feasible assignment without completed optimization proves only UB. | H,L via wrapper; external weighted CNF for CLI solver. | External solver-dependent; no general threaded guarantee verified. | CLI default cashwmaxsatcoreplus; Python python-sat. | See scale note; backend-specific maximum not verified. |
| codeDistance / pySATDist | [Backend inventory](https://github.com/m-webster/codeDistancePYPI#solver-based-methods); Python MaxSAT (RC2/FM/LSU) | Optimal solve certifies exact distance. A feasible assignment without completed optimization proves only UB. | H,L via Python wrapper; pySATsolver/pySATbinary select backend. | Backend-dependent; no general threaded guarantee verified. | python-sat plus codeDistance dependencies/licence caveat in §4. | See scale note; backend-specific maximum not verified. |
| codeDistance / BZDistMW | [Backend inventory](https://github.com/m-webster/codeDistancePYPI#brouwer-zimmermanncodeword-enumeration-algorithms); Brouwer–Zimmermann | Algorithmic exhaustive completion can certify exact distance; wrapper progress needs inspection. | Package H,L. | Native scaling/threads not verified. | Python package dependencies below. | Per-backend maxima not verified. |
| codeDistance / connectedClusterMW | [Backend inventory](https://github.com/m-webster/codeDistancePYPI#brouwer-zimmermanncodeword-enumeration-algorithms); connected-cluster enumeration | Algorithmic exhaustive completion can certify exact distance; wrapper progress needs inspection. | Package H,L. | Native scaling/threads not verified. | Python package dependencies below. | Per-backend maxima not verified. |
| codeDistance / MeetMiddleMW | [Backend inventory](https://github.com/m-webster/codeDistancePYPI#brouwer-zimmermanncodeword-enumeration-algorithms); meet-in-middle | Algorithmic completion can certify value, but current wrapper sets only d and leaves zero L: **no usable witness** ([dispatch](https://github.com/m-webster/codeDistancePYPI/blob/main/codedistance/distance.py)). | Package H,L. | Native scaling/threads not verified. | Python package dependencies below. | Per-backend maxima not verified; witness recovery required before benchmark exact record. |
| CASHWMaxSAT-CorePlus / codeDistance CLISAT default ([Stim example](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimcircuitshortest_error_sat_problem), [codeDistance](https://github.com/m-webster/codeDistancePYPI)) | Complete partial MaxSAT; exact internal algorithm details not audited | Completed optimum plus model gives exact distance; limit/assignment alone UB. | Distance WCNF from Stim or explicit H,L encoding; DEM conversion in §2. | Threads/interruption-bound controls unverified. | Published supplied binary; licence, dependencies, archive size and source-build steps unverified; acquisition in §4. | Direct prior CLISAT circuit competitor: midout family completion in shared scale note; backend-specific largest not verified ([paper](https://arxiv.org/html/2603.22532v1)). |
| Tesseract search decoder | [Repository](https://github.com/quantumlib/tesseract-decoder), [2025 paper](https://arxiv.org/abs/2503.10988); A* with beam/pruning heuristics | Normally decoder correction; adapted search gives witnessed UB. Paper also discusses exact decoding when cutoffs are absent, but a released certificate interface for distance was not verified. | Stim circuit, DEM, detection-event file; matrix-to-DEM conversion needed. | CLI threads; batch decoding parallelism, not a verified parallel speedup for one distance search. | Apache-2.0; pip tesseract-decoder or Bazel build. [Bazel dependencies](https://github.com/quantumlib/tesseract-decoder/blob/main/MODULE.bazel) include Stim, HiGHS1.9.0, Boost1.83, zlib1.3.2, pybind11, rules_python, rules_cc; README additionally lists argparse and nlohmann/json. | Decoding sizes must not be represented as distances solved. Separate MaxSAT certifications are in paper note below. |
| Tesseract Simplex decoder / HiGHS | [Python API](https://github.com/quantumlib/tesseract-decoder/blob/main/src/py/README.md), [paper](https://arxiv.org/html/2503.10988v1); integer-program decoding | Exact most-likely correction when full ILP completes; adaptation and solver termination inspection needed for exact distance. Windowed decoding must not be equated with whole-instance optimality. | DEM, syndrome; use augmented detector row for logical constraint. | Config parallelize exists; meaning for distance run not verified. | Same Tesseract distribution; [Bazel manifest](https://github.com/quantumlib/tesseract-decoder/blob/main/MODULE.bazel) pins HiGHS1.9.0. | No dedicated distance benchmark maximum verified. |
| Height-bound DTD | [Ott–Hetényi–Beverland 2025](https://arxiv.org/html/2502.16408v1); decision-tree / admissible syndrome-height lower bounds; BP-guided variant | Height-bound DTD guarantees minimum correction; all augmented logical-row subproblems completed gives exact distance. | Binary H and logical action A (= benchmark L), including circuit detector matrices. | Paper's all-logical enumeration algorithm is staged/sequential; native threading not verified. | Public source, software licence, installation, binary/API name, dependencies unverified. Paper mentions Python and a modified Cython BP implementation. | Dedicated exact-distance largest run not verified; paper gives algorithms, rather than a verified distance-performance maximum. |
| BP-DTD | [Ott–Hetényi–Beverland 2025](https://arxiv.org/html/2502.16408v1); decision-tree / admissible syndrome-height lower bounds; BP-guided variant | Heuristic correction; augmented logical-row search supplies witness upper bounds only. | Binary H and logical action A (= benchmark L), including circuit detector matrices. | Paper's all-logical enumeration algorithm is staged/sequential; native threading not verified. | Public source, software licence, installation, binary/API name, dependencies unverified. Paper mentions Python and a modified Cython BP implementation. | Dedicated exact-distance largest run not verified; paper gives algorithms, rather than a verified distance-performance maximum. |
| Arbitrary-CSS MaxSAT decoder | [Noormandipour–Haug 2024](https://arxiv.org/html/2410.01673v1); weighted partial MaxSAT, Open-WBO selected | Optimizes most-probable error for given syndrome; fitted effective distance and decoding error rates do not certify code/circuit distance. | CSS parity checks and syndrome; phenomenological measurement noise described. General DEM importer unverified. | Published decoding runs serially; suggested future parallel hardware is not an implemented benchmark guarantee. | Authors' repository, licence, install/API not verified. Generic Open-WBO route can implement the formulation. | Decoding examples include [[144,12,12]] and color d=13; exact-distance solved size not reported in checked source. |
| MQT QECC color-code MaxSAT decoder | [Repository](https://github.com/munich-quantum-toolkit/qecc), [Berent et al. paper](https://arxiv.org/abs/2303.14237); LightsOut/MaxSAT via Z3 | Minimum-weight decoder estimates; no native general DEM-distance certification verified. | Triangular color-code models; general H,L/DEM support for this decoder not verified. | Distance-search threading unverified. | MIT; pip mqt.qecc; current PyPI requires Python >=3.10. | Exact-distance maximum unverified; decoder benchmark sizes are a different question. |

### Source-reported scale: shared codeDistance backends

[Webster–Jacob–Higgott §5.5/Table20](https://arxiv.org/html/2603.22532v1) reports these solver completions on **author-filtered basis DEMs**, rather than raw full matrices. Surface d=11 has241 total qubits, raw1320 detectors/24485 mechanisms, filtered720/4741. Both MILP families completed surface distances, sometimes beyond eight hours. Gurobi, CLISAT and CC completed five midout cases (maximum101 total qubits, filtered300/2459) within eight hours. QDistEvol attained code UB34 at756 data qubits. BB720/filtered4500×51840 is dataset coverage, not all-backend success. Per-backend maxima remain unverified without the [detailed XLSX results](https://github.com/m-webster/codeDistancePYPI/tree/main/paper%20results), which were not downloaded.

[Tesseract AppendixD](https://arxiv.org/html/2503.10988v1) uses Stim WCNF plus an unnamed MaxSAT2024 solver for exact BB72 circuit6 and BB90 circuit8 (144/180 total qubits, code-distance-many rounds). Its larger BB numbers remain upper bounds; its main decoder timings are not distance-solve timings.

## 2. Exact input recipes and fair execution

The following are API recipes, **not adapters with deadline enforcement**. The lead must wrap them with `common.adapter_args` and `common.save_result`; no proposed command was installed or built. Tools lacking witness or interruption support need an adapter change or explicit unavailable status, not invented output. Every solver must receive a remaining wall-time budget after model construction, and a parent watchdog must terminate hung native calls while preserving completed bounds. A library's solve-time limit alone does not meet the whole-run time contract.

### Common H,L / DEM conversion

Load the fixed interface without trusting truth:

```python
import sys
sys.path.insert(0, 'bench')
import common
p = common.load('bench/instances/fx_sdbb16_r3', 'sector')
# p.h[j], p.l[j] are bitmasks; all returned supports use these column indices.
```

Where a recipe takes NumPy/SciPy matrices, obtain binary CSR matrices without changing column order:

```python
import numpy as np
from scipy.sparse import csr_matrix
def csr_from_columns(columns, rows):
    rr, cc = [], []
    for j, mask in enumerate(columns):
        for i in common.bits(mask):
            rr.append(i)
            cc.append(j)
    return csr_matrix((np.ones(len(rr), dtype=np.uint8), (rr,cc)),
                      shape=(rows,len(columns)))
H = csr_from_columns(p.h, p.nrows)
L = csr_from_columns(p.l, p.nobs)
```

A compact DEM can encode every column with positive, equal dummy probability. This is our representation construction, using [Stim's documented DEM format](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md), not a probability model fitted from the circuit:

```python
import stim
dem = stim.DetectorErrorModel()
for h, l in zip(p.h, p.l):
    targets = [stim.target_relative_detector_id(i) for i in common.bits(h)]
    targets += [stim.target_logical_observable_id(i) for i in common.bits(l)]
    dem.append('error', 0.01, targets)
for i in range(p.nrows):
    dem.append('detector', [], [stim.target_relative_detector_id(i)])
for i in range(p.nobs):
    dem.append('logical_observable', [], [stim.target_logical_observable_id(i)])
dem.to_file('instance.dem')
```

To start from a circuit use `stim.Circuit.from_file('circuit.stim').detector_error_model(decompose_errors=False).flattened()`. To start from a DEM use `stim.DetectorErrorModel.from_file('instance.dem').flattened()`. For each `error` instruction XOR its detector and observable targets; separators are grouping hints, not new unit-cost columns. Include the complete target set once per mechanism. Apply the same duplicate-signature merge and zero-column removal as the exporter and retain a column map. Never split correlated mechanisms into independently priced components. Declare `decompose_errors=False` explicitly and audit any source DEM already containing decompositions ([Stim format](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md)).

Some Stim methods accept only a circuit. The following synthetic independent measurement circuit realizes exactly the supplied parity map; it preserves the **minimum weight** after Stim merges duplicate signatures, but a column map is still needed for witnesses:

```python
def matrix_circuit(p):
    c = stim.Circuit()
    c.append('R', range(p.ncols))
    c.append('X_ERROR', range(p.ncols), 0.01)
    c.append('M', range(p.ncols))
    for i in range(p.nrows):
        c.append('DETECTOR', [stim.target_rec(j-p.ncols)
                             for j,h in enumerate(p.h) if (h >> i) & 1])
    for i in range(p.nobs):
        c.append('OBSERVABLE_INCLUDE', [stim.target_rec(j-p.ncols)
                                      for j,l in enumerate(p.l) if (l >> i) & 1], i)
    return c
c = matrix_circuit(p)
```

This construction was checked locally on BB72 full and SDBB16 collapsed by comparing all DEM `(H-column,L-column)` signatures. For a standalone DEM first convert its instructions to p-like columns, then call this function. Record conversion cost, especially for large column counts. This is an objective-preserving bridge, not a claim that its dummy hardware is the physical circuit.

### Stim graphlike and hypergraph calls

```python
# Strict full-target proof eligibility: undecomposed degree at most 2.
assert all(bin(h).count('1') <= 2 for h in p.h)
answer = dem.shortest_graphlike_error(ignore_ungraphlike_errors=False)
# On general hypergraphs use True only for a witness upper bound.
answer_upper = dem.shortest_graphlike_error(ignore_ungraphlike_errors=True)

errors = c.search_for_undetectable_logical_errors(
    dont_explore_detection_event_sets_with_size_above=4,
    dont_explore_edges_with_degree_above=max(bin(h).count('1') for h in p.h),
    dont_explore_edges_increasing_symptom_degree=False,
    canonicalize_circuit_errors=True)
```

The hypergraph options are truncation parameters, not maximum fault weight, and there is no trials/seed parameter in this API. Benchmark several declared syndrome caps (e.g. 2,4,6,8) and both increasing-degree choices within the same total budget; report all settings. Map each returned error's detector/observable signature to an original column, XOR repeated columns, and run `common.check_witness`. A missing result from the heuristic proves nothing. The graphlike routine's answer is exact only on the strict original-model case above ([API](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference)); no independently checkable shortest-path certificate exporter was verified. Python3.9-compatible code must use `bin(h).count('1')`, not `int.bit_count`.

### Stim MaxSAT route and explicit-column SAT/MaxSAT

```python
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
text = c.shortest_error_sat_problem(format='WDIMACS')
wcnf = WCNF(from_string=text)
with RC2(wcnf, solver='g3') as solver:
    model = solver.compute()
    optimum = solver.cost if model is not None else None
```

This uniform-cost call was verified to export WCNF with installed Stim1.15; RC2 execution was not possible locally because PySAT is absent. `likeliest_error_sat_problem` optimizes probability/log-odds and must not substitute for this objective. Stim's documented exporter does not promise that WCNF variable IDs equal benchmark column indices; verify its pinned source map or use the following explicit-column formulation before recording a witness. RC2's `compute()` completion certifies optimal cost; an interrupted `cost` is not automatically a retained primal witness or a publicly exposed certified dual bound ([RC2 docs](https://pysathq.github.io/docs/html/api/examples/rc2.html)).

Our direct encoding assigns fault j variable j+1; use hard XOR clauses for H, logical parity variables b_i for L, the clause OR_i b_i, and unit-weight soft clauses `[-(j+1)]`. For a two-input XOR `z=a XOR b`, use `(a,b,-z),(a,-b,z),(-a,b,z),(-a,-b,-z)` and chain longer rows. Empty H rows impose no condition; empty logical rows force their b_i false. This derivation implements the target directly and avoids exponential enumeration of logical signatures. Use the documented calls below after constructing `hard`, a list of CNF clauses, and `top`, the highest auxiliary variable:

```python
def distance_hard_clauses(p):
    hard = []
    top = p.ncols
    def parity(lits):
        nonlocal top
        if not lits:
            top += 1
            hard.append([-top])
            return top
        a = lits[0]
        for b in lits[1:]:
            top += 1
            z = top
            hard.extend([[a,b,-z], [a,-b,z], [-a,b,z], [-a,-b,-z]])
            a = z
        return a
    for i in range(p.nrows):
        row = [j+1 for j,h in enumerate(p.h) if (h >> i) & 1]
        if row:
            hard.append([-parity(row)])
    logical_bits = [parity([j+1 for j,l in enumerate(p.l) if (l >> i) & 1])
                    for i in range(p.nobs)]
    hard.append(logical_bits)  # empty clause correctly excludes no-logical inputs
    return hard, top
hard, top = distance_hard_clauses(p)
```

```python
# Bounded exact feasibility at K:
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
card = CardEnc.atmost(lits=list(range(1,p.ncols+1)), bound=K,
                      top_id=top, encoding=EncType.seqcounter)
with Solver(name='g3', bootstrap_with=hard+card.clauses) as s:
    sat = s.solve()  # False = UNSAT; a limited/interrupt call can return None.
    model = s.get_model() if sat else None
    witness = [j for j in range(p.ncols) if j+1 in set(model)] if model else None
# Or complete uniform MaxSAT:
w = WCNF()
w.extend(hard)
for j in range(p.ncols): w.append([-(j+1)], weight=1)
with RC2(w, solver='g3') as s:
    model = s.compute()
    cost = s.cost if model is not None else None
w.to_file('instance.wcnf')
```

UNSAT at K excludes all weights ≤K; SAT gives its checked support. Never interpret timeout/UNKNOWN as UNSAT. A completed MaxSAT model gives exact cost, and only e-variable assignments become the witness. External solver examples/build-specific options follow below; their `o <cost>` lines alone report objective candidates, while `s OPTIMUM FOUND` establishes solver completion. Retain version, formula digest, model, and proof/status logs ([PySAT solver docs](https://pysathq.github.io/docs/html/api/solvers.html), [cardinality docs](https://pysathq.github.io/docs/html/api/card.html)).

### MILP that applies directly to both tracks

Use binary e_j, integer detector quotients z_r, integer logical quotients t_i and binary b_i. Impose `H e - 2z = 0`, `L e - 2t - b = 0`, `sum(b)>=1`, minimize `sum(e)`. Quotients can be bounded between zero and n. These are our formulation choices; no CSS commutation condition is needed. One alternative solves every logical row with `L_i e=1 mod2` and takes the minimum, but it must complete/prove bounds for **all** rows; completing one row proves only that row's optimum.

Exact SciPy call for sparse H,L (float CSR matrices) is:

```python
import numpy as np
from scipy.sparse import bmat, eye, csr_matrix
from scipy.optimize import milp, Bounds, LinearConstraint
m,n = H.shape
q = L.shape[0]
A = bmat([[H,-2*eye(m),None,None],
          [L,None,-2*eye(q),-eye(q)],
          [None,None,None,csr_matrix(np.ones((1,q)))]], format='csc')
objective = np.r_[np.ones(n), np.zeros(m+2*q)]
result = milp(objective, integrality=np.ones(len(objective)),
    bounds=Bounds(np.zeros(len(objective)),
                  np.r_[np.ones(n),np.full(m+q,n),np.ones(q)]),
    constraints=LinearConstraint(A, np.r_[np.zeros(m+q),1],
                                 np.r_[np.zeros(m+q),q]),
    options={'time_limit':remaining_seconds,'mip_rel_gap':0.0})
```

Check `result.x[:n]` against the integer H,L after rounding; do not accept rounding alone as feasibility. `status=0` is optimal, `status=1` is a limit, and `mip_dual_bound` is the lower-bound field ([SciPy API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)). Conservatively round a finite dual bound up after subtracting the declared numerical tolerance. No bound is produced when the field is absent/nonfinite. The recipe ran locally on a 3-column parity-path example: status0, witness [0,1,2], primal=dual=3. Use explicit solver APIs below for Gurobi/SCIP thread control. A DEM requires only the common extraction above; no noise probability weights enter this MILP.


### Native Gurobi, SCIP and CP-SAT

The following native calls implement the same parity-quotient model. They are derived distance models using the documented optimization APIs, not claims of native quantum-distance commands. H and L are binary CSR matrices; define their row supports once, and charge this work:

```python
Hr = [H.indices[H.indptr[i]:H.indptr[i+1]].tolist() for i in range(H.shape[0])]
Lr = [L.indices[L.indptr[i]:L.indptr[i+1]].tolist() for i in range(L.shape[0])]
n, m, q = H.shape[1], H.shape[0], L.shape[0]
```

Gurobi ([model API](https://docs.gurobi.com/projects/optimizer/en/12.0/reference/python/model.html), [parameters](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html)):

```python
import gurobipy as gp
s = gp.Model('distance')
e = s.addVars(n, vtype=gp.GRB.BINARY, name='e')
z = s.addVars(m, lb=0, ub=n, vtype=gp.GRB.INTEGER, name='z')
t = s.addVars(q, lb=0, ub=n, vtype=gp.GRB.INTEGER, name='t')
b = s.addVars(q, vtype=gp.GRB.BINARY, name='b')
for i, row in enumerate(Hr): s.addConstr(gp.quicksum(e[j] for j in row) == 2*z[i])
for i, row in enumerate(Lr): s.addConstr(gp.quicksum(e[j] for j in row) == 2*t[i]+b[i])
s.addConstr(gp.quicksum(b.values()) >= 1)
s.setObjective(gp.quicksum(e.values()), gp.GRB.MINIMIZE)
s.Params.Threads = threads
s.Params.Seed = seed
s.Params.MIPGap = 0.0
s.Params.MIPGapAbs = 0.0
s.Params.TimeLimit = remaining_seconds  # recompute after model building
s.optimize()
witness = [j for j in range(n) if e[j].X > 0.5] if s.SolCount else None
dual = s.ObjBound
complete = s.Status == gp.GRB.OPTIMAL
```

`ObjBound`/`SolCount` are documented [attributes](https://docs.gurobi.com/projects/optimizer/en/12.0/reference/attributes/model.html); `OPTIMAL`, `TIME_LIMIT` and `INFEASIBLE` are distinct [statuses](https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/statuscodes.html). Recheck witness, round finite dual bounds conservatively, retain logs/tolerances. The wheel's restricted evaluation licence disallows publishing benchmark results; use a licence permitting this benchmark before scheduling Gurobi ([PyPI licence text](https://pypi.org/project/gurobipy/)). No licence was obtained here.

SCIP through OR-Tools ([example](https://developers.google.com/optimization/mip/mip_example), [solver API](https://or-tools.github.io/docs/python/classortools_1_1linear__solver_1_1pywraplp_1_1Solver.html)):

```python
from ortools.linear_solver import pywraplp
s = pywraplp.Solver.CreateSolver('SCIP')
assert s is not None
thread_control_accepted = s.SetNumThreads(threads)
e = [s.BoolVar('e%d' % j) for j in range(n)]
z = [s.IntVar(0,n,'z%d' % i) for i in range(m)]
t = [s.IntVar(0,n,'t%d' % i) for i in range(q)]
b = [s.BoolVar('b%d' % i) for i in range(q)]
for i, row in enumerate(Hr): s.Add(s.Sum([e[j] for j in row]) == 2*z[i])
for i, row in enumerate(Lr): s.Add(s.Sum([e[j] for j in row]) == 2*t[i]+b[i])
s.Add(s.Sum(b) >= 1)
s.Minimize(s.Sum(e))
s.SetTimeLimit(max(1,int(remaining_seconds*1000)))
status = s.Solve()
witness = ([j for j in range(n) if e[j].solution_value() > .5]
           if status in (s.OPTIMAL,s.FEASIBLE) else None)
dual = s.Objective().BestBound()
```

`BestBound` is a minimization lower bound ([objective API](https://or-tools.github.io/docs/python/classortools_1_1linear__solver_1_1pywraplp_1_1Objective.html)). Retain status and thread-control acceptance; backend seed/gap option strings were not verified here. Each DEM uses the same extracted H,L; the original probabilities are discarded for this unit-cost model.

CP-SAT alternative, using [documented Python solver controls](https://developers.google.com/optimization/cp/cp_solver):

```python
from ortools.sat.python import cp_model
a = cp_model.CpModel()
e = [a.new_bool_var('e%d' % j) for j in range(n)]
z = [a.new_int_var(0,n,'z%d' % i) for i in range(m)]
t = [a.new_int_var(0,n,'t%d' % i) for i in range(q)]
b = [a.new_bool_var('b%d' % i) for i in range(q)]
for i, row in enumerate(Hr): a.add(sum(e[j] for j in row) == 2*z[i])
for i, row in enumerate(Lr): a.add(sum(e[j] for j in row) == 2*t[i]+b[i])
a.add(sum(b) >= 1)
a.minimize(sum(e))
s = cp_model.CpSolver()
s.parameters.num_search_workers = threads
s.parameters.random_seed = seed
s.parameters.max_time_in_seconds = remaining_seconds
status = s.solve(a)
witness = ([j for j in range(n) if s.value(e[j])]
           if status in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None)
dual = s.best_objective_bound
```

The integer formulation avoids float feasibility arithmetic, but every returned support still needs `check_witness`. `num_search_workers` is a supported legacy alias; current `num_workers` is preferred ([parameter definitions](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto)). This recipe was not executed; CP-SAT is an optional same-installation challenger, not the published SCIP/Gurobi result.

### dist-m4ri CLI and bounds



Current CLI proposals (replace K/N/SEED/TIME/THREADS with preregistered values):

```sh
./src/dist_m4ri method=1 finH=H.mtx finL=L.mtx steps=N seed=SEED wmin=0 timeout=TIME threads=THREADS outC=rw.nz smax=0 debug=0
./src/dist_m4ri method=2 finH=H.mtx finL=L.mtx wmax=K timeout=TIME threads=THREADS outC=cc.nz smax=0 debug=0
./src/dist_m4ri method=3 finH=H.mtx finL=L.mtx steps=N seed=SEED timeout=TIME threads=THREADS outC=bracket.nz smax=0 debug=0
# Replace finH/finL by fdem=model.dem for native DEM input:
./src/dist_m4ri method=3 fdem=model.dem pmin=0 steps=N seed=SEED timeout=TIME threads=THREADS outC=dem.nz smax=0 debug=0
```

These flags are also implemented by [the low-level wrapper](https://github.com/QEC-pages/dist-m4ri/blob/master/dist_m4ri.py): `run_dist_m4ri(method=3,finH="H.mtx",finL="L.mtx",steps=N,seed=SEED,wmin=0,timeout=TIME,threads=THREADS,outC="cws.nz",smax=0) -> (dmin,dmax,rw_steps)`; replace `finH/finL` with `fdem="model.dem"` for DEM. The wrapper describes equality as exact, `dmax=0` as no upper bound, and a completed CC scan as proved exclusion through weight `dmin-1`. Its high-level result can cast to an int even when only a bound; do not infer optimum from that int. High-level caching can reuse previous bounds/witnesses; disable it or use binary/low-level invocation for independent runs. [Source](https://github.com/QEC-pages/dist-m4ri/blob/master/dist_m4ri.py).

NZLIST indices are 1-based. Automatic throttling can use fewer workers than `threads`; `nothrottle=1` disables it. [README](https://github.com/QEC-pages/dist-m4ri). Our benchmark choices: do not supply `dmin` from metadata, restrict `start/cbeg/cend` without proved symmetry, or set `pmin>0`; do not set `dexp` from ground truth. Recheck exported witnesses.

The CC `outC` path can retain all minimum codewords rather than a single support ([README](https://github.com/QEC-pages/dist-m4ri)). Record this output overhead; a documented single-witness mode was not verified. Do not silently disable witness output to improve reported time.

**Version trap:** the [generated legacy manual](https://qec-pages.github.io/dist-m4ri/) describes single-threaded `d`/`-w`, lacks current bound output, and has obsolete build text `sh make -j all`. Use `make all` from the current repository and record its commit. Readme says .mtx/.mmx; benchmark's exact `coordinate pattern general` parser compatibility needs a smoke test after approval. No such test was run.

### QDistRnd


```gap
LoadPackage("QDistRnd");
Hx := ReadMTXE("Hx.mtx", 0)[3];;
Hz := ReadMTXE("Hz.mtx", 0)[3];;
dZub := AbsInt(DistRandCSS(Hx, Hz, 100000, 0, 11 : field:=GF(2)));
# Both CSS sectors, if both are wanted:
dXub := AbsInt(DistRandCSS(Hz, Hx, 100000, 0, 11 : field:=GF(2)));
# For a general stabilizer G with interleaved (a1,b1,a2,b2,...):
dub := AbsInt(DistRandStab(G, 100000, 0, 11 : field:=GF(2)));
```

`num` is information-set count; `mindist=0` avoids early stopping at a chosen threshold; otherwise success below it returns a negative integer. `debug` bitmap 1 prints a vector, 2 verifies orthogonality, 8 estimates success; `maxav` is the empirical stopping threshold. No seed or wall-time argument is documented; external process deadline and verified GAP RNG seeding are needed. [API](https://qec-pages.github.io/QDistRnd/doc/chap4.html).

**Derived H/L route, not native functionality:** form a row basis G of `ker([H;L])` over GF(2), then call `DistRandCSS(H,G,num,0,debug)`. Its Z-type nontrivial codewords are exactly `ker(H) \ ker([H;L])`, the target. Charge the dense nullspace conversion to runtime; converting DEM to its undecomposed H/L is required first. Pattern-only .mtx support not documented: write integer-valued MTXE if necessary. Printed-vector format must be audited before an adapter claims a witness.

### BP+OSD sampling and the ldpc classical distance functions


Documented decoder call, followed by **our derived distance sampling loop**:

```python
from ldpc import BpOsdDecoder
decoder = BpOsdDecoder(
    H, error_rate=p_error, max_iter=max_iter, bp_method="minimum_sum",
    ms_scaling_factor=0.625, schedule="parallel",
    omp_thread_count=threads, osd_method="OSD_CS", osd_order=order)
rng = np.random.default_rng(seed)
for trial in range(trials):
    e = (rng.random(H.shape[1]) < p_error).astype(np.uint8)
    c = decoder.decode(np.asarray(H @ e).reshape(-1) % 2)
    r = e ^ c
    if not np.any(np.asarray(H @ r).reshape(-1) % 2) and np.any(np.asarray(L @ r).reshape(-1) % 2):
        witness = np.flatnonzero(r).tolist()  # candidate UB; keep minimum
```

The [API](https://software.roffe.eu/ldpc/ldpc/bposd_decoder.html) documents the decoder arguments and `decode(syndrome)`. Seed/trial loop is adapter logic, and must obey total wall deadline including preparation. Report p, BP max iterations/scaling/schedule, OSD method/order, trial counts and seed; those choices materially change search. For a DEM, use the same H/L columns as the benchmark; uniform p is a search parameter, not the physical DEM probabilities.

The logical-row configuration directly searches the nontrivial-error problem, following [Bravyi et al. §6](https://arxiv.org/html/2308.07915v1): append one logical parity to H and decode syndrome `(0,...,0,1)`. Exhaustively visiting individual rows covers every nonzero logical action; visiting randomized row combinations supplies upper witnesses and does not prove coverage or decoder optimality. A concrete per-row call is:

```python
from scipy.sparse import vstack
for i in range(L.shape[0]):
    H_aug = vstack([H,L.getrow(i)], format='csr')
    target = np.zeros(H_aug.shape[0], dtype=np.uint8)
    target[-1] = 1
    searcher = BpOsdDecoder(H_aug, error_rate=p_error, max_iter=max_iter,
        bp_method='minimum_sum', ms_scaling_factor=0.625,
        schedule='parallel', omp_thread_count=threads,
        osd_method='OSD_CS', osd_order=order)
    candidate = np.asarray(searcher.decode(target), dtype=np.uint8)
    # Check H candidate=0 and L candidate!=0; save its original-column support.
```

Here `p_error` is the declared search prior. Multiple trials may perturb priors with a declared RNG seed; repeated deterministic calls with identical settings are not independent trials. This is a derived sampler, not an undocumented ldpc distance API.

`ldpc.mod2.compute_exact_code_distance(H)` is a documented exact classical PCM minimum-distance routine; `estimate_code_distance(H,timeout_seconds=...,number_of_words_to_save=...)` returns estimate, searched samples, saved words. Both use only H, and may return stabilizers that fail L. They are not direct quantum/DEM distance algorithms. [mod2 API](https://software.roffe.eu/ldpc/ldpc/mod2.html). The older classical [tutorial](https://software.roffe.eu/ldpc/classical_coding.html) describes estimate sampling random kernel-row combinations. Do not conflate this with BP+OSD sampling.

### Qubitserf: current Python/C++ library


```python
from qubitserf import distfind as df
dz = df.css_distance(Hx, Hz, which="z", method="cc", backend="cpu", threads=threads, verbose=True)
dz_bz = df.css_distance(Hx, Hz, which="z", method="bz", backend="cpu", threads=threads, verbose=True)
# method="mitm" is another independent exact engine.
```

Shared options and signatures are in [distance docs](https://github.com/Quantinuum/Qubitserf/blob/main/docs/distance.md). **Derived general H/L adapter:** G=`ker([H;L])` row basis, then `df.css_distance(H,G,which="z",...)` has exactly the target Z-distance. This is not the default `which="min"`: the complementary X-distance is irrelevant. Charge conversion to runtime. DEM needs H/L extraction first. No documented wall timeout or returned witness/partial bounds: a wrapper needs further API/source audit before satisfying `save_result`. `threads=0` means all cores and should not be used in bounded runs.

### QDistSAT and DistQLDPC (2026)


```sh
# QDistSAT's documented experiment frontend (existing BB stem):
python3 benchmarks/benchmark_solver_performance.py --stem BB_108_8_10 -d 10 --solvers rc2-glucose42 maxcdcl distqldpc
# DistQLDPC native CSS frontend:
./bin/distqldpc -cpu-lim=300 path/to/MY_CODE
./bin/distqldpc -cpu-lim=300 -no-card path/to/MY_CODE
./bin/distqldpc -cpu-lim=300 -card-mto path/to/MY_CODE
```

DistQLDPC `-cpu-lim` is documented as **wall-clock** parent deadline with child SIGKILL; timeout retains `d_lb/d_ub`. `-card-sinz`, `-card-mto`, `-card-both-force`, `-no-card` vary encodings. Final `c d : N` denotes optimum; compare proved bounds, not `o N` alone. [README](https://github.com/guluchen/DistQLDPC).

[Paper Table19](https://arxiv.org/html/2606.12445v1#A1.T19): LP[[544,80,12]] exact by MaxCDCL2775.920s, DistQLDPC4954.660s/no-card or5047.318s/MTO; [Table24](https://arxiv.org/html/2606.12445v1#A1.T24): TN[[250,10,15]] MaxCDCL6525.009s, DistQLDPC timeout[8,15]. These are code results. A native DistQLDPC CSS construction from arbitrary H/L can accidentally include a smaller complementary X sector; do **not** use it as a DEM solver without verified sector-specific or generic WCNF adaptation. The necessary circuit competitor is the branch-and-bound MaxSAT architecture with the correct target encoding.

### Magma and GAP/GUAVA


Magma documented calls:

```magma
SetNthreads(threads);
SetVerbose("Code", 1);
SetSeed(seed);
d := MinimumWeight(C : Method:="Zimmermann", MaximumTime:=limit, Nthreads:=threads);
lo, hi := MinimumWeightBounds(C);
w := MinimumWord(C);
// Actual CSS/stabilizer quantum-code object:
dq := MinimumWeight(Q : MaximumTime:=limit);
```

`MaximumTime` is **user CPU time**, not whole-run wall time; external wall deadline needed. `MinimumWord` witness behavior is documented for classical codes, not as generic H/L logical-witness export. [Classical docs](https://magma.maths.usyd.edu.au/magma/handbook/text/1977), [quantum docs](https://magma.maths.usyd.edu.au/magma/handbook/text/2039).

Magma's [parallel examples](https://magma.maths.usyd.edu.au/magma/handbook/text/69) include classical binary[273,102,24] and[256,56,68], the latter20560s on160 threads/five machines; these are not QLDPC/DEM solves. Quantum docs give [[40,30,4]] example. **Version requirement:** [Magma2.29-9 release notes](https://magma.maths.usyd.edu.au/magma/releasenotes/2/29/9/) fix a multi-thread quantum MinimumWeight bug that returned too-small values. Use >=2.29-9 for quantum runs or document single-thread/older-version restriction.

GAP exact/heuristic calls:

```gap
LoadPackage("guava");
C := GeneratorMatCode(G, GF(2));;
d := MinimumDistance(C);
dw := MinimumDistance(C, w);
ub_with_word := DecreaseMinimumDistanceUpperBound(C, t, trials);
```

For arbitrary H/L, calling classical `MinimumDistance(ker(H))` is insufficient because low-weight stabilizers can dominate. **Derived exact coset route:** T=`ker([H;L])`, D=`ker(H)`; enumerate the `2^k-1` nonzero cosets D/T, where `k=dim(D)-dim(T)=rank([H;L])-rank(H)` over GF(2), not necessarily the observable-row count. Call `MinimumDistance(Tcode,rep)` for each and take the minimum. This is exact only after all cosets complete and needs witness extraction audit. Magma could use its documented `WeightDistribution(Tcode,rep)` for the same cosets or enumerate `Words(Dcode,w)` and filter L; no native direct H/L API verified. These conversions and coset enumeration are charged to runtime; DEM first becomes H/L. GUAVA's `[n,k]` best-known-code tables are not certificates for the supplied instance: [bounds docs](https://gap-packages.github.io/guava/doc/chap7.html).

### codeDistance H,L and circuit APIs

Package export/import is verified by [__init__.py](https://github.com/m-webster/codeDistancePYPI/blob/main/codedistance/__init__.py), and signatures/circuit behavior by [distance.py](https://github.com/m-webster/codeDistancePYPI/blob/main/codedistance/distance.py). Proposed call for the benchmark's existing binary arrays:

```python
from codedistance import codeDistance
result = codeDistance(
    H, L, tB=1, method="QDistEvol",
    params={"isDEM": 1, "iterCount": 10000, "nThreads": 1,
            "maxTime": 600, "LOCheck": 1}, seed=12345)
```

Change method to GurobiDist, MIPDist, CLISATDist, pySATDist, BZDistMW, connectedClusterMW, or MeetMiddleMW as appropriate. For a supplied circuit:

```python
from codedistance import circuitDistance
result = circuitDistance(
    circuit, method="QDistEvol",
    params={"filterCircuit": False, "iterCount": 10000,
            "nThreads": 1, "maxTime": 600, "LOCheck": 1}, seed=12345)
```

The package's circuit wrapper flattens a newly generated DEM, sets isDEM, and defaults to basis filtering. Set filtering off to benchmark an existing full variant. A direct public DEM-file distance function is not verified: convert flattened DEM columns to the benchmark H,L and call the matrix function. Recheck returned binary result['L'] in original coordinates; package preprocessing/remapping and backend completion must be audited before trusting exact or lower-bound status. The exported dictionary's d, L, T, R, progress fields do not include a uniform proof-status field. [Output contract](https://github.com/m-webster/codeDistancePYPI#output-format)

Documented options worth recording: [parameters](https://github.com/m-webster/codeDistancePYPI#parameters-for-distance-finding-methods) iterCount, seed, maxTime (documented specifically for CLI methods), nThreads (incomplete support), CCstart=-1 (no unsupported anchor restriction), MIP_solver, pySATsolver, pySATbinary (rc2/fm/lsu), and QDistEvol genCount/offspring/pMut/pMutScale/sMut/swapPivot/tabuLength/HL. No uniform wall deadline for all in-process methods is verified. Do not assume maxTime satisfies the benchmark contract; use a supervised process.

The current [MeetMiddleMW dispatch](https://github.com/m-webster/codeDistancePYPI/blob/main/codedistance/distance.py) assigns only `result['d']` and leaves `result['L']` at its initialized zero vector. Its scalar result cannot supply the required upper-bound witness; expose/recover a support before treating this implementation as a usable exact baseline.

For the direct prior CLISAT backend, after individual approval and preparation of the explicit-column WCNF:

```sh
./CASHWMaxSAT-CorePlus/bin/cashwmaxsatcoreplus -bm -m instance.wcnf
```

This is [Stim's documented invocation](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimcircuitshortest_error_sat_problem). The `-bm -m` flags are retained from that example; their internal semantics, timeout controls and bound retention were not independently audited. Supervise wall time, require a completed optimum status and assignment, and recover only fault variables1..n from the explicit encoder. Stim-generated IDs need their separate map audit. CLI codeDistance can instead use `method='CLISATDist'` when this executable is on PATH; its `maxTime` does not include every benchmark preparation step.

The separately sourced Open-WBO invocation for the same formula is:

```sh
./open-wbo -print-model instance.wcnf
```

The [README](https://github.com/sat-group/open-wbo) documents model printing, `-algorithm` selection (WBO/LinearSU/MSU3/PartMSU3/OLL/default best), cardinality encodings and the `s/o/v` output contract; [Main.cc](https://github.com/sat-group/open-wbo/blob/master/Main.cc) verifies filename/stdin input and CPU/memory limiting. Use a wall watchdog; `s SATISFIABLE` proves only an incumbent, while `s OPTIMUM FOUND` plus its checked assignment closes the bound. Formula/parser compatibility and timeout witness retention still need smoke testing; no solver was run.

### Decoder-to-distance reduction and API

The following mathematical reduction is explicitly documented in [DTD Appendix A.4](https://arxiv.org/html/2502.16408v1): for each L row i, solve minimum-weight syndrome decoding for H_i=stack(H,L[i]) with syndrome zero except the last bit one; minimize the resulting weights over all i. Each witness is valid for the original problem. Exactness requires optimality/completed infeasibility for every subproblem. App. A.5 also proposes height-pruned enumeration of all minimum logical operators, given d. DTD executable/API is unverified, so do not invent one. This reduction also explains how other minimum-error decoders can be used as searchers.

For Tesseract, construct one artificial, **undecomposed** error instruction per H_i column at the same probability below 0.5. Equal probabilities make cost proportional to Hamming weight. Add detector declarations to retain zero rows. No native Tesseract generic matrix constructor was verified. Its published DEM decode calls are:

The following is our derived representation builder using [Stim DEM APIs](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference), before invoking that published decoder API:

```python
def decoding_dem(H_aug):
    D = stim.DetectorErrorModel()
    columns = H_aug.tocsc()
    for j in range(columns.shape[1]):
        rows = columns.indices[columns.indptr[j]:columns.indptr[j+1]]
        D.append('error', 0.01,
                 [stim.target_relative_detector_id(int(i)) for i in rows])
    for i in range(columns.shape[0]):
        D.append('detector', [], [stim.target_relative_detector_id(i)])
    return D
# For each logical row i; every row is needed for an exact all-row reduction.
H_aug = vstack([H,L.getrow(i)], format='csr')
augmented_dem = decoding_dem(H_aug)
target_syndrome = np.zeros(H_aug.shape[0], dtype=np.uint8)
target_syndrome[-1] = 1
```

```python
from tesseract_decoder import tesseract
config = tesseract.TesseractConfig(
    dem=augmented_dem, det_beam=50, pqlimit=200000,
    no_revisit_dets=False, merge_errors=False, det_penalty=0.0,
    sparsify_errors=False, seed=12345)
decoder = config.compile_decoder()
decoder.decode_to_errors(target_syndrome)
witness = list(decoder.predicted_errors_buffer)
```

This is a **heuristic search call**, not an exact configuration. Finite beam/priority-queue limits prune candidates. The [header](https://github.com/quantumlib/tesseract-decoder/blob/main/src/tesseract.h) defines INF_DET_BEAM as uint16's maximum (65535), and the Python example exposes decoder.low_confidence_flag, but a complete exact-mode recipe and sufficient optimality-status interpretation were not verified. Defaults also merge errors and enable no-revisit pruning. See [configuration documentation](https://github.com/quantumlib/tesseract-decoder/blob/main/src/py/README.md); archive the configuration and original-column mapping.

CLI decoding example, after preparing augmented DEM and one-shot syndrome file:

```sh
./bazel-bin/src/tesseract --dem augmented.dem --in syndrome.01 --in-format 01 --threads 1 --out decoded.01 --out-format 01 --print-stats
```

This CLI returns observable predictions/statistics, not the needed original fault-set witness; use the Python error buffer for a distance adapter. CLI flags that alter results include beam, beam-climbing, pqlimit, det-order-seed, num-det-orders, no-revisit-dets, det-penalty, and sparsification. [CLI README](https://github.com/quantumlib/tesseract-decoder#usage)

The separate ILP interface is documented as:

```python
from tesseract_decoder import simplex
config = simplex.SimplexConfig(dem=augmented_dem, parallelize=False,
                              window_length=0, window_slide_length=0,
                              merge_errors=False)
decoder = simplex.SimplexDecoder(config)
decoder.init_ilp()
decoder.decode_to_errors(target_syndrome)
witness = list(decoder.predicted_errors_buffer)
```

The Simplex error buffer is documented. Explicit HiGHS gap/time-limit/status controls for this class remain unverified; the above is not a ready certified adapter. [Simplex API](https://github.com/quantumlib/tesseract-decoder/blob/main/src/py/README.md#tesseract_decodersimplex-module)


### Generic MaxCDCL WCNF execution

**Recommend a generic MaxCDCL route separately from specialized DistQLDPC.** The [CP2026 authors' repository](https://github.com/zjl9959/enMaxCDCL_CP26) supplies six generic MaxSAT variants, source and static Linux binaries. Use enMaxCDCL as the initial named variant; lambda/alwaysFLA variants require separate configurations, not unnamed automatic selection. The [binary page](https://github.com/zjl9959/enMaxCDCL_CP26/blob/main/bins/enMaxCDCL) states 12.7 MB. Repository/archive total size is unstated. Its README requires Linux GCC>=15.2.0, static libstdc++ and zlib; [source directories](https://github.com/zjl9959/enMaxCDCL_CP26/tree/main/codes) verify the variant names. Proposed source build and invocation, not executed:

```sh
cd enMaxCDCL_CP26/codes/enMaxCDCL/simp
make rs
./maxcdcl_static -cpu-lim=600 -mem-lim=1900 problem.wcnf
```

Alternatively the published binary is `./bins/enMaxCDCL problem.wcnf`. macOS source build uses `make`, producing maxcdcl. The README also identifies the original [MaxCDCL2024 archive](https://maxsat-evaluations.github.io/2024/mse24-solver-src/exact/unweighted/MaxCDCL2024.zip) and `bin/maxcdcl_static problem.wcnf`; archive size and its build recipe were not verified. [QDistSAT](https://github.com/guluchen/QDistSAT) offers one-at-a-time acquisition through `python3 scripts/download_maxsat_solvers.py --only maxcdcl` after approving that script. This command downloads a binary; it was not run.

[Main.cc](https://github.com/zjl9959/enMaxCDCL_CP26/blob/main/codes/enMaxCDCL/simp/Main.cc) verifies CPU seconds, memory MB, interruption handling, optimum/UNSAT output, and inherited MIT licence text. No root-level licence was found; licence coverage of new modifications is not independently verified. No thread flag was verified. WCNF parser/PrintFlags/Makefile views failed with cache misses, so supported WCNF dialect and whether final-model printing is enabled must be checked after approval. Do not treat the leftover DRUP option as a checked MaxSAT optimality proof. The optimum status is algorithmic completion, not an independently checked certificate. Interrupted runs must not report exact, and any incumbent requires its assignment and original H,L witness check. CPU limits do not meet the benchmark wall-time contract: supervise the whole process. H,L requires the benchmark's generic WCNF encoding; Stim circuits use shortest_error_sat_problem(WDIMACS), while existing DEMs must preserve their column identities through matrix encoding.

The distinct [Vandesande–Coll–Bogaerts 2025/AAAI2026 paper](https://arxiv.org/html/2511.10273v1) adds independently checkable VeriPB logging to WMaxCDCL. The checked arXiv version says implementation/data will be made available later. Current source/build/API availability was not verified in allowed sources; do not imply that either MaxCDCL2024 or enMaxCDCL supports those proofs.


## 3. How papers obtain circuit distance

Local sources: [catalog.json](../../code_instances/catalog.json), [PROGRAMS.md](../../code_instances/PROGRAMS.md), and the paper summaries linked in every detailed row.

Coverage: all 296 records in `../code_instances/catalog.json` (catalog cutoff 2026-10-03) were inspected for their circuit-distance field and matched against the local `papers/*.md` summaries and `PROGRAMS.md`. The table below includes every positive, analytical, conditional, effective-distance, or noise-specific statement, plus nearby statements whose absence/metric distinction materially prevents an exact circuit-distance claim. Plain “not reported” records are counted and listed separately. This is a catalog audit, not a new reproduction of each result.

**Provenance:** `P` means the method/result paragraph was rechecked directly in the arXiv HTML version linked here (v1 for these checks); `C` means only the read-only local catalog/reviewed paper summary was inspected, and algorithm/certification details remain unverified. Numerical code distance is never substituted for circuit distance. Local catalog links are relative to this file.

| Paper and source | Sizes/model | Circuit-distance statement | How obtained; proof caveat | Provenance |
|---|---|---|---|---|
| [2601.04467: Holographic codes seen through ZX-calculus](https://arxiv.org/abs/2601.04467v3) ([catalog](../../code_instances/papers/2601.04467.md)) | New dual-tessellation ZX holographic family; bond-extended gauge-fixed example [[52,1,d unknown]]. | Fault-protected spacetime edges discussed; numeric circuit distance not reported. | No computing/certification algorithm recorded in catalog; not independently verified. | C |
| [2601.05113: Unitary fault-tolerant encoding of Pauli states in surface codes](https://arxiv.org/abs/2601.05113v1) ([catalog](../../code_instances/papers/2601.05113.md)) | Rotated [[d²,1,d]], unrotated [[d²+(d−1)²,1,d]]. | Relevant-error fault distance=d: X errors for \|0>, Z errors for \|+>. Complementary error distance is bounded. | Directional fault-propagation construction/proof (catalog); solver not recorded. | C |
| [2601.09911: Time-Dynamic Circuits for Fault-Tolerant Shift Automorphisms in Quantum LDPC Codes](https://arxiv.org/html/2601.09911v1) ([catalog](../../code_instances/papers/2601.09911.md)) | Established BB examples [[72,12,6]], [[120,8,12]], [[144,12,12]], [[170,16,10]]. | Table 1 BP-OSD estimates: [[72,12,6]] d_circ≤6; [[120,8,12]] ≤10; [[144,12,12]] ≤10; [[170,16,10]] ≤10. Shift circuits preserve the corresponding memory fault structure; bounds are not exact certificates. | BP-OSD randomized upper-bound estimator; Table 1 and §II.1 primary checked. | P (v1) |
| [2601.10042: Towards Minimal Fault-tolerant Error-Correction Sequence with Quantum Hamming Codes](https://arxiv.org/abs/2601.10042v1) ([catalog](../../code_instances/papers/2601.10042.md)) | Established quantum Hamming [[2^r−1,2^r−1−2r,3]], r=3a+1, a≥1; example [[15,7,3]]. | Weak fault-tolerant distance-3 QEC guarantee; no general circuit-distance value certified beyond that model. | Weak-FT analytic guarantee (catalog); no exact DEM search recorded. | C |
| [2601.13313: Synthesis of Fault-tolerant State Preparation Circuits using Steane-type Error Detection](https://arxiv.org/abs/2601.13313v1) ([catalog](../../code_instances/papers/2601.13313.md)) | Established CSS codes including [[19,1,5]], [[17,1,5]], and distance-seven examples. | Strict/appropriate fault-tolerance conditions tested up to t=floor((d−1)/2); no universal scalar circuit distance table extracted. | Fault-set-guided synthesis and tests through t (catalog); no scalar DEM certificate recorded. | C |
| [2601.17580: PropHunt: Automated Optimization of Quantum Syndrome Measurement Circuits](https://arxiv.org/html/2601.17580v1) ([catalog](../../code_instances/papers/2601.17580.md)) | [[9,1,3]], [[25,1,5]], [[49,1,7]], [[81,1,9]], [[39,3,3]], [[54,11,4]], [[108,18,4]], [[60,2,6]] (Table 1). | Per-circuit effective d_eff defined/evaluated; no new code distance. | Connected ambiguous-subgraph search + MaxSAT (§5.1–5.2); exact within selected subgraph, global certification not established by source inspected. | P (v1) |
| [2601.18879: Multivariate Multicycle Codes for Complete Single-Shot Decoding](https://arxiv.org/abs/2601.18879v2) ([catalog](../../code_instances/papers/2601.18879.md)) | MM examples [[96,12,8]] and [[486,24,12]] have Table 1 connected-cluster cross-checks. Other abstract examples [[144,12,d≤12]], [[216,12,d≤14]], [[288,12,d≤16]], [[324,12,d≤20]], [[432,12,d≤27]], [[630,70,d≤9]], [[648,18,d≤23]] are appendix numerical distance estimates; many additional tables. | Not separately reported as a certified table; code distance must not be copied into circuit distance. | No computing/certification algorithm recorded in catalog; not independently verified. | C |
| [2601.20818: Quantum Memory and Autonomous Computation in Two Dimensions](https://arxiv.org/abs/2601.20818v3) ([catalog](../../code_instances/papers/2601.20818.md)) | Concatenated base-code family within 2D self-simulating cellular automaton; no practical finite [[n,k,d]] instance table. | Nonzero-threshold fault-tolerance theorem, not finite numeric circuit distance. | Threshold proof (catalog), not a finite distance solver. | C |
| [2601.20927: Entangling logical qubits without physical operations](https://arxiv.org/abs/2601.20927v1) ([catalog](../../code_instances/papers/2601.20927.md)) | Phantom qRM family [[2^m,m−l+1,min(2^(m−l),2^l)]]; examples [[16,3,4]], [[64,4,8]], [[49,3,4]], [[15,4,2]]. | No universally certified scalar QEC circuit distance; temporary projection magic-gate schemes are effectively distance two. | No computing/certification algorithm recorded in catalog; not independently verified. | C |
| [2602.09099: Surface code off-the-hook: diagonal syndrome-extraction scheduling](https://arxiv.org/abs/2602.09099v1) ([catalog](../../code_instances/papers/2602.09099.md)) | Established surface-code/lattice-surgery layouts. | Full circuit-level distance with Tesseract decoder in studied setting; matching effective distance may be reduced at surgery interface. | Tesseract-decoded logical-error simulation (catalog); intrinsic distance proof/search method not recorded. | C |
| [2602.09103: Constant-space-overhead fault-tolerant quantum input/output and communication](https://arxiv.org/abs/2602.09103v1) ([catalog](../../code_instances/papers/2602.09103.md)) | Established concatenated Hamming [[N^(L),K^(L),3^L]], including [[105,7,9]], [[3255,147,27]]; N^(L)=∏_(l=1)^L (2^(l+2)−1), K^(L)=∏_(l=1)^L (2^(l+2)−1−2(l+2)). | Threshold/level-conversion theorem, not a finite scalar circuit-distance certificate; physical interfaces incur O(p) input/output error. | Threshold/interface theorem (catalog), not a finite distance solver. | C |
| [2602.16948: Fault-tolerant interfaces for quantum LDPC codes](https://arxiv.org/abs/2602.16948v2) ([catalog](../../code_instances/papers/2602.16948.md)) | Existing asymptotically good quantum Tanner/qLDPC families; no new finite instance. | Threshold and local-stochastic-noise guarantee; no finite numeric circuit distance. | Analytical local-stochastic-noise theorem (catalog). | C |
| [2602.17438: Fault-tolerant preparation of arbitrary logical states in the cat code](https://arxiv.org/abs/2602.17438v1) ([catalog](../../code_instances/papers/2602.17438.md)) | Established four-legged cat code, one logical qubit per bosonic mode. | Infidelity approximately quadratic in physical error; no discrete circuit-distance certificate. | Infidelity scaling (catalog), not discrete DEM distance. | C |
| [2602.20900: Error correction with brickwork Clifford circuits](https://arxiv.org/abs/2602.20900v1) ([catalog](../../code_instances/papers/2602.20900.md)) | At any constant rate k/n, random 1D Clifford brickwork depth O(d) yields [[n,k,d+1]] with high probability for d∈o(n)∩Ω(log n); approximate good codes in logarithmic depth. | No noisy-encoding circuit fault distance claimed. | No computing/certification algorithm recorded in catalog; not independently verified. | C |
| [2602.22211: Computing with many encoded logical qubits beyond break-even](https://arxiv.org/abs/2602.22211v1) ([catalog](../../code_instances/papers/2602.22211.md)) | Established iceberg [[k+2,k,2]] and concatenated [[(k2+2)(k1+2),k2k1,4]]. Examples [[80,48,4]], [[16,4,4]]. | Specific complete GHZ preparation/readout circuit has fault distance 4; not inferred for every experimental gadget. | Specific GHZ fault-distance claim (catalog); computing algorithm not recorded. | C |
| [2602.22906: Hyperbolic and Semi-Hyperbolic Floquet Codes for Photonic Quantum Computing](https://arxiv.org/abs/2602.22906v2) ([catalog](../../code_instances/papers/2602.22906.md)) | {8,3},{10,3},{12,3} hyperbolic/semi-hyperbolic Floquet families; see complete code parameter tables. | No exact numeric circuit-distance table extracted. | No computing/certification algorithm recorded in catalog; not independently verified. | C |
| [2603.00228: Stairway Codes: Floquetifying Bivariate Bicycle Codes and Beyond](https://arxiv.org/html/2603.00228v1) ([catalog](../../code_instances/papers/2603.00228.md)) | Stairway embedded examples [[192,16,4]], [[192,8,6]], [[288,14,9≤d≤10]], [[384,16,d≤12]], [[576,26,d≤12]], [[576,14,d≤20]]. | EM3: d_circ=4 for (192,16); 6 for (192,8); ≤7 for (288,14); ≤8 for (384,16) and (576,26); ≤14 for (576,14). | Gurobi ILP on DEM (§VI.3.3): ≥10,000 seconds/distance type, 32 threads, AMD EPYC 9R14 (§VI.4). Exact only when solver finds optimum. | P (v1) |
| [2603.01628: No More Hooks in the Surface Code: Distance-Preserving Syndrome Extraction for Arbitrary Layouts at Minimum Depth](https://arxiv.org/abs/2603.01628v2) ([catalog](../../code_instances/papers/2603.01628.md)) | Established arbitrary regular-tile surface layouts, including memory/surgery. | Claim/proof preserves full fault distance d for stated surface layouts. | ZX schedule/fault-propagation proof (catalog); qualifying layout theorem, no generic DEM solver. | C |
| [2603.04156: Achieving Optimal-Distance Atom-Loss Correction via Pauli Envelope](https://arxiv.org/abs/2603.04156v2) ([catalog](../../code_instances/papers/2603.04156.md)) | Established rotated surface [[d²,1,d]]. | Optimal loss distance d_loss≈d for Envelope-MLE; matching d_loss≈2d/3. These are loss/noise/decoder-specific distances, not a universal Pauli circuit d. | Envelope-MLE/loss-distance theorem (catalog); decoder/noise-specific. | C |
| [2603.05398: QGPU: Parallel logic in quantum LDPC codes](https://arxiv.org/abs/2603.05398v1) ([catalog](../../code_instances/papers/2603.05398.md)) | Clustered-cyclic family [[2pn_an_b,2n_an_b,d≤p]], constant check weight 2(w_a+w_b); [[136,8,d≤14]], [[198,18,d≤10]] numerically estimated, [[24,8,3]] small instance exact. | No separately certified numeric memory-circuit fault distance. Surgery preserves code distance for HGP by proof and tested k=8 CC instances numerically; these statements are not a scalar circuit-distance certificate. | Surgery preservation theorem for HGP plus numerical CC tests (catalog); no scalar circuit search recorded. | C |
| [2603.05481: High-performance syndrome extraction circuits for quantum codes](https://arxiv.org/html/2603.05481v1) ([catalog](../../code_instances/papers/2603.05481.md)) | Established CSS codes; principal example gross [[144,12,12]]. | Gross non-interleaved SECs cannot reach d_circ=12; explicit schedule conjectured d_circ=11 after extensive testing. Uniform non-interleaved tilings cannot reach 11. | Residual-pattern analytic exclusion + adaptive-prior BP-OSD upper bounds (§D.2/H.2); no <11 witness in 10,000 outer loops supports conjecture, not lower-bound proof. | P (v1) |
| [2603.05496: Mirror codes: High-threshold quantum LDPC codes beyond the CSS regime](https://arxiv.org/abs/2603.05496v1) ([catalog](../../code_instances/papers/2603.05496.md)) | Non-CSS mirror examples [[60,4,10]], [[36,6,6]], [[48,8,6]], [[85,8,9]] with weight 6. | Provably fully FT circuits preserve d_circ=d under stated model; minimal-ancilla memory benchmarks do not certify this equality for every selected code. | Analytical FT construction under assumptions (catalog); not transferred to every minimal-ancilla benchmark. | C |
| [2603.17988: Adaptive Loss-tolerant Syndrome Measurements](https://arxiv.org/abs/2603.17988v1) ([catalog](../../code_instances/papers/2603.17988.md)) | Input arbitrary stabilizer [[n,k,d]]; no new block family. Prime/composite qudit dimensions handled separately. | Fault-tolerance conditions formulated for t=floor((d−1)/2) input-code correction; no universal separate numeric circuit distance. | t-fault correctness conditions (catalog), not independent minimum. | C |
| [2603.19522: Preserving MWPM-Decodability in Fault-Equivalent Rewrites](https://arxiv.org/abs/2603.19522v1) ([catalog](../../code_instances/papers/2603.19522.md)) | Input matchable stabilizer-code ZX diagram; no new finite [[n,k,d]] block. | Distance-preservation results conditional on input diagram distance and spider degree; no new numeric circuit-distance example extracted. | Fault-equivalence/ZX proof conditional on diagram degree and input distance (catalog). | C |
| [2603.21499: Optimal Compilation of Syndrome Extraction Circuits for General Quantum LDPC Codes](https://arxiv.org/abs/2603.21499v1) ([catalog](../../code_instances/papers/2603.21499.md)) | Established qLDPC benchmark instances in Table III. | No general numeric circuit-distance guarantee; optimal depth does not imply optimal fault distance. | No computing/certification algorithm recorded in catalog; not independently verified. | C |
| [2603.28852: Color code off-the-hook: avoiding hook errors with a single auxiliary per plaquette](https://arxiv.org/html/2603.28852v1) ([catalog](../../code_instances/papers/2603.28852.md)) | Triangular color patches, d≤13 numerical check; finite n not stated in inspected distance paragraph. | Bulk preserves d; finite boundaries d_circ=d−floor((d+3)/6), numerically verified up to d=13; asymptotically 5d/6. | Boundary-hook argument + numerical check through d=13 (§II); exact search implementation not stated in inspected text; Tesseract is the simulation decoder (§III). | P (v1) |
| [2604.09797: Optimising Quantum Error Correction Using Morphing Circuits](https://arxiv.org/html/2604.09797v1) ([catalog](../../code_instances/papers/2604.09797.md)) | [[42,6,6]]; [[30,8,5]]; [[73,1,9]] | Table 6: triangular weight-6 original end-distance 3,5,7,9 gives dcirc=2,4,5,6; Extra Layer gives 3,4,6,7; Extra Qubits gives 3,5,7,9. Diamond weight-7 gives dcirc=3,5,7. Numerically checked. | One-round reduction (Prop.1/§2.5), Gurobi minimum-weight solver (Appendix E); structure-specific exact method. | P (v1) |
| [2604.17339: Fault-Tolerant Cut-Cat State Syndrome Extraction for Quantum Codes](https://arxiv.org/abs/2604.17339v1) ([catalog](../../code_instances/papers/2604.17339.md)) | [[49,1,5]] | not_reported; fault-tolerance proof and O(p^3) example do not independently supply a numerical dcirc. | Fault-tolerance proof/scaling (catalog); no scalar minimum recorded. | C |
| [2604.19481: Fault-Tolerant Quantum Computing with Trapped Ions: The Walking Cat Architecture](https://arxiv.org/html/2604.19481v1) ([catalog](../../code_instances/papers/2604.19481.md)) | [[102,22,9]]; [[70,6,9]]; [[54,2,10]] | Reported dcirc=9 for all three Q102/Q70/Q54 syndrome circuits (Tables 9–10). Static Q54 d=10 does not imply dcirc=10. | Table 10 reports dcirc; algorithm/proof status of circuit distances not found in inspected source. Appendix C exact enumeration/QDistRnd description refers to static code distances. | P (v1) |
| [2605.11318: Spatial overhead reduction for 2D hypergraph product codes](https://arxiv.org/abs/2605.11318v2) ([catalog](../../code_instances/papers/2605.11318.md)) | [[160,9,6]]; [[441,64,6]]; [[931,49,11]]; [[475,25,9]]; [[684,36,10]]; [[2025,256,8]] | Theorem 4.2 gives distance-preserving syndrome extraction under its assumptions; effective distances match code distances for the qualifying schedules. | Theorem 4.2 distance-preserving schedule under hypotheses (catalog). | C |
| [2605.15348: Clifford-deformed zero-rate LDPC codes with 50% biased noise thresholds](https://arxiv.org/html/2605.15348v1) ([catalog](../../code_instances/papers/2605.15348.md)) | CSS/linear open tile circuits through d=9; finite n not extracted from inspected section. | Exactly verified dcirc=d for CSS and linear-deformed tile circuits through d=9; other deformations have circuit simulations, not the same certificate. | codeDistance QDistEvol followed by Gurobi MILP exact cross-check, CSS and linear-deformed open tile circuits through d=9 (§V.1). | P (v1) |
| [2605.19471: Efficient Fault-Tolerant Ancilla Preparation for Quantum BCH codes via Cyclic Symmetry](https://arxiv.org/abs/2605.19471v1) ([catalog](../../code_instances/papers/2605.19471.md)) | [[31,11,5]]; [[63,27,7]]; [[127,71,9]] | not_reported; strict fault-tolerance conditions are stated separately. | Strict FT preparation conditions (catalog); no independent scalar minimum. | C |
| [2605.30455: A Denser Planar Surface Code](https://arxiv.org/abs/2605.30455v1) ([catalog](../../code_instances/papers/2605.30455.md)) | [[49,3,5]] | Compact single-logical patch schedule achieves dcirc=d (paper cites the alternating-schedule result); dense/yoked architecture has additional hook/outer-decoder qualifications. | Alternating schedule theorem cited (catalog); compact patch only. | C |
| [2606.06365: A framework for low-overhead quantum fault tolerance via spacetime lifting](https://arxiv.org/abs/2606.06365v2) ([catalog](../../code_instances/papers/2606.06365.md)) | Fault-complex cost N with fault distance Omega(N/log N); teleportation logical dimension Theta(log N). | Proved asymptotic fault-distance lower bound Omega(N/log N), subject to expansion and boundary assumptions. | Analytical expansion/boundary theorem (catalog); asymptotic spacetime lower bound. | C |
| [2606.09678: The dynamic 4.8.8 Floquet code](https://arxiv.org/html/2606.09678v1) ([catalog](../../code_instances/papers/2606.09678.md)) | n=4L^2 data qubits, k=2 on L×L square-octagon torus. | Authors claim exact spatial dcirc=L for all four variants from Stim searches; completeness settings/maximum L unverified. Reset dynamic timelike slope2<=dt/nqec<=3; other variants3/2 refer to a separate boundary-path metric. | Stim graphlike/full undetectable-error searches (Appendix E). Timelike graph/clique brackets (Appendix F) are not verified bounds for our H e=0,L e!=0 objective. | P (v1) |
| [2606.17268: Breaking the bicycle frame: Coset-based quantum LDPC codes](https://arxiv.org/html/2606.17268v1) ([catalog](../../code_instances/papers/2606.17268.md)) | (n,k,dcirc upper bound): (48,8,5), (96,8,9), (224,12,14), (84,16,7), (112,16,8), (128,16,10), (168,16,13). | Upper bounds in Table 5: respective dcirc<=5,9,14,7,8,10,13 for the seven listed instances; randomized BP-OSD witnesses, not exact minima. | Randomized BP-OSD optimization, ≥50,000 trials per code (§VI); Table 5 upper bounds. stimbposd 10,000 BP iterations/order 10 are simulation settings, not separately verified estimator settings. | P (v1) |
| [2606.20263: Vine Codes: Low-Overhead Quantum LDPC Codes on a Planar Square Grid](https://arxiv.org/html/2606.20263v1) ([catalog](../../code_instances/papers/2606.20263.md)) | (n_data,k,dcirc,n_total): (180,6,6,393), (221,6,7,511), (191,6,6,456), (231,6,7,535), (266,9,6,617), (256,9,6,625), (234,9,6,582), (278,9,6,683), (173,4,7,384), (182,4,7,434), (207,7,6,500), (144,5,6,364), (151,5,6,372), (143,5,6,373), (130,4,6,320), (121,4,6,298), (206,6,6,479), (105,3,6,248). | Table 1 has 18 exact patches (catalog selected only four), dcirc=6 or 7; no d=10 verification in Table 2. | dist-m4ri connected-cluster exact search (Appendix B, Table 1); Table 2 d=10 extrapolated. | P (v1) |
| [2606.22853: Bunny Codes: Broadening Superconducting Quantum Error Correction Capability through Advanced Control Engineering](https://arxiv.org/html/2606.22853v1) ([catalog](../../code_instances/papers/2606.22853.md)) | [[40,4,5]]; [[36,8,4]]; [[30,2,5]]; [[28,4,4]] | For [[30,2,5]], circuits 1–3 have dcirc=3 and circuits 4–7 have dcirc=5 (Figure 9). Circuit distances computed only up to static d=5 in the main search. | PySAT circuit-distance calculation (§2.6); SAT encoding/solver options/proof-file details not given in inspected text. | P (v1) |
| [2606.25011: Fast and Parallel High-Rate STAR Architecture for Megaquop Quantum Simulation](https://arxiv.org/html/2606.25011v1) ([catalog](../../code_instances/papers/2606.25011.md)) | Catalog matching instance [[42,6,6]]; paper claim refers to the d=6 schedule test and grammar, not all chain lengths. | Static d=6 instance has dfault=5 for 20 optimal schedules and dfault=4 for 192 other valid schedules (Appendix B.2). Do not extrapolate this numeric certificate to d=8/10 codes or all chain lengths. | Enumerate schedule grammar, symbolic GF(2) correctness filter, rank by fault distance (Appendix B.2); distance-search algorithm referred to earlier methodology, not specified here. | P (v1) |
| [2606.25330: Routing Codes: High-Rate Quantum LDPC Codes with Short, Parallel Non-Local Connectivity](https://arxiv.org/html/2606.25330v1) ([catalog](../../code_instances/papers/2606.25330.md)) | [[54,8,6]]; [[70,8,7]]; [[90,8,9]]; [[100,8,10]]; [[110,8,11]]; [[140,8,12]]; [[140,8,13]]; [[200,24,14]]; [[200,16,17]] | Table 1 circuit upper bounds <=6,7,9,9,10,11,12 for first seven instances; weight-11 examples Table 4 have <=14 and <=17. Randomized BP-OSD bounds, not proofs of equality. | BP-OSD randomized rows on linearized circuit-fault H/L matrices (§VII.3); witness upper bounds only. | P (v1) |
| [2606.25870: Evolving Quantum Error-Correcting Encodings for Molecular Simulation](https://arxiv.org/abs/2606.25870v1) ([catalog](../../code_instances/papers/2606.25870.md)) | Five physical qubits per mode at tested 12,14,16,20 modes; dense fallback for failing 18-mode case; one 20-mode construction reaches d=6. | Explicitly unmeasured: author states circuit-level effective distance is future work. | No computing/certification algorithm recorded in catalog; not independently verified. | C |
| [2607.05107: Complementary 3D color codes for transversal quantum logic](https://arxiv.org/abs/2607.05107v1) ([catalog](../../code_instances/papers/2607.05107.md)) | [[15,1,3]] | All single-fault configurations enumerated; none cause logical failure in either block. No independent numeric minimum circuit-fault distance extracted. | Exhaustive single-fault enumeration (catalog); bounded-fault verification, no complete minimum. | C |
| [2609.20183: Fast Unitary Preparation of Surface-Code Logical States on Neutral-Atom Hardware](https://arxiv.org/abs/2609.20183v1) ([catalog](../../code_instances/papers/2609.20183.md)) | No finite size recorded in catalog; not independently extracted. | Unitary preparation fault distance equals d in the protected error direction; opposite direction has a different preparation guarantee. | Protected-direction unitary preparation theorem (catalog); opposite direction differs. | C |
| [2607.27521: Floquet Abelian Multicycle Codes](https://arxiv.org/abs/2607.27521v1) ([catalog](../../code_instances/papers/2607.27521.md)) | Table 3 uses embedded distance d_emb=min_t min(d_X(t),d_Z(t)); k=6 for these Floquet AMC4 instances. Local round period is six rotated-time layers. Integer-cut d_X/d_Z values and embedded values are separate columns; the n=900 example gives d_emb≤14. | Table 3 reports embedded distances (minimum Pauli logical weight over inequivalent circuit cuts), not minimum circuit-fault weights. The three simulated instances have d_emb=5,8,10 at n=108,144,324; the n=900 row gives d_emb≤14. No independent circuit-fault distance value recorded. | Embedded static distance minimized over cuts (catalog); not circuit-fault optimization. | C |
| [2607.27644: Quantum LDPC codes with design rate 1/5 and good performance below 1000 physical qubits](https://arxiv.org/html/2607.27644v1) ([catalog](../../code_instances/papers/2607.27644.md)) | [[160,32,10]], [[240,48,12]], [[320,64,14]], [[390,78,≤16]], [[550,110,≤18]]; data+ancilla 288,432,576,702,990. | n=160,240,320: dcirc≤8,10,12; n=390,550: Table 15 leaves distance blank. The fitted d−2 for larger codes is an assumption. | QDistEvol 10^6 iterations per shallow one-round DEM (Appendix F/Table 15); upper bounds, large-code estimates inconclusive. | P (v1) |
| [2607.28605: Logical computation with canonical lifted product codes](https://arxiv.org/abs/2607.28605v1) ([catalog](../../code_instances/papers/2607.28605.md)) | [[1122,148,20]]; [[4350,1224,20]]; [[100,26,4]] | Merged surgery has phenomenological fault distance at least dressed merged-code distance; magic protocol at least min(d,d_s). | Phenomenological surgery theorem (catalog); excludes gate-propagation noise. | C |
| [2607.29443: Erasure surface code circuit without mid-circuit erasure checks](https://arxiv.org/abs/2607.29443v4) ([catalog](../../code_instances/papers/2607.29443.md)) | No finite size recorded in catalog; not independently extracted. | Leakage fault distance and erasure correctability depend separately on extraction circuit, erasure-check schedule and leaked-gate effect. Do not replace with Pauli d. | Leakage/erasure-model-specific analysis (catalog); solver not recorded. | C |
| [2608.02773: Quantum error correction at ultra-low overhead](https://arxiv.org/html/2608.02773v1) ([catalog](../../code_instances/papers/2608.02773.md)) | n=36s data qubits and 18s syndrome ancillas, with each block a 3×s array; the seven Table 1 instances have k=n/2+4. The grid-column variable s (called q in the paper) is not the physical alphabet dimension, which is 2. General k=18s+epsilon_X+epsilon_Z depends on check ranks. | Table 1 gives BP-OSD upper bounds on minimum independent physical-fault weight: d_circ≤5,8,10,11,14,16,18 for n=252,576,900,1044,1764,2304,2844 respectively. These are upper bounds, distinct from exactly certified Pauli code distances. | BP-OSD upper-bound search (Methods/§1.7). Cascaded RelayBP+OSD settings describe simulations, not exact certification. | P (v1) |
| [2608.06187: Error-detected surgery on Iceberg codes](https://arxiv.org/abs/2608.06187v1) ([catalog](../../code_instances/papers/2608.06187.md)) | Iceberg [[2N,2N−2,2]]; paper contributes surgery gadgets on the existing family. | Circuit-level simulations verify fault detection/postselected scaling of the gadgets; base code distance is2. | Postselected fault-detection simulations (catalog); no independent intrinsic minimum. | C |
| [2609.03703: Fractalizing spacetime: Floquet codes with fractonic excitations that are immobile in space and time](https://arxiv.org/abs/2609.03703v1) ([catalog](../../code_instances/papers/2609.03703.md)) | No finite size recorded in catalog; not independently extracted. | Spacetime type-II fracton Floquet examples have superlinear fault-distance growth with time; no finite numeric distance extracted. | Fractal spacetime growth analysis (catalog); no finite instance minimum recorded. | C |
| [2609.10666: Walking Floquet code circuits for zero-overhead leakage reduction](https://arxiv.org/abs/2609.10666v1) ([catalog](../../code_instances/papers/2609.10666.md)) | No finite size recorded in catalog; not independently extracted. | Walking honeycomb schedules preserve Pauli fault distance; leakage protection is noise-model dependent. | Walking schedule preserves Pauli distance (catalog); checking algorithm not recorded. | C |
| [2609.16159: Towards Block-Level Fault-Tolerant Quantum Simulation on Small High-Rate Non-CSS Codes](https://arxiv.org/abs/2609.16159v1) ([catalog](../../code_instances/papers/2609.16159.md)) | [[8,3,3]] | A shared parity-ancilla fault can become an undetectable logical in one Trotter sector; memory-code d=3 does not certify block-gate circuit d=3. | Propagated single-ancilla-fault audit (catalog); sector-specific failure example. | C |
| [2609.21376: Denser Planar Color Codes](https://arxiv.org/abs/2609.21376v3) ([catalog](../../code_instances/papers/2609.21376.md)) | Total physical qubits including ancillas q=(2d²+5d−5)/2; q is not n_data. Twelve CNOT layers per periodic extraction cycle. | Twelve-layer periodic superdense schedules appear to preserve full distance; paper wording is empirical, not a general proof. | Empirical periodic schedule claim (catalog); solver/proof not recorded. | C |
| [2609.26973: Near-optimal high-rate surgery from linear PCPPs](https://arxiv.org/abs/2609.26973v1) ([catalog](../../code_instances/papers/2609.26973.md)) | For a μ-coordinate subcode with t logicals: surgery ancillas μ^(1+o(1)),phenomenological fault distance≥d with d rounds. This is not a circuit-level fault-distance claim. | Fault distance≥d for d repeated surgery rounds under phenomenological noise. | Phenomenological repeated-surgery lower-bound proof (catalog). | C |
| [2609.29890: Syndrome measurements enable deterministic fault-tolerant $T$ gates](https://arxiv.org/abs/2609.29890v1) ([catalog](../../code_instances/papers/2609.29890.md)) | No finite size recorded in catalog; not independently extracted. | Fixed22-qubit and direct Golay logical-T gadgets tolerate one circuit fault; this is not automatically an exact minimum circuit-distance value. | One-fault-tolerance gadget proof (catalog); not exact minimum. | C |
| [2609.37231: Ultra-high-distance quantum memories from amplified qLDPC codes](https://arxiv.org/html/2609.37231v1) ([catalog](../../code_instances/papers/2609.37231.md)) | Seed [[18,4,4]], then [[9738,4,76]] or [[13320,64,64]]; numeric circuit bounds stated separately. | [[9738,4,76]]: 57≤dcirc≤76; [[13320,64,64]]: 48≤dcirc≤64. Ideal input, noiseless idles, perfect final checks; full noisy/flag record retained. | Complete local response catalog + quotient Dijkstra/BFS (Appendix B.2), then amplifier-certificate theorem. Returns full-circuit lower bound; equality only with attained seed certificate. | P (v1) |
| [2609.39522: Layer codes as quantum memories: syndrome extraction, thresholds and idle robustness](https://arxiv.org/html/2609.39522v1) ([catalog](../../code_instances/papers/2609.39522.md)) | 18 layer-code instances/four input codes; certificate subset built from [[4,2,2]]. Maximum certified size not extracted. | No hook-induced distance loss in [[4,2,2]]-input layer codes where circuit-distance verification is feasible; no all-family proof inferred. | Small-instance integer-programming certification; BP+OSD minimum residual-distance proxy for larger cases (§II.2); no all-family exact claim. | P (v1) |
| [2610.01923: Loss-tolerant distributed lattice surgery using fusion networks](https://arxiv.org/abs/2610.01923v1) ([catalog](../../code_instances/papers/2610.01923.md)) | No finite size recorded in catalog; not independently extracted. | Hybrid interface merge erasure distance2d+1; perpendicular observable distance d. Bell geometry d+1 and floor((d+1)/2). These are directional interface-erasure distances. | Analytical directional interface-erasure distances (catalog), not Pauli DEM minimum. | C |


### Catalog exclusions and completeness

The detailed table has 58 individual records; the table below groups the other 238 records by their exact circuit-distance metadata statement. Its 34 rows plus the 58 distinct positive/caveat rows cover the catalog’s 92 unique statements and all 296 paper records. These are absence or metric-caution records, not circuit-distance ground truth. No algorithm or scalar minimum is recorded for them.

| Exact catalog statement | Paper IDs (primary abstract links; statements not independently verified) | Sizes/method |
|---|---|---|
| Not reported. | [2601.01137](https://arxiv.org/abs/2601.01137), [2601.06736](https://arxiv.org/abs/2601.06736), [2601.08014](https://arxiv.org/abs/2601.08014), [2601.08568](https://arxiv.org/abs/2601.08568), [2601.08636](https://arxiv.org/abs/2601.08636), [2601.08824](https://arxiv.org/abs/2601.08824), [2601.09850](https://arxiv.org/abs/2601.09850), [2601.15446](https://arxiv.org/abs/2601.15446), [2601.15505](https://arxiv.org/abs/2601.15505), [2601.18562](https://arxiv.org/abs/2601.18562), [2601.19848](https://arxiv.org/abs/2601.19848), [2601.22363](https://arxiv.org/abs/2601.22363), [2601.22567](https://arxiv.org/abs/2601.22567), [2602.04443](https://arxiv.org/abs/2602.04443), [2602.12309](https://arxiv.org/abs/2602.12309), [2602.12228](https://arxiv.org/abs/2602.12228), [2602.13638](https://arxiv.org/abs/2602.13638), [2602.19057](https://arxiv.org/abs/2602.19057), [2602.19558](https://arxiv.org/abs/2602.19558), [2602.20158](https://arxiv.org/abs/2602.20158), [2602.20661](https://arxiv.org/abs/2602.20661), [2603.03182](https://arxiv.org/abs/2603.03182), [2603.03542](https://arxiv.org/abs/2603.03542), [2603.04548](https://arxiv.org/abs/2603.04548), [2603.04883](https://arxiv.org/abs/2603.04883), [2603.08213](https://arxiv.org/abs/2603.08213), [2603.08711](https://arxiv.org/abs/2603.08711), [2603.10981](https://arxiv.org/abs/2603.10981), [2603.13538](https://arxiv.org/abs/2603.13538), [2603.15190](https://arxiv.org/abs/2603.15190), [2603.16036](https://arxiv.org/abs/2603.16036), [2603.20294](https://arxiv.org/abs/2603.20294), [2603.18560](https://arxiv.org/abs/2603.18560), [2603.19597](https://arxiv.org/abs/2603.19597), [2603.22336](https://arxiv.org/abs/2603.22336), [2603.24588](https://arxiv.org/abs/2603.24588), [2603.25831](https://arxiv.org/abs/2603.25831), [2603.28459](https://arxiv.org/abs/2603.28459), [2603.29896](https://arxiv.org/abs/2603.29896) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported for a complete new code. | [2601.03623](https://arxiv.org/abs/2601.03623) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No separately certified circuit fault distance. Circuit-level thresholds depend on hardware, detector resolution and GHZ cut-off timing. | [2601.07241](https://arxiv.org/abs/2601.07241) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; numerical infidelity and gate error are distinct from preparation fault distance. | [2601.08782](https://arxiv.org/abs/2601.08782) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No separately certified numeric circuit distance found. | [2601.10786](https://arxiv.org/abs/2601.10786) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No universal numeric circuit distance reported; LER optimization is decoder/model-dependent. | [2601.12509](https://arxiv.org/abs/2601.12509) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No certified numeric circuit distance extracted; hook-error suppression modeled. | [2601.13648](https://arxiv.org/abs/2601.13648) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; syndrome/error-correction gadgets beyond this toolkit are explicitly future work. | [2601.15019](https://arxiv.org/abs/2601.15019) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; approximation/noise-specific correctability. | [2601.17592](https://arxiv.org/abs/2601.17592) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; leakage-detection probability is not distance. | [2601.21616](https://arxiv.org/abs/2601.21616) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No separately certified erasure or Pauli circuit distance found. | [2602.07578](https://arxiv.org/abs/2602.07578) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; generated-state squeezing/fidelity does not certify FT preparation distance. | [2602.08209](https://arxiv.org/abs/2602.08209) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported numerically. | [2602.12685](https://arxiv.org/abs/2602.12685), [2603.05502](https://arxiv.org/abs/2603.05502) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported as numeric circuit distance; Table 1 3.9ms cycle time for Q4 is a timing metric. | [2602.14273](https://arxiv.org/abs/2602.14273) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; active repeated correction not experimentally demonstrated and full finite-squeezing/ancilla-error analysis left for future work. | [2602.14461](https://arxiv.org/abs/2602.14461) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported as exact numeric circuit distance. | [2602.15372](https://arxiv.org/abs/2602.15372) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No independently extracted certified circuit-distance list. | [2602.17969](https://arxiv.org/abs/2602.17969) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; loss capacity L is not a full circuit fault distance. | [2603.03263](https://arxiv.org/abs/2603.03263) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported for noisy encoding; channel-capacity setting assumes ideal encode/decode. | [2603.04543](https://arxiv.org/abs/2603.04543) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; break-even lifetimes and postselection gain are performance metrics. | [2603.04564](https://arxiv.org/abs/2603.04564) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported as scalar Pauli circuit distance. | [2603.15760](https://arxiv.org/abs/2603.15760) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No separately certified circuit-distance values extracted; numerical logical-error curves are not distance certificates. | [2603.17703](https://arxiv.org/abs/2603.17703) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; reduced depth/gate count does not certify fault tolerance. | [2603.17743](https://arxiv.org/abs/2603.17743) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported separately. Simulation squeezing threshold 11.5dB is a noise-performance metric, not circuit distance. | [2603.18778](https://arxiv.org/abs/2603.18778) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; approximate dissipative/noise-specific protocol. | [2603.21598](https://arxiv.org/abs/2603.21598) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported; published thresholds use independent X/Z code-capacity noise. | [2603.26311](https://arxiv.org/abs/2603.26311) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| Not reported for a specified realistic circuit noise model. | [2603.29811](https://arxiv.org/abs/2603.29811) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| not_reported | [2604.01478](https://arxiv.org/abs/2604.01478), [2604.01874](https://arxiv.org/abs/2604.01874), [2604.03569](https://arxiv.org/abs/2604.03569), [2604.05871](https://arxiv.org/abs/2604.05871), [2604.05874](https://arxiv.org/abs/2604.05874), [2604.06087](https://arxiv.org/abs/2604.06087), [2604.06149](https://arxiv.org/abs/2604.06149), [2604.06565](https://arxiv.org/abs/2604.06565), [2604.08247](https://arxiv.org/abs/2604.08247), [2604.08672](https://arxiv.org/abs/2604.08672), [2604.09002](https://arxiv.org/abs/2604.09002), [2604.11145](https://arxiv.org/abs/2604.11145), [2604.12684](https://arxiv.org/abs/2604.12684), [2604.13219](https://arxiv.org/abs/2604.13219), [2604.13529](https://arxiv.org/abs/2604.13529), [2604.14296](https://arxiv.org/abs/2604.14296), [2604.14299](https://arxiv.org/abs/2604.14299), [2604.14931](https://arxiv.org/abs/2604.14931), [2604.16209](https://arxiv.org/abs/2604.16209), [2604.18714](https://arxiv.org/abs/2604.18714), [2604.19163](https://arxiv.org/abs/2604.19163), [2604.19687](https://arxiv.org/abs/2604.19687), [2604.20838](https://arxiv.org/abs/2604.20838), [2604.21800](https://arxiv.org/abs/2604.21800), [2604.21824](https://arxiv.org/abs/2604.21824), [2604.22471](https://arxiv.org/abs/2604.22471), [2604.24739](https://arxiv.org/abs/2604.24739), [2604.25026](https://arxiv.org/abs/2604.25026), [2604.27565](https://arxiv.org/abs/2604.27565), [2604.27817](https://arxiv.org/abs/2604.27817), [2605.01942](https://arxiv.org/abs/2605.01942), [2605.02571](https://arxiv.org/abs/2605.02571), [2605.03631](https://arxiv.org/abs/2605.03631), [2605.04151](https://arxiv.org/abs/2605.04151), [2605.10943](https://arxiv.org/abs/2605.10943), [2605.11092](https://arxiv.org/abs/2605.11092), [2605.12796](https://arxiv.org/abs/2605.12796), [2605.18961](https://arxiv.org/abs/2605.18961), [2605.19298](https://arxiv.org/abs/2605.19298), [2605.21898](https://arxiv.org/abs/2605.21898), [2605.22439](https://arxiv.org/abs/2605.22439), [2605.23119](https://arxiv.org/abs/2605.23119), [2605.23894](https://arxiv.org/abs/2605.23894), [2605.24262](https://arxiv.org/abs/2605.24262), [2605.24519](https://arxiv.org/abs/2605.24519), [2606.02418](https://arxiv.org/abs/2606.02418), [2606.02531](https://arxiv.org/abs/2606.02531), [2606.08592](https://arxiv.org/abs/2606.08592), [2606.08771](https://arxiv.org/abs/2606.08771), [2606.09379](https://arxiv.org/abs/2606.09379), [2606.11010](https://arxiv.org/abs/2606.11010), [2606.11468](https://arxiv.org/abs/2606.11468), [2606.12030](https://arxiv.org/abs/2606.12030), [2606.12394](https://arxiv.org/abs/2606.12394), [2606.13521](https://arxiv.org/abs/2606.13521), [2606.14253](https://arxiv.org/abs/2606.14253), [2606.14901](https://arxiv.org/abs/2606.14901), [2606.17709](https://arxiv.org/abs/2606.17709), [2606.19873](https://arxiv.org/abs/2606.19873), [2606.20548](https://arxiv.org/abs/2606.20548), [2606.22594](https://arxiv.org/abs/2606.22594), [2606.24469](https://arxiv.org/abs/2606.24469), [2606.24808](https://arxiv.org/abs/2606.24808), [2606.25048](https://arxiv.org/abs/2606.25048), [2606.26226](https://arxiv.org/abs/2606.26226), [2606.27130](https://arxiv.org/abs/2606.27130), [2606.27211](https://arxiv.org/abs/2606.27211) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| not_reported; encoder optimization is not a fault-distance certificate. | [2605.15266](https://arxiv.org/abs/2605.15266) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| not_reported; SM-code distance concerns classical syndrome redundancy. | [2605.25317](https://arxiv.org/abs/2605.25317) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| not_reported as a separately certified numerical fault distance. | [2606.06062](https://arxiv.org/abs/2606.06062) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| not_reported; the author explicitly does not optimize layer ordering, which can change circuit distance. | [2606.12724](https://arxiv.org/abs/2606.12724) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| not_reported as a separate certified numerical dcirc in the inspected main tables. | [2606.19482](https://arxiv.org/abs/2606.19482) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |
| No independent circuit-fault distance value recorded from the inspected evidence. Code distance or logical-error-rate scaling is not substituted. | [2607.00786](https://arxiv.org/abs/2607.00786), [2607.01887](https://arxiv.org/abs/2607.01887), [2607.02170](https://arxiv.org/abs/2607.02170), [2607.02346](https://arxiv.org/abs/2607.02346), [2607.04462](https://arxiv.org/abs/2607.04462), [2607.05897](https://arxiv.org/abs/2607.05897), [2607.06404](https://arxiv.org/abs/2607.06404), [2607.07607](https://arxiv.org/abs/2607.07607), [2607.12118](https://arxiv.org/abs/2607.12118), [2607.12242](https://arxiv.org/abs/2607.12242), [2607.13105](https://arxiv.org/abs/2607.13105), [2607.12948](https://arxiv.org/abs/2607.12948), [2607.13784](https://arxiv.org/abs/2607.13784), [2607.14091](https://arxiv.org/abs/2607.14091), [2607.14861](https://arxiv.org/abs/2607.14861), [2607.14988](https://arxiv.org/abs/2607.14988), [2607.15326](https://arxiv.org/abs/2607.15326), [2607.15159](https://arxiv.org/abs/2607.15159), [2607.19574](https://arxiv.org/abs/2607.19574), [2607.22460](https://arxiv.org/abs/2607.22460), [2607.22498](https://arxiv.org/abs/2607.22498), [2607.25865](https://arxiv.org/abs/2607.25865), [2607.27527](https://arxiv.org/abs/2607.27527), [2607.28621](https://arxiv.org/abs/2607.28621), [2607.28795](https://arxiv.org/abs/2607.28795), [2608.00165](https://arxiv.org/abs/2608.00165), [2608.00601](https://arxiv.org/abs/2608.00601), [2608.01111](https://arxiv.org/abs/2608.01111), [2608.01887](https://arxiv.org/abs/2608.01887), [2608.05518](https://arxiv.org/abs/2608.05518), [2608.05688](https://arxiv.org/abs/2608.05688), [2608.05821](https://arxiv.org/abs/2608.05821), [2608.07431](https://arxiv.org/abs/2608.07431), [2608.08996](https://arxiv.org/abs/2608.08996), [2608.09115](https://arxiv.org/abs/2608.09115), [2608.09727](https://arxiv.org/abs/2608.09727), [2608.09886](https://arxiv.org/abs/2608.09886), [2608.10069](https://arxiv.org/abs/2608.10069), [2608.11160](https://arxiv.org/abs/2608.11160), [2608.12450](https://arxiv.org/abs/2608.12450), [2608.12509](https://arxiv.org/abs/2608.12509), [2608.15754](https://arxiv.org/abs/2608.15754), [2608.16857](https://arxiv.org/abs/2608.16857), [2608.16995](https://arxiv.org/abs/2608.16995), [2608.17118](https://arxiv.org/abs/2608.17118), [2609.27801](https://arxiv.org/abs/2609.27801), [2608.18536](https://arxiv.org/abs/2608.18536), [2608.19094](https://arxiv.org/abs/2608.19094), [2608.19917](https://arxiv.org/abs/2608.19917), [2608.20164](https://arxiv.org/abs/2608.20164), [2608.23460](https://arxiv.org/abs/2608.23460), [2608.24000](https://arxiv.org/abs/2608.24000), [2608.25797](https://arxiv.org/abs/2608.25797), [2608.25959](https://arxiv.org/abs/2608.25959), [2608.27565](https://arxiv.org/abs/2608.27565), [2608.29173](https://arxiv.org/abs/2608.29173), [2608.30775](https://arxiv.org/abs/2608.30775), [2609.00167](https://arxiv.org/abs/2609.00167), [2609.00234](https://arxiv.org/abs/2609.00234), [2609.02098](https://arxiv.org/abs/2609.02098), [2609.02428](https://arxiv.org/abs/2609.02428), [2609.03021](https://arxiv.org/abs/2609.03021), [2609.03048](https://arxiv.org/abs/2609.03048), [2609.04121](https://arxiv.org/abs/2609.04121), [2609.04459](https://arxiv.org/abs/2609.04459), [2609.05699](https://arxiv.org/abs/2609.05699), [2609.06572](https://arxiv.org/abs/2609.06572), [2609.08203](https://arxiv.org/abs/2609.08203), [2609.08957](https://arxiv.org/abs/2609.08957), [2609.10683](https://arxiv.org/abs/2609.10683), [2609.12020](https://arxiv.org/abs/2609.12020), [2609.11723](https://arxiv.org/abs/2609.11723), [2609.11796](https://arxiv.org/abs/2609.11796), [2609.15924](https://arxiv.org/abs/2609.15924), [2609.16125](https://arxiv.org/abs/2609.16125), [2609.16133](https://arxiv.org/abs/2609.16133), [2609.16542](https://arxiv.org/abs/2609.16542), [2609.20780](https://arxiv.org/abs/2609.20780), [2609.26735](https://arxiv.org/abs/2609.26735), [2609.26736](https://arxiv.org/abs/2609.26736), [2609.30069](https://arxiv.org/abs/2609.30069), [2609.30159](https://arxiv.org/abs/2609.30159), [2609.30860](https://arxiv.org/abs/2609.30860), [2609.31541](https://arxiv.org/abs/2609.31541), [2609.35129](https://arxiv.org/abs/2609.35129), [2609.35601](https://arxiv.org/abs/2609.35601), [2609.36213](https://arxiv.org/abs/2609.36213), [2609.36273](https://arxiv.org/abs/2609.36273), [2609.37699](https://arxiv.org/abs/2609.37699), [2609.38986](https://arxiv.org/abs/2609.38986), [2609.38996](https://arxiv.org/abs/2609.38996), [2609.39345](https://arxiv.org/abs/2609.39345), [2609.40252](https://arxiv.org/abs/2609.40252), [2609.40313](https://arxiv.org/abs/2609.40313), [2609.40319](https://arxiv.org/abs/2609.40319), [2610.00525](https://arxiv.org/abs/2610.00525), [2610.00561](https://arxiv.org/abs/2610.00561), [2610.00865](https://arxiv.org/abs/2610.00865), [2610.01277](https://arxiv.org/abs/2610.01277), [2610.02137](https://arxiv.org/abs/2610.02137) | No separate circuit-distance size/method in catalog; static parameters remain in each linked local paper summary. |

### Standard earlier and out-of-catalog references

| Reference | Circuit-distance relevance and reported scope | Verification/caveat |
|---|---|---|
| [Bravyi et al., High-threshold and low-overhead fault-tolerant quantum memory, 2308.07915](https://arxiv.org/html/2308.07915v1) | §6 random logical-row augmentation + BP-OSD; Table 1 `(n,k,d_circ bound)` = `(72,12,≤6)`, `(90,8,≤8)`, `(108,8,≤8)`, `(144,12,≤10)`, `(288,12,≤18)`. n counts data; 2n total qubits. Gross 12-round decoding matrices have 8857/8785 columns. Candidate static code distances use ILP. | Primary checked. BP-OSD bounds are witnesses, not optimum proofs. The random logical-row 1/2 coverage argument is conditional on an optimal decoder and does not certify BP-OSD success probability. |
| [Gidney, Stim, 2103.02202](https://arxiv.org/abs/2103.02202), [Stim API](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference) | DEM compiler and graphlike/undetectable-error searches; source of the detector model used by the papers above. | Installed Stim1.15 APIs inspected and WCNF/signature conversion checked locally; see §§1–2 for proof limits. |
| [Pryadko/Zeng, dist-m4ri](https://github.com/QEC-pages/dist-m4ri), [QDistRnd](https://github.com/QEC-pages/QDistRnd) | Connected-cluster and randomized information-set/random-window methods are cited as established code/circuit baselines by [Webster et al., §4](https://arxiv.org/html/2603.22532v1). Vine uses connected clusters for exact circuit distances. | Current repository/manual interfaces inspected; see §§1–2 and §4 for commands and build proposals. |
| [Berent et al., Decoding quantum color codes with MaxSAT, 2303.14237](https://arxiv.org/abs/2303.14237) | MaxSAT decoding through LightsOut formulation; MQT implementation. | arXiv abstract search checked. Direct HTML v1 request failed (“Internal Error”). Decoder benchmark, not a verified dedicated circuit-distance result. |
| [Noormandipour/Haug, MaxSAT decoders for arbitrary CSS codes, 2410.01673](https://arxiv.org/abs/2410.01673) | Hard syndrome clauses, weighted soft error clauses; includes nonuniform/biased errors and surface/BB decoding. | arXiv abstract checked; no minimum circuit-distance achievement extracted. |
| [Ott/Hetényi/Beverland, Decision-tree decoders for general quantum LDPC codes, 2502.16408](https://arxiv.org/abs/2502.16408) | Provable minimum-weight decoder plus heuristic variant; abstract explicitly says adaptable to all minimum-weight logical operators and provable distances. | arXiv abstract checked. Run/API, licence and largest certified distance not verified. |
| [Aghababaie Beni/Higgott/Shutty, Tesseract, 2503.10988](https://arxiv.org/html/2503.10988v1) | A* on subsets of DEM mechanisms; admissible search can be exact. §3 identifies heuristic pruning/cutoffs; §5 compares exact DTD, MaxSAT, IP and Tesseract without beam cutoffs. [Repository](https://github.com/quantumlib/tesseract-decoder) also contains HiGHS integer-program decoder. | Primary checked. “AtMostTwo” pruning loses exactness; finite beam, queue limits, and other heuristic restrictions must be considered when claiming a proof. Paper decodes noisy syndromes, not a published largest exact circuit-distance sweep. |
| [Beverland et al., Fail Fast, 2511.15177](https://arxiv.org/html/2511.15177v1) | Adaptive decoder-prior perturbation is the distance-upper-bound technique cited in [LR circuits Appendix D.2](https://arxiv.org/html/2603.05481v1). | Primary page opened; direct algorithm text not audited here. 2603.05481 explicitly returns an upper bound and uses 10,000 outer loops only as evidence for its d=11 conjecture. |
| [Webster/Jacob/Higgott, Distance-Finding Algorithms for Quantum Codes and Circuits, 2603.22532](https://arxiv.org/html/2603.22532v1) | Direct prior benchmark of exact MILP/MaxSAT/connected-cluster/Brouwer-Zimmermann against randomized window/evolution/BP-OSD/Stim search. Table 2 recommends m4riCC for surface/color circuits and Gurobi for BB circuits. Adds QDistEvol refinement and Python Brouwer-Zimmermann. [codeDistance source](https://github.com/m-webster/codeDistancePYPI). | Primary checked. Not in local code-construction catalog. §5.5 filters DEM mechanisms/detectors before benchmarking; use identical verified reductions across competitors. The original d=11 superdense circuit has 43,298 unique mechanisms (§1). |

### Dedicated 2024–2026 methods requiring explicit consideration

- The directly verified general circuit-distance comparison/algorithm package is [2603.22532](https://arxiv.org/html/2603.22532v1). It is a required prior-art benchmark reference. Its exact tools remain separate competitors; wrapping them in codeDistance does not make them one algorithm.
- [PropHunt §5](https://arxiv.org/html/2601.17580v1) searches ambiguous connected DEM subgraphs with MaxSAT. Subgraph optima supply global witnesses, but do not by themselves rule out a lighter solution elsewhere.
- [Morphing circuits Prop. 1/§2.5](https://arxiv.org/html/2604.09797v1) supply a proven reduction of two-round morphing/alternating extraction distance to one measurement round. This is a structured-circuit reduction to pair with any exact solver, not a replacement arbitrary-DEM solver.
- [Amplified qLDPC Appendix B.2](https://arxiv.org/html/2609.37231v1) computes response certificates by Dijkstra/BFS after quotienting by stabilizers; theorem transfer gives large lower bounds. Its response problem omits ordinary syndrome-record constraints, so that minimum is a lower bound on the complete circuit minimum. Large finite memories have unequal lower and upper bounds.
- [MaxSAT arbitrary CSS, 2410.01673](https://arxiv.org/abs/2410.01673), [DTD, 2502.16408](https://arxiv.org/abs/2502.16408), and [Tesseract, 2503.10988](https://arxiv.org/html/2503.10988v1) are broadly applicable search/solver methods whose exact versions can serve as distance searchers via added logical parity constraints. The adaptation must be explicit; ordinary zero-syndrome decoding returns the empty error.

### Unverified details and interpretation cautions

- `C` rows preserve catalog assertions and linked reviewed versions; they are not independent source verification. Most analytical papers’ maximum finite sizes, full noise support, proof artifacts, and executable APIs were not checked here.
- Several catalog reviewed versions are newer than v1 (LR circuits, morphing, Bunny, Routing, Cornucopia). Primary verifications above are explicitly v1; check newest versions before quoting a changed value. The catalog field remains authoritative only as a record of its own review.
- Vine’s catalog selected four instances, but its primary Table 1 has 18 exact patches; use the expanded values above. The largest Table 1 total qubit count is 683 at circuit distance 6, while verified distance-7 examples reach total qubits 535. Table 2 distance-10 labels are conjectural.
- Walking Cat’s Table 10 circuit minima were found, but no circuit-distance algorithm or proof-status explanation was located. Its Appendix C exhaustive enumeration/QDistRnd statements describe static code distance and must not be transferred to circuit distance.
- ZSZ-LP’s catalog does not give Table 15 values; the primary source supplies ≤8/10/12 for n=160/240/320. Blank large-code cells do not justify a d−2 certificate.
- Dynamic 4.8.8 says its full Stim undetectable search yields exact d=L, but supplies no search truncation options or largest L. Treat this as an author claim until settings confirm completeness; its timelike boundary-path brackets have not been shown equivalent to the benchmark H,L minimum.
- API/build/licence/download-size details and their remaining gaps are in §§1–2 and §4. No repository was cloned, archive downloaded, package installed, environment created, solver run, or remote job submitted in this catalog audit.


## 4. Ranked benchmark recommendation and acquisition decisions

### Necessary for a defensible exact circuit-distance comparison

1. **Current dist-m4ri connected cluster (`method=2`) and bracketing (`method=3`).** Established exhaustive sparse-search competitor with direct H,L/DEM input and partial bounds. Run unrestricted CC and combined RW+CC separately; a combined solver gets one total budget, not a free precomputed upper bound. [Source](https://github.com/QEC-pages/dist-m4ri).
2. **Native Gurobi MILP and one open MILP implementation (SCIP preferred; HiGHS also useful).** Published prior circuit benchmarks select different winners by circuit family. Use the same parity constraints and the same verified variant, with no metadata incumbent. Gurobi's usable licence is a prerequisite; lack of a licence must be reported as a benchmark coverage limitation. [Prior benchmark](https://arxiv.org/html/2603.22532v1), [Stairway](https://arxiv.org/html/2603.00228v1).
3. **SAT/cardinality, PySAT RC2, the direct prior CASHWMaxSAT-CorePlus/CLISAT solver, and generic branch-and-bound MaxSAT (MaxCDCL family).** RC2 alone does not cover the strongest published MaxCDCL results or establish equivalent performance to the prior CLISAT implementation. Benchmark Stim WCNF and explicit-column H,L encodings, charging export/model recovery; require completion/UNSAT and checked witnesses. CASHW licence/build details remain an acquisition gap. [QDistSAT](https://arxiv.org/abs/2606.12445), [prior comparison](https://arxiv.org/html/2603.22532v1), [Stim invocation](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimcircuitshortest_error_sat_problem).
4. **Logical-aware BZ/codeword enumeration and meet-in-middle.** codeDistance supplies the direct prior implementations, but its MITM wrapper lacks a witness; Qubitserf's chosen Z sector is an independent candidate after witness/deadline audit. Include a usable logical-aware BZ implementation, and either run a usable MITM engine or disclose its interface gap. [codeDistance](https://github.com/m-webster/codeDistancePYPI), [Qubitserf](https://github.com/Quantinuum/Qubitserf).
5. **Stim graphlike exact search on eligible instances.** It is a necessary fast baseline wherever all original columns have detector degree≤2. On a hypergraph its restricted result belongs to the upper-bound comparison. [API](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimdetectorerrormodelshortest_graphlike_error).

**Conditional exact challenger:** height-bound DTD is provably applicable via logical-row augmentation; its unverified public release prevents a reproducible run now. Tesseract/Simplex may become exact competitors only after auditing full-search completion, witness recovery and interruption bounds. CP-SAT is a useful extra exact solver once OR-Tools is approved. Formal Lean/VeriPB checking should be included if the claim concerns independently checked proof artifacts rather than completed solver optimality. [DTD](https://arxiv.org/abs/2502.16408), [Tesseract](https://github.com/quantumlib/tesseract-decoder), [Lean-QEC](https://github.com/VerifiedQC/Lean-QEC), [proof-logging MaxSAT](https://arxiv.org/abs/2511.10273).

### Useful upper-bound comparisons

1. **QDistEvol, dist-m4ri RW, BP+OSD**, and **Stim hypergraph search**: direct prior comparators with different search behavior; record trials/settings/seeds and never assign a heuristic lower bound. BP+OSD should include logical-row augmentation and sampled-noise residual search as separately named configurations. [QDistEvol](https://github.com/m-webster/codeDistancePYPI), [dist-m4ri](https://github.com/QEC-pages/dist-m4ri), [BP+OSD](https://software.roffe.eu/ldpc/ldpc/bposd_decoder.html), [Stim](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference).
2. **QDistRnd**: independent information-set implementation, especially for code-capacity CSS inputs; matrix conversion overhead matters for circuits. [Manual](https://qec-pages.github.io/QDistRnd/doc/chap4.html).
3. **Tesseract heuristic search**, and Fail Fast prior perturbation if an implementation is obtained: useful circuit-specific witness search, not an exact proof comparator in their pruning/sampling modes. [Tesseract](https://github.com/quantumlib/tesseract-decoder), [Fail Fast](https://arxiv.org/abs/2511.15177).

### What can be left out, with the scope stated

| Method/tool | Reason for omission from the main arbitrary-DEM exact benchmark |
|---|---|
| Native DistQLDPC and QDistSAT's four-CSS-file frontend | Valuable code-capacity controls, but no verified fixed-sector arbitrary H,L route; generic MaxCDCL/RC2 covers their solver classes without changing the target ([README](https://github.com/guluchen/DistQLDPC)). |
| Magma | Optional independent BZ control if already licensed; open logical-aware BZ gives class coverage. If included use≥2.29-9 for fixed multithread quantum-distance bug ([release notes](https://magma.maths.usyd.edu.au/magma/releasenotes/2/29/9/)). |
| GAP/GUAVA classical distance, ldpc classical kernel-distance routines | Native objective includes trivial stabilizers; exact coset adaptation can be exponential and lacks a verified witness/deadline interface here ([GUAVA](https://gap-packages.github.io/guava/doc/chap4.html), [ldpc](https://software.roffe.eu/ldpc/ldpc/mod2.html)). |
| Open-WBO / MQT / arbitrary-CSS MaxSAT decoder as additional frontends | Generic exact MaxSAT already covers the class; color-code or syndrome-decoding APIs need logical augmentation, so their decoding benchmarks are not exact-distance evidence ([Open-WBO](https://github.com/sat-group/open-wbo), [MQT](https://github.com/munich-quantum-toolkit/qecc), [CSS paper](https://arxiv.org/abs/2410.01673)). |
| Tensor-network enumerators | Retain as prior art; no verified general DEM executable and exact contraction is topology dependent. Include if an accessible implementation and favorable instance representation emerge ([paper](https://arxiv.org/abs/2308.05152)). |
| Lean-QEC, proof-logging WMaxCDCL | Proof-artifact comparators, not currently verified general DEM timed APIs; include for a stronger machine-checked-certification claim ([Lean](https://github.com/VerifiedQC/Lean-QEC), [MaxSAT](https://arxiv.org/abs/2511.10273)). |
| Structured surface/topological proofs, morphing reduction, response amplification | Apply only where hypotheses match the input/noise model; their analytical bounds do not compare general solver speed ([morphing](https://arxiv.org/abs/2604.09797), [amplification](https://arxiv.org/abs/2609.37231)). |
| PropHunt subgraph scoring | Restricted search already supplies UB; no unrestricted optimum proof verified ([paper](https://arxiv.org/abs/2601.17580)). |
| Probability-weighted decoding / effective-distance fits | Different objective or statistical metric; use unit weights plus nontrivial-logical constraints if adapting a decoder ([Stim SAT APIs](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference)). |

### Individual acquisition/build proposals — none executed

Each row is a separate approval item. Sizes are distribution-specific and exclude dependencies; “unstated” is not an estimate. Pin the approved version/commit, platform, compiler and solver configuration. Reuse already installed versions first; no survey command below downloaded or built software.

| Approval item / priority | Download source and stated size | Proposed installation/build after approval; dependencies and restrictions |
|---|---|---|
| Stim — existing required baseline | [PyPI](https://pypi.org/project/stim/), [GitHub](https://github.com/quantumlib/Stim); 1.16.0 sdist882.5kB, CPython3.13 Linux wheel5.3MB | Installed1.15 already exports distance WCNF; no upgrade required. If approved on fresh server: `python3.13 -m pip install stim==1.16.0`; wheel installation, no build. |
| PySAT — required SAT/RC2 | [PyPI](https://pypi.org/project/python-sat/), [GitHub](https://github.com/pysathq/pysat); current1.9.dev15 sdist6.0MB | Server1.8 already present; reuse it. Fresh approved install `python3.13 -m pip install python-sat==1.9.dev15`; source build needs compiler; optional `aiger,pblib` extras are separate acquisitions and not required for seqcounter/RC2. Audit embedded-solver licences. |
| dist-m4ri — required CC/RW/bracketing | [GitHub](https://github.com/QEC-pages/dist-m4ri); archive/repo size unstated | Approved source tree: `cd src`, then `make all`; GCC, POSIX threads and libm4ri development headers/library. libm4ri is a separate dependency approval. Do not use obsolete generated-manual command. |
| Gurobi — required commercial MILP | [PyPI](https://pypi.org/project/gurobipy/); 13.0.3 CPython3.13 Linux x86-64 wheel14.9MB, no source build offered | `python3.13 -m pip install gurobipy==13.0.3`; licence permitting problem size and publication required. This version requires Python≥3.10; no local3.9 installation. No licence activation performed. |
| OR-Tools / SCIP / CP-SAT — required open solver alternative | [PyPI](https://pypi.org/project/ortools/), [source](https://github.com/google/or-tools); 9.15.6755 CPython3.13 Linux x86-64 wheel29.8MB | `python3.13 -m pip install ortools==9.15.6755`; bundled native solver wheel; Python≥3.9. Source alternative requires CMake≥3.24/C++20 and separately approved native deps (zlib, bzip2, Abseil, Protobuf, COIN-OR, SCIP/SoPlex; [build docs](https://github.com/google/or-tools/blob/stable/cmake/README.md)); wheel preferred, exact Python dependency resolution not inspected. |
| SciPy / HiGHS — existing MILP | [PyPI](https://pypi.org/project/scipy/), [HiGHS](https://github.com/ERGO-Code/HiGHS); current SciPy1.18.1 sdist30.8MB | Reuse local1.13.1/server1.16; neither needs upgrade for `milp`. Fresh wheel `python3.13 -m pip install scipy==1.18.1` (requires Python≥3.12). Direct highspy acquisition is optional and must be separately approved if used for audited thread control. |
| enMaxCDCL — required branch-bound MaxSAT candidate | [authors' repo](https://github.com/zjl9959/enMaxCDCL_CP26), [binary page](https://github.com/zjl9959/enMaxCDCL_CP26/blob/main/bins/enMaxCDCL); binary12.7MB, repo size unstated | Approved tree: `cd codes/enMaxCDCL/simp`, `make rs` (Linux GCC≥15.2, static libstdc++/zlib); macOS `make` -> `maxcdcl`. Alternatively approved published Linux binary. Licence coverage/WCNF parser/model printing must be audited. Original MaxCDCL2024 is separately acquired via the authors' linked evaluation archive or QDistSAT's `python3 scripts/download_maxsat_solvers.py --only maxcdcl`; original archive size/build unverified; do not fetch all solvers. |
| CASHWMaxSAT-CorePlus — direct prior required MaxSAT comparator | [Stim-linked archive](https://maxsat-evaluations.github.io/2023/mse23-solver-src/exact/CASHWMaxSAT-CorePlus.zip), verified as a reference on the [Stim API page](https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference#stimcircuitshortest_error_sat_problem); size unstated | After approved archive acquisition: `unzip CASHWMaxSAT-CorePlus.zip`, then `./CASHWMaxSAT-CorePlus/bin/cashwmaxsatcoreplus -bm -m instance.wcnf`. Supplied binary, no compile step in documented example. Licence, dependencies, source build, platform compatibility and interruption behavior unverified; archive was not fetched. |
| codeDistance — required direct prior BZ/MITM implementation; useful QDistEvol | [PyPI](https://pypi.org/project/codedistance/), [GitHub](https://github.com/m-webster/codeDistancePYPI); 0.0.8 wheel55.0kB, sdist1.9MB | `python3.13 -m pip install codedistance==0.0.8`; approved source `python3.13 -m pip install -e .` (poetry-core build). Requires Python≥3.10; declared deps stim, NumPy, qiskit, igraph, gurobipy, ldpc, numba, ortools, python-sat, typing_extensions ([manifest](https://github.com/m-webster/codeDistancePYPI/blob/main/pyproject.toml)); approve dependency set explicitly. MIT file conflicts with GNUv3 manifest/PyPI; resolve before redistribution. |
| Qubitserf — independent exact BZ/CC/MITM candidate | [GitHub](https://github.com/Quantinuum/Qubitserf); size unstated | `python3.13 -m pip install .` in approved tree; alternative `./build.sh` and `PYTHONPATH=python`; NumPy, Python≥3.9, CMake≥3.20, C++17. CPU backend sufficient; CUDA/Metal optional and not requested. Witness/deadline API audit required. |
| ldpc BP+OSD — useful upper bound, already on server | [PyPI](https://pypi.org/project/ldpc/), [GitHub](https://github.com/quantumgizmos/ldpc); 2.4.1 sdist1.1MB | Reuse server2.4.1. Fresh approved `python3.13 -m pip install ldpc==2.4.1`; deps NumPy/SciPy/tqdm/pytest/stim/sinter/pymatching; source build Cython/setuptools/compiler ([manifest](https://github.com/quantumgizmos/ldpc/blob/main/pyproject.toml)). Python≥3.10 excludes local3.9. |
| QDistRnd — useful random information sets | [GitHub/releases](https://github.com/QEC-pages/QDistRnd), [install docs](https://github.com/QEC-pages/QDistRnd/blob/main/README.md); size unstated | GAP≥4.13 bundle: `LoadPackage("QDistRnd");` no build. Otherwise approved release under GAP `pkg`; GAP/GUAVA separate dependency approvals. RNG/deadline and printed-vector parsing audit. |
| Tesseract — useful heuristic; conditional exact | [PyPI](https://pypi.org/project/tesseract-decoder/), [GitHub](https://github.com/quantumlib/tesseract-decoder); 0.1.1.dev20260910235247 CPython3.13 Linux wheel3.4MB(glibc2.39)/3.5MB(glibc2.35) | `python3.13 -m pip install tesseract-decoder==0.1.1.dev20260910235247`; source `bazel build src:all`. Bazel downloads dependencies: Stim/HiGHS/Boost/zlib/pybind11/rules_python/rules_cc ([manifest](https://github.com/quantumlib/tesseract-decoder/blob/main/MODULE.bazel)); approve them first. Source distribution size unverified. |
| QDistSAT — optional published code-only controls | [GitHub](https://github.com/guluchen/QDistSAT); size unstated | Approved tree `python3.13 -m pip install -e '.[dev]'`; external solvers individually via documented `--only` downloader, SMT `z3-solver`/`cvc5` separately. Do not run omnibus install/download script. |
| DistQLDPC — optional code-only branch-bound control | [GitHub](https://github.com/guluchen/DistQLDPC); size unstated | Approved source `make` -> `bin/distqldpc`; g++/zlib; fixed-sector adaptation remains unverified. |
| Magma — optional independent code-distance control | [ordering](https://magma.maths.usyd.edu.au/magma/faq/costs), [installation](https://magma.maths.usyd.edu.au/magma/faq/install); binary size unstated | Licensed binary only, no source build verified; install per platform instructions; quantum multithread version≥2.29-9. No purchase/download proposed automatically. |
| GAP/GUAVA — optional coset reference | [package](https://gap-packages.github.io/guava/), [install](https://gap-packages.github.io/guava/doc/chap1.html); size unstated | Usually included in GAP: `LoadPackage("guava");`; approved source optional Leon binaries `./configure ../..`, `make`; GAP≥4.11 and SONATA≥2.3. Exact coset witness interface not audited. |

DTD, Fail Fast, tensor-distance software, structured morphing reduction and proof-logging WMaxCDCL have no verified acquisition/build recipe in inspected sources. They are literature gaps, not silently runnable recommendations. Optional structured `dp_certificates` and Lean-QEC recipes are in the inventory; no generic DEM frontend was verified. Open-WBO is redundant with required MaxSAT configurations; if chosen as an additional control, approved source build is `make rs` ([INSTALL](https://github.com/sat-group/open-wbo/blob/master/INSTALL)), source/archive size unstated, MIT plus embedded-solver licences. No build was run.

### Reporting requirements and remaining verification gaps

Report one record per method/configuration/variant/seed, with instance digest, original-column witness, elapsed wall time, native threads or explicit lack of thread support, solver version, settings, completed weight exclusions, and termination status. Repeated random trials share the stated total budget; publish seed distribution and best UB versus wall time, not a statistically certified exact value. Any available CPU/GPU acceleration is a separately labelled resource configuration. No confidence interval is justified merely because many heuristic runs agree.

Local checks covered installed Stim exports/column signatures on two fixtures, the direct XOR-CNF encoding by exhaustive tiny truth tables, a three-column SciPy MILP, Python3.9 syntax of the recipes, table structure, local links and all296 catalog IDs ([check results](../results/bench_dev/survey/verification.json)). No external solver performance was measured. Per-codeDistance-backend maxima remain unverified without its detailed XLSX outputs; licence declarations conflict and its MITM wrapper lacks a witness. Qubitserf's int-only API, Tesseract/DTD exact completion, MaxCDCL model printing, native DistQLDPC sector restriction, MatrixMarket parser compatibility, floating-bound tolerances and several licences remain source-audit items. Failed source views and actual commands are in the survey research notes. Catalog coverage is complete for its296 entries, not proof of exhaustive worldwide literature coverage.
