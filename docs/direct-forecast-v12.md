# Direct GPU-price forecasting v12

Registered November 16, 2026, after the event. This study trains model weights to predict observed future log-price changes directly. It does not change the experiment-selector studies or official submission.

The primary comparison is a Qwen3.5-4B LoRA versus its untuned base and the unmodified official numerical baselines. The secondary comparison requires origin-safe supplementary evidence. Current retrieval alone cannot satisfy that gate.

[Protocol](../configs/direct-forecast-v12.json). Data preparation and exact target/cohort audit run remotely before training. Measured counts, eligibility and gates will be published. No performance result is claimed at registration.

Training labels end September 19; development origins are September 27 and October 4; October 11/18/25 form an additional **retrospective** evaluation. These periods have been accessible to earlier research and are not untouched tests. The primary endpoint is seven-day USD-per-GPU-hour quantile pinball. Later compatible observations are required for prospective accuracy.

Supplementary candidates: [Price of Compute](https://priceofcompute.com/api), [versioned AWS rate cards](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-the-aws-price-list-bulk-api-fetching-price-list-files-manually.html), [AWS Spot API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html), [ALFRED BLS vintages](https://alfred.stlouisfed.org/series?seid=PCU221122221122), [EIA](https://www.eia.gov/opendata/), and [SEC EDGAR](https://www.sec.gov/edgar/sec-api-documentation). Check source-specific permissions, vintage and identity before ingestion. Existing Epoch/MLPerf rows are not new data sources.

SFT follows the [official Tinker tutorial](https://tinker-docs.thinkingmachines.ai/tutorials/basics/first-sft/). [Thinking Machines' direct time-series example](https://thinkingmachines.ai/news/inkling-2-small/) is a precedent, not evidence of GPU-price performance. Actual future outcomes train return-vector likelihood; empirical quantiles come from fixed-budget samples. A single observed value is not labeled as three true quantiles. RL remains separately gated.

Raw pack data, secrets and model paths stay private. Approved numerical derivatives retain Pacific and component attribution. Protected November 7–13 outcomes are excluded; existing November 23 gates are unchanged.

## Registered implementation

The official non-thinking renderer is locked before training. A fixed 64-sample budget produces the three forecast quantiles; invalid outputs trigger the registered last-value fallback and remain counted. Optimizer and sampler checkpoints are retained privately in Tinker for 30 days, with study/configuration/seed metadata discoverable through the authenticated RestClient. Private paths are never written into public run artifacts.

The source audit requires both the collector and instrument class. Marketplace asks are excluded. Data windows are approved, attributed numerical derivatives, not raw offer tables. The hosted preparation path is available when Modal authentication expires.

The evidence-augmented arm remains gated until a varying, origin-safe supplementary table is registered. The price-only model can train independently. This does not establish an effect of news, infrastructure or BLS features.
