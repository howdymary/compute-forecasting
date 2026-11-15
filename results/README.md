# Public results

This directory contains versioned public research outputs. It is sufficient for inspecting the main numerical findings without a running application or account credentials. Numerical reruns require the separately obtained source data and, for training, provider access.

Current extension: [Pacific value v5](value-v5/README.md) adds approved matching history, the exact official-control audit, conditional economics and verified shared-memory receipts. The original manifest below describes its earlier frozen snapshot and is preserved.

## Artifact index

| Path | Contents |
| --- | --- |
| [manifest.json](manifest.json) | Exact byte counts, SHA-256 hashes, source endpoints, publication time, and source revisions |
| [frozen-v1/forecasts.csv](frozen-v1/forecasts.csv) | Unchanged November 6 official export: 37 series, 111 rows, horizons 1/3/7, q10/q50/q90 |
| [frozen-v1/release.json](frozen-v1/release.json) | Original frozen v1 result, controls, recorded traces, and provenance |
| [frozen-v1/outlook.md](frozen-v1/outlook.md) | Assumption-based rental and resale outlook |
| [frozen-v1/outlook-scenarios.json](frozen-v1/outlook-scenarios.json) | Published scenario assumptions |
| [expanded-v2/summary.json](expanded-v2/summary.json) | Completed six-SFT / three-RL campaign, controls, checkpoints, analyses, and execution receipts |
| [explorer-v3/chronos-control.json](explorer-v3/chronos-control.json) | One fixed Chronos-2 control, exact 12-cell scope, model revision, runtime, and pending future commitment |
| [explorer-v3/history-and-traces.json](explorer-v3/history-and-traces.json) | Independently licensed context, source-by-source permission decisions, and real paired traces |
| [explorer-v3/diagnostics.json](explorer-v3/diagnostics.json) | Coverage/width, feedback changes, denominators, and separate work units |
| [review-v4/findings.json](review-v4/findings.json) | Hash-verified portfolio reconstruction, exact matched contributions and training-readiness diagnostic |
| [review-v4/manifest.json](review-v4/manifest.json) | Byte hashes of the v4 core analysis |
| [review-v4/market/43754381651.json](review-v4/market/43754381651.json) | Six primary sources, authored memory receipts and two actual bounded planning decisions |
| [review-v4/runtime/43754381644.json](review-v4/runtime/43754381644.json) | Explicitly synthetic runtime checks and actual retained-source coverage metadata |
| [review-v4/ui-publication.json](review-v4/ui-publication.json) | Deployed UI revision, inspected PNG source hashes and validation run |
| [review-v4/operations-index.json](review-v4/operations-index.json) | Versioned interval, controlled evidence/criticism and pack-access receipts |
| [explorer-v3/series-metadata.json](explorer-v3/series-metadata.json) | Verified series labels, units, archived forecast points, and scenario definitions |

## Scope and interpretation

The frozen v1 SFT result is negative. Expanded v2 shows lower SFT loss on previously inspected, dependent A100 dates; its three RL selections return their SFT parents. The added Chronos comparison is retrospective and outside the frozen selector pool. The 15-cell numerical-grid summaries and 12-cell selector comparisons have different eligibility and must not be mixed.

Independent A100 40GB and T4 history is contextual only, not a matching competition history overlay. [Data rights and definitions](../docs/DATA_SOURCES.md). No raw competition offers, private trained model paths, development sessions, or restricted source excerpts are included.

Prospective outcomes remain pending. A committed hash is evidence of a fixed prediction, not evidence of accuracy.

## Verification and refresh

The **Publish verified public research snapshot** workflow retrieves only the listed public endpoints, enforces the frozen CSV hash and completed campaign scope, validates publication permissions and private-field exclusions, then commits snapshots with a SHA-256 manifest. It does not train models, load future outcomes, or modify numerical configurations.

The **Verify public research package** workflow checks the committed manifest, exact values, relative links, citation metadata, and PNG provenance against the original successful UI-validation artifacts. The application and immutable Actions runs remain complementary execution evidence.

The official CSV SHA-256 is:

```text
67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80
```

The manifest describes the committed snapshot; later live snapshots can have different publication timestamps or serving revisions without changing frozen numerical results.
