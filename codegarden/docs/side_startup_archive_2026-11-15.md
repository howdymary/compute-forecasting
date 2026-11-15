# Startup and neutral-state experiments — 15 November 2026

**Best independently verified cardinality remains 226. No 227-word construction or global record was found.**

## Bounded cold initialization

Source `4e4e3eec815ced48acbfa18204ba0b4ea0025eef`; [run 43755774242](https://github.com/howdymary/compute-forecasting/actions/runs/43755774242); terminal artifact commit `1865237d35b00fc1f80ab6d71b0b8f7763ed3a9e`. Files are under `codegarden/artifacts/side_research/startup_001/`.

All three workers completed separator-pool construction, population initialization and actual evolution, then returned explicit witnesses accepted by both protected verifiers.

| Run | Seed | Policy | Verified size | Native wall seconds |
| --- | ---: | --- | ---: | ---: |
| Paired control | 2271139 | thin | 212 | 264.145 |
| Paired comparison | 2271139 | balanced | 208 | 260.184 |
| Additional exploration | 2271140 | balanced, selected by Tinker | 208 | 269.183 |

The first pair shares a seed and a 240-second soft budget. Thin uses a four-member population and one repetition; balanced uses eight and two. These are configuration bundles, so the difference does not identify one parameter's causal effect. The fresh-seed run is exploration.

This test resolves the prior startup bottleneck in this bounded setting. It does not establish neighborhood exhaustion or inability to reach227. The cold results remain below the retained226 incumbent.

The same whole-universe graph was rebuilt: 65,536 vertices, 80,964,349 edges, SHA-256 `de8221d0814e5fcb303f529d423e801713af1cbcd61e309d8a9937a6aad08564`. Native binaries retained generic ISA/static-runtime checks and independent small-graph tests.

Tinker selected balanced using two actual retrieved past.dev documents from `codegarden-global-43753466573-analyst`. The model was untrained. Its selected configuration did not outperform thin in this small comparison. The completed result was submitted once as `codegarden-startup-43755774242-analyst`, ingestion `f72b4415-e555-46a7-85b0-5bfaeeacbac2`. The saved ingestion checkpoint was processing; resume that handle rather than reingesting.

## Observe states hidden by strict best-witness export

Source `3ed4ee23547c3c9f8749b6137374a0b56703f7d5`; [run 43756020700](https://github.com/howdymary/compute-forecasting/actions/runs/43756020700); terminal artifact commit `8a92ee195aae5672a2c0efae5ac483e595b4e444`. Files are under `codegarden/artifacts/side_research/archive_001/`.

The pinned upstream ILS copies its final best solution only on strict improvement. A bounded observational hook therefore exported distinct full-graph states with at least226 selected vertices, without changing search acceptance. Every captured witness was checked by both protected verifiers.

| Worker | Seed | Captured distinct226 states | New outside the recorded152 arrays | Final verified size |
| --- | ---: | ---: | ---: | ---: |
| Default forcing | 2271141 | 10 | 0 | 226 |
| Tinker-selected forcing | 2271141 | 37 | 0 | 226 |

The archive cap was64 per worker. Neither reached it. The counts measure observed states in these runs, not every reachable state. No novel226 state qualified for the bounded exact followup, so no exact archive repair was run. The two workers used about200 native wall seconds each. The selected policy captured more known states but showed no cardinality gain.

Exa research on [Graph Partitioning for Independent Sets](https://arxiv.org/abs/1502.01687) and [Evolutionary Algorithms For Independent Sets](https://publikationen.bibliothek.kit.edu/1000048276/3609658) informed the plateau/diversity hypothesis; source inspection established the strict-export gap. This is an adaptation of existing methods, not a discovery claim. Actual query provenance is in `codegarden/side_archive/research_provenance.json`. Controller Exa calls and past.dev recalls are recorded in execution artifacts.

## Next experiment

The new `side_seeded_evo` experiment seeds an identity-labelled full graph with eight far-apart verified226 parents. It compares the original strict population insertion gate with a treatment that admits distinct equal-size offspring into the existing ILS and nearest eligible non-best replacement path. It bypasses root kernelization and disables recursive reduction only in this explicit seeded mode, avoiding any assumption about reduced-to-original word mappings.

The paired runs will share seed2271142, parents, resources and time limit. A third fresh-seed run2271143 uses the Tinker-selected insertion policy and is labelled exploration. Parent files, hashes, inserted sizes, root-identity markers and policy markers will be retained. Small-graph fixtures must check both modes and reject a conflicting parent before remote searches start.

This is a new hypothesis, not a claimed result. Both protected verifier files remain unchanged. Any227 candidate requires the separate frozen-checker acceptance job. Global-record auditing remains incomplete; the latest recorded arena comparison in these artifacts was226, not a proof of a global maximum.
