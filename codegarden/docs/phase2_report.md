# CodeGarden phase-two research report

Research date: November 14, 2026, America/Los_Angeles; run timestamps are UTC.
Bounded window: 2026-11-15 04:18:09–05:48:09 UTC. New paid work is forbidden after 05:33:09 UTC.

## Mathematical result

Best found and best independently verified: **226**, reproducing kgrey's arena submission 2778.
No 227-word code was found. No new global record or global optimality result is claimed.
The primary mathematical objective remains unmet.

Canonical witness SHA-256: `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`.

The current arena was refreshed before search and again in the final closeout. The initial
capture at 04:24:21 UTC reproduced all five leading witnesses; the leader was 226.
[Final arena capture, verifier comparison and account receipts](../artifacts/phase2/closeout.json)
are authoritative for the final timestamp. The official verifier matched its pinned source.
The two protected verifier files and their manifest were not changed.

The historical [CPro1 construction](https://github.com/Constructive-Codes/CPro1) remains 208,
with its source revision and matching explicit witness pinned in the phase-one report.
[Weindel–Heckel v2](https://arxiv.org/html/2504.00613v2) reports a 215-word KaMIS comparison;
that particular witness was not reproduced. These literature reports and the arena standings
are distinct. A complete global-record audit has not been established.

## What changed

The compiled kernel now supports explicit 1→2 and bounded 2→3 augmentations,
depth-three ejection repairs, structural and variable-size ruin/recreate, exact-state
exhaustion caching, and archives deduplicated under complement/reversal.
Sparse ownership/incidence structures retain the full 65,536-word universe.
Two independent implementations of the exchange enumerator passed 48 small-instance
brute-force comparisons each.

Sixteen Modal search periods ran 3,840 search CPU seconds and **8,488,730 iterations**.
Independent islands exchanged archived populations at the period boundary.
There was no improvement beyond 226. Population diversity, per-worker resource receipts,
native configuration hashes and scoped cache counters are retained in
[analysis](../artifacts/phase2/analysis.json), long_period1.json and long_period2.json.
Period-two islands started from different donor archives, so their aggregate fixed/adaptive
scores are exploratory rather than a paired causal comparison.

## Exact scoped negative findings

| Removed k | New words sought | Removal sets exhaustively checked around the pinned incumbent |
|---:|---:|---:|
| 1 | 2 | 226 |
| 2 | 3 | 25,425 |
| 3 | 4 | 1,898,400 |
| 4 | 5 | 105,835,800 |

Every row uses all 65,536 candidate words, excludes original incumbent words from additions,
and tests every removal set. The compiled enumeration reports completion without an improving
move. These are executable enumeration results, not independently certified formal proofs.
They do not imply global optimality.

[Root radii 1–2](../artifacts/phase2/root_sweeps.json);
[radii 3–4](../artifacts/phase2/radius34/sweeps.json).

A separate conflict-driven batch selected **512** explicit 5–12-word removal sets.
For each fixed outside code, its repair pool includes every compatible word in the full universe.
175 pools have matching-cover certificates; the other 337 were declared INFEASIBLE by CP-SAT.
An independent checker imported neither the search implementation nor OR-Tools: it rebuilt
all 512 pools using the protected string descendant generator, checked the 175 matching
certificates, and re-solved the other 337 with exact compatibility-clique search.
The initial audit passed in 9.72 seconds; the final audit also reconstructs every one-for-one neighbor of the plateau component. Scope is precisely those recorded pools, not every radius-5–12 exchange.
[Report](../artifacts/phase2/conflict_repairs/report.json);
[independent audit](../artifacts/phase2/conflict_repairs/independent_audit.json).

Six additional sparse CP-SAT repairs—three population unions and three ruin repairs—were
INFEASIBLE in their encoded pools. Some union pools were extremely small (4–6 words);
the result diagnoses insufficient useful diversity, not a strong global bound.
The prior full-universe target-227 CP-SAT run remains UNKNOWN, not impossible.

## Structural and plateau probes

Complement and reversal were checked on all 65,536 words before orbit-based search.
Complement-invariant packing improved its own greedy code from 196 to 198; the
complement-and-reversal family stayed at 188. Both 60-second CP-SAT solves ended FEASIBLE,
without an optimality certificate. Their solver upper bounds are loose family bounds;
they do not improve the published global bound. All explicit outputs passed both verifiers.
[Orbit experiment receipts](../artifacts/phase2/orbit_search/report.json).

Four 30-CPU-second one-for-one plateau walks retained 226 and each visited just two distinct
states. Their high cache-hit counts reveal repeated work rather than progress.
The follow-up exhaustively found a component of exactly two states: replacing integer word 584 with 1096, or reversing that swap. Neither has a compatible extra word without removal. All 1→2 through 4→5 exchanges were also exhausted around the second state. The final independent string-based audit reconstructs all neighbors in both states. Additional scoped
augmentation checks in [the component report](../artifacts/phase2/plateau_component/report.json).
Only completed flags justify exhaustion. These outer-controller extensions were selected
after inspecting failures and are outside the preregistered policy comparison.

## Learning gate and controlled comparisons

The evaluation manifest was committed before counterfactual labels or training.
There were 32 training cases and eight held-out cases, with disjoint exact starting-code
symmetry orbits. The original split used arena-author families; a later overlap audit found
the 225-word family has **0.71483 maximum Jaccard overlap** with 226 modulo symmetries.
Author names therefore do not establish independent construction lineages.
The supplemental fixed-operator selection excluded that close family. All eight held-out
cases still derive from one 226-word lineage, limiting generalization.

The six operators were compared under one search CPU second per case, with all outputs checked.
Nineteen cases had different raw outcomes, but exchange23 was the only unique winner and
was tied for best on every case. The gate rejected conditional learning, so **no new Tinker
fine-tuning or checkpoint was created**.

A stricter reward audit found all raw gains were recovery to known parents: **zero cases
exceeded their known parent cardinality**, and zero had differential gains beyond that reference.
These data do not support training a discovery policy. Future dataset code now gates on gains
above the maximum known parent/episode best. The original raw receipts are preserved unchanged;
the corrected gate and early metadata persistence are post-experiment fixes, not features
retroactively attributed to the recorded runs.
[Reward audit](../artifacts/phase2/reward_audit.json).

The original 120-CPU-second study completed eight cases in each of three conditions.
All three summed to 1777 verified best words, with 960 search CPU seconds per condition.
After the gate failed, the two nominal adaptive arms used the same empirical operator sweep.
They made no LLM decisions and did not reach exchange23 during their four chunks.
This is **not evidence for or against an LLM or research/memory benefit**.

A separate preregistered supplemental study compares a training-selected strong fixed
operator, the untrained model without external context, the same model with actual recalled
evidence, and the pinned historical trained checkpoint with the same evidence.
All use eight matched starting codes/seeds and 20 search CPU seconds per case, the same
legacy action space mapped explicitly into six native backends, and equal monetary caps.
It is an experiment-level operator choice, not a test of within-episode switching.
No new model was trained on the degenerate phase-two labels.

| Condition | Cases | Sum / mean verified best | Search CPU s | Per-case decisions s |
|---|---:|---:|---:|---:|
| strong_fixed | 8 | 1807 / 225.875 | 160.00 | 0.00 |
| untrained_no_external | 8 | 1776 / 222.000 | 160.01 | 44.07 |
| untrained_with_memory | 8 | 1771 / 221.375 | 160.01 | 45.31 |
| historical_trained_with_memory | 8 | 1807 / 225.875 | 160.00 | 44.18 |

The historical trained proposer selected exchange23's backend in all eight cases and tied the training-selected fixed control at 1807 total (225.875 mean). The untrained/no-context control totaled 1776; recalled context totaled 1771. All 24 model choices parsed as valid. Per-case decision timing excludes shared model initialization, checkpoint lookup, image preparation and the initial memory ingest/recall; those shared overheads are not fully instrumented. Their wall time is visible in the linked workflow receipts. This supports the historical checkpoint's operator choice on these recovery cases, while a fixed operator achieved the same result with negligible controller overhead. Recalled context did not improve this small search comparison. It does not demonstrate new adaptation, discovery, or general superiority beyond this single-lineage sample.

The enclosing supplemental status is `failed_or_partial` because the subsequent, separate memory benchmark failed required-source retrieval; the 32 search evaluations themselves were complete and durable. That failure is preserved rather than hidden behind the workflow's successful exit code. A serialized memory-only recovery uses the original analyst root-result source and imports every cumulative hold.


[Supplement protocol](../artifacts/phase2/supplement/protocol.json);
[results](../artifacts/phase2/supplement/evaluation.json);
[score/resource curves](../artifacts/phase2/score_resource.svg);
[raw curve data](../artifacts/phase2/score_resource.csv).
Curves use independently verified chunk endpoints, not unverified internal score claims.
Configuration duplicates and equivalent backend aliases are reported separately.
Recovered parent words are not counted as new mathematical discoveries.

The no-memory/full-history/past.dev **memory-only ablation is incomplete**. The first attempt failed required-source retrieval after five model calls; its progress file was not promoted by the enclosing script. A separate 24-query retry used the original analyst root-result source, but its publisher then failed with `KeyError: SOURCE_SHA`: the workflow supplied `GITHUB_SHA` and omitted the publisher variable. The ephemeral runner's per-question data was not committed. No accuracy, latency or token-cost scores are inferred for that lost run. The failure receipt and workflow logs are preserved; a conservative extra $1.20 Tinker hold and 32 past.dev credits cover its full bounded possible usage. The publisher fallback is fixed prospectively. This is an implementation/durability failure, not evidence that memory improved or harmed the benchmark. The four-condition search comparison above was already durable and remains complete.

The prior negative Tinker evidence remains: one-action small-instance totals rose 100→104,
but under matched search CPU budgets the result reversed, 113→104. Length-16 transfer
retained 226→226. The saved historical sampler is compared without relabeling it as newly
adapted. Its pinned identifier hash is
`da17c9ec31e782ae2f5a265b12c6f8d68a634d6f274b5377f3695264d97203cb`.

## Research and cross-role memory: what actually happened

Analyst PID 2972 wrote the scoped root failure; researcher PID 2975 recalled that source,
made a real Exa request, and wrote a source-backed larger-repair hypothesis. Strategist
PID 2980 recalled the researcher source and wrote the plan. Later the analyst wrote outcomes
and the researcher retrieved them. These are independently executing Python processes with
separate inputs, outputs and memory authors; they are not an autonomous swarm of independent
LLM scientists. Their role plans are bounded software templates. The outer research assistant
made additional experiment-level judgments.

Actual Exa query:
`binary deletion code maximum independent set escape two exchange local optimum large neighborhood exact set packing`.
Request ID: `efcbc532f1843c857a81c4c93eacd56b`.
It returned [Sviridenko–Ward](https://arxiv.org/abs/1302.4347), motivating larger packing
neighborhoods. The paper studies local-search limitations and larger exchanges; its
approximation guarantee is not claimed for CodeGarden's implementation.
The initial automated HTML excerpt captured navigation rather than the substantive method;
the primary abstract was re-read during closeout, and this provenance limitation is retained.

Exa is called in `codegarden/providers.py::Providers.exa`, from
`phase2/role.py::main` and the bounded final record check in `phase2/closeout.py::main`.
Past writes/reads are in `Providers.write/read`; source IDs, returned content hashes,
parents and process IDs appear under [roles](../artifacts/phase2/roles/).
The source-backed method was followed by larger repairs and verified negative results.
The additional radius/component probes were chosen by the outer assistant after inspecting
these findings. This documents an evidence trail, not a demonstrated learned switching advantage.
GitHub/Modal hold authoritative witnesses and run receipts; past.dev holds facts, hypotheses,
scope restrictions and links.

## Accounting, isolation and reproducibility

Provider caps are cumulative across phases: Exa $5, past.dev 2,000 credits, Modal $50,
Tinker $70. Full BoundForge reservations, separate forecasting guards and verification
reserves were deducted before CodeGarden allocations. Authenticated initial balances were
Exa $119.44, Modal $249.21, Tinker $280.43, and past.dev 699,336 credits.
No purchases, upgrades, replenishment, payment methods or billing limits were changed.

The main campaign and supplemental paid work were serialized with one Actions concurrency
group. The supplemental ledger imported every main-campaign cumulative hold before spending;
closeout imports that cumulative ledger again. Historical unknown charges were not silently
released. Exact charges, gross account estimates, unresolved holds and per-provider units
remain distinct in [final accounting](../budget/phase2-usage-summary.json).
Account-wide usage includes other projects; it is not all attributed to CodeGarden.
No dollar cost is invented for past.dev credits.

All application/source/artifact changes are under codegarden/, apart from the approved
isolated launcher. Scratch branches isolated CPU-only probes and queued model controls.
No workstation project checkout or project files were created. BoundForge/forecasting
files, dependencies, credentials and jobs were not modified or cancelled.
Workers checkpointed CodeGarden-only Volumes; completed jobs and the final app inventory
document their state.

Main immutable executed source:
`c484c1629ebd04149512697ec617ae9d31636eb7`.
Supplement source:
`9ba3694d779244641a2f89561a0d264d7db46eb4`.
Each side experiment pins its own source in its report. The final source contains explicitly
identified prospective fixes; immutable executed revisions remain the reproduction authority.

Main run: [43677895831](https://github.com/howdymary/compute-forecasting/actions/runs/43677895831). Supplemental controls: [43679442742](https://github.com/howdymary/compute-forecasting/actions/runs/43679442742). Memory recovery: [43681234748](https://github.com/howdymary/compute-forecasting/actions/runs/43681234748).

## Verification and next hypothesis

In an authorized remote container, from the repository root:

~~~sh
python -B codegarden/protected/verify_descendants.py codegarden/artifacts/best_code.txt
python -B codegarden/protected/verify_lcs.py codegarden/artifacts/best_code.txt
python -B codegarden/supervisor.py codegarden/artifacts/best_code.txt
python -B codegarden/phase2/audit_certificates.py
python -B codegarden/phase2/exhaustion_index.py
~~~

The protected boundary is an application interface and pinned-source supervisor, not a
security sandbox against arbitrary hostile native code. No boundary defect was found.
The final verification manifest records every exported file, with byte-identical witness
data checked once in fresh protected subprocesses and safely reused across copies.

The next specific hypothesis is to search connected multiword neutral components or
larger blocker unions that escape the small plateau and evade matching-cover obstructions.
Prioritize diverse near-226 incumbents before expensive union repairs. A useful training
episode must improve on its known parent, not just restore removed words. Stop revisiting
a component once its recorded finite scope is exhausted; a new incumbent invalidates old
exhaustion unless a verified symmetry maps the entire scope.

Remaining gaps: no 227 construction; no global optimality or complete global-record audit;
limited family independence; no new informative Tinker training set; small memory benchmark;
unresolved provider attribution; and no demonstrated general learned advantage. Sponsor
integrations and a working replay demo do not establish hackathon victory.

## Final closeout receipt

The final verification run [43681661930](https://github.com/howdymary/compute-forecasting/actions/runs/43681661930) passed: **189 exported files, 117 distinct byte sequences**, every accepted exported witness valid under both protected checks. The existing 21-test suite passed. The separate final scope audit also independently reconstructed every neutral neighbor in both plateau states and all 512 full repair pools. Its source is pinned in the audit artifact.

The arena still led at 226 in the final 05:35 UTC capture. Both CodeGarden Modal apps were stopped in the final inventory. No additional paid experiment is pending.

| Provider | Cumulative conservative hold | CodeGarden cap | Unreserved allocation |
|---|---:|---:|---:|
| Exa | $0.028 | $5 | $4.972 |
| past.dev | 165 credits | 2,000 credits | 1,835 credits |
| Modal | $23.56 | $50 | $26.44 |
| Tinker | $22.65 | $70 | $47.35 |

These holds include historical and failed-run uncertainty and are **not actual charges**. Four unique Exa provider receipts report $0.028 gross. The final account-wide Modal meter was $2.13016283, offset by credits/allowances; it is not all CodeGarden spending. Tinker account-wide gross estimates were $0.808107828, with no reliable metadata match to CodeGarden and possible hourly lag. Past.dev's live account balance was 699,250 credits. Other-project reserves remain separate. No unknown hold was released.
