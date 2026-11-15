# CodeGarden phase-three progress — research ongoing

Updated 2026-11-15 08:53 UTC. **Target not achieved. Best independently verified code: 226 distinct words.** No 227-word witness or new global-record claim.

## Incumbent and verification
Fresh official preflight at 08:49 UTC reproduced kgrey's arena solution 2778, score 226, SHA-256 `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`. Its 6,410 distinct length-14 descendants are disjoint across codewords. Independent LCS verification checked all 25,425 pairs, maximum 13. Official verifier hash remains `563cc3bc7d39bdc261dd6cff08eb634c03e149d59df8f0c7ceff5b3f68730325`.

Arena comparison is not a complete global-record audit. Historical 208, literature 215, and the reproduced current arena 226 are different comparison points. The protected verifier sources remain unchanged. Positive-energy 227-word states are invalid diagnostics.

## Completed findings
- **Connected exchange search:** any improving compatible bundle has a blocker-connected improving component. A unique canonical parent enumerates connected bundles; currently disconnected but compatible future candidates remain available. Thirty-six small deletion-code brute-force comparisons and 160 arbitrary blocker/compatibility examples check implementation.
- **Root exact local radius eight:** independent orderings completed without a strict improvement. Ascending order took 328.312 CPU seconds; constrained-first order took 130.138. This is a native exhaustive local search, not global optimality and not a formal proof certificate.
- **Certified outside dominance:** all 444 descendant-inclusion replacements are independently checked using protected string descendants. Pruning outside dominated words preserves existence of strict improvements with a bounded removal count, including when replacement restores an incumbent word. Thirty-six additional small brute-force comparisons include incumbents containing dominated words. Reduced radius eight completed in 96.063 CPU seconds. Radius nine and ten each timed out after 450 CPU seconds; neither is an impossibility result.
- **Neutral component:** full radius-five enumeration closed exactly 38 labeled 226-word codes. Primitive connected neutral moves reproduced the same component at radius five (5.49 native CPU seconds), six (39.97), and seven (298.80). All 38 witnesses passed both protected verifiers, and all individual radius-seven searches completed without augmentation. Radius eight neutral exploration was capped and is not closed. All 38 codes survive dominance normalization unchanged; these are not merely dominated-word aliases.
- **Persistent walkers:** fixed radius-three from eight distant 225-word starts explored 6,000 states and recovered 226 repeatedly, but the recovered 226 lies in the known component. Adaptive radius-three/four processed 834 states and stopped before its adaptation trigger. Different seeds and caps prevent a causal policy-superiority claim.
- **Frontier repair:** fixed low-radius closures no longer silently stop the entire search. Completed frontier_002 runs explicitly escalated after local exhaustion and distinguished capped retries from closure. Four lineages retained scores 225,225,224,223; larger repairs consumed their 450 CPU-second limits without a novel 226 orbit.
- **Tempering:** genuine symmetric Metropolis and replica exchange passed independent energy checks. A denser 32-temperature ladder improved swap traffic, but four paired 180-CPU-second comparisons still reached only positive conflict energy. Exact vertex-cover projections of archived states produced zero novel 226 orbits. Quench/injection flow statistics are not equilibrium mixing estimates.
- **CP-SAT:** union pools 896 and 930 were optimal at 226 within those pools. Subsequent novel-component cuts yielded one restricted INFEASIBLE result and three UNKNOWN results. Full-universe and 3,032-word CP/LNS runs returned feasible 225 hints only, with open bounds and explicit fixed-word/component-cut restrictions. No global upper bound follows.
- **KaMIS:** pinned upstream `2e4b3861b8063f05e8520434b97ce59e21ca49e7`; full conflict graph has 65,536 vertices and 80,964,349 edges, independently checked for small instances. Original warm starts retained 226. ReduMIS failed with bad_alloc under a 6-GiB cap. A documented saturating fix for an upstream unsigned plateau decrement retained 226 from root and 225 from distant starts; no demonstrated improvement.
- **Other attempts:** infeasible-state tabu, Morris-style breakout, conflict closures, elastic CP, and pair replacements found no valid 227. Full-universe LP attempts returned no usable primal and produced zero LP-guided repairs. These incomplete attempts remain visible.

## Current hypothesis: reuse local certificates
The isolated learned_native_001 experiment is running from `f6b84881208f231ec2583c8f17fffa0013902d46`, Actions run 43696235726. If an outside compatible set T contains a known balanced neutral set U, then the proposed improved code differs from the neutral code by at most k-|U| removals. A completed radius-seven no-improvement search around that code can therefore forbid this whole subset when k-|U| <= 7. Each clause records both witness hashes, blocker sets, source, pool hash and radius.

The contraction lemma and pruned search are checked against exhaustive arbitrary conflict examples before the length-16 run. This changes proposal enumeration, never validity. Saturated helper repairs remain unrestricted, so an exported positive candidate is always checked as ordinary explicit data. No outcome of this pending experiment is claimed yet.

## Real sponsor execution and limits of the evidence
Actual Exa requests in research_003 used recalled analyst findings to choose connected local-improvement and canonical-enumeration queries. `providers.py::Providers.exa` is called from `phase3/research3.py::main`. Query/source/request provenance and paraphrased method links are preserved.

Past.dev has three named software author identities in one serialized process. The researcher retrieved the analyst's structured radius-eight finding and used it to change the first external query; the strategist retrieved cross-author material before a decision. These are logical software roles, not independent assistant subagents.

A real Tinker 4B choice selected primitive_bridge. It generated a valid 225-word bridge followed by a capped radius-eight search, without improving 226. This is verified decision execution, not evidence of trained-policy superiority. New fine-tuning is not justified by zero primary improvements. Earlier fixed-budget trained/untrained tie and negative results remain in the phase-two report.

Modal ran bounded independent CPU workers with pinned source, seeds, starting codes, time limits and exported witnesses. The 36-root older radius-six batch returned all workers: 12 complete and 24 timeouts. The newer primitive kernel subsequently closed radius six across all 38 much faster; we do not count the old timeouts as proofs.

## Shared resources
All code and artifacts are remote under codegarden/, with only the separately authorized launcher outside that directory. Public standard GitHub runners make zero sponsor API calls unless running the serialized provider coordinator. BoundForge and forecasting files/jobs are preserved.

Conservative cumulative accounting through research_003: Exa $0.098; past.dev 278 estimated credits; Modal $96.56 held; Tinker $22.85 held. Historical unknown holds and failed-launch reservation remain included. These are not attributed actual account charges. Current caps are Exa $5, past 2,000 credits, Modal $100, Tinker $70. Other-project reserves and independent verification reserves remain intact. Allocation expires 12:00 UTC; no new billable reservations after 11:45 UTC. No replenishment, plan upgrade or billing setting change.

## Provenance and unresolved work
Per-experiment artifacts contain exact starting hashes, candidate pools or pool hashes, parameters, statuses and independent positive verifications. phase3_progress.json pins the consolidated branches. The preserved native completeness claims have no formal proof artifact. One thermal projection diagnostic used colliding filenames for already-known recoveries; no novel witness or primary score depends on those files.

Continue testing new structural/search hypotheses until a real independently verified target witness exists. Larger local neighborhoods, new basins and the source audit remain open. The mathematical objective is unresolved.
