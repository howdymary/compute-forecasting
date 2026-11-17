# Market-state v19 artifacts

The registered comparison tests other-provider within-group price changes and observed collection composition. News and availability are excluded.

- [Training protocol](../../configs/market-state-v19.json)
- [Readiness gates](../../configs/market-state-v19-readiness.json)
- [Measured data readiness](readiness/44040999343/audit.json)
- [Native and matched numerical controls](controls/44041529178/controls.json)
- [First current-source capture](captures/44040999346/capture.json)
- [Latest completed report](latest.json) (published only after all six runs reconstruct)
- [Methods, source rights and limitations](../../docs/market-state-v19.md)
- [Future protocol](../../configs/market-state-v19-prospective.json)
- [Fixed final analysis](../../configs/market-state-v19-analysis.json)

Public arithmetic verification: `python -m compute_forecast.verify_market_v19`.

Manifests bind every public file by SHA-256. Private source bodies, checkpoint paths and numerical states remain outside this directory. Completed model outputs are retained even if orchestration later exits unsuccessfully; workflow receipts expose that distinction. Negative findings and failed collection/setup attempts remain inspectable. No private access is required to reconstruct the published probability/quantile/loss arithmetic.

The experiment is running; prospective improvement is not yet established.
