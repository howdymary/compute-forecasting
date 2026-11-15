# CodeGarden phase-three progress — research ongoing

Updated 2026-11-15 07:14 UTC. Mathematical completion target: an explicit independently verified binary length-16 two-deletion code with at least 227 distinct words, or a source-audited new global record. **Target not achieved. Best independently verified remains 226.**

## Incumbent and scope
The reproduced arena incumbent is kgrey's 226-word construction, witness SHA-256 `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`. Fresh official preflights continue to reproduce 226 and check the pinned official verifier. Arena comparison is not a complete global-record audit.

D2 and pairwise LCS verifiers remain protected and unchanged. Positive-energy 227-word search states are invalid diagnostics. Only explicit witnesses accepted by both verifiers determine the mathematical score.

## What changed
- Infeasible-state tabu, periodic penalties, event-triggered breakout and pair replacements explored many thousands of near-states; no zero-conflict 227-word proposal.
- A safe descendant-set dominance reduction removes 444 dominated words, retains 65,092, and was independently checked through protected string descendants; exact small-length optima agree. Global elastic CP runs found only invalid slack-two states.
- A new compatible-bundle kernel searches cliques of excluded words while tracking the union of incumbent blockers. Saturated blocker unions are pruned by exact subset-group lookup. Both kernel versions passed 36 exhaustive small-instance comparisons, including full neutral-neighbor sets where no augmentation exists.
- Native enumeration closed a 32-code component under neutral exchanges removing at most four words, with no strict improvement there. A separate protected-string removal enumerator independently checked the complete radius-two component.
- Optimized native search exhausted strict improving exchanges removing at most five and six root words: 442,020,804 and 11,058,288,841 search nodes, respectively. These are restricted local enumerations, **not a global bound**. No formal proof artifact was produced. A separate root-radius-five CP encoding timed out UNKNOWN and did not independently certify that larger enumeration.
- Radius-five neutral exploration discovered 38 code hashes after processing 32, leaving six pending. At least one processed 226-word witness lies outside the old radius-two component. The continuation is active; no complete radius-five component claim.
- Full unions of five arena constructions (896 candidates), and that union plus valid projections (930), were CP-optimal at 226 within those exact pools. Larger 983/3,000 candidate pools timed out with feasible 226 and open bounds.
- 80 conflict-endpoint/blocker-closure repairs all returned verified 225-word candidates: 44 encoded OPTIMAL and 36 FEASIBLE with open bounds. The global incumbent remained 226.
- Pinned KaMIS revision `2e4b3861b8063f05e8520434b97ce59e21ca49e7`: full sparse conflict graph has 65,536 vertices and 80,964,349 undirected edges; independently checked all small-instance edges. Two warm-start ILS runs retained 226; both from-scratch ReduMIS attempts failed with bad_alloc under a 6-GiB address-space cap, providing no mathematical negative.
- An unsigned plateau decrement in upstream ILS wraps zero to UINT_MAX before an impossible negative comparison. A narrowly documented saturating-decrement variant is now being tested, with original/patched hashes and arithmetic regression. This is an adaptation of upstream KaMIS, not an unchanged reproduction.
- Full-universe SciPy LP attempts returned no usable primal within budget; consequently they generated zero LP-guided repairs. This is an incomplete attempt.

## Sponsor evidence and current decisions
Real Exa searches researched current records, dynamic local search, Morris breakout and KaMIS. Provenance is in `artifacts/phase3/research_001/` and `research_002/`; the API call remains `providers.py::Providers.exa`, called from the phase-three research scripts.

In the second research cycle, a researcher identity actually recalled the analyst's complete 32-state scoped finding. A strategist recall returned attribution text, not the full algorithmic finding; do not claim substantive strategy transfer from that thin recall. Three real Tinker 4B choices selected `deep_bundle` for three contexts. The new Modal batch applies that selected action to distinct valid 225-word projections. This is evidence of a real proposal influencing an experiment, **not evidence of policy superiority**.

No new fine-tuning is justified by the present zero-improvement results. Earlier trained-versus-untrained evaluation and its negative/tied results remain documented in the phase-two report.

## Resources
All work is remote, under codegarden/, except the separately authorized isolated workflow. Public standard GitHub runners make zero Exa/past/Modal/Tinker calls unless explicitly running the serialized provider coordinator.

Conservative cumulative holds/accounting, including prior phases and the retained failed-launch reservation: Exa $0.077; past.dev 234 estimated credits; Modal $44.16; Tinker $22.80. These are not an assertion of actual bill charges. Latest provider coordinator receipts are the authority; unknown holds remain included. Existing cumulative caps: Exa $5, past 2,000 credits, Modal $50, Tinker $70, with full other-project guards and independent-verification reserves retained. Allocation expires 08:00 UTC; no new billable work after 07:45 without renewal.

## Still active
1. Complete the newly opened radius-five neutral frontier and test radius-six augmentation from a new 226-word state.
2. Compare the saturating-plateau KaMIS variant from incumbent and distant starts.
3. Run the Tinker-selected distant-basin bundle walkers on Modal.
4. Independently verify every cardinality improvement, and recheck arena/literature before any record claim.

Results live in artifacts/phase3/; each branch and source revision is listed in phase3_progress.json. Failed runs and solver timeouts stay visible. The absence of a 227-word witness remains unresolved.
