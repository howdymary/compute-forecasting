# Categorical CE continuation v21

This post-event study continues the operational v19 direct forecaster. It preserves Qwen3.5-4B LoRA16, the input and renderer, the frozen 19 future-price levels (including zero change), conditional probability extraction, CE objective and quantile convention.

## Questions and controls

A is the frozen v19 price-only seed17 checkpoint30. B continues on the original corpus; C continues on a larger verified corpus. Both updated arms restore the same A weights **and optimizer**, use learning rate0.00002 and batch16, and receive at most100 additional updates with checkpoints0/20/50/100. All continuation ordering seeds share that same parent. They vary only future example order.

B versus A tests the complete continuation procedure, not learning rate alone. C versus B tests corpus expansion under matched training. The old high-rate run already reached59 updates, and update30 had lower development loss. More steps are not assumed to help.

[Registered configuration](../configs/ce-continuation-v21.json) and [new future protocol](../configs/ce-continuation-v21-prospective.json) are committed before data-readiness assessment or optimization.

## Data and information boundaries

Original training has314 windows /942 horizon examples. Expansion retains every original task and adds metadata-selected H100/A100 source/provider/SKU/region/node daily quote-median windows from the same approved Pacific source classes. It uses training origins no later than October4 and labels no later than October11. The original development and retrospective tasks remain identical.

Source-specific grouping, instruments and USD/GPU-hour units remain explicit. No series are stitched together. The separate AWS change-event archive is not ingested, so its missing March–June segment is not interpolated or applied to unrelated collector observations. No protected November7–13 outcomes are retrieved.

Selection is source/provider/family round robin plus uniformly spaced calendar origins, never changed-price oversampling. Exact task duplicates are removed; repeated flat contexts and overlapping windows are reported as dependent observations. Gates require at least628 windows, six added groups,120 distinct origins and114 changed-seven-day windows, at least eight providers, unchanged original tasks and adequate frozen support. These are engineering screens, not power guarantees.

Pacific Machines gpu-price-pack v0.1.1-handover is the CC BY4.0 compilation; approved source IDs afhubbard, gpurentalprices and fastgpu_daily retain their component rights and attribution in [DATA_SOURCES](DATA_SOURCES.md). Raw offers stay in the verified private pack. Public predictions, source-level audits and input hashes support reproduction.

Historical source-reported snapshot timestamps do not establish independent historical publication vintages. Base pretraining exposure remains unknown. All development and retrospective dates have already been opened.

## Restoration and bounded execution

Tinker SDK0.39.1 documents [create_training_client_from_state_with_optimizer](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/serviceclient/), restoring saved weights and Adam state. A failed restore gates the study rather than silently resetting moments. The committed v19 dependency lock is reused.

The batch stream is deterministic, begins at offset480 and wraps at corpus boundaries without short batches. Its full task/horizon hash, unique exposures, repetitions, prompt-token presentations and optimizer acknowledgments are retained. Additional update0 is the already-trained parent, not an untuned model.

One pilot ordering seed17 is run for both eligible arms. The prespecified development gate can unlock seeds29/43; at most six runs /600 new updates /18 learned persistent checkpoints, with zero checkpoint deletion or billing changes. Checkpoint zero stays eligible. Development-only selection has equal opportunities for B and C. A data benefit requires a separate matched C-minus-B result.

All learned states and checkpoint selections remain private where required; public resource-ID hashes are not weight-byte checksums. Publication retries reuse completed optimization and saved predictions.

## Future evaluation

The new contract-transfer panel preserves every prior registration, including the November23 gate and existing v18/v19/v20 dates. It uses the same licensed first-vintage source cohort with separate study IDs and bindings,16 weekly origins starting December20 and fixed analysis no earlier than April12. Shared outcomes are dependent and do not constitute independent replication.

All available A/B/C arms receive identical origin-safe inputs. A development-selected primary continuation is frozen before issuance. Full probabilities and quantiles bind to exact snapshots, source revisions and checkpoint identities, with verified signed publication times. Missing or stale quotes remain unavailable. No test is extended until it wins; no automatic future retuning.

## Reproduction and interface

Training, builds and testing run on GitHub Actions and Modal. No local workspace checkout is required for execution. A credential-free verifier reconstructs published probabilities, quantiles, scores and selections. Authorized numerical reruns additionally need the verified pack, private model resources and service access.

The cream interactive figure links actual saved additional updates to actual price forecasts on fixed axes, with uncertainty width, coverage, source-bound pins and explicit historical/future labels. No video or recording work is included.

Prospective improvement is not yet established.
