> Phase one is preserved below. See [the phase-two report](phase2_report.md) for the subsequent bounded campaign and current limitations.

# CodeGarden research report
Research date: November 14, 2026 (America/Los_Angeles); execution timestamps use UTC.

## Result and target
Best found and best independently verified: **226 words**, reproduced from
kgrey's arena submission 2778. **No 227-word code was found and no new global
record is claimed.** The primary mathematical objective remains unmet.

Canonical witness SHA-256:
`417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`.

The [live arena API](https://einsteinarena.com/api/solutions/best?problem_id=34&limit=5)
was rechecked at 2026-11-15T04:09:15Z: its leading listed score was 226, with the
same canonical witness hash. See artifacts/sources/arena_final_check.json.
227 is consequently the provisional strict-improvement target for this capture.

The [official problem and verifier](https://einsteinarena.com/problems/two-deletion-code-16)
agree with the requested conventions: descendants are sets within a word, and
ambiguities concern descendants shared across different words.

## Comparisons that remain separate
- Historical [CPro1](https://github.com/Constructive-Codes/CPro1) construction:
  208, reproduced from the author result pinned to
  `5b26b1a5ca0625a857cf6c2adcc6668e1d66a2ac` and from the arena.
  The canonical witnesses agree exactly.
- [Weindel–Heckel v2](https://arxiv.org/html/2504.00613v2) reports 215 for a KaMIS
  comparison, 200 in one of the authors' own search rows, and an LP upper bound
  of 487. The 215 is a literature report; its witness was not reproduced here.
- Five explicit arena/historical witnesses, of sizes 208, 223, 224, 225 and 226,
  passed the two independent verifiers and the official verifier.
- A complete global-record audit is not established. An asymptotic construction
  or a secondary site's stale lower bound does not supply a new explicit n=16
  witness.

## Trustworthy verification
The string-deletion verifier validates alphabet, length and uniqueness, deduplicates
each word's descendants, and reports conflicting words, a shared descendant and
deletion positions. The separate dynamic-programming LCS implementation imports
no descendant code. Its maximum LCS on the 226-word witness is 13 across 25,425 pairs.
The string verifier finds 6,410 occupied distinct descendants. The official
verifier also scores the witness at 226.

The supervisor checks pinned verifier source hashes and runs both in fresh
subprocesses before accepting exported best witnesses. The proposer chooses only
bounded action identifiers; it cannot alter verifier files or reported scores.
This is an application interface boundary, not an OS sandbox against arbitrary
hostile programs.

Twenty-one tests pass, covering strict parsing, duplicate/collision failures,
exhaustive small-length incidence agreement, brute-force bounded-search checks,
timeout semantics, budget refusal and the actual tokenizer/action-parser contract.
Native checks additionally compare 512 length-16
descendant sets with the string implementation, reject duplicate input, check
incremental state and independently verify actual search output.

## Search and experiments
The sparse representation includes all 65,536 words, 16,384 descendants and
2,244,608 deduplicated incidences. Python uses packed integers and bitsets; the
compiled kernel uses incidence lists, descendant owners, blocked counts and an
incremental compatible-word list. Neither needs a dense conflict graph.

| Experiment | Actual result | Scope |
|---|---|---|
| 12 seeded greedy constructions | 145–192 words | Tiny method sample, not bounds |
| Four 60-cycle fixed/adaptive pilots | 226 retained | Unequal runtime, integration check |
| Seed-43 three-second pair | Both 226 | Single matched budget, no efficacy claim |
| 21 bipartite-union optimizations | No improvement over better input | Matching/vertex-cover union certificates |
| Hosted 1,200-cycle adaptive batch | 226 verified | Seed 2026 |
| Hosted 5,000-cycle adaptive batch | 226 verified | Seed 2027 |
| Eight sparse CP-SAT weight-band repairs | Four INFEASIBLE, four UNKNOWN | Fixed outside and explicit candidate pools |
| Full-universe CP-SAT target 227 | UNKNOWN after 181.04 s | No global impossibility conclusion |
| Eight compiled Modal workers | 226 verified in all eight | Four paired seeds, 120-second search caps |
| Structural probes | VT-style restriction 131; repeated/mirrored families 23–25; recursive product 49 | Tested families only; independently verified |

Hosted receipts:
[1,200 cycles](https://github.com/howdymary/compute-forecasting/actions/runs/43670274708),
[5,000 cycles](https://github.com/howdymary/compute-forecasting/actions/runs/43670635979),
[CP-SAT](https://github.com/howdymary/compute-forecasting/actions/runs/43671948159),
[compiled paired batch](https://github.com/howdymary/compute-forecasting/actions/runs/43672967716).

Compiled Modal results:
- 2,295,850 iterations total; fixed 1,632,250, adaptive 663,600.
- Four fixed/adaptive pairs all retained the same 226-word best.
- 126 retained archive entries represent 116 distinct codes, or 112 orbits under
  the separately verified complement/reversal symmetries. Sizes are 224–226.
- Pairwise symmetric differences range from 2 to 446. This is combinatorial
  diversity, not evidence of a new best code or independent sample quality.
- All eight best exports pass string and LCS verification both in workers and on
  the separate GitHub host. Archive members are string-verified in workers.
- Native workers use one CPU and 768 MB, at most four concurrent containers, with
  checkpoints committed to CodeGarden's own Volume. No GPU is used.

The structural module also checks a recursive product of a seven-word length-8
component with itself. The 49 resulting length-16 words pass both verifiers.
Syndrome-restricted and mirror-family results are exploratory lower baselines;
they never cause candidates to be permanently excluded from the main search.
The recorded structural run used RAM only and wrote no workstation project files.

## What the negative results justify
The exact union certificates prove optima only in their explicitly recorded
unions. CP-SAT INFEASIBLE means no strict improvement with that fixed outside and
candidate pool; no independently checked SAT proof artifact was produced.
UNKNOWN means the solver did not establish feasibility or infeasibility within
the limit.

The native batch found no strict improvement within its randomized trajectories
and time caps. It does not exhaust any global neighborhood. The adaptive policy's
zero best-improvement rewards led to balanced operator exploration; switching
alone is not learned recognition of mathematical exhaustion. No advantage over
the fixed strategy is established.

All detailed Python exact neighborhoods record witness/pool hashes, the fixed
outside, pool restrictions, budgets and status. Native algorithm source, seed,
starting baseline, resources and final archive define a bounded heuristic
experiment, not an exhaustive certificate. A scoped aggregate finding is in
artifacts/negative_findings.json.

## Executed sponsor loop and adaptation
Real Exa research, past.dev role memory, Modal workers and Tinker training all ran.
See docs/sponsor_provenance.json, integrations/STATUS.md and the saved status files.
Three Exa calls returned sources and $0.021 in API-reported cost. The actual
call path is providers.py::Providers.exa. A single-deletion MILP/conflict-graph
source informs a representation adapted to two deletions; retrieved papers do
not promise that CodeGarden's neighborhoods will improve this incumbent.
The record-check query returned current/asymptotic literature, not a new verified
length-16 witness.

The feedback context contains actual recalled analyst/researcher content, source
IDs and content hashes. Both untrained and trained decisions used the identical
context hash. Multiple logical roles wrote and read; execution is serialized in
one orchestrator. Independently spawned assistant agents were not demonstrated.
GitHub artifacts authorize scores; past.dev stores source-backed findings,
hypotheses, results and scoped negatives, never authoritative witnesses.

Tinker used Qwen/Qwen3.5-4B, rank-8 LoRA and eight updates on 32 verified small-code
cases. Eight disjoint held-out cases were generated; the first six, selected
before evaluation to fit the reservation budget, were evaluated.

| Evaluation | Before | After | Justified conclusion |
|---|---:|---:|---|
| One selected repair per small held-out case, summed sizes | 100 | 104 | Better operator preference in this tiny action-count comparison |
| Frozen choices replayed for 0.2 search CPU seconds per case | 113 | 104 | Training lost under this matched-compute replay |
| Same n=16 context/start/seed, 30-second caps on the same runner | 226 | 226 | No length-16 gain |

The initial one-action comparison consumed approximately 0.028 versus 0.038 seconds
of reported search/verification work, so it was not an equal-consumed-CPU result.
The matched replay is explicitly post-hoc and reuses frozen decisions; it is not
a fresh generalization test. Its per-case measured CPU times are about
0.200–0.203 seconds. Both original policies chose a constant operator across the
six cases: random8greedy before, opportunity12exact after. This does not establish
state-dependent exhaustion recognition.

For n=16, the saved untrained action ran 1,551 cycles and the trained
action ran 232 cycles, retaining 226 in both. The existing private
sampler checkpoint was restored only after matching its exact saved SHA-256;
there was no second training run. No adaptation benefit under matched budgets
is established.

Early integration failures are preserved: missing template dependency, tokenizer
return type, Modal closure serialization, parser rejection, metadata lookup and
a skipped-client preflight mismatch. Paid decisions were resumed from durable
receipts when possible. Partial status files were never treated as successful
research results.

## Budget and isolation
[Shared allocation](../budget/shared-allocation.json) is pinned to the authenticated
BoundForge balance snapshot at commit
`938795b118ffdc40e1a84abeb7361b8f41721adb`. It subtracts BoundForge's full
operational allowances, forecasting pending guards and verification reserves.
The CodeGarden caps are Exa $2, past.dev 500 credits, Modal $10 and Tinker $20.
These are allocations, not assertions that they were spent.

CodeGarden stages are serialized under one orchestrator and share one job ledger.
Conservative historical reservations are imported on subsequent runners.
Other projects' private SQLite ledgers do not participate in this coordinator.
Available balances and usage are distinct from pending reservations; unknown or
expired allocations refuse further billable work.

Actual Exa cost receipts, estimated memory credits, unresolved Modal/Tinker
reservations, remaining project allowances and attribution gaps are separated in
budget/usage-summary.json. No credit purchase, automatic replenishment, upgrade
or payment-setting change was made.

All project source, dependencies, environments, demo and results stay under
codegarden/. The sole approved exception is .github/workflows/codegarden.yml.
Development used the codegarden branch, with no workstation project checkout.
The comparison against the original branch point changes no existing file outside
codegarden/: only the new launcher is added. Existing default-branch forecasting
and BoundForge jobs were neither cancelled nor modified.

## Demo and independent reproduction
[Open the recorded dashboard and live decoder](https://raw.githack.com/howdymary/compute-forecasting/186ed67fc18fa7509889205fd41d284ab6b43355/codegarden/demo/index.html).
The static proxy can show an external-content notice first; it requires no account
or credentials. The repository contains the complete demo source and data.

The demo labels recorded experiments separately from its live browser decoder.
A verified UI interaction recovered `0000000001000011` from
`00000001000011` after deleting zero-based positions 2 and 7.
The rejected pair of all-zero and last-bit-one words visibly shares fourteen zeros.

From a remote container at the repository root, no model or provider API is
needed for either verification command:

~~~sh
python -B codegarden/protected/verify_descendants.py codegarden/artifacts/best_code.txt
python -B codegarden/protected/verify_lcs.py codegarden/artifacts/best_code.txt
~~~

## Final checks and scoped duplicate audit
[Final verification run](https://github.com/howdymary/compute-forecasting/actions/runs/43675549312)
passed all 21 tests, compiled-kernel checks and both independent verifiers for
25 explicit exported length-16 witnesses. It also reverified the recorded
small-code replay witnesses without overwriting timing receipts. Its default
mode was verify and made no paid provider calls.

artifacts/experiment_index.json inventories 360 teacher action experiments and
12 initial before/after evaluations. The 12 policy-selected evaluations
intentionally repeat fixed-seed teacher configurations; they are not independent
additional samples. Duplicate tracking is scoped to that inventory, not every
inner-loop mutation. No strict-improvement operator or time/cost to improvement
is reported, because no length-16 improvement occurred.

## What changed and what remains unknown
Correctness no longer depends on a proposer score. Independent witnesses, source
pins, exact pool logs, conservative provider reservations and durable remote
receipts make results reviewable. Incremental compiled search materially increases
the number of attempted moves. Early recovery-based rewards were corrected to
count improvements over the retained best.

No larger length-16 code was discovered. It remains unknown whether learned
neighborhood selection helps at n=16, whether larger exact neighborhoods can
escape the current basin, and whether unlocated literature contains a stronger
explicit reproducible construction. More switching or more sampled codes would
not settle those questions by itself.
