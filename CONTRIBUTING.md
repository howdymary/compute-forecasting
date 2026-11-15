# Contributing

Start with the [project overview](README.md), [methods index](docs/README.md), and [public results](results/README.md). Separate improvements to presentation or retrospective analysis from changes to registered forecasting procedures.

## Research changes

- Keep advertised offers, transactions, available capacity, and resale distinct.
- Preserve original target definitions, units, forecast origins, and publication permissions.
- Use chronological evaluation, past-only inputs, matured labels, and matched comparison cells.
- Do not retune on opened periods or replace the frozen official export. New studies need separate configurations and identifiers.
- Report unsuccessful runs, dependent observations, unknown costs, and negative findings.
- Preserve source and checkpoint provenance. Do not commit private checkpoint URIs, credentials, restricted excerpts, or the raw competition pack.

## Remote workflow

The registered execution entrypoints target the `compute-observatory` branch. Follow the [reproduction runbook](docs/campaign-v2-reproduction.md) for access requirements and GitHub Actions / Modal execution. Inspect committed results without credentials before requesting a costly rerun.

Use small, reviewable commits and the existing tests. UI changes should retain exact data values, keyboard/touch access, reduced motion, responsive layouts, immutable pins, and separate pricing/research loading.

The public-result publisher updates only its allowlisted results paths. Its validation checks hashes, scientific scope, relative documentation links, screenshot provenance, and excluded private fields. Publishing new outputs does not reclassify retrospective evaluations as prospective ones.
