# Quantile training v20 artifacts

This directory separates fixed ensemble controls, direct quantile-head training and future commitments. Existing v19 and official forecasts remain unchanged.

- `preflight/<run>/`: original fixed-ensemble selection, reconstructible predictions, loss contributions and technical readiness.
- `runs/<run>/report.json`: completed or gated study, actual update counts, quantile-head coefficients, development-only checkpoint selection and exploratory historical scores.
- `latest.json`: hash-verified canonical report pointer.
- `future/<run>/`: separate prospective status and, when eligible, commitments with signed publication receipts. No pending outcome is an observed result.
- `validation/<run>/`: exact arithmetic checks and PNG-only browser validation.

No private model paths or credentials are published. The 314 training windows and 24 seven-day retrospective cases are overlapping/dependent data, not independent market experiments. The internal head coefficients encode scalar quantiles and are not a predictive CDF.

Public arithmetic: `python -m compute_forecast.verify_quantile_v20` after installing the package. Authorized training additionally requires private data-volume access and Tinker resources. [Methods and source attribution](../../docs/quantile-training-v20.md).
