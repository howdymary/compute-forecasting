# Compute Forecast

Reproducible research on **advertised H100 and A100 GPU rental rates**, with a bounded experiment-selection study trained using Tinker.

## Current status

Implementation is on [compute-observatory](https://github.com/howdymary/compute-forecasting/tree/compute-observatory). The `metagame` branch must not be created or modified.

The foundation includes typed internal records, cutoff guards, a 24-configuration registry, internal scoring checks, and hosted validation. **No official forecasts, real-data benchmark scores, sponsor API calls, or policy improvements have been established.**

The Pacific starter kit, exact target/export contracts, and dataset license remain unverified. `reproduce` exits with an explicit blocked status until those contracts are verified and the official adapter exists.

## Research

1. How do representation and provider/configuration composition affect short-horizon GPU rental-rate forecast accuracy?
2. Does a Tinker-trained selector find better configurations than fixed/random search under six candidate evaluations per task?

The study does not assume improvement. See [the protocol](docs/protocol.md).

Advertised offers are distinct from executed transactions, available capacity, and physical GPU resale prices. Normalization precedents include [Silicon Data](https://www.silicondata.com/products/silicon-index) and [SemiAnalysis](https://semianalysis.com/gpu-pricing-index/).

## Remote workflow

Source edits use GitHub APIs. Builds and tests run on hosted Actions; experiments and deployment will run on Modal. No developer-machine clone, installation, or working files are required.

Pushes to `compute-observatory` run [foundation validation](.github/workflows/validate.yml). Hosted runners fetch the exact source archive without cloning and publish test, dependency, readiness and **synthetic-only** validation artifacts.

Commands below are intended for hosted runners:

```text
python -m compute_forecast preflight
python -m compute_forecast synthetic-smoke
python -m compute_forecast reproduce --run-spec configs/pacific.json
```

## Access required for real execution

Configure GitHub Actions secrets through repository settings, never in source or chat:

- MODAL_TOKEN_ID
- MODAL_TOKEN_SECRET
- TINKER_API_KEY
- EXA_API_KEY
- PAST_API_KEY

Provide the official starter and authorized dataset location. Do not redistribute the raw pack until its license and attribution have been verified.

## Validation boundary

Internal schemas and synthetic fixtures are application/test designs, not claims about the competition schema or real market data. Synthetic outputs are labeled and are never official exports.
