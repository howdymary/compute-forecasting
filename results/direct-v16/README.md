# Direct-forecasting diagnosis

[Current diagnosis](runs/43997050518/diagnosis.json) · [Numerical findings](../../docs/direct-v16-diagnostic-findings.md) · [Manifest](runs/43997050518/manifest.json)

Post-hoc reconstruction from saved samples, not another training or forecasting campaign. All training, development selections and future protocols remain unchanged.

[Diagnosis and publication plan](../../docs/direct-v16-publication-plan.md) · [Credential-free verification workflow](https://github.com/howdymary/mochi-demo/actions/runs/43998461487)

~~~sh
PYTHONPATH=src python scripts/verify_direct_v16_public.py --root .
~~~

This command verifies committed samples, quantiles, losses, cohorts, contribution sums and median/shape accounting without model credentials or prepared-data access. Source-composition reconstruction additionally requires the hash-bound prepared dataset; it is not claimed by the public check.
