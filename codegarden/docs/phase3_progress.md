# CodeGarden research status — 2026-11-15T13:35:49Z

**Objective open. Best found and independently verified remains226, reproduced from the arena. No227 witness or new global record is claimed.**

## Verification and comparison

The current official preflight at13:32:16UTC still reproduces kgrey’s solution2778 at226. Witness SHA-256: `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`. The unchanged protected checkers accept6410 distinct14-bit descendants and25425 pairwise LCS comparisons, maximum13. Duplicate words, invalid lengths/alphabet and cross-word descendants remain failures; repeated descendants within one word are deduplicated.

The arena comparison is current; it is not a complete global-record audit. The checked [Weindel–Heckel primary paper](https://arxiv.org/html/2504.00613v2) reports215 from general MIS solvers at length16. Its released framework is [DistributedFunSearch](https://github.com/MLI-lab/DistributedFunSearch). The older public208 baseline, later arena constructions and incomplete literature/global audit remain distinguished in prior reports. No record claim follows from this limited literature check.

## Completed local results

- Root strict radius10 is completed across old eight prefixes and32 resumed suffixes. Every61427-root index is covered exactly once, totaling17262.28 native CPU seconds. A separate coverage audit passed. This is a restricted native enumeration under pinned safe reductions, not a global or formal independently checked absence proof.
- The38 known226 codes share216 words. Independent literal-string enumeration considers all65536 words, finds57 outside variables compatible with the full fixed core, and establishes maximum226 with exactly38 maxima. Each maximum passes both protected verifiers. The older241-word palette contains only25 variables; it is not the full fixed-core pool.
- All23436 single/pair and1656360 triple core-removal queries completed. Checked blocker-support generation reduces88201170 four-sets to203077 supported queries, and3739729608 five-sets to2731144 supported queries. All primary227 and secondary226 targets completed without improvement, timeout or pool cap. Unsupported sets are eliminated only by the explicit reinsertion lemma and lower-depth prerequisites. Case9’s initial HTTP502 happened before search; its isolated retry completed.
- These conditional computations imply a different226 or any227 must omit at least six shared-core words. They concern this core and pinned computations; they do not establish global optimality.
- All51569 single forced-pivot hulls completed both targets, without caps/timeouts. A further16 bounded compound-pivot runs processed38785634 query **occurrences** and found no new226 or227. Counts overlap across workers and are not globally unique neighborhoods or exhaustive compound-family coverage.
- Core-quota heuristics produced positive-energy invalid states. Complete minimum-cover projection of final states independently checked34 explicit projections and selected eight fresh225 orbits. Two exact repairs recovered known226 codes; six remained225. Their completed radius6/7 neighborhoods and four radius8 neighborhoods are scoped negatives; radius9 attempts timed out.
- A goal-filtered connected kernel continues beyond known226 recoveries. It passed160 arbitrary-graph controls and two goal-filter fixtures. Eight runs found no novel226 or227. **The strict-gain connected-component lemma does not imply completeness for novelty-filtered search.** Disconnected combinations can remain unsearched even when this encoded family finishes.
- Multi-edge star capture now recognizes that several pair-conflict edges may share one removable word. Independent two-edge and three-edge regression fixtures recover known226 codes. Eight full runs found no novel226 or227. This corrects event coverage; it is not a new mathematical construction.
- Four full compatible core hulls fix185,201,209 or206 core words and use pools457,369,75 or91. All eight matched CP-SAT models return OPTIMAL225 **after excluding known226 at exact size226, or imposing conditional overlap cuts**. Exact-size exclusions allow every larger candidate. These are novelty-model optima; the known226 codes remain valid constructions in the ordinary problem. Fixed-core/pool hashes and model text are preserved.

Earlier randomized construction, ARW/KaMIS, Hamming mutation, weight-band, tensor, exact-repair, structural-hash, union-fusion and long Modal results remain in durable artifacts and earlier reports. No adaptive or trained-policy superiority has been established. Structural hashing itself reached202; the retained global226 score is separate.

## Active hypothesis: expand an exhausted family

[Run43719457523](https://github.com/howdymary/compute-forecasting/actions/runs/43719457523) compares random single-word unfixing with adaptive unlock-ranked1/2/4-word unfixing, from four matched225 seeds. Each case has a600-wall-second search deadline and two CP-SAT threads; actual CPU is recorded separately.

The loop keeps an independently valid225 hint. Only a completed OPTIMAL225 novelty-model result closes its fixed-set family. A closed-family exclusion is carried forward **only for candidates of size>=226**, so225 hints remain feasible. It then unfixes additional core words and admits every word compatible with the enlarged family. FEASIBLE/UNKNOWN leaves the child open, restores the last completed parent and changes the relaxation. Checkpoints include source/engine hashes, explicit fixed sets, pools, statuses, witnesses, RNG state and dependency receipts. Resume requires the same engine and a225 checkpoint.

Any new226 passes both protected checkers, then receives unfiltered bounded augmentation toward227. A positive-energy state, timeout or solver log cannot establish success.

## Real sponsor use and credit boundaries

Real Exa calls, source-backed reviews, past.dev writes/recalls and Tinker choices are preserved in `research_gpu_002/`, `research_gpu_003/` and `research_cpu_001/`. API location: `codegarden/providers.py::Providers.exa`, called from `phase3/research_gpu2.py::main`. Separate frozen contexts acted as analyst, researcher and strategist; a researcher actually used the analyst’s retrieved finding, and the strategist actually retrieved the researcher’s method context before choosing quota206. These are role contexts, not assistant subagents or an asynchronous swarm.

Modal rejected T4 deployment because that account requires a payment method. No payment method, replenishment, plan or billing settings changed. The CPU fallback actually completed in930.854seconds and retained226. No GPU speedup/result is claimed. Earlier trained/untrained comparisons and their tied/negative outcomes are preserved; no new training success is asserted.

Cumulative conservative holds remain Exa0.112USD, past319credits, Modal149.998USD and Tinker23.05USD. These are not attributed charges. Full other-project and verification reserves remain protected. No unknown hold was released. The last paid allocation expired12:00UTC; current experiments use free public standard GitHub runners with bounded jobs and short artifact retention.

Read-only accounting at13:08:36UTC returned Modal account-wide gross3.49103696USD, billed0, past balance699096, and a partial Tinker priced-row estimate22.645927005USD with eight unpriced rows and no invoice-reconciled boundary. These are account metadata, not project attribution or fresh prepaid balances. Exa/Tinker prepaid balances remain unknown because dashboard access is unavailable on the locked desktop. No allocation was renewed or billable work started by these reads. Earlier schema-parsing attempts must not be read as zero spend.

## Evidence limits and preservation

Most bulk native negatives store reconstructible family definitions, completion vectors and sampled individual pool hashes, rather than a SHA-256 for every query. The newer CP trials store every explicit fixed set, candidate pool/hash, model hash, parameters and solver status. No formal absence certificate is claimed. All33 size225 long-run checkpoints were symmetry-equivalent to the older412-state archive, preventing repeated completed-neighborhood work.

All project source, dependencies, environments, artifacts, logs, reports and demo are remote under `codegarden/`. The approved isolated workflow is the sole tracked exception. Main consolidation preserves every blob outside the directory, the main launcher and protected verifier files. Isolated branches and source pins retain historical failures and limitations.

## Independent commands

```sh
python -B codegarden/protected/verify_descendants.py codegarden/artifacts/best_code.txt
python -B codegarden/protected/verify_lcs.py codegarden/artifacts/best_code.txt
python -B codegarden/phase3/audit_root10.py
python -B codegarden/phase3/core_all_optima.py
```

The explicit witness and acceptance checks require no model, provider API or search history. The latter audits cover logged local families, not the entire code problem.
