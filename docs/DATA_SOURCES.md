# Data sources, permissions and target definitions

Publication decisions below were checked on **November 15, 2026 UTC**. A public URL alone is not permission to redistribute. Every plotted observation retains its own source, units and frozen collection vintage.

## Current publication decision

The [official Pacific brief](https://drive.google.com/file/d/1r-dIO5Ol6RYLmcHXRwEUFr1vIBpi5CiZ/view) expressly grants **CC BY 4.0 on the compilation**, with component-specific provenance. The pack's DATA.md section 5 describes shipped open licenses, but its older section 5(g) retains default-pending wording. The current brief resolves the compilation-grant question. It does not remove source-register marketplace or third-party-aggregate caveats.

The v3 decision to withhold matching history was made before this explicit brief was verified. It is superseded for the approved v5 sources below; the frozen v3 artifact remains unchanged as an audit record.

| Source | Exact measure | Current publication | Permission and limits |
| --- | --- | --- | --- |
| Pacific Machines, gpu-price-pack v0.1.1-handover | Official starter daily target series, USD per GPU-hour | 36 exact submitted target histories, 3,204 observations; unchanged 37-series/111-row forecasts | [Compilation CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), current official brief and shipped DATA.md, ATTRIBUTION.md and sources_register.csv. Raw offer tables and the full archive are not republished here. |
| Alex Hubbard / afhubbard shipped filtered collector | Source-level hyperscaler spot daily medians | Four series, 234 dates each | Shipped CC BY 4.0 data license and attribution; daily-statistic source populations may vary. |
| GPU Rental Prices / gpurentalprices shipped filtered collector | Source-level neocloud on-demand daily medians | Twelve series, 89 dates each | Shipped CC BY 4.0 and applicable GitHub notice. This is the pack's median target, not an independently scraped cheapest-per-day statistic. |
| FastGPU / fastgpu_daily shipped filtered collector | Source-level spot/on-demand medians | Twenty series, 60 dates each | Shipped CC BY 4.0 register entry and pack attribution. Contract/tier identities remain separate. |
| Marketplace-ask target | Original submitted forecast; source-specific ask history | Forecast retained; matching history withheld | The source-register owner-decision caveat remains unresolved. Compilation licensing does not silently override it. |
| Independently retrieved Alex Hubbard archive | Daily median eligible quality-ok AWS/Azure/GCP spot offers, divided by SKU GPU count | A100 40GB and T4 contextual series, 234 dates each | [Explicit archive/mirror data license](https://raw.githubusercontent.com/alex-hubbard/gpu_price_tracker/ac287bacc95f3b2ceaa97af10a50031ee0abcacf/DATA_LICENSE), CC BY 4.0. Failed strict identity check against competition targets; never stitched to matching v5 history. |
| Epoch AI hardware | Form-factor-specific hardware references, power and documented release-price estimates | Selected attributed reference rows | [Epoch data](https://epoch.ai/data/machine-learning-hardware), CC BY 4.0. TDP is not measured whole-server power. Derived server allocations are not current module resale or official MSRP. |
| MLPerf-derived capability ladder | Precision/context-specific shipped per-accelerator ratios | Attributed A100/H100 context rows and descriptive rental/throughput ratios | Pack APACHE-2.0 source labels and attribution. These derived composites are not official verified MLCommons scores. Chains may splice benchmark families; exact notes remain available. |
| Chronos-2 | Pinned pretrained numerical control | Configuration, revision and scores, no weights | [Amazon model](https://huggingface.co/amazon/chronos-2), Apache 2.0. |
| Exa / past.dev | Current primary evidence, authorship and shared recall | Metadata, hashes and actual decision receipts | Original source bodies and private diagnostics remain private. Current research never enters archived benchmark features. |

The immutable [v5 study](../results/value-v5/runs/43757456253/study.json) records one permission decision per submitted series, exact catalog fields, source-file hashes, point hashes, attribution and URLs. [Copied notices](../results/value-v5/runs/43757456253/notices) and [additional source notices](../results/value-v5/runs/43758970357/notices) accompany the public derivatives.

## Coverage, gaps and vintage

Every matching history ends November 6. Counts differ by source; there are no fabricated observations or gap fills. The official starter defines each source/series/contract. Its frozen compilation is not evidence of exact real-time availability or absence of subsequent revisions.

The 673-file description is consistent with 672 entries in MANIFEST.sha256 plus the manifest itself. The archive hash is f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c.

Independent contextual A100/T4 history has 65 missing calendar dates in its 299-day span. Its identities and preprocessing remain separately documented in the [original context audit](research-explorer-v3.md).

The AWS spot archive is a different instrument. Its March–June 2026 coverage hole must never be interpolated across. No AWS spot study is substituted for Sunday's posted-rental targets.

## Publication and evaluation boundaries

- Advertised offers, transactions, available capacity and physical resale are different measures.
- Original forecasts and frozen numerical studies remain unchanged. The official CSV SHA256 is 67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80.
- Protected November 7–13 competition outcomes were not retrieved.
- Current primary evidence belongs to a dated current outlook, not historical forecasting inputs.
- Existing November commitments and the November 23 UTC evaluator gate remain unchanged; compatible outcomes are additionally required.
- Rental cashflow scenarios are calculations conditional on assumptions. Income-based residual proxies are not observed resale transactions or calibrated long-term intervals.
- A component license is not a blanket license over repository code, other sources or model resources.

## Prospective signals v6 source extension

The new [v6 cohort](prospective-signals-v6.md) uses the source’s explicitly licensed current JSON and health endpoints. Four exact provider configurations were retained on November15: Lambda A100 PCIe40GB (one/two-GPU nodes), Lambda H100 PCIe80GB, and HyperAI H100 PCIe80GB. The new IDs are not competition series IDs. Provider timestamps, null region/node metadata, quote availability limits and CC BY4 attribution remain attached. No historical-price endpoint was downloaded.

BLS PCU221122221122 is retained as an index with its actual retrieval vintage and preliminary footnotes. Primary news bodies remain private; public metadata and features preserve source hashes and first-observed timestamps. No source is backdated into the benchmark.


## Market-state v19

The [v19 source decision](market-state-v19.md#sources-and-publication-decisions) and [machine-readable audit](market-state-v19-sources.json) separate approved historical provider-group medians from current individual-contract captures. This study tests other-provider price changes and observed collection composition only. News, availability, BLS and infrastructure are excluded. Historical cohort quality checks use the frozen pack through November 6, so the selected universe is a retrospective cohort rather than a reconstruction of every origin-time eligible universe. The future cohort has its own first-vintage collection and eligibility rules.
