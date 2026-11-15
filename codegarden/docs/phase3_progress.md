# CodeGarden research checkpoint

Updated 2026-11-15, 17:35 UTC. **Goal not achieved. Best found and independently verified: 226, reproduced from the arena.** No new 227-word construction or global record is claimed.

## Mathematical status

The arena preflight at 17:27:55 UTC still lists kgrey’s solution 2778 with 226 words. The official verifier is unchanged. The reproduced witness has SHA-256 `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`, occupies 6,410 distinct length-14 descendants, and passes all 25,425 pairwise LCS checks with maximum 13. Historical 208 and the Weindel–Heckel literature result of 215 are separate comparisons. The global literature audit remains incomplete.

The protected descendant and LCS verifiers are unchanged. A separate verifier-only job has replayed the baseline and six 225-word witnesses with frozen checker source `ce5eab1859c271686876ee5c2d21c0e0a5316d67`. Every future 227-word candidate must pass fresh isolated acceptance before the goal can be completed.

## Latest experiments

| Experiment | Result | What remains open |
| --- | --- | --- |
| Broad fixed-64 CP models, four control/treatment pairs | All eight retained 225 after 150 solver-wall seconds and two workers; no treatment gain | All eight models timed out; the imposed 227 ceiling is not a global bound |
| Fresh 225-word radius-nine exchanges | Six of seven families completed, with no new code; five completed families are unfiltered | 405 roots remain in the final narrower goal-filtered family |
| Neutral radius nine from the 226-word root | All 56,840 roots completed; no new 226 or 227; 701.5274 summed native CPU seconds | Disconnected unsaturated neutral exchanges are outside the completeness claim |
| Three-parent unions from seven fresh families | 560 orientation proposals reduced to 556 distinct models; all attempted; 134 completed without a new 226 | 422 models timed out after two native CPU seconds each |
| Neutral radius ten | 54,720 of 61,871 roots completed; no new code | 7,151 roots remain open |

The neutral searches exclude the 152 known oriented 226-word arrays as exact goals. Larger supersets remain eligible. Coverage concerns connected outside-blocker bundles and saturated repair pools. These results are conditional native computations, without independent formal absence certificates.

The new neutral kernel passed 1,200 exhaustive saturated-graph fixtures and 400 connected-blocker fixtures. The goal-filtered triple kernel passed 1,300 exhaustive graph fixtures, including excluded minimum goals with eligible larger extensions.

The first neutral-nine launch passed its native fixtures but failed before any mathematical workers because an unused import required ortools. Removing that import kept setup dependency-free; the corrected preflight and search succeeded. This setup failure is retained in the detailed report. An older radius-nine continuation printed legacy FRESH8 labels; its structured `exchange_rank: 9` and `native.k: 9` were correct. No score depended on the label.

## Current hypothesis: whole low-blocker corridors

A RAM-only profile found 185 outside words with one or two distinct blockers around the 226-word root. Their mate graph contains a stub-reachable component touching 95 incumbent words. The seven fresh 225-word families have such components touching 77–107 incumbent words. A large component does not establish a compatible augmenting path.

[Dong et al., MetaMIS](https://mauricio.resende.info/doc/metaMIS.pdf), sections 3.2–3.4, describes one-tight and two-tight neighborhoods and alternating augmenting paths. Our adaptation searches the entire induced packing pool at once, allowing an unlimited number of affected incumbent words to change. It widens blocker thresholds from two to three to four after exact model closure or bounded stagnation, recording those reasons separately.

The proposed batch uses eight starting codes and 60 native CPU seconds per explicit model. Only incumbent words untouched by every eligible outside word are fixed. All other incumbent words and all eligible outside words remain in the pool. Exact known 226-word goals are excluded; larger supersets remain eligible. A new 226-word code is independently checked and receives strict augmentation attempts toward 227. The active branch is `codegarden-low-blocker-001`; no result is assumed in this checkpoint.

## Earlier findings retained

The detailed JSON report preserves the completed strict radius-ten search around the reproduced root; the 38 known 226-word codes and their 216-word common core; supported core removals through rank five; single and compound pivot studies; pair recombination; coordinate lifts; two-choice domains; conditional guidance; matching completion; and exact-family studies.

These have produced no new 226 or 227. Guided search supplied 28 portfolio-new 225-word orbits; the combined guided/neutral delta supplied 39 relative to the recorded older portfolio. All 74,880 explicitly represented pair queries incident to the new canonical parents completed without a strict new code. Some overlap older or symmetry-equivalent families. Diversity is secondary evidence, not objective success.

An adaptive minimum-growth study closed 123 families versus 68 for random selection, but both retained a method score of 225. Earlier Tinker evaluation did not establish a cardinality benefit. Positive-energy 227-word states remain invalid. Neither speed nor diversity nor negative-query counts substitute for a verified 227-word witness.

## Budget, preservation, and evidence

All new batches in this checkpoint use standard public GitHub runners. No new Exa, past.dev, Tinker, or Modal requests or reservations were created. The paid allocation expired at 12:00 UTC; unknown balances remain unavailable. Existing conservative holds and other-project and verification reserves are preserved. The last dashboard attempt reported a locked Mac. No credits were bought, no card was added, and no billing settings changed.

Earlier genuine sponsor calls remain in their original artifacts. New artifact reuse is labeled as local-artifact reuse. The MetaMIS refresh used web research and is not labeled as an Exa call. The provenance is: query → primary paper → extracted neighborhood method → measured topology → explicit repair experiment → protected witness checks.

All application code, dependencies, results, and logs remain under `codegarden/`. Only approved isolated launchers use `.github/workflows/codegarden.yml` on experiment branches. The main launcher, protected checkers, default branch, BoundForge, and other project files are preserved. No project checkout, generated artifact, or environment was written on the workstation.

- Full findings and source revisions: `docs/phase3_progress.json`.
- Exact solver models, pools, environment snapshots, and checks: `artifacts/phase3/fresh_cp_001/`.
- Fresh radius-nine coverage: `artifacts/phase3/fresh9_resume_001/` and `artifacts/phase3/fresh9_tail_001/`.
- Neutral coverage: `artifacts/phase3/neutral9_goal_001/` and `artifacts/phase3/neutral10_goal_001/`.
- Explicit three-parent models and statuses: `artifacts/phase3/fresh_triples_001/`.
- Large older raw logs: immutable source links in `artifacts/phase3/immutable_query_log_index.json`.

The demo is a dated replay of verified evidence. A timeout is open. A completed local result applies only to its encoded pool and move rules. The research goal remains active.
