# Data sources and publication rights

The project studies **advertised GPU rental offers**. None of these observations establishes executed transaction prices, guaranteed available capacity, or hardware resale value.

| Source | Target and units | Published here | Permission / limitation |
| --- | --- | --- | --- |
| Pacific Machines GPU price pack v0.1.1-handover | Official headline advertised-rental targets; USD per GPU-hour | Official forecast, derived scores, configuration metadata, and reported research findings | The compilation's historical offer/price tables are not redistributed. Its “owner's default pending confirmation” license wording is not treated as an unconditional grant. |
| Alex Hubbard GPU Price Tracker, independently retrieved S3 snapshots | Daily median of eligible quality-ok AWS/Azure/GCP spot offers; SKU price divided by GPU count; USD per GPU-hour | A100 40GB and T4 contextual series, 234 dates each, January 12–November 6, 2026 | Explicit [DATA_LICENSE](https://raw.githubusercontent.com/alex-hubbard/gpu_price_tracker/ac287bacc95f3b2ceaa97af10a50031ee0abcacf/DATA_LICENSE) covers the archive and mirrors under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution, license links, changes, retrieval vintage, and point hashes accompany the data. |
| FastGPU historical compilation | Source-level headline medians with distinct spot/on-demand configurations | Existing reported forecast/score metadata; no historical compilation values | A matching independently licensed history archive was not verified. [Upstream dataset](https://huggingface.co/datasets/fastgpu/cloud-gpu-prices). |
| GPU Rental Prices upstream historical CSV | Cheapest-per-GPU daily rates | No matching historical overlay | The [data page](https://gpurentalprices.com/data) offers CC BY 4.0, but its cheapest-per-day statistic differs from the median competition target. |
| Chronos-2 | Fixed pretrained numerical forecasting model | Configuration, pinned revision, derived evaluation metrics, and future commitment | [Amazon model](https://huggingface.co/amazon/chronos-2), Apache 2.0; no model weights are redistributed here. |
| Exa and past.dev | Evidence discovery and cross-role memory | Source metadata, hashes, authored decisions, and measured usage where available | Restricted source excerpts, raw provider responses, private sessions, and credentials are excluded. |

## Independent historical context

Source: **Alex Hubbard, GPU Price Tracker**, [original repository](https://github.com/alex-hubbard/gpu_price_tracker). License evidence was retrieved on **November 15, 2026 UTC / November 14 Pacific**.

Changes: independently downloaded pre-cutoff snapshots; filtered eligible hyperscaler spot observations; divided full-SKU hourly price by GPU count; computed one median per UTC day. No calendar gaps are filled. Provider and regional composition can change, so this is not a fixed-basket return series.

Each published series has **65 missing calendar dates** within its 299-day coverage span. Current retrieval of recorded snapshots does not prove exact real-time historical availability or revision-free data.

The strict, predeclared exact-agreement test against the competition targets failed. The tolerance was not relaxed after inspection. Consequently these are separately identified contextual observations, never benchmark inputs, forecast overlays, or automatic scenario dollar anchors. Unverified A100 80GB/SXM and V100 mappings remain excluded.

The committed [history-and-traces artifact](../results/explorer-v3/history-and-traces.json) contains source URLs, permission decisions, attribution, retrieval timestamps, normalization, exact point hashes, and missingness. [Full audit and verification runs](research-explorer-v3.md).

## Publication boundaries

- The official November 6 forecast remains byte-identical. November 7–13 protected competition outcomes were not loaded.
- Frozen and retrospective policy studies retain their original time boundaries. Current literature is not silently added to historical model inputs.
- Prospective outcomes for November 16, 18, and 22 remain pending. Their evaluator is time-gated and requires separately audited compatible truth.
- Public artifacts contain derived research outputs and the explicitly licensed independent context, not the raw competition compilation or private provider resources.
- A source-specific license is not a blanket license over other sources, code, models, or the complete repository.
