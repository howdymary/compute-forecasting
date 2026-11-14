# Measured status and release boundaries

All code and workflows are on compute-observatory. No metagame branch was created or modified. Development, package installation, tests, downloads and experiments run on hosted GitHub Actions and Modal, not a workstation checkout.

## Verified runs

- Pack integrity: Actions run 43634354788. Published archive SHA-256 f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c; all 672 manifest-listed files verified.
- Official starter execution: run 43637893251, code 61c6e305521f2cb6baa21bce4c101e4495cc721b. Four unmodified official methods at July 24 (training) and August 8 (development); official scorer refused deliberately contaminated history. Raw pack is retained privately on Modal.
- Tinker warmup: run 43639917509, code 3e3abfad1c0be72f8dfc83e8a0507fb70edbd963. Qwen/Qwen3.5-4B, rank-16 LoRA, 147 training cases from one temporal origin, 168 development cases from one later origin. Three epochs, 15 actual optimizer updates, 441 training-example presentations, 672 inference decisions. Three state and sampler checkpoints are retained in the run artifact.

## Warmup results (diagnostic, not the main experiment)

Mean pinball losses reconstructed from the official report's rounded per-cell metrics on the August 8 development origin:

| Policy | Diagnostic loss |
|---|---:|
| Starting model | 0.05654880 |
| SFT epoch 1 | 0.04938868 |
| SFT epoch 2 | 0.04593399 |
| SFT epoch 3 | 0.05287022 |
| Fixed last-value empirical | 0.04321399 |
| Fixed drift | 0.04396017 |
| Seeded random choice | 0.05714498 |

Epoch 2 is about 18.8% below the starting policy, but does not beat the strongest fixed reference. Checkpoint selection uses development results, so these are not held-out final results. Cases share an origin, series and horizons; 168 cases are not 168 independent temporal replications. This warmup selects one of four starter methods per case. It does not implement the proposed equal-budget six-trial experiment-selection study, and does not establish improved research ability. No RL result is claimed.

On July 24 the official drift baseline's pooled skill was 0.207774, while mean per-series skill was -2.621166. This is a reproduced baseline, not a contribution or an out-of-sample result. Both aggregations must be retained in the main evaluation.

Actual model billing was not available in the SDK result. Cost is marked unavailable, never inferred from credits.

## Information boundaries

The final evaluation origins remain unopened: September 27; October 4, 11, 18 and 25. The official competition origin is November 6. The pack is a retrospectively assembled frozen vintage, not proof that every row was accessible in its current form at a historical origin. Retrieval timestamps and provisional aggregation windows require separate scrutiny. No post-November-6 competition truth has been requested.

## Data and licensing

The primary measurement is advertised rental offers, not executed transactions, guaranteed available capacity or hardware resale prices. Provider/configuration normalization is established practice; credit Silicon Data's Silicon Index and SemiAnalysis's GPU Pricing Index. Our intended contribution is a reproducible empirical evaluation.

DATA.md describes CC BY 4.0 for the compilation as the owner's default pending confirmation and retains open owner decisions and upstream terms. Do not redistribute the raw pack. Preserve ATTRIBUTION.md, sources_register.csv, licenses and table provenance. EWLuda is a pointer with unresolved licensing and must remain excluded. Removed Vast.ai and RunPod rows must not be reconstructed. Provisional weekly/index tables are not eligible benchmark features by default.

## Outstanding release work

The main representation benchmark, equal-budget search study, cross-agent Exa/past.dev loop, polished application, final-period evaluation and official submission export are not yet complete. The reproduce CLI remains blocked until the official adapter and release checks are integrated. Credentials and credits alone do not establish sponsor eligibility.
