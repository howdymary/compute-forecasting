# Categorical continuation v21 artifacts

This is a separate, post-event study of the existing direct categorical forecasting model. It preserves the official export, earlier studies and existing prospective panels.

- [Registration and methods](../../docs/ce-continuation-v21.md).
- [Frozen training design](../../configs/ce-continuation-v21.json).
- [Immutable input binding](../../configs/ce-continuation-v21-inputs.json).
- [Completed data audit](data/44134233839/audit.json).
- [Completed optimizer-restoration preflight](preflight/44135344681/readiness.json).
- [Pilot execution](https://github.com/howdymary/mochi-demo/actions/runs/44136095711).
- [Separate future registration](../../configs/ce-continuation-v21-prospective.json).
- [Current future status](future/latest.json).
- [Interactive training and price figure](https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run/continuation).

After publication, `latest.json` points to an immutable `runs/<workflow-id>/report.json` and its SHA-256. Every run includes full development probabilities at actual saved checkpoints, the original selected checkpoint and one selected-checkpoint retrospective comparison. Versioned reports and failed or gated results remain available.

Preparation added 3,523 real training windows while preserving all 314 original windows. This expands configuration and temporal coverage within the same collector and eight-provider population; it does not add independent market experiments or supplementary news.

## Public verification

```bash
python -m compute_forecast.verify_continuation_v21
```

No service credentials are required to reconstruct the published arithmetic. Training needs authorized numerical inputs and private model resources; their resource-ID hashes are not weight-byte checksums. Restricted paths and credentials are excluded.

Development uses two reused dates. Exploratory evaluation uses 24 seven-day cases across three reused, dependent dates. Seeds share the same parent and market outcomes. Unknown provider charges remain null. Future outcomes are pending and are never filled with historical or synthetic values.

Prospective improvement is not yet established.
