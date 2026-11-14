# Research protocol v1

Status: preregistered implementation design; no real-data results exist yet.

## Measurement and precedent

The benchmark concerns advertised GPU rental rates. Offers do not establish executed transactions or available capacity. Physical GPU resale prices belong to a separate scenario analysis.

Provider normalization and composition control are established practices. Credit:
- https://www.silicondata.com/products/silicon-index
- https://semianalysis.com/gpu-pricing-index/

## Official contract gate

Do not implement source-column mapping or official export aggregation until the Pacific starter kit has been inspected. Internal Python contracts are not assertions about pack fields.

Verify exact targets, cutoff timestamp/timezone, horizon semantics, units, aggregation, scoring, export schema, historical revisions, and licensing. Unknown licensing prohibits redistribution.

## Primary study

Compare level/log representation and target-only/raw-composition/fixed-basket inputs, holding the Ridge family constant. Candidate grid: 3 composition choices x 2 representations x 2 windows (28/56 days) x 2 regularization settings (1/100).

Mark unsupported candidates ineligible before comparison. Never change the competition target.

Fit all transformations, imputers, basket membership and weights on eligible training data. Freeze fixed-basket weights within each training boundary. Missingness is not zero and cannot be repaired with future values.

## Temporal evaluation

Inspect actual history before choosing calendar boundaries. Freeze chronological train, development, and untouched final periods before candidate results are viewed. Separate partitions by enough time that seven-day labels do not cross boundaries.

Use rolling origins and matured, out-of-sample residuals for quantile calibration. Never use random row splits. Report origins, date coverage, overlap and calibration sample counts. Offer counts are not independent forecast cases.

Follow official pinball aggregation and last-value skill exactly. Internal helper scores must never be labeled official.

The November 6 forecast outcomes already exist during the event. Do not retrieve them into forecasting or research-agent context. Report internal held-out scores separately if official scoring outcomes are unavailable.

## Secondary study

Use six trials per task, including two common initial trials. Compare fixed search, seeded random search, starting Tinker policy and SFT policy with identical information access and eligible menus.

Tinker selects configuration IDs; deterministic tools fit models and calculate scores. Train only from completed development experiments. Split policy examples by chronological task, never by masks of the same task.

Teacher labels may use completed training-task results, but observations may not expose untested scores or the teacher's next action. The final task period never enters training.

## Evidence and memory

Maintain actual research creation time separately from market availability. Do not backdate records created during the hackathon.

Publication dates alone do not prove historical availability of page content. Require versioned snapshots and verified availability; unknown evidence fails closed.

Current-news and benchmark memory use separate past.dev projects. Benchmark tasks use restricted audiences and task-specific identities. Store source IDs, ingestion IDs, read provenance and actual downstream consumption.

Canonical numerical artifacts live outside past.dev. Memory text is not a scoring authority.

## Limits and claims

Pretrained policies can contain later knowledge. Mask dates/assets where practical and exclude market-news narratives, but do not claim complete removal.

Report unsuccessful experiments, null results, uncertainty and limitations. A genuine training update does not establish improved research ability.
