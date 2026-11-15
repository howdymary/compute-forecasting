# Expanded robustness study

Registered configuration: `mochi/configs/robustness-v2.json`. Runtime: `mochi/src/mochi/robustness.py`. Numerical task and success verifier remain the original supported pushing experiment, not the new desk-humanoid design or proposed bowling task.

## Question and budget

V1's research-selected controller improved on its small held-out cohort but failed under higher friction and mass. Its conventional search also had a narrower controller-family space. This follow-up broadens development to an equal low/high friction-and-mass mixture and gives both search arms access to the same four controller families. It is a fresh study; do not pool the outcomes with V1 or infer a causal search/memory benefit.

- Eight research rounds, four candidates per round, 24 development seeds: 768 candidate rollouts.
- Conventional control: 32 candidates, the same four families, 24 development seeds: 768 candidate rollouts.
- Initial development measurement: 24 rollouts.
- Final evaluation of three frozen policies on 24 development, 64 held-out mixture, and 64 high-friction/mass stress scenarios: 456 rollouts.
- Total: 2,016 rollouts, at most eight concurrent single-CPU Modal workers. Each completed row records requested resources and simulation duration. These are execution receipts, not a claim about exact billed container time or dollar spend.

Both search methods use the same parameter-sampling helper. The research arm chooses families using source-grounded model decisions; the conventional arm samples families uniformly. Equal total rollout counts do not equate model or retrieval costs, nor do they force equal samples within every family.

The research-selected policy is frozen before held-out or stress evaluation. The conventional winner is selected using development data only. The deterministic critic gate rejects a candidate without a strict improvement in development success count, then mean final distance as a tie-breaker. A model critic can also veto a candidate. Small cohorts, narrow policy bounds, correlated simulation assumptions, and disabled non-hand self-collisions remain limitations.

## Service use

Exa runs once per research round. Tinker supplies researcher, designer, experimenter, and critic decisions, then one prospective next-question decision: 33 total. The current advertised model list is checked for a supported larger model; the exact selected ID is logged and reported. The verified 4B sampler is retained if capability inspection or compatible renderer setup fails. This is model inference in the outer loop, with no new neural motor-policy training.

Four identities exchange 33 source records and 41 cross-agent recalls in a successful complete run. Every read must return the required source ID under the explicit reader's actual audience access. Only then is the exact numerical payload resolved by ID for model context. The expanded run does not repeat V1's private-canary experiment; its own report must not claim that test passed again.

The new study uses the separate `mochi-robustness-lab` Modal app and fresh Mochi audience and identity names. Provider keys remain in the backend GitHub Actions environment.

## Incomplete first attempt

[Workflow 43765530700](https://github.com/howdymary/compute-forecasting/actions/runs/43765530700) stopped when a critic could not recall the earlier hypothesis's exact source ID. It completed 216 simulations, two Exa searches, seven Tinker decisions, eight memory writes, and nine verified cross-agent reads. These are partial execution counts, not a completed evaluation. The source guard failed closed; no unverified canonical-memory fallback was counted.

The next attempt uses natural-language topic queries and an exact occurrence-time window to disambiguate same-topic records. It retains reader identity, audience enforcement, and exact source-ID verification. It also archives all initial rollout rows and uses current model identifiers.

Primary references checked November 15, 2026:

- [past.dev endpoint reference](https://past.dev/docs/memory-api/api-reference#post-api-v1-recall): `occurredFrom` and `occurredTo` are inclusive bounds; `identity` determines eligible audiences. Metadata is not a recall filter.
- [past.dev OpenAPI](https://past.dev/openapi.json): exact request schemas, source evidence, ingestion readiness, and recall limits.
- [Tinker models](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/): current model IDs and retirement information. Package compatibility was inspected in the pinned `tinker==0.39.0` and `tinker-cookbook==0.6.1` wheels.

## Audit and publication

Download the successful workflow artifact and run, from the repository root:

```sh
python mochi/scripts/audit_robustness.py mochi/artifacts/robustness-v2/report.json
```

The audit recomputes summaries from every trial, checks the exact seed distributions and disjoint cohorts, verifies all 2,016 per-rollout receipts, checks selected-policy/configuration hashes, and traces all required cross-agent reads to source records actually used by model decisions. The static design page publishes this study separately from V1 after the audit passes.
